---
name: feedback_agent-briefing-sendmessage-main
description: "Ajan brifing'inde SendMessage to main zorunlu — eksik kalırsa ajan idle olur ama rapor ana konuşmaya gelmez"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a54ee6d9-6b08-4223-9ec8-2806bf40444a
---

Ajan prompt'unda "lider'e DÖN" veya "BUG_GATE_READY raporla" YETMEZ — ajan plain-text output'unu main konuşmaya otomatik iletmez.

Her ajan brifing'inin ÇIKTI bölümüne şunu ekle:

> İş bitince `SendMessage({to: "main"})` ile raporunu ilet (plain-text output görünmez; iletmezsen lider almaz).

**Why:** Ajan idle_notification geldi ama rapor gelmedi → lider ayrıca istedi → ekstra round-trip. Önceki oturumlarda prompt'ta bu talimat açıkça vardı.

**How to apply:** Tüm on-demand ajan (backend-expert, frontend-expert, bug-expert, sap-research vb.) dispatch prompt'larında ÇIKTI/RAPOR bölümüne SendMessage to main talimatını ekle.
