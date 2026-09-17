---
name: feedback_worktree-kapatmadan-once-ajanin-nihai-raporunu-al
description: "Merge sonrası worktree'yi kapatmadan önce ajanın NİHAİ raporunu al — \"completed\" bildirimi, SendMessage ile yeniden uyanıp arka plan süiti koşan ajanı kapsamaz"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cca08bdf-c505-460c-a1ba-8d1635bd8f7c
---

Bir infra ajanının PR'ı merge olunca worktree'yi hemen kapatma. Önce ajanın nihai raporunun geldiğini gör. Görev bildirimindeki "completed" durumu tek başına yetmez: ajan her durduğunda bildirim gelir, ama SendMessage ile yeniden uyanabilir ve arka planda süit koşturuyor olabilir.

**Why:** 2026-09-13, Q203. PR #226 merge edildi ve bildirim "completed" dediği için `--wt-kapat` çalıştırıldı. Oysa ajan KOD DONDU'dan sonra tam süiti koşuyordu. Silinen fixture'lar yüzünden süit 71 kez `No such file` verdi (205/276) ve ajan "worktree bozuluyor" diye DERHAL alarmı yolladı. Kod main'de olduğu için kayıp yaşanmadı, ama commit'lenmemiş reçete metni riske girdi ve tam süit kanıtı kaybedildi.

**How to apply:** Merge'den sonra ajana "kapatıyorum, commit'lenmemiş bir şey var mı?" diye sor. Nihai rapor (ya da "dur" onayı) gelince `--wt-kapat` koş. Brifinglerde de şunu iste: tam süit KOD DONDU'dan ÖNCE koşulsun. İlgili ders: [[kapi-kosarken-dosya-donar-md5-teyidi]].

Son-doğrulama: 2026-09-13 · Applies-to: lider, infra-expert worktree yaşam döngüsü
