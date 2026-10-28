import unittest
from unittest.mock import patch

from src.mysql_storage import load_template_configuration


class LoadTemplateConfigurationTests(unittest.TestCase):
    @patch("src.mysql_storage.get_active_clients", return_value=[
        {"source_system_owner": "GRISMO"}
    ])
    @patch("src.mysql_storage.get_attributes")
    @patch("src.mysql_storage.get_objects")
    @patch("src.mysql_storage.get_field_mappings", return_value=[])
    @patch("src.mysql_storage.get_templates", return_value=[{
        "template_id": 1,
        "template_name": "Worker",
        "active": 1,
    }])
    def test_orders_person_email_fields_by_database_sequence(
        self,
        _get_templates,
        _get_mappings,
        get_objects,
        get_attributes,
        _get_active_clients,
    ):
        get_objects.return_value = [{
            "object_id": 4,
            "object_name": "PersonEmail",
            "active": 1,
        }]
        get_attributes.return_value = [
            {
                "attribute_id": 39,
                "attribute_name": "SourceSystemId",
                "required": 1,
                "sequence_no": 7,
                "generated_field": 1,
                "active": 1,
            },
            {
                "attribute_id": 35,
                "attribute_name": "DateTo",
                "required": 0,
                "sequence_no": 3,
                "generated_field": 0,
                "active": 1,
            },
            {
                "attribute_id": 33,
                "attribute_name": "PersonNumber",
                "required": 1,
                "sequence_no": 1,
                "generated_field": 0,
                "active": 1,
            },
            {
                "attribute_id": 38,
                "attribute_name": "SourceSystemOwner",
                "required": 1,
                "sequence_no": 6,
                "generated_field": 1,
                "active": 1,
            },
        ]

        _template, objects = load_template_configuration()

        self.assertEqual(
            [field["field_name"] for field in objects[0]["fields"]],
            ["PersonNumber", "DateTo", "SourceSystemOwner", "SourceSystemId"],
        )

    @patch("src.mysql_storage.get_attributes")
    @patch("src.mysql_storage.get_objects")
    @patch("src.mysql_storage.get_field_mappings")
    @patch("src.mysql_storage.get_templates")
    def test_selects_first_active_template_and_normalizes_schema(
        self,
        get_templates,
        get_field_mappings,
        get_objects,
        get_attributes,
    ):
        get_templates.return_value = [
            {"template_id": 1, "template_name": "Inactive", "active": 0},
            {
                "template_id": 2,
                "template_name": "Worker",
                "output_file_name": "Worker.dat",
                "active": 1,
            },
            {"template_id": 3, "template_name": "Job", "active": 1},
        ]
        get_field_mappings.return_value = [
            {
                "mapping_id": 10,
                "object_id": 20,
                "attribute_id": 30,
                "client_column_name": "Employee Number",
                "mapping_type": "COLUMN",
                "active": 1,
            }
        ]
        get_objects.return_value = [
            {"object_id": 20, "object_name": "Worker", "active": 1}
        ]
        get_attributes.return_value = [
            {
                "attribute_id": 30,
                "attribute_name": "PersonNumber",
                "required": 1,
                "active": 1,
            }
        ]

        template, objects = load_template_configuration()

        self.assertEqual(template["template_name"], "Worker")
        self.assertEqual(objects[0]["fields"][0]["field_name"], "PersonNumber")
        self.assertEqual(objects[0]["fields"][0]["required_flag"], 1)
        self.assertEqual(objects[0]["mappings"][0]["field_name"], "PersonNumber")
        self.assertEqual(
            objects[0]["mappings"][0]["excel_column"],
            "Employee Number",
        )
        get_objects.assert_called_once_with(2, "config/settings.json")

    @patch("src.mysql_storage.get_attributes", return_value=[])
    @patch(
        "src.mysql_storage.get_objects",
        return_value=[{"object_id": 20, "object_name": "Worker", "active": 1}],
    )
    @patch("src.mysql_storage.get_field_mappings", return_value=[])
    @patch(
        "src.mysql_storage.get_templates",
        return_value=[{
            "template_id": 2,
            "template_name": "Worker",
            "active": 1,
        }],
    )
    def test_reports_objects_without_attributes(
        self,
        _get_templates,
        _get_mappings,
        _get_objects,
        _get_attributes,
    ):
        with self.assertRaisesRegex(
            ValueError,
            "No active attributes are configured for HDL object 'Worker'",
        ):
            load_template_configuration()


if __name__ == "__main__":
    unittest.main()
