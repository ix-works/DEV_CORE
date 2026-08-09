#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""veri_yetki_guardlari fixture — PII guard'i ATLATAN sekil + guard'siz mutasyon tool'u.

NEDEN VAR (2026-08-01 adversarial bug-avi; KAYIT K-1/K-2/K-3):

K-1 `data_guard` (ADR 0011 PII) UC AYRI DELIK:
  (a) TAKMA AD: `is_sensitive_target("KNA1 AS K")` -> False (regex `^...$` capali,
      ciplak ad bekliyordu) ama `is_sensitive_target("KNA1")` -> True. Yani guard
      bir bosluk karakteriyle atlatiliyordu ve bu sekil CANLI calisiyor (avci
      `T000 AS T` ile 2 satir aldi). Ayni kacis: JOIN, virgullu liste, sema oneki
      ("SAPABAP1.KNA1" -> kardes tool bunu 'SAPABAP1' okuyup serbest birakiyordu).
  (b) ALAN-SEVIYESI GUARD OLU KOD: `is_sensitive_target(table, fields)` dogustan beri
      `fields=["STCD1"]` icin BLOCKED diyordu, ama HICBIR tool `fields=` gecirmiyordu.
      `columns` da dogrulanmadan SELECT'e giriyordu.
  (c) RELEASED CDS KAPSAM DISI: desen tablo-adi tabanliydi -> `I_Customer`,
      `I_BusinessPartner`, `V_KNA1` gorunmuyordu. Projenin KENDI standardi
      ("released CDS kullan") kullaniciyi tam o kor noktaya yonlendiriyordu.

K-2 `adt_syntax_check` MUTASYON YAPAN TEK GUARD'SIZ TOOL: `require_writable_tier` de
  namespace guard'i da YOKTU. Alt katman docstring'i "NOT READ-ONLY ... ACTIVATES it ...
  treat as WRITE" derken MCP docstring'i "read-only" diyordu (dokuman-yalani).

K-3 `adt_lock_check` KILIT TESPITI YAPAMIYORDU: strateji "metadata OKU; SAPLockError
  duserse kilitli" idi; okuma kilit hatasi uretmez ve alt katman her istisnayi yutar ->
  `locked: True` ULASILAMAZ olu daldi, tool DAIMA `locked: False` diyordu (kanitsiz
  olumsuzlama). Ayrica hata -> `exists: false` (adt_get DDIC daliyla ayni sinif).

⚠ KONTROL GRUBU BU TESTIN OMURGASI: hassas-OLMAYAN hedefler (T000, T000 AS T,
ZSD001_T_BOOKHD, TADIR, /SCWM/AQUA) SERBEST kalmali; DEV tier muafiyeti, acik-onay yolu
ve gecerli Z-obje syntax_check'i CALISMAYA devam etmeli. O satirlar kaldirilirsa test
asiri-siki olur ve gunluk isi bloklar.
"""
from __future__ import annotations

import os
import sys
import types
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
# `query.py` -> `_app.py` -> `from mcp.server.fastmcp import FastMCP`. Olculen sey guard
# davranisi; FastMCP kapsam DISI. CI'da SDK yoksa alakasiz bir bagimlilik testi kosulamaz
# kilar -> yalnizca EKSIKSE asgari sahte modul kurulur. Gercek SDK varsa DOKUNULMAZ.
# (Kaynak: tests/fixtures/adtget_yokluk_kaniti/run.py — ayni koprü.)
try:  # pragma: no cover - ortam kosullu
    import mcp.server.fastmcp  # type: ignore  # noqa: F401
except Exception:
    _mcp = types.ModuleType("mcp")
    _srv = types.ModuleType("mcp.server")
    _fast = types.ModuleType("mcp.server.fastmcp")

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
    from mcp_servers.sap_adt import _conn as CONN
    from mcp_servers.sap_adt import data_guard as DG
    from mcp_servers.sap_adt.tools import query as Q
    from sap_client import SAPClient
except Exception as exc:                                     # pragma: no cover
    raise SystemExit(f"[fixture-hatasi] modul yuklenemedi (sessiz gecme YOK): {exc}")

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul), detay))


def tier(deger):
    """Aktif tier'i sabitle (gercek .conn_adt okunmaz — yanlis olcum tuzagi)."""
    CONN.get_active_tier = lambda: deger                     # type: ignore[assignment]


