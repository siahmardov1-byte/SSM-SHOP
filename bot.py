import json, os, re, sqlite3, threading, time, urllib.request, urllib.parse, urllib.error

# ======================= Танзимот =======================
BOT_TOKEN = "9111340924:AAG8R57fDM0ybiRt28I8lgOMHO3xEW0ppSA"
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
# Мукофот барои даъвати дӯстон: (чанд дӯст, чанд SSM). Метавонед озодона иваз кунед.
REF_MILESTONES = [(3, 10), (5, 20), (10, 50)]
REF_REQUIRE_TOPUP = False    # True = дӯст танҳо баъди як пуркунӣ ҳисоб мешавад (ҳимоя аз аккаунти қалбакӣ)
# --- Crypto (CryptoBot / Crypto Pay API) ---
CRYPTO_TOKEN = os.environ.get("CRYPTO_TOKEN", "672153:AAuwpMacIwZlLHBD2gZTpdUU0d5LfshLksS")   # токен аз @CryptoBot -> Crypto Pay -> Create App
CRYPTO_TESTNET = False       # True = озмоиш тавассути @CryptoTestnetBot
CRYPTO_ASSET = "USDT"        # асъор: USDT, TON ва ғ.
CRYPTO_RATE = 50             # 1 USDT = чанд SSM (ИВАЗ КУНЕД ба нархи худатон!)
CRYPTO_PRESETS = [1, 2, 5, 10, 20]
CRYPTO_MIN = 0.5             # ҳадди ақали як пуркунӣ
CRYPTO_MAX = 1000            # ҳадди аксар
CRYPTO_EXPIRES = 3600        # ҳисоб чанд сония кор мекунад
CRYPTO_SYNC_EVERY = 10       # ҳар чанд сония пардохтҳоро месанҷад
# --- Т-Банк (дастӣ, бо скриншоти чек) ---
TBANK_ENABLED = True
TBANK_NAME = "Т-Банк"
TBANK_CARD = "2200702190668116"        # рақами корт ("" = нишон намедиҳад)
TBANK_PHONE = "+7 999 000-06-98"       # рақами СБП ("" = нишон намедиҳад). САНҶЕД!
TBANK_HOLDER = ""                      # номи гиранда, масалан "Азиз К." (ихтиёрӣ)
TBANK_RATE = 1                         # 1 ₽ = чанд SSM
TBANK_MIN = 50                         # ҳадди ақал (₽)
TBANK_MAX = 100000                     # ҳадди аксар (₽)
TBANK_PRESETS = [50, 100, 200, 500, 1000]
TBANK_MAX_PENDING = 3                  # як корбар чанд дархости кушода дошта метавонад
# --- Душанбе Сити (дастӣ, бо скриншоти чек, сомонӣ) ---
DC_ENABLED = True
DC_NAME = "Душанбе Сити"
DC_PHONE = "934185556"                 # рақами телефон барои интиқол
DC_HOLDER = ""                         # номи гиранда (ихтиёрӣ)
DC_RATE = 8                            # 1 сомонӣ = чанд SSM (1 сомонӣ ≈ 8,8 ₽, 1 ₽ = 1 SSM)
DC_MIN = 6                             # ҳадди ақал (сомонӣ), тақрибан 50 ₽
DC_MAX = 20000
DC_PRESETS = [10, 20, 50, 100, 200]
CAR_DONE_TEXT = "Заходите в игру и проверяйте. Рекомендуем сменить пароль аккаунта."
BUTTON_EMOJIS = ["🛒", "💰", "📦", "❓", "🤝", "⚙️", "⬅️", "✅", "✖️", "➕", "✏️", "🗑", "🧹",
                 "❌", "👥", "💳", "📤", "🔎", "🛍", "⭐", "✨", "🔥", "🖼", "📝", "👁",
                 "🏠", "💱", "💵", "👇", "🎉", "⚠️", "🕒", "🔗", "🎁", "🔒", "➡️", "🏆", "📢",
                 "🟢", "🟡", "🔴", "🧾", "🔢", "🎟", "💎", "🏦", "📱", "📎", "🏙", "🚗", "📨", "🔐", "👤", "🆕"]

db = sqlite3.connect(DB_PATH)
db.execute("PRAGMA journal_mode=WAL")
db.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, "
           "name TEXT, username TEXT, joined INTEGER)")
db.execute("CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, "
           "price INTEGER, active INTEGER DEFAULT 1)")
db.execute("CREATE TABLE IF NOT EXISTS stock(id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, "
           "data TEXT, used_by INTEGER, used_at INTEGER, price_paid INTEGER)")
db.execute("CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, "
           "stars INTEGER, coins INTEGER, charge_id TEXT UNIQUE, ts INTEGER, refunded INTEGER DEFAULT 0)")
db.execute("CREATE TABLE IF NOT EXISTS tx(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, "
           "amount INTEGER, kind TEXT, note TEXT, ts INTEGER)")
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
db.execute("CREATE TABLE IF NOT EXISTS ref_rewards(user_id INTEGER, need INTEGER, reward INTEGER, "
           "ts INTEGER, PRIMARY KEY(user_id, need))")
db.execute("CREATE TABLE IF NOT EXISTS ratings(user_id INTEGER, product_id INTEGER, "
           "stars INTEGER, ts INTEGER, PRIMARY KEY(user_id, product_id))")
# --- Промокодҳо ---
db.execute("CREATE TABLE IF NOT EXISTS promos(code TEXT PRIMARY KEY, bonus INTEGER, "
           "max_uses INTEGER DEFAULT 0, used INTEGER DEFAULT 0, expires INTEGER, "
           "active INTEGER DEFAULT 1, created INTEGER)")
db.execute("CREATE TABLE IF NOT EXISTS promo_uses(user_id INTEGER, code TEXT, ts INTEGER, "
           "PRIMARY KEY(user_id, code))")
# --- Crypto ҳисобҳо ---
db.execute("CREATE TABLE IF NOT EXISTS crypto_invoices(id INTEGER PRIMARY KEY AUTOINCREMENT, "
           "invoice_id INTEGER UNIQUE, user_id INTEGER, amount REAL, coins INTEGER, "
           "status TEXT DEFAULT 'active', ts INTEGER, paid_at INTEGER)")
# --- Т-Банк дархостҳо ---
db.execute("CREATE TABLE IF NOT EXISTS rub_requests(id INTEGER PRIMARY KEY AUTOINCREMENT, "
           "user_id INTEGER, amount INTEGER, coins INTEGER, status TEXT DEFAULT 'new', "
           "file_id TEXT, file_uid TEXT, ts INTEGER, done_at INTEGER)")
# --- Огоҳӣ дар бораи мавҷудшавии мол ---
db.execute("CREATE TABLE IF NOT EXISTS stock_notify(user_id INTEGER, product_id INTEGER, "
           "PRIMARY KEY(user_id, product_id))")
# --- Машинҳо (фармоишҳои дастӣ) ---
db.execute("CREATE TABLE IF NOT EXISTS cars(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, "
           "price INTEGER, photo TEXT, descr TEXT, active INTEGER DEFAULT 1)")
db.execute("CREATE TABLE IF NOT EXISTS car_orders(id INTEGER PRIMARY KEY AUTOINCREMENT, car_id INTEGER, "
           "user_id INTEGER, title TEXT, price INTEGER, status TEXT DEFAULT 'paid', account TEXT, "
           "ts INTEGER, done_at INTEGER)")
try:
    db.execute("ALTER TABLE rub_requests ADD COLUMN method TEXT DEFAULT 'tbank'")
except sqlite3.OperationalError:
    pass
db.commit()

TOPUP_WAIT = set()      # корбароне, ки суммаи дилхоҳро менависанд
SUPPORT_WAIT = set()    # корбароне, ки ба админ мурољиат мекунанд
PROMO_WAIT = set()      # корбароне, ки промокод ворид мекунанд
CTOPUP_WAIT = set()     # корбароне, ки суммаи crypto менависанд
RUB_WAIT = set()        # корбароне, ки суммаи рубл менависанд
DC_WAIT = set()         # корбароне, ки суммаи сомонӣ менависанд
CAR_WAIT = {}           # uid -> order_id (корбар аккаунт мефиристад)
LAST_CRYPTO_SYNC = 0
ADMIN_STATE = {}        # uid -> ҳолати интизорӣ
BCAST = {}              # admin uid -> (chat_id, message_id) паёми омодаи рассылка
BCAST_RUNNING = False


# ======================= Telegram API =======================

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


EMOJI_MAP = {}      # эмодзи -> custom_emoji_id (премиум)
FALLBACK = {}       # (матни тугма, id) -> эмодзии оддӣ


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
    return bool(buttons) and any("icon_custom_emoji_id" in b or "style" in b
                                 for row in buttons["inline_keyboard"] for b in row)


def strip_fancy(buttons):
    """Рангҳо ва эмодзии премиумро мебарорад, эмодзии оддиро ба матн бармегардонад."""
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
    """Эмодзии оддиро дар матн ба премиум-эмодзӣ (entities) иваз мекунад."""
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
            ents.append({"type": "custom_emoji", "offset": off, "length": length,
                         "custom_emoji_id": cid})
        off += length
        i = j
    return ents


def _variants(buttons, has_ents):
    """Тартиби кӯшишҳо: пурра -> бе эмодзии матн -> бе рангу эмодзии тугмаҳо."""
    v = [(buttons, True)] if has_ents else [(buttons, False)]
    if has_ents:
        v.append((buttons, False))
    if is_fancy(buttons):
        v.append((strip_fancy(buttons), False))
    return v


CODE_OPEN, CODE_CLOSE = "\u27e6", "\u27e7"     # ⟦ ⟧ — нишони «нусхабардорӣ бо зер кардан»


def code(d):
    """Матнро чунон нишон медиҳад, ки бо зер кардан нусха шавад."""
    d = str(d).replace(CODE_OPEN, "").replace(CODE_CLOSE, "")
    return f"{CODE_OPEN}{d}{CODE_CLOSE}" if d.strip() else d


def prepare(text):
    """Баргардонад: (матни тоза, entities). Нишонҳои ⟦ ⟧ ба entity-и code табдил мешаванд."""
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
    ents = [e for e in decorate(clean)
            if not any(e["offset"] < st + ln and st < e["offset"] + e["length"] for st, ln in ranges)]
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
            if "no text in the message" in s_:      # паём акс аст — онро нав мекунем
                res = send(chat_id, text, buttons)
                if res:
                    delete_msg(chat_id, msg_id)
                return res
    return send(chat_id, text, buttons)


def show(chat_id, msg_id, screen):
    return edit(chat_id, msg_id, screen[0], screen[1])


# ======================= Корбарон ва баланс =======================

def ensure_user(user):
    """Баргардонад: True агар корбар нав бошад."""
    uid = user["id"]
    name = (user.get("first_name", "") + " " + user.get("last_name", "")).strip()
    is_new = db.execute("SELECT 1 FROM users WHERE user_id=?", (uid,)).fetchone() is None
    db.execute("INSERT OR IGNORE INTO users(user_id, balance, joined) VALUES(?,0,?)",
               (uid, int(time.time())))
    db.execute("UPDATE users SET name=?, username=?, blocked=0 WHERE user_id=?",
               (name, user.get("username", ""), uid))
    db.commit()
    return is_new


def referrer_of(uid):
    r = db.execute("SELECT referrer FROM users WHERE user_id=?", (uid,)).fetchone()
    return r[0] if r and r[0] else None


def invited_count(uid):
    if REF_REQUIRE_TOPUP:
        return db.execute(
            "SELECT COUNT(*) FROM users u WHERE u.referrer=? AND ("
            "EXISTS(SELECT 1 FROM payments p WHERE p.user_id=u.user_id AND p.refunded=0) OR "
            "EXISTS(SELECT 1 FROM crypto_invoices c WHERE c.user_id=u.user_id AND c.status='paid') OR "
            "EXISTS(SELECT 1 FROM rub_requests r WHERE r.user_id=u.user_id AND r.status='approved'))",
            (uid,)).fetchone()[0]
    return db.execute("SELECT COUNT(*) FROM users WHERE referrer=?", (uid,)).fetchone()[0]


def check_milestones(ref):
    """Мукофоти зинапояиро медиҳад, агар шумораи дӯстон расида бошад (як маротиба)."""
    n = invited_count(ref)
    for need, reward in REF_MILESTONES:
        if n < need:
            continue
        cur = db.execute("INSERT OR IGNORE INTO ref_rewards(user_id, need, reward, ts) "
                         "VALUES(?,?,?,?)", (ref, need, reward, int(time.time())))
        if cur.rowcount:
            add_tx(ref, reward, "ref_milestone", str(need))
            db.commit()
            send(ref, f"🎁 Награда за друзей!\nТы пригласил {need} друзей — тебе +{reward} {COIN}\n"
                      f"💰 Баланс: {balance(ref)} {COIN}", markup(back_row()))


def register_referral(uid, text):
    parts = text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].startswith("ref_"):
        return
    code = parts[1][4:]
    if not code.isdigit():
        return
    ref = int(code)
    if ref == uid or not db.execute("SELECT 1 FROM users WHERE user_id=?", (ref,)).fetchone():
        return
    db.execute("UPDATE users SET referrer=? WHERE user_id=? AND referrer IS NULL", (ref, uid))
    db.commit()
    send(ref, "🤝 По вашей ссылке пришёл новый друг! "
              f"Вы получите {REF_PERCENT}% {COIN} с каждого его пополнения.")
    if not REF_REQUIRE_TOPUP:
        check_milestones(ref)


def balance(uid):
    r = db.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
    return r[0] if r else 0


def add_tx(uid, amount, kind, note=""):
    db.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
    db.execute("INSERT INTO tx(user_id, amount, kind, note, ts) VALUES(?,?,?,?,?)",
               (uid, amount, kind, note, int(time.time())))


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
    return db.execute("SELECT COUNT(*) FROM stock WHERE product_id=? AND used_by IS NULL",
                      (pid,)).fetchone()[0]


SEP = "━━━━━━━━━━━━━━"


def stock_icon(n):
    return "🟢" if n >= 3 else ("🟡" if n > 0 else "🔴")


def back_row(text="⬅️ Меню", data="menu"):
    return [cb(text, data)]


# ======================= Crypto пардохт (CryptoBot) =======================

def crypto_enabled():
    return bool(CRYPTO_TOKEN)


def crypto_api(method, **params):
    base = "https://testnet-pay.crypt.bot/api/" if CRYPTO_TESTNET else "https://pay.crypt.bot/api/"
    req = urllib.request.Request(
        base + method, data=json.dumps(params).encode(),
        headers={"Content-Type": "application/json", "Crypto-Pay-API-Token": CRYPTO_TOKEN,
                 "User-Agent": "Mozilla/5.0 (Linux; Android 13) SSMShopBot/1.0",
                 "Accept": "application/json"})
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


def create_crypto_invoice(uid, amount):
    """Ҳисоби crypto месозад. Баргардонад: (invoice_id, url) ё None."""
    coins = int(amount * CRYPTO_RATE)
    if coins < 1:
        return None
    try:
        inv = crypto_api("createInvoice", asset=CRYPTO_ASSET, amount=fmt_amount(amount),
                         description=f"Пополнение: {coins} {COIN}",
                         payload=f"topup:{uid}", expires_in=CRYPTO_EXPIRES,
                         allow_comments=False, allow_anonymous=False)
    except Exception as e:
        print("createInvoice error:", e)
        send(ADMIN_ID, f"⚠️ Crypto Pay: не удалось создать счёт\n{str(e)[:700]}")
        return None
    url = inv.get("bot_invoice_url") or inv.get("pay_url")
    db.execute("INSERT INTO crypto_invoices(invoice_id, user_id, amount, coins, status, ts) "
               "VALUES(?,?,?,?,'active',?)",
               (inv["invoice_id"], uid, amount, coins, int(time.time())))
    db.commit()
    return inv["invoice_id"], url


def credit_crypto(invoice_id):
    """Пардохти тасдиқшударо ба баланс мегузорад (танҳо як маротиба). Баргардонад: (uid, coins) ё None."""
    r = db.execute("SELECT user_id, amount, coins FROM crypto_invoices "
                   "WHERE invoice_id=? AND status='active'", (invoice_id,)).fetchone()
    if not r:
        return None
    uid, amount, coins = r
    cur = db.execute("UPDATE crypto_invoices SET status='paid', paid_at=? "
                     "WHERE invoice_id=? AND status='active'", (int(time.time()), invoice_id))
    if cur.rowcount == 0:
        db.rollback()
        return None
    add_tx(uid, coins, "topup_crypto", str(invoice_id))
    ref = referrer_of(uid)
    bonus = coins * REF_PERCENT // 100 if ref else 0
    if bonus > 0:
        add_tx(ref, bonus, "ref", str(uid))
    db.commit()
    if ref and REF_REQUIRE_TOPUP:
        check_milestones(ref)
    if bonus > 0:
        send(ref, f"🎉 Ваш друг пополнил баланс! Вам начислено +{bonus} {COIN}\n"
                  f"💰 Баланс: {balance(ref)} {COIN}", markup(back_row()))
    send(uid, f"✅ Оплата получена: {fmt_amount(amount)} {CRYPTO_ASSET}\n"
              f"💰 Начислено: +{coins} {COIN}\nТеперь на балансе: {balance(uid)} {COIN}",
         markup([cb("🛒 Аккаунты", "shop")], back_row()))
    send(ADMIN_ID, f"💎 Crypto-пополнение: {fmt_amount(amount)} {CRYPTO_ASSET} ({coins} {COIN})\n"
                   f"От: {name_of(uid)}")
    return uid, coins


def crypto_sync():
    """Ҳамаи ҳисобҳои кушодаро месанҷад ва пардохтшударо ҳисоб мекунад."""
    if not crypto_enabled():
        return
    rows = db.execute("SELECT invoice_id FROM crypto_invoices WHERE status='active' "
                      "ORDER BY id DESC LIMIT 100").fetchall()
    if not rows:
        return
    res = crypto_api("getInvoices", invoice_ids=",".join(str(r[0]) for r in rows), count=100)
    items = res.get("items", []) if isinstance(res, dict) else res
    for it in items:
        st = it.get("status")
        if st == "paid":
            credit_crypto(it["invoice_id"])
        elif st == "expired":
            db.execute("UPDATE crypto_invoices SET status='expired' "
                       "WHERE invoice_id=? AND status='active'", (it["invoice_id"],))
            db.commit()


