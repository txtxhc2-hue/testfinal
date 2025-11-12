import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.enums import ChatMemberStatus
import asyncio
import time
from aiogram import types, F
from aiogram.filters import StateFilter
from datetime import datetime
from aiogram.filters import CommandObject
import os
from dotenv import load_dotenv
import random
import html
import tempfile
import shutil
from aiogram.filters import StateFilter
import aiosqlite
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram import exceptions
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from typing import List, Dict
# .env faylidan konfiguratsiyani yuklash
load_dotenv()

# Bot konfiguratsiyasi
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7956962802:AAEfHnVO89IK7Yj52GZqo-U_lDg7gG08idQ")
ADMIN_ID = int(os.getenv("TELEGRAM_ADMIN_ID", "6607605946"))

# Database initialization
import sqlite3
import logging
import os

def init_db():
    """
    Ma'lumotlar bazasini ishga tushirish va kerakli jadvallarni yaratish.
    Agar jadvallar allaqachon mavjud bo'lsa, ularni qayta yaratmaydi.
    """
    # Ma'lumotlar bazasi fayli nomi
    DB_NAME = 'anime_bot.db'
    
    # Bog'lanishni o'rnatish
    conn = None
    try:
        # Ma'lumotlar bazasiga ulanish
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Muhim PRAGMA sozlamalari
        cursor.execute("PRAGMA foreign_keys = ON")  # Foreign key cheklovlari
        cursor.execute("PRAGMA journal_mode = WAL")  # Yozuv rejimi
        cursor.execute("PRAGMA synchronous = NORMAL")  # Sinxronlash
        
        # Mavjud jadvallarni aniqlash
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [table[0] for table in cursor.fetchall()]
        
        # 1. Versiya nazorati jadvali
        if 'db_version' not in existing_tables:
            cursor.execute('''
                CREATE TABLE db_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute("INSERT INTO db_version (version) VALUES (1)")
            logging.info("'db_version' jadvali yaratildi")
        
        # 2. Anime jadvali
        if 'anime' not in existing_tables:
            cursor.execute('''
                CREATE TABLE anime (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    country TEXT,
                    language TEXT,
                    year INTEGER,
                    genre TEXT,
                    description TEXT,
                    image TEXT,
                    video TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            logging.info("'anime' jadvali yaratildi")
        
        # 3. Epizodlar jadvali
        if 'episodes' not in existing_tables:
            cursor.execute('''
                CREATE TABLE episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    anime_code TEXT NOT NULL,
                    episode_number INTEGER NOT NULL,
                    video_file_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (anime_code) REFERENCES anime(code) ON DELETE CASCADE,
                    UNIQUE(anime_code, episode_number)
                )
            ''')
            logging.info("'episodes' jadvali yaratildi")
        
        # 4. Davom etayotgan anime jadvali
        if 'ongoing_anime' not in existing_tables:
            cursor.execute('''
                CREATE TABLE ongoing_anime (
                    anime_code TEXT PRIMARY KEY,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (anime_code) REFERENCES anime(code) ON DELETE CASCADE
                )
            ''')
            logging.info("'ongoing_anime' jadvali yaratildi")
        
        # 5. Adminlar jadvali
        if 'admins' not in existing_tables:
            cursor.execute('''
                CREATE TABLE admins (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    added_by INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (added_by) REFERENCES admins(user_id)
                )
            ''')
            # Asosiy adminni qo'shamiz
            cursor.execute("INSERT OR IGNORE INTO admins (user_id, username, added_by) VALUES (?, ?, ?)", 
                          (ADMIN_ID, "owner", ADMIN_ID))
            logging.info("'admins' jadvali yaratildi")
        
     
        if 'channels' not in existing_tables:
             cursor.execute('''
        CREATE TABLE channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_type TEXT CHECK(channel_type IN ('mandatory', 'post', 'additional_mandatory', 'group')),
            channel_id TEXT UNIQUE NOT NULL,
            channel_username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
             logging.info("'channels' jadvali yaratildi")
 
        if 'favorites' not in existing_tables:
            cursor.execute('''
                CREATE TABLE favorites (
                    user_id INTEGER,
                    anime_code TEXT,
                    PRIMARY KEY (user_id, anime_code),
                    FOREIGN KEY (anime_code) REFERENCES anime(code) ON DELETE CASCADE
                )
            ''')
            logging.info("'favorites' jadvali yaratildi")
        
        # 8. Obunachilar jadvali
        if 'subscribers' not in existing_tables:
            cursor.execute('''
                CREATE TABLE subscribers (
                    user_id INTEGER PRIMARY KEY,
                    notifications BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            logging.info("'subscribers' jadvali yaratildi")
        
        # 9. Savol-javob jadvali
        if 'questions' not in existing_tables:
            cursor.execute('''
                CREATE TABLE questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            logging.info("'questions' jadvali yaratildi")
        
        # 10. Test ishtirokchilari jadvali
        if 'quiz_participants' not in existing_tables:
            cursor.execute('''
                CREATE TABLE quiz_participants (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    correct_answers INTEGER DEFAULT 0,
                    total_answers INTEGER DEFAULT 0,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            logging.info("'quiz_participants' jadvali yaratildi")
        
        # 11. Chatbot javoblari jadvali
        if 'chatbot_responses' not in existing_tables:
            cursor.execute('''
                CREATE TABLE chatbot_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            logging.info("'chatbot_responses' jadvali yaratildi")
        
        # Indekslarni qo'shamiz
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_anime_code ON anime(code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_episodes_anime_code ON episodes(anime_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_favorites_user_id ON favorites(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_questions_question ON questions(question)")
        
        conn.commit()
        logging.info("Ma'lumotlar bazasi muvaffaqiyatli ishga tushirildi")
        
    except sqlite3.Error as e:
        logging.error(f"Ma'lumotlar bazasi xatosi: {e}")
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        logging.error(f"Kutilmagan xato: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
# Database ni ishga tushirish
try:
    init_db()
except Exception as e:
    logging.critical(f"Failed to initialize database: {e}")
    raise SystemExit("Database initialization failed")

# Botni ishga tushirish
bot = Bot(token=TOKEN)
dp = Dispatcher()

# User states dictionary
user_state = {}


# ==================== HELPER FUNCTIONS ====================

async def is_owner(user_id: int) -> bool:
    """Foydalanuvchi bot egasi (asosiy admin) ekanligini tekshiradi"""
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM admins WHERE user_id = ? AND added_by = user_id", (user_id,))
        return cursor.fetchone() is not None
    finally:
        conn.close()

async def is_admin(user_id: int) -> bool:
    """Foydalanuvchi admin ekanligini tekshiradi"""
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None
    finally:
        conn.close()
async def validate_database(db_path: str) -> dict:
    """Validate the database structure and return counts"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check required tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        required_tables = {'anime', 'episodes', 'ongoing_anime', 'admins', 'channels'}
        
        missing_tables = required_tables - tables
        if missing_tables:
            return {
                "valid": False,
                "message": f"Quyidagi jadvallar topilmadi: {', '.join(missing_tables)}"
            }
        
        # Validate table structures (asosiy maydonlarni tekshirish)
        try:
            cursor.execute("SELECT code, title FROM anime LIMIT 1")
            cursor.execute("SELECT anime_code, episode_number FROM episodes LIMIT 1")
            cursor.execute("SELECT anime_code FROM ongoing_anime LIMIT 1")
            cursor.execute("SELECT user_id FROM admins LIMIT 1")
            cursor.execute("SELECT channel_id FROM channels LIMIT 1")
        except sqlite3.Error as e:
            return {
                "valid": False,
                "message": f"Jadval strukturasida xatolik: {str(e)}"
            }
        
        # Get counts
        counts = {}
        cursor.execute("SELECT COUNT(*) FROM anime")
        counts['anime_count'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM episodes")
        counts['episodes_count'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ongoing_anime")
        counts['ongoing_count'] = cursor.fetchone()[0]
        
        counts['valid'] = True
        return counts
        
    except Exception as e:
        return {
            "valid": False,
            "message": f"Bazani tekshirishda xatolik: {str(e)}"
        }
    finally:
        if conn:
            conn.close()
async def check_admin(user_id: int, message=None, call=None, require_owner=False):
    """Admin huquqini tekshiradi"""
    if require_owner:
        if not await is_owner(user_id):
            if message:
                await message.answer("❌ Bu amalni faqat bot egasi bajarishi mumkin!")
            if call:
                await call.answer("❌ Bu amalni faqat bot egasi bajarishi mumkin!", show_alert=True)
            return False
        return True
    
    if not await is_admin(user_id):
        if message:
            await message.answer("❌ Siz admin emassiz!")
        if call:
            await call.answer("❌ Siz admin emassiz!", show_alert=True)
        return False
    return True

async def check_subscription(user_id: int) -> bool:
    """Foydalanuvchi barcha majburiy kanallarga obuna bo'lganligini tekshiradi"""
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT channel_id FROM channels 
            WHERE channel_type IN ('mandatory', 'additional_mandatory')
            ORDER BY channel_type
        """)
        channels = [row[0] for row in cursor.fetchall()]
        
        if not channels:
            return True  # Agar majburiy kanal yo'q bo'lsa, obuna shart emas
            
        for channel_id in channels:
            try:
                member = await bot.get_chat_member(channel_id, user_id)
                if member.status not in [
                    ChatMemberStatus.MEMBER,
                    ChatMemberStatus.ADMINISTRATOR,
                    ChatMemberStatus.CREATOR
                ]:
                    return False
            except exceptions.TelegramAPIError:
                return False
        
        return True
    except Exception as e:
        logging.error(f"Obunani tekshirishda xatolik: {e}")
        return False
    finally:
        conn.close()
def check_anime_in_db():
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM anime")
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0
async def show_subscription_required(message: types.Message):
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT channel_id, channel_name 
        FROM channels 
        WHERE channel_type IN ('mandatory', 'additional_mandatory')
        ORDER BY channel_type
    """)
    channels = cursor.fetchall()
    conn.close()
    
    if not channels:
        await show_main_menu(message)
        return
    
    buttons = []
    for channel_id, channel_name in channels:
        try:
            chat = await bot.get_chat(channel_id)
            invite_link = await chat.export_invite_link() if not chat.username else f"https://t.me/{chat.username}"
            
            # Kanal a'zoligini tekshiramiz
            try:
                member = await bot.get_chat_member(channel_id, message.from_user.id)
                is_member = member.status in [
                    ChatMemberStatus.MEMBER,
                    ChatMemberStatus.ADMINISTRATOR,
                    ChatMemberStatus.CREATOR
                ]
            except:
                is_member = False
                
            # Agar a'zo bo'lgan bo'lsa, kanalni ko'rsatmaymiz
            if not is_member:
                buttons.append([InlineKeyboardButton(
                    text=f"❌ {chat.title} kanaliga obuna bo'lish",
                    url=invite_link
                )])
                
        except exceptions.TelegramAPIError as e:
            logging.error(f"Kanal linkini olishda xato: {e}")
            continue
    
    # Agar barcha kanallarga a'zo bo'lgan bo'lsa
    if not buttons:
        await show_main_menu(message)
        return
    
    buttons.append([InlineKeyboardButton(
        text="🔄 Obunani tekshirish",
        callback_data="check_subscription"
    )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer(
        "⚠️ Botdan foydalanish uchun quyidagi kanal(lar)ga obuna bo'lishingiz kerak:",
        reply_markup=keyboard
    )

async def show_main_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
    keyboard=[
        # Tepada 2 ta tugma (qidiruv va sevimlilar)
        [
            KeyboardButton(text="🔍 Anime Qidirish"), 
            KeyboardButton(text="⭐️ Sevimlilarim")
        ],
        
        # O'rtada 1 ta katta tugma (ongoing)
        [
            KeyboardButton(text="📺 Ongoing Animelar")
        ],
        
        # Pastda 2 ta tugma (savol-javob va yordam)
        [
            KeyboardButton(text="❓ Savol-Javob"),
            KeyboardButton(text="ℹ️ Yordam")
        ],
        
        # Eng pastda 1 ta alohida tugma (obuna)
        [
            KeyboardButton(text="🔔 Obuna Sozlamalari")
        ]
    ],
    resize_keyboard=True,
    input_field_placeholder="Kerakli bo'limni tanlang"
)
    
    await message.answer(
        "👋 Anime botiga xush kelibsiz!\n"
        "Quyidagi menyudan kerakli bo'limni tanlang:",
        reply_markup=keyboard
    )

@dp.message(lambda message: message.text == "📺 Ongoing Animelar")
async def ongoing_anime_menu(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await show_subscription_required(message)
        return
    
    await show_ongoing_anime_list(message)
async def show_ongoing_anime_list(message: types.Message, page: int = 0):
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    LIMIT = 5  # Har bir sahifada 5 ta anime
    
    try:
        cursor.execute('''
            SELECT a.code, a.title, a.image 
            FROM ongoing_anime o
            JOIN anime a ON o.anime_code = a.code
            ORDER BY o.added_at DESC
            LIMIT ? OFFSET ?
        ''', (LIMIT, page * LIMIT))
        ongoing_anime = cursor.fetchall()
        
        if not ongoing_anime and page > 0:
            await message.answer("Boshqa ongoing animelar mavjud emas")
            return
        elif not ongoing_anime:
            await message.answer("ℹ️ Hozircha ongoing animelar mavjud emas")
            return
            
        builder = InlineKeyboardBuilder()
        for code, title, image in ongoing_anime:
            builder.row(
                InlineKeyboardButton(
                    text=f"🎬 {title}",
                    callback_data=f"watch_{code}"
                )
            )
        
        # Sahifalash tugmalari
        pagination_buttons = []
        if page > 0:
            pagination_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Oldingi",
                    callback_data=f"ongoing_page_{page-1}"
                )
            )
        
        cursor.execute("SELECT COUNT(*) FROM ongoing_anime")
        total = cursor.fetchone()[0]
        if (page + 1) * LIMIT < total:
            pagination_buttons.append(
                InlineKeyboardButton(
                    text="Keyingi ➡️",
                    callback_data=f"ongoing_page_{page+1}"
                )
            )
        
        if pagination_buttons:
            builder.row(*pagination_buttons)
        
        await message.answer(
            "📺 Ongoing Animelar:",
            reply_markup=builder.as_markup()
        )
            
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        conn.close()

@dp.callback_query(lambda call: call.data.startswith("ongoing_page_"))
async def ongoing_page_callback(call: types.CallbackQuery):
    page = int(call.data.replace("ongoing_page_", ""))
    await call.answer()
    await show_ongoing_anime_list(call.message, page)
async def notify_subscribers(anime_code: str, episode_number: int):
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT user_id FROM subscribers WHERE notifications = TRUE")
        subscribers = cursor.fetchall()
        
        cursor.execute("SELECT title FROM anime WHERE code = ?", (anime_code,))
        anime_title = cursor.fetchone()[0]
        
        for (user_id,) in subscribers:
            try:
                await bot.send_message(
                    user_id,
                    f"🎉 Yangi qism! {anime_title} {episode_number}-qism qo'shildi!\n\n"
                    f"Tomosha qilish uchun: /watch_{anime_code}"
                )
            except Exception as e:
                logging.error(f"Xabar yuborishda xatolik (user_id={user_id}): {e}")
    except Exception as e:
        logging.error(f"Obunachilarga xabar yuborishda xatolik: {e}")
    finally:
        conn.close()

# ==================== USER HANDLERS ====================

@dp.message(Command("start"))
async def user_start(message: types.Message, command: CommandObject):
    if command.args and command.args.startswith("watch_"):
        anime_code = command.args.replace("watch_", "")
        
        # Agar qism raqami ham keltirilgan bo'lsa
        if "_" in anime_code:
            anime_code, episode_num = anime_code.split("_", 1)
            
            # Majburiy obunani tekshirish
            if not await check_subscription(message.from_user.id):
                await show_subscription_required(message)
                return
                
            # To'g'ridan-to'g'ri tanlangan qismni ko'rsatish
            conn = sqlite3.connect('anime_bot.db')
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    SELECT video_file_id 
                    FROM episodes 
                    WHERE anime_code = ? AND episode_number = ?
                """, (anime_code, episode_num))
                episode = cursor.fetchone()
                
                if episode:
                    video_file_id = episode[0]
                    
                    cursor.execute("SELECT title FROM anime WHERE code = ?", (anime_code,))
                    anime_title = cursor.fetchone()[0]
                    
                    await bot.send_video(
                        chat_id=message.from_user.id,
                        video=video_file_id,
                        caption=f"🎬 {anime_title} - {episode_num}-qism"
                    )
                    return
            except Exception as e:
                logging.error(f"Video yuklashda xatolik: {str(e)}")
            finally:
                conn.close()
        
        # Agar faqat anime kodi bo'lsa, oddiy anime detallarini ko'rsatish
        await show_anime_details(message, anime_code)
        return
    
    # Oddiy start komandasi
    if not await check_subscription(message.from_user.id):
        await show_subscription_required(message)
        return
    
    await show_main_menu(message)

@dp.callback_query(lambda call: call.data == "check_subscription")
async def check_subscription_callback(call: types.CallbackQuery):
    # Kanal a'zoligini tekshiramiz
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT channel_id, channel_name 
        FROM channels 
        WHERE channel_type IN ('mandatory', 'additional_mandatory')
        ORDER BY channel_type
    """)
    channels = cursor.fetchall()
    conn.close()
    
    not_subscribed = []
    for channel_id, channel_name in channels:
        try:
            member = await bot.get_chat_member(channel_id, call.from_user.id)
            if member.status not in [
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.CREATOR
            ]:
                not_subscribed.append((channel_id, channel_name))
        except:
            not_subscribed.append((channel_id, channel_name))
    
    if not not_subscribed:
        await call.message.delete()
        await show_main_menu(call.message)
        await call.answer("✅ Barcha kanallarga obuna bo'lgansiz!", show_alert=True)
    else:
        # Yangi tugmalar yaratamiz (faqat obuna bo'lmagan kanallar uchun)
        buttons = []
        for channel_id, channel_name in not_subscribed:
            try:
                chat = await bot.get_chat(channel_id)
                invite_link = await chat.export_invite_link() if not chat.username else f"https://t.me/{chat.username}"
                buttons.append([InlineKeyboardButton(
                    text=f"❌ {chat.title} kanaliga obuna bo'lish",
                    url=invite_link
                )])
            except exceptions.TelegramAPIError as e:
                logging.error(f"Kanal linkini olishda xato: {e}")
                continue
        
        buttons.append([InlineKeyboardButton(
            text="🔄 Obunani tekshirish",
            callback_data="check_subscription"
        )])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        try:
            await call.message.edit_text(
                "⚠️ Siz hali quyidagi kanal(lar)ga obuna bo'lmagansiz:",
                reply_markup=keyboard
            )
        except:
            await call.message.answer(
                "⚠️ Siz hali quyidagi kanal(lar)ga obuna bo'lmagansiz:",
                reply_markup=keyboard
            )
        
        await call.answer("❌ Hali barcha kanallarga obuna bo'lmagansiz!", show_alert=True)

@dp.message(lambda message: message.text in ["🔍 Anime Qidirish", "⭐️ Sevimlilarim", "❓ Savol-Javob"])
async def protected_features(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await show_subscription_required(message)
        return
    
    if message.text == "🔍 Anime Qidirish":
        await search_anime(message)
    elif message.text == "⭐️ Sevimlilarim":
        await show_favorites(message)
    elif message.text == "❓ Savol-Javob":
        await quiz_menu(message)

@dp.callback_query(lambda call: call.data.startswith(("watch_", "episode_")))
async def handle_watch_requests(call: types.CallbackQuery):
    if not await check_subscription(call.from_user.id):
        await call.answer("❌ Avval kanal(lar)ga obuna bo'ling!", show_alert=True)
        await show_subscription_required(call.message)
        return
    
    if call.data.startswith("watch_"):
        anime_code = call.data.replace("watch_", "")
        await show_episodes_menu(call.message, anime_code)
    elif call.data.startswith("episode_"):
        await show_episode(call)

# ==================== ANIME FUNCTIONS ====================

async def send_media_post(message: types.Message, media_type: str, media_file: str, anime_data: dict, is_channel: bool = False):
    caption = f"""
╭──────────────────────
├‣ <b>Nomi:</b> {anime_data['title']}
├‣ <b>Qism:</b> {anime_data['episodes_count']} ta
├‣ <b>Tili:</b> {anime_data['language']}
├‣ <b>Davlati:</b> {anime_data['country']}
├‣ <b>Janrlari:</b> {anime_data['genre']}
╰──────────────────────
🔢 <b>Kodi:</b> {anime_data['code']}
    """
    
    if is_channel:
        bot_username = (await bot.get_me()).username
        buttons = [
            [InlineKeyboardButton(
                text="▶️ Botda Tomosha Qilish", 
                url=f"https://t.me/{bot_username}?start=watch_{anime_data['code']}"
            )]
        ]
    else:
        buttons = [
            [InlineKeyboardButton(text="▶️ Tomosha Qilish", callback_data=f"watch_{anime_data['code']}")],
            [InlineKeyboardButton(text="⭐️ Sevimlilarga Qo'shish", callback_data=f"add_fav_{anime_data['code']}")]
        ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    reply_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]],
        resize_keyboard=True
    )
    
    try:
        if media_type == 'photo':
            await message.answer_photo(
                photo=media_file,
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        elif media_type == 'video':
            await message.answer_video(
                video=media_file,
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    except Exception as e:
        logging.error(f"Media post yuborishda xatolik: {e}")
        await message.answer("❌ Post yuborishda xatolik yuz berdi.")
async def show_anime_details(message: types.Message, anime_code: str):
    conn = None
    try:
        conn = sqlite3.connect('anime_bot.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT title, country, language, year, genre, image, video 
            FROM anime WHERE code = ?
        """, (anime_code,))
        anime = cursor.fetchone()
        
        if not anime:
            await message.answer("❌ Bunday kodli anime topilmadi.")
            return
            
        title, country, language, year, genre, image, video = anime
        
        cursor.execute("SELECT COUNT(*) FROM episodes WHERE anime_code = ?", (anime_code,))
        episodes_count = cursor.fetchone()[0]
        
        anime_data = {
            'title': title,
            'country': country,
            'language': language,
            'year': year,
            'genre': genre,
            'episodes_count': episodes_count,
            'code': anime_code
        }
        
        if video:
            await send_media_post(message, 'video', video, anime_data)
        elif image:
            await send_media_post(message, 'photo', image, anime_data)
        else:
            await send_text_post(message, anime_data)
            
    except Exception as e:
        logging.error(f"Anime details error: {str(e)}")
        await message.answer("❌ Anime ma'lumotlarini yuklashda xatolik yuz berdi.")
    finally:
        if conn:
            conn.close()

async def send_text_post(message: types.Message, anime_data: dict):
    caption = f"""
     
╭──────────────────────
├‣ <b>Nomi:</b> {anime_data['title']}
├‣ <b>Qism:</b> {anime_data['episodes_count']} ta
├‣ <b>Tili:</b> {anime_data['language']}
├‣ <b>Davlati:</b> {anime_data['country']}
├‣ <b>Janrlari:</b> {anime_data['genre']}
╰──────────────────────

🔢 <b>Kodi:</b> {anime_data['code']}
    """
    
    buttons = [
        [InlineKeyboardButton(text="▶️ Tomosha Qilish", callback_data=f"watch_{anime_data['code']}")],
        [InlineKeyboardButton(text="⭐️ Sevimlilarga Qo'shish", callback_data=f"add_fav_{anime_data['code']}")]
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer(
        text=caption,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

async def search_anime(message: types.Message):
    """Anime qidirish funksiyasi"""
    if not await check_subscription(message.from_user.id):
        await show_subscription_required(message)
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="🔍 Nom qidirish", callback_data="search_by_name"),
        InlineKeyboardButton(text="🔢 Kod qidirish", callback_data="search_by_code")
    ],
    [
        InlineKeyboardButton(text="🏆 Reyting", callback_data="top_anime"),
        InlineKeyboardButton(text="🎲 Random", callback_data="random_anime")
    ],
    [
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main")
    ]
])
    
    await message.answer(
        "🔍 Qanday usulda anime qidirmoqchisiz?",
        reply_markup=keyboard
    )

async def show_episodes_menu(message: types.Message, anime_code: str):
    """Anime qismlari menyusini ko'rsatadi"""
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        # Anime ma'lumotlarini olamiz
        cursor.execute("SELECT title FROM anime WHERE code = ?", (anime_code,))
        anime_title = cursor.fetchone()[0]
        
        # Barcha qismlarni olamiz
        cursor.execute("""
            SELECT episode_number 
            FROM episodes 
            WHERE anime_code = ?
            ORDER BY episode_number
        """, (anime_code,))
        episodes = cursor.fetchall()
        
        if not episodes:
            await message.answer("❌ Bu anime uchun hali qismlar qo'shilmagan!")
            return
        
        # Tugmalarni yaratamiz (har qatorda 3 ta tugma)
        buttons = []
        row = []
        for ep in episodes:
            row.append(InlineKeyboardButton(
                text=f"{ep[0]}-qism",
                callback_data=f"episode_{anime_code}_{ep[0]}"
            ))
            if len(row) >= 3:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        
    
        
        # Bekor qilish tugmasi (bosh menyuga qaytish uchun)
        buttons.append([InlineKeyboardButton(
            text="🔙 Bosh Menyu",
            callback_data="back_to_main_from_episodes"
        )])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Avvalgi xabarni o'chiramiz
        try:
            await message.delete()
        except:
            pass
        
        await message.answer(
            f"🎬 {anime_title}\n\n📺 Qismlar soni: {len(episodes)}\n\nTomosha qilish uchun qismni tanlang:",
            reply_markup=keyboard
        )
        
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        conn.close()
@dp.callback_query(lambda call: call.data == "ongoing_anime")
async def show_ongoing_anime(call: types.CallbackQuery):
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT a.code, a.title, a.image 
            FROM ongoing_anime o
            JOIN anime a ON o.anime_code = a.code
            ORDER BY o.added_at DESC
        ''')
        ongoing_anime = cursor.fetchall()
        
        if not ongoing_anime:
            await call.answer("ℹ️ Hozircha ongoing animelar mavjud emas", show_alert=True)
            return
            
        for code, title, image in ongoing_anime:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="▶️ Tomosha Qilish", callback_data=f"watch_{code}")],
                [InlineKeyboardButton(text="⭐️ Sevimlilarga Qo'shish", callback_data=f"add_fav_{code}")]
            ])
            
            await call.message.answer_photo(
                image,
                caption=f"🎬 {title}\n🔢 Kodi: {code}",
                reply_markup=keyboard
            )
            
    except Exception as e:
        await call.answer(f"❌ Xatolik yuz berdi: {str(e)}", show_alert=True)
    finally:
        conn.close()
        
@dp.callback_query(lambda call: call.data == "back_to_main_from_episodes")
async def back_to_main_from_episodes(call: types.CallbackQuery):
    try:
        await call.message.delete()
    except:
        pass
    await show_main_menu(call.message)
    await call.answer()
@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_anime_code")
async def process_anime_search(message: types.Message):
    if message.text == "🔙 Bekor qilish":
        await show_main_menu(message)
        if message.from_user.id in user_state:
            del user_state[message.from_user.id]
        return
    
    anime_code = message.text.strip()
    await show_anime_details(message, anime_code)
    
    if message.from_user.id in user_state:
        del user_state[message.from_user.id]

@dp.callback_query(lambda call: call.data.startswith("episode_"))
async def show_episode(call: types.CallbackQuery):
    """Anime qismini ko'rsatish funksiyasi"""
    conn = None
    try:
        await call.answer("⏳ Yuklanmoqda...")
        
        # Callback ma'lumotlarini ajratib olamiz (format: episode_animeCode_episodeNumber)
        parts = call.data.split('_')
        if len(parts) != 3:
            await call.answer("❌ Noto'g'ri format!", show_alert=True)
            return
            
        anime_code = parts[1]
        try:
            episode_num = int(parts[2])  # Qism raqami
        except ValueError:
            await call.answer("❌ Noto'g'ri epizod raqami!", show_alert=True)
            return
        
        # Bazadan anime ma'lumotlarini olamiz
        conn = sqlite3.connect('anime_bot.db')
        cursor = conn.cursor()

        cursor.execute("SELECT title FROM anime WHERE code = ?", (anime_code,))
        anime = cursor.fetchone()
        
        if not anime:
            await call.answer("❌ Anime topilmadi!", show_alert=True)
            return

        # Bazadan qism videosini olamiz
        cursor.execute("""
            SELECT video_file_id 
            FROM episodes 
            WHERE anime_code = ? AND episode_number = ?
        """, (anime_code, episode_num))
        episode = cursor.fetchone()

        if not episode:
            await call.answer(f"❌ {episode_num}-qism topilmadi!", show_alert=True)
            return

        video_file_id = episode[0]  # Video fayl IDsi

        # Qismlar sonini aniqlaymiz (oldingi/keyingi tugmalar uchun)
        cursor.execute("""
            SELECT MIN(episode_number), MAX(episode_number)
            FROM episodes
            WHERE anime_code = ?
        """, (anime_code,))
        min_ep, max_ep = cursor.fetchone()

        # Navigatsiya tugmalarini yaratamiz
        buttons = []
        if episode_num > min_ep:  # Oldingi qism tugmasi
            buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Oldingi",
                    callback_data=f"episode_{anime_code}_{episode_num-1}"
                )
            )
        
        if episode_num < max_ep:  # Keyingi qism tugmasi
            buttons.append(
                InlineKeyboardButton(
                    text="Keyingi ➡️",
                    callback_data=f"episode_{anime_code}_{episode_num+1}"
                )
            )
        
        # Qismlar menyusiga qaytish tugmasi
        buttons.append(
            InlineKeyboardButton(
                text="📋 Barcha qismlar",
                callback_data=f"watch_{anime_code}"
            )
        )
        
        # Bosh menyuga qaytish tugmasi
        buttons.append(
            InlineKeyboardButton(
                text="🔙 Bosh Menyu",
                callback_data="back_to_main_from_episode"
            )
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None

        # Avvalgi xabarni o'chiramiz
        try:
            await call.message.delete()
        except Exception:
            pass

        # Videoni yuboramiz
        await bot.send_video(
            chat_id=call.from_user.id,
            video=video_file_id,
            caption=f"🎬 {anime[0]} - {episode_num}-qism",
            reply_markup=keyboard
        )

    except Exception as e:
        logging.error(f"Xatolik: {str(e)}")
        await call.answer("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.", show_alert=True)
    finally:
        if conn:
            conn.close()
@dp.callback_query(lambda call: call.data == "back_to_main_from_episode")
async def back_to_main_from_episode(call: types.CallbackQuery):
    try:
        await call.message.delete()
    except:
        pass
    await show_main_menu(call.message)
    await call.answer()          

# ==================== FAVORITES FUNCTIONS ====================

@dp.callback_query(lambda call: call.data.startswith("add_fav_"))
async def add_favorite(call: types.CallbackQuery):
    anime_code = call.data.replace("add_fav_", "")

    try:
        async with aiosqlite.connect('anime_bot.db') as conn:
            cursor = await conn.cursor()

            try:
                await cursor.execute(
                    "INSERT INTO favorites (user_id, anime_code) VALUES (?, ?)",
                    (call.from_user.id, anime_code)
                )
                await conn.commit()
                await call.answer("✅ Anime sevimlilarga qo'shildi!", show_alert=True)
            except aiosqlite.IntegrityError:
                await call.answer("ℹ️ Bu anime allaqachon sevimlilarda bor", show_alert=True)
                return

            await cursor.execute(
                "SELECT title, image FROM anime WHERE code = ?", (anime_code,)
            )
            anime = await cursor.fetchone()

            if not anime:
                await call.answer("❌ Bunday anime topilmadi!", show_alert=True)
                return

            title, image = anime

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="▶️ Tomosha Qilish", callback_data=f"watch_{anime_code}")],
                [InlineKeyboardButton(text="❌ Sevimlilardan O'chirish", callback_data=f"remove_fav_{anime_code}")]
            ])

            try:
                await call.message.edit_reply_markup(reply_markup=keyboard)
            except Exception:
                await call.answer("⚠️ Tugmalarni yangilashda xatolik yuz berdi.")

    except Exception as e:
        await call.answer(f"❌ Xatolik yuz berdi: {str(e)}", show_alert=True)

