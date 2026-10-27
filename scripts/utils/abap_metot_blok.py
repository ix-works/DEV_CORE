#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ABAP `METHOD <ad>.` .. `ENDMETHOD.` blok sınırı — METİNSEL, TEK KAYNAK (DEV_CORE Issue #362).

Tüketiciler (ikisi de aynı sınır kararını kullanır; ayrı desen YENİDEN TÜRETİLMEZ):
  · `mcp_servers/sap_adt/tools/query.py` `_metot_cikar` → `adt_get_method` (salt-okur)
  · `scripts/sap_client.py` `_push_method_includes` → metot include FALLBACK'i (YAZMA yolu:
    bulunan blok SAP'ye PUT edilir ⇒ yanlış sınır = yanlış kaynağın yazılması; AMDP başlıklı
    blok orada `amdp_baslik_mi` ile ATLANIR — okuma yolu AMDP'yi döndürür)

NEDEN (2026-10-27 ölçümü): iki tüketici de bitişi SATIR BAŞINA çapalı `ENDMETHOD.` ile
arıyordu. Tek satırlık `METHOD a. x = 1. ENDMETHOD.` ya da satır ortasındaki
`x = 1. ENDMETHOD.` bitişi KAÇIRILIYOR, sonraki metodun `ENDMETHOD.`una kadar giden YANLIŞ
gövde "bulundu" diye dönüyordu (sorgu aracında `found:true`, fallback'te PUT).

SÖZLEŞME — `metot_bloklari(kaynak, metot)` → `[(bas, son, metin)]`, 1-tabanlı satır:
  · başlangıç = satır başındaki `METHOD <metot>` deyimi (`METOT_BAS`; harf-durumu bağımsız)
  · bitiş = başlangıçtan sonraki İLK `METHOD`/`ENDMETHOD` DEYİMİ (satırın neresinde olursa):
      - aynı satırda yalnız bir `ENDMETHOD` → tek satırlık blok (`son == bas`)
      - sonraki satırlarda ilk deyim tek başına `ENDMETHOD` → blok o satırda biter
      - araya `METHOD` girerse ya da bitiş satırında METHOD/ENDMETHOD karışırsa
        → `son = SINIR_BELIRSIZ` (çağıran ÖLÇÜLEMEDİ der; YANLIŞ GÖVDE DÖNMEZ) ve tarama durur
      - hiç deyim yoksa → `son = None` (kapanmamış) ve tarama durur
  · deyim = satır başında ya da `.`'dan sonra gelen anahtar kelime, deyim BİÇİMİNDE
    (`ENDMETHOD.` · `METHOD <ad>.` · `METHOD <ad> BY …` · satır sonunda biten `METHOD <ad>`;
    `method = …` tanımlayıcıdır; `ENDMETHOD ##PRAGMA.` TANINMAZ — sonraki METHOD başlığı
    pragma taşımadıkça güvenli yön; başlık da pragmalıysa (`METHOD b ##P.`) a+b birleşik
    blok döner — main'den beri var, ÖLÇÜLMEDİ: derleyicinin bu başlığı kabul edip etmediği), ancak
    KOD kısmında: sütun-1 `*` yorumu, `"` satır-içi yorumu ve tek satırlık literaller (`'…'`,
    `` `…` ``, `|…|` — şablonda `\\` kaçışı atlanır) ayıklanır (`kod_kismi`).
  ⚠ SINIR (ÖLÇÜLMEDİ, bilinçli): ÇOK SATIRLI string şablonunun (`|…` satır sonunda kapanmayan)
    devam satırları KOD sayılır — orada satıra düşen `ENDMETHOD.` bitiş sanılabilir.
    Tüketicilerin KAPSAM metni bunu söyler.
"""
from __future__ import annotations

import re

METOT_BAS = re.compile(r"^\s*METHOD\s+([A-Za-z0-9_/~]+)(?=[\s.]|$)", re.IGNORECASE)
# Deyim başı: satır başı ya da `.` sonrası. `METHODS`/`CLASS-METHODS`/`ls-method` eşleşmez.
# Deyim BİÇİMİ de istenir (bug-gate #378 F3): `ENDMETHOD` ardından `.`; `METHOD` ardından
# `<ad>` + (`.` | ` BY …` AMDP). Böylece `method = 'GET'.` · çok satırlı çağrıdaki
# `method = …` · `x = 1.method = 2.` · AMDP `select t.method from …` deyim SAYILMAZ.
_DEYIM = re.compile(r"(?:^|\.)\s*(?:(ENDMETHOD)(?=\s*\.)"
                    r"|(METHOD)(?=\s+[A-Za-z0-9_/~]+\s*(?:\.|\s+BY\b|$)))", re.IGNORECASE)
# ⚠ `|$` (bug-gate 206a1c1 F5): adı satır sonunda biten başlık (`METHOD b` ⏎ `BY DATABASE …`)
# da deyimdir; yoksa araya giren böyle bir METHOD görülmez, blok sonraki metodun ENDMETHOD'una
# kadar uzar ve fallback a+b'yi a'nın include'una PUT eder (ölçüldü).
SINIR_BELIRSIZ = "sinir_belirsiz"
_AMDP_BASLIK = re.compile(r"\bBY\s+DATABASE\b", re.IGNORECASE)


def amdp_baslik_mi(blok: str) -> bool:
    """Bloğun METHOD başlık deyimi (ilk `.`'ya kadar, KOD kısmı) `BY DATABASE` taşıyor mu?

    Başlık birden çok satıra yayılabilir (`METHOD b` ⏎ `BY DATABASE PROCEDURE … USING t.`).
    Tüketici: `sap_client._push_method_includes` — AMDP bloğu YAZMA yolunda PUT edilmez.
    """
    kod = " ".join(kod_kismi(s) for s in (blok or "").split("\n"))
    return bool(_AMDP_BASLIK.search(kod.split(".", 1)[0]))


def kod_kismi(satir: str) -> str:
    """Satırın KOD kısmı: sütun-1 `*` → ''; `"` sonrası kesilir; literal içi boşluğa iner.

    Kapanmayan literal (çok satırlı `|…|` şablonu) satırın kalanını literal sayar.
    """
    if satir.startswith("*"):
        return ""
    parca, i, n = [], 0, len(satir)
    while i < n:
        c = satir[i]
        if c == '"':
            break
        if c in "'`|":
            j = i + 1
            while j < n and satir[j] != c:
                # `|…|` şablonunda `\` sonraki karakteri kaçışlar (`\|` `\\` `\{` `\}`); atlanmazsa
                # `|x\|. ENDMETHOD. |` içindeki ENDMETHOD bitiş sanılır (bug-gate #378 F1, YAZMA yolu).
                # `'…'`/`` `…` `` içinde kaçış iki katlı ayraçtır (`''`): iki ardışık literal gibi işler.
                j += 2 if (c == "|" and satir[j] == "\\") else 1
            if j >= n:
                break
            parca.append(" ")
            i = j + 1
            continue
        parca.append(c)
        i += 1
    return "".join(parca)


def deyimler(satir: str) -> list:
    """Satırdaki METHOD/ENDMETHOD deyimleri, sırayla: ['METHOD', 'ENDMETHOD', …]."""
    return [(m.group(1) or m.group(2)).upper() for m in _DEYIM.finditer(kod_kismi(satir))]


def metot_bloklari(kaynak: str, metot: str) -> list:
    """`METHOD <metot>.` .. `ENDMETHOD.` blokları → [(bas, son, metin)] (sözleşme: modül başı).

    Satır bölme yalnız `\\n` (str.splitlines Unicode ayırıcılarda da böler); `\\r` atılır.
    """
    hedef = (metot or "").strip().upper()
    satirlar = [s[:-1] if s.endswith("\r") else s for s in (kaynak or "").split("\n")]
    bulunan, i = [], 0
    while i < len(satirlar):
        m = METOT_BAS.match(satirlar[i])
        if m and m.group(1).upper() == hedef:
            ek = deyimler(satirlar[i])
            if ek[:1] == ["METHOD"]:      # başlangıç deyiminin kendisi (`.`'sı alt satırdaysa yok)
                ek = ek[1:]
            if ek == ["ENDMETHOD"]:
                bulunan.append((i + 1, i + 1, satirlar[i]))
                i += 1
                continue
            if ek:
                bulunan.append((i + 1, SINIR_BELIRSIZ, satirlar[i]))
                break
            son, bitis = None, i
            for k in range(i + 1, len(satirlar)):
                d = deyimler(satirlar[k])
                if d:
                    son, bitis = (k + 1 if d == ["ENDMETHOD"] else SINIR_BELIRSIZ), k
                    break
            if son is None:
                bulunan.append((i + 1, None, "\n".join(satirlar[i:])))
                break
            if son == SINIR_BELIRSIZ:
                bulunan.append((i + 1, SINIR_BELIRSIZ, "\n".join(satirlar[i:bitis + 1])))
                break
            bulunan.append((i + 1, son, "\n".join(satirlar[i:son])))
            i = son - 1
        i += 1
    return bulunan
