#!/usr/bin/env python3
"""PreCompact — context compaction ÖNCESİ SESSION_NOTES/memory flush hatırlatması.

Uzun oturumlarda compaction sırasında "güncel iş durumu" kaybolabilir. Bu hook,
compaction olmadan hemen önce, aktif paketin SESSION_NOTES'una son durumu yazmayı
ve önemli kalıcı bilgiyi memory'ye düşürmeyi hatırlatır (gap-analysis #9).

Kısa; gerçek yazımı Claude yapar (hook sadece nudge enjekte eder).
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _active_pkg() -> str:
    p = REPO / ".claude" / "active_package"
    try:
        return p.read_text(encoding="utf-8").strip()
    except Exception:
        return "<aktif paket>"


def main() -> int:
    try:
        json.load(sys.stdin)
    except Exception:
        pass
    pkg = _active_pkg()
    msg = (
        f"[PreCompact — flush hatırlatması] Context sıkıştırılmadan önce, kaybolmaması "
        f"gereken durumu KALICI yaz:\n"
        f"  • Aktif paket ({pkg}) SESSION_NOTES.md'ye son durum / yarım iş / sıradaki adım.\n"
        f"  • Non-obvious karar/öğrenim → memory (project/feedback).\n"
        f"  • Yarım SAP işlemi/transport varsa açıkça not et (T1/T10)."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreCompact",
            "additionalContext": msg,
        }
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
