import json
from http.server import BaseHTTPRequestHandler

CATEGORIES = ["cong-nghe", "kinh-doanh", "the-thao", "thoi-su", "giai-tri", "suc-khoe", "giao-duc", "phap-luat", "du-lich", "doi-song", "xe"]

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        stats = {
            "status": "online",
            "model": "PhoBERT (Vercel Serverless)",
            "num_classes": len(CATEGORIES),
            "categories": CATEGORIES,
            "engine": "PhoBERT (Vercel Serverless)"
        }
        self.wfile.write(json.dumps(stats, ensure_ascii=False).encode('utf-8'))
