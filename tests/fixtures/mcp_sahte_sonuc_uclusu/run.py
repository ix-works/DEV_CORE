#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mcp_sahte_sonuc_uclusu fixture — MCP atom katmaninda "arac YANLIS soyluyor" UCLUSU.

NEDEN VAR — ayni ailenin uc uyesi, uc AYRI kayit, TEK ortak kok:
`ok`/`exists`/`activated` alanlari ALT KATMANIN IDDIASINI tekrarliyordu; hicbiri
BAGIMSIZ bir kanitla olculmuyordu. Ucu de HTTP 200/dolu-cikti ile geldigi icin
sessizdi.

  A) kayit #8  (2026-08-18) — `adt_get(object_type="tabl")` bir DDIC YAPI icin
     `exists:false` dedi; obje CANLIDA VARDI (`adt_search_objects` buldu). Sebep:
     `tabl` `/ddic/tables/` ucuna gider, yapilar `/ddic/structures/` altindadir.
     "YANLIS UCA SORDUM" -> "OBJE YOK" diye raporlaniyordu.
     ⛔ Zarar: "on kosul yok" sonucu ya build'i durdurur ya MUKERRER obje yaratma
     karari uretir (ADR 0005-A/D zinciri).

  B) kayit #70 (2026-08-22) — `adt_activate(object_type='fugr')` **`activated: true`**
     dondu; ayni anda ham `POST /activation` **`activationExecuted="false"`** diyordu,
     `adt_inactive_objects` objeyi LISTEDE gosteriyordu ve ATC "contains inactive parts"
     diyordu. Uc bagimsiz kanit aracin donusunu YALANLIYORDU.
     ⚠ Klasik yolun tek dogrulamasi `_content_readback`'ti; o da yalniz
     `_SOURCE_BASED_TYPES` + bu seansta push kaydi olan objeler icin kosar
     ⇒ `fugr` / XML-DDIC / salt re-activate HIC dogrulanmiyordu.

  C) kayitlar #20 + #49 (2026-08-19 / 08-21) — `adt_post_shell` `400`/`500` raporladi,
     kabuk DORT objede de FIILEN YARATILMISTI. ⛔ RETRY TUZAGI: `ok:false` gorunce
     dogal refleks tekrar denemektir; idempotent olmayan bir tipte MUKERRER YARATMA.
     ⇒ "exit 0 != kanit"in TERS YUZU: **`ok:false` da kanit degildir.**

BU FIXTURE'IN OLCTUGU DEGISMEZLER:
  1. Yanlis uca sorulan DDIC objesi kardes uctan BULUNUR (iki yon de: tabl<->structure).
  2. Aktivasyon iddiasi BAGIMSIZ worklist sondasiyla carpisirsa SAHTE-OK yakalanir.
  3. Create hatasi sonrasi VARLIK olculur; obje varsa RETRY acikca yasaklanir.
  4. ⭐ UCUNCU DEGER: sonda kosamazsa sonuc "temiz"e DEGIL `None`+uyariya duser
     ("olculemedi" != "dogrulandi", "bakamadim" != "yok").             [SILINMEZ CAPA]
  5. ⭐ KONTROL GRUPLARI: dogru/temiz vakalar BOZULMAZ ve fazladan HTTP uretmez.
                                                                       [SILINMEZ CAPA]
⛔ (4) ve (5) SILINMEZ. (4) kaldirilirsa fix fail-open'a doner ve kayitlarin koku geri
gelir. (5) kaldirilirsa test asiri-siki olur: gercek aktivasyonu/gercek yoklugu da
reddeder ve her SAP yazma turunu bloklar.

