# -*- coding: utf-8 -*-
"""
Test dừng giữa chừng (stop) + lưu/đọc checkpoint + resume.

Chạy:  python tests/test_stop_resume.py
"""
import os
import sys
import json
import glob
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlers.newspaper_crawler import NewspaperCrawler
from utils.path_utils import get_data_dir

DATA_DIR = str(get_data_dir(create=True))
SRC_KEY  = '__test_stop__'

# ═══════════════════════════════════════════════════════════════════════
#  TEST 1: Stop flag
# ═══════════════════════════════════════════════════════════════════════
def test_stop_flag():
    print("=" * 60)
    print("TEST 1: Stop flag")
    print("=" * 60)

    c = NewspaperCrawler()
    assert not c.is_stopped, "is_stopped phải False ban đầu"
    print("  ✅ is_stopped = False (ban đầu)")

    c.request_stop()
    assert c.is_stopped, "is_stopped phải True sau request_stop()"
    print("  ✅ is_stopped = True (sau request_stop)")

    articles = c.crawl_category('vnexpress', 'thoi-su', 3)
    assert len(articles) == 0, "crawl_category khi đã stop phải trả về rỗng"
    print("  ✅ crawl_category → 0 bài khi đã stop")

# ═══════════════════════════════════════════════════════════════════════
#  TEST 2: STOP.flag file
# ═══════════════════════════════════════════════════════════════════════
def test_stop_file():
    print("\n" + "=" * 60)
    print("TEST 2: STOP.flag file")
    print("=" * 60)

    c = NewspaperCrawler()
    flag_path = c.STOP_FLAG_FILE

    # Tạo file flag
    with open(flag_path, 'w') as f:
        f.write('stop')
    assert c.is_stopped, "is_stopped phải True khi STOP.flag tồn tại"
    print("  ✅ Phát hiện STOP.flag → is_stopped = True")

    # Dọn dẹp
    if os.path.exists(flag_path):
        os.remove(flag_path)
    print("  ✅ Đã xóa STOP.flag")

# ═══════════════════════════════════════════════════════════════════════
#  TEST 3: Checkpoint save + load progress
# ═══════════════════════════════════════════════════════════════════════
def test_checkpoint():
    print("\n" + "=" * 60)
    print("TEST 3: Checkpoint save + load progress")
    print("=" * 60)

    c = NewspaperCrawler()
    test_articles = [
        {'chu_de': 'test', 'tieu_de': 'Bài 1', 'noi_dung': 'Nội dung 1', 'nguon': 'Test', 'link': 'http://t.co/1'},
        {'chu_de': 'test', 'tieu_de': 'Bài 2', 'noi_dung': 'Nội dung 2', 'nguon': 'Test', 'link': 'http://t.co/2'},
        None,               # bài cào dở → lọc
        {'chu_de': 'test'},  # thiếu trường → lọc
    ]

    c.save_checkpoint(test_articles, SRC_KEY, ['cat1', 'cat2'], DATA_DIR)

    # Kiểm tra progress
    progress = c.load_progress(DATA_DIR)
    src_p = progress.get(SRC_KEY, {})
    assert src_p.get('total_articles') == 2, f"expected 2, got {src_p.get('total_articles')}"
    assert src_p.get('completed_categories') == ['cat1', 'cat2']
    print(f"  ✅ progress.json: 2 bài, 2 chuyên mục")

    # Kiểm tra file checkpoint
    json_files = glob.glob(os.path.join(DATA_DIR, f'checkpoint_{SRC_KEY}_*.json'))
    csv_files  = glob.glob(os.path.join(DATA_DIR, f'checkpoint_{SRC_KEY}_*.csv'))
    assert len(json_files) >= 1, "Thiếu file JSON checkpoint"
    assert len(csv_files) >= 1,  "Thiếu file CSV checkpoint"

    with open(json_files[-1], 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert len(data) == 2, f"JSON phải có 2 bài, got {len(data)}"
    assert set(data[0].keys()) == {'chu_de', 'tieu_de', 'noi_dung', 'nguon', 'link'}
    print(f"  ✅ JSON checkpoint: 2 bài, 5 trường")

    import csv as csv_mod
    with open(csv_files[-1], 'r', encoding='utf-8-sig') as f:
        reader = csv_mod.DictReader(f)
        rows = list(reader)
    assert len(rows) == 2
    assert set(reader.fieldnames) == {'chu_de', 'tieu_de', 'noi_dung', 'nguon', 'link'}
    print(f"  ✅ CSV checkpoint: 2 bài, 5 trường")

    # ── Cleanup ──
    for fp in json_files + csv_files:
        os.remove(fp)
    # Xóa key test khỏi progress
    progress.pop(SRC_KEY, None)
    progress_path = os.path.join(DATA_DIR, 'progress.json')
    if progress:
        with open(progress_path, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
    elif os.path.exists(progress_path):
        os.remove(progress_path)
    print("  ✅ Cleanup xong")

# ═══════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    try:
        test_stop_flag()
        test_stop_file()
        test_checkpoint()
        print(f"\n{'=' * 60}")
        print("✅  TẤT CẢ TEST PASSED!")
        print(f"{'=' * 60}")
    except AssertionError as e:
        print(f"\n❌ ASSERTION FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ LỖI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
