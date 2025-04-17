FROM python:3.12-slim

WORKDIR /app

# 필요한 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 요구사항 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사
COPY app ./app
COPY README.md .

# 환경 변수 설정을 위한 .env.example 파일 복사
# 주의: 실제 .env 파일은 .gitignore에 있으므로 복사되지 않습니다
# 실행 시 -v 옵션으로 .env 파일을 마운트하거나 환경 변수를 직접 전달해야 합니다
COPY app/.env.example ./app/.env.example

# 포트 설정
EXPOSE 8000

# 실행 명령
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 