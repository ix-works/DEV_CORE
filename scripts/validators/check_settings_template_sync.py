#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VALIDATOR — `claude/settings.template.json` hook envanteriyle senkron mu? (C-TPL-01)

NEDEN (2026-07-10 template provası):

`init_project.py` yeni projeyi `claude/settings.template.json`'dan üretir. Ama hook YAZMAK
ile hook'u ŞABLONA KABLOLAMAK ayrı işlerdir ve ikincisi unutuluyor:

* `sap_worktype_hint` ve `itg_backstop` 2026-07-09'da yazıldı, TD'ye ve `template_project`'e
  ELLE eklendi — **şablona hiç eklenmedi.** Yani `init_project` o gün ve sonrasında, mevcut
  template_project'ten DAHA GERİDE bir proje üretiyordu.
* `instructions_loaded_log` 2026-07-10'da aynı yola giriyordu.

Yeni hook `core/scripts/hooks/` altına düşer düşmez bu gate kırılır → şablona kablolanır.
"Playbook'a not düşmek" yetmez (T11); kablolanmamış hook = olmayan hook.

Ayrıca ŞEKİL kontrolü: `hooks` nesnesinin doğrudan içine yazılan bir anahtar Claude Code
tarafından **olay adı** sanılır. 2026-07-10'da `_comment_InstructionsLoaded` böyle konuldu.
Yorumlar üst seviyede ya da bir hook-bloğunun `_comment` alanında durur.

ENFORCES: C-TPL-01
Onarım: `core/claude/settings.template.json`'a hook'u kabla (ya da OPT_OUT'a gerekçeli ekle).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

CORE = Path(__file__).resolve().parents[2]
SABLON = CORE / "claude" / "settings.template.json"
HOOK_DIZINI = CORE / "scripts" / "hooks"

# Bilerek şablona kablolanmayan hook'lar — her satır GEREKÇELİ olmalı.
OPT_OUT: set[str] = set()  # (şu an yok; eklenirse gerekçesi yorum olarak yazılır)

# Claude Code'un tanıdığı olay adları (şablonda kullanılanlar). Bilinmeyen anahtar =
# muhtemelen yanlış yere konmuş yorum.
GECERLI_OLAYLAR = {
    "SessionStart", "SessionEnd", "UserPromptSubmit", "PreToolUse", "PostToolUse",
    "PreCompact", "PostCompact", "ConfigChange", "InstructionsLoaded", "Stop",
    "SubagentStart", "SubagentStop", "Notification",
}


def _kablolu_hooklar(d: dict, hatalar: list[str]) -> set[str]:
    kablolu: set[str] = set()
    hooks = d.get("hooks", {})
    for olay, bloklar in hooks.items():
        if not isinstance(bloklar, list):
            hatalar.append(
                f"[FAIL] `hooks.{olay}` bir liste değil (<{type(bloklar).__name__}>). "
                f"Claude Code bunu OLAY adı sanar. Yorumlar ÜST SEVİYEDE ya da blok içindeki "
                f"`_comment` alanında durur.")
            continue
        if olay not in GECERLI_OLAYLAR:
            hatalar.append(f"[FAIL] bilinmeyen olay adı: `hooks.{olay}`")
        for blok in bloklar:
            for h in blok.get("hooks", []):
                args = h.get("args") or []
                if args:
                    kablolu.add(str(args[-1]))
    return kablolu


def main() -> int:
    hatalar: list[str] = []
    if not SABLON.is_file():
        print(f"  [FAIL] şablon yok: {SABLON}")
        return 1
    try:
        d = json.loads(SABLON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"  [FAIL] settings.template.json geçersiz JSON: {e}")
        return 1

    kablolu = _kablolu_hooklar(d, hatalar)

    mevcut = {p.stem for p in HOOK_DIZINI.glob("*.py") if not p.name.startswith("_")}
    kablosuz = sorted(mevcut - kablolu - OPT_OUT)
    hayalet = sorted(kablolu - mevcut)

    for h in kablosuz:
        hatalar.append(
            f"[FAIL] `scripts/hooks/{h}.py` var ama settings.template.json'da KABLOLU DEĞİL "
            f"— yeni proje bu korumadan yoksun açılır (kod ≠ kablolama).")
    for h in hayalet:
        hatalar.append(
            f"[FAIL] şablon `{h}` hook'unu kabluyor ama `scripts/hooks/{h}.py` YOK "
            f"— hook_shim çözümleyemez, oturum-başı hata.")

    for e in hatalar:
        print("  " + e)
    if hatalar:
        print(f"\n  Toplam {len(hatalar)} ihlal (C-TPL-01). "
              f"Onarım: şablona kabla ya da OPT_OUT'a gerekçeli ekle.")
        return 1
    print(f"  [OK] settings.template.json ↔ {len(mevcut)} hook script senkron")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
