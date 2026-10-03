#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dump_okuma fixture — `adt_dump_read` + `adt_dump_list` (ST22) SAP'siz davranış korpusu.

NEDEN VAR (2026-10-03, K4 — kullanıcı onayı ADT-altyapı)
  `adt_dump_list` yalnız liste veriyordu; dump GÖVDESİ okunamıyordu (radar V2, Q149 aday
  aksiyonu). Yeni `adt_dump_read` yapılandırılmış XML / özet / tam metin okur. Aynı turda
  iki yan değişmez eklendi:
  · ARAÇ GÜRÜLTÜSÜ: canlı DEV feed'inde son 100 dumpın 36'sı `GENERATE_SUBPOOL_DIR_FULL` ∧
    `CL_ADT_DP_OPEN_SQL_HANDLER====CP` (ADT SQL konsolu). İmza İKİ alanın VE'sidir; liste
    dumpı ATMAZ, etiketler.
  · BAŞKA CLIENT (kullanıcı kararı 2026-10-03): DEV bağlantısının (client 100) feed'inde
    client 110 dumpları da görünüyordu (ölçüldü 49/100). Varsayılan GİZLENİR / OKUNMAZ;
    `acknowledge_risk=True` açar. Client tespit edilemeyen girdi de gizlenir (fail-closed)
    ama SAYISI ayrı alanda + notice ile döner ⇒ "dump yok" yanılgısı üretilmez.

ÖLÇÜLEN DEĞİŞMEZLER (vektör kimliği = satırın ilk sözcüğü)
  L*  liste: gizleme + sayaçlar + notice · gürültü VE-imzası (FP çapaları L3b/L3c) ·
      özet başlığı client otoritesi (L7) · sabit-genişlik kimlik (L8) · tier guard (L5)
  R*  okuma: alanlar · kimlik normalizasyonu · 404 ≠ sessiz boş · başka client · özet ·
      formatted bayt tavanı · hata yolları
  ⛔ SİLİNMEZ FP ÇAPALARI: L3b/L3c (tek alan eşleşmesi gürültü DEĞİL) · L2/R6b (ack ile
     başka client GÖRÜNÜR) · R1 (aynı client'ta tek GET, PII guard'ı engellemez). Bunlar
     olmadan "her şeyi gizle / her şeyi gürültü say" diyen bir kusur da geçerdi.

SAP GEREKTİRMEZ: HTTP oturumu sahtelenir; veriler JENERİK (gerçek kullanıcı/sistem YOK).

MUTASYON (CORE-07): kaynak METNİ gerçek `__file__` ile exec edilir; çapa TAM 1 kez eşleşmeli.
  Her kipin düşmesi BEKLENEN küme `_BEKLENEN_DUSEN`'de pinli, EŞİTLİKLE kıyaslanır.
  Çıkış: 0 taban yeşil · 1 beklenen kümeyle düştü · 2 SAPMA · 3 DOĞRULANAMADI (çapa/derleme).
  python tests/fixtures/dump_okuma/run.py [--mutasyon-...]
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
import types
from pathlib import Path
from xml.sax.saxutils import escape

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
if not (REPO / "mcp_servers" / "sap_adt" / "tools" / "query.py").is_file():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")
for _p in (REPO, REPO / "scripts", REPO / "scripts" / "utils"):
    sys.path.insert(0, str(_p))
QUERY = REPO / "mcp_servers" / "sap_adt" / "tools" / "query.py"

# ── MCP SDK KÖPRÜSÜ (yalnız SDK yoksa; desen: sorgu_basarisizligi_gorunur) ──────────
try:  # pragma: no cover
    import mcp.server.fastmcp  # type: ignore  # noqa: F401
except Exception:
    _mcp, _srv, _fast = (types.ModuleType("mcp"), types.ModuleType("mcp.server"),
                         types.ModuleType("mcp.server.fastmcp"))

    class _FastMCP:
        def __init__(self, *a, **k):
            pass

        def tool(self, *a, **k):
            return lambda fn: fn

    _fast.FastMCP = _FastMCP          # type: ignore[attr-defined]
    _srv.fastmcp = _fast              # type: ignore[attr-defined]
    _mcp.server = _srv                # type: ignore[attr-defined]
    sys.modules.setdefault("mcp", _mcp)
    sys.modules.setdefault("mcp.server", _srv)
    sys.modules.setdefault("mcp.server.fastmcp", _fast)

