---
name: feedback_gateway-git-commit-push-yasak
description: adt_gateway rolü git commit/push YAPMAZ — lider commit eder (rol-def 2026-06-14)
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 791c30b9-6728-4e20-94d7-8d4a14484d2d
---

adt_gateway (bu rol) **git commit/push ASLA yapmaz** — güncellenmiş rol-def kuralı (lider bildirimi 2026-06-14 gün sonu). Commit'i LİDER yapar.

**Why:** Çok-ajan takımda tek-yazar/commit disiplini; gateway yalnız SAP'ye yazar + yerel kaynak senkronlar, versiyonlama lider sorumluluğu.

**How to apply:** Lider "commit et" dese bile — bu kural aktifken commit etme, "rol-def commit yasağı var, sen commit et" diye geri bildir. SAP push/activate + yerel dosya senkron + rapor = gateway işi; `git commit`/`git push` = lider. (NOT: 2026-06-14'te increment-2 commit'i 5ea7f934 eski "bitince commit" direktifiyle yapıldı; kural BUNDAN SONRA geçerli.) İlgili: [[project_agent-team-td-agent-teams]].
