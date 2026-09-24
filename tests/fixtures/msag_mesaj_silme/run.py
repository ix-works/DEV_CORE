#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""populate_message_class --delete: mesaj sinifindan TEK TEK mesaj silme korpusu (SAP'siz).

KOK (olculdu 2026-09-24, s4_private 2025): tam PUT govdesinden mesaji CIKARMAK SILMEZ —
SAP `CL_ADT_MC_RES_CONTROLLER=>DO_UPDATE`'teki "listede olmayani sil" dongusu YORUM
satirinda. Silme YALNIZ govdedeki `<mc:deletedmessages mc:msgno="NNN"/>` koleksiyonuyla
olur (ST `ST_ADT_MESSAGE_CLASS` -> `tt_deletedmessage` -> api `delete( iv_number = .. )`).
Canli kanit: 1 mesaj (229->228) sonra 16 mesaj tek PUT'ta (->212), kalanlar birebir.

Bu korpus araci SAHTE bir ADT sunucusuna karsi GERCEK giris noktasindan (`main()`) kosar.
Sahte sunucu SAP'nin olculmus davranisini taklit eder: govdede olmayan mesaja DOKUNMAZ,
yalniz `deletedmessages`'taki numarayi siler. Ayrica uc BOZUK sunucu kipi vardir
(`noop` = eski tam-PUT davranisi · `fazla` · `degistir`) — kapinin onlari yakaladigini olcer.

Senaryolar:
  S1   mutlu yol: --delete 006,011 -> rc 0, giden TAM {006,011}, tek PUT, kalanlar birebir
       (documented=true + tirnakli + &-li metin dahil), KAPSAM BEYANI basilir
  S2-S8  KORUMALAR — her biri rc 2 VE SAP'ye HICBIR yazma cagrisi (LOCK/PUT) gitmez:
       S2 bos oge "006,,011" (bos msgno SAP'de 000'i siler) · S3 "6" (3 hane degil)
       S4 canlida olmayan 999 · S5 tum sinif · S6 bos liste · S7 master dil != oturum dili
       S8 tekrar eden numara
  S9 ⭐ NEGATIF KONTROL — `noop` sunucu (PUT 200 ama hicbir sey silinmez = eski tam-PUT):
       rc 3 olmali. "PUT 200 == silindi" varsayan bir arac burada rc 0 verirdi.
  S10  `fazla` sunucu (istenmeyen mesaj da gider) -> rc 3
  S11  `degistir` sunucu (kalan bir metin degisir) -> rc 3
  S12  --dry-run: rc 0, LOCK/PUT YOK, govde dosyasi yazilir
  S13  3. BAGLAM (gorev-DISI, CSV kipi): tirnakli metin (`"`) gecerli XML uretir ve
       geri-ayristirinca AYNI metni verir (eski `xml_escape` tirnagi KACIRMIYORDU)
  S14  CSV kipi (yazma, sahte sunucu): canlida olup CSV'de olmayan mesaj icin UYARI basilir,
       govdede deletedmessages YOKTUR, sap-client/sap-language eski sabitler ('100'/'TR')
  S15  --delete + --messages-csv birlikte -> argparse hatasi (iki ayri kip)
  S16  --package canli paketle uyusmaz -> rc 2, yazma yok
  S17  ONCE okunamaz (HTTP 500) -> rc 2, yazma yok
  S18  PUT 500 -> rc 1 ve UNLOCK YINE gonderilir (finally)
  S19  SONRA okunamaz -> rc 3 ("olculemedi" != "tuttu")
  S20 ⭐ TOCTOU: LOCK aninda baskasi 002'yi degistirir -> rc 2, SIFIR PUT, 1 UNLOCK, 002'nin
       yeni metni korunur (koruma yokken bug-gate olcumu: rc 0 + 002 ESKI metne donuyordu)
  S21  kilit altinda yeniden okuma 500 -> rc 2, sifir PUT (olculemeyen = yazilmaz)
  S22  PUT gonderildikten sonra ag istisnasi -> rc 3 "elle dogrula" + KAPSAM + UNLOCK
  S23  SONRA okumasi istisna -> rc 3 + KAPSAM (traceback + rc 1 degil)
  S24  LOCK istisnasi (PUT gonderilmedi) -> rc 1 (yazilmadigi BILINIR, 3 degil)
  S25  TAB/LF/CR tasiyan metin: build_xml geri-ayristirma ayni + cok satirli canliyla silme rc 0
  U1-U4 katman-ici birim capalari (savunma derinligi: iki katman ayni korumayi tasir,
       her katman AYRI olculur — biri sokulunce digeri korpusu yesil tutmasin)
  U5   govde oz-denetimi (silme_govdesi_dogrula) KENDI BASINA: dort bozuk govde -> hata listesi

