---
name: atc-pretty-print-birim-basina-ilk-fark
description: ATC "Incorrect Pretty Print state" birim başına (metot / ccau / ccimp include) yalnız İLK fark satırını bildirir — bulgu satırını düzeltmek kapatmaz; birimi SAP Pretty Printer ucuyla bütün biçimle
metadata:
  type: feedback
  seed: evet
---

ATC'nin "Incorrect Pretty Print state" bulgusu **birim başına tek** gelir ve yalnız o birimdeki **ilk** fark satırını gösterir (birim: main kaynakta metot, `ccau`/`ccimp`'te tüm include). Bulgu satırını elle düzeltmek bulguyu kapatmaz — sıradaki fark satırı ortaya çıkar.

**Kanıt (2026-09-24):** standart check `CL_CI_TEST_PRETTY_PRINT` `RUN` metodu canlı okundu — birim = program seviyesi (metot `CM###` / include), `CU`/`CO`/`CI`/`CP`/`IP`/`IU` seviyeleri DIŞLANIR (tanım bölümü hiç kontrol edilmez), `PRETTY_PRINTER` FM + satır satır kıyas, ilk farkta `INFORM` + `exit`. Ayar = ATC varyant parametresi (`CASE`/`INDENT`/`KEEP_CASE`). ⚠ Yalnız YEREL koşum dalı; uzak dal (`SRCID` → `RS_ABAP_PRETTY_PRINT_E`, `exit` yok) ÖLÇÜLMEDİ. Kanonik: core `playbook/adt-classes.md` "ATC Incorrect Pretty Print state" (DEV_CORE#293).

**Why:** Bir projede, 2026-09-24 turunda ölçüldü: 23/23 konumda ATC satırı = SAP Pretty Printer çıktısıyla birimdeki ilk fark; bir ccimp'te 33 fark bloğu / 1 bulgu, bir ccau'da 3 metotta fark / 1 bulgu. Kök nedenler yalnız karışık harfli CDS alan adları değildi: yerel tanımlayıcı harfi, imza hizası ve `CALL FUNCTION ... EXPORTING p = x` (parametre anahtar kelimeyle aynı satırda → Pretty Printer satıra böler, satır sayısı değişir).

**How to apply:** Önce kardeş taraması (paketin tüm sınıflarında ATC). Sonra sunucu Pretty Printer ucu `POST /sap/bc/adt/abapsource/prettyprinter` (durumsuz, kaynağı yazmaz; ayarı GET ile oku) ile disk kaynağını biçimlet, farkı birimlere grupla, yalnız ATC'nin işaretlediği birimlere uygula (tanım bölümü hiza farkları bulgu üretmiyorsa dokunma). Eşdeğerliği mekanik kanıtla: token akışı küçük harfte eşit + literal/şablon metni/yorum bayt bayt aynı + negatif test. Satır bölen düzeltme `dosya:satır` yorum atıflarını kaydırır. İlgili: [[atc-bulgusu-select-i-iceren-sinifa-yazilir]] · [[adt-readback-md5-disk-md5-ile-dogrudan-kiyaslanamaz]].

Son-doğrulama: 2026-09-24
Applies-to: s4_private (projenin ATC varyantı; diğer profillerde ATC Pretty Print kontrolü ölçülmedi)
prior-art: bulundu — 6 önceki vaka, farklı paketlerde (07-05 muaf · 08-03 bırakıldı, nedensellik kanıtsız · 08-20 7/7 elle · 09-02/09-09 FUGR iskeleti · 09-24 BEYAN); mekanizma hiçbirinde yazılı değildi. core adt-classes.md `run_pretty_printer` bölümü "kaynağı değiştirir" diyordu (yanlış, DEV_CORE#293'te düzeltildi).
