# -*- coding: utf-8 -*-
"""Kiểm tra tất cả thư viện cần thiết cho project."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def main():
    print('=== Kiểm tra tất cả thư viện trong requirements.txt ===')
    print()
    errors = []

    # 1. Core
    libs = [
        ('requests', 'requests'),
        ('newspaper (newspaper3k)', 'newspaper'),
        ('beautifulsoup4 (bs4)', 'bs4'),
        ('lxml', 'lxml'),
        ('cssselect', 'cssselect'),
    ]
    print('[Core crawling]')
    for name, mod in libs:
        try:
            __import__(mod)
            print(f'  ✅ {name}')
        except ImportError:
            print(f'  ❌ {name} - THIẾU!')
            errors.append(name)

    # 2. newspaper3k deps
    libs2 = [
        ('nltk', 'nltk'),
        ('Pillow (PIL)', 'PIL'),
        ('feedparser', 'feedparser'),
        ('tldextract', 'tldextract'),
        ('feedfinder2', 'feedfinder2'),
    ]
    print('[newspaper3k dependencies]')
    for name, mod in libs2:
        try:
            __import__(mod)
            print(f'  ✅ {name}')
        except ImportError:
            print(f'  ❌ {name} - THIẾU!')
            errors.append(name)

    # 3. nltk data
    print('[nltk data]')
    import nltk
    for d in ['punkt', 'punkt_tab']:
        try:
            nltk.data.find(f'tokenizers/{d}')
            print(f'  ✅ nltk/{d}')
        except Exception:
            print(f'  ❌ nltk/{d} - THIẾU! Chạy: nltk.download("{d}")')
            errors.append(f'nltk-{d}')

    # 4. Scrapy
    libs3 = [('scrapy', 'scrapy'), ('twisted', 'twisted')]
    print('[Scrapy (optional)]')
    for name, mod in libs3:
        try:
            __import__(mod)
            print(f'  ✅ {name}')
        except ImportError:
            print(f'  ⚠️  {name} - không có (optional)')

    # 5. Data processing
    libs4 = [('pandas', 'pandas'), ('numpy', 'numpy')]
    print('[Data processing]')
    for name, mod in libs4:
        try:
            __import__(mod)
            print(f'  ✅ {name}')
        except ImportError:
            print(f'  ❌ {name} - THIẾU!')
            errors.append(name)

    # 6. Utilities
    libs5 = [('python-dateutil', 'dateutil'), ('tqdm', 'tqdm'), ('colorama', 'colorama')]
    print('[Utilities]')
    for name, mod in libs5:
        try:
            __import__(mod)
            print(f'  ✅ {name}')
        except ImportError:
            print(f'  ❌ {name} - THIẾU!')
            errors.append(name)

    # 7. Test import project modules
    print('[Project modules]')
    try:
        from crawlers.newspaper_crawler import NewspaperCrawler
        print('  ✅ crawlers.newspaper_crawler')
    except Exception as e:
        print(f'  ❌ crawlers.newspaper_crawler: {e}')
        errors.append('newspaper_crawler')
    try:
        from utils.data_utils import DataSaver, DataCleaner, DataAnalyzer
        print('  ✅ utils.data_utils')
    except Exception as e:
        print(f'  ❌ utils.data_utils: {e}')
        errors.append('data_utils')
    try:
        from config import NEWS_SOURCES
        print(f'  ✅ config ({len(NEWS_SOURCES)} nguồn)')
    except Exception as e:
        print(f'  ❌ config: {e}')
        errors.append('config')

    print()
    if errors:
        print(f'❌ Có {len(errors)} lỗi: {errors}')
        return 1
    else:
        print('✅ Tất cả thư viện OK - không có lỗi!')
        return 0

if __name__ == '__main__':
    sys.exit(main())
