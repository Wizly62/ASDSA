from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = "7958295913:AAF_VcDTIXHYDmoRhtDdfpZwpxPAJ9A3L-I"
ADMIN_ID = 1250481865

TARIFFS = {
    '1_day': {'name': '1 день', 'price': 49},
    '7_days': {'name': '7 дней', 'price': 149},
    '14_days': {'name': '14 дней', 'price': 299},
    '30_days': {'name': '30 дней', 'price': 499},
    'forever': {'name': 'Навсегда', 'price': 999}
}

pending_requests = {}
waiting_for_key = {}
user_keys = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 Привет! <b>Добро пожаловать в kasper shop</b>!\n\n"
        "<b>Выберите действие:</b>"
    )
    keyboard = [
        [InlineKeyboardButton("💰 Купить подписку", callback_data='select_tariff')],
        [InlineKeyboardButton("🔑 Мои ключи", callback_data='my_keys')],
        [InlineKeyboardButton("💬 Поддержка", url="https://t.me/ksssdd12312")]
    ]

    if update.message:
        # Отправляем гифку
        await update.message.reply_animation(
            animation='https://i.imgur.com/Yks1Ve7.gif'
        )
        # Отправляем приветственный текст с кнопками
        await update.message.reply_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

async def select_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton(f"1 день — {TARIFFS['1_day']['price']} ₽", callback_data='tariff_1_day')],
        [InlineKeyboardButton(f"7 дней — {TARIFFS['7_days']['price']} ₽", callback_data='tariff_7_days')],
        [InlineKeyboardButton(f"14 дней — {TARIFFS['14_days']['price']} ₽", callback_data='tariff_14_days')],
        [InlineKeyboardButton(f"30 дней — {TARIFFS['30_days']['price']} ₽", callback_data='tariff_30_days')],
        [InlineKeyboardButton(f"Навсегда — {TARIFFS['forever']['price']} ₽", callback_data='tariff_forever')],
        [InlineKeyboardButton("🔙 Назад", callback_data='back_to_start')]
    ]
    await query.edit_message_text("📋 **Выберите тариф:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def process_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tariff_key = query.data.replace('tariff_', '')
    if tariff_key not in TARIFFS:
        await query.edit_message_text("❌ Неверный тариф.")
        return
    context.user_data['tariff'] = tariff_key
    keyboard = [
        [InlineKeyboardButton("💳 Оплатить", callback_data=f'pay_{tariff_key}')],
        [InlineKeyboardButton("🔙 Назад", callback_data='select_tariff')]
    ]
    text = (
        f"💼 **Тариф:** {TARIFFS[tariff_key]['name']}\n"
        f"💰 **Цена:** {TARIFFS[tariff_key]['price']} ₽\n\n"
        "Нажмите **«Оплатить»** для получения реквизитов."
    )
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def process_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tariff_key = query.data.replace('pay_', '')
    if tariff_key not in TARIFFS:
        await query.edit_message_text("❌ Неверный тариф.")
        return
    text = (
        f"💼 **Тариф:** {TARIFFS[tariff_key]['name']}\n"
        f"💵 **Сумма:** {TARIFFS[tariff_key]['price']} ₽\n\n"
        "🏦 Реквизиты для оплаты:\n"
        "💳 Тинькофф: `2200701041421857`\n\n"
        "📸 После оплаты отправьте фото чека с **HWID** в подписи в этот чат."
    )
    await query.edit_message_text(text, parse_mode='Markdown')

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        caption = update.message.caption
        if not caption:
            await update.message.reply_text("⚠️ Пожалуйста, отправьте фото чека с **HWID** в подписи.", parse_mode='Markdown')
            return
        user_id = update.effective_user.id
        username = update.effective_user.username or "N/A"
        tariff = context.user_data.get('tariff', 'N/A')
        hwid = caption.strip()
        file_id = update.message.photo[-1].file_id

        pending_requests[user_id] = {'hwid': hwid, 'file_id': file_id, 'username': username, 'tariff': tariff}

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Принять", callback_data=f"approve_{user_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}")
            ]
        ])

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=file_id,
            caption=(
                f"📩 Новый чек от @{username} (ID: {user_id})\n"
                f"💼 Тариф: {tariff}\n"
                f"🔑 HWID: {hwid}"
            ),
            reply_markup=keyboard
        )
        await update.message.reply_text("✅ Чек и HWID отправлены админу. Ожидайте ответа.")
    else:
        await update.message.reply_text("⚠️ Отправьте фото чека с **HWID** в подписи.", parse_mode='Markdown')

async def approve_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    admin_id = query.from_user.id
    user_id = int(query.data.split('_')[1])
    if user_id not in pending_requests:
        await query.edit_message_text("❌ Заявка не найдена или уже обработана.")
        return
    waiting_for_key[admin_id] = user_id
    await context.bot.send_message(chat_id=admin_id, text=f"✍️ Введите ключ для пользователя ID {user_id}:")

async def reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split('_')[1])
    if user_id in pending_requests:
        del pending_requests[user_id]
    await context.bot.send_message(chat_id=user_id, text="❌ Ваш чек отклонён. Свяжитесь с админом.")
    await query.edit_message_text("❌ Чек отклонён.")

async def handle_key_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id
    if admin_id not in waiting_for_key:
        return
    user_id = waiting_for_key[admin_id]
    key = update.message.text.strip()
    if user_id not in pending_requests:
        await update.message.reply_text("❌ Заявка пользователя не найдена или уже обработана.")
        waiting_for_key.pop(admin_id)
        return
    req = pending_requests.pop(user_id)
    user_keys.setdefault(user_id, []).append(key)
    await context.bot.send_message(
        chat_id=user_id,
        text=(
            "✅ Ваш чек одобрен!\n\n"
            f"🔑 **Ваш ключ:**\n`{key}`\n\n"
            f"🔐 HWID: {req['hwid']}"
        ),
        parse_mode='Markdown'
    )
    await update.message.reply_text(f"✅ Ключ отправлен пользователю ID {user_id}.")
    waiting_for_key.pop(admin_id)

async def my_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    keys = user_keys.get(user_id)
    if not keys:
        await query.edit_message_text("🔑 У вас ещё нет ключей.")
        return
    text = "🔑 **Ваши ключи:**\n" + "\n".join(f"{i+1}. `{k}`" for i, k in enumerate(keys))
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='back_to_start')]])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await start(update, context)

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(CallbackQueryHandler(select_tariff, pattern='^select_tariff$'))
    app.add_handler(CallbackQueryHandler(process_tariff, pattern='^tariff_'))
    app.add_handler(CallbackQueryHandler(process_payment, pattern='^pay_'))
    app.add_handler(CallbackQueryHandler(back_to_start, pattern='^back_to_start$'))
    app.add_handler(CallbackQueryHandler(approve_payment, pattern=r'^approve_\d+$'))
    app.add_handler(CallbackQueryHandler(reject_payment, pattern=r'^reject_\d+$'))
    app.add_handler(CallbackQueryHandler(my_keys, pattern='^my_keys$'))

    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), handle_key_input))

    app.run_polling()

if __name__ == '__main__':
    main()
