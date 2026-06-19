import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# 1. SOZLAMALAR
BOT_TOKEN = "8646478674:AAGCnz-J99VuhmZlCTU6Cq0vAvd2mFbGayg"  # Tokeningiz
ADMIN_ID = 8236886172  # Admin ID

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 2. MA'LUMOTLAR BAZASI BILAN ISHLASH
conn = sqlite3.connect("konkurs_baza.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    ball INTEGER DEFAULT 0,
    invited_by INTEGER DEFAULT 0
)""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS channels (
    channel_id TEXT PRIMARY KEY,
    channel_name TEXT
)""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)""")

# Standart sozlamalarni kiritish (HTML formatida xavfsiz holatga keltirildi)
cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('shartlar', 'Konkurs shartlari: Kanallarga a''zo bo''ling va do''stlaringizni taklif qilib ball yiging!')")
cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('goliblar_soni', '5')")
conn.commit()

class AdminStates(StatesGroup):
    reklama_kutish = State()
    kanal_id_kutish = State()
    shart_kutish = State()

# 3. YORDAMCHI FUNKSIYALAR
async def check_sub(user_id: int) -> bool:
    cursor.execute("SELECT channel_id FROM channels")
    channels = cursor.fetchall()
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch[0], user_id=user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception:
            return False
    return True

async def get_sub_keyboard():
    cursor.execute("SELECT channel_id, channel_name FROM channels")
    channels = cursor.fetchall()
    builder = InlineKeyboardBuilder()
    for ch in channels:
        url = f"https://t.me/{ch[0].replace('@', '')}" if ch[0].startswith('@') else ch[0]
        builder.button(text=f"➕ {ch[1]}", url=url)
    builder.button(text="✅ Tekshirish", callback_data="check_subscription")
    builder.adjust(1)
    return builder.as_markup()

def main_keyboard(user_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔗 Taklif havolasi (Link)", callback_data="get_link")
    builder.button(text="📊 Balimni ko'rish", callback_data="my_balance")
    builder.button(text="🏆 TOP Reyting", callback_data="top_rating")
    builder.button(text="🎁 Konkurs Shartlari", callback_data="view_rules")
    if user_id == ADMIN_ID:
        builder.button(text="⚙️ Admin Panel", callback_data="admin_panel")
    builder.adjust(2, 2)
    return builder.as_markup()

# 4. BOT BUYRUQLARI VA KOD QISMI

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Foydalanuvchi"
    
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else 0

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute("INSERT INTO users (user_id, username, invited_by) VALUES (?, ?, ?)", 
                       (user_id, username, referrer_id))
        conn.commit()

    if not await check_sub(user_id):
        await message.answer("❌ <b>Botdan foydalanish uchun homiy kanallarga a'zo bo'ling!</b>", 
                             reply_markup=await get_sub_keyboard(), parse_mode="HTML")
        return

    await message.answer(f"👋 Salom {message.from_user.full_name}!\n🏆 Konkurs botimizga xush kelibsiz!", 
                         reply_markup=main_keyboard(user_id))

@dp.callback_query(F.data == "check_subscription")
async def check_subscription_callback(call: types.CallbackQuery):
    user_id = call.from_user.id
    if await check_sub(user_id):
        cursor.execute("SELECT invited_by, ball FROM users WHERE user_id = ?", (user_id,))
        user_info = cursor.fetchone()
        
        if user_info and user_info[0] > 0:
            ref_id = user_info[0]
            cursor.execute("UPDATE users SET ball = ball + 1 WHERE user_id = ?", (ref_id,))
            cursor.execute("UPDATE users SET invited_by = -1 WHERE user_id = ?", (user_id,))
            conn.commit()
            try:
                await bot.send_message(ref_id, f"🎉 Bitta do'stingiz kanallarga a'zo bo'ldi va sizga <b>1 ball</b> berildi!", parse_mode="HTML")
            except:
                pass
                
        await call.message.delete()
        await call.message.answer("🎉 Tabriklaymiz, barcha kanallarga a'zolik tasdiqlandi!", reply_markup=main_keyboard(user_id))
    else:
        await call.answer("❌ Hamma kanallarga a'zo bo'lmadingiz!", show_alert=True)

@dp.callback_query(F.data == "get_link")
async def get_link(call: types.CallbackQuery):
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={call.from_user.id}"
    await call.message.answer(f"🔗 Sizning referal havolangiz:\n<code>{link}</code>\n\nUshbu havolani do'stlaringizga tarqating va ball yiging!", parse_mode="HTML")
    await call.answer()

@dp.callback_query(F.data == "my_balance")
async def my_balance(call: types.CallbackQuery):
    cursor.execute("SELECT ball FROM users WHERE user_id = ?", (call.from_user.id,))
    ball = cursor.fetchone()[0]
    await call.message.answer(f"📊 Sizning balingiz: <b>{ball} ball</b>", parse_mode="HTML")
    await call.answer()

@dp.callback_query(F.data == "top_rating")
async def top_rating(call: types.CallbackQuery):
    cursor.execute("SELECT value FROM settings WHERE key = 'goliblar_soni'")
    limit = int(cursor.fetchone()[0])
    
    cursor.execute("SELECT username, ball FROM users ORDER BY ball DESC LIMIT ?", (limit,))
    top_users = cursor.fetchall()
    
    text = f"🏆 <b>TOP {limit} Reyting (Eng ko'p ball to'plaganlar):</b>\n\n"
    for i, u in enumerate(top_users, 1):
        text += f"{i}. @{u[0]} — {u[1]} ball\n"
    
    await call.message.answer(text, parse_mode="HTML")
    await call.answer()

@dp.callback_query(F.data == "view_rules")
async def view_rules(call: types.CallbackQuery):
    cursor.execute("SELECT value FROM settings WHERE key = 'shartlar'")
    shartlar = cursor.fetchone()[0]
    await call.message.answer(f"🎁 <b>Konkurs shartlari va sovg'alar:</b>\n\n{shartlar}", parse_mode="HTML")
    await call.answer()

# 5. ADMIN PANEL FUNKSIYALARI
@dp.callback_query(F.data == "admin_panel")
async def admin_panel(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Ommaviy Xabar (Reklama)", callback_data="admin_reklama")
    builder.button(text="➕ Kanal Qo'shish", callback_data="admin_add_channel")
    builder.button(text="❌ Kanallarni Tozalash", callback_data="admin_clear_channels")
    builder.button(text="✍️ Shartlarni o'zgartirish", callback_data="admin_edit_rules")
    builder.button(text="⬅️ Chiqish", callback_data="back_to_menu")
    builder.adjust(1)
    await call.message.answer("⚙️ <b>Admin boshqaruv paneli:</b>", reply_markup=builder.as_markup(), parse_mode="HTML")
    await call.answer()

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(call: types.CallbackQuery):
    await call.message.edit_text("Asosiy menyu:", reply_markup=main_keyboard(call.from_user.id))

# JONLI SHARTLARNI O'ZGARTIRISH KODI (Yangi qo'shildi)
@dp.callback_query(F.data == "admin_edit_rules")
async def admin_edit_rules(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.answer("✍️ Yangi konkurs shartlarini yuboring (Oddiy matn shaklida):")
    await state.set_state(AdminStates.shart_kutish)
    await call.answer()

@dp.message(AdminStates.shart_kutish)
async def save_new_rules(message: types.Message, state: FSMContext):
    new_text = message.text
    cursor.execute("UPDATE settings SET value = ? WHERE key = 'shartlar'", (new_text,))
    conn.commit()
    await message.answer("✅ Konkurs shartlari muvaffaqiyatli yangilandi!")
    await state.clear()

# Ommaviy xabar yuborish
@dp.callback_query(F.data == "admin_reklama")
async def admin_reklama(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Xabarni yuboring (Matn, rasm yoki video bo'lishi mumkin):")
    await state.set_state(AdminStates.reklama_kutish)

@dp.message(AdminStates.reklama_kutish)
async def send_reklama(message: types.Message, state: FSMContext):
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    count = 0
    for u in users:
        try:
            await message.copy_to(chat_id=u[0])
            count += 1
        except:
            pass
    await message.answer(f"📢 Xabar {count} ta foydalanuvchiga muvaffaqiyatli yuborildi!")
    await state.clear()

# Kanal qo'shish
@dp.callback_query(F.data == "admin_add_channel")
async def add_channel_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Kanal ID yoki usernamesini va nomini mana bunday formatda yuboring:\n\n<code>@kanal_username|Kanal nomi</code> yoki <code>-1001234567|Kanal nomi</code>", parse_mode="HTML")
    await state.set_state(AdminStates.kanal_id_kutish)

@dp.message(AdminStates.kanal_id_kutish)
async def add_channel_finish(message: types.Message, state: FSMContext):
    try:
        ch_id, ch_name = message.text.split("|")
        cursor.execute("INSERT OR REPLACE INTO channels (channel_id, channel_name) VALUES (?, ?)", (ch_id.strip(), ch_name.strip()))
        conn.commit()
        await message.answer("✅ Kanal muvaffaqiyatli qo'shildi!")
    except:
        await message.answer("❌ Xato format. Qaytadan urinib ko'ring.")
    await state.clear()

@dp.callback_query(F.data == "admin_clear_channels")
async def clear_channels(call: types.CallbackQuery):
    cursor.execute("DELETE FROM channels")
    conn.commit()
    await call.message.answer("🗑 Barcha majburiy kanallar o'chirildi!")
    await call.answer()

if __name__ == "__main__":
    dp.run_polling(bot)
