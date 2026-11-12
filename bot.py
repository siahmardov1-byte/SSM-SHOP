import json, os, re, sqlite3, threading, time, urllib.request, urllib.parse, urllib.error

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
CRYPTO_TESTNET = False       # True = озмоиш тавассути @CryptoTestnetBot
CRYPTO_ASSET = "USDT"        # асъор: USDT, TON ва ғ.
CRYPTO_RATE = 50             # 1 USDT = чанд SSM
CRYPTO_PRESETS = [1, 2, 5, 10, 20]
CRYPTO_MIN = 0.5
CRYPTO_MAX = 1000
CRYPTO_EXPIRES = 3600
CRYPTO_SYNC_EVERY = 10

# --- Т-Банк (дастӣ, бо скриншоти чек) ---
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
    if REF_REQUIRE_TOPUP:
        return db.execute("SELECT COUNT(*) FROM users u WHERE u.referrer=? AND (EXISTS(SELECT 1 FROM payments p WHERE p.user_id=u.user_id AND p.refunded=0) OR EXISTS(SELECT 1 FROM crypto_invoices c WHERE c.user_id=u.user_id AND c.status='paid') OR EXISTS(SELECT 1 FROM rub_requests r WHERE r.user_id=u.user_id AND r.status='approved'))", (uid,)).fetchone()[0]
    return db.execute("SELECT COUNT(*) FROM users WHERE referrer=?", (uid,)).fetchone()[0]

def check_milestones(ref):
    n = invited_count(ref)
    for need, reward in REF_MILESTONES:
        if n < need:
            continue
        cur = db.execute("INSERT OR IGNORE INTO ref_rewards(user_id, need, reward, ts) VALUES(?,?,?,?)", (ref, need, reward, int(time.time())))
        if cur.rowcount:
            add_tx(ref, reward, "ref_milestone", str(need))
            db.commit()
            send(ref, f"🎁 Награда за друзей!\nТы пригласил {need} друзей — тебе +{reward} {COIN}\n💰 Баланс: {balance(ref)} {COIN}", markup(back_row()))

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

def create_crypto_invoice(uid, amount):
    coins = int(amount * CRYPTO_RATE)
    if coins < 1:
        return None
    try:
        inv = crypto_api("createInvoice", asset=CRYPTO_ASSET, amount=fmt_amount(amount),
                         description=f"Пополнение: {coins} {COIN}", payload=f"topup:{uid}", expires_in=CRYPTO_EXPIRES, allow_comments=False, allow_anonymous=False)
    except Exception as e:
        print("createInvoice error:", e)
        return None
    url = inv.get("bot_invoice_url") or inv.get("pay_url")
    db.execute("INSERT INTO crypto_invoices(invoice_id, user_id, amount, coins, status, ts) VALUES(?,?,?,?,'active',?)", (inv["invoice_id"], uid, amount, coins, int(time.time())))
    db.commit()
    return inv["invoice_id"], url

def credit_crypto(invoice_id):
    r = db.execute("SELECT user_id, amount, coins FROM crypto_invoices WHERE invoice_id=? AND status='active'", (invoice_id,)).fetchone()
    if not r:
        return None
    uid, amount, coins = r
    cur = db.execute("UPDATE crypto_invoices SET status='paid', paid_at=? WHERE invoice_id=? AND status='active'", (int(time.time()), invoice_id))
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
        send(ref, f"🎉 Ваш друг пополнил баланс! Вам начислено +{bonus} {COIN}\n💰 Баланс: {balance(ref)} {COIN}", markup(back_row()))
    send(uid, f"✅ Оплата получена: {fmt_amount(amount)} {CRYPTO_ASSET}\n💰 Начислено: +{coins} {COIN}\nТеперь на балансе: {balance(uid)} {COIN}", markup([cb("🛒 Аккаунты", "shop")], back_row()))
    return uid, coins

def crypto_sync():
    if not crypto_enabled():
        return
    rows = db.execute("SELECT invoice_id FROM crypto_invoices WHERE status='active' ORDER BY id DESC LIMIT 100").fetchall()
    if not rows:
        return
    res = crypto_api("getInvoices", invoice_ids=",".join(str(r[0]) for r in rows), count=100)
    items = res.get("items", []) if isinstance(res, dict) else res
    for it in items:
        st = it.get("status")
        if st == "paid":
            credit_crypto(it["invoice_id"])
        elif st == "expired":
            db.execute("UPDATE crypto_invoices SET status='expired' WHERE invoice_id=? AND status='active'", (it["invoice_id"],))
            db.commit()

