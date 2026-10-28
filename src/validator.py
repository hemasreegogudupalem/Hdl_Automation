
import numbers
import re
from datetime import date, datetime

import pandas as pd

from src.field_mapper import normalize_column_name


def is_empty(value):
    """Check whether a value is empty or missing."""
    if value is None:
        return True

    try:
        missing = pd.isna(value)
        if isinstance(missing, bool) and missing:
            return True
        if not isinstance(missing, bool) and bool(missing):
            return True
    except (TypeError, ValueError):
        pass

    return isinstance(value, str) and value.strip() == ""


def format_hdl_date(value, dayfirst=False):
    """
    Convert a date to Oracle HDL format YYYY/MM/DD.

    Use dayfirst=True for source strings such as 31/12/2025.
    Empty values remain empty.
    """
    if is_empty(value):
        return ""

    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.strftime("%Y/%m/%d")

    text = str(value).strip()

    # Reject ambiguous numeric date strings unless the caller
    # explicitly chooses dayfirst behavior.
    if re.fullmatch(r"\d{1,2}[/-]\d{1,2}[/-]\d{4}", text):
        parts = re.split(r"[/-]", text)
        first, second = int(parts[0]), int(parts[1])

        if first <= 12 and second <= 12:
            raise ValueError(
                f"Ambiguous date '{text}'. Specify the expected "
                "date format before converting."
            )

    parsed = pd.to_datetime(
        text,
        errors="coerce",
        dayfirst=dayfirst,
    )

    if pd.isna(parsed):
        raise ValueError(f"Invalid date: {text}")

    return parsed.strftime("%Y/%m/%d")


def validate_required_fields(data, required_fields):
    """Return a list of missing required fields."""
    errors = []

    for field in required_fields:
        if is_empty(data.get(field)):
            errors.append(f"Required field '{field}' is missing.")

    return errors


def validate_employee_row(row):
    """Validate basic employee fields and date values."""
    errors = []

    if is_empty(row.get("PersonNumber")):
        errors.append("PersonNumber is required.")

    if is_empty(row.get("StartDate")):
        errors.append("StartDate is required.")
    else:
        try:
            format_hdl_date(row["StartDate"])
        except ValueError as exc:
            errors.append(f"StartDate: {exc}")

    for field in ("DateOfBirth", "EffectiveStartDate"):
        if not is_empty(row.get(field)):
            try:
                format_hdl_date(row[field])
            except ValueError as exc:
                errors.append(f"{field}: {exc}")

    return errors


def normalize_national_identifier(value):
    """
    Convert numeric identifiers to text without a trailing decimal.

    Note: if Excel has already removed leading zeros from a numeric
    cell, they cannot be recovered without a known width rule.
    """
    if is_empty(value):
        return ""

    if isinstance(value, numbers.Real) and not isinstance(value, bool):
        if float(value).is_integer():
            return str(int(value))

    text = str(value).strip()

    # Handle strings like '12345.0' while preserving leading zeros
    # in strings like '0012345'.
    if re.fullmatch(r"\d+\.0+", text):
        return text.split(".")[0]

    return text


def validate_national_identifier(row, config):
    """Validate an identifier against supplied country-specific rules."""
    identifier = row.get("NationalIdentifierNumber")

    if is_empty(identifier):
        return []

    if not isinstance(config, dict):
        return ["National identifier configuration must be a dictionary."]

    country_field = config.get("country_field")
    country_rules = config.get("country_rules", {})

    if not country_field:
        return ["National identifier country_field is not configured."]

    country = row.get(country_field)

    if is_empty(country):
        return [
            f"{country_field} is required when a national identifier is provided."
        ]

    country_name = str(country).strip()
    normalized_country = normalize_column_name(country_name)

    required_digits = country_rules.get(normalized_country)

    if required_digits is None:
        return [
            f"No national identifier digit rule is configured for "
            f"{country_field} '{country_name}'."
        ]

    identifier = normalize_national_identifier(identifier)

    if not re.fullmatch(r"[0-9]+", identifier):
        return ["National identifier must contain digits only."]

    if len(identifier) != int(required_digits):
        return [
            f"National identifier for {country_name} must contain exactly "
            f"{required_digits} digits."
        ]

    return []


def validate_unique_person_numbers(records):
    """Detect missing or duplicate PersonNumber values across records."""
    errors = []
    seen = set()

    for row_number, record in enumerate(records, start=2):
        value = record.get("PersonNumber")

        if is_empty(value):
            errors.append(
                f"Excel row {row_number}: PersonNumber is missing."
            )
            continue

        person_number = str(value).strip()

        if person_number in seen:
            errors.append(
                f"Excel row {row_number}: duplicate PersonNumber "
                f"'{person_number}'."
            )
        else:
            seen.add(person_number)

    return errors
