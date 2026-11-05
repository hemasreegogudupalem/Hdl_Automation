import numbers
import re
from pathlib import Path

import pandas as pd

from src.dat_generator import generate_hdl_bundle
from src.field_mapper import normalize_column_name
from src.validator import is_empty


CONTACT_METADATA_FIELDS = {
    "Contact": [
        "PersonId",
        "EffectiveStartDate",
        "EffectiveEndDate",
        "PersonNumber",
        "BloodType",
        "CorrespondenceLanguage",
        "StartDate",
        "DateOfBirth",
        "DateOfDeath",
        "CountryOfBirth",
        "RegionOfBirth",
        "TownOfBirth",
        "SourceSystemOwner",
        "SourceSystemId",
    ],
    "ContactLegislativeData": [
        "PersonLegislativeId",
        "EffectiveStartDate",
        "EffectiveEndDate",
        "PersonId(SourceSystemId)",
        "PersonNumber",
        "LegislationCode",
        "HighestEducationLevel",
        "MaritalStatus",
        "MaritalStatusDate",
        "Sex",
        "SourceSystemOwner",
        "SourceSystemId",
    ],
    "ContactName": [
        "PersonNameId",
        "EffectiveStartDate",
        "EffectiveEndDate",
        "PersonId(SourceSystemId)",
        "PersonNumber",
        "LegislationCode",
        "NameType",
        "FirstName",
        "MiddleNames",
        "LastName",
        "Honors",
        "KnownAs",
        "PreNameAdjunct",
        "MilitaryRank",
        "PreviousLastName",
        "Suffix",
        "Title",
        "CharSetContext",
        "SourceSystemOwner",
        "SourceSystemId",
    ],
    "ContactRelationship": [
        "ContactRelationshipId",
        "EffectiveStartDate",
        "EffectiveEndDate",
        "PersonId(SourceSystemId)",
        "PersonNumber",
        "RelatedPersonId",
        "RelatedPersonNumber",
        "ContactType",
        "StatutoryDependent",
        "EmergencyContactFlag",
        "PersonalFlag",
        "PrimaryContactFlag",
        "SequenceNumber",
        "SourceSystemOwner",
        "SourceSystemId",
        "LegislationCode",
    ],
    "ContactAddress": [
        "PersonAddrUsageId",
        "EffectiveStartDate",
        "EffectiveEndDate",
        "AddressType",
        "PersonId(SourceSystemId)",
        "PersonNumber",
        "AddressId",
        "AddressLine1",
        "AddressLine2",
        "Building",
        "FloorNumber",
        "TownOrCity",
        "Region1",
        "Region2",
        "Region3",
        "Country",
        "PostalCode",
        "LongPostalCode",
        "PrimaryFlag",
        "SourceSystemOwner",
        "SourceSystemId",
    ],
    "ContactEmail": [
        "EmailAddressId",
        "DateFrom",
        "DateTo",
        "PersonId(SourceSystemId)",
        "PersonNumber",
        "EmailType",
        "EmailAddress",
        "PrimaryFlag",
        "SourceSystemOwner",
        "SourceSystemId",
    ],
}

_RELATIONSHIPS = (
    {
        "source_field": "FatherName",
        "id_role": "FAT",
        "contact_type": "IN_FR",
        "sex": "M",
        "emergency": "Y",
        "primary": "N",
        "email_columns": ("fatheremail", "fatheremailaddress", "fatherpersonalemail"),
    },
    {
        "source_field": "MotherName",
        "id_role": "MOT",
        "contact_type": "IN_MR",
        "sex": "F",
        "emergency": "N",
        "primary": "N",
        "email_columns": ("motheremail", "motheremailaddress", "motherpersonalemail"),
    },
    {
        "source_field": "Spouse",
        "id_role": "SPO",
        "contact_type": "S",
        "sex": "",
        "emergency": "Y",
        "primary": "Y",
        "email_columns": ("spouseemail", "spouseemailaddress", "spousepersonalemail"),
    },
)

_COUNTRY_CODES = {
    "saudiarabian": "SA",
    "saudiarabia": "SA",
    "sa": "SA",
    "sau": "SA",
    "india": "IN",
    "indian": "IN",
    "in": "IN",
    "ind": "IN",
}


def _text(value):
    if is_empty(value):
        return ""
    if isinstance(value, numbers.Integral):
        return str(value)
    if isinstance(value, numbers.Real) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _split_contact_name(value):
    parts = re.split(r"\s+", _text(value))
    if not parts or not parts[0]:
        return "", "", ""
    if len(parts) == 1:
        return parts[0], "", ""
    return parts[0], " ".join(parts[1:-1]), parts[-1]


def _contact_source_id(role, person_number):
    return f"PER_{role}_{person_number}"


