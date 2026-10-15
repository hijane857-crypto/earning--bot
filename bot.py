import os
import sqlite3
import threading
from flask import Flask
import telebot
from telebot import types

# --- কনফিগারেশন ---
BOT_TOKEN = "8893588513:AAEopQIxE75DKqna_JRrQUMDSBf1RepOg3U"
ADMIN_ID = "7103959220"

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
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    link TEXT,
                    reward REAL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_tasks (
                    user_id INTEGER,
                    task_id INTEGER,
                    PRIMARY KEY (user_id, task_id)
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
            return True
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

# --- ইউজার মেনু বাটনসমূহ ---
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
    user_id = message.chat.id
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''SELECT id, title, link, reward FROM tasks 
                 WHERE id NOT IN (SELECT task_id FROM user_tasks WHERE user_id=?)''', (user_id,))
    tasks = c.fetchall()
    conn.close()

    if not tasks:
        bot.send_message(user_id, "🎉 বর্তমানে কোনো নতুন টাস্ক নেই! পরে আবার চেষ্টা করুন।")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for t in tasks:
        t_id, title, link, reward = t
        markup.add(
            types.InlineKeyboardButton(f"👉 {title} (+{reward}৳)", url=link),
            types.InlineKeyboardButton(f"✅ সম্পন্ন করেছি #{t_id}", callback_data=f"claim_{t_id}")
        )
    bot.send_message(user_id, "🎯 **নিচের টাস্কগুলো সম্পন্ন করে লিংকের নিচের বোতাম চেপে বোনাস সংগ্রহ করুন:**", reply_markup=markup)

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
        types.InlineKeyboardButton("➕ নতুন টাস্ক যোগ", callback_data="adm_add_task"),
        types.InlineKeyboardButton("🗑 টাস্ক ডিলিট", callback_data="adm_del_task"),
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
            f"নিচের মেনু থেকে আপনার অ্যাকশন নির্বাচন করুন:")
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=get_admin_markup())

# --- কলব্যাক কুয়েরি হ্যান্ডলার ---
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

    # ইউজার টাস্ক রিওয়ার্ড ক্লেম
    elif data.startswith("claim_"):
        t_id = int(data.split("_")[1])
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id FROM user_tasks WHERE user_id=? AND task_id=?", (chat_id, t_id))
        already_done = c.fetchone()
        if already_done:
            bot.answer_callback_query(call.id, "⚠️ আপনি ইতিমধ্যে এই টাস্কটি সম্পন্ন করেছেন!", show_alert=True)
            conn.close()
            return

        c.execute("SELECT reward FROM tasks WHERE id=?", (t_id,))
        task = c.fetchone()
        if task:
            reward = task[0]
            c.execute("INSERT INTO user_tasks (user_id, task_id) VALUES (?, ?)", (chat_id, t_id))
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (reward, chat_id))
            conn.commit()
            bot.answer_callback_query(call.id, f"🎉 অভিনন্দন! +{reward} টাকা ব্যালেন্সে যুক্ত হয়েছে।", show_alert=True)
            bot.delete_message(chat_id, call.message.message_id)
        conn.close()

    # উইথড্র রিকোয়েস্ট সাবমিট
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

    # অ্যাডমিন উইথড্র অনুমোদন ও বাতিল
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
                bot.send_message(wd[0], f"🎉 আপনার **{wd[1]:.2f} টাকার** পেমেন্ট পাঠানো হয়েছে! ধন্যবাদ।")
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
            bot.edit_message_text(f"❌ উইথড্র #{wd_id} **বাতিল** করা হয়েছে এবং টাকা ইউজারের ব্যালেন্সে ফেরত দেওয়া হয়েছে।", chat_id, call.message.message_id)
            try:
                bot.send_message(wd[0], f"⚠️ আপনার **{wd[1]:.2f} টাকার** উত্তোলনের আবেদনটি বাতিল করে টাকা পুনরায় ব্যালেন্সে দেওয়া হয়েছে।")
            except:
                pass
        conn.close()

    # অ্যাডমিন বাটন অ্যাকশন
    elif data == "adm_add_task":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(ADMIN_ID, "📝 নতুন টাস্ক যোগ করতে এভাবে লিখে পাঠান:\n\n`শিরোনাম | লিংক | রিওয়ার্ড`\n\nউদাহরণ:\n`ইউটিউব চ্যানেল সাবস্ক্রাইব | https://youtube.com/@channel | 3.5`")
        bot.register_next_step_handler(msg, step_create_task)

    elif data == "adm_del_task":
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, title FROM tasks")
        all_tasks = c.fetchall()
        conn.close()
        if not all_tasks:
            bot.answer_callback_query(call.id, "মুছে ফেলার মতো কোনো টাস্ক নেই!", show_alert=True)
            return
        del_markup = types.InlineKeyboardMarkup(row_width=1)
        for t in all_tasks:
            del_markup.add(types.InlineKeyboardButton(f"❌ ডিলিট: {t[1]}", callback_data=f"deltask_{t[0]}"))
        bot.send_message(ADMIN_ID, "🗑 যে টাস্কটি মুছে ফেলতে চান তাতে চাপ দিন:", reply_markup=del_markup)

    elif data.startswith("deltask_"):
        task_id = int(data.split("_")[1])
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        c.execute("DELETE FROM user_tasks WHERE task_id=?", (task_id,))
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, "টাস্কটি সফলভাবে মুছে ফেলা হয়েছে!", show_alert=True)
        bot.delete_message(chat_id, call.message.message_id)

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
        msg = bot.send_message(ADMIN_ID, "📢 সমস্ত ইউজারের কাছে পাঠানোর জন্য নোটিশটি লিখে পাঠান:")
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
        msg = bot.send_message(ADMIN_ID, "🎁 প্রতি রেফারে কত টাকা দিতে চান? সংখ্যা লিখে পাঠান (যেমন: 5):")
        bot.register_next_step_handler(msg, step_set_ref_bonus)

    elif data == "adm_set_minwd":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(ADMIN_ID, "💳 সর্বনিম্ন উত্তোলন কত টাকা করতে চান? সংখ্যা লিখে পাঠান (যেমন: 50):")
        bot.register_next_step_handler(msg, step_set_min_wd)

# --- অ্যাডমিন ইনপুট স্টেপ ফাংশনসমূহ ---
def step_create_task(message):
    try:
        parts = [p.strip() for p in message.text.split("|")]
        title = parts[0]
     
