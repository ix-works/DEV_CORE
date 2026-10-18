---
name: feedback_playwright-httpcredentials-sap-bsp-401-onden-basic
description: "Deploy edilmiş SAP BSP'yi Playwright ile gezerken context httpCredentials 401 verir — önden Authorization: Basic başlığı (extraHTTPHeaders) gerekir; 401 'kimlik yanlış' demek değil"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 8865df6b-2e94-44e8-8952-84b42fc53742
  modified: 2026-10-15T21:21:23.557Z
---

Doğrudan SAP BSP'ye (`/sap/bc/ui5_ui5/sap/<bsp>/index.html`) Playwright ile kimlikli tur atarken
`browser.newContext({ httpCredentials })` **401** ile düştü. Aynı kimlik `extraHTTPHeaders: { Authorization:
'Basic …' }` (önden gönderilen başlık) ile **200** verdi: index 200, `$metadata` 200, pageerror 0.

**Vaka (bir projede, 2026-10-15, BSP tarayıcı turu):** httpCredentials → 401; önden Basic → tur tamam. Kontrol grubu:
aynı kimlik Python `urllib` + Basic başlıkla statik varlıklarda 42/42 200.

**Why:** `httpCredentials` yalnız sunucu `WWW-Authenticate` meydan okumasıyla 401 döndüğünde kimliği yollar;
SAP ICF'in ilk yanıtı (login/SAML yönlendirme vb.) bu akışa uymazsa kimlik hiç gönderilmez. **Bunu kaynaktan
ölçmedim — mekanizma DOĞRULANMADI**; ölçülen yalnız iki yöntemin sonucu.

**How to apply:** SAP BSP/ICF'e Playwright turu → önden Basic başlık kullan; kimlik yalnız süreç env'inden,
diske/loga yazılmaz. 401 görünce "parola yanlış" deme; önce önden başlıkla dene. Lokal `fiori run` turu ayrı
yoldur (proxy kimliği `FIORI_TOOLS_USER/PASSWORD`).

Son-doğrulama: 2026-10-15
Applies-to: Playwright (node) + SAP S/4 BSP/ICF Basic auth
prior-art: yok (memory + core playbook/standards grep "httpCredentials" 2026-10-16 = 0)
