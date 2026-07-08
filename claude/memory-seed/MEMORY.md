# MEMORY (seed) — feedback / çalışma-disiplini kuralları

> Bu, repoya committed **feedback memory tohumudur**. `scripts/seed_memory.py` bu klasörü
> bu makinedeki Claude Code proje-hafıza klasörüne kopyalar → yeni geliştirici, proje sahibinin
> çalışma disiplinini (nasıl-çalışırsın kuralları) devralır.
>
> KAPSAM: yalnız `feedback` tipi memory (davranış/disiplin). Projeye-özel work-state
> (project-tipi memory) bu tohuma DAHİL DEĞİLDİR. Hedef makinede zaten var olan dosyalar
> EZİLMEZ (merge-safe) — yerel öğrenmeler korunur. Bu index yalnız hedefte yoksa kopyalanır.

## Feedback

- [ADT-infra değişikliği → önce uyar + onay](feedback_adt-infra-degisikligi-once-uyar-onay.md) — script/kural/MCP/hook/validator dokunuşu HIGH; iş listesine gömülü onay YETMEZ; tek-tek öne çıkar
- [Lider build yapmaz, expert'e dağıtır](feedback_lider-build-yapmaz-experte-dagit.md) — substantive FE/BE build = expert; "context bende" rasyonalizasyonu meşru değil (ADR 0018)
- [Karar sorma disiplini (aşırı kapı yok)](feedback_karar-verimliligi-asiri-kapi-yok.md) — makul-default varken sorma/ilerle; gerçek kararda tek-tek+düz-dil+trade-off; AskUserQuestion BLOKLAR
- [Soru → önce tartış, hemen act etme](feedback_soru-once-tartis-act-etme.md) — SORU'da hemen edit/commit/kural yapma; cevapla+tartış, onayda uygula
- [Doğrula-önce-flag (spekülatif blocker yasak)](feedback_dogrula-once-flag-spekulatif-blocker-yasak.md) — doğrudan-okunabilir iddiayı doğrulamadan BLOCKER yapma; büyük-dump→dosya→grep
- [Fix öncesi where-used + blast-radius](feedback_fix-oncesi-where-used-blast-radius.md) — değişen obje başka yerde mi (where_used/grep)+etki; paylaşılan breaking→DUR; aynı kök diğer tüketicilerde de
- [Ajan "yapılamaz" raporunu sorgula](feedback_ajan-olumsuz-donusu-kanitla-sorgula.md) — ajanın "yapılamaz/blocker/yok" dönüşünü kanıtsız KABUL ETME; alt-yol ara→yönlendir, yoksa kendin doğrula
- [Araç başarısızlığını "zararsız" sayma](feedback_arac-basarisizligini-zararsiz-sayma.md) — activate/push "fail"i geçiştirme; "kalıcı ama aktif değil" ≠ tamam; canlı active-state doğrula
- [Tek soru → bağımsız-tam döküman](feedback_tek-soru-ve-bagimsiz-dokuman.md) — tip/uygulama dökümanı delta DEĞİL bağımsız-tam, link içermez
- [Namespaced DTEL DDL'de tırnaksız](feedback_namespaced-dtel-ddl-tirnaksiz.md) — /SCWM/.. DTEL tırnaksız küçük harf; tek-tırnak sessizce düşer → adt_get readback şart
- [Gateway git commit/push YASAK](feedback_gateway-git-commit-push-yasak.md) — gateway commit/push YAPMAZ, lider commit eder; gateway = SAP push/activate+senkron+rapor
- [Source-drift → PULL-BEFORE-EDIT (ADR 0016)](feedback_source-drift-pull-before-edit-model.md) — GATE pull_before_edit.py; edit-öncesi tazelik (eski M1/M2/M3 block kaldırıldı)
- [Belge uygulaması ortak UI şablonu](feedback_belge-uygulama-ortak-ui-sablonu.md) — FIT/SIP/IHR/Booking aynı layout: List(filtre+akordion)→başlık+kalem (FIT_SE deseni)
- [Legacy/Draft .txt Files](feedback_legacy-draft-txt-files.md) — paket root'undaki .txt'ler ilk draft/legacy; rename/silme yapma
- [Z'li Obje Text Tahmin Yasağı](feedback_zli-obje-text-tahmin-yasak.md) — Z domain/DTEL/CDS description'ları <LEGACY_SOURCE>/spec'ten çıkar, ASLA tahmin etme
- [Playbook'u Önce Oku](feedback_playbook-once-oku.md) — ADT işlem öncesi playbook annotation/syntax pattern'ini oku, tahmin yapma
- [Placeholder Tuzağı — Önce Mevcut Artefakt](feedback_placeholder-tuzagi-once-mevcut-artefakt.md) — tip-playbook boşsa "pattern yok" deme; adt-foundation.md + çalışan .abap ara, kopyala
- [Klasik Program Include'lara Bölünür](feedback_klasik-program-include-bol.md) — tek-body OLMAZ; main=INCLUDE+event, kod T01/C01/O01/I01/F01'e; baştan böl (std 06 §1)
- [Klasik ALV Template-First (ADR 0012)](feedback_klasik-alv-template-first.md) — klasik ALV programa inline; template classic-alv-list.prog.abap; ZSD000_CL_ALV_* silindi
- [Generic Tool'a Program-Spesifik İsim Verme](feedback_generic-tool-program-spesifik-isim-verme.md) — GATE check_reuse_gate; reusable araç generic isim+container almalı, program adını DEĞİL
- [<LEGACY_SOURCE> Field Adları Sistem Bağımlı](feedback_<legacy_source>-field-adlari-sistem-bagimli.md) — eski source'tan kopyada standart tablo alan adlarını yeni sistemde teyit et
- [PONUMBER + POSNUMBER Global İptal](feedback_ponumber-posnumber-global-iptal.md) — GATE check_td_cancelled_fields; ZSD001 struct'larda iptal (TD "korunan" dese bile)
- [<LEGACY_SOURCE> Full Dump Pattern](feedback_<legacy_source>-full-dump-pattern.md) — kapsam kararı öncesi ilgili tüm <LEGACY_SOURCE> objelerini (struct/DTEL/domain) tam indir
- [Yeni Teknoloji → Önce Kural Seti](feedback_yeni-teknoloji-once-kural-seti.md) — ilk-kez teknolojide SAP'ye yazmadan ÖNCE tam formal kural seti (L2/L3/L4+reviewer)
- [Yeni Yetenek → Önce Araştır](feedback_yeni-yetenek-once-arastir.md) — yeni yetenek/araç benimsemeden önce dünyada nasıl yapıldığını araştır; sıfırdan keşfetme
- [MCP post_shell EN Master Lang](feedback_mcp-post-shell-en-master-lang.md) — GATE check_sap_master_language; Z obje raw REST + masterLanguage=TR + post-create doğrula
- [Bağlantı Tutarsızlığında ADT Blok](feedback_baglanti-tutarsizligi-adt-blok.md) — GATE pre_tool_guard; .conn_adt↔MCP ayrışıkken HİÇBİR ADT işlemi yapma, uyar + /mcp iste
- [Freestyle UI PRE-FLIGHT Zorunlu](feedback_freestyle-ui-preflight.md) — GATE ui-freestyle-creation + check_ui5_freestyle_traps; ui-freestyle-odata-v2 + ui-backend-rap §0 baştan
- [Liste Ekranı ALV Standardı](feedback_liste-ekrani-alv-standardi.md) — GATE check_list_view_grid; sort/filtre+çubuk+göster-gizle/varyant+Excel zorunlu (istemese bile)
- [Grid Liste Standardı (sap.ui.table)](feedback_grid-liste-standardi.md) — GATE check_list_view_grid; ALV-tarzı=grid+native sort/filter+DB varyant; m.Table mobil istisna
- [Rapor Filtre = Select-Options + Contains](feedback_rapor-filtre-select-options-contains-standardi.md) — GATE check_filter_search_pattern (FE-32); MultiInput+VHD çoklu+aralık; caseSensitive:false YASAK (/IWBEP toupper 400, Note 1797736); wildcard _parseSearchTerm; kanonik ZSD001
- [Audit Alan Auto-Fill](feedback_audit-alan-autofill-standardi.md) — GATE check_audit_fields_autofill; idempotent setAdmin; create→tümü, update→updated_*
- [Ortak Value-Help — KULLANICIYA SOR](feedback_ortak-value-help-sor.md) — VH için ortak ZSD000_I_* mı local mi SOR; generic master VH tekrar yaratma, expose+assoc (ADR 0009)
- [Done = Tam Kapsam Doğrula](feedback_done-tam-kapsam-dogrula.md) — "tamam" demeden TAM kapsama karşı doğrula; ertelenen alt-maddeyi flag+register; canlı teyit
- [Hook Bakım Protokolü (T11)](feedback_hook-bakim-protokolu-t11.md) — yeni tuzak/iş-türü → playbook notu YETMEZ; T11 ağacı: validator/checklist/hook/pre_tool_guard
- [Review Bulguları → Bug-Checklist Routing](feedback_review-bulgulari-bug-checkliste-routing.md) — review/bug bulgusu → bug-checklist'e FE/BE-NN satır; playbook notu tek başına YETMEZ
- [Araç/Kod Fix Lider'in İşi](feedback_arac-kod-fix-lider-isi.md) — paylaşılan tooling kök-fix'i = LİDER; gateway dar lane (SAP yazımı+retry+rapor)
- [Dosya Bölgeleri / Yazım Yetkisi](feedback_dosya-bolgeleri-yazim-yetkisi.md) — A metodoloji/araç=lider · B paket kaynağı/docs=feature+lider · C SAP=gateway; commit=lider
- [Takım Süreklilik / Gün-sonu / Resume](feedback_takim-sureklilik-gun-sonu-resume.md) — süreklilik=lider; ajan durumsuz; gün-sonu=checkpoint+SESSION_NOTES+WIP commit+**push origin main ZORUNLU**; resume=re-spawn+brief
- [Kararları Önce Topla, Sonra Dispatch](feedback_kararlari-once-topla-sonra-dispatch.md) — build-unit'in TÜM user-kararlarını önce topla, sonra konsolide yönerge; mid-build ping-pong yok
- [ATC Priority 1 Zorunlu](feedback_atc-priority-1-zorunlu.md) — yalnız Prio 1 zorunlu; Prio 2/3 açık onayla pass (sessiz pass yok); variant ZZNDBS_ATC
- [Clean Core Released-CDS Proaktif](feedback_clean-core-released-cds-proaktif.md) — GATE check_released_objects; released CDS tercih (MARA değil I_Product); released_successors.json
- [Spec-Mutabakat Gate (her dev başı)](feedback_spec-mutabakat-gate.md) — yeni program: ekran+fonksiyonel spec iste → <LEGACY_SOURCE>+app+DDL/S ile sentezle → MUTABAKAT → build
- [Hook Komut ${CLAUDE_PROJECT_DIR} Exec-Form](feedback_hook-komut-project-dir-execform.md) — hook+statusLine ASLA göreceli yol; cwd kayınca kırılır; exec-form + ${CLAUDE_PROJECT_DIR}
- [API Call İç Gateway Proxy (ZBC002)](feedback_api-call-ic-gateway-proxy-zbc002.md) — RFC-dest call'da ZBC002_CL_GET_TOKEN + /iwfnd iç loopback; host/client runtime; örn ZSD001 simulate_pricing
- [Tablo Yaratma Onay Gate](feedback_tablo-yaratma-onay-gate.md) — DDIC tablo öncesi alan+DTEL+key tasarımı göster, açık onay al; ad max 16 char
- [Reviewer: checklist ≠ wired validator](feedback_reviewer-checklist-vs-wired-validator.md) — reviewer sürekli PASS'e güvenme; BLOCKER arkasında script olmayabilir; bozuk-girdiyle test et
- [abaplint parser_error gerçek olabilir](feedback_abaplint-parser-error-gercek-olabilir.md) — ccimp parser_error'ı körü körüne false-positive sayma; çalışan ccimp ile kıyas + adt_syntax_check
- [Yetim yorum → class push 400](feedback_detached-leading-abapdoc-class-push-400.md) — OO_SOURCE_BASED 012 "unknown comments"=yetim yorum; metot silince yorumunu da sil
- [PowerShell utf8 BOM tuzağı](feedback_powershell-utf8-bom-trap.md) — PS 5.1 Set-Content -Encoding utf8 BOM ekler, JSON kırar; Edit/Write tool veya WriteAllText($false)
- [FE merge-key padding + playwright tespit](feedback_fe-merge-key-padding-ve-playwright-runtime-tespit.md) — "10" vs "000010" string-merge sessiz null → parseInt normalize; "BE doğru FE boş"→playwright evaluate
- [Template drift CRLF şişmesi](feedback_template-drift-crlf-inflation.md) — raw diff CRLF↔LF sayar→sahte "büyük drift"; --strip-trailing-cr / --ignore-cr-at-eol ile doğrula
- [Grid UI lokal-çalıştırma popup'ı](feedback_grid-ui-local-run-popup.md) — (1) lrep 401→flexibility-services="[]"+start-noflp; (2) ısrarlı popup+lrep yok=HESAP KİLİDİ→SU01 unlock
- [Inline-POST boş-source tuzağı](feedback_inline-post-empty-source-trap.md) — CDS inline-source POST children'ı boş bırakabilir; create sonrası SOURCE doğrula; kompozisyonda LOCK+PUT
- [ABAP decimal→OData locale tuzağı](feedback_abap-decimal-odata-serialize-locale.md) — GATE check_decimal_write_to; decimal'i API body string'ine WRITE...TO KULLANMA; packed→string direkt
- [Vergi=0 → önce master data](feedback_tax-zero-check-master-data-first.md) — KDV=0 → ÖNCE müşteri vergi sınıfı; EML/pricing suçlama; çalışan vs bozuk belge kıyas
- [Source-based class TYPE c trap + bisect](feedback_source-based-class-type-c-trap-ve-vague-scan-bisect.md) — GATE check_method_param_type_c; `TYPE c LENGTH n` save-scan kırar→`TYPE string`; vague→bisect
- [Araştır-önce: üretim/araç patinajı](feedback_arastir-once-patinaj-uretim-gorev.md) — tanıdık-olmayan görevde deneme-yanılma yerine ÖNCE kanıtlı yöntem + çıktıyı say/doğrula
- [Sayısal Input'ta type=Number kullanma](feedback_numeric-input-no-type-number.md) — GATE check_ui5_freestyle_traps; düzenlenebilir miktar type=Text + onNumericLiveChange filtresi
- [UI deploy non-interaktif YAPILIR](feedback_ui-deploy-noninteractive.md) — "deploy edemem" deme; std/03 §2.4.1: .conn_adt→FIORI_TOOLS env + --yes; tr -d '\r', mutlak --prefix
- [Lokal test OK'siz SAP deploy yok](feedback_deploy-lokal-test-onayi-sart.md) — FE build→bug-gate→LOKAL sun (8101)→kullanıcı "OK"→ANCAK O ZAMAN deploy; erken deploy YASAK
- [Subagent karar kuralı](feedback_subagent-karar-kurali.md) — önemsiz→kendin; token-ağır+seri→tek subagent; paralelleşir→ÇOK fan-out; paraleli tek-subagent'a seri=anti-pattern
- [Lider bloke olmama / background](feedback_lider-bloke-olmama-background-dispatch.md) — Agent çağrısı DAİMA run_in_background:true; foreground yalnız kronik-debug istisnası; dispatch→kullanıcıya açık kal
- [Context yönetimi: 5-yollu + Rewind](feedback_context-yonetimi-compact-clear.md) — her turn Continue/**Rewind(esc esc)**/compact/clear/subagent; Rewind>Correcting; rot~%40-50→düşer; /clear öncesi checkpoint ZORUNLU
- [Scratch dosyaları .tmp/ klasörüne](feedback_scratch-dosyalari-tmp-klasoru.md) — geçici dosya ana klasöre DEĞİL .tmp/'ye; kalıcı script→scripts/TempScripts/
- [RAP editableFieldFor key-create](feedback_rap-editablefieldfor-key-create.md) — Released BO CREATE BY _assoc: semantik key salt-okunur → `<Key>ForEdit`; takılınca projeksiyon CDS oku; adt-rap §35
- [UI5+V2 plumbing reuse + tuzaklar](feedback_ui5-v2-plumbing-reuse-traps.md) — GATE check_ui5_freestyle_traps; plumbing'i kanonik §K'dan reuse; save=sıralı update, nav=to_X; done=runtime-doğrula
- [Ajan brifing'inde SendMessage to main zorunlu](feedback_agent-briefing-sendmessage-main.md) — "lider'e DÖN" YETMEZ; ÇIKTI bölümüne SendMessage({to:"main"}) ekle yoksa rapor gelmez
- [Gate'lenmemiş kural ≈ kuralsız](feedback_kural-gate-lenmeli-yoksa-anlamsiz.md) — GATE check_rule_gate_coverage; her kural atlanamaz kurgulanmalı (validator/hook/checklist)
- [TR app i18n: her iki dosya](feedback_i18n-tr-her-iki-dosya.md) — language=tr app'te i18n_tr override eder; etiket değişikliği HER İKİ dosyada + hard refresh
- [RAP BY-assoc read ALL FIELDS WITH](feedback_rap-by-assoc-read-all-fields.md) — GATE check_rap_byassoc_keys_only; READ BY _assoc YALNIZ KEY döner, non-key için ALL FIELDS WITH
- [Playwright UI5: firePress + model API](feedback_playwright-ui5-firepress-model-api.md) — .click() bazen press tetiklemez → firePress()/controller-invoke + getModel().getData() ile doğrula
- [Inactive-worklist audit (HTTP-200≠aktif)](feedback_inactive-worklist-audit-http200-degil.md) — commit+gün-sonu worklist_audit.py; root-CDS-alan FOR-BEHAVIOR BDEF'i sessizce inactive; canlı re-verify
- [Çözülmüş tooling-bug'ları (10)](feedback_resolved-tooling-bugs.md) — regresyon ref: adt_dtel_create·adt_get-ddic·source-drift·bdef-blues·csrf·push-stale-lock·cds-escape·mcp-stdio·table-read
- [Behavior pool main boş → CCIMP tuzağı](feedback_behavior-pool-main-empty-ccimp-trap.md) — managed pool source/main DAİMA boş; handler CCIMP'te; incelemeden ÖNCE CCIMP çek, BDEF↔lhc_* eşle
