#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C-CDS-QTYEXPR-01 — miktar/tutar alani IFADEYE HAM giremez (check_cds_qty_in_expression).

NEDEN BU KORPUS VAR (2026-08-19 canli vaka)
-------------------------------------------
Bir tahsis gorunumunun aktivasyonu SAP tarafindan REDDEDILDI:
    "Amounts and quantities are not allowed in expression"
⚠ ADR 0006 reviewer o objeye PASS vermisti (13/13 rc=0, 0 BLOCKER). Yani hicbir YEREL
kapi bu DERLEYICI kuralini gormuyordu -- kardes kapi (`check_cds_currency_reference`)
annotation'in BICIMINE bakar, ifadedeki KULLANIMA degil (kendi docstring'i soyluyor).

⭐ BU KORPUSUN ASIL ISI PRECISION'DIR, ATESLEME DEGIL
-----------------------------------------------------
"Kapi atesliyor" bir kabul olcutu DEGILDIR. Kaydin kendisi IKI yanlis-pozitif tuzagini
CANLI OLCUMLE belgeledi ve gate'in onlari bulgu SAYMAMASINI sart kostu:
  (1) ifadesiz DOGRUDAN cast (`cast( fp.fkimg as abap.quan(13,3) )`) canlida AKTIF
  (2) BIRIM alanlari (`cast( coalesce( es.meins, fp.vrkme ) as meins )`) canlida AKTIF
S3/S4/S5 bu iki tuzagi ve `case` yuklemini civiler. Onlar silinirse gate, DOGRU yazilmis
kodu suclamaya baslar -- ki ilk (genis) tasarim tam bunu yapiyordu:

    263 gercek `.cds` uzerinde olculdu (2026-08-29):
      genis varyant (coalesce+case+aritmetik+fonksiyon) -> 49 bulgu,
        ve bunlarin arasinda kaydin KENDI "dogru emsal" dedigi IKI AKTIF gorunum vardi
      dar varyant  (yalniz `coalesce()` argumani)       -> 11 bulgu,
        dogru-emsal gorunumlerde SIFIR bulgu
    ⇒ kapsam SAYIYLA daraltildi. Bu bir GEVSETME degil, PRECISION duzeltmesidir.

⚠ KASITLI RECALL SINIRI (S6 bunu ADIYLA civiler): yalniz `coalesce()` argumani taranir.
Aritmetik/`case` yoluyla giren ham miktar YAKALANMAZ. Kaydin belgeledigi dusen bicim
`coalesce( _Assoc.Miktar, ... )` oldugu icin VAKA KAPSANIR; genisletme once bir tip
cozumleyici ister (kayit bunu ongormustu: "yol ifadelerinde SEZGISELDIR").

KOSUM:  python tests/fixtures/cds_qty_in_expression/run.py
        ... --mutasyon-cast-korlugu (siyrilmis `cast(...)` argumani da bulgu sayilir -> S2 duser)
        ... --mutasyon-annotationsuz (annotation kaniti aranmaz -> S5 duser)
