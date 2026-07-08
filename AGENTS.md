# AGENTS.md — <PROJECT_NAME> AI Agent Davranış Kuralları (L1)

> Bu dosya **L1 katman**: AI agent'ın her oturumda nasıl davranması gerektiğini tanımlar. Detay kurallar (kodlama, naming, doc format, ADT pattern) ayrı dosyalarda — referanslar aşağıda.
>
> **Önce oku:** [`CLAUDE.core.md`](CLAUDE.core.md) — proje session protokolü + indeks.

---

```
████████████████████████████████████████████████████████████████
█                                                              █
█   ⛔  KESİN YASAKLAR — HİÇBİR İSTİSNA YOK, BYPASS YOK  ⛔   █
█                                                              █
████████████████████████████████████████████████████████████████
```

## ⛔ KATEGORİ A — SAP STANDART OBJELERE DOKUNMA YASAĞI

**Z ile başlamayan TÜM SAP objeleri standart sayılır. AI bunlara HİÇBİR şekilde dokunamaz:**

- ❌ Standart **tablo** (LIKP, LIPS, VBAK, VBAP, VBPA, MARA, MARC, KNA1, KNVP, T-tables, vb.) yaratma/değiştirme/silme
- ❌ Standart tabloya **append struct** ekleme veya append struct alan değiştirme
- ❌ Append struct, custom field, DTEL **adı önerme ve uygulama** — AI YAPMAZ, kullanıcı SAP GUI'den belirler ve uygular, sonucu (field/DTEL adı) AI'a bildirir. AI sadece bu sonucu Z'li objelerinde kullanır.
- ❌ Standart **struct/view/data element/domain** değiştirme veya alan ekleme
- ❌ Standart **program/include/class/FM/BAdI/enhancement** değiştirme veya implementation yazma
- ❌ Standart **customizing tablo (T-tables)** değiştirme
- ❌ Standart **message class** değiştirme veya yeni mesaj ekleme
- ❌ Standart **CDS/DDIC view** değiştirme
- ❌ Yukarıdakileri yapan **script yazma veya çalıştırma** — bypass YASAK

## ⛔ KATEGORİ B — STANDART TABLO VERİLERİNE DİREKT MÜDAHALE YASAĞI

- ❌ Standart tabloya direkt **INSERT / UPDATE / DELETE / MODIFY** (SQL veya ABAP üzerinden)
- ❌ **Z'li programda yazdığın ABAP kodunda** bile standart tabloya direkt INSERT/UPDATE/MODIFY/DELETE YASAK — kendi yazdığın program içinde olsa bile bypass değildir, hâlâ yasak
- ❌ SAP standart business logic'i bypass eden veri yazma
- ❌ Update FM/BAPI yoksa **alternatif yol icat etme** (BDC + direkt update mix, vb.) — kullanıcıdan manuel iste
- ✅ **ZORUNLU sıralı arama:** BAPI (`BAPI_*_CREATE/CHANGE`) → RFC FM → transaction (BDC) → kullanıcıdan manuel. Asla direkt SQL.

## ⛔ KATEGORİ C — SİSTEM STATE YÖNETİMİ YASAĞI

- ❌ **Transport request yaratma** (yeni TR açma)
- ❌ **Transport request release etme** (var olanı kapama)
- ❌ **Package yaratma** (SE21 veya `scripts/create_package.py` çalıştırma)
- ❌ Username/enqueue **lock silme**
- ❌ **System change option** değiştirme

## ✅ KATEGORİ D — Z'Lİ OBJE YARATIRKEN/DEĞİŞTİRİRKEN ZORUNLULAR

- ✅ SAP'ye **TR (Türkçe) login** ol — `sap-language=TR` (yoksa metinler boş kalır)
- ✅ Obje **deskripsiyonu/title TR olarak DOLU** yarat (boş bırakma)
- ✅ Tüm **4 field label** (short=10, medium=20, long=40, heading=55) **TR olarak TAM** yaz
- ✅ Message class mesajları **TR olarak yaz** (selfexplanatory veya açıklamalı)
- ✅ DTEL/Domain `@EndUserText.label`, CDS `@EndUserText.label` **TR**
- ✅ Activate ÖNCE doğrula: label'lar gerçekten kaydedildi mi? (REST GET ile kontrol)

## YAPILMASI GEREKİYORSA — OPERATÖRE SORMA PROTOKOLÜ

