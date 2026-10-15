import os
import sqlite3
import threading
from flask import Flask
import telebot
from telebot import types

# --- কনফিগারেশন ---
BOT_TOKEN = "8893588513:AAEopQIxE75DKqna_JRrQUMDSBf1RepOg3U"
ADMIN_ID = "7103959220"  # আপনার আপডেট করা টেলিগ্রাম আইডি

bot = telebot.TeleBot(BOT_TOKEN)

# ফ্লাস্ক ওয়েব সার্ভার (Render ২৪ ঘণ্টা সচল রাখার জন্য)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running healthy & live!"

def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()

# --- ডেটাবেজ সেটআপ (SQLite) ---
DB_NAME = "earning_bot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    username TEXT,
                    balance REAL DEFAULT 0.0,
                    referred_by INTEGER DEFAULT 0,
                    total_refers INTEGER DEFAULT 0,
                    wallet TEXT DEFAULT 'Not Set',
                    is_banned INTEGER DEFAULT 0
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS withdraws (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount REAL,
                    method TEXT,
                    wallet TEXT,
                    status TEXT DEFAULT 'PENDING'
                )''')
    # ডিফল্ট সেটিংস
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('refer_bonus', '5.0')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('min_withdraw', '50.0')")
    conn.commit()
    conn.close()

init_db()

def get_setting(key, default="0"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default

def update_setting(key, value):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, first_name, username, balance, referred_by, total_refers, wallet, is_banned FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def add_user(user_id, first_name, username, referrer=0):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, first_name, username, balance, referred_by) VALUES (?, ?, ?, 0.0, ?)",
                  (user_id, first_name, username, referrer))
        conn.commit()
        if referrer and referrer != user_id:
            c.execute("SELECT user_id FROM users WHERE user_id=?", (referrer,))
            if c.fetchone():
                ref_bonus = float(get_setting("refer_bonus", "5.0"))
                c.execute("UPDATE users SET balance = balance + ?, total_refers = total_refers + 1 WHERE user_id=?", (ref_bonus, referrer))
                conn.commit()
                try:
                    bot.send_message(referrer, f"🎉 আপনার রেফারেল লিংকের মাধ্যমে একজন নতুন ইউজার যুক্ত হয়েছেন!\n💰 আপনি পেয়েছেন: {ref_bonus} টাকা।")
                except:
                    pass
    conn.close()

# --- ফোর্স সাবস্ক্রাইব চ্যানেল তালিকা ---
CHANNELS = [
    {"name": "📢 মেইন চ্যানেল", "username": "@AbolTabolStudio", "link": "https://t.me/AbolTabolStudio"}
]

def is_subscribed(user_id):
    for ch in CHANNELS:
        try:
            status = bot.get_chat_member(ch["username"], user_id).status
            if status not in ['member', 'administrator', 'creator']:
                return False
        except:
            return True  # চ্যানেল প্রাইভেট বা অ্যাডমিন না থাকলে বট যেন আটকে না থাকে
    return True

def force_sub_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in CHANNELS:
        markup.add(types.InlineKeyboardButton(ch["name"], url=ch["link"]))
    markup.add(types.InlineKeyboardButton("✅ জয়েন করেছি", callback_data="check_sub"))
    return markup

# --- মেইন কিবোর্ড মেনু ---
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_bal = types.KeyboardButton("💰 ব্যালেন্স")
    btn_ref = types.KeyboardButton("👥 রেফারেল")
    btn_task = types.KeyboardButton("📋 টাস্ক")
    btn_set = types.KeyboardButton("⚙️ ওয়ালেট সেট")
    btn_wd = types.KeyboardButton("💳 উত্তোলন")
    markup.add(btn_bal, btn_ref, btn_task, btn_set, btn_wd)
    return markup

# --- স্টার্ট কমান্ড (/start) ---
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.chat.id
    first_name = message.from_user.first_name or "User"
    username = message.from_user.username or ""

    user = get_user(user_id)
    if user and user[7] == 1:
        bot.send_message(user_id, "🚫 আপনাকে বট থেকে ব্যান করা হয়েছে।")
        return

    referrer = 0
    if len(message.text.split()) > 1:
        param = message.text.split()[1]
        if param.isdigit():
            referrer = int(param)

    add_user(user_id, first_name, username, referrer)

    if not is_subscribed(user_id):
        bot.send_message(user_id, "⚠️ **বটটি ব্যবহার করতে নিচের চ্যানেলগুলোতে জয়েন করুন:**",
                         parse_mode="Markdown", reply_markup=force_sub_markup())
        return

    bot.send_message(user_id, f"👋 স্বাগতম **{first_name}**!\nনিচের মেনু থেকে আপনার কাঙ্ক্ষিত অপশন বেছে নিন।",
                     parse_mode="Markdown", reply_markup=get_main_keyboard())

# --- ইউজার বাটন অ্যাকশন ---
@bot.message_handler(func=lambda msg: msg.text == "💰 ব্যালেন্স")
def user_balance(message):
    user = get_user(message.chat.id)
    if not user:
        return
    text = (f"👤 **আপনার তথ্য:**\n"
            f"🆔 আইডি: `{user[0]}`\n"
            f"💰 মূল ব্যালেন্স: **{user[3]:.2f} টাকা**\n"
            f"👥 মোট রেফার: **{user[5]} জন**\n"
            f"⚙️ সেভ করা ওয়ালেট: `{user[6]}`")
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "👥 রেফারেল")
def user_refer(message):
    user_id = message.chat.id
    ref_bonus = get_setting("refer_bonus", "5.0")
    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    text = (f"👥 **রেফারেল প্রোগ্রাম:**\n\n"
            f"প্রতি রেফারে পাবেন: **{ref_bonus} টাকা**\n\n"
            f"🔗 **আপনার রেফারেল লিংক:**\n`{ref_link}`\n\n"
            f"বন্ধুদের সাথে শেয়ার করুন এবং বোনাস আয় করুন!")
    bot.send_message(user_id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "📋 টাস্ক")
def user_tasks(message):
    bot.send_message(message.chat.id, "🎯 **ডেইলি টাস্ক:**\nবর্তমানে কোনো টাস্ক সক্রিয় নেই। খুব শীঘ্রই নতুন টাস্ক যোগ হবে!")

@bot.message_handler(func=lambda msg: msg.text == "⚙️ ওয়ালেট সেট")
def user_set_wallet(message):
    msg = bot.send_message(message.chat.id, "📝 আপনার পেমেন্ট গ্রহণের নাম্বার (bKash/Nagad/Rocket) লিখে সেন্ড করুন:")
    bot.register_next_step_handler(msg, save_wallet_step)

def save_wallet_step(message):
    wallet = message.text.strip()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET wallet=? WHERE user_id=?", (wallet, message.chat.id))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, f"✅ আপনার ওয়ালেট নাম্বার সফলভাবে সেভ হয়েছে:\n`{wallet}`", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "💳 উত্তোলন")
def user_withdraw(message):
    user_id = message.chat.id
    user = get_user(user_id)
    if not user:
        return
    min_wd = float(get_setting("min_withdraw", "50.0"))
    if user[6] == 'Not Set':
        bot.send_message(user_id, "⚠️ অনুগ্রহ করে আগে **⚙️ ওয়ালেট সেট** অপশন থেকে আপনার নাম্বার সেভ করে নিন।")
        return
    if user[3] < min_wd:
        bot.send_message(user_id, f"❌ উত্তোলনের জন্য সর্বনিম্ন ব্যালেন্স **{min_wd:.2f} টাকা** প্রয়োজন।\nআপনার বর্তমান ব্যালেন্স: {user[3]:.2f} টাকা।")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("bKash", callback_data="wd_bKash"),
        types.InlineKeyboardButton("Nagad", callback_data="wd_Nagad"),
        types.InlineKeyboardButton("Rocket", callback_data="wd_Rocket")
    )
    bot.send_message(user_id, "💳 কোন মেথডে টাকা নিতে চান সিলেক্ট করুন:", reply_markup=markup)

# --- আধুনিক অ্যাডমিন প্যানেল (/admin) ---
def get_admin_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 মোট ইউজার", callback_data="adm_stats"),
        types.InlineKeyboardButton("📢 ব্রডকাস্ট", callback_data="adm_bcast"),
        types.InlineKeyboardButton("🔍 ইউজার চেক", callback_data="adm_find_user"),
        types.InlineKeyboardButton("➕ ব্যালেন্স অ্যাড", callback_data="adm_add_bal"),
        types.InlineKeyboardButton("➖ ব্যালেন্স কাট", callback_data="adm_sub_bal"),
        types.InlineKeyboardButton("🚫 ব্যান / আনব্যান", callback_data="adm_ban"),
        types.InlineKeyboardButton("⚙️ রেফার বোনাস সেট", callback_data="adm_set_ref"),
        types.InlineKeyboardButton("💳 মিনিমাম উইথড্র সেট", callback_data="adm_set_minwd")
    )
    return markup

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if str(message.chat.id) != str(ADMIN_ID):
        bot.send_message(message.chat.id, "⛔ আপনি এই কমান্ড ব্যবহারের যোগ্য নন।")
        return
    ref_b = get_setting("refer_bonus", "5.0")
    min_w = get_setting("min_withdraw", "50.0")
    text = (f"🛠 **অ্যাডমিন কন্ট্রোল প্যানেল**\n\n"
            f"🎁 প্রতি রেফার বোনাস: {ref_b} টাকা\n"
            f"💳 মিনিমাম উইথড্র: {min_w} টাকা\n"
            f"কন্ট্রোল করতে নিচের অপশন নির্বাচন করুন:")
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=get_admin_markup())

# --- কলব্যাক কুয়েরি হ্যান্ডলার (অ্যাডমিন ও ইউজার বাটন) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "check_sub":
        if is_subscribed(chat_id):
            bot.delete_message(chat_id, call.message.message_id)
            bot.send_message(chat_id, "✅ সাবস্ক্রিপশন নিশ্চিত হয়েছে! বটের সুবিধা উপভোগ করুন।", reply_markup=get_main_keyboard())
        else:
            bot.answer_callback_query(call.id, "❌ আপনি এখনো সবগুলো চ্যানেলে জয়েন করেননি!", show_alert=True)

    # উইথড্র রিকোয়েস্ট ইনিশিয়েট
    elif data.startswith("wd_"):
        method = data.split("_")[1]
        user = get_user(chat_id)
        amount = user[3]
        wallet = user[6]

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE users SET balance = 0.0 WHERE user_id=?", (chat_id,))
        c.execute("INSERT INTO withdraws (user_id, amount, method, wallet) VALUES (?, ?, ?, ?)",
                  (chat_id, amount, method, wallet))
        wd_id = c.lastrowid
        conn.commit()
        conn.close()

        bot.edit_message_text(f"✅ আপনার **{amount:.2f} টাকা** উত্তোলনের রিকোয়েস্ট গ্রহণ করা হয়েছে।\nঅ্যাডমিন পর্যালোচনার পর পেমেন্ট কমপ্লিট করা হবে।",
                              chat_id, call.message.message_id, parse_mode="Markdown")

        # অ্যাডমিনের কাছে নোটিফিকেশন পাঠানো
        adm_markup = types.InlineKeyboardMarkup(row_width=2)
        adm_markup.add(
            types.InlineKeyboardButton("✅ Approve", callback_data=f"appr_{wd_id}"),
            types.InlineKeyboardButton("❌ Reject", callback_data=f"rejc_{wd_id}")
        )
        adm_text = (f"🔔 **নতুন উইথড্রয়াল রিকোয়েস্ট!**\n\n"
                    f"🆔 ইউজার: `{chat_id}`\n"
                    f"💰 পরিমাণ: **{amount:.2f} টাকা**\n"
                    f"💳 মেথড: {method}\n"
                    f"📱 একাউন্ট: `{wallet}`")
        bot.send_message(ADMIN_ID, adm_text, parse_mode="Markdown", reply_markup=adm_markup)

    # অ্যাডমিন উইথড্র অনুমোদন/বাতিল
    elif data.startswith("appr_"):
        wd_id = data.split("_")[1]
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT user_id, amount FROM withdraws WHERE id=?", (wd_id,))
        wd = c.fetchone()
        if wd:
            c.execute("UPDATE withdraws SET status='APPROVED' WHERE id=?", (wd_id,))
            conn.commit()
            bot.edit_message_text(f"✅ উইথড্র #{wd_id} সফলভাবে **অনুমোদিত** করা হয়েছে।", chat_id, call.message.message_id)
            try:
                bot.send_message(wd[0], f"🎉 আপনার **{wd[1]:.2f} টাকার** পেমেন্ট পাঠানো হয়েছে! সাথে থাকার জন্য ধন্যবাদ।")
            except:
                pass
        conn.close()

    elif data.startswith("rejc_"):
        wd_id = data.split("_")[1]
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT user_id, amount FROM withdraws WHERE id=?", (wd_id,))
        wd = c.fetchone()
        if wd:
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (wd[1], wd[0]))
            c.execute("UPDATE withdraws SET status='REJECTED' WHERE id=?", (wd_id,))
            conn.commit()
            bot.edit_message_text(f"❌ উইথড্র #{wd_id} **বাতিল** করা হয়েছে এবং ব্যালেন্স ফেরত দেওয়া হয়েছে।", chat_id, call.message.message_id)
            try:
                bot.send_message(wd[0], f"⚠️ আপনার **{wd[1]:.2f} টাকার** উত্তোলনের আবেদনটি বাতিল করা হয়েছে এবং টাকা ব্যালেন্সে ফিরিয়ে দেওয়া হয়েছে।")
            except:
                pass
        conn.close()

    # অ্যাডমিন কন্ট্রোল বাটনসমূহ
    elif data == "adm_stats":
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        total_u = c.fetchone()[0]
        c.execute("SELECT SUM(balance) FROM users")
        total_bal = c.fetchone()[0] or 0.0
        conn.close()
        bot.answer_callback_query(call.id)
        bot.send_message(ADMIN_ID, f"📊 **স্ট্যাটিস্টিক্স:**\n👥 মোট ইউজার: {total_u} জন\n💰 সমস্ত ইউজারের মোট ব্যালেন্স: {total_bal:.2f} টাকা")

    elif data == "adm_bcast":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(ADMIN_ID, "📢 সমস্ত ইউজারের কাছে পাঠানোর জন্য আপনার নোটিশ/মেসেজটি লিখে পাঠান:")
        bot.register_next_step_handler(msg, step_broadcast)

    elif data == "adm_find_user":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(ADMIN_ID, "🔍 যে ইউজারের তথ্য দেখতে চান তার টেলিগ্রাম আইডি লিখে পাঠান:")
        bot.register_next_step_handler(msg, step_find_user)

    elif data == "adm_add_bal":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(ADMIN_ID, "➕ ব্যালেন্স যোগ করতে লিখুন (আইডি এবং পরিমাণ স্পেস দিয়ে):\nযেমন: `12345678 20`")
        bot.register_next_step_handler(msg, step_modify_bal, mode="add")

    elif data == "adm_sub_bal":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(ADMIN_ID, "➖ ব্যালেন্স কাটতে লিখুন (আইডি এবং পরিমাণ স্পেস দিয়ে):\nযেমন: `12345678 10`")
        bot.register_next_step_handler(msg, step_modify_bal, mode="sub")

    elif data == "adm_ban":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(ADMIN_ID, "🚫 ব্যান বা আনব্যান করতে ইউজারের আইডি লিখে পাঠান:")
        bot.register_next_step_handler(msg, step_toggle_ban)

    elif data == "adm_set_ref":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(ADMIN_ID, "🎁 প্রতি রেফারে কত টাকা দিতে চান? শুধু সংখ্যা লিখে পাঠান (যেমন: 10):")
        bot.register_next_step_handler(msg, step_set_ref_bonus)

    elif data == "adm_set_minwd":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(ADMIN_ID, "💳 সর্বনিম্ন উইথড্র কত টাকা করতে চান? শুধু সংখ্যা লিখে পাঠান (যেমন: 100):")
        bot.register_next_step_handler(msg, step_set_min_wd)

# --- অ্যাডমিন নেক্সট স্টেপ হ্যান্ডলারসমূহ ---
def step_broadcast(message):
    text = message.text
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    sent = 0
    for u in users:
        try:
            bot.send_message(u[0], f"📢 **অফিসিয়াল নোটিশ:**\n\n{text}", parse_mode="Markdown")
            sent += 1
        except:
            pass
    bot.send_message(ADMIN_ID, f"✅ সফলভাবে **{sent}** জন ইউজারের কাছে নোটিশ পাঠানো হয়েছে!")

def step_find_user(message):
    try:
        uid = int(message.text.strip())
        u = get_user(uid)
        if u:
            status = "নিষিদ্ধ (Banned)" if u[7] == 1 else "সক্রিয় (Active)"
            text = (f"👤 **ইউজার ডাটা:**\n\n"
                    f"🆔 আইডি: `{u[0]}`\n"
                    f"📛 নাম: {u[1]} (@{u[2]})\n"
                    f"💰 ব্যালেন্স: **{u[3]:.2f} টাকা**\n"
                    f"👥 মোট রেফার: {u[5]} জন\n"
                    f"⚙️ ওয়ালেট: `{u[6]}`\n"
                    f"🚦 স্ট্যাটাস: {status}")
            bot.send_message(ADMIN_ID, text, parse_mode="Markdown")
        else:
            bot.send_message(ADMIN_ID, "❌ এই আইডির কোনো ইউজার খুঁজে পাওয়া যায়নি।")
    except:
        bot.send_message(ADMIN_ID, "⚠️ সঠিক টেলিগ্রাম আইডি লিখুন।")

def step_modify_bal(message, mode):
    try:
        parts = message.text.strip().split()
        uid = int(parts[0])
        amt = float(parts[1])
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        if mode == "add":
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, uid))
            bot.send_message(ADMIN_ID, f"✅ `{uid}` আইডিতে **+{amt} টাকা** সফলভাবে যোগ করা হয়েছে।")
            try:
                bot.send_message(uid, f"🎁 অ্যাডমিন আপনার একাউন্টে **{amt} টাকা** যোগ করেছেন!")
            except:
                pass
        else:
            c.execute("UPDATE users SET balance = MAX(0, balance - ?) WHERE user_id=?", (amt, uid))
            bot.send_message(ADMIN_ID, f"✅ `{uid}` আইডি থেকে **-{amt} টাকা** কেটে নেওয়া হয়েছে।")
        conn.commit()
        conn.close()
    except:
        bot.send_message(ADMIN_ID, "⚠️ ভুল ফরম্যাট! সঠিক আইডি এবং পরিমাণ স্পেস দিয়ে লিখুন।")

def step_toggle_ban(message):
    try:
        uid = int(message.text.strip())
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT is_banned FROM users WHERE user_id=?", (uid,))
        row = c.fetchone()
        if row:
            new_status = 0 if row[0] == 1 else 1
            c.execute("UPDATE users SET is_banned=? WHERE user_id=?", (new_status, uid))
            conn.commit()
            status_text = "আনব্যান" if new_status == 0 else "ব্যান"
            bot.send_message(ADMIN_ID, f"✅ ইউজার `{uid}` কে **{status_text}** করা হয়েছে।")
        else:
            bot.send_message(ADMIN_ID, "❌ ইউজার খুঁজে পাওয়া যায়নি।")
        conn.close()
    except:
        bot.send_message(ADMIN_ID, "⚠️ সঠিক আইডি লিখুন।")

def step_set_ref_bonus(message):
    try:
        val = float(message.text.strip())
        update_setting("refer_bonus", val)
        bot.send_message(ADMIN_ID, f"✅ রেফারেল বোনাস সফলভাবে **{val} টাকা** নির্ধারণ করা হয়েছে।")
    except:
        bot.send_message(ADMIN_ID, "⚠️ অনুগ্রহ করে একটি সঠিক সংখ্যা লিখুন।")

def step_set_min_wd(message):
    try:
        val = float(message.text.strip())
        update_setting("min_withdraw", val)
        bot.send_message(ADMIN_ID, f"✅ সর্বনিম্ন উত্তোলন লিমিট **{val} টাকা** সেট করা হয়েছে।")
    except:
        bot.send_message(ADMIN_ID, "⚠️ অনুগ্রহ করে একটি সঠিক সংখ্যা লিখুন।")

# --- বট স্টার্ট ---
if __name__ == "__main__":
    print("Starting Keep-Alive Web Server...")
    keep_alive()
    print("Bot is listening for messages...")
    bot.infinity_polling(skip_pending=True)
    
