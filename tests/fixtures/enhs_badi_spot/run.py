#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""enhs_badi_spot fixture — DEV_CORE #413: BAdI enhancement spot (ENHS/XSB) + BAdI tanimi.

NEDEN VAR (2026-11-08)
  Cekirdekte enhancement spot / BAdI tanimi yazan arac YOKTU. Canli olcum (bir gelistirme
  sistemi, SAP_BASIS 758) uc tuzak gosterdi: ① PUT TAM BELGEDIR — gonderilmeyen filtre sunucuda
  SILINIR ⇒ belge GET'ten kurulmazsa her guncelleme veri kaybettirir ② hic aktive edilmemis spotta
  `?version=active` 200 + `adtcore:version="active"` + INAKTIF icerik doner ⇒ surum alani aktiflik
  kaniti DEGIL ③ worklist spot'u `ENHS/XS` + `.../enhsxs/<ad>` ile listeler, aktivasyon istegi
  `ENHS/XSB` + `.../enhsxsb/<ad>` ⇒ URI/tam-tip ile eslestiren sonda inaktif spot'u GOREMEZ.
  `canli/` = olculen readback + kabul edilmis PUT belgesi (adlar ZSD001 ornegine, kimlik
  alanlari yer tutucuya cevrildi; yapi/sira/bayt bicimi aynen).

VEKTORLER (SAP YOK: gercek `SAPADTClient` + oturuma takilan SAHTE HTTP adaptoru; istek listesi kanit)
  S  ayristir/kur: S1 olculen readback -> model, sunucu eklentileri tolere ·
     S2 kur(ayristir(readback)) == olculen kabul edilmis PUT belgesi (bayt-esit)
  G  ADR 0005-A + ad siniri: G1 standart spot · G2 standart BAdI adi · G3 31 karakter spot
     (30 gecer — G3b) · G4 lib yazma katmani (CLI'siz) · G5a CLI masterSystem=SAP ·
     G5b lib masterSystem=SAP · G6 sunucudaki belgede standart adli tanim · G7 bildirilmis
     namespace kabul · G8 bildirilmemis namespace red
  P  tam belge: P1 yalniz kisa metin degisir, fallback/ornek/filtre/kontrol KORUNUR ·
     P2 ayni spottaki ikinci tanim korunur
  R  kaldirma: R1 --remove-filter · R2 --remove-fallback-class · R3 olmayan filtre -> PUT yok
  L  kilit: L1 PUT 400 -> unlock · L2 PUT istisna -> unlock · L3 kilit yok -> PUT yok ·
     L4 LOCK -> PUT -> UNLOCK sirasi
  A  aktivasyon hukmu: A1 activationExecuted=true ama worklist'te -> AKTIF DEGIL (surum tuzagi
     acik) · A2 yalniz-generation + worklist'te -> AKTIF DEGIL · A3 worklist 500 ->
     DOGRULANAMADI · A4 mutlu yol · A5 istek tipi ENHS/XSB · W1 hedef eslesir / W2 komsu ad eslesmez
  E  kacis/UTF-8: E1 `& < > "` + ğüşıöçİ iyi bicimli + geri okunur · E2 PUT baytlari UTF-8
  K  K1 sunucu filtreyi dusururse cikis 1 · M1 modellenmeyen eleman -> PUT yok ·
     F1 olculmemis filtre tipi -> PUT yok · C1 yaratma sirasi · C2 paketsiz yaratma -> POST yok ·
     T1 transportsuz yazma -> istek yok
  O  coklu tanim + govde sirasi (SAP kaynagi `CL_ENH_ADT_BADI_DEF_CONT_SVC->SET_DATA_TO_TOOL`,
     canlida tetiklenmedi): O1 CLI yeni tanim sonda, canli tanim aynen · O2 lib [yeni, canli] ->
     PUT [canli, yeni] · O3 hepsi yeni + canlida tanim var -> sira_tuzagi, PUT yok ·
     SP1 spec 2 tanim tek PUT, ucuncu tanim aynen · SP2 --spec + --badi -> istek yok
  U  U1/U2 `--coklu-kullanim evet|hayir` -> singleUse false|true (TERS esleme) · U3 sunucu
     `enhs:usages` doldurur: PUT'ta yok, kiyas disi
  A6 activationExecuted=true + worklist bos AMA surumsuz GET inactive -> AKTIF DEGIL
     (`?version=active` yanki yapar) · A7 surumsuz GET okunamadi -> DOGRULANAMADI · F2 bos filtre adi
  T  duzeltme turu 1 (bagimsiz kontrol): L5 okuma ile kilit arasinda modellenmeyen alan -> kilit
     alti GET yakalar · L6 araya giren degisiklik -> taban_degisti · L7 lib: canli belgede
     modellenmeyen -> kilit yok · L8 RequestException disi PUT istisnasi sizmaz · L9 taban
     zorunlu · CW1/CW2 --cwd projesinin customer_namespaces'i ad denetiminden ONCE · CW3 yaratma
     SAPValidationError -> cikis 2 · D1 --dry-run transport'suz yalniz GET · D2/D3 var olan
     spot'ta --description farkliysa red · N1 onlyConstantFilterValues="true" korunur · N2 baska
     deger bicimi modellenmeyen
  Sahte surum modeli (olculen, 758 + 816): `?version=active` daima "active"; `?version=inactive`
  bekleyen yoksa "active"; yalniz SURUMSUZ GET gercek durumu verir.

KULLANIM
  python tests/fixtures/enhs_badi_spot/run.py                   # taban (exit 0)
  python tests/fixtures/enhs_badi_spot/run.py --mutasyon-<ad>   # tek mutasyon (KIPLER)
  Mutasyon cikisi (run_battery karar tablosu): ilan edilen kume TAM dustu -> 1 · sapma -> 2 ·
  capa != 1 kez / mutant derlenmedi / alt surec sayi vermedi -> 3.
