---
name: feedback_paralel-oturum-ayni-calisma-agacinda-degisikligi-tasir
description: "Aynı çalışma ağacında paralel oturum varken commit'siz değişikliğim onun commit'ine girip checkout ile ağaçtan \"kayboldu\" — branch/commit öncesi reflog + PR listesi ölç, kayıp sanma"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: a4cc5860-05b0-47fa-b9f6-6cee48d45d90
  modified: 2026-10-03T11:48:14.137Z
---

**Vaka (bir projede, 2026-10-03):** Gün içinde SESSION_NOTES / deferred / FS-TS dosyalarını
düzenledim, commit etmedim. Aynı proje ağacında çalışan **paralel bir oturum**
12:10'da kendi dalını açtı, `git add` ile **benim değişikliklerimi de** kendi commit'ine aldı
(bir PR), push etti, sonra `main`'e döndü. 14:45'te ben branch açıp `git add` yaptığımda
dosyalarda fark yoktu — değişiklikler "kaybolmuş" görünüyordu. Kayıp değildi: başka dalda,
açık bir PR'daydı.

**Why:** Ortak çalışma ağacı oturumlar arası bir paylaşılan durumdur; bir oturumun `checkout`u
ötekinin commit'siz işini **taşır**. Yanlış teşhis ("dosyalar silindi") ya yeniden yazmaya
(çift iş, çakışan PR) ya da yanlış alarma götürür. Üstelik benim kısa `checkout`um da o
oturumun ağacını değiştirdi.

**How to apply:**
- Branch açmadan / commit'ten önce `git status` beklenenden boşsa **önce** `git reflog -15` +
  `gh pr list --repo <ORG>/<REPO> --state open` + `git show --stat <şüpheli commit>` — içerik
  başka dalda mı?
- İçerik bir başkasının açık PR'ındaysa o PR'ı **onun** işi say: merge kararını kullanıcıya
  sor (o PR incelemediğin değişiklik taşır); kendi kopyanı yeniden yaratma.
- Ortak ağaçta `checkout` yaptıysan **hemen** geri dön ve kullanıcıya söyle (öteki oturum o
  anda git komutu koşuyor olabilir). Uzun iş için paralel oturum varken worktree tercih et.
- Gün-sonu memory/agent-memory commit'inde **yalnız kendi dosyalarını** `git add` et; ağaçta
  başka oturumun commit'siz dosyaları olabilir.

prior-art: yok (memory'de "paralel oturum / aynı çalışma ağacı" araması 0). Yakın:
[[feedback_lider-ajan-paralel-yazim-cakismasi]] (aynı oturum içi lider↔ajan), bu ise oturumlar arası.

Son-doğrulama: 2026-10-03
Applies-to: tek çalışma ağacını paylaşan birden çok Claude Code oturumu (her profil)
