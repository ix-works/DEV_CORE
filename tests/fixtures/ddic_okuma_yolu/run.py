#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ddic_okuma_yolu fixture — DDIC okuma-yolu: `/source/main` VAR mi YOK mu (tip basina).

NEDEN VAR (2026-08-09):
`adt_get` bes DDIC tipini (dataelement/domain/table/structure/tabletype) TEK kume
halinde XML-okuyucusuna yonlendiriyordu. Ikisi icin bu YANLIS: `table` ve `structure`
ADT'de GERCEK bir `/source/main` DDL ucu tasir (canli olculdu; Z objelerde de STANDART
objelerde de HTTP 200 + duz DDL). Sonuc: `adt_get(<TABLO>, "table")` DDL yerine
`<blue:blueSource>` XML zarfi donduruyordu.

⚠ ASIL ZARAR IKINCI TUKETICIDE: `scripts/sap_sync_pull.py` AYNI kurali ELLE KOPYALANMIS
bagimsiz bir literal olarak tasiyordu ve `write_repo_from_live()` XML->DDL ayiklamasi
YAPMAZ, HAM yazar. Yani tablo/struct pull'u repo'daki DDL dosyasinin uzerine XML zarfi
yazacakti (olculen vaka: canli "1 satir" sanildi, FIX-C shrink korumasi devreye girdi;
`--force` verilseydi 32 satirlik dosya XML copuyle EZILECEKTI).

BU FIXTURE'IN OLCTUGU DEGISMEZLER:
  1. table/structure  -> `/source/main` ucundan DUZ DDL (URL de dogrulanir).
  2. dtel/domain/ttyp -> XML yolu KORUNUR ve `/source/main` HIC ISTENMEZ.  [REGRESYON CAPASI]
  3. Iki tuketici (adt_get + sap_sync_pull) AYNI karari verir (ayrisma bu kusurun koku).
  4. Kanit-zinciri: 404 -> exists:false AMA log'da 404 KANITI var · 500 -> yokluk
     BEYAN EDILMEZ (ok:false) · 200-bos-govde -> `source_empty` + uyari (sessiz bosluk yok).
  5. TEK KAYNAK: iki tuketicide de YEREL DDIC tip-literali YOK (AST capasi).

⛔ SILINMEZ CAPALAR: (2) ve (5). (2) kaldirilirsa fix asiri-genellesir ve dtel/domain/
tabletype `/source/main`e yonlenip 404 alir -> obje YANLISLIKLA "yok" gorunur (2026-06-16'da
kapatilan sinifin geri gelmesi). (5) kaldirilirsa iki kopya yeniden ayrisabilir.

SAP GEREKTIRMEZ: HTTP katmani ve DDIC okuyucusu sahtelenir; olculen sey YONLENDIRME.
"""
from __future__ import annotations

import ast
import os
import sys
import tempfile
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

# Yan-etkiler (tazelik damgasi vb.) GERCEK projeye degil gecici koke yazilsin.
_TMP = tempfile.mkdtemp(prefix="ddic_okuma_yolu_")
os.environ["CLAUDE_PROJECT_DIR"] = _TMP
# Asgari profil: yoksa MCP katmani fail-closed davranip her tool icin "GIZLENDI"
# uyarisi basar (gurultu; testin olctugu sey bu DEGIL). Dogrudan cagri etkilenmez.
Path(_TMP, "project.yaml").write_text(
    "sap_profile: s4_private\nrelease: '2025'\nsource_root: SOURCE_CODES\n",
    encoding="utf-8",
)

# ── MCP SDK KOPRUSU (test-harness'i; FastMCP test kapsaminda DEGIL) ──────────────
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
    from mcp_servers.sap_adt.tools import atom
except Exception as exc:                                     # pragma: no cover
    raise SystemExit(f"[fixture-hatasi] atom yuklenemedi (sessiz gecme YOK): {exc}")


DDL_GOVDE = (
    "@EndUserText.label : 'Test'\n"
    "@AbapCatalog.enhancement.category : #NOT_EXTENSIBLE\n"
    "define table ztest_t_x {\n  key mandt : mandt not null;\n}\n"
)
XML_GOVDE = '<?xml version="1.0" encoding="utf-8"?><blue:blueSource/>'


class _SahteYanit:
    def __init__(self, kod, metin):
        self.status_code = kod
        self.text = metin


class _SahteSession:
    """`/source/main` GET'lerini KAYDEDER; kodu/govdeyi disaridan alir."""

    def __init__(self, kod=200, govde=DDL_GOVDE):
        self.kod, self.govde = kod, govde
        self.istenen: list[str] = []

    def get(self, url, **kw):
        self.istenen.append(url)
        return _SahteYanit(self.kod, self.govde)


