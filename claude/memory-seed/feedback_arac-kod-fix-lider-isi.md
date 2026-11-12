---
name: feedback_arac-kod-fix-lider-isi
description: "REVİZE 2026-08-01: infra-fix akışı=howto-infra-fix (EXPRESS+karar+commit=lider; kuyruk-ÜRETİMİ=infra-expert taze-spawn+worktree); gateway/expert yine yalnız RAPORLAR"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 791c30b9-6728-4e20-94d7-8d4a14484d2d
---

Kullanıcı (2026-06-14, tartışma) lane ayrımını netleştirdi: **kök-sebep araç/kod bug'ı (paylaşılan tooling: `scripts/sap_adt_lib.py`, MCP server, validator/hook) düzeltmek = LİDER'in işi, gateway'in DEĞİL.** Gateway dar lane: SAP'ye yazar + geçici (CSRF/lock) retry yapar + **sorunu yukarı raporlar**. Lider = en geniş context + paylaşılan altyapının tek sahibi → kök-fix'i lider yazar; gerekirse gateway yalnız geçici Z test objesiyle doğrular.

**Why:** Paylaşılan tooling tüm ajanlar+MCP tarafından kullanılır; dar executor'ın (gateway) onu değiştirmesi scope-creep + drift riski. Kök-fix bir tasarım kararı (payload/CSRF stratejisi) → en çok context'i olan lider vermeli. Tooling kodu yazmak SAP yazımı değil → gateway lane'i dışı.

**How to apply:** Takım aktifken gateway bir araç/kod bug'ı bulursa → tanı+ham hatayı SendMessage ile lider'e ver, KOD DÜZELTME. Lider fix'i yazar (solo'da zaten lider yazar). Bu oturumdaki 3 fix (create_dataelement/create_bdef/CSRF) istisna olarak gateway+kullanıcı-onayı ile yapıldı; bundan sonra lider sahiplenir. Kural: [[governance/agent-teams-operating-model]] §2 + [[.claude/agents/adt-gateway]]. İlgili: [[feedback_subagent-karar-kurali]].

**REVİZYON (2026-08-01, kullanıcı onaylı):** Kural evrildi — gateway/expert tarafı AYNEN
(düzeltmez, raporlar). Lider tarafı: `core/playbook/howto-infra-fix-proseduru.md` akışı —
DONDUR→SINIFLA→(EXPRESS S0=lider anında | KUYRUK `governance/infra-findings.md`)→fix-ÜRETİMİ
**infra-expert** (taze-spawn, YALNIZ worktree, F1-F5+üç-bağlam-test, ⚠GEVŞETME-bayrağı);
diff-review+test-tekrarı+commit+onay+META-İNFRA = LİDER. Gerekçe: taze-spawn görev-bulaşmasını
fiziksel keser (bug-expert kanıtı); 'tek sahip' korunur (tek üretici-ajan + tek karar-verici).
Son-doğrulama: 2026-08-01 · Applies-to: tüm profiller (all).
