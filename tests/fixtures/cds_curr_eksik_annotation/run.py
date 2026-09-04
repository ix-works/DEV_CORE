#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_cds_currency_reference DERINLIK: EKSIK annotation hic ARANMIYORDU.

KOK: `check_cds()` yalniz VAR OLAN annotation'in BICIMINI denetliyordu; EKSIKLIGINI
hic aramiyordu. Kapi ajaninin bilerek kirlettigi dosya (`define root view entity` +
`vbrk.netwr` = CURR + `@Semantics.amount.currencyCode` YOK + CUKY YOK) HEM root HEM
non-root surumde `rc=0 "temiz"` dondu. ⇒ *"13/13 rc=0"* gibi bir sonuc BILGI TASIMIYOR:
dosyada annotation HIC yoksa da yesil doner. (Kapsam kusuru `ea1abf1` ile kapanmisti;
DERINLIK kusuru aciktı.)

FIX — TASARIM OLCUMLE SECILDI, tahminle degil:
  · Ilk aday "DTEL sozlugunden coz" idi. Gercek korpus onu CURUTTU: proje CDS'leri
    `klm_kalem_tutari_vh` gibi OZEL kolon adlari kullaniyor ⇒ tek basina sozluk
    neredeyse hic atesler, olu gate olurdu.
  · Olcum (233 CDS): acik `abap.curr(`/`abap.quan(` cast'i **117 gecis / 20 dosya**;
    sozluk-adli kolon **81 gecis / 23 dosya** ⇒ IKI sinyal de gercek, ikisi kullanilir.
  · SIDDET = WARNING (BLOCKER DEGIL) ve bu da OLCULDU: gercek korpusta **129 CURR/QUAN
    eleman**, bunlarin **46'si / 15 dosyada** annotation'siz -- ve o dosyalar CANLIDA
    AKTIF. BLOCKER yapmak calisan 15 dosyayi aninda kirmiziya cevirirdi; ilk refleks
    kapiyi KAPATMAK olurdu (erisilemez yesil = olu gate).
  · Gercek-korpus regresyonu: 233 dosyada rc dagilimi DEGISMEDI (233x0 -> 233x0),
    46 yeni WARNING dogdu. Yani gorunurluk arttı, hicbir build bloklanmadi.

  S1-S2  kaydin BIREBIR kirli dosyasi yakalanir / annotation eklenince temizlenir
  S3     3. BAGLAM: acik cast (korpusta baskin sinyal) annotation'siz -> bulgu
  S4     ⭐ PRECISION SINIRI: IFADE icinde gecen sozluk adi bulgu SAYILMAZ (yol
         ifadesi tahmini = FP kaynagi; arac tahmin etmez)
  S5-S6  SIDDET = WARNING · CIKIS KODU = 0 (build bloklanmaz)
  S7     ⭐ PAYDA: "temiz" kac elemana bakildigini SOYLER; sifirsa kapsama iddia ETMEZ
  S8     3. BAGLAM: non-root `define view entity` ayni davranir
  S9     FP capasi: CUKY/UNIT alaninin KENDISI amount/quantity annotation'i istemez
  M1-M5  fix'i sok -> korpus KIRMIZI olmali

