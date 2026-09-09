#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PUSH/YUKLEME AKISINDA SAHTE BASARI — iki kayit, tek sinif (Q268 + Q222(2)).

KOK-1 (Q268) `populate_cds_views.py`: `create_one` zaten var olan CDS icin
`[SKIP] zaten var` yazip **True** donuyordu; `main()` bunu `ok += 1` sayiyor,
ekrana *"N basarili, 0 hatali"* yazip **exit 0** veriyordu. Yani ATLANAN ile
YARATILAN ayni kovaya dusuyordu ve kullanici HICBIR SEY yazilmadigi halde isin
bittigini saniyordu. FIX: `atlandi` AYRI bir sonuc kovasidir; ozet satirinda
ayri sayilir; cikis kodu politikasi aciktir (0 = idempotans korunur, 3 =
`--fail-on-skip` ile opt-in sikilastirma, 1 = gercek hata).
EMSAL: `populate_tables.py:268` ayni sinifi 2026-08-19'da olctu ("obje VAR" !=
"obje DOGRU") ve orada `readback_dogrula()` ile cozdu. Bu tur o cozumun YERINE
gecmez, ONCESIDIR — CDS yolunda icerik hala kiyaslanmiyor, `[ATLANDI]` satiri
bunu ARTIK ACIKCA BEYAN EDIYOR (F5 yayilim notu).

KOK-2 (Q222(2)) `push_object.py` + `sap_client.py`: basarida tek satir vardi —
"[OK] Push completed successfully: <ad>". HANGI dosyanin gittigi ciktida YOKTU
(`--source-file` verilmediginde yol `sap_client` icinde TURETILIR) ve `md5` bu
yolun hicbir yerinde gecmiyordu ⇒ staging ↔ repo kiyasi yapilamiyordu. Bu
deponun olculmus dersi: **push ara-kopyasi BAYATLAR ve readback bunu yapisal
olarak GOREMEZ** (readback canliyi GONDERILENLE kiyaslar; gonderilen yanlis
dosyaysa ikisi de tutar). FIX: alt katman yol + md5 uretir (`kaynak_kimligi`),
her iki push yolu basar, `push_object.py` HEM basari HEM hata dalinda gosterir.

KOK-1② (Q268②) `push_object.py` YONLENDIRMESI: reddedilen `--type ddls` icin not
KOSULSUZ `populate_cds_views.py` diyordu. 09-08 vakasinin GIRIS UCU tam buydu —
istek MEVCUT view'i GUNCELLEMEKTI, oysa o arac batch YARATICIDIR ve mevcut
view'i atlar. Yani hata "yanlis arac" degil **YANLIS IS ICIN DOGRU ARAC**
onerilmesiydi. Otorite playbook'un yazili sinir cumlesidir:
`playbook/adt-cds.md:178` — *"Batch (cok CDS): populate_cds_views.py. Mevcut CDS
guncelle: dogrudan adt_push_source."* FIX: `TIP_GUNCELLEME_YOLU` + `[GUNCELLEME]`
satiri. ⚠ KOK-1 ile KOK-1② AYRI degismezdir, biri digerinin yerine GECMEZ:
biri sessizligi bozar (arac artik "yazmadim" der), digeri operatoru en bastan
dogru yola koyar.

Korpus S(enaryo) + M(utasyon) tasir:
  C1-C6  populate_cds_views: UC BAGLAM (yaratildi / atlandi / gercek hata) +
         karisim (kova sizmasi FP capasi) + gurultu capasi + fail-closed
  P1-P10 kaynak izi: md5 ikiligi (dosya baytlari vs gonderilen metin),
         "olculemedi != temiz", sessizlik yasagi, AST KABLOLAMA (iki dosyada)
  R1-R5  yonlendirme: yaratma+guncelleme AYRI satir, guncelleme batch yaraticiyi
         ONERMEZ, olculmemis tip icin yol UYDURULMAZ (FP capasi), esanlamli
         cozumu korunur, ve 3. BAGLAM = ayri surecte GERCEK CLI (rc=2 korunur)
  M1-M10 fix'i sok -> korpus KIRMIZI olmali (yesil kalirsa korpus o degismezi
         olcmuyor). Uc dosya x bagimsiz degismezler.

