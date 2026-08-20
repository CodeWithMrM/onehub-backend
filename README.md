# OneHub API

Backend for **OneHub** — a food ordering platform, currently serving one
spaza/kota shop but designed from day one to support multiple stores.

One FastAPI backend. One Neon Postgres database. One Clerk auth system.
Both **OneHub Customer** and **OneHub Admin** are Vite + React web apps
(browser-based, no Expo) that talk to this API and never touch the
database directly.

---

## 1. Overview

```
OneHub Customer (Vite/React, browser) ──┐
                                          ├──► FastAPI (/api/v1) ──► Prisma ──► Neon Postgres
OneHub Admin (Vite/React, browser)     ──┘         ▲
                                                     │
                                                  Clerk JWT
```

- **Public routes** (`/api/v1/stores`, `/api/v1/products`, ...) — no auth,
  used for browsing the menu.
- **Customer routes** (`/api/v1/me`, `/api/v1/orders`) — require a signed-in
  Clerk user.
- **Admin routes** (`/api/v1/admin/...`) — require a signed-in Clerk user
  whose local `role` is `ADMIN` *and* who has a `StoreMember` row for the
  store being accessed. Store membership is always checked server-side —
  the frontend's claimed store id is never trusted.

## 2. Requirements

- Python 3.12+
- A Neon Postgres database (or any Postgres 14+ for local dev)
- A Clerk application (for `CLERK_SECRET_KEY` / `CLERK_JWT_ISSUER`)
- Redis (optional locally, recommended in production — see §7)

## 3. Environment variables

Copy `.env.example` to `.env` and fill in real values:

```bash
cp .env.example .env
```

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Pooled Neon connection string, used at runtime |
| `DIRECT_DATABASE_URL` | Direct (non-pooled) Neon connection string, used by Prisma migrations |
| `CLERK_SECRET_KEY` | From your Clerk dashboard |
| `CLERK_JWT_ISSUER` | e.g. `https://your-app.clerk.accounts.dev` — used to fetch Clerk's JWKS and verify session tokens |
| `REDIS_URL` | Optional locally; falls back to an in-memory rate limiter if unset or unreachable |
| `ENVIRONMENT` | `development` or `production` |
| `CORS_ORIGINS` | Comma-separated allowed origins (never `*` in production) |
| `DEV_ADMIN_CLERK_USER_ID` | Optional — seeds a local admin membership for this Clerk user id |

This repo ships with a `.env` already populated with **placeholder** values
so the app boots locally without crashing. Replace them with real
credentials before connecting to an actual database or verifying real
Clerk tokens.

## 4. Neon setup

1. Create a Neon project and database.
2. Neon gives you both a **pooled** connection string (for normal query
   traffic) and a **direct** connection string (required for Prisma
   migrations). Put the pooled one in `DATABASE_URL` and the direct one in
   `DIRECT_DATABASE_URL`.
3. Both must include `?sslmode=require`.

## 5. Clerk setup

1. Create a Clerk application (or reuse an existing one — the customer and
   future admin apps share the same Clerk instance).
2. Copy the **Secret Key** into `CLERK_SECRET_KEY`.
3. Copy your instance's issuer URL (visible in Clerk's JWT template /
   API keys page, formatted like `https://xxxx.clerk.accounts.dev`) into
   `CLERK_JWT_ISSUER`. The backend uses this to fetch Clerk's public JWKS
   and verify session tokens — it never calls back to Clerk's API on the
   hot path.
4. To make a user an admin: set their local `User.role` to `ADMIN` and
   create a `StoreMember` row linking them to a store (see §11, seed data).
   There's no separate admin signup flow — Clerk handles authentication
   for both apps identically; this backend decides authorization.

## 6. Redis setup (rate limiting)

Rate limiting works out of the box locally with **no Redis required** —
`app/core/rate_limit.py` automatically falls back to an in-memory,
per-process counter if `REDIS_URL` is empty or the connection fails, so a
missing Redis instance never blocks local development.

In production, set `REDIS_URL` so limits are shared correctly across
multiple worker processes/containers.

## 7. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 8. Prisma setup & migrations

> **Verify the exact commands against your installed `prisma` package
> version** (`pip show prisma`) before running these in a new environment —
> the Prisma Python CLI's flags have changed between minor versions.
> These are correct for `prisma==0.13.1`, pinned in `requirements.txt`.

Generate the Python client from the schema:

```bash
prisma generate --schema=prisma/schema.prisma
```

Apply the schema to your database (creates tables):

```bash
prisma db push --schema=prisma/schema.prisma
```

For a real migration history instead of `db push` (recommended once you
have a production database):

```bash
prisma migrate dev --schema=prisma/schema.prisma --name init
```

