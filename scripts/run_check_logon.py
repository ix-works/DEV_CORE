#!/usr/bin/env python3
"""Small CLI helper to check SAP ADT connectivity.

Prints a small result to stdout (no file I/O unless .conn_adt template is created).
Exit codes:
  0: success
  1: config missing / logon failed

IMPORTANT: This script looks for .conn_adt in the Claude Code working directory,
NOT in the plugin scripts directory. You can pass the working directory explicitly
using --cwd, or it will search in this order:
1. CLAUDE_CWD environment variable (set by Claude Code)
2. INIT_CWD environment variable
3. Current working directory
4. PWD environment variable

The .conn_adt file should be in your project folder (where you opened Claude Code).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Add the scripts directory to path so imports work correctly
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

# Set working directory BEFORE importing sap_client (which calls find_conn_file at import time)
from sap_adt_lib import set_explicit_working_dir

from sap_client import SAPClient


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Check SAP ADT connection and .conn_adt configuration'
    )
    parser.add_argument(
        '--cwd',
        type=str,
        help='Explicit working directory where .conn_adt is located '
             '(e.g., the project folder where Claude Code was opened)'
    )
    args = parser.parse_args()

    # If explicit cwd provided, set it before any SAP operations
    if args.cwd:
        set_explicit_working_dir(args.cwd)

    # Debug: Print working directory info to help troubleshoot
    cwd = Path.cwd()
    env_cwd = os.getenv('CLAUDE_CWD') or os.getenv('INIT_CWD')

    try:
        status = SAPClient.check_sap_config()

        # Add working directory info to status output for debugging
        status['working_directory'] = str(cwd)
        if env_cwd:
            status['claude_cwd'] = env_cwd
        if args.cwd:
            status['explicit_cwd'] = args.cwd

        if not status.get("configured"):
            print(json.dumps({"configured": False, **status}, indent=2))
            print("")
            print("=" * 60)
            print("[FAIL] LOGON CHECK FAILED - SAP is NOT configured")
            print("=" * 60)
            print("")
            print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
            print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
            print("=" * 60)
            return 1

        result = SAPClient.check_logon()
        print(json.dumps({"configured": True, **result}, indent=2))

        if not result.get("success"):
            print("")
            print("=" * 60)
            print("[FAIL] LOGON CHECK FAILED - could NOT log on to SAP")
            print("=" * 60)
            print("")
            print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
            print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
            print("=" * 60)
            return 1

        return 0
    except Exception as e:
        print("")
        print("=" * 60)
        print("[FAIL] LOGON CHECK FAILED - could NOT check SAP connectivity")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
