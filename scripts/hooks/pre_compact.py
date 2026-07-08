#!/usr/bin/env python3
"""PreCompact — context compaction ÖNCESİ SESSION_NOTES/memory flush hatırlatması.

Uzun oturumlarda compaction sırasında "güncel iş durumu" kaybolabilir. Bu hook,
compaction olmadan hemen önce, aktif paketin SESSION_NOTES'una son durumu yazmayı
ve önemli kalıcı bilgiyi memory'ye düşürmeyi hatırlatır (gap-analysis #9).

Kısa; gerçek yazımı Claude yapar (hook sadece nudge verir).

NOT (şema): PreCompact hookSpecificOutput.additionalContext KABUL ETMEZ (Claude Code
şema doğrulaması reddeder — 2026-07-08 canlı hatayla kanıtlı). Geçerli kanal:
üst-seviye "systemMessage" (kullanıcıya gösterilir; compact'ı kullanıcı tetiklediği
için doğru muhatap odur — flush eksikse compact öncesi isteyebilir).
"""
import json
import os
import re
import sys
from pathlib import Path

# Proje kökü: env-first (junction'da __file__.resolve() DEV_CORE'a çözülür — KULLANMA)
PROJ = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def _active_pkg() -> str:
    p = PROJ / ".claude" / "active_package"
    try:
        return p.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    try:
        m = re.search(r"^active_package:\s*[\"']?([A-Za-z0-9_/]+)",
                      (PROJ / "project.yaml").read_text(encoding="utf-8"), re.M)
        if m:
            return m.group(1)
    except Exception:
        pass
    return "<aktif paket>"


def main() -> int:
    try:
        json.load(sys.stdin)
    except Exception:
        pass
    pkg = _active_pkg()
    msg = (
        f"[PreCompact — flush hatırlatması] Compaction öncesi kalıcılaştırılmış olmalı: "
        f"aktif paket ({pkg}) SESSION_NOTES.md son-durum · non-obvious öğrenim → memory · "
        f"yarım SAP işlemi/transport notu (T1/T10). Eksikse compact sonrası ilk mesajda yazdır."
    )
    print(json.dumps({"systemMessage": msg}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
