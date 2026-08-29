import asyncio
import logging
import os
import yt_dlp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from database import init_db, add_video, get_random_video

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
SECRET_PASSWORD = "webhook1100"

router = Router()

class AdminUploadState(StatesGroup):
    waiting_for_password = State()
    waiting_for_content = State()

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
    is_admin = (int(message.from_user.id) == int(ADMIN_ID))
    await message.answer(
        "Привет! Выбери категорию контента с помощью кнопок ниже:",
        reply_markup=get_categories_keyboard(is_admin)
    )

@router.message(Command("get"))
async def cmd_get_video(message: Message, state: FSMContext):
    await state.clear()
    is_admin = (int(message.from_user.id) == int(ADMIN_ID))
    await message.answer(
        "Выбери категорию видео:",
        reply_markup=get_categories_keyboard(is_admin)
    )

@router.callback_query(F.data == "admin_add_video")
async def start_add_video(callback: CallbackQuery, state: FSMContext):
    if int(callback.from_user.id) != int(ADMIN_ID):
        await callback.answer("У вас нет прав!", show_alert=True)
        return
    
    await state.set_state(AdminUploadState.waiting_for_password)
    await callback.message.answer("🔒 Введите пароль для доступа к загрузке:")
    await callback.answer()

@router.message(AdminUploadState.waiting_for_password)
async def process_password(message: Message, state: FSMContext):
    if message.text.strip() == SECRET_PASSWORD:
        await state.set_state(AdminUploadState.waiting_for_content)
        await message.answer("✅ Пароль верный!\nТеперь отправь мне **MP4-файл** или **ссылку** на видео.")
    else:
        await message.answer("❌ Неверный пароль. Попробуй еще раз или напиши /start для отмены.")

@router.message(AdminUploadState.waiting_for_content, F.video)
async def save_video_file(message: Message, state: FSMContext):
    file_id = message.video.file_id
    title = message.caption or "Без названия"
    await add_video(file_id=file_id, title=title)
    await state.clear()
    is_admin = (int(message.from_user.id) == int(ADMIN_ID))
    await message.reply("🎉 Видео успешно сохранено в базу!", reply_markup=get_categories_keyboard(is_admin))

@router.message(AdminUploadState.waiting_for_content, F.text.startswith("http"))
async def save_video_link(message: Message, state: FSMContext):
    url = message.text.strip()
    await add_video(youtube_url=url, title="YouTube ролик")
    await state.clear()
    is_admin = (int(message.from_user.id) == int(ADMIN_ID))
    await message.reply("🎉 Ссылка успешно сохранена в базу!", reply_markup=get_categories_keyboard(is_admin))

# Функция скачивания видео с помощью yt-dlp
async def download_youtube_video(url: str) -> str:
    output_template = "temp_video.mp4"
    if os.path.exists(output_template):
        os.remove(output_template)
        
    ydl_opts = {
        'format': 'mp4/best',
        'outtmpl': output_template,
        'quiet': True,
        'max_filesize': 50 * 1024 * 1024, # Ограничение до 50 МБ для Telegram
    }
    
    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    await asyncio.to_thread(_download)
    return output_template if os.path.exists(output_template) else None

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
        await callback.message.answer("⏳ Скачиваю видео с ссылки, подождите...")
        try:
            file_path = await download_youtube_video(youtube_url)
            if file_path:
                video_file = FSInputFile(file_path)
                await callback.message.answer_video(video_file, caption=caption)
                os.remove(file_path) # Удаляем файл после отправки
            else:
                await callback.message.answer(f"Не удалось скачать видео по ссылке: {youtube_url}")
        except Exception as e:
            await callback.message.answer(f"Ошибка при скачивании: {str(e)}")
            
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
