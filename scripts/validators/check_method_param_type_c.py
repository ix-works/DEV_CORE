#!/usr/bin/env python3
"""check_method_param_type_c.py — Source-based ABAP class METHOD parametresinde
`TYPE c LENGTH n` kullanımını yakalar (2026-06-11 dersi, adt-rap §34-A).

NEDEN: Source-based class'ta method IMPORTING/EXPORTING/CHANGING/RETURNING param'ında
`TYPE c LENGTH 100` → save reddedilir (OO_SOURCE_BASED / ResourceScanDuringSaveFailure,
SATIR NO YOK) → saatlerce patinaj. Aynı `TYPE c LENGTH 220` TYPES/struct'ta sorunsuz —
sadece method imzasında kırar. ÇÖZÜM: `TYPE string` veya DDIC data element.

Bu KÖR-NOKTA idi: hata satırsız geldiği için körlemesine bisect gerekti. Validator
deterministik regex ile yazma-ÖNCESİ yakalar → bisect'e gerek kalmaz.

Kullanım:
    python check_method_param_type_c.py [--file <path>] [--strict]
    (--file verilmezse <source_root>/ altındaki tüm *.clas.abap / *.abap taranır)
Çıkış: 0 temiz/uyarı, 1 ihlal (--strict ile WARNING de fail).
"""
# ENFORCES: BE-10a  (ADR 0019 coverage binding)
import argparse
import io
import re
import sys
from pathlib import Path
import sys as _pc_sys
from pathlib import Path as _pc_Path
_pc_sys.path.insert(0, str(_pc_Path(__file__).resolve().parents[1]))
from utils.project_config import SOURCE_ROOT_NAME  # K12: kaynak-klasor adi config'ten

if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# METHODS / CLASS-METHODS bildirimi (gövde DEĞİL) — imza bloğu içinde TYPE c LENGTH ara.
_METHODS_START = re.compile(r"^\s*(CLASS-METHODS|METHODS)\b", re.IGNORECASE)
_TYPE_C_LEN = re.compile(r"\bTYPE\s+c\s+LENGTH\s+\d+", re.IGNORECASE)
# Gövde başlangıcı (METHOD impl) — imza taramasını orada durdur.
_METHOD_IMPL = re.compile(r"^\s*METHOD\s+\w", re.IGNORECASE)


def scan_text(text):
    """(line_no, line) ihlal listesi döner. METHODS bildiriminden onu kapatan '.'a
    kadar olan blok içinde TYPE c LENGTH n geçişlerini bulur."""
    hits = []
    lines = text.splitlines()
    in_decl = False
    for i, raw in enumerate(lines, 1):
        line = raw.split('"', 1)[0]  # satır-içi yorum at
        if _METHOD_IMPL.match(line):
            in_decl = False
            continue
        if _METHODS_START.match(line):
            in_decl = True
        if in_decl and _TYPE_C_LEN.search(line):
            hits.append((i, raw.strip()))
        if in_decl and line.rstrip().endswith("."):
            in_decl = False
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="taranacak dosya (run_review pozisyonel artifact)")
    ap.add_argument("--file")
    ap.add_argument("--strict", action="store_true")
    args, _unknown = ap.parse_known_args()  # run_review ek flag geçebilir → yut

    root = Path(__file__).resolve().parents[2]
    target = args.file or args.path
    if target:
        files = [Path(target)]
    else:
        files = list((root / SOURCE_ROOT_NAME).rglob("*.clas.abap")) + \
            [p for p in (root / SOURCE_ROOT_NAME).rglob("*.abap") if not p.name.endswith(".clas.abap")]

    total = 0
    for f in files:
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for ln, content in scan_text(txt):
            total += 1
            rel = f.relative_to(root) if str(f).startswith(str(root)) else f
            print(f"[İHLAL] {rel}:{ln}  method-param 'TYPE c LENGTH' → 'TYPE string' kullan "
                  f"(adt-rap §34-A): {content}")

    if total:
        print(f"\n{total} ihlal — source-based class method-param'da TYPE c LENGTH n save-scan'i "
              f"kırar (satırsız 400). TYPE string / DDIC element kullan.")
        return 1
    print("[OK] method-param TYPE c LENGTH ihlali yok.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
