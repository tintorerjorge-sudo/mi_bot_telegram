import logging
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
NOWPAYMENTS_IPN_KEY = "pBlLEEBbskZxVnKEa7GulspBv/Ladb7Q"
NOWPAYMENTS_BASE    = "https://api.nowpayments.io/v1"
ADMIN_ID            = 8774834097
SUPPORT_LINK        = "https://t.me/cypheeer"
TOOLS_PREVIEW_LINK  = "https://t.me/+pKSnJlsioSIyMmY0"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
#  AVAILABLE CRYPTOS
# ─────────────────────────────────────────
CRYPTOS = {
    "btc":       "₿ Bitcoin (BTC)",
    "eth":       "Ξ Ethereum (ETH)",
    "usdttrc20": "💵 USDT TRC20",
    "usdterc20": "💵 USDT ERC20",
    "ltc":       "Ł Litecoin (LTC)",
    "xrp":       "◈ XRP",
    "sol":       "◎ Solana (SOL)",
    "bnbbsc":    "🔶 BNB (BSC)",
    "trx":       "🔺 TRON (TRX)",
    "doge":      "🐶 Dogecoin (DOGE)",
}

# ─────────────────────────────────────────
#  ACCESS MESSAGES
# ─────────────────────────────────────────
SUBSCRIPTION_LINK = "https://t.me/+5qbVUN5pklYzYzBk"

SUBSCRIPTION_ACCESS = (
    "✅ *Payment Confirmed — Welcome!*\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🔗 *Your Private Access Link:*\n"
    f"👉 {SUBSCRIPTION_LINK}\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "📋 *How to get in:*\n"
    "1️⃣ Tap the link above to request access\n"
    "2️⃣ The admin will verify your transaction\n"
    "3️⃣ Once approved, you're in — enjoy!\n\n"
    "⚠️ *This link is personal. Do not share it.*\n"
    f"💬 Support: {SUPPORT_LINK}"
)

COURSE_ACCESS = (
    "✅ *Payment Confirmed — Lifetime Access Granted!*\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🔗 *Your Private Access Link:*\n"
    f"👉 {SUBSCRIPTION_LINK}\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "📋 *What happens next:*\n"
    "1️⃣ Tap the link and request to join\n"
    "2️⃣ The admin verifies your transaction\n"
    "3️⃣ Once accepted, you get full lifetime access\n"
    "4️⃣ The owner will connect via AnyDesk to set everything up for you — one click and it runs on its own\n\n"
    "⚠️ *This link is personal. Do not share it.*\n"
    f"💬 Support: {SUPPORT_LINK}"
)

ACCESS_LINKS = {
    "plan_1w":   SUBSCRIPTION_ACCESS,
    "plan_1m":   SUBSCRIPTION_ACCESS,
    "plan_3m":   SUBSCRIPTION_ACCESS,
    "plan_life": SUBSCRIPTION_ACCESS,
    "course_1":  COURSE_ACCESS,
    "support_1": SUBSCRIPTION_ACCESS,
    "support_2": SUBSCRIPTION_ACCESS,
}

# ─────────────────────────────────────────
#  PRODUCT CATALOG
# ─────────────────────────────────────────
PLANS = {
    "plan_1w":   {"name": "⚡ 1 Week",    "price": 25.00,  "desc": "Full access for 7 days"},
    "plan_1m":   {"name": "📅 1 Month",   "price": 55.00,  "desc": "Full access for 30 days"},
    "plan_3m":   {"name": "🚀 3 Months",  "price": 120.00, "desc": "Full access for 90 days"},
    "plan_life": {"name": "♾️ Lifetime",  "price": 300.00, "desc": "Lifetime access — pay once, keep forever"},
}

COURSES = {
    "course_1": {
        "name":  "🖥️ Build Your Own Cloud",
        "price": 200.00,
        "desc":  (
            "Get *all tools included — lifetime access.*\n\n"
            "Everything you need to build and run your own cloud infrastructure:\n"
            "• Full video library & documentation\n"
            "• All tools unlocked forever\n"
            "• The owner connects via *AnyDesk* to set it all up for you\n"
            "• One click and it runs on its own — fully automated\n\n"
            "💡 _You own it. No subscriptions. No limits._"
        ),
    },
}

