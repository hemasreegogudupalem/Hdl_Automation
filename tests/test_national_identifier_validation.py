import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from main import _make_mapping_lookup
from src.dat_generator import generate_hdl_bundle
from src.field_mapper import (
    build_alias_index,
    load_field_mappings,
    load_national_identifier_config,
    map_excel_dataframe,
    normalize_column_name,
)
from src.validator import (
    normalize_national_identifier,
    validate_national_identifier,
)


class NationalIdentifierValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_national_identifier_config()

    def test_accepts_country_specific_digit_lengths(self):
        saudi_errors = validate_national_identifier(
            {
                "Nationality": "Saudi Arabian",
                "NationalIdentifierNumber": "1234567890",
            },
            self.config,
        )
        india_errors = validate_national_identifier(
            {
                "Nationality": "Indian",
                "NationalIdentifierNumber": "123456789012",
            },
            self.config,
        )

        self.assertEqual(saudi_errors, [])
        self.assertEqual(india_errors, [])

    def test_accepts_country_code_for_identifier_rule(self):
        errors = validate_national_identifier(
            {
                "Nationality": "SA",
                "NationalIdentifierNumber": "1000002303",
            },
            self.config,
        )

        self.assertEqual(errors, [])

    def test_allows_blank_identifier(self):
        errors = validate_national_identifier(
            {"Nationality": "India", "NationalIdentifierNumber": ""},
            self.config,
        )

        self.assertEqual(errors, [])

    def test_normalizes_numeric_excel_identifier(self):
        identifier = normalize_national_identifier(1234567890.0)
        errors = validate_national_identifier(
            {
                "Nationality": "Saudi Arabian",
                "NationalIdentifierNumber": 1234567890.0,
            },
            self.config,
        )

        self.assertEqual(identifier, "1234567890")
        self.assertEqual(errors, [])

    def test_rejects_wrong_length_and_non_digit_values(self):
        wrong_length = validate_national_identifier(
            {
                "Nationality": "India",
                "NationalIdentifierNumber": "1234567890",
            },
            self.config,
        )
        non_digits = validate_national_identifier(
            {
                "Nationality": "Saudi Arabia",
                "NationalIdentifierNumber": "123456789A",
            },
            self.config,
        )

        self.assertIn("exactly 12 digits", wrong_length[0])
        self.assertEqual(non_digits, ["National identifier must contain digits only."])

    def test_requires_country_for_populated_identifier(self):
        errors = validate_national_identifier(
            {"NationalIdentifierNumber": "1234567890"},
            self.config,
        )

        self.assertIn("Nationality is required", errors[0])

    def test_rejects_country_without_configured_rule(self):
        errors = validate_national_identifier(
            {
                "Nationality": "Unknown",
                "NationalIdentifierNumber": "1234567890",
            },
            self.config,
        )

        self.assertIn("No national identifier digit rule is configured", errors[0])

    def test_maps_alternate_identifier_column(self):
        aliases = load_field_mappings()
        alias_index = build_alias_index(aliases)
        normalized_columns = {
            normalize_column_name("Aadhaar Number"): "Aadhaar Number"
        }
        objects = [
            {
                "object_name": "Person",
                "mappings": [
                    {
                        "field_name": "NationalIdentifierNumber",
                        "excel_column": "National Identifier (10-digit test value)",
                        "mapping_type": "COLUMN",
                    }
                ],
                "fields": [{"field_name": "NationalIdentifierNumber"}],
            }
        ]

        lookup, _ = _make_mapping_lookup(
            objects,
            normalized_columns,
            alias_index,
        )

        self.assertEqual(
            lookup[("Person", "NationalIdentifierNumber")]["excel_column"],
            "Aadhaar Number",
        )

    def test_writes_hdl_bundle(self):
        output_objects = [
            {
                "object_name": "Person",
                "metadata_fields": [
                    "PersonNumber",
                    "DateOfBirth",
                    "NationalIdentifierNumber",
                ],
                "records": [
                    {
                        "PersonNumber": "1001",
                        "DateOfBirth": pd.Timestamp("1990-04-03"),
                        "NationalIdentifierNumber": "1234567890",
                    }
                ],
            }
        ]

        with TemporaryDirectory() as output_dir:
            output_file = generate_hdl_bundle(
                Path(output_dir) / "Person.dat",
                output_objects,
            )

            self.assertEqual(
                output_file.read_text(encoding="utf-8"),
                "METADATA|Person|PersonNumber|DateOfBirth|NationalIdentifierNumber\n"
                "MERGE|Person|1001|1990/04/03|1234567890\n",
            )

    def test_formats_string_dates_in_hdl_output(self):
        output_objects = [
            {
                "object_name": "Worker",
                "metadata_fields": ["EffectiveStartDate", "StartDate"],
                "records": [
                    {
                        "EffectiveStartDate": "2024-01-02",
                        "StartDate": "2025-12-31",
                    }
                ],
            }
        ]

        with TemporaryDirectory() as output_dir:
            output_file = generate_hdl_bundle(
                Path(output_dir) / "Worker.dat",
                output_objects,
            )

            self.assertIn(
                "MERGE|Worker|2024/01/02|2025/12/31",
                output_file.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
