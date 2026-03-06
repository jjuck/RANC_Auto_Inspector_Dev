"""
판정 로직 모듈
Vrms 값이 허용 범위 내에 있는지 판정
허용 범위: (468.6 / 8192) ≤ Vrms ≤ (572.7 / 8192)
"""

import logging
from typing import Dict, Literal

logger = logging.getLogger(__name__)


def calculate_bounds() -> tuple:
    """
    허용 범위 상한/하한 계산
    
    Returns:
        (lower_bound, upper_bound) 튜플
    """
    lower_bound = 468.6 / 8192
    upper_bound = 572.7 / 8192
    return lower_bound, upper_bound


def judge_vrms(vrms: float) -> Dict[str, any]:
    """
    Vrms 값이 허용 범위 내에 있는지 판정
    
    Args:
        vrms: 입력 Vrms 값 (float)
        
    Returns:
        판정 결과 딕셔너리:
        {
            'result': 'PASS' 또는 'FAIL',
            'vrms': 입력 Vrms 값,
            'lower_bound': 하한 값,
            'upper_bound': 상한 값,
            'is_within_range': 범위 내 여부 (bool)
        }
    """
    lower_bound, upper_bound = calculate_bounds()
    
    # 범위 체크 (양쪽 포함)
    is_within_range = lower_bound <= vrms <= upper_bound
    
    result: Literal['PASS', 'FAIL'] = 'PASS' if is_within_range else 'FAIL'
    
    judgement = {
        'result': result,
        'vrms': vrms,
        'lower_bound': lower_bound,
        'upper_bound': upper_bound,
        'is_within_range': is_within_range
    }
    
    logger.debug(f"판정 완료: Vrms={vrms:.6f} -> {result} "
                 f"(범위: {lower_bound:.6f} ~ {upper_bound:.6f})")
    
    return judgement


def judge_with_tolerance(vrms: float, tolerance_percent: float = 0.0) -> Dict[str, any]:
    """
    허용 오차를 고려한 판정
    
    Args:
        vrms: 입력 Vrms 값
        tolerance_percent: 허용 오차 백분율 (예: 1.0 = 1%)
        
    Returns:
        판정 결과 딕셔너리 (기본 judge_vrms 결과에 오차 정보 추가)
    """
    lower_bound, upper_bound = calculate_bounds()
    
    # 오차 적용
    tolerance_factor = tolerance_percent / 100.0
    lower_bound_with_tol = lower_bound * (1 - tolerance_factor)
    upper_bound_with_tol = upper_bound * (1 + tolerance_factor)
    
    is_within_range = lower_bound_with_tol <= vrms <= upper_bound_with_tol
    result: Literal['PASS', 'FAIL'] = 'PASS' if is_within_range else 'FAIL'
    
    judgement = {
        'result': result,
        'vrms': vrms,
        'lower_bound': lower_bound,
        'upper_bound': upper_bound,
        'lower_bound_with_tolerance': lower_bound_with_tol,
        'upper_bound_with_tolerance': upper_bound_with_tol,
        'is_within_range': is_within_range,
        'tolerance_percent': tolerance_percent,
        'is_within_original_range': lower_bound <= vrms <= upper_bound
    }
    
    return judgement


def get_judgement_statistics(judgements: list) -> Dict[str, any]:
    """
    여러 판정 결과에 대한 통계 계산
    
    Args:
        judgements: judge_vrms() 결과 리스트
        
    Returns:
        통계 정보 딕셔너리
    """
    if not judgements:
        return {
            'total': 0,
            'pass': 0,
            'fail': 0,
            'pass_rate': 0.0
        }
    
    total = len(judgements)
    pass_count = sum(1 for j in judgements if j['result'] == 'PASS')
    fail_count = total - pass_count
    pass_rate = (pass_count / total) * 100 if total > 0 else 0.0
    
    # Vrms 값 분포
    vrms_values = [j['vrms'] for j in judgements]
    
    return {
        'total': total,
        'pass': pass_count,
        'fail': fail_count,
        'pass_rate': pass_rate,
        'min_vrms': min(vrms_values) if vrms_values else None,
        'max_vrms': max(vrms_values) if vrms_values else None,
        'avg_vrms': sum(vrms_values) / total if total > 0 else None
    }


if __name__ == "__main__":
    # 모듈 테스트
    import sys
    
    # 로깅 설정
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1:
        try:
            test_vrms = float(sys.argv[1])
            result = judge_vrms(test_vrms)
            print(f"판정 테스트:")
            print(f"  입력 Vrms: {result['vrms']:.6f}")
            print(f"  허용 범위: {result['lower_bound']:.6f} ~ {result['upper_bound']:.6f}")
            print(f"  범위 내 여부: {'예' if result['is_within_range'] else '아니오'}")
            print(f"  판정 결과: {result['result']}")
        except ValueError:
            print("오류: 숫자를 입력해주세요.")
    else:
        # 기본 테스트 값
        test_values = [0.0572, 0.0650, 0.0700, 0.0550, 0.0750]
        lower, upper = calculate_bounds()
        print(f"허용 범위: {lower:.6f} ~ {upper:.6f}")
        print("\n기본 테스트:")
        
        for vrms in test_values:
            result = judge_vrms(vrms)
            status = "✓" if result['result'] == 'PASS' else "✗"
            print(f"{status} Vrms={vrms:.6f}: {result['result']} "
                  f"(범위 내: {result['is_within_range']})")
        
        # 통계 테스트
        print("\n통계 테스트:")
        judgements = [judge_vrms(v) for v in test_values]
        stats = get_judgement_statistics(judgements)
        print(f"  총 개수: {stats['total']}")
        print(f"  PASS: {stats['pass']}, FAIL: {stats['fail']}")
        print(f"  합격률: {stats['pass_rate']:.1f}%")