@dp.callback_query(lambda call: call.data.startswith("remove_fav_"))
async def remove_favorite(call: types.CallbackQuery):
    anime_code = call.data.replace("remove_fav_", "")
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM favorites WHERE user_id = ? AND anime_code = ?", 
                      (call.from_user.id, anime_code))
        conn.commit()
        await call.answer("❌ Anime sevimlilardan olib tashlandi!", show_alert=True)
        
        cursor.execute("SELECT title, image FROM anime WHERE code = ?", (anime_code,))
        title, image = cursor.fetchone()[0]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Tomosha Qilish", callback_data=f"watch_{anime_code}")],
            [InlineKeyboardButton(text="⭐️ Sevimlilarga Qo'shish", callback_data=f"add_fav_{anime_code}")]
        ])
        
        await call.message.edit_reply_markup(reply_markup=keyboard)
        
    except Exception as e:
        await call.answer(f"❌ Xatolik yuz berdi: {str(e)}", show_alert=True)
    finally:
        conn.close()

@dp.message(lambda message: message.text == "⭐️ Sevimlilarim")
async def show_favorites(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await message.answer("❌ Avval kanalga obuna bo'ling!")
        return
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''SELECT a.code, a.title, a.image 
                        FROM favorites f 
                        JOIN anime a ON f.anime_code = a.code 
                        WHERE f.user_id = ?''', (message.from_user.id,))
        favorites = cursor.fetchall()
        
        if favorites:
            for code, title, image in favorites:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="▶️ Tomosha Qilish", callback_data=f"watch_{code}")],
                    [InlineKeyboardButton(text="❌ O'chirish", callback_data=f"remove_fav_{code}")]
                ])
                
                await message.answer_photo(
                    image,
                    caption=f"⭐️ {title}\n🔢 Kodi: {code}",
                    reply_markup=keyboard
                )
        else:
            await message.answer("ℹ️ Sizda hali sevimli anime lar mavjud emas.")
            
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        conn.close()

# ==================== SUBSCRIPTION FUNCTIONS ====================

@dp.message(lambda message: message.text == "🔔 Obuna Bo'lish")
async def toggle_subscription(message: types.Message):
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT notifications FROM subscribers WHERE user_id = ?", (message.from_user.id,))
        sub = cursor.fetchone()
        
        if sub:
            new_status = not sub[0]
            cursor.execute("UPDATE subscribers SET notifications = ? WHERE user_id = ?", 
                         (new_status, message.from_user.id))
            status_text = "faollashtirildi" if new_status else "o'chirildi"
        else:
            cursor.execute("INSERT INTO subscribers (user_id, notifications) VALUES (?, TRUE)", 
                         (message.from_user.id,))
            status_text = "faollashtirildi"
        
        conn.commit()
        await message.answer(f"🔔 Obuna holati {status_text}!")
        
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        conn.close()
@dp.callback_query(lambda call: call.data == "search_by_name")
async def search_by_name_start(call: types.CallbackQuery):
    user_state[call.from_user.id] = {"state": "waiting_anime_name"}
    await call.message.answer("🔍 Anime nomini kiriting (qisman nom ham ishlaydi):")

@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_anime_name")
async def search_by_name_process(message: types.Message):
    search_term = f"%{message.text}%"
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT code, title, image 
            FROM anime 
            WHERE title LIKE ? 
            ORDER BY title
            LIMIT 20
        """, (search_term,))
        results = cursor.fetchall()
        
        if not results:
            await message.answer("❌ Hech qanday anime topilmadi")
            return
            
        for code, title, image in results:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="▶️ Tomosha Qilish", callback_data=f"watch_{code}")],
                [InlineKeyboardButton(text="⭐️ Sevimlilarga Qo'shish", callback_data=f"add_fav_{code}")]
            ])
            
            await message.answer_photo(
                image,
                caption=f"🎬 {title}\n🔢 Kodi: {code}",
                reply_markup=keyboard
            )
            
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        if message.from_user.id in user_state:
            del user_state[message.from_user.id]
        conn.close()

@dp.callback_query(lambda call: call.data == "top_anime")
async def show_top_anime(call: types.CallbackQuery):
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        # Eng ko'p ko'rilgan animelarni topamiz (favorites jadvalidan)
        cursor.execute('''
            SELECT a.code, a.title, a.image, COUNT(f.user_id) as fav_count
            FROM anime a
            LEFT JOIN favorites f ON a.code = f.anime_code
            GROUP BY a.code
            ORDER BY fav_count DESC
            LIMIT 10
        ''')
        top_anime = cursor.fetchall()
        
        if not top_anime:
            await call.answer("ℹ️ Hozircha reyting mavjud emas", show_alert=True)
            return
            
        for code, title, image, fav_count in top_anime:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="▶️ Tomosha Qilish", callback_data=f"watch_{code}")],
                [InlineKeyboardButton(text="⭐️ Sevimlilarga Qo'shish", callback_data=f"add_fav_{code}")]
            ])
            
            await call.message.answer_photo(
                image,
                caption=f"🏆 {title}\n❤️ Sevimlilar soni: {fav_count}\n🔢 Kodi: {code}",
                reply_markup=keyboard
            )
            
    except Exception as e:
        await call.answer(f"❌ Xatolik yuz berdi: {str(e)}", show_alert=True)
    finally:
        conn.close()
@dp.callback_query(lambda call: call.data == "search_by_code")
async def search_by_code_start(call: types.CallbackQuery):
    user_state[call.from_user.id] = {"state": "waiting_anime_code_for_search"}
    await call.message.answer("🔢 Qidirmoqchi bo'lgan anime kodini kiriting:")

@dp.callback_query(lambda call: call.data == "search_by_code")
async def search_by_code_start(call: types.CallbackQuery):
    user_state[call.from_user.id] = {"state": "waiting_anime_code_for_search"}
    await call.message.answer("🔢 Qidirmoqchi bo'lgan anime kodini kiriting:")

@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_anime_code_for_search")
async def search_by_code_process(message: types.Message):
    anime_code = message.text.strip()
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT a.code, a.title, a.image, a.video, a.language, a.country, a.genre, a.year,
                   (SELECT COUNT(*) FROM episodes WHERE anime_code = a.code) as episodes_count
            FROM anime a
            WHERE a.code = ?
        """, (anime_code,))
        anime = cursor.fetchone()
        
        if not anime:
            await message.answer("❌ Bunday kodli anime topilmadi. Qayta urinib ko'ring:")
            return
            
        code, title, image, video, language, country, genre, year, episodes_count = anime
        
        anime_data = {
            'title': title,
            'episodes_count': episodes_count,
            'code': code,
            'language': language or 'Noma\'lum',
            'country': country or 'Noma\'lum',
            'genre': genre or 'Noma\'lum',
            'year': year or 'Noma\'lum'
        }
        
        if video:
            await send_media_post(message, 'video', video, anime_data)
        elif image:
            await send_media_post(message, 'photo', image, anime_data)
        else:
            await send_text_post(message, anime_data)
            
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        if message.from_user.id in user_state:
            del user_state[message.from_user.id]
        conn.close()
@dp.callback_query(lambda call: call.data == "random_anime")
async def show_random_anime(call: types.CallbackQuery):
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        # Avval animelar sonini aniqlaymiz
        cursor.execute("SELECT COUNT(*) FROM anime")
        count = cursor.fetchone()[0]
        
        if count == 0:
            await call.answer("❌ Bazada anime topilmadi", show_alert=True)
            return
            
        # 5 ta tasodifiy anime olamiz
        cursor.execute("""
            SELECT a.code, a.title, COALESCE(a.video, a.image) as media, a.video IS NOT NULL as is_video
            FROM anime a
            ORDER BY RANDOM()
            LIMIT 5
        """)
        random_anime = cursor.fetchall()
        
        for code, title, media, is_video in random_anime:
            try:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="▶️ Tomosha Qilish", callback_data=f"watch_{code}")],
                    [InlineKeyboardButton(text="⭐️ Sevimlilarga Qo'shish", callback_data=f"add_fav_{code}")]
                ])
                
                if is_video:
                    await call.message.answer_video(
                        video=media,
                        caption=f"🎲 {title}\n🔢 Kodi: {code}",
                        reply_markup=keyboard
                    )
                elif media:
                    await call.message.answer_photo(
                        photo=media,
                        caption=f"🎲 {title}\n🔢 Kodi: {code}",
                        reply_markup=keyboard
                    )
                else:
                    await call.message.answer(
                        text=f"🎲 {title}\n🔢 Kodi: {code}",
                        reply_markup=keyboard
                    )
                    
            except exceptions.TelegramBadRequest as e:
                logging.error(f"Media yuborishda xatolik (anime: {code}): {str(e)}")
                continue
                
    except Exception as e:
        logging.error(f"Tasodifiy anime yuborishda xatolik: {str(e)}")
        await call.answer("❌ Xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.", show_alert=True)
    finally:
        conn.close()       
@dp.callback_query(lambda call: call.data == "random_anime")
async def show_random_anime(call: types.CallbackQuery):
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT code, title, image FROM anime ORDER BY RANDOM() LIMIT 5")
        random_anime = cursor.fetchall()
        
        if not random_anime:
            await call.answer("ℹ️ Anime topilmadi", show_alert=True)
            return
            
        for code, title, image in random_anime:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="▶️ Tomosha Qilish", callback_data=f"watch_{code}")],
                [InlineKeyboardButton(text="⭐️ Sevimlilarga Qo'shish", callback_data=f"add_fav_{code}")]
            ])
            
            await call.message.answer_photo(
                image,
                caption=f"🎲 {title}\n🔢 Kodi: {code}",
                reply_markup=keyboard
            )
            
    except Exception as e:
        await call.answer(f"❌ Xatolik yuz berdi: {str(e)}", show_alert=True)
    finally:
        conn.close()
# ==================== QUIZ FUNCTIONS ====================

@dp.message(lambda message: message.text == "❓ Savol-Javob")
async def quiz_menu(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Test Ishlash", callback_data="start_quiz")],
        [InlineKeyboardButton(text="🏆 Reyting", callback_data="show_rating")],
        [InlineKeyboardButton(text="ℹ️ Qoidalar", callback_data="quiz_rules")]
    ])
    
    await message.answer(
        "❓ Savol-Javob bo'limi\n\n"
        "Bu yerda anime haqidagi bilimingizni sinab ko'rishingiz mumkin!",
        reply_markup=keyboard
    )

@dp.callback_query(lambda call: call.data == "start_quiz")
async def start_quiz(call: types.CallbackQuery):
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, question, answer FROM questions ORDER BY RANDOM() LIMIT 1")
        question = cursor.fetchone()
        
        if question:
            q_id, question_text, correct_answer = question
            
            wrong_answers = [
                "Noto'g'ri javob 1",
                "Noto'g'ri javob 2",
                "Noto'g'ri javob 3"
            ]
            
            all_answers = wrong_answers + [correct_answer]
            random.shuffle(all_answers)
            
            keyboard_buttons = []
            for answer in all_answers:
                keyboard_buttons.append(
                    InlineKeyboardButton(
                        text=answer,
                        callback_data=f"answer_{q_id}_{1 if answer == correct_answer else 0}"
                    )
                )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                keyboard_buttons[i:i+2] for i in range(0, len(keyboard_buttons), 2)
            ])
            
            user_state[call.from_user.id] = {
                "quiz_state": "waiting_answer",
                "question_id": q_id
            }
            
            await call.message.answer(f"❓ Savol:\n\n{question_text}", reply_markup=keyboard)
        else:
            await call.message.answer("ℹ️ Hozircha savollar mavjud emas. Iltimos, keyinroq urinib ko'ring.")
    except Exception as e:
        await call.message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        conn.close()
        
@dp.callback_query(lambda call: call.data.startswith("answer_"))
async def check_answer(call: types.CallbackQuery):
    _, q_id, is_correct = call.data.split("_")
    is_correct = bool(int(is_correct))
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''INSERT OR IGNORE INTO quiz_participants 
                        (user_id, username, last_activity) 
                        VALUES (?, ?, CURRENT_TIMESTAMP)''', 
                      (call.from_user.id, call.from_user.username))
        
        cursor.execute('''UPDATE quiz_participants 
                        SET total_answers = total_answers + 1,
                            correct_answers = correct_answers + ?,
                            last_activity = CURRENT_TIMESTAMP
                        WHERE user_id = ?''', 
                      (1 if is_correct else 0, call.from_user.id))
        
        conn.commit()
        
        if is_correct:
            await call.answer("✅ To'g'ri javob! Tabriklaymiz!", show_alert=True)
        else:
            cursor.execute("SELECT answer FROM questions WHERE id = ?", (q_id,))
            correct_answer = cursor.fetchone()[0]
            await call.answer(f"❌ Noto'g'ri javob! To'g'ri javob: {correct_answer}", show_alert=True)
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Keyingi savol", callback_data="start_quiz")],
            [InlineKeyboardButton(text="🏆 Reyting", callback_data="show_rating")]
        ])
        
        await call.message.answer("Yana savol ishlaysizmi?", reply_markup=keyboard)
        
    except Exception as e:
        await call.message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        conn.close()

