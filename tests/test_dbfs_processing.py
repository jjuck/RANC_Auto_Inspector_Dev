import csv
import math
import tempfile
import unittest
from pathlib import Path

from src.calculator import convert_dbfs
from src.csv_processor import CSVProcessor
from src.integrated_server import AutoInspectorDaemon
from src.result_writer import ResultWriter


class DbfsProcessingTest(unittest.TestCase):
    def _raw_csv_with_noise(self, dbfs: float, noise_level: float) -> str:
        return (
            '"RMS Level","RMS Level",,,,\n'
            'Channel,"RMS Level","Lower Limit","Passed Lower Limit","Upper Limit","Passed Upper Limit"\n'
            ",dBFS,dBFS,,dBFS,\n"
            f"Ch1,{dbfs},,True,,True\n"
            "Ch2,-53.9899371144151,,True,,True\n"
            "\n"
            '"Noise Level","Noise Level",,,,\n'
            'Channel,"Noise Level","Lower Limit","Passed Lower Limit","Upper Limit","Passed Upper Limit"\n'
            ",FS,FS,,FS,\n"
            f"Ch1,{noise_level},,True,,True\n"
            "Ch2,0.0019964198465005,,True,,True\n"
        )

    def test_convert_dbfs_uses_dbfs_as_sens_and_converts_to_linear_value(self):
        dbfs = 20 * math.log10(0.0625)

        converted = convert_dbfs(dbfs)

        self.assertAlmostEqual(converted["original_dbfs"], dbfs)
        self.assertAlmostEqual(converted["original_vrms"], 0.0625)
        self.assertAlmostEqual(converted["lsb"], 512.0)
        self.assertAlmostEqual(converted["sens"], dbfs)
        self.assertAlmostEqual(converted["g"], 1.0)

    def test_extract_dbfs_from_rms_level_ch1_row(self):
        csv_text = self._raw_csv_with_noise(-19.8321729604144, 0.00177202812042252)

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "sample.csv"
            csv_path.write_text(csv_text, encoding="utf-8")

            dbfs = CSVProcessor().extract_dbfs_from_csv(csv_path)

        self.assertAlmostEqual(dbfs, -19.8321729604144)

    def test_extract_noise_level_from_noise_level_ch1_row(self):
        csv_text = self._raw_csv_with_noise(-55.085314388487, 0.00177202812042252)

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "sample.csv"
            csv_path.write_text(csv_text, encoding="utf-8")

            noise_level = CSVProcessor().extract_noise_level_from_csv(csv_path)

        self.assertAlmostEqual(noise_level, 0.00177202812042252)

    def test_daemon_converts_extracted_dbfs_before_saving_result(self):
        dbfs = 20 * math.log10(0.0625)
        noise_level = 0.00177202812042252
        csv_text = self._raw_csv_with_noise(dbfs, noise_level)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            csv_path = input_dir / "sample.csv"
            csv_path.write_text(csv_text, encoding="utf-8")

            daemon = AutoInspectorDaemon(input_dir, output_dir, websocket_manager=None)
            daemon._handle_new_file(csv_path)

            with (output_dir / "inspection_results.csv").open(encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["dBFS"], f"{dbfs:.2f}")
        self.assertEqual(rows[0]["Vrms"], "0.062500")
        self.assertEqual(rows[0]["LSB"], "512.00")
        self.assertEqual(rows[0]["SENS"], f"{dbfs:.2f}")
        self.assertEqual(rows[0]["Judgement"], "PASS")
        self.assertEqual(rows[0]["Noise_Level"], f"{noise_level:.15f}")

    def test_result_writer_migrates_existing_output_header_to_include_dbfs_and_noise_level(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            output_file = output_dir / "inspection_results.csv"
            output_file.write_text(
                "Timestamp,Input_Filename,Vrms,LSB,SENS,g,Judgement\n"
                "2026-01-01T00:00:00,old.csv,0.062500,512.00,-24.08,1.000000,PASS\n",
                encoding="utf-8",
            )

            writer = ResultWriter(output_dir)
            writer.save_result({
                "timestamp": "2026-01-01T00:00:01",
                "input_file": "new.csv",
                "dbfs": -24.082399653118497,
                "vrms": 0.0625,
                "lsb": 512.0,
                "sens": -24.082399653118497,
                "g": 1.0,
                "judgement": "PASS",
                "noise_level": 0.00177202812042252,
            })

            with output_file.open(encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

        self.assertEqual(reader.fieldnames, ["Timestamp", "Input_Filename", "dBFS", "Vrms", "LSB", "SENS", "g", "Judgement", "Noise_Level"])
        self.assertEqual(rows[0]["dBFS"], "")
        self.assertEqual(rows[0]["Noise_Level"], "")
        self.assertEqual(rows[1]["dBFS"], "-24.08")
        self.assertEqual(rows[1]["Noise_Level"], "0.001772028120423")


if __name__ == "__main__":
    unittest.main()
