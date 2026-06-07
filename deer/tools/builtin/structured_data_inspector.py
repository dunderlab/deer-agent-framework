import json
import csv
import sqlite3
from typing import Any, Dict, List
from dataclasses import dataclass

from deer.tools import ToolProvider, tool
from deer.schema.io import Return


@dataclass
class StructuredDataInspector(ToolProvider):

    @tool()
    def inspect_json_keys(self, path: str) -> Return(schema=Dict[str, Any]):
        """Parses a JSON file to extract its structural schema (keys and data types). Use this to map out large configurations without saturating the context window with raw data."""
        safe_path = self.jailed_path(path)

        with open(safe_path, "r") as f:
            data = json.load(f)

        def get_schema(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {k: get_schema(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                if not obj:
                    return []
                # Return the schema of the first element as representative
                return [get_schema(obj[0])]
            else:
                return type(obj).__name__

        return {"schema": get_schema(data)}

    @tool()
    def preview_csv_columns(
        self, path: str, nrows: int = 5
    ) -> Return(headers=List[str], rows=List[List[Any]]):
        """Reads CSV headers and a small subset of rows. Essential for identifying column names, data formats, and delimiters before performing full analysis."""
        safe_path = self.jailed_path(path)

        headers = []
        rows = []
        with open(safe_path, "r", newline="") as f:
            reader = csv.reader(f)
            headers = next(reader, [])
            for i, row in enumerate(reader):
                if i >= nrows:
                    break
                rows.append(row)

        return {"headers": headers, "rows": rows}

    @tool()
    def query_sqlite_metadata(self, path: str) -> Return(tables=List[Dict[str, Any]]):
        """Connects to a local SQLite database to retrieve table schemas and column layouts. Provides the necessary relational blueprint to construct valid SQL queries."""
        safe_path = self.jailed_path(path)

        conn = sqlite3.connect(safe_path)
        try:
            cursor = conn.cursor()

            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()

            result = []
            for (table_name,) in tables:
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                # columns: (id, name, type, notnull, default_value, pk)
                cols_info = [
                    {
                        "name": c[1],
                        "type": c[2],
                        "notnull": bool(c[3]),
                        "pk": bool(c[5]),
                    }
                    for c in columns
                ]
                result.append({"table": table_name, "columns": cols_info})

            return {"tables": result}
        finally:
            conn.close()

    @tool(modifies_state=True)
    def execute_sqlite_statement(
        self, path: str, statement: str
    ) -> Return(rows_affected=int, success=bool, message=str):
        """Executes mutation statements (INSERT, UPDATE, DELETE) on a SQLite database. Returns the count of affected rows to verify the operational impact."""
        safe_path = self.jailed_path(path)

        conn = sqlite3.connect(safe_path)
        try:
            cursor = conn.cursor()
            cursor.execute(statement)
            rows_affected = cursor.rowcount
            conn.commit()
            return {
                "rows_affected": rows_affected,
                "success": True,
                "message": "Statement executed successfully",
            }
        except sqlite3.Error as e:
            return {
                "rows_affected": 0,
                "success": False,
                "message": str(e),
            }
        finally:
            conn.close()
