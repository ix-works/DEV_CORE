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
