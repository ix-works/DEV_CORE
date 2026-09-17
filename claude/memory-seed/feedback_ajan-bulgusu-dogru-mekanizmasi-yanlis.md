---
name: feedback_ajan-bulgusu-dogru-mekanizmasi-yanlis
description: "Ajanın POZİTİF bulgusunu kabul ederken GEREKÇESİNİ ayrı ölç — bulgu doğru, mekanizma yanlış olabilir; yanlış mekanizma kayda geçerse sonraki okuyucu yanlış yerde arar"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 2fcd323d-256d-4115-adc0-ffa0aaac6a0e
---

Bir alt-ajan **haklı bir kusur** bildirdiğinde, bulguyu kabul et ama **gerekçesini AYRI bir iddia
say ve kendin ölç**. İkisi bağımsızdır: *"X bozuk"* doğru olabilirken *"çünkü Y oluyor"* yanlış olabilir.

**Vaka (2026-08-22):** gateway ajanı ADR 0006 ön-uçuş komutunun yolunun kırık olduğunu bildirdi —
**haklıydı** (6 canlı talimat yüzeyinde `core/` öneki eksikti; en kritiği **her oturum yüklenen**
`CLAUDE.core.md`). Gerekçe olarak *"boru hattında `exit=0` gibi görünür, yeşil sanılır"* dedi.
**Ölçüm:** doğrudan çağrı → **`exit=2`**, `| grep BLOCKER` → **`exit=1`**. Sahte-yeşil-exit **YOK**.
**Gerçek risk başkaydı ve daha sinsiydi:** komut hiç koşmadığı için **`BLOCKER` satırı da basılmaz**
⇒ çıktıya bakan *"blocker yok ⇒ temiz"* der. Kusur exit kodunda değil, **kanıtın yokluğunun kanıt
sanılmasında**.

**Why:** Kayıt, bulgudan uzun yaşar. Yanlış mekanizma kayda geçerse (a) düzeltmeyi yapan **yanlış
yerde** arar, (b) *"exit kodunu kontrol edelim"* gibi **işe yaramaz bir gate** doğabilir, (c) gerçek
sınıf (*"sessiz kanıt yokluğu"*) hiç adlandırılmadığı için **başka yüzeylerde tekrar eder**.
Ayrıca bu, tersinin kardeşidir: olumsuz dönüşü sorgulamak zaten kuraldır
([[feedback_ajan-olumsuz-donusu-kanitla-sorgula]]) — **pozitif dönüşün gerekçesi de aynı muameleyi
hak eder**, çünkü "haklı çıkmış ajan" güveni gerekçeye de yayar.

**How to apply:** Ajan raporunu kayda/karara çevirirken iki soruyu ayrı sor:
① **Bulgu gerçek mi?** (kendi kontrol grubunla doğrula) ② **Anlattığı mekanizma gerçek mi?**
(mekanizmayı **birebir tekrarla** — komutu koş, exit kodunu oku, çıktıyı gör).
Mekanizma tutmuyorsa **iddiayı DARALT ve gerçek olanı yaz**; ajanın cümlesini kopyalama.
İlişkili: [[feedback_tarama-ciktisi-hipotezdir-is-listesi-degil]] · [[feedback_sonucu-olc-uygulamayi-degil]] ·
[[feedback_exit0-degil-cikti-kaniti.md]] (exit 0 ≠ kanıt) · [[feedback_yesil-sinyalin-kapsamini-sor]]

Son-doğrulama: 2026-08-22 (run_review yol kusuru — bulgu doğru, mekanizma çürütüldü, kayıt daraltıldı)
Applies-to: TÜM projeler · her alt-ajan raporunun kayda/karara dönüşü
