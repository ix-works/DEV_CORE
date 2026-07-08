#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_cbo_inventory.py — CBO (Z obje) envanteri çıkar (gap-analysis #3).

Verilen paket(ler)deki tüm Z objelerini SAP'den (list_package_contents) toplayıp
governance/cbo-inventory.json'a yazar. check_reuse_gate.py bu envanteri okuyarak
repo-local CDS taramasının ÖTESİNDE (tüm DDIC/class/...) duplicate uyarısı verir.

Kullanım:
    python scripts/build_cbo_inventory.py                       # default: ZSD000_CLC + aktif paket
    python scripts/build_cbo_inventory.py ZSD000_CLC ZSD001_CLC

Çıktı: governance/cbo-inventory.json {packages, objects:{NAME_UPPER:{type,description,package}}}
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
OUT = REPO / "governance" / "cbo-inventory.json"


def _default_packages() -> list[str]:
    pkgs = ["ZSD000_CLC"]
    ap = REPO / ".claude" / "active_package"
    try:
        v = ap.read_text(encoding="utf-8").strip()
        if v and v not in pkgs:
            pkgs.append(v)
    except Exception:
        pass
    return pkgs


def main() -> int:
    import contextlib
    pkgs = sys.argv[1:] or _default_packages()
    from sap_client import SAPClient  # type: ignore
    c = SAPClient()
    inv: dict[str, dict] = {}
    for pkg in pkgs:
        print(f"[envanter] {pkg} ...")
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                objs = c.list_package_contents(pkg)
        except Exception as exc:
            print(f"  [uyarı] {pkg} okunamadı: {type(exc).__name__}: {exc}")
            continue
        n = 0
        for o in objs or []:
            name = (o.get("name") or "").strip()
            if not name or not name.upper().startswith(("Z", "Y")):
                continue
            key = name.upper()
            # DEVC (paketin kendisi) gibi tekrarları atla
            if (o.get("type") or "").startswith("DEVC"):
                continue
            inv.setdefault(key, {
                "type": o.get("type", ""),
                "description": o.get("description", ""),
                "package": pkg,
            })
            n += 1
        print(f"  {n} Z obje")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "_note": "CBO envanteri (build_cbo_inventory.py). check_reuse_gate.py okur. "
                 "Tarih/sistem damgasını commit/CI ekler; burada deterministik tutuldu.",
        "packages": pkgs,
        "object_count": len(inv),
        "objects": dict(sorted(inv.items())),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] {OUT.relative_to(REPO)} — {len(inv)} obje, paketler: {', '.join(pkgs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
