"""
Single Prisma client instance shared across the app. Connected on
startup and disconnected on shutdown via the lifespan handler in
app.main.
"""

from prisma import Prisma

db = Prisma()


async def connect_db() -> None:
    if not db.is_connected():
        await db.connect()


async def disconnect_db() -> None:
    if db.is_connected():
        await db.disconnect()


async def check_db_connection() -> bool:
    try:
        await db.query_raw("SELECT 1")
        return True
    except Exception:
        return False
