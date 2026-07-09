"""
check_amdp_comment_apostrophe.py — AMDP SQLScript `--` yorumunda apostrof (') YASAK.

# ENFORCES: BE-28  (alt-madde c; ADR 0019 coverage binding)

Neden (canlı post-mortem 2026-06-29, ZSD001 voyage-decouple satis_navlun AMDP): AMDP
method gövdesindeki (LANGUAGE SQLSCRIPT) `--` yorum satırına Türkçe apostrof girince
(ör. "voyage'a", "SELECT'te", "precedent'i") HANA SQLScript parser apostrofu STRING-LITERAL
açıcı sayar → literal bir sonraki apostrofa kadar UZAR → aktivasyonda
"Literals across more than one line are not allowed" → activation FAIL.

**Bu hata adt_syntax_check (INACTIVE sürümü okur) + abaplint + bug-gate'i GEÇER, yalnız
ilk gerçek ACTIVATION'da çıkar** (bizde bug-gate PASS dedi, activate patladı). Kural
bug-checklist-backend BE-28c'de PROSE olarak vardı ("edit sonrası grep guard ZORUNLU")
ama GATE'siz → bug-expert hatırlamadı → atlandı (ADR 0019: gate'siz kural ≈ kuralsız).
Bu validator o boşluğu deterministik kapatır — yerel source'u tarar, activation'ı beklemez.

DOĞRU DESEN: AMDP `--` yorumlarında apostrof KULLANMA. Türkçe eki yeniden yaz
("voyage'a"→"voyaga", "SELECT'te"→"SELECT icinde"), tırnaklı-değer anımını apostrofsuz yaz.
(Bonus: AMDP gövdesi PUR ASCII-7 olmalı — Türkçe karakter de yasak; bkz. BE-28b.)

Kapsam: <source_root>/**/*.clas.abap, *.ccimp.abap (AMDP gövdesi burada). `^\s*--` ile başlayan
  satır = SQLScript yorumu (ABAP yorumu `*`/`"` kullanır; `--` ABAP'ta yorum değil) → o
  satırda apostrof varsa flag.
  Kaçış: ilgili satıra `#NO_AMDP_APOSTROPHE_CHECK <gerekçe>` (gerçek-gerekli apostrof —
  pratikte yok; kaçış sadece bilinçli istisna için).

Bulgular:
  ERROR (BLOCKER): `^\s*--` SQLScript yorum satırında `'` (apostrof) — aktivasyon kırılır.

Kullanım:
    python scripts/validators/check_amdp_comment_apostrophe.py
    python scripts/validators/check_amdp_comment_apostrophe.py --strict

Exit: 0 — temiz · 1 — en az bir ERROR
"""
import argparse
import re
import sys
from pathlib import Path
import sys as _pc_sys
from pathlib import Path as _pc_Path
_pc_sys.path.insert(0, str(_pc_Path(__file__).resolve().parents[1]))
from utils.project_config import project_root, source_dir  # K12: kaynak-klasor adi config'ten

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ADR 0020: junction'da __file__ DEV_CORE'a çözülür → kanonik project_root()/source_dir()
REPO = project_root()
ERP = source_dir()

_SKIP_SEGMENTS = {"node_modules", "dist", "tmp", ".tmp"}
_SCAN_SUFFIXES = (".clas.abap", ".ccimp.abap")
_ESCAPE = "#NO_AMDP_APOSTROPHE_CHECK"

# SQLScript yorum satırı (`--` ile başlar; baştaki boşluk serbest) + içinde apostrof.
_RX_COMMENT_APOS = re.compile(r"^\s*--.*'")


def _iter_files():
    if not ERP.exists():
        return
    import os
    for dirpath, dirnames, filenames in os.walk(ERP):
        dirnames[:] = [d for d in dirnames if d.lower() not in _SKIP_SEGMENTS]
        for fn in filenames:
            if fn.lower().endswith(_SCAN_SUFFIXES):
                yield Path(dirpath) / fn


def _has_amdp(text: str) -> bool:
    """Yalnız AMDP içeren class'larda tara (BY DATABASE PROCEDURE / LANGUAGE SQLSCRIPT)."""
    return bool(re.search(r"BY\s+DATABASE\s+(PROCEDURE|FUNCTION)|LANGUAGE\s+SQLSCRIPT", text, re.IGNORECASE))


def _scan():
    findings = []  # (file, lineno, text)
    for f in _iter_files():
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if not _has_amdp(text):
            continue
        for i, raw in enumerate(text.splitlines(), 1):
            if _ESCAPE in raw:
                continue
            if _RX_COMMENT_APOS.search(raw):
                findings.append((f, i, raw.strip()[:120]))
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description="AMDP SQLScript `--` yorumunda apostrof yasağı (BE-28c)")
    ap.add_argument("--strict", action="store_true", help="(uyumluluk; ERROR zaten fail)")
    ap.add_argument("--quick", action="store_true", help="(uyumluluk; bu kontrol zaten hızlı)")
    ap.parse_args()

    findings = _scan()
    if not findings:
        print("AMDP yorum-apostrof (BE-28c): temiz (SQLScript `--` yorumlarında apostrof yok).")
        return 0

    for f, ln, text in findings:
        rel = f.relative_to(REPO)
        print(f"[İHLAL] {rel}:{ln}  AMDP `--` yorumunda apostrof  → {text}")

    print()
    print(f"Özet: {len(findings)} ERROR — AMDP SQLScript `--` yorumunda apostrof.")
    print("APOSTROF = HANA SQLScript parser literal-açıcı sanır → aktivasyon "
          "'Literals across more than one line' FAIL (adt_syntax_check/abaplint/bug-gate GÖRMEZ, "
          "yalnız activation yakalar). Apostrofu kaldır (\"voyage'a\"→\"voyaga\", \"SELECT'te\"→"
          "\"SELECT icinde\"). Gerçek-gerekli ise satıra `#NO_AMDP_APOSTROPHE_CHECK <gerekçe>`. Build DURUR.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
