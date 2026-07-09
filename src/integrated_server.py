#!/usr/bin/env python3
"""
RANC Auto Inspector 통합 서버
FastAPI 기반 단일 진입점 서버:
- WebSocket 실시간 통신 (/ws)
- 프론트엔드 정적 파일 서빙 (frontend/)
- 백엔드 데몬 자동 실행
"""

import asyncio
import json
import logging
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Set, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

# 프로젝트 모듈 임포트 (전체 상단에 명시)
from src.csv_processor import CSVProcessor
from src.calculator import convert_dbfs
from src.judge import judge_vrms
from src.result_writer import DEFAULT_OUTPUT_GROUP, ResultWriter
from src.file_watcher import FileWatcher

# 프로젝트 루트 디렉토리 계산
PROJECT_ROOT = Path(__file__).parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
ALT_FRONTEND_DIR = PROJECT_ROOT / "frontend_alt"
DATA_DIR = PROJECT_ROOT / "data"
INPUT_DIR = DATA_DIR / "input_logs"
OUTPUT_DIR = DATA_DIR / "output_results"

# 디렉토리 생성 (존재하지 않으면)
DATA_DIR.mkdir(parents=True, exist_ok=True)
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
ALT_FRONTEND_DIR.mkdir(parents=True, exist_ok=True)

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / 'inspector.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket 연결 관리자 (FastAPI 통합)"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        
    async def connect(self, websocket: WebSocket):
        """클라이언트 연결 수락"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket 클라이언트 연결됨. 총 연결: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        """클라이언트 연결 해제"""
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket 클라이언트 연결 해제됨. 남은 연결: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        """클라이언트 연결 해제"""
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket 클라이언트 연결 해제됨. 남은 연결: {len(self.active_connections)}")
        
    async def broadcast_result(self, result_data: Dict[str, Any]):
        """모든 연결된 클라이언트에 결과 브로드캐스트"""
        if not self.active_connections:
            return
            
        message = json.dumps({
            "type": "new_result",
            "data": result_data
        })
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"클라이언트에 메시지 전송 중 오류: {e}")
                disconnected.append(connection)
                
        for connection in disconnected:
            self.disconnect(connection)
            
        if self.active_connections:
            logger.debug(f"결과 브로드캐스트 완료: {len(self.active_connections)}개 클라이언트")


class AutoInspectorDaemon:
    """자동 감시 및 판정 데몬 클래스 (통합 서버용)"""
    
    def __init__(
        self,
        input_dir: Path = INPUT_DIR,
        output_dir: Path = OUTPUT_DIR,
        websocket_manager: Optional[WebSocketManager] = None
    ):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.websocket_manager = websocket_manager or WebSocketManager()
        self.processor = CSVProcessor()
        self.writer = ResultWriter(self.output_dir)
        self.current_output_group = DEFAULT_OUTPUT_GROUP
        self.watcher: Optional[FileWatcher] = None
        self.is_running = False
        self.processed_files: Dict[str, float] = {}  # 파일명: 처리 시간 (debounce용)
        self.debounce_seconds = 2.0  # 2초 내 중복 처리 방지
        
        logger.info(f"데몬 초기화: 입력 디렉토리={self.input_dir}, 출력 디렉토리={self.output_dir}")

    def set_output_group(self, group: str) -> str:
        """결과 저장 라인 그룹을 X/Y/Z 중 하나로 설정"""
        self.current_output_group = self.writer.normalize_output_group(group)
        logger.info(f"결과 저장 그룹 변경: {self.current_output_group}")
        return self.current_output_group
        
    def _should_process_file(self, file_path: Path) -> bool:
        """파일 중복 처리 방지 (debounce)"""
        filename = file_path.name
        current_time = time.time()
        
        if filename in self.processed_files:
            last_processed = self.processed_files[filename]
            if current_time - last_processed < self.debounce_seconds:
                logger.debug(f"중복 파일 처리 방지: {filename} (최근 처리: {current_time - last_processed:.2f}초 전)")
                return False
        
        self.processed_files[filename] = current_time
        return True
        
    def _handle_new_file(self, file_path: Path):
        """새 파일 생성 이벤트 핸들러"""
        # Debounce 체크
        if not self._should_process_file(file_path):
            return
            
        try:
            logger.info(f"새 파일 감지: {file_path.name}")
            
            # 1. CSV 파일에서 RMS Level dBFS 값과 활성 채널 추출
            active_dbfs = self.processor.extract_active_dbfs_from_csv(file_path)
            
            if active_dbfs is None:
                logger.error(f"dBFS 값 추출 실패: {file_path.name}")
                return

            dbfs_value = active_dbfs.value
                
            logger.info(f"dBFS 값 추출 성공: {active_dbfs.channel}={dbfs_value:.6f}")

            # Noise Level은 RMS Level에서 선택된 활성 채널과 같은 채널 값을 사용합니다.
            noise_level = self.processor.extract_noise_level_from_csv(file_path, active_dbfs.channel)
            
            # 2. dBFS를 기존 Vrms 기반 계산 값으로 변환
            converted = convert_dbfs(dbfs_value)
            vrms_value = converted['original_vrms']
            
            # 3. 판정
            judgement = judge_vrms(vrms_value)
            
            # 4. 결과 데이터 준비
            result = {
                'timestamp': datetime.now().isoformat(),
                'input_file': file_path.name,
                'output_group': self.current_output_group,
                'dbfs': dbfs_value,
                'active_channel': active_dbfs.channel,
                'noise_level': noise_level,
                'vrms': vrms_value,
                'lsb': converted['lsb'],
                'sens': converted['sens'],
                'g': converted['g'],
                'judgement': judgement['result'],
                'lower_bound': judgement['lower_bound'],
                'upper_bound': judgement['upper_bound'],
                'is_within_range': judgement['is_within_range']
            }
            
            # 5. 터미널 출력
            self._print_result(result)
            
            # 6. 파일 저장
            save_success = self.writer.save_result(result)
            if save_success:
                logger.info(f"결과 저장 완료: {file_path.name}")
            else:
                logger.error(f"결과 저장 실패: {file_path.name}")
                
            logger.info(f"처리 완료: {file_path.name} -> {judgement['result']}")
            
            # 7. WebSocket 브로드캐스트 (이벤트 루프가 있으면 예약)
            if hasattr(self, '_main_event_loop') and self._main_event_loop is not None:
                asyncio.run_coroutine_threadsafe(
                    self.websocket_manager.broadcast_result(result),
                    self._main_event_loop
                )
                logger.debug(f"WebSocket 브로드캐스트 예약됨: {file_path.name}")
            else:
                logger.warning("메인 이벤트 루프가 없어 WebSocket 브로드캐스트를 할 수 없습니다.")
                
        except Exception as e:
            logger.error(f"파일 처리 중 오류: {file_path.name}, 오류: {e}")
            
    def _print_result(self, result: dict):
        """결과를 터미널에 출력"""
        print("\n" + "="*60)
        print(f"[RANC Auto Inspector] 처리 완료")
        print("="*60)
        print(f"  입력 파일: {result['input_file']}")
        print(f"  저장 그룹: {result.get('output_group', DEFAULT_OUTPUT_GROUP)}")
        print(f"  처리 시간: {result['timestamp']}")
        if 'dbfs' in result:
            print(f"  dBFS 값: {result['dbfs']:.6f}")
        if result.get('noise_level') is not None:
            print(f"  Noise Level: {result['noise_level']:.15f}")
        print(f"  Vrms 값: {result['vrms']:.6f}")
        print(f"  LSB: {result['lsb']:.2f}")
        print(f"  SENS: {result['sens']:.2f} dB")
        print(f"  g: {result['g']:.6f}")
        print(f"  판정: {result['judgement']}")
        print(f"  허용 범위: {result['lower_bound']:.6f} ~ {result['upper_bound']:.6f}")
        print(f"  범위 내 여부: {'예' if result['is_within_range'] else '아니오'}")
        print("="*60)
        
    def start(self, main_event_loop: Optional[asyncio.AbstractEventLoop] = None):
        """데몬 시작 (메인 이벤트 루프 전달)"""
        if self.is_running:
            logger.warning("데몬이 이미 실행 중입니다.")
            return
            
        self._main_event_loop = main_event_loop
        
        self.watcher = FileWatcher(
            watch_dir=self.input_dir,
            on_file_created=self._handle_new_file
        )
        
        # 파일 감시기 시작 (별도 스레드)
        self.watcher_thread = threading.Thread(target=self.watcher.start, daemon=True)
        self.watcher_thread.start()
        self.is_running = True
        
        logger.info("데몬 시작됨 - 파일 감시 활성화")
        
    def stop(self):
        """데몬 중지"""
        if self.watcher:
            self.watcher.stop()
        self.is_running = False
        logger.info("데몬 중지됨")


# FastAPI 앱 상태 관리
class AppState:
    """애플리케이션 상태 컨테이너 (의존성 주입)"""
    def __init__(self):
        self.websocket_manager: Optional[WebSocketManager] = None
        self.daemon: Optional[AutoInspectorDaemon] = None
        self.main_event_loop: Optional[asyncio.AbstractEventLoop] = None


# 전역 앱 상태
app_state = AppState()


# Lifespan 컨텍스트 매니저 (FastAPI 최신 문법)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작/종료 이벤트 처리 (lifespan)"""
    # 서버 시작
    logger.info("="*60)
    logger.info("RANC Auto Inspector 통합 서버 시작")
    logger.info(f"프로젝트 루트: {PROJECT_ROOT}")
    logger.info(f"입력 디렉토리: {INPUT_DIR}")
    logger.info(f"출력 디렉토리: {OUTPUT_DIR}")
    logger.info(f"프론트엔드 디렉토리: {FRONTEND_DIR}")
    logger.info("="*60)
    logger.info("서버 정보:")
    logger.info("  HTTP 서버: http://localhost:8000")
    logger.info("  WebSocket: ws://localhost:8000/ws")
    logger.info("  건강 상태: http://localhost:8000/health")
    logger.info("="*60)
    
    # 메인 이벤트 루프 저장
    app_state.main_event_loop = asyncio.get_running_loop()
    logger.info(f"메인 이벤트 루프 저장됨")
    
    # WebSocket 관리자 생성
    app_state.websocket_manager = WebSocketManager()
    
    # 데몬 생성 및 시작
    app_state.daemon = AutoInspectorDaemon(
        input_dir=INPUT_DIR,
        output_dir=OUTPUT_DIR,
        websocket_manager=app_state.websocket_manager
    )
    app_state.daemon.start(main_event_loop=app_state.main_event_loop)
    
    # 기존 통계 출력
    stats = app_state.daemon.writer.get_statistics()
    logger.info(f"현재까지 처리 통계: 총 {stats['total']}개, "
                f"PASS {stats['pass']}개, FAIL {stats['fail']}개 "
                f"(합격률 {stats['pass_rate']:.1f}%)")
    
    logger.info("데몬 실행 중... 새 CSV 파일을 생성하면 자동 처리됩니다.")
    logger.info("종료하려면 Ctrl+C를 누르세요.")
    
    yield  # 서버 실행 중
    
    # 서버 종료
    logger.info("서버 종료 중...")
    if app_state.daemon:
        app_state.daemon.stop()
    logger.info("서버 종료 완료")