2026-09-04 — KUYRUK Q234 + Q237 (ayni fonksiyon, ayni belirti sinifi: YANLIS POZITIF)
  KOK: esleme FIZIKSEL satir uzerindeydi.
   Q234 cok-satirli eleman ifadesinin ARA satirlari ne `_ELEMAN`'a uyuyor ne de
        `_YAPISAL` ile basliyordu ⇒ `bekleyen = []` annotation blogunu SILIYOR.
        AYNI DOSYA ICINDE kontrol grubu: tek-satirlik kardes eleman AYNI annotation
        ile uyari URETMIYOR — tek fark satir sayisi.
   Q237 `union [all]` taninmiyordu. CDS'te element-level `@Semantics.*` YALNIZ 1.
        SELECT dalinda yazilabilir (playbook adt-cds.md T4-b: 2. dalda
        "Annotations are not allowed in this branch"); deger 1. daldan MIRAS alinir.
        ⛔ Kapinin onerdigi duzeltme (2. dala annotation ekle) AKTIVASYONU KIRAR.
  CANLI KORPUS OLCUMU (316 CDS/DDL, tuketici proje): bulgu 52 -> 9; susturulan 43'un
  31'i cok-satirli (annotation ifadenin USTUNDE) + 12'si union 2.+ dal (annotation
  1. DALDA); "kaniti olmayan" susturma 0; YENI DOGAN bulgu 0; rc dagilimi DEGISMEDI.
  ⚠ SINIR OLCULEREK SECILDI: ilk tasarim "parantez dengesi kapaninca biter" idi ve
  korpus onu CURUTTU — kusurun IKINCI yazim bicimi `case when ... end as X,` seklinde
  ve ILK SATIRI parantez bakimindan DENGELI. Dogru sinir CDS gramerinden gelir:
  eleman derinlik 0'daki ayracta (`,` `{` `}` `;`) biter.

  S10    Q234: cok-satirli `cast(...)` + annotation -> TEMIZ
  S11    ⭐ KARSI-KANIT: ayni sekil, annotation YOK -> bulgu HALA cikar (daraltma
         gercek bulguyu elemiyor)
  S12    Q234 IKINCI BICIM: `case when ... end as X,` (ilk satir paren-DENGELI)
  S13    Q237: union, annotation YALNIZ 1. dalda -> TEMIZ
  S14    ⭐ KARSI-KANIT: union, HICBIR dalda annotation yok -> TAM 1 bulgu ve o bulgu
         1. dalda (mukerrer basma YOK, sessiz yutma YOK)
  S15    Q237 SINIR: 2. dalda 1. dalda OLMAYAN alias -> bulgu + "miras kanitlanamadi"
  S16    ⭐ REGRESYON CAPASI: select listesinin SON elemani VIRGULSUZDUR; birlestirme
         onu `}` ile kaynastirirsa eleman SESSIZCE kaybolur — fix'in kendi uretebilecegi
         en tehlikeli gerileme budur
  S17    3. BAGLAM (gorev-disi): DDIC `define table` yolu birlestirmeden ETKILENMEZ
  S18    cok-satirli `@UI...` annotation araya girse de `@Semantics` DUSMEZ
  S19    tirnak-ici `(` bir sonraki annotation'i YUTMAZ (ayrac sayimi tirnak-duyarli)
  M6-M11 yeni fix'in ALTI ayri degismezi -> alti ayri mutasyon

Kosum: python tests/fixtures/cds_curr_eksik_annotation/run.py     (exit 0 = PASS)
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[2]
VALIDATORS = CORE / "scripts" / "validators"
V_PATH = VALIDATORS / "check_cds_currency_reference.py"

TMP = Path(tempfile.mkdtemp(prefix="cds_eksik_"))


def kos(cds_metni: str, validator: Path = V_PATH) -> tuple[int, str]:
    """Validator'i CLI ile kosar -> (rc, stdout+stderr).

    ⚠ CLI (subprocess) BILEREK: olculmek istenen degismez `run_review`'in gordugu
    CIKIS KODU'dur; main()'deki dallanma fonksiyon-seviyesi testte gorunmez (B24).
    """
    f = TMP / "vaka.cds"
    f.write_text(cds_metni, encoding="utf-8")
    r = subprocess.run([sys.executable, str(validator), str(f)],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout + r.stderr)


# ---------------------------------------------------------------------------
# Sekiller — S1 kaydin BIREBIR kirli dosyasidir (adlar jenerik)
# ---------------------------------------------------------------------------
KIRLI_ROOT = """define root view entity ZSD001_I_KIRLI
  as select from vbrk
{
  key vbrk.vbeln as Vbeln,
      vbrk.netwr as NetDeger
}
"""
TEMIZ_ROOT = """define root view entity ZSD001_I_TEMIZ
  as select from vbrk
{
  key vbrk.vbeln as Vbeln,
      @Semantics.amount.currencyCode: 'ParaBirimi'
      vbrk.netwr as NetDeger,
      vbrk.waerk as ParaBirimi
}
"""
CAST_ANNOTSUZ = """define root view entity ZSD001_I_CAST
  as select from vbrk
{
  key vbrk.vbeln as Vbeln,
      cast( vbrk.fkimg as abap.quan( 13, 3 ) ) as Miktar
}
"""
IFADE_ICINDE = """define root view entity ZSD001_I_IFADE
  as select from vbrk
{
  key vbrk.vbeln as Vbeln,
      coalesce( _Kalem.menge, 0 ) as TahminiMiktar
}
"""
KIRLI_NONROOT = """define view entity ZSD001_I_KIRLI2
  as select from vbrk
{
  key vbrk.vbeln as Vbeln,
      vbrk.netwr as NetDeger
}
"""
SADECE_CUKY = """define root view entity ZSD001_I_CUKY
  as select from vbrk
{
  key vbrk.vbeln as Vbeln,
      vbrk.waerk as ParaBirimi,
      vbrk.meins as Birim
}
"""
PAYDASIZ = """define view entity ZSD001_I_YALIN
  as select from vbrk
{
  key vbrk.vbeln as Vbeln,
      vbrk.bukrs as SirketKodu
}
"""

