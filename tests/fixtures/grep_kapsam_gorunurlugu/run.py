#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C-04 — `adt_grep_source`: okunamayan obje SESSIZCE dusuyordu (`ok:true, match_count:0`).

=== KOK ===
Tarama dongusu `if not src: continue` diyordu. Okunamayan obje ne SAYILIYOR ne
RAPORLANIYOR ne de bir bayragi kirletiyordu. Cagiran icin *"bu metin gecmiyor"* ile
*"o objeyi hic okuyamadim"* AYNI ciktiya dusuyordu — ve karar (push/silme/blast-radius)
bu ciktiya dayaniyordu.

Sessiz dusus BES ayri kapidan oluyordu, dordu okuma dongusunun DISINDA:
  · `object_types` filtresi (varsayilan CLAS,PROG,INTF,DDLS -> FUGR HIC girmiyor)
  · `_GREP_TYPE_MAP` disi tip (TABL/DTEL/FUNC...)   · `max_objects` kesmesi
  · `adt_get` hatasi / `exists:false` / BOS govde
Ustune ALTINCI bir eksen var: obje OKUNUYOR ama ICERIGI EKSIK (FUGR iskelet ana
include; FM govdesi `L<FG>U01`de — playbook/adt-fugr-functions.md §4.1).

=== Q106 ILE ILISKI (ayni kok, farkli ayak) ===
Q106 leg-① *"kapsayamiyorsa `scope_verified` YESIL VERMEMELI; atlanan obje tipleri
MAKINECE OKUNUR raporlanmali"* diyor. Fix `scope_verified`in ANLAMINI DEGISTIRMEZ
(o paket-ucunun DOGRULUGUNU soyler; tuketicisi var: dogrulama_kosamadi R5) — AYRI bir
eksen ekler: `coverage_complete` + `skipped_objects` + `partial_objects`. Iki eksen
bilerek ayridir; N1 bunu civiler.

  K1 ⭐ AYIRT EDICI  bes sessiz dusus kapisi -> `skipped_objects` (ad + SEBEP) + uyari
  K2 pozitif kontrol tam kapsam -> uyari YOK, `coverage_complete: true`, ESKI ALANLAR AYNI
  K3 3.BAGLAM       `objects=` dali (paket YOK): `func` tipi `exists:false` -> `not_readable`
  K4 ⭐ Q106 ayagi   FUGR okundu ama ISKELET -> `partial_objects` + coverage_complete FALSE
  K5               `max_objects` kesmesi: dusen objenin ADI da raporlanir (eski bayrak durur)
  N1 FP capasi      `scope_verified` ekseni DEGISMEDI (paket-ucu dogru -> true, uyari yok)
  N2 FP capasi      fallback kapsaminda `scope_warning` HALA basiliyor (komsu eksen sag)
  N3 FP capasi      `matches` ve sayaclarin sekli degismedi (tuketici sozlesmesi)
  M1-M5             fix'i sok -> korpus KIRMIZI olmali

⛔ SAP'ye BAGLANMAZ: `adt_get` ve paket ucu sahtelenir. Olculen sey KAPSAM MUHASEBESIDIR,
SAP'nin gercekten ne dondurdugu DEGIL (o sekiller Q106'nin 2026-08-18 canli olcumunden
ve playbook §4.1'den alindi).

Kosum: python tests/fixtures/grep_kapsam_gorunurlugu/run.py     (exit 0 = PASS)
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

from mcp_servers.sap_adt.tools import atom                     # noqa: E402
from mcp_servers.sap_adt.tools import query as QUERY_TABAN     # noqa: E402

HEDEF = REPO / "mcp_servers" / "sap_adt" / "tools" / "query.py"
DESEN = "MARA"

# Sahte kaynaklar (gercek ABAP olmasi gerekmiyor; olculen sey MUHASEBE).
KAYNAK = {
    "ZCL_OKUNUR": "SELECT * FROM mara INTO TABLE @lt.",
    "ZCL_TEMIZ": "WRITE 'merhaba'.",
    "ZSD_FG_ORNEK": "  INCLUDE lzsd_fg_orneknek_top.\n  INCLUDE lzsd_fg_orneku01.",
}
# `adt_get` DONUS SEKILLERI (2026-08-01 uc-degerli sozlesmeden):
CEVAP = {
    "ZCL_OKUNUR": {"ok": True, "exists": True, "source": KAYNAK["ZCL_OKUNUR"]},
    "ZCL_TEMIZ": {"ok": True, "exists": True, "source": KAYNAK["ZCL_TEMIZ"]},
    "ZCL_OKUNAMAZ": {"ok": False, "error": "http_500", "message": "Internal Server Error"},
    "ZCL_YOK": {"ok": True, "exists": False},
    "ZIF_BOS": {"ok": True, "exists": True, "source": ""},
    "ZSD_FG_ORNEK": {"ok": True, "exists": True, "source": KAYNAK["ZSD_FG_ORNEK"]},
    "ZFM_ORNEK": {"ok": True, "exists": False},      # func: group-resolution kusuru (§4)
}


