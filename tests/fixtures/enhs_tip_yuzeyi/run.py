#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""enhs_tip_yuzeyi fixture — Q402 / DEV_CORE #415: ENHS (BAdI enhancement spot) genel tip tablosunda.

NEDEN VAR (2026-11-11)
  `object_types.OBJECT_TYPES`'ta ENHS yoktu ⇒ `adt_delete` / `adt_lock_check` / `adt_atc_check`
  "Unsupported object type" ile reddediyordu. Duz bir girdi eklemek ~12 cagirani birden ACARDI;
  en tehlikelisi `adt_activate` tek-obje yolu: worklist sondasi tip `ENHS/XSB` ile sorar, worklist
  spot'u `ENHS/XS` listeler (#413) ⇒ inaktif spot "dogrulandi" (sahte-yesil). Bu yuzden girdi
  ISLEM-IZINLIDIR: `generic_islemler = (silme, kilit, metadata)`; `islem` vermeyen her cagiran
  ValueError alir. Canli salt-okur olcum (SAP_BASIS 758, 2026-11-11):
    · ATC: var olan Z spot · standart spot · VAR OLMAYAN spot · VAR OLMAYAN sinif ⇒ dordu de
      `FINDING_STATS 0,0,0` + bos objects; kontrol grubu bulgulu Z sinif `0,0,1` + 1 obje
      ⇒ ENHS'te "0 bulgu" yokluktan ayirt edilemez ⇒ ATC KAPSAM DISI (istek gonderilmez).
    · metadata GET yalniz `Accept: */*` ile 200 (classes v2/v4 · core.v1 · application/xml 406);
      var olmayan spot `*/*` ile 404.
    · `GET /sap/bc/adt/locks?objectRef=` sinifta DA 404 ⇒ `adt_lock_check` = `kilit_belirsiz`.
  Sahte sunucu bu olculen davranisi taklit eder.

VEKTORLER (SAP YOK: gercek SAPADTClient + sahte HTTP adaptoru; istek listesi kanit)
  U1 URL == sap_adt_lib.enhs_spot_url (Z · /ABCD/ namespace · karisik harf) · U2 es anlamlilar
  U3 islem None/atc/kaynak -> ValueError (fail-closed varsayilan) · U4 get_source_url acik red
  U5 FP: diger HER tip islem'den etkilenmez · U6 get_adt_type_from_url ENHS/XSB (eskiden UNKNOWN)
  U7 supports_generic_url islem'e duyarli · U8 bilinmeyen islem adi -> ValueError
  D1 SAPClient.delete_object: kilit nesne URL'inde -> DELETE (lockHandle+corrNr) -> UNLOCK
  D2 MCP adt_delete ok + delete_verified (silme sonrasi GET 404) · D3 standart spot: SIFIR istek
  K1 adt_lock_check: var olan spot -> exists True, locked None, kilit_belirsiz (GET /locks 404)
  K2 adt_lock_check: var olmayan spot -> exists False
  A1 adt_atc_check ENHS -> atc_kapsam_disi, SIFIR istek · A2 SAPClient.run_atc_check ENHS -> None,
     SIFIR ATC istegi · A3 run_atc_check.atc_bulgulari ENHS -> ValueError · A4 KONTROL: sinifta
     ATC istegi GIDER (A1-A3 bos gecmesin)
  V1 SAPClient.activate_object ENHS -> ValueError, /activation istegi YOK · V2 MCP adt_activate
     ENHS -> ok false, /activation istegi YOK (sahte-yesil yolu kapali) · V3 push_object ENHS ->
     ValueError, SIFIR istek · V4 syntax_check / object_exists (where-used) ENHS -> ValueError

KULLANIM
  python tests/fixtures/enhs_tip_yuzeyi/run.py                   # taban (exit 0)
  python tests/fixtures/enhs_tip_yuzeyi/run.py --mutasyon-<ad>   # tek mutasyon
  Mutasyon cikisi (run_battery karar tablosu): ilan edilen kume TAM dustu -> 1 · sapma -> 2 ·
  capa != 1 kez / mutant derlenmedi / alt surec sayi vermedi -> 3.