class _SahteAdt:
    def __init__(self, session):
        self.url = "https://sap.example.test:44300"
        self.session = session


class _SahteClient:
    """XML yolu (`get_ddic_object`) ve source yolu (`session.get`) AYRI kaydedilir."""

    def __init__(self, kod=200, govde=DDL_GOVDE):
        self.session = _SahteSession(kod, govde)
        self.adt_client = _SahteAdt(self.session)
        self.xml_cagrilari: list[tuple] = []

    def get_ddic_object(self, object_type, name):
        self.xml_cagrilari.append((object_type, name))
        return XML_GOVDE

    # adt_get'in genel (source-based) yolu buraya duser — DDIC'te CAGRILMAMALI
    def download_object(self, name, object_type="class", save_local=True):
        raise AssertionError(f"genel yola dusuldu: {name}/{object_type}")

    def get_object_metadata(self, name, object_type="class"):
        raise AssertionError(f"genel yola dusuldu (metadata): {name}/{object_type}")


def _adt_get(typ, name, kod=200, govde=DDL_GOVDE):
    """adt_get'i sahte client ile kosar; COKERSE olcume cevir (mutasyon-dostu)."""
    c = _SahteClient(kod, govde)
    atom._get_client = lambda _c=c: _c
    atom._record_active_binding = lambda _c=None: None
    try:
        r = atom.adt_get(name=name, object_type=typ, include_source=True)
    except Exception as exc:                                  # cokme != FAIL, OLC
        r = {"ok": None, "_exc": f"{type(exc).__name__}: {exc}"}
    return r, c


def _sekil(src):
    if not isinstance(src, str) or not src:
        return "YOK"
    return "XML" if src.lstrip().startswith("<") else "DDL"


def _sabit_adlari(rel: str) -> set:
    """Modulun MODUL-DUZEYI atama adlari (AST; import/yan-etki YOK)."""
    adlar = set()
    try:
        agac = ast.parse((REPO / rel).read_text(encoding="utf-8"))
    except Exception:
        return adlar
    for d in agac.body:
        if isinstance(d, ast.Assign):
            for t in d.targets:
                if isinstance(t, ast.Name):
                    adlar.add(t.id)
    return adlar


