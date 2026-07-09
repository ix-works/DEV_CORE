#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VALIDATOR — hook'ların ENJEKTE ettiği doküman yolları gerçekten açılabiliyor mu?

NEDEN (2026-07-09 denetimi): `skill_injector` ve `intake_triage`, ajana "OKU: <yol>" diye
ZORUNLU okuma talimatı enjekte ediyor. Metodoloji `core/` junction'ı altına taşınınca
enjekte edilen yollar öneksiz kaldı:

    Read("playbook/intake-triage.md")       -> "File does not exist"

Ölçüm: bir oturumda 32 `OKU:` talimatı enjekte edildi, 0 checklist okundu. Kırık yol,
"o dosya yok" gibi okunur — ajan protokolü atlar. Bu validator o sessiz kırılmayı yakalar.

ENFORCES: C-HOOK-01 (enjekte edilen her .md yolu proje kökünden çözülmeli)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Windows konsolu cp1252'dir: Türkçe karakterli çıktı UnicodeEncodeError ile ÇÖKER →
# validator her ortamda exit 1 verip SAHTE FAIL üretir (bu dosyanın ilk koşumunda oldu).
for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

CORE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CORE / "scripts"))
from utils.project_config import project_root  # type: ignore  # noqa: E402

PROJ = project_root()

# Farklı iş-tiplerini tetikleyen örnek prompt'lar (her biri farklı checklist enjekte eder)
ORNEK_PROMPTLAR = [
    "RAP BDEF yarat, CDS view ekle, freestyle UI5 yap",
    "klasik ALV raporu yaz, DDIC struct ekle",
    "domain ve DTEL yarat, tablo ekle",
    "yeni bir rapor gelistir",          # intake_triage tetikleyicisi
]

HOOKLAR = ("skill_injector", "intake_triage")
YOL_DESENI = re.compile(r"[\w/\-.]+\.md")


def _hook_ciktisi(hook: str, prompt: str) -> str:
    shim = PROJ / "scripts" / "hook_shim.py"
    argv = [sys.executable, str(shim), hook] if shim.exists() else \
           [sys.executable, str(CORE / "scripts" / "hooks" / f"{hook}.py")]
    r = subprocess.run(argv, input=json.dumps({"prompt": prompt}), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=60,
                       env=dict(os.environ, CLAUDE_PROJECT_DIR=str(PROJ)))
    if r.returncode != 0 or not r.stdout.strip():
        return ""
    try:
        return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
    except Exception:
        return ""


def main() -> int:
    kirik: list = []
    toplam = 0
    for hook in HOOKLAR:
        for p in ORNEK_PROMPTLAR:
            metin = _hook_ciktisi(hook, p)
            if not metin:
                continue
            for yol in sorted(set(YOL_DESENI.findall(metin))):
                toplam += 1
                if not (PROJ / yol).is_file():
                    kirik.append(f"{hook}: '{yol}' çözülmüyor (prompt: {p[:30]}…)")

    if not toplam:
        print("  [WARN] hiçbir yol enjekte edilmedi — örnek prompt'lar tetiklemiyor olabilir")
        return 0
    if kirik:
        print(f"  [FAIL] enjekte edilen {len(kirik)}/{toplam} yol PROJE KÖKÜNDEN ÇÖZÜLMÜYOR:")
        for k in kirik:
            print(f"         - {k}")
        print("         Ajan bu yolu Read edemez → 'dosya yok' sanır → ZORUNLU protokolü atlar.")
        print("         Çözüm: core/scripts/utils/inject_paths.py::core_onekle() ile önekle.")
        return 1
    print(f"  [OK] enjekte edilen {toplam} doküman yolunun tamamı çözülüyor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
