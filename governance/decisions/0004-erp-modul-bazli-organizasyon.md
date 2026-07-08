---
adr: 0004
title: ERP/ modül-bazlı klasör organizasyonu (ERP/<MODULE>/<PKG>/)
status: accepted
date: 2026-05-14
deciders: <SAP_USER>
supersedes: —
superseded-by: —
---

# ADR 0004 — ERP/ Modül-Bazlı Klasör Organizasyonu

## Bağlam

Migration sonrası (ADR 0003) `ERP/` klasörü altında doğrudan paket klasörleri vardı:
```
ERP/ZSD000_CLC/, ERP/ZSD001_CLC/, ..., ERP/ZSD001_CLC/
```

Şu ana kadar tüm geliştirme **SD (Sales & Distribution)** modülünde yapılmıştı. Ancak proje ilerledikçe diğer SAP modüllerinden de paket geleceği belli — MM (Materials Management), FI (Finance), QM (Quality Management), PM (Plant Maintenance), EWM (Extended Warehouse Management), CO (Controlling). Tüm paketleri tek seviyede tutmak:

- Görsel kalabalık (10+ paket sonrası flat listede arama zorlaşır)
- Modül bazlı sahip/yetki ayrımı kolaylaşmıyor
- Validator regex'i obje tipinden modül anlamı çıkaramıyor
- AI'nın "bu paket hangi modüle ait?" sorusunu sürekli `.rules.md` okuyarak çözmesi gerekiyor

## Karar

**ERP/ altında modül seviyesi alt klasör katmanı ekle:** `ERP/<MODULE>/<PKG_FULL>/`

### Yeni yapı

```
ERP/
├── README.md                ← modül indeks
├── SD/  (Sales & Distribution)
│   ├── ZSD000_CLC/
│   ├── ZSD001_CLC/
│   ├── ZSD001_CLC/
│   ├── ZSD001_CLC/
│   ├── ZSD001_CLC/
│   ├── ZSD001_CLC/
│   └── ZSD001_CLC/
├── MM/  (Materials Management — boş, .gitkeep ile tracked)
├── FI/  (Finance)
├── QM/  (Quality Management)
├── PM/  (Plant Maintenance)
├── EWM/ (Extended Warehouse Management)
└── CO/  (Controlling)
```

### Path Standardı

| Önce (ADR 0003) | Sonra (ADR 0004) |
|---|---|
| `ERP/ZSD001_CLC/` | `ERP/SD/ZSD001_CLC/` |
| `ERP/<PKG>/.rules.md` | `ERP/<MODULE>/<PKG>/.rules.md` |

### Boş Modüller

`MM/`, `FI/`, `QM/`, `PM/`, `EWM/`, `CO/` — şu an boş ama gelecekteki paketleri beklemek için `.gitkeep` ile tracked. Yeni modül gelirse `mkdir ERP/<MODULE>` ile eklenir.

## Gerekçe

- **Görsel netlik:** Modül bazlı gruplama sayesinde paket listesi okunabilir
- **Sahip/yetki ayrımı:** "MM modülünden sorumlu danışman" ↔ `ERP/MM/` net karşılık
- **NTTDATA naming uyumu:** Paket adı zaten modül prefix'i içeriyor (ZSD, ZMM, ZFI, ...) — klasör hiyerarşisi semantik ile doğal uyum
- **AI refleksi:** "MM altında çalış" denildiğinde AI `ERP/MM/` altına lokalize olur — modül-spesifik `.rules.md`'leri okuma gerekmez
- **Boş modül klasörleri:** Yeni modül başlatıldığında ekstra bootstrap gerekmez — `.gitkeep` zaten var

## Sonuçlar

- ✅ 159 dosyalık git mv (rename detection %100, history korundu)
- ✅ Validator'lar güncellendi: `check_package_*`, `check_object_in_correct_pkg`, `build_package_index`
- ✅ `bootstrap_package.py --module SD` artık `ERP/SD/<PKG>/` altına kurar
- ✅ `governance/package-registry.md` yeni format: "Modül | Paket | Prefix | Açıklama | Owner | Durum"
- ❌ Eski path referansları (commit'lerde, eski dosyalarda) artık geçersiz — git log/blame'de izlenir
- ❌ AGENTS.md, CLAUDE.md, README.md, ADR 0003 path'leri güncellenmeli (bu commit'te yapılıyor)

## Uygulama

Migration Adımı (Adım 9-11):

1. **Adım 9** (commit `61cc7bc4`) — Klasör reorganize: mkdir modüller, git mv 7 paket, .gitkeep boş modüllere, ERP/README.md
2. **Adım 10** (commit `52ac65f`) — Validator + bootstrap script güncellemeleri
3. **Adım 11** (bu commit) — ADR 0004 + AGENTS.md/CLAUDE.md/README.md path güncelleme

## İlgili

- `governance/package-registry.md` *(proje reposunda)*
- [`0003-layered-rule-architecture.md`](0003-layered-rule-architecture.md) — Önceki mimari kararı (L1-L4 katmanlar)
- `<source_root>/README.md` *(proje reposunda)* — Modül indeks
- [`../../standards/01-naming.md`](../../standards/01-naming.md) — NTTDATA modül prefix standardı
