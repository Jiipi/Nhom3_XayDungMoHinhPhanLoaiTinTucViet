# -*- coding: utf-8 -*-
"""
Kiểm tra toàn diện: so sánh link-bao.txt vs config.py
+ test crawl các link thiếu để tìm link nào hoạt động
"""
import sys, os, re, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlers.newspaper_crawler import NewspaperCrawler
from config import NEWS_SOURCES

# ── Parse link-bao.txt ──────────────────────────────────────────────────
def parse_link_bao(filepath):
    """Trả về dict {domain_key: {'name': ..., 'base_url': ..., 'urls': [...], 'categories': [...]}}"""
    sources = {}
    
    # Map domain → source_key trong config
    DOMAIN_MAP = {
        'vietnamplus.vn': 'vietnamplus',
        'nhandan.vn': 'nhandan',
        'qdnd.vn': 'qdnd',
        'cand.com.vn': 'cand',
        'baodautu.vn': 'baodautu',
        'vneconomy.vn': 'vneconomy',
        'laodong.vn': 'laodong',
        'dantri.com.vn': 'dantri',
        'thanhnien.vn': 'thanhnien',
        'tuoitre.vn': 'tuoitre',
        'baochinhphu.vn': 'baochinhphu',
        'vnexpress.net': 'vnexpress',
        'vietnamnet.vn': 'vietnamnet',
        'vtv.vn': 'vtv',
        'zingnews.vn': 'zingnews',
        'znews.vn': 'zingnews',  # alias
    }
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Tìm tất cả URL
    urls = re.findall(r"https?://[^\s'\"<>,]+", content)
    
    for url in urls:
        url = url.rstrip('/')
        # Parse domain
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        
        # Skip subdomain khác (giamngheobenvung.vietnamnet.vn, etc)
        source_key = None
        for d, k in DOMAIN_MAP.items():
            if domain == d or domain.endswith('.' + d):
                if domain == d:  # chỉ match domain chính
                    source_key = k
                break
        
        if not source_key:
            continue
        
        if source_key not in sources:
            sources[source_key] = {
                'name': NEWS_SOURCES.get(source_key, {}).get('name', source_key),
                'base_url': NEWS_SOURCES.get(source_key, {}).get('base_url', ''),
                'urls': [],
                'categories': []
            }
        
        sources[source_key]['urls'].append(url)
        
        # Trích category từ URL
        path = parsed.path.strip('/')
        # Loại bỏ extension (.htm, .html, .vnp)
        path = re.sub(r'\.(htm|html|vnp)$', '', path)
        # Loại bỏ # fragment
        path = path.split('#')[-1] if '#' in url else path
        
        if path and '/' not in path:  # chỉ lấy category level 1
            sources[source_key]['categories'].append(path)
    
    return sources


def extract_config_categories():
    """Trích categories từ config.py"""
    result = {}
    for key, src in NEWS_SOURCES.items():
        result[key] = {
            'name': src['name'],
            'base_url': src['base_url'],
            'categories': list(src.get('categories', []))
        }
    return result


def main():
    link_bao_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'link-bao.txt')
    
    print("=" * 70)
    print("  KIỂM TRA ĐỘ BAO PHỦ: link-bao.txt vs config.py")
    print("=" * 70)
    
    # Parse
    linkbao = parse_link_bao(link_bao_path)
    config = extract_config_categories()
    
    crawler = NewspaperCrawler()
    
    total_in_linkbao = 0
    total_in_config = 0
    total_missing = 0
    total_extra = 0
    missing_to_test = []  # (source_key, category)
    
    all_sources = sorted(set(list(linkbao.keys()) + list(config.keys())))
    
    for sk in all_sources:
        lb_cats = set(linkbao.get(sk, {}).get('categories', []))
        cf_cats = set(config.get(sk, {}).get('categories', []))
        name = config.get(sk, {}).get('name', linkbao.get(sk, {}).get('name', sk))
        
        missing = lb_cats - cf_cats  # có trong link-bao, thiếu trong config
        extra = cf_cats - lb_cats    # có trong config, không có trong link-bao
        common = lb_cats & cf_cats
        
        total_in_linkbao += len(lb_cats)
        total_in_config += len(cf_cats)
        total_missing += len(missing)
        total_extra += len(extra)
        
        print(f"\n{'─' * 70}")
        print(f"📰  {name} ({sk})")
        print(f"    link-bao.txt: {len(lb_cats)} | config.py: {len(cf_cats)} | "
              f"chung: {len(common)} | thiếu: {len(missing)} | thừa: {len(extra)}")
        
        if missing:
            print(f"    ❌ Thiếu trong config (có trong link-bao.txt):")
            for c in sorted(missing):
                print(f"       - {c}")
                missing_to_test.append((sk, c))
        
        if extra:
            print(f"    ➕ Thừa trong config (không có trong link-bao.txt):")
            for c in sorted(extra):
                print(f"       + {c}")
        
        if not missing and not extra:
            print(f"    ✅ Khớp hoàn toàn!")
    
    print(f"\n{'=' * 70}")
    print(f"📊  TỔNG KẾT SO SÁNH")
    print(f"{'=' * 70}")
    print(f"  Tổng categories trong link-bao.txt: {total_in_linkbao}")
    print(f"  Tổng categories trong config.py:    {total_in_config}")
    print(f"  Thiếu trong config:                 {total_missing}")
    print(f"  Thừa trong config:                  {total_extra}")
    
    if not missing_to_test:
        print(f"\n✅ Không có link nào thiếu!")
        return 0
    
    # ── Test các link thiếu ──────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print(f"🔍  TEST {len(missing_to_test)} LINK THIẾU TRONG CONFIG")
    print(f"{'=' * 70}")
    
    working = []
    broken = []
    
    for sk, cat in missing_to_test:
        print(f"\n  Testing {sk}/{cat}...", end=" ", flush=True)
        try:
            links = crawler.get_article_links(sk, cat, max_links=3)
            if links and len(links) > 0:
                print(f"✅ {len(links)} bài")
                working.append((sk, cat, len(links)))
            else:
                print("⚠️  0 bài")
                broken.append((sk, cat, "0 links"))
        except Exception as e:
            err = str(e)[:60]
            print(f"❌ {err}")
            broken.append((sk, cat, err))
        time.sleep(0.5)
    
    # ── Kết quả ──────────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print(f"📊  KẾT QUẢ TEST LINK THIẾU")
    print(f"{'=' * 70}")
    
    if working:
        print(f"\n  ✅ {len(working)} link CẦN THÊM vào config.py:")
        for sk, cat, n in working:
            print(f"     {sk:20s} → {cat}")
    
    if broken:
        print(f"\n  ❌ {len(broken)} link KHÔNG HOẠT ĐỘNG (bỏ qua):")
        for sk, cat, err in broken:
            print(f"     {sk:20s} → {cat:30s} ({err})")
    
    # ── Xuất code gợi ý thêm vào config.py ──────────────────────────────
    if working:
        print(f"\n{'=' * 70}")
        print(f"📝  GỢI Ý CẬP NHẬT config.py")
        print(f"{'=' * 70}")
        by_source = {}
        for sk, cat, _ in working:
            by_source.setdefault(sk, []).append(cat)
        for sk, cats in sorted(by_source.items()):
            name = config.get(sk, {}).get('name', sk)
            print(f"\n  {name} ({sk}): thêm {len(cats)} chuyên mục")
            for c in sorted(cats):
                print(f"    + '{c}'")
    
    return 1 if working else 0


if __name__ == '__main__':
    sys.exit(main())
