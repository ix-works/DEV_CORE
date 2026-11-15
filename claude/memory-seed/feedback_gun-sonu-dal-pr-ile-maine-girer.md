---
name: feedback_gun-sonu-dal-pr-ile-maine-girer
description: "Gün sonu = iş dalı PR ile MAIN'E GİRER + birleşen dallar silinir; dalı push'lamak 'push origin main' maddesini KARŞILAMAZ"
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

Kanonik kural çekirdekte: CLAUDE.core §1.1 GIT maddesi ("main'e doğrudan commit YOK → branch + PR") ile gün-sonu maddesi ("`push origin main` ZORUNLU") **birlikte** okunur. Anlamı şudur: gün sonunda günün işi **PR ile main'e girmiş** olmalıdır. Dalı yalnız push'lamak bu maddeyi karşılamaz. Bu ders yalnız o okumayı ve uygulama sırasını işaretler. Çekirdek metni değişirse çekirdek geçerlidir.

Sıra: PR aç → CI (`statusCheckRollup`) yeşil → squash-merge → birleşen dal uzakta ve yerelde silinir → yerel `main` origin'e eşitlenir.

**Why:** Vaka 2026-11-08: bir build dalında 21 commit birikti. Gün sonu yalnız dalı push'ladı, PR açılmadı. Ertesi sabah `/core-guncelle` "dal main değil → DUR" ile takıldı. PR'ları MERGED olan 7 eski dal da origin'de duruyordu. Kullanıcı (2026-11-09): *"herşeyin maine atılmış olması gerek gün sonunda"*. Prior-art: [[feedback_takim-sureklilik-gun-sonu-resume]] (push zorunluluğunu söylüyor, dal/PR ayağını söylemiyor).

**How to apply:**
- Gün sonunda `git log origin/main..HEAD` boş değilse PR açılır ve merge edilir. `--admin` yalnız "onaylayan yok" şartını aşmak içindir, CI'yi atlamak için değil.
- İş bitince `git ls-remote --heads origin` yalnız `main`'i göstermelidir. İstisna: bilerek açık bırakılmış ve kullanıcıya söylenmiş bir dal.
- Uzak dalı silmeden önce dalın ucunun merge edilen PR'ın `headRefOid`'ine eşit olduğunu ölç. Böylece merge'den sonra eklenmiş bir commit kaybolmaz.
- Kullanıcı açıkça "dal açık kalsın" derse kural uygulanmaz; karar RESUME'ye yazılır.

Son-doğrulama: 2026-11-09
Applies-to: tüm projeler, branch+PR akışı (gün sonu)
