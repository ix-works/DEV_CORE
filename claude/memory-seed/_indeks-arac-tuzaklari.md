---
name: _indeks-arac-tuzaklari
description: Araç, kabuk ve kodlama tuzaklarının tam indeksi
metadata: 
  node_type: memory
  type: reference
---

# Araç · kabuk · kodlama tuzakları — tohum indeksi

> Bash/PowerShell/regex/kodlama katmanının sessiz kusurları. Bu dosya `MEMORY.md`'den link'lenir; dersler burada yaşar.

**8 ders.**

- [Bash heredoc kacis ve utf8 bozulmasi](feedback_bash-heredoc-kacis-ve-utf8-bozulmasi.md) — Bash tool'una gecen komut metni ters-bolu kacislarini ve Turkce karakterleri BOZAR — tirnakli heredoc bile korumaz
- [Gfm tablo bos satir tuzagi](feedback_gfm-tablo-bos-satir-tuzagi.md) — Markdown tablosu render olmazsa üç ayrı biçimde kaybolur; `<p>…|---` deseni bunlardan yalnız birini yakalar
- ⭐ [Mojibake taramasi ciplak karakter aramaz](feedback_mojibake-taramasi-ciplak-karakter-aramaz.md) — Brifinge yazılan mojibake taraması çıplak `Â`/`Ã` aramaz — Türkçede meşru (hâlâ, kâr); mojibake İKİLİ dizidir. Liderin brifing kapısı da bir kapıdır, ajan ona itaat edip doğru metni bozar
- [Powershell commandline filtresi kendi kabugunu yakalar](feedback_powershell-commandline-filtresi-kendi-kabugunu-yakalar.md) — Get-CimInstance Win32_Process | Where CommandLine -like '*X*' filtresi, X'i içeren KENDİ PowerShell aracı kabuğunu da döndürür → Stop-Process kendini öldürür (exit 255, çıktı yok) ve 'kalan: 1' sahte sayım verir. $PID ve ParentProcessId -ne $PID ile dışla. 2026-08-29 watchdog daemon temizliğinde 5 tur kaybettirdi
- ⭐ [Python yazdigi liste crlf tasir xargs sessizce bosa koser](feedback_python-yazdigi-liste-crlf-tasir-xargs-sessizce-bosa-koser.md) — Windows'ta Python'un yazdığı satır listesi CRLF taşır; git/xargs'a beslenince her ad sonunda \r kalır, eşleşme tutmaz ve işlem SESSİZCE hiçbir şey yapmaz. `| wc -l` çıktıyı sayarken HATA satırlarını sayar ⇒ başarı gibi görünür.
- [Timeout rg shim sessiz sifir](feedback_timeout-rg-shim-sessiz-sifir.md) — Kabukta `timeout <n> rg … 2>/dev/null` SESSİZCE boş döner — rg bir shim, timeout onu exec edemez (rc=127) ve hata stderr'le yutulur; boş arama sonucu bir hüküm değildir
- ⭐ [Tr karakter varyantli arama](feedback_tr-karakter-varyantli-arama.md) — Müşteri/metin aramasında Türkçe İ/Ş/Ç varyantı — ASCII LIKE 'yok' der (TRİGO vakası)
- [Xml tag regexi attribute icindeki buyuktur isaretinde kesilir](feedback_xml-tag-regexi-attribute-icindeki-buyuktur-isaretinde-kesilir.md) — Toplu XML/HTML düzenlemede `<tag[^>]*>` deseni attribute DEĞERİ içindeki `>` karakterinde erken keser ve dosyayı bozar; tırnak-duyarlı desen + parser doğrulaması şart

<!-- makine-okunur erişilebilirlik çapası (C-MEM-01): indeks bütünlüğü kapısı
     cift-koseli-parantez linki arar, markdown link saymaz. Liste yukarıdakiyle AYNI olmalı. -->
[[feedback_bash-heredoc-kacis-ve-utf8-bozulmasi]] · [[feedback_gfm-tablo-bos-satir-tuzagi]] · [[feedback_mojibake-taramasi-ciplak-karakter-aramaz]] · [[feedback_powershell-commandline-filtresi-kendi-kabugunu-yakalar]] · [[feedback_python-yazdigi-liste-crlf-tasir-xargs-sessizce-bosa-koser]] · [[feedback_timeout-rg-shim-sessiz-sifir]] · [[feedback_tr-karakter-varyantli-arama]] · [[feedback_xml-tag-regexi-attribute-icindeki-buyuktur-isaretinde-kesilir]]
