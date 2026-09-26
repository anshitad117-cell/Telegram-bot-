#!/usr/bin/env python3
# SMM Bot - Complete Working Code
import sqlite3
import re
import logging
from uuid import uuid4
from functools import wraps
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= CONFIG =================
BOT_TOKEN = "8825904902:AAEaIfurVLLYVvB4SPLfW-TmA34kyavynlI"
ADMIN_TG_ID = 8782064983
UPI_ID = "mdaryan@fam"
INVITE_REWARD = 20
POINTS_PER_INR = 10
DB_PATH = "smm_bot.db"
CHANNEL_LINK = "https://t.me/+J7vhp-ifIW5iYjc1"

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
        (id INTEGER PRIMARY KEY, tg_id INTEGER UNIQUE, username TEXT, 
         points INTEGER DEFAULT 0, referrer_tg_id INTEGER, 
         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS purchases 
        (id TEXT PRIMARY KEY, user_tg_id INTEGER, amount REAL, points INTEGER, 
         status TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS referrals 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_tg_id INTEGER, 
         referee_tg_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders 
        (id TEXT PRIMARY KEY, user_tg_id INTEGER, service_name TEXT, 
         platform TEXT, quantity INTEGER, target TEXT, points_spent INTEGER, 
         status TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS withdrawals 
        (id TEXT PRIMARY KEY, user_tg_id INTEGER, amount INTEGER, 
         status TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()
    print("✅ Database ready!")

def db(query, params=(), fetch=False, one=False):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(query, params)
        res = c.fetchall() if fetch else None
        conn.commit()
        conn.close()
        if one and fetch:
            return res[0] if res else None
        return res
    except Exception as e:
        print(f"DB error: {e}")
        return None

init_db()

# ================= HELPERS =================
def admin_only(f):
    @wraps(f)
    async def wrapped(update, context):
        if update.effective_user.id != ADMIN_TG_ID:
            await update.message.reply_text("⚠️ Sirf admin ke liye.")
            return
        return await f(update, context)
    return wrapped

def menu():
    kb = [
        [KeyboardButton("🛒 New Order"), KeyboardButton("📦 Services")],
        [KeyboardButton("⭐ My Points"), KeyboardButton("📜 Orders")],
        [KeyboardButton("🔄 Status"), KeyboardButton("🎁 Invite & Earn")],
        [KeyboardButton("💳 Buy Points"), KeyboardButton("💰 Withdraw")],
        [KeyboardButton("📊 Stats"), KeyboardButton("ℹ️ Help")],
        [KeyboardButton("📢 Join Channel")]
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

SERVICES = {
    "telegram": {"name": "Telegram Members", "platform": "Telegram", "price": 1, "min": 10, "max": 200000},
    "instagram": {"name": "Instagram Followers", "platform": "Instagram", "price": 1, "min": 10, "max": 100000},
    "facebook": {"name": "Facebook Likes", "platform": "Facebook", "price": 1, "min": 10, "max": 50000},
    "twitter": {"name": "Twitter Followers", "platform": "Twitter", "price": 1, "min": 10, "max": 50000},
    "youtube": {"name": "YouTube Subs", "platform": "YouTube", "price": 2, "min": 10, "max": 10000},
    "tiktok": {"name": "TikTok Followers", "platform": "TikTok", "price": 1, "min": 10, "max": 50000}
}

def receipt(pid, uid, amt, pts, status, date):
    return f"""
╔══════════════════════════════════╗
║         💳 PAYMENT RECEIPT       ║
╠══════════════════════════════════╣
║ Transaction ID: {pid}
║ User ID: {uid}
║ Amount: ₹{amt}
║ Points: {pts}
║ Status: {status}
║ Date: {date}
╚══════════════════════════════════╝
"""

# ================= START =================
async def start(update, context):
    args = context.args
    user = update.effective_user
    tg_id = user.id
    username = user.username or user.full_name
    
    existing = db("SELECT tg_id, points FROM users WHERE tg_id = ?", (tg_id,), fetch=True, one=True)
    
    if not existing:
        referrer = None
        if args:
            try:
                rid = int(args[0])
                if rid != tg_id and db("SELECT tg_id FROM users WHERE tg_id = ?", (rid,), fetch=True):
                    referrer = rid
            except:
                pass
        
        db("INSERT INTO users (tg_id, username, referrer_tg_id) VALUES (?, ?, ?)", (tg_id, username, referrer))
        
        if referrer:
            db("INSERT INTO referrals (referrer_tg_id, referee_tg_id) VALUES (?, ?)", (referrer, tg_id))
            db("UPDATE users SET points = points + ? WHERE tg_id = ?", (INVITE_REWARD, referrer))
            try:
                await context.bot.send_message(referrer, f"🎉 {INVITE_REWARD} points added!\nSomeone used your referral link!")
            except:
                pass
    
    await update.message.reply_text(
        f"👋 Welcome {username}!\n\n"
        f"💰 1 INR = {POINTS_PER_INR} points\n"
        f"   ₹10 = 100 points\n"
        f"   ₹20 = 200 points\n"
        f"🎁 Referral = {INVITE_REWARD} points\n\n"
        f"📢 Join: {CHANNEL_LINK}\n\n"
        f"Select an option:",
        reply_markup=menu()
    )

# ================= TEXT HANDLER =================
async def text_handler(update, context):
    text = update.message.text
    tg_id = update.effective_user.id
    
    # JOIN CHANNEL
    if text == "📢 Join Channel":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ Joined", callback_data="joined")]
        ])
        await update.message.reply_text(
            f"📢 Join our channel:\n{CHANNEL_LINK}\n\nAfter joining click ✅ Joined",
            reply_markup=kb
        )
    
    # MY POINTS
    elif text == "⭐ My Points":
        pts = db("SELECT points FROM users WHERE tg_id = ?", (tg_id,), fetch=True, one=True)
        await update.message.reply_text(f"⭐ Your Points: {pts[0] if pts else 0}", reply_markup=menu())
    
    # INVITE & EARN
    elif text == "🎁 Invite & Earn":
        bot = (await context.bot.get_me()).username
        link = f"https://t.me/{bot}?start={tg_id}"
        refs = db("SELECT COUNT(*) FROM referrals WHERE referrer_tg_id = ?", (tg_id,), fetch=True)
        rc = refs[0][0] if refs else 0
        pts = db("SELECT points FROM users WHERE tg_id = ?", (tg_id,), fetch=True, one=True)
        cp = pts[0] if pts else 0
        
        await update.message.reply_text(
            f"🎁 Invite & Earn\n\n"
            f"🔗 Your Link:\n{link}\n\n"
            f"👥 Referrals: {rc}\n"
            f"⭐ Points: {cp}\n"
            f"🎁 Per Referral: {INVITE_REWARD} pts",
            reply_markup=menu()
        )
    
    # BUY POINTS
    elif text == "💳 Buy Points":
        await update.message.reply_text(
            f"💳 Buy Points\n\n"
            f"💰 1 INR = {POINTS_PER_INR} points\n"
            f"   ₹10 = 100 points\n"
            f"   ₹20 = 200 points\n"
            f"   ₹50 = 500 points\n"
            f"   ₹100 = 1000 points\n\n"
            f"📱 UPI ID: {UPI_ID}\n\n"
            f"Steps:\n"
            f"1️⃣ Send payment to UPI\n"
            f"2️⃣ Take screenshot\n"
            f"3️⃣ Send screenshot with caption: amount:10\n\n"
            f"✅ You'll get receipt after approval!",
            reply_markup=menu()
        )
    
    # SERVICES
    elif text == "📦 Services":
        msg = "📦 Services:\n\n"
        for k, s in SERVICES.items():
            msg += f"🔹 {s['name']}\n   Price: {s['price']} pts\n   Min: {s['min']} | Max: {s['max']}\n\n"
        await update.message.reply_text(msg, reply_markup=menu())
    
    # WITHDRAW
    elif text == "💰 Withdraw":
        pts = db("SELECT points FROM users WHERE tg_id = ?", (tg_id,), fetch=True, one=True)
        if pts and pts[0] >= 100:
            await update.message.reply_text("Enter points to withdraw (multiples of 100):")
            context.user_data['withdraw'] = True
        else:
            await update.message.reply_text("❌ Minimum 100 points required.", reply_markup=menu())
    
    # STATS
    elif text == "📊 Stats":
        pts = db("SELECT points FROM users WHERE tg_id = ?", (tg_id,), fetch=True, one=True)
        refs = db("SELECT COUNT(*) FROM referrals WHERE referrer_tg_id = ?", (tg_id,), fetch=True)
        orders = db("SELECT COUNT(*) FROM orders WHERE user_tg_id = ?", (tg_id,), fetch=True)
        await update.message.reply_text(
            f"📊 Stats:\n⭐ Points: {pts[0] if pts else 0}\n👥 Referrals: {refs[0][0] if refs else 0}\n📦 Orders: {orders[0][0] if orders else 0}",
            reply_markup=menu()
        )
    
    # NEW ORDER
    elif text == "🛒 New Order":
        kb = []
        for k, s in SERVICES.items():
            kb.append([InlineKeyboardButton(f"{s['platform']} - {s['name']}", callback_data=f"order_{k}")])
        kb.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
        await update.message.reply_text("Select service:", reply_markup=InlineKeyboardMarkup(kb))
    
    # ORDERS
    elif text == "📜 Orders":
        orders = db("SELECT id, platform, service_name, quantity, status FROM orders WHERE user_tg_id = ? ORDER BY created_at DESC LIMIT 5", (tg_id,), fetch=True)
        if orders:
            msg = "📜 Recent Orders:\n\n"
            for o in orders:
                msg += f"🔹 {o[0]}\n   {o[1]} | {o[2]}\n   Qty: {o[3]} | Status: {o[4]}\n\n"
            await update.message.reply_text(msg, reply_markup=menu())
        else:
            await update.message.reply_text("No orders yet.", reply_markup=menu())
    
    # STATUS
    elif text == "🔄 Status":
        await update.message.reply_text("Send Order ID to check status:")
    
    # HELP
    elif text == "ℹ️ Help":
        await update.message.reply_text(
            "🤖 Bot Guide:\n\n"
            "1️⃣ New Order - Get members/followers\n"
            "2️⃣ Services - View all services\n"
            "3️⃣ My Points - Check balance\n"
            "4️⃣ Orders - View history\n"
            "5️⃣ Status - Check order\n"
            "6️⃣ Invite & Earn - Referral (20 pts)\n"
            "7️⃣ Buy Points - UPI payment\n"
            "8️⃣ Withdraw - Cash out\n"
            "9️⃣ Join Channel - Get updates",
            reply_markup=menu()
        )
    
    # ORDER ID / WITHDRAW INPUT
    else:
        if re.fullmatch(r"[0-9a-fA-F]{8}", text):
            order = db("SELECT status, service_name, quantity FROM orders WHERE id = ? AND user_tg_id = ?", (text, tg_id), fetch=True, one=True)
            if order:
                await update.message.reply_text(f"Order {text}: {order[1]} x {order[2]} - {order[0]}", reply_markup=menu())
                return
        
        if context.user_data.get('withdraw'):
            try:
                pts = int(text)
                if pts % 100 == 0 and pts >= 100:
                    cur = db("SELECT points FROM users WHERE tg_id = ?", (tg_id,), fetch=True, one=True)
                    if cur and cur[0] >= pts:
                        wid = str(uuid4())[:8]
                        db("INSERT INTO withdrawals (id, user_tg_id, amount, status) VALUES (?, ?, ?, ?)", (wid, tg_id, pts, "PENDING"))
                        await context.bot.send_message(ADMIN_TG_ID, f"💰 Withdrawal: {wid}\nUser: {tg_id}\nPoints: {pts}")
                        await update.message.reply_text(f"✅ Withdrawal requested!\nID: {wid}", reply_markup=menu())
                    else:
                        await update.message.reply_text("❌ Insufficient points.", reply_markup=menu())
                else:
                    await update.message.reply_text("❌ Enter multiples of 100.", reply_markup=menu())
            except:
                await update.message.reply_text("❌ Invalid number.", reply_markup=menu())
            context.user_data['withdraw'] = False

# ================= PHOTO HANDLER =================
async def photo_handler(update, context):
    cap = (update.message.caption or "").lower()
    m = re.search(r"amount\s*[:=]\s*(\d+)", cap)
    if not m:
        await update.message.reply_text("❌ Add caption: amount:10", reply_markup=menu())
        return
    
    amount = float(m.group(1))
    pts = int(amount * POINTS_PER_INR)
    pid = str(uuid4())[:8]
    tg_id = update.effective_user.id
    username = update.effective_user.username or "User"
    date = datetime.now().strftime("%d-%m-%Y %H:%M")
    
    db("INSERT INTO purchases (id, user_tg_id, amount, points, status) VALUES (?, ?, ?, ?, ?)", (pid, tg_id, amount, pts, "PENDING"))
    await context.bot.forward_message(ADMIN_TG_ID, update.message.chat_id, update.message.message_id)
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{pid}"),
         InlineKeyboardButton("❌ Reject", callback_data=f"reject_{pid}")]
    ])
    
    await context.bot.send_message(ADMIN_TG_ID, f"💰 New Payment\nID: {pid}\nUser: {tg_id} (@{username})\nAmount: ₹{amount}\nPoints: {pts}", reply_markup=kb)
    
    r = receipt(pid, tg_id, amount, pts, "PENDING", date)
    await update.message.reply_text(
        f"✅ Payment Received!\n\n"
        f"📋 Payment being verified.\n"
        f"You'll get {pts} points after approval.\n\n"
        f"📄 Receipt:\n{r}\n\n"
        f"⏳ Status: PENDING",
        reply_markup=menu()
    )

