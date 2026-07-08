# Hook'lar — Envanter + Bakım/Evrim Protokolü

> **Bu klasör = proaktif güvence katmanı.** Hook'lar Claude Code event'lerinde otomatik çalışır
> (config: `.claude/settings.json` *(proje reposunda; template: `claude/settings.template.json`)*). Reviewer/validator REAKTİF
> (yazımdan sonra kontrol); hook'lar PROAKTİF (iş başlamadan hatırlat / yazımı blokla).
>
> **Neden var:** kural seti büyüdükçe "doğru anda hatırlamak" insan/AI hafızasına bırakılamaz
> (bkz. lessons-learned PATTERN #8 — include-böl kuralı tek-body yazılırken unutuldu). Hook =
> kuralın *kendini doğru anda dayatması*.

---

## 1. Envanter — 7 hook (event → görev)

| Hook | Event | Matcher | Görev | ADR/ref |
|---|---|---|---|---|
| `session_start.py` | SessionStart | — | ADR 0005 yasaklar + Ekran Teyidi formatını enjekte | CLAUDE.md §2 |
| `skill_injector.py` | UserPromptSubmit | — | SAP işi sezilince skill + **iş-türüne özel ZORUNLU checklist**i adıyla söyle | gap #9 / §3 aşağıda |
| `pre_tool_guard.py` | PreToolUse | `Bash\|mcp__sap-adt` | Transport/release girişimini blokla (exit 2) | ADR 0005-C |
| `post_validate.py` | PostToolUse | `Edit\|Write\|MultiEdit` | Yönetişim/standart/validator/spec dosyası değişince `run_all_validators --quick` | kod-gate |
| `post_tool_failure.py` | PostToolUse | `mcp__sap-adt` | Yapısal SAP hatasında patinaj-kesici uyarı | ADR 0006 |
| `pre_compact.py` | PreCompact | — | SESSION_NOTES + memory flush hatırlatması | bağlam koruma |

> MCP server **server-side guardrail** (ADR 0005 A/B/C/D) ayrı bir katman — hook'tan bağımsız,
> bypass yok. İki katman: hook (proaktif) + MCP guard (yazma anı).

---

## 2. KARAR — yeni tekrar-eden durumda hangi katman?

Yeni bir tuzak/kural/iş-türü keşfedince (T10 / lessons-learned SELF-UPDATE sırasında) **sırayla** sor:

```
1. Saf yazım-sonrası kontrol mü? (dosya/obje yazıldıktan sonra "şu doğru mu")
   → VALIDATOR (scripts/validators/) + reviewer task (run_review.py). Hook DEĞİL.

2. Belirli bir İŞ-TÜRÜNE özel mi, iş başlarken hatırlatılmalı mı?
   → CHECKLIST satırı (playbook/checklists/<is-turu>.md).
     ├─ İş-türü skill_injector._WORKTYPES'ta VAR mı?
     │    ├─ VAR  → checklist'e satır ekle. Hook zaten okutuyor → BİTTİ (otomatik yüzeye çıkar).
     │    └─ YOK  → skill_injector._WORKTYPES'a (regex, label, checklist-ref) ekle + checklist yarat.
     └─ _STRONG eşiğini de tetikliyor mu? Değilse _STRONG regex'ine keyword ekle.

3. Cross-cutting (her iş için geçerli) PROAKTİF hatırlatma mı? (örn. her oturum başı, her compact)
   → İlgili EVENT hook'una ekle (session_start / pre_compact) veya yeni hook.

4. Yazma-anında DAYATILMALI (sadece hatırlatma değil, BLOKLA) mı?
   → pre_tool_guard.py'ye guard ekle (exit 2) — veya MCP server guardrail (server-side).
```

**Kural:** Bir tuzak ikinci kez tekrarladıysa (PATTERN recurrence) ve "iş başlarken hatırlasaydım
olmazdı" diyorsan → **checklist + (gerekirse) hook** zorunlu. Sadece playbook'a not düşmek YETMEZ
(playbook reaktif okunur; hook doğru anda dayatır).

---

## 3. skill_injector._WORKTYPES nasıl genişletilir

`skill_injector.py` içinde `_WORKTYPES` listesi: `(regex, label, checklist-ref)`. Yeni iş-türü:

1. `playbook/checklists/<yeni>.md` yarat (format: `| ID | Kontrol | Severity | Ref |`).
2. `_WORKTYPES`'a satır ekle; gerekiyorsa `_STRONG` regex'ine tetikleyici keyword ekle.
3. `SKILL.md` tetiklemeli-yükleme tablosuna iş-türü→dosya satırı ekle.
4. Test: `echo '{"prompt":"<örnek istek>"}' | python scripts/hooks/skill_injector.py` → checklist
   adı çıkıyor mu?

Mevcut 7 iş-türü: RAP/CDS, Klasik dialog/ALV, Freestyle UI5, DDIC struct, DDIC tablo,
DDIC domain/DTEL, Adobe Forms. (Checklist kapsamı = %100, 2026-06-03.)

---

## 4. Test — bir hook çalışıyor mu?

```powershell
# skill_injector (UserPromptSubmit): prompt ver, additionalContext + checklist adı dönsün
echo '{"prompt":"ZSD001 icin ALV report yaz"}' | python scripts/hooks/skill_injector.py

# session_start: bos stdin, Ekran Teyidi context'i dönsün
echo '{}' | python scripts/hooks/session_start.py

# pre_tool_guard: transport-create denemesi exit 2 + reason dönmeli
```

Hook eklediğinde/değiştirdiğinde **mutlaka** bu şekilde elle çalıştır (sessiz bozulma = güvence kaybı).