Mutasyonlar (her biri korpusu KIRMIZI yapmali; capa TAM BIR KEZ eslesmeli — CORE-07):
  M1 ayristirici bicim korumasi sokulur · M2 planlayici bicim korumasi sokulur
  M3 varlik korumasi · M4 tum-sinif korumasi · M5 dil korumasi · M6 kapi devre disi
  M7 oznitelik kacisi tumden geri alinir · M8 documented sabit 'false'a doner
  M9 deletedmessages mesajlardan ONCE yazilir · M10 populate hazir govdeyi yok sayar
  M11 CSV kipindeki UYARI sokulur · M12 kilit-alti yeniden okuma baglantisi kopar
  M13 govde oz-denetimi etkisiz · M14 kilit-alti kiyas sokulur · M15 'PUT gonderildi' izi
  dusurulur · M16 yalniz TAB/LF/CR kacisi geri alinir

Kosum: python tests/fixtures/msag_mesaj_silme/run.py     (exit 0 = PASS; 2 = DOGRULANAMADI)
"""
from __future__ import annotations

import io
import os
import re
import shutil
import stat
import sys
import tempfile
import types
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape as _esc

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[2]
SCRIPTS = CORE / "scripts"
PMC_PATH = SCRIPTS / "populate_message_class.py"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

_mod_refs: list = []   # GC-koruma: modulun import aninda kurdugu stdout wrapper'lari (B22/B25)

SINIF = "ZSD001_MSG"
PAKET = "ZSD001_CLC"
BASKA_PAKET = "ZSD000_CLC"
NS_MC = "http://www.sap.com/adt/MessageClass"
NS_CORE = "http://www.sap.com/adt/core"

# Canli benzeri baslangic durumu: msgno -> (metin, selfexp, documented)
# Bilerek zor metinler: `&1` yer tutucu, cift tirnak, `<`, Turkce karakter, documented=true.
BASLANGIC = {
    "000": ("&1 &2 &3 &4", "true", "false"),
    "001": ('Belge "&1" bulunamadı.', "false", "true"),
    "002": ("Miktar < 0 olamaz (&1).", "false", "false"),
    "006": ("Atıl mesaj — silinecek.", "true", "false"),
    "011": ("İkinci atıl mesaj; uzun metinli.", "false", "true"),
    "020": ("Şube & depo eşleşmedi.", "true", "false"),
}


def _sil(d: Path) -> None:
    def _ac(func, path, _exc):                       # noqa: ANN001
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass
    kw = {"onexc": _ac} if sys.version_info >= (3, 12) else {"onerror": _ac}
    try:
        shutil.rmtree(d, **kw)                       # type: ignore[arg-type]
    except Exception:
        shutil.rmtree(d, ignore_errors=True)


def _a(s: str) -> str:
    # SAP GET yaniti gibi: oznitelikte TAB/LF/CR sayisal referansla gelir (yoksa ET bosluga cevirir)
    return _esc(s, {'"': "&quot;", "\t": "&#9;", "\n": "&#10;", "\r": "&#13;"})


class _AgHatasi(Exception):
    """requests.ReadTimeout benzeri ag istisnasi (sahte)."""


class _Yanit:
    def __init__(self, durum: int, metin: str = "", basliklar: dict | None = None):
        self.status_code = durum
        self.text = metin
        self.headers = basliklar or {}


class _SahteOturum:
    """ADT'nin mesaj sinifi ucunu taklit eder. Her cagriyi `kayit`a yazar."""

    def __init__(self, sunucu: "_SahteSunucu"):
        self.s = sunucu

    def get(self, url, headers=None, params=None, **k):
        self.s.kayit.append(("GET", url, dict(params or {}), dict(headers or {})))
        if url.endswith("/sap/bc/adt/discovery"):
            return _Yanit(200, "<app:service/>", {"X-CSRF-Token": "sahte-csrf-token-0123456789"})
        if "/sap/bc/adt/messageclass/" in url:
            self.s.get_sayisi += 1
            if self.s.get_hata and self.s.get_sayisi in self.s.get_hata:
                return _Yanit(500, "<exc/>")
            if self.s.get_istisna and self.s.get_sayisi in self.s.get_istisna:
                raise _AgHatasi("Read timed out (GET)")
            return _Yanit(200, self.s.xml())
        return _Yanit(404, "")

    def post(self, url, params=None, headers=None, **k):
        p = dict(params or {})
        self.s.kayit.append(("POST", url, p, dict(headers or {})))
        if p.get("_action") == "LOCK":
            if self.s.lock_istisna:
                raise _AgHatasi("Connection reset (LOCK)")
            if self.s.lock_degistir:
                # TOCTOU: ONCE okumasindan SONRA, kilit alinirken baskasi 002'nin metnini degistirir
                t, s_, d = self.s.durum["002"]
                self.s.durum["002"] = (t + " [baskasi degistirdi]", s_, d)
            return _Yanit(200, "<asx:abap><asx:values><DATA><LOCK_HANDLE>HNDL0001</LOCK_HANDLE>"
                               "</DATA></asx:values></asx:abap>")
        return _Yanit(200, "")

    def put(self, url, params=None, headers=None, data=None, **k):
        self.s.kayit.append(("PUT", url, dict(params or {}), dict(headers or {})))
        govde = data.decode("utf-8") if isinstance(data, bytes) else data
        self.s.govdeler.append(govde)
        if self.s.put_hata:
            return _Yanit(500, "<exc/>")
        try:
            kok = ET.fromstring(govde)
        except ET.ParseError:
            return _Yanit(400, "<exc>XML parse error</exc>")   # bozuk govde -> 400
        # SAP'nin OLCULMUS davranisi: govdedeki mesaj eklenir/guncellenir; govdede OLMAYAN
        # mesaja DOKUNULMAZ; yalniz deletedmessages silinir.
        for m in kok.findall("{%s}messages" % NS_MC):
            no = m.get("{%s}msgno" % NS_MC)
            yeni = (m.get("{%s}msgtext" % NS_MC), m.get("{%s}selfexplainatory" % NS_MC),
                    m.get("{%s}documented" % NS_MC))
            if no not in self.s.durum or self.s.durum[no][0] != yeni[0]:
                self.s.durum[no] = yeni
        silinen = [d.get("{%s}msgno" % NS_MC) for d in kok.findall("{%s}deletedmessages" % NS_MC)]
        if self.s.kip == "gercek":
            for no in silinen:
                self.s.durum.pop(no or "000", None)      # bos msgno -> 000 (SAP kaynagi)
        elif self.s.kip == "fazla":
            for no in silinen:
                self.s.durum.pop(no, None)
            self.s.durum.pop("020", None)
        elif self.s.kip == "degistir":
            for no in silinen:
                self.s.durum.pop(no, None)
            t, s_, d = self.s.durum["002"]
            self.s.durum["002"] = (t + " (degisti)", s_, d)
        # kip == "noop": eski tam-PUT davranisi — hicbir sey silinmez, yine 200
        if self.s.put_istisna:
            # en kotu hal: sunucu isledi (silme GERCEKLESTI) ama yanit gelmedi
            raise _AgHatasi("Read timed out (PUT)")
        return _Yanit(200, "")


