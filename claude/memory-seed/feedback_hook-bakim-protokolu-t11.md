---
name: feedback_hook-bakim-protokolu-t11
description: Yeni tekrar-eden tuzak/iş-türü → hangi katman dayatmalı? (T11) — hook/checklist self-maintenance
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c874b6ce-b5f4-4780-8a44-b99611c71492
---

Yeni bir tekrar-eden tuzak veya yeni iş-türü keşfedince, sadece playbook'a not düşmek YETMEZ.
"İş başlarken hatırlasaydım olmazdı" diyorsan → doğru anda **dayatan** katmana ekle. Karar ağacı
`scripts/hooks/README.md` §2'de; tetik **T11** (CLAUDE.md) + lessons-learned SELF-UPDATE adım 5.

Katmanlar: validator (yazım-sonrası kontrol) / **checklist** (iş-türüne özel pre-flight) /
**hook** (proaktif/cross-cutting) / pre_tool_guard (yazma-anı blokla). Yeni iş-türü →
`skill_injector._WORKTYPES`'a (regex,label,checklist-ref) + checklist yarat + SKILL.md tablosu.

**Why:** Hook sistemi (gap #9) kurulmuştu ama hook'ları güncel tutacak bilinçli bir tetik yoktu;
T10 yalnız validator/checklist'i kapsıyordu, proaktif hook katmanından hiç bahsetmiyordu. Tıpkı
include-böl kuralının "unutulması" gibi (lessons-learned PATTERN #8), hook bakımı da ad-hoc kalırsa
unutulur.

**How to apply:** Hata-tespit/T10 sırasında her zaman §2 karar ağacını geç. Hook ekleyince/değiştirince
README §4'teki elle test komutunu çalıştır (sessiz bozulma = güvence kaybı). Bkz.
[[project_dynpro-gui-status-uretici]], [[feedback_klasik-program-include-bol]].
