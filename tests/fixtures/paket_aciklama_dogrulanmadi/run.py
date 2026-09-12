#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q230 — `adt_package_contents`: `description` sutunu SUNUCU TARAFINDA kayiyor, arac SESSIZDI.

=== OLCUM (2026-09-13, DEV, salt-okuma; kimlikler bu dosyada ANONIM) ===
Buyuk bir paketin nodestructure yaniti bir HATA DUGUMU tasidi:
  OBJECT_NAME="Error loading node:"  TECH_NAME="The message content is not acceptable.
  Accepted content types: application/atomsvc+xml"   (OBJECT_TYPE YOK)
O paketin karsilastirilabilen 120/120 objesinin aciklamasi YANLISTI; ayni-tip bloklarinda
hemen hepsi bir ONCEKI objenin gercek aciklamasini tasiyordu. Kontrol paketi (hata dugumu
yok) 10/10 dogru. Kayma HAM XML'dedir: `SAPClient.list_package_contents` aciklamayi
DUGUM-ICI okur (kaydirma mekanizmasi yok). `Accept`e `application/atomsvc+xml` eklemek
yaniti DEGISTIRMEDI (ayni uzunluk, ayni hata dugumu) => istemcide DUZELTILEMEZ.
Cozum: "isaretle + belgele" — `description_verified: false` (KOSULSUZ) + dogrulama yolu.

  K1 ⭐ AYIRT EDICI  nodestructure dali: `description_verified: false` + uyari dogrulama
                    YOLUNU soyluyor (adt_search_objects / adt_get)   [fix oncesi alan YOK]
  K2 ⭐ 3.BAGLAM     fallback dali (`package_verified: false`): bayrak ORADA DA var (kosulsuz)
  S1 SINIR beyani   arac aciklamayi DUZELTMEYE CALISMAZ (kayik deger AYNEN doner) — eski kodda
                    da gecer; "istemci kaydirmasi" gibi tahmin eden bir yamanin capasi
  S2 SINIR beyani   hata dugumu ayristiricida DUSER (sayim yalniz gercek objeler) — sinyalin
                    arac ciktisina NEDEN ulasmadigini belgeler (eski kodda da gecer)
  N1 FP capasi      eski alanlar AYNEN (ok/package/count/package_verified; node dalinda `warning` yok)
  M1-M3             fix'i sok -> korpus KIRMIZI olmali

