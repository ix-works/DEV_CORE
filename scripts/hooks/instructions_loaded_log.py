#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""InstructionsLoaded hook — hangi talimat dosyası, NE ZAMAN, NEDEN yüklendi?

NEDEN: `CLAUDE.md` / `.claude/rules/*.md` yüklemesi **sessizdir**. Bir kural hiç yüklenmese
de kimse fark etmez — 2026-07-10 denetiminde `AGENTS.md`'nin 356 satırı aylarca ölü kaldı ve
ekran teyidi her oturum "yüklendi" dedi. Ayrıca `globs:` yerine dokümante `paths:` yazılırsa
kural **sessizce** yüklenmez (anthropics/claude-code#17204). Ve `core/` bir junction'dır —
junction ardındaki kuralların yüklenip yüklenmediği KANIT ister (D29).

Bu hook karar vermez, bloklamaz. Yalnız `.tmp/instructions-loaded.log`'a satır yazar:
    <ISO-zaman>  <matcher>  <yol>

Matcher değerleri: session_start · nested_traversal · path_glob_match · include · compact
`path_glob_match` görülüyorsa glob-tetiklemeli kural GERÇEKTEN yüklenmiştir.

Doğrulama: bir `.abap` dosyası okut → log'da `path_glob_match ... sap-source-protokolu.md`
satırı çıkmalı. Çıkmıyorsa kural ÖLÜDÜR (glob yanlış ya da junction takip edilmiyor).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass


def main() -> int:
    try:
        veri = json.load(sys.stdin)
    except Exception:
        return 0  # hiçbir zaman bloklamaz

    kok = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
    log = kok / ".tmp" / "instructions-loaded.log"
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        zaman = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        matcher = veri.get("matcher") or veri.get("source") or "?"
        yollar = veri.get("paths") or veri.get("filePaths") or [veri.get("path", "?")]
        if isinstance(yollar, str):
            yollar = [yollar]
        with log.open("a", encoding="utf-8") as fh:
            for y in yollar:
                fh.write(f"{zaman}\t{matcher}\t{y}\n")
            if not yollar:
                fh.write(f"{zaman}\t{matcher}\t<yol-yok>\t{json.dumps(veri)[:300]}\n")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
