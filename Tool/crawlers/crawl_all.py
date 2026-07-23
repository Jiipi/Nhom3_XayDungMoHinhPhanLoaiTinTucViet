# -*- coding: utf-8 -*-
"""
🚀 CRAWL ALL - Cào tất cả nguồn, tất cả chuyên mục, tối đa số lượng
====================================================================
Mục tiêu: 15,000+ bài chất lượng cao

Tính năng:
  - Cào TẤT CẢ nguồn song song (mỗi nguồn 1 luồng riêng)
  - Dừng giữa chừng (Ctrl+C) → tự lưu checkpoint JSON
  - Resume tự động: bỏ qua chuyên mục đã cào xong
  - Lọc bài cào dở: chỉ lưu bài có đủ 5 trường
  - Checkpoint: chỉ lưu JSON (nhẹ, nhanh)
  - File tổng: lưu cả JSON + CSV, tự động lưu mỗi SAVE_AGGREGATE_EVERY bài
  - Thông tin: chủ đề, tiêu đề, nội dung, nguồn, link

Chạy:
    python crawl_all.py                        # Cào tất cả, merge với data cũ
    python crawl_all.py --fresh                # Cào tất cả, KHÔNG merge
    python crawl_all.py --sources vnexpress dantri  # Chỉ cào các nguồn chỉ định
    python crawl_all.py --max 100              # Giới hạn 100 bài/category
"""

import argparse
import os
import sys
import json
import csv
import hashlib
import random
import time
import signal
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from crawlers.newspaper_crawler import NewspaperCrawler
from utils.data_utils import DataSaver
from config import (NEWS_SOURCES, MAX_WORKERS, SAVE_AGGREGATE_EVERY,
                    SOURCE_PARALLELISM, PROGRESS_USE_COLOR,
                    PROGRESS_BAR_WIDTH, PROGRESS_RATE_UNIT)

DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)

# ── Biến toàn cục để dừng giữa chừng ──
_stop_event = threading.Event()
_crawlers: list = []  # danh sách crawler đang chạy (để gửi request_stop)
STOP_FLAG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'STOP.flag')

# ── Lock để ghi file chung thread-safe ──
_write_lock = threading.Lock()
_ANSI_RESET = "\033[0m"
_ANSI_GRAY = "\033[90m"
_ANSI_PINK = "\033[95m"
_ANSI_GREEN = "\033[92m"
_ANSI_RED = "\033[91m"
_ANSI_CYAN = "\033[96m"


def _supports_ansi_output() -> bool:
    if not PROGRESS_USE_COLOR:
        return False
    if os.getenv('NO_COLOR'):
        return False
    return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()


def _human_bytes(value: float) -> str:
    units = ['bytes', 'KB', 'MB', 'GB']
    size = float(max(0.0, value))
    idx = 0
    while size >= 1024.0 and idx < len(units) - 1:
        size /= 1024.0
        idx += 1
    if idx == 0:
        return f"{int(size)} {units[idx]}"
    return f"{size:.1f} {units[idx]}"


def _format_eta(seconds: float) -> str:
    if seconds <= 0:
        return '0:00:00'
    sec = int(seconds)
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h}:{m:02d}:{s:02d}"


def _build_progress_line(done: int, total: int, start_ts: float, counter: dict) -> str:
    width = max(20, PROGRESS_BAR_WIDTH)
    pct = (done / total) if total else 0.0
    fill = int(width * pct)
    bar_fill = '█' * fill
    bar_rest = '─' * (width - fill)
    elapsed = max(0.001, time.monotonic() - start_ts)
    remain = max(0, total - done)

    payload_done = counter.get('payload_bytes', 0)
    avg_payload = (payload_done / done) if done else 0.0
    payload_total_est = int(avg_payload * total) if total else payload_done

    if PROGRESS_RATE_UNIT == 'bytes':
        rate = payload_done / elapsed
        eta = (max(0, payload_total_est - payload_done) / rate) if rate > 0 else 0.0
        progress_txt = f"{_human_bytes(payload_done)}/{_human_bytes(payload_total_est)}"
        rate_txt = f"{_human_bytes(rate)}/s"
    else:
        rate = done / elapsed
        eta = (remain / rate) if rate > 0 else 0.0
        progress_txt = f"{done}/{total} links"
        rate_txt = f"{rate:.1f} links/s"

    info = (
        f"{progress_txt} {rate_txt} eta {_format_eta(eta)} "
        f"ok:{counter['ok']} short:{counter['short']} "
        f"dup:{counter['dup']} old:{counter['old']} err:{counter['error']}"
    )

    if _supports_ansi_output():
        bar = (
            f"{_ANSI_PINK}{bar_fill}{_ANSI_RESET}"
            f"{_ANSI_GRAY}{bar_rest}{_ANSI_RESET}"
        )
        info = (
            info
            .replace('eta ', f"{_ANSI_CYAN}eta ")
            .replace('ok:', f"{_ANSI_GREEN}ok:")
            .replace('err:', f"{_ANSI_RED}err:")
        ) + _ANSI_RESET
    else:
        bar = bar_fill + bar_rest

    return f"[{bar}] {info}"


