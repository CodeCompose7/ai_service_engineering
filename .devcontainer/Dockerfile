# Dev environment for the AI 서비스 엔지니어링 공통 VOD course.
# 모든 섹션(S1~S5 + 캡스톤)이 이 컨테이너 하나를 공유하며,
# 의존성은 /workspace/.venv 에 산다 (postCreateCommand의 `uv sync`가 생성).
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        curl \
        ca-certificates \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package manager) from the official image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /workspace

SHELL ["/bin/bash", "-c"]
