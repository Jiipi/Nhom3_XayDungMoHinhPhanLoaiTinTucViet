# 🚀 HƯỚNG DẪN SỬ DỤNG NHANH

## Cách dùng đơn giản nhất (Windows)

1. **Double-click** vào file `START.bat`
2. Chọn nguồn báo: 1-15 (hoặc 16 để cào tất cả)
3. Nhập số lượng bài: từ 10-200 bài/chuyên mục
4. Nhấn Enter và chờ

✅ **XONG!** Dữ liệu sẽ lưu ở `Tool/data/news_final_*.csv`

---

## 📰 Nguồn báo có sẵn (15 nguồn)

**6 báo lớn nhất:**
1. **VnExpress** - 16 chuyên mục
2. **Thanh Niên** - 12 chuyên mục  
3. **Tuổi Trẻ** - 12 chuyên mục
4. **VietnamNet** - 12 chuyên mục
5. **Zing News** - 7 chuyên mục
6. **Dân Trí** - 13 chuyên mục

**Báo kinh tế:**
7. **Lao Động** - 11 chuyên mục
8. **VnEconomy** - 8 chuyên mục
9. **Báo Đầu tư** - 14 chuyên mục

**Báo nhà nước, an ninh:**
10. **VietnamPlus** - 15 chuyên mục (Thông tấn xã VN)
11. **Nhân Dân** - 14 chuyên mục (Báo Đảng)
12. **Quân đội ND** - 14 chuyên mục
13. **Công an ND** - 8 chuyên mục
14. **Báo Chính phủ** - 7 chuyên mục
15. **VTV News** - 11 chuyên mục

**Tổng cộng: 172 chuyên mục**

---

## Hoặc dùng Python trực tiếp

```bash
python run.py
```

---

## Ví dụ cụ thể

### Lấy 8,600 bài từ TẤT CẢ 15 nguồn (Khuyến nghị!)
- Chọn: **16** (Tất cả nguồn)
- Số bài: **50** bài/chuyên mục
- Kết quả: ~8,600 bài trong 40-60 phút
- ⚡ **Cào song song 15 nguồn cùng lúc!**

### Lấy 800 bài chỉ từ VnExpress
- Chọn: **1** (VnExpress)
- Số bài: **50** bài/chuyên mục
- Kết quả: ~800 bài trong 15-20 phút

### Test nhanh với nhiều nguồn
- Chọn: **16** (Tất cả)
- Số bài: **10** bài/chuyên mục
- Kết quả: ~800 bài trong 3-5 phút

---

## Lưu ý

- **Không tắt máy** khi đang chạy (sẽ mất dữ liệu chưa lưu)
- **Sleep mode cũng dừng** crawler (mất kết nối mạng)
- Dữ liệu backup tự động sau mỗi nguồn báo (file `checkpoint_*.json`)
- Nếu bị lỗi, chạy lại là được (tool tự động loại bỏ trùng lặp)
- **4 luồng đồng thời** - cân bằng giữa tốc độ và tránh bị chặn

---

## Khắc phục lỗi thường gặp

### Lỗi: "Chưa cài Python"
→ Tải Python từ: https://www.python.org/downloads/
→ Tick chọn "Add Python to PATH" khi cài

### Lỗi: "Module not found"
→ Chạy lại `python run.py` và chọn **y** để cài thư viện

### Lỗi: "Connection timeout"
→ Kiểm tra kết nối internet
→ Chạy lại (đã có checkpoint backup)

### Một số nguồn báo lấy ít bài
→ Bình thường! Mỗi nguồn có cấu trúc khác nhau
→ VnExpress và Thanh Niên thường lấy được nhiều nhất

---

**Liên hệ hỗ trợ**: GitHub Copilot