def screen_ctopup(uid):
    text = (f"💎 Пополнение криптовалютой\n\nТекущий баланс: {balance(uid)} {COIN}\nКурс: 1 {CRYPTO_ASSET} = {CRYPTO_RATE} {COIN}\nМин.: {fmt_amount(CRYPTO_MIN)} {CRYPTO_ASSET}\n\nОплата через @CryptoBot.")
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
        send(uid, f"Сумма должна быть от {fmt_amount(CRYPTO_MIN)} до {CRYPTO_MAX} {CRYPTO_ASSET}.", markup([cb("✖️ Отмена", "ctopup")]))
        return
    res = create_crypto_invoice(uid, amount)
    if not res:
        send(uid, "😔 Не удалось создать счёт. Попробуйте позже.", markup(back_row()))
        return
    inv_id, url = res
    coins = int(amount * CRYPTO_RATE)
    text = (f"💎 Счёт создан\n{SEP}\n💵 К оплате: {fmt_amount(amount)} {CRYPTO_ASSET}\n🎁 Вы получите: {coins} {COIN}\n")
    kb = markup([url_btn("💳 Оплатить", url, "success")] if url else [], [cb("✅ Я оплатил(а)", f"ccheck:{inv_id}", "primary")], back_row("⬅️ Пополнение", "topup"))
    if mid:
        show(uid, mid, (text, kb))
    else:
        send(uid, text, kb)

def check_crypto_payment(uid, mid, inv_id):
    r = db.execute("SELECT user_id, status FROM crypto_invoices WHERE invoice_id=?", (inv_id,)).fetchone()
    if not r or r[0] != uid:
        return
    if r[1] == "paid":
        edit(uid, mid, f"✅ Этот счёт уже оплачен.\n💰 Баланс: {balance(uid)} {COIN}", markup([cb("🛒 Аккаунты", "shop")], back_row()))
        return
    try:
        res = crypto_api("getInvoices", invoice_ids=str(inv_id))
        items = res.get("items", []) if isinstance(res, dict) else res
        st = items[0].get("status") if items else None
    except Exception:
        st = None
    if st == "paid":
        credit_crypto(inv_id)
        delete_msg(uid, mid)
    elif st == "expired":
        db.execute("UPDATE crypto_invoices SET status='expired' WHERE invoice_id=? AND status='active'", (inv_id,))
        db.commit()
        edit(uid, mid, "⌛ Срок счёта истёк.", markup([cb("💎 Новый счёт", "ctopup")], back_row()))
    else:
        edit(uid, mid, "⏳ Оплата пока не найдена.", markup([cb("✅ Я оплатил(а)", f"ccheck:{inv_id}", "primary")], back_row("⬅️ Пополнение", "topup")))

def method_cfg(method):
    if method == "dc":
        return {"name": DC_NAME, "unit": "сомони", "rate": DC_RATE, "min": DC_MIN, "max": DC_MAX, "presets": DC_PRESETS, "pre": "dc", "icon": "🏙"}
    return {"name": TBANK_NAME, "unit": "₽", "rate": TBANK_RATE, "min": TBANK_MIN, "max": TBANK_MAX, "presets": TBANK_PRESETS, "pre": "rub", "icon": "🏦"}

def rub_enabled():
    return TBANK_ENABLED and bool(TBANK_CARD or TBANK_PHONE)

def dc_enabled():
    return DC_ENABLED and bool(DC_PHONE)

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
        lines.append(f"📱 СБП по номеру: {TBANK_PHONE}\n    ({TBANK_NAME})")
    if TBANK_CARD:
        lines.append(f"💳 Карта {TBANK_NAME}: {fmt_card(TBANK_CARD)}")
    return "\n".join(lines)

