---
name: feedback_monitor-sessiz-oldu-bash-background-ile-dogrula
description: "Monitor aracı CI izlemede iki kez SIFIR olayla doldu; aynı işi Bash run_in_background yaptı — izleyicinin sessizliği 'henüz bitmedi' ile ayırt edilemez, sonucu DAİMA doğrudan sor"
metadata:
  type: feedback
---

`Monitor` ile kurulan bir CI/PR izleyicisi **sessiz kalabilir** ve bu sessizlik *"iş henüz
bitmedi"* ile **ayırt edilemez**. Ölçülen vaka (2026-09-18, aynı oturumda iki kez): PR #265 ve
PR #331 için kurulan iki izleyici de **30 dk sonra "no events delivered" ile doldu**, oysa her
iki CI de o süre içinde **tamamlanmıştı** (doğrudan sorulduğunda `SUCCESS` göründü ve ikisi de
merge edildi).

**Kontrol grubu (aynı oturum, aynı iş):** `Bash` aracı `run_in_background: true` ile kurulan
bir `until`-döngüsü aynı görevi **iki kez başarıyla** yaptı (PR #264 ve #330) — bitince
bildirim geldi ve çıktı dosyasında adım adım durum vardı. ⇒ Kusur "arka plan izleme" fikrinde
değil, o araçtaki koşumda.

**Why:** izleyicinin sessizliği yanlış tarafa yorumlanırsa lider **bekler**; iş bitmiştir ama
kimse ilerletmez. Bu, "sessizlik başarı değildir" sınıfının izleyici-tarafındaki hâlidir.

**How to apply:**
- Uzun bir CI/PR beklemesinde **`Bash` + `run_in_background`** tercih et; çıkış koşulu net bir
  `until` döngüsü yaz (bitince süreç ölür, bildirim gelir).
- İzleyici kurduysan bile **sonucu bir kez doğrudan sor** — "bildirim gelmedi" hüküm değildir.
- İzleyici *"no events"* ile dolduysa bunu **ölçüm başarısızlığı** say, "olay olmadı" sayma;
  filtreyi genişletmeden önce komutun o kabukta gerçekten koştuğunu doğrula.
- İlgili: [[feedback_brifinge-koydugun-yolu-once-kendin-kos]] ·
  [[feedback_arac-basarisizligini-zararsiz-sayma]] · [[feedback_sendmessage-gorevi-sessizce-islenmemis-olabilir]]
