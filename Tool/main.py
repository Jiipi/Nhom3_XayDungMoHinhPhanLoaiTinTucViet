# -*- coding: utf-8 -*-
"""
🚀 TOOL CÀO BÁO TỐC ĐỘ CAO
===========================

Script chính để cào hàng nghìn bài báo từ nhiều nguồn

Tính năng:
- Hỗ trợ 15 nguồn báo lớn tại Việt Nam
- 2 chế độ: newspaper3k (đơn giản) và Scrapy (cực nhanh)
- Dừng giữa chừng (Ctrl+C) → tự lưu checkpoint
- Resume tự động: bỏ qua chuyên mục đã cào
- Lưu checkpoint CSV + JSON sau mỗi chuyên mục
- Lọc bài cào dở, chỉ giữ bài hoàn chỉnh

Thông tin bài báo lưu: chủ đề, tiêu đề, nội dung, nguồn, link

Sử dụng:
    python main.py --sources vnexpress dantri --max 100
    python main.py --sources all --max 500
"""

import argparse
import sys
import os
import json
import csv
import signal
from datetime import datetime
from typing import List

# Import các module
from crawlers.newspaper_crawler import NewspaperCrawler
from utils.data_utils import DataSaver, DataCleaner, DataAnalyzer
from utils.path_utils import get_data_dir
from utils.schema import is_valid_article_record
from config import NEWS_SOURCES, MAX_ARTICLES_PER_CATEGORY, OUTPUT_FORMAT, SOURCE_PARALLELISM
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

DATA_DIR = str(get_data_dir())


