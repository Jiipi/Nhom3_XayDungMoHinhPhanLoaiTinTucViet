# -*- coding: utf-8 -*-
"""
🚀 OPTIMIZED CRAWL FOR LARGE-SCALE DATA (2GB+)
==================================================

Cải tiến so với main.py:
1. ✅ Progress bar + ETA (tqdm)
2. ✅ Incremental save: ghi từng bài ngay, không load hết RAM
3. ✅ Memory monitoring + warning
4. ✅ Auto-rotate output file khi quá 500MB
5. ✅ Real-time stats (bài/phút, DL time, eta giờ)

Sử dụng:
    python crawl_large_scale.py --mode newspaper --max 500000 --memory-limit 1500
"""

import argparse
import signal
import tracemalloc
import psutil
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Set

try:
    from tqdm import tqdm
except ImportError:
    print("⚠️  tqdm not found. Install: pip install tqdm")
    def tqdm(iterable, **kwargs):
        return iterable

# Handle imports - support both running from root and from crawlers/
import sys
from pathlib import Path

# Add parent folder to path for parent folder imports
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

try:
    from crawlers.newspaper_crawler import NewspaperCrawler
except ImportError:
    from .newspaper_crawler import NewspaperCrawler

from utils.path_utils import get_data_dir
from utils.incremental_writer import IncrementalWriter
from utils.data_utils import DataSaver
from utils.schema import is_valid_article_record
from utils.large_scale_checkpoint import (
    get_checkpoint_path,
    load_checkpoint,
    parse_completed_categories,
    save_checkpoint,
)

try:
    from config import NEWS_SOURCES, MAX_ARTICLES_PER_CATEGORY, OUTPUT_FORMAT
except ImportError:
    # Fallback nếu config.py không tồn tại
    NEWS_SOURCES = ['vnexpress', 'dantri', 'cand', 'thanhnien']
    MAX_ARTICLES_PER_CATEGORY = 100
    OUTPUT_FORMAT = 'jsonl'

DATA_DIR = get_data_dir(create=True)


