# -*- coding: utf-8 -*-
"""kapsam — validator'ların ORTAK "kaç dosya tarandı" çıktı sözleşmesi (K1, 2026-08-20).

⛔ KAPATTIĞI KUSUR (ölçülmüş, kayıt satır 48+30):
Ağaç tarayan validator'lar taradıkları DOSYA SAYISINI hiç raporlamıyordu. Sonuç:
`IX_SOURCE_ROOT` / `CLAUDE_PROJECT_DIR` yanlışsa ya da kaynak klasörü taşınmışsa
validator **0 dosya tarayıp** `[OK] ... ihlali yok` diyordu — yani

    "ihlal bulamadım"  ile  "bakacak dosya bulamadım"  AYIRT EDİLEMİYORDU.

BOŞ sandbox ölçümü (2026-08-20, `CLAUDE_PROJECT_DIR`=boş proje): 12 validator
"temiz/[OK]" dedi, **6'sı HARD gate**. Kontrol grubu: aynı validator'lar dolu
sandbox'ta ihlalleri DOĞRU yakalıyor ⇒ dedektör sağlam, **kapsam kaybı görünmez**.
Görünmez kapsam kaybı, bozuk dedektörden daha tehlikelidir: yeşil ekran verir.

=== NE DEĞİL: bu bir GATE SERTLEŞTİRMESİ DEĞİLDİR (ADR 0019 / gate-moratoryumu) ===
`n == 0` **FAIL ÜRETMEZ** ve hiçbir validator'ın çıkış kodu değişmez. Sebep ölçülü:
sıfır dosya MEŞRU bir durumdur — `.bdef`i olmayan bir proje 0 `.bdef` tarar ve bu
bir ihlal değildir (`check_docu_itf_line_width` bunu zaten "DOCU runner yok" diye
dürüstçe söylüyordu; sınıfın tek doğru üyesiydi). `n == 0`ı FAIL yapmak, kapsamı
meşru şekilde boş olan her projede kalıcı kırmızı üretirdi.
⇒ Kapatılan şey SESSİZLİKTİR, gevşeklik değil. Çıktı artık PAYDAYI gösterir.

Kullanım (üç satırlık bağlama):
    from utils.kapsam import Kapsam
    KAPSAM = Kapsam(".bdef")
    for f in KAPSAM.say(files):          # ← sayaç iterator'ı sarar
        ...
    # ve "temiz" satırının sonuna:  + KAPSAM.ek()   ← payda OK satırına eklenir
    #
    # ⚠ Bu modül BİLEREK hiçbir şey basmaz (saf kütüphane) — dolayısıyla C-ENC-01
    # konsol koruması taşımaz. Yukarıdaki örneği gerçek bir çıktı çağrısı gibi
    # yazmak bu dosyayı "non-ASCII basıyor ama koruması yok" diye SUÇLATIYORDU
    # (gate metin arar, çalıştırmaz; docstring ile kodu ayırmıyor — kuyruk kalemi).

`ek()` iki biçim döner:
  n > 0  ->  "  (37 .bdef tarandı)"                       — tek satır, sessiz
  n == 0 ->  "\\n⚠ KAPSAM SIFIR: 0 .bdef tarandı — ..."    — GÖRÜNÜR + kök/kaynak yazar
`run_all_validators` her alt-validator'ın stdout'unu aynen basar (kablolama ölçüldü),
dolayısıyla bu satır toplu koşumda da görünür.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Iterator, TypeVar

T = TypeVar("T")

__all__ = ["Kapsam", "kapsam_eki"]


def _kok_izi() -> str:
    """Kapsamın NEREDEN çözüldüğünü yazar — "0 dosya" mesajının eyleme dönüşen kısmı.

    Sıfır kapsam görüldüğünde sorulacak tek soru "kök neresi çözüldü" olduğu için
    tanı satırı bunu KENDİ basar; okuyanın ayrıca env yoklaması gerekmez.
    """
    cpd = os.environ.get("CLAUDE_PROJECT_DIR")
    src = os.environ.get("IX_SOURCE_ROOT")
    return (f"kök={cpd or Path.cwd()}"
            f"{'' if cpd else ' (env CLAUDE_PROJECT_DIR YOK → cwd)'}"
            f" · IX_SOURCE_ROOT={src or '(yok → project.yaml/fallback)'}")


def kapsam_eki(n: int, birim: str) -> str:
    """OK satırına eklenecek PAYDA metni (sayaç kullanmayan çağıranlar için)."""
    if n > 0:
        return f"  ({n} {birim} tarandı)"
    return (f"\n⚠ KAPSAM SIFIR: 0 {birim} tarandı — yukarıdaki satır \"ihlal yok\" DEĞİL, "
            f"\"BAKILACAK DOSYA BULUNAMADI\" demektir.\n"
            f"   Kapsam doğru mu? {_kok_izi()}\n"
            f"   (Sıfır kapsam meşru olabilir; bu bir FAIL değil — ama sessiz de geçmez.)")


class Kapsam:
    """Taranan dosyaları sayan hafif sarmalayıcı.

    `say()` bir iterator'ı sarar: sayaç, dosya GERÇEKTEN ulaşıldığında artar —
    "listede vardı" ile "tarandı" ayrılır. Birden çok kaynağı sarabilirsin
    (ör. .js + .view.xml); sayaç birikir.
    """

    __slots__ = ("birim", "n")

    def __init__(self, birim: str) -> None:
        self.birim = birim
        self.n = 0

    def say(self, it: Iterable[T]) -> Iterator[T]:
        for x in it:
            self.n += 1
            yield x

    def ek(self) -> str:
        return kapsam_eki(self.n, self.birim)
