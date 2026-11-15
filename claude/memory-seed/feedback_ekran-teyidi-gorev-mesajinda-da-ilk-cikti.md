---
name: feedback_ekran-teyidi-gorev-mesajinda-da-ilk-cikti
description: "Oturumun ilk mesajı doğrudan iş istese de (\"nerede kaldık, devam edelim\") Ekran Teyidi ilk metin çıktısıdır — işe başlamadan (yazma/merge/spawn öncesi) basılır; atlanırsa kullanıcı hook'ların/çekirdeğin yüklenmediğini sanar. Compact sonrası teyit istenmez (session_start)"
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

Oturumun ilk yanıtında, kullanıcının ilk mesajı somut bir iş isteği olsa bile (*"en son ne yaptık, hatırla ve devam edelim"*), çekirdek §3 **Ekran Teyidi** bloğu **ilk metin çıktısı** olarak verilir. Durum toplamak için yapılan salt-okur çağrılar (RESUME/SESSION_NOTES okuma, `run_all_validators --quick`) teyitten önce gelebilir, çünkü teyidin satırlarını onlar doldurur. **Yazma, merge, dal açma ya da ajan başlatma ise her zaman teyitten SONRA gelir.** `[YUKLEME — session_start]` satırı aynen aktarılır.

**Why:** Vaka 2026-11-13 (bir tüketici projesi): SessionStart hook'u çalıştı ve hem `[YUKLEME]` satırını hem de "ilk yanıt Ekran Teyidi ile başlar" hatırlatmasını verdi. `instructions-loaded.log` çekirdeğin yüklendiğini kaydetti. Buna rağmen lider "devam edelim" isteğini görünce doğrudan işe girdi: dal açtı, birleştirme yaptı, ajan başlattı ve teyidi hiç basmadı. Kullanıcı *"session start hook'ları neden tetiklenmedi, core'daki hook'lar sende tetiklenemiyor mu?"* diye sordu. Teyit eksik olunca kullanıcı mekanizmanın bozuk olduğunu düşünüyor ve sağlam çalışan altyapıyı teşhis etmeye başlıyor (§3: "format atlanırsa kullanıcı loader'ın yüklenmediğini varsayar"). Hook'un hatırlatması yetmedi, çünkü görev odaklı ilk mesaj bu hatırlatmayı bastırdı.

**How to apply:** Oturumun ilk turunda, ilk metni yazmadan önce teyit bloğunun yazılıp yazılmadığına bak. İlk yazma, dal açma, merge ya da spawn çağrısından önce kendine "teyit bloğu ekranda mı?" diye sor. Değilse önce onu yaz. Kullanıcı hook'ların çalışıp çalışmadığını sorarsa önce kanıt göster: bağlamdaki `[YUKLEME]` satırı, `.tmp/instructions-loaded.log` içinde bu oturumun `sid`'i ve settings'teki hook sayısı. Ardından eksik teyidi bas.

**Kapsam — compact sonrası istenmez:** compact sonrası Ekran Teyidi istenmez. `session_start` hook'u `source == "compact"` dalında teyit satırını çıkarır ve "Ekran Teyidi ISTENMIYOR, kaldığın yerden devam et" der (`scripts/hooks/session_start.py`, `STATIK_COMPACT`). Bu ders yalnız hook'un teyit istediği açılışlar içindir. Bugünkü kodda bunlar `startup`, `resume`, `clear`, `fork` ve tanınmayan `source` değeridir. `resume` için hook teyidi hâlâ istiyor; bunun gerekli olup olmadığı hook'ta "ölçülmedi, ayrı karar" diye yazılı. Kural, hook'un o açılışta ne dediğine bakar.

Son-doğrulama: 2026-11-13
Applies-to: bu çekirdeği kullanan tüm projeler, oturumun ilk yanıtı (tüm profiller)
prior-art: yok (memory'de "ekran teyid" eşleşmesi yok; core `playbook/lessons-learned.md` + `claude/memory-seed` içinde de yok)