Kosum: python tests/fixtures/push_atlandi_ve_kaynak_izi/run.py   (exit 0 = PASS)
"""
from __future__ import annotations

import ast
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path
from typing import Any, Dict

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[2]
SCRIPTS = CORE / "scripts"
PCV_PATH = SCRIPTS / "populate_cds_views.py"
PO_PATH = SCRIPTS / "push_object.py"
SC_PATH = SCRIPTS / "sap_client.py"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

_gc_koruma: list = []
_BOS_KOK: list = []


def _bos_kok() -> str:
    if not _BOS_KOK:
        _BOS_KOK.append(tempfile.mkdtemp(prefix="push_izi_bos_"))
    return _BOS_KOK[0]


# ---------------------------------------------------------------------------
# YUKLEYICILER
# ---------------------------------------------------------------------------
def _exec_modul(yol: Path, ad: str, mut=None, env: dict | None = None):
    """Kaynagi (istege bagli mutasyonla) TAZE namespace'te calistirir.

    ⚠ Env exec'ten ONCE kurulur: modul IMPORT ANINDA config okuyor
    (`_SQLP`/`_VNP`). Sonradan monkeypatch GEC kalir.
    ⚠ stdout: modul win32 dalinda stdout'u gaspediyor; gercek stdout'a
    dokundurmamak icin atilabilir TextIOWrapper(BytesIO) baglanir (StringIO
    OLMAZ: `.buffer` yok -> modulun else dali AttributeError verir).
    """
    src = yol.read_text(encoding="utf-8")
    if mut:
        src = mut(src)
    eski_env = {}
    for k, v in (env or {}).items():
        eski_env[k] = os.environ.get(k)
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    saved_out, saved_err = sys.stdout, sys.stderr
    cop_out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    cop_err = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    sys.stdout, sys.stderr = cop_out, cop_err
    try:
        mod = types.ModuleType(ad)
        mod.__file__ = str(yol)
        exec(compile(src, str(yol), "exec"), mod.__dict__)
    finally:
        sys.stdout, sys.stderr = saved_out, saved_err
        _gc_koruma.append((cop_out, cop_err))
        for k, v in eski_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return mod


def pcv_env() -> dict:
    return {"CLAUDE_PROJECT_DIR": _bos_kok(),
            "IX_SQL_VIEW_PREFIX": "ZMOD001_V_",
            "IX_CDS_VIEW_NAME_PREFIX": "zmod001_ddl_",
            "IX_CDS_TARGET_SPRINT": None}


def yukle_pcv(mut=None):
    return _exec_modul(PCV_PATH, "populate_cds_views", mut, pcv_env())


def fonksiyonlari_al(src: str, adlar: tuple, globaller: dict) -> dict:
    """Kaynaktan YALNIZ istenen ust-duzey fonksiyonlari AST ile ayiklayip calistirir.

    ⛔ TUM modulu `exec` ETME: modul-seviyesi yan etkiler (baglanti/stdout gaspi)
    korpusu cokertir ve kosucu bunu *"mutasyon YAKALANDI"* sayar (cokme != FAIL).
    Bu ders `transport_sifir_kaniti` korpusunda olculdu; burada tekrarlanmiyor.
    """
    agac = ast.parse(src)
    parcalar = [d for d in agac.body
                if isinstance(d, ast.FunctionDef) and d.name in adlar]
    bulunan = {d.name for d in parcalar}
    eksik = set(adlar) - bulunan
    if eksik:
        raise RuntimeError("ust-duzey fonksiyon BULUNAMADI: %s" % sorted(eksik))
    ns = dict(globaller)
    modul = ast.Module(body=parcalar, type_ignores=[])
    exec(compile(ast.fix_missing_locations(modul), "<parca>", "exec"), ns)
    return ns


def yukle_po(src: str) -> dict:
    return fonksiyonlari_al(src, ("kaynak_izi_satirlari",), {})


def yukle_po_yonlendirme(src: str) -> dict:
    """`tip_yonlendirme_notu` + BAGLI MODUL-SABITLERINI ayni kaynaktan ayiklar.

    ⚠ Yalniz `def`i almak yetmez: fonksiyon modul-seviyesi dict'lere bakiyor,
    izole exec'te `NameError` verir. Sabitler de AYNI kaynaktan gelir — burada
    elle bir kopya yazmak, mutasyonun asla goremeyecegi bir IKIZ uretirdi
    (bu evin olculmus tuzagi: "mutasyon gercek kaynaga bakmiyorsa sahte-KACAR").
    ⛔ Tum modulu exec ETMIYORUZ: `push_object` import aninda `sap_client`
    zincirini cekiyor (SAP baglantisi) — cokme "mutasyon yakalandi" sanilirdi.
    """
    agac = ast.parse(src)
    istenen_sabit = {"TIP_YONLENDIRME", "TIP_XML_ZARF", "TIP_YAZICISI_YOK",
                     "TIP_GUNCELLEME_YOLU"}
    parcalar, bulunan = [], set()
    for d in agac.body:
        if isinstance(d, ast.Assign):
            adlar = {t.id for t in d.targets if isinstance(t, ast.Name)}
            if adlar & istenen_sabit:
                parcalar.append(d)
                bulunan |= adlar & istenen_sabit
        elif isinstance(d, ast.FunctionDef) and d.name == "tip_yonlendirme_notu":
            parcalar.append(d)
            bulunan.add(d.name)
    eksik = (istenen_sabit | {"tip_yonlendirme_notu"}) - bulunan
    if eksik:
        raise RuntimeError("push_object'te BULUNAMADI: %s" % sorted(eksik))
    ns: dict = {}
    modul = ast.Module(body=parcalar, type_ignores=[])
    exec(compile(ast.fix_missing_locations(modul), "<parca-yonlendirme>", "exec"), ns)
    return ns


def yukle_sc(src: str) -> dict:
    # Anotasyonlar def ANINDA degerlendirilir (`sap_client` `from __future__
    # import annotations` KULLANMIYOR) => Dict/Any/Path namespace'te olmali.
    return fonksiyonlari_al(src, ("kaynak_kimligi", "kaynak_kimligi_bas"),
                            {"Path": Path, "Dict": Dict, "Any": Any})


# ---------------------------------------------------------------------------
# SAHTE SAP KATMANI (populate_cds_views.main GERCEK yolundan kosar)
# ---------------------------------------------------------------------------
class _SahteYanit:
    def __init__(self, status_code=200, text="", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


class _SahteSession:
    """ADT uclarini taklit eder. Plan: hangi CDS VAR, hangisi POST/PUT'ta duser."""

    def __init__(self, plan):
        self.plan = plan
        self.izler = plan.setdefault("izler", [])

    def get(self, url, **kw):
        if "/discovery" in url:
            return _SahteYanit(200, "", {"X-CSRF-Token": "TOKEN-XYZ-0123456789"})
        ad = url.rstrip("/").rsplit("/", 1)[-1].upper()
        self.izler.append(("GET", ad))
        return _SahteYanit(200 if ad in self.plan.get("var", ()) else 404)

    def post(self, url, **kw):
        params = kw.get("params") or {}
        eylem = params.get("_action")
        if eylem == "LOCK":
            return _SahteYanit(200, "<LOCK_HANDLE>H-1</LOCK_HANDLE>")
        if eylem == "UNLOCK":
            return _SahteYanit(200, "")
        govde = (kw.get("data") or b"").decode("utf-8", "replace")
        m = re.search(r'adtcore:name="([^"]+)"', govde)
        ad = (m.group(1) if m else "").upper()
        self.izler.append(("POST", ad))
        if ad in self.plan.get("post_hata", ()):
            return _SahteYanit(500, "ADT: creation failed")
        return _SahteYanit(201, "")

    def put(self, url, **kw):
        ad = url.rsplit("/source/main", 1)[0].rstrip("/").rsplit("/", 1)[-1].upper()
        self.izler.append(("PUT", ad))
        if ad in self.plan.get("put_hata", ()):
            return _SahteYanit(400, "ADT: put failed")
        return _SahteYanit(204, "")

    def delete(self, url, **kw):
        ad = url.rstrip("/").rsplit("/", 1)[-1].upper()
        self.izler.append(("DELETE", ad))
        return _SahteYanit(200, "")


