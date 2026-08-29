import aiosqlite

DB_NAME = "videos.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT,
                youtube_url TEXT,
                title TEXT
            )
        """)
        await db.commit()

async def add_video(file_id: str = None, youtube_url: str = None, title: str = "Видео"):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO videos (file_id, youtube_url, title) VALUES (?, ?, ?)",
            (file_id, youtube_url, title)
        )
        await db.commit()

async def get_random_video():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT file_id, youtube_url, title FROM videos ORDER BY RANDOM() LIMIT 1") as cursor:
            return await cursor.fetchone()