"""
from __future__ import annotations

import importlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

BURASI = Path(__file__).resolve().parent
REPO = BURASI.parents[2]
if not (REPO / "scripts" / "sap_adt_lib.py").is_file():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")

_OT = "scripts/object_types.py"
_SC = "scripts/sap_client.py"
_QY = "mcp_servers/sap_adt/tools/query.py"
_AT = "scripts/run_atc_check.py"

# kip -> (dosya, eski, yeni, dusmesi ILAN edilen kume)
MUTASYONLAR = {
    "--mutasyon-izin-kumesi-yok": (
        _OT, "        'generic_islemler': ('silme', 'kilit', 'metadata'),\n", "",
        {"U3", "U4", "U7", "A1", "A2", "A3", "V1", "V2", "V3", "V4"}),
    "--mutasyon-atc-izinli": (
        _OT, "        'generic_islemler': ('silme', 'kilit', 'metadata'),\n",
        "        'generic_islemler': ('silme', 'kilit', 'metadata', 'atc'),\n",
        {"U3", "U7", "A1", "A2", "A3"}),
    "--mutasyon-ret-yok-sayilir": (
        _OT, "    ret = islem_reddi(object_type, islem)\n    if ret:\n        raise ValueError(ret)\n",
        "    ret = islem_reddi(object_type, islem)\n",
        {"U3", "U4", "A2", "A3", "V1", "V2", "V3", "V4"}),
    "--mutasyon-kaynak-islemsiz": (
        _OT, "    base_url = get_object_url(object_name, object_type, islem='kaynak')\n",
        "    base_url = get_object_url(object_name, object_type)\n", {"U4", "V3"}),
    "--mutasyon-url-yolu": (
        _OT, "        'url_path': 'enhancements/enhsxsb',\n",
        "        'url_path': 'enhancements/enhsxs',\n", {"U1", "U2", "U6", "D1", "D2", "K1"}),
    "--mutasyon-silme-islemsiz": (
        _SC, "        object_url = get_object_url(object_name, object_type, islem='silme')  # Q402: ENHS izinli\n",
        "        object_url = get_object_url(object_name, object_type)\n", {"D1", "D2"}),
    "--mutasyon-metadata-islemsiz": (
        _SC, "        object_url = get_object_url(object_name, object_type, islem='metadata')  # Q402: ENHS izinli\n",
        "        object_url = get_object_url(object_name, object_type)\n", {"D2", "K1", "K2"}),
    "--mutasyon-kilit-islemsiz": (
        _QY, '                bilgi = adt.is_object_locked(get_object_url(name, object_type, islem="kilit"))\n',
        '                bilgi = adt.is_object_locked(get_object_url(name, object_type))\n', {"K1"}),
    "--mutasyon-atc-on-red-yok": (
        _QY, "    if _ret:\n        return {\"ok\": False, \"error\": \"atc_kapsam_disi\"",
        "    if False:\n        return {\"ok\": False, \"error\": \"atc_kapsam_disi\"", {"A1"}),
    "--mutasyon-cli-atc-islemsiz": (
        _AT, "    url = get_object_url(object_name, object_type, islem='atc')  # Q402: ENHS -> ValueError (kapsam disi)\n",
        "    url = get_object_url(object_name, object_type, islem='silme')\n", {"A3"}),
}
KIPLER = list(MUTASYONLAR)

SPOT = "ZSD001_ES_ORNEK"
SPOT_NS = "/ABCD/ES_ORNEK"
KOL = "/sap/bc/adt/enhancements/enhsxsb"
TR = "<TR_ISTEK>"
LOCK_GOVDE = ('<?xml version="1.0" encoding="utf-8"?><asx:abap version="1.0" xmlns:asx="http://www.sap.com/'
              'abapxml"><asx:values><DATA><LOCK_HANDLE>SAHTE-KILIT-0001</LOCK_HANDLE><CORRNR/><CORRUSER/>'
              '<CORRTEXT/><IS_LOCAL>X</IS_LOCAL><IS_LINK_UP/><MODIFICATION_SUPPORT/><SCOPE_MESSAGES/>'
              '</DATA></asx:values></asx:abap>')
SPOT_GOVDE = ('<?xml version="1.0" encoding="utf-8"?><enhs:objectData xmlns:enhs="http://www.sap.com/adt/'
              'enhancements/enhs" xmlns:adtcore="http://www.sap.com/adt/core" adtcore:name="%s" '
              'adtcore:type="ENHS/XSB" adtcore:version="active"/>')
WL_BOS = ('<?xml version="1.0" encoding="utf-8"?><atcworklist:worklist atcworklist:id="WL1" '
          'xmlns:atcworklist="http://www.sap.com/adt/atc/worklist"><atcworklist:objects/>'
          '<atcworklist:infos/></atcworklist:worklist>')
RUN_GOVDE = ('<?xml version="1.0" encoding="utf-8"?><atcworklist:worklistRun xmlns:atcworklist='
             '"http://www.sap.com/adt/atc/worklist"><atcworklist:worklistId>WL1</atcworklist:worklistId>'
             '</atcworklist:worklistRun>')

S: list = []


def ekle(ad, kosul, detay=""):
    S.append((ad, bool(kosul), str(detay)[:300]))


def _sessiz(fn, *a, **k):
    eski = (sys.stdout, sys.stderr)
    tampon = io.StringIO()
    sys.stdout = sys.stderr = tampon
    try:
        try:
            return fn(*a, **k), None, tampon.getvalue()
        except Exception as exc:                      # noqa: BLE001 — istisna OLCULUR
            return None, exc, tampon.getvalue()
    finally:
        sys.stdout, sys.stderr = eski


class Sunucu:
    """Olculen davranis: spot metadata yalniz `Accept: */*` ile 200; GET/POST /locks 404;
    kilit nesne URL'inde `_action=LOCK`; DELETE lockHandle ile 200 ve spot silinir."""

    def __init__(self, spotlar=(SPOT,)):
        self.spotlar = {s.lower() for s in spotlar}
        self.istekler: list = []

    def yanit(self, request):
        import requests
        from requests.structures import CaseInsensitiveDict
        u = urlsplit(request.url)
        yol, q, m = u.path, {k: v[0] for k, v in parse_qs(u.query).items()}, request.method.upper()
        self.istekler.append((m, yol, q))
        acc = request.headers.get("Accept") or ""
        durum, govde, bas = 404, "<sahte>bulunamadi</sahte>", {}
        if (request.headers.get("X-CSRF-Token") or "").lower() == "fetch":
            durum, govde, bas = 200, "<sahte/>", {"X-CSRF-Token": "SAHTE-CSRF"}
        elif yol in ("/sap/bc/adt/locks", "/sap/bc/adt/core/objectlock"):
            durum = 404                                   # OLCULDU: GET ve POST, sinifta da
        elif yol.startswith(KOL + "/"):
            ad = unquote(yol[len(KOL) + 1:]).lower()
            var = ad in self.spotlar
            if q.get("_action") == "LOCK":
                durum, govde = (200, LOCK_GOVDE) if var else (404, "<sahte/>")
            elif q.get("_action") == "UNLOCK":
                durum, govde = 200, ""
            elif m == "DELETE":
                if var and q.get("lockHandle"):
                    self.spotlar.discard(ad)
                    durum, govde = 200, ""
                else:
                    durum = 423 if var else 404
            elif m == "GET":
                if acc.strip() != "*/*":
                    durum, govde = 406, "<sahte>406</sahte>"   # OLCULDU: v2/v4/core.v1/xml
                elif var:
                    durum, govde = 200, SPOT_GOVDE % ad.upper()
        elif yol == "/sap/bc/adt/atc/worklists" and m == "POST":
            durum, govde = 200, "WL1"
        elif yol == "/sap/bc/adt/atc/runs" and m == "POST":
            durum, govde = 200, RUN_GOVDE
        elif yol.startswith("/sap/bc/adt/atc/worklists/") and m == "GET":
            durum, govde = 200, WL_BOS
        elif yol.startswith("/sap/bc/adt/activation"):
            durum, govde = 200, "<sahte/>"
        r = requests.Response()
        r.status_code, r.reason, r.url, r.request, r.encoding = durum, "SAHTE", request.url, request, "utf-8"
        r._content = (govde or "").encode("utf-8")
        r.headers = CaseInsensitiveDict(bas)
        return r

    def say(self, ek):
        return sum(1 for m, y, q in self.istekler if ek(m, y, q))

    def sap_istekleri(self):
        return [(m, y, q) for m, y, q in self.istekler if not (m == "GET" and y == "/sap/bc/adt/discovery")]


