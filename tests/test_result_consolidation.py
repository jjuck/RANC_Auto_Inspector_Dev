import csv
import tempfile
import threading
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from src.result_writer import ResultWriter
from src.integrated_server import AutoInspectorDaemon


class ResultConsolidationTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.writer = ResultWriter(self.root)

    def save(self, sn, axis, timestamp, judgement="PASS"):
        self.assertTrue(self.writer.save_result({
            "input_file": f"{sn}.csv", "output_group": axis,
            "timestamp": timestamp, "judgement": judgement,
        }))

    def merged_path(self, day):
        short = f"{day:%y%m%d}"
        return self.root / "merged" / short / f"{short}_RANC_XYZ.csv"

    def rows(self, day=None):
        path = self.merged_path(day) if day else self.writer.merged_file
        with path.open(encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream))

    def test_latest_per_axis_across_days_and_missing_axes(self):
        self.save("001.part", "X", "2026-09-18T12:00:00")
        self.save("001.part", "X", "2026-09-19T12:00:00", "FAIL")
        # Later append with an older time must not replace the latest measurement.
        self.save("001.part", "X", "2026-09-19T09:00:00")
        self.save("001.part", "Y", "2026-09-18T13:00:00")
        self.save("002", "Z", "2026-09-19T14:00:00")
        self.save("001.part", "X", "2026-09-20T00:00:00")
        sources = {path: path.read_bytes() for path in self.writer._iter_result_files()}
        self.assertTrue(self.writer.consolidate_previous_days(date(2026, 9, 20)))
        rows = self.rows(date(2026, 9, 19))
        self.assertEqual([row["SN"] for row in rows], ["001.part", "002"])
        self.assertEqual(rows[0]["X_Judgement"], "FAIL")
        self.assertEqual(rows[0]["X_Timestamp"], "2026-09-19T12:00:00")
        self.assertEqual(rows[0]["Y_Judgement"], "")
        self.assertEqual(rows[0]["Z_Timestamp"], "")
        self.assertEqual(rows[1]["Z_Judgement"], "PASS")
        self.assertEqual(self.rows(date(2026, 9, 20))[0]["X_Judgement"], "PASS")
        self.assertNotIn("X_Input_Filename", rows[0])
        self.assertNotIn("X_SN", rows[0])
        self.assertTrue(all(path.read_bytes() == original for path, original in sources.items()))
        self.assertEqual(self.writer.get_statistics()["total"], 6)

    def test_equal_timestamp_uses_last_row(self):
        self.save("0007", "X", "2026-09-19T12:00:00")
        self.save("0007", "X", "2026-09-19T12:00:00", "FAIL")
        self.assertTrue(self.writer.consolidate_previous_days(date(2026, 9, 20)))
        self.assertEqual(self.rows()[0]["X_Judgement"], "FAIL")

    def test_each_measurement_updates_same_day_merged_file_immediately(self):
        day = date(2026, 9, 19)
        self.save("A", "X", "2026-09-19T12:00:00")
        self.assertEqual(self.rows(day)[0]["X_Judgement"], "PASS")
        self.assertEqual(self.rows(day)[0]["Y_Judgement"], "")
        self.save("A_1", "Y", "2026-09-19T13:00:00", "FAIL")
        rows = self.rows(day)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["SN"], "A")
        self.assertEqual(rows[0]["X_Judgement"], "PASS")
        self.assertEqual(rows[0]["Y_Judgement"], "FAIL")

    def test_missing_merged_file_is_regenerated(self):
        day = date(2026, 9, 19)
        self.save("A", "X", "2026-09-19T12:00:00")
        path = self.merged_path(day)
        original = path.read_bytes()
        path.unlink()
        self.assertTrue(self.writer.consolidate_previous_days(day))
        self.assertEqual(path.read_bytes(), original)

    def test_cutoff_includes_today_and_excludes_later_source_files_and_rows(self):
        self.save("A", "X", "2026-09-19T12:00:00")
        future = self.root / "Y" / "260921" / "260921_RANC_Y.csv"
        future.parent.mkdir(parents=True)
        future.write_text("Timestamp,SN,Judgement\n2026-09-21T12:00:00,B,PASS\n", encoding="utf-8")
        source = self.root / "X" / "260919" / "260919_RANC_X.csv"
        with source.open("a", encoding="utf-8", newline="") as stream:
            stream.write("2026-09-21T12:00:00,C,,,,,,PASS,\n")
        self.assertTrue(self.writer.consolidate_previous_days(date(2026, 9, 19)))
        self.assertEqual([row["SN"] for row in self.rows(date(2026, 9, 19))], ["A"])
        self.assertFalse(self.merged_path(date(2026, 9, 21)).exists())

    def test_july_and_august_logs_have_separate_matching_dates(self):
        self.save("ABC", "X", "2026-07-04T12:00:00")
        self.save("ABC_1", "Y", "2026-07-04T13:00:00")
        self.save("ABC_2", "Z", "2026-08-01T12:00:00")
        self.assertTrue(self.writer.consolidate_previous_days(date(2026, 9, 24)))
        for day, present, missing in (("260704", "X", "Z"), ("260801", "Z", "X")):
            path = self.root / "merged" / day / f"{day}_RANC_XYZ.csv"
            with path.open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["SN"], "ABC")
            self.assertEqual(rows[0][f"{present}_Judgement"], "PASS")
            self.assertEqual(rows[0][f"{missing}_Judgement"], "")
        self.assertFalse((self.root / "merged" / "260923").exists())

    def test_numbered_sn_variants_combine_all_axes_in_one_row(self):
        self.save("0001.part", "X", "2026-09-19T12:00:00")
        self.save("0001.part_1", "Y", "2026-09-19T12:00:00")
        self.save("0001.part_2", "Z", "2026-09-19T13:00:00")
        self.save("0001.part_10", "X", "2026-09-19T14:00:00", "FAIL")
        self.save("0001.part_3", "X", "2026-09-19T09:00:00")
        self.assertTrue(self.writer.consolidate_previous_days(date(2026, 9, 20)))
        rows = self.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["SN"], "0001.part")
        self.assertEqual(rows[0]["X_Judgement"], "FAIL")
        self.assertEqual(rows[0]["Y_Judgement"], "PASS")
        self.assertEqual(rows[0]["Z_Judgement"], "PASS")
        self.assertIn("0001.part_10", {row["SN"] for row in self.writer.get_recent_results()})

    def test_sn_non_numeric_suffixes_remain_distinct(self):
        for sn in ("ABC", "ABC_A", "ABC_1A", "ABC-1"):
            self.save(sn, "X", "2026-09-19T12:00:00")
        self.assertTrue(self.writer.consolidate_previous_days(date(2026, 9, 20)))
        self.assertEqual(len(self.rows()), 4)

    def test_old_and_new_schema_merge_same_sn_without_truncating_dots(self):
        (self.root / "X" / "260919_RANC_X.csv").write_text(
            "Timestamp,Input_Filename,Judgement\n"
            "2026-09-19T10:00:00,0001.part.csv,PASS\n", encoding="utf-8",
        )
        self.save("0001.part", "X", "2026-09-19T12:00:00", "FAIL")
        self.assertTrue(self.writer.consolidate_previous_days(date(2026, 9, 20)))
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.rows()[0]["SN"], "0001.part")
        self.assertEqual(self.rows()[0]["X_Judgement"], "FAIL")
        self.assertTrue(all(row["SN"] == "0001.part" for row in self.writer.get_recent_results()))

    def test_failed_header_migration_preserves_file_and_does_not_append(self):
        path = self.root / "X" / "260919" / "260919_RANC_X.csv"
        path.parent.mkdir()
        original = b"Timestamp,Input_Filename,Judgement\n2026-09-19T12:00:00,0001.csv,PASS\n"
        path.write_bytes(original)
        with patch("src.result_writer.os.replace", side_effect=PermissionError("locked")):
            self.assertFalse(self.writer.save_result({
                "input_file": "0002.csv", "timestamp": "2026-09-19T13:00:00",
            }))
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(list(path.parent.glob("*.tmp")), [])

    def test_rollover_restart_and_late_history_write(self):
        self.save("A", "X", "2026-09-19T23:59:59")
        self.assertTrue(self.writer.consolidate_previous_days(date(2026, 9, 19)))
        self.assertEqual(len(self.rows(date(2026, 9, 19))), 1)
        self.assertTrue(self.writer.consolidate_previous_days(date(2026, 9, 20)))
        self.assertEqual(self.writer.merged_file, self.root / "merged" / "260919" / "260919_RANC_XYZ.csv")
        self.assertEqual(len(self.rows()), 1)
        original = (self.writer.merged_file.read_bytes(), self.writer.merged_file.stat().st_mtime_ns)
        self.writer = ResultWriter(self.root)
        self.assertTrue(self.writer.consolidate_previous_days(date(2026, 9, 20)))
        path = self.merged_path(date(2026, 9, 19))
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), original)
        self.save("B", "Y", "2026-09-18T00:00:00")
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), original)
        self.assertTrue(self.writer.consolidate_previous_days(date(2026, 9, 20)))
        self.assertEqual(len(self.rows(date(2026, 9, 19))), 1)
        with (self.root / "merged" / "260918" / "260918_RANC_XYZ.csv").open(encoding="utf-8-sig") as stream:
            self.assertEqual(list(csv.DictReader(stream))[0]["SN"], "B")
        self.assertEqual(len(list((self.root / "merged").rglob("*.csv"))), 2)

    def test_legacy_flat_file_and_missing_optional_columns(self):
        (self.root / "X" / "260919_RANC_X.csv").write_text(
            "Timestamp,Input_Filename,Vrms,Judgement\n"
            "2026-09-19T12:00:00,0001.csv,0.0625,PASS\n", encoding="utf-8-sig",
        )
        self.assertTrue(self.writer.consolidate_previous_days(date(2026, 9, 20)))
        self.assertEqual(self.rows()[0]["SN"], "0001")
        self.assertEqual(self.rows()[0]["X_Noise_Level"], "")

    def test_failed_replace_preserves_previous_output_and_retries(self):
        self.save("A", "X", "2026-09-19T12:00:00")
        original = self.writer.merged_file.read_bytes()
        with patch("src.result_writer.os.replace", side_effect=PermissionError("locked")):
            self.save("B", "Y", "2026-09-19T13:00:00")
        self.assertEqual(self.writer.merged_file.read_bytes(), original)
        self.assertEqual(list((self.root / "merged").rglob("*.tmp")), [])
        with (self.root / "Y" / "260919" / "260919_RANC_Y.csv").open(encoding="utf-8") as stream:
            self.assertEqual([row["SN"] for row in csv.DictReader(stream)], ["B"])
        self.assertTrue(self.writer.consolidate_previous_days(date(2026, 9, 19)))
        self.assertEqual([row["SN"] for row in self.rows(date(2026, 9, 19))], ["A", "B"])

    def test_malformed_log_preserves_previous_output(self):
        self.save("A", "X", "2026-09-18T12:00:00")
        self.assertTrue(self.writer.consolidate_previous_days(date(2026, 9, 19)))
        original = self.writer.merged_file.read_bytes()
        path = self.root / "X" / "260919_RANC_X.csv"
        path.write_text("Timestamp,Input_Filename\ninvalid,A.csv\n", encoding="utf-8")
        self.assertFalse(self.writer.consolidate_previous_days(date(2026, 9, 20)))
        self.assertEqual(self.writer.merged_file.read_bytes(), original)

    def test_clear_removes_merged_and_daily_results(self):
        self.save("A", "X", "2026-09-18T12:00:00")
        self.writer.consolidate_previous_days(date(2026, 9, 19))
        self.writer.consolidate_previous_days(date(2026, 9, 20))
        self.assertEqual(len(list((self.root / "merged").rglob("*.state.json"))), 1)
        self.assertTrue(self.writer.clear_results())
        self.assertFalse(self.writer.merged_file.exists())
        self.assertEqual(list((self.root / "merged").rglob("*.csv")), [])
        self.assertEqual(list((self.root / "merged").rglob("*.state.json")), [])
        self.assertEqual(self.writer._iter_result_files(), [])

    def test_daemon_checks_again_without_input_and_stops(self):
        daemon = AutoInspectorDaemon(self.root / "input", self.root / "output")
        with patch.object(daemon.writer, "consolidate_previous_days", return_value=True) as merge:
            with patch.object(daemon._consolidation_stop, "wait") as wait:
                def advance(_seconds):
                    if wait.call_count == 2:
                        daemon._consolidation_stop.set()
                wait.side_effect = advance
                daemon._consolidation_loop()
        self.assertEqual(merge.call_count, 2)
        wait.assert_called_with(30)

    def test_daemon_starts_merge_worker_and_joins_on_stop(self):
        daemon = AutoInspectorDaemon(self.root / "input", self.root / "output")
        merged = threading.Event()
        with patch("src.integrated_server.FileWatcher"):
            with patch.object(daemon.writer, "consolidate_previous_days", side_effect=merged.set):
                daemon.start()
                try:
                    self.assertTrue(merged.wait(5))
                finally:
                    daemon.stop()
        self.assertFalse(daemon._consolidation_thread.is_alive())

    def test_offsets_compare_actual_time_and_future_files_are_excluded(self):
        self.save("A", "X", "2026-09-18T10:00:00+00:00", "FAIL")
        self.save("A", "X", "2026-09-18T18:00:00+09:00")
        self.save("B", "Y", "2026-09-21T00:00:00")
        self.assertTrue(self.writer.consolidate_previous_days(date(2026, 9, 20)))
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.rows()[0]["X_Judgement"], "FAIL")


if __name__ == "__main__":
    unittest.main()