> **Note on this delivery:** `prisma generate` downloads Prisma's query/
> schema engine binaries from `binaries.prisma.sh`. In the sandboxed
> environment used to build this backend, outbound network access is
> restricted to a small allow-list (PyPI, npm, GitHub) that does **not**
> include Prisma's binary CDN, so codegen could not be run or verified
> end-to-end here. Every `.py` file has been syntax-checked
> (`python -m py_compile`) and `requirements.txt` has been verified to
> install cleanly from PyPI, but you'll need to run `prisma generate` in
> your own environment (which should have normal internet access) before
> the app will actually start. This is a one-time step — there's no
> reason to expect it to fail there.

## 9. Seed data

```bash
python -m prisma.seed
```

Creates one demo store ("Mama's Kota"), four categories, a Russian Kota
with Protein/Extras customization, and a Coke. If `DEV_ADMIN_CLERK_USER_ID`
is set in `.env`, it also creates a local admin `User` + `StoreMember`
(`OWNER`) for that Clerk user id, so you can hit the `/admin` routes
locally without manually inserting rows.

The **production** database is never required to have any of this —
every list endpoint returns an empty, correctly-shaped page (see §"Empty
store support" below) rather than erroring when a store has no products.

## 10. Running locally

```bash
uvicorn app.main:app --reload
```

- API: http://localhost:8000/api/v1
- Interactive docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/health and http://localhost:8000/health/db

## 11. Testing

```bash
pytest
```

The test suite (`tests/`) uses FastAPI's `dependency_overrides` to fake
authentication and `unittest.mock` to stand in for Prisma calls, so it
runs without a live database — useful for fast, deterministic checks of
routing, validation, and authorization logic (store isolation, role
permissions, order-status transition rules, etc.).

These tests require the generated Prisma client to import successfully
(`prisma generate` — see §8) even though they mock its calls, since
`app/db/prisma.py` imports `from prisma import Prisma` at module load
time. Run `prisma generate` once before your first `pytest` run.

For true integration coverage against a real database, point
`DATABASE_URL`/`DIRECT_DATABASE_URL` at a disposable Neon branch, run
`prisma db push`, and adapt the fixtures in `tests/conftest.py` to hit
the real `db` object instead of mocking it.

## 12. API documentation

FastAPI auto-generates OpenAPI docs at `/docs` and `/redoc`, grouped into
**Public**, **Customer**, **Admin**, and **System** tags.

## 13. Docker

```bash
docker build -t onehub-api .
docker run -p 8000:8000 --env-file .env onehub-api
```

No secrets are baked into the image — everything comes from the runtime
environment.

## 14. Production deployment

- Run `prisma migrate deploy` (not `db push`) against production.
- Set `ENVIRONMENT=production` — this disables verbose error bodies and
  requires `CORS_ORIGINS` to be explicitly set (no wildcard fallback).
- Set a real `REDIS_URL` so rate limits are enforced consistently across
  instances.
- Put the API behind HTTPS; Clerk session tokens should never travel over
  plain HTTP.

## 15. Connecting the OneHub Customer app (Vite/React)

The customer app is a browser-based SPA (see the separate `onehub-web`
project), so two things matter that don't apply to a native app:

1. **CORS.** The browser enforces this, not the API, but the API has to
   explicitly allow the page's origin or every request gets blocked
   before your route code even runs. Set `CORS_ORIGINS` to include
   wherever the web app is served from:

   ```env
   # Local dev (Vite's default port)
   CORS_ORIGINS=http://localhost:5173

   # Add your deployed URL once it exists
   CORS_ORIGINS=http://localhost:5173,https://onehub-web.example.com
   ```

   In non-production environments the API also falls back to allowing
   `http://localhost:5173` (customer web dev), `http://localhost:5174`
   (admin dashboard dev), and their preview-build ports automatically —
   so local development works even before you set `CORS_ORIGINS`. In
   production, `CORS_ORIGINS` must be set explicitly; there is no
   wildcard fallback.

2. **Attaching the Clerk token to every request.** `@clerk/clerk-react`'s
   `useAuth()` hook exposes `getToken()`, which the web app calls before
   each authenticated request:

   ```js
   import { useAuth } from "@clerk/clerk-react";

   const { getToken } = useAuth();

   async function apiFetch(path, options = {}) {
     const token = await getToken();
     const response = await fetch(`${import.meta.env.VITE_API_URL}${path}`, {
       ...options,
       headers: {
         "Content-Type": "application/json",
         ...(token ? { Authorization: `Bearer ${token}` } : {}),
         ...options.headers,
       },
     });
     if (!response.ok) {
       const body = await response.json().catch(() => null);
       throw new Error(body?.error?.message || "Request failed");
     }
     return response.json();
   }
   ```

   This is exactly the shape `onehub-web/src/lib/api.js` is written to
   drop real calls into — each mock function (`getProducts`,
   `getProduct`, `createOrder`, etc.) becomes a thin wrapper around
   `apiFetch(...)` with no other code changing, since every screen
   already consumes `lib/api.js`'s functions rather than calling
   `fetch` directly.

Once wired up, the browsing routes work signed-out; placing an order
requires a signed-in Clerk session, same as before:

```
GET  /api/v1/stores
GET  /api/v1/stores/{id}
GET  /api/v1/stores/{id}/categories
GET  /api/v1/stores/{id}/products?category_id=&search=&page=&page_size=
GET  /api/v1/products/{id}

GET  /api/v1/me

POST /api/v1/orders          (send Idempotency-Key header)
GET  /api/v1/orders
GET  /api/v1/orders/{id}
```

### Example: create an order

```bash
curl -X POST https://api.onehub.example.com/api/v1/orders \
  -H "Authorization: Bearer $CLERK_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: 6f2a9e2e-1a3b-4c9d-9c2f-1a2b3c4d5e6f" \
  -d '{
    "storeId": "store-uuid",
    "customerName": "John",
    "customerPhone": "0712345678",
    "pickupType": "ASAP",
    "notes": "Extra sauce",
    "items": [
      { "productId": "product-uuid", "quantity": 2, "optionIds": ["option-uuid"] }
    ]
  }'
```

Note there is no `price`, `subtotal`, or `total` in the request — the
server calculates all of it from the current catalog state, inside a
transaction, and rejects the request if any product/option is missing,
unavailable, or doesn't belong to the given store.

## 16. Connecting the OneHub Admin app (Vite/React)

Same two things as the customer app apply here — CORS (covered above,
`localhost:5174` is allowed by default in non-production) and attaching
a Clerk token via `getToken()` to every request. The admin app
(`onehub-admin`) uses the identical `apiClient.js` pattern as the
customer app.

One difference: being signed in with Clerk isn't enough to see anything
useful here — the account also needs a local `role = ADMIN` and at least
one `StoreMember` row (see the backend's `prisma/seed.py` for a way to
seed this locally via `DEV_ADMIN_CLERK_USER_ID`). Without that, every
`/admin` call correctly 403s; `onehub-admin`'s `StoreGate` component
shows a friendly "no store access" screen instead of a raw error in that
case.

```
GET   /api/v1/admin/stores
GET   /api/v1/admin/stores/{id}/dashboard

GET   /api/v1/admin/stores/{id}/categories
POST  /api/v1/admin/stores/{id}/categories
GET   /api/v1/admin/categories/{id}
PATCH /api/v1/admin/categories/{id}
DELETE /api/v1/admin/categories/{id}

GET   /api/v1/admin/stores/{id}/products
POST  /api/v1/admin/stores/{id}/products
GET   /api/v1/admin/products/{id}
PATCH /api/v1/admin/products/{id}
DELETE /api/v1/admin/products/{id}

POST   /api/v1/admin/products/{id}/option-groups
PATCH  /api/v1/admin/option-groups/{id}
DELETE /api/v1/admin/option-groups/{id}
POST   /api/v1/admin/option-groups/{id}/options
PATCH  /api/v1/admin/options/{id}
DELETE /api/v1/admin/options/{id}

GET   /api/v1/admin/stores/{id}/orders?status=&page=&page_size=
GET   /api/v1/admin/orders/{id}
PATCH /api/v1/admin/orders/{id}/status
```

`OWNER`/`MANAGER` can create/edit/delete; `STAFF` is read-only on
categories/products and can still update order status. Every mutation is
scoped to the caller's `StoreMember` row — an admin at Store A gets a 403
if they try to touch Store B's data, even if they somehow obtain Store
B's id.

`onehub-admin`'s Orders page polls `GET /api/v1/admin/stores/{id}/orders`
every 10 seconds for new orders in this MVP; no WebSocket/SSE
infrastructure has been added, though the service layer
(`order_service.py`) is structured so that can be layered in later
without a rewrite.

## 17. What was intentionally not built

Per the MVP scope: WhatsApp integration, payments, delivery/drivers,
loyalty/coupons/promotions/referrals, push notifications, complex
analytics, live maps, chat, social features, a separate admin backend or
database. The dashboard endpoint returns simple counts only — no charts,
no historical analytics.

## Project structure

```
app/
├── main.py              FastAPI app, lifespan, CORS, error handlers, /health
├── core/                config, Clerk verification, rate limiting, auth dependencies
├── db/prisma.py         Shared Prisma client singleton
├── schemas/             Pydantic request/response models
├── services/            Business logic (the only layer that touches Prisma directly)
└── api/
    ├── public/          No auth: stores, categories, products
    ├── customer/        Auth required: /me, orders
    └── admin/            Auth + store membership required

prisma/
├── schema.prisma        Database models, enums, indexes
└── seed.py              Dev-only demo data

tests/                   pytest suite (mocked DB, real routing/auth logic)
```
