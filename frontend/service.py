"""Frontend Service Layer for Oracle Fusion HCM HDL Automation.

Integrates with existing backend modules (main.py, src/*) without modifying
any backend files.
"""

from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from mysql.connector import Error

# Import unmodified backend modules
from src.dat_generator import generate_hdl_bundle
from src.excel_reader import read_excel
from src.contact_generator import generate_contact_dat
from src.field_mapper import (
    build_alias_index,
    load_field_mappings,
    load_national_identifier_config,
    map_excel_dataframe,
    normalize_column_name,
)
from src.mysql_storage import (
    get_active_clients,
    get_attributes,
    get_connection,
    get_objects,
    get_templates,
    load_settings,
    load_template_configuration,
)
from src.validator import (
    is_empty,
    normalize_national_identifier,
    validate_national_identifier,
)

# Import helper functions and constants from main.py
import main as backend_main


def test_database_connection(settings_path: str = "config/settings.json") -> Dict[str, Any]:
    """Test MySQL connectivity and return detailed status."""
    try:
        settings = load_settings(settings_path)
        db_conf = settings.get("mysql", {})
        connection = get_connection(settings_path)
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT DATABASE() AS db_name, VERSION() AS db_version")
        info = cursor.fetchone() or {}
        cursor.close()
        connection.close()

        templates = get_templates(settings_path)
        clients = get_active_clients(settings_path)

        return {
            "status": "connected",
            "database": info.get("db_name", db_conf.get("database")),
            "version": info.get("db_version"),
            "host": db_conf.get("host"),
            "port": db_conf.get("port", 3306),
            "user": db_conf.get("user"),
            "template_count": len(templates),
            "client_count": len(clients),
            "active_client": clients[0]["client_name"] if clients else "None",
            "source_system_owner": clients[0]["source_system_owner"] if clients else "None",
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "host": "127.0.0.1",
            "database": "hdl_automate",
        }


def get_available_templates(settings_path: str = "config/settings.json") -> List[Dict[str, Any]]:
    """Retrieve all available templates and their objects from MySQL."""
    try:
        templates = get_templates(settings_path)
        catalog = []
        for t in templates:
            t_id = t.get("template_id")
            objects = get_objects(t_id, settings_path) if t_id else []
            catalog.append({
                "template_id": t_id,
                "template_name": t.get("template_name"),
                "output_file_name": t.get("output_file_name"),
                "description": t.get("description"),
                "active": bool(t.get("active")),
                "objects_count": len(objects),
                "objects": [obj.get("object_name") for obj in objects],
            })
        return catalog
    except Exception as exc:
        return []


def get_template_details(template_name: str, settings_path: str = "config/settings.json") -> Dict[str, Any]:
    """Fetch deep structure of a specific template including objects and attributes."""
    try:
        template, objects = load_template_configuration(settings_path, template_name)
    except Exception as exc:
        return {
            "template_name": template_name,
            "output_file_name": f"{template_name}.dat",
            "source_system_owner": "None",
            "description": f"Template configuration: {exc}",
            "objects": [],
            "error": str(exc),
        }

    structured_objects = []
    for obj in objects:
        fields = obj.get("fields", [])
        structured_objects.append({
            "object_name": obj.get("object_name"),
            "attribute_count": len(fields),
            "attributes": [
                {
                    "field_name": f.get("field_name"),
                    "required": bool(f.get("required_flag")),
                    "sequence_no": f.get("sequence_no", 0),
                    "data_type": f.get("data_type", "VARCHAR"),
                }
                for f in fields
            ],
            "mappings_count": len(obj.get("mappings", [])),
        })
    return {
        "template_name": template.get("template_name"),
        "output_file_name": template.get("output_file_name") or template.get("dat_file"),
        "source_system_owner": template.get("source_system_owner"),
        "description": template.get("description"),
        "objects": structured_objects,
        "error": None,
    }


def list_input_files(input_dir: str = "input") -> List[Dict[str, Any]]:
    """List all available Excel files in the input directory."""
    path = Path(input_dir)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)

    files = []
    for f in path.glob("*.*"):
        if f.suffix.lower() in (".xlsx", ".xls"):
            stat = f.stat()
            files.append({
                "filename": f.name,
                "path": str(f.as_posix()),
                "size_kb": round(stat.st_size / 1024, 1),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            })
    files.sort(key=lambda x: x["modified"], reverse=True)
    return files


