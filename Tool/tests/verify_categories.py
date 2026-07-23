# -*- coding: utf-8 -*-
"""
Kiểm tra mapping chủ đề:
  1. Mỗi category trong config.py → tạo URL → kiểm tra HTTP status
  2. So sánh config.py với link-bao.txt để phát hiện thiếu/thừa
  3. Thử lấy link bài viết (get_article_links) → có link hay không

Chạy:  python tests/verify_categories.py
"""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from crawlers.newspaper_crawler import NewspaperCrawler
from config import NEWS_SOURCES

# ── Đọc link-bao.txt để lấy danh sách URL gốc ──────────────────────
def parse_link_bao(filepath='docs/link-bao.txt'):
    """Trích xuất tất cả URL từ link-bao.txt, nhóm theo domain."""
    urls_by_domain = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
    except FileNotFoundError:
        print(f"⚠️  Không tìm thấy {filepath}")
        return {}

    for url in re.findall(r'https?://[^\s\'"<>,]+', text):
        url = url.rstrip('/')
        # Lấy domain
        m = re.match(r'https?://(?:www\.|m\.)?([^/]+)', url)
        if m:
            domain = m.group(1).lower()
            urls_by_domain.setdefault(domain, set()).add(url)
    return urls_by_domain


def extract_category_from_url(url, base_url):
    """Trích xuất phần category từ URL đầy đủ."""
    # Loại bỏ base_url (cả www. variant)
    path = url
    for prefix in [base_url, base_url.replace('https://', 'https://www.'),
                   base_url.replace('https://www.', 'https://')]:
        path = path.replace(prefix, '')
    path = path.strip('/')
    # Bỏ đuôi .htm/.html
    path = re.sub(r'\.(htm|html)$', '', path)
    # Bỏ query string
    path = path.split('?')[0].split('#')[0]
    return path


# ── Tạo URL cho mỗi category theo pattern của crawler ────────────────
SOURCE_URL_PATTERNS = {
    'vnexpress':   '{base}/{cat}',
    'dantri':      '{base}/{cat}.htm',
    'tuoitre':     '{base}/{cat}.htm',
    'thanhnien':   '{base}/{cat}',
    'vietnamnet':  '{base}/{cat}',
    'vneconomy':   '{base}/{cat}.htm',
    'laodong':     '{base}/{cat}',
    'zingnews':    '{base}/{cat}.html',
    'vietnamplus': '{base}/{cat}/',
    'nhandan':     '{base}/{cat}/',
    'qdnd':        '{base}/{cat}',
    'cand':        '{base}/{cat}/',
    'baodautu':    '{base}/{cat}/',
    'baochinhphu': '{base}/{cat}.htm',
    'vtv':         '{base}/{cat}.htm',
}

# ── Domain mapping cho so sánh với link-bao.txt ─────────────────────
SOURCE_DOMAINS = {
    'vnexpress': 'vnexpress.net',
    'dantri': 'dantri.com.vn',
    'tuoitre': 'tuoitre.vn',
    'thanhnien': 'thanhnien.vn',
    'vietnamnet': 'vietnamnet.vn',
    'vneconomy': 'vneconomy.vn',
    'laodong': 'laodong.vn',
    'zingnews': 'znews.vn',      # zingnews redirect → znews
    'vietnamplus': 'vietnamplus.vn',
    'nhandan': 'nhandan.vn',
    'qdnd': 'qdnd.vn',
    'cand': 'cand.com.vn',
    'baodautu': 'baodautu.vn',
    'baochinhphu': 'baochinhphu.vn',
    'vtv': 'vtv.vn',
}