⛔ SAP'ye BAGLANMAZ: nodestructure XML'i sentetiktir (SEKIL canli dokumden, adlar anonim).
Kosum: python tests/fixtures/paket_aciklama_dogrulanmadi/run.py     (exit 0 = PASS)
"""
from __future__ import annotations

import importlib.util
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

try:  # pragma: no cover - ortam kosullu (MCP SDK CI'da yok)
    import mcp.server.fastmcp  # type: ignore  # noqa: F401
except Exception:
    _mcp, _srv, _fast = (types.ModuleType("mcp"), types.ModuleType("mcp.server"),
                         types.ModuleType("mcp.server.fastmcp"))

    class _FastMCP:
        def __init__(self, *a, **k):
            pass

        def tool(self, *a, **k):
            def _dek(fn):
                return fn
            return _dek

    _fast.FastMCP = _FastMCP                                  # type: ignore[attr-defined]
    _srv.fastmcp = _fast                                      # type: ignore[attr-defined]
    _mcp.server = _srv                                        # type: ignore[attr-defined]
    sys.modules.setdefault("mcp", _mcp)
    sys.modules.setdefault("mcp.server", _srv)
    sys.modules.setdefault("mcp.server.fastmcp", _fast)

from sap_client import SAPClient                               # noqa: E402
from mcp_servers.sap_adt.tools import query as QUERY_TABAN     # noqa: E402

HEDEF = REPO / "mcp_servers" / "sap_adt" / "tools" / "query.py"


def _dugum(tip: str, ad: str, aciklama: str) -> str:
    return ("<SEU_ADT_REPOSITORY_OBJ_NODE><OBJECT_TYPE>%s</OBJECT_TYPE><OBJECT_NAME>%s"
            "</OBJECT_NAME><TECH_NAME>%s</TECH_NAME><DESCRIPTION>%s</DESCRIPTION>"
            "</SEU_ADT_REPOSITORY_OBJ_NODE>" % (tip, ad, ad, aciklama))


# Canli SEKIL: kategori dugumleri (DEVC/*) + ADSIZ-TIPSIZ hata dugumu + KAYIK aciklamalar.
# Gercek aciklamalar: T_A="A tablosu", T_B="B tablosu", T_C="C tablosu".
# Yanitta her obje bir ONCEKININ aciklamasini tasiyor (ilki bos).
KAYIK_XML = ('<asx:abap xmlns:asx="http://www.sap.com/abapxml"><asx:values><DATA>'
             + _dugum("DEVC/DT", "ZSD001_CLC", "")
             + "<SEU_ADT_REPOSITORY_OBJ_NODE><OBJECT_NAME>Error loading node:</OBJECT_NAME>"
               "<TECH_NAME>The message content is not acceptable. Accepted content types: "
               "&amp;application/atomsvc+xml&amp;</TECH_NAME><VISIBILITY>0</VISIBILITY>"
               "</SEU_ADT_REPOSITORY_OBJ_NODE>"
             + _dugum("TABL/DT", "ZSD001_T_A", "")
             + _dugum("TABL/DT", "ZSD001_T_B", "A tablosu")
             + _dugum("TABL/DT", "ZSD001_T_C", "B tablosu")
             + "</DATA></asx:values></asx:abap>")
KAYIK_BEKLENEN = {"ZSD001_T_A": "", "ZSD001_T_B": "A tablosu", "ZSD001_T_C": "B tablosu"}


class _Istemci:
    """GERCEK `SAPClient.list_package_contents` govdesi; yalniz uclar sahte."""

    def __init__(self, node_calisiyor: bool):
        self.debug_enabled = False

        class _Adt:
            def get_package_contents(_s, pkg):
                if not node_calisiyor:
                    raise Exception("HTTP 500 nodestructure (yetki yok)")
                return KAYIK_XML
        self.adt_client = _Adt()

    def search_objects(self, pattern, max_results=500, debug_context=None):
        return [{"name": "ZSD001_T_A", "type": "TABL/DT", "uri": "/u", "description": "A tablosu"}]

    def list_package_contents(self, pkg):
        return SAPClient.list_package_contents(self, pkg)


SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul), detay))


def _kos(q, node_calisiyor: bool) -> dict:
    eski = q._get_client
    q._get_client = lambda: _Istemci(node_calisiyor)
    try:
        return q.adt_package_contents(package="ZSD001_CLC")
    finally:
        q._get_client = eski


def k1_node_dali(q) -> None:
    r = _kos(q, True)
    uyari = str(r.get("description_warning", ""))
    kontrol("K1 ⭐ nodestructure dali: `description_verified: false` [fix oncesi alan YOK]",
            r.get("description_verified") is False,
            f"description_verified={r.get('description_verified', 'YOK')!r}")
    kontrol("K1b ⭐ uyari DOGRULAMA YOLUNU soyluyor (adt_search_objects + adt_get metadata)",
            "adt_search_objects" in uyari and "adt_get" in uyari and "DOĞRULANMADI" in uyari,
            f"uyari={uyari[:120]!r}")


def k2_fallback_dali(q) -> None:
    r = _kos(q, False)
    kontrol("K2 ⭐ 3.BAGLAM fallback dali (`package_verified: false`): bayrak KOSULSUZ orada da",
            r.get("package_verified") is False and r.get("description_verified") is False
            and bool(r.get("description_warning")) and bool(r.get("warning")),
            f"pv={r.get('package_verified')} dv={r.get('description_verified', 'YOK')!r}")


def s1_duzeltme_yok(q) -> None:
    r = _kos(q, True)
    gorulen = {o["name"]: o.get("description") for o in r.get("objects", [])}
    kontrol("S1 SINIR: arac aciklamayi DUZELTMEYE CALISMAZ — kayik deger AYNEN doner "
            "(istemci-kaydirma yamasi YOK)",
            gorulen == KAYIK_BEKLENEN, f"gorulen={gorulen}")


def s2_hata_dugumu(q) -> None:
    r = _kos(q, True)
    kontrol("S2 SINIR: sunucu hata dugumu ayristiricida DUSER (count=3 gercek obje) — kayma "
            "sinyali arac ciktisina ulasmaz, bu yuzden bayrak KOSULSUZDUR",
            r.get("count") == 3
            and not any("Error" in str(o.get("name")) for o in r.get("objects", [])),
            f"count={r.get('count')} adlar={[o.get('name') for o in r.get('objects', [])]}")


def n1_sozlesme(q) -> None:
    r = _kos(q, True)
    kontrol("N1 FP capasi: eski alanlar AYNEN (ok/package/package_verified) + node dalinda "
            "`warning` YOK (paket-uyeligi ekseni bozulmadi)",
            r.get("ok") is True and r.get("package") == "ZSD001_CLC"
            and r.get("package_verified") is True and "warning" not in r
            and isinstance(r.get("objects"), list),
            f"ok={r.get('ok')} pv={r.get('package_verified')} warning={r.get('warning', 'YOK')!r}")


def korpus(modul_yolu: Path, ad: str) -> list[tuple[str, bool, str]]:
    global SONUC
    SONUC = []
    if modul_yolu == HEDEF:
        q = QUERY_TABAN
    else:
        sys.modules.pop(ad, None)
        spec = importlib.util.spec_from_file_location(ad, modul_yolu)
        q = importlib.util.module_from_spec(spec)              # type: ignore[arg-type]
        sys.modules[ad] = q
        spec.loader.exec_module(q)                             # type: ignore[union-attr]
    for bolum in (k1_node_dali, k2_fallback_dali, s1_duzeltme_yok, s2_hata_dugumu, n1_sozlesme):
        try:
            bolum(q)
        except BaseException as exc:                           # noqa: BLE001
            kontrol(f"[BOLUM COKTU] {bolum.__name__}", False,
                    f"{type(exc).__name__}: {str(exc)[:200]}")
    return SONUC


MUTASYONLAR = [
    ("M1 ⭐AYIRT EDICI kusurun BIREBIR hali: bayrak HIC basilmasin",
     lambda s: s.replace('            "description_verified": False,\n', "")),
    ("M2 ⭐SINIR bayrak YALAN soylesin (true)",
     lambda s: s.replace('            "description_verified": False,\n',
                         '            "description_verified": True,\n')),
    ("M3 ⭐SINIR uyari dogrulama YOLUNU soylemesin",
     lambda s: s.replace('"gerekiyorsa adt_search_objects ya da adt_get metadata\'sı (adtcore:description; "',
                         '"gerekiyorsa baska kaynaga bak (; "')),
]


def main() -> int:
    print("=" * 78)
    print("paket_aciklama_dogrulanmadi — Q230: description sunucuda kayiyor, arac sessizdi")
    print("=" * 78)
    ham = HEDEF.read_text(encoding="utf-8")
    sonuc = korpus(HEDEF, "query_taban_q230")
    kirik = [(a, d) for a, ok, d in sonuc if not ok]
    for ad, ok, detay in sonuc:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok or os.environ.get("IX_FIXTURE_VERBOSE"):
            print("         -> %s" % detay)
    print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

    print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
    mutant = HEDEF.with_name("_mutant_query_q230.py")
    mut_kirik, yama_kirik, kurulamadi = [], [], []
    for i, (ad, mut) in enumerate(MUTASYONLAR):
        bozuk = mut(ham)
        if bozuk == ham:
            print("  [YAMA TUTMADI] %s" % ad)
            yama_kirik.append(ad)
            continue
        try:
            mutant.write_text(bozuk, encoding="utf-8", newline="\n")
            kacan = [a for a, ok, _ in korpus(mutant, "query_mutant_q230_%d" % i) if not ok]
        except BaseException as e:                             # noqa: BLE001
            kurulamadi.append("%s -> %s: %s" % (ad, type(e).__name__, e))
            print("  [KURULAMADI] %s -> %s: %s" % (ad, type(e).__name__, e))
            continue
        finally:
            mutant.unlink(missing_ok=True)
        print("  [%s] %s" % ("YAKALANDI" if kacan else "KACTI", ad))
        if kacan:
            print("         kiran senaryo(lar): %s" % ", ".join(kacan[:3]))
        else:
            mut_kirik.append(ad)

    print("\n" + "=" * 78)
    if kirik or mut_kirik or yama_kirik or kurulamadi:
        if kirik:
            print("FAIL — senaryo: %s" % ", ".join(a for a, _ in kirik))
        if mut_kirik:
            print("FAIL — mutasyon KACTI: %s" % ", ".join(mut_kirik))
        if yama_kirik:
            print("FAIL — mutasyon yamasi kaynaga UYMADI: %s" % ", ".join(yama_kirik))
        if kurulamadi:
            print("FAIL — mutasyon KURULAMADI (olcum yapilamadi): %s" % "; ".join(kurulamadi))
        return 1
    print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(MUTASYONLAR)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
