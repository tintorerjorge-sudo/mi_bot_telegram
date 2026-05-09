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
#  CONFIGURACIÓN — edita estos valores
# ─────────────────────────────────────────
BOT_TOKEN = "8635925049:AAGQmYXxJO46sAlDwqUHrYn_Gji13rBmnIA"
NOWPAYMENTS_API_KEY = "PXZH1F1-BEH4YKA-HJB3Y2A-J0EVFGH"          # ← pega tu key aquí
NOWPAYMENTS_BASE    = "https://api.nowpayments.io/v1"
ADMIN_ID            = 8774834097                   # ← tu Telegram user ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
#  CATÁLOGO DE PRODUCTOS
# ─────────────────────────────────────────
PLANS = {
    "plan_1w":  {"name": "⚡ 1 Semana",   "price": 5.00,  "desc": "Acceso completo 7 días"},
    "plan_1m":  {"name": "📅 1 Mes",      "price": 15.00, "desc": "Acceso completo 30 días"},
    "plan_3m":  {"name": "🚀 3 Meses",    "price": 35.00, "desc": "Acceso completo 90 días"},
    "plan_life":{"name": "♾️ Lifetime",   "price": 99.00, "desc": "Acceso de por vida"},
}

TOOLS = {
    "tool_1": {"name": "🛠️ Herramienta Pro",     "price": 10.00, "desc": "Herramienta premium #1"},
    "tool_2": {"name": "⚙️ Pack Herramientas",    "price": 20.00, "desc": "Pack completo de herramientas"},
}

VIP_CHANNELS = {
    "vip_1": {"name": "📢 Canal VIP Básico",     "price": 8.00,  "desc": "Acceso canal VIP nivel 1"},
    "vip_2": {"name": "👑 Canal VIP Premium",    "price": 18.00, "desc": "Acceso canal VIP nivel 2"},
}

COURSES = {
    "course_1": {"name": "📚 Curso Starter",     "price": 25.00, "desc": "Curso introductorio"},
    "course_2": {"name": "🎓 Curso Avanzado",    "price": 50.00, "desc": "Curso nivel avanzado"},
}

SUPPORT = {
    "support_1": {"name": "💬 Soporte Básico",   "price": 12.00, "desc": "Soporte por 30 días"},
    "support_2": {"name": "🏆 Soporte Premium",  "price": 30.00, "desc": "Soporte ilimitado 90 días"},
}

ALL_PRODUCTS = {**PLANS, **TOOLS, **VIP_CHANNELS, **COURSES, **SUPPORT}

# ─────────────────────────────────────────
#  HELPERS — NOWPAYMENTS
# ─────────────────────────────────────────
def create_payment(amount: float, product_name: str, order_id: str) -> dict | None:
    """Crea un pago en NOWPayments y devuelve la respuesta."""
    headers = {
        "x-api-key": NOWPAYMENTS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "price_amount": amount,
        "price_currency": "usd",
        "pay_currency": "usdttrc20",   # cambia la crypto si quieres
        "order_id": order_id,
        "order_description": product_name,
        "ipn_callback_url": "",        # ← opcional: URL de tu webhook
    }
    try:
        r = requests.post(f"{NOWPAYMENTS_BASE}/payment", json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error(f"NOWPayments error: {e}")
        return None

# ─────────────────────────────────────────
#  TECLADOS
# ─────────────────────────────────────────
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Planes de Suscripción", callback_data="cat_plans")],
        [InlineKeyboardButton("🛠️ Herramientas",          callback_data="cat_tools")],
        [InlineKeyboardButton("📢 Canales VIP",            callback_data="cat_vip")],
        [InlineKeyboardButton("📚 Cursos",                 callback_data="cat_courses")],
        [InlineKeyboardButton("💬 Soporte",                callback_data="cat_support")],
    ])

def category_keyboard(products: dict, back_cb: str = "menu"):
    rows = [[InlineKeyboardButton(p["name"], callback_data=key)] for key, p in products.items()]
    rows.append([InlineKeyboardButton("🔙 Volver", callback_data=back_cb)])
    return InlineKeyboardMarkup(rows)

def product_keyboard(product_key: str, back_cb: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Pagar con Crypto", callback_data=f"pay_{product_key}")],
        [InlineKeyboardButton("🔙 Volver",            callback_data=back_cb)],
    ])