@dp.callback_query(lambda call: call.data == "show_rating")
async def show_rating(call: types.CallbackQuery):
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''SELECT username, correct_answers, total_answers 
                        FROM quiz_participants 
                        ORDER BY correct_answers DESC, last_activity DESC
                        LIMIT 10''')
        top_participants = cursor.fetchall()
        
        if top_participants:
            text = "🏆 Top 10 ishtirokchilar:\n\n"
            for idx, (username, correct, total) in enumerate(top_participants, 1):
                accuracy = (correct / total * 100) if total > 0 else 0
                text += f"{idx}. @{username}\n✅ {correct} | ❌ {total-correct} | 📊 {accuracy:.1f}%\n\n"
            
            await call.message.answer(text)
        else:
            await call.message.answer("ℹ️ Hozircha reyting mavjud emas.")
            
    except Exception as e:
        await call.message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        conn.close()

@dp.callback_query(lambda call: call.data == "quiz_rules")
async def quiz_rules(call: types.CallbackQuery):
    rules = (
        "📚 Savol-Javob qoidalari:\n\n"
        "1. Har bir to'g'ri javob uchun 1 ball\n"
        "2. Har bir noto'g'ri javob uchun 0 ball\n"
        "3. Reytingda faqat eng yaxshi 10 ta ishtirokchi ko'rsatiladi\n"
        "4. Javoblarni kichik harflarda yuborishingiz mumkin\n"
        "5. Har bir savolga faqat bir marta javob berishingiz mumkin\n\n"
        "Omad tilaymiz! 🍀"
    )
    await call.message.answer(rules)

# ==================== HELP FUNCTION ====================

@dp.message(lambda message: message.text == "ℹ️ Yordam")
async def show_help(message: types.Message):
    help_text = (
        "ℹ️ Anime Bot Yordam\n\n"
        "🔍 Anime qidirish uchun uning kodini yuboring yoki 'Anime Qidirish' tugmasini bosing.\n"
        "⭐️ Sevimli anime laringizni saqlash uchun 'Sevimlilarim' bo'limidan foydalaning.\n"
        "❓ Anime bilimingizni sinab ko'rish uchun 'Savol-Javob' bo'limiga kiring\n"
        "🔔 Yangi qismlar haqida xabar olish uchun obuna bo'lish tugmasini bosing.\n\n"
        "Agar muammo bo'lsa, admin bilan bog'laning."
    )
    await message.answer(help_text)

# ==================== ADMIN PANEL ====================

@dp.message(Command("admin"))
async def admin_login(message: types.Message):
    if not await check_admin(message.from_user.id, message=message):
        return
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎥 Anime Sozlash"), KeyboardButton(text="📢 Kanal Sozlash")],
            [KeyboardButton(text="📝 Post Tayyorlash"), KeyboardButton(text="🎞 Serial Post Qilish")],
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="👥 Obunachilar")],
            [KeyboardButton(text="👨‍💻 Adminlar"), KeyboardButton(text="❓ Savollar")],
            [KeyboardButton(text="🔙 Bosh Menyu")]
        ],
        resize_keyboard=True
    )
    await message.answer("👨‍💻 Admin Panelga xush kelibsiz!", reply_markup=keyboard)

# Anime settings
# Anime settings menyusiga ongoing anime boshqaruvi tugmasini qo'shamiz
@dp.message(lambda message: message.text == "🎥 Anime Sozlash")
async def anime_settings(message: types.Message):
    if not await check_admin(message.from_user.id, message=message):
        return
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Anime Qo'shish")],
            [KeyboardButton(text="✏️ Anime Tahrirlash")],
            [KeyboardButton(text="🗑 Anime O'chirish")],
            [KeyboardButton(text="🎞 Qism Qo'shish"), KeyboardButton(text="🗑 Qism O'chirish")],  # Yangi tugma
            [KeyboardButton(text="📺 Ongoing Anime"), KeyboardButton(text="🔙 Admin Panel")]
        ],
        resize_keyboard=True
    )
    await message.answer("🎥 Anime Sozlamalari:", reply_markup=keyboard)
@dp.message(lambda message: message.text == "🗑 Qism O'chirish")
async def delete_episode_start(message: types.Message):
    if not await check_admin(message.from_user.id, message=message):
        return
    
    user_state[message.from_user.id] = {"state": "waiting_anime_code_for_episode_delete"}
    await message.answer("🔢 Qism o'chirish uchun anime kodini yuboring:",
                       reply_markup=ReplyKeyboardMarkup(
                           keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]],
                           resize_keyboard=True
                       ))
@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_anime_code_for_episode_delete")
async def show_episodes_for_deletion(message: types.Message):
    if message.text == "🔙 Bekor qilish":
        await cancel_action(message)
        return
    
    anime_code = message.text.strip()
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        # Anime mavjudligini tekshirish
        cursor.execute("SELECT title FROM anime WHERE code = ?", (anime_code,))
        anime = cursor.fetchone()
        
        if not anime:
            await message.answer("❌ Bunday kodli anime topilmadi!")
            return
            
        # Qismlarni olish
        cursor.execute("""
            SELECT episode_number 
            FROM episodes 
            WHERE anime_code = ?
            ORDER BY episode_number
        """, (anime_code,))
        episodes = cursor.fetchall()
        
        if not episodes:
            await message.answer("❌ Bu anime uchun hech qanday qism topilmadi!")
            return
            
        # Tugmalarni yaratish (har qatorda 3 ta tugma)
        buttons = []
        row = []
        for ep in episodes:
            row.append(InlineKeyboardButton(
                text=f"{ep[0]}-qism",
                callback_data=f"delete_ep_{anime_code}_{ep[0]}"
            ))
            if len(row) >= 3:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        
        # Bekor qilish tugmasi
        buttons.append([InlineKeyboardButton(
            text="🔙 Bekor qilish",
            callback_data="cancel_episode_deletion"
        )])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await message.answer(
            f"🎬 {anime[0]}\n\n"
            f"🗑 O'chirish uchun qismni tanlang:",
            reply_markup=keyboard
        )
        
        # Anime kodini saqlab qo'yamiz
        user_state[message.from_user.id] = {
            "state": "waiting_episode_to_delete",
            "anime_code": anime_code,
            "anime_title": anime[0]
        }
        
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        conn.close()
@dp.callback_query(lambda call: call.data.startswith("delete_ep_"))
async def confirm_episode_deletion(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    # Callback ma'lumotlarini ajratib olish
    parts = call.data.split('_')
    anime_code = parts[2]
    episode_num = parts[3]
    
    # Tasdiqlash tugmalari
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Ha, o'chirish",
                callback_data=f"confirm_delete_ep_{anime_code}_{episode_num}"
            ),
            InlineKeyboardButton(
                text="❌ Bekor qilish",
                callback_data="cancel_episode_deletion"
            )
        ]
    ])
    
    await call.message.edit_text(
        f"⚠️ {anime_code} kodli animening {episode_num}-qismini o'chirishni tasdiqlaysizmi?",
        reply_markup=keyboard
    )
    await call.answer()
@dp.callback_query(lambda call: call.data.startswith("confirm_delete_ep_"))
async def delete_episode_final(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    # Callback ma'lumotlarini ajratib olish
    parts = call.data.split('_')
    anime_code = parts[3]
    episode_num = parts[4]
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        # Qism mavjudligini tekshirish
        cursor.execute("""
            SELECT 1 FROM episodes 
            WHERE anime_code = ? AND episode_number = ?
        """, (anime_code, episode_num))
        
        if not cursor.fetchone():
            await call.answer("❌ Bu qism allaqachon o'chirilgan!", show_alert=True)
            return
            
        # Qismni o'chirish
        cursor.execute("""
            DELETE FROM episodes 
            WHERE anime_code = ? AND episode_number = ?
        """, (anime_code, episode_num))
        conn.commit()
        
        await call.answer(f"✅ {episode_num}-qism muvaffaqiyatli o'chirildi!", show_alert=True)
        
        # Foydalanuvchiga xabar qaytarish
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🗑 Qism O'chirish")],
                [KeyboardButton(text="🔙 Admin Panel")]
            ],
            resize_keyboard=True
        )
        
        await call.message.answer(
            f"🎬 {anime_code} kodli animening {episode_num}-qismi o'chirildi!",
            reply_markup=keyboard
        )
        
    except Exception as e:
        await call.answer(f"❌ Xatolik yuz berdi: {str(e)}", show_alert=True)
    finally:
        conn.close()
@dp.callback_query(lambda call: call.data == "cancel_episode_deletion")
async def cancel_episode_deletion(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    # Foydalanuvchi holatini tozalash
    if call.from_user.id in user_state:
        del user_state[call.from_user.id]
    
    # Admin panelga qaytish
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🗑 Qism O'chirish")],
            [KeyboardButton(text="🔙 Admin Panel")]
        ],
        resize_keyboard=True
    )
    
    await call.message.answer(
        "❌ Qism o'chirish bekor qilindi.",
        reply_markup=keyboard
    )
    await call.answer()
async def cancel_action(message: types.Message):
    if message.from_user.id in user_state:
        del user_state[message.from_user.id]
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎥 Anime Sozlash")],
            [KeyboardButton(text="🔙 Admin Panel")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "❌ Amal bekor qilindi.",
        reply_markup=keyboard
    )

# Ongoing anime boshqaruvi
@dp.message(lambda message: message.text == "📺 Ongoing Anime")
async def manage_ongoing_anime(message: types.Message):
    if not await check_admin(message.from_user.id, message=message):
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Ongoingga Qo'shish", callback_data="add_ongoing")],
        [InlineKeyboardButton(text="➖ Ongoingdan O'chirish", callback_data="remove_ongoing")],
        [InlineKeyboardButton(text="📋 Ongoing Ro'yxati", callback_data="list_ongoing")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_anime_settings")]
    ])
    
    await message.answer("📺 Ongoing Anime Boshqaruvi", reply_markup=keyboard)

@dp.callback_query(lambda call: call.data == "add_ongoing")
async def add_ongoing_start(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    user_state[call.from_user.id] = {"state": "waiting_ongoing_code"}
    await call.message.answer("🔢 Ongoing ro'yxatiga qo'shish uchun anime kodini yuboring:")

@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_ongoing_code")
async def add_ongoing_process(message: types.Message):
    anime_code = message.text.strip()
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        # Anime mavjudligini tekshiramiz
        cursor.execute("SELECT title FROM anime WHERE code = ?", (anime_code,))
        anime = cursor.fetchone()
        
        if not anime:
            await message.answer("❌ Bunday kodli anime topilmadi!")
            return
            
        # Ongoing ro'yxatiga qo'shamiz
        cursor.execute("INSERT OR IGNORE INTO ongoing_anime (anime_code) VALUES (?)", (anime_code,))
        conn.commit()
        
        await message.answer(f"✅ {anime[0]} ongoing ro'yxatiga qo'shildi!")
        
    except sqlite3.IntegrityError:
        await message.answer("ℹ️ Bu anime allaqachon ongoing ro'yxatida")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        if message.from_user.id in user_state:
            del user_state[message.from_user.id]
        conn.close()

@dp.callback_query(lambda call: call.data == "list_ongoing")
async def list_ongoing_anime(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT a.code, a.title, o.added_at 
            FROM ongoing_anime o
            JOIN anime a ON o.anime_code = a.code
            ORDER BY o.added_at DESC
        ''')
        ongoing_list = cursor.fetchall()
        
        if not ongoing_list:
            await call.answer("ℹ️ Ongoing ro'yxati bo'sh", show_alert=True)
            return
            
        text = "📺 Ongoing Anime Ro'yxati:\n\n"
        for idx, (code, title, added_at) in enumerate(ongoing_list, 1):
            text += f"{idx}. {title} (Kod: {code})\n   📅 Qo'shilgan: {added_at}\n\n"
        
        await call.message.answer(text)
        
    except Exception as e:
        await call.answer(f"❌ Xatolik yuz berdi: {str(e)}", show_alert=True)
    finally:
        conn.close()

