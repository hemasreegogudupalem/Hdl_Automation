
import argparse
import re
from pathlib import Path

import pandas as pd
from mysql.connector import Error

from src.dat_generator import generate_hdl_bundle
from src.excel_reader import read_excel
from src.field_mapper import (
    build_alias_index,
    load_field_mappings,
    load_national_identifier_config,
    map_excel_dataframe,
    normalize_column_name,
)
from src.mysql_storage import load_template_configuration
from src.validator import (
    is_empty,
    normalize_national_identifier,
    validate_national_identifier,
)


SUPPORTED_MAPPING_TYPES = {
    "",
    "COLUMN",
    "DIRECT",
    "EXCEL",
    "DEFAULT",
    "CONSTANT",
    "STATIC",
    "DERIVED",
    "GENERATED",
}

PREFERRED_SOURCE_COLUMNS = {
    "StartDate": "Start Date",
    "EffectiveStartDate": "Start Date",
    "DateStart": "Start Date",
    "EmailAddress": "Work Email",
    "PhoneNumber": "Work Phone Number",
    "CountryCodeNumber": "Work Dial Code",
    "WorkerType": "Worker Type",
    "TownOrCity": "Location",
}

DEFAULT_FIELD_VALUES = {
    "NameType": "GLOBAL",
    "EmailType": "W1",
    "PhoneType": "W1",
    "AddressType": "HOME",
    "AssignmentStatusType": "ACTIVE_PROCESS",
}

COUNTRY_HDL_VALUES = {
    "saudiarabian": {
        "country": "SA",
        "legislation": "SAU",
        "identifier_type": "National ID",
    },
    "saudiarabia": {
        "country": "SA",
        "legislation": "SAU",
        "identifier_type": "National ID",
    },
    "india": {
        "country": "IN",
        "legislation": "IND",
        "identifier_type": "Aadhaar",
    },
    "indian": {
        "country": "IN",
        "legislation": "IND",
        "identifier_type": "Aadhaar",
    },
}

WORKER_METADATA_FIELDS = {
    "Worker": [
        "EffectiveStartDate",
        "PersonNumber",
        "StartDate",
        "DateOfBirth",
        "ActionCode",
        "SourceSystemId",
        "SourceSystemOwner",
    ],
    "PersonName": [
        "EffectiveStartDate",
        "PersonId(SourceSystemId)",
        "NameType",
        "LegislationCode",
        "Title",
        "FirstName",
        "MiddleNames",
        "LastName",
        "SourceSystemId",
        "SourceSystemOwner",
    ],
    "PersonNationalIdentifier": [
        "PersonNumber",
        "LegislationCode",
        "NationalIdentifierType",
        "NationalIdentifierNumber",
        "PersonId(SourceSystemId)",
        "PrimaryFlag",
        "SourceSystemId",
        "SourceSystemOwner",
    ],
    "PersonEmail": [
        "PersonNumber",
        "DateFrom",
        "DateTo",
        "EmailType",
        "EmailAddress",
        "SourceSystemOwner",
        "SourceSystemId",
    ],
    "PersonPhone": [
        "PhoneType",
        "PersonNumber",
        "DateFrom",
        "LegislationCode",
        "PhoneNumber",
        "PrimaryFlag",
        "SourceSystemId",
        "SourceSystemOwner",
    ],
    "PersonAddress": [
        "EffectiveStartDate",
        "EffectiveEndDate",
        "AddressType",
        "PersonId(SourceSystemId)",
        "AddressLine1",
        "AddressLine2",
        "AddressLine3",
        "AddressLine4",
        "Building",
        "FloorNumber",
        "TownOrCity",
        "Region1",
        "Region2",
        "Region3",
        "Country",
        "PostalCode",
        "SourceSystemId",
        "SourceSystemOwner",
    ],
    "PersonLegislativeData": [
        "EffectiveStartDate",
        "PersonId(SourceSystemId)",
        "LegislationCode",
        "Sex",
        "MaritalStatus",
        "SourceSystemId",
        "SourceSystemOwner",
    ],
    "WorkRelationship": [
        "PersonId(SourceSystemId)",
        "LegalEmployerName",
        "DateStart",
        "WorkerType",
        "PrimaryFlag",
        "SourceSystemId",
        "SourceSystemOwner",
    ],
    "WorkTerms": [
        "PeriodOfServiceId(SourceSystemId)",
        "PersonId(SourceSystemId)",
        "ActionCode",
        "EffectiveStartDate",
        "EffectiveSequence",
        "EffectiveLatestChange",
        "AssignmentNumber",
        "PrimaryWorkTermsFlag",
        "AssignmentType",
        "SourceSystemId",
        "SourceSystemOwner",
    ],
    "Assignment": [
        "PeriodOfServiceId(SourceSystemId)",
        "PersonId(SourceSystemId)",
        "ActionCode",
        "EffectiveStartDate",
        "EffectiveSequence",
        "EffectiveLatestChange",
        "WorkTermsAssignmentId(SourceSystemId)",
        "AssignmentNumber",
        "AssignmentStatusTypeCode",
        "PersonTypeCode",
        "BusinessUnitShortCode",
        "PrimaryFlag",
        "PrimaryAssignmentFlag",
        "AssignmentCategory",
        "DepartmentName",
        "FullPartTime",
        "LocationCode",
        "WorkTermsNumber",
        "AssignmentType",
        "WorkerCategory",
        "JobCode",
        "SourceSystemId",
        "SourceSystemOwner",
    ],
}

