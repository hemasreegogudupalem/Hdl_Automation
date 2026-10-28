
import json
import re
from pathlib import Path

import pandas as pd


DEFAULT_ALIASES = {
    "PersonNumber": [
        "person number", "person_number", "employee id",
        "employee number", "employee code", "staff id"
    ],
    "FirstName": ["first name", "firstname", "given name"],
    "MiddleNames": ["middle name", "middle names", "middle initial"],
    "LastName": ["last name", "lastname", "surname", "family name"],
    "DateOfBirth": ["date of birth", "dob", "birth date"],
    "StartDate": [
        "start date", "date of joining", "joining date",
        "hire date", "date joined"
    ],
    "EffectiveStartDate": [
        "effective start date", "effective date"
    ],
    "Sex": ["sex", "gender"],
    "MaritalStatus": ["marital status", "marital"],
    "EmailAddress": ["email", "email address", "work email", "official email"],
    "EmailType": ["email type"],
    "DateTo": ["date to", "email end date"],
    "PhoneNumber": ["phone", "phone number", "mobile", "mobile number"],
    "CountryCodeNumber": ["country code", "calling code"],
    "DepartmentName": ["department", "department name", "dept"],
    "JobCode": ["job code", "job id", "job"],
    "JobName": ["job title", "job name", "designation", "position"],
    "BusinessUnitName": ["business unit", "business unit name"],
    "LegalEmployerName": ["legal employer", "legal employer name"],
    "LocationCode": ["location code", "location id"],
    "LocationName": ["location", "location name", "work location"],
    "AssignmentNumber": ["assignment number", "assignment id"],
    "AssignmentStatusType": ["assignment status", "employment status"],
    "WorkerType": ["worker type", "employee type", "employment type"],
    "LegislationCode": ["legislation code", "legislation"],
    "LegalEntity": ["legal entity", "legal entity name"],
    "Nationality": ["nationality", "citizenship"],
    "NationalIdentifierNumber": [
        "national identifier", "national id", "national id number",
        "iqama number", "iqama id"
    ],
    "NationalIdentifierType": ["national identifier type", "id type"],
    "AddressLine1": ["address", "address line 1", "street address"],
    "AddressLine2": ["address line 2", "additional address"],
    "TownOrCity": ["city", "town", "town or city"],
    "PostalCode": ["postal code", "zip code", "postcode"],
    "Country": ["country", "country code"],
    "LegalEmployer": ["legal employer", "employer"],
    "ReportingManager": [
        "reporting manager", "manager", "manager name", "reports to"
    ],
}


def normalize_column_name(name):
    """Normalize a column label for case- and punctuation-insensitive matching."""
    text = str(name).strip().casefold()
    return re.sub(r"[^a-z0-9]", "", text)


def _load_mapping_document(mapping_file):
    path = Path(mapping_file)

    if not path.is_absolute():
        path = Path.cwd() / path

    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as file:
        custom = json.load(file)

    if not isinstance(custom, dict):
        raise ValueError("The mapping JSON must contain an object.")

    return custom


def load_field_mappings(mapping_file="mappings/mappings.json"):
    """
    Load aliases from JSON if available.
    Default aliases remain available if the file does not exist.
    """
    aliases = {
        canonical: list(names)
        for canonical, names in DEFAULT_ALIASES.items()
    }

    custom = _load_mapping_document(mapping_file)

    for canonical, names in custom.items():
        if canonical == "_validation":
            continue

        if isinstance(names, str):
            names = [names]

        if not isinstance(names, list):
            raise ValueError(
                f"Aliases for {canonical} must be a string or list."
            )

        aliases.setdefault(canonical, [])
        aliases[canonical] = list(dict.fromkeys(
            aliases[canonical] + [str(name) for name in names]
        ))

    return aliases


