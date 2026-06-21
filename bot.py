import os
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiohttp import web

# --- SOZLAMALAR ---
BOT_TOKEN = "8646478674:AAE81PMd2Z01E21E94mxSfR3ezuYOq81X4A"
ADMIN_ID = 8236886172
BOT_USERNAME = "konkurs_menejer_bot" # <--- Bot tahririga botingiz usenamini yozing (masalan: konkurs_uz_bot)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- MA'LUMOTLAR BAZASI (SQLITE3) ---
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            referred_by INTEGER,
            points INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- RENDER UCHUN PORT SERVERI ---
async def handle(request):
    return web.Response(text="Konkurs boti muvaffaqiyatli ishlayapti!")

async def start_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- BOT HANDLERLARI ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    args = command.args  # Referal ID tekshirish
    
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        referred_by = None
        if args and args.isdigit() and int(args) != user_id:
            referred_by = int(args)
            # Taklif qilganga ball berish
            cursor.execute("UPDATE users SET points = points + 1 WHERE user_id = ?", (referred_by,))
            try:
                await bot.send_message(referred_by, f"🎉 Yangi taklif! {full_name} sizning havolangiz orqali kirdi va sizga 1 ball berildi.")
            except Exception:
                pass
        
        cursor.execute("INSERT INTO users (user_id, full_name, referred_by) VALUES (?, ?, ?)", (user_id, full_name, referred_by))
        conn.commit()
    
    conn.close()
    
    # Referal havola yaratish
    ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    
    await message.answer(
        f"Salom {full_name}! 👋\n\n"
        f"🎁 Konkursimizga xush kelibsiz!\n\n"
        f"🔗 Sizning referal havolangiz:\n{ref_link}\n\n"
        f"Do'stlaringizni taklif qiling va ballarni qo'lga kiriting!"
    )

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        builder = ReplyKeyboardBuilder()
        builder.button(text="📊 Konkurs holati (Top 10)")
        builder.button(text="👥 Umumiy a'zolar")
        builder.button(text="✉️ Reklama yuborish")
        builder.adjust(2)
        
        await message.answer(
            "🔒 **Admin panelga xush kelibsiz!**\nKerakli bo'limni tanlang:",
            reply_markup=builder.as_markup(resize_keyboard=True)
        )
    else:
        await message.answer("❌ Kechirasiz, siz admin emassiz!")

@dp.message(lambda message: message.text == "📊 Konkurs holati (Top 10)")
async def admin_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, points FROM users ORDER BY points DESC LIMIT 10")
    top_users = cursor.fetchall()
    conn.close()
    
    text = "📊 **Konkurs yetakchilari (Top 10):**\n\n"
    for i, user in enumerate(top_users, 1):
        text += f"{i}. {user[0]} — {user[1]} ball\n"
        
    await message.answer(text)

@dp.message(lambda message: message.text == "👥 Umumiy a'zolar")
async def admin_all_users(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    
    await message.answer(f"👥 Botdagi jami ro'yxatdan o'tgan foydalanuvchilar: {count} ta")

@dp.message(lambda message: message.text == "✉️ Reklama yuborish")
async def admin_reklama_prompt(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("✉️ Reklama xabarini tarqatish uchun quyidagi formatda yozing:\n`/send Xabar matni`")

@dp.message(Command("send"))
async def admin_send_reklama(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    xabar = command.args
    if not xabar:
        await message.answer("Xabar matnini kiriting. Masalan: `/send Salom`")
        return
        
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    all_users = cursor.fetchall()
    conn.close()
    
    count = 0
    await message.answer("🚀 Reklama yuborish boshlandi...")
    for user in all_users:
        try:
            await bot.send_message(user[0], xabar)
            count += 1
            await asyncio.sleep(0.05) # Telegram bloklamasligi uchun cheklov
        except Exception:
            continue
            
    await message.answer(f"✅ Reklama muvaffaqiyatli {count} ta foydalanuvchiga yetkazildi!")

# --- ASOSIY ISHGA TUSHISH ---
async def main():
    await start_server()
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
