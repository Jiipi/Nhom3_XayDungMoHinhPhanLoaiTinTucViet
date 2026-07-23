# 🚀 Tool Cào Báo Tốc Độ Cao

Tool chuyên nghiệp để cào hàng nghìn bài báo từ các nguồn tin tức lớn tại Việt Nam.

## ✨ Tính năng

- 🎯 **15 nguồn báo lớn**: VnExpress, Dân Trí, Tuổi Trẻ, Thanh Niên, VietnamNet, VnEconomy, Lao Động, Zing News, VietnamPlus, Nhân Dân, Quân đội ND, Công an ND, Báo Đầu tư, Báo Chính phủ, VTV News
- ⚡ **2 chế độ tốc độ**:
  - `newspaper3k`: Đơn giản, dễ sử dụng, ổn định
  - `scrapy`: Async, cực nhanh, có thể cào hàng trăm request đồng thời
- 🛡️ **Anti-blocking**: 
  - Tự động thay đổi User-Agent
  - Ưu tiên sử dụng mobile version (nhẹ hơn, ít bị chặn)
  - Random delay giữa các request
- 💾 **Đa dạng format**: CSV, JSON, JSONL
- 🧹 **Tự động làm sạch**: Loại bỏ trùng lặp, bài viết quá ngắn
- 📊 **Thống kê chi tiết**: Phân tích dữ liệu theo nguồn, chuyên mục
- 💼 **Checkpoint**: Tự động lưu sau mỗi nguồn, tránh mất dữ liệu

## 📦 Cài đặt

```bash
cd Tool
pip install -r requirements.txt
```

**Lưu ý**: Nếu chỉ dùng mode `newspaper` (đơn giản), có thể bỏ qua Scrapy:

```bash
pip install newspaper3k beautifulsoup4 lxml requests pandas
```

## 🚀 Sử dụng

### Cơ bản - Cào VnExpress

```bash
python main.py
```

### Cào nhiều nguồn với Newspaper3k

```bash
python main.py --sources vnexpress dantri tuoitre --max 100
```

### Cào TẤT CẢ nguồn với Scrapy (siêu nhanh)

```bash
python main.py --mode scrapy --sources all --max 500
```

### Cào và lưu nhiều format

```bash
python main.py --sources thanhnien vietnamnet --max 200 --format all
```

### Chuẩn bị dataset cho học máy (phân loại chủ đề)

```bash
python scripts/prepare_dataset.py
```

Tool sẽ tự lấy file `news_final_*` mới nhất trong `Tool/data/`, sau đó:
- chuẩn hóa nhãn chủ đề liên báo bằng mapping tự động (override + fuzzy + content scoring),
- lọc bài ngắn/trùng,
- chia `train/val/test` theo stratified split,
- xuất `report.json` + `report.md` + `mapping_review.csv` trong thư mục `Tool/data/ml_dataset_*`.

Tuỳ chỉnh mapping:

```bash
python scripts/prepare_dataset.py --mapping-config docs/topic_mapping.json --confidence-threshold 0.6
```

Trong đó `docs/topic_mapping.json` cho phép chỉnh:
- `label_aliases`: alias category theo từng nhãn chuẩn,
- `label_keywords`: từ khoá nội dung để suy luận nhãn,
- `source_overrides`: map thủ công theo từng nguồn/chuyên mục để tăng độ chính xác.

## 📋 Tham số

| Tham số | Mô tả | Mặc định |
|---------|-------|----------|
| `--mode` | Chế độ: `newspaper` hoặc `scrapy` | `newspaper` |
| `--sources` | Danh sách nguồn hoặc `all` | `vnexpress` |
| `--max` | Số bài tối đa mỗi chuyên mục | `100` |
| `--format` | Format output: `csv`, `json`, `jsonl`, `all` | `csv` |

## 📁 Cấu trúc dự án

```
Tool/
├── main.py                 # Script chính
├── config.py              # Cấu hình (nguồn báo, User-Agent, settings)
├── requirements.txt       # Dependencies
├── README.md             # File này
│
├── crawlers/             # Các crawler
│   ├── newspaper_crawler.py   # Crawler dùng newspaper3k
│   └── scrapy_crawler.py      # Crawler dùng Scrapy
│
├── utils/                # Utilities
│   └── data_utils.py     # Lưu, làm sạch, phân tích dữ liệu
│
└── data/                 # Dữ liệu output (tự động tạo)
    ├── checkpoint_*.json     # Checkpoint files
    └── news_final_*.csv      # Dữ liệu cuối cùng
```

## 🎯 Các nguồn hỗ trợ (15 nguồn)