class _SahteSunucu:
    def __init__(self, kip="gercek", paket=PAKET, master="TR", get_hata=None, put_hata=False,
                 lock_degistir=False, put_istisna=False, get_istisna=None, lock_istisna=False,
                 ek=None):
        self.kip = kip
        self.paket = paket
        self.master = master
        self.durum = dict(BASLANGIC, **(ek or {}))
        self.lock_degistir = lock_degistir
        self.put_istisna = put_istisna
        self.get_istisna = set(get_istisna or ())
        self.lock_istisna = lock_istisna
        self.kayit: list = []
        self.govdeler: list = []
        self.get_sayisi = 0
        self.get_hata = set(get_hata or ())
        self.put_hata = put_hata

    def xml(self) -> str:
        # Gercek GET yanitinin bicimi: tek satir, oznitelik sirasi, atom:link cocuklari.
        msj = "".join(
            '<mc:messages mc:msgno="%s" mc:msgtext="%s" mc:selfexplainatory="%s" '
            'mc:documented="%s" mc:lastchangedby="&lt;SAP_USER&gt;" mc:lastmodified="2026-08-20" '
            'adtcore:name=""><atom:link href="/sap/bc/adt/messageclass/%s/messages/%s" '
            'rel="http://www.sap.com/adt/relations/messageclasses/messages" '
            'xmlns:atom="http://www.w3.org/2005/Atom"/></mc:messages>'
            % (n, _a(t), s, d, SINIF.lower(), n)
            for n, (t, s, d) in sorted(self.durum.items()))
        return ('<?xml version="1.0" encoding="utf-8"?><mc:messageClass '
                'adtcore:responsible="&lt;SAP_USER&gt;" adtcore:masterLanguage="%s" '
                'adtcore:masterSystem="DEV" adtcore:name="%s" adtcore:type="MSAG/N" '
                'adtcore:changedAt="2026-09-23T11:24:44Z" adtcore:version="active" '
                'adtcore:description="%s Paket Mesajlari" adtcore:language="%s" '
                'xmlns:mc="%s" xmlns:adtcore="%s"><adtcore:packageRef '
                'adtcore:uri="/sap/bc/adt/packages/%s" adtcore:type="DEVC/K" adtcore:name="%s"/>'
                '%s</mc:messageClass>'
                % (self.master, SINIF, SINIF, self.master, NS_MC, NS_CORE,
                   self.paket.lower(), self.paket, msj))

    def yazma_cagrilari(self) -> list:
        return [k for k in self.kayit
                if k[0] == "PUT" or (k[0] == "POST" and k[2].get("_action") == "LOCK")]


class _SahteClient:
    def __init__(self, sunucu: _SahteSunucu, dil="TR", client="100"):
        self.url = "https://sahte.invalid"
        self.session = _SahteOturum(sunucu)
        self.language = dil
        self.client = client
        self.temizlik = 0

    def _invalidate_csrf_cache(self):
        pass

    def clear_enqueue_lock(self, object_url=None, transport=None):
        self.temizlik += 1