Yukarıdaki yasaklardan birini yapma ihtiyacı doğarsa:

1. **DURDUR** — Otomatik yapma
2. **AÇIKLA** — Neden gerekli? Hangi obje? Hangi alan?
3. **ÖNERİ SUN** — Alternatif yol var mı? (Append yerine custom field, custom tablo, custom enhancement vs.)
4. **KULLANICIDAN İSTE** — "X yapmam gerekiyor çünkü Y. Alternatif Z var ama uygun değil. SAP GUI'den siz yapar mısınız?"
5. **BEKLE** — Kullanıcı yapınca obje adını/değişiklik notunu sana iletir
6. **DEVAM ET** — Yeni durum üzerine kendi (Z'li) işine devam et

❌ **"Küçük bir dokunuş, kullanıcı fark etmez"** mantığı YASAK — istisna yok.

---

📖 **Detay + gerekçe:** [`governance/decisions/0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md`](governance/decisions/0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md)

---

## ⚠️ ADT-ALTYAPISI DEĞİŞİKLİĞİ — ÖNCE HIGHLIGHT'LI UYAR + ONAY (lider DAHİL)

**[L1-ADTINFRA-01]** (MUST) Aşağıdaki "kapsam" listesindeki paylaşılan ADT-altyapısı dosyalarından birini **Edit/Write etmeden ÖNCE** agent (lider DAHİL) kullanıcıya **HIGHLIGHT** bir uyarı sunar: `⚠️ ADT-INFRA (<HIGH|orta>)` etiketi + ne değişecek + neden + hangi dosya + blast-radius; ve **açık onay alana kadar BEKLER.**

**[L1-ADTINFRA-02]** (MUST-NOT) Bu onayı bir iş listesinin/çoklu-maddenin arasına gömülü tek satır olarak isteme; ADT-infra maddesi ayrıca öne çıkarılıp **tek-tek** onaylanır.

**Kapsam (HIGH — onaysız Edit/Write YASAK):**
- `scripts/sap_adt_lib.py`, `scripts/sap_sync_pull.py`, `scripts/source_drift.py` ve diğer pull/drift/aktivasyon mantığı taşıyan `scripts/*.py`
- MCP server: `mcp_servers/sap_adt/**`
- Hook'lar: `scripts/hooks/**` · Validator'lar: `scripts/validators/**`
- Kural dosyaları (AGENTS/standards/playbook/governance) — yalnız SAP-yazma/pull/aktivasyon **davranışını** değiştiren kısımlar

**Kapsam DIŞI (highlight gerekmez):** salt-okunur analiz; repo-içi uygulama kaynağı (FE/BE build, paket `.cds/.abap` iş kodu); saf dokümantasyon.

**Enforcement (ADR 0019 §5):** YARGI sınıfı — "uyarı yeterince belirgin mi" deterministik değil; ama TETİK (kapsam dosyasına Edit/Write) deterministiktir → **proaktif PreToolUse cue-hook ÖNERİLDİ** (kullanıcı onayı bekliyor) + bu kural metni + reviewer/self-check üyeliği. Coverage: tetik = kapsam glob'ları; ihlal sinyali = highlight'sız infra edit.

> **Gerekçe (somut):** 2026-06-21 — drift-fix (v1) iş listesi arasında highlight'sız/onaysız uygulandı; kanıt incelemesiyle yanlış kapsamda olduğu görülüp geri alındı. Paylaşılan altyapı + SAP-yazma yolu → sessiz değişiklik kullanıcının kontrolünü kaybettirir. Bkz. memory `feedback_adt-infra-degisikligi-once-uyar-onay`, [`feedback_arac-kod-fix-lider-isi`], ADR 0019 (gate'siz kural ≈ kuralsız).

---

## 0. SESSION BAŞLANGICI — EKRAN TEYİDİ ZORUNLU

Her yeni oturumun **ilk yanıtının** [`CLAUDE.core.md`](CLAUDE.core.md) §2'deki template'le başlamalı:

```
[Session başladı — <PROJECT_NAME>]
⛔ KESİN YASAKLAR aktif (ADR 0005): standart SAP objelerine, standart
   tablo verilerine, transport/package state'ine dokunma YASAK.
   Z'li obje yaratırken TR login + TR text zorunlu.
✓ AGENTS.md + CLAUDE.md yüklendi (L1-L4 katman mimarisi aktif)
✓ run_all_validators.py --quick: <OK | N ihlal>
✓ Aktif paket: <PKG_FULL>
✓ Son session notu: <bir satır>
✓ Mimari: ADR 0003 (4 katman) + ADR 0005 (yasaklar), kod gate'ler aktif

Devam: <kullanıcıya soru / hazır olduğun bilgi>
```

