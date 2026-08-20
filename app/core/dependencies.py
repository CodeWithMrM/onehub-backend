"""
Reusable FastAPI dependencies for authentication and authorization.

Routes should never decode tokens or query StoreMember directly —
they depend on these functions instead, so the authorization logic
lives in exactly one place.
"""

from typing import Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prisma.models import User

from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import verify_clerk_token
from app.db.prisma import db
from app.services.user_service import get_or_create_user

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[User]:
    """
    Returns the authenticated User, or None if no/invalid token was
    supplied. Use this for routes where auth is optional (e.g.
    browsing the public menu while signed out).
    """
    if credentials is None:
        return None

    claims = verify_clerk_token(credentials.credentials)
    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        raise UnauthorizedError("Invalid authentication token.")

    user = await get_or_create_user(clerk_user_id)
    request.state.current_user = user
    return user


async def require_authenticated_user(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """Use for any route that requires the caller to be signed in."""
    if user is None:
        raise UnauthorizedError("Authentication required.")
    return user


async def require_admin(
    user: User = Depends(require_authenticated_user),
) -> User:
    """Use for admin-only routes that aren't scoped to a specific store."""
    if user.role != "ADMIN":
        raise ForbiddenError("Admin access required.")
    return user


async def require_store_member(store_id: str, user: User = Depends(require_admin)):
    """
    Verifies the authenticated admin belongs to `store_id`. Returns
    the StoreMember row (which carries their role at that store).
    Never let the frontend's claimed store id go unchecked — this is
    what enforces store isolation (spec §62).
    """
    membership = await db.storemember.find_unique(
        where={"userId_storeId": {"userId": user.id, "storeId": store_id}}
    )
    if membership is None:
        raise ForbiddenError("You do not have access to this store.")
    return membership


async def check_store_role(user_id: str, store_id: str, allowed_roles: tuple[str, ...] | None = None):
    """
    Plain (non-FastAPI-dependency) version of the store-membership
    check, for routes whose path parameter is a resource id (e.g.
    /admin/categories/{category_id}) rather than a store id. Look up
    the resource's storeId first, then call this.
    """
    membership = await db.storemember.find_unique(
        where={"userId_storeId": {"userId": user_id, "storeId": store_id}}
    )
    if membership is None:
        raise ForbiddenError("You do not have access to this store.")
    if allowed_roles and membership.role not in allowed_roles:
        raise ForbiddenError(
            f"Your role ({membership.role}) does not have permission for this action."
        )
    return membership


def require_store_role(*allowed_roles: str):
    """
    Dependency factory: require_store_role("OWNER", "MANAGER") ensures
    the caller's StoreMember role at the target store is one of the
    given roles (e.g. blocking STAFF from mutating endpoints).
    """

    async def dependency(membership=Depends(require_store_member)):
        if membership.role not in allowed_roles:
            raise ForbiddenError(
                f"Your role ({membership.role}) does not have permission for this action."
            )
        return membership

    return dependency
