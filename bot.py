import telebot
from telebot import types

BOT_TOKEN = "8893588513:AAEopQIxE75DKqna_JRrQUMDSBf1RepOg3U"
ADMIN_ID = "7103959220"

bot = telebot.TeleBot(BOT_TOKEN)

CHANNELS = [
    {"name": "📢 চ্যানেল ১", "link": "https://t.me/+mL_1MIX1IXphMDNl"},
    {"name": "📢 চ্যানেল ২", "link": "https://t.me/bounsbox"},
    {"name": "📢 চ্যানেল ৩", "link": "https://t.me/+ctuysqHkGBNkNjNl"}
]

users = {}
user_states = {}
verified_users = set()

def send_force_sub_message(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in CHANNELS:
        markup.add(types.InlineKeyboardButton(f"{ch['name']}-এ জয়েন করুন", url=ch["link"]))
    markup.add(types.InlineKeyboardButton("✅ জয়েন করেছি (যাচাই করুন)", callback_data="check_joined"))
    
    bot.send_message(
        chat_id, 
        "⚠️ **বট ব্যবহার করতে আপনাকে অবশ্যই নিচের ৩টি চ্যানেলে জয়েন থাকতে হবে!**\n\nচ্যানেলগুলোতে জয়েন করে নিচের বাটনে চাপ দিন এবং ২ টাকা বোনাস নিন:",
        parse_mode="Markdown",
        reply_markup=markup
    )

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_bal = types.KeyboardButton("💰 ব্যালেন্স")
    btn_ref = types.KeyboardButton("👥 রেফারেল")
    btn_task = types.KeyboardButton("📋 টাস্ক")
    btn_set = types.KeyboardButton("⚙️ ওয়ালেট সেট")
    btn_wd = types.KeyboardButton("💳 উত্তোলন")
    markup.add(btn_bal, btn_ref, btn_task, btn_set, btn_wd)
    return markup

# --- অ্যাডমিন কমান্ড (/admin) ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    uid = str(message.chat.id)
    if uid != ADMIN_ID:
        bot.send_message(uid, "⛔ আপনি এই কমান্ডটি ব্যবহার করার অনুমতিপ্রাপ্ত নন!")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_stats = types.InlineKeyboardButton("📊 মোট ইউজার", callback_data="adm_stats")
    markup.add(types.InlineKeyboardButton("✅ জয়েন করেছি (যাচাই করুন)", callback_data="check_joined"))
    
    