# ── Q234 / Q237 sekilleri (2026-09-04) ──────────────────────────────────────
# ⚠ Adlar ZSD001 ailesindendir (genericize allowlist'i); gercek proje objesi DEGIL.
COKSATIR_ANNOTLU = """define root view entity ZSD001_I_COKSATIR
  as select from vbrp
{
  key vbrp.vbeln as Vbeln,
      vbrp.meins as Birim,
      @Semantics.quantity.unitOfMeasure: 'Birim'
      cast( sum( case when vbrp.fktyp = 'L' then cast( vbrp.fkimg as abap.dec( 13, 3 ) )
                      else cast( 0 as abap.dec( 13, 3 ) ) end )
            as abap.quan( 13, 3 ) )                as ToplamMiktar,
      vbrp.matnr as Malzeme
}
"""
COKSATIR_ANNOTSUZ = """define root view entity ZSD001_I_COKSATIR2
  as select from vbrp
{
  key vbrp.vbeln as Vbeln,
      vbrp.meins as Birim,
      cast( sum( case when vbrp.fktyp = 'L' then cast( vbrp.fkimg as abap.dec( 13, 3 ) )
                      else cast( 0 as abap.dec( 13, 3 ) ) end )
            as abap.quan( 13, 3 ) )                as ToplamMiktar,
      vbrp.matnr as Malzeme
}
"""
# ILK SATIRI PAREN-DENGELI cok-satirli ifade — paren-tabanli sinir bunu KACIRIR
CASE_BICIMI = """define root view entity ZSD001_I_CASE
  as select from vbrk
{
  key vbrk.vbeln as Vbeln,
      vbrk.waerk as ParaBirimi,
      @Semantics.amount.currencyCode: 'ParaBirimi'
      case when vbrk.waerk <> '' and vbrk.waerk is not null
             then cast( vbrk.netwr as abap.curr( 15, 2 ) )
             else cast( 0 as abap.curr( 15, 2 ) ) end       as NetTutar,
      vbrk.bukrs as SirketKodu
}
"""
UNION_ANNOT_1DAL = """define view entity ZSD001_I_UNION
  as select from vbrp
{
  key vbrp.vbeln as Vbeln,
      vbrp.meins as Birim,
      @Semantics.quantity.unitOfMeasure: 'Birim'
      cast( vbrp.fkimg as abap.quan( 13, 3 ) )  as Miktar
}
where vbrp.fktyp = 'L'

union all

select from vbap
{
  key vbap.vbeln as Vbeln,
      vbap.vrkme as Birim,
      cast( vbap.kwmeng as abap.quan( 13, 3 ) ) as Miktar
}
where vbap.abgru = ''
"""
UNION_HIC_ANNOT = UNION_ANNOT_1DAL.replace(
    "      @Semantics.quantity.unitOfMeasure: 'Birim'\n", "")
UNION_YABANCI_ALIAS = UNION_ANNOT_1DAL.replace(
    "      cast( vbap.kwmeng as abap.quan( 13, 3 ) ) as Miktar",
    "      cast( vbap.kwmeng as abap.quan( 13, 3 ) ) as BaskaMiktar")
