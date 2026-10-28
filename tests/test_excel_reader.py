
from src.excel_reader import read_excel
from tabulate import tabulate

file_path = r"input\saudi_employee_data.xlsx"

df = read_excel(file_path)

print("\n========== EMPLOYEE DATA TABLE ==========\n")
print(f"Total employees: {len(df)}")
print(f"Total columns: {len(df.columns)}\n")

# Display a readable table with selected columns
columns_to_show = [
    "Person Number",
    "First Name",
    "Last Name",
    "Sex",
    "Department",
    "Location",
    "Nationality"
]

available_columns = [
    col for col in columns_to_show if col in df.columns
]

print(
    tabulate(
        df[available_columns].head(10),
        headers="keys",
        tablefmt="grid",
        showindex=False
    )
)
