
from src.mysql_storage import get_connection


WORKER_ATTRIBUTES = {
    "Worker": [
        ("PersonNumber", "STRING", 1, 1, "Generated employee number"),
        ("EffectiveStartDate", "DATE", 1, 2, "Employment effective start date"),
        ("StartDate", "DATE", 1, 3, "Employment start date"),
        ("DateOfBirth", "DATE", 0, 4, "Employee date of birth"),
        ("ActionCode", "STRING", 0, 5, "Employment action code"),
        ("SourceSystemOwner", "STRING", 1, 6, "Source system owner"),
        ("SourceSystemId", "STRING", 1, 7, "Source system identifier"),
    ],
    "PersonName": [
        ("PersonNumber", "STRING", 1, 1, "Employee number"),
        ("EffectiveStartDate", "DATE", 1, 2, "Name effective start date"),
        ("EffectiveEndDate", "DATE", 0, 3, "Name effective end date"),
        ("NameType", "STRING", 1, 4, "Name type"),
        ("LegislationCode", "STRING", 0, 5, "Legislation code"),
        ("FirstName", "STRING", 1, 6, "Employee first name"),
        ("MiddleNames", "STRING", 0, 7, "Employee middle names"),
        ("LastName", "STRING", 1, 8, "Employee last name"),
        ("SourceSystemOwner", "STRING", 1, 9, "Source system owner"),
        ("SourceSystemId", "STRING", 1, 10, "Source system identifier"),
    ],
    "PersonNationalIdentifier": [
        ("PersonNumber", "STRING", 1, 1, "Employee number"),
        ("LegislationCode", "STRING", 1, 2, "Legislation code"),
        ("NationalIdentifierType", "STRING", 1, 3, "Identifier type"),
        ("NationalIdentifierNumber", "STRING", 1, 4, "Identifier number"),
        ("IssueDate", "DATE", 0, 5, "Identifier issue date"),
        ("ExpirationDate", "DATE", 0, 6, "Identifier expiration date"),
        ("SourceSystemOwner", "STRING", 1, 7, "Source system owner"),
        ("SourceSystemId", "STRING", 1, 8, "Source system identifier"),
    ],
    "PersonEmail": [
        ("PersonNumber", "STRING", 1, 1, "Employee number"),
        ("DateFrom", "DATE", 0, 2, "Email start date"),
        ("DateTo", "DATE", 0, 3, "Email end date"),
        ("EmailType", "STRING", 1, 4, "Email type"),
        ("EmailAddress", "STRING", 1, 5, "Email address"),
        ("SourceSystemOwner", "STRING", 1, 6, "Source system owner"),
        ("SourceSystemId", "STRING", 1, 7, "Source system identifier"),
    ],
    "PersonPhone": [
        ("PersonNumber", "STRING", 1, 1, "Employee number"),
        ("DateFrom", "DATE", 0, 2, "Phone start date"),
        ("DateTo", "DATE", 0, 3, "Phone end date"),
        ("PhoneType", "STRING", 1, 4, "Phone type"),
        ("PhoneNumber", "STRING", 1, 5, "Phone number"),
        ("CountryCodeNumber", "STRING", 0, 6, "Country calling code"),
        ("SourceSystemOwner", "STRING", 1, 7, "Source system owner"),
        ("SourceSystemId", "STRING", 1, 8, "Source system identifier"),
    ],
    "PersonAddress": [
        ("PersonNumber", "STRING", 1, 1, "Employee number"),
        ("EffectiveStartDate", "DATE", 1, 2, "Address effective start date"),
        ("EffectiveEndDate", "DATE", 0, 3, "Address effective end date"),
        ("AddressType", "STRING", 1, 4, "Address type"),
        ("AddressLine1", "STRING", 1, 5, "Address line 1"),
        ("AddressLine2", "STRING", 0, 6, "Address line 2"),
        ("TownOrCity", "STRING", 1, 7, "Town or city"),
        ("Region1", "STRING", 0, 8, "Region"),
        ("PostalCode", "STRING", 0, 9, "Postal code"),
        ("Country", "STRING", 1, 10, "Country code"),
        ("SourceSystemOwner", "STRING", 1, 11, "Source system owner"),
        ("SourceSystemId", "STRING", 1, 12, "Source system identifier"),
    ],
    "PersonLegislativeData": [
        ("PersonNumber", "STRING", 1, 1, "Employee number"),
        ("LegislationCode", "STRING", 1, 2, "Legislation code"),
        ("EffectiveStartDate", "DATE", 1, 3, "Legislative data start date"),
        ("EffectiveEndDate", "DATE", 0, 4, "Legislative data end date"),
        ("Sex", "STRING", 0, 5, "Sex"),
        ("MaritalStatus", "STRING", 0, 6, "Marital status"),
        ("HighestEducationLevel", "STRING", 0, 7, "Education level"),
        ("SourceSystemOwner", "STRING", 1, 8, "Source system owner"),
        ("SourceSystemId", "STRING", 1, 9, "Source system identifier"),
    ],
    "WorkRelationship": [
        ("PersonNumber", "STRING", 1, 1, "Employee number"),
        ("DateStart", "DATE", 1, 2, "Work relationship start date"),
        ("LegalEmployerName", "STRING", 1, 3, "Legal employer"),
        ("WorkerType", "STRING", 1, 4, "Worker type"),
        ("PrimaryFlag", "STRING", 0, 5, "Primary relationship flag"),
        ("SourceSystemOwner", "STRING", 1, 6, "Source system owner"),
        ("SourceSystemId", "STRING", 1, 7, "Source system identifier"),
    ],
    "WorkTerms": [
        ("PersonNumber", "STRING", 1, 1, "Employee number"),
        ("PeriodOfServiceId", "STRING", 0, 2, "Period of service identifier"),
        ("EffectiveStartDate", "DATE", 1, 3, "Work terms start date"),
        ("ActionCode", "STRING", 0, 4, "Employment action"),
        ("AssignmentName", "STRING", 0, 5, "Work terms name"),
        ("LegalEmployerName", "STRING", 1, 6, "Legal employer"),
        ("WorkerType", "STRING", 1, 7, "Worker type"),
        ("SourceSystemOwner", "STRING", 1, 8, "Source system owner"),
        ("SourceSystemId", "STRING", 1, 9, "Source system identifier"),
    ],
    "Assignment": [
        ("PersonNumber", "STRING", 1, 1, "Employee number"),
        ("EffectiveStartDate", "DATE", 1, 2, "Assignment start date"),
        ("EffectiveEndDate", "DATE", 0, 3, "Assignment end date"),
        ("AssignmentNumber", "STRING", 1, 4, "Assignment number"),
        ("AssignmentStatusType", "STRING", 1, 5, "Assignment status"),
        ("BusinessUnitName", "STRING", 1, 6, "Business unit"),
        ("DepartmentName", "STRING", 0, 7, "Department"),
        ("JobCode", "STRING", 0, 8, "Job code"),
        ("LocationCode", "STRING", 0, 9, "Location"),
        ("SourceSystemOwner", "STRING", 1, 10, "Source system owner"),
        ("SourceSystemId", "STRING", 1, 11, "Source system identifier"),
    ],
}


