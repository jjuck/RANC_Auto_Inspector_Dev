#!/usr/bin/env python3
"""
RANC Auto Inspector Daemon
디렉토리 감시 및 실시간 CSV 처리 데몬

기능:
1. data/input_logs/ 디렉토리를 이벤트 기반으로 감시
2. 새 CSV 파일이 생성되면 B열 4행(B4 셀)에서 Vrms 값 추출
3. 변환 계산: LSB = Vrms * 8192, SENS = 20 * log10(Vrms), g = Vrms * 16
4. 판정: Vrms가 (468.6 / 8192) ~ (572.7 / 8192) 사이면 PASS, 아니면 FAIL
5. 결과를 터미널에 출력하고 data/output_results/에 CSV로 누적 저장
"""

import time
import logging
import signal
import sys
from pathlib import Path
from datetime import datetime

from src.csv_processor import CSVProcessor
from src.calculator import convert_vrms
from src.judge import judge_vrms
from src.result_writer import ResultWriter
from src.file_watcher import FileWatcher


class AutoInspectorDaemon:
    """자동 감시 및 판정 데몬 클래스"""
    
    def __init__(self, input_dir: str = "data/input_logs", 
                 output_dir: str = "data/output_results"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        
        # 디렉토리 생성
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 컴포넌트 초기화
        self.processor = CSVProcessor()
        self.writer = ResultWriter(self.output_dir)
        
        # 파일 감시기 초기화 (콜백으로 _handle_new_file 연결)
        self.watcher = FileWatcher(
            watch_dir=self.input_dir,
            on_file_created=self._handle_new_file
        )
        
        # 로깅 설정
        self._setup_logging()
        
        # 종료 신호 처리
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _setup_logging(self):
        """로깅 설정 (INFO 레벨로 설정)"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('inspector.log', encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def _signal_handler(self, signum, frame):
        """시그널 핸들러 (Ctrl+C 등)"""
        self.logger.info(f"시그널 {signum} 수신, 데몬 종료 중...")
        self.watcher.stop()
        sys.exit(0)
        
    def _handle_new_file(self, file_path: Path):
        """
        새 파일 생성 이벤트 핸들러
        
        Args:
            file_path: 생성된 파일 경로 (Path 객체)
        """
        try:
            self.logger.info(f"새 파일 감지: {file_path.name}")
            
            # 1. CSV 파일에서 Vrms 값 추출 (B열 4행)
            vrms_value = self.processor.extract_vrms_from_csv(file_path)
            
            if vrms_value is None:
                self.logger.error(f"Vrms 값 추출 실패: {file_path.name}")
                return
            
            self.logger.info(f"Vrms 값 추출 성공: {vrms_value:.6f}")
            
            # 2. 변환 계산
            converted = convert_vrms(vrms_value)
            
            # 3. 판정
            judgement = judge_vrms(vrms_value)
            
            # 4. 결과 데이터 준비
            result = {
                'timestamp': datetime.now().isoformat(),
                'input_file': file_path.name,
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
                self.logger.info(f"결과 저장 완료: {file_path.name}")
            else:
                self.logger.error(f"결과 저장 실패: {file_path.name}")
            
            self.logger.info(f"처리 완료: {file_path.name} -> {judgement['result']}")
            
        except Exception as e:
            self.logger.error(f"파일 처리 중 오류: {file_path.name}, 오류: {e}")
    
    def _print_result(self, result: dict):
        """
        결과를 터미널에 출력 (사용자 요구사항에 맞춤)
        
        Args:
            result: 처리 결과 딕셔너리
        """
        print("\n" + "="*60)
        print(f"[RANC Auto Inspector] 처리 완료")
        print("="*60)
        print(f"  입력 파일: {result['input_file']}")
        print(f"  처리 시간: {result['timestamp']}")
        print(f"  Vrms 값: {result['vrms']:.6f}")
        print(f"  LSB: {result['lsb']:.2f}")
        print(f"  SENS: {result['sens']:.2f} dB")
        print(f"  g: {result['g']:.6f}")
        print(f"  판정: {result['judgement']}")
        print(f"  허용 범위: {result['lower_bound']:.6f} ~ {result['upper_bound']:.6f}")
        print(f"  범위 내 여부: {'예' if result['is_within_range'] else '아니오'}")
        print("="*60)
    
    def run(self):
        """데몬 실행 메인 루프"""
        self.logger.info("="*60)
        self.logger.info("RANC Auto Inspector Daemon 시작")
        self.logger.info(f"감시 디렉토리: {self.input_dir.absolute()}")
        self.logger.info(f"결과 저장 위치: {self.output_dir.absolute()}")
        self.logger.info("="*60)
        self.logger.info("데몬 실행 중... 새 CSV 파일을 생성하면 자동 처리됩니다.")
        self.logger.info("종료하려면 Ctrl+C를 누르세요.")
        
        # 기존 통계 출력
        stats = self.writer.get_statistics()
        self.logger.info(f"현재까지 처리 통계: 총 {stats['total']}개, "
                        f"PASS {stats['pass']}개, FAIL {stats['fail']}개 "
                        f"(합격률 {stats['pass_rate']:.1f}%)")
        
        try:
            # 파일 감시 시작
            self.watcher.start()
        except KeyboardInterrupt:
            self.logger.info("사용자에 의해 종료됨")
        except Exception as e:
            self.logger.error(f"데몬 실행 중 오류: {e}")
        finally:
            self.watcher.stop()
            self.logger.info("데몬 종료")


def print_banner():
    """시작 배너 출력"""
    banner = """
    ╔══════════════════════════════════════════════════════╗
    ║      RANC Auto Inspector Daemon v1.0.0               ║
    ║      디렉토리 감시 및 실시간 CSV 처리 시스템              ║
    ╚══════════════════════════════════════════════════════╝
    """
    print(banner)


def main():
    """메인 진입점"""
    print_banner()
    
    # 명령줄 인자 처리
    import argparse
    parser = argparse.ArgumentParser(description='RANC Auto Inspector Daemon')
    parser.add_argument('--input', '-i', default='data/input_logs',
                       help='입력 CSV 파일 감시 디렉토리 (기본: data/input_logs)')
    parser.add_argument('--output', '-o', default='data/output_results',
                       help='결과 저장 디렉토리 (기본: data/output_results)')
    parser.add_argument('--version', '-v', action='store_true',
                       help='버전 정보 출력')
    
    args = parser.parse_args()
    
    if args.version:
        print(f"RANC Auto Inspector Daemon v1.0.0")
        return
    
    # 데몬 생성 및 실행
    daemon = AutoInspectorDaemon(
        input_dir=args.input,
        output_dir=args.output
    )
    daemon.run()


if __name__ == "__main__":
    main()