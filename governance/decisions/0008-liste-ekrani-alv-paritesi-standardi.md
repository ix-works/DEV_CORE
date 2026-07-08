# ADR 0008 — Liste Ekranı ALV-Paritesi Standardı (<PROJECT_NAME> Geneli)

**Durum:** Kabul edildi (2026-05-19) · **REVİZE 2026-06-08 (tablo teknolojisi)**
**Karar veren:** Kullanıcı (Özgür) — açık talimat
**Bağlam katmanı:** L2 (standart) + L3 (playbook pattern) — T7

---

> ## ⚠️ REVİZE 2026-06-08 — Tablo teknolojisi GRID oldu (m.Table değil)
>
> Bu ADR'nin **üst-ilkesi geçerli**: her liste ekranı ALV-paritesi (sırala/filtrele/
> kolon göster-gizle/varyant/Excel) zorunlu, AI istemeden uygular. **ANCAK aşağıdaki
> gövde `sap.m.Table` + `columnmenu.Menu` + `infoToolbar` mekaniğini anlatıyor — bu
> ARTIK KANONİK DEĞİL.** 2026-06-08 (kullanıcı kararı, ZSD001 pilot onaylı): liste/
> rapor ekranları **`sap.ui.table.Table` (grid)** ile yapılır (yatay+sanal scroll,
> resize/reorder/freeze, **NATIVE** kolon-menüsü → columnmenu.Menu+infoToolbar
> GEREKMEZ). m.Table yalnız mobil-öncelikli/hücre-zengin istisna. Kanonik path
> **ZSD001 delivery_report / ZSD001 sales_order_report** (voyage DEĞİL).
> Güncel kural: **standards/03 §10.0** + playbook/ui-freestyle-odata-v2.md §E.
> Aşağıdaki m.Table gövdesini mobil-istisna referansı olarak okuyun.

## Bağlam

<PROJECT_NAME> freestyle SAPUI5 (OData V2 / RAP) uygulamalarında liste
ekranları kullanıcılar tarafından **SAP ALV gibi** kullanılıyor: alan
bazında sırala, alan bazında operatörlü filtrele (`= ≠ > < ≥ ≤ arası
içerir başlar biter`), kolon göster/gizle, **Excel'e aktar**. ORDER
(ZSD001) pilotunda bu yetenekler kanıtlandı (kullanıcı onayı 2026-05-19).

Klasik `sap.m.P13nDialog` yaklaşımı denendi ve **reddedildi**: P13nFilterPanel
eklenen koşulları model'e otomatik yazmıyor (event-sync kırılganlığı) →
"75 ile başlar" filtresi uygulanmıyordu. `sap.m.table.columnmenu.Menu`
(kolon başlığı menüsü) bu sınıfı kökten çözdü.

## Karar

**Bundan sonra <PROJECT_NAME>'de yapılan TÜM uygulamalarda** (sadece ZSD001
değil), her **liste ekranı** aşağıdaki ALV-paritesi bileşenini **zorunlu**
olarak içerir. AI bunu **kullanıcı ayrıca istemese bile** otomatik uygular:

1. **Kolon başlığı menüsü** (`sap.m.table.columnmenu.Menu`): başlığa tıkla
   → hızlı **Sırala** (↑/↓) + alana **operatörlü Filtre** (tip-duyarlı:
   metin Contains/EQ/StartsWith/EndsWith/NE; sayı·tarih EQ/NE/GT/GE/LT/LE/BT;
   bool EQ).
2. **Aktif filtre çubuğu** (tablo `infoToolbar`): hangi alan filtrelendi
   `Alan op değer ✕` + "Tümünü temizle"; filtreli kolon başlığı belirgin.
3. **Kolon göster/gizle** popover ("Kolonlar" butonu).
4. **Excel export** (`sap.ui.export.Spreadsheet`): gerçek `.xlsx`, OData
   binding'den **filtreye uyan TÜM satırlar** (ekrandaki sayfa değil);
   kapsam sorulur (**Görünür / Tüm kolonlar**).
5. State **localStorage**'da kalıcı (ALV varyant mantığı); scr1/selection
   filtreleriyle **AND**.

**Kanonik implementasyon (referans, kopyalanır):**
`ERP/SD/ZSD001_CLC/ui/voyage/webapp/util/TablePersonalizer.js`
+ `List.controller.js` (onColumns/onExportExcel wiring) + gerekli i18n
keyleri (`op.*`, `flt.*`, `exp.*`, `btn.cols/btn.excel`).

## Gerekçe

- Kullanıcı beklentisi ALV; tutarlılık tüm modüllerde aynı UX.
- `columnmenu.Menu` = SAP'nin modern, sağlam, freestyle-uyumlu yolu;
  P13nFilterPanel model-sync kırılganlığı yok.
- Reusable util → her ekran tek instance; ORDER/BOOKING/SHIPMENT
  tek satırla aynı yeteneği alır (sıfırdan patinaj yok — bkz. ADR 0006/T10).

## Sonuçlar

- `standards/03-coding-ui-fiori.md` §16 = bağlayıcı standart; §14
  checklist'e eklendi.
- `playbook/ui-freestyle-odata-v2.md` = kanıtlanmış pattern + §0 PRE-FLIGHT
  adımı; `checklists/ui-freestyle-creation.md` = zorunlu kontrol.
- Yeni liste ekranı PR'ı bu bileşen olmadan **eksik** sayılır.
- AI davranışı: yeni liste ekranı görevinde bu standardı **proaktif**
  uygular (feedback memory ile oturumlar arası kalıcı).

## İlgili

ADR 0003 (katman mimarisi) · ADR 0006 (reviewer/T10 kör nokta → checklist)
· `playbook/ui-freestyle-odata-v2.md` · `standards/03-coding-ui-fiori.md` §16
