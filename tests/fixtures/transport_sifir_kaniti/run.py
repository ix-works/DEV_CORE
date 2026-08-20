#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""adt_transport_list: YANLIS SIFIRA GUVEN DAMGASI basiyordu (sahte yesil).

KOK: tool `count:0` donerken `shape_recognized:true` bayragini da basiyordu ve
DOCSTRING'i cagirana aynen sunu ogretiyordu: *"`shape_recognized` alanina bak: True
ise sifir GERCEKTIR"*. Uc bagimsiz olcum bunu curuttu -- her uc vakada da
`count:0 + shape_recognized:true` iken `E070`'te ACIK transport VARDI (2026-08-18: 1
kayit · 2026-08-19: 2 kayit · 2026-08-19 A-00: 4 acik gorev).

⭐ ASIL DERS (bu fixture'in var olma sebebi): curutme 2026-08-18'de yapilmis ve
`DEGISIKLIK-OZETI §8` ile ajan brifinglerine yazilmisti -- ama ARACIN KENDI
DOCSTRING'i duzeltilmemisti. Yani duzeltme BELGEYE yazildi, arac yanlisi
BIRINCI AGIZDAN ogretmeye 2 gun daha devam etti. Bu korpus onu civilliyor.

⛔ NEDEN CIDDI: transport teyidi bir ADR 0005-C kapisidir. Arac "TR yok" derse dogal
refleks YENI TR ACMAKTIR -- ki yasaktir. Sahte-negatif dogrudan yasak ihlaline surukler.

FIX: `shape_recognized` yalniz BICIM sinyali olarak kaldi; sifir sonucta uc-degerli
`zero_verified` alani eklendi (`None` = soru gecersiz / `False` = kanitlanamadi;
⛔ ASLA `True`) + `zero_notice` cagirani E070 caprazina yolluyor. Docstring'deki
curutulmus cumle KALDIRILDI.

  S1-S3  uc-degerli sozlesme: 0 -> False · >0 -> None + notice YOK (FP capasi)
  S4-S5  ⭐ DOCSTRING: curutulmus cumle YOK · E070 caprazi VAR
  S6     3. BAGLAM: tam curutulen bilesim (shape_recognized True + count 0)
  S7     profil matrisi bozulmadi (B11: s4_private = btp_abap + 1 farki bu tool'dur)
  M1-M3  fix'i sok -> korpus KIRMIZI olmali

Kosum: python tests/fixtures/transport_sifir_kaniti/run.py     (exit 0 = PASS)
"""
from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
if not (REPO / "mcp_servers").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")
for p in (REPO, REPO / "scripts", REPO / "scripts" / "utils"):
    sys.path.insert(0, str(p))
os.environ.setdefault("CLAUDE_PROJECT_DIR", str(REPO))

# ── MCP SDK KOPRUSU (test-harness'i, uretim kodu DEGIL) — desen: dogrulama_kosamadi
try:  # pragma: no cover
    import mcp.server.fastmcp  # type: ignore  # noqa: F401
except Exception:
    import types as _t
    _mcp, _srv, _fast = (_t.ModuleType("mcp"), _t.ModuleType("mcp.server"),
                         _t.ModuleType("mcp.server.fastmcp"))

    class _FastMCP:
        def __init__(self, *a, **k):
            pass

        def tool(self, *a, **k):
            def _dek(fn):
                return fn
            return _dek

    _fast.FastMCP = _FastMCP          # type: ignore[attr-defined]
    _srv.fastmcp = _fast              # type: ignore[attr-defined]
    _mcp.server = _srv                # type: ignore[attr-defined]
    sys.modules.setdefault("mcp", _mcp)
    sys.modules.setdefault("mcp.server", _srv)
    sys.modules.setdefault("mcp.server.fastmcp", _fast)

try:
    from mcp_servers.sap_adt.tools import query
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"[fixture-hatasi] modul yuklenemedi (sessiz gecme YOK): {exc}")

QUERY_PATH = REPO / "mcp_servers" / "sap_adt" / "tools" / "query.py"

# CURUTULMUS REHBERLIK imzasi — docstring'de BU YENIDEN BELIRIRSE arac yanlisi
# ogretmeye geri donmustur. Desen gevsek tutuldu (yeniden yazim varyantlarini da yakalar).
_CURUK = re.compile(r"True\s+ise\s+s[iı]f[iı]r\s+GERCEKTIR|True\s+ise\s+s[iı]f[iı]r\s+GERÇEKTİR",
                    re.I)


class _SahteClient:
    """list_user_transports'u sabitler; SAP'ye HIC gidilmez."""

    def __init__(self, transports, shape=True):
        self._t = transports
        self._last_transport_meta = {"accept": "application/xml", "shape_recognized": shape}

    def list_user_transports(self, user=None):
        return self._t


# Mutasyonlu fonksiyon KENDI globals kopyasiyla kosar; stub o kopyaya uygulanmali.
# ⚠ Bu satir bir dersin urunu: stub yalniz `query` modulune uygulaniyordu, mutant ise
# globals KOPYASINDAKI gercek `_get_client`i goruyordu -> GERCEK SAP baglantisi denendi,
# `SAPConnectionError` firladi ve uc mutasyon da "KURULAMADI/KACTI" oldu. Sandbox,
# TUKETICININ cozum kokunu tasimali.
_AKTIF_G: dict | None = None


def cagir(transports, shape=True) -> dict:
    hedef = _AKTIF_G if _AKTIF_G is not None else query.__dict__
    eski = hedef.get("_get_client")
    try:
        hedef["_get_client"] = lambda: _SahteClient(transports, shape)
        return query.adt_transport_list(user="TESTUSER")
    finally:
        hedef["_get_client"] = eski


def _decorator_profilleri(src: str) -> set[str]:
    """adt_transport_list'in `profil_tool(...)` dekoratorundeki profil adlari (AST)."""
    try:
        agac = ast.parse(src)
    except SyntaxError:
        return set()
    for fn in ast.walk(agac):
        if isinstance(fn, ast.FunctionDef) and fn.name == "adt_transport_list":
            for d in fn.decorator_list:
                if isinstance(d, ast.Call) and getattr(d.func, "id", "") == "profil_tool":
                    for a in d.args:
                        if isinstance(a, (ast.Tuple, ast.List)):
                            return {e.value for e in a.elts
                                    if isinstance(e, ast.Constant) and isinstance(e.value, str)}
    return set()


def senaryolar(src: str) -> list[tuple[str, bool, str]]:
    out = []

    def ekle(ad, kosul, detay=""):
        out.append((ad, bool(kosul), detay))

    # --- S1: count == 0 -> zero_verified FALSE (True DEGIL, eksik DEGIL) ----
    r = cagir([])
    ekle("S1 count:0 -> zero_verified is False (ASLA True)",
         r.get("count") == 0 and r.get("zero_verified") is False,
         "count=%s zero_verified=%r" % (r.get("count"), r.get("zero_verified")))

    # --- S2: sifir sonucta cagiran E070 caprazina yonlendirilir -------------
    n = r.get("zero_notice", "")
    ekle("S2 count:0 -> zero_notice VAR ve E070 caprazini soyler",
         "E070" in n and "KANIT DEGILDIR" in n, "notice=%r" % n[:90])

    # --- S3: FP capasi (AYRI vektor) — dolu sonucta soru GECERSIZ ----------
    r2 = cagir([{"number": "DS4K900029", "description": "x", "status": "D"}])
    ekle("S3 FP capasi: count>0 -> zero_verified None + notice YOK",
         r2.get("count") == 1 and r2.get("zero_verified") is None
         and "zero_notice" not in r2,
         "zero_verified=%r notice_var=%s"
         % (r2.get("zero_verified"), "zero_notice" in r2))

    # --- S4: ⭐ CURUTULMUS REHBERLIK docstring'den KALKTI -------------------
    ds = query.adt_transport_list.__doc__ or ""
    ekle("S4 docstring curutulmus cumleyi ('True ise sifir GERCEKTIR') TASIMAZ",
         not _CURUK.search(ds), "eslesme=%r" % (_CURUK.search(ds).group(0)
                                                if _CURUK.search(ds) else None))

    # --- S5: docstring DOGRU yontemi soyler --------------------------------
    ekle("S5 docstring E070 caprazini + ADR 0005-C riskini soyler",
         "E070" in ds and "0005-C" in ds,
         "E070=%s ADR=%s" % ("E070" in ds, "0005-C" in ds))

    # --- S6: 3. BAGLAM — tam CURUTULEN bilesim -----------------------------
    # shape_recognized=True + count=0: eski docstring'in "sifir GERCEKTIR" dedigi
    # bilesim. Uc canli vakada bu bilesim YANLIS cikti.
    r3 = cagir([], shape=True)
    ekle("S6 3.baglam: shape_recognized True + count 0 -> HALA kanit degil",
         r3.get("shape_recognized") is True and r3.get("zero_verified") is False,
         "shape=%r zero_verified=%r"
         % (r3.get("shape_recognized"), r3.get("zero_verified")))

    # --- S7: profil matrisi bozulmadi (B11 sekli) --------------------------
    prof = _decorator_profilleri(src)
    ekle("S7 profil matrisi: tool s4_private'ta KAYITLI, btp_abap'ta DEGIL",
         "s4_private" in prof and "btp_abap" not in prof, "profiller=%s" % sorted(prof))

    return out


MUTASYONLAR = [
    ("M1 zero_verified'i True yap (sahte guven damgasi geri)",
     lambda s: s.replace('"zero_verified": None if n else False,',
                         '"zero_verified": None if n else True,')),
    ("M2 zero_notice'i sok (cagiran E070'e yonlendirilmesin)",
     lambda s: s.replace('        if not n:\n            sonuc["zero_notice"] = (',
                         '        if False:\n            sonuc["zero_notice"] = (')),
    ("M3 curutulmus cumleyi docstring'e geri koy",
     lambda s: s.replace(
         "    ⛔⛔ `count: 0` **KANIT DEĞİLDİR** — `shape_recognized: true` OLSA BİLE.",
         "    `count: 0` gördüğünde `shape_recognized` alanına bak: "
         "True ise sıfır GERÇEKTİR.")),
]


def _fonksiyonu_kur(src: str):
    """Mutasyonlu kaynaktan YALNIZ `adt_transport_list`i kurar ve dondurur.

    ⛔ TUM MODULU exec ETME: modul-seviyesi yan etkiler (profil cozumu / baglanti)
    `SAPConnectionError` firlatiyor ve koşucu bunu "mutasyon YAKALANDI" sayiyordu.
    Bu bir SAHTE-KIRMIZI'ydi: uc mutasyonun ucu de ayni istisnayla "yakalandi"
    goruntusu verdi ⇒ korpus o degismezler icin FIILEN BOSTU (cokme != FAIL, D2/2).
    Cozum: fonksiyon blogunu ayikla, globals olarak GERCEK modulun namespace
    KOPYASINI ver (importlar zaten cozulmus; yeni yan etki yok).
    """
    # ⚠ Blok siniri AST ile bulunur, satir-deseniyle DEGIL: elle yazilmis
    # "@ ile baslayan bir sonraki satir" mantigi blogu yanlis yerden kesti ve
    # `SyntaxError: line 1` uretti (mutasyonlar "KURULAMADI" -> KACTI).
    agac = ast.parse(src)
    dugum = next((n for n in agac.body
                  if isinstance(n, ast.FunctionDef) and n.name == "adt_transport_list"), None)
    if dugum is None:
        raise AssertionError("adt_transport_list bulunamadi (yama sekli degisti?)")
    # ⛔ DEKORATOR BILEREK ATLANIR (`def` satirindan baslanir): `@profil_tool`
    # uygulandiginda profil cozumu `.conn_adt`ye gidip SAPConnectionError firlatiyor
    # ve mutasyon "KURULAMADI" oluyordu. Dekorator zaten mutasyonun konusu DEGIL;
    # profil matrisi S7'de KAYNAKTAN (AST) ayrica olculuyor.
    blok = "\n".join(src.splitlines()[dugum.lineno - 1:dugum.end_lineno])
    g = dict(query.__dict__)          # gercek modulun cozulmus namespace'i
    exec(compile(blok, str(QUERY_PATH), "exec"), g)
    return g["adt_transport_list"], g


def main() -> int:
    print("=" * 78)
    print("transport_sifir_kaniti — 'count:0' bir KANIT DEGILDIR")
    print("=" * 78)

    ham = QUERY_PATH.read_text(encoding="utf-8")
    sonuc = senaryolar(ham)
    kirik = [(a, d) for a, ok, d in sonuc if not ok]
    for ad, ok, detay in sonuc:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok:
            print("         gorulen: %s" % detay)
    print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

    print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
    mut_kirik, yama_kirik = [], []
    eski_mod = query.adt_transport_list
    for ad, mut in MUTASYONLAR:
        bozuk = mut(ham)
        if bozuk == ham:
            print("  [YAMA TUTMADI] %s" % ad)
            yama_kirik.append(ad)
            continue
        try:
            global _AKTIF_G
            query.adt_transport_list, _AKTIF_G = _fonksiyonu_kur(bozuk)
            m_res = senaryolar(bozuk)
            yakalandi = any(not ok for _, ok, _ in m_res)
            kacan = [a for a, ok, _ in m_res if not ok]
        except BaseException as e:
            # ⛔ COKME != FAIL: mutasyon "yakalandi" gorunmesin diye AYRI raporlanir.
            yakalandi, kacan = False, []
            print("  [KURULAMADI] %s -> %s: %s" % (ad, type(e).__name__, e))
        finally:
            query.adt_transport_list = eski_mod
            _AKTIF_G = None
        print("  [%s] %s" % ("YAKALANDI" if yakalandi else "KACTI", ad))
        if yakalandi:
            print("         kiran senaryo(lar): %s" % ", ".join(kacan[:3]))
        else:
            mut_kirik.append(ad)

    print("\n" + "=" * 78)
    if kirik or mut_kirik or yama_kirik:
        if kirik:
            print("FAIL — senaryo: %s" % ", ".join(a for a, _ in kirik))
        if mut_kirik:
            print("FAIL — mutasyon KACTI: %s" % ", ".join(mut_kirik))
        if yama_kirik:
            print("FAIL — mutasyon yamasi kaynaga UYMADI: %s" % ", ".join(yama_kirik))
        return 1
    print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(MUTASYONLAR)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