WORKER_METADATA_SOURCE_COLUMNS = {
    "Title": ("Title",),
    "JobCode": ("Job Code", "Job ID"),
    "WorkerCategory": ("Worker Category",),
    "FullPartTime": ("Full Part Time", "Full/Part Time"),
    "AssignmentCategory": ("Assignment Category",),
    "AssignmentType": ("Assignment Type",),
    "PersonTypeCode": ("Person Type Code",),
    "BusinessUnitShortCode": ("Business Unit Short Code",),
    "WorkTermsNumber": ("Work Terms Number",),
    "AddressLine3": ("Address Line 3",),
    "AddressLine4": ("Address Line 4",),
    "Building": ("Building",),
    "FloorNumber": ("Floor Number",),
    "Region2": ("Region 2",),
    "Region3": ("Region 3",),
}

WORKER_METADATA_DEFAULTS = {
    "PrimaryFlag": "Y",
    "PrimaryAssignmentFlag": "Y",
    "PrimaryWorkTermsFlag": "Y",
    "EffectiveSequence": "1",
    "EffectiveLatestChange": "Y",
}

WORKER_OBJECT_ID_PREFIXES = {
    "Worker": "wor",
    "PersonName": "pn",
    "PersonNationalIdentifier": "pni",
    "PersonEmail": "PE",
    "PersonPhone": "pp",
    "PersonAddress": "pa",
    "PersonLegislativeData": "pld",
    "WorkRelationship": "wr",
    "WorkTerms": "wt",
    "Assignment": "asg",
}


def _is_required(value):
    return value is True or str(value).strip().lower() in {
        "1", "true", "yes", "y", "required"
    }


def _worker_generation_defaults(canonical_rows, source_system_owner):
    """Derive prompt defaults when Excel contains one unambiguous value."""
    defaults = {"source_system_owner": source_system_owner}

    for field_name, key in (("LegalEmployerName", "legal_employer_name"),):
        values = {
            str(row[field_name]).strip()
            for row in canonical_rows
            if field_name in row and not is_empty(row[field_name])
        }
        if len(values) != 1:
            defaults[key] = ""
            continue

        defaults[key] = next(iter(values))

    legislation_codes = {
        str(row["LegislationCode"]).strip()
        for row in canonical_rows
        if "LegislationCode" in row and not is_empty(row["LegislationCode"])
    }
    if len(legislation_codes) == 1:
        defaults["legislation_code"] = next(iter(legislation_codes))
    else:
        nationalities = {
            str(row["Nationality"]).strip()
            for row in canonical_rows
            if "Nationality" in row and not is_empty(row["Nationality"])
        }
        if len(nationalities) == 1:
            try:
                defaults["legislation_code"] = _country_hdl_value(
                    "LegislationCode",
                    next(iter(nationalities)),
                )
            except ValueError:
                defaults["legislation_code"] = ""
        else:
            defaults["legislation_code"] = ""

    return defaults


