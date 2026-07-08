---
adr: 0002
title: Paket adlandırma — ZSDxxx_CLC suffix standardı
status: accepted
date: 2026-05-14
deciders: <SAP_USER>
supersedes: —
superseded-by: —
---

# ADR 0002 — Paket Adlandırma (ZSDxxx_CLC Suffix)

## Bağlam

<PROJECT_NAME> projesinde paketler aşağıdaki gibi karışık şekilde adlandırılmıştı:
- `ZSD000_CLC`, `ZSD001_CLC`, `ZSD001_CLC`, `ZSD001_CLC`, `ZSD001_CLC`, `ZSD001_CLC` → suffix'li
- `ZSD001` → suffix'siz (istisna)
- `ZAI` → "default download" amaçlı (deprecated)

Tutarsız adlandırma:
- Validator regex'lerini zorlaştırıyor
- AI'ın paket isimlendirme refleksini bozuyor
- "Bu paket NTTDATA standardına uyuyor mu?" sorusunu cevaplamayı zorlaştırıyor

## Karar

**Tüm yeni ve mevcut paketler `_CLC` suffix kullanır:** `ZSD<NNN>_CLC`

- `<NNN>` = 3 haneli sıra numarası (NTTDATA naming standardı uyarınca)
- `_CLC` suffix kurum standardı (Classic — vs. ABAP Cloud)
- Lokal klasör adı = SAP'deki paket adı

### Mevcut istisnaların düzeltimi (Migration Adım 5)

- `ZSD001` → `ZSD001_CLC` (SAP tarafında rename, lokal klasör de aynı)
- `ZAI` → silinir (deprecated, `archive/ZAI_backup_2026-05-14/` altında sadece MPC yedek)

## Gerekçe

- **Tutarlılık:** Validator regex'i `^ZSD\d{3}_CLC$` tek pattern'e indirir
- **NTTDATA standardı:** `standards/01-naming.md` §3 (Package Naming Rules) ile uyumlu
- **AI refleksi:** Yeni paket önerirken AI default suffix'i kullanır

## Sonuçlar

- ✅ `scripts/validators/check_package_naming.py` tek regex ile tüm paketleri doğrular
- ✅ Yeni paket bootstrap'ı (`scripts/bootstrap_package.py`) default `_CLC` kullanır
- ❌ Tarihsel commit'lerde `ZSD001` referansları görünür (kaçınılmaz)

## Uygulama

Adım 5 (Migration ERP normalize)'te:
- `git mv ERP/ZSD001 ERP/ZSD001_CLC`
- `ERP/ZSD001_CLC/.rules.md` yazılır (prefix: `ZSD001_*`)
- `package-registry.md` güncellenir

## İlgili

- [`../package-registry.md`](../package-registry.md)
- [`../../standards/01-naming.md`](../../standards/01-naming.md)
- [`../../migration/audit.md`](../../migration/audit.md) — S3 cevabı