@dp.callback_query(lambda call: call.data == "remove_ongoing")
async def remove_ongoing_start(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT a.code, a.title 
            FROM ongoing_anime o
            JOIN anime a ON o.anime_code = a.code
            ORDER BY a.title
        ''')
        ongoing_list = cursor.fetchall()
        
        if not ongoing_list:
            await call.answer("ℹ️ Ongoing ro'yxati bo'sh", show_alert=True)
            return
            
        buttons = []
        for code, title in ongoing_list:
            buttons.append([InlineKeyboardButton(
                text=f"❌ {title}",
                callback_data=f"remove_ongoing_{code}"
            )])
        
        buttons.append([InlineKeyboardButton(
            text="🔙 Orqaga",
            callback_data="manage_ongoing"
        )])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await call.message.edit_text(
            "🗑 Ongoing ro'yxatidan o'chirish uchun anime tanlang:",
            reply_markup=keyboard
        )
        
    except Exception as e:
        await call.answer(f"❌ Xatolik: {str(e)}", show_alert=True)
    finally:
        conn.close()

@dp.callback_query(lambda call: call.data.startswith("remove_ongoing_"))
async def remove_ongoing_confirm(call: types.CallbackQuery):
    anime_code = call.data.replace("remove_ongoing_", "")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"confirm_remove_ongoing_{anime_code}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="remove_ongoing")
        ]
    ])
    
    await call.message.edit_text(
        f"⚠️ Bu animeni ongoing ro'yxatidan o'chirishni tasdiqlaysizmi?",
        reply_markup=keyboard
    )

@dp.callback_query(lambda call: call.data.startswith("confirm_remove_ongoing_"))
async def remove_ongoing_final(call: types.CallbackQuery):
    anime_code = call.data.replace("confirm_remove_ongoing_", "")
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM ongoing_anime WHERE anime_code = ?", (anime_code,))
        conn.commit()
        await call.answer("✅ Anime ongoing ro'yxatidan o'chirildi!", show_alert=True)
        await manage_ongoing_anime(call)
    except Exception as e:
        await call.answer(f"❌ Xatolik: {str(e)}", show_alert=True)
    finally:
        conn.close()

@dp.message(lambda message: message.text == "🔙 Admin Panel")
async def back_to_admin_panel(message: types.Message):
    if not await check_admin(message.from_user.id, message=message):
        return
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
           [KeyboardButton(text="🎥 Anime Sozlash"), KeyboardButton(text="📢 Kanal Sozlash")],
            [KeyboardButton(text="📝 Post Tayyorlash"), KeyboardButton(text="🎞 Serial Post Qilish")],
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="👥 Obunachilar")],
            [KeyboardButton(text="👨‍💻 Adminlar"), KeyboardButton(text="❓ Savollar")],
            [KeyboardButton(text="🔙 Bosh Menyu")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "👨‍💻 Admin Panelga xush kelibsiz!",
        reply_markup=keyboard
    )

@dp.message(lambda message: message.text == "➕ Anime Qo'shish")
async def add_anime_menu(message: types.Message):
    if not await check_admin(message.from_user.id, message=message):
        return
    
    user_state[message.from_user.id] = {"state": "waiting_anime_title"}
    await message.answer("🎬 Anime nomini yuboring:",
                       reply_markup=ReplyKeyboardMarkup(
                           keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]],
                           resize_keyboard=True
                       ))

@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_anime_title")
async def get_anime_title(message: types.Message):
    if message.text == "🔙 Bekor qilish":
        await cancel_anime_addition(message)
        return
    
    user_state[message.from_user.id] = {
        "state": "waiting_anime_country",
        "title": message.text
    }
    await message.answer("🌍 Davlatini kiriting:",
                       reply_markup=ReplyKeyboardMarkup(
                           keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]],
                           resize_keyboard=True
                       ))

@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_anime_country")
async def get_anime_country(message: types.Message):
    if message.text == "🔙 Bekor qilish":
        await cancel_anime_addition(message)
        return
    
    user_state[message.from_user.id].update({
        "state": "waiting_anime_language",
        "country": message.text
    })
    await message.answer("🇺🇿 Tilini kiriting:",
                       reply_markup=ReplyKeyboardMarkup(
                           keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]],
                           resize_keyboard=True
                       ))

@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_anime_language")
async def get_anime_language(message: types.Message):
    if message.text == "🔙 Bekor qilish":
        await cancel_anime_addition(message)
        return
    
    user_state[message.from_user.id].update({
        "state": "waiting_anime_year",
        "language": message.text
    })
    await message.answer("📆 Yilini kiriting (masalan: 2023):",
                       reply_markup=ReplyKeyboardMarkup(
                           keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]],
                           resize_keyboard=True
                       ))

@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_anime_year")
async def get_anime_year(message: types.Message):
    if message.text == "🔙 Bekor qilish":
        await cancel_anime_addition(message)
        return
    
    if not message.text.isdigit():
        await message.answer("❌ Noto'g'ri yil formatida. Qayta kiriting:",
                           reply_markup=ReplyKeyboardMarkup(
                               keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]],
                               resize_keyboard=True
                           ))
        return
    
    user_state[message.from_user.id].update({
        "state": "waiting_anime_genre",
        "year": int(message.text)
    })
    await message.answer("🎞 Janrini kiriting (masalan: Action, Drama):",
                       reply_markup=ReplyKeyboardMarkup(
                           keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]],
                           resize_keyboard=True
                       ))

@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_anime_genre")
async def get_anime_genre(message: types.Message):
    if message.text == "🔙 Bekor qilish":
        await cancel_anime_addition(message)
        return
    
    user_state[message.from_user.id].update({
        "state": "waiting_anime_description",
        "genre": message.text
    })
    await message.answer("📝 Anime haqida qisqacha tavsif yozing:",
                       reply_markup=ReplyKeyboardMarkup(
                           keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]],
                           resize_keyboard=True
                       ))

@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_anime_description")
async def get_anime_description(message: types.Message):
    if message.text == "🔙 Bekor qilish":
        await cancel_anime_addition(message)
        return
    
    user_state[message.from_user.id].update({
        "state": "waiting_anime_image",
        "description": message.text
    })
    await message.answer("🖼 Anime uchun rasm (PNG/JPG) yoki qisqa video (MP4) yuboring:",
                       reply_markup=ReplyKeyboardMarkup(
                           keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]],
                           resize_keyboard=True
                       ))
@dp.message(
    lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_anime_image" 
    and (message.photo or message.video)
)
async def get_anime_media(message: types.Message):
    media_file_id = None
    media_type = None
    
    if message.photo:
        media_file_id = message.photo[-1].file_id
        media_type = 'photo'
    elif message.video:
        media_file_id = message.video.file_id
        media_type = 'video'
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) FROM anime")
        anime_code = str(cursor.fetchone()[0] + 1)
        
        cursor.execute('''INSERT INTO anime (
            code, title, country, language, year, genre, description, image, video
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
            anime_code, 
            user_state[message.from_user.id]["title"],
            user_state[message.from_user.id]["country"],
            user_state[message.from_user.id]["language"],
            user_state[message.from_user.id]["year"],
            user_state[message.from_user.id]["genre"],
            user_state[message.from_user.id]["description"],
            media_file_id if media_type == 'photo' else None,
            media_file_id if media_type == 'video' else None
        ))
        
        conn.commit()
        
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🎥 Anime Sozlash")],
                [KeyboardButton(text="🔙 Admin Panel")]
            ],
            resize_keyboard=True
        )
        
        if media_type == 'photo':
            await message.answer_photo(
                media_file_id,
                caption=f"✅ Anime muvaffaqiyatli qo'shildi!\n\n"
                       f"🎬 Nomi: {user_state[message.from_user.id]['title']}\n"
                       f"🌍 Davlati: {user_state[message.from_user.id]['country']}\n"
                       f"🇺🇿 Tili: {user_state[message.from_user.id]['language']}\n"
                       f"📆 Yili: {user_state[message.from_user.id]['year']}\n"
                       f"🎞 Janri: {user_state[message.from_user.id]['genre']}\n\n"
                       f"🔢 Anime kodi: {anime_code}",
                reply_markup=keyboard
            )
        else:
            await message.answer_video(
                media_file_id,
                caption=f"✅ Anime muvaffaqiyatli qo'shildi!\n\n"
                       f"🎬 Nomi: {user_state[message.from_user.id]['title']}\n"
                       f"🌍 Davlati: {user_state[message.from_user.id]['country']}\n"
                       f"🇺🇿 Tili: {user_state[message.from_user.id]['language']}\n"
                       f"📆 Yili: {user_state[message.from_user.id]['year']}\n"
                       f"🎞 Janri: {user_state[message.from_user.id]['genre']}\n\n"
                       f"🔢 Anime kodi: {anime_code}",
                reply_markup=keyboard
            )
        
        del user_state[message.from_user.id]
        
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        conn.close()

async def cancel_anime_addition(message: types.Message):
    if message.from_user.id in user_state:
        del user_state[message.from_user.id]
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Anime Qo'shish")],
            [KeyboardButton(text="✏️ Anime Tahrirlash")],
            [KeyboardButton(text="🗑 Anime O'chirish")],
            [KeyboardButton(text="🎞 Qism Qo'shish")],
            [KeyboardButton(text="🔙 Admin Panel")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "❌ Anime qo'shish bekor qilindi.",
        reply_markup=keyboard
    )

# Edit animedwd
@dp.message(lambda message: message.text == "✏️ Anime Tahrirlash")
async def edit_anime_menu(message: types.Message):
    if not await check_admin(message.from_user.id, message=message):
        return
    
    user_state[message.from_user.id] = {"state": "waiting_anime_code_for_edit"}
    await message.answer("✏️ Tahrirlash uchun anime kodini yuboring:")

@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_anime_code_for_edit")
async def get_anime_for_edit(message: types.Message):
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM anime WHERE code = ?", (message.text,))
    anime = cursor.fetchone()
    
    if anime:
        user_state[message.from_user.id] = {
            "state": "editing_anime",
            "anime_code": message.text
        }
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Nomi", callback_data="edit_title")],
            [InlineKeyboardButton(text="🌍 Davlati", callback_data="edit_country")],
            [InlineKeyboardButton(text="🇺🇿 Tili", callback_data="edit_language")],
            [InlineKeyboardButton(text="📆 Yili", callback_data="edit_year")],
            [InlineKeyboardButton(text="🎞 Janri", callback_data="edit_genre")],
            [InlineKeyboardButton(text="📝 Tavsif", callback_data="edit_description")],
            [InlineKeyboardButton(text="🖼 Rasm", callback_data="edit_image")]
        ])
        
        await message.answer("Qaysi maydonni tahrirlamoqchisiz?", reply_markup=keyboard)
    else:
        await message.answer("❌ Bunday kodli anime topilmadi")
    
    conn.close()

@dp.callback_query(lambda call: call.data.startswith("edit_"))
async def edit_anime_field(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    field = call.data.replace("edit_", "")
    user_state[call.from_user.id]["editing_field"] = field
    await call.message.answer(f"Yangi {field} qiymatini yuboring:")
    await call.answer()

@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("editing_field"))
async def save_edited_field(message: types.Message):
    user_data = user_state[message.from_user.id]
    field = user_data["editing_field"]
    anime_code = user_data["anime_code"]
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        if field == "image":
            if not message.photo:
                await message.answer("❌ Iltimos, rasm yuboring!")
                return
            new_value = message.photo[-1].file_id
        else:
            new_value = message.text
        
        cursor.execute(f"UPDATE anime SET {field} = ? WHERE code = ?", (new_value, anime_code))
        conn.commit()
        
        await message.answer(f"✅ Anime {field} muvaffaqiyatli yangilandi!")
        
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    
    finally:
        if "editing_field" in user_state[message.from_user.id]:
            del user_state[message.from_user.id]["editing_field"]
        conn.close()

# Delete anime
@dp.message(lambda message: message.text == "🗑 Anime O'chirish")
async def delete_anime_menu(message: types.Message):
    if not await check_admin(message.from_user.id, message=message):
        return
    
    user_state[message.from_user.id] = {"state": "waiting_anime_code_for_delete"}
    await message.answer("🗑 O'chirish uchun anime kodini yuboring:")

@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_anime_code_for_delete")
async def delete_anime(message: types.Message):
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM episodes WHERE anime_code = ?", (message.text,))
        cursor.execute("DELETE FROM anime WHERE code = ?", (message.text,))
        cursor.execute("DELETE FROM favorites WHERE anime_code = ?", (message.text,))
        conn.commit()
        
        await message.answer("✅ Anime va uning barcha qismlari muvaffaqiyatli o'chirildi!")
        
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    
    finally:
        del user_state[message.from_user.id]
        conn.close()

# Add episode
@dp.message(lambda message: message.text == "🔙 Bekor qilish")
async def cancel_episode_adding(message: types.Message):
    if not await check_admin(message.from_user.id, message=message):
        return
    
    if message.from_user.id in user_state:
        del user_state[message.from_user.id]
    
    # Admin panelga qaytish
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
         [KeyboardButton(text="🎥 Anime Sozlash"), KeyboardButton(text="📢 Kanal Sozlash")],
            [KeyboardButton(text="📝 Post Tayyorlash"), KeyboardButton(text="🎞 Serial Post Qilish")],
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="👥 Obunachilar")],
            [KeyboardButton(text="👨‍💻 Adminlar"), KeyboardButton(text="❓ Savollar")],
            [KeyboardButton(text="🔙 Bosh Menyu")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "Qism qo'shish bekor qilindi.\nAdmin panelga qaytildi:",
        reply_markup=keyboard
    )

