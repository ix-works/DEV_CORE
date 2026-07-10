# `claude/rules/` — L1b: dosya-tetiklemeli davranış kuralları

> **Bu dosya `claude/rules/` dizininin DIŞINDADIR ve bu kasıtlıdır.** O dizindeki her `.md`
> Claude Code tarafından talimat dosyası sayılır; içeriği insan için olan bir README orada
> dursaydı **her oturum context'e girerdi.** Nitekim 2026-07-10'a kadar öyle oldu —
> "eşleşmeyen glob ile etkisiz hâle getirildi" sanılıyordu, oysa yükleniyordu.

Bu dizindeki her `.md`, frontmatter'ındaki `paths:` desenine uyan bir dosya okunduğunda
context'e **otomatik** yüklenir. Startup maliyeti sıfırdır (yüklenmezler), tetiklenmeleri
model kararına bağlı değildir.

## Neden var (2026-07-10 memory/recall denetimi)

`AGENTS.md` hiçbir oturumda yüklenmiyordu — Claude Code `CLAUDE.md` okur, `AGENTS.md` okumaz.
356 satırlık davranış katmanı, düz bir markdown link'in arkasında sessizce ölüydü. Çözüm:
her-oturum gerekli olan → `CLAUDE.core.md §1.1`; **iş-anına özgü olan → `claude/rules/`.**

## Yazım kuralı — `paths:` (`globs:` DEĞİL)

```yaml
---
paths: **/*.abap, **/*.ddls
---
```

Değer hem virgüllü tek satır hem YAML listesi olabilir; ikisi de kabul edilir.
Eşleştirme **gitignore semantiğiyle**, proje köküne göreli yol üzerinde yapılır.

`paths:` **olmayan** kural koşulsuz yüklenir (her oturum, `CLAUDE.md` gibi) — bunu bilerek yap.
Kural gerçekten güvenlik-kritikse koşulsuz bırakmak meşru bir tercihtir.

### ⚠ Ters yöndeki tuzak — okumadan yazma

2026-07-10'dan **önce** bu doküman tam tersini söylüyordu: *"`globs:` kullan, `paths:` KULLANMA"*.
Dayanağı [issue #17204](https://github.com/anthropics/claude-code/issues/17204) idi
("closed as not planned"). O tavsiye **bu sürümde yanlıştır ve sessizce zarar verir.**

Claude Code **2.1.206** binary'sinden okunan frontmatter parser'ı:

```js
function SQh(e){ let {frontmatter:t, content:r} = ng(e);
  if(!t.paths) return {content:r};        // ← YALNIZ `paths` okunur
  ... return {content:r, paths:n} }
```

Yükleyicinin ayıklaması `filter(b => conditionalRule ? b.globs : !b.globs)` biçimindedir ve
`.claude/rules` oturum başında `conditionalRule:false` ile çağrılır. Sonuç zinciri:

> `globs:` yazarsın → parser `paths` arar, bulamaz → kural "koşulsuz" kovasına düşer →
> **her oturum yüklenir**, tembel yükleme hiç çalışmaz. Hata mesajı yoktur.

Yani yanlış anahtar kuralı öldürmez — **sessizce her oturuma taşır.** Belirti yok, teyit yanıltıcı.
Bundan daha kötüsü: aleti kuran hook da yanlış anahtar arıyordu, log `?  ?` yazıyordu ve
"ölçüyoruz" sanılıyordu.

**Ders:** anahtar adını dokümandan ya da issue'dan değil, **çalışan sürümün kendisinden**
doğrula. Kanıt yolu:

```bash
grep -a -o -E 'function SQh\(.{800}' "$(which claude)"
```

## Yüklendiğini nasıl KANITLARSIN

`InstructionsLoaded` hook'u (`scripts/hooks/instructions_loaded_log.py`) her yüklemeyi
`.tmp/instructions-loaded.log`'a yazar. Gerçek payload alanları — tahmin değil, binary'den:

| alan | değerler |
|---|---|
| `load_reason` | `session_start` · `nested_traversal` · `path_glob_match` · `include` · `compact` |
| `memory_type` | `User` · `Project` · `Local` · `Managed` |
| `file_path` | yüklenen talimat dosyası |
| `globs?` · `trigger_file_path?` | koşullu kuralda: desen + tetikleyen dosya |

**Doğrulama:** taze oturumda bir `.abap` okut → log'da
`path_glob_match  Project  .../sap-source-protokolu.md` satırı çıkmalı.
Çıkmıyorsa kural ölüdür.

⚠ Talimat dosyaları **oturum başında cache'lenir.** Frontmatter'ı seans içinde değiştirip
aynı seansta ölçemezsin — **taze oturum şarttır.**

## Compaction

`paths:`-scoped kurallar `/compact` sonrası kaybolur; eşleşen dosya tekrar okununca geri
gelirler. Bu yüzden **anayasa (KESİN YASAKLAR) buraya konmaz** — o, kök `CLAUDE.md`'ye fiziksel
damgalıdır (ADR 0021) ve compaction'dan sağ çıkan tek yerdir.
