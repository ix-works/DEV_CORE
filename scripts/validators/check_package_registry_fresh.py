#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VALIDATOR — `governance/package-registry.md` kaynak ağaçla güncel mi? (C-REG-01)

NEDEN (2026-07-10 denetimi): Dosyanın frontmatter'ı `manual-edit: PROHIBITED —
scripts/build_package_index.py ile auto-üretilir` diyor, ama **tazeliğini hiçbir gate
ölçmüyordu**. Üreteci olan ama tazelik-kontrolü olmayan artefakt, sessizce bayatlar:
yeni paket açılır, registry eski kalır, ajan "böyle paket yok" diye rapor eder.
CORE-INDEX'te (C-IDX-01) aynı dersi almıştık; bu onun ikizi.

ENFORCES: C-REG-01
Onarım:   python core/scripts/build_package_index.py
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
URETICI = CORE / "scripts" / "build_package_index.py"


def main() -> int:
    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()
    registry = proj / "governance" / "package-registry.md"
    if not registry.is_file():
        print("  [SKIP] governance/package-registry.md yok (core-modu ya da yeni proje)")
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