Cikis:  0 hepsi beklendigi gibi · 1 sapma · 2 DOGRULANAMADI (mutasyon capasi tutmadi)
"""
from __future__ import annotations

import importlib.util
import os
import sys

from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
GATE = REPO / "scripts" / "validators" / "check_cds_qty_in_expression.py"

# ⭐ DUSEN BICIM — kaydin (2026-08-20) BIREBIR alintiladigi sekil. Miktar alani
# `coalesce()`a HAM giriyor; yanindaki `cast( 0 as ... )` onu KURTARMIYOR.
DUSEN = """define view entity ZTEST_I_DUSEN as select from ztest_es as es
  association [0..1] to ZTEST_I_LOT as _Lot on _Lot.LotId = es.lot_id
{
  key es.lfdnr as Lfdnr,
      @Semantics.quantity.unitOfMeasure: 'Meins'
      cast( coalesce( _Lot.SerbestMiktar, cast( 0 as abap.dec( 13, 3 ) ) )
            as abap.quan( 13, 3 ) )                   as SerbestMiktar,
      es.meins                                        as Meins,
}
"""

# ⭐ DOGRU DEYIM — canlida AKTIF olan bicim (ic cast VAR).
DOGRU = """define view entity ZTEST_I_DOGRU as select from ztest_es as es
  association [0..1] to ZTEST_I_LOT as _Lot on _Lot.LotId = es.lot_id
{
  key es.lfdnr as Lfdnr,
      @Semantics.quantity.unitOfMeasure: 'Meins'
      cast( coalesce( cast( _Lot.SerbestMiktar as abap.dec( 13, 3 ) ),
                      cast( 0 as abap.dec( 13, 3 ) ) )
            as abap.quan( 13, 3 ) )                   as SerbestMiktar,
      es.meins                                        as Meins,
}
"""

# FP TUZAGI #1 — IFADESIZ DOGRUDAN CAST (canlida AKTIF, bulgu SAYILMAMALI).
FP_DUZ_CAST = """define view entity ZTEST_I_DUZCAST as select from ztest_fp as fp
{
  key fp.posnr as Posnr,
      @Semantics.quantity.unitOfMeasure: 'Vrkme'
      cast( fp.fkimg as abap.quan( 13, 3 ) )          as Fkimg,
      fp.vrkme                                        as Vrkme,
}
"""

# FP TUZAGI #2 — BIRIM alani coalesce'ta (canlida AKTIF, bulgu SAYILMAMALI).
# ⛔ Bu eleman `@Semantics.quantity/amount` TASIMAZ; `@Semantics.unitOfMeasure: true`
# marker'i NOKTA ALMAZ ve _SEM_QTY'ye takilmamalidir.
FP_BIRIM = """define view entity ZTEST_I_BIRIM as select from ztest_es as es
  association [0..1] to ztest_fp as fp on fp.posnr = es.posnr
{
  key es.lfdnr as Lfdnr,
      @Semantics.unitOfMeasure: true
      cast( coalesce( es.meins, fp.vrkme ) as meins ) as Meins,
}
"""

# FP TUZAGI #3 — `case` YUKLEMINDEKI CHAR kiyasi (canlida AKTIF gorunumlerden alindi).
# Genis varyant burayi bulgu sayiyordu ve kaydin "dogru emsal"ini sucluyordu.
FP_CASE = """define view entity ZTEST_I_CASE as select from ztest_mv as mv
{
  key mv.posnr as Posnr,
      @Semantics.quantity.unitOfMeasure: 'Meins'
      cast( sum( case when mv.Tip = '' then cast( mv.Menge as abap.dec( 13, 3 ) )
                      else cast( 0 as abap.dec( 13, 3 ) ) end )
            as abap.quan( 13, 3 ) )                   as SerbestMiktar,
      mv.meins                                        as Meins,
}
"""

MUTLAR = {
    # Fix'in SOKUMU: "yalniz SADE alan/yol referansi bulgu sayilir" kosulu kaldirilir ->
    # `cast( X as abap.dec(...) )` argumani da HAM operand sayilir => DOGRU deyim de
    # bulgu olur (S2 duser). Yani "ic cast KORUYOR" degismezi olculur.
    # ⚠ ILK YAZIMDA bu mutasyon AYRI bir "cast ile basliyorsa atla" satirini
    # sokuyordu ve KACIYORDU (7/7): asagidaki fullmatch onu zaten eliyordu, yani
    # sokulen satir OLU KODDU. Kaba filtre ince filtreyi maskeliyordu; capa ASIL
    # ayirt ediciye tasindi ve olu satir kaynaktan kaldirildi.
    "--mutasyon-cast-korlugu": (
        '            if not re.fullmatch(r"(?i)[a-z_][a-z0-9_]*\\s*\\.\\s*[a-z_][a-z0-9_]*"\n'
        '                                r"|[a-z_][a-z0-9_]*", a):\n'
        "                continue",
        "            if False:\n                pass"),
    # AYRI DEGISMEZ: annotation kaniti aranmaz -> her eleman kapsama girer, BIRIM
    # alani da bulgu olur (S5 duser). ⛔ Ustteki mutasyon bunu KAPSAMAZ.
    "--mutasyon-annotationsuz": (
        "        if not _SEM_QTY.search(ann):\n            continue",
        "        if False:\n            pass"),
}

SONUC: list[tuple[str, bool, str]] = []


def ekle(ad, kosul, aciklama=""):
    SONUC.append((ad, bool(kosul), aciklama))


def main() -> int:
    for a in sys.argv[1:]:
        if a.startswith("--mutasyon") and a not in MUTLAR:
            raise SystemExit(f"[KULLANIM] bilinmeyen mutasyon kipi: {a} -> gecerli: "
                             + ", ".join(sorted(MUTLAR)))
    secili = [a for a in sys.argv[1:] if a in MUTLAR]
    ham = GATE.read_text(encoding="utf-8")
    if secili:
        eski, yeni = MUTLAR[secili[0]]
        if eski not in ham:
            print(f"[DOGRULANAMADI] mutasyon capasi tabanda bulunamadi ({secili[0]}) -> "
                  "mutasyon uygulanmadi; 'gecti' sonucu ANLAMSIZ olurdu.")
            return 2
        ham = ham.replace(eski, yeni, 1)

    # ⛔ MUTANT KARDESLERININ YANINA YAZILIR, gecici dizine DEGIL: gate `utils.project_config`
    # ve `utils.kapsam`i `Path(__file__).parents[1]` uzerinden import eder. Baska bir yere
    # koyarsak `ModuleNotFoundError: utils` alinir ve olculen sey "fix" degil KURULUM
    # HATASI olur (KURULAMADI != KACTI -- bu tuzaga bir kez dusuldu, 2026-08-29).
    # `_` onekli ad: `check_*.py` globlarina TAKILMAZ (komsu gate'leri kirletmez).
    yol = GATE.parent / "_qtygate_mutant_fixture.py"
    try:
        yol.write_text(ham, encoding="utf-8")
        spec = importlib.util.spec_from_file_location("_qtygate", yol)
        mod = importlib.util.module_from_spec(spec)
        sys.argv = ["gate"]
        spec.loader.exec_module(mod)

        n = lambda src: len(mod.tara(src))  # noqa: E731

        # === S1 DUSEN BICIM YAKALANIR (kaydin birebir alintisi) ==============
        ekle("S1 dusen bicim `coalesce( _Lot.SerbestMiktar, ... )` -> BULGU",
             n(DUSEN) == 1, f"bulgu={n(DUSEN)} (beklenen 1)")

        # === S2 ⭐ KONTROL GRUBU: DOGRU deyim bulgu URETMEZ ===================
        # ⛔ SILINEMEZ: S1 tek basina "her coalesce'a bulgu de" ile de gecerdi.
        # Bu satir, IC CAST'in gercekten ayirt edici oldugunu civiler.
        ekle("S2 KONTROL GRUBU: ic cast'li DOGRU deyim -> bulgu YOK",
             n(DOGRU) == 0, f"bulgu={n(DOGRU)} (beklenen 0)")

        # === S3 FP TUZAGI #1: ifadesiz dogrudan cast (canlida AKTIF) =========
        ekle("S3 FP: `cast( fp.fkimg as abap.quan )` (ifade YOK) -> bulgu YOK",
             n(FP_DUZ_CAST) == 0, f"bulgu={n(FP_DUZ_CAST)} (beklenen 0)")

        # === S4 FP TUZAGI #3: `case` yuklemindeki CHAR kiyasi ================
        # ⭐ Bu vektor GERCEK KORPUSTAN dogdu: genis varyant burayi bulgu sayiyor ve
        # kaydin "dogru emsal" dedigi AKTIF gorunumu sucluyordu.
        ekle("S4 FP: `case when mv.Tip = ''` yuklemi -> bulgu YOK (deger operandi degil)",
             n(FP_CASE) == 0, f"bulgu={n(FP_CASE)} (beklenen 0)")

        # === S5 FP TUZAGI #2: BIRIM alani kapsam disi =======================
        # `@Semantics.unitOfMeasure: true` NOKTA ALMAZ -> _SEM_QTY eslesmemeli.
        ekle("S5 FP: birim alani (`@Semantics.unitOfMeasure: true`) -> bulgu YOK",
             n(FP_BIRIM) == 0, f"bulgu={n(FP_BIRIM)} (beklenen 0)")

        # === S6 KASITLI RECALL SINIRI ADIYLA BELGELENIR =====================
        # ⛔ Bu bir "gecti" satiri DEGIL, bir SINIR beyanidir: aritmetik yoluyla giren
        # ham miktar BU SURUMDE yakalanmaz. Sinir sessizce degil ADIYLA durur; birisi
        # recall'i genisletirse bu satir kirmizi yanar ve karar BILINCLI verilir.
        ARITMETIK_HAM = DUSEN.replace(
            "cast( coalesce( _Lot.SerbestMiktar, cast( 0 as abap.dec( 13, 3 ) ) )\n"
            "            as abap.quan( 13, 3 ) )",
            "cast( _Lot.SerbestMiktar - es.menge as abap.quan( 13, 3 ) )")
        ekle("S6 SINIR: aritmetikle giren ham miktar BU SURUMDE yakalanmaz (kasitli recall siniri)",
             n(ARITMETIK_HAM) == 0,
             f"bulgu={n(ARITMETIK_HAM)} — 0 ise sinir hala gecerli; >0 ise recall GENISLEMIS, "
             "S6 metnini ve docstring'i guncelle")

        # === S7 CANLI KORPUS: payda ciktida + kapi COKMUYOR ==================
        # ⚠ Sandbox yesili canli yesil demek degildir.
        import subprocess
        p = subprocess.run([sys.executable, str(GATE)], capture_output=True, timeout=180,
                           cwd=str(REPO), env={**os.environ, "CLAUDE_PROJECT_DIR": str(REPO)})
        cikti = p.stdout.decode("utf-8", "replace") + p.stderr.decode("utf-8", "replace")
        ekle("S7 CANLI: kapi cokmuyor + PAYDA ('elemani kapsandi') ciktida",
             p.returncode == 0 and "elemanı kapsandı" in cikti,
             f"exit={p.returncode} cikti={cikti[-160:]!r}")
    finally:
        # ⛔ KALINTI BIRAKMA: mutant gercek `validators/` agacinda yasadi.
        if yol.exists():
            yol.unlink()

    gecen = sum(1 for _, ok, _ in SONUC if ok)
    for ad, ok, detay in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
        if not ok or os.environ.get("IX_FIXTURE_VERBOSE"):
            print(f"         -> {detay}")
    print(f"\ncds_qty_in_expression: {gecen}/{len(SONUC)}")
    if secili:
        print(f"  (MUTASYON {secili[0]} — dusmesi BEKLENEN vektorler var; "
              "tam skor 'mutasyon KACTI' demektir)")
        return 0 if gecen < len(SONUC) else 1
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
