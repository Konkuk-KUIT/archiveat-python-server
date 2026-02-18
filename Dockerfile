FROM python:3.11-slim

WORKDIR /app

# Sentry 환경 변수를 위한 ARG 선언
ARG SENTRY_DSN
ARG SENTRY_ENVIRONMENT=production

# ARG를 ENV로 변환 (런타임에 사용)
ENV SENTRY_DSN=${SENTRY_DSN}
ENV SENTRY_ENVIRONMENT=${SENTRY_ENVIRONMENT}

# curl 설치 (health check용)
# RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ffmpeg \
  && rm -rf /var/lib/apt/lists/*

# requirements.txt 복사 및 설치
COPY requirements.cpu.txt .
# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
      --extra-index-url https://download.pytorch.org/whl/cpu \
      -r requirements.cpu.txt

# 애플리케이션 코드 복사
COPY . .

# Health check 추가
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 포트 노출
EXPOSE 8000

# 애플리케이션 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