# SON eleman VIRGULSUZDUR ve cok satirlidir: `}` ile kaynastirilirsa KAYBOLUR
SON_ELEMAN_COKSATIR = """define root view entity ZSD001_I_SONELEMAN
  as select from vbrp
{
  key vbrp.vbeln as Vbeln,
      cast( sum( vbrp.fkimg )
            as abap.quan( 13, 3 ) )   as ToplamMiktar
}
"""
TABLO_3BAGLAM = """define table zsd001_t_kalem {
  key mandt : mandt not null;
  key belnr : belnr;
  netwr : netwr;
}
"""
# Cok satirli `@UI...` annotation araya girerse `@Semantics` DUSMEMELI.
# ⚠ SEKIL OLCULEREK SECILDI: iki satirlik `@UI` blogu AYIRT EDICI DEGILDI —
# annotation birlestirmesi soktugunde bile arta kalan parca bir SONRAKI elemana
# yapisiyor ve `bekleyen`'i dusurmuyordu (M10 ilk yazimda KACTI). Ucuncu satir
# (ikinci lineItem girdisi) parcanin derinlik 0'da VIRGULLE bitmesini saglar ⇒
# parca kendi basina bir birim olur ve `_YAPISAL` olmadigi icin bloku SIFIRLAR.
COKSATIR_ANNOTASYON = """define root view entity ZSD001_I_MULTIANNOT
  as select from vbrp
{
  key vbrp.vbeln as Vbeln,
      vbrp.meins as Birim,
      @Semantics.quantity.unitOfMeasure: 'Birim'
      @UI.lineItem: [ { position: 10,
                        label: 'Miktar' },
                      { position: 20 } ]
      cast( vbrp.fkimg as abap.quan( 13, 3 ) )  as Miktar,
      vbrp.matnr as Malzeme
}
"""
# Tirnak ICINDEKI `(` sayilirsa onceki eleman bir SONRAKI annotation'i yutar
TIRNAK_ICI_PAREN = """define root view entity ZSD001_I_TIRNAK
  as select from vbrp
{
  key vbrp.vbeln as Vbeln,
      vbrp.meins as Birim,
      cast( concat( 'A(', vbrp.matnr ) as abap.char( 20 ) ) as Kod,
      @Semantics.quantity.unitOfMeasure: 'Birim'
      cast( vbrp.fkimg as abap.quan( 13, 3 ) )              as Miktar,
      vbrp.arktx as Metin
}
"""


