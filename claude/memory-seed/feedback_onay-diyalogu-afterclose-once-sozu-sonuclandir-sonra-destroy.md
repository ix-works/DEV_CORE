---
name: feedback_onay-diyalogu-afterclose-once-sozu-sonuclandir-sonra-destroy
description: "Söz (Promise) döndüren onay diyalogu yardımcısında afterClose önce sözü sonuçlandırır, SONRA destroy eder; tersi Esc'te TypeError atar, söz hiç sonuçlanmaz, meşgul bayrakları kalıcı kilitlenir"
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

Onay diyalogunu Promise'e saran ortak bir yardımcı düşün (`Onay.sor()` → `true/false`). Bu yardımcıda `afterClose` içinde **önce `destroy()`, sonra `bitir(false)`** yazılırsa şu olur:
1. Esc ile (ya da düğmesiz) kapanış yolunda `bitir` diyaloğu kapatmaya çalışır.
2. Diyalog zaten yok edildiği için `getOpenState` TypeError atar.
3. Söz **hiç sonuçlanmaz** ve çağıranın `finally` bloğu koşmaz.
4. Çağıranın tuttuğu `_onayAcik` / `_deleting` gibi meşgul bayrakları açık kalır ve ekran sayfa yenilenene kadar kilitlenir.

Düğmeyle kapanış yolu çalıştığı için bu hata kolay görülmez.

**Why:** Bir UI5 ayar uygulamasında bug-gate bunu BLOCKER olarak buldu. Esc ile kapatma senaryoları, kod eski sıralamaya döndürülünce kırmızıya düştü (mutasyonla kanıtlandı). Düzeltmeden sonra üç senaryonun üçü de yeşil oldu. (2026-11-12)

**How to apply:**
- `bitir(b)` tek girişli olmalı: önce sözü sonuçlandırır (ikinci çağrıda hiçbir şey yapmaz), sonra `close()`'u yalnız `!oDlg.bIsDestroyed && oDlg.isOpen()` doğruysa çağırır.
- `afterClose` içinde sıra `bitir(false); oDlg.destroy();` olmalı.
- Her diyalog yardımcısı için üç kapanış yolunun testi yazılır: düğme, Esc ve programla kapatma. Her yolda sözün tam olarak bir kez sonuçlandığı ve meşgul bayrağının indiği ölçülür.

Son-doğrulama: 2026-11-12
Applies-to: freestyle UI5 (sap.m.Dialog / MessageBox), Promise sarmalı onay yardımcıları
