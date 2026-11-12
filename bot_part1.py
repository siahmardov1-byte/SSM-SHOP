import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import json
import sqlite3
import time
import urllib.request
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

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# ======================= Танзимот ва База =======================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "9111340924:AAG8R57fDM0ybiRt28I8lgOMHO3xEW0ppSA")
ADMIN_ID = 8731580691
COIN = "SSM"
DB_PATH = os.environ.get("DB_PATH", "shop.db")

db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.execute("PRAGMA journal_mode=WAL")
db.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, name TEXT, username TEXT, joined INTEGER)")
db.execute("CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, title TEXT, price INTEGER, photo TEXT, descr TEXT, active INTEGER DEFAULT 1)")
db.execute("CREATE TABLE IF NOT EXISTS stock(id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, data TEXT, used_by INTEGER, used_at INTEGER, price_paid INTEGER)")
db.commit()

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

def send_photo(chat_id, photo, caption, buttons=None):
    p = {"chat_id": chat_id, "photo": photo, "caption": caption}
    if buttons:
        p["reply_markup"] = buttons
    try:
        return api("sendPhoto", **p)
    except Exception as e:
        print("send_photo error:", e)

def markup(*rows):
    return {"inline_keyboard": [list(r) for r in rows if r]}

def cb(text, data):
    return {"text": text, "callback_data": data}

# ======================= Менюи асосӣ =======================
def screen_menu(uid):
    text = f"🛒 Магазин\n\n💸 Ваш баланс: {balance(uid)} {COIN}\n\nВыберите раздел 👇"
    rows = [
        [cb("💸 🪙 Деньги и монет", "cat:money"), cb("🏎 💨 ПРЕМИУМ ТАЧКИ", "cat:cars")],
        [cb("🆕 🏎 Carparking 2", "cat:cp2"), cb("👑 🎨 RANG CING", "cat:rang")],
        [cb("🔒 ⚙️ MATOR W16", "cat:mator"), cb("🆕 👕 ВСЕ ОДЕЖДЫ", "cat:clothes")],
        [cb("🏎 🛞 ВСЕ ВИНИЛ", "cat:vinyl"), cb("🆔 💱 Обмен ID", "cat:id")],
        [cb("🆕 💨 SMOKE", "cat:smoke"), cb("🆕 ⛽ MAX FUEL", "cat:fuel")],
        [cb("🆕 🏠 ALL HOUSES", "cat:houses"), cb("✨ 🎬 ANIMATIONS", "cat:anim")],
        [cb("🆕 🛡 NO DAMAGE", "cat:nodamage"), cb("🛞 ⚙️ WHEELS", "cat:wheels")],
        [cb("📊 📈 I WINS LOSSES", "cat:stats")],
        [cb("👤 Мои покупки", "buys")],
    ]
    if uid == ADMIN_ID:
        rows.append([cb("➕ Добавить товар", "a_add_prod"), cb("➖ Удалить товар", "a_del_prod")])
    rows.append([cb("🔙 Меню", "menu")])
    return text, markup(*rows)

def screen_category(uid, cat):
    titles = {
        "money": "💸 Деньги и монеты", "cars": "🏎 Премиум тачки", "cp2": "Car Parking 2",
        "rang": "Rang Cing", "mator": "Mator W16", "clothes": "Все одежды",
        "vinyl": "Все винилы", "id": "Обмен ID", "smoke": "Smoke (Дым)",
        "fuel": "Max Fuel", "houses": "All Houses", "anim": "Animations",
        "nodamage": "No Damage", "wheels": "Wheels", "stats": "Wins & Losses"
    }
    cat_name = titles.get(cat, "Товары")
    prods = db.execute("SELECT id, title, price FROM products WHERE category=? AND active=1", (cat,)).fetchall()
    
    rows = []
    for pid, title, price in prods:
        rows.append([cb(f"{title} — {price} {COIN}", f"p:{pid}")])
    rows.append([cb("⬅️ Назад в меню", "menu")])
    
    text = f"📂 Категория: {cat_name}\n\nВыберите товар из списка 👇"
    return text, markup(*rows)