try:
    from mcp_servers.sap_adt import _conn as CONN
    import mcp_servers.sap_adt.tools  # noqa: F401  (paket; query modülü aşağıda exec edilir)
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"[fixture-hatasi] modul yuklenemedi (sessiz gecme YOK): {exc}")

_GECERLI_KIP = frozenset({
    "--mutasyon-okuma-client-guard", "--mutasyon-okuma-bilinmeyen-acik",
    "--mutasyon-liste-gizleme-yok", "--mutasyon-liste-bilinmeyen-acik",
    "--mutasyon-gurultu-veya", "--mutasyon-id-bosluk", "--mutasyon-404-sessiz",
    "--mutasyon-formatted-tavansiz", "--mutasyon-ozet-client-otorite",
    "--mutasyon-liste-ozet-otorite"})

# CORE-07: kip -> düşmesi BEKLENEN vektör kimlikleri (EŞİTLİK; alt-küme değil).
_BEKLENEN_DUSEN = {
    "--mutasyon-okuma-client-guard": {"R6a", "R7b", "R7d"},
    "--mutasyon-okuma-bilinmeyen-acik": {"R7d"},
    "--mutasyon-liste-gizleme-yok": {"L1", "L4", "L6"},
    "--mutasyon-liste-bilinmeyen-acik": {"L1", "L4", "L6"},
    "--mutasyon-gurultu-veya": {"L3a", "L3b", "L3c"},
    "--mutasyon-id-bosluk": {"L1", "L8"},
    "--mutasyon-404-sessiz": {"R4"},
    "--mutasyon-formatted-tavansiz": {"R10a"},
    "--mutasyon-ozet-client-otorite": {"R9"},
    "--mutasyon-liste-ozet-otorite": {"L1", "L7"},
}

# (eski, yeni) — eski TAM 1 kez eşleşmeli.
_MUT = {
    "--mutasyon-okuma-client-guard": (
        "            if karar != \"ayni\" and not acknowledge_risk:\n",
        "            if False:\n"),
    "--mutasyon-okuma-bilinmeyen-acik": (
        "            if karar != \"ayni\" and not acknowledge_risk:\n",
        "            if karar == \"farkli\" and not acknowledge_risk:\n"),
    "--mutasyon-liste-gizleme-yok": (
        "            if not acknowledge_risk and karar != \"ayni\":\n",
        "            if False:\n"),
    "--mutasyon-liste-bilinmeyen-acik": (
        "            if not acknowledge_risk and karar != \"ayni\":\n",
        "            if not acknowledge_risk and karar == \"farkli\":\n"),
    "--mutasyon-gurultu-veya": (
        "    return _ARAC_GURULTUSU.get((error_type or \"\", program or \"\"))\n",
        "    return next((s for (e, p), s in _ARAC_GURULTUSU.items()\n"
        "                 if e == error_type or p == program), None)\n"),
    "--mutasyon-id-bosluk": (
        "    if len(ham) == 70 and ham[:14].isdigit() and ham[58:61].isdigit():\n"
        "        return ham[58:61]\n",
        "    t = ham.split()\n"
        "    if len(t) == 4 and t[2].isdigit():\n"
        "        return t[2]\n"),
    "--mutasyon-404-sessiz": (
        "        if r.status_code == 404:\n            return _bulunamadi(r)\n",
        "        if r.status_code == 404:\n            return {\"ok\": True, \"id\": kodlu}\n"),
    "--mutasyon-formatted-tavansiz": (
        "                parca = ham_b[:tavan]\n",
        "                parca = ham_b\n"),
    "--mutasyon-ozet-client-otorite": (
        "                if o_client and o_client != d_client:\n",
        "                if False:\n"),
    "--mutasyon-liste-ozet-otorite": (
        "            d_client = (_ozet_ayristir(ozet.text)[\"header\"].get(\"Client\")\n"
        "                        if ozet is not None and ozet.text else None)\n",
        "            d_client = None\n"),
}

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(ok), detay))


# ══ JENERİK VERİ (gerçek sistem/kullanıcı YOK) ═══════════════════════════════════
URL = "https://sap.example.invalid:44300"
HOST = "sapapp01_XYZ_00"


def kimlik(ts: str, kullanici: str, client: str, no: str = "07") -> str:
    """SNAP anahtarı biçimi: 14 zaman + 32 host + 12 kullanıcı + 3 client + 9 → uzunluk 70."""
    ham = ts + HOST.ljust(32) + kullanici.ljust(12) + client + no.rjust(9)
    assert len(ham) == 70, len(ham)
    return ham


