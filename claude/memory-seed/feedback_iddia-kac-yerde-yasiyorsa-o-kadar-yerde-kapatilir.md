---
name: feedback_iddia-kac-yerde-yasiyorsa-o-kadar-yerde-kapatilir
description: "Bir borç/iddia kaç artefaktta yaşıyorsa o kadarında kapatılır; ayrıca PLANLAMA belgesindeki yanlış çerçeve, build turunda KAYNAK YORUMUNA birebir kopyalanır"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e0774ea9-348e-4e2c-ae54-bd02ef91d832
---

**İki yüzü olan tek kural (02.09.2026, ZSD001 — aynı gün İKİ kez ısırdı):**

**(a) Kapanış, iddianın yaşadığı HER yerde yapılır.** `A-22 §6` borç #2 hem `TS-05 §5.2.10`
anahtar satırında hem `ZSD001_I_FATURA_BEYAN.cds:24`'teki `⏳ … düzeltilmelidir (lider)`
şerhinde yaşıyordu. Yalnız TS'i düzeltmek, kaynaktaki `⏳`'yı **bayat bir iş kalemi** olarak
bırakırdı. Aynı tur içinde `D-R70`'in *"`Edm` tel biçimi ÖLÇÜLEMEDİ"* şerhi de `D-R71`'de
ölçülünce **aynı turda** kayda çevrildi.

**(b) Planlama belgesindeki YANLIŞ çerçeve, kaynağa BULAŞIR.** `A-22 §4/C-ek`,
`ZSD001_C_TAHSIS`'i *"TS-06 §6.4.3 mini listesi"*nin besleyicisi sayıyordu. Ölçüm: `§6.4.3` =
**EKR-03**, o view ise **EKR-04** taşıyıcısı. Build turu bu gerekçeyi **kaynak yorumuna birebir
kopyaladı**; bug-gate kodda yakaladı, ama **kusur belgedeydi**. Kaynağı düzeltip belgeyi
bırakmak, bir sonraki turda aynı hatayı **yeniden üretirdi**.

**Why:** Bayat/yanlış kayıt, sonraki ajanın gözünde **otoritedir** — kapanmış işi yeniden
açtırır ya da yanlış işi doğru sandırır. Tek yerde düzeltme, kaydı **kendi kendini onaran**
değil **kendi kendini tekrarlayan** hâle getirir.

**How to apply:**
- Bir borcu/iddiayı kapatmadan önce **nerede yaşadığını ara** (TS · kaynak yorumu · `A-`
  koşu belgesi · `deferred-triggers` · RESUME · iş listesi). Kapanış **hepsinde aynı turda**.
- Build gerekçesi bir belgeden alıntı yapıyorsa, **alıntıyı yeniden ölç** (bölüm no → başlık).
  *"Belge böyle diyor"* bir kanıt değil, bir **hipotezdir** — özellikle ekran/bölüm atıflarında.
- Kapatılan şerh **silinmez**, `⏳ → ✅ … artık bir İŞ DEĞİL, KAYITTIR` diye çevrilir; yoksa
  sonraki tur onu yeniden açar.
İlgili: [[feedback_karar-degisince-kaydi-ayni-turda-guncelle]] ·
[[feedback_capadaki-acik-madde-devralmadan-once-olculur]] ·
[[feedback_kanit-yeniden-uretilebilir-bicimde-yazilir]]