"""
from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
import xml.etree.ElementTree as ET

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

BURASI = Path(__file__).resolve().parent
REPO = BURASI.parents[2]
if not (REPO / "scripts" / "sap_adt_lib.py").is_file():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")
CANLI = BURASI / "canli"

_KUM = tempfile.mkdtemp(prefix="enhs_badi_")
Path(_KUM, ".conn_adt").write_bytes(b"ADT_SAP_URL=https://sahte.invalid\nADT_SAP_CLIENT=000\n")
Path(_KUM, "project.yaml").write_text(
    "sap_profile: s4_private\nrelease: '2025'\nsource_root: SOURCE_CODES\n"
    "customer_namespaces: [\"/ABCD/\"]\n", encoding="utf-8")
os.environ["CLAUDE_PROJECT_DIR"] = _KUM
for _v in ("CLAUDE_CWD", "INIT_CWD", "COPILOT_CWD", "ADT_SAP_DEBUG", "SAP_ADT_DEBUG"):
    os.environ.pop(_v, None)
os.environ["ADT_SAP_URL"] = "https://sahte.invalid"
os.chdir(_KUM)
for _p in (REPO / "scripts" / "utils", REPO / "scripts"):
    sys.path.insert(0, str(_p))

TR = "<TR_ISTEK>"
SPOT = "ZSD001_ES_BADI_A"
BADI = "ZSD001_BADI_A"
KOL = "/sap/bc/adt/enhancements/enhsxsb"
ADTCORE = "http://www.sap.com/adt/core"
ENHS = "http://www.sap.com/adt/enhancements/enhs"
GUSIOC = "ğüşıöçİ"

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


# ─────────────────────────────────────────────────────────────────────────────
# SAHTE SUNUCU — olculen davranis: tam-belge PUT, kilit nesne URL'inde, worklist ENHS/XS
# ─────────────────────────────────────────────────────────────────────────────
def _tanim(ad=BADI, kisa="Test 413 BAdI tanımı", fallback="ZCL_SD001_BADI_A_FB",
           ornek="ZCL_SD001_BADI_A_EX", filtreler=(("ULKE", "C", "Ülke", "LAND"),
                                                   ("SAYI", "I", "Sayısal deneme", None)),
           ek="", tek="true"):
    p = ['<enhs:badiDefinition enhs:name="%s" enhs:shorttext="%s" enhs:singleUse="%s" '
         'enhs:useFallbackClass="%s" enhs:filterLimitation="false" enhs:contextMode="N" '
         'enhs:amdp="false" enhs:internalUse="false"><enhs:interface adtcore:uri="/sap/bc/adt/oo/'
         'interfaces/zif_sd001_badi_a" adtcore:type="INTF/OI" adtcore:name="ZIF_SD001_BADI_A"/>'
         % (ad, kisa, tek, "true" if fallback else "false")]
    if fallback:
        p.append('<enhs:defaultClass adtcore:uri="/sap/bc/adt/oo/classes/%s" adtcore:type="CLAS/OC" '
                 'adtcore:name="%s"/>' % (fallback.lower(), fallback))
    if ornek:
        p.append('<enhs:sampleClasses><enhs:sampleClass adtcore:uri="/sap/bc/adt/oo/classes/%s" '
                 'adtcore:type="CLAS/OC" adtcore:name="%s"/></enhs:sampleClasses>' % (ornek.lower(), ornek))
    if filtreler:
        p.append("<enhs:filters>")
        for n, t, k, c in filtreler:
            if c:
                p.append('<enhs:filter enhs:filterName="%s" enhs:filterType="%s" enhs:shorttext="%s">'
                         '<enhs:filterCheck xsi:type="enhcore:DictionaryCheck" xmlns:xsi="http://www.w3.'
                         'org/2001/XMLSchema-instance" xmlns:enhcore="http://www.sap.com/abapsource/'
                         'enhancementscore"><enhcore:checkObject adtcore:uri="/sap/bc/adt/ddic/dataelements/'
                         '%s" adtcore:type="DTEL/DE" adtcore:name="%s"/></enhs:filterCheck></enhs:filter>'
                         % (n, t, k, c.lower(), c))
            else:
                p.append('<enhs:filter enhs:filterName="%s" enhs:filterType="%s" enhs:shorttext="%s"/>'
                         % (n, t, k))
        p.append("</enhs:filters>")
    p.append(ek + "</enhs:badiDefinition>")
    return "".join(p)


def _belge(spot=SPOT, tanimlar=None):
    tanimlar = [_tanim()] if tanimlar is None else tanimlar
    ic = ("<enhs:badiDefinitions>%s</enhs:badiDefinitions>" % "".join(tanimlar)
          if tanimlar else "<enhs:badiDefinitions/>")
    return ('<?xml version="1.0" encoding="UTF-8"?><enhs:objectData xmlns:enhs="%s" xmlns:adtcore="%s" '
            'xmlns:enhcore="http://www.sap.com/abapsource/enhancementscore" adtcore:name="%s" '
            'adtcore:type="ENHS/XSB" adtcore:description="Test 413 BAdI noktası (%s)" '
            'adtcore:language="TR" adtcore:masterLanguage="TR"><adtcore:packageRef adtcore:name="$TMP"/>'
            '<enhs:contentCommon enhs:toolType="BADI_DEF"/><enhs:contentSpecific><enhs:badiTechnology>'
            '%s</enhs:badiTechnology></enhs:contentSpecific></enhs:objectData>'
            % (ENHS, ADTCORE, spot, GUSIOC, ic))


def _wl_girdi(ad, tip="ENHS/XS", yol="enhancements/enhsxs"):
    return ('<ioc:entry><ioc:object ioc:user="SAP_USER_A" ioc:deleted="false"><ioc:ref '
            'adtcore:uri="/sap/bc/adt/%s/%s" adtcore:type="%s" adtcore:name="%s"/></ioc:object>'
            '<ioc:transport/></ioc:entry>' % (yol, ad.lower(), tip, ad))


def _wl(*girdiler):
    return ('<?xml version="1.0" encoding="utf-8"?><ioc:inactiveObjects xmlns:ioc="http://www.sap.com/'
            'abapxml/inactiveCtsObjects" xmlns:adtcore="%s">%s</ioc:inactiveObjects>'
            % (ADTCORE, "".join(girdiler)))


YABANCI_WL = _wl_girdi("ZCL_SD001_YABANCI", "CLAS/OC", "oo/classes")
AKT_TAM = ('<?xml version="1.0" encoding="utf-8"?><chkl:messages xmlns:chkl="http://www.sap.com/abapxml/'
           'checklist"><chkl:properties checkExecuted="true" activationExecuted="true" '
           'generationExecuted="true"/></chkl:messages>')
AKT_GEN = AKT_TAM.replace('checkExecuted="true" activationExecuted="true"',
                          'checkExecuted="false" activationExecuted="false"')
LOCK_GOVDE = ('<?xml version="1.0" encoding="utf-8"?><asx:abap version="1.0" xmlns:asx="http://www.sap.com/'
              'abapxml"><asx:values><DATA><LOCK_HANDLE>SAHTE-KILIT-0001</LOCK_HANDLE><CORRNR/><CORRUSER/>'
              '<CORRTEXT/><IS_LOCAL>X</IS_LOCAL><IS_LINK_UP/><MODIFICATION_SUPPORT/><SCOPE_MESSAGES/>'
              '</DATA></asx:values></asx:abap>')
EXC400 = ('<?xml version="1.0" encoding="utf-8"?><exc:exception xmlns:exc="http://www.sap.com/abapxml/types/'
          'communicationframework"><namespace id="com.sap.adt"/><type id="ExceptionResourceInvalid"/>'
          '<message lang="TR">sahte 400</message></exc:exception>')


def _utf8_mi(b):
    try:
        b.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


class Sunucu:
    """Durumlu sahte ADT. `spotlar` = istemcinin GONDERDIGI belge (sunucu bicimi GET'te eklenir)."""

    def __init__(self, spotlar=None, **ayar):
        self.spotlar = {k.lower(): v for k, v in (spotlar or {}).items()}
        self.ayar = {"master_system": "XYZ", "lock_durum": 200, "put_durum": 200,
                     "put_istisna": False, "akt_govde": AKT_TAM, "wl_spot": False,
                     "wl_durum": 200, "readback_bozucu": None, "ek_kok": "",
                     "akt_aktiflestirir": True, "bekleyen_baslangic": False, "surumsuz_durum": 200,
                     "usages": False, "kilit_aninda": None}
        self.ayar.update(ayar)
        self.bekleyen = {k: self.ayar["bekleyen_baslangic"] for k in self.spotlar}
        self.istekler: list = []
        self.put_sayisi = 0

    def sunucu_bicimi(self, govde, surum):
        g = govde.replace("<enhs:objectData ", '<enhs:objectData adtcore:responsible="SAP_USER_A" '
                          'adtcore:masterSystem="%s" adtcore:version="%s" ' % (self.ayar["master_system"], surum), 1)
        g = g.replace("<enhs:badiDefinition ", '<enhs:badiDefinition enhs:documentationId="" '
                      'enhs:customLogicRegistered="false" ')
        if self.ayar["usages"]:      # olculen: sunucu doldurur (ornek sinif kullanimi), istemci GONDERMEZ
            g = g.replace('<enhs:contentCommon enhs:toolType="BADI_DEF"/>',
                          '<enhs:contentCommon enhs:toolType="BADI_DEF"><enhs:usages><enhcore:referencedObject '
                          'enhcore:program_id="R3TR" enhcore:element_usage="USEO"/></enhs:usages>'
                          '</enhs:contentCommon>', 1)
        if self.ayar["ek_kok"]:
            g = g.replace("</enhs:badiDefinition>", self.ayar["ek_kok"] + "</enhs:badiDefinition>", 1)
        return g

    def yanit(self, request):
        import requests
        from requests.structures import CaseInsensitiveDict
        u = urlsplit(request.url)
        yol, q, m = u.path, parse_qs(u.query), request.method.upper()
        govde_b = request.body if isinstance(request.body, bytes) else (request.body or "").encode("utf-8")
        self.istekler.append((m, yol, {k: v[0] for k, v in q.items()}, govde_b))
        durum, govde, bas = 404, "<sahte>bulunamadi</sahte>", {}
        if (request.headers.get("X-CSRF-Token") or "").lower() == "fetch":
            durum, govde, bas = 200, "<sahte/>", {"X-CSRF-Token": "SAHTE-CSRF"}
        elif yol in ("/sap/bc/adt/locks", "/sap/bc/adt/core/objectlock"):
            durum = 404
        elif q.get("_action") == ["LOCK"]:
            durum = self.ayar["lock_durum"]
            govde = LOCK_GOVDE if durum == 200 else "<sahte>kilit yok</sahte>"
            if durum == 200 and self.ayar["kilit_aninda"] and yol.startswith(KOL + "/"):
                # baska bir oturum okuma ile kilit ARASINDA yazdi (TOCTOU)
                kad = unquote(yol[len(KOL) + 1:]).lower()
                self.spotlar[kad] = self.ayar["kilit_aninda"](self.spotlar[kad])
        elif q.get("_action") == ["UNLOCK"]:
            durum, govde = 200, ""
        elif yol == KOL and m == "POST":
            b = govde_b.decode("utf-8")
            ad = re.search(r'adtcore:name="([^"]+)"', b).group(1).lower()
            self.spotlar[ad] = b
            self.bekleyen[ad] = True
            durum, govde, bas = 201, b, {"Location": KOL + "/" + ad}
        elif yol.startswith(KOL + "/"):
            ad = unquote(yol[len(KOL) + 1:]).lower()
            if m == "GET" and ad in self.spotlar and "version" not in q and self.ayar["surumsuz_durum"] != 200:
                durum, govde = self.ayar["surumsuz_durum"], "<html>hata</html>"
            elif m == "GET" and ad in self.spotlar:
                # OLCULEN (758 + 816): ?version=active daima "active" YANKILAR; ?version=inactive
                # bekleyen yoksa "active" der; yalniz SURUMSUZ GET gercek durumu verir.
                gercek = "inactive" if self.bekleyen.get(ad) else "active"
                surum = "active" if q.get("version") == ["active"] else gercek
                g = self.sunucu_bicimi(self.spotlar[ad], surum)
                if self.put_sayisi and self.ayar["readback_bozucu"]:
                    g = self.ayar["readback_bozucu"](g)
                durum, govde, bas = 200, g, {"Content-Type": "application/vnd.sap.adt.enh.enhs.v2+xml"}
            elif m == "PUT":
                if isinstance(self.ayar["put_istisna"], BaseException):
                    raise self.ayar["put_istisna"]
                if self.ayar["put_istisna"]:
                    raise requests.ConnectionError("sahte baglanti koptu")
                if "lockHandle" not in q:
                    durum, govde = 400, EXC400
                elif self.ayar["put_durum"] != 200:
                    durum, govde = self.ayar["put_durum"], EXC400
                elif not _utf8_mi(govde_b):
                    durum, govde = 400, EXC400          # UTF-8 olmayan govde: sunucu reddeder
                elif ad in self.spotlar:
                    self.spotlar[ad] = govde_b.decode("utf-8")
                    self.bekleyen[ad] = True
                    self.put_sayisi += 1
                    durum, govde = 200, self.spotlar[ad]
        elif yol == "/sap/bc/adt/activation" and m == "POST":
            durum, govde = 200, self.ayar["akt_govde"]
            if self.ayar["akt_govde"] == AKT_TAM and self.ayar["akt_aktiflestirir"]:
                self.bekleyen = {k: False for k in self.bekleyen}
        elif yol == "/sap/bc/adt/activation/inactiveobjects":
            girdi = [YABANCI_WL] + ([_wl_girdi(SPOT)] if self.ayar["wl_spot"] else [])
            durum = self.ayar["wl_durum"]
            govde = _wl(*girdi) if durum == 200 else "<html>500</html>"
        r = requests.Response()
        r.status_code, r.reason, r.url, r.request, r.encoding = durum, "SAHTE", request.url, request, "utf-8"
        r._content = (govde or "").encode("utf-8")
        r.headers = CaseInsensitiveDict(bas)
        return r

    def say(self, metot=None, ek=None):
        return sum(1 for m, y, q, _ in self.istekler
                   if (metot is None or m == metot) and (ek is None or ek(y, q)))

    def putlar(self):
        return [b.decode("utf-8", "replace") for m, y, q, b in self.istekler if m == "PUT" and "lockHandle" in q]

    def unlock_var(self):
        return self.say("POST", lambda y, q: q.get("_action") == "UNLOCK") >= 1

    def lock_var(self):
        return self.say("POST", lambda y, q: q.get("_action") == "LOCK") >= 1


def _istemci(L, sunucu):
    from requests.adapters import BaseAdapter

    class _Ad(BaseAdapter):
        def send(self, request, **kw):
            return sunucu.yanit(request)

        def close(self):
            pass

    c = L.SAPADTClient(url="https://sahte.invalid", user="SAP_USER_A", password="x", client="000",
                       language="TR")
    for on in ("https://", "http://"):
        c.session.mount(on, _Ad())
    return c


def _cli(P, L, argv, sunucu):
    c = _istemci(L, sunucu)
    rc, exc, cikti = _sessiz(P.calistir, argv, client=c)
    if exc is not None:
        return ("COKTU:%s:%s" % (type(exc).__name__, exc)), cikti
    return rc, cikti


def _model(L, xml_metin):
    return L.enhs_belgesi_ayristir(xml_metin.encode("utf-8"))


def _tanim_bul(model, ad):
    return next((t for t in model["tanimlar"] if t["name"] == ad), None)


def _put_model(L, s):
    p = s.putlar()
    return _model(L, p[-1]) if p else None


def _yaz(BADI_=BADI, *ek):
    return ["--spot", SPOT, "--transport", TR, "--badi", BADI_] + list(ek)


# ─────────────────────────────────────────────────────────────────────────────
def bolum_s(L, P):
    m = L.enhs_belgesi_ayristir((CANLI / "readback_aktif.xml").read_bytes())
    t = _tanim_bul(m, BADI) or {}
    ekle("S1 olculen readback -> model; sunucu eklentileri tolere (modellenmeyen bos)",
         m["modellenmeyen"] == [] and t.get("defaultClass") == "ZCL_SD001_BADI_A_FB"
         and t.get("sampleClasses") == ["ZCL_SD001_BADI_A_EX"]
         and t.get("filters") == [{"name": "ULKE", "type": "C", "shorttext": "Ülke (güncel)", "check": "LAND"}]
         and m["spot"]["masterSystem"] == "XYZ" and "contentCommon/usages" in m["sunucu_ek"], m)
    kabul = (CANLI / "put_kabul.xml").read_text(encoding="utf-8").strip()
    ekle("S2 kur(ayristir(readback)) == olculen kabul edilmis PUT belgesi (bayt-esit)",
         L.enhs_belgesi_kur(m) == kabul, L.enhs_belgesi_kur(m)[:200])


def bolum_g(L, P):
    s = Sunucu({SPOT: _belge()})
    rc, _ = _cli(P, L, ["--spot", "ES_STANDART_X", "--transport", TR, "--badi", BADI, "--shorttext", "x"], s)
    ekle("G1 standart spot adi -> cikis 2, SIFIR istek", rc == 2 and not s.istekler, (rc, len(s.istekler)))
    s = Sunucu({SPOT: _belge()})
    rc, _ = _cli(P, L, _yaz("BADI_STANDART", "--shorttext", "x"), s)
    ekle("G2 standart BAdI adi -> cikis 2, SIFIR istek", rc == 2 and not s.istekler, (rc, len(s.istekler)))
    uzun = "Z" + "X" * 30
    s = Sunucu({uzun: _belge(uzun)})
    rc, _ = _cli(P, L, ["--spot", uzun, "--transport", TR, "--badi", BADI, "--shorttext", "x"], s)
    ekle("G3 31 karakterlik spot -> cikis 2, SIFIR istek", rc == 2 and not s.istekler, (rc, len(s.istekler)))
    h = L.enhs_ad_denetimi("Z" + "X" * 29, [BADI])
    ekle("G3b 30 karakter siniri gecer (ad denetimi bos)", h == [], h)
    s = Sunucu({"es_standart_x": _belge("ES_STANDART_X")})
    c = _istemci(L, s)
    w, exc, _ = _sessiz(c.write_enhancement_spot, "ES_STANDART_X", _model(L, _belge("ES_STANDART_X")), TR,
                        taban=_model(L, _belge("ES_STANDART_X")))
    ekle("G4 lib yazma katmani: standart spot -> hata ad_denetimi, SIFIR istek",
         exc is None and not w["ok"] and str(w["hata"]).startswith("ad_denetimi") and not s.istekler,
         (exc, w, len(s.istekler)))
    s = Sunucu({SPOT: _belge()}, master_system="SAP")
    rc, _ = _cli(P, L, _yaz(BADI, "--shorttext", "x"), s)
    ekle("G5a CLI: masterSystem=SAP -> cikis 2, kilit/PUT YOK",
         rc == 2 and not s.lock_var() and not s.putlar(), (rc, [i[:2] for i in s.istekler]))
    s = Sunucu({SPOT: _belge()}, master_system="SAP")
    c = _istemci(L, s)
    w, exc, _ = _sessiz(c.write_enhancement_spot, SPOT, _model(L, _belge()), TR,
                        taban=_model(L, s.spotlar[SPOT.lower()]))
    ekle("G5b lib: masterSystem=SAP -> hata standart_obje, kilit/PUT YOK",
         exc is None and str((w or {}).get("hata")).startswith("standart_obje")
         and not s.lock_var() and not s.putlar(), (exc, w))
    s = Sunucu({SPOT: _belge(tanimlar=[_tanim(), _tanim(ad="BADI_STANDART", filtreler=())])})
    c = _istemci(L, s)
    w, exc, _ = _sessiz(c.write_enhancement_spot, SPOT, _model(L, _belge()), TR,
                        taban=_model(L, s.spotlar[SPOT.lower()]))
    ekle("G6 sunucudaki belgede standart adli tanim -> hata mevcut_belge_ad_denetimi, PUT YOK",
         exc is None and str((w or {}).get("hata")).startswith("mevcut_belge_ad_denetimi")
         and not s.putlar(), (exc, w))
    h = L.enhs_ad_denetimi("/ABCD/ES_X", ["/ABCD/BADI_X"])
    ekle("G7 bildirilmis namespace (/ABCD/) kabul", h == [], h)
    h = L.enhs_ad_denetimi("/QQQ/ES_X", [])
    ekle("G8 bildirilmemis namespace (/QQQ/) red", len(h) == 1 and "namespace-kayitsiz" in h[0], h)


def bolum_p(L, P):
    s = Sunucu({SPOT: _belge()})
    rc, cikti = _cli(P, L, _yaz(BADI, "--shorttext", "Yeni kısa metin"), s)
    pm = _put_model(L, s)
    t = _tanim_bul(pm, BADI) if pm else None
    ekle("P1 yalniz kisa metin: fallback/ornek/filtreler/kontrol PUT'ta KORUNUR, cikis 0",
         rc == 0 and t is not None and t["shorttext"] == "Yeni kısa metin"
         and t["defaultClass"] == "ZCL_SD001_BADI_A_FB" and t["useFallbackClass"] == "true"
         and t["sampleClasses"] == ["ZCL_SD001_BADI_A_EX"]
         and [(f["name"], f["type"], f["check"]) for f in t["filters"]] == [("ULKE", "C", "LAND"), ("SAYI", "I", None)],
         (rc, t, cikti[-300:]))
    s = Sunucu({SPOT: _belge(tanimlar=[_tanim(), _tanim(ad="ZSD001_BADI_B", kisa="İkinci", filtreler=())])})
    rc, _ = _cli(P, L, _yaz(BADI, "--shorttext", "x"), s)
    pm = _put_model(L, s)
    ikinci = _tanim_bul(pm, "ZSD001_BADI_B") if pm else None
    ekle("P2 ayni spottaki ikinci tanim PUT'ta KORUNUR",
         rc == 0 and ikinci is not None and ikinci["shorttext"] == "İkinci"
         and ikinci["defaultClass"] == "ZCL_SD001_BADI_A_FB", (rc, ikinci))


def bolum_r(L, P):
    s = Sunucu({SPOT: _belge()})
    rc, _ = _cli(P, L, _yaz(BADI, "--remove-filter", "SAYI"), s)
    pm = _put_model(L, s)
    t = _tanim_bul(pm, BADI) if pm else None
    ekle("R1 --remove-filter SAYI: PUT'ta yalniz ULKE (kontroluyle)",
         rc == 0 and t is not None and [(f["name"], f["check"]) for f in t["filters"]] == [("ULKE", "LAND")],
         (rc, t))
    s = Sunucu({SPOT: _belge()})
    rc, _ = _cli(P, L, _yaz(BADI, "--remove-fallback-class"), s)
    pm = _put_model(L, s)
    t = _tanim_bul(pm, BADI) if pm else None
    ekle("R2 --remove-fallback-class: useFallbackClass=false + defaultClass yok, digerleri korunur",
         rc == 0 and t is not None and t["useFallbackClass"] == "false" and t["defaultClass"] is None
         and len(t["filters"]) == 2 and "<enhs:defaultClass" not in s.putlar()[-1], (rc, t))
    s = Sunucu({SPOT: _belge()})
    rc, _ = _cli(P, L, _yaz(BADI, "--remove-filter", "YOKFILTRE"), s)
    ekle("R3 olmayan filtreyi kaldirma -> cikis 2, kilit/PUT YOK",
         rc == 2 and not s.lock_var() and not s.putlar(), (rc, [i[:2] for i in s.istekler]))


def _etiket(m, y, q):
    if q.get("_action") in ("LOCK", "UNLOCK"):
        return q["_action"]
    if y == "/sap/bc/adt/activation":
        return "AKT"
    if y == "/sap/bc/adt/activation/inactiveobjects":
        return "WL"
    if y == KOL and m == "POST":
        return "YARAT"
    return m


def _sira(s, beklenen):
    i = 0
    for e in [_etiket(m, y, q) for m, y, q, _ in s.istekler]:
        if i < len(beklenen) and e == beklenen[i]:
            i += 1
    return i == len(beklenen)


def bolum_l(L, P):
    s = Sunucu({SPOT: _belge()}, put_durum=400)
    rc, cikti = _cli(P, L, _yaz(BADI, "--shorttext", "x"), s)
    ekle("L1 PUT 400 -> UNLOCK gonderildi, cikis 1, aktivasyon YOK",
         rc == 1 and s.lock_var() and s.unlock_var()
         and not s.say("POST", lambda y, q: y == "/sap/bc/adt/activation"), (rc, cikti[-200:]))
    s = Sunucu({SPOT: _belge()}, put_istisna=True)
    c = _istemci(L, s)
    w, exc, _ = _sessiz(c.write_enhancement_spot, SPOT, _model(L, _belge()), TR,
                        taban=_model(L, s.spotlar[SPOT.lower()]))
    ekle("L2 PUT istisnasi -> UNLOCK gonderildi, istisna sizmaz, lock_released True",
         exc is None and w and not w["ok"] and str(w["hata"]).startswith("put_istisna")
         and w["lock_released"] is True and s.unlock_var(), (exc, w))
    s = Sunucu({SPOT: _belge()}, lock_durum=404)
    rc, cikti = _cli(P, L, _yaz(BADI, "--shorttext", "x"), s)
    ekle("L3 kilit alinamadi -> PUT YOK, cikis 1",
         rc == 1 and not s.say("PUT"), (rc, [i[:2] for i in s.istekler][-6:], cikti[-200:]))
    s = Sunucu({SPOT: _belge()})
    rc, _ = _cli(P, L, _yaz(BADI, "--shorttext", "x"), s)
    ekle("L4 mutlu yol: LOCK -> PUT (lockHandle + corrNr) -> UNLOCK sirasi",
         rc == 0 and _sira(s, ["LOCK", "PUT", "UNLOCK"])
         and any(q.get("corrNr") == TR and q.get("lockHandle") == "SAHTE-KILIT-0001"
                 for m, y, q, b in s.istekler if m == "PUT"), rc)


def bolum_a(L, P):
    s = Sunucu({SPOT: _belge()}, wl_spot=True)
    rc, cikti = _cli(P, L, _yaz(BADI, "--shorttext", "x"), s)
    tuzak = _istemci(L, Sunucu({SPOT: _belge()})).get_enhancement_spot(SPOT, "active").text
    ekle("A1 activationExecuted=true AMA worklist'te ENHS/XS -> AKTIF DEGIL, cikis 1 (surum 'active' der)",
         rc == 1 and 'adtcore:version="active"' in tuzak and "aktivasyon olmadi" in cikti, (rc, cikti[-250:]))
    s = Sunucu({SPOT: _belge()}, wl_spot=True, akt_govde=AKT_GEN)
    ak, exc, _ = _sessiz(_istemci(L, s).activate_enhancement_spot, SPOT)
    ekle("A2 yalniz-generation + worklist'te -> aktif False", exc is None and ak and ak["aktif"] is False
         and bool(ak["kalan_inaktif"]) and ak["kalan_inaktif"][0]["type"] == "ENHS/XS", (exc, ak))
    s = Sunucu({SPOT: _belge()}, wl_durum=500)
    ak, exc, _ = _sessiz(_istemci(L, s).activate_enhancement_spot, SPOT)
    ekle("A3 worklist 500 -> aktif False + dogrulanamadi True", exc is None and ak and ak["aktif"] is False
         and ak["dogrulanamadi"] is True, (exc, ak))
    s = Sunucu({SPOT: _belge()})
    ak, exc, _ = _sessiz(_istemci(L, s).activate_enhancement_spot, SPOT)
    ekle("A4 mutlu yol (yabanci worklist girdisi var) -> aktif True", exc is None and ak and ak["aktif"] is True,
         (exc, ak))
    govdeler = [b.decode("utf-8") for m, y, q, b in s.istekler if y == "/sap/bc/adt/activation"]
    ekle("A5 aktivasyon istegi adtcore:type=ENHS/XSB + spot URI",
         bool(govdeler) and 'adtcore:type="ENHS/XSB"' in govdeler[0]
         and 'adtcore:uri="%s/%s"' % (KOL, SPOT.lower()) in govdeler[0], govdeler[:1])
    gird = L.aktivasyon_worklist_ayristir(_wl(YABANCI_WL, _wl_girdi(SPOT)))
    kalan = [g["name"] for g in L.aktivasyon_worklist_kalan(gird, L.enhs_worklist_hedefi(SPOT))]
    ekle("W1 enhs_worklist_hedefi ENHS/XS girdisini eslesir", kalan == [SPOT], kalan)
    gird = L.aktivasyon_worklist_ayristir(_wl(_wl_girdi(SPOT + "_T"), _wl_girdi(SPOT, "CLAS/OC", "oo/classes")))
    kalan = L.aktivasyon_worklist_kalan(gird, L.enhs_worklist_hedefi(SPOT))
    ekle("W2 komsu ad (_T) ve ayni adli ENHS-disi tip eslesmez", kalan == [], kalan)


def bolum_e(L, P):
    metin = 'A & B <c> "d" ' + GUSIOC
    s = Sunucu({SPOT: _belge()})
    rc, cikti = _cli(P, L, _yaz(BADI, "--shorttext", metin, "--filter", "ULKE", "C", metin), s)
    p = s.putlar()
    try:
        pm = _model(L, p[-1]) if p else None
        t = _tanim_bul(pm, BADI) if pm else None
    except ET.ParseError as exc:
        t = None
        cikti += " PARSE:%s" % exc
    ekle("E1 & < > \" + ğüşıöçİ: PUT iyi bicimli, kisa metinler geri okunur, readback esit",
         rc == 0 and t is not None and t["shorttext"] == metin and t["filters"][0]["shorttext"] == metin,
         (rc, t and t["shorttext"], cikti[-200:]))
    b = [b for m, y, q, b in s.istekler if m == "PUT"]
    ekle("E2 PUT baytlari UTF-8 (ğüşıöçİ bayt-esit)", bool(b) and GUSIOC.encode("utf-8") in b[-1],
         b[-1][:80] if b else None)


def bolum_k(L, P):
    def bozucu(g):
        return re.sub(r'<enhs:filter enhs:filterName="SAYI"[^>]*/>', "", g)
    s = Sunucu({SPOT: _belge()}, readback_bozucu=bozucu)
    rc, cikti = _cli(P, L, _yaz(BADI, "--shorttext", "x"), s)
    ekle("K1 sunucu SAYI filtresini dusururse readback kiyasi -> cikis 1",
         rc == 1 and "readback gonderilenle ayni DEGIL" in cikti, (rc, cikti[-250:]))
    s = Sunucu({SPOT: _belge()}, ek_kok="<enhs:bilinmeyenAlan/>")
    rc, cikti = _cli(P, L, _yaz(BADI, "--shorttext", "x"), s)
    ekle("M1 modellenmeyen eleman -> cikis 1, kilit/PUT YOK",
         rc == 1 and "modellemedigi" in cikti and not s.lock_var() and not s.say("PUT"), (rc, cikti[-250:]))
    s = Sunucu({SPOT: _belge()})
    rc, _ = _cli(P, L, _yaz(BADI, "--filter", "YENI", "S", "x"), s)
    ekle("F1 olculmemis filtre tipi S -> cikis 2, kilit/PUT YOK",
         rc == 2 and not s.lock_var() and not s.say("PUT"), rc)
    s = Sunucu({})
    rc, cikti = _cli(P, L, _yaz(BADI, "--package", "$TMP", "--description", "Yeni nokta " + GUSIOC,
                                "--interface", "ZIF_SD001_BADI_A", "--shorttext", "Yeni tanım"), s)
    yarat = [b.decode("utf-8") for m, y, q, b in s.istekler if y == KOL and m == "POST"]
    ekle("C1 yaratma: GET404 -> bos kabuk POST(corrNr) -> GET -> LOCK -> PUT -> UNLOCK -> AKT -> WL -> GET",
         rc == 0 and _sira(s, ["GET", "YARAT", "GET", "LOCK", "PUT", "UNLOCK", "AKT", "WL", "GET"])
         and bool(yarat) and "<enhs:badiDefinitions/>" in yarat[0]
         and any(q.get("corrNr") == TR for m, y, q, b in s.istekler if y == KOL and m == "POST"),
         (rc, [_etiket(m, y, q) for m, y, q, _ in s.istekler], cikti[-200:]))
    s = Sunucu({})
    rc, _ = _cli(P, L, _yaz(BADI, "--interface", "ZIF_SD001_X", "--shorttext", "x"), s)
    ekle("C2 spot yok + --package/--description yok -> cikis 2, POST YOK",
         rc == 2 and not s.say("POST", lambda y, q: y == KOL), rc)
    s = Sunucu({SPOT: _belge()})
    rc, _ = _cli(P, L, ["--spot", SPOT, "--badi", BADI, "--shorttext", "x"], s)
    ekle("T1 --transport yok (yazma) -> cikis 2, SIFIR istek", rc == 2 and not s.istekler, rc)


BADI_B = "ZSD001_BADI_B"
BADI_C = "ZSD001_BADI_C"


def _adlar(pm):
    return [t["name"] for t in pm["tanimlar"]] if pm else None


def bolum_o(L, P):
    """Coklu tanim + govde sirasi + coklu kullanim eslemesi + surumsuz GET + sunucu eki."""
    # O1 — CLI: canlida A varken yeni B eklenir -> govde A, B; A aynen tasinir
    s = Sunucu({SPOT: _belge()})
    rc, cikti = _cli(P, L, _yaz(BADI_B, "--interface", "ZIF_SD001_BADI_B", "--shorttext", "Yeni B"), s)
    pm = _put_model(L, s)
    a = _tanim_bul(pm, BADI) if pm else None
    ekle("O1 CLI yeni tanim: PUT sirasi [A, B] (canli once, yeni sonda), A aynen, cikis 0",
         rc == 0 and _adlar(pm) == [BADI, BADI_B] and a is not None
         and a["defaultClass"] == "ZCL_SD001_BADI_A_FB" and len(a["filters"]) == 2,
         (rc, _adlar(pm), cikti[-200:]))
    # O2 — lib: model [B(yeni), A(canli)] -> PUT [A, B]
    s = Sunucu({SPOT: _belge()})
    m = _model(L, _belge(tanimlar=[_tanim(ad=BADI_B, filtreler=()), _tanim()]))
    w, exc, _ = _sessiz(_istemci(L, s).write_enhancement_spot, SPOT, m, TR,
                        taban=_model(L, s.spotlar[SPOT.lower()]))
    pm = _put_model(L, s)
    ekle("O2 lib model [B yeni, A canli] -> PUT sirasi [A, B]",
         exc is None and w and w["ok"] and _adlar(pm) == [BADI, BADI_B], (exc, w and w.get("hata"), _adlar(pm)))
    # O3 — lib: govdedeki tanimlarin HICBIRI canlida yok, canlida tanim var -> RED, kilit/PUT YOK
    s = Sunucu({SPOT: _belge()})
    m = _model(L, _belge(tanimlar=[_tanim(ad=BADI_B, filtreler=())]))
    w, exc, _ = _sessiz(_istemci(L, s).write_enhancement_spot, SPOT, m, TR,
                        taban=_model(L, s.spotlar[SPOT.lower()]))
    ekle("O3 hepsi yeni + canlida tanim var -> hata sira_tuzagi, kilit/PUT YOK",
         exc is None and w and str(w.get("hata")).startswith("sira_tuzagi")
         and not s.lock_var() and not s.putlar(), (exc, w))
    # SP1 — spec: A guncelle + yeni C, canlida A + B -> tek PUT [A, B, C], B aynen, silme yok
    s = Sunucu({SPOT: _belge(tanimlar=[_tanim(), _tanim(ad=BADI_B, kisa="İkinci", filtreler=())])})
    spec_yolu = Path(_KUM, "spec_sp1.json")
    spec_yolu.write_text(
        '{"tanimlar": [{"badi": "%s", "shorttext": "A yeni"}, '
        '{"badi": "%s", "interface": "ZIF_SD001_BADI_C", "shorttext": "Yeni C", "coklu_kullanim": "evet", '
        '"filtreler": [{"ad": "ULKE", "tip": "C", "kisa": "Ülke", "dtel": "LAND"}]}]}' % (BADI, BADI_C),
        encoding="utf-8")
    rc, cikti = _cli(P, L, ["--spot", SPOT, "--transport", TR, "--spec", str(spec_yolu)], s)
    pm = _put_model(L, s)
    b, c, a = ((_tanim_bul(pm, x) if pm else None) for x in (BADI_B, BADI_C, BADI))
    ekle("SP1 spec 2 tanim tek PUT: sira [A, B, C], B aynen, C singleUse=false + filtre kontrolu, cikis 0",
         rc == 0 and len(s.putlar()) == 1 and _adlar(pm) == [BADI, BADI_B, BADI_C]
         and b is not None and b["shorttext"] == "İkinci" and a is not None and a["shorttext"] == "A yeni"
         and c is not None and c["singleUse"] == "false"
         and [(f["name"], f["check"]) for f in c["filters"]] == [("ULKE", "LAND")],
         (rc, _adlar(pm), cikti[-250:]))
    s = Sunucu({SPOT: _belge()})
    rc, _ = _cli(P, L, ["--spot", SPOT, "--transport", TR, "--spec", str(spec_yolu), "--badi", BADI], s)
    ekle("SP2 --spec + --badi birlikte -> cikis 2, SIFIR istek", rc == 2 and not s.istekler, rc)
    # U — coklu kullanim TERS esleme
    s = Sunucu({SPOT: _belge()})
    rc, _ = _cli(P, L, _yaz(BADI, "--coklu-kullanim", "evet"), s)
    pm = _put_model(L, s)
    ekle("U1 --coklu-kullanim evet -> PUT singleUse=\"false\"",
         rc == 0 and pm is not None and _tanim_bul(pm, BADI)["singleUse"] == "false", rc)
    s = Sunucu({SPOT: _belge(tanimlar=[_tanim(tek="false")])})
    rc, _ = _cli(P, L, _yaz(BADI, "--coklu-kullanim", "hayir"), s)
    pm = _put_model(L, s)
    ekle("U2 --coklu-kullanim hayir -> PUT singleUse=\"true\"",
         rc == 0 and pm is not None and _tanim_bul(pm, BADI)["singleUse"] == "true", rc)
    # U3 — sunucu enhs:usages doldurur: istemci GONDERMEZ, readback kiyasina girmez
    s = Sunucu({SPOT: _belge()}, usages=True)
    rc, cikti = _cli(P, L, _yaz(BADI, "--shorttext", "x"), s)
    p = s.putlar()
    ekle("U3 sunucu usages eklerse: cikis 0, PUT'ta usages YOK, kiyas disi bilgi satiri",
         rc == 0 and bool(p) and "usages" not in p[-1] and "contentCommon/usages" in cikti, (rc, cikti[-250:]))
    # A6 — activationExecuted=true + worklist bos AMA surumsuz GET inaktif -> AKTIF DEGIL
    s = Sunucu({SPOT: _belge()}, akt_aktiflestirir=False, bekleyen_baslangic=True)
    ak, exc, _ = _sessiz(_istemci(L, s).activate_enhancement_spot, SPOT)
    yanki = _istemci(L, s).get_enhancement_spot(SPOT, "active").text
    ekle("A6 akt=true + worklist bos + surumsuz GET inactive -> aktif False (?version=active 'active' der)",
         exc is None and ak and ak["aktif"] is False and ak["dogrulanamadi"] is False
         and ak["surumsuz_surum"] == "inactive" and 'adtcore:version="active"' in yanki, (exc, ak))
    # A7 — surumsuz GET okunamadi -> DOGRULANAMADI
    s = Sunucu({SPOT: _belge()}, surumsuz_durum=500)
    ak, exc, _ = _sessiz(_istemci(L, s).activate_enhancement_spot, SPOT)
    ekle("A7 surumsuz GET 500 -> aktif False + dogrulanamadi True",
         exc is None and ak and ak["aktif"] is False and ak["dogrulanamadi"] is True, (exc, ak))
    # F2 — bos filtre adi (SAP e037)
    s = Sunucu({SPOT: _belge()})
    rc, _ = _cli(P, L, _yaz(BADI, "--filter", " ", "C", "x"), s)
    ekle("F2 bos filtre adi -> cikis 2, kilit/PUT YOK", rc == 2 and not s.lock_var() and not s.putlar(), rc)


def bolum_t(L, P):
    """Duzeltme turu 1: kilit alti yeniden okuma (TOCTOU) · istisna sozlesmesi · --cwd sirasi ·
    --dry-run transport'suz · var olan spot'ta --description · yalniz-sabit-deger filtresi."""
    yabanci = lambda g: g.replace("</enhs:badiDefinition>", "<enhs:bilinmeyenAlan/></enhs:badiDefinition>", 1)  # noqa: E731
    s = Sunucu({SPOT: _belge()}, kilit_aninda=yabanci)
    rc, cikti = _cli(P, L, _yaz(BADI, "--shorttext", "x"), s)
    ekle("L5 okuma ile kilit arasinda modellenmeyen alan girer -> kilit alti GET yakalar, PUT YOK, UNLOCK, cikis 1",
         rc == 1 and "kilit_alti:modellenmeyen_alan" in cikti and not s.putlar() and s.unlock_var(),
         (rc, cikti[-250:]))
    baska = lambda g: g.replace('enhs:shorttext="İkinci"', 'enhs:shorttext="Başkası yazdı"', 1)  # noqa: E731
    s = Sunucu({SPOT: _belge(tanimlar=[_tanim(), _tanim(ad=BADI_B, kisa="İkinci", filtreler=())])},
               kilit_aninda=baska)
    rc, cikti = _cli(P, L, _yaz(BADI, "--shorttext", "x"), s)
    ekle("L6 okuma ile kilit arasinda ikinci tanim degisir -> taban_degisti, PUT YOK, UNLOCK, cikis 1",
         rc == 1 and "taban_degisti" in cikti and not s.putlar() and s.unlock_var(), (rc, cikti[-250:]))
    s = Sunucu({SPOT: _belge()}, ek_kok="<enhs:bilinmeyenAlan/>")
    w, exc, _ = _sessiz(_istemci(L, s).write_enhancement_spot, SPOT, _model(L, _belge()), TR,
                        taban=_model(L, _belge()))
    ekle("L7 lib dogrudan: canli belgede modellenmeyen alan -> hata modellenmeyen_alan, kilit/PUT YOK",
         exc is None and w and str(w.get("hata")).startswith("modellenmeyen_alan")
         and not s.lock_var() and not s.putlar(), (exc, w))
    s = Sunucu({SPOT: _belge()}, put_istisna=RuntimeError("sahte"))
    w, exc, _ = _sessiz(_istemci(L, s).write_enhancement_spot, SPOT, _model(L, _belge()), TR,
                        taban=_model(L, _belge()))
    ekle("L8 PUT'ta RequestException DISI istisna -> sizmaz, hata put_istisna:RuntimeError, UNLOCK",
         exc is None and w and w.get("hata") == "put_istisna:RuntimeError" and w["lock_released"] is True
         and s.unlock_var(), (exc, w))
    s = Sunucu({SPOT: _belge()})
    w, exc, _ = _sessiz(_istemci(L, s).write_enhancement_spot, SPOT, _model(L, _belge()), TR, taban=None)
    s2 = Sunucu({SPOT: _belge()})  # sekli eksik taban ('spot' anahtari yok): kilitten sonra KeyError sizmamali
    w2, exc2, _ = _sessiz(_istemci(L, s2).write_enhancement_spot, SPOT, _model(L, _belge()), TR,
                          taban={"tanimlar": []})
    ekle("L9 lib taban verilmedi ya da sekli eksik -> hata taban_yok, SIFIR istek",
         exc is None and w and str(w.get("hata")).startswith("taban_yok") and not s.istekler
         and exc2 is None and w2 and str(w2.get("hata")).startswith("taban_yok") and not s2.istekler,
         (exc, w, exc2, w2))
    # --cwd: ad denetimi hedef projenin customer_namespaces'ini okur (sira)
    b = tempfile.mkdtemp(prefix="enhs_badi_b_")
    Path(b, ".conn_adt").write_bytes(b"ADT_SAP_URL=https://sahte-b.invalid\nADT_SAP_CLIENT=000\n")
    Path(b, "project.yaml").write_text("sap_profile: s4_private\nrelease: '2025'\nsource_root: SOURCE_CODES\n"
                                       "customer_namespaces: [\"/EFGH/\"]\n", encoding="utf-8")
    try:
        s = Sunucu({"/EFGH/ES_X": _belge("/EFGH/ES_X")})
        rc, cikti = _cli(P, L, ["--cwd", b, "--spot", "/EFGH/ES_X", "--transport", TR, "--badi", "/EFGH/BADI_X",
                                "--interface", "ZIF_SD001_BADI_A", "--shorttext", "x"], s)
        ekle("CW1 --cwd projesinde bildirilmis /EFGH/ -> kabul, cikis 0", rc == 0, (rc, cikti[-250:]))
        s = Sunucu({"/ABCD/ES_X": _belge("/ABCD/ES_X")})
        rc, _ = _cli(P, L, ["--cwd", b, "--spot", "/ABCD/ES_X", "--transport", TR, "--badi", "/ABCD/BADI_X",
                            "--interface", "ZIF_SD001_BADI_A", "--shorttext", "x"], s)
        ekle("CW2 --cwd projesinde bildirilmemis /ABCD/ -> cikis 2, SIFIR istek", rc == 2 and not s.istekler,
             (rc, len(s.istekler)))
    finally:
        L.set_explicit_working_dir(_KUM)
        shutil.rmtree(b, ignore_errors=True)
    s = Sunucu({})
    c = _istemci(L, s)

    def _red(*a, **k):
        raise L.SAPValidationError("sahte yaratma reddi")
    c.create_enhancement_spot = _red
    rc, exc, cikti = _sessiz(P.calistir, _yaz(BADI, "--package", "$TMP", "--description", "Yeni",
                                              "--interface", "ZIF_SD001_BADI_A", "--shorttext", "x"), client=c)
    ekle("CW3 yaratma SAPValidationError -> cikis 2 (traceback YOK)", exc is None and rc == 2, (rc, exc))
    # --dry-run transport'suz · --description var olan spot'ta
    s = Sunucu({SPOT: _belge()})
    rc, cikti = _cli(P, L, ["--spot", SPOT, "--badi", BADI, "--shorttext", "x", "--dry-run"], s)
    ekle("D1 --dry-run --transport'suz -> cikis 0, yalniz GET (kilit/PUT/POST YOK)",
         rc == 0 and "[DRY-RUN]" in cikti and s.istekler and all(m == "GET" for m, y, q, _ in s.istekler),
         (rc, [i[:2] for i in s.istekler]))
    s = Sunucu({SPOT: _belge()})
    rc, cikti = _cli(P, L, _yaz(BADI, "--shorttext", "x", "--description", "Başka açıklama"), s)
    ekle("D2 var olan spot'ta farkli --description -> cikis 2, kilit/PUT YOK (sessizce yok sayilmaz)",
         rc == 2 and not s.lock_var() and not s.putlar(), (rc, cikti[-200:]))
    s = Sunucu({SPOT: _belge()})
    rc, _ = _cli(P, L, _yaz(BADI, "--shorttext", "x", "--description", "Test 413 BAdI noktası (%s)" % GUSIOC), s)
    ekle("D3 var olan spot'ta AYNI --description -> engel degil, cikis 0", rc == 0, rc)
    # yalniz-sabit-deger filtresi (BADI_FILTER-CONSTANT): GET'te yalniz ="true" olculdu
    eski = 'enhs:filterName="SAYI" enhs:filterType="I" enhs:shorttext="Sayısal deneme"/>'
    sabit = _belge().replace(eski, eski[:-2] + ' enhs:onlyConstantFilterValues="true"/>')
    s = Sunucu({SPOT: sabit})
    rc, cikti = _cli(P, L, _yaz(BADI, "--shorttext", "x"), s)
    pm = _put_model(L, s)
    t = _tanim_bul(pm, BADI) if pm else None
    ekle("N1 onlyConstantFilterValues=\"true\" okunur, PUT'ta AYNI filtrede korunur, readback esit, cikis 0",
         rc == 0 and t is not None
         and [(f["name"], f.get("onlyConstant")) for f in t["filters"]] == [("ULKE", None), ("SAYI", "true")]
         and 'enhs:shorttext="Sayısal deneme" enhs:onlyConstantFilterValues="true"' in s.putlar()[-1],
         (rc, t, cikti[-200:]))
    s = Sunucu({SPOT: _belge().replace(eski, eski[:-2] + ' enhs:onlyConstantFilterValues="false"/>')})
    rc, cikti = _cli(P, L, _yaz(BADI, "--shorttext", "x"), s)
    ekle("N2 olculmemis deger bicimi (=\"false\") -> modellenmeyen, kilit/PUT YOK, cikis 1",
         rc == 1 and "onlyConstantFilterValues=false" in cikti and not s.lock_var() and not s.putlar(),
         (rc, cikti[-200:]))


def main() -> int:
    import importlib
    mods = {}
    for ad in ("sap_adt_lib", "populate_badi_spot"):
        m, exc, _ = _sessiz(importlib.import_module, ad)
        if m is None:
            print(f"[fixture-hatasi] {ad} import edilemedi: {exc!r}")
            return 3
        mods[ad] = m
    L, P = mods["sap_adt_lib"], mods["populate_badi_spot"]
    for fn in (bolum_s, bolum_g, bolum_p, bolum_r, bolum_l, bolum_a, bolum_e, bolum_k, bolum_o, bolum_t):
        try:
            fn(L, P)
        except Exception as exc:                       # noqa: BLE001 — bolum cokmesi FAIL'dir
            ekle(f"{fn.__name__}-COKTU", False, f"{type(exc).__name__}: {exc}")
    for ad, ok, d in S:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         -> {d}"))
    n = sum(1 for _, ok, _ in S if ok)
    print(f"\n{n}/{len(S)} OK")
    os.chdir(str(REPO))
    shutil.rmtree(_KUM, ignore_errors=True)
    return 0 if n == len(S) else 1


# ─────────────────────────────────────────────────────────────────────────────
# MUTASYON — her kip TEK bir degismezi geri alir; dusmesi ILAN EDILEN kume TAM olmalidir.
# ─────────────────────────────────────────────────────────────────────────────
_LIB = "scripts/sap_adt_lib.py"
_CLI = "scripts/populate_badi_spot.py"
MUTASYONLAR = {
    "--mutasyon-ad-politikasi": (_LIB, "        if karar != 'musteri':\n", "        if False:\n",
                                 {"CW2", "G1", "G2", "G4", "G6", "G8"}),
    "--mutasyon-ad-siniri": (_LIB, "        if len(a) > sinir:\n", "        if False:\n", {"G3"}),
    "--mutasyon-cli-ad-katmani": (_CLI, "    hatalar = L.enhs_ad_denetimi(spot, adlar, root=root)\n",
                                  "    hatalar = []\n", {"CW2", "G1", "G2", "G3"}),
    "--mutasyon-yazma-ad-katmani": (
        _LIB, "        hatalar = enhs_ad_denetimi(spot, [t.get('name') for t in model.get('tanimlar') or []],\n"
              "                                   root=root)\n",
        "        hatalar = []\n", {"G4"}),
    "--mutasyon-mevcut-ad-katmani": (
        _LIB, "        hatalar = enhs_ad_denetimi(spot, [t.get('name') for t in m['tanimlar']], root=root)\n",
        "        hatalar = []\n", {"G6"}),
    "--mutasyon-lib-master-system": (
        _LIB, "        if (m['spot'].get('masterSystem') or '').upper() == 'SAP':\n",
        "        if False:\n", {"G5b"}),
    "--mutasyon-cli-master-system": (
        _CLI, "    if (model['spot'].get('masterSystem') or '').upper() == 'SAP':\n", "    if False:\n", {"G5a"}),
    "--mutasyon-tam-belge": (
        _LIB, "        t = tanimlar[sira[0]]\n",
        "        t = dict(ENHS_TANIM_VARSAYILAN, name=ad, shorttext=tanimlar[sira[0]].get('shorttext'),\n"
        "                 interface=tanimlar[sira[0]].get('interface'), defaultClass=None,\n"
        "                 sampleClasses=[], filters=[])\n"
        "        tanimlar[sira[0]] = t\n", {"K1", "N1", "P1", "R1", "R2"}),
    "--mutasyon-get-tabani": (_CLI, "            yeni, yapilan = L.enhs_tanim_uygula(model, d)\n",
                              "            yeni, yapilan = L.enhs_tanim_uygula(dict(model, tanimlar=[]), d)\n",
                              {"A1", "CW1", "D1", "D3", "E1", "E2", "K1", "L1", "L3", "L4", "L5", "L6", "N1", "O1", "P1", "P2", "R1", "R2", "U1", "U2", "U3"}),
    "--mutasyon-kaldirma": (_LIB, "        del t['filters'][konum[0]]\n", "        pass\n", {"R1"}),
    "--mutasyon-unlock-finally": (
        _LIB, "        finally:\n            sonuc['lock_released'] = bool(self.unlock_object(url, el))\n",
        "        except ZeroDivisionError:\n            raise\n"
        "        sonuc['lock_released'] = bool(self.unlock_object(url, el))\n", {"C1", "L1", "L2", "L4", "L5", "L6", "L8"}),
    "--mutasyon-kilitsiz-put": (
        _LIB, "        if el in ('NO_LOCK_SUPPORT', 'IMPLICIT_LOCK', None, ''):\n            # Kilitsiz",
        "        if False:\n            # Kilitsiz", {"L3"}),
    "--mutasyon-surum-hukmu": (
        _LIB, "        ok, sonda, kalan = aktivasyon_worklist_sondasi(self, hedef)\n",
        "        ok, sonda, kalan = ('adtcore:version=\"active\"' in (self.get_enhancement_spot(spot, 'active')"
        ".text or '')), 'surum', []\n", {"A1", "A2", "A3", "C1"}),
    "--mutasyon-worklist-hedefi": (
        _LIB, "    return [{'name': (spot or '').upper(), 'type': 'ENHS'}]\n",
        "    return [{'uri': enhs_spot_url(spot), 'name': (spot or '').upper(), 'type': ENHS_TIP}]\n", {"A1", "A2", "W1"}),
    "--mutasyon-dogrulanamadi-basari": (
        _LIB, "        return {'aktif': akt.get('success') is True and ok is True,\n",
        "        return {'aktif': akt.get('success') is True and ok is not False,\n", {"A3", "A7"}),
    "--mutasyon-aktivasyon-tipi": (
        _LIB, "        akt = self.activate_object((spot or '').upper(), url, object_type=ENHS_TIP)\n",
        "        akt = self.activate_object((spot or '').upper(), url)\n", {"A5"}),
    "--mutasyon-kacis": (_LIB, "    return '\"%s\"' % _esc('' if deger is None else str(deger), {'\"': '&quot;'})\n",
                         "    return '\"%s\"' % ('' if deger is None else str(deger))\n", {"E1"}),
    "--mutasyon-utf8": (_LIB, "                    data=govde.encode('utf-8'))\n            except Exception as exc:  # noqa: BLE001 — PUT",
                        "                    data=govde.encode('latin-1', 'replace'))\n            except Exception as exc:  # noqa: BLE001 — PUT",
                        {"A1", "C1", "CW1", "D3", "E1", "E2", "K1", "L4", "N1", "O1", "O2", "P1", "P2", "R1", "R2", "SP1", "U1", "U2", "U3"}),
    "--mutasyon-modellenmeyen": (_CLI, "    if model['modellenmeyen']:\n", "    if False:\n", {"M1"}),
    "--mutasyon-bilinmeyen-eleman": (_LIB, "        else:\n            m.append('%s/%s' % (yol, y))\n",
                                     "        else:\n            pass\n", {"L5", "L7", "M1"}),
    "--mutasyon-readback": (_CLI, "    fark = L.enhs_kiyasla(yeni, okunan)\n", "    fark = []\n", {"K1"}),
    "--mutasyon-filtre-tipi": (_LIB, "        if tip not in ENHS_FILTRE_TIPLERI:\n", "        if False:\n", {"F1"}),
    "--mutasyon-transport": (_CLI, "    if yazma and not a.dry_run and not a.transport:\n", "    if False:\n", {"T1"}),
    "--mutasyon-kilit-alti-get": (_LIB, "            taze, hata = self._enhs_yazilabilir_oku(spot, root)\n",
                                  "            taze, hata = mevcut, None\n", {"L5", "L6"}),
    "--mutasyon-taban-kiyasi": (_LIB, "            fark = enhs_kiyasla(taban, taze)\n", "            fark = []\n", {"L6"}),
    "--mutasyon-lib-modellenmeyen": (_LIB, "        if m['modellenmeyen']:\n", "        if False:\n", {"L5", "L7"}),
    "--mutasyon-put-istisna-genis": (
        _LIB, "            except Exception as exc:  # noqa: BLE001 — PUT istisnasi raporlanir, sizmaz\n",
        "            except requests.RequestException as exc:\n", {"L8"}),
    "--mutasyon-taban-zorunlu": (_LIB, "        if not isinstance(taban, dict) or 'tanimlar' not in taban or 'spot' not in taban:\n",
                                 "        if False:\n", {"L9"}),
    "--mutasyon-cwd-sirasi": (_CLI, "    if a.cwd:\n        # Ad denetimi hedef projenin",
                              "    if False:\n        # Ad denetimi hedef projenin", {"CW1", "CW2"}),
    "--mutasyon-yaratma-reddi": (_CLI, "        except L.SAPValidationError as exc:\n",
                                 "        except ZeroDivisionError as exc:\n", {"CW3"}),
    "--mutasyon-aciklama-sessiz": (
        _CLI, "        if a.description is not None and a.description != model['spot'].get('description'):\n",
        "        if False:\n", {"D2"}),
    "--mutasyon-sabit-filtre-kur": (_LIB, "                        bas += ' enhs:onlyConstantFilterValues=\"true\"'\n",
                                    "                        pass\n", {"N1"}),
    "--mutasyon-sabit-filtre-oku": (_LIB, "        if y == 'onlyConstantFilterValues' and v == 'true':\n",
                                    "        if False:\n", {"N1"}),
    "--mutasyon-sabit-filtre-deger": (_LIB, "        if y == 'onlyConstantFilterValues' and v == 'true':\n",
                                      "        if y == 'onlyConstantFilterValues':\n", {"N2"}),
    "--mutasyon-yeni-basa": (_LIB, "    return mevcutlar + yeniler, None\n", "    return yeniler + mevcutlar, None\n",
                             {"O1", "O2", "SP1"}),
    "--mutasyon-sira-reddi": (_LIB, "    if canli and tanimlar and not mevcutlar:\n", "    if False:\n", {"O3"}),
    "--mutasyon-surumsuz-get": (_LIB, "        r = adt.get_enhancement_spot(spot)\n",
                                "        r = adt.get_enhancement_spot(spot, 'active')\n", {"A6", "A7"}),
    "--mutasyon-surumsuz-hukum": (_LIB, "        elif surum != 'active' and ok is True:\n", "        elif False:\n",
                                  {"A6"}),
    "--mutasyon-surumsuz-okunamadi": (_LIB, "        if surum is None and ok is not False:\n", "        if False:\n",
                                      {"A7"}),
    "--mutasyon-coklu-kullanim-ters": (
        _LIB, "        return 'false'\n    if d == 'hayir':\n        return 'true'\n",
        "        return 'true'\n    if d == 'hayir':\n        return 'false'\n", {"SP1", "U1", "U2"}),
    "--mutasyon-diger-tanimlar": (
        _LIB, "    tanimlar = yeni['tanimlar']\n",
        "    tanimlar = yeni['tanimlar'] = [t for t in yeni['tanimlar'] if (t.get('name') or '').upper() == ad]\n",
        {"CW1", "O1", "P2", "SP1"}),
    "--mutasyon-usages-ek": (_LIB, "                    ek.append('contentCommon/usages')   # sunucu doldurur; GONDERILMEZ\n",
                             "                    m.append('contentCommon/usages')\n", {"S1", "U3"}),
    "--mutasyon-filtre-adi-bos": (_LIB, "        if not fa:\n            raise ValueError('filtre adi bos (SAP e037)')\n",
                                  "        if False:\n            raise ValueError('filtre adi bos (SAP e037)')\n", {"F2"}),
}
KIPLER = list(MUTASYONLAR)


def _mutasyon(kip) -> int:
    yol, eski, yeni, beklenen = MUTASYONLAR[kip]
    kok = Path(tempfile.mkdtemp(prefix="enhs_badi_kum_"))
    try:
        shutil.copytree(REPO / "scripts", kok / "scripts",
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
