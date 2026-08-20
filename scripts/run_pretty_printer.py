#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bicimlendirilmis ABAP kaynagini SAP'den ALIR ve EKRANA BASAR. KAYDETMEZ.

⛔ ADIN VAAT ETTIGI SEY DEGIL (olculdu 2026-08-20, lider varsayimi CURUDU):
Bu arac SAP'nin `POST /sap/bc/adt/abapsource/prettyprinter` ucunu cagirir; o uc
DURUMSUZ bir BICIMLEME SERVISIDIR. Kaynagi GET eder, bicimlenmis metni RETURN eder.
`lock` YOK · `PUT source/main` YOK · `activate` YOK · `transport` YOK
(kanit: sap_client.py `pretty_print()` + sap_adt_lib.py `POST .../prettyprinter`;
canli kontrol: kosumdan once ve sonra aktif kaynak SHA'si AYNI).

⚠ Eski cikti metinleri bunu GIZLIYORDU: basarida "Pretty printer applied to: X",
hatada "X was NOT formatted in SAP" yaziyordu -- ikisi de olmayan bir sunucu
yazmasi iddia ediyor. O turda kayip olmadi (bicim zaten ayniydi, 0 satir fark)
ama FARK CIKSAYDI sessizce kaybolurdu ve "SAP bicimledi" sanilirdi.

Kaydetmek istiyorsan bicimlenmis metni alip AYRI bir push adimiyla yaz
(`push_object.py`) -- bu arac onu YAPMAZ.

Usage:
    python run_pretty_printer.py --object-name ZCL_MY_CLASS --object-type class --cwd /path/to/project
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
        description='Format ABAP source code using SAP Pretty Printer'
    )
    parser.add_argument('--object-name', required=True,
                       help='Object name (e.g., ZCL_MY_CLASS)')
    parser.add_argument('--object-type', default='class',
                       help='Object type: class, interface, program, include, function (default: class)')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    try:
        client = SAPClient()
        result = client.pretty_print(
            object_name=args.object_name,
            object_type=args.object_type
        )
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] Bicimlenmis kaynak ALINAMADI: {args.object_name}")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[BILGI] SUNUCU DEGISMEDI — bu arac zaten KAYDETMEZ; basarisiz olan")
        print("        okuma/bicimleme cagrisidir, bir SAP yazmasi DEGIL.")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("=" * 60)
        return 1

    if result:
        # ⛔ "applied to" DEME: hicbir sey uygulanmadi, yalnizca bicimlenmis metin
        # DONDU. Eski metin tam da bu yuzden liderin varsayimini besledi.
        print(f"[OK] Bicimlenmis kaynak DONDU: {args.object_name} ({len(result)} karakter)"
              if isinstance(result, str) else
              f"[OK] Bicimlenmis kaynak DONDU: {args.object_name}")
        print("[BILGI] SUNUCU DEGISMEDI — bu arac kaydetmez (lock/PUT/activate YOK).")
        print("        Kalici olmasini istiyorsan asagidaki metni AYRI bir push adimiyla yaz.")
        if isinstance(result, str):
            print(f"\nFormatted source ({len(result)} chars):")
            print(result)
        return 0
    else:
        print("")
        print("=" * 60)
        print(f"[FAIL] Bicimlenmis kaynak ALINAMADI: {args.object_name}")
        print("=" * 60)
        print("")
        print("[BILGI] SUNUCU DEGISMEDI — bu arac zaten KAYDETMEZ; basarisiz olan")
        print("        okuma/bicimleme cagrisidir, bir SAP yazmasi DEGIL.")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
