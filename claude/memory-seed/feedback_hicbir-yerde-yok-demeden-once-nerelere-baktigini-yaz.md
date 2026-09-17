---
name: feedback_hicbir-yerde-yok-demeden-once-nerelere-baktigini-yaz
description: "\"Hiçbir kayıtta yok / yeni yaratılmalı\" bir NEGATİF İDDİADIR — hangi SİSTEMLERE baktığını yazmadan kurulamaz. Tek sisteme bakıp 'hiçbir yerde yok' demek, aynı gün içinde 62→72 gibi yanlış iş listesi üretir."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 861ca50c-63ab-4fdb-9003-e77ece277765
---

**KURAL:** *"Bu kayıt hiçbir yerde yok"* / *"yeni yaratılmalı"* demeden önce **hangi
kaynaklara baktığını açıkça yaz**: sistem adı + tablo + kapsam. Negatif iddia, ancak
**arama uzayı beyan edilirse** kurulabilir. Beyansız negatif = *"benim baktığım yerde yok"*.

**Ölçülmüş vaka (2026-09-07, ZSD001 ADIM-2, malzeme/KNMT).**
Korpustan 76 tekil müşteri malzeme kodu (`KDMAT`) çıkardım, S/4 `KNMT`+`MARA`'da aradım,
bulamadıklarıma **"62 yeni malzeme yaratılmalı"** dedim ve bunu rapora yazdım.
⛔ Yalnız **S/4'e** bakmıştım. Kullanıcı ECC KNMT dökümünü verince (`ECCQA_KNMT.XLSX` 6664
satır · `ECCPRD_KNMT.XLSX` 6843 satır) 76 kodun **74'ü** ECC'de karşılığını buldu ⇒ doğru
sayı **72 yeni MATNR**, ve daha önemlisi **eşleşecek MATNR'ler ECC'den geldi** — ben onları
"yok" sayıp yeni numara açtıracaktım. Aynı hata mevcut 11 KNMT satırının **10'unun yanlış**
olduğunu da gizlemişti.

**Why:** Bu şirkette bir malzemenin kimliği **tek bir sistemde yaşamıyor** (ECC QA + ECC PRD
+ S/4 DEV). "Yok" hükmü doğrudan **iş üretiyor** — yanlışsa gereksiz master data yaratılıyor
ve sonradan geri alınamıyor. Pozitif bulgunun aksine negatif bulgu kendini ele vermez:
0 satır dönen sorgu, "yanlış yere baktım"la "gerçekten yok"u **aynı gösterir**.

**How to apply:**
- Negatif iddiayı **daima kapsamıyla** yaz: *"S/4 DEV `MARA`+`KNMT`'de yok (ECC'ye BAKILMADI)"*.
  Kapsamsız *"hiçbir yerde yok"* cümlesini kurma.
- **Sormadan önce sor:** bu veri başka hangi sistemde/dökümde yaşıyor olabilir? Kullanıcıda
  duran bir Excel/ECC dökümü varsa **iste** — ölçümden önce, sonra değil.
- Eşleme kurarken **kontrol grubu** çalıştır: karşılığı olduğunu bildiğin birkaç kaydı da
  aynı sorgudan geçir. Onlar da 0 dönüyorsa sorun veride değil **aramanda**dır.
- İş listesi sayısı ("62 yeni malzeme") bir **ölçümdür**; kaynağı değişince
  [[feedback_curutme-de-bir-iddiadir-yerine-yazilan-sayi-olculur]] gereği yerine yazdığın
  sayıyı da ölç ve **her yerde** güncelle ([[feedback_iddia-kac-yerde-yasiyorsa-o-kadar-yerde-kapatilir]]).

İlgili: [[feedback_olcum-duzeyi-kayit-ici-mi-kayitlar-arasi-mi]] ·
[[feedback_kapsam-niteleyicisini-dusurme]] · [[project_ecc-s4-malzeme-numaralandirmasi-ortak]] ·
[[feedback_arac-basarisizligini-zararsiz-sayma]]
