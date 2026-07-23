# 🚀 Hướng dẫn khắc phục lỗi HTTP 429 (Too Many Requests)

## 📋 Vấn đề

Crawler đang gặp lỗi **HTTP 429 Too Many Requests** từ www.qdnd.vn (và có thể từ các trang khác):
```
Lỗi trang 1: HTTPSConnectionPool(host='www.qdnd.vn', port=443): 
Max retries exceeded with url: /giao-duc 
(Caused by ResponseError('too many 429 error responses'))
```

**Nguyên nhân:** Crawler gửi requests quá nhanh (độ trễ chỉ 50-200ms), server tưởng là bot tấn công nên chặn.

---

## ✅ Cải tiến đã thực hiện

### 1. **Tăng độ trễ cơ bản (Base Delays)**

#### Trước:
```python
REQUEST_DELAY_MIN = 0.05   # 50ms - quá nhanh!
REQUEST_DELAY_MAX = 0.2    # 200ms
PAGE_DELAY_MIN = 0.2
PAGE_DELAY_MAX = 0.6
CATEGORY_DELAY_MIN = 0.5
CATEGORY_DELAY_MAX = 1.0
```

#### Sau:
```python
REQUEST_DELAY_MIN = 0.5    # 500ms - an toàn hơn
REQUEST_DELAY_MAX = 1.5    # 1.5 giây
PAGE_DELAY_MIN = 1.0       # 1 giây
PAGE_DELAY_MAX = 2.0       # 2 giây
CATEGORY_DELAY_MIN = 2.0   # 2 giây
CATEGORY_DELAY_MAX = 3.0   # 3 giây
```

**Ý nghĩa:** Giữa mỗi request, tool sẽ chờ **1-2 giây** thay vì **0.05-0.2 giây**. Điều này giả lập hành động của người dùng thực.

---

### 2. **Giảm số luồng concurrent (MAX_WORKERS)**

#### Trước:
```python
MAX_WORKERS = 6  # 6 luồng cào cùng lúc
```

#### Sau:
```python
MAX_WORKERS = 3  # 3 luồng - ít burst requests hơn
```

**Ý nghĩa:** Thay vì cào 6 bài cùng lúc, chỉ cào 3 bài. Giảm khối lượng yêu cầu đồng thời.

---

### 3. **Giảm batch size**

#### Trước:
```python
BATCH_SIZE = 30  # Xử lý 30 bài trước khi pause
```

#### Sau:
```python
BATCH_SIZE = 10  # Xử lý 10 bài rồi pause - an toàn hơn
```

---

### 4. **Thêm Rate Limiting cho từng domain**

**Cấu hình mới trong `config.py`:**
```python
PER_DOMAIN_DELAYS = {
    'www.qdnd.vn': {'min': 3.0, 'max': 5.0},      # QDND = 3-5 giây
    'cand.com.vn': {'min': 2.0, 'max': 4.0},      # CAND = 2-4 giây  
    'laodong.vn': {'min': 2.0, 'max': 3.5},       # Lao Động = 2-3.5 giây
}
```

**Ý nghĩa:** Những trang nhạy cảm sẽ tự động được chậm hơn.

---

### 5. **Cải tiến xử lý 429 (Too Many Requests)**

#### Trước:
```python
# Chờ 60 giây (1 phút) - không đủ
wait_time = 60
# Multiplier chỉ tăng 1.5x
self._current_delay_multiplier = min(5.0, self._current_delay_multiplier * 1.5)
```

#### Sau:
```python
# Chờ 180 giây (3 phút) - server có thời gian khôi phục
wait_time = 180
# Multiplier tăng 2.0x (mạnh hơn)
self._current_delay_multiplier = min(10.0, self._current_delay_multiplier * 2.0)
```

**Ý nghĩa:** Khi server phản hồi 429, tool sẽ:
- Chờ **3 phút** thay vì 1 phút
- Tăng độ trễ toàn bộ crawler lên **3-10x**
- Ví dụ: nếu độ trễ bình thường là 1 giây, thì khi gặp 429 sẽ trở thành 10 giây

---

## 📊 So sánh hiệu suất (Speed vs Safety)

| Metric | Trước | Sau | Ghi chú |
|--------|--------|--------|---------|
| Delay mỗi request | 50-200ms | 500-1500ms | **Chậm 3-10x** |
| Luồng concurrent | 6 | 3 | Giảm 50% |
| Time/1000 articles | ~5 phút | ~15-20 phút | **Chậm nhưng an toàn** |
| 429 errors | Rất nhiều | Rất ít | ✅ Cải thiện |

