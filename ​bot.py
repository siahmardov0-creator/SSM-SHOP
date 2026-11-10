#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram-бот магазина (чистый Python, urllib + sqlite3).
Доработан по ТЗ: разделы магазина, универсальные товары (cars + category),
процесс покупки с аккаунтом, админ-панель разделов.
"""

import json, os, re, sqlite3, threading, time, urllib.request, urllib.parse, urllib.error

# ======================= Танзимот =======================
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
REF_MILESTONES = [(3, 10), (5, 20), (10, 50)]
REF_REQUIRE_TOPUP = False

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

# Каналы (url-кнопки)
CHANNEL_URL = "https://t.me/your_channel"          # TELEGRAM KANAL
REVIEWS_URL = "https://t.me/your_reviews_channel"  # SSM OTVIZ

# Разделы магазина по умолчанию (засеваются в БД при первом запуске)
DEFAULT_SECTIONS = [
    # key, title, style, full_width (1 = кнопка на всю ширину)
    ("money",   "💸 Деньги и монеты", "primary", 0),
    ("premium", "🏎 ПРЕМИУМ ТАЧКА",   "primary", 0),
    ("cp2",     "🏎 Carparking 2",    "primary", 1),
    ("rang",    "👑 RANG CING",       "primary", 0),
    ("mator",   "🔒 MATOR W16",       "primary", 0),
    ("clothes", "🔒 ВСЕ ОДЕЖДЫ",      "primary", 0),
    ("vinyl",   "🏎 ВСЕ ВИНИЛ",       "primary", 0),
    ("new",     "🏎 NEW",             "success", 0),
    ("id",      "🆔 Обмен ID",        "primary", 0),
    ("sliiv",   "СЛИВ АКАУНТ",        "primary", 1),
]

BUTTON_EMOJIS = ["🛒", "💰", "📦", "❓", "🤝", "⚙️", "⬅️", "✅", "✖️", "➕", "✏️", "🗑", "🧹",
                 "❌", "👥", "💳", "📤", "🔎", "🛍", "⭐", "✨", "🔥", "🖼", "📝", "👁",
                 "🏠", "💱", "💵", "👇", "🎉", "⚠️", "🕒", "🔗", "🎁", "🔒", "➡️", "🏆", "📢",
                 "🟢", "🟡", "🔴", "🧾", "🔢", "🎟", "💎", "🏦", "📱", "📎", "🏙", "🚗", "📨", "🔐",
                 "💸", "🏎", "👑", "🆔", "👤"]

# ======================= БД =======================
db = sqlite3.connect(DB_PATH, check_same_thread=False)
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
db.execute("CREATE TABLE IF NOT EXISTS promos(code TEXT PRIMARY KEY, bonus INTEGER, "
           "max_uses INTEGER DEFAULT 0, used INTEGER DEFAULT 0, expires INTEGER, "
           "active INTEGER DEFAULT 1, created INTEGER)")
db.execute("CREATE TABLE IF NOT EXISTS promo_uses(user_id INTEGER, code TEXT, ts INTEGER, "
           "PRIMARY KEY(user_id, code))")
db.execute("CREATE TABLE IF NOT EXISTS crypto_invoices(id INTEGER PRIMARY KEY AUTOINCREMENT, "
           "invoice_id INTEGER UNIQUE, user_id INTEGER, amount REAL, coins INTEGER, "
           "status TEXT DEFAULT 'active', ts INTEGER, paid_at INTEGER)")
db.execute("CREATE TABLE IF NOT EXISTS rub_requests(id INTEGER PRIMARY KEY AUTOINCREMENT, "
           "user_id INTEGER, amount INTEGER, coins INTEGER, status TEXT DEFAULT 'new', "
           "file_id TEXT, file_uid TEXT, ts INTEGER, done_at INTEGER)")
db.execute("CREATE TABLE IF NOT EXISTS cars(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, "
           "price INTEGER, photo TEXT, descr TEXT, active INTEGER DEFAULT 1)")
db.execute("CREATE TABLE IF NOT EXISTS car_orders(id INTEGER PRIMARY KEY AUTOINCREMENT, car_id INTEGER, "
           "user_id INTEGER, title TEXT, price INTEGER, status TEXT DEFAULT 'paid', account TEXT, "
           "ts INTEGER, done_at INTEGER)")
try:
    db.execute("ALTER TABLE rub_requests ADD COLUMN method TEXT DEFAULT 'tbank'")
except sqlite3.OperationalError:
    pass
# category для универсальных товаров (старые = 'car')
try:
    db.execute("ALTER TABLE cars ADD COLUMN category TEXT DEFAULT 'car'")
except sqlite3.OperationalError:
    pass
db.execute("UPDATE cars SET category='car' WHERE category IS NULL OR category=''")
# Миграции для старых баз — все недостающие колонки
for _sql in (
    "ALTER TABLE car_orders ADD COLUMN price INTEGER DEFAULT 0",
    "ALTER TABLE car_orders ADD COLUMN title TEXT",
    "ALTER TABLE car_orders ADD COLUMN account TEXT",
    "ALTER TABLE car_orders ADD COLUMN done_at INTEGER",
    "ALTER TABLE car_orders ADD COLUMN car_id INTEGER",
    "ALTER TABLE car_orders ADD COLUMN user_id INTEGER",
    "ALTER TABLE car_orders ADD COLUMN status TEXT DEFAULT 'paid'",
    "ALTER TABLE car_orders ADD COLUMN ts INTEGER",
    "ALTER TABLE cars ADD COLUMN photo TEXT",
    "ALTER TABLE cars ADD COLUMN descr TEXT",
    "ALTER TABLE cars ADD COLUMN active INTEGER DEFAULT 1",
    "ALTER TABLE cars ADD COLUMN price INTEGER DEFAULT 0",
    "ALTER TABLE cars ADD COLUMN title TEXT",
    "ALTER TABLE products ADD COLUMN photo TEXT",
    "ALTER TABLE products ADD COLUMN descr TEXT",
    "ALTER TABLE products ADD COLUMN price INTEGER DEFAULT 0",
    "ALTER TABLE stock ADD COLUMN price_paid INTEGER",
    "ALTER TABLE rub_requests ADD COLUMN method TEXT DEFAULT 'tbank'",
):
    try:
        db.execute(_sql)
    except sqlite3.OperationalError:
        pass
# Если у заказов price=0/NULL — подтянуть из cars
try:
    db.execute("""
        UPDATE car_orders SET price = (
            SELECT c.price FROM cars c WHERE c.id = car_orders.car_id
        ) WHERE (price IS NULL OR price = 0) AND car_id IS NOT NULL
    """)
except Exception as e:
    print("price backfill skip:", e)
db.commit()
print("DB migrations done")


# --- Разделы магазина (кнопки) ---
db.execute("""CREATE TABLE IF NOT EXISTS sections(
    key TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    style TEXT DEFAULT 'primary',
    full_width INTEGER DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1,
    emoji_cid TEXT
)""")
try:
    db.execute("ALTER TABLE sections ADD COLUMN emoji_cid TEXT")
except sqlite3.OperationalError:
    pass
# seed defaults if empty
_cnt = db.execute("SELECT COUNT(*) FROM sections").fetchone()[0]
if _cnt == 0:
    for i, (k, t, st, fw) in enumerate(DEFAULT_SECTIONS):
        db.execute("INSERT OR IGNORE INTO sections(key, title, style, full_width, sort_order, active) VALUES(?,?,?,?,?,1)",
                   (k, t, st, fw, i * 10))
    print("sections seeded:", len(DEFAULT_SECTIONS))
db.commit()

TOPUP_WAIT = set()
SUPPORT_WAIT = set()
PROMO_WAIT = set()
CTOPUP_WAIT = set()
RUB_WAIT = set()
DC_WAIT = set()
CAR_WAIT = {}          # uid -> order_id
LAST_CRYPTO_SYNC = 0
ADMIN_STATE = {}
BCAST = {}
BCAST_RUNNING = False

# ======================= Telegram API =======================

def api(method, **params):
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан в переменных окружения")
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


def sec_btn(title, data, style=None, emoji_cid=None):
    """Кнопка раздела: если задан emoji_cid — премиум-иконка, иначе обычная логика _btn."""
    if emoji_cid:
        b = {"text": title, "callback_data": data, "icon_custom_emoji_id": str(emoji_cid)}
        if style and BUTTON_STYLES:
            b["style"] = style
        return b
    return cb(title, data, style)


def markup(*rows):
    return {"inline_keyboard": [list(r) for r in rows if r]}


def is_fancy(buttons):
    return bool(buttons) and any("icon_custom_emoji_id" in b or "style" in b
                                 for row in buttons["inline_keyboard"] for b in row)


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
            ents.append({"type": "custom_emoji", "offset": off, "length": length,
                         "custom_emoji_id": cid})
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


def send(chat_id, text, buttons=None, entities=None):
    ents = entities if entities is not None else decorate(text)
    last = None
    for b, use in _variants(buttons, bool(ents)):
        p = {"chat_id": chat_id, "text": text}
        if b:
            p["reply_markup"] = b
        if use and ents:
            p["entities"] = ents
        try:
            return api("sendMessage", **p)
        except Exception as e:
            last = e
    print("send error:", last)
    return None


def send_photo(chat_id, file_id, caption, buttons=None):
    caption = caption[:1024]
    ents = decorate(caption)
    last = None
    for b, use in _variants(buttons, bool(ents)):
        p = {"chat_id": chat_id, "photo": file_id, "caption": caption}
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
    ents = decorate(text)
    for b, use in _variants(buttons, bool(ents)):
        p = {"chat_id": chat_id, "message_id": msg_id, "text": text}
        if b:
            p["reply_markup"] = b
        if use:
            p["entities"] = ents
        try:
            return api("editMessageText", **p)
        except Exception as e:
            s = str(e)
            if "not modified" in s:
                return None
            if "no text in the message" in s:
                res = send(chat_id, text, buttons)
                if res:
                    delete_msg(chat_id, msg_id)
                return res
    return send(chat_id, text, buttons)


def show(chat_id, msg_id, screen):
    return edit(chat_id, msg_id, screen[0], screen[1])


# ======================= Пользователи и баланс =======================

def ensure_user(user):
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


# ======================= Crypto =======================

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
         markup([cb("🛒 Магазин", "shop")], back_row()))
    send(ADMIN_ID, f"💎 Crypto-пополнение: {fmt_amount(amount)} {CRYPTO_ASSET} ({coins} {COIN})\n"
                   f"От: {name_of(uid)}")
    return uid, coins


def crypto_sync():
    if not crypto_enabled():
        return
    rows = db.execute("SELECT invoice_id FROM crypto_invoices WHERE status='active' "
                      "ORDER BY id DESC LIMIT 100").fetchall()
    if not rows:
        return
    try:
        res = crypto_api("getInvoices", invoice_ids=",".join(str(r[0]) for r in rows), count=100)
    except Exception as e:
        print("crypto_sync error:", e)
        return
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
             markup([cb("🛒 Магазин", "shop")], back_row()))
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


# ======================= Ручные платежи =======================

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
         markup([cb("🛒 Магазин", "shop")], back_row()))
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
         markup([cb("🛒 Магазин", "shop")], back_row()))
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


# ======================= Универсальные товары (cars + category) =======================

def get_sections(active_only=True):
    """Список разделов из БД: (key, title, style, full_width, emoji_cid)."""
    sql = "SELECT key, title, style, full_width, emoji_cid FROM sections"
    if active_only:
        sql += " WHERE active=1"
    sql += " ORDER BY sort_order, key"
    try:
        rows = db.execute(sql).fetchall()
        return rows
    except Exception as e:
        print("get_sections error:", e)
        # fallback without emoji_cid
        try:
            sql2 = "SELECT key, title, style, full_width FROM sections"
            if active_only:
                sql2 += " WHERE active=1"
            sql2 += " ORDER BY sort_order, key"
            return [(*r, None) for r in db.execute(sql2).fetchall()]
        except Exception:
            return [(k, t, st, fw, None) for k, t, st, fw in DEFAULT_SECTIONS]


def section_title(cat):
    r = db.execute("SELECT title FROM sections WHERE key=?", (cat,)).fetchone()
    if r:
        return r[0]
    for key, title, st, fw in DEFAULT_SECTIONS:
        if key == cat:
            return title
    return cat


# Категории → тип заказа для текстов (money / car / other)
MONEY_CATS = {"money"}
CAR_CATS = {"premium", "cp2", "vinyl", "new", "car", "mator"}


def order_kind_by_cat(cat):
    cat = (cat or "").lower()
    if cat in MONEY_CATS or "money" in cat or "монет" in cat or "деньг" in cat:
        return "money"
    if cat in CAR_CATS or "car" in cat or "тачк" in cat or "машин" in cat:
        return "car"
    return "other"


def order_kind_for_oid(oid):
    """Определяет тип заказа по category товара."""
    try:
        r = db.execute(
            "SELECT c.category, o.title FROM car_orders o "
            "LEFT JOIN cars c ON c.id=o.car_id WHERE o.id=?", (oid,)
        ).fetchone()
        if r:
            kind = order_kind_by_cat(r[0])
            if kind == "other" and r[1]:
                t = r[1].lower()
                if any(x in t for x in ("деньг", "монет", "money", "ssm", "cash")):
                    return "money"
                if any(x in t for x in ("bmw", "mers", "car", "тачк", "машин", "vinil", "винил")):
                    return "car"
            return kind
    except Exception as e:
        print("order_kind error:", e)
    return "other"


def wait_text_for_kind(kind, title=""):
    if kind == "money":
        return ("⏳ Данные получены!\n\n"
                "Бот начисляет деньги на ваш аккаунт.\n"
                "Обычно это занимает несколько минут.\n\n"
                "🔒 Сообщение с паролем удалено из чата.")
    if kind == "car":
        return ("⏳ Данные получены!\n\n"
                "Бот устанавливает машину на ваш аккаунт.\n"
                "Обычно это занимает несколько минут.\n\n"
                "🔒 Сообщение с паролем удалено из чата.")
    return ("⏳ Данные получены!\n\n"
            "Бот выполняет ваш заказ.\n"
            "Обычно это занимает несколько минут.\n\n"
            "🔒 Сообщение с паролем удалено из чата.")


def done_text_for_kind(kind, title):
    if kind == "money":
        return (f"🎉 Ваш заказ готов!\n💰 {title}\n\n"
                "Бот начислил деньги на аккаунт.\n"
                "Заходите в игру и проверяйте баланс.\n"
                "Рекомендуем сменить пароль.\n\nСпасибо за покупку! ❤️")
    if kind == "car":
        return (f"🎉 Ваш заказ готов!\n🚗 {title}\n\n"
                "Бот установил машину на аккаунт.\n"
                "Заходите в игру и проверяйте.\n"
                "Рекомендуем сменить пароль.\n\nСпасибо за покупку! ❤️")
    return (f"🎉 Ваш заказ готов!\n🏎 {title}\n\n"
            "Бот выполнил ваш заказ.\n"
            "Заходите в игру и проверяйте.\n"
            "Рекомендуем сменить пароль.\n\nСпасибо за покупку! ❤️")


def admin_action_hint(kind):
    if kind == "money":
        return "Начислите деньги и нажмите «Готово»."
    if kind == "car":
        return "Установите машину и нажмите «Готово»."
    return "Выполните заказ и нажмите «Готово»."


def car_get(cid):
    return db.execute("SELECT id, title, price, photo, descr, category FROM cars "
                      "WHERE id=? AND active=1", (cid,)).fetchone()


def cars_by_category(cat):
    return db.execute("SELECT id, title, price FROM cars WHERE active=1 AND category=? "
                      "ORDER BY id", (cat,)).fetchall()


def screen_section(uid, cat):
    rows = cars_by_category(cat)
    open_n = db.execute("SELECT COUNT(*) FROM car_orders WHERE user_id=? AND status IN ('paid','sent')",
                        (uid,)).fetchone()[0]
    title = section_title(cat)
    kb = []
    for i, t, pr in rows:
        kb.append([cb(f"🏎 {t} — {pr} {COIN}", f"item:{i}", "primary")])
    if uid == ADMIN_ID:
        kb.append([cb("➕ Добавить", f"a_additem:{cat}", "success")])
    kb.append([cb("🧾 Мои заказы" + (f" ({open_n})" if open_n else ""), "myorders")])
    kb.append([cb("⬅️ Магазин", "shop")])
    if rows:
        text = f"{title}\n{SEP}\n💰 Ваш баланс: {balance(uid)} {COIN}\n\nВыберите товар 👇"
    else:
        text = f"{title}\n{SEP}\n💰 Ваш баланс: {balance(uid)} {COIN}\n\nПока пусто."
    return text, markup(*kb)


def screen_item(uid, cid):
    c = car_get(cid)
    if not c:
        return screen_shop(uid)
    _, title, price, _photo, descr, cat = c
    bal = balance(uid)
    text = f"🏎 {title}\n{SEP}\n\n"
    if descr:
        text += f"📝 {descr}\n\n"
    text += (f"💵 Цена: {price} {COIN}\n💰 Ваш баланс: {bal} {COIN}\n\n"
             "ℹ️ После оплаты вы отправите данные своего аккаунта, "
             "и администратор установит заказ.")
    kb = []
    if bal < price:
        text += f"\n\n⚠️ Не хватает {price - bal} {COIN}."
        kb.append([cb("💰 Пополнить баланс", "topup", "primary")])
    else:
        kb.append([cb(f"✅ Купить за {price} {COIN}", f"itembuy:{cid}", "success")])
    kb.append([cb("⬅️ Назад", f"sec:{cat}")])
    return text, markup(*kb)


def show_item(uid, mid, cid):
    text, kb = screen_item(uid, cid)
    c = car_get(cid)
    if c and c[3]:
        if send_photo(uid, c[3], text, kb):
            delete_msg(uid, mid)
            return
    show(uid, mid, (text, kb))


def screen_item_confirm(uid, cid):
    c = car_get(cid)
    if not c:
        return screen_shop(uid)
    _, title, price, _p, _d, cat = c
    bal = balance(uid)
    text = f"🧾 Подтверждение покупки\n{SEP}\n\n🏎 Товар: {title}\n💵 Итого: {price} {COIN}\n"
    if bal < price:
        text += f"\n⚠️ Не хватает {price - bal} {COIN}."
        return text, markup([cb("💰 Пополнить баланс", "topup", "primary")],
                            [cb("⬅️ Назад", f"item:{cid}")])
    text += f"💰 Баланс после покупки: {bal - price} {COIN}"
    return text, markup([cb("✅ Подтвердить", f"itemok:{cid}", "success"),
                         cb("✖️ Отмена", f"item:{cid}", "danger")])


def do_buy_item(uid, cid):
    """Возвращает: ('ok', oid) | ('nobal', need) | ('gone', None) | ('fail', None)."""
    c = car_get(cid)
    if not c:
        return "gone", None
    _, title, price, _p, _d, cat = c
    if balance(uid) < price:
        return "nobal", price - balance(uid)
    cur = db.execute("INSERT INTO car_orders(car_id, user_id, title, price, status, ts) "
                     "VALUES(?,?,?,?,'paid',?)", (cid, uid, title, price, int(time.time())))
    oid = cur.lastrowid
    add_tx(uid, -price, "buy_item", f"{title} #{oid}")
    db.commit()
    kind = order_kind_by_cat(cat)
    icon = "💰" if kind == "money" else ("🚗" if kind == "car" else "🏎")
    text = (f"✅ Оплата прошла!\n{icon} Заказ #{oid} — {title}\n{SEP}\n\n"
            "⚠️ Сначала выйдите из аккаунта в игре.\n"
            "Затем нажмите кнопку ниже и отправьте данные аккаунта (email : пароль).")
    kb = markup([cb("📤 Отправить аккаунт", f"itemacc:{oid}", "success")],
                [cb("🧾 Мои заказы", "myorders")], back_row())
    if not send(uid, text, kb):
        db.execute("UPDATE car_orders SET status='refunded' WHERE id=?", (oid,))
        add_tx(uid, price, "item_refund", f"#{oid}")
        db.commit()
        send(ADMIN_ID, f"⚠️ Не удалось отправить заказ #{oid} пользователю {name_of(uid)}. "
                       "Покупка отменена, SSM возвращены.")
        return "fail", None
    send(ADMIN_ID, f"🏎 Новый заказ #{oid}: {title} — {price} {COIN}\n"
                   f"Покупатель: {name_of(uid)}\nОжидает отправки данных аккаунта.")
    return "ok", oid


def ask_item_account(uid, mid, oid):
    r = db.execute("SELECT title, status FROM car_orders WHERE id=? AND user_id=?", (oid, uid)).fetchone()
    if not r:
        return
    title, status = r
    if status not in ("paid", "sent"):
        edit(uid, mid, "ℹ️ Этот заказ уже обработан.",
             markup([cb("🧾 Мои заказы", "myorders")], back_row()))
        return
    CAR_WAIT[uid] = oid
    text = f"📤 Заказ #{oid} — {title}\n\n"
    if status == "sent":
        text += "Данные уже отправлены. Если хотите изменить, отправьте новые.\n\n"
    text += ("⚠️ Сначала выйдите из аккаунта в игре.\n\n"
             "Отправьте одним сообщением:\nemail : пароль\n\n"
             "Например:\nali123@mail.com : Pass777")
    edit(uid, mid, text, markup([cb("✖️ Отмена", "myorders")]))


def item_admin_kb(oid):
    return markup([cb("✅ Готово", f"idone:{oid}", "success"),
                   cb("❌ Отклонить", f"ino:{oid}", "danger")])


def u16_len(s):
    return len(s.encode("utf-16-le")) // 2


def make_code_entities(text, parts):
    """parts = list of (start_char_index, length_in_chars) for code spans.
    Returns entities with UTF-16 offsets."""
    ents = []
    # Convert char offsets to UTF-16 code units
    # Simple approach: walk the string
    for start, length in parts:
        prefix = text[:start]
        off = u16_len(prefix)
        ln = u16_len(text[start:start + length])
        ents.append({"type": "code", "offset": off, "length": ln})
    return ents


def handle_item_account(uid, text, msg_id=None):
    oid = CAR_WAIT.get(uid)
    acc = text.strip()[:500]
    r = db.execute("SELECT title, status FROM car_orders WHERE id=? AND user_id=?",
                   (oid, uid)).fetchone() if oid else None
    if not r or r[1] not in ("paid", "sent"):
        CAR_WAIT.pop(uid, None)
        send(uid, "ℹ️ Этот заказ уже обработан.", markup([cb("🧾 Мои заказы", "myorders")], back_row()))
        return
    if len(acc) < 3:
        send(uid, "Отправьте данные в формате: email : пароль",
             markup([cb("✖️ Отмена", "myorders")]))
        return
    title = r[0]
    db.execute("UPDATE car_orders SET status='sent', account=? WHERE id=? AND user_id=? "
               "AND status IN ('paid','sent')", (acc, oid, uid))
    db.commit()
    CAR_WAIT.pop(uid, None)
    if msg_id:
        delete_msg(uid, msg_id)
    kind = order_kind_for_oid(oid)
    send(uid, wait_text_for_kind(kind, title),
         markup([cb("🧾 Мои заказы", "myorders")], back_row()))

    # Разбор email : пароль для code-entities
    email, password = "", ""
    if ":" in acc:
        email, _, password = acc.partition(":")
        email, password = email.strip(), password.strip()
    else:
        lines = [l.strip() for l in acc.splitlines() if l.strip()]
        if len(lines) >= 2:
            email, password = lines[0], lines[1]
        else:
            email = acc

    head = f"🏎 Заказ #{oid} — {title}\nПокупатель: {name_of(uid)}\n\n"
    body = ""
    parts = []  # (char_start, char_len)
    if email:
        label = "Email: "
        start = len(head + body) + len(label)
        body += label + email + "\n"
        parts.append((start, len(email)))
    if password:
        label = "Пароль: "
        start = len(head + body) + len(label)
        body += label + password + "\n"
        parts.append((start, len(password)))
    if not email and not password:
        body = f"🔐 Аккаунт:\n{acc}\n"
    kind = order_kind_for_oid(oid)
    footer = "\n" + admin_action_hint(kind)
    full = head + body + footer
    ents = make_code_entities(full, parts) if parts else None
    send(ADMIN_ID, full, item_admin_kb(oid), entities=ents)


def screen_my_orders(uid):
    rows = db.execute("SELECT id, title, price, status FROM car_orders WHERE user_id=? "
                      "ORDER BY id DESC LIMIT 15", (uid,)).fetchall()
    if not rows:
        return ("🧾 У вас пока нет заказов.", markup([cb("🛒 Магазин", "shop")], back_row()))
    names = {"paid": "ждём ваш аккаунт 📤", "sent": "отправлено, ожидайте ⏳",
             "done": "готово ✅", "refunded": "возвращено ↩️"}
    lines, kb = ["🧾 Ваши заказы\n"], []
    for oid, title, price, st in rows:
        lines.append(f"#{oid} {title} — {price} {COIN}\n    {names.get(st, st)}")
        if st == "paid":
            kb.append([cb(f"📤 Отправить аккаунт — #{oid}", f"itemacc:{oid}", "success")])
        elif st == "sent":
            kb.append([cb(f"✏️ Изменить аккаунт — #{oid}", f"itemacc:{oid}")])
    kb.append([cb("🛒 Магазин", "shop")])
    kb.append(back_row())
    return "\n".join(lines), markup(*kb)


def admin_item_done_prompt(admin_id, oid):
    r = db.execute("SELECT title, status FROM car_orders WHERE id=?", (oid,)).fetchone()
    if not r or r[1] != "sent":
        send(admin_id, "Заказ уже обработан или ещё ждёт аккаунт.")
        return
    ADMIN_STATE[admin_id] = ("itemdone", oid)
    send(admin_id, f"✅ Заказ #{oid} — {r[0]}\n\nНапишите сообщение покупателю "
                   "(оно придёт вместе с «Заказ готов») или нажмите кнопку для стандартного текста.\n\n"
                   "/cancel — отмена",
         markup([cb("📨 Отправить стандартное", f"idonestd:{oid}", "success")],
                [cb("✖️ Отмена", "admin")]))


def finish_item_order(admin_id, oid, note=None):
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
    kind = order_kind_for_oid(oid)
    if (note or "").strip():
        icon = "💰" if kind == "money" else ("🚗" if kind == "car" else "🏎")
        msg = f"🎉 Ваш заказ готов!\n{icon} {title}\n\n{(note or '').strip()}\n\nСпасибо за покупку! ❤️"
    else:
        msg = done_text_for_kind(kind, title)
    res = send(uid, msg, markup([cb("🛒 Магазин", "shop")], back_row()))
    extra = "" if res else "\n⚠️ Но сообщение покупателю не доставлено (возможно, заблокировал бота)."
    send(admin_id, f"✅ Заказ #{oid} завершён, покупатель уведомлён.{extra}",
         markup([cb("🛒 Заказы", "a_orders")], admin_back()))


def refund_item_order(admin_id, oid):
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
    add_tx(uid, price, "item_refund", f"#{oid}")
    db.commit()
    send(uid, f"❌ Заказ #{oid} ({title}) отклонён. {price} {COIN} возвращены на баланс.\n"
              f"💰 Баланс: {balance(uid)} {COIN}",
         markup([cb("🛒 Магазин", "shop")], back_row()))
    send(admin_id, f"❌ Заказ #{oid} отклонён, SSM возвращены.",
         markup([cb("🛒 Заказы", "a_orders")], admin_back()))


# ======================= Старые машины (для совместимости) =======================
# Используем те же функции, category='car'

def screen_cars(uid):
    return screen_section(uid, "car")


# ======================= Магазин (разделы) =======================

def screen_shop(uid):
    text = f"🛒 Магазин\n{SEP}\n💰 Ваш баланс: {balance(uid)} {COIN}\n\nВыберите раздел 👇"
    sections = get_sections(active_only=True)
    kb = []
    row = []
    for row_data in sections:
        # (key, title, style, full_width[, emoji_cid])
        key, title, style, full_width = row_data[0], row_data[1], row_data[2], row_data[3]
        emoji_cid = row_data[4] if len(row_data) > 4 else None
        btn = sec_btn(title, f"sec:{key}", style or "primary", emoji_cid)
        if full_width:
            if row:
                kb.append(row)
                row = []
            kb.append([btn])
        else:
            row.append(btn)
            if len(row) >= 2:
                kb.append(row)
                row = []
    if row:
        kb.append(row)
    # URL-кнопки каналов (если заданы)
    url_row = []
    if CHANNEL_URL and "your_channel" not in CHANNEL_URL:
        url_row.append(url_btn("📢 TELEGRAM KANAL", CHANNEL_URL, "primary"))
    if REVIEWS_URL and "your_reviews" not in REVIEWS_URL:
        url_row.append(url_btn("⭐ SSM OTVIZ", REVIEWS_URL, "primary"))
    if url_row:
        kb.append(url_row)
    kb.append([cb("👤 Аккаунты", "accounts", "primary")])
    kb.append(back_row())
    return text, markup(*kb)



def screen_accounts(uid):
    rows = db.execute("SELECT id, title, price FROM products WHERE active=1 ORDER BY id").fetchall()
    kb = []
    for i, t, pr in rows:
        n = stock_count(i)
        kb.append([cb(f"{stock_icon(n)} {t} — {pr} {COIN}", f"prod:{i}", "primary")])
    kb.append(back_row("⬅️ Магазин", "shop"))
    text = (f"👤 Аккаунты\n{SEP}\n💰 Ваш баланс: {balance(uid)} {COIN}\n\nВыберите товар 👇"
            if rows else "👤 Аккаунтов пока нет.")
    return text, markup(*kb)


def screen_product(uid, pid):
    p = get_product(pid)
    if not p:
        return screen_accounts(uid)
    _, title, price = p
    photo, descr = product_extra(pid)
    n = stock_count(pid)
    bal = balance(uid)
    text = f"🛍 {title}\n{SEP}\n\n"
    if descr:
        text += f"📝 {descr}\n\n"
    text += f"💵 Цена: {price} {COIN}\n📦 В наличии: {n}\n💰 Ваш баланс: {bal} {COIN}"
    line = rating_line(pid)
    if line:
        text += "\n" + line
    kb = []
    if n == 0:
        text += "\n\n⚠️ Товар закончился."
    elif bal < price:
        text += f"\n\n⚠️ Не хватает {price - bal} {COIN}."
        kb.append([cb("💰 Пополнить баланс", "topup", "primary")])
    else:
        for q in QTY_OPTIONS:
            if q <= n and q <= MAX_QTY:
                tot = calc_total(price, q)
                kb.append([cb(f"🛒 Купить ×{q} за {tot} {COIN}", f"buy:{pid}:{q}:{tot}", "success")])
    kb.append([cb("⬅️ Аккаунты", "accounts")])
    return text, markup(*kb)


def show_product(uid, mid, pid):
    text, kb = screen_product(uid, pid)
    photo, _ = product_extra(pid)
    if photo:
        if send_photo(uid, photo, text, kb):
            delete_msg(uid, mid)
            return
    show(uid, mid, (text, kb))


def do_buy(uid, pid, qty=1, expected=None):
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
    tail = f"\n{SEP}\nСпасибо! ❤️\n📦 Все покупки всегда есть в разделе «Мои покупки»."
    items = [f"{i}. {d}" if qty > 1 else d for i, (_sid, d) in enumerate(rows, 1)]
    chunks, cur = [], head
    for it in items:
        if len(cur) + len(it) + 1 > 3700:
            chunks.append(cur)
            cur = ""
        cur += it + "\n"
    chunks.append(cur + tail)
    kb = markup([cb("📦 Мои покупки", "buys:0")], [cb("🛒 Магазин", "shop")], back_row())
    ok = None
    for i, c in enumerate(chunks):
        res = send(uid, c, kb if i == len(chunks) - 1 else None)
        if i == 0:
            ok = res
        if not ok:
            break
    if not ok:
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


def send_rating_request(uid, pid):
    p = get_product(pid)
    if not p:
        return
    send(uid, f"⭐ Оцените покупку «{p[1]}»",
         markup([cb("⭐" * i, f"rate:{pid}:{i}") for i in range(1, 6)],
                [cb("Пропустить", "menu")]))


# ======================= Меню, помощь, реф, промо =======================

def screen_menu(uid):
    text = (f"🏠 Главное меню\n{SEP}\n"
            f"💰 Баланс: {balance(uid)} {COIN}\n\n"
            "Выберите действие 👇")
    kb = [
        [cb("🛒 Магазин", "shop", "primary"), cb("💰 Пополнить", "topup", "primary")],
        [cb("📦 Мои покупки", "buys:0"), cb("🤝 Друзья и бонусы", "ref")],
        [cb("🎟 Промокод", "promo"), cb("❓ Помощь", "help")],
    ]
    if uid == ADMIN_ID:
        kb.append([cb("⚙️ Админ-панель", "admin", "primary")])
    return text, markup(*kb)


def screen_help(uid):
    text = (f"❓ Помощь\n{SEP}\n\n"
            "• Магазин — покупка товаров и аккаунтов\n"
            "• Пополнить — Stars, Crypto, Т-Банк, Душанбе Сити\n"
            "• Мои покупки — история аккаунтов\n"
            "• Друзья и бонусы — реферальная ссылка\n"
            "• Промокод — активация бонусов\n\n"
            "По вопросам оплаты: /paysupport\n"
            f"Админ: {ADMIN_ID}")
    return text, markup(back_row())


def screen_ref(uid):
    global BOT_USERNAME
    if not BOT_USERNAME:
        try:
            me = api("getMe")
            BOT_USERNAME = me.get("username", "")
        except Exception:
            pass
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}" if BOT_USERNAME else "…"
    n = invited_count(uid)
    text = (f"🤝 Друзья и бонусы\n{SEP}\n\n"
            f"Ваша ссылка:\n{link}\n\n"
            f"Приглашено: {n}\n"
            f"Вы получаете {REF_PERCENT}% {COIN} с каждого пополнения друга.\n\n"
            "Награды за количество друзей:\n")
    for need, reward in REF_MILESTONES:
        text += f"• {need} друзей → +{reward} {COIN}\n"
    return text, markup(back_row())


def screen_promo_ask():
    return ("🎟 Введите промокод одним сообщением.",
            markup([cb("✖️ Отмена", "menu")]))


PROMO_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")


def promo_alive(r):
    code, bonus, mx, used, exp, act = r
    if not act:
        return False
    if exp and time.time() > exp:
        return False
    if mx and used >= mx:
        return False
    return True


def do_promo(uid, code):
    PROMO_WAIT.discard(uid)
    code = code.strip().upper()
    if not PROMO_RE.match(code):
        send(uid, "Неверный формат промокода.", markup(back_row()))
        return
    r = db.execute("SELECT code, bonus, max_uses, used, expires, active FROM promos WHERE code=?",
                   (code,)).fetchone()
    if not r or not promo_alive(r):
        send(uid, "Промокод не найден или уже не действует.", markup(back_row()))
        return
    if db.execute("SELECT 1 FROM promo_uses WHERE user_id=? AND code=?", (uid, code)).fetchone():
        send(uid, "Вы уже использовали этот промокод.", markup(back_row()))
        return
    bonus = r[1]
    cur = db.execute("UPDATE promos SET used = used + 1 WHERE code=? AND (max_uses=0 OR used < max_uses)",
                     (code,))
    if cur.rowcount == 0:
        db.rollback()
        send(uid, "Промокод исчерпан.", markup(back_row()))
        return
    db.execute("INSERT INTO promo_uses(user_id, code, ts) VALUES(?,?,?)",
               (uid, code, int(time.time())))
    add_tx(uid, bonus, "promo", code)
    db.commit()
    send(uid, f"🎉 Промокод активирован! +{bonus} {COIN}\n💰 Баланс: {balance(uid)} {COIN}",
         markup([cb("🛒 Магазин", "shop")], back_row()))


def screen_topup(uid):
    text = (f"💰 Пополнение баланса\n{SEP}\n"
            f"Текущий баланс: {balance(uid)} {COIN}\n"
            f"Курс: 1 ⭐ = {RATE} {COIN}\n\n"
            "Выберите способ 👇")
    kb, row = [], []
    for n in TOPUP_PRESETS:
        row.append(cb(f"⭐ {n}", f"stars:{n}"))
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
        return ("📦 У вас пока нет покупок.", markup([cb("🛒 Магазин", "shop")], back_row()))
    pages = (total + PAGE - 1) // PAGE
    page = max(0, min(page, pages - 1))
    rows = db.execute(
        "SELECT p.title, s.data, s.used_at, s.price_paid FROM stock s "
        "LEFT JOIN products p ON p.id=s.product_id WHERE s.used_by=? "
        "ORDER BY s.used_at DESC, s.id DESC LIMIT ? OFFSET ?",
        (uid, PAGE, page * PAGE)).fetchall()
    lines = [f"📦 Ваши покупки ({total})   стр. {page + 1}/{pages}\n"]
    for i, (title, data, ts, paid) in enumerate(rows, page * PAGE + 1):
        lines.append(f"{i}. {title or 'Товар'} — {paid or 0} {COIN}\n{data}\n🕒 {fmt_time(ts)}\n")
    nav = []
    if page > 0:
        nav.append(cb("‹ Назад", f"buys:{page - 1}"))
    if page < pages - 1:
        nav.append(cb("Вперёд ›", f"buys:{page + 1}"))
    return "\n".join(lines), markup(nav, back_row())


# ======================= Stars =======================

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
    if cur.rowcount == 0:
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
         markup([cb("🛒 Магазин", "shop")], back_row()))
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


# ======================= Админ-панель =======================

def admin_back():
    return [cb("⬅️ Админ-панель", "admin")]


def screen_admin():
    def q(sql, default=0):
        try:
            r = db.execute(sql).fetchone()
            return r[0] if r and r[0] is not None else default
        except Exception as e:
            print("admin sql skip:", sql[:60], "->", e)
            return default

    in_stock = q("SELECT COUNT(*) FROM stock s JOIN products p ON p.id=s.product_id "
                 "WHERE s.used_by IS NULL AND p.active=1")
    crypto_sum = q("SELECT COALESCE(SUM(amount),0) FROM crypto_invoices WHERE status='paid'")
    rub_sum = q("SELECT COALESCE(SUM(amount),0) FROM rub_requests "
                "WHERE status='approved' AND COALESCE(method,'tbank')='tbank'")
    dc_sum = q("SELECT COALESCE(SUM(amount),0) FROM rub_requests "
               "WHERE status='approved' AND method='dc'")
    rub_wait = q("SELECT COUNT(*) FROM rub_requests WHERE status='pending'")
    cars_done = q("SELECT COUNT(*) FROM car_orders WHERE status='done'")
    # price может отсутствовать в очень старых БД — пробуем оба варианта
    cars_sum = q("SELECT COALESCE(SUM(price),0) FROM car_orders WHERE status='done'")
    if cars_sum == 0:
        # fallback: если колонки нет, q уже вернул 0
        pass
    cars_open = q("SELECT COUNT(*) FROM car_orders WHERE status IN ('paid','sent')")
    cars_wait = q("SELECT COUNT(*) FROM car_orders WHERE status='sent'")
    users_n = q("SELECT COUNT(*) FROM users")
    bal_sum = q("SELECT COALESCE(SUM(balance),0) FROM users")
    stars_sum = q("SELECT COALESCE(SUM(stars),0) FROM payments WHERE refunded=0")
    sales_n = q("SELECT COUNT(*) FROM stock WHERE used_by IS NOT NULL")
    sales_sum = q("SELECT COALESCE(SUM(price_paid),0) FROM stock WHERE used_by IS NOT NULL")
    refs_n = q("SELECT COUNT(*) FROM users WHERE referrer IS NOT NULL")
    promo_n = q("SELECT COUNT(*) FROM promo_uses")

    text = ("⚙️ Админ-панель\n\n"
            f"👥 Пользователей: {users_n}\n"
            f"💰 Сумма балансов: {bal_sum} {COIN}\n"
            f"⭐ Получено Stars: {stars_sum}\n"
            f"🛍 Продаж: {sales_n} на {sales_sum} {COIN}\n"
            f"🤝 Рефералов: {refs_n}\n"
            f"💎 Crypto получено: {crypto_sum:g} {CRYPTO_ASSET}\n"
            f"🏦 {TBANK_NAME} получено: {rub_sum} ₽\n"
            f"🏙 {DC_NAME} получено: {dc_sum} сомони\n"
            f"⏳ Заявок на проверке: {rub_wait}\n"
            f"🏎 Товаров продано: {cars_done} на {cars_sum} {COIN} (в работе: {cars_open})\n"
            f"🎟 Активаций промокодов: {promo_n}\n"
            f"📦 В складе: {in_stock}")
    kb = markup(
        [cb("🛒 Разделы магазина" + (f" ({cars_wait})" if cars_wait else ""), "a_sections")],
        [cb("📦 Товары и склад (аккаунты)", "a_prods")],
        [cb("👥 Пользователи", "a_users"), cb("💳 Платежи", "a_pay")],
        [cb("📤 Продажи", "a_sales"), cb("🔎 Пользователь", "a_user")],
        [cb("💰 Изменить баланс", "a_bal"), cb("✨ Премиум-эмодзи", "a_emoji")],
        [cb("🎟 Промокоды", "a_promos"), cb("📢 Рассылка", "a_bc")],
        [cb("🏦 Заявки на оплату" + (f" ({rub_wait})" if rub_wait else ""), "a_rub")],
        [cb("🛒 Заказы в работе" + (f" ({cars_wait})" if cars_wait else ""), "a_orders")],
        [cb("📋 Команды бота", "a_cmds")],
        back_row())
    return text, kb



def get_bot_commands():
    """Список команд из Telegram API: [{command, description}, ...]"""
    try:
        return api("getMyCommands") or []
    except Exception as e:
        print("getMyCommands error:", e)
        return []


def set_bot_commands(cmds):
    """cmds = list of {command, description}. Возвращает True/False."""
    try:
        api("setMyCommands", commands=cmds)
        return True
    except Exception as e:
        print("setMyCommands error:", e)
        return False


def screen_acmds(note=""):
    cmds = get_bot_commands()
    lines = [note + "📋 Команды бота (меню Telegram)\n" + SEP + "\n"]
    if cmds:
        for c in cmds:
            lines.append(f"/{c.get('command', '?')} — {c.get('description', '')}")
    else:
        lines.append("Пока команд нет (или Telegram ещё не обновил список).")
    lines.append("\nНажми на команду, чтобы удалить. Или добавь новую.")
    kb = []
    for c in cmds:
        name = c.get("command", "")
        if name:
            kb.append([cb(f"🗑 /{name}", f"a_cmddel:{name}", "danger")])
    kb.append([cb("➕ Добавить команду", "a_cmdadd", "success")])
    kb.append([cb("🔄 Обновить список", "a_cmds")])
    kb.append([cb("🧹 Удалить ВСЕ команды", "a_cmdclear", "danger")])
    kb.append(admin_back())
    return "\n".join(lines), markup(*kb)



def screen_asections():
    rows = db.execute(
        "SELECT key, title, style, full_width, active, sort_order FROM sections ORDER BY sort_order, key"
    ).fetchall()
    kb = []
    for key, title, style, fw, act, so in rows:
        mark = "🟢" if act else "🔴"
        w = " [wide]" if fw else ""
        n = db.execute("SELECT COUNT(*) FROM cars WHERE active=1 AND category=?", (key,)).fetchone()[0]
        kb.append([cb(f"{mark} {title} ({n}){w}", f"a_secm:{key}")])
    kb.append([cb("➕ Новый раздел-кнопка", "a_secadd", "success")])
    kb.append(admin_back())
    text = ("🛒 Разделы магазина (кнопки)\n\n"
            "Нажми на раздел, чтобы изменить или удалить.\n"
            "🟢 = виден в магазине, 🔴 = скрыт.")
    if not rows:
        text += "\n\nПока разделов нет — добавь первый 👇"
    return text, markup(*kb)


def screen_asecm(key, note=""):
    r = db.execute(
        "SELECT key, title, style, full_width, active, sort_order, emoji_cid FROM sections WHERE key=?",
        (key,)
    ).fetchone()
    if not r:
        # fallback without emoji_cid
        r = db.execute(
            "SELECT key, title, style, full_width, active, sort_order FROM sections WHERE key=?",
            (key,)
        ).fetchone()
        if not r:
            return screen_asections()
        key, title, style, fw, act, so = r
        emoji_cid = None
    else:
        key, title, style, fw, act, so, emoji_cid = r
    n = db.execute("SELECT COUNT(*) FROM cars WHERE active=1 AND category=?", (key,)).fetchone()[0]
    emoji_line = f"✨ Премиум-эмодзи: {'установлен ✅' if emoji_cid else 'нет'}"
    text = (f"{note}📂 {title}\n\n"
            f"Ключ: `{key}`\n"
            f"Стиль: {style or '—'}\n"
            f"Ширина: {'на всю строку' if fw else 'обычная (2 в ряд)'}\n"
            f"Статус: {'🟢 виден' if act else '🔴 скрыт'}\n"
            f"Порядок: {so}\n"
            f"{emoji_line}\n"
            f"Товаров: {n}")
    kb = markup(
        [cb("✏️ Название", f"a_sectitle:{key}"), cb("🎨 Стиль", f"a_secstyle:{key}")],
        [cb("✨ Премиум-эмодзи", f"a_secemoji:{key}"),
         cb("🗑 Убрать эмодзи", f"a_secemojidel:{key}", "danger")] if emoji_cid else
        [cb("✨ Премиум-эмодзи", f"a_secemoji:{key}")],
        [cb("↔️ На всю ширину" if not fw else "↕️ Обычная ширина", f"a_secwidth:{key}")],
        [cb("🔴 Скрыть" if act else "🟢 Показать", f"a_sectog:{key}")],
        [cb("⬆️ Выше", f"a_secup:{key}"), cb("⬇️ Ниже", f"a_secdn:{key}")],
        [cb("📦 Товары раздела", f"a_sec:{key}")],
        [cb("❌ Удалить раздел", f"a_secrm:{key}", "danger")],
        [cb("⬅️ Разделы", "a_sections")])
    return text, kb



def screen_asec(cat):
    rows = cars_by_category(cat)
    title = section_title(cat)
    kb = [[cb(f"{t} — {pr} {COIN}", f"a_item:{i}")] for i, t, pr in rows]
    kb.append([cb("➕ Добавить", f"a_additem:{cat}", "success")])
    kb.append([cb("⬅️ Разделы", "a_sections")])
    text = f"{title}\n\nТовары раздела:" if rows else f"{title}\n\nПока пусто. Добавьте первый товар 👇"
    return text, markup(*kb)


def screen_aitem(cid, note=""):
    c = car_get(cid)
    if not c:
        return screen_asections()
    _, title, price, photo, descr, cat = c
    short = (descr[:80] + "…") if descr and len(descr) > 80 else (descr or "нет")
    text = (f"{note}🏎 {title}\n\n💵 Цена: {price} {COIN}\n"
            f"📂 Раздел: {section_title(cat)}\n"
            f"🖼 Фото: {'есть ✅' if photo else 'нет'}\n📝 Описание: {short}")
    kb = markup(
        [cb("🖼 Фото", f"a_itemphoto:{cid}"), cb("📝 Описание", f"a_itemdesc:{cid}")],
        [cb("🗑 Убрать фото", f"a_itemnophoto:{cid}")] if photo else [],
        [cb("👁 Как видит покупатель", f"a_itemview:{cid}")],
        [cb("✏️ Изменить цену", f"a_itemprice:{cid}"), cb("✏️ Название", f"a_itemtitle:{cid}")],
        [cb("❌ Удалить товар", f"a_itemrm:{cid}", "danger")],
        [cb("⬅️ К разделу", f"a_sec:{cat}")])
    return text, kb


def screen_aorders():
    rows = db.execute("SELECT id, user_id, title, price, status FROM car_orders "
                      "WHERE status IN ('paid','sent') ORDER BY id").fetchall()
    kb = []
    for oid, u, t, pr, st in rows[:40]:
        mark = "📤" if st == "paid" else "⏳"
        kb.append([cb(f"{mark} #{oid} {t[:20]} — {pr} {COIN} — {name_of(u)[:20]}", f"a_ord:{oid}")])
    kb.append(admin_back())
    text = (f"🛒 Заказы в работе: {len(rows)}\n\nНажмите на заказ."
            if rows else "🛒 Заказов в работе нет.")
    return text, markup(*kb)


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
    text = "📦 Товары и склад (аккаунты)\n\nНажми на товар, чтобы управлять им." if rows else \
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
        try:
            text, kb = screen_admin()
            # Always send fresh message — edit often fails after photo messages
            send(uid, text, kb)
            if mid:
                try:
                    delete_msg(uid, mid)
                except Exception:
                    pass
        except Exception as e:
            print("screen_admin error:", e)
            send(uid, f"⚠️ Ошибка админ-панели: {e}")
    elif data == "a_rub":
        show(uid, mid, screen_arub())
    elif data == "a_cmds":
        ADMIN_STATE.pop(uid, None)
        show(uid, mid, screen_acmds())
    elif data == "a_cmdadd":
        ask_admin(uid, mid, ("newcmd",),
                  "➕ Новая команда.\nОтправь одним сообщением:\n"
                  "команда | описание\n\n"
                  "Пример:\n"
                  "shop | Открыть магазин\n"
                  "balance | Показать баланс\n\n"
                  "• команда — латиница, 1–32 символа, без /\n"
                  "• описание — до 256 символов")
    elif data.startswith("a_cmddel:"):
        name = data.split(":", 1)[1].strip().lstrip("/")
        cmds = [c for c in get_bot_commands() if c.get("command") != name]
        if set_bot_commands(cmds):
            show(uid, mid, screen_acmds(f"✅ Команда /{name} удалена.\n\n"))
        else:
            show(uid, mid, screen_acmds("⚠️ Не удалось удалить команду.\n\n"))
    elif data == "a_cmdclear":
        edit(uid, mid, "Удалить ВСЕ команды бота из меню Telegram?",
             markup([cb("🧹 Да, удалить все", "a_cmdcleary", "danger"),
                     cb("✖️ Отмена", "a_cmds")]))
    elif data == "a_cmdcleary":
        if set_bot_commands([]):
            show(uid, mid, screen_acmds("✅ Все команды удалены.\n\n"))
        else:
            show(uid, mid, screen_acmds("⚠️ Не удалось очистить команды.\n\n"))
    elif data == "a_sections":
        ADMIN_STATE.pop(uid, None)
        show(uid, mid, screen_asections())
    elif data == "a_secadd":
        ask_admin(uid, mid, ("newsec",),
                  "➕ Новый раздел (кнопка в магазине).\n"
                  "Отправь одним сообщением:\n"
                  "ключ | название | стиль\n\n"
                  "• ключ — латиница, без пробелов (например: sliiv, money)\n"
                  "• название — текст кнопки, можно с эмодзи\n"
                  "• стиль — primary / success / danger (необязательно)\n\n"
                  "Пример:\n"
                  "sliiv | 💀 СЛИВ АККАУНТ | primary\n"
                  "vip | 👑 VIP | success")
    elif data.startswith("a_secm:"):
        show(uid, mid, screen_asecm(data.split(":", 1)[1]))
    elif data.startswith("a_sectitle:"):
        key = data.split(":", 1)[1]
        ask_admin(uid, mid, ("sectitle", key), "✏️ Отправь новое название кнопки (с эмодзи можно).")
    elif data.startswith("a_secemoji:"):
        key = data.split(":", 1)[1]
        ask_admin(uid, mid, ("secemoji", key),
                  "✨ Отправь сообщение с ОДНИМ премиум-эмодзи "
                  "(из любого набора Telegram Premium).\n\n"
                  "Он станет иконкой кнопки этого раздела в магазине.\n"
                  "Можно просто вставить премиум-эмодзи и отправить.")
    elif data.startswith("a_secemojidel:"):
        key = data.split(":", 1)[1]
        try:
            db.execute("UPDATE sections SET emoji_cid=NULL WHERE key=?", (key,))
            db.commit()
        except Exception as e:
            print("emoji del error:", e)
        show(uid, mid, screen_asecm(key, "🗑 Премиум-эмодзи убран.\n\n"))
    elif data.startswith("a_secstyle:"):
        key = data.split(":", 1)[1]
        edit(uid, mid, "🎨 Выбери стиль кнопки:",
             markup([cb("primary (синий)", f"a_secstset:{key}:primary", "primary"),
                     cb("success (зелёный)", f"a_secstset:{key}:success", "success"),
                     cb("danger (красный)", f"a_secstset:{key}:danger", "danger"),
                     cb("без стиля", f"a_secstset:{key}:")],
                    [cb("⬅️ Назад", f"a_secm:{key}")]))
    elif data.startswith("a_secstset:"):
        parts = data.split(":")
        key = parts[1]
        style = parts[2] if len(parts) > 2 else ""
        db.execute("UPDATE sections SET style=? WHERE key=?", (style or None, key))
        db.commit()
        show(uid, mid, screen_asecm(key, "✅ Стиль обновлён.\n\n"))
    elif data.startswith("a_secwidth:"):
        key = data.split(":", 1)[1]
        db.execute("UPDATE sections SET full_width = 1 - COALESCE(full_width,0) WHERE key=?", (key,))
        db.commit()
        show(uid, mid, screen_asecm(key, "✅ Ширина изменена.\n\n"))
    elif data.startswith("a_sectog:"):
        key = data.split(":", 1)[1]
        db.execute("UPDATE sections SET active = 1 - COALESCE(active,0) WHERE key=?", (key,))
        db.commit()
        show(uid, mid, screen_asecm(key, "✅ Статус изменён.\n\n"))
    elif data.startswith("a_secup:") or data.startswith("a_secdn:"):
        key = data.split(":", 1)[1]
        delta = -15 if data.startswith("a_secup:") else 15
        db.execute("UPDATE sections SET sort_order = COALESCE(sort_order,0) + ? WHERE key=?", (delta, key))
        db.commit()
        # normalize order
        rows = db.execute("SELECT key FROM sections ORDER BY sort_order, key").fetchall()
        for i, (k,) in enumerate(rows):
            db.execute("UPDATE sections SET sort_order=? WHERE key=?", (i * 10, k))
        db.commit()
        show(uid, mid, screen_asections())
    elif data.startswith("a_secrmy:"):
        key = data.split(":", 1)[1]
        db.execute("DELETE FROM sections WHERE key=?", (key,))
        db.commit()
        show(uid, mid, screen_asections())
    elif data.startswith("a_secrm:"):
        key = data.split(":", 1)[1]
        edit(uid, mid,
             f"Удалить раздел «{section_title(key)}»?\n"
             "Товары в нём останутся в БД, но кнопка пропадёт из магазина.",
             markup([cb("❌ Да, удалить", f"a_secrmy:{key}", "danger"),
                     cb("✖️ Отмена", f"a_secm:{key}")]))
    elif data.startswith("a_sec:"):
        show(uid, mid, screen_asec(data.split(":", 1)[1]))
    elif data.startswith("a_additem:"):
        cat = data.split(":", 1)[1]
        ask_admin(uid, mid, ("newitem", cat),
                  f"➕ Новый товар в «{section_title(cat)}».\nОтправь одним сообщением:\n"
                  "Название | цена\n\nНапример:\nBMW M5 | 100")
    elif data.startswith("a_item:"):
        show(uid, mid, screen_aitem(int(data.split(":")[1])))
    elif data.startswith("a_itemphoto:"):
        ask_admin(uid, mid, ("item_photo", int(data.split(":")[1])),
                  "🖼 Отправь фото товара.\nЕсли напишешь подпись к фото, она станет описанием.")
    elif data.startswith("a_itemnophoto:"):
        cid = int(data.split(":")[1])
        db.execute("UPDATE cars SET photo=NULL WHERE id=?", (cid,))
        db.commit()
        show(uid, mid, screen_aitem(cid, "🗑 Фото убрано.\n\n"))
    elif data.startswith("a_itemdesc:"):
        ask_admin(uid, mid, ("item_desc", int(data.split(":")[1])),
                  "📝 Отправь описание (до 700 символов).\nЧтобы убрать, отправь «-»")
    elif data.startswith("a_itemprice:"):
        ask_admin(uid, mid, ("item_price", int(data.split(":")[1])),
                  f"✏️ Отправь новую цену числом (в {COIN}).")
    elif data.startswith("a_itemtitle:"):
        ask_admin(uid, mid, ("item_title", int(data.split(":")[1])), "✏️ Отправь новое название.")
    elif data.startswith("a_itemview:"):
        show_item(uid, None, int(data.split(":")[1]))
    elif data.startswith("a_itemrmy:"):
        cid = int(data.split(":")[1])
        cat = db.execute("SELECT category FROM cars WHERE id=?", (cid,)).fetchone()
        cat = cat[0] if cat else "car"
        db.execute("UPDATE cars SET active=0 WHERE id=?", (cid,))
        db.commit()
        show(uid, mid, screen_asec(cat))
    elif data.startswith("a_itemrm:"):
        cid = int(data.split(":")[1])
        edit(uid, mid, "Удалить товар? Он пропадёт из магазина (история заказов сохранится).",
             markup([cb("❌ Да, удалить", f"a_itemrmy:{cid}", "danger"),
                     cb("✖️ Отмена", f"a_item:{cid}")]))
    elif data == "a_orders":
        show(uid, mid, screen_aorders())
    elif data.startswith("a_ord:"):
        oid = int(data.split(":")[1])
        r = db.execute("SELECT user_id, title, price, status, account FROM car_orders WHERE id=?",
                       (oid,)).fetchone()
        if not r:
            send(uid, "Заказ не найден.")
            return
        u, t, pr, st, acc = r
        text = (f"Заказ #{oid}\n{t} — {pr} {COIN}\nСтатус: {st}\n"
                f"Покупатель: {name_of(u)}\n\nАккаунт:\n{acc or '—'}")
        kb = []
        if st == "sent":
            kb.append([cb("✅ Готово", f"idone:{oid}", "success"),
                       cb("❌ Отклонить", f"ino:{oid}", "danger")])
        elif st == "paid":
            kb.append([cb("❌ Отклонить", f"ino:{oid}", "danger")])
        kb.append([cb("⬅️ Заказы", "a_orders")])
        show(uid, mid, (text, markup(*kb)))
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
                  "📝 Отправь описание аккаунта (до 700 символов).\n"
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
    if kind == "newsec":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) < 2:
            ADMIN_STATE[uid] = state
            send(uid, "Формат: ключ | название | стиль\nПример: sliiv | 💀 СЛИВ АККАУНТ | primary")
            return
        key = parts[0].lower().lstrip("/")
        title = parts[1]
        style = parts[2] if len(parts) > 2 and parts[2] else "primary"
        if style not in ("primary", "success", "danger", ""):
            style = "primary"
        if not re.match(r"^[a-z0-9_]{1,32}$", key):
            ADMIN_STATE[uid] = state
            send(uid, "Ключ: только латиница, цифры и _, 1–32 символа.")
            return
        if not title:
            ADMIN_STATE[uid] = state
            send(uid, "Название не может быть пустым.")
            return
        if db.execute("SELECT 1 FROM sections WHERE key=?", (key,)).fetchone():
            ADMIN_STATE[uid] = state
            send(uid, "Такой ключ уже есть. Выбери другой.")
            return
        mx = db.execute("SELECT COALESCE(MAX(sort_order),0) FROM sections").fetchone()[0]
        db.execute(
            "INSERT INTO sections(key, title, style, full_width, sort_order, active) VALUES(?,?,?,0,?,1)",
            (key, title[:60], style or None, mx + 10))
        db.commit()
        send(uid, f"✅ Раздел создан: {title}\nКлюч: {key}\nТеперь можно добавить товары.",
             markup([cb("📦 Товары раздела", f"a_sec:{key}")],
                    [cb("📂 К разделу", f"a_secm:{key}")],
                    [cb("⬅️ Все разделы", "a_sections")]))
    elif kind == "secemoji":
        # text path — if no custom emoji entities, remind
        ADMIN_STATE[uid] = state
        send(uid, "Нужен именно премиум-эмодзи (custom emoji). "
                  "Отправь сообщение, где есть премиум-эмодзи из Premium-набора.\n"
                  "Или /cancel")
    elif kind == "sectitle":
        key = state[1]
        title = text.strip()[:60]
        if not title:
            ADMIN_STATE[uid] = state
            send(uid, "Название не может быть пустым.")
            return
        db.execute("UPDATE sections SET title=? WHERE key=?", (title, key))
        db.commit()
        send(uid, f"✅ Название обновлено: {title}",
             markup([cb("📂 К разделу", f"a_secm:{key}")], [cb("⬅️ Разделы", "a_sections")]))
    elif kind == "newcmd":
        if "|" not in text:
            ADMIN_STATE[uid] = state
            send(uid, "Формат: команда | описание\nНапример: shop | Открыть магазин")
            return
        cmd, _, desc = text.partition("|")
        cmd, desc = cmd.strip().lstrip("/").lower(), desc.strip()
        if not re.match(r"^[a-z0-9_]{1,32}$", cmd):
            ADMIN_STATE[uid] = state
            send(uid, "Команда: только латиница, цифры и _, 1–32 символа. Без пробелов и /.")
            return
        if not desc or len(desc) > 256:
            ADMIN_STATE[uid] = state
            send(uid, "Описание обязательно, до 256 символов.")
            return
        cmds = get_bot_commands()
        # заменить если уже есть
        cmds = [c for c in cmds if c.get("command") != cmd]
        cmds.append({"command": cmd, "description": desc})
        if set_bot_commands(cmds):
            send(uid, f"✅ Команда добавлена: /{cmd}\n{desc}",
                 markup([cb("📋 Команды", "a_cmds")], admin_back()))
        else:
            send(uid, "⚠️ Telegram не принял команду. Проверьте формат.",
                 markup([cb("📋 Команды", "a_cmds")], admin_back()))
    elif kind == "itemdone":
        finish_item_order(uid, state[1], text)
    elif kind == "newitem":
        cat = state[1]
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
        cur = db.execute("INSERT INTO cars(title, price, category) VALUES(?,?,?)",
                         (title[:60], int(price), cat))
        db.commit()
        cid = cur.lastrowid
        send(uid, f"✅ Товар создан: {title} — {price} {COIN}\nМожно добавить фото и описание 👇",
             markup([cb("🖼 Фото", f"a_itemphoto:{cid}"), cb("📝 Описание", f"a_itemdesc:{cid}")],
                    [cb("🏎 К товару", f"a_item:{cid}")],
                    [cb("⬅️ К разделу", f"a_sec:{cat}")]))
    elif kind == "item_price":
        if not text.strip().isdigit() or int(text) <= 0:
            ADMIN_STATE[uid] = state
            send(uid, "Нужно положительное число. Попробуй ещё раз.")
            return
        db.execute("UPDATE cars SET price=? WHERE id=?", (int(text), state[1]))
        db.commit()
        send(uid, f"✅ Цена обновлена: {int(text)} {COIN}",
             markup([cb("🏎 К товару", f"a_item:{state[1]}")]))
    elif kind == "item_title":
        db.execute("UPDATE cars SET title=? WHERE id=?", (text.strip()[:60], state[1]))
        db.commit()
        send(uid, "✅ Название обновлено.", markup([cb("🏎 К товару", f"a_item:{state[1]}")]))
    elif kind == "item_desc":
        d = text.strip()
        db.execute("UPDATE cars SET descr=? WHERE id=?", (None if d == "-" else d[:700], state[1]))
        db.commit()
        send(uid, "🗑 Описание убрано." if d == "-" else "✅ Описание сохранено.",
             markup([cb("👁 Как видит покупатель", f"a_itemview:{state[1]}")],
                    [cb("🏎 К товару", f"a_item:{state[1]}")]))
    elif kind == "item_photo":
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
        send(uid, f"✅ Добавлено: {len(lines)}\n📦 Всего в складе: {stock_count(pid)}",
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


# ======================= Премиум-эмодзи =======================

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

def handle_callback(uid, mid, data):
    if data == "menu":
        show(uid, mid, screen_menu(uid))
    elif data == "shop":
        show(uid, mid, screen_shop(uid))
    elif data == "topup":
        show(uid, mid, screen_topup(uid))
    elif data == "help":
        show(uid, mid, screen_help(uid))
    elif data == "ref":
        show(uid, mid, screen_ref(uid))
    elif data == "promo":
        PROMO_WAIT.add(uid)
        show(uid, mid, screen_promo_ask())
    elif data.startswith("buys:"):
        show(uid, mid, screen_buys(uid, int(data.split(":")[1])))
    elif data == "accounts":
        show(uid, mid, screen_accounts(uid))
    elif data.startswith("prod:"):
        show_product(uid, mid, int(data.split(":")[1]))
    elif data.startswith("buy:"):
        parts = data.split(":")
        pid, qty, expected = int(parts[1]), int(parts[2]), int(parts[3])
        res, val = do_buy(uid, pid, qty, expected)
        if res == "ok":
            delete_msg(uid, mid)
        elif res == "nobal":
            edit(uid, mid, f"⚠️ Не хватает {val} {COIN}.",
                 markup([cb("💰 Пополнить", "topup", "primary")], [cb("⬅️ Назад", f"prod:{pid}")]))
        elif res == "empty":
            edit(uid, mid, f"⚠️ Недостаточно товара (доступно {val}).",
                 markup([cb("⬅️ Назад", f"prod:{pid}")]))
        elif res == "changed":
            edit(uid, mid, "Цена изменилась. Обновите страницу.",
                 markup([cb("🔄 Обновить", f"prod:{pid}")]))
        else:
            show(uid, mid, screen_accounts(uid))
    elif data.startswith("sec:"):
        show(uid, mid, screen_section(uid, data.split(":", 1)[1]))
    elif data.startswith("item:"):
        show_item(uid, mid, int(data.split(":")[1]))
    elif data.startswith("itembuy:"):
        show(uid, mid, screen_item_confirm(uid, int(data.split(":")[1])))
    elif data.startswith("itemok:"):
        cid = int(data.split(":")[1])
        res, val = do_buy_item(uid, cid)
        if res == "ok":
            delete_msg(uid, mid)
        elif res == "nobal":
            edit(uid, mid, f"⚠️ Не хватает {val} {COIN}.",
                 markup([cb("💰 Пополнить", "topup", "primary")], [cb("⬅️ Назад", f"item:{cid}")]))
        elif res == "gone":
            show(uid, mid, screen_shop(uid))
        else:
            show(uid, mid, screen_shop(uid))
    elif data.startswith("itemacc:"):
        ask_item_account(uid, mid, int(data.split(":")[1]))
    elif data == "myorders":
        show(uid, mid, screen_my_orders(uid))
    elif data.startswith("idone:"):
        if uid == ADMIN_ID:
            admin_item_done_prompt(uid, int(data.split(":")[1]))
    elif data.startswith("idonestd:"):
        if uid == ADMIN_ID:
            finish_item_order(uid, int(data.split(":")[1]))
    elif data.startswith("ino:"):
        if uid == ADMIN_ID:
            refund_item_order(uid, int(data.split(":")[1]))
    # Stars / Crypto / Rub
    elif data.startswith("stars:"):
        send_invoice(uid, int(data.split(":")[1]))
    elif data == "topup_custom":
        TOPUP_WAIT.add(uid)
        edit(uid, mid, f"✏️ Введите сумму в ⭐ (1–{MAX_TOPUP}):",
             markup([cb("✖️ Отмена", "topup")]))
    elif data == "ctopup":
        show(uid, mid, screen_ctopup(uid))
    elif data == "ctopup_custom":
        CTOPUP_WAIT.add(uid)
        edit(uid, mid, f"✏️ Введите сумму в {CRYPTO_ASSET} ({fmt_amount(CRYPTO_MIN)}–{CRYPTO_MAX}):",
             markup([cb("✖️ Отмена", "ctopup")]))
    elif data.startswith("cpay:"):
        start_crypto_payment(uid, mid, float(data.split(":")[1]))
    elif data.startswith("ccheck:"):
        check_crypto_payment(uid, mid, int(data.split(":")[1]))
    elif data == "rub":
        show(uid, mid, screen_rub(uid, "tbank"))
    elif data == "dc":
        show(uid, mid, screen_rub(uid, "dc"))
    elif data == "rub_custom" or data == "dc_custom":
        method = "dc" if data.startswith("dc") else "tbank"
        wait = DC_WAIT if method == "dc" else RUB_WAIT
        wait.add(uid)
        c = method_cfg(method)
        edit(uid, mid, f"✏️ Введите сумму в {c['unit']} ({c['min']}–{c['max']}):",
             markup([cb("✖️ Отмена", c["pre"])]))
    elif data.startswith("rubpay:") or data.startswith("dcpay:"):
        method = "dc" if data.startswith("dc") else "tbank"
        start_rub_request(uid, mid, int(data.split(":")[1]), method)
    elif data.startswith("rubcancel:"):
        rid = int(data.split(":")[1])
        db.execute("UPDATE rub_requests SET status='cancelled' WHERE id=? AND user_id=? AND status='new'",
                   (rid, uid))
        db.commit()
        show(uid, mid, screen_topup(uid))
    elif data.startswith("rubok:"):
        if uid == ADMIN_ID:
            approve_rub(uid, int(data.split(":")[1]))
    elif data.startswith("rubno:"):
        if uid == ADMIN_ID:
            reject_rub(uid, int(data.split(":")[1]))
    elif data.startswith("rubv:"):
        rid = int(data.split(":")[1])
        r = db.execute("SELECT user_id, amount, coins, file_id, method FROM rub_requests WHERE id=?",
                       (rid,)).fetchone()
        if r and r[3]:
            send_proof(uid, r[3], rub_caption(rid, r[0], r[1], r[2], r[4]), rub_admin_kb(rid))
        else:
            send(uid, "Чек не найден.")
    elif data.startswith("rate:"):
        _, pid, stars = data.split(":")
        db.execute("INSERT OR REPLACE INTO ratings(user_id, product_id, stars, ts) VALUES(?,?,?,?)",
                   (uid, int(pid), int(stars), int(time.time())))
        db.commit()
        edit(uid, mid, f"Спасибо за оценку {'⭐' * int(stars)}!", markup(back_row()))
    # Admin
    elif data == "admin" or data.startswith("a_"):
        if uid == ADMIN_ID:
            handle_admin_cb(uid, mid, data)
        else:
            edit(uid, mid, "⛔ Доступ только для администратора.", markup(back_row()))
    elif uid == ADMIN_ID:
        handle_admin_cb(uid, mid, data)


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

    if text.startswith("/myid") or text.startswith("/id"):
        send(uid, f"Ваш Telegram ID: `{uid}`\nADMIN_ID в боте: `{ADMIN_ID}`\nСовпадает: {'✅ да' if uid == ADMIN_ID else '❌ нет'}")
        return

    if text.startswith("/admin"):
        print(f"/admin from uid={uid} ADMIN_ID={ADMIN_ID} match={uid == ADMIN_ID}")
        if uid == ADMIN_ID:
            try:
                t, kb = screen_admin()
                send(uid, t, kb)
            except Exception as e:
                print("screen_admin error:", e)
                send(uid, f"⚠️ Ошибка: {e}")
        else:
            send(uid, f"⛔ Доступ запрещён.\nВаш ID: {uid}\nНужен ADMIN_ID: {ADMIN_ID}\n\nОтправьте /myid и пришлите свой ID.")
        return

    if text.startswith("/balance"):
        t, kb = screen_menu(uid)
        send(uid, t, kb)
        return

    if (text.split() or [""])[0].split("@")[0] == "/promo":
        parts = text.split(maxsplit=1)
        if len(parts) > 1:
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

    if text.startswith("/refund") and uid == ADMIN_ID:
        parts = text.split(maxsplit=1)
        handle_refund(uid, parts[1] if len(parts) > 1 else "")
        return

    if text.strip() == "/cancel" and uid == ADMIN_ID:
        ADMIN_STATE.pop(uid, None)
        send(uid, "Отменено.", markup(admin_back()))
        return

    if text.startswith("/emoji") and uid == ADMIN_ID:
        handle_emoji_cmd(msg)
        return

    if uid in CAR_WAIT and text and not text.startswith("/"):
        handle_item_account(uid, text, msg.get("message_id"))
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

        if msg.get("photo") and st and st[0] == "item_photo":
            ADMIN_STATE.pop(uid, None)
            fid = msg["photo"][-1]["file_id"]
            db.execute("UPDATE cars SET photo=? WHERE id=?", (fid, st[1]))
            cap = (msg.get("caption") or "").strip()
            if cap:
                db.execute("UPDATE cars SET descr=? WHERE id=?", (cap[:700], st[1]))
            db.commit()
            send(uid, "✅ Фото сохранено" + (" и описание из подписи." if cap else "."),
                 markup([cb("👁 Как видит покупатель", f"a_itemview:{st[1]}")],
                        [cb("🏎 К товару", f"a_item:{st[1]}")]))
            return

        # Премиум-эмодзи для раздела магазина
        if st and st[0] == "secemoji":
            ents = [e for e in (msg.get("entities") or []) + (msg.get("caption_entities") or [])
                    if e.get("type") == "custom_emoji"]
            if ents:
                cid = ents[0]["custom_emoji_id"]
                key = st[1]
                ADMIN_STATE.pop(uid, None)
                try:
                    db.execute("UPDATE sections SET emoji_cid=? WHERE key=?", (str(cid), key))
                    db.commit()
                    send(uid, f"✅ Премиум-эмодзи сохранён для раздела «{section_title(key)}».\n"
                              "Открой магазин и проверь кнопку.",
                         markup([cb("📂 К разделу", f"a_secm:{key}")],
                                [cb("🛒 Магазин", "shop")], admin_back()))
                except Exception as e:
                    send(uid, f"⚠️ Ошибка сохранения: {e}", markup(admin_back()))
                return
            # no custom emoji in message — fall through to state handler reminder

        if text and not text.startswith("/") and st:
            handle_admin_state(uid, text)
            return


def process_update(upd):
    try:
        if "callback_query" in upd:
            cq = upd["callback_query"]
            uid = cq["from"]["id"]
            mid = cq["message"]["message_id"] if cq.get("message") else None
            data = cq.get("data", "")
            try:
                api("answerCallbackQuery", callback_query_id=cq["id"])
            except Exception:
                pass
            handle_callback(uid, mid, data)
        elif "message" in upd:
            handle_message(upd["message"])
        elif "pre_checkout_query" in upd:
            pq = upd["pre_checkout_query"]
            try:
                api("answerPreCheckoutQuery", pre_checkout_query_id=pq["id"], ok=True)
            except Exception as e:
                print("pre_checkout error:", e)
    except Exception as e:
        import traceback
        print("process_update error:", e)
        traceback.print_exc()


def main():
    if not BOT_TOKEN:
        print("ERROR: задайте BOT_TOKEN в переменных окружения")
        return
    load_emoji()
    print(f"Bot started... ADMIN_ID={ADMIN_ID}")
    offset = 0
    while True:
        try:
            updates = api("getUpdates", offset=offset, timeout=30)
            for u in updates:
                offset = u["update_id"] + 1
                process_update(u)
            global LAST_CRYPTO_SYNC
            if crypto_enabled() and time.time() - LAST_CRYPTO_SYNC > CRYPTO_SYNC_EVERY:
                LAST_CRYPTO_SYNC = time.time()
                try:
                    crypto_sync()
                except Exception as e:
                    print("crypto_sync:", e)
        except Exception as e:
            print("main loop error:", e)
            time.sleep(3)


if __name__ == "__main__":
    main()
