import unittest

from main import _make_mapping_lookup
from src.field_mapper import (
    build_alias_index,
    load_field_mappings,
    normalize_column_name,
)


class JobMappingTests(unittest.TestCase):
    def test_derives_required_job_code_from_job_name(self):
        fields = [
            {"field_name": "JobCode", "required_flag": 1, "generated_field": 0},
            {"field_name": "SetCode", "required_flag": 1, "generated_field": 0},
            {
                "field_name": "EffectiveStartDate",
                "required_flag": 1,
                "generated_field": 0,
            },
            {"field_name": "Name", "required_flag": 1, "generated_field": 0},
            {
                "field_name": "SourceSystemOwner",
                "required_flag": 1,
                "generated_field": 1,
            },
            {
                "field_name": "SourceSystemId",
                "required_flag": 1,
                "generated_field": 1,
            },
        ]
        objects = [{
            "object_name": "Job",
            "fields": fields,
            "mappings": [],
        }]
        columns = {
            normalize_column_name(name): name
            for name in ("Job Name", "Start Date")
        }

        lookup, report = _make_mapping_lookup(
            objects,
            columns,
            build_alias_index(load_field_mappings()),
        )
        mappings = {item["field_name"]: item for item in report}

        self.assertEqual(
            lookup[("Job", "JobCode")]["mapping_type"],
            "DERIVED",
        )
        self.assertEqual(
            lookup[("Job", "JobCode")]["excel_column"],
            "Job Name",
        )
        self.assertEqual(mappings["JobCode"]["status"], "MAPPED")
        self.assertEqual(
            lookup[("Job", "Name")]["excel_column"],
            "Job Name",
        )
        self.assertEqual(mappings["SetCode"]["mapping_type"], "DEFAULT")
        self.assertEqual(mappings["SourceSystemId"]["mapping_type"], "GENERATED")
        self.assertTrue(all(item["status"] == "MAPPED" for item in report))


if __name__ == "__main__":
    unittest.main()