# ═════════════════════════════════════════════════════════════════════════════════
# SAHTE KATMANLAR
# ═════════════════════════════════════════════════════════════════════════════════
class _SahteSqlClient:
    """SAP'ye giden sorguyu KAYDEDER — guard delinirse hangi SQL kacti gorunur."""

    def __init__(self):
        self.sorgular: list[str] = []

    def run_sql_query(self, q, max_rows=100):
        self.sorgular.append(q)
        return {"columns": ["A"], "data": [["1"]]}

    def syntax_check(self, name, object_type="class"):
        return {"valid": True, "errors": [], "warnings": []}


class _SahteAdt:
    def __init__(self, md_hata=None, kilit=None):
        self._md_hata = md_hata
        self._kilit = kilit

    def get_object_structure(self, url):
        if self._md_hata is not None:
            raise self._md_hata
        return "<xml>metadata</xml>"

    def is_object_locked(self, url):
        return self._kilit


class _SahteLockClient:
    """GERCEK `SAPClient.get_object_metadata` govdesini kullanir (istisna-yutma dahil)."""

    def __init__(self, md_hata=None, kilit=None):
        self.adt_client = _SahteAdt(md_hata, kilit)

    def get_object_metadata(self, object_name, object_type="class"):
        return SAPClient.get_object_metadata(self, object_name, object_type)


def _pii_bloklu(r: dict) -> bool:
    return r.get("code") == "ADR_0011_PII"


def dg_cagir(fn_adi: str, *a):
    """Opsiyonel data_guard API'si — YOKSA cokme degil, olculebilir bir 'yetenek yok'.

    ⚠ MUTASYON TESTI ICIN SART: fixture eski surume karsi kosturuldugunda
    `sensitive_matches`/`select_fields` HENUZ YOKTUR. Duz `DG.sensitive_matches(...)`
    AttributeError ile COKER ve kosucu HIC FAIL raporlamaz -> "cokme != FAIL" tuzagi
    (ilk surumde tam bu oldu: mutasyon 0 FAIL gosterdi, cunku hic olcum yapilmadi).
    """
    fn = getattr(DG, fn_adi, None)
    if fn is None:
        return None
    try:
        return fn(*a)
    except Exception as exc:                                 # pragma: no cover
        return f"[HATA] {exc}"


# ═════════════════════════════════════════════════════════════════════════════════
# A) data_guard NORMALIZASYONU + released CDS  (K-1a / K-1c)
# ═════════════════════════════════════════════════════════════════════════════════
def bolum_a() -> None:
    hassas = [
        ("KNA1", "KONTROL: ciplak hassas tablo (bu HEP calisiyordu)"),
        ("KNA1 AS K", "takma ad (AS)"),
        ("kna1 k", "takma ad (AS'siz, kucuk harf)"),
        ("SAPABAP1.KNA1", "sema oneki"),
        ("ZSD001_T_X AS B INNER JOIN LFA1 AS L ON B~LIFNR = L~LIFNR", "JOIN'li ifade"),
        ("T000, KNA1", "virgullu liste (ikincisi hassas)"),
        ("T000 UNION SELECT * FROM KNA1", "enjekte edilmis ikinci tablo"),
        ("I_Customer", "released CDS (semantik ad)"),
        ("I_BusinessPartner", "released CDS (BP)"),
        ("V_KNA1", "sarmalayici gorunum"),
        ("ZV_LFA1_KOPYA", "Z sarmalayici (segment eslesmesi)"),
    ]
    for ifade, aciklama in hassas:
        kontrol(f"A/HASSAS {aciklama}", DG.is_sensitive_target(ifade),
                f"{ifade!r} -> eslesme={dg_cagir('sensitive_matches', ifade)}")

    # ── KONTROL GRUBU (FP capasi): bunlar SERBEST kalmali ──
    temiz = ["T000", "T000 AS T", "ZSD001_T_BOOKHD", "TADIR", "DD02L", "TRDIR",
             "/SCWM/AQUA", "E070", "ZSD001_T_DORHD"]
    for ifade in temiz:
        kontrol(f"A/FP-CAPA hassas DEGIL: {ifade}", not DG.is_sensitive_target(ifade),
                f"eslesme={dg_cagir('sensitive_matches', ifade)}")

    # ── Alan-seviyesi (K-1b saf katman) ──
    kontrol("A/ALAN fields=['STCD1'] hassas", DG.is_sensitive_target("ZTEST", ["STCD1"]))
    kontrol("A/ALAN FP-CAPA fields=['VBELN','MATNR'] hassas DEGIL",
            not DG.is_sensitive_target("ZTEST", ["VBELN", "MATNR"]))
    cikarim = dg_cagir("select_fields", "SELECT k~stcd1, name1 AS n FROM kna1")
    kontrol("A/ALAN select_fields cikarimi", cikarim == ["STCD1", "NAME1"], str(cikarim))
    kontrol("A/ALAN select_fields('*') alan IDDIA ETMEZ",
            dg_cagir("select_fields", "SELECT * FROM t000") == [])


