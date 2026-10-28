import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.excel_reader import read_excel
from src.field_mapper import load_field_mappings, map_excel_dataframe
from src.validator import format_hdl_date


class ExcelReaderHeaderDetectionTests(unittest.TestCase):
    def test_detects_bulk_headers_after_a_title_row_and_maps_date_of_birth(self):
        rows = [
            ["Add Employee Personal Details", None, None],
            ["Employee Number *", "Date Of Birth", "Date Joined *"],
            ["EMP001", "1990-04-03", "2020-01-15"],
        ]
        workbook = pd.DataFrame(rows)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bulk.xlsx"
            workbook.to_excel(path, header=False, index=False)
            dataframe = read_excel(path)

        self.assertIn("Date Of Birth", dataframe.columns)
        self.assertEqual(len(dataframe), 1)

        canonical_rows, _ = map_excel_dataframe(
            dataframe,
            load_field_mappings(),
        )
        self.assertEqual(
            format_hdl_date(canonical_rows[0]["DateOfBirth"]),
            "1990/04/03",
        )


if __name__ == "__main__":
    unittest.main()