def load(mut=None):
    """Kaynagi TAZE namespace'e yukler; mutasyon KAYNAK METNINE uygulanir (gercek __file__)."""
    src = PMC_PATH.read_text(encoding="utf-8")
    if mut:
        src = mut(src)
    saved_out, saved_err = sys.stdout, sys.stderr
    cop_out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    cop_err = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    sys.stdout, sys.stderr = cop_out, cop_err
    try:
        mod = types.ModuleType("populate_message_class")
        mod.__file__ = str(PMC_PATH)
        exec(compile(src, str(PMC_PATH), "exec"), mod.__dict__)
    finally:
        sys.stdout, sys.stderr = saved_out, saved_err
        _mod_refs.append((cop_out, cop_err))
    return mod


def kos(mod, argv: list, client: _SahteClient) -> tuple[int, str]:
    """GERCEK giris noktasi: main(). (rc, cikti). argparse hatasi -> rc = SystemExit kodu."""
    eski_argv, eski_out, eski_err = sys.argv[:], sys.stdout, sys.stderr
    tut = io.StringIO()
    sys.argv = ["populate_message_class.py"] + argv
    mod.SAPADTClient = lambda *a, **k: client
    sys.stdout = sys.stderr = tut
    try:
        rc = mod.main()
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else 2
    except Exception as e:           # cokme != FAIL: senaryo kirmizi olur, korpus cokmez
        rc = "COKTU:%s" % type(e).__name__
    finally:
        sys.stdout, sys.stderr = eski_out, eski_err
        sys.argv = eski_argv
    return rc, tut.getvalue()


