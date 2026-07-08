---
name: feedback_lider-bloke-olmama-background-dispatch
description: Lider agent dispatch ederken kendini bloke etmemeli — Agent çağrısı DAİMA run_in_background:true
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 5ecec217-78c0-499b-ad67-bf1afb7f70a6
---

**KURAL (mutlak, istisnasız):** Bir ajana iş verince kendini bloke etme. `Agent(...)` her çağrısında **`run_in_background: true`** yaz. Dispatch sonrası kullanıcıya tek satır ("X'i background'da başlattım") de, turn'ü kapat; iş bitince bildirimle topla.

**Mekanik:** Foreground (varsayılan) çağrı = lider turu ajan bitene kadar duraklar → başka tool çağrılamaz **ve kullanıcıya yanıt verilemez**. `run_in_background: true` = ajan detached koşar, lider devam eder, bitince bildirim gelir.

**Why:** (1) Lider paralel bağımsız iş yapabilir; (2) DAHA ÖNEMLİ: foreground bloke iken kullanıcı araya girmek/bir şey sormak istese turn duraklı olduğu için ona ulaşamaz. "Yapacak iş yok / sıradaki adım çıktıya bağlı" GEREKÇE DEĞİL — kullanıcıya açık kalmak başlı başına sebep. Bloke olmak harness-zorunluluğu değil.

**Tek istisna (nadir, bilinçli):** kronik/inatçı bir sorunda ajanın loglarını anlık görüp adım adım müdahale etmen gerektiğine dair somut neden varsa foreground seç. Onun dışında HER ŞEY (build/review/deploy/recon/doküman) background.

**Seri zincir:** build→review→deploy→commit kaçınılmaz seri ama her adımı background ver, bitince bir sonrakini background ver — zincir seri kalır, kullanıcıya HİÇ kapanmazsın.

> NOT: Bu kullanıcının defalarca tekrarladığı bir düzeltme (kronik unutma). Foreground çağırmadan önce DUR: "neden background değil?" — cevabın yukarıdaki tek istisna değilse, background yap.

**İlgili:** [[feedback_subagent-karar-kurali]] (paralel fan-out kararı), [[feedback_takim-sureklilik-gun-sonu-resume]], [[project_agent-team-td-agent-teams]] (ADR 0018).
