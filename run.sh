#!/bin/bash
# RANC Auto Inspector Daemon 실행 스크립트 (Linux/Mac)
# 사용법: ./run.sh [옵션]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 가상환경 확인 및 활성화
if [ -d "venv" ]; then
    echo "가상환경 활성화 중..."
    source venv/bin/activate
else
    echo "가상환경이 없습니다. 생성 중..."
    python3 -m venv venv
    source venv/bin/activate
    echo "의존성 설치 중..."
    pip install -r requirements.txt
fi

# Python 실행
echo "RANC Auto Inspector Daemon 시작..."
echo ""
echo "디렉토리 정보:"
echo "  입력 디렉토리: data/input_logs/"
echo "  출력 디렉토리: data/output_results/"
echo ""
echo "새 CSV 파일을 data/input_logs/에 놓으면 자동으로 처리됩니다."
echo "종료하려면 Ctrl+C를 누르세요."
echo ""

# 통합 서버 실행 (FastAPI + WebSocket + 프론트엔드)
echo "통합 서버 시작: http://localhost:8000"
echo "대시보드 접속: http://localhost:8000/"
echo ""
python -m src.integrated_server "$@"

# 오류 코드 확인
if [ $? -ne 0 ]; then
    echo ""
    echo "프로그램이 오류와 함께 종료되었습니다. (오류 코드: $?)"
    read -p "계속하려면 아무 키나 누르세요..."
fi