def _kum():
    kum = tempfile.mkdtemp(prefix="enhs_tip_")
    Path(kum, ".conn_adt").write_bytes(
        b"ADT_SAP_URL=https://sahte.invalid\nADT_SAP_CLIENT=000\nADT_SAP_TIER=DEV\n")
    Path(kum, "project.yaml").write_text(
        "sap_profile: s4_private\nrelease: '2025'\nsource_root: SOURCE_CODES\n"
        "customer_namespaces: [\"/ABCD/\"]\n", encoding="utf-8")
    return kum


def main() -> int:
    kum = _kum()
    os.environ["CLAUDE_PROJECT_DIR"] = kum
    for _v in ("CLAUDE_CWD", "INIT_CWD", "COPILOT_CWD", "ADT_SAP_DEBUG", "SAP_ADT_DEBUG"):
        os.environ.pop(_v, None)
    os.environ["ADT_SAP_URL"] = "https://sahte.invalid"
    os.chdir(kum)
    for p in (REPO, REPO / "scripts", REPO / "scripts" / "utils"):
        sys.path.insert(0, str(p))
    try:  # MCP SDK koprusu (yalniz eksikse)
        import mcp.server.fastmcp  # type: ignore  # noqa: F401
    except Exception:
        import types as _t
        _mcp, _srv, _fast = (_t.ModuleType("mcp"), _t.ModuleType("mcp.server"),
                             _t.ModuleType("mcp.server.fastmcp"))

        class _FastMCP:
            def __init__(self, *a, **k):
                pass

            def tool(self, *a, **k):
                return lambda fn: fn
        _fast.FastMCP = _FastMCP                         # type: ignore[attr-defined]
        _srv.fastmcp = _fast                             # type: ignore[attr-defined]
        _mcp.server = _srv                               # type: ignore[attr-defined]
        sys.modules.setdefault("mcp", _mcp)
        sys.modules.setdefault("mcp.server", _srv)
        sys.modules.setdefault("mcp.server.fastmcp", _fast)

    import object_types as OT
    import sap_adt_lib as L
    import sap_client as SC
    # ⚠ run_atc_check import aninda (win32) sys.stdout/stderr'i AYNI buffer uzerine yeni
    # TextIOWrapper ile sarar; eski sarmalayici sahipsiz kalinca GC buffer'i KAPATIR. Asil
    # akislari geri koy, yenilerini buffer'i kapatmadan AYIR (sorgu_araclari_durustlugu deseni).
    _o, _e = sys.stdout, sys.stderr
    _o.flush()
    _e.flush()
    import run_atc_check as RA
    for _yeni, _asil in ((sys.stdout, _o), (sys.stderr, _e)):
        if _yeni is not _asil:
            _yeni.flush()
            _yeni.detach()
    sys.stdout, sys.stderr = _o, _e
    from mcp_servers.sap_adt.tools import atom as AT
    from mcp_servers.sap_adt.tools import query as Q
    from requests.adapters import BaseAdapter

    def istemci(sunucu):
        class _Ad(BaseAdapter):
            def send(self, request, **kw):
                return sunucu.yanit(request)

            def close(self):
                pass
        a = L.SAPADTClient(url="https://sahte.invalid", user="SAP_USER_A", password="x",
                           client="000", language="TR")
        for on in ("https://", "http://"):
            a.session.mount(on, _Ad())
        c = SC.SAPClient.__new__(SC.SAPClient)
        c.debug_enabled = False
        c.debug_log_path = None
        c.adt_client = a
        c.local_base = Path(kum) / "yerel" / "src"
        AT._get_client = lambda _c=c: _c                 # type: ignore[assignment]
        return c

    def red(fn, *a, **k):
        _, exc, _ = _sessiz(fn, *a, **k)
        return exc if isinstance(exc, ValueError) else None

    # ── U: tablo ─────────────────────────────────────────────────────────────
    u1 = [(ad, _sessiz(OT.get_object_url, ad, "enhs", islem="silme")[0], L.enhs_spot_url(ad))
          for ad in (SPOT, SPOT_NS, "zsd001_Es_Karisik")]
    ekle("U1 URL == sap_adt_lib.enhs_spot_url (Z · /ABCD/ · karisik harf)",
         all(a == b and a for _, a, b in u1), u1)
    u2 = {t: (_sessiz(OT.get_object_url, SPOT, t, islem="kilit")[0], _sessiz(OT.get_adt_type, t)[0])
          for t in ("enhs", "ENHS", "enhsxsb", "enhs/xsb", "enhancementspot")}
    ekle("U2 es anlamlilar ayni URL + ENHS/XSB",
         len(set(u2.values())) == 1 and list(u2.values())[0] == (KOL + "/zsd001_es_ornek", "ENHS/XSB"), u2)
    u3 = {i: red(OT.get_object_url, SPOT, "enhs", islem=i) for i in (None, "atc", "kaynak")}
    ekle("U3 islem None/atc/kaynak -> ValueError (fail-closed varsayilan)",
         all(u3.values()) and "KAPSAM DISI" in str(u3["atc"])
         and "populate_badi_spot" in str(u3[None]), {k: str(v)[:60] for k, v in u3.items()})
    u4 = red(OT.get_source_url, SPOT, "enhs")
    ekle("U4 get_source_url ENHS -> acik red (kaynak ucu YOK + kanonik arac)",
         u4 is not None and "/source/main) ucu YOKTUR" in str(u4) and "populate_badi_spot" in str(u4),
         str(u4)[:160])
    # Eski kod (taban) karsitligi icin yeni semboller getattr ile okunur: eski agacta vektor
    # COKMEZ, FAIL olur (cokme != FAIL).
    isl = getattr(OT, "GENERIC_ISLEM_ADLARI", ("silme", "kilit", "metadata", "atc", "kaynak"))
    reddi = getattr(OT, "islem_reddi", None)
    u5 = [] if reddi else [("islem_reddi", "yok")]
    for t, info in OT.OBJECT_TYPES.items():
        if t == "enhancementspot" or not reddi:
            continue
        for i in isl:
            if reddi(t, i) is not None:
                u5.append((t, i, "reddi"))
        if info.get("url_path"):
            if {_sessiz(OT.get_object_url, "ZX_A", t, islem=i)[0] for i in (None,) + tuple(isl)} != \
                    {"/sap/bc/adt/%s/zx_a" % info["url_path"]}:
                u5.append((t, "url"))
    ekle("U5 FP: diger %d tip islem'den ETKILENMEZ (url ayni, ret yok)" % (len(OT.OBJECT_TYPES) - 1),
         not u5 and len(OT.OBJECT_TYPES) >= 17, u5)
    u6 = (OT.get_adt_type_from_url(KOL + "/zsd001_es_ornek"),
          OT.get_adt_type_from_url("/sap/bc/adt/oo/classes/zcl_x"))
    ekle("U6 get_adt_type_from_url: ENHS/XSB (eskiden UNKNOWN) · sinif degismedi",
         u6 == ("ENHS/XSB", "CLAS/OC"), u6)
    u7 = (_sessiz(OT.supports_generic_url, "enhs")[0], _sessiz(OT.supports_generic_url, "enhs", "silme")[0],
          _sessiz(OT.supports_generic_url, "enhs", "atc")[0], _sessiz(OT.supports_generic_url, "class")[0])
    ekle("U7 supports_generic_url islem'e duyarli (F,T,F,T)", u7 == (False, True, False, True), u7)
    ekle("U8 bilinmeyen islem adi -> ValueError (yazim hatasi sessiz izin olmaz)",
         reddi is not None and red(reddi, "enhs", "silmee") is not None and red(reddi, "class", "xx") is not None)

    # ── D: silme ─────────────────────────────────────────────────────────────
    sv = Sunucu()
    c = istemci(sv)
    sonuc, exc, log = _sessiz(c.delete_object, SPOT, "enhs", transport=TR, confirm=False)
    dl = [(m, y, q) for m, y, q in sv.istekler if m == "DELETE"]
    kilit = [(y, q) for m, y, q in sv.istekler if m == "POST" and q.get("_action") == "LOCK"]
    ekle("D1 delete_object ENHS: nesne URL'i kilidi -> DELETE(lockHandle+corrNr) -> UNLOCK",
         sonuc is True and len(dl) == 1 and dl[0][1] == L.enhs_spot_url(SPOT)
         and dl[0][2].get("lockHandle") == "SAHTE-KILIT-0001" and dl[0][2].get("corrNr") == TR
         and [y for y, _ in kilit] == ["/sap/bc/adt/locks", "/sap/bc/adt/core/objectlock",
                                       L.enhs_spot_url(SPOT)]   # OLCULEN sira (#413)
         and sv.say(lambda m, y, q: q.get("_action") == "UNLOCK") == 1 and SPOT.lower() not in sv.spotlar,
         f"sonuc={sonuc} exc={exc!r} dl={dl} kilit={kilit} log={log[-160:]!r}")
    sv = Sunucu()
    istemci(sv)
    r, exc, _ = _sessiz(AT.adt_delete, SPOT, "enhs", transport=TR)
    ekle("D2 MCP adt_delete ENHS: ok + delete_verified (silme sonrasi GET */* 404)",
         isinstance(r, dict) and r.get("ok") is True and r.get("delete_verified") is True,
         {k: (r or {}).get(k) for k in ("ok", "deleted", "delete_verified", "delete_reason", "error", "message")}
         if isinstance(r, dict) else exc)
    sv = Sunucu(spotlar=("ES_BADI_ORNEK",))
    istemci(sv)
    r, exc, _ = _sessiz(AT.adt_delete, "ES_BADI_ORNEK", "enhs", transport=TR)
    ekle("D3 standart spot silme -> guardrail, SIFIR SAP istegi",
         isinstance(r, dict) and r.get("ok") is False and not sv.sap_istekleri(),
         f"{(r or {}).get('error') if isinstance(r, dict) else exc} istek={sv.sap_istekleri()[:3]}")

    # ── K: kilit sorgusu ─────────────────────────────────────────────────────
    sv = Sunucu()
    istemci(sv)
    r, exc, _ = _sessiz(Q.adt_lock_check, SPOT, "enhs")
    lk = [q.get("objectRef") for m, y, q in sv.istekler if m == "GET" and y == "/sap/bc/adt/locks"]
    ekle("K1 adt_lock_check ENHS: exists True + locked None + kilit_belirsiz (GET /locks 404, durust)",
         isinstance(r, dict) and r.get("exists") is True and r.get("locked") is None
         and r.get("error") == "kilit_belirsiz" and r.get("reason") == "http_404"
         and lk == [L.enhs_spot_url(SPOT)],
         f"{ {k: (r or {}).get(k) for k in ('ok', 'exists', 'locked', 'error', 'reason')} if isinstance(r, dict) else exc} lk={lk}")
    sv = Sunucu(spotlar=())
    istemci(sv)
    r, exc, _ = _sessiz(Q.adt_lock_check, SPOT, "enhs")
    ekle("K2 adt_lock_check var olmayan spot -> exists False (metadata */* 404)",
         isinstance(r, dict) and r.get("ok") is True and r.get("exists") is False,
         {k: (r or {}).get(k) for k in ("ok", "exists", "locked", "error")} if isinstance(r, dict) else exc)

    # ── A: ATC ───────────────────────────────────────────────────────────────
    atc = (lambda m, y, q: y.startswith("/sap/bc/adt/atc/"))
    sv = Sunucu()
    istemci(sv)
    r, exc, _ = _sessiz(Q.adt_atc_check, SPOT, "enhs", variant="DEFAULT")
    ekle("A1 adt_atc_check ENHS -> atc_kapsam_disi + finding_count None, SIFIR istek",
         isinstance(r, dict) and r.get("ok") is False and r.get("error") == "atc_kapsam_disi"
         and r.get("finding_count") is None and "KAPSAM DISI" in (r.get("message") or "")
         and not sv.sap_istekleri(),
         f"{ {k: (r or {}).get(k) for k in ('ok', 'error')} if isinstance(r, dict) else exc} istek={len(sv.sap_istekleri())}")
    sv = Sunucu()
    c = istemci(sv)
    r, exc, log = _sessiz(c.run_atc_check, SPOT, "enhs")
    ekle("A2 SAPClient.run_atc_check ENHS -> None + KAPSAM DISI log, SIFIR ATC istegi",
         r is None and exc is None and sv.say(atc) == 0 and "KAPSAM DISI" in log,
         f"r={r} exc={exc!r} atc={sv.say(atc)}")
    sv = Sunucu()
    c = istemci(sv)
    ex = red(RA.atc_bulgulari, SPOT, "enhs", client=c)
    ekle("A3 run_atc_check.atc_bulgulari ENHS -> ValueError, SIFIR ATC istegi",
         ex is not None and sv.say(atc) == 0, f"{str(ex)[:80]} atc={sv.say(atc)}")
    sv = Sunucu()
    istemci(sv)
    r, exc, _ = _sessiz(Q.adt_atc_check, "ZCL_ORNEK", "class", variant="DEFAULT")
    ekle("A4 KONTROL: sinifta ATC istegi GIDER ve ok:true doner",
         isinstance(r, dict) and r.get("ok") is True and sv.say(atc) >= 3,
         f"{(r or {}).get('error') if isinstance(r, dict) else exc} atc={sv.say(atc)}")

    # ── V: diger yollar ENHS'te KAPALI ───────────────────────────────────────
    akt = (lambda m, y, q: y.startswith("/sap/bc/adt/activation"))
    sv = Sunucu()
    c = istemci(sv)
    ex = red(c.activate_object, SPOT, "enhs")
    ekle("V1 SAPClient.activate_object ENHS -> ValueError, /activation istegi YOK",
         ex is not None and sv.say(akt) == 0, f"{str(ex)[:80]} akt={sv.say(akt)}")
    sv = Sunucu()
    istemci(sv)
    r, exc, _ = _sessiz(AT.adt_activate, SPOT, "enhs")
    ekle("V2 MCP adt_activate ENHS -> ok false, activated yok, /activation istegi YOK",
         isinstance(r, dict) and r.get("ok") is False and r.get("activated") is not True
         and sv.say(akt) == 0 and "activation_verified" not in r,
         f"{ {k: (r or {}).get(k) for k in ('ok', 'error', 'activated')} if isinstance(r, dict) else exc} akt={sv.say(akt)}")
    sv = Sunucu()
    c = istemci(sv)
    kaynak = Path(kum) / "spot.xml"
    kaynak.write_text("<x/>", encoding="utf-8")
    r, exc, _ = _sessiz(c.push_object, SPOT, "enhs", TR, str(kaynak))
    ekle("V3 push_object ENHS -> ValueError (kaynak ucu yok), SIFIR SAP istegi",
         isinstance(exc, ValueError) and "/source/main) ucu YOKTUR" in str(exc) and not sv.sap_istekleri(),
         f"r={str(r)[:60]} exc={str(exc)[:80]} istek={len(sv.sap_istekleri())}")
    sv = Sunucu()
    c = istemci(sv)
    v4 = (red(c.syntax_check, SPOT, "enhs"), red(c.object_exists, SPOT, "enhs"))
    ekle("V4 syntax_check (aktivasyon on-denetimi) + object_exists (where-used) ENHS -> ValueError, SIFIR istek",
         all(v4) and not sv.sap_istekleri(), f"{[str(x)[:40] for x in v4]} istek={len(sv.sap_istekleri())}")

    gecen = 0
    for ad, ok, detay in S:
        print(("[PASS] " if ok else "[FAIL] ") + ad + ("" if ok else "  -- " + detay))
        gecen += ok
    print(f"{gecen}/{len(S)} OK")
    shutil.rmtree(kum, ignore_errors=True)
    return 0 if gecen == len(S) else 1


