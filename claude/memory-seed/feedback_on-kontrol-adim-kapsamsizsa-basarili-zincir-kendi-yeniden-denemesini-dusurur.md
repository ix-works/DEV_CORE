---
name: feedback_on-kontrol-adim-kapsamsizsa-basarili-zincir-kendi-yeniden-denemesini-dusurur
description: "Çok adımlı zincirde ön-kontrol KOŞULSUZ tam kümeyle koşarsa, başarılı adımların tükettiği kaynak yeniden denemede hata olarak geri döner"
metadata:
  node_type: memory
  type: feedback
---

Çok adımlı bir belge zincirinde (sipariş → teslimat → mal çıkışı → fatura) ön-kontrol
**koşulsuz ve TAM grup kümesiyle**, üstelik **zincir durumu okunmadan ÖNCE** koşuyorsa:
başarıyla tamamlanmış adımların **tükettiği kaynak** (stok, kredi limiti, miktar) sonraki
yeniden denemede **hata olarak** geri döner ⇒ **başarılı bir zincir kendi yeniden denemesini
kalıcı olarak düşürür.** Kusur kontrolün kendisinde değil, **kapsam kararının yokluğundadır.**

**Why:** 2026-09-16, ZSD001: dört belgenin dördü de canlıda vardı (fatura dahil) ama kayıt
`C-03` (stok yetersiz) ×9 ile `06 HATA`daydı — grup 4 serbest stoğu **bu mesajın kendi
çıkardığı miktara kredi vermeden** karşılaştırıyordu. Aynı sınıf fiyat/kredi simülasyonunda
(`BAPI_SALESORDER_SIMULATE`) **latent**ti: kendi siparişimiz kredi riskini zaten yükseltmişti.
Kullanıcının teşhisi kuran cümlesi: *"bu belgenin faturası bile oluşmuş. neyi kontrolü."*

**How to apply:**
1. *"Hangi kontrol düşsün?"* diye sorma — **önce mimariyi ölç**: her kontrol grubunun hangi
   adımdan SONRA anlamsızlaştığını `dosya:satır` ile çıkar, sonra kapsam tablosunu kullanıcıya sun.
2. Kapsamı **ÇAĞIRAN verir** (`iv_adim` gibi bir OPTIONAL parametre). Motorun zincir durumunu
   bilmesi katman değişmezini kırar; çağıran zaten bilir.
3. **Fail-closed:** parametre boş / durum okunamadı ⇒ **tam küme** (bugünkü davranış). `WHEN OTHERS`
   da tam küme olsun.
4. Aynı belgeyi iki düğme kontrol ediyorsa (ör. `[İşle]` ve `[Kontrol Et]`) **ikisi de daralsın** —
   yoksa iki düğme iki farklı gerçek söyler.
5. Kapsam daraltması bir **şerhi yalanlayabilir** (*"grup 7 yalnız tam kümede çağrılır"*): şerhi silme,
   **üstünü çiz** ve gerekçeyi yeniden temellendir.

Son-doğrulama: 2026-09-16 · Applies-to: çok adımlı SD belge zincirleri (RAP/ABAP)
İlgili: [[project_zsd001-<MUSTERI-D>-konsinye]] · [[feedback_fix-oncesi-where-used-blast-radius]] ·
[[feedback_duzeltme-turu-kendi-regresyonunu-uretir]]
