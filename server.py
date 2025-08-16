from flask import Flask, request, jsonify, abort
from flask_cors import CORS
import os, json, time

app = Flask(__name__)

# Allow only your static site origin (change if your static URL differs)
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "https://actual-website-for-terasure-hunt.onrender.com")
CORS(app, resources={r"/check": {"origins": [ALLOWED_ORIGIN]}}, supports_credentials=False)

# Load answers from env var: e.g. {"123456":"Clue #1","7654321":"Clue #2"}
ANSWERS = {}
ANSWERS_JSON = os.getenv("ANSWERS_JSON", "")
if ANSWERS_JSON:
    try:
        ANSWERS = json.loads(ANSWERS_JSON)
    except Exception:
        ANSWERS = {}

# Simple in-memory rate limit
WINDOW_SECONDS = 60
MAX_TRIES_PER_WINDOW = 100
ATTEMPTS = {}  # ip -> [timestamps]

def limited(ip: str) -> bool:
    now = time.time()
    bucket = [t for t in ATTEMPTS.get(ip, []) if now - t < WINDOW_SECONDS]
    if len(bucket) >= MAX_TRIES_PER_WINDOW:
        ATTEMPTS[ip] = bucket
        return True
    bucket.append(now)
    ATTEMPTS[ip] = bucket
    return False

@app.route("/check", methods=["POST", "OPTIONS"])
def check():
    # CORS preflight handled here (Flask-CORS adds headers)
    if request.method == "OPTIONS":
        return ("", 204)

    ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"
    if limited(ip):
        return jsonify(ok=False, reason="rate_limited"), 429

    data = request.get_json(silent=True) or {}
    code = str(data.get("code", "")).strip()

    # EXACTLY 6 or 7 digits
    if not (code.isdigit() and len(code) in (6, 7)):
        return jsonify(ok=False, reason="bad_format"), 400

    msg = ANSWERS.get(code)
    if not msg:
        return jsonify(ok=False), 200

    return jsonify(ok=True, message=msg), 200

@app.get("/health")
def health():
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5050)), debug=True)