def _mutasyon(kip) -> int:
    yol, eski, yeni, beklenen = MUTASYONLAR[kip]
    kok = Path(tempfile.mkdtemp(prefix="enhs_tip_kum_"))
    try:
        for d in ("scripts", "mcp_servers"):
            shutil.copytree(REPO / d, kok / d,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules"))
        hedef = kok / "tests" / "fixtures" / BURASI.name
        shutil.copytree(BURASI, hedef, ignore=shutil.ignore_patterns("__pycache__"))
        dosya = kok / yol
        asil = dosya.read_bytes().decode("utf-8")
        if asil.count(eski) != 1:
            print(f"[KURULAMADI] {kip} -> capa {asil.count(eski)} kez ({yol})")
            return 3
        mutant = asil.replace(eski, yeni, 1)
        try:
            compile(mutant, str(dosya), "exec")
        except SyntaxError as exc:
            print(f"[KURULAMADI] {kip} -> mutant derlenmedi: {exc}")
            return 3
        dosya.write_bytes(mutant.encode("utf-8"))
        r = subprocess.run([sys.executable, str(hedef / "run.py")], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600, cwd=str(kok))
        m = re.search(r"^(\d+)/(\d+) OK$", r.stdout, re.M)
        if not m:
            son = [x for x in (r.stdout + r.stderr).splitlines() if x.strip()][-1:] or ["-"]
            print(f"[ALT-SUREC SAYI VERMEDI] {kip} rc={r.returncode} son={son[0][:160]}")
            return 3
        dusen = {x.split()[1] for x in r.stdout.splitlines() if x.strip().startswith("[FAIL]")}
        print(f"{kip}: {m.group(0)} · dusen={sorted(dusen)} · ilan={sorted(beklenen)}")
        if dusen == beklenen:
            print("MUTASYON DUSTU (ilan edilen kume TAM)")
            return 1
        print(f"[SAPMA] fazla={sorted(dusen - beklenen)} eksik={sorted(beklenen - dusen)}")
        return 2
    finally:
        shutil.rmtree(kok, ignore_errors=True)


if __name__ == "__main__":
    _kipler = [a for a in sys.argv[1:] if a.startswith("--")]
    if _kipler:
        if len(_kipler) != 1 or _kipler[0] not in MUTASYONLAR:
            print(f"[KULLANIM] gecerli kipler: {KIPLER}")
            sys.exit(2)
        sys.exit(_mutasyon(_kipler[0]))
    sys.exit(main())
