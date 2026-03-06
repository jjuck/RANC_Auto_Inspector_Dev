# RANC Auto Inspector - 프론트엔드 대시보드

로컬 데몬(CSV 처리 및 PASS/FAIL 판정)의 결과를 실시간으로 보여주는 대시보드 UI 프로토타입입니다.

## 기능 요약

- **모던 화이트 테마**: 옅은 회색 배경, 순백색 카드 컴포넌트, 연한 테두리와 그림자
- **메인 판정 영역**: PASS(초록색)/FAIL(빨간색) 상태가 매우 크고 직관적으로 표시
- **데이터 카드 레이아웃**: Vrms, LSB, SENS, g 값을 개별 카드 형태로 배치
- **숫자 가독성**: Monospace 폰트 적용으로 값 변경 시 레이아웃 유지
- **헤더 정보**: 최근 검사 파일명과 검사 시간 표시
- **히스토리 테이블**: 최근 검사 기록 확인 가능
- **실시간 시뮬레이션**: 버튼 클릭 또는 R 키로 새 데이터 생성 가능

## 기술 스택

- HTML5 (시맨틱 마크업)
- Tailwind CSS v3.4+ (CDN 방식)
- 순수 JavaScript (ES6+)
- Font Awesome Icons (CDN)
- Google Fonts (Roboto Mono)

## 파일 구조

```
frontend/
├── index.html          # 메인 대시보드 페이지
├── dashboard.js        # 대시보드 로직 및 데이터 업데이트 함수
└── README.md           # 이 문서
```

## 사용 방법

### 1. 브라우저에서 직접 열기

`index.html` 파일을 더블클릭하거나 브라우저에 드래그&드롭하면 바로 실행됩니다.

### 2. 로컬 서버로 실행 (권장)

Python으로 간단한 HTTP 서버를 실행할 수 있습니다:

```bash
# Python 3
python -m http.server 8080

# 또는 Python 2
python -m SimpleHTTPServer 8080
```

그 후 브라우저에서 `http://localhost:8080/frontend/`로 접속합니다.

### 3. VSCode Live Server 확장 사용

VSCode에서 "Live Server" 확장을 설치하고 `index.html`을 마우스 우클릭 → "Open with Live Server"를 선택합니다.

## 대시보드 기능 설명

### 주요 컴포넌트

1. **헤더 영역**
   - 프로젝트 제목 및 설명
   - 최근 검사 정보 (파일명, 시간)
   - "새 데이터 시뮬레이션" 버튼

2. **메인 판정 영역**
   - PASS/FAIL 상태가 대형 배지로 표시
   - Vrms 값과 허용 기준 범위 표시
   - 상태에 따라 초록색(PASS) 또는 빨간색(FAIL) 배경

3. **데이터 카드 그리드 (4개)**
   - **Vrms**: 전압 RMS 값 (허용 기준: 0.0572 ~ 0.0699)
   - **LSB**: Vrms × 8192 변환값
   - **SENS**: 20 × log₁₀(Vrms) 변환값
   - **g**: Vrms × 16 변환값

4. **히스토리 테이블**
   - 최근 20개 검사 기록 표시
   - 각 행에서 데이터 재생 또는 삭제 가능
   - "기록 지우기" 버튼으로 전체 삭제

### 상호작용 방법

- **새 데이터 시뮬레이션**: 상단 버튼 클릭 또는 키보드 `R` 키
- **히스토리 재생**: 테이블 행의 🔄 아이콘 클릭
- **히스토리 삭제**: 테이블 행의 🗑️ 아이콘 클릭
- **전체 기록 지우기**: 테이블 상단의 "기록 지우기" 버튼
- **키보드 단축키**:
  - `R`: 새 데이터 생성
  - `Escape`: 히스토리 전체 지우기

### 프로그래밍 인터페이스

대시보드는 `updateDashboard(data)` 함수를 통해 외부에서 데이터를 주입할 수 있습니다:

```javascript
// 데이터 형식 예시
const sampleData = {
    timestamp: "2026-03-05 14:30:25 KST",
    filename: "96398XGR500X251215X052.csv",
    judgement: "PASS", // 또는 "FAIL"
    values: {
        vrms: 0.0625,
        lsb: 512.0,
        sens: -24.08,
        g: 1.0
    },
    limits: {
        vrms_min: 0.0572,
        vrms_max: 0.0699
    }
};

// 대시보드 업데이트
window.updateDashboard(sampleData);
```

이 함수는 WebSocket, REST API, 또는 기타 실시간 통신 방식과 연동할 수 있습니다.

## 백엔드 연동 준비사항

이 프로토타입은 정적 UI이지만, 다음과 같은 방식으로 백엔드와 연동할 수 있습니다:

### 1. WebSocket 연동
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    updateDashboard(data);
};
```

### 2. REST API 폴링
```javascript
setInterval(async () => {
    const response = await fetch('/api/latest-inspection');
    const data = await response.json();
    updateDashboard(data);
}, 5000); // 5초마다 폴링
```

### 3. Server-Sent Events (SSE)
```javascript
const eventSource = new EventSource('/api/events');
eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    updateDashboard(data);
};
```

## 디자인 커스터마이징

### 색상 테마 변경

`index.html`의 CSS 변수를 수정하여 색상을 변경할 수 있습니다:

```css
:root {
    --primary-bg: #f8fafc;
    --card-bg: #ffffff;
    --pass-gradient: linear-gradient(135deg, #10b981 0%, #059669 100%);
    --fail-gradient: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
}
```

### 반응형 디자인

Tailwind CSS의 반응형 클래스를 활용하여 다양한 화면 크기에 대응합니다:
- 데스크톱 (≥1024px): 4열 그리드
- 태블릿 (768px~1023px): 2열 그리드
- 모바일 (≤767px): 1열 그리드

## 향후 개선 사항

1. **백엔드 연동**: WebSocket을 통한 실시간 데이터 스트리밍
2. **차트 시각화**: Vrms 값의 변화를 라인 차트로 표시
3. **알림 시스템**: 판정 결과에 따른 사운드/브라우저 알림
4. **다국어 지원**: 한국어/영어 전환 기능
5. **다크 모드**: 어두운 테마 지원
6. **데이터 내보내기**: 히스토리 데이터 CSV/Excel 다운로드

## 문제 해결

### 대시보드가 로드되지 않을 때
1. 인터넷 연결 확인 (Tailwind, Font Awesome CDN 필요)
2. 브라우저 콘솔(F12)에서 오류 확인
3. `dashboard.js` 파일이 `index.html`과 같은 디렉토리에 있는지 확인

### 시뮬레이션 버튼이 작동하지 않을 때
1. JavaScript가 활성화되었는지 확인
2. 브라우저 캐시 지우기 및 새로고침

## 라이선스

이 프로젝트는 RANC Auto Inspector 시스템의 일부입니다.