def senaryolar(validator: Path = V_PATH) -> list[tuple[str, bool, str]]:
    out = []

    def ekle(ad, kosul, detay=""):
        out.append((ad, bool(kosul), detay))

    # --- S1: kaydin BIREBIR kirli dosyasi (root view entity) ----------------
    rc, o = kos(KIRLI_ROOT, validator)
    ekle("S1 kaydin kirli dosyasi (root view entity, netwr, annotation YOK) yakalanir",
         "C-CDS-CUR-05" in o and "NetDeger" in o,
         "rc=%s cikti=%r" % (rc, o[:110]))

    # --- S2: FP capasi — annotation eklenince temizlenir (AYRI vektor) ------
    rc, o = kos(TEMIZ_ROOT, validator)
    ekle("S2 annotation eklenince TEMIZ (FP capasi)",
         rc == 0 and "C-CDS-CUR-05" not in o,
         "rc=%s cikti=%r" % (rc, o[:110]))

    # --- S3: 3. BAGLAM — acik cast (korpusta baskin sinyal: 117 gecis) ------
    rc, o = kos(CAST_ANNOTSUZ, validator)
    ekle("S3 3.baglam: acik `cast(... as abap.quan)` annotation'siz -> bulgu",
         "C-CDS-QUAN-05" in o and "Miktar" in o,
         "rc=%s cikti=%r" % (rc, o[:110]))

    # --- S4: ⭐ PRECISION SINIRI — ifade icindeki sozluk adi SAYILMAZ -------
    # `coalesce( _Kalem.menge, 0 )` icinde 'menge' geciyor ama elemanin TIPINI
    # kanitlamiyor (yol ifadesi). Arac TAHMIN ETMEZ; burada bulgu uretmek
    # 46 gercek bulgunun yanina gurultu koyardi.
    rc, o = kos(IFADE_ICINDE, validator)
    ekle("S4 PRECISION: ifade icindeki sozluk adi bulgu SAYILMAZ (tahmin yok)",
         "C-CDS-QUAN-05" not in o and "C-CDS-CUR-05" not in o,
         "cikti=%r" % o[:110])

    # --- S5: SIDDET = WARNING (olculmus karar: 46 canli vaka) ---------------
    rc, o = kos(KIRLI_ROOT, validator)
    ekle("S5 siddet WARNING (BLOCKER DEGIL) — 46 canli vaka bloklanmaz",
         "[WARNING]" in o and "[BLOCKER]" not in o,
         "cikti=%r" % o[:110])

    # --- S6: CIKIS KODU 0 — build bloklanmaz --------------------------------
    ekle("S6 cikis kodu 0 (yalniz WARNING varken build durmaz)",
         rc == 0, "rc=%s" % rc)

    # --- S7: ⭐ PAYDA — "temiz"in kapsami gorunur ---------------------------
    _, o_temiz = kos(TEMIZ_ROOT, validator)
    _, o_paydasiz = kos(PAYDASIZ, validator)
    ekle("S7 PAYDA: temiz cikti kac eleman denetlendigini soyler; sifirsa "
         "KAPSAMA iddia ETMEZ",
         ("1 CURR/QUAN" in o_temiz) and ("KAPSAMA iddias" in o_paydasiz),
         "temiz=%r | paydasiz=%r" % (o_temiz[-60:], o_paydasiz[-60:]))

    # --- S8: 3. BAGLAM — non-root `define view entity` ----------------------
    rc, o = kos(KIRLI_NONROOT, validator)
    ekle("S8 3.baglam: non-root `define view entity` ayni davranir",
         "C-CDS-CUR-05" in o, "cikti=%r" % o[:110])

    # --- S9: FP capasi — CUKY/UNIT alaninin KENDISI bulgu degildir ----------
    rc, o = kos(SADECE_CUKY, validator)
    ekle("S9 FP capasi: CUKY/UNIT alani amount/quantity annotation'i ISTEMEZ",
         rc == 0 and "-05" not in o, "cikti=%r" % o[:110])

    # ===================== Q234 — COK SATIRLI IFADE (2026-09-04) =============
    # --- S10: annotation VAR, ifade cok satirli -> bulgu OLMAMALI -----------
    rc, o = kos(COKSATIR_ANNOTLU, validator)
    ekle("S10 Q234: cok-satirli `cast(...)` + annotation -> TEMIZ (yanlis pozitif YOK)",
         rc == 0 and "C-CDS-QUAN-05" not in o, "rc=%s cikti=%r" % (rc, o[:140]))

    # --- S11: ⭐ KARSI-KANIT — daraltma GERCEK bulguyu elemiyor -------------
    # Gevsetme onayinin bedeli budur: FP kaniti YETMEZ, "gercek ihlal hala
    # yakalaniyor" ayrica olculur. S10 ile TEK farki annotation satiri.
    rc, o = kos(COKSATIR_ANNOTSUZ, validator)
    ekle("S11 KARSI-KANIT: ayni cok-satirli sekil annotation'SIZ -> bulgu HALA cikar",
         "C-CDS-QUAN-05" in o and "ToplamMiktar" in o,
         "rc=%s cikti=%r" % (rc, o[:140]))

    # --- S12: ikinci yazim bicimi (ilk satir paren-DENGELI) ----------------
    # ⚠ Bu vektor bir OLCUMUN kaydidir: paren-tabanli sinir tasarimi burada
    # CURUDU (`case when x <> '' and x is not null` dengelidir) ⇒ sinir CDS
    # gramerine (derinlik 0'daki ayrac) tasindi.
    rc, o = kos(CASE_BICIMI, validator)
    ekle("S12 Q234 IKINCI BICIM: `case when ... end as X,` -> TEMIZ",
         rc == 0 and "C-CDS-CUR-05" not in o, "rc=%s cikti=%r" % (rc, o[:140]))

    # ===================== Q237 — UNION DALLARI =============================
    # --- S13: annotation YALNIZ 1. dalda (SAP 2. dalda YASAKLAR) -----------
    rc, o = kos(UNION_ANNOT_1DAL, validator)
    ekle("S13 Q237: union, annotation 1. dalda -> 2. dal icin bulgu YOK (miras)",
         rc == 0 and "C-CDS-QUAN-05" not in o, "rc=%s cikti=%r" % (rc, o[:140]))

    # --- S14: ⭐ KARSI-KANIT — hicbir dalda annotation yoksa YINE yakalanir --
    # TAM 1 bulgu beklenir: 1. dal RAPORLANIR, 2. dal mukerrer BASILMAZ.
    rc, o = kos(UNION_HIC_ANNOT, validator)
    n14 = o.count("(C-CDS-QUAN-05)")
    ekle("S14 KARSI-KANIT: union'da HICBIR dalda annotation yok -> TAM 1 bulgu (1. dal)",
         n14 == 1 and "[union-miras-yok]" not in o,
         "bulgu=%d cikti=%r" % (n14, o[:200]))

    # --- S15: SINIR — 2. daldaki alias 1. dalda YOKSA sessiz yutma OLMAZ ----
    rc, o = kos(UNION_YABANCI_ALIAS, validator)
    ekle("S15 Q237 SINIR: 2. dalda 1. dalda OLMAYAN alias -> bulgu + niteleyici",
         "BaskaMiktar" in o and "[union-miras-yok]" in o,
         "cikti=%r" % o[:220])

    # --- S16: ⭐ REGRESYON CAPASI — virgulsuz SON eleman kaybolmamali -------
    rc, o = kos(SON_ELEMAN_COKSATIR, validator)
    ekle("S16 REGRESYON: cok-satirli+VIRGULSUZ son eleman `}` ile kaynasmaz",
         "C-CDS-QUAN-05" in o and "ToplamMiktar" in o, "cikti=%r" % o[:160])

    # --- S17: 3. BAGLAM (gorev-disi) — DDIC tablo yolu etkilenmez ----------
    rc, o = kos(TABLO_3BAGLAM, validator)
    ekle("S17 3.BAGLAM: `define table` yolu birlestirmeden ETKILENMEZ (BLOCKER durur)",
         rc == 1 and "C-TBL-CUR-03" in o and "netwr" in o,
         "rc=%s cikti=%r" % (rc, o[:160]))

    # --- S18: cok-satirli @UI annotation `@Semantics`'i DUSURMEZ -----------
    rc, o = kos(COKSATIR_ANNOTASYON, validator)
    ekle("S18 cok-satirli `@UI...` araya girse de `@Semantics` DUSMEZ",
         rc == 0 and "C-CDS-QUAN-05" not in o, "rc=%s cikti=%r" % (rc, o[:160]))

    # --- S19: tirnak-ici `(` bir sonraki annotation'i YUTMAZ ---------------
    rc, o = kos(TIRNAK_ICI_PAREN, validator)
    ekle("S19 tirnak-ici `(` sonraki annotation'i YUTMAZ (ayrac sayimi tirnak-duyarli)",
         rc == 0 and "C-CDS-QUAN-05" not in o, "rc=%s cikti=%r" % (rc, o[:160]))

    return out