def _sahte_client_sinifi(plan):
    class _SahteClient:
        def __init__(self, *a, **kw):
            self.url = "https://sahte.invalid:44300"
            self.session = _SahteSession(plan)

        def _invalidate_csrf_cache(self):
            pass

    return _SahteClient


def _sahte_td_spec():
    m = types.ModuleType("td_spec_check")
    m.require_td_spec = lambda ad, tip: ""
    m.find_deleted_items = lambda t: {"fields": [], "joins": []}
    m.scan_source_for_deleted = lambda s, d: []
    return m


def kos_main(mod, argv: list, plan: dict, create_one_yerine=None):
    """`main()`i GERCEK giris noktasindan kosar. Doner: (rc, cikti).

    ⚠ Istisna YUTULMAZ, (None, iz) olarak doner: cagiran senaryo bunu FAIL sayar
    ("cokme != FAIL" dersinin tersi degil — burada cikis-kodu SOZLESMESI olculuyor,
    coken bir main sozlesmeyi zaten saglamamistir).
    """
    eski_argv = sys.argv
    eski_tds = sys.modules.get("td_spec_check")
    eski_client = mod.SAPADTClient
    eski_create = getattr(mod, "create_one", None)
    sys.modules["td_spec_check"] = _sahte_td_spec()
    mod.SAPADTClient = _sahte_client_sinifi(plan)
    if create_one_yerine is not None:
        mod.create_one = create_one_yerine
    sys.argv = ["populate_cds_views.py"] + argv
    yakala = io.StringIO()
    saved_out, saved_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = yakala
    try:
        rc = mod.main()
    except BaseException as e:
        rc = None
        yakala.write("\nISTISNA: %s: %s" % (type(e).__name__, e))
    finally:
        sys.stdout, sys.stderr = saved_out, saved_err
        sys.argv = eski_argv
        mod.SAPADTClient = eski_client
        if create_one_yerine is not None and eski_create is not None:
            mod.create_one = eski_create
        if eski_tds is None:
            sys.modules.pop("td_spec_check", None)
        else:
            sys.modules["td_spec_check"] = eski_tds
    return rc, yakala.getvalue()


