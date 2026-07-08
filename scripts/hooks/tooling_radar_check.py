#!/usr/bin/env python3
"""SessionStart hook — Genel Agent-Dev Tooling Radar bayatlık kontrolü.

governance/tooling-radar.md frontmatter'ındaki `last-run` tarihini okur; `cadence-days`
(varsayılan 21) geçtiyse açılışta 1-satır nudge enjekte eder (aktif işi bölmeden, iş-arası
öner). Bayat değilse SESSİZ (normal oturumlarda token maliyeti yok). Kök sorun: tooling
taramamız SAP-dar kalıyordu; bu radar SAP-dışı verim-araçlarını (playwright-cli gibi)
proaktif yüzeye çıkarır. Bkz. governance/tooling-radar.md.
"""
import datetime
import json
import re
import sys
from pathlib import Path

RADAR = Path(__file__).resolve().parents[2] / "governance" / "tooling-radar.md"
DEFAULT_CADENCE = 21


def main() -> int:
    try:
        json.load(sys.stdin)
    except Exception:
        pass

    last = None
    cadence = DEFAULT_CADENCE
    try:
        txt = RADAR.read_text(encoding="utf-8")
        m = re.search(r"^last-run:\s*(\d{4}-\d{2}-\d{2})", txt, re.M)
        if m:
            last = datetime.date.fromisoformat(m.group(1))
        c = re.search(r"^cadence-days:\s*(\d+)", txt, re.M)
        if c:
            cadence = int(c.group(1))
    except Exception:
        return 0  # radar dosyası yoksa sessiz kal (kurulmamış)

    today = datetime.date.today()
    age = None if last is None else (today - last).days
    due = age is None or age >= cadence
    if not due:
        return 0  # bayat değil → SESSİZ

    age_txt = "tarih yok" if age is None else f"{age} gün"
    nudge = (
        f"[Tooling radar — bayat ({age_txt}, eşik {cadence}g)] Genel agent-dev verimlilik araçları "
        "taraması vakti geldi (SADECE SAP-AI DEĞİL: tarayıcı/UI-doğrulama, token-verim/MCP↔CLI, "
        "arama, orkestrasyon, kod-zekası, Claude Code yenilikleri). AKTİF İŞİ BÖLME — iş-arası uygun "
        "anda kullanıcıya öner; onaylarsa governance/tooling-radar.md'deki subagent prompt'uyla bir "
        "general-purpose subagent başlat → bulguları 'Bulgu Log'a + adopt-adaylarını tooling-plugins.md'ye "
        "yaz, frontmatter last-run'ı bugüne güncelle. (Bu körlük 2026-06-13 playwright-cli dersinden doğdu.)"
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": nudge,
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
