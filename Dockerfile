FROM python:3.10-slim

# 캐시된 모델 저장을 위한 환경 변수 설정
ENV TRANSFORMERS_CACHE=/app/cache
ENV SENTENCE_TRANSFORMERS_HOME=/app/cache
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 패키지 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 파이썬 패키지 설치만 먼저 분리해서 캐시 활용
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# 나머지 소스 코드 복사
COPY . .

# 실행 권한 설정
RUN chmod +x /app/main.py

# 컨테이너 실행 (로깅 활성화)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "info"] 