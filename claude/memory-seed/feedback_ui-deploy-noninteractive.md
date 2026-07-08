---
name: feedback_ui-deploy-noninteractive
description: "UI5 BSP deploy non-interaktif YAPILIR — '.conn_adt' kimlik → FIORI_TOOLS env + --yes; 'deploy edemem' deme, standards/03 §2.4.1 oku"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d2889f86-35d9-41c7-b431-b18fba6cedae
---

Freestyle UI5 app'i BSP'ye deploy ederken **"ben çalıştıramam / kimlik yok"** DEME (2026-06-12 hatası: FIORI_TOOLS env boş görüp "yapamam" dedim, oysa reçete vardı). Çalışan non-interaktif yöntem **`standards/03-coding-ui-fiori.md` §2.4.1**'de:

```bash
U=$(grep '^ADT_SAP_USER=' /c/IX/<PROJECT_NAME>/.conn_adt | cut -d= -f2 | tr -d '\r')
P=$(grep '^ADT_SAP_PASSWORD=' /c/IX/<PROJECT_NAME>/.conn_adt | cut -d= -f2- | tr -d '\r')
FIORI_TOOLS_USER="$U" FIORI_TOOLS_PASSWORD="$P" \
  npm --prefix <app_mutlak_yol> run deploy -- --yes
```

**Kritik:** (1) `--yes` → "Start deployment (Y/n)?" prompt'unu atlar (yoksa non-interactive bash'te takılır — benim ilk denemem buydu); (2) kimlik **CLI `--username/--password` DEĞİL** (shell:true mangling → 401 + log sızıntısı), **env** ile; (3) `tr -d '\r'` ŞART (.conn_adt CRLF parolayı bozar); (4) mutlak `--prefix`/`.conn_adt` yolu (cwd kayması); (5) hedef URL = `.conn_adt` kanonik host; (6) "ZZ1_ prefix" = soft uyarı, bloklamaz; (7) stray `webapp/.claude` → 400 "Type of file unknown" → ui5-deploy.yaml `exclude /.claude`. **İŞ ANINDA standards/03 §2.4.1'i OKU** (deploy = tetik). Backend (CDS/class) zaten MCP push+activate ile canlı, ayrıca deploy gerektirmez — UI deploy yalnız UI app'leri içindir. İlişkili: [[feedback_grid-ui-local-run-popup]].
