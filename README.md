# RANC Auto Inspector

실시간 CSV 파일 처리 및 대시보드 모니터링 시스템

## 개요

RANC Auto Inspector는 생산 공정에서 생성되는 CSV 로그 파일을 실시간으로 감시하고, RMS Level dBFS 값을 추출하여 판정한 후 대시보드에 실시간으로 표시하는 통합 시스템입니다.

### 주요 기능
- **실시간 파일 감시**: `data/input_logs/` 디렉토리에 새 CSV 파일이 생성되면 자동 감지
- **자동 처리**: RMS Level dBFS 및 Noise Level 값 추출 → Vrms/LSB/SENS/g 변환 → 합격/불합격 판정
- **실시간 대시보드**: WebSocket을 통한 실시간 결과 표시
- **Zero-Setup 배포**: 단일 실행 파일로 모든 구성 요소 실행
- **통합 서버**: FastAPI 기반 단일 서버 (HTTP + WebSocket + 정적 파일)

## 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CSV 파일 생성  │───▶│   파일 감시 데몬  │───▶│   처리 엔진     │
│  (data/input_logs)│    │  (FileWatcher)  │    │ (CSVProcessor)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                         │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   웹 대시보드    │◀───│   WebSocket     │◀───│   결과 브로드캐스트│
│  (frontend/)    │    │   서버          │    │  (ResultWriter)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 빠른 시작

### 1. 시스템 요구사항
- Python 3.9 이상
- Windows 10/11 또는 Linux/macOS
- 4GB RAM 이상
- 500MB 디스크 공간

### 2. 설치 및 실행 (Zero-Setup)

#### Windows 사용자
1. `run.bat` 파일을 더블클릭
2. 또는 명령 프롬프트에서:
   ```cmd
   run.bat
   ```

#### Linux/macOS 사용자
1. 터미널에서 실행 권한 부여:
   ```bash
   chmod +x run.sh
   ```
2. 실행:
   ```bash
   ./run.sh
   ```

### 3. 접속 및 사용
1. 서버가 시작되면 브라우저에서 다음 주소로 접속:
   ```
   http://localhost:8000
   ```
2. 대시보드가 표시됩니다.
3. CSV 파일을 `data/input_logs/` 디렉토리에 복사하거나 생성합니다.
4. 실시간으로 결과가 대시보드에 표시됩니다.

## CSV 파일 형식

시스템은 다음 형식의 CSV 파일을 처리합니다:

```
"RMS Level","RMS Level",,,,
Channel,"RMS Level","Lower Limit","Passed Lower Limit","Upper Limit","Passed Upper Limit"
,dBFS,dBFS,,dBFS,
Ch1,-24.082399653118497,,True,,True
Ch2,-34.6442157520136,,True,,True

"Noise Level","Noise Level",,,,
Channel,"Noise Level","Lower Limit","Passed Lower Limit","Upper Limit","Passed Upper Limit"
,FS,FS,,FS,
Ch1,0.00177202812042252,,True,,True
Ch2,0.0019964198465005,,True,,True
```

**중요**: RMS Level 섹션에서 `Ch1` 행의 `RMS Level` 값은 dBFS 단위, Noise Level 섹션에서 `Ch1` 행의 `Noise Level` 값은 FS 단위여야 합니다.

## 대시보드 기능

### 실시간 모니터링
- 현재 처리 결과 실시간 표시
- Vrms 값, LSB, SENS, g 값 계산 결과
- 합격/불합격 판정 배지
- 허용 범위 시각화

### 기록 관리
- 처리 이력 테이블
- 개별 결과 재생 기능
- 이력 삭제 기능
- 통계 정보

### 시스템 상태
- WebSocket 연결 상태
- 서버 건강 상태
- 실시간 업데이트 표시기

## 고급 설정

### 포트 변경
기본 포트(8000)를 변경하려면:

```bash
# Windows
set PORT=8080 && python -m src.integrated_server

# Linux/macOS
PORT=8080 python -m src.integrated_server
```

### 디렉토리 구성
```
RANC_Auto_Inspector_Dev/
├── data/
│   ├── input_logs/      # 입력 CSV 파일 디렉토리
│   └── output_results/  # 처리 결과 CSV 파일
├── frontend/            # 웹 대시보드 파일
├── src/                 # Python 소스 코드
├── run.bat              # Windows 실행 스크립트
├── run.sh               # Linux/macOS 실행 스크립트
└── requirements.txt     # Python 의존성
```

### 로그 파일
- `inspector.log`: 시스템 로그 파일
- 콘솔 출력: 실시간 처리 상태

## 문제 해결

### 일반적인 문제

#### 1. 서버가 시작되지 않음
- Python 3.9 이상이 설치되어 있는지 확인:
  ```bash
  python --version
  ```
- 의존성 패키지 설치:
  ```bash
  pip install -r requirements.txt
  ```

#### 2. 대시보드에 접속할 수 없음
- 방화벽 설정 확인 (포트 8000 열기)
- 서버가 실행 중인지 확인:
  ```bash
  curl http://localhost:8000/health
  ```

#### 3. CSV 파일이 처리되지 않음
- 파일이 `data/input_logs/` 디렉토리에 있는지 확인
- CSV 형식이 올바른지 확인 (RMS Level 섹션의 Ch1 dBFS 값, Noise Level 섹션의 Ch1 FS 값)
- 파일 확장자가 `.csv`인지 확인

#### 4. WebSocket 연결 실패
- 브라우저 콘솔에서 오류 확인 (F12 → Console)
- 서버 로그 확인:
  ```
  inspector.log 파일 확인
  ```

### 로그 확인
- Windows: `inspector.log` 파일 열기
- Linux/macOS: `tail -f inspector.log`

## 개발자 가이드

### 프로젝트 구조
```
src/
├── calculator.py        # dBFS/Vrms 변환 계산
├── csv_processor.py    # CSV 파일 처리
├── file_watcher.py     # 파일 시스템 감시
├── integrated_server.py # 통합 서버 (주 진입점)
├── judge.py            # 합격/불합격 판정
├── main.py             # 원래 데몬 (레거시)
├── result_writer.py    # 결과 저장
└── websocket_server.py # WebSocket 서버
```

### 새로운 기능 추가
1. 소스 코드 수정
2. 테스트:
   ```bash
   python -m src.integrated_server
   ```
3. 변경 사항 확인

### 빌드 및 배포
1. 가상환경 생성:
   ```bash
   python -m venv venv
   ```
2. 의존성 설치:
   ```bash
   pip install -r requirements.txt
   ```
3. 실행 스크립트 테스트

## 라이선스

프로젝트 내부 사용을 위한 전용 소프트웨어입니다.

## 지원

문제가 발생하면 다음을 확인하세요:
1. `inspector.log` 파일
2. 서버 콘솔 출력
3. 브라우저 개발자 도구 (F12)

기술 지원: 시스템 관리자에게 문의
