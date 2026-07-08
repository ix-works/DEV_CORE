---
layer: governance
scope: project-wide
type: templates
last-updated: 2026-05-14
---

# Templates — Bootstrap Şablonları

Bu klasör yeni iş bileşenleri kurarken **kopyalanan ve doldurulan** şablonları içerir.

## Şablonlar

| Şablon | Kullanım |
|---|---|
| [`new-package/`](new-package/) | Yeni ZSDxxx_CLC paketi başlatılırken |

## Yeni Paket Bootstrap

```powershell
python scripts/bootstrap_package.py ZSD001_CLC --title "Sevkiyat Optimizasyon" --module SD
```

Script `templates/new-package/` içeriğini `ERP/<MODULE>/<PKG_FULL>/`'e kopyalar (örn. `ERP/SD/ZSD001_CLC/`), placeholder'ları doldurur:
- `{PKG}` → `ZSD001`
- `{PKG_FULL}` → `ZSD001_CLC`
- `{TITLE}` → `Sevkiyat Optimizasyon`
- `{MODULE}` → `SD`
- `{DATE}` → bugünün tarihi
- `{OWNER}` → git config user.name

Bootstrap sonrası `governance/package-registry.md` otomatik yeniden üretilir (`scripts/build_package_index.py`).

## Şablon Değişikliği

Şablonu değiştirmek için doğrudan dosyaları edit et. Mevcut paketler etkilenmez (sadece YENİ paketler yeni template'i alır). Mevcut paketleri güncellemek için manuel müdahale gerek.

## İlgili

- [`../scripts/bootstrap_package.py`](../scripts/) — Bootstrap script (Adım 6'da yazılacak)
- `governance/package-registry.md` *(proje reposunda)* — Paket listesi