class _SahteIstemci:
    def __init__(self, objeler: list[dict], dogrulanmis: bool = True):
        self._objeler, self._dogrulanmis = objeler, dogrulanmis
        self.debug_enabled = False

    def list_package_contents(self, paket):
        return [dict(o, package_verified=self._dogrulanmis) for o in self._objeler]


SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul), detay))


def _sahte_get(name, object_type="class", include_source=True):
    return dict(CEVAP.get(str(name).upper(), {"ok": True, "exists": False}))


def _kos(q, objeler=None, dogrulanmis=True, **kw):
    eski_client, eski_get = q._get_client, atom.adt_get
    q._get_client = lambda: _SahteIstemci(objeler or [], dogrulanmis)
    atom.adt_get = _sahte_get
    try:
        return q.adt_grep_source(pattern=DESEN, **kw)
    finally:
        q._get_client, atom.adt_get = eski_client, eski_get


def _sebepler(r: dict) -> dict:
    return {a["object"]: a["reason"] for a in r.get("skipped_objects", [])}


# =============================================================================
def k1_bes_kapi(q) -> None:
    objeler = [{"name": "ZCL_OKUNUR", "type": "CLAS/OC"},
               {"name": "ZCL_OKUNAMAZ", "type": "CLAS/OC"},
               {"name": "ZCL_YOK", "type": "CLAS/OC"},
               {"name": "ZIF_BOS", "type": "INTF/OI"},
               {"name": "ZTB_ORNEK", "type": "TABL/DT"},      # grep'lenemez tip
               {"name": "ZSD_FG_ORNEK", "type": "FUGR/F"}]    # varsayilan filtre disi
    # ⚠ ALET NOTU (ilk kosumda yakalandi): kapilarin SIRASI onemli — `object_types`
    # filtresi `_GREP_TYPE_MAP` kontrolunden ONCE calisir. Varsayilan filtre TABL'i de
    # disladigi icin `type_unsupported` dali OLCULEMIYORDU (ikisi de `type_filtered`
    # gorunuyordu). Filtreye TABL EKLENIR ki iki sinif AYRI AYRI olculebilsin.
    r = _kos(q, objeler, package="ZORNEK_PKG", object_types="CLAS,INTF,TABL")
    s = _sebepler(r)
    bekl = {"ZCL_OKUNAMAZ": "read_failed", "ZCL_YOK": "not_readable",
            "ZIF_BOS": "source_empty", "ZTB_ORNEK": "type_unsupported",
            "ZSD_FG_ORNEK": "type_filtered"}
    kontrol("K1 ⭐ bes sessiz dusus kapisinin BESI de ad+SEBEP ile raporlaniyor",
            s == bekl, f"gorulen={s} beklenen={bekl}")
    kontrol("K1b ⭐ `coverage_complete: false` + makinece okunur sayac + uyari",
            r.get("coverage_complete") is False and r.get("skipped_count") == 5
            and "match_count" in str(r.get("coverage_warning", "")),
            f"complete={r.get('coverage_complete')} sayac={r.get('skipped_count')} "
            f"uyari={str(r.get('coverage_warning'))[:90]!r}")
    kontrol("K1c eslesen TEK obje yine dogru sayiliyor (muhasebe eslesmeyi bozmadi)",
            r.get("scanned_objects") == 1 and r.get("match_count") == 1,
            f"scanned={r.get('scanned_objects')} match={r.get('match_count')}")


def k2_pozitif(q) -> None:
    objeler = [{"name": "ZCL_OKUNUR", "type": "CLAS/OC"},
               {"name": "ZCL_TEMIZ", "type": "CLAS/OC"}]
    r = _kos(q, objeler, package="ZORNEK_PKG")
    eski_alanlar = {"ok": True, "pattern": DESEN, "scanned_objects": 2, "match_count": 1,
                    "truncated_object_scope": False, "truncated_matches": False,
                    "scope_verified": True}
    sapan = {k: (r.get(k), v) for k, v in eski_alanlar.items() if r.get(k) != v}
    kontrol("K2 pozitif kontrol: tam kapsamda ESKI ALANLARIN HEPSI aynen (sozlesme)",
            not sapan, f"sapan={sapan}")
    kontrol("K2b pozitif kontrol: uyari YOK + `coverage_complete: true` "
            "(alarm yorgunlugu capasi)",
            r.get("coverage_complete") is True and "coverage_warning" not in r
            and r.get("skipped_count") == 0 and r.get("partial_count") == 0,
            f"complete={r.get('coverage_complete')} uyari={r.get('coverage_warning', 'YOK')!r}")
    kontrol("N3 FP capasi: `matches` sekli degismedi (object/type/line/text)",
            r.get("matches") and set(r["matches"][0]) == {"object", "type", "line", "text"},
            f"matches={r.get('matches')}")


