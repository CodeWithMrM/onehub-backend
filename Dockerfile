FROM python:3.12-slim

WORKDIR /app

# System deps needed by Prisma's engine binaries.
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssl \
    ca-certificates \
    libatomic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY prisma ./prisma
RUN prisma generate --schema=prisma/schema.prisma

COPY app ./app

# No secrets baked into the image — everything comes from the
# runtime environment (see .env.example).
ENV ENVIRONMENT=production
EXPOSE 8000


CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]