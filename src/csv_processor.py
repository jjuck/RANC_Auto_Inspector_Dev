"""
CSV 파일 처리 모듈
B열 4행 (엑셀 기준 B4 셀)에서 Vrms 값을 추출
"""

import pandas as pd
from pathlib import Path
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class CSVProcessor:
    """CSV 파일에서 Vrms 값을 추출하는 클래스"""
    
    def __init__(self):
        pass
    
    def extract_vrms_from_csv(self, file_path: Path) -> Optional[float]:
        """
        CSV 파일에서 Vrms 값을 추출
        
        Args:
            file_path: CSV 파일 경로 (Path 객체)
            
        Returns:
            추출된 Vrms 값 (float), 실패 시 None
        """
        try:
            # CSV 파일을 헤더 없이 읽기 (header=None)
            # 엑셀 B4 셀은 0-based 인덱스로 [3, 1] (행=3, 열=1)
            df = pd.read_csv(file_path, header=None)
            
            # 데이터프레임 크기 확인
            if df.shape[0] < 4 or df.shape[1] < 2:
                logger.error(f"CSV 파일 크기가 너무 작습니다: {file_path.name}")
                return None
            
            # B4 셀 값 추출 (iloc[3, 1])
            vrms_value = df.iloc[3, 1]
            
            # 값이 숫자인지 확인
            try:
                vrms_float = float(vrms_value)
                logger.debug(f"Vrms 값 추출 성공: {file_path.name} -> {vrms_float}")
                return vrms_float
            except (ValueError, TypeError):
                logger.error(f"B4 셀 값이 숫자가 아닙니다: {vrms_value}")
                return None
                
        except FileNotFoundError:
            logger.error(f"파일을 찾을 수 없습니다: {file_path}")
            return None
        except pd.errors.EmptyDataError:
            logger.error(f"CSV 파일이 비어 있습니다: {file_path.name}")
            return None
        except pd.errors.ParserError:
            logger.error(f"CSV 파일 파싱 오류: {file_path.name}")
            return None
        except Exception as e:
            logger.error(f"CSV 파일 처리 중 예상치 못한 오류: {file_path.name}, 오류: {e}")
            return None
    
    def validate_csv_file(self, file_path: Path) -> bool:
        """
        CSV 파일이 유효한지 검증 (확장자 및 존재 여부)
        
        Args:
            file_path: 검증할 파일 경로
            
        Returns:
            유효하면 True, 아니면 False
        """
        if not file_path.exists():
            logger.warning(f"파일이 존재하지 않습니다: {file_path}")
            return False
        
        if file_path.suffix.lower() != '.csv':
            logger.warning(f"CSV 파일이 아닙니다: {file_path.name}")
            return False
        
        return True


if __name__ == "__main__":
    # 모듈 테스트
    import sys
    
    if len(sys.argv) > 1:
        test_file = Path(sys.argv[1])
        processor = CSVProcessor()
        
        if processor.validate_csv_file(test_file):
            vrms = processor.extract_vrms_from_csv(test_file)
            if vrms is not None:
                print(f"테스트 성공: Vrms = {vrms}")
            else:
                print("테스트 실패: Vrms 값을 추출할 수 없습니다.")
        else:
            print("테스트 실패: 유효한 CSV 파일이 아닙니다.")
    else:
        print("사용법: python csv_processor.py <csv_file_path>")