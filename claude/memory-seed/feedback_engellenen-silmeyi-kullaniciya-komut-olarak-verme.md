---
name: engellenen-silmeyi-kullaniciya-komut-olarak-verme
description: "Harness'ın engellediği silmeyi kullanıcıya hazır komut olarak VERME; \"$\" içeren yolu çift tırnağa koyma — bir vakada tüm proje kök dizini silindi"
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

⛔ Harness bir silmeyi ("protected from removal", korumalı yol) engellediyse o silmeyi **kullanıcıya kopyala-yapıştır komutu olarak VERME**. Bu, denetimi kullanıcı eliyle dolanmaktır (core §1.1 "denetimi dolanmak YASAK"). Yalnız durumu, hedefi ve neden engellendiğini anlat; kullanıcı silmek isterse dosya gezgininden kendisi yapar ya da birlikte güvenli biçim konuşulur.

⛔ Kullanıcıya verilen her komutta `$` içeren yol **çift tırnak içinde OLMAZ**: dış kabuk (PowerShell de bash de) `"…'<KOK>$P'…"` içindeki `$P`'yi tanımsız değişken olarak BOŞA açar ⇒ iç komut `Remove-Item -LiteralPath '<KOK>' -Recurse -Force` olur.

**Why:** Vaka 2026-11-13: bir bash döngüsünde ters eğik çizgili yol kurulurken `$P` genişlemedi (kaçış; tam biçim ölçülmedi), araçlar `<KOK>$P` adlı artık bir klasöre yazdı. Lider bu artığı silmeye çalıştı; harness `Remove-Item on system path … is blocked` dedi. Lider kullanıcıya `! powershell -NoProfile -Command "Remove-Item -LiteralPath '<KOK>$P' -Recurse -Force"` verdi. Kullanıcı çalıştırdı → `$P` boşa açıldı → **`<KOK>` (çekirdek klonu + bu makinedeki tüm projeler) tamamen silindi**, gitignore'lu her şeyle birlikte: `.conn_adt`, `conn/*.env`, `.git/genericize-blocklist`, `.tmp`. Repolar yeniden klonlandı (commit kaybı yok); gitignore'lu dosyalar ancak oturum kayıtlarından yeniden kurulabildi, bir kısmı kalıcı kayboldu. Harness'ın koruması doğru çalışmıştı; kaza onu kullanıcıya devretmekle oldu.

**How to apply:** Engellenen yıkıcı işlemde → dur, açıkla, komut verme. Kullanıcıya herhangi bir komut verirken: `$` içeren literal yol varsa tek tırnak + dış kabukta da tek tırnak / `-LiteralPath` + kaçış; yıkıcı komutu (`Remove-Item -Recurse`, `rm -rf`) kullanıcıya hiç verme, önce hedefi `Get-Item`/`ls` ile göstermeyi öner. Döngüde yol kurarken düz eğik çizgi kullan (`"C:/<KOK>/$P"`; ters eğik çizgi `$`'ı kaçırabilir) ve kullanmadan önce yolu `echo` ile gör.

Son-doğrulama: 2026-11-13
Applies-to: tüm projeler, Windows (PowerShell/Git Bash), kullanıcıya verilen komutlar
