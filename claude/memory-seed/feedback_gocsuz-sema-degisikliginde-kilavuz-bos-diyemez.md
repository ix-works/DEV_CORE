---
name: feedback_gocsuz-sema-degisikliginde-kilavuz-bos-diyemez
description: "Alan anlamı veri göçü OLMADAN daraltıldıysa doküman 'eski alan artık boştur' diyemez — tasarım niyeti veri garantisi değildir; eski kayıtlar eski alanda kalır"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 4924b64d-79dd-407f-adb3-ac337efdbae4
---

2026-09-11 ZSD001 KD-SD-005 v1.3: kılavuza *"kamyon/TIR kaleminde Konteyner No boştur, plaka Çekici/Dorse
Plakası kolonlarındadır"* yazdım. Dayanak CDS yorumuydu (*"ContainerNo'nun ANLAMI DARALDI"*). Doküman kapısı
BLOCKER verdi: plaka ayrıştırması **K6 = veri göçü YOK** kararıyla yapılmıştı; canlıda **11 eski kamyon
teslimatında** plaka hâlâ Konteyner No'da (`8000000029` → `34QWER141`, çekici boş). İddia yalnız 07-28
sonrası kayıtlarda doğruydu (13/13).

**Why:** Kod yorumu / tasarım belgesi *niyeti* anlatır ("artık yalnız gerçek konteyner no"); kullanıcıya
giden metin ise *veri garantisi* verir. Göçsüz şema/anlam değişikliğinde iki popülasyon birlikte yaşar
(eski kayıt eski alanda, yeni kayıt yeni alanda) — kılavuz birini anlatırsa diğerini gören kullanıcı
"hata" bildirir.

**How to apply:** Doküman/mesaj metninde "X boştur / X doludur / artık Y'de görünür" yazmadan önce:
① değişikliğin tasarım kaydında **veri göçü** kararını ara (INTAKE/FS karar tablosu) ② canlıda **eski
tarihli** kayıtla karşı-örnek sorgusu koş (yalnız yeni kayıt örneklemek kör kanıttır — bkz.
[[feedback_olcum-duzeyi-kayit-ici-mi-kayitlar-arasi-mi]]) ③ göç yoksa ifadeyi "eski kayıtlarda … kalmış
olabilir" diye daralt. Aynı turda alanın **kategoriye göre çift anlamı** da aranır (K4: UCAK/EKSPRES'te
çekici alanı takip numarası taşır). İlgili: [[feedback_iddia-yazma-aninda-kanit-kurallari]] ·
[[feedback_kardes-artefakt-benzerligi-kip-semantigini-kanitlamaz]].
