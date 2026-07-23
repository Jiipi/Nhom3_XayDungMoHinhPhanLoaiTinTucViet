# -*- coding: utf-8 -*-
"""
Test tổng hợp: kiểm tra toàn bộ 15 nguồn báo
  1. Kiểm tra thư viện cần thiết
  2. Lấy link bài viết (1 chuyên mục / nguồn, tối đa 5 link)
  3. Trích xuất nội dung + kiểm tra encoding UTF-8
  4. Kiểm tra 5 trường dữ liệu đầu ra
  5. Xử lý lỗi mạng

Chạy:  python tests/test_all.py
       python tests/test_all.py --sources vnexpress dantri
"""
import sys
import os
import time
import argparse

# ── Thêm project root vào path ──────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  PHẦN 1: KIỂM TRA THƯ VIỆN                                        ║
# ╚══════════════════════════════════════════════════════════════════════╝
REQUIRED_LIBS = {
    'requests':       'requests',
    'bs4':            'beautifulsoup4',
    'lxml':           'lxml',
    'newspaper':      'newspaper3k',
}

def check_libraries() -> bool:
    """Kiểm tra tất cả thư viện bắt buộc đã cài chưa."""
    print("=" * 60)
    print("📦  KIỂM TRA THƯ VIỆN")
    print("=" * 60)
    ok = True
    for module, pip_name in REQUIRED_LIBS.items():
        try:
            __import__(module)
            print(f"  ✅ {pip_name}")
        except ImportError:
            print(f"  ❌ {pip_name}  →  pip install {pip_name}")
            ok = False
    if ok:
        print("  → Tất cả thư viện OK\n")
    else:
        print("\n  ⚠️  Thiếu thư viện! Chạy:  pip install -r requirements.txt\n")
    return ok


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  PHẦN 2 + 3: LẤY LINK + TRÍCH XUẤT BÀI + ENCODING                 ║
# ╚══════════════════════════════════════════════════════════════════════╝
EXPECTED_FIELDS = {'chu_de', 'tieu_de', 'noi_dung', 'nguon', 'link'}


def test_source(crawler, source_key: str, source_info: dict) -> dict:
    """
    Test 1 nguồn báo:
      - Lấy link (max 5)
      - Trích xuất bài đầu tiên
      - Kiểm tra encoding + 5 trường

    Returns:
        dict với kết quả: links, article_ok, encoding_ok, fields_ok, error
    """
    cat = source_info['categories'][0]
    result = {
        'name': source_info['name'],
        'category': cat,
        'links': 0,
        'article_ok': False,
        'encoding_ok': False,
        'fields_ok': False,
        'words': 0,
        'error': None,
    }

    # ── Bước 1: lấy link ────────────────────────────────────────────────
    try:
        links = crawler.get_article_links(source_key, cat, max_links=5)
        result['links'] = len(links)
    except Exception as e:
        result['error'] = f"Lỗi lấy link: {e}"
        return result

    if not links:
        result['error'] = "Không lấy được link nào"
        return result

    # ── Bước 2: trích xuất bài (thử tối đa 3 bài) ──────────────────────
    for url in links[:3]:
        try:
            status, data = crawler.extract_article(url, source_info['name'], cat)
        except Exception as e:
            result['error'] = f"Exception trích xuất: {e}"
            continue

        if status == 'ok' and data:
            # Kiểm tra 5 trường
            result['fields_ok'] = EXPECTED_FIELDS.issubset(data.keys())

            text = data.get('noi_dung', '')
            result['words'] = len(text.split())

            # Kiểm tra encoding UTF-8
            try:
                text.encode('utf-8')
                data.get('tieu_de', '').encode('utf-8')
                result['encoding_ok'] = True
            except UnicodeEncodeError as ue:
                result['error'] = f"Lỗi encoding: {ue}"

            result['article_ok'] = True
            break
        elif status == 'network_error':
            result['error'] = "Lỗi mạng khi trích xuất"
            break  # Không thử thêm nếu mạng lỗi
        # status = short/old/dup → thử bài tiếp
    else:
        if result['error'] is None:
            result['error'] = "Không trích xuất được bài nào (short/old/dup)"

    return result


def run_all_tests(source_keys: list = None) -> bool:
    """
    Chạy test cho tất cả (hoặc các nguồn chỉ định).

    Returns:
        True nếu tất cả nguồn pass.
    """
    from crawlers.newspaper_crawler import NewspaperCrawler
    from config import NEWS_SOURCES

    crawler = NewspaperCrawler()
    keys = source_keys or list(NEWS_SOURCES.keys())

    results = {}
    for key in keys:
        if key not in NEWS_SOURCES:
            print(f"  ⚠️  '{key}' không tồn tại trong config → bỏ qua")
            continue

        src = NEWS_SOURCES[key]
        print(f"\n{'─' * 60}")
        print(f"🧪  {src['name']}  /  {src['categories'][0]}")
        print(f"{'─' * 60}")

        r = test_source(crawler, key, src)
        results[key] = r

        # Hiển thị ngắn gọn
        parts = []
        parts.append(f"links={r['links']}")
        parts.append("article=✅" if r['article_ok'] else "article=❌")
        parts.append("encoding=✅" if r['encoding_ok'] else "encoding=❌")
        parts.append("fields=✅" if r['fields_ok'] else "fields=❌")
        if r['words']:
            parts.append(f"words={r['words']}")
        print(f"  → {', '.join(parts)}")
        if r['error']:
            print(f"  ⚠️  {r['error']}")

        time.sleep(1)

    # ── Tổng kết ─────────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("📊  TỔNG KẾT")
    print(f"{'=' * 60}")

    passed = 0
    total = len(results)
    for key, r in results.items():
        ok = r['article_ok'] and r['encoding_ok'] and r['fields_ok']
        if ok:
            passed += 1
            status = f"✅  {r['words']} từ"
        elif r['links'] > 0 and not r['article_ok']:
            status = f"⚠️  Có link nhưng không trích xuất được"
        elif r['error'] and 'mạng' in (r['error'] or '').lower():
            status = f"🌐  Lỗi mạng"
        else:
            status = f"❌  {r['error'] or 'Thất bại'}"
        print(f"  {r['name']:20s} : {status}")

    print(f"\n  ✅ Passed: {passed}/{total}")
    if passed < total:
        print(f"  ❌ Failed: {total - passed}/{total}")

    return passed == total


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  MAIN                                                              ║
# ╚══════════════════════════════════════════════════════════════════════╝
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test tổng hợp 15 nguồn báo')
    parser.add_argument('--sources', nargs='+', default=None,
                        help='Chỉ test các nguồn cụ thể (vd: vnexpress dantri)')
    args = parser.parse_args()

    # 1. Kiểm tra thư viện
    if not check_libraries():
        sys.exit(1)

    # 2. Test lấy link + trích xuất + encoding
    ok = run_all_tests(args.sources)
    sys.exit(0 if ok else 1)