@dp.message(lambda message: message.text == "🏠 Bosh Menyu")
async def main_menu(message: types.Message):
    await message.answer("Bosh menyu:",
                       reply_markup=ReplyKeyboardMarkup(
                           keyboard=[
                               [KeyboardButton(text="🎞 Qism Qo'shish")],
                               [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="⚙️ Sozlamalar")]
                           ],
                           resize_keyboard=True
                       ))

@dp.message(lambda message: message.text == "🎞 Qism Qo'shish")
async def add_episode_menu(message: types.Message):
    if not await check_admin(message.from_user.id, message=message):
        await main_menu(message)
        return
    
    user_state[message.from_user.id] = {"state": "waiting_anime_code_for_episode"}
    await message.answer("🎞 Qism qo'shish uchun anime kodini yuboring:",
                       reply_markup=ReplyKeyboardMarkup(
                           keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]],
                           resize_keyboard=True
                       ))

@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_anime_code_for_episode")
async def get_anime_for_episode(message: types.Message):
    if message.text == "🔙 Bekor qilish":
        await cancel_episode_adding(message)
        return
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT title FROM anime WHERE code = ?", (message.text,))
    anime = cursor.fetchone()
    
    if anime:
        user_state[message.from_user.id] = {
            "state": "waiting_episode_video",
            "anime_code": message.text,
            "anime_title": anime[0]
        }
        
        cursor.execute("SELECT MAX(episode_number) FROM episodes WHERE anime_code = ?", (message.text,))
        last_episode = cursor.fetchone()[0] or 0
        
        await message.answer(
            f"🎬 {anime[0]}\n\n"
            f"📹 {last_episode + 1}-qism videosini yuboring (MP4 formatida):",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]],
                resize_keyboard=True
            ))
    else:
        await message.answer("❌ Bunday kodli anime topilmadi. Qayta urinib ko'ring:")
    
    conn.close()

@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_episode_video")
async def handle_episode_video_or_cancel(message: types.Message):
    if message.text == "🔙 Bekor qilish":
        await cancel_episode_adding(message)
        return
    
    if message.video:
        video = message.video
        file_id = video.file_id
        
        conn = sqlite3.connect('anime_bot.db')
        cursor = conn.cursor()
        
        try:
            anime_code = user_state[message.from_user.id]["anime_code"]
            anime_title = user_state[message.from_user.id]["anime_title"]
            
            cursor.execute("SELECT MAX(episode_number) FROM episodes WHERE anime_code = ?", (anime_code,))
            last_episode = cursor.fetchone()[0] or 0
            
            new_episode_number = last_episode + 1
            
            cursor.execute('''INSERT INTO episodes (anime_code, episode_number, video_file_id) 
                              VALUES (?, ?, ?)''',
                           (anime_code, new_episode_number, file_id))
            
            conn.commit()
            
            await notify_subscribers(anime_code, new_episode_number)
            
            await message.answer(
                f"✅ {anime_title} animega {new_episode_number}-qism muvaffaqiyatli qo'shildi!\n\n"
                f"📹 {new_episode_number + 1}-qism videosini yuboring (agar qo'shmoqchi bo'lsangiz)\n\n"
                f"Aks holda 🔙 Bekor qilish tugmasini bosing",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]],
                    resize_keyboard=True
                ))
            
        except Exception as e:
            await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
        finally:
            conn.close()
    else:
        await message.answer("Iltimos, faqat video yuboring yoki 🔙 Bekor qilish tugmasini bosing")

@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_multiple_episodes" and message.video)
async def get_multiple_episodes_video(message: types.Message):
    video = message.video
    file_id = video.file_id
    
    user_data = user_state[message.from_user.id]
    user_data["qism_fayllari"].append(file_id)
    user_data["qolgan_qismlar"] -= 1
    
    if user_data["qolgan_qismlar"] > 0:
        user_data["hozirgi_qism"] += 1
        await message.answer(
            f"✅ {user_data['hozirgi_qism']-1}-qism qabul qilindi.\n\n"
            f"Qoldi: {user_data['qolgan_qismlar']} ta\n\n"
            f"{user_data['hozirgi_qism']}-qism videosini yuboring:"
        )
        return
    
    # Barcha qismlar qabul qilindi, endi bazaga saqlaymiz
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        anime_code = user_data["anime_code"]
        anime_title = user_data["anime_title"]
        
        cursor.execute("SELECT COUNT(*) FROM episodes WHERE anime_code = ?", (anime_code,))
        boshlangich_qism = cursor.fetchone()[0] + 1
        
        for i, file_id in enumerate(user_data["qism_fayllari"]):
            qism_raqami = boshlangich_qism + i
            cursor.execute('''INSERT INTO episodes (anime_code, episode_number, video_file_id) 
                              VALUES (?, ?, ?)''',
                           (anime_code, qism_raqami, file_id))
            await notify_subscribers(anime_code, qism_raqami)
        
        conn.commit()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎞 Yana Qism Qo'shish", callback_data=f"add_episode_{anime_code}")],
            [InlineKeyboardButton(text="➕ Bir nechta qism qo'shish", callback_data=f"add_multiple_{anime_code}")],
            [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="back_to_admin")]
        ])
        
        await message.answer(
            f"✅ {anime_title} animega {len(user_data['qism_fayllari'])} ta yangi qism muvaffaqiyatli qo'shildi!\n\n"
            f"Qo'shilgan qismlar: {boshlangich_qism}-{boshlangich_qism + len(user_data['qism_fayllari']) - 1}",
            reply_markup=keyboard
        )
        
        del user_state[message.from_user.id]
        
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        conn.close()

@dp.callback_query(lambda c: c.data.startswith("add_episode_"))
async def add_another_episode(callback: types.CallbackQuery):
    anime_code = callback.data.replace("add_episode_", "")
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT title FROM anime WHERE code = ?", (anime_code,))
    anime = cursor.fetchone()
    
    if anime:
        user_state[callback.from_user.id] = {
            "state": "waiting_episode_video",
            "anime_code": anime_code,
            "anime_title": anime[0],
            "rejim": "bitta"
        }
        await callback.message.answer(f"🎬 {anime[0]}\n\n📹 Yangi qism videosini yuboring (MP4 formatida):",
                            reply_markup=ReplyKeyboardMarkup(
                                keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]],
                                resize_keyboard=True
                            ))
    else:
        await callback.message.answer("❌ Bunday kodli anime topilmadi.")
    
    conn.close()
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("add_multiple_"))
async def add_multiple_episodes(callback: types.CallbackQuery):
    anime_code = callback.data.replace("add_multiple_", "")
    
    await callback.message.answer(
        f"📝 Qancha qism qo'shmoqchisiz?\n\n"
        f"Anime kodi: <code>{anime_code}</code>\n\n"
        f"Quyidagi formatda yuboring:\n"
        f"<code>{anime_code}:qismlar_soni</code>\n\n"
        f"Masalan: <code>{anime_code}:3</code>",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]],
            resize_keyboard=True
        )
    )
    
    user_state[callback.from_user.id] = {
        "state": "waiting_episode_count",
        "anime_code": anime_code
    }
    
    await callback.answer()

@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_episode_count")
async def process_episode_count(message: types.Message):
    if message.text == "🔙 Bekor qilish":
        await cancel_post_action(message)
        return
    
    anime_code = user_state[message.from_user.id]["anime_code"]
    
    if ":" in message.text:
        parts = message.text.split(":")
        if len(parts) == 2 and parts[1].isdigit() and parts[0] == anime_code:
            qismlar_soni = int(parts[1])
            
            conn = sqlite3.connect('anime_bot.db')
            cursor = conn.cursor()
            
            cursor.execute("SELECT title FROM anime WHERE code = ?", (anime_code,))
            anime = cursor.fetchone()
            
            if anime:
                user_state[message.from_user.id] = {
                    "state": "waiting_multiple_episodes",
                    "anime_code": anime_code,
                    "anime_title": anime[0],
                    "qolgan_qismlar": qismlar_soni,
                    "hozirgi_qism": 1,
                    "qism_fayllari": []
                }
                await message.answer(
                    f"🎬 {anime[0]}\n\n"
                    f"📹 {qismlar_soni} ta qism qo'shish rejimi\n\n"
                    f"1-qism videosini yuboring (MP4 formatida):",
                    reply_markup=ReplyKeyboardMarkup(
                        keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]],
                        resize_keyboard=True
                    )
                )
                conn.close()
                return
    
    await message.answer("❌ Noto'g'ri format. Iltimos, quyidagi formatda yuboring:\n"
                        f"<code>{anime_code}:qismlar_soni</code>\n\n"
                        f"Masalan: <code>{anime_code}:5</code>")

# ==================== CHANNEL SETTINGS ====================

@dp.message(lambda message: message.text == "📢 Kanal Sozlash")
async def channel_settings(message: types.Message):
    if not await check_admin(message.from_user.id, message=message):
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔔 Majburiy Obuna Kanal", callback_data="mandatory_channel_menu")],
        [InlineKeyboardButton(text="📢 Post Kanal", callback_data="post_channel_menu")],
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="back_to_admin")]
    ])
    await message.answer("📢 Kanal Sozlash", reply_markup=keyboard)

@dp.callback_query(lambda call: call.data == "post_channel_menu")
async def post_channel_menu(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id, channel_name FROM channels WHERE channel_type = 'post'")
    channel = cursor.fetchone()
    conn.close()
    
    text = "📢 Post kanal: " + (f"{channel[1]} (ID: {channel[0]})" if channel else "❌ O'rnatilmagan")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Post Kanal Qo'shish", callback_data="add_post_channel")],
        [InlineKeyboardButton(text="➖ Post Kanal O'chirish", callback_data="remove_post_channel")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_channels")]
    ])
    
    await call.message.edit_text(text, reply_markup=keyboard)

@dp.callback_query(lambda call: call.data == "add_post_channel")
async def add_post_channel_start(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    user_state[call.from_user.id] = {"state": "waiting_post_channel"}
    await call.message.edit_text(
        "Yangi post kanalini quyidagi formatlardan birida yuboring:\n\n"
        "• @channel_username\n"
        "• https://t.me/channel\n"
        "• -100123456789 (private kanal ID)\n\n"
        "Bot kanalda admin bo'lishi shart!"
    )

@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_post_channel")
async def process_post_channel(message: types.Message):
    raw_input = message.text.strip()
    
    try:
        if raw_input.startswith(("https://t.me/", "t.me/")):
            channel_id = "@" + raw_input.split("/")[-1]
        elif raw_input.startswith("-100") and raw_input[4:].isdigit():
            channel_id = raw_input
        elif raw_input.startswith("@"):
            channel_id = raw_input
        else:
            raise ValueError("Noto'g'ri format")
        
        chat = await bot.get_chat(channel_id)
        
        bot_member = await bot.get_chat_member(chat.id, (await bot.get_me()).id)
        if bot_member.status != ChatMemberStatus.ADMINISTRATOR:
            raise ValueError("Bot kanalda admin emas")
        
        with sqlite3.connect('anime_bot.db') as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO channels (channel_type, channel_id, channel_name)
                VALUES ('post', ?, ?)
            """, (channel_id, chat.title))
            conn.commit()
        
        await message.answer(
            f"✅ Post kanal qo'shildi!\n"
            f"📢 Nomi: {chat.title}\n"
            f"🆔 ID: {channel_id}"
        )
        await post_channel_menu(await bot.send_message(message.from_user.id, "Post kanal menyusi:"))
        
    except ValueError as e:
        await message.answer(f"❌ {str(e)}\nQayta urinib ko'ring:")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")
    finally:
        if 'state' in user_state.get(message.from_user.id, {}):
            del user_state[message.from_user.id]["state"]

@dp.callback_query(lambda call: call.data == "remove_post_channel")
async def remove_post_channel(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    with sqlite3.connect('anime_bot.db') as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM channels WHERE channel_type = 'post'")
        conn.commit()
    
    await call.answer("✅ Post kanal o'chirildi!", show_alert=True)
    await post_channel_menu(call)

@dp.callback_query(lambda call: call.data == "back_to_channels")
async def back_to_channels_menu(call: types.CallbackQuery):
    await channel_settings(await bot.send_message(call.from_user.id, "Kanal sozlamalari:"))

@dp.callback_query(lambda call: call.data == "mandatory_channel_menu")
async def mandatory_channel_menu(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    try:
        with sqlite3.connect('anime_bot.db') as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, channel_id, channel_name, channel_type 
                FROM channels 
                WHERE channel_type IN ('mandatory', 'additional_mandatory')
                ORDER BY 
                    CASE WHEN channel_type = 'mandatory' THEN 1 ELSE 2 END,
                    id
            """)
            channels = cursor.fetchall()
        
        text = "🔔 Majburiy obuna kanallari:\n\n"
        if channels:
            for idx, (db_id, channel_id, channel_name, channel_type) in enumerate(channels, 1):
                text += f"{idx}. {channel_name or channel_id} ({'Asosiy' if channel_type == 'mandatory' else 'Qoʻshimcha'})\n"
        else:
            text += "ℹ️ Hozircha kanallar qo'shilmagan"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Asosiy kanal qo'shish", callback_data="add_main_mandatory")],
            [InlineKeyboardButton(text="➕ Qo'shimcha kanal qo'shish", callback_data="add_additional_mandatory")],
            [InlineKeyboardButton(text="➖ Kanal o'chirish", callback_data="remove_mandatory_channel")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_channels")]
        ])
        
        await call.message.edit_text(text, reply_markup=keyboard)
    except Exception as e:
        await call.answer(f"❌ Xatolik: {str(e)}", show_alert=True)

@dp.callback_query(lambda call: call.data == "add_main_mandatory")
async def add_main_mandatory_channel(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    user_state[call.from_user.id] = {
        "state": "waiting_main_mandatory_channel",
        "channel_type": "mandatory"
    }
    await call.message.answer(
        "Asosiy majburiy kanalni yuboring (faqat 1 ta bo'lishi mumkin):\n\n"
        "Format: @username yoki https://t.me/... yoki -100...",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="mandatory_channel_menu")]
        ])
    )

@dp.callback_query(lambda call: call.data == "add_additional_mandatory")
async def add_additional_mandatory_channel(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    user_state[call.from_user.id] = {
        "state": "waiting_additional_mandatory_channel",
        "channel_type": "additional_mandatory"
    }
    await call.message.answer(
        "Qo'shimcha majburiy kanalni yuboring (cheksiz sonida qo'shishingiz mumkin):\n\n"
        "Format: @username yoki https://t.me/... yoki -100...",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="mandatory_channel_menu")]
        ])
    )

@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") in 
            ["waiting_main_mandatory_channel", "waiting_additional_mandatory_channel"])
async def process_new_mandatory_channel(message: types.Message):
    user_data = user_state[message.from_user.id]
    channel_type = user_data["channel_type"]
    
    try:
        raw_input = message.text.strip()
        if raw_input.startswith(("https://t.me/", "t.me/")):
            channel_id = "@" + raw_input.split("/")[-1]
        elif raw_input.startswith("-100") and raw_input[4:].isdigit():
            channel_id = raw_input
        elif raw_input.startswith("@"):
            channel_id = raw_input
        else:
            raise ValueError("Noto'g'ri format")
        
        chat = await bot.get_chat(channel_id)
        
        bot_member = await bot.get_chat_member(chat.id, (await bot.get_me()).id)
        if bot_member.status != ChatMemberStatus.ADMINISTRATOR:
            raise ValueError("Bot kanalda admin emas")
        
        with sqlite3.connect('anime_bot.db') as conn:
            cursor = conn.cursor()
            
            if channel_type == "mandatory":
                cursor.execute("DELETE FROM channels WHERE channel_type = 'mandatory'")
            
            cursor.execute("""
                INSERT INTO channels (channel_type, channel_id, channel_name)
                VALUES (?, ?, ?)
            """, (channel_type, channel_id, chat.title))
            conn.commit()
        
        await message.answer(
            f"✅ {'Asosiy' if channel_type == 'mandatory' else 'Qoʻshimcha'} kanal qo'shildi!\n"
            f"📢 Nomi: {chat.title}\n"
            f"🆔 ID: {channel_id}"
        )
        
        del user_state[message.from_user.id]
        
        await mandatory_channel_menu(await bot.send_message(message.from_user.id, "Kanal menyusi:"))
        
    except ValueError as e:
        await message.answer(f"❌ {str(e)}\nQayta urinib ko'ring:")
    except exceptions.TelegramAPIError as e:
        await message.answer(f"❌ Telegram xatosi: {str(e)}")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")
    finally:
        user_state.pop(message.from_user.id, None)

