---
paths: **/*.abap, **/*.ddls, **/*.asddls, **/*.bdef, **/*.behavior, **/*.srvd, **/*.srvb, **/*.ddlx, **/.rules.md
---

# SAP kaynağına dokunurken (L1b — bu kural eşleşen dosya okununca yüklenir)

## 1. PULL-BEFORE-EDIT (ADR 0016) — ANALİZDEN ÖNCE
Repo kopyası SAP'deki aktif sürümden bayat olabilir. **Tazelik doğrulanmadan edit YOK.**
Gate: `core/scripts/hooks/pull_before_edit.py`. Drift varsa önce çek, sonra düşün.

**Neden ANALİZDEN önce (edit'ten değil):** bayat koda göre analiz edersen değişiklik planın **yanlış/uygunsuz** çıkar; edit anında çekmek GEÇ kalır (analizini zaten eski koda yaptın, plan kirlenmiş olur). Tazelik bu yüzden **görev başında, okuma/analizden önce** sağlanır. (working-tree ≠ canlı her edit'te doğal → eski M1 pre-push drift-block kaldırıldı; başkasının canlıda yaptığı belgelenmemiş değişikliği ezme riski baştan-taze ile düşer.)

- **PreToolUse(Edit/Write) hook = YALNIZ BACKSTOP** (`core/scripts/hooks/pull_before_edit.py`): analiz-anında gate EDEMEZ (edit choke-point'i geç kalır) — proaktif pull'u unutursan bayat SAP-kaynak edit'ini bloklar + komutu söyler. **Asıl disiplin = proaktif görev-başı pull**, hook sigortadır.
- **Solo-lider DAHİL** (sen doğrudan yazarken). Takımda editleyen ajan yapar (prompt'larında var).
- **Muaf:** doküman/script/governance/ADR (SAP-dışı) · git-dirty (üstünde çalıştığın WIP) · yeni obje · `ref_docs/`/`.tmp/`.

---

## 6. SAP ADT İŞLEM SIRASI (özet — detay [`playbook/`](playbook/))

> ⛔ **ZORUNLU KURAL:** SAP sisteminde herhangi bir **okuma, yazma veya aktivasyon** işlemi yapmadan ÖNCE [`playbook/README.md`](playbook/README.md)'yi aç ve obje tipine göre ilgili pattern dosyasını oku. **Bu dosyayı okumadan ADT işlemi BAŞLATMA.**

Her ADT işlemi için bu sırayı uygula:

1. **OKU** — [`playbook/README.md`](playbook/README.md) → obje tipine göre dosyayı bul → ilgili `playbook/adt-<tip>.md`'yi aç
2. **PATTERN VARSA UYGULA** — "ÇALIŞAN YÖNTEM" kopyala, parametreleri değiştir. **"Denenen ve başarısız"** tablosundakileri **tekrar deneme** (zaman kaybı).
3. **DOĞRULA** — REST GET + (kritik objeler için) SAP GUI'den onay iste
4. **YENİ KEŞİF VARSA PLAYBOOK GÜNCELLE** — T1/T2/T9 trigger (bkz. [`CLAUDE.core.md`](CLAUDE.core.md))

Bu dosya şunları içerir:
- Her obje tipi için **denenmiş ve başarılı** komut örnekleri (push, activate, download, SQL, lock, vb.)
- **Bilinen hatalar ve kesin çözümleri** (409 conflict, syntax_check yanlış rapor, sap.f 404, vb.)
- **Başarısız olan yollar** — bunları tekrar deneme
- Her playbook section'ı `scripts/` altındaki kanonik implementasyon'a referans verir

### Yasaklar
- ❌ **Playbook okunmadan ADT işlemi başlatma** — yukarıdaki KURAL
- ❌ Playbook'ta yöntem varken kendi script'ini yazma
- ❌ "Çalışmıyor" işaretli library script'i tekrar deneme
- ❌ Yeni keşfi playbook'a yazmadan task kapatma (T1/T2 trigger)

---

## 7. REFERANS DOSYALARI

| Konu | Dosya |
|---|---|
| Session protokol + trigger + indeks | [`CLAUDE.core.md`](CLAUDE.core.md) |
| Naming | [`standards/01-naming.md`](standards/01-naming.md) |
| Backend kodlama (OData/CDS/RAP) | [`standards/02-coding-backend.md`](standards/02-coding-backend.md) |
| Fiori UI | [`standards/03-coding-ui-fiori.md`](standards/03-coding-ui-fiori.md) |
| FS/TS şablonu | [`standards/04-documentation-fs-ts.md`](standards/04-documentation-fs-ts.md) |
| ADT pattern bankası | [`playbook/`](playbook/) (README'den başla) |
| Hata pattern + trigger phrases | [`playbook/lessons-learned.md`](playbook/lessons-learned.md) |
| Paket listesi | `governance/package-registry.md` *(proje reposunda; auto-generated)* |
| Mimari kararlar | [`governance/decisions/`](governance/decisions/) |

---

## 8. KOD GATE'LERİ (BYPASS YASAK)

| Gate | Script | Tetiklenme |
|---|---|---|
| Sprint geçiş | `core/scripts/sprint_gate_check.py` | populate_*.py / spec değişikliği |
| TD spec varlık | `core/scripts/td_spec_check.py` | populate_cds_views.py pre-flight |
| Namespace whitelist | `populate_cds_views.py::validate_sql_view_names()` | populate_cds_views.py pre-flight |
| Paket .rules.md varlık | `core/scripts/validators/check_package_rules_present.py` | run_all_validators |
| Paket naming regex | `core/scripts/validators/check_package_naming.py` | run_all_validators |
| Obje paket sınırı | `core/scripts/validators/check_object_in_correct_pkg.py` | run_all_validators |
| Script playbook ref | `core/scripts/validators/check_scripts_documented.py` | run_all_validators |

Tüm validator'lar: `python core/scripts/validators/run_all_validators.py` (core + proje `scripts/validators-local/` birlikte)

Detay: [`governance/decisions/0003-layered-rule-architecture.md`](governance/decisions/0003-layered-rule-architecture.md)

## 2. REVIEWER PRE-FLIGHT (ADR 0006) — SAP'YE YAZMADAN ÖNCE
`python core/scripts/validators/run_review.py` →
`PASS` → yaz · `WARNING` → yaz + raporla · **`BLOCKER` → YAZMA.**

> ⛔ **ZORUNLU KURAL:** SAP sisteminde herhangi bir **okuma, yazma veya aktivasyon** işlemi yapmadan ÖNCE [`playbook/README.md`](playbook/README.md)'yi aç ve obje tipine göre ilgili pattern dosyasını oku. **Bu dosyayı okumadan ADT işlemi BAŞLATMA.**

Her ADT işlemi için bu sırayı uygula:

1. **OKU** — [`playbook/README.md`](playbook/README.md) → obje tipine göre dosyayı bul → ilgili `playbook/adt-<tip>.md`'yi aç
2. **PATTERN VARSA UYGULA** — "ÇALIŞAN YÖNTEM" kopyala, parametreleri değiştir. **"Denenen ve başarısız"** tablosundakileri **tekrar deneme** (zaman kaybı).
3. **DOĞRULA** — REST GET + (kritik objeler için) SAP GUI'den onay iste
4. **YENİ KEŞİF VARSA PLAYBOOK GÜNCELLE** — T1/T2/T9 trigger (bkz. [`CLAUDE.core.md`](CLAUDE.core.md))

Bu dosya şunları içerir:
- Her obje tipi için **denenmiş ve başarılı** komut örnekleri (push, activate, download, SQL, lock, vb.)
- **Bilinen hatalar ve kesin çözümleri** (409 conflict, syntax_check yanlış rapor, sap.f 404, vb.)
- **Başarısız olan yollar** — bunları tekrar deneme
- Her playbook section'ı `scripts/` altındaki kanonik implementasyon'a referans verir

### Yasaklar
- ❌ **Playbook okunmadan ADT işlemi başlatma** — yukarıdaki KURAL
- ❌ Playbook'ta yöntem varken kendi script'ini yazma
- ❌ "Çalışmıyor" işaretli library script'i tekrar deneme
- ❌ Yeni keşfi playbook'a yazmadan task kapatma (T1/T2 trigger)

---

## 7. REFERANS DOSYALARI

| Konu | Dosya |
|---|---|
| Session protokol + trigger + indeks | [`CLAUDE.core.md`](CLAUDE.core.md) |
| Naming | [`standards/01-naming.md`](standards/01-naming.md) |
| Backend kodlama (OData/CDS/RAP) | [`standards/02-coding-backend.md`](standards/02-coding-backend.md) |
| Fiori UI | [`standards/03-coding-ui-fiori.md`](standards/03-coding-ui-fiori.md) |
| FS/TS şablonu | [`standards/04-documentation-fs-ts.md`](standards/04-documentation-fs-ts.md) |
| ADT pattern bankası | [`playbook/`](playbook/) (README'den başla) |
| Hata pattern + trigger phrases | [`playbook/lessons-learned.md`](playbook/lessons-learned.md) |
| Paket listesi | `governance/package-registry.md` *(proje reposunda; auto-generated)* |
| Mimari kararlar | [`governance/decisions/`](governance/decisions/) |

---

## 8. KOD GATE'LERİ (BYPASS YASAK)

| Gate | Script | Tetiklenme |
|---|---|---|
| Sprint geçiş | `core/scripts/sprint_gate_check.py` | populate_*.py / spec değişikliği |
| TD spec varlık | `core/scripts/td_spec_check.py` | populate_cds_views.py pre-flight |
| Namespace whitelist | `populate_cds_views.py::validate_sql_view_names()` | populate_cds_views.py pre-flight |
| Paket .rules.md varlık | `core/scripts/validators/check_package_rules_present.py` | run_all_validators |
| Paket naming regex | `core/scripts/validators/check_package_naming.py` | run_all_validators |
| Obje paket sınırı | `core/scripts/validators/check_object_in_correct_pkg.py` | run_all_validators |
| Script playbook ref | `core/scripts/validators/check_scripts_documented.py` | run_all_validators |

Tüm validator'lar: `python core/scripts/validators/run_all_validators.py` (core + proje `scripts/validators-local/` birlikte)

Detay: [`governance/decisions/0003-layered-rule-architecture.md`](governance/decisions/0003-layered-rule-architecture.md)

## 3. ADT İŞLEM SIRASI
DDIC (domain → DTEL → struct → tablo) → CDS → BDEF → behavior class → SRVD → SRVB publish.
- Aktivasyon **HTTP 200 sahte-OK verir**: `activationExecuted` + `type="E"/"A"` ile değerlendir.
  `severity=` attribute'u YOKTUR. "Activated" mesajına güvenme → `adt_get` ile canlı doğrula.
- BDEF + behavior class **BİRLİKTE** aktive edilir.
- Inline aktivasyon YASAK (sahte-OK). `adt_activate` kullan.

## 4. YAZMA TEK KAPIDAN
SAP'ye yazan **tek rol `adt-gateway`**'dir. Diğer ajanlar tasarlar + yerel kaynak hazırlar.
Gateway **commit/push etmez** — push/activate yapar, lider'e raporlar.

## 5. DOSYA YERLEŞİMİ
`<source_root>/<MODULE>/<PKG>/` altında obje-tipi klasörleri. Paket kuralları o paketin
`.rules.md`'sinde (L4). Yeni paket → `bootstrap_package.py`.

## 6. KESİN YASAKLAR (ADR 0005 — hatırlatma; tam metin kök CLAUDE.md'de)
Z/Y ile başlamayan standart objeye dokunma · standart tablo verisine direkt SQL yok
(BAPI→RFC→BDC→manuel) · transport/package yaratma-release yok · Z obje = `master_language`
login + 4 alan label TAM.

## 7. KULLANICIDAN TEYİT TABLOSU (AGENTS.md'den taşındı — D1 2026-08-01)
| Konu | Kural |
|---|---|
| **Yeni request** | Yaratma — kullanıcıdan **request numarası iste**. **Geliştirme zaten bir requeste bağlı ise o request üzerinden DEVAM ET, yeni iste**me. |
| **Yeni package** | Yaratma — hangi package kullanılacağını **sor**. Rastgele kullanma. (Bkz. ⛔ KATEGORİ C — yasak) |
| **Yeni transport** | Yaratma — hangi TR kullanılacağını **sor**. Yeni TR otomatik açma. (Bkz. ⛔ KATEGORİ C — yasak) |
| **Yeni ABAP programı/include** | Yaratmadan önce **TITLE iste**. Ana program description'ına TITLE yaz, **include'lara TITLE + standart suffix** ekle. |
| **Yeni DDIC tablo** | Yaratmadan **ÖNCE** tasarımı kullanıcıya **göster + açık ONAY al** (onaysız `create_table` YASAK): tüm alanlar + her alanın **data element'i** + key/uzunluk. Kurallar: client alanı = **`mandt : mandt`** (DTEL MANDT; "client/abap.clnt" değil); mümkün olan her alanda **mevcut std data element** kullan (raw `abap.char(n)`'den kaçın); audit alanı varsa std §F. |

## 8. OBJE→KLASÖR YERLEŞİMİ (somut; AGENTS §4'ten)
### Obje Tipi → Klasör Eşlemesi (Somut Örnekler)

SAP objelerini local'e indirirken **varsayılan `ZAI` klasörünü KULLANMA** (deprecated, ADR 0005). Her objeyi paket adıyla eşleşen klasöre, obje tipine göre alt klasöre kaydet:

| Obje Tipi | Klasör | Örnek (ZSD001_CLC) |
|---|---|---|
| Class | `classes/` | `<source_root>/SD/ZSD001_CLC/classes/ZCL_ZSD_ORDER_DPC_EXT.abap` |
| CDS view (kaynak) | `cds/` | `<source_root>/SD/ZSD001_CLC/cds/ZSD001_C_SO_ITEM.cds` |
| CDS TD spec | `cds/` | `<source_root>/SD/ZSD001_CLC/cds/<obje>.md` (yan yana .cds + .md) |
| Function module / FUGR | `functions/` | `<source_root>/SD/ZSD001_CLC/functions/ZSD001_FM_SO_CREATE.abap` |
| Structure | `structures/` | `<source_root>/SD/ZSD000_CLC/structures/ZSD000_S_BP_BASIC.ddls.asddls` |
| Tablo / Z table | `tables/` | `<source_root>/SD/<PKG>/tables/<obje>.abap` |
| Program / include | `programs/` | `<source_root>/SD/ZSD001_CLC/programs/ZSD001_P_SCHED_ITEMS.abap` |
| Fiori UI app | `ui/<app_adi>/` | `<source_root>/SD/ZSD001_CLC/ui/order_app/` |
| Auth check | `auth/` | `<source_root>/SD/<PKG>/auth/<obje>` |
| Sprint planları, FS doc'u | paket root | `<source_root>/SD/<PKG>/SPEC.md`, `SESSION_NOTES.md` |
| FS/TS txt doc | `docs/` | `<source_root>/SD/<PKG>/docs/FS.txt`, `TS.txt` |

**⛔ ZAI YASAK:** Hiçbir obje `<source_root>/ZAI/` veya benzer "default" klasöre düşemez. Paket adı belirsizse **kullanıcıya sor**.

---

## 5. SAP BAĞLANTI DOSYASI

- Konum: `<PROJECT_ROOT>\.conn_adt` (**nokta İLE** — `.conn_adt`, gizli dosya formatında)
- Script'ler `sap_adt_lib.py` üzerinden okur (CWD'den otomatik bulur). Manuel: `open(r'<PROJECT_ROOT>\.conn_adt')`
- **⚠️ `populate_*.py` çağrılarında `--cwd` argümanı VERME.** Bash'ten path geçerken backslash escape bozulur (`C:\IX\<PROJECT_NAME>` → script'te `C:IX<PROJECT_NAME>` olur, yanlış path). CWD zaten doğru olduğu için argüman gereksiz.
- Bağlantı testi: `GET /sap/bc/adt/discovery` + `auth=(user, pw)`, `headers={'sap-client':'100','X-CSRF-Token':'Fetch'}`, `verify=False`

---

## 5.5. REVIEWER PRE-FLIGHT — SAP YAZMA ÖNCESI ZORUNLU (ADR 0006)

Her SAP yazma işlemi (domain/DTEL/CDS/tablo yarat veya update, class/program push) **öncesinde**:

```powershell
python core/scripts/validators/run_review.py --task <task_type> --artifact <path>
```

| Task Type | Ne zaman | Validator zinciri |
|---|---|---|
| `cds_creation` | Yeni CDS yaratırken | window function, deprecated, currency reference |
| `cds_update` | Mevcut CDS update | aynı + namespace conversion |
| `table_creation` | Yeni Z tablo | currency reference, deprecated |
| `table_update` | Tablo ALTER (T_BOOKHD vakası gibi) | currency reference (qualified format!), deprecated |
| `struct_creation` | Z struct yaratırken (Sprint 6) | DTEL active, currency reference, deprecated |
| `domain_creation_csv` | populate_domains öncesi | output length formula |

**Verdict:**
- **PASS** → SAP'ye yaz
- **WARNING** → Yaz + kullanıcıya raporda belirt
- **BLOCKER** → Yazma YASAK, düzelt + tekrar review

Reviewer = deterministik script orchestrator. LLM'in inisiyatifinde değil. Checklist'ler: [`playbook/checklists/`](playbook/checklists/).

**Atlanırsa:** Manuel kontrol gerekçesini SESSION_NOTES'a yaz. Atlamak risk = patinaj.

---

## 5.6. PULL-BEFORE-EDIT — SAP KAYNAĞI ÜZERİNDE ÇALIŞMAYA BAŞLARKEN (ANALİZDEN ÖNCE; ADR 0016 revize; lider DAHİL)

Bir SAP source objesini (CDS/BDEF/SRVD/class/DDL — `<source_root>/<pkg>/` altı, source uzantısı) değiştirme amacıyla **üzerinde çalışmaya başladığın AN — yani onu İNCELEMEDEN/ANALİZ ETMEDEN ÖNCE** (edit anından çok daha erken) canlı güncel halini çek:

```powershell
python core/scripts/sap_sync_pull.py <NAME> --type <ddls|bdef|srvd|class|structure|...>
```

(seans-bazlı, obje başına 1×; `--session` SessionStart marker'ından otomatik; SAP erişilemezse `--offline`).

**Neden ANALİZDEN önce (edit'ten değil):** bayat koda göre analiz edersen değişiklik planın **yanlış/uygunsuz** çıkar; edit anında çekmek GEÇ kalır (analizini zaten eski koda yaptın, plan kirlenmiş olur). Tazelik bu yüzden **görev başında, okuma/analizden önce** sağlanır. (working-tree ≠ canlı her edit'te doğal → eski M1 pre-push drift-block kaldırıldı; başkasının canlıda yaptığı belgelenmemiş değişikliği ezme riski baştan-taze ile düşer.)

- **PreToolUse(Edit/Write) hook = YALNIZ BACKSTOP** (`core/scripts/hooks/pull_before_edit.py`): analiz-anında gate EDEMEZ (edit choke-point'i geç kalır) — proaktif pull'u unutursan bayat SAP-kaynak edit'ini bloklar + komutu söyler. **Asıl disiplin = proaktif görev-başı pull**, hook sigortadır.
- **Solo-lider DAHİL** (sen doğrudan yazarken). Takımda editleyen ajan yapar (prompt'larında var).
- **Muaf:** doküman/script/governance/ADR (SAP-dışı) · git-dirty (üstünde çalıştığın WIP) · yeni obje · `ref_docs/`/`.tmp/`.

---

## 6. SAP ADT İŞLEM SIRASI (özet — detay [`playbook/`](playbook/))

> ⛔ **ZORUNLU KURAL:** SAP sisteminde herhangi bir **okuma, yazma veya aktivasyon** işlemi yapmadan ÖNCE [`playbook/README.md`](playbook/README.md)'yi aç ve obje tipine göre ilgili pattern dosyasını oku. **Bu dosyayı okumadan ADT işlemi BAŞLATMA.**

Her ADT işlemi için bu sırayı uygula:

1. **OKU** — [`playbook/README.md`](playbook/README.md) → obje tipine göre dosyayı bul → ilgili `playbook/adt-<tip>.md`'yi aç
2. **PATTERN VARSA UYGULA** — "ÇALIŞAN YÖNTEM" kopyala, parametreleri değiştir. **"Denenen ve başarısız"** tablosundakileri **tekrar deneme** (zaman kaybı).
3. **DOĞRULA** — REST GET + (kritik objeler için) SAP GUI'den onay iste
4. **YENİ KEŞİF VARSA PLAYBOOK GÜNCELLE** — T1/T2/T9 trigger (bkz. [`CLAUDE.core.md`](CLAUDE.core.md))

Bu dosya şunları içerir:
- Her obje tipi için **denenmiş ve başarılı** komut örnekleri (push, activate, download, SQL, lock, vb.)
- **Bilinen hatalar ve kesin çözümleri** (409 conflict, syntax_check yanlış rapor, sap.f 404, vb.)
- **Başarısız olan yollar** — bunları tekrar deneme
- Her playbook section'ı `scripts/` altındaki kanonik implementasyon'a referans verir

### Yasaklar
- ❌ **Playbook okunmadan ADT işlemi başlatma** — yukarıdaki KURAL
- ❌ Playbook'ta yöntem varken kendi script'ini yazma
- ❌ "Çalışmıyor" işaretli library script'i tekrar deneme
- ❌ Yeni keşfi playbook'a yazmadan task kapatma (T1/T2 trigger)

---

## 7. REFERANS DOSYALARI

| Konu | Dosya |
|---|---|
| Session protokol + trigger + indeks | [`CLAUDE.core.md`](CLAUDE.core.md) |
| Naming | [`standards/01-naming.md`](standards/01-naming.md) |
| Backend kodlama (OData/CDS/RAP) | [`standards/02-coding-backend.md`](standards/02-coding-backend.md) |
| Fiori UI | [`standards/03-coding-ui-fiori.md`](standards/03-coding-ui-fiori.md) |
| FS/TS şablonu | [`standards/04-documentation-fs-ts.md`](standards/04-documentation-fs-ts.md) |
| ADT pattern bankası | [`playbook/`](playbook/) (README'den başla) |
| Hata pattern + trigger phrases | [`playbook/lessons-learned.md`](playbook/lessons-learned.md) |
| Paket listesi | `governance/package-registry.md` *(proje reposunda; auto-generated)* |
| Mimari kararlar | [`governance/decisions/`](governance/decisions/) |

---

## 8. KOD GATE'LERİ (BYPASS YASAK)

| Gate | Script | Tetiklenme |
|---|---|---|
| Sprint geçiş | `core/scripts/sprint_gate_check.py` | populate_*.py / spec değişikliği |
| TD spec varlık | `core/scripts/td_spec_check.py` | populate_cds_views.py pre-flight |
| Namespace whitelist | `populate_cds_views.py::validate_sql_view_names()` | populate_cds_views.py pre-flight |
| Paket .rules.md varlık | `core/scripts/validators/check_package_rules_present.py` | run_all_validators |
| Paket naming regex | `core/scripts/validators/check_package_naming.py` | run_all_validators |
| Obje paket sınırı | `core/scripts/validators/check_object_in_correct_pkg.py` | run_all_validators |
| Script playbook ref | `core/scripts/validators/check_scripts_documented.py` | run_all_validators |

Tüm validator'lar: `python core/scripts/validators/run_all_validators.py` (core + proje `scripts/validators-local/` birlikte)

Detay: [`governance/decisions/0003-layered-rule-architecture.md`](governance/decisions/0003-layered-rule-architecture.md)

📖 Derin referans: `core/playbook/` (AGENTS.md SUPERSEDED — içeriği bu dosya + MAINTENANCE + operating-model'e taşındı)