def screen_rub(uid, method="tbank"):
    c = method_cfg(method)
    text = (f"{c['icon']} Пополнение через {c['name']} ({c['unit']})\n\nТекущий баланс: {balance(uid)} {COIN}\nКурс: 1 {c['unit']} = {c['rate']} {COIN}\nМин.: {c['min']} {c['unit']}\n")
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
        send(uid, f"Сумма должна быть от {c['min']} до {c['max']} {c['unit']}.", markup([cb("✖️ Отмена", c["pre"])]))
        return
    now = int(time.time())
    db.execute("UPDATE rub_requests SET status='cancelled' WHERE user_id=? AND status='new'", (uid,))
    coins = amount * c["rate"]
    cur = db.execute("INSERT INTO rub_requests(user_id, amount, coins, status, ts, method) VALUES(?,?,?,'new',?,?)", (uid, amount, coins, now, method))
    db.commit()
    rid = cur.lastrowid
    text = (f"{c['icon']} Заявка #{rid}\n{SEP}\n💵 Переведите ровно: {amount} {c['unit']}\n🎁 Вы получите: {coins} {COIN}\n\n{requisites(method)}\n\n📎 Отправьте сюда скриншот чека.")
    kb = markup([cb("✖️ Отмена", f"rubcancel:{rid}", "danger")])
    if mid:
        show(uid, mid, (text, kb))
    else:
        send(uid, text, kb)

def send_proof(chat_id, stored, caption, buttons):
    if stored.startswith("d:"):
        return api("sendDocument", chat_id=chat_id, document=stored[2:], caption=caption[:1024], reply_markup=buttons)
    return send_photo(chat_id, stored, caption, buttons)

def rub_admin_kb(rid):
    return markup([cb("✅ Подтвердить", f"rubok:{rid}", "success"), cb("❌ Отклонить", f"rubno:{rid}", "danger")])

def rub_caption(rid, uid, amount, coins, method="tbank"):
    c = method_cfg(method or "tbank")
    return (f"{c['icon']} Заявка #{rid} ({c['name']})\nОт: {name_of(uid)}\n💵 Сумма: {amount} {c['unit']} → {coins} {COIN}")

def handle_rub_proof(msg, uid):
    ph, doc = msg.get("photo"), msg.get("document")
    if ph:
        stored, fuid = ph[-1]["file_id"], ph[-1].get("file_unique_id")
    elif doc and (doc.get("mime_type") or "").startswith("image/"):
        stored, fuid = "d:" + doc["file_id"], doc.get("file_unique_id")
    else:
        return False
    r = db.execute("SELECT id, amount, coins, method FROM rub_requests WHERE user_id=? AND status='new' AND ts>? ORDER BY id DESC LIMIT 1", (uid, int(time.time()) - 86400)).fetchone()
    if not r:
        return False
    rid, amount, coins, method = r
    c = method_cfg(method or "tbank")
    db.execute("UPDATE rub_requests SET status='pending', file_id=?, file_uid=? WHERE id=? AND status='new'", (stored, fuid, rid))
    db.commit()
    send(uid, f"✅ Чек получен! Заявка #{rid} отправлена на проверку.", markup([cb("🛒 Аккаунты", "shop")], back_row()))
    send_proof(ADMIN_ID, stored, rub_caption(rid, uid, amount, coins, method), rub_admin_kb(rid))
    return True

def approve_rub(admin_id, rid):
    r = db.execute("SELECT user_id, amount, coins, status, method FROM rub_requests WHERE id=?", (rid,)).fetchone()
    if not r:
        return
    uid, amount, coins, status, method = r
    c = method_cfg(method or "tbank")
    if status != "pending":
        return
    db.execute("UPDATE rub_requests SET status='approved', done_at=? WHERE id=? AND status='pending'", (int(time.time()), rid))
    add_tx(uid, coins, "topup_rub", str(rid))
    ref = referrer_of(uid)
    bonus = coins * REF_PERCENT // 100 if ref else 0
    if bonus > 0:
        add_tx(ref, bonus, "ref", str(uid))
    db.commit()
    send(uid, f"✅ Оплата подтверждена!\n💰 Начислено: +{coins} {COIN}", markup([cb("🛒 Аккаунты", "shop")], back_row()))
    send(admin_id, f"✅ Заявка #{rid} подтверждена.", markup([cb("🏦 Заявки", "a_rub")], admin_back()))

def reject_rub(admin_id, rid):
    r = db.execute("SELECT user_id, amount, status, method FROM rub_requests WHERE id=?", (rid,)).fetchone()
    if not r:
        return
    uid, amount, status, method = r
    c = method_cfg(method or "tbank")
    if status != "pending":
        return
    db.execute("UPDATE rub_requests SET status='rejected', done_at=? WHERE id=? AND status='pending'", (int(time.time()), rid))
    db.commit()
    send(uid, f"❌ Заявка #{rid} отклонена.", markup(back_row()))
    send(admin_id, f"❌ Заявка #{rid} отклонена.", markup([cb("🏦 Заявки", "a_rub")], admin_back()))

