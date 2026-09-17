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
İlgili: [[feedback_kararlari-once-topla-sonra-dispatch]] · [[feedback_arac-kod-fix-lider-isi]]
