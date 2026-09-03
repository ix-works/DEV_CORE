# adhoc-fosil — 2026-09-04 attic taşıması (Q235 / infra-fix turu)

**Neden:** 10 dosyanın tamamı **çalıştırılamaz fosildi** — her çağrıda ölüyorlardı, üstelik
iki ayrı biçimde:

| Kusur biçimi | Dosyalar | Ölçülen sonuç |
|---|---|---|
| `open(r'<PROJECT_ROOT>\.conn_adt')` — icra konumunda doldurulmamış yer tutucu | `fetch_cds_source.py` + `search/*` (5) | `OSError: [Errno 22] Invalid argument` · exit 1 |
| `sys.path.insert(0, r'<PROJECT_ROOT>/scripts')` — import kökü yer tutucu | `workflows/_*` (4) | `ModuleNotFoundError: No module named 'sap_adt_lib'` · exit 1 |

**Kök sebep — yer tutucu bir eksiklik değil, göçün parmak izidir.** Hiçbir jeneratör
`<PROJECT_ROOT>` doldurmaz (`init_project` · `bootstrap_package` · `team_setup` → 0 eşleşme);
`MAINTENANCE.md` onu `<SYSTEM_ID>`/`<SAP_USER>` ile birlikte **kimlik-temizleme** yer tutucusu
olarak sayar. 2026-07-08 genericize göçü (`f85e3fd`) bu dosyaları core'a alırken kimlik taşıyan
mutlak yolu yer tutucuyla değiştirdi — düzyazıda doğru olan bu ikame, **icra konumundaki**
dizede çalışan script'i fosile çevirdi. Aynı commit'in mesajı *"ad-hoc 13 dosya çıkarıldı"*
diyor: o turda bir eleme yapılmış, bu 10'u elemeden kaçmış.

**Tasfiye ölçütleri (üçü de ayrı ayrı ölçüldü, 2026-09-04):**
1. **0 çağıran** — 10 basename core genelinde `*.md`/`*.py`/`*.json`/`*.yml` içinde arandı;
   CLI · playbook · hook · CI · ajan brifi, hiçbirinde atıf yok.
2. **Belgesiz** — `check_scripts_documented` bunları hiç görmüyordu (yalnız
   `create_/populate_/run_` ön-ekli 28 script'i tarar; `fetch_`/`find_`/`search_`/`_*`
   ad-filtresinin dışında).
3. **İkame canlı** — `search_objects.py` · `download_object.py` · `activate_object.py` ·
   `run_sql_query.py` · `run_data_preview.py` · `populate_cds_views.py` · `push_bo_atomic.py`
   (+ MCP muadilleri) hepsi mevcut ve koşuyor.

**Ek gerekçe:** `workflows/_*` dosyaları ayrıca tek bir projeye ait paket sabiti ile
`<TRANSPORT>` / `<source_root>` yer tutucuları taşıyor; onarım, tek bir tarihsel CDS keşif
araştırmasının ad-hoc kalıntısını genericize etmek anlamına gelirdi. `workflows/__init__.py`
yalnız `write_workflow`'dan import eder — bu 4 dosya paket API'sinin parçası **değildi**.

**Emsal:** `governance/removed-controls.md` 2026-08-01 satırı — `scripts/create_program.py`
**birebir aynı kusur imzasıyla** (`<PROJECT_ROOT>\conn_adt`) "çalıştırılamaz fosil" diye
kaldırılmıştı. Bu taşıma o hükmün ikinci uygulamasıdır. Kardeş taşıma: `attic/validators-fosil`
(2026-07-31, aynı sınıf).

**Kanıt:** `governance/infra-changelog.md` 2026-09-04 Q235 satırı.

⚠ Dosyalar **silinmedi, taşındı** — geri alınabilir. `attic/` 5 validator tarafından atlanır,
yani buradaki içerik kapıların bakım yüzeyinden düşer (taşıma öncesi `check_console_utf8`
bu fosilleri "UTF-8 korumalı 139 script" iddiasına dahil ediyordu).
