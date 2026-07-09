---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: playbook
applies-to: both
last-updated: 2026-05-14
status: active
purpose: Tekrarlayan hata pattern'leri ve trigger phrases
---

# LESSONS_LEARNED — Tekrarlanan Hata Pattern Kataloğu

> **AMAÇ:** Claude (AI agent) yaptığı tekrar eden hataları **tanıma + önleme** mekanizması. Her oturum başında okunur, oturum sonunda güncellenir.

> **OKUNMA SIKLIĞI:** Her SAP iş oturumu başında. AGENTS.md ve CLAUDE.md bu dosyaya referans verir.

---

## ⛔ KRİTİK YASAKLAR — En Üstte (ADR 0005)

Bu yasaklar **HİÇBİR şekilde bypass edilemez**. AI bir oturumda bu yasaklardan birine yaklaştığında trigger phrase olarak değerlendir, DUR:

| Kategori | Trigger Phrase / Niyet | Aksiyon |
|---|---|---|
| **A** | "Standart tabloya alan ekle", "VBAK'a custom field", "standart classte method değiştir" | STOP → operatöre sor |
| **A** | "Bu append struct'u yaratabilir misin", "LIPS'e zz_field ekle" | STOP → kullanıcı SAP GUI'den yapacak |
| **B** | "VBAK'a şu kaydı ekle", "T001'i güncelle", "standart tabloda veri değiştir" | STOP → BAPI/RFC ara, yoksa manuel iste |
| **C** | "Yeni TR aç", "transport release et", "yeni package yarat" | STOP → kullanıcıya sor |
| **D ihmali** | Z'li obje yarattım ama label'lar İngilizce/boş kaldı | DÜZELT — TR'ye çevir, REST GET ile doğrula |

📖 Detay: [`../governance/decisions/0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md`](../governance/decisions/0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md)

---

## 🚨 TRIGGER PHRASES — Kullanıcıdan Gelen Meta-Uyarı Sinyalleri

Aşağıdaki ifadeler kullanıcıdan geldiğinde **IMMEDIATELY DURAKLA**, meta-pattern olarak değerlendir:

| Trigger | Anlamı | Tepki |
|---|---|---|
| "yine yapıyorsun" | Tekrar eden pattern | Aşağıdaki pattern'lere bak, hangisi |
| "sürekli aynı hata" | Çoklu ihlal | Sistem yetersiz → strüktürel önleme öner |
| "kaç defa hatırlatmama rağmen" | Documentation enforcement değil | Code-level check ekle |
| "kuralı atlama" | Forward bias | sprint_gate_check + spec_check çalıştır |
| "anladım yapma" | Davranış değişikliği isteniyor | Onay alma istediği şeyi yapma |
| "doğrudan ileri gidiyorsun" | Backward verification atlandı | Audit yap, sonra ilerle |
| "okudun mu" | Documentation skipped | İlgili dosyayı oku, sonra cevapla |
| "kontrol et" / "test et" | Verification eksik | Code-level/SAP-level doğrulama |

**Tepki protokolü:**
1. Forward progress STOP — devam etme
2. Bu dosyada ilgili pattern var mı kontrol et
3. Yeni pattern ise → ekle (aşağıdaki ACTIVE PATTERNS bölümüne)
4. Strüktürel prevention öner
5. User onayı al, sonra ilerle

---

## 📋 ACTIVE PATTERNS (tekrarlayan hata kataloğu)

> Aşağıdaki pattern'ler genel SAP-AI dersleridir (proje-bağımsız). Numaralar başka
> dosyalardan referanslıdır (örn. checklist'ler PATTERN #8'e atıf yapar) → **yeniden
> numaralandırma YAPMA**. Projeye-özel disiplin pattern'lerini (sprint/plan-disiplini,
> spec-disiplini vb.) keşfettikçe buraya yeni numarayla ekle + ilgili kod gate'i kur.

