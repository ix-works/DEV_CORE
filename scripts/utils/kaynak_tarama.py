# -*- coding: utf-8 -*-
"""kaynak_tarama — icerik-validator'lari icin ORTAK "normalize edilmis tarama" katmani.

NEDEN VAR (2026-08-28, adversarial bug-avi B2 ailesi — 8 kalem, TEK kok):
icerik-validator'larimizin cogu kaynagi **ham satir** olarak gorup satir-basina regex
kosturuyordu. Bu üc sinif hatayi ayni anda uretir:

  1. **SATIR-KAPSAMI (kacis):** dil ifadesi iki satira boluncE desen eslesmez.
     `COMMIT` \\n `WORK.` — ABAP'ta gecerli TEK ifadedir, gate icin iki satirdir.
     `TYPE c` \\n `LENGTH 100` — ayni sinif.
  2. **YORUM-DURUMU (yanlis-pozitif):** cok-satirli `/* ... */` blogunun ICI kod
     sayilir; olu/ornek kod BLOCKER uretir. `startswith("*")` yalnizca JSDoc tarzi
     hizali bloklari yakalar; yildizsiz blok tamamen acikta kalir.
  3. **LITERAL-DURUMU (iki yonlu):** string literalinin ICINDEKI anahtar kelime
     ihlal sayilir (FP), ve literal icindeki tirnak/`"` yorum-baslangici sanilip
     satirin gerisi ATILIR (kacis).

Bu modul o üc durumu TEK yerde cozer; validator'lar desenlerini degistirmeden
normalize edilmis metin uzerinde arar. Desen kumeleri ve siddetler validator'da kalir
(davranis sahibi orasidir); burada YALNIZ "hangi karakter kod, hangisi degil" yasar.

SINIR (bilerek):
  - Tam bir ABAP/JS ayristiricisi DEGILDIR. Amac ham-satir taramasinin ustune
    olculebilir bir kat cikmak; %100 dogruluk degil.
  - ABAP satir-yorumu tespiti mevcut validator davranisiyla ayni tutuldu
    (`lstrip().startswith("*")` = tam-satir yorumu) — degistirmek davranis kaymasi olurdu.
  - JS'te string durumu SATIR SONUNDA sifirlanir (template literal dahil). Dengesiz
    tirnak (ör. regex literali icindeki `'`) yalnizca O SATIRI etkiler, dosyanin
    gerisini degil — hasari sinirli tutmak icin bilincli secim.

Kullanan: check_no_rap_commit · check_amdp_comment_apostrophe ·
          check_method_param_type_c · check_filter_search_pattern ·
          check_ui5_freestyle_traps
"""
from __future__ import annotations

import re
from bisect import bisect_right

__all__ = [
    "abap_satir",
    "abap_kod",
    "MantiksalMetin",
    "amdp_govde_araliklari",
    "sqlscript_yorumu",
    "js_kod",
]


# ══════════════════════════════════════════════════════════════════ ABAP ══════

def abap_satir(ham: str) -> tuple[str, str]:
    """Tek ABAP satirini normalize eder → (kod, kod_literalsiz).

    - Tam-satir yorumu (`*` ile baslar) → ("", "")
    - Satir-ici yorum: literal DISINDAKI ilk `"` ve sonrasi atilir
      (ham `line.find('"')` bunu literal-korumasiz yapiyordu → `'a"b'` satirin
      gerisini yutuyordu = sessiz kacis).
    - `kod_literalsiz`: `'...'` literallerinin ICI bosluga cevrilir (uzunluk korunur;
      ofset→satir eslemesi bozulmasin). Literal SINIRLARI (`'`) yerinde kalir.
      `''` (ABAP escape) da bosaltilir.

    Iki cikti neden AYRI: bazi desenler literal ICINDE de gercek ihlaldir
    (`CALL FUNCTION 'BAPI_TRANSACTION_COMMIT'`), bazilari literal icinde
    yanlis-pozitiftir (`lv_metin = 'COMMIT WORK yapilmadi'`). Karari cagiran verir.
    """
    if ham.lstrip().startswith("*"):
        return "", ""
    kod: list[str] = []
    kodsuz: list[str] = []
    i, n, literalde = 0, len(ham), False
    while i < n:
        ch = ham[i]
        if literalde:
            kod.append(ch)
            if ch == "'":
                if i + 1 < n and ham[i + 1] == "'":       # '' = escape'li tirnak
                    kod.append("'")
                    kodsuz.append("  ")
                    i += 2
                    continue
                literalde = False
                kodsuz.append("'")
            else:
                kodsuz.append(" ")
            i += 1
            continue
        if ch == '"':                                      # literal DISINDA → yorum
            break
        kod.append(ch)
        kodsuz.append(ch)
        if ch == "'":
            literalde = True
        i += 1
    return "".join(kod), "".join(kodsuz)


def abap_kod(metin: str) -> list[tuple[int, str, str]]:
    """Dosya → [(satir_no, kod, kod_literalsiz)] (1-tabanli)."""
    return [(i, *abap_satir(ham)) for i, ham in enumerate(metin.splitlines(), 1)]


