import sqlite3
import telebot
from telebot import types

# ================= কনফিগারেশন =================
BOT_TOKEN = "8893588513:AAFizN3XvN0qwuaRPCbUI6kY3e7IqA1pSnw"
ADMIN_ID = 7103959220  # আপনার অ্যাডমিন আইডি
DB_NAME = "database.db"

# যে ৩টি প্রাইভেট চ্যানেলে জয়েন বাধ্যতামূলক
CHANNELS = [
    {"name": "📢 ১ম চ্যানেল", "id": -1004387726267, "link": "https://t.me/+your_link_1"},
    {"name": "📢 ২য় চ্যানেল", "id": -1004396751732, "link": "https://t.me/+your_link_2"},
    {"name": "📢 ৩য় চ্যানেল", "id": -1004319291695, "link": "https://t.me/+your_link_3"}
]

bot = telebot.TeleBot(BOT_TOKEN)

# ================= ডাটাবেজ সেটআপ =================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    username TEXT,
                    balance REAL DEFAULT 0.0,
                    wallet TEXT DEFAULT 'Not Set',
                    referrer INTEGER DEFAULT 0,
                    is_banned INTEGER DEFAULT 0
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    link TEXT,
                    reward REAL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_tasks (
                    user_id INTEGER,
                    task_id INTEGER
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS withdrawals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount REAL,
                    method TEXT,
                    number TEXT,
                    status TEXT DEFAULT 'pending'
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )''')
    c.execute("INSERT OR IGNORE INTO settings VALUES ('ref_bonus', '5.0')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('min_wd', '50.0')")
    conn.commit()
    conn.close()

init_db()

# ডাটাবেজ হেল্পার ফাংশন
def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def get_setting(key, default):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default

def set_setting(key, value):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

# চ্যানেল সাবস্ক্রিপশন চেক
def is_subscribed_all(user_id):
    return True

def force_sub_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in CHANNELS:
        markup.add(types.InlineKeyboardButton(ch["name"], url=ch["link"]))
    markup.add(types.InlineKeyboardButton("✅ ভেরিফাই করুন", callback_data="verify_sub"))
    return markup

# ================= বাটন কিবোর্ড মেনু =================
def member_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📋 Task"),
        types.KeyboardButton("👥 Raffer"),
        types.KeyboardButton("⚙️ Wallet add"),
        types.KeyboardButton("✨ New service"),
        types.KeyboardButton("💳 Withdrawal"),
        types.KeyboardButton("👨‍💻 Support admin")
    )
    return markup

def admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("👤 Member user info"),
        types.KeyboardButton("📋 All withdrawal list"),
        types.KeyboardButton("➕ Balance add"),
        types.KeyboardButton("➖ Balance moved"),
        types.KeyboardButton("🔍 Withdrawal request check"),
        types.KeyboardButton("📢 Personal+ public message"),
        types.KeyboardButton("🚀 New fewsar"),
        types.KeyboardButton("🛠 All button edit + opening"),
        types.KeyboardButton("🔙 User Mode")
    )
    return markup
            # ================= অ্যাডমিন বাটন অ্যাকশন =================
@bot.message_handler(func=lambda msg: msg.from_user.id == ADMIN_ID and msg.text in [
    "👤 Member user info", "📋 All withdrawal list", "➕ Balance add", "➖ Balance moved",
    "🔍 Withdrawal request check", "📢 Personal+ public message", "🚀 New fewsar", "🛠 All button edit + opening"
])
def handle_admin_features(message):
    text = message.text

    # ১. Member user info
    if text == "👤 Member user info":
        m = bot.send_message(ADMIN_ID, "🔍 যে ইউজারের তথ্য দেখতে চান তার Telegram User ID দিন:")
        bot.register_next_step_handler(m, admin_lookup_user)

    # ২. All withdrawal list (সর্বশেষ হিস্ট্রি)
    elif text == "📋 All withdrawal list":
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, user_id, amount, method, number, status FROM withdrawals ORDER BY id DESC LIMIT 15")
        rows = c.fetchall()
        conn.close()

        if not rows:
            bot.send_message(ADMIN_ID, "উইথড্র তালিকায় কোনো ডাটা নেই।")
            return

        res = "📋 **সর্বশেষ ১৫টি উইথড্র হিস্ট্রি:**\n\n"
        for r in rows:
            res += f"ID: `{r[0]}` | User: `{r[1]}` | {r[2]}৳ ({r[3]})\n📱 `{r[4]}` | অবস্থা: **{r[5]}**\n------------------\n"
        bot.send_message(ADMIN_ID, res, parse_mode="Markdown")

    # ৩. Balance add
    elif text == "➕ Balance add":
        m = bot.send_message(ADMIN_ID, "ব্যালেন্স যোগ করতে লিখুন (ফরম্যাট: UserID Amount):")
        bot.register_next_step_handler(m, admin_add_balance)

    # ৪. Balance moved (ব্যালেন্স কাটা)
    elif text == "➖ Balance moved":
        m = bot.send_message(ADMIN_ID, "ব্যালেন্স কাটতে লিখুন (ফরম্যাট: UserID Amount):")
        bot.register_next_step_handler(m, admin_cut_balance)

    # ৫. Withdrawal request check
    elif text == "🔍 Withdrawal request check":
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, user_id, amount, method, number FROM withdrawals WHERE status = 'pending'")
        rows = c.fetchall()
        conn.close()

        if not rows:
            bot.send_message(ADMIN_ID, "✅ বর্তমানে কোনো পেন্ডিং উইথড্র রিকোয়েস্ট নেই!")
            return

        for r in rows:
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ Approve", callback_data=f"app_wd_{r[0]}_{r[1]}_{r[2]}"),
                types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_wd_{r[0]}_{r[1]}_{r[2]}")
            )
            bot.send_message(
                ADMIN_ID,
                f"🆔 রিকোয়েস্ট ID: `{r[0]}`\n👤 ইউজার: `{r[1]}`\n💰 পরিমাণ: {r[2]}৳\n💳 মেথড: {r[3]}\n📱 নাম্বার: `{r[4]}`",
                reply_markup=markup,
                parse_mode="Markdown"
            )

    # ৬. Personal + public message
    elif text == "📢 Personal+ public message":
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("📢 Public Broadcast (সবাইকে)", callback_data="admin_broadcast_all"),
            types.InlineKeyboardButton("👤 Personal Message (একজনকে)", callback_data="admin_send_personal")
        )
        bot.send_message(ADMIN_ID, "মেসেজ পাঠানোর ধরন বেছে নিন:", reply_markup=markup)

    # ৭. New fewsar (টাস্ক যোগ)
    elif text == "🚀 New fewsar":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ নতুন আর্নিং টাস্ক যোগ", callback_data="admin_add_task"))
        bot.send_message(ADMIN_ID, "🚀 **New Feature & Task Panel:**", reply_markup=markup, parse_mode="Markdown")

    # ৮. All button edit + opening (লিংক ও সেটিংস এডিটর)
    elif text == "🛠 All button edit + opening":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🔗 সাপোর্ট লিংক পরিবর্তন", callback_data="edit_support_link"),
            types.InlineKeyboardButton("🎁 ফ্রি সার্ভিস টেক্সট/লিংক", callback_data="edit_free_service"),
            types.InlineKeyboardButton("💎 পেইড সার্ভিস টেক্সট/লিংক", callback_data="edit_paid_service"),
            types.InlineKeyboardButton("💰 বোনাস ও মিনিমাম উইথড্র", callback_data="edit_limits")
        )
        bot.send_message(ADMIN_ID, "🛠 **বাটন ও লিংক কন্ট্রোল সেন্টার:**\nকোন অপশনটি আপডেট বা এডিট করতে চান?", reply_markup=markup, parse_mode="Markdown")

def admin_lookup_user(message):
    try:
        uid = int(message.text.strip())
        user = get_user(uid)
        if user:
            bot.send_message(ADMIN_ID, f"👤 **ইউজার তথ্য:**\nআইডি: `{user[0]}`\nনাম: {user[1]}\nব্যালেন্স: {user[3]}৳\nওয়ালেট: `{user[4]}`\nরেফারার: `{user[5]}`", parse_mode="Markdown")
        else:
            bot.send_message(ADMIN_ID, "❌ এই আইডির কোনো ইউজার পাওয়া যায়নি।")
    except:
        bot.send_message(ADMIN_ID, "ভুল ইনপুট।")

def admin_add_balance(message):
    try:
        uid, amt = message.text.split()
        amt = float(amt)
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, int(uid)))
        conn.commit()
        conn.close()
        bot.send_message(ADMIN_ID, f"✅ ইউজার `{uid}`-এর একাউন্টে {amt}৳ যোগ করা হয়েছে।", parse_mode="Markdown")
        bot.send_message(int(uid), f"🎁 এডমিন আপনার একাউন্টে {amt}৳ ব্যালেন্স যোগ করেছেন!")
    except:
        bot.send_message(ADMIN_ID, "❌ ফরম্যাট ভুল! লিখুন: `UserID Amount` যেমন: `7103959220 20`")

def admin_cut_balance(message):
    try:
        uid, amt = message.text.split()
        amt = float(amt)
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amt, int(uid)))
        conn.commit()
        conn.close()
        bot.send_message(ADMIN_ID, f"✅ ইউজার `{uid}`-এর ব্যালেন্স থেকে {amt}৳ কাটা হয়েছে।", parse_mode="Markdown")
    except:
        bot.send_message(ADMIN_ID, "❌ ফরম্যাট ভুল! লিখুন: `UserID Amount`")
# ================= মেম্বার বাটন অ্যাকশন =================
@bot.message_handler(func=lambda msg: msg.text in [
    "📋 Task", "👥 Raffer", "⚙️ Wallet add", "✨ New service", "💳 Withdrawal", "👨‍💻 Support admin", "🔙 User Mode"
])
def handle_member_buttons(message):
    uid = message.chat.id
    text = message.text

    if not is_subscribed_all(uid):
        bot.send_message(uid, "⚠️ অনুগ্রহ করে আগে ৩টি চ্যানেলে জয়েন করে ভেরিফাই করুন!", reply_markup=force_sub_markup())
        return

    user = get_user(uid)
    if not user:
        return

    if text == "📋 Task":
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM tasks WHERE id NOT IN (SELECT task_id FROM user_tasks WHERE user_id = ?)", (uid,))
        available_tasks = c.fetchall()
        conn.close()

        if not available_tasks:
            bot.send_message(uid, "✅ এই মুহূর্তে কোনো নতুন টাস্ক নেই।")
            return

        for t in available_tasks:
            t_id, title, link, reward = t
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("🔗 টাস্ক লিংক", url=link),
                types.InlineKeyboardButton("✅ সম্পন্ন করেছি", callback_data=f"claim_{t_id}_{reward}")
            )
            bot.send_message(uid, f"📌 **{title}**\n💰 রিওয়ার্ড: {reward}৳", reply_markup=markup, parse_mode="Markdown")

    elif text == "👥 Raffer":
        bot_user = bot.get_me().username
        ref_link = f"https://t.me/{bot_user}?start={uid}"
        bonus = get_setting("ref_bonus", "5.0")
        msg = (
            f"👥 **আপনার রেফারেল লিংক:**\n`{ref_link}`\n\n"
            f"🎁 প্রতি রেফারে পাবেন: **{bonus}৳**\n"
            f"💰 বর্তমান ব্যালেন্স: **{user[3]}৳**"
        )
        bot.send_message(uid, msg, parse_mode="Markdown")

    elif text == "⚙️ Wallet add":
        m = bot.send_message(uid, f"📱 আপনার সেভ করা ওয়ালেট: `{user[4]}`\n\nনতুন বিকাশ বা নগদ নাম্বারটি লিখে পাঠান:")
        bot.register_next_step_handler(m, process_wallet_save)

    elif text == "✨ New service":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🎁 Free Use", callback_data="service_free"),
            types.InlineKeyboardButton("💎 Paid Use", callback_data="service_paid")
        )
        bot.send_message(uid, "✨ **New Service নির্বাচন করুন:**", reply_markup=markup, parse_mode="Markdown")

    elif text == "💳 Withdrawal":
        min_w = float(get_setting("min_wd", "50.0"))
        if user[4] == 'Not Set':
            bot.send_message(uid, "⚠️ টাকা তোলার আগে **Wallet add** বাটনে চাপ দিয়ে নাম্বার সেট করুন।")
            return
        if user[3] < min_w:
            bot.send_message(uid, f"❌ সর্বনিম্ন উইথড্র **{min_w}৳**। আপনার ব্যালেন্স **{user[3]}৳**।")
            return

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("bKash", callback_data="wd_bKash"),
            types.InlineKeyboardButton("Nagad", callback_data="wd_Nagad")
        )
        bot.send_message(uid, f"💳 ব্যালেন্স: **{user[3]}৳**\nকোন মাধ্যমে উত্তোলন করতে চান?", reply_markup=markup, parse_mode="Markdown")

    elif text == "👨‍💻 Support admin":
        bot.send_message(uid, f"👨‍💻 সরাসরি এডমিনের সাথে যোগাযোগ করুন:\n👉 tg://user?id=7103959220")

    elif text == "🔙 User Mode":
        bot.send_message(uid, "মেম্বার মেনুতে ফিরে আসা হয়েছে।", reply_markup=member_keyboard())

def process_wallet_save(message):
    num = message.text.strip()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET wallet = ? WHERE user_id = ?", (num, message.chat.id))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, f"✅ আপনার ওয়ালেট নাম্বার সফলভাবে সেভ হয়েছে: `{num}`", parse_mode="Markdown")

# ================= কলব্যাক কুয়েরি হ্যান্ডলার =================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data
    uid = call.message.chat.id

    # ১. সাবস্ক্রিপশন ভেরিফাই বাটন
    if data == "verify_sub":
        if is_subscribed_all(uid):
            bot.delete_message(uid, call.message.message_id)
            bot.send_message(uid, "✅ সফলভাবে ভেরিফাই সম্পন্ন হয়েছে!", reply_markup=member_keyboard())
        else:
            bot.answer_callback_query(call.id, "❌ আপনি এখনো সবগুলো চ্যানেলে জয়েন করেননি!", show_alert=True)

    # ২. টাস্ক রিওয়ার্ড ক্লেইম
    elif data.startswith("claim_"):
        _, t_id, rew = data.split("_")
        t_id, rew = int(t_id), float(rew)

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM user_tasks WHERE user_id = ? AND task_id = ?", (uid, t_id))
        if c.fetchone():
            bot.answer_callback_query(call.id, "⚠️ আপনি ইতিমধ্যে এই টাস্কটি সম্পন্ন করেছেন!", show_alert=True)
            conn.close()
            return

        c.execute("INSERT INTO user_tasks (user_id, task_id) VALUES (?, ?)", (uid, t_id))
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (rew, uid))
        conn.commit()
        conn.close()

        bot.answer_callback_query(call.id, f"🎉 অভিনন্দন! {rew}৳ ব্যালেন্সে যোগ হয়েছে!", show_alert=True)
        bot.delete_message(uid, call.message.message_id)

    # ৩. নিউ সার্ভিস বাটন
    elif data == "service_free":
        free_txt = get_setting("free_service_info", "🎁 **ফ্রি সার্ভিস:**\nআমাদের ফ্রি সিগন্যাল ও কন্টেন্ট পেতে নিয়মিত চ্যানেলে অ্যাক্টিভ থাকুন।")
        bot.send_message(uid, free_txt, parse_mode="Markdown")
    elif data == "service_paid":
        paid_txt = get_setting("paid_service_info", "💎 **পেইড সার্ভিস:**\nভিআইপি প্ল্যান নিতে সরাসরি এডমিনের সাথে যোগাযোগ করুন: tg://user?id=7103959220")
        bot.send_message(uid, paid_txt, parse_mode="Markdown")

    # ৪. উইথড্র মেথড সিলেক্ট
    elif data.startswith("wd_"):
        method = data.split("_")[1]
        m = bot.send_message(uid, f"💰 {method}-এ কত টাকা উত্তোলন করতে চান?")
        bot.register_next_step_handler(m, process_withdraw_step, method)

    # ৫. উইথড্র অ্যাপ্রুভ / রিজেক্ট
    elif data.startswith("app_wd_"):
        _, _, w_id, u_id, amt = data.split("_")
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE withdrawals SET status = 'approved' WHERE id = ?", (w_id,))
        conn.commit()
        conn.close()
        bot.edit_message_text(f"✅ উইথড্রল রিকোয়েস্ট ID `{w_id}` সফলভাবে Approved হয়েছে।", ADMIN_ID, call.message.message_id)
        try:
            bot.send_message(int(u_id), f"🎉 অভিনন্দন! আপনার {amt}৳ উত্তোলন সম্পন্ন হয়েছে।")
        except:
            pass

    elif data.startswith("rej_wd_"):
        _, _, w_id, u_id, amt = data.split("_")
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE withdrawals SET status = 'rejected' WHERE id = ?", (w_id,))
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (float(amt), int(u_id)))
        conn.commit()
        conn.close()
        bot.edit_message_text(f"❌ উইথড্রল রিকোয়েস্ট ID `{w_id}` বাতিল করা হয়েছে এবং টাকা ব্যালেন্সে ফেরত দেওয়া হয়েছে।", ADMIN_ID, call.message.message_id)
        try:
            bot.send_message(int(u_id), f"⚠️ আপনার {amt}৳ উত্তোলন বাতিল করা হয়েছে এবং মূল ব্যালেন্সে টাকা রিফান্ড করা হয়েছে।")
        except:
            pass

    # ৬. ব্রডকাস্ট ও টাস্ক কলব্যাক
    elif data == "admin_broadcast_all":
        m = bot.send_message(ADMIN_ID, "📢 সকল ইউজারের কাছে যে বার্তা পাঠাতে চান তা লিখুন:")
        bot.register_next_step_handler(m, process_broadcast)

    elif data == "admin_send_personal":
        m = bot.send_message(ADMIN_ID, "ফরম্যাট: `UserID আপনার বার্তা` লিখে পাঠান:")
        bot.register_next_step_handler(m, process_personal_msg)

    elif data == "admin_add_task":
        m = bot.send_message(ADMIN_ID, "টাস্ক যোগ করতে লিখুন:\n`শিরোনাম|লিংক|টাকা`")
        bot.register_next_step_handler(m, process_add_task)

    # ৭. All Button Edit কলব্যাকস
    elif data == "edit_support_link":
        m = bot.send_message(ADMIN_ID, "নতুন সাপোর্ট এডমিন ইউজারনেম বা আইডি লিংক পাঠান:")
        bot.register_next_step_handler(m, save_setting_step, "support_link")

    elif data == "edit_free_service":
        m = bot.send_message(ADMIN_ID, "ফ্রি সার্ভিসের জন্য নতুন মেসেজ বা লিংক লিখে পাঠান:")
        bot.register_next_step_handler(m, save_setting_step, "free_service_info")

    elif data == "edit_paid_service":
        m = bot.send_message(ADMIN_ID, "পেইড সার্ভিসের জন্য নতুন মেসেজ বা লিংক লিখে পাঠান:")
        bot.register_next_step_handler(m, save_setting_step, "paid_service_info")

    elif data == "edit_limits":
        m = bot.send_message(ADMIN_ID, "ফরম্যাট: `রেফার_বোনাস মিনিমাম_উইথড্র` (যেমন: `5.0 50`)")
        bot.register_next_step_handler(m, save_limits_step)

# উইথড্র প্রসেস
def process_withdraw_step(message, method):
    try:
        amt = float(message.text.strip())
        uid = message.chat.id
        user = get_user(uid)
        min_w = float(get_setting("min_wd", "50.0"))

        if amt < min_w or amt > user[3]:
            bot.send_message(uid, f"❌ সঠিক পরিমাণ লিখুন। সর্বনিম্ন উইথড্র {min_w}৳ এবং আপনার ব্যালেন্স {user[3]}৳।")
            return

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amt, uid))
        c.execute("INSERT INTO withdrawals (user_id, amount, method, number) VALUES (?, ?, ?, ?)", (uid, amt, method, user[4]))
        req_id = c.lastrowid
        conn.commit()
        conn.close()

        bot.send_message(uid, f"✅ আপনার {amt}৳ উত্তোলনের রিকোয়েস্ট সফলভাবে জমা হয়েছে।")
        bot.send_message(ADMIN_ID, f"🔔 **নতুন উত্তোলন রিকোয়েস্ট!**\n\n🆔 আইডি: `{req_id}`\n👤 ইউজার: `{uid}`\n💰 টাকা: {amt}৳\n💳 মেথড: {method}\n📱 নাম্বার: `{user[4]}`", parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "❌ শুধুমাত্র সংখ্যা লিখুন।")

# ব্রডকাস্ট ও সেটিংস সেভ ফাংশন
def process_broadcast(message):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    
    count = 0
    for u in users:
        try:
            bot.send_message(u[0], f"📢 **বিজ্ঞপ্তি:**\n\n{message.text}", parse_mode="Markdown")
            count += 1
        except:
            pass
    bot.send_message(ADMIN_ID, f"✅ মোট {count} জন ইউজারের কাছে নোটিফিকেশন পৌঁছেছে।")

def process_personal_msg(message):
    try:
        parts = message.text.split(" ", 1)
        uid = int(parts[0])
        msg = parts[1]
        bot.send_message(uid, f"📩 **এডমিন মেসেজ:**\n\n{msg}", parse_mode="Markdown")
        bot.send_message(ADMIN_ID, "✅ মেসেজ পাঠানো হয়েছে।")
    except:
        bot.send_message(ADMIN_ID, "❌ ভুল ফরম্যাট! লিখুন: `UserID মেসেজ`")

def process_add_task(message):
    try:
        title, link, rew = message.text.split("|")
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO tasks (title, link, reward) VALUES (?, ?, ?)", (title.strip(), link.strip(), float(rew.strip())))
        conn.commit()
        conn.close()
        bot.send_message(ADMIN_ID, "✅ নতুন টাস্ক সফলভাবে তৈরি হয়েছে!")
    except:
        bot.send_message(ADMIN_ID, "❌ পাইপ (|) দিয়ে লিখুন: `শিরোনাম|লিংক|টাকা`")

def save_setting_step(message, key_name):
    set_setting(key_name, message.text)
    bot.send_message(ADMIN_ID, f"✅ `{key_name}` সফলভাবে ডাটাবেজে আপডেট হয়েছে!", parse_mode="Markdown")

def save_limits_step(message):
    try:
        ref, min_w = message.text.split()
        set_setting("ref_bonus", ref)
        set_setting("min_wd", min_w)
        bot.send_message(ADMIN_ID, f"✅ রেফার বোনাস: {ref}৳ এবং মিনিমাম উইথড্র: {min_w}৳ সেট করা হয়েছে।")
    except:
        bot.send_message(ADMIN_ID, "❌ ফরম্যাট ভুল! লিখুন: `5.0 50`")

import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class SimpleHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_http():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

# ওয়েব সার্ভারকে আলাদা ব্যাকগ্রাউন্ড থ্রেডে পাঠানো
threading.Thread(target=run_http, daemon=True).start()

# বট চালু
print("Bot is successfully running...")
bot.remove_webhook()
bot.infinity_polling(skip_pending=True)
        