def load_national_identifier_config(mapping_file="mappings/mappings.json"):
    """Load country-specific national identifier validation rules."""
    document = _load_mapping_document(mapping_file)
    validation = document.get("_validation")
    if not isinstance(validation, dict):
        raise ValueError("The mapping JSON must define a '_validation' object.")

    config = validation.get("national_identifier")
    if not isinstance(config, dict):
        raise ValueError(
            "The mapping JSON must define '_validation.national_identifier'."
        )

    country_field = config.get("country_field")
    if not isinstance(country_field, str) or not country_field.strip():
        raise ValueError(
            "'_validation.national_identifier.country_field' must be a "
            "non-empty field name."
        )

    country_rules = config.get("country_rules")
    if not isinstance(country_rules, dict) or not country_rules:
        raise ValueError(
            "'_validation.national_identifier.country_rules' must be a "
            "non-empty object."
        )

    allow_blank = config.get("allow_blank", False)
    if not isinstance(allow_blank, bool):
        raise ValueError(
            "'_validation.national_identifier.allow_blank' must be a boolean."
        )

    rules = {}
    for country, digits in country_rules.items():
        key = normalize_column_name(country)
        if not key:
            raise ValueError("Country names in identifier rules cannot be blank.")
        if isinstance(digits, bool) or not isinstance(digits, int) or digits < 1:
            raise ValueError(
                f"Identifier digit count for '{country}' must be a positive "
                "integer."
            )
        if key in rules:
            raise ValueError(
                f"Duplicate country identifier rule after normalization: "
                f"'{country}'."
            )
        rules[key] = digits

    return {
        "country_field": country_field.strip(),
        "country_rules": rules,
        "allow_blank": allow_blank,
    }


def build_alias_index(alias_map):
    """Create a normalized lookup: Excel column spelling -> canonical field."""
    index = {}

    for canonical, names in alias_map.items():
        for name in [canonical, *names]:
            key = normalize_column_name(name)

            if key and key not in index:
                index[key] = canonical

    return index


def map_excel_row(row, alias_map):
    """Map one pandas row to canonical fields."""
    alias_index = build_alias_index(alias_map)
    mapped = {}
    report = []

    for column, value in row.items():
        canonical = alias_index.get(normalize_column_name(column))

        if canonical is None:
            report.append({
                "excel_column": str(column),
                "canonical_field": None,
                "status": "Unmapped",
            })
            continue

        if canonical in mapped and not pd.isna(mapped[canonical]):
            report.append({
                "excel_column": str(column),
                "canonical_field": canonical,
                "status": "Duplicate canonical field; first non-empty value retained",
            })
            continue

        mapped[canonical] = value
        report.append({
            "excel_column": str(column),
            "canonical_field": canonical,
            "status": "Mapped",
        })

    return mapped, report


def map_excel_dataframe(df, alias_map=None):
    """Map an entire Excel dataframe and return records plus a mapping report."""
    if alias_map is None:
        alias_map = load_field_mappings()

    alias_index = build_alias_index(alias_map)
    records = []
    report = []

    for column in df.columns:
        canonical = alias_index.get(normalize_column_name(column))

        report.append({
            "excel_column": str(column),
            "canonical_field": canonical,
            "status": "Mapped" if canonical else "Unmapped",
        })

    for _, row in df.iterrows():
        mapped = {}

        for column, value in row.items():
            canonical = alias_index.get(normalize_column_name(column))

            if canonical is None:
                continue

            if canonical not in mapped or pd.isna(mapped[canonical]):
                mapped[canonical] = value

        records.append(mapped)

    return records, report


if __name__ == "__main__":
    from src.excel_reader import read_excel

    input_file = Path("input/saudi_employee_data.xlsx")
    df = read_excel(input_file)
    aliases = load_field_mappings()
    records, report = map_excel_dataframe(df, aliases)

    print("\n========== FIELD MAPPING REPORT ==========")
    for item in report:
        print(
            f"{item['excel_column']:<30} -> "
            f"{str(item['canonical_field'] or 'Unmapped'):<30} "
            f"{item['status']}"
        )

    print(f"\nTotal employee rows mapped: {len(records)}")
