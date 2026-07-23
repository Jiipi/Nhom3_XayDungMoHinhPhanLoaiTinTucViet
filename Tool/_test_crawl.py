#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug test - run crawl_source directly and see detailed output"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawlers.newspaper_crawler import NewspaperCrawler
from config import NEWS_SOURCES

# Print config info
print("=" * 60)
src = NEWS_SOURCES.get('vnexpress', {})
cats = src.get('categories', {})
print(f"Source: {src.get('name')}")
print(f"Categories type: {type(cats)}")
if isinstance(cats, dict):
    print(f"Categories (dict keys): {list(cats.keys())[:5]}...")
elif isinstance(cats, list):
    print(f"Categories (list): {cats[:5]}...")
print(f"Total categories: {len(cats)}")

print("\n" + "=" * 60)
print("Running crawl_source for vnexpress with max=10...")
print("=" * 60 + "\n")

crawler = NewspaperCrawler(use_mobile=True)
articles = crawler.crawl_source('vnexpress', max_per_category=10, delay=1.0,
                                data_dir='data', resume=True)

print(f"\n{'='*60}")
print(f"RESULT: {len(articles)} articles")
if articles:
    for i, a in enumerate(articles[:3]):
        print(f"\n  Article {i+1}:")
        print(f"    chu_de: {a.get('chu_de', '?')}")
        print(f"    tieu_de: {a.get('tieu_de', '?')[:80]}")
        print(f"    noi_dung: {len(a.get('noi_dung', ''))} chars")
print("=" * 60)
