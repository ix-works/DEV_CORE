---
name: diagnosing-bugs
description: >
  Disciplined root-cause loop for a defect whose CAUSE IS NOT YET KNOWN: build a red-capable
  feedback loop first, reproduce + minimise, rank 3-5 falsifiable hypotheses (RCA table with a
  refutation attempt each), probe one variable at a time, then fix at the unit where the defect
  lives. Covers SAP/ABAP (dumps, wrong data, OData/Gateway errors, slow reports), freestyle UI5
  and this repo's own tooling (hooks, validators, MCP scripts). Use when something that should
  work is broken, throwing, wrong, flaky or slow and nobody can yet say why. Triggers include
  "neden çalışmıyor", "hata veriyor ama sebebi belli değil", "dump alıyoruz", "ara ara bozuluyor",
  "yavaşladı", "debug et", "kök nedeni bul", "teşhis et". DO NOT USE FOR: a new development or a
  change whose cause/scope is already known (use intake-triage), pure code-reading questions,
  or reviewing a finished diff (bug-expert agent).
---

# HATA TEŞHİSİ — kök neden döngüsü

> ⚠ **Compaction notu — öz:** ① Kırmızıya dönebilen bir **geri bildirim döngüsü** kurmadan
> hipotez kurma. ② Hatayı **küçült**. ③ **3-5 çürütülebilir hipotez** + her birine çürütme
> denemesi (tablo). ④ Her prob **tek değişken**. ⑤ Düzeltme hatanın **yaşadığı birimde**;
> yeni test **projenin test politikasına** göre. ⑥ Doğrulanan hipotezi kayda geçir.

**Kaynak ve lisans:** Bu dosya `mattpocock/skills` → `skills/engineering/diagnosing-bugs/SKILL.md`
(commit `f3fc563`) metninin **Türkçe çeviri-uyarlamasıdır**: faz yapısı ve birçok madde oradan çevrildi,
bu çekirdeğin araçlarına, yasaklarına ve kanıt kurallarına göre uyarlandı. Upstream MIT lisanslıdır,
Copyright (c) 2026 Matt Pocock — lisans metninin tamamı [`LICENSE.upstream`](LICENSE.upstream),
kaynak/gümrük kaydı [`KAYNAK.md`](KAYNAK.md).

## 0. ÖNCE-ARA ve gizlilik

- **Bu hata daha önce yaşandı mı?** Hipotezden önce: memory (araç kök-fix kayıtları),
  `playbook/lessons-learned.md` + `playbook/known-errors.md`, ilgili paketin
  `SESSION_NOTES.md`'si. Tanıdık semptom bir sinyaldir; cevap yazılmış olabilir (KB-01).
- **Gizli bilgi:** `.conn_adt` / `conn/*.env` içeriği **basılmaz, loglanmaz, kopyalanmaz**; bağlantı
  sorununun teşhisi için `python core/scripts/sap_doctor.py` kullanılır. Komut ve
  çıktı gösterirken parola/token/oturum çerezi yerine `<REDACTED>` yaz. Kimlik bilgisini
  ortam değişkeninden okuyan döngü kur. Maskelenmiş çıktı yetmiyorsa bunu söyle, kullanıcıya sor.
- **Otorite kaynağını belirle:** DEV bir test sistemidir. Eski denemelerden kalan veri
  yanlış olabilir. Doğruyu söyleyen belge/dosya hangisiyse döngü ona göre kurulur.

## 1. Geri bildirim döngüsü kur — işin özü bu

Hatayı **bu hataya özgü** biçimde kırmızıya çeviren, hızlı ve tekrarlanabilir bir komut
bulursan sebebi de bulursun. Döngü yoksa koda bakarak teori kurmak boşa zamandır.

**Döngü adayları (kabaca bu sırayla):**

