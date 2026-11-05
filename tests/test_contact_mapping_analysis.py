import unittest

from main import _make_mapping_lookup
from src.field_mapper import build_alias_index, load_field_mappings, normalize_column_name


class ContactMappingAnalysisTests(unittest.TestCase):
    def test_infers_contact_mappings_from_family_columns(self):
        fields = [
            {"field_name": "PersonId(SourceSystemId)", "required_flag": 1, "generated_field": 1},
            {"field_name": "EffectiveStartDate", "required_flag": 1, "generated_field": 0},
            {"field_name": "FirstName", "required_flag": 1, "generated_field": 0},
            {"field_name": "SourceSystemId", "required_flag": 1, "generated_field": 1},
            {"field_name": "SourceSystemOwner", "required_flag": 1, "generated_field": 1},
        ]
        objects = [{
            "object_name": "ContactName",
            "fields": fields,
            "mappings": [],
        }]
        columns = {
            normalize_column_name(name): name
            for name in (
                "Start Date",
                "Father Name",
                "Mother Name",
                "Spouse",
            )
        }

        lookup, report = _make_mapping_lookup(
            objects,
            columns,
            build_alias_index(load_field_mappings()),
        )
        mappings = {item["field_name"]: item for item in report}

        self.assertEqual(
            lookup[("ContactName", "PersonId(SourceSystemId)")]["mapping_type"],
            "GENERATED",
        )
        self.assertEqual(
            mappings["EffectiveStartDate"]["excel_column"],
            "Start Date",
        )
        self.assertEqual(
            mappings["FirstName"]["mapping_type"],
            "DERIVED",
        )
        self.assertEqual(mappings["FirstName"]["status"], "MAPPED")
        self.assertEqual(mappings["SourceSystemId"]["mapping_type"], "GENERATED")
        self.assertTrue(all(item["status"] == "MAPPED" for item in report))


if __name__ == "__main__":
    unittest.main()
