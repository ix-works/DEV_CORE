---
name: feedback_merge-yalniz-ci-yesilse-admin-bypass-yasak
description: "PR merge komutu CI sonucuna KOŞULLU bağlanır (state==SUCCESS); `--admin` DEV_CORE'da hiç gerekmiyordu (ruleset gates required, reviews=0) ve bypass = kırmızıyı main'e sokmak. 2026-08-29: koşulsuz zincir kırmızı PR #181'i merge etti → revert #182"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 199aed41-f1ec-4c03-ae34-a0b1b09c15be
---

**Merge komutu hiçbir zaman `watch ; merge` diye koşulsuz zincirlenmez.** 2026-08-29: `gh pr checks --watch … ; gh pr merge --admin` zinciri, CI `gates fail` bitmişken PR #181'i DEV_CORE main'e soktu → revert PR #182 + ileri-fix turu (~1 saat).

**Ölçülen olgular:**
- DEV_CORE ruleset `main-pr-required`: `required_status_checks(gates)` + `pull_request(reviews=0)`, bypass = OrganizationAdmin. Yani **kapı zaten vardı**; `--admin` onu delen tek şeydi. PR #183 `--admin` OLMADAN merge edildi → bypass DEV_CORE'da hiç gerekmiyordu.
- <REPO> ruleset: `pull_request(reviews=1)`, required check YOK → tek geliştiricide her merge `--admin` ister (Δ4-B ayarı bekliyor: reviews=0 + `guard` required).

**How to apply:**
- Kalıp: `S=$(gh pr checks N --json state,name --jq '[.[]|select(.name=="gates")][0].state'); [ "$S" = SUCCESS ] && gh pr merge …` — `--watch` çıktısına değil **state** alanına bak.
- DEV_CORE'da `--admin` YAZMA. <REPO>'da ruleset düzelene kadar `--admin` yalnız `guard`==SUCCESS koşuluyla.
- Yerel süit yeşil ≠ CI yeşil ([[feedback_yerel-suit-ci-ikizi-degil]]); aynı gün iki ortam sınıfı (sığ klon, POSIX symlink) yalnız CI'da göründü. Ajan "yerel yeşil" der demez dalı push edip draft PR açmak CI'yı rapor bitmeden koşturur (Δ1).
İlgili: [[feedback_exit0-degil-cikti-kaniti]] · [[feedback_kendi-isini-yeniden-siniflandirip-kural-disina-cikma]]