def prompt_worker_generation_values(input_func=input, defaults=None):
    """Ask for common HDL values, accepting unambiguous input defaults."""
    defaults = defaults or {}
    prompts = (
        ("legislation_code", "Legislation code"),
        ("legal_employer_name", "Legal employer name"),
        ("source_system_owner", "Source system owner"),
    )
    values = {}

    for key, label in prompts:
        while True:
            default = str(defaults.get(key, "") or "").strip()
            suffix = f" [{default}]" if default else ""
            value = input_func(f"{label}{suffix}: ").strip()
            if value:
                values[key] = value
                break
            if default:
                values[key] = default
                break
            print(f"{label} is required.")

    return values


def _source_column_for_field(field_name, normalized_columns, alias_index):
    preferred_column = PREFERRED_SOURCE_COLUMNS.get(field_name)
    preferred_columns = [preferred_column] if preferred_column else []
    if field_name == "EmailAddress":
        preferred_columns.extend(("Official Email", "Email Address", "Email"))
    fallback_fields = {
        "EffectiveStartDate": ("StartDate",),
        "DateStart": ("StartDate",),
    }

    for fallback_field in fallback_fields.get(field_name, ()):
        preferred_columns.extend(
            column
            for normalized, column in normalized_columns.items()
            if alias_index and alias_index.get(normalized) == fallback_field
        )

    for column in preferred_columns:
        normalized = normalize_column_name(column)
        if normalized in normalized_columns:
            return normalized_columns[normalized]

    matching_columns = [
        column
        for normalized, column in normalized_columns.items()
        if alias_index and alias_index.get(normalized) == field_name
    ]
    return matching_columns[0] if len(matching_columns) == 1 else None


def _make_mapping_lookup(objects, normalized_columns, alias_index=None):
    lookup = {}
    report = []

    for obj in objects:
        mappings_by_field = {}
        output_fields = WORKER_METADATA_FIELDS.get(obj["object_name"])

        for mapping in obj["mappings"]:
            field_name = mapping["field_name"]
            mappings_by_field.setdefault(field_name, []).append(mapping)

            mapping_type = str(mapping.get("mapping_type") or "").strip().upper()
            if mapping_type not in SUPPORTED_MAPPING_TYPES:
                raise ValueError(
                    f"Unsupported mapping type '{mapping_type}' for "
                    f"{obj['object_name']}.{field_name}."
                )

            excel_column = mapping.get("excel_column")
            if (
                excel_column
                and normalize_column_name(excel_column) not in normalized_columns
                and alias_index
                and (
                    normalize_column_name(field_name)
                    == "nationalidentifiernumber"
                    or alias_index.get(normalize_column_name(excel_column))
                    == "NationalIdentifierNumber"
                )
            ):
                identifier_columns = [
                    column
                    for column in normalized_columns.values()
                    if alias_index.get(normalize_column_name(column))
                    == "NationalIdentifierNumber"
                ]
                if len(identifier_columns) > 1:
                    raise ValueError(
                        "Multiple Excel columns match NationalIdentifierNumber: "
                        + ", ".join(identifier_columns)
                    )
                if identifier_columns:
                    mapping = {
                        **mapping,
                        "excel_column": identifier_columns[0],
                    }
                    mappings_by_field[field_name][-1] = mapping
                    excel_column = identifier_columns[0]

            if (
                excel_column
                and mapping_type not in {"DEFAULT", "CONSTANT", "STATIC"}
                and normalize_column_name(excel_column) not in normalized_columns
            ):
                source_column = _source_column_for_field(
                    field_name,
                    normalized_columns,
                    alias_index,
                )
                if source_column:
                    mapping = {
                        **mapping,
                        "excel_column": source_column,
                    }
                    mappings_by_field[field_name][-1] = mapping
                elif (
                    output_fields is not None
                    and field_name not in output_fields
                ):
                    mapping = None
                    mappings_by_field[field_name][-1] = mapping
                elif not _is_required(next(
                    (
                        field.get("required_flag")
                        for field in obj["fields"]
                        if field["field_name"] == field_name
                    ),
                    0,
                )):
                    mapping = None
                    mappings_by_field[field_name][-1] = mapping
                else:
                    raise ValueError(
                        f"Database mapping for {obj['object_name']}.{field_name} "
                        f"expects Excel column '{excel_column}', but that column "
                        "was not found in the workbook."
                    )

        for field in obj["fields"]:
            field_name = field["field_name"]
            matches = mappings_by_field.get(field_name, [])
            if len(matches) > 1:
                raise ValueError(
                    f"Multiple active mappings found for "
                    f"{obj['object_name']}.{field_name}."
                )

            mapping = matches[0] if matches else None
            if mapping is None:
                source_column = _source_column_for_field(
                    field_name,
                    normalized_columns,
                    alias_index,
                )
                if source_column:
                    mapping = {
                        "field_name": field_name,
                        "excel_column": source_column,
                        "mapping_type": "DIRECT",
                        "required": field.get("required_flag"),
                    }
                elif field_name in DEFAULT_FIELD_VALUES:
                    mapping = {
                        "field_name": field_name,
                        "mapping_type": "DEFAULT",
                        "default_value": DEFAULT_FIELD_VALUES[field_name],
                        "required": field.get("required_flag"),
                    }
                elif field_name in {
                    "Country",
                    "LegislationCode",
                    "NationalIdentifierType",
                    "SourceSystemOwner",
                    "SourceSystemId",
                    "AssignmentNumber",
                }:
                    mapping = {
                        "field_name": field_name,
                        "mapping_type": "GENERATED",
                        "required": field.get("required_flag"),
                    }

            is_output_field = (
                output_fields is None or field_name in output_fields
            )
            if (
                mapping is None
                and is_output_field
                and _is_required(field.get("required_flag"))
            ):
                raise ValueError(
                    f"Required field {obj['object_name']}.{field_name} "
                    "has no active database mapping."
                )

            lookup[(obj["object_name"], field_name)] = mapping
            report.append({
                "object_name": obj["object_name"],
                "field_name": field_name,
                "excel_column": (
                    mapping.get("excel_column") if mapping else ""
                ),
                "mapping_type": (
                    mapping.get("mapping_type") if mapping else ""
                ),
                "default_value": (
                    mapping.get("default_value") if mapping else ""
                ),
                "status": "MAPPED" if mapping else "UNMAPPED",
            })

    return lookup, report


