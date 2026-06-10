# 배포 이미지 — 개발 devcontainer와 다르다.
# devcontainer는 개발 도구(편집기 확장·디버거·테스트)를 다 담지만, 배포 이미지는
# 서버를 돌리는 데 필요한 것만 담아 작고 빠르게 만든다.
FROM python:3.13-slim

WORKDIR /app

# uv로 의존성만 먼저 설치한다. 소스보다 덜 바뀌므로 캐시가 살아 빌드가 빠르다.
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

# 소스를 복사한다. 키(.env)는 굽지 않는다.
COPY src ./src

# API 키는 이미지에 넣지 않고 런타임 환경변수로 주입한다.
#   docker run -e GEMINI_API_KEY=... -e DEFAULT_PROVIDER=gemini -p 8000:8000 image
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "section5.lec02.app:app", "--host", "0.0.0.0", "--port", "8000"]