def senaryolar(mod, tmp: Path) -> list:
    out = []

    def ekle(ad, kosul, detay=""):
        out.append((ad, bool(kosul), detay))

    def sil_argv(liste, *ek):
        return ["--name", SINIF, "--transport", "<TRANSPORT>", "--delete", liste,
                "--body-out", str(tmp / "govde.xml")] + list(ek)

    # --- S1 mutlu yol --------------------------------------------------------
    sv = _SahteSunucu()
    rc, cikti = kos(mod, sil_argv("006,011"), _SahteClient(sv))
    giden = set(BASLANGIC) - set(sv.durum)
    kalan_ayni = all(sv.durum.get(n) == v for n, v in BASLANGIC.items() if n not in {"006", "011"})
    put = [k for k in sv.kayit if k[0] == "PUT"]
    ekle("S1 mutlu yol: rc 0 + giden TAM {006,011} + tek PUT + kalanlar birebir + KAPSAM",
         rc == 0 and giden == {"006", "011"} and len(put) == 1 and kalan_ayni
         and "KAPI TUTTU" in cikti and "BAKILMAYAN" in cikti,
         "rc=%s giden=%s put=%d kalan_ayni=%s" % (rc, sorted(giden), len(put), kalan_ayni))
    if sv.govdeler:
        g = sv.govdeler[0]
        ekle("S1b govde: deletedmessages son mesajdan SONRA, bos msgno yok, documented korunur",
             g.rfind("<mc:messages ") < g.find("<mc:deletedmessages")
             and 'mc:msgno=""' not in g.split("<mc:deletedmessages", 1)[1]
             and re.search(r'mc:msgno="001"[^>]*mc:documented="true"', g) is not None,
             "govde sirasi/oznitelik")
    else:
        ekle("S1b govde: deletedmessages son mesajdan SONRA", False, "PUT govdesi YOK")

    # --- S2-S8 korumalar: rc 2 + HICBIR yazma cagrisi --------------------------
    for ad, liste, dil in (
            ("S2 bos oge '006,,011' (bos msgno 000'i siler)", "006,,011", "TR"),
            ("S3 3 hane degil '6'", "6", "TR"),
            ("S4 canlida olmayan '999'", "999", "TR"),
            ("S5 tum sinif", ",".join(sorted(BASLANGIC)), "TR"),
            ("S6 bos liste ''", "", "TR"),
            ("S7 master dil TR != oturum dili EN", "006", "EN"),
            ("S8 tekrar eden '006,006'", "006,006", "TR")):
        sv = _SahteSunucu()
        rc, cikti = kos(mod, sil_argv(liste), _SahteClient(sv, dil=dil))
        yz = sv.yazma_cagrilari()
        ekle("%s -> rc 2 + yazma YOK" % ad, rc == 2 and not yz and sv.durum == BASLANGIC,
             "rc=%s yazma=%d" % (rc, len(yz)))

    # --- S9-S11 bozuk sunucular: kapi yakalamali -----------------------------
    for ad, kip in (("S9 NEGATIF: noop sunucu (PUT 200, hicbir sey silinmez)", "noop"),
                    ("S10 fazla silen sunucu", "fazla"),
                    ("S11 kalan metni degistiren sunucu", "degistir")):
        sv = _SahteSunucu(kip=kip)
        rc, cikti = kos(mod, sil_argv("006"), _SahteClient(sv))
        ekle("%s -> rc 3 + 'KAPISI TUTMADI'" % ad, rc == 3 and "TUTMADI" in cikti,
             "rc=%s" % rc)

    # --- S12 dry-run ---------------------------------------------------------
    sv = _SahteSunucu()
    govde_yolu = tmp / "govde.xml"
    if govde_yolu.exists():
        govde_yolu.unlink()
    rc, cikti = kos(mod, sil_argv("006", "--dry-run"), _SahteClient(sv))
    g = govde_yolu.read_text(encoding="utf-8") if govde_yolu.exists() else ""
    ekle("S12 dry-run: rc 0 + LOCK/PUT YOK + govde dosyasi deletedmessages 006 tasir",
         rc == 0 and not sv.yazma_cagrilari() and '<mc:deletedmessages mc:msgno="006"/>' in g
         and sv.durum == BASLANGIC,
         "rc=%s yazma=%d govde=%d bayt" % (rc, len(sv.yazma_cagrilari()), len(g)))

    # --- S13 3. BAGLAM: CSV kipi govdesi tirnakli metinle gecerli XML ---------
    metin = 'Belge "X" & <Y> bulunamadı'
    xml = mod.build_xml("ZSD001", 'Aciklama "tirnakli"', PAKET, "DEVELOPER",
                        [("001", metin, "false")])
    try:
        kok = ET.fromstring(xml)
        geri = kok.find("{%s}messages" % NS_MC).get("{%s}msgtext" % NS_MC)
        ekle("S13 3.BAGLAM CSV kipi: tirnakli metin gecerli XML + geri-ayristirma AYNI",
             geri == metin, "geri=%r" % geri)
    except ET.ParseError as e:
        ekle("S13 3.BAGLAM CSV kipi: tirnakli metin gecerli XML + geri-ayristirma AYNI",
             False, "XML BOZUK: %s" % e)

    # --- S14 CSV kipi yazma: UYARI + deletedmessages yok + eski sabitler -----
    csv_yolu = tmp / "messages.csv"
    csv_yolu.write_text('msgno,msgtext,selfexplainatory\n000,"&1 &2 &3 &4",true\n'
                        '002,"Miktar < 0 olamaz (&1).",false\n', encoding="utf-8")
    sv = _SahteSunucu()
    rc, cikti = kos(mod, ["--name", SINIF, "--package", PAKET, "--transport", "<TRANSPORT>",
                          "--description", "Test", "--responsible", "DEVELOPER",
                          "--messages-csv", str(csv_yolu)],
                    _SahteClient(sv))
    put = [k for k in sv.kayit if k[0] == "PUT"]
    g = sv.govdeler[0] if sv.govdeler else ""
    basliklar = put[0][3] if put else {}
    ekle("S14 CSV kipi: UYARI basilir + govdede deletedmessages YOK + sap-client/dil '100'/'TR'",
         rc == 0 and "[UYARI]" in cikti and "SİLMEZ" in cikti and "--delete" in cikti
         and "deletedmessages" not in g and g
         and basliklar.get("sap-client") == "100" and basliklar.get("sap-language") == "TR"
         and 'mc:documented="false"' in g,
         "rc=%s uyari=%s put=%d basliklar=%s" % (rc, "[UYARI]" in cikti, len(put),
                                            {k: basliklar.get(k) for k in ("sap-client", "sap-language")}))

    # --- S15 iki kip birlikte ------------------------------------------------
    sv = _SahteSunucu()
    rc, cikti = kos(mod, sil_argv("006", "--messages-csv", str(csv_yolu)), _SahteClient(sv))
    ekle("S15 --delete + --messages-csv -> argparse hatasi, yazma yok",
         rc == 2 and not sv.yazma_cagrilari(), "rc=%s" % rc)

    # --- S16 paket uyusmazligi ------------------------------------------------
    sv = _SahteSunucu()
    rc, cikti = kos(mod, sil_argv("006", "--package", BASKA_PAKET), _SahteClient(sv))
    ekle("S16 --package canli paketle uyusmaz -> rc 2, yazma yok",
         rc == 2 and not sv.yazma_cagrilari(), "rc=%s" % rc)

    # --- S17 ONCE okunamaz ---------------------------------------------------
    sv = _SahteSunucu(get_hata={1})
    rc, cikti = kos(mod, sil_argv("006"), _SahteClient(sv))
    ekle("S17 ONCE GET 500 -> rc 2, yazma yok", rc == 2 and not sv.yazma_cagrilari(),
         "rc=%s" % rc)

    # --- S18 PUT 500 -> rc 1 + UNLOCK -----------------------------------------
    sv = _SahteSunucu(put_hata=True)
    cl = _SahteClient(sv)
    rc, cikti = kos(mod, sil_argv("006"), cl)
    unlock = [k for k in sv.kayit if k[0] == "POST" and k[2].get("_action") == "UNLOCK"]
    ekle("S18 PUT 500 -> rc 1 + UNLOCK gonderildi + enqueue temizligi",
         rc == 1 and len(unlock) == 1 and cl.temizlik == 1,
         "rc=%s unlock=%d temizlik=%d" % (rc, len(unlock), cl.temizlik))

    # --- S19 SONRA okunamaz ---------------------------------------------------
    # GET sirasi: 1 = ONCE · 2 = kilit ALTINDA yeniden okuma · 3 = SONRA
    sv = _SahteSunucu(get_hata={3})
    rc, cikti = kos(mod, sil_argv("006"), _SahteClient(sv))
    ekle("S19 SONRA GET 500 -> rc 3 (olculemedi != tuttu)", rc == 3 and "ÖLÇÜLEMEDİ" in cikti,
         "rc=%s" % rc)

    def unlock_say(sv_):
        return len([k for k in sv_.kayit if k[0] == "POST" and k[2].get("_action") == "UNLOCK"])

    # --- S20 TOCTOU: LOCK aninda baskasi 002'yi degistirir -------------------
    # Koruma yokken (bug-gate olcumu): rc 0 + 002 ESKI metne geri doner. Beklenen: PUT YOK.
    sv = _SahteSunucu(lock_degistir=True)
    cl = _SahteClient(sv)
    rc, cikti = kos(mod, sil_argv("006"), cl)
    put = [k for k in sv.kayit if k[0] == "PUT"]
    ekle("S20 TOCTOU: kilit altinda canli degismis -> rc 2 + SIFIR PUT + 1 UNLOCK + 002 korunur",
         rc == 2 and not put and unlock_say(sv) == 1 and cl.temizlik == 1
         and sv.durum["002"][0].endswith("[baskasi degistirdi]") and "006" in sv.durum
         and "DEĞİŞTİ" in cikti,
         "rc=%s put=%d unlock=%d 002=%r" % (rc, len(put), unlock_say(sv), sv.durum["002"][0]))

    # --- S21 kilit altinda yeniden okuma olculemez -> yazma YOK ----------------
    sv = _SahteSunucu(get_hata={2})
    rc, cikti = kos(mod, sil_argv("006"), _SahteClient(sv))
    put = [k for k in sv.kayit if k[0] == "PUT"]
    ekle("S21 kilit altinda GET 500 -> rc 2 + SIFIR PUT + 1 UNLOCK (olculemeyen = yazilmaz)",
         rc == 2 and not put and unlock_say(sv) == 1 and sv.durum == BASLANGIC,
         "rc=%s put=%d unlock=%d" % (rc, len(put), unlock_say(sv)))

    # --- S22 PUT gonderildikten sonra ag istisnasi -> rc 3 + KAPSAM + UNLOCK ----
    sv = _SahteSunucu(put_istisna=True)
    cl = _SahteClient(sv)
    rc, cikti = kos(mod, sil_argv("006"), cl)
    ekle("S22 PUT sonrasi istisna (ReadTimeout) -> rc 3 'elle dogrula' + KAPSAM + UNLOCK",
         rc == 3 and "elle doğrula" in cikti and "BAKILMAYAN" in cikti
         and unlock_say(sv) == 1 and cl.temizlik == 1,
         "rc=%s unlock=%d temizlik=%d" % (rc, unlock_say(sv), cl.temizlik))

    # --- S23 SONRA okumasi istisna -> rc 3 + KAPSAM ----------------------------
    sv = _SahteSunucu(get_istisna={3})
    rc, cikti = kos(mod, sil_argv("006"), _SahteClient(sv))
    ekle("S23 SONRA GET istisnasi -> rc 3 'elle dogrula' + KAPSAM (traceback degil)",
         rc == 3 and "elle doğrula" in cikti and "BAKILMAYAN" in cikti, "rc=%s" % rc)

    # --- S24 PUT'tan ONCE istisna (LOCK) -> rc 1, 'yazilmadi' ------------------
    sv = _SahteSunucu(lock_istisna=True)
    rc, cikti = kos(mod, sil_argv("006"), _SahteClient(sv))
    ekle("S24 LOCK istisnasi (PUT gonderilmedi) -> rc 1 + PUT YOK (3 degil: yazilmadigi BILINIR)",
         rc == 1 and not [k for k in sv.kayit if k[0] == "PUT"] and sv.durum == BASLANGIC,
         "rc=%s" % rc)

    # --- S25 TAB/LF/CR tasiyan metin: ozniteliklerde kacis + silme mutlu yolu ----
    cok_satir = "Satir1\nSatir2\tsekme\rSON"
    xml = mod.build_xml("ZSD001", "Aciklama", PAKET, "DEVELOPER", [("001", cok_satir, "false")])
    try:
        geri = ET.fromstring(xml).find("{%s}messages" % NS_MC).get("{%s}msgtext" % NS_MC)
    except ET.ParseError as e:
        geri = "XML BOZUK: %s" % e
    sv = _SahteSunucu(ek={"030": ("Ilk satir\nikinci\tsatir", "false", "false")})
    rc, cikti = kos(mod, sil_argv("006"), _SahteClient(sv))
    ekle("S25 TAB/LF/CR: build_xml geri-ayristirma AYNI + cok satirli canli metinle silme rc 0",
         geri == cok_satir and rc == 0 and sv.durum.get("030", ("",))[0] == "Ilk satir\nikinci\tsatir"
         and "006" not in sv.durum,
         "geri=%r rc=%s" % (geri, rc))

    # --- U1-U4 katman-ici birim capalari -------------------------------------
    Hata = mod.SilmeGirdiHatasi

    def firlatir(f, *a):
        try:
            f(*a)
            return False
        except Hata:
            return True

    canli = mod.sinif_xml_ayristir(_SahteSunucu().xml())
    ekle("U1 ayristirici: '006,,011' ve '6' reddedilir, '000' kabul edilir",
         firlatir(mod.silme_listesi_ayristir, "006,,011")
         and firlatir(mod.silme_listesi_ayristir, "6")
         and mod.silme_listesi_ayristir("000") == ["000"], "")
    ekle("U2 planlayici: bos msgno / olmayan / tum sinif / dil ayri ayri reddedilir",
         firlatir(mod.silme_planla, canli, ["006", ""], "TR")
         and firlatir(mod.silme_planla, canli, ["999"], "TR")
         and firlatir(mod.silme_planla, canli, sorted(BASLANGIC), "TR")
         and firlatir(mod.silme_planla, canli, ["006"], "EN")
         and len(mod.silme_planla(canli, ["006"], "TR")) == len(BASLANGIC) - 1, "")
    # U2b: planlayicinin KENDI bicim korumasi — canli veride bos anahtar olsa bile (varlik
    # korumasi o durumda gecer) bos msgno reddedilmeli. Bu vektor olmadan M2 KACIYORDU:
    # varlik korumasi ayni girdiyi yakaladigi icin bicim korumasi olculmuyordu.
    tuhaf = dict(canli, messages=dict(canli["messages"], **{"": ("x", "false", "false")}))
    ekle("U2b planlayici bicim korumasi varlik korumasindan BAGIMSIZ (canlida bos anahtar)",
         firlatir(mod.silme_planla, tuhaf, ["006", ""], "TR"), "")
    ekle("U3 ayristirma canli metni kacissiz verir (tirnak/&/<)",
         canli["messages"]["001"] == BASLANGIC["001"] and canli["messages"]["002"] == BASLANGIC["002"]
         and canli["package"] == PAKET and canli["masterLanguage"] == "TR",
         "001=%r" % (canli["messages"].get("001"),))
    once = {"messages": dict(BASLANGIC)}
    sonra = {"messages": {k: v for k, v in BASLANGIC.items() if k != "006"}}
    ekle("U4 kapi: dogru sonuc bos liste, noop sonuc hata listesi",
         mod.silme_kapisi(once, sonra, ["006"]) == []
         and mod.silme_kapisi(once, {"messages": dict(BASLANGIC)}, ["006"]) != [], "")
    # U5: govde oz-denetimi KENDI BASINA olculur (M7-M9 yalniz dolayli olcuyordu)
    kalan = mod.silme_planla(canli, ["006"], "TR")
    iyi = mod.silme_govdesi(canli, ["006"], kalan)
    satirlar = iyi.split("\n")
    del_i = next(i for i, s in enumerate(satirlar) if "<mc:deletedmessages" in s)
    ilk_m = next(i for i, s in enumerate(satirlar) if "<mc:messages " in s)
    once_gelen = satirlar[:]
    once_gelen.insert(ilk_m, once_gelen.pop(del_i))
    bozuklar = {
        "deleted mesajlardan once": "\n".join(once_gelen),
        "bos msgno": iyi.replace('<mc:deletedmessages mc:msgno="006"/>',
                                 '<mc:deletedmessages mc:msgno=""/>'),
        "kalan metin degismis": iyi.replace("Miktar &lt; 0 olamaz", "Miktar &lt; 1 olamaz"),
        "yanlis numara silinir": iyi.replace('mc:msgno="006"/>', 'mc:msgno="020"/>'),
    }
    sonuc = {k: mod.silme_govdesi_dogrula(v, canli, ["006"]) for k, v in bozuklar.items()}
    degismeyen = [k for k, v in bozuklar.items() if v == iyi]
    ekle("U5 govde oz-denetimi: dogru govde bos liste, her bozuk govde hata listesi",
         mod.silme_govdesi_dogrula(iyi, canli, ["006"]) == [] and not degismeyen
         and all(sonuc.values()),
         "bos donen: %s · bozulamayan: %s" % ([k for k, v in sonuc.items() if not v], degismeyen))
    return out


