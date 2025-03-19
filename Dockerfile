# Dockerfile
FROM python:3.12-slim

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 파일 복사 및 설치
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# 프로젝트 전체 소스 복사
COPY . /app/

# static 파일 수집 (필요한 경우)
RUN python manage.py collectstatic --noinput

# wait-for-it.sh 스크립트 복사 및 실행 권한 부여
COPY wait-for-it.sh /app/wait-for-it.sh
RUN chmod +x /app/wait-for-it.sh

# entrypoint.sh 복사 및 실행 권한 부여
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh


# 컨테이너 포트 노출 (Daphne의 기본 포트 8000)
EXPOSE 8000

# entrypoint 스크립트 실행 (자동으로 makemigrations, migrate, collectstatic 후 Daphne 실행)
ENTRYPOINT ["/app/entrypoint.sh"]
