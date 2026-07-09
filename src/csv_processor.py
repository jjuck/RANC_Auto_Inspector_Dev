"""
CSV 파일 처리 모듈
RMS Level 섹션에서 Ch1/Ch2 dBFS 값 중 더 높은 값을 추출
"""

import pandas as pd
from pathlib import Path
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_RMS_CHANNELS = ("Ch1", "Ch2")
NOISE_LEVEL_SCALE = 0.1


@dataclass(frozen=True)
class ChannelMeasurement:
    channel: str
    value: float


class CSVProcessor:
    """CSV 파일에서 측정 값을 추출하는 클래스"""
    
    def __init__(self):
        pass

    @staticmethod
    def _cell_text(value) -> str:
        if pd.isna(value):
            return ""
        return str(value).strip()

    def extract_dbfs_from_csv(self, file_path: Path, channel: Optional[str] = None) -> Optional[float]:
        """
        CSV 파일의 RMS Level 섹션에서 dBFS 값을 추출
        
        Args:
            file_path: CSV 파일 경로 (Path 객체)
            channel: 추출할 채널명. None이면 Ch1/Ch2 중 더 높은 값을 사용
            
        Returns:
            추출된 dBFS 값 (float), 실패 시 None
        """
        if channel is None:
            measurement = self.extract_active_dbfs_from_csv(file_path)
            return None if measurement is None else measurement.value

        try:
            df = pd.read_csv(file_path, header=None)
            
            if df.shape[0] < 4 or df.shape[1] < 2:
                logger.error(f"CSV 파일 크기가 너무 작습니다: {file_path.name}")
                return None
            
            dbfs_value = self._find_rms_level_dbfs(df, channel)
            if dbfs_value is None:
                logger.error(f"RMS Level 섹션에서 {channel} dBFS 값을 찾을 수 없습니다: {file_path.name}")
                return None
            
            logger.debug(f"dBFS 값 추출 성공: {file_path.name} -> {dbfs_value}")
            return dbfs_value
                
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

    def extract_active_dbfs_from_csv(self, file_path: Path) -> Optional[ChannelMeasurement]:
        """
        CSV 파일의 RMS Level 섹션에서 Ch1/Ch2 중 더 높은 dBFS 값과 채널을 추출
        """
        try:
            df = pd.read_csv(file_path, header=None)

            if df.shape[0] < 5 or df.shape[1] < 2:
                logger.error(f"CSV 파일 크기가 너무 작습니다: {file_path.name}")
                return None

            measurement = self._find_highest_rms_level_dbfs(df, DEFAULT_RMS_CHANNELS)
            if measurement is None:
                logger.error(f"RMS Level 섹션에서 활성 dBFS 값을 찾을 수 없습니다: {file_path.name}")
                return None

            logger.debug(
                f"dBFS 값 추출 성공: {file_path.name} -> {measurement.channel}={measurement.value}"
            )
            return measurement

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

    def extract_noise_level_from_csv(self, file_path: Path, channel: str = "Ch1") -> Optional[float]:
        """
        CSV 파일의 Noise Level 섹션에서 지정 채널의 FS 값을 추출
        
        Args:
            file_path: CSV 파일 경로 (Path 객체)
            channel: 추출할 채널명 (기본값: Ch1)
            
        Returns:
            추출된 Noise Level 값 (float), 실패 시 None
        """
        try:
            df = pd.read_csv(file_path, header=None)
            
            if df.shape[0] < 4 or df.shape[1] < 2:
                logger.error(f"CSV 파일 크기가 너무 작습니다: {file_path.name}")
                return None
            
            noise_level = self._find_measurement_value(df, "Noise Level", "fs", channel)
            if noise_level is None:
                logger.error(f"Noise Level 섹션에서 {channel} FS 값을 찾을 수 없습니다: {file_path.name}")
                return None
            
            scaled_noise_level = noise_level * NOISE_LEVEL_SCALE
            logger.debug(
                f"Noise Level 값 추출 성공: {file_path.name} -> "
                f"{channel}={noise_level}, scaled={scaled_noise_level}"
            )
            return scaled_noise_level
                
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

    def _find_rms_level_dbfs(self, df: pd.DataFrame, channel: str) -> Optional[float]:
        return self._find_measurement_value(df, "RMS Level", "dbfs", channel)

    def _find_highest_rms_level_dbfs(self, df: pd.DataFrame, channels: tuple[str, ...]) -> Optional[ChannelMeasurement]:
        selected: Optional[ChannelMeasurement] = None
        for channel in channels:
            value = self._find_rms_level_dbfs(df, channel)
            if value is None:
                continue
            if selected is None or value > selected.value:
                selected = ChannelMeasurement(channel=channel, value=value)
        return selected

    def _find_measurement_value(
        self,
        df: pd.DataFrame,
        measurement_name: str,
        unit_name: str,
        channel: str
    ) -> Optional[float]:
        for header_row in range(len(df) - 2):
            first_cell = self._cell_text(df.iloc[header_row, 0])
            second_cell = self._cell_text(df.iloc[header_row, 1])
            unit_cell = self._cell_text(df.iloc[header_row + 1, 1]).lower()
            
            if first_cell != "Channel" or second_cell != measurement_name or unit_cell != unit_name:
                continue
            
            for data_row in range(header_row + 2, len(df)):
                row_channel = self._cell_text(df.iloc[data_row, 0])
                if row_channel == channel:
                    try:
                        return float(df.iloc[data_row, 1])
                    except (ValueError, TypeError):
                        logger.error(f"{channel} {measurement_name} 값이 숫자가 아닙니다: {df.iloc[data_row, 1]}")
                        return None
                
                if row_channel and not row_channel.startswith("Ch"):
                    break
        
        return None
    
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
            if df.shape[0] < 5:
                logger.error(f"CSV file is too small to read B5: {file_path.name}")
                return None

            vrms_values = [df.iloc[3, 1], df.iloc[4, 1]]
            
            # 값이 숫자인지 확인
            try:
                vrms_float = max(float(value) for value in vrms_values)
                logger.debug(f"Vrms 값 추출 성공: {file_path.name} -> {vrms_float}")
                return vrms_float
            except (ValueError, TypeError):
                logger.error(f"B4/B5 셀 값이 숫자가 아닙니다: {vrms_values}")
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
