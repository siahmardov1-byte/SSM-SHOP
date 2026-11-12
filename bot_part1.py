import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import json
import sqlite3
import time
import urllib.request
import urllib.error

# ======================= Танзимот =======================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "9111340924:AAG8R57fDM0ybiRt28I8lgOMHO3xEW0ppSA")
DB_PATH = os.environ.get("DB_PATH", "shop.db")
COIN = "SSM"

db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.execute("PRAGMA journal_mode=WAL")
db.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, name TEXT, username TEXT, joined INTEGER)")
db.execute("CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, price INTEGER, active INTEGER DEFAULT 1)")
db.execute("CREATE TABLE IF NOT EXISTS stock(id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, data TEXT, used_by INTEGER, used_at INTEGER, price_paid INTEGER)")
db.commit()

def api(method, **params):
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
        data=json.dumps(params).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)["result"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode("utf-8", "ignore"))

def ensure_user(user):
    uid = user["id"]
    name = (user.get("first_name", "") + " " + user.get("last_name", "")).strip()
    db.execute("INSERT OR IGNORE INTO users(user_id, balance, joined) VALUES(?,0,?)", (uid, int(time.time())))
    db.execute("UPDATE users SET name=?, username=?, blocked=0 WHERE user_id=?", (name, user.get("username", ""), uid))
    db.commit()

def send(chat_id, text):
    try:
        api("sendMessage", chat_id=chat_id, text=text)
    except Exception as e:
        print("send error:", e)

def handle_message(msg):
    if msg.get("chat", {}).get("type") != "private":
        return
    user = msg["from"]
    uid = user["id"]
    ensure_user(user)
    text = msg.get("text", "")
    if text.startswith("/start"):
        send(uid, f"🏠 Бот-магазин {COIN} успешно запущен и работает!")
    else:
        send(uid, "Используйте /start для открытия меню.")

# ======================= 1. Веб-сервер барои Render =======================
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is live and running!")
    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    print(f"Web server started on port {port}")
    server.serve_forever()

# ======================= 2. Боти Telegram (Polling) =======================
def run_bot():
    print("Telegram bot polling started...")
    offset = 0
    while True:
        try:
            updates = api("getUpdates", offset=offset, timeout=10, allowed_updates=["message", "callback_query"])
            for u in updates:
                offset = u["update_id"] + 1
                if "message" in u:
                    handle_message(u["message"])
        except Exception as e:
            print("poll error:", e)
            time.sleep(5)

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ Токен не найден.")
    else:
        # Оғози веб-сервер дар паси саҳна
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # Оғози бот дар потоки асосӣ
        run_bot()
