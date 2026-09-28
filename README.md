# RANC Auto Inspector

실시간 CSV 파일 처리 및 대시보드 모니터링 시스템

## 개요

RANC Auto Inspector는 생산 공정에서 생성되는 CSV 로그 파일을 실시간으로 감시하고, RMS Level dBFS 값을 추출하여 판정한 후 대시보드에 실시간으로 표시하는 통합 시스템입니다.

### 주요 기능
- **실시간 파일 감시**: `data/input_logs/` 디렉토리에 새 CSV 파일이 생성되면 자동 감지
- **자동 처리**: RMS Level dBFS 및 Noise Level 값 추출 → Vrms/LSB/SENS/g 변환 → 합격/불합격 판정
- **실시간 대시보드**: WebSocket을 통한 실시간 결과 표시
- **날짜별 결과 저장**: X, Y, Z별 일별 CSV와 SN별 통합 CSV 저장
- **즉시 통합**: 측정 저장 직후 같은 날짜의 통합 결과 갱신, 변경 없는 날짜는 건너뜀
- **실행 스크립트**: `run.bat` 또는 `run.sh`로 가상환경 준비와 서버 실행
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
- Python 3.10 이상 (개발본 검증 환경: Python 3.12)
- Windows 10/11 또는 Linux/macOS
- 4GB RAM 이상
- 500MB 디스크 공간

### 2. 설치 및 실행

개발본은 최초 실행 시 가상환경을 만들고 의존성을 설치하므로 Python과 인터넷 연결이 필요합니다.
내장 Python이 포함된 포터블 배포본은 해당 폴더의 `run.bat`으로 실행합니다.

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

대체 대시보드는 `http://localhost:8000/alt`에서 열 수 있습니다.
검사할 축(X, Y, Z)을 대시보드에서 선택하면 이후 결과가 해당 축 폴더에 저장됩니다. 서버 시작 시 기본 축은 X입니다.

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

**측정값 선택**: RMS Level 섹션의 `Ch1`, `Ch2` 중 dBFS 값이 높은 채널을 사용합니다.
Noise Level도 선택된 채널의 FS 값에 `0.1`을 곱해 저장합니다.

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
기본 포트는 8000입니다. 다른 포트로 직접 실행하려면 프로젝트 루트에서 가상환경을 활성화한 뒤 다음 명령을 사용합니다.

```bash
python -m uvicorn src.integrated_server:app --host 0.0.0.0 --port 8080
```

### 디렉토리 구성
```
RANC_Auto_Inspector_Dev/
├── data/
│   ├── input_logs/      # 입력 CSV 파일 디렉토리
│   └── output_results/
│       ├── X/260704/260704_RANC_X.csv
│       ├── Y/260704/260704_RANC_Y.csv
│       ├── Z/260704/260704_RANC_Z.csv
│       └── merged/260704/
│           ├── 260704_RANC_XYZ.csv        # 해당 날짜의 SN별 통합 결과
│           └── 260704_RANC_XYZ.state.json # 변경 감지 상태
├── frontend/            # 웹 대시보드 파일
├── frontend_alt/        # 대체 대시보드
├── src/                 # Python 소스 코드
├── tests/               # 자동 테스트
├── run.bat              # Windows 실행 스크립트
├── run.sh               # Linux/macOS 실행 스크립트
└── requirements.txt     # Python 의존성
```

### 로그 파일
- `inspector.log`: 시스템 로그 파일
- 콘솔 출력: 실시간 처리 상태

### 날짜별 로그 자동 통합

새 측정 결과를 저장한 직후, 해당 날짜의 X, Y, Z 결과를
`data/output_results/merged/YYMMDD/YYMMDD_RANC_XYZ.csv`에 날짜별로 통합합니다.
폴더와 파일의 날짜는 원본 일별 CSV 파일명의 날짜입니다.
7월 4일 로그는 `merged/260704/260704_RANC_XYZ.csv`,
8월 1일 로그는 `merged/260801/260801_RANC_XYZ.csv`에 각각 저장합니다.
각 파일에는 그날의 결과만 들어가며, 다른 날짜의 축 기록으로 빈칸을 채우지 않습니다.
오늘 측정한 결과도 바로 반영합니다. 원본이 없는 날짜의 파일은 새로 만들지 않습니다.
서버 시작 시와 30초 간격의 확인에서는 원본이 변경되었거나 통합 파일이 없는 날짜만 갱신합니다.
서버가 꺼져 있던 기간의 로그는 다음 시작 시 반영합니다.

- **SN**: 입력 파일명에서 마지막 확장자만 제거한 전체 파일명입니다. 일별 CSV도 `SN` 컬럼으로 저장합니다.
  예: `96398XGR500X251215X052.csv` → `96398XGR500X251215X052`.
  SN의 대소문자와 앞자리 0은 그대로 유지합니다.
