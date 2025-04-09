# Dockerfile (Django + Celery + Daphne)
FROM python:3.12-slim

# 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gdal-bin \
    libgdal-dev \ 
    binutils \
    libproj-dev \
    libgeos-dev \
    gettext \
 && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# requirements 설치
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# 소스 복사
COPY . .

# 포트 오픈
EXPOSE 8000

# 기본 환경 설정
ENV PYTHONUNBUFFERED=1

# 엔트리포인트 등록
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

COPY run_web.sh run_worker.sh /app/
RUN chmod +x /entrypoint.sh /app/run_web.sh /app/run_worker.sh