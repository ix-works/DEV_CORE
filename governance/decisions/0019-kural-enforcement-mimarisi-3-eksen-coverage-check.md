# ADR 0019 — Kural-Enforcement Mimarisi: 3-Eksen Sınıflandırma + Coverage-Check Keystone + Kademeli Gate-Doğum

**Durum:** Kabul edildi (2026-06-18)
**Bağlam tetikleyici:** Rule-list soundness remediation (Faz 1-5, 2026-06-18) tamamlandı → asıl kök sorun ortaya çıktı: kural KALİTESİ değil, kural→**gate bağlama (enforcement coverage)**.

## Bağlam

Kök sebep: **"kural var ama gate yok" → pasif prose çürür** (`feedback_kural-gate-lenmeli-yoksa-anlamsiz`). 5-fazlık remediation bunu kanıtladı:

- **Korpus zaten sağlam.** ~1062 ham inventory maddesi denetlendi (8 partition × 4 paralel recon ajanı, canlı-dosyaya karşı). Sonuç birebir tekrar etti: inventory dağınık/duplike/aşırı-güçlü gösteriyordu ama **canlı korpus disiplinli** — toplam gerçek-edit ~25 küçük dokunuş, korpus yeniden-yazma değil. Yani rule-list "soundness" sorunları çoğunlukla inventory-çıkarım artefaktıydı.
- **Asıl boşluk = enforcement coverage.** Remediation 3 **orphan validator** buldu: `check_standard_table_fields` · `check_list_view_grid` · `check_sap_master_language` — dosya VAR ama hiçbir runner'a (run_all / run_review) WIRED DEĞİL. Yani checklist'ler bunları BLOCKER gösteriyor ama arkalarında ateşleyen gate yok = `table-update.md`'de kayıtlı "checklist satırı ≠ wired validator" tuzağının ta kendisi.
- **Daha derin risk: eşleme çürür.** "Hangi kuralın hangi gate'i var" elle-bakımlı tutulursa zamanla yalan söyler (kanıt: `run_all` 28 validator dosyasından yalnız 8'ini koşuyordu; table-update vakası = wired-ama-ateşlemeyen).

Sonuç: kuralları tek tek temizlemek yetmez; **kural↔gate bağının kendisini atlanamaz + kendi-kendini-denetleyen** kılmak gerek.

Dış dayanak: **RFC 2119** (güç seviyeleri) · **Sentinel/OPA/Gatekeeper** (enforcement seviyeleri + kademeli rollout) · **ESLint** ("warning çürür" dersi).

## Karar

### 1. Her kural 3 DİK EKSENDE sınıflanır (5-kova değil)

| Eksen | Değerler |
|---|---|
| **GÜÇ** | ZORUNLU (MUST) · YASAK (MUST-NOT) · ÖNERİLİR (SHOULD) · OPSİYONEL (MAY) |
| **KAPSAM** | her-zaman · rol:`<ad>` · koşul:`<predikat>` |
| **ENFORCEMENT** | hard-gate · soft-gate (override'lı) · checklist-gate · warn · advisory |

> **ONE-OF güç DEĞİL** — "şu seçeneklerden biri" kapsam/predikat tarafında ifade edilir, güç ekseninde değil.

### 2. Güç→mekanizma DEFAULT eşlemesi (bağlayıcı değil, danışılan)

| Güç + nitelik | Önerilen ENFORCEMENT |
|---|---|
| ZORUNLU + oto-güvenilir detektör | **hard-gate** |
| ZORUNLU + oto-**kırılgan** detektör | **warn → doğrula → terfi** (detektör güvenilirliği AYRI girdi) |
| ZORUNLU + yargı gerektirir | **checklist-gate** (seyrek: yalnız MUST + yargı + yüksek-değer) |
| ÖNERİLİR | **warn** |
| OPSİYONEL | **advisory** |

### 3. KEYSTONE — coverage-check (modelin kendisi çürümesin)

Elle-bakımlı eşleme TUTULMAZ → **hesaplattırılır:**

- **Kural = stabil-ID + inline-keyword.** Her gate kaynağında `# ENFORCES: <rule-id>` (veya dilin yorum biçiminde) **declare** eder.
- **`check_rule_gate_coverage`** validator'ı: "GÜÇ=ZORUNLU + ENFORCEMENT=hard ama declare-eden gate'i YOK" → **FAIL**.
- **3 kademe doğrula** (yalnız "dosya var" = aynı çürüme):
  1. gate dosyası var,
  2. run_all/hook'a **WIRED**,
  3. **kırmızı-fixture'ı yakalıyor** (bozuk-girdi testi geçiyor).
- **declare ⇄ fixture BAĞLI:** bir declare, eşleşen geçen-fixture olmadan geçerli sayılmaz. Fixture corpus'u **büyüyen**: her prod-kaçağı → yeni fixture; yazımda failure-mode enumerate edilir. Bu **yalnız oto-gate'lerde**; yargı-kuralında kanıt = **wired-reviewer-rolü + checklist-üyeliği**.

### 4. Kademeli gate-doğum (Gatekeeper deseni)

Yeni gate **`warn`/dryrun doğar** → false-positive shakeout → temizse **hard'a terfi**. Orphan validator wire'lama da bu yolu izler (önce warn, kırmızı-fixture + temiz-koşu kanıtıyla hard).

### 5. Yeni-kural onboarding (prosedür GATE'lenir, prose değil)

Kural eklenince/değişince **per-rule 5-adım** bir HOOK'la dayatılır:
1. güç-etiketle (3-eksen),
2. enforcement seç (default tablodan),
3. gate + fixture (oto) **veya** reviewer-rolü + checklist-üyeliği (yargı) kur,
4. stabil-ID ver,
5. coverage-check koştur.

(Mekanizma: `post_validate` hook — `standards/` · `playbook/` · `governance/decisions/` · `checklists/` edit'i + edit güç-keyword içeriyorsa fire eder. AMENDMENT 2026-06-18: önce yalnız `checklists/` ateşliyordu → ADR §5 kapsamı eksikti; standards/playbook/governance'a genişletildi.)

### 5A. RUBRIC — iyi kural METİN-KALİTESİ (8 ölçüt; onboarding'in parçası)

Enforcement-onboarding (§5) bir kuralı *gate'ler*; ama kuralın **iyi YAZILMIŞ** olması ayrı bir gerekliliktir (kötü-yazılmış kural gate'lense bile çürür). Yeni/değişen kural bu 8 ölçütle **teyit edilir** (onboarding adımı, §5'e paralel):

**GRAIN:** kural = bağımsız denetlenebilir EN KÜÇÜK kısıt, flag'lenmeye değer. Çok-geniş ("temiz kod") → böl/sil; çok-mikro → birleştir.

| # | Ölçüt | Açıklama |
|---|---|---|
| 1 | **atomik** | tek bağımsız-denetlenebilir kısıt (çoklu→böl) |
| 2 | **güç-açık** | MUST / MUST-NOT / SHOULD / MAY net (RFC2119) |
| 3 | **denetlenebilir** | pass/fail kararı verilebilir (muğlak "uygun olmalı" değil) |
| 4 | **kapsam-belli** | her-zaman / rol / koşul açık |
| 5 | **tek-ev** | canonical kaynak; başka yerde tekrar DEĞİL referans |
| 6 | **bağımsız-anlaşılır** | tek başına okunur + gerekçe içerir |
| 7 | **stabil-ID/kaynak** | kimliklenmiş, izlenebilir |
| 8 | **güncel-çelişkisiz** | mevcut kurallarla çakışmaz, bayat değil |

**Kalite barı enforcement-tipine göre:** auto-gate → makine-kesin (ölçüt 3 sıkı) · judgment → reviewer-brief netliği · advisory → en azından atomik + anlaşılır. (Kaynak: rule-remediation rubric'i — kalıcı ev artık BURASI, .tmp/RESUME değil.)

### 6. Regress nerede biter

coverage-check **de bir validator** → `run_all_validators` + `post_validate` hook'ta biter (başka doc'ta DEĞİL). Bizde sunucu-CI yok → **CI-eşdeğeri = run_all + hook**.

## Reddedilen alternatifler

- **Elle-bakımlı kural↔gate eşleme tablosu** — zamanla yalan söyler (rot); KEYSTONE'un çözdüğü tam sorun.
- **5-kova tek-eksen sınıflama** — güç/kapsam/enforcement'ı karıştırır; bir kural aynı anda "MUST + koşullu + warn" olabilir → 3 dik eksen şart.
- **Naive "dosya var → enforced" sayımı** — run_all'ın 28'den 8 validator koşması bunun neden yetersiz olduğunun kanıtı (3-kademe doğrulama gerekçesi).

## Sonuçlar

- **Olumlu:** enforcement coverage ölçülebilir + kendi-kendini-denetler; orphan gate'ler görünür; yeni kural gate'siz giremez; "checklist BLOCKER der ama script yok" tuzağı yapısal olarak engellenir.
- **Maliyet:** her hard-gate için fixture yazma yükü (ama büyüyen corpus = amortisman); gate'lerin `# ENFORCES:` ile etiketlenmesi (tek seferlik geriye-dönük).
- **Kapsam dışı (şimdilik):** kademeli build — bu ADR mimariyi sabitler; uygulama sırası: (a) orphan-wire (warn-first), (b) `check_rule_gate_coverage` iskeleti, (c) onboarding hook. Her biri ayrı commit + kırmızı-fixture testi.

## Ek (2026-07-10) — GATE-MORATORYUMU: yeni gate açmanın 5 şartı

**Sorun.** Bu ADR "her kural bir gate'le zorlanmalı" der. Tersi okunursa gate enflasyonu
üretir: 2026-07-10'da bir belge iki repoya **kopyalandı** → kopya bayatlar → tazelik gate'i
(C-DOC-01) → gate CI'da kaçınılmaz kırmızı verdi → `--admin` ile bypass edildi → bypass'ı
önlemek için bir guard kuralı daha (kural 10). **Kural kuralı doğurdu.** Kök sebep kural
eksikliği değil, **gereksiz çoğaltmaydı**; kopya kaldırılınca iki gate birden düştü.

**Karar.** Yeni bir gate ancak **beş şartın hepsi** sağlandığında açılır:

1. **Hata gerçekten yaşandı** — varsayım, ihtimal ya da "olabilir" yetmez.
2. **Sonuç geri alınamaz VEYA sessiz** — ikisi de değilse runtime guard meşru değildir
   (merdiven ilkesi: statik kontrole in).
3. **Başka hiçbir katman yakalamıyor** — tasarım / validator / pre-commit / CI zaten
   kapatıyorsa ikinci bir gate yalnız gürültüdür.
4. **Önce dokümanla hatırlatma denendi ve yetmedi** — `CLAUDE.core.md §1.1` (L1a),
   `claude/rules/` (glob-tetiklemeli), skill ya da checklist. **Gate son çaredir.**
5. **Kullanıcıya detaylı izah + AÇIK ONAY** — *auto-mode'da bile*. Gömülü onay
   ("hepsini yap", "devam et", "erteleme") bu izni **VERMEZ**. `feedback_adt-infra-*`
   kuralıyla aynı ruh.

> Ve her şeyden önce: **kök sebep çoğu zaman gereksiz bir çoğaltma/karmaşadır — önce onu kaldır.**
> Bir gate'i silmek, bir gate eklemekten daha sık doğru cevaptır.

**Kapsam.** Şartlar, *otomatik bir zorlama noktası ekleyen* her şey için geçerlidir:
`scripts/validators/check_*.py` · `scripts/hooks/*` (özellikle bloklayan) ·
`pre_tool_guard` kuralı · pre-commit / CI job'u · `run_review` görev-zinciri ·
checklist'te `check_*.py` iddia eden yeni satır.

**Kapsam dışı** (5 şart aranmaz):
- Var olan bir gate'in **onarımı** (yanlış-pozitif düzeltme, kaçak kapatma, desen sertleştirme).
- Bir gate'i **kaldırmak/gevşetmek** — teşvik edilir; yalnız kullanıcıya bildirilir.
- Zorlama yapmayan yardımcı araç (ör. `scripts/merge_pr.py`).

*Not:* bloklamayan ama davranış-yüzeyine dokunan hook'lar (ör. yalnız log yazan) bu beş şarta
girmez; onlar **ADT-altyapısı/hook değişikliği → önce uyar + açık onay** kuralına tabidir.
Pratik sonuç aynıdır: **onaysız yeni hook yok.**

## İlgili

- Remediation süreci + bulgular: `governance/rule-remediation-RESUME.md` + `archive/rule-remediation-2026-06-18/` (arşiv audit-izi).
- Gate altyapısı: `scripts/validators/run_all_validators.py` · `scripts/validators/run_review.py` (ADR 0006) · `scripts/hooks/`.
- Trigger sistemi (yeni-bilgi-yazma): `CLAUDE.md` §3 (T1-T12).
- Hook bakım karar-ağacı: `scripts/hooks/README.md` §2 (T11).
