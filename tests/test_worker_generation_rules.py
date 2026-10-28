import unittest

from main import (
    WORKER_METADATA_FIELDS,
    _build_worker_metadata_record,
    _country_hdl_value,
    _email_entries,
    _generated_value,
    _make_mapping_lookup,
    prompt_worker_generation_values,
    _worker_generation_defaults,
    _worker_source_system_id,
)
from src.field_mapper import (
    build_alias_index,
    load_field_mappings,
    normalize_column_name,
)


class WorkerGenerationRulesTests(unittest.TestCase):
    def test_creates_typed_email_records_for_work_and_personal_columns(self):
        aliases = {
            "workemail": "EmailAddress",
            "personalemail": "EmailAddress",
        }
        normalized_columns = {
            normalize_column_name("Work Email"): "Work Email",
            normalize_column_name("Personal Email"): "Personal Email",
        }

        entries = _email_entries(
            {
                "Work Email": "work@example.test",
                "Personal Email": "personal@example.test",
            },
            normalized_columns,
            aliases,
        )

        self.assertEqual(entries, [
            {
                "EmailAddress": "work@example.test",
                "EmailType": "W1",
                "PrimaryFlag": "Y",
            },
            {
                "EmailAddress": "personal@example.test",
                "EmailType": "H1",
                "PrimaryFlag": "N",
            },
        ])

    def test_uses_personal_email_as_primary_when_work_is_blank(self):
        entries = _email_entries(
            {"Personal Email": "personal@example.test"},
            {normalize_column_name("Personal Email"): "Personal Email"},
            {"personalemail": "EmailAddress"},
        )

        self.assertEqual(entries, [{
            "EmailAddress": "personal@example.test",
            "EmailType": "H1",
            "PrimaryFlag": "Y",
        }])

    def test_maps_generic_email_column_and_ignores_blank_cells(self):
        aliases = load_field_mappings()
        alias_index = build_alias_index(aliases)
        normalized_columns = {
            normalize_column_name("Email Address"): "Email Address",
            normalize_column_name("Work Email"): "Work Email",
        }

        entries = _email_entries(
            {"Email Address": "generic@example.test", "Work Email": None},
            normalized_columns,
            alias_index,
        )

        self.assertEqual(entries, [{
            "EmailAddress": "generic@example.test",
            "EmailType": "W1",
            "PrimaryFlag": "Y",
        }])

    def test_preserves_email_type_from_excel(self):
        aliases = build_alias_index(load_field_mappings())
        normalized_columns = {
            normalize_column_name("EmailAddress"): "EmailAddress",
            normalize_column_name("EmailType"): "EmailType",
        }

        entries = _email_entries(
            {
                "EmailAddress": "personal@example.test",
                "EmailType": "H1",
            },
            normalized_columns,
            aliases,
        )

        self.assertEqual(entries, [{
            "EmailAddress": "personal@example.test",
            "EmailType": "H1",
            "PrimaryFlag": "Y",
        }])

    def test_prompts_for_required_generation_values(self):
        answers = iter([
            "SAU",
            "Example Employer",
            "EXAMPLE_OWNER",
        ])
        prompts = []

        def input_func(prompt):
            prompts.append(prompt)
            return next(answers)

        values = prompt_worker_generation_values(input_func)

        self.assertEqual(values, {
            "legislation_code": "SAU",
            "legal_employer_name": "Example Employer",
            "source_system_owner": "EXAMPLE_OWNER",
        })
        self.assertEqual(prompts, [
            "Legislation code: ",
            "Legal employer name: ",
            "Source system owner: ",
        ])

    def test_enter_accepts_excel_and_database_defaults(self):
        prompts = []
        defaults = {
            "legislation_code": "SAU",
            "legal_employer_name": "MIS LE",
            "source_system_owner": "GRISMO",
        }

        values = prompt_worker_generation_values(
            defaults=defaults,
            input_func=lambda prompt: prompts.append(prompt) or "",
        )

        self.assertEqual(values, defaults)
        self.assertEqual(prompts, [
            "Legislation code [SAU]: ",
            "Legal employer name [MIS LE]: ",
            "Source system owner [GRISMO]: ",
        ])

    def test_derives_defaults_only_from_single_unambiguous_values(self):
        defaults = _worker_generation_defaults(
            [
                {"Nationality": "Saudi Arabian", "LegalEmployerName": "MIS LE"},
                {"Nationality": "Saudi Arabian", "LegalEmployerName": "MIS LE"},
            ],
            "GRISMO",
        )

        self.assertEqual(defaults, {
            "legislation_code": "SAU",
            "legal_employer_name": "MIS LE",
            "source_system_owner": "GRISMO",
        })

    def test_prefers_explicit_legislation_code_from_excel(self):
        defaults = _worker_generation_defaults(
            [
                {"LegislationCode": "SA", "LegalEmployerName": "MIS LE"},
                {"LegislationCode": "SA", "LegalEmployerName": "MIS LE"},
            ],
            "GRISMO",
        )

        self.assertEqual(defaults, {
            "legislation_code": "SA",
            "legal_employer_name": "MIS LE",
            "source_system_owner": "GRISMO",
        })

    def test_reprompts_when_value_is_blank(self):
        answers = iter(["", "SAU", "Employer", "OWNER"])

        values = prompt_worker_generation_values(
            lambda _prompt: next(answers)
        )

        self.assertEqual(values["legislation_code"], "SAU")
        self.assertEqual(values["legal_employer_name"], "Employer")
        self.assertEqual(values["source_system_owner"], "OWNER")

    def test_worker_metadata_headers_match_expected_hdl_layouts(self):
        self.assertEqual(WORKER_METADATA_FIELDS["Worker"], [
            "EffectiveStartDate", "PersonNumber", "StartDate", "DateOfBirth",
            "ActionCode", "SourceSystemId", "SourceSystemOwner",
        ])
        self.assertEqual(WORKER_METADATA_FIELDS["PersonName"], [
            "EffectiveStartDate", "PersonId(SourceSystemId)", "NameType",
            "LegislationCode", "Title", "FirstName", "MiddleNames",
            "LastName", "SourceSystemId", "SourceSystemOwner",
        ])
        self.assertEqual(WORKER_METADATA_FIELDS["PersonNationalIdentifier"], [
            "PersonNumber", "LegislationCode", "NationalIdentifierType",
            "NationalIdentifierNumber", "PersonId(SourceSystemId)",
            "PrimaryFlag", "SourceSystemId", "SourceSystemOwner",
        ])
        self.assertEqual(WORKER_METADATA_FIELDS["PersonEmail"], [
            "PersonNumber", "DateFrom", "DateTo", "EmailType", "EmailAddress",
            "SourceSystemOwner", "SourceSystemId",
        ])
        self.assertEqual(WORKER_METADATA_FIELDS["PersonPhone"], [
            "PhoneType", "PersonNumber", "DateFrom", "LegislationCode",
            "PhoneNumber", "PrimaryFlag", "SourceSystemId",
            "SourceSystemOwner",
        ])
        self.assertEqual(WORKER_METADATA_FIELDS["PersonAddress"], [
            "EffectiveStartDate", "EffectiveEndDate", "AddressType",
            "PersonId(SourceSystemId)", "AddressLine1", "AddressLine2",
            "AddressLine3", "AddressLine4", "Building", "FloorNumber",
            "TownOrCity", "Region1", "Region2", "Region3", "Country",
            "PostalCode", "SourceSystemId", "SourceSystemOwner",
        ])
        self.assertEqual(WORKER_METADATA_FIELDS["PersonLegislativeData"], [
            "EffectiveStartDate", "PersonId(SourceSystemId)",
            "LegislationCode", "Sex", "MaritalStatus", "SourceSystemId",
            "SourceSystemOwner",
        ])
        self.assertEqual(WORKER_METADATA_FIELDS["WorkRelationship"], [
            "PersonId(SourceSystemId)", "LegalEmployerName", "DateStart",
            "WorkerType", "PrimaryFlag", "SourceSystemId",
            "SourceSystemOwner",
        ])
        self.assertEqual(WORKER_METADATA_FIELDS["WorkTerms"], [
            "PeriodOfServiceId(SourceSystemId)", "PersonId(SourceSystemId)",
            "ActionCode", "EffectiveStartDate", "EffectiveSequence",
            "EffectiveLatestChange", "AssignmentNumber",
            "PrimaryWorkTermsFlag", "AssignmentType", "SourceSystemId",
            "SourceSystemOwner",
        ])
        self.assertEqual(WORKER_METADATA_FIELDS["Assignment"], [
            "PeriodOfServiceId(SourceSystemId)", "PersonId(SourceSystemId)",
            "ActionCode", "EffectiveStartDate", "EffectiveSequence",
            "EffectiveLatestChange", "WorkTermsAssignmentId(SourceSystemId)",
            "AssignmentNumber", "AssignmentStatusTypeCode", "PersonTypeCode",
            "BusinessUnitShortCode", "PrimaryFlag", "PrimaryAssignmentFlag",
            "AssignmentCategory", "DepartmentName", "FullPartTime",
            "LocationCode", "WorkTermsNumber", "AssignmentType",
            "WorkerCategory", "SourceSystemId", "SourceSystemOwner",
        ])

    def test_expands_parent_source_ids_and_metadata_defaults(self):
        record = _build_worker_metadata_record(
            "Assignment",
            {
                "AssignmentNumber": "ASG_SAEMP1001",
                "AssignmentStatusType": "ACTIVE",
                "SourceSystemId": "Assignment_SAEMP1001",
                "SourceSystemOwner": "GRISMO",
            },
            "SAEMP1001",
            "GRISMO",
            {},
            generation_values={
                "legislation_code": "SAU",
                "legal_employer_name": "Example Employer",
                "source_system_owner": "EXAMPLE_OWNER",
            },
        )

        self.assertEqual(
            record["PeriodOfServiceId(SourceSystemId)"],
            "wr_1001",
        )
        self.assertEqual(
            record["WorkTermsAssignmentId(SourceSystemId)"],
            "wt_1001",
        )
        self.assertEqual(record["PersonId(SourceSystemId)"], "wor_1001")
        self.assertEqual(record["SourceSystemId"], "asg_1001")
        self.assertEqual(
            record["AssignmentStatusTypeCode"],
            "ACTIVE_PROCESS",
        )
        self.assertEqual(record["EffectiveSequence"], "1")
        self.assertEqual(record["EffectiveLatestChange"], "Y")
        self.assertEqual(record["PrimaryAssignmentFlag"], "Y")
        self.assertEqual(record["SourceSystemOwner"], "EXAMPLE_OWNER")

    def test_generates_work_terms_and_assignment_numbers_without_underscores(self):
        work_terms = _build_worker_metadata_record(
            "WorkTerms",
            {},
            "12301",
            "GRISMO",
            {},
        )
        assignment = _build_worker_metadata_record(
            "Assignment",
            {},
            "12301",
            "GRISMO",
            {},
        )

        self.assertEqual(work_terms["AssignmentNumber"], "ET12301")
        self.assertEqual(work_terms["AssignmentType"], "ET")
        self.assertEqual(assignment["AssignmentNumber"], "E12301")
        self.assertEqual(assignment["WorkTermsNumber"], "ET12301")
        self.assertEqual(assignment["AssignmentType"], "E")

    def test_generation_values_override_excel_legal_employer(self):
        record = _build_worker_metadata_record(
            "WorkRelationship",
            {"LegalEmployerName": "Employer from Excel"},
            "SAEMP1001",
            "DB_OWNER",
            {},
            generation_values={
                "legislation_code": "SAU",
                "legal_employer_name": "Prompted Employer",
                "source_system_owner": "PROMPTED_OWNER",
            },
        )

        self.assertEqual(record["LegalEmployerName"], "Prompted Employer")
        self.assertEqual(record["SourceSystemOwner"], "PROMPTED_OWNER")

    def test_selects_explicit_workbook_columns_for_ambiguous_fields(self):
        columns = {
            normalize_column_name(column): column
            for column in (
                "Start Date",
                "Date of Joining",
                "Personal Email",
                "Work Email",
                "Phone Number",
                "Work Phone Number",
                "Country Dial Code",
                "Work Dial Code",
                "Worker Type",
                "Worker Category",
            )
        }
        fields = [
            {"field_name": name, "required_flag": 1}
            for name in (
                "StartDate",
                "EffectiveStartDate",
                "DateStart",
                "EmailAddress",
                "PhoneNumber",
                "CountryCodeNumber",
                "WorkerType",
            )
        ]
        objects = [{
            "object_name": "Worker",
            "mappings": [],
            "fields": fields,
        }]

        lookup, _ = _make_mapping_lookup(objects, columns)

        expected_columns = {
            "StartDate": "Start Date",
            "EffectiveStartDate": "Start Date",
            "DateStart": "Start Date",
            "EmailAddress": "Work Email",
            "PhoneNumber": "Work Phone Number",
            "CountryCodeNumber": "Work Dial Code",
            "WorkerType": "Worker Type",
        }
        for field_name, expected_column in expected_columns.items():
            self.assertEqual(
                lookup[("Worker", field_name)]["excel_column"],
                expected_column,
            )

    def test_maps_person_email_from_generic_email_column(self):
        column = "EmailAddress"
        objects = [{
            "object_name": "PersonEmail",
            "mappings": [],
            "fields": [{"field_name": "EmailAddress", "required_flag": 1}],
        }]

        lookup, _ = _make_mapping_lookup(
            objects,
            {normalize_column_name(column): column},
            {"emailaddress": "EmailAddress"},
        )

        self.assertEqual(
            lookup[("PersonEmail", "EmailAddress")]["excel_column"],
            "EmailAddress",
        )

    def test_ignores_required_database_fields_not_in_worker_hdl_layout(self):
        objects = [{
            "object_name": "Assignment",
            "mappings": [{
                "field_name": "BusinessUnitName",
                "excel_column": "Business Unit",
                "mapping_type": "DIRECT",
            }],
            "fields": [{
                "field_name": "BusinessUnitName",
                "required_flag": 1,
            }],
        }]

        lookup, _ = _make_mapping_lookup(
            objects,
            {normalize_column_name("BusinessUnitShortCode"): "BusinessUnitShortCode"},
            {"businessunitshortcode": "BusinessUnitShortCode"},
        )

        self.assertIsNone(lookup[("Assignment", "BusinessUnitName")])

    def test_generates_unique_object_source_ids(self):
        row = {"Nationality": "Saudi Arabian"}

        self.assertEqual(
            _generated_value(
                "SourceSystemOwner",
                "Worker",
                "SAEMP1001",
                row,
                "GRISMO",
            ),
            "GRISMO",
        )
        self.assertEqual(
            _generated_value(
                "SourceSystemId",
                "Worker",
                "SAEMP1001",
                row,
                "GRISMO",
            ),
            "wor_1001",
        )
        self.assertEqual(
            _generated_value(
                "AssignmentNumber",
                "Assignment",
                "SAEMP1001",
                row,
                "GRISMO",
            ),
            "E1001",
        )

    def test_source_system_id_uses_object_specific_prefix(self):
        self.assertEqual(
            _worker_source_system_id("Worker", "SAEMP1001"),
            "wor_1001",
        )
        self.assertEqual(
            _worker_source_system_id("PersonName", "SAEMP1001"),
            "pn_1001",
        )
        self.assertEqual(
            _worker_source_system_id("Worker", "emp1001"),
            "wor_1001",
        )
        self.assertEqual(
            _worker_source_system_id("PersonEmail", "1001"),
            "PE_1001",
        )

    def test_derives_country_values_for_supported_nationalities(self):
        self.assertEqual(
            _country_hdl_value("LegislationCode", "Saudi Arabian"),
            "SAU",
        )
        self.assertEqual(
            _country_hdl_value("Country", "Indian"),
            "IN",
        )
        self.assertEqual(
            _country_hdl_value("NationalIdentifierType", "India"),
            "Aadhaar",
        )
        with self.assertRaisesRegex(ValueError, "No HDL country values"):
            _country_hdl_value("Country", "Unknown")


if __name__ == "__main__":
    unittest.main()
