---
name: feedback_ui-local-run-paket-workspace-node-modules
description: "UI5 uygulamasını lokal çalıştırırken app dizininde npm install YAPMA — paketin ui/ workspace'inden başlat"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e2be199b-d6c4-4f86-89d4-092318c5ddbf
---

UI5 uygulaması lokal çalıştırılırken **uygulama dizininde `npm install` YASAK**. Bağımlılıklar
paketin `ui/` workspace'inde (kök `node_modules`) yaşar; app içinde install etmek ikinci bir
`node_modules` yaratır ve sürüm çakışmasıyla sessiz kırılma üretir.

**Why:** Paket `ui/` dizini bir npm workspace'idir. App-içi install workspace çözümlemesini
bozar; `ui5 serve` bazen çalışır, bazen bayat/çakışan sürümü yükler → teşhisi zor hatalar.

**How to apply:** `<source_root>/<MODULE>/<PKG>/ui/` dizininden `npm run start-noflp`
(index.html; `flp.html` değil). `FIORI_TOOLS_*` kimlik değişkenleri `.conn_adt`'den okunur —
elle girme, uydurma. Popup ısrar ediyorsa [[feedback_grid-ui-local-run-popup]] karar ağacına
bak (flexibility-services=[] → hâlâ geliyorsa HESAP KİLİDİ, SU01).

> **Not (2026-07-10 memory denetimi):** Bu dosyanın gövdesi kaybolmuştu; `MEMORY.md`
> ölü linke işaret ediyordu. İçerik indeks satırından + [[feedback_ui-deploy-noninteractive]]
> ve [[feedback_grid-ui-local-run-popup]] bağlamından yeniden kuruldu. Orijinal ayrıntı
> (varsa) eksik olabilir.
