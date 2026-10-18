---
name: feedback_doc-builder-diagram-png-render-gurultusu-geri-al
description: "KD builder `diagram-01.png`'yi her koşuda yeniden render eder — mermaid kaynağı aynıyken PNG piksel gürültüsüyle 'değişmiş' görünür; kaynak aynıysa build sonrası git checkout"
metadata:
  type: feedback
  seed: evet
---

KD/FS builder'ı her koşuda mermaid diyagramını yeniden render eder; kaynak bir harf değişmese de
PNG baytları farklı çıkar (antialias/zaman gürültüsü) ⇒ `git status` `M .../diagram-01.png` gösterir,
help kopyası da değişir ve gereksiz deploy/commit gürültüsü doğar (bir projede, 2026-10-10 —
dört ayrı doküman turunda).

**Why:** "dosya değişti" ≠ "içerik değişti"; görsel artefaktta bayt farkı anlam taşımaz.

**How to apply:** build sonrası mermaid kaynağının md'de değişip değişmediğine bak
(`git diff -- <md> | grep -A3 mermaid`); değişmediyse `git checkout -- <docs ve help diagram-*.png>`.
Ajan brifine "diagram farkı 0 olmalı / kaynak değişmediyse geri al" maddesi koy.
Son-doğrulama: 2026-10-10 · Applies-to: md→html→pdf doküman hattı (mermaid render eden builder'lar)
