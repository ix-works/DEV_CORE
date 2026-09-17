---
name: feedback_idoc-segment-alani-alfabesi-hedef-tablodan-farkli
description: "IDoc segment alanının geçerli değer alfabesi, o değerin sonunda yazılacağı TABLO alanının alfabesinden farklı olabilir — çeviriyi SAP kendi yapar; tablo kodunu segmente yazmak segmenti SESSİZCE düşürür (hata YOK)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 48bcccdc-68ae-4a1a-96f1-4a32db57747e
---

Bir IDoc segment alanına değer üretirken (mapping/CPI/kendi kodumuz), alfabeyi **segmenti YORUMLAYAN
standart kodun** kabul ettiği değer kümesinden doğrula — hedef tablo alanının domaininden DEĞİL.
SAP çeviriyi çoğu zaman kendi yapar; tablodaki iç kodu segmente yazmak alanı "doğru" yapmaz, **bozar**.

**Why:** ZSD001 EDI/DELFOR, ölçülmüş vaka (2026-08-28 hata → 2026-09-01 geri alma; 6 müşteri paketi
etkilendi, danışmana yanlış değerle zip gönderilmişti).
`E1EDP16-PRGRS`'in geçerli girdi alfabesi **harftir**: `' '`/`D`/`I`/`W`/`M`. Standart kod
`LVED4F0D` `FORM DATUM_MENGE_ERMITTELN` (`:63-360`, her segment için `DYNP_DATA_SCHED_LINE:1174`'ten
çağrılır) bu harfleri **kendisi rakama çevirir** (`:72-74` → `if prgrs = ' ' or 'D'. prgrs = '1'.`
sonra `FILL_XEINT`; `W`→`2`, `M`→`3`, `I`→`1`/`2`). `VBEP-PRGRS`'teki `1/2/3` bu çevrimin **ÇIKTISIDIR**.
⛔ FORM'da rakamlar için **hiçbir `IF` yok ve `ELSE` de yok** ⇒ segmente `'1'` yazılırsa hiçbir dal
ateşlenmez, `FILL_XEINT` hiç çağrılmaz, **hata da basılmaz** — segment sessizce düşer, IDoc işlemez.
İki tuzak birlikte çalıştı: ① domain `EDI_DATTYP` **hem harf hem rakam** içeriyor (`DD07L`: `''`,D,W,M,I,0-9)
⇒ üyelik kontrolü (`LVED4F0Z:255`) rakamı da geçirir, hata görünmez. ② `DD07T(PRGRS)=1 Tag/2 Woche/3 Monat`
gerçekten vardır — ama **hedef tablonun** domainidir. Eski karar bu ikisini karıştırıp çıktıyı girdiye yazdı.
Canlı teyit: tüm `VBEP`'te 264 satırın 264'ü `PRGRS='1'`; <MUSTERI-D>'nunkiler `VBLB.DOCNUM`
(204611/204851/204852) ile kanıtlı EDI kaynaklı ⇒ harf girdi, rakam çıktı.

🔬 **CANLI İKİZ-KANIT (2026-09-01, <MUSTERI-G>/SNDPRN <CARI-3> — kontrollü tek-değişken):** Aynı <MUSTERI-G>
dosyası iki kez gönderildi, **tek fark PRGRS**; `EDID4.SDATA` ham okundu:
`205454` (15:20:12) = `" 120260729    20260729  1500"` → PRGRS **`1`** ·
`205534` (19:22:04) = `" D20260729    20260729  1500"` → PRGRS **`D`**.
Tarihler ve miktarlar 35 segmentte birebir aynı. Sonuç: `3000000059`'daki `VBEP` satırlarının
**28'i tam olarak 205534'ün sıfır-olmayan segmentleri** (tarih *ve* miktar dizisi örtüşüyor);
rakamlı turlar hiç termin yazmadı.
⛔ **`205454` de EDIDC statü 53 aldı.** "Statü 53" bu sınıfta kabul kanıtı DEĞİL — IDoc başarılı
görünür, `VBEP` boş kalır. Kullanıcının ifadesi: *"sadece PRGRS değişikliği yapılarak işlenen
asıl başarılı IDoc bu (205534). diğerleri denemeler. çoğunda terminleri kaydetmedi. prgrs yüzünden."*
Yan ölçüm: 205534'ün 7 `WMENG=0` segmenti `VBEP`'te hiç satır yaratmadı ⇒ sıfır miktarı SAP
kendisi eliyor (bkz. `governance/deferred-triggers.md` `T-ZEROQTY-ZSD001`).

**How to apply:**
- Bir IDoc segment alanına sabit/tablo değeri üretmeden önce, o alanı **tüketen FORM/FM'i bul ve
  kabul ettiği değer kümesini oku**. Hedef tablo alanının domainine bakıp segmenti doldurma.
- **Domain üyeliği ≠ doğru anlam.** Değerin domainde bulunması onu geçerli girdi yapmaz.
- ⛔ **"IDoc hata vermedi" kabul edildi demek DEĞİLDİR.** Bu sınıfta başarısızlık *sessizdir*:
  segment düşer, mesaj çıkmaz. Kabul kanıtı = hedef tabloda (`VBEP` vb.) satırın OLUŞMASI.
- Elde çalışan bir emsal varsa (bu vakada <MUSTERI-D> canlı `D` ile statü 53) **onu otorite say**;
  hiç canlı koşmamış paketlerin "düzeltilmiş" değeri kanıt değildir.
- Kendi canlı kodumuz da bir emsaldir: `ZCL_SD019_IDOC_PROCESSOR.clas.abap:446`
  (`ls_p16-prgrs = ls_s-prgrs. " D/W/M/I`) Temmuz'dan beri harf yazıyordu.

⭐ **Meta-ders (asıl pahalı olan):** 08-28 kararı, depoda **zaten duran doğru bir ölçümün** üstüne
yazıldı — `GUIDE-ANALIZ-<MUSTERI-A>.md` `E1EDP16-PRGRS` (domainsiz) ↔ `VBEP-PRGRS` (domain `PRGRS`) ayrımını
canlı `DD03L` ölçümüyle yazmıştı, `vda2idoc.py` de hep harf üretiyordu. Kod-okuma **çıkarımı**,
mevcut **ölçümü** ezdi; üstelik dayandığı atıf (`LVED4F0A:78` `CHAR2/CHAR3`) yanlış yere bakıyordu
(gelen segmenti değil, DB'deki eski `VBEP` satırını kontrol eden Odette-özel FORM).
⇒ Bir çıkarım mevcut bir ölçümle çelişiyorsa **ölçüm kazanır**; çıkarım ancak kendi mekanizmasını
canlıda gösterirse kaydı değiştirir. Bkz. [[feedback_kaydin-onerdigi-fix-yonu-de-bir-iddiadir]] ·
[[feedback_onay-da-bir-iddiadir-mekanizmayi-olcmeden-net-deme]] ·
[[feedback_alan-anlamini-ddic-etiketinden-dogrula-tvak-fkara-fkarv]] · [[feedback_kod-yolu-vardi-veri-gecmemisti]]
