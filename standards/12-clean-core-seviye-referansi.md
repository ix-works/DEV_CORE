---
applies_to: [s4_private]
layer: L2
scope: project-wide
applies-to: backend
version: 1.0
last-updated: 2026-10-12
status: active
---

# Clean Core — `cleancore_policy` × Seviye (A–D) × Teknik — Referans Tablosu

> **Ne:** `project.yaml`'daki `cleancore_policy` (`strict | balanced | classic`, yalnız `s4_private`)
> değerinin **seviye bazında ne anlama geldiğini** tek yerde toplar. Bugüne kadar bu anlam dağınıktı:
> politika ekseni [`../profiles/s4_private.yaml`](../profiles/s4_private.yaml) `policy_axis` (iki bayrak),
> seviye tanımı [`01-naming.md`](01-naming.md) §1 "Clean Core Extensibility Levels", yazma zinciri
> [`10-standart-veriye-yazma-api-secimi.md`](10-standart-veriye-yazma-api-secimi.md) "Profil ayarı".
> **Bu sayfa yeni kural KOYMAZ** — o üç kaynağı hizalar; çelişki olursa o kaynaklar üstündür.
>
> **Hücre sözlüğü (dürüstlük şartı):** `serbest` · `gerekçeyle` (TS'te yazılı gerekçe) · `kullanıcı onayı` ·
> `yasak` · **`ölçülmedi`** = matristen/dokümandan türetildi, canlı ya da araçla doğrulanmadı ·
> **`zorlama yok`** = hiçbir araç bu politikayı uygulamıyor (yalnız doküman + reviewer).
> ⛔ Boş ya da `ölçülmedi` hücre **"serbest" demek DEĞİLDİR** (kayıt yok ≠ izin var).

## 1. Seviyeler (std 01 §1'in özeti — tanım orada)

| Seviye | Kısa anlam | Tipik teknik |
|---|---|---|
| **A** | Released API + ABAP Cloud / yan uygulama | RAP, released CDS (`I_*`), released BO (EML) |
| **B** | SAP'nin klasik ABAP için önerdiği klasik API'ler | Klasik ABAP, released olmayan ama sınıflandırılmış klasik API'ler (BAPI vb.) |
| **C** | SAP iç objelerine bağımlılık; yükseltme öncesi kontrol ister | Released olmayan tablo/FM/sınıf okuması |
| **D** | Modifikasyon, önerilmeyen obje, örtük genişletme | Standart obje değişikliği, implicit enhancement |

## 2. Politika × seviye

| Politika | A | B | C | D | Kaynak / durum |
|---|---|---|---|---|---|
| `strict` | serbest (tercih) | gerekçeyle — klasik Dynpro **yasak** (`classic_dynpro: forbidden_by_policy`) | **yasak** (`released_apis_only: true`) | **yasak** | profil matrisi · **ölçülmedi** · **zorlama yok** |
| `balanced` | serbest (tercih) | serbest | gerekçeyle — `check_released_objects` WARNING verir (yalnız tablo→CDS ailesi), ATC "Usage of APIs" otoritedir | **yasak** | matris + std 10 ADIM 1 bir senaryoda ölçüldü; C hücresinin geri kalanı **ölçülmedi** |
| `classic` | serbest (RAP tercih baskısı yok — `rap: available`) | serbest | gerekçeyle | **yasak** | profil matrisi · **ölçülmedi** · **zorlama yok** |

**D sütunu her politikada `yasak`tır** ve bu politika ekseninden değil **KESİN YASAKLAR A** kategorisinden
(ADR 0005) gelir: standart objeyi değiştirmek hiçbir politika değeriyle açılmaz. Append/alan adı AI
tarafından önerilmez.

## 3. Teknik × politika (sık sorulanlar)

| Teknik | `strict` | `balanced` | `classic` | Not |
|---|---|---|---|---|
| Standart tabloyu doğrudan **okuma** (`SELECT` VBAK…) | yasak (C) | gerekçeyle; released halef önerilir | gerekçeyle | ADR 0005-B okumayı yasaklamaz. Halef `#CHECK` taşıyorsa geçiş fail-open üretebilir (`playbook/adt-cds.md` CDS-DCL-02) |
| Standart veriye **yazma** | std 10 zinciri (4 kapalı) | std 10 tam zincir | std 10 tam zincir | Doğrudan SQL her politikada **yasak** (ADR 0005-B) |
| Klasik rapor / Dynpro / ALV | Dynpro yasak; rapor ölçülmedi | serbest (std 06, ADR 0012) | serbest | — |
| RAP / released CDS | tercih | tercih | serbest | — |
| SEGW OData | ölçülmedi | serbest | serbest | std 02 legacy statüsünde |

⚠ Bu tablonun `strict` ve `classic` sütunlarının **tamamı** profil matrisinden türetilmiştir (**ölçülmedi**,
**zorlama yok**); `balanced` sütununda canlı ölçülmüş tek hücre std 10 ADIM 1'dir.

## 4. Kullanım kuralı

- FS/TS'te Clean Core gerekçesi yazılırken **seviye harfi + politika** birlikte anılır ("C seviyesi okuma,
  `balanced` — gerekçe: released halefi yok/`#CHECK` riski").
- Bir hücreyi `ölçülmedi`den çıkarmak **canlı ölçüm** ister (ATC "Usage of APIs" ya da aktivasyon) —
  matris rehberdir, kanıt değildir (CLAUDE.core §2).
- Bu tablo bir gate'in girdisi değildir; `cleancore_policy`'yi okuyan bir doğrulayıcı bugün **yoktur**
  (2026-10-12 tarama: `scripts/` + `mcp_servers/` altında politika değerini okuyan kod 0 — yalnız
  `init_project` şablonu ve `parity_probe` alan listesi). Bunu değiştirmek ADR 0019 kararıdır.

prior-art: kısmi — `profiles/s4_private.yaml` `policy_axis` · std 01 §1 · std 10 "Profil ayarı" (bu sayfa üçünü hizalar; dış bir pazardaki profil tablosu fikrinden uyarlanmıştır, karar kümesi bizim).
