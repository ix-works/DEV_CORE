#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`core/docs/*.md` → `<proje>/docs/*.md` aynasını senkronlar (C-DOC-01 onarımı).

NEDEN: Mimari kılavuzu gibi belgeler bazı projelerde (ör. referans iskelet) repo içinde de
bulunmak ister. Kopya, tazelik kontrolü olmadan **kesinlikle** bayatlar — bu, aynı gün
`settings.template.json` ve `guard.template.yml` için canlı yaşandı (2026-07-10 provası).

TEK KAYNAK: `core/docs/`. Proje kopyası bire bir aynı olmalıdır; düzenleme DEV_CORE'da PR
ile yapılır. Gate: `scripts/validators/check_docs_mirror.py`.

Kullanım (proje kökünde):
    python core/scripts/sync_docs_mirror.py            # ayna dosyalarını tazele
    python core/scripts/sync_docs_mirror.py --check    # yalnız kontrol (exit 1 = bayat)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

CORE = Path(__file__).resolve().parents[1]
CORE_DOCS = CORE / "docs"


def _oku(p: Path) -> bytes:
    return p.read_bytes()


def main() -> int:
    sadece_kontrol = "--check" in sys.argv
    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()
    proj_docs = proj / "docs"

    if proj.resolve() == CORE.resolve():
        print("  [SKIP] core'un kendisi — ayna yok")
        return 0
    if not proj_docs.is_dir():
        print("  [SKIP] projede docs/ yok — ayna istenmiyor")
        return 0
    if not CORE_DOCS.is_dir():
        print(f"  [FAIL] kaynak yok: {CORE_DOCS}")
        return 1

    bayat: list[str] = []
    yazilan: list[str] = []
    # YALNIZ projede zaten var olan aynalar tazelenir; core'daki her dokümanı projeye
    # itmeyiz (proje hangi belgeyi aynaladığına kendi karar verir).
    for hedef in sorted(proj_docs.glob("*.md")):
        if hedef.name == "README.md":
            continue  # ayna açıklaması proje-lokaldir
        kaynak = CORE_DOCS / hedef.name
        if not kaynak.is_file():
            print(f"  [WARN] '{hedef.name}' core/docs'ta yok — ayna değil, proje-lokal sayıldı")
            continue
        if _oku(kaynak) == _oku(hedef):
            continue
        bayat.append(hedef.name)
        if not sadece_kontrol:
            hedef.write_bytes(_oku(kaynak))
            yazilan.append(hedef.name)

    if sadece_kontrol:
        if bayat:
            print("  [FAIL] docs aynası BAYAT: " + ", ".join(bayat))
            print("         Onarım: python core/scripts/sync_docs_mirror.py")
            return 1
        print("  [OK] docs aynası core ile eş")
        return 0

    if yazilan:
        print("  [OK] tazelendi: " + ", ".join(yazilan))
    else:
        print("  [OK] ayna zaten güncel")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