---

## 🚀 Cách sử dụng

### Lần đầu:
```bash
python main.py --sources all --max 500
```

Tool sẽ:
1. Chờ **1-2 giây** giữa mỗi article
2. Tự động detect domain nhạy cảm (QDND, CAND)
3. Tự động chờ **3-5 giây** cho những domain especiales
4. Nếu gặp 429, chờ 3 phút + tăng độ trễ 2x

### Nếu vẫn gặp 429:

**Option 1:** Tăng thêm delay cho domain cụ thể trong `config.py`:
```python
PER_DOMAIN_DELAYS = {
    'www.qdnd.vn': {'min': 5.0, 'max': 8.0},  # Tăng lên 5-8 giây
    'cand.com.vn': {'min': 3.0, 'max': 5.0},
    'laodong.vn': {'min': 2.5, 'max': 4.0},
}
```

**Option 2:** Giảm thêm MAX_WORKERS trong `config.py`:
```python
MAX_WORKERS = 1  # Chi cào 1 article cùng lúc (chậm nhưng an toàn nhất)
```

**Option 3:** Chỉ cào 1 source tại một thời điểm:
```bash
# Thay vì --sources all, hãy:
python main.py --sources qdnd --max 500
# Sau 30 phút, chạy lần 2:
python main.py --sources cand --max 500
```

---

## 📈 Dấu hiệu hoạt động tốt

✅ Bạn sẽ thấy:
```
⏳ [1/298] OK:0 | Short:0 | Dup:0 | Old:0 | Err:0
⏳ [2/298] OK:1 | Short:0 | Dup:0 | Old:0 | Err:0
⏳ [3/298] OK:1 | Short:0 | Dup:0 | Old:0 | Err:0
```

❌ Dấu hiệu BAD:
```
⚠️  429 Too Many Requests | Delay x2.0 | Chờ 180s...
```

Nếu thấy 429 quá nhiều, tăng `PER_DOMAIN_DELAYS` cho domain đó.

---

## ⚡ Tối ưu hóa nâng cao

### Nếu bạn muốn cào NHANH + ít lỗi:

```python
# config.py
REQUEST_DELAY_MIN = 1.0    # 1 giây
REQUEST_DELAY_MAX = 2.0    # 2 giây
MAX_WORKERS = 2            # 2 luồng
BATCH_SIZE = 5             # Batch nhỏ hơn

PER_DOMAIN_DELAYS = {
    'www.qdnd.vn': {'min': 5.0, 'max': 8.0},
    'cand.com.vn': {'min': 3.0, 'max': 5.0},
    'laodong.vn': {'min': 3.0, 'max': 5.0},  # Tăng vì Lao Động khó tính
}
```

### Nếu server QUÊN LẠ và cứ chặn bạn:

```python
# config.py - FULL SAFE MODE
REQUEST_DELAY_MIN = 3.0    # 3 giây
REQUEST_DELAY_MAX = 5.0    # 5 giây
MAX_WORKERS = 1            # Chỉ 1 luồng duy nhất
BATCH_SIZE = 1             # Cào từng bài rồi pause

PER_DOMAIN_DELAYS = {
    'www.qdnd.vn': {'min': 8.0, 'max': 12.0},   # 8-12 giây
    'cand.com.vn': {'min': 5.0, 'max': 8.0},
    'laodong.vn': {'min': 5.0, 'max': 8.0},
}
```

---

## 🔍 Monitor (Giám sát)

Kiểm tra file log/progress:
```bash
tail -f data/progress.json
```

Hoặc theo dõi thống kê:
```bash
python tests/check_link_coverage.py  # Xem số lượng crawled
```

---

## 📚 Tài liệu tham khảo

- HTTP 429: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429
- backoff strategy: https://en.wikipedia.org/wiki/Exponential_backoff
- Crawler etiquette: https://en.wikipedia.org/wiki/Web_crawler#Etiquette

---

**Tóm tắt:** 
- ❌ Tốc độ sẽ chậm hơn (~3-5x)
- ✅ Nhưng sẽ rất ít lỗi 429 và được server chào đón hơn
- ✅ Tool sẽ hoạt động ổn định lâu dài

Chúc bạn cào thành công! 🎉
