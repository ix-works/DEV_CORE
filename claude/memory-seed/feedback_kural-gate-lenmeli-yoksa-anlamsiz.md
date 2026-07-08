---
name: feedback_kural-gate-lenmeli-yoksa-anlamsiz
description: "Gate'lenmemiş (pasif prose) kural ≈ kuralsız; her kural atlanamaz şekilde kurgulanmalı (validator/hook/checklist-gate)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: aa35f5d0-75ef-4442-ba81-d3a0da0e3929
---

Kullanıcı (2026-06-18) net koydu: "kural var ama gate'lenmemiş" lafını çok sık söylüyorum → **gate'lenmemiş kuralın anlamı yok; ajan uymayacaksa kuralın ne anlamı var.** Bir kural varsa, **atlanamayacak şekilde kurgulanmalı** — sadece o anki kural için değil, TÜM kurallar için bu ilke geçerli.

**Why:** Pasif prose kural (standards/playbook'ta yazı) hatırlamaya/iyi niyete bağlı → ajan (alt-ajan dahil) görmez/atlar → patinaj + sessiz regresyon. Bu seansta 4 kanıt: (1) manifest JSONModel çift-sarmalama — validator yoktu; (2) F4 VH write-back — checklist'te yoktu; (3) KD mock-veri kuralı standards §1.3 + howto'da VARDI ama KD-regen ajanı gerçek/kirli backend verisi kullandı; (4) KD grid-toolbar bölümü zorunlu değildi. Hepsi "kural mevcut ama enforcement yok" kökünden.

**How to apply:** Yeni bir kural koyarken DUR ve sor: "bu nasıl atlanamaz olur?" → doğru katmana DAYAT (validator=yazım-sonrası / hook=proaktif-cross-cutting / checklist-gate=iş-türüne-özel bağımsız reviewer / pre_tool_guard=blokla). Sadece prose'a yazmak YETMEZ ([[feedback_hook-bakim-protokolu-t11]] T11 karar ağacı). "kural var ama gate yok" dediğim her an = enforcement açığı → flag'le. KALICI ÇÖZÜM AYRI İŞ: voyage sonrası "kural-enforcement mimarisi" planlanacak (tüm kuralların gate-coverage envanteri + her birini atlanamaz kılma) — register: governance/deferred-triggers.md. İlgili: doc-gate ([[feedback_review-bulgulari-bug-checkliste-routing]]), kod bug-gate (ADR 0018).
