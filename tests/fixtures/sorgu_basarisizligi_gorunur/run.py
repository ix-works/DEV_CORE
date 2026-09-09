#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sorgu_basarisizligi_gorunur fixture — `ok:true` + 0 satır SESSİZ FAIL-OPEN'ı.

NEDEN VAR (2026-08-19, lider bizzat düştü — ölçülü vaka)
  `sap_client.run_sql_query()` başarısızlıkta **`None`** döner ve sebebi YALNIZ stdout'a
  basar (`[ERROR] SQL query error: [400] Failed to run query`). `tools/query.py` bu değeri
  `ok:true` + `row_count:0` + `rows:null` olarak döndürüyordu ⇒ çağıran bunu *"TADIR'da 0
  obje"* diye okudu: **kanıt sanılan sahte yeşil**. Yanlış bir araç teşhisi kuruldu ve
  teşhis üç kez taşındı.

  KONTROL GRUBU (canlıda ölçülmüş): kısa `LIKE` filtreli TADIR sorgusu → 3 satır,
  `client_log` BOŞ ✅ · aynı sorgu 15 elemanlı `IN` listesiyle → `ok:true` + 0 satır +
  log'da `[400]` ⛔ ⇒ sebep uzun `IN` listesi. Bu fixture'ın konusu **başarısızlığın
  görünürlüğü**dir; `IN` limiti düzeltilmedi (kapsam dışı).

  SINIF: "üç-değerli doğrulama sözleşmesi" (2026-08-01, `dogrulama_kosamadi` korpusu).
  O süpürge beş yeri düzeltmişti; `run_sql_query`'nin `None`'ı listede YOKTU — bu kalıntı.

DÖRT DEĞİŞMEZ, DÖRT ÇAPA
  (1) YENİ: alt katman `None` → `ok:false` + `error` + sebep `message`'ta   → A1-A5, B1-B3
  (2) ESKİ KORUNDU: başarılı sorgu/okuma, guard'lar, `client_log`, istisna yolu → F1-F9
  (2) olmadan (1) trivial olurdu: "her şeye ok:false de" diyen bir fix de A'yı geçirir.
  (3) ⭐ Q205 (2026-09-09): `adt_syntax_check.valid` ÜÇ-DEĞERLİ                  → G1-G8
  (4) ⭐ Q224 (2026-09-09): `adt_inactive_objects` ÜÇ KOVA + sayı ŞİŞMEZ         → H1-H8

  ⭐ (3) ve (4) AYNI KÖKÜN iki üyesidir — kayıtlar ayrı açıldı, kusur TEK:
  **"ölçülemedi" ile "ölçülmüş olumsuz" AYNI DEĞERE çöküyor.**
    · Q205: `bool(res.get("valid"))` — `bool(None)` = `False` ⇒ *"bakamadım"* → *"kod hatalı"*.
      Kilitli obje (`sap_adt_lib.py:3490-3506`) ve alt-katman istisnası (`sap_client.py:1594`)
      TAM BU ŞEKİLDE `valid:false` üretiyordu; ajan olmayan bir hatayı düzeltmeye oturur.
    · Q224: `tadir_deleted is not True` — `None` (ölçülemedi) `False` (ölçüldü: silinmemiş)
      ile aynı kovaya düşüyordu ⇒ `count` sahte-pozitif şişiyor, `warning` basılıyor ama
      **sayı düzeltilmiyordu** (fail-open: uyarıyı okumayan çağıran yanlış sayıyı alır).
  ⛔ Bu yüzden ikisi TEK ilkeyle düzeltildi ve ÇAPALARI BİRLİKTE durur: biri kaldırılırsa
  sınıf yarım kapanır. Emsal (aynı dosyada, ÖNCEDEN vardı): `adt_lock_check` → `ok:false` +
  `locked:null`; `adt_atc_check` → `ok:false` + `finding_count_unverified`.