def screen_ctopup(uid):
    text = (f"💎 Пополнение криптовалютой\n\n"
            f"Текущий баланс: {balance(uid)} {COIN}\n"
            f"Курс: 1 {CRYPTO_ASSET} = {CRYPTO_RATE} {COIN}\n"
            f"Мин.: {fmt_amount(CRYPTO_MIN)} {CRYPTO_ASSET}\n\n"
            f"Оплата через @CryptoBot, монеты начисляются автоматически.\n"
            "Выбери сумму или введи свою 👇")
    kb, row = [], []
    for n in CRYPTO_PRESETS:
        row.append(cb(f"💎 {fmt_amount(n)} {CRYPTO_ASSET}", f"cpay:{n}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([cb("✏️ Другая сумма", "ctopup_custom")])
    kb.append(back_row("⬅️ Пополнение", "topup"))
    return text, markup(*kb)


def start_crypto_payment(uid, mid, amount):
    if not (CRYPTO_MIN <= amount <= CRYPTO_MAX):
        send(uid, f"Сумма должна быть от {fmt_amount(CRYPTO_MIN)} до {CRYPTO_MAX} {CRYPTO_ASSET}.",
             markup([cb("✖️ Отмена", "ctopup")]))
        return
    res = create_crypto_invoice(uid, amount)
    if not res:
        send(uid, "😔 Не удалось создать счёт. Попробуйте позже.", markup(back_row()))
        return
    inv_id, url = res
    coins = int(amount * CRYPTO_RATE)
    text = (f"💎 Счёт создан\n{SEP}\n"
            f"💵 К оплате: {fmt_amount(amount)} {CRYPTO_ASSET}\n"
            f"🎁 Вы получите: {coins} {COIN}\n"
            f"🕒 Счёт действует {CRYPTO_EXPIRES // 60} мин.\n\n"
            "Нажмите «Оплатить», оплатите в @CryptoBot. Монеты придут сами, "
            "обычно в течение минуты. Можно также нажать «Я оплатил».")
    kb = markup([url_btn("💳 Оплатить", url, "success")] if url else [],
                [cb("✅ Я оплатил(а)", f"ccheck:{inv_id}", "primary")],
                back_row("⬅️ Пополнение", "topup"))
    if mid:
        show(uid, mid, (text, kb))
    else:
        send(uid, text, kb)


def check_crypto_payment(uid, mid, inv_id):
    r = db.execute("SELECT user_id, status FROM crypto_invoices WHERE invoice_id=?",
                   (inv_id,)).fetchone()
    if not r or r[0] != uid:
        return
    if r[1] == "paid":
        edit(uid, mid, f"✅ Этот счёт уже оплачен и зачислен.\n💰 Баланс: {balance(uid)} {COIN}",
             markup([cb("🛒 Аккаунты", "shop")], back_row()))
        return
    try:
        res = crypto_api("getInvoices", invoice_ids=str(inv_id))
        items = res.get("items", []) if isinstance(res, dict) else res
        st = items[0].get("status") if items else None
    except Exception as e:
        print("check invoice error:", e)
        st = None
    if st == "paid":
        credit_crypto(inv_id)
        delete_msg(uid, mid)
    elif st == "expired":
        db.execute("UPDATE crypto_invoices SET status='expired' WHERE invoice_id=? AND status='active'",
                   (inv_id,))
        db.commit()
        edit(uid, mid, "⌛ Срок счёта истёк. Создайте новый.",
             markup([cb("💎 Новый счёт", "ctopup")], back_row()))
    else:
        edit(uid, mid, "⏳ Оплата пока не найдена. Если вы уже оплатили, подождите минуту "
                       "и нажмите «Я оплатил» ещё раз.",
             markup([cb("✅ Я оплатил(а)", f"ccheck:{inv_id}", "primary")],
                    back_row("⬅️ Пополнение", "topup")))


# ======================= Пардохти дастӣ бо чек (Т-Банк, Душанбе Сити) =======================

def method_cfg(method):
    if method == "dc":
        return {"name": DC_NAME, "unit": "сомони", "rate": DC_RATE, "min": DC_MIN,
                "max": DC_MAX, "presets": DC_PRESETS, "pre": "dc", "icon": "🏙"}
    return {"name": TBANK_NAME, "unit": "₽", "rate": TBANK_RATE, "min": TBANK_MIN,
            "max": TBANK_MAX, "presets": TBANK_PRESETS, "pre": "rub", "icon": "🏦"}


def rub_enabled():
    return TBANK_ENABLED and bool(TBANK_CARD or TBANK_PHONE)


def dc_enabled():
    return DC_ENABLED and bool(DC_PHONE)


def manual_enabled(method):
    return dc_enabled() if method == "dc" else rub_enabled()


def fmt_card(c):
    c = "".join(ch for ch in c if ch.isdigit())
    return " ".join(c[i:i + 4] for i in range(0, len(c), 4))


def requisites(method):
    lines = []
    if method == "dc":
        lines.append(f"📱 Перевод в {DC_NAME} по номеру:\n    {DC_PHONE}")
        if DC_HOLDER:
            lines.append(f"👤 Получатель: {DC_HOLDER}")
        return "\n".join(lines)
    if TBANK_PHONE:
        lines.append(f"📱 СБП по номеру: {TBANK_PHONE}\n    (банк получателя: {TBANK_NAME})")
    if TBANK_CARD:
        lines.append(f"💳 Карта {TBANK_NAME}: {fmt_card(TBANK_CARD)}")
    if TBANK_HOLDER:
        lines.append(f"👤 Получатель: {TBANK_HOLDER}")
    return "\n".join(lines)


def screen_rub(uid, method="tbank"):
    c = method_cfg(method)
    text = (f"{c['icon']} Пополнение через {c['name']} ({c['unit']})\n\n"
            f"Текущий баланс: {balance(uid)} {COIN}\n"
            f"Курс: 1 {c['unit']} = {c['rate']} {COIN}\n"
            f"Мин.: {c['min']} {c['unit']}\n\n"
            "Выбери сумму или введи свою 👇")
    kb, row = [], []
    for n in c["presets"]:
        row.append(cb(f"{c['icon']} {n} {c['unit']}", f"{c['pre']}pay:{n}"))
        if len(row) == 3:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([cb("✏️ Другая сумма", f"{c['pre']}_custom")])
    kb.append(back_row("⬅️ Пополнение", "topup"))
    return text, markup(*kb)


def start_rub_request(uid, mid, amount, method="tbank"):
    c = method_cfg(method)
    if not (c["min"] <= amount <= c["max"]):
        send(uid, f"Сумма должна быть от {c['min']} до {c['max']} {c['unit']}.",
             markup([cb("✖️ Отмена", c["pre"])]))
        return
    now = int(time.time())
    open_n = db.execute("SELECT COUNT(*) FROM rub_requests WHERE user_id=? AND status='pending'",
                        (uid,)).fetchone()[0]
    if open_n >= TBANK_MAX_PENDING:
        send(uid, "⏳ У вас уже есть заявки на проверке. Дождитесь ответа администратора.",
             markup(back_row()))
        return
    # дархости кӯҳнаи «new»-ро мебандем, то ҳамеша як дархости фаъол бошад
    db.execute("UPDATE rub_requests SET status='cancelled' WHERE user_id=? AND status='new'", (uid,))
    coins = amount * c["rate"]
    cur = db.execute("INSERT INTO rub_requests(user_id, amount, coins, status, ts, method) "
                     "VALUES(?,?,?,'new',?,?)", (uid, amount, coins, now, method))
    db.commit()
    rid = cur.lastrowid
    text = (f"{c['icon']} Заявка #{rid}\n{SEP}\n"
            f"💵 Переведите ровно: {amount} {c['unit']}\n"
            f"🎁 Вы получите: {coins} {COIN}\n\n"
            f"{requisites(method)}\n{SEP}\n"
            "📎 После оплаты отправьте сюда скриншот чека (фото).\n"
            "Администратор проверит перевод, обычно это занимает несколько минут.\n\n"
            "⚠️ Переводите точную сумму, иначе заявку могут отклонить.")
    kb = markup([cb("✖️ Отмена", f"rubcancel:{rid}", "danger")])
    if mid:
        show(uid, mid, (text, kb))
    else:
        send(uid, text, kb)


def send_proof(chat_id, stored, caption, buttons):
    """stored: file_id (акс) ё 'd:'+file_id (ҳуҷҷат)."""
    if stored.startswith("d:"):
        last = None
        for b in (buttons, strip_fancy(buttons) if is_fancy(buttons) else None):
            if b is None:
                continue
            try:
                return api("sendDocument", chat_id=chat_id, document=stored[2:],
                           caption=caption[:1024], reply_markup=b)
            except Exception as e:
                last = e
        print("send_proof doc error:", last)
        return None
    return send_photo(chat_id, stored, caption, buttons)


def rub_admin_kb(rid):
    return markup([cb("✅ Подтвердить", f"rubok:{rid}", "success"),
                   cb("❌ Отклонить", f"rubno:{rid}", "danger")])


def rub_caption(rid, uid, amount, coins, method="tbank"):
    c = method_cfg(method or "tbank")
    return (f"{c['icon']} Заявка #{rid} ({c['name']})\nОт: {name_of(uid)}\n"
            f"💵 Сумма: {amount} {c['unit']} → {coins} {COIN}\n\n"
            "Сверьте чек и поступление в банке, затем подтвердите.")


def handle_rub_proof(msg, uid):
    """Агар корбар чек фиристад ва дархости кушода дошта бошад — True."""
    ph, doc = msg.get("photo"), msg.get("document")
    if ph:
        stored, fuid = ph[-1]["file_id"], ph[-1].get("file_unique_id")
    elif doc and (doc.get("mime_type") or "").startswith("image/"):
        stored, fuid = "d:" + doc["file_id"], doc.get("file_unique_id")
    else:
        return False
    r = db.execute("SELECT id, amount, coins, method FROM rub_requests WHERE user_id=? "
                   "AND status='new' AND ts>? ORDER BY id DESC LIMIT 1",
                   (uid, int(time.time()) - 86400)).fetchone()
    if not r:
        return False
    rid, amount, coins, method = r
    c = method_cfg(method or "tbank")
    if fuid and db.execute("SELECT 1 FROM rub_requests WHERE file_uid=?", (fuid,)).fetchone():
        send(uid, "⚠️ Этот чек уже был отправлен ранее. Пришлите актуальный чек.",
             markup([cb("✖️ Отмена", f"rubcancel:{rid}", "danger")]))
        return True
    db.execute("UPDATE rub_requests SET status='pending', file_id=?, file_uid=? "
               "WHERE id=? AND status='new'", (stored, fuid, rid))
    db.commit()
    send(uid, f"✅ Чек получен! Заявка #{rid} на {amount} {c['unit']} отправлена на проверку.\n"
              f"Как только админ подтвердит, на баланс придёт {coins} {COIN}.",
         markup([cb("🛒 Аккаунты", "shop")], back_row()))
    if not send_proof(ADMIN_ID, stored, rub_caption(rid, uid, amount, coins, method), rub_admin_kb(rid)):
        send(ADMIN_ID, f"{c['icon']} Новая заявка #{rid} от {name_of(uid)}: {amount} {c['unit']}, "
                       "но чек не удалось переслать. Откройте её в «Заявки».",
             markup([cb("🏦 Заявки", "a_rub")]))
    return True


def approve_rub(admin_id, rid):
    r = db.execute("SELECT user_id, amount, coins, status, method FROM rub_requests WHERE id=?",
                   (rid,)).fetchone()
    if not r:
        send(admin_id, "Заявка не найдена.")
        return
    uid, amount, coins, status, method = r
    c = method_cfg(method or "tbank")
    if status != "pending":
        send(admin_id, f"Заявка #{rid} уже обработана (статус: {status}).")
        return
    cur = db.execute("UPDATE rub_requests SET status='approved', done_at=? "
                     "WHERE id=? AND status='pending'", (int(time.time()), rid))
    if cur.rowcount == 0:
        db.rollback()
        return
    add_tx(uid, coins, "topup_rub", str(rid))
    ref = referrer_of(uid)
    bonus = coins * REF_PERCENT // 100 if ref else 0
    if bonus > 0:
        add_tx(ref, bonus, "ref", str(uid))
    db.commit()
    if ref and REF_REQUIRE_TOPUP:
        check_milestones(ref)
    if bonus > 0:
        send(ref, f"🎉 Ваш друг пополнил баланс! Вам начислено +{bonus} {COIN}\n"
                  f"💰 Баланс: {balance(ref)} {COIN}", markup(back_row()))
    send(uid, f"✅ Оплата подтверждена: {amount} {c['unit']}\n💰 Начислено: +{coins} {COIN}\n"
              f"Теперь на балансе: {balance(uid)} {COIN}",
         markup([cb("🛒 Аккаунты", "shop")], back_row()))
    send(admin_id, f"✅ Заявка #{rid} подтверждена: {amount} {c['unit']} → {coins} {COIN}\n"
                   f"Пользователь: {name_of(uid)}", markup([cb("🏦 Заявки", "a_rub")], admin_back()))


def reject_rub(admin_id, rid):
    r = db.execute("SELECT user_id, amount, status, method FROM rub_requests WHERE id=?",
                   (rid,)).fetchone()
    if not r:
        send(admin_id, "Заявка не найдена.")
        return
    uid, amount, status, method = r
    c = method_cfg(method or "tbank")
    if status != "pending":
        send(admin_id, f"Заявка #{rid} уже обработана (статус: {status}).")
        return
    cur = db.execute("UPDATE rub_requests SET status='rejected', done_at=? "
                     "WHERE id=? AND status='pending'", (int(time.time()), rid))
    if cur.rowcount == 0:
        db.rollback()
        return
    db.commit()
    send(uid, f"❌ Заявка #{rid} ({amount} {c['unit']}) отклонена: перевод не найден.\n"
              "Если вы оплатили, напишите администратору: /paysupport",
         markup(back_row()))
    send(admin_id, f"❌ Заявка #{rid} отклонена.", markup([cb("🏦 Заявки", "a_rub")], admin_back()))


def screen_arub():
    rows = db.execute("SELECT id, user_id, amount, method FROM rub_requests WHERE status='pending' "
                      "ORDER BY id").fetchall()
    kb = []
    for i, u, a, m in rows[:30]:
        c = method_cfg(m or "tbank")
        kb.append([cb(f"{c['icon']} #{i} — {a} {c['unit']} — {name_of(u)[:25]}", f"rubv:{i}")])
    kb.append(admin_back())
    text = (f"🏦 Заявки на проверке: {len(rows)}\n\nНажми на заявку, чтобы увидеть чек."
            if rows else "🏦 Заявок на проверке нет.")
    return text, markup(*kb)


# ======================= Машины (заказы вручную) =======================

def car_get(cid):
    return db.execute("SELECT id, title, price, photo, descr FROM cars WHERE id=? AND active=1",
                      (cid,)).fetchone()


def pair_rows(buttons):
    """Тугмаҳоро ду-дуӣ дар як қатор мегузорад."""
    rows = []
    for i in range(0, len(buttons), 2):
        rows.append(buttons[i:i + 2])
    return rows


def screen_cars(uid, note=""):
    rows = db.execute("SELECT id, title, price FROM cars WHERE active=1 ORDER BY id").fetchall()
    open_n = db.execute("SELECT COUNT(*) FROM car_orders WHERE user_id=? AND status IN ('paid','sent')",
                        (uid,)).fetchone()[0]
    kb = pair_rows([cb(t, f"car:{i}", "primary") for i, t, _pr in rows])
    if uid == ADMIN_ID:
        kb.append([cb("➕ Добавить кнопку", "caradd", "success"),
                   cb("🗑 Удалить кнопку", "cardel", "danger")])
    kb.append([cb("🧾 Мои заказы" + (f" ({open_n})" if open_n else ""), "carorders")])
    kb.append([cb("👤 Аккаунты", "shop", "primary")])
    kb.append(back_row())
    if rows:
        text = f"{note}🚗 Машины\n{SEP}\n💰 Ваш баланс: {balance(uid)} {COIN}\n\nВыберите раздел 👇"
    else:
        text = f"{note}🚗 В этом разделе пока ничего нет. Загляните позже!"
        if uid == ADMIN_ID:
            text += "\n\nНажмите «➕ Добавить кнопку», чтобы создать первую."
    return text, markup(*kb)


def screen_car_delete(uid):
    rows = db.execute("SELECT id, title FROM cars WHERE active=1 ORDER BY id").fetchall()
    kb = pair_rows([cb(f"🗑 {t}", f"cardel1:{i}", "danger") for i, t in rows])
    kb.append(back_row("⬅️ Машины", "cars"))
    text = ("🗑 Удаление кнопки\n\nНажмите на кнопку, которую нужно удалить 👇"
            if rows else "Удалять нечего: кнопок нет.")
    return text, markup(*kb)


def screen_car(uid, cid):
    c = car_get(cid)
    if not c:
        return screen_cars(uid)
    _, title, price, _photo, descr = c
    bal = balance(uid)
    text = f"🚗 {title}\n{SEP}\n\n"
    if descr:
        text += f"📝 {descr}\n\n"
    text += (f"💵 Цена: {price} {COIN}\n💰 Ваш баланс: {bal} {COIN}\n\n"
             "ℹ️ После оплаты вы отправите данные своего аккаунта, "
             "и администратор установит машину.")
    kb = []
    if bal < price:
        text += f"\n\n⚠️ Не хватает {price - bal} {COIN}."
        kb.append([cb("💰 Пополнить баланс", "topup", "primary")])
    else:
        kb.append([cb(f"✅ Купить за {price} {COIN}", f"carbuy:{cid}", "success")])
    if uid == ADMIN_ID:
        kb.append([cb("⚙️ Управлять", f"a_car:{cid}")])
    kb.append(back_row("⬅️ Машины", "cars"))
    return text, markup(*kb)


def show_car(uid, mid, cid):
    text, kb = screen_car(uid, cid)
    c = car_get(cid)
    if c and c[3]:
        if send_photo(uid, c[3], text, kb):
            delete_msg(uid, mid)
            return
    show(uid, mid, (text, kb))


def screen_car_confirm(uid, cid):
    c = car_get(cid)
    if not c:
        return screen_cars(uid)
    _, title, price, _p, _d = c
    bal = balance(uid)
    text = f"🧾 Подтверждение покупки\n{SEP}\n\n🚗 Машина: {title}\n💵 Итого: {price} {COIN}\n"
    if bal < price:
        text += f"\n⚠️ Не хватает {price - bal} {COIN}."
        return text, markup([cb("💰 Пополнить баланс", "topup", "primary")],
                            back_row("⬅️ Машина", f"car:{cid}"))
    text += f"💰 Баланс после покупки: {bal - price} {COIN}"
    return text, markup([cb("✅ Подтвердить", f"carok:{cid}", "success"),
                         cb("✖️ Отмена", f"car:{cid}", "danger")])


def do_buy_car(uid, cid):
    """Баргардонад: ('ok', oid) | ('nobal', need) | ('gone', None) | ('fail', None)."""
    c = car_get(cid)
    if not c:
        return "gone", None
    _, title, price, _p, _d = c
    if balance(uid) < price:
        return "nobal", price - balance(uid)
    cur = db.execute("INSERT INTO car_orders(car_id, user_id, title, price, status, ts) "
                     "VALUES(?,?,?,?,'paid',?)", (cid, uid, title, price, int(time.time())))
    oid = cur.lastrowid
    add_tx(uid, -price, "buy_car", f"{title} #{oid}")
    db.commit()
    text = (f"✅ Оплата прошла!\n🚗 Заказ #{oid} — {title}\n{SEP}\n\n"
            "⚠️ Сначала выйдите из аккаунта в игре.\n"
            "Затем нажмите кнопку ниже и отправьте данные аккаунта (логин и пароль).")
    kb = markup([cb("📤 Отправить аккаунт", f"caracc:{oid}", "success")],
                [cb("🧾 Мои заказы", "carorders")], back_row())
    if not send(uid, text, kb):
        db.execute("UPDATE car_orders SET status='refunded' WHERE id=?", (oid,))
        add_tx(uid, price, "car_refund", f"#{oid}")
        db.commit()
        send(ADMIN_ID, f"⚠️ Не удалось отправить заказ #{oid} пользователю {name_of(uid)}. "
                       "Покупка отменена, SSM возвращены.")
        return "fail", None
    send(ADMIN_ID, f"🚗 Новый заказ #{oid}: {title} — {price} {COIN}\n"
                   f"Покупатель: {name_of(uid)}\nОжидает отправки данных аккаунта.")
    return "ok", oid


def ask_car_account(uid, mid, oid):
    r = db.execute("SELECT title, status FROM car_orders WHERE id=? AND user_id=?", (oid, uid)).fetchone()
    if not r:
        return
    title, status = r
    if status not in ("paid", "sent"):
        edit(uid, mid, "ℹ️ Этот заказ уже обработан.",
             markup([cb("🧾 Мои заказы", "carorders")], back_row()))
        return
    CAR_WAIT[uid] = oid
    text = f"📤 Заказ #{oid} — {title}\n\n"
    if status == "sent":
        text += "Данные уже отправлены. Если хотите изменить, отправьте новые.\n\n"
    text += ("⚠️ Сначала выйдите из аккаунта в игре.\n\n"
             "Отправьте одним сообщением:\nлогин : пароль\n\n"
             "Например:\nali123@mail.com : Pass777")
    edit(uid, mid, text, markup([cb("✖️ Отмена", "carorders")]))


def car_admin_kb(oid):
    return markup([cb("✅ Готово", f"cdone:{oid}", "success"),
                   cb("❌ Отклонить", f"cno:{oid}", "danger")])


def handle_car_account(uid, text, msg_id=None):
    oid = CAR_WAIT.get(uid)
    acc = text.strip()[:500]
    r = db.execute("SELECT title, status FROM car_orders WHERE id=? AND user_id=?",
                   (oid, uid)).fetchone() if oid else None
    if not r or r[1] not in ("paid", "sent"):
        CAR_WAIT.pop(uid, None)
        send(uid, "ℹ️ Этот заказ уже обработан.", markup([cb("🧾 Мои заказы", "carorders")], back_row()))
        return
    if len(acc) < 3:
        send(uid, "Отправьте данные в формате: логин : пароль",
             markup([cb("✖️ Отмена", "carorders")]))
        return
    title = r[0]
    db.execute("UPDATE car_orders SET status='sent', account=? WHERE id=? AND user_id=? "
               "AND status IN ('paid','sent')", (acc, oid, uid))
    db.commit()
    CAR_WAIT.pop(uid, None)
    if msg_id:
        delete_msg(uid, msg_id)     # паролро аз чати корбар тоза мекунем
    send(uid, "⏳ Данные отправлены. Ожидайте.\n🔒 Сообщение с паролем удалено из чата для безопасности.",
         markup([cb("🧾 Мои заказы", "carorders")], back_row()))
    send(ADMIN_ID, f"🚗 Заказ #{oid} — {title}\nПокупатель: {name_of(uid)}\n\n"
                   f"🔐 Аккаунт (нажмите, чтобы скопировать):\n{code(acc)}\n\n"
                   "Установите машину и нажмите «Готово».", car_admin_kb(oid))


def screen_car_orders(uid):
    rows = db.execute("SELECT id, title, price, status FROM car_orders WHERE user_id=? "
                      "ORDER BY id DESC LIMIT 10", (uid,)).fetchall()
    if not rows:
        return ("🧾 У вас пока нет заказов машин.", markup([cb("🚗 Машины", "cars")], back_row()))
    names = {"paid": "ждём ваш аккаунт 📤", "sent": "отправлено, ожидайте ⏳",
             "done": "готово ✅", "refunded": "возвращено ↩️"}
    lines, kb = ["🧾 Ваши заказы машин\n"], []
    for oid, title, price, st in rows:
        lines.append(f"#{oid} {title} — {price} {COIN}\n    {names.get(st, st)}")
        if st == "paid":
            kb.append([cb(f"📤 Отправить аккаунт — #{oid}", f"caracc:{oid}", "success")])
        elif st == "sent":
            kb.append([cb(f"✏️ Изменить аккаунт — #{oid}", f"caracc:{oid}")])
    kb.append([cb("🚗 Машины", "cars")])
    kb.append(back_row())
    return "\n".join(lines), markup(*kb)


def admin_car_done_prompt(admin_id, oid):
    r = db.execute("SELECT title, status FROM car_orders WHERE id=?", (oid,)).fetchone()
    if not r or r[1] != "sent":
        send(admin_id, "Заказ уже обработан или ещё ждёт аккаунт.")
        return
    ADMIN_STATE[admin_id] = ("cardone", oid)
    send(admin_id, f"✅ Заказ #{oid} — {r[0]}\n\nНапишите сообщение покупателю "
                   "(оно придёт вместе с «Машина готова») или нажмите кнопку для стандартного текста.\n\n"
                   "/cancel — отмена",
         markup([cb("📨 Отправить стандартное", f"cdonestd:{oid}", "success")],
                [cb("✖️ Отмена", "admin")]))


def finish_car_order(admin_id, oid, note=None):
    ADMIN_STATE.pop(admin_id, None)
    r = db.execute("SELECT user_id, title, status FROM car_orders WHERE id=?", (oid,)).fetchone()
    if not r or r[2] != "sent":
        send(admin_id, "Заказ уже обработан.")
        return
    uid, title, _st = r
    cur = db.execute("UPDATE car_orders SET status='done', account=NULL, done_at=? "
                     "WHERE id=? AND status='sent'", (int(time.time()), oid))
    db.commit()
    if cur.rowcount == 0:
        return
    body = (note or "").strip() or CAR_DONE_TEXT
    res = send(uid, f"🎉 Ваша машина готова!\n🚗 {title}\n\n{body}\n\nСпасибо за покупку! ❤️",
               markup([cb("🚗 Машины", "cars")], back_row()))
    extra = "" if res else "\n⚠️ Но сообщение покупателю не доставлено (возможно, заблокировал бота)."
    send(admin_id, f"✅ Заказ #{oid} завершён, покупатель уведомлён.{extra}",
         markup([cb("🚗 Заказы", "a_corders")], admin_back()))


def refund_car_order(admin_id, oid):
    r = db.execute("SELECT user_id, title, price, status FROM car_orders WHERE id=?", (oid,)).fetchone()
    if not r or r[3] not in ("paid", "sent"):
        send(admin_id, "Заказ уже обработан.")
        return
    uid, title, price, _st = r
    cur = db.execute("UPDATE car_orders SET status='refunded', account=NULL, done_at=? "
                     "WHERE id=? AND status IN ('paid','sent')", (int(time.time()), oid))
    if cur.rowcount == 0:
        db.rollback()
        return
    add_tx(uid, price, "car_refund", f"#{oid}")
    db.commit()
    CAR_WAIT.pop(uid, None)
    send(uid, f"❌ Заказ #{oid} ({title}) отклонён. {price} {COIN} возвращены на баланс.\n"
              f"💰 Баланс: {balance(uid)} {COIN}", markup([cb("🚗 Машины", "cars")], back_row()))
    send(admin_id, f"↩️ Заказ #{oid} отклонён, {price} {COIN} возвращены покупателю.",
         markup([cb("🚗 Заказы", "a_corders")], admin_back()))


def send_admin_order(admin_id, oid):
    r = db.execute("SELECT user_id, title, price, status, account FROM car_orders WHERE id=?",
                   (oid,)).fetchone()
    if not r:
        send(admin_id, "Заказ не найден.")
        return
    uid, title, price, st, acc = r
    if st == "sent":
        send(admin_id, f"🚗 Заказ #{oid} — {title} ({price} {COIN})\nПокупатель: {name_of(uid)}\n\n"
                       f"🔐 Аккаунт (нажмите, чтобы скопировать):\n{code(acc)}", car_admin_kb(oid))
    elif st == "paid":
        send(admin_id, f"🚗 Заказ #{oid} — {title} ({price} {COIN})\nПокупатель: {name_of(uid)}\n\n"
                       "Ждём, пока покупатель отправит аккаунт.",
             markup([cb("❌ Отклонить и вернуть", f"cno:{oid}", "danger")]))
    else:
        send(admin_id, f"Заказ #{oid} уже обработан (статус: {st}).")


def screen_acars():
    rows = db.execute("SELECT id, title, price FROM cars WHERE active=1 ORDER BY id").fetchall()
    waiting = db.execute("SELECT COUNT(*) FROM car_orders WHERE status IN ('paid','sent')").fetchone()[0]
    kb = [[cb(f"🚗 {t} — {pr} {COIN}", f"a_car:{i}")] for i, t, pr in rows]
    kb.append([cb(f"📋 Заказы в работе ({waiting})", "a_corders")])
    kb.append([cb("➕ Новая машина", "a_newcar")])
    kb.append(admin_back())
    text = "🚗 Машины\n\nНажми на машину, чтобы управлять ею." if rows else \
           "🚗 Машин пока нет. Создай первую 👇"
    return text, markup(*kb)


def screen_acar(cid, note=""):
    c = car_get(cid)
    if not c:
        return screen_acars()
    _, title, price, photo, descr = c
    sold = db.execute("SELECT COUNT(*) FROM car_orders WHERE car_id=? AND status='done'",
                      (cid,)).fetchone()[0]
    short = ((descr or "")[:80] + "…") if len(descr or "") > 80 else (descr or "нет")
    text = (f"{note}🚗 {title}\n\n💵 Цена: {price} {COIN}\n✅ Продано: {sold}\n"
            f"🖼 Фото: {'есть ✅' if photo else 'нет'}\n📝 Описание: {short}")
    kb = markup(
        [cb("🖼 Фото", f"a_carphoto:{cid}"), cb("📝 Описание", f"a_cardesc:{cid}")],
        [cb("🗑 Убрать фото", f"a_carnophoto:{cid}")] if photo else [],
        [cb("👁 Как видит покупатель", f"a_carview:{cid}")],
        [cb("✏️ Изменить цену", f"a_carprice:{cid}"), cb("✏️ Название", f"a_cartitle:{cid}")],
        [cb("❌ Удалить машину", f"a_carrm:{cid}", "danger")],
        [cb("⬅️ Машины", "a_cars")])
    return text, kb


def screen_acorders():
    rows = db.execute("SELECT id, user_id, title, status FROM car_orders "
                      "WHERE status IN ('paid','sent') ORDER BY (status='sent') DESC, id").fetchall()
    kb = []
    for oid, u, title, st in rows[:30]:
        mark = "🔐" if st == "sent" else "⏳"
        kb.append([cb(f"{mark} #{oid} {title} — {name_of(u)[:22]}", f"cview:{oid}")])
    kb.append([cb("⬅️ Машины", "a_cars")])
    text = ("📋 Заказы машин в работе\n\n🔐 — аккаунт получен, ждёт вас\n⏳ — ждём аккаунт от покупателя"
            if rows else "📋 Заказов в работе нет.")
    return text, markup(*kb)


# ======================= Промокодҳо =======================

PROMO_RE = re.compile(r"^[A-Z0-9_]{3,20}$")


def redeem_promo(uid, code):
    """Баргардонад: (статус, бонус). Статус: ok | bad | expired | limit | already."""
    code = (code or "").strip().upper()
    r = db.execute("SELECT bonus, max_uses, used, expires, active FROM promos WHERE code=?",
                   (code,)).fetchone()
    if not r or not r[4]:
        return "bad", 0
    bonus, mx, used, exp, _active = r
    now = int(time.time())
    if exp and now > exp:
        return "expired", 0
    if mx and used >= mx:
        return "limit", 0
    cur = db.execute("INSERT OR IGNORE INTO promo_uses(user_id, code, ts) VALUES(?,?,?)",
                     (uid, code, now))
    if cur.rowcount == 0:
        db.commit()
        return "already", 0
    cur2 = db.execute("UPDATE promos SET used=used+1 WHERE code=? AND (max_uses=0 OR used<max_uses)",
                      (code,))
    if cur2.rowcount == 0:      # дар ҳамин лаҳза лимит тамом шуд
        db.rollback()
        return "limit", 0
    add_tx(uid, bonus, "promo", code)
    db.commit()
    return "ok", bonus


def promo_alive(row):
    """row = (code, bonus, max_uses, used, expires, active)"""
    _c, _b, mx, used, exp, act = row
    return bool(act) and not (exp and time.time() > exp) and (not mx or used < mx)


def screen_promo_ask():
    return ("🎟 Промокод\n\nОтправьте промокод одним сообщением 👇",
            markup([cb("✖️ Отмена", "menu")]))


# ======================= Баҳодиҳӣ (⭐ 1-5) =======================

def rating_info(pid):
    r = db.execute("SELECT COUNT(*), AVG(stars) FROM ratings WHERE product_id=?", (pid,)).fetchone()
    return (r[0], r[1]) if r and r[0] else (0, 0)


def rating_line(pid):
    n, avg = rating_info(pid)
    return f"⭐ Рейтинг: {avg:.1f} из 5 ({n})" if n else ""


def rating_kb(pid):
    return markup([cb(f"⭐ {i}", f"rate:{pid}:{i}", "success" if i == 5 else "primary")
                   for i in range(1, 6)],
                  back_row())


def send_rating_request(uid, pid):
    """Баъд аз харид аз харидор баҳо мепурсад (агар пештар баҳо надода бошад)."""
    p = get_product(pid)
    if not p:
        return
    if db.execute("SELECT 1 FROM ratings WHERE user_id=? AND product_id=?", (uid, pid)).fetchone():
        return
    caption = f"⭐ Оцените покупку\n\n🛍 {p[1]}\n\nВыберите оценку 👇"
    photo = product_extra(pid)[0]
    if photo and send_photo(uid, photo, caption, rating_kb(pid)):
        return
    send(uid, caption, rating_kb(pid))


def handle_rate(cq):
    uid = cq["from"]["id"]
    mid = (cq.get("message") or {}).get("message_id")
    try:
        _, pid_s, n_s = cq["data"].split(":")
        pid, n = int(pid_s), int(n_s)
    except ValueError:
        return
    bought = db.execute("SELECT 1 FROM stock WHERE used_by=? AND product_id=? LIMIT 1",
                        (uid, pid)).fetchone()
    if not (1 <= n <= 5) or not bought:
        return
    db.execute("INSERT OR REPLACE INTO ratings VALUES(?,?,?,?)", (uid, pid, n, int(time.time())))
    db.commit()
    row = db.execute("SELECT title FROM products WHERE id=?", (pid,)).fetchone()
    title = row[0] if row else "Товар"
    edit(uid, mid, f"✅ Спасибо за оценку!\n\n🛍 {title}\n{'⭐' * n}{'☆' * (5 - n)}  {n} из 5",
         markup([cb("🛒 Аккаунты", "shop")], back_row()))
    if n <= 2:
        send(ADMIN_ID, f"⚠️ Низкая оценка {n}/5\nТовар: {title}\nОт: {name_of(uid)}")


# ======================= Экранҳои корбар =======================

def clear_waits(uid):
    TOPUP_WAIT.discard(uid)
    SUPPORT_WAIT.discard(uid)
    PROMO_WAIT.discard(uid)
    CTOPUP_WAIT.discard(uid)
    RUB_WAIT.discard(uid)
    DC_WAIT.discard(uid)
    CAR_WAIT.pop(uid, None)


def screen_menu(uid):
    r = db.execute("SELECT name FROM users WHERE user_id=?", (uid,)).fetchone()
    first = ((r[0] or "").split() or [""])[0] if r else ""
    buys = db.execute("SELECT COUNT(*) FROM stock WHERE used_by=?", (uid,)).fetchone()[0] + \
        db.execute("SELECT COUNT(*) FROM car_orders WHERE user_id=? AND status='done'",
                   (uid,)).fetchone()[0]
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
    text = ("❓ Как это работает\n\n"
            f"1️⃣ Нажми «Пополнить» и оплати Telegram Stars ⭐. 1 ⭐ = {RATE} {COIN}.\n"
            f"2️⃣ Монеты {COIN} сразу появятся на балансе.\n"
            "3️⃣ В разделе «Аккаунты» выбери товар и нажми «Купить» — данные придут в чат "
            "(нажми на них, чтобы скопировать).\n"
            "4️⃣ Все покупки всегда лежат в разделе «Мои покупки».\n"
            f"5️⃣ Есть промокод? Нажми «Промокод» и получи бонус {COIN}.\n"
            "6️⃣ «Машины»: оплати, отправь данные аккаунта — админ установит машину.\n\n"
            "💬 Вопросы по оплате и возврату: /paysupport")
    return text, markup([cb("🛒 Аккаунты", "shop")], back_row())


def screen_ref(uid):
    if not BOT_USERNAME:
        return "Реферальная ссылка скоро будет доступна.", markup(back_row())
    invited = db.execute("SELECT COUNT(*) FROM users WHERE referrer=?", (uid,)).fetchone()[0]
    counted = invited_count(uid)
    earned = db.execute("SELECT COALESCE(SUM(amount),0) FROM tx WHERE user_id=? "
                        "AND kind IN ('ref','ref_revoke','ref_milestone')", (uid,)).fetchone()[0]
    goals = []
    for need, reward in REF_MILESTONES:
        mark = "✅" if counted >= need else "🔒"
        goals.append(f"{mark} {need} друзей — +{reward} {COIN}")
    nxt = next((need for need, _ in REF_MILESTONES if counted < need), None)
    goals_text = "\n".join(goals)
    if nxt:
        goals_text += f"\n\n➡️ До следующей награды: ещё {nxt - counted}"
    else:
        goals_text += "\n\n🏆 Ты получил все награды!"
    if REF_REQUIRE_TOPUP:
        goals_text += "\n(друг засчитывается после первого пополнения)"
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
    text = (f"🤝 Друзья и бонусы\n\n"
            f"Приглашай друзей и получай {REF_PERCENT}% {COIN} с каждого их пополнения!\n\n"
            f"🔗 Твоя ссылка:\n{link}\n\n"
            f"🎁 Награды за друзей:\n{goals_text}\n\n"
            f"👥 Приглашено друзей: {invited}\n"
            f"💰 Заработано: {earned} {COIN}")
    share = "https://t.me/share/url?url=" + urllib.parse.quote(link) + \
            "&text=" + urllib.parse.quote("🛒 Магазин аккаунтов! Заходи по моей ссылке 👇")
    return text, markup([url_btn("📤 Поделиться ссылкой", share)], back_row())


SHOP_PAGE = 8


def screen_shop(uid, page=0):
    rows = db.execute(
        "SELECT id, title, price FROM products WHERE active=1 ORDER BY id").fetchall()
    if not rows:
        return ("🛒 Аккаунтов пока нет. Загляните позже!", markup(back_row()))
    items = [(pid, t, pr, stock_count(pid)) for pid, t, pr in rows]
    items.sort(key=lambda x: (x[3] == 0, x[0]))          # аввал онҳое, ки ҳастанд
    pages = (len(items) + SHOP_PAGE - 1) // SHOP_PAGE
    page = max(0, min(page, pages - 1))
    kb = []
    for pid, t, pr, n in items[page * SHOP_PAGE:(page + 1) * SHOP_PAGE]:
        if n:
            kb.append([cb(f"{stock_icon(n)} {t} — {pr} {COIN} · {n} шт.", f"p:{pid}", "primary")])
        else:
            kb.append([cb(f"🔴 {t} — нет в наличии", f"p:{pid}")])
    nav = []
    if page > 0:
        nav.append(cb("‹ Назад", f"shop:{page - 1}"))
    if pages > 1:
        nav.append(cb(f"{page + 1}/{pages}", f"shop:{page}"))
    if page < pages - 1:
        nav.append(cb("Вперёд ›", f"shop:{page + 1}"))
    if nav:
        kb.append(nav)
    kb.append(back_row())
    avail = sum(1 for x in items if x[3])
    text = (f"🛒 Аккаунты\n{SEP}\n"
            f"💰 Ваш баланс: {balance(uid)} {COIN}\n"
            f"📦 В наличии: {avail} из {len(items)}\n\n"
            "🟢 много   🟡 мало   🔴 нет в наличии\n\n"
            "Выберите аккаунт 👇")
    return text, markup(*kb)


def get_product(pid):
    return db.execute("SELECT id, title, price FROM products WHERE id=? AND active=1",
                      (pid,)).fetchone()


def product_extra(pid):
    r = db.execute("SELECT photo, descr FROM products WHERE id=?", (pid,)).fetchone()
    return (r[0], r[1] or "") if r else (None, "")


def bulk_percent(qty):
    pct = 0
    for need, p in BULK_DISCOUNTS:
        if qty >= need:
            pct = p
    return pct


def calc_total(price, qty):
    """Нархи умумӣ бо тахфиф (ба боло мудаввар мешавад)."""
    raw = price * qty * (100 - bulk_percent(qty))
    return -(-raw // 100)


def screen_product(uid, pid, note=""):
    p = get_product(pid)
    if not p:
        return screen_shop(uid)
    _, title, price = p
    n = stock_count(pid)
    bal = balance(uid)
    _photo, descr = product_extra(pid)
    sold = db.execute("SELECT COUNT(*) FROM stock WHERE product_id=? AND used_by IS NOT NULL",
                      (pid,)).fetchone()[0]
    text = f"{note}🛍 {title}\n{SEP}\n\n"
    line = rating_line(pid)
    if line:
        text += f"{line}\n"
    if sold:
        text += f"✅ Продано: {sold}\n"
    if line or sold:
        text += "\n"
    if descr:
        text += f"📝 {descr}\n\n"
    text += (f"💵 Цена: {price} {COIN}\n"
             f"{stock_icon(n)} В наличии: {n} шт.\n"
             f"💰 Ваш баланс: {bal} {COIN}")
    kb = []
    if n == 0:
        text += "\n\n❌ Сейчас нет в наличии."
        sub = db.execute("SELECT 1 FROM stock_notify WHERE user_id=? AND product_id=?",
                         (uid, pid)).fetchone()
        if sub:
            text += "\n🔔 Мы напишем вам, как только появится."
            kb.append([cb("🔕 Не уведомлять", f"unnotify:{pid}")])
        else:
            kb.append([cb("🔔 Сообщить, когда появится", f"notify:{pid}", "primary")])
    elif bal < price:
        text += f"\n\n⚠️ Не хватает {price - bal} {COIN}."
        kb.append([cb("💰 Пополнить баланс", "topup", "primary")])
    else:
        kb.append([cb(f"✅ Купить за {price} {COIN}", f"buy:{pid}:1", "success")])
        extra, need_topup = [], False
        for q in QTY_OPTIONS:
            if q <= 1 or q > n:
                continue
            t = calc_total(price, q)
            if t <= bal:
                d = bulk_percent(q)
                lbl = f"🛒 ×{q} — {t} {COIN}" + (f" (−{d}%)" if d else "")
                extra.append(cb(lbl, f"buy:{pid}:{q}", "primary"))
            else:
                need_topup = True
        for i in range(0, len(extra), 2):
            kb.append(extra[i:i + 2])
        if need_topup:
            kb.append([cb("💰 Пополнить баланс", "topup", "primary")])
    if n > 1 and BULK_DISCOUNTS:
        text += "\n\n🎁 Скидки при покупке нескольких:\n" + \
                "\n".join(f"   • от {a} шт. — −{b}%" for a, b in BULK_DISCOUNTS)
    kb.append(back_row("⬅️ Аккаунты", "shop"))
    return text, markup(*kb)


def show_product(uid, mid, pid, note=""):
    """Агар товар акс дошта бошад — акс бо тавсиф нишон медиҳад."""
    text, kb = screen_product(uid, pid, note)
    photo = product_extra(pid)[0]
    if photo and get_product(pid):
        if send_photo(uid, photo, text, kb):
            delete_msg(uid, mid)
            return
    show(uid, mid, (text, kb))


def notify_subscribers(pid):
    """Ба онҳое, ки «Сообщить, когда появится» зада буданд, паём мефиристад."""
    row = db.execute("SELECT title FROM products WHERE id=? AND active=1", (pid,)).fetchone()
    if not row or stock_count(pid) == 0:
        return 0
    users = [r[0] for r in db.execute("SELECT user_id FROM stock_notify WHERE product_id=?", (pid,))]
    db.execute("DELETE FROM stock_notify WHERE product_id=?", (pid,))
    db.commit()
    n = 0
    for u in users:
        if send(u, f"🔔 «{row[0]}» снова в наличии!\n\nУспейте купить 👇",
                markup([cb("🛍 Открыть", f"p:{pid}", "success")], back_row())):
            n += 1
        time.sleep(0.05)
    return n


def screen_confirm(uid, pid, qty=1, note=""):
    p = get_product(pid)
    if not p:
        return screen_shop(uid)
    _, title, price = p
    n = stock_count(pid)
    if qty < 1 or qty > n:
        return (f"{note}❌ Столько нет в наличии (осталось: {n}).",
                markup(back_row("⬅️ Товар", f"p:{pid}")))
    total = calc_total(price, qty)
    bal = balance(uid)
    d = bulk_percent(qty)
    text = f"{note}🧾 Подтверждение покупки\n{SEP}\n\n🛍 Товар: {title}\n🔢 Количество: {qty} шт.\n"
    if d:
        text += f"🎁 Скидка: {d}% (без скидки {price * qty} {COIN})\n"
    text += f"💵 Итого: {total} {COIN}\n"
    if bal < total:
        text += f"\n⚠️ Не хватает {total - bal} {COIN}."
        return text, markup([cb("💰 Пополнить баланс", "topup", "primary")],
                            back_row("⬅️ Товар", f"p:{pid}"))
    text += f"💰 Баланс после покупки: {bal - total} {COIN}"
    return text, markup([cb("✅ Подтвердить", f"buyok:{pid}:{qty}:{total}", "success"),
                         cb("✖️ Отмена", f"p:{pid}", "danger")])


def screen_topup(uid):
    text = (f"💰 Пополнение баланса\n\n"
            f"Текущий баланс: {balance(uid)} {COIN}\n"
            f"Курс: 1 ⭐ = {RATE} {COIN}\n\n"
            "Выбери сумму (в звёздах ⭐) или введи свою 👇")
    kb, row = [], []
    for n in TOPUP_PRESETS:
        row.append(cb(f"⭐ {n}", f"pay:{n}"))
        if len(row) == 3:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([cb("✏️ Другая сумма", "topup_custom")])
    if rub_enabled():
        kb.append([cb(f"🏦 {TBANK_NAME} (₽, СБП/карта)", "rub", "primary")])
    if dc_enabled():
        kb.append([cb(f"🏙 {DC_NAME} (сомони)", "dc", "primary")])
    if crypto_enabled():
        kb.append([cb(f"💎 Криптой ({CRYPTO_ASSET})", "ctopup", "primary")])
    kb.append(back_row())
    return text, markup(*kb)


def screen_buys(uid, page=0):
    total = db.execute("SELECT COUNT(*) FROM stock WHERE used_by=?", (uid,)).fetchone()[0]
    if total == 0:
        return ("📦 У вас пока нет покупок.", markup([cb("🛒 Аккаунты", "shop")], back_row()))
    pages = (total + PAGE - 1) // PAGE
    page = max(0, min(page, pages - 1))
    rows = db.execute(
        "SELECT p.title, s.data, s.used_at, s.price_paid FROM stock s "
        "LEFT JOIN products p ON p.id=s.product_id WHERE s.used_by=? "
        "ORDER BY s.used_at DESC, s.id DESC LIMIT ? OFFSET ?",
        (uid, PAGE, page * PAGE)).fetchall()
    lines = [f"📦 Ваши покупки ({total})   стр. {page + 1}/{pages}\n"]
    for i, (title, data, ts, paid) in enumerate(rows, page * PAGE + 1):
        lines.append(f"{i}. {title or 'Товар'} — {paid or 0} {COIN}\n{code(data)}\n🕒 {fmt_time(ts)}\n")
    nav = []
    if page > 0:
        nav.append(cb("‹ Назад", f"buys:{page - 1}"))
    if page < pages - 1:
        nav.append(cb("Вперёд ›", f"buys:{page + 1}"))
    return "\n".join(lines), markup(nav, back_row())


# ======================= Пардохт бо Stars =======================

def send_invoice(uid, stars):
    coins = stars * RATE
    try:
        api("sendInvoice", chat_id=uid,
            title=f"{coins} {COIN}",
            description=f"Пополнение баланса: {coins} {COIN} за {stars} ⭐",
            payload=f"topup:{uid}:{stars}",
            currency="XTR",
            prices=[{"label": f"{coins} {COIN}", "amount": stars}])
        return True
    except Exception as e:
        print("sendInvoice error:", e)
        send(uid, "😔 Не удалось создать счёт. Попробуйте позже.", markup(back_row()))
        return False


def handle_payment(msg):
    sp = msg["successful_payment"]
    uid = msg["from"]["id"]
    if sp.get("currency") != "XTR":
        return
    stars = sp["total_amount"]
    charge = sp["telegram_payment_charge_id"]
    coins = stars * RATE
    cur = db.execute("INSERT OR IGNORE INTO payments(user_id, stars, coins, charge_id, ts) "
                     "VALUES(?,?,?,?,?)", (uid, stars, coins, charge, int(time.time())))
    if cur.rowcount == 0:       # аллакай ҳисоб шудааст
        db.commit()
        return
    add_tx(uid, coins, "topup", charge)
    ref = referrer_of(uid)
    bonus = coins * REF_PERCENT // 100 if ref else 0
    if bonus > 0:
        add_tx(ref, bonus, "ref", str(uid))
        db.execute("UPDATE payments SET ref_user=?, ref_bonus=? WHERE charge_id=?",
                   (ref, bonus, charge))
    db.commit()
    if ref and REF_REQUIRE_TOPUP:
        check_milestones(ref)
    if bonus > 0:
        send(ref, f"🎉 Ваш друг пополнил баланс! Вам начислено +{bonus} {COIN}\n"
                  f"💰 Баланс: {balance(ref)} {COIN}", markup(back_row()))
    send(uid, f"✅ Баланс пополнен на {coins} {COIN}!\n💰 Теперь на балансе: {balance(uid)} {COIN}",
         markup([cb("🛒 Аккаунты", "shop")], back_row()))
    send(ADMIN_ID, f"💳 Пополнение: +{stars} ⭐ ({coins} {COIN})\nОт: {name_of(uid)}")


def handle_refund(admin_id, arg):
    if not arg.isdigit():
        send(admin_id, "Формат: /refund ID_платежа (ID смотри в «💳 Платежи»)")
        return
    p = db.execute("SELECT user_id, stars, coins, charge_id, refunded, ref_user, ref_bonus "
                   "FROM payments WHERE id=?",
                   (int(arg),)).fetchone()
    if not p:
        send(admin_id, "Платёж не найден.")
        return
    uid, stars, coins, charge, refunded, ref_user, ref_bonus = p
    if refunded:
        send(admin_id, "Этот платёж уже возвращён.")
        return
    if balance(uid) < coins:
        send(admin_id, f"Нельзя вернуть: у пользователя на балансе {balance(uid)} {COIN}, "
                       f"а нужно {coins} (часть уже потрачена).")
        return
    try:
        api("refundStarPayment", user_id=uid, telegram_payment_charge_id=charge)
    except Exception as e:
        send(admin_id, f"⚠️ Telegram не вернул платёж: {e}")
        return
    db.execute("UPDATE payments SET refunded=1 WHERE id=?", (int(arg),))
    add_tx(uid, -coins, "refund", charge)
    if ref_user and ref_bonus:
        take = min(ref_bonus, balance(ref_user))
        if take > 0:
            add_tx(ref_user, -take, "ref_revoke", charge)
    db.commit()
    send(admin_id, f"✅ Возврат выполнен: {stars} ⭐ → {name_of(uid)}")
    send(uid, f"↩️ Платёж возвращён: {stars} ⭐. С баланса списано {coins} {COIN}.")


# ======================= Харид =======================

def do_buy(uid, pid, qty=1, expected=None):
    """Баргардонад: ('ok', None) | ('nobal', need) | ('empty', available) | ('changed', total) | ('gone', None)."""
    p = get_product(pid)
    if not p:
        return "gone", None
    _, title, price = p
    if qty < 1 or qty > MAX_QTY:
        return "empty", 0
    total = calc_total(price, qty)
    if expected is not None and expected != total:
        return "changed", total
    if balance(uid) < total:
        return "nobal", total - balance(uid)
    rows = db.execute("SELECT id, data FROM stock WHERE product_id=? AND used_by IS NULL "
                      "ORDER BY id LIMIT ?", (pid, qty)).fetchall()
    if len(rows) < qty:
        return "empty", len(rows)
    now = int(time.time())
    base, rest = divmod(total, qty)
    for i, (sid, _d) in enumerate(rows):
        db.execute("UPDATE stock SET used_by=?, used_at=?, price_paid=? WHERE id=? AND used_by IS NULL",
                   (uid, now, base + (1 if i < rest else 0), sid))
    add_tx(uid, -total, "buy", f"{title} x{qty}")
    db.commit()

    head = (f"🎉 Покупка успешна!\n{SEP}\n🛍 {title}" + (f" × {qty}" if qty > 1 else "") +
            f"\n{SEP}\n\n")
    tail = (f"\n{SEP}\n💡 Нажмите на данные аккаунта, чтобы скопировать.\n"
            "Спасибо! ❤️\n📦 Все покупки всегда есть в разделе «Мои покупки».")
    items = [f"{i}. {code(d)}" if qty > 1 else code(d) for i, (_sid, d) in enumerate(rows, 1)]
    chunks, cur = [], head
    for it in items:
        if len(cur) + len(it) + 1 > 3700:
            chunks.append(cur)
            cur = ""
        cur += it + "\n"
    chunks.append(cur + tail)
    kb = markup([cb("📦 Мои покупки", "buys:0")], [cb("🛒 Аккаунты", "shop")], back_row())
    ok = None
    for i, c in enumerate(chunks):
        res = send(uid, c, kb if i == len(chunks) - 1 else None)
        if i == 0:
            ok = res
        if not ok:
            break
    if not ok:      # фиристода нашуд — харидро бекор мекунем
        for sid, _d in rows:
            db.execute("UPDATE stock SET used_by=NULL, used_at=NULL, price_paid=NULL WHERE id=?", (sid,))
        add_tx(uid, total, "buy_cancel", f"{title} x{qty}")
        db.commit()
        send(ADMIN_ID, f"⚠️ Не удалось отправить товар пользователю {name_of(uid)} "
                       "(возможно, бот заблокирован). Покупка отменена, деньги возвращены на баланс.")
        return "fail", None
    send(ADMIN_ID, f"🛍 Продажа: {title}" + (f" × {qty}" if qty > 1 else "") +
         f" за {total} {COIN}\nПокупатель: {name_of(uid)}")
    left = stock_count(pid)
    if left <= 2:
        send(ADMIN_ID, f"⚠️ В складе «{title}» осталось: {left}. Добавьте аккаунты в админ-панели.")
    try:
        send_rating_request(uid, pid)
    except Exception as e:
        print("rating request error:", e)
    return "ok", None


# ======================= Админ-панель =======================

def admin_back():
    return [cb("⬅️ Админ-панель", "admin")]


def screen_admin():
    q = lambda sql: db.execute(sql).fetchone()[0]
    in_stock = q("SELECT COUNT(*) FROM stock s JOIN products p ON p.id=s.product_id "
                 "WHERE s.used_by IS NULL AND p.active=1")
    crypto_sum = q("SELECT COALESCE(SUM(amount),0) FROM crypto_invoices WHERE status='paid'")
    rub_sum = q("SELECT COALESCE(SUM(amount),0) FROM rub_requests "
                "WHERE status='approved' AND COALESCE(method,'tbank')='tbank'")
    dc_sum = q("SELECT COALESCE(SUM(amount),0) FROM rub_requests "
               "WHERE status='approved' AND method='dc'")
    rub_wait = q("SELECT COUNT(*) FROM rub_requests WHERE status='pending'")
    cars_done = q("SELECT COUNT(*) FROM car_orders WHERE status='done'")
    cars_sum = q("SELECT COALESCE(SUM(price),0) FROM car_orders WHERE status='done'")
    cars_open = q("SELECT COUNT(*) FROM car_orders WHERE status IN ('paid','sent')")
    cars_wait = q("SELECT COUNT(*) FROM car_orders WHERE status='sent'")
    text = ("⚙️ Админ-панель\n\n"
            f"👥 Пользователей: {q('SELECT COUNT(*) FROM users')}\n"
            f"💰 Сумма балансов: {q('SELECT COALESCE(SUM(balance),0) FROM users')} {COIN}\n"
            f"⭐ Получено Stars: {q('SELECT COALESCE(SUM(stars),0) FROM payments WHERE refunded=0')}\n"
            f"🛍 Продаж: {q('SELECT COUNT(*) FROM stock WHERE used_by IS NOT NULL')} "
            f"на {q('SELECT COALESCE(SUM(price_paid),0) FROM stock WHERE used_by IS NOT NULL')} {COIN}\n"
            f"🤝 Рефералов: {q('SELECT COUNT(*) FROM users WHERE referrer IS NOT NULL')}\n"
            f"💎 Crypto получено: {crypto_sum:g} {CRYPTO_ASSET}\n"
            f"🏦 {TBANK_NAME} получено: {rub_sum} ₽\n"
            f"🏙 {DC_NAME} получено: {dc_sum} сомони\n"
            f"⏳ Заявок на проверке: {rub_wait}\n"
            f"🚗 Машин продано: {cars_done} на {cars_sum} {COIN} (в работе: {cars_open})\n"
            f"🎟 Активаций промокодов: {q('SELECT COUNT(*) FROM promo_uses')}\n"
            f"📦 В складе: {in_stock}")
    kb = markup(
        [cb("📦 Товары и склад", "a_prods")],
        [cb("👥 Пользователи", "a_users"), cb("💳 Платежи", "a_pay")],
        [cb("📤 Продажи", "a_sales"), cb("🔎 Пользователь", "a_user")],
        [cb("💰 Изменить баланс", "a_bal"), cb("✨ Премиум-эмодзи", "a_emoji")],
        [cb("🎟 Промокоды", "a_promos"), cb("📢 Рассылка", "a_bc")],
        [cb("🚗 Машины" + (f" ({cars_wait})" if cars_wait else ""), "a_cars"),
         cb("🏦 Заявки на оплату" + (f" ({rub_wait})" if rub_wait else ""), "a_rub")],
        back_row())
    return text, kb


def screen_apromos(note=""):
    rows = db.execute("SELECT code, bonus, max_uses, used, expires, active FROM promos "
                      "ORDER BY rowid DESC LIMIT 30").fetchall()
    kb = []
    for r in rows:
        code, bonus, mx, used, _exp, _act = r
        mark = "🟢" if promo_alive(r) else "🔴"
        kb.append([cb(f"{mark} {code} — +{bonus} {COIN} [{used}/{mx if mx else '∞'}]",
                      f"a_promo:{code}")])
    kb.append([cb("➕ Новый промокод", "a_newpromo")])
    kb.append(admin_back())
    text = note + ("🎟 Промокоды\n\nНажми на промокод, чтобы управлять им." if rows else
                   "🎟 Промокодов пока нет. Создай первый 👇")
    return text, markup(*kb)


def screen_apromo(code, note=""):
    r = db.execute("SELECT code, bonus, max_uses, used, expires, active FROM promos WHERE code=?",
                   (code,)).fetchone()
    if not r:
        return screen_apromos()
    _c, bonus, mx, used, exp, act = r
    status = "🟢 действует" if promo_alive(r) else "🔴 не действует"
    if not act:
        status += " (выключен)"
    elif exp and time.time() > exp:
        status += " (срок истёк)"
    elif mx and used >= mx:
        status += " (лимит исчерпан)"
    text = (f"{note}🎟 {code}\n\n"
            f"🎁 Бонус: +{bonus} {COIN}\n"
            f"👥 Использовано: {used}/{mx if mx else '∞'}\n"
            f"🕒 Срок до: {fmt_time(exp) if exp else 'без срока'}\n"
            f"Статус: {status}")
    kb = markup(
        [cb("🔴 Выключить" if act else "🟢 Включить", f"a_promoff:{code}")],
        [cb("🗑 Удалить", f"a_promodel:{code}", "danger")],
        [cb("⬅️ Промокоды", "a_promos")])
    return text, kb


def screen_aprods():
    rows = db.execute("SELECT id, title, price FROM products WHERE active=1 ORDER BY id").fetchall()
    kb = [[cb(f"{t} — {pr} {COIN} [{stock_count(i)}]", f"a_p:{i}")] for i, t, pr in rows]
    kb.append([cb("➕ Новый товар", "a_newprod")])
    kb.append(admin_back())
    text = "📦 Товары и склад\n\nНажми на товар, чтобы управлять им." if rows else \
           "📦 Товаров пока нет. Создай первый 👇"
    return text, markup(*kb)


def screen_aprod(pid, note=""):
    p = get_product(pid)
    if not p:
        return screen_aprods()
    _, title, price = p
    sold = db.execute("SELECT COUNT(*) FROM stock WHERE product_id=? AND used_by IS NOT NULL",
                      (pid,)).fetchone()[0]
    photo, descr = product_extra(pid)
    short = (descr[:80] + "…") if len(descr) > 80 else (descr or "нет")
    text = (f"{note}🛍 {title}\n\n💵 Цена: {price} {COIN}\n"
            f"📦 В складе: {stock_count(pid)}\n✅ Продано: {sold}\n"
            f"🖼 Фото: {'есть ✅' if photo else 'нет'}\n📝 Описание: {short}")
    line = rating_line(pid)
    if line:
        text += "\n" + line
    kb = markup(
        [cb("➕ Добавить аккаунты", f"a_add:{pid}")],
        [cb("🖼 Фото", f"a_photo:{pid}"), cb("📝 Описание", f"a_desc:{pid}")],
        [cb("🗑 Убрать фото", f"a_nophoto:{pid}")] if photo else [],
        [cb("👁 Как видит покупатель", f"a_view:{pid}")],
        [cb("✏️ Изменить цену", f"a_price:{pid}"), cb("✏️ Название", f"a_title:{pid}")],
        [cb("🗑 Удалить 1", f"a_del:{pid}:1"), cb("🗑 Удалить 5", f"a_del:{pid}:5"),
         cb("🗑 Удалить 10", f"a_del:{pid}:10")],
        [cb("🧹 Очистить склад", f"a_clr:{pid}"), cb("❌ Удалить товар", f"a_rm:{pid}", "danger")],
        [cb("⬅️ Товары", "a_prods")])
    return text, kb


def ask_admin(uid, mid, state, text):
    ADMIN_STATE[uid] = state
    edit(uid, mid, text + "\n\n/cancel — отмена", markup([cb("✖️ Отмена", "admin")]))


def send_chunks(chat_id, head, lines):
    chunk = head
    for line in lines:
        if len(chunk) + len(line) > 3800:
            send(chat_id, chunk)
            chunk = ""
        chunk += line + "\n"
    if chunk.strip():
        send(chat_id, chunk, markup(admin_back()))


def show_users(uid):
    rows = db.execute("SELECT user_id, balance FROM users ORDER BY balance DESC, joined DESC "
                      "LIMIT 40").fetchall()
    total = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    send_chunks(uid, f"👥 Пользователей: {total} (топ по балансу)\n\n",
                [f"{i}. {name_of(u)} — {b} {COIN}" for i, (u, b) in enumerate(rows, 1)] or ["Пока никого."])


def show_payments(uid):
    rows = db.execute("SELECT id, user_id, stars, ts, refunded FROM payments "
                      "ORDER BY id DESC LIMIT 20").fetchall()
    lines = [f"#{i} {fmt_time(ts)} — {name_of(u)} — {s} ⭐" + (" ↩️ возвращён" if r else "")
             for i, u, s, ts, r in rows]
    crows = db.execute("SELECT user_id, amount, coins, paid_at FROM crypto_invoices "
                       "WHERE status='paid' ORDER BY paid_at DESC LIMIT 10").fetchall()
    if crows:
        lines.append("\n💎 Crypto (возврат вручную):")
        lines += [f"{fmt_time(t)} — {name_of(u)} — {a:g} {CRYPTO_ASSET} → {c} {COIN}"
                  for u, a, c, t in crows]
    rrows = db.execute("SELECT id, user_id, amount, done_at, method FROM rub_requests "
                       "WHERE status='approved' ORDER BY done_at DESC LIMIT 10").fetchall()
    if rrows:
        lines.append("\n🏦 Ручные оплаты (подтверждено):")
        lines += [f"#{i} {fmt_time(t)} — {name_of(u)} — {a} {method_cfg(m or 'tbank')['unit']}"
                  f" ({method_cfg(m or 'tbank')['name']})" for i, u, a, t, m in rrows]
    send_chunks(uid, "💳 Последние платежи\nВозврат Stars: /refund ID\n\n",
                lines or ["Платежей пока нет."])


def show_sales(uid):
    rows = db.execute(
        "SELECT p.title, s.price_paid, s.used_by, s.used_at FROM stock s "
        "LEFT JOIN products p ON p.id=s.product_id WHERE s.used_by IS NOT NULL "
        "ORDER BY s.used_at DESC, s.id DESC LIMIT 30").fetchall()
    send_chunks(uid, "📤 Последние продажи\n\n",
                [f"{fmt_time(ts)} — {t or 'Товар'} — {pr or 0} {COIN} → {name_of(u)}"
                 for t, pr, u, ts in rows] or ["Продаж пока нет."])


def find_user(arg):
    arg = arg.lstrip("@")
    if arg.isdigit():
        return int(arg)
    r = db.execute("SELECT user_id FROM users WHERE LOWER(username)=LOWER(?)", (arg,)).fetchone()
    return r[0] if r else None


def show_user(admin_id, arg):
    uid = find_user(arg)
    if uid is None:
        send(admin_id, "Пользователь не найден.")
        return
    topup = db.execute("SELECT COALESCE(SUM(stars),0) FROM payments WHERE user_id=? AND refunded=0",
                       (uid,)).fetchone()[0]
    buys = db.execute("SELECT COUNT(*), COALESCE(SUM(price_paid),0) FROM stock WHERE used_by=?",
                      (uid,)).fetchone()
    lines = [f"🔎 {name_of(uid)}\n", f"💰 Баланс: {balance(uid)} {COIN}",
             f"⭐ Пополнено всего: {topup}", f"🛍 Покупок: {buys[0]} на {buys[1]} {COIN}\n"]
    for t, d, ts in db.execute(
            "SELECT p.title, s.data, s.used_at FROM stock s LEFT JOIN products p ON p.id=s.product_id "
            "WHERE s.used_by=? ORDER BY s.used_at DESC LIMIT 5", (uid,)):
        lines.append(f"• {fmt_time(ts)} — {t or 'Товар'}: {d}")
    send(admin_id, "\n".join(lines), markup(admin_back()))


def handle_admin_cb(uid, mid, data):
    global BCAST_RUNNING
    if data == "admin":
        ADMIN_STATE.pop(uid, None)
        BCAST.pop(uid, None)
        show(uid, mid, screen_admin())
    elif data == "a_rub":
        show(uid, mid, screen_arub())
    elif data == "a_cars":
        ADMIN_STATE.pop(uid, None)
        show(uid, mid, screen_acars())
    elif data == "a_corders":
        show(uid, mid, screen_acorders())
    elif data == "a_newcar":
        ask_admin(uid, mid, ("newcar",),
                  "➕ Новая машина. Отправь одним сообщением:\nНазвание | цена\n\n"
                  "Например:\nBMW M5 | 100")
    elif data.startswith("a_car:"):
        show(uid, mid, screen_acar(int(data.split(":")[1])))
    elif data.startswith("a_carphoto:"):
        ask_admin(uid, mid, ("car_photo", int(data.split(":")[1])),
                  "🖼 Отправь фото машины.\nЕсли напишешь подпись к фото, она станет описанием.")
    elif data.startswith("a_carnophoto:"):
        cid = int(data.split(":")[1])
        db.execute("UPDATE cars SET photo=NULL WHERE id=?", (cid,))
        db.commit()
        show(uid, mid, screen_acar(cid, "🗑 Фото убрано.\n\n"))
    elif data.startswith("a_cardesc:"):
        ask_admin(uid, mid, ("car_desc", int(data.split(":")[1])),
                  "📝 Отправь описание машины (до 700 символов).\nЧтобы убрать, отправь «-»")
    elif data.startswith("a_carprice:"):
        ask_admin(uid, mid, ("car_price", int(data.split(":")[1])),
                  f"✏️ Отправь новую цену числом (в {COIN}).")
    elif data.startswith("a_cartitle:"):
        ask_admin(uid, mid, ("car_title", int(data.split(":")[1])), "✏️ Отправь новое название машины.")
    elif data.startswith("a_carview:"):
        show_car(uid, None, int(data.split(":")[1]))
    elif data.startswith("a_carrmy:"):
        cid = int(data.split(":")[1])
        db.execute("UPDATE cars SET active=0 WHERE id=?", (cid,))
        db.commit()
        show(uid, mid, screen_acars())
    elif data.startswith("a_carrm:"):
        cid = int(data.split(":")[1])
        edit(uid, mid, "Удалить машину? Она пропадёт из магазина (история заказов сохранится).",
             markup([cb("❌ Да, удалить", f"a_carrmy:{cid}", "danger"), cb("✖️ Отмена", f"a_car:{cid}")]))
    elif data == "a_promos":
        ADMIN_STATE.pop(uid, None)
        show(uid, mid, screen_apromos())
    elif data == "a_newpromo":
        ask_admin(uid, mid, ("newpromo",),
                  "🎟 Новый промокод. Отправь одним сообщением:\n"
                  "КОД | бонус | лимит | дней\n\n"
                  "• КОД — латиница/цифры, 3–20 символов\n"
                  f"• бонус — сколько {COIN} получит пользователь\n"
                  "• лимит — сколько раз можно использовать (0 = без лимита)\n"
                  "• дней — срок действия (необязательно)\n\n"
                  "Примеры:\nSSM20 | 20 | 50\nNEWYEAR | 10 | 100 | 7")
    elif data.startswith("a_promoff:"):
        code = data.split(":", 1)[1]
        db.execute("UPDATE promos SET active=1-active WHERE code=?", (code,))
        db.commit()
        show(uid, mid, screen_apromo(code, "✅ Статус изменён.\n\n"))
    elif data.startswith("a_promodel:"):
        code = data.split(":", 1)[1]
        edit(uid, mid, f"Удалить промокод {code}?",
             markup([cb("🗑 Да, удалить", f"a_promodely:{code}", "danger"),
                     cb("✖️ Отмена", f"a_promo:{code}")]))
    elif data.startswith("a_promodely:"):
        code = data.split(":", 1)[1]
        db.execute("DELETE FROM promos WHERE code=?", (code,))
        db.execute("DELETE FROM promo_uses WHERE code=?", (code,))
        db.commit()
        show(uid, mid, screen_apromos("🗑 Промокод удалён.\n\n"))
    elif data.startswith("a_promo:"):
        show(uid, mid, screen_apromo(data.split(":", 1)[1]))
    elif data == "a_bc":
        ask_admin(uid, mid, ("bcast",),
                  "📢 Рассылка\n\nОтправь сообщение, которое получат все пользователи "
                  "(текст, фото или видео с подписью). Сначала я покажу предпросмотр.")
    elif data == "a_bcgo":
        msg_ref = BCAST.pop(uid, None)
        if not msg_ref:
            edit(uid, mid, "Нет сообщения для рассылки.", markup(admin_back()))
        elif BCAST_RUNNING:
            BCAST[uid] = msg_ref
            edit(uid, mid, "⏳ Предыдущая рассылка ещё идёт. Подожди её окончания.", markup(admin_back()))
        else:
            BCAST_RUNNING = True
            threading.Thread(target=run_broadcast, args=(uid, msg_ref[0], msg_ref[1]),
                             daemon=True).start()
            edit(uid, mid, "📤 Рассылка запущена. Я напишу, когда закончу.", markup(admin_back()))
    elif data == "a_prods":
        show(uid, mid, screen_aprods())
    elif data == "a_newprod":
        ask_admin(uid, mid, ("newprod",),
                  "➕ Новый товар. Отправь одним сообщением:\nНазвание | цена\n\n"
                  "Например:\nФулл аккаунт CPM | 100")
    elif data.startswith("a_p:"):
        show(uid, mid, screen_aprod(int(data.split(":")[1])))
    elif data.startswith("a_photo:"):
        ask_admin(uid, mid, ("photo", int(data.split(":")[1])),
                  "🖼 Отправь фото (скриншот) аккаунта.\n"
                  "Если напишешь подпись к фото — она станет описанием.")
    elif data.startswith("a_nophoto:"):
        pid = int(data.split(":")[1])
        db.execute("UPDATE products SET photo=NULL WHERE id=?", (pid,))
        db.commit()
        show(uid, mid, screen_aprod(pid, "🗑 Фото убрано.\n\n"))
    elif data.startswith("a_desc:"):
        ask_admin(uid, mid, ("desc", int(data.split(":")[1])),
                  "📝 Отправь описание аккаунта (до 700 символов): уровень, машины, деньги и т.д.\n"
                  "Чтобы убрать описание, отправь «-»")
    elif data.startswith("a_view:"):
        show_product(uid, None, int(data.split(":")[1]))
    elif data.startswith("a_add:"):
        ask_admin(uid, mid, ("addacc", int(data.split(":")[1])),
                  "➕ Отправь аккаунты одним сообщением. Каждая строка = 1 аккаунт, например:\n"
                  "логин1:пароль1\nлогин2:пароль2")
    elif data.startswith("a_price:"):
        ask_admin(uid, mid, ("price", int(data.split(":")[1])),
                  f"✏️ Отправь новую цену числом (в {COIN}).")
    elif data.startswith("a_title:"):
        ask_admin(uid, mid, ("title", int(data.split(":")[1])), "✏️ Отправь новое название товара.")
    elif data.startswith("a_del:"):
        _, pid, n = data.split(":")
        db.execute("DELETE FROM stock WHERE id IN (SELECT id FROM stock WHERE product_id=? "
                   "AND used_by IS NULL ORDER BY id DESC LIMIT ?)", (int(pid), int(n)))
        db.commit()
        show(uid, mid, screen_aprod(int(pid), f"🗑 Удалено (до {n} шт.)\n\n"))
    elif data.startswith("a_clr:"):
        pid = int(data.split(":")[1])
        edit(uid, mid, f"Удалить все {stock_count(pid)} аккаунтов этого товара из склада?",
             markup([cb("🧹 Да, очистить", f"a_clry:{pid}", "danger"), cb("✖️ Отмена", f"a_p:{pid}")]))
    elif data.startswith("a_clry:"):
        pid = int(data.split(":")[1])
        db.execute("DELETE FROM stock WHERE product_id=? AND used_by IS NULL", (pid,))
        db.commit()
        show(uid, mid, screen_aprod(pid, "🧹 Склад очищен.\n\n"))
    elif data.startswith("a_rm:"):
        pid = int(data.split(":")[1])
        edit(uid, mid, "Удалить товар? Он пропадёт из магазина (история продаж сохранится).",
             markup([cb("❌ Да, удалить", f"a_rmy:{pid}", "danger"), cb("✖️ Отмена", f"a_p:{pid}")]))
    elif data.startswith("a_rmy:"):
        pid = int(data.split(":")[1])
        db.execute("UPDATE products SET active=0 WHERE id=?", (pid,))
        db.execute("DELETE FROM stock WHERE product_id=? AND used_by IS NULL", (pid,))
        db.commit()
        show(uid, mid, screen_aprods())
    elif data == "a_users":
        show_users(uid)
    elif data == "a_pay":
        show_payments(uid)
    elif data == "a_sales":
        show_sales(uid)
    elif data == "a_emoji":
        handle_emoji_cmd({"from": {"id": uid}, "text": "/emoji"})
    elif data == "a_user":
        ask_admin(uid, mid, ("user",), "🔎 Отправь ID или @username пользователя.")
    elif data == "a_bal":
        ask_admin(uid, mid, ("bal",),
                  "💰 Изменить баланс. Отправь:\nID сумма\n\nНапример:\n123456789 +50\n123456789 -20")


def run_broadcast(admin_id, src_chat, src_mid):
    """Дар риштаи алоҳида кор мекунад, то бот ва пардохтҳо банд нашаванд."""
    global BCAST_RUNNING
    ok = fail = blocked = 0
    try:
        con = sqlite3.connect(DB_PATH, timeout=30)
        ids = [r[0] for r in con.execute(
            "SELECT user_id FROM users WHERE COALESCE(blocked,0)=0 AND user_id!=?", (admin_id,))]
        for u in ids:
            for attempt in range(2):
                try:
                    api("copyMessage", chat_id=u, from_chat_id=src_chat, message_id=src_mid)
                    ok += 1
                    break
                except Exception as e:
                    err = str(e)
                    m = re.search(r'retry_after"?:\s*(\d+)', err)
                    if m and attempt == 0:
                        time.sleep(int(m.group(1)) + 1)
                        continue
                    fail += 1
                    if any(k in err for k in ("blocked", "deactivated", "chat not found", "kicked")):
                        blocked += 1
                        con.execute("UPDATE users SET blocked=1 WHERE user_id=?", (u,))
                        con.commit()
                    break
            time.sleep(0.05)
        con.close()
        send(admin_id, f"✅ Рассылка завершена\n\n📨 Доставлено: {ok}\n"
                       f"🚫 Не доставлено: {fail} (заблокировали бота: {blocked})",
             markup(admin_back()))
    except Exception as e:
        print("broadcast error:", e)
        send(admin_id, f"⚠️ Ошибка рассылки: {e}")
    finally:
        BCAST_RUNNING = False


def handle_admin_state(uid, text):
    state = ADMIN_STATE.pop(uid, None)
    if not state:
        return
    kind = state[0]
    if kind == "cardone":
        finish_car_order(uid, state[1], text)
    elif kind == "newcar":
        if "|" not in text:
            ADMIN_STATE[uid] = state
            send(uid, "Формат: Название | цена\nНапример: BMW M5 | 100")
            return
        title, _, price = text.rpartition("|")
        title, price = title.strip(), price.strip()
        if not title or not price.isdigit() or int(price) <= 0:
            ADMIN_STATE[uid] = state
            send(uid, "Цена должна быть положительным числом. Попробуй ещё раз.")
            return
        cur = db.execute("INSERT INTO cars(title, price) VALUES(?,?)", (title[:60], int(price)))
        db.commit()
        cid = cur.lastrowid
        send(uid, f"✅ Кнопка создана: {title} — {price} {COIN}\nМожно добавить фото и описание 👇",
             markup([cb("🖼 Фото", f"a_carphoto:{cid}"), cb("📝 Описание", f"a_cardesc:{cid}")],
                    [cb("⚙️ Управлять", f"a_car:{cid}")], [cb("↩️ В раздел «Машины»", "cars")]))
    elif kind == "car_price":
        if not text.strip().isdigit() or int(text) <= 0:
            ADMIN_STATE[uid] = state
            send(uid, "Нужно положительное число. Попробуй ещё раз.")
            return
        db.execute("UPDATE cars SET price=? WHERE id=?", (int(text), state[1]))
        db.commit()
        send(uid, f"✅ Цена обновлена: {int(text)} {COIN}", markup([cb("🚗 К машине", f"a_car:{state[1]}")]))
    elif kind == "car_title":
        db.execute("UPDATE cars SET title=? WHERE id=?", (text.strip()[:60], state[1]))
        db.commit()
        send(uid, "✅ Название обновлено.", markup([cb("🚗 К машине", f"a_car:{state[1]}")]))
    elif kind == "car_desc":
        d = text.strip()
        db.execute("UPDATE cars SET descr=? WHERE id=?", (None if d == "-" else d[:700], state[1]))
        db.commit()
        send(uid, "🗑 Описание убрано." if d == "-" else "✅ Описание сохранено.",
             markup([cb("👁 Как видит покупатель", f"a_carview:{state[1]}")],
                    [cb("🚗 К машине", f"a_car:{state[1]}")]))
    elif kind == "car_photo":
        ADMIN_STATE[uid] = state
        send(uid, "Нужно отправить именно фото (не текст). Или /cancel.")
    elif kind == "newpromo":
        parts = [p.strip() for p in text.split("|")]
        code = parts[0].upper() if parts else ""
        try:
            bonus = int(parts[1])
            limit = int(parts[2]) if len(parts) > 2 and parts[2] else 0
            days = int(parts[3]) if len(parts) > 3 and parts[3] else 0
        except (ValueError, IndexError):
            ADMIN_STATE[uid] = state
            send(uid, "Формат: КОД | бонус | лимит | дней\nНапример: SSM20 | 20 | 50")
            return
        if not PROMO_RE.match(code):
            ADMIN_STATE[uid] = state
            send(uid, "Код: только латиница, цифры и _, от 3 до 20 символов. Попробуй ещё раз.")
            return
        if bonus <= 0 or limit < 0 or days < 0:
            ADMIN_STATE[uid] = state
            send(uid, "Бонус должен быть больше 0, лимит и дни — не меньше 0. Попробуй ещё раз.")
            return
        if db.execute("SELECT 1 FROM promos WHERE code=?", (code,)).fetchone():
            ADMIN_STATE[uid] = state
            send(uid, "Такой промокод уже есть. Придумай другой код.")
            return
        now = int(time.time())
        exp = now + days * 86400 if days else None
        db.execute("INSERT INTO promos(code, bonus, max_uses, used, expires, active, created) "
                   "VALUES(?,?,?,0,?,1,?)", (code, bonus, limit, exp, now))
        db.commit()
        send(uid, f"✅ Промокод создан: {code}\n"
                  f"🎁 Бонус: +{bonus} {COIN}\n"
                  f"👥 Лимит: {limit if limit else 'без лимита'}\n"
                  f"🕒 Срок: {fmt_time(exp) if exp else 'без срока'}",
             markup([cb("🎟 Промокоды", "a_promos")], admin_back()))
    elif kind == "newprod":
        if "|" not in text:
            ADMIN_STATE[uid] = state
            send(uid, "Формат: Название | цена\nНапример: Фулл аккаунт CPM | 100")
            return
        title, _, price = text.rpartition("|")
        title, price = title.strip(), price.strip()
        if not title or not price.isdigit() or int(price) <= 0:
            ADMIN_STATE[uid] = state
            send(uid, "Цена должна быть положительным числом. Попробуй ещё раз.")
            return
        cur = db.execute("INSERT INTO products(title, price) VALUES(?,?)", (title, int(price)))
        db.commit()
        pid = cur.lastrowid
        send(uid, f"✅ Товар создан: {title} — {price} {COIN}\nТеперь добавь аккаунты 👇",
             markup([cb("➕ Добавить аккаунты", f"a_add:{pid}")], [cb("⬅️ Товары", "a_prods")]))
    elif kind == "addacc":
        pid = state[1]
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for l in lines:
            db.execute("INSERT INTO stock(product_id, data) VALUES(?,?)", (pid, l))
        db.commit()
        notified = notify_subscribers(pid)
        send(uid, f"✅ Добавлено: {len(lines)}\n📦 Всего в складе: {stock_count(pid)}" +
             (f"\n🔔 Уведомлено покупателей: {notified}" if notified else ""),
             markup([cb("🛍 К товару", f"a_p:{pid}")], admin_back()))
    elif kind == "price":
        if not text.strip().isdigit() or int(text) <= 0:
            ADMIN_STATE[uid] = state
            send(uid, "Нужно положительное число. Попробуй ещё раз.")
            return
        db.execute("UPDATE products SET price=? WHERE id=?", (int(text), state[1]))
        db.commit()
        send(uid, f"✅ Цена обновлена: {int(text)} {COIN}", markup([cb("🛍 К товару", f"a_p:{state[1]}")]))
    elif kind == "title":
        db.execute("UPDATE products SET title=? WHERE id=?", (text.strip()[:60], state[1]))
        db.commit()
        send(uid, "✅ Название обновлено.", markup([cb("🛍 К товару", f"a_p:{state[1]}")]))
    elif kind == "desc":
        d = text.strip()
        db.execute("UPDATE products SET descr=? WHERE id=?",
                   (None if d == "-" else d[:700], state[1]))
        db.commit()
        send(uid, "🗑 Описание убрано." if d == "-" else "✅ Описание сохранено.",
             markup([cb("👁 Как видит покупатель", f"a_view:{state[1]}")],
                    [cb("🛍 К товару", f"a_p:{state[1]}")]))
    elif kind == "photo":
        ADMIN_STATE[uid] = state
        send(uid, "Нужно отправить именно фото (не текст). Или /cancel.")
    elif kind == "user":
        parts = text.strip().split()
        if parts:
            show_user(uid, parts[0])
    elif kind == "bal":
        parts = text.split()
        try:
            target, delta = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            ADMIN_STATE[uid] = state
            send(uid, "Формат: ID сумма, например: 123456789 +50")
            return
        r = db.execute("SELECT 1 FROM users WHERE user_id=?", (target,)).fetchone()
        if not r:
            send(uid, "Такого пользователя нет в базе (он должен хотя бы раз нажать /start).")
            return
        add_tx(target, delta, "admin", "ручное изменение")
        db.commit()
        send(uid, f"✅ Баланс {name_of(target)}: {balance(target)} {COIN}", markup(admin_back()))
        send(target, f"💰 Баланс изменён админом: {delta:+d} {COIN}\nТеперь: {balance(target)} {COIN}")


# ======================= Премиум-эмодзи (команда) =======================

def u16_slice(text, off, ln):
    return text.encode("utf-16-le")[off * 2:(off + ln) * 2].decode("utf-16-le", "ignore")


def handle_emoji_cmd(msg):
    uid = msg["from"]["id"]
    text = msg.get("text", "")
    ents = [e for e in msg.get("entities", []) if e.get("type") == "custom_emoji"]
    if text.strip() == "/emoji clear":
        db.execute("DELETE FROM emoji_map")
        db.commit()
        load_emoji()
        send(uid, "🗑 Премиум-эмодзи сброшены, всё снова с обычными эмодзи.")
        return
    if not ents:
        done = [e for e in BUTTON_EMOJIS if norm_emoji(e) in EMOJI_MAP]
        todo = [e for e in BUTTON_EMOJIS if norm_emoji(e) not in EMOJI_MAP]
        send(uid,
             "✨ Премиум-эмодзи (в кнопках и в тексте)\n\n"
             "Отправь /emoji и премиум-эмодзи (из любого набора). Формат:\n"
             "/emoji\n🛒 = (премиум)\n💰 = (премиум)\n\n"
             "Слева — обычный эмодзи, справа — премиум, который его заменит. "
             "Если у премиум-эмодзи тот же базовый смайл, можно отправить его без «=».\n\n"
             f"Ещё не настроены: {' '.join(todo) or '—'}\n"
             f"Уже настроены: {' '.join(done) or '—'}\n\n"
             "/emoji clear — сбросить всё.\n"
             "⚠️ Работает, если у владельца бота есть Telegram Premium. "
             "Если Telegram откажет, бот сам покажет обычные эмодзи.")
        return
    saved = []
    prev_end = 0
    for e in sorted(ents, key=lambda x: x["offset"]):
        fallback = u16_slice(text, e["offset"], e["length"])
        pre = u16_slice(text, prev_end, e["offset"] - prev_end)
        pre = pre.replace("/emoji", "").replace("=", "").strip()
        key = pre if pre else fallback
        prev_end = e["offset"] + e["length"]
        db.execute("INSERT OR REPLACE INTO emoji_map VALUES(?,?)",
                   (norm_emoji(key), e["custom_emoji_id"]))
        saved.append(key)
    db.commit()
    load_emoji()
    send(uid, f"✅ Сохранено: {' '.join(saved)}\nОткрой /menu и посмотри.")


# ======================= Обработчики =======================

def handle_message(msg):
    if msg["chat"]["type"] != "private":
        return
    user = msg["from"]
    uid = user["id"]
    is_new = ensure_user(user)

    if msg.get("successful_payment"):
        handle_payment(msg)
        return

    text = msg.get("te
# ======================= Пардохт бо Stars =======================

def send_invoice(uid, stars):
    coins = stars * RATE
    try:
        api("sendInvoice", chat_id=uid,
            title=f"{coins} {COIN}",
            description=f"Пополнение баланса: {coins} {COIN} за {stars} ⭐",
            payload=f"topup:{uid}:{stars}",
            currency="XTR",
            prices=[{"label": f"{coins} {COIN}", "amount": stars}])
        return True
    except Exception as e:
        print("sendInvoice error:", e)
        send(uid, "😔 Не удалось создать счёт. Попробуйте позже.", markup(back_row()))
        return False


def handle_payment(msg):
    sp = msg["successful_payment"]
    uid = msg["from"]["id"]
    if sp.get("currency") != "XTR":
        return
    stars = sp["total_amount"]
    charge = sp["telegram_payment_charge_id"]
    coins = stars * RATE
    cur = db.execute("INSERT OR IGNORE INTO payments(user_id, stars, coins, charge_id, ts) "
                     "VALUES(?,?,?,?,?)", (uid, stars, coins, charge, int(time.time())))
    if cur.rowcount == 0:       # аллакай ҳисоб шудааст
        db.commit()
        return
    add_tx(uid, coins, "topup", charge)
    ref = referrer_of(uid)
    bonus = coins * REF_PERCENT // 100 if ref else 0
    if bonus > 0:
        add_tx(ref, bonus, "ref", str(uid))
        db.execute("UPDATE payments SET ref_user=?, ref_bonus=? WHERE charge_id=?",
                   (ref, bonus, charge))
    db.commit()
    if ref and REF_REQUIRE_TOPUP:
        check_milestones(ref)
    if bonus > 0:
        send(ref, f"🎉 Ваш друг пополнил баланс! Вам начислено +{bonus} {COIN}\n"
                  f"💰 Баланс: {balance(ref)} {COIN}", markup(back_row()))
    send(uid, f"✅ Баланс пополнен на {coins} {COIN}!\n💰 Теперь на балансе: {balance(uid)} {COIN}",
         markup([cb("🛒 Аккаунты", "shop")], back_row()))
    send(ADMIN_ID, f"💳 Пополнение: +{stars} ⭐ ({coins} {COIN})\nОт: {name_of(uid)}")


def handle_refund(admin_id, arg):
    if not arg.isdigit():
        send(admin_id, "Формат: /refund ID_платежа (ID смотри в «💳 Платежи»)")
        return
    p = db.execute("SELECT user_id, stars, coins, charge_id, refunded, ref_user, ref_bonus "
                   "FROM payments WHERE id=?",
                   (int(arg),)).fetchone()
    if not p:
        send(admin_id, "Платёж не найден.")
        return
    uid, stars, coins, charge, refunded, ref_user, ref_bonus = p
    if refunded:
        send(admin_id, "Этот платёж уже возвращён.")
        return
    if balance(uid) < coins:
        send(admin_id, f"Нельзя вернуть: у пользователя на балансе {balance(uid)} {COIN}, "
                       f"а нужно {coins} (часть уже потрачена).")
        return
    try:
        api("refundStarPayment", user_id=uid, telegram_payment_charge_id=charge)
    except Exception as e:
        send(admin_id, f"⚠️ Telegram не вернул платёж: {e}")
        return
    db.execute("UPDATE payments SET refunded=1 WHERE id=?", (int(arg),))
    add_tx(uid, -coins, "refund", charge)
    if ref_user and ref_bonus:
        take = min(ref_bonus, balance(ref_user))
        if take > 0:
            add_tx(ref_user, -take, "ref_revoke", charge)
    db.commit()
    send(admin_id, f"✅ Возврат выполнен: {stars} ⭐ → {name_of(uid)}")
    send(uid, f"↩️ Платёж возвращён: {stars} ⭐. С баланса списано {coins} {COIN}.")


# ======================= Харид =======================

def do_buy(uid, pid, qty=1, expected=None):
    """Баргардонад: ('ok', None) | ('nobal', need) | ('empty', available) | ('changed', total) | ('gone', None)."""
    p = get_product(pid)
    if not p:
        return "gone", None
    _, title, price = p
    if qty < 1 or qty > MAX_QTY:
        return "empty", 0
    total = calc_total(price, qty)
    if expected is not None and expected != total:
        return "changed", total
    if balance(uid) < total:
        return "nobal", total - balance(uid)
    rows = db.execute("SELECT id, data FROM stock WHERE product_id=? AND used_by IS NULL "
                      "ORDER BY id LIMIT ?", (pid, qty)).fetchall()
    if len(rows) < qty:
        return "empty", len(rows)
    now = int(time.time())
    base, rest = divmod(total, qty)
    for i, (sid, _d) in enumerate(rows):
        db.execute("UPDATE stock SET used_by=?, used_at=?, price_paid=? WHERE id=? AND used_by IS NULL",
                   (uid, now, base + (1 if i < rest else 0), sid))
    add_tx(uid, -total, "buy", f"{title} x{qty}")
    db.commit()

    head = (f"🎉 Покупка успешна!\n{SEP}\n🛍 {title}" + (f" × {qty}" if qty > 1 else "") +
            f"\n{SEP}\n\n")
    tail = (f"\n{SEP}\n💡 Нажмите на данные аккаунта, чтобы скопировать.\n"
            "Спасибо! ❤️\n📦 Все покупки всегда есть в разделе «Мои покупки».")
    items = [f"{i}. {code(d)}" if qty > 1 else code(d) for i, (_sid, d) in enumerate(rows, 1)]
    chunks, cur = [], head
    for it in items:
        if len(cur) + len(it) + 1 > 3700:
            chunks.append(cur)
            cur = ""
        cur += it + "\n"
    chunks.append(cur + tail)
    kb = markup([cb("📦 Мои покупки", "buys:0")], [cb("🛒 Аккаунты", "shop")], back_row())
    ok = None
    for i, c in enumerate(chunks):
        res = send(uid, c, kb if i == len(chunks) - 1 else None)
        if i == 0:
            ok = res
        if not ok:
            break
    if not ok:      # фиристода нашуд — харидро бекор мекунем
        for sid, _d in rows:
            db.execute("UPDATE stock SET used_by=NULL, used_at=NULL, price_paid=NULL WHERE id=?", (sid,))
        add_tx(uid, total, "buy_cancel", f"{title} x{qty}")
        db.commit()
        send(ADMIN_ID, f"⚠️ Не удалось отправить товар пользователю {name_of(uid)} "
                       "(возможно, бот заблокирован). Покупка отменена, деньги возвращены на баланс.")
        return "fail", None
    send(ADMIN_ID, f"🛍 Продажа: {title}" + (f" × {qty}" if qty > 1 else "") +
         f" за {total} {COIN}\nПокупатель: {name_of(uid)}")
    left = stock_count(pid)
    if left <= 2:
        send(ADMIN_ID, f"⚠️ В складе «{title}» осталось: {left}. Добавьте аккаунты в админ-панели.")
    try:
        send_rating_request(uid, pid)
    except Exception as e:
        print("rating request error:", e)
    return "ok", None


# ======================= Админ-панель =======================

def admin_back():
    return [cb("⬅️ Админ-панель", "admin")]


def screen_admin():
    q = lambda sql: db.execute(sql).fetchone()[0]
    in_stock = q("SELECT COUNT(*) FROM stock s JOIN products p ON p.id=s.product_id "
                 "WHERE s.used_by IS NULL AND p.active=1")
    crypto_sum = q("SELECT COALESCE(SUM(amount),0) FROM crypto_invoices WHERE status='paid'")
    rub_sum = q("SELECT COALESCE(SUM(amount),0) FROM rub_requests "
                "WHERE status='approved' AND COALESCE(method,'tbank')='tbank'")
    dc_sum = q("SELECT COALESCE(SUM(amount),0) FROM rub_requests "
               "WHERE status='approved' AND method='dc'")
    rub_wait = q("SELECT COUNT(*) FROM rub_requests WHERE status='pending'")
    cars_done = q("SELECT COUNT(*) FROM car_orders WHERE status='done'")
    cars_sum = q("SELECT COALESCE(SUM(price),0) FROM car_orders WHERE status='done'")
    cars_open = q("SELECT COUNT(*) FROM car_orders WHERE status IN ('paid','sent')")
    cars_wait = q("SELECT COUNT(*) FROM car_orders WHERE status='sent'")
    text = ("⚙️ Админ-панель\n\n"
            f"👥 Пользователей: {q('SELECT COUNT(*) FROM users')}\n"
            f"💰 Сумма балансов: {q('SELECT COALESCE(SUM(balance),0) FROM users')} {COIN}\n"
            f"⭐ Получено Stars: {q('SELECT COALESCE(SUM(stars),0) FROM payments WHERE refunded=0')}\n"
            f"🛍 Продаж: {q('SELECT COUNT(*) FROM stock WHERE used_by IS NOT NULL')} "
            f"на {q('SELECT COALESCE(SUM(price_paid),0) FROM stock WHERE used_by IS NOT NULL')} {COIN}\n"
            f"🤝 Рефералов: {q('SELECT COUNT(*) FROM users WHERE referrer IS NOT NULL')}\n"
            f"💎 Crypto получено: {crypto_sum:g} {CRYPTO_ASSET}\n"
            f"🏦 {TBANK_NAME} получено: {rub_sum} ₽\n"
            f"🏙 {DC_NAME} получено: {dc_sum} сомони\n"
            f"⏳ Заявок на проверке: {rub_wait}\n"
            f"🚗 Машин продано: {cars_done} на {cars_sum} {COIN} (в работе: {cars_open})\n"
            f"🎟 Активаций промокодов: {q('SELECT COUNT(*) FROM promo_uses')}\n"
            f"📦 В складе: {in_stock}")
    kb = markup(
        [cb("📦 Товары и склад", "a_prods")],
        [cb("👥 Пользователи", "a_users"), cb("💳 Платежи", "a_pay")],
        [cb("📤 Продажи", "a_sales"), cb("🔎 Пользователь", "a_user")],
        [cb("💰 Изменить баланс", "a_bal"), cb("✨ Премиум-эмодзи", "a_emoji")],
        [cb("🎟 Промокоды", "a_promos"), cb("📢 Рассылка", "a_bc")],
        [cb("🚗 Машины" + (f" ({cars_wait})" if cars_wait else ""), "a_cars"),
         cb("🏦 Заявки на оплату" + (f" ({rub_wait})" if rub_wait else ""), "a_rub")],
        back_row())
    return text, kb


def screen_apromos(note=""):
    rows = db.execute("SELECT code, bonus, max_uses, used, expires, active FROM promos "
                      "ORDER BY rowid DESC LIMIT 30").fetchall()
    kb = []
    for r in rows:
        code, bonus, mx, used, _exp, _act = r
        mark = "🟢" if promo_alive(r) else "🔴"
        kb.append([cb(f"{mark} {code} — +{bonus} {COIN} [{used}/{mx if mx else '∞'}]",
                      f"a_promo:{code}")])
    kb.append([cb("➕ Новый промокод", "a_newpromo")])
    kb.append(admin_back())
    text = note + ("🎟 Промокоды\n\nНажми на промокод, чтобы управлять им." if rows else
                   "🎟 Промокодов пока нет. Создай первый 👇")
    return text, markup(*kb)


def screen_apromo(code, note=""):
    r = db.execute("SELECT code, bonus, max_uses, used, expires, active FROM promos WHERE code=?",
                   (code,)).fetchone()
    if not r:
        return screen_apromos()
    _c, bonus, mx, used, exp, act = r
    status = "🟢 действует" if promo_alive(r) else "🔴 не действует"
    if not act:
        status += " (выключен)"
    elif exp and time.time() > exp:
        status += " (срок истёк)"
    elif mx and used >= mx:
        status += " (лимит исчерпан)"
    text = (f"{note}🎟 {code}\n\n"
            f"🎁 Бонус: +{bonus} {COIN}\n"
            f"👥 Использовано: {used}/{mx if mx else '∞'}\n"
            f"🕒 Срок до: {fmt_time(exp) if exp else 'без срока'}\n"
            f"Статус: {status}")
    kb = markup(
        [cb("🔴 Выключить" if act else "🟢 Включить", f"a_promoff:{code}")],
        [cb("🗑 Удалить", f"a_promodel:{code}", "danger")],
        [cb("⬅️ Промокоды", "a_promos")])
    return text, kb


def screen_aprods():
    rows = db.execute("SELECT id, title, price FROM products WHERE active=1 ORDER BY id").fetchall()
    kb = [[cb(f"{t} — {pr} {COIN} [{stock_count(i)}]", f"a_p:{i}")] for i, t, pr in rows]
    kb.append([cb("➕ Новый товар", "a_newprod")])
    kb.append(admin_back())
    text = "📦 Товары и склад\n\nНажми на товар, чтобы управлять им." if rows else \
           "📦 Товаров пока нет. Создай первый 👇"
    return text, markup(*kb)


def screen_aprod(pid, note=""):
    p = get_product(pid)
    if not p:
        return screen_aprods()
    _, title, price = p
    sold = db.execute("SELECT COUNT(*) FROM stock WHERE product_id=? AND used_by IS NOT NULL",
                      (pid,)).fetchone()[0]
    photo, descr = product_extra(pid)
    short = (descr[:80] + "…") if len(descr) > 80 else (descr or "нет")
    text = (f"{note}🛍 {title}\n\n💵 Цена: {price} {COIN}\n"
            f"📦 В складе: {stock_count(pid)}\n✅ Продано: {sold}\n"
            f"🖼 Фото: {'есть ✅' if photo else 'нет'}\n📝 Описание: {short}")
    line = rating_line(pid)
    if line:
        text += "\n" + line
    kb = markup(
        [cb("➕ Добавить аккаунты", f"a_add:{pid}")],
        [cb("🖼 Фото", f"a_photo:{pid}"), cb("📝 Описание", f"a_desc:{pid}")],
        [cb("🗑 Убрать фото", f"a_nophoto:{pid}")] if photo else [],
        [cb("👁 Как видит покупатель", f"a_view:{pid}")],
        [cb("✏️ Изменить цену", f"a_price:{pid}"), cb("✏️ Название", f"a_title:{pid}")],
        [cb("🗑 Удалить 1", f"a_del:{pid}:1"), cb("🗑 Удалить 5", f"a_del:{pid}:5"),
         cb("🗑 Удалить 10", f"a_del:{pid}:10")],
        [cb("🧹 Очистить склад", f"a_clr:{pid}"), cb("❌ Удалить товар", f"a_rm:{pid}", "danger")],
        [cb("⬅️ Товары", "a_prods")])
    return text, kb


def ask_admin(uid, mid, state, text):
    ADMIN_STATE[uid] = state
    edit(uid, mid, text + "\n\n/cancel — отмена", markup([cb("✖️ Отмена", "admin")]))


def send_chunks(chat_id, head, lines):
    chunk = head
    for line in lines:
        if len(chunk) + len(line) > 3800:
            send(chat_id, chunk)
            chunk = ""
        chunk += line + "\n"
    if chunk.strip():
        send(chat_id, chunk, markup(admin_back()))


def show_users(uid):
    rows = db.execute("SELECT user_id, balance FROM users ORDER BY balance DESC, joined DESC "
                      "LIMIT 40").fetchall()
    total = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    send_chunks(uid, f"👥 Пользователей: {total} (топ по балансу)\n\n",
                [f"{i}. {name_of(u)} — {b} {COIN}" for i, (u, b) in enumerate(rows, 1)] or ["Пока никого."])


def show_payments(uid):
    rows = db.execute("SELECT id, user_id, stars, ts, refunded FROM payments "
                      "ORDER BY id DESC LIMIT 20").fetchall()
    lines = [f"#{i} {fmt_time(ts)} — {name_of(u)} — {s} ⭐" + (" ↩️ возвращён" if r else "")
             for i, u, s, ts, r in rows]
    crows = db.execute("SELECT user_id, amount, coins, paid_at FROM crypto_invoices "
                       "WHERE status='paid' ORDER BY paid_at DESC LIMIT 10").fetchall()
    if crows:
        lines.append("\n💎 Crypto (возврат вручную):")
        lines += [f"{fmt_time(t)} — {name_of(u)} — {a:g} {CRYPTO_ASSET} → {c} {COIN}"
                  for u, a, c, t in crows]
    rrows = db.execute("SELECT id, user_id, amount, done_at, method FROM rub_requests "
                       "WHERE status='approved' ORDER BY done_at DESC LIMIT 10").fetchall()
    if rrows:
        lines.append("\n🏦 Ручные оплаты (подтверждено):")
        lines += [f"#{i} {fmt_time(t)} — {name_of(u)} — {a} {method_cfg(m or 'tbank')['unit']}"
                  f" ({method_cfg(m or 'tbank')['name']})" for i, u, a, t, m in rrows]
    send_chunks(uid, "💳 Последние платежи\nВозврат Stars: /refund ID\n\n",
                lines or ["Платежей пока нет."])


def show_sales(uid):
    rows = db.execute(
        "SELECT p.title, s.price_paid, s.used_by, s.used_at FROM stock s "
        "LEFT JOIN products p ON p.id=s.product_id WHERE s.used_by IS NOT NULL "
        "ORDER BY s.used_at DESC, s.id DESC LIMIT 30").fetchall()
    send_chunks(uid, "📤 Последние продажи\n\n",
                [f"{fmt_time(ts)} — {t or 'Товар'} — {pr or 0} {COIN} → {name_of(u)}"
                 for t, pr, u, ts in rows] or ["Продаж пока нет."])


def find_user(arg):
    arg = arg.lstrip("@")
    if arg.isdigit():
        return int(arg)
    r = db.execute("SELECT user_id FROM users WHERE LOWER(username)=LOWER(?)", (arg,)).fetchone()
    return r[0] if r else None


def show_user(admin_id, arg):
    uid = find_user(arg)
    if uid is None:
        send(admin_id, "Пользователь не найден.")
        return
    topup = db.execute("SELECT COALESCE(SUM(stars),0) FROM payments WHERE user_id=? AND refunded=0",
                       (uid,)).fetchone()[0]
    buys = db.execute("SELECT COUNT(*), COALESCE(SUM(price_paid),0) FROM stock WHERE used_by=?",
                      (uid,)).fetchone()
    lines = [f"🔎 {name_of(uid)}\n", f"💰 Баланс: {balance(uid)} {COIN}",
             f"⭐ Пополнено всего: {topup}", f"🛍 Покупок: {buys[0]} на {buys[1]} {COIN}\n"]
    for t, d, ts in db.execute(
            "SELECT p.title, s.data, s.used_at FROM stock s LEFT JOIN products p ON p.id=s.product_id "
            "WHERE s.used_by=? ORDER BY s.used_at DESC LIMIT 5", (uid,)):
        lines.append(f"• {fmt_time(ts)} — {t or 'Товар'}: {d}")
    send(admin_id, "\n".join(lines), markup(admin_back()))


def handle_admin_cb(uid, mid, data):
    global BCAST_RUNNING
    if data == "admin":
        ADMIN_STATE.pop(uid, None)
        BCAST.pop(uid, None)
        show(uid, mid, screen_admin())
    elif data == "a_rub":
        show(uid, mid, screen_arub())
    elif data == "a_cars":
        ADMIN_STATE.pop(uid, None)
        show(uid, mid, screen_acars())
    elif data == "a_corders":
        show(uid, mid, screen_acorders())
    elif data == "a_newcar":
        ask_admin(uid, mid, ("newcar",),
                  "➕ Новая машина. Отправь одним сообщением:\nНазвание | цена\n\n"
                  "Например:\nBMW M5 | 100")
    elif data.startswith("a_car:"):
        show(uid, mid, screen_acar(int(data.split(":")[1])))
    elif data.startswith("a_carphoto:"):
        ask_admin(uid, mid, ("car_photo", int(data.split(":")[1])),
                  "🖼 Отправь фото машины.\nЕсли напишешь подпись к фото, она станет описанием.")
    elif data.startswith("a_carnophoto:"):
        cid = int(data.split(":")[1])
        db.execute("UPDATE cars SET photo=NULL WHERE id=?", (cid,))
        db.commit()
        show(uid, mid, screen_acar(cid, "🗑 Фото убрано.\n\n"))
    elif data.startswith("a_cardesc:"):
        ask_admin(uid, mid, ("car_desc", int(data.split(":")[1])),
                  "📝 Отправь описание машины (до 700 символов).\nЧтобы убрать, отправь «-»")
    elif data.startswith("a_carprice:"):
        ask_admin(uid, mid, ("car_price", int(data.split(":")[1])),
                  f"✏️ Отправь новую цену числом (в {COIN}).")
    elif data.startswith("a_cartitle:"):
        ask_admin(uid, mid, ("car_title", int(data.split(":")[1])), "✏️ Отправь новое название машины.")
    elif data.startswith("a_carview:"):
        show_car(uid, None, int(data.split(":")[1]))
    elif data.startswith("a_carrmy:"):
        cid = int(data.split(":")[1])
        db.execute("UPDATE cars SET active=0 WHERE id=?", (cid,))
        db.commit()
        show(uid, mid, screen_acars())
    elif data.startswith("a_carrm:"):
        cid = int(data.split(":")[1])
        edit(uid, mid, "Удалить машину? Она пропадёт из магазина (история заказов сохранится).",
             markup([cb("❌ Да, удалить", f"a_carrmy:{cid}", "danger"), cb("✖️ Отмена", f"a_car:{cid}")]))
    elif data == "a_promos":
        ADMIN_STATE.pop(uid, None)
        show(uid, mid, screen_apromos())
    elif data == "a_newpromo":
        ask_admin(uid, mid, ("newpromo",),
                  "🎟 Новый промокод. Отправь одним сообщением:\n"
                  "КОД | бонус | лимит | дней\n\n"
                  "• КОД — латиница/цифры, 3–20 символов\n"
                  f"• бонус — сколько {COIN} получит пользователь\n"
                  "• лимит — сколько раз можно использовать (0 = без лимита)\n"
                  "• дней — срок действия (необязательно)\n\n"
                  "Примеры:\nSSM20 | 20 | 50\nNEWYEAR | 10 | 100 | 7")
    elif data.startswith("a_promoff:"):
        code = data.split(":", 1)[1]
        db.execute("UPDATE promos SET active=1-active WHERE code=?", (code,))
        db.commit()
        show(uid, mid, screen_apromo(code, "✅ Статус изменён.\n\n"))
    elif data.startswith("a_promodel:"):
        code = data.split(":", 1)[1]
        edit(uid, mid, f"Удалить промокод {code}?",
             markup([cb("🗑 Да, удалить", f"a_promodely:{code}", "danger"),
                     cb("✖️ Отмена", f"a_promo:{code}")]))
    elif data.startswith("a_promodely:"):
        code = data.split(":", 1)[1]
        db.execute("DELETE FROM promos WHERE code=?", (code,))
        db.execute("DELETE FROM promo_uses WHERE code=?", (code,))
        db.commit()
        show(uid, mid, screen_apromos("🗑 Промокод удалён.\n\n"))
    elif data.startswith("a_promo:"):
        show(uid, mid, screen_apromo(data.split(":", 1)[1]))
    elif data == "a_bc":
        ask_admin(uid, mid, ("bcast",),
                  "📢 Рассылка\n\nОтправь сообщение, которое получат все пользователи "
                  "(текст, фото или видео с подписью). Сначала я покажу предпросмотр.")
    elif data == "a_bcgo":
        msg_ref = BCAST.pop(uid, None)
        if not msg_ref:
            edit(uid, mid, "Нет сообщения для рассылки.", markup(admin_back()))
        elif BCAST_RUNNING:
            BCAST[uid] = msg_ref
            edit(uid, mid, "⏳ Предыдущая рассылка ещё идёт. Подожди её окончания.", markup(admin_back()))
        else:
            BCAST_RUNNING = True
            threading.Thread(target=run_broadcast, args=(uid, msg_ref[0], msg_ref[1]),
                             daemon=True).start()
            edit(uid, mid, "📤 Рассылка запущена. Я напишу, когда закончу.", markup(admin_back()))
    elif data == "a_prods":
        show(uid, mid, screen_aprods())
    elif data == "a_newprod":
        ask_admin(uid, mid, ("newprod",),
                  "➕ Новый товар. Отправь одним сообщением:\nНазвание | цена\n\n"
                  "Например:\nФулл аккаунт CPM | 100")
    elif data.startswith("a_p:"):
        show(uid, mid, screen_aprod(int(data.split(":")[1])))
    elif data.startswith("a_photo:"):
        ask_admin(uid, mid, ("photo", int(data.split(":")[1])),
                  "🖼 Отправь фото (скриншот) аккаунта.\n"
                  "Если напишешь подпись к фото — она станет описанием.")
    elif data.startswith("a_nophoto:"):
        pid = int(data.split(":")[1])
        db.execute("UPDATE products SET photo=NULL WHERE id=?", (pid,))
        db.commit()
        show(uid, mid, screen_aprod(pid, "🗑 Фото убрано.\n\n"))
    elif data.startswith("a_desc:"):
        ask_admin(uid, mid, ("desc", int(data.split(":")[1])),
                  "📝 Отправь описание аккаунта (до 700 символов): уровень, машины, деньги и т.д.\n"
                  "Чтобы убрать описание, отправь «-»")
    elif data.startswith("a_view:"):
        show_product(uid, None, int(data.split(":")[1]))
    elif data.startswith("a_add:"):
        ask_admin(uid, mid, ("addacc", int(data.split(":")[1])),
                  "➕ Отправь аккаунты одним сообщением. Каждая строка = 1 аккаунт, например:\n"
                  "логин1:пароль1\nлогин2:пароль2")
    elif data.startswith("a_price:"):
        ask_admin(uid, mid, ("price", int(data.split(":")[1])),
                  f"✏️ Отправь новую цену числом (в {COIN}).")
    elif data.startswith("a_title:"):
        ask_admin(uid, mid, ("title", int(data.split(":")[1])), "✏️ Отправь новое название товара.")
    elif data.startswith("a_del:"):
        _, pid, n = data.split(":")
        db.execute("DELETE FROM stock WHERE id IN (SELECT id FROM stock WHERE product_id=? "
                   "AND used_by IS NULL ORDER BY id DESC LIMIT ?)", (int(pid), int(n)))
        db.commit()
        show(uid, mid, screen_aprod(int(pid), f"🗑 Удалено (до {n} шт.)\n\n"))
    elif data.startswith("a_clr:"):
        pid = int(data.split(":")[1])
        edit(uid, mid, f"Удалить все {stock_count(pid)} аккаунтов этого товара из склада?",
             markup([cb("🧹 Да, очистить", f"a_clry:{pid}", "danger"), cb("✖️ Отмена", f"a_p:{pid}")]))
    elif data.startswith("a_clry:"):
        pid = int(data.split(":")[1])
        db.execute("DELETE FROM stock WHERE product_id=? AND used_by IS NULL", (pid,))
        db.commit()
        show(uid, mid, screen_aprod(pid, "🧹 Склад очищен.\n\n"))
    elif data.startswith("a_rm:"):
        pid = int(data.split(":")[1])
        edit(uid, mid, "Удалить товар? Он пропадёт из магазина (история продаж сохранится).",
             markup([cb("❌ Да, удалить", f"a_rmy:{pid}", "danger"), cb("✖️ Отмена", f"a_p:{pid}")]))
    elif data.startswith("a_rmy:"):
        pid = int(data.split(":")[1])
        db.execute("UPDATE products SET active=0 WHERE id=?", (pid,))
        db.execute("DELETE FROM stock WHERE product_id=? AND used_by IS NULL", (pid,))
        db.commit()
        show(uid, mid, screen_aprods())
    elif data == "a_users":
        show_users(uid)
    elif data == "a_pay":
        show_payments(uid)
    elif data == "a_sales":
        show_sales(uid)
    elif data == "a_emoji":
        handle_emoji_cmd({"from": {"id": uid}, "text": "/emoji"})
    elif data == "a_user":
        ask_admin(uid, mid, ("user",), "🔎 Отправь ID или @username пользователя.")
    elif data == "a_bal":
        ask_admin(uid, mid, ("bal",),
                  "💰 Изменить баланс. Отправь:\nID сумма\n\nНапример:\n123456789 +50\n123456789 -20")


def run_broadcast(admin_id, src_chat, src_mid):
    """Дар риштаи алоҳида кор мекунад, то бот ва пардохтҳо банд нашаванд."""
    global BCAST_RUNNING
    ok = fail = blocked = 0
    try:
        con = sqlite3.connect(DB_PATH, timeout=30)
        ids = [r[0] for r in con.execute(
            "SELECT user_id FROM users WHERE COALESCE(blocked,0)=0 AND user_id!=?", (admin_id,))]
        for u in ids:
            for attempt in range(2):
                try:
                    api("copyMessage", chat_id=u, from_chat_id=src_chat, message_id=src_mid)
                    ok += 1
                    break
                except Exception as e:
                    err = str(e)
                    m = re.search(r'retry_after"?:\s*(\d+)', err)
                    if m and attempt == 0:
                        time.sleep(int(m.group(1)) + 1)
                        continue
                    fail += 1
                    if any(k in err for k in ("blocked", "deactivated", "chat not found", "kicked")):
                        blocked += 1
                        con.execute("UPDATE users SET blocked=1 WHERE user_id=?", (u,))
                        con.commit()
                    break
            time.sleep(0.05)
        con.close()
        send(admin_id, f"✅ Рассылка завершена\n\n📨 Доставлено: {ok}\n"
                       f"🚫 Не доставлено: {fail} (заблокировали бота: {blocked})",
             markup(admin_back()))
    except Exception as e:
        print("broadcast error:", e)
        send(admin_id, f"⚠️ Ошибка рассылки: {e}")
    finally:
        BCAST_RUNNING = False


def handle_admin_state(uid, text):
    state = ADMIN_STATE.pop(uid, None)
    if not state:
        return
    kind = state[0]
    if kind == "cardone":
        finish_car_order(uid, state[1], text)
    elif kind == "newcar":
        if "|" not in text:
            ADMIN_STATE[uid] = state
            send(uid, "Формат: Название | цена\nНапример: BMW M5 | 100")
            return
        title, _, price = text.rpartition("|")
        title, price = title.strip(), price.strip()
        if not title or not price.isdigit() or int(price) <= 0:
            ADMIN_STATE[uid] = state
            send(uid, "Цена должна быть положительным числом. Попробуй ещё раз.")
            return
        cur = db.execute("INSERT INTO cars(title, price) VALUES(?,?)", (title[:60], int(price)))
        db.commit()
        cid = cur.lastrowid
        send(uid, f"✅ Кнопка создана: {title} — {price} {COIN}\nМожно добавить фото и описание 👇",
             markup([cb("🖼 Фото", f"a_carphoto:{cid}"), cb("📝 Описание", f"a_cardesc:{cid}")],
                    [cb("⚙️ Управлять", f"a_car:{cid}")], [cb("↩️ В раздел «Машины»", "cars")]))
    elif kind == "car_price":
        if not text.strip().isdigit() or int(text) <= 0:
            ADMIN_STATE[uid] = state
            send(uid, "Нужно положительное число. Попробуй ещё раз.")
            return
        db.execute("UPDATE cars SET price=? WHERE id=?", (int(text), state[1]))
        db.commit()
        send(uid, f"✅ Цена обновлена: {int(text)} {COIN}", markup([cb("🚗 К машине", f"a_car:{state[1]}")]))
    elif kind == "car_title":
        db.execute("UPDATE cars SET title=? WHERE id=?", (text.strip()[:60], state[1]))
        db.commit()
        send(uid, "✅ Название обновлено.", markup([cb("🚗 К машине", f"a_car:{state[1]}")]))
    elif kind == "car_desc":
        d = text.strip()
        db.execute("UPDATE cars SET descr=? WHERE id=?", (None if d == "-" else d[:700], state[1]))
        db.commit()
        send(uid, "🗑 Описание убрано." if d == "-" else "✅ Описание сохранено.",
             markup([cb("👁 Как видит покупатель", f"a_carview:{state[1]}")],
                    [cb("🚗 К машине", f"a_car:{state[1]}")]))
    elif kind == "car_photo":
        ADMIN_STATE[uid] = state
        send(uid, "Нужно отправить именно фото (не текст). Или /cancel.")
    elif kind == "newpromo":
        parts = [p.strip() for p in text.split("|")]
        code = parts[0].upper() if parts else ""
        try:
            bonus = int(parts[1])
            limit = int(parts[2]) if len(parts) > 2 and parts[2] else 0
            days = int(parts[3]) if len(parts) > 3 and parts[3] else 0
        except (ValueError, IndexError):
            ADMIN_STATE[uid] = state
            send(uid, "Формат: КОД | бонус | лимит | дней\nНапример: SSM20 | 20 | 50")
            return
        if not PROMO_RE.match(code):
            ADMIN_STATE[uid] = state
            send(uid, "Код: только латиница, цифры и _, от 3 до 20 символов. Попробуй ещё раз.")
            return
        if bonus <= 0 or limit < 0 or days < 0:
            ADMIN_STATE[uid] = state
            send(uid, "Бонус должен быть больше 0, лимит и дни — не меньше 0. Попробуй ещё раз.")
            return
        if db.execute("SELECT 1 FROM promos WHERE code=?", (code,)).fetchone():
            ADMIN_STATE[uid] = state
            send(uid, "Такой промокод уже есть. Придумай другой код.")
            return
        now = int(time.time())
        exp = now + days * 86400 if days else None
        db.execute("INSERT INTO promos(code, bonus, max_uses, used, expires, active, created) "
                   "VALUES(?,?,?,0,?,1,?)", (code, bonus, limit, exp, now))
        db.commit()
        send(uid, f"✅ Промокод создан: {code}\n"
                  f"🎁 Бонус: +{bonus} {COIN}\n"
                  f"👥 Лимит: {limit if limit else 'без лимита'}\n"
                  f"🕒 Срок: {fmt_time(exp) if exp else 'без срока'}",
             markup([cb("🎟 Промокоды", "a_promos")], admin_back()))
    elif kind == "newprod":
        if "|" not in text:
            ADMIN_STATE[uid] = state
            send(uid, "Формат: Название | цена\nНапример: Фулл аккаунт CPM | 100")
            return
        title, _, price = text.rpartition("|")
        title, price = title.strip(), price.strip()
        if not title or not price.isdigit() or int(price) <= 0:
            ADMIN_STATE[uid] = state
            send(uid, "Цена должна быть положительным числом. Попробуй ещё раз.")
            return
        cur = db.execute("INSERT INTO products(title, price) VALUES(?,?)", (title, int(price)))
        db.commit()
        pid = cur.lastrowid
        send(uid, f"✅ Товар создан: {title} — {price} {COIN}\nТеперь добавь аккаунты 👇",
             markup([cb("➕ Добавить аккаунты", f"a_add:{pid}")], [cb("⬅️ Товары", "a_prods")]))
    elif kind == "addacc":
        pid = state[1]
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for l in lines:
            db.execute("INSERT INTO stock(product_id, data) VALUES(?,?)", (pid, l))
        db.commit()
        notified = notify_subscribers(pid)
        send(uid, f"✅ Добавлено: {len(lines)}\n📦 Всего в складе: {stock_count(pid)}" +
             (f"\n🔔 Уведомлено покупателей: {notified}" if notified else ""),
             markup([cb("🛍 К товару", f"a_p:{pid}")], admin_back()))
    elif kind == "price":
        if not text.strip().isdigit() or int(text) <= 0:
            ADMIN_STATE[uid] = state
            send(uid, "Нужно положительное число. Попробуй ещё раз.")
            return
        db.execute("UPDATE products SET price=? WHERE id=?", (int(text), state[1]))
        db.commit()
        send(uid, f"✅ Цена обновлена: {int(text)} {COIN}", markup([cb("🛍 К товару", f"a_p:{state[1]}")]))
    elif kind == "title":
        db.execute("UPDATE products SET title=? WHERE id=?", (text.strip()[:60], state[1]))
        db.commit()
        send(uid, "✅ Название обновлено.", markup([cb("🛍 К товару", f"a_p:{state[1]}")]))
    elif kind == "desc":
        d = text.strip()
        db.execute("UPDATE products SET descr=? WHERE id=?",
                   (None if d == "-" else d[:700], state[1]))
        db.commit()
        send(uid, "🗑 Описание убрано." if d == "-" else "✅ Описание сохранено.",
             markup([cb("👁 Как видит покупатель", f"a_view:{state[1]}")],
                    [cb("🛍 К товару", f"a_p:{state[1]}")]))
    elif kind == "photo":
        ADMIN_STATE[uid] = state
        send(uid, "Нужно отправить именно фото (не текст). Или /cancel.")
    elif kind == "user":
        parts = text.strip().split()
        if parts:
            show_user(uid, parts[0])
    elif kind == "bal":
        parts = text.split()
        try:
            target, delta = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            ADMIN_STATE[uid] = state
            send(uid, "Формат: ID сумма, например: 123456789 +50")
            return
        r = db.execute("SELECT 1 FROM users WHERE user_id=?", (target,)).fetchone()
        if not r:
            send(uid, "Такого пользователя нет в базе (он должен хотя бы раз нажать /start).")
            return
        add_tx(target, delta, "admin", "ручное изменение")
        db.commit()
        send(uid, f"✅ Баланс {name_of(target)}: {balance(target)} {COIN}", markup(admin_back()))
        send(target, f"💰 Баланс изменён админом: {delta:+d} {COIN}\nТеперь: {balance(target)} {COIN}")


# ======================= Премиум-эмодзи (команда) =======================

def u16_slice(text, off, ln):
    return text.encode("utf-16-le")[off * 2:(off + ln) * 2].decode("utf-16-le", "ignore")


def handle_emoji_cmd(msg):
    uid = msg["from"]["id"]
    text = msg.get("text", "")
    ents = [e for e in msg.get("entities", []) if e.get("type") == "custom_emoji"]
    if text.strip() == "/emoji clear":
        db.execute("DELETE FROM emoji_map")
        db.commit()
        load_emoji()
        send(uid, "🗑 Премиум-эмодзи сброшены, всё снова с обычными эмодзи.")
        return
    if not ents:
        done = [e for e in BUTTON_EMOJIS if norm_emoji(e) in EMOJI_MAP]
        todo = [e for e in BUTTON_EMOJIS if norm_emoji(e) not in EMOJI_MAP]
        send(uid,
             "✨ Премиум-эмодзи (в кнопках и в тексте)\n\n"
             "Отправь /emoji и премиум-эмодзи (из любого набора). Формат:\n"
             "/emoji\n🛒 = (премиум)\n💰 = (премиум)\n\n"
             "Слева — обычный эмодзи, справа — премиум, который его заменит. "
             "Если у премиум-эмодзи тот же базовый смайл, можно отправить его без «=».\n\n"
             f"Ещё не настроены: {' '.join(todo) or '—'}\n"
             f"Уже настроены: {' '.join(done) or '—'}\n\n"
             "/emoji clear — сбросить всё.\n"
             "⚠️ Работает, если у владельца бота есть Telegram Premium. "
             "Если Telegram откажет, бот сам покажет обычные эмодзи.")
        return
    saved = []
    prev_end = 0
    for e in sorted(ents, key=lambda x: x["offset"]):
        fallback = u16_slice(text, e["offset"], e["length"])
        pre = u16_slice(text, prev_end, e["offset"] - prev_end)
        pre = pre.replace("/emoji", "").replace("=", "").strip()
        key = pre if pre else fallback
        prev_end = e["offset"] + e["length"]
        db.execute("INSERT OR REPLACE INTO emoji_map VALUES(?,?)",
                   (norm_emoji(key), e["custom_emoji_id"]))
        saved.append(key)
    db.commit()
    load_emoji()
    send(uid, f"✅ Сохранено: {' '.join(saved)}\nОткрой /menu и посмотри.")


# ======================= Обработчики =======================

def handle_message(msg):
    if msg["chat"]["type"] != "private":
        return
    user = msg["from"]
    uid = user["id"]
    is_new = ensure_user(user)

    if msg.get("successful_payment"):
        handle_payment(msg)
        return

    text = msg.get("text", "") or ""

    if text.startswith("/start") or text.startswith("/menu"):
        if is_new and text.startswith("/start"):
            register_referral(uid, text)
        TOPUP_WAIT.discard(uid)
        SUPPORT_WAIT.discard(uid)
        PROMO_WAIT.discard(uid)
        CTOPUP_WAIT.discard(uid)
        RUB_WAIT.discard(uid)
        DC_WAIT.discard(uid)
        CAR_WAIT.pop(uid, None)
        t, kb = screen_menu(uid)
        send(uid, t, kb)
        return

    if (text.split() or [""])[0].split("@")[0] == "/ref":
        t, kb = screen_ref(uid)
        send(uid, t, kb)
        return

    if text.startswith("/help"):
        t, kb = screen_help(uid)
        send(uid, t, kb)
        return

    if text.startswith("/balance"):
        t, kb = screen_menu(uid)
        send(uid, t, kb)
        return

    quick = {"/shop": screen_shop, "/cars": screen_cars, "/topup": screen_topup,
             "/buys": lambda u: screen_buys(u, 0)}
    qcmd = (text.split() or [""])[0].split("@")[0]
    if qcmd in quick:
        clear_waits(uid)
        t, kb = quick[qcmd](uid)
        send(uid, t, kb)
        return

    if (text.split() or [""])[0].split("@")[0] == "/promo":
        parts = text.split(maxsplit=1)
        if len(parts) > 1:      # /promo КОД — якбора
            do_promo(uid, parts[1])
        else:
            PROMO_WAIT.add(uid)
            t, kb = screen_promo_ask()
            send(uid, t, kb)
        return

    if text.startswith("/paysupport"):
        SUPPORT_WAIT.add(uid)
        send(uid, "💬 Опишите проблему с оплатой или возвратом одним сообщением — "
                  "я передам его администратору.", markup([cb("✖️ Отмена", "menu")]))
        return

    if uid in CAR_WAIT and text and not text.startswith("/"):
        handle_car_account(uid, text, msg.get("message_id"))
        return

    if uid in SUPPORT_WAIT and text and not text.startswith("/"):
        SUPPORT_WAIT.discard(uid)
        send(ADMIN_ID, f"💬 Вопрос по оплате\nОт: {name_of(uid)}\n\n{text[:1500]}")
        send(uid, "✅ Сообщение отправлено админу. Он свяжется с вами.", markup(back_row()))
        return

    if uid in PROMO_WAIT and text and not text.startswith("/"):
        do_promo(uid, text)
        return

    if (msg.get("photo") or msg.get("document")) and (rub_enabled() or dc_enabled()) and \
            not (uid == ADMIN_ID and ADMIN_STATE.get(uid)):
        if handle_rub_proof(msg, uid):
            return

    for wait, method in ((RUB_WAIT, "tbank"), (DC_WAIT, "dc")):
        if uid in wait and text and not text.startswith("/"):
            c = method_cfg(method)
            digits = text.strip().replace(" ", "")
            if digits.isdigit() and c["min"] <= int(digits) <= c["max"]:
                wait.discard(uid)
                start_rub_request(uid, None, int(digits), method)
            else:
                send(uid, f"Введите целое число ({c['unit']}) от {c['min']} до {c['max']}.",
                     markup([cb("✖️ Отмена", c["pre"])]))
            return

    if uid in CTOPUP_WAIT and text and not text.startswith("/"):
        try:
            amount = float(text.strip().replace(",", "."))
        except ValueError:
            amount = None
        if amount is not None and CRYPTO_MIN <= amount <= CRYPTO_MAX:
            CTOPUP_WAIT.discard(uid)
            start_crypto_payment(uid, None, round(amount, 2))
        else:
            send(uid, f"Введите число от {fmt_amount(CRYPTO_MIN)} до {CRYPTO_MAX} ({CRYPTO_ASSET}).",
                 markup([cb("✖️ Отмена", "ctopup")]))
        return

    if uid in TOPUP_WAIT and text and not text.startswith("/"):
        if text.strip().isdigit() and 1 <= int(text) <= MAX_TOPUP:
            TOPUP_WAIT.discard(uid)
            send_invoice(uid, int(text))
        else:
            send(uid, f"Введите целое число от 1 до {MAX_TOPUP}.", markup([cb("✖️ Отмена", "topup")]))
        return

    if uid == ADMIN_ID:
        st = ADMIN_STATE.get(uid)

        # Рассылка: ҳар намуди паём (матн/акс/видео) қабул мешавад
        if st and st[0] == "bcast" and not text.startswith("/"):
            ADMIN_STATE.pop(uid, None)
            BCAST[uid] = (msg["chat"]["id"], msg["message_id"])
            total = db.execute("SELECT COUNT(*) FROM users WHERE COALESCE(blocked,0)=0 "
                               "AND user_id!=?", (uid,)).fetchone()[0]
            try:
                api("copyMessage", chat_id=uid, from_chat_id=uid, message_id=msg["message_id"])
            except Exception as e:
                print("preview error:", e)
            send(uid, f"👆 Предпросмотр выше.\n\nОтправить всем ({total} польз.)?",
                 markup([cb("✅ Отправить", "a_bcgo", "success"), cb("✖️ Отмена", "admin", "danger")]))
            return

        if msg.get("photo") and st and st[0] == "photo":
            ADMIN_STATE.pop(uid, None)
            fid = msg["photo"][-1]["file_id"]
            db.execute("UPDATE products SET photo=? WHERE id=?", (fid, st[1]))
            cap = (msg.get("caption") or "").strip()
            if cap:
                db.execute("UPDATE products SET descr=? WHERE id=?", (cap[:700], st[1]))
            db.commit()
            send(uid, "✅ Фото сохранено" + (" и описание из подписи." if cap else "."),
                 markup([cb("👁 Как видит покупатель", f"a_view:{st[1]}")],
                        [cb("🛍 К товару", f"a_p:{st[1]}")]))
            return

        if msg.get("photo") and st and st[0] == "car_photo":
            ADMIN_STATE.pop(uid, None)
            fid = msg["photo"][-1]["file_id"]
            db.execute("UPDATE cars SET photo=? WHERE id=?", (fid, st[1]))
            cap = (msg.get("caption") or "").strip()
            if cap:
                db.execute("UPDATE cars SET descr=? WHERE id=?", (cap[:700], st[1]))
            db.commit()
            send(uid, "✅ Фото сохранено" + (" и описание из подписи." if cap else "."),
                 markup([cb("👁 Как видит покупатель", f"a_carview:{st[1]}")],
                        [cb("🚗 К машине", f"a_car:{st[1]}")]))
            return

        if text.startswith("/cancel"):
            ADMIN_STATE.pop(uid, None)
            BCAST.pop(uid, None)
            send(uid, "Отменено.", markup(admin_back()))
            return
        if text.startswith("/admin"):
            ADMIN_STATE.pop(uid, None)
            t, kb = screen_admin()
            send(uid, t, kb)
            return
        if text.startswith("/refund"):
            parts = text.split()
            handle_refund(uid, parts[1] if len(parts) > 1 else "")
            return
        if text.startswith("/emoji"):
            handle_emoji_cmd(msg)
            return
        if st and not text.startswith("/"):
            handle_admin_state(uid, text)
            return

    t, kb = screen_menu(uid)
    send(uid, t, kb)


def do_promo(uid, code):
    """Промокодро фаъол мекунад ва ба корбар натиҷаро мефиристад."""
    status, bonus = redeem_promo(uid, code)
    nav = markup([cb("🛒 Аккаунты", "shop")], back_row())
    again = markup([cb("🎟 Ещё раз", "promo")], back_row())
    if status == "ok":
        PROMO_WAIT.discard(uid)
        send(uid, f"🎉 Промокод активирован!\n🎁 Вам начислено: +{bonus} {COIN}\n"
                  f"💰 Баланс: {balance(uid)} {COIN}", nav)
        send(ADMIN_ID, f"🎟 Промокод {code.strip().upper()} активирован\nПользователь: {name_of(uid)} (+{bonus} {COIN})")
    elif status == "already":
        PROMO_WAIT.discard(uid)
        send(uid, "ℹ️ Вы уже использовали этот промокод.", nav)
    elif status == "limit":
        PROMO_WAIT.discard(uid)
        send(uid, "😔 Лимит активаций этого промокода исчерпан.", nav)
    elif status == "expired":
        PROMO_WAIT.discard(uid)
        send(uid, "⌛ Срок действия этого промокода истёк.", nav)
    else:
        send(uid, "❌ Такого промокода нет. Проверьте и отправьте ещё раз.",
             markup([cb("✖️ Отмена", "menu")]))


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
        TOPUP_WAIT.discard(uid)
        SUPPORT_WAIT.discard(uid)
        PROMO_WAIT.discard(uid)
        CTOPUP_WAIT.discard(uid)
        RUB_WAIT.discard(uid)
        DC_WAIT.discard(uid)
        CAR_WAIT.pop(uid, None)
        show(uid, mid, screen_menu(uid))
    elif data == "cars":
        CAR_WAIT.pop(uid, None)
        if uid == ADMIN_ID:
            ADMIN_STATE.pop(uid, None)
        show(uid, mid, screen_cars(uid))
    elif data == "caradd" and uid == ADMIN_ID:
        ADMIN_STATE[uid] = ("newcar",)
        edit(uid, mid, "➕ Новая кнопка. Отправь одним сообщением:\nНазвание | цена\n\n"
                       "Например:\nMAX FUEL | 150\n\n"
                       "Можно начать с эмодзи (он станет иконкой кнопки), например:\n🆕 SMOKE | 100\n\n"
                       "/cancel — отмена", markup([cb("✖️ Отмена", "cars")]))
    elif data == "cardel" and uid == ADMIN_ID:
        show(uid, mid, screen_car_delete(uid))
    elif data.startswith("cardel1:") and uid == ADMIN_ID:
        cid = int(data.split(":")[1])
        c = car_get(cid)
        if not c:
            show(uid, mid, screen_cars(uid))
        else:
            edit(uid, mid, f"Удалить кнопку «{c[1]}»?\nУже оформленные заказы сохранятся.",
                 markup([cb("✅ Да, удалить", f"cardel2:{cid}", "danger"), cb("✖️ Нет", "cardel")]))
    elif data.startswith("cardel2:") and uid == ADMIN_ID:
        cid = int(data.split(":")[1])
        c = car_get(cid)
        if c:
            db.execute("UPDATE cars SET active=0 WHERE id=?", (cid,))
            db.commit()
        show(uid, mid, screen_cars(uid, f"🗑 Кнопка «{c[1]}» удалена.\n\n" if c else ""))
    elif data.startswith("car:"):
        show_car(uid, mid, int(data.split(":")[1]))
    elif data.startswith("carbuy:"):
        show(uid, mid, screen_car_confirm(uid, int(data.split(":")[1])))
    elif data.startswith("carok:"):
        status, extra = do_buy_car(uid, int(data.split(":")[1]))
        if status == "ok":
            delete_msg(uid, mid)
        elif status == "nobal":
            edit(uid, mid, f"⚠️ Не хватает {extra} {COIN}. Пополните баланс.",
                 markup([cb("💰 Пополнить", "topup", "primary")], back_row("⬅️ Машины", "cars")))
        elif status == "gone":
            show(uid, mid, screen_cars(uid))
        else:
            edit(uid, mid, "😔 Не удалось выполнить покупку. Баланс не изменён.", markup(back_row()))
    elif data.startswith("caracc:"):
        ask_car_account(uid, mid, int(data.split(":")[1]))
    elif data == "carorders":
        CAR_WAIT.pop(uid, None)
        show(uid, mid, screen_car_orders(uid))
    elif data == "cclose" and uid == ADMIN_ID:
        delete_msg(uid, mid)
    elif data.startswith(("cdone:", "cdonestd:", "cno:", "cnoy:", "cview:")) and uid == ADMIN_ID:
        kind, _, oid_s = data.partition(":")
        try:
            oid = int(oid_s)
        except ValueError:
            return
        if kind == "cdone":
            admin_car_done_prompt(uid, oid)
        elif kind == "cdonestd":
            finish_car_order(uid, oid, None)
        elif kind == "cno":
            send(uid, f"Отклонить заказ #{oid} и вернуть SSM покупателю?",
                 markup([cb("✅ Да, вернуть", f"cnoy:{oid}", "danger"), cb("✖️ Нет", "cclose")]))
        elif kind == "cnoy":
            delete_msg(uid, mid)
            refund_car_order(uid, oid)
        else:
            send_admin_order(uid, oid)
    elif data == "rub" and rub_enabled():
        RUB_WAIT.discard(uid)
        show(uid, mid, screen_rub(uid, "tbank"))
    elif data == "rub_custom" and rub_enabled():
        RUB_WAIT.add(uid)
        edit(uid, mid, f"✏️ Отправьте сумму в рублях целым числом, от {TBANK_MIN} до {TBANK_MAX}.",
             markup([cb("✖️ Отмена", "rub")]))
    elif data == "dc" and dc_enabled():
        DC_WAIT.discard(uid)
        show(uid, mid, screen_rub(uid, "dc"))
    elif data == "dc_custom" and dc_enabled():
        DC_WAIT.add(uid)
        edit(uid, mid, f"✏️ Отправьте сумму в сомони целым числом, от {DC_MIN} до {DC_MAX}.",
             markup([cb("✖️ Отмена", "dc")]))
    elif data.startswith("dcpay:") and dc_enabled():
        try:
            start_rub_request(uid, mid, int(data.split(":")[1]), "dc")
        except ValueError:
            pass
    elif data.startswith("rubpay:") and rub_enabled():
        try:
            start_rub_request(uid, mid, int(data.split(":")[1]))
        except ValueError:
            pass
    elif data.startswith("rubcancel:"):
        try:
            rid = int(data.split(":")[1])
            db.execute("UPDATE rub_requests SET status='cancelled' WHERE id=? AND user_id=? "
                       "AND status='new'", (rid, uid))
            db.commit()
        except ValueError:
            pass
        show(uid, mid, screen_topup(uid))
    elif data.startswith(("rubok:", "rubno:", "rubv:")) and uid == ADMIN_ID:
        try:
            kind, rid_s = data.split(":")
            rid = int(rid_s)
        except ValueError:
            return
        if kind == "rubok":
            delete_msg(uid, mid)
            approve_rub(uid, rid)
        elif kind == "rubno":
            delete_msg(uid, mid)
            reject_rub(uid, rid)
        else:
            r = db.execute("SELECT user_id, amount, coins, status, file_id, method FROM rub_requests "
                           "WHERE id=?", (rid,)).fetchone()
            if r and r[3] == "pending" and r[4]:
                send_proof(uid, r[4], rub_caption(rid, r[0], r[1], r[2], r[5]), rub_admin_kb(rid))
            else:
                send(uid, "Заявка уже обработана или не найдена.", markup([cb("🏦 Заявки", "a_rub")]))
    elif data == "ctopup" and crypto_enabled():
        CTOPUP_WAIT.discard(uid)
        show(uid, mid, screen_ctopup(uid))
    elif data == "ctopup_custom" and crypto_enabled():
        CTOPUP_WAIT.add(uid)
        edit(uid, mid, f"✏️ Отправьте сумму пополнения числом (в {CRYPTO_ASSET}), "
                       f"от {fmt_amount(CRYPTO_MIN)} до {CRYPTO_MAX}.",
             markup([cb("✖️ Отмена", "ctopup")]))
    elif data.startswith("cpay:") and crypto_enabled():
        try:
            start_crypto_payment(uid, mid, float(data.split(":")[1]))
        except ValueError:
            pass
    elif data.startswith("ccheck:") and crypto_enabled():
        try:
            check_crypto_payment(uid, mid, int(data.split(":")[1]))
        except ValueError:
            pass
    elif data == "promo":
        TOPUP_WAIT.discard(uid)
        SUPPORT_WAIT.discard(uid)
        PROMO_WAIT.add(uid)
        show(uid, mid, screen_promo_ask())
    elif data == "help":
        show(uid, mid, screen_help(uid))
    elif data == "ref":
        show(uid, mid, screen_ref(uid))
    elif data == "shop":
        show(uid, mid, screen_shop(uid))
    elif data.startswith("shop:"):
        try:
            page = int(data.split(":")[1])
        except ValueError:
            page = 0
        show(uid, mid, screen_shop(uid, page))
    elif data.startswith(("notify:", "unnotify:")):
        kind, _, pid_s = data.partition(":")
        try:
            pid = int(pid_s)
        except ValueError:
            return
        if kind == "notify":
            db.execute("INSERT OR IGNORE INTO stock_notify(user_id, product_id) VALUES(?,?)", (uid, pid))
            note = "🔔 Готово! Мы напишем, когда появится.\n\n"
        else:
            db.execute("DELETE FROM stock_notify WHERE user_id=? AND product_id=?", (uid, pid))
            note = "🔕 Уведомление отключено.\n\n"
        db.commit()
        show_product(uid, mid, pid, note)
    elif data.startswith("p:"):
        show_product(uid, mid, int(data.split(":")[1]))
    elif data.startswith("buy:"):
        parts = data.split(":")
        pid = int(parts[1])
        qty = int(parts[2]) if len(parts) > 2 else 1
        show(uid, mid, screen_confirm(uid, pid, qty))
    elif data.startswith("buyok:"):
        parts = data.split(":")
        pid = int(parts[1])
        qty = int(parts[2]) if len(parts) > 2 else 1
        expected = int(parts[3]) if len(parts) > 3 else None
        status, extra = do_buy(uid, pid, qty, expected)
        if status == "ok":
            delete_msg(uid, mid)
        elif status == "nobal":
            edit(uid, mid, f"⚠️ Не хватает {extra} {COIN}. Пополните баланс.",
                 markup([cb("💰 Пополнить", "topup", "primary")], back_row("⬅️ Аккаунты", "shop")))
        elif status == "empty":
            edit(uid, mid, f"❌ Столько нет в наличии (осталось: {extra}).",
                 markup(back_row("⬅️ Аккаунты", "shop")))
        elif status == "changed":
            show(uid, mid, screen_confirm(
                uid, pid, qty, "ℹ️ Цена или скидка изменились. Проверьте и подтвердите ещё раз.\n\n"))
        elif status == "gone":
            show(uid, mid, screen_shop(uid))
        else:
            edit(uid, mid, "😔 Не удалось выполнить покупку. Баланс не изменён.",
                 markup(back_row()))
    elif data.startswith("rate:"):
        handle_rate(cq)
    elif data == "topup":
        TOPUP_WAIT.discard(uid)
        CTOPUP_WAIT.discard(uid)
        RUB_WAIT.discard(uid)
        DC_WAIT.discard(uid)
        show(uid, mid, screen_topup(uid))
    elif data == "topup_custom":
        TOPUP_WAIT.add(uid)
        edit(uid, mid, f"✏️ Отправьте сумму пополнения числом (в ⭐), от 1 до {MAX_TOPUP}.",
             markup([cb("✖️ Отмена", "topup")]))
    elif data.startswith("pay:"):
        n = int(data.split(":")[1])
        if 1 <= n <= MAX_TOPUP:
            send_invoice(uid, n)
    elif data.startswith("buys:"):
        try:
            page = int(data.split(":")[1])
        except ValueError:
            page = 0
        show(uid, mid, screen_buys(uid, page))
    elif (data == "admin" or data.startswith("a_")) and uid == ADMIN_ID:
        handle_admin_cb(uid, mid, data)


def handle_pre_checkout(pq):
    payload = pq.get("invoice_payload", "")
    ok = pq.get("currency") == "XTR" and payload.startswith("topup:")
    try:
        if ok:
            api("answerPreCheckoutQuery", pre_checkout_query_id=pq["id"], ok=True)
        else:
            api("answerPreCheckoutQuery", pre_checkout_query_id=pq["id"], ok=False,
                error_message="Платёж не распознан. Попробуйте ещё раз.")
    except Exception as e:
        print("pre_checkout error:", e)


def main():
    global BOT_USERNAME
    if not BOT_TOKEN:
        print("❌ Токен не найден.")
        return
    print("Бот-магазин работает...")
    load_emoji()
    try:
        BOT_USERNAME = api("getMe")["username"]
    except Exception as e:
        print("getMe error:", e)
    try:
        api("setMyCommands", commands=[
            {"command": "start", "description": "Главное меню"},
            {"command": "shop", "description": "Аккаунты"},
            {"command": "cars", "description": "Машины"},
            {"command": "topup", "description": "Пополнить баланс"},
            {"command": "buys", "description": "Мои покупки"},
            {"command": "balance", "description": "Мой баланс"},
            {"command": "promo", "description": "Ввести промокод"},
            {"command": "ref", "description": "Друзья и бонусы"},
            {"command": "help", "description": "Как это работает"},
            {"command": "paysupport", "description": "Вопрос по оплате"},
        ])
    except Exception as e:
        print("setMyCommands error:", e)
    if crypto_enabled():
        try:
            app = crypto_api("getMe")
            print("Crypto Pay подключён:", app.get("name", "ok"))
        except Exception as e:
            print("❌ Crypto Pay токен не работает:", e)
    else:
        print("ℹ️ CRYPTO_TOKEN не задан — оплата криптой выключена.")
    global LAST_CRYPTO_SYNC
    offset = 0
    while True:
        if crypto_enabled() and time.time() - LAST_CRYPTO_SYNC >= CRYPTO_SYNC_EVERY:
            LAST_CRYPTO_SYNC = time.time()
            try:
                crypto_sync()
            except Exception as e:
                print("crypto sync error:", e)
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
    main()
