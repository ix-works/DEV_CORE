#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cds_kaynak_kapisi fixture - `SAPADTClient._validate_cds_source` (create_cds_view kapisi).

NEDEN VAR (Q277 = T-INFRA-CREATE-CDS-VIEW-ABSTRACT-REDDI; bedeli UC kez odendi)
  Kapi DUZ ALT-DIZE ariyordu: `'SELECT FROM' in upper` + `'DEFINE VIEW'|'VIEW ENTITY' in upper`.
  (a) `as select distinct from` bu alt-diziyi ASLA icermez (select ile from arasina
      `distinct` girer) -> gecerli view REDDEDILIYORDU.
  (b) `define [root] abstract entity` tanimi geregi SELECT tasimaz -> REDDEDILIYORDU.
  (c) Arama yorum/string ayirt etmiyordu -> yorumunda "select from" gecen BOZUK kaynak
      1. kontrolu geciyordu; `defin view entity` yazim hatasi 'VIEW ENTITY' alt-dizesiyle
      2. kontrolu geciyordu.
  Mesaj "kaynagi duzelt" diyordu, oysa kaynak DOGRUYDU -> calisan CDS'i bozmaya davet.
  OLCULMUS YAYILIM (tuketici korpusu, 289 .cds, salt-okuma, 2026-09-13):
    once 226 GECER / 63 RED (54 abstract + 7 distinct + 2 table function)
    sonra 287 GECER / 2 RED (2 table function - lider karari: BILINCLI RED, dogru mesaj)
    G->R gecisi 0 (siklastirmanin korpusta yan etkisi yok).

