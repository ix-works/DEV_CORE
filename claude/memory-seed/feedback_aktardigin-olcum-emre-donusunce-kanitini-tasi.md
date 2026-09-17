---
name: feedback_aktardigin-olcum-emre-donusunce-kanitini-tasi
description: "Ajana verdiğin talimat bir OLGU iddiası taşıyorsa ölçümünü de taşı ya da 'ölçülmedi' diye işaretle — ölçmediğin bir şeyi emir kılığında göndermek ajanı bug yazmaya sürükler"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c613ab5b-9b21-4fae-8c5a-7ee49cb6d82c
---

Lider olarak ajana gönderdiğin talimatın içinde bir **olgu iddiası** varsa
("şu alan CHAR10", "standart 20'ye kırpıyor", "13 satır / 10 müşteri", "V4 002 IDoc'u durdurur"),
o iddianın **ölçümünü de gönder** — ya da açıkça **"ölçülmedi, doğrula"** diye işaretle.

Aksi hâlde iddia **emir kılığına girer**: ajan onu doğrulanmış kabul edip uygular ve
senin ölçmediğin bir şey koda gömülür.

⛔ **En tehlikeli biçim: "şunu düzelt" talimatı.** Düzeltme emri, altındaki olgu iddiasını görünmez kılar.

**Simetrik tuzak:** bayat bir talimat, ölçülmüş bir olguya "ölçülmedi" yazdırabilir. Talimatın
**amacını** emrin kendisinden ayır; ajan bunu yaptığında **haklıdır**, ısrar etme.

**Why:** 2026-08-26'da tek oturumda beş kez aktardığım ölçüm yanlış çıktı:
- *"`VBAK-KTEXT` domain TEXT20, standart 20'ye kırpıyor"* → aslında `KTEXT_V`(40); **düzeltme emri
  uygulansaydı olmayan bir hatayı düzeltirken GERÇEK bir hata yaratacaktık** (aday 0 → özellik sessizce ölür).
  Üretici emri uygulamak yerine ölçtü ve çürüttü.
- *"`T661W-LIFNR` CHAR10, ALPHA'ya dikkat"* → aslında `LIFNR_ED1` **17**; uyarı dayanaksızdı.
- *"13 satır / **10** farklı müşteri"* → **9**. Sayı koda "ölçüldü" etiketiyle girmişti.
- *"`ZSD000_T_PARTI` canlıda yorumlu"* → yalnız **repo** dosyasına bakmıştım; canlıda 0 yorum.
- *"Yanlış BELNR `V4 002` ile IDoc'u durdurur"* → `T160M`'de **'W'**; belge kaydediliyor. Kullanıcı
  mimari kararını bu yanlış güvenceye bakarak vermişti, doğru bilgiyle **yeniden onaylatmak** gerekti.

Beşini de **ölçen kişi** (üretici/kapı) düzeltti. Bir kez de ajan talimatı bilerek reddetti
(*"ölçülmüş bir olguya 'ölçülmedi' yazamam"*) ve haklıydı.

**How to apply:**
- Talimata olgu koyarken yanına kaynağı yaz: tablo+alan, include+satır, ya da sorgunun kendisi.
- Ölçmediysen **"DOĞRULA"** de, "yap" deme.
- Sayı iddiasını **açıp say** — bu kuralı ajana hatırlatırken kendin uygula.
- Ajan aktarımını çürütürse **teşekkür et ve ölçümü kabul et**; kapıların değeri liderin haklı
  çıkmasında değil, her katmanın ölçme hakkını kullanmasında.

İlgili: [[feedback_tarama-ciktisi-hipotezdir-is-listesi-degil]], [[feedback_kapsam-niteleyicisini-dusurme]],
[[feedback_ajan-bulgusu-dogru-mekanizmasi-yanlis]], [[feedback_iddia-yazma-aninda-kanit-kurallari]]
