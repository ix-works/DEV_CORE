#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Execute SQL SELECT query via SAP ADT datapreview.

Usage:
    python run_sql_query.py --query "SELECT * FROM ZSD000_T_CONFIG" --max-rows 10 --cwd /path/to/project
    python run_sql_query.py --query "SELECT * FROM ZSD000_T_HISTORY" --max-rows 5 --format json --cwd /path/to/project
    python run_sql_query.py --query "SELECT * FROM ZSD000_T_HISTORY" --max-rows 5 --columns UNAME,MODEL --cwd /path/to/project
"""
import argparse
import csv
import json
import sys
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add scripts directory to path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from sap_adt_lib import set_explicit_working_dir
from sap_client import SAPClient


def truncate(val, width):
    """Truncate a value to fit within width, adding ... if needed."""
    s = str(val) if val is not None else "NULL"
    if len(s) > width:
        return s[:width - 3] + "..."
    return s.ljust(width)


def format_table(result, max_col_width=50, selected_columns=None):
    """Print result as a formatted table with auto-sized columns."""
    columns = list(result['columns'])
    data = [list(row) for row in result['data']]

    # Filter columns if specified
    if selected_columns:
        sel_upper = [c.upper() for c in selected_columns]
        indices = [i for i, c in enumerate(columns) if c.upper() in sel_upper]
        if not indices:
            print(f"[WARNING] None of the requested columns found. Available: {', '.join(columns)}")
            return
        columns = [columns[i] for i in indices]
        data = [[row[i] for i in indices] for row in data]

    # Auto-size: max(header_len, max_data_len) capped at max_col_width
    widths = []
    for i, col in enumerate(columns):
        max_w = len(col)
        for row in data:
            val = str(row[i]) if i < len(row) and row[i] is not None else "NULL"
            max_w = max(max_w, len(val))
        widths.append(min(max_w, max_col_width))

    # Print
    header = " | ".join(truncate(c, widths[i]) for i, c in enumerate(columns))
    separator = "-+-".join("-" * w for w in widths)
    print(header)
    print(separator)
    for row in data:
        print(" | ".join(truncate(row[i] if i < len(row) else None, widths[i]) for i in range(len(columns))))


def format_json(result, selected_columns=None):
    """Print result as JSON."""
    columns = list(result['columns'])
    data = result['data']

    if selected_columns:
        sel_upper = [c.upper() for c in selected_columns]
        indices = [i for i, c in enumerate(columns) if c.upper() in sel_upper]
        columns = [columns[i] for i in indices]
        data = [[row[i] for i in indices] for row in data]

    rows = []
    for row in data:
        rows.append({columns[i]: row[i] for i in range(len(columns))})

    output = {
        'total_rows': result['total_rows'],
        'execution_time': result['execution_time'],
        'columns': columns,
        'data': rows
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def format_csv(result, selected_columns=None):
    """Print result as CSV."""
    columns = list(result['columns'])
    data = result['data']

    if selected_columns:
        sel_upper = [c.upper() for c in selected_columns]
        indices = [i for i, c in enumerate(columns) if c.upper() in sel_upper]
        columns = [columns[i] for i in indices]
        data = [[row[i] for i in indices] for row in data]

    writer = csv.writer(sys.stdout)
    writer.writerow(columns)
    for row in data:
        writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(
        description='Execute SQL SELECT query via SAP ADT'
    )
    parser.add_argument('--query', required=True,
                       help='SQL SELECT query (ABAP SQL syntax)')
    parser.add_argument('--max-rows', type=int, default=100,
                       help='Maximum rows to return (default: 100)')
    parser.add_argument('--format', choices=['table', 'json', 'csv'], default='table',
                       help='Output format (default: table)')
    parser.add_argument('--max-col-width', type=int, default=50,
                       help='Max column width in table mode (default: 50)')
    parser.add_argument('--columns',
                       help='Comma-separated list of columns to include')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    selected_columns = [c.strip() for c in args.columns.split(',')] if args.columns else None

    try:
        client = SAPClient()
        result = client.run_sql_query(
            query=args.query,
            max_rows=args.max_rows
        )
    except Exception as e:
        print("")
        print("=" * 60)
        print("[FAIL] SQL QUERY FAILED - query was NOT executed in SAP")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if not result:
        print("")
        print("=" * 60)
        print("[FAIL] SQL QUERY FAILED - query was NOT executed in SAP")
        print("=" * 60)
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    # Print metadata (skip for csv/json to keep output clean)
    if args.format == 'table':
        print(f"\nQuery executed successfully")
        print(f"Total rows: {result['total_rows']}")
        print(f"Execution time: {result['execution_time']:.3f}s")
        print(f"Returned: {len(result['data'])} rows\n")

    if not result['columns']:
        print("No columns returned.")
        return 0

    if args.format == 'json':
        format_json(result, selected_columns)
    elif args.format == 'csv':
        format_csv(result, selected_columns)
    else:
        format_table(result, max_col_width=args.max_col_width, selected_columns=selected_columns)
        print(f"\nShowing {len(result['data'])} of {result['total_rows']} total rows")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