def screen_arub():
    rows = db.execute("SELECT id, user_id, amount, method FROM rub_requests WHERE status='pending' ORDER BY id").fetchall()
    kb = []
    for i, u, a, m in rows[:30]:
        c = method_cfg(m or "tbank")
        kb.append([cb(f"{c['icon']} #{i} — {a} {c['unit']} — {name_of(u)[:25]}", f"rubv:{i}")])
    kb.append(admin_back())
    text = f"🏦 Заявки на проверке: {len(rows)}" if rows else "🏦 Заявок на проверке нет."
    return text, markup(*kb)

def car_get(cid):
    return db.execute("SELECT id, title, price, photo, descr FROM cars WHERE id=? AND active=1", (cid,)).fetchone()

def pair_rows(buttons):
    rows = []
    for i in range(0, len(buttons), 2):
        rows.append(buttons[i:i + 2])
    return rows

def screen_cars(uid, note=""):
    rows = db.execute("SELECT id, title, price FROM cars WHERE active=1 ORDER BY id").fetchall()
    open_n = db.execute("SELECT COUNT(*) FROM car_orders WHERE user_id=? AND status IN ('paid','sent')", (uid,)).fetchone()[0]
    kb = pair_rows([cb(t, f"car:{i}", "primary") for i, t, _pr in rows])
    if uid == ADMIN_ID:
        kb.append([cb("➕ Добавить кнопку", "caradd", "success"), cb("🗑 Удалить кнопку", "cardel", "danger")])
    kb.append([cb("🧾 Мои заказы" + (f" ({open_n})" if open_n else ""), "carorders")])
    kb.append([cb("👤 Аккаунты", "shop", "primary")])
    kb.append(back_row())
    text = f"{note}🚗 Машины\n{SEP}\n💰 Баланс: {balance(uid)} {COIN}" if rows else f"{note}🚗 Машин пока нет."
    return text, markup(*kb)

def screen_car_delete(uid):
    rows = db.execute("SELECT id, title FROM cars WHERE active=1 ORDER BY id").fetchall()
    kb = pair_rows([cb(f"🗑 {t}", f"cardel1:{i}", "danger") for i, t in rows])
    kb.append(back_row("⬅️ Машины", "cars"))
    return "🗑 Удаление кнопки", markup(*kb)

def screen_car(uid, cid):
    c = car_get(cid)
    if not c:
        return screen_cars(uid)
    _, title, price, _photo, descr = c
    bal = balance(uid)
    text = f"🚗 {title}\n{SEP}\n\n{descr or ''}\n\n💵 Цена: {price} {COIN}\n💰 Баланс: {bal} {COIN}"
    kb = []
    if bal < price:
        kb.append([cb("💰 Пополнить баланс", "topup", "primary")])
    else:
        kb.append([cb(f"✅ Купить за {price} {COIN}", f"carbuy:{cid}", "success")])
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
    if bal < price:
        return f"⚠️ Не хватает {price - bal} {COIN}.", markup(back_row("⬅️ Машина", f"car:{cid}"))
    return f"🧾 Подтвердить покупку машины {title} за {price} {COIN}?", markup([cb("✅ Подтвердить", f"carok:{cid}", "success"), cb("✖️ Отмена", f"car:{cid}", "danger")])

def do_buy_car(uid, cid):
    c = car_get(cid)
    if not c:
        return "gone", None
    _, title, price, _p, _d = c
    if balance(uid) < price:
        return "nobal", price - balance(uid)
    cur = db.execute("INSERT INTO car_orders(car_id, user_id, title, price, status, ts) VALUES(?,?,?,?,'paid',?)", (cid, uid, title, price, int(time.time())))
    oid = cur.lastrowid
    add_tx(uid, -price, "buy_car", f"{title} #{oid}")
    db.commit()
    text = f"✅ Оплата прошла!\n🚗 Заказ #{oid} — {title}\n\nОтправьте данные своего аккаунта (логин и пароль)."
    kb = markup([cb("📤 Отправить аккаунт", f"caracc:{oid}", "success")], [cb("🧾 Мои заказы", "carorders")], back_row())
    send(uid, text, kb)
    return "ok", oid

def ask_car_account(uid, mid, oid):
    CAR_WAIT[uid] = oid
    edit(uid, mid, f"📤 Заказ #{oid}\n\nОтправьте логин и пароль одним сообщением:", markup([cb("✖️ Отмена", "carorders")]))

