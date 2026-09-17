---
name: feedback_gfm-tablo-bos-satir-tuzagi
description: Markdown tablosu render olmazsa üç ayrı biçimde kaybolur; `<p>…|---` deseni bunlardan yalnız birini yakalar
metadata:
  node_type: memory
  type: feedback
  originSessionId: a7d41ea7-18cd-4daf-a34c-df913d3c26a7
---

**Bir markdown tablosu render olmazsa `|---|---|` satırı ekranda ham metin olarak kalır** — hata
vermez, sessizdir. **Üç ayrı tetikleyicisi vardır ve üçü HTML'de farklı yere düşer:**

| Tetikleyici | HTML'de nereye düşer | `<p>[^<]*\|---` yakalar mı |
|---|---|---|
| Başlık satırından önce **boş satır yok** | `<p>` içinde ham metin | ✅ evet |
| Tablo **liste öğesi altında girintili** | **`<li>` içinde** ham metin | ⛔ **HAYIR** |
| Tablo **`<details>` ham-HTML bloğu** içinde | blok ham geçer | ⛔ **HAYIR** |

**Why:** 2026-08-19'da kendi kontrolüm *"0 kırık"* dedi, adversaryal ajan **7 kayıp tablo** ölçtü —
ikisi de doğruydu: dosyada `<p>` sızıntısı yoktu, tablolar `<li>` içinde kayboluyordu. Yani
**dedektörün kendisi kör noktalıydı** ve *"temiz"* raporu sahte güven üretti.

**How to apply:**
- **Doğru ölçüm — iki sayıyı karşılaştır, desen arama:**
  `ayrac = len(re.findall(r'(?m)^\s*\|[\s\-:|]+\|\s*$', src))` ↔ `html.count('<table>')`.
  **Eşit değilse tablo kaybolmuştur** — nerede kaybolduğuna bakmadan önce bunu ölç.
  Ek emniyet: `'|---' in html` (kod bloklarını `re.sub(r'<code>.*?</code>','',html,flags=re.S)` ile
  ayıkla; tuzağı **anlatan** metin yanlış pozitif verir).
- Tablo yazarken: **öncesine boş satır** · ⛔ **liste öğesi altına girintili tablo koyma** ·
  `<details>` içinde tablo yerine **liste** kullan.
- ⚠ **Parser'a bağlıdır:** `python-markdown` (repo PDF hattı) girintili tabloyu kaybeder,
  `markdown-it`/GitHub kaybetmez. *"GitHub'da görünüyor"* düzeltmeyi gereksiz kılmaz —
  ama **hangi hattı ölçtüğün** yazılmalı.
- ⚠ **Toplu girinti düzeltmesi RİSKLİDİR:** `<details>`/liste bağlamında girinti kaldırmak
  komşu blokların ayrıştırmasını bozabilir (ölçüldü: 14 tablo → 9). Düzeltmeden **önce ve sonra**
  `<table>` sayımı yap; kötüleşiyorsa **geri al**.

İlgili: [[feedback_iddia-yazma-aninda-kanit-kurallari]] · [[feedback_dogrulama-sezgileri-dort-kural]] · [[feedback_reviewer-checklist-vs-wired-validator]]
