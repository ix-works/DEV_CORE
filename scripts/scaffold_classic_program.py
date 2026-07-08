#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scaffold_classic_program.py — klasik dialog ABAP iskeleti üret (gap-analysis #C2).

standards/06-coding-classic-dialog.md deseninde Main + koşullu include + OO ALV
(LCL_DATA/LCL_ALV/LCL_EVENT) iskeletini lokal dosyalar olarak üretir. SAP'ye YAZMAZ —
çıktı repo'da; reviewer + spec-mutabakat sonrası MCP push_source ile gider.

Kullanım:
    python scripts/scaffold_classic_program.py ZSD001_CLC_P_ORDER_LIST --out <source_root>/SD/ZSD001_CLC/programs/
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

MAIN = """\
*&---------------------------------------------------------------------*
*& Report {prog}
*& {desc}
*&---------------------------------------------------------------------*
REPORT {prog_lc}.

INCLUDE {prog_lc}_top.   " global data + LCL tanımları
INCLUDE {prog_lc}_cls.   " LCL implementasyonları
INCLUDE {prog_lc}_f01.   " FORM rutinleri (gerekirse)

START-OF-SELECTION.
  DATA(go_app) = NEW lcl_app( ).
  go_app->run( ).
"""

TOP = """\
*&---------------------------------------------------------------------*
*& Include {prog_lc}_top
*&---------------------------------------------------------------------*

" TODO: TABLES / SELECT-OPTIONS / PARAMETERS (text element TR — ADR 0005-D)

CLASS lcl_app DEFINITION DEFERRED.

CLASS lcl_data DEFINITION.
  PUBLIC SECTION.
    METHODS select_data.   " TODO: veri okuma (BAPI/SELECT — std tabloya direkt yazma yok)
ENDCLASS.

CLASS lcl_alv DEFINITION.
  PUBLIC SECTION.
    " ZSD000_CL_ALV_GRID reuse (ADR 0008 klasik kanonik) — sıfırdan CL_GUI_ALV_GRID kurma
    METHODS display.
ENDCLASS.

CLASS lcl_app DEFINITION.
  PUBLIC SECTION.
    METHODS run.
  PRIVATE SECTION.
    DATA mo_data TYPE REF TO lcl_data.
    DATA mo_alv  TYPE REF TO lcl_alv.
ENDCLASS.
"""

CLS = """\
*&---------------------------------------------------------------------*
*& Include {prog_lc}_cls
*&---------------------------------------------------------------------*

CLASS lcl_data IMPLEMENTATION.
  METHOD select_data.
    " TODO
  ENDMETHOD.
ENDCLASS.

CLASS lcl_alv IMPLEMENTATION.
  METHOD display.
    " TODO: ZSD000_CL_ALV_GRID ile sort/filtre/Kolonlar/Excel (ADR 0008)
  ENDMETHOD.
ENDCLASS.

CLASS lcl_app IMPLEMENTATION.
  METHOD run.
    mo_data = NEW lcl_data( ).
    mo_data->select_data( ).
    mo_alv = NEW lcl_alv( ).
    mo_alv->display( ).
  ENDMETHOD.
ENDCLASS.
"""

F01 = """\
*&---------------------------------------------------------------------*
*& Include {prog_lc}_f01
*&---------------------------------------------------------------------*
" FORM rutinleri (OO tercih; klasik gerekirse buraya).
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Klasik dialog ABAP iskeleti")
    ap.add_argument("program", help="Program adı (ZSDxxx_..._P_...)")
    ap.add_argument("--desc", default="<TODO: TR açıklama>", help="Açıklama (TR)")
    ap.add_argument("--out", default=".", help="Çıktı klasörü")
    args = ap.parse_args()

    if not args.program.upper().startswith(("Z", "Y")):
        print("[HATA] Program adı Z/Y ile başlamalı (ADR 0005-A)", file=sys.stderr)
        return 2

    prog = args.program.upper()
    ctx = {"prog": prog, "prog_lc": prog.lower(), "desc": args.desc}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    files = {
        f"{prog.lower()}.abap": MAIN,
        f"{prog.lower()}_top.abap": TOP,
        f"{prog.lower()}_cls.abap": CLS,
        f"{prog.lower()}_f01.abap": F01,
    }
    for fn, tmpl in files.items():
        (out / fn).write_text(tmpl.format(**ctx), encoding="utf-8")
        print(f"[OK] {out / fn}")
    print("→ Düzelt + text element TR + reviewer (run_review) → spec-mutabakat → MCP push_source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