def yaz_cds(dizin: Path, harf: str) -> str:
    dizin.mkdir(parents=True, exist_ok=True)
    ad = "ZMOD001_DDL_%s" % harf.upper()
    (dizin / (ad + ".cds")).write_text(
        "@AbapCatalog.sqlViewName: 'ZMOD001_V_%s'\n"
        "@EndUserText.label: 'Test view %s'\n"
        "define view zmod001_ddl_%s as select from t000 {\n"
        "  key t000.mandt as Client\n"
        "}\n" % (harf.upper(), harf.upper(), harf.lower()),
        encoding="utf-8")
    return ad


# ---------------------------------------------------------------------------
# SENARYOLAR — Q268 (uc baglam + FP capalari)
# ---------------------------------------------------------------------------
def senaryolar_pcv(pcv, kum: Path) -> list:
    r = []
    temel = ["--package", "ZMOD001_CLC", "--transport", "TR1", "--source-dir"]

    # --- BAGLAM 1: gercekten yaratilan view -> "yazildi" (REGRESYON) ---------
    d1 = kum / "b1"
    yaz_cds(d1, "A")
    plan1 = {"var": ()}
    rc, c = kos_main(pcv, temel + [str(d1)], plan1)
    yazildi = ("PUT", "ZMOD001_DDL_A") in plan1["izler"]
    r.append(("C1 BAGLAM-1 yaratilan view -> 1 yazildi, exit 0, PUT atildi",
              rc == 0 and "1 yazıldı" in c and "0 atlandı" in c
              and "[OK]   ZMOD001_DDL_A" in c and yazildi
              and "HİÇBİR CDS YAZILMADI" not in c,
              "rc=%r put=%r ozet=%r" % (rc, yazildi, _ozet(c))))

    # --- BAGLAM 2: zaten var -> "atlandi", "basarili" DEMEMELI ---------------
    d2 = kum / "b2"
    yaz_cds(d2, "A")
    plan2 = {"var": ("ZMOD001_DDL_A",)}
    rc, c = kos_main(pcv, temel + [str(d2)], plan2)
    hic_yazma = not any(t[0] in ("PUT", "POST") for t in plan2["izler"])
    r.append(("C2 BAGLAM-2 zaten var -> 0 yazildi/1 atlandi, HIC yazma yok",
              rc == 0 and "0 yazıldı" in c and "1 atlandı (YAZILMADI)" in c
              and "[ATLANDI] ZMOD001_DDL_A" in c and hic_yazma,
              "rc=%r yazmayok=%r ozet=%r" % (rc, hic_yazma, _ozet(c))))
    # AYIRT EDICI: ozet satirinda "basarili" kelimesi ARTIK YOK (eski metin).
    r.append(("C2b ozet 'N başarılı' DEMEMELI (eski sahte-yesil metni)",
              "başarılı" not in _ozet(c), _ozet(c)))
    # GURULTU degil KANIT: hicbir sey yazilmadiginda GORUNUR uyari.
    r.append(("C2c hic yazma yokken '[UYARI] HİÇBİR CDS YAZILMADI' basilir",
              "HİÇBİR CDS YAZILMADI" in c, _ozet(c)))

    # --- BAGLAM 2': cikis kodu POLITIKASI opt-in sikilastirma ---------------
    plan2b = {"var": ("ZMOD001_DDL_A",)}
    rc, c = kos_main(pcv, temel + [str(d2), "--fail-on-skip"], plan2b)
    r.append(("C3 --fail-on-skip: atlanan varsa exit 3 (1'den AYRI kod)",
              rc == 3 and "--fail-on-skip" in c, "rc=%r" % rc))

    # --- BAGLAM 3: GERCEK hata -> fail + exit != 0 --------------------------
    d3 = kum / "b3"
    yaz_cds(d3, "A")
    plan3 = {"var": (), "post_hata": ("ZMOD001_DDL_A",)}
    rc, c = kos_main(pcv, temel + [str(d3)], plan3)
    r.append(("C4 BAGLAM-3 gercek hata -> 1 hatalı, exit 1",
              rc == 1 and "1 hatalı" in c and "0 yazıldı" in c
              and "0 atlandı" in c,
              "rc=%r ozet=%r" % (rc, _ozet(c))))

    # --- KARISIM: kovalar birbirine SIZMIYOR (FP capasi) --------------------
    d4 = kum / "b4"
    for h in ("A", "B", "C"):
        yaz_cds(d4, h)
    plan4 = {"var": ("ZMOD001_DDL_B",), "post_hata": ("ZMOD001_DDL_C",)}
    rc, c = kos_main(pcv, temel + [str(d4)], plan4)
    r.append(("C5 karisim 1 yazildi + 1 atlandi + 1 hatali -> exit 1, kovalar ayri",
              rc == 1 and "1 yazıldı" in c and "1 atlandı (YAZILMADI)" in c
              and "1 hatalı" in c,
              "rc=%r ozet=%r" % (rc, _ozet(c))))
    # FP capasi: yazilan varken "HICBIR CDS YAZILMADI" uyarisi BASILMAMALI.
    r.append(("C5b yazilan varken 'HİÇBİR CDS YAZILMADI' uyarisi BASILMAZ (gurultu)",
              "HİÇBİR CDS YAZILMADI" not in c, _ozet(c)))

    # --- FAIL-CLOSED: taninmayan durum sessizce basariya sayilmaz ------------
    d5 = kum / "b5"
    yaz_cds(d5, "A")
    plan5 = {"var": ()}
    rc, c = kos_main(pcv, temel + [str(d5)], plan5,
                     create_one_yerine=lambda **kw: "beklenmedik_deger")
    r.append(("C6 create_one taninmayan deger -> HATA sayilir, exit 1",
              rc == 1 and "TANINMAYAN durum" in c, "rc=%r ozet=%r" % (rc, _ozet(c))))
    return r