def _contact_country(value):
    return _COUNTRY_CODES.get(normalize_column_name(value), "")


def _append_record(output_objects, object_name, record):
    output_objects[object_name]["records"].append(record)


def build_contact_output_objects(dataframe, source_system_owner):
    """Build Contact HDL records from worker rows and their family columns."""
    normalized_columns = {
        normalize_column_name(column): column
        for column in dataframe.columns
    }

    def row_value(row, *names):
        for name in names:
            column = normalized_columns.get(normalize_column_name(name))
            if column is not None and not is_empty(row[column]):
                return row[column]
        return ""

    output_objects = {
        object_name: {
            "object_name": object_name,
            "metadata_fields": fields,
            "records": [],
        }
        for object_name, fields in CONTACT_METADATA_FIELDS.items()
    }

    for _, row in dataframe.iterrows():
        person_number = _text(row_value(
            row,
            "PersonNumber",
            "Person Number",
            "Employee Number",
            "Employee ID",
        ))
        if not person_number:
            continue

        effective_start_date = row_value(
            row,
            "EffectiveStartDate",
            "StartDate",
            "Start Date",
            "Date of Joining",
        )
        address = row_value(
            row,
            "Contact Address",
            "Home Address",
            "Address",
            "Address Line 1",
        )
        city = row_value(row, "Town / City", "TownOrCity", "City")
        country = _contact_country(row_value(row, "Country", "Nationality"))

        for relation in _RELATIONSHIPS:
            contact_name = row_value(row, relation["source_field"])
            if not contact_name:
                continue

            source_id = _contact_source_id(
                relation["id_role"],
                person_number,
            )
            contact_first_name, middle_names, last_name = _split_contact_name(
                contact_name
            )
            legislative_code = country

            _append_record(output_objects, "Contact", {
                "EffectiveStartDate": effective_start_date,
                "StartDate": effective_start_date,
                "CountryOfBirth": "",
                "SourceSystemOwner": source_system_owner,
                "SourceSystemId": source_id,
            })
            _append_record(output_objects, "ContactLegislativeData", {
                "EffectiveStartDate": effective_start_date,
                "PersonId(SourceSystemId)": source_id,
                "LegislationCode": legislative_code,
                "Sex": relation["sex"],
                "SourceSystemOwner": source_system_owner,
                "SourceSystemId": f"LEG_{relation['id_role']}_{person_number}",
            })
            _append_record(output_objects, "ContactName", {
                "EffectiveStartDate": effective_start_date,
                "PersonId(SourceSystemId)": source_id,
                "LegislationCode": legislative_code,
                "NameType": "GLOBAL",
                "FirstName": contact_first_name,
                "MiddleNames": middle_names,
                "LastName": last_name,
                "SourceSystemOwner": source_system_owner,
                "SourceSystemId": f"NM_{relation['id_role']}_{person_number}",
            })
            _append_record(output_objects, "ContactRelationship", {
                "EffectiveStartDate": effective_start_date,
                "PersonId(SourceSystemId)": source_id,
                "RelatedPersonNumber": person_number,
                "ContactType": relation["contact_type"],
                "EmergencyContactFlag": relation["emergency"],
                "PersonalFlag": "Y",
                "PrimaryContactFlag": relation["primary"],
                "SequenceNumber": "1",
                "SourceSystemOwner": source_system_owner,
                "SourceSystemId": f"REL_{relation['id_role']}_{person_number}",
                "LegislationCode": legislative_code,
            })

            if address:
                _append_record(output_objects, "ContactAddress", {
                    "EffectiveStartDate": effective_start_date,
                    "AddressType": "HOME",
                    "PersonId(SourceSystemId)": source_id,
                    "AddressLine1": address,
                    "TownOrCity": city,
                    "Country": country,
                    "PrimaryFlag": "Y",
                    "SourceSystemOwner": source_system_owner,
                    "SourceSystemId": f"ADD_{relation['id_role']}_{person_number}",
                })

            email = row_value(row, *relation["email_columns"])
            if email:
                _append_record(output_objects, "ContactEmail", {
                    "DateFrom": effective_start_date,
                    "PersonId(SourceSystemId)": source_id,
                    "EmailType": "H1",
                    "EmailAddress": _text(email),
                    "PrimaryFlag": "Y",
                    "SourceSystemOwner": source_system_owner,
                    "SourceSystemId": f"EML_{relation['id_role']}_{person_number}",
                })

    return list(output_objects.values())


def generate_contact_dat(dataframe, source_system_owner, output_dir):
    """Write Contact.dat using the standard HDL bundle writer."""
    output_file = Path(output_dir) / "Contact.dat"
    return generate_hdl_bundle(
        output_file,
        build_contact_output_objects(dataframe, source_system_owner),
    )