# ---------------------------------------------------------------------------
# MUTASYONLAR — bes ayri degismez, bes ayri mutasyon.
# ⚠ MUTANT GERCEK `scripts/validators/` DIZININDE YASAR (B24 dersi): validator
# kendi yolundan `parents[1]` ile `utils.ddic_semantics`'i import eder; tempdir'e
# kopyalanirsa import OLUR ve HER mutasyon "yakalandi" gorunur (SAHTE-KIRMIZI).
# ---------------------------------------------------------------------------
MUTASYONLAR = [
    ("M1 eksiklik denetimini check_cds'ten sok (kablolama)",
     lambda s: s.replace("    violations.extend(eksik_annotation_bul(text))\n", "")),
    ("M2 acik-cast sinyalini sok (S3 dali)",
     lambda s: s.replace("    if _CAST_CURR.search(ifade):\n        return 'CURR'\n"
                         "    if _CAST_QUAN.search(ifade):\n        return 'QUAN'\n", "")),
    ("M3 sozluk sinyalini sok (S1 dali)",
     lambda s: s.replace("        if kolon in CURR_DTELS:\n            return 'CURR'\n",
                         "        if False:\n            return 'CURR'\n")),
    ("M4 siddeti BLOCKER yap (olculmus karari geri al)",
     lambda s: s.replace("                    'severity': 'WARNING',\n"
                         "                    'line': i,\n"
                         "                    'check_id': 'C-CDS-CUR-05'",
                         "                    'severity': 'BLOCKER',\n"
                         "                    'line': i,\n"
                         "                    'check_id': 'C-CDS-CUR-05'")),
    ("M5 payda satirini sok (yesilin kapsami gizlensin)",
     lambda s: s.replace(
         "            print(f'OK — {path.name} ({src_type}) CURR/QUAN reference check temiz · {kapsam}')",
         "            print(f'OK — {path.name} ({src_type}) CURR/QUAN reference check temiz')")),
    # --- 2026-09-04, Q234+Q237: ALTI degismez -> ALTI mutasyon --------------
    # ⚠ Fix IKI bagimsiz mekanizma getirdi (cok-satirli birlestirme + union mirasi)
    # ve her birinin KENDI ic sinirlari var (ayrac-basi bosaltma · annotation
    # birlestirme · tirnak-duyarli sayim). Tek mutasyon hepsini kesmez; savunma
    # derinligi kadar ayirt edici gerekir.
    ("M6 cok-satirli birlestirmeyi sok (her fiziksel satir kendi birimi = eski davranis)",
     lambda s: s.replace("        if not tam and len(buf) < _MAX_BIRLESIM_SATIR:\n"
                         "            continue\n",
                         "        if False:\n"
                         "            continue\n")),
    ("M7 union dal sayacini sok (2.+ dal yine 1. dal sanilsin)",
     lambda s: s.replace("            dal += 1\n", "            dal += 0\n")),
    ("M8 miras kuralini ASIRI genislet (2.+ dalda HIC uyarma = sessiz yutma)",
     lambda s: s.replace(
         "                eksik = alias.lower() not in (dal0_annotasyonlu | dal0_bulgulu)\n",
         "                eksik = False\n")),
    ("M9 `}` oncesi bosaltmayi sok (virgulsuz SON eleman `}` ile kaynassin)",
     lambda s: s.replace("_AYRAC_BASI = re.compile(r'^(?:union\\b|\\})', re.I)",
                         "_AYRAC_BASI = re.compile(r'^(?:union\\b)', re.I)")),
    ("M10 annotation ayrac birlestirmesini sok (cok-satirli @UI blogu bekleyeni dusursun)",
     lambda s: s.replace("        derinlik += (_denge(s, '([{', ')]}') if anot "
                         "else _denge(s, '(', ')'))",
                         "        derinlik += _denge(s, '(', ')')")),
    ("M11 ayrac sayimindan tirnak-duyarliligi sok (tirnak-ici `(` sayilsin)",
     lambda s: s.replace("        elif c in \"'\\\"\":\n            q = c\n",
                         "        elif False:\n            q = c\n")),
]


