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
- **KARDEŞ VAKA — 2026-07-30, `check_standard_table_fields`:** validator "bir tablo alanlarını kendi DDL gövdesinde listeler" varsayıyordu. **S/4'te bu istisna değil, KURALIN TERSİ:** canlı ölçüm — `MARA`'nın 191 alanından **doğrudan yalnız 2'si** (`key mandt`, `key matnr`) gövdede; gerisi `include emara` zincirinden geliyor · `LIKP` durum alanları `likp_status : include likp_status;` içinde (ham metinde `wbstk` **hiç geçmiyor**). Sonuç: `mara.matkl` · `mara.meins` · `likp.wbstk` referansı veren HER CDS'te yanlış bulgu. Üstelik script çıktısı `[BLOCKER]` yazarken `run_review` onu 4 yerde de **WARNING**'e eşliyordu → **şiddet kelimesi kablolamadan koptuğu için** bir ajan bunu gerçek BLOCKER sanıp rapor etti. **Fix:** include zinciri **özyineli** çözülür (structures→tables, önbellekli, derinlik 4) + çözülemeyen include kalırsa alan `YOK` değil **`DOĞRULANAMADI`** raporlanır + şiddet kelimesi kablolamayla hizalandı (script `[BULGU]` der, şiddeti `run_review` atar). **Fail-open korumayı delmedi — ölçüldü:** sentetik view'da 5 gerçek alan temiz geçti, 2 uydurma alan **hâlâ yakalandı** (exit 1); `derinlik=0` zorlamasıyla `DOĞRULANAMADI` dalının ölü kod olmadığı da doğrulandı. **Ders:** gürültü kesme ile koruma delme arasındaki sınır **ölçülür**, tasarımdan çıkarılmaz — ve include-tabanlı bir şemayı düz metin gibi okuyan her araç "yok" derken aslında "bakmadım" demektedir.

### PATTERN #12: Guard'ın kör noktaları — "komut" ile "komuttan bahis" karışır; tek yüzey kapatılır
- **Hata:** Guard kuralları **ham komut metnini** tarıyordu. Heredoc/here-string gövdesi (commit mesajı, PR gövdesi) komut DEĞİL **veri**dir → kural, kendi tarihçe notunu bloklar. Ayrıca kabuk kuralları yalnız `Bash` tool'una bakıyordu; aynı komut `PowerShell` tool'undan geçiyordu.
- **Trigger:** Bir guard, gate'i **tanıtan** commit/PR metnini reddediyor. Ya da akla "Bash'te bloklandı, PowerShell'den deneyeyim" geliyor — bu düşünce mümkünse yüzey zaten açıktır.
- **Kök sebep:** Desen `\bkomut\b` diye yazıldı, metnin **nerede** geçtiği sorulmadı. Ve kural `tool_name == "Bash"` ile sabitlendi; kabuk yüzeyi tek sanıldı.
- **Detection:** Guard kendi commit'ini bloklar (dogfood). **Tek tek yamamak tuzaktır:** bir kuralda görülen körlük tüm kurallarda vardır. Denetim: `rg "\.search\(hay\)|== .Bash." scripts/hooks/` → her eşleşme adaydır.
- **Prevention (GATE):** (1) `main()`'de TEK normalizasyon — `komut = _komut_govdesi(hay)` (heredoc/here-string gövdeleri düşer); komut-niyeti kurallarının hepsi `komut` kullanır. (2) `_KABUK_TOOLLARI` **+ `settings.json` PreToolUse matcher'ı** — ikisi birlikte (aşağıya bak). (3) Kural başına **3-eksenli** regresyon testi (`scripts/tests/test_pre_tool_guard.py`, CI'a bağlı, fixture'lı → hiçbir senaryo sessizce atlanmaz). (4) **Kablolama gate'i:** `ix_doctor.py::_kablolama_kontrol()` — guard'ın kodda koruduğu her tool, matcher'da da var mı?
- **⚠ EN ÖNEMLİ ALT-DERS — "kod-seviyesi koruma" ≠ "korunuyor":** İlk düzeltmede `_KABUK_TOOLLARI = ("Bash","PowerShell")` yazıldı, 29 senaryoluk test yeşil verdi, PR merge edildi. **Ama `settings.json` matcher'ı `Bash|mcp__sap-adt__.*` idi — hook PowerShell'de HİÇ tetiklenmiyordu.** Test guard'ı *doğrudan* çağırdığı için kablolamayı hiç sınamadı. Canlı A/B kanıtı: aynı komut Bash'te ⛔, PowerShell'de çalıştı. **Guard'ı doğrudan çağıran her test, sahte güvence üretme riski taşır** → ayrıca matcher'ı okuyan bir kablolama gate'i şart.
- **Aynı denetimde çıkan kardeş bulgular:** (a) **Koşmayan test gate değildir** — test vardı, CI çağırmıyordu; sonra çağırdı ama `CLAUDE_PROJECT_DIR` olmadığı için FREEZE'in 5 senaryosunu **sessizce atlayıp** "TUTUYOR" yazıyordu → fixture ile bağımlılık kaldırıldı, atlananlar adıyla listelenir. (b) **Yapılandırma korumayı zayıflatmasın** — `_leak_desenleri()` "ilk bulunan kazanır"dı: blocklist tanımlayan proje jenerik desenleri kaybediyordu (*daha fazla yapılandırma = daha az koruma*); artık birleşim. (c) Aynı deseni iki dosyada "bilerek aynı" yorumuyla tutmak enforcement değildir → drift'i gate'le. (d) **Fiil kara-listesi hedefi sormaz:** freeze-guard `2>&1`'deki `>`'i yazma sanıp salt-okumayı bloklarken, `python -c "open(f,'w')"` / `tar -C` / `shutil.rmtree` ile gerçek yazmayı geçiriyordu → **hedef-tabanlı** analize geçildi (`_frozen_yazma_hedefi`). (e) `hook_shim` junction kırıkken `return 1` veriyordu; PreToolUse'da bloklayan kod **2** → guard en çok gerektiği anda (kurulum bozuk) sessizce yok oluyordu → fail-closed. **(f) Guard'ın kendi yardımcı çağrısı ortam-biçimine kördü (2026-07-30):** `_repo_public_mu()` hedef repoyu `cd` önekinden çıkarıp `subprocess(cwd=)` veriyordu; Bash tool'unda yazılan `cd /c/IX/<proje> && git commit …` **POSIX** yolu Windows'ta çözülemiyor → exception → `gorunurluk-sorulamadi(fail-closed)` → **PRIVATE repo public sayılıp meşru commit bloklanıyordu.** ⚠ Ders iki katmanlı: (i) fail-closed **yön olarak** doğruydu ama *yanlış-pozitif* üretti ve yanlış-pozitif bypass alışkanlığı doğurur — "güvenli yön" tek başına yeterli tasarım kriteri değil; (ii) guard bir dış araca (`gh`) delege ediyorsa **delege çağrısının girdisi de kural yüzeyidir**: `--repo` verilen yolda cwd önemsizken, commit yolunda cwd TEK belirleyiciydi. Fix: `_win_yol()` normalizasyonu + çözülemeyen `cd` → proje köküne düşme; test: `_win_yol` birim ekseni (ağsız, her ortamda) + uçtan-uca `gh repo view` ekseni (LIVE-gated, adıyla SKIP yazdırılır) — **mutasyon testiyle dişi kanıtlandı** (fix bozulunca test FAIL verdi).
- **Genel ders:** Bir gate'in **neyi** taradığı kadar **nerede durduğu**, **hangi yüzeylere kablolandığı** ve **hedefe mi yoksa metne mi** baktığı da kuralın parçasıdır. Guard yazarken üç soru: bu deseni içeren zararsız bir *metin* var mı? Aynı işi yapan ikinci bir *araç* var mı? Bu kural gerçekten o araca **bağlı** mı?
- **Status:** ✅ SOLVED — hedef-tabanlı freeze-guard + matcher + fail-closed shim + fixture'lı test + kablolama gate'i. Kanıt: 48 senaryoluk davranış korpusu (öncesi 17 bozuk → sonrası 0, **0 regresyon**), kablolama gate'i negatif testle doğrulandı.
- **Vakalar:** 2026-07-09 guard denetimi — 3 guard arka arkaya kendi commit'ini bloklad; toplu denetimde 4 kural daha aynı körlükteydi; `PowerShell` yüzeyi kodda "kapalı" sanılırken matcher'da hiç yoktu; freeze-guard salt-okumayı bloklayıp gerçek yazmayı geçiriyordu. · 2026-07-30 — POSIX `cd /c/...` öneki görünürlük sorgusunu fail-closed'a kaçırdı; private repoya meşru commit bloklandı (aynı mesaj `cd` öneksiz geçti → A/B kanıtı).

---

