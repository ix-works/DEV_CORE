# Hook'lar — Envanter + Bakım/Evrim Protokolü

> **Bu klasör = proaktif güvence katmanı.** Hook'lar Claude Code event'lerinde otomatik çalışır
> (config: `.claude/settings.json` *(proje reposunda; template: `claude/settings.template.json`)*). Reviewer/validator REAKTİF
> (yazımdan sonra kontrol); hook'lar PROAKTİF (iş başlamadan hatırlat / yazımı blokla).
>
> **Neden var:** kural seti büyüdükçe "doğru anda hatırlamak" insan/AI hafızasına bırakılamaz
> (bkz. lessons-learned PATTERN #8 — include-böl kuralı tek-body yazılırken unutuldu). Hook =
> kuralın *kendini doğru anda dayatması*.

---

## 1. Envanter (event → görev)

> ⛔ **Başlığa ve metne SAYI YAZMA** ("N hook" deme) — **tablo kanoniktir.** Sayı yazılırsa
> bayatlar: 2026-08-13'te başlık "7 hook" diyordu, tabloda **6** satır vardı, diskte **16**
> `.py` vardı ve envanterde hiç geçmeyen 10 hook "yok" diye okunuyordu.
>
> **Tazelik kuralı:** kablolama `claude/settings.template.json`'da yaşar, bu tablo onu ANLATIR.
> Hook ekler/çıkarırsan İKİSİNİ birlikte güncelle.
> Son çapraz-doğrulama: **2026-08-13 — 16/16 `.py` kablolu, kablosuz dosya YOK, template'te
> karşılığı olmayan kayıt YOK** (`pre_tool_guard` üç ayrı matcher'a kablolu).
>
> ⚠ **BU TABLO GATE'Lİ DEĞİL — tazeliği disiplinle korunur.** `check_settings_template_sync.py`
> (C-TPL-01) **template ↔ `scripts/hooks/` DİZİNİNİ** karşılaştırır; **bu README'yi okumaz.**
> Yani yeni hook kablolanmadan geçemez, ama tabloya yazılmadan **geçer** — 2026-08-13'teki
> bayatlığın sebebi tam olarak budur. (Yeni gate açmak ADR 0019 moratoryumuna tabidir:
> önce doküman-hatırlatma denenir; bu satır o hatırlatmadır.)

**Parse-fail sütunu** = hook stdin'deki JSON'u okuyamazsa ne olur (ayrıntı: §4).
`not+serbest` = stderr'e `GIRDI-PARSE-EDILEMEDI` + `exit 0`, işi bırakır ·
`not+degrade` = not basar ama boş girdiyle devam eder ·
`not YOK` = **bilinçli**: stdin hiçbir karara girmez, kaybolan bir şey yok.

| Hook | Event | Matcher | Görev | Parse-fail |
|---|---|---|---|---|
| `session_start.py` | SessionStart | — | Yasaklar + protokol enjeksiyonu + sağlık kontrolleri (junction/manifest) | not+degrade¹ |
| `tooling_radar_check.py` | SessionStart | — | Agent-Dev Tooling Radar bayatlık kontrolü | **not YOK**² |
| `instructions_loaded_log.py` | InstructionsLoaded | — | Hangi talimat dosyası ne zaman/neden yüklendi — ölçüm logu | not+serbest |
| `skill_injector.py` | UserPromptSubmit | — | Tarayıcı/UI-doğrulama + yapısal-kod-arama akış nudge'ları | not+serbest |
| `intake_triage.py` | UserPromptSubmit | — | INTAKE TRIAGE GATE (ITG) tetiği + protokol enjeksiyonu | not+serbest |
| `recall_inject.py` | UserPromptSubmit | — | U1 JIT-recall enjeksiyonu (ilgili hafıza kaydını anında getir) | not+serbest |
| `pre_tool_guard.py` | PreToolUse | `Bash\|PowerShell\|mcp__sap-adt__.*` · `Edit\|Write\|MultiEdit` · `NotebookEdit` | Çok-katmanlı 9 kural: yasaklar, hedef-açıklık, sızıntı, bağlantı-tutarlılık (blok = **exit 2**) | not+serbest |
| `pull_before_edit.py` | PreToolUse | `Edit\|Write\|MultiEdit` | PULL-BEFORE-EDIT gate — bayat SAP kaynağına edit'i bloklar (ADR 0016) | not+serbest |
| `infra_write_guard.py` | PreToolUse | `Edit\|Write\|MultiEdit` | İNFRA YAZIMI BLOĞU — korunan infra yüzeyine (hook/validator/gate/pre-commit/MCP/`claude/rules`/paylaşılan `scripts/**.py`) **ana oturumdan** ya da infra-expert DIŞI bir alt-ajandan doğrudan yazım **exit 2**; `agent_type == infra-expert` MUAF (payload şeması ÖLÇÜLDÜ 2026-08-19). Bypass bayrağı YOK. Korpus: `tests/fixtures/infra_write_guard` | not+serbest |
| `sap_worktype_hint.py` | PreToolUse | `mcp__sap-adt__adt_(push_source\|activate\|dtel_create\|domain_create\|struct_create\|publish_service)` | Obje tipinden deterministik worktype→checklist hatırlatması | not+serbest |
| `itg_backstop.py` | PreToolUse | `mcp__sap-adt__.*` | ITG deterministik backstop — triyajsız SAP işini yakalar (ADR 0022) | not+serbest |
| `watchdog_launch.py` | PreToolUse | `Agent` | Arka-plan agent spawn'ında detached watchdog daemon'ı başlatır; ayrıca **iki brifing ekseni**: `[BRIFING-LINT]` (R2 şablon izi) ve **`[PRIOR-ART / KB-01]`** (2026-08-19) — brifingde adı geçen core script'inin reçetesi `playbook/`de varsa ve brifing o dosyaya atıf VERMİYORSA yolu **spawn anında** verir. Metin-izi ARAMAZ (ölçüldü: 570 gerçek brifingin %98,6'sı zaten yol atfı taşıyor ⇒ trivial yeşil); aramayı KENDİ yapar. Notlar daemon başarısından BAĞIMSIZ (4 emit yolunun hepsinde). Korpus: `tests/fixtures/prior_art_kb01` | not+degrade³ |
| `post_validate.py` | PostToolUse | `Edit\|Write\|MultiEdit` | Governance/standard/validator/spec/`.rules.md` değişince `run_all_validators --quick`; ayrıca **`doc-fs` dalı** (2026-08-17): `**/docs/(FS\|TS\|KD\|EK)-*.md` → oturumda bir kez OKU-işaretçisi + FS/EK için `check_fs_no_analysis_log --file --bulguda-exit1` özeti (warn-first, exit 2 = geri besleme). ayrıca **`infra-express` dalı** (2026-08-17, PATTERN #30): paylaşılan infra (`core/scripts/**/*.py` · proje `scripts/validators-local/*.py`) düzenlenince oturumda BİR KEZ "EXPRESS mi kuyruk mu?" yol-ayrımı (howto-infra-fix ADIM 2); erken-return YOK, TRIGGER/HIZLI_KUME yolu aynen sürer. Korpus: `tests/fixtures/fs_docstd` | not+serbest |
| `post_tool_failure.py` | PostToolUse | `mcp__sap-adt__.*` | Başarısız SAP işleminde patinaj-kesici uyarı (ADR 0006) | not+serbest |
| `config_change_guard.py` | ConfigChange | — | Seans-içi ayar/davranış-yüzeyi değişikliği nöbetçisi (D31; F2'nin runtime bacağı) | not+degrade⁴ |
| `pre_compact.py` | PreCompact | — | Compaction ÖNCESİ SESSION_NOTES + memory flush hatırlatması | **not YOK**² |
| `watchdog_stop.py` | SessionEnd | — | Bu seansın detached watchdog daemon'ını durdurur (stop-sentinel) | not+degrade³ |

**Hook OLMAYAN dosyalar** (event'e bağlı değil, envanterde yok sayılmaz): `watchdog_daemon.sh`
— `watchdog_launch` tarafından spawn edilen yardımcı · `README.md` (bu dosya).

¹ Seans marker'ı `session_id`'siz yazılır → tazelik/seans zinciri (pull_before_edit, intake_triage) sessizce etkilenir.
² **Bilinçli istisna:** stdin yalnızca boşaltılır, çıktı statiktir → parse-fail'de kaybolan karar yok. Fixture'ın **iç kontrol grubu** (not BASMAMALI).
³ Seans kimliği `nosid`/boşa düşer → watchdog yanlış anahtarla açılır / durdurulacak daemon bulunamaz.
⁴ Tespit tamamen payload'a dayanır → parse-fail sessizce "değişiklik yok" gibi okunurdu.

> MCP server **server-side guardrail** (ADR 0005 A/B/C/D) ayrı bir katman — hook'tan bağımsız,
> bypass yok. İki katman: hook (proaktif) + MCP guard (yazma anı).
> ⚠ Kablolama `hook_shim.py` üzerinden gider (D15) ve şim hook'u **`runpy` ile AYNI SÜREÇTE**
> koşturur — bunun sonuçları için §4'teki "ortak yardımcıya bağlanmadı" notuna bak.

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
#   payload'i DOSYAYA yaz, yonlendir:  python scripts/hooks/pre_tool_guard.py < payload.json
```

Hook eklediğinde/değiştirdiğinde **mutlaka** bu şekilde elle çalıştır (sessiz bozulma = güvence kaybı).

### ⛔ `exit 0` "serbest" DEMEK DEĞİLDİR — negatif testin en sık sahte sonucu

Stdin'den JSON okuyan hook'lar **bozuk girdide de 0 döner** (`json.load` → `except: return 0`;
"yabancı girdi serbest" bilinçli fail-safe'i). Dolayısıyla *"guard geçirdi"* ile *"guard payload'ı
hiç okuyamadı"* **ayırt edilemez**di — ve ikincisi "guard bypass edildi" diye raporlanıyordu.

> ✅ **KÖK-FIX 2026-08-13 — sessizlik kalktı, `exit 0` DURUYOR.** Girdiye dayalı karar veren
> **14 hook** parse-fail dalında stderr'e tek satır basar:
> `[<hook>] GIRDI-PARSE-EDILEMEDI: ... -> fail-safe SERBEST (exit 0); KARAR DEGILDIR ...`
> **Exit davranışı bilerek DEĞİŞMEDİ** (bozuk/yabancı girdi hiçbir aracı bloklamamalı) —
> değişen tek şey ayırt edilebilirlik. Artık `0` görünce stderr'e bak: **not varsa ölçümün
> geçersizdir** (payload hiç okunmadı), **not yoksa gerçekten meşru serbesttir.**
>
> - **Not DAİMA stderr'e gider.** Hook'ların bir kısmı stdout'a JSON sözleşmesi basar ve
>   harness onu parse eder → stdout'a tek bayt sızıntı sözleşmeyi kırar. Fixture bunu
>   bayt düzeyinde ölçer (V14/V15).
> - **Not ASCII'dir.** Bazı hook'larda stderr'in utf-8 sarmalayıcısı win32'ye koşulludur;
>   Türkçe harf cp1252/locale'de `UnicodeEncodeError` → **exit 1** üretip fail-safe'i bozardı.
> - **Ortak yardımcıya bağlanMADI, her hook'ta yerel.** Ölçüldü: `hook_shim` hook'ları
>   `runpy.run_path` ile AYNI SÜREÇTE koşturur → `sys.path[0]` `''` olur ve kardeş-modül
>   importu **canlı kablolamada patlar** (doğrudan çağrıda çalışır → sahte-yeşil). Tek
>   kaynak, kod paylaşımıyla değil **fixture sözleşmesiyle** korunur (V13/V16).
> - **KAPSAM DIŞI (bilinçli, 2 hook):** `pre_compact` · `tooling_radar_check` — stdin yalnız
>   boşaltılır, hiçbir karara girmez → parse-fail'de kaybolan bir şey yok. Bunlar fixture'ın
>   **iç kontrol grubudur** (not BASMAMALI).
> - **Gösterim harness'a bağlıdır:** stderr'in kullanıcıya nasıl gösterildiği iddia EDİLMEZ;
>   sözleşme yalnız **stderr'de notun varlığıdır.**
> - Yeni bir stdin-okuyan hook eklersen: notu ekle **ve** fixture'daki `HOOK_KAYDI`'na yaz —
>   yazmazsan `V16 KAYIT TAMLIGI` düşer (sınıf sessizce yeniden büyüyemez).

- **Kök tuzak:** elle yazılan `\\` kabuğa **tek `\`** olarak ulaşır → JSON'da geçersiz escape →
  parse-fail → 0. Ölçüm 2026-08-13 (aynı payload, tek fark yol biçimi): `\\`→**0** · `/`→**2 BLOK** ·
  `\\\\`→**2** · byte-tam `\\` dosyadan→**2**.
- **Yap:** yolları `/` ile yaz **veya** payload'ı `json.dumps` ile dosyaya ürettirip `<` ile ver.
- **Pozitif kontrol ZORUNLU:** aynı harness'ta bloklaması bilinen bir payload da koş; o da 0
  dönüyorsa ölçtüğün şey guard değil **harness'ındır**.
- 🔴 **Hiçbir boru harness'ına güvenme — güvenilirliği ORTAM-BAĞIMLI** (2026-08-13, iki zıt
  ölçüm: bir koşumda PS borusu exit 2 / kabuk borusu 2; diğerinde PS borusu 0 / kabuk borusu
  **255 = taşıyıcı hiç koşmadı**). Ne "PS bozuk" ne "PS sağlam" genellenebilir; `printf`e geçmek
  de kurtarmaz. **Yap:** payload'ı dosyaya yaz + `<` ile ver + pozitif kontrol; taşıyıcının
  koştuğunu doğrula (255 / "command not found" bir guard sonucu DEĞİLDİR).
  Reçete: `governance/infra-test-recipes.md` **B0b**.
