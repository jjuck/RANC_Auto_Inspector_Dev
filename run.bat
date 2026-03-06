@echo off
chcp 65001 > nul

REM RANC Auto Inspector Daemon 실행 스크립트 (Windows)
REM 사용법: run.bat [옵션]

setlocal enabledelayedexpansion

REM 기본 디렉토리 설정
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM 가상환경 확인 및 활성화
if exist "venv\Scripts\activate.bat" (
    echo 가상환경 활성화 중...
    call venv\Scripts\activate.bat
) else (
    echo 가상환경이 없습니다. 생성 중...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo 의존성 설치 중...
    pip install -r requirements.txt
)

REM Python 실행
echo RANC Auto Inspector Daemon 시작...
echo.
echo 디렉토리 정보:
echo   입력 디렉토리: data\input_logs\
echo   출력 디렉토리: data\output_results\
echo.
echo 새 CSV 파일을 data\input_logs\에 놓으면 자동으로 처리됩니다.
echo 종료하려면 Ctrl+C를 누르세요.
echo.

REM 메인 프로그램 실행
python -m src.main %*

REM 일시정지 (오류 발생 시 창이 닫히지 않도록)
if errorlevel 1 (
    echo.
    echo 프로그램이 오류와 함께 종료되었습니다. (오류 코드: %errorlevel%)
    pause
)