@dp.callback_query(lambda call: call.data == "remove_mandatory_channel")
async def remove_mandatory_channel_start(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    try:
        with sqlite3.connect('anime_bot.db') as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, channel_id, channel_name, channel_type 
                FROM channels 
                WHERE channel_type IN ('mandatory', 'additional_mandatory')
                ORDER BY id
            """)
            channels = cursor.fetchall()
        
        if not channels:
            return await call.answer("ℹ️ O'chirish uchun kanal mavjud emas", show_alert=True)
        
        buttons = []
        for idx, (db_id, cid, name, ctype) in enumerate(channels, 1):
            channel_type = "Asosiy" if ctype == 'mandatory' else "Qo'shimcha"
            buttons.append([
                InlineKeyboardButton(
                    text=f"{idx}. {name or cid} ({channel_type})",
                    callback_data=f"remove_channel_{db_id}"
                )
            ])
        
        # Pastga "Barchasini o'chirish" va "Orqaga" tugmalarini qo'shamiz
        buttons.append([
            InlineKeyboardButton(text="🗑 Barchasini O'chirish", callback_data="remove_all_channels"),
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="mandatory_channel_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await call.message.edit_text(
            "O'chirish uchun kanalni tanlang:\n\n" +
            "\n".join([f"{idx}. {name or cid} ({'Asosiy' if ctype == 'mandatory' else 'Qoʻshimcha'})" 
                      for idx, (_, cid, name, ctype) in enumerate(channels, 1)]),
            reply_markup=keyboard
        )
        
    except Exception as e:
        await call.answer(f"❌ Xatolik: {str(e)}", show_alert=True)

@dp.callback_query(lambda call: call.data == "remove_all_channels")
async def remove_all_channels_confirm(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data="confirm_remove_all"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="remove_mandatory_channel")
        ]
    ])
    
    await call.message.edit_text(
        "⚠️ Barcha majburiy kanallarni o'chirishni tasdiqlaysizmi?\n"
        "Bu amalni qaytarib bo'lmaydi!",
        reply_markup=keyboard
    )

@dp.callback_query(lambda call: call.data == "confirm_remove_all")
async def remove_all_channels(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    try:
        with sqlite3.connect('anime_bot.db') as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM channels WHERE channel_type IN ('mandatory', 'additional_mandatory')")
            conn.commit()
        
        await call.answer("✅ Barcha majburiy kanallar o'chirildi!", show_alert=True)
        await mandatory_channel_menu(call)
    except Exception as e:
        await call.answer(f"❌ Xatolik: {str(e)}", show_alert=True)

@dp.callback_query(lambda call: call.data.startswith("remove_channel_"))
async def remove_mandatory_channel_confirm(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    channel_db_id = call.data.replace("remove_channel_", "")
    
    try:
        with sqlite3.connect('anime_bot.db') as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT channel_id, channel_name, channel_type 
                FROM channels 
                WHERE id = ?
            """, (channel_db_id,))
            channel = cursor.fetchone()
            
            if not channel:
                return await call.answer("❌ Kanal topilmadi!", show_alert=True)
            
            channel_id, channel_name, channel_type = channel
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"confirm_remove_{channel_db_id}"),
                    InlineKeyboardButton(text="❌ Bekor qilish", callback_data="remove_mandatory_channel")
                ]
            ])
            
            await call.message.edit_text(
                f"⚠️ Kanalni o'chirishni tasdiqlaysizmi?\n\n"
                f"📢 Nomi: {channel_name or 'Nomsiz'}\n"
                f"🆔 ID: {channel_id}\n"
                f"📌 Turi: {'Asosiy' if channel_type == 'mandatory' else 'Qoʻshimcha'}",
                reply_markup=keyboard
            )
            
    except Exception as e:
        await call.answer(f"❌ Xatolik: {str(e)}", show_alert=True)

@dp.callback_query(lambda call: call.data.startswith("confirm_remove_"))
async def remove_channel_final(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    channel_db_id = call.data.replace("confirm_remove_", "")
    
    try:
        with sqlite3.connect('anime_bot.db') as conn:
            cursor = conn.cursor()
            
            # Avval kanal ma'lumotlarini olamiz (xabarda ko'rsatish uchun)
            cursor.execute("""
                SELECT channel_id, channel_name, channel_type 
                FROM channels 
                WHERE id = ?
            """, (channel_db_id,))
            channel = cursor.fetchone()
            
            if not channel:
                return await call.answer("❌ Kanal topilmadi!", show_alert=True)
            
            channel_id, channel_name, channel_type = channel
            
            # Kanalni o'chiramiz
            cursor.execute("DELETE FROM channels WHERE id = ?", (channel_db_id,))
            conn.commit()
            
            await call.answer(
                f"✅ Kanal o'chirildi: {channel_name or channel_id}",
                show_alert=True
            )
            await mandatory_channel_menu(call)
            
    except Exception as e:
        await call.answer(f"❌ Xatolik: {str(e)}", show_alert=True)
@dp.message(lambda message: message.text == "👨‍💻 Adminlar")
async def manage_admins(message: types.Message):
    if not await check_admin(message.from_user.id, message=message):
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Admin Qo'shish", callback_data="add_admin")],
        [InlineKeyboardButton(text="🗑 Admin O'chirish", callback_data="remove_admin")],
        [InlineKeyboardButton(text="📋 Adminlar Ro'yxati", callback_data="list_admins")],
        [InlineKeyboardButton(text="📦 Bazani Ko'chirish", callback_data="transfer_db")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_admin")]
    ])
    
    await message.answer("👨‍💻 Adminlar boshqaruvi", reply_markup=keyboard)

# Add these new handlers
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TransferDB(StatesGroup):
    waiting_target_bot = State()
    waiting_db_file = State()
    waiting_confirmation = State()

@dp.callback_query(F.data == "transfer_db")
async def transfer_db_start(call: types.CallbackQuery):
    """Handle database transfer initiation"""
    if not await check_admin(call.from_user.id, call=call, require_owner=True):
        return
    
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📤 Bazani Yuklab Olish", callback_data="download_db"),
        InlineKeyboardButton(text="📥 Bazani Yuklash", callback_data="upload_db"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="manage_admins")
    )
    builder.adjust(1)
    
    await call.message.edit_text(
        "📦 Bazani boshqa botga ko'chirish:\n\n"
        "1. 📤 Yuklab olish - hozirgi bazani fayl sifatida yuklab olish\n"
        "2. 📥 Yuklash - boshqa botdan yuklangan bazani qabul qilish",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "download_db")
async def download_database(call: types.CallbackQuery):
    """Handle database download request"""
    if not await check_admin(call.from_user.id, call=call, require_owner=True):
        return
    
    temp_dir = tempfile.mkdtemp()
    try:
        db_path = 'anime_bot.db'
        if not os.path.exists(db_path):
            await call.answer("❌ Baza fayli topilmadi!", show_alert=True)
            return
            
        temp_db_path = os.path.join(temp_dir, "anime_bot.db")
        shutil.copy2(db_path, temp_db_path)
        
        with open(temp_db_path, 'rb') as db_file:
            await bot.send_document(
                chat_id=call.from_user.id,
                document=types.BufferedInputFile(
                    db_file.read(),
                    filename="anime_bot.db"
                ),
                caption="📦 Bot bazasi fayli"
            )
        
        await call.answer("✅ Bazani yuklab olish muvaffaqiyatli yakunlandi!", show_alert=True)
    except Exception as e:
        logger.error(f"Database download error: {e}")
        await call.answer(f"❌ Xatolik yuz berdi: {str(e)}", show_alert=True)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@dp.callback_query(F.data == "upload_db")
async def upload_db_start(call: types.CallbackQuery, state: FSMContext):
    """Start database upload process - simplified version without bot token requirement"""
    if not await check_admin(call.from_user.id, call=call, require_owner=True):
        return
    
    await state.set_state(TransferDB.waiting_db_file)
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="cancel_db_upload"))
    
    await call.message.edit_text(
        "📥 Bazani yuklash:\n\n"
        "1. SQLite formatidagi baza faylini yuboring\n"
        "2. Fayl .db yoki .sqlite kengaytmasiga ega bo'lishi kerak\n"
        "3. Yuklash jarayoni avtomatik boshlanadi\n\n"
        "⚠️ Diqqat: Bu mavjud bazani to'liq almashtirishi mumkin!",
        reply_markup=builder.as_markup()
    )

