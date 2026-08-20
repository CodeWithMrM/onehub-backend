"""
Development seed script.

Creates one demo store ("Mama's Kota") with categories, products, and
customization options so the frontend has something to render locally.

This is dev-only. The production database must work correctly with
zero products — the API already handles that case; this script exists
purely to make local development pleasant.

Run with:
    python -m prisma.seed
"""

import asyncio
import os

from prisma import Prisma


async def main() -> None:
    db = Prisma()
    await db.connect()

    try:
        store = await db.store.find_unique(where={"slug": "mamas-kota"})
        if store is None:
            store = await db.store.create(
                data={
                    "name": "Mama's Kota",
                    "slug": "mamas-kota",
                    "description": "Local spaza shop serving kotas, chips, and drinks.",
                    "phone": "0712345678",
                    "address": "123 Main Road",
                    "isActive": True,
                }
            )
            print(f"Created store: {store.name} ({store.id})")
        else:
            print(f"Store already exists: {store.name} ({store.id})")

        category_defs = [
            {"name": "Kotas", "slug": "kotas", "sortOrder": 1},
            {"name": "Chips", "slug": "chips", "sortOrder": 2},
            {"name": "Drinks", "slug": "drinks", "sortOrder": 3},
            {"name": "Extras", "slug": "extras", "sortOrder": 4},
        ]
        categories = {}
        for c in category_defs:
            existing = await db.category.find_unique(
                where={"storeId_slug": {"storeId": store.id, "slug": c["slug"]}}
            )
            if existing:
                categories[c["slug"]] = existing
                continue
            created = await db.category.create(
                data={
                    "storeId": store.id,
                    "name": c["name"],
                    "slug": c["slug"],
                    "sortOrder": c["sortOrder"],
                    "isActive": True,
                }
            )
            categories[c["slug"]] = created
            print(f"Created category: {created.name}")

        existing_product = await db.product.find_unique(
            where={"storeId_slug": {"storeId": store.id, "slug": "russian-kota"}}
        )
        if existing_product is None:
            product = await db.product.create(
                data={
                    "storeId": store.id,
                    "categoryId": categories["kotas"].id,
                    "name": "Russian Kota",
                    "slug": "russian-kota",
                    "description": "A delicious kota with Russian, egg and cheese.",
                    "price": "45.00",
                    "isAvailable": True,
                    "sortOrder": 1,
                }
            )
            print(f"Created product: {product.name}")

            protein_group = await db.productoptiongroup.create(
                data={
                    "productId": product.id,
                    "name": "Protein",
                    "required": True,
                    "multiSelect": False,
                    "minSelections": 1,
                    "maxSelections": 1,
                    "sortOrder": 1,
                }
            )
            for i, name in enumerate(["Russian", "Vienna", "Polony"]):
                await db.productoption.create(
                    data={
                        "groupId": protein_group.id,
                        "name": name,
                        "price": "0.00",
                        "isAvailable": True,
                        "sortOrder": i,
                    }
                )

            extras_group = await db.productoptiongroup.create(
                data={
                    "productId": product.id,
                    "name": "Extras",
                    "required": False,
                    "multiSelect": True,
                    "minSelections": 0,
                    "maxSelections": 4,
                    "sortOrder": 2,
                }
            )
            for i, (name, price) in enumerate(
                [("Cheese", "5.00"), ("Egg", "5.00"), ("Atchar", "3.00"), ("Extra sauce", "2.00")]
            ):
                await db.productoption.create(
                    data={
                        "groupId": extras_group.id,
                        "name": name,
                        "price": price,
                        "isAvailable": True,
                        "sortOrder": i,
                    }
                )

            await db.product.create(
                data={
                    "storeId": store.id,
                    "categoryId": categories["drinks"].id,
                    "name": "Coke 300ml",
                    "slug": "coke-300ml",
                    "description": "Ice cold Coca-Cola.",
                    "price": "15.00",
                    "isAvailable": True,
                    "sortOrder": 1,
                }
            )
            print("Created sample drink")
        else:
            print("Sample products already exist, skipping.")

        dev_admin_clerk_id = os.getenv("DEV_ADMIN_CLERK_USER_ID")
        if dev_admin_clerk_id:
            user = await db.user.find_unique(where={"clerkUserId": dev_admin_clerk_id})
            if user is None:
                user = await db.user.create(
                    data={
                        "clerkUserId": dev_admin_clerk_id,
                        "name": "Dev Admin",
                        "role": "ADMIN",
                    }
                )
                print(f"Created dev admin user: {user.id}")

            membership = await db.storemember.find_unique(
                where={"userId_storeId": {"userId": user.id, "storeId": store.id}}
            )
            if membership is None:
                await db.storemember.create(
                    data={"userId": user.id, "storeId": store.id, "role": "OWNER"}
                )
                print("Linked dev admin as OWNER of Mama's Kota")
        else:
            print(
                "DEV_ADMIN_CLERK_USER_ID not set — skipping dev admin creation. "
                "Set it in .env if you want a local admin membership seeded."
            )

        print("Seed complete.")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
