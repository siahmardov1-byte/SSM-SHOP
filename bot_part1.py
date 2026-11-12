import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import json
import re
import sqlite3
import time
import urllib.request
import urllib.parse
import urllib.error

# ======================= Веб-сервер барои Render =======================
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")
    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

# Оғози сервер дар потоки алоҳида
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# ======================= Танзимоти асосӣ =======================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "9111340924:AAG8R57fDM0ybiRt28I8lgOMHO3xEW0ppSA")
ADMIN_ID = 8731580691
COIN = "SSM"
RATE = 1
MAX_TOPUP = 10000
TOPUP_PRESETS = [10, 25, 50, 100, 250, 500]
PAGE = 5
TZ_OFFSET = 5 * 3600
BUTTON_STYLES = True
DB_PATH = os.environ.get("DB_PATH", "shop.db")
REF_PERCENT = 10
BOT_USERNAME = ""
QTY_OPTIONS = [1, 2, 5, 10]
MAX_QTY = 50
BULK_DISCOUNTS = [(5, 5), (10, 10)]

CRYPTO_TOKEN = os.environ.get("CRYPTO_TOKEN", "")
CRYPTO_TESTNET = False
CRYPTO_ASSET = "USDT"
CRYPTO_RATE = 50

TBANK_ENABLED = True
TBANK_NAME = "Т-Банк"
TBANK_CARD = "2200702190668116"
TBANK_PHONE = "+7 999 000-06-98"
TBANK_RATE = 1
TBANK_MIN = 50
TBANK_MAX = 100000

DC_ENABLED = True
DC_NAME = "Душанбе Сити"
DC_PHONE = "934185556"
DC_RATE = 8
DC_MIN = 6
DC_MAX = 20000

db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.execute("PRAGMA journal_mode=WAL")
db.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, name TEXT, username TEXT, joined INTEGER)")
db.execute("CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, price INTEGER, active INTEGER DEFAULT 1)")
db.execute("CREATE TABLE IF NOT EXISTS stock(id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, data TEXT, used_by INTEGER, used_at INTEGER, price_paid INTEGER)")
db.execute("CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, stars INTEGER, coins INTEGER, charge_id TEXT UNIQUE, ts INTEGER, refunded INTEGER DEFAULT 0)")
db.execute("CREATE TABLE IF NOT EXISTS tx(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, kind TEXT, note TEXT, ts INTEGER)")
for _sql in ("ALTER TABLE users ADD COLUMN referrer INTEGER",
             "ALTER TABLE products ADD COLUMN photo TEXT",
             "ALTER TABLE products ADD COLUMN descr TEXT",
             "ALTER TABLE users ADD COLUMN blocked INTEGER DEFAULT 0"):
    try:
        db.execute(_sql)
    except sqlite3.OperationalError:
        pass
db.commit()

TOPUP_WAIT = set()
ADMIN_STATE = {}

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

def balance(uid):
    r = db.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
    return r[0] if r else 0

def send(chat_id, text, buttons=None):
    p = {"chat_id": chat_id, "text": text}
    if buttons:
        p["reply_markup"] = buttons
    try:
        return api("sendMessage", **p)
    except Exception as e:
        print("send error:", e)

def markup(*rows):
    return {"inline_keyboard": [list(r) for r in rows if r]}

def cb(text, data):
    return {"text": text, "callback_data": data}

def screen_menu(uid):
    text = f"🏠 Главное меню\n\n💰 Баланс: {balance(uid)} {COIN}\n\nВыберите раздел 👇"
    rows = [[cb("🛒 Аккаунты", "shop"), cb("💰 Пополнить", "topup")]]
    if uid == ADMIN_ID:
        rows.append([cb("⚙️ Админ-панель", "admin")])
    return text, markup(*rows)

def handle_message(msg):
    if msg.get("chat", {}).get("type") != "private":
        return
    user = msg["from"]
    uid = user["id"]
    ensure_user(user)
    text = msg.get("text", "")
    if text.startswith("/start") or text.startswith("/menu"):
        t, kb = screen_menu(uid)
        send(uid, t, kb)
    else:
        t, kb = screen_menu(uid)
        send(uid, t, kb)

def handle_callback(cq):
    try:
        api("answerCallbackQuery", callback_query_id=cq["id"])
    except Exception:
        pass
    user = cq["from"]
    uid = user["id"]
    ensure_user(user)
    data = cq.get("data") or ""
    mid = (cq.get("message") or {}).get("message_id")
    if data == "menu":
        t, kb = screen_menu(uid)
        api("editMessageText", chat_id=uid, message_id=mid, text=t, reply_markup=kb)

# ======================= Оғози Поллинг (Bot Main Loop) =======================
def main():
    global BOT_USERNAME
    if not BOT_TOKEN:
        print("❌ Токен не найден.")
        return
    print("Бот-магазин ва веб-сервер бомуваффақият ба кор даромаданд...")
    try:
        BOT_USERNAME = api("getMe")["username"]
    except Exception as e:
        print("getMe error:", e)
    
    offset = 0
    while True:
        try:
            updates = api("getUpdates", offset=offset, timeout=10, allowed_updates=["message", "callback_query"])
            for u in updates:
                offset = u["update_id"] + 1
                try:
                    if "message" in u:
                        handle_message(u["message"])
                    if "callback_query" in u:
                        handle_callback(u["callback_query"])
                except Exception as e:
                    print("handler error:", e)
        except Exception as e:
            print("poll error:", e)
            time.sleep(5)

if __name__ == "__main__":
    main()
