---
name: feedback_olcumu-artefaktin-kendi-baglaminda-kos
description: "Bir artefaktın davranışını ölçerken sorguyu HAM KAYNAKTA değil, artefaktın KENDİ kısıtlarıyla (join/WHERE) koş — atlanan tek bir kısıt, artefaktın asla üretemeyeceği bir kusuru VAR gibi gösterir. Ayırt edici kolonu seçmemek iki ayrı popülasyonu sessizce tek küme yapar."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 78c7bae5-81aa-4c75-a44f-1fc2d4679222
---

**KURAL:** *"Bu view/program şu vakada yanlış davranır"* demeden önce ölçümü **artefaktın kendi
bağlamında** kur: onun join'leri, WHERE'i ve grup anahtarı ölçümde de olmalı. Ham kaynakta
yapılan sayım, artefaktın **hiç göremeyeceği** satırları da kümeye sokar ⇒ **hayalet kusur**.

**Ölçülmüş vaka (2026-09-09, ZSD001 teslimat toplama listesi).** Alt ajan, miktar netlemesinin
zorunlu olduğunu göstermek için canlı bir "regresyon" tablosu yazdı ve bunu **kodun şerhine**
işledi: `MALGIRIS` gözünde `−1 / +10 / +100` satırları var, düz `count(distinct HU)` kullanılırsa
**109 ST · 3 kasa** çıkar (doğrusu 109 · 2).

⛔ Üç satır **aynı sorguda asla buluşmuyor.** Sayım `I_EWM_AvailableStock`'ta **ambar kolonu
seçilmeden** yapılmıştı:
```
-1   -> EWMWarehouse = FDPO
+10  -> EWMWarehouse = SPDP
+100 -> EWMWarehouse = SPDP
```
View'in kendisi `:159`'da `stk.EWMWarehouse = odo.EWMWarehouse` ile join ediyor ve teslimatın
ODO ambarı **SPDP** ⇒ `−1` satırı **join'e hiç girmiyor**. Gerçek sonuç eski kuralda da yeni
kuralda da **110 · 2**; iddia edilen regresyon **canlıda yok**.

**Mekanizma — ayırt edici kolonu SEÇMEMEK iki popülasyonu birleştirir.** `MALGIRIS` göz adı ve
`9010` depo tipi **iki ambarda birden** var. Ambar kolonu `SELECT`'te olmadığı için iki ayrı
ambarın satırları tek bir gözün satırlarıymış gibi göründü. Kolon **görünmüyorsa** çakışma da
görünmez.

**Why:** Bu tuzak, [[feedback_olcum-duzeyi-kayit-ici-mi-kayitlar-arasi-mi]]'nin **ters yönüdür**.
Orada ölçüm fazla **dardı** ve sahte bir *"kusur yok"* üretti; burada fazla **genişti** ve sahte
bir *"kusur var"* üretti. İkisi de aynı kökten: ölçümün kapsamı, hakkında hüküm verilen şeyin
kapsamıyla **aynı** değil. Hayalet kusur masum görünür ("fazladan tedbir") ama üç zarar verir:
(a) yanlış kanıt **kodun şerhine** yazılır ve sonraki okuyucuyu yanıltır (b) gerçek gerekçeyi
gizler — kural yapısal olarak doğruydu, ampirik olarak değil (c) *"canlıda ölçtüm"* ibaresi
sorgulanamaz bir otorite tonu taşır.

**How to apply:**
- Ölçüm sorgusunu kurarken artefaktın **WHERE + JOIN + GROUP BY**'ını yanına koy ve **tek tek**
  ölçüme taşı. Taşımadığın her kısıt için *"bunu bilerek dışarıda bıraktım, çünkü…"* yaz.
- **Grup/join anahtarının HER kolonunu `SELECT`'e koy** — sonucu daraltmasa bile. Görünmeyen
  kolon, görünmeyen çakışma demektir. (Burada: `EWMWarehouse`.)
- Bir "regresyon vakası" bulduğunda **artefaktın gerçek anahtarıyla geri doğrula**: vakanın
  bağlı olduğu üst kayıt (belge/başlık) o satırları **fiilen kapsıyor mu?**
- **Yapısal gerekçe ile ampirik gerekçeyi AYIR.** Kural mantıktan çıkıyorsa vaka aramaya gerek
  yok; vaka uyduramıyorsan kuralı düşürme, *"bugün DEV'de ayırt eden vaka yok"* diye yaz
  ([[feedback_dev-verisi-yapi-olcer-dagilim-olcmez]] — yapı ≠ dağılım).
- Yanlış kanıt bulunduğunda **kodu değil şerhi** düzelt; kural doğruysa kural kalır.

İlgili: [[feedback_curutme-de-bir-iddiadir-yerine-yazilan-sayi-olculur]] ·
[[feedback_kapsam-niteleyicisini-dusurme]] · [[feedback_ajan-bulgusu-dogru-mekanizmasi-yanlis]] ·
[[feedback_kanit-yeniden-uretilebilir-bicimde-yazilir]] ·
[[project_ewm-embedded-erp-lgnum-cevirisi]]
