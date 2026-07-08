#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Push local object changes to SAP (complete workflow: lock -> upload -> activate -> unlock).

Usage:
    python push_object.py --name ZCL_MY_CLASS --type class --transport TRXXXXX --cwd /path/to/project

With explicit source file:
    python push_object.py --name ZCL_MY_CLASS --type class --source-file /path/to/ZCL_MY_CLASS.abap --transport TRXXXXX --cwd /path/to/project
"""
import argparse
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


def main():
    parser = argparse.ArgumentParser(
        description='Push local object changes to SAP (lock -> upload -> activate -> unlock)'
    )
    parser.add_argument('--name', required=True,
                       help='Object name (e.g., ZCL_MY_CLASS)')
    parser.add_argument('--type', default='class',
                       choices=['class', 'clas', 'interface', 'intf', 'program', 'prog',
                               'report', 'include', 'incl', 'functiongroup', 'fugr'],
                       help='Object type (default: class)')
    parser.add_argument('--transport',
                       help='Transport request number (e.g., TRXXXXXX)')
    parser.add_argument('--source-file',
                       help='Full path to local source file (optional, auto-detected if not provided)')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    if not args.transport:
        print("[FAIL] --transport is required.")
        print("[INFO] You MUST run list_transports.py --modifiable-only and ASK the user which transport to use.")
        print("[INFO] NEVER assume, fabricate, or reuse a transport number from memory.")
        return 1

    try:
        client = SAPClient()
        result = client.push_object(
            object_name=args.name,
            object_type=args.type,
            transport=args.transport,
            source_file=args.source_file
        )
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] PUSH FAILED - object {args.name} was NOT pushed to SAP")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user the push succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("[ACTION REQUIRED] Do NOT call push_object.py again without user confirmation.")
        print("[ACTION REQUIRED] Each retry creates new SAP transport tasks (ghost transports).")
        print("=" * 60)
        return 1

    # result is a dict with 'success' key (or True/False for backward compat)
    success = result.get('success') if isinstance(result, dict) else bool(result)

    if success:
        print(f"[OK] Push completed successfully: {args.name}")
        return 0
    else:
        error = result.get('error', '') if isinstance(result, dict) else ''
        error_type = result.get('error_type', '') if isinstance(result, dict) else ''
        print("")
        print("=" * 60)
        print(f"[FAIL] PUSH FAILED - object {args.name} was NOT pushed to SAP")
        print("=" * 60)
        if error:
            print(f"[ERROR] {error}")
        if error_type:
            print(f"[ERROR TYPE] {error_type}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user the push succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("[ACTION REQUIRED] Do NOT call push_object.py again without user confirmation.")
        print("[ACTION REQUIRED] Each retry may create new SAP transport tasks (ghost transports).")
        if error_type in ('SAPTransportError', 'SAPAuthenticationError'):
            print("[HINT] Run list_transports.py --modifiable-only and ask the user to pick a valid transport.")
        if error_type == 'SAPLockError':
            if '409' in error or 'transport' in error.lower() or 'CORRNR' in error:
                print("[HINT] Transport conflict: object is locked under a different transport.")
                print("")
                print("=" * 60)
                print("[CRITICAL] DO NOT re-push using the transport number from this error message.")
                print("[CRITICAL] That transport may belong to ANOTHER developer (different owner).")
                print("[CRITICAL] Using it would silently inject your changes into their transport request.")
                print("")
                print("[ACTION REQUIRED] STOP. Report the conflict to the user.")
                print("[ACTION REQUIRED] Run list_transports.py --modifiable-only and SHOW the list.")
                print("[ACTION REQUIRED] ASK the user which transport to use. Wait for their answer.")
                print("[ACTION REQUIRED] NEVER pick a transport yourself.")
                print("")
                print("[MANUAL FIX] If object is stuck:")
                print("  1. SM12 -> delete enqueue lock for this object")
                print("  2. SE01/SE09 -> move object from conflicting transport to the correct one")
                print("  3. Retry push only after user confirms which transport to use")
                print("=" * 60)
            else:
                print("[HINT] Object may be locked by another user. Ask user to check SM12.")
        if error_type == 'SAPActivationError':
            print("[HINT] Run syntax_check.py --name %s to diagnose." % args.name)
        print("=" * 60)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