# ─────────────────────────────────────────
#  HANDLERS
# ─────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"👋 ¡Hola, {user.first_name}!\n\n"
        "Bienvenido a nuestro bot de servicios y pagos.\n"
        "Elige una categoría para comenzar:"
    )
    await update.message.reply_text(text, reply_markup=main_menu_keyboard())

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ── Menú principal ──────────────────────────────────
    if data == "menu":
        await query.edit_message_text(
            "🏠 Menú principal — elige una categoría:",
            reply_markup=main_menu_keyboard()
        )

    # ── Categorías ──────────────────────────────────────
    elif data == "cat_plans":
        await query.edit_message_text(
            "📦 *Planes de Suscripción*\n\nElige el plan que mejor se adapte a ti:",
            parse_mode="Markdown",
            reply_markup=category_keyboard(PLANS, "menu")
        )
    elif data == "cat_tools":
        await query.edit_message_text(
            "🛠️ *Herramientas*\n\nNuestras herramientas premium:",
            parse_mode="Markdown",
            reply_markup=category_keyboard(TOOLS, "menu")
        )
    elif data == "cat_vip":
        await query.edit_message_text(
            "📢 *Canales VIP*\n\nAccede a contenido exclusivo:",
            parse_mode="Markdown",
            reply_markup=category_keyboard(VIP_CHANNELS, "menu")
        )
    elif data == "cat_courses":
        await query.edit_message_text(
            "📚 *Cursos*\n\nFormación especializada:",
            parse_mode="Markdown",
            reply_markup=category_keyboard(COURSES, "menu")
        )
    elif data == "cat_support":
        await query.edit_message_text(
            "💬 *Soporte*\n\nPlanes de soporte personalizado:",
            parse_mode="Markdown",
            reply_markup=category_keyboard(SUPPORT, "menu")
        )

    # ── Detalle de producto ──────────────────────────────
    elif data in ALL_PRODUCTS:
        prod = ALL_PRODUCTS[data]
        # determinar categoría para el botón "volver"
        back = (
            "cat_plans"   if data in PLANS else
            "cat_tools"   if data in TOOLS else
            "cat_vip"     if data in VIP_CHANNELS else
            "cat_courses" if data in COURSES else
            "cat_support"
        )
        text = (
            f"{prod['name']}\n\n"
            f"📝 {prod['desc']}\n"
            f"💰 Precio: *${prod['price']:.2f} USD*\n\n"
            "Paga de forma segura con criptomonedas vía NOWPayments."
        )
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=product_keyboard(data, back)
        )

    # ── Iniciar pago ─────────────────────────────────────
    elif data.startswith("pay_"):
        product_key = data[4:]
        if product_key not in ALL_PRODUCTS:
            await query.edit_message_text("❌ Producto no encontrado.")
            return

        prod = ALL_PRODUCTS[product_key]
        order_id = str(uuid.uuid4())[:8].upper()

        await query.edit_message_text("⏳ Generando tu pago, espera un momento...")

        payment = create_payment(prod["price"], prod["name"], order_id)

        if not payment:
            await query.edit_message_text(
                "❌ Error al conectar con el procesador de pagos. Intenta de nuevo más tarde.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Volver al menú", callback_data="menu")
                ]])
            )
            return

        pay_address  = payment.get("pay_address", "N/A")
        pay_amount   = payment.get("pay_amount", "N/A")
        pay_currency = payment.get("pay_currency", "crypto").upper()
        payment_id   = payment.get("payment_id", order_id)

        text = (
            f"✅ *Pago generado correctamente*\n\n"
            f"🛒 Producto: {prod['name']}\n"
            f"💰 Total: *${prod['price']:.2f} USD*\n"
            f"🔑 Order ID: `{order_id}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📤 Envía exactamente:\n"
            f"`{pay_amount}` *{pay_currency}*\n\n"
            f"📋 A la dirección:\n"
            f"`{pay_address}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⚠️ El pago expira en 60 minutos.\n"
            f"Una vez confirmado recibirás acceso automáticamente."
        )
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Volver al menú", callback_data="menu")
            ]])
        )

        # Notificar al admin
        admin_text = (
            f"🆕 Nuevo pago iniciado\n"
            f"👤 User: @{query.from_user.username or query.from_user.id}\n"
            f"🛒 Producto: {prod['name']}\n"
            f"💵 Monto: ${prod['price']:.2f} USD\n"
            f"🔑 Order ID: {order_id}\n"
            f"🆔 Payment ID: {payment_id}"
        )
        try:
            await ctx.bot.send_message(ADMIN_ID, admin_text)
        except Exception:
            pass  # no bloquear si el admin no está disponible

# ─────────────────────────────────────────
#  ARRANQUE
# ─────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    # ignorar mensajes de texto que no sean comandos
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))

    logger.info("🤖 Bot iniciado con polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