| Bağlam | Döngü |
|---|---|
| ABAP dump | `adt_dump_list` → `adt_dump_read` (ST22): aynı dump'ı yeniden üreten çağrı |
| Yanlış veri | `adt_sql_query` ile **kontrol grubu**: sorunlu kayıt + doğru çalışan kayıt yan yana |
| Mevcut sınıf/FM davranışı | **mevcut** testler için `adt_unit_run` · `adt_classrun` (mevcut bir `if_oo_adt_classrun` sınıfı) **kod ÇALIŞTIRIR, yazma yapabilir** ⇒ yalnız **adt-gateway** koşar. Push/aktivasyon sonrası **eski kodun çıktısını** dönebilir: taze oturum + yeni koda özgü bir imza satırıyla doğrula |
| OData / Gateway | Doğrudan HTTP isteği (`$metadata`, entity GET, `$batch`). Git Bash'te `MSYS_NO_PATHCONV=1`. Dar teşhis için `$skip` bisection + tek alan `$select` |
| Freestyle UI5 | Playwright betiği = kapı (DOM / konsol / ağ üzerinde doğrulama). Chrome eklentisi = göz |
| Çekirdek aracı (hook/validator/MCP betiği) | `python core/tests/run_battery.py <fixture>` · hook'a sentetik payload: `python core/scripts/hooks/<hook>.py < payload.json` (çekirdek reposunun kendisinde `core/` öneki yok). **exit 0 ≠ serbest**, stderr'e bak |
| Yakalanmış iz | Gerçek istek/IDoc/dosya diske alınır, aynı kod yolundan yeniden oynatılır |
| İki durum arası regresyon | Fark ekseni: eski/yeni sürüm, iki client, iki kullanıcı. Aynı girdi iki tarafta koşulup çıktı karşılaştırılır |

⛔ SAP'ye **yazan** her şey (geçici sınıf, log satırı, test verisi) **adt-gateway**'den
geçer ve ADR 0005'e tabidir. Standart veriye yazma yasağı teşhiste de geçerlidir. Yazmayan
döngü varken yazan döngü kurma.

**Döngüyü sıkılaştır:** daha hızlı mı (kapsamı daralt) · sinyal daha keskin mi ("çökmedi"
değil, **kullanıcının gördüğü semptom**) · daha deterministik mi (tarih, sayaç, kilit,
önbellek sabitlensin).

**Ara ara çıkan hata:** hedef temiz bir tekrar değil, **tekrar oranını yükseltmek**tir.
Döngüyü çok kez koş, eşzamanlılığı artır, zaman penceresini daralt.

**Döngü kurulamıyorsa DUR:** ne denendiğini listele. Kullanıcıdan erişim, maskelenmiş bir
artefakt (log, IDoc numarası, ekran kaydı) ya da **iş gerçeğini** iste. Ayrım: **kullanıcının
bildiği/yaptığı** (deneme sonucu, izlediği adımlar) → önce sor · **verinin/kodun davranışı** (alan
dolu mu, kaç kayıt, hangi dal koşuyor) → ölç.

**Faz 1 bitti mi?** Adını verebileceğin, **en az bir kez koştuğun** (komut + maskelenmiş
çıktı) tek bir komut var ve bu komut:
- [ ] **kırmızıya dönebilir:** gerçek kod yolunu sürer, kullanıcının tam semptomunu doğrular
- [ ] **deterministik** (ara ara çıkan hatada sabitlenmiş, yüksek tekrar oranı)
- [ ] **hızlı:** saniyeler
- [ ] **ajanın tek başına koşabileceği** türde

## 2. Yeniden üret + küçült

