# -*- coding: utf-8 -*-
"""
Crawler sử dụng newspaper3k để cào nhanh và đơn giản
"""
import random
import re
import html
import time
import hashlib
import json
import csv
import signal
import threading
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from newspaper import Article
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import os

# Thêm path để import config
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import (USER_AGENTS, NEWS_SOURCES, USE_MOBILE_VERSION,
                    REQUEST_DELAY_MIN, REQUEST_DELAY_MAX,
                    PAGE_DELAY_MIN, PAGE_DELAY_MAX,
                    CATEGORY_DELAY_MIN, CATEGORY_DELAY_MAX,
                    MAX_RETRIES, TIMEOUT, MAX_WORKERS,
                    ENABLE_ADAPTIVE_THROTTLING, ENABLE_RESPONSE_CACHE,
                    ENABLE_BATCH_PROCESSING, BATCH_SIZE, CONNECTION_POOL_SIZE,
                    MAX_RETRIES_FOR_429, SAVE_AGGREGATE_EVERY, PER_DOMAIN_DELAYS,
                    AUTO_DISCOVER_CATEGORIES, DISCOVERY_SEED_LIMIT,
                    PROGRESS_USE_COLOR, PROGRESS_BAR_WIDTH, PROGRESS_RATE_UNIT)
from utils.data_utils import DataSaver


