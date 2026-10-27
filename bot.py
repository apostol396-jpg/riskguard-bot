import asyncio
import json
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    LabeledPrice, PreCheckoutQuery, CallbackQuery, FSInputFile
)

# Настройки проекта
BOT_TOKEN = "8487245947:AAFZvadtWRzjJbkiI4pt5RIvaJGVXwqIWWU"
WEBAPP_URL = "https://riskguard-pro.apostol396.workers.dev"
PDF_FILE_PATH = "RiskGuard_PRO_Guide.pdf"  # Файл лежит в одной папке с bot.py

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Кеш file_id в памяти, чтобы не загружать PDF с диска при каждой покупке
cached_pdf_file_id = None


@dp.message(CommandStart())
@dp.message(CommandStart())
async def cmd_start(message: Message):
    # 1. Нижняя кнопка (ОБЯЗАТЕЛЬНА для работы оплат через tg.sendData)
    reply_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 Открыть RiskGuard PRO", web_app=WebAppInfo(url=WEBAPP_URL))]
        ],
        resize_keyboard=True
    )

    # 2. Инлайн-кнопки под сообщением (ТОЛЬКО для быстрых действий в чате, без запуска Web App)
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐ Поддержать (15)", callback_data="tip_15"),
            InlineKeyboardButton(text="⭐ (50)", callback_data="tip_50"),
            InlineKeyboardButton(text="⭐ (100)", callback_data="tip_100")
        ],
        [InlineKeyboardButton(text="📚 Купить PRO-пакет (50 Stars)", callback_data="buy_pro")]
    ])

    await message.answer(
        "Добро пожаловать в **RiskGuard PRO**!\n\n"
        "• Рассчитывайте точный объем позиции и цену ликвидации\n"
        "• Находите монеты с перегревом лонгов и шортов в Радаре\n"
        "• Тренируйте риск-менеджмент в Практикуме:\n\n"
        "👇 **Для запуска нажмите кнопку «🚀 Открыть RiskGuard PRO» в самом низу экрана.**",
        reply_markup=inline_kb,
        parse_mode="Markdown"
    )
    await message.answer(
        "Калькулятор всегда доступен в нижнем меню чата:",
        reply_markup=reply_kb
    )

# Обработка донатов через инлайн-кнопки в чате
@dp.callback_query(F.data.startswith("tip_"))
async def process_tip_callback(callback: CallbackQuery):
    amount = int(callback.data.split("_")[1])
    if amount not in (15, 50, 100):
        amount = 15
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Поддержка проекта RiskGuard",
        description=f"Благодарность автору за разработку приложения ({amount} Stars).",
        payload=f"tip_{amount}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Благодарность автору", amount=amount)]
    )
    await callback.answer()


# Обработка команд на оплату и донат напрямую из окна Mini App (tg.sendData)
@dp.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
        action = data.get("action")

        if action == "tip_stars":
            amount = int(data.get("amount", 15))
            if amount not in (15, 50, 100):
                amount = 15
            await bot.send_invoice(
                chat_id=message.from_user.id,
                title="Поддержка проекта RiskGuard",
                description=f"Благодарность автору за разработку ({amount} Stars).",
                payload=f"tip_{amount}",
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="Благодарность автору", amount=amount)]
            )
        elif action == "buy_pro_stars":
            await send_pro_invoice(message)
    except Exception:
        await message.answer("Не удалось обработать запрос. Воспользуйтесь командой /pro.")


# Выставление счета на покупку PRO-пакета (50 Stars)
@dp.callback_query(F.data == "buy_pro")
@dp.message(Command("pro"))
async def send_pro_invoice(event):
    chat_id = event.from_user.id
    await bot.send_invoice(
        chat_id=chat_id,
        title="PRO-пакет: Анти-Ликвидация (PDF)",
        description="Формула чистого безубытка, матрица безопасных плеч, сетапы по фандингу и чек-лист сделки.",
        payload="pro_pack_v1",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="PRO-гайд Анти-Ликвидация", amount=50)]
    )
    if isinstance(event, CallbackQuery):
        await event.answer()


# Обязательное подтверждение готовности принять платеж (Telegram Stars)
@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


# Автоматическая выдача PDF-файла строго после подтверждения оплаты сервером Telegram
@dp.message(F.successful_payment)
async def success_payment_handler(message: Message):
    global cached_pdf_file_id
    payload = message.successful_payment.invoice_payload

    if payload.startswith("tip_"):
        await message.answer("Спасибо за вашу поддержку! 🌟 Ваши звезды помогают развивать RiskGuard PRO.")
    elif payload == "pro_pack_v1":
        await message.answer("✅ Оплата прошла успешно! Отправляю ваш закрытый PDF-регламент:")

        if cached_pdf_file_id:
            await message.answer_document(
                document=cached_pdf_file_id,
                caption="📘 **Протокол «Анти-Ликвидация» (PRO Edition)**\nСохраните файл в Избранное Telegram, чтобы шпаргалка всегда была под рукой.",
                parse_mode="Markdown"
            )
        elif os.path.exists(PDF_FILE_PATH):
            doc = FSInputFile(PDF_FILE_PATH)
            sent_msg = await message.answer_document(
                document=doc,
                caption="📘 **Протокол «Анти-Ликвидация» (PRO Edition)**\nСохраните файл в Избранное Telegram, чтобы шпаргалка всегда была под рукой.",
                parse_mode="Markdown"
            )
            cached_pdf_file_id = sent_msg.document.file_id
        else:
            await message.answer(
                "📘 **Протокол «Анти-Ликвидация» (Краткая сводка):**\n"
                "1. Чистый БУ Long = Вход × 1.0015 (+0.15%)\n"
                "2. Чистый БУ Short = Вход × 0.9985 (-0.15%)\n"
                "3. Правило фиксации: 50% позиции закрывается на уровне риска 1:1, остаток переводится в Чистый БУ."
            )


from aiohttp import web

async def ping(request):
    return web.Response(text="RiskGuard Bot is alive!")

async def main():
    # Запуск фонового веб-сервера для прохождения проверок Render
    app = web.Application()
    app.router.add_get('/', ping)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())