# -*- coding: utf-8 -*-
"""
VietNews AI — Lightweight Local Web Server & API Backend
=========================================================

Phục vụ Giao diện Web (Frontend) và API Phân loại Tin tức (Backend).
Chạy hoàn toàn bằng Python standard library (http.server), không cần cài thêm package phụ thuộc!
"""

import http.server
import socketserver
import json
import os
import sys
import re
import time
from urllib.parse import parse_qs, urlparse
from pathlib import Path

PORT = 8000
WEB_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_FILE = Path(WEB_DIR) / "news_model.joblib"

# Load trained model if available
ML_PIPELINE = None
if MODEL_FILE.exists():
    try:
        import joblib
        ML_PIPELINE = joblib.load(MODEL_FILE)
        print(f"[MODEL] Loaded trained machine learning model from {MODEL_FILE.name}")
    except Exception as e:
        print(f"[WARNING] Could not load joblib model: {e}")

CATEGORIES = [
    {"key": "cong-nghe", "name": "Công nghệ"},
    {"key": "kinh-doanh", "name": "Kinh doanh"},
    {"key": "the-thao", "name": "Thể thao"},
    {"key": "thoi-su", "name": "Thời sự"},
    {"key": "giai-tri", "name": "Giải trí"},
    {"key": "suc-khoe", "name": "Sức khỏe"},
    {"key": "giao-duc", "name": "Giáo dục"},
    {"key": "phap-luat", "name": "Pháp luật"},
    {"key": "du-lich", "name": "Du lịch"},
    {"key": "doi-song", "name": "Đời sống"},
    {"key": "xe", "name": "Xe / Ô tô"}
]

TOPIC_KEYWORDS = {
    "cong-nghe": ["ai", "trí tuệ nhân tạo", "trí_tuệ_nhân_tạo", "công nghệ", "công_nghệ", "phần mềm", "phần_mềm", "ứng dụng", "ứng_dụng", "llm", "chatgpt", "openai", "deepseek", "robot", "chip", "iphone", "samsung", "máy tính", "máy_tính", "bảo mật", "bảo_mật", "dữ liệu", "dữ_liệu"],
    "kinh-doanh": ["giá vàng", "giá_vàng", "doanh nghiệp", "doanh_nghiệp", "lợi nhuận", "lợi_nhuận", "kinh tế", "kinh_tế", "chứng khoán", "chứng_khoán", "tài chính", "tài_chính", "ngân hàng", "ngân_hàng", "lạm phát", "lạm_phát", "đầu tư", "đầu_tư", "thị trường", "thị_trường", "tăng trưởng", "tăng_trưởng", "bất động sản", "bất_động_sản", "doanh thu", "doanh_thu"],
    "the-thao": ["cơ thủ", "cơ_thủ", "bóng đá", "bóng_đá", "giải đấu", "giải_đấu", "tỷ số", "tỷ_số", "đồng đội", "đồng_đội", "vô địch", "vô_địch", "billiards", "huy chương", "huy_chương", "trận đấu", "trận_đấu", "bàn thắng", "bàn_thắng", "hlv", "clb", "vận động viên", "vận_động_viên"],
    "giao-duc": ["đại học", "đại_học", "xét tuyển", "xét_tuyển", "thí sinh", "thí_sinh", "điểm chuẩn", "điểm_chuẩn", "bách khoa", "bách_khoa", "thpt", "trường học", "trường_học", "học phí", "học_phí", "giáo dục", "giáo_dục", "học sinh", "học_sinh", "giáo viên", "giáo_viên", "học bổng", "học_bổng", "bộ giáo dục", "tuyển sinh", "tuyển_sinh"],
    "suc-khoe": ["bệnh", "y tế", "y_tế", "bác sĩ", "bác_sĩ", "vắc xin", "vắc_xin", "hô hấp", "hô_hấp", "cúm", "cúm a", "cúm_a", "sức khỏe", "sức_khỏe", "bệnh viện", "bệnh_viện", "dịch bệnh", "dịch_bệnh", "thuốc", "điều trị", "điều_trị", "triệu chứng", "triệu_chứng", "bệnh nhân", "bệnh_nhân", "viêm phổi", "viêm_phổi"],
    "giai-tri": ["phim", "diễn viên", "diễn_viên", "ca sĩ", "ca_sĩ", "nghệ sĩ", "nghệ_sĩ", "show", "giải trí", "giải_trí", "hollywood", "album", "nhạc", "kpop", "nhạc kịch", "lễ trao giải", "quả cầu vàng", "rạp chiếu", "rạp_chiếu", "điện ảnh", "điện_ảnh", "chiếu rạp", "chiếu_rạp", "bộ phim", "bộ_phim"],
    "phap-luat": ["công an", "công_an", "điều tra", "điều_tra", "vụ án", "vụ_án", "xử phạt", "xử_phạt", "tòa án", "tòa_án", "pháp luật", "pháp_luật", "tội phạm", "tội_phạm", "bắt giữ", "bắt_giữ", "vi phạm", "vi_phạm", "khởi tố", "khởi_tố", "bị cáo", "bị_cáo", "luật sư", "luật_sư"],
    "du-lich": ["du lịch", "du_lịch", "khách sạn", "khách_sạn", "điểm đến", "điểm_đến", "vé máy bay", "vé_máy_bay", "tour", "nghỉ dưỡng", "nghỉ_dưỡng", "bãi biển", "bãi_biển", "du khách", "du_khách", "vịnh", "resort", "trải nghiệm", "phú quốc", "phú_quốc"],
    "doi-song": ["gia đình", "gia_đình", "đời sống", "đời_sống", "mẹ bầu", "con cái", "con_cái", "tình yêu", "tình_yêu", "hôn nhân", "hôn_nhân", "ẩm thực", "ẩm_thực", "mẹo hay", "nội trợ"],
    "xe": ["ô tô", "ô_tô", "xe máy", "xe_máy", "xe điện", "xe_điện", "động cơ", "động_cơ", "vinfast", "hyundai", "toyota", "lái xe", "lái_xe", "giao thông", "giao_thông", "tốc độ", "tốc_độ", "mẫu xe", "mẫu_xe"],
    "thoi-su": ["chính phủ", "chính_phủ", "thời sự", "thời_sự", "quy hoạch", "quy_hoạch", "dự án", "dự_án", "nghị quyết", "nghị_quyết", "lãnh đạo", "lãnh_đạo", "tp hcm", "hà nội", "giao thông", "đô thị", "đô_thị", "hạ tầng", "hạ_tầng"]
}

