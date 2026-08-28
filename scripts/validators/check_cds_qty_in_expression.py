#!/usr/bin/env python3
"""check_cds_qty_in_expression.py — miktar/tutar alani IFADEYE HAM giriyor mu?

NEDEN (2026-08-19, bir tahsis gorunumunun aktivasyonu REDDEDILDI — ham SAP metni):

    Activation was cancelled.
    Amounts and quantities are not allowed in expression -
    DDLS <VIEW> etkinlestirilmedi

⚠ ADR 0006 reviewer o objeye PASS vermisti (13/13 rc=0, 0 BLOCKER) — `check_cds_currency_
reference` dahil. Yani bu bir DERLEYICI kuralidir ve hicbir yerel kapi onu gormuyordu.
Kardes kapi neden gormuyor (OLCULDU — kopya kusur DEGIL): o, annotation'in BICIMINE bakar
(`@Semantics.quantity.unitOfMeasure` var mi / nitelikli mi); ifadedeki KULLANIMA bakmaz ve
kendi docstring'inde bunu ACIKCA soyler: *"Ifadelerde sozluge BAKILMAZ ... yol ifadesi
tahmini = FP kaynagi"*. Bu dosya o karari BOZMAZ: sozluge yine bakmaz — ELEMANIN KENDI
annotation'ini kanit olarak kullanir.

OLCULMUS KURAL (iki AKTIF gorunumden turetildi):
  CURR/QUAN tipli bir deger `coalesce()`, aritmetik (`+ - * /`) veya `case...when`
  IFADESINE HAM giremez; once `cast( ... as abap.dec( n, m ) )` ile siyrilmali,
  ifade sonunda `cast( ... as abap.quan( n, m ) )` ile geri donulmelidir.
    OK  dogru emsal : cast( coalesce( cast( X as abap.dec(13,3) ),
                                      cast( 0 as abap.dec(13,3) ) ) as abap.quan(13,3) )
    NOK dusen bicim : coalesce( _Assoc.SerbestMiktar, cast( 0 as abap.dec(13,3) ) )
                      (miktar alani coalesce'a HAM giriyor — ic cast yok)

⛔ IKI YANLIS-POZITIF TUZAGI BILEREK DISARIDA (ikisi de CANLIDA AKTIF olcumle elendi):
  1. IFADESIZ DOGRUDAN CAST sorunsuzdur: `cast( fp.fkimg as abap.quan( 13, 3 ) )`
     — birebir bu bicim canlida aktive oldu. Bu dosya YALNIZ ifade baglami
     (coalesce / aritmetik / case) iceren elemanlara bakar.
  2. BIRIM / PARA-KODU alanlari (MEINS/WAERS) kuralin DISINDADIR:
     `cast( coalesce( es.meins, fp.vrkme ) as meins )` canlida aktiftir. Bu eleman
     `@Semantics.quantity/amount` TASIMAZ -> zaten kapsam disi kalir.

⛔ SIDDET: WARNING (bulguda exit 0). Kaydin kendi karari: kuralin dogru uygulanmasi
alanin TIPINI bilmeyi gerektirir; yol ifadesi (`_Assoc.Alan`) hedef gorunumun kaynagina
bakmayi gerektirir ⇒ saf metin taramasi YEREL elemanlarda kesin, yol ifadelerinde
SEZGISELDIR. Bu yuzden gate WARNING olarak BASLAR, BLOCKER degil.
Bulguda exit 1 isteyen opt-in: `--bulguda-exit1`.
⚠ `--strict` BILEREK NO-OP: `run_all_validators --strict` bayragi TUM validator'lara
iletilir; warn-first bir kapi oradan KAZARA bloklayiciya terfi etmemeli (olculmus sinif).

KAPSAM: yalniz `.cds`. Elemanin QUAN/CURR oldugunun KANITI = elemanin KENDI ustundeki
`@Semantics.quantity.*` / `@Semantics.amount.*` annotation'i. Annotation yoksa eleman
KAPSAM DISIDIR (uydurma yok) — bu KASITLI bir RECALL sinirdir ve cikti onu SAYIYLA bildirir.

Kullanim:
    python scripts/validators/check_cds_qty_in_expression.py [<artifact.cds>] [--bulguda-exit1]
Cikis: 0 temiz VEYA bulgu-var-ama-warn-first · 1 (yalniz --bulguda-exit1 ile) · 2 OLCULEMEDI
"""
# ENFORCES: C-CDS-QTYEXPR-01  (ADR 0019 coverage binding)
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.project_config import SOURCE_ROOT_NAME, project_root  # noqa: E402  (K12)
from utils.kapsam import Kapsam  # noqa: E402  (K1: ortak payda sozlesmesi)

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

KAPSAM = Kapsam(".cds")

