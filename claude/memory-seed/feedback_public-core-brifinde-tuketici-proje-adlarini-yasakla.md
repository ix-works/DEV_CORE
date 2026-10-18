---
name: feedback_public-core-brifinde-tuketici-proje-adlarini-yasakla
description: "Public çekirdeğe yazan ajan brifinde TÜKETİCİ PROJE ADLARINI açıkça yasakla + yayılım ölçümünü 'bir tüketici proje' diye yazdır — çekirdek sızıntı listesi diğer projelerin adlarını bilmez, ad commit'e ve PR geçmişine girer"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 10e41d9b-dbe7-47b8-b42e-99b8fddb9a68
  modified: 2026-10-03T15:16:02.201Z
---

Public çekirdeğe (DEV_CORE) yazan bir ajanı birden çok projede salt-okur ölçüm yapmaya
yönlendiriyorsan, brife şunu AYNEN yaz: *"rapor mesajında proje adlarını kullanabilirsin; ama çekirdek
dosyalarına (kod yorumu, changelog, reçete, tohum dersi) proje adı YAZMA — 'bir tüketici proje' de."*

**Why:** 2026-10-03 core #321 düzeltme turunda infra-expert changelog satırına yayılım ölçümünü proje
adıyla yazdı (bir müşteri adı). Kod yorumlarında aynı ajan "bir tüketicide" diye genericize etmişti;
yani kural biliniyordu ama changelog'da kaydı. Commit sızıntı kapısı YAKALAMADI: çekirdeğin
git-dir blocklist'inde o projenin adı yoktu (blocklist proje başınadır; bir projenin adı başka bir
projenin oturumundan yazılan commit'te bilinmez). Ad push'lanmış PR dalına girdi; bağımsız inceleme
BLOCKER verdi. Kullanıcı yalnız metnin düzeltilmesini seçti; ad PR commit geçmişinde kaldı (geri
alınamaz). Aynı tarama main'de eski bir tohum dersinde de aynı adı buldu (eski sızıntı).

**How to apply:**
- Brifte §4 placeholder maddesine tüketici proje adlarını örnek olarak ekle.
- Merge öncesi lider: `git diff origin/main <dal> | grep -i -E '<proje adları>'` — yalnız `-` satırı
  kalmalı.
- Brife yayılım ölçümü koyduğunda (birden çok proje okuma) bu risk en yüksektir.

Son-doğrulama: 2026-10-03 · Applies-to: public çekirdeğe yazan tüm ajan brifleri (infra-expert, bug-expert raporu dahil değil)