def kodla(ham: str) -> str:
    return ham.replace(" ", "%20")


def ozet_html(client: str | None, kullanici: str = "KULLANICI1", ek_bolum: bool = False) -> str:
    satirlar = [("Short Text", "A row already exists with this key"),
                ("Runtime Error", "ITAB_DUPLICATE_KEY"),
                ("Program", "ZCL_SD001_ORNEK===============CP"),
                ("Date/Time", "01.01.2026 12:00:00 (System)"),
                ("User", "%s (Ad Soyad)" % kullanici)]
    if client is not None:
        satirlar.append(("Client", client))
    satirlar.append(("Host", HOST))
    tablo = "".join('<tr><td><b>%s&nbsp;</b></td><td nowrap> %s </td></tr>' % (a, d)
                    for a, d in satirlar)
    h = ('<p><a class="showInRuntimeViewerLink" href="adt://XYZ/x">Show in Runtime Error '
         'Viewer</a></p><h4 id="OVERVIEW">Contents</h4><a href="#HEADERX">Header Information</a>'
         '<br><h4 id="HEADERX">Header Information</h4><table cellspacing="3">' + tablo + '</table>'
         '<h4 id="WHATHAPPENED">What happened?</h4>Error in the ABAP application program.<br><br>'
         'The current program had to be terminated.'
         '<h4 id="ERROR">Error analysis</h4>Duplicate key in "&lt;fs&gt;"<br>second line'
         '<h4 id="TERMINATION">Information on where terminated</h4>The termination occurred in '
         '"LOAD_DATA".<br><br>In the source code, the termination point is in line 6 of include '
         '"ZCL_SD001_ORNEK===============CM009".'
         '<h4 id="SOURCE">Source Code Extract</h4><style> .keyword { color: blue } </style>'
         '<table id="sourcetable"><tr><td id="sourcetablecolumn"><span class="linenumber">1</span>'
         '<span class="linenumber"><a title="Show where terminated" href="adt://XYZ/t#start=211">'
         '<span class="indicator">></span></a></span><span class="linenumber">3</span></td>'
         '<td id="sourcetablecolumn"><div lang="#" class="sourceline"><span>&nbsp;&nbsp;'
         '<span class="keyword">METHOD</span> load_data<span class="keyword">.</span></span></div>'
         '<div lang="#" class="sourceline highlight"><a href="adt://XYZ/t#start=211"><span>'
         '&nbsp;&nbsp;&nbsp;&nbsp;<span class="keyword">INSERT</span> ls INTO TABLE lt.</span></a></div>'
         '<div lang="#" class="sourceline"><span>&nbsp;&nbsp;<span class="keyword">ENDMETHOD</span>'
         '.</span></div></td></tr></table>'
         '<h4 id="STACK">Active Calls/Events</h4><style>code { font-family: x; }</style>'
         '<table cellspacing="5"><tr><th align="left">No.</th><th align="left">Event</th>'
         '<th align="left">Program</th><th align="left">Include</th><th align="left">Line</th></tr>'
         '<tr><td><code><a href="adt://XYZ/sap/bc/adt/oo/classes/zcl_sd001_ornek/source/main#start=211">'
         '2</a></code></td><td><code>LOAD_DATA</code></td><td><code>ZCL_SD001_ORNEK===============CP'
         '</code></td><td><code>ZCL_SD001_ORNEK===============CM009</code></td><td><code>6</code>'
         '</td></tr><tr><td><code><a href="adt://XYZ/sap/bc/adt/programs/programs/zsd001_p_ornek/source/'
         'main#start=83">1</a></code></td><td><code>START-OF-SELECTION</code></td><td><code>'
         'ZSD001_P_ORNEK</code></td><td><code>ZSD001_P_ORNEK</code></td><td><code>83</code></td>'
         '</tr></table>')
    if ek_bolum:
        h += '<h4 id="EXTRA">Yeni bolum</h4>beklenmeyen icerik'
    return h


