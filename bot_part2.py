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
