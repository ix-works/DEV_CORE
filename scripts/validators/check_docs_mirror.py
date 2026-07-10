#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VALIDATOR — `<proje>/docs/*.md` aynası `core/docs/` ile eş mi? (C-DOC-01)

NEDEN: Bir belgeyi iki yerde tutmak, tazelik kontrolü olmadan **kesinlikle** drift üretir.
2026-07-10 template provası bunu üç ayrı artefaktta canlı gösterdi (settings şablonu 3 hook
geride, CI şablonunda bir job eksik, `.gitignore` ~35 satır geride). Aynı hatayı mimari
kılavuzunun kopyasında tekrarlamamak için ayna gate'lenir.

Kanonik kaynak: `core/docs/`. Proje kopyası bire bir aynı olmalıdır; düzenleme DEV_CORE'da
PR ile yapılır, sonra ayna senkronlanır.

ENFORCES: C-DOC-01
Onarım:   python core/scripts/sync_docs_mirror.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

CORE = Path(__file__).resolve().parents[2]
URETICI = CORE / "scripts" / "sync_docs_mirror.py"


def main() -> int:
    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()
    if not (proj / "docs").is_dir():
        print("  [SKIP] projede docs/ yok — ayna istenmiyor")
        return 0
    if not URETICI.is_file():
        print(f"  [FAIL] üretici yok: {URETICI}")
        return 1
    r = subprocess.run([sys.executable, str(URETICI), "--check"], cwd=str(proj),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    sys.stdout.write(r.stdout)
    if r.stderr.strip():
        sys.stderr.write(r.stderr)
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
