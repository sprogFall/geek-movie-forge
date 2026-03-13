FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY services ./services
COPY workers ./workers
COPY apps/remotion_renderer ./apps/remotion_renderer
COPY packages ./packages
COPY skills ./skills
COPY .env.example ./.env.example

RUN pip install --no-cache-dir -e .