def k3_objects_dali(q) -> None:
    """3. BAGLAM: paket dali DEGIL `objects=` dali; ustelik playbook §4'un `func` kusuru."""
    r = _kos(q, objects="ZFM_ORNEK:func,ZCL_OKUNUR:class")
    s = _sebepler(r)
    kontrol("K3 3.BAGLAM `objects=` dali: `func` exists:false -> `not_readable` "
            "(sessiz dusus DEGIL)",
            s == {"ZFM_ORNEK": "not_readable"} and r.get("coverage_complete") is False
            and r.get("scanned_objects") == 1,
            f"sebepler={s} complete={r.get('coverage_complete')} "
            f"scanned={r.get('scanned_objects')}")
    kontrol("K3b sebep DETAYI playbook'un OLCULMUS korlugune isaret ediyor (uydurma yok)",
            any("group-resolution" in (a.get("detail") or "")
                for a in r.get("skipped_objects", [])),
            f"detaylar={[a.get('detail', '')[:60] for a in r.get('skipped_objects', [])]}")


def k4_fugr_kismi(q) -> None:
    """⭐ Q106 leg-①: obje TARANDI ama icerigi EKSIK — 'taradim, temiz' yalani burada."""
    objeler = [{"name": "ZSD_FG_ORNEK", "type": "FUGR/F"},
               {"name": "ZCL_OKUNUR", "type": "CLAS/OC"}]
    r = _kos(q, objeler, package="ZORNEK_PKG", object_types="CLAS,FUGR")
    kismi = {k["object"]: k["reason"] for k in r.get("partial_objects", [])}
    kontrol("K4 ⭐ FUGR okundu ama ISKELET -> `partial_objects` (fugr_skeleton_only)",
            kismi == {"ZSD_FG_ORNEK": "fugr_skeleton_only"},
            f"kismi={kismi} scanned={r.get('scanned_objects')}")
    kontrol("K4b ⭐ kismi kapsamda `coverage_complete` YESIL YANMIYOR (Q106 leg-①)",
            r.get("coverage_complete") is False and bool(r.get("coverage_warning")),
            f"complete={r.get('coverage_complete')} skipped={r.get('skipped_count')}")
    kontrol("K4c FP capasi: kismi tarama YINE DE sayiliyor (obje kapsamdan atilmadi)",
            r.get("scanned_objects") == 2 and r.get("skipped_count") == 0,
            f"scanned={r.get('scanned_objects')} skipped={r.get('skipped_count')}")


def k5_max_objects(q) -> None:
    objeler = [{"name": "ZCL_OKUNUR", "type": "CLAS/OC"},
               {"name": "ZCL_TEMIZ", "type": "CLAS/OC"},
               {"name": "ZCL_UCUNCU", "type": "CLAS/OC"}]
    r = _kos(q, objeler, package="ZORNEK_PKG", max_objects=2)
    s = _sebepler(r)
    kontrol("K5 `max_objects` kesmesi: eski bayrak DURUYOR + dusen objenin ADI raporlaniyor",
            r.get("truncated_object_scope") is True and s == {"ZCL_UCUNCU": "max_objects"},
            f"truncated={r.get('truncated_object_scope')} sebepler={s}")


