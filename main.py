import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import Message
from database import init_db, add_video, get_random_video

TOKEN = "ТВОЙ_ТОКЕН_БОТА"
ADMIN_ID = 123456789  # Твой Telegram ID для доступа к добавлению контента

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Нажми /get, чтобы получить случайное видео из базы."
    )

@router.message(Command("get"))
async def cmd_get_video(message: Message):
    video = await get_random_video()
    if not video:
        await message.answer("База данных пока пуста!")
        return
    
    file_id, youtube_url, title = video
    if file_id:
        # Отправляем видео напрямую из Telegram по file_id (быстро и без скачивания)
        await message.answer_video(file_id, caption=title)
    elif youtube_url:
        await message.answer(f"Вот видео по ссылке: {youtube_url}")

# Добавление видео администратором
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
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())