class NewspaperCrawler:
    _DOMAIN_SCHEDULER_LOCK = threading.Lock()
    _DOMAIN_NEXT_REQUEST_AT = {}
    _DOMAIN_REQUEST_LOCKS = {}
    _ANSI_RESET = "\033[0m"
    _ANSI_GRAY = "\033[90m"
    _ANSI_PINK = "\033[95m"
    _ANSI_GREEN = "\033[92m"
    _ANSI_RED = "\033[91m"
    _ANSI_CYAN = "\033[96m"

    _NOISE_PATTERNS = [
        r'Mời bạn đọc.*?$', r'Xem thêm.*?$', r'Đọc thêm.*?$',
        r'Theo dõi.*?trên.*?$', r'Bình luận.*?$', r'Tags?:.*?$',
        r'Chia sẻ.*?$', r'Bản quyền.*?$', r'All rights reserved.*?$',
        r'Copyright.*?$', r'\bAds?\b.*?$', r'Quảng cáo.*?$',
        r'Hotline:.*?$', r'Email:.*?$', r'Liên hệ.*?$',
        r'Tải app.*?$', r'Download app.*?$',
        r'^\s*\d+\s*$',  # dòng chỉ có số (page number)
    ]

    _SOURCE_LINK_CONFIGS = {
        # ── Nhóm A: VnExpress ─────────────────────────────────────────────
        'vnexpress': {
            'cat_url':  '{base}/{cat}',
            'page_url': '{base}/{cat}-p{page}',
            'link_ext': ['.html', '.htm'],
            'link_re':  None,                       # chỉ cần có chữ số
            'exclude':  ['/tag/', '/topic/', '/search/', '/event/', '#box_comment'],
        },
        # ── Nhóm B: VietnamPlus (.vnp) ────────────────────────────────────
        'vietnamplus': {
            'cat_url':  '{base}/{cat}/',
            'page_url': '{base}/{cat}/?page={page}',
            'link_ext': ['.vnp'],
            'link_re':  r'post\d+\.vnp',
            'exclude':  ['/tag/', '/rss/', '/topics/'],
        },
        # ── Nhóm C: Nhân Dân (post*.html) ─────────────────────────────────
        'nhandan': {
            'cat_url':  '{base}/{cat}/',
            'page_url': '{base}/{cat}/?page={page}',
            'link_ext': ['.html'],
            'link_re':  r'post\d+\.html',
            'exclude':  ['/tag/', '/rss/', '/chu-de/'],
        },
        # ── Nhóm D-1: QDND (không ext, -NNNNNNN) ─────────────────────────
        'qdnd': {
            'cat_url':  '{base}/{cat}',
            'page_url': '{base}/{cat}?trang={page}',
            'link_ext': None,                       # không yêu cầu đuôi file
            'link_re':  r'-\d{5,}$',               # kết thúc bằng -NNNNN+
            'exclude':  ['/infographic/', '/media/', '/tag/'],
        },
        # ── Nhóm D-2: CAND (không ext, -iNNNNNN) ─────────────────────────
        'cand': {
            'cat_url':  '{base}/{cat}/',
            'page_url': '{base}/{cat}/?trang={page}',
            'link_ext': None,
            'link_re':  r'-i\d{4,}',               # chứa -iNNNN+
            'exclude':  ['/tag/', '/chu-de/'],
        },
        # ── Nhóm E: Báo Đầu tư (-d*.html) ────────────────────────────────
        'baodautu': {
            'cat_url':  '{base}/{cat}/',
            'page_url': '{base}/{cat}/p{page}/',
            'link_ext': ['.html'],
            'link_re':  r'-d\d+\.html',
            'exclude':  ['/tag/'],
        },
        # ── Nhóm F-1: Báo Chính phủ (.htm, ID dài) ───────────────────────
        'baochinhphu': {
            'cat_url':  '{base}/{cat}.htm',
            'page_url': '{base}/{cat}.htm?page={page}',
            'link_ext': ['.htm'],
            'link_re':  r'\d{10,}\.htm',            # ID >= 10 chữ số
            'exclude':  ['/chu-de/', '/tag/', '/topics/'],
        },
        # ── Nhóm F-2: VTV (.htm, ID dài) ──────────────────────────────────
        'vtv': {
            'cat_url':  '{base}/{cat}.htm',
            'page_url': '{base}/{cat}.htm?page={page}',
            'link_ext': ['.htm'],
            'link_re':  r'\d{10,}\.htm',
            'exclude':  ['/dong-su-kien/', '/tag/', '/chu-de/', '/topics/'],
        },
        # ── Nhóm G: Lao Động (JS cookie challenge → bypass + HTML) ─────────
        'laodong': {
            'use_js_bypass': True,
            'cat_url':  '{base}/{cat}',
            'page_url': '{base}/{cat}?page={page}',
            'link_ext': ['.ldo'],
            'link_re':  r'\d{5,}\.ldo',
            'exclude':  ['/tag/', '/chu-de/', '/video/'],
            'sitemap_url': '{base}/SiteMap.xml',
            'sitemap_cat_url': '{base}/sitemap/{cat}.xml',
        },
    }

    _CHROME_HEADERS = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'DNT': '1',
        'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
    }

    # File flag để dừng từ bên ngoài (STOP.bat)
    STOP_FLAG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'STOP.flag')

    def __init__(self, use_mobile: bool = False, max_article_age_days: int = 730):
        self.use_mobile = use_mobile
        self.session = requests.Session()
        # Bỏ qua proxy hệ thống (thường gây lỗi WinError 10013 trên một số máy chặn socket)
        self.session.trust_env = False
        self.articles_data = []
        self.content_hashes = set()  # dedup theo nội dung
        self.max_article_age_days = max_article_age_days  # mặc định 2 năm
        self._js_bypass_done = {}  # cache domain đã bypass JS challenge
        # ── Hỗ trợ dừng giữa chừng ──
        self._stop_requested = False
        self._stop_lock = threading.Lock()
        self._collected_articles = []  # bài đã cào (dùng khi dừng giữa chừng)
        
        # ── Tối ưu hóa nâng cao ──
        self._response_cache = {} if ENABLE_RESPONSE_CACHE else None  # {url: response}
        self._cache_lock = threading.Lock()
        self._current_delay_multiplier = 1.0  # Adaptive throttling multiplier
        self._429_count = 0  # Đếm số lần nhận 429
        self._requests_count = 0  # Đếm tổng requests
        
        # Setup HTTP connection pooling
        self._setup_connection_pooling()
        
        # Xóa STOP.flag cũ nếu còn tồn tại khi khởi tạo
        self._clear_stop_flag()

    def _setup_connection_pooling(self):
        """
        Thiết lập Connection Pooling (Bể chứa kết nối) & Chiến lược Retry.
        Giải thích cho GV: Thay vì mỗi lần request báo, máy tính phải thực hiện quá trình 
        bắt tay 3 bước (TCP 3-way handshake) rất tốn thời gian, Connection Pool sẽ "giữ nóng" 
        các cổng kết nối này. Khi có request mạng mới, nó xài lại cổng cũ -> Tốc độ tăng gấp nhiều lần.
        """
        if not ENABLE_BATCH_PROCESSING:
            return
        
        # urllib3 Retry: Tự động bắt lỗi ở tầng thấp nhất của gói tin mạng
        retry_strategy = Retry(
            total=MAX_RETRIES,                           
            status_forcelist=[429, 500, 502, 503, 504],  
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            # backoff_factor=1 có nghĩa là thời gian chờ tăng lũy thừa: 1s, 2s, 4s, 8s -> Tránh đánh sập server của ngta
            backoff_factor=1,  
            respect_retry_after_header=True
        )
        
        # Khởi tạo Adapter gắn chiến lược trên vào Session của requests
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=CONNECTION_POOL_SIZE,       # Số lượng kết nối (đường ống) mở đồng thời
            pool_maxsize=CONNECTION_POOL_SIZE,
            pool_block=False                             # Nếu bể đầy, không khóa chết mà tự mở kết nối bên ngoài
        )
        
        # Gắn Adapter này cho cả luồng bảo mật (https) và không bảo mật (http)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        # Ràng buộc thời gian đợi tối đa, qua số giây này mà web báo không đẩy data về thì bỏ qua bài này.
        self.session.timeout = TIMEOUT

    def _check_stop_file(self) -> bool:
        """Kiểm tra file STOP.flag có tồn tại không (do STOP.bat tạo)"""
        return os.path.exists(self.STOP_FLAG_FILE)

    def _clear_stop_flag(self):
        """Xóa file STOP.flag"""
        try:
            if os.path.exists(self.STOP_FLAG_FILE):
                os.remove(self.STOP_FLAG_FILE)
        except Exception:
            pass

    def _resolve_target_count(self, max_items: int) -> int:
        """0 hoặc số âm nghĩa là crawl không giới hạn đến khi hết trang."""
        if max_items is None or max_items <= 0:
            return sys.maxsize
        return max_items

    def _get_category_map(self, source_key: str) -> Dict[str, str]:
        source = NEWS_SOURCES.get(source_key, {})
        categories = source.get('categories', {})
        if isinstance(categories, dict):
            return {str(key): str(value) for key, value in categories.items()}
        category_map = {}
        base_url = source.get('base_url', '').rstrip('/')
        for category in categories or []:
            category_map[str(category)] = f"{base_url}/{category}"
        return category_map

    def _normalize_category_url(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')

    def _category_slug_from_url(self, base_url: str, category_url: str) -> str:
        parsed = urlparse(category_url)
        path = parsed.path.strip('/')
        if path.endswith('.html'):
            path = path[:-5]
        elif path.endswith('.htm'):
            path = path[:-4]
        if base_url.endswith('/index.html') and path == 'index':
            return ''
        return path

    def _resolve_category_path(self, source_key: str, category: str) -> str:
        category_map = self._get_category_map(source_key)
        category_url = category_map.get(category)
        if category_url:
            return self._category_slug_from_url(NEWS_SOURCES[source_key]['base_url'], category_url)
        return str(category).strip('/').removesuffix('.html').removesuffix('.htm')

    def _resolve_category_url(self, source_key: str, category: str) -> str:
        category_map = self._get_category_map(source_key)
        category_url = category_map.get(category)
        if category_url:
            return self._normalize_category_url(category_url)
        base_url = NEWS_SOURCES[source_key]['base_url'].rstrip('/')
        category_path = self._resolve_category_path(source_key, category)
        return f"{base_url}/{category_path}".rstrip('/')

    def _is_probable_article_url(self, source_key: str, url: str) -> bool:
        cfg = self._SOURCE_LINK_CONFIGS.get(source_key, {})
        parsed = urlparse(url)
        path = parsed.path.lower()
        filename = path.rsplit('/', 1)[-1]
        exclude = cfg.get('exclude', [])
        link_ext = cfg.get('link_ext', ['.html', '.htm'])
        link_re = cfg.get('link_re')

        if any(ex in path for ex in exclude):
            return False
        if link_re and re.search(link_re, path):
            return True
        if link_ext is not None and any(filename.endswith(ext) for ext in link_ext):
            if any(char.isdigit() for char in filename):
                return True
            if filename.count('-') >= 4:
                return True
        return False

    def _discover_category_candidates(self, source_key: str, seed_url: str) -> Dict[str, str]:
        source = NEWS_SOURCES.get(source_key, {})
        base_url = source.get('base_url', '').rstrip('/')
        discovered = {}
        headers = {'User-Agent': self.get_random_user_agent()}
        response = self._safe_request(seed_url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
        if response is None or response.status_code != 200:
            return discovered

        soup = BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')
        blacklist = {
            'lien-he', 'gioi-thieu', 'rss', 'podcast', 'video', 'media', 'longform',
            'infographic', 'multimedia', 'search', 'tim-kiem', 'tag', 'topic', 'chu-de'
        }
        for anchor in soup.find_all('a', href=True):
            href = anchor.get('href', '').strip()
            if not href:
                continue
            absolute_url = urljoin(base_url + '/', href)
            normalized_url = self._normalize_category_url(absolute_url)
            parsed = urlparse(normalized_url)
            if parsed.netloc != urlparse(base_url).netloc:
                continue
            if normalized_url == base_url:
                continue
            slug = self._category_slug_from_url(base_url, normalized_url)
            if not slug:
                continue
            parts = [part for part in slug.split('/') if part]
            if len(parts) > 2:
                continue
            if any(part in blacklist for part in parts):
                continue
            if any(char.isdigit() for char in slug):
                continue
            if self._is_probable_article_url(source_key, normalized_url):
                continue
            discovered[slug] = normalized_url
        return discovered

    def discover_categories(self, source_key: str) -> Dict[str, str]:
        category_map = self._get_category_map(source_key)
        if not AUTO_DISCOVER_CATEGORIES:
            return category_map

        source = NEWS_SOURCES.get(source_key, {})
        base_url = source.get('base_url', '').rstrip('/')
        discovered = dict(category_map)
        static_urls = {
            self._normalize_category_url(category_url): category_slug
            for category_slug, category_url in category_map.items()
        }
        seed_urls = [base_url]
        seed_urls.extend(list(category_map.values())[:DISCOVERY_SEED_LIMIT])

        for seed_url in seed_urls:
            try:
                for slug, category_url in self._discover_category_candidates(source_key, seed_url).items():
                    normalized_url = self._normalize_category_url(category_url)
                    if normalized_url in static_urls:
                        continue
                    discovered.setdefault(slug, category_url)
            except Exception:
                continue

        return discovered

    def _wait_for_domain_slot(self, url: str):
        """Điều phối request theo domain trên toàn bộ process để tránh burst gây block."""
        domain = urlparse(url).netloc.lower()
        if not domain:
            return

        with self._DOMAIN_SCHEDULER_LOCK:
            domain_lock = self._DOMAIN_REQUEST_LOCKS.setdefault(domain, threading.Lock())

        with domain_lock:
            now = time.monotonic()
            next_allowed = self._DOMAIN_NEXT_REQUEST_AT.get(domain, 0.0)
            wait_time = max(0.0, next_allowed - now)
            if wait_time > 0:
                time.sleep(wait_time)

            delay_min, delay_max = self._get_domain_delay(url)
            next_delay = self._get_adaptive_delay(random.uniform(delay_min, delay_max))
            self._DOMAIN_NEXT_REQUEST_AT[domain] = time.monotonic() + next_delay

    def request_stop(self):
        """Yêu cầu dừng cào (gọi từ signal handler, Ctrl+C, hoặc STOP.bat)"""
        with self._stop_lock:
            if not self._stop_requested:
                self._stop_requested = True
                print("\n⚠️  Đã nhận yêu cầu dừng! Đang hoàn thành bài đang cào...")

    @property
    def is_stopped(self) -> bool:
        """Kiểm tra đã yêu cầu dừng chưa (qua flag HOẶC file STOP.flag)"""
        with self._stop_lock:
            if self._stop_requested:
                return True
        # Kiểm tra file flag từ STOP.bat
        if self._check_stop_file():
            self.request_stop()
            return True
        return False
        
    def get_random_user_agent(self) -> str:
        """Lấy ngẫu nhiên một User-Agent"""
        return random.choice(USER_AGENTS)

    # ── Xử lý lỗi mạng: retry tự động ────────────────────────────────────
    _NETWORK_ERRORS = (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.ChunkedEncodingError,
        ConnectionResetError,
        ConnectionAbortedError,
    )

    def _safe_request(self, url: str, retries: int = 3,
                      backoff: float = 2.0, **kwargs) -> Optional[requests.Response]:
        """
        GET request có retry tự động khi bị rớt mạng + adaptive throttling.

        Args:
            url: URL cần request
            retries: Số lần thử lại khi gặp lỗi mạng
            backoff: Hệ số chờ tăng dần giữa các lần retry (giây)
            **kwargs: Truyền thẳng cho session.get()

        Returns:
            Response nếu thành công, None nếu thất bại sau hết lần retry.
        """
        # ── Kiểm tra cache ──
        if ENABLE_RESPONSE_CACHE and url in self._response_cache:
            return self._response_cache[url]
        
        last_err = None
        # Vòng lặp 'Cố gắng đấm ăn xôi', cứu vãn kết nối do lỗi timeout vài lần thay vì báo sập luôn
        for attempt in range(1, retries + 1):
            try:
                # Kỹ thuật Connection Pooling: Gọi requests.Session().get thay vì requests.get để tăng tốc Tái sử dụng cổng tcp
                self._wait_for_domain_slot(url)
                resp = self.session.get(url, **kwargs)
                
                # ── Xử lý 429 (Too Many Requests - Tức là dập dồn dập khiến server chặn BOT) ──
                if resp.status_code == 429:
                    self._handle_429_throttling(resp, url) # Hàm phạt, tự động tăng giãn cách request
                    # Tha cho lần này, retry ngay lập tức
                    if attempt < retries:
                        continue
                
                # ── Cache response ──
                if resp.status_code == 200 and ENABLE_RESPONSE_CACHE:
                    # Thread Lock: Khóa luồng cào hiện tại ngăn đứa khác viết ghi đè biến lúc lưu RAM
                    with self._cache_lock:
                        self._response_cache[url] = resp
                
                self._requests_count += 1
                return resp
                
            except self._NETWORK_ERRORS as e:
                last_err = e
                # Nếu HTTPS bị chặn, thử fallback sang HTTP một lần
                if url.startswith("https://"):
                    http_url = "http://" + url[len("https://"):]
                    try:
                        resp = self.session.get(http_url, **kwargs)
                        self._requests_count += 1
                        return resp
                    except self._NETWORK_ERRORS:
                        last_err = e

                # Cắt rớt mạng/Wifi: Áp dụng Backoff cơ chế -> Lần 1 chờ 2s, lần 2 chờ 4s, dài dần ra
                if attempt < retries:
                    wait = backoff * attempt
                    print(f"  🌐 Lỗi mạng ({type(e).__name__}), thử lại sau {wait:.0f}s… "
                          f"[{attempt}/{retries}]")
                    time.sleep(wait) # Cho luồng này ngủ
                else:
                    print(f"  ❌ Lỗi mạng sau {retries} lần thử: {e}")
        return None

    def _handle_429_throttling(self, response: requests.Response, url: str = ''):
        """
        Xử lý 429 Too Many Requests:
        - Đọc Retry-After nếu có
        - Tăng delay multiplier toàn cục
        - Tạm dừng domain đang bị chặn
        """
        if not ENABLE_ADAPTIVE_THROTTLING:
            return
        
        self._429_count += 1
        
        retry_after = response.headers.get('Retry-After')
        delay_min, _ = self._get_domain_delay(url) if url else (REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
        wait_time = max(20, int(delay_min * 12))
        if retry_after:
            try:
                wait_time = max(wait_time, int(retry_after))
            except ValueError:
                pass
        
        self._current_delay_multiplier = min(10.0, self._current_delay_multiplier * 2.0)
        if url:
            domain = urlparse(url).netloc.lower()
            with self._DOMAIN_SCHEDULER_LOCK:
                current_next = self._DOMAIN_NEXT_REQUEST_AT.get(domain, 0.0)
                self._DOMAIN_NEXT_REQUEST_AT[domain] = max(current_next, time.monotonic() + wait_time)
        
        print(f"  ⚠️  429 Too Many Requests | Delay x{self._current_delay_multiplier:.1f} | "
              f"Chờ {wait_time}s để server khôi phục...")
        time.sleep(min(wait_time, 180))
    
    def _get_domain_delay(self, url: str) -> tuple:
        """
        Lấy delay config cho một domain cụ thể.
        Một số domain (QDND, CAND) rất chặt, cần delay lâu hơn.
        
        Returns:
            (min_delay, max_delay) seconds
        """
        try:
            domain = urlparse(url).netloc  # Lấy domain từ URL, eg: www.qdnd.vn
            # Kiểm tra xem domain có trong danh sách "nhạy cảm" không
            if domain in PER_DOMAIN_DELAYS:
                config = PER_DOMAIN_DELAYS[domain]
                return config['min'], config['max']
        except Exception:
            pass
        return REQUEST_DELAY_MIN, REQUEST_DELAY_MAX

    def _download_article_html(self, url: str, timeout: int = 15) -> Optional[str]:
        headers = dict(self._CHROME_HEADERS)
        headers['User-Agent'] = self.get_random_user_agent()
        needs_bypass = any(
            source_cfg.get('use_js_bypass') and source_data.get('base_url', '') in url
            for source_key, source_cfg in self._SOURCE_LINK_CONFIGS.items()
            for source_data in [NEWS_SOURCES.get(source_key, {})]
        )
        if needs_bypass:
            response = self._request_with_bypass(url, timeout=timeout, headers=headers)
        else:
            response = self._safe_request(url, headers=headers, timeout=timeout, allow_redirects=True)
        if response is None or response.status_code >= 400:
            return None
        response.encoding = response.apparent_encoding or 'utf-8'
        return response.text

    def _format_eta(self, seconds: float) -> str:
        if seconds <= 0:
            return "0:00:00"
        seconds_int = int(seconds)
        h = seconds_int // 3600
        m = (seconds_int % 3600) // 60
        s = seconds_int % 60
        return f"{h}:{m:02d}:{s:02d}"

    def _supports_ansi_output(self) -> bool:
        if not PROGRESS_USE_COLOR:
            return False
        if os.getenv('NO_COLOR'):
            return False
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

    def _human_bytes(self, value: float) -> str:
        units = ['bytes', 'KB', 'MB', 'GB']
        size = float(max(0.0, value))
        idx = 0
        while size >= 1024.0 and idx < len(units) - 1:
            size /= 1024.0
            idx += 1
        if idx == 0:
            return f"{int(size)} {units[idx]}"
        return f"{size:.1f} {units[idx]}"

    def _build_progress_line(self, done: int, total: int, start_ts: float, stats: Dict[str, int]) -> str:
        width = max(20, PROGRESS_BAR_WIDTH)
        pct = (done / total) if total else 0.0
        filled = int(width * pct)
        bar_fill = '█' * filled
        bar_rest = '─' * (width - filled)

        elapsed = max(0.001, time.monotonic() - start_ts)
        remaining = max(0, total - done)

        payload_done = stats.get('payload_bytes', 0)
        avg_payload = (payload_done / done) if done else 0.0
        payload_total_est = int(avg_payload * total) if total else payload_done

        if PROGRESS_RATE_UNIT == 'bytes':
            rate = payload_done / elapsed
            eta = (max(0, payload_total_est - payload_done) / rate) if rate > 0 else 0.0
            progress_txt = f"{self._human_bytes(payload_done)}/{self._human_bytes(payload_total_est)}"
            rate_txt = f"{self._human_bytes(rate)}/s"
        else:
            rate = done / elapsed
            eta = (remaining / rate) if rate > 0 else 0.0
            progress_txt = f"{done}/{total} links"
            rate_txt = f"{rate:.1f} links/s"

        info = (
            f"{progress_txt} "
            f"{rate_txt} "
            f"eta {self._format_eta(eta)} "
            f"ok:{stats['ok']} short:{stats['short']} dup:{stats['dup']} old:{stats['old']} err:{stats['error']}"
        )
        if stats.get('network_error', 0):
            info += f" net:{stats['network_error']}"

        if self._supports_ansi_output():
            bar = (
                f"{self._ANSI_PINK}{bar_fill}{self._ANSI_RESET}"
                f"{self._ANSI_GRAY}{bar_rest}{self._ANSI_RESET}"
            )
            info = (
                info
                .replace('eta ', f"{self._ANSI_CYAN}eta ")
                .replace('ok:', f"{self._ANSI_GREEN}ok:")
                .replace('err:', f"{self._ANSI_RED}err:")
            ) + self._ANSI_RESET
        else:
            bar = bar_fill + bar_rest

        return f"[{bar}] {info}"
    
    def _get_adaptive_delay(self, base_delay: float) -> float:
        """Tính delay với adaptive throttling multiplier"""
        if not ENABLE_ADAPTIVE_THROTTLING:
            return base_delay
        return base_delay * self._current_delay_multiplier

    # ── Bypass JS cookie challenge (Lao Động, …) ──────────────────────────
    def _request_with_bypass(self, url: str, max_retries: int = 3, **kwargs) -> Optional[requests.Response]:
        """
        Hàm Cao Cấp: Qua mặt hệ thống chống Bot (Anti-Bot Bypass) bằng cơ chế bắt Cookie.
        
        Giải thích vấn đề: Một số báo (như Lao Động) dùng tường lửa (kiểu Cloudflare). 
        Khi tool Request lần đầu, nó không trả về bài báo (HTML), mà trả về 1 đoạn mã Javascript ngầm
        bắt tạo một biến Cookie rồi Reload lại trang -> Để lọc tụi code cào dữ liệu dỏm (vì thư viện Python ko chạy đc JS).
        
        Cách giải quyết của tool: Bắt cái response JS đó, dùng Biểu thức chính quy (Regex) quét tìm đoạn mã định dạng document.cookie,
        thu lại Tên Cookie và Giá trị của nó -> Tự nhét vào Bộ nhớ Session của Tool -> Gửi lại Request lần 2. Tường lửa tin là người thật -> Trả text!
        """
        # Băm các thuộc tính Header "đóng giả" trình duyệt Google Chrome xịn 100% để tường lửa không nghi ngờ
        headers = dict(self._CHROME_HEADERS)
        headers['User-Agent'] = self.get_random_user_agent()
        headers.update(kwargs.pop('headers', {}))

        domain = urlparse(url).netloc # Cắt lấy tên miền, ví dụ: laodong.vn

        for attempt in range(max_retries):
            # Cố xin dữ liệu (có cho phép allow_redirects vì web hay tự động chuyển hướng link)
            resp = self._safe_request(url, retries=2, headers=headers,
                                      timeout=kwargs.get('timeout', 20),
                                      allow_redirects=True)
            if resp is None:
                return None  # Lỗi mạng thực sự, tắt

            # Bắt giữ JS challenge: Thường HTML trả về mà dung lượng bé tí xíu (<500 bytes), chắc chắn 100% là màn hình chờ (challenge JS)
            if len(resp.content) < 500:
                # Quét Regex dạng: document.cookie="TENCK=GiatriXYZ"
                match = re.search(r'document\.cookie\s*=\s*"(\w+)=([^"]+)"', resp.text)
                if match:
                    cname, cval = match.group(1), match.group(2)
                    
                    # Tool phải xóa cookie rác cũ (nếu có) để nhét vào cookie xịn vừa lấy được
                    try:
                        self.session.cookies.clear(domain=domain, path='/', name=cname)
                    except KeyError:
                        pass
                    
                    # Ép trực tiếp Cookie này vào session hiện tại. Vượt rào thành công!
                    self.session.cookies.set(cname, cval, domain=domain, path='/')
                    self._js_bypass_done[domain] = cname # Ghi vào sổ tay là tao đã có bằng lái ở domain này, các luồng khác cứ thế đi
                    print(f"  🔑 Cú Lừa Thành Công - Cookie bypass ({domain}): {cname}={cval[:16]}…")
                    time.sleep(0.5)
                    continue  # Lặp lại vòng lặp để Request lại URL cũ (lúc này đã có Cookie thông hành)

            # Nếu dung lượng > 500 bytes thì có file đọc được rồi, Response thật, báo về luồng chính.
            return resp

        # Rớt vòng lặp thử đi thử lại mà vẫn tắc -> cứ trả về resp cuối.
        return resp

    def clean_text(self, text: str) -> str:
        """
        Siêu công cụ Cắt tỉa (Data Cleaning) làm sạch văn bản dùng cho AI Model.
        Giải thích logic: Máy đọc không hiểu các thể loại kí tự như &nbsp; (Khoảng trắng html)
        và model AI rất chê các dạng câu chữ "Quảng cáo mua A B C" hay "Mời bạn đọc".
        """
        if not text:
            return ''

        # BƯỚC 1: Phiên dịch ngược kí tự HTML. Vd: "&amp;" sẽ tự dộng dịch thành dấu "&"
        text = html.unescape(text)

        # BƯỚC 2: Loại bỏ triệt để các byte rác vô hình (control characters) hay chen giữa bài lúc tải, để chừa lại \n và \t.
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

        # BƯỚC 3: Máy chém rác (Noise Filtering)
        lines = text.splitlines() # Chém văn bản ra từng dòng một
        clean_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Đem dòng đó đọ với danh sách Regex (Khai báo mảng _NOISE_PATTERNS ở đầu class)
            is_noise = False
            for pattern in self._NOISE_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    is_noise = True # Nếu chứa "Copyright", "hotline:..." thì vứt luôn dòng này.
                    break
            
            # Chỉ giữ lại văn bản chính tông
            if not is_noise:
                clean_lines.append(line)

        # Trộn mảng trở lại thành 1 văn bản xuyên suốt
        text = '\n'.join(clean_lines)

        # BƯỚC 4: Normalize (Chuẩn hóa) lại khoảng trắng. 
        # Cứ thấy 2,3 dấu cách hoặc TAB liên tiếp dính nhau thì ép lại thành đúng 1 dấu cách.
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Cứ thấy hố rỗng enter 3 4 dòng 1 lúc thì ép lại tối đa là 2 dòng để bài dễ đọc ko bị ngợp mắt
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def get_content_hash(self, text: str) -> str:
        """Tính hash MD5 của nội dung để dedup"""
        # Chuẩn hóa trước khi hash: lowercase, bỏ whitespace thừa
        normalized = re.sub(r'\s+', ' ', text.lower().strip())
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()

    def is_article_too_old(self, publish_date) -> bool:
        """Kiểm tra bài có quá cũ không (vượt quá max_article_age_days)"""
        if publish_date is None:
            return False  # Không có ngày → giữ lại
        try:
            if hasattr(publish_date, 'tzinfo') and publish_date.tzinfo is not None:
                from datetime import timezone
                now = datetime.now(timezone.utc)
            else:
                now = datetime.now()
            age = (now - publish_date).days
            return age > self.max_article_age_days
        except Exception:
            return False
    
    def get_thanhnien_links(self, category: str, max_links: int = 100) -> List[str]:
        """
        Phương thức riêng cho Thanh Niên - lọc chặt chẽ hơn
        
        Args:
            category: Chuyên mục
            max_links: Số lượng link tối đa
        
        Returns:
            Danh sách URL bài viết
        """
        base_url = 'https://thanhnien.vn'
        links = []  
        seen_urls = set()
        page = 1
        consecutive_empty = 0
        target_links = self._resolve_target_count(max_links)
        category_path = self._resolve_category_path('thanhnien', category)
        category_root_url = self._resolve_category_url('thanhnien', category)
        
        # Danh sách các trang rác cần loại bỏ
        blacklist = [
            '/video.htm', '/magazine.htm', '/chao-ngay-moi.htm',
            '/tin-24h.htm', '/tin-nhanh-360.htm', '/ban-can-biet.htm',
            '/thi-truong.htm', '/tien-ich/', '/thong-tin-toa-soan.html',
            '/lien-he.htm', '/chinh-tri.htm', '/kinh-te.htm', '/the-gioi.htm',
            '/doi-song.htm', '/gioi-tre.htm', '/suc-khoe.htm', '/van-hoa.htm',
            '/giai-tri.htm', '/du-lich.htm', '/cong-nghe.htm', '/the-thao.htm',
            '/giao-duc.htm', '/xe.htm', '/tieu-dung-thong-minh.htm'
        ]
        
        while len(links) < target_links:
            if page == 1:
                category_url = category_root_url
            else:
                category_url = f"{base_url}/{category_path}-p{page}"
            
            headers = {'User-Agent': self.get_random_user_agent()}
            
            try:
                if page > 1:
                    print(f"📄 Trang {page}: {category_url}")
                else:
                    print(f"📡 Đang lấy danh sách bài từ: {category_url}")
                
                response = self._safe_request(category_url, headers=headers, timeout=15)
                if response is None:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        break
                    page += 1
                    continue
                
                if response.status_code == 404:
                    break
                
                response.raise_for_status()
                response.encoding = response.apparent_encoding or 'utf-8'
                soup = BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')
                
                page_links = []
                for link in soup.find_all('a', href=True):
                    url = link['href']
                    
                    # Chuẩn hóa URL
                    if url.startswith('/'):
                        url = base_url + url
                    elif not url.startswith('http'):
                        continue
                    
                    # Chỉ lấy link .htm từ thanhnien.vn
                    if (base_url in url and 
                        '.htm' in url and
                        url != category_url and
                        url != base_url):
                        
                        # Loại bỏ các link trong blacklist
                        if any(black in url for black in blacklist):
                            continue
                        
                        # Loại bỏ link có /category/subcategory.htm (category page)
                        # Chỉ chấp nhận link có ID số hoặc tiêu đề dài (bài viết thật)
                        url_path = url.replace(base_url, '').replace('.htm', '')
                        parts = url_path.strip('/').split('/')
                        
                        # Bài viết thật thường có format: /category/title-123.htm hoặc /long-title.htm
                        # Category page: /category.htm hoặc /category/subcategory.htm
                        is_article = (
                            len(parts) == 1 and len(parts[0].split('-')) >= 4 or  # /tieu-de-dai-nay.htm
                            len(parts) >= 2 and any(char.isdigit() for char in parts[-1])  # /category/title-123.htm
                        )
                        
                        if is_article:
                            url = url.split('#')[0]
                            if url not in seen_urls:
                                seen_urls.add(url)
                                page_links.append(url)
                                links.append(url)
                                
                                if len(links) >= target_links:
                                    break
                
                if len(page_links) == 0:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        break
                else:
                    consecutive_empty = 0
                
                print(f"  ✓ Trang {page}: +{len(page_links)} bài (tổng: {len(links)})")
                page += 1
                
            except Exception as e:
                print(f"❌ Lỗi trang {page}: {e}")
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    break
        
        print(f"✅ Tổng cộng: {len(links)} bài từ Thanh Niên/{category}")
        return links if target_links == sys.maxsize else links[:target_links]
    
    def get_tuoitre_links(self, category: str, max_links: int = 100) -> List[str]:
        """Phương thức riêng cho Tuổi Trẻ"""
        base_url = 'https://tuoitre.vn'
        links = []
        seen_urls = set()
        page = 1
        consecutive_empty = 0
        target_links = self._resolve_target_count(max_links)
        category_path = self._resolve_category_path('tuoitre', category)
        
        while len(links) < target_links:
            if page == 1:
                category_url = self._resolve_category_url('tuoitre', category)
            else:
                category_url = f"{base_url}/{category_path}-p{page}.htm"
            
            headers = {'User-Agent': self.get_random_user_agent()}
            
            try:
                if page > 1:
                    print(f"📄 Trang {page}: {category_url}")
                else:
                    print(f"📡 Đang lấy danh sách bài từ: {category_url}")
                
                response = self._safe_request(category_url, headers=headers, timeout=15)
                if response is None:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        break
                    page += 1
                    continue
                if response.status_code == 404:
                    break
                response.raise_for_status()
                response.encoding = response.apparent_encoding or 'utf-8'
                
                soup = BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')
                page_links = []
                
                for link in soup.find_all('a', href=True):
                    url = link['href']
                    if url.startswith('/'):
                        url = base_url + url
                    elif not url.startswith('http'):
                        continue
                    
                    # Tuổi Trẻ: link bài viết có ID số dạng /abc-xyz-123456.htm
                    if (base_url in url and '.htm' in url and
                        url != category_url and
                        any(char.isdigit() for char in url.split('/')[-1])):
                        
                        url = url.split('#')[0]
                        if url not in seen_urls:
                            seen_urls.add(url)
                            page_links.append(url)
                            links.append(url)
                            if len(links) >= target_links:
                                break
                
                if len(page_links) == 0:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        break
                else:
                    consecutive_empty = 0
                
                print(f"  ✓ Trang {page}: +{len(page_links)} bài (tổng: {len(links)})")
                page += 1
                
            except Exception as e:
                print(f"❌ Lỗi trang {page}: {e}")
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    break
        
        print(f"✅ Tổng cộng: {len(links)} bài từ Tuổi Trẻ/{category}")
        return links if target_links == sys.maxsize else links[:target_links]
    
    def get_vietnamnet_links(self, category: str, max_links: int = 100) -> List[str]:
        """Phương thức riêng cho VietnamNet"""
        base_url = 'https://vietnamnet.vn'
        links = []
        seen_urls = set()
        page = 1
        consecutive_empty = 0
        target_links = self._resolve_target_count(max_links)
        category_path = self._resolve_category_path('vietnamnet', category)
        
        while len(links) < target_links:
            if page == 1:
                category_url = self._resolve_category_url('vietnamnet', category)
            else:
                category_url = f"{base_url}/{category_path}?page={page}"
            
            headers = {'User-Agent': self.get_random_user_agent()}
            
            try:
                if page > 1:
                    print(f"📄 Trang {page}: {category_url}")
                else:
                    print(f"📡 Đang lấy danh sách bài từ: {category_url}")
                
                response = self._safe_request(category_url, headers=headers, timeout=15)
                if response is None:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        break
                    page += 1
                    continue
                if response.status_code == 404:
                    break
                response.raise_for_status()
                response.encoding = response.apparent_encoding or 'utf-8'
                
                soup = BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')
                page_links = []
                
                for link in soup.find_all('a', href=True):
                    url = link['href']
                    if url.startswith('/'):
                        url = base_url + url
                    elif not url.startswith('http'):
                        continue
                    
                    # VietnamNet: link có .html và ID số (không cần chứa tên category)
                    if (base_url in url and '.html' in url and
                        url != category_url and
                        '/tag/' not in url and '/topic/' not in url and
                        any(char.isdigit() for char in url)):
                        
                        url = url.split('#')[0]
                        if url not in seen_urls:
                            seen_urls.add(url)
                            page_links.append(url)
                            links.append(url)
                            if len(links) >= target_links:
                                break
                
                if len(page_links) == 0:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        break
                else:
                    consecutive_empty = 0
                
                print(f"  ✓ Trang {page}: +{len(page_links)} bài (tổng: {len(links)})")
                page += 1
                
            except Exception as e:
                print(f"❌ Lỗi trang {page}: {e}")
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    break
        
        print(f"✅ Tổng cộng: {len(links)} bài từ VietnamNet/{category}")
        return links if target_links == sys.maxsize else links[:target_links]
    
    def get_dantri_links(self, category: str, max_links: int = 100) -> List[str]:
        """Phương thức riêng cho Dân Trí"""
        base_url = 'https://dantri.com.vn'
        links = []
        seen_urls = set()
        page = 1
        consecutive_empty = 0
        target_links = self._resolve_target_count(max_links)
        category_path = self._resolve_category_path('dantri', category)

        while len(links) < target_links:
            # Page 1: /category.htm  |  Page N: /category/trang-N.htm
            if page == 1:
                category_url = self._resolve_category_url('dantri', category)
            else:
                category_url = f"{base_url}/{category_path}/trang-{page}.htm"

            headers = {'User-Agent': self.get_random_user_agent()}

            try:
                if page > 1:
                    print(f"📄 Trang {page}: {category_url}")
                else:
                    print(f"📡 Đang lấy danh sách bài từ: {category_url}")

                response = self._safe_request(category_url, headers=headers, timeout=15)
                if response is None:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        break
                    page += 1
                    continue
                if response.status_code == 404:
                    break
                response.raise_for_status()
                response.encoding = response.apparent_encoding or 'utf-8'

                soup = BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')
                page_links = []

                for link_tag in soup.find_all('a', href=True):
                    url = link_tag['href']
                    if url.startswith('/'):
                        url = base_url + url
                    elif not url.startswith('http'):
                        continue

                    # Dân Trí: bài viết có timestamp dạng -20YYMMDDHHMMSS.htm
                    if (base_url in url and '.htm' in url and
                        url != category_url and
                        '/event/' not in url and
                        '/tag/' not in url and
                        '/media/' not in url and
                        f'/{category_path}.htm' not in url and
                        any(char.isdigit() for char in url.split('/')[-1])):

                        url = url.split('#')[0]
                        if url not in seen_urls:
                            seen_urls.add(url)
                            page_links.append(url)
                            links.append(url)
                            if len(links) >= target_links:
                                break

                if len(page_links) == 0:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        break
                else:
                    consecutive_empty = 0

                print(f"  ✓ Trang {page}: +{len(page_links)} bài (tổng: {len(links)})")
                page += 1

            except Exception as e:
                print(f"❌ Lỗi trang {page}: {e}")
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    break

        print(f"✅ Tổng cộng: {len(links)} bài từ Dân Trí/{category}")
        return links if target_links == sys.maxsize else links[:target_links]
    
    def get_vneconomy_links(self, category: str, max_links: int = 100) -> List[str]:
        """Phương thức riêng cho VnEconomy (đuôi .htm, phân trang ?page=N)"""
        base_url = 'https://vneconomy.vn'
        links = []
        seen_urls = set()
        page = 1
        consecutive_empty = 0
        target_links = self._resolve_target_count(max_links)
        category_path = self._resolve_category_path('vneconomy', category)

        while len(links) < target_links:
            if page == 1:
                category_url = self._resolve_category_url('vneconomy', category)
            else:
                category_url = f"{base_url}/{category_path}.htm?page={page}"

            headers = {'User-Agent': self.get_random_user_agent()}
            try:
                if page > 1:
                    print(f"📄 Trang {page}: {category_url}")
                else:
                    print(f"📡 Đang lấy danh sách bài từ: {category_url}")

                response = self._safe_request(category_url, headers=headers, timeout=15)
                if response is None:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        break
                    page += 1
                    continue
                if response.status_code == 404:
                    break
                response.raise_for_status()
                response.encoding = response.apparent_encoding or 'utf-8'

                soup = BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')
                page_links = []

                for link in soup.find_all('a', href=True):
                    url = link['href']
                    if url.startswith('/'):
                        url = base_url + url
                    elif not url.startswith('http'):
                        continue

                    # VnEconomy: link bài viết kết thúc .htm, có tiêu đề dài
                    # Loại bỏ các URL là trang chuyên mục (vd: /chung-khoan.htm)
                    slug = url.replace(base_url + '/', '').replace('.htm', '')
                    all_cats = NEWS_SOURCES.get('vneconomy', {}).get('categories', [])
                    if (base_url in url and url.endswith('.htm') and
                        url != category_url and
                        slug not in all_cats and
                        f'/{category_path}' not in url.replace(base_url, '') and
                        '/tag/' not in url and '/chu-de/' not in url and
                        '/event' not in url and '/video' not in url and
                        len(url.split('/')[-1]) > 10):

                        url = url.split('#')[0]
                        if url not in seen_urls:
                            seen_urls.add(url)
                            page_links.append(url)
                            links.append(url)
                            if len(links) >= target_links:
                                break

                if len(page_links) == 0:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        break
                else:
                    consecutive_empty = 0

                print(f"  ✓ Trang {page}: +{len(page_links)} bài (tổng: {len(links)})")
                page += 1

            except Exception as e:
                print(f"❌ Lỗi trang {page}: {e}")
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    break

        print(f"✅ Tổng cộng: {len(links)} bài từ VnEconomy/{category}")
        return links if target_links == sys.maxsize else links[:target_links]

    def get_article_links(self, source_key: str, category: str, max_links: int = 100) -> List[str]:
        """
        Hàm Phân trang và Quét URL bài viết (Dùng BeautifulSoup)
        Quy trình: Đi vào URL Chuyên mục (thể thao) -> Load Page 1, Page 2 -> Móc thẻ <a> -> Phân tích đuôi -> Thu về mảng Link.
        """
        if source_key not in NEWS_SOURCES:
            print(f"⚠️  Nguồn '{source_key}' không tồn tại trong config")
            return []
        
        # Nhóm "Báo Đặc Biệt": Layout html của tụi này lắt léo quái đản, em tách ra hàm quét riêng
        if source_key == 'thanhnien':
            return self.get_thanhnien_links(category, max_links)
        elif source_key == 'tuoitre':
            return self.get_tuoitre_links(category, max_links)
        elif source_key == 'vietnamnet':
            return self.get_vietnamnet_links(category, max_links)
        elif source_key == 'dantri':
            return self.get_dantri_links(category, max_links)
        elif source_key == 'vneconomy':
            return self.get_vneconomy_links(category, max_links)
        
        # --- BẮT ĐẦU BLOCK DÀNH CHO CÁC BÁO CHUNG ----
        source = NEWS_SOURCES[source_key]
        base_url = source['base_url']
        # Đọc bộ Quy Tắc ở biến chung. Vd: báo VnExpress (nhóm A) link bắt buộc đuôi là .html
        cfg = self._SOURCE_LINK_CONFIGS.get(source_key, {})

        # Nguồn có JS cookie challenge (Bức tường chắn ddos) → Phải đem Cookie Bypass qua thì mới gọi được
        use_bypass = cfg.get('use_js_bypass', False)

        # Lấy chuẩn Format ráp link truyền trang (Vd vnexpress.net/thẻ-thao-p{page})
        cat_url_fmt  = cfg.get('cat_url',  '{base}/{cat}')
        page_url_fmt = cfg.get('page_url', '{base}/{cat}-p{page}')
        category_path = self._resolve_category_path(source_key, category)
        resolved_category_url = self._resolve_category_url(source_key, category)
        
        # Mảng đuôi hợp lệ (phòng hờ mút nhầm link ảnh .jpeg hay video .mp4)
        link_ext     = cfg.get('link_ext', ['.html', '.htm'])
        link_re      = cfg.get('link_re')
        exclude      = cfg.get('exclude',  ['/tag/', '/topic/', '/search/'])
        target_links = self._resolve_target_count(max_links)

        links = []           # Túi đựng link đã hái
        seen_urls = set()    # Bộ nhớ tạm (cache) để check URL này tao quét qua chưa
        page = 1             # Biến lật trang (như lật sách)
        consecutive_empty = 0 # Bộ đếm, lật 3 trang liên tiếp mà trống trơn thì nghỉ khỏe (end danh sách)

        while len(links) < target_links:
            # Tạo URL phân trang theo format (Dùng định dạng chuỗi động .format)
            if page == 1:
                category_url = resolved_category_url
            else:
                category_url = page_url_fmt.format(base=base_url, cat=category_path, page=page)

            # Phù phép Header IP mạo danh, có luôn DNT (Do Not Track) cho chân thật
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }

            try:
                # Ghi đè một dòng progress thay vì spam nhiều dòng
                msg = f"📄 Trang {page} | Đã gom: {len(links)} link"
                sys.stdout.write('\r' + msg)
                sys.stdout.flush()

                # Dùng bypass cho nguồn có JS cookie challenge
                if use_bypass:
                    response = self._request_with_bypass(category_url)
                else:
                    # Gửi POST lấy mã HTML trang Chuyên mục (thử tối đa 15s)
                    response = self._safe_request(
                        category_url, headers=headers, timeout=15, allow_redirects=True)

                if response is None:
                    print(f"  ❌ Không thể kết nối trang {page}")
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        break # Trạm mạng chết, stop để đi báo khác
                    page += 1
                    continue

                if response.status_code == 404: # Quét lố trang (Vd web chỉ có 10 trang, quét tới trang 11 báo NOT FOUND)
                    break
                    
                response.raise_for_status()
                response.encoding = response.apparent_encoding or 'utf-8' # Ép font chữ tiếng Việt ko bị lỗi

                # Bắt bớ Redirect (Vd vào zing.vn nó tự nhảy mẹ qua znews.com) -> Cập nhật lại Base URL
                parsed_resp = urlparse(response.url)
                actual_base = f"{parsed_resp.scheme}://{parsed_resp.netloc}"

                # Thả BeautifulSoup vào nhai nuốt HTML, build lên cây thư mục DOM
                soup = BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')

                page_links = []
                
                # Quét mọi thẻ mỏ neo <a> có chưa href (địa chỉ)
                for a_tag in soup.find_all('a', href=True):
                    url = a_tag['href']

                    # Tiêu chuẩn hóa: Báo việt nam hay bỏ chữ base đi ở link phụ ( href="/tin-nong.html" ) -> Phải Cộng lại
                    if url.startswith('/'):
                        url = actual_base + url
                    elif not url.startswith('http'):
                        continue

                    # Kháng việc bốc nhầm link ngoài mảng (Link nhảy fb/youtube các kiểu)
                    if base_url not in url and actual_base not in url:
                        continue

                    # Xé thẻ Query param `?page=1` & Anchor tag `#comment` đi
                    url_clean = url.split('?')[0].split('#')[0].rstrip('/')

                    # Vứt link vòng lặp (Url này lại là của cái category đang kiếm)
                    cat_clean = category_url.split('?')[0].split('#')[0].rstrip('/')
                    if url_clean == cat_clean or url_clean == base_url or url_clean == actual_base:
                        continue

                    # Rule Xóa Bẩn (exclude): Nếu Url chứa các thư mục '/video', 'tag' thì Vứt luon ko ngoái đầu
                    if any(ex in url for ex in exclude):
                        continue

                    # Kiểm tra đuôi file chuyên biệt (Nhóm A bắt buộc đuôi file sinh ra HTML)
                    if link_ext is not None:
                        if not any(url_clean.endswith(ext) for ext in link_ext):
                            continue

                    # Check Regex mẫu bài báo: (Nhóm ko có HTML ví dụ đuôi dạng /id-45812) thì phải kiểm tra xem chứa mã sô ID bài ko
                    if link_re:
                        if not re.search(link_re, url_clean):
                            continue
                    else:
                        # Mặc định: cắt phần cuối URL, nến xui xẻo không chứa ký tự SỐ nào thì đó chắc cú là link "Giới thiệu, menu..." chứ đek phải báo.
                        last_seg = url_clean.split('/')[-1]
                        if not any(c.isdigit() for c in last_seg):
                            continue

                    # Cuối cùng, nếu check đủ các môn phái mà URL này chưa từng quét (Túi set)
                    if url_clean not in seen_urls:
                        seen_urls.add(url_clean)      # Lưu tạm ổ cứng
                        page_links.append(url_clean)  # Cất đếm theo trang này lấy đc bao bài
                        links.append(url_clean)       # Thảy vào cái Thúng lớn để trả về 
                        
                        # Ầu, giỏ đầy rồi. Phá For loop đóng máy đi về!
                        if len(links) >= target_links:
                            break

                # Trang này quá rách không mọc được nổi 1 bài mới (thường là qua trang lố index hoặc dính quảng cáo che tịt)
                if len(page_links) == 0:
                    consecutive_empty += 1
                    # Quá tam ba bận, 3 trang trống => Website hết bài rồi, không lật trang nữa!
                    if consecutive_empty >= 3:
                        break
                else: # Có bài, đếm tiếp
                    consecutive_empty = 0

                # Cập nhật progress bar với số link mới
                msg = f"📄 Trang {page} | +{len(page_links)} link | Tổng: {len(links)}"
                sys.stdout.write('\r' + msg)
                sys.stdout.flush()
                page += 1 # Sang trang sách tiếp theo!

                # Không thì chờ ngẫu nhiên 0.2 - 0.5s cho chân thật rải rải request
            except Exception as e:
                print(f"❌ Lỗi trang {page}: {e}")
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    break

        # Xuống dòng sau progress bar
        sys.stdout.write('\n')
        sys.stdout.flush()
        print(f"✅ Tổng cộng thu hoạch: {len(links)} bài từ source: {source['name']} - mục: {category}")
        return links if target_links == sys.maxsize else links[:target_links]

    def extract_article(self, url: str, source_name: str = '', category: str = '') -> tuple:
        """
        Trích xuất nội dung bài viết sử dụng newspaper3k
        
        Args:
            url: URL của bài viết
            source_name: Tên nguồn báo
            category: Chuyên mục
        
        Returns:
            Dictionary chứa thông tin bài viết hoặc None nếu thất bại
        """
        try:
            # Tạo Article object với cấu hình
            article = Article(url, language='vi')
            
            # Set User-Agent
            article.config.browser_user_agent = self.get_random_user_agent()
            article.config.request_timeout = 15
            article.config.number_threads = 1
            article.config.memoize_articles = False
            
            html_text = self._download_article_html(url, timeout=article.config.request_timeout)
            if not html_text:
                return ('network_error', None)

            article.download(input_html=html_text)
            article.parse()

            # BƯỚC LỌC 1: Lọc bỏ bài báo quá cũ (vượt quá thời gian date config, mặc định 2 năm)
            if self.is_article_too_old(article.publish_date):
                return ('old', None)

            # Trích xuất dữ liệu gốc ban đầu do html trả về
            title = article.title.strip() if article.title else ''
            raw_text = article.text or ''

            # BƯỚC LỌC 2: Đưa qua bộ filter regex để cắt bỏ mấy cụm từ tào lao (Click quảng cáo e đi anh v.v)
            title = self.clean_text(title)
            text = self.clean_text(raw_text)

            # BƯỚC LỌC 3: Loại bỏ các bài ảo (toàn ảnh là ảnh or video hỏng ko có Text). Đo khoảng trắng nhỏ hơn 100 từ!
            word_count = len(text.split())
            if word_count < 100:
                return ('short', None)

            # BƯỚC LỌC 4: Chống Trùng (Deduplication). Trộn tựa & Thân bài, băm ra 1 mã Vân tay MD5
            combined_text = f"{title}. {text}" if title else text
            content_hash = self.get_content_hash(combined_text)
            
            # Nếu Vân Tay này đã có sẵn bộ nhớ (set) thì từ chối tiếp nhận vì bài này báo Đã Đăng ở mục khác rồi.
            if content_hash in self.content_hashes:
                return ('dup', None)
            self.content_hashes.add(content_hash)

            # Trích xuất thêm các trường phụ từ newspaper3k (summary, date, authors, tags)
            summary = self.clean_text(article.meta_description or '') if article.meta_description else ''
            publish_date = ''
            if article.publish_date:
                try:
                    publish_date = article.publish_date.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    publish_date = str(article.publish_date)
            authors = '; '.join(article.authors) if article.authors else ''
            tags = '; '.join(sorted(article.tags)) if article.tags else ''
            if not tags and article.meta_keywords:
                tags = '; '.join(article.meta_keywords) if isinstance(article.meta_keywords, list) else str(article.meta_keywords)

            # Đóng gói sản phẩm gửi về kho, bài qua 4 vòng lọc này siêu xịn
            data = {
                'chu_de': category,
                'tieu_de': title,
                'tom_tat': summary,
                'noi_dung': text,
                'ngay': publish_date,
                'tac_gia': authors,
                'nguon': source_name,
                'link': url,
                'tags': tags,
            }
            return ('ok', data)

        except self._NETWORK_ERRORS as e:
            # Lỗi mạng → retry 1 lần
            try:
                time.sleep(2)
                article2 = Article(url, language='vi')
                article2.config.browser_user_agent = self.get_random_user_agent()
                article2.config.request_timeout = 20
                html_text = self._download_article_html(url, timeout=article2.config.request_timeout)
                if not html_text:
                    return ('network_error', None)
                article2.download(input_html=html_text)
                article2.parse()
                title = self.clean_text(article2.title.strip() if article2.title else '')
                text = self.clean_text(article2.text or '')
                if len(text.split()) < 100:
                    return ('short', None)
                combined_text = f"{title}. {text}" if title else text
                content_hash = self.get_content_hash(combined_text)
                if content_hash in self.content_hashes:
                    return ('dup', None)
                self.content_hashes.add(content_hash)
                summary2 = self.clean_text(article2.meta_description or '') if article2.meta_description else ''
                pub_date2 = ''
                if article2.publish_date:
                    try:
                        pub_date2 = article2.publish_date.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        pub_date2 = str(article2.publish_date)
                authors2 = '; '.join(article2.authors) if article2.authors else ''
                tags2 = '; '.join(sorted(article2.tags)) if article2.tags else ''
                return ('ok', {
                    'chu_de': category, 'tieu_de': title, 'tom_tat': summary2,
                    'noi_dung': text, 'ngay': pub_date2, 'tac_gia': authors2,
                    'nguon': source_name, 'link': url, 'tags': tags2,
                })
            except Exception:
                return ('network_error', None)

        except Exception as e:
            return ('error', None)
    
    def crawl_category(self, source_key: str, category: str, max_articles: int = 100, delay: float = 1.0) -> List[Dict]:
        """
        Cào tất cả bài viết từ một chuyên mục (ĐA LUỒNG).
        Hỗ trợ dừng giữa chừng: nếu _stop_requested == True, dừng sớm và trả về
        những bài đã cào xong (không bao gồm bài đang cào dở).
        """
        source = NEWS_SOURCES.get(source_key)
        if not source:
            return []

        # Kiểm tra dừng trước khi bắt đầu
        if self.is_stopped:
            return []
        
        # Lấy danh sách link
        links = self.get_article_links(source_key, category, max_articles)
        
        articles = []
        total = len(links)
        if total == 0:
            return []

        print(f"🚀 Bắt đầu cào {total} link với {MAX_WORKERS} luồng...")

        counter = {
            'ok': 0, 'short': 0, 'dup': 0, 'old': 0,
            'error': 0, 'network_error': 0, 'done': 0,
            'payload_bytes': 0
        }
        lock = threading.Lock()
        start_ts = time.monotonic()

        # (Công việc luồng con): Định nghĩa vòng đời xử lý nội dung 1 url duy nhất 
        def crawl_one(url_info):
            idx, url = url_info
            
            # Trước khi tải trang, nghía xem Cờ Stop bên ngoài (User bấm Ctrl+C k) có bật ko.
            if self.is_stopped:
                return None
            
            if self.is_stopped:
                return None
                
            # Đâm thủng vào trích text website
            status, article_data = self.extract_article(url, source['name'], category)
            
            # Cơ chế Khóa (Lock): Do biến `counter` là Tài sản chung (Share State), nếu 2 Thread cùng cộng 1 lúc sẽ gây mất dữ liệu (Race Condition). Phải khóa trước cộng sau.
            with lock:
                counter['done'] += 1
                counter[status] += 1
                if status == 'ok' and article_data:
                    counter['payload_bytes'] += len((article_data.get('noi_dung') or '').encode('utf-8', errors='ignore'))
                done = counter['done']
                # In thanh tiến trình một dòng (ghi đè) theo kiểu bar + tốc độ + ETA
                bar = self._build_progress_line(done, total, start_ts, counter)
                if self.is_stopped:
                    bar += " [ĐANG DỪNG...]"
                sys.stdout.write('\r' + bar[:220])
                sys.stdout.flush()
            return article_data
        
        # Mở Bể Cạn Đa Luồng (ví dụ max=4 tức là thuê 4 Công nhân đi cào cùng lúc thay vì đợi lần lượt)
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Phát công việc ra cho các thợ nhặt
            futures = {executor.submit(crawl_one, (i, url)): url for i, url in enumerate(links, 1)}
            
            # Đợi thợ làm xong, thằng nào xong rảnh tay nộp bài trước ko cần theo thứ tự
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        articles.append(result)
                except Exception:
                    pass
                
                # Nếu Nhận Lệnh báo Dừng Cấp Tốc -> Lật đổ mâm giải tán hết những Luồng (Futures) chưa xử lý
                if self.is_stopped:
                    for f in futures:
                        f.cancel()
                    break
            
            # Xuống dòng sau khi hoàn thành progress bar để tránh đè log tiếp theo
            sys.stdout.write('\n')
            sys.stdout.flush()
        
        status_msg = "🛑 Đã dừng" if self.is_stopped else "🏁 Xong"
        print(f"{status_msg}: {len(articles)}/{total} bài hợp lệ")
        return articles
    
    # ── Lưu checkpoint giữa chừng (chỉ JSON) ──────────────────────────────
    def save_checkpoint(self, articles: List[Dict], source_key: str,
                        completed_categories: List[str],
                        data_dir: str = 'data'):
        """
        Lưu checkpoint JSON và tiến độ để có thể resume.
        Mỗi nguồn báo chỉ lưu 1 file checkpoint duy nhất (ghi đè).

        Args:
            articles: Danh sách bài đã cào
            source_key: Key nguồn báo
            completed_categories: Các chuyên mục đã xong
            data_dir: Thư mục lưu
        """
        os.makedirs(data_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Lọc bài hợp lệ (loại None / thiếu trường)
        valid = [a for a in articles if a and isinstance(a, dict)
                 and a.get('noi_dung') and a.get('tieu_de')]

        if not valid:
            print("  ⚠️  Không có bài hợp lệ để lưu checkpoint")
            return

        # ── Lưu JSON (1 file duy nhất / nguồn, ghi đè) ──
        json_path = os.path.join(data_dir, f'checkpoint_{source_key}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(valid, f, ensure_ascii=False, indent=2)

        print(f"  💾 Checkpoint: {len(valid)} bài → {json_path}")

        # ── Lưu tiến độ (danh sách chuyên mục đã xong) ──
        progress_path = os.path.join(data_dir, 'progress.json')
        progress = {}
        if os.path.exists(progress_path):
            try:
                with open(progress_path, 'r', encoding='utf-8') as f:
                    progress = json.load(f)
            except Exception:
                pass
        progress[source_key] = {
            'completed_categories': completed_categories,
            'total_articles': len(valid),
            'last_update': timestamp,
        }
        with open(progress_path, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

    # ── Lưu file dữ liệu tổng (JSON + CSV) ────────────────────────────────
    def save_aggregate(self, articles: List[Dict], data_dir: str = 'data'):
        """
        Append dữ liệu vào file final (CSV + JSONL) mỗi khi đạt ngưỡng SAVE_AGGREGATE_EVERY.
        """
        os.makedirs(data_dir, exist_ok=True)
        # Đảm bảo file final tồn tại với header ngay từ đầu
        final_csv = os.path.join(data_dir, 'news_final.csv')
        if not os.path.exists(final_csv):
            with open(final_csv, 'w', encoding='utf-8-sig', newline='') as f:
                fieldnames = ['URL', 'Title', 'Summary', 'Contents', 'Date', 'Author(s)', 'Category', 'Tags']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
        final_jsonl = os.path.join(data_dir, 'news_final.jsonl')
        if not os.path.exists(final_jsonl):
            open(final_jsonl, 'w', encoding='utf-8').close()

        valid = [a for a in articles if a and isinstance(a, dict)
                 and a.get('noi_dung') and a.get('tieu_de')]
        if not valid:
            return

        saver = DataSaver(output_dir=data_dir)
        # Đảm bảo file final có header ngay từ đầu
        final_csv = os.path.join(data_dir, 'news_final.csv')
        if not os.path.exists(final_csv):
            with open(final_csv, 'w', encoding='utf-8-sig', newline='') as f:
                fieldnames = ['URL', 'Title', 'Summary', 'Contents', 'Date', 'Author(s)', 'Category', 'Tags']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
        final_jsonl = os.path.join(data_dir, 'news_final.jsonl')
        if not os.path.exists(final_jsonl):
            open(final_jsonl, 'w', encoding='utf-8').close()

        # Append CSV chuẩn hóa
        saver.append_to_csv(valid, 'news_final.csv')

        # Append JSONL để không mất bài khi dừng giữa chừng
        jsonl_path = os.path.join(data_dir, 'news_final.jsonl')
        with open(jsonl_path, 'a', encoding='utf-8') as f:
            for item in valid:
                norm = DataSaver.normalize_article(item, ['URL', 'Title', 'Summary', 'Contents', 'Date', 'Author(s)', 'Category', 'Tags'])
                f.write(json.dumps(norm, ensure_ascii=False) + '\n')

        print(f"  📦 Aggregate append: {len(valid)} bài → news_final.csv / news_final.jsonl")

    def load_progress(self, data_dir: str = 'data') -> dict:
        """Đọc tiến độ đã lưu (để resume)"""
        progress_path = os.path.join(data_dir, 'progress.json')
        if os.path.exists(progress_path):
            try:
                with open(progress_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def crawl_source(self, source_key: str, max_per_category: int = 50,
                     delay: float = 1.0, data_dir: str = 'data',
                     resume: bool = True, category_filter: str = None) -> List[Dict]:
        """
        Cào tất cả bài viết từ một nguồn báo (tất cả chuyên mục).
        Hỗ trợ:
          - Dừng giữa chừng (Ctrl+C) → lưu checkpoint (JSON)
          - Resume: bỏ qua chuyên mục đã cào xong
          - Lưu file tổng (JSON+CSV) mỗi SAVE_AGGREGATE_EVERY bài
          - Batch processing: cào nhiều chuyên mục rồi delay 1 lần (nhanh hơn 3x)
        """
        source = NEWS_SOURCES.get(source_key)
        if not source:
            print(f"❌ Không tìm thấy nguồn: {source_key}")
            return []
        
        print(f"\n{'='*60}")
        print(f"🚀 Bắt đầu cào {source['name']}")
        if ENABLE_BATCH_PROCESSING:
            print(f"⚡ Batch processing: {BATCH_SIZE} chuyên mục/lần (nhanh ~{100*BATCH_SIZE/10:.0f}%)")
        print(f"{'='*60}\n")
        
        all_articles = []
        category_map = self.discover_categories(source_key)
        categories = list(category_map.keys())
        if AUTO_DISCOVER_CATEGORIES and category_map:
            static_categories = self._get_category_map(source_key)
            extra_count = max(0, len(category_map) - len(static_categories))
            print(f"  🔎 Chủ đề khả dụng: {len(category_map)} ({extra_count} chủ đề discover thêm)")
        if category_filter:
            if category_filter in categories:
                categories = [category_filter]
                print(f"  🎯 Chỉ cào chuyên mục: {category_filter}")
            else:
                print(f"⚠️  Chuyên mục '{category_filter}' không có trong nguồn {source['name']}")
                return []
        completed_categories = []

        # Resume: tải tiến độ cũ, bỏ qua chuyên mục đã xong
        if resume:
            progress = self.load_progress(data_dir)
            src_progress = progress.get(source_key, {})
            done_cats = src_progress.get('completed_categories', [])
            if done_cats:
                print(f"  ♻️  Resume: đã xong {len(done_cats)} chuyên mục → bỏ qua")
                completed_categories = list(done_cats)
                remaining = [c for c in categories if c not in done_cats]
                print(f"  📋 Còn lại: {len(remaining)} chuyên mục: {', '.join(remaining)}")
                categories = remaining
        
        # ── Batch processing ──
        if ENABLE_BATCH_PROCESSING:
            for batch_idx in range(0, len(categories), BATCH_SIZE):
                batch = categories[batch_idx:batch_idx + BATCH_SIZE]
                
                for idx, category in enumerate(batch, 1):
                    # Kiểm tra dừng
                    if self.is_stopped:
                        print(f"\n🛑 Dừng giữa chừng tại {source['name']}/{category}")
                        break

                    cat_num = batch_idx + idx
                    print(f"\n📂 [{cat_num}/{len(categories)}] Chuyên mục: {category}")
                    print("-" * 60)
                    
                    articles = self.crawl_category(source_key, category, max_per_category, delay)
                    all_articles.extend(articles)
                    completed_categories.append(category)
                    
                    print(f"✨ Chuyên mục '{category}': +{len(articles)} bài")
                    print(f"📦 TỔNG BÀI ĐÃ CÀO: {len(all_articles)} bài\n")

                    # Lưu checkpoint sau mỗi chuyên mục
                    self.save_checkpoint(all_articles, source_key,
                                        completed_categories, data_dir)
                    # Append luôn vào file final (tránh bỏ lỡ khi chưa đủ ngưỡng)
                    if articles:
                        self.save_aggregate(articles, data_dir)

                    # Kiểm tra dừng SAU khi đã lưu checkpoint
                    if self.is_stopped:
                        print(f"\n🛑 Dừng giữa chừng sau khi lưu {source['name']}/{category}")
                        break
                    
                    # Delay nhỏ giữa chuyên mục trong batch
                if self.is_stopped:
                    break
        else:
            # Non-batch mode (cũ)
            for idx, category in enumerate(categories, 1):
                # Kiểm tra dừng
                if self.is_stopped:
                    print(f"\n🛑 Dừng giữa chừng tại {source['name']}/{category}")
                    break

                print(f"\n📂 [{idx}/{len(categories)}] Chuyên mục: {category}")
                print("-" * 60)
                
                articles = self.crawl_category(source_key, category, max_per_category, delay)
                all_articles.extend(articles)
                completed_categories.append(category)
                
                print(f"✨ Chuyên mục '{category}': +{len(articles)} bài")
                print(f"📦 TỔNG BÀI ĐÃ CÀO: {len(all_articles)} bài\n")

                # Lưu checkpoint sau mỗi chuyên mục
                self.save_checkpoint(all_articles, source_key,
                                    completed_categories, data_dir)
                # Append luôn vào file final
                if articles:
                    self.save_aggregate(articles, data_dir)

                # Kiểm tra dừng SAU khi đã lưu checkpoint
                if self.is_stopped:
                    print(f"\n🛑 Dừng giữa chừng sau khi lưu {source['name']}/{category}")
                    break
                
                # Delay giữa các chuyên mục
                if self.is_stopped:
                    break
        
        status = "🛑 ĐÃ DỪNG" if self.is_stopped else "🎉 Hoàn thành"
        print(f"\n{'='*60}")
        print(f"{status} cào {source['name']}: {len(all_articles)} bài")
        if ENABLE_RESPONSE_CACHE:
            cache_hit_rate = 100 * len(self._response_cache) / max(1, self._requests_count) if self._requests_count else 0
            print(f"💾 Cache: {len(self._response_cache)} entries | Hit rate: {cache_hit_rate:.1f}%")
        print(f"{'='*60}\n")
        
        return all_articles


if __name__ == '__main__':
    # Test thử crawler
    crawler = NewspaperCrawler(use_mobile=True)
    
    # Test với VnExpress, chuyên mục thời sự
    articles = crawler.crawl_category('vnexpress', 'thoi-su', max_articles=5, delay=1.0)
    
    print(f"\n📊 Kết quả: Cào được {len(articles)} bài")
    if articles:
        print(f"📄 Bài đầu tiên: {articles[0].get('tieu_de', '')}")
        print(f"📝 Nội dung: {articles[0].get('noi_dung', '')[:200]}...")
