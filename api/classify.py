import os
import json
import joblib
from pathlib import Path
from pyvi import ViTokenizer
from http.server import BaseHTTPRequestHandler

BASE_DIR = Path(__file__).parent.parent
MODEL_PATH = BASE_DIR / "web" / "news_model.joblib"

MODEL_PIPELINE = None
if MODEL_PATH.exists():
    try:
        MODEL_PIPELINE = joblib.load(MODEL_PATH)
    except Exception as e:
        print(f"Model load error: {e}")

CATEGORIES_MAP = {
    "cong-nghe": "Công nghệ",
    "kinh-doanh": "Kinh doanh",
    "the-thao": "Thể thao",
    "thoi-su": "Thời sự",
    "giai-tri": "Giải trí",
    "suc-khoe": "Sức khỏe",
    "giao-duc": "Giáo dục",
    "phap-luat": "Pháp luật",
    "du-lich": "Du lịch",
    "doi-song": "Đời sống",
    "xe": "Xe / Ô tô"
}

def clean_text(text):
    if not text:
        return ""
    text = str(text).lower()
    text = ViTokenizer.tokenize(text)
    return text

def extract_keywords(text, top_n=5):
    words = clean_text(text).split()
    unique_words = []
    stopwords = {"và", "của", "là", "có", "trong", "đã", "được", "cho", "với", "không", "các", "người", "như", "khi", "tại", "đang", "đến", "này", "về", "ra", "những"}
    for w in words:
        w_clean = w.replace("_", " ")
        if len(w) > 2 and w not in stopwords and w_clean not in unique_words:
            unique_words.append(w_clean)
        if len(unique_words) >= top_n:
            break
    return unique_words

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            body = json.loads(post_data.decode('utf-8'))
            title = body.get('title', '')
            content = body.get('content', '')
            full_text = f"{title} {content}".strip()

            if not full_text:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Vui lòng nhập nội dung"}, ensure_ascii=False).encode('utf-8'))
                return

            if MODEL_PIPELINE is None:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Model không thể tải"}, ensure_ascii=False).encode('utf-8'))
                return

            cleaned = clean_text(full_text)
            probs = MODEL_PIPELINE.predict_proba([cleaned])[0]
            classes = MODEL_PIPELINE.classes_

            results = []
            for cls_name, prob in zip(classes, probs):
                results.append({
                    "category": cls_name,
                    "name": CATEGORIES_MAP.get(cls_name, cls_name),
                    "score": float(prob)
                })

            results.sort(key=lambda x: x["score"], reverse=True)
            top_result = results[0]
            keywords = extract_keywords(full_text)

            response_data = {
                "primary_category": top_result["category"],
                "primary_name": top_result["name"],
                "confidence": top_result["score"],
                "distribution": results,
                "keywords": keywords,
                "engine": "PhoBERT V4 (Vercel Serverless + PyVi)"
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}, ensure_ascii=False).encode('utf-8'))
