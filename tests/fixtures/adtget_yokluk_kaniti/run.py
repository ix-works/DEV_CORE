#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""adtget_yokluk_kaniti fixture — "BULUNAMADI != YOK" (DDIC dali).

NEDEN VAR (2026-08-01 adversarial bug-avi, W2-MCPT-01):
`adt_get` DDIC tiplerinde (dtel/doma/tabl/structure/tabletype) `exists: xml is not None`
yaziyordu. Alt katman (`sap_client.get_ddic_object`) ise HER istisnayi yutup `None`
donduruyor -> ust kattaki `except` dali bu tipler icin HIC atesLENMIYOR. Olculdu
(stub'li kontrol grubuyla):
    obje VAR         -> exists:true            (dogru)
    gercek 404       -> exists:false           (dogru)
    HTTP 500         -> exists:false, ok:true  (YANLIS — 404'ten ayirt edilemez)
    HTTP 403 logon   -> exists:false, ok:true  (YANLIS)
    ReadTimeout      -> exists:false, ok:true  (YANLIS)
    baglanti kopuk   -> exists:false, ok:true  (YANLIS)
Sonuc: ajan "yok" sanip objeyi YENIDEN YARATIR (ADR 0005-A siniri) ya da mevcut objeyi
ezer. Ayni sinif `class` yolunda 2026-07-31'de kapatilmisti; DDIC dali geride kalmisti.

POLITIKA: yokluk iddiasi KANIT ister. `exists:false` yalniz (a) temiz-bos yanit ya da
(b) log'da KESIN bulunamadi imzasi (404 / not found / does not exist) varsa doner.
Ag hatasi -> `unreachable`; digeri -> `belirsiz`. Ikisinde de `ok:false`.

⚠ KONTROL GRUBU BU TESTIN OMURGASI: "404 hala exists:false" satiri kaldirilirsa test
asiri-siki hale gelir ve gercek yokluk tespitini de bozar; o satir korunmalidir.
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
if not (REPO / "mcp_servers").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")
for p in (REPO, REPO / "scripts", REPO / "scripts" / "utils"):
    sys.path.insert(0, str(p))
os.environ.setdefault("CLAUDE_PROJECT_DIR", str(REPO))

# ── MCP SDK KOPRUSU (test-harness'i, uretim kodu DEGIL) ──────────────────────────
# `atom.py` -> `_app.py` -> `from mcp.server.fastmcp import FastMCP` zinciri var. Bu
# fixture'in OLCTUGU sey `adt_get`'in DDIC dalindaki YOKLUK-SINIFLANDIRMASI; FastMCP'nin
# kendisi test kapsaminda DEGIL. CI'da SDK yok (once `pip install mcp` denendi, gelen
# paket `mcp.server.fastmcp` saglamadi) -> alakasiz bir bagimlilik testi kosulamaz
# kiliyordu. Cozum: yalnizca EKSIKSE, sadece bu import'u karsilayan asgari bir sahte
# modul kurulur. Gercek SDK varsa DOKUNULMAZ (yerelde gercek zincir kosar).
# ⚠ Sinir: bu koprü FastMCP davranisini test etmez ve etmemeli; kirilirsa MCP sunucusunun
# kendi smoke testi (`team_setup` "MCP server import smoke") yakalar.
try:  # pragma: no cover - ortam kosullu
    import mcp.server.fastmcp  # type: ignore  # noqa: F401
except Exception:
    import types as _t
    _mcp = _t.ModuleType("mcp")
    _srv = _t.ModuleType("mcp.server")
    _fast = _t.ModuleType("mcp.server.fastmcp")

    class _FastMCP:                                          # asgari yuzey
        def __init__(self, *a, **k):
            pass

        def tool(self, *a, **k):
            def _dek(fn):
                return fn
            return _dek

    _fast.FastMCP = _FastMCP                                 # type: ignore[attr-defined]
    _srv.fastmcp = _fast                                     # type: ignore[attr-defined]
    _mcp.server = _srv                                       # type: ignore[attr-defined]
    sys.modules.setdefault("mcp", _mcp)
    sys.modules.setdefault("mcp.server", _srv)
    sys.modules.setdefault("mcp.server.fastmcp", _fast)

try:
    from mcp_servers.sap_adt.tools import atom
    from sap_adt_lib import SAPADTError, SAPObjectNotFoundError
    from sap_client import SAPClient
except Exception as exc:                                    # pragma: no cover
    raise SystemExit(f"[fixture-hatasi] modul yuklenemedi (sessiz gecme YOK): {exc}")


class _SahteAdt:
    def __init__(self, hata):
        self._hata = hata

    def get_ddic_object(self, object_type, name):
        if self._hata is None:
            return "<xml>ok</xml>"
        raise self._hata


class _SahteClient:
    """GERCEK `SAPClient.get_ddic_object` govdesini kullanir (istisna-yutma dahil)."""

    def __init__(self, hata):
        self.adt_client = _SahteAdt(hata)

    def get_ddic_object(self, object_type, name):
        return SAPClient.get_ddic_object(self, object_type, name)


def _hata(sinif, mesaj, kod=None):
    e = sinif(mesaj)
    if kod is not None:
        setattr(e, "status_code", kod)
    return e


def main() -> int:
    # (ad, hata, beklenen_ok, beklenen_exists)  exists=None -> "iddia edilmemeli"
    vakalar = [
        ("KONTROL obje VAR -> exists:true", None, True, True),
        ("KONTROL gercek 404 -> exists:false",
         _hata(SAPObjectNotFoundError, "Object ZTEST not found", 404), True, False),
        ("HTTP 500 -> yokluk BEYAN EDILMEZ",
         _hata(SAPADTError, "Internal Server Error", 500), False, None),
        ("HTTP 403 logon -> yokluk BEYAN EDILMEZ",
         _hata(SAPADTError, "403 Forbidden - logon failed", 403), False, None),
        ("ReadTimeout -> yokluk BEYAN EDILMEZ",
         _hata(TimeoutError, "Read timed out"), False, None),
        ("baglanti kopuk -> unreachable",
         _hata(ConnectionError, "Max retries exceeded / getaddrinfo failed"), False, None),
    ]

    sonuc = []
    for ad, hata, b_ok, b_exists in vakalar:
        atom._get_client = lambda h=hata: _SahteClient(h)
        r = atom.adt_get(name="ZTEST_DTEL", object_type="dtel")
        ok = (r.get("ok") is b_ok)
        if b_exists is None:
            ok = ok and (r.get("exists") is not False)      # "yok" DEMEMELI
        else:
            ok = ok and (r.get("exists") is b_exists)
        sonuc.append((ad, ok,
                      f"ok={r.get('ok')} exists={r.get('exists')} error={r.get('error') or '-'}"))

    gecen = sum(1 for _, ok, _ in sonuc if ok)
    for ad, ok, detay in sonuc:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad} -> {detay}")
    print(f"\n{gecen}/{len(sonuc)} OK")
    return 0 if gecen == len(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
