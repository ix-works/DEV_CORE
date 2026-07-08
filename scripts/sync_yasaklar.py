#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sync_yasaklar — KESİN YASAKLAR kanonik bloğunu projelerin kök CLAUDE.md'sine yeniden damgalar.

Ne zaman: kanonik (core/claude/kesin-yasaklar.canonical.md) değiştiğinde (nadir; ADR 0005
anayasal). Tüm projeleri gezip damgayı günceller; drift-guard damgalanmayanı yakalar.

Kullanım:
    python core/scripts/sync_yasaklar.py                 # bu projeyi (cwd) damgala
    python core/scripts/sync_yasaklar.py --root C:\\IX    # C:\\IX altındaki TÜM projeleri
    python core/scripts/sync_yasaklar.py --check         # yazMA, yalnız sapanları listele
Bir "proje" = altında project.yaml + CLAUDE.md olan dizin (core/DEV_CORE'un kendisi hariç).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent))  # <core>/scripts
from utils import yasaklar_stamp  # noqa: E402

CORE_ROOT = _HERE.parent.parent  # <core>


def _projeler(root: Path) -> list[Path]:
    out = []
    for py in root.rglob("project.yaml"):
        d = py.parent
        if (d / "CLAUDE.md").exists() and "node_modules" not in str(d) and ".git" not in str(d):
            out.append(d)
    return sorted(set(out))


def _damgala(proje: Path, check_only: bool) -> str:
    cmd = proje / "CLAUDE.md"
    metin = cmd.read_text(encoding="utf-8")
    ok, _ = yasaklar_stamp.check(metin, CORE_ROOT)
    if ok:
        return f"[EŞ]   {proje}"
    if check_only:
        return f"[SAPMA] {proje}  → sync gerekli"
    yeni = yasaklar_stamp.upsert(metin, CORE_ROOT)
    cmd.write_text(yeni, encoding="utf-8", newline="\n")
    return f"[DAMGALANDI] {proje}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None, help="Bu kök altındaki TÜM projeler (yoksa: cwd)")
    ap.add_argument("--check", action="store_true", help="Yazma; yalnız sapanları listele")
    a = ap.parse_args()

    if not yasaklar_stamp.canonical_path(CORE_ROOT).exists():
        print(f"[FAIL] kanonik yok: {yasaklar_stamp.canonical_path(CORE_ROOT)}")
        return 1

    if a.root:
        projeler = _projeler(Path(a.root).resolve())
    else:
        cwd = Path.cwd()
        projeler = [cwd] if (cwd / "project.yaml").exists() and (cwd / "CLAUDE.md").exists() else []
    if not projeler:
        print("Damgalanacak proje bulunamadı (project.yaml + CLAUDE.md olan dizin yok).")
        return 0

    sapan = 0
    for p in projeler:
        satir = _damgala(p, a.check)
        print(" " + satir)
        if satir.startswith("[SAPMA]") or satir.startswith("[DAMGALANDI]"):
            sapan += 1
    print(f"\n{len(projeler)} proje · {sapan} {'sapma' if a.check else 'güncellendi'} "
          f"· kanonik={yasaklar_stamp.digest(yasaklar_stamp.canonical_text(CORE_ROOT))}")
    return 1 if (a.check and sapan) else 0


if __name__ == "__main__":
    raise SystemExit(main())