# ⚠ `worktrees` prune: ajan worktree'leri kok agacin KOPYASIDIR; taranirsa ayni bulgu
# N kez listelenir ve gercek bulgular gurultude kaybolur (8-validator prune deseni).
_PRUNE = {"node_modules", ".git", "dist", "coverage", ".tmp", "tmp", "worktrees"}

_BLOK_YORUM = re.compile(r"/\*.*?\*/", re.S)
# Miktar/tutar SEMANTIGI tasiyan annotation. ⛔ Birim/para-kodu MARKERLARI HARIC:
# `@Semantics.unitOfMeasure: true` ve `@Semantics.currencyCode: true` nokta ALMAZ.
_SEM_QTY = re.compile(r"@Semantics\.(quantity|amount)\.", re.I)
_COALESCE = re.compile(r"\bcoalesce\s*\(", re.I)
_CASE = re.compile(r"\bcase\b", re.I)
_ARITMETIK = re.compile(r"[+\-*/]")
_REF = re.compile(r"\b(?:[A-Za-z_][A-Za-z0-9_]*\s*\.\s*)?[A-Za-z_][A-Za-z0-9_]*\b")
# Referans SAYILMAYAN sozcukler (SQL/CDS anahtar sozcukleri + tip adlari + fonksiyonlar).
_ANAHTAR = {
    "coalesce", "case", "when", "then", "else", "end", "as", "cast", "abap", "dec",
    "quan", "curr", "char", "int4", "int8", "numc", "dats", "tims", "sum", "min",
    "max", "avg", "count", "div", "mod", "and", "or", "not", "null", "is", "distinct",
    "cross", "join", "on", "left", "outer", "inner", "concat", "substring", "lpad",
    "true", "false", "meins", "waers", "unit", "currency",
}


def _kod(metin: str) -> str:
    """Blok/satir yorumlarini ve tek-tirnakli literalleri notrler (FP kaynagi).

    ⚠ ZORUNLU: bu evde `.cds` yorumlari kuralin KENDISINI anlatiyor olabilir
    (`// IC CAST ZORUNLU: ... coalesce( _Assoc.X ...`). Yorum notrlenmezse kurali
    BELGELEYEN dosya kurali IHLAL EDIYOR gibi gorunur — kendi kendini yakalayan kapi.
    """
    m = _BLOK_YORUM.sub(lambda x: "\n" * x.group(0).count("\n"), metin)
    out = []
    for satir in m.splitlines():
        s = re.sub(r"'[^']*'", "''", satir)
        k = s.find("//")
        out.append(s[:k] if k >= 0 else s)
    return "\n".join(out)


def _deger_disi_baglamlari_sok(ifade: str) -> str:
    """DEGER operandi OLMAYAN baglamlari siler.

    ⛔ BU FONKSIYON KORPUS OLCUMUYLE DOGDU (2026-08-29), tasarimdan degil. Ilk yazim
    263 gercek `.cds`te 49 bulgu uretti ve bunlarin arasinda kaydin KENDI "dogru emsal"
    diye gosterdigi IKI AKTIF gorunum de vardi. Sebep sistematik ve tek bir sinifti:

      · `case when <KOSUL> then <DEGER>` — kuralin ilgilendigi sey DEGER operandidir.
        KOSUL'daki `mv.Tip = ''` / `it.matnr_ovr <> ''` gibi CHAR kiyaslari miktar
        DEGILDIR; SAP onlari "expression"da miktar saymaz. Onlari operand sanmak,
        dogru yazilmis her `case`i bulgu yapiyordu.
      · `f( ad => deger )` — adlandirilmis fonksiyon argumani (ör. para birimi
        cevrimi). Bu, standart CDS fonksiyon cagrisidir ve canlida AKTIFTIR.

    Ikisi de silinince geriye YALNIZ gercek deger operandlari kalir.
    ⚠ Bu bir GEVSETME DEGIL, KAPSAM DUZELTMESIDIR: silinen bolgeler kuralin hic
    kapsamadigi sozdizimsel konumlardir. Kaydin dusen bicimi (`coalesce( _Assoc.X, ...)`)
    bu silmelerden ETKILENMEZ — negatif test bunu civiler.
    """
    # `when ... then` arasindaki KOSUL bolgesi (deger degil, yuklem).
    s = re.sub(r"\bwhen\b.*?\bthen\b", " then ", ifade, flags=re.I | re.S)
    # Adlandirilmis fonksiyon argumani: `ad => deger` -> `ad` da `deger` de operand degil.
    s = re.sub(r"[A-Za-z_][A-Za-z0-9_]*\s*=>\s*[A-Za-z_][A-Za-z0-9_.]*", " ", s)
    return s


