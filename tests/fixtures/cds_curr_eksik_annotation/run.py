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