def handle_car_account(uid, text, msg_id=None):
    oid = CAR_WAIT.get(uid)
    acc = text.strip()[:500]
    db.execute("UPDATE car_orders SET status='sent', account=? WHERE id=? AND user_id=?", (acc, oid, uid))
    db.commit()
    CAR_WAIT.pop(uid, None)
    if msg_id:
        delete_msg(uid, msg_id)
    send(uid, "⏳ Данные отправлены администратору.", markup([cb("🧾 Мои заказы", "carorders")], back_row()))

def screen_car_orders(uid):
    rows = db.execute("SELECT id, title, price, status FROM car_orders WHERE user_id=? ORDER BY id DESC LIMIT 10", (uid,)).fetchall()
    if not rows:
        return "🧾 У вас пока нет заказов машин.", markup([cb("🚗 Машины", "cars")], back_row())
    names = {"paid": "ждём аккаунт 📤", "sent": "ожидайте ⏳", "done": "готово ✅", "refunded": "возвращено ↩️"}
    lines, kb = ["🧾 Ваши заказы машин\n"], []
    for oid, title, price, st in rows:
        lines.append(f"#{oid} {title} — {price} {COIN}\n    {names.get(st, st)}")
        if st == "paid":
            kb.append([cb(f"📤 Отправить аккаунт — #{oid}", f"caracc:{oid}", "success")])
    kb.append([cb("🚗 Машины", "cars")])
    kb.append(back_row())
    return "\n".join(lines), markup(*kb)

def screen_acars():
    rows = db.execute("SELECT id, title, price FROM cars WHERE active=1 ORDER BY id").fetchall()
    kb = [[cb(f"🚗 {t} — {pr} {COIN}", f"a_car:{i}")] for i, t, pr in rows]
    kb.append([cb("➕ Новая машина", "a_newcar")])
    kb.append(admin_back())
    return "🚗 Управление машинами", markup(*kb)

def redeem_promo(uid, code):
    code = (code or "").strip().upper()
    r = db.execute("SELECT bonus, max_uses, used, expires, active FROM promos WHERE code=?", (code,)).fetchone()
    if not r or not r[4]:
        return "bad", 0
    bonus, mx, used, exp, _active = r
    if exp and time.time() > exp:
        return "expired", 0
    if mx and used >= mx:
        return "limit", 0
    cur = db.execute("INSERT OR IGNORE INTO promo_uses(user_id, code, ts) VALUES(?,?,?)", (uid, code, int(time.time())))
    if cur.rowcount == 0:
        db.commit()
        return "already", 0
    db.execute("UPDATE promos SET used=used+1 WHERE code=?", (code,))
    add_tx(uid, bonus, "promo", code)
    db.commit()
    return "ok", bonus

def screen_promo_ask():
    return "🎟 Промокод\n\nОтправьте промокод в чат 👇", markup([cb("✖️ Отмена", "menu")])

def screen_menu(uid):
    r = db.execute("SELECT name FROM users WHERE user_id=?", (uid,)).fetchone()
    first = ((r[0] or "").split() or [""])[0] if r else ""
    text = f"🏠 Главное меню\n{SEP}\n💰 Баланс: {balance(uid)} {COIN}\n"
    rows = [[cb("🛒 Аккаунты", "shop", "primary"), cb("🚗 Машины", "cars", "primary")],
            [cb("💰 Пополнить", "topup", "success"), cb("📦 Мои покупки", "buys:0")],
            [cb("🎟 Промокод", "promo"), cb("🤝 Друзья", "ref")],
            [cb("❓ Помощь", "help")]]
    if uid == ADMIN_ID:
        rows.append([cb("⚙️ Админ-панель", "admin")])
    return text, markup(*rows)

def screen_help(uid):
    return "❓ Помощь по использованию бота.", markup([cb("🛒 Аккаунты", "shop")], back_row())

def screen_ref(uid):
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
    return f"🤝 Реферальная ссылка:\n{link}", markup(back_row())

SHOP_PAGE = 8

