# server.py
from flask import Flask, request, jsonify, abort
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/check": {"origins": [
    "https://actual-website-for-terasure-hunt.onrender.com"
]}})

@app.after_request
def add_cors_headers(resp):
    resp.headers.setdefault("Vary", "Origin")
    resp.headers.setdefault("Access-Control-Allow-Methods", "POST, OPTIONS")
    resp.headers.setdefault("Access-Control-Allow-Headers", "Content-Type")
    return resp

@app.route("/check", methods=["POST", "OPTIONS"])
def check():
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.get_json(silent=True) or {}
    code = str(data.get("code", "")).strip()

    # Accept only 6 or 7 digits
    if not (code.isdigit() and len(code) in (6, 7)):
        return jsonify({"ok": False, "reason": "bad_format"}), 200

    # look up message from your ANSWERS dict (server-side secret)
    msg = ANSWERS.get(code)
    if not msg:
        return jsonify({"ok": False}), 200

    return jsonify({"ok": True, "message": msg}), 200

@app.errorhandler(429)
def ratelimited(e):
    return jsonify({"ok": False, "reason": "rate_limited"}), 429


import os, json, time
from flask import Flask, request, jsonify, abort

app = Flask(__name__)

# Load the answers from an environment variable (keep repo public and secrets private!)
# Example value (as JSON) in env: {"123456":"Clue #1", "314159":"Clue #2", "271828":"Final prize!"}
ANSWERS = {}
ANSWERS_JSON = os.getenv("ANSWERS_JSON", "")
if ANSWERS_JSON:
    try:
        ANSWERS = json.loads(ANSWERS_JSON)
    except Exception:
        # If env var is bad, keep empty to avoid leaking anything
        ANSWERS = {}

# Simple in-memory IP rate limit to deter brute forcing
WINDOW_SECONDS = 60
MAX_TRIES_PER_WINDOW = 100
ATTEMPTS = {}  # ip -> [timestamps]

def limited(ip: str) -> bool:
    now = time.time()
    bucket = ATTEMPTS.get(ip, [])
    bucket = [t for t in bucket if now - t < WINDOW_SECONDS]
    if len(bucket) >= MAX_TRIES_PER_WINDOW:
        ATTEMPTS[ip] = bucket
        return True
    bucket.append(now)
    ATTEMPTS[ip] = bucket
    return False

@app.route("/check", methods=["POST"])
def check():
    # Get caller IP (Render passes the real one; behind proxies you could trust X-Forwarded-For)
    ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"
    if limited(ip):
        abort(429, description="Too many attempts, try again soon.")

    data = request.get_json(silent=True) or {}
    code = str(data.get("code", "")).strip()

    # Basic format check (6 digits)
    if not (code.isdigit() and len(code) >= 6):
        return jsonify({"ok": False, "reason": "bad_format"}), 200

    msg = ANSWERS.get(code)
    if not msg:
        return jsonify({"ok": False}), 200

    # Success: return only the message (don’t reveal the full map!)
    return jsonify({"ok": True, "message": msg}), 200

@app.get("/health")
def health():
    return "ok", 200

if __name__ == "__main__":
    # Local dev
    app.run(host="0.0.0.0", port=5050, debug=True)