Bu format atlanırsa kullanıcı protokol'e uyulmadığını varsayar.

---

## 1. GIT WORKFLOW — ZORUNLU

**Tek branch:** Bu repo sadece `main` branch kullanır.

- ❌ `git checkout -b`, `git branch <ad>`, `git switch -c` — **yasak**
- ❌ `git worktree add`, EnterWorktree tool — **yasak**, tüm iş `<PROJECT_ROOT>`'da
- ❌ `main-backup-*` branch'lerine dokunma — güvenlik yedeği
- ❌ `git push --force[-with-lease]`, `--no-verify` — kullanıcı açıkça istemedikçe yapma
- ✅ Push öncesi **her zaman** kullanıcı onayı al ("git'e gönder" demediyse pushlama)
- ✅ Commit mesajı Türkçe yazılabilir. Net, "ne" değil "neden" odaklı.

ADR referansı: [`governance/decisions/0001-tek-branch-main.md`](governance/decisions/0001-tek-branch-main.md)

---

## 2. PROJE SKILL'LERİ — Kullanıcıdan TEYIT

| Konu | Kural |
|---|---|
| **Yeni request** | Yaratma — kullanıcıdan **request numarası iste**. **Geliştirme zaten bir requeste bağlı ise o request üzerinden DEVAM ET, yeni iste**me. |
| **Yeni package** | Yaratma — hangi package kullanılacağını **sor**. Rastgele kullanma. (Bkz. ⛔ KATEGORİ C — yasak) |
| **Yeni transport** | Yaratma — hangi TR kullanılacağını **sor**. Yeni TR otomatik açma. (Bkz. ⛔ KATEGORİ C — yasak) |
| **Yeni ABAP programı/include** | Yaratmadan önce **TITLE iste**. Ana program description'ına TITLE yaz, **include'lara TITLE + standart suffix** ekle. |
| **Yeni DDIC tablo** | Yaratmadan **ÖNCE** tasarımı kullanıcıya **göster + açık ONAY al** (onaysız `create_table` YASAK): tüm alanlar + her alanın **data element'i** + key/uzunluk. Kurallar: client alanı = **`mandt : mandt`** (DTEL MANDT; "client/abap.clnt" değil); mümkün olan her alanda **mevcut std data element** kullan (raw `abap.char(n)`'den kaçın); audit alanı varsa std §F. |

### ABAP Include TITLE Suffix Standardı

Ana program: `"<Rapor Adı>"` (örn. `"Ornek Termin Raporu"`)

Include'lar için zorunlu suffix'ler:

| Include Tipi | Suffix | TITLE Örneği |
|---|---|---|
| TOP (data declarations) | `TOP` | `"Ornek Termin Raporu - TOP"` |
| Selection screen | `SEL` | `"Ornek Termin Raporu - SEL"` |
| Module / dialog logic | `MDL` veya `O01`/`I01` | `"Ornek Termin Raporu - MDL"` |
| Form (FORM/PERFORM) | `F01` (artarak F02, F03) | `"Ornek Termin Raporu - F01"` |
| ALV logic | `ALV` | `"Ornek Termin Raporu - ALV"` |
| Class local definitions | `CL` veya `CLD` | `"Ornek Termin Raporu - CL"` |

