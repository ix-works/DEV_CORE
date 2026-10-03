---
applies_to: [s4_private]
---
# ADT — MCP Tool Kullanımı (Coordinator için)

> **Bağlam:** [ADR 0007](../governance/decisions/0007-sap-adt-mcp-server.md). MCP server `mcp_servers/sap_adt/` altında. 11 typed tool, server-side ADR 0005 guardrails.

## Ne Zaman MCP Tool, Ne Zaman Script?

| Senaryo | Çağrı |
|---|---|
| Tek bir domain/DTEL/struct yarat | `adt_domain_create` / `adt_dtel_create` / `adt_struct_create` (composite) |
| Mevcut objeyi oku (source/metadata) | `adt_get` |
| Var olan objeye source push (CDS update gibi) | `adt_push_source` + `adt_activate` |
| Sadece aktive et | `adt_activate` |
| İsim/wildcard ile obje ara | `adt_search_objects` |
| Aktif transportları listele | `adt_transport_list` |
| Lock kontrol | `adt_lock_check` |
| **CSV'den toplu yaratım** (10+ obje) | `python scripts/populate_*.py` (mevcut script'ler — batch + audit) |
| Sprint gate, TD spec check, validator | `python scripts/sprint_gate_check.py`, `td_spec_check.py`, vd. |

**Karar kuralı:** Tek obje + atomik flow → MCP. CSV-driven batch → script. Pre-flight validator → script.

## Composite Tool Davranışı

Her composite (`adt_*_create`) şu adımları sırayla yapar, sonuçları `steps` field'ında raporlar:

```
1. Guardrails check (Z/Y prefix, transport, TR text, labels)
2. pre_check    → adt_get ile zaten var mı? Varsa already_exists
3. create       → SAPClient.create_<x>() (shell + source set)
4. activate     → SAPClient.activate_object()
5. verify       → get_object_metadata ile son durum teyit
```

**Failure modları:**

| Adım | Hata | Davranış |
|---|---|---|
| Guardrail | code: ADR_0005_A/C/D | İstek SAP'a hiç gitmez, hata döner |
| pre_check | already_exists | Reject, kullanıcı kararı bekler |
| create | SAPADTError | Şey yaratılmadı, hatayı döner |
| activate | activation_failed | **Obje inactive kaldı, otomatik delete YOK** — kullanıcı düzelt-aktive-et veya manual delete |
| verify | mismatch | activated:true ama verified:false (nadir, raporla) |

Auto-rollback yok — bu kasıtlı (ADR 0007). Inactive obje değerli olabilir, coordinator/kullanıcı karar verir.

## Server-Side Guardrails (ADR 0005)

Tool çağrısı SAP'a gitmeden önce reject edilebilir:

| Code | Sebep | Düzeltme |
|---|---|---|
| `ADR_0005_A` | İsim Z/Y ile başlamıyor | Customer namespace kullan |
| `ADR_0005_C` | Transport boş | `adt_transport_list` ile aktif transport seç, kullanıcıya doğrulat |
| `ADR_0005_D` | Description veya 4 label'dan biri boş | TR text doldur (<LEGACY_SOURCE> SEVKEMRI'den çıkar — tahmin YASAK) |

## Tipik Patterns

### Pattern 1 — Tek domain yarat

```
1. adt_transport_list → modifiable transport seç (kullanıcı onayı)
2. adt_get(name='ZSD001_D_DEMO', object_type='doma') → exists:false bekle
3. adt_domain_create(
     name='ZSD001_D_DEMO',
     datatype='CHAR', length=10,
     description='Demo Durum Kodu',
     package='ZSD001_CLC',
     transport='<TRANSPORT>',
   )
4. steps.verify.ok kontrol → reviewer'a rapor
```

### Pattern 2 — Mevcut CDS update

```
1. adt_get(name='ZSD001_DDL_X', object_type='ddls') → source al
2. Local'de değiştir → reviewer pre-flight (run_review.py)
3. adt_push_source(name='ZSD001_DDL_X', object_type='ddls', source=<new>, transport='<TRANSPORT>')
4. adt_activate(name='ZSD001_DDL_X', object_type='ddls')
5. adt_get tekrar → verify
```

### Pattern 3 — Struct yarat (Sprint 6 — REVİZE EDİLDİ 2026-05-14)

`adt_struct_create` SAP'de **placeholder bırakıyor** (`component_to_be_changed:abap.string(0)`).
Tool create+activate OK döndürür ama field'lar yazılmaz. Doğru pattern: shell olarak yarat,
sonra **`adt_push_source(object_type='structure')`** ile full DDL push.

```
1. sprint6_adapt_struct.py ile lokal .ddls.asddls üret
2. Manuel düzeltmeler: non-ZSD001 Z ref'leri (<LEGACY_SOURCE> zsd_007_t_*, zsd_007_sh_*,
   zsd_d_* → bizim karşılıkları veya SAP standart), /sapapo/* → uygun Z DTEL
3. run_review.py --task struct_creation → PASS bekle
4. SAP DTEL audit: kullanılan tüm Z DTEL'lerin domain'i (BU_PARTNER, KNOTN, LIFNR,
   VERSART vs.) FK hedef tablo alanıyla uyumlu mu kontrol et
   → uyumsuzsa DELETE + CSV doğru ile populate_dataelements + activate cascade
5. adt_struct_create(name=..., fields=[...], description='TR', package='ZSD001_CLC',
                     transport='<TRANSPORT>')   # artifact_path VERME (MCP içi timeout)
   → ok=False, verify=False bekleniyor — shell yaratıldı
6. adt_push_source(name=..., object_type='structure', source=<full DDL>,
                   transport='<TRANSPORT>', skip_reviewer=True)
   → ok=True, activated=True
7. python scripts/validators/check_sap_struct_consistency.py <local artifact>
   → "OK — N alan, active"
```

**Kaçınılması gereken pattern'ler:**

| Pattern | Sorun |
|---|---|
| `adt_struct_create` tek başına | SAP'de placeholder kalır, tool yalan söyler |
| `adt_struct_create(artifact_path=...)` | MCP içi reviewer subprocess 120s timeout |
| `adt_push_source(object_type='tabl')` struct için | "Invalid lock handle" 423 hatası |
| `adt_post_shell` ile struct yaratma denemesi | `Unsupported object type: TABL/DS` |
| MCP `verify: {ok: true}`'ye güvenip post-check atlama | Old behavior sadece existence kontrol ediyordu, content kontrol etmiyordu. Bugün `composite._activate_and_verify` aktivasyon hükmünü `sap_client.activate_object` → `sap_adt_lib.activate_object` `success`'inden alır (kanonik `aktivasyon_govde_hukmu` + worklist sondası, Q187/Q188); `version="active"` metadata kontrolü bunun üstüne EK şarttır, tek başına kanıt değildir (boş kabuk da "active" der). İçerik doğrulaması hâlâ çağıranda: aktif kaynağı çek, bayt/içerik kıyasla. Kod değişince MCP server restart şart |