# ═════════════════════════════════════════════════════════════════════════════════
# B) TOOL KABLOLAMASI + IKI TOOL'UN ESDEGERLIGI  (K-1b — asil kusur AYRISMAYDI)
# ═════════════════════════════════════════════════════════════════════════════════
def bolum_b() -> None:
    istemci = _SahteSqlClient()
    Q._get_client = lambda: istemci                          # type: ignore[assignment]
    tier("PRD")

    # (1) alan-seviyesi guard KABLOLU mu? (fix oncesi: columns hic denetlenmiyordu)
    r = Q.adt_table_read(table="ZSD001_T_BOOKHD", columns="STCD1,NAME1")
    kontrol("B/K-1b adt_table_read(columns='STCD1') -> PII BLOK", _pii_bloklu(r),
            f"ok={r.get('ok')} code={r.get('code','-')}")
    r = Q.adt_sql_query(query="SELECT stcd1 FROM ZSD001_T_BOOKHD")
    kontrol("B/K-1b adt_sql_query(SELECT stcd1 ...) -> PII BLOK", _pii_bloklu(r),
            f"ok={r.get('ok')} code={r.get('code','-')}")

    # KONTROL GRUBU: hassas OLMAYAN kolonlar SERBEST + sorgu gercekten kosuyor
    n0 = len(istemci.sorgular)
    r = Q.adt_table_read(table="ZSD001_T_BOOKHD", columns="VBELN,MATNR")
    kontrol("B/FP-CAPA hassas-olmayan kolonlar SERBEST (ve SQL kostu)",
            r.get("ok") is True and len(istemci.sorgular) == n0 + 1,
            f"ok={r.get('ok')} sorgu={istemci.sorgular[-1] if istemci.sorgular else '-'}")

    # (2) IKI TOOL AYNI KARARI VERMELI (ayrisma = kusurun koku)
    esdeger = [
        ("KNA1", "SELECT * FROM KNA1", True),
        ("KNA1 AS K", "SELECT * FROM KNA1 AS K", True),
        ("SAPABAP1.KNA1", "SELECT * FROM SAPABAP1.KNA1", True),
        ("I_Customer", "SELECT * FROM I_Customer", True),
        ("T000", "SELECT * FROM T000", False),                          # KONTROL GRUBU
        ("ZSD001_T_BOOKHD", "SELECT * FROM ZSD001_T_BOOKHD", False),    # KONTROL GRUBU
    ]
    for tablo, sorgu, beklenen in esdeger:
        a = _pii_bloklu(Q.adt_table_read(table=tablo))
        b = _pii_bloklu(Q.adt_sql_query(query=sorgu))
        kontrol(f"B/ESDEGERLIK {tablo} -> iki tool da {'BLOK' if beklenen else 'SERBEST'}",
                a == beklenen and b == beklenen,
                f"table_read={a} sql_query={b}")

    # (3) SEKIL: serbest ifade tek-tablo tool'una girmez (enjeksiyon yuzeyi)
    n1 = len(istemci.sorgular)
    r = Q.adt_table_read(table="T000 UNION SELECT * FROM KNA1")
    kontrol("B/SEKIL enjekte ifade adt_table_read'de REDDEDILIR",
            r.get("ok") is False, f"error={r.get('error') or r.get('code')}")
    kontrol("B/SEKIL reddedilen cagri SAP'ye HIC GITMEDI",
            len(istemci.sorgular) == n1, f"sorgu_sayisi={len(istemci.sorgular)}")
    # PII'siz enjeksiyon: guard susar, SEKIL kontrolu tek basina yakalamali
    r = Q.adt_table_read(table="T000 AS T")
    kontrol("B/SEKIL PII'siz serbest ifade de REDDEDILIR (sekil tek basina)",
            r.get("error") == "gecersiz_tablo_adi", f"error={r.get('error')}")

    # (3b) GECMIS-ETKI CAPALARI — changelog'daki ESKI kayitlarin senaryolari yeniden kosar.
    #  · 2026-07-12 (core#24-25): adt_sql_query dogus-testi T100 uzerinde canli dogrulanmisti
    #    ("WHERE-5 / COUNT-54"). Yeni normalizasyon T100'u hassas SAYMAMALI.
    #  · 2026-06-22 (DORIT.BATCH dersi): rows_labeled uretilmeli, ham POZISYONEL 'data' sokulmeli.
    r = Q.adt_sql_query(query="SELECT msgnr, text FROM t100 WHERE arbgb = 'ZSD001' AND sprsl = 'T'")
    kontrol("B/GECMIS 2026-07-12 T100 WHERE sorgusu SERBEST kalir",
            r.get("ok") is True and r.get("tables") == ["T100"],
            f"ok={r.get('ok')} tables={r.get('tables')}")
    r = Q.adt_sql_query(query="SELECT COUNT(*) FROM t100")
    kontrol("B/GECMIS 2026-07-12 T100 COUNT sorgusu SERBEST kalir", r.get("ok") is True,
            f"ok={r.get('ok')} code={r.get('code','-')}")
    r = Q.adt_sql_query(query="UPDATE t100 SET text = 'x'")
    kontrol("B/GECMIS 2026-07-12 YAZMA hala REDDEDILIR (ADR 0005-B)",
            r.get("ok") is False and r.get("error") in ("not_select", "write_keyword"),
            f"error={r.get('error')}")
    r = Q.adt_table_read(table="ZSD001_T_BOOKHD")
    veri = r.get("data") or {}
    kontrol("B/GECMIS 2026-06-22 rows_labeled uretilir + pozisyonel 'data' sokulur",
            r.get("ok") is True and "rows_labeled" in veri and "data" not in veri,
            f"anahtarlar={sorted(veri)}")

    # (4) DEV MUAFIYETI KORUNUYOR (kontrol grubu — guard gunluk isi bloklamamali)
    tier("DEV")
    r = Q.adt_table_read(table="KNA1")
    kontrol("B/FP-CAPA DEV tier'da hassas okuma SERBEST (ADR 0011 muafiyeti)",
            r.get("ok") is True, f"ok={r.get('ok')} code={r.get('code','-')}")

    # (5) FAIL-CLOSED: tier cozulemezse hassas hedef yine BLOK (tier_fail_closed ile uyum)
    tier(None)
    kontrol("B/FAIL-CLOSED tier=None + hassas -> BLOK",
            _pii_bloklu(Q.adt_table_read(table="KNA1 AS K")))
    kontrol("B/FAIL-CLOSED tier=None + hassas-DEGIL -> SERBEST (salt-okuma kisitlanmaz)",
            Q.adt_table_read(table="T000").get("ok") is True)

    # (6) ACIK ONAY yolu hala calisiyor (asiri-sikilasma capasi)
    tier("PRD")
    r = Q.adt_table_read(table="KNA1 AS K", acknowledge_risk=True, approval_text="onay")
    kontrol("B/ONAY onayla PII gecer, sekil ayri sebeple reddeder",
            (not _pii_bloklu(r)) and r.get("error") == "gecersiz_tablo_adi",
            f"code={r.get('code','-')} error={r.get('error')}")
    r = Q.adt_sql_query(query="SELECT * FROM KNA1 AS K",
                        acknowledge_risk=True, approval_text="onay")
    kontrol("B/ONAY adt_sql_query onayla GECER", r.get("ok") is True,
            f"ok={r.get('ok')} code={r.get('code','-')}")
    r = Q.adt_sql_query(query="SELECT * FROM KNA1 AS K",
                        acknowledge_risk=True, approval_text="dene bakalim")
    kontrol("B/ONAY muglak ifade YETMEZ", _pii_bloklu(r))