def dump_xml(ham: str, hata: str, program: str, istisna: str = "") -> bytes:
    k = kodla(ham)
    return ('<?xml version="1.0" encoding="utf-8"?><dump:dump title="Runtime Error: %s 01.01.2026 '
            '12:00:00 KULLANICI1 (Ad Soyad)" error="%s" author="KULLANICI1" exception="%s" '
            'terminatedProgram="%s" serverInstance="%s" datetime="2026-01-01T09:00:00Z" '
            'systemDate="01.01.2026" systemTime="12:00:00" language="TR" '
            'xmlns:dump="http://www.sap.com/adt/categories/dump"><dump:links>'
            '<dump:link relation="self" uri="/sap/bc/adt/runtime/dump/%s" '
            'contentType="application/vnd.sap.adt.runtime.dump.v1+xml"/>'
            '<dump:link relation="http://www.sap.com/adt/relations/runtime/dump/termination" '
            'uri="adt://XYZ/sap/bc/adt/oo/classes/zcl_sd001_ornek/source/main#start=211" '
            'contentType=""/></dump:links><dump:chapters><dump:chapter name="kap0" '
            'title="Short Text" line="10"/></dump:chapters></dump:dump>'
            % (hata, hata, istisna, program, HOST, k)).encode("utf-8")


NOTFOUND = ('<?xml version="1.0" encoding="utf-8"?><exc:exception xmlns:exc="http://www.sap.com/'
            'abapxml/types/communicationframework"><namespace id="com.sap.adt.runtime.dump"/>'
            '<type id="notFound"/><message lang="EN">An exception was raised</message>'
            '<localizedMessage lang="TR">An exception was raised</localizedMessage><properties>'
            '<entry key="T100KEY-ID">SY</entry><entry key="T100KEY-NO">530</entry></properties>'
            '</exc:exception>').encode("utf-8")

ADT_SQL = "CL_ADT_DP_OPEN_SQL_HANDLER====CP"
ZPROG = "ZCL_SD001_ORNEK===============CP"
FEED_GIRDI = [
    # ad, ham kimlik, hata, program, özet-client (None=özet YOK, "-"=özette Client satırı yok)
    ("E1", kimlik("20260101120001", "KULLANICI1", "100"), "GENERATE_SUBPOOL_DIR_FULL", ADT_SQL, "100"),
    ("E2", kimlik("20260101120002", "KULLANICI1", "100"), "GENERATE_SUBPOOL_DIR_FULL", ZPROG, "100"),
    ("E3", kimlik("20260101120003", "KULLANICI1", "100"), "ITAB_DUPLICATE_KEY", ADT_SQL, "100"),
    ("E4", kimlik("20260101120004", "KULLANICI2", "110"), "ITAB_DUPLICATE_KEY", ZPROG, "110"),
    ("E5", "20260101120005" + HOST + " KISA", "ITAB_DUPLICATE_KEY", ZPROG, None),
    ("E6", kimlik("20260101120006", "KULLANICI1", "100"), "ITAB_DUPLICATE_KEY", ZPROG, None),
    ("E7", kimlik("20260101120007", "KULLANICI1", "110"), "ITAB_DUPLICATE_KEY", ZPROG, "100"),
    ("E8", kimlik("20260101120008", "KULLANICIUZN", "110"), "ITAB_DUPLICATE_KEY", ZPROG, None),
]


def feed_xml() -> bytes:
    A = "http://www.w3.org/2005/Atom"
    girdiler = []
    for ad, ham, hata, prog, oz in FEED_GIRDI:
        k = kodla(ham)
        ozet = ("" if oz is None else
                '<summary type="html">%s</summary>' % escape(ozet_html(None if oz == "-" else oz)))
        girdiler.append(
            '<entry><author><name>%s</name></author><category term="%s" label="ABAP runtime error"/>'
            '<category term="%s" label="Terminated ABAP program"/><id>/sap/bc/adt/vit/runtime/dumps/'
            '%s</id><link href="adt://XYZ/sap/bc/adt/runtime/dump/%s" rel="self"/><updated>'
            '2026-01-01T09:00:00Z</updated><title>%s</title>%s</entry>'
            % (ad, hata, prog, k, k, ad, ozet))
    return ('<?xml version="1.0" encoding="utf-8"?><feed xmlns="%s">%s</feed>'
            % (A, "".join(girdiler))).encode("utf-8")


# ══ SAHTE HTTP ═════════════════════════════════════════════════════════════════
class _Yanit:
    def __init__(self, status: int, govde: bytes):
        self.status_code = status
        self.content = govde
        self.text = govde.decode("utf-8", "replace")
        self.headers = {}