def main() -> int:
    sonuc: list[tuple[str, bool, str]] = []

    def ekle(ad, kosul, detay):
        sonuc.append((ad, bool(kosul), str(detay)))

    # ── 1. DDL-uclu tipler: /source/main + DUZ DDL ────────────────────────────
    for typ, beklenen_seg in (("table", "ddic/tables"),
                              ("tabl", "ddic/tables"),          # esanlamli
                              ("structure", "ddic/structures")):
        r, c = _adt_get(typ, "ZTEST_X")
        url = c.session.istenen[0] if c.session.istenen else ""
        ekle(f"{typ}: /source/main ucundan DUZ DDL",
             _sekil(r.get("source")) == "DDL" and r.get("exists") is True,
             f"sekil={_sekil(r.get('source'))} exists={r.get('exists')} {r.get('_exc','')}")
        ekle(f"{typ}: dogru ADT segmenti ({beklenen_seg}/.../source/main)",
             beklenen_seg in url and url.endswith("/source/main"),
             url or "HIC ISTEK YOK")
        ekle(f"{typ}: XML okuyucusu (get_ddic_object) CAGRILMADI",
             not c.xml_cagrilari, str(c.xml_cagrilari))

    # ── 2. REGRESYON CAPASI: XML-only tipler DEGISMEDI ───────────────────────
    #     (SILINMEZ — kaldirilirsa fix asiri-genellesir ve bu tipler 404 alir.)
    for typ in ("dtel", "dataelement", "domain", "doma", "tabletype", "ttyp"):
        r, c = _adt_get(typ, "ZTEST_X")
        ekle(f"CAPA {typ}: XML yolu KORUNDU (get_ddic_object cagrildi)",
             len(c.xml_cagrilari) == 1 and _sekil(r.get("source")) == "XML",
             f"xml_cagri={len(c.xml_cagrilari)} sekil={_sekil(r.get('source'))} {r.get('_exc','')}")
        ekle(f"CAPA {typ}: /source/main HIC ISTENMEDI (404 tuzagi)",
             not c.session.istenen, str(c.session.istenen))

    # ── 3. KANIT ZINCIRI (sessiz bosluk YOK) ─────────────────────────────────
    r, c = _adt_get("table", "ZTEST_YOK", kod=404, govde="")
    ekle("404 -> exists:false (gercek yokluk KORUNDU)",
         r.get("ok") is True and r.get("exists") is False,
         f"ok={r.get('ok')} exists={r.get('exists')} {r.get('_exc','')}")
    ekle("404 -> yokluk KANITI log'da (kaza degil, delil)",
         "404" in str(r.get("client_log") or ""),
         repr(str(r.get("client_log") or ""))[:70])

    r, _ = _adt_get("table", "ZTEST_X", kod=500, govde="patladi")
    ekle("500 -> yokluk BEYAN EDILMEZ (ok:false)",
         r.get("ok") is False and r.get("exists") is not False,
         f"ok={r.get('ok')} exists={r.get('exists')} error={r.get('error')}")

    r, _ = _adt_get("table", "ZTEST_X", kod=200, govde="   \n")
    ekle("200 + BOS govde -> sessiz gecmez (source_empty + uyari)",
         r.get("source_empty") is True and bool(r.get("warning")),
         f"source_empty={r.get('source_empty')} warning={'VAR' if r.get('warning') else 'YOK'}")

    # ── 4. IKI TUKETICI AYNI KARARI VERIYOR (ayrisma = bu kusurun koku) ──────
    try:
        from object_types import ddic_read_mode
        mods = {t: ddic_read_mode(t)[0] for t in
                ("table", "tabl", "structure", "dataelement", "dtel",
                 "domain", "doma", "tabletype", "ttyp", "ddls", "class")}
        ekle("object_types: table/structure = 'ddl'",
             mods["table"] == mods["tabl"] == mods["structure"] == "ddl", str(mods))
        ekle("object_types: dtel/domain/tabletype = 'xml'",
             {mods[k] for k in ("dataelement", "dtel", "domain", "doma",
                                "tabletype", "ttyp")} == {"xml"}, str(mods))
        ekle("KONTROL: DDIC olmayan tip None (asiri-yakalama yok)",
             mods["ddls"] is None and mods["class"] is None, str(mods))
    except Exception as exc:
        ekle("object_types.ddic_read_mode TEK KAYNAK olarak var", False, f"{exc}")

    # sap_sync_pull AYNI siniflandirmayi mi kullaniyor? (fonksiyonel)
    ekle(*_sync_pull_karari())

    # ── 5. TEK KAYNAK CAPASI (yerel kopya geri gelmesin) ─────────────────────
    atom_adlari = _sabit_adlari("mcp_servers/sap_adt/tools/atom.py")
    pull_adlari = _sabit_adlari("scripts/sap_sync_pull.py")
    ekle("atom.py'de YEREL DDIC tip-literali YOK",
         not ({"_DDIC_XML_TYPES", "_DDIC_XML", "_DDIC_CANON"} & atom_adlari),
         str(sorted({"_DDIC_XML_TYPES", "_DDIC_XML", "_DDIC_CANON"} & atom_adlari) or "temiz"))
    ekle("sap_sync_pull.py'de YEREL DDIC tip-literali YOK",
         not ({"_DDIC_XML_TYPES", "_DDIC_XML", "_DDIC_CANON"} & pull_adlari),
         str(sorted({"_DDIC_XML_TYPES", "_DDIC_XML", "_DDIC_CANON"} & pull_adlari) or "temiz"))

    gecen = sum(1 for _, ok, _ in sonuc if ok)
    for ad, ok, detay in sonuc:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad} -> {detay}")
    print(f"\n{gecen}/{len(sonuc)} OK")
    return 0 if gecen == len(sonuc) else 1


