---
name: yeni-onay-kurali-verilmis-karari-yeniden-sordurmaz
description: "Yeni bir \"onay al\" kuralı geldiğinde, kullanıcının DAHA ÖNCE açıkça verdiği kararlar yeniden sorulmaz — önce karar kaydını (INTAKE K-n) tara; kalıcı karar sorulmaz, bildirilir"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 9ae82ec2-3c76-473e-b33d-e575d7132a92
  modified: 2026-09-29T18:38:20.003Z
---

Yeni bir onay kuralı (örn. "mevcut altyapıya dokunmadan önce onay al") **geriye dönük karar sorgulatmaz**. Sorulacak liste = tasarımdaki kalemler − kullanıcının zaten açıkça kararlaştırdıkları.

Vaka (bir projede, 2026-09-29): mevcut-altyapı onay turunda bir tasarım kalemi (düzeltme teslimatlarını dışlayan CDS süzgeci) yeniden soruldu; oysa K-30'da kullanıcı *"düzeltme teslimatları her zaman etkisiz elemandır, hiçbir noktada dikkate alınmamalıdır"* demişti. Kullanıcı: *"Bunu daha öncede sordun … bunu sürekli sorman beni korkutuyor, sanki biyerde kullanıyorsun …"*.

**Why:** Kararlı bir kuralı tekrar sormak kullanıcıya "kural uygulanmıyor olabilir" sinyali verir ve güveni sarsar; ayrıca kullanıcının zamanını tören için harcar (bkz. [[alinti-onay-turu-acmaz-toren-enflasyonu]]).

**How to apply:**
- Onay listesi kurmadan önce karar kaydını (INTAKE K-tablosu, FS EK, `.rules.md`) tara; kalemi karara bağlayan K-n varsa onu "zaten kararlı (K-n)" diye **bildir**, sorma.
- Sorulacak olan yalnız kararın kapsamadığı yeni boyuttur (örn. uygulama biçimi değişmişse) — o zaman da kararı alıntıla, yalnız farkı sor.

Son-doğrulama: 2026-09-29
Applies-to: tüm projeler (onay/karar turu)
