---
name: feedback_numeric-input-no-type-number
description: "Düzenlenebilir miktar/sayı Input'unda type=Number KULLANMA; type=Text + liveChange rakam-filtresi (ok-tuşu artırma + grid satır-gezme tuzağı)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d2889f86-35d9-41c7-b431-b18fba6cedae
---

Tablo/grid içindeki düzenlenebilir **sayısal Input** (miktar, sevk miktarı vb.) için **`sap.m.Input type="Number"` KULLANMA** (kullanıcı kuralı, 2026-06-12, ZSD001 picker).

**Why:** HTML `<input type="number">` (1) yukarı/aşağı **ok tuşuyla değeri artırır/azaltır** → kullanıcı satır-gezmek için ok'a basınca miktar değişir (yanıltıcı, sessiz veri bozulması); (2) spinner okları yer kaplar; (3) grid/tablo satırları arası ok-tuşu navigasyonunu bozar. Kullanıcı: "text olmaz, abc girilebiliyor; başka çözüm". Number'ın ok-artırmasını UI5'te kapatan temiz property YOK.

**How to apply:** `type="Text"` + **`liveChange` ile canlı rakam filtresi**. Generic handler (binding path'inden bağımsız, value binding'i neyse onu günceller):
```js
onNumericLiveChange: function (oEvent) {
    var oInput = oEvent.getSource();
    var sVal = oEvent.getParameter("value");
    if (sVal === null || sVal === undefined) { return; }
    var sClean = sVal.replace(/[^0-9.,]/g, "").replace(/,/g, ".");   // sadece rakam + ondalık
    var parts = sClean.split(".");
    if (parts.length > 2) { sClean = parts[0] + "." + parts.slice(1).join(""); }   // tek ondalık
    if (sClean !== sVal) { oInput.setValue(sClean); var oB = oInput.getBinding("value"); if (oB) { oB.setValue(sClean); } }
}
```
View: `<Input type="Text" change=".onItemQtyChange" liveChange=".onNumericLiveChange" .../>`. Böylece harf engellenir, ok-tuşu değeri değiştirmez, ok'la satır-gezme geri gelir. `change`'de cap/validasyon yine parseFloat ile. **Uygulandı:** ZSD001 picker + SE kalem tabloları (Create+Change), ZSD001 sipariş kalem tabloları (Create+Change, BaseOrder.onNumericLiveChange). Standart: `standards/03-coding-ui-fiori.md`. İlişkili: [[feedback_grid-liste-standardi]].