def _sync_pull_karari():
    """sap_sync_pull: `table` DDL(source-based) dalina, `dtel` XML dalina gitmeli.

    Mutasyon-dostu: eski surumde de main() cagrilabilir; hangi dala gittigini
    KAYDEDIP olceriz, cokerse FAIL degil "olculen sonuc" olur.
    """
    kayit = {"source_based": [], "xml": []}

    def _kur():
        sc = types.ModuleType("sap_client")

        class _C:
            def __init__(self):
                self.adt_client = object()

            def get_ddic_object(self, t, n):
                kayit["xml"].append((t, n))
                return XML_GOVDE

        sc.SAPClient = _C                                    # type: ignore[attr-defined]
        lib = types.ModuleType("sap_adt_lib")

        def _sync(object_url=None, object_name=None, object_type=None, client=None, force=False):
            kayit["source_based"].append((object_name, object_type))
            return {"written": True, "repo_path": "x"}

        lib.sync_repo_from_live = _sync                      # type: ignore[attr-defined]
        sd = types.ModuleType("source_drift")

        def _w(obj, src, object_type=None, force=False):
            kayit["xml"].append(("write", object_type))
            return {"written": True, "repo_path": "x"}

        sd.write_repo_from_live = _w                         # type: ignore[attr-defined]
        sys.modules["sap_client"] = sc
        sys.modules["sap_adt_lib"] = lib
        sys.modules["source_drift"] = sd

    # ⚠ TUZAK: `sap_sync_pull` import ANINDA `sys.stdout = TextIOWrapper(sys.stdout.buffer)`
    # yapar (Windows cp1252 korumasi). Bu sarmalayici cop-toplandiginda ALTTAKI GERCEK
    # buffer'i KAPATIR -> testin geri kalani "I/O operation on closed file" ile coker ve
    # HICBIR sonuc basilamaz (sebep de gorunmez). Cozum: modulu import etmeden ONCE
    # akislari ATILABILIR bir bellek-buffer'ina cevir; boylece sarmalama gercek stdout'a
    # HIC dokunmaz. (Bu bir harness detayidir; uretim davranisini olcmez.)
    import io as _io
    yedek_out, yedek_err = sys.stdout, sys.stderr
    eski_argv = sys.argv[:]
    cop = _io.TextIOWrapper(_io.BytesIO(), encoding="utf-8", errors="replace")
    try:
        _kur()
        sys.stdout = sys.stderr = cop
        sys.modules.pop("sap_sync_pull", None)
        import importlib
        ssp = importlib.import_module("sap_sync_pull")
        for ad, tip in (("ZTEST_T_X", "table"), ("ZTEST_E_X", "dtel")):
            sys.argv = ["sap_sync_pull.py", ad, "--type", tip, "--session", "fx"]
            try:
                ssp.main()
            except SystemExit:
                pass
    except Exception as exc:
        sys.stdout, sys.stderr = yedek_out, yedek_err
        return ("sap_sync_pull AYNI siniflandirmayi kullaniyor", False, f"olculemedi: {exc}")
    finally:
        sys.stdout, sys.stderr = yedek_out, yedek_err
        sys.argv = eski_argv
        for m in ("sap_client", "sap_adt_lib", "source_drift", "sap_sync_pull"):
            sys.modules.pop(m, None)

    tablo_dogru = any(t in ("table", "tabl") for _, t in kayit["source_based"])
    dtel_dogru = any(str(x[0]) in ("dataelement", "dtel") for x in kayit["xml"])
    return ("sap_sync_pull: table->DDL dali, dtel->XML dali (adt_get ile AYNI)",
            tablo_dogru and dtel_dogru,
            f"source_based={kayit['source_based']} xml={kayit['xml']}")


if __name__ == "__main__":
    sys.exit(main())
