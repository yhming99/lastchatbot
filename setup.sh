#!/bin/bash

# 스크립트 실행 오류 발생 시 중단
set -e

echo "=== FindYourWave RAG 챗봇 설치 스크립트 ==="
echo "1. 필수 패키지 업데이트 및 설치"
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common

echo "2. Docker 저장소 추가"
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

echo "3. Docker 및 Docker Compose 설치"
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Docker 권한 부여
sudo usermod -aG docker $USER
echo "Docker 그룹에 사용자 추가됨. 변경사항을 적용하려면 로그아웃 후 다시 로그인하거나 다음 명령어를 실행하세요:"
echo "newgrp docker"

echo "4. .env 파일 확인"
if [ ! -f ./app/.env ]; then
    echo ".env 파일이 없습니다. .env.example 파일을 복사하여 생성합니다."
    cp ./app/.env.example ./app/.env
    echo "app/.env 파일을 수정하여 API 키와 필요한 값들을 설정하세요."
    echo "편집하려면: nano app/.env"
    exit 1
fi

echo "5. Docker 컨테이너 빌드 및 실행"
sudo docker compose up -d --build

echo "=== 설치 완료 ==="
echo "FindYourWave RAG 챗봇이 백그라운드에서 실행 중입니다."
echo "서비스 상태 확인: sudo docker compose ps"
echo "로그 확인: sudo docker compose logs -f"
echo "서비스 중지: sudo docker compose down"
echo "웹 API 접근: http://$(curl -s ifconfig.me):8000/docs" 