def _ozet(cikti: str) -> str:
    for satir in cikti.splitlines():
        if satir.startswith("=== Sonuç:"):
            return satir
    return "<ozet satiri YOK>"


# ---------------------------------------------------------------------------
# SENARYOLAR — Q222(2) kaynak izi
# ---------------------------------------------------------------------------
def _bas(fn, kimlik) -> str:
    yakala = io.StringIO()
    saved = sys.stdout
    sys.stdout = yakala
    try:
        fn(kimlik)
    finally:
        sys.stdout = saved
    return yakala.getvalue()


def senaryolar_izi(po_ns: dict, sc_ns: dict, po_src: str, sc_src: str,
                   kum: Path) -> list:
    r = []
    kaynak_kimligi = sc_ns["kaynak_kimligi"]
    kaynak_kimligi_bas = sc_ns["kaynak_kimligi_bas"]
    izi = po_ns["kaynak_izi_satirlari"]

    d = kum / "kaynak"
    d.mkdir(parents=True, exist_ok=True)

    # LF dosya: md5(dosya) == md5(gonderilen)
    lf = d / "ZCL_LF.abap"
    lf.write_bytes(b"CLASS zcl_lf DEFINITION.\nENDCLASS.\n")
    with open(lf, "r", encoding="utf-8") as fh:
        lf_metin = fh.read()
    k_lf = kaynak_kimligi(lf, lf_metin)
    beklenen = hashlib.md5(lf.read_bytes()).hexdigest()
    r.append(("P1 LF dosya: md5(dosya) == dosya baytlarinin md5'i + mutlak yol",
              k_lf["source_md5"] == beklenen
              and k_lf["source_path"] == str(lf.resolve())
              and k_lf["source_md5_sent"] == beklenen,
              str(k_lf)))

    # CRLF dosya: IKI md5 AYRISIR (satir sonu cevrimi) — ayirt edici capa
    crlf = d / "ZCL_CRLF.abap"
    crlf.write_bytes(b"CLASS zcl_crlf DEFINITION.\r\nENDCLASS.\r\n")
    with open(crlf, "r", encoding="utf-8") as fh:
        crlf_metin = fh.read()
    k_crlf = kaynak_kimligi(crlf, crlf_metin)
    r.append(("P2 CRLF dosya: md5(dosya) BAYTLARDAN, md5(gonderilen)'den FARKLI",
              k_crlf["source_md5"] == hashlib.md5(crlf.read_bytes()).hexdigest()
              and k_crlf["source_md5_sent"] == hashlib.md5(
                  crlf_metin.encode("utf-8")).hexdigest()
              and k_crlf["source_md5"] != k_crlf["source_md5_sent"],
              str(k_crlf)))

    c = _bas(kaynak_kimligi_bas, k_lf)
    r.append(("P3 LF: TEK md5 satiri basilir (gurultu capasi)",
              "md5(dosya)" in c and "md5(gönderilen)" not in c, c.strip()))

    c = _bas(kaynak_kimligi_bas, k_crlf)
    r.append(("P4 CRLF: IKI md5 de basilir + 'CRLF->LF' gerekcesi",
              "md5(dosya)" in c and "md5(gönderilen)" in c and "CRLF->LF" in c,
              c.strip()))

    # "olculemedi" != "temiz"
    yok = d / "YOK.abap"
    k_yok = kaynak_kimligi(yok, "govde")
    c = _bas(kaynak_kimligi_bas, k_yok)
    r.append(("P5 okunamayan dosya: md5 None + cikti 'DOĞRULANAMADI' (olculemedi!=temiz)",
              k_yok["source_md5"] is None and "DOĞRULANAMADI" in c, c.strip()))

    # push_object tarafi — fail-closed, SESSIZLIK YASAK
    s = izi({})
    r.append(("P6 result bos: SESSIZ kalmaz, 'DOĞRULANAMADI' satiri uretir",
              len(s) >= 1 and any("DOĞRULANAMADI" in x for x in s),
              str(s)))
    s = izi({"source_path": "/x/ZCL_A.abap", "source_md5": "aa" * 16,
             "source_md5_sent": "aa" * 16})
    r.append(("P7 dolu result: yol + md5 satirlari uretilir",
              any("[KAYNAK] /x/ZCL_A.abap" in x for x in s)
              and any("md5(dosya)" in x and "aa" * 16 in x for x in s),
              str(s)))
    s = izi({}, istenen_source_file="/verilen/ZCL_B.abap")
    r.append(("P8 alt katman bildirmediyse cagiranin --source-file'i kullanilir",
              any("/verilen/ZCL_B.abap" in x for x in s), str(s)))

    # --- KABLOLAMA (AST) — 'kod != kablolama' -------------------------------
    r.append(("P9 push_object.main: izi HEM basari HEM hata dalinda basilir (AST)",
              _po_kablolu(po_src), _po_kablolu(po_src, detay=True)))
    r.append(("P10 sap_client: IKI push yolu da kimligi uretir VE basar (AST)",
              _sc_kablolu(sc_src), _sc_kablolu(sc_src, detay=True)))
    return r