SUPPORT_PLANS = {
    "support_1": {"name": "💬 Standard Support",  "price": 12.00, "desc": "Priority support for 30 days"},
    "support_2": {"name": "🏆 Premium Support",   "price": 30.00, "desc": "Dedicated support for 90 days — fastest response time"},
}

ALL_PRODUCTS = {**PLANS, **COURSES, **SUPPORT_PLANS}

# ─────────────────────────────────────────
#  NOWPAYMENTS
# ─────────────────────────────────────────
def get_available_currencies() -> list:
    try:
        r = requests.get(
            f"{NOWPAYMENTS_BASE}/currencies?fixed_rate=true",
            headers={"x-api-key": NOWPAYMENTS_API_KEY},
            timeout=10
        )
        r.raise_for_status()
        available = [c.lower() for c in r.json().get("currencies", [])]
        return [k for k in CRYPTOS if k in available] or list(CRYPTOS.keys())
    except Exception as e:
        logger.error(f"Currency fetch error: {e}")
        return list(CRYPTOS.keys())

def create_payment(amount: float, product_name: str, order_id: str, pay_currency: str) -> dict | None:
    headers = {"x-api-key": NOWPAYMENTS_API_KEY, "Content-Type": "application/json"}
    payload = {
        "price_amount":        amount,
        "price_currency":      "usd",
        "pay_currency":        pay_currency,
        "order_id":            order_id,
        "order_description":   product_name,
        "is_fee_paid_by_user": True,
    }
    try:
        r = requests.post(f"{NOWPAYMENTS_BASE}/payment", json=payload, headers=headers, timeout=15)
        logger.info(f"NOWPayments {r.status_code}: {r.text}")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error(f"NOWPayments error: {e}")
        return None

# ─────────────────────────────────────────
#  SEND ACCESS
# ─────────────────────────────────────────
async def send_access(bot, chat_id: int, product_key: str, prod: dict):
    message = ACCESS_LINKS.get(product_key)
    if not message:
        await bot.send_message(chat_id, f"✅ Payment confirmed for *{prod['name']}*!\n💬 Support: {SUPPORT_LINK}", parse_mode="Markdown")
        return
    await bot.send_message(chat_id, message, parse_mode="Markdown")

# ─────────────────────────────────────────
#  KEYBOARDS
# ─────────────────────────────────────────
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦  Subscription Plans", callback_data="cat_plans")],
        [InlineKeyboardButton("🛠️  Tools & Software",   callback_data="cat_tools")],
        [InlineKeyboardButton("🖥️  Build Your Cloud",   callback_data="cat_courses")],
        [InlineKeyboardButton("🏆  Support",            callback_data="cat_support")],
        [InlineKeyboardButton("📞  Contact Us",         callback_data="cat_contact")],
    ])

def category_keyboard(products: dict, back_cb: str = "menu"):
    rows = [[InlineKeyboardButton(p["name"], callback_data=key)] for key, p in products.items()]
    rows.append([InlineKeyboardButton("⬅️  Back to Menu", callback_data=back_cb)])
    return InlineKeyboardMarkup(rows)

def product_keyboard(product_key: str, back_cb: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳  Pay with Crypto", callback_data=f"choosecrypto_{product_key}")],
        [InlineKeyboardButton("⬅️  Back",            callback_data=back_cb)],
    ])

