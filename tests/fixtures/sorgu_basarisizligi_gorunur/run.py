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

İKİ DEĞİŞMEZ, İKİ ÇAPA
  (1) YENİ: alt katman `None` → `ok:false` + `error` + sebep `message`'ta   → A1-A5, B1-B3
  (2) ESKİ KORUNDU: başarılı sorgu/okuma, guard'lar, `client_log`, istisna yolu → F1-F9
  (2) olmadan (1) trivial olurdu: "her şeye ok:false de" diyen bir fix de A'yı geçirir.

KULLANIM
  python tests/fixtures/sorgu_basarisizligi_gorunur/run.py
  python tests/fixtures/sorgu_basarisizligi_gorunur/run.py --modul <query.py yolu>   # MUTASYON
  (mutasyon tabani PINLI SHA olmali:
   `git show ab37296:mcp_servers/sap_adt/tools/query.py > <scratch>/eski.py`)
  ⛔ `origin/main` VERME: merge sonrasi o ref "fix SONRASI"na kayar, korpus ayirt
     etmiyormus gibi gorunur (hareketli ref = sessiz bosalma; infra-changelog 2026-08-10).
     Kosucu tabani OZ-DENETLER: modulde `_cagri_basarisiz` VARSA exit 2 + [DOGRULANAMADI].
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


def modul_yukle(yol: Path | None):
    if yol is None:
        from mcp_servers.sap_adt.tools import query as Q  # type: ignore
        return Q
    spec = importlib.util.spec_from_file_location("query_test_surumu", str(yol))
    m = importlib.util.module_from_spec(spec)
    sys.modules["query_test_surumu"] = m
    spec.loader.exec_module(m)
    return m


def main(modul_yolu: str | None = None) -> int:
    if modul_yolu and not Path(modul_yolu).is_file():
        sys.stderr.write("OLCULEMEDI: modul yok: %s\n" % modul_yolu)
        return 2
    Q = modul_yukle(Path(modul_yolu) if modul_yolu else None)
    CONN.get_active_tier = lambda: "DEV"          # type: ignore[assignment]
    print("modul:", getattr(Q, "__file__", "?"))
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
    r = Q.adt_syntax_check(name="ZCL_ZSD001_TEST", object_type="class")
    kontrol("F8 3.BAGLAM kardes tool DEGISMEDI (valid:false, ok:true)",
            r.get("ok") is True and r.get("valid") is False,
            "ok=%r valid=%r" % (r.get("ok"), r.get("valid")))
    Q._get_client = lambda: _Firlatan()           # type: ignore[assignment]
    r = Q.adt_sql_query(query="SELECT pgmid FROM tadir")
    kontrol("F9 istisna yolu DEGISMEDI (ok:false + sap_error)",
            r.get("ok") is False and r.get("error") == "sap_error",
            "error=%r" % r.get("error"))

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
    sys.exit(main(arg))
