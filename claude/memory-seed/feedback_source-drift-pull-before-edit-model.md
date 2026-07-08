---
name: feedback_source-drift-pull-before-edit-model
description: ADR 0016 REVİZE — pre-push drift-block (M1) + repo-sync (M2) kaldırıldı; yerine PULL-BEFORE-EDIT (edit-öncesi tazelik + PreToolUse hook backstop)
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 612f1395-101e-440c-93a8-f64bda823d69
---

ADR 0016'nın ilk modeli (M1 pre-push drift HARD-BLOCK + M2 post-write repo-sync + M3 drift validator) ilk gerçek kullanımda **KUSURLU** çıktı: M1 `normalize(canlı) != normalize(repo)` **symmetric** kıyas yaptığı için **KASITLI edit'i de blokluyordu** — bir objeyi düzenleyip push ettiğinde repo zaten canlıdan FARKLIDIR (push'un amacı bu). M1, 404/no-op dışındaki HER meşru source push'unu blokladı (railway kampanyası ADIM 1'de yakalandı). Doğru referans working-tree değil **baseline** olmalıydı (git merge-base mantığı); ama gerçek koruma = edit'e başlamadan **güncel hali çekmek**.

**Yeni model (2026-06-16, kullanıcı-yönlendirmeli) — PULL-BEFORE-EDIT:**
- **M1+M2 KALDIRILDI** (`mcp_servers/sap_adt/tools/atom.py`): `adt_push_source` artık `source_drift` bloğu atmaz; `adt_activate` repo'ya geri-yazmaz. M3 (`check_source_drift.py`) run_all'dan çıkarıldı (drift artık editlerken DOĞAL → noise).
- **P1 PreToolUse(Edit|Write) hook** `scripts/hooks/pull_before_edit.py` (settings.json wire'lı): yönetilen SAP source'u (ERP/ altı, source-ext) düzenlemeden önce bu seansta çekilmemişse exit-2 blok + yönlendirme. **Subagent edit'lerinde de fire eder** (KANITLANDI: project-level PreToolUse subagent Bash'inde bloklandı). MUAF: git-dirty (WIP), yeni obje, ref_docs/.tmp, SAP-dışı/UI dosyası.
- **P2 helper** `scripts/sap_sync_pull.py <NAME> --type <T>`: canlı çek → repo'ya yaz (CRLF-korur, tip-farkında) → seans-tazelik damgala (`.claude/.session_fresh.json`, session-match fail-safe). `--session` SessionStart marker'ından (`.claude/.current_session`) otomatik. `--offline` = SAP erişilemezken fetch'siz damgalar (ezme riskini kabul).
- **Analiz tazeliği (C, ASIL koruma):** editleyen ajan görev başında hedef objeyi ANALİZDEN ÖNCE pull eder (prompt'lara eklendi: backend-expert/adt-gateway/sap-feature). Hook = backstop (FE UI dosyaları gate'lenmez).

**Why:** M1 "bayat-repo (clobber)" ile "kasıtlı-edit"i ayıramaz; koruma push-anından edit-öncesine taşındı. Best-effort (hard-gate değil) — eşzamanlı canlı-edit penceresi kalır, kabul (gerçek hayatta da olur). Araç fix'i = lider işi ([[feedback_arac-kod-fix-lider-isi]]).

**How to apply:** SAP source DÜZENLEYECEKSEN → bu seansta ilk kez `sap_sync_pull` ile çek (hook unutursan bloklar). atom.py M1/M2 sökümü canlı olması için **/mcp restart** gerekir. Name-collision tip-fix'i ([[feedback_source-drift-name-collision-fixed]]) hâlâ geçerli — artık pull helper'ın yolunda kullanılıyor. Bkz. ADR 0016 (REVİZE banner).
