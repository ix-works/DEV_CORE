---
adr: 0003
title: 4-katmanlı kural mimarisi (L1-L4) ve kod gate enforcement
status: accepted
date: 2026-05-14
deciders: <SAP_USER>
supersedes: —
superseded-by: —
---

# ADR 0003 — 4-Katmanlı Kural Mimarisi (L1-L4) ve Kod Gate Enforcement

## Bağlam

Repo root'unda zamanla 9 farklı .md kural dosyası birikmişti (AGENTS, CLAUDE, LESSONS_LEARNED, SAP_ADT_PLAYBOOK 143 KB, SAP_S4HANA_CODING 102 KB, NTTDATA_NAMING, UI_FIORI, SAP_FS_TS, SESSION_NOTES). Sorunlar:

1. **Mükerrer kurallar** — Aynı kural 2-3 dosyada (örn. "yeni package yaratma" AGENTS.md + NTTDATA'da)
2. **Drift riski** — Bir dosyada güncellenen kural diğerinde eskimiş kalıyor
3. **Pakete özel kural saklayacak yer yok** — Tüm paketlere uygulanır gibi yazılıyordu
4. **AI bilgi araması zor** — Bir konu için hangi dosyaya bakacağı belirsiz
5. **Documentation ≠ Enforcement** — LESSONS_LEARNED #4: kural yazılınca uygulandığını sanıyoruz, gerçekte bypass ediliyor

## Karar

**4-katmanlı kural mimarisi:**

| Katman | İçerik | Konum | Kapsam |
|---|---|---|---|
| **L1 — Agent davranışı** | Git, project skills, ADT işlem sırası, SAP standart objeler | `AGENTS.md` + `CLAUDE.md` (loader) | Her oturum |
| **L2 — Stabil kurumsal standart** | Naming, coding, UI, doc format | `standards/*.md` | Tüm projeler |
| **L3 — Operasyonel pattern** | ADT REST pattern + denenmiş başarısız + lessons-learned | `playbook/*.md` | İhtiyaç anında |
| **L4 — Paket-spesifik** | Prefix, bağımlılık, istisna | `ERP/<PKG>/.rules.md` | Sadece o paket |

**Her dosyada frontmatter zorunlu:** `layer`, `scope`, `applies-to`, `version`, `last-updated`, `status`

### Enforcement — Kod Gate Şart

Sadece doc bypass edilebilir (`LESSONS_LEARNED #4`). Her kural ikinci katmanla destekli:

- **Sprint gate:** `scripts/sprint_gate_check.py` (mevcut)
- **TD spec gate:** `scripts/td_spec_check.py` (mevcut)
- **Namespace whitelist:** `populate_cds_views.py::validate_sql_view_names()` (mevcut)
- **Yeni — Package naming:** `scripts/validators/check_package_naming.py` (Adım 6)
- **Yeni — Paket .rules.md varlık:** `check_package_rules_present.py` (Adım 6)
- **Yeni — Obje doğru paketde:** `check_object_in_correct_pkg.py` (Adım 6)
- **Yeni — Script playbook'ta referans:** `check_scripts_documented.py` (Adım 6)
- **Yeni — Playbook freshness:** `check_playbook_freshness.py` (Adım 6)

### Update Protokolü (T1-T9 Triggers + Karar Ağacı)

`CLAUDE.md` ince loader'ında:

- **T1-T8:** Mevcut trigger listesi (audit §11.2'de tanımlı)
- **T9:** scripts/'te bir script kullanıldı ama playbook'ta referansı yok → playbook'a pattern + script referansı ekle

3-soru karar ağacı:
1. Kapsamı tek paket mi? → L4
2. Tipi ne? Davranış → L1; Standart → L2; Pattern → L3
3. Mimari karar mı? → `governance/decisions/`

## Gerekçe

- **Tek doğruluk kaynağı her bilgi parçası için** — drift'i önler
- **Context tasarrufu** — AI sadece ihtiyaç duyulan katmanı yükler (143 KB tek dosya yerine)
- **Pakete özel kural mümkün** — `.rules.md` ile her paket bağımsız
- **Kod gate zorunluluğu** — `LESSONS_LEARNED #4` deneyimine cevap
- **AI refleksi** — 3-soru karar ağacı yeni bilginin yerini bulmayı mekanikleştirir

## Sonuçlar

- ✅ Drift riski minimum
- ✅ Yeni paket bootstrap'ı (Adım 6) `.rules.md` template'inden çoğaltır
- ✅ AI session başında tek loader (CLAUDE.md) okur — gerekirse alt katmana iner
- ❌ Migration bir kerelik yük (~8 adım, audit.md'de detaylı)
- ❌ Kural ekleyen kişi katmana karar vermek zorunda (eğitim eğrisi)

## Uygulama Sırası

`migration/audit.md` §10'da tanımlı 8 adım:

1. ✅ Audit + sorular cevaplandı
2. ✅ standards/ kuruldu (Commit: 1674b95d)
3. ✅ playbook/ kuruldu, ADT playbook 13 dosyaya bölündü (Commit: 5abe26c)
4. 🔄 governance/, templates/, archive/ (bu adım)
5. ⏭ ERP/ paket normalize
6. ⏭ validators/ + bootstrap script
7. ⏭ AGENTS.md slim + CLAUDE.md loader
8. ⏭ Final doğrulama + push

## İlgili

- [`../../migration/audit.md`](../../migration/audit.md) — Detaylı plan
- [`../../playbook/lessons-learned.md`](../../playbook/lessons-learned.md) — Pattern #4 (Doc ≠ Enforcement)
- [`../../AGENTS.md`](../../AGENTS.md) — L1 davranış kuralları
- [`../../CLAUDE.md`](../../CLAUDE.md) — Loader (Adım 7'de yenilenecek)