class _Oturum:
    def __init__(self, yollar: dict, firlat: Exception | None = None):
        self.yollar = yollar        # yol-soneki (URL - kök) -> (status, bytes)
        self.cagrilar: list = []
        self.firlat = firlat

    def get(self, url, params=None, headers=None, verify=None, timeout=None):
        yol = url[len(URL):]
        self.cagrilar.append((yol, (headers or {}).get("Accept"), params))
        if self.firlat:
            raise self.firlat
        st, g = self.yollar.get(yol, (404, NOTFOUND))
        return _Yanit(st, g)


def istemci(yollar: dict, client: str | None = "100", firlat=None):
    adt = types.SimpleNamespace(url=URL, session=_Oturum(yollar, firlat), client=client)
    return types.SimpleNamespace(adt_client=adt)


def D(ham: str, son: str = "") -> str:
    return "/sap/bc/adt/runtime/dump/" + kodla(ham) + son


def modul_yukle(kaynak: str) -> types.ModuleType:
    ad = "mcp_servers.sap_adt.tools.query"
    mod = types.ModuleType(ad)
    mod.__file__ = str(QUERY)
    mod.__package__ = "mcp_servers.sap_adt.tools"
    sys.modules[ad] = mod
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        exec(compile(kaynak, str(QUERY), "exec"), mod.__dict__)
    return mod


