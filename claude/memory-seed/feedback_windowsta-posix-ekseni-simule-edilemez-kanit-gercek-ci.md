---
name: windowsta-posix-ekseni-simule-edilemez-kanit-gercek-ci
description: Dosya-sistemi dokunan infra işinde POSIX davranışı Windows'ta simüle edilemez — case-sensitive TEMP yalnız HARF eksenini taklit eder; symlink/`..` ekseninin kanıtı gerçek Linux CI koşusudur; eksenler İLK brife yazılır
metadata:
  type: feedback
  seed: evet
---

Dosya yolu / dizin gezinmesi / bağ (link) çözümü içeren bir infra değişikliğinde **dört platform ekseni** vardır: ① harf duyarlılığı ② `..` çözümü (sözcüksel mi fiziksel mi) ③ Windows junction ④ POSIX symlink. Windows makinede `fsutil setCaseSensitiveInfo` ile açılan TEMP dizini **yalnız ①'i** taklit eder; ②–④ POSIX'te farklı davranır ve burada ölçülemez.

Vaka (2026-09-26, çekirdek PULL-BEFORE-EDIT turu): UI kaynak okuyucusu `rglob` ile gezindi. Windows'ta tüm vektörler yeşildi, ubuntu CI'da bağ vektörü FAIL verdi — Py 3.11 `rglob` junction'a iner ama POSIX symlink'ine inmez. Ürün düzeyinde `os.scandir` + ata kümesiyle düzeltildi, kanıtı gerçek CI koşusu oldu. Eksen brife baştan konmadığı için tur fazladan döndü.

**Why:** "Windows'ta yeşil" = "o platformda yeşil"; POSIX iddiası kanıtsız kalır ve hata ancak CI'da (ya da kullanıcı makinesinde) görünür.

**How to apply:** Dosya-sistemi dokunan infra brifinde dört ekseni İLK turda yaz; POSIX iddiasının kanıtı için dalı push edip gerçek Linux CI koşusunu bekle, yerel proxy'yi kanıt sayma. Ölçülemeyen ekseni "DOĞRULANAMADI" diye işaretle.

Son-doğrulama: 2026-09-26
Applies-to: çekirdek infra (hook/validator/araç) — Windows geliştirme makinesi + Linux CI