def _clean_for_csv(text) -> str:
    """Loại bỏ ký tự xuống dòng/tab để tránh dính dòng trong CSV"""
    if not text:
        return ''
    return str(text).replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')


def append_to_shared_files(articles: list, data_dir: str):
    """Ghi nối tiếp bài báo vào file chung all_articles.csv + all_articles.jsonl (thread-safe)"""
    # Lọc theo tiêu chí cũ (có nội dung + tiêu đề) để tránh lưu bài dở
    valid = [a for a in articles if a and isinstance(a, dict)
             and (a.get('noi_dung') or a.get('content')) and (a.get('tieu_de') or a.get('title'))]
    if not valid:
        return

    # Chuẩn cột mong muốn
    DEFAULT_FIELDS = ['URL', 'Title', 'Summary', 'Contents', 'Date', 'Author(s)', 'Category', 'Tags']
    saver = DataSaver(output_dir=data_dir)

    with _write_lock:
        # ── JSONL (append, mỗi dòng 1 JSON) ──
        jsonl_path = os.path.join(data_dir, 'all_articles.jsonl')
        with open(jsonl_path, 'a', encoding='utf-8') as f:
            for article in valid:
                norm = DataSaver.normalize_article(article, DEFAULT_FIELDS)
                json.dump(norm, f, ensure_ascii=False)
                f.write('\n')

        # ── CSV (append, header chỉ ghi khi file chưa có) ──
        csv_path = os.path.join(data_dir, 'all_articles.csv')
        write_header = not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0
        with open(csv_path, 'a', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=DEFAULT_FIELDS,
                                    extrasaction='ignore', quoting=csv.QUOTE_ALL)
            if write_header:
                writer.writeheader()
            for article in valid:
                clean = {k: _clean_for_csv(v) for k, v in DataSaver.normalize_article(article, DEFAULT_FIELDS).items()}
                writer.writerow(clean)

    print(f"  📦 Đã ghi thêm {len(valid)} bài → all_articles.jsonl + all_articles.csv")

