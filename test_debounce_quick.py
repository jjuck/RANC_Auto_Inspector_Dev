#!/usr/bin/env python3
"""
디바운스 기능 테스트 스크립트
동일한 파일을 0.5초 간격으로 두 번 복사하여 중복 처리 방지 확인
"""
import time
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
SOURCE_FILE = PROJECT_ROOT / "data" / "input_logs" / "96398XGR500X251215X052.csv"
TARGET_DIR = PROJECT_ROOT / "data" / "input_logs"
TARGET_NAME = "test_debounce_quick.csv"

def main():
    print("디바운스 테스트 시작...")
    print(f"원본 파일: {SOURCE_FILE}")
    print(f"대상 디렉토리: {TARGET_DIR}")
    
    # 첫 번째 복사
    target1 = TARGET_DIR / TARGET_NAME
    shutil.copy2(SOURCE_FILE, target1)
    print(f"[{time.strftime('%H:%M:%S')}] 첫 번째 복사 완료: {target1.name}")
    
    # 0.5초 대기
    time.sleep(0.5)
    
    # 두 번째 복사 (동일 파일명)
    target2 = TARGET_DIR / TARGET_NAME
    shutil.copy2(SOURCE_FILE, target2)
    print(f"[{time.strftime('%H:%M:%S')}] 두 번째 복사 완료: {target2.name} (0.5초 후)")
    
    # 3초 대기하여 처리 로그 확인
    print("3초 대기 중... 서버 로그를 확인하세요.")
    time.sleep(3)
    
    # 파일 정리
    if target1.exists():
        target1.unlink()
        print(f"테스트 파일 삭제: {target1.name}")
    
    print("테스트 완료. 서버 로그에서 '중복 파일 처리 방지' 메시지를 확인하세요.")

if __name__ == "__main__":
    main()