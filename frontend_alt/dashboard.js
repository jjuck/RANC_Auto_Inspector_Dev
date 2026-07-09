// RANC Auto Inspector Dashboard - JavaScript Logic
// 주요 함수: updateDashboard(data)

// ==================== 전역 상태 ====================
let history = [];
let selectedOutputGroup = 'X';
const NOMINAL_DBFS = -24;
const DBFS_TOLERANCE = 1.5;
const LIMITS = {
    vrms_min: Math.pow(10, (NOMINAL_DBFS - DBFS_TOLERANCE) / 20),
    vrms_max: Math.pow(10, (NOMINAL_DBFS + DBFS_TOLERANCE) / 20)
};

// 파생된 Limit 계산
function calculateDerivedLimits() {
    return {
        vrms: { min: LIMITS.vrms_min, max: LIMITS.vrms_max },
        lsb: {
            min: LIMITS.vrms_min * 8192,
            max: LIMITS.vrms_max * 8192
        },
        sens: {
            min: 20 * Math.log10(LIMITS.vrms_min),
            max: 20 * Math.log10(LIMITS.vrms_max)
        },
        g: {
            min: LIMITS.vrms_min * 16,
            max: LIMITS.vrms_max * 16
        }
    };
}

// ==================== DOM 요소 참조 ====================
const elements = {
    // 헤더 정보
    currentFilename: document.getElementById('current-filename'),
    currentTimestamp: document.getElementById('current-timestamp'),
    outputGroupSelect: document.getElementById('output-group-select'),
    
    // 판정 영역
    judgementBadge: document.getElementById('judgement-badge'),
    judgementText: document.querySelector('#judgement-badge .judgement-badge'),
    judgementVrms: document.getElementById('judgement-vrms'),
    judgementLsb: document.getElementById('judgement-lsb'),
    judgementLsbRange: document.getElementById('judgement-lsb-range'),
    
    // 데이터 카드
    cardVrms: document.getElementById('card-vrms'),
    cardLsb: document.getElementById('card-lsb'),
    cardSens: document.getElementById('card-sens'),
    cardG: document.getElementById('card-g'),
    cardNoiseLevel: document.getElementById('card-noise-level'),
    cardNoiseChannel: document.getElementById('card-noise-channel'),
    
    // Limit 표시 요소
    limitVrms: document.getElementById('limit-vrms'),
    limitLsb: document.getElementById('limit-lsb'),
    limitSens: document.getElementById('limit-sens'),
    limitG: document.getElementById('limit-g'),
    
    // 히스토리 테이블
    historyBody: document.getElementById('history-body'),
    historyEmpty: document.getElementById('history-empty'),
    
    // 버튼
    clearHistoryBtn: document.getElementById('clear-history')
};

// ==================== 유틸리티 함수 ====================

/**
 * 현재 시간을 포맷팅된 문자열로 반환
 */