### PATTERN #3: Memory Drift — Workspace ≠ SAP State
- **Hata:** Conversation uzayınca, todo "tamamlandı" claim'ime güveniyorum, SAP gerçek state'i sormuyorum
- **Trigger:** Long-running context, çoklu obje işlemi, "sıradaki ne?" soruları
- **Kök sebep:** Internal state model gerçeklikle senkron tutulmuyor
- **Detection:** User audit yaptırınca todo ile SAP fark ettiği görülür (örn. Sprint 1A "6 done" todo'da, plan 34 hedef)
- **Prevention:**
  - "Tamamlandı" iddiasından ÖNCE SAP query (TADIR/GET)
  - Session start: `sprint_gate_check.py` çıktısı user'la paylaş
- **Status:** ✅ KOD GATE AKTİF (2026-05-13)
- **Vakalar:** Tüm sprint audit sonuçları

### PATTERN #4: Documentation ≠ Enforcement
- **Hata:** Playbook'a kural yazdım → problem çözüldü sanıyorum. Ben de okumuyorum sonra.
- **Trigger:** "Kural koyalım" → MD dosyasına yazıp bitirme refleksi
- **Kök sebep:** Documentation alone bypass edilebilir; sadece kod-düzeyi gate'ler zorunludur
- **Detection:** Aynı pattern 2+ kez tekrar olur, kural varlığına rağmen
- **Prevention:** Her documentation kuralı **kod gate**'iyle birlikte yazılır. Sadece doc → değer yok.
- **Status:** ✅ SİSTEMATİK (her yeni kural için 2-katman: doc + code)
- **Vakalar:** Namespace whitelist (önce sadece doc, sonra pre-flight check eklendi)

### PATTERN #5: Trust Without Verify
- **Hata:** User "sildim" / "yaptım" derken GET ile doğrulamadan varsayıyorum
- **Trigger:** User'ın state-değiştirici claim'leri
- **Kök sebep:** Politeness bias — "user'ı sorgulama" düşüncesi
- **Detection:** Beklenmedik error mesajları (lock conflict, "still active", "rename broken")
- **Prevention:** State-değişikliği claim'inden sonra ilk SAP işlemi öncesi GET sorgu
- **Status:** ⚠️ İLGİLİ — disiplinim
- **Vakalar:** ZSD_007 cleanup ("temizledim" denildi, ama orphan kalmıştı)

### PATTERN #6: TempScripts/'i playbook'a yansıtmama
- **Hata:** TempScripts/ altında çözüm bulunca, playbook'a yansıtmadan başka iş yapıyorum
- **Trigger:** "Şu an çalıştı, playbook'a sonra yazarım"
- **Kök sebep:** Forward bias + ergonomik kestirme
- **Detection:** Gelecek session aynı problemle karşılaşınca, TempScripts'i bulamam veya hatırlamam
- **Prevention:** AGENTS.md §4 zaten zorunlu kılıyor — başardıktan sonra playbook update
- **Status:** ⚠️ İLGİLİ — disiplinim
- **Vakalar:** Sprint 4 vaka çözümleri (auto-fallback pattern)

### PATTERN #7: Placeholder'a bakıp "pattern yok" deyip patinaj (yanlış dosya)
- **Hata:** Daha önce ÇALIŞMIŞ bir işi (FM imza+gövde push) "yapılamaz" sanıp baştan deneme-yanılmaya girdim; saatlerce 400/423/500 yedim.
- **Trigger:** Obje-tipine özel playbook dosyası **placeholder/boş** ("status: placeholder") → "demek pattern yok".
- **Kök sebep:** Çalışan pattern BAŞKA dosyadaydı (`adt-foundation.md §3.2` + canlı `ERP/.../functions/ZSD001_*.abap`); ben sadece adı eşleşen `adt-fugr-functions.md`'e baktım. Register'ın yanlış çerçevesine ("abap-adt-api comment-block ile yapıyor") demir attım, `*"` block reddedilince "ADT'den olmaz" diye yanlış genelledim. Oysa doğru = **satır-içi ABAP imzası**.
- **Detection:** "geçmişte yapılmış bir iş için neden uğraşıyorsun" (kullanıcı trigger) + reddedilen denemeler.
- **Prevention:** **Obje işi öncesi:** (1) obje-tipi playbook'u placeholder ise DURMADAN `adt-foundation.md` + `grep -r` ile repo'da **mevcut çalışan artefakt** (aynı tip `.abap`) ara, formatı KOPYALA. (2) "X ADT'den yapılamaz" sonucuna varmadan önce repo'da X'in canlı örneği var mı bak. (3) Register notunu KANIT değil HİPOTEZ say.
- **Status:** 🔴 YENİ — `feedback_playbook-once-oku` ile aynı kök (tahmin yapma, önce oku); placeholder tuzağı yeni boyut.
- **Vakalar:** 2026-06-02 C1 ZSD000_FM_SCREEN_GEN (FM imza push). Düzeltme: `adt-fugr-functions.md` artık dolu + §3.2'ye link.

### PATTERN #8: Klasik programı tek-body yazmak (include'lara bölmeme)
- **Hata:** Klasik ABAP programını (ZSD000_P_ALV_TEMP1/2/3) tüm kod tek REPORT body'sinde yazdım; std 06 §1 include-bölme kuralını unuttum.
- **Trigger:** Yeni klasik program (report/module pool/Dynpro) yazımı.
- **Kök sebep:** Standart (std 06 §1) baştan vardı (kullanıcı projenin başında koymuştu) ama yazarken hatırlamadım/uygulamadım.
- **Detection:** Kullanıcı "tek body olmamalı, include'lara bölünmeli, _CLS/_TOP standardımız vardı" (geçmiş-kural trigger).
- **Prevention:** Klasik program işine başlamadan std 06 §1 + [[feedback_klasik-program-include-bol]] oku → main=INCLUDE+event, kod T01/C01/O01/I01/F01 (PROG/I objeleri). sap-abap-dev skill tetikleme tablosunda da uyarı var.
- **Status:** 🔴 YENİ — guarantee: std 06 §1 + .rules.md + memory + skill-tetik + bu pattern.
- **Vakalar:** 2026-06-03 TEMP1/2/3 (kasıtlı tek-body bırakıldı=şablon; gerçek programda bölünür).

### PATTERN #9: Satırsız save-scan hatasında feature suçlayıp körlemesine patinaj
- **Hata:** Class push'u `OO_SOURCE_BASED / ResourceScanDuringSaveFailure` (satır no YOK) verdi → hatayı SAVE_TEXT feature'ına yükledim, EML'e geçtim, defalarca tahminle değiştirip push ettim (saatler kayboldu). Asıl suçlu **method-param `TYPE c LENGTH 100`** idi (SAVE_TEXT masumdu).
- **Trigger:** SAP class/CDS push `ResourceScanDuringSaveFailure` veya satırsız opak 400; kullanıcı "ne yapmaya çalıştığını söyle" / "bi dur".
- **Kök sebep:** Lokal ABAP derleyici yok + hata satırsız → tahmin reflexi; ayrıca push_object "Source uploaded/activated" mesajına güvendim (oysa persist olmamıştı — diff ile kanıtlandı).
- **Detection:** Kullanıcı "lokali aktif sürümle aynı yap, push et, sonra değişiklikleri tek tek yap" disiplinini dayattı → ilk atomik adımda (`TYPE c LENGTH 100`) hata yakalandı.
- **Prevention:** Satırsız save-scan'de **feature suçlama**. (1) `adt_get .../source/main` → lokali aktif SAP ile **birebir** yap, push → temiz baseline. (2) Değişiklikleri **TEK TEK** ekle+push → kıranı bul. (3) "uploaded/activated" mesajına güvenme, `adt_get` diff ile persist'i doğrula. (4) Source-based class method-param'da `TYPE c LENGTH n` KULLANMA → `TYPE string`. Detay: [[feedback_source-based-class-type-c-trap-ve-vague-scan-bisect]], adt-rap.md §34.
- **Status:** 🔴 YENİ — guarantee: memory + adt-rap §34 + bu pattern.
- **Vakalar:** 2026-06-11 ZSD001 sipariş-notu backend (manager save/get_order_texts).

---

### PATTERN #10: Junction'da `__file__`-türetimli proje kökü (D24 ihlali)
- **Hata:** Core script'i proje kökünü `Path(__file__).resolve().parents[1]` ile türetti → junction üzerinden koşunca `resolve()` CORE reposuna çözüldü; `.conn_adt`/ui-root/çıktı-dosyası yanlış repoda arandı (deploy_ui `[FAIL] ui-root yok: <CORE>/...`).
- **Trigger:** Core script proje-tarafı artefakt (`.conn_adt`, `conn/`, `<source_root>/`, `governance/`, `.claude/`) ararken CORE-köklü yol hatası; "X yok: <CORE_ROOT>/..." biçiminde FAIL.
- **Kök sebep:** K12/B10 dönüşümünde `cfg()` çağrıları eklendi ama köke giden `REPO = parents[1]` sabiti gözden kaçtı (cfg proje'den okunuyor, yol CORE'dan kuruluyordu — yarı-dönüşüm).
- **Detection:** D15 ilk normal-iş provası (`deploy_ui --verify-only`) ilk koşuda yakaladı; `rg "parents\[1\]" scripts/` taramasıyla kalan 2 script (switch_tier, build_cbo_inventory) bulundu.
- **Prevention:** Proje kökü İÇİN TEK kaynak `utils/project_config.project_root()` (env `CLAUDE_PROJECT_DIR` → cwd). `__file__` yalnız CORE-içi varlıklar için meşru (sys.path, core config/şablon). Yeni core script'te köke dokunan her yol için sor: "bu artefakt CORE'un mu PROJE'nin mi?". Denetim: `rg "parents\[1\]" scripts/ --type py` → her eşleşme ya sys.path ya core-varlığı olmalı.
- **Status:** 🔴 YENİ — fix: deploy_ui + switch_tier + build_cbo_inventory (PR, 2026-07-08); F2-P sağlık taramasına aday-denetim.
- **Vakalar:** 2026-07-08 D15 provası (<PROJECT_NAME> ilk yan-kurulum oturumu).

### PATTERN #11: `where_used` count=0 → "orphan" sanma (yokluk ≠ tüketicisizlik)
- **Hata:** Orphan-sweep'te `adt_where_used` `{ok:true, count:0}` döndü → "tüketicisi yok, silinebilir" okundu. Oysa obje **zaten silinmişti**: SAP, var olmayan obje için usageReferences'ta **HTTP 200 + boş liste** döner. "Tüketicisi yok" ile "obje yok" birebir aynı cevabı üretir.
- **Trigger:** Silmeden-önce-kullanım-kontrolü, orphan sweep, blast-radius analizi — `count == 0` / `if not results` üzerine kurulan HER karar.
- **Kök sebep:** `where_used` varlık doğrulaması yapmıyordu; boş liste iki ayrı gerçeği (yok / kullanılmıyor) tek sinyale çöktürüyordu. Araç sessizliği "temiz" gibi okunuyordu.
- **Kanıt (canlı ölçüm):** silinmiş DDLS → `get_object_structure` `SAPADTError[404]`, `where_used` `count=0`. Canlı DDLS → structure OK, `count=4`. Yani varlık sondası `get_object_structure`; `where_used` değil. **Not:** 404 her zaman `SAPObjectNotFoundError` olarak gelmez — düz `SAPADTError` + `status_code=404` de gelir; gate'i yalnız sınıf tipine bağlamak kaçırır.
- **Prevention (GATE, kod — not değil):** `SAPClient.object_exists()` eklendi; `SAPClient.where_used()` obje yoksa `SAPObjectNotFoundError` **fırlatır**. MCP `adt_where_used` obje yoksa `{ok:false, error_code:"OBJECT_NOT_FOUND"}` döner ve **`count` anahtarını HİÇ döndürmez** (çağıran onu 0 sanamaz). CLI `where_used.py` ayrı exit kodu **2** + "bunu orphan sanma" uyarısı; `[OK] No usages found` mesajı artık "(object EXISTS, verified)" der. Paylaşılan client katmanında olduğu için MCP + script yüzeylerinin İKİSİ de korunur.
- **Genel ders:** Bir araç "boş" dönerse, sorunun *önkoşulunun* sağlandığını doğrula. Boş sonuç iki farklı dünyayı (soru anlamsız / cevap gerçekten sıfır) ayırt etmiyorsa, o araç o soruya cevap veremez. Aynı sınıf: sessiz `[]`, `None`, `count:0`, HTTP 200+boş gövde.
- **Status:** ✅ SOLVED (kod gate; canlı test 5/5 — silinmiş/canlı/uydurma obje) — fix PR `fix/where-used-object-not-found`.
- **Vakalar:** 2026-07-09 <PROJECT_NAME> orphan sweep (`ZSD001_I_SOME_VIEW` tipi silinmiş CDS'te yakalandı; sweep ajanı `count=0`'a güvenmeyip envanter+grep ile çaprazladığı için yanlış silme OLMADI).

### PATTERN #12: Guard'ın kör noktaları — "komut" ile "komuttan bahis" karışır; tek yüzey kapatılır
- **Hata:** Guard kuralları **ham komut metnini** tarıyordu. Heredoc/here-string gövdesi (commit mesajı, PR gövdesi) komut DEĞİL **veri**dir → kural, kendi tarihçe notunu bloklar. Ayrıca kabuk kuralları yalnız `Bash` tool'una bakıyordu; aynı komut `PowerShell` tool'undan geçiyordu.
- **Trigger:** Bir guard, gate'i **tanıtan** commit/PR metnini reddediyor. Ya da akla "Bash'te bloklandı, PowerShell'den deneyeyim" geliyor — bu düşünce mümkünse yüzey zaten açıktır.
- **Kök sebep:** Desen `\bkomut\b` diye yazıldı, metnin **nerede** geçtiği sorulmadı. Ve kural `tool_name == "Bash"` ile sabitlendi; kabuk yüzeyi tek sanıldı.
- **Detection:** Guard kendi commit'ini bloklar (dogfood). **Tek tek yamamak tuzaktır:** bir kuralda görülen körlük tüm kurallarda vardır. Denetim: `rg "\.search\(hay\)|== .Bash." scripts/hooks/` → her eşleşme adaydır.
- **Prevention (GATE):** (1) `main()`'de TEK normalizasyon — `komut = _komut_govdesi(hay)` (heredoc/here-string gövdeleri düşer); komut-niyeti kurallarının hepsi `komut` kullanır. (2) `_KABUK_TOOLLARI` **+ `settings.json` PreToolUse matcher'ı** — ikisi birlikte (aşağıya bak). (3) Kural başına **3-eksenli** regresyon testi (`scripts/tests/test_pre_tool_guard.py`, CI'a bağlı, fixture'lı → hiçbir senaryo sessizce atlanmaz). (4) **Kablolama gate'i:** `ix_doctor.py::_kablolama_kontrol()` — guard'ın kodda koruduğu her tool, matcher'da da var mı?
- **⚠ EN ÖNEMLİ ALT-DERS — "kod-seviyesi koruma" ≠ "korunuyor":** İlk düzeltmede `_KABUK_TOOLLARI = ("Bash","PowerShell")` yazıldı, 29 senaryoluk test yeşil verdi, PR merge edildi. **Ama `settings.json` matcher'ı `Bash|mcp__sap-adt__.*` idi — hook PowerShell'de HİÇ tetiklenmiyordu.** Test guard'ı *doğrudan* çağırdığı için kablolamayı hiç sınamadı. Canlı A/B kanıtı: aynı komut Bash'te ⛔, PowerShell'de çalıştı. **Guard'ı doğrudan çağıran her test, sahte güvence üretme riski taşır** → ayrıca matcher'ı okuyan bir kablolama gate'i şart.
- **Aynı denetimde çıkan kardeş bulgular:** (a) **Koşmayan test gate değildir** — test vardı, CI çağırmıyordu; sonra çağırdı ama `CLAUDE_PROJECT_DIR` olmadığı için FREEZE'in 5 senaryosunu **sessizce atlayıp** "TUTUYOR" yazıyordu → fixture ile bağımlılık kaldırıldı, atlananlar adıyla listelenir. (b) **Yapılandırma korumayı zayıflatmasın** — `_leak_desenleri()` "ilk bulunan kazanır"dı: blocklist tanımlayan proje jenerik desenleri kaybediyordu (*daha fazla yapılandırma = daha az koruma*); artık birleşim. (c) Aynı deseni iki dosyada "bilerek aynı" yorumuyla tutmak enforcement değildir → drift'i gate'le. (d) **Fiil kara-listesi hedefi sormaz:** freeze-guard `2>&1`'deki `>`'i yazma sanıp salt-okumayı bloklarken, `python -c "open(f,'w')"` / `tar -C` / `shutil.rmtree` ile gerçek yazmayı geçiriyordu → **hedef-tabanlı** analize geçildi (`_frozen_yazma_hedefi`). (e) `hook_shim` junction kırıkken `return 1` veriyordu; PreToolUse'da bloklayan kod **2** → guard en çok gerektiği anda (kurulum bozuk) sessizce yok oluyordu → fail-closed.
- **Genel ders:** Bir gate'in **neyi** taradığı kadar **nerede durduğu**, **hangi yüzeylere kablolandığı** ve **hedefe mi yoksa metne mi** baktığı da kuralın parçasıdır. Guard yazarken üç soru: bu deseni içeren zararsız bir *metin* var mı? Aynı işi yapan ikinci bir *araç* var mı? Bu kural gerçekten o araca **bağlı** mı?
- **Status:** ✅ SOLVED — hedef-tabanlı freeze-guard + matcher + fail-closed shim + fixture'lı test + kablolama gate'i. Kanıt: 48 senaryoluk davranış korpusu (öncesi 17 bozuk → sonrası 0, **0 regresyon**), kablolama gate'i negatif testle doğrulandı.
- **Vakalar:** 2026-07-09 guard denetimi — 3 guard arka arkaya kendi commit'ini bloklad; toplu denetimde 4 kural daha aynı körlükteydi; `PowerShell` yüzeyi kodda "kapalı" sanılırken matcher'da hiç yoktu; freeze-guard salt-okumayı bloklayıp gerçek yazmayı geçiriyordu.

---

## 🔄 SELF-UPDATE PROTOKOLÜ

### Oturum BAŞLANGICI (her yeni session)
1. **OKU**: Bu dosya (LESSONS_LEARNED.md) — ACTIVE pattern'leri akıl
2. **ÇALIŞTIR**: `python scripts/sprint_gate_check.py` — gerçek state
3. **CONFIRM**: User'a sprint durumu paylaş, açık sprint varsa onay al
4. **OKU**: SESSION_NOTES.md son entry — current context
5. **READY**: Bilgilenmiş şekilde ilk işe başla

### Hata TESPİT edildiğinde (oturum sırasında)
1. TRIGGER phrase mi geldi? → Forward progress STOP
2. Bu dosyada ACTIVE pattern var mı? → Recurrence olarak işaretle
3. Yoksa → Yeni entry ekle (Hata/Trigger/Detection/Prevention/Status)
4. Code-level gate eklenebilir mi? → User'a öner
5. **Hangi katman dayatmalı?** (T11) → `scripts/hooks/README.md` §2: validator (yazım-sonrası) /
   checklist (iş-türüne özel) / **hook** (proaktif/cross-cutting) / pre_tool_guard (blokla).
   Yeni iş-türü → `skill_injector._WORKTYPES`. "İş başlarken hatırlasaydım olmazdı" diyorsan
   playbook notu YETMEZ — doğru anda dayatan katmana ekle.
6. Documentation güncelle (playbook + AGENTS.md + bu dosya)

### Oturum BİTİŞİ (büyük milestone sonrası)
1. Yeni pattern keşfedildi mi → Bu dosyaya ekle
2. Mevcut pattern Status değişti mi (ACTIVE → SOLVED) → güncelle
3. SESSION_NOTES.md kapanış raporu yaz
4. Git commit (user "git'e gönder" derse)

---

## 📊 PATTERN İstatistikleri (audit için)

| Pattern | İlk keşif | Tekrar sayısı | Status |
|---|---|---|---|
| #3 Memory Drift | 2026-05-13 | 1 (Sprint 1A todo vs SAP) | ✅ KOD GATE |
| #4 Doc ≠ Enforcement | 2026-05-13 | 2 (Namespace whitelist v1, v2) | ✅ SİSTEMATİK |
| #5 Trust Without Verify | 2026-05-13 | 2 (ZSD_007 cleanup, SHIPMENT_LIST) | ⚠️ DİSİPLİN |
| #6 TempScripts → Playbook | 2026-05-13 | 1 | ⚠️ DİSİPLİN |
| #11 where_used count=0 = orphan sanma | 2026-07-09 | 1 (orphan sweep) | ✅ SOLVED (kod gate) |
| #12 Guard kör noktası (heredoc + tek yüzey) | 2026-07-09 | 3 guard + 4 kural (denetim) | ✅ SOLVED (tek normalizasyon + CI testi) |

> **Hedef:** ACTIVE/⚠️ DİSİPLİN olanları zamanla SOLVED'a çevir (kod gate ile).

---

## 🎯 META-KURAL — "Doubt-Driven"

Bu dosyanın özü tek cümlede:

> **Bir iddiada bulunmadan önce SAP'a sor. "Tamamlandı" yerine "henüz doğrulamadım" de.**

Forward progress doğal refleks, ama **verification refleksini geliştirmek** sistemli güveni sağlar. User'ın güveni = audit dirençli iddialar = bu kural.
