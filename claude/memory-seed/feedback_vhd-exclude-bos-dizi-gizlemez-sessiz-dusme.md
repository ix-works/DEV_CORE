---
name: vhd-exclude-bos-dizi-gizlemez-sessiz-dusme
description: "UI5 ValueHelpDialog setExcludeRangeOperations([]) 'hariç tut' seçeneğini GİZLEMEZ (1.120.23 ölçüldü); seçim kurucu exclude token'ı `return` ile atlarsa dışlanan değer rapora girer, uyarı yok — reddet, sessizce atma"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 558cf803-e863-47bd-a743-3e15bcb13a3b
  modified: 2026-10-15T12:03:50.868Z
---

`sap.ui.comp.valuehelpdialog.ValueHelpDialog` üzerinde `setExcludeRangeOperations([], "string")` çağrısı "Koşulları tanımla" sekmesindeki **Hariç tut → eşit değildir** seçeneğini KALDIRMADI (UI5 1.120.23, canlı ölçüm). Kullanıcı hariç koşul girince MultiInput'ta `!(=<değer>)` token'ı görünür (`{exclude:true, operation:"EQ"}`); seçim kurucu `if (r.exclude) { return; }` ile onu atladığı için backend'e yalnız dahil aralıklar gider ⇒ **dışlanan değer sonuçta durur, hata/uyarı yok** (finansal raporda sessiz yanlış sonuç). Kod "hariç sunulmaz" kuralını uygulamış gibi görünür; statik okuma ve FE'nin kendi tarayıcı turu kaçırdı, taze bug-gate canlı uçtan uca ölçümle yakaladı.

**Why:** Bir projede, 2026-10-15 FE bug-gate (BLOCKER) — 5 MultiInput aynı VH yolundan geçiyordu.

**How to apply:** Backend'in desteklemediği bir range türünü (exclude, desteklenmeyen operatör) asla sessizce düşürme — VH ok handler'ında ya da seçim doğrulamasında **reddet + mesaj**. "Gizledim" iddiasını UI5 API'sinin adına değil tarayıcıda operatör listesine bakarak ölç. Seçim özeti çubuğu da gönderilen kriteri değil, ekrandaki token'ları göstermeli ki fark görünür olsun.

Son-doğrulama: 2026-10-15 — canlı :8094, DEV 100, UI5 1.120.23
Applies-to: freestyle UI5 + sap.ui.comp ValueHelpDialog filtre ekranları (tüm profiller)
prior-art: yok (memory + core playbook/standards `setExcludeRangeOperations` 0 isabet); ilgili [[rapor-filtre-select-options-contains-standardi]]. Kardeş uygulama taraması yazıldığı tarihte ertelenmiş iş olarak açıktı.
