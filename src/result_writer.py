"""
결과 저장 모듈
처리 결과를 CSV 파일에 누적 저장
"""

import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ResultWriter:
    """결과 CSV 파일 작성기"""
    
    def __init__(self, output_dir: Path, filename: str = "inspection_results.csv"):
        """
        Args:
            output_dir: 결과 파일 저장 디렉토리
            filename: 결과 CSV 파일명
        """
        self.output_dir = output_dir
        self.output_file = output_dir / filename
        
        # 디렉토리 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # CSV 컬럼 정의 (사용자 요구사항에 맞춤)
        self.fieldnames = [
            'Timestamp',
            'Input_Filename',
            'dBFS',
            'Vrms',
            'LSB',
            'SENS',
            'g',
            'Judgement',
            'Noise_Level'
        ]
        
        # 파일 존재 여부 확인 (헤더 작성 필요 여부)
        self.file_exists = self.output_file.exists() and self.output_file.stat().st_size > 0
        if self.file_exists:
            self._migrate_header_if_needed()
        
        logger.info(f"결과 저장 위치: {self.output_file.absolute()}")

    def _migrate_header_if_needed(self) -> None:
        """
        기존 결과 파일에 새 컬럼이 추가되었을 때 헤더와 기존 행을 보정
        """
        try:
            with open(self.output_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                existing_fieldnames = reader.fieldnames or []
                rows = list(reader)
            
            if existing_fieldnames == self.fieldnames:
                return
            
            if not set(existing_fieldnames).issubset(set(self.fieldnames)):
                logger.warning(f"알 수 없는 결과 CSV 컬럼이 있어 헤더 마이그레이션을 건너뜁니다: {existing_fieldnames}")
                return
            
            with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow({field: row.get(field, "") for field in self.fieldnames})
            
            logger.info(f"결과 CSV 헤더 마이그레이션 완료: {self.output_file.name}")
        except Exception as e:
            logger.error(f"결과 CSV 헤더 마이그레이션 중 오류: {e}")
    
    def save_result(self, result: Dict[str, any]) -> bool:
        """
        단일 결과를 CSV 파일에 저장 (append 모드)
        
        Args:
            result: 저장할 결과 딕셔너리
            
        Returns:
            성공 시 True, 실패 시 False
        """
        try:
            # 결과 데이터 준비
            csv_row = self._prepare_csv_row(result)
            
            # 파일 열기 (append 모드, 헤더는 파일이 없을 때만 작성)
            mode = 'a' if self.file_exists else 'w'
            with open(self.output_file, mode, newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                
                # 파일이 새로 생성된 경우 헤더 작성
                if not self.file_exists:
                    writer.writeheader()
                    self.file_exists = True
                
                # 데이터 행 작성
                writer.writerow(csv_row)
            
            logger.debug(f"결과 저장 완료: {result.get('input_file', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"결과 저장 중 오류: {e}")
            return False
    
    def save_batch_results(self, results: List[Dict[str, any]]) -> int:
        """
        여러 결과를 일괄 저장
        
        Args:
            results: 저장할 결과 딕셔너리 리스트
            
        Returns:
            성공적으로 저장된 결과 수
        """
        if not results:
            return 0
        
        success_count = 0
        for result in results:
            if self.save_result(result):
                success_count += 1
        
        logger.info(f"배치 저장 완료: {success_count}/{len(results)}개 성공")
        return success_count
    
    def _prepare_csv_row(self, result: Dict[str, any]) -> Dict[str, any]:
        """
        결과 딕셔너리를 CSV 행으로 변환
        
        Args:
            result: 원본 결과 딕셔너리
            
        Returns:
            CSV 행에 맞는 딕셔너리
        """
        # 타임스탬프 (이미 있으면 사용, 없으면 현재 시간)
        timestamp = result.get('timestamp')
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        # 파일명 (확장자 포함 전체 파일명)
        input_filename = result.get('input_file', 'unknown')
        
        # 숫자 값 포맷팅 (소수점 적절히)
        dbfs = result.get('dbfs')
        noise_level = result.get('noise_level')
        vrms = float(result.get('vrms', 0))
        lsb = float(result.get('lsb', 0))
        sens = float(result.get('sens', 0))
        g_value = float(result.get('g', 0))
        
        # 판정 결과
        judgement = result.get('judgement', 'UNKNOWN')
        
        return {
            'Timestamp': timestamp,
            'Input_Filename': input_filename,
            'dBFS': "" if dbfs is None else f"{float(dbfs):.2f}",
            'Vrms': f"{vrms:.6f}",
            'LSB': f"{lsb:.2f}",
            'SENS': f"{sens:.2f}",
            'g': f"{g_value:.6f}",
            'Judgement': judgement,
            'Noise_Level': "" if noise_level is None else f"{float(noise_level):.15f}"
        }
    
    def get_recent_results(self, limit: int = 10) -> List[Dict[str, any]]:
        """
        최근 저장된 결과 조회
        
        Args:
            limit: 조회할 최대 결과 수
            
        Returns:
            최근 결과 리스트
        """
        if not self.output_file.exists():
            return []
        
        try:
            results = []
            with open(self.output_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    results.append(row)
            
            # 최근 결과부터 반환 (마지막 행이 최신)
            return list(reversed(results))[:limit]
            
        except Exception as e:
            logger.error(f"결과 조회 중 오류: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, any]:
        """
        저장된 결과 통계 계산
        
        Returns:
            통계 정보 딕셔너리
        """
        if not self.output_file.exists():
            return {
                'total': 0,
                'pass': 0,
                'fail': 0,
                'pass_rate': 0.0
            }
        
        try:
            total = 0
            pass_count = 0
            
            with open(self.output_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    total += 1
                    if row.get('Judgement', '').upper() == 'PASS':
                        pass_count += 1
            
            fail_count = total - pass_count
            pass_rate = (pass_count / total * 100) if total > 0 else 0.0
            
            return {
                'total': total,
                'pass': pass_count,
                'fail': fail_count,
                'pass_rate': pass_rate
            }
            
        except Exception as e:
            logger.error(f"통계 계산 중 오류: {e}")
            return {
                'total': 0,
                'pass': 0,
                'fail': 0,
                'pass_rate': 0.0
            }
    
    def clear_results(self) -> bool:
        """
        결과 파일 초기화
        
        Returns:
            성공 시 True, 실패 시 False
        """
        try:
            if self.output_file.exists():
                self.output_file.unlink()
                self.file_exists = False
                logger.info("결과 파일 초기화 완료")
            return True
        except Exception as e:
            logger.error(f"결과 파일 초기화 중 오류: {e}")
            return False


if __name__ == "__main__":
    # 모듈 테스트
    import sys
    
    # 로깅 설정
    logging.basicConfig(level=logging.INFO)
    
    # 테스트 디렉토리
    test_dir = Path("data/output_results")
    writer = ResultWriter(test_dir, "test_results.csv")
    
    # 테스트 데이터
    test_results = [
        {
            'timestamp': '2024-01-01T10:00:00',
            'input_file': 'test1.csv',
            'vrms': 0.0572,
            'lsb': 468.6,
            'sens': -24.85,
            'g': 0.9152,
            'judgement': 'PASS'
        },
        {
            'timestamp': '2024-01-01T10:01:00',
            'input_file': 'test2.csv',
            'vrms': 0.0700,
            'lsb': 573.4,
            'sens': -23.10,
            'g': 1.1200,
            'judgement': 'FAIL'
        }
    ]
    
    print("결과 저장 테스트:")
    
    # 기존 파일 초기화
    writer.clear_results()
    
    # 결과 저장
    for i, result in enumerate(test_results):
        success = writer.save_result(result)
        status = "성공" if success else "실패"
        print(f"  결과 {i+1} 저장: {status}")
    
    # 통계 조회
    stats = writer.get_statistics()
    print(f"\n저장 통계:")
    print(f"  총 개수: {stats['total']}")
    print(f"  PASS: {stats['pass']}, FAIL: {stats['fail']}")
    print(f"  합격률: {stats['pass_rate']:.1f}%")
    
    # 최근 결과 조회
    recent = writer.get_recent_results(5)
    print(f"\n최근 결과 ({len(recent)}개):")
    for i, row in enumerate(recent):
        print(f"  {i+1}. {row['Input_Filename']}: {row['Judgement']} (Vrms={row['Vrms']})")
    
    print(f"\n테스트 완료. 결과 파일: {writer.output_file}")
