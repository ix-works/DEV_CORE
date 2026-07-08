---
name: feedback_reviewer-checklist-vs-wired-validator
description: "Reviewer checklist satırı ≠ çalıştırılan validator; gate'i bozuk-girdiyle adversarial test et, sürekli PASS'e güvenme"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 221a6a93-26fb-43be-9837-c5989e246ea5
---

Reviewer (ADR 0006) "sürekli PASS geçiyor, gerçekten çalışıyor mu?" — kullanıcı 2026-06-10'da haklı çıktı. `run_review.py['table_update']` zinciri sadece 2 trivial validator (CURR/QUAN + deprecated-annotation) çalıştırıyordu; ~15 alan DROP eden + var olmayan DTEL'e referans veren ALTER source'una **PASS** verdi. Checklist (`table-update.md`) ~20 BLOCKER satır listeliyordu ama çoğunun arkasında **çalıştırılan script yoktu** (sadece prose / `regex:...` placeholder).

**Why:** Checklist dokümanı ile orkestratörün (`TASK_VALIDATORS`) gerçekten koştuğu validator zinciri AYRI şeyler. "PASS" çoğu zaman "girdi temiz" değil "o task için anlamlı validator bağlı değil / girdi o validator'ı tetiklemiyor" demek olabilir. check_rap_managed_etag gibi GERÇEK iş yapanlar da var (etag gap'ini o yakaladı) → reviewer tiyatro değil ama kapsamı yanıltıcı olabilir.

**How to apply:** (1) Yeni bir task tipinde/var olan zincirde reviewer PASS verince, o zincirin checklist BLOCKER satırlarını gerçekten script'le karşıladığını VARSAYMA — `TASK_VALIDATORS[task]`'a bak. (2) Gate'i **adversarial test et**: kasıtlı bozuk girdi (alan DROP, var olmayan DTEL, yanlış tip) ver → BLOCKER vermiyorsa zincir kör, validator yaz/bağla. (3) Düzeltince doğru girdiyle regresyon (false-positive olmamalı). (4) MCP içi reviewer timeout'u artık non-blocking WARNING (eskiden sahte BLOCKER 0/0) — asıl gate manuel `run_review.py`. Bağlanan/yazılan: `check_table_field_drop.py` (canlı SAP diff DROP/RENAME/TYPE), `check_struct_field_dtel_active` table_update'e WIRED. İlgili: [[feedback_done-tam-kapsam-dogrula]] [[feedback_hook-bakim-protokolu-t11]]
