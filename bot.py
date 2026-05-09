import logging
import os
import uuid
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

# ─────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────
BOT_TOKEN           = "8635925049:AAGQmYXxJO46sAlDwqUHrYn_Gji13rBmnIA"
NOWPAYMENTS_API_KEY = "PXZH1F1-BEH4YKA-HJB3Y2A-J0EVFGH"
NOWPAYMENTS_BASE    = "https://api.nowpayments.io/v1"
ADMIN_ID            = 8774834097

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
#  ACCESS LINKS — edit these after each payment is confirmed
#  For plans/vip/courses: Telegram invite links
#  For tools: instructions sent automatically
# ─────────────────────────────────────────
ACCESS_LINKS = {
    # ── Subscription Plans ──
    "plan_1w":   "https://t.me/+YOUR_1WEEK_INVITE_LINK",    # ← replace
    "plan_1m":   "https://t.me/+YOUR_1MONTH_INVITE_LINK",   # ← replace
    "plan_3m":   "https://t.me/+YOUR_3MONTH_INVITE_LINK",   # ← replace
    "plan_life": "https://t.me/+YOUR_LIFETIME_INVITE_LINK", # ← replace

    # ── VIP Channels ──
    "vip_1": "https://t.me/+YOUR_VIP_BASIC_LINK",           # ← replace
    "vip_2": "https://t.me/+YOUR_VIP_PREMIUM_LINK",         # ← replace

    # ── Courses ──
    "course_1": "https://t.me/+YOUR_STARTER_COURSE_LINK",   # ← replace
    "course_2": "https://t.me/+YOUR_ADVANCED_COURSE_LINK",  # ← replace

    # ── Tools — automatic message sent to buyer ──
    "tool_1": (
        "✅ *Thank you for purchasing Pro Tool!*\n\n"
        "Here are your access instructions:\n\n"
        "1️⃣ Step one — edit this message\n"
        "2️⃣ Step two — edit this message\n"
        "3️⃣ Step three — edit this message\n\n"
        "If you need help, contact support."
    ),
    "tool_2": (
        "✅ *Thank you for purchasing Tools Bundle!*\n\n"
        "Here are your access instructions:\n\n"
        "1️⃣ Step one — edit this message\n"
        "2️⃣ Step two — edit this message\n"
        "3️⃣ Step three — edit this message\n\n"
        "If you need help, contact support."
    ),
}

# ─────────────────────────────────────────
#  PRODUCT CATALOG
# ─────────────────────────────────────────
PLANS = {
    "plan_1w":   {"name": "⚡ 1 Week",   "price": 25.00,  "desc": "Full access for 7 days"},
    "plan_1m":   {"name": "📅 1 Month",  "price": 55.00,  "desc": "Full access for 30 days"},
    "plan_3m":   {"name": "🚀 3 Months", "price": 120.00, "desc": "Full access for 90 days"},
    "plan_life": {"name": "♾️ Lifetime", "price": 300.00, "desc": "Lifetime access — pay once, keep forever"},
}

TOOLS = {
    "tool_1": {"name": "🛠️ Pro Tool",     "price": 50.00, "desc": "Premium tool — edit description later"},
    "tool_2": {"name": "⚙️ Tools Bundle", "price": 50.00, "desc": "Full tools pack — edit description later"},
}

VIP_CHANNELS = {
    "vip_1": {"name": "📢 VIP Channel Basic",   "price": 8.00,  "desc": "VIP channel access — tier 1"},
    "vip_2": {"name": "👑 VIP Channel Premium", "price": 18.00, "desc": "VIP channel access — tier 2"},
}

COURSES = {
    "course_1": {"name": "📚 Starter Course",  "price": 25.00, "desc": "Introductory course"},
    "course_2": {"name": "🎓 Advanced Course", "price": 50.00, "desc": "Advanced level course"},
}

SUPPORT = {
    "support_1": {"name": "💬 Basic Support",   "price": 12.00, "desc": "Support for 30 days"},
    "support_2": {"name": "🏆 Premium Support", "price": 30.00, "desc": "Unlimited support for 90 days"},
}

