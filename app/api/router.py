from fastapi import APIRouter

from app.api.admin import categories as admin_categories
from app.api.admin import orders as admin_orders
from app.api.admin import products as admin_products
from app.api.admin import stores as admin_stores
from app.api.customer import orders as customer_orders
from app.api.customer import users as customer_users
from app.api.public import categories as public_categories
from app.api.public import products as public_products
from app.api.public import stores as public_stores

api_router = APIRouter(prefix="/api/v1")

# Public — no authentication required.
api_router.include_router(public_stores.router)
api_router.include_router(public_categories.router)
api_router.include_router(public_products.router)

# Customer — requires a signed-in user.
api_router.include_router(customer_users.router)
api_router.include_router(customer_orders.router)

# Admin — requires a signed-in ADMIN with store membership.
api_router.include_router(admin_stores.router)
api_router.include_router(admin_categories.router)
api_router.include_router(admin_products.router)
api_router.include_router(admin_orders.router)
