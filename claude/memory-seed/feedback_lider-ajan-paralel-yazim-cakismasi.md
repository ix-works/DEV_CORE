---
name: feedback_lider-ajan-paralel-yazim-cakismasi
description: Ajan çalışırken lider aynı dosyaya yazarsa sessiz çakışma olur — devralmadan ÖNCE ajanı durdur ve durduğunu doğrula
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d86b1173-85ae-4dc7-bf30-a1c8f99859fc
---

Bir ajan worktree'de çalışırken, lider aynı dosyaya **paralel** yazmaya başlarsa ikisi
birbirinin değişikliğini sessizce ezebilir. 2026-08-13'te oldu: ajan iki kez ilettiğim
atomiklik şartını uygulamamıştı, kullanıcı süreden rahatsızdı, üçüncü gidiş-dönüşü
beklemeyip fonksiyonu **ben yazmaya başladım** — ajan da aynı anda yazıyordu. Sonuç:
aynı dosyada **iki `_yerinde_senkron` tanımı** yan yana (Pyright `obscured by a declaration
of the same name` diye yakaladı; Edit aracı da *"dosya diskte değişmiş"* uyarısı verdi).

Zarar olmadı çünkü ikisini karşılaştırıp **ajanınkini** tuttum (benimkinde olmayan iki
şeyi vardı: çağırandan bağımsız ikinci savunma katmanı + içerik değişmemişse hiç yazmama),
kendi kopyamı sildim. Ama tur maliyeti benim aceleciliğimdendi.

**Why:** Devralma meşru bir karar (ajan şartı uygulamadı + kullanıcı bekliyor), ama
devralma **anı** yanlıştı: durdurmadan başladım. "İki yazıcı tek dosya" bu evde zaten
düzelttiğimiz kusurun (sessiz ezme) insan hâli.

**How to apply:** Devralacaksan sıra şu: ① `SendMessage` ile **DUR** de ② durduğunu
**doğrula** (dosya mtime'ı sabitlendi mi / ajan onayladı mı) ③ sonra yaz. Devralırken
ajanın o ana kadarki işini **oku ve karşılaştır** — seninki otomatik olarak iyi değildir.
Çakışma sinyalleri: Edit aracının *"dosya diskte değişmiş"* uyarısı · aynı adın iki kez
tanımlanması · beklenmedik mtime. **Son-doğrulama:** 2026-08-13 ·
**Applies-to:** lider + worktree'de çalışan her ajan.
**Vaka 2 (2026-10-09, ajan↔ajan, ortak çalışma ağacı):** kapsamı iki FE ajanı arasında yeniden böldüm;
eski sahibine *"bu uygulamaları bırak"* dedim, o da kendi değişikliklerini `git checkout -- <dosya>` ile geri aldı —
ama yeni sahip aynı dosyalara **çoktan** yazmaya başlamıştı ⇒ 4 uygulamadaki kopyaları sessizce silindi (ikinci
ajan durum teyidinde fark etti, yeniden kopyaladı). **Ek kural:** kapsam devrinde eski sahibe *"yalnız KENDİ
satırlarını geri al, dosya-düzeyi `git checkout`/`restore` YOK"* de ve geri almayı **devirden ÖNCE** bitirt; yeni
sahip ancak onay geldikten sonra başlar. Devir sonrası iki ajandan da dosya md5 listesi al. Son-doğrulama: 2026-10-09.

İlgili: [[feedback_kararlari-once-topla-sonra-dispatch]] · [[feedback_arac-kod-fix-lider-isi]]