def show_product_card(uid, msg_id, pid):
    p = db.execute("SELECT id, title, price, photo, descr FROM products WHERE id=?", (pid,)).fetchone()
    if not p:
        return
    _, title, price, photo, descr = p
    text = f"🛍 <b>{title}</b>\n\n💵 Цена: {price} {COIN}\n\n📝 Описание:\n{descr or 'Описание отсутствует.'}"
    kb = markup([cb("🛒 Купить", f"buy:{pid}")], [cb("⬅️ Назад", "menu")])
    
    if msg_id:
        try:
            api("deleteMessage", chat_id=uid, message_id=msg_id)
        except Exception:
            pass
    if photo:
        send_photo(uid, photo, text, kb)
    else:
        send(uid, text, kb)

# ======================= Коркарди паёмҳо ва Админ =======================
def handle_message(msg):
    if msg.get("chat", {}).get("type") != "private":
        return
    user = msg["from"]
    uid = user["id"]
    ensure_user(user)
    text = msg.get("text", "")
    
    # Илова кардани маҳсулоти нав тавассути админ
    if uid == ADMIN_ID and uid in ADMIN_STATE:
        state = ADMIN_STATE.pop(uid)
        if state == "add_title":
            parts = text.split("|")
            if len(parts) >= 3:
                cat, title, price = parts[0].strip(), parts[1].strip(), int(parts[2].strip())
                ADMIN_STATE[uid] = ("add_desc", cat, title, price)
                send(uid, "📝 Теперь отправьте описание товара (или напишите '-' если без описания):")
            else:
                send(uid, "❌ Формат хато! Нависед: категория | ном | нарх\nМисол: cars | BMW M5 | 150")
            return
        elif state[0] == "add_desc":
            _, cat, title, price = state
            descr = "" if text.strip() == "-" else text.strip()
            ADMIN_STATE[uid] = ("add_photo", cat, title, price, descr)
            send(uid, "🖼 Отправьте фото (скриншот) товара (или напишите '-' если без фото):")
            return
        elif state[0] == "add_photo":
            _, cat, title, price, descr = state
            photo = None
            if msg.get("photo"):
                photo = msg["photo"][-1]["file_id"]
            
            db.execute("INSERT INTO products(category, title, price, photo, descr) VALUES(?,?,?,?,?)",
                       (cat, title, price, photo, descr))
            db.commit()
            send(uid, f"✅ Товар «{title}» бомуваффақият илова шуд!")
            t, kb = screen_menu(uid)
            send(uid, t, kb)
            return

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
        try:
            api("editMessageText", chat_id=uid, message_id=mid, text=t, reply_markup=kb)
        except Exception:
            send(uid, t, kb)
    elif data.startswith("cat:"):
        cat = data.split(":")[1]
        t, kb = screen_category(uid, cat)
        try:
            api("editMessageText", chat_id=uid, message_id=mid, text=t, reply_markup=kb)
        except Exception:
            send(uid, t, kb)
    elif data.startswith("p:"):
        pid = int(data.split(":")[1])
        show_product_card(uid, mid, pid)
    elif data == "a_add_prod" and uid == ADMIN_ID:
        ADMIN_STATE[uid] = "add_title"
        send(uid, "➕ Илова кардани маҳсулот.\n\nКатегорияҳоро интихоб кунед: money, cars, cp2, rang, mator, clothes, vinyl, id, smoke, fuel, houses, anim, nodamage, wheels, stats\n\nФорматро фиристед:\nкатегория | Номи маҳсулот | Нарх\n\nМисол:\ncars | BMW M5 F90 | 250")
    elif data == "a_del_prod" and uid == ADMIN_ID:
        prods = db.execute("SELECT id, title FROM products WHERE active=1").fetchall()
        rows = [[cb(f"❌ Нест кардан: {t}", f"del_p:{i}")] for i, t in prods]
        rows.append([cb("⬅️ Назад", "menu")])
        api("editMessageText", chat_id=uid, message_id=mid, text="🗑 Интихоб кунед кадом маҳсулотро нест кардан мехоҳед:", reply_markup=markup(*rows))
    elif data.startswith("del_p:") and uid == ADMIN_ID:
        pid = int(data.split(":")[1])
        db.execute("DELETE FROM products WHERE id=?", (pid,))
        db.commit()
        send(uid, "✅ Маҳсулот нест карда шуд.")
        t, kb = screen_menu(uid)
        send(uid, t, kb)

# ======================= Оғози Поллинг =======================
def main():
    if not BOT_TOKEN:
        print("❌ Токен не найден.")
        return
    print("Бот запущен с функцией добавления/удаления товаров...")
    offset = 0
    while True:
        try:
            updates = api("GetUpdates", offset=offset, timeout=10, allowed_updates=["message", "callback_query"])
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
