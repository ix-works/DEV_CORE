#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""InstructionsLoaded hook — hangi talimat dosyası, NE ZAMAN, NEDEN yüklendi?

NEDEN: `CLAUDE.md` / `.claude/rules/*.md` yüklemesi **sessizdir**. Bir kural hiç yüklenmese
de kimse fark etmez — 2026-07-10 denetiminde `AGENTS.md`'nin 356 satırı aylarca ölü kaldı ve
ekran teyidi her oturum "yüklendi" dedi. Ve `core/` bir junction'dır — junction ardındaki
kuralların yüklenip yüklenmediği KANIT ister (D29).

Bu hook karar vermez, bloklamaz. Yalnız `.tmp/instructions-loaded.log`'a satır yazar:
    <ISO-zaman>  <load_reason>  <memory_type>  <file_path>  [globs]

PAYLOAD ŞEMASI (Claude Code 2.1.206 binary'sinden okundu, tahmin DEĞİL):
    hook_event_name · file_path · memory_type · load_reason · globs? · trigger_file_path?
`load_reason` ∈ {session_start, nested_traversal, path_glob_match, include, compact}
`memory_type` ∈ {User, Project, Local, Managed}

⚠ 2026-07-10 dersi: bu hook önce `matcher`/`paths` anahtarlarını arıyordu — İKİSİ DE YOK.
Log aylarca `?  ?` yazdı ve "ölçüyoruz" sanıldı. Sessiz yüklemeyi yakalayan aletin kendisi
sessizce başarısızdı. Tanımadığın anahtarı ASLA varsayma → `_ham` alanı bu yüzden var.

Doğrulama: bir `.abap` dosyası okut → log'da `path_glob_match ... sap-source-protokolu.md`
satırı çıkmalı. Çıkmıyorsa kural ÖLÜDÜR (`paths:` yanlış ya da junction takip edilmiyor).
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

        sebep = veri.get("load_reason")
        yol = veri.get("file_path")
        tip = veri.get("memory_type")

        if sebep is None or yol is None:
            # Şema beklenenden farklı → SESSİZ KALMA, ham payload'ı dök.
            # (Bu dalın erişilemez olması yüzünden aylarca `? ?` yazıldı.)
            satir = f"{zaman}\tSEMA-DEGISTI\t?\t?\t_ham={json.dumps(veri, ensure_ascii=False)[:500]}\n"
        else:
            globs = veri.get("globs") or []
            tetik = veri.get("trigger_file_path") or ""
            ek = f"\tglobs={','.join(globs)}" if globs else ""
            ek += f"\ttrigger={tetik}" if tetik else ""
            satir = f"{zaman}\t{sebep}\t{tip or '?'}\t{yol}{ek}\n"

        with log.open("a", encoding="utf-8") as fh:
            fh.write(satir)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