def screen_shop(uid, page=0):
    rows = db.execute("SELECT id, title, price FROM products WHERE active=1 ORDER BY id").fetchall()
    if not rows:
        return "🛒 Аккаунтов пока нет.", markup(back_row())
    items = [(pid, t, pr, stock_count(pid)) for pid, t, pr in rows]
    pages = (len(items) + SHOP_PAGE - 1) // SHOP_PAGE
    page = max(0, min(page, pages - 1))
    kb = []
    for pid, t, pr, n in items[page * SHOP_PAGE:(page + 1) * SHOP_PAGE]:
        kb.append([cb(f"{stock_icon(n)} {t} — {pr} {COIN} · {n} шт.", f"p:{pid}", "primary")])
    kb.append(back_row())
    return "🛒 Аккаунты", markup(*kb)

def get_product(pid):
    return db.execute("SELECT id, title, price FROM products WHERE id=? AND active=1", (pid,)).fetchone()

def product_extra(pid):
    r = db.execute("SELECT photo, descr FROM products WHERE id=?", (pid,)).fetchone()
    return (r[0], r[1] or "") if r else (None, "")

def bulk_percent(qty):
    return 0

def calc_total(price, qty):
    return price * qty

def screen_product(uid, pid, note=""):
    p = get_product(pid)
    if not p:
        return screen_shop(uid)
    _, title, price = p
    n = stock_count(pid)
    text = f"🛍 {title}\nЦена: {price} {COIN}\nВ наличии: {n} шт."
    kb = []
    if n > 0:
        kb.append([cb(f"✅ Купить за {price} {COIN}", f"buy:{pid}:1", "success")])
    kb.append(back_row("⬅️ Аккаунты", "shop"))
    return text, markup(*kb)

def show_product(uid, mid, pid, note=""):
    text, kb = screen_product(uid, pid, note)
    show(uid, mid, (text, kb))

def screen_confirm(uid, pid, qty=1, note=""):
    p = get_product(pid)
    _, title, price = p
    total = price * qty
    return f"Подтвердить покупку {title} за {total} {COIN}?", markup([cb("✅ Подтвердить", f"buyok:{pid}:{qty}:{total}", "success"), cb("✖️ Отмена", f"p:{pid}", "danger")])

def screen_topup(uid):
    text = f"💰 Пополнение баланса\nТекущий баланс: {balance(uid)} {COIN}"
    kb = []
    if rub_enabled():
        kb.append([cb(f"🏦 {TBANK_NAME} (₽)", "rub", "primary")])
    if dc_enabled():
        kb.append([cb(f"🏙 {DC_NAME}", "dc", "primary")])
    if crypto_enabled():
        kb.append([cb(f"💎 Крипта ({CRYPTO_ASSET})", "ctopup", "primary")])
    kb.append(back_row())
    return text, markup(*kb)

def screen_buys(uid, page=0):
    rows = db.execute("SELECT p.title, s.data, s.used_at, s.price_paid FROM stock s LEFT JOIN products p ON p.id=s.product_id WHERE s.used_by=? ORDER BY s.used_at DESC LIMIT 10", (uid,)).fetchall()
    if not rows:
        return "📦 У вас нет покупок.", markup(back_row())
    lines = ["📦 Ваши покупки:\n"]
    for title, data, ts, paid in rows:
        lines.append(f"{title} — {code(data)}")
    return "\n".join(lines), markup(back_row())

def do_buy(uid, pid, qty=1, expected=None):
    p = get_product(pid)
    _, title, price = p
    total = price * qty
    if balance(uid) < total:
        return "nobal", total - balance(uid)
    rows = db.execute("SELECT id, data FROM stock WHERE product_id=? AND used_by IS NULL LIMIT ?", (pid, qty)).fetchall()
    if len(rows) < qty:
        return "empty", 0
    now = int(time.time())
    for sid, _d in rows:
        db.execute("UPDATE stock SET used_by=?, used_at=?, price_paid=? WHERE id=?", (uid, now, price, sid))
    add_tx(uid, -total, "buy", title)
    db.commit()
    send(uid, f"✅ Покупка успешна!\n\n" + "\n".join(code(d) for _, d in rows), markup(back_row()))
    return "ok", None

def screen_admin():
    return "⚙️ Админ-панель", markup(admin_back())

def admin_back():
    return [cb("⬅️ Админ-панель", "admin")]

