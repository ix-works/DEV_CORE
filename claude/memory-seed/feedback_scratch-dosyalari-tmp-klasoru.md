---
name: feedback_scratch-dosyalari-tmp-klasoru
description: "Geçici/scratch dosyalar (ekran görüntüsü, çıktı vb.) ana klasöre DEĞİL .tmp/'ye yaratılır; .tmp/ + .playwright-mcp/ gitignore'da, git'e gönderilmez"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a1b6afef-4b32-4db8-92e7-c8825dc4ffa1
---

Geçici / scratch dosyaları (ekran görüntüsü, deneme çıktıları, dökümler vb.) **ana repo klasörüne yaratma** — kök dizini kirletiyor. Hepsini **`.tmp/`** altına yarat. `.tmp/` ve `.playwright-mcp/` `.gitignore`'da → git'e gönderilmez. Playwright screenshot'larında `filename` parametresine `.tmp/...` yolu ver.

**Why:** Kullanıcı kuralı (2026-06-13): bir UI doğrulama oturumunda 7 `.png`'yi repo köküne yarattım → "ana klasör oluşturmuşsun, bu tip işlemler için temp klasörü oluştur, git'e göndermene gerek yok". Kök dizin temiz kalmalı; geçici artefaktlar versiyonlanmamalı.

**How to apply:** Ekran görüntüsü / geçici dosya gerektiğinde önce `.tmp/`'ye yaz (yoksa `mkdir -p .tmp`). Asla repo köküne `*.png`/scratch bırakma; iş bitince silmek zorunda kalma. Bu kural tarayıcı-doğrulama nudge'ına da işlendi ([[scripts/hooks/skill_injector.py]] `_BROWSER` adım 4) ve token-verimli akışın parçası ([[feedback_grid-ui-local-run-popup]] · governance/tooling-plugins.md §playwright). İlgili: kalıcı script gerekiyorsa `.tmp/` değil `scripts/TempScripts/` (farklı amaç — script vs artefakt).