# ================= CALLBACK HANDLER =================
async def callback_handler(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    date = datetime.now().strftime("%d-%m-%Y %H:%M")
    
    if data == "joined":
        await query.edit_message_text("✅ Thank you for joining!\n\nNow use the bot:", reply_markup=menu())
        return
    
    if data.startswith("approve_") or data.startswith("reject_"):
        if update.effective_user.id != ADMIN_TG_ID:
            await query.edit_message_text("⚠️ Admin only")
            return
        
        action, pid = data.split("_", 1)
        p = db("SELECT user_tg_id, points, amount, status FROM purchases WHERE id = ?", (pid,), fetch=True, one=True)
        if not p or p[3] != "PENDING":
            await query.edit_message_text("Already processed")
            return
        
        uid, points, amount, status = p
        
        if action == "approve":
            db("UPDATE users SET points = points + ? WHERE tg_id = ?", (points, uid))
            db("UPDATE purchases SET status = 'APPROVED' WHERE id = ?", (pid,))
            r = receipt(pid, uid, amount, points, "✅ APPROVED", date)
            try:
                await context.bot.send_message(uid, f"✅ Payment Approved!\n\n⭐ {points} points added!\n\n📄 Receipt:\n{r}", reply_markup=menu())
            except:
                pass
            await query.edit_message_text(f"✅ Approved {pid}")
        else:
            db("UPDATE purchases SET status = 'REJECTED' WHERE id = ?", (pid,))
            r = receipt(pid, uid, amount, points, "❌ REJECTED", date)
            try:
                await context.bot.send_message(uid, f"❌ Payment Rejected!\n\n📄 Receipt:\n{r}", reply_markup=menu())
            except:
                pass
            await query.edit_message_text(f"❌ Rejected {pid}")
        return
    
    if data.startswith("order_"):
        key = data.split("_", 1)[1]
        context.user_data['service'] = key
        s = SERVICES[key]
        await query.edit_message_text(
            f"📌 {s['name']}\nPlatform: {s['platform']}\nPrice: {s['price']} pts/member\nMin: {s['min']} | Max: {s['max']}\n\nEnter quantity:"
        )
        return
    
    if data == "cancel":
        await query.edit_message_text("❌ Cancelled")

# ================= ORDER FLOW =================
async def order_input(update, context):
    if 'service' not in context.user_data:
        return
    try:
        qty = int(update.message.text)
        key = context.user_data['service']
        s = SERVICES[key]
        
        if qty < s['min'] or qty > s['max']:
            await update.message.reply_text(f"❌ Min: {s['min']} Max: {s['max']}")
            return
        
        total = int(qty * s['price'])
        tg_id = update.effective_user.id
        pts = db("SELECT points FROM users WHERE tg_id = ?", (tg_id,), fetch=True, one=True)
        
        if not pts or pts[0] < total:
            await update.message.reply_text(f"❌ Need {total} pts, you have {pts[0] if pts else 0}")
            return
        
        context.user_data['order_qty'] = qty
        context.user_data['order_total'] = total
        await update.message.reply_text("Enter target (username/link):")
    except ValueError:
        await update.message.reply_text("❌ Enter a valid number")

async def target_input(update, context):
    if 'service' not in context.user_data or 'order_qty' not in context.user_data:
        return
    
    target = update.message.text
    key = context.user_data.pop('service')
    qty = context.user_data.pop('order_qty')
    total = context.user_data.pop('order_total')
    tg_id = update.effective_user.id
    
    s = SERVICES[key]
    oid = str(uuid4())[:8]
    
    db("UPDATE users SET points = points - ? WHERE tg_id = ?", (total, tg_id))
    db("INSERT INTO orders (id, user_tg_id, service_name, platform, quantity, target, points_spent, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
       (oid, tg_id, s['name'], s['platform'], qty, target, total, "PENDING"))
    
    await context.bot.send_message(ADMIN_TG_ID, f"📦 New Order: {oid}\nUser: {tg_id}\nService: {s['name']}\nQty: {qty}\nTarget: {target}\nPoints: {total}")
    await update.message.reply_text(
        f"✅ Order placed!\n\n"
        f"📋 ID: {oid}\n"
        f"Platform: {s['platform']}\n"
        f"Service: {s['name']}\n"
        f"Qty: {qty}\n"
        f"Target: {target}\n"
        f"Points: {total}\n"
        f"Status: PENDING",
        reply_markup=menu()
    )

# ================= ADMIN =================
@admin_only
async def update_order(update, context):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /update_order ORDER_ID STATUS")
        return
    
    db("UPDATE orders SET status = ? WHERE id = ?", (args[1].upper(), args[0]))
    order = db("SELECT user_tg_id FROM orders WHERE id = ?", (args[0],), fetch=True, one=True)
    
    if order:
        try:
            await context.bot.send_message(order[0], f"🔄 Order {args[0]} status: {args[1].upper()}", reply_markup=menu())
        except:
            pass
    
    await update.message.reply_text(f"✅ Order {args[0]} updated to {args[1].upper()}")

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("update_order", update_order))
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, order_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, target_input))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    print("=" * 40)
    print("🤖 Bot is running!")
    print(f"💰 1 INR = {POINTS_PER_INR} points")
    print(f"🎁 Referral = {INVITE_REWARD} po