⛔ SİLİNMEZ FP ÇAPALARI: G1/G2 (gerçek sözdizimi hatası HÂLÂ `valid:false`; temiz HÂLÂ
  `valid:true`) ve H1/H4/H6 (silinmiş obje HÂLÂ eleniyor; ölçülmüş sayı HÂLÂ dönüyor).
  Bunlar olmadan (3)+(4) trivial olurdu: "her şeye null de" diyen bir fix de geçerdi ve
  kapı KÖR kalırdı.

KULLANIM
  python tests/fixtures/sorgu_basarisizligi_gorunur/run.py
  python tests/fixtures/sorgu_basarisizligi_gorunur/run.py --modul <query.py yolu>   # MUTASYON
  (mutasyon tabani PINLI SHA olmali:
   `git show ab37296:mcp_servers/sap_adt/tools/query.py > <scratch>/eski.py`)
  ⛔ `origin/main` VERME: merge sonrasi o ref "fix SONRASI"na kayar, korpus ayirt
     etmiyormus gibi gorunur (hareketli ref = sessiz bosalma; infra-changelog 2026-08-10).
     Kosucu tabani OZ-DENETLER: modulde `_cagri_basarisiz` VARSA exit 2 + [DOGRULANAMADI].

  ⭐ Q205/Q224 icin CERRAHI (bellek-ici) mutasyon kipleri — `--modul` PINLI SHA'si bu iki
  fix'ten ONCEsine denk geldigi icin o yol IKISINI BIRDEN soker (kaba). Her degismezin
  KENDI kolu olsun diye:
  python tests/fixtures/sorgu_basarisizligi_gorunur/run.py --mutasyon-q205
  python tests/fixtures/sorgu_basarisizligi_gorunur/run.py --mutasyon-q224-kova
  python tests/fixtures/sorgu_basarisizligi_gorunur/run.py --mutasyon-q224-isaret
  (mutasyon BELLEKTE kurulur; dosyaya/git'e DOKUNMAZ -> komsu korpusu kirletmez)
"""
from __future__ import annotations

import importlib.util
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

# ── MCP SDK KÖPRÜSÜ (test harness'ı, üretim kodu DEĞİL) ──────────────────────────
# `query.py` -> `_app.py` -> `from mcp.server.fastmcp import FastMCP`. Ölçülen şey tool
# KATMANININ ÇALIŞMA-ZAMANI DAVRANIŞI → import şart. CI'da SDK yoksa asgari sahte modül
# kurulur (gerçek SDK varsa DOKUNULMAZ). Desen: tests/fixtures/veri_yetki_guardlari.
try:  # pragma: no cover - ortam koşullu
    import mcp.server.fastmcp  # type: ignore  # noqa: F401
except Exception:
    import types as _t
    _mcp, _srv, _fast = (_t.ModuleType("mcp"), _t.ModuleType("mcp.server"),
                         _t.ModuleType("mcp.server.fastmcp"))

    class _FastMCP:  # noqa: D401
        def __init__(self, *a, **k):
            pass

        def tool(self, *a, **k):
            def _d(fn):
                return fn
            return _d

    _fast.FastMCP = _FastMCP           # type: ignore[attr-defined]
    _srv.fastmcp = _fast               # type: ignore[attr-defined]
    _mcp.server = _srv                 # type: ignore[attr-defined]
    sys.modules.setdefault("mcp", _mcp)
    sys.modules.setdefault("mcp.server", _srv)
    sys.modules.setdefault("mcp.server.fastmcp", _fast)

try:
    from mcp_servers.sap_adt import _conn as CONN
    from sap_adt_lib import SAPADTError  # type: ignore
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"[fixture-hatasi] modul yuklenemedi (sessiz gecme YOK): {exc}")

HATA_LOG = "[ERROR] SQL query error: [400] Failed to run query"
SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul), detay))


class _Basarisiz:
    """Alt katmanın GERÇEK başarısızlık şekli: stdout'a basar, `None` döner."""

    def run_sql_query(self, q, max_rows=100):
        print(HATA_LOG)
        return None


class _Sessiz:
    """Sebep bile basmayan başarısızlık (log boş) — mesaj yine de anlamlı olmalı."""

    def run_sql_query(self, q, max_rows=100):
        return None


class _Basarili:
    def run_sql_query(self, q, max_rows=100):
        return {"columns": ["PGMID", "OBJECT"], "data": [["R3TR", "CLAS"]],
                "executedQueryString": q}

    def syntax_check(self, name, object_type="class"):
        return {"valid": False, "error": "baglanti yok"}


class _Firlatan:
    def run_sql_query(self, q, max_rows=100):
        raise SAPADTError("SAP 503", status_code=503)


# ══ Q205 — `syntax_check` yanit SEKILLERI (hepsi KAYNAKTA yazili, uydurma DEGIL) ══
class _Sozdizimi:
    """Alt katmanin verdigi yaniti aynen dondurur (sekil ne ise o olculur)."""

    def __init__(self, yanit):
        self._yanit = yanit

    def syntax_check(self, name, object_type="class"):
        return self._yanit


# GERCEK sozdizimi hatasi: SAP'nin kendi `msg` kaydi (type='E') — sap_adt_lib.py:3568-3580
SAP_HATASI = {"valid": False, "check_executed": True, "activation_executed": False,
              "errors": [{"type": "E", "message": "Field 'LV_X' is unknown",
                          "object": "ZCL_SD001_ORNEK", "line": "42", "href": ""}],
              "warnings": []}
# Temiz: sap_adt_lib.py:3585-3591
SAP_TEMIZ = {"valid": True, "check_executed": True, "errors": [], "warnings": []}
# KILITLI (HTTP 403): sozdizimi HIC kontrol edilmedi — sap_adt_lib.py:3490-3506
SAP_KILITLI = {"valid": False, "check_executed": False, "activation_executed": False,
               "locked": True, "lock_user": "BASKA_KULLANICI",
               "errors": [{"message": "Object locked by BASKA_KULLANICI."}], "warnings": []}
# Alt katman ISTISNA yakaladi: sap_client.py:1594
SAP_ISTISNA = {"valid": False, "error": "baglanti yok"}
# Yanit XML'i AYRISTIRILAMADI: sap_adt_lib.py:3596-3598 (yerel mesaj, `type` YOK)
SAP_PARSE = {"valid": False, "check_executed": False, "errors": [
    {"message": "Could not parse syntax check response: no element found"}], "warnings": []}


# ══ Q224 — inaktif worklist + TADIR capraz kontrolu ══════════════════════════════
_IOC = ('xmlns:ioc="http://www.sap.com/abapxml/inactiveCtsObjects" '
        'xmlns:adtcore="http://www.sap.com/adt/core"')


def worklist_xml(*adlar: str) -> str:
    govde = "".join(
        '<ioc:entry><ioc:object ioc:deleted="false" ioc:user="TESTUSER">'
        '<ioc:ref adtcore:uri="/sap/bc/adt/oo/classes/%s" adtcore:type="CLAS/OC" '
        'adtcore:name="%s"/></ioc:object></ioc:entry>' % (a.lower().replace(" ", "_"), a)
        for a in adlar)
    return ('<?xml version="1.0" encoding="UTF-8"?><ioc:inactiveObjects %s>%s'
            '</ioc:inactiveObjects>' % (_IOC, govde))


class _Yanit:
    def __init__(self, kod, metin):
        self.status_code, self.text = kod, metin


class _WlSession:
    def __init__(self, xml, kod=200):
        self._y = _Yanit(kod, xml)
        self.istenen: list[str] = []

    def get(self, url, **kw):
        self.istenen.append(url)
        return self._y


class _WlAdt:
    def __init__(self, s):
        self.url = "https://sap.example.test:44300"
        self.session = s


class _Worklist:
    """adt_inactive_objects'in HTTP ucunu sahteler; SAP GEREKTIRMEZ."""

    def __init__(self, xml, kod=200):
        self.session = _WlSession(xml, kod)
        self.adt_client = _WlAdt(self.session)


def tadir_yaniti(*silinmis_adlar: str):
    """`adt_sql_query` yerine gecer: verilen adlari DELFLAG='X' olarak dondurur."""
    def _f(query, row_limit=100, **kw):
        return {"ok": True, "row_count": len(silinmis_adlar),
                "rows": [{"OBJ_NAME": a, "OBJECT": "CLAS", "DELFLAG": "X"}
                         for a in silinmis_adlar]}
    return _f


def tadir_dustu(query, row_limit=100, **kw):
    """Olculmus vaka: uzun `IN` listesi -> 400 (bkz. bu dosyanin ust basligi)."""
    return {"ok": False, "error": "sorgu_kosmadi",
            "message": "ADT data preview sorgusu KOSMADI — [ERROR] SQL query error: [400]"}


def tadir_patladi(query, row_limit=100, **kw):
    raise RuntimeError("baglanti koptu")


def modul_yukle(yol: Path | None):
    if yol is None:
        from mcp_servers.sap_adt.tools import query as Q  # type: ignore
        return Q
    spec = importlib.util.spec_from_file_location("query_test_surumu", str(yol))
    m = importlib.util.module_from_spec(spec)
    sys.modules["query_test_surumu"] = m
    spec.loader.exec_module(m)
    return m


# ── CERRAHI MUTASYONLAR (bellek-ici; fix'i BIREBIR fix-oncesi haline dondurur) ────
# ⛔ Her DEGISMEZ kendi kolunu alir: tek kol iki katmani birden sokerse "hangi capa
#   olcuyor" ayirt edilemez (ders: mutasyon katman sayisi kadar capa keser).
_GECERLI_KIP = frozenset({"--mutasyon-q205", "--mutasyon-q224-kova",
                          "--mutasyon-q224-isaret"})


def _eski_gecerlilik(res):
    """Q205 ONCESI: `bool(res.get("valid")) if isinstance(res, dict) else None`."""
    return (bool(res.get("valid")) if isinstance(res, dict) else None), None


def _eski_kovalar(out):
    """Q224 ONCESI: `is not True` -> `None` ile `False` AYNI kovada."""
    return ([o for o in out if o.get("tadir_deleted") is not True],
            [o for o in out if o.get("tadir_deleted") is True],
            [])


def _eski_isaretle(out, sorulan, silinmis):
    """Q224 ONCESI: sorguya girmemis ad da 'olculdu' damgasi aliyordu."""
    for o in out:
        tadir_obj = (str(o.get("type", "")).split("/")[0] or "").strip()
        o["tadir_deleted"] = (o.get("name", ""), tadir_obj) in silinmis


_MUT_KOL = {
    "--mutasyon-q205": ("_gecerlilik", _eski_gecerlilik),
    "--mutasyon-q224-kova": ("_tadir_kovalari", _eski_kovalar),
    "--mutasyon-q224-isaret": ("_tadir_isaretle", _eski_isaretle),
}


def main(modul_yolu: str | None = None, mutasyon: str | None = None) -> int:
    if modul_yolu and not Path(modul_yolu).is_file():
        sys.stderr.write("OLCULEMEDI: modul yok: %s\n" % modul_yolu)
        return 2
    Q = modul_yukle(Path(modul_yolu) if modul_yolu else None)
    CONN.get_active_tier = lambda: "DEV"          # type: ignore[assignment]
    print("modul:", getattr(Q, "__file__", "?"))
    if mutasyon:
        ad, eski = _MUT_KOL[mutasyon]
        if not hasattr(Q, ad):
            # "KURULAMADI" != "KACTI": mutasyon kurulamadiysa SAYI RAPORLAMA.
            sys.stderr.write("[DOGRULANAMADI] mutasyon kurulamadi: modulde `%s` YOK "
                             "(%s) -> hicbir sayi raporlanmadi.\n" % (ad, mutasyon))
            return 3
        setattr(Q, ad, eski)
        print("mutasyon:", mutasyon, "->", ad)
    # TABAN OZ-DENETIMI: mutasyon modunda taban GERCEKTEN kusurlu (fix'siz) olmali.
    if modul_yolu and hasattr(Q, "_cagri_basarisiz"):
        sys.stderr.write("[DOGRULANAMADI] mutasyon tabani fix'i ZATEN tasiyor "
                         "(_cagri_basarisiz var): %s -> hicbir sayi raporlanmadi. "
                         "Pinli SHA ver.\n" % modul_yolu)
        return 2

    # ═══ A) adt_sql_query — ölçülmüş vaka ════════════════════════════════════════
    Q._get_client = lambda: _Basarisiz()          # type: ignore[assignment]
    r = Q.adt_sql_query(query="SELECT pgmid FROM tadir WHERE obj_name LIKE 'ZSD001%'")
    kontrol("A1 sorgu KOSMADI -> ok:false", r.get("ok") is False,
            "ok=%r row_count=%r" % (r.get("ok"), r.get("row_count")))
    kontrol("A2 error alani DOLU", bool(r.get("error")), "error=%r" % r.get("error"))
    kontrol("A3 sebep message'ta gorunur", "[400]" in (r.get("message") or ""),
            (r.get("message") or "")[:70])
    kontrol("A4 client_log KALDIRILMADI (kapsam capasi)",
            HATA_LOG in (r.get("client_log") or ""),
            "log=%r" % (r.get("client_log") or "")[:40])

    Q._get_client = lambda: _Sessiz()             # type: ignore[assignment]
    r = Q.adt_sql_query(query="SELECT pgmid FROM tadir")
    kontrol("A5 log BOS olsa da ok:false + anlamli mesaj",
            r.get("ok") is False and len(r.get("message") or "") > 20,
            (r.get("message") or "")[:70])

    # ═══ B) adt_table_read — KARDES cagri yeri (ayni alt katman) ═════════════════
    Q._get_client = lambda: _Basarisiz()          # type: ignore[assignment]
    r = Q.adt_table_read(table="TADIR", row_limit=5)
    kontrol("B1 tablo okuma KOSMADI -> ok:false", r.get("ok") is False,
            "ok=%r data=%r" % (r.get("ok"), r.get("data")))
    kontrol("B2 error alani DOLU", bool(r.get("error")), "error=%r" % r.get("error"))
    kontrol("B3 sebep message'ta gorunur", "[400]" in (r.get("message") or ""),
            (r.get("message") or "")[:70])

    # ═══ F) FP ÇAPALARI — eski davranış BİT DÜZEYİNDE korunmalı ══════════════════
    Q._get_client = lambda: _Basarili()           # type: ignore[assignment]
    r = Q.adt_sql_query(query="SELECT pgmid, object FROM tadir")
    kontrol("F1 basarili sorgu HALA ok:true + satirlar",
            r.get("ok") is True and r.get("row_count") == 1
            and r.get("rows") == [{"PGMID": "R3TR", "OBJECT": "CLAS"}],
            "ok=%r n=%r" % (r.get("ok"), r.get("row_count")))
    kontrol("F2 basarida error alani YOK", "error" not in r, str(list(r.keys())))
    r = Q.adt_table_read(table="TADIR", row_limit=5)
    kontrol("F3 basarili okuma HALA ok:true + rows_labeled",
            r.get("ok") is True
            and r["data"].get("rows_labeled") == [{"PGMID": "R3TR", "OBJECT": "CLAS"}],
            "ok=%r" % r.get("ok"))
    kontrol("F4 pozisyonel 'data' HALA sokuluyor (2026-06-22 capasi)",
            "data" not in r["data"], str(sorted(r["data"].keys())))
    # ⚠ Sıra anlamlı: SELECT-ile-başlamayan sorgu ZATEN `not_select`e düşer (ilk ölçümde
    # `UPDATE ...` verildi ve `not_select` döndü) — yazma-keyword çapası SELECT ile
    # BAŞLAYIP içinde yazma barındıran şekli sınamalı (enjeksiyon şekli).
    r = Q.adt_sql_query(query="SELECT pgmid FROM tadir; DROP TABLE t000")
    kontrol("F5 yazma-keyword guard'i HALA reddediyor", r.get("error") == "write_keyword",
            "error=%r" % r.get("error"))
    r = Q.adt_sql_query(query="DESCRIBE tadir")
    kontrol("F6 SELECT-degil guard'i HALA reddediyor", r.get("error") == "not_select",
            "error=%r" % r.get("error"))
    r = Q.adt_table_read(table="TADIR AS T")
    kontrol("F7 sekil guard'i HALA reddediyor", r.get("error") == "gecersiz_tablo_adi",
            "error=%r" % r.get("error"))
    # ⚠ F8'in ESKI yuku `{"valid": False, "error": "baglanti yok"}` idi — yani capanin
    # KENDISI Q205 kusurunun bir ornegiydi ("baglanti yok" = OLCULEMEDI, "kod hatali" degil).
    # 2026-09-09'da yuk GERCEK bir SAP bulgusuyla degistirildi: capanin AMACI (kardes tool
    # hala ok:true + BOOLEAN hukum veriyor) korundu, YANLIS anlami dusuruldu. Eski yuk
    # artik G4'te ve dogru yanit `valid:null` bekleniyor.
    Q._get_client = lambda: _Sozdizimi(SAP_HATASI)   # type: ignore[assignment]
    r = Q.adt_syntax_check(name="ZCL_ZSD001_TEST", object_type="class")
    kontrol("F8 3.BAGLAM kardes tool DEGISMEDI (gercek bulgu -> valid:false, ok:true)",
            r.get("ok") is True and r.get("valid") is False,
            "ok=%r valid=%r" % (r.get("ok"), r.get("valid")))
    Q._get_client = lambda: _Firlatan()           # type: ignore[assignment]
    r = Q.adt_sql_query(query="SELECT pgmid FROM tadir")
    kontrol("F9 istisna yolu DEGISMEDI (ok:false + sap_error)",
            r.get("ok") is False and r.get("error") == "sap_error",
            "error=%r" % r.get("error"))

    # ═══ G) Q205 — `adt_syntax_check.valid` UC-DEGERLI ═══════════════════════════
    def sozdizimi(yanit):
        Q._get_client = lambda: _Sozdizimi(yanit)  # type: ignore[assignment]
        return Q.adt_syntax_check(name="ZCL_ZSD001_TEST", object_type="class")

    # ── FP CAPALARI [SILINMEZ]: olculmus vakalar BOZULMAZ ──
    r = sozdizimi(SAP_HATASI)
    kontrol("G1 ⛔CAPA GERCEK sozdizimi hatasi HALA olculmus-olumsuz (ok:true, valid:false)",
            r.get("ok") is True and r.get("valid") is False
            and r.get("errors") == SAP_HATASI["errors"] and "valid_reason" not in r,
            "ok=%r valid=%r n_err=%d" % (r.get("ok"), r.get("valid"), len(r.get("errors") or [])))
    r = sozdizimi(SAP_TEMIZ)
    kontrol("G2 ⛔CAPA temiz obje HALA valid:true (asiri-siki DEGIL)",
            r.get("ok") is True and r.get("valid") is True and "error" not in r,
            "ok=%r valid=%r" % (r.get("ok"), r.get("valid")))

    # ── UCUNCU DEGER: "bakamadim" != "hayir" ──
    r = sozdizimi(SAP_KILITLI)
    kontrol("G3 ⭐KILITLI obje -> valid:null + ok:false ('kod hatali' DEMEZ)",
            r.get("valid") is None and r.get("ok") is False
            and r.get("error") == "sozdizimi_belirsiz"
            and "KILITLI" in (r.get("valid_reason") or "").replace("İ", "I")
            and "ANLAMINA GELMEZ" in (r.get("message") or ""),
            "valid=%r reason=%r" % (r.get("valid"), (r.get("valid_reason") or "")[:48]))
    r = sozdizimi(SAP_ISTISNA)
    kontrol("G4 ⭐alt katman istisnasi -> valid:null (F8'in ESKI yuku; sebep gorunur)",
            r.get("valid") is None and r.get("ok") is False
            and "baglanti yok" in (r.get("valid_reason") or ""),
            "valid=%r reason=%r" % (r.get("valid"), (r.get("valid_reason") or "")[:48]))
    r = sozdizimi(SAP_PARSE)
    kontrol("G5 ⭐yanit ayristirilamadi (yerel mesaj, `type` YOK) -> valid:null",
            r.get("valid") is None and r.get("ok") is False,
            "valid=%r reason=%r" % (r.get("valid"), (r.get("valid_reason") or "")[:48]))
    r = sozdizimi({"errors": [], "warnings": []})
    kontrol("G6 ⭐3.BAGLAM bulgu listesi BOS + `valid` anahtari YOK -> valid:null (False DEGIL)",
            r.get("valid") is None and "URETMEDI" in (r.get("valid_reason") or "")
            .replace("Ü", "U").replace("İ", "I"),
            "valid=%r reason=%r" % (r.get("valid"), (r.get("valid_reason") or "")[:48]))
    r = sozdizimi({"valid": False, "errors": [], "warnings": []})
    kontrol("G7 ⭐valid:false ama TEK bulgu YOK -> kanit yok, valid:null",
            r.get("valid") is None and r.get("ok") is False,
            "valid=%r reason=%r" % (r.get("valid"), (r.get("valid_reason") or "")[:48]))
    r = sozdizimi(None)
    kontrol("G8 alt katman None dondu -> valid:null + 'KOSMADI' sebebi",
            r.get("valid") is None and r.get("ok") is False
            and "KOSMADI" in (r.get("valid_reason") or "").replace("Ş", "S"),
            "valid=%r reason=%r" % (r.get("valid"), (r.get("valid_reason") or "")[:48]))

    # ═══ H) Q224 — `adt_inactive_objects` UC KOVA, sayi SISMEZ ═══════════════════
    A, B = "ZCL_SD001_ORNEK", "ZIF_SD001_ORNEK"
    _sql_yedek = Q.adt_sql_query

    def inaktif(adlar, sql):
        Q._get_client = lambda: _Worklist(worklist_xml(*adlar))  # type: ignore[assignment]
        Q.adt_sql_query = sql                                    # type: ignore[assignment]
        try:
            return Q.adt_inactive_objects()
        finally:
            Q.adt_sql_query = _sql_yedek                         # type: ignore[assignment]

    # ── 1. BAGLAM (REGRESYON) [SILINMEZ]: TADIR KOSUYOR + obje silinmis ──
    r = inaktif([A, B], tadir_yaniti(A))
    kontrol("H1 ⛔CAPA TADIR kostu + A silinmis -> count=1 (silinmis ELENDI, regresyon yok)",
            r.get("ok") is True and r.get("count") == 1
            and r.get("count_verified") is True and r.get("stale_deleted_count") == 1
            and [o["name"] for o in r.get("inactive_objects") or []] == [B],
            "ok=%r count=%r stale=%r" % (r.get("ok"), r.get("count"),
                                         r.get("stale_deleted_count")))
    # ── 2. BAGLAM: TADIR COKUYOR -> sayi SISMEMELI, sonuc AYIRT EDILEBILIR ──
    r = inaktif([A, B], tadir_dustu)
    kontrol("H2 ⭐TADIR sorgusu DUSTU -> ok:false + `count` anahtari HIC BASILMADI",
            r.get("ok") is False and r.get("error") == "tadir_kontrolu_belirsiz"
            and "count" not in r and "inactive_objects" not in r,
            "ok=%r anahtarlar=%s" % (r.get("ok"), sorted(r.keys())))
    kontrol("H2b ⭐sahte-pozitif SISME YOK: dogrulanmis canli 0, olculemeyen 2",
            r.get("confirmed_live_count") == 0 and r.get("unverified_count") == 2
            and r.get("count_verified") is False
            and all(o.get("tadir_deleted") is None for o in r.get("unverified") or []),
            "canli=%r olculemedi=%r" % (r.get("confirmed_live_count"),
                                        r.get("unverified_count")))
    kontrol("H2c ⭐belirsizlik ARALIKLA bildiriliyor + tadir_check sebebi tasiyor",
            "EN AZ 0" in (r.get("message") or "") and "EN COK 2" in
            (r.get("message") or "").replace("Ç", "C")
            and "[400]" in (r.get("tadir_check") or ""),
            "msg=%r" % (r.get("message") or "")[:70])
    # ── TADIR ISTISNA firlatti (ayni sinif, farkli yol) ──
    r = inaktif([A, B], tadir_patladi)
    kontrol("H3 ⭐TADIR istisna firlatti -> ayni belirsiz-sonuc sozlesmesi",
            r.get("ok") is False and r.get("unverified_count") == 2 and "count" not in r,
            "ok=%r olculemedi=%r" % (r.get("ok"), r.get("unverified_count")))
    # ── FP CAPALARI [SILINMEZ]: olculebilen her sey OLCULMEYE DEVAM EDIYOR ──
    r = inaktif([], tadir_yaniti())
    kontrol("H4 ⛔CAPA worklist BOS -> ok:true + count=0 (bos liste HALA temiz cevap)",
            r.get("ok") is True and r.get("count") == 0 and r.get("count_verified") is True,
            "ok=%r count=%r" % (r.get("ok"), r.get("count")))
    r = inaktif([A, B], tadir_yaniti())
    kontrol("H5 ⛔CAPA hicbiri silinmemis -> count=2 (fix 'her seye null de' DEMIYOR)",
            r.get("ok") is True and r.get("count") == 2
            and r.get("stale_deleted_count") == 0,
            "ok=%r count=%r" % (r.get("ok"), r.get("count")))
    # ── SESSIZ KARDES: ad suzgeci eledi -> girdi SORULMADI, "olculdu" damgasi YASAK ──
    r = inaktif([A, "ZCL SD001 BOSLUK"], tadir_yaniti())
    kontrol("H6 ⭐ad suzgecinin eledigi girdi 'olculdu: silinmemis' SAYILMIYOR",
            r.get("ok") is False and r.get("confirmed_live_count") == 1
            and r.get("unverified_count") == 1
            and [o["name"] for o in r.get("unverified") or []] == ["ZCL SD001 BOSLUK"],
            "canli=%r olculemedi=%r" % (r.get("confirmed_live_count"),
                                        r.get("unverified_count")))
    # ── HICBIR ad sorgulanabilir degil -> capraz kontrol HIC kosmadi ──
    r = inaktif(["ZCL SD001 BOSLUK"], tadir_yaniti())
    kontrol("H7 ⭐hicbir ad sorgulanamadi -> ok:false + sebep bildirildi (sessiz gecme YOK)",
            r.get("ok") is False and r.get("unverified_count") == 1
            and "ad suzgeci" in (r.get("tadir_check") or "").replace("ü", "u"),
            "ok=%r tadir_check=%r" % (r.get("ok"), (r.get("tadir_check") or "")[:60]))
    # ── 3. BAGLAM: HTTP ucu 200 DEGIL -> eski dal DEGISMEDI ──
    Q._get_client = lambda: _Worklist("bos", 500)      # type: ignore[assignment]
    r = Q.adt_inactive_objects()
    kontrol("H8 3.BAGLAM worklist ucu 500 -> eski http_500 dali DEGISMEDI",
            r.get("ok") is False and r.get("error") == "http_500",
            "ok=%r error=%r" % (r.get("ok"), r.get("error")))

    hata = 0
    for ad, ok, detay in SONUC:
        hata += 0 if ok else 1
        print("[%s] %-52s %s" % ("ok" if ok else "FAIL", ad, detay))
    # ⚠ Kosucu ozeti bu bicimden ayristirir (run_fixture_tests: r"^\s*\d+/\d+ OK")
    print("%d/%d OK" % (len(SONUC) - hata, len(SONUC)))
    print("SONUC: %d/%d gecti" % (len(SONUC) - hata, len(SONUC)))
    return 1 if hata else 0


if __name__ == "__main__":
    arg = None
    if "--modul" in sys.argv:
        arg = sys.argv[sys.argv.index("--modul") + 1]
    kip = None
    for _a in sys.argv[1:]:
        if _a.startswith("--mutasyon"):
            if _a not in _GECERLI_KIP:
                # KIP-RED: bilinmeyen kipte SESSIZ exit 0 verme (exit 0 iki anlamli olurdu).
                print("[KULLANIM] bilinmeyen mutasyon kipi: %s · gecerli kipler: %s"
                      % (_a, ", ".join(sorted(_GECERLI_KIP))))
                sys.exit(3)
            kip = _a
    sys.exit(main(arg, kip))
