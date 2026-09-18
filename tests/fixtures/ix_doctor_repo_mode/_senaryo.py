#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tek senaryo: ix_doctor `katman3()`ü SAHTE gh ile koşar, sonucu JSON basar.

Neden alt-süreç + sahte `_run`: gerçek `gh` ağ + kimlik ister; sahte bir `gh.cmd`
Windows'ta `--jq` argümanındaki `|`'yi cmd.exe'ye yorumlatır (kırılgan). Burada yalnız
`gh` çağrıları sahtelenir; `git remote get-url` GERÇEK `_run` ile koşar. Kaynak METNİ
(gerçek/mutant/taban) GERÇEK `__file__` ile exec edilir ⇒ CORE_ROOT doğru, repo'ya yazım yok.

Kullanım: CLAUDE_PROJECT_DIR=<proje> python _senaryo.py <ix_doctor.py> <kaynak|-> <gh:var|yok> <log>
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

hedef = Path(sys.argv[1]).resolve()
kaynak, gh_durum, log_yolu = sys.argv[2], sys.argv[3], Path(sys.argv[4])
sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != Path(__file__).resolve().parent]

metin = hedef.read_text(encoding="utf-8") if kaynak == "-" else Path(kaynak).read_text(encoding="utf-8")
g = {"__name__": "ix_doctor_senaryo", "__file__": str(hedef), "__builtins__": __builtins__}
exec(compile(metin, str(hedef), "exec"), g)

SAHTE = "gh-sahte"
cagrilar: list[list[str]] = []
_gercek_run = g["_run"]


def _sahte_run(args, *a, **k):  # noqa: ANN001
    if args and args[0] == SAHTE:
        cagrilar.append(list(args[1:]))
        yol = args[2] if len(args) > 2 else ""
        if yol.endswith("/rulesets"):
            return 0, "[]"
        if "/actions/runs" in yol:
            return 0, json.dumps({"workflow_runs": []})
        if "/git/trees/" in yol:
            return 0, "false\t0"
        return 1, "bilinmeyen sahte gh cagrisi"
    return _gercek_run(args, *a, **k)


g["_run"] = _sahte_run
g["shutil"] = types.SimpleNamespace(which=lambda ad: (SAHTE if gh_durum == "var" else None)
                                    if ad == "gh" else None)
sonuc = g["katman3"]()
log_yolu.write_text(json.dumps(cagrilar), encoding="utf-8")
print(json.dumps([[t, m] for t, m in sonuc], ensure_ascii=False))