# FastAPI 앱 생성 (lifespan 포함)
app = FastAPI(
    title="RANC Auto Inspector",
    description="실시간 CSV 처리 및 대시보드 시스템",
    version="1.0.0",
    lifespan=lifespan
)


# FastAPI 라우트 정의
def serve_frontend_file(frontend_dir: Path, filename: str) -> FileResponse | HTMLResponse:
    """지정된 프론트엔드 디렉토리에서 파일 서빙"""
    target_path = frontend_dir / filename
    if not target_path.exists():
        return HTMLResponse(content=f"<h1>{filename} 파일을 찾을 수 없습니다.</h1>", status_code=404)
    response = FileResponse(target_path)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """기본 대시보드 메인 페이지 서빙"""
    return serve_frontend_file(FRONTEND_DIR, "index.html")


@app.get("/alt", response_class=HTMLResponse)
async def serve_alt_index():
    """대체 디자인 대시보드 메인 페이지 서빙"""
    return serve_frontend_file(ALT_FRONTEND_DIR, "index.html")


@app.get("/dashboard.js")
async def serve_dashboard_js():
    """기본 대시보드 JavaScript 파일 서빙"""
    return serve_frontend_file(FRONTEND_DIR, "dashboard.js")


@app.get("/alt/dashboard.js")
async def serve_alt_dashboard_js():
    """대체 디자인 대시보드 JavaScript 파일 서빙"""
    return serve_frontend_file(ALT_FRONTEND_DIR, "dashboard.js")


