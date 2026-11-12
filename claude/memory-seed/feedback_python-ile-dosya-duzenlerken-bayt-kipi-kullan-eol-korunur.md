---
name: feedback_python-ile-dosya-duzenlerken-bayt-kipi-kullan-eol-korunur
description: "Repo dosyasını Python'la yerinde düzenlerken metin kipi (open(...,encoding) + newline='' yazım) CRLF'yi LF'ye çevirir ve metindeki tek başına CR'yi YENİ SATIRA böler ⇒ tüm dosya diff'i. Bayt kipinde (rb/wb) bytes.replace kullan."
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 7969a665-1ae6-42c4-9e40-b8efb61144ca
---

**KURAL:** Var olan bir repo dosyasında Python'la yerinde değiştir-yaz yapacaksan **bayt kipi**
kullan: `b=open(f,'rb').read(); assert b.count(old)==1; open(f,'wb').write(b.replace(old,new))`
(`old`/`new` = `'…'.encode()`). Yazdıktan sonra `git diff --stat <f>` ile değişen satır sayısının
düzenlemeyle orantılı olduğunu gör; `git ls-files --eol <f>` önce/sonra aynı olmalı.

**NEDEN:** Metin kipinde okuma (varsayılan `newline=None`) `\r\n`'yi ve **tek başına `\r`'yi**
`\n`'ye çevirir; `newline=''` ile yazınca dosya LF'ye döner. Vaka 2026-11-12: bir projenin
`infra-findings.md`'si (8.684 satır, çoğu CRLF + 16 LF-only satır + metin içinde bir literal `\r`)
15/6 satırlık düzenleme sonrası `git diff --stat` **17.345** satır gösterdi; `i/-text` (tek CR
yüzünden git dosyayı ikili sayıyor) ⇒ `--ignore-cr-at-eol` maskesi de güvenilmez. Onarım: HEAD
satır sonlarını difflib eşlemesiyle geri yazmak + tek CR'yi bayt düzeyinde geri koymak → 13/5.

**NE ZAMAN:** `python - <<EOF` ile governance/memory/kaynak dosyasında replace yaparken.
Yeni dosya yazarken geçerli değil.

**NEREDE:** Windows + `text=auto`, karışık satır sonlu ya da CR'li dosyalar (sık: büyük
governance kayıt dosyaları).

Son-doğrulama: 2026-11-12 · Applies-to: tüm projeler, Windows, Python yerinde düzenleme.
prior-art: komşu dersler var ama bu sınıf yok — [[feedback_python-yazdigi-liste-crlf-tasir-xargs-sessizce-bosa-koser]] (araçlar arası liste) · [[feedback_template-drift-crlf-inflation]] (diff şişmesi okuma tarafı).
