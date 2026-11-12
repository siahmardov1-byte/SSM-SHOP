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

# Оғози сервер дар паси саҳна (background thread)
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

# --- Crypto (CryptoBot / Crypto Pay API) ---
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
BUTTON_EMOJIS = ["🛒", "💰", "📦", "❓", "🤝", "⚙️", "⬅️", "✅", "✖️", "➕", "✏️", "🗑", "🧹",
                 "❌", "👥", "💳", "📤", "🔎", "🛍", "⭐", "✨", "🔥", "🖼", "📝", "👁",
                 "🏠", "💱", "💵", "👇", "🎉", "⚠️", "🕒", "🔗", "🎁", "🔒", "➡️", "🏆", "📢",
                 "🟢", "🟡", "🔴", "🧾", "🔢", "🎟", "💎", "🏦", "📱", "📎", "🏙", "🚗", "📨", "🔐", "👤", "🆕"]

db = sqlite3.connect(DB_PATH)
db.execute("PRAGMA journal_mode=WAL")
db.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, name TEXT, username TEXT, joined INTEGER)")
db.execute("CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, price INTEGER, active INTEGER DEFAULT 1)")
db.execute("CREATE TABLE IF NOT EXISTS stock(id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, data TEXT, used_by INTEGER, used_at INTEGER, price_paid INTEGER)")
db.execute("CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, stars INTEGER, coins INTEGER, charge_id TEXT UNIQUE, ts INTEGER, refunded INTEGER DEFAULT 0)")
db.execute("CREATE TABLE IF NOT EXISTS tx(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, kind TEXT, note TEXT, ts INTEGER)")
for _sql in ("ALTER TABLE users ADD COLUMN referrer INTEGER",
             "ALTER TABLE payments ADD COLUMN ref_user INTEGER",
             "ALTER TABLE payments ADD COLUMN ref_bonus INTEGER",
             "ALTER TABLE products ADD COLUMN photo TEXT",
             "ALTER TABLE products ADD COLUMN descr TEXT",
             "ALTER TABLE users ADD COLUMN blocked INTEGER DEFAULT 0"):
    try:
        db.execute(_sql)
    except sqlite3.OperationalError:
        pass
db.execute("CREATE TABLE IF NOT EXISTS emoji_map(emoji TEXT PRIMARY KEY, cid TEXT)")
db.execute("CREATE TABLE IF NOT EXISTS ref_rewards(user_id INTEGER, need INTEGER, reward INTEGER, ts INTEGER, PRIMARY KEY(user_id, need))")
db.execute("CREATE TABLE IF NOT EXISTS ratings(user_id INTEGER, product_id INTEGER, stars INTEGER, ts INTEGER, PRIMARY KEY(user_id, product_id))")
db.execute("CREATE TABLE IF NOT EXISTS promos(code TEXT PRIMARY KEY, bonus INTEGER, max_uses INTEGER DEFAULT 0, used INTEGER DEFAULT 0, expires INTEGER, active INTEGER DEFAULT 1, created INTEGER)")
db.execute("CREATE TABLE IF NOT EXISTS promo_uses(user_id INTEGER, code TEXT, ts INTEGER, PRIMARY KEY(user_id, code))")
db.execute("CREATE TABLE IF NOT EXISTS crypto_invoices(id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_id INTEGER UNIQUE, user_id INTEGER, amount REAL, coins INTEGER, status TEXT DEFAULT 'active', ts INTEGER, paid_at INTEGER)")
db.execute("CREATE TABLE IF NOT EXISTS rub_requests(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, coins INTEGER, status TEXT DEFAULT 'new', file_id TEXT, file_uid TEXT, ts INTEGER, done_at INTEGER)")
db.execute("CREATE TABLE IF NOT EXISTS stock_notify(user_id INTEGER, product_id INTEGER, PRIMARY KEY(user_id, product_id))")
db.execute("CREATE TABLE IF NOT EXISTS cars(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, price INTEGER, photo TEXT, descr TEXT, active INTEGER DEFAULT 1)")
db.execute("CREATE TABLE IF NOT EXISTS car_orders(id INTEGER PRIMARY KEY AUTOINCREMENT, car_id INTEGER, user_id INTEGER, title TEXT, price INTEGER, status TEXT DEFAULT 'paid', account TEXT, ts INTEGER, done_at INTEGER)")
try:
    db.execute("ALTER TABLE rub_requests ADD COLUMN method TEXT DEFAULT 'tbank'")
