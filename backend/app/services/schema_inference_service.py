from datetime import date, datetime
from typing import Any, Dict, List
from app.schemas.dataset import ColumnSchema


class SchemaInferenceService:
    """Business service responsible for inferring data types and structural schemas."""

    DATABRICKS_TYPE_MAP = {
        "string": "string",
        "varchar": "string",
        "char": "string",
        "bigint": "integer",
        "int": "integer",
        "smallint": "integer",
        "tinyint": "integer",
        "double": "float",
        "float": "float",
        "decimal": "float",
        "boolean": "boolean",
        "timestamp": "datetime",
        "date": "date",
    }

    @classmethod
    def infer_python_type(cls, value: Any) -> str:
        """Infer canonical schema data type from a Python runtime value."""
        if value is None:
            return "string"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "float"
        if isinstance(value, (datetime, date)):
            return "datetime"
        return "string"

    @classmethod
    def infer_from_records(cls, records: List[Dict[str, Any]]) -> List[ColumnSchema]:
        """Infer list of column schemas across multiple dictionary records."""
        if not records:
            return []

        column_types: Dict[str, str] = {}
        column_nullability: Dict[str, bool] = {}

        for record in records:
            for key, val in record.items():
                if key not in column_types or column_types[key] == "string":
                    inferred = cls.infer_python_type(val)
                    if val is not None:
                        column_types[key] = inferred

                if key not in column_nullability:
                    column_nullability[key] = False
                if val is None:
                    column_nullability[key] = True

        return [
            ColumnSchema(
                name=col_name,
                data_type=column_types.get(col_name, "string"),
                nullable=column_nullability.get(col_name, True),
            )
            for col_name in column_types
        ]

    @classmethod
    def parse_databricks_describe(cls, describe_rows: List[Dict[str, Any]]) -> List[ColumnSchema]:
        """Convert output of Databricks DESCRIBE TABLE into ColumnSchema models."""
        columns: List[ColumnSchema] = []
        for row in describe_rows:
            col_name = row.get("col_name", "")
            data_type_raw = str(row.get("data_type", "")).lower()
            comment = row.get("comment")

            # Ignore internal partition or empty metadata lines from DESCRIBE output
            if not col_name or col_name.startswith("#") or not data_type_raw:
                continue

            canonical_type = cls.DATABRICKS_TYPE_MAP.get(data_type_raw, data_type_raw)
            columns.append(
                ColumnSchema(
                    name=col_name,
                    data_type=canonical_type,
                    nullable=True,
                    comment=str(comment) if comment else None,
                )
            )
        return columns
