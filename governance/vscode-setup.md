# VS Code Eklenti & Ayar Kurulumu — <PROJECT_NAME>

> **Amaç:** Claude Code'un yanında, editörde gerçek değer katan VS Code eklentileri
> ve workspace ayarları. Kapsam = `governance/` (proje-geneli araç kaydı).
> Eşi: [`tooling-plugins.md`](tooling-plugins.md) (Claude Code plugin envanteri).

**Son güncelleme:** 2026-06-02

---

## ⛔ ÖNCE — Editör eklentisi de yasakların üstünde değil (ADR 0005)

SAP/Fiori eklentileri **CAP** veya **standart-obje doğrudan-edit** akışı varsayabilir.
Biz **ABAP RAP + freestyle UI5** kullanıyoruz; SAP yazma işlemleri **yalnızca** kendi
`sap-adt` MCP / script + reviewer pre-flight (ADR 0006/0007) üzerinden gider. Bu yüzden:

- ⛔ **ABAP doğrudan-edit eklentisi (ör. "ABAP remote filesystem") KURULMAZ** —
  MCP/script disiplinini ve reviewer gate'ini bypass eder. Bilinçli karar.
- ✅ XML/i18n/manifest/JS/Python/Git **yardımcı** eklentileri serbest — bunlar SAP'ye
  yazmaz, sadece editör zekası verir.

---

## 1. Hızlı kurulum

VS Code workspace'i (`<PROJECT_ROOT>`) açınca sağ altta **"Bu workspace için
önerilen eklentiler"** bildirimi çıkar (`.vscode/extensions.json`'dan) → "Install All".

Veya terminalden tek tek:

```powershell
code --install-extension SAPOSS.vscode-ui5-language-assistant
code --install-extension SAPSE.sap-ux-fiori-tools-extension-pack
code --install-extension redhat.vscode-xml
code --install-extension redhat.vscode-yaml
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension dbaeumer.vscode-eslint
code --install-extension eamodio.gitlens
code --install-extension EditorConfig.EditorConfig
```

---

## 2. Eklentiler — ne işe yarar, bizde hangi iş

| Eklenti (ID) | Ne sağlar | Bizde hangi iş | Dikkat |
|---|---|---|---|
| **UI5 Language Assistant** (`SAPOSS.vscode-ui5-language-assistant`) | `.view.xml` + `manifest.json` autocomplete, kontrol/aggregation doğrulama, i18n key kontrolü, hover doküman | Freestyle UI5 ekranları (voyage, container_report, BOOKING) yazarken kontrol API'sini **editörde** doğrula. `ui5-mcp-server`'ı tamamlar | — |
| **SAP Fiori Tools – Extension Pack** (`SAPSE.sap-ux-fiori-tools-extension-pack`) | XML annotation dili, i18n editör, app yapısı görünümü, guided dev | i18n + XML view düzenleme yardımı | FE/CAP **generator**'larını ve "Application Wizard" CAP akışını **kullanma** (RAP+freestyle). Sadece XML/i18n araçları |
| **XML** (`redhat.vscode-xml`) | XML şema/format/validate | `manifest`-dışı XML, `.view.xml` format | — |
| **YAML** (`redhat.vscode-yaml`) | YAML şema/validate | `ui5.yaml`, `ui5-deploy.yaml`, frontmatter | — |
| **Python** (`ms-python.python`) | Python dil desteği, test, debug | `scripts/`, `mcp_servers/`, validator/populate geliştirme | — |
| **Pylance** (`ms-python.vscode-pylance`) | Tip kontrolü/IntelliSense (Pyright motoru) | `pyright-lsp` plugin'inin editör karşılığı; inline tip | Windows: konsol çıktısı ASCII-only kuralı geçerli |
| **ESLint** (`dbaeumer.vscode-eslint`) | JS/TS lint | UI5 controller (`.js`) kalite. `ui5-mcp` linter'ı tamamlar | — |
| **GitLens** (`eamodio.gitlens`) | blame, branch/PR görünürlüğü, geçmiş | **Çok-geliştiricili, modül-bazlı repo**: kim hangi paketi dokundu, satır geçmişi | — |
| **EditorConfig** (`EditorConfig.EditorConfig`) | Editör tutarlılığı (indent, EOL, charset) | Takım genelinde tutarlı dosya formatı | `.editorconfig` eklenirse aktif |
| **Claude Code** (`anthropic.claude-code`) | Bu araç | Zaten kullanımda | — |

---

## 3. Önerilen workspace ayarları (opsiyonel)

İstenirse `.vscode/settings.json` (commit'lenir) içine:

```jsonc
{
  // Python: Pyright/Pylance proje köküne baksin
  "python.languageServer": "Pylance",
  "python.analysis.typeCheckingMode": "basic",
  // XML/JSON dosyalarinda tutarli girinti
  "[xml]": { "editor.tabSize": 2 },
  "[json]": { "editor.tabSize": 2 },
  // i18n .properties dosyalari UTF-8
  "files.encoding": "utf8"
}
```

> Not: `.vscode/settings.json` kişisel tercih içeriyorsa `.gitignore`'a alınabilir;
> takım-ortak ayarlar commit'lenir.

---

## 4. Karar — "editörde bu iş için ne?"

| İş | Araç |
|---|---|
| UI5 XML view / manifest autocomplete | UI5 Language Assistant |
| i18n çeviri editörü | Fiori Tools (i18n) / UI5 Lang Assistant |
| UI5 control API kesin doğrulama / lint | `ui5-mcp-server` (Claude) + ESLint |
| Python tip/hata | Pylance (editör) + `pyright-lsp` (Claude) |
| Git geçmiş / multi-dev blame | GitLens |
| ABAP/CDS/RAP yaz-değiştir | **Yalnızca** `sap-adt` MCP/script (ADR 0005/0006/0007) — editör eklentisi DEĞİL |

> Yeni eklenti eklenirse: `.vscode/extensions.json`'a ID ekle → bu tabloya satır → gerekçe.
