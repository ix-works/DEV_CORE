#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`IX-GATE-STATUS` SÖZLEŞMESİ — ÜRETİCİ UCU (ortak yardımcı).

Tüketici ucu `run_review.py:271-386` (`_GATE_DURUM_RE` + `gate_durum_beyani`) ve
2026-08-29'da kablolandı; o gün YALNIZ `check_abaplint.py` satırı basıyordu. Bu modül
sözleşmenin ÜRETİCİ ucunu, SAP'ye bağlanan validator ailesi için tek kaynaktan verir.

SATIR BİÇİMİ (alan sırası SABİT, satır `IX-GATE-STATUS:` ile BAŞLAR):

    IX-GATE-STATUS: gate=<ad> status=<OK|FINDING|SKIPPED|FAIL> measured=<true|false> reason=<slug>

⚠ MARKÖRÜ TARİF EDEN METİN BEYAN SAYILMAZ — tüketici iki çapa kullanır: satır-başı `^`
(re.M) ve `measured=(true|false)` TAM eşleşme. Bu yüzden yukarıdaki ÖRNEK satır girintili
yazılmıştır ve `measured=<true|false>` şablon metnidir: ikisi de beyan olarak okunmaz.
Aynı sebeple bu modüldeki hiçbir docstring/yorum satırı sütun 0'dan `IX-GATE-STATUS:`
ile başlamaz.

⛔ ÇIKIŞ KODU BU MODÜLÜN İŞİ DEĞİLDİR. Sözleşmenin bütün amacı, `exit 0`'ın ÜÇ ayrı
anlamını ("ölçtüm, temiz" · "kapsam dışı" · "koşturamadım") çıkış kodunu DEĞİŞTİRMEDEN
ayırt edilebilir kılmaktır. Çağıran `return 0` davranışını korur; ayrım bu AYRI KANALDAN
gelir. (Gerekçe: üreticinin `return 0`'ı offline reviewer zincirini kırmamak için
bilinçli seçilmişti — tek taraflı exit-kodu değişimi her offline koşumda yeni bir
BLOCKER üretirdi. Ayrımı taşıyan kanal ile bloklama kararını veren kanal ayrıdır:
bloklama kararını TÜKETİCİ (`run_review`) severity'ye göre verir.)

KULLANIM:

    from _gate_status import gate_status
    gate_status('check_sap_active_version', 'SKIPPED', False, 'sap-baglanti-yok')

`gate` alanı, tüketicinin `Path(script_name).stem` ile eşleştirdiği addır — script'in
dosya adı (uzantısız) VERİLMELİDİR, yoksa beyan "yabancı" sayılıp son beyana düşer.
"""
from __future__ import annotations

import sys

# C-ENC-01: bu modül non-ASCII taşır (yorumlar + olası gerekçe metinleri) ve Windows
# konsolu cp1252'dir → koruma olmadan UnicodeEncodeError ile ÇÖKER ve gerçek FAIL'den
# ayırt edilemeyen bir `exit 1` üretir. Çağıranların çoğu bunu zaten yapıyor; burada
# TEKRARLAMAK zararsızdır (idempotent) ve modülü tek başına import edilebilir kılar.
for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

# Tüketicinin beklediği sözlükler. Yalnız doğrulama içindir; yeni bir değer eklemek
# isteyen ÖNCE `run_review._GATE_DURUM_RE` tüketicisini ve fixture'ı güncellemelidir.
GECERLI_STATUS = frozenset({'OK', 'FINDING', 'SKIPPED', 'FAIL'})


def gate_status(gate: str, status: str, measured: bool, reason: str) -> None:
    """Sözleşme satırını stdout'a bas (tek satır, satır-başı çapalı).

    `reason` bir SLUG'dır (boşluksuz): tüketicinin regex'i `\\S+` bekler. Boşluk içeren
    bir gerekçe satırı BOZAR (ayrıştırıcı eşleşmez → beyan YOK sayılır → bugünkü
    davranışa, yani sessiz PASS'a geri düşer). Bu yüzden boşluklar `-` ile değiştirilir:
    fail-safe yön "beyanı kaybetmek" değil "beyanı ayrıştırılabilir tutmak"tır.
    """
    if status not in GECERLI_STATUS:
        raise ValueError(f'gecersiz status={status!r}; beklenen: {sorted(GECERLI_STATUS)}')
    slug = '-'.join(str(reason).split()) or 'belirtilmedi'
    ad = '-'.join(str(gate).split()) or 'bilinmeyen'
    print(f'IX-GATE-STATUS: gate={ad} status={status} '
          f'measured={"true" if measured else "false"} reason={slug}')
    # Beyan, çağıranın kendi çıktısıyla aynı akışa gider; tüketici stdout'u satır satır
    # tarar. `flush` gerekir: bazı çağıranlar bu satırdan sonra stderr'e yazıp çıkıyor ve
    # tamponlama sırası bozulursa insan-okur çıktı yanıltıcı sıralanır.
    sys.stdout.flush()


def sap_baglanti_yok(gate: str) -> None:
    """SAP bağlantısı kurulamadı — ailenin EN SIK fail-open yolu (tek satırlık kısayol).

    Ayrı bir yardımcı olmasının sebebi: bu dal altı validator'da BİREBİR aynıdır ve
    hepsinde `reason` slug'ının AYNI olması gerekir (tüketici tarafında gerekçeye göre
    gruplama yapılabilsin). Serbest metin bırakılsaydı altı ayrı slug oluşurdu.

    İstisna nesnesi BİLEREK parametre DEĞİL: gerekçe metni zaten çağıranın kendi
    `UYARI:` satırında stderr'e basılıyor; slug ise SABİT olmalı (bkz. yukarıdaki
    gerekçe). İkisini birleştirmek slug'ı istisna metnine bağımlı kılardı.
    """
    gate_status(gate, 'SKIPPED', False, 'sap-baglanti-yok')
