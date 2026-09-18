---
name: feedback_yesil-sinyalin-kapsamini-sor
description: "Yeşilin KAPSAMINI sor — iki yüzü var: (1) dar bir aracın \"0 bulgu\"su geniş güvence sanılır (kusur araçta değil, okumada), (2) doğrulama ölçütündeki SABİT SAYI bayatlayınca ölçüt kendi boşluğunu yeşil gösterir"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 500a163e-c3ce-4b97-9c3d-35322425892b
---

**Bir yeşil sinyal yalnız kendi kapsamı kadar şey söyler.** Kapsamı sorulmayan yeşil, **yanlış
güven** üretir — ve bu, kırmızıdan daha tehlikelidir çünkü aramayı durdurur.

## Yüz 1 — dar araç, geniş okuma
**Vaka (2026-08-19):** Belgeler arası sayı tutarlılığını ölçen bir script yazıldı, *"**0 çelişki ·
22 dosya**"* dedi. Lider bunu *"belgeler doğru"* diye okudu ve bir tur **rahatladı**. Oysa araç
yalnız **sayı** tutarlılığına bakıyordu — atıl kalem, süpersede artığı, ters yön, alan yetimliği,
durum-makinesi erişilebilirliği **kapsamında değildi**; üstelik beş sayı kalıbını da kaçırıyordu.
Aynı gün o kapsam dışı alanlardan **40+ bulgu** çıktı.
⇒ **Kusur araçta değil, çıktısının nasıl okunduğundaydı.**

**Çare:** *"Her gate/validator/denetim aracının çıktısı **neye BAKMADIĞINI** da yazar."*
① *"bakılanlar"* listesi **koddan türetilsin** (elle liste bayatlar — bayatlık aracının beyanı
bayatlar) ② beyan **her koşumda** basılsın; **en kritik an sıfır-bulgu anıdır**.

## Yüz 2 — ölçütteki sabit sayı
**Vaka (aynı gün):** Build planının bir adımının doğrulama ölçütü *"**6 + 4 aktif**"* idi. Sonradan
**10 obje daha onaylandı** ama ölçüt güncellenmedi ⇒ 10 obje eksikken ölçüt **GEÇİYOR**. Adım,
kendi boşluğunu **yeşil** gösteriyordu. Aynı sınıf: test bölümünün kapsama beyanı *"T-01…T-40
kimliklerinin tamamı karşılandı"* diyordu — **kimlik tamlığını** ölçüyor, kabul kriteri kapsamasını
değil; 7 kabul kriteri (biri **komple bir özellik**) beyanın altından geçmişti.

**Çare:** Bir ölçüt içinde **elle yazılmış sabit sayı** varsa, o ölçüt bayatlamaya adaydır.
Ya **kanonik kaynaktan** gelsin, ya en azından yanına **kaynak atfı** yazılsın
(*"(kaynak: ADLAR §4.2-C)"*). Ve her kapsama beyanı **neyi ölçmediğini** söylesin.

**How to apply:** Bir yeşil gördüğünde refleks soru: **"bu yeşil neyi kapsıyor, neyi kapsamıyor?"**
Cevabı araçtan okuyamıyorsan yeşil **eksik bilgidir**, güvence değil. Kendi yazdığın araca karşı
bu refleksi **iki kat** uygula — kendi aracına en çok sen güvenirsin.

İlgili: [[feedback_reviewer-checklist-vs-wired-validator]] · [[feedback_exit0-degil-cikti-kaniti]] ·
[[feedback_kural-gate-lenmeli-yoksa-anlamsiz]] · [[feedback_ad-sayan-gate-elenen-adayi-sayar]] ·
[[feedback_duzeltme-turu-kendi-ciktisina-kapi-ister]]
