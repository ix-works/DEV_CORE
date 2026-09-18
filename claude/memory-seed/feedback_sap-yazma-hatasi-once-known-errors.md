---
name: feedback_sap-yazma-hatasi-once-known-errors
description: "SAP yazma/aktivasyon hatası tekrarlıyorsa ÖLÇMEDEN ÖNCE known-errors.md'de SEMPTOMU ara — hata kodu bazlı kanonik dosya odur ve çalışan yöntemi de taşır"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: edda0e20-2708-4052-a568-c399431cd5a6
---

2026-08-14, <PAKET-B> DCL turu. Sınıf ana-kaynak push'u `423 InvalidLockHandle` ile düştü.
**12 deneme, 6 tur, ~2 saat, 3 yanlış hipotez** harcandı. Kullanıcı: **"ya bu sorunu daha öncede
ara ara yaşıyorsun, ve çözüyorsun uğraştıktan sonra geçmiş tecrübelerden bak bu soruna,
lesson-learnd falan"** → tek grep'te bulundu: `core/playbook/known-errors.md` **§12.7c**,
**3 gün önce** yazılmış, başlığı semptomu birebir taşıyor ve **çalışan yöntemi** de içeriyor.
O yöntem ilk denemede tuttu.

**Why:** Hata mesajı yalan söyleyebilir — burada asıl hata `400 Session Timed Out`'tu, aracın
retry döngüsü onu `423`'e çeviriyordu. Semptomdan kök sebebe kendi başına gitmek pahalı;
`known-errors.md` **hata kodu bazlı** düzenlidir ve "DENENEN BAŞARISIZ" tablosuyla yanlış
yolları da kapatır. Arama maliyeti ~1 dk, atlamanın maliyeti ~2 saat oldu.

**How to apply:**
- SAP yazma/aktivasyon hatası **2. kez** aynı şekilde düşerse → DUR, ölçme, **ARA**:
  `Grep path=core/playbook pattern='<hata kodu veya mesaj parçası>'` (ör. `423` · `is not locked` ·
  `Session Timed Out`). Sıra: **known-errors.md → adt-*.md → lessons-learned.md → checklists**.
- Alt-ajan kanıtlı ve emin bir teşhis verse bile: *"bu cevap doğru mu"* ile *"bu cevap zaten
  yazılı mı"* **ayrı sorulardır**. Doğrulama, aramanın yerine geçmez — bugün tam olarak bu oldu.
- Görev başında bir kez arama yapmış olmak yetmez: **görev ortasında çıkan YENİ problem YENİ
  arama tetiğidir**. (Bugün DCL konusu için core arandı, push hatası için aranmadı.)
- Kontrol grubu kurarken **"değişmiş ama masum"** bir vaka şart: no-op push'lar geçtiği,
  değişmiş her içerik düştüğü için içeriğin masum bir özelliği (`WITH PRIVILEGED ACCESS` klozu)
  suçlandı. Sadece "çalışan vs çalışmayan" yetmiyor.
- Mekanik destek (2026-08-14 eklendi): `post_tool_failure` hook'u artık **Bash** yüzeyinde de
  ateşliyor ve doğrudan known-errors.md'ye yönlendiriyor. ⚠ Yeni bir SAP-yazma aracı eklenirse
  `_BASH_SAP_KOMUT_IMZALARI`'na yazılmalı, yoksa hook o araç için yine sessiz kalır.

İlgili: [[feedback_arastir-once-patinaj-uretim-gorev]] (dış araştırma ekseni) ·
[[feedback_ajan-olumsuz-donusu-kanitla-sorgula]] · [[feedback_kural-gate-lenmeli-yoksa-anlamsiz]]
(bugünün üst-deseni: kural yazıldı, ateşleyecek yere bağlanmadı — 3 örneği aynı gün çıktı).

Son-doğrulama: 2026-08-14 · Applies-to: SAP ADT yazma/aktivasyon (tüm profiller)