def _country_hdl_value(field_name, nationality):
    country_key = normalize_column_name(nationality)
    country_values = COUNTRY_HDL_VALUES.get(country_key)
    if country_values is None:
        raise ValueError(
            f"No HDL country values are configured for nationality "
            f"'{nationality}'."
        )

    field_values = {
        "Country": country_values["country"],
        "LegislationCode": country_values["legislation"],
        "NationalIdentifierType": country_values["identifier_type"],
    }
    return field_values[field_name]


def _email_entries(row, normalized_columns, alias_index):
    """Return one typed email record for each populated email source column."""
    entries = []
    seen = set()
    explicit_email_type = ""
    for normalized_column, column in normalized_columns.items():
        if (
            alias_index.get(normalized_column) == "EmailType"
            and not is_empty(row[column])
        ):
            explicit_email_type = str(row[column]).strip()
            break

    for normalized_column, column in normalized_columns.items():
        if alias_index.get(normalized_column) != "EmailAddress":
            continue

        value = row[column]
        if is_empty(value):
            continue

        if "personal" in normalized_column or "home" in normalized_column:
            email_type = "H1"
        elif "work" in normalized_column or "official" in normalized_column:
            email_type = "W1"
        else:
            email_type = explicit_email_type or "W1"

        address = str(value).strip()
        key = (email_type, address.casefold())
        if key in seen:
            continue
        seen.add(key)
        entries.append({
            "EmailAddress": address,
            "EmailType": email_type,
        })

    if not entries:
        return []

    preferred = next(
        (
            entry for entry in entries
            if entry["EmailType"].strip().casefold() in {"w1", "work"}
        ),
        entries[0],
    )
    for entry in entries:
        entry["PrimaryFlag"] = "Y" if entry is preferred else "N"

    return entries


def _worker_person_number_suffix(person_number):
    return re.sub(
        r"^(?:[A-Za-z]{2})?EMP",
        "",
        str(person_number).strip(),
        flags=re.IGNORECASE,
    )


def _worker_source_system_id(object_name, person_number):
    template_prefix = WORKER_OBJECT_ID_PREFIXES.get(
        object_name,
        "".join(
            character
            for character in str(object_name).casefold()
            if character.isalpha()
        )[:3],
    )
    return f"{template_prefix}_{_worker_person_number_suffix(person_number)}"


