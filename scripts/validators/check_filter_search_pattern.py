#!/usr/bin/env python3
"""check_filter_search_pattern.py — Rapor/liste filtre + value-help + grid arama deseni
standardını dayatır (FE-32). Kaynak: ZSD001 sales_order_report kanonik pilotu (2026-06-24);
standart: standards/03-coding-ui-fiori.md §filtre-arama · playbook/ui-freestyle-odata-v2.md.

NEDEN (canlı kanıt 2026-06-24): freestyle UI5 + OData V2 + SAP Gateway (/IWBEP) ortamında
`caseSensitive:false` UI5'e `$filter`'da `toupper()`/`tolower()` ÜRETTİRİR → /IWBEP expression
parser bu fonksiyonları DESTEKLEMEZ → HTTP 400 "Function toupper/tolower is not supported"
(SAP Note 1797736) → arama HİÇ sonuç döndürmez. Düz `substringof`/`startswith`/`endswith`
zaten HARF-DUYARSIZ (DB collation; probe: "gül"→"GÜLAK", 200) → caseSensitive'e GEREK YOK.

HARD (BLOCKER): ui webapp JS'inde `caseSensitive: false` KULLANIMI yasak (kod; yorum HARİÇ).
WARNING (bloklamaz): rapor `Filter.view.xml`'inde tek-değer `<Input ... valueHelpRequest>`
  → select-options için `<MultiInput>` olmalı (çoklu-değer + aralık standardı, FE-32).
  (Tüm raporlar replike edilince temizlenir → sonra HARD'a terfi adayı.)

Kapsam: ERP/**/ui/**/webapp/** (dist/ build-kopyası hariç).
Kullanım: python check_filter_search_pattern.py [--file <path>] [--strict]
Çıkış: 0 temiz (veya yalnız WARNING) · 1 BLOCKER (caseSensitive:false bulundu).
"""
# ENFORCES: FE-32
import argparse
import io
import re
import sys
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# kod-içi caseSensitive:false (yorum DEĞİL) — açık/kapalı tırnak/boşluk varyasyonları
_CASE_SENS = re.compile(r"caseSensitive\s*:\s*false", re.IGNORECASE)
# rapor filtre ekranında tek-değer F4 input (MultiInput olmalı).
# NOT: `<Input...valueHelpRequest` regex'i binding'deki `>` (ör. {ui>/...}) yüzünden
# kırılıyor → daha sağlam: valueHelpRequest VAR + MultiInput YOK ⇒ F4 düz Input'ta.
_VHREQ = re.compile(r"valueHelpRequest", re.IGNORECASE)
_MULTIINPUT = re.compile(r"<MultiInput\b", re.IGNORECASE)


def strip_line_comment(line: str) -> str:
    """// satır-yorumunu at (basit; string-içi // nadirdir, kabul). /* */ inline de at."""
    line = re.sub(r"/\*.*?\*/", "", line)
    idx = line.find("//")
    return line[:idx] if idx != -1 else line


def scan_js(path: Path):
    """JS'te kod-içi caseSensitive:false → [(satır_no, kod_parçası)] (yorumlar hariç)."""
    hits = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return hits
    for i, raw in enumerate(lines, 1):
        code = strip_line_comment(raw)
        if _CASE_SENS.search(code):
            hits.append((i, code.strip()))
    return hits


def scan_filter_view(path: Path):
    """Rapor Filter.view.xml'de F4 (valueHelpRequest) var ama MultiInput yok → tek-değer
    Input'ta F4 ⇒ select-options değil → WARNING."""
    try:
        txt = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
    return bool(_VHREQ.search(txt)) and not _MULTIINPUT.search(txt)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="run_review pozisyonel artifact")
    ap.add_argument("--file")
    ap.add_argument("--strict", action="store_true")
    args, _unknown = ap.parse_known_args()

    root = Path(__file__).resolve().parents[2]
    target = args.file or args.path

    if target:
        p = Path(target)
        js_files = [p] if p.suffix == ".js" else []
        view_files = [p] if p.name.lower().endswith("filter.view.xml") else []
    else:
        import os
        # PERF: rglob node_modules'ı (1184 dizin) dolaşıyordu → os.walk ile yürüyüş anında buda.
        _prune = {"node_modules", "dist", ".tmp", "tmp", ".git"}
        ui_files = []
        for dirpath, dirnames, filenames in os.walk(root / "ERP"):
            dirnames[:] = [d for d in dirnames if d.lower() not in _prune]
            if "ui" not in Path(dirpath).parts:  # yalnız ui/ ağacı
                continue
            ui_files += [Path(dirpath) / fn for fn in filenames]
        js_files = [f for f in ui_files if f.suffix == ".js"]
        view_files = [f for f in ui_files if f.name.lower() == "filter.view.xml"]

    blockers = []
    for f in js_files:
        for ln, code in scan_js(f):
            rel = f.relative_to(root) if str(f).startswith(str(root)) else f
            blockers.append((rel, ln, code))

    warnings = []
    for f in view_files:
        if scan_filter_view(f):
            rel = f.relative_to(root) if str(f).startswith(str(root)) else f
            warnings.append(rel)

    for rel, ln, code in blockers:
        print(f"[İHLAL] {rel}:{ln}  BLOCKER (FE-32): caseSensitive:false KULLANMA → "
              f"V2+/IWBEP toupper/tolower üretir → HTTP 400 (SAP Note 1797736). "
              f"Düz Contains/StartsWith/EndsWith zaten harf-duyarsız. → {code[:80]}")

    for rel in warnings:
        print(f"[UYARI] {rel}  WARNING (FE-32): rapor filtre ekranı tek-değer <Input valueHelpRequest> "
              f"kullanıyor → select-options için <MultiInput> olmalı (çoklu-değer+aralık; "
              f"kanonik: ZSD001 sales_order_report).")

    if blockers:
        print(f"\n{len(blockers)} BLOCKER (FE-32) — caseSensitive:false yasak. "
              f"new Filter(path, FilterOperator.Contains, q) (caseSensitive parametresi VERME) → "
              f"düz substringof, backend zaten harf-duyarsız.", file=sys.stderr)
        return 1
    if warnings:
        print(f"\n{len(warnings)} WARNING (FE-32) — rapor filtre ekranı select-options (MultiInput) değil. "
              f"Bloklamaz; replike sırasında MultiInput'a çevir. (Tümü temizlenince HARD'a terfi.)")
    if args.strict and warnings:
        return 1
    if not blockers and not warnings:
        print("[OK] filtre/VH/grid arama deseni ihlali yok (caseSensitive:false yok; rapor filtreleri select-options).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