def main() -> int:
    print("=" * 78)
    print("cds_curr_eksik_annotation — DERINLIK: eksik annotation aranir mi?")
    print("=" * 78)

    sonuc = senaryolar()
    kirik = [(a, d) for a, ok, d in sonuc if not ok]
    for ad, ok, detay in sonuc:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok:
            print("         gorulen: %s" % detay)
    print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

    print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
    ham = V_PATH.read_text(encoding="utf-8")
    mut_kirik, yama_kirik = [], []
    for ad, mut in MUTASYONLAR:
        bozuk = mut(ham)
        if bozuk == ham:
            print("  [YAMA TUTMADI] %s" % ad)
            yama_kirik.append(ad)
            continue
        mutant = VALIDATORS / "_mutant_cds_curr.py"
        try:
            mutant.write_text(bozuk, encoding="utf-8")
            m_res = senaryolar(mutant)
            yakalandi = any(not ok for _, ok, _ in m_res)
            kacan = [a for a, ok, _ in m_res if not ok]
        except BaseException as e:   # cokme != FAIL
            yakalandi, kacan = True, ["kosum hatasi: %s" % type(e).__name__]
        finally:
            mutant.unlink(missing_ok=True)
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
            print("FAIL — mutasyon yamasi kaynaga UYMADI (sahte-yesil riski): %s"
                  % ", ".join(yama_kirik))
        return 1
    print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(MUTASYONLAR)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
