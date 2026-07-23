#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 KIỂM TRA ENCODING TIẾNG VIỆT
=================================
Kiểm tra toàn bộ pipeline: crawl → extract → clean → save
đảm bảo tiếng Việt (dấu) hiển thị đúng ở mọi bước.
"""
import sys, os, json, csv, tempfile, re
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from crawlers.newspaper_crawler import NewspaperCrawler
from config import NEWS_SOURCES

# Ký tự tiếng Việt đặc biệt cần kiểm tra
VIET_CHARS = set('àáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ'
                 'ÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ')

def has_vietnamese(text: str) -> bool:
    """Kiểm tra text có chứa ký tự tiếng Việt (dấu)"""
    return bool(set(text) & VIET_CHARS)

def has_mojibake(text: str) -> bool:
    """Kiểm tra text có bị lỗi encoding (mojibake) - chỉ kiểm tra nội dung thực"""
    # Chỉ kiểm tra khi text dài (nội dung bài báo), bỏ qua source code / comment
    # Đếm số ký tự mojibake Latin-1 phổ biến xuất hiện LIÊN TIẾP
    # Ví dụ: "Ã¡" là 2 ký tự liên tiếp đều thuộc range latin-1 extended
    count_suspicious = 0
    for i in range(len(text) - 1):
        c1, c2 = ord(text[i]), ord(text[i+1])
        # Cặp ký tự Ã + [€-¿] hoặc Ä + [€-¿] hoặc Æ + [€-¿]
        if c1 in (0xC3, 0xC4, 0xC6) and 0x80 <= c2 <= 0xBF:
            count_suspicious += 1
    # Nếu có >5 cặp → nhiều khả năng bị mojibake
    if count_suspicious > 5:
        return True
    return False

def test_crawl_encoding():
    """Test 1: Crawl bài báo và kiểm tra encoding tiếng Việt"""
    print("=" * 60)
    print("🔍 TEST 1: CRAWL & ENCODING TIẾNG VIỆT")
    print("=" * 60)
    
    crawler = NewspaperCrawler(use_mobile=True)
    
    # Test trên 5 nguồn đa dạng
    test_sources = ['vnexpress', 'dantri', 'tuoitre', 'thanhnien', 'vietnamnet']
    results = []
    
    for sk in test_sources:
        src = NEWS_SOURCES.get(sk)
        if not src:
            continue
        cat = src['categories'][0]
        name = src['name']
        
        print(f"\n  📰 {name}/{cat}...", end=' ', flush=True)
        
        links = crawler.get_article_links(sk, cat, max_links=3)
        if not links:
            print("❌ Không lấy được link")
            results.append((name, 'NO_LINKS', False))
            continue
        
        # Lấy bài đầu tiên
        status, data = crawler.extract_article(links[0], name, cat)
        if status not in ('ok',) or not data:
            # Thử bài tiếp (short/dup không phải lỗi encoding)
            for alt_link in links[1:]:
                status, data = crawler.extract_article(alt_link, name, cat)
                if status == 'ok' and data:
                    break
        
        if status != 'ok' or not data:
            print(f"⚠️  Không trích xuất được bài (status={status})")
            results.append((name, status, False))
            continue
        
        title = data.get('tieu_de', '')
        content = data.get('noi_dung', '')
        
        # Kiểm tra encoding
        has_vn_title = has_vietnamese(title)
        has_vn_content = has_vietnamese(content)
        has_moji_title = has_mojibake(title)
        has_moji_content = has_mojibake(content)
        
        ok = (has_vn_title or has_vn_content) and not has_moji_title and not has_moji_content
        
        if ok:
            print(f"✅ encoding OK")
            # Hiển thị mẫu tiếng Việt
            sample = title[:80] if title else content[:80]
            print(f"     → \"{sample}...\"")
        else:
            issues = []
            if not has_vn_title and not has_vn_content:
                issues.append("không có ký tự tiếng Việt")
            if has_moji_title:
                issues.append(f"tiêu đề bị mojibake: {title[:50]}")
            if has_moji_content:
                issues.append(f"nội dung bị mojibake: {content[:50]}")
            print(f"❌ {'; '.join(issues)}")
        
        results.append((name, 'ok', ok))
    
    passed = sum(1 for _, _, ok in results if ok)
    print(f"\n  → Kết quả: {passed}/{len(results)} nguồn encoding OK")
    return passed == len(results)


def test_save_encoding():
    """Test 2: Kiểm tra encoding khi lưu CSV/JSON"""
    print("\n" + "=" * 60)
    print("🔍 TEST 2: LƯU FILE CSV/JSON - ENCODING")
    print("=" * 60)
    
    # Dữ liệu mẫu với tiếng Việt đầy đủ dấu
    test_data = [
        {
            'chu_de': 'thời-sự',
            'tieu_de': 'Đại hội Đảng toàn quốc lần thứ XIV: Những quyết sách quan trọng',
            'noi_dung': 'Việt Nam đang trên đà phát triển mạnh mẽ. Chủ tịch nước Lương Cường '
                        'đã có bài phát biểu quan trọng tại Đại hội. Các đại biểu đã thảo luận '
                        'về nhiều vấn đề kinh tế - xã hội, quốc phòng - an ninh, đối ngoại. '
                        'Người dân cả nước hướng về Đại hội với niềm tin và kỳ vọng lớn lao.',
            'nguon': 'VnExpress',
            'link': 'https://vnexpress.net/test-123.html'
        },
        {
            'chu_de': 'giáo-dục',
            'tieu_de': 'Học sinh Việt Nam đạt huy chương vàng Olympic Toán học quốc tế',
            'noi_dung': 'Đoàn học sinh Việt Nam xuất sắc giành được 3 huy chương vàng, '
                        '2 huy chương bạc tại kỳ thi Olympic Toán học quốc tế năm 2026. '
                        'Thầy Nguyễn Văn Ất, trưởng đoàn, chia sẻ: "Các em đã nỗ lực '
                        'rất nhiều. Đây là thành quả xứng đáng." Phụ huynh và giáo viên '
                        'đều rất tự hào về kết quả này.',
            'nguon': 'Dân Trí',
            'link': 'https://dantri.com.vn/test-456.htm'
        }
    ]
    
    all_ok = True
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # ── Test CSV (utf-8-sig cho Excel) ──
        csv_path = os.path.join(tmpdir, 'test_vn.csv')
        fieldnames = ['chu_de', 'tieu_de', 'noi_dung', 'nguon', 'link']
        
        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(test_data)
        
        # Đọc lại và kiểm tra
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        csv_ok = True
        for i, row in enumerate(rows):
            orig = test_data[i]
            for field in fieldnames:
                if row.get(field) != orig.get(field):
                    print(f"  ❌ CSV mismatch [{field}]: '{row.get(field)[:30]}...' != '{orig.get(field)[:30]}...'")
                    csv_ok = False
                elif has_mojibake(row.get(field, '')):
                    print(f"  ❌ CSV mojibake [{field}]: '{row.get(field)[:50]}'")
                    csv_ok = False
        
        if csv_ok:
            print(f"  ✅ CSV: encoding OK (utf-8-sig, {os.path.getsize(csv_path)} bytes)")
            # Kiểm tra BOM
            with open(csv_path, 'rb') as f:
                bom = f.read(3)
            if bom == b'\xef\xbb\xbf':
                print(f"     → BOM (EF BB BF) present → Excel sẽ hiển thị đúng tiếng Việt")
            else:
                print(f"     ⚠️  Thiếu BOM → Excel có thể hiển thị sai dấu")
                csv_ok = False
        all_ok = all_ok and csv_ok
        
        # ── Test JSON (utf-8, ensure_ascii=False) ──
        json_path = os.path.join(tmpdir, 'test_vn.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)
        
        with open(json_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        
        json_ok = True
        for i, item in enumerate(loaded):
            orig = test_data[i]
            for field in fieldnames:
                if item.get(field) != orig.get(field):
                    print(f"  ❌ JSON mismatch [{field}]")
                    json_ok = False
        
        if json_ok:
            # Kiểm tra file không chứa \\uXXXX escape
            with open(json_path, 'r', encoding='utf-8') as f:
                raw = f.read()
            if '\\u' in raw:
                print(f"  ⚠️  JSON chứa unicode escape (\\uXXXX) thay vì ký tự thật")
                json_ok = False
            else:
                print(f"  ✅ JSON: encoding OK (utf-8, non-escaped, {os.path.getsize(json_path)} bytes)")
                # Kiểm tra ký tự Việt xuất hiện trực tiếp trong file
                if 'Đại hội' in raw and 'Việt Nam' in raw:
                    print(f"     → Tiếng Việt hiển thị trực tiếp trong file ✓")
        all_ok = all_ok and json_ok

        # ── Test JSONL ──
        jsonl_path = os.path.join(tmpdir, 'test_vn.jsonl')
        with open(jsonl_path, 'w', encoding='utf-8') as f:
            for item in test_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            lines = [json.loads(line) for line in f if line.strip()]
        
        jsonl_ok = len(lines) == len(test_data)
        for i, item in enumerate(lines):
            for field in fieldnames:
                if item.get(field) != test_data[i].get(field):
                    jsonl_ok = False
        
        if jsonl_ok:
            print(f"  ✅ JSONL: encoding OK ({os.path.getsize(jsonl_path)} bytes)")
        else:
            print(f"  ❌ JSONL: encoding lỗi!")
        all_ok = all_ok and jsonl_ok
    
    return all_ok


def test_checkpoint_encoding():
    """Test 3: Kiểm tra checkpoint JSON file encoding"""
    print("\n" + "=" * 60)
    print("🔍 TEST 3: CHECKPOINT FILE ENCODING")
    print("=" * 60)
    
    # Kiểm tra các checkpoint đã tồn tại trong Tool/data/
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Tool', 'data')
    if not os.path.exists(data_dir):
        print(f"  ⚠️  Thư mục {data_dir} không tồn tại, bỏ qua test này")
        return True
    
    checkpoint_files = [f for f in os.listdir(data_dir) if f.startswith('checkpoint_') and f.endswith('.json')]
    
    if not checkpoint_files:
        print(f"  ⚠️  Không tìm thấy checkpoint files, bỏ qua")
        return True
    
    all_ok = True
    for fname in sorted(checkpoint_files):
        fpath = os.path.join(data_dir, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not data:
                print(f"  ⚠️  {fname}: rỗng")
                continue

            # Kiểm tra encoding trong nội dung
            has_vn = False
            has_moji = False
            sample = ''
            for item in data[:3]:  # Chỉ kiểm tra 3 bài đầu
                for field in ['tieu_de', 'noi_dung', 'chu_de', 'nguon']:
                    val = item.get(field, '')
                    if has_vietnamese(val):
                        has_vn = True
                        if not sample and field == 'tieu_de':
                            sample = val[:60]
                    if has_mojibake(val):
                        has_moji = True
            
            if has_moji:
                print(f"  ❌ {fname}: bị mojibake!")
                all_ok = False
            elif has_vn:
                print(f"  ✅ {fname}: {len(data)} bài, encoding OK")
                if sample:
                    print(f"     → \"{sample}...\"")
            else:
                print(f"  ⚠️  {fname}: {len(data)} bài, không thấy tiếng Việt có dấu")
        
        except UnicodeDecodeError as e:
            print(f"  ❌ {fname}: UnicodeDecodeError: {e}")
            all_ok = False
        except json.JSONDecodeError as e:
            print(f"  ❌ {fname}: JSON lỗi: {e}")
            all_ok = False
        except Exception as e:
            print(f"  ❌ {fname}: {e}")
            all_ok = False
    
    return all_ok


def test_source_code_encoding():
    """Test 4: Kiểm tra encoding của source code files"""
    print("\n" + "=" * 60)
    print("🔍 TEST 4: SOURCE CODE FILE ENCODING")
    print("=" * 60)
    
    root = os.path.dirname(os.path.dirname(__file__))
    py_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip __pycache__, .git, node_modules
        dirnames[:] = [d for d in dirnames if d not in ('__pycache__', '.git', 'node_modules', 'data')]
        for fn in filenames:
            if fn.endswith('.py'):
                py_files.append(os.path.join(dirpath, fn))
    
    all_ok = True
    for fpath in sorted(py_files):
        relpath = os.path.relpath(fpath, root)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Kiểm tra file có ký tự tiếng Việt
            if has_vietnamese(content):
                # Kiểm tra có khai báo encoding header
                first_lines = content.split('\n')[:3]
                has_coding = any('coding' in line and 'utf-8' in line for line in first_lines)
                
                if has_mojibake(content):
                    print(f"  ❌ {relpath}: chứa tiếng Việt bị mojibake!")
                    all_ok = False
                elif not has_coding:
                    print(f"  ⚠️  {relpath}: chứa tiếng Việt nhưng thiếu # -*- coding: utf-8 -*-")
                else:
                    pass  # OK, có VN + có coding header
            
        except UnicodeDecodeError:
            print(f"  ❌ {relpath}: không đọc được bằng UTF-8!")
            all_ok = False
    
    if all_ok:
        print(f"  ✅ Tất cả {len(py_files)} file .py đọc UTF-8 OK")
    
    return all_ok


def test_console_encoding():
    """Test 5: Kiểm tra console có hiển thị tiếng Việt đúng không"""
    print("\n" + "=" * 60)
    print("🔍 TEST 5: CONSOLE OUTPUT ENCODING")
    print("=" * 60)
    
    test_strings = [
        "Tiếng Việt có dấu: à á ả ã ạ ă ắ ằ ẳ ẵ ặ â ấ ầ ẩ ẫ ậ",
        "Đặc biệt: đ Đ ê ế ề ể ễ ệ ô ố ồ ổ ỗ ộ ơ ớ ờ ở ỡ ợ ư ứ ừ ử ữ ự",
        "Emoji: 🇻🇳 📰 🔥 ✅ ❌ ⚠️ 💾 📊",
        "Nguồn: VnExpress, Dân Trí, Tuổi Trẻ, Thanh Niên, Lao Động",
        "Chuyên mục: kinh-doanh, thời-sự, giáo-dục, khoa-học-công-nghệ",
    ]
    
    ok = True
    for s in test_strings:
        try:
            print(f"  → {s}")
        except UnicodeEncodeError as e:
            print(f"  ❌ UnicodeEncodeError: {e}")
            ok = False
    
    # Kiểm tra sys.stdout encoding
    stdout_enc = sys.stdout.encoding or 'unknown'
    print(f"\n  sys.stdout.encoding = {stdout_enc}")
    if stdout_enc.lower() in ('utf-8', 'utf8', 'cp65001'):
        print(f"  ✅ Console encoding OK")
    else:
        print(f"  ⚠️  Console encoding là {stdout_enc} (không phải UTF-8)")
        print(f"     → Có thể gặp lỗi hiển thị tiếng Việt trên Windows CMD")
        print(f"     → Khuyến nghị: dùng PowerShell hoặc chạy 'chcp 65001'")
    
    return ok


def test_response_encoding():
    """Test 6: Kiểm tra response encoding từ các trang báo"""
    print("\n" + "=" * 60)
    print("🔍 TEST 6: RESPONSE ENCODING TỪ CÁC BÁO")
    print("=" * 60)
    
    import requests as req
    
    test_urls = {
        'VnExpress': 'https://vnexpress.net/thoi-su',
        'Dân Trí': 'https://dantri.com.vn/thoi-su.htm',
        'Tuổi Trẻ': 'https://tuoitre.vn/thoi-su.htm',
        'Thanh Niên': 'https://thanhnien.vn/thoi-su',
        'VietnamNet': 'https://vietnamnet.vn/thoi-su',
    }
    
    all_ok = True
    for name, url in test_urls.items():
        try:
            resp = req.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            # Kiểm tra Content-Type header
            ct = resp.headers.get('Content-Type', '')
            declared_enc = 'unknown'
            if 'charset=' in ct:
                declared_enc = ct.split('charset=')[-1].strip().lower()
            
            # Kiểm tra apparent encoding
            apparent = (resp.apparent_encoding or 'unknown').lower()
            
            # Kiểm tra meta charset trong HTML
            meta_enc = 'unknown'
            if b'charset=' in resp.content[:2000]:
                m = re.search(rb'charset=["\']?([^"\'\s;>]+)', resp.content[:2000])
                if m:
                    meta_enc = m.group(1).decode('ascii', errors='replace').lower()
            
            # Kiểm tra nội dung có tiếng Việt đúng không
            text = resp.content.decode('utf-8', errors='replace')
            has_vn = has_vietnamese(text[:5000])
            
            status = '✅' if has_vn and ('utf' in declared_enc or 'utf' in meta_enc or 'utf' in apparent) else '⚠️'
            if not has_vn:
                status = '❌'
                all_ok = False
            
            print(f"  {status} {name:15s} | header: {declared_enc:10s} | meta: {meta_enc:10s} | "
                  f"apparent: {apparent:10s} | VN: {'✓' if has_vn else '✗'}")
            
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            all_ok = False
    
    return all_ok


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   🔍 KIỂM TRA ENCODING TIẾNG VIỆT - TOÀN DIỆN 🔍      ║")
    print("╚══════════════════════════════════════════════════════════╝")
    
    results = {}
    
    results['console']    = test_console_encoding()
    results['source']     = test_source_code_encoding()
    results['response']   = test_response_encoding()
    results['crawl']      = test_crawl_encoding()
    results['save']       = test_save_encoding()
    results['checkpoint'] = test_checkpoint_encoding()
    
    print("\n" + "=" * 60)
    print("📊 TỔNG KẾT ENCODING")
    print("=" * 60)
    
    labels = {
        'console': 'Console output',
        'source': 'Source code files',
        'response': 'HTTP response encoding',
        'crawl': 'Crawl & extract articles',
        'save': 'Save CSV/JSON/JSONL',
        'checkpoint': 'Checkpoint files',
    }
    
    total_pass = 0
    total = len(results)
    for key, ok in results.items():
        icon = '✅' if ok else '❌'
        print(f"  {icon} {labels[key]}")
        if ok:
            total_pass += 1
    
    print(f"\n  → Kết quả: {total_pass}/{total} PASS")
    if total_pass == total:
        print("  🎉 TẤT CẢ ENCODING TEST ĐỀU PASS!")
    else:
        print("  ⚠️  CÓ LỖI ENCODING CẦN SỬA!")
    
    sys.exit(0 if total_pass == total else 1)
