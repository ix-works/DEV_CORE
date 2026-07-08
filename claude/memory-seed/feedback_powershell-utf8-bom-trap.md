---
name: feedback_powershell-utf8-bom-trap
description: "PowerShell 5.1 Set-Content -Encoding utf8 BOM ekler, JSON/tooling kırar; Edit/Write tool veya WriteAllText(UTF8Encoding $false) kullan"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 221a6a93-26fb-43be-9837-c5989e246ea5
---

Windows PowerShell 5.1'de `Set-Content -Encoding utf8` (veya `Out-File -Encoding utf8`) dosyaya **UTF-8 BOM (﻿ / 239,187,191)** ekler. 2026-06-10'da config'lerde `-replace ... | Set-Content -Encoding utf8` ile package.json'a BOM girdi → `fiori run` mockserver `Unexpected token "﻿"... is not valid JSON` ile çöktü (JSON parser BOM'u sevmez). YAML/properties de etkilenebilir.

**Why:** PS 5.1'in `utf8` encoding'i BOM'LU yazar; `utf8NoBOM` 5.1'de YOK. JSON/UI5-tooling/Node BOM'u parse edemez. Sessiz tuzak: dosya görsel olarak doğru görünür, byte düzeyinde bozuk.

**How to apply:** (1) Tool'ların okuyacağı dosyalara (json/yaml/abap/properties) PowerShell ile yazma; **Edit/Write tool** kullan (BOM'suz). (2) Mecbursan BOM'suz UTF-8: `[System.IO.File]::WriteAllText($path, $content, (New-Object System.Text.UTF8Encoding $false))`. (3) BOM temizleme: `$c.TrimStart([char]0xFEFF)` + WriteAllText. (4) Şüphede ilk baytları kontrol et: `[IO.File]::ReadAllBytes($p)[0..2]` (239,187,191 = BOM). İlişkili: skill Windows-encoding notu, [[feedback_hook-komut-project-dir-execform]] (Windows yol tuzakları).