**T10 bulgu: DTEL/CSV domain consistency** — Sprint 1B'de bazı DTEL'ler CSV'nin söylediği SAP std
domain yerine Z domain ile yaratılmıştı. Foreign key hedef alanla domain mismatch → struct
aktive olmuyor. `check_sap_struct_consistency.py` placeholder yakalar; FK problemi struct
activate çıktısında "X and Y point to different domains" mesajı ile gelir, audit edip
DTEL force-recreate gerek.

## Setup ve Bağımlılık

- `pip install -r mcp_servers/sap_adt/requirements.txt` (`mcp`, `requests`, `python-dotenv`)
- `.mcp.json` (repo kökü) → Claude Code'un standart project-level MCP config dosyası, `claude mcp add` ile yaratılır. Repo'da paylaşılır.
- Claude Code'u tamamen kapatıp açtıktan sonra `/mcp` veya `claude mcp list` ile `sap-adt: ✓ Connected` görmen lazım
- `.conn_adt` lokal — credentials her makinede ayrı
- Diğer geliştiriciler: **proje kökünden** `python core/scripts/team_setup.py` tek komutla setup
  *(⛔ 2026-09-03 düzeltmesi: burada eskiden `python scripts/team_setup.py` yazıyordu. Ölçüldü — script **hiçbir projede** `scripts/` altında YOK (dört proje kökünün dördü de: 4/4 yok); yalnız çekirdekte var ve projeye `core/` junction'ı üzerinden görünür. Yayınlanmış çalışmayan komut, okuyanı kendi kurulumunu suçlamaya iter.)* (`.mcp.json` git pull'la geldiği için ek adım yok)

## Reviewer (ADR 0006) ile İlişki

Reviewer **MCP'nin içine entegre.** Coordinator manuel çağrı yapmaz — composite tool veya `adt_push_source` çağrılınca otomatik tetiklenir.

**Coordinator akışı (tek çağrı):**

```
adt_struct_create(name, fields, artifact_path='ERP/SD/.../X.asddls', ...)
   ↓
  [0. adım] reviewer otomatik çalışır (run_review.py --task struct_creation --artifact <path>)
              BLOCKER → tool reject eder, payload: {ok:false, error:'reviewer_blocker', reviewer:{...}}
              WARNING → devam, response'da reviewer field'ı taşınır
              PASS    → devam
   ↓
  [1. adım] MCP guardrail (Z/Y prefix, transport, TR text)
   ↓
  [2-4. adım] create + activate + verify
```

**Reviewer ne zaman tetiklenir:**

| MCP tool | Reviewer task | Tetikleyici |
|---|---|---|
| `adt_struct_create` | `struct_creation` | `artifact_path` parametresi verildiyse |
| `adt_domain_create` | (henüz validator yok → SKIP) | aynı |
| `adt_dtel_create` | `dtel_creation` (`check_dtel_creation_labels`, BLOCKER; `_reviewer.py` `COMPOSITE_TOOL_TO_TASK`) | aynı *(2026-09-13 düzeltmesi: bu satır "henüz validator yok → SKIP" diyordu; görev 2026-08-29'da bağlandı)* |
| `adt_push_source` (object_type='ddls') | `cds_update` | otomatik (source text → temp file) |
| `adt_push_source` (object_type='tabl') | `table_update` | otomatik |
| `adt_push_source` (object_type='fugr') | ⛔ **KAYITLI İSTİSNA (Q308)**: görev YOK → SKIP | Bu push yalnız **FG ana include**'unu yazar (`/functions/groups/<fg>/source/main` = `FUNCTION-POOL` satırı). **FM gövdesi** `set_function_module_source` ile yazılır: MCP aracı yok, **reviewer yok** ([`adt-fugr-functions.md` §2b](adt-fugr-functions.md)). `func`/`function` push'u `get_object_url` ValueError ile fail-closed. **FM yazmadan önce elle:** `run_review --task class_push --artifact <fm>.abap` + `adt_syntax_check`. Beklenen tablo (ölçüldü: 10 FM/FUGR artefaktı): **BLOCKER 0**, 10/10 **WARNING**. `check_abaplint` `measured=false` WARNING'i **beklenen gürültüdür** (FM'yi lintlemez). Anlamlı tek sinyal `check_released_objects`'tir (3/10 bulgu). Diğer dört validator'ın tetikleyici deseni FM'de yok (METHODS / AMDP / DOCU runner / API marker). Oradaki "tarandı" satırı uygulandı demek DEĞİLDİR. Pin: `tests/fixtures/reviewer_tip_kapsam` F1-F5 |
| `adt_push_source` (diğer) | (validator yok → SKIP) | otomatik |

`adt_push_source`'ta `skip_reviewer=True` flag'i var ama acil durum dışında **kullanma**.

