#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""populate_domains / populate_dataelements / populate_tables — IKI SINIF, TEK KORPUS.

Bu korpus, `populate_message_class` #41 Y-1'in ACIKCA "yapilmadi" diye birakilan
SINIF TARAMASINI kapatir (kuyruk: *"ayni desen kardes ureticilerde ARANMADI"*).

============================================================================
SINIF 1 — NORMALIZASYON: bos girdi GECERLI bir degere donusuyordu
============================================================================
Kardes vaka (kapandi 2026-08-29): `''.strip().zfill(3)` == `'000'` ve `'000'`
GECERLI bir mesaj numarasidir -> bos `msgno` tasiyan satir sessizce `000`i EZDI.
Ayni sinifin bu uc dosyadaki ornekleri OLCULDU:

  populate_domains.py       `int(r.get('decimals','0') or '0')`  -> bos = **0**
                            `int(r.get('length','10'))`          -> kolon YOKSA = 10
                            `r.get('datatype','CHAR')`           -> kolon YOKSA = CHAR
                            `r.get('description','')`            -> bos ACIKLAMA (ADR 0005-D)
                            bos `name` -> satir SESSIZCE DUSURULUYORDU
  populate_dataelements.py  yukaridakilerin HEPSI + 4 label bos -> ETIKETSIZ DTEL
                            label sinir asimi -> `[WARN] (will trim)` = SESSIZ KIRPMA
                            bos `type_kind`  -> sessizce `'domain'`, `typeName` BOS
                                                (playbook §26.5: "domain bagi KAYBOLUR")
  populate_tables.py        bos `is_key`     -> `!= 'Y'` testinden gecip NON-KEY
                            bos `delivery_class`/`data_maint` -> DDL'e `#`
                            bos `field_name`/`type` -> BOZUK alan satiri
                            bos `table_desc` -> aciklamasiz tablo (ADR 0005-D)

⭐ FP OLCUMU (guard yazmadan ONCE, canli korpusa karsi — kardes vakanin dersi):
  · 2 gercek `domains.csv` / **55 satir**: bos alan **0**, ama **53 satir acikca
    `decimals=0`** ve **41 satir `fixed_values` BOS** (mesru!).
  · 2 gercek `dataelements.csv` / **90 satir**: bos alan **0**, **87 satir acikca
    `decimals=0`**, `type_kind=BUILTIN` **0 satir**, sinir asan label **0**.
  · 3 gercek `table_fields.csv` / **359 satir**: yapisal alanlarda bos **0**, AMA
    **`description` 175 satirda BOS** (bir paketin TAMAMI) ⇒ `description` guard'a
    ALINMADI; alinsaydi 175 FP verir ve calisan bir paketi kirardi.
  Bu yuzden guard'lar HAM alana bakar ve `description` (tables) DISARIDA birakildi.

============================================================================
SINIF 2 — UC-DEGERLILIK: "bakamadim" ile "yok" ayni sonuca dusuyordu
============================================================================
`table_exists()` (ve kardesleri `domain_exists`/`dtel_exists`) govdesi tek satirdi:
`return r.status_code == 200`. GET **500**/403/timeout -> `False` -> cagiran "obje
yok" okuyup **CREATE** dalina sapiyordu. Sonuc okuma degil **YAZMA**'dir.
Kanonik ayrim `mcp_servers/sap_adt/tools/atom.py` `_varlik_sondasi`de ZATEN vardi
(`checked_absent` / `unavailable:http_500`) — uc uretici ondan geri kalmisti.
⚠ `populate_tables.readback_dogrula` bu ayrimi yapiyordu; ayni dosyadaki varlik
sondasi yapmiyordu ⇒ tutarsizlik dosyanin KENDI icindeydi.

Vektorler:
  D1-D9  domains   : normalizasyon guard'lari + FP capalari (acik `0`, bos fixed_values)
  E1-E8  dtel      : label/description/type_kind + ⭐ URETICI<->DENETCI mutabakati
  T1-T5  tables    : yapisal alanlar + ⭐ FP capasi (bos `description` KABUL)
  V1-V8  uc-degerlilik: 500 -> YAZMA YOK · 404 -> CREATE yolu ACIK · exception dali
  M1-M9  mutasyonlar (ikisi SINIR mutasyonu: naif "normalize sonrasina bak" ve
         naif "hepsini guard'la" yazimlari — yalniz FP capalari onlari yakalar)