class MantiksalMetin:
    """Satir parcalarini `\\n` ile birlestirip ofset→satir_no eslemesi tutar.

    NEDEN: ABAP ifadesi satira degil NOKTAYA baglidir. `COMMIT\\nWORK.` tek ifadedir.
    Birlesik metinde `\\s+` satir sonunu da eslestirir → cok-satirli ifade yakalanir.
    Ifade siniri KENDILIGINDEN korunur: aradaki `.` (ifade sonu) `\\s+` ile eslesmez,
    yani `... COMMIT.\\nWORK = 1.` YANLIS-POZITIF vermez.
    """

    def __init__(self, parcalar: list[tuple[int, str]]):
        self._satirlar = [p[0] for p in parcalar]
        self._ofsetler: list[int] = []
        o = 0
        for _, kod in parcalar:
            self._ofsetler.append(o)
            o += len(kod) + 1                              # +1 = "\n"
        self.metin = "\n".join(kod for _, kod in parcalar)

    def satir_no(self, ofset: int) -> int:
        if not self._satirlar:
            return 1
        idx = bisect_right(self._ofsetler, ofset) - 1
        return self._satirlar[max(idx, 0)]

    def bul(self, rx: re.Pattern) -> list[tuple[int, int]]:
        """[(baslangic_satiri, bitis_satiri)] — eslesme basi ve sonu."""
        return [(self.satir_no(m.start()), self.satir_no(max(m.end() - 1, m.start())))
                for m in rx.finditer(self.metin)]


# ═══════════════════════════════════════════════════════ AMDP / SQLScript ══════

_AMDP_BAS = re.compile(r"BY\s+DATABASE\s+(?:PROCEDURE|FUNCTION)", re.IGNORECASE)
_AMDP_SON = re.compile(r"^\s*ENDMETHOD\b", re.IGNORECASE)


def amdp_govde_araliklari(metin: str) -> list[tuple[int, int]]:
    """AMDP govde satir araliklari [(bas, son)] — 1-tabanli, ikisi de DAHIL.

    `... BY DATABASE PROCEDURE ...` satirindan `ENDMETHOD`e kadar. Bu aralik ICINDE
    `--` bir SQLScript yorumudur; DISINDA ABAP kodudur (`--` orada yorum DEGILDIR,
    ve `*`/`"` ABAP yorumlarinda apostrof MESRUDUR).
    """
    araliklar: list[tuple[int, int]] = []
    bas: int | None = None
    for i, ham in enumerate(metin.splitlines(), 1):
        if bas is None:
            if _AMDP_BAS.search(ham):
                bas = i
        elif _AMDP_SON.match(ham):
            araliklar.append((bas, i))
            bas = None
    if bas is not None:                                    # kapanmamis govde → dosya sonu
        araliklar.append((bas, len(metin.splitlines())))
    return araliklar


def sqlscript_yorumu(ham: str) -> str | None:
    """Satirdaki SQLScript `--` yorum GOVDESINI dondurur (yoksa None).

    `--` yalnizca string literali DISINDA yorum baslatir: `WHERE x = 'a--b'` yorum
    DEGILDIR. Satir-basi capasi YOKTUR — satir SONUNDAKI yorum da yakalanir
    (`SELECT foo -- Ali'nin notu` eski `^\\s*--` capasindan kaciyordu).
    """
    i, n, literalde = 0, len(ham), False
    while i < n:
        ch = ham[i]
        if literalde:
            if ch == "'":
                if i + 1 < n and ham[i + 1] == "'":
                    i += 2
                    continue
                literalde = False
            i += 1
            continue
        if ch == "'":
            literalde = True
            i += 1
            continue
        if ch == "-" and i + 1 < n and ham[i + 1] == "-":
            return ham[i + 2:]
        i += 1
    return None


# ════════════════════════════════════════════════════════════ JavaScript ══════

def js_kod(metin: str) -> list[tuple[int, str]]:
    """JS dosyasi → [(satir_no, kod)] — `/* */` bloklari ve `//` yorumlari SILINMIS.

    Blok yorumu DOSYA GENELINDE durumludur (cok-satirli). Satir yapisi korunur:
    yorum icerigi bosluga cevrilir, satir sayisi degismez → bulgu satir numaralari
    ham dosyayla ayni kalir.

    `/*` ve `//` yalnizca string DISINDA yorum baslatir; boylece `"http://x"` satirin
    gerisini yutmaz. String durumu satir sonunda SIFIRLANIR (bkz. modul SINIR notu).
    """
    cikti: list[tuple[int, str]] = []
    blokta = False
    for no, ham in enumerate(metin.splitlines(), 1):
        parcalar: list[str] = []
        i, n = 0, len(ham)
        tirnak: str | None = None
        while i < n:
            ch = ham[i]
            if blokta:
                if ch == "*" and i + 1 < n and ham[i + 1] == "/":
                    blokta = False
                    i += 2
                else:
                    i += 1
                continue
            if tirnak is not None:
                parcalar.append(ch)
                if ch == "\\" and i + 1 < n:
                    parcalar.append(ham[i + 1])
                    i += 2
                    continue
                if ch == tirnak:
                    tirnak = None
                i += 1
                continue
            if ch in "\"'`":
                tirnak = ch
                parcalar.append(ch)
                i += 1
                continue
            if ch == "/" and i + 1 < n and ham[i + 1] == "/":
                break                                       # satir yorumu
            if ch == "/" and i + 1 < n and ham[i + 1] == "*":
                blokta = True
                i += 2
                continue
            parcalar.append(ch)
            i += 1
        cikti.append((no, "".join(parcalar)))
    return cikti