def _worker_assignment_number(object_name, person_number):
    if not person_number:
        return ""
    prefix = {
        "WorkTerms": "ET",
        "Assignment": "E",
    }.get(object_name)
    if not prefix:
        return ""
    return f"{prefix}{_worker_person_number_suffix(person_number)}"


def _generated_value(
    field_name,
    object_name,
    person_number,
    row,
    source_owner,
    template_name="Worker",
):
    if field_name == "SourceSystemOwner":
        return source_owner
    if field_name == "SourceSystemId":
        return (
            _worker_source_system_id(object_name, person_number)
            if person_number else ""
        )
    if field_name == "AssignmentNumber":
        return _worker_assignment_number(object_name, person_number)
    if field_name in {"Country", "LegislationCode", "NationalIdentifierType"}:
        return _country_hdl_value(field_name, row.get("Nationality"))
    return ""


def _build_worker_metadata_record(
    object_name,
    record,
    person_number,
    source_owner,
    source_columns,
    template_name="Worker",
    generation_values=None,
    metadata_fields=None,
):
    generation_values = generation_values or {}
    worker_source_id = _worker_source_system_id(
        "Worker",
        person_number,
    )
    metadata_record = {}

    for field_name in metadata_fields or WORKER_METADATA_FIELDS[object_name]:
        if field_name == "PersonId(SourceSystemId)":
            value = worker_source_id
        elif field_name == "PeriodOfServiceId(SourceSystemId)":
            value = _worker_source_system_id("WorkRelationship", person_number)
        elif field_name == "WorkTermsAssignmentId(SourceSystemId)":
            value = _worker_source_system_id("WorkTerms", person_number)
        elif field_name == "SourceSystemId":
            value = _worker_source_system_id(object_name, person_number)
        elif field_name == "AssignmentNumber" and object_name in {
            "WorkTerms",
            "Assignment",
        }:
            value = _worker_assignment_number(object_name, person_number)
        elif field_name == "WorkTermsNumber" and object_name == "Assignment":
            value = _worker_assignment_number("WorkTerms", person_number)
        elif field_name == "AssignmentType" and object_name in {
            "WorkTerms",
            "Assignment",
        }:
            value = "ET" if object_name == "WorkTerms" else "E"
        elif field_name == "JobCode" and object_name == "Assignment":
            value = source_columns.get(normalize_column_name("JobCode"), "")
        elif field_name in WORKER_METADATA_DEFAULTS:
            value = record.get(field_name, "")
            if is_empty(value):
                value = WORKER_METADATA_DEFAULTS[field_name]
        elif field_name == "SourceSystemOwner":
            value = generation_values.get("source_system_owner", source_owner)
        elif field_name == "AssignmentStatusTypeCode":
            value = record.get(field_name, "")
            if is_empty(value):
                value = record.get("AssignmentStatusType", "")
            if str(value).strip().upper() == "ACTIVE":
                value = "ACTIVE_PROCESS"
        elif field_name == "DateFrom":
            value = record.get(field_name, "")
            if is_empty(value):
                value = source_columns.get(normalize_column_name("Start Date"), "")
        elif field_name in {"Country", "LegislationCode", "NationalIdentifierType"}:
            if field_name == "LegislationCode" and generation_values.get(
                "legislation_code"
            ):
                value = generation_values["legislation_code"]
            else:
                value = record.get(field_name, "")
            if is_empty(value):
                nationality = source_columns.get("Nationality", "")
                value = _country_hdl_value(field_name, nationality)
        else:
            value = record.get(field_name, "")
            if (
                field_name == "LegalEmployerName"
                and generation_values.get("legal_employer_name")
            ):
                value = generation_values["legal_employer_name"]
            if is_empty(value):
                for source_column in WORKER_METADATA_SOURCE_COLUMNS.get(
                    field_name, (field_name,)
                ):
                    normalized_source = normalize_column_name(source_column)
                    if normalized_source in source_columns:
                        value = source_columns[normalized_source]
                        break

        metadata_record[field_name] = value

    return metadata_record


