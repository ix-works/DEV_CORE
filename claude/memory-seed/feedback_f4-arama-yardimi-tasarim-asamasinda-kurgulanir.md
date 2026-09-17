---
name: feedback_f4-arama-yardimi-tasarim-asamasinda-kurgulanir
description: "Ekran alanlarının F4/arama yardımı mimarisi TS'te alan-alan kurgulanır; build sırasında sonradan eklenmez (ZSD001 F4 sagası tekrarlanmasın)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 2caf4c00-51c1-475d-9676-09ad5b0e676b
---

Yeni bir ekranlı geliştirme (klasik dynpro veya UI5 fark etmez) tasarlanırken,
**hangi alanın arama yardımı (F4) olacağı ve hangi mekanizmayla sağlanacağı
TS'te alan-alan yazılır** — build sırasında "sonra ekleriz" diye bırakılmaz.
Kullanıcı talimatı (2026-08-17, ZSD000 TS öncesi): *"ZSD001'te ekranlardaki
field'ların arama yardımlarıyla çok uğraşmıştın, bu defa baştan düzgün
kurgulamayı unutma; sonuçta bazı veriler seçilebilir olmalı."*

**Why:** ZSD001'te F4 tasarımı build'e ertelendi → 1 gün süren "ekran F4 sagası"
(RESEARCH-04 PA-B06): depo yeri F4'ü ÜY getirdi, kök sebep parametre eşlemesiydi,
teşhis `.tmp/`'de yazılı olduğu hâlde günler sonra aynı kapıya ikinci kez çarpıldı.
F4 mekanizması (DDIC search help / `F4IF_INT_TABLE_VALUE_REQUEST` / POV modülü /
ALV field catalog / domain fix values) alan tipine ve veri kaynağına bağlıdır;
sonradan seçilince ekran alanı tipi/parametre eşlemesi de değişmek zorunda kalır.

**How to apply:** TS'e "alan × F4 mekanizması × veri kaynağı × filtre/parametre
eşlemesi" tablosu koy; her F4 için ortak mı paket-local mi sorusunu
[[feedback_ortak-value-help-sor]] uyarınca kullanıcıya SOR. Prior-art'ı okumadan
mekanizma seçme ([[feedback_arastir-once-patinaj-uretim-gorev]]); F4 kodunun
hangi include'a düştüğü klasik program deseninin parçasıdır
([[feedback_klasik-program-include-bol]]). Başlık/metinler tahmin edilmez
([[feedback_zli-obje-text-tahmin-yasak]]).
