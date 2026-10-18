---
name: feedback_git-stash-u-salt-okunur-bos-dizinde-yarim-kalir
description: "`git stash -u` salt-okunur boş dizinli ağaçta YARIM kalır — stash yaratılır, izlenmeyen dosya stash'e taşınıp diskten silinir, rc≠0 ile `&&` zinciri kırılır; HEAD==origin/main ise stash'siz dal aç"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 10e41d9b-dbe7-47b8-b42e-99b8fddb9a68
  modified: 2026-10-03T15:15:51.395Z
---

İş dalı açmadan önce çalışma ağacındaki değişikliği taşımak için `git stash -u` KULLANMA. Önce
`git rev-parse HEAD` ile `origin/main`'i karşılaştır; eşitse değişiklikler olduğu yerde kalır ve
`git checkout -b <dal>` doğrudan yeterlidir (checkout değişiklikleri taşır).

**Why:** Bir projede, 2026-10-03: `git stash -q -u && git checkout -b … origin/main && git stash pop`
zinciri koşuldu. Ağaçta salt-okunur (R öznitelikli) boş dizinler vardı: stash commit'i YARATILDI,
izlenmeyen ders dosyası stash'e alınıp diskten SİLİNDİ, ardından boş dizinleri silme adımı
`Permission denied` ile düştü ⇒ rc≠0 ⇒ `&&` zinciri kırıldı, `stash pop` hiç koşmadı. Sonuç: dosya
yalnız `stash@{0}^3` ağacındaydı ve çıktı "failed to remove" uyarılarına gömülüydü; sonraki push
"src refspec does not match" ile düştü. Kurtarma: `git show stash@{0}^3:<yol> > <yol>` + `git hash-object`
ile blob eşliği doğrulandı, sonra `git stash drop`. Veri kaybı olmadı ama yalnız kontrol edildiği için.

**How to apply:**
- Dal açmadan önce `HEAD == origin/main` ölç; eşitse stash'siz `checkout -b`.
- Değilse stash yerine izlenmeyen dosyaları scratch'e KOPYALA, sonra dal aç.
- Bir stash beklenmedik düştüyse önce `git stash list` + `git show --name-only --format= stash@{0}^3`
  (izlenmeyenler) + `git stash show --name-only` (izlenenler) ile içeriği ölç; `pop`'u körlemesine koşma
  (çalışma kopyasında aynı dosya değişikse pop reddeder ya da çakışır).

Son-doğrulama: 2026-10-03 · Applies-to: Windows, salt-okunur dizin içeren proje ağaçları (git stash -u)
