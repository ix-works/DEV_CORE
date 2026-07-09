#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VALIDATOR — `governance/CORE-INDEX.md` core dokümanlarıyla güncel mi?

NEDEN: `core/` junction'dır; `Grep`/`Glob` junction'ı takip etmez (ölçüldü, gitignore'dan
bağımsız). Metodoloji kökten aramada görünmez. `CORE-INDEX.md` gerçek bir dosya olarak o
körlüğü kapatır — ama **bayat indeks, ajana yanlış yol veren sessiz bir hatadır**:
"core/playbook/x.md" der, dosya yoktur; ajan "kural yok" diye raporlar.

ENFORCES: C-IDX-01 (CORE-INDEX, core doküman ağacıyla eş olmalı)
Onarım:   python core/scripts/build_core_index.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Windows konsolu cp1252'dir: alt-sürecin Türkçe çıktısını aynen yazmak UnicodeEncodeError
# ile ÇÖKER → exit 1 verir ve gerçek FAIL'den ayırt edilemez (2026-07-09: ilk negatif test
# bu yüzden hiçbir şey kanıtlamadı).
for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

CORE = Path(__file__).resolve().parents[2]
URETICI = CORE / "scripts" / "build_core_index.py"


def main() -> int:
    if not URETICI.is_file():
        print(f"  [FAIL] üretici yok: {URETICI}")
        return 1
    r = subprocess.run([sys.executable, str(URETICI), "--check"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    sys.stdout.write(r.stdout)
    if r.stderr.strip():
        sys.stderr.write(r.stderr)
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
