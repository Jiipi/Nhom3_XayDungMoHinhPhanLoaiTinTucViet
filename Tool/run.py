#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 SCRIPT TỰ ĐỘNG CÀO BÁO
===========================
Tự động cài đặt thư viện và chạy crawler

Sử dụng:
    python run.py
    
Sau đó chọn chế độ và nhập số lượng bài khi được hỏi.
"""

import subprocess
import sys
import os

def install_requirements():
    """Tự động cài đặt các thư viện cần thiết"""
    print("=" * 60)
    print("📦 ĐANG CÀI ĐẶT THƯ VIỆN...")
    print("=" * 60)
    
    # Danh sách các thư viện cốt lõi cần thiết để chạy Tool
    requirements = [
        'newspaper3k',    # Dùng để bóc tách nội dung văn bản báo
        'beautifulsoup4', # Dùng để parse HTML, lấy danh sách link bài viết
        'lxml',           # Dùng hỗ trợ parse xml/html siêu tốc
        'requests',       # Dùng để khởi tạo HTTP Request (gọi internet)
        'pandas',         # Dùng xử lý dữ liệu dataframe sau khi cào
        'lxml_html_clean' # Tiện ích dọn dẹp HTML bẩn
    ]
    
    for package in requirements:
        print(f"\n📥 Cài đặt {package}...")
        try:
            # subprocess mở cổng console, chạy pip install với cờ -q (chạy im lặng ẩn log)
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package, '-q'])
            print(f"✅ Đã cài {package}")
        except subprocess.CalledProcessError:
            # Nếu cài bằng pip hỏng mạng thì in log bỏ qua qua lỗi, để Tool khỏi tắt nẻo
            print(f"⚠️  Lỗi khi cài {package}, thử tiếp...")
    
    print("\n✅ Hoàn thành cài đặt thư viện!\n")

def run_crawler():
    """Chạy crawler với tham số từ người dùng"""
    print("=" * 60)
    print("🚀 TOOL CÀO BÁO TỐC ĐỘ CAO")
    print("=" * 60)
    print()
    print("📋 CHỌN CHẾ ĐỘ:")
    print()
    print("  ── CÀO THEO NGUỒN (14 nguồn) ──")
    print("  1.  VnExpress       (18 chuyên mục)")
    print("  2.  Thanh Niên      (16 chuyên mục)")
    print("  3.  Tuổi Trẻ        (17 chuyên mục)")
    print("  4.  VietnamNet      (23 chuyên mục)")
    print("  5.  Dân Trí         (18 chuyên mục)")
    print("  6.  Lao Động        (18 chuyên mục)")
    print("  7.  VnEconomy       (14 chuyên mục) ← kinh tế, tài chính")
    print("  8.  VietnamPlus     (15 chuyên mục) ← thông tấn xã VN")
    print("  9.  Nhân Dân        (15 chuyên mục) ← báo Đảng")
    print("  10. Quân đội ND     (15 chuyên mục) ← an ninh, quốc phòng")
    print("  11. Công an ND       (8 chuyên mục) ← pháp luật, an ninh")
    print("  12. Báo Đầu tư      (14 chuyên mục) ← đầu tư, kinh tế")
    print("  13. Báo Chính phủ    (7 chuyên mục) ← chính trị, chính phủ")
    print("  14. VTV News        (11 chuyên mục) ← đài truyền hình")
    print()
    print("  ── CÀO HÀNG LOẠT ──")
    print("  15. TẤT CẢ 14 NGUỒN SONG SONG (tối đa dữ liệu - KHUYẾN NGHỊ)")
    print("  16. Merge data cũ thành 1 file sạch (không crawl mới)")
    print("  17. Chuẩn bị dataset ML (chuẩn hóa nhãn + train/val/test)")
    print()

    while True:
        choice = input("Chọn chế độ (1-17): ").strip()
        if choice in [str(i) for i in range(1, 18)]:
            break
        print("❌ Vui lòng chọn từ 1-17!")

    # Merge-only mode
    if choice == '16':
        print("\n🧹 Đang gộp và làm sạch tất cả data cũ...")
        try:
            subprocess.run([sys.executable, os.path.join('crawlers', 'crawl_all.py'), '--fresh'], check=True)
        except Exception as e:
            print(f"❌ Lỗi: {e}")
            return False
        return True

    # Prepare dataset for ML mode
    if choice == '17':
        print("\n🧠 Chuẩn bị dataset ML từ dữ liệu đã crawl...")
        min_words = input("Số từ tối thiểu mỗi bài (mặc định 100): ").strip()
        min_words = min_words if min_words else '100'
        confidence = input("Ngưỡng confidence mapping (0.0-1.0, mặc định 0.6): ").strip()
        confidence = confidence if confidence else '0.6'

        cmd = [
            sys.executable,
            os.path.join('data_processing', 'prepare_dataset.py'),
            '--min-words',
            str(min_words),
            '--mapping-config',
            os.path.join('docs', 'topic_mapping.json'),
            '--confidence-threshold',
            str(confidence),
        ]
        try:
            subprocess.run(cmd, check=True)
        except Exception as e:
            print(f"❌ Lỗi: {e}")
            return False
        return True

    source_map = {
        '1':  ('vnexpress',      18),
        '2':  ('thanhnien',      16),
        '3':  ('tuoitre',        17),
        '4':  ('vietnamnet',     23),
        '5':  ('dantri',         18),
        '6':  ('laodong',        18),
        '7':  ('vneconomy',      14),
        '8':  ('vietnamplus',    15),
        '9':  ('nhandan',        15),
        '10': ('qdnd',           15),
        '11': ('cand',            8),
        '12': ('baodautu',       14),
        '13': ('baochinhphu',     7),
        '14': ('vtv',            11),
        '15': ('all',            99),
    }

    sources, total_categories = source_map[choice]

    # crawl_all mode (option 15)
    if choice == '15':
        while True:
            try:
                num_articles = int(input("\nSố bài tối đa mỗi chuyên mục (50-3000, khuyến nghị 3000): ").strip())
                if 50 <= num_articles <= 3000:
                    break
                print("❌ Vui lòng nhập từ 50-3000!")
            except ValueError:
                print("❌ Vui lòng nhập số!")

        while True:
            try:
                parallel = int(input("Số nguồn chạy song song (1-10, khuyến nghị 3): ").strip())
                if 1 <= parallel <= 10:
                    break
            except ValueError:
                pass
            print("❌ Vui lòng nhập từ 1-5!")

        print(f"\n🎯 Cào TẤT CẢ nguồn, {num_articles} bài/chuyên mục")
        print(f"   Dùng {parallel} luồng song song. Dữ liệu sẽ merge với data cũ để không trùng lặp\n")
        input("Nhấn Enter để bắt đầu...")

        cmd = [sys.executable, os.path.join('crawlers', 'crawl_all.py'),
               '--max', str(num_articles),
               '--parallel', str(parallel)]
        print("\n" + "=" * 60)
        print("🚀 BẮT ĐẦU CÀO TẤT CẢ NGUỒN...")
        print("=" * 60 + "\n")
        try:
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            print("\n⚠️  Đã dừng bởi người dùng!")
            return False
        return True

    # Single-source mode
    while True:
        try:
            num_articles = int(input(f"\nSố bài mỗi chuyên mục (10-3000): ").strip())
            if 10 <= num_articles <= 3000:
                break
            print("❌ Vui lòng nhập từ 10-3000!")
        except ValueError:
            print("❌ Vui lòng nhập số!")

    total_articles = num_articles * total_categories
    print(f"\n🎯 Sẽ cào ~{total_articles:,} bài từ {total_categories} chuyên mục")
    print(f"⏱️  Thời gian ước tính: {total_articles*0.5/60:.0f}–{total_articles/60:.0f} phút")
    print(f"ℹ️  Nhấn Ctrl+C để dừng giữa chừng (sẽ tự lưu, chạy lại để resume)\n")
    input("Nhấn Enter để bắt đầu...")

    cmd = [sys.executable, 'main.py', '--sources'] + sources.split() + ['--max', str(num_articles)]

    print("\n" + "=" * 60)
    print("🚀 BẮT ĐẦU CÀO DỮ LIỆU...")
    print("=" * 60 + "\n")

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print("\n❌ Có lỗi xảy ra trong quá trình cào!")
        return False
    except KeyboardInterrupt:
        print("\n⚠️  Đã dừng bởi người dùng!")
        return False

    return True

def main():
    """Hàm main"""
    print("\n" + "=" * 60)
    print("   🚀 TOOL CÀO BÁO TỐC ĐỘ CAO - TỰ ĐỘNG SETUP 🚀")
    print("=" * 60 + "\n")
    
    install = input("Cài đặt/cập nhật thư viện cần thiết? (y/n, mặc định=n): ").strip().lower()
    if install == 'y':
        install_requirements()
    else:
        print("⏭️  Bỏ qua cài đặt thư viện\n")
    
    success = run_crawler()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 HOÀN THÀNH!")
        print("📁 Dữ liệu đã được lưu vào thư mục: data/")
    else:
        print("⚠️  Quá trình cào đã bị gián đoạn!")
    print("=" * 60 + "\n")

if __name__ == '__main__':
    main()
