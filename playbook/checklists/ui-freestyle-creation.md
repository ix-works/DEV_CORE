---
applies_to: [s4_private]
---
# Checklist — Freestyle UI5 (OData V2 / RAP tüketen) Oluşturma

> **Manuel checklist.** Freestyle UI = SAP-yazması DEĞİL → otomatik
> `run_review.py` gate'i YOK (reviewer UI'ı yakalayamaz = bilinen kör nokta,
> ADR 0006 / T10). Bu yüzden yeni bir freestyle UI'a başlarken / PR öncesi
> bu liste **elle** geçilir. Amaç: ORDER'deki UI patinajını ORDER ve
> sonraki uygulamalarda **tekrarlamamak**.
>
> **İlgili:** [`../ui-freestyle-odata-v2.md`](../ui-freestyle-odata-v2.md) ·
> **Standart:** [`../../standards/03-coding-ui-fiori.md`](../../standards/03-coding-ui-fiori.md)

---

## Faz 1 — İskelet (kod yazmadan)

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| UI-BOOT-01 | `index.html` UI5 sürümü **pinli** + `data-sap-ui-language="tr"` | BLOCKER | §A1 |
| UI-BOOT-02 | manifest 3 model: `i18n` + `""` (V2: TwoWay, useBatch:false, Inline) + `ui` (JSON `{busy,filter:{}}`); Component.js deps tam | BLOCKER | §A2 |
| UI-BOOT-03 | i18n TR-first; tüm label/buton/mesaj key'leri TR (tahmin değil) | BLOCKER | ADR 0005 D |
| UI-BOOT-04 | Paket `ui/` = npm WORKSPACE kökü (`workspaces:["*"]` + ortak devDeps hoist, ilk app'ten itibaren çoklu-varsay); yeni app **minimal** package.json (devDeps yok→inherit); `npm install` **`ui/` KÖKÜNDE** (app dizininde DEĞİL); per-app `package-lock.json` YOK | WARNING | std/03 §2.0 |

## Faz 2 — Mimari karar (EN KRİTİK — patinaj kaynağı)

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| UI-ARCH-01 | Editable **child grid** (composition satır ekle/sil/düzenle) var mı? VARSA → **JSON edit-buffer** mimarisi kuruldu mu? (load=`read $expand`→buffer, save=explicit) | BLOCKER | §B3 |
| UI-ARCH-02 | Editable child grid'i V2 nav-binding + `createEntry` ile yapmaya **çalışılmadı** (yasak — patinaj) | BLOCKER | §B2/B3 |
| UI-ARCH-03 | Save akışı şablonu (§B kutusu) uygulandı: `isNew?deepCreate:(headerMERGE+child C/U/D)` → **_runSeq SIRALI** → tek `_ok/_err` | BLOCKER | §B kutu |
| UI-ARCH-04 | `hasPendingChanges()` ön-gate **kullanılmadı** | WARNING | §B7 |

## Faz 3 — Save davranışı

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| UI-SAVE-01 | `createEntry` deep nav path'e kullanılmadı; `create/update/remove` (anında) tercih edildi | BLOCKER | §B2 |
| UI-SAVE-02 | Mevcut (değişmiş) child satırları için de **UPDATE** gönderiliyor (sadece create/delete değil); child KEY alanı UPDATE gövdesinde yok | BLOCKER | §B5 |
| UI-SAVE-03 | RAP BO op'ları **SIRALI** (paralel `jQuery.when` değil) — lock çakışması yok | BLOCKER | §B6 |
| UI-SAVE-04 | Başarı → `MessageToast` + `model.refresh()` + navTo; hata → `MessageBox` + `_extractMsg` | WARNING | §B kutu |

## Faz 4 — Binding / kontrol tipleri

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| UI-BIND-01 | Her numeric/date OData binding'inde `sap.ui.model.odata.type.*` belirtilmiş | BLOCKER | §D1 |
| UI-BIND-02 | CHAR1 bayrak alanları CheckBox + expression display + `select` handler ('X'/'') | WARNING | §D2 |
| UI-BIND-03 | Composition nav property `to_<assoc>` (V2 SADL prefix) kullanıldı | BLOCKER | §B1 |

## Faz 5 — Value-help & kişiselleştirme

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| UI-VH-01 | Value-help confirm'de değer **kontrole DİREKT** yazılıyor (setValue+setDescription), sadece binding'e güvenilmiyor | BLOCKER | §C1 |
| UI-VH-02 | Value-helped alanlarda kod+ad: `<X>Name` CDS projeksiyonda expose + `description` bind | WARNING | §C2 |
| UI-PERSO-01 | **Liste ekranı = ZORUNLU ALV standardı (ADR 0008):** kanonik `TablePersonalizer.js` kopyalandı → kolon-başlığı sort/filtre + aktif filtre çubuğu + **Kolonlar göster/gizle** + Excel (kapsam sorulu). `P13nDialog`/`TablePersoController` KULLANILMADI. Sıfırdan filtre/sort/export YAZILMADI | BLOCKER | §E · ADR 0008 |

## Faz 6 — Kapanış

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| UI-FIN-01 | Benign konsol uyarıları (preload404/favicon/locale) hata sanılıp kovalanmadı | INFO | §A3 |
| UI-FIN-02 | Sayfa başlığındaki anahtar form alanı olarak tekrarlanmadı; form compact | INFO | §F1/F2 |
| UI-FIN-03 | Yaşanan yeni UI patinajı varsa `ui-freestyle-odata-v2.md`'ye eklendi (T1/T2) | WARNING | T1/T2 |
| UI-FIN-04 | **BSP deploy: standart-dışı dosya tipi YOK** (`.svg`/`.woff` vb.). SAP BSP repo `.UI5RepositoryTextFiles`/`BinaryFiles`'de olmayan uzantıyı "Type of file X is unknown" → Application Index **400** ile REDDEDER. **Lokal run'da görünmez** (server serve eder), yalnız `fiori deploy` BSP upload'ta çıkar. Logo/ikon = **inline SVG** (HTML'e göm) veya base64; ayrı `.svg` dosyası app'e koyup deploy etme. | BLOCKER | ZSD001_BOOKING 2026-06-30 |

---

**Kullanım:** Yeni freestyle UI → Faz 1-2'yi **kod yazmadan**, 3-5'i geliştirme
sırasında, 6'yı PR/kapanış öncesi geç. BLOCKER varsa düzeltmeden devam etme.
