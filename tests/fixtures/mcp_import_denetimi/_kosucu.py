#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yardımcı koşucu — hedef aracı (ix_doctor / team_setup) GERÇEK `__file__` ile koşar.

Neden: iki araç da `CORE_ROOT = Path(__file__).resolve().parents[1]` türetir. Mutant ya da
taban kopyasını repo içine KARDEŞ dosya olarak yazmak gerçek ağacı kirletir (komşu korpus
kalıntıyı görür); düz temp'e yazmak ise CORE_ROOT'u temp'e kaydırır. Burada kaynak METNİ
değişir, `__file__` DEĞİŞMEZ ⇒ repo ağacına tek bayt yazılmadan mutasyon ölçülür.

Kullanım:
    python _kosucu.py <hedef.py> <hedef-kaynagi|-> <yardimci-kaynagi|-> [arguman ...]
      <hedef-kaynagi>   '-' = hedefin kendisi; aksi hâlde bu dosyanın METNİ koşulur
      <yardimci-kaynagi> '-' = gerçek `utils.mcp_import_denetimi`; aksi hâlde bu metin
                         `sys.modules`'a o adla yerleştirilir (mutasyonlu yardımcı)
    env `_IX_TEST_EK_YOL` (YALNIZ bu koşucu okur; üretim kodu OKUMAZ): verilirse yerleştirilen
    yardımcının `mcp_import_denetimi`'si `ek_yol=[...]` ile sarılır ⇒ sahte "kurulu" `mcp`
    `.mcp.json` PYTHONPATH'inin ARKASINA girer (site-packages benzeri).
"""
from __future__ import annotations

import os
import sys
import types
from pathlib import Path

hedef = Path(sys.argv[1]).resolve()
kaynak, yardimci, argumanlar = sys.argv[2], sys.argv[3], sys.argv[4:]
scripts = hedef.parent

# fixture dizini sys.path'ten çıkar (run.py/_kosucu.py hiçbir modülü gölgelemesin)
sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != Path(__file__).resolve().parent]
sys.path.insert(0, str(scripts))

if yardimci != "-":
    import utils  # type: ignore  # gerçek paket (scripts/utils/__init__.py)
    yol = scripts / "utils" / "mcp_import_denetimi.py"
    mod = types.ModuleType("utils.mcp_import_denetimi")
    mod.__file__ = str(yol)
    exec(compile(Path(yardimci).read_text(encoding="utf-8"), str(yol), "exec"), mod.__dict__)
    _ek = os.environ.pop("_IX_TEST_EK_YOL", "")
    if _ek:
        _asil = mod.mcp_import_denetimi

        def _sarmal(core_root, proje, timeout=60, ek_yol=None):  # noqa: ANN001
            return _asil(core_root, proje, timeout=timeout, ek_yol=ek_yol or _ek.split(os.pathsep))
        mod.mcp_import_denetimi = _sarmal
    sys.modules["utils.mcp_import_denetimi"] = mod
    utils.mcp_import_denetimi = mod  # type: ignore[attr-defined]

metin = hedef.read_text(encoding="utf-8") if kaynak == "-" else \
    Path(kaynak).read_text(encoding="utf-8")
sys.argv = [str(hedef), *argumanlar]
genel = {"__name__": "__main__", "__file__": str(hedef), "__builtins__": __builtins__}
exec(compile(metin, str(hedef), "exec"), genel)