# Capa TAM BIR KEZ eslesmeli (CORE-07); aksi hâlde DOGRULANAMADI.
MUTASYONLAR = [
    ("M1 ayristirici bicim korumasi sokulur",
     "    hatali = [o for o in ogeler if not MSGNO_RE.match(o)]\n",
     "    hatali = []\n"),
    ("M2 planlayici bicim korumasi sokulur",
     "        if not MSGNO_RE.match(no or ''):\n",
     "        if False:\n"),
    ("M3 varlik korumasi sokulur",
     "    yok = [no for no in silinecek if no not in mesajlar]\n",
     "    yok = []\n"),
    ("M4 tum-sinif korumasi sokulur",
     "    if silinecek and not yok and not kalan:\n",
     "    if False:\n"),
    ("M5 dil korumasi sokulur",
     "    if not ml or ml != od:\n",
     "    if False:\n"),
    ("M6 once/sonra kapisi devre disi",
     "    hatalar = silme_kapisi(once, sonra, silinecek)\n",
     "    hatalar = []\n"),
    ("M7 oznitelik kacisi (tirnak + TAB/LF/CR) tumden geri alinir",
     "    return xml_escape(metin, _ATTR_KACIS)\n",
     "    return xml_escape(metin)\n"),
    ("M8 documented sabit 'false'a doner",
     "        d = m[3] if len(m) > 3 else 'false'\n",
     "        d = 'false'\n"),
    ("M9 deletedmessages mesajlardan ONCE yazilir",
     "    satirlar += [f'  <mc:deletedmessages mc:msgno=\"{n}\"/>' for n in deleted]\n",
     "    satirlar[:0] = [f'  <mc:deletedmessages mc:msgno=\"{n}\"/>' for n in deleted]\n"),
    ("M10 populate hazir govdeyi yok sayar",
     "    if xml_payload is None:\n        xml_payload = build_xml(",
     "    if True:\n        xml_payload = build_xml("),
    ("M11 CSV kipindeki UYARI sokulur",
     "        if yalniz_canli:\n",
     "        if False:\n"),
    ("M12 kilit-alti yeniden okuma baglantisi kopar (TOCTOU korumasi)",
     "                      kilit_sonrasi_kontrol=_kilit_alti_yeniden_oku,\n",
     "                      kilit_sonrasi_kontrol=None,\n"),
    ("M13 govde oz-denetimi etkisizlesir (silme_govdesi_dogrula tek basina)",
     "    dm = [d.get(_NS_MC + 'msgno') for d in kok.findall(_NS_MC + 'deletedmessages')]\n",
     "    return []\n"),
    ("M14 kilit-alti karsilastirma sokulur (okur ama kiyaslamaz)",
     "        if fark or fark_no:\n",
     "        if False:\n"),
    ("M15 'PUT gonderildi' izi dusurulur (istisnada rc 3 yerine 1)",
     "            iz['put_gonderildi'] = True\n",
     "            pass\n"),
    ("M16 yalniz TAB/LF/CR kacisi geri alinir (tirnak kalir)",
     "_ATTR_KACIS = {'\"': '&quot;', '\\t': '&#9;', '\\n': '&#10;', '\\r': '&#13;'}\n",
     "_ATTR_KACIS = {'\"': '&quot;'}\n"),
]


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="msag_sil_"))
    try:
        return _main(tmp)
    finally:
        _sil(tmp)


