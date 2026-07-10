# CLAUDE.core.md — Çekirdek Loader (DEV_CORE; her projede @import ile yüklenir)

> **Bu dosya metodoloji çekirdeğinin loader'ıdır.** Projeler ince `CLAUDE.md`'lerinden
> `@core/CLAUDE.core.md` ile yükler (ADR 0020). Proje-özel bilgi (SAP bağlantısı, aktif
> paketler, yerel kurallar) PROJE `CLAUDE.md`'sindedir — buraya YAZILMAZ.
> **Konum bilinci:** Bu dosya proje içinden `core/` junction'ı üzerinden okunur;
> buradaki TÜM göreli linkler CORE köküne göredir (proje kökünden erişim: `core/<yol>`).

---

<kesin-yasaklar priority="MUST-NOT" enforcement="ADR-0005 · bypass-yok · istisna-yok · FİZİKSEL-DAMGA">

```
████████████████████████████████████████████████████████████████
█  ⛔  KESİN YASAKLAR — BYPASS YOK, İSTİSNA YOK (ADR 0005)  ⛔  █
████████████████████████████████████████████████████████████████
```

> **Bu yasakların TAM metni her projenin kök `CLAUDE.md`'sine FİZİKSEL damgalıdır**
> (kanonik: `claude/kesin-yasaklar.canonical.md`) — junction/`@import`'a bağımlı DEĞİL:
> kök CLAUDE.md doğrudan yüklenir, junction kırılsa da anayasa context'te. `init_project`
> damgalar · `check_kesin_yasaklar` guard'ı (run_all_validators + session_start +
> pre_tool_guard SAP-yazma) damganın kanonikle eşliğini zorlar · `sync_yasaklar.py`
> kanonik değişince yeniden damgalar. **Özet (tam metin kök CLAUDE.md'de):**
>
> - **A — Standart SAP objeleri** (Z/Y ile başlamayan): yarat/değiştir/sil YASAK; append/DTEL adını AI önermez.
> - **B — Standart tablo verileri**: direkt `INSERT/UPDATE/DELETE/MODIFY` YASAK (BAPI→RFC→BDC→manuel).
> - **C — Sistem state**: transport/package yaratma/release, enqueue lock silme YASAK.
> - **D — Z'li obje**: login = projenin `master_language`'i; 4 field label TAM; activate öncesi REST GET doğrula.
>
> **Yapılması gerekiyorsa:** DUR → AÇIKLA → ÖNERİ SUN → KULLANICIDAN İSTE → BEKLE → DEVAM. "Küçük dokunuş" istisnası YOK.
> 📖 Detay: [`governance/decisions/0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md`](governance/decisions/0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md)

</kesin-yasaklar>

> **🧭 ÇEKİRDEK DAVRANIŞ — lider + TÜM alt-ajanlar:** **TAHMİN YASAK = kanıtlı hareket et.**
> Yöntem/pattern/syntax/alan-adını mevcut artefakt + playbook/standard'dan doğrula, canlı
> teyit et; "activated/uploaded/çalıştı" mesajına güvenme; emin değilsen DUR → sor;
> DTEL/append adı önerme (kullanıcı verir). (Tam yasak metni kök CLAUDE.md'de fiziksel damgalı.)

> **🔎 ARAMA TALİMATI (D29 — kritik):** `core/` bir **junction**'dır ve `Grep`/`Glob`
> junction'ı **TAKİP ETMEZ**. Kontrollü deney (2026-07-09): *ignore'suz* bir junction'ın
> arkasındaki dosya iki araçla da **bulunamadı**; aynı dosya gerçek dizindeyken bulundu.
> Yani sebep `.gitignore` DEĞİL — `/core/` satırını silmek ya da `respectGitignore:false`
> yapmak **hiçbir şeyi değiştirmez**. İkisi de **SESSİZCE BOŞ** döner; "dosya yok" ile
> ayırt edilemez. **Kökten sıfır-sonuç ≠ "core'da yok".**
>
> **YAPISAL ÇÖZÜM — önce buraya bak:** `governance/CORE-INDEX.md` (proje reposunda
> **gerçek** dosya → kökten aranır, bulunur, doğru `core/...` yolunu verir).
> `build_core_index.py` üretir, `check_core_index_fresh.py` tazeliğini zorlar.
>
> Doğrudan aramak gerekirse DAİMA `path=` ile:
> - **`Grep`:** `path="core"` veya `path="core/playbook"` — pattern serbest.
> - **`Glob`:** `path="core"` **+ tek-segmentli pattern** (`"**/*.md"` ya da `"*.md"`).
>   ⚠ `path=` verildiğinde pattern'de `/` geçerse Glob **DAİMA 0** döner →
>   `Glob("core/playbook/*.md")` ve `Glob(path="core", "playbook/*.md")` İKİSİ DE YANLIŞ.
>   Doğrusu: `Glob(path="core/playbook", "*.md")`.
> - **`Read`:** göreli `core/...` çalışır (hook'ların verdiği yollar artık önekli).
> - **`Bash`:** `rg -L --no-ignore <p>` **veya** açıkça `rg <p> core/`; `find -L core`
>   (`find core` → 0). `--no-ignore` TEK BAŞINA yetmez, `-L` TEK BAŞINA yetmez.
>
> **Alt-ajanlara da söyle:** brifingde `path=core/` demezsen ajan metodolojinin var
> olduğunu bile keşfedemez ve "böyle bir kural yok" diye rapor eder.

---

## 1. KATMAN ÖZETİ (Rule Architecture — ADR 0003 + 0020)

| Katman | Konu | Yer | Nasıl yüklenir |
|---|---|---|---|
| **L1a** | Her-oturum davranış değişmezleri | **§1.1 (aşağıda)** | her oturum (bu dosya) |
| **L1b** | Dosya-türüne bağlı davranış (ADT sırası, reviewer, yerleşim) | [`claude/rules/`](claude/rules/) | **eşleşen dosyaya dokununca** (`globs:`) |
| **L1c** | Derin davranış referansı | [`AGENTS.md`](AGENTS.md) | ⚠ **OTOMATİK YÜKLENMEZ** — açıkça okunmalı |
| **L2** | Stabil kurumsal standartlar (naming, coding, UI, doc format) | [`standards/`](standards/) | on-demand |
| **L3** | Operasyonel pattern (ADT pattern bankası, lessons-learned) | [`playbook/`](playbook/) | on-demand |
| **L4** | Paket-spesifik (prefix, bağımlılık, istisna) — **PROJE reposunda** | `<source_root>/<MODULE>/<PKG>/.rules.md` | on-demand |

> **⚠ 2026-07-10 memory/recall denetimi:** `AGENTS.md` **hiçbir oturumda context'e girmiyordu.**
> Claude Code `CLAUDE.md` okur, `AGENTS.md` okumaz (resmî: code.claude.com/docs/en/memory) ve
> buradaki bağlantı `@import` değil düz markdown link'ti. 356 satır / 25 zorunlu kural sessizce
> ölüydü — üstelik ekran teyidi her oturum "AGENTS.md yüklendi" diyordu. Her-oturum gerekli olan
> §1.1'e taşındı; dosya-türüne bağlı olan `claude/rules/`e (glob-tetiklemeli) indi.
> **"Yüklendi" varsayma — markdown link hiçbir şey yüklemez.**

## 1.1 HER-OTURUM DAVRANIŞ DEĞİŞMEZLERİ (L1a)

- **GIT:** `main`'e doğrudan commit YOK → branch + PR. Commit = **lider**; alt-ajan commit/push etmez.
  Gün-sonu: checkpoint + `SESSION_NOTES.md` + WIP commit + **`push origin main` ZORUNLU**.
- **HEDEF-AÇIKLIK — `gh`/`git` üç değişmez (2026-07-10 dersi; guard kural 9):**
  1. **Repoyu DEĞİŞTİREN her `gh` alt-komutunda hedef AÇIKÇA verilir.** Üç biçim vardır:
     · `pr`/`issue`/`release`/`secret`/`variable`/`workflow`/`ruleset`/`label` → **`--repo <ORG>/<REPO>`**
     · `repo create|edit|rename|delete|archive` → **konumsal `<ORG>/<REPO>`** (bu komutlarda `--repo` yok)
     · `api` → **yolun kendisi**: `repos/<ORG>/<REPO>/...` (⚠ `{owner}`/`{repo}` placeholder'ı cwd'den çözülür — YASAK)
     Gerekçe: `gh` hedefi verilmezse **cwd'den** çıkarır ve `core/` bir **junction**'dır →
     yanlış dizinde çalışan bir komut private proje içeriğini **public çekirdeğe** yayınlayabilir.
     Yayın cache'lenir: **geri alınamaz**, üstelik `gh` başarı döner (sessiz).
     Okuma komutları (`list`/`view`/`status`) ve repo-hedefsiz API'ler (`gh api user|graphql|rate_limit`) serbesttir.
  2. **`git` cwd-tabanlıdır:** proje içinden `cd core && git …` **DEV_CORE'u** etkiler.
     Hedef bariz değilse `git -C <repo-kökü> …` kullan.
  3. **`git commit` (heredoc) ile `gh pr create` AYNI Bash çağrısına konmaz.** Guard komut
     metninin tamamını "yayınlanan gövde" sayar; commit mesajındaki e-posta/iz PR gövdesi
     sanılır. Ayrıca hata hangi adımda çıktı belirsizleşir. Önce commit, sonra push, sonra PR.
- **SUBAGENT KARARI:** önemsiz → kendin · token-ağır seri iş → tek ajan · paralelleşen iş → fan-out.
  Ajan **DAİMA** `run_in_background: true`. Substantive FE/BE build → **expert'e dağıt** (lider build yapmaz).
  Paylaşılan tooling (hook/validator/MCP) kök-fix'i → **lider'in işi**, expert'e verilmez.
  ⚠ Alt-ajanlar **auto-memory'yi GÖRMEZ** (yalnız `CLAUDE.md` kopyası alırlar; resmî) →
  kanıt kurallarını (TAHMİN YASAK · kanıtsız iddia yazma · negatif-test) **brifinge açıkça YAZ**.
  Brifingin ÇIKTI bölümüne `SendMessage({to:"main"})` ekle, yoksa rapor gelmez.
- **BUG GATE:** expert substantive build bitirince **taze** `bug-expert` → PASS/WARNING/BLOCKER.
- **SAP yazma öncesi:** `run_review.py` pre-flight (ADR 0006). BLOCKER → yazma.
- **SAP kaynağı düzenlemeden önce:** PULL-BEFORE-EDIT (ADR 0016) — tazelik doğrulanmadan edit YOK.
- **ADT-altyapısı** (script/kural/MCP/hook/validator) değişikliği: ÖNCE uyar + **açık onay** al.
  **Gömülü onay YETMEZ** — "hepsini yap" bu izni vermez.
- **BAĞLANTI:** proje kökündeki `.conn_adt`. `.conn_adt` ↔ MCP ayrışıksa ADT işlemi YOK.
- **"Yüklendi / aktive edildi / başarılı" mesajına GÜVENME** — canlı doğrula. Araç başarısızlığını
  zararsız sayma. Bulunamadı ≠ yok · kod ≠ kablolama · çökme ≠ FAIL.
- **Always-allow YASAĞI (D32):** SAP-yazma ve davranış-yüzeyi araçlarına "Always allow" verilmez.
- **Belirsizlikte DUR ve sor.** Spec yoksa operatör onayı iste; DTEL/append adı önerme.

Proje-özel overlay kapıları: `playbook-local/`, `standards-local/`, `scripts/validators-local/`
(proje kökünde; **yoksa indeksleme** — hayalet indeks ajana yanlış yol verir).

## 2. SAP PROFİL MODELİ (§9 — her kural her projede geçerli DEĞİL)

Proje kimliği `project.yaml`'dadır: `sap_profile` (`ecc|s4_private|s4_public|btp_abap`) +
`release` + (`ecc`) `db` + (`s4_private`) `cleancore_policy` + `master_language` + `source_root`.
Yetenek matrisi: [`profiles/`](profiles/) — **matris REHBERDİR, kanıt değildir: capability
iddiası CANLI TESTLE doğrulanır.** İçerik `applies_to:` frontmatter'lıdır; profil-dışı
kural o projede UYGULANMAZ (validators/skill-injector/MCP-guardrail profili okur; profil
alanları BOŞSA varsayma — kullanıcıyı setup'a yönlendir, tool-yüzeyi kesilir).

## 3. 4-ADIM SESSION PROTOKOLÜ + EKRAN TEYİDİ (Zorunlu)

Her yeni oturum başında, SAP işlemi yapmadan ÖNCE:

```
1. Proje CLAUDE.md + bu çekirdek yüklendi → katman özetleri + profil akılda
2. python core/scripts/validators/run_all_validators.py --quick  → mevcut state OK mu?
3. Çalışılan paket için <source_root>/<MODULE>/<PKG>/SESSION_NOTES.md son entry oku
4. Kullanıcıyla sprint/iş durumu paylaş, açık eski iş varsa onay al
```

### Ekran Teyidi — İlk Mesaj Formatı (ZORUNLU)

```
[Session başladı — <PROJECT_NAME>]
⛔ KESİN YASAKLAR aktif (ADR 0005): A/B/C/D (D: master_language=<ML>)
✓ Core loader yüklendi (junction sağlam) — CLAUDE.core.md (L1a) + claude/rules/ (L1b, glob-tetiklemeli)
✓ SAP profili: <sap_profile>/<release> (bloklu yetenekler: <profilden>)
✓ run_all_validators.py --quick: <OK | N ihlal>
✓ Aktif paket: <PKG_FULL veya "belirsiz, kullanıcıya sor">
✓ Son session notu: <SESSION_NOTES.md'den 1 satır>
Devam: <soru veya hazır bilgi>
```

Bu format atlanırsa kullanıcı loader'ın yüklenmediğini varsayar → T4.

## 4. T1-T11 TRIGGERS + SORU 0 (Yeni Bilgi Yazma)

| # | Tetikleyici | Hedef |
|---|---|---|
| **T1** | ADT işlemi başarısız denemelerden sonra başarılı oldu | `playbook/<obje-tipi>.md` (ÇALIŞAN YÖNTEM + DENENEN BAŞARISIZ) — **core'a, SORU 0 kurallarıyla** |
| **T2** | Playbook'ta olmayan obje tipi/scenario başarıyla işlendi | Yeni section/dosya `playbook/` (core) |
| **T3** | Kullanıcı kural koydu | Davranışsa AGENTS.md, standartsa standards/ (core); pakete özelse proje `.rules.md` |
| **T4** | Kullanıcı trigger phrase kullandı | `playbook/lessons-learned.md` recurrence + kod gate öner |
| **T5** | Yeni paket / naming kararı | Proje: `<source_root>/<MODULE>/<PKG>/.rules.md` (bootstrap script) |
| **T6** | TempScripts'te çalışan script, kalıcı lazım | core `scripts/`e taşı + playbook referansı (genericize!) |
| **T7** | Mimari/yapısal karar | Metodolojiyse core `governance/decisions/NNNN-*.md`; proje işiyse proje reposu `<PROJE>-NNN` |
| **T8** | Paket-spesifik bağımlılık/istisna | Proje `.rules.md` "Bilinen İstisnalar" |
| **T9** | Script kullanıldı ama playbook referansı yok | İlgili playbook MD'sine pattern + script ref |
| **T10** | Patinaj/hata yakalandı | Düzelt + playbook (T1) + "reviewer yakalar mıydı?" → validator/checklist ya da known blind spot (ADR 0006) |
| **T11** | Tekrar-eden tuzak / yeni iş-türü | [`scripts/hooks/README.md`](scripts/hooks/README.md) §2 karar ağacı: validator / checklist / hook / pre_tool_guard. Playbook'a not YETMEZ |

**SORU 0 (eski T12'nin yerine — yazım-anı hedef kararı):**

```
SORU 0: Bu bilgi metodoloji mi, projeye mi özel?
  ├─ Metodoloji (pattern, validator, hook, standart, ADT dersi, checklist satırı)
  │     → DOĞRUDAN core'a yaz. Yazarken:
  │       • genericize et: ZSD0xx→ZSD001 örneği · sistem/kullanıcı/müşteri→placeholder
  │         (ZSD000/ZSD001 demoları İSTİSNA — çalışan-örnek korunur; pre-commit gate yakalar)
  │       • link kuralı: core-içi link CORE-göreli; core→proje link YASAK
  │       • profil etiketi: applies_to hangi profiller? (kanıtsız genişletme YOK)
  └─ Proje işi (paket, iş kuralı, müşteri süreci, bağlantı, sprint)
        → proje reposu (SORU 1-3 ağacı; L4 .rules.md aynen)
SORU 1: Tek paket mi, tüm proje mi?  → tek paket = L4
SORU 2: Tipi? davranış=AGENTS · standart=standards · nasıl-yaparım=playbook · karar=decisions
SORU 3 (L3): dar obje-tipi → playbook/adt-<tip>.md · cross-cutting → lessons-learned.md
```

## 5. MEMORY KURALLARI (§10)

- **Memory = hatırlatıcı, CORE = kanonik.** Metodoloji-nitelikli her memory-feedback
  core'a TERFİ eder (gün-sonu kontrolü), memory'de tek satır pointer kalır.
- **Kullanıcı-seviyesi `~\.claude\CLAUDE.md`'ye METODOLOJİ YAZILMAZ** (çift-kaynak drift +
  git-dışı + kapsam taşması). Yalnız projeden-bağımsız kişisel tercih.
- Yeni proje memory'si `claude/memory-seed/`'den tohumlanır (`seed_memory`).

## 6. STOP KURALI — Belirsizlik Halinde Forward Progress YOK

1. `run_all_validators.py` fail → önce düzelt
2. Gate başarısız → eksiği kapat ÖNCE
3. Spec yok → operator approval iste
4. Trigger phrase geldi → pattern bak, kod gate öner
5. SAP "rename broken"/"still active"/"lock conflict" → audit, sebep bul
6. **Davranış-yüzeyi uyarısı** (manifest/ConfigChange) → oturuma güvenme, lider'e bildir (§11)

## 7. KOD GATE'LERİ (Bypass YASAK; hepsi hook_shim üzerinden — D15)

| Gate | Script | Ne zaman |
|---|---|---|
| Sprint geçiş | `scripts/sprint_gate_check.py` | populate/spec değişikliği |
| Spec pre-flight | `scripts/td_spec_check.py` | populate_cds_views öncesi |
| Namespace whitelist | `populate_cds_views.py::validate_sql_view_names()` | (project.yaml `sql_view_prefix`) |
| Paket kuralları | `scripts/validators/check_package_*.py` | run_all_validators (`source_root`'tan okur) |
| **Core-sızıntı kilidi** | `scripts/validators/check_core_not_committed.py` | run_all_validators + pre_tool_guard commit-kapsamı |
| **Davranış-manifest (F2)** | session_start manifest-diff + **ConfigChange hook** | oturum-başı + seans-içi |
| **Freeze/salt-okunur kökler** | `pre_tool_guard` — project.yaml `frozen_readonly_paths` hedefli yazma RED | her Edit/Write/Bash |
| **Özyinelemeli-silme bloğu** | `pre_tool_guard` — core/junction path'ine rm -rf/clean/Remove-Item RED | her Bash |
| PULL-BEFORE-EDIT | `scripts/hooks/pull_before_edit.py` | SAP source düzenleme öncesi (ADR 0016) |
| Reviewer pre-flight | `scripts/validators/run_review.py` | SAP yazma öncesi (ADR 0006): PASS→yaz · WARNING→yaz+raporla · BLOCKER→yazma |

Tek komut: `python core/scripts/validators/run_all_validators.py` (core + proje `validators-local/` birlikte; profil-modlu).
⚠ **Always-allow YASAĞI (D32):** SAP-yazma ve davranış-yüzeyi araçlarına "Always allow" izni VERİLMEZ — izin katmanı hook-safeguard'ları soyar.

### SAP ADT MCP Server (ADR 0007)

Typed MCP tool'lar ([`mcp_servers/sap_adt/`](mcp_servers/sap_adt/)): tek-obje yaratım/aktivasyon/push/search/lock = MCP; CSV-batch/validator/gate = script. Server-side guardrail: ADR 0005 + bağlantı-tutarsızlık gate'i (ADR 0010). **Profil-bazlı tool-blok (§9.4d) CANLI** (D34d, 2026-07-10): tool'lar `available_on` etiketi taşır; profil uymuyorsa tool `tools/list`'te **hiç görünmez** (`mcp_servers/sap_adt/_profile.py` + `_app.profil_tool`). `project.yaml`'da `sap_profile` yok/enum-dışıysa **fail-closed: yalnız `ping` açılır.** Politika tablosu kanıtla dolar — bugün tek matris-kanıtlı daraltma `adt_transport_list` ∉ `btp_abap` (`transport: gcts` → CTS ucu yok); `s4_public` hücresi "NÖTR, canlı doğrulanacak" dediği için BLOKLANMAZ. Bağlantı: proje kökündeki `.conn_adt` (env `CLAUDE_PROJECT_DIR` → cwd fallback).

## 8. DAVRANIŞ GÜVENLİK DUVARI — ÖZET (§11)

*Davranış taşıyan dosya ya core'dan junction'la gelir ya behavior-manifest'te kayıtlıdır;
değilse RED ya da intake-gümrüğünden geçer.* Davranış-yüzeyi (CLAUDE.md, `**/CLAUDE.md`,
`.claude/**`, `.mcp.json`, `project.yaml`, `scripts/hook_shim.py`) yalnız lider-onaylı PR
ile değişir. **Yabancı repoya ilk temas:** ÖNCE Claude'suz `foreign_project_audit.py`
pre-scan → `--safe-mode` → kod-sınıfı (hooks/MCP) incelemesiz normal oturum AÇILMAZ →
`guest_mode.py` ile CLAUDE.local.md. Değerli dış kural → `intake/` karantina → çakışma-
analizi + canlı-test → PR.

## 9. DOSYA İNDEKSİ — "Şu konu nerede?" (yollar CORE-göreli)

| Konu | Dosya |
|---|---|
| Her-oturum davranış değişmezleri | §1.1 (bu dosya) |
| Dosya-türüne bağlı davranış (glob-tetiklemeli) | [`claude/rules/`](claude/rules/) |
| Git workflow / ADT-infra — **derin referans, otomatik yüklenmez** | [`AGENTS.md`](AGENTS.md) |
| Naming standardı | [`standards/01-naming.md`](standards/01-naming.md) |
| Klasik backend (SEGW/FE) | [`standards/02-coding-backend.md`](standards/02-coding-backend.md) |
| RAP kodlama | [`standards/05-coding-rap.md`](standards/05-coding-rap.md) |
| Fiori UI5 kodlama + deploy | [`standards/03-coding-ui-fiori.md`](standards/03-coding-ui-fiori.md) |
| Klasik dialog (report/Dynpro/ALV) | [`standards/06-coding-classic-dialog.md`](standards/06-coding-classic-dialog.md) |
| Klasik ALV kanonik template (ADR 0012) | [`playbook/templates/classic-alv-list.prog.abap`](playbook/templates/classic-alv-list.prog.abap) |
| Dynpro + GUI status üretimi | [`playbook/howto-dynpro-gui-status-generation.md`](playbook/howto-dynpro-gui-status-generation.md) |
| Çıktı / Adobe Forms | [`standards/07-output-forms.md`](standards/07-output-forms.md) |
| FS/TS şablonları | [`standards/04-documentation-fs-ts.md`](standards/04-documentation-fs-ts.md) |
| Klasik GUI F1/KD yardımı | [`standards/08-classic-gui-f1-help.md`](standards/08-classic-gui-f1-help.md) |
| Ambalajlama talimatı tüketimi | [`standards/09-packing-instruction-consumption.md`](standards/09-packing-instruction-consumption.md) |
| İş-alım / kapsam-triage / modül-persona (ADR 0022) | [`playbook/intake-triage.md`](playbook/intake-triage.md) · modül paketleri [`playbook/modules/`](playbook/modules/) |
| ADT pattern bankası | [`playbook/README.md`](playbook/README.md) |
| Hata pattern + trigger phrases | [`playbook/lessons-learned.md`](playbook/lessons-learned.md) |
| Belge kilidi (ADR 0014) | [`playbook/howto-document-lock.md`](playbook/howto-document-lock.md) |
| UI tecrübesi FE+BE (§0 PRE-FLIGHT) | [`playbook/ui-freestyle-odata-v2.md`](playbook/ui-freestyle-odata-v2.md) · [`playbook/ui-backend-rap.md`](playbook/ui-backend-rap.md) |
| Profil yetenek matrisi | [`profiles/`](profiles/) |
| Mimari kararlar (ADR) | [`governance/decisions/`](governance/decisions/) |
| **Yeni proje açılışı** | [`PROJECT_BOOTSTRAP.md`](PROJECT_BOOTSTRAP.md) *(E3'te gözden geçirilir)* |
| **Canlı-çekirdek işletimi** (PR/CI/stable/rollback) | [`MAINTENANCE.md`](MAINTENANCE.md) |
| Agent teams işletim modeli | [`governance/agent-teams-operating-model.md`](governance/agent-teams-operating-model.md) |
| Kurulu plugin envanteri | [`governance/tooling-plugins.md`](governance/tooling-plugins.md) |
| Ekip/proje kurulumu | `python core/scripts/team_setup.py` · yeni proje: `core/scripts/init_project.py` |
| Paket bootstrap | `python core/scripts/bootstrap_package.py <PKG_FULL> --title "..."` |

## 10. SAP BAĞLANTI (jenerik kural)

- Bağlantı dosyası: **proje kökünde** `.conn_adt` (K10; env `CLAUDE_PROJECT_DIR`-öncelikli
  çözümleme). Sistem kimliği/client/kullanıcı PROJE `CLAUDE.md`'sinde belgelenir.
- İş sonu 5-saniye self-check: pattern playbook'ta var mıydı? başarısız deneme kaydedildi mi?
  paket kuralı netleşti mi (→ `.rules.md`)? commit mesajına yansıt. Memory-terfi kontrolü (§5).

---

> **Bu dosya çekirdek loader'dır.** Proje-özel her şey proje `CLAUDE.md`'sinde. Yeni bilgi
> nereye? → §4 SORU 0. Metodoloji araması NASIL? → baştaki 🔎 ARAMA TALİMATI (path=core/).
