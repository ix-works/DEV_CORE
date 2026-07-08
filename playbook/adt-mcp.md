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
| MCP `verify: {ok: true}`'ye güvenip post-check atlama | Old behavior sadece existence kontrol ediyordu, content kontrol etmiyordu (yeni `_activate_and_verify` version=active kontrol eder, ama MCP server restart şart) |

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
- Diğer geliştiriciler: `python scripts/team_setup.py` tek komutla setup (`.mcp.json` git pull'la geldiği için ek adım yok)

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
| `adt_dtel_create` | (henüz validator yok → SKIP) | aynı |
| `adt_push_source` (object_type='ddls') | `cds_update` | otomatik (source text → temp file) |
| `adt_push_source` (object_type='tabl') | `table_update` | otomatik |
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

## Bilinen Sınırlar (v1)

- `adt_lock_check` best-effort probe — bazı lock tipleri sadece write sırasında ortaya çıkar
- Composite tool'lar auto-rollback yapmaz (inactive obje değerli olabilir)
- Tool listesinde `transport_release`, `package_create` **YOK** (ADR 0005 §C)
- TR karakter validation v1'de sadece boş kontrolü; non-Latin karakter dağılım kontrolü v2'de
- ⚠️ **`adt_get`/`adt_lock_check` object_type='func' GÜVENİLMEZ** — mevcut FM'e bile `exists:false` (group-resolution bug). Varlık için `adt_search_objects` ya da group-qualified metadata GET (`/sap/bc/adt/functions/groups/<fg>/fmodules/<fm>`). Bkz. `adt-fugr-functions.md` §4. **KAPSAM:** yalnız `object_type='func'`; genel `adt_get` DDIC-okuması güvenilir (KÖK-FIX 2026-06-16, `feedback_adt-get-ddic-read-fixed`) — "adt_get genelde güvenilmez" algısı yok.
- ⚠️ **`adt_delete` object_type='func' ÇALIŞMAZ** ("lock not supported"). FM silmek için stateful lock + DELETE (lib pattern, `adt-fugr-functions.md`). FG/class delete OK.
- ⚠️ **`adt_classrun` dialog-context FM çalıştıramaz** (RPY_DYNPRO_*/RS_CUA_*) → `400 "Session Timed Out"`. Bunlar için RFC-enabled FM + `/sap/bc/soap/rfc`. Ayrıca classrun **app-server load-cache**: push+activate sonrası eski load çalışabilir → iterasyonda yeni class adı. Bkz. `adt-fugr-functions.md` §6.

## Geliştirme

Yeni tool eklemek için:
1. `mcp_servers/sap_adt/tools/<group>.py`'a `@mcp.tool()` ile ekle
2. SAPClient'ta karşılığı yoksa önce script seviyesinde test et
3. Guardrail gerekiyorsa `guardrails.py`'a `require_*` ekle
4. `tests/smoke.py`'a beklenen tool ismini ekle
5. Bu doc'a pattern özeti yaz (T2 trigger)