def _main(tmp: Path) -> int:
    print("=" * 78)
    print("msag_mesaj_silme — populate_message_class --delete korpusu (sahte ADT sunucusu)")
    print("=" * 78)
    sonuc = senaryolar(load(), tmp)
    kirik = [(a, d) for a, ok, d in sonuc if not ok]
    for ad, ok, detay in sonuc:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok:
            print("         gorulen: %s" % detay)
    print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

    print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
    ham = PMC_PATH.read_text(encoding="utf-8")
    mut_kirik, capa_kirik = [], []
    for ad, eski, yeni in MUTASYONLAR:
        n = ham.count(eski)
        if n != 1:
            print("  [DOGRULANAMADI] %s — capa %d kez eslesti (1 olmali)" % (ad, n))
            capa_kirik.append(ad)
            continue
        try:
            m_res = senaryolar(load(mut=lambda s, e=eski, y=yeni: s.replace(e, y, 1)), tmp)
            kacan = [a for a, ok, _ in m_res if not ok]
        except BaseException as e:   # cokme != FAIL: ayirt edilebilir kalsin
            kacan = ["COKTU: %s" % type(e).__name__]
        print("  [%s] %s" % ("YAKALANDI" if kacan else "KACTI", ad))
        if kacan:
            print("         kiran: %s" % ", ".join(kacan[:3]))
        else:
            mut_kirik.append(ad)

    print("\n" + "=" * 78)
    if capa_kirik:
        print("DOGRULANAMADI — mutasyon capasi tek eslesmedi: %s" % ", ".join(capa_kirik))
        return 2
    if kirik or mut_kirik:
        if kirik:
            print("FAIL — senaryo: %s" % ", ".join(a for a, _ in kirik))
        if mut_kirik:
            print("FAIL — mutasyon KACTI: %s" % ", ".join(mut_kirik))
        return 1
    print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(MUTASYONLAR)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
