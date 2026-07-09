#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Konsol çıktısını UTF-8'e sabitler — Windows cp1252 çökmesini önler.

NEDEN (2026-07-09, üç kez arka arkaya yaşandı):
Windows konsolunun/pipe'ının varsayılan kodlaması `cp1252`'dir. Türkçe karakter basan bir
script `UnicodeEncodeError` ile ÇÖKER ve `exit 1` verir. Bir **validator** için bu felakettir:
çökme, gerçek FAIL'den ayırt edilemez — negatif testin hiçbir şey kanıtlamaz, ya da her
ortamda sahte FAIL üretirsin.

Kanıt: `check_hook_injected_paths.py`, `test_pre_tool_guard.py` ve `check_core_index_fresh.py`
aynı hatayla üst üste çöktü. Repo'da 94 script bunu zaten doğru yapıyordu; konvansiyon vardı,
enforcement yoktu. Artık `check_console_utf8.py` zorluyor.

Kullanım (bağımlılıksız alternatif de kabul — validator ikisini de tanır):
    from utils.console import utf8_konsol
    utf8_konsol()
veya doğrudan:
    for _a in (sys.stdout, sys.stderr):
        try: _a.reconfigure(encoding="utf-8", errors="replace")
        except Exception: pass
"""
from __future__ import annotations

import sys


def utf8_konsol() -> None:
    """stdout/stderr'i UTF-8 + errors='replace' yapar. Idempotent, hata fırlatmaz."""
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