ALL_PRODUCTS = {**PLANS, **TOOLS, **VIP_CHANNELS, **COURSES, **SUPPORT}
TOOL_KEYS    = set(TOOLS.keys())

# ─────────────────────────────────────────
#  NOWPAYMENTS HELPER
# ─────────────────────────────────────────
def create_payment(amount: float, product_name: str, order_id: str) -> dict | None:
    headers = {
        "x-api-key": NOWPAYMENTS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "price_amount": amount,
        "price_currency": "usd",
        "pay_currency": "usdttrc20",
        "order_id": order_id,
        "order_description": product_name,
        "ipn_callback_url": "",
    }
    try:
        r = requests.post(f"{NOWPAYMENTS_BASE}/payment", json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error(f"NOWPayments error: {e}")
        return None

# ─────────────────────────────────────────
#  SEND ACCESS — called after payment confirmed
# ─────────────────────────────────────────
async def send_access(bot, chat_id: int, product_key: str, prod: dict):
    access = ACCESS_LINKS.get(product_key)
    if not access:
        await bot.send_message(chat_id, "✅ Payment confirmed! Contact support to receive your access.")
        return

    if product_key in TOOL_KEYS:
        # Tools: send the instruction message directly
        await bot.send_message(chat_id, access, parse_mode="Markdown")
    else:
        # Plans / VIP / Courses: send Telegram invite link
        await bot.send_message(
            chat_id,
            f"✅ *Payment confirmed!*\n\n"
            f"🎉 Here is your access link for *{prod['name']}*:\n\n"
            f"👉 {access}\n\n"
            f"⚠️ This link is personal — do not share it.",
            parse_mode="Markdown"
        )

# ─────────────────────────────────────────
#  KEYBOARDS
# ─────────────────────────────────────────
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Subscription Plans", callback_data="cat_plans")],
        [InlineKeyboardButton("🛠️ Tools",              callback_data="cat_tools")],
        [InlineKeyboardButton("📢 VIP Channels",       callback_data="cat_vip")],
        [InlineKeyboardButton("📚 Courses",            callback_data="cat_courses")],
        [InlineKeyboardButton("💬 Support",            callback_data="cat_support")],
    ])

def category_keyboard(products: dict, back_cb: str = "menu"):
    rows = [[InlineKeyboardButton(p["name"], callback_data=key)] for key, p in products.items()]
    rows.append([InlineKeyboardButton("🔙 Back", callback_data=back_cb)])
    return InlineKeyboardMarkup(rows)

def product_keyboard(product_key: str, back_cb: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Pay with Crypto", callback_data=f"pay_{product_key}")],
        [InlineKeyboardButton("🔙 Back",            callback_data=back_cb)],
    ])

