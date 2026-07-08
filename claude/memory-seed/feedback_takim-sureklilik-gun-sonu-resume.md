---
name: feedback_takim-sureklilik-gun-sonu-resume
description: "Takım oturum-sürekliliği — lider sahibi; ajanlar durumsuz, artefakttan resume"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 791c30b9-6728-4e20-94d7-8d4a14484d2d
---

Kullanıcı (2026-06-14) multi-agent oturum-sürekliliğini sordu. Karar: **süreklilik sahibi = LİDER; ajanlar durumsuz işçi.** Süreklilik ajanın canlı bağlamında değil **kalıcı artefaktlarda** yaşar (repo Zone B yerel kaynak + SAP objeleri + paylaşımlı task list + SESSION_NOTES + memory + git). Ajan süreçleri oturum kapanınca ÖLÜR (transcript kalır, otomatik resume YOK).

**Why:** Ajan canlı-bağlamı uçucu; tek kalıcı kaynak artefaktlar. Bu "TAHMİN YASAK / artefakt otoritedir" ile aynı. Task izole değil — lider hub'dır, kullanıcı "gün sonu" deyince lider toparlar.

**How to apply:** **Gün-sonu (yarım iş):** lider her aktif ajana checkpoint sorar (diskte ne hazır+yollar / sıradaki adım / açık-noktalar, sonra dur) → task'a "kaldığı yer" + SESSION_NOTES ajan-bazlı entry + WIP commit → **`git push origin main` ZORUNLU (kullanıcı kuralı 2026-06-25: "gün sonu dediğimde push etmeliyiz mutlaka")** — commit YETMEZ; push = origin yedek + paylaşımlı-repo ekip senkron + ultrareview dar kapsam → oturum kapanabilir. Yarım dosyayı commit etme; checkpoint yazım bitince. **Resume:** config kalıcı → ajanları yeniden spawn + resume-brief (task durumu+dosya yolları+sıradaki adım) → ajan dosyaları okuyup devam (kafadan değil artefakttan). Kanonik: [[governance/agent-teams-operating-model]] §3B. İlgili: [[feedback_dosya-bolgeleri-yazim-yetkisi]] · [[project_agent-team-td-agent-teams]].