# ---------------------------------------------------------------------------
# SENARYOLAR — Q268② YARATMA araci != GUNCELLEME yolu (push_object yonlendirmesi)
# ---------------------------------------------------------------------------
def senaryolar_yonlendirme(po_src: str, gercek_cli: bool = False) -> list:
    """09-08 vakasinin GIRIS UCU: `--type ddls` reddedilince operator NEREYE gider?

    Kok, "yanlis arac" degil **YANLIS IS ICIN DOGRU ARAC** onerilmesiydi: not
    kosulsuz `populate_cds_views.py` (batch YARATICI) diyordu, oysa istek MEVCUT
    view'i GUNCELLEMEKTI ve o arac mevcut view'i atlar. Otorite playbook'un
    yazili sinir cumlesidir (`playbook/adt-cds.md:178`), bu korpusun tahmini degil.
    """
    r = []
    ns = yukle_po_yonlendirme(po_src)
    notu = ns["tip_yonlendirme_notu"]

    n_ddls = notu("ddls")
    g_satirlar = [s for s in n_ddls.splitlines() if s.startswith("[GUNCELLEME]")]
    g = g_satirlar[0] if g_satirlar else ""
    r.append(("R1 `ddls` reddi HEM yaratma HEM guncelleme yolunu soyler",
              "[YONLENDIRME]" in n_ddls and "populate_cds_views.py" in n_ddls
              and len(g_satirlar) == 1 and "adt_push_source" in g,
              n_ddls.replace("\n", " | ")))
    # AYIRT EDICI: guncelleme yolu batch YARATICIYI gostermez (vakanin ta kendisi).
    r.append(("R2 guncelleme satiri batch YARATICIYI onermez (09-08 vakasinin koku)",
              bool(g) and "populate_cds_views.py" not in g, g or "<satir YOK>"))
    # FP/gurultu capasi: olculmemis tip icin guncelleme yolu UYDURULMAZ.
    n_tbl = notu("table")
    r.append(("R3 olculmemis tip (`table`) icin '[GUNCELLEME]' BASILMAZ (uydurma yok)",
              "[YONLENDIRME]" in n_tbl and "XML-ZARF" in n_tbl
              and "[GUNCELLEME]" not in n_tbl,
              n_tbl.replace("\n", " | ")))
    # Esanlamli cozumu KORUNUYOR: operatorun yazdigi `ddls` ile kanonik `cds` esit.
    r.append(("R4 esanlamli `ddls` ile kanonik `cds` AYNI notu uretir",
              n_ddls != "" and notu("ddls") == notu("cds"),
              "esit=%r" % (notu("ddls") == notu("cds"))))

    if gercek_cli:
        # 3. BAGLAM: ayri surec, GERCEK CLI giris noktasi. "Fonksiyon dogru"
        # kablolamayi kanitlamaz; argparse reddi ayri bir yoldan gecer.
        p = subprocess.run(
            [sys.executable, str(PO_PATH), "--name", "ZMOD001_I_X",
             "--type", "ddls", "--transport", "TR1"],
            cwd=str(CORE), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=180)
        ciktisi = (p.stdout or "") + (p.stderr or "")
        r.append(("R5 *3.BAGLAM* gercek CLI: rc=2 KORUNUR + [GUNCELLEME] gorunur",
                  p.returncode == 2 and "[GUNCELLEME]" in ciktisi
                  and "adt_push_source" in ciktisi,
                  "rc=%r cikti=%r" % (p.returncode, ciktisi[-220:])))
    return r


