---
name: feedback_wt-denetim-entegrasyon-dali-uzerinden-birlesen-dal-hukmu
description: "--wt-denetim, bir entegrasyon dalına gerçek merge'le girip sonra entegrasyon dalıyla squash-merge edilen dallarda ② içerik FAIL verir; hüküm iki ölçümle kurulur — dal entegrasyon dalının ATASI mı + entegrasyon ağacı main'le 0 fark mı. --is-ancestor istisnası YALNIZ dal→entegrasyon gerçek merge bağındadır"
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

Kanonik kural çekirdekte: CLAUDE.core §1.1 WORKTREE madde 3 (`--wt-denetim` ölçütleri, "bilinen sınır" ve "`--is-ancestor` KULLANILMAZ"). Bu ders yalnız o bilinen sınırın bir alt durumunu ölçülebilir kılar. Çekirdek metni değişirse çekirdek geçerlidir.

**Durum:** dallar önce bir **entegrasyon dalına gerçek merge** ile girer, sonra entegrasyon dalı main'e **squash** edilir. Entegrasyon dalında o dosyalara sonradan dokunulduğu için ② ekseni her dal için "N dosya main'den FARKLI" → FAIL der. Vaka 2026-11-15: 10 dalın 10'u FAIL verdi, hepsinin işi main'deydi.

**Hüküm (üç ölçüm birlikte; değerler entegrasyon dalının merge edilen PR'ından alınır: `gh pr view <N> --repo <ORG>/<REPO> --json headRefOid,mergeCommit` — uzak dal silinmiş ya da main sonradan ilerlemiş olsa da çalışır):**
1. `git merge-base --is-ancestor refs/heads/<dal> <headRefOid>`: dal entegrasyon dalının atası mı?
2. F = `git diff --name-only <mergeCommit>^ <mergeCommit>`; `git diff --name-only <headRefOid> <mergeCommit> -- <F>` boş mu? Yani entegrasyon dalının son hâli squash commit'ine aynen girmiş mi?
3. `--wt-denetim` çıktısında bu worktree için ③ (izlenen değişiklik) FAIL yok ve HASAT ADAYI yok — ya da ③b adayları ana projede aynı göreli yola kopyalandı ve md5 eşitliği ölçüldü. Kalan tek bulgu bu dalın ②'si olmalı.

⛔ **`--is-ancestor` istisnası DARDIR.** Yalnız 1. adımda, dal ile entegrasyon dalı arasındaki **gerçek merge** bağını ölçmek için kullanılır. Dal→main ya da entegrasyon→main bağı squash'tır. Orada çekirdek yasağı aynen geçerlidir, çünkü squash-merge'de `--is-ancestor` yanıltır. Main'e girişin kanıtı 2. adımdaki içerik farkıdır, atalık değil.

Entegrasyon dalına girmemiş dal için iki ölçüm var: dalın ucu, PR'ının head SHA'sının (`gh pr view N --json headRefOid`) atası mı; bu head ile squash commit'inin ağacı arasında fark 0 mı. Burada da atalık yalnız dal ile kendi PR head'i arasında, gerçek commit zincirinde ölçülür. Main'e girişin kanıtı ağaç farkıdır.

**How to apply:** ② FAIL veren dal main'e bir entegrasyon dalı üzerinden girdiyse önce bu üç ölçümü koş. Üçü de geçerse `--wt-kapat --zorla` meşrudur. ⛔ 3. ölçüm atlanamaz: `--zorla` denetimi tümden atlar ve ağacı siler (`team_setup.py` `wt_kapat`), yani 1. ve 2. ölçüm geçse bile commit'lenmemiş izlenen değişiklik ve hasat edilmemiş dosya geri dönüşsüz kaybolur.

Son-doğrulama: 2026-11-15
Applies-to: çok-dallı iş + entegrasyon dalı + squash-merge akışı (tüm profiller)
