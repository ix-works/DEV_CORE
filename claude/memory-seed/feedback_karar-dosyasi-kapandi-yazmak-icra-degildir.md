---
name: feedback_karar-dosyasi-kapandi-yazmak-icra-degildir
description: "Kendi karar dosyanda 'KAPANDI' yazmak kaydı kapatmaz — kapanış İCRANIN kanıtına dayanır; toplu kuyruk turlarında bu hata SESSİZ ve ÖLÇEKLİ olur (2026-08-29: 84 kaydın 3'ü kanıtsız kapatılmıştı, kapıyı yazan ajan yakaladı)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f911c8cf-83f3-4ff2-bd38-ae5ee4790ae5
---

⛔ **KARAR ≠ İCRA.** Bir kuyruk kaydı için *"şöyle kapatılacak"* kararı vermek, o kaydı
**kapatmaz**. `DURUM: KAPANDI` yazmanın ön koşulu **icranın kanıtıdır** (merge edilmiş commit,
koşan kapı, canlı ölçüm) — kararın kendisi değil.

**Vaka 2026-08-29 (ölçüldü):** 84 kayıtlık kuyruğun tamamı için kararlarımı tek dosyada topladım
(`.tmp/Q34-DURUM-KARARLARI-*.md`) ve bir ajana **mekanik uygula** dedim. Üç kalemde
(`#5③`, `#13`, ve birleştirilmemiş bir worktree'deki **5 eksen**) `KAPANDI` yazmıştım; oysa
① ikisinin icrası henüz PR'a girmemişti ② beşi **merge edilmemiş** bir dalda duruyordu ⇒ `main`'de
yoktu. Ajan **kanıtsız kapanışı yazmayı REDDETTİ** ve her birini ayrı ayrı bayrakladı.
⇒ Dal `main`'e alındı, kararlar düzeltildi, sonra yazıldı.

**Why:** Tekil işte bu hata görünür — kullanıcı ertesi gün *"hani yapılmıştı?"* der. **Toplu
turda görünmez:** 84 kaydın içinde 3 yanlış kapanış, kuyruğun **kendi güvenilirliğini** bozar
ve bir daha kimse o kaydı açmaz. Kuyruk, açık işin **tek makinece sayılabilir** kaynağıysa,
yanlış `KAPANDI` bir bulguyu **silmekle** eşdeğerdir. Ayrıca *"worktree'de duruyor"* ile
*"`main`'de"* aynı şey değildir — dalda biten iş, **merge edilene kadar YOKTUR**.
İlişkili kök: [[feedback_flag-degil-icra-bekleyen-is-kapat]] (flag ≠ icra) — bu kayıt onun
**toplu/ölçekli** kardeşi.

**How to apply:** Kapanış yazmadan önce her kayıt için tek soruyu sor: *"bunun `main`'deki
kanıtı ne?"* — commit SHA'sı, kapı çıktısı ya da canlı ölçüm gösteremiyorsan `KAPANDI` yazma;
`KARAR-VERİLDİ` / `İCRA-BEKLİYOR` gibi ayrı bir durum kullan. Toplu tura girmeden önce
**birleştirilmemiş dal kalmasın** — worktree denetimini kapanıştan ÖNCE koş. Ve bu kuralı
**kapıya bağla**: uygulayıcı ajan kanıtsız kapanışı reddedebilmeli; bu turda beni tam da o
kapı yakaladı. İlişkili: [[feedback_done-tam-kapsam-dogrula]] ·
[[feedback_kural-gate-lenmeli-yoksa-anlamsiz]] · [[feedback_kapi-kosarken-dosya-donar-md5-teyidi]]