# ═════════════════════════════════════════════════════════════════════════════════
# C) 3. BAGLAM — adt_syntax_check (K-2): FARKLI tool ailesi, FARKLI ADR (0005/0010)
# ═════════════════════════════════════════════════════════════════════════════════
def bolum_c() -> None:
    Q._get_client = lambda: _SahteSqlClient()                # type: ignore[assignment]

    tier("DEV")
    r = Q.adt_syntax_check(name="ZCL_ZSD_TEST", object_type="class")
    kontrol("C/KONTROL DEV + Z obje -> syntax_check CALISIR", r.get("ok") is True,
            f"ok={r.get('ok')} valid={r.get('valid')}")

    tier("PRD")
    r = Q.adt_syntax_check(name="ZCL_ZSD_TEST", object_type="class")
    kontrol("C/K-2 PRD tier -> REDDEDILIR (mutasyon: temiz surumu AKTIVE EDER)",
            r.get("code") == "ADR_0010_TIER", f"code={r.get('code','-')}")

    tier(None)
    r = Q.adt_syntax_check(name="ZCL_ZSD_TEST", object_type="class")
    kontrol("C/K-2 tier COZULEMEDI -> REDDEDILIR (fail-closed)",
            r.get("code") == "ADR_0010_TIER", f"code={r.get('code','-')}")

    tier("DEV")
    r = Q.adt_syntax_check(name="CL_GUI_ALV_GRID", object_type="class")
    kontrol("C/K-2 STANDART obje -> REDDEDILIR (ADR 0005-A)",
            r.get("code") == "ADR_0005_A", f"code={r.get('code','-')}")
    r = Q.adt_syntax_check(name="EZSD000_LOCK", object_type="enqu")
    kontrol("C/FP-CAPA lock objesi (E+Z) MESRU -> gecer", r.get("ok") is True,
            f"ok={r.get('ok')} code={r.get('code','-')}")

    # OZET SATIRI olculur: ajan/model ilk once onu gorur. (Govdede tarihce anlatilirken
    # "read-only" ifadesi ALINTI olarak gecebilir — bu testin ilk surumu tam oraya takildi.)
    dok = (Q.adt_syntax_check.__doc__ or "")
    ozet = (dok.strip().splitlines() or [""])[0]
    kontrol("C/DOKUMAN ozet satiri artik 'read-only' DEMIYOR",
            "read-only" not in ozet.lower() and "YAN ETK" in ozet,
            f"alt katman 'treat as WRITE' diyor; ozet={ozet[:70]!r}")