@dp.message(TransferDB.waiting_target_bot)
async def get_target_bot(message: types.Message, state: FSMContext):
    """Validate target bot information"""
    target_bot = message.text.strip()
    
    # Validate input format
    is_token = ":" in target_bot and len(target_bot.split(":")) == 2
    is_username = target_bot.startswith("@") and len(target_bot) > 1
    
    if not (is_token or is_username):
        await message.answer(
            "❌ Noto'g'ri format! Bot tokeni yoki username ni to'g'ri kiriting:\n\n"
            "Misol: <code>1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11</code> yoki <code>@bot_username</code>",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(target_bot=target_bot)
    await state.set_state(TransferDB.waiting_db_file)
    
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔙 Bekor qilish"))
    
    await message.answer(
        "📎 Endi yuklamoqchi bo'lgan bazani fayl sifatida yuboring (anime_bot.db)",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

@dp.message(TransferDB.waiting_db_file, F.document)
async def process_db_file(message: types.Message, state: FSMContext):
    """Process uploaded database file"""
    if not message.document or message.document.file_name != "anime_bot.db":
        await message.answer("❌ Iltimos, anime_bot.db faylini yuboring!")
        return
    
    temp_dir = tempfile.mkdtemp()
    temp_db_path = os.path.join(temp_dir, "anime_bot.db")
    
    try:
        # Download the file
        file = await bot.get_file(message.document.file_id)
        await bot.download_file(file.file_path, temp_db_path)
        
        # Validate database structure
        validation_result = await validate_database(temp_db_path)
        if not validation_result["valid"]:
            raise ValueError(validation_result["message"])
        
        # Store temporary file info
        await state.update_data(
            temp_db_path=temp_db_path,
            temp_dir=temp_dir,
            anime_count=validation_result["anime_count"],
            episodes_count=validation_result["episodes_count"],
            ongoing_count=validation_result["ongoing_count"]
        )
        
        # Show confirmation
        builder = InlineKeyboardBuilder()
        builder.add(
            InlineKeyboardButton(text="✅ Qabul qilish", callback_data="confirm_db_transfer"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data="cancel_db_transfer")
        )
        
        await message.answer(
            f"📦 Bazani qabul qilish:\n\n"
            f"• Anime lar soni: {validation_result['anime_count']} ta\n"
            f"• Epizodlar soni: {validation_result['episodes_count']} ta\n"
            f"• Davom etayotganlar: {validation_result['ongoing_count']} ta\n\n"
            f"⚠️ Diqqat:\n"
            f"• Eski animelar saqlanib qoladi\n"
            f"• Yangi animelar qo'shiladi\n"
            f"• Bir xil kodli animelar yangilanmaydi\n\n"
            f"Bazani qabul qilishni tasdiqlaysizmi?",
            reply_markup=builder.as_markup()
        )
        
        await state.set_state(TransferDB.waiting_confirmation)
        
    except Exception as e:
        logger.error(f"Database processing error: {e}")
        await message.answer(f"❌ Xatolik: {str(e)}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        await state.clear()

async def validate_database(db_path: str) -> dict:
    """Validate the database structure and return counts"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check required tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        required_tables = {'anime', 'episodes', 'ongoing_anime'}
        
        missing_tables = required_tables - tables
        if missing_tables:
            return {
                "valid": False,
                "message": f"Quyidagi jadvallar topilmadi: {', '.join(missing_tables)}"
            }
        
        # Validate table structures
        try:
            cursor.execute("SELECT code, title FROM anime LIMIT 1")
            cursor.execute("SELECT anime_code, episode_number FROM episodes LIMIT 1")
            cursor.execute("SELECT anime_code FROM ongoing_anime LIMIT 1")
        except sqlite3.Error as e:
            return {
                "valid": False,
                "message": f"Jadval strukturasida xatolik: {str(e)}"
            }
        
        # Get counts
        cursor.execute("SELECT COUNT(*) FROM anime")
        anime_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM episodes")
        episodes_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ongoing_anime")
        ongoing_count = cursor.fetchone()[0]
        
        return {
            "valid": True,
            "anime_count": anime_count,
            "episodes_count": episodes_count,
            "ongoing_count": ongoing_count
        }
        
    except Exception as e:
        return {
            "valid": False,
            "message": f"Bazani tekshirishda xatolik: {str(e)}"
        }
    finally:
        if conn:
            conn.close()

@dp.callback_query(F.data == "confirm_db_transfer", StateFilter(TransferDB.waiting_confirmation))
async def confirm_db_transfer(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    temp_db_path = data.get('temp_db_path')
    temp_dir = data.get('temp_dir')

    if not temp_db_path or not os.path.exists(temp_db_path):
        await call.message.answer("❌ Vaqtinchalik baza fayli topilmadi.")
        await state.finish()
        return

    transferred = {'anime': 0, 'episodes': 0, 'ongoing': 0}
    skipped = {'anime': 0, 'episodes': 0, 'ongoing': 0}
    conflicts_resolved = 0
    added_anime = []
    conflict_anime = []

    try:
        with sqlite3.connect('anime_bot.db') as main_conn, sqlite3.connect(temp_db_path) as temp_conn:
            # Enable foreign keys and WAL mode for better performance
            main_conn.execute("PRAGMA foreign_keys = ON")
            main_conn.execute("PRAGMA journal_mode = WAL")
            
            main_cursor = main_conn.cursor()
            temp_cursor = temp_conn.cursor()

            # 1. Create temporary mapping table
            main_cursor.execute("""
                CREATE TEMPORARY TABLE IF NOT EXISTS code_mapping (
                    old_code TEXT PRIMARY KEY,
                    new_code TEXT NOT NULL
                )
            """)
            
            # 2. First pass - transfer all anime with original codes where possible
            temp_cursor.execute("SELECT code, title, country, language, year, genre, description, image, video FROM anime")
            for row in temp_cursor.fetchall():
                original_code = row[0]
                title = row[1]
                new_code = original_code
                is_conflict = False

                # Check if anime with same code exists but different title (conflict)
                main_cursor.execute("SELECT title FROM anime WHERE code = ?", (original_code,))
                existing = main_cursor.fetchone()

                if existing:
                    if existing[0] == title:
                        # Exact match, no conflict
                        main_cursor.execute(
                            "INSERT OR IGNORE INTO code_mapping (old_code, new_code) VALUES (?, ?)",
                            (original_code, original_code)
                        )
                        skipped['anime'] += 1
                        continue
                    else:
                        # Conflict - generate new code
                        counter = 1
                        while True:
                            new_code = f"{original_code}_{counter}"
                            main_cursor.execute("SELECT 1 FROM anime WHERE code = ?", (new_code,))
                            if not main_cursor.fetchone():
                                break
                            counter += 1
                        is_conflict = True
                        conflicts_resolved += 1
                        conflict_anime.append(f"{title} (kod: {original_code} → {new_code})")

                try:
                    # Insert new anime
                    main_cursor.execute("""
                        INSERT OR IGNORE INTO anime (
                            code, title, country, language, year, genre, 
                            description, image, video
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (new_code, *row[1:]))

                    # Add to mapping table
                    main_cursor.execute(
                        "INSERT OR REPLACE INTO code_mapping (old_code, new_code) VALUES (?, ?)",
                        (original_code, new_code)
                    )
                    
                    if main_cursor.rowcount > 0:  # Only count if actually inserted
                        transferred['anime'] += 1
                        added_anime.append(f"{title} (kod: {new_code})")

                except sqlite3.Error as e:
                    skipped['anime'] += 1
                    logging.error(f"Anime insert error (code: {new_code}): {e}")
                    continue
            
            main_conn.commit()  # Commit anime inserts before episodes
            
            # 3. Transfer episodes with proper mapping
            temp_cursor.execute("""
                SELECT e.anime_code, e.episode_number, e.video_file_id
                FROM episodes e
                ORDER BY e.anime_code, e.episode_number
            """)

            for anime_code, ep_num, video_id in temp_cursor.fetchall():
                # Get new code from mapping
                main_cursor.execute(
                    "SELECT new_code FROM code_mapping WHERE old_code = ?",
                    (anime_code,)
                )
                mapping = main_cursor.fetchone()
                
                if not mapping:
                    skipped['episodes'] += 1
                    logging.warning(f"Episode skipped - no mapping for anime: {anime_code}")
                    continue

                new_code = mapping[0]
                
                try:
                    # Check if episode already exists
                    main_cursor.execute(
                        "SELECT 1 FROM episodes WHERE anime_code = ? AND episode_number = ?",
                        (new_code, ep_num)
                    )
                    
                    if main_cursor.fetchone():
                        skipped['episodes'] += 1
                        continue

                    # Insert new episode with proper foreign key reference
                    main_cursor.execute("""
                        INSERT INTO episodes (anime_code, episode_number, video_file_id) 
                        VALUES (?, ?, ?)
                    """, (new_code, ep_num, video_id))
                    
                    transferred['episodes'] += 1
                    
                except sqlite3.IntegrityError as e:
                    if "FOREIGN KEY constraint failed" in str(e):
                        # Anime doesn't exist in main DB - skip episode
                        skipped['episodes'] += 1
                        logging.error(f"Foreign key error - anime {new_code} not found for episode {ep_num}")
                    else:
                        raise
                except sqlite3.Error as e:
                    skipped['episodes'] += 1
                    logging.error(f"Episode insert error (anime: {new_code}, ep: {ep_num}): {e}")

            main_conn.commit()  # Commit episodes
            
            # 4. Transfer ongoing status
            temp_cursor.execute("SELECT anime_code FROM ongoing_anime")
            for (anime_code,) in temp_cursor.fetchall():
                main_cursor.execute(
                    "SELECT new_code FROM code_mapping WHERE old_code = ?",
                    (anime_code,)
                )
                mapping = main_cursor.fetchone()
                
                if not mapping:
                    skipped['ongoing'] += 1
                    continue

                new_code = mapping[0]
                
                try:
                    main_cursor.execute(
                        "INSERT OR IGNORE INTO ongoing_anime (anime_code) VALUES (?)",
                        (new_code,)
                    )
                    
                    if main_cursor.rowcount > 0:
                        transferred['ongoing'] += 1
                    
                except sqlite3.Error as e:
                    skipped['ongoing'] += 1
                    logging.error(f"Ongoing insert error: {e}")

            main_conn.commit()
            
            # 5. Prepare and send detailed report
            report = [
                "📊 Ko'chirish natijalari:",
                f"• Anime: {transferred['anime']} ta qo'shildi, {skipped['anime']} ta o'tkazib yuborildi",
                f"• Epizodlar: {transferred['episodes']} ta qo'shildi, {skipped['episodes']} ta o'tkazib yuborildi",
                f"• Ongoing: {transferred['ongoing']} ta qo'shildi, {skipped['ongoing']} ta o'tkazib yuborildi",
                f"• Kod konfliktlari: {conflicts_resolved} ta hal qilindi"
            ]

            if added_anime:
                report.append("\n➕ Yangi animelar:")
                report.extend(added_anime[:5])
                if len(added_anime) > 5:
                    report.append(f"... va yana {len(added_anime) - 5} ta")

            if conflict_anime:
                report.append("\n🛠 Kodlari o'zgartirilgan animelar:")
                report.extend(conflict_anime[:3])
                if len(conflict_anime) > 3:
                    report.append(f"... va yana {len(conflict_anime) - 3} ta")

            full_report = "\n".join(report)

            # Split long messages
            if len(full_report) > 4000:
                parts = [full_report[i:i + 4000] for i in range(0, len(full_report), 4000)]
                for part in parts:
                    await call.message.answer(part)
            else:
                await call.message.answer(full_report)

    except sqlite3.Error as e:
        logging.error(f"Database transfer failed: {e}", exc_info=True)
        await call.message.answer(f"❌ Ma'lumotlar bazasi xatosi: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error in database transfer: {e}", exc_info=True)
        await call.message.answer(f"❌ Kutilmagan xatolik yuz berdi: {str(e)}")
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
        await state.clear()
@dp.callback_query(F.data == "cancel_db_transfer", StateFilter(TransferDB.waiting_confirmation))
async def cancel_db_transfer(call: types.CallbackQuery, state: FSMContext):
    """Cancel database transfer process"""
    await call.answer()
    
    data = await state.get_data()
    temp_dir = data.get('temp_dir')
    
    if temp_dir and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    await call.message.answer("❌ Baza qabul qilinmadi")
    await state.clear()

class AddAdmin(StatesGroup):
    waiting_user_id = State()

@dp.callback_query(lambda call: call.data == "add_admin")
async def add_admin_start(call: types.CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, call=call, require_owner=True):
        return
    
    await state.set_state(AddAdmin.waiting_user_id)
    await call.message.answer(
        "➕ Yangi admin qo'shish uchun foydalanuvchi ID sini yuboring:\n\n"
        "Foydalanuvchi ID sini olish uchun @userinfobot dan foydalanishingiz mumkin.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]],
            resize_keyboard=True
        )
    )
    await call.answer()

@dp.message(AddAdmin.waiting_user_id)
async def add_admin_process(message: types.Message, state: FSMContext):
    if message.text == "🔙 Bekor qilish":
        await state.clear()
        await cancel_action(message)
        return
    
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri format! Faqat raqam kiriting:")
        return
    
    # Foydalanuvchi mavjudligini tekshirish
    try:
        user = await bot.get_chat(user_id)
    except exceptions.TelegramAPIError:
        await message.answer("❌ Bunday ID li foydalanuvchi topilmadi yoki bot bloklangan!")
        return
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        # Admin allaqachon mavjudligini tekshirish
        cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            await message.answer("ℹ️ Bu foydalanuvchi allaqachon admin!")
            return
        
        # Yangi adminni qo'shish
        cursor.execute(
            "INSERT INTO admins (user_id, username, added_by) VALUES (?, ?, ?)",
            (user_id, user.username or f"user_{user_id}", message.from_user.id)
        )
        conn.commit()
        
        await message.answer(
            f"✅ Yangi admin muvaffaqiyatli qo'shildi!\n\n"
            f"👤 Foydalanuvchi: {user.full_name}\n"
            f"🆔 ID: {user_id}\n"
            f"📌 Username: @{user.username or 'yoq'}"
        )
        
        try:
            # Yangi adminga xabar yuborish
            await bot.send_message(
                user_id,
                f"🎉 Tabriklaymiz! Siz {message.from_user.full_name} tomonidan "
                f"bot admini qilib tayinlandingiz!\n\n"
                f"Endi siz /admin buyrug'i orqali admin panelga kirishingiz mumkin."
            )
        except exceptions.TelegramAPIError as e:
            logging.error(f"Yangi adminga xabar yuborishda xatolik: {e}")
            
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        await state.clear()
        conn.close()

@dp.callback_query(lambda call: call.data == "list_admins")
async def list_admins(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT a.user_id, a.username, a.added_at, 
                   b.username as added_by_username
            FROM admins a
            LEFT JOIN admins b ON a.added_by = b.user_id
            ORDER BY a.added_at
        """)
        admins = cursor.fetchall()
        
        if not admins:
            await call.message.answer("ℹ️ Hozircha adminlar ro'yxati bo'sh")
            return
        
        text = "👨‍💻 Adminlar ro'yxati:\n\n"
        for idx, (user_id, username, added_at, added_by) in enumerate(admins, 1):
            text += (
                f"{idx}. ID: {user_id}\n"
                f"   👤 Username: @{username or 'yoq'}\n"
                f"   📅 Qo'shilgan: {added_at}\n"
                f"   🛠 Qo'shgan admin: @{added_by or 'yoq'}\n\n"
            )
        
        await call.message.answer(text)
        
    except Exception as e:
        await call.message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        conn.close()

@dp.callback_query(lambda call: call.data == "remove_admin")
async def remove_admin_start(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call, require_owner=True):
        return
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        # Asosiy adminni o'chirish mumkin emas
        cursor.execute("""
            SELECT user_id, username 
            FROM admins 
            WHERE user_id != ?
            ORDER BY username
        """, (ADMIN_ID,))
        admins = cursor.fetchall()
        
        if not admins:
            await call.answer("ℹ️ O'chirish uchun adminlar mavjud emas", show_alert=True)
            return
        
        buttons = []
        for user_id, username in admins:
            buttons.append([InlineKeyboardButton(
                text=f"❌ @{username or user_id}",
                callback_data=f"remove_admin_{user_id}"
            )])
        
        buttons.append([InlineKeyboardButton(
            text="🔙 Orqaga",
            callback_data="manage_admins"
        )])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await call.message.edit_text(
            "🗑 Admin o'chirish uchun tanlang:\n\n"
            "⚠️ Asosiy adminni o'chirib bo'lmaydi!",
            reply_markup=keyboard
        )
        
    except Exception as e:
        await call.answer(f"❌ Xatolik: {str(e)}", show_alert=True)
    finally:
        conn.close()

@dp.callback_query(lambda call: call.data.startswith("remove_admin_"))
async def remove_admin_confirm(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call, require_owner=True):
        return
    
    user_id = int(call.data.replace("remove_admin_", ""))
    
    if user_id == ADMIN_ID:
        await call.answer("❌ Asosiy adminni o'chirib bo'lmaydi!", show_alert=True)
        return
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT username FROM admins WHERE user_id = ?", (user_id,))
        admin = cursor.fetchone()
        
        if not admin:
            await call.answer("❌ Admin topilmadi!", show_alert=True)
            return
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"confirm_remove_admin_{user_id}"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="remove_admin")
            ]
        ])
        
        await call.message.edit_text(
            f"⚠️ Adminni o'chirishni tasdiqlaysizmi?\n\n"
            f"👤 Foydalanuvchi: @{admin[0] or user_id}\n"
            f"🆔 ID: {user_id}",
            reply_markup=keyboard
        )
        
    except Exception as e:
        await call.answer(f"❌ Xatolik: {str(e)}", show_alert=True)
    finally:
        conn.close()

@dp.callback_query(lambda call: call.data.startswith("confirm_remove_admin_"))
async def remove_admin_final(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call, require_owner=True):
        return
    
    user_id = int(call.data.replace("confirm_remove_admin_", ""))
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT username FROM admins WHERE user_id = ?", (user_id,))
        admin = cursor.fetchone()
        
        if not admin:
            await call.answer("❌ Admin topilmadi!", show_alert=True)
            return
        
        cursor.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        conn.commit()
        
        await call.answer(f"✅ Admin @{admin[0]} muvaffaqiyatli o'chirildi!", show_alert=True)
        
        try:
            # O'chirilgan adminga xabar yuborish
            await bot.send_message(
                user_id,
                f"⚠️ Siz {call.from_user.full_name} tomonidan "
                f"bot adminlaridan o'chirildingiz!\n\n"
                f"Endi siz /admin buyrug'i orqali admin panelga kira olmaysiz."
            )
        except exceptions.TelegramAPIError as e:
            logging.error(f"O'chirilgan adminga xabar yuborishda xatolik: {e}")
            
        await manage_admins(call)
        
    except Exception as e:
        await call.answer(f"❌ Xatolik: {str(e)}", show_alert=True)
    finally:
        conn.close()
# ==================== POST FUNCTIONS ====================

class CreatePost(StatesGroup):
    waiting_anime_code = State()

async def cancel_post_action(message: types.Message, state: FSMContext):
    # Clear state
    try:
        await state.clear()
    except Exception as e:
        logging.error(f"Error clearing state: {e}")
    
    # Create admin keyboard
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Post Tayyorlash")],
            [KeyboardButton(text="🔙 Admin Panel")]
        ],
        resize_keyboard=True
    )
    
    # Send cancellation message
    await message.answer(
        "❌ Post tayyorlash bekor qilindi.",
        reply_markup=keyboard
    )

@dp.message(lambda message: message.text == "📝 Post Tayyorlash")
async def create_post_start(message: types.Message, state: FSMContext):
    # Check admin status
    if not await check_admin(message.from_user.id, message=message):
        return
    
    # Set state
    await state.set_state(CreatePost.waiting_anime_code)
    
    # Create cancel keyboard
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]],
        resize_keyboard=True
    )

    # Ask for anime code
    await message.answer(
        "🔢 <b>Post uchun anime kodini kiriting:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.message(CreatePost.waiting_anime_code)
async def get_anime_for_post(message: types.Message, state: FSMContext):
    # Handle cancellation
    if message.text == "🔙 Bekor qilish":
        await cancel_post_action(message, state)
        return
    
    # Validate anime code
    anime_code = message.text.strip()
    if not anime_code.isalnum():
        await message.answer(
            "❌ Noto'g'ri anime kodi! Faqat harflar va raqamlardan foydalaning.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]],
                resize_keyboard=True
            )
        )
        return

    try:
        # Get anime data from database
        with sqlite3.connect('anime_bot.db') as conn:
            cursor = conn.cursor()
            
            # Get anime info
            cursor.execute("""
                SELECT title, country, language, year, genre, image, video 
                FROM anime WHERE code = ?
            """, (anime_code,))
            anime = cursor.fetchone()
            
            if not anime:
                await message.answer(
                    "❌ Bunday kodli anime topilmadi. Qayta urinib ko'ring:",
                    reply_markup=ReplyKeyboardMarkup(
                        keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]],
                        resize_keyboard=True
                    )
                )
                return
                
            title, country, language, year, genre, image, video = anime
            
            # Get episodes count
            cursor.execute("SELECT COUNT(*) FROM episodes WHERE anime_code = ?", (anime_code,))
            episodes_count = cursor.fetchone()[0]
            
            # Get post channel info
            cursor.execute("SELECT channel_name FROM channels WHERE channel_type = 'post' LIMIT 1")
            channel = cursor.fetchone()
            channel_name = channel[0] if channel else (await bot.get_me()).username
            
            # Prepare post caption
            post_caption = f"""
‣  Anime: {html.escape(title)}
╭━━━━━━━━━━━━━━━━━━━━━━━━━
• Janr: {html.escape(genre)}
• Qismi: {episodes_count} ta
• Davlat: {html.escape(country)}
• Til: {html.escape(language)}
• Kanal: {html.escape(channel_name)}
╰━━━━━━━━━━━━━━━━━━━━━━━━━
            """
            
            # Create inline keyboard
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="▶️ Tomosha Qilish", 
                    callback_data=f"watch_{anime_code}"
                )],
                [InlineKeyboardButton(
                    text="📢 Kanalga Yuborish", 
                    callback_data=f"confirm_post_{anime_code}"
                )],
                [InlineKeyboardButton(
                    text="🔙 Admin Panel", 
                    callback_data="back_to_admin"
                )]
            ])
            
            # Send post preview
            try:
                if video:
                    await message.answer_video(
                        video=video,
                        caption=post_caption,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                elif image:
                    await message.answer_photo(
                        photo=image,
                        caption=post_caption,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                else:
                    await message.answer(
                        text=post_caption,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                
                # Clear state after successful preview
                await state.clear()
                    
            except exceptions.TelegramAPIError as e:
                await message.answer(f"❌ Telegram xatosi: {str(e)}")
                logging.error(f"Telegram API error: {str(e)}")
                
    except sqlite3.Error as e:
        await message.answer("❌ Ma'lumotlar bazasi xatosi! Iltimos, keyinroq urinib ko'ring.")
        logging.error(f"Database error: {str(e)}")
    except Exception as e:
        await message.answer("❌ Kutilmagan xatolik yuz berdi! Iltimos, keyinroq urinib ko'ring.")
        logging.error(f"Unexpected error: {str(e)}")

@dp.callback_query(lambda call: call.data.startswith("confirm_post_"))
async def confirm_post(call: types.CallbackQuery):
    anime_code = call.data.replace("confirm_post_", "")
    
    # Create confirmation keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Ha, Kanalga Yuborish", 
            callback_data=f"send_post_{anime_code}"
        )],
        [InlineKeyboardButton(
            text="❌ Bekor qilish", 
            callback_data="cancel_post"
        )]
    ])
    
    # Edit message with confirmation buttons
    await call.message.edit_reply_markup(reply_markup=keyboard)
    await call.answer()

@dp.callback_query(lambda call: call.data.startswith("send_post_"))
async def send_post_to_channel(call: types.CallbackQuery):
    try:
        anime_code = call.data.replace("send_post_", "").strip()
        
        # Validate anime code
        if not anime_code.isalnum():
            await call.answer("❌ Noto'g'ri anime kodi!", show_alert=True)
            return

        # Connect to database
        with sqlite3.connect('anime_bot.db') as conn:
            cursor = conn.cursor()
            
            # Get anime info
            cursor.execute("""
                SELECT title, country, language, year, genre, image, video 
                FROM anime WHERE code = ?
            """, (anime_code,))
            anime = cursor.fetchone()
            
            if not anime:
                await call.answer("❌ Anime topilmadi!", show_alert=True)
                return
                
            title, country, language, year, genre, image, video = anime
            
            # Get episodes count
            cursor.execute("SELECT COUNT(*) FROM episodes WHERE anime_code = ?", (anime_code,))
            episodes_count = cursor.fetchone()[0]
            
            # Get channel info (both ID and name)
            cursor.execute("SELECT channel_id, channel_name FROM channels WHERE channel_type = 'post' LIMIT 1")
            channel = cursor.fetchone()
            
            if not channel:
                await call.answer("❌ Post kanali o'rnatilmagan!", show_alert=True)
                return
                
            channel_id, channel_name = channel
            
            try:
                # Convert channel_id to integer if it's numeric
                if str(channel_id).startswith('-100') and str(channel_id)[4:].isdigit():
                    channel_id = int(channel_id)
                elif str(channel_id).isdigit():
                    channel_id = int(f"-100{channel_id}")
            except:
                pass
                
            bot_username = (await bot.get_me()).username
            
            # Use channel name if available, otherwise use bot username
            channel_display = f"{channel_name}" if channel_name else f"{bot_username}"
            
            # Prepare final post caption
            post_caption = f"""
‣  Anime: {title} 
╭━━━━━━━━━━━━━━━━━━━━━━━━━
• Janr: {genre}
• Qismi: {episodes_count} ta
• Davlat: {country}
• Til: {language}
• Kanal: {channel_display}
╰━━━━━━━━━━━━━━━━━━━━━━━━━
            """
            
            # Create watch button with direct link
            watch_url = f"https://t.me/{bot_username}?start=watch_{anime_code}"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="▶️ Tomosha Qilish", 
                    url=watch_url
                )]
            ])

            # Send to channel
            try:
                if video:
                    msg = await bot.send_video(
                        chat_id=channel_id,
                        video=video,
                        caption=post_caption,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                elif image:
                    msg = await bot.send_photo(
                        chat_id=channel_id,
                        photo=image,
                        caption=post_caption,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                else:
                    msg = await bot.send_message(
                        chat_id=channel_id,
                        text=post_caption,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                    
                await call.answer("✅ Post kanalga muvaffaqiyatli yuborildi!", show_alert=True)
                
            except exceptions.ChatNotFound:
                await call.answer("❌ Kanal topilmadi yoki bot admin emas!", show_alert=True)
            except exceptions.BotBlocked:
                await call.answer("❌ Bot kanalda bloklangan!", show_alert=True)
            except exceptions.ChatWriteForbidden:
                await call.answer("❌ Botda kanalga yozish huquqi yo'q!", show_alert=True)
            except exceptions.RetryAfter as e:
                await call.answer(f"❌ Telegram limiti: {e.timeout} soniyadan keyin urinib ko'ring", show_alert=True)
            except Exception as e:
                error_msg = f"❌ Yuborishda xatolik: {str(e)}"
                logging.error(f"Post yuborishda xatolik: {str(e)}")
                await call.answer(error_msg[:200], show_alert=True)
                
    except sqlite3.Error as e:
        await call.answer("❌ Ma'lumotlar bazasi xatosi!", show_alert=True)
        logging.error(f"Database error: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error in send_post: {str(e)}")
        await call.answer("❌ Kutilmagan xatolik yuz berdi!", show_alert=True)

@dp.callback_query(lambda call: call.data == "cancel_post")
async def cancel_post_callback(call: types.CallbackQuery, state: FSMContext):
    # Clear any existing state
    try:
        await state.clear()
    except:
        pass
    
    # Edit message to remove buttons
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except:
        pass
    
    # Send cancellation message
    await cancel_post_action(call.message, state)
    await call.answer("❌ Post yuborish bekor qilindi", show_alert=True)

async def cancel_post_action(message: types.Message):
    if message.from_user.id in user_state:
        del user_state[message.from_user.id]
    
    await message.answer("❌ Post tayyorlash bekor qilindi.",
                        reply_markup=ReplyKeyboardMarkup(
                            keyboard=[
                                [KeyboardButton(text="📝 Post Tayyorlash")],
                                [KeyboardButton(text="🔙 Admin Panel")]
                            ],
                            resize_keyboard=True
                        ))
class SerialPost(StatesGroup):
    waiting_anime_code = State()
    waiting_episode_number = State()
    waiting_description = State()
    waiting_media = State()
    waiting_channel = State()

@dp.message(lambda message: message.text == "🎞 Serial Post Qilish")
async def serial_post_start(message: types.Message, state: FSMContext):
    if not await check_admin(message.from_user.id, message=message):
        return
    
    await state.set_state(SerialPost.waiting_anime_code)
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]],
        resize_keyboard=True
    )

    await message.answer(
        "🔢 <b>Serial post qilish uchun anime kodini kiriting:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.message(SerialPost.waiting_anime_code)
async def get_serial_anime_code(message: types.Message, state: FSMContext):
    if message.text == "🔙 Bekor qilish":
        await state.clear()
        await cancel_post_action(message)
        return
    
    anime_code = message.text.strip()
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT title FROM anime WHERE code = ?", (anime_code,))
        anime = cursor.fetchone()
        
        if not anime:
            await message.answer("❌ Bunday kodli anime topilmadi. Qayta urinib ko'ring:")
            return
            
        await state.update_data(anime_code=anime_code, anime_title=anime[0])
        await state.set_state(SerialPost.waiting_episode_number)
        
        cursor.execute("SELECT episode_number FROM episodes WHERE anime_code = ? ORDER BY episode_number", (anime_code,))
        episodes = cursor.fetchall()
        
        if not episodes:
            await message.answer("❌ Bu anime uchun hech qanday qism topilmadi.")
            return
            
        # Qismlarni inline keyboardda ko'rsatamiz
        buttons = []
        row = []
        for ep in episodes:
            row.append(InlineKeyboardButton(
                text=f"{ep[0]}-qism",
                callback_data=f"select_ep_{ep[0]}"
            ))
            if len(row) >= 3:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        
        buttons.append([InlineKeyboardButton(
            text="🔙 Bekor qilish",
            callback_data="cancel_serial_post"
        )])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await message.answer(
            f"🎬 {anime[0]}\n\n"
            f"📺 Post qilish uchun qismni tanlang:",
            reply_markup=keyboard
        )
        
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        conn.close()

@dp.callback_query(SerialPost.waiting_episode_number, lambda c: c.data.startswith("select_ep_"))
async def select_episode_for_post(call: types.CallbackQuery, state: FSMContext):
    episode_number = int(call.data.replace("select_ep_", ""))
    await state.update_data(episode_number=episode_number)
    await state.set_state(SerialPost.waiting_description)
    
    await call.message.edit_text(
        f"📝 {episode_number}-qism uchun post tavsifini kiriting:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="cancel_serial_post")]
        ])
    )
    await call.answer()

@dp.message(SerialPost.waiting_description)
async def get_serial_description(message: types.Message, state: FSMContext):
    if message.text == "🔙 Bekor qilish":
        await state.clear()
        await cancel_post_action(message)
        return
    
    await state.update_data(description=message.text)
    await state.set_state(SerialPost.waiting_media)
    
    await message.answer(
        "🖼 Post uchun rasm yoki video yuboring (agar kerak bo'lsa):\n\n"
        "Agar media yubormasangiz, anime standart rasmi/videosi ishlatiladi",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="⏭️ Media yubormaslik")],
                [KeyboardButton(text="🔙 Bekor qilish")]
            ],
            resize_keyboard=True
        )
    )

@dp.message(SerialPost.waiting_media, lambda m: m.text == "⏭️ Media yubormaslik")
@dp.message(SerialPost.waiting_media, lambda m: m.photo or m.video)
async def get_serial_media(message: types.Message, state: FSMContext):
    if message.text == "🔙 Bekor qilish":
        await state.clear()
        await cancel_post_action(message)
        return
    
    media_file_id = None
    media_type = None
    
    if message.photo:
        media_file_id = message.photo[-1].file_id
        media_type = 'photo'
    elif message.video:
        media_file_id = message.video.file_id
        media_type = 'video'
    
    await state.update_data(media_file_id=media_file_id, media_type=media_type)
    
    # Kanal tanlash uchun menyu
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id, channel_name FROM channels WHERE channel_type = 'post'")
    channels = cursor.fetchall()
    conn.close()
    
    if not channels:
        await message.answer("❌ Post kanali topilmadi! Iltimos, avval kanal qo'shing.")
        await state.clear()
        return
    
    buttons = []
    for channel_id, channel_name in channels:
        buttons.append([InlineKeyboardButton(
            text=f"📢 {channel_name}",
            callback_data=f"select_channel_{channel_id}"
        )])
    
    buttons.append([InlineKeyboardButton(
        text="🔙 Bekor qilish",
        callback_data="cancel_serial_post"
    )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await state.set_state(SerialPost.waiting_channel)
    await message.answer(
        "📢 Post qilish uchun kanalni tanlang:",
        reply_markup=keyboard
    )

@dp.callback_query(SerialPost.waiting_channel, lambda c: c.data.startswith("select_channel_"))
async def select_serial_channel(call: types.CallbackQuery, state: FSMContext):
    channel_id = call.data.replace("select_channel_", "")
    data = await state.get_data()
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        # Anime ma'lumotlarini olish
        cursor.execute("""
            SELECT title, image, video 
            FROM anime 
            WHERE code = ?
        """, (data['anime_code'],))
        anime = cursor.fetchone()
        
        if not anime:
            await call.answer("❌ Anime topilmadi!", show_alert=True)
            return
            
        title, default_image, default_video = anime
        
        # Tanlangan qism videosini olish
        cursor.execute("""
            SELECT video_file_id 
            FROM episodes 
            WHERE anime_code = ? AND episode_number = ?
        """, (data['anime_code'], data['episode_number']))
        episode = cursor.fetchone()
        
        if not episode:
            await call.answer("❌ Qism topilmadi!", show_alert=True)
            return
            
        video_file_id = episode[0]
        
        # Post uchun media tanlash
        media_file_id = data.get('media_file_id')
        media_type = data.get('media_type')
        
        if not media_file_id:
            if default_video:
                media_file_id = default_video
                media_type = 'video'
            elif default_image:
                media_file_id = default_image
                media_type = 'photo'
        
        # Post tayyorlash
        bot_username = (await bot.get_me()).username
        description = data.get('description', '')
        
        post_caption = f"""
<blockquote>
<b>- {title}</b>  
<b>- QISM - {data['episode_number']}</b>
</blockquote>

"""
        
        # Tomosha qilish uchun link
        watch_url = f"https://t.me/{bot_username}?start=watch_{data['anime_code']}_{data['episode_number']}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="▶️ Tomosha Qilish",
                url=watch_url
            )]
        ])
        
        # Postni yuborish
        try:
            if media_type == 'photo':
                await bot.send_photo(
                    chat_id=channel_id,
                    photo=media_file_id,
                    caption=post_caption,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            elif media_type == 'video':
                await bot.send_video(
                    chat_id=channel_id,
                    video=media_file_id,
                    caption=post_caption,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    chat_id=channel_id,
                    text=post_caption,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            
            await call.answer("✅ Post muvaffaqiyatli yuborildi!", show_alert=True)
            
        except exceptions.TelegramAPIError as e:
            await call.answer(f"❌ Xatolik: {str(e)}", show_alert=True)
        
    except Exception as e:
        await call.answer(f"❌ Xatolik: {str(e)}", show_alert=True)
    finally:
        await state.clear()
        conn.close()

@dp.callback_query(SerialPost.waiting_channel, lambda c: c.data == "cancel_serial_post")
async def cancel_serial_post(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer("❌ Post qilish bekor qilindi", show_alert=True)
    await call.message.delete()
# ==================== STATISTICS ====================

@dp.message(lambda message: message.text == "📊 Statistika")
async def show_stats(message: types.Message):
    if not await check_admin(message.from_user.id, message=message):
        return
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        # Asosiy statistikalar
        cursor.execute("SELECT COUNT(*) FROM anime")
        anime_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM episodes")
        episodes_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM subscribers WHERE notifications = TRUE")
        active_subs = cursor.fetchone()[0]
        
        # Bloklangan foydalanuvchilar soni (bot bloklaganlar)
        try:
            blocked_count = 0
            cursor.execute("SELECT user_id FROM subscribers")
            for (user_id,) in cursor.fetchall():
                try:
                    member = await bot.get_chat_member(user_id, user_id)
                    if member.status == ChatMemberStatus.BANNED:
                        blocked_count += 1
                except exceptions.TelegramAPIError as e:
                    if "user not found" in str(e).lower() or "bot was blocked" in str(e).lower():
                        blocked_count += 1
        except Exception as e:
            blocked_count = "Noma'lum"
        
        # Bugungi yangi obunachilar
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) FROM subscribers WHERE DATE(created_at) = ?", (today,))
        today_subs = cursor.fetchone()[0]
        
        # Oylik statistikalar
        current_month = datetime.now().strftime("%Y-%m")
        cursor.execute("""
            SELECT strftime('%Y-%m', created_at) as month, 
                   COUNT(*) as count
            FROM subscribers
            WHERE strftime('%Y-%m', created_at) = ?
            GROUP BY month
        """, (current_month,))
        monthly_stats = cursor.fetchone()
        monthly_subs = monthly_stats[1] if monthly_stats else 0
        
        # Kanal statistikasi
        cursor.execute("SELECT COUNT(*) FROM channels WHERE channel_type = 'mandatory'")
        mandatory_channels = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM channels WHERE channel_type = 'post'")
        post_channels = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM questions")
        questions_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM quiz_participants")
        quiz_participants = cursor.fetchone()[0]
        
        # Statistikani yuborish
        stats_text = f"""
📊 <b>Bot statistikasi:</b>

🎬 <b>Anime lar soni:</b> {anime_count}
📺 <b>Qismlar soni:</b> {episodes_count}

👥 <b>Obunachilar:</b>
├─ Faol obunachilar: {active_subs}
├─ Bugun qo'shilganlar: {today_subs}
├─ Bu oy qo'shilganlar: {monthly_subs}
└─ Bloklanganlar: {blocked_count}

📢 <b>Kanallar:</b>
├─ Majburiy kanallar: {mandatory_channels}
└─ Post kanallari: {post_channels}

❓ <b>Savol-javob:</b>
├─ Savollar soni: {questions_count}
└─ Qatnashchilar soni: {quiz_participants}
"""
        
        # Oylik statistikani grafik shaklda ko'rsatish
        cursor.execute("""
            SELECT strftime('%Y-%m', created_at) as month, 
                   COUNT(*) as count
            FROM subscribers
            GROUP BY month
            ORDER BY month DESC
            LIMIT 6
        """)
        monthly_data = cursor.fetchall()
        
        if monthly_data:
            stats_text += "\n📈 <b>Oxirgi 6 oylik obunachilar statistikasi:</b>\n"
            for month, count in monthly_data:
                stats_text += f"├─ {month}: {count} ta\n"
            stats_text += "└─ ..."
        
        await message.answer(stats_text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        conn.close()

# ==================== SUBSCRIBERS MANAGEMENT ====================

@dp.message(lambda message: message.text == "👥 Obunachilar")
async def manage_subscribers(message: types.Message):
    if not await check_admin(message.from_user.id, message=message):
        return
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM subscribers WHERE notifications = TRUE")
    active_count = cursor.fetchone()[0]
    conn.close()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Xabar Yuborish", callback_data="send_to_subs")],
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="back_to_admin")]
    ])
    
    await message.answer(
        f"👥 Obunachilar boshqaruvi\n\n"
        f"🔔 Faol obunachilar soni: {active_count}",
        reply_markup=keyboard
    )

@dp.callback_query(lambda call: call.data == "send_to_subs")
async def send_to_subs_start(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    user_state[call.from_user.id] = {"state": "waiting_subs_message"}
    await call.message.edit_text("📢 Obunachilarga yubormoqchi bo'lgan xabaringizni yuboring:")

@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_subs_message")
async def send_to_subs_process(message: types.Message):
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT user_id FROM subscribers WHERE notifications = TRUE")
        subscribers = cursor.fetchall()
        
        success = 0
        failed = 0
        
        for (user_id,) in subscribers:
            try:
                await bot.send_message(user_id, message.text)
                success += 1
            except Exception as e:
                failed += 1
                logging.error(f"Xabar yuborishda xatolik (user_id={user_id}): {e}")
        
        await message.answer(
            f"📢 Xabar yuborish natijasi:\n\n"
            f"✅ Muvaffaqiyatli: {success}\n"
            f"❌ Xatoliklar: {failed}"
        )
        
        del user_state[message.from_user.id]
        
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        conn.close()

# ==================== Q&A MANAGEMENT ====================

@dp.message(lambda message: message.text == "❓ Savollar")
async def manage_questions(message: types.Message):
    if not await check_admin(message.from_user.id, message=message):
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Savol Qo'shish", callback_data="add_question")],
        [InlineKeyboardButton(text="🗑 Savol O'chirish", callback_data="delete_question")],
        [InlineKeyboardButton(text="📋 Savollar Ro'yxati", callback_data="list_questions")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_admin")]
    ])
    
    await message.answer("❓ Savollar boshqaruvi", reply_markup=keyboard)

@dp.callback_query(lambda call: call.data == "add_question")
async def add_question_start(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    user_state[call.from_user.id] = {"state": "waiting_question"}
    await call.message.answer("❓ Yangi savol matnini yuboring:")

@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_question")
async def get_question_text(message: types.Message):
    user_state[message.from_user.id] = {
        "state": "waiting_answer_for_question",
        "question": message.text
    }
    await message.answer("💡 Endi bu savolga javobni yuboring:")

@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_answer_for_question")
async def get_answer_for_question(message: types.Message):
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("INSERT INTO questions (question, answer) VALUES (?, ?)",
                     (user_state[message.from_user.id]["question"], message.text))
        conn.commit()
        await message.answer("✅ Savol muvaffaqiyatli qo'shildi!")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        del user_state[message.from_user.id]
        conn.close()

@dp.callback_query(lambda call: call.data == "list_questions")
async def list_questions(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, question, answer FROM questions")
        questions = cursor.fetchall()
        
        if questions:
            text = "📋 Savollar ro'yxati:\n\n"
            for idx, (q_id, question, answer) in enumerate(questions, 1):
                text += f"{idx}. {question}\n💡 Javob: {answer}\n\n"
            
            await call.message.answer(text)
        else:
            await call.message.answer("ℹ️ Hozircha savollar mavjud emas.")
    except Exception as e:
        await call.message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        conn.close()

@dp.callback_query(lambda call: call.data == "delete_question")
async def delete_question_start(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, question FROM questions")
    questions = cursor.fetchall()
    conn.close()
    
    if questions:
        questions_text = "\n\n".join([f"🆔 {q[0]}: {q[1]}" for q in questions])
        await call.message.answer(
            f"❌ O'chirish uchun savol ID sini yuboring:\n\n{questions_text}",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]],
                resize_keyboard=True
            )
        )
        user_state[call.from_user.id] = {"state": "waiting_question_id"}
    else:
        await call.message.answer("ℹ️ Hozircha savollar mavjud emas.")

@dp.message(lambda message: user_state.get(message.from_user.id, {}).get("state") == "waiting_question_id")
async def delete_question_by_id(message: types.Message):
    if message.text == "🔙 Bekor qilish":
        await cancel_action(message)
        return
    
    if not message.text.isdigit():
        await message.answer("❌ Noto'g'ri format. Faqat raqam kiriting:")
        return
    
    question_id = int(message.text)
    conn = sqlite3.connect('anime_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT question FROM questions WHERE id = ?", (question_id,))
        question = cursor.fetchone()
        
        if question:
            cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
            conn.commit()
            
            await message.answer(
                f"✅ Savol muvaffaqiyatli o'chirildi:\n\n{question[0]}",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text="❓ Savollar")],
                        [KeyboardButton(text="🔙 Admin Panel")]
                    ],
                    resize_keyboard=True
                )
            )
        else:
            await message.answer("❌ Bunday ID li savol topilmadi. Qayta urinib ko'ring:")
            return
        
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        conn.close()
        if message.from_user.id in user_state:
            del user_state[message.from_user.id]

async def cancel_action(message: types.Message):
    if message.from_user.id in user_state:
        del user_state[message.from_user.id]
    
    await message.answer(
        "❌ Amal bekor qilindi.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="❓ Savollar")],
                [KeyboardButton(text="🔙 Admin Panel")]
            ],
            resize_keyboard=True
        )
    )

# ==================== BACK BUTTONS ====================

@dp.message(lambda message: message.text == "🔙 Orqaga")
async def back_from_anime_settings(message: types.Message):
    if not await check_admin(message.from_user.id, message=message):
        return
    
    await admin_login(message)

@dp.callback_query(lambda call: call.data == "back_to_admin")
async def back_to_admin(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id, call=call):
        return
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
          [KeyboardButton(text="🎥 Anime Sozlash"), KeyboardButton(text="📢 Kanal Sozlash")],
            [KeyboardButton(text="📝 Post Tayyorlash"), KeyboardButton(text="🎞 Serial Post Qilish")],
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="👥 Obunachilar")],
            [KeyboardButton(text="👨‍💻 Adminlar"), KeyboardButton(text="❓ Savollar")],
            [KeyboardButton(text="🔙 Bosh Menyu")]
        ],
        resize_keyboard=True
    )
    
    await call.message.edit_text("👨‍💻 Admin Panel")
    await call.message.answer("Tanlang:", reply_markup=keyboard)

@dp.message(lambda message: message.text == "🔙 Bosh Menyu")
async def back_to_main(message: types.Message):
    if message.from_user.id in user_state:
        del user_state[message.from_user.id]
    
    await show_main_menu(message)

# ==================== MAIN FUNCTION ====================

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    try:
        session = AiohttpSession()
        bot = Bot(token=TOKEN, session=session)
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Bot ishga tushirishda xatolik: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())    