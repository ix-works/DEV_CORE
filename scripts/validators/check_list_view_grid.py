#!/usr/bin/env python3
"""check_list_view_grid.py — Liste/rapor ekranlarının sap.m.Table yerine sap.ui.table (grid)
kullanmasını dayatır (memory: feedback_grid-liste-standardi / liste-ekrani-alv-standardi, ADR 0008).

NEDEN: ALV-tarzı liste/rapor = sap.ui.table.Table (grid): yatay+sanal scroll, native sort/filter,
DB varyant + TablePersonalizer. sap.m.Table mobil istisnadır; çok kolonlu liste için grid şart.

KONSERVATİF tespit (SADECE *.view.xml). İşaretleme koşulu = HEPSİ (a∧b∧c):
  (a) dosya adı `list/report/liste/rapor` içerir (case-insensitive),
  (b) view'de GERÇEKTEN bir `sap.m.Table` var (`<Table>`),
  (c) view HİÇBİR yerde `sap.ui.table` namespace'i kullanmıyor.
2026-06-18 triage (A-2): ">=5 kolon" sezgisi (detay-form item-table FP) + "tablosuz
List" (akordion belge-listesi FP, feedback_belge-uygulama-ortak-ui-sablonu) KALDIRILDI.
Yalnız gerçek tablo-tarzı liste ekranı (m.Table, grid değil) işaretlenir. Emin değilse
işaretleme (FN tercih). HARD (terfi 2026-06-18): bulgu = exit 1 (BLOCKER).

Kullanım:
    python check_list_view_grid.py [--file <path>]
    (--file verilmezse <source_root>/ altındaki ui/**/*.view.xml taranır)
Çıkış: 0 temiz · 1 ihlal (BLOCKER).
"""
# ENFORCES: FE-13  (ADR 0019 coverage binding)
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

_LIST_NAME = re.compile(r"list|report|liste|rapor", re.IGNORECASE)
_UI_TABLE_NS = re.compile(r"sap\.ui\.table", re.IGNORECASE)
_M_TABLE = re.compile(r"<(\w+:)?Table\b", re.IGNORECASE)  # sap.m.Table (default/m: ns)
_COLUMN = re.compile(r"<(\w+:)?Column\b", re.IGNORECASE)


def is_list_view(filename, text):
    """Net liste/rapor view mı? YALNIZ dosya-adı (List/Report/Liste/Rapor).

    ">=5 kolon = liste" sezgisi KALDIRILDI (2026-06-18 triage, ADR 0019 FP-shakeout):
    detay/düzenleme formundaki item-table'ları (ChangeOrder/Detail vb.) FP yakalıyordu —
    8 yanlış-pozitif. Proje konvansiyonu liste ekranını `List.view.xml` adlandırır →
    dosya-adı güvenilir sinyal. Detektör docstring'i "emin değilsen işaretleme (FN tercih)"
    der → FP-azalt, nadir FN kabul. (_M_TABLE/_COLUMN artık scan_view içinde kolon-sayımı için.)"""
    return bool(_LIST_NAME.search(filename))


_XML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)  # B7 fix (2026-07-09): yorum-strip


def scan_view(filename, text):
    """List/Report-adlı + GERÇEK m.Table'lı + sap.ui.table'sız view → (1, col_count); aksi []."""
    # B7 fix: XML yorumlarını çıkar — yorumdaki `<!-- sap.ui.table -->` gerçek m.Table ihlalini
    # MASKELEMESİN (health-check false-negative bulgusu). is_list_view dosya-adına bakar (etkilenmez).
    text = _XML_COMMENT.sub("", text)
    if _UI_TABLE_NS.search(text):
        return []  # grid zaten kullanılıyor → temiz
    if not is_list_view(filename, text):
        return []  # dosya-adı List/Report değil → kapsam dışı
    if not _M_TABLE.search(text):
        return []  # tablo YOK (akordion/custom belge-listesi) → grid-aday DEĞİL (A-2 FP-fix)
    col_count = len(_COLUMN.findall(text))
    return [(1, col_count)]


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
        import os
        # PERF: rglob node_modules'ı (1184 dizin) dolaşıyordu → os.walk ile yürüyüş anında buda.
        _prune = {"node_modules", "dist", ".tmp", "tmp", ".git"}
        files = []
        for dirpath, dirnames, filenames in os.walk(root / SOURCE_ROOT_NAME):
            dirnames[:] = [d for d in dirnames if d.lower() not in _prune]
            if "ui" not in Path(dirpath).parts:  # yalnız ui/ ağacı
                continue
            files += [Path(dirpath) / fn for fn in filenames if fn.endswith(".view.xml")]

    total = 0
    for f in files:
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for ln, col_count in scan_view(f.name, txt):
            total += 1
            rel = f.relative_to(root) if str(f).startswith(str(root)) else f
            print(f"[İHLAL] {rel}:{ln}  WARNING: liste/rapor view'i sap.m.Table ({col_count} kolon) "
                  f"kullanıyor, sap.ui.table (grid) yok → grid + TablePersonalizer kullan "
                  f"(ADR 0008): sort/filter/sanal-scroll + varyant.")

    if total:
        # HARD (ADR 0019 Gatekeeper TERFİ 2026-06-18): A-2 triage detektörü daralttı
        # (gerçek m.Table şartı → detay-form + akordion FP'leri elendi, 10→0). Artık FP yok →
        # bulgu = BLOCKER (gerçek tablo-tarzı liste grid değil).
        print(f"\n{total} BLOCKER — liste/rapor view'i grid (sap.ui.table) yerine sap.m.Table "
              f"kullanıyor. ALV-tarzı liste için grid + TablePersonalizer standardı (ADR 0008). "
              f"NOT: detay/düzenleme formundaki item-table + akordion belge-listesi MEŞRU — yalnız "
              f"gerçek tablo-tarzı LİSTE ekranı grid olmalı.", file=sys.stderr)
        return 1
    print("[OK] liste view grid (sap.ui.table) ihlali yok.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