TITLE boş veya İngilizce bırakılmaz (⛔ KATEGORİ D — Z'li obje text zorunluluğu).

### Kurulu Araçlar (Plugin) — Hangi İş → Hangi Araç

Tam envanter + kullanım: [`governance/tooling-plugins.md`](governance/tooling-plugins.md). Özet:

| İş | Araç |
|---|---|
| ABAP/CDS/RAP/DDIC | `sap-abap-dev` skill → MCP `sap-adt` / script |
| UI5 yaz (API/lint/best-practice) | `ui5` plugin (skill + `ui5-mcp-server`: `get_api_reference`, `run_ui5_linter`) |
| UI'ı tarayıcıda doğrula/ekran görüntüsü | `playwright-cli` (skill, token-verimli) / `playwright` MCP — **layout'u SAYIYLA** (bounding-box), vision değil |
| **Yapısal** kod arama/refactor (imza/AST deseni; ripgrep lexical-kör) | **`ast-grep`** CLI (`ast-grep -p '<pat>' -l <dil> <path>`, `--rewrite`) — düz metin yetiyorsa Grep |
| Python script düzenle | `pyright-lsp` |
| Commit/PR kalite | `code-review` |

⚠️ Hiçbir plugin ADR 0005 yasaklarını gevşetmez. SAP/UI5 plugin'lerinin **CAP** önerileri bizde geçersiz (ABAP RAP backend). Yeni plugin kurulunca envanteri güncelle.

### Subagent / Orkestrasyon Kararı (ne zaman kendin, ne zaman tek, ne zaman fan-out)

Subagent'ın değeri **context izolasyonu**dur: ağır işi atılabilir bir pencerede yapıp ana
context'e sadece SONUCU döner (tek subagent ≠ "kendin yapmak"). Karar:

| Durum | Karar |
|---|---|
| Önemsiz / ara-detaylar zaten lazım | **Kendin yap** — subagent indirection'ı gereksiz |
| Token-ağır, sadece sonuç lazım, **paralelleşmez** | **Tek subagent** (context izolasyonu) — veya taze-gözle/adversarial 2. bakış |
| Token-ağır **VE paralelleşir** (bağımsız parçalar) | **ÇOK subagent — paralel fan-out** (izolasyon + hız + kategori/parça-derinliği) |

⛔ **ANTİ-PATTERN:** paralelleşen bir işi (ör. N bağımsız kategori/dosya/paket taraması) **tek
subagent'a seri** verdirmek — izolasyonu alır ama hızı+derinliği kaybeder. Bağımsız parçalar varsa
**tek mesajda N Agent çağrısı** (concurrent). Bunu paralelleştirdiysen kendin de aynı işi tekrar
koşma — sonucu bekle. (Ders: tooling-radar ilk run'ı, 6 bağımsız kategori tek-subagent koşuldu →
paralel'e revize, 2026-06-13.) Bkz. [[feedback_subagent-karar-kurali]].

**Tam takım (agent teams)** — birden çok kalıcı isimli üye + tek SAP-yazıcı gateway gerektiğinde,
işletim modeli **BAĞLAYICI**: [`governance/agent-teams-operating-model.md`](governance/agent-teams-operating-model.md).
Özet: (1) ajanları **`.claude/agents/` tiplerinden** spawn et — `sap-feature`/`sap-research` SAP'ye
**tool-düzeyinde YAZAMAZ**, yalnız `adt-gateway` yazar; (2) **single-writer KOŞULLU** — takım aktifken
lider de doğrudan yazmaz, gateway'e devreder; **solo'da lider doğrudan yazar** (gateway gereksiz);
(3) gateway'i **gözlemle** — 3 deneme→ZORUNLU araştır→toplam 5→DUR+eskalasyon; sessizse output-dosyasını oku.

**(4) HERHANGİ bir alt-ajanın "YAPILAMAZ"/olumsuz raporunu KANITSIZ KABUL ETME — SORGULA (lider; BAĞLAYICI).** **Her** alt-ajan (`adt-gateway`/`bug-expert`/`backend-expert`/`frontend-expert`/`sap-research`/`general` — gateway yalnız en sık örnek) "yapılamaz / desteklenmiyor / blocker / yok / bulunamadı" derse, bunu doğru kabul edip **ona göre işlem yapma veya durma**. Önce sorgula: bu **gerçekten imkânsız mı**, yoksa **"bu ajanın elindeki araçlarla/kapsamla yapamadı/bulamadı"** mı? Ajanın tool-görünümü repo'nun gerçek kabiliyetinden DARDIR. Protokol: (a) iddiayı **repo'da ara** — aynı işi yapan mevcut `scripts/*.py` / playbook reçetesi / alternatif yol var mı (`grep`/Glob); (b) varsa ajanı o yolla **yeniden yönlendir/taze-spawn et**; (c) yoksa iddiayı **kendin canlı doğrula**, sonra kullanıcıya ilet. **Ders (2026-06-22):** gateway "SRVB description typed-tool ile değişmez" dedi → lider kabul etti; oysa `scripts/sap_set_object_description.py` tam bu senaryo için (voyage "Sefer..." düzeltme) yazılmıştı. Bu, ajan-tarafı [[feedback_dogrula-once-flag-spekulatif-blocker-yasak]]'ın **lider-tarafı tamamlayıcısı**; kök ilke = TAHMİN YASAK = kanıtlı hareket et. Bkz. [[feedback_ajan-olumsuz-donusu-kanitla-sorgula]].

### UI BUILD DONE-CRITERIA + LİDER DOĞRULAMA (ADR 0017 — Booking post-mortem)

> Booking UI'da çok fazla amatör patinaj oldu çünkü (a) çalışan kardeş deseni yerine sıfırdan yazıldı, (b) ajan "done/verified" dedi ama runtime hata ancak kullanıcı test edince çıktı, (c) lider doğrulamadan kabul etti. Bunlar **bağlayıcı**:

1. **Plumbing'i icat etme — içeriği değil (app-kopyalama DEĞİL):** Freestyle UI5+V2'nin **mekanik/plumbing** kısmı (save=sıralı `update(merge)`, nav=`to_X`, `setData` tam şekil, master-detail seçim-wiring, MERGE tarih-null) **tek-doğru-yol, uygulamadan bağımsız** → [`playbook/ui-freestyle-odata-v2.md`](playbook/ui-freestyle-odata-v2.md) **§K**'yı **referans al, sıfırdan icat etme** (icat = çözülmüş bug'ı geri getirmek). **Uygulamaya özel her şey BESPOKE yazılır** (entity/servis, alan listesi, ekran layout/grid, iş/gating kuralları, VH hedefleri, label, akış) — hiçbir ekran diğerinin kopyası değildir. Sınır: *framework-plumbing = reuse · iş-içeriği = bespoke*.
2. **"done/verified" kanıtsız KABUL EDİLMEZ** (lider): UI build için → `check_ui5_freestyle_traps.py` PASS **+ runtime smoke** (G1 playwright-cli, yoksa elle console: zero render error + ana akış). SAP yazımı için → `adt_get` active readback. "node --check OK / XML well-formed" runtime/fonksiyonel hatayı YAKALAMAZ — yeterli değil.
3. **Recon ≠ implementasyon:** Bir recon dokümanı "done" değildir. Çıkarılan kural/gating UI'a **gerçekten kodlandı mı** lider doğrular (done = tam kapsam; [[feedback_done-tam-kapsam-dogrula]]).
4. **Kör-bug YASAK:** "Kaydedilemedi" gibi opak hatada deneme-yanılma yapma → önce **gerçek hatayı** al (F12 Network/Console status+body, ya da gateway ile birebir replikte). Kanıtsız tek satır bile değiştirme.

---

## 3. SAP STANDART OBJELER — Detay (özet en üstte ⛔ bloğunda)

Detay için bu dosyanın başındaki **⛔ KESİN YASAKLAR** bloğuna ve [`governance/decisions/0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md`](governance/decisions/0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md) ADR'sine bak. Bu bölüm sadece referans amaçlıdır — kurallar üst blokta tanımlıdır.

---

## 4. DOSYA YERLEŞTİRME

| Tip | Konum |
|---|---|
| Paket-özel SAP objeleri | `ERP/<MODULE>/<PKG>/<obje-tipi>/` (cds/, classes/, programs/, structures/, tables/, functions/, ui/) |
| Paket-spesifik kurallar | `ERP/<MODULE>/<PKG>/.rules.md` |
| Paket spec/notlar | `ERP/<MODULE>/<PKG>/SPEC.md`, `SESSION_NOTES.md` |
| Modüller | `ERP/SD/`, `ERP/MM/`, `ERP/FI/`, `ERP/QM/`, `ERP/PM/`, `ERP/EWM/`, `ERP/CO/` (ADR 0004) |
| Geçici script + test | `TempScripts/` (gitignored) |
| Kalıcı utility | `scripts/` veya alt klasör (`workflows/`, `cleanup/`, `search/`, `validators/`, `utils/`) |
| Legacy referans `.txt` | Paket root'unda kalır — `.abap`/`.cds`'a rename **YASAK** |

### Obje Tipi → Klasör Eşlemesi (Somut Örnekler)

SAP objelerini local'e indirirken **varsayılan `ZAI` klasörünü KULLANMA** (deprecated, ADR 0005). Her objeyi paket adıyla eşleşen klasöre, obje tipine göre alt klasöre kaydet:

| Obje Tipi | Klasör | Örnek (ZSD001_CLC) |
|---|---|---|
| Class | `classes/` | `ERP/SD/ZSD001_CLC/classes/ZCL_ZSD_ORDER_DPC_EXT.abap` |
| CDS view (kaynak) | `cds/` | `ERP/SD/ZSD001_CLC/cds/ZSD001_C_SO_ITEM.cds` |
| CDS TD spec | `cds/` | `ERP/SD/ZSD001_CLC/cds/<obje>.md` (yan yana .cds + .md) |
| Function module / FUGR | `functions/` | `ERP/SD/ZSD001_CLC/functions/ZSD001_FM_SO_CREATE.abap` |
| Structure | `structures/` | `ERP/SD/ZSD000_CLC/structures/ZSD000_S_BP_BASIC.ddls.asddls` |
| Tablo / Z table | `tables/` | `ERP/SD/<PKG>/tables/<obje>.abap` |
| Program / include | `programs/` | `ERP/SD/ZSD001_CLC/programs/ZSD001_P_SCHED_ITEMS.abap` |
| Fiori UI app | `ui/<app_adi>/` | `ERP/SD/ZSD001_CLC/ui/order_app/` |
| Auth check | `auth/` | `ERP/SD/<PKG>/auth/<obje>` |
| Sprint planları, FS doc'u | paket root | `ERP/SD/<PKG>/SPEC.md`, `SESSION_NOTES.md` |
| FS/TS txt doc | `docs/` | `ERP/SD/<PKG>/docs/FS.txt`, `TS.txt` |

**⛔ ZAI YASAK:** Hiçbir obje `ERP/ZAI/` veya benzer "default" klasöre düşemez. Paket adı belirsizse **kullanıcıya sor**.

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
python scripts/validators/run_review.py --task <task_type> --artifact <path>
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

Bir SAP source objesini (CDS/BDEF/SRVD/class/DDL — `ERP/<pkg>/` altı, source uzantısı) değiştirme amacıyla **üzerinde çalışmaya başladığın AN — yani onu İNCELEMEDEN/ANALİZ ETMEDEN ÖNCE** (edit anından çok daha erken) canlı güncel halini çek:

```powershell
python scripts/sap_sync_pull.py <NAME> --type <ddls|bdef|srvd|class|structure|...>
```

(seans-bazlı, obje başına 1×; `--session` SessionStart marker'ından otomatik; SAP erişilemezse `--offline`).

**Neden ANALİZDEN önce (edit'ten değil):** bayat koda göre analiz edersen değişiklik planın **yanlış/uygunsuz** çıkar; edit anında çekmek GEÇ kalır (analizini zaten eski koda yaptın, plan kirlenmiş olur). Tazelik bu yüzden **görev başında, okuma/analizden önce** sağlanır. (working-tree ≠ canlı her edit'te doğal → eski M1 pre-push drift-block kaldırıldı; başkasının canlıda yaptığı belgelenmemiş değişikliği ezme riski baştan-taze ile düşer.)

- **PreToolUse(Edit/Write) hook = YALNIZ BACKSTOP** (`scripts/hooks/pull_before_edit.py`): analiz-anında gate EDEMEZ (edit choke-point'i geç kalır) — proaktif pull'u unutursan bayat SAP-kaynak edit'ini bloklar + komutu söyler. **Asıl disiplin = proaktif görev-başı pull**, hook sigortadır.
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
| Sprint geçiş | `scripts/sprint_gate_check.py` | populate_*.py / spec değişikliği |
| TD spec varlık | `scripts/td_spec_check.py` | populate_cds_views.py pre-flight |
| Namespace whitelist | `populate_cds_views.py::validate_sql_view_names()` | populate_cds_views.py pre-flight |
| Paket .rules.md varlık | `scripts/validators/check_package_rules_present.py` | run_all_validators |
| Paket naming regex | `scripts/validators/check_package_naming.py` | run_all_validators |
| Obje paket sınırı | `scripts/validators/check_object_in_correct_pkg.py` | run_all_validators |
| Script playbook ref | `scripts/validators/check_scripts_documented.py` | run_all_validators |

Tüm validator'lar: `python scripts/validators/run_all_validators.py`

Detay: [`governance/decisions/0003-layered-rule-architecture.md`](governance/decisions/0003-layered-rule-architecture.md)