def _cagri_adlari(dugum) -> set:
    return {n.func.id for n in ast.walk(dugum)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}


def _metot_cagri_adlari(dugum) -> set:
    adlar = _cagri_adlari(dugum)
    adlar |= {n.func.attr for n in ast.walk(dugum)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    return adlar


def _po_kablolu(src: str, detay: bool = False):
    """`main` icinde uretim var mi VE `kaynak_izi` IKI ayri dalda basiliyor mu?

    ⚠ Capa AST'dir: `"kaynak_izi_satirlari(" in src` fonksiyonun KENDI `def`
    satiriyla eslesir ve cagri sokulmus olsa bile True doner (olculmus tuzak).
    """
    try:
        agac = ast.parse(src)
    except SyntaxError as e:
        return ("parse hatasi: %s" % e) if detay else False
    ana = [d for d in ast.walk(agac)
           if isinstance(d, ast.FunctionDef) and d.name == "main"]
    if not ana:
        return "main YOK" if detay else False
    uretim = "kaynak_izi_satirlari" in _cagri_adlari(ana[0])
    donguler = [n for n in ast.walk(ana[0])
                if isinstance(n, ast.For) and isinstance(n.iter, ast.Name)
                and n.iter.id == "kaynak_izi"]
    if detay:
        return "uretim=%r basma_dali=%d" % (uretim, len(donguler))
    return uretim and len(donguler) >= 2


def _sc_kablolu(src: str, detay: bool = False):
    try:
        agac = ast.parse(src)
    except SyntaxError as e:
        return ("parse hatasi: %s" % e) if detay else False
    durum = {}
    for ad in ("push_object", "push_class_include"):
        dugumler = [d for d in ast.walk(agac)
                    if isinstance(d, ast.FunctionDef) and d.name == ad]
        if not dugumler:
            durum[ad] = "YOK"
            continue
        cagrilar = _metot_cagri_adlari(dugumler[0])
        durum[ad] = ("kaynak_kimligi" in cagrilar,
                     "kaynak_kimligi_bas" in cagrilar)
    if detay:
        return str(durum)
    return all(v == (True, True) for v in durum.values())


# ---------------------------------------------------------------------------
# MUTASYONLAR
# ---------------------------------------------------------------------------
PCV_MUT = [
    ("M1 atlanani BASARI say (eski davranis)",
     lambda s: s.replace("        return SONUC_ATLANDI",
                         "        return SONUC_OLUSTURULDU")),
    ("M2 ozetten 'atlandi' kovasini kaldir",
     lambda s: s.replace(
         "    ozet = (f'\\n=== Sonuç: {olusturuldu} yazıldı, {atlandi} atlandı '\n"
         "            f'(YAZILMADI), {fail} hatalı')",
         "    ozet = (f'\\n=== Sonuç: {olusturuldu + atlandi} başarılı, '\n"
         "            f'{fail} hatalı')")),
    ("M3 --fail-on-skip politikasini sok",
     lambda s: s.replace("    if atlandi and args.fail_on_skip:",
                         "    if False and args.fail_on_skip:")),
    ("M4 taninmayan durum fail-closed'ini sok",
     lambda s: s.replace("        if durum not in sayac:",
                         "        if False:")),
]

PO_MUT = [
    ("M5 md5 degerini ciktidan dusur",
     lambda s: s.replace('        satirlar.append(f"         md5(dosya)      = {md5}")',
                         '        satirlar.append("         md5(dosya)")')),
    ("M6 kaynak bilinmiyorken SESSIZ kal",
     lambda s: s.replace(
         '    else:\n        satirlar.append("[KAYNAK] DOĞRULANAMADI',
         '    elif False:\n        satirlar.append("[KAYNAK] DOĞRULANAMADI')),
    # Q268② — iki AYRI degismez, iki AYRI mutasyon (biri digerini maskelemesin).
    ("M9 guncelleme yolunu notta HIC BASMA (eski kosulsuz yonlendirme)",
     lambda s: s.replace("        if t in TIP_GUNCELLEME_YOLU:",
                         "        if False:")),
    ("M10 guncelleme yolu olarak batch YARATICIYI goster (vakayi geri getir)",
     lambda s: s.replace(
         "\"mcp__sap-adt__adt_push_source (object_type='ddls') ya da \"",
         "\"populate_cds_views.py ya da \"")),
]

SC_MUT = [
    ("M7 push_object'te kimligi BASMA (kablolama)",
     lambda s: s.replace(
         '        print(f"      Size: {len(source_code)} characters")\n'
         "        kaynak_kimligi_bas(result)",
         '        print(f"      Size: {len(source_code)} characters")')),
    ("M8 md5'i BAYTLAR yerine METINDEN hesapla (CRLF korlugu)",
     lambda s: s.replace(
         "        md5_dosya = hashlib.md5(Path(local_file).read_bytes()).hexdigest()",
         "        md5_dosya = hashlib.md5(Path(local_file)"
         ".read_text(encoding='utf-8').encode('utf-8')).hexdigest()")),
]


def _kum_kur() -> Path:
    return Path(tempfile.mkdtemp(prefix="push_atlandi_izi_"))


def main() -> int:
    print("=" * 78)
    print("push_atlandi_ve_kaynak_izi — atlanan != basarili (Q268) + "
          "push kaynak izi (Q222-2)")
    print("=" * 78)

    kum = _kum_kur()
    po_ham = PO_PATH.read_text(encoding="utf-8")
    sc_ham = SC_PATH.read_text(encoding="utf-8")
    try:
        sonuc = []
        sonuc += senaryolar_pcv(yukle_pcv(), kum)
        sonuc += senaryolar_izi(yukle_po(po_ham), yukle_sc(sc_ham),
                                po_ham, sc_ham, kum)
        sonuc += senaryolar_yonlendirme(po_ham, gercek_cli=True)
        kirik = [(a, d) for a, ok, d in sonuc if not ok]
        for ad, ok, detay in sonuc:
            print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
            if not ok:
                print("         gorulen: %s" % detay)
        print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

        print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
        mut_kirik = []
        for ad, mut in PCV_MUT + PO_MUT + SC_MUT:
            try:
                if (ad, mut) in PCV_MUT:
                    m_res = senaryolar_pcv(yukle_pcv(mut=mut), kum)
                elif (ad, mut) in PO_MUT:
                    m_src = mut(po_ham)
                    m_res = senaryolar_izi(yukle_po(m_src), yukle_sc(sc_ham),
                                           m_src, sc_ham, kum)
                    # `gercek_cli=False`: mutasyon BELLEKTE yasar, diskteki CLI
                    # onu goremez -> alt surec her mutasyonda YESIL kalir ve
                    # "kacti/yakalandi" hukmunu KIRLETIRDI (sahte-yesil).
                    m_res += senaryolar_yonlendirme(m_src)
                else:
                    m_src = mut(sc_ham)
                    m_res = senaryolar_izi(yukle_po(po_ham), yukle_sc(m_src),
                                           po_ham, m_src, kum)
                yakalandi = any(not ok for _, ok, _ in m_res)
                kacan = [a for a, ok, _ in m_res if not ok]
            except BaseException as e:
                # KURULAMADI != KACTI: yuklenemeyen mutasyon OLCUM DEGILDIR.
                print("  [KURULAMADI] %s -> %s: %s" % (ad, type(e).__name__, e))
                mut_kirik.append(ad + " (KURULAMADI)")
                continue
            print("  [%s] %s" % ("YAKALANDI" if yakalandi else "KACTI", ad))
            if yakalandi:
                print("         kiran senaryo(lar): %s" % ", ".join(kacan[:3]))
            else:
                mut_kirik.append(ad)

        print("\n--- yama-tuttu kaniti ---")
        yama_kirik = []
        for ad, mut in PCV_MUT + PO_MUT + SC_MUT:
            if (ad, mut) in PCV_MUT:
                ham = PCV_PATH.read_text(encoding="utf-8")
            elif (ad, mut) in PO_MUT:
                ham = po_ham
            else:
                ham = sc_ham
            degisti = mut(ham) != ham
            print("  [%s] %s" % ("degisti" if degisti else "YAMA TUTMADI", ad))
            if not degisti:
                yama_kirik.append(ad)

        print("\n" + "=" * 78)
        if kirik or mut_kirik or yama_kirik:
            if kirik:
                print("FAIL — senaryo: %s" % ", ".join(a for a, _ in kirik))
            if mut_kirik:
                print("FAIL — mutasyon KACTI/KURULAMADI: %s" % ", ".join(mut_kirik))
            if yama_kirik:
                print("FAIL — mutasyon yamasi kaynaga UYMADI (sahte-yesil riski): %s"
                      % ", ".join(yama_kirik))
            return 1
        print("PASS — %d senaryo + %d mutasyon"
              % (len(sonuc), len(PCV_MUT) + len(PO_MUT) + len(SC_MUT)))
        return 0
    finally:
        shutil.rmtree(kum, ignore_errors=True)
        for _b in _BOS_KOK:
            shutil.rmtree(_b, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
