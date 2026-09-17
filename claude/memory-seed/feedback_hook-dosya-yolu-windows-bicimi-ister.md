---
name: feedback_hook-dosya-yolu-windows-bicimi-ister
description: "Bash tool'undan çağrılan git/gh komutlarında -F/--file argümanı POSIX yol (/c/...) alırsa Python hook'u dosyayı OKUYAMAZ ve FAIL-CLOSED reddeder — Windows yolu (C:/...) ver"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 1b79c373-845b-483c-b916-c9b4b5cdfc6e
---

`git commit -F /c/Users/.../msg.txt` **hook tarafından reddedilir**: COMMIT-MESAJI SIZINTI
GATE dosyayı Python'la açar, Python `/c/...` MSYS yolunu **çözemez** ⇒ gate *"okunamadı"*
der ve fail-closed davranıp işlemi bloklar. Komutun kendisi (git) o yolu çözerdi — yani
**araç çalışırdı, kapı çalışmadı**; hata mesajı sızıntıymış gibi görünür ama sebep yol
biçimidir. Ölçüldü 2026-09-02: aynı dosya `<KULLANICI-KOKU>` yazılınca commit geçti.

**Why:** Bash tool'u MSYS kabuğudur, hook'lar Windows Python'ıdır. İkisi arasında geçen
her **dosya yolu argümanı** (yalnız `cd`/`cat` gibi kabuk-içi kullanımlar değil) sınırı
geçer. `-F`/`--file`/`--body-file` bu sınıfın en sık örneğidir.

**How to apply:** Bash tool'undan `git commit -F`, `gh pr create --body-file`,
`gh pr merge --body-file` gibi **dosya yolu alan** argümanlarda daima Windows biçimi
(`C:/...`, ileri bölü çalışır) yaz — `cd` ve okuma komutlarında POSIX yol serbest.
Hook reddi geldiğinde önce mesajı OKU: *"okunamadı"* diyorsa yol biçimidir, içerik değil;
*"genericize"*/*"sızıntı"* diyorsa gerçekten metni düzelt. Bkz.
[[feedback_auto-mode-deny-kararsiz-yeniden-dene]] (önce red mesajını oku) ·
[[feedback_bash-heredoc-kacis-ve-utf8-bozulmasi]].

---
**Son-dogrulama:** 2026-09-02 (ders yazim tarihi — o gunden beri YENIDEN OLCULMEDI) · **Applies-to:** bu cekirdegi kullanan tum projeler

⚠ **ARAC IDDIASI** — bu ders *"bugun su arac/kapi boyle davraniyor"* der, yapisal bir olgu
degil. Arac surumu degismis olabilir: davranisa **dayanmadan once bir kez olc**. (Vaka: bir
kardes ders, dayandigi kusur duzeltildikten sonra 3 hafta bayat yasadi; tohuma alinmadan
once olculup elendi.)