function getCurrentTimestamp() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds} KST`;
}

/**
 * 파일명 생성기 (시뮬레이션용)
 */
function generateFilename() {
    const prefixes = ['96398XGR500X', '96398XGR501X', '96399XGR500X'];
    const date = new Date();
    const dateStr = `${date.getFullYear().toString().slice(2)}${String(date.getMonth() + 1).padStart(2, '0')}${String(date.getDate()).padStart(2, '0')}`;
    const randomNum = Math.floor(Math.random() * 100).toString().padStart(2, '0');
    const prefix = prefixes[Math.floor(Math.random() * prefixes.length)];
    return `${prefix}${dateStr}X${randomNum}.csv`;
}

/**
 * Vrms 값으로부터 LSB, SENS, g 계산
 */
function calculateValues(vrms) {
    const lsb = vrms * 8192;
    const sens = vrms > 0 ? 20 * Math.log10(vrms) : -Infinity;
    const g = vrms * 16;
    return { lsb, sens, g };
}

/**
 * Vrms 값으로 판정 (PASS/FAIL)
 */
function judgeVrms(vrms) {
    return (vrms >= LIMITS.vrms_min && vrms <= LIMITS.vrms_max) ? 'PASS' : 'FAIL';
}

/**
 * 숫자를 지정된 소수점 자리로 포맷팅
 */
function formatNumber(num, decimals = 4) {
    if (typeof num !== 'number' || isNaN(num)) return 'N/A';
    return num.toFixed(decimals);
}

function optionalNumber(value) {
    if (value === null || value === undefined || value === '') return NaN;
    const number = Number(value);
    return Number.isFinite(number) ? number : NaN;
}

function getNoiseLevel(values) {
    return optionalNumber(values?.noise_level ?? values?.noiseLevel);
}

function getActiveChannel(values) {
    return values?.active_channel || values?.activeChannel || 'N/A';
}

// ==================== 핵심 함수: updateDashboard ====================

/**
 * 대시보드 전체를 새로운 데이터로 업데이트
 * @param {Object} data - 업데이트할 데이터 객체
 *   {
 *     timestamp: "2026-03-05 14:30:25",
 *     filename: "96398XGR500X251215X052.csv",
 *     judgement: "PASS",
 *     values: { vrms: 0.0625, lsb: 512.0, sens: -24.08, g: 1.0, noise_level: 0.000177203, active_channel: "Ch1" },
 *     limits: { vrms_min: 0.0531, vrms_max: 0.0750 }
 *   }
 */
function updateDashboard(data) {
    console.log('대시보드 업데이트:', data);
    
    // 1. 헤더 정보 업데이트
    if (elements.currentFilename) {
        elements.currentFilename.textContent = data.filename;
    }
    if (elements.currentTimestamp) {
        elements.currentTimestamp.textContent = data.timestamp;
    }
    
    // 2. 판정 영역 업데이트
    updateJudgementBadge(data.judgement, data.values.vrms);
    
    // 3. 데이터 카드 업데이트
    updateValueCards(data.values);
    
    // 4. Limit 표시 업데이트
    updateLimitDisplays();
    
    // 5. 히스토리 테이블에 추가
    addToHistoryTable(data);
    
    // 6. 시각적 피드백
    highlightNewData();
}

/**
 * 판정 배지 업데이트
 */
function updateJudgementBadge(judgement, vrms) {
    const badge = elements.judgementBadge;
    const textEl = elements.judgementText;
    
    // 클래스 및 스타일 업데이트
    badge.classList.remove('pulse-pass', 'pulse-fail');
    if (judgement === 'PASS') {
        badge.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
        badge.classList.add('pulse-pass');
        textEl.innerHTML = 'PASS';
    } else {
        badge.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
        badge.classList.add('pulse-fail');
        textEl.innerHTML = 'FAIL';
    }
    
    // LSB 값 계산 및 업데이트
    const lsb = vrms * 8192;
    elements.judgementLsb.textContent = formatNumber(lsb, 2);
    
    // LSB 범위 업데이트
    const limits = calculateDerivedLimits();
    elements.judgementLsbRange.textContent = `${formatNumber(limits.lsb.min, 1)} ~ ${formatNumber(limits.lsb.max, 1)}`;
}

/**
 * 데이터 카드 업데이트
 */
function updateValueCards(values) {
    elements.cardVrms.textContent = formatNumber(values.vrms, 6);
    elements.cardLsb.textContent = formatNumber(values.lsb, 2);
    elements.cardSens.textContent = formatNumber(values.sens, 2);
    elements.cardG.textContent = formatNumber(values.g, 3);
    elements.cardNoiseLevel.textContent = formatNumber(getNoiseLevel(values), 9);
    elements.cardNoiseChannel.textContent = getActiveChannel(values);
}

/**
 * Limit 표시 업데이트
 */
function updateLimitDisplays() {
    const limits = calculateDerivedLimits();
    elements.limitVrms.textContent = `${formatNumber(limits.vrms.min, 4)} ~ ${formatNumber(limits.vrms.max, 4)}`;
    elements.limitLsb.textContent = `${formatNumber(limits.lsb.min, 2)} ~ ${formatNumber(limits.lsb.max, 2)}`;
    elements.limitSens.textContent = `${formatNumber(limits.sens.min, 2)} ~ ${formatNumber(limits.sens.max, 2)}`;
    elements.limitG.textContent = `${formatNumber(limits.g.min, 4)} ~ ${formatNumber(limits.g.max, 4)}`;
}

/**
 * 히스토리 테이블에 새 행 추가
 */
function addToHistoryTable(data) {
    // 빈 상태 메시지 숨기기
    elements.historyEmpty.style.display = 'none';
    
    // 새 행 생성
    const row = document.createElement('tr');
    row.className = 'fade-in';
    row.innerHTML = `
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 mono">${data.timestamp}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">${data.filename}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 mono">${formatNumber(data.values.vrms, 6)}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 mono">${formatNumber(data.values.lsb, 2)}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 mono">${formatNumber(getNoiseLevel(data.values), 9)}</td>
        <td class="px-6 py-4 whitespace-nowrap">
            <span class="px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full
                ${data.judgement === 'PASS' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
                ${data.judgement}
            </span>
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
            <button class="text-blue-600 hover:text-blue-900 mr-3" onclick="replayData(this)">
                <i class="fas fa-redo"></i>
            </button>
            <button class="text-red-600 hover:text-red-900" onclick="deleteRow(this)">
                <i class="fas fa-trash"></i>
            </button>
        </td>
    `;
    
    // 테이블 상단에 추가
    elements.historyBody.insertBefore(row, elements.historyBody.firstChild);
    
    // 히스토리 배열에 저장 (최대 20개)
    history.unshift(data);
    if (history.length > 20) {
        history.pop();
        // DOM에서도 마지막 행 제거
        if (elements.historyBody.children.length > 20) {
            elements.historyBody.removeChild(elements.historyBody.lastChild);
        }
    }
}

/**
 * 새 데이터 추가 시 시각적 강조 효과
 */
function highlightNewData() {
    // 카드에 강조 효과
    const cards = document.querySelectorAll('[id^="card-"]');
    cards.forEach(card => {
        card.classList.add('text-blue-600');
        setTimeout(() => {
            card.classList.remove('text-blue-600');
        }, 1000);
    });
    
    // 판정 배지에 펄스 효과 강화
    const badge = elements.judgementBadge;
    badge.style.transform = 'scale(1.02)';
    setTimeout(() => {
        badge.style.transform = 'scale(1)';
    }, 300);
}

// ==================== 시뮬레이션 및 테스트 기능 ====================

/**
 * 랜덤 데이터 생성 (시뮬레이션용)
 */
function generateRandomData() {
    const vrms = Math.random() * 0.1; // 0 ~ 0.1 사이 랜덤
    const { lsb, sens, g } = calculateValues(vrms);
    const judgement = judgeVrms(vrms);
    const active_channel = Math.random() > 0.5 ? 'Ch1' : 'Ch2';
    const noise_level = (0.001 + Math.random() * 0.002) * 0.1;
    
    return {
        timestamp: getCurrentTimestamp(),
        filename: generateFilename(),
        judgement: judgement,
        values: { vrms, lsb, sens, g, noise_level, active_channel },
        limits: LIMITS
    };
}

/**
 * 히스토리 테이블 행 삭제
 */
function deleteRow(button) {
    const row = button.closest('tr');
    row.style.opacity = '0';
    row.style.transform = 'translateX(20px)';
    row.style.transition = 'all 0.3s ease';
    
    setTimeout(() => {
        row.remove();
        // 테이블이 비었으면 빈 상태 메시지 표시
        if (elements.historyBody.children.length === 0) {
            elements.historyEmpty.style.display = 'block';
        }
    }, 300);
}

/**
 * 히스토리 데이터 재생 (재적용)
 */
function replayData(button) {
    const row = button.closest('tr');
    const filename = row.children[1].textContent;
    const vrms = parseFloat(row.children[2].textContent);
    
    // 해당 데이터 찾기
    const originalData = history.find(item => item.filename === filename);
    if (originalData) {
        // 데이터 재적용
        updateDashboard({
            ...originalData,
            timestamp: getCurrentTimestamp() // 현재 시간으로 업데이트
        });
        
        // 버튼 피드백
        button.innerHTML = '<i class="fas fa-check text-green-600"></i>';
        setTimeout(() => {
            button.innerHTML = '<i class="fas fa-redo"></i>';
        }, 1000);
    }
}

/**
 * 히스토리 테이블 전체 지우기
 */
function clearHistory() {
    elements.historyBody.innerHTML = '';
    elements.historyEmpty.style.display = 'block';
    history = [];
    
    // 버튼 피드백
    elements.clearHistoryBtn.innerHTML = '<i class="fas fa-check mr-2"></i>기록 삭제됨';
    setTimeout(() => {
        elements.clearHistoryBtn.innerHTML = '<i class="fas fa-trash-alt mr-2"></i>기록 지우기';
    }, 1500);
}

// ==================== 초기화 ====================

/**
 * 초기 더미 데이터로 대시보드 설정
 */
function initializeDashboard() {
    const initialData = {
        timestamp: getCurrentTimestamp(),
        filename: "96398XGR500X251215X052.csv",
        judgement: "PASS",
        values: { vrms: 0.0625, lsb: 512.0, sens: -24.08, g: 1.0, noise_level: 0.000177202812042, active_channel: "Ch1" },
        limits: LIMITS
    };
    
    updateDashboard(initialData);
    updateLimitDisplays(); // 초기 Limit 표시 업데이트
    
    // 추가로 몇 개의 히스토리 데이터 생성
    for (let i = 0; i < 3; i++) {
        const pastData = generateRandomData();
        pastData.timestamp = new Date(Date.now() - (i + 1) * 60000).toISOString()
            .replace('T', ' ')
            .replace(/\..*/, '') + ' KST';
        addToHistoryTable(pastData);
    }
}

/**
 * 이벤트 리스너 등록
 */
function setupEventListeners() {
    if (elements.outputGroupSelect) {
        selectedOutputGroup = elements.outputGroupSelect.value;
        elements.outputGroupSelect.addEventListener('change', () => {
            selectedOutputGroup = elements.outputGroupSelect.value;
            sendOutputGroupSelection();
        });
    }
    
    // 히스토리 지우기 버튼
    elements.clearHistoryBtn.addEventListener('click', clearHistory);
    
    // 키보드 단축키
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            clearHistory();
        }
    });
    
    // 주기적 자동 시뮬레이션 (옵션)
    // setInterval(simulateNewData, 10000); // 10초마다 자동 업데이트
}

// ==================== 문서 로드 완료 시 실행 ====================

document.addEventListener('DOMContentLoaded', () => {
    console.log('RANC 대시보드 초기화 중...');
    
    // 글로벌 함수 노출 (HTML 인라인 이벤트에서 사용)
    window.replayData = replayData;
    window.deleteRow = deleteRow;
    
    initializeDashboard();
    setupEventListeners();
    
    // WebSocket 연결 시작
    console.log('WebSocket 연결 시도 중...');
    connectWebSocket();
    
    console.log('대시보드 준비 완료');
});

// ==================== WebSocket 클라이언트 ====================

let websocket = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 10;
const RECONNECT_DELAY = 2000; // 2초

function sendOutputGroupSelection() {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) {
        return;
    }

    websocket.send(JSON.stringify({
        type: 'set_output_group',
        value: selectedOutputGroup
    }));
}

/**
 * WebSocket 연결 설정
 */
function connectWebSocket() {
    // 동적 WebSocket URL 생성: 현재 브라우저의 호스트와 포트 사용
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    try {
        websocket = new WebSocket(wsUrl);
        
        websocket.onopen = function(event) {
            console.log('WebSocket 연결 성공:', wsUrl);
            reconnectAttempts = 0;
            updateConnectionStatus(true);
            sendOutputGroupSelection();
        };
        
        websocket.onmessage = function(event) {
            try {
                const message = JSON.parse(event.data);
                console.log('WebSocket 메시지 수신:', message);
                
                if (message.type === 'new_result') {
                    // 백엔드에서 전송된 결과 데이터를 대시보드 형식으로 변환
                    const dashboardData = {
                        timestamp: message.data.timestamp,
                        filename: message.data.input_file,
                        judgement: message.data.judgement,
                        values: {
                            vrms: message.data.vrms,
                            lsb: message.data.lsb,
                            sens: message.data.sens,
                            g: message.data.g,
                            noise_level: message.data.noise_level,
                            active_channel: message.data.active_channel,
                            output_group: message.data.output_group
                        },
                        limits: {
                            vrms_min: message.data.lower_bound,
                            vrms_max: message.data.upper_bound
                        }
                    };
                    
                    // 대시보드 업데이트
                    updateDashboard(dashboardData);
                } else if (message.type === 'output_group_status') {
                    selectedOutputGroup = message.data?.output_group || selectedOutputGroup;
                    if (elements.outputGroupSelect) {
                        elements.outputGroupSelect.value = selectedOutputGroup;
                    }
                } else if (message.type === 'system_status') {
                    console.log('시스템 상태 업데이트:', message.data);
                    // 필요 시 시스템 상태 UI 업데이트 구현
                }
            } catch (error) {
                console.error('WebSocket 메시지 처리 오류:', error);
            }
        };
        
        websocket.onclose = function(event) {
            console.log('WebSocket 연결 종료:', event.code, event.reason);
            updateConnectionStatus(false);
            
            // 자동 재연결 시도
            if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                reconnectAttempts++;
                console.log(`재연결 시도 중... (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);
                setTimeout(connectWebSocket, RECONNECT_DELAY);
            } else {
                console.error('최대 재연결 시도 횟수 초과. 수동 재연결 필요.');
            }
        };
        
        websocket.onerror = function(error) {
            console.error('WebSocket 오류:', error);
            updateConnectionStatus(false);
        };
        
    } catch (error) {
        console.error('WebSocket 연결 실패:', error);
        updateConnectionStatus(false);
        
        // 재연결 시도
        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            reconnectAttempts++;
            console.log(`재연결 시도 중... (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);
            setTimeout(connectWebSocket, RECONNECT_DELAY);
        }
    }
}

/**
 * 연결 상태 UI 업데이트
 */
function updateConnectionStatus(connected) {
    const statusIndicator = document.getElementById('connection-status');
    if (!statusIndicator) {
        // 상태 표시기가 없으면 생성
        const header = document.querySelector('header .container > div');
        if (header) {
            const statusDiv = document.createElement('div');
            statusDiv.id = 'connection-status';
            statusDiv.className = 'px-2 py-1 rounded-full text-xs font-medium whitespace-nowrap';
            statusDiv.textContent = connected ? '실시간 연결됨' : '연결 끊김';
            statusDiv.style.backgroundColor = connected ? '#10b981' : '#ef4444';
            statusDiv.style.color = 'white';
            header.appendChild(statusDiv);
        }
        return;
    }
    
    statusIndicator.textContent = connected ? '실시간 연결됨' : '연결 끊김';
    statusIndicator.style.backgroundColor = connected ? '#10b981' : '#ef4444';
}

/**
 * WebSocket 연결 수동 재시작
 */
function reconnectWebSocket() {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.close();
    }
    reconnectAttempts = 0;
    connectWebSocket();
}

// ==================== 글로벌 함수 (외부에서 호출용) ====================

/**
 * 외부에서 호출 가능한 대시보드 업데이트 함수
 * 예: WebSocket 메시지 수신 시 updateDashboard(data) 호출
 */
window.updateDashboard = updateDashboard;

/**
 * WebSocket 연결 재시작 함수 (글로벌 노출)
 */
window.reconnectWebSocket = reconnectWebSocket;

/**
 * 외부에서 대시보드 상태 확인용
 */
window.getDashboardState = () => ({
    historyCount: history.length,
    currentJudgement: elements.judgementText?.textContent || 'UNKNOWN',
    lastUpdate: elements.currentTimestamp?.textContent || '',
    selectedOutputGroup,
    websocketConnected: websocket ? websocket.readyState === WebSocket.OPEN : false
});
