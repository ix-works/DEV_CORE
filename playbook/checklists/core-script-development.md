---
applies_to: [ecc, s4_private, s4_public, btp_abap]
---
# Reviewer Checklist — CORE Script / Validator / Hook Geliştirme

> DEV_CORE (`core/`) altında script, validator veya hook yazarken/değiştirirken uygulanır.
> Proje reposundaki `scripts/validators-local/` de aynı kurallara tabidir.
>
> **Neden ayrı checklist:** core kodu, projelerin **içinden** `core/` junction'ı üzerinden
> koşar. Bu, sıradan Python sezgilerini bozar — en çok da "bulunduğum dizin" sezgisini.

**İlgili ADR:** 0020 (çoklu-proje / junction'lı çekirdek) · 0019 (kural↔gate coverage)
**İlgili kanonik modül:** [`../../scripts/utils/project_config.py`](../../scripts/utils/project_config.py)

---

## Checklist

| ID | Kontrol | Validator | Severity | Kural Referansı |
|---|---|---|---|---|
| **CORE-01** | Proje kökü / proje kaynağı / proje state'i `Path(__file__)` türevinden hesaplanıyor mu? (YASAK — junction'da `__file__` DAİMA DEV_CORE'a çözülür) | `check_project_root_resolution.py` | BLOCKER | ADR 0020 · aşağıdaki §Neden |
| **CORE-02** | Proje kökü gerekiyorsa `project_config.project_root()`, kaynak dizini için `source_dir()` kullanıldı mı? | `check_project_root_resolution.py` | BLOCKER | Kanonik API |
| **CORE-03** | Core'un KENDİ yolları (`playbook/`, `governance/`, `abaplint/`, `scripts/`) için `__file__` kullanımı korunuyor mu? (bunlar meşru — "hepsini değiştir" refleksi core'u kırar) | manual:core-path-review | BLOCKER | ADR 0020 |
| **CORE-04** | Yeni validator `# ENFORCES: <rule-id>` beyanı taşıyor + `run_all_validators.py`/`run_review.py` zincirine WIRED mi? | `check_rule_gate_coverage.py` | BLOCKER | ADR 0019 |
| **CORE-05** | Gate **bozuk girdiyle** canlı test edildi mi? (temiz-girdi PASS'i hiçbir şey ispatlamaz) | manual:negative-test | BLOCKER | Health-check dersi 2026-07-09 |
| **CORE-06** | Toplu yazan script (`populate_*` · `push_*` · `deploy_*`) **ATLANAN** işi `başarılı` kovasına karıştırıyor mu? Kapanış özeti "N başarılı" derken N'in içinde **hiç dokunulmamış** obje varsa bu SAHTE-YEŞİLDİR: `atlandi` AYRI sayılır ve çıkış kodu politikası **yazılı** olur. | manual:sahte-yesil-kova | BLOCKER | Q268 (2026-09-09) · aşağıdaki §populate_* |

---

## `populate_*` / toplu-yazma ailesi — "atlanan ≠ başarılı" (CORE-06)

⛔ **EMSAL VARDI, ATEŞLEMEDİ (PATTERN #30 sınıfı: kural vardı, konumu hatırlatmadı).**
`populate_tables.py` bu sınıfı **2026-08-19'da** ölçtü ve çözdü — fonksiyon başlığı
aynen şöyle diyor: *"⛔ Bu fonksiyon `[SKIP] zaten var -> return True` SAHTE
YESILININ panzehiridir"* (`scripts/populate_tables.py:268`, `readback_dogrula`).
Ölçülmüş vaka: yarım shell üzerinde koşuldu, ekrana **"1 basarili, 0 hatali"** yazdı,
**exit 0** verdi; readback tek satırlık shell gösterdi ⇒ **hiçbir şey yazılmamıştı**.

Buna rağmen aynı desen ailede yaşamaya devam etti (2026-09-09 statik envanteri):
`populate_cds_views.py` (Q268'de düzeltildi) ve `populate_domains.py:298` (AÇIK).
Emsalin tek bir dosyanın içinde yaşaması onu **görünmez** kıldı — bu satır o
yüzden var: aileye yeni script yazan ya da dokunan **önce buraya bakar**.

**İki ayrı değişmez (biri diğerini KAPSAMAZ):**
1. **KOVA** — "atlandı" başarı değildir: özet satırında ayrı sayılır, hiçbir yazma
   yapılmadıysa görünür uyarı basılır, çıkış kodu politikası kod içinde yazılıdır.
   İdempotans **korunur** (yeniden koşum meşru bir başarıdır); değişen şey iddianın
   dürüstlüğüdür. Emsal: `populate_cds_views.py` `SONUC_*` kovaları + `--fail-on-skip`.
2. **DOĞRULAMA** — "obje VAR" ≠ "obje DOĞRU": atlama kararı canlı içerikle
   kıyaslanmadan verildiyse bu bir **yazma kanıtı değil, atlama bildirimidir** ve
   çıktı bunu açıkça söylemelidir. Emsal: `populate_tables.readback_dogrula()`
   (`OLCULEMEDI` çağırana **temiz** diye dönmez).
3. **YÖNLENDİRME** — "kanonik YARATMA aracı" ≠ "kanonik GÜNCELLEME yolu": bir tipi
   reddedip operatörü **yaratıcıya** göndermek, elindeki soru *"nasıl güncellerim"*
   ise onu tam da yukarıdaki sahte-yeşile sürükler. Ölçülmüş vaka (2026-09-08):
   `push_object.py --type ddls` reddi koşulsuz `populate_cds_views.py` diyordu;
   istek MEVCUT bir view'ı güncellemekti, araç onu atladı. Hata *"yanlış araç"*
   değil **"yanlış iş için doğru araç"**tı. Emsal: `push_object.TIP_GUNCELLEME_YOLU`
   + `[GUNCELLEME]` satırı. ⚠ Yeni üye eklerken **playbook'ta yazılı bir sınır
   cümlesi göster** (`cds` için `playbook/adt-cds.md:178`); ölçülmemiş tipe
   güncelleme yolu **uydurulmaz** (bulunamadı ≠ yok).

Korpus: `tests/fixtures/push_atlandi_ve_kaynak_izi/run.py` (kova ekseni) ·
`tests/fixtures/populate_ddic_fail_closed/run.py` (fail-closed ekseni).

---

## Neden CORE-01 var — üç kez ısırdı (2026-07-08/09)

Core script'i `C:\<proje>\core\scripts\x.py` yolundan koşar ama `core/` bir junction'dır;
`Path(__file__).resolve()` linki çözer ve `C:\IX\DEV_CORE\scripts\x.py` verir. Yani:

```python
ROOT = Path(__file__).resolve().parent.parent      # -> C:\IX\DEV_CORE   (proje DEĞİL!)
files = (ROOT / SOURCE_ROOT_NAME).rglob("*.abap")  # -> yok -> 0 dosya -> "[OK] ihlal yok"
```

Hata **sessizdir**: exception atmaz, boş liste döner, gate yeşil yanar.

| Vaka | Sonuç |
|---|---|
| `source_drift.repo_root()` | `find_repo_source_file()` daima `None` → PULL-BEFORE-EDIT (ADR 0016) TÜM projede her SAP source Edit'ini bloklıyordu |
| 11 validator (`check_method_param_type_c` vb.) | `DEV_CORE/SOURCE_CODES` yok → 0 dosya tarandı → projedeki gerçek ihlallere **sahte PASS** |
| `sap_sync_pull` · `pull_before_edit` | seans tazelik damgası ortak core'a yazıldı → projeler arası state sızıntısı |

`project_config.py`'nin docstring'i bunu **zaten** yazıyordu. Kimse okumadı, hiçbir şey zorlamadı.
**Yorum gate değildir** (ADR 0019). CORE-01 o yorumun zorlayıcı hâlidir.

### İkinci biçim — göç artığı yer tutucu (⚠ kapı bunu GÖRMEZ)

Yukarıdaki biçim `__file__`'dan **yanlış türetir**. İkinci biçim hiç türetmez: proje kökünü
**doldurulmamış bir kimlik yer tutucusu** olarak taşır ve her çağrıda ölür.

```python
open(r'<PROJECT_ROOT>\.conn_adt')          # -> OSError: [Errno 22] Invalid argument
sys.path.insert(0, r'<PROJECT_ROOT>/scripts')  # -> ModuleNotFoundError: sap_adt_lib
```

⚠ `check_project_root_resolution.py` **bu biçimi yapısal olarak göremez**: AST'si
`X = <Path(__file__) içeren ifade>` ataması arar; burada `Path(__file__)` hiç yoktur.
Kapı aynı koşuda *"N core script'inde ihlal yok"* diyerek **sahte güven** üretir.
(Ölçüldü 2026-09-04 / Q235: 10 kırık script, kapı `[OK]`. Dosyalar `attic/adhoc-fosil/`e
taşındı — bkz. `governance/removed-controls.md`.)

**Yer tutucu bir eksiklik değil, göçün parmak izidir.** Hiçbir jeneratör `<PROJECT_ROOT>`
doldurmaz; `MAINTENANCE.md` onu `<SYSTEM_ID>`/`<SAP_USER>` ile birlikte **kimlik-temizleme**
yer tutucusu olarak sayar. Genericize/göç turu, kimlik taşıyan mutlak yolu yer tutucuyla
değiştirir — düzyazıda doğru olan bu ikame, **icra konumundaki** dizede çalışan script'i
fosile çevirir.

📌 **Göç/genericize turundan sonra sorulacak soru** *"kim doldurmayı unuttu"* değil,
**"eleme filtresinden ne kaçtı"**dır.

**Ayırt edici ölçüt — konum değil, dizenin BAŞI:** aynı yer tutucu düzyazıda meşrudur.
Ölçüldü (208 script): *"icra konumunda yer tutucu"* ölçütü **21 dosya** yakalar, yalnız 10'u
gerçek kusurdur (**precision %48**) — `help='Transport (e.g. <TRANSPORT>)'`, guard'ın kendi
açıklama metni ve `init_project.py`'ın `replace("<source_root>", …)` **ikame anahtarı**
yanlış yakalanır. Ölçüt *"dize değeri yer tutucuyla **BAŞLIYOR**"* olunca **10/10, 0 FP**:

| Dize | Hüküm |
|---|---|
| `'<PROJECT_ROOT>\.conn_adt'` · `'<PROJECT_ROOT>/scripts'` | **yoldur → kusur** (yer tutucu başta) |
| `'Transport (e.g. <TRANSPORT>)'` | mesaj metnidir → meşru (yer tutucu ortada) |
| `replace("<source_root>", a.source_root)` | **ikame anahtarıdır → meşru**; yer tutucuyu DOLDURAN kod onu adlandırmak zorundadır — bu ayrımın çapasıdır |

## Kanonik API

```python
from utils.project_config import project_root, source_dir, source_root_name

project_root()       # env CLAUDE_PROJECT_DIR → cwd     (PROJE kökü)
source_dir()         # project_root() / source_root_name()  (PROJE kaynağı)
project_root() / ".claude" / ".session_fresh.json"       # PROJE state'i
```

Core'un kendi varlıkları için `__file__` **doğru** kullanımdır:

```python
CORE_ROOT = Path(__file__).resolve().parents[2]
CHECKLISTS = CORE_ROOT / "playbook" / "checklists"   # meşru
sys.path.insert(0, str(Path(__file__).resolve().parent))  # meşru (atama değil)
```

## Negatif test (CORE-05) — reçete

Gate'i yazdıktan sonra **bilerek bozuk** girdi ver, yakaladığını gör; sonra temiz girdide
sustuğunu gör. İkisi de yapılmadan gate "çalışıyor" sayılmaz.

```bash
# örnek: check_method_param_type_c
cat > <proje>/<source_root>/.../ZZZ_PROBE.clas.abap <<'EOF'
CLASS zzz_probe DEFINITION PUBLIC.
  PUBLIC SECTION.
    METHODS probe IMPORTING iv_bad TYPE c LENGTH 10.
ENDCLASS.
CLASS zzz_probe IMPLEMENTATION.
  METHOD probe.
  ENDMETHOD.
ENDCLASS.
EOF
python core/scripts/validators/check_method_param_type_c.py; echo "exit=$?"   # exit != 0 OLMALI
rm <proje>/<source_root>/.../ZZZ_PROBE.clas.abap
python core/scripts/validators/check_method_param_type_c.py; echo "exit=$?"   # exit == 0 OLMALI
```
