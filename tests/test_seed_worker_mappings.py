import unittest
from unittest.mock import patch

from src.seed_worker_mappings import build_mapping_plan


class BuildMappingPlanTests(unittest.TestCase):
    @patch("src.seed_worker_mappings.get_attributes")
    def test_only_unique_alias_matches_are_planned(self, get_attributes):
        objects = [
            {"object_id": 1, "object_name": "Worker", "active": 1},
        ]
        get_attributes.return_value = [
            {
                "attribute_id": 10,
                "attribute_name": "PersonNumber",
                "active": 1,
                "required": 1,
            },
            {
                "attribute_id": 11,
                "attribute_name": "EmailAddress",
                "active": 1,
                "required": 1,
            },
            {
                "attribute_id": 12,
                "attribute_name": "EffectiveStartDate",
                "active": 1,
                "required": 1,
            },
        ]
        aliases = {
            "PersonNumber": ["Person Number", "Employee Number"],
            "EmailAddress": ["Personal Email", "Work Email"],
            "EffectiveStartDate": ["Effective Start Date"],
        }

        planned, ambiguous, unmatched = build_mapping_plan(
            objects,
            ["Person Number", "Personal Email", "Work Email"],
            aliases,
            [],
        )

        self.assertEqual(
            [(item["field_name"], item["client_column_name"]) for item in planned],
            [("PersonNumber", "Person Number")],
        )
        self.assertEqual(ambiguous[0]["field_name"], "EmailAddress")
        self.assertEqual(unmatched[0]["field_name"], "EffectiveStartDate")

    @patch("src.seed_worker_mappings.get_attributes")
    def test_existing_mapping_is_not_replaced_or_duplicated(self, get_attributes):
        get_attributes.return_value = [{
            "attribute_id": 10,
            "attribute_name": "PersonNumber",
            "active": 1,
            "required": 1,
        }]

        planned, ambiguous, unmatched = build_mapping_plan(
            [{"object_id": 1, "object_name": "Worker", "active": 1}],
            ["Person Number"],
            {"PersonNumber": ["Person Number"]},
            [{"object_id": 1, "attribute_id": 10, "active": 1}],
        )

        self.assertEqual(planned, [])
        self.assertEqual(ambiguous, [])
        self.assertEqual(unmatched, [])


if __name__ == "__main__":
    unittest.main()