def check_url_status(session, url, timeout=15):
    """Kiểm tra HTTP status của URL. Trả về (status_code, final_url) hoặc (0, error)."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,*/*;q=0.8',
            'Accept-Language': 'vi-VN,vi;q=0.9',
        }
        resp = session.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        return resp.status_code, resp.url
    except Exception as e:
        return 0, str(e)


def main():
    link_bao_urls = parse_link_bao()
    crawler = NewspaperCrawler()
    session = requests.Session()

    all_results = {}
    grand_ok = 0
    grand_fail = 0
    grand_total = 0

    for src_key, src_info in NEWS_SOURCES.items():
        base_url = src_info['base_url']
        name = src_info['name']
        categories = src_info.get('categories', [])
        pattern = SOURCE_URL_PATTERNS.get(src_key, '{base}/{cat}')
        domain = SOURCE_DOMAINS.get(src_key, '')

        print(f"\n{'=' * 70}")
        print(f"📰  {name}  ({base_url})")
        print(f"{'=' * 70}")

        # Lấy các category từ link-bao.txt cho domain này
        linkbao_cats = set()
        for d_key, urls in link_bao_urls.items():
            if domain in d_key or d_key in domain:
                for u in urls:
                    cat = extract_category_from_url(u, base_url)
                    # Cũng thử với www variant
                    if not cat:
                        cat = extract_category_from_url(u, base_url.replace('https://', 'https://www.'))
                    if cat and '/' not in cat and cat != domain and len(cat) > 1:
                        linkbao_cats.add(cat)

        config_cats = set(categories)

        # So sánh
        only_config = config_cats - linkbao_cats
        only_linkbao = linkbao_cats - config_cats

        if only_config:
            print(f"  ⚠️  Chỉ có trong config (không thấy trong link-bao.txt):")
            for c in sorted(only_config):
                print(f"       + {c}")
        if only_linkbao:
            print(f"  ⚠️  Chỉ có trong link-bao.txt (thiếu trong config):")
            for c in sorted(only_linkbao):
                print(f"       - {c}")
        if not only_config and not only_linkbao:
            print(f"  ✅  Config khớp hoàn toàn với link-bao.txt")

        # Kiểm tra từng category URL
        print(f"\n  {'Chuyên mục':<35} {'HTTP':>5}  {'Links':>6}  {'Trạng thái'}")
        print(f"  {'─' * 35} {'─' * 5}  {'─' * 6}  {'─' * 20}")

        source_ok = 0
        source_fail = 0

        for cat in categories:
            grand_total += 1
            cat_url = pattern.format(base=base_url, cat=cat)

            # Kiểm tra HTTP status
            status_code, final_url = check_url_status(session, cat_url)

            # Thử lấy link bài viết (max 3)
            try:
                links = crawler.get_article_links(src_key, cat, max_links=3)
                link_count = len(links)
            except Exception:
                link_count = 0

            # Đánh giá
            if status_code == 200 and link_count > 0:
                status = "✅ OK"
                source_ok += 1
                grand_ok += 1
            elif status_code == 200 and link_count == 0:
                status = "⚠️  200 nhưng 0 link"
                source_fail += 1
                grand_fail += 1
            elif status_code in (301, 302, 308):
                # Redirect — check if final URL is valid
                if link_count > 0:
                    status = f"↪️  Redirect → {link_count} link"
                    source_ok += 1
                    grand_ok += 1
                else:
                    status = f"↪️  Redirect, 0 link"
                    source_fail += 1
                    grand_fail += 1
            elif status_code == 404:
                status = "❌ 404 Not Found"
                source_fail += 1
                grand_fail += 1
            elif status_code == 0:
                status = f"❌ Lỗi: {final_url[:40]}"
                source_fail += 1
                grand_fail += 1
            else:
                status = f"⚠️  HTTP {status_code}"
                if link_count > 0:
                    status += f", {link_count} link"
                    source_ok += 1
                    grand_ok += 1
                else:
                    source_fail += 1
                    grand_fail += 1

            in_linkbao = "📋" if cat in linkbao_cats else "  "
            print(f"  {in_linkbao} {cat:<33} {status_code:>5}  {link_count:>6}  {status}")

            time.sleep(0.5)

        all_results[src_key] = {'ok': source_ok, 'fail': source_fail,
                                'total': len(categories), 'name': name}
        print(f"\n  → {name}: {source_ok}/{len(categories)} chuyên mục OK")

    # ── Tổng kết ─────────────────────────────────────────────────────────
    print(f"\n\n{'=' * 70}")
    print(f"📊  TỔNG KẾT KIỂM TRA CHUYÊN MỤC")
    print(f"{'=' * 70}")
    print(f"  {'Nguồn':<25} {'OK':>5} {'Fail':>5} {'Tổng':>5}")
    print(f"  {'─' * 25} {'─' * 5} {'─' * 5} {'─' * 5}")
    for src_key, r in all_results.items():
        mark = "✅" if r['fail'] == 0 else "⚠️ "
        print(f"  {mark} {r['name']:<23} {r['ok']:>5} {r['fail']:>5} {r['total']:>5}")
    print(f"  {'─' * 25} {'─' * 5} {'─' * 5} {'─' * 5}")
    print(f"  {'TỔNG':<25} {grand_ok:>5} {grand_fail:>5} {grand_total:>5}")
    
    if grand_fail > 0:
        print(f"\n  ❌ Có {grand_fail} chuyên mục cần sửa!")
    else:
        print(f"\n  ✅ Tất cả {grand_total} chuyên mục đều OK!")

    return grand_fail == 0


if __name__ == '__main__':
    ok = main()
    sys.exit(0 if ok else 1)