class LargeScaleCrawler:
    """Crawler tối ưu cho dữ liệu lớn 2GB+ với monitoring"""
    
    def __init__(self, mode: str = 'newspaper', output_format: str = 'jsonl',
                 memory_limit_mb: int = 2000):
        self.mode = mode
        self.output_format = output_format
        self.memory_limit_mb = memory_limit_mb
        
        self.crawler = NewspaperCrawler(use_mobile=True)
        self.writer: Optional[IncrementalWriter] = None
        self.run_id: Optional[str] = None
        self.checkpoint_path: Optional[Path] = None
        self.completed_categories: Set[Tuple[str, str]] = set()
        
        self._stopped = False
        self.stats = {
            'total_articles': 0,
            'failed_articles': 0,
            'start_time': None,
            'categories_done': 0,
            'skipped_categories': 0,
        }
        
        # Memory tracking
        tracemalloc.start()
        self.process = psutil.Process()
    
    def _signal_handler(self, sig, frame):
        """Xử lý Ctrl+C"""
        print('\n\n⚠️  Nhận lệnh dừng (Ctrl+C)...')
        self._stopped = True
    
    def _get_memory_usage(self) -> Dict[str, float]:
        """Lấy thông tin memory hiện tại"""
        try:
            return {
                'ram_usage_mb': self.process.memory_info().rss / (1024**2),
                'ram_percent': self.process.memory_percent(),
            }
        except:
            return {'ram_usage_mb': 0, 'ram_percent': 0}
    
    def _check_memory(self) -> bool:
        """Kiểm tra nếu memory quá cao"""
        mem = self._get_memory_usage()
        if mem['ram_usage_mb'] > self.memory_limit_mb:
            print(f"⚠️  ⚠️  CẢNH BÁO MEMORY: {mem['ram_usage_mb']:.0f}MB > {self.memory_limit_mb}MB")
            print(f"  → Xem xét tăng --memory-limit nếu không bị hang")
            return False
        return True

    def _build_category_plan(self, sources: List[str]) -> List[Tuple[str, str]]:
        all_categories: List[Tuple[str, str]] = []
        for source in sources:
            if source not in NEWS_SOURCES:
                print(f"⚠️  Nguồn '{source}' không tìm thấy")
                continue
            categories = NEWS_SOURCES[source].get('categories', [])
            for category in categories:
                all_categories.append((source, category))
        return all_categories

    def _save_checkpoint(self):
        if not self.checkpoint_path or not self.writer or not self.run_id:
            return
        save_checkpoint(
            checkpoint_path=self.checkpoint_path,
            run_id=self.run_id,
            output_format=self.output_format,
            completed_categories=self.completed_categories,
            stats=self.stats,
            writer=self.writer,
        )

    def _load_checkpoint(self, resume_id: str):
        checkpoint_path = get_checkpoint_path(DATA_DIR, resume_id)
        if not checkpoint_path.exists():
            print(f"⚠️  Không tìm thấy checkpoint cho run_id={resume_id}. Bắt đầu mới.")
            return

        try:
            payload = load_checkpoint(checkpoint_path)
            self.completed_categories = parse_completed_categories(payload)
            self.stats['total_articles'] = int(payload.get('total_articles', 0))
            self.stats['failed_articles'] = int(payload.get('failed_articles', 0))
            self.stats['categories_done'] = int(payload.get('categories_done', 0))
            print(f"♻️  Resume run_id={resume_id}: {len(self.completed_categories)} chuyên mục đã hoàn tất")
        except Exception as e:
            print(f"⚠️  Đọc checkpoint lỗi: {e}. Tiếp tục như phiên mới.")

    def _resolve_target_size_bytes(self, goal: str, target_gb: float, target_mb: int) -> int:
        if target_mb and target_mb > 0:
            return target_mb * 1024 * 1024
        if target_gb and target_gb > 0:
            return int(target_gb * 1024 * 1024 * 1024)
        if goal == 'processed-1gb':
            return 1024 * 1024 * 1024
        if goal == 'raw-2gb':
            return 2 * 1024 * 1024 * 1024
        return 0

    def crawl_sources(self, sources: List[str], max_articles: int = 100,
                      articles_per_category: int = MAX_ARTICLES_PER_CATEGORY,
                      run_id: Optional[str] = None,
                      resume_id: Optional[str] = None,
                      goal: str = 'none',
                      target_gb: float = 0,
                      target_mb: int = 0,
                      category_retries: int = 2,
                      rotate_mb: int = 500,
                      batch_size: int = 50):
        """Cào từ các nguồn"""
        
        # Setup signal handler
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Chuẩn bị output + checkpoint
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.run_id = resume_id or run_id or timestamp
        output_filename = f'news_crawled_{self.run_id}'
        self.checkpoint_path = get_checkpoint_path(DATA_DIR, self.run_id)

        if resume_id:
            self._load_checkpoint(resume_id)

        self.writer = IncrementalWriter(
            DATA_DIR,
            output_filename,
            format=self.output_format,
            max_file_size_mb=rotate_mb,
            batch_size=batch_size  # Ghi CSV sau mỗi batch_size bài khi dùng json-csv
        )

        target_size_bytes = self._resolve_target_size_bytes(goal, target_gb, target_mb)
        
        self.stats['start_time'] = datetime.now()
        
        all_categories = self._build_category_plan(sources)
        if self.completed_categories:
            before = len(all_categories)
            all_categories = [
                item for item in all_categories
                if item not in self.completed_categories
            ]
            self.stats['skipped_categories'] = before - len(all_categories)
        
        print(f"\n🔄 Chuẩn bị cào {len(all_categories)} chuyên mục từ {len(sources)} nguồn")
        print(f"📊 Max {max_articles} bài/chuyên mục | Limit memory: {self.memory_limit_mb}MB")
        print(f"💾 Format: {self.output_format.upper()} (auto-rotate ≥{rotate_mb}MB)")
        if target_size_bytes > 0:
            print(f"🎯 Target dung lượng: {target_size_bytes / (1024**3):.2f} GB")
        print(f"{'='*70}\n")
        
        # Progress bar chính
        with tqdm(total=len(all_categories), desc="📡 Crawling", unit="category") as pbar:
            for source, cat_name in all_categories:
                if self._stopped:
                    print("\n⛔ Dừng crawl theo yêu cầu")
                    break
                
                # Check memory trước mỗi category
                if not self._check_memory():
                    print("⚠️  Có thể memory quá cao, continue tuy nhiên...")
                
                # Cào bài từ category này + retry chống mất mạng
                articles = []
                for attempt in range(1, category_retries + 1):
                    articles = self._crawl_category(
                        source,
                        cat_name,
                        max_articles=articles_per_category
                    )
                    if articles or attempt == category_retries:
                        break
                    backoff = min(20, 2 ** attempt)
                    print(f"  🔄 Retry category {source}/{cat_name} sau {backoff}s ({attempt}/{category_retries})")
                    time.sleep(backoff)
                
                # Ghi từng bài (incremental)
                for article in articles:
                    if self._stopped:
                        break
                    
                    # Validate & clean
                    if is_valid_article_record(article):
                        # Chuẩn hoá sang cột chuẩn trước khi ghi
                        DEFAULT_FIELDS = ['URL', 'Title', 'Summary', 'Contents', 'Date', 'Author(s)', 'Category', 'Tags']
                        norm = DataSaver.normalize_article(article, DEFAULT_FIELDS)
                        self.writer.write_article(norm, fieldnames=DEFAULT_FIELDS)
                        self.stats['total_articles'] += 1

                        if target_size_bytes > 0 and self.writer.total_bytes_written >= target_size_bytes:
                            print("\n🎯 Đã đạt mục tiêu dung lượng, dừng crawl an toàn...")
                            self._stopped = True
                            break
                    else:
                        self.stats['failed_articles'] += 1
                
                self.stats['categories_done'] += 1
                self.completed_categories.add((source, cat_name))
                self._save_checkpoint()
                elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
                
                # Update progress bar
                mem = self._get_memory_usage()
                speed = self.stats['total_articles'] / max(elapsed if elapsed > 0 else 1, 1)
                pbar.set_postfix({
                    'bài': self.stats['total_articles'],
                    'RAM': f"{mem['ram_usage_mb']:.0f}MB",
                    'tốc độ': f"{speed:.1f}/s"
                })
                pbar.update(1)

                if self._stopped:
                    break
        
        # Hoàn tất
        self.writer.flush()  # Ghi batch cuối cùng nếu dùng json-csv
        self.writer.close()
        self._print_final_stats()
        self._save_checkpoint()
    
    def _crawl_category(self, source: str, cat_name: str,
                       max_articles: int) -> List[Dict]:
        """Cào 1 chuyên mục"""
        try:
            articles = self.crawler.crawl_category(
                source_key=source,
                category=cat_name,
                max_articles=max_articles,
                delay=0.5,
            )
            return articles
        except Exception as e:
            print(f"❌ Lỗi cào {source}/{cat_name}: {e}")
            return []
    
    def _print_final_stats(self):
        """In thống kê cuối"""
        elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
        elapsed_hours = elapsed / 3600
        
        print(f"\n{'='*70}")
        print(f"✅ CRAWL HOÀN TẤT")
        print(f"{'='*70}")
        print(f"⏱️  Thời gian: {elapsed_hours:.1f} giờ ({elapsed:.0f} giây)")
        print(f"📊 Tổng bài cào: {self.stats['total_articles']}")
        print(f"❌ Bài lỗi: {self.stats['failed_articles']}")
        print(f"📁 Chuyên mục done: {self.stats['categories_done']}")
        if self.stats['skipped_categories']:
            print(f"♻️  Chuyên mục skip do resume: {self.stats['skipped_categories']}")
        print(f"🚀 Tốc độ: {self.stats['total_articles']/max(elapsed, 1):.2f} bài/giây")
        
        mem = self._get_memory_usage()
        print(f"💾 Memory cuối: {mem['ram_usage_mb']:.0f}MB")
        
        # File info
        if self.writer:
            files = sorted(self.writer.output_dir.glob(f'news_crawled_{self.run_id}*'))
            total_size_mb = sum(f.stat().st_size for f in files) / (1024**2)
            print(f"📦 Output files ({self.output_format.upper()}):")
            for f in files:
                size_mb = f.stat().st_size / (1024**2)
                print(f"   {f.name}: {size_mb:.2f}MB")
            print(f"   TỔNG: {total_size_mb:.2f}MB")

        if self.checkpoint_path:
            print(f"🧷 Checkpoint: {self.checkpoint_path}")
        
        print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description='Crawl báo tối ưu cho dữ liệu lớn 2GB+')
    parser.add_argument('--mode', default='newspaper', choices=['newspaper', 'scrapy'],
                        help='Chế độ cào (mặc định: newspaper)')
    parser.add_argument('--sources', nargs='+', default=['vnexpress'],
                        help='Danh sách nguồn (hoặc "all" cho tất cả)')
    parser.add_argument('--max', type=int, default=100,
                        help='Max bài/chuyên mục (mặc định: 100)')
    parser.add_argument('--output-format', choices=['jsonl', 'csv', 'json-csv'], default='jsonl',
                        help='Format output (mặc định: jsonl). Sử dụng json-csv để ghi ĐỒNG THỜI JSON + CSV')
    parser.add_argument('--memory-limit', type=int, default=2000,
                        help='Memory limit MB (mặc định: 2000)')
    parser.add_argument('--run-id', type=str, default=None,
                        help='ID phiên crawl (để đặt tên output/checkpoint)')
    parser.add_argument('--resume-id', type=str, default=None,
                        help='Resume từ run_id cũ')
    parser.add_argument('--batch-size', type=int, default=50,
                        help='Số bài để batch trước khi ghi CSV (chỉ dùng với --output-format json-csv, mặc định: 50)')
    parser.add_argument('--goal', choices=['none', 'processed-1gb', 'raw-2gb'], default='none',
                        help='Mục tiêu dung lượng nhanh: processed-1gb hoặc raw-2gb')
    parser.add_argument('--target-gb', type=float, default=0,
                        help='Dừng khi đạt dung lượng GB (ưu tiên cao hơn --goal)')
    parser.add_argument('--target-mb', type=int, default=0,
                        help='Dừng khi đạt dung lượng MB (ưu tiên cao nhất)')
    parser.add_argument('--category-retries', type=int, default=2,
                        help='Số lần retry cho mỗi chuyên mục khi lỗi mạng')
    parser.add_argument('--rotate-mb', type=int, default=500,
                        help='Tự tách file khi vượt dung lượng MB')
    
    args = parser.parse_args()
    
    # Resolve sources
    if args.sources == ['all']:
        sources = list(NEWS_SOURCES.keys())
    else:
        sources = args.sources
    
    # Crawl
    crawler = LargeScaleCrawler(
        mode=args.mode,
        output_format=args.output_format,
        memory_limit_mb=args.memory_limit
    )
    
    crawler.crawl_sources(
        sources,
        max_articles=args.max,
        articles_per_category=args.max,
        run_id=args.run_id,
        resume_id=args.resume_id,
        goal=args.goal,
        target_gb=args.target_gb,
        target_mb=args.target_mb,
        category_retries=max(1, args.category_retries),
        rotate_mb=max(100, args.rotate_mb),
        batch_size=max(1, args.batch_size),
    )


if __name__ == '__main__':
    main()
