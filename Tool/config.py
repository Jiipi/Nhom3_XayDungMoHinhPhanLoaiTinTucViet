# -*- coding: utf-8 -*-
"""
Cấu hình chính cho Tool cào báo
================================

Chứa các hằng số toàn cục dùng bởi crawlers và scripts khác.
"""

# 📰 Danh sách Nguồn Báo
NEWS_SOURCES = {
    'vnexpress': {
        'name': 'VnExpress',
        'base_url': 'https://vnexpress.net',
        'url': 'https://vnexpress.net',
        'categories': {
            'thoi-su': 'https://vnexpress.net/thoi-su',
            'the-gioi': 'https://vnexpress.net/the-gioi',
            'kinh-doanh': 'https://vnexpress.net/kinh-doanh',
            'cong-nghe': 'https://vnexpress.net/so-hoa',
            'the-thao': 'https://vnexpress.net/the-thao',
            'giai-tri': 'https://vnexpress.net/giai-tri',
            'giao-duc': 'https://vnexpress.net/giao-duc',
            'suc-khoe': 'https://vnexpress.net/suc-khoe',
            'doi-song': 'https://vnexpress.net/doi-song',
            'du-lich': 'https://vnexpress.net/du-lich',
            'phap-luat': 'https://vnexpress.net/phap-luat',
            'khoa-hoc': 'https://vnexpress.net/khoa-hoc',
            'xe': 'https://vnexpress.net/oto-xe-may',
            'y-kien': 'https://vnexpress.net/y-kien',
        }
    },
    'tuoitre': {
        'name': 'Tuổi Trẻ',
        'base_url': 'https://tuoitre.vn',
        'url': 'https://tuoitre.vn',
        'categories': {
            'thoi-su': 'https://tuoitre.vn/thoi-su.htm',
            'the-gioi': 'https://tuoitre.vn/the-gioi.htm',
            'kinh-doanh': 'https://tuoitre.vn/kinh-doanh.htm',
            'cong-nghe': 'https://tuoitre.vn/nhip-song-so.htm',
            'the-thao': 'https://tuoitre.vn/the-thao.htm',
            'giai-tri': 'https://tuoitre.vn/giai-tri.htm',
            'giao-duc': 'https://tuoitre.vn/giao-duc.htm',
            'suc-khoe': 'https://tuoitre.vn/suc-khoe.htm',
            'du-lich': 'https://tuoitre.vn/du-lich.htm',
            'phap-luat': 'https://tuoitre.vn/phap-luat.htm',
            'xe': 'https://tuoitre.vn/xe.htm',
            'van-hoa': 'https://tuoitre.vn/van-hoa.htm',
            'doi-song': 'https://tuoitre.vn/doi-song.htm',
        }
    },
    'dantri': {
        'name': 'Dân Trí',
        'base_url': 'https://dantri.com.vn',
        'url': 'https://dantri.com.vn',
        'categories': {
            'thoi-su': 'https://dantri.com.vn/thoi-su.htm',
            'the-gioi': 'https://dantri.com.vn/the-gioi.htm',
            'kinh-doanh': 'https://dantri.com.vn/kinh-doanh.htm',
            'cong-nghe': 'https://dantri.com.vn/suc-manh-so.htm',
            'the-thao': 'https://dantri.com.vn/the-thao.htm',
            'giai-tri': 'https://dantri.com.vn/giai-tri.htm',
            'giao-duc': 'https://dantri.com.vn/giao-duc.htm',
            'suc-khoe': 'https://dantri.com.vn/suc-khoe.htm',
            'doi-song': 'https://dantri.com.vn/doi-song.htm',
            'du-lich': 'https://dantri.com.vn/du-lich.htm',
            'phap-luat': 'https://dantri.com.vn/phap-luat.htm',
            'xe': 'https://dantri.com.vn/o-to-xe-may.htm',
            'bat-dong-san': 'https://dantri.com.vn/bat-dong-san.htm',
            'viec-lam': 'https://dantri.com.vn/viec-lam.htm',
        }
    },
    'thanhnien': {
        'name': 'Thanh Niên',
        'base_url': 'https://thanhnien.vn',
        'url': 'https://thanhnien.vn',
        'categories': {
            'thoi-su': 'https://thanhnien.vn/thoi-su',
            'the-gioi': 'https://thanhnien.vn/the-gioi',
            'kinh-doanh': 'https://thanhnien.vn/tai-chinh-kinh-doanh',
            'cong-nghe': 'https://thanhnien.vn/cong-nghe',
            'the-thao': 'https://thanhnien.vn/the-thao',
            'giai-tri': 'https://thanhnien.vn/giai-tri',
            'giao-duc': 'https://thanhnien.vn/giao-duc',
            'suc-khoe': 'https://thanhnien.vn/suc-khoe',
            'doi-song': 'https://thanhnien.vn/doi-song',
            'du-lich': 'https://thanhnien.vn/du-lich',
            'xe': 'https://thanhnien.vn/xe',
            'van-hoa': 'https://thanhnien.vn/van-hoa',
        }
    },
    'vietnamnet': {
        'name': 'VietnamNet',
        'base_url': 'https://vietnamnet.vn',
        'url': 'https://vietnamnet.vn',
        'categories': {
            'thoi-su': 'https://vietnamnet.vn/thoi-su',
            'the-gioi': 'https://vietnamnet.vn/the-gioi',
            'kinh-doanh': 'https://vietnamnet.vn/kinh-doanh',
            'cong-nghe': 'https://vietnamnet.vn/cong-nghe',
            'the-thao': 'https://vietnamnet.vn/the-thao',
            'giai-tri': 'https://vietnamnet.vn/giai-tri',
            'giao-duc': 'https://vietnamnet.vn/giao-duc',
            'suc-khoe': 'https://vietnamnet.vn/suc-khoe',
            'doi-song': 'https://vietnamnet.vn/doi-song',
            'du-lich': 'https://vietnamnet.vn/du-lich',
            'phap-luat': 'https://vietnamnet.vn/phap-luat',
            'xe': 'https://vietnamnet.vn/oto-xe-may',
            'bat-dong-san': 'https://vietnamnet.vn/bat-dong-san',
        }
    },
    'laodong': {
        'name': 'Lao Động',
        'base_url': 'https://laodong.vn',
        'url': 'https://laodong.vn',
        'categories': {
            'thoi-su': 'https://laodong.vn/thoi-su',
            'the-gioi': 'https://laodong.vn/the-gioi',
            'kinh-doanh': 'https://laodong.vn/kinh-doanh',
            'cong-nghe': 'https://laodong.vn/cong-nghe',
            'the-thao': 'https://laodong.vn/the-thao',
            'giai-tri': 'https://laodong.vn/giai-tri',
            'giao-duc': 'https://laodong.vn/giao-duc',
            'suc-khoe': 'https://laodong.vn/suc-khoe',
            'doi-song': 'https://laodong.vn/doi-song',
            'du-lich': 'https://laodong.vn/du-lich',
            'phap-luat': 'https://laodong.vn/phap-luat',
            'xe': 'https://laodong.vn/xe',
            'bat-dong-san': 'https://laodong.vn/bat-dong-san',
        }
    },
    'vneconomy': {
        'name': 'VnEconomy',
        'base_url': 'https://vneconomy.vn',
        'url': 'https://vneconomy.vn',
        'categories': {
            'thoi-su': 'https://vneconomy.vn/thoi-su.htm',
            'kinh-doanh': 'https://vneconomy.vn/kinh-te-viet-nam.htm',
            'the-gioi': 'https://vneconomy.vn/the-gioi.htm',
            'tai-chinh': 'https://vneconomy.vn/tai-chinh.htm',
            'bat-dong-san': 'https://vneconomy.vn/bat-dong-san.htm',
            'cong-nghe': 'https://vneconomy.vn/cong-nghe.htm',
            'doi-song': 'https://vneconomy.vn/doi-song.htm',
        }
    },
    'vietnamplus': {
        'name': 'VietnamPlus',
        'base_url': 'https://www.vietnamplus.vn',
        'url': 'https://www.vietnamplus.vn',
        'categories': {
            'thoi-su': 'https://www.vietnamplus.vn/chinh-tri.vnp',
            'the-gioi': 'https://www.vietnamplus.vn/the-gioi.vnp',
            'kinh-doanh': 'https://www.vietnamplus.vn/kinh-te.vnp',
            'the-thao': 'https://www.vietnamplus.vn/the-thao.vnp',
            'giai-tri': 'https://www.vietnamplus.vn/van-hoa.vnp',
            'cong-nghe': 'https://www.vietnamplus.vn/scitech.vnp',
            'xa-hoi': 'https://www.vietnamplus.vn/xa-hoi.vnp',
        }
    },
    'nhandan': {
        'name': 'Nhân Dân',
        'base_url': 'https://nhandan.vn',
        'url': 'https://nhandan.vn',
        'categories': {
            'thoi-su': 'https://nhandan.vn/chinh-tri',
            'the-gioi': 'https://nhandan.vn/the-gioi',
            'kinh-doanh': 'https://nhandan.vn/kinh-te',
            'the-thao': 'https://nhandan.vn/the-thao',
            'giao-duc': 'https://nhandan.vn/giao-duc',
            'van-hoa': 'https://nhandan.vn/van-hoa',
            'xa-hoi': 'https://nhandan.vn/xa-hoi',
            'phap-luat': 'https://nhandan.vn/phap-luat',
            'cong-nghe': 'https://nhandan.vn/khoa-hoc-cong-nghe',
            'doi-song': 'https://nhandan.vn/doi-song',
        }
    },
    'qdnd': {
        'name': 'Quân đội ND',
        'base_url': 'https://www.qdnd.vn',
        'url': 'https://www.qdnd.vn',
        'categories': {
            'thoi-su': 'https://www.qdnd.vn/chinh-tri',
            'the-gioi': 'https://www.qdnd.vn/quoc-te',
            'kinh-doanh': 'https://www.qdnd.vn/kinh-te',
            'the-thao': 'https://www.qdnd.vn/the-thao',
            'giao-duc': 'https://www.qdnd.vn/giao-duc-khoa-hoc',
            'van-hoa': 'https://www.qdnd.vn/van-hoa-xa-hoi',
            'phap-luat': 'https://www.qdnd.vn/phap-luat',
            'quoc-phong': 'https://www.qdnd.vn/quoc-phong-an-ninh',
        }
    },
    'cand': {
        'name': 'CAND Online',
        'base_url': 'https://cand.com.vn',
        'url': 'https://cand.com.vn',
        'categories': {
            'thoi-su': 'https://cand.com.vn/thoi-su',
            'the-gioi': 'https://cand.com.vn/the-gioi',
            'kinh-doanh': 'https://cand.com.vn/kinh-te',
            'phap-luat': 'https://cand.com.vn/ban-tin-113',
            'cong-nghe': 'https://cand.com.vn/cong-nghe-khoa-hoc',
            'giai-tri': 'https://cand.com.vn/van-hoa-giai-tri',
            'xa-hoi': 'https://cand.com.vn/xa-hoi',
        }
    },
    'baodautu': {
        'name': 'Báo Đầu tư',
        'base_url': 'https://baodautu.vn',
        'url': 'https://baodautu.vn',
        'categories': {
            'kinh-doanh': 'https://baodautu.vn/kinh-te',
            'bat-dong-san': 'https://baodautu.vn/bat-dong-san',
            'tai-chinh': 'https://baodautu.vn/tai-chinh',
            'the-gioi': 'https://baodautu.vn/the-gioi',
            'cong-nghe': 'https://baodautu.vn/cong-nghe',
        }
    },
    'baochinhphu': {
        'name': 'Báo Chính phủ',
        'base_url': 'https://baochinhphu.vn',
        'url': 'https://baochinhphu.vn',
        'categories': {
            'thoi-su': 'https://baochinhphu.vn/thoi-su',
            'the-gioi': 'https://baochinhphu.vn/the-gioi',
            'kinh-doanh': 'https://baochinhphu.vn/kinh-te',
            'xa-hoi': 'https://baochinhphu.vn/xa-hoi',
        }
    },
    'vtv': {
        'name': 'VTV News',
        'base_url': 'https://vtv.vn',
        'url': 'https://vtv.vn',
        'categories': {
            'thoi-su': 'https://vtv.vn/chinh-tri.htm',
            'the-gioi': 'https://vtv.vn/the-gioi.htm',
            'kinh-doanh': 'https://vtv.vn/kinh-te.htm',
            'the-thao': 'https://vtv.vn/the-thao.htm',
            'giai-tri': 'https://vtv.vn/giai-tri.htm',
            'cong-nghe': 'https://vtv.vn/cong-nghe.htm',
            'suc-khoe': 'https://vtv.vn/suc-khoe.htm',
            'doi-song': 'https://vtv.vn/doi-song.htm',
        }
    },
}