Kosum: python tests/fixtures/populate_ddic_fail_closed/run.py     (exit 0 = PASS)
"""
from __future__ import annotations

import io
import subprocess
import sys
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[2]
SCRIPTS = CORE / "scripts"
GATE_DTEL = SCRIPTS / "validators" / "check_dtel_creation_labels.py"

YOLLAR = {
    "dom": SCRIPTS / "populate_domains.py",
    "dtel": SCRIPTS / "populate_dataelements.py",
    "tbl": SCRIPTS / "populate_tables.py",
}

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

_mod_refs: list = []      # GC-koruma: modullerin kurdugu stdout wrapper'lari


def load(anahtar: str, mut=None):
    """Modulu TAZE namespace'e yukler; mutasyon KAYNAK METNINE uygulanir.

    ⚠ Uc modul de import aninda `io.TextIOWrapper(sys.stdout.buffer)` kurar (win32
    dali). Sadece `sys.stdout`u geri koymak YETMEZ: o wrapper GC'ye girince sardigi
    GERCEK buffer'i KAPATIR -> sonraki print "I/O operation on closed file" ile
    patlar (kardes fixture'da olculdu, B22). Bu yuzden import sirasinda stdout
    ATILABILIR bir BytesIO'ya baglanir; gercek stdout'a hic dokunulmaz.
    """
    yol = YOLLAR[anahtar]
    src = yol.read_text(encoding="utf-8")
    if mut:
        src = mut(src)
    saved_out, saved_err = sys.stdout, sys.stderr
    cop_out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    cop_err = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    sys.stdout, sys.stderr = cop_out, cop_err
    try:
        mod = types.ModuleType("_pddic_" + anahtar)
        mod.__file__ = str(yol)
        exec(compile(src, str(yol), "exec"), mod.__dict__)
    finally:
        sys.stdout, sys.stderr = saved_out, saved_err
        _mod_refs.append((cop_out, cop_err))
    return mod


def csv_yaz(tmp: Path, ad: str, basliklar: list, satirlar: list) -> Path:
    p = tmp / ad
    govde = [",".join(basliklar)]
    for s in satirlar:
        govde.append(",".join('"%s"' % str(x).replace('"', '""') for x in s))
    p.write_text("\n".join(govde) + "\n", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Sahte SAP yuzeyi — uc-degerlilik vektorleri icin
# ---------------------------------------------------------------------------
class _Resp:
    def __init__(self, code=200, text=""):
        self.status_code, self.text = code, text
        self.headers = {"X-CSRF-Token": "tok"}


class _PatlayanGet(Exception):
    pass


class _Sess:
    """Varlik-GET'i tek yerden yonlendirir; YAZMA cagrilarini SAYAR.

    `dokunma` sayaci "yazmaya HIC gidilmedi" iddiasini OLCULEBILIR yapar —
    `[FAIL]` basmak yetmez, POST/PUT/DELETE gercekten yapilmamis olmali.
    """

    def __init__(self, varlik_kod=200, patla=False):
        self._kod, self._patla = varlik_kod, patla
        self.dokunma = {"post": 0, "put": 0, "delete": 0}

    def get(self, url, **k):
        if self._patla:
            raise _PatlayanGet("baglanti koptu")
        if url.endswith("/source/main"):
            return _Resp(200, "")
        return _Resp(self._kod, "")

    def post(self, url, **k):
        if (k.get("params") or {}).get("_action") == "LOCK":
            return _Resp(200, "<asx><LOCK_HANDLE>H1</LOCK_HANDLE></asx>")
        self.dokunma["post"] += 1
        return _Resp(201, "")

    def put(self, url, **k):
        self.dokunma["put"] += 1
        return _Resp(200, "")

    def delete(self, url, **k):
        self.dokunma["delete"] += 1
        return _Resp(200, "")


class _Client:
    def __init__(self, varlik_kod=200, patla=False):
        self.url = "https://ornek"
        self.session = _Sess(varlik_kod, patla)


def _tut(fn, *a, **k):
    """Cagriyi kosar, stdout'u yakalar -> (donen, cikti)."""
    buf = io.StringIO()
    saved = sys.stdout
    sys.stdout = buf
    try:
        donen = fn(*a, **k)
    finally:
        sys.stdout = saved
    return donen, buf.getvalue()


# ---------------------------------------------------------------------------
# Sekiller
# ---------------------------------------------------------------------------
DOM_H = ["name", "datatype", "length", "decimals", "description", "fixed_values"]
DOM_TEMIZ = ["ZSD001_D_ORNEK", "CHAR", "10", "0", "Ornek aciklama", ""]

DTEL_H = ["name", "type_kind", "type_name", "datatype", "length", "decimals",
          "description", "short", "medium", "long", "heading"]
DTEL_TEMIZ = ["ZSD001_E_ORNEK", "domain", "ZSD001_D_ORNEK", "CHAR", "10", "0",
              "Ornek aciklama", "Kisa", "Orta metin", "Uzun metin", "Baslik metni"]

TBL_H = ["table_name", "table_desc", "delivery_class", "data_maint",
         "field_name", "is_key", "type", "description", "unit_field"]
TBL_TEMIZ = ["ZSD001_T_ORNEK", "Ornek tablo", "A", "ALLOWED", "MANDT", "Y", "MANDT",
             "Client", ""]


def _degis(taban: list, basliklar: list, **kv) -> list:
    s = list(taban)
    for k, v in kv.items():
        s[basliklar.index(k)] = v
    return s


# ---------------------------------------------------------------------------
# SENARYOLAR
# ---------------------------------------------------------------------------
def senaryolar(mods: dict, tmp: Path) -> list:
    out = []

    def ekle(ad, kosul, detay=""):
        out.append((ad, bool(kosul), detay))

    dom, dtel, tbl = mods["dom"], mods["dtel"], mods["tbl"]

    # =====================================================================
    # D — populate_domains
    # =====================================================================
    DomEksik = dom.DomainSatiriEksikError
    DomKolon = dom.DomainCsvKolonEksikError

    # --- D1: bilinen-BOZUK (bos decimals) -> fail-closed + satir no ---------
    p = csv_yaz(tmp, "d1.csv", DOM_H,
                [DOM_TEMIZ, _degis(DOM_TEMIZ, DOM_H, name="ZSD001_D_IKI", decimals="")])
    try:
        r = dom.load_domains_from_csv(p)
        ekle("D1 bos `decimals` FAIL-CLOSED", False, "hata YOK, %d satir dondu" % len(r))
    except DomEksik as e:
        metin = str(e)
        # ⚠ SEBEBI de assert edilir, yalniz alan adi DEGIL: `int('')` zaten
        # ValueError verip "SAYI DEGIL" diye raporlanirdi ve o dal bu capayi
        # MASKELERDI (guard soksek bile D1 yesil kalirdi). Capa "BOS" sebebine
        # baglanarak gercek degismezi olcer hale getirildi.
        ekle("D1 bos `decimals` FAIL-CLOSED + satir no + SEBEP=BOS raporlanir",
             "satir 3" in metin and "`decimals` BOS" in metin, "metin=%r" % metin[:200])

    # --- D2: ⭐ FP CAPASI — ACIKCA yazilan `0` KABUL edilir -----------------
    # Olculdu: 2 canli `domains.csv` / 55 satirin **53'u** acikca `decimals=0`.
    # Normalizasyon SONRASINA bakan naif bir guard bunlari REDDEDER -> korpus kirilir.
    p = csv_yaz(tmp, "d2.csv", DOM_H, [DOM_TEMIZ])
    try:
        r = dom.load_domains_from_csv(p)
        ekle("D2 ⭐FP capasi: ACIKCA yazilan decimals=0 kabul edilir (53/55 canli satir)",
             len(r) == 1 and r[0]["decimals"] == 0, "donen=%r" % (r,))
    except DomEksik as e:
        ekle("D2 ⭐FP capasi: ACIKCA yazilan decimals=0 kabul edilir (53/55 canli satir)",
             False, "acik 0 REDDEDILDI (normalize SONRASINA bakan guard): %s" % str(e)[:120])

    # --- D3: bos `description` -> ADR 0005-D ------------------------------
    p = csv_yaz(tmp, "d3.csv", DOM_H, [_degis(DOM_TEMIZ, DOM_H, description="")])
    try:
        dom.load_domains_from_csv(p)
        ekle("D3 bos `description` FAIL-CLOSED (ADR 0005-D)", False, "hata YOK")
    except DomEksik:
        ekle("D3 bos `description` FAIL-CLOSED (ADR 0005-D)", True)

    # --- D4: ⭐ FP CAPASI — bos `fixed_values` MESRU -----------------------
    # 55 canli satirin 41'i bos: sabit degeri olmayan domain normaldir.
    p = csv_yaz(tmp, "d4.csv", DOM_H, [_degis(DOM_TEMIZ, DOM_H, fixed_values="")])
    try:
        r = dom.load_domains_from_csv(p)
        ekle("D4 ⭐FP capasi: bos `fixed_values` MESRU (41/55 canli satir) -> gecer",
             len(r) == 1 and r[0]["fixed_values"] == [], "donen=%r" % (r,))
    except DomEksik as e:
        ekle("D4 ⭐FP capasi: bos `fixed_values` MESRU (41/55 canli satir) -> gecer",
             False, "guard fazla genis: %s" % str(e)[:120])

    # --- D5: eksik KOLON — AYRI hata tipi ---------------------------------
    # Bos HUCRE ile eksik KOLON farkli kusurlardir; tek tipe indirgenirse guard'lardan
    # biri digerini maskeler ve mutasyonla olculemez.
    p = csv_yaz(tmp, "d5.csv", ["name", "datatype", "length", "description"],
                [["ZSD001_D_ORNEK", "CHAR", "10", "Aciklama"]])
    try:
        dom.load_domains_from_csv(p)
        ekle("D5 eksik KOLON -> DomainCsvKolonEksikError (bos hucreden AYRI tip)",
             False, "hata YOK")
    except DomKolon as e:
        ekle("D5 eksik KOLON -> DomainCsvKolonEksikError (bos hucreden AYRI tip)",
             "decimals" in str(e), "metin=%r" % str(e)[:120])
    except DomEksik:
        ekle("D5 eksik KOLON -> DomainCsvKolonEksikError (bos hucreden AYRI tip)",
             False, "YANLIS TIP: satir hatasi olarak raporlandi (tipler maskelemis)")

    # --- D6: FP CAPASI — tamamen bos satir dolgudur ------------------------
    p = tmp / "d6.csv"
    p.write_text(",".join(DOM_H) + "\n"
                 + ",".join(DOM_TEMIZ) + "\n"
                 + ",,,,,\n"
                 + ",".join(_degis(DOM_TEMIZ, DOM_H, name="ZSD001_D_IKI")) + "\n",
                 encoding="utf-8")
    try:
        r = dom.load_domains_from_csv(p)
        ekle("D6 FP capasi: tamamen bos satir = dolgu, sessizce atlanir",
             len(r) == 2, "donen=%d" % len(r))
    except DomEksik as e:
        ekle("D6 FP capasi: tamamen bos satir = dolgu, sessizce atlanir",
             False, "dolgu satiri hata verdi: %s" % str(e)[:120])

    # --- D7: bilinen-TEMIZ -> gecer ----------------------------------------
    p = csv_yaz(tmp, "d7.csv", DOM_H,
                [DOM_TEMIZ,
                 _degis(DOM_TEMIZ, DOM_H, name="ZSD001_D_IKI", datatype="QUAN",
                        length="13", decimals="3", fixed_values="A=Bir;B=Iki")])
    try:
        r = dom.load_domains_from_csv(p)
        ekle("D7 bilinen-TEMIZ 2 satir gecer (fixed_values ayristirilir)",
             len(r) == 2 and r[1]["decimals"] == 3 and len(r[1]["fixed_values"]) == 2,
             "donen=%r" % (r,))
    except DomEksik as e:
        ekle("D7 bilinen-TEMIZ 2 satir gecer (fixed_values ayristirilir)",
             False, "beklenmedik hata: %s" % str(e)[:140])

    # --- D8: bos `name` -> eskiden SESSIZCE DUSURULUYORDU ------------------
    p = csv_yaz(tmp, "d8.csv", DOM_H, [DOM_TEMIZ, _degis(DOM_TEMIZ, DOM_H, name="")])
    try:
        r = dom.load_domains_from_csv(p)
        ekle("D8 bos `name` FAIL-CLOSED (eskiden sessizce DUSURULUYORDU)",
             False, "sessizce dusuruldu, %d satir dondu" % len(r))
    except DomEksik:
        ekle("D8 bos `name` FAIL-CLOSED (eskiden sessizce DUSURULUYORDU)", True)

    # --- D9: `length` sayi degil -> teshis edilebilir hata ------------------
    p = csv_yaz(tmp, "d9.csv", DOM_H, [_degis(DOM_TEMIZ, DOM_H, length="on")])
    try:
        dom.load_domains_from_csv(p)
        ekle("D9 sayisal olmayan `length` FAIL-CLOSED (ham ValueError degil)",
             False, "hata YOK")
    except DomEksik as e:
        ekle("D9 sayisal olmayan `length` FAIL-CLOSED (ham ValueError degil)",
             "SAYI DEGIL" in str(e), "metin=%r" % str(e)[:140])
    except ValueError as e:
        ekle("D9 sayisal olmayan `length` FAIL-CLOSED (ham ValueError degil)",
             False, "CIPLAK ValueError sizdi: %s" % e)

    # =====================================================================
    # E — populate_dataelements
    # =====================================================================
    DtelEksik = dtel.DtelSatiriEksikError

    # --- E1: bos label -> gate R2 --------------------------------------
    p = csv_yaz(tmp, "e1.csv", DTEL_H, [_degis(DTEL_TEMIZ, DTEL_H, short="")])
    try:
        dtel.load_dataelements_from_csv(p)
        ekle("E1 bos `short` label FAIL-CLOSED (gate R2 / ADR 0005-D)", False, "hata YOK")
    except DtelEksik as e:
        ekle("E1 bos `short` label FAIL-CLOSED (gate R2 / ADR 0005-D)",
             "short" in str(e), "metin=%r" % str(e)[:140])

    # --- E2: sinir asimi -> SESSIZ KIRPMA YOK, fail-closed ----------------
    p = csv_yaz(tmp, "e2.csv", DTEL_H, [_degis(DTEL_TEMIZ, DTEL_H, short="A" * 11)])
    try:
        dtel.load_dataelements_from_csv(p)
        ekle("E2 label 11>10 FAIL-CLOSED (eskiden `[WARN] will trim` = SESSIZ KIRPMA)",
             False, "hata YOK — sessiz kirpma geri gelmis")
    except DtelEksik as e:
        ekle("E2 label 11>10 FAIL-CLOSED (eskiden `[WARN] will trim` = SESSIZ KIRPMA)",
             "11 karakter > 10" in str(e), "metin=%r" % str(e)[:160])

    # --- E3: ⭐ FP capasi / esik ikizi — TAM sinirda label GECER -----------
    p = csv_yaz(tmp, "e3.csv", DTEL_H,
                [_degis(DTEL_TEMIZ, DTEL_H, short="A" * 10, medium="B" * 20,
                        long="C" * 40, heading="D" * 55)])
    try:
        r = dtel.load_dataelements_from_csv(p)
        ekle("E3 ⭐esik ikizi: TAM sinirda 4 label (10/20/40/55) GECER",
             len(r) == 1, "donen=%d" % len(r))
    except DtelEksik as e:
        ekle("E3 ⭐esik ikizi: TAM sinirda 4 label (10/20/40/55) GECER",
             False, "off-by-one: %s" % str(e)[:140])

    # --- E4: `BUILTIN` reddedilir (playbook §26.6) ------------------------
    p = csv_yaz(tmp, "e4.csv", DTEL_H,
                [_degis(DTEL_TEMIZ, DTEL_H, type_kind="BUILTIN", type_name="DATS")])
    try:
        dtel.load_dataelements_from_csv(p)
        ekle("E4 `type_kind=BUILTIN` FAIL-CLOSED + §26.6 yonlendirmesi", False, "hata YOK")
    except DtelEksik as e:
        metin = str(e)
        ekle("E4 `type_kind=BUILTIN` FAIL-CLOSED + §26.6 yonlendirmesi",
             "type_kind" in metin and "26.6" in metin, "metin=%r" % metin[:200])

    # --- E5: bos `type_kind` -> eskiden sessizce 'domain' -----------------
    p = csv_yaz(tmp, "e5.csv", DTEL_H, [_degis(DTEL_TEMIZ, DTEL_H, type_kind="")])
    try:
        dtel.load_dataelements_from_csv(p)
        ekle("E5 bos `type_kind` FAIL-CLOSED (eskiden sessizce 'domain')", False, "hata YOK")
    except DtelEksik:
        ekle("E5 bos `type_kind` FAIL-CLOSED (eskiden sessizce 'domain')", True)

    # --- E6: ad Z/Y ile baslamiyor (gate R1) ------------------------------
    p = csv_yaz(tmp, "e6.csv", DTEL_H, [_degis(DTEL_TEMIZ, DTEL_H, name="ABC_E_ORNEK")])
    try:
        dtel.load_dataelements_from_csv(p)
        ekle("E6 Z/Y ile baslamayan ad FAIL-CLOSED (gate R1)", False, "hata YOK")
    except DtelEksik as e:
        ekle("E6 Z/Y ile baslamayan ad FAIL-CLOSED (gate R1)",
             "Z/Y" in str(e), "metin=%r" % str(e)[:140])

    # --- E7: 3. BAGLAM — build_xml ARTIK KIRPMIYOR ------------------------
    # Guard uretim noktasina tasindi; build_xml yalniz bicimler. Iki yerde ayni
    # degismezi tutmak mutasyonla olcumu imkansiz kilardi.
    xml = dtel.build_xml(name="ZSD001_E_X", description="d", package="ZSD001_CLC",
                         responsible="<SAP_USER>", type_kind="domain",
                         type_name="ZSD001_D_X", datatype="CHAR", length=10, decimals=0,
                         short="A" * 14, medium="B", long="C", heading="D")
    ekle("E7 3.baglam: build_xml label'i KIRPMAZ (guard tek noktada)",
         "<dtel:shortFieldLabel>" + "A" * 14 + "</dtel:shortFieldLabel>" in xml,
         "shortFieldLabel bloku=%r" % xml[xml.find("<dtel:shortFieldLabel>"):][:60])

    # --- E8: ⭐ URETICI <-> DENETCI mutabakati ----------------------------
    # `check_dtel_creation_labels.py` (`# ENFORCES: C-DTEL-CREATE-01`) AYNI CSV'ye
    # ne diyorsa uretici de onu demeli. Ayrisirlarsa gate yesil derken arac kirpar
    # (ya da tersi) — bu, kaydin kok sinifi.
    if GATE_DTEL.is_file():
        ikili = []
        for ad, satir in (("bozuk", _degis(DTEL_TEMIZ, DTEL_H, short="")),
                          ("temiz", DTEL_TEMIZ)):
            yol = csv_yaz(tmp, "e8_%s_dataelements.csv" % ad, DTEL_H, [satir])
            g = subprocess.run([sys.executable, str(GATE_DTEL), str(yol)],
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace")
            gate_red = (g.returncode == 1)
            try:
                dtel.load_dataelements_from_csv(yol)
                uretici_red = False
            except DtelEksik:
                uretici_red = True
            ikili.append((ad, gate_red, uretici_red))
        uyum = all(gr == ur for _, gr, ur in ikili)
        ekle("E8 ⭐URETICI<->DENETCI: gate ve uretici AYNI CSV'de AYNI karari verir",
             uyum and ikili[0][1] is True and ikili[1][1] is False,
             "olculen=%r" % (ikili,))
    else:
        ekle("E8 ⭐URETICI<->DENETCI mutabakati", False,
             "OLCULEMEDI: gate dosyasi yok -> %s" % GATE_DTEL)

    # =====================================================================
    # T — populate_tables (main() = gercek giris noktasi)
    # =====================================================================
    def tbl_main(satirlar, ad):
        """main()'i GERCEK giris noktasindan kosar.

        ⚠ `main()` CSV ayristirmasindan SONRA kosulsuz `SAPADTClient()` kurar ve bu
        makinede baglanti yer-tutucudur -> istisna atar. Bu bir HARNESS sinirdir,
        kod hatasi degil: guard'lar SAP'ye gitmeden ONCE karar verdigi icin
        olculecek her sey istisnadan once basilir. Kardes fixture
        (`populate_tables_unit_kind.run_main`) ayni sekilde yakalar.
        """
        yol = csv_yaz(tmp, ad, TBL_H, satirlar)
        argv = sys.argv[:]
        sys.argv = ["populate_tables.py", "--package", "ZSD001_CLC",
                    "--transport", "<TRANSPORT>", "--csv", str(yol), "--dry-run"]
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            rc = tbl.main()
        except BaseException as e:
            rc = "EXC:%s" % type(e).__name__
        finally:
            sys.stdout = saved
            sys.argv = argv
        return rc, buf.getvalue()

    # "satir guard'i satiri REDDETTI" izi — SAP'ye hic gidilmedigini de kanitlar.
    RED_IZI = "YARIM/GECERSIZ"
    KABUL_IZI = "1 tablo yüklendi"

    # --- T1: bos `is_key` -------------------------------------------------
    rc, cikti = tbl_main([_degis(TBL_TEMIZ, TBL_H, is_key="")], "t1.csv")
    ekle("T1 bos `is_key` -> rc=1, SAP'ye HIC gidilmez",
         rc == 1 and RED_IZI in cikti and "`is_key`" in cikti and KABUL_IZI not in cikti,
         "rc=%r cikti=%r" % (rc, cikti[:200]))

    # --- T2: gecersiz `is_key` -> sessizce NON-KEY OLMAZ ------------------
    rc, cikti = tbl_main([_degis(TBL_TEMIZ, TBL_H, is_key="Yes")], "t2.csv")
    ekle("T2 gecersiz `is_key='Yes'` -> rc=1 (sessizce NON-KEY olmaz)",
         rc == 1 and "yalniz Y/N" in cikti and KABUL_IZI not in cikti,
         "rc=%r cikti=%r" % (rc, cikti[:200]))

    # --- T3: ⭐ FP CAPASI — bos `description` KABUL ----------------------
    # Olculdu: 3 canli `table_fields.csv` / 359 satirin **175'i** (bir paketin
    # TAMAMI) bos `description` tasiyor ve bu kolon DDL'e ZATEN yazilmaz.
    # "Hepsini guard'la" diyen naif yazim burada 175 FP verir.
    rc, cikti = tbl_main([_degis(TBL_TEMIZ, TBL_H, description="")], "t3.csv")
    ekle("T3 ⭐FP capasi: bos `description` KABUL (175/359 canli satir) -> satir gecer",
         RED_IZI not in cikti and KABUL_IZI in cikti and "fields=  1" in cikti,
         "rc=%r cikti=%r" % (rc, cikti[:220]))

    # --- T4: bos `delivery_class` ----------------------------------------
    rc, cikti = tbl_main([_degis(TBL_TEMIZ, TBL_H, delivery_class="")], "t4.csv")
    ekle("T4 bos `delivery_class` -> rc=1 (DDL'e `#` yazilmaz)",
         rc == 1 and "`delivery_class`" in cikti and KABUL_IZI not in cikti,
         "rc=%r cikti=%r" % (rc, cikti[:200]))

    # --- T5: FP capasi — tam/gecerli satir -------------------------------
    rc, cikti = tbl_main([TBL_TEMIZ], "t5.csv")
    ekle("T5 FP capasi: gecerli satir kabul edilir + `table_desc` korunur",
         RED_IZI not in cikti and KABUL_IZI in cikti and "desc=Ornek tablo" in cikti,
         "rc=%r cikti=%r" % (rc, cikti[:220]))

    # =====================================================================
    # V — UC-DEGERLILIK: "olculemedi" != "yok"
    # =====================================================================
    # --- V1/V2/V3: domains -----------------------------------------------
    c = _Client(varlik_kod=500)
    sonuc, cikti = _tut(dom.create_one, c, "tok", "ZSD001_D_X", "d", "ZSD001_CLC",
                        "<SAP_USER>", "<TRANSPORT>", "CHAR", 10, 0, [])
    ekle("V1 domains: varlik GET 500 -> False + OLCULEMEDI + HICBIR yazma",
         sonuc is False and "OLCULEMEDI" in cikti and c.session.dokunma["post"] == 0,
         "donen=%r post=%d cikti=%r" % (sonuc, c.session.dokunma["post"], cikti[:160]))

    c = _Client(varlik_kod=404)
    sonuc, cikti = _tut(dom.create_one, c, "tok", "ZSD001_D_X", "d", "ZSD001_CLC",
                        "<SAP_USER>", "<TRANSPORT>", "CHAR", 10, 0, [])
    ekle("V2 ⭐FP capasi: domains 404 -> CREATE yolu ACIK kalir (POST yapilir)",
         sonuc is True and c.session.dokunma["post"] == 1,
         "donen=%r post=%d" % (sonuc, c.session.dokunma["post"]))

    c = _Client(varlik_kod=200)
    sonuc, cikti = _tut(dom.create_one, c, "tok", "ZSD001_D_X", "d", "ZSD001_CLC",
                        "<SAP_USER>", "<TRANSPORT>", "CHAR", 10, 0, [])
    ekle("V3 FP capasi: domains 200 -> [SKIP] zaten var (idempotans korunur)",
         sonuc is True and "[SKIP]" in cikti and c.session.dokunma["post"] == 0,
         "donen=%r cikti=%r" % (sonuc, cikti[:120]))

    # --- V4/V5: dataelements ---------------------------------------------
    satir = dict(zip(DTEL_H, DTEL_TEMIZ))
    satir["length"], satir["decimals"] = 10, 0
    c = _Client(varlik_kod=500)
    sonuc, cikti = _tut(dtel.create_one, c, "tok", satir, "ZSD001_CLC",
                        "<SAP_USER>", "<TRANSPORT>")
    ekle("V4 dtel: varlik GET 500 -> False + OLCULEMEDI + HICBIR yazma",
         sonuc is False and "OLCULEMEDI" in cikti and c.session.dokunma["post"] == 0,
         "donen=%r post=%d cikti=%r" % (sonuc, c.session.dokunma["post"], cikti[:160]))

    c = _Client(varlik_kod=404)
    sonuc, cikti = _tut(dtel.create_one, c, "tok", satir, "ZSD001_CLC",
                        "<SAP_USER>", "<TRANSPORT>")
    ekle("V5 ⭐FP capasi: dtel 404 -> CREATE yolu ACIK kalir",
         sonuc is True and c.session.dokunma["post"] == 1,
         "donen=%r post=%d" % (sonuc, c.session.dokunma["post"]))

    # --- V6/V7: tables ----------------------------------------------------
    ALANLAR = [{"name": "mandt", "is_key": "Y", "type": "mandt", "description": ""}]
    c = _Client(varlik_kod=500)
    sonuc, cikti = _tut(tbl.create_one, c, "tok", "ZSD001_T_X", "d", "A", "ALLOWED",
                        ALANLAR, "ZSD001_CLC", "<TRANSPORT>")
    ekle("V6 tables: varlik GET 500 -> False + OLCULEMEDI + HICBIR yazma "
         "(kaydin ta kendisi: 500 -> CREATE)",
         sonuc is False and "OLCULEMEDI" in cikti
         and c.session.dokunma["post"] == 0 and c.session.dokunma["put"] == 0,
         "donen=%r dokunma=%r cikti=%r" % (sonuc, c.session.dokunma, cikti[:160]))

    c = _Client(varlik_kod=404)
    sonuc, cikti = _tut(tbl.create_one, c, "tok", "ZSD001_T_X", "d", "A", "ALLOWED",
                        ALANLAR, "ZSD001_CLC", "<TRANSPORT>")
    ekle("V7 ⭐FP capasi: tables 404 -> CREATE+PUT yolu ACIK kalir",
         sonuc is True and c.session.dokunma["put"] == 1,
         "donen=%r dokunma=%r" % (sonuc, c.session.dokunma))

    # --- V8: 3. BAGLAM — GET'in KENDISI patlarsa --------------------------
    # HTTP kodu bile yok: `unavailable:<ExcName>`. Fail-closed yon AYNI kalmali.
    c = _Client(patla=True)
    sonuc, cikti = _tut(tbl.create_one, c, "tok", "ZSD001_T_X", "d", "A", "ALLOWED",
                        ALANLAR, "ZSD001_CLC", "<TRANSPORT>")
    ekle("V8 3.baglam: varlik GET EXCEPTION -> unavailable:<Exc> + yazma YOK",
         sonuc is False and "unavailable:_PatlayanGet" in cikti
         and c.session.dokunma["post"] == 0,
         "donen=%r cikti=%r" % (sonuc, cikti[:160]))

    return out


# ---------------------------------------------------------------------------
# MUTASYONLAR — (hedef_anahtar, ad, yama)
# ---------------------------------------------------------------------------
MUTASYONLAR = [
    ("dom", "M1 domains satir guard'ini sok (bos alan yine sessizce gecer)",
     lambda s: s.replace("            bos = [a for a in REQUIRED_CSV_COLUMNS if not ham[a]]",
                         "            bos = []")),

    # ⭐ SINIR mutasyonu: guard'i HAM alan yerine NORMALIZE SONRASINA baktiran naif
    # yazim. Bos decimals'i yakalamaya DEVAM eder (D1 yesil kalir) ama ACIKCA
    # yazilmis `0`i da reddeder. Yalniz D2 bunu yakalayabilir; yakalayamazsa D2
    # bos bir capadir. (Kardes vakada ayni tuzak 5 paketi kiracakti.)
    ("dom", "M2 ⭐SINIR: guard normalize SONRASINA bakar (acik decimals=0'i da reddeder)",
     lambda s: s.replace(
         "            bos = [a for a in REQUIRED_CSV_COLUMNS if not ham[a]]",
         "            bos = [a for a in REQUIRED_CSV_COLUMNS if not ham[a]]\n"
         "            if ham['decimals'].lstrip('0') == '':\n"
         "                bos.append('decimals')")),

    ("dom", "M3 domains uc-degerliligi sok (500 yine 'yok' sayilir -> CREATE)",
     lambda s: s.replace("    return None, 'unavailable:http_%s' % kod",
                         "    return False, 'checked_absent'")),

    ("dtel", "M4 dtel label sinir guard'ini sok (sessiz kirpma sinifi geri gelir)",
     lambda s: s.replace("                if len(ham[alan]) > sinir:",
                         "                if False:")),

    ("dtel", "M5 dtel `type_kind` kontrolunu sok (BUILTIN + bos yine gecer)",
     lambda s: s.replace("            if ham['type_kind'].lower() != 'domain':",
                         "            if False:")),

    ("dtel", "M6 dtel uc-degerliligi sok",
     lambda s: s.replace("    return None, 'unavailable:http_%s' % kod",
                         "    return False, 'checked_absent'")),

    ("tbl", "M7 tables `is_key` kontrolunu sok (gecersiz deger sessizce NON-KEY)",
     lambda s: s.replace("            if ham['is_key'].upper() not in IS_KEY_GECERLI:",
                         "            if False:")),

    # ⭐ SINIR mutasyonu: "hepsini guard'la" diyen naif yazim. Bos alanlari
    # yakalamaya DEVAM eder (T1/T4 yesil kalir) ama canli korpusta 175 satirin
    # tasidigi BOS `description`i da reddeder -> calisan bir paket kirilir.
    # Yalniz T3 bunu yakalayabilir.
    ("tbl", "M8 ⭐SINIR: `description` de zorunlu olsun (175 canli satir kirilir)",
     lambda s: s.replace(
         "ROW_REQUIRED_FIELDS = tuple(c for c in REQUIRED_CSV_COLUMNS if c != 'description')",
         "ROW_REQUIRED_FIELDS = REQUIRED_CSV_COLUMNS")),

    ("tbl", "M9 tables uc-degerliligi sok (kaydin ta kendisi: 500 -> CREATE)",
     lambda s: s.replace("    return None, 'unavailable:http_%s' % kod",
                         "    return False, 'checked_absent'")),
]


def main() -> int:
    import tempfile

    print("=" * 78)
    print("populate_ddic_fail_closed — normalizasyon sinifi + uc-degerli varlik sondasi")
    print("=" * 78)

    tmp = Path(tempfile.mkdtemp(prefix="pddic_"))

    mods = {k: load(k) for k in YOLLAR}
    sonuc = senaryolar(mods, tmp)
    kirik = [(a, d) for a, ok, d in sonuc if not ok]
    for ad, ok, detay in sonuc:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok:
            print("         gorulen: %s" % detay)
    print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

    print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
    mut_kirik, kurulamadi = [], []
    for hedef, ad, mut in MUTASYONLAR:
        try:
            m_mods = dict(mods)
            m_mods[hedef] = load(hedef, mut=mut)
            m_res = senaryolar(m_mods, tmp)
            yakalandi = any(not ok for _, ok, _ in m_res)
            kacan = [a for a, ok, _ in m_res if not ok]
        except BaseException as e:      # KURULAMADI != KACTI (ucuncu deger sart)
            print("  [KURULAMADI] %s -> %s: %s" % (ad, type(e).__name__, e))
            kurulamadi.append(ad)
            continue
        print("  [%s] %s" % ("YAKALANDI" if yakalandi else "KACTI", ad))
        if yakalandi:
            print("         kiran senaryo(lar): %s" % ", ".join(k.split(":")[0] for k in kacan[:4]))
        else:
            mut_kirik.append(ad)

    # Mutasyonun GERCEKTEN uygulandigini kanitla (yama tutmazsa sahte-YESIL olur)
    print("\n--- yama-tuttu kanidi ---")
    yama_kirik = []
    ham = {k: v.read_text(encoding="utf-8") for k, v in YOLLAR.items()}
    for hedef, ad, mut in MUTASYONLAR:
        degisti = mut(ham[hedef]) != ham[hedef]
        print("  [%s] %s" % ("degisti" if degisti else "YAMA TUTMADI", ad))
        if not degisti:
            yama_kirik.append(ad)

    print("\n" + "=" * 78)
    if kirik or mut_kirik or yama_kirik or kurulamadi:
        if kirik:
            print("FAIL — senaryo: %s" % ", ".join(a.split(":")[0] for a, _ in kirik))
        if mut_kirik:
            print("FAIL — mutasyon KACTI: %s" % ", ".join(mut_kirik))
        if kurulamadi:
            print("FAIL — mutasyon KURULAMADI (olcum yapilamadi): %s" % ", ".join(kurulamadi))
        if yama_kirik:
            print("FAIL — mutasyon yamasi kaynaga UYMADI: %s" % ", ".join(yama_kirik))
        return 1
    print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(MUTASYONLAR)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
