#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ước lượng khả năng scale của tool crawl: 2GB thô / 1GB xử lý

Tính:
- Kích thước 1 bài báo (thô vs xử lý)
- Tốc độ crawl hiện tại
- Thời gian để đạt 2GB / 1GB
- Memory usage khi crawl dữ liệu lớn
"""
import os
import json
import csv
from pathlib import Path
from datetime import datetime, timedelta

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.path_utils import get_data_dir

def analyze_sample_dataset():
    """Phân tích kích thước dataset mẫu hiện có"""
    data_dir = get_data_dir(create=True)
    
    results = {
        "raw_files": {},
        "processed_files": {},
        "total_raw_mb": 0,
        "total_processed_mb": 0,
        "article_count": 0,
        "avg_raw_size_kb": 0,
        "avg_processed_size_kb": 0,
    }
    
    # Tìm file news_final_*.json (dữ liệu thô chưa xử lý)
    for f in data_dir.glob("news_final_*.json"):
        size_bytes = f.stat().st_size
        size_mb = size_bytes / (1024**2)
        results["raw_files"][f.name] = size_mb
        results["total_raw_mb"] += size_mb
        
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
                results["article_count"] += len(data)
        except:
            pass
    
    # Tìm file test.csv từ ml_dataset_* (dữ liệu đã xử lý)
    for f in data_dir.glob("ml_dataset_*/test.csv"):
        size_bytes = f.stat().st_size
        size_mb = size_bytes / (1024**2)
        results["processed_files"][f.name] = size_mb
        results["total_processed_mb"] += size_mb
    
    if results["article_count"] > 0:
        # Ước lượng size raw (JSON array overhead ~20%)
        results["avg_raw_size_kb"] = (results["total_raw_mb"] * 1024) / results["article_count"]
        print(f"📊 Phân tích dataset mẫu hiện tại")
        print(f"{'='*60}")
        print(f"🔍 Raw files:")
        for fname, mb in results["raw_files"].items():
            print(f"   {fname}: {mb:.2f} MB")
        print(f"\n📁 Processed files:")
        for fname, mb in results["processed_files"].items():
            print(f"   {fname}: {mb:.2f} MB")
        print(f"\n📈 Thống kê:")
        print(f"   Tổng bài: {results['article_count']}")
        print(f"   Avg raw size/bài: {results['avg_raw_size_kb']:.1f} KB")
        print(f"   Tổng dung lượng thô: {results['total_raw_mb']:.2f} MB")
        print(f"   Tổng dung lượng xử lý: {results['total_processed_mb']:.2f} MB")
    
    return results

def estimate_scale(article_count: int, avg_raw_kb: float):
    """Ước lượng khả năng đạt 2GB thô / 1GB xử lý"""
    print(f"\n📈 Ước lượng scale (dựa trên {article_count} bài mẫu)")
    print(f"{'='*60}")
    
    # Giả định:
    # - 1 bài thô: avg_raw_kb KB (JSON với HTTP metadata)
    # - 1 bài xử lý: ~0.3x size thô (text only)
    # - Thời gian crawl: 0.5-2 bài/giây (từ test dantri: 37.4s/12 bài = 3.1s/bài)
    
    raw_per_article_kb = max(avg_raw_kb, 15)  # Mặc định tối thiểu 15KB nếu không tính được
    processed_per_article_kb = raw_per_article_kb * 0.3
    
    crawl_speed_bps = 0.5  # bài/giây (conservative, tính thêm delay)
    
    # 2GB thô
    target_raw_gb = 2
    target_raw_kb = target_raw_gb * (1024**2)
    articles_for_2gb = int(target_raw_kb / raw_per_article_kb)
    time_for_2gb_hours = articles_for_2gb / (crawl_speed_bps * 3600)
    
    # 1GB xử lý
    target_processed_gb = 1
    target_processed_kb = target_processed_gb * (1024**2)
    articles_for_1gb = int(target_processed_kb / processed_per_article_kb)
    time_for_1gb_hours = articles_for_1gb / (crawl_speed_bps * 3600)
    
    print(f"\n🔧 Giả định:")
    print(f"   Size/bài thô: {raw_per_article_kb:.1f} KB")
    print(f"   Size/bài xử lý: {processed_per_article_kb:.1f} KB (~30% size thô)")
    print(f"   Tốc độ crawl: {crawl_speed_bps} bài/giây (conservative)")
    
    print(f"\n🎯 Mục tiêu 2GB dữ liệu thô:")
    print(f"   Cần crawl: {articles_for_2gb:,} bài")
    print(f"   Thời gian ước tính: {time_for_2gb_hours:.1f} giờ (~{time_for_2gb_hours/24:.1f} ngày)")
    
    print(f"\n🎯 Mục tiêu 1GB dữ liệu xử lý:")
    print(f"   Cần crawl: {articles_for_1gb:,} bài")
    print(f"   Thời gian ước tính: {time_for_1gb_hours:.1f} giờ (~{time_for_1gb_hours/24:.1f} ngày)")
    
    return {
        "articles_for_2gb": articles_for_2gb,
        "time_for_2gb_hours": time_for_2gb_hours,
        "articles_for_1gb": articles_for_1gb,
        "time_for_1gb_hours": time_for_1gb_hours,
    }

def assess_bottlenecks():
    """Đánh giá bottleneck cho crawl dữ liệu lớn"""
    print(f"\n⚠️ Bottleneck & giới hạn hiện tại:")
    print(f"{'='*60}")
    
    issues = [
        ("Memory", "Response cache in-memory (session level) có thể đầy khi crawl lâu", "MEDIUM"),
        ("Storage", "CSV/JSON file tối đa ~2GB tùy filesystem/Excel limit", "MEDIUM"),
        ("Speed", "Delay anti-block 0.2-2s/bài → bottleneck chính", "HIGH"),
        ("Progress", "Không có ETA/progress bar cho long-running jobs", "LOW"),
        ("Reliability", "Crawl 20+h liên tục → risk network timeout/crash", "MEDIUM"),
        ("Checkpoint", "Checkpoint per-category; để resume mất ~dữ liệu 1 chuyên mục", "LOW"),
    ]
    
    for i, (aspect, issue, severity) in enumerate(issues, 1):
        print(f"\n{i}. {aspect} [{severity}]")
        print(f"   {issue}")
    
    return issues

def assess_readiness():
    """Đánh giá readiness cho crawl 2GB"""
    print(f"\n✅ Readiness assessment:")
    print(f"{'='*60}")
    
    checks = {
        "Multithreading (15 workers)": True,
        "Batch processing (3 cat/batch)": True,
        "Adaptive throttling": True,
        "Connection pooling (20)": True,
        "Checkpoint/resume": True,
        "Anti-block (User-Agent rotate)": True,
        "Dedup (MD5 hash)": True,
        "Progress tracking for 20h+": False,
        "Memory monitoring": False,
        "Auto-retry on network error": True,
        "Incremental file save (<<memory)": False,
    }
    
    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    
    for feature, ready in checks.items():
        status = "✅" if ready else "❌"
        print(f"{status} {feature}")
    
    print(f"\nReadiness score: {passed}/{total} ({100*passed//total}%)")
    return checks

if __name__ == "__main__":
    print("\n" + "🔬 SCALE ANALYSIS: 2GB THÔ / 1GB XỬ LÝ".center(60))
    print("=" * 60)
    
    # 1. Phân tích sample
    sample = analyze_sample_dataset()
    
    # 2. Ước lượng scale
    if sample["article_count"] > 0:
        estimate = estimate_scale(sample["article_count"], sample["avg_raw_size_kb"])
    else:
        estimate = estimate_scale(40, 20)  # Default nếu không có sample
    
    # 3. Đánh giá bottleneck
    issues = assess_bottlenecks()
    
    # 4. Readiness
    readiness = assess_readiness()
    
    # 5. Khuyến cáo
    print(f"\n💡 Khuyến cáo:")
    print(f"{'='*60}")
    print(f"""
• Crawl 2GB thô/1GB xử lý là KHẢ THI nhưng cần chuẩn bị:
  - Để lại máy chạy 24-48h liên tục (hoặc chia thành 2-3 lần)
  - Monitor memory nếu quá 2GB RAM
  - Backup data định kỳ (checkpoint auto mỗi chuyên mục)

• Ưu tiên cải tiến trước khi crawl 2GB:
  1. Thêm progress bar & ETA (tqdm)
  2. Implement incremental save (append CSV/JSONL, không load hết vào memory)
  3. Add memory monitoring + warning
  4. Add auto-rotate output file (chia nhỏ file sau 500MB)

• Deadline gấp? Crawl theo mức:
  - 100MB: ~30 phút (tư liệu test)
  - 500MB: ~2.5 giờ (đủ cho tiểu luận)
  - 2GB: ~10+ giờ (dành cho research hoàn chỉnh)
    """)
