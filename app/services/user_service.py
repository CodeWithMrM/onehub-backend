"""
Business logic for mapping an authenticated Clerk identity to a
local `User` row. The database is the source of truth for
application-level fields (name, phone, role) — Clerk only proves
who someone is, not what they're allowed to do.
"""

from prisma.models import User

from app.db.prisma import db


async def get_or_create_user(clerk_user_id: str, name: str | None = None) -> User:
    user = await db.user.find_unique(where={"clerkUserId": clerk_user_id})
    if user is not None:
        return user

    return await db.user.create(
        data={
            "clerkUserId": clerk_user_id,
            "name": name,
        }
    )


async def get_user_by_clerk_id(clerk_user_id: str) -> User | None:
    return await db.user.find_unique(where={"clerkUserId": clerk_user_id})