# ═════════════════════════════════════════════════════════════════════════════════
# D) 3. BAGLAM (2) — adt_lock_check (K-3): kanitsiz olumsuzlama
# ═════════════════════════════════════════════════════════════════════════════════
def bolum_d() -> None:
    def cagir(md_hata=None, kilit=None):
        Q._get_client = lambda: _SahteLockClient(md_hata, kilit)   # type: ignore[assignment]
        return Q.adt_lock_check(name="ZCL_ZSD_TEST", object_type="class")

    r = cagir(kilit={"locked": True, "lock_owner": "BASKA_KULLANICI"})
    kontrol("D/K-3 GERCEKTEN KILITLI -> locked:true (eski surumde ULASILAMAZ daldi)",
            r.get("locked") is True and r.get("lock_owner") == "BASKA_KULLANICI",
            f"locked={r.get('locked')} owner={r.get('lock_owner')}")

    r = cagir(kilit={"locked": False, "lock_owner": None})
    kontrol("D/KONTROL kilitli DEGIL -> locked:false (durust olumsuzlama MUMKUN)",
            r.get("ok") is True and r.get("locked") is False, f"locked={r.get('locked')}")

    r = cagir(kilit=None)
    kontrol("D/K-3 kilit ucu cevapsiz -> locked:null + ok:false ('hayir' DEGIL)",
            r.get("ok") is False and r.get("locked") is None,
            f"ok={r.get('ok')} locked={r.get('locked')} error={r.get('error')}")

    r = cagir(md_hata=RuntimeError("Internal Server Error 500"))
    kontrol("D/K-3 HTTP 500 -> yokluk BEYAN EDILMEZ (exists:false DEGIL)",
            r.get("ok") is False and r.get("exists") is not False
            and r.get("locked") is None,
            f"ok={r.get('ok')} exists={r.get('exists')} locked={r.get('locked')}")

    r = cagir(md_hata=ConnectionError("Max retries exceeded / getaddrinfo failed"))
    kontrol("D/K-3 baglanti kopuk -> unreachable (kilit iddiasi YOK)",
            r.get("ok") is False and r.get("locked") is None,
            f"error={r.get('error')} locked={r.get('locked')}")


def main() -> int:
    bolum_a()
    bolum_b()
    bolum_c()
    bolum_d()
    gecen = sum(1 for _, ok, _ in SONUC if ok)
    for ad, ok, detay in SONUC:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad}" + (f" -> {detay}" if detay else ""))
    print(f"\n{gecen}/{len(SONUC)} OK")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
