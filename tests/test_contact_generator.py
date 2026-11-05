import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.contact_generator import (
    build_contact_output_objects,
    generate_contact_dat,
)


class ContactGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.dataframe = pd.DataFrame([{
            "Person Number": "SAEMP1001",
            "Start Date": "2020-01-01",
            "Father Name": "Rajiv Sharma",
            "Mother Name": "Sunanda Sharma",
            "Spouse": "Neena Sharma",
            "Home Address": "1 Main Street",
            "Nationality": "Saudi Arabian",
            "Personal Email": "worker@example.test",
        }])

    def test_builds_contact_records_from_family_columns(self):
        output_objects = build_contact_output_objects(
            self.dataframe,
            "GRISMO",
        )
        objects = {
            output_obj["object_name"]: output_obj
            for output_obj in output_objects
        }

        self.assertEqual(len(objects["Contact"]["records"]), 3)
        self.assertEqual(
            [record["SourceSystemId"] for record in objects["Contact"]["records"]],
            [
                "PER_FAT_SAEMP1001",
                "PER_MOT_SAEMP1001",
                "PER_SPO_SAEMP1001",
            ],
        )
        self.assertEqual(
            objects["ContactName"]["records"][0]["FirstName"],
            "Rajiv",
        )
        self.assertEqual(
            objects["ContactName"]["records"][0]["LastName"],
            "Sharma",
        )
        self.assertEqual(
            objects["ContactRelationship"]["records"][0]["ContactType"],
            "IN_FR",
        )
        self.assertEqual(
            objects["ContactRelationship"]["records"][2]["PrimaryContactFlag"],
            "Y",
        )
        self.assertEqual(
            objects["ContactAddress"]["records"][0]["Country"],
            "SA",
        )
        self.assertEqual(objects["ContactEmail"]["records"], [])

    def test_only_uses_contact_specific_emails(self):
        self.dataframe["Father Email"] = "father@example.test"
        objects = {
            output_obj["object_name"]: output_obj
            for output_obj in build_contact_output_objects(
                self.dataframe,
                "GRISMO",
            )
        }

        self.assertEqual(len(objects["ContactEmail"]["records"]), 1)
        email = objects["ContactEmail"]["records"][0]
        self.assertEqual(email["PersonId(SourceSystemId)"], "PER_FAT_SAEMP1001")
        self.assertEqual(email["EmailAddress"], "father@example.test")

    def test_writes_contact_dat_with_hdl_metadata_and_records(self):
        with tempfile.TemporaryDirectory() as output_dir:
            output_file = generate_contact_dat(
                self.dataframe,
                "GRISMO",
                output_dir,
            )
            content = Path(output_file).read_text(encoding="utf-8")

        self.assertEqual(Path(output_file).name, "Contact.dat")
        self.assertIn("METADATA|Contact|PersonId|", content)
        self.assertIn(
            "MERGE|Contact||2020/01/01|||||2020/01/01",
            content,
        )
        self.assertIn("PER_FAT_SAEMP1001", content)


if __name__ == "__main__":
    unittest.main()