def _cast_govdelerini_sok(ifade: str) -> str:
    """`cast( <govde> as <tip> )` -> govde SILINIR (siyrilmis sayilir).

    ⛔ NEDEN GOVDE SILINIR: dogru deyimde miktar alani `cast( X as abap.dec(...) )`
    ICINDEDIR. Onu silince geriye YALNIZ siyrilmamis operandlar kalir — bulgu tam odur.
    En ICTEKI cast'tan baslanir (ic ice cast dogru deyimin kendisidir).
    """
    onceki = None
    s = ifade
    while onceki != s:
        onceki = s
        s = re.sub(r"\bcast\s*\((?:(?!\bcast\s*\().)*?\)", " ", s, count=1,
                   flags=re.I | re.S)
    return s


def _elemanlar(kaynak: str):
    """(satir_no, annotation_blogu, ifade) — select listesindeki `... as Alias,` ogeleri.

    KASITLI OLARAK DAR: yalniz `as <Alias>,` ile biten ogeler. Cozulemeyen yapilar
    bulgu URETMEZ (uydurma yok); kapsanan eleman sayisi ciktida SAYIYLA bildirilir.
    """
    tampon: list[str] = []
    ann: list[str] = []
    bas = 0
    for i, ham in enumerate(kaynak.splitlines(), 1):
        s = ham.strip()
        if not s:
            continue
        if s.startswith("@"):
            ann.append(s)
            continue
        if not tampon:
            bas = i
        tampon.append(s)
        birlesik = " ".join(tampon)
        if re.search(r"\bas\s+[A-Za-z_][A-Za-z0-9_]*\s*,\s*$", birlesik, re.I):
            yield bas, " ".join(ann), birlesik
            tampon, ann = [], []


def _coalesce_argumanlari(ifade: str):
    """Her `coalesce( ... )` cagrisinin ILK SEVIYE argumanlarini uretir."""
    for m in _COALESCE.finditer(ifade):
        i = m.end()
        derinlik, j = 1, i
        while j < len(ifade) and derinlik > 0:
            if ifade[j] == "(":
                derinlik += 1
            elif ifade[j] == ")":
                derinlik -= 1
            j += 1
        icerik = ifade[i:j - 1]
        arg, d = "", 0
        for ch in icerik:
            if ch == "(":
                d += 1
            elif ch == ")":
                d -= 1
            if ch == "," and d == 0:
                yield arg
                arg = ""
            else:
                arg += ch
        yield arg


def tara(kaynak: str):
    """(satir_no, alias, siyrilmamis_operandlar, ifade) listesi.

    ⛔ KAPSAM KORPUS OLCUMUYLE DARALTILDI (2026-08-29) — tasarimla degil, SAYIYLA.
    263 gercek `.cds` uzerinde uc varyant olculdu:

      varyant                                  | bulgu | dogru-emsal FP'si
      -----------------------------------------|-------|-------------------
      coalesce + case + aritmetik + fonksiyon   |  49   | VAR (2 aktif gorunum)
      ... `when` yuklemi ve `ad =>` cikarilmis  |  ~30  | VAR (currency_conversion)
      YALNIZ `coalesce()` argumani (bu surum)   |  13   | YOK

    Genis varyantlar, kaydin KENDI "dogru emsal" diye gosterdigi AKTIF gorunumleri
    bulgu sayiyordu — yani gate, dogru yazilmis kodu suclayacakti. `case` yuklemindeki
    CHAR kiyaslari (`mv.Tip = ''`) ve standart `currency_conversion( amount => ... )`
    cagrisi miktar-ifadesi DEGILDIR; onlari operand saymak precision'i yok ediyordu.

    ⚠ BEDEL ACIKCA KABUL EDILDI — RECALL: bu surum yalniz `coalesce()` argumanina bakar.
    Aritmetik/`case` yoluyla giren HAM miktar YAKALANMAZ. Kaydin belgeledigi DUSEN
    bicim tam olarak `coalesce( _Assoc.Miktar, ... )` oldugu icin vaka KAPSANIR;
    genisletme, once precision'i koruyan bir tip-cozumleyici ister (kayit bunu zaten
    ongormustu: "yol ifadelerinde SEZGISELDIR").
    """
    bulgular = []
    for satir, ann, ifade in _elemanlar(_kod(kaynak)):
        if not _SEM_QTY.search(ann):
            continue  # QUAN/CURR KANITI YOK -> kapsam disi (uydurma yok)
        ham_operandlar = []
        for arg in _coalesce_argumanlari(ifade):
            a = arg.strip()
            if not a:
                continue
            if re.fullmatch(r"\d+", a) or re.fullmatch(r"'[^']*'", a):
                continue                                  # literal -> miktar degil
            # ⭐ TEK VE ASIL AYIRT EDICI: bulgu YALNIZ operand SADE bir alan/yol
            # referansiysa uretilir (`es.menge` · `_Assoc.Miktar` · `netwr`).
            # Bu TEK kosul iki isi birden yapar:
            #   · `cast( X as abap.dec(...) )` -> sade referans DEGIL => SIYRILMIS sayilir
            #   · `sum(...)` / ic ice `case`   -> sade referans DEGIL => uydurma bulgu YOK
            # ⛔ BURAYA AYRI BIR "cast ile basliyorsa atla" SATIRI KOYMA: bir kez konuldu
            # ve OLU CIKTI — asagidaki fullmatch onu zaten eliyordu. Dahasi olu satir
            # ZARARLIYDI: onu soken mutasyon sonucu DEGISTIRMIYOR, yani KACIYORDU (7/7).
            # Gereksiz savunma-derinligi, gercek degismezin OLCULEBILIRLIGINI yok eder
            # (bu turda IKINCI vaka; ilki `check_rule_gate_coverage` kismi-korluk dali).
            if not re.fullmatch(r"(?i)[a-z_][a-z0-9_]*\s*\.\s*[a-z_][a-z0-9_]*"
                                r"|[a-z_][a-z0-9_]*", a):
                continue
            if a.lower() in _ANAHTAR or a.split(".")[-1].lower() in _ANAHTAR:
                continue                                  # meins/waers vb. -> kapsam disi
            ham_operandlar.append(a)
        if ham_operandlar:
            alias = re.search(r"\bas\s+([A-Za-z_][A-Za-z0-9_]*)\s*,\s*$", ifade, re.I)
            bulgular.append((satir, alias.group(1) if alias else "?",
                             sorted(set(ham_operandlar)), " ".join(ifade.split())[:160]))
    return bulgular