def crypto_keyboard(product_key: str, available: list):
    rows = []
    for i in range(0, len(available), 2):
        row = []
        for key in available[i:i+2]:
            label = CRYPTOS.get(key, key.upper())
            row.append(InlineKeyboardButton(label, callback_data=f"pay_{product_key}_{key}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("⬅️  Back", callback_data=product_key)])
    return InlineKeyboardMarkup(rows)

# ─────────────────────────────────────────
#  HANDLERS
# ─────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"👋 *Welcome, {user.first_name}!*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ *Cypher Services* — your gateway to premium cloud tools, automation, and private access.\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Select a category below to get started:"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu":
        await query.edit_message_text(
            "🏠 *Main Menu*\n\nSelect a category below:",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )

    elif data == "cat_plans":
        await query.edit_message_text(
            "📦 *Subscription Plans*\n\n"
            "Get full access to our private network.\n"
            "All plans include the same premium features — choose what fits your budget:\n\n"
            "⚡ 1 Week — $25\n"
            "📅 1 Month — $55\n"
            "🚀 3 Months — $120\n"
            "♾️ Lifetime — $300",
            parse_mode="Markdown",
            reply_markup=category_keyboard(PLANS, "menu")
        )

    elif data == "cat_tools":
        await query.edit_message_text(
            "🛠️ *Tools & Software*\n\n"
            "Browse our full suite of premium tools — *completely free to preview.*\n\n"
            "👀 Tap below to explore everything available in our tools channel:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔓  View All Tools (Free)", url=TOOLS_PREVIEW_LINK)],
                [InlineKeyboardButton("⬅️  Back to Menu", callback_data="menu")],
            ])
        )

    elif data == "cat_courses":
        prod = COURSES["course_1"]
        await query.edit_message_text(
            f"🖥️ *Build Your Own Cloud*\n\n"
            f"{prod['desc']}\n\n"
            f"💰 One-time payment: *$200 USD*",
            parse_mode="Markdown",
            reply_markup=product_keyboard("course_1", "menu")
        )

    elif data == "cat_support":
        await query.edit_message_text(
            "🏆 *Support Plans*\n\n"
            "Get direct access to our team.\n\n"
            "💬 *Standard Support* — $12 / 30 days\n"
            "_Priority response, issue resolution & guidance._\n\n"
            "🏆 *Premium Support* — $30 / 90 days\n"
            "_Dedicated agent, fastest response, full assistance._",
            parse_mode="Markdown",
            reply_markup=category_keyboard(SUPPORT_PLANS, "menu")
        )

    elif data == "cat_contact":
        await query.edit_message_text(
            "📞 *Contact & Support*\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Our team is available to assist you with:\n"
            "• Pre-sale questions\n"
            "• Technical issues\n"
            "• Account & access problems\n"
            "• Custom requests\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 Reach us directly: {SUPPORT_LINK}\n\n"
            "⏱ _Typical response time: under 2 hours_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬  Open Support Chat", url=SUPPORT_LINK)],
                [InlineKeyboardButton("⬅️  Back to Menu", callback_data="menu")],
            ])
        )

    elif data in ALL_PRODUCTS:
        prod = ALL_PRODUCTS[data]
        back = "cat_plans" if data in PLANS else "cat_courses" if data in COURSES else "cat_support"
        desc = prod["desc"] if data in COURSES else f"📝 {prod['desc']}"
        await query.edit_message_text(
            f"{'🖥️' if data in COURSES else '📦'} *{prod['name']}*\n\n"
            f"{desc}\n\n"
            f"💰 Price: *${prod['price']:.2f} USD*\n\n"
            "All payments are processed securely via *NOWPayments*.\n"
            "_You choose your preferred cryptocurrency._",
            parse_mode="Markdown",
            reply_markup=product_keyboard(data, back)
        )

    elif data.startswith("choosecrypto_"):
        product_key = data[len("choosecrypto_"):]
        if product_key not in ALL_PRODUCTS:
            await query.edit_message_text("❌ Product not found.")
            return
        prod = ALL_PRODUCTS[product_key]
        await query.edit_message_text("⏳ Loading available currencies...")
        available = get_available_currencies()
        await query.edit_message_text(
            f"💳 *Select Payment Currency*\n\n"
            f"🛒 {prod['name']}\n"
            f"💰 *${prod['price']:.2f} USD*\n\n"
            "Choose your preferred crypto below.\n"
            "_Network fees are covered by the buyer._",
            parse_mode="Markdown",
            reply_markup=crypto_keyboard(product_key, available)
        )

    elif data.startswith("cancel_"):
        order_id = data[len("cancel_"):]
        pending  = ctx.bot_data.get("pending", {})
        user_id  = query.from_user.id
        to_delete = [oid for oid, info in pending.items() if info["chat_id"] == user_id and oid == order_id]
        for oid in to_delete:
            del pending[oid]
        await query.edit_message_text(
            "🚫 *Transaction Cancelled*\n\n"
            "Your pending payment has been cancelled.\n"
            "You can start a new one anytime.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠  Back to Menu", callback_data="menu")]])
        )

    elif data.startswith("pay_"):
        parts = data[4:].rsplit("_", 1)
        if len(parts) != 2:
            await query.edit_message_text("❌ Invalid selection.")
            return
        product_key, crypto = parts[0], parts[1]

        if product_key not in ALL_PRODUCTS:
            await query.edit_message_text("❌ Product not found.")
            return

        # ── One pending transaction per user ──
        user_id = query.from_user.id
        pending = ctx.bot_data.setdefault("pending", {})
        existing = {oid: info for oid, info in pending.items() if info["chat_id"] == user_id}
        if existing:
            oid, info = next(iter(existing.items()))
            await query.edit_message_text(
                "⚠️ *You already have a pending transaction.*\n\n"
                f"🛒 Product: *{info['prod']['name']}*\n"
                f"🔑 Order ID: `{oid}`\n\n"
                "Please complete or cancel your current payment before starting a new one.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"🚫  Cancel order {oid}", callback_data=f"cancel_{oid}")],
                    [InlineKeyboardButton("⬅️  Back to Menu", callback_data="menu")],
                ])
            )
            return

        prod     = ALL_PRODUCTS[product_key]
        order_id = str(uuid.uuid4())[:8].upper()

        await query.edit_message_text("⏳ *Generating your invoice...*\nThis takes just a moment.", parse_mode="Markdown")

        payment = create_payment(prod["price"], prod["name"], order_id, crypto)

        if not payment:
            await query.edit_message_text(
                "❌ *Payment generation failed.*\n\n"
                "This may be a temporary issue. Please try again or contact support.\n\n"
                f"💬 {SUPPORT_LINK}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️  Back to Menu", callback_data="menu")]])
            )
            return

        pay_address  = payment.get("pay_address", "N/A")
        pay_amount   = payment.get("pay_amount", "N/A")
        pay_currency = payment.get("pay_currency", crypto).upper()
        payment_id   = payment.get("payment_id", order_id)

        ctx.bot_data.setdefault("pending", {})[order_id] = {
            "chat_id":     query.from_user.id,
            "product_key": product_key,
            "prod":        prod,
            "payment_id":  payment_id,
        }

        await query.edit_message_text(
            f"✅ *Invoice Generated*\n\n"
            f"🛒 *{prod['name']}*\n"
            f"💰 Amount: *${prod['price']:.2f} USD*\n"
            f"🔑 Order ID: `{order_id}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📤 *Send exactly:*\n"
            f"`{pay_amount}` {pay_currency}\n\n"
            f"📋 *To this address:*\n"
            f"`{pay_address}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⏱ Expires in *60 minutes*\n"
            f"🔔 You'll receive your access link automatically once payment is confirmed.\n\n"
            f"💬 Issues? {SUPPORT_LINK}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️  Back to Menu", callback_data="menu")]])
        )

        try:
            await ctx.bot.send_message(
                ADMIN_ID,
                f"🆕 *New Payment Initiated*\n\n"
                f"👤 User: @{query.from_user.username or query.from_user.id}\n"
                f"🛒 Product: {prod['name']}\n"
                f"💵 Amount: ${prod['price']:.2f} USD\n"
                f"💎 Crypto: {pay_currency}\n"
                f"🔑 Order ID: `{order_id}`\n"
                f"🆔 Payment ID: {payment_id}\n\n"
                f"✅ To confirm: `/confirm {order_id}`",
                parse_mode="Markdown"
            )
        except Exception:
            pass

# ─────────────────────────────────────────
#  ADMIN: /confirm <order_id>
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
    await update.message.reply_text(f"✅ Access sent for order `{order_id}`.", parse_mode="Markdown")

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