**Các báo lớn nhất:**
- `vnexpress` - VnExpress
- `dantri` - Dân Trí
- `tuoitre` - Tuổi Trẻ
- `thanhnien` - Thanh Niên
- `vietnamnet` - VietnamNet
- `zingnews` - Zing News

**Báo kinh tế, tài chính:**
- `vneconomy` - VnEconomy
- `baodautu` - Báo Đầu tư
- `laodong` - Lao Động

**Báo nhà nước, an ninh:**
- `vietnamplus` - VietnamPlus (Thông tấn xã VN)
- `nhandan` - Nhân Dân (Báo Đảng)
- `qdnd` - Quân đội nhân dân
- `cand` - Công an nhân dân
- `baochinhphu` - Báo Chính phủ
- `vtv` - VTV News

## 💡 Ví dụ nâng cao

### Test nhanh với 1 nguồn

```bash
python main.py --sources vnexpress --max 50
```

### Cào báo kinh tế

```bash
python main.py --sources vneconomy baodautu laodong --max 200
```

### Cào báo nhà nước

```bash
python main.py --sources vietnamplus nhandan baochinhphu qdnd --max 150
```

### Cào nhiều nguồn lớn

```bash
python main.py --sources vnexpress dantri tuoitre thanhnien --max 150
```

### Cào số lượng lớn (hàng nghìn bài)

```bash
python main.py --mode scrapy --sources all --max 1000
```

### Cào dữ liệu lớn có checkpoint/resume (khuyến nghị cho 1GB/2GB)

```bash
# Mục tiêu 1GB dữ liệu đã xử lý (JSONL), tự dừng khi đủ
python crawl_large_scale.py --sources all --max 500 --goal processed-1gb --run-id nhom_1gb

# Mục tiêu 2GB dữ liệu chưa xử lý (JSONL), tự dừng khi đủ
python crawl_large_scale.py --sources all --max 500 --goal raw-2gb --run-id nhom_2gb

# Resume khi mất mạng/cúp điện/cắt ngang
python crawl_large_scale.py --sources all --max 500 --resume-id nhom_1gb
```

Ghi chú:
- Crawler lưu checkpoint tại `data/large_scale_checkpoint_<run_id>.json`.
- Dữ liệu được ghi incremental (từng bài), nên rớt mạng sẽ không mất phần đã ghi.
- Có thể tùy chỉnh ngưỡng dừng bằng `--target-mb` hoặc `--target-gb`.

## 📊 Output

Dữ liệu được lưu trong thư mục `Tool/data/` với **2 cột đơn giản**:

- `chu_de`: Chủ đề/chuyên mục (vd: thoi-su, kinh-doanh, giai-tri...)
- `noi_dung`: Nội dung bài viết (tiêu đề + nội dung, tối đa 300 từ)

## ⚡ Tốc độ

- **Newspaper3k**: ~5-10 bài/phút (an toàn, ít bị chặn)
- **Scrapy**: ~50-100 bài/phút (nhanh gấp 10 lần)

## 🛠️ Tùy chỉnh

Chỉnh sửa `config.py` để:

- Thêm nguồn báo mới
- Điều chỉnh User-Agent
- Thay đổi cấu hình Scrapy (concurrent requests, delay...)
- Thay đổi số bài tối đa

## ⚠️ Lưu ý

1. **Tuân thủ robots.txt**: Tool này bỏ qua robots.txt để cào nhanh hơn. Nếu muốn tuân thủ, set `ROBOTSTXT_OBEY = True` trong `config.py`

2. **Delay hợp lý**: Nếu bị chặn IP, tăng `DOWNLOAD_DELAY` trong config

3. **Mobile version**: Ưu tiên dùng mobile version (nhẹ hơn, ít bị chặn)

4. **Checkpoint**: Tool tự động lưu checkpoint sau mỗi nguồn. Nếu bị gián đoạn, chỉ mất dữ liệu của nguồn đang cào

## 🐛 Xử lý lỗi

### Lỗi: "No module named 'newspaper'"

```bash
pip install newspaper3k
```

### Lỗi: "No module named 'scrapy'"

Nếu chỉ dùng mode newspaper:
```bash
python main.py --mode newspaper ...
```

Hoặc cài Scrapy:
```bash
pip install scrapy
```

### Bị chặn IP

- Giảm `CONCURRENT_REQUESTS` trong `config.py`
- Tăng `DOWNLOAD_DELAY`
- Sử dụng proxy (tự implement)

## 📝 License

Free to use for research and educational purposes.

## 🤝 Đóng góp

Mọi đóng góp đều được chào đón! Hãy tạo Pull Request hoặc Issue.

---

**Made with ❤️ for Vietnamese news aggregation**