### PATTERN #13: Enqueue lock-leak — session/agent mid-operation ölünce in-flight lock kalır
**Belirti:** SM12'de kendi kullanıcın (`<SAP_USER>`) üstünde stale lock: mesaj sınıfında `EU 510` (workbench), class generate/aktivasyonda `E_ABAP_GENPH` (`=HPZ`/`=HCZ` include'ları), hatta silinmiş temp objede orphan lock (`...DIAGTMP...` — `adt_syntax_check`'in geçici probe class'ı). Sonraki yazım/aktivasyon aynı kullanıcı tarafından bile **bloklanır**.
**Kök-neden:** lock alan akış (populate/create/activate) `try/finally` ile UNLOCK garanti eder AMA **process ÖLÜRSE** (401 auth-expiry, timeout, agent-kill) finally HİÇ çalışmaz → lock canlı kalır. `clear_enqueue_lock` kurtaramaz: release için önce **acquire** gerekir, o da bloke. Yani in-process safety-net session-ölümünü YAKALAYAMAZ.
**Ayırt et — CANLI mı STALE mı (kritik):** Aktif SAP-yazıcısı (gateway) **çalışıyorsa** lock CANLI olabilir → silme, işi bozarsın. Gateway görevi bittiyse/öldüyse + başka yazıcı yoksa → STALE. Kanıt: `adt_get`(temp obje exists=false → orphan lock) + `adt_lock_check` + gateway'in aktif olup olmadığı (SendMessage "no active task" = ölü).
**Kurtarma:** STALE ise **kullanıcı SM12'den elle siler** (kendi lock'u, ADR 0005-C: AI force-clear ETMEZ). Silinen shell/temp arkasında kayıp iş yok (boş shell / silinmiş obje).
**Önleme (pre-flight):** gateway her obje yazımından ÖNCE `adt_lock_check` → kendi stale lock'u varsa aktivasyonun ORTASINDA patlamak yerine ERKEN yüzeye çıkar + lider'e bildirir. **Robust auto-recovery** (pre-flight kendi-stale-lock'unu programatik temizle) = paylaşılan lib lock-döngüsü riski + ADR 0005-C sınırı → **deferred tooling task** (aceleye getirme). Kanıt: ZSD001 EXCUPL msgclass EU 510 + class E_ABAP_GENPH 2026-07-12.

### PATTERN #14: Gate/veri DEVREYE ALMA — "koştu" ≠ "baktı"; muafiyetsiz açılış FP seli doğurur
**Belirti:** Bir kontrol yeşil veriyor ama hiçbir şeye bakmıyor (fail-open); ya da yeni açılan bir kontrol tek seferde onlarca bulgu döküyor ve bulgular triage edilmeden kural gevşetiliyor.
**Üç ayrı hastalık, aynı aile:**
- **(a) Fail-open sessiz PASS** — veri/önkoşul yoksa `return {}` / `except: return ""` → exit 0 → reviewer PASS. Canlı vaka: `check_released_objects.py` haritası hiç üretilmemişti (`refresh_released_successors.py` çıktı klasörünü yaratmıyordu → taze klonda `FileNotFoundError`), validator boş harita ile aylarca PASS verdi. Kardeşleri: guard damga-kontrolünde `except: return ""`, path-parse bug'ı yüzünden "ölü" freeze-guard, 0 token çıkaran proje-lokal validator. **Ortak imza: kontrol koştu ≠ kontrol baktı.**
- **(b) Muafiyetsiz/geniş-detektörlü açılış → FP seli** — bir liste-ekranı detektörü ilk taramada 10 bulgu verdi, **10'u da false-positive** çıktı (meşru detay-form tabloları). Sezgisel eşikler (">=5 kolon") kaldırılıp detektör exact-logic'e daraltılınca 10→0 oldu; **gerçek backlog yoktu.** Aynı aile: her oturum sahte "drift" bağıran imza kontrolü → *yanlış-pozitif üreten uyarı, gerçek uyarı geldiğinde görülmez.*
- **(c) Kabul edilmiş eski ihlal ↔ yeni ihlal ayırt edilemez** — WARNING seviyeli bir kontrol açıldığında eski kod stoğu her koşuda yeniden listelenir. Kural metni genelde "WARNING'i düzelt" değil **"sessiz geçme = gerekçeni bildir"** der; gerekçe SESSION_NOTES'a yazılır ama **koşum çıktısında görünmez** → üçüncü göz için yeni ihlal eski yığının içinde kaybolur.
**Devreye alma sırası (ZORUNLU — atlanırsa üstteki üç hastalıktan biri kesin):**
1. Detektörü **dar** yaz (exact-logic; sezgisel eşik yok). 2. **warn-first** koş (exit 0), repoyu tara. 3. Bulguları **triage et** — FP mi, gerçek legacy mi? (FP'yi muafiyete yazma; detektörü düzelt.) 4. Gerçek legacy'yi **isim-isim** `project.yaml`'a yaz (core'a GÖMME) + satır-içi gerekçe + **çıkış şartı**. 5. Kuralı `standards/` + checklist satırına yaz, `# ENFORCES:<ID>` ver. 6. **İki fixture:** muaf-olmayan ihlal FAIL **ve** muaf giriş PASS. 7. 0 bulgu → ancak o zaman HARD'a terfi. 8. Anahtarı `MAINTENANCE.md` §6 kataloğuna ekle. 9. ADR 0019 5-şart + **açık kullanıcı onayı** (gömülü onay saymaz).
**Grandfather deseninin 5 değişmezi** (kurulu üç örnekten türetildi — `include_naming_exempt`, `package_exceptions`, `cds_legacy_sqlview_exceptions`): ① muafiyet **projede**, gate **core'da** · ② kural gevşetilmez, **liste** verilir (yeni ihlal aynı gate'e takılır) · ③ her girişte gerekçe + çıkış şartı ("rename edilince listeden SİL") · ④ muafiyet kural metninde **ilan edilir** (gizli muafiyet yok) · ⑤ gate ID'si coverage-check'e bağlı kalır.
**Bilinen boşluk (kabul edilmiş):** muafiyet girişlerinin hâlâ gerekli olduğunu denetleyen bir gate YOK — listeden silmek insan hafızasına bağlı. Yeni gate açmak yerine (moratoryum) her girişe **çıkış şartı yorumu** yazmak zorunlu kılındı.
**Genel ders:** Bir kontrolü açmak = üç soruyu yanıtlamak: **veri/önkoşul gerçekten var mı** (yoksa fail-loud mu fail-open mu?), **ilk tarama kaç bulgu veriyor ve kaçı gerçek**, **eski stok yeni ihlali gizler mi**. Üçü yanıtlanmadan "gate aktif" demek, gate'i açmak değil, **gate hissi** üretmektir.
**Status:** ✅ AKTİF ders — kaynak: 11 vakalık gate-arkeolojisi (2026-07-26); ADR 0019 (gate-moratoryumu) + ADR 0006 (reviewer WARNING semantiği) ile birlikte okunur.

### PATTERN #15: `git diff A...B` (üç-nokta) ile "merge edilmemiş iş" yanılsaması
**Belirti:** Ölü-dal temizliğinde/denetimde bir dal için "N satır merge edilmemiş iş var" alarmı verilir; dal aslında tamamen süperseded ve main **ondan ileridedir**.
**Kök-neden — iki sözdizimi, iki AYRI soru:**
- `git diff A...B` (**üç nokta**) = *merge-base(A,B) → B*. "Bu dal **kendi ömrü boyunca** ne yaptı?" Sorunun içinde `A`'nın **bugünkü** hali YOKTUR — A o sırada aynı işi başka yoldan almış olsa bile diff küçülmez.
- `git diff A..B` (**iki nokta**) = *A → B*. "Şu anda aralarında ne fark var?" Ölü-dal / kayıp-iş kararı **YALNIZ bunu** sorar.
- `--stat` çıktısı ikisinde de aynı biçimde görünür → yanlış olan diff **yanlış görünmez**, sadece büyük görünür. Sinyal yok.
**Neden squash-merge'de kaçınılmaz:** squash, dalın commit'lerini main'e **yeni bir SHA** olarak koyar. Dalın kendi commit'leri main'in tarihçesinde HİÇ görünmez → `git branch --merged` dalı "merge olmamış" sayar, `git log main..dal` commit listeler, `A...B` de tüm dal-diff'ini gösterir. **Üç sinyal birden aynı anda yanıltır** ve birbirini "doğruluyor" gibi okunur.
**Doğru karar zinciri (ölü dal / kayıp iş):**
1. `git diff main..<dal>` → benzersiz "+" satırı **0** ise dal main'in tam alt kümesidir, tartışma biter.
2. "+" satırı varsa **yönü oku**: `-` satırları = main'de olup dalda olmayan (dal geride). `+` satırları teker teker bakılır — çoğu zaman **kaldırılmış/süperseded** eski sürümlerdir.
3. Hakem kanıt **PR durumudur**: `gh pr list --state merged --json headRefName` ile dal adını eşle. Merged PR = dalın diff'i o an main'e girdi; sonrası main'in evrimidir, kayıp değil.
4. PR'ı olmayan dal → asıl dosyaları main ile **birebir kıyasla** (`git diff main..dal -- <dosya>`); değişmemiş dosya = iş main'de.
**Genel ders:** Aynı komutun iki noktalama biçimi iki farklı soruya cevap veriyorsa, hangisini sorduğunu **komutu yazmadan önce** söyle. "Fark" tek kelime ama en az iki anlamı var: *bu dal ne üretti* ≠ *bugün ne eksik*. Aynı sınıf: `log A..B` vs `log A...B`, `--merged` (tarihçe-temelli) vs içerik-temelli kapsanma.
**Prevention:** GATE YOK (moratoryum — sonuç geri alınabilir: silinen dal reflog/uzak ref ile geri gelir, üstelik yanılgı fazla-temkinli yönde çalışır → veri kaybı değil, yanlış alarm üretir). Disiplin: silme kararı **`..` + PR eşleşmesi** ikilisine dayanır; `...` yalnız "bu dal ne yaptı" sorusunda kullanılır.
**Status:** ⚠️ DİSİPLİN — kaynak: 2026-07-27 ölü-dal temizliği (22 dal, 2 repo).
**Vakalar:** 2026-07-27 — PR'sız bir çekirdek dalı için `main...dal` "748 satır, 12 dosya merge edilmemiş" dedi; `main..dal` ölçünce dal main'in **5.162 satır gerisindeydi** ve kendine ait 51 satırın tamamı süperseded çıktı (kaldırılmış guard referansları, hardcode yol, terk edilmiş safety-net). Yanlış alarm; dal güvenle silindi.

### #17 — Çapraz-kesen işte KATMAN KATMAN KEŞİF (envantersiz ilerleme)

**Belirti:** iş "küçük bir düzeltme" sanılır; her düzeltme bir sonraki eksiği doğurur; kapsam
yol boyunca büyür; kullanıcı *"neden bu kadar uzadı / neden tek tek yapıyorsun"* der.
**Kök sebep:** davranış **çapraz-kesen** (BE kuralı + FE akışı + mesaj + veri, ve/veya çok app)
olmasına rağmen **hiçbir noktada yüzeyin tamamı taranmamıştır.**
**Vaka (2026-07-29, silme kontrolü):** "3 app'lik FE düzeltmesi" sanıldı → tam tarama sonrası
**7 app + 2 backend boşluğu + canlıda yetim veri**; silme yolu 14 → **24**; aynı hata sınıfının
**7 varyantı**; **6 review turu**. Bir app hiçbir review'un kapsamına girmediği için gözden kaçtı
(kullanıcı "atladığımız bir şey kalmasın" demeseydi kaçacaktı).
**Prevention:** GATE YOK (moratoryum — bu bir yöntem disiplinidir, statik olarak yakalanamaz).
Kanonik sıra: **runtime'da teyit → envanter/matris → tek iş listesi + tahmin → kapsam kararı (toplu)
→ deseni dondur → çoğalt → tek review turu → runtime kabul.**
📖 Tam yöntem, yapılacaklar/yapılmayacaklar tablosu ve öz-değerlendirme listesi:
**`playbook/howto-cok-katmanli-degisiklik.md`** (tek-ev; burada tekrarlanmaz).
**Status:** ⚠️ DİSİPLİN.

### #18 — BAYAT SAYI / SATIR REFERANSI (yorumdaki sayı kod kadar bayatlar)

