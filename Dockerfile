# ============= BASE STAGE =============
FROM python:3.12-slim-bullseye AS base

WORKDIR /wbb

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# install required system dependencies for python packages
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    git gcc build-essential \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# install uv
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

ENV PATH="/root/.local/bin/:$PATH"

COPY .python-version .
COPY pyproject.toml .
COPY uv.lock .

# ============= PRODUCTION STAGE =============
FROM base

ENV UV_NO_DEV=1
RUN uv sync
RUN uv pip install nest_asyncio

COPY . .

# Patch pyrogram dispatcher to ignore "Peer id invalid" errors
RUN sed -i 's/await parser(update, users, chats)/try:\n                await parser(update, users, chats)\n            except ValueError as e:\n                if "Peer id invalid" not in str(e):\n                    raise/' .venv/lib/python3.12/site-packages/pyrogram/dispatcher.py || true

# Starting Bot
ENTRYPOINT ["uv", "run", "python", "-m", "wbb"]
