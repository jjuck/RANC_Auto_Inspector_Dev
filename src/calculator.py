"""
Vrms 값 변환 계산 모듈
LSB = Vrms * 8192
SENS = 20 * log10(Vrms)
g = Vrms * 16
"""

import math
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def convert_vrms(vrms: float) -> Dict[str, float]:
    """
    Vrms 값을 LSB, SENS, g 값으로 변환
    
    Args:
        vrms: 입력 Vrms 값 (float)
        
    Returns:
        변환된 값들을 포함한 딕셔너리:
        {
            'lsb': LSB 값,
            'sens': SENS 값 (dB),
            'g': g 값,
            'original_vrms': 원본 Vrms 값
        }
        
    Raises:
        ValueError: vrms가 음수일 경우 (log10 계산 불가)
    """
    if vrms <= 0:
        logger.warning(f"Vrms 값이 0 이하입니다: {vrms}. SENS 계산 불가")
        sens = float('-inf')
    else:
        try:
            sens = 20 * math.log10(vrms)
        except ValueError as e:
            logger.error(f"SENS 계산 오류: {e}")
            sens = float('-inf')
    
    lsb = vrms * 8192
    g_value = vrms * 16
    
    result = {
        'lsb': lsb,
        'sens': sens,
        'g': g_value,
        'original_vrms': vrms
    }
    
    logger.debug(f"Vrms 변환 완료: {vrms} -> LSB={lsb:.2f}, SENS={sens:.2f} dB, g={g_value:.6f}")
    return result


def batch_convert_vrms(vrms_list: list) -> list:
    """
    여러 Vrms 값을 일괄 변환
    
    Args:
        vrms_list: Vrms 값 리스트
        
    Returns:
        변환 결과 리스트
    """
    results = []
    for vrms in vrms_list:
        try:
            result = convert_vrms(vrms)
            results.append(result)
        except Exception as e:
            logger.error(f"Vrms 변환 실패: {vrms}, 오류: {e}")
            results.append(None)
    return results


if __name__ == "__main__":
    # 모듈 테스트
    import sys
    
    # 로깅 설정
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1:
        try:
            test_vrms = float(sys.argv[1])
            result = convert_vrms(test_vrms)
            print(f"테스트 결과:")
            print(f"  입력 Vrms: {result['original_vrms']}")
            print(f"  LSB: {result['lsb']:.2f}")
            print(f"  SENS: {result['sens']:.2f} dB")
            print(f"  g: {result['g']:.6f}")
        except ValueError:
            print("오류: 숫자를 입력해주세요.")
    else:
        # 기본 테스트 값
        test_values = [0.0572, 0.0650, 0.0700, 0.0, -0.1]
        print("기본 테스트:")
        for vrms in test_values:
            result = convert_vrms(vrms)
            print(f"Vrms={vrms}: LSB={result['lsb']:.2f}, SENS={result['sens']:.2f} dB, g={result['g']:.6f}")