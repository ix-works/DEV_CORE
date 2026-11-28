"""ui5_kutuphane — UI5 reuse library KAYNAK dosyasını tanıyan TEK tanım (2026-11-28).

NEDEN: freestyle UI5 denetimleri (checklist_check FE maddeleri · check_ui5_freestyle_traps ·
check_filter_search_pattern) kaynağı `webapp/` (ya da `ui/`) segmentiyle tanıyordu. Reuse library
kaynağı `webapp/` altında DEĞİL `src/<ns-yolu>/` altındadır ⇒ kütüphane JS/fragment'ları bu
denetimlere sessizce girmiyordu (ölçüldü 2026-11-28, bir tüketici projede: `check_ui5_freestyle_traps`
15 kütüphane JS'i + 2 fragment'ı hiç taramıyordu; checklist FE maddeleri bir farktaki 17 kütüphane dosyasını
hiçbir özgül maddeye eşlemiyordu. `check_filter_search_pattern` `ui/` segmentine baktığı için `ui/` altındaki
kütüphaneyi zaten tarıyordu; `ui/` dışındaki kütüphaneyi taramıyordu).
Tanıma tek yerde durur: üç kopya ayrışırsa bir denetim kütüphaneyi görür, öbürü görmez.

TANIM (deploy_ui ile aynı kural — `deploy_ui.kutuphane_kaynak_koku`): kütüphane kaynak kökü =
`src/` ağacındaki (`src/` dahil) `.library` dosyasının dizini. Bir dosya, `src` segmentinde ya da
altında kalan en yakın atasında `.library` varsa kütüphane kaynağıdır. `.library` adı TAM eşleşir (Windows'ta `.Library`
diskte de bulunurdu, Linux'ta bulunmaz — `os.listdir` ile platformdan bağımsız).
`ui5.yaml type: library` ayrıca okunmaz: checklist_check `--diff` kipinde dosyayı git ağacından
okur, orada yalnız ad listesi vardır. `src/` olmayan dizindeki `.library` (ör. Flat build `dist/`
kökü) kaynak sayılmaz.

Bilinen sınır (ÖLÇÜLMEDİ): `ui5.yaml` `resources.configuration.paths.src` ile `src` dışına taşınmış
kaynak kökü tanınmaz.

KAHİN (`deploy_ui.kutuphane_kaynak_koku`, 10 vaka, 2026-11-28): fark 3, üçü de BİLEREK —
① iç içe ② kardeş iki `.library`: deploy_ui "tam 1 beklenir" diye reddeder (deploy güvenliği); burada
her dosya EN YAKIN köküne bağlanır (statik denetim kütüphaneyi yine taramalı) ③ `.Library` (büyük harf):
deploy_ui `rglob` Windows'ta harf duyarsız bulur, Linux'ta bulmaz; burada iki platformda da kök DEĞİL.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

KUTUPHANE_TANIM = ".library"    # deploy_ui.KUTUPHANE_TANIM ile aynı ad
KUTUPHANE_KAYNAK = "src"        # deploy_ui.KUTUPHANE_KAYNAK ile aynı ad

__all__ = ["KUTUPHANE_TANIM", "KUTUPHANE_KAYNAK", "aday_kokler", "kok_sec", "diskte_tanim_var",
           "DiskKutuphanesi"]


def aday_kokler(rel: str) -> list[str]:
    """`rel` (`/` ayraçlı göreli DOSYA yolu) için `src` segmentinde ya da ALTINDA kalan ata dizinler,
    en yakından en uzağa. `a/src/com/x/util/X.js` → [`a/src/com/x/util`, `a/src/com/x`, `a/src/com`,
    `a/src`] (`a` DEĞİL). `src/`'nin kendisi deploy_ui kahiniyle eşlik için adaydır."""
    p = rel.split("/")[:-1]
    return ["/".join(p[:i]) for i in range(len(p), 0, -1) if KUTUPHANE_KAYNAK in p[:i]]


def kok_sec(rel: str, tanim_var: Callable[[str], bool]) -> str | None:
    """`rel`'in kütüphane kökü (`.library`'nin dizini) ya da None. `tanim_var(dizin)` = o dizinde
    `.library` var mı — varlığın NEREDEN okunduğu (disk / git ağacı / girdi kümesi) çağıranındır."""
    return next((a for a in aday_kokler(rel) if tanim_var(a)), None)


def diskte_tanim_var(dizin: Path) -> bool:
    try:
        return KUTUPHANE_TANIM in os.listdir(dizin)
    except OSError:
        return False


class DiskKutuphanesi:
    """Disk ağacı tarayan denetimler için önbellekli tanıma (dizin başına bir `listdir`)."""

    def __init__(self, taban: Path):
        self.taban = Path(taban)
        self._var: dict[str, bool] = {}

    def _tanim_var(self, a: str) -> bool:
        if a not in self._var:
            self._var[a] = diskte_tanim_var(self.taban / a)
        return self._var[a]

    def kok(self, dosya: Path) -> str | None:
        """`dosya`nın (taban altında) kütüphane kökü — taban-göreli `/` ayraçlı — ya da None."""
        try:
            rel = Path(dosya).relative_to(self.taban).as_posix()
        except ValueError:
            return None
        return kok_sec(rel, self._tanim_var)
