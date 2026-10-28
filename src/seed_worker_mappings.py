import argparse

import pandas as pd

from src.field_mapper import load_field_mappings, normalize_column_name
from src.mysql_storage import (
    fetch_all,
    get_attributes,
    get_connection,
    get_field_mappings,
    get_objects,
)


def build_mapping_plan(
    objects,
    columns,
    aliases,
    existing_mappings,
    settings_path="config/settings.json",
):
    """Create unique alias-based mappings without overriding existing rows."""
    column_lookup = {}
    for column in columns:
        column_lookup.setdefault(normalize_column_name(column), []).append(column)

    existing_keys = {
        (mapping.get("object_id"), mapping.get("attribute_id"))
        for mapping in existing_mappings
    }
    planned = []
    ambiguous = []
    unmatched_required = []

    for obj in objects:
        if not obj.get("active"):
            continue

        for attribute in get_attributes(obj["object_id"], settings_path):
            if not attribute.get("active"):
                continue

            key = (obj["object_id"], attribute["attribute_id"])
            if key in existing_keys:
                continue

            field_name = attribute["attribute_name"]
            names = [field_name, *aliases.get(field_name, [])]
            candidates = sorted({
                column
                for name in names
                for column in column_lookup.get(normalize_column_name(name), [])
            })

            if len(candidates) == 1:
                planned.append({
                    "object_id": obj["object_id"],
                    "attribute_id": attribute["attribute_id"],
                    "field_name": field_name,
                    "client_column_name": candidates[0],
                })
            elif len(candidates) > 1:
                ambiguous.append({
                    "object_name": obj["object_name"],
                    "field_name": field_name,
                    "columns": candidates,
                })
            elif attribute.get("required"):
                unmatched_required.append({
                    "object_name": obj["object_name"],
                    "field_name": field_name,
                })

    return planned, ambiguous, unmatched_required


def seed_worker_mappings(
    input_file="input/saudi_employee_data.xlsx",
    settings_path="config/settings.json",
):
    """Insert only unique Excel-column matches for the Worker template."""
    df = pd.read_excel(input_file)
    aliases = load_field_mappings()
    objects = get_objects(1, settings_path)
    existing = get_field_mappings(settings_path)
    planned, ambiguous, unmatched_required = build_mapping_plan(
        objects,
        [str(column).strip() for column in df.columns],
        aliases,
        existing,
        settings_path,
    )

    clients = fetch_all(
        "SELECT client_id FROM hclients WHERE active = 1",
        settings_path=settings_path,
    )
    if len(clients) != 1:
        raise ValueError(
            "Expected exactly one active client to assign the new mappings; "
            f"found {len(clients)}."
        )

    connection = get_connection(settings_path)
    cursor = connection.cursor()
    try:
        cursor.executemany(
            """
            INSERT INTO h_mappings
            (
                client_id, object_id, attribute_id, client_column_name,
                mapping_type, default_value, transformation_rule, active
            )
            VALUES (%s, %s, %s, %s, 'DIRECT', NULL, NULL, 1)
            """,
            [
                (
                    clients[0]["client_id"],
                    mapping["object_id"],
                    mapping["attribute_id"],
                    mapping["client_column_name"],
                )
                for mapping in planned
            ],
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()

    print(f"Excel-column mappings added: {len(planned)}")
    print(f"Ambiguous fields left unmapped: {len(ambiguous)}")
    for item in ambiguous:
        print(
            f"  {item['object_name']}.{item['field_name']}: "
            f"{', '.join(item['columns'])}"
        )
    print(f"Required fields without a matching column: {len(unmatched_required)}")
    for item in unmatched_required:
        print(f"  {item['object_name']}.{item['field_name']}")


def main():
    parser = argparse.ArgumentParser(
        description="Create unique Excel-column mappings for the Worker template"
    )
    parser.add_argument(
        "--input",
        default="input/saudi_employee_data.xlsx",
        help="Excel workbook used to match source columns",
    )
    parser.add_argument(
        "--settings",
        default="config/settings.json",
        help="Path to MySQL settings JSON",
    )
    args = parser.parse_args()
    seed_worker_mappings(args.input, args.settings)


if __name__ == "__main__":
    main()
