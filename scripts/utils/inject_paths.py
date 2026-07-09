#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hook'ların ENJEKTE ettiği doküman yollarını proje-çözümlenebilir hâle getirir.

SORUN (2026-07-09 denetimi): `skill_injector` ve `intake_triage` metodoloji dosyalarını
adıyla söylüyordu — `OKU: playbook/intake-triage.md`. Ama metodoloji artık `core/`
junction'ı altında. Ajanın gördüğü yol ÇÖZÜLMÜYOR:

    Read("playbook/intake-triage.md")  -> "File does not exist"
    Read("core/playbook/intake-triage.md") -> OK

Sonuç: her geliştirme talebinde ZORUNLU protokolün yolu kırıktı; ajan `core/` önekini
tahmin etmek zorundaydı. Tahmin etmediğinde protokol okunmadan geçildi (canlı ölçüm:
32 `OKU:` talimatı, 0 checklist okuması).

Bu modül TEK KAYNAKTIR — iki hook da buradan çağırır. Kopyalanırsa drift eder
(bkz. `ZSD_PAT` iki dosyada ayrı tanımlıydı, drift gate'iyle çözüldü).
"""
from __future__ import annotations

import re

# core kökündeki üst-düzey metodoloji dizinleri (junction altında yaşarlar)
_CORE_DIZINLERI = ("playbook", "standards", "profiles", "governance/decisions")

# `core/` zaten varsa TEKRAR ekleme (çift-önek `core/core/playbook` üretmesin).
_DESEN = re.compile(
    r"(?<![\w/])(?<!core/)(" + "|".join(d.replace("/", r"/") for d in _CORE_DIZINLERI) + r")/"
)


def core_onekle(metin: str) -> str:
    """Enjekte edilecek metindeki çıplak metodoloji yollarına `core/` öneki ekler.

    >>> core_onekle("OKU: playbook/intake-triage.md")
    'OKU: core/playbook/intake-triage.md'
    >>> core_onekle("OKU: core/playbook/x.md")        # zaten önekli → dokunma
    'OKU: core/playbook/x.md'
    >>> core_onekle("bkz. standards/05-coding-rap.md")
    'bkz. core/standards/05-coding-rap.md'
    """
    return _DESEN.sub(r"core/\1/", metin)


if __name__ == "__main__":  # hızlı kendi-kendini sınama
    ornekler = [
        ("OKU: playbook/intake-triage.md", "OKU: core/playbook/intake-triage.md"),
        ("OKU: core/playbook/x.md", "OKU: core/playbook/x.md"),
        ("standards/05 · playbook/checklists/rap-creation.md",
         "core/standards/05 · core/playbook/checklists/rap-creation.md"),
        ("scripts/playbook/x", "scripts/playbook/x"),   # başka bir ağacın altındaysa dokunma
    ]
    hata = 0
    for girdi, beklenen in ornekler:
        c = core_onekle(girdi)
        if c != beklenen:
            hata += 1
            print(f"FAIL {girdi!r} -> {c!r} (beklenen {beklenen!r})")
    print("inject_paths: OK" if not hata else f"inject_paths: {hata} HATA")
    raise SystemExit(1 if hata else 0)