DEGISMEZLER -> CAPALAR
  1. YENI KABUL (gevsetme; her bicim korpus kanitli):  A1-A6   [tabanda DUSER]
  2. ESKI KABUL KORUNDU (FP capasi):                   B1-B9   [B8 haric her mutasyonda
                                                                GECER; B8 yorum ayiklamasina
                                                                BAGLIDIR -> yorum'da DUSER]
  3. ESKI RED KORUNDU (negatif vektor):                N1-N11  [serbest/govde'de DUSER]
  4. SIKILASTIRMA - yorum/string/yazim hatasi sayilmaz: S1-S4  [tabanda + yorum'da DUSER]
  5. BILINCLI RED DOGRU MESAJLA (table function / custom entity; "duzelt" DEMEZ):
                                                       T1-T3   [tf'de + tabanda DUSER]
  6. GERCEK GIRIS NOKTASI `create_cds_view`: kabul -> POST 1 kez, red -> POST 0:
                                                       E1-E4

KIPLER (BEYAN):
  (kipsiz)              duzeltilmis modul -> hepsi PASS, exit 0
  --mutasyon            taban SHA d6c9539 (kusurun CANLI oldugu surum; git show, SIG KLONDA
                        KOSMAZ -> exit 2 DOGRULANAMADI). DAL ADI/main/HEAD VERME.
  --mutasyon-serbest    kapi bos-olmayan her seyi kabul eder     -> N* DUSER
  --mutasyon-yorum      yorum/string ayiklama sokulur            -> S1/S3 DUSER
  --mutasyon-govde      govde (select/projection, `{`) kosulu sokulur -> N6/N7/N11/S4/E3 DUSER
  --mutasyon-tf         table function dali sokulur              -> T2/E4 mesaji DUSER
  Mutasyon calisma agacina YAZMAZ: kaynak kuma kopyalanir, capa sayisi 1 degilse
  exit 3 KURULAMADI (kurulamadi != kacti).

SAP GEREKTIRMEZ: HTTP oturumu sahtedir; olculen sey KAPI KARARI + POST'un atilip atilmadigi.
"""
from __future__ import annotations

import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

_GERCEK_ERR = sys.stderr
KOK = Path(__file__).resolve().parents[3]
if not (KOK / "scripts" / "sap_adt_lib.py").is_file():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {KOK}")

TABAN_SHA = "d6c9539"
GECERLI_KIP = ("--mutasyon", "--mutasyon-serbest", "--mutasyon-yorum",
               "--mutasyon-govde", "--mutasyon-tf")
KIPLER = [a for a in sys.argv[1:] if a.startswith("--")]
if len(KIPLER) > 1 or (KIPLER and KIPLER[0] not in GECERLI_KIP):
    print(f"[KULLANIM] gecerli kipler: {', '.join(GECERLI_KIP)} (en fazla bir tane)")
    sys.exit(2)
KIP = KIPLER[0] if KIPLER else ""

# (capa, yerine) - capa uretim kodunda TAM OLARAK 1 kez gecmeli
MUTASYONLAR = {
    "--mutasyon-serbest": (("        kod = _kod_metni(cds_source)\n",
                            "        return\n        kod = _kod_metni(cds_source)\n"),),
    "--mutasyon-yorum": (("kod = _kod_metni(cds_source)", "kod = cds_source"),),
    "--mutasyon-govde": (
        ("            if not re.match(r'\\s*\\{', govde):\n",
         "            if False:\n"),
        ("        if not re.search(r'\\bas\\s+(?:select\\s+(?:distinct\\s+)?from|projection\\s+on)\\b',\n",
         "        if False and re.search(r'\\bas\\s+(?:select\\s+(?:distinct\\s+)?from|projection\\s+on)\\b',\n"),
    ),
    "--mutasyon-tf": (("        if tur == 'table function':\n", "        if False:\n"),),
}

KUM = Path(tempfile.mkdtemp(prefix="cdskapi_"))
_eski_cwd = os.getcwd()
os.environ["CLAUDE_PROJECT_DIR"] = str(KUM)
(KUM / ".conn_adt").write_text(
    "ADT_SAP_URL=https://ornek.invalid\nADT_SAP_USER=TESTUSER\n"
    "ADT_SAP_PASSWORD=x\nADT_SAP_CLIENT=100\nADT_SAP_TIER=DEV\n", encoding="utf-8")
os.chdir(KUM)
for _p in (KOK / "scripts", KOK / "scripts" / "utils"):
    sys.path.insert(0, str(_p))


def _bitir(kod: int) -> None:
    try:
        os.chdir(_eski_cwd)
    except Exception:
        pass
    shutil.rmtree(KUM, ignore_errors=True)
    sys.exit(kod)


def _kaynak_uret() -> str:
    canli = (KOK / "scripts" / "sap_adt_lib.py").read_text(encoding="utf-8")
    if KIP == "":
        return canli
    if KIP == "--mutasyon":
        r = subprocess.run(["git", "-C", str(KOK), "show", f"{TABAN_SHA}:scripts/sap_adt_lib.py"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print(f"[DOGRULANAMADI] git show {TABAN_SHA} -> {r.stderr.strip()[:160]} "
                  "(tipik: SIG KLON)", file=_GERCEK_ERR)
            _bitir(2)
        if "'SELECT FROM' not in cds_upper" not in r.stdout:
            print(f"[DOGRULANAMADI] taban {TABAN_SHA} kusurlu surum DEGIL (literal yok) -> "
                  "hicbir sayi raporlanmadi", file=_GERCEK_ERR)
            _bitir(2)
        return r.stdout
    metin = canli
    for capa, yerine in MUTASYONLAR[KIP]:
        n = metin.count(capa)
        if n != 1:
            print(f"[KURULAMADI] {KIP}: capa {n} kez bulundu (1 bekleniyordu): {capa.strip()[:80]}",
                  file=_GERCEK_ERR)
            _bitir(3)
        metin = metin.replace(capa, yerine)
    return metin


def _yukle():
    src = _kaynak_uret()
    yol = KUM / "sap_adt_lib_olcum.py"
    yol.write_text(src, encoding="utf-8")
    if yol.read_text(encoding="utf-8") != src:          # yazim DOGRULANIR
        print("[KURULAMADI] kum dosyasi geri okunamadi", file=_GERCEK_ERR)
        _bitir(3)
    yedek = sys.stdout, sys.stderr
    sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
    try:
        spec = importlib.util.spec_from_file_location("sap_adt_lib_olcum", yol)
        m = importlib.util.module_from_spec(spec)            # type: ignore[arg-type]
        sys.modules["sap_adt_lib_olcum"] = m
        spec.loader.exec_module(m)                           # type: ignore[union-attr]
        return m
    except Exception as exc:                                 # noqa: BLE001
        sys.stdout, sys.stderr = yedek
        print(f"[KURULAMADI] modul yuklenemedi: {type(exc).__name__}: {exc}", file=_GERCEK_ERR)
        _bitir(3)
    finally:
        sys.stdout, sys.stderr = yedek


L = _yukle()
print(f"### kip: {KIP or '(duzeltilmis modul)'}")

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(ok), detay))


def karar(src):
    """('GECER', '') | ('RED', mesaj) | ('COKTU', tip)."""
    c = L.SAPADTClient.__new__(L.SAPADTClient)
    try:
        c._validate_cds_source(src)
        return "GECER", ""
    except L.SAPValidationError as exc:
        return "RED", str(exc)
    except Exception as exc:                                 # noqa: BLE001
        return "COKTU", f"{type(exc).__name__}: {exc}"


ESKI_MESAJ = "must contain 'SELECT FROM'"
# NOT: annotation isareti dize icinde bir HARFTEN hemen sonra yazilmaz (core yazim
#   guard'i o bicimi e-posta adresi sanip reddeder) -> satir sonundan sonra ortuk
#   dize birlestirmesi kullanilir.

# ── 1. YENI KABUL (korpus kanitli bicimler; placeholder adlar) ────────────────
A = {
    "A1 view entity + select distinct from": (
        "@AccessControl.authorizationCheck: #NOT_REQUIRED\n"
        "define view entity ZSD001_I_ORNEK_VH\n"
        "  as select distinct from I_ORNEK_KAYNAK as p\n"
        "    inner join zsd001_t_ornek as t on t.vkorg = p.SalesOrganization\n"
        "{\n  key p.Customer\n}\n"),
    "A2 root view entity + select distinct from": (
        "define root view entity ZSD001_I_ORNEK_COVER\n"
        "  as select distinct from zsd001_t_ornek\n{\n  key se_type as SeTypeKey\n}\n"),
    "A3 abstract entity (action parametresi)": (
        "// kilit parametresi\n"
        "@EndUserText.label: 'Kilit Parametresi'\n"
        "define abstract entity ZSD001_I_LOCK_P\n{\n"
        "  @EndUserText.label: 'Siparis No'\n  IvSalesOrder : vbeln_va;\n}\n"),
    "A4 root abstract entity": (
        "define root abstract entity ZSD001_I_ORNEK_R\n{\n  EvMessage : abap.char(220);\n}\n"),
    "A5 select /*yorum*/ distinct from (yorum tokenlar arasinda)": (
        "define view entity ZSD001_I_ORNEK2 as select /* tekillestir */ distinct from zsd001_t_ornek\n"
        "{ key a }\n"),
    "A6 abstract entity CRLF + BOM + TAB (Windows dosya bicimi)": (
        "﻿"
        "@EndUserText.label: 'Sonuc'\r\ndefine\tabstract\tentity\tZSD001_I_ORNEK_P\r\n{\r\n"
        "\tIvDeger : abap.char(10);\r\n}\r\n"),
}
for ad, src in A.items():
    k, m = karar(src)
    kontrol(ad, k == "GECER", f"{k} {m[:90]}")

# ── 2. ESKI KABUL KORUNDU (FP capasi) ─────────────────────────────────────────
B = {
    "B1 klasik define view + sqlViewName": (
        "@AbapCatalog.sqlViewName: 'ZSD001VORNEK'\ndefine view ZSD001_DDL_ORNEK as\n"
        "select from zsd001_t_ornek\n{\n  key id,\n  ad\n}\nwhere durum = 'A'\n"),
    "B2 view entity + union": (
        "define view entity ZSD001_I_ORNEK_U as select from zsd001_t_a { key id }\n"
        "union all select from zsd001_t_b { key id }\n"),
    "B3 root view entity + projection on": (
        "define root view entity ZSD001_C_ORNEK provider contract transactional_query\n"
        "  as projection on ZSD001_I_ORNEK\n{\n  key Id\n}\n"),
    "B4 view entity + with parameters": (
        "define view entity ZSD001_I_ORNEK_P2\n  with parameters P_Tarih : abap.dats\n"
        "  as select from zsd001_t_ornek\n{ key id }\nwhere tarih <= $parameters.P_Tarih\n"),
    "B5 BUYUK harf + CRLF": (
        "DEFINE VIEW ENTITY ZSD001_I_ORNEK_BH\r\n  AS SELECT FROM ZSD001_T_ORNEK\r\n{ KEY ID }\r\n"),
    "B6 view entity (projection, root yok)": (
        "define view entity ZSD001_C_ORNEK_ITEM as projection on ZSD001_I_ORNEK_ITEM { key Id }\n"),
    "B7 string icinde '' kacisi + // (lexer FP capasi)": (
        "@EndUserText.label: 'Musteri''nin adresi // http://ornek'\n"
        "define view entity ZSD001_I_ORNEK_S as select from zsd001_t_ornek { key id }\n"),
    "B8 satir sonu yorumu + blok yorum basligin icinde": (
        "define /* rap */ view entity ZSD001_I_ORNEK_Y // arayuz\n"
        "  as select from zsd001_t_ornek { key id }\n"),
    # B9: korpusta ornek YOK ama ESKI kapi kabul ediyordu -> KORUNUR. Ilk yazimda bu
    # vektor N11 (red bekleniyor) olarak yazilmisti; taban mutasyonu onu GECER gosterip
    # yeni kapinin gecerli bir bicimde YENI yanlis-red urettigini yakaladi.
    "B9 transient view entity + projection on (eski kabul korunur)": (
        "define transient view entity ZSD001_I_ORNEK_T provider contract analytical_query\n"
        "  as projection on ZSD001_I_ORNEK { Id }\n"),
}
for ad, src in B.items():
    k, m = karar(src)
    kontrol(ad, k == "GECER", f"{k} {m[:90]}")

# ── 3. ESKI RED KORUNDU (negatif vektor) ──────────────────────────────────────
N = {
    "N1 None": None,
    "N2 bos dize": "",
    "N3 yalniz bosluk": "   \n\t  \n",
    "N4 str degil (bytes)": b"define view entity X as select from y { key a }",
    "N5 define YOK (ciplak select)": "select from mara { matnr }\n",
    "N6 view entity, select/projection YOK": "define view entity ZSD001_I_ORNEK { key a }\n",
    "N7 abstract entity + as select from (karisik)": (
        "define abstract entity ZSD001_I_ORNEK_X as select from zsd001_t_ornek { key a }\n"),
    "N8 DDIC tablo kaynagi (define table)": (
        "define table zsd001_t_ornek {\n  key mandt : mandt not null;\n  key id : abap.char(10);\n}\n"),
    "N9 DCL (define role)": (
        "define role ZSD001_I_ORNEK_DCL {\n  grant select on ZSD001_I_ORNEK where (Vkorg) = "
        "aspect pfcg_auth(V_VBAK_VKO, VKORG, ACTVT = '03');\n}\n"),
    "N10 root view (entity eksik) + select": "define root view ZSD001_I_ORNEK as select from t { key a }\n",
    "N11 transient view entity, projection YOK": (
        "define transient view entity ZSD001_I_ORNEK_T provider contract analytical_query\n"
        "{ Id }\n"),
}
for ad, src in N.items():
    k, m = karar(src)
    kontrol(ad, k == "RED", f"{k} {m[:90]}")

# ── 4. SIKILASTIRMA: yorum/string/yazim hatasi ANAHTAR SOZCUK SAYILMAZ ────────
S = {
    "S1 anahtar sozcukler YALNIZ yorumda": (
        "// define view entity ZSD001_I_ORNEK as select from zsd001_t_ornek\n"
        "/* DEFINE VIEW ... SELECT FROM ... */\nbu satir kod degil { key a }\n"),
    "S2 yazim hatasi `defin view entity`": (
        "defin view entity ZSD001_I_ORNEK as select from zsd001_t_ornek { key a }\n"),
    "S3 anahtar sozcukler YALNIZ string'de": (
        "@EndUserText.label: 'define view entity X as select from y'\nbos { key a }\n"),
    "S4 view entity; select from YALNIZ yorumda": (
        "define view entity ZSD001_I_ORNEK\n  // as select from zsd001_t_ornek\n{ key a }\n"),
}
for ad, src in S.items():
    k, m = karar(src)
    kontrol(ad, k == "RED", f"{k} {m[:90]}")

# ── 5. BILINCLI RED - DOGRU MESAJ ("duzelt" demez) ────────────────────────────
TF = ("@ClientHandling.type: #CLIENT_DEPENDENT\n"
      "// govdede SELECT x FROM y gecen AMDP aciklamasi\n"
      "define table function ZSD001_I_ORNEK_TF\n"
      "  with parameters @Environment.systemField: #CLIENT p_client : abap.clnt\n"
      "  returns {\n    key client : abap.clnt;\n    key id : abap.char(10);\n  }\n"
      "  implemented by method zsd001_cl_ornek=>get_data;\n")
k, m = karar(TF)
kontrol("T1 table function -> RED", k == "RED", f"{k} {m[:90]}")
kontrol("T2 table function mesaji 'bu aracla yaratilmaz' der, 'kaynagi duzelt' DEMEZ",
        "table function is not created by this tool" in m and "do NOT rewrite" in m
        and ESKI_MESAJ not in m, m[:120])
k, m = karar("define custom entity ZSD001_I_ORNEK_CE\n{\n  key Id : abap.char(10);\n}\n")
kontrol("T3 custom entity -> RED + 'desteklenmiyor' mesaji",
        k == "RED" and "custom entity is not supported" in m and "do NOT rewrite" in m, m[:120])

# ── 6. GERCEK GIRIS NOKTASI: create_cds_view (POST atilir mi) ─────────────────


class _Yanit:
    status_code = 201
    headers: dict = {}
    text = ""


class _Oturum:
    def __init__(self):
        self.postlar: list[bytes] = []

    def post(self, url, headers=None, data=None, params=None, timeout=None):
        self.postlar.append(data or b"")
        return _Yanit()


def giris(src):
    c = L.SAPADTClient.__new__(L.SAPADTClient)
    c.csrf_token = "sahte"
    c.url = "https://ornek.invalid"
    c.language = "TR"
    c.timeout_default = 5
    c.session = _Oturum()
    c._get_headers = lambda *a, **k: {}
    c._retry_request = lambda f, operation=None: f()
    try:
        r = c.create_cds_view("ZSD001_I_ORNEK", src, "Ornek", "ZSD001_CLC", transport=None)
        return r, None, c.session.postlar
    except Exception as exc:                                 # noqa: BLE001
        return None, exc, c.session.postlar


r, e, p = giris(A["A3 abstract entity (action parametresi)"])
kontrol("E1 create_cds_view abstract entity -> POST 1 kez, govdede 'abstract entity'",
        e is None and bool(r and r.get("success")) and len(p) == 1 and b"abstract entity" in p[0],
        f"hata={type(e).__name__ if e else None} post={len(p)}")
r, e, p = giris(A["A1 view entity + select distinct from"])
kontrol("E2 create_cds_view select distinct -> POST 1 kez",
        e is None and len(p) == 1, f"hata={type(e).__name__ if e else None} post={len(p)}")
r, e, p = giris(N["N6 view entity, select/projection YOK"])
kontrol("E3 create_cds_view govdesiz view entity -> SAPValidationError + POST 0",
        isinstance(e, L.SAPValidationError) and len(p) == 0,
        f"hata={type(e).__name__ if e else None} post={len(p)}")
r, e, p = giris(TF)
kontrol("E4 create_cds_view table function -> SAPValidationError(TF mesaji) + POST 0",
        isinstance(e, L.SAPValidationError) and len(p) == 0
        and "table function is not created" in str(e),
        f"hata={type(e).__name__ if e else None} post={len(p)}")

# ── RAPOR ─────────────────────────────────────────────────────────────────────
basarisiz = [s for s in SONUC if not s[1]]
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"  -> {detay}"))
print(f"\nSONUC: {len(SONUC) - len(basarisiz)}/{len(SONUC)} PASS")
_bitir(1 if basarisiz else 0)