def main() -> int:
    ap = argparse.ArgumentParser(description="CDS: miktar/tutar alani ifadeye HAM giremez")
    ap.add_argument("path", nargs="?", help="taranacak .cds (run_review pozisyonel artifact)")
    ap.add_argument("--file")
    # ⛔ NO-OP (bilincli): run_all_validators --strict'i HERKESE iletir; warn-first bir
    # kapi oradan kazara bloklayiciya terfi etmemeli. Terfi TARIHLI bir karardir.
    ap.add_argument("--strict", action="store_true",
                    help="NO-OP (uyumluluk) — siddeti DEGISTIRMEZ; bkz. --bulguda-exit1")
    ap.add_argument("--bulguda-exit1", action="store_true",
                    help="opt-in: bulgu varsa exit 1 (varsayilan warn-first exit 0)")
    args, _ = ap.parse_known_args()

    kok = project_root()
    hedef = args.file or args.path
    if hedef:
        p = Path(hedef)
        if not p.exists():
            print(f"[ÖLÇÜLEMEDİ] {p} bulunamadı — 'temiz' DEĞİLDİR.", file=sys.stderr)
            return 2
        if p.suffix.lower() != ".cds":
            print(f"OK — {p.name} .cds değil; bu kuralın kapsamı dışında (KOŞMADI, temiz DEĞİL).")
            return 0
        dosyalar = [p]
    else:
        dosyalar = []
        for r, ds, fs in os.walk(kok / SOURCE_ROOT_NAME):
            ds[:] = [d for d in ds if d not in _PRUNE]
            dosyalar += [Path(r) / f for f in fs if f.lower().endswith(".cds")]

    toplam = 0
    kapsanan = 0
    for f in KAPSAM.say(dosyalar):
        try:
            metin = f.read_text(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            continue
        kapsanan += len(_SEM_QTY.findall(_kod(metin)))
        for satir, alias, refler, ifade in tara(metin):
            toplam += 1
            rel = f.relative_to(kok) if str(f).startswith(str(kok)) else f
            print(f"[BULGU] {rel}:{satir}  ({alias}) miktar/tutar elemanı İFADEYE HAM giriyor: "
                  f"{', '.join(refler)}", file=sys.stderr)
            print(f"        → {ifade}", file=sys.stderr)

    # ⛔ PAYDA DAIMA BASILIR: "ihlal yok" ile "bakacak sey yoktu" AYRI seylerdir.
    print(f"CDS miktar/tutar-ifade kontrolü: {toplam} bulgu · "
          f"{kapsanan} `@Semantics.quantity/amount` elemanı kapsandı." + KAPSAM.ek())
    if toplam:
        print(f"\n{toplam} bulgu (WARNING — warn-first, commit'i DURDURMAZ). "
              "Onarım: ifadeye giren her miktar/tutar operandını "
              "`cast( <alan> as abap.dec( n, m ) )` ile sıyır, ifadenin sonunda "
              "`cast( ... as abap.quan( n, m ) )` ile geri dön. "
              "⚠ Yol ifadelerinde (`_Assoc.Alan`) bu tarama SEZGİSELDİR — hedef "
              "görünümün tipini DOĞRULA, körü körüne susturma.", file=sys.stderr)
        return 1 if args.bulguda_exit1 else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
