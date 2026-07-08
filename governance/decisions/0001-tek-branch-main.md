---
adr: 0001
title: Tek branch — sadece main
status: accepted (revize 2026-07-08 — ADR 0020)
date: 2026-04-29
deciders: <SAP_USER>, NTT DATA TR ekibi
supersedes: —
superseded-by: —
---

# ADR 0001 — Tek Branch (Sadece `main`)

> **REVİZE (2026-07-08, ADR 0020 canlı-çekirdek geçişi):** Karar özü korunur — tek
> UZUN-YAŞAYAN branch `main`'dir. Ancak `main` artık doğrudan-push'a KAPALIDIR (GitHub
> ruleset `main-pr-required`) → değişiklikler **kısa-ömürlü branch + PR + CI** ile girer,
> merge sonrası branch otomatik silinir. "Hiç branch açılmaz" hükmü
> [AGENTS.md §1](../../AGENTS.md)'deki güncel kural setine devredildi. Worktree yalnız
> `team_setup.py --provision-worktree` ile (D16 provizyonu).

## Bağlam

`<PROJECT_REPO_URL>` reposu birden fazla AI agent (Claude Code, OpenCode) ve insan geliştirici tarafından kullanılıyor. Branch karmaşası, worktree çoğalması, merge conflict riski ve agent'ların kendi başlarına branch açma alışkanlığı ciddi sorun oluşturuyordu.

## Karar

**Bu repoda sadece `main` branch kullanılır.** Hiçbir agent veya geliştirici yeni branch açmaz, worktree yaratmaz.

### Yasaklar

- `git checkout -b <name>`, `git branch <name>`, `git switch -c <name>` → ❌
- `git worktree add ...` veya Claude Code'un EnterWorktree tool'u → ❌
- `main-backup-*` branch'lerine dokunma → ❌ (güvenlik yedeği)
- `git push --force`, `--force-with-lease`, `--no-verify` → ❌ (kullanıcı açıkça istemedikçe)

### Zorunluluklar

- Tüm iş `<PROJECT_ROOT>` ana klasöründe yapılır
- Push öncesi kullanıcı onayı şart
- Pre-push hook bypass edilmez

## Gerekçe

- **Karmaşa azaltma:** Birden fazla agent senkronize çalışıyor; branch çoğalsa merge yükü patlar
- **Geri alınamaz işlemlerin kontrolü:** Force push, branch silme gibi geri alınamaz işlemler tek noktada (kullanıcı izniyle)
- **Yedek garantisi:** `main-backup-*` branch'leri tarihsel snapshot — silinmesi tehlike
- **Hook koruması:** Pre-push hook bir güvenlik katmanı; bypass etmek prensibi zedeler

## Sonuçlar

- ✅ Tek doğruluk kaynağı
- ✅ Agent davranışı tahmin edilebilir
- ❌ Paralel feature geliştirme branch'siz olamaz → workaround: feature flag veya zamanlı koordinasyon
- ❌ Roll-back için yine main'e revert/reset kullanılır (zor ama netlik için kabul)

## Uygulama

Bu karar AGENTS.md'ye yazıldı (2026-04-29). Adım 7'de (CLAUDE.md ince loader) referans verilecek.

## İlgili

- `governance/package-registry.md` *(proje reposunda)*
- [`../../AGENTS.md`](../../AGENTS.md) — Git workflow zorunlu kuralları
