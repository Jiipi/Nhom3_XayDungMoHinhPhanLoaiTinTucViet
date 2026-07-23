# Kiến trúc mã nguồn (sau refactor)

## Mục tiêu
- Giảm hard-code đường dẫn dữ liệu.
- Tách logic I/O và checkpoint khỏi orchestration crawler.
- Chuẩn hóa schema bài báo dùng chung.

## Module mới

### `utils/path_utils.py`
- `get_data_dir()` / `get_data_dirs()`
- Trách nhiệm: chọn thư mục dữ liệu thống nhất cho toàn dự án.

### `utils/incremental_writer.py`
- `IncrementalWriter`
- Trách nhiệm: ghi JSONL/CSV incremental, auto-rotate file theo dung lượng.

### `utils/large_scale_checkpoint.py`
- `get_checkpoint_path()`, `save_checkpoint()`, `load_checkpoint()`, `parse_completed_categories()`
- Trách nhiệm: quản lý checkpoint cho crawl large-scale.

### `utils/schema.py`
- `ARTICLE_FIELDS`, `is_valid_article_record()`
- Trách nhiệm: chuẩn hóa kiểm tra record bài báo hợp lệ.

## File đã chuyển sang dùng module chung
- `main.py`
- `crawl_large_scale.py`
- `scripts/prepare_dataset.py`
- `tests/comprehensive_test.py`
- `tests/test_stop_resume.py`
- `tests/estimate_scale.py`
- `tests/topic_drift_check.py`

## Lợi ích kiến trúc
- Một nguồn sự thật cho đường dẫn data và schema.
- Tách rõ: orchestration (`crawl_large_scale.py`) vs I/O (`utils/*`).
- Dễ test unit riêng cho writer/checkpoint/schema.
- Giảm rủi ro lỗi khi đổi cấu trúc thư mục hoặc mở rộng pipeline.