- [ ] Döngü **kullanıcının anlattığı** hatayı üretiyor, yanındaki başka bir hatayı değil.
- [ ] Birden çok koşuda tekrarlanıyor.
- [ ] Tam semptom (mesaj no + metin, yanlış değer, süre) yakalandı; düzeltme buna göre doğrulanacak.
- [ ] **Kontrol grubu** var: aynı döngü **çalıştığı bilinen** vakada yeşil (`playbook/lessons-learned.md`
  PATTERN #19). Kontrol grubu yoksa elindeki tek cümle "bu vakada çalışmadı"dır, "X bozuk" değil.

**Küçült:** girdiyi, çağıranı, ayarı, veriyi ve adımları **teker teker** çıkar; her kesimden
sonra döngüyü yeniden koş. Kalan her öğe hatayı taşıyorsa, yani hangisi çıkarılsa döngü
yeşile dönüyorsa küçültme biter.

## 3. Hipotez — RCA tablosu

Test etmeden önce **3-5 sıralı hipotez** üret; tek hipotez ilk akla gelene çakılır. Her
hipotez **çürütülebilir** olmalı: *"Sebep X ise, Y'yi değiştirince hata kaybolur / Z'yi
değiştirince kötüleşir."* Tahmin yazılamıyorsa o bir sezgidir: keskinleştir ya da at.

| # | Hipotez | Tahmin (bunu değiştirirsem …) | Çürütme denemesi (komut/ölçüm) | Sonuç |
|---|---|---|---|---|
| 1 | … | … | … | ÇÜRÜTÜLDÜ · AYAKTA · ÖLÇÜLEMEDİ |

- Her hipoteze onu **yanlışlamaya** çalışan bir deneme yazılır; doğrulamaya çalışan değil.
- "AYAKTA" kanıt değildir. Kanıt, tahmini yapılmış bir değişikliğin döngüyü yeşile çevirmesidir.
- **Tabloyu test etmeden önce kullanıcıya göster.** Kullanıcı sıralamayı bilgiyle değiştirebilir
  ("dün #3'e transport geldi") ya da elenmiş hipotezi söyleyebilir. Kullanıcı yoksa bekleme,
  kendi sıranla devam et.
- **Bulgu doğru, mekanizma yanlış olabilir:** semptomu açıklayan ilk mekanizmaya kilitlenme;
  aynı semptomu üreten diğer mekanizmayı da tabloya koy.

## 4. Prob — tek değişken

- Her prob Faz 3'teki **bir tahmine** karşılık gelir. **Aynı anda tek değişken** değiştirilir.
- Tercih sırası: salt-okur ölçüm (`adt_sql_query`, `adt_dump_read`, `adt_get`, HTTP GET) →
  sınır noktalarında hedefli iz → asla "her şeyi logla, sonra ara".
- Geçici iz eklenecekse **etiketli** olur (ör. `DEBUG-a4f2`). Temizlik tek aramayla yapılır.
  SAP'deki iz bir **SAP yazmasıdır**: gateway + aynı etiket + Faz 6'da geri alma.
- **Performans dalı:** iz değil **ölçüm**. Önce taban ölçülür (çalışma süresi, SQL izi,
  süre harness'ı), sonra bisection. Maliyetin nerede olduğu ölçülmeden kaldıraç önerilmez.

## 5. Düzeltme + regresyon kilidi

- **Düzeltme yeri:** semptomun göründüğü yer değil, **hatanın yaşadığı birim**. Aynı birimi
  çağıran **kardeş çağıranlar** taranır. Gerekçesiz dışarıda bırakılan kardeş, eksik düzeltmedir
  (bug-expert bunu `[EKSİK]` olarak işaretler).
- Yeni test (ABAP Unit / karakterizasyon) **projenin test politikasına** göre yazılır; bazı projelerde
  yeni test açık kullanıcı onayına bağlıdır — politikayı bilmiyorsan sor. Çekirdek aracında kilit = fixture,
  akışı `playbook/howto-infra-fix-proseduru.md` (çekirdek aracı değişikliği önce uyarı + açık onay ister).
- SAP kaynağını düzenlemeden önce PULL-BEFORE-EDIT (ADR 0016); esaslı düzeltmeden sonra taze bug-expert (BUG GATE).
- Test yazılacaksa **doğru dikişte** yazılır, yani hatanın gerçek çağrı zincirini sürdüğü
  yerde. Daha sığ bir dikiş sahte güven verir. **Doğru dikiş yoksa bu da bir bulgudur**; kaydet.
- Sıra: küçültülmüş tekrar → kırmızı → düzeltme → yeşil → **orijinal, küçültülmemiş** senaryo
  Faz 1 döngüsüyle yeniden koşulur. Kırmızıyı bir mutasyonla zorladıysan, mutasyonun gerçekten
  uygulandığını temiz kopyayla karşılaştırarak göster.
- SAP'ye yazılan düzeltme: `run_review.py` pre-flight → gateway → **canlı readback**
  ("aktive edildi" mesajı kanıt değildir).

## 6. Temizlik + kayıt

- [ ] Orijinal tekrar artık hata üretmiyor (Faz 1 döngüsü yeniden koşuldu, çıktısı var)
- [ ] Regresyon kilidi yeşil, **ya da** neden yok yazıldı (test politikası/onay gereği yazılmadı · doğru dikiş yok)
- [ ] Tüm `DEBUG-…` izleri kaldırıldı (etiketle arandı; SAP'deki iz gateway ile geri alındı)
- [ ] Geçici prototip/test objeleri silindi ya da açıkça işaretlendi
- [ ] **Doğrulanan hipotez** ve çürütülenler `SESSION_NOTES.md`'ye ve commit/PR mesajına yazıldı
- [ ] Tekrar edebilecek bir tuzaksa T1/T10 tetiği: `playbook/` kaydı (ÖNCE-ARA → `prior-art:` satırı)
