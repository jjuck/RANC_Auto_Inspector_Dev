import csv
import math
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from src.calculator import convert_dbfs
from src.csv_processor import CSVProcessor
from src.integrated_server import AutoInspectorDaemon
from src.judge import calculate_bounds, judge_vrms
from src.result_writer import ResultWriter


class DbfsProcessingTest(unittest.TestCase):
    def _raw_csv_with_noise(
        self,
        dbfs: float,
        noise_level: float,
        ch2_dbfs: float = -53.9899371144151,
        ch2_noise_level: float = 0.0019964198465005,
    ) -> str:
        return (
            '"RMS Level","RMS Level",,,,\n'
            'Channel,"RMS Level","Lower Limit","Passed Lower Limit","Upper Limit","Passed Upper Limit"\n'
            ",dBFS,dBFS,,dBFS,\n"
            f"Ch1,{dbfs},,True,,True\n"
            f"Ch2,{ch2_dbfs},,True,,True\n"
            "\n"
            '"Noise Level","Noise Level",,,,\n'
            'Channel,"Noise Level","Lower Limit","Passed Lower Limit","Upper Limit","Passed Upper Limit"\n'
            ",FS,FS,,FS,\n"
            f"Ch1,{noise_level},,True,,True\n"
            f"Ch2,{ch2_noise_level},,True,,True\n"
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

    def test_extract_dbfs_uses_higher_value_between_b4_and_b5(self):
        csv_text = self._raw_csv_with_noise(-53.3673171056118, 0.00216658732609638, ch2_dbfs=-23.472900117816)

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "sample.csv"
            csv_path.write_text(csv_text, encoding="utf-8")

            dbfs = CSVProcessor().extract_dbfs_from_csv(csv_path)

        self.assertAlmostEqual(dbfs, -23.472900117816)

    def test_extract_legacy_vrms_cell_uses_higher_value_between_b4_and_b5(self):
        csv_text = self._raw_csv_with_noise(-48.4105147726355, 0.00379835708024134, ch2_dbfs=-23.5811609819599)

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "sample.csv"
            csv_path.write_text(csv_text, encoding="utf-8")

            value = CSVProcessor().extract_vrms_from_csv(csv_path)

        self.assertAlmostEqual(value, -23.5811609819599)

    def test_judgement_bounds_use_minus_24_dbfs_with_1_5_db_tolerance(self):
        lower_bound, upper_bound = calculate_bounds()

        self.assertAlmostEqual(lower_bound, math.pow(10, -25.5 / 20))
        self.assertAlmostEqual(upper_bound, math.pow(10, -22.5 / 20))
        self.assertEqual(judge_vrms(math.pow(10, -24 / 20))["result"], "PASS")
        self.assertEqual(judge_vrms(math.pow(10, -26 / 20))["result"], "FAIL")
        self.assertEqual(judge_vrms(math.pow(10, -22 / 20))["result"], "FAIL")

    def test_extract_noise_level_from_noise_level_ch1_row(self):
        csv_text = self._raw_csv_with_noise(-55.085314388487, 0.00177202812042252)

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "sample.csv"
            csv_path.write_text(csv_text, encoding="utf-8")

            noise_level = CSVProcessor().extract_noise_level_from_csv(csv_path)

        self.assertAlmostEqual(noise_level, 0.000177202812042252)

    def test_daemon_uses_active_rms_channel_for_scaled_noise_level(self):
        ch1_noise_level = 0.00177202812042252
        ch2_noise_level = 0.00216658732609638
        csv_text = self._raw_csv_with_noise(
            -53.3673171056118,
            ch1_noise_level,
            ch2_dbfs=-23.472900117816,
            ch2_noise_level=ch2_noise_level,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            csv_path = input_dir / "sample.csv"
            csv_path.write_text(csv_text, encoding="utf-8")

            daemon = AutoInspectorDaemon(input_dir, output_dir, websocket_manager=None)
            daemon._handle_new_file(csv_path)

            date_folder = f"{datetime.now():%y%m%d}"
            output_file = output_dir / "X" / date_folder / f"{date_folder}_RANC_X.csv"
            with output_file.open(encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["dBFS"], f"{-23.472900117816:.2f}")
        self.assertEqual(rows[0]["Noise_Level"], f"{ch2_noise_level * 0.1:.15f}")

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

            date_folder = f"{datetime.now():%y%m%d}"
            output_file = output_dir / "X" / date_folder / f"{date_folder}_RANC_X.csv"
            with output_file.open(encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["dBFS"], f"{dbfs:.2f}")
        self.assertEqual(rows[0]["Vrms"], "0.062500")
        self.assertEqual(rows[0]["LSB"], "512.00")
        self.assertEqual(rows[0]["SENS"], f"{dbfs:.2f}")
        self.assertEqual(rows[0]["Judgement"], "PASS")
        self.assertEqual(rows[0]["Noise_Level"], f"{noise_level * 0.1:.15f}")

    def test_daemon_saves_to_current_output_group_directory(self):
        dbfs = 20 * math.log10(0.0625)
        csv_text = self._raw_csv_with_noise(dbfs, 0.00177202812042252)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            csv_path = input_dir / "sample.csv"
            csv_path.write_text(csv_text, encoding="utf-8")

            daemon = AutoInspectorDaemon(input_dir, output_dir, websocket_manager=None)
            daemon.set_output_group("Z")
            daemon._handle_new_file(csv_path)

            date_folder = f"{datetime.now():%y%m%d}"
            output_file = output_dir / "Z" / date_folder / f"{date_folder}_RANC_Z.csv"
            with output_file.open(encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Input_Filename"], "sample.csv")

    def test_result_writer_splits_results_by_group_and_date(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            writer = ResultWriter(output_dir)

            writer.save_result({
                "timestamp": "2026-06-10T23:59:59",
                "input_file": "x.csv",
                "output_group": "X",
                "dbfs": -24.0,
                "vrms": 0.0625,
                "lsb": 512.0,
                "sens": -24.0,
                "g": 1.0,
                "judgement": "PASS",
                "noise_level": 0.000177202812042,
            })
            writer.save_result({
                "timestamp": "2026-06-11T00:00:01",
                "input_file": "y.csv",
                "output_group": "Y",
                "dbfs": -24.0,
                "vrms": 0.0625,
                "lsb": 512.0,
                "sens": -24.0,
                "g": 1.0,
                "judgement": "PASS",
                "noise_level": 0.000177202812042,
            })

            x_file = output_dir / "X" / "260610" / "260610_RANC_X.csv"
            y_file = output_dir / "Y" / "260611" / "260611_RANC_Y.csv"
            with x_file.open(encoding="utf-8", newline="") as f:
                x_rows = list(csv.DictReader(f))
            with y_file.open(encoding="utf-8", newline="") as f:
                y_rows = list(csv.DictReader(f))
            z_dir_exists = (output_dir / "Z").is_dir()

        self.assertTrue(z_dir_exists)
        self.assertEqual(len(x_rows), 1)
        self.assertEqual(len(y_rows), 1)
        self.assertEqual(x_rows[0]["Input_Filename"], "x.csv")
        self.assertEqual(y_rows[0]["Input_Filename"], "y.csv")

    def test_result_writer_migrates_existing_output_header_to_include_dbfs_and_noise_level(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            output_file = output_dir / "X" / "260610" / "260610_RANC_X.csv"
            output_file.parent.mkdir(parents=True)
            output_file.write_text(
                "Timestamp,Input_Filename,Vrms,LSB,SENS,g,Judgement\n"
                "2026-01-01T00:00:00,old.csv,0.062500,512.00,-24.08,1.000000,PASS\n",
                encoding="utf-8",
            )

            writer = ResultWriter(output_dir)
            writer.save_result({
                "timestamp": "2026-06-10T00:00:01",
                "input_file": "new.csv",
                "output_group": "X",
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
