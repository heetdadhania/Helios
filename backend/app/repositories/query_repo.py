import re
from typing import Any, Dict, List, Optional
from app.repositories.base import BaseRepository

# Strict alphanumeric/underscore identifier pattern to prevent SQL injection in DDL/Introspection
IDENTIFIER_REGEX = re.compile(r"^[a-zA-Z0-9_]+$")


class QueryRepository(BaseRepository):
    """Data access repository for introspecting and querying Databricks Unity Catalog tables."""

    @staticmethod
    def _sanitize_identifier(name: str) -> str:
        """Validate SQL identifiers (catalog, schema, table) against alphanumeric pattern."""
        clean = name.strip()
        if not IDENTIFIER_REGEX.match(clean):
            raise ValueError(f"Invalid SQL identifier: {name}")
        return f"`{clean}`"

    def list_tables(self, catalog: str, schema: str) -> List[Dict[str, Any]]:
        """List all tables under the specified Unity Catalog and schema."""
        cat = self._sanitize_identifier(catalog)
        sch = self._sanitize_identifier(schema)
        query = f"SHOW TABLES IN {cat}.{sch}"
        return self.execute_query(query)

    def describe_table(self, catalog: str, schema: str, table_name: str) -> List[Dict[str, Any]]:
        """Introspect columns and data types for a Delta Lake table in Unity Catalog."""
        cat = self._sanitize_identifier(catalog)
        sch = self._sanitize_identifier(schema)
        tbl = self._sanitize_identifier(table_name)
        query = f"DESCRIBE TABLE {cat}.{sch}.{tbl}"
        return self.execute_query(query)

    def sample_table_data(
        self,
        catalog: str,
        schema: str,
        table_name: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Fetch sample rows from a Delta table for preview and schema inference."""
        cat = self._sanitize_identifier(catalog)
        sch = self._sanitize_identifier(schema)
        tbl = self._sanitize_identifier(table_name)
        safe_limit = max(1, min(limit, 1000))
        query = f"SELECT * FROM {cat}.{sch}.{tbl} LIMIT {safe_limit}"
        return self.execute_query(query)

    def count_table_rows(self, catalog: str, schema: str, table_name: str) -> Optional[int]:
        """Return total row count of a Delta Lake table."""
        cat = self._sanitize_identifier(catalog)
        sch = self._sanitize_identifier(schema)
        tbl = self._sanitize_identifier(table_name)
        query = f"SELECT COUNT(*) AS total_count FROM {cat}.{sch}.{tbl}"
        result = self.execute_single(query)
        if result and "total_count" in result:
            return int(result["total_count"])
        return None
