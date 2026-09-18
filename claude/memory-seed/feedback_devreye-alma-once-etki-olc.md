---
name: feedback_devreye-alma-once-etki-olc
description: "Bir gate/veri/tooling değişikliğini uygulamadan ÖNCE kablolamayı ve yükü ÖLÇ; bozma ihtimali varsa yapma, önce araştır"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 779612fa-ff90-44d0-a2a0-ede9e8040518
---

Bir kontrolü/veriyi/tooling ayarını **devreye almadan önce ölç**: nerede kablolu (hangi runner/CI/hook/MCP), hangi severity, kaç bulgu üretiyor, dosya başına kaç tane, bir şeyi **bloklar mı**. Kullanıcı (2026-07-26): *"bi yeri bozma ihtimali varsa o düzenlemeyi yapma, önce bi yere etkisi var mı yok mu, sıkıntıya sebep olabilir mi onu araştır"* + *"mevcut memory/skill/MCP ve diğer kural dosyalarımızı detaylı okuyarak etki analizi yap; daha önce bu tarz düzenlemelerin sebep olduğu sorunlar varsa onları incele ve aynı sorunları yaşamayacak şekilde düzenle."*

**Why:** Bu repoda devreye-alma hatalarının kayıtlı bir tarihi var: fail-open sessiz PASS (veri yoksa `return {}` → exit 0), muafiyetsiz açılışın FP seli (bir detektör 10 bulgunun 10'unu da FP verdi), kabul edilmiş eski ihlalin yeni ihlali gizlemesi. Ölçmeden açmak "gate aktif" değil **gate hissi** üretir.

**How to apply:** Kanonik yöntem core'da → `core/playbook/lessons-learned.md` **PATTERN #14** (üç hastalık + 9 adımlı devreye-alma sırası + grandfather deseninin 5 değişmezi). Uygulamadan önce en az şunları kanıtla: (1) `rg` ile kablolama (run_all / run_review / CI / pre-commit / MCP guardrail), (2) severity ve **blokluyor mu** (`--strict` kullanılıyor mu), (3) tüm repoda ve **dosya başına** bulgu sayısı, (4) pozitif **ve** negatif test. Bulguyu kullanıcıya sun, kararı ona bırak. Yeni gate açma refleksi için [[feedback_gate-moratoryumu-bes-sart]]; SAP objesi tarafındaki karşılığı [[feedback_fix-oncesi-where-used-blast-radius]]; "kontrol koştu ≠ kontrol baktı" ailesi [[feedback_reviewer-checklist-vs-wired-validator]].