**Belirti:** yorum "N obje", "N doğrulama metodu", "dosya:satır", "canlıda X yok" der; ölçülünce
**yanlış** çıkar. Hiçbir validator yorumdaki sayıyı doğrulamaz.
**Vaka (2026-07-29, tek turda 6 kez):** "7 obje" (gerçek 9) · "10 doğrulama metodu" (gerçek 13;
satırın kendi listesi zaten 12 diyordu = baştan tutarsız) · "canlıda bağlı teslimat yok"
(SQL: 26 satır var — **iki ayrı ajan bunu kanıt sanıp aktardı**) · yorum içi `dosya:satır` **iki kez**
üst üste bayatladı (düzeltmenin kendisi satırları kaydırdı) · "0 bayat referans kaldı" iddiası
(denetim grep'i **dar desenliydi**, kardeş-dosya referanslarını görmüyordu).
**En öğretici hâli:** *"satır no yazma, içerik-çapası kullan"* diyen yorum bloğunun **kendisi**
3 bayat satır numarası taşıyordu.
**Prevention:** GATE YOK (moratoryum — §4 "önce doküman denendi ve yetmedi" henüz karşılanmadı).
Yazım disiplini: **(a)** sayı yazarken **ölçüm tarihini** de yaz · **(b)** aynı dosya içinde
**içerik çapası** kullan, satır numarası değil · **(c)** çapraz-dosya referansını **sembol adına**
bağla (*"ada göre ara: `<sembol>`"*) · **(d)** **sayıyı tazelemek sınıfı çözmez** — çapaya çevir ·
**(e)** yorumdaki **veri iddiasını** (canlıda X var/yok) ölçmeden aktarma ·
**(f) TABAN-ÖLÇÜM — bir işlemin başarısını İDDİAYLA değil İKİ SAYIYLA kanıtla.** `rc=0` /
`HTTP 200` / `[OK]` bir iddiadır, sonuç değil. İşlemden **ÖNCE taban**, işlemden **SONRA hedef**
ölç; kanıt ikisinin **farkıdır**. Örnekler: GUI status buton sayısı **0→5** · text-pool sembol
sayısı **6→35** · mesaj sayısı **37→38** · inaktif-worklist **1→0**. Taban alınmadıysa "sonra"
değeri hiçbir şey kanıtlamaz (zaten öyle olabilirdi).
**(g) "X ÇÜRÜDÜ" bir cümle değil, bir KOŞULDUR.** Bir çürütme notu yazarken **hangi koşulda**
çürüdüğünü de yaz (hangi obje tipi · hangi bağlam · hangi sürüm/uç nokta). Koşulsuz yazılmış
çürütme notu, sonraki turda **hâlâ geçerli olduğu yerde de** kullanılmaz → yanlış kanal/yöntem
seçtirir; yani fazla-genelleme, bilgiyi silmekle aynı sonucu verir. Uygulanmış örnek:
[`adt-fugr-functions.md`](adt-fugr-functions.md) §3.1 (SOAP-RFC vakası koşullu yazıldı).
**Status:** ⚠️ DİSİPLİN — kaynak: 2026-07-29 silme kontrolü turu · (f)/(g) 2026-07-31.

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

### PATTERN #16: Arama aracının KAPSAMI sonucun anlamını belirler — `0 eşleşme` "yok" demek değildir
- **Hata:** `adt_grep_source(package=…, object_types="…,FUGR")` çalıştırıldı, `match_count: 0` döndü, "bu paket o tabloyu kullanmıyor" sonucuna varıldı. **Yanlıştı** — FM tabloyu okuyordu. Tool FUGR için yalnız **iskelet ana include**'u çeker (`/functions/groups/<fg>/source/main` = iki satır `INCLUDE`); FM gövdesi `L<FG>U01`'dedir ve **hiç taranmaz**.
- **Neden sinsi:** Sonuç *yapı olarak* başarılıdır — `ok: true`, `scanned_objects: 7`, **`truncated_object_scope: false`, `truncated_matches: false`**. Yani aracın "kesme yaptım" bayrakları bile temiz. `scanned_objects` "tarandı" der ama **ne** tarandığını söylemez. Sessiz-kesme detektörü sessiz-kapsam'ı yakalamaz.
- **Trigger (altın sinyal):** **İki araç çelişiyor** — `adt_where_used` objeyi listeliyor ama `adt_grep_source` 0 döndürüyor. Bu çelişki neredeyse hiçbir zaman veri değil, **kapsam farkı**dır: `where_used` DDIC bağımlılık indeksinden okur (derleyicinin gördüğü), grep indirdiği metinden. **Çelişkide indeks haklıdır.**
- **Detection:** "Aramada çıkmadı" ile "yok" arasında kalınca sor: *bu araç o objenin kaynağını gerçekten indiriyor mu, yoksa bir sarmalayıcı mı indiriyor?* Şüphede tek bir objeyi elle indir ve gözle bak.
- **Prevention:** (1) Negatif sonucu **ikinci, farklı-mekanizmalı** bir araçla çapraz-doğrula (grep ↔ where_used ↔ indeks). (2) Kapsam sınırını **dokümante et** — `adt-fugr-functions.md §4.1` (FUGR körlüğü, çalışan include-indirme yöntemi). (3) Tool düzeltilebiliyorsa asıl çözüm odur: FUGR'da FM include'larını da tara (**ADT-altyapısı değişikliği → açık onay şart**).
- **Akraba pattern:** **#11**'in aynadaki hâli. #11: `where_used count=0` → "orphan" sanma (obje yoksa da 0 döner). #16: `grep count=0` → "kullanılmıyor" sanma (araç bakmadıysa da 0 döner). **Ortak çekirdek: `0`, "arananın yokluğu" değil "aracın bulamaması"dır.** Aynı çekirdek D29'da da var (junction arkasını `Grep`/`Glob` sessizce boş döndürür).
- **Status:** ⚠️ DİSİPLİN (doküman + çapraz-doğrulama refleksi). Tool-fix önerildi, onay bekliyor.
- **🔻 KARDEŞ VAKA — aracın KENDİ TEŞHİSİ yanlış olabilir (2026-07-28):** `adt_classrun` sağlam bir sınıf için *"Class does not implement if_oo_adt_classrun~main!"* döndürdü **ve yanına hazır bir teşhis bastı**: *"class-LOAD-cache binding bozulması; ÇÖZÜM: TAZE sınıf adıyla yeniden yarat"*. Reçete uygulandı — taze isimle **aynı hata**. Gerçek sebep bambaşkaydı: çağıran header'ı `_request_with_csrf_retry`'dan ÖNCE kuruyordu, soğuk session'da token o dict'e hiç yazılmıyordu → istek CSRF'siz gidiyor, SAP 403 yerine **200 + yanıltıcı gövde** dönüyordu. **Ders: bir aracın gömülü teşhisi de bir iddiadır — kanıt değil.** Reçetesini uygulayıp sonuç değişmiyorsa, bu **teşhisin kendisine karşı kanıttır**; daha çok denemek yerine teşhisi bırak. **Bedeli:** yanlış teşhis, araştırmacıyı gereksiz bir ikinci obje yaratmaya sevk etti. Kök-fix + `scripts/tests/test_csrf_header_injection.py` (A/B kanıtlı: fix kapalı → exit 1) + teşhis metninde artık iki sebep sıralı veriliyor. *Sinyal: "bulunamadı/başarısız" mesajının yanında gelen **hazır çözüm önerisi**, hatanın kendisi kadar şüpheli.*
- **🔻 KARDEŞ VAKA — İKİNCİ TUR: TEŞHİSİN KENDİSİ KANIT GEREKTİRİR (2026-07-31, `adt_classrun` kök-fix):** Yukarıdaki vakanın ardından `adt_classrun` yine *"does not implement if_oo_adt_classrun~main"* dedi ve bu kez sonuç **"araç bu sistemde GÜVENİLMEZ/BOZUK; çare taze bir sınıf adı"** diye **6 dokümana yazıldı**. Canlı ölçüm bunu çürüttü: **araç bozuk değildi, SAP'nin mesajı DOĞRUYDU.** İki bağımsız hata birleşip yanlış sonucu üretmişti.
  - **HATA 1 — teşhis fonksiyonu YANLIŞ SÜRÜMÜ okuyordu.** `_diagnose_classrun_binding`, `source/main`'i **`version=` parametresi vermeden** GET ediyordu ve **ADT'nin varsayılanı İNAKTİF sürümdür**. Aynı sınıf, aynı an: parametresiz GET → **10.659 bayt, arayüz VAR** · `version=active` → **192 bayt boş kabuk, arayüz YOK**. Yani sınıf **hiç aktive edilmemişken** teşhis "yapısal olarak geçerli" diyordu; oradan da mantıken *"kod sağlamsa suçlu tooling'dir → taze class adı dene"* doğuyordu. Gerçek durum: sınıf push edilmiş ama **AKTİVE EDİLMEMİŞTİ**.
  - **HATA 2 — bayat uzun-ömürlü oturum.** Sınıfın aktif olduğu **kanıtlandıktan sonra** (`adt_inactive_objects` = 0, syntax temiz) hata **sürdü**. İstemci, süreç ömrü boyunca TEK `requests.Session` tutuyor (`x-sap-adt-sessiontype: stateful`); obje **başka bir süreçte** aktive edildiyse bu sürecin SAP oturumu aktivasyonu görmez, eski class-load'a bağlı kalır. Aynı çağrı **taze bir süreçte anında** çalıştı. **Süreç-içi retry ELENDİ** — kod zaten aynı oturumda iki kez POST ediyordu, ikisi de aynı hatayı verdi: çare retry değil **RESET** (`activate() → new_session() → execute()`; aynı desen `jfilak/sapcli` `d223ed3c`).
  - **DENENEN — BAŞARISIZ:** *"taze (hiç kullanılmamış) class adıyla yeniden yarat"* — **iki kez** uygulandı, **çözmedi**, geriye **iki gereksiz obje** bıraktı. Bir reçeteyi uygulayıp sonuç değişmiyorsa bu, **reçeteyi doğuran teşhise karşı kanıttır**; üçüncü kez deneme, teşhisi bırak.
  - **META-DERS (bu ailenin çekirdeği):** **Yanlış veri okuyan bir teşhis, GÜVENLE yanlış bir reçete üretir** — ve o reçete "araç bozuk" diye terfi eder, dokümanlara yayılır, sonra herkes ona dayanır. **Teşhisin KENDİSİ kanıt gerektirir:** hangi veriyi, hangi sürümünü, hangi parametreyle okuduğunu sor. Burada **tek eksik parametre** (`version=active`) → 6 dokümana yanlış bilgi, 2 gereksiz obje, saatlerce yanlış yerde arama.
  - **YAN BULGU (bağımsız değerli):** `adtcore:version="active"` metadata'sı **boş kabuk için de "active" der** → **tek başına aktivasyon kanıtı DEĞİLDİR.** Güvenilir kanıt **`adt_inactive_objects`** + aktif kaynağın içerik/bayt kıyası.
  - **Status:** ✅ KÖK-FIX (teşhis artık `version=active` okuyor · `new_session()` + reset'li retry · yanıltıcı teşhis metni yeniden yazıldı) + doküman geri-alması. Vaka evi: [`adt-classes.md`](adt-classes.md) §24.9.
- **🔺 KARDEŞ VAKA — AYNANIN ÖTEKİ YÜZÜ: `1 eşleşme` de "var" demek değildir (2026-07-30):** Bir inceleme ajanı, riskli bir CDS konstrüksiyonu için *"classic view emsali BULDUM"* dedi ve dosya+satır verdi — **risk kapandı sanıldı ve lider bunu aşağıya da yukarıya da aktardı.** Build ajanı sevinerek kabul etmedi, **ölçtü ve çürüttü:** gösterilen obje `define view **entity**`'ydi (classic değil) ve `@AbapCatalog.sqlViewName` o dosyada **tek bir yerde** geçiyordu — **bir YORUM satırında**, üstelik cümlenin anlamı *"sqlViewName **YOK**"* idi. Yani grep, aradığı token'ı **kendi yokluğunu ilan eden cümlenin içinde** buldu ve "var" sinyali üretti. Bağımsız süpürme kesinleştirdi: o konstrüksiyonu içeren 12 dosyanın `sqlViewName` taşıyanı **yalnız aktive edilmeye çalışılan dosyanın kendisiydi** — yani emsal **hiç yoktu**.
  - **Ortak çekirdek genişliyor:** #16 *"`0`, arananın yokluğu değil aracın bulamamasıdır"* diyordu. Ayna hâli: **`>0`, arananın varlığı değil, aracın bir dizgeye çarpmasıdır.** Token'ın **hangi sözdizimsel bağlamda** (yorum · dizge sabiti · olumsuzlama · dokümantasyon) geçtiği sorulmadıkça eşleşme kanıt değildir.
  - **Neden bu sinsi:** olumsuzlama **eşleşmeyi artırır**. Bir şeyin yokluğunu belgeleyen yorum (`// X YOK`, `# no longer uses Y`, `⛔ Z KULLANMA`), o şeyi arayan her grep'e **isabet** verir. Yani *iyi belgelenmiş* kod tabanları bu hataya **daha açıktır**.
  - **Prevention:** (1) Emsal/varlık iddiasını **tanımlayıcı satırdan** doğrula, arama isabetinden değil — CDS'te `define view` ↔ `define view entity`, tabloda `define table`, sınıfta `CLASS … DEFINITION`. (2) Aday listesini **iki koşulun kesişimiyle** daralt (hem konstrüksiyon hem tip), tek grep'le değil. (3) **Çelişkide ölç:** iki ajan/araç çelişiyorsa üçüncü, mekanizması farklı bir ölçüm yap — burada canlı `adt_get` metadata (`source_type="view entity"`) kesin kanıttı.
  - **Yönetsel ders (en az teknik kadar önemli):** *"riski kapattım"* haberi, *"risk var"* haberinden **daha sıkı** doğrulanmalıdır — çünkü kabul edilirse bir güvenlik ağı (burada: kaynağa yazılmış fallback) **kaldırılır**. Build ajanı iyi haberi reddedip fallback yorumunu yerinde bıraktı; aksi hâlde kaynağa **yanlış bir kanıt iddiası** gömülecek ve ileride biri ona dayanıp fallback'i silecekti.
- **Vakalar:** 2026-07-28 — bir Adobe-Form paketinin plaka-ayrıştırma işinden **etkilenip etkilenmediği** araştırılırken; `where_used` FM'i listeliyordu, paket grep'i 0 diyordu. Include indirilince bağ **gerçek** çıktı (ama okunan tek alan farklıydı → sonuçta etki yoktu). Kanıtsız "yok" denseydi, blast-radius eksik kalırdı.

---

### PATTERN #19: *"Araç bozuk"* KARŞILAŞTIRMALI bir iddiadır — kontrol grubu olmadan kurulamaz

- **Hata:** Bir araç beklenen sonucu vermeyince, **yalnız sorunlu obje üzerinde** denemeler yapılır (header varyantları, retry, farklı isim, farklı oturum tipi…), hepsi başarısız olur ve sonuç *"araç bu sistemde bozuk/güvenilmez"* diye yazılır. Oysa araç **hiçbir zaman çalıştığı bilinen bir örnek üzerinde koşulmamıştır.**
- **Neden sinsi:** Denemeler *çoğaldıkça* "araç bozuk" hipotezine olan güven **artar** — ama hepsi aynı kirli girdiyi kullandığı için hiçbiri hipotezi test etmez. Beş başarısız varyant, bir kontrol grubunun verdiği bilginin **hiçbirini** vermez. Üstelik uğraşılan süre, sonuca duyulan güveni haksız yere büyütür ("bu kadar denedik, demek ki gerçekten bozuk").
- **Kural:** *"X bozuk"* ile *"X bu objede çalışmadı"* **farklı cümlelerdir**. Birincisini kurmak için **iki** ölçüm gerekir: sorunlu vaka **+ çalıştığı bilinen vaka**. İkincisi yoksa elindeki iddia yalnız ikincisidir — dokümana da öyle yazılır.
- **Kontrol grubu seçerken:**
  1. **Yan etkiye bak, adına değil.** Vakada uygun görünen 13 adayın **hepsi** yazma yapıyordu (12'si doküman üretiyor, biri `DELETE`+`COMMIT`). "Runner", "test", "probe" gibi masum adlar hiçbir şey garanti etmez — **gövdesini oku**.
  2. Yan etkisiz aday yoksa **yarat**: `$TMP`'de en basit hâli (bir satır çıktı), aktive et, koş, sil. Ucuzdur ve kesin cevap verir.
  3. Kontrol grubunun **gerçekten sağlam olduğunu** ölç (burada: `adt_inactive_objects` = 0). Kontrol grubun da hastaysa deney anlamsızdır.
- **Prevention (sıra önemli):** ① **ÖNCE HAFIZAYI ARA** (aşağı bak) → ② kontrol grubu koş → ③ hipotez üret → ④ ancak o zaman "araç" sonucuna git.
- **🔻 İKİZ KURAL — tanıdık semptomda önce hafızayı ara; cevap zaten yazılmış olabilir:** Bu vakanın HATA 2'si (bayat oturum) **bir ay önce, 2026-06-30'da çözülmüş ve kayda geçmişti**: *"BOZUK YANLIŞTI — kod bug'ı değil, bayat süreç; çözüm `/mcp` reconnect."* Semptom 2026-07-30'da tekrar geldi, **kayıt okunmadı**, sıfırdan hipotez kuruldu ve **üstüne yanlış sonuç yazıldı** — yani doğru bilgi yanlışıyla **değiştirildi**. Semptomun tanıdık gelmesi bir sezgi değil **sinyaldir**: playbook + lessons-learned + memory'de arama yapmadan teşhis koyma. *Bir kuralı ikinci kez öğrenmenin bedeli, birinci kez öğrenmekten yüksektir — çünkü arada ona dayanan kararlar alınır.*
- **🔻 ÜÇÜNCÜ KURAL — pahalı bir çare ilk denemede işe yaramadıysa, ikinci kez deneme: çareyi doğuran KANITI sorgula.** Vakada "taze class adı" **iki kez** uygulandı. Birincisi başarısız olduğunda sorgulanacak şey sınıfın adı değil **reçetenin dayanağıydı** — ki dayanak bir ölçüm değil, bir teşhis fonksiyonunun çıktısıydı (bkz. #16, HATA 1).
- **Bedel (2026-07-31 vakası):** 1 eksik query parametresi → 6 dokümana yanlış bilgi + 1 core PR + auto-memory kaydı + 2 gereksiz Z obje + bir gün "harici bir kanala bağımlıyız" varsayımıyla planlama + saatlerce yanlış hipotez (çok-app-server asimetrisi · CSRF · bare-header · taze isim). **Kontrol grubu bunu ilk yarım saatte bitirirdi.**
- **Akraba:** **#16** (teşhisin kendisi kanıt gerektirir) — #16 *teşhisin girdisini*, #19 *sonucun kurulma biçimini* denetler. İkisi birlikte: **kanıt hem doğru veriden okunmalı hem karşılaştırmalı olmalı.**
- **Status:** ⚠️ DİSİPLİN. Vaka evi: [`adt-classes.md`](adt-classes.md) §24.9-A.

---

### PATTERN #20: Salt-okunur SANILAN araç yazıyordu — yetki sınırını **ad ve doküman değil, ÖLÇÜM** belirler

- **Hata:** Bir tool'un **adına** (`*_check`, `*_get`, `*_list`, "preaudit", "dry-run") ve
  **docstring'ine** bakılarak "okuma" kovasına konur; ajan allowlist'lerine, tek-yazıcı
  mimarisine ve "bunu çağırmak zararsızdır" refleksine bu sınıflandırma temel yapılır.
  **Hiç ölçülmemiştir.**
- **Vaka (2026-07-31):** `adt_syntax_check` **salt-okunur sanılıyordu** — docstring'i açıkça
  *"performs a syntax check without actually activating the object"* + *"activationExecuted
  will be false"* diyordu. Ölçüm bunu çürüttü: tool
  `POST /sap/bc/adt/activation?method=activate&preauditRequested=true` çağırıyor ve bu sistemde
  preaudit **onurlandırılmıyor** → bekleyen inaktif sürüm **temizse objeyi AKTİVE ediyor**
  (`adt_inactive_objects` **1 → 0**; `?version=active` kaynağı push edilene eşitlendi), hatalıysa
  etmiyor. Gerçek semantiği **"hatasızsa aktive et"**.
- **Neden sinsi — üç kat:**
  1. **Ad ikna edicidir.** "check" kelimesi, kimsenin sormadığı bir yetki iddiasında bulunur.
  2. **Yan etki BAŞARILI durumda ortaya çıkar.** Hata varsa aktive etmiyor → tool "gerçekten
     sadece kontrol ediyor" gibi görünüyor; yazma yalnız her şey yolundayken oluyor, yani
     **kimsenin bakmadığı anda**.
  3. **Araç kod göndermez** — çağrıda yalnız obje adı gider, SAP **sunucudaki bekleyen sürümü**
     devreye alır. Yani çağıran, gönderdiğini değil **orada duranı** aktive eder; bilinçli
     bekletilen bir aktivasyon (co-activation sırası, def/impl include çifti) varken **sırayı bozar**.
- **YÖNTEM — bir tool'u "read-only" kovasına koymadan önce yan etkisini ÖLÇ:**
  ```
  TABAN ölç  →  tool'u ÇAĞIR  →  TEKRAR ölç  →  fark var mı?
  ```
  Ölçüm için tool'un kendi ailesinden **bağımsız** bir sayaç seç (burada: `adt_inactive_objects`
  worklist sayısı; ayrıca `?version=active` kaynağın bayt/içerik kıyası). Tool'un **kendi
  dönüşünü** kanıt sayma — `activationExecuted:false` tam da bu vakada yanıltıcıydı.
  (Taban-sonra ölçüm ilkesi: #18 (f).)
- **Neden bu bir MİMARİ mesele, sadece doküman hatası değil:** single-writer mimarisinde
  "okuma" kovası ajan **tool-allowlist'lerine** dönüşür. Yanlış sınıflandırılmış bir tool,
  yazma yetkisi olmayan rollere sessizce yazma yeteneği verir — ilke ihlal edilir ama
  **hiçbir gate ötmez**, çünkü ihlal izin katmanının kendi içindedir.
- **⚠ Kaynağı düzelt, dokümanı değil (yalnız):** yanlış bilgi **kodun docstring'inde**
  durduğu sürece her okuyan yeniden yanılır; playbook'a not düşmek onu **çürütmez**, yanına
  ikinci bir gerçek koyar. Bu vakada `scripts/sap_adt_lib.py::syntax_check_via_activation`
  docstring'i ölçülen davranışa göre yeniden yazıldı (davranış DEĞİŞMEDİ — kasıtlı: karar
  kullanıcınındır, düzeltilen yalnız **iddia**).
- **Akraba:** **#16** (teşhisin girdisi kanıt gerektirir) · **#19** ("bozuk" karşılaştırmalı
  iddiadır). Üçünün ortak çekirdeği: **araç hakkındaki her cümle — adı, docstring'i, teşhisi,
  dönüş bayrağı — bir İDDİADIR; kanıt yalnız ölçümdür.**
- **Status:** ⚠️ DİSİPLİN + kaynak-fix (docstring). Tool semantiği evi:
  [`adt-mcp.md`](adt-mcp.md) "Tool SEMANTİĞİ"; envanter tablosu `docs/ix-works-mimari-kilavuzu.md` §10.1.

---

### PATTERN #21: S/4'te **classic DDIC view + "tablo-değiştirme" (replacement) tablosu = SESSİZ 0 SATIR**

*(applies_to: `s4_private` · `s4_public` — ECC'de bu sınıf YOKTUR)*

- **Hata:** S/4'te bir classic DDIC view (`@AbapCatalog.sqlViewName`'li DDIC-based CDS view ya
  da SE11 view) `MSEG`/`MKPF` gibi bir tablo üzerine kurulur. Aktive olur, sözdizimi temizdir,
  ATC susar, `adt_inactive_objects` 0 der — ve view **hep 0 satır** döner. Hiçbir hata yok.
- **Mekanizma:** S/4'te bu tablolar birer **tablo-değiştirme (table replacement) objesidir**
  (`DD02L-VIEWREF` dolu; ör. `MSEG → NSDM_V_MSEG`). Gerçek veri başka bir tabloya taşınmıştır
  (MM-IM'de `MATDOC`) ve **fiziksel tablo BOŞTUR**. Yönlendirme **Open SQL katmanındadır**:
  ABAP `SELECT ... FROM mseg` çalışır. Ama **classic DDIC view DB seviyesinde üretilir ve
  fiziksel tabloyu okur**; onun yönlendirilmesi ayrı bir mekanizmaya bağlıdır — view'ın kendi
  `DD25L-VIEWREF`'i. SAP kendi view'larına bunu tanımlar, **senin Z view'ına kimse tanımlamaz**.
- **Neden bu sınıf özellikle sinsi — dört kat:**
  1. **Tek uyarı yok.** Aktivasyon başarılı, ATC temiz, syntax temiz. Sessizliğin tek belirtisi
     boş bir ekran.
  2. **Doğuştan gelir, GEÇ patlar.** İlgili veri kapsamı boşken (yeni modül, yeni malzeme grubu,
     test öncesi) view zaten 0 döner ve bu **doğru** görünür. Kusur, ilk gerçek veri girildiği
     gün — yani genelde kullanıcı testinin ilk saatinde — ortaya çıkar.
  3. **Aynı obje, iki farklı erişim yolu, iki farklı cevap.** Programın Open SQL'i veriyi görür,
     aynı programın classic view'ı görmez. "Ama SELECT çalışıyor" refleksi teşhisi saptırır.
  4. **Ters yönde de bozar.** Boş view'a `NOT EXISTS`/anti-join yapan bir sayaç **şişer**
     (her satır "eşleşmedi" sayılır). Yani semptom hep "boş" değildir; biri boşalırken
     diğeri dolabilir ve ikisi aynı kusurdur.
- **TEŞHİS — üç sorgu, beş dakika:**
  ```
  1) SELECT tabname, viewref FROM dd02l WHERE tabname = '<TABLO>'      -- replacement var mı?
  2) SELECT viewname, viewref FROM dd25l WHERE viewname = '<Z_VIEW>'   -- benimki yönlendirilmiş mi? (null = kusur)
  3) Kontrol grubu: DD26S ile aynı tabloyu taşıyan TÜM view'ları çıkar, her biri için
     COUNT(*) + DD25L-VIEWREF ölç → "VIEWREF dolu ⇒ satır var / null ⇒ 0" ayrışması
  ```
  ⚠ **KONTROL GRUBUNU SEÇERKEN KONTROL EDİLEN DEĞİŞKENİ DE ÖLÇ.** Bu vakada ilk turda
  "standart `CNMSEG` satır döndürüyor ⇒ classic view'lar bu tabloyu görebiliyor ⇒ hipotez
  çürüdü" denip **yanlış elendi**. Meğer `CNMSEG`'in `DD25L-VIEWREF`'i doluymuş — yani o
  ölçüm hipotezi çürütmüyor, **doğruluyormuş**. Kontrol grubu, ayırt edici değişken
  ölçülmeden kurulursa **tersini kanıtlar gibi görünür**. (#19'un ince hâli.)
- **ÇALIŞAN YÖNTEM:** veri kaynağını **NSDM uyumluluk CDS'ine** çevir — `mseg` → `nsdm_e_mseg`,
  `mkpf` → `nsdm_e_mkpf`. Alan adları birebir aynıdır; `sqlViewName`, alan listesi, key'ler,
  WHERE ve UNION dalları **DEĞİŞMEZ** → DB view yaşamaya devam eder → onu `USING` ile tüketen
  **AMDP bozulmaz**. Emsal SAP'nin kendi DDIC-based CDS view'ıdır (`C_GdsRcptItemQty` →
  `select from nsdm_e_mseg`). Değişiklik yalnız FROM/JOIN adlarıdır.
- **Denenmesi gereksiz iki yol:**
  · **Doğrudan hedef tabloya inmek** (`matdoc` + `record_type`/`header_counter`) — çalışır ama
    SAP'nin uyumluluk semantiğini **elle taklit** etmek demektir; SAP tabloyu genişletince
    sessizce kayar.
  · **View entity'ye çevirmek** — Open SQL yönlendirmesi devreye girer, AMA view entity **DB
    view ÜRETMEZ** → `USING <sql_view>` yapan AMDP kırılır. Classic view bilinçli seçildiyse
    (AMDP zinciri) bu seçenek tasarımı bozar.
- **Kapsam taraması (aynı tuzak başka nerede?):** `DD26S`'te Z view'ları tara, ama **genel
  `viewname LIKE 'Z%'` sorgusu satır tavanına `ZZ1_*` uzantı view'larıyla dayanır** → tabloyu
  önek önek böl (`tabname LIKE 'MS%'`, `'MB%'`, …) ve **kırpılmadığını göster**. Kırpılmış bir
  taramaya dayanarak "başka etkilenen yok" DEME (#16).
- **Gate?** HENÜZ YOK — **bilinçli** (ADR 0019 merdiven ilkesi §4: önce doküman denenir).
  Bu ders + `adt-cds.md` §"NSDM" ilk savunmadır. Tekrar ederse validator adayı:
  *"classic DDIC view'ın FROM/JOIN'inde `DD02L-VIEWREF`'i dolu bir tablo varsa BLOCKER."*
- **Akraba:** **#16** (0 ≠ yok) · **#19** (kontrol grubu) · **#5** (trust without verify).
  Ortak çekirdek: **"aktive oldu" bir çalışma kanıtı değildir; veri döndürdüğünü ölç.**
- **Status:** ⚠️ DİSİPLİN. Obje-tipi evi: [`adt-cds.md`](adt-cds.md).

---

### PATTERN #22: Klasik Dynpro diyalog üretecinde — donör-çakışan fcode + `IT_BUTTONS` tam-yeniden-kurulum + ölçülemeyen toolbar

*(applies_to: `s4_private` — `ZSD000_FM_SCREEN_GEN` benzeri bir AI Dynpro/CUA üreteci kullanan
her proje için geçerli; kaynak vaka bir stok-hareket takip programının 3 modal diyalog ekranı)*

- **Hata sınıfı:** Aynı programda birden çok modal diyalog ekranı (Dynpro) art arda CUA
  turlarıyla üretilirken, **o turda dokunulmayan bir ekranın toolbar'ı veya fonksiyon
  etiketi sessizce bozulur.** İki AYRI mekanizma, iki AYRI belirti:
  1. **Donör-çakışan fcode:** o turun `IT_BUTTONS`'ında verilmeyen ama standart donör
     status'te de var olan bir fcode (ör. bir "Kaydet" kodu), her `WRITE` çağrısında
     donör etiketine geri döner — hem de bu turda hiç dokunulmayan **başka bir ekranda**
     görünür (fonksiyon tanımı program-geneli).
  2. **`IT_BUTTONS` tam-yeniden-kurulum:** üreteç her `WRITE` çağrısında hedef status'ün
     toolbar'ını (`but`) koşulsuz sıfırlar ve yalnız o turun `IT_BUTTONS`'ında verilen
     butonlarla yeniden kurar — o statüsün önceki turda eklenmiş ama bu turda payload'a
     KONULMAYAN butonu **düşer**.
- **Neden tehlikeli — sayaçlar bu sınıfı GÖRMEZ:** `FUN`/`PFK`/`BUT`/`TITLES` program-geneli
  sayaçlardır; fonksiyon tanımları hiç silinmediği için etiket-kaybında bu sayılar
  **değişmez**. `BUT` yalnız buton-DÜŞMESİNDE değişir, o da yalnız ilgili ekranı etkileyen
  toplam bir delta olarak görünür — hangi statüde düştüğünü söylemez.
- **Kök-yanlış-genelleme dersi:** önceki bir kural *"`IT_BUTTONS` `IV_RECREATE` ile KURAR,
  `IV_RECREATE`'siz sadece EKLER"* diye yazılmıştı ve **YANLIŞTI**. Yanlışın kökü ölçüm
  hatası değil, **dar bir ölçümün geniş genellenmesiydi**: ilk deney yalnız `FUN`/`PFK`
  sayaçlarını ölçmüştü (bunlar zaten hiç azalmaz); *"hedef status'ün `IT_BUTTONS`'ından bir
  butonu bilerek atla, o status'ten düşüyor mu bak"* deneyi hiç yapılmamıştı.
  **⭐ Genel ilke: bir davranış iddiası, o davranışı ÜRETEN deneyle kurulmalıdır — yan bir
  sayacın değişmemesi, farklı bir tablonun aynı şekilde davrandığını GÖSTERMEZ.**
- **ÇALIŞAN YÖNTEM (üç katman):**
  1. **Önden hesap (yazmadan önce):** per-status toolbar içeriği araçla okunamaz (ikili
     format) → beklenen `BUT` deltası (`Σ gönderilecek buton − tahmini mevcut buton`,
     WRITE edilecek her status için) **CUA çağrısından ÖNCE** hesaplanır ve tur-başı
     sayaçla toplanır; final bu toplamla uyuşmuyorsa **yazmadan** durulur. Kontrol tur
     SONRASINDA yapılırsa doğru teşhis gelir ama **bir tur geç** — buton bu arada gerçekten
     düşmüş olur.
  2. **`FUNDTL` diff (yazdıktan sonra):** tur-başı ve final `IV_MODE='READ'` fonksiyon
     dökümleri karşılaştırılır — sayaç değil **döküm** diff'lenir; kaybolan fcode yoksa PASS.
  3. **Tasarım:** birden çok status aynı fcode'u paylaşıyorsa (fonksiyon özniteliği
     program-geneli olduğu için) tooltip ikisinde birden doğru olamaz → **her ekrana ayrı
     fcode ver.** "Jenerik etiket yaz" uzlaşması denenip GERİ ALINMIŞTIR (çare değil,
     sorunun tarifiydi). Bundan sonraki her turda, o turda dokunulmayan status'lerin
     donör-çakışan fcode'ları da payload'a KONULUR (ya da hepsini içeren status en son
     koşulur).
- **Gate?** HENÜZ YOK — **bilinçli** (ADR 0019 merdiven ilkesi §4: önce doküman denenir; bu
  sınıf yalnız çok-ekranlı CUA üreteci kullanan projelerde oluşur, dar kapsam). Bu ders +
  [`howto-classic-dynpro-datafield-screens.md`](howto-classic-dynpro-datafield-screens.md) §3
  ilk savunmadır.
- **Akraba:** **#19** (kontrol grubu olmadan "araç bozuk" denemez — burada "üreteç butonları
  bozuyor" hipotezi kontrol grubuyla "tam olarak donör-çakışması"na daraltıldı) · **#16**
  (arama/ölçüm kapsamı sonucun anlamını belirler — burada "sayı neyi sayıyor" sorusu).
- **Status:** ⚠️ DİSİPLİN. Obje-tipi evi: [`adt-fugr-functions.md`](adt-fugr-functions.md) §6 ·
  [`howto-classic-dynpro-datafield-screens.md`](howto-classic-dynpro-datafield-screens.md).

---

### PATTERN #23: Klasik Dynpro datafield ekranında arama-yardımı — bileşene attachment, ekran alan adına DEĞİL; eskimiş "kusur doğamaz" varsayımı

*(applies_to: `s4_private` — DDIC yapıya bağlı (`FROM_DICT`) klasik Dynpro alanı + standart
search-help attachment kullanan her build; kaynak vaka: aynı stok-hareket takip programının
depo-yeri F4'ü sondası)*

- **Hata sınıfı 1 — yanlış-elenmiş çözüm:** bir DDIC yapının iki bileşeni aynı tipte olduğunda
  (ör. iki `lgort_d` alanı: "veren" ve "alan" deposu) *"ikisi aynı DDIC search-help adını
  taşıyamaz ⇒ attachment yolu kapalı"* diye elenmişti. **YANLIŞ:** search-help attachment
  ekran ALANININ ADINA değil **yapı BİLEŞENİNE** yapılır (`define structure` içinde her
  bileşen kendi `with value help ... where` bloğunu taşır) — iki bileşen aynı SHLP'ye ayrı
  ayrı bağlanabilir. Canlı ölçüm: 7 alanlı bir yapının tümü `MATCHCODE` boş + `FROM_DICT`,
  ikisi aynı standart SHLP'ye bağlıydı.
- **Hata sınıfı 2 — eskimiş "kusur doğamaz" varsayımı, ölçümle çürüdü:** *"alan DDIC yapıya
  bağlıysa ('`FROM_DICT`'), arama yardımının varsayılan parametreye düşmesi kusuru doğamaz"*
  diye yazılmıştı. **Ölçüm çürüttü:** `FROM_DICT` olsa bile F4, seçilen kaydın YANLIŞ bir
  alanını (ör. üretim yeri, depo yeri yerine) ekran alanına yazmaya devam etti. **Gerçek kök
  sebep:** search-help'in kendi parametre-pozisyonu (ör. `FLPOSITION`/ilk `EXPORT`
  parametresi) ile ekran alanı arasında **eşleme kurulmamıştı** — DDIC'e bağlı olmak bu
  eşlemeyi kendiliğinden KURMAZ; `where` bloğunda parametre AÇIKÇA verilmelidir.
- **Hata sınıfı 3 — tekrarlanan yanlış teşhis, önceki not görülmeden:** kusur bir kez elle
  `MATCHCODE` eklenerek "çözüldü" denip kapatılmıştı; birkaç gün sonra aynı semptomla geri
  geldiğinde **aynı deney tekrar kuruldu** (matchcode tekrar eklendi) — oysa görev-içi bir
  teşhis dosyası kök sebebin `MATCHCODE`'un yokluğu değil **parametre eşlemesinin yokluğu**
  olduğunu ÇOKTAN yazmıştı. O rapora bakılmadan çözülmüş bir teşhisin üstüne yeniden deney
  kuruldu, ve tekrar çürüdü.
  **⭐ Kural: tanıdık bir semptomda ÖNCE görev-içi geçici dosyalar + SESSION_NOTES + memory
  ARANIR, SONRA yeni deney kurulur** — cevap muhtemelen zaten yazılmıştır.
- **⚠ Dördüncü katman — ekrandaki elle `MATCHCODE` attachment'ın ÖNÜNE geçer:** DDIC
  yapısına attachment eklense bile, ekran alanında geçmişten kalan elle `MATCHCODE` DEĞERİ
  varsa **ekran onu kazanır**, attachment hiç devreye girmez. Yeni ekranda `MATCHCODE`
  BOŞ bırakılmalıdır.
- **⚠ Beşinci katman — DDIC değişti ama tüketici (ekran) regen edilmedi:** klasik Dynpro,
  DDIC bilgisini **ÜRETİLDİĞİ anda gömer.** Bir yapıya sonradan attachment eklemek, o yapıyı
  KULLANAN ekran daha önce üretilmişse, kendiliğinden ekrana inmez — ekranın (yalnız gerekli
  alanlarla) **bir kez daha üretilmesi (regen)** gerekir. *Obje aktif ≠ tüketici güncel.*
- **ÇALIŞAN YÖNTEM:** DDIC yapı bileşenine `with value help <shlp> where <param> = <yapı>.
  <bileşen>` (birden fazla `where` satırı, gerekirse başka bir bileşene referansla) ekle →
  ekran alanının elle `MATCHCODE`'unu boşalt → ekranı (yalnız etkilenen alanlarla) regen et
  → §"Doğrulama protokolü" ile kanıtla (`DD35L`/`DD36S` attachment/parametre-eşleme sayısı +
  `adt_inactive_objects` 0 + sayaç kıyası). "Aktif" metadata'sına güvenme; F4'ün fiilen doğru
  alanı yazdığını **kullanıcı GUI'de test eder** (araçla okunamaz).
- **Gate?** HENÜZ YOK — **bilinçli** (dar kapsam: yalnız çok-bileşenli aynı-tipte DDIC
  yapılarda + Z SHLP yaratılamayan sistemlerde oluşur). Bu ders +
  [`howto-classic-dynpro-datafield-screens.md`](howto-classic-dynpro-datafield-screens.md) §2
  ilk savunmadır.
- **Akraba:** **#19** (kontrol grubu) — "aynı DDIC adını taşıyamaz" iddiası da kontrolsüz
  bir eleme örneğiydi.
- **Status:** ⚠️ DİSİPLİN. Obje-tipi evi: [`howto-classic-dynpro-datafield-screens.md`](howto-classic-dynpro-datafield-screens.md).

---

## 📊 PATTERN İstatistikleri (audit için)

| Pattern | İlk keşif | Tekrar sayısı | Status |
|---|---|---|---|
| #3 Memory Drift | 2026-05-13 | 1 (Sprint 1A todo vs SAP) | ✅ KOD GATE |
| #4 Doc ≠ Enforcement | 2026-05-13 | 2 (Namespace whitelist v1, v2) | ✅ SİSTEMATİK |
| #5 Trust Without Verify | 2026-05-13 | 2 (ZSD_007 cleanup, SHIPMENT_LIST) | ⚠️ DİSİPLİN |
| #6 TempScripts → Playbook | 2026-05-13 | 1 | ⚠️ DİSİPLİN |
| #7 Placeholder'a bakıp "pattern yok" (yanlış dosya) | 2026-06-02 | 1 (FM imza push; sınıfsal akrabaları #16/#19'da sayılır) | ⚠️ DİSİPLİN (adt-fugr dolduruldu + memory) |
| #8 Klasik programı tek-body yazmak | 2026-06-03 | 1 (ALV_TEMP1/2/3) | ⚠️ DİSİPLİN (std 06 §1 + memory + skill-tetik) |
| #9 Satırsız save-scan'de feature suçlama + körlemesine patinaj | 2026-06-11 | 1 (ZSD001 sipariş-notu) | ⚠️ DİSİPLİN (bisect disiplini; TYPE c gate'i AYRICA kod-gate) |
| #10 Junction'da `__file__` proje kökü | 2026-07-08 | 1 (deploy_ui + rg ile 2 script daha) | ✅ SOLVED (kök-fix + CORE-01 gate) |
| #11 where_used count=0 = orphan sanma | 2026-07-09 | 1 (orphan sweep) | ✅ SOLVED (kod gate) |
| #12 Guard kör noktası (heredoc + tek yüzey) | 2026-07-09 | 3 guard + 4 kural (denetim) + 1 kapsam-dışı varyant (2026-07-30 POSIX-cd → fix+mutasyon-testi) | ✅ SOLVED (tek normalizasyon + CI testi; varyant sınıfı için negatif-test kültürü) |
| #13 Enqueue lock-leak (session ölünce in-flight lock) | 2026-07-12 | 1 (EU 510 + E_ABAP_GENPH) | ⚠️ DİSİPLİN (gateway pre-flight lock_check; auto-recovery DEFERRED) |
| #14 Devreye alma — "koştu ≠ baktı" + FP seli | 2026-07-26 | aile 5 kez (released_objects boş-harita, damga except-PASS, ölü freeze-guard, 0-token validator, 10/10-FP detektör) | ✅ AKTİF ders (9-adım devreye-alma protokolü + grandfather değişmezleri) |
| #15 `git diff A...B` "merge edilmemiş iş" yanılsaması | 2026-07-27 | 1 (748-satır yanlış alarm; dal 5.162 satır gerideydi) | ⚠️ DİSİPLİN (iki-nokta + PR-hakem zinciri) |
| #16 Arama aracının kapsamı — `0` ≠ "yok" · **teşhisin kendisi de kanıt gerektirir** | 2026-07-28 | **6** (FUGR grep · classrun sahte teşhis ×2 → 2026-07-31 kök-fix: teşhis İNAKTİF sürümü okuyordu · behavior-pool `main` boş · lock-check tip desteği · dar grep deseni "0 referans") | ⚠️ DİSİPLİN + CI testi (CSRF regresyonu) + kök-fix (`version=active` + session reset) |
| #17 **Katman katman keşif** — çapraz-kesen işte envantersiz ilerleme | 2026-07-29 | 1 (silme kontrolü: 3 app sanıldı, 7 çıktı; 14 yol sanıldı, 24 çıktı; 6 review turu) | ⚠️ DİSİPLİN → `howto-cok-katmanli-degisiklik.md` |
| #18 **Bayat sayı/satır referansı** (yorumda `dosya:satır`, "N obje", "N metot") | 2026-07-29 | **6** (obje sayısı · metot sayısı ×2 · veri iddiası · yorum satır-no ×2) | ⚠️ DİSİPLİN (içerik-çapası kuralı) |
| #19 **"Araç bozuk" kontrol grubu olmadan kurulamaz** + tanıdık semptomda önce hafızayı ara | 2026-07-31 | **2** (classrun "güvenilmez" ×2 — 2026-06-30'da çözülmüştü, 2026-07-30'da unutulup üstüne yanlış yazıldı) | ⚠️ DİSİPLİN |
| #20 **Salt-okunur sanılan araç yazıyordu** — yetkiyi ad/doküman değil ölçüm belirler | 2026-07-31 | 1 (`adt_syntax_check` → temiz inaktif sürümü AKTİVE ediyor; docstring aksini söylüyordu) | ⚠️ DİSİPLİN + kaynak-fix (docstring) |
| #21 **S/4 classic DDIC view + replacement tablo = sessiz 0 satır** (`s4_*` profilleri) | 2026-08-03 | 1 (classic view `MSEG`/`MKPF` üzerine kurulu → doğuştan 0 satır; 3 tüketici birden boş, 1 sayaç ters yönde şişik; ayrıca kontrol grubu **yanlış eledi** — `DD25L-VIEWREF` ölçülmemişti) | ⚠️ DİSİPLİN (gate BİLİNÇLİ ertelendi — ADR 0019 §4 merdiven) |

> **Hedef:** ACTIVE/⚠️ DİSİPLİN olanları zamanla SOLVED'a çevir (kod gate ile).
> **Numara notu (2026-07-31):** #1–#2 hiç tanımlanmadı (tarihsel boşluk — yeniden kullanma);
> #17–#18'in ayrıntı gövdesi bu dosyada değil `howto-cok-katmanli-degisiklik.md` +
> içerik-çapası kuralındadır (tablo satırları kanonik sayaçtır).

### PATTERN #24: Bağlantı dosyasını düzeltmek YETMEZ — MCP server kimliği **başlangıçta** okur, restart şart

- **Belirti:** SAP parolası değişti → `.conn_adt` güncellendi → ADT çağrıları **hâlâ 401**.
  Dosya tarafı doğrulandı (BOM yok, tırnak yok, boşluk yok, mtime taze) ⇒ dosya suçsuz.
- **Kök sebep:** MCP server bağlantı dosyasını **süreç başlangıcında** okur ve bellekte tutar.
  Dosya değişince kendiliğinden yenilemez. Süreç yaşadığı sürece **eski parola** kullanılır.
- **Çözüm:** `.conn_adt` düzelt **VE** MCP server'ı reconnect/restart et (`/mcp`). İkisi birlikte.
- **Neden bu pattern'e değer:** hata mesajı **401** — yani "yanlış kimlik" diyor, ki doğru; ama
  yanlış *hangi* kimliğin kullanıldığını söylemiyor. Doğal refleks parolayı tekrar tekrar
  yazmak/denemektir → **hesap kilidi riski**. Kilit eşiğine yaklaşan bir sistemde bu, tek bir
  yanlış teşhisin günü kilitlemesi demektir.
- **Kural:** Kimlik-bilgisi dosyası değiştikten sonraki İLK başarısızlıkta parolayı değil
  **sürecin tazeliğini** şüphelen. Retry'dan önce restart. Ve kimlik hatalarında **retry
  bütçesi tut** (kilit eşiği gerçek bir kaynaktır; körlemesine deneme onu harcar).
- **Genelleme:** Aynı sınıf her uzun-ömürlü süreç için geçerlidir (MCP server, daemon, dil
  sunucusu, çalışan container). *Config değişikliği ≠ davranış değişikliği* — süreç yeniden
  okuyana kadar eski dünyada yaşar.

---

## 🎯 META-KURAL — "Doubt-Driven"

Bu dosyanın özü tek cümlede:

> **Bir iddiada bulunmadan önce SAP'a sor. "Tamamlandı" yerine "henüz doğrulamadım" de.**

Forward progress doğal refleks, ama **verification refleksini geliştirmek** sistemli güveni sağlar. User'ın güveni = audit dirençli iddialar = bu kural.

### PATTERN #25: `$metadata` alan doğrulaması **TİP-KAPSAMLI** olmalı — belge-geneli arama sahte-pozitif verir

- **Hata:** Bir OData servisinde alanın varlığı `$metadata` belgesinde **düz metin araması** ile
  doğrulanır (`grep '<AlanAdı>'`). Belge yalnız iş entity'lerini değil **SADL/altyapı tiplerini**
  de taşır (`SAP__Signature`, parametre/aksiyon tipleri, complex type'lar) → aynı ada sahip bir
  altyapı property'si eşleşir ve **alan var sanılır**.
- **Vaka:** İki ajan aynı servis için **çelişen** sonuç bildirdi; biri "alan var" dedi (altyapı
  tipinden eşleşme), diğeri "yok". Doğru cevap ancak EntityType izole edilince çıktı.
- **Ters yüzü de var:** entity izole edilmeden yapılan *"yok"* hükmü de güvenilmez — projeksiyon
  farklı adla expose ediyor olabilir (SRVD rename).
- **DOĞRU YÖNTEM:** ① ilgili **EntityType'ı İZOLE ET** (`<EntityType Name="...Type">…</EntityType>`
  bloğunu ayır) ② alanı **o blok içinde** ara ③ tipini/uzunluğunu da oku (`Type`, `MaxLength`,
  `sap:sortable`, `sap:filterable`) — bunlar tasarım kararını da doğrular.
- **Bonus:** `sap:sortable="false"`/`filterable="false"` gördüysen, FE'de `sortProperty`/
  `filterProperty` **verilmemeli**; verilirse servis 400 döner. Doğrulama tasarımı da denetler.
- 📌 **Bu ders 2 gün "core'a terfi adayı" damgasıyla proje notunda bekledi.** Aynı sınıfın kardeşi
  (`known-errors.md` §12.7) o iki günde ısırdı. **Terfi etmeyen ders = çözülmemiş ders.**

### PATTERN #26: Kopya dosya silmeden önce **REFERANS ölç — hash'e bakma**

- **Hata:** Birden çok yerde aynı içerikli dosya bulunur (aynı hash); "kopya" sayılıp toptan
  silinir ya da tek kaynağa indirgenir. Hash **içerik** eşitliğini söyler, **kullanım**
  eşitliğini DEĞİL.
- **Vaka:** Bir hash-ailesinin üyeleri silinseydi, gerçekten **çalışan bir uygulamanın**
  (kendi kopyasını yükleyen) yolu kırılacaktı. İçerik aynıydı; **tüketicisi farklıydı.**
- **DOĞRU YÖNTEM:** silmeden önce her kopya için **kim yüklüyor/import ediyor** ölç
  (`where_used`, `grep -r` ile import/require/manifest/`addStyleClass`/yol dizgesi).
  Referansı olan kopya **silinmez**; tek kaynağa indirgeme ancak tüm tüketiciler yeni kaynağa
  bağlandıktan SONRA yapılır.
- **Sonuç geri alınamaza yakın:** silinen kopya kolay geri gelir, ama kırılan uygulama
  **fark edilene kadar** üretimde bozuktur.
- İlişkili: PATTERN #11 (`where_used` count=0 → "orphan" sanma).

### PATTERN #27: Lider, **kendi önerdiği** uygulamayı arayıp bulamayınca "yapılmadı" DEMEZ

- **Hata:** Lider brifingde bir uygulama önerir (sınıf adı, fonksiyon adı, dosya). Doğrulama
  aşamasında **o adı** arar, `0` bulur ve *"ajan yapmamış"* hükmü verir + ajanı geri gönderir.
- **Gerçek:** Ajan işi **yapmıştır** — ama gerekçeli olarak **başka (çoğu zaman daha doğru)** bir
  uygulama seçmiştir. `0` sonucu "yapılmadı" değil, **"başka türlü yapılmış"** demektir.
- **Vaka:** Lider mevcut bir CSS sınıfının yeniden kullanılmasını önerdi; ajan o sınıfın istenen
  kombinasyonu (hücre+başlık ayrı boyut) karşılamadığını görüp **aynı desende yeni** bir sınıf
  tanımladı ve gerekçesini yazdı. Liderin `grep <önerdiği-ad>` → 0 ölçümü "iş yapılmadı" sanıldı;
  ajanla gereksiz bir "yaptım/yapmadın" turu döndü.
- **DOĞRULAMA SIRASI:** ① `git status`/`git diff --stat` — **hangi dosyalar** değişti
  ② **etkiyi** ara, adı değil (font kuralı eklendi mi · kolon bağlandı mı · dal açıldı mı)
  ③ ancak sonra spesifik ad; `0` dönerse **"başka nasıl yapılmış olabilir"** diye sor.
- ⚠ **İkinci yüz:** `git diff` (HEAD'e karşı) boş dönmesi de "yapılmadı" DEĞİLDİR — ajanlar
  **commit etmez** (commit = lider), iş **daima çalışma ağacındadır** (`git status --short`).
- ⚠ **Üçüncü yüz:** koşan bir ajana gönderilen revizyon, o **tura yetişmeyebilir**. Ajan
  "yapmadım" değil **"görmedim"** durumundadır. Suçlamadan önce zamanlamayı düşün.

### PATTERN #28: Üretilmiş indeks (CORE-INDEX) **DAL-BAĞIMLIDIR** — küçülme "silinmiş" demek değil

- **Hata:** `CORE-INDEX` proje reposundadır ama içeriği `core/` **junction'ının o an hangi dalda
  durduğundan** üretilir. Core'da dal değiştikten sonra indeks yeniden üretilirse doküman sayısı
  **düşer**; ilk okuyuşta *"bir doküman silinmiş"* gibi görünür.
- **Vaka:** İndeks 87 → 86'ya düştü. Sebep silme değildi: lider core'u kendi PR dalına almıştı ve
  bir playbook dokümanı **yalnız başka bir dalda** vardı. Core eski dalına dönünce sayı geri geldi.
- **DOĞRU SIRA:** ① `git -C <CORE> branch --show-current` — beklediğin dal mı? ② yeniden üret,
  **farkı OKU**; sayı düştüyse **DUR** ③ **hangi dosya** düştü, **neden** yok — ölç
  ④ indeks **paylaşılan gerçeği** temsil eden daldan üretilir (`main`), kişisel PR dalından değil
  ⑤ fark yalnız `uretim:`/`core-commit:` yorum satırıysa **commit etme** (tazelik kıyasında yok sayılır).
- **Meşru düşüş de olur:** doküman gerçekten merge edilmemiş bir daldaysa, `main`'e göre üretilen
  indeks **doğruyu** söyler — ajan o dokümanı fiilen bulamaz. O hâlde düşüşü **gerekçesiyle** commit'le.
- Aynı sınıf `_worktrees/` için de geçerli: hangi çalışma ağacının junction'a bağlı olduğunu
  **varsayma, ölç**.

### PATTERN #29: Auto-mode permission soft-deny **NON-DETERMİNİSTİKTİR** — ret bir olgu değil, sinyaldir

- **Belirti:** SAP-yazma niyeti taşıyan bir eylem (MCP yazma çağrısı **ya da gateway ajanı
  spawn'ı**) *"Blocked by classifier"* ile reddedilir. Aynı iş, **hiçbir ayar değişmeden**,
  ikinci denemede **geçer**.
- **Kanıt (ölçüm):** `permissions` yalnız `allow` taşıyordu — `deny` YOK, `ask` YOK,
  `defaultMode` YOK, `Agent`/`Task` kuralı YOK ⇒ **kural motoru değil, çağrı başına model kararı.**
  Kural olsaydı iki deneme de reddedilirdi.
- **Tetikleyici obje tipi DEĞİL:** ret, "canlı BO/behavior" gibi bir sınıfa bağlı değil; sıradan
  bir klasik program include'unun push'u için açılan **ajan** da reddedilebiliyor.
- **YAP:** ① reti **olgu değil sinyal** say ② **önce hafızayı/dersi ara** — bu sınıf kayıtlı
  ③ kullanıcıya onay sorusu taşımadan **bir kez daha dene** ④ tur canlı obje içeriyorsa
  **baştan** *"auto-mode'u kapatalım, prompt'ları sen onayla"* diye öner — deneme-yanılma ve
  onay trafiği ortadan kalkar.
- ⛔ **YAPMA:** reti dolanmaya çalışma; `settings.local.json`'a kendine izin yazma (self-grant
  ayrıca bloklanır ve doğru davranış değildir).

### PATTERN #30: Kural VARDI ama ateşlemedi — **kuralı hatırlatan şey KONUMUDUR** (ÖNCE-ARA / KB-01)

> **Kanonik kural metni: [`CLAUDE.core.md §4 ÖNCE-ARA (KB-01)`](../CLAUDE.core.md).** Bu kayıt
> onun tekrarı değil, **neden atlandığının teşhisi** + JIT-recall'a giriş noktasıdır.

- **Belirti:** Doğru talimat dokümanda **yazılıdır**, ekip onu daha önce uygulamıştır — yine de
  o tur atlanır. Refleks açıklama *"kural yetersiz yazılmış"* olur; **çoğu zaman yanlıştır.**
- **Ölçülen dört sebep (vaka 2026-08-11 — prior-art'sız sınıf-iddiası çekirdeğe yazıldı):**
  1. **Yanlış kapı:** kural, *"X demeden önce…"* diye bir **duruma** bağlıydı; yapılan eylem
     başka bir eylemdi (*ders yazmak*) ⇒ tetikleyici cümle eşleşmedi. **Tetikleyiciyi
     EYLEM-bazlı yaz** ("şunu yazacaksan"), durum-bazlı değil.
  2. **Yazma yolunda adım yok:** hedef-seçme ağacı (SORU 0) *"nereye yazayım"* diye sorar,
     *"zaten yazılı mı"* diye **sormazdı**. Kural, insanın/ajanın **üstünde durduğu yola**
     konmalıydı.
  3. **Hatırlatıcı yanlış olayda:** JIT-recall YALNIZ `UserPromptSubmit`'te koşar. **Sentetik
     payload'la ölçüldü:** doğru prompt verilince ilgili PATTERN'i **doğru döndürüyor** ⇒
     indeks/eşleştirme sağlam; sorun hatanın **tur ortasında** yapılmış olması. ⇒ *Kullanıcı
     mesajına bağlı hatırlatıcı, tur-içi davranışı koruyamaz.*
  4. **Doğru anda ateşleyen hatırlatıcı eksik listeyle çalışıyordu** (nudge vardı, maddesi yoktu).
- **KARŞIT KANIT — aynı turda uyulan kural:** başka bir "önce ara" kuralı **uygulandı** ve
  çoğaltma önlendi. Farkı yaratan şey kuralın kalitesi değil, o dersin **o an bağlamda fiziksel
  olarak durması**ydı (az önce okunan bir dosyada yazılıydı).
- **YAP:** ① kuralı **eylemin geçtiği yola** koy (yazma yolu / checklist / o anki dosya)
  ② tetikleyiciyi **eylem-bazlı** yaz ③ doğru anda ateşleyen mevcut nudge'a **maddeyi ekle**
  (yeni gate açmadan) ④ **indekslenen** yere de kısa girdi koy — JIT-recall yalnız `MEMORY.md`
  + `lessons-learned.md` PATTERN başlıkları + `playbook/howto-*.md`'den beslenir; `CLAUDE.core.md`
  **indekslenmez** (ölçüldü).
- ⛔ **YAPMA:** "kuralı daha sert yazalım/gate açalım" refleksi — sorun metnin gücü değil
  **konumu** olabilir; önce onu ölç (moratoryum: ADR 0019 şart-4).

### PATTERN #31: PowerShell 5.1 → native komuta giden argümanda **gömülü çift-tırnak** sessizce parçalar (`git commit -m` here-string)

- **Belirti:** `git commit -m @'...'@` (tek-tırnaklı here-string) içinde `"kelime"` biçiminde
  çift-tırnak varsa git, mesajın tırnaktan sonraki kısmını **ayrı argüman = pathspec** sanır:
  `error: pathspec '...' did not match any file(s)`. Here-string PS içinde literal'dir —
  kırılma PS→native **komut-satırı yeniden kurulumunda** olur (PS 5.1 gömülü `"` kaçışlamaz).
- **Ölçüm (2026-08-12, aynı oturum):** çift-tırnaklı 2 mesaj → 2 kez pathspec hatası;
  aynı kalıpla tırnaksız 3 mesaj → 3 commit temiz. `prior-art: yok` (BOM/heredoc dersleri farklı sınıf).
- **YAP:** commit/PR mesajında çift-tırnak karakteri **hiç kullanma** (vurgu için tek tırnak
  ya da tırnaksız yaz). Uzun mesajda `-F <dosya>` doğaldır ama ⚠ `pre_tool_guard` commit-mesajı
  gate'i `-F` yolunu şu an backslash'sız okuyup FAIL-CLOSED reddediyor (bilinen kusur, infra-kuyrukta)
  — düzelene dek pratik yol: tırnaksız `-m` here-string.
- **Sınır:** ölçüm PS 5.1 + git for Windows; `Bash` tool'u ve pwsh 7 ölçülmedi.

### Talimat-bakımı pilotunun 3 dersi (2026-08-12 — T1 terfisi; kaynak: infra-devir pilot raporu)

Fixture/talimat-bakımı işi yapan herkes için (akış: [`howto-talimat-dosyasi-bakimi.md`](howto-talimat-dosyasi-bakimi.md)):
1. **Fixture gövdesine md-link koyma** — talimat-bütçe vektörleri onu ölü-link sayar = sahte kırmızı.
2. **Suite özet satırı `^\d+/\d+ OK` deseniyle başlamalı** — başlamazsa koşucu tabloda sayıyı GÖSTERMEZ
   (test geçer ama görünmez; "exit 0 ≠ çıktı" sınıfı).
3. **Worktree dalı main'in GERİSİNDE olabilir** → F0 adımına `git diff HEAD origin/main` ekle
   (2026-08-12 pilotunda changelog append-append çakışması tam bundan çıktı, öngörülmüştü).
