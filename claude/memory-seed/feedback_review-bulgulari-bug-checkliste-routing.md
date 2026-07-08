---
name: feedback_review-bulgulari-bug-checkliste-routing
description: "Review/compare/bug-expert bulgusu → bug-checklist'e yaz (FE/BE-NN) ki bug-expert gelecekte yakalasın; playbook notu tek başına YETMEZ"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 1c3d5afe-c59f-47a5-bd26-acfc8243bd5b
---

Bir review/karşılaştırma/post-mortem'de yakalanan tekrar-edebilir UI/backend tuzağı, **bug-expert'in okuduğu checklist'e** (`playbook/checklists/bug-checklist-frontend.md` FE-NN / `bug-checklist-backend.md` BE-NN) yeni satır olarak yazılmalı — sadece playbook'a not düşmek YETMEZ.

**Why:** bug-expert (ADR 0018) **checklist-tabanlı** çalışır; review'da bulduğumuz şey checklist'e girmezse bir sonraki build'de tekrar kaçar. Playbook = builder'ın reçetesi; bug-checklist = bug-expert'in dayatma katmanı. İkisi ayrı; ders ikisine de gider ama **enforcement = bug-checklist**.

**How to apply:** Review/compare/bug bulgusu çıkınca → (1) fix'i uygula, (2) playbook'a kanonik desen/troubleshoot satırı (builder reuse), (3) **bug-checklist'e FE/BE-NN satır** (Kontrol+Severity+Ref; tip HATA/EKSİK) → bug-expert sonraki review'da yakalar. Kanıt: ZSD001 booking save-bug maratonu (2026-06-16) → FE-20 alan-adı-$metadata-drift · FE-21 generic-hata-yutma · FE-22 commit-barrier · FE-23 Create/Change kopya-drift eklendi; playbook §1-B B8/B9 + _parseError. Bkz. [[feedback_hook-bakim-protokolu-t11]] (T11 karar ağacı — checklist dalı) · [[feedback_done-tam-kapsam-dogrula]].
