---
name: feedback_template-drift-crlf-inflation
description: "template drift/diff satır-sayısı CRLF↔LF uyuşmazlığıyla ŞİŞER; 'büyük drift/port gerek' demeden ÖNCE CR-nötr diff'le doğrula"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7a28f63f-6ff0-4fe7-88d3-e6cc7c9c76c5
---

Template port drift ölçerken raw `diff | grep -c "^[<>]"` veya `git diff --stat` **CRLF vs LF** satır-sonu uyuşmazlığını HER satır farkı sayar → sahte "büyük drift". Bir oturumda `run_review.py` 614 + `_reviewer.py` 408 satır "drift" sandım; CR-nötr ölçünce gerçek = **16 / 26** (gürültüydü). Sadece `sap_adt_lib.py` (267) gerçekti.

**Why:** Kullanıcı "birkaç gün önce de template güncellemesi yapmıştın, o zaman böyle uyarmamıştın — emin misin büyük fark olduğuna?" diye **haklı** itiraz etti. Over-alarm verdim (CRLF artefaktı), doğrulamadan "600+ satır kasıtlı batch" dedim.

**How to apply:** "büyük drift / büyük port gerek / ayrı oturuma bırakalım" demeden ÖNCE gerçek içerik farkını **CR-insensitive** ölç: `diff --strip-trailing-cr A B` veya `git diff --ignore-cr-at-eol --stat`. Raw ≫ CR-nötr ise fark satır-sonudur (commit'te normalize olur, gerçek değil). Drift büyüklüğüne göre karar vermeden bu kontrolü yap. İlgili: [[feedback_powershell-utf8-bom-trap]] (satır-sonu/encoding tooling tuzakları), [[project_development-template-repo]] (T12 port).
