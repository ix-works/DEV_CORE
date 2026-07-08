---
name: feedback_hook-komut-project-dir-execform
description: "settings.json komutları göreceli/hardcoded yol kullanmamalı, ${CLAUDE_PROJECT_DIR} zorunlu; AMA hook=exec-form(args), statusLine=tek command STRING (args yok sayılır)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 08e5fb65-fb2e-42f1-baf5-bfc3e9d94061
---

`.claude/settings.json` içindeki komutlar **göreceli/hardcoded yol kullanmamalı**, her zaman `${CLAUDE_PROJECT_DIR}` placeholder. AMA iki alanın ŞEMASI FARKLI:

- **Hook** → exec-form destekler: `{ "command": "python", "args": ["${CLAUDE_PROJECT_DIR}/scripts/hooks/X.py"] }` (kanıt: session_start hook'u bu formla çalışıyor).
- **statusLine** → exec-form DESTEKLEMEZ; `args` SESSİZCE YOK SAYILIR → sadece `python` argümansız koşar, JSON stdin'i kod sanıp SyntaxError → **satır boş kalır**. Doğrusu tek shell-form STRING: `{ "command": "python \"${CLAUDE_PROJECT_DIR}/scripts/statusline.py\"" }`.

**Why:** Hook'lar oturumun o anki cwd'siyle çalışır. UI işi sırasında (npm install / ui5 serve) Bash aracı cwd'yi `ERP/.../ui/<app>` alt klasörüne kalıcı kaydırınca göreceli yol yanlış köke çözülür → "can't open file ...skip_injector.py" → her promptta hata, terminali kapat-aç gerekir. `${CLAUDE_PROJECT_DIR}` Claude Code tarafından düz metin olarak proje köküne çözülür (shell-bağımsız, Windows PowerShell dahil), exec-form ise shell tokenizasyonu/quoting riskini sıfırlar.

**How to apply:** Yeni HOOK → `command:"python" + args:["${CLAUDE_PROJECT_DIR}/..."]`. Yeni STATUSLINE → `command:"python \"${CLAUDE_PROJECT_DIR}/...\""` (args yazma, işe yaramaz). settings.json paylaşılan dosya → sabit mutlak yol da gömme (takım kırılır); placeholder taşınabilir. Boş statusline teşhisi: komut string'ini elle stdin'e JSON vererek koştur. Bu T12 kapsamında template'e de port edilir. 2026-06-04 hook exec-form uygulandı; 2026-06-09 statusLine args→string-form düzeltildi (args sebebiyle satır hiç görünmüyormuş). İlgili: [[project_development-template-repo]], [[feedback_hook-bakim-protokolu-t11]].
