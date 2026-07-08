#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_kesin_yasaklar — KESİN YASAKLAR fiziksel-damga drift guard'ı (BLOCKER).

Kullanıcı direktifi (2026-07-08): yasaklar her projenin kök CLAUDE.md'sine FİZİKSEL
damgalı olmalı (junction/@import'a bağımlı DEĞİL). Bu validator kök CLAUDE.md'deki
damganın kanonikle (core/claude/kesin-yasaklar.canonical.md) birebir eşliğini doğrular.

- Damga YOK → BLOCKER (yasaklar junction'a bağlı kalmış).
- Damga SAPMIŞ (bayat/elle-değiştirilmiş) → BLOCKER (sync_yasaklar.py yeniden-damgalar).
- CORE-modu (project.yaml yok = DEV_CORE'un kendisi): SKIP — core'un kök CLAUDE'u yok/farklı.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent))  # <core>/scripts
from utils import yasaklar_stamp  # noqa: E402


def _proje_koku() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def _core_koku(proje: Path) -> Path:
    # Proje modunda core = <proje>/core (junction). Guard core-repo içinden de koşabilir.
    c = proje / "core"
    return c if (c / "claude").is_dir() else _HERE.parent.parent.parent


def main() -> int:
    proje = _proje_koku()
    # CORE-modu: project.yaml yoksa bu DEV_CORE'un kendisidir → SKIP
    if not (proje / "project.yaml").exists():
        print("[SKIP] check_kesin_yasaklar (core-modu; proje CLAUDE.md yok)")
        return 0
    claude_md = proje / "CLAUDE.md"
    if not claude_md.exists():
        print(f"[FAIL] check_kesin_yasaklar: kök CLAUDE.md YOK ({claude_md})")
        return 1
    core = _core_koku(proje)
    if not yasaklar_stamp.canonical_path(core).exists():
        print(f"[SKIP] check_kesin_yasaklar: kanonik bulunamadı ({core}) — junction kopuk?")
        return 0
    ok, mesaj = yasaklar_stamp.check(claude_md.read_text(encoding="utf-8"), core)
    if ok:
        print(f"[OK] {mesaj}")
        return 0
    print(f"[FAIL] check_kesin_yasaklar: {mesaj}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
