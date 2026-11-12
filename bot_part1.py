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
        pass  # Барои пешгирии пур шудани логҳо бо дархостҳои HTTP

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

# Оғози сервер дар паси саҳна (background thread) бе халал расонидан ба бот
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# ======================= Танзимот =======================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "9111340924:AAG8R57fDM0ybiRt28I8lgOMHO3xEW0ppSA")
ADMIN_ID = 8731580691
COIN = "SSM"                 # номи коини бот
RATE = 1                     # 1 ⭐ = RATE коин
MAX_TOPUP = 10000            # ҳадди аксар барои як пуркунӣ (⭐)
TOPUP_PRESETS = [10, 25, 50, 100, 250, 500]
PAGE = 5                     # чанд харид дар як саҳифа
TZ_OFFSET = 5 * 3600         # UTC+5 (Тоҷикистон)
BUTTON_STYLES = True         # тугмаҳои рангин (Bot API 9.4+)
DB_PATH = os.environ.get("DB_PATH", "shop.db")
REF_PERCENT = 10             # реферал аз ҳар пуркунии дӯсташ чанд % SSM мегирад
BOT_USERNAME = ""            # худкор аз Telegram гирифта мешавад
QTY_OPTIONS = [1, 2, 5, 10]  # чанд адад якбора харидан мумкин (тугмаҳо)
MAX_QTY = 50                 # ҳадди аксар барои як харид (ҳимоя)
BULK_DISCOUNTS = [(5, 5), (10, 10)]   # (аз чанд адад, тахфиф %)
REF_MILESTONES = [(3, 10), (5, 20), (10, 50)]
REF_REQUIRE_TOPUP = False    # True = дӯст танҳо баъди як пуркунӣ ҳисоб мешавад

# --- Crypto ---
CRYPTO_TOKEN = os.environ.get("CRYPTO_TOKEN", "672153:AAuwpMacIwZlLHBD2gZTpdUU0d5LfshLksS")
CRYPTO_TESTNET = False
CRYPTO_ASSET = "USDT"
CRYPTO_RATE = 50
CRYPTO_PRESETS = [1, 2, 5, 10, 20]
CRYPTO_MIN = 0.5
CRYPTO_MAX = 1000
CRYPTO_EXPIRES = 3600
CRYPTO_SYNC_EVERY = 10

# --- Т-Банк ---
TBANK_ENABLED = True
TBANK_NAME = "Т-Банк"
TBANK_CARD = "2200702190668116"
TBANK_PHONE = "+7 999 000-06-98"
TBANK_HOLDER = ""
TBANK_RATE = 1
TBANK_MIN = 50
TBANK_MAX = 100000
TBANK_PRESETS = [50, 100, 200, 500, 1000]
TBANK_MAX_PENDING = 3

# --- Душанбе Сити ---
DC_ENABLED = True
DC_NAME = "Душанбе Сити"
DC_PHONE = "934185556"
DC_HOLDER = ""
DC_RATE = 8
DC_MIN = 6
DC_MAX = 20000
DC_PRESETS = [10, 20, 50, 100, 200]
CAR_DONE_TEXT = "Заходите в игру и проверяйте. Рекомендуем сменить пароль аккаунта."

db = sqlite3.connect(DB_PATH)
db.execute("PRAGMA journal_mode=WAL")
db.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, name TEXT, username TEXT, joined INTEGER)")
db.execute("CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, price INTEGER, active INTEGER DEFAULT 1)")
db.execute("CREATE TABLE IF NOT EXISTS stock(id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, data TEXT, used_by INTEGER, used_at INTEGER, price_paid INTEGER)")
db.execute("CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, stars INTEGER, coins INTEGER, charge_id TEXT UNIQUE, ts INTEGER, refunded INTEGER DEFAULT 0)")
db.execute("CREATE TABLE IF NOT EXISTS tx(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, kind TEXT, note TEXT, ts INTEGER)")
db.commit()

print("Web server & Bot initialized successfully.")
