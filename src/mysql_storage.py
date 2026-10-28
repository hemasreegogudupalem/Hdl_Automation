
import json
from pathlib import Path

import mysql.connector


def load_settings(settings_path="config/settings.json"):
    """Load MySQL configuration from the JSON settings file."""
    path = Path(settings_path)

    if not path.is_absolute():
        path = Path.cwd() / path

    if not path.exists():
        raise FileNotFoundError(
            f"Settings file not found: {path.resolve()}"
        )

    with path.open("r", encoding="utf-8") as file:
        settings = json.load(file)

    if not isinstance(settings.get("mysql"), dict):
        raise ValueError(
            "The settings file must contain a 'mysql' object."
        )

    return settings


def get_connection(settings_path="config/settings.json"):
    """Create a MySQL connection using settings.json."""
    db = load_settings(settings_path)["mysql"]

    required = ["host", "user", "database"]
    missing = [key for key in required if not db.get(key)]

    if missing:
        raise ValueError(
            "Missing MySQL configuration: " + ", ".join(missing)
        )

    return mysql.connector.connect(
        host=db["host"],
        port=int(db.get("port", 3306)),
        user=db["user"],
        password=db.get("password", ""),
        database=db["database"],
    )


def test_connection(settings_path="config/settings.json"):
    """Test the connection and display basic database information."""
    connection = get_connection(settings_path)

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE(), VERSION()")
        database, version = cursor.fetchone()

        print("MySQL connection successful.")
        print(f"Database: {database}")
        print(f"MySQL version: {version}")

        cursor.close()
    finally:
        connection.close()


def fetch_all(query, params=None, settings_path="config/settings.json"):
    """Execute a read query and return rows as dictionaries."""
    connection = get_connection(settings_path)

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params or ())
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def get_table_columns(table_name, settings_path="config/settings.json"):
    """Return column names for a table in the current database."""
    allowed_tables = {
        "hdl_templates",
        "hdl_objects",
        "hdl_attributes",
        "hclients",
        "h_mappings",
    }

    if table_name not in allowed_tables:
        raise ValueError(f"Unsupported table: {table_name}")

    rows = fetch_all(
        f"DESCRIBE `{table_name}`",
        settings_path=settings_path,
    )

    return [row["Field"] for row in rows]


def get_templates(settings_path="config/settings.json"):
    """Read available HDL templates."""
    return fetch_all(
        "SELECT * FROM hdl_templates",
        settings_path=settings_path,
    )


def get_objects(template_id, settings_path="config/settings.json"):
    """Read objects belonging to a template."""
    columns = get_table_columns("hdl_objects", settings_path)

    if "template_id" not in columns:
        raise ValueError(
            "hdl_objects has no template_id column. "
            "Check its schema before querying objects."
        )

    return fetch_all(
        "SELECT * FROM hdl_objects WHERE template_id = %s",
        (template_id,),
        settings_path,
    )


def get_attributes(object_id, settings_path="config/settings.json"):
    """Read attributes belonging to an HDL object."""
    columns = get_table_columns("hdl_attributes", settings_path)

    object_column = next(
        (name for name in ("object_id", "hdl_object_id")
         if name in columns),
        None,
    )

    if object_column is None:
        raise ValueError(
            "Could not find an object ID column in hdl_attributes. "
            "Check the table structure."
        )

    return fetch_all(
        f"SELECT * FROM hdl_attributes WHERE `{object_column}` = %s",
        (object_id,),
        settings_path,
    )


def get_field_mappings(settings_path="config/settings.json"):
    """Read mapping records from the existing h_mappings table."""
    return fetch_all(
        "SELECT * FROM h_mappings",
        settings_path=settings_path,
    )


def get_active_clients(settings_path="config/settings.json"):
    """Read active client records used for generated HDL source identifiers."""
    return fetch_all(
        "SELECT * FROM hclients WHERE active = 1",
        settings_path=settings_path,
    )


def _is_active(row):
    """Treat omitted active flags as enabled for compatible schemas."""
    value = row.get("active", True)
    if isinstance(value, str):
        return value.strip().casefold() in {"1", "true", "yes", "y"}
    return bool(value)


def load_template_configuration(
    settings_path="config/settings.json",
    template_name=None,
):
    """Load one active template and normalize its objects for the CLI."""
    templates = [
        row for row in get_templates(settings_path)
        if _is_active(row)
    ]

    if template_name:
        templates = [
            row for row in templates
            if str(row.get("template_name", "")).casefold()
            == template_name.casefold()
        ]

    if not templates:
        raise ValueError(
            f"No matching HDL template found: {template_name or 'any'}"
        )

    template = templates[0]
    clients = get_active_clients(settings_path)
    if len(clients) != 1:
        raise ValueError(
            "Expected exactly one active client for HDL source identifiers; "
            f"found {len(clients)}."
        )
    source_system_owner = clients[0].get("source_system_owner")
    if not source_system_owner:
        raise ValueError(
            "The active client has no source_system_owner configured."
        )
    template["source_system_owner"] = source_system_owner

    mappings = [
        mapping for mapping in get_field_mappings(settings_path)
        if _is_active(mapping)
    ]
    objects = [
        obj for obj in get_objects(template.get("template_id"), settings_path)
        if _is_active(obj)
    ]

    normalized_objects = []
    for obj in objects:
        attributes = [
            attribute
            for attribute in get_attributes(obj.get("object_id"), settings_path)
            if _is_active(attribute)
        ]
        attributes.sort(key=lambda attribute: attribute.get("sequence_no", 0))
        if not attributes:
            raise ValueError(
                f"No active attributes are configured for HDL object "
                f"'{obj.get('object_name')}' in template "
                f"'{template.get('template_name')}'."
            )

        attribute_by_id = {
            attribute.get("attribute_id"): attribute
            for attribute in attributes
        }
        object_mappings = []
        for mapping in mappings:
            if mapping.get("object_id") != obj.get("object_id"):
                continue

            attribute = attribute_by_id.get(mapping.get("attribute_id"))
            if attribute is None:
                raise ValueError(
                    f"Mapping {mapping.get('mapping_id')} for HDL object "
                    f"'{obj.get('object_name')}' references an inactive or "
                    "missing attribute."
                )

            object_mappings.append({
                **mapping,
                "field_name": attribute.get("attribute_name"),
                "excel_column": mapping.get("client_column_name"),
                "required": attribute.get("required"),
            })

        normalized_objects.append({
            **obj,
            "fields": [
                {
                    "field_name": attribute.get("attribute_name"),
                    "required_flag": attribute.get("required"),
                    "data_type": attribute.get("data_type"),
                    "generated_field": attribute.get("generated_field"),
                    "default_value": attribute.get("default_value"),
                }
                for attribute in attributes
            ],
            "mappings": object_mappings,
        })

    if not normalized_objects:
        raise ValueError(
            f"No active HDL objects are configured for template "
            f"'{template.get('template_name')}'."
        )

    return template, normalized_objects
