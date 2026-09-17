---
name: feedback_github-actions-asili-queued-kosu-pr-kapat-ac
description: "GitHub Actions koşusu saatlerce `queued` + 0 job asılı kalırsa cancel/rerun çelişkili döner; PR'ı kapat+yeniden aç (tek komutta) yeni koşu doğurur"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cca08bdf-c505-460c-a1ba-8d1635bd8f7c
---

**Kural:** PR check koşusu `queued` durumda ve `jobs total_count=0` ile saatlerce asılıysa cancel/rerun ile uğraşma.
Önce koşunun gerçekten yenilenip yenilenmediğini ölç: `gh api repos/<ORG>/<REPO>/actions/runs/<id>`'de `run_attempt`
ve `updated_at` alanlarına bak. Değişmemişse **`gh pr close N --repo R && gh pr reopen N --repo R`** komutunu **tek
komutta** koş (PR kapalı kalmasın). Bu `pull_request: reopened` olayıyla taze bir koşu doğurur. Merge yine CI
koşullu yapılır.

**Why:** 2026-09-13, OzakTekstil PR #9. İki koşu 08:52Z/09:19Z'den gece yarısına kadar `queued`, 0 job'da kaldı.
`gh run cancel` → *"Cannot cancel a workflow run that is completed"*, `gh run rerun` → *"This workflow is already
running"*: GitHub tarafında çelişkili, asılı durum. Kullanıcı arayüzden "yeniden tetikledim" dedi ama API'de
`run_attempt=1`, `updated_at` değişmemişti, yani tetik yansımamıştı. PR kapat/aç sonrası yeni koşu `34779596080`
20 sn içinde doğdu ve **success** verdi, #9 merge edildi. `guard.yml` çalışan TD kopyasıyla birebir aynıydı,
concurrency yoktu. Kusur dosyada değil, asılı koşudaydı. Eski iki koşu GitHub'da `queued` kaldı (zararsız).

**How to apply:** (1) `run_attempt`/`updated_at` ile "tetik yansıdı mı" ölç; kullanıcının "tetikledim" demesi kanıt
değildir. (2) Workflow dosyası çalışan bir kontrol grubuyla aynıysa kapat+aç yap. (3) Check'ler head SHA'da
SUCCESS olunca koşullu merge et. İlgili: [[feedback_merge-yalniz-ci-yesilse-admin-bypass-yasak]].

Son-doğrulama: 2026-09-13 · Applies-to: GitHub Actions PR check'leri (ix-works org repoları)