# ─────────────────────────────────────────
#  HANDLERS
# ─────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"👋 Hey, {user.first_name}!\n\n"
        "Welcome to our services & payments bot.\n"
        "Choose a category to get started:"
    )
    await update.message.reply_text(text, reply_markup=main_menu_keyboard())

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu":
        await query.edit_message_text(
            "🏠 Main Menu — choose a category:",
            reply_markup=main_menu_keyboard()
        )
    elif data == "cat_plans":
        await query.edit_message_text(
            "📦 *Subscription Plans*\n\nChoose the plan that fits you best:",
            parse_mode="Markdown",
            reply_markup=category_keyboard(PLANS, "menu")
        )
    elif data == "cat_tools":
        await query.edit_message_text(
            "🛠️ *Tools*\n\nOur premium tools:",
            parse_mode="Markdown",
            reply_markup=category_keyboard(TOOLS, "menu")
        )
    elif data == "cat_vip":
        await query.edit_message_text(
            "📢 *VIP Channels*\n\nGet access to exclusive content:",
            parse_mode="Markdown",
            reply_markup=category_keyboard(VIP_CHANNELS, "menu")
        )
    elif data == "cat_courses":
        await query.edit_message_text(
            "📚 *Courses*\n\nSpecialized training:",
            parse_mode="Markdown",
            reply_markup=category_keyboard(COURSES, "menu")
        )
    elif data == "cat_support":
        await query.edit_message_text(
            "💬 *Support*\n\nPersonalized support plans:",
            parse_mode="Markdown",
            reply_markup=category_keyboard(SUPPORT, "menu")
        )
    elif data in ALL_PRODUCTS:
        prod = ALL_PRODUCTS[data]
        back = (
            "cat_plans"   if data in PLANS else
            "cat_tools"   if data in TOOLS else
            "cat_vip"     if data in VIP_CHANNELS else
            "cat_courses" if data in COURSES else
            "cat_support"
        )
        await query.edit_message_text(
            f"{prod['name']}\n\n"
            f"📝 {prod['desc']}\n"
            f"💰 Price: *${prod['price']:.2f} USD*\n\n"
            "Pay securely with cryptocurrency via NOWPayments.",
            parse_mode="Markdown",
            reply_markup=product_keyboard(data, back)
        )
    elif data.startswith("pay_"):
        product_key = data[4:]
        if product_key not in ALL_PRODUCTS:
            await query.edit_message_text("❌ Product not found.")
            return

        prod     = ALL_PRODUCTS[product_key]
        order_id = str(uuid.uuid4())[:8].upper()

        await query.edit_message_text("⏳ Generating your payment, please wait...")

        payment = create_payment(prod["price"], prod["name"], order_id)

        if not payment:
            await query.edit_message_text(
                "❌ Error connecting to the payment processor. Please try again later.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to menu", callback_data="menu")
                ]])
            )
            return

        pay_address  = payment.get("pay_address", "N/A")
        pay_amount   = payment.get("pay_amount", "N/A")
        pay_currency = payment.get("pay_currency", "crypto").upper()
        payment_id   = payment.get("payment_id", order_id)

        # Store pending payment in bot_data for webhook confirmation
        ctx.bot_data.setdefault("pending", {})[order_id] = {
            "chat_id":     query.from_user.id,
            "product_key": product_key,
            "prod":        prod,
            "payment_id":  payment_id,
        }

        await query.edit_message_text(
            f"✅ *Payment generated successfully*\n\n"
            f"🛒 Product: {prod['name']}\n"
            f"💰 Total: *${prod['price']:.2f} USD*\n"
            f"🔑 Order ID: `{order_id}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📤 Send exactly:\n"
            f"`{pay_amount}` *{pay_currency}*\n\n"
            f"📋 To this address:\n"
            f"`{pay_address}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⚠️ Payment expires in 60 minutes.\n"
            f"Once confirmed, you'll receive your access link automatically.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to menu", callback_data="menu")
            ]])
        )

        # Notify admin
        try:
            await ctx.bot.send_message(
                ADMIN_ID,
                f"🆕 New payment initiated\n"
                f"👤 User: @{query.from_user.username or query.from_user.id}\n"
                f"🛒 Product: {prod['name']}\n"
                f"💵 Amount: ${prod['price']:.2f} USD\n"
                f"🔑 Order ID: {order_id}\n"
                f"🆔 Payment ID: {payment_id}"
            )
        except Exception:
            pass

# ─────────────────────────────────────────
#  ADMIN COMMAND: /confirm <order_id>
#  Use this to manually confirm a payment
#  and send the access link to the buyer
# ─────────────────────────────────────────
async def confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not ctx.args:
        await update.message.reply_text("Usage: /confirm <ORDER_ID>")
        return

    order_id = ctx.args[0].upper()
    pending  = ctx.bot_data.get("pending", {})

    if order_id not in pending:
        await update.message.reply_text(f"❌ Order `{order_id}` not found.", parse_mode="Markdown")
        return

    info        = pending.pop(order_id)
    chat_id     = info["chat_id"]
    product_key = info["product_key"]
    prod        = info["prod"]

    await send_access(ctx.bot, chat_id, product_key, prod)
    await update.message.reply_text(f"✅ Access sent to user for order `{order_id}`.", parse_mode="Markdown")

# ─────────────────────────────────────────
#  STARTUP
# ─────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("confirm", confirm))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))

    logger.info("🤖 Bot started with polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
