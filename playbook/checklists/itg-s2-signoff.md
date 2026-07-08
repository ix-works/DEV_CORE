---
applies_to: [s4_private]
---
# Reviewer Checklist — ITG S2 Sign-off (ADR 0022)

> **Ne zaman:** S2 (kapsamlı) bir iş SAP-yazmasına geçmeden ÖNCE.
> `run_review.py --task itg_s2_signoff --artifact <intake-artefaktı.md>` ile çağrılır.
> S0/S1 işlerde bu gate KOŞULMAZ (kapsam-orantılılık; over-gating yok).
> **İlgili:** [`../intake-triage.md`](../intake-triage.md) S2 akışı + intake-artefaktı şeması · ADR 0022.

---

## Checklist — ITG S2 sign-off

| ID | Kontrol | Validator | Severity | Kural |
|---|---|---|---|---|
| **C-ITG-01** | Intake-artefaktı üretildi mi (playbook/intake-triage.md S2 şeması)? | `check_itg_signoff.py` | BLOCKER | ADR 0022 |
| **C-ITG-02** | Zorunlu alanlar dolu mu: KAPSAM · Etkilenen objeler (canlı-doğrulanmış) · Prior-art · Kabul kriterleri (EARS)? | `check_itg_signoff.py` | BLOCKER | ADR 0022 |
| **C-ITG-03** | Prior-art alanı DOLU mu ('bulundu: <ref>' VEYA 'yok')? (kurumsal-hafıza araması mecburi; boş bırakılamaz) | `check_itg_signoff.py` | BLOCKER | ADR 0022 · 3-eksen (c) |
| **C-ITG-04** | Kullanıcı MUTABAKAT [x] işareti var mı (sign-off)? | `check_itg_signoff.py` | BLOCKER | ADR 0022 |
| **C-ITG-05** | Etkilenen Z-objeler CANLI doğrulandı mı (hafıza-hipotez değil; source-drift)? | manual | BLOCKER | ⛔ ADR 0016 · kalite kilidi |
| **C-ITG-06** | Kabul kriterleri EARS kalıbında + test-edilebilir mi (INVEST/DoR)? | manual | WARNING | ADR 0022 · standards/04 §1.1.0 |

> **Not (Faz-1):** Hangi işin S2 olduğunu ajan/lider belirler (hook durum-tutmaz — ADR 0022).
> Deterministik `pre_tool_guard` state-gate (Faz-2) pilot-kanıtına bağlıdır (deferred).