def inspect_excel_data(
    file_path: str,
    page: int = 1,
    page_size: int = 15,
    search_query: str = "",
) -> Dict[str, Any]:
    """Read Excel workbook and provide rich paginated tabular data."""
    df = read_excel(file_path)
    total_rows = len(df)
    columns = [str(c) for c in df.columns]

    # Convert dataframe to safe records (replace NaN with "")
    df_clean = df.fillna("")

    # Ensure search_query is string
    if not isinstance(search_query, str):
        search_query = ""

    # If search query provided, filter across string representation of rows
    if search_query.strip():
        q = search_query.strip().casefold()
        mask = df_clean.astype(str).apply(lambda row: any(q in cell.casefold() for cell in row), axis=1)
        df_filtered = df_clean[mask]
    else:
        df_filtered = df_clean

    filtered_count = len(df_filtered)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_df = df_filtered.iloc[start_idx:end_idx]

    rows = []
    for idx, row in page_df.iterrows():
        row_dict = {"_row_number": int(idx) + 2}
        for col in columns:
            val = row[col]
            if isinstance(val, (datetime, pd.Timestamp)):
                val = val.strftime("%Y-%m-%d")
            row_dict[col] = str(val) if val is not None else ""
        rows.append(row_dict)

    return {
        "filename": Path(file_path).name,
        "total_rows": total_rows,
        "filtered_rows": filtered_count,
        "total_pages": max(1, (filtered_count + page_size - 1) // page_size),
        "current_page": page,
        "page_size": page_size,
        "columns": columns,
        "rows": rows,
    }


def analyze_field_mappings(
    file_path: str,
    template_name: str = "Worker",
    settings_path: str = "config/settings.json",
) -> Dict[str, Any]:
    """Analyze mappings between the selected Excel file and HDL template objects."""
    template, objects = load_template_configuration(settings_path, template_name)
    df = read_excel(file_path)
    alias_map = load_field_mappings()
    alias_index = build_alias_index(alias_map)

    normalized_columns = {}
    for column in df.columns:
        normalized = normalize_column_name(column)
        normalized_columns[normalized] = column

    mapping_lookup, mapping_report = backend_main._make_mapping_lookup(
        objects,
        normalized_columns,
        alias_index,
    )

    # Summaries
    mapped_count = sum(1 for m in mapping_report if m["status"] == "MAPPED")
    unmapped_count = sum(1 for m in mapping_report if m["status"] == "UNMAPPED")
    type_counts: Dict[str, int] = {}
    for m in mapping_report:
        mtype = m.get("mapping_type") or "NONE"
        type_counts[mtype] = type_counts.get(mtype, 0) + 1

    return {
        "template_name": template["template_name"],
        "excel_file": Path(file_path).name,
        "total_fields": len(mapping_report),
        "mapped_count": mapped_count,
        "unmapped_count": unmapped_count,
        "mapping_types": type_counts,
        "mappings": mapping_report,
    }


def detect_generation_defaults(
    file_path: str,
    template_name: str = "Worker",
    settings_path: str = "config/settings.json",
) -> Dict[str, Any]:
    """Auto-detect common generation parameter values from Excel data."""
    template, _ = load_template_configuration(settings_path, template_name)
    df = read_excel(file_path)
    alias_map = load_field_mappings()
    canonical_rows, _ = map_excel_dataframe(df, alias_map)

    defaults = backend_main._worker_generation_defaults(
        canonical_rows,
        template["source_system_owner"],
    )

    return {
        "legislation_code": defaults.get("legislation_code") or "",
        "legal_employer_name": defaults.get("legal_employer_name") or "",
        "source_system_owner": defaults.get("source_system_owner") or template.get("source_system_owner") or "GRISMO",
    }


def run_hdl_generation_pipeline(
    file_path: str,
    template_name: str = "Worker",
    generation_overrides: Optional[Dict[str, str]] = None,
    settings_path: str = "config/settings.json",
    output_dir: str = "output",
    reports_dir: str = "reports",
) -> Dict[str, Any]:
    """Execute the full HDL generation pipeline faithfully using backend logic."""
    generation_overrides = generation_overrides or {}

    template, objects = load_template_configuration(settings_path, template_name)
    df = read_excel(file_path)
    alias_map = load_field_mappings()
    canonical_rows, _ = map_excel_dataframe(df, alias_map)

    generation_defaults = backend_main._worker_generation_defaults(
        canonical_rows,
        template["source_system_owner"],
    )

    # Merge user overrides with auto-detected defaults
    generation_values = {
        "legislation_code": generation_overrides.get("legislation_code")
        or generation_defaults.get("legislation_code")
        or "",
        "legal_employer_name": generation_overrides.get("legal_employer_name")
        or generation_defaults.get("legal_employer_name")
        or "",
        "source_system_owner": generation_overrides.get("source_system_owner")
        or generation_defaults.get("source_system_owner")
        or template.get("source_system_owner")
        or "",
    }

    identifier_config = load_national_identifier_config()
    alias_index = build_alias_index(alias_map)

    normalized_columns = {}
    for column in df.columns:
        normalized = normalize_column_name(column)
        if normalized in normalized_columns:
            raise ValueError(
                f"Excel columns '{normalized_columns[normalized]}' and "
                f"'{column}' normalize to the same field name."
            )
        normalized_columns[normalized] = column

    mapping_lookup, mapping_report = backend_main._make_mapping_lookup(
        objects,
        normalized_columns,
        alias_index,
    )

    output_objects = [
        {
            "object_name": obj["object_name"],
            "metadata_fields": (
                [field["field_name"] for field in obj["fields"]]
                if (
                    template["template_name"].casefold() == "worker"
                    and obj["object_name"] == "PersonEmail"
                )
                else backend_main.WORKER_METADATA_FIELDS.get(
                    obj["object_name"],
                    [field["field_name"] for field in obj["fields"]],
                ) if template["template_name"].casefold() == "worker" else [
                    field["field_name"] for field in obj["fields"]
                ]
            ),
            "records": [],
        }
        for obj in objects
    ]
    validation_errors = []

    for data_index, (_, row) in enumerate(df.iterrows()):
        row_index = data_index + 2
        email_entries = backend_main._email_entries(
            row,
            normalized_columns,
            alias_index,
        )
        mapped_row_objects = []
        identifier_row = canonical_rows[data_index]
        country_field = identifier_config.get("country_field")
        if is_empty(identifier_row.get(country_field)):
            for country_source in ("Country", "LegislationCode"):
                country_value = identifier_row.get(country_source)
                if not is_empty(country_value):
                    identifier_row = {
                        **identifier_row,
                        country_field: country_value,
                    }
                    break
        row_errors = [
            {
                "ExcelRow": row_index,
                "Object": "",
                "Field": "NationalIdentifierNumber",
                "Error": error,
            }
            for error in validate_national_identifier(
                identifier_row,
                identifier_config,
            )
        ]

        for obj in objects:
            record = {}
            for field in obj["fields"]:
                field_name = field["field_name"]
                mapping = mapping_lookup[(obj["object_name"], field_name)]
                if obj["object_name"] == "PersonEmail" and field_name in {
                    "EmailAddress", "EmailType", "PrimaryFlag"
                }:
                    value = (
                        email_entries[0].get(field_name, "")
                        if email_entries else ""
                    )
                elif mapping and mapping.get("mapping_type") == "GENERATED":
                    value = backend_main._generated_value(
                        field_name,
                        obj["object_name"],
                        canonical_rows[data_index].get("PersonNumber", ""),
                        canonical_rows[data_index],
                        generation_values["source_system_owner"],
                        template["template_name"],
                    )
                else:
                    value = backend_main._map_value(mapping, row, normalized_columns)
                if normalize_column_name(field_name) == "nationalidentifiernumber":
                    value = normalize_national_identifier(value)
                record[field_name] = value

                is_required = backend_main._is_required(field.get("required_flag"))
                output_fields = backend_main.WORKER_METADATA_FIELDS.get(
                    obj["object_name"]
                )
                if (
                    output_fields is not None
                    and field_name not in output_fields
                ):
                    is_required = False
                if mapping and backend_main._is_required(mapping.get("required")):
                    is_required = True

                identifier_may_be_blank = (
                    identifier_config["allow_blank"]
                    and normalize_column_name(field_name)
                    == "nationalidentifiernumber"
                )
                if is_required and not identifier_may_be_blank and (
                    value is None or pd.isna(value) or str(value).strip() == ""
                ):
                    row_errors.append({
                        "ExcelRow": row_index,
                        "Object": obj["object_name"],
                        "Field": field_name,
                        "Error": "Required value is blank.",
                    })

            mapped_row_objects.append(record)

        if row_errors:
            validation_errors.extend(row_errors)
            continue

        source_columns = {
            normalize_column_name(column): value
            for column, value in row.items()
        }
        source_columns["Nationality"] = canonical_rows[data_index].get(
            "Nationality",
            "",
        )
        person_number = canonical_rows[data_index].get("PersonNumber", "")
        for output_obj, record in zip(output_objects, mapped_row_objects):
            if template["template_name"].casefold() == "worker":
                if output_obj["object_name"] == "PersonEmail":
                    for email_entry in email_entries:
                        email_record = {
                            **record,
                            **email_entry,
                        }
                        base_source_id = email_record.get(
                            "SourceSystemId",
                            "",
                        )
                        if base_source_id and len(email_entries) > 1:
                            email_record["SourceSystemId"] = (
                                f"{base_source_id}_"
                                f"{email_entry['EmailType'].casefold()}"
                            )
                        output_obj["records"].append(
                            backend_main._build_worker_metadata_record(
                                output_obj["object_name"],
                                email_record,
                                person_number,
                                generation_values["source_system_owner"],
                                source_columns,
                                template["template_name"],
                                generation_values,
                                output_obj["metadata_fields"],
                            )
                        )
                    continue
                record = backend_main._build_worker_metadata_record(
                    output_obj["object_name"],
                    record,
                    person_number,
                    generation_values["source_system_owner"],
                    source_columns,
                    template["template_name"],
                    generation_values,
                )
            output_obj["records"].append(record)

    dat_name = Path(
        template.get("dat_file")
        or template.get("output_file_name")
        or ""
    ).name
    if not dat_name:
        dat_name = f"{template['template_name'].replace(' ', '_')}.dat"
    if Path(dat_name).suffix.lower() != ".dat":
        raise ValueError(
            f"Template output file must have a .dat extension: {dat_name}"
        )

    out_dir_path = Path(output_dir)
    rep_dir_path = Path(reports_dir)
    out_dir_path.mkdir(parents=True, exist_ok=True)
    rep_dir_path.mkdir(parents=True, exist_ok=True)

    output_file = out_dir_path / dat_name
    generate_hdl_bundle(output_file, output_objects)

    mapping_report_path = rep_dir_path / "mapping_report.xlsx"
    validation_report_path = rep_dir_path / "validation_errors.csv"
    pd.DataFrame(mapping_report).to_excel(mapping_report_path, index=False)
    pd.DataFrame(validation_errors).to_csv(validation_report_path, index=False)

    generated_rows = len(output_objects[0]["records"]) if output_objects else 0
    skipped_rows = len({item["ExcelRow"] for item in validation_errors})

    # Read preview of DAT file
    dat_snippet = []
    if output_file.exists():
        with output_file.open("r", encoding="utf-8") as f:
            for _ in range(60):
                line = f.readline()
                if not line:
                    break
                dat_snippet.append(line.rstrip("\r\n"))

    return {
        "success": True,
        "output_file": str(output_file.as_posix()),
        "output_filename": dat_name,
        "output_file_size_kb": round(output_file.stat().st_size / 1024, 2),
        "total_excel_rows": len(df),
        "generated_rows": generated_rows,
        "skipped_rows": skipped_rows,
        "validation_errors_count": len(validation_errors),
        "validation_errors": validation_errors[:100],  # Return up to first 100 in payload
        "mapping_report_path": str(mapping_report_path.as_posix()),
        "validation_report_path": str(validation_report_path.as_posix()),
        "dat_preview": dat_snippet,
        "generation_values": generation_values,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def list_reports_and_outputs(output_dir: str = "output", reports_dir: str = "reports") -> Dict[str, Any]:
    """Retrieve all generated outputs and reports for management and downloading."""
    out_path = Path(output_dir)
    rep_path = Path(reports_dir)

    outputs = []
    if out_path.exists():
        for f in out_path.glob("*.dat"):
            stat = f.stat()
            outputs.append({
                "filename": f.name,
                "type": "HDL DAT File",
                "size_kb": round(stat.st_size / 1024, 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "path": f"output/{f.name}",
            })

    reports = []
    contact_output_file = None
    if template["template_name"].casefold() == "worker":
        invalid_rows = {
            error["ExcelRow"] - 2
            for error in validation_errors
            if "ExcelRow" in error
        }
        valid_rows = df.iloc[
            [index for index in range(len(df)) if index not in invalid_rows]
        ]
        contact_output_file = generate_contact_dat(
            valid_rows,
            generation_values["source_system_owner"],
            out_dir_path,
        )
    if rep_path.exists():
        for f in rep_path.glob("*.*"):
            if f.suffix.lower() in (".xlsx", ".csv", ".json"):
                stat = f.stat()
                reports.append({
                    "filename": f.name,
                    "type": "Excel Report" if f.suffix.lower() == ".xlsx" else "CSV Report",
                    "size_kb": round(stat.st_size / 1024, 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "path": f"reports/{f.name}",
                })

    outputs.sort(key=lambda x: x["modified"], reverse=True)
    reports.sort(key=lambda x: x["modified"], reverse=True)
    return {"outputs": outputs, "reports": reports}


def read_full_dat_file(filename: str, output_dir: str = "output", max_lines: int = 500) -> Dict[str, Any]:
    """Read contents of an HDL DAT file for interactive browser inspection."""
    file_path = Path(output_dir) / filename
    if not file_path.exists():
        raise FileNotFoundError(f"File {filename} not found in {output_dir}")

    lines = []
        "contact_output_file": (
            str(contact_output_file.as_posix())
            if contact_output_file else None
        ),
    metadata_count = 0
    merge_count = 0
    with file_path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            clean_line = line.rstrip("\r\n")
            if clean_line.startswith("METADATA|"):
                metadata_count += 1
            elif clean_line.startswith("MERGE|"):
                merge_count += 1
            if idx < max_lines:
                lines.append(clean_line)

    return {
        "filename": filename,
        "total_lines_read": len(lines),
        "metadata_lines": metadata_count,
        "merge_lines": merge_count,
        "has_more": (metadata_count + merge_count) > max_lines,
        "lines": lines,
    }


def read_report_csv(
    filename: str,
    reports_dir: str = "reports",
    max_rows: int = 150,
) -> Dict[str, Any]:
    """Read a CSV report (e.g. validation_errors.csv) for interactive preview."""
    file_path = Path(reports_dir) / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Report file {filename} not found in {reports_dir}")

    if file_path.stat().st_size == 0:
        return {
            "filename": filename,
            "total_rows": 0,
            "columns": ["ExcelRow", "Object", "Field", "Error"],
            "rows": [],
        }

    try:
        df = pd.read_csv(file_path)
    except pd.errors.EmptyDataError:
        return {
            "filename": filename,
            "total_rows": 0,
            "columns": ["ExcelRow", "Object", "Field", "Error"],
            "rows": [],
        }
    except Exception as exc:
        raise ValueError(f"Failed to read CSV report: {exc}")

    total_rows = len(df)
    columns = [str(c) for c in df.columns]
    rows = df.head(max_rows).fillna("").to_dict(orient="records")

    return {
        "filename": filename,
        "total_rows": total_rows,
        "columns": columns,
        "rows": rows,
    }


def read_report_excel(
    filename: str,
    reports_dir: str = "reports",
    max_rows: int = 250,
) -> Dict[str, Any]:
    """Read an Excel report (e.g. mapping_report.xlsx) for interactive preview."""
    file_path = Path(reports_dir) / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Report file {filename} not found in {reports_dir}")

    try:
        df = pd.read_excel(file_path)
    except Exception as exc:
        raise ValueError(f"Failed to read Excel report: {exc}")

    total_rows = len(df)
    columns = [str(c) for c in df.columns]
    rows = df.head(max_rows).fillna("").to_dict(orient="records")

    return {
        "filename": filename,
        "total_rows": total_rows,
        "columns": columns,
        "rows": rows,
    }