@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    daemon_running = app_state.daemon.is_running if app_state.daemon else False
    ws_clients = len(app_state.websocket_manager.active_connections) if app_state.websocket_manager else 0
    
    return {
        "status": "healthy",
        "service": "RANC Auto Inspector",
        "version": "1.0.0",
        "websocket_clients": len(app_state.websocket_manager.active_connections) if app_state.websocket_manager else 0,
        "daemon_running": app_state.daemon.is_running if app_state.daemon else False
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 실시간 통신 엔드포인트"""
    if not app_state.websocket_manager:
        await websocket.close(code=1011, reason="Server not ready")
        return
        
    await app_state.websocket_manager.connect(websocket)
    try:
        # 클라이언트 메시지 수신 대기
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                logger.debug(f"클라이언트 메시지 수신: {message}")
                
                # 클라이언트 요청 처리 (예: 히스토리 요청)
                if message.get("type") == "set_output_group":
                    if not app_state.daemon:
                        await websocket.send_text(json.dumps({
                            "type": "output_group_status",
                            "data": {"ok": False, "output_group": DEFAULT_OUTPUT_GROUP}
                        }))
                        continue

                    output_group = app_state.daemon.set_output_group(message.get("value", DEFAULT_OUTPUT_GROUP))
                    await websocket.send_text(json.dumps({
                        "type": "output_group_status",
                        "data": {"ok": True, "output_group": output_group}
                    }))
                elif message.get("type") == "request_history":
                    # 히스토리 데이터 전송 로직은 향후 구현
                    pass
                    
            except json.JSONDecodeError:
                logger.warning(f"잘못된 JSON 메시지: {data}")
                
    except WebSocketDisconnect:
        logger.info("WebSocket 연결이 정상적으로 종료됨")
    except Exception as e:
        logger.error(f"WebSocket 통신 중 오류: {e}")
    finally:
        app_state.websocket_manager.disconnect(websocket)


# 정적 파일 서빙 (frontend/ 디렉토리 전체)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


def main():
    """메인 진입점"""
    # 배너 출력
    banner = """
    ========================================================
          RANC Auto Inspector 통합 서버 v1.0.0
          단일 진입점: HTTP + WebSocket + 데몬
    ========================================================
    """
    print(banner)
    
    # Uvicorn 서버 실행
    uvicorn.run(
        "src.integrated_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
