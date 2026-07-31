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

# Windows konsolu/pipe'i cp1252'dir: non-ASCII basmak UnicodeEncodeError ile COKER
# (exit 1 -> gercek FAIL'den ayirt edilemez). C-ENC-01 / check_console_utf8.py
for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

import os

CORE_GOV = Path(__file__).resolve().parents[2] / "governance"
DEFAULT_CADENCE = 21


def _bayat_mi(dosya: Path):
    """(due, age_txt, cadence) — dosya yoksa/parse edilemezse (False, ..) → sessiz."""
    try:
        txt = dosya.read_text(encoding="utf-8")
    except Exception:
        return False, "", 0
    last = None
    cadence = DEFAULT_CADENCE
    m = re.search(r"^last-run:\s*(\d{4}-\d{2}-\d{2})", txt, re.M)
    if m:
        last = datetime.date.fromisoformat(m.group(1))
    c = re.search(r"^cadence-days:\s*(\d+)", txt, re.M)
    if c:
        cadence = int(c.group(1))
    age = None if last is None else (datetime.date.today() - last).days
    due = age is None or age >= cadence
    return due, ("tarih yok" if age is None else f"{age} gün"), cadence


def main() -> int:
    try:
        json.load(sys.stdin)
    except Exception:
        pass

    nudges = []

    due, age_txt, cadence = _bayat_mi(CORE_GOV / "tooling-radar.md")
    if due and (CORE_GOV / "tooling-radar.md").is_file():
        nudges.append(
            f"[Tooling radar — bayat ({age_txt}, eşik {cadence}g)] Genel agent-dev verimlilik araçları "
            "taraması vakti geldi (SADECE SAP-AI DEĞİL: tarayıcı/UI-doğrulama, token-verim/MCP↔CLI, "
            "arama, orkestrasyon, kod-zekası, Claude Code yenilikleri). AKTİF İŞİ BÖLME — iş-arası uygun "
            "anda kullanıcıya öner; onaylarsa governance/tooling-radar.md'deki subagent prompt'uyla bir "
            "general-purpose subagent başlat → bulguları 'Bulgu Log'a + adopt-adaylarını tooling-plugins.md'ye "
            "yaz, frontmatter last-run'ı bugüne güncelle. (Bu körlük 2026-06-13 playwright-cli dersinden doğdu.)")

    # T4.2 (2026-08-01): İÇERİK-SAĞLIK RADARI — proje-lokal dosya (denetim §8 Ayak-2).
    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    saglik = proj / "governance" / "content-health-radar.md"
    due2, age2, cad2 = _bayat_mi(saglik)
    if due2 and saglik.is_file():
        nudges.append(
            f"[İçerik-sağlık radarı — bayat ({age2}, eşik {cad2}g)] Dönemsel içerik-sağlık turu vakti "
            "(sahte-koruma grep'i + overlay-fark + memory doluluk + recurrence sayaçları + bayat-iddia "
            "örneklemi + trend tablosu). AKTİF İŞİ BÖLME — iş-arası öner; tur maddeleri + trend tablosu: "
            "governance/content-health-radar.md. Bitince last-run'ı güncelle. (Denetim 2026-07-31 §8; "
            "classrun '1 ay sonra tekrar' penceresine karşı 28g cadence.)")

    if not nudges:
        return 0  # SESSİZ
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n".join(nudges),
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
