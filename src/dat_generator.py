from pathlib import Path
import pandas as pd

from src.validator import format_hdl_date, is_empty


def _format_hdl_value(field, value):
    normalized_field = "".join(
        character for character in str(field).casefold()
        if character.isalnum()
    )
    if "date" in normalized_field:
        return format_hdl_date(value)
    if is_empty(value):
        return ""
    return str(value).strip()


def normalize_name(value):
    """
    Normalize names/IDs for matching.
    Example:
        'Ankur Saxena' -> 'ankursaxena'
    """

    if pd.isna(value):
        return ""

    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
    )


def generate_hdl_bundle(output_file, output_objects):
    """Write mapped HDL objects and their records to one DAT file."""
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    lines = []

    for output_obj in output_objects:
        object_name = output_obj["object_name"]
        fields = output_obj["metadata_fields"]
        lines.append(
            "METADATA|" + object_name + "|" + "|".join(fields)
        )

        for record in output_obj["records"]:
            values = []
            for field in fields:
                values.append(
                    _format_hdl_value(field, record.get(field, ""))
                )
            lines.append(
                "MERGE|" + object_name + "|" + "|".join(values)
            )

    output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_file


def generate_assignment_supervisor(df, output_dir):
    """
    Generate AssignmentSupervisor.dat.

    Expected client columns:
        Employee Number
        Full Name
        Reporting To

    Example output:

    METADATA|AssignmentSupervisor|PersonNumber|ManagerName
    MERGE|AssignmentSupervisor|GS_1099|Ankur Saxena
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # ---------------------------------------------------------
    # Find required Excel columns
    # ---------------------------------------------------------

    employee_column = None
    name_column = None
    reporting_column = None

    for column in df.columns:

        normalized = normalize_name(column)

        if normalized in {
            "employeenumber",
            "employeeid",
            "employeecode"
        }:
            employee_column = column

        elif normalized in {
            "fullname",
            "employeename"
        }:
            name_column = column

        elif normalized in {
            "reportingto",
            "manager",
            "reportingmanager"
        }:
            reporting_column = column

    # ---------------------------------------------------------
    # Validate columns
    # ---------------------------------------------------------

    missing = []

    if employee_column is None:
        missing.append("Employee Number")

    if name_column is None:
        missing.append("Full Name")

    if reporting_column is None:
        missing.append("Reporting To")

    if missing:

        raise ValueError(
            "AssignmentSupervisor requires columns: "
            + ", ".join(missing)
        )

    # ---------------------------------------------------------
    # Create employee lookup
    #
    # Full Name -> Employee Number
    # ---------------------------------------------------------

    employee_lookup = {}

    for _, row in df.iterrows():

        employee_name = row[name_column]
        employee_number = row[employee_column]

        name_key = normalize_name(
            employee_name
        )

        if name_key and not pd.isna(employee_number):

            employee_lookup[name_key] = str(
                employee_number
            ).strip()

    # ---------------------------------------------------------
    # Metadata
    # ---------------------------------------------------------

    lines = []

    lines.append(
        "METADATA|AssignmentSupervisor|"
        "PersonNumber|ManagerName"
    )

    # ---------------------------------------------------------
    # Generate MERGE records
    # ---------------------------------------------------------

    for _, row in df.iterrows():

        reporting_to = row[reporting_column]

        if pd.isna(reporting_to):
            continue

        manager_name = str(
            reporting_to
        ).strip()

        if not manager_name:
            continue

        # Find manager's Employee Number
        manager_key = normalize_name(
            manager_name
        )

        manager_employee_number = (
            employee_lookup.get(
                manager_key
            )
        )

        # -----------------------------------------------------
        # Manager not found
        # -----------------------------------------------------

        if manager_employee_number is None:

            print(
                f"WARNING: Manager "
                f"'{manager_name}' "
                f"not found in employee data."
            )

            continue

        # -----------------------------------------------------
        # Generate requested format
        # -----------------------------------------------------

        lines.append(
            "MERGE|AssignmentSupervisor|"
            f"{manager_employee_number}|"
            f"{manager_name}"
        )

    # ---------------------------------------------------------
    # Write file
    # ---------------------------------------------------------

    output_file = (
        output_dir /
        "AssignmentSupervisor.dat"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "\n".join(lines)
        )

        file.write("\n")

    print(
        f"\nCreated: {output_file}"
    )

    return output_file


# =============================================================
# GENERIC DAT GENERATOR
# =============================================================

def generate_dat_files(
    df,
    mapping_config,
    settings,
    output_dir
):
    """
    Generate all HDL files.

    AssignmentSupervisor is handled separately because
    Reporting To requires employee relationship lookup.
    """

    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # ---------------------------------------------------------
    # Assignment Supervisor
    # ---------------------------------------------------------

    generate_assignment_supervisor(
        df,
        output_dir
    )

    # ---------------------------------------------------------
    # Other DAT files
    # ---------------------------------------------------------

    if isinstance(mapping_config, dict):

        mappings = mapping_config.get(
            "mappings",
            []
        )

    elif isinstance(mapping_config, list):

        mappings = mapping_config

    else:

        mappings = []

    # Group mappings by DAT file
    dat_groups = {}

    for mapping in mappings:

        if not isinstance(mapping, dict):
            continue

        dat_file = (
            mapping.get("dat_file")
            or mapping.get("business_object")
            or mapping.get("template")
        )

        if not dat_file:
            continue

        # AssignmentSupervisor already handled above
        if (
            "assignmentsupervisor"
            in str(dat_file).lower()
        ):
            continue

        dat_file = str(dat_file)

        if not dat_file.lower().endswith(".dat"):
            dat_file += ".dat"

        dat_groups.setdefault(
            dat_file,
            []
        ).append(mapping)

    # ---------------------------------------------------------
    # Generate other DAT files
    # ---------------------------------------------------------

    for dat_file, file_mappings in dat_groups.items():

        output_file = (
            output_dir /
            dat_file
        )

        hdl_fields = []

        for mapping in file_mappings:

            hdl_field = (
                mapping.get("hdl_field")
                or mapping.get("target")
            )

            if hdl_field:
                hdl_fields.append(
                    str(hdl_field)
                )

        if not hdl_fields:
            continue

        business_object = dat_file.replace(
            ".dat",
            ""
        )

        lines = []

        # Metadata
        lines.append(
            "METADATA|"
            + business_object
            + "|"
            + "|".join(hdl_fields)
        )

        # Data
        for _, row in df.iterrows():

            values = []

            for mapping in file_mappings:

                excel_column = (
                    mapping.get("excel_column")
                    or mapping.get("source")
                    or mapping.get("client_field")
                )

                if not excel_column:

                    values.append("")

                    continue

                actual_column = None

                for column in df.columns:

                    if (
                        normalize_name(column)
                        ==
                        normalize_name(
                            excel_column
                        )
                    ):
                        actual_column = column
                        break

                if actual_column is None:

                    values.append("")

                    continue

                value = row[
                    actual_column
                ]

                hdl_field = (
                    mapping.get("hdl_field")
                    or mapping.get("target")
                    or ""
                )

                values.append(
                    _format_hdl_value(hdl_field, value)
                )

            lines.append(
                "MERGE|"
                + "|".join(values)
            )

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                "\n".join(lines)
            )

            file.write("\n")

        print(
            f"Created: {output_file}"
        )