**Manuel CLI hala kullanılabilir:**
- Lokal-only draft kontrolü (SAP'a yazma niyeti yok)
- Yeni validator geliştirirken test
- CI/pre-commit hook (gelecekte)

**Üç ayrı katman:**

| Katman | Ne kontrol | Bypass |
|---|---|---|
| Reviewer (ADR 0006) | Lokal draft kalitesi — namespace pattern, validator chain | `skip_reviewer=True` (acil) |
| MCP guardrails (ADR 0005) | REST parametreleri — Z/Y prefix, TR text, transport | Yok — server-side hardcoded |
| SAP'in kendi validasyonu | Aktivasyon, syntax, FK | n/a |

Katmanlar overlapping değil tamamlayıcı — biri kaçırırsa diğeri yakalar.

## Tool SEMANTİĞİ — adı/dokümanı değil, ÖLÇÜLEN yan etkisi belirler

### `adt_syntax_check` **SALT-OKUNUR DEĞİLDİR** (ölçüm 2026-07-31)

Adı "check" olmasına rağmen bu tool bir **aktivasyon** ucuna gider:

```
POST /sap/bc/adt/activation?method=activate&preauditRequested=true
```

**Ölçülen davranış (bu sistem):** `preauditRequested=true` **onurlandırılmıyor** — bekleyen
**inaktif** sürüm TEMİZSE tool objeyi **AKTİVE EDİYOR**. Kanıt: çağrı öncesi
`adt_inactive_objects` = **1**, çağrı sonrası = **0**; `?version=active` ile okunan kaynak
push edilen kaynağa **eşitlendi**. Hatalıysa aktive etmiyor (`"Activation was cancelled"`).
⇒ Gerçek semantiği: **"hatasızsa aktive et"**.

**⚠ Araç KOD GÖNDERMEZ.** Çağrının gövdesinde yalnız **obje adı/URI** gider; SAP o ad altında
**o an bekleyen sürümü** devreye alır. Yani elindeki kaynağı değil, **sunucudaki bekleyen
sürümü** aktive edersin. Somut risk: bilinçli bekletilen bir aktivasyon (co-activation sırası,
def/impl include çifti, gözden geçirilmeyi bekleyen inaktif sürüm) varken çağırmak **sırayı bozar**.

**Sonuç (MUST):** `adt_syntax_check` **yazma yetkili** sayılır → yalnız **tek-yazıcı (gateway)**
rolünün allowlist'inde bulunur; "read-only" kovasına **konmaz**. Aksi hâlde single-writer
ilkesi sessizce delinir (bkz. `lessons-learned.md` PATTERN #20).

### `adt_push_source` ZATEN aktivasyon-öncesi syntax-check yapar

Ayrı bir "zararsız ön-derleyici turu" **kurmaya gerek YOK** — push bunu içeriyor:

- Upload sonrası / aktivasyon öncesi syntax-check koşar; **hatalıysa AKTİVE ETMEZ** ve hataları
  **satır/kolon** bilgisiyle döndürür.
- Kanıt: `scripts/sap_client.py` →
  `[BLOCK] Aktivasyon-oncesi syntax-check BASARISIZ -> AKTIVE EDILMEDI` (`syntax_precheck='failed'`
  + `syntax_errors`); MCP yüzeyi `mcp_servers/sap_adt/tools/atom.py` → `syntax_precheck == "failed"`
  ise `ok=False` + `syntax_errors` yanıta çıkarılır (nested kalmaz).
- Kapsam sınırı: preaudit **class/interface** push'unda koşar; `prog`/`fugr`/`include` DIŞLANMIŞTIR
  (standalone include preaudit FAKE — `checklists/bug-checklist-backend.md` BE-46).
- **Ölçülemedi ≠ temiz (Q312):** ön-kontrol koşmazsa (`valid=None` · kontrol istisnası yutuldu ·
  çağrı istisnası) push **aktivasyona devam eder** — engel değildir — ama sonuç
  `syntax_precheck='olculemedi'` + `sozdizimi_sebep` taşır. MCP yanıtı üst seviyede `syntax_precheck`
  + `syntax_precheck_notice` verir (`ok` değişmez); CLI `push_object.py` hükmün yanına
  `[UNVERIFIED] PUSH SOZDIZIMI ON-KONTROLU OLCULEMEDI` basar. Korpus:
  `tests/fixtures/push_onkontrol_olculemedi`.

⇒ Doğru sıra: **push → (hata varsa dur, düzelt) → `adt_activate` → readback**. Araya elle bir
syntax-check turu eklemek hem gereksiz hem — yukarıdaki semantiği yüzünden — **yan etkilidir**.

## Tool ayrıntı ekleri — MCP açıklama bütçesi (2026-10-03)

Claude Code 2.1.280+ MCP tool açıklamasını `CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH` = **2.048
karakterde keser** (bu oturumda canlı görüldü: `adt_sql_query` açıklaması `… [truncated]` ile
bitiyordu). Kesilen kısım modele **hiç ulaşmaz** — ⛔ uyarıların bir kısmı tam orada duruyordu.
Ölçüm, FastMCP'nin çalışma zamanında ürettiği `Tool.description` üzerinden yapıldı (ham
`__doc__`, girinti DAHİL — AST'nin `get_docstring`'i girintiyi siler ve ~%5 düşük ölçer):

| Tool | Önce | Sonra |
|---|---:|---:|
| `adt_sql_query` | 7.008 | 1.986 |
| `adt_grep_source` | 4.323 | 1.648 |
| `adt_inactive_objects` | 2.404 | 1.284 |
| `adt_transport_list` | 2.388 | 1.120 |
| `adt_classrun` | 2.318 | 1.131 |
| `adt_activate` | 2.250 | 1.389 |

**Desen (yeni tool yazarken de):** açıklamanın ilk satırları **kural/yasak özeti**dir; vaka
anlatısı, tarihçe ve ayrıntılı dönüş sözleşmesi buraya gelir, açıklamada tek satırlık atıf
kalır. Aşağıdaki "önceki tam açıklama" blokları 2026-10-03'e kadar MCP açıklaması olan metnin
**birebir** kopyasıdır (bilgi kaybı yok); yeni ölçümler blokların ÜSTÜNDE yazılıdır.

### `adt_sql_query` — ayrıntı

**255 karakter satır sınırı (ölçüldü 2026-10-03, DEV, yalnız T000 SELECT; son kodda iki kez):**

| Girdi | Sonuç |
|---|---|
| 288 kr tek satır, 14 `OR` terimi, otomatik kırma KAPALI | **400** `"O" is invalid here (due to grammar).` — 255. karakter `OR`'un `O`'su |
| aynı sorgu, otomatik kırma AÇIK (253 + 34 kr) | 200 |
| aynı sorgu elle iki satır (kontrol) | 200 |
| 252 kr tek satır, **13 `OR`** terimi | 200 |
| 260 kr'lik literal kendi satırında (kırma KAPALI) | **400** `Yalnızca bir SELECT deyimi geçerli.` |
| 291 kr, kırma `COUNT(` ⏎ `* ) AS cnt …` (önek YOK) | **400** `"INTO" is invalid here (due to grammar).` |
| aynısı, devam satırı ` * )` (tek boşluk önekli — araç bunu yapar) | 200 |

⇒ Freestyle ucu her satırı 255. karakterde KESER; hata mesajı kesimin düştüğü kelimeyi gösterir,
sebebi göstermez. `sap_adt_lib.sql_satirlarini_kir` (`run_query` + freestyle'a POST eden üç kardeş:
E070 fallback · ghost-transport sondası · `sprint_gate_check._query_sap`) uzun satırı literal
(`'…'`, `` `…` ``) ve satır-sonu yorumu (`"`) DIŞINDAKİ boşluktan kırar; freestyle sütun-1 `*`'ı
TAM-SATIR YORUMU saydığı için `*` ile başlayan devam satırına tek boşluk öneki koyar (uzunluğa
dahil; >255 `*` yorum satırı bölünemez → aynı hata); tek atom 255'i aşıyorsa
`SQLSatirKirilamadi` fırlar ve istek GİTMEZ (yukarıdaki son satır: o sorgu zaten 400'dü). Ayrıca
`run_query` 400 gövdesini artık kırpmıyor — 255 vakasının gövdesi 563 bayttı, `[:500]` XML'i
bozuyor ve `sap_error.message` sebep yerine ham XML başını gösteriyordu.
Korpus: `tests/fixtures/sql_satir_kirma`.

⛔ **ÇÜRÜYEN TEŞHİS:** aşağıdaki blokta madde 1 (*"5'ten fazla `OR` → 400 · WHERE'i 5'erli
parçalara böl"*) ve `adt_transport_list`'teki `E070×E071` JOIN / `IN (…)` 400'leri büyük
olasılıkla bu sınırın yansımasıdır (uzun WHERE = uzun satır). 13 `OR` ≤255 karakterde koştu.
`E070×E071` vakaları yeniden ölçülmedi (**DOĞRULANAMADI** — bu turda yalnız T000 serbestti).
Aynı kökü taşıyan ders: `claude/memory-seed/feedback_adt-sql-query-400-sebebi-where-terim-sayisi.md`.
⚠ **Her 400 bu değildir:** kısa ama 400 veren vakalar ayrı sebeplidir (ör. iki terimli
`WHERE vbeln = 'X' AND vbtyp = 'E'` — açıklanmadı; blokta madde 2–8). 400'de önce
`sap_error.message`. Çok baytlı karakterde sınırın bayt mı karakter mi olduğu ÖLÇÜLMEDİ.

Önceki tam açıklama (2026-10-03'e kadar MCP açıklamasıydı; birebir):

````text
WHERE/JOIN/aggregate destekli serbest OpenSQL **SELECT** çalıştır — READ-ONLY.

`adt_table_read` yalnız `SELECT * FROM tablo` yapar (WHERE yok); bu tool ADT Data
Preview freestyle (`/datapreview/freestyle`) ile tam OpenSQL SELECT'i koşar:
WHERE, JOIN, GROUP BY, COUNT/SUM (başka kolonla birlikte aggregate'e ALIAS şart — madde 4).
INTO/UP TO **YAZMA** — SAP kendi ekler.

Guard'lar:
  • **SELECT-only (ADR 0005-B):** SELECT/WITH ile başlamalı; yazma/DDL keyword'ü
    (INSERT/UPDATE/DELETE/MODIFY/DROP/...) tespit edilirse REDDEDİLİR. (Data Preview
    zaten server-side salt-okuma; bu tool-seviyesi ikinci katman.)
  • **PII (ADR 0011):** FROM/JOIN tabloları çıkarılır; DEV serbest, QA/PRD'de hassas
    tablo (KNA1/PA*/banka/TCKN...) için `acknowledge_risk=True` + onay kelimesi ZORUNLU.

⚠ **HTTP 400 = "sorgu kabul edilmedi", "tablo erişilemez" DEĞİL** (ölçüldü 2026-08-17,
iki ajan bağımsız yaşadı). "400 ⇒ tabloya bakamıyorum" teşhisi bu araçta YANLIŞTIR ve
doğrudan *"bulunamadı ≠ yok"* ihlaline götürür. Ölçülmüş üç 400 sebebi:

  1. **UZUN `WHERE`.** Uzun `IN (...)` listesi ya da **5'ten fazla `OR`** → 400.
     Çözüm (iki ajan da böyle tamamladı): WHERE'i **5'erli parçalara böl**, sonuçları
     çağıran tarafta birleştir. (Kardeş ölçüm, `adt_transport_list:138`: `E070×E071`
     JOIN + `E07T` tek sorguda 400; `IN ('a','b')` listesi de 400 verebilir.)
  2. **VAR OLMAYAN KOLON ADI TAHMİNİ.** `DD30L` sorgusu 400 döndü; sebep erişim değil,
     **tahmin edilen kolon adıydı**. ⇒ Kolon adını TAHMİN ETME: önce `SELECT *` ile
     (küçük `row_limit`) kolonları KEŞFET, sonra daralt.
  3. **ABAP anahtar-kelime çakışması (bağlama göre).** `tadir`'da `object`, `seoclass`'ta
     `state` kolonu 400 verdi; kolon çıkarılınca sorgu koştu. ⚠ **Genel bir yasak DEĞİL** —
     aynı turda `E071` `object` kolonuyla sorgulanabildi ve bu modülün kendi
     `adt_inactive_objects`'i bugün `SELECT obj_name, object, delflag FROM tadir` koşuyor.
     **Kapsamı ÖLÇÜLMEDİ.** 400 alırsan şüpheli kolonu çıkarıp tekrar ölç.

⚠ **SAP'NİN 400/500 GÖVDESİ ARTIK `sap_error` ALANINDA** (Q304, 2026-09-13). 2026-09-13
öncesi bu araç gövdeyi TAŞIMIYORDU (ölçüldü: `client_log` yalnız `[ERROR] SQL query error:
[400] Failed to run query`; *"…must have an alias name"* sebebi hiçbir alanda yoktu).
Şimdi `sap_client.run_sql_query` hata dalı `SAPADTError.response_text`'ten
`last_sql_error = {status_code, message, body_excerpt}` üretir; araç bunu `sap_error`
olarak döndürür ve `message`'a `SAP: <sebep>` ekler. Ölçülmüş gövde biçimleri: 400 → XML
`exc:exception/message` · aralıklı 500 → HTML `<title>` (*Application Server Error*).
`body_excerpt` ilk 500 bayttır. ⇒ 400'de refleks: önce `sap_error.message`'ı oku, aynı
sorguyu körlemesine TEKRARLAMA; aşağıdaki ölçülmüş biçimlerle **daralt** (tek değişken).

⚠ **ÖLÇÜLMÜŞ BİÇİM SINIRLARI (Q274 — kayıt 2026-09-08; canlı yeniden ölçüm 2026-09-13,
DEV, yalnız SELECT; her satır en az 2 çağrı; sebep metinleri SAP gövdesinden):**

  4. **Aggregate başka kolonla birlikteyse ALIAS ŞART.** `SELECT lgnum, COUNT(*) FROM likp
     GROUP BY lgnum` → **400**, gövde *"all expressions in the projection list must have
     an alias name"*. Aynısı `COUNT(*) AS cnt` ile → **200**. ⇒ Sebep `GROUP BY` DEĞİL,
     alias'sız ifade; değer başına ayrı `COUNT` koşmaya gerek yok. Tek başına `COUNT(*)`
     alias'lı da alias'sız da 200.
  5. **Kolon-kolon karşılaştırmada sağ taraf `tablo~kolon` yazılır.** `WHERE vrkme <> meins`
     (ve `= meins`) → **400**, gövde *"The variable "MEINS" must be escaped using "@""* —
     çıplak ad host değişkeni sanılıyor. `WHERE vrkme <> lips~meins` ve
     `WHERE lips~vrkme <> lips~meins` → **200**. Kolon-literal karşılaştırma zaten 200.
  6. **Aralıklı 500, ardından "Session Timed Out" 400 — SORGUYA AİT DEĞİL.** Başka
     çağrılarda 200 dönen sorgular (`SELECT land1 FROM t005`, `SELECT * FROM t320`) tek
     seferlik **500** döndü (gövde SAP mesajı değil, HTML *"Application Server Error"*);
     iki vakada da HEMEN SONRAKİ çağrı **400** + gövde *"400 Session Timed Out"* verdi,
     bir sonraki normale döndü. ⇒ 500'den sonraki ilk 400'ü "sorgu reddedildi" diye okuma
     (yukarıdaki *"400 = sorgu kabul edilmedi"* kuralının ölçülmüş istisnası); aynı sorguyu
     BİR kez tekrarla.
  7. **KIRPMA (Q304 ile GÖRÜNÜR).** `row_limit=10` ile `SELECT LAND1 FROM T005` →
     `row_count:10`, SAP `totalRows` **249**. Araç artık `truncated` ve `total_rows` (SAP
     `totalRows` aynen) döndürür. `truncated` KESİNDİR: araç SAP'den `row_limit + 1` satır
     ister, fazlası gelirse `true` der ve sondayı atar. Eskiden elde yalnız
     `row_count == row_limit` vardı ve bu bir TAHMİNDİ: tam `row_limit` kadar satırı olan
     sonuç da aynı görünürdü. ⚠ `totalRows` sonuç satırı sayısı DEĞİLDİR: aggregate
     sorguda alttaki satır sayısıdır (ölçüldü: `SELECT COUNT(*) AS cnt FROM t005` → 1 satır,
     `totalRows` 249) ⇒ `truncated` ondan TÜRETİLMEZ. Sayı gerekiyorsa `row_limit`'i yükselt
     ya da `SELECT COUNT(*) …` koş (kayıttaki vaka: `row_limit=300` → tam 300, gerçek 994).
  8. **Namespace'li ad TIRNAKSIZ yazılır.** `FROM /scwm/aqua` ve `FROM /SCWM/AQUA` → 200;
     `FROM "/SCWM/AQUA"` → **400** (gövde login dilinde: geçersiz sorgu dizilimi).

  ⓘ **2026-09-08'de ölçülüp 2026-09-13'te TEKRARLANAMAYANLAR — kural DEĞİL:**
  `COUNT(*) AS CNT` → 500 (bugün 6/6 çağrı 200) · belirli bir alanda `<>` → 400
  (`I_EWM_HANDLINGUNITHDR` `handlingunitindicator <> 'A'` bugün 2/2 200; `=` ve `<>`
  sayıları toplamla tutarlı) · `SELECT * FROM T320` → 400 (bugün 8/8 200; bir kez 500 =
  madde 6) · "terim bütçesi" (7 alan + 1 WHERE → 400, 14 alan → 500) — bugün `lips`'ten
  4/6/7/8/14 alan + 1 WHERE her biri 2/2 200. Kayıttaki vakaların madde 6'nın aralıklı
  500/oturum ikilisi olup olmadığı **DOĞRULANMADI**.

Args:
    query: OpenSQL SELECT. Ör: "SELECT msgnr, text FROM t100 WHERE arbgb = 'ZSD001' AND sprsl = 'T'".
    row_limit: Maks satır (default 100).
    acknowledge_risk / approval_text: QA/PRD hassas-tablo için (ADR 0011).

Returns:
    {ok, query, row_count, row_limit, total_rows, truncated, truncated_notice?, columns,
     rows: [{KOLON: değer}, ...], executed?, client_log}
    veya {ok: false, error, message, sap_error?} (SELECT-değil / yazma-keyword /
    **sorgu KOŞMADI**; `sap_error` = {status_code, message, body_excerpt} — Q304)
    veya guardrail_violation.
    ⚠ `row_count: 0` YALNIZ `ok: true` iken "0 satır" demektir. Sorgu SAP'de düşerse
    `ok: false` + `error: "sorgu_kosmadi"` döner (sebep `message`+`client_log`) — 0 satır
    ile başarısızlık artık AYIRT EDİLEBİLİR (2026-08-19).
    Satırları DAİMA `rows`'tan oku (kolon-adı→değer eşlemeli; hizalama-güvenli).
````

### `adt_grep_source` — ayrıntı

Önceki tam açıklama (2026-10-03'e kadar MCP açıklamasıydı; birebir):

````text
Paket/obje kapsamında ABAP **KAYNAK-METİN** regex arama — READ-ONLY.

`adt_where_used` "beni kim referanslıyor" der; bu tool "bu metin/pattern nerede geçiyor"
der (tamamlayıcı). Kaynağı indirip satır-satır regex. Token-ekonomisi için `max_objects`
ve toplam 500 eşleşme sınırlı — sınıra ulaşılırsa `truncated_*` işaretlenir (sessiz-kesme yok).

Args:
    pattern: Python regex. package: paket adı (kapsam). objects: "NAME" veya "NAME:type"
             virgüllü liste (package'a alternatif; tip yazımı SERBEST — `FUGR`/`fugr`/
             `FuGr`/`functiongroup` aynı şeydir, `_grep_tip_normalize` ile `package=`
             dalının sözlüğüne çevrilir). object_types: paket-taramada tip filtresi
             (CLAS/PROG/INTF/DDLS/FUGR/BDEF). max_objects: taranacak maks obje. ignore_case.

⛔ 2026-08-28 (C-04) — "EŞLEŞME YOK" ile "OKUYAMADIM" ayrı şeylerdir. Eskiden okunamayan
obje `if not src: continue` ile SESSİZCE düşüyordu: ne sayılıyor ne raporlanıyordu.
Çağıran `match_count: 0` görüp "bu pakette geçmiyor" diye KARAR veriyordu (ölçülmüş
vaka: kuyruk Q106 + `playbook/lessons-learned.md` PATTERN #19/#20). Artık kapsamdan
düşen her obje **makinece okunur** biçimde döner:
  `skipped_objects[{object, type, reason, detail}]` — sebep sınıfları:
    `type_filtered`    → `object_types` filtresi dışladı (ör. varsayılanda FUGR yok)
    `type_unsupported` → grep'lenebilir tip değil (TABL/DTEL/DOMA/FUNC…)
    `max_objects`      → `max_objects` sınırının dışında kaldı
    `read_failed`      → `adt_get` hata döndü (HTTP/parse/timeout)
    `not_readable`     → `adt_get` `exists:false` dedi (⚠ `func`/FUGR group-resolution
                         kusuru dahil — playbook/adt-fugr-functions.md §4, §4.1)
    `source_empty`     → 200 ama gövde BOŞ (ör. behavior pool `source/main`)
  `partial_objects[{object, type, reason}]` — okundu ama İÇERİK EKSİK:
    `fugr_skeleton_only` → FUGR'ın yalnız iskelet ana include'u; FM gövdesi
                           `L<FG>U01`'de ve TARANMADI (playbook §4.1)
    `class_includes_not_scanned` → sınıfın ana kaynağı tarandı ama alt-include'larından
                           (CCIMP/CCDEF/CCMAC/CCAU) en az biri OKUNAMADI ya da include
                           listesi (sınıf metadata'sı) alınamadı — `detail` hangisi/neden
  `coverage_complete` → hiçbir obje düşmedi/eksilmedi mi? (`scope_verified`
  paket ucunun DOĞRULUĞUNU, bu alan taramanın TAMLIĞINI söyler — ikisi ayrı eksendir)
Mevcut alanların hiçbiri kaldırılmadı/anlamı değiştirilmedi (tüketici sözleşmesi).

⛔ 2026-09-04 (Q206/Q106①/Q226) — yukarıdaki muhasebe `package=` dalında koşuyordu,
`objects=` dalında KOŞMUYORDU: tip dizesi ham geçtiği için (`"…:FUGR"` → `"fugr"`)
iskelet muhafızı tutmuyor, `coverage_complete` **sahte-yeşil** yanıyordu. Artık iki dal
aynı sözlüğü konuşur (`_grep_tip_normalize`). ⚠ TÜKETİCİ NOTU: `objects=` dalında tip
eşanlamlısı verilen çağrılarda dönüş alanlarındaki `type` artık KANONİK addır
(`"…:INTF"` → `interface`, `"…:FUGR"` → `functiongroup`) — `package=` dalı zaten böyleydi.

⛔ 2026-09-13 (Q282) — SINIF ALT-INCLUDE'LARI artık TARANIR. Eskiden sınıfta yalnız
ana kaynak (`source/main`) okunuyordu; behavior pool / local class gövdesi
`includes/implementations` (CCIMP) içindedir ⇒ `match_count: 0` + `coverage_complete:
true` = SAHTE NEGATİF (canlı vaka 2026-09-11). Okunacak include'lar sınıf metadata'sının
`class:include` listesinden gelir (listelenmeyen uç YOKLANMAZ). Metadata alınamazsa ya
da listelenen bir include okunamazsa obje `partial_objects`e
`class_includes_not_scanned` ile düşer — "tarandı" ile "taranmadı" karışmaz.
⚠ Maliyet: include'lu her sınıf için listelenen include başına +1 GET.
Include'dan gelen eşleşme `include` alanı taşır (`"implementations"` vb.); `line`
o include İÇİNDEKİ satırdır. Ana kaynak eşleşmelerinin şekli DEĞİŞMEDİ.

Returns:
    {ok, pattern, scanned_objects, match_count, truncated_object_scope, truncated_matches,
     scanned_class_include_count,
     matches: [{object, type, line, text, include?}], scope_verified, coverage_complete,
     skipped_count, skipped_objects, partial_count, partial_objects, client_log}
````

### `adt_inactive_objects` — ayrıntı

Önceki tam açıklama (2026-10-03'e kadar MCP açıklamasıydı; birebir):

````text
Aktive-bekleyen (inactive) obje worklist'ini oku — READ-ONLY.

`scripts/worklist_audit.py`'nin MCP-native karşılığı. Gün-sonu/commit-öncesi "aktive
edilmemiş obje var mı" kontrolü tek çağrıya iner. `GET /sap/bc/adt/activation/inactiveobjects`.

⚠ **SİLİNMİŞ OBJE TUZAĞI (2026-07-29, canlı vaka).** Bu uç nokta SİLİNMİŞ objeleri de
listeler ve kendi `ioc:deleted` alanı bunu ELE VERMEZ (ölçüm: TADIR `DELFLAG='X'` olan
iki sınıf için `ioc:deleted="false"` döndü — o alan *bekleyen taslağın* türünü anlatıyor,
objenin silinmiş olup olmadığını değil). Ham liste "2 obje aktive bekliyor" gibi okundu;
oysa objeler silinmişti (SE24/SE80'de yok, `adt_get` `exists:false`) ve geriye yalnız
bayat worklist kaydı kalmıştı. → Bu tool her girdiyi **TADIR DELFLAG** ile çapraz
kontrol eder; silinmişler `count`/`inactive_objects`'ten ÇIKARILIR, `stale_deleted`
altında ayrıca raporlanır. TADIR sorgusu koşamazsa SUSULMAZ: `tadir_deleted` null olur
+ `warning` alanı döner.
⚠ TADIR'daki `DELFLAG='X'` satırları **SİLİNMEZ** — silme işleminin transport'la
taşınması için gereklidir.

Returns:
    ÖLÇÜLDÜ (her girdi çapraz kontrol edildi):
    {ok: true, count, count_verified: true, inactive_objects, stale_deleted_count,
     stale_deleted, client_log}
    count=0 → AKSİYON GEREKTİREN aktive-bekleyen obje yok (silinmişler + transport/
    method-seviyesi girdiler elenir). Girdi: {name, type, uri, user, deleted, transport,
    tadir_deleted}.

    ÖLÇÜLEMEDİ (2026-09-09 / Q224 — en az bir girdide `tadir_deleted: null`):
    {ok: false, error: "tadir_kontrolu_belirsiz", count_verified: false,
     confirmed_live_count, unverified_count, confirmed_live, unverified,
     stale_deleted*, tadir_check, warning, message, client_log}
    ⛔ Bu dalda **`count` ve `inactive_objects` anahtarları HİÇ BASILMAZ.** Eskiden
    `warning` basılıyor ama sayı DÜZELTİLMİYORDU: `tadir_deleted is not True` süzgeci
    `null`ı (=ölçülemedi) `false` (=ölçüldü, silinmemiş) ile aynı kovaya atıyordu ⇒
    `count` sahte-pozitif şişiyordu ve uyarıyı okumayan çağıran yanlış sayıyı "kanıt"
    sanıyordu (fail-open). Doğru okuma: `confirmed_live_count` ≤ gerçek ≤
    `confirmed_live_count + unverified_count`. Emsal: `adt_atc_check`
    (`finding_count_unverified`) · `adt_lock_check` (`locked: null`).
````

### `adt_transport_list` — ayrıntı

⚠ **2026-10-03:** aşağıdaki *"`E070×E071` JOIN + `E07T` tek sorguda 400"* ve *"`IN ('a','b')` 400
verebilir"* ölçümleri freestyle ucunun **255 karakter satır sınırı** bilinmeden yapıldı (bkz.
`adt_sql_query` — ayrıntı); uzun satır artık otomatik kırılıyor. Bu vakalar yeniden
ölçülmedi (**DOĞRULANAMADI**). 400 alırsan önce `sap_error.message`'ı oku.

Önceki tam açıklama (2026-10-03'e kadar MCP açıklamasıydı; birebir):

````text
List a user's transport requests (modifiable + released).

Use this BEFORE create/modify operations to confirm the correct transport ID.
Never invent a transport — always pick one from this list and verify with the user.

Args:
    user: SAP user name. Defaults to the .conn_adt user.

⛔⛔ `count: 0` **KANIT DEĞİLDİR** — `shape_recognized: true` OLSA BİLE.

⚠ 2026-08-10 tarihli eski docstring, `shape_recognized` bayrağını sıfırın
DOĞRULUK kanıtı olarak sunuyordu. **BU REHBERLİK 2026-08-18'de ÖLÇÜLEREK
ÇÜRÜTÜLDÜ ve 2026-08-20'de bu metinden kaldırıldı.** (Çürütülen cümle burada
BİLEREK yeniden yazılmıyor: bir korpus çapası onun yokluğunu denetliyor ve
"tarihçe olarak alıntılamak" ile "hâlâ öğretmek" metin düzeyinde ayırt
edilemez — Parti-1'de aynı tuzağa bir kez düşüldü.) Çürüten ölçümler:
  · 2026-08-18: `count:0` + `shape_recognized:true` iken `DS4K918705` VARdı
    (E070: TRFUNCTION='S', TRSTATUS='D', AS4USER eşleşiyor).
  · 2026-08-19: aynı bileşim, E070'te **iki** açık kayıt.
  · 2026-08-19 (A-00): aynı bileşim, E070'te **dört** açık görev.
⇒ `shape_recognized` YALNIZCA *"yanıtın BİÇİMİNİ ayrıştırabildim"* der; içeriğin
doğruluğu hakkında HİÇBİR ŞEY söylemez. İkisini karıştırmak, yanlış cevaba güven
damgası basmaktır.

⛔ **NEDEN CİDDİ:** transport teyidi bir **ADR 0005-C kapısıdır**. Araç "TR yok"
derse doğal refleks **yeni TR açmaktır** — ki bu YASAKTIR. Yani bu sahte-negatif
doğrudan bir yasak ihlaline sürükleyebilir.

✅ **DOĞRU YÖNTEM:** sıfır sonucu `E070` (+ içerik için `E071`) ile ÇAPRAZ KONTROL
et — `TRSTATUS`, `AS4USER`, `TRFUNCTION`, `STRKORR` alanlarına bak. ⚠ `E070×E071`
JOIN + `E07T` tek sorguda **400** döndürür; iki ayrı sorguya böl. ⚠ Ayrıca
`IN ('a','b')` listesi de 400 verebilir — `OR` zincirine çevir.

Returns:
    {ok, count, transports: [...], accept_header, shape_recognized,
     zero_verified, zero_notice, client_log}

    `zero_verified`: `None` → count > 0 (soru geçersiz) ·
                     `False` → count == 0 ve **bu araç sıfırı KANITLAYAMAZ**.
                     ⛔ Bu alan ASLA `True` olmaz: pozitif kontrolü (dolu döndüğü
                     bilinen bir sorgu) bu tool koşmaz. Üç-değerli doğrulama
                     sözleşmesinin kardeşi (`delete_verified`/`readback_verified`).
````

### `adt_classrun` — ayrıntı

Önceki tam açıklama (2026-10-03'e kadar MCP açıklamasıydı; birebir):

````text
Bir IF_OO_ADT_CLASSRUN sınıfını çalıştır (ADT classrun, F9-run muadili).

ADT-only ABAP execute kanalı. RFC FM (RPY_DYNPRO_INSERT/RS_CUA_*) çağıran generator
sınıflarını çalıştırmak için (ekran/GUI status üretimi — C1). Kod ÇALIŞTIRIR (yazma
yapabilir) → ADR 0010 tier guard: yalnızca DEV.

⛔ **PUSH+ACTIVATE SONRASI ÇIKTI BAYAT OLABİLİR — TEK BAŞINA KANIT DEĞİLDİR.**
Ölçülmüş vaka (2026-08-19, `ZCL_SD000_GET_IDOCDATA`): sınıfa `c_docnum = '204075'`
sabiti eklenip push+activate edildi; `adt_classrun` **HTTP 200 + dolu, akla yatkın**
çıktı verdi — ama **eski kodun** çıktısı (sabit sanki BOŞ). **İkinci çağrı da aynı bayat
sonucu** verdi ⇒ tek seferlik aksaklık DEĞİL, tekrarlanabilir. Kaynak tarafı dört
bağımsız okumayla temiz ölçüldü (`source/main` default = `?version=active` =
`?version=inactive`, aynı sha, sabit VAR; `adt_inactive_objects` count 0).
**Kök sebep kaynakta değil, ÇALIŞTIRAN OTURUMDA:** MCP sunucusu tek uzun-ömürlü ABAP
oturumu kullanır (`sap-contextid` çerezi) ve **sınıf load'u o oturumda bayat kalır;
aktivasyon onu tazelemez.** Kanıt: TAZE oturumdan (yeni logon, kendi süreç,
`SAPClient().run_classrun(...)`) aynı sınıf DOĞRU çalıştı.
⚠ Bu, *"araç başarısız"* değil **"araç başarılı görünerek yanlış söylüyor"** sınıfıdır —
`adt_transport_list` sahte-sıfırı ve `adt_post_shell` sahte-400'ü ile aynı raf.

✅ **DOĞRU YÖNTEM (ikisinden BİRİ zorunlu):**
  1. **Taze oturumda koştur** — `python -c "...; SAPClient().run_classrun('<AD>')"`
     (ayrı süreç, yeni logon), **veya**
  2. **Çıktıyı kaynakla ÇAPRAZ KONTROL et** — çıktıda yeni koda ÖZGÜ bir imza
     (yeni başlık satırı, yeni sabitin değeri) görünüyor mu? Görünmüyorsa sonucu
     "davranış yanlış" diye RAPORLAMA; önce bayatlığı ele.

⚠ Bu tool bugün dönüşünde bayatlık ölçmez (`session_age`/`context_reused` alanı YOK —
oturum tazeleme/uyarı alanı infra kuyruğunda AÇIK kalemdir). Yani aşağıdaki `Returns`
sözleşmesinde **tazelik kanıtı yoktur**; kanıtı çağıran üretir.

Args:
    name: Sınıf (Z*/Y*, if_oo_adt_classrun~main implement etmeli).

Returns:
    {ok, class, status, output} — output = out->write konsol çıktısı.
    ⚠ `ok: true` çıktının GÜNCEL olduğunu KANITLAMAZ (yukarıdaki bayatlık şerhi).
````

### `adt_activate` — ayrıntı

Önceki tam açıklama (2026-10-03'e kadar MCP açıklamasıydı; birebir):

````text
Activate an SAP object — single, OR multiple objects ATOMICALLY (one /activation POST).

Atomik çoklu-obje aktivasyon (RAP zincirleri): birbirine bağımlı objeler (ör. interface
DDLS + onun BDEF'i + behavior class) AYNI istekte aktive edilmeli → `also` ile ek objeleri
ver, hepsi tek POST'ta aktive + doğrulanır (activationExecuted + type=E parse; sahte-OK
imkansız). bdef/srvd gibi activate_object'in desteklemediği tipler de bu yolda çalışır.

Args:
    name: Birincil obje adı (Z*/Y*).
    object_type: 'class', 'ddls', 'bdef', 'srvd', 'tabl', ...
    also: Atomik co-activate ek objeler: [{"name": "...", "object_type": "..."}, ...].
          None/boş → tek-obje aktivasyon (klasik yol).

Returns:
    {ok, name, type, activated, errors?, warnings?, refs?, client_log}

⛔ **KLASIK YOLDA `ok` = `activated`** (Q231-b, 2026-09-13). Eskiden `activated:false`
iken `ok:true` donuyordu (canlida olculdu). Artik `activated` True degilse `ok=false`,
`error="activation_failed"`. Alt katmanin hukmu TEK KAYNAKTAN gelir
(`sap_adt_lib.aktivasyon_govde_hukmu` + worklist sondasi — Q188).

⛔ **KLASIK YOLDA AKTIVASYON READBACK'i** (kayit #70, olculmus sahte-OK vakasi — `fugr`).
Obje **bagimsiz olarak** aktive-bekleyen worklist'inde (`/activation/inactiveobjects`)
aranir; eslestirme URI-siniri + ad+tip ile (`sap_adt_lib.aktivasyon_worklist_kalan`):
  • `activated: true` + `activation_verified: true`  → obje listede YOK, dogrulandi.
  • `activated: true` + `activation_verified: false` → obje HALA listede ⇒ **SAHTE-OK**:
    `ok=false`, `activated=false`, `error="activation_not_executed"`, `still_inactive=[...]`.
  • `activation_verified: null`  → sonda kosamadi ⇒ iddia **KANITLANMADI** (`warning`).
    Bu "dogrulandi" DEGILDIR.
  • `activated: false` → sonda YINE kosar ama YALNIZ BILGI tasir (`still_inactive`,
    `activation_probe`); `ok` false KALIR. Liste temizse `probe_note`: obje aktivasyondan
    ONCE listede degilse "temiz" ayirt edici DEGILDIR (on-snapshot alinmaz).
⚠ `also=` (atomik cok-obje) ve `srvb` yollari zaten `activate_and_verify` ile
`activationExecuted` + `type=E` parse eder; readback onlarda TEKRARLANMAZ.
````

## Bilinen Sınırlar (v1)

- `adt_lock_check` best-effort probe — bazı lock tipleri sadece write sırasında ortaya çıkar
- Composite tool'lar auto-rollback yapmaz (inactive obje değerli olabilir)
- Tool listesinde `transport_release`, `package_create` **YOK** (ADR 0005 §C)
- TR karakter validation v1'de sadece boş kontrolü; non-Latin karakter dağılım kontrolü v2'de
- ⚠️ **`adt_get`/`adt_lock_check` object_type='func' GÜVENİLMEZ** — mevcut FM'e bile `exists:false` (group-resolution bug). ⭐ **2026-09-04'ten sonra `exists:false` DEĞİL, `ok:false` + yönlendiren mesaj** gelir (generic URL tablosu `func` için fail-closed) — yani yanlış "obje yok" iddiası kalktı; okuma yolu yine açılmadı. Varlık için `adt_search_objects` ya da group-qualified metadata GET (`/sap/bc/adt/functions/groups/<fg>/fmodules/<fm>`). Bkz. `adt-fugr-functions.md` §4. **KAPSAM:** yalnız `object_type='func'`; genel `adt_get` DDIC-okuması güvenilir (KÖK-FIX 2026-06-16, `feedback_adt-get-ddic-read-fixed`) — "adt_get genelde güvenilmez" algısı yok.
- ⚠️ **AĞ/DNS kesintisinde `adt_get` `ok:true` + `exists:false` DÖNEBİLİR** — yani "obje yok" ile
  "sunucuya ulaşamadım" **aynı görünür**. Ayırt edici: yanıtın `client_log` alanında
  `NameResolutionError` (ya da benzeri bağlantı hatası) görünür. **KURAL:** `exists:false`
  gördüğünde **önce `client_log`'a BAK**; ağ hatası varsa bu bir varlık kanıtı değildir, tekrar
  ölç. (Bulunamadı ≠ yok — `lessons-learned.md` PATTERN #16 ailesi.)
- ⚠️ **`adt_delete` object_type='func' ÇALIŞMAZ** ("lock not supported"). FM silmek için stateful lock + DELETE (lib pattern, `adt-fugr-functions.md`). FG/class delete OK.
- ⚠️ **`adt_classrun` dialog-context FM çalıştıramaz** (RPY_DYNPRO_*/RS_CUA_*) → `400 "Session Timed Out"`. Bunlar için RFC-enabled FM + `/sap/bc/soap/rfc`. Bkz. `adt-fugr-functions.md` §6.
- ✅ **`adt_classrun` BOZUK/GÜVENİLMEZ DEĞİL** (2026-07-31 kök-fix; önceki "güvenilmez" kaydı GERİ ALINDI). *"does not implement if_oo_adt_classrun~main"* mesajı **DOĞRUDUR**: ya sınıf **aktive edilmemiştir** (aktif sürüm boş kabuk) ya da çağıran süreç **bayat stateful oturum** tutmaktadır (obje başka süreçte aktive edildi). Çare: aktive et + `adt_inactive_objects` doğrula · oturum RESET. ⛔ **"taze/yeni class adıyla yeniden yarat" reçetesini UYGULAMA** — yanlıştı, çözmez, çöp obje bırakır. Tam vaka + ölçüm: `adt-classes.md` §24.9.

## Geliştirme

Yeni tool eklemek için:
1. `mcp_servers/sap_adt/tools/<group>.py`'a `@mcp.tool()` ile ekle
2. SAPClient'ta karşılığı yoksa önce script seviyesinde test et
3. Guardrail gerekiyorsa `guardrails.py`'a `require_*` ekle
4. `tests/smoke.py`'a beklenen tool ismini ekle
5. Bu doc'a pattern özeti yaz (T2 trigger)