SAP GEREKTIRMEZ: HTTP katmani + SAPClient sahtelenir; olculen sey KARAR MANTIGI.
Mutasyon modu:  python run.py --mutasyon   (fix'i BELLEKTE soker, KIRMIZI bekler)
"""
from __future__ import annotations

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

# Yan etkiler GERCEK projeye degil gecici koke yazilsin (korpus koşum dizinine
# gore sonuc degistirmesin).
_TMP = tempfile.mkdtemp(prefix="sahte_sonuc_")
os.environ["CLAUDE_PROJECT_DIR"] = _TMP
Path(_TMP, "project.yaml").write_text(
    "sap_profile: s4_private\nrelease: '2025'\nsource_root: SOURCE_CODES\n", encoding="utf-8")

# ── MCP SDK KOPRUSU (test harness'i; FastMCP test kapsaminda DEGIL) ─────────────
try:  # pragma: no cover - ortam kosullu
    import mcp.server.fastmcp  # type: ignore  # noqa: F401
except Exception:
    _mcp = types.ModuleType("mcp")
    _srv = types.ModuleType("mcp.server")
    _fast = types.ModuleType("mcp.server.fastmcp")

    class _FastMCP:
        def __init__(self, *a, **k):
            pass

        def tool(self, *a, **k):
            def _dek(fn):
                return fn
            return _dek

    _fast.FastMCP = _FastMCP                       # type: ignore[attr-defined]
    _srv.fastmcp = _fast                           # type: ignore[attr-defined]
    _mcp.server = _srv                             # type: ignore[attr-defined]
    sys.modules.setdefault("mcp", _mcp)
    sys.modules.setdefault("mcp.server", _srv)
    sys.modules.setdefault("mcp.server.fastmcp", _fast)

try:
    from mcp_servers.sap_adt.tools import atom
except Exception as exc:                           # pragma: no cover
    raise SystemExit(f"[fixture-hatasi] atom yuklenemedi (sessiz gecme YOK): {exc}")


DDL = "@EndUserText.label : 'X'\ndefine structure ztest_s_x {\n  key mandt : mandt;\n}\n"
FG = "ZSD001_FG_ORNEK"          # ⚠ core PUBLIC repo — yalniz jenerik ornek ad

_IOC = ('xmlns:ioc="http://www.sap.com/abapxml/inactiveCtsObjects" '
        'xmlns:adtcore="http://www.sap.com/adt/core"')


def _worklist(*adlar: str) -> str:
    govde = "".join(
        '<ioc:entry><ioc:object ioc:deleted="false" ioc:user="TESTUSER">'
        '<ioc:ref adtcore:uri="/sap/bc/adt/functions/groups/%s" adtcore:type="FUGR/F" '
        'adtcore:name="%s"/></ioc:object></ioc:entry>' % (a.lower(), a) for a in adlar)
    return ('<?xml version="1.0" encoding="UTF-8"?><ioc:inactiveObjects %s>%s'
            '</ioc:inactiveObjects>' % (_IOC, govde))


class _Yanit:
    def __init__(self, kod, metin):
        self.status_code, self.text = kod, metin


class _SegSession:
    """Uc SEGMENTINE gore farkli yanit veren sahte session; URL'leri KAYDEDER."""

    def __init__(self, kural, varsayilan=(404, "")):
        self.kural, self.varsayilan = kural, varsayilan
        self.istenen: list[str] = []

    def get(self, url, **kw):
        self.istenen.append(url)
        for seg, kg in self.kural.items():
            if seg in url:
                return _Yanit(*kg)
        return _Yanit(*self.varsayilan)


class _Adt:
    def __init__(self, s):
        self.url = "https://sap.example.test:44300"
        self.session = s


class _Client:
    def __init__(self, kural, aktive=None, olustur=None, varsayilan=(404, "")):
        self.session = _SegSession(kural, varsayilan)
        self.adt_client = _Adt(self.session)
        self._aktive, self._olustur = aktive, olustur

    # DDIC XML yolu / genel yol: bu korpusta HIC kullanilmamali
    def get_ddic_object(self, t, n):
        raise AssertionError("XML yoluna dusuldu: %s/%s" % (t, n))

    def download_object(self, name, object_type="class", save_local=True):
        raise AssertionError("genel yola dusuldu")

    def get_object_metadata(self, name, object_type="class"):
        raise AssertionError("genel yola dusuldu (metadata)")

    def activate_object(self, name, object_type="class"):
        print("[OK] Object activated successfully")
        return self._aktive

    def create_object(self, object_type, name, package, description, transport, **kw):
        print(self._olustur)                       # gercek sap_client: hatayi BASAR,
        return None                                # istisnayi YUTAR, None doner


def _kur(c):
    atom._get_client = lambda _c=c: _c
    atom._record_active_binding = lambda _c=None: None
    atom.get_active_tier = lambda: "DEV"


def _cagir(fn, **kw):
    """Cokmeyi FAIL'e degil OLCUME cevir (mutasyon-dostu)."""
    try:
        return fn(**kw)
    except Exception as exc:                       # noqa: BLE001
        return {"ok": None, "_exc": "%s: %s" % (type(exc).__name__, exc)}


def _uclar(c):
    return [u.split("/sap/bc/adt/")[-1].rsplit("/source/main", 1)[0] for u in c.session.istenen]


def main() -> int:
    S: list[tuple[str, bool, str]] = []

    def ekle(ad, kosul, detay):
        S.append((ad, bool(kosul), str(detay)))

    T, ST = "ddic/tables", "ddic/structures"

    # ══ A) kayit #8 — tabl <-> structure kardes-uc ═══════════════════════════
    c = _Client({T: (404, ""), ST: (200, DDL)}); _kur(c)
    r = _cagir(atom.adt_get, name="ZTEST_S_X", object_type="tabl", include_source=True)
    ekle("A1 YAPI `tabl` ile soruldu -> exists:true (eski davranis: false)",
         r.get("exists") is True and r.get("ok") is True,
         "exists=%s ok=%s %s" % (r.get("exists"), r.get("ok"), r.get("_exc", "")))
    ekle("A1b kardes uc GERCEKTEN cagrildi (once tables, sonra structures)",
         _uclar(c) == ["ddic/tables/ztest_s_x", "ddic/structures/ztest_s_x"], str(_uclar(c)))
    ekle("A1c kanonik tip bildirildi + kaynak DOGRU objeden okundu",
         r.get("resolved_type") == "structure" and r.get("sibling_probe") == "checked_found"
         and "define structure" in str(r.get("source") or ""),
         "resolved=%s probe=%s" % (r.get("resolved_type"), r.get("sibling_probe")))
    ekle("A1d `type` cagiranin verdigi deger olarak KALDI (sozlesme sabit)",
         r.get("type") == "tabl", "type=%s" % r.get("type"))

    c = _Client({ST: (404, ""), T: (200, DDL)}); _kur(c)
    r = _cagir(atom.adt_get, name="ZTEST_T_X", object_type="structure", include_source=True)
    ekle("A2 TERS yon: `structure` ile TABLO soruldu -> bulundu",
         r.get("exists") is True and r.get("resolved_type") == "table",
         "exists=%s resolved=%s" % (r.get("exists"), r.get("resolved_type")))

    # KONTROL GRUBU [SILINMEZ]: dogru uc -> fallback HIC kosmamali
    c = _Client({T: (200, DDL), ST: (200, DDL)}); _kur(c)
    r = _cagir(atom.adt_get, name="ZTEST_T_X", object_type="tabl", include_source=True)
    ekle("A3 KONTROL dogru uc -> tek istek, fallback KOSMADI, uyari YOK",
         r.get("exists") is True and _uclar(c) == ["ddic/tables/ztest_t_x"]
         and "sibling_probe" not in r and "warning" not in r,
         "uclar=%s probe=%s" % (_uclar(c), r.get("sibling_probe")))

    # KONTROL GRUBU [SILINMEZ]: gercekten YOK -> exists:false KORUNUR + delil
    c = _Client({T: (404, ""), ST: (404, "")}); _kur(c)
    r = _cagir(atom.adt_get, name="ZTEST_YOK", object_type="tabl", include_source=True)
    ekle("A4 KONTROL iki ucta da 404 -> exists:false KORUNDU + probed_endpoints delili",
         r.get("ok") is True and r.get("exists") is False
         and r.get("sibling_probe") == "checked_absent"
         and r.get("probed_endpoints") == [T, ST],
         "exists=%s probe=%s probed=%s" % (r.get("exists"), r.get("sibling_probe"),
                                           r.get("probed_endpoints")))

    # UCUNCU DEGER [SILINMEZ]: kardes uc olculemedi -> yokluk beyani DARALTILIR
    c = _Client({T: (404, ""), ST: (500, "patladi")}); _kur(c)
    r = _cagir(atom.adt_get, name="ZTEST_S_X", object_type="tabl", include_source=True)
    ekle("A5 ⭐ kardes uc 500 -> 'unavailable' + YARATMA yasagi uyarisi ('bakamadim' != 'yok')",
         str(r.get("sibling_probe", "")).startswith("unavailable")
         and "YARATMA" in str(r.get("warning") or ""),
         "probe=%s warning=%s" % (r.get("sibling_probe"), "VAR" if r.get("warning") else "YOK"))

    # ══ B) kayit #70 — aktivasyon readback ══════════════════════════════════
    WL = "/activation/inactiveobjects"
    c = _Client({WL: (200, _worklist(FG))}, aktive=True); _kur(c)
    r = _cagir(atom.adt_activate, name=FG, object_type="fugr")
    ekle("B1 SAHTE-OK yakalandi (alt katman true dedi, obje HALA worklist'te)",
         r.get("ok") is False and r.get("activated") is False
         and r.get("error") == "activation_not_executed",
         "ok=%s activated=%s error=%s %s" % (r.get("ok"), r.get("activated"),
                                             r.get("error"), r.get("_exc", "")))
    ekle("B1b kanit alanlari dolu + worklist ucu gercekten cagrildi",
         r.get("activation_verified") is False
         and [h["name"] for h in (r.get("still_inactive") or [])] == [FG]
         and any(WL in u for u in c.session.istenen),
         "verified=%s still=%s" % (r.get("activation_verified"), r.get("still_inactive")))

    # KONTROL GRUBU [SILINMEZ]: gercek aktivasyon BOZULMAMALI
    c = _Client({WL: (200, _worklist())}, aktive=True); _kur(c)
    r = _cagir(atom.adt_activate, name=FG, object_type="fugr")
    ekle("B2 KONTROL worklist bos -> ok/activated TRUE korundu (asiri-siki DEGIL)",
         r.get("ok") is True and r.get("activated") is True
         and r.get("activation_verified") is True and "error" not in r,
         "ok=%s activated=%s verified=%s" % (r.get("ok"), r.get("activated"),
                                             r.get("activation_verified")))

    # 3. BAGLAM: worklist'te BASKA obje inaktif -> bizimki dogrulanir (asiri-yakalama yok)
    c = _Client({WL: (200, _worklist("ZSD001_FG_BASKA"))}, aktive=True); _kur(c)
    r = _cagir(atom.adt_activate, name=FG, object_type="fugr")
    ekle("B3 3.BAGLAM baska obje inaktif -> bizimki ok:true (isim esleme DAR)",
         r.get("ok") is True and r.get("activation_verified") is True,
         "ok=%s verified=%s still=%s" % (r.get("ok"), r.get("activation_verified"),
                                         r.get("still_inactive")))

    # UCUNCU DEGER [SILINMEZ]
    c = _Client({WL: (500, "patladi")}, aktive=True); _kur(c)
    r = _cagir(atom.adt_activate, name=FG, object_type="fugr")
    ekle("B4 ⭐ sonda 500 -> activation_verified=None + 'KANITLANMADI' uyarisi",
         r.get("activation_verified") is None
         and str(r.get("activation_probe", "")).startswith("unavailable")
         and "KANITLANMADI" in str(r.get("warning") or ""),
         "verified=%s probe=%s" % (r.get("activation_verified"), r.get("activation_probe")))

    # Maliyet capasi: zaten "olmadi" diyorsa sonda KOSMAZ
    c = _Client({WL: (200, _worklist(FG))}, aktive=False); _kur(c)
    r = _cagir(atom.adt_activate, name=FG, object_type="fugr")
    ekle("B5 activated=false iken sonda KOSMADI (gereksiz HTTP yok)",
         r.get("activated") is False and "activation_verified" not in r
         and not any(WL in u for u in c.session.istenen),
         "verified=%s istekler=%s" % (r.get("activation_verified"), c.session.istenen))

    # `fugr` aktivasyon URI'si (also= atomik co-activate yolu icin)
    ekle("B6 _activation_uri('fugr') / ('functiongroup') cozuluyor (eskiden None)",
         atom._activation_uri(FG, "fugr") == "/sap/bc/adt/functions/groups/%s" % FG.lower()
         and atom._activation_uri(FG, "functiongroup") == atom._activation_uri(FG, "fugr"),
         repr(atom._activation_uri(FG, "fugr")))

    # ══ C) kayitlar #20 + #49 — post_shell varlik sondasi ═══════════════════
    def shell(hata, exists):
        c = _Client({}, olustur=hata); _kur(c)
        _orig = atom.adt_get
        atom.adt_get = ((lambda **k: {"ok": False, "error": "unreachable"}) if exists == "hata"
                        else (lambda **k: {"ok": True, "exists": bool(exists)}))
        try:
            return _cagir(atom.adt_post_shell, object_type="class", name="ZCL_SD001_ORNEK",
                          package="ZSD001_CLC", transport="XXXK900001", description="Ornek")
        finally:
            atom.adt_get = _orig

    r = shell("\n[ERROR] [500] Failed to create CLAS/OC", True)
    ekle("C1 500 raporlandi AMA obje VAR -> exists_after=true + RETRY YASAGI",
         r.get("ok") is False and r.get("exists_after") is True
         and "TEKRAR YARATMAYA CALISMA" in str(r.get("message") or ""),
         "ok=%s exists_after=%s error=%s" % (r.get("ok"), r.get("exists_after"), r.get("error")))

    r = shell("\n[ERROR] [400] ExceptionResourceAlreadyExists", True)
    ekle("C2 'zaten var' AYRI donus koduna cikti (already_exists)",
         r.get("error") == "already_exists" and r.get("exists_after") is True,
         "error=%s exists_after=%s" % (r.get("error"), r.get("exists_after")))

    r = shell('\n[ERROR] [400] adtcore:descriptionTextLimit="60"', False)
    ekle("C3 GERCEK 400 (metin siniri) sahte-400'den AYRILDI",
         r.get("error") == "description_too_long" and r.get("exists_after") is False
         and "KISALT" in str(r.get("message") or ""),
         "error=%s exists_after=%s" % (r.get("error"), r.get("exists_after")))

    r = shell("\n[ERROR] [500] Failed to create CLAS/OC", "hata")
    ekle("C4 ⭐ sonda kosamadi -> exists_after=None + 'KOR RETRY YAPMA'",
         r.get("exists_after") is None
         and str(r.get("exists_probe", "")).startswith("unavailable")
         and "KOR RETRY YAPMA" in str(r.get("message") or ""),
         "exists_after=%s probe=%s" % (r.get("exists_after"), r.get("exists_probe")))

    # KONTROL GRUBU [SILINMEZ]: basari yolu bozulmadi (+ object_url artik doluyor)
    class _Ok(_Client):
        def __init__(self):
            super().__init__({})

        def create_object(self, **kw):
            print("[OK] Object created successfully")
            return "/sap/bc/adt/oo/classes/zcl_sd001_ornek"

    _kur(_Ok())
    r = _cagir(atom.adt_post_shell, object_type="class", name="ZCL_SD001_ORNEK",
               package="ZSD001_CLC", transport="XXXK900001", description="Ornek")
    ekle("C5 KONTROL basari yolu: ok:true + object_url DOLU (eskiden DAIMA None)",
         r.get("ok") is True
         and r.get("object_url") == "/sap/bc/adt/oo/classes/zcl_sd001_ornek"
         and "exists_after" not in r,
         "ok=%s object_url=%s" % (r.get("ok"), r.get("object_url")))

    gecen = sum(1 for _, ok, _ in S if ok)
    for ad, ok, detay in S:
        print("  [%s] %s -> %s" % ("OK" if ok else "FAIL", ad, detay))
    print("\n%d/%d OK" % (gecen, len(S)))
    return 0 if gecen == len(S) else 1


# ── MUTASYON MODU ────────────────────────────────────────────────────────────
# Fix'i BELLEKTE soker (dosyaya/git'e DOKUNMAZ -> komsu korpusu kirletmez) ve
# korpusun KIRMIZI dondugunu olcer. "KURULAMADI" != "KACTI": mutasyon kurulamazsa
# ucuncu deger basilir.
_MUTASYONLAR = [
    ("M1 #8 fix SOKULDU: kardes-uc haritasi bosaltildi",
     lambda a: setattr(a, "_DDL_KARDES_SEG", {})),
    ("M2 #8 YANLIS kardes: her uc kendine eslenir",
     lambda a: setattr(a, "_DDL_KARDES_SEG",
                       {"ddic/tables": ("ddic/tables", "table"),
                        "ddic/structures": ("ddic/structures", "structure")})),
    ("M3 #70 fix SOKULDU: readback DAIMA 'temiz' der (eski kor-guven)",
     lambda a: setattr(a, "_aktivasyon_readback",
                       lambda c, ad: (True, "checked_active", []))),
    ("M4 #70 fugr URI segmenti SOKULDU",
     lambda a: [a._ACTIVATION_URI_SEG.pop(k, None) for k in ("fugr", "functiongroup")]),
    ("M5 #20/#49 varlik sondasi SOKULDU",
     lambda a: setattr(a, "_varlik_sondasi", lambda n, t: (None, "unavailable:mut"))),
    ("M6 #20/#49 hata siniflandirmasi SOKULDU",
     lambda a: setattr(a, "_CREATE_HATA_IMZALARI", ())),
]


def _mutasyon() -> int:
    import copy
    kotu = []
    for ad, mut in _MUTASYONLAR:
        yedek = {k: copy.deepcopy(getattr(atom, k, None)) for k in
                 ("_DDL_KARDES_SEG", "_ACTIVATION_URI_SEG", "_CREATE_HATA_IMZALARI",
                  "_aktivasyon_readback", "_varlik_sondasi")}
        try:
            mut(atom)
        except Exception as exc:                   # noqa: BLE001
            print("  [KURULAMADI] %s -> %s" % (ad, exc))
            kotu.append(ad)
            continue
        finally_rc = None
        try:
            finally_rc = main()
        finally:
            for k, v in yedek.items():
                if v is not None:
                    setattr(atom, k, v)
        durum = "YAKALANDI" if finally_rc else "⛔ KACTI"
        print("--> [%s] exit=%s -> %s\n" % (ad, finally_rc, durum))
        if not finally_rc:
            kotu.append(ad)
    print("MUTASYON OZETI: %d/%d yakalandi" % (len(_MUTASYONLAR) - len(kotu), len(_MUTASYONLAR)))
    if kotu:
        print("  YAKALANAMAYAN/KURULAMAYAN: %s" % ", ".join(kotu))
    return 1 if kotu else 0


if __name__ == "__main__":
    sys.exit(_mutasyon() if "--mutasyon" in sys.argv else main())
