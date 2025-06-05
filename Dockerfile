FROM python:3.10-slim

WORKDIR /app

# 시스템 패키지 업데이트
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 파이썬 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 실행 권한 설정
RUN chmod +x /app/main.py

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1

# 컨테이너 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "info"] 