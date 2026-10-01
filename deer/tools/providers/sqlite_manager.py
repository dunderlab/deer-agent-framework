import sqlite3
from typing import Any, Dict, List
from dataclasses import dataclass

from deer.tools import ToolProvider, tool
from deer.tools.schemas import Return, Case


@dataclass
class SQLiteManager(ToolProvider):
    """
    Provides tools to inspect and modify SQLite databases.
    Used for analyzing relational schemas and performing data mutations.
    """

    @tool(
        tests=[
            # Test: Inspecting a new/empty database should return no tables
            Case({"path": "empty.db"}, {"tables": []}),
        ]
    )
    def inspect_schema(self, path: str) -> Return(tables=List[Dict[str, Any]]):
        """Retrieves the schema of all tables in the SQLite database at 'path', including column names, types, and primary keys."""
        safe_path = self.jailed_path(path)

        with sqlite3.connect(safe_path) as conn:
            cursor = conn.cursor()

            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()

            result = []
            for (table_name,) in tables:
                # Get column metadata for each table
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

    @tool(
        modifies_state=True,
        tests=[
            # Test: Successful table creation
            Case(
                {
                    "path": "test.db",
                    "statement": "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)",
                },
                {"rows_affected": int, "success": True, "message": str},
            ),
            # Test: Failed mutation (insert into non-existent table)
            Case(
                {
                    "path": "test.db",
                    "statement": "INSERT INTO nonexistent (id) VALUES (1)",
                },
                {"rows_affected": 0, "success": False, "message": str},
            ),
            # Test: SQL syntax error
            Case(
                {"path": "test.db", "statement": "INVALID SQL STATEMENT"},
                {"rows_affected": 0, "success": False, "message": str},
            ),
        ],
    )
    def execute_mutation(
        self, path: str, statement: str
    ) -> Return(rows_affected=int, success=bool, message=str):
        """Executes a data mutation statement (INSERT, UPDATE, DELETE) on the SQLite database at 'path'. Returns the number of affected rows."""
        safe_path = self.jailed_path(path)

        try:
            with sqlite3.connect(safe_path) as conn:
                cursor = conn.cursor()
                cursor.execute(statement)
                rows_affected = cursor.rowcount
                conn.commit()
                return {
                    "rows_affected": rows_affected,
                    "success": True,
                    "message": "Mutation executed successfully.",
                }
        except sqlite3.Error as e:
            return {
                "rows_affected": 0,
                "success": False,
                "message": f"SQLite error: {str(e)}",
            }
