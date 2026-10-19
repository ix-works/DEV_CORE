---
applies_to: [s4_private]
layer: L3
type: reference
module: SD
status: active
purpose: SD SPRO / customizing referansı (doküman tipleri, kopya kontrol, teslimat, çıktı)
---

# SD — SPRO / Customizing (referans)

> Customizing okuma/farkındalık. Z geliştirme bu config'e dayanır; değiştirme = danışman/operatör.

## Satış
| IMG / TX | Konu |
|---|---|
| VOV8 | Satış doküman tipleri (order types) |
| VOV7 | Kalem kategorileri (item categories) |
| VOV6 | Schedule line kategorileri |
| VOV4 | Kalem kategori belirleme |
| V/08, V/06 | Fiyatlandırma prosedürü / koşul tipleri |

## Kopya kontrol (copy control)
| TX | Akış |
|---|---|
| VTAA | SO → SO |
| VTLA | SO → Delivery |
| VTFL | Delivery → Billing |
| VTFA | SO → Billing |

## Teslimat / Shipping
| IMG / TX | Konu |
|---|---|
| 0VLK | Teslimat tipleri |
| 0VLP | Teslimat kalem kategorileri |
| Shipping point determination | Sevkiyat noktası belirleme |
| Route determination | Rota belirleme |
| LE-TRA (VT) | Taşıma/shipment config |

## Çıktı / Statutory
| Konu | Not |
|---|---|
| NACE | Output determination |
| SAP Document Compliance | Yerel yasal belgeler (ör. Türkiye e-İrsaliye / e-Fatura) |

## Varyant konfigürasyonu — aynı belgede kalemi konfigürasyonuyla devretme (Mill hızlı giriş)

> **İhtiyaç:** VA21/VA22'de bir kalemin (örn. 10) karakteristik değerlerini **aynı belgedeki**
> başka bir kaleme (20) taşımak. **Kopya kontrol (VTAA) DEĞİLDİR** — VTAA belge→belge kopyalar.
> Karşılığı Mill Products'ın **karakteristik hızlı girişi + genel/yerel kalem** işlevidir
> (`VBAP-MILL_SE_GPOSN` "Genel kalem"). ⚠ IMG'de "kopyala/copy" kelimesiyle aranırsa BULUNMAZ —
> düğüm adı "Satış belgelerinde kalem konfigürasyonu".

| Adım | Nerede | Ne |
|---|---|---|
| 1 | IMG `ISMP/SAPMP/SD_TVAK1` (TVAK) | `/SAPMP/CEACT` "Karakteristik hızlı girişi etkin" = X (mantığı açar). Mevcut kaleme sonradan aktarım ("Aktarım" düğmesi, `/SAPMP/PROP`) için `/SAPMP/PDACT` = X; `PPROT` / `PUSER` / `PAUSW` isteğe bağlı |
| 2 ⭐ | **VOV8 → belge türü → "Genel bakış ekranı işlev kodu"** (`TVAK-UEVOR`) | **`MILL_SE_UE`** — "Karakteristiklere genel bakış" ekranını (SAPMV45A 4001 + alt ekran 4434) açar; "Genel kalem" sütunu YALNIZ bu ekrandadır, standart kalem genel bakışında YOKTUR |
| 3 | Ekranda "kapsam" listesi | "Tüm kalemler" — "Yalnız genel" sütunu gizler, "Genel+yerel" alanı kilitler |
| ops. | IMG `ISMP/SAPMP/V_VBMUEH` (`/SAPMP/VBMUEH`) · `ISMP/SAPMP/SD_MUEBS` (SM34 `/SAPMP/SD_MUEBERSICHT` → VBMUE/VBMUET/VBMUEZ) · kullanıcı parametresi `VAM` | Ekranda gösterilecek karakteristik DEĞER sütunları (≤10) — "Genel kalem" sütununu ETKİLEMEZ |

- **Devir:** yeni kalem yaratılırken "Genel kalem" alanına kaynak kalem no yazılır → otomatik; mevcut
  kalem için genel kalem işaretlenip "Aktarım". Yalnız **aynı adlı** karakteristikler devredilir.
- **⛔ Tuzak (ölçüldü, s4_private 2025, tek sistem):** `CEACT`…`PAUSW` = X iken alan AÇILMADI;
  `TVAK-UEVOR = MILL_SE_UE` girilince açıldı (kullanıcı GUI testi). Kod okuması yanıltır:
  `MILL_SE_ACTIVATE` yalnız `CEACT`'a bakar ve "kapı bu" sanılır — oysa ekrana ulaşan yol
  belge türünün genel bakış işlev kodudur. "Uyarlama tamam ama açılmıyor" denirse önce `UEVOR`'a bak.
- Business function gerekmedi (ölçülen sistemde `/SAPMP/*` switch'leri zaten açıktı — başka sistemde
  SFW5'te canlı teyit et). Okuma tarafı (belgedeki değerler): `VBAP-CUOBJ → IBINOWN → IBIN → IBINVALUES`;
  yerel kalem kendi `CUOBJ`'unu taşır.
- prior-art: yok (2026-10-19 `path=core` araması: MILL_SE / LO-VC / IBINVALUES → 0 dosya).
