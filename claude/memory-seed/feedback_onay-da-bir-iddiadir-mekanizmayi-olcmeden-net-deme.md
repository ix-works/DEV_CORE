---
name: feedback_onay-da-bir-iddiadir-mekanizmayi-olcmeden-net-deme
description: "Bir incelemenin bir maddeyi 'NET/doğru' bulması MEKANİZMASINI doğruladığı anlamına gelmez — onay da bir iddiadır ve kendi kanıtını ister; veriyi ölçüp kodu ölçmeyen onay, yanlış bir talimatı mühürler"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d2ae3acf-f779-4cd4-8d3e-283134b2c1db
---

Bir inceleme/denetim **mevcut bir maddeyi ONAYLADIĞINDA** ("spec'te NET", "doğru yazılmış",
"kontrol ettim, sorun yok"), o onayı **bulgu kadar sorgula**: *neyi ölçerek* onayladı?
**Onay da bir iddiadır ve kendi kanıtını ister.** Reddin kanıt yükü ağır, onayınki hafif sanılır —
tersi doğrudur: bir onay, hatayı **mühürler** ve sonraki turlar o maddeyi bir daha açmaz.

**Sor:** *"Bu onay VERİYİ mi ölçtü, MEKANİZMAYI mı?"* İkisi bağımsızdır.

**Vaka (2026-08-27, dört müşteriye giden ana veri talimatı):**
`T661W-KNREF`'in *"30 haneye sıfır-dolgulu girilmeli"* talimatı dört pakette de yazılıydı.
Bir adversarial inceleme (`REVIEW-<MUSTERI-A>` `B-6`) bunu **"spec'te NET; hatta brifingten daha keskin"**
diye onayladı. Onayın dayanağı: verinin **%97,2'sinin rakamsal** olduğu ölçümü.
⇒ **Veri ölçülmüştü, kod hiç açılmamıştı.**

Gerçek ise tersiydi ve ancak **canlı ölçümle** çıktı: `E1EDKA1-PARTN` CHAR 17 → `RV45S-KNREF`
CHAR 30 ⇒ değerin sonunda daima ≥13 boşluk; ABAP `CO` sondaki boşlukları **dikkate alır**
(`=` gibi davranmaz) ⇒ `IF … CO '0123456789'` **daima FALSE** ve `UNPACK` **ölü koddur**.
Canlı `classrun`: `'7201'` → FALSE, **`sy-fdpos=4`** (kıran karakter = değerden sonraki ilk boşluk).
Talimat uygulansaydı **her IDoc `V4 032`** ile düşerdi (bir pakette 895/895 kalem).

⚠ **Zincirin kırılması üç kademe ve üç ayrı ajan aldı:** ① bir inceleme "NET" dedi ② başka bir
paketin incelemesi canlı kaynağı okuyup **tersini** iddia etti (BLOCKER) ③ bağımsız hakem + canlı
çalıştırma iddiayı doğruladı. Tek bir inceleme daha az olsaydı yanlış talimat müşteriye giderdi.

**Nasıl uygulanır**
- Onay cümlesinin yanına **neyle** onaylandığını yaz: `onay-dayanağı: veri ölçümü (N=…)` /
  `canlı kaynak` / `resmî doküman`. Dayanağı yazılmayan onay, **yeniden açılabilir** sayılır.
- Bir maddeyi *"kapandı/net"* diye kaydeden inceleme, mekanizmaya **hiç bakmadıysa** bunu
  açıkça `[MEKANİZMA ÖLÇÜLMEDİ]` diye işaretlesin — sonraki tur nereden devam edeceğini bilsin.
- Çelişen iki inceleme varsa **hakem üçüncü bir ölçümdür**, oy çokluğu değil.
- Geçersizleşen onayın üstüne **banner** koy, gövdeyi silme: *"B-6 veriyi ölçtü, kodu ölçmedi."*

**Why:** yanlış bir *bulgu* gürültü üretir ve bir sonraki tur onu eler; yanlış bir *onay* **sessizdir**
ve maddeyi kapalı gösterir. Maliyeti, hatanın müşteriye/prod'a kadar gitmesidir.

**Related:** [[feedback_ajan-bulgusu-dogru-mekanizmasi-yanlis]] (bunun ikizi: pozitif bulgunun
GEREKÇESİNİ ölç) · [[feedback_yesil-sinyalin-kapsamini-sor]] · [[feedback_kapsam-niteleyicisini-dusurme]] ·
[[feedback_kod-yolu-vardi-veri-gecmemisti]] (dalın var olması çalıştığının kanıtı değil)

Son-doğrulama: 2026-08-27
Applies-to: her inceleme/denetim turu (kod · doküman · spec); profil-bağımsız
