---
adr: 0006
title: Reviewer Agent Pattern — Pre-Flight Quality Gate
status: accepted
date: 2026-05-14
priority: HIGH
deciders: <SAP_USER>
supersedes: —
superseded-by: —
---

# ADR 0006 — Reviewer Agent Pattern (Pre-Flight Quality Gate)

## Bağlam

Coordinator (kullanıcıyla konuşan tek AI agent) SAP ADT işlemlerini yaparken **playbook'taki kuralları zaman zaman atlıyor** — görev baskısı, context tasarrufu, "biliyorum sandım" kısayolu. Bu **patinaj** (deneme yanılma) yaratıyor:

**Vaka 2026-05-14 — Sprint 5 turunda 3 büyük patinaj:**

| Hata | Kayıp Süre | Sebep |
|---|---|---|
| T_BOOKHD currency annotation qualified format eksik | ~5 dk + 3 deneme | Playbook §15 okunmadan tahmin |
| `vsartkat` field eski <LEGACY_SOURCE> source'ta var, yeni T173'te yok (`vktra` doğrusu) | ~8 dk + cascade fail | Standart tablo field varlık teyit edilmedi |
| Domain output length QUAN(15,3) → 19 olmalı, 15 verildi | ~10 dk + 5 delete+recreate | Formül bilinmeden default kullanıldı |

Kullanıcı ("<SAP_USER>") her seferinde manuel olarak müdahale edip uyardı. Bu kullanıcı zamanını kaybediyor + sistemli kalite kontrol eksikliği gösteriyor.

## Karar

**Reviewer Agent Pattern** — coordinator'ın SAP yazma işlemi YAPMADAN önce, **bağımsız bir agent** draft'ı denetler.

### Roller (kesin ayrım)

| Rol | Yetki | Bias |
|---|---|---|
| **Kullanıcı** | Nihai onay, business kararları | Doğal denetim |
| **Coordinator** | İş yapan (SAP yazma, doc update, git) | "İşi bitir" baskısı altında |
| **Reviewer** | Bağımsız denetim, sadece rapor | "Bu doğru mu?" soğukkanlı |

Üçü farklı rol, **örtüşmez**.

### Reviewer Tool Profili (Kısıtlama)

| Tool | İzin |
|---|---|
| `Read`, `Grep`, `Glob` | ✅ |
| `Bash` (sadece read komutları, SAP GET) | ✅ |
| `Edit`, `Write`, `Bash` (yazma) | ❌ |
| `git commit`, `git push` | ❌ |
| `AskUserQuestion` | ❌ — kullanıcıyla konuşamaz |
| SAP ADT yazma endpoint (POST/PUT/DELETE) | ❌ |
| SAP ADT okuma endpoint (GET) | ✅ |

**Kritik:** Reviewer yazılı dünyada hiçbir şey değiştirmez. Sadece rapor döner.

### Verdict Hiyerarşisi

| Verdict | Coordinator Davranışı |
|---|---|
| **PASS** | Yazabilir, devam et |
| **WARNING** | Yazabilir AMA kullanıcıya raporda belirt |
| **BLOCKER** | Yazma YASAK — düzelt veya kullanıcıya açıkla |

Coordinator BLOCKER'ı **görmezden gelemez**. WARNING **override edilebilir** (kullanıcı onayıyla).

### Çağrı Tetikleyicileri (Zorunlu)

Reviewer **SAP yazma işlemi öncesi** zorunlu çağrılır:

- ✅ Yeni Z domain/DTEL yarat
- ✅ DTEL update (LOCK + PUT pattern)
- ✅ Yeni CDS source yaz/update
- ✅ Tablo ALTER (yeni field, struct change)
- ✅ Class push (önemli: ABAP kodunda standart tablo direkt I/U/D yasak — ⛔ KATEGORİ B)
- ✅ Program/include push
- ✅ Aktivasyon hatası belirsiz mesaj döndüyse (alternatif yorum)

