---
name: ui5-table-ctrl-a-testi-odakla-tik-sahte-negatif
description: "sap.ui.table Ctrl+A otomasyon testinde hücreye TIK + Ctrl+A olay üretmedi, hücreye focus() + Ctrl+A üretti — tık yolu sahte negatif verir"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  modified: 2026-10-18T11:20:15.558Z
---

sap.ui.table (UI5 1.120.23, `selectionMode=MultiToggle`) Ctrl+A davranışını tarayıcı otomasyonuyla test ederken klavye kısayolunu **içerik hücresine `locator.focus()` verdikten sonra** gönder. Hücreye **fare tıkı + Ctrl+A** yolunda canlı BSP'de hiç `rowSelectionChange` gelmedi (seçim değişmedi); aynı hücreye odak + Ctrl+A `selectAll=true` olayını üretti (`enableSelectAll="false"` iken de).

**Why:** Tık yoluyla koşulan test "Ctrl+A hiçbir şey yapmıyor" sonucunu verir ve geri-alma/koruma kodunun hiç sınanmamasına rağmen yeşil görünür. Ölçüm 2026-10-17, bir projede canlı BSP turu (deploy edilmiş freestyle uygulama). Tık yolunun neden olay üretmediği ÖLÇÜLMEDİ — mekanizma iddiası yok, yalnız gözlem.

**How to apply:** Ctrl+A/klavye kısayolu senaryolarında önce `focus()` yolunu koş; olay sayacı (ör. `rowSelectionChange` dinleyicisi) ile "olay geldi" kanıtını al. Olay 0 ise sonucu "kısayol etkisiz" diye değil "olay tetiklenmedi — test yolu doğrulanmadı" diye yaz. Kontrol grubu: aynı sayfada focus yolu olay üretiyor mu.

Son-doğrulama: 2026-10-17 · Applies-to: freestyle UI5 sap.ui.table, Playwright/otomasyon testi (tek sürüm ölçüldü: 1.120.23)
prior-art: yok (memory'de Ctrl+A/MultiToggle/focus araması 0)
