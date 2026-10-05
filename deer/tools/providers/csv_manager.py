import csv
from typing import Any, Dict, List, Literal
from dataclasses import dataclass
from itertools import islice

from deer.tools import ToolProvider, tool
from deer.tools.schemas import Return, Case


@dataclass
class CSVManager(ToolProvider):
    """
    Provides tools to analyze and manipulate CSV files.
    Designed to process data on disk to avoid overloading the agent's context window.
    """

    @tool(
        tests=[
            Case(
                {"path": "data.csv", "num_rows": 2},
                {"rows": list, "columns": ["name", "age"], "total_rows": 3},
                files={"data.csv": "name,age\nAlice,30\nBob,25\nCharlie,35"},
            ),
        ]
    )
    def read_sample(
        self, path: str, num_rows: int = 10
    ) -> Return(rows=List[Dict[str, Any]], columns=List[str], total_rows=int):
        """Reads a small sample of the CSV file. Use this first to understand the schema and data format before performing deeper analysis."""
        safe_path = self.jailed_path(path)

        with open(safe_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames or []
            # Use islice to avoid loading the whole file into memory
            rows = list(islice(reader, num_rows))

            # To get total rows without loading everything, we can use a quick line count
            f.seek(0)
            total_rows = sum(1 for line in f) - 1  # Subtract header

        return {"rows": rows, "columns": columns, "total_rows": max(0, total_rows)}

    @tool(
        tests=[
            Case(
                {"path": "data.csv", "column": "age", "value": "30"},
                {"rows": [{"name": "Alice", "age": "30"}], "count": 1},
                files={"data.csv": "name,age\nAlice,30\nBob,25\nCharlie,35"},
            ),
        ]
    )
    def filter_data(
        self, path: str, column: str, value: str
    ) -> Return(rows=List[Dict[str, Any]], count=int):
        """Filters the CSV and returns only the rows where the specified column matches the value. Ideal for finding specific records in large datasets."""
        safe_path = self.jailed_path(path)
        matches = []

        with open(safe_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get(column) == value:
                    matches.append(row)

        return {"rows": matches, "count": len(matches)}

    @tool(
        tests=[
            Case(
                {"path": "data.csv", "column": "age", "metric": "sum"},
                {"value": 90.0},
                files={"data.csv": "name,age\nAlice,30\nBob,25\nCharlie,35"},
            ),
        ]
    )
    def calculate_metric(
        self, path: str, column: str, metric: Literal["sum", "average", "max", "min"]
    ) -> Return(value=float):
        """Calculates a numeric metric (sum, average, max, or min) for a specific column. Use this to analyze trends or totals without reading all data."""
        safe_path = self.jailed_path(path)
        values = []

        with open(safe_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    val = float(row[column])
                    values.append(val)
                except (ValueError, KeyError):
                    continue

        if not values:
            return {"value": 0.0}

        if metric == "sum":
            res = sum(values)
        elif metric == "average":
            res = sum(values) / len(values)
        elif metric == "max":
            res = max(values)
        elif metric == "min":
            res = min(values)
        else:
            res = 0.0

        return {"value": float(res)}

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {"path": "data.csv", "row": {"name": "David", "age": "40"}},
                {"success": True},
                files={"data.csv": "name,age\nAlice,30"},
            ),
        ],
    )
    def append_row(self, path: str, row: Dict[str, Any]) -> Return(success=bool):
        """Appends a new row of data to the CSV file. The 'row' dictionary keys must match the CSV header."""
        safe_path = self.jailed_path(path)

        # We need to read the header first to ensure correct column order
        with open(safe_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            if not fieldnames:
                return {"success": False}

        with open(safe_path, mode="a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow(row)

        return {"success": True}
