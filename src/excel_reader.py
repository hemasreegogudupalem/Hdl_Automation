
from pathlib import Path
import pandas as pd

from src.field_mapper import DEFAULT_ALIASES, build_alias_index, normalize_column_name


def _detect_header_row(path):
    preview = pd.read_excel(path, header=None, nrows=10)
    alias_index = build_alias_index(DEFAULT_ALIASES)
    best_row = 0
    best_match_count = 0

    for row_index, row in preview.iterrows():
        matched_fields = {
            alias_index[normalize_column_name(value)]
            for value in row
            if not pd.isna(value)
            and normalize_column_name(value) in alias_index
        }
        if len(matched_fields) > best_match_count:
            best_row = row_index
            best_match_count = len(matched_fields)

    return best_row if best_match_count >= 2 else 0


def read_excel(file_path):
    """Read an Excel workbook without modifying the original."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Excel file not found: {path.resolve()}"
        )

    if path.suffix.lower() not in (".xlsx", ".xls"):
        raise ValueError(
            "Unsupported file type. Please provide an Excel file."
        )

    df = pd.read_excel(path, header=_detect_header_row(path))

    # Remove completely empty columns from the DataFrame only.
    df = df.dropna(axis=1, how="all")

    # Clean column headings.
    df.columns = [str(column).strip() for column in df.columns]

    print(f"Excel file loaded: {path.name}")
    print(f"Total rows: {len(df)}")
    print(f"Total columns: {len(df.columns)}")
    print("Column names:", df.columns.tolist())

    return df