def n1_scope_ekseni(q) -> None:
    """FP capasi: `scope_verified` AYRI eksendir; kapsam muhasebesi onu bozmamali."""
    objeler = [{"name": "ZCL_OKUNUR", "type": "CLAS/OC"}]
    r = _kos(q, objeler, dogrulanmis=True, package="ZORNEK_PKG")
    kontrol("N1 FP capasi: paket-ucu dogru -> `scope_verified: true` + `scope_warning` YOK",
            r.get("scope_verified") is True and "scope_warning" not in r,
            f"verified={r.get('scope_verified')} uyari={r.get('scope_warning', 'YOK')!r}")
    r = _kos(q, objeler, dogrulanmis=False, package="ZORNEK_PKG")
    kontrol("N2 FP capasi: fallback kapsaminda `scope_warning` HALA basiliyor "
            "(komsu eksen sag)",
            r.get("scope_verified") is False and bool(r.get("scope_warning")),
            f"verified={r.get('scope_verified')} uyari={str(r.get('scope_warning'))[:60]!r}")


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
    for bolum in (k1_bes_kapi, k2_pozitif, k3_objects_dali, k4_fugr_kismi,
                  k5_max_objects, n1_scope_ekseni):
        try:
            bolum(q)
        except BaseException as exc:                           # noqa: BLE001
            # ⛔ COKME != FAIL: patlayan bolum ADIYLA FAIL yazilir (kanit uretilemedi).
            kontrol(f"[BOLUM COKTU] {bolum.__name__}", False,
                    f"{type(exc).__name__}: {str(exc)[:200]}")
    return SONUC


# --- MUTASYONLAR ------------------------------------------------------------
MUTASYONLAR = [
    ("M1 kusurun BIREBIR eski hali: okunamayan obje SESSIZCE `continue`",
     lambda s: s.replace(
         '            if r.get("ok") is False:\n'
         '                sebep, detay = "read_failed", str(r.get("error") or r.get("message") or "")[:200]\n'
         '            elif r.get("exists") is False:\n'
         '                sebep = "not_readable"\n'
         '                detay = ("adt_get exists:false — obje YOK ya da bu tip bu uçtan okunamıyor "\n'
         '                         "(func/FUGR group-resolution: playbook/adt-fugr-functions.md §4)")\n'
         '            else:\n'
         '                sebep, detay = "source_empty", "HTTP 200 ama kaynak gövdesi BOŞ"\n'
         '            atlanan.append({"object": n, "type": at, "reason": sebep, "detail": detay})\n'
         '            continue\n',
         '            continue\n')),
    ("M2 ⭐SINIR dusenler raporlanir ama `coverage_complete` DAIMA true (bayrak yalani)",
     lambda s: s.replace(
         "    tam_kapsam = not atlanan and not kismi and not truncated_scope and not hit_cap\n",
         "    tam_kapsam = True\n")),
    ("M3 ⭐SINIR yarim-fix: TIP FILTRESI dususlerini sessiz birak (yalniz okuma sayilir)",
     lambda s: s.replace(
         '                    atlanan.append({"object": o.get("name"), "type": pref,\n'
         '                                    "reason": "type_filtered",\n'
         '                                    "detail": f"object_types={object_types}"})\n'
         '                    continue\n',
         '                    continue\n')),
    ("M4 ⭐SINIR dusen objeyi say ama ADINI/SEBEBINI verme (makinece okunamaz)",
     lambda s: s.replace(
         '           "skipped_count": len(atlanan), "skipped_objects": atlanan[:50],\n',
         '           "skipped_count": len(atlanan), "skipped_objects": [],\n')),
    ("M5 ⭐SINIR FUGR kismi-kapsam raporunu kaldir (Q106 leg-① geri gelir)",
     lambda s: s.replace(
         '        if at == "functiongroup":\n',
         '        if False and at == "functiongroup":\n')),
]


def main() -> int:
    print("=" * 78)
    print("grep_kapsam_gorunurlugu — C-04: okunamayan obje SESSIZCE dusuyordu")
    print("=" * 78)
    if not HEDEF.is_file():
        print(f"FAIL — hedef yok: {HEDEF}")
        return 1
    ham = HEDEF.read_text(encoding="utf-8")

    sonuc = korpus(HEDEF, "query_taban_c04")
    kirik = [(a, d) for a, ok, d in sonuc if not ok]
    for ad, ok, detay in sonuc:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok or os.environ.get("IX_FIXTURE_VERBOSE"):
            print("         -> %s" % detay)
    print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

    print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
    mutant = HEDEF.with_name("_mutant_query_c04.py")
    mut_kirik, yama_kirik, kurulamadi = [], [], []
    for i, (ad, mut) in enumerate(MUTASYONLAR):
        bozuk = mut(ham)
        if bozuk == ham:
            print("  [YAMA TUTMADI] %s" % ad)
            yama_kirik.append(ad)
            continue
        try:
            mutant.write_text(bozuk, encoding="utf-8", newline="\n")
            kacan = [a for a, ok, _ in korpus(mutant, "query_mutant_c04_%d" % i) if not ok]
        except BaseException as e:                             # noqa: BLE001
            # ⛔ KURULAMADI != KACTI: olcum HIC yapilamadi (korpus zayif DEMEK DEGIL).
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