def seed_worker_attributes():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT object_id, object_name
            FROM hdl_objects
            WHERE template_id = %s AND active = 1
            """,
            (1,),
        )
        objects = cursor.fetchall()
        object_ids = {obj["object_name"]: obj["object_id"] for obj in objects}

        missing_objects = set(WORKER_ATTRIBUTES) - set(object_ids)
        if missing_objects:
            raise ValueError(
                f"Worker objects not found: {sorted(missing_objects)}"
            )

        cursor.execute("START TRANSACTION")

        inserted = 0

        for object_name, attributes in WORKER_ATTRIBUTES.items():
            object_id = object_ids[object_name]

            for name, data_type, required, sequence, description in attributes:
                cursor.execute(
                    """
                    SELECT attribute_id
                    FROM hdl_attributes
                    WHERE object_id = %s AND attribute_name = %s
                    """,
                    (object_id, name),
                )

                if cursor.fetchone():
                    continue

                generated = name in {
                    "PersonNumber",
                    "AssignmentNumber",
                    "SourceSystemOwner",
                    "SourceSystemId",
                }

                cursor.execute(
                    """
                    INSERT INTO hdl_attributes
                    (
                        object_id, attribute_name, data_type, required,
                        sequence_no, generated_field, default_value,
                        description, active
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1)
                    """,
                    (
                        object_id,
                        name,
                        data_type,
                        required,
                        sequence,
                        int(generated),
                        None,
                        description,
                    ),
                )
                inserted += 1

        connection.commit()
        print(f"Worker attributes added: {inserted}")
        print("Existing attributes were preserved.")

    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    seed_worker_attributes()
