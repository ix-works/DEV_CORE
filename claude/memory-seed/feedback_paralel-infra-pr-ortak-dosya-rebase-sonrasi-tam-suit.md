---
name: feedback_paralel-infra-pr-ortak-dosya-rebase-sonrasi-tam-suit
description: "Paralel infra ajanları aynı core dosyalarına dokunuyorsa: kardeş PR merge olunca tam süit REBASE'Lİ HEAD'de koşar (KOD DONDU → HAZIR-REBASE → lider rebase → ajan süit); reçete/B-numarasını baştan ayır"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cca08bdf-c505-460c-a1ba-8d1635bd8f7c
---

**Olgu (2026-09-13, DEV_CORE #243/#244/#245):** üç infra ajanı paralel koştu. İkisi `scripts/sap_adt_lib.py` ve `sap_client.py`'ye dokunuyordu, üçü de `infra-changelog.md` / `infra-test-recipes.md`'ye bölüm ekliyordu. İlk PR (#243) merge olunca ikinci ajanın bir HARİTA girdisi (`syntax_check.py → aktivasyon_govde_hukmu`) **yalnız #243'lü ağaçta anlamlıydı**: eski tabanda o fixture dosyayı hiç yüklemiyordu. Ajanın eski tabanda koştuğu tam süit bunu göremezdi; rebase'siz merge seçimi sessizce daraltırdı.

**Çalışan akış:**
1. Ajan KOD DONDU + changelog/reçete stage eder, tam süiti **KOŞMAZ**, `HAZIR-REBASE` der ve durur (worktree'de git yazma yok).
2. Lider commit + `git rebase origin/main` (changelog üst satır çakışması: iki bölüm korunur, en yeni üstte) + push + draft PR.
3. Ajan tam süiti **rebase'li HEAD**'de koşar; ortak dosya md5'lerinin değiştiğini, diğerlerinin KOD DONDU ile eşit olduğunu raporlar.
4. Sıradaki PR, önceki merge olduktan sonra **tek sefer** rebase edilir (erken rebase = aynı çakışmayı iki kez çözmek).

**Reçete numarası:** paralel ajanlar aynı dosyaya `B5x` açar → spawn'da ya da ilk merge'de numara aralığını ajana SÖYLE (bu turda B51/B52/B53 çakışması mesajla önlendi).

**Why:** yeşil süit yalnız koştuğu ağacı kanıtlar; ortak dosyada kardeş değişikliği sonrası ağaç farklıdır. Worktree `git fetch`'i ayrıca bayat `.git/worktrees` kayıtlarını budamaya çalışır — `gitdir` dosyası yoksa bayattır, etkin worktree'ye dokunmaz (alarm değil).

**How to apply:** paralel infra turunda brif sahipliği yazarken ortak dosyaları listele; merge sırasını baştan belirle; ikinci+ PR için yukarıdaki 4 adım.

Son-doğrulama: 2026-09-13
Applies-to: çok-ajanlı infra turları (DEV_CORE); tüm projeler
İlgili: [[feedback_worktree-kapatmadan-once-ajanin-nihai-raporunu-al]] [[feedback_yesil-regresyon-suiti-duzeltmenin-kaniti-degildir]] [[feedback_lider-ajan-paralel-yazim-cakismasi]]
