
from pathlib import Path
import pandas as pd


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

    df = pd.read_excel(path)

    # Remove completely empty columns from the DataFrame only.
    df = df.dropna(axis=1, how="all")

    # Clean column headings.
    df.columns = [str(column).strip() for column in df.columns]

    print(f"Excel file loaded: {path.name}")
    print(f"Total rows: {len(df)}")
    print(f"Total columns: {len(df.columns)}")
    print("Column names:", df.columns.tolist())

    return df