class NewsAggregator:
    """Class chính để điều phối việc cào báo"""
    
    def __init__(self, output_format: str = OUTPUT_FORMAT):
        self.output_format = output_format
        self.all_articles = []
        self._stopped = False
        
        # Khởi tạo crawler duy nhất (Newspaper3k)
        self.crawler = NewspaperCrawler(use_mobile=True)
        
        # Khởi tạo các utility
        self.saver = DataSaver(output_dir=DATA_DIR)
        self.cleaner = DataCleaner()
        self.analyzer = DataAnalyzer()

        # Đăng ký signal handler cho Ctrl+C
        signal.signal(signal.SIGINT, self._handle_stop)

    def _handle_stop(self, signum, frame):
        """Xử lý Ctrl+C (Interrupt): Bắt tín hiệu dừng từ bàn phím để Tool nghỉ an toàn (checkpoint) thay vì Crash"""
        if self._stopped:
            # Nếu user mất kiên nhẫn ấn Ctrl+C lần 2 (Spam) thì ngắt cầu dao điện văng thẳng khỏi python
            print("\n\n⚡ Thoát ngay lập tức!")
            sys.exit(1)
            
        # Thao tác ấn 1 lần: Bật cờ (flag) thành True để luồng bên trong cào báo đọc nhận ra đã dừng!
        self._stopped = True
        
        # Phi lệnh Stop xuống sâu Crawler ở Cấp thấp
        if hasattr(self.crawler, 'request_stop'):
            self.crawler.request_stop()
        print("\n⚠️  Nhấn Ctrl+C lần nữa để thoát ngay (không lưu)")
    
    def crawl_sources(self, sources: List[str], max_per_category: int = MAX_ARTICLES_PER_CATEGORY, category: str = None):
        if 'all' in sources:
            sources = list(NEWS_SOURCES.keys())
        
        print("\n" + "🎯" + "="*59)
        print(f"🎯 BẮT ĐẦU CÀO {len(sources)} NGUỒN BÁO")
        print("🎯" + "="*59)
        print(f"📋 Nguồn: {', '.join(sources)}")
        print(f"📊 Tối đa: {max_per_category} bài/chuyên mục")
        print(f"ℹ️  Nhấn Ctrl+C để dừng giữa chừng (sẽ tự lưu)")
        print("="*60 + "\n")
        
        start_time = datetime.now()

        # Chạy song song theo nguồn
        lock = threading.Lock()
        def run_source(src_key):
            crawler = NewspaperCrawler(use_mobile=True)
            articles = crawler.crawl_source(
                src_key, max_per_category, delay=1.0,
                data_dir=DATA_DIR, resume=True, category_filter=category)
            with lock:
                if articles:
                    self.all_articles.extend(articles)
            return src_key, len(articles)

        with ThreadPoolExecutor(max_workers=min(SOURCE_PARALLELISM, len(sources))) as executor:
            futures = {executor.submit(run_source, s): s for s in sources}
            for idx, future in enumerate(as_completed(futures), 1):
                src_key = futures[future]
                try:
                    _, count = future.result()
                    print(f"\n✅ Hoàn thành {src_key}: +{count} bài | Tổng hiện tại: {len(self.all_articles)}")
                except Exception as e:
                    print(f"❌ Lỗi khi cào {src_key}: {e}")
        
        duration = (datetime.now() - start_time).total_seconds()
        
        status = "🛑 ĐÃ DỪNG" if self._stopped else "🎉 HOÀN THÀNH"
        print(f"\n{'='*60}")
        print(f"{status}")
        print(f"⏱️  Thời gian: {duration:.1f} giây ({duration/60:.1f} phút)")
        print(f"📊 Tổng số bài: {len(self.all_articles)}")
        if duration > 0:
            print(f"⚡ Tốc độ: {len(self.all_articles)/duration*60:.1f} bài/phút")
        print("="*60 + "\n")
    
    def process_and_save(self):
        """Xử lý và lưu dữ liệu cuối cùng (cả CSV + JSON, 5 trường đầy đủ)"""
        if not self.all_articles:
            print("⚠️  Không có dữ liệu để lưu")
            return
        
        print("\n" + "🧹"*30)
        print("🧹 XỬ LÝ DỮ LIỆU")
        print("🧹"*30 + "\n")
        
        # Lọc bài cào dở (thiếu trường bắt buộc)
        valid = [a for a in self.all_articles if is_valid_article_record(a)]
        removed = len(self.all_articles) - len(valid)
        if removed:
            print(f"  🗑️  Đã lọc {removed} bài không hợp lệ / cào dở")
        self.all_articles = valid

        # Làm sạch
        original_count = len(self.all_articles)
        self.all_articles = self.cleaner.clean_dataset(self.all_articles)
        cleaned_count = len(self.all_articles)
        
        print(f"✅ Đã làm sạch: {original_count} → {cleaned_count} bài\n")
        
        # Thống kê
        stats = self.analyzer.get_statistics(self.all_articles)
        self.analyzer.print_statistics(stats)
        
        # Lưu file cuối cùng
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        print("💾 Đang lưu dữ liệu...\n")

        # ── CSV / JSON / JSONL theo cột chuẩn (URL, Title, Summary, Contents, Date, Author(s), Category)
        csv_path = os.path.join(DATA_DIR, f'news_final_{timestamp}.csv')
        saver = DataSaver(output_dir=DATA_DIR)
        saver.save_to_csv(self.all_articles, filename=os.path.basename(csv_path))

        json_path = os.path.join(DATA_DIR, f'news_final_{timestamp}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            # Ghi JSON đầy đủ (gốc) để tham khảo
            json.dump(self.all_articles, f, ensure_ascii=False, indent=2)
        print(f"  ✅ JSON: {len(self.all_articles)} bài → {json_path}")

        if self.output_format in ('jsonl', 'all'):
            jsonl_path = os.path.join(DATA_DIR, f'news_final_{timestamp}.jsonl')
            with open(jsonl_path, 'w', encoding='utf-8') as f:
                for item in self.all_articles:
                    norm = DataSaver.normalize_article(item, ['URL', 'Title', 'Summary', 'Contents', 'Date', 'Author(s)', 'Category', 'Tags'])
                    f.write(json.dumps(norm, ensure_ascii=False) + '\n')
            print(f"  ✅ JSONL: {len(self.all_articles)} bài → {jsonl_path}")
        
        # Xóa progress sau khi hoàn thành (chỉ khi không bị dừng)
        if not self._stopped:
            progress_path = os.path.join(DATA_DIR, 'progress.json')
            if os.path.exists(progress_path):
                os.remove(progress_path)
                print("  🗑️  Đã xóa progress.json (đã hoàn thành)")

        print(f"\n✅ HOÀN THÀNH! Dữ liệu đã được lưu vào thư mục {DATA_DIR}/\n")


def main():
    """Hàm main"""
    parser = argparse.ArgumentParser(
        description='🚀 Tool cào báo tốc độ cao',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ sử dụng:
  # Cào VnExpress và Dân Trí
  python main.py --sources vnexpress dantri --max 100

  # Cào tất cả nguồn (siêu nhanh, lưu mặc định)
  python main.py --sources all --max 500

  # Cào Tuổi Trẻ, Thanh Niên, lưu tất cả format
  python main.py --sources tuoitre thanhnien --max 200 --format all

Các nguồn hỗ trợ (15 nguồn):
  vnexpress, dantri, tuoitre, thanhnien, vietnamnet,
  vneconomy, laodong, zingnews, vietnamplus, nhandan,
  qdnd, cand, baodautu, baochinhphu, vtv
        """
    )
    
    parser.add_argument(
        '--sources',
        type=str,
        nargs='+',
        default=['all'],
        help='Danh sách nguồn báo cần cào, hoặc "all" để cào tất cả (mặc định: all)'
    )
    
    parser.add_argument(
        '--max',
        type=int,
        default=MAX_ARTICLES_PER_CATEGORY,
        help='Số bài tối đa mỗi chuyên mục. Dùng 0 để cào hết tất cả trang của chuyên mục (mặc định: 0)'
    )
    
    parser.add_argument(
        '--format',
        type=str,
        default=OUTPUT_FORMAT,
        choices=['csv', 'json', 'jsonl', 'all'],
        help=f'Format output (mặc định: {OUTPUT_FORMAT})'
    )
    parser.add_argument(
        '--category',
        type=str,
        default=None,
        help='Tên chuyên mục cụ thể cần cào (ví dụ: thoi-su). Để trống để cào tất cả.'
    )
    
    args = parser.parse_args()
    
    # Banner
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║        🚀 TOOL CÀO BÁO TỐC ĐỘ CAO 🚀                        ║
║                                                              ║
║  ⚡ Cào hàng nghìn bài báo trong vài phút                   ║
║  📰 Hỗ trợ 15 nguồn báo lớn tại Việt Nam                   ║
║  🔥 Đa luồng xử lý siêu tốc (Newspaper3k)                   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Chạy
    try:
        aggregator = NewsAggregator(output_format=args.format)
        aggregator.crawl_sources(args.sources, args.max, category=args.category)
        aggregator.process_and_save()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Đã dừng bởi người dùng. Đang lưu dữ liệu hiện có...")
        try:
            aggregator.process_and_save()
        except Exception:
            # Lưu khẩn cấp nếu process_and_save lỗi
            if aggregator.all_articles:
                emergency = os.path.join(DATA_DIR, 'emergency_save.json')
                with open(emergency, 'w', encoding='utf-8') as f:
                    json.dump(aggregator.all_articles, f, ensure_ascii=False, indent=2)
                print(f"  💾 Đã lưu khẩn cấp → {emergency}")
        
    except Exception as e:
        print(f"\n\n❌ Lỗi nghiêm trọng: {e}")
        import traceback
        traceback.print_exc()
        # Cố lưu những gì đã có
        if aggregator.all_articles:
            try:
                aggregator.process_and_save()
            except Exception:
                pass


if __name__ == '__main__':
    main()
