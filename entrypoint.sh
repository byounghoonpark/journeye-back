#!/bin/bash
set -e

# requirements 재설치 (볼륨 공유 시 보장)
pip install --upgrade pip
pip install -r requirements.txt

# 조건부 마이그레이션, makemigrations, 및 static 수집
if [ "$RUN_MIGRATE" = "true" ]; then
  echo ">> Generating migrations (makemigrations)"
  python manage.py makemigrations --noinput
  echo ">> Applying DB migrations"
  yes | python manage.py migrate --noinput
  echo ">> Collecting static files"
  python manage.py collectstatic --noinput
else
  echo ">> Skipping migrations, makemigrations and collectstatic"
fi

# 넘겨받은 명령 실행 (예: daphne, celery)
exec "$@"