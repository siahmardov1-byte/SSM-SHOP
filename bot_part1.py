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


