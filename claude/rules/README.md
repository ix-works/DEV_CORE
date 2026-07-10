---
globs: __asla-eslesmez__/*.none
---

# `claude/rules/` — L1b: glob-tetiklemeli davranış kuralları

Bu dizindeki her `.md`, frontmatter'ındaki `globs:` desenine uyan bir dosya okunduğunda
context'e **otomatik** yüklenir. Startup maliyeti sıfırdır (yüklenmezler), tetiklenmeleri
model kararına bağlı değildir.

## Neden var (2026-07-10 memory/recall denetimi)

`AGENTS.md` hiçbir oturumda yüklenmiyordu — Claude Code `CLAUDE.md` okur, `AGENTS.md` okumaz.
356 satırlık davranış katmanı, düz bir markdown link'in arkasında sessizce ölüydü. Çözüm:
her-oturum gerekli olan → `CLAUDE.core.md §1.1`; **iş-anına özgü olan → burası.**

## Yazım kuralları — ÖNEMLİ TUZAK

**`globs:` kullan, `paths:` KULLANMA.** Resmî doküman `paths:` (YAML listesi, tırnaklı) tarif
eder ama o biçim **sessizce çalışmaz** — hata vermez, kural hiç yüklenmez
(anthropics/claude-code issue #17204, "closed as not planned"). Çalışan biçim:

```yaml
---
globs: **/*.abap, **/*.ddls
---
```
tırnaksız, virgülle ayrılmış, tek satır.

`globs:` **olmayan** kural koşulsuz yüklenir (her oturum, `CLAUDE.md` gibi) — bunu bilerek yap.

## Compaction uyarısı

`globs:`-scoped kurallar `/compact` sonrası **kaybolur**; eşleşen dosya tekrar okununca geri
gelirler. Bu yüzden **anayasa (KESİN YASAKLAR) buraya konmaz** — o, kök `CLAUDE.md`'ye fiziksel
damgalıdır (ADR 0021) ve compaction'dan sağ çıkan tek yerdir.

## Bu dosya neden `globs: __asla-eslesmez__`?

Frontmatter'sız bırakılırsa README her oturum context'e girerdi. Eşleşmeyen bir glob ile
etkisiz hâle getirildi — içeriği insan içindir.
