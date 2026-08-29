import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import init_db, add_video, get_random_video

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

router = Router()

# Клавиатура с выбором категорий
def get_categories_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎬 Pornohub", callback_data="category_pornohub"),
                InlineKeyboardButton(text="🔥 Hentai", callback_data="category_hentai")
            ],
            [
                InlineKeyboardButton(text="📺 YouTube", callback_data="category_youtube")
            ],
            [
                InlineKeyboardButton(text="🎲 Случайное", callback_data="category_random")
            ]
        ]
    )
    return keyboard

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Выбери категорию контента с помощью кнопок ниже:",
        reply_markup=get_categories_keyboard()
    )

@router.message(Command("get"))
async def cmd_get_video(message: Message):
    await message.answer(
        "Выбери категорию видео:",
        reply_markup=get_categories_keyboard()
    )

# Обработка нажатий на инлайн-кнопки
@router.callback_query(F.data.startswith("category_"))
async def process_category_callback(callback: CallbackQuery):
    category = callback.data.split("_")[1]
    
    # Пока что выдаем случайное видео из базы (в будущем можно добавить колонку category в БД для фильтрации)
    video = await get_random_video()
    
    if not video:
        await callback.message.answer("В этой категории пока нет видео!")
        await callback.answer()
        return
    
    file_id, youtube_url, title = video
    caption = f"Категория: {category.upper()}\n{title}"
    
    if file_id:
        await callback.message.answer_video(file_id, caption=caption)
    elif youtube_url:
        await callback.message.answer(f"Категория: {category.upper()}\n{youtube_url}")
        
    await callback.answer() # Убираем «часики» загрузки на кнопке

# Добавление видео администратором с выбором категории через подпись (например: #hentai Название)
@router.message(F.from_user.id == ADMIN_ID, F.video)
async def save_video_file(message: Message):
    file_id = message.video.file_id
    title = message.caption or "Без названия"
    await add_video(file_id=file_id, title=title)
    await message.reply("Видео успешно сохранено в базу!")

@router.message(F.from_user.id == ADMIN_ID, F.text.startswith("http"))
async def save_video_link(message: Message):
    url = message.text.strip()
    await add_video(youtube_url=url, title="YouTube ролик")
    await message.reply("Ссылка на YouTube успешно сохранена!")

async def main():
    logging.basicConfig(level=logging.INFO)
    if not TOKEN:
        logging.error("Не задан BOT_TOKEN в переменных окружения!")
        return
        
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    await init_db()
    logging.info("Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
