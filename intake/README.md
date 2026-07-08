# intake/ — Dış İçerik Gümrüğü (F4 firewall)

> Dışarıdan gelen HER metodoloji parçası (skill, hook, script, agent tanımı, playbook,
> CLAUDE-talimatı — repo/gist/blog/başka projeden) core'un canlı yüzeyine **DOĞRUDAN
> GİRMEZ**. Önce buraya iner, gümrükten geçer, sonra yerine taşınır. Sebep: core CANLI —
> buraya giren şey junction'lı TÜM projelerde anında etki eder; hook/agent tanımı
> onaysız komut çalıştırma yüzeyidir.

## Süreç (her kalem için)

1. **İNDİR** → `intake/<tarih>-<kaynak-kısa-ad>/` altına ham haliyle koy
   (+ `KAYNAK.md`: URL, lisans, neden alındığı — 3 satır yeter).
2. **GÜVENLİK İNCELE** → çalıştırılabilir içerik satır satır okunur: komut çalıştıran
   hook mu, ağa çıkıyor mu, dosya siliyor mu, gizli veri okuyor mu?
   Şüpheli desen = kullanıcıya göster, karar onun.
3. **LİSANS** → lisansı yeniden-dağıtıma uygun mu; atıf gerekiyorsa `KAYNAK.md`'ye.
4. **GENERICIZE** → kaynak-projenin kimliği ayıklanır (pre-commit gate'i zaten
   yakalar, ama intake'te elle yapılır — gate son savunmadır).
5. **UYARLA + TAŞI** → normal PR ile hedef klasöre (skill → `claude/skills/`, script →
   `scripts/`, pattern → `playbook/` [+`applies_to`!]); PR açıklamasına intake klasör
   referansı. Taşındıktan sonra intake kopyası SİLİNİR (git tarihi kaynağı saklar).

## Kurallar

- intake/ altındaki hiçbir şey **çalıştırılmaz, import edilmez, junction'lanmaz** —
  karantina pasiftir. (`.claude/`, `scripts/` gibi aktif yollara dış içerik atlamak =
  gümrük atlamak; PR review'da reddedilir.)
- Bekleyen kalem birikirse (>2 hafta) ya taşınır ya silinir — intake depo değildir.
- Yabancı projeyi yerinde incelemek (içerik ALMADAN) ayrı iştir →
  `scripts/foreign_project_audit.py` + `scripts/guest_mode.py`.
