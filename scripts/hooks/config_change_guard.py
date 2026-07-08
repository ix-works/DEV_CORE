#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ConfigChange hook — SEANS-İÇİ ayar değişikliği nöbetçisi (D31, §11.6; F2'nin runtime bacağı).

Neden: hooks/settings CANLI reload olur ve proje hook'ları ONAYSIZ çalışır (doküman-teyitli
§11.2) → oturum başındaki manifest kontrolü seans-içi değişimi GÖREMEZ. Bu hook her
ConfigChange olayında tetiklenir: davranış-yüzeyi dosyası manifest-onaysız değiştiyse
BLOKLAR (exit 2); değilse denetim-izine yazar (.tmp/config-changes.log).

Payload şeması savunmacı işlenir (alan adları sürüme göre değişebilir): stdin JSON'ında
geçen dosya-yolu benzeri değerler davranış-yüzeyi desenleriyle eşlenir.
"""
import io
import json
import os
import re
import sys
import time
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJ = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
CORE = PROJ / "core"

_YUZEY = re.compile(
    r"(\.claude[/\\]settings(\.local)?\.json|\.mcp\.json|CLAUDE(\.local)?\.md"
    r"|project\.yaml|hook_shim\.py|\.claude[/\\]rules[/\\])", re.IGNORECASE)


def _duz_metin(obj) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    metin = _duz_metin(data)
    hit = _YUZEY.search(metin)

    # denetim izi (her durumda; fail-safe)
    try:
        log = PROJ / ".tmp" / "config-changes.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} yuzey={'EVET' if hit else 'hayir'} "
                    f"payload={metin[:400]}\n")
    except Exception:
        pass

    if not hit:
        return 0

    # Davranış-yüzeyi değişimi: manifest hâlâ eş mi?
    try:
        sys.path.insert(0, str(CORE / "scripts"))
        import behavior_manifest  # type: ignore
        sapmalar = behavior_manifest.verify_quiet(PROJ)
    except Exception as e:
        sapmalar = [f"manifest kontrolu calismadi: {e}"]

    if sapmalar:
        sys.stderr.write(
            "⛔ SEANS-İÇİ AYAR DEĞİŞİMİ (ConfigChange guard, D31/F2): davranış-yüzeyi "
            f"dosyası değişti ('{hit.group(0)}') ve behavior-manifest ile UYUŞMUYOR:\n"
            + "\n".join("   • " + s for s in sapmalar[:6])
            + "\nBu oturumun çıktısına GÜVENME — lider'e bildir. Bilinçli değişiklikse: "
              "lider-PR + `python core/scripts/behavior_manifest.py generate`. BLOKLANDI.\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