- **통합 형식**: SN당 한 행이며 `X_Timestamp`, `X_dBFS`, `X_Judgement`처럼
  축별 컬럼에 처리 시각, 측정값, 판정을 저장합니다. SN은 맨 앞의 공통 컬럼에 한 번만 저장하며 없는 축은 빈칸입니다.
  기존 `Input_Filename` 형식도 읽을 수 있고, 해당 일별 파일에 새 결과를 추가할 때 `SN` 형식으로 변환합니다.
- **중복 기준**: 같은 날짜 안에서 같은 SN과 같은 축의 `Timestamp`가 가장 늦은 행을 선택합니다.
  통합 시 SN 끝의 `_숫자`를 제거하므로 `ABC`, `ABC_1`, `ABC_2`는 `ABC` 한 행으로 묶입니다.
  X, Y, Z 결과는 그 행의 축별 컬럼에 저장합니다. 일별 원본의 SN은 그대로 보존합니다.
  시각이 같으면 마지막으로 읽은 행을 선택합니다. 파일은 경로순, 각 파일은 행순으로 읽습니다.
- **날짜 기준**: 원본 일별 CSV 파일명의 날짜로 나눕니다. 오늘까지 포함하고 서버 PC 기준 미래 날짜의 파일과 기록은 제외합니다.
  시간대가 있는 Timestamp는 PC의 로컬 시각으로 변환해 비교합니다.
- **원본 보관**: 일별 원본 CSV는 유지합니다. 기존 축 폴더 바로 아래의 날짜별 CSV도 통합 대상입니다.
  기존 이력 조회와 통계는 계속 원본 전체 검사 기록을 기준으로 계산합니다.
  축 정보가 없는 과거 `inspection_results.csv`는 자동 통합 대상이 아닙니다.
- **저장 실패**: 임시 파일 작성을 마친 뒤 통합 파일을 교체합니다. 읽기 오류나 Excel 파일 잠금 등으로
  실패하면 기존 통합 파일을 보존하고 30초 후 재시도하며, 원인은 `inspector.log`에 남깁니다.

통합 CSV 옆의 `.state.json` 파일에 원본 경로, 크기, 수정 시각과 통합 파일 상태를 기록합니다.
프로그램을 재시작하거나 날짜가 바뀌어도 변경되지 않은 파일은 다시 읽거나 작성하지 않습니다.
원본 CSV를 외부에서 수정하면 다음 확인 때 반영됩니다. 상태 파일이 없거나 손상되면 해당 날짜를 다시 통합합니다.
업데이트 후 첫 실행에서는 상태 파일 생성을 위해 기존 로그를 한 번 통합합니다.
통합 CSV는 Excel에서 SN 컬럼을 텍스트로 가져와야 앞자리 0이 유지됩니다.

일별 CSV 컬럼은 `Timestamp, SN, dBFS, Vrms, LSB, SENS, g, Judgement, Noise_Level`입니다.
통합 CSV는 공통 `SN`과 각 측정 컬럼에 `X_`, `Y_`, `Z_` 접두사를 붙인 형태입니다.
예를 들어 `ABC.csv`, `ABC_1.csv`, `ABC_2.csv`를 같은 날 서로 다른 축에서 측정하면 통합 결과는 `ABC` 한 행으로 표시됩니다.
일별 CSV에는 각 파일에서 얻은 SN이 그대로 남습니다.

## 문제 해결

### 일반적인 문제

#### 1. 서버가 시작되지 않음
- Python 3.10 이상이 설치되어 있는지 확인:
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
- CSV 형식이 올바른지 확인 (RMS Level의 Ch1/Ch2 dBFS 값, 같은 채널의 Noise Level FS 값)
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
└── result_writer.py    # 일별 저장, SN별 통합, 변경 감지
```

### 새로운 기능 추가
1. 소스 코드 수정
2. 테스트:
   ```bash
   python -m unittest discover -s tests -v
   ```
3. 변경 사항 확인

테스트는 임시 디렉토리에서 측정값 계산, 기존 CSV 호환, 날짜별 SN 통합, 저장 직후 반영,
재시작 후 불필요한 재작성 방지, 파일 잠금 시 원본 보존과 재시도를 검증합니다.
서버 실행 확인은 `python -m src.integrated_server`로 진행합니다.

### 빌드 및 배포
1. 가상환경 생성:
   ```bash
   python -m venv venv
   ```
2. 가상환경 활성화 후 의존성 설치 (Windows PowerShell):
   ```bash
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
3. 실행 스크립트 테스트

포터블 배포본에는 수정된 `src/`와 필요한 프론트엔드 파일을 반영하고 내장 Python으로 검증합니다.
기존 측정 데이터와 내장 런타임은 보존하며, 실행 중인 서버는 업데이트 후 재시작해야 합니다.
측정 CSV, 통합 상태 파일, 로그, 가상환경, `update_backups/`는 Git 추적 대상에서 제외합니다.

## 라이선스

프로젝트 내부 사용을 위한 전용 소프트웨어입니다.

## 지원

문제가 발생하면 다음을 확인하세요:
1. `inspector.log` 파일
2. 서버 콘솔 출력
3. 브라우저 개발자 도구 (F12)

기술 지원: 시스템 관리자에게 문의
