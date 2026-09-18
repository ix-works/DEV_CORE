---
name: feedback_ajan-okuma-disiplini-tazelik
description: "düzenleyen-ajan Edit sonrası re-read YOK; run başı taze oku; read-only'ye Edit-eki yazma"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9fac5cf8-9dc0-49a7-bbf6-02243dd60ce8
---

Ajan brifinglerinde okuma disiplini (token-verimliliği vs tazelik). Kanonik: core `governance/agent-teams-operating-model.md` §4C.

**Why:** Bir düzenleyen-ajan aynı büyük ABAP sınıfını her Edit'ten sonra baştan okuyup tek run'da 24× Read etti → ağır token israfı. Ama naif "bir kez oku" kuralı tazeliği bozar (kod değişmiş olabilir).

**How to apply:**
- ORTAK (tüm ajanlar): her dosyayı run içinde bir kez taze oku; git diff/snapshot'tan çalış; değişmemiş dosyayı aynı run'da gereksiz tekrar okuma.
- DÜZENLEYEN (backend/frontend/gateway): Edit sonrası aynı dosyayı baştan tekrar Read ETME (harness Edit-state izler).
- READ-ONLY (bug-expert/sap-research/Explore): Edit-eki UYGULANMAZ — brifinge "Edit sonrası okuma" yazma; yalnız "her dosyayı bir kez".
- 🔴 Tazelik her zaman kazanır ([[feedback_source-drift-pull-before-edit-model]], ADR 0016): kural yalnız aynı-run tekrarını keser; her run/resume başında ve dosya değişmiş olabilecekse TAZE oku. "Önceki oturumda okumuştum, atlayayım" YASAK.

İlgili: [[feedback_ajan-olumsuz-donusu-kanitla-sorgula]] (lider satır-no değil içerik doğrular) · [[feedback_agent-briefing-sendmessage-main]].
