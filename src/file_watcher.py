"""
파일 시스템 감시 모듈 (watchdog 기반)
이벤트 기반으로 새 CSV 파일 생성 감지
"""

import time
import logging
from pathlib import Path
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

logger = logging.getLogger(__name__)


class CSVFileHandler(FileSystemEventHandler):
    """CSV 파일 생성 이벤트 핸들러"""
    
    def __init__(self, callback: Callable[[Path], None]):
        """
        Args:
            callback: 새 CSV 파일이 생성될 때 호출될 콜백 함수
                     (파일 경로를 Path 객체로 받음)
        """
        self.callback = callback
        super().__init__()
    
    def on_created(self, event: FileCreatedEvent):
        """
        파일 생성 이벤트 핸들러
        
        Args:
            event: FileCreatedEvent 객체
        """
        if not event.is_directory:
            file_path = Path(event.src_path)
            
            # CSV 파일만 처리
            if file_path.suffix.lower() == '.csv':
                logger.info(f"새 CSV 파일 감지: {file_path.name}")
                
                # 파일이 완전히 쓰여질 때까지 약간 대기 (옵션)
                time.sleep(0.1)
                
                # 콜백 호출
                try:
                    self.callback(file_path)
                except Exception as e:
                    logger.error(f"콜백 실행 중 오류: {file_path.name}, 오류: {e}")
            else:
                logger.debug(f"CSV가 아닌 파일 무시: {file_path.name}")


class FileWatcher:
    """파일 시스템 감시기 클래스"""
    
    def __init__(self, watch_dir: Path, on_file_created: Callable[[Path], None]):
        """
        Args:
            watch_dir: 감시할 디렉토리 경로 (Path 객체)
            on_file_created: 새 파일 생성 시 호출할 콜백 함수
        """
        self.watch_dir = watch_dir
        self.on_file_created = on_file_created
        self.observer = Observer()
        self.event_handler = CSVFileHandler(on_file_created)
        self.is_running = False
        
        # 디렉토리 존재 확인 및 생성
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"감시 디렉토리 설정: {self.watch_dir.absolute()}")
    
    def start(self):
        """감시 시작"""
        if self.is_running:
            logger.warning("이미 실행 중인 감시기입니다.")
            return
        
        try:
            self.observer.schedule(
                self.event_handler,
                str(self.watch_dir),
                recursive=False  # 하위 디렉토리 감시 안 함
            )
            self.observer.start()
            self.is_running = True
            logger.info(f"파일 감시 시작: {self.watch_dir.name}")
            
            # 메인 스레드 유지
            while self.is_running:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"감시기 시작 중 오류: {e}")
            raise
    
    def stop(self):
        """감시 중지"""
        if self.is_running:
            self.observer.stop()
            self.observer.join()
            self.is_running = False
            logger.info("파일 감시 중지")
    
    def restart(self):
        """감시 재시작"""
        self.stop()
        time.sleep(1)
        self.start()


def watch_directory_simple(watch_dir: str, callback: Callable[[Path], None]) -> Observer: # type: ignore
    """
    단순한 디렉토리 감시 함수 (빠른 시작용)
    
    Args:
        watch_dir: 감시할 디렉토리 경로 (문자열)
        callback: 새 파일 생성 시 호출할 콜백 함수
        
    Returns:
        Observer 객체 (나중에 중지할 때 사용)
    """
    watch_path = Path(watch_dir)
    watch_path.mkdir(parents=True, exist_ok=True)
    
    observer = Observer()
    event_handler = CSVFileHandler(callback)
    
    observer.schedule(event_handler, str(watch_path), recursive=False)
    observer.start()
    
    logger.info(f"단순 감시 시작: {watch_path.absolute()}")
    return observer


if __name__ == "__main__":
    # 모듈 테스트
    import sys
    import threading
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    def test_callback(file_path: Path):
        """테스트용 콜백 함수"""
        print(f"[테스트] 새 파일 처리: {file_path.name}")
        print(f"  전체 경로: {file_path}")
        print(f"  파일 크기: {file_path.stat().st_size if file_path.exists() else 'N/A'} 바이트")
    
    if len(sys.argv) > 1:
        watch_dir = Path(sys.argv[1])
    else:
        watch_dir = Path("data/input_logs")
    
    print(f"테스트 모드: {watch_dir.absolute()} 디렉토리 감시 중...")
    print("새 CSV 파일을 생성하면 콘솔에 메시지가 출력됩니다.")
    print("종료하려면 Ctrl+C를 누르세요.")
    
    try:
        watcher = FileWatcher(watch_dir, test_callback)
        
        # 별도 스레드에서 실행
        watcher_thread = threading.Thread(target=watcher.start)
        watcher_thread.daemon = True
        watcher_thread.start()
        
        # 메인 스레드 대기
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n테스트 종료")
    except Exception as e:
        print(f"테스트 중 오류: {e}")