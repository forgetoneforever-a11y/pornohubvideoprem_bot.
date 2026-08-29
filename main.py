import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from database import init_db, add_video, get_random_video

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
SECRET_PASSWORD = "webhook1100"

router = Router()

# Состояния FSM для проверки пароля и загрузки контента
class AdminUploadState(StatesGroup):
    waiting_for_password = State()
    waiting_for_content = State()

# Клавиатура категорий (с кнопкой добавления для админа)
def get_categories_keyboard(is_admin: bool = False):
    keyboard = [
        [
            InlineKeyboardButton(text="🎬 Pornohub", callback_data="category_pornohub"),
            InlineKeyboardButton(text="🔥 Hentai", callback_data="category_hentai")
        ],
        [
            InlineKeyboardButton(text="📺 YouTube", callback_data="category_youtube"),
            InlineKeyboardButton(text="🎲 Случайное", callback_data="category_random")
        ]
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton(text="➕ Добавить видео", callback_data="admin_add_video")])
        
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    is_admin = (message.from_user.id == ADMIN_ID)
    await message.answer(
        "Привет! Выбери категорию контента с помощью кнопок ниже:",
        reply_markup=get_categories_keyboard(is_admin)
    )

@router.message(Command("get"))
async def cmd_get_video(message: Message, state: FSMContext):
    await state.clear()
    is_admin = (message.from_user.id == ADMIN_ID)
    await message.answer(
        "Выбери категорию видео:",
        reply_markup=get_categories_keyboard(is_admin)
    )

# Нажатие на кнопку «Добавить видео»
@router.callback_query(F.data == "admin_add_video")
async def start_add_video(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет прав!", show_alert=True)
        return
    
    await state.set_state(AdminUploadState.waiting_for_password)
    await callback.message.answer("🔒 Введите пароль для доступа к загрузке:")
    await callback.answer()

# Проверка введенного пароля
@router.message(AdminUploadState.waiting_for_password)
async def process_password(message: Message, state: FSMContext):
    if message.text.strip() == SECRET_PASSWORD:
        await state.set_state(AdminUploadState.waiting_for_content)
        await message.answer("✅ Пароль верный!\nТеперь отправь мне **MP4-файл** или **ссылку** на видео.")
    else:
        await message.answer("❌ Неверный пароль. Попробуй еще раз или напиши /start для отмены.")

# Загрузка видео-файла после авторизации
@router.message(AdminUploadState.waiting_for_content, F.video)
async def save_video_file(message: Message, state: FSMContext):
    file_id = message.video.file_id
    title = message.caption or "Без названия"
    await add_video(file_id=file_id, title=title)
    await state.clear()
    is_admin = (message.from_user.id == ADMIN_ID)
    await message.reply("🎉 Видео успешно сохранено в базу!", reply_markup=get_categories_keyboard(is_admin))

# Загрузка ссылки после авторизации
@router.message(AdminUploadState.waiting_for_content, F.text.startswith("http"))
async def save_video_link(message: Message, state: FSMContext):
    url = message.text.strip()
    await add_video(youtube_url=url, title="YouTube ролик")
    await state.clear()
    is_admin = (message.from_user.id == ADMIN_ID)
    await message.reply("🎉 Ссылка успешно сохранена в базу!", reply_markup=get_categories_keyboard(is_admin))

# Обработка выбора категорий контента
@router.callback_query(F.data.startswith("category_"))
async def process_category_callback(callback: CallbackQuery):
    category = callback.data.split("_")[1]
    video = await get_random_video()
    
    if not video:
        await callback.message.answer("В базе данных пока нет видео!")
        await callback.answer()
        return
    
    file_id, youtube_url, title = video
    caption = f"Категория: {category.upper()}\n{title}"
    
    if file_id:
        await callback.message.answer_video(file_id, caption=caption)
    elif youtube_url:
        await callback.message.answer(f"Категория: {category.upper()}\n{youtube_url}")
        
    await callback.answer()

async def main():
    logging.basicConfig(level=logging.INFO)
    if not TOKEN:
        logging.error("Не задан BOT_TOKEN в переменных окружения!")
        return
        
    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    
    await init_db()
    logging.info("Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