def main(kip: str | None) -> int:
    kaynak = QUERY.read_text(encoding="utf-8")
    if kip:
        eski, yeni = _MUT[kip]
        n = kaynak.count(eski)
        if n != 1:
            sys.stderr.write("[DOGRULANAMADI] mutasyon capasi %d kez eslesti (beklenen 1): %s "
                             "-> hicbir sayi raporlanmadi.\n" % (n, kip))
            return 3
        kaynak = kaynak.replace(eski, yeni, 1)
        try:
            compile(kaynak, str(QUERY), "exec")
        except SyntaxError as e:
            sys.stderr.write("[DOGRULANAMADI] mutant DERLENMEDI (%s): %s\n" % (kip, e))
            return 3
        print("mutasyon:", kip)
    Q = modul_yukle(kaynak)
    tier = {"v": "DEV"}
    CONN.get_active_tier = lambda: tier["v"]      # type: ignore[assignment]

    def kur(yollar, client="100", firlat=None):
        c = istemci(yollar, client, firlat)
        Q._get_client = lambda: c
        return c.adt_client.session

    # ═══ L) adt_dump_list ══════════════════════════════════════════════════════
    FEED = {"/sap/bc/adt/runtime/dumps": (200, feed_xml())}
    s = kur(FEED)
    r = Q.adt_dump_list(limit=50)
    adlar = [d["user"] for d in r.get("dumps", [])]
    kontrol("L1 varsayilan: baska client + bilinmeyen GIZLI, sayaclar + notice ('dump yok' DEGIL)",
            r.get("ok") and adlar == ["E1", "E2", "E3", "E6", "E7"]
            and r.get("gizlenen_baska_client") == 2 and r.get("gizlenen_client_bilinmeyen") == 1
            and r.get("taranan") == 8 and "dump yok" in r.get("notice", "")
            and "acknowledge_risk=True" in r.get("notice", ""),
            "adlar=%s gizli=%s/%s" % (adlar, r.get("gizlenen_baska_client"),
                                      r.get("gizlenen_client_bilinmeyen")))
    ra = Q.adt_dump_list(limit=50, acknowledge_risk=True)
    cl = {d["user"]: d.get("client") for d in ra.get("dumps", [])}
    kontrol("L2 ack: hepsi gorunur + her girdide client (bilinmeyen = None), notice yok",
            ra.get("count") == 8 and cl.get("E4") == "110" and cl.get("E5") is None
            and cl.get("E1") == "100" and "notice" not in ra, "client=%s" % cl)
    gr = {d["user"]: d.get("arac_gurultusu") for d in ra.get("dumps", [])}
    kontrol("L3a gurultu: SUBPOOL ∧ ADT SQL isleyicisi -> arac_gurultusu + sebep",
            gr.get("E1") is True and ra["dumps"][0].get("arac_gurultusu_sebep")
            and ra.get("arac_gurultusu_sayisi") == 1, "gr=%s" % gr)
    kontrol("L3b FP capasi: SUBPOOL baska programda -> gurultu DEGIL", gr.get("E2") is False)
    kontrol("L3c FP capasi: ADT SQL isleyicisi baska hatayla -> gurultu DEGIL", gr.get("E3") is False)
    r4 = Q.adt_dump_list(limit=4)
    kontrol("L4 limit gorunenleri sayar; gizlenenler taranan icinde ayri sayilir",
            [d["user"] for d in r4["dumps"]] == ["E1", "E2", "E3", "E6"] and r4["taranan"] == 6
            and r4["gizlenen_baska_client"] == 1 and r4["gizlenen_client_bilinmeyen"] == 1,
            "%s taranan=%s" % ([d["user"] for d in r4["dumps"]], r4["taranan"]))
    tier["v"] = "QA"
    s = kur(FEED)
    r5 = Q.adt_dump_list()
    kontrol("L5 QA tier ack'siz -> tier_pii_guard + HTTP YOK",
            r5.get("error") == "tier_pii_guard" and s.cagrilar == [])
    tier["v"] = "DEV"
    kur(FEED, client=None)
    r6 = Q.adt_dump_list(limit=50)
    kontrol("L6 baglanti client'i bilinmiyor -> fail-closed: hepsi gizli, sayac + notice",
            r6.get("count") == 0 and r6.get("gizlenen_client_bilinmeyen") == 8
            and "notice" in r6, "count=%s gizli=%s" % (r6.get("count"),
                                                     r6.get("gizlenen_client_bilinmeyen")))
    kontrol("L7 ozet basligi client OTORITE (id 110, ozet 100 -> gorunur)", "E7" in adlar)
    kontrol("L8 12 karakter kullanici: sabit-genislik kimlik -> client 110 (baska client sayaci)",
            cl.get("E8") == "110", "E8=%s" % cl.get("E8"))

    # ═══ R) adt_dump_read ══════════════════════════════════════════════════════
    h100 = kimlik("20260101130000", "KULLANICI1", "100")
    h110 = kimlik("20260101130001", "KULLANICI2", "110")
    hsub = kimlik("20260101130002", "KULLANICI1", "100")
    kisa = "20260101130003" + HOST + "_KISA"
    yollar = {
        D(h100): (200, dump_xml(h100, "ITAB_DUPLICATE_KEY", ZPROG)),
        D(h110): (200, dump_xml(h110, "ITAB_DUPLICATE_KEY", ZPROG)),
        D(hsub): (200, dump_xml(hsub, "GENERATE_SUBPOOL_DIR_FULL", ADT_SQL,
                                "CX_SY_GENERATE_SUBPOOL_FULL")),
        D(h100, "/summary"): (200, ozet_html("100", ek_bolum=True).encode("utf-8")),
        D(kisa): (200, dump_xml(kisa, "ITAB_DUPLICATE_KEY", ZPROG)),
        D(kisa, "/summary"): (200, ozet_html("100").encode("utf-8")),
    }
    s = kur(yollar)
    r = Q.adt_dump_read(dump="adt://XYZ" + D(h100))
    kontrol("R1 varsayilan: alanlar + termination satiri + TEK GET (vnd Accept), ozet/formatted YOK",
            r.get("ok") and r.get("error_type") == "ITAB_DUPLICATE_KEY" and r.get("program") == ZPROG
            and r.get("user") == "KULLANICI1" and r.get("exception") is None
            and r.get("termination", {}).get("line") == 211 and r.get("client") == "100"
            and s.cagrilar == [(D(h100), "application/vnd.sap.adt.runtime.dump.v1+xml", None)]
            and "formatted OKUNMADI" in r.get("kapsam", ""),
            "cagri=%s" % s.cagrilar)
    bicimler = ["adt://XYZ" + D(h100), "/sap/bc/adt/vit/runtime/dumps/" + kodla(h100), h100,
                kodla(h100), D(h100, "/summary"), "  " + kodla(h100) + "#x  "]
    urller = []
    for b in bicimler:
        s = kur(yollar)
        Q.adt_dump_read(dump=b)
        urller.append(s.cagrilar[-1][0] if s.cagrilar else None)
    kontrol("R2 kimlik normalizasyonu: 6 bicim AYNI URL", set(urller) == {D(h100)}, "%s" % urller)
    kur(yollar)
    rs = Q.adt_dump_read(dump=kodla(hsub))
    kontrol("R3 okuma: gurultu imzasi etiketlenir + istisna sinifi",
            rs.get("arac_gurultusu") is True and rs.get("exception") == "CX_SY_GENERATE_SUBPOOL_FULL"
            and r.get("arac_gurultusu") is False)
    kur(yollar)
    r4 = Q.adt_dump_read(dump=kodla(kimlik("20260101139999", "KULLANICI1", "100")))
    kontrol("R4 404 -> ok:false dump_bulunamadi + SAP sebebi (sessiz bos YOK)",
            r4.get("ok") is False and r4.get("error") == "dump_bulunamadi"
            and "notFound" in r4.get("message", "") and "SY/530" in r4.get("message", ""),
            "%s" % r4)
    kur({D(h100): (500, NOTFOUND.replace(b"notFound", b"internal"))})
    r5 = Q.adt_dump_read(dump=h100)
    kontrol("R5 500 -> ok:false http_500 + ayristirilmis SAP mesaji",
            r5.get("error") == "http_500" and "internal" in r5.get("message", ""), "%s" % r5)
    s = kur(yollar)
    r6 = Q.adt_dump_read(dump=h110)
    kontrol("R6a baska client ack'siz -> baska_client_pii + dump GOVDESI ISTENMEDI",
            r6.get("error") == "baska_client_pii" and r6.get("client") == "110"
            and s.cagrilar == [], "%s cagri=%s" % (r6.get("error"), s.cagrilar))
    kur(yollar)
    r6b = Q.adt_dump_read(dump=h110, acknowledge_risk=True)
    kontrol("R6b FP capasi: ack ile baska client OKUNUR", r6b.get("ok") and r6b.get("client") == "110")
    kur(yollar)
    r7 = Q.adt_dump_read(dump=kisa)
    kontrol("R7a kimlik bicimi tanimsiz -> client ozetten (100) -> okunur",
            r7.get("ok") and r7.get("client_kaynagi") == "summary" and r7.get("client") == "100",
            "%s" % {k: r7.get(k) for k in ("ok", "error", "client", "client_kaynagi")})
    y2 = dict(yollar)
    y2[D(kisa, "/summary")] = (200, ozet_html("110").encode("utf-8"))
    kur(y2)
    kontrol("R7b kimlik tanimsiz + ozet client 110 -> baska_client_pii",
            Q.adt_dump_read(dump=kisa).get("error") == "baska_client_pii")
    y3 = dict(yollar)
    del y3[D(kisa, "/summary")]
    del y3[D(kisa)]
    kur(y3)
    kontrol("R7c kimlik tanimsiz + ozet 404 -> dump_bulunamadi",
            Q.adt_dump_read(dump=kisa).get("error") == "dump_bulunamadi")
    y4 = dict(yollar)
    y4[D(kisa, "/summary")] = (500, b"<x/>")
    kur(y4)
    kontrol("R7d client TESPIT EDILEMEDI (ozet 500) ack'siz -> fail-closed baska_client_pii",
            Q.adt_dump_read(dump=kisa).get("error") == "baska_client_pii")
    s = kur(yollar)
    r8 = Q.adt_dump_read(dump=h100, summary=True)
    oz = r8.get("summary") or {}
    src = oz.get("source_extract", "")
    kontrol("R8 summary: header + bolumler + active_calls + '> ' kesilen satir + other_sections",
            r8.get("ok") and oz.get("header", {}).get("Runtime Error") == "ITAB_DUPLICATE_KEY"
            and oz.get("header", {}).get("Client") == "100"
            and "Duplicate key in \"<fs>\"\nsecond line" == oz.get("error_analysis")
            and "line 6 of include" in oz.get("where_terminated", "")
            and ">     INSERT ls INTO TABLE lt." in src and "  METHOD load_data." in src
            and "color" not in src and "211" not in src
            and oz.get("active_calls", [{}])[0].get("include") == "ZCL_SD001_ORNEK===============CM009"
            and oz["active_calls"][0].get("line") == "6"
            and oz["active_calls"][1].get("uri", "").endswith("#start=83")
            and oz.get("other_sections") == {"EXTRA": "beklenmeyen icerik"}
            and len(s.cagrilar) == 2,
            "src=%r calls=%s other=%s" % (src[:80], oz.get("active_calls"), oz.get("other_sections")))
    y5 = dict(yollar)
    y5[D(h100, "/summary")] = (200, ozet_html("110").encode("utf-8"))
    kur(y5)
    r9 = Q.adt_dump_read(dump=h100, summary=True)
    kontrol("R9 ozet client (110) kimlikten (100) farkli -> ack'siz baska_client_pii",
            r9.get("error") == "baska_client_pii", "%s" % r9.get("error"))
    metin = ("Kısa döküm başlığı\n" + "ş" * 3000).encode("utf-8")
    y6 = dict(yollar)
    y6[D(h100, "/formatted")] = (200, metin)
    kur(y6)
    r10 = Q.adt_dump_read(dump=h100, formatted=True, max_bytes=1001)
    ft = r10.get("formatted_text", "")
    kontrol("R10a formatted: bayt tavani + truncated + toplam boy + yarim karakter YOK",
            r10.get("truncated") is True and r10.get("formatted_total_bytes") == len(metin)
            and r10.get("formatted_returned_bytes", 10**9) <= 1001 and "�" not in ft
            and len(ft.encode("utf-8")) == r10.get("formatted_returned_bytes"),
            "trunc=%s ret=%s" % (r10.get("truncated"), r10.get("formatted_returned_bytes")))
    kur(y6)
    r10b = Q.adt_dump_read(dump=h100, formatted=True, max_bytes=10**9)
    kur(y6)
    r10c = Q.adt_dump_read(dump=h100, formatted=True, max_bytes=5)
    kontrol("R10b tavan kistirilir (1000..200000); kisa metin truncated=False",
            r10b.get("max_bytes") == 200000 and r10b.get("truncated") is False
            and r10c.get("max_bytes") == 1000, "%s/%s" % (r10b.get("max_bytes"), r10c.get("max_bytes")))
    tier["v"] = "QA"
    s = kur(yollar)
    r11 = Q.adt_dump_read(dump=h100)
    kontrol("R11 QA tier ack'siz -> tier_pii_guard + HTTP YOK",
            r11.get("error") == "tier_pii_guard" and s.cagrilar == [])
    tier["v"] = "DEV"
    s = kur(yollar)
    r12 = Q.adt_dump_read(dump="/sap/bc/adt/runtime/dumps")
    kontrol("R12 cozulemeyen kimlik -> gecersiz_dump_kimligi + HTTP YOK",
            r12.get("error") == "gecersiz_dump_kimligi" and s.cagrilar == [])
    from sap_adt_lib import SAPADTError  # type: ignore
    kur(yollar, firlat=SAPADTError("baglanti koptu", status_code=503))
    r13 = Q.adt_dump_read(dump=h100)
    kontrol("R13 oturum istisnasi -> ok:false (cokme YOK)", r13.get("ok") is False, "%s" % r13)
    y7 = dict(yollar)
    y7[D(h100, "/summary")] = (500, b"<x/>")
    kur(y7)
    r14 = Q.adt_dump_read(dump=h100, summary=True)
    kontrol("R14 istenen ozet okunamadi -> ok:false summary_okunamadi (sessiz ok YOK)",
            r14.get("ok") is False and r14.get("error") == "summary_okunamadi")

    hata = 0
    for ad, ok, detay in SONUC:
        hata += 0 if ok else 1
        print("[%s] %-78s %s" % ("ok" if ok else "FAIL", ad, detay if not ok else ""))
    print("%d/%d OK" % (len(SONUC) - hata, len(SONUC)))
    print("SONUC: %d/%d gecti" % (len(SONUC) - hata, len(SONUC)))
    if kip:
        dusen = {ad.split()[0] for ad, ok, _ in SONUC if not ok}
        beklenen = _BEKLENEN_DUSEN[kip]
        if dusen != beklenen:
            print("[SAPMA] %s: beklenen=%s dusen=%s fazla=%s eksik=%s -> exit 2"
                  % (kip, sorted(beklenen), sorted(dusen), sorted(dusen - beklenen),
                     sorted(beklenen - dusen)))
            return 2
        print("[BEKLENEN] %s: dusen kume = beklenen %s" % (kip, sorted(beklenen)))
        return 1
    return 1 if hata else 0


if __name__ == "__main__":
    os.environ.pop("CLAUDE_PROJECT_DIR", None)
    kip = None
    for _a in sys.argv[1:]:
        if _a.startswith("--mutasyon"):
            if _a not in _GECERLI_KIP:
                print("[KULLANIM] bilinmeyen mutasyon kipi: %s · gecerli kipler: %s"
                      % (_a, ", ".join(sorted(_GECERLI_KIP))))
                sys.exit(3)
            kip = _a
    sys.exit(main(kip))