except sqlite3.OperationalError:
    pass
db.commit()

TOPUP_WAIT = set()
SUPPORT_WAIT = set()
PROMO_WAIT = set()
CTOPUP_WAIT = set()
RUB_WAIT = set()
DC_WAIT = set()
CAR_WAIT = {}
LAST_CRYPTO_SYNC = 0
ADMIN_STATE = {}
BCAST = {}
BCAST_RUNNING = False

# ======================= Telegram API & Logic =======================
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

EMOJI_MAP = {}
FALLBACK = {}

def norm_emoji(e):
    return e.replace("\ufe0f", "")

def load_emoji():
    EMOJI_MAP.clear()
    for e, c in db.execute("SELECT emoji, cid FROM emoji_map").fetchall():
        EMOJI_MAP[e] = c

def _btn(text, extra, style=None):
    prefix, _, rest = text.partition(" ")
    cid = EMOJI_MAP.get(norm_emoji(prefix)) if rest else None
    if cid:
        FALLBACK[(rest, cid)] = prefix
        b = {"text": rest, "icon_custom_emoji_id": cid}
    else:
        b = {"text": text}
    if style and BUTTON_STYLES:
        b["style"] = style
    b.update(extra)
    return b

def cb(text, data, style=None):
    return _btn(text, {"callback_data": data}, style)

def url_btn(text, url, style=None):
    return _btn(text, {"url": url}, style)

def markup(*rows):
    return {"inline_keyboard": [list(r) for r in rows if r]}

def is_fancy(buttons):
    return bool(buttons) and any("icon_custom_emoji_id" in b or "style" in b for row in buttons["inline_keyboard"] for b in row)

def strip_fancy(buttons):
    rows = []
    for row in buttons["inline_keyboard"]:
        new_row = []
        for b in row:
            b = dict(b)
            cid = b.pop("icon_custom_emoji_id", None)
            b.pop("style", None)
            if cid:
                pre = FALLBACK.get((b["text"], cid), "")
                b["text"] = (pre + " " + b["text"]).strip()
            new_row.append(b)
        rows.append(new_row)
    return {"inline_keyboard": rows}

def decorate(text):
    if not EMOJI_MAP or not text:
        return []
    ents, off, i = [], 0, 0
    while i < len(text):
        j = i + 1
        if j < len(text) and text[j] == "\ufe0f":
            j += 1
        seg = text[i:j]
        length = len(seg.encode("utf-16-le")) // 2
        cid = EMOJI_MAP.get(text[i])
        if cid:
            ents.append({"type": "custom_emoji", "offset": off, "length": length, "custom_emoji_id": cid})
        off += length
        i = j
    return ents

def _variants(buttons, has_ents):
    v = [(buttons, True)] if has_ents else [(buttons, False)]
    if has_ents:
        v.append((buttons, False))
    if is_fancy(buttons):
        v.append((strip_fancy(buttons), False))
    return v

CODE_OPEN, CODE_CLOSE = "\u27e6", "\u27e7"

def code(d):
    d = str(d).replace(CODE_OPEN, "").replace(CODE_CLOSE, "")
    return f"{CODE_OPEN}{d}{CODE_CLOSE}" if d.strip() else d

