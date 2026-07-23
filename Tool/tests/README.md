# Tests

Thư mục chứa các file test cho dự án crawler báo.

## File test chính

- **`test_all.py`** — Test tổng hợp tất cả 15 nguồn báo:
  - Kiểm tra thư viện (`requests`, `beautifulsoup4`, `lxml`, `newspaper3k`)
  - Lấy link bài viết (1 chuyên mục / nguồn, tối đa 5 link)
  - Trích xuất nội dung + kiểm tra encoding UTF-8
  - Kiểm tra đầy đủ 5 trường: `chu_de`, `tieu_de`, `noi_dung`, `nguon`, `link`
  - Xử lý lỗi mạng (hiển thị rõ ràng khi bị rớt mạng)

- **`test_stop_resume.py`** — Test dừng giữa chừng + checkpoint:
  - Stop flag (`request_stop()` / `is_stopped`)
  - File STOP.flag (từ STOP.bat)
  - Lưu/đọc checkpoint (CSV + JSON + progress.json)

## Chạy test

```bash
# Test tất cả 15 nguồn
python tests/test_all.py

# Chỉ test vài nguồn
python tests/test_all.py --sources vnexpress dantri tuoitre

# Test stop + checkpoint
python tests/test_stop_resume.py
```

## deprecated/

Chứa các file test cũ, không còn sử dụng.
