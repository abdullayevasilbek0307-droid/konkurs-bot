import os
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.client.default import DefaultBotProperties

# 1. ASOSIY SOZLAMALAR
BOT_TOKEN = "8646478674:AAE81PMd2Z01E2iE94mxSfR3ezuYOq81X4A"  # <-- Bot tokeningizni shu yerga qo'ying
ADMIN_ID = 8236886172  # <-- Siz yuborgan Telegram ID

# Majburiy a'zolik uchun kanal va guruh sozlamalari
REQUIRED_CHANNELS = [
    {"id": "@Al_Matin_Mebel", "name": "Al Matin Mebel (Kanal)"},
    {"id": -1001914961318, "name": "Al Matin Mebel group (Guruh)"}
]

# Aiogram 3.x uchun to'g'ri sozlama
bot = Bot(
    token=BOT_TOKEN, 
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

db_conn = sqlite3.connect("konkurs.db")
cursor = db_conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    referred_by INTEGER,
    score INTEGER DEFAULT 0
)
""")
db_conn.commit()

# 2. YORDAMCHI FUNKSIYALAR
async def check_subscription(user_id: int) -> bool:
    for chat in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=chat["id"], user_id=user_id)
            if member.status in ['left', 'kicked', 'left_chat_member']:
                return False
        except Exception:
            return False
    return True

def get_subscription_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Al Matin Mebel (Kanal)", url="https://t.me/Al_Matin_Mebel")],
        [InlineKeyboardButton(text="💬 Al Matin Mebel group", url="https://t.me/+f0wV4eD1h701N2Ri" if "https" in str(REQUIRED_CHANNELS[1]["id"]) else f"https://t.me/c/{str(REQUIRED_CHANNELS[1]['id'])[4:]}/1")],
        [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")]
    ])
    return keyboard

def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔗 Referal havolam", callback_data="my_link"),
            InlineKeyboardButton(text="📊 Balimni ko'rish", callback_data="my_score")
        ],
        [
            InlineKeyboardButton(text="🏆 Top Reyting", callback_data="top_rating"),
            InlineKeyboardButton(text="🎁 Konkurs shartlari", callback_data="terms")
        ]
    ])
    return keyboard

# 3. HANDLERLAR
@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = message.from_user.id
    text_args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    args = text_args[0] if text_args else None
    
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        referred_by = None
        if args and args.isdigit() and int(args) != user_id:
            referred_by = int(args)
        
        cursor.execute("INSERT INTO users (user_id, referred_by, score) VALUES (?, ?, 0)", (user_id, referred_by))
        db_conn.commit()

    is_sub = await check_subscription(user_id)
    if not is_sub:
        await message.answer(
            "👋 <b>Assalomu alaykum!</b>\n\nKonkursda qatnashish uchun quyidagi kanal va guruhimizga obuna bo'lishingiz shart:",
            reply_markup=get_subscription_keyboard()
        )
    else:
        await message.answer("🎉 <b>Konkurs botimizga xush kelibsiz!</b>\nQuyidagi tugmalardan foydalaning:", reply_markup=get_main_keyboard())

@dp.callback_query(lambda c: c.data == "check_sub")
async def callback_check_sub(call: CallbackQuery):
    user_id = call.from_user.id
    is_sub = await check_subscription(user_id)
    
    if is_sub:
        cursor.execute("SELECT referred_by FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        if res and res[0]:
            ref_id = res[0]
            cursor.execute("SELECT score FROM users WHERE user_id = ?", (ref_id,))
            ref_user = cursor.fetchone()
            if ref_user:
                cursor.execute("UPDATE users SET score = score + 1 WHERE user_id = ?", (ref_id,))
                cursor.execute("UPDATE users SET referred_by = NULL WHERE user_id = ?", (user_id,))
                db_conn.commit()
                try:
                    await bot.send_message(chat_id=ref_id, text="🎉 <b>Siz taklif qilgan foydalanuvchi kanallarga a'zo bo'ldi va sizga 1 ball berildi!</b>")
                except:
                    pass

        await call.message.delete()
        await call.message.answer("🎉 <b>Tabriklaymiz, obuna tasdiqlandi!</b>\nKonkurs menyusi ochildi:", reply_markup=get_main_keyboard())
    else:
        await call.answer("❌ Siz hali ham barcha kanal yoki guruhlarga a'zo bo'lmadingiz!", show_alert=True)

@dp.callback_query(lambda c: c.data == "my_link")
async def callback_my_link(call: CallbackQuery):
    if not await check_subscription(call.from_user.id):
        await call.message.answer("❌ Konkursda qatnashish uchun avval obuna bo'ling!", reply_markup=get_subscription_keyboard())
        return
        
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={call.from_user.id}"
    await call.message.answer(
        f"🔗 <b>Sizning referal havolangiz:</b>\n\n<code>{ref_link}</code>\n\n"
        f"Ushbu havolani do'stlaringizga tarqating. Har bir a'zo bo'lgan do'stingiz uchun <b>1 ball</b> beriladi!",
        disable_web_page_preview=True
    )

@dp.callback_query(lambda c: c.data == "my_score")
async def callback_my_score(call: CallbackQuery):
    if not await check_subscription(call.from_user.id):
        await call.message.answer("❌ Konkursda qatnashish uchun avval obuna bo'ling!", reply_markup=get_subscription_keyboard())
        return

    cursor.execute("SELECT score FROM users WHERE user_id = ?", (call.from_user.id,))
    res = cursor.fetchone()
    score = res[0] if res else 0
    await call.message.answer(f"📊 <b>Sizning joriy ballaringiz:</b> {score} ball")

@dp.callback_query(lambda c: c.data == "top_rating")
async def callback_top_rating(call: CallbackQuery):
    if not await check_subscription(call.from_user.id):
        await call.message.answer("❌ Konkursda qatnashish uchun avval obuna bo'ling!", reply_markup=get_subscription_keyboard())
        return

    cursor.execute("SELECT user_id, score FROM users ORDER BY score DESC LIMIT 10")
    top_users = cursor.fetchall()
    
    text = "🏆 <b>Eng ko'p ball to'plagan Top 10 ishtirokchi:</b>\n\n"
    for i, user in enumerate(top_users, 1):
        text += f"{i}. ID: <code>{user[0]}</code> — <b>{user[1]} ball</b>\n"
        
    await call.message.answer(text)

@dp.callback_query(lambda c: c.data == "terms")
async def callback_terms(call: CallbackQuery):
    if not await check_subscription(call.from_user.id):
        await call.message.answer("❌ Konkursda qatnashish uchun avval obuna bo'ling!", reply_markup=get_subscription_keyboard())
        return

    text = (
        "🎁 <b>Konkurs Shartlari:</b>\n\n"
        "1. @Al_Matin_Mebel kanaliga a'zo bo'lish.\n"
        "2. Al Matin Mebel group guruhiga a'zo bo'lish.\n"
        "3. O'zingizning maxsus referal havolangizni do'stlaringizga tarqatish.\n\n"
        "<i>Eng ko'p ball to'plagan ishtirokchilar qimmatbaho sovg'alar bilan taqdirlanadi!</i>"
    )
    await call.message.answer(text)

# 4. BOTNI ISHGA TUSHIRISH
async def main():
    # Veb-serverni asosiy kodni bloklamasdan, orqa fonda (task qilib) ishga tushiramiz:
   
    
    # Endi Telegram bot xabarlarni bemalol eshitadi:
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
from aiohttp import web
import asyncio

# Render o'chib qolmasligi uchun soxta veb-server
async def handle(request):
    return web.Response(text="Bot ishlayapti!")

async def start_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()

# Botni ishga tushirish qismida (main funksiyada) buni chaqiring:
# asyncio.create_task(start_server())
