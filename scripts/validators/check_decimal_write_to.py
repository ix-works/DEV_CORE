#!/usr/bin/env python3
"""check_decimal_write_to.py — API/JSON body string'ine decimal/quantity serileştirirken
`WRITE <x> TO <y>` kullanımını yakalar (memory: feedback_abap-decimal-odata-serialize-locale).

NEDEN: `WRITE lv_qty TO lv_str.` ABAP locale'ine göre binlik ayıraç ekler ('1111' → '1.111.000')
→ JSON body'de Edm.Decimal alanı HTTP 400 döner. ÇÖZÜM: packed → string DİREKT atama
(lv_str = lv_qty), '.' ondalık, gruplama yok. ZSD001 simülasyon 1111→'1.111.000' bug.

KONSERVATİF tespit (gürültülü validator yok sayılır): SADECE dosyanın HERHANGİ bir yerinde
API-body marker'ı (web_request / request_body / /ui2/cl_json / cl_http / iv_request_body /
payload) GEÇİYORSA, o dosyadaki `WRITE ... TO ...` satırları işaretlenir. Normal ALV/rapor
class'ı (marker yok) işaretlenmez. WARNING seviyesi.

Kullanım:
    python check_decimal_write_to.py [--file <path>] [--strict]
    (--file verilmezse <source_root>/ altındaki *.clas.abap / *.abap taranır)
Çıkış: 0 temiz/uyarı, 1 ihlal (--strict ile WARNING de fail).
"""
# ENFORCES: BE-04  (ADR 0019 coverage binding)
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

# API-body inşa eden class işareti — bu marker'lardan biri dosyada varsa scope içindeyiz.
_API_MARKERS = re.compile(
    r"web_request|request_body|/ui2/cl_json|cl_http|iv_request_body|payload",
    re.IGNORECASE,
)
# WRITE <x> TO <y> — locale'li serileştirme (WRITE ... TO yapısı).
_WRITE_TO = re.compile(r"\bWRITE\s+.+?\s+TO\s+\S", re.IGNORECASE)


def file_has_api_marker(text):
    """Dosya API-body inşa ediyor mu? (scope filtresi)"""
    return bool(_API_MARKERS.search(text))


def scan_text(text):
    """(line_no, line) ihlal listesi döner. SADECE dosyada API marker varsa çalışır."""
    if not file_has_api_marker(text):
        return []
    hits = []
    for i, raw in enumerate(text.splitlines(), 1):
        line = raw.split('"', 1)[0]  # satır-içi yorum at
        if _WRITE_TO.search(line):
            hits.append((i, raw.strip()))
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
            print(f"[İHLAL] {rel}:{ln}  WARNING: API-body class'ında 'WRITE ... TO' decimal'e "
                  f"binlik ayıraç ekler (Edm.Decimal 400) → 'lv_str = lv_packed' DİREKT atama "
                  f"kullan: {content}")

    if total:
        print(f"\n{total} uyarı — API-body inşa eden class'ta 'WRITE ... TO' decimal/qty "
              f"serileştirmesi locale ayıracı ekler. Direkt packed→string atama kullan.")
        return 1
    print("[OK] API-body class'ında 'WRITE ... TO' decimal serileştirme ihlali yok.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