**Atlanır (ölçüt = işlem SAP'ye GİTMİYOR):**
- ❌ Yerel `.md` / dokümantasyon draft yazımı (SAP'ye gitmeyen)
- ❌ Git commit/push (read-only review zaten oldu)
- ❌ Kullanıcıyla sohbet
- ❌ Sprint gate / validator çalıştırma (zaten otomatik)

> ⚠️ **Sınır netliği:** `.cds`/`.bdef`/`.abap` gibi **SAP'ye push edilecek** taslakların yerel yazımı tek başına review tetiklemez, AMA **push anında** üstteki §Çağrı Tetikleyicileri (SAP-yazma) devreye girer — yani bu dosyalar "atlanır" kapsamında DEĞİL. Atlama yalnız SAP'ye hiç gitmeyecek işlemler içindir.

### Çıktı Formatı (Yapılandırılmış)

Reviewer **mutlaka** şu formatta döner:

```yaml
review_result:
  verdict: PASS | WARNING | BLOCKER
  task_type: cds_creation | domain_creation | dtel_update | table_alter | class_push | ...
  artifact: <path>

  checklist_results:
    - id: C-CDS-CUR-01
      status: FAIL
      rule_reference: "playbook/adt-tables-structures.md §15.3"
      quote_from_rule: "Annotation isimleri (case-sensitive): @Semantics.amount.currencyCode"
      violation_in_artifact: "ZSD001_DDL_X.cds:12 — qualified format eksik"
      suggested_fix: "'order_currency' → 'zsd001_t_bookhd.order_currency'"
      validator_output: "check_cds_currency_reference.py: FAIL line 12"
    - id: C-CDS-VIEW-01
      status: PASS
      validator_output: "check_namespace_whitelist.py: PASS"
    # ...

  known_blind_spots:
    - "BIN tipindeki yeni alan için check yok"
    - "ABAP CDS 'cast as abap.curr' format'ını kontrol etmedim"

  net_decision_for_coordinator: |
    BLOCKER bulguları düzelt:
    1. Line 12: annotation'ı qualified format'a çevir
    2. Line 18: order_currency üzerine @Semantics.currencyCode marker ekle
    Sonra tekrar review iste.
```

### Fail-Fast Framing (LLM Bias Karşı)

Reviewer prompt'unun başında ZORUNLU:

> **"Şüphe varsa BLOCKER. Override etmek coordinator'ın işidir, senin değil. 'Muhtemelen OK', 'genelde böyle yapılır', 'sanırım problem yok' YASAK ifadeler. Her checklist maddesi için kesin durum (PASS/FAIL/N/A) ve kanıt zorunlu. Kanıt veremeyeceğin maddeyi FAIL işaretle."**

### Kanıt Zorunluluğu (Halüsinasyon Karşı)

Reviewer'ın "playbook diyor ki" cümlesi **yetmez**. Mutlaka:

- `rule_reference`: doğrulanabilir dosya yolu + satır aralığı
- `quote_from_rule`: doğrudan alıntı (coordinator grep'le teyit edebilir)
- `validator_output`: deterministik script çıktısı (varsa)
- `violation_in_artifact`: satır numarası + cümle

Coordinator **otomatik teyit edebilir**:
```bash
grep "Annotation isimleri" playbook/adt-tables-structures.md  # alıntı gerçek mi
python scripts/validators/check_cds_currency_reference.py <artifact>  # validator'ı kendi çalıştır
```

### Yeni Trigger — T10

CLAUDE.md trigger tablosuna **T10** eklenir:

> **T10** — Patinaj/hata yakalandı (deneme yanılma cycle):
> - Hatayı düzelt + playbook update (T1 zaten gerekli)
> - **PLUS:** "Bu hatayı reviewer yakalayabilir miydi?" sor:
>   - Evet → yeni validator/checklist madde ekle
>   - Hayır (gerçek LLM yorumu gerektiriyor) → "known blind spot" not düş

T10 mevcut T1 (yeni başarılı pattern) ve T2 (yeni keşif) ile tamamlayıcıdır.

### Reviewer Kapasitesi Güncellemesi (Self-Improving)

5 mekanizma:

1. **T10 trigger** (yukarıda) — her patinaj reviewer kapasitesini büyütür
2. **Playbook ↔ Checklist zorunlu bağ** — yeni playbook section'ı zorunlu checklist parçası içerir
3. **Reviewer blind spot raporu** — coordinator 3+ kez gördüğü blind spot için validator yaratılması işaretlenir
4. **Sprint sonu retrospektif agent** — yakalama oranı + false positive + kapasite önerisi
5. **Validator metadata + 90-gün audit** — eski/kullanılmayan validator'lar gözden geçirilir

## Gerekçe

- **LESSONS_LEARNED #4** (Doc ≠ Enforcement): sadece "şunu unutma" demek yetmez, **kod gate** ve **mekanik checklist** gerek
- **Coordinator self-check yetersiz**: aynı LLM = aynı blind spots (görev baskısı, context kısayolu)
- **Kullanıcı manuel uyarısı sürdürülebilir değil**: yorucu, sistemli değil
- **Deterministik validator'lar LLM-bağımsız**: false positive/negative ihtimal sıfır
- **Setup maliyeti uzun vadede amortize**: bu turun patinajları ~50 dk, reviewer overhead ~8 dk/sprint, break-even ~Sprint 6-7

## Sonuçlar

- ✅ Patinaj sayısı düşer (tahmin: %70-80)
- ✅ Kullanıcı manuel uyarı zamanı azalır
- ✅ Setup yatırımı 1 sprint sonra amortize
- ✅ Kalite gerçek zamanlı görünür (verdict + kanıt)
- ❌ Sprint başına ~5-8 dk overhead (kompleks obje için)
- ❌ Setup bir kerelik ~5-8 saat (validator + checklist + reviewer + audit)
- ❌ Validator listesi büyüdükçe bakım yükü (mitigation: 90-gün audit)

## Optimum Nokta

| Durum | Reviewer çağrılır mı? |
|---|---|
| SAP yazma içeren işlem | ✅ ZORUNLU |
| Yerel doc/MD edit | ❌ Atla |
| Eski source'tan kopya (standart tablo alanları içeren) | ✅ ZORUNLU |
| Küçük tip-aynı field güncelleme (CDS source minor edit) | ⚠️ Coordinator karar verir |
| Class push (ABAP kodu içerir) | ✅ ZORUNLU (⛔ KATEGORİ B nedeniyle) |

## Self-Monitoring (3 Sprint Kuralı)

Sprint sonu metric'ler:
- Toplam reviewer süresi
- Yakaladığı BLOCKER sayısı (gerçek hata önleme)
- False positive sayısı
- Tahmini net kazanç (dk)

**3 sprint üst üste negatif kazanç** → reviewer'ı sadeleştir veya kaldır. Sürekli izlenir.

## Enforcement

| Katman | Mekanizma |
|---|---|
| **Doküman** | AGENTS.md §A — reviewer kuralı, CLAUDE.md §3 — T10 trigger |
| **Session loader** | Ekran teyidi template'inde "Reviewer aktif" satırı |
| **Coordinator davranışı** | SAP yazma öncesi `scripts/validators/run_review.py` zorunlu çağrı |
| **Code gate** | run_review.py BLOCKER dönerse populate/activate script'leri durur |
| **Kullanıcı gözetimi** | WARNING durumda kullanıcıya raporda görünür |

## Pilot — Sprint 6

13 Z structure yaratımı sırasında:
1. Coordinator her struct draft'ını yazar (lokal `.ddls.asddls`)
2. `run_review.py --task struct_creation --artifact <path>` zorunlu çağrı
3. PASS → populate + activate
4. WARNING → kullanıcıya rapor, kullanıcı onayı sonrası devam
5. BLOCKER → düzelt, tekrar review

**Başarı kriteri:** 13 struct'ın ≥11'i tek seferde aktif olur (≥%85). Eğer altında kalırsa tasarım eksik, iyileştirilir.

## İlgili

- [`../playbook/lessons-learned.md`](../../playbook/lessons-learned.md) — LESSONS_LEARNED #4 (Doc ≠ Enforcement)
- [`0003-layered-rule-architecture.md`](0003-layered-rule-architecture.md) — L1-L4 katman + kod gate
- [`0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md`](0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md) — Reviewer ⛔ KATEGORİ B kontrolü (ABAP'ta std tablo I/U/D)
- [`../../playbook/checklists/`](../../playbook/checklists/) — Mekanik checklist'ler
- [`../../scripts/validators/run_review.py`](../../scripts/validators/run_review.py) — Reviewer orchestrator