def prepare(text):
    if not text or CODE_OPEN not in text:
        return text, decorate(text)
    clean, ranges = "", []
    for part in re.split(f"({CODE_OPEN}.*?{CODE_CLOSE})", text, flags=re.S):
        if part.startswith(CODE_OPEN) and part.endswith(CODE_CLOSE) and len(part) >= 2:
            inner = part[1:-1]
            start = len(clean.encode("utf-16-le")) // 2
            clean += inner
            if inner.strip():
                ranges.append((start, len(inner.encode("utf-16-le")) // 2))
        else:
            clean += part
    ents = [e for e in decorate(clean) if not any(e["offset"] < st + ln and st < e["offset"] + e["length"] for st, ln in ranges)]
    ents += [{"type": "code", "offset": st, "length": ln} for st, ln in ranges]
    ents.sort(key=lambda e: e["offset"])
    return clean, ents

def send(chat_id, text, buttons=None):
    clean, ents = prepare(text)
    last = None
    for b, use in _variants(buttons, bool(ents)):
        p = {"chat_id": chat_id, "text": clean}
        if b:
            p["reply_markup"] = b
        if use:
            p["entities"] = ents
        try:
            return api("sendMessage", **p)
        except Exception as e:
            last = e
    print("send error:", last)
    return None

def send_photo(chat_id, file_id, caption, buttons=None):
    clean, ents = prepare(caption)
    clean = clean[:1024]
    lim = len(clean.encode("utf-16-le")) // 2
    ents = [e for e in ents if e["offset"] + e["length"] <= lim]
    last = None
    for b, use in _variants(buttons, bool(ents)):
        p = {"chat_id": chat_id, "photo": file_id, "caption": clean}
        if b:
            p["reply_markup"] = b
        if use:
            p["caption_entities"] = ents
        try:
            return api("sendPhoto", **p)
        except Exception as e:
            last = e
    print("send_photo error:", last)
    return None

def delete_msg(chat_id, msg_id):
    if not msg_id:
        return
    try:
        api("deleteMessage", chat_id=chat_id, message_id=msg_id)
    except Exception:
        pass

def edit(chat_id, msg_id, text, buttons=None):
    if not msg_id:
        return send(chat_id, text, buttons)
    clean, ents = prepare(text)
    for b, use in _variants(buttons, bool(ents)):
        p = {"chat_id": chat_id, "message_id": msg_id, "text": clean}
        if b:
            p["reply_markup"] = b
        if use:
            p["entities"] = ents
        try:
            return api("editMessageText", **p)
        except Exception as e:
            s_ = str(e)
            if "not modified" in s_:
                return None
            if "no text in the message" in s_:
                res = send(chat_id, text, buttons)
                if res:
                    delete_msg(chat_id, msg_id)
                return res
    return send(chat_id, text, buttons)

def show(chat_id, msg_id, screen):
    return edit(chat_id, msg_id, screen[0], screen[1])

def ensure_user(user):
    uid = user["id"]
    name = (user.get("first_name", "") + " " + user.get("last_name", "")).strip()
    is_new = db.execute("SELECT 1 FROM users WHERE user_id=?", (uid,)).fetchone() is None
    db.execute("INSERT OR IGNORE INTO users(user_id, balance, joined) VALUES(?,0,?)", (uid, int(time.time())))
    db.execute("UPDATE users SET name=?, username=?, blocked=0 WHERE user_id=?", (name, user.get("username", ""), uid))
    db.commit()
    return is_new

def referrer_of(uid):
    r = db.execute("SELECT referrer FROM users WHERE user_id=?", (uid,)).fetchone()
    return r[0] if r and r[0] else None

def invited_count(uid):
    return db.execute("SELECT COUNT(*) FROM users WHERE referrer=?", (uid,)).fetchone()[0]

def balance(uid):
    r = db.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
    return r[0] if r else 0

def add_tx(uid, amount, kind, note=""):
    db.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
    db.execute("INSERT INTO tx(user_id, amount, kind, note, ts) VALUES(?,?,?,?,?)", (uid, amount, kind, note, int(time.time())))

def name_of(uid):
    r = db.execute("SELECT name, username FROM users WHERE user_id=?", (uid,)).fetchone()
    name, uname = r if r else ("", "")
    s = name or str(uid)
    if uname:
        s += f" (@{uname})"
    return f"{s} [{uid}]"

def fmt_time(ts):
    return time.strftime("%d.%m.%Y %H:%M", time.gmtime(ts + TZ_OFFSET)) if ts else "—"

def stock_count(pid):
    return db.execute("SELECT COUNT(*) FROM stock WHERE product_id=? AND used_by IS NULL", (pid,)).fetchone()[0]

SEP = "━━━━━━━━━━━━━━"

def stock_icon(n):
    return "🟢" if n >= 3 else ("🟡" if n > 0 else "🔴")

def back_row(text="⬅️ Меню", data="menu"):
    return [cb(text, data)]

def crypto_enabled():
    return bool(CRYPTO_TOKEN)

def crypto_api(method, **params):
    base = "https://testnet-pay.crypt.bot/api/" if CRYPTO_TESTNET else "https://pay.crypt.bot/api/"
    req = urllib.request.Request(
        base + method, data=json.dumps(params).encode(),
        headers={"Content-Type": "application/json", "Crypto-Pay-API-Token": CRYPTO_TOKEN,
                 "User-Agent": "Mozilla/5.0 (Linux; Android 13) SSMShopBot/1.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode("utf-8", "ignore"))
    if not data.get("ok"):
        raise RuntimeError(str(data))
    return data["result"]

def fmt_amount(a):
    return f"{a:.2f}".rstrip("0").rstrip(".")

def crypto_sync():
    pass

def method_cfg(method):
    return {"name": TBANK_NAME, "unit": "₽", "rate": TBANK_RATE, "min": TBANK_MIN,
            "max": TBANK_MAX, "presets": TBANK_PRESETS, "pre": "rub", "icon": "🏦"}

def rub_enabled():
    return TBANK_ENABLED and bool(TBANK_CARD or TBANK_PHONE)

def dc_enabled():
    return DC_ENABLED and bool(DC_PHONE)

def screen_menu(uid):
    r = db.execute("SELECT name FROM users WHERE user_id=?", (uid,)).fetchone()
    first = ((r[0] or "").split() or [""])[0] if r else ""
    buys = db.execute("SELECT COUNT(*) FROM stock WHERE used_by=?", (uid,)).fetchone()[0]
    text = (f"🏠 Главное меню\n{SEP}\n" +
            (f"👋 Привет, {first}!\n\n" if first else "\n") +
            f"💰 Баланс: {balance(uid)} {COIN}\n"
            f"📦 Покупок: {buys}\n\n"
            "Выберите раздел 👇")
    rows = [[cb("🛒 Аккаунты", "shop", "primary"), cb("🚗 Машины", "cars", "primary")],
            [cb("💰 Пополнить", "topup", "success"), cb("📦 Мои покупки", "buys:0")],
            [cb("🎟 Промокод", "promo"), cb("🤝 Друзья и бонусы", "ref")],
            [cb("❓ Помощь", "help")]]
    if uid == ADMIN_ID:
        rows.append([cb("⚙️ Админ-панель", "admin")])
    return text, markup(*rows)

def screen_help(uid):
    return "❓ Помощь\n\nБот работает в штатном режиме.", markup(back_row())

def screen_ref(uid):
    return "🤝 Реферальная система", markup(back_row())

def screen_shop(uid, page=0):
    rows = db.execute("SELECT id, title, price FROM products WHERE active=1 ORDER BY id").fetchall()
    if not rows:
        return ("🛒 Аккаунтов пока нет. Загляните позже!", markup(back_row()))
    kb = [[cb(f"{t} — {pr} {COIN}", f"p:{i}")] for i, t, pr in rows]
    kb.append(back_row())
    return "🛒 Аккаунты 👇", markup(*kb)

def get_product(pid):
    return db.execute("SELECT id, title, price FROM products WHERE id=? AND active=1", (pid,)).fetchone()

def product_extra(pid):
    r = db.execute("SELECT photo, descr FROM products WHERE id=?", (pid,)).fetchone()
    return (r[0], r[1] or "") if r else (None, "")

def screen_topup(uid):
    return f"💰 Пополнение баланса\n\nТекущий баланс: {balance(uid)} {COIN}", markup(back_row())

def screen_buys(uid, page=0):
    return "📦 Ваши покупки", markup(back_row())

def screen_promo_ask():
    return "🎟 Введите промокод", markup(back_row())

def screen_cars(uid, note=""):
    return "🚗 Машины", markup(back_row())

def handle_message(msg):
    if msg["chat"]["type"] != "private":
        return
    user = msg["from"]
    uid = user["id"]
    ensure_user(user)
    text = msg.get("text", "") or ""

    if text.startswith("/start") or text.startswith("/menu"):
        t, kb = screen_menu(uid)
        send(uid, t, kb)
        return
    
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
        show(uid, mid, screen_menu(uid))

def handle_pre_checkout(pq):
    try:
        api("answerPreCheckoutQuery", pre_checkout_query_id=pq["id"], ok=True)
    except Exception:
        pass

# ======================= Асоси (Main Polling) =======================
def main():
    global BOT_USERNAME
    if not BOT_TOKEN:
        print("❌ Токен не найден.")
        return
    print("Бот-магазин ва веб-сервер бомуваффақият ба кор даромаданд...")
    load_emoji()
    try:
        BOT_USERNAME = api("getMe")["username"]
    except Exception as e:
        print("getMe error:", e)
    
    offset = 0
    while True:
        try:
            updates = api("getUpdates", offset=offset, timeout=10,
                          allowed_updates=["message", "callback_query", "pre_checkout_query"])
            for u in updates:
                offset = u["update_id"] + 1
                try:
                    if "pre_checkout_query" in u:
                        handle_pre_checkout(u["pre_checkout_query"])
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
    # Оғози лучи асосии бот дар пасгоҳ (thread) ё мустақиман
    main()
