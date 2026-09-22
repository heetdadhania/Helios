from typing import Any, Dict, List, Optional
try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore


class BaseRepository:
    """Base repository providing standardized SQL query execution and mapping on Databricks."""

    def __init__(self, cursor: Cursor) -> None:
        self.cursor = cursor

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a SQL query against Databricks and return result rows as dictionaries."""
        if parameters:
            self.cursor.execute(query, parameters)
        else:
            self.cursor.execute(query)

        description = self.cursor.description
        if not description:
            return []

        column_names = [col[0] for col in description]
        rows = self.cursor.fetchall()
        return [dict(zip(column_names, row)) for row in rows]

    def execute_single(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Execute query and return the first matching record or None."""
        results = self.execute_query(query, parameters)
        return results[0] if results else None

    def execute_non_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Execute DDL/DML statement that does not return rows."""
        if parameters:
            self.cursor.execute(query, parameters)
        else:
            self.cursor.execute(query)