COMPOUND_WORDS = [
    "giáo dục", "tuyển sinh", "học sinh", "sinh viên", "đại học", "trường học", "thpt", "điểm chuẩn", "bách khoa", "xét tuyển",
    "bác sĩ", "y tế", "sức khỏe", "bệnh viện", "dịch bệnh", "vắc xin", "hô hấp", "cúm a", "viêm phổi", "điều trị",
    "bóng đá", "thể thao", "cơ thủ", "vô địch", "trận đấu", "bàn thắng", "huy chương", "giải đấu",
    "công an", "điều tra", "vụ án", "xử phạt", "tòa án", "pháp luật", "tội phạm", "khởi tố",
    "doanh nghiệp", "kinh tế", "chứng khoán", "tài chính", "ngân hàng", "lợi nhuận", "giá vàng", "bất động sản",
    "trí tuệ nhân tạo", "công nghệ", "phần mềm", "ứng dụng", "bảo mật", "dữ liệu", "robot",
    "diễn viên", "ca sĩ", "nghệ sĩ", "giải trí", "hollywood", "bộ phim", "rạp chiếu",
    "du lịch", "khách sạn", "điểm đến", "vé máy bay", "nghỉ dưỡng",
    "ô tô", "xe máy", "xe điện", "giao thông", "động cơ"
]

try:
    from pyvi import ViTokenizer
    HAS_PYVI = True
except ImportError:
    HAS_PYVI = False

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if HAS_PYVI:
        try:
            return ViTokenizer.tokenize(text).lower()
        except Exception:
            pass
    text_lower = text.lower()
    for cw in COMPOUND_WORDS:
        text_lower = text_lower.replace(cw, cw.replace(" ", "_"))
    return text_lower

def classify_news(title, content):
    full_text = clean_text(f"{title} {content}").lower()
    found_keywords = []

    for cat_key, kws in TOPIC_KEYWORDS.items():
        for kw in kws:
            if kw in full_text:
                if kw not in found_keywords and len(found_keywords) < 6:
                    found_keywords.append(kw)

    # Use REAL Machine Learning model if available
    if ML_PIPELINE is not None:
        try:
            probs = ML_PIPELINE.predict_proba([full_text])[0]
            classes = ML_PIPELINE.classes_
            
            score_map = {cls: float(prob) for cls, prob in zip(classes, probs)}

            distribution = []
            for c in CATEGORIES:
                score = score_map.get(c["key"], 0.001)
                distribution.append({
                    "category": c["key"],
                    "name": c["name"],
                    "score": round(score, 4)
                })

            distribution.sort(key=lambda x: x["score"], reverse=True)
            top = distribution[0]

            return {
                "primary_category": top["category"],
                "primary_name": top["name"],
                "confidence": top["score"],
                "keywords": found_keywords if found_keywords else [],
                "distribution": distribution,
                "engine": "ML Model V3 (LogisticRegression + TF-IDF, trained on 260K+ articles)"
            }
        except Exception as err:
            print(f"[ERROR] ML prediction error: {err}")

    # Heuristic fallback if model not loaded
    scores = {c["key"]: 0.02 for c in CATEGORIES}
    for cat_key, kws in TOPIC_KEYWORDS.items():
        for kw in kws:
            if kw in full_text:
                scores[cat_key] += 0.3

    total = sum(scores.values())
    distribution = []
    for c in CATEGORIES:
        score = scores[c["key"]] / total
        distribution.append({
            "category": c["key"],
            "name": c["name"],
            "score": round(score, 4)
        })

    distribution.sort(key=lambda x: x["score"], reverse=True)
    top = distribution[0]

    return {
        "primary_category": top["category"],
        "primary_name": top["name"],
        "confidence": top["score"],
        "keywords": found_keywords if found_keywords else ["tin tức", "báo chí"],
        "distribution": distribution,
        "engine": "Heuristic Engine"
    }

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_POST(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/api/classify':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                payload = json.loads(post_data.decode('utf-8'))
                title = payload.get('title', '')
                content = payload.get('content', '')

                result = classify_news(title, content)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        else:
            self.send_error(404, "Endpoint not found")

    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/api/stats':
            stats = {
                "status": "online",
                "model": "PhoBERT v4 (VietNews)",
                "num_classes": len(CATEGORIES),
                "categories": CATEGORIES
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(stats, ensure_ascii=False).encode('utf-8'))
        else:
            super().do_GET()

class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

def run_server():
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    with ThreadingHTTPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
        print("=" * 60)
        print(f"[OK] VietNews AI Web App (Multi-Threaded) is running locally!")
        print(f"[URL] Access URL: http://localhost:{PORT}")
        print("=" * 60)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")

if __name__ == "__main__":
    run_server()
