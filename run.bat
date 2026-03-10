@echo off
chcp 65001 > nul

REM RANC Auto Inspector Daemon 실행 스크립트 (Windows)
REM 사용법: run.bat [옵션]

setlocal enabledelayedexpansion

REM 기본 디렉토리 설정
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo ========================================================
echo        RANC Auto Inspector 서버 시작 준비 중...
echo ========================================================
echo.

REM [핵심 1] 기존 포트(8000) 강제 정리 (좀비 프로세스 암살)
echo [1/4] 서버 찌꺼기 정리 중 (8000번 포트 확보)...
for /f "tokens=5" %%a in ('netstat -a -n -o ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo  - 8000번 포트 사용 중인 이전 서버 강제 종료 PID: %%a
    taskkill /F /PID %%a > nul 2>&1
)
echo.

REM [기존 로직 보존] 가상환경 확인 및 활성화 / 없으면 자동 설치
echo [2/4] 파이썬 가상환경 설정 중...
if exist "venv\Scripts\activate.bat" (
    echo  - 기존 가상환경 활성화 중...
    call venv\Scripts\activate.bat
) else (
    echo  - 가상환경이 없습니다. 새로 생성합니다...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo  - 의존성 패키지 설치 중...
    pip install -r requirements.txt
)
echo.

REM [핵심 2] 브라우저 자동 실행 (백그라운드에서 2초 대기 후 실행)
echo [3/4] 대시보드 브라우저 자동 실행 대기 중...
start /B cmd /c "timeout /t 2 > nul & start http://localhost:8000"
echo.

REM 통합 서버 실행
echo [4/4] RANC Auto Inspector 통합 서버 시작!
echo.
echo 디렉토리 정보:
echo   입력 디렉토리: data\input_logs\
echo   출력 디렉토리: data\output_results\
echo.
echo 새 CSV 파일을 data\input_logs\에 놓으면 자동으로 처리됩니다.
echo 종료하려면 이 창을 닫거나 Ctrl+C를 누르세요.
echo.

REM 서버 본체 실행 (여기서 터미널이 멈춰서 서버를 띄워둡니다)
python -m src.integrated_server %*

REM 일시정지 (오류 발생 시 창이 닫히지 않도록)
if errorlevel 1 (
    echo.
    echo 프로그램이 오류와 함께 종료되었습니다. 오류 코드: %errorlevel%
    pause
)