def handle_message(msg):
    if msg["chat"]["type"] != "private":
        return
    user = msg["from"]
    uid = user["id"]
    ensure_user(user)
    text = msg.get("text", "") or ""

    if text.startswith("/start"):
        send(uid, "Главное меню", markup(screen_menu(uid)[1]))
        return

    if uid in PROMO_WAIT and text:
        PROMO_WAIT.discard(uid)
        status, bonus = redeem_promo(uid, text)
        if status == "ok":
            send(uid, f"🎉 Промокод активирован! +{bonus} {COIN}", markup(back_row()))
        else:
            send(uid, "❌ Неверный или просроченный промокод.", markup(back_row()))
        return

    if uid in CAR_WAIT and text:
        handle_car_account(uid, text, msg.get("message_id"))
        return

    if (msg.get("photo") or msg.get("document")) and handle_rub_proof(msg, uid):
        return

    for wait, method in ((RUB_WAIT, "tbank"), (DC_WAIT, "dc")):
        if uid in wait and text:
            wait.discard(uid)
            try:
                start_rub_request(uid, None, int(text.strip()), method)
            except ValueError:
                pass
            return

    if uid in CTOPUP_WAIT and text:
        CTOPUP_WAIT.discard(uid)
        try:
            start_crypto_payment(uid, None, float(text.strip().replace(",", ".")))
        except ValueError:
            pass
        return

    send(uid, "Используйте меню:", markup(screen_menu(uid)[1]))

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
    elif data == "cars":
        show(uid, mid, screen_cars(uid))
    elif data.startswith("car:"):
        show_car(uid, mid, int(data.split(":")[1]))
    elif data.startswith("carbuy:"):
        show(uid, mid, screen_car_confirm(uid, int(data.split(":")[1])))
    elif data.startswith("carok:"):
        do_buy_car(uid, int(data.split(":")[1]))
    elif data.startswith("caracc:"):
        ask_car_account(uid, mid, int(data.split(":")[1]))
    elif data == "carorders":
        show(uid, mid, screen_car_orders(uid))
    elif data == "rub" and rub_enabled():
        RUB_WAIT.add(uid)
        show(uid, mid, screen_rub(uid, "tbank"))
    elif data == "dc" and dc_enabled():
        DC_WAIT.add(uid)
        show(uid, mid, screen_rub(uid, "dc"))
    elif data.startswith("rubpay:"):
        start_rub_request(uid, mid, int(data.split(":")[1]), "tbank")
    elif data.startswith("dcpay:"):
        start_rub_request(uid, mid, int(data.split(":")[1]), "dc")
    elif data.startswith("rubok:") and uid == ADMIN_ID:
        approve_rub(uid, int(data.split(":")[1]))
    elif data.startswith("rubno:") and uid == ADMIN_ID:
        reject_rub(uid, int(data.split(":")[1]))
    elif data == "ctopup" and crypto_enabled():
        CTOPUP_WAIT.add(uid)
        show(uid, mid, screen_ctopup(uid))
    elif data.startswith("cpay:"):
        start_crypto_payment(uid, mid, float(data.split(":")[1]))
    elif data.startswith("ccheck:"):
        check_crypto_payment(uid, mid, int(data.split(":")[1]))
    elif data == "promo":
        PROMO_WAIT.add(uid)
        show(uid, mid, screen_promo_ask())
    elif data == "help":
        show(uid, mid, screen_help(uid))
    elif data == "ref":
        show(uid, mid, screen_ref(uid))
    elif data == "shop":
        show(uid, mid, screen_shop(uid))
    elif data.startswith("p:"):
        show_product(uid, mid, int(data.split(":")[1]))
    elif data.startswith("buy:"):
        parts = data.split(":")
        show(uid, mid, screen_confirm(uid, int(parts[1]), int(parts[2]) if len(parts) > 2 else 1))
    elif data.startswith("buyok:"):
        parts = data.split(":")
        do_buy(uid, int(parts[1]), int(parts[2]))
    elif data == "topup":
        show(uid, mid, screen_topup(uid))
    elif data.startswith("buys:"):
        show(uid, mid, screen_buys(uid))
    elif data == "admin" and uid == ADMIN_ID:
        show(uid, mid, screen_admin())
    elif data == "a_rub" and uid == ADMIN_ID:
        show(uid, mid, screen_arub())

def main():
    global BOT_USERNAME
    if not BOT_TOKEN:
        print("❌ Токен не найден.")
        return
    print("Бот запущен...")
    load_emoji()
    try:
        BOT_USERNAME = api("getMe")["username"]
    except Exception as e:
        print("getMe error:", e)

    offset = 0
    while True:
        if crypto_enabled():
            try:
                crypto_sync()
            except Exception:
                pass
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