# 🤖 User Agents
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
]

# 📊 Crawler Configuration
MAX_ARTICLES_PER_CATEGORY = 0     # 0 = không giới hạn, cào đến khi hết trang trong chuyên mục
OUTPUT_FORMAT = 'jsonl'

# 🌐 Request Configuration
USE_MOBILE_VERSION = False
REQUEST_DELAY_MIN = 0.12   # nhịp mặc định cho domain "dễ"
REQUEST_DELAY_MAX = 0.35
PAGE_DELAY_MIN = 0.0       # đã có scheduler theo domain, không cần sleep cố định giữa trang
PAGE_DELAY_MAX = 0.0
CATEGORY_DELAY_MIN = 0.0   # chuyển chuyên mục ngay, scheduler sẽ tự giữ nhịp request an toàn
CATEGORY_DELAY_MAX = 0.0

# ⚙️ Network Configuration
MAX_RETRIES = 4
TIMEOUT = 20
MAX_WORKERS = 10           # tăng worker, nhưng request thực sẽ được scheduler điều tiết theo domain
CONNECTION_POOL_SIZE = 32
MAX_RETRIES_FOR_429 = 8    # tăng số lần thử 429
SOURCE_PARALLELISM = 6     # số nguồn chạy đồng thời

# ⚙️ Per-Domain Rate Limiting - các site nhạy cảm như QDND, CAND cần delay lâu hơn
PER_DOMAIN_DELAYS = {
    'www.qdnd.vn': {'min': 1.8, 'max': 3.0},      # QDND rate-limit rất chặt
    'cand.com.vn': {'min': 1.2, 'max': 2.2},      # CAND cũng khá chặt
    'laodong.vn': {'min': 1.4, 'max': 2.4},       # Lao Động có anti-bot
    'baochinhphu.vn': {'min': 0.6, 'max': 1.2},
    'vtv.vn': {'min': 0.5, 'max': 1.0},
}

# 💾 Performance Configuration
ENABLE_ADAPTIVE_THROTTLING = True
ENABLE_RESPONSE_CACHE = True
ENABLE_BATCH_PROCESSING = True
BATCH_SIZE = 50            # chỉ còn dùng cho checkpoint grouping, không còn là cơ chế chống burst chính

# 🔎 Discovery Configuration
AUTO_DISCOVER_CATEGORIES = True
DISCOVERY_SEED_LIMIT = 8   # số trang seed mỗi nguồn để tìm thêm chủ đề mới

# 📈 Progress UI Configuration
PROGRESS_USE_COLOR = True
PROGRESS_BAR_WIDTH = 40
PROGRESS_RATE_UNIT = 'bytes'  # 'links' | 'bytes'

# 📁 Folder Configuration
DATA_DIR = 'data'  # Hoặc 'Tool/data'
CHECKPOINT_DIR = DATA_DIR
LOG_DIR = 'logs'

# 📊 Aggregate save: lưu vào file final mỗi khi đạt N bài mới
SAVE_AGGREGATE_EVERY = 1  # append ngay khi có bài mới
