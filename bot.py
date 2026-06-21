import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiohttp import web

# --- SOZLAMALAR ---
# Bu yerga faqat @BotFather bergan eng oxirgi toza tokenni qo'ying
BOT_TOKEN = "8646478674:AAE81PMd2Z01E21E94mxSfR3ezuYOq81X4A"
ADMIN_ID = 8236886172  # Sizning Telegram ID raqamingiz

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- RENDER UCHUN PORT TINGLOVCHI SERVER ---
async def handle(request):
    return web.Response(text="Bot muvaffaqiyatli ishlayapti!")

async def start_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- BOT BUYRUQLARI ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"Salom {message.from_user.full_name}! 👋\n"
        "Konkurs botimizga xush kelibsiz! Bot hozirda bulutli serverda 24/7 rejimda faol."
    )

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    # ID tekshirish
    if message.from_user.id == ADMIN_ID:
        builder = ReplyKeyboardBuilder()
        builder.button(text="📊 Konkurs holati")
        builder.button(text="➕ Yangi konkurs ochish")
        builder.button(text="✉️ Foydalanuvchilarga xabar")
        builder.adjust(2)  # Tugmalarni qatorlarga chiroyli taqsimlash
        
        await message.answer(
            "🔒 **Admin panelga xush kelibsiz!**\nKerakli bo'limni tanlang:",
            reply_markup=builder.as_markup(resize_keyboard=True)
        )
    else:
        await message.answer("❌  Saz admin amassan!")

# --- ASOSIY ISHGA TUSHISH QISMI ---
async def main():
    # Render o'chib qolmasligi uchun serverni fonda yoqamiz
    await start_server()
    
    # Konfliktlarni oldini olish uchun eski xabarlarni tozalab tashlaymiz
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Telegram bilan aloqani boshlaymiz
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

 if __name__ == "__main__":
    asyncio.run(main())
