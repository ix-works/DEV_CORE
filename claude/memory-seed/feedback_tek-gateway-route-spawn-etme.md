---
name: feedback_tek-gateway-route-spawn-etme
description: Standing gateway varken yeni gateway spawn etme; SAP yazımını mevcut tek-yazıcıya route et + task owner doğru ata
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 4e294fa5-6541-49dd-96dc-e83aaba422a1
---

SAP yazımı (push/activate) gerektiğinde, oturumda zaten **standing bir adt-gateway** varsa YENİ gateway spawn ETME — işi mevcut gateway'e SendMessage ile route et. Ayrıca SAP-yazma task'ının `owner`'ını gerçekten yazacak ajana doğru ata (yanlış owner + redundant spawn = iki ajanın aynı objeleri yazması).

**Why:** 2026-06-29 <PAKET-C>'de task #9 owner'ını yanlış ajana atayıp ayrıca yeni gateway spawn ettim → iki gateway aynı 5 objeyi push+activate etti (çift-yazım). Aynı kaynak olduğu için idempotent/zararsızdı (son-yazan-kazandı, lock-conflict olmadı) AMA single-writer (ADR 0018) ihlali + lock-conflict riski. İyi ki gateway'ler bug-gate teyidi olmadan push'u reddetti.

**How to apply:** (1) SAP push gerekince önce mevcut gateway var mı bak; varsa SendMessage ile ona ver. (2) Yeni gateway yalnız standing yoksa spawn et. (3) Task owner'ı = fiilen push edecek ajan. (4) İki yazıcıya asla aynı objeyi verme; biri push'a başladıysa diğerine net "DUR" yolla. İlgili: [[feedback_arac-basarisizligini-zararsiz-sayma]] · [[feedback_gateway-git-commit-push-yasak]].
