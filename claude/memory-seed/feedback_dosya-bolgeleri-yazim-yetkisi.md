---
name: feedback_dosya-bolgeleri-yazim-yetkisi
description: "Takımda dosya yazım bölgeleri (A metodoloji=lider, B paket=feature, C SAP=gateway, D memory=lider)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 791c30b9-6728-4e20-94d7-8d4a14484d2d
---

Kullanıcı (2026-06-14, "ultrathink" tasarımı) takımda **3 dosya bölgesi + yazım yetkisi** kuralını koydu:
- **Zone A — Metodoloji/Yönetişim/Araç** (`CLAUDE.md`, `AGENTS.md`, `standards/`, `playbook/`, `governance/`, `.claude/`, `scripts/`, `mcp_servers/`) = **yalnız LİDER** yazar; feature/gateway/research salt-okunur.
- **Zone B — Özellik/Paket eseri** (`ERP/<pkg>/` SAP kaynak + `docs/` FS/TS + `SESSION_NOTES.md` + `.rules.md`) = sahibi **feature ajanı (kendi paketi) + lider**; gateway OKUR, düzenlemez.
- **Zone C — SAP sistemi** = yalnız **gateway** (MCP write) / solo'da lider.
- **Zone D — Lider süreklilik deposu (memory)** (`~/.claude/projects/.../memory/*.md` + `MEMORY.md` index, repo DIŞI) = **yalnız LİDER**; ajanlar ders/karar/tuzağı lider'e **RAPORLAR**, dosya/pointer yazmaz (2026-06-15 ihlali: feature-ajan dersi doğrudan memory'ye yazdı → kural matrise + 3 role prompt'a eklendi, T11).
- `.tmp/` herkes; **git commit yalnız lider.**
- **Tek cümle:** proje-geneli kural/yöntem .md = LİDER; belirli paketi belgeleyen .md = o feature ajanı.

**Why:** Kullanıcı gateway'in metodoloji/.md + tooling değiştirdiğini fark edince ("haberim yoktu") rol netliği istedi. Paylaşılan altyapı tek-sahip olmalı (drift önleme); kök-fix tasarım kararıdır → en geniş context'i olan lider.

**How to apply:** **Enforcement = orantılı (1+2+3):** research SAP-write+Edit yok (sert) · lider tek-commit + her diff-inceleme (sert geri-durdurucu) · rol prompt'larında bölge (savunma derinliği). Saf `tools:` allowlist yol-granüler DEĞİL + Bash süper-küme → tam-önleme için ileride PreToolUse yol-guard (`transcript_path`'te `/subagents/` tespiti) gerekir, şimdilik KAPSAM DIŞI. Kanonik: [[governance/agent-teams-operating-model]] §3A + 3 rol `.claude/agents/`. İlgili: [[feedback_arac-kod-fix-lider-isi]].
