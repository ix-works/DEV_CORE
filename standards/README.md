---
applies_to: [s4_private]
layer: L2
scope: project-wide
type: index
last-updated: 2026-05-14
---

# Standards — Kurumsal & Proje Standartları

Bu klasör **L2 katman** dosyaları içerir: stabil, değişme sıklığı düşük, tüm projelere uygulanan kurallar. Detay için kural katmanları → [`../CLAUDE.core.md`](../CLAUDE.core.md).

## Dosyalar

| Dosya | Kapsam | Konu |
|---|---|---|
| [`01-naming.md`](01-naming.md) | both (backend + UI) | Package, WRICEF, namespace, obje adlandırma kuralları (NTTDATA/TR rehberi) |
| [`02-coding-backend.md`](02-coding-backend.md) | backend | **Klasik track:** OData v2 (SEGW), RFC/BAPI, CDS, Fiori Elements, performans, security |
| [`03-coding-ui-fiori.md`](03-coding-ui-fiori.md) | ui | Fiori UI5 proje yapısı, manifest, controller, OData binding, CSS, deploy (ui5-deploy.yaml) |
| [`04-documentation-fs-ts.md`](04-documentation-fs-ts.md) | both | FS ve TS şablonları, versiyon kontrolü, onay süreci |
| [`05-coding-rap.md`](05-coding-rap.md) | backend | **RAP track:** view entity katmanlama, BDEF (managed/unmanaged), service definition/binding/publish, ADR 0005 RAP yüzeyi (02'nin alternatifi, all-or-nothing) |

## Ne Zaman Buraya Yazılır?

Aşağıdaki tip kararlar L2 katmana yazılır:
- Yeni bir kurumsal standart netleşti (örn. "Tüm proxyler `cl_http_client` ile çağrılır")
- Naming convention'a yeni bir kategori eklendi
- FS/TS şablonu güncellendi (zorunlu yeni alan)
- UI/backend pattern'i kurum genelinde stabilize oldu

L3 ile karışıklık: **"nasıl yaparım" operasyonel ise L3 (`playbook/`), "ne kural" stabil ise L2 (burası).**

## Frontmatter

Her dosya zorunlu frontmatter taşır:
```yaml
---
layer: L2
scope: project-wide
applies-to: backend|ui|both
version: <semver>
last-updated: <YYYY-MM-DD>
status: active|deprecated
---
```

## İlgili

- [`../playbook/`](../playbook/) — L3 operasyonel pattern bankası
- [`../CLAUDE.core.md`](../CLAUDE.core.md) — Katman özetleri + session protokolü
- [`../AGENTS.md`](../AGENTS.md) — L1 agent davranış kuralları
