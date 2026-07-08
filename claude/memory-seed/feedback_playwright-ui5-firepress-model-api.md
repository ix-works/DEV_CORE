---
name: feedback_playwright-ui5-firepress-model-api
description: UI5 doğrulamada playwright .click() bazen tetiklemez → firePress/controller-invoke + model API ile sayısal doğrula
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a70ade51-38bb-4cb2-9aee-1e92823043a0
---

UI5 freestyle app'i playwright ile doğrularken: `playwright-cli click` (CSS id veya `getByRole`) bir sap.m.Button'a basıldığında **press handler'ı tetiklemeyebilir** (koordinat/overlay/DynamicPage-header artefaktı) — buton enabled+visible+press-bound+offsetParent olsa bile. Bu durumda fix'i "bozuk" sanma tuzağı oluşur (gerçekte çalışıyor).

**Why:** ZSD001 R6 shipment "Temizle" doğrulamasında `.click()` → grid temizlenmedi (items=5 kaldı) görünürken, `button.firePress()` ve `controller.onClearFilters()` doğrudan çağrısı → items 5→0 düzgün çalıştı. Yani fonksiyon + buton wiring doğruydu; `.click()` harness artefaktıydı.

**How to apply:** UI5 davranışını GÖZLE/`.click()` sonucuna değil **sayıyla** doğrula:
1. Buton wiring şüphesinde `sap.ui.core.Element.registry.get('<id>').firePress()` (gerçek press = kullanıcı tıklaması eşdeğeri) veya `getController().<handler>()` direkt-invoke.
2. State'i model API'den oku: `getModel('<name>').getData()` (DOM satır sayısı değil — sap.ui.table virtual-row DOM'u yanıltır).
3. Buton sağlığını kontrol et: `getEnabled()/getVisible()/mEventRegistry.press/getDomRef().offsetParent`.
4. Genişlik/hiza: `getBoundingClientRect()` ile px ölç (vision yok). [[feedback_dogrula-once-flag-spekulatif-blocker-yasak]] · [[feedback_done-tam-kapsam-dogrula]] · [[feedback_fe-merge-key-padding-ve-playwright-runtime-tespit]]