# ──────────────────────────────────────────────
# Helper: load tất cả data cũ từ data/
# ──────────────────────────────────────────────
def load_existing_data(data_dir: str) -> list:
    """Gộp tất cả JSON checkpoint + CSV đã có thành 1 list"""
    all_data = []
    for fname in sorted(os.listdir(data_dir)):
        path = os.path.join(data_dir, fname)
        try:
            if fname.endswith('.json'):
                with open(path, encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    all_data.extend(data)
            elif fname.endswith('.csv'):
                with open(path, encoding='utf-8-sig', newline='') as f:
                    all_data.extend(list(csv.DictReader(f)))
        except Exception as e:
            print(f"  ⚠️  Bỏ qua {fname}: {e}")
    return all_data


def dedup(data: list) -> list:
    """Dedup theo nội dung (MD5 của 100 từ đầu tiên, lowercase)"""
    seen = set()
    result = []
    for item in data:
        text = item.get('noi_dung', '')
        key = hashlib.md5(' '.join(text.lower().split()[:100]).encode('utf-8')).hexdigest()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def save_csv(data: list, path: str):
    """Lưu CSV với 5 trường đầy đủ, lọc bài cào dở, tránh dính dòng"""
    if not data:
        return
    # Lọc bài hợp lệ (có đủ nội dung + tiêu đề)
    valid = [d for d in data if d and isinstance(d, dict)
             and (d.get('noi_dung') or d.get('content')) and (d.get('tieu_de') or d.get('title'))]
    if not valid:
        return

    # Lưu file với cột chuẩn mới
    DEFAULT_FIELDS = ['URL', 'Title', 'Summary', 'Contents', 'Date', 'Author(s)', 'Category', 'Tags']
    saver = DataSaver(output_dir=os.path.dirname(path) or '.')
    # Sử dụng DataSaver để ghi CSV (sẽ chuẩn hoá và ghi theo DEFAULT_FIELDS)
    saver.save_to_csv(valid, filename=os.path.basename(path))
    print(f"  💾 Đã lưu {len(valid)} bài → {path}")


def save_json(data: list, path: str):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def print_stats(data: list):
    print(f"\n{'='*62}")
    print(f"📊 THỐNG KÊ: {len(data)} bài")
    print(f"{'='*62}")
    counts = Counter(d.get('chu_de', '?') for d in data)
    for cat, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        bar = '█' * (cnt // 30)
        print(f"  {cat:30s}: {cnt:5d}  {bar}")
    print(f"{'='*62}\n")


# ──────────────────────────────────────────────
# Core: cào 1 nguồn toàn bộ categories
# ──────────────────────────────────────────────
def crawl_source_full(source_key: str, max_per_cat: int, crawler: NewspaperCrawler,
                      global_hashes: set, hash_lock: threading.Lock) -> list:
    """Cào toàn bộ chuyên mục của 1 nguồn. Hỗ trợ dừng giữa chừng."""
    source = NEWS_SOURCES.get(source_key)
    if not source:
        return []

    src_name = source['name']
    categories = source.get('categories', [])

    # Resume: bỏ qua chuyên mục đã hoàn thành
    progress = crawler.load_progress(DATA_DIR)
    src_progress = progress.get(source_key, {})
    done_cats = src_progress.get('completed_categories', [])
    if done_cats:
        remaining = [c for c in categories if c not in done_cats]
        print(f"  ♻️  Resume {src_name}: đã xong {len(done_cats)}, còn {len(remaining)} chuyên mục")
        categories = remaining

    print(f"\n{'🔥'*30}")
    print(f"  🔥 Bắt đầu: {src_name} ({len(categories)} chuyên mục)")
    print(f"{'🔥'*30}")

    all_articles = []
    completed_categories = list(done_cats)  # giữ lại đã xong
    _last_aggregate_count = 0  # theo dõi số bài lần lưu aggregate gần nhất

    for cat_idx, category in enumerate(categories, 1):
        # Kiểm tra dừng
        if _stop_event.is_set() or crawler.is_stopped:
            print(f"\n  🛑 Dừng {src_name} tại chuyên mục {category}")
            break

        print(f"\n  📂 [{cat_idx}/{len(categories)}] {src_name}/{category}")

        links = crawler.get_article_links(source_key, category, max_links=max_per_cat)
        if not links:
            print(f"    ⚠️  Không lấy được link nào")
            completed_categories.append(category)
            continue

        total = len(links)
        print(f"  🚀 Cào {total} link với {MAX_WORKERS} luồng...")

        counter = {'ok': 0, 'short': 0, 'dup': 0, 'old': 0, 'error': 0, 'done': 0, 'payload_bytes': 0}
        lock = threading.Lock()
        batch = []
        start_ts = time.monotonic()

        def crawl_one(url):
            if _stop_event.is_set() or crawler.is_stopped:
                return None
            if _stop_event.is_set() or crawler.is_stopped:
                return None
            status, data = crawler.extract_article(url, src_name, category)
            with lock:
                counter['done'] += 1
                counter[status] += 1
                if status == 'ok' and data:
                    counter['payload_bytes'] += len((data.get('noi_dung') or '').encode('utf-8', errors='ignore'))
                done = counter['done']
                progress = _build_progress_line(done, total, start_ts, counter)
                sys.stdout.write('\r    ' + progress[:220])
                sys.stdout.flush()
            # Global dedup
            if data:
                text = data.get('noi_dung', '')
                key = hashlib.md5(' '.join(text.lower().split()[:100]).encode()).hexdigest()
                with hash_lock:
                    if key in global_hashes:
                        return None
                    global_hashes.add(key)
            return data

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(crawl_one, u) for u in links]
            for f in as_completed(futures):
                try:
                    r = f.result()
                    if r:
                        batch.append(r)
                except Exception:
                    pass
                if _stop_event.is_set() or crawler.is_stopped:
                    for remaining_f in futures:
                        remaining_f.cancel()
                    break

        sys.stdout.write('\n')
        sys.stdout.flush()

        print(f"  ✅ {src_name}/{category}: {len(batch)}/{total} bài hợp lệ")
        all_articles.extend(batch)
        completed_categories.append(category)

        # Lưu checkpoint sau mỗi chuyên mục (chỉ JSON + progress)
        crawler.save_checkpoint(all_articles, source_key,
                                completed_categories, DATA_DIR)

        # Ghi nối tiếp vào file chung khi đạt ngưỡng
        if len(all_articles) - _last_aggregate_count >= SAVE_AGGREGATE_EVERY:
            new_batch = all_articles[_last_aggregate_count:]
            append_to_shared_files(new_batch, DATA_DIR)
            _last_aggregate_count = len(all_articles)

        if _stop_event.is_set() or crawler.is_stopped:
            break

    # Ghi phần còn lại chưa được lưu vào file chung
    if len(all_articles) > _last_aggregate_count:
        remaining = all_articles[_last_aggregate_count:]
        append_to_shared_files(remaining, DATA_DIR)

    status_msg = "🛑 ĐÃ DỪNG" if (_stop_event.is_set() or crawler.is_stopped) else "🏁"
    print(f"\n  {status_msg} {src_name}: TỔNG {len(all_articles)} bài")
    return all_articles


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Cào tất cả nguồn, tối đa dữ liệu')
    parser.add_argument('--sources', nargs='+', default=['all'],
                        help='Nguồn cần cào, hoặc "all"')
    parser.add_argument('--max', type=int, default=0,
                        help='Bài tối đa / chuyên mục. Dùng 0 để cào hết toàn bộ trang của chuyên mục')
    parser.add_argument('--fresh', action='store_true',
                        help='Không merge data cũ, crawl từ đầu')
    parser.add_argument('--parallel', type=int, default=SOURCE_PARALLELISM,
                        help='Số nguồn chạy song song')
    args = parser.parse_args()

    sources = list(NEWS_SOURCES.keys()) if 'all' in args.sources else args.sources
    priority = ['vnexpress', 'tuoitre', 'dantri', 'thanhnien', 'vietnamnet',
                'zingnews', 'laodong', 'vneconomy', 'vietnamplus', 'nhandan',
                'qdnd', 'cand', 'baodautu', 'baochinhphu', 'vtv']
    sources = sorted(sources, key=lambda s: priority.index(s) if s in priority else 99)

    # Đăng ký signal handler cho Ctrl+C
    _stop_count = [0]
    def handle_stop(signum, frame):
        _stop_count[0] += 1
        if _stop_count[0] >= 2:
            print("\n\n⚡ Thoát ngay lập tức!")
            sys.exit(1)
        _stop_event.set()
        # Gửi tín hiệu dừng đến tất cả crawler
        for c in _crawlers:
            c.request_stop()
        print("\n⚠️  Đang dừng... Nhấn Ctrl+C lần nữa để thoát ngay (không lưu)")

    signal.signal(signal.SIGINT, handle_stop)

    print("""
╔══════════════════════════════════════════════════════════════╗
║           🚀 CRAWL ALL - TỐI ĐA DỮ LIỆU 🚀                 ║
╚══════════════════════════════════════════════════════════════╝""")
    print(f"  Nguồn    : {', '.join(sources)}")
    max_label = 'không giới hạn' if args.max <= 0 else f'{args.max} bài'
    print(f"  Max/cat  : {max_label}")
    print(f"  Song song: {args.parallel} nguồn cùng lúc")
    print(f"  Fresh    : {args.fresh}")
    if args.max > 0:
        est_total = sum(len(NEWS_SOURCES.get(s, {}).get('categories', [])) for s in sources) * args.max * 0.6
        print(f"  Ước tính : ~{int(est_total):,} bài (sau lọc)")
    else:
        print("  Ước tính : không giới hạn, phụ thuộc số trang thực tế của từng nguồn")
    print(f"  ℹ️  Nhấn Ctrl+C để dừng giữa chừng (sẽ tự lưu)")
    print()

    # Xóa progress cũ + file chung cũ nếu --fresh
    if args.fresh:
        progress_path = os.path.join(DATA_DIR, 'progress.json')
        if os.path.exists(progress_path):
            os.remove(progress_path)
            print("  🗑️  Đã xóa progress.json (chế độ fresh)")
        for old_file in ['all_articles.csv', 'all_articles.jsonl', 'all_articles.json']:
            old_path = os.path.join(DATA_DIR, old_file)
            if os.path.exists(old_path):
                os.remove(old_path)
                print(f"  🗑️  Đã xóa {old_file} (chế độ fresh)")

    # Load data cũ (để dedup xuyên suốt)
    global_hashes: set = set()
    hash_lock = threading.Lock()

    existing = []
    if not args.fresh:
        print("📂 Đang load data cũ để dedup...")
        existing = load_existing_data(DATA_DIR)
        for item in existing:
            text = item.get('noi_dung', '')
            key = hashlib.md5(' '.join(text.lower().split()[:100]).encode()).hexdigest()
            global_hashes.add(key)
        print(f"  ✅ Đã load {len(existing)} bài cũ, {len(global_hashes)} hash\n")

    start_time = datetime.now()
    new_articles = []
    new_lock = threading.Lock()

    def run_source(src_key):
        crawler = NewspaperCrawler(use_mobile=False)
        _crawlers.append(crawler)
        with hash_lock:
            crawler.content_hashes = global_hashes
        articles = crawl_source_full(src_key, args.max, crawler, global_hashes, hash_lock)
        if articles:
            with new_lock:
                new_articles.extend(articles)
                print(f"\n  📦 TỔNG MỚI ĐẾN NAY: {len(new_articles)} bài\n")
        return articles

    # Chạy song song theo nhóm
    with ThreadPoolExecutor(max_workers=args.parallel) as executor:
        futures = {executor.submit(run_source, s): s for s in sources}
        for f in as_completed(futures):
            src = futures[f]
            try:
                f.result()
            except Exception as e:
                print(f"❌ Lỗi {src}: {e}")
            # Nếu dừng, cancel remaining
            if _stop_event.is_set():
                for remaining_f in futures:
                    remaining_f.cancel()
                break

    # Lọc bài cào dở
    valid_new = [a for a in new_articles
                 if a and isinstance(a, dict)
                 and a.get('noi_dung') and a.get('tieu_de')]
    removed = len(new_articles) - len(valid_new)
    if removed:
        print(f"  🗑️  Đã lọc {removed} bài không hợp lệ / cào dở")

    # Merge + dedup toàn bộ
    print(f"\n{'='*62}")
    print(f"🧹 Merge + dedup toàn bộ data...")
    all_data = existing + valid_new if not args.fresh else valid_new
    before = len(all_data)
    all_data = dedup(all_data)
    print(f"  {before} → {len(all_data)} bài (sau dedup)")

    # Lưu file kết quả cuối (JSON đầy đủ để tham khảo)
    out_json = os.path.join(DATA_DIR, 'all_articles.json')
    save_json(all_data, out_json)

    # Ghi đè file CSV chung (dedup sạch, tránh trùng lặp nếu resume)
    out_csv = os.path.join(DATA_DIR, 'all_articles.csv')
    save_csv(all_data, out_csv)

    duration = (datetime.now() - start_time).total_seconds()
    print_stats(all_data)

    status = "🛑 ĐÃ DỪNG" if _stop_event.is_set() else "🎉 HOÀN THÀNH"
    print(f"{status}! {len(all_data)} bài trong {duration/60:.1f} phút")
    print(f"📁 CSV  : {out_csv}")
    print(f"📁 JSON : {out_json}")
    print(f"📁 JSONL: {os.path.join(DATA_DIR, 'all_articles.jsonl')}")

    if _stop_event.is_set():
        print(f"\n💡 Chạy lại để RESUME (sẽ tự bỏ qua chuyên mục đã cào)")
    else:
        # Xóa progress khi hoàn thành
        progress_path = os.path.join(DATA_DIR, 'progress.json')
        if os.path.exists(progress_path):
            os.remove(progress_path)

    # Xóa STOP.flag nếu có
    try:
        if os.path.exists(STOP_FLAG_FILE):
            os.remove(STOP_FLAG_FILE)
    except Exception:
        pass


if __name__ == '__main__':
    main()