def _map_value(mapping, row, normalized_columns):
    if mapping is None:
        return ""

    mapping_type = str(mapping.get("mapping_type") or "").strip().upper()
    if mapping_type in {"DEFAULT", "CONSTANT", "STATIC"}:
        return mapping.get("default_value") or ""

    excel_column = mapping.get("excel_column")
    if excel_column:
        column = normalize_column_name(excel_column)
        if column in normalized_columns:
            return row[normalized_columns[column]]

    return mapping.get("default_value") or ""


def main():
    parser = argparse.ArgumentParser(
        description="Generate Oracle Fusion HDL files using MySQL templates"
    )
    parser.add_argument(
        "--input",
        default="input/saudi_employee_data.xlsx",
        help=(
            "Path to the source Excel workbook "
            "(default: input/saudi_employee_data.xlsx)"
        )
    )
    parser.add_argument(
        "--settings",
        default="config/settings.json",
        help="Path to MySQL settings JSON"
    )
    parser.add_argument(
        "--template",
        help="Active database template name (defaults to first active template)"
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory for generated HDL files"
    )
    parser.add_argument(
        "--reports-dir",
        default="reports",
        help="Directory for mapping and validation reports"
    )
    args = parser.parse_args()

    try:
        template, objects = load_template_configuration(
            args.settings,
            args.template
        )
    except (Error, FileNotFoundError, ValueError) as exc:
        raise SystemExit(f"Could not load HDL template from MySQL: {exc}") from exc

    print(f"MySQL connected; using template: {template['template_name']}")

    df = read_excel(args.input)
    alias_map = load_field_mappings()
    canonical_rows, _ = map_excel_dataframe(df, alias_map)
    generation_defaults = _worker_generation_defaults(
        canonical_rows,
        template["source_system_owner"],
    )
    generation_values = prompt_worker_generation_values(
        defaults=generation_defaults,
    )
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
    try:
        mapping_lookup, mapping_report = _make_mapping_lookup(
            objects,
            normalized_columns,
            alias_index
        )
    except ValueError as exc:
        raise SystemExit(f"Could not map HDL template: {exc}") from exc

    output_objects = [
        {
            "object_name": obj["object_name"],
            "metadata_fields": (
                [field["field_name"] for field in obj["fields"]]
                if (
                    template["template_name"].casefold() == "worker"
                    and obj["object_name"] == "PersonEmail"
                )
                else WORKER_METADATA_FIELDS.get(
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
        email_entries = _email_entries(
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
                    value = _generated_value(
                        field_name,
                        obj["object_name"],
                        canonical_rows[data_index].get("PersonNumber", ""),
                        canonical_rows[data_index],
                        generation_values["source_system_owner"],
                        template["template_name"],
                    )
                else:
                    value = _map_value(mapping, row, normalized_columns)
                if normalize_column_name(field_name) == "nationalidentifiernumber":
                    value = normalize_national_identifier(value)
                record[field_name] = value

                is_required = _is_required(field.get("required_flag"))
                output_fields = WORKER_METADATA_FIELDS.get(
                    obj["object_name"]
                )
                if (
                    output_fields is not None
                    and field_name not in output_fields
                ):
                    is_required = False
                if mapping and _is_required(mapping.get("required")):
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
        source_columns[normalize_column_name("JobCode")] = (
            canonical_rows[data_index].get("JobCode", "")
        )
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
                            _build_worker_metadata_record(
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
                record = _build_worker_metadata_record(
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

    output_file = Path(args.output_dir) / dat_name
    report_dir = Path(args.reports_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    generate_hdl_bundle(output_file, output_objects)
    mapping_report_path = report_dir / "mapping_report.xlsx"
    validation_report_path = report_dir / "validation_errors.csv"
    pd.DataFrame(mapping_report).to_excel(mapping_report_path, index=False)
    pd.DataFrame(validation_errors).to_csv(validation_report_path, index=False)

    generated_rows = len(output_objects[0]["records"]) if output_objects else 0
    print("\n========== HDL AUTOMATION SUMMARY ==========")
    print(f"Excel rows read: {len(df)}")
    print(f"Rows generated in each HDL object: {generated_rows}")
    skipped_rows = len({
        item["ExcelRow"] for item in validation_errors
    })
    print(f"Rows skipped due to validation errors: {skipped_rows}")
    print(f"Output file: {output_file}")
    print(f"Mapping report: {mapping_report_path}")
    print(f"Validation report: {validation_report_path}")
    print("============================================")


if __name__ == "__main__":
    main()