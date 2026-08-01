# İNFRA-CHANGELOG — bileşen-başına değişiklik/gerekçe/test kaydı

> **Ne:** Paylaşılan altyapıdaki her anlamlı değişikliğin NEDENİ (hangi senaryo/vaka) ve
> NASIL test edildiği. **Niçin:** bileşenin bugünkü hali eski bir vakanın çözümüdür;
> bilmeden dokunan onu geri açar. **Kim yazar:** LİDER (fix-kapanışında; infra-expert
> worktree-raporunda taslak-satırı verir). **Kim okur (GARANTİLİ):** infra-expert **F0**
> adımı — değiştireceği bileşenin buradaki geçmişini okumadan fix'e başlayamaz.
> Fixture-ref = eski senaryonun YENİDEN-KOŞULABİLİR hali (tests/fixtures + koşucu CI'da).
> Daha eski tarihçe: git-log (worktree'de tam) + `removed-controls.md` (kaldırmalar).
> **Test-reçeteleri AYRI dosyada:** `governance/infra-test-recipes.md` (bileşen-başına koş-adımları) — F0'da İKİSİ birlikte okunur.

Format: `| tarih | değişiklik | NEDEN (senaryo/vaka) | NASIL test edildi | fixture/koşucu-ref | PR |`
Her bileşen bölümü ayrıca **`Test-senaryosu:`** bloğu taşır — o bileşene dokunan HERKESİN
(infra-expert F0/F3 + lider bağımsız-koşum) çalıştıracağı adım reçetesi; mevcut test-varlığı
yoksa `[ÖNERİ]` etiketiyle aday yazılır (varmış gibi gösterilmez).

## hook_shim (+tüm hook'ların stdin/stdout zemini)
| 2026-08-01 | stdin UTF-8 reconfigure | Harness payload'ı cp1252-mojibake ulaşıyordu ("GÖREV"→"GA–REV"); 16 hook'ta Türkçe alanlar sessiz bozuktu — brifing-lint FP'sinin kökü (debug-log kanıtı) | Sentetik Türkçe payload: FP-yok(P) + şablonsuz-nudge(N) | elle: sentetik-payload komutu howto-sistem-denetimi §3'te | core#67 |

## pre_tool_guard.py (bug-avi turu)
| 2026-08-01 | Kabuk-sozdizimi modeli: tirnak-duyarli `_kelimeler`/`_segmentler` + POSIX/git/pflag `_bayrak_degerleri`; commit-mesaji cikarimi token-tabanli, kural-9 ve iki sizinti gate'i SEGMENT BASINA | Adversarial bug-avi 4 atlatma (canli repro): AV-16 `git commit -am` (kumelenmis kisa bayrak lookbehind'e takiliyor -> mesaj HIC cikarilmiyor) · AV-17 `--file=` taninmiyor · AV-18 zincirde "odunc hedef" · AV-18b gorunurluk ILK `--repo`dan cozuluyor (PRIVATE okuma -> PUBLIC yayin SIZDI) | (1)bozuk: 6 atlatma+varyant BLOK (2)temiz: 22 FP vakasi (grep/tar `-am`, tirnak-ici bahis, private repo, temiz `--file`) (3)3.baglam: PowerShell + `git -C` + here-string; MUTASYON: fix-oncesi koda karsi korpus 29/45 (16 FAIL). LIDER BAGIMSIZ: eski-vs-yeni 8 vaka, sapma 0 | tests/fixtures/pre_tool_guard/ + tests/run_guard_fixture_tests.py (45 vaka) | core#75 · GEVSETME: 2 FP-blogu kalkti (private hedefli yayin/commit — gate'in KENDI sartnamesi) |
| 2026-08-01 | `_core_hedef_mi`: yol-dizgesi + ISARET-DOSYASI kimligi (CLAUDE.core.md ve claude/kesin-yasaklar.canonical.md) | AV-21 (KRITIK): core kimligi ADINDAN okunuyordu -> `git worktree`/adi farkli klonda GENERICIZE-LEAK kurali SESSIZCE kapaliydi (ayni payload DEV_CORE'da exit 2, worktree'de exit 0; UC ayri ajan bagimsiz buldu + lider kontrol grubuyla olctu). Worktree infra-expert'in ZORUNLU alani. Hafifletici CANLI dogrulandi: core_precommit worktree'de calisiyor (staged sizinti -> exit 1), delik yazim-anindaydi | Gercek `git worktree add` ile sentetik core ikizi: sizintili->2, temiz->0, fix-oncesi->0; FP: SOURCE_CODES/.tmp/scratchpad/tek-isaretli dizin->0; maliyet 0,42 ms/cagri | tests/fixtures/pre_tool_guard/agac/ | core#75 |
| 2026-08-01 | `test_commit_message_leak_gate` CI'a BAGLANDI (+3 spec testi) | Changelog 07-28'de "...(CI)" diyordu ama workflow'da adim YOKTU: gate'in kendi testi hic kosmadi ve 3 gun sonra ayni gate `-am` ile atlatildi. KOD != KABLOLAMA — changelog'un kendisi de yanlis beyan tasiyabiliyor | Lokal 17/17; CI adimi bu PR'da gorunur | scripts/tests/test_commit_message_leak_gate.py | core#75 |
| 2026-08-01 | `_core_hedef_mi`: isaret-dosyasi kimligine IKI FP freni — ata-taramasindan once `os.path.abspath` + hedefin KENDI deposunun kokunde (`.git`) durma | AV-21 fix'i ters yonde sizdirdi: PR #75 CI'da konformans (4) "core DISI hedef taranmaz" dustu. Kok OLCULDU (liderin komsu-repo hipotezi YANLISTI): goreli `--project` + goreli hedefte `Path.parents` `..`/`.` ile biter, `.` = CALISMA DIZINI = core checkout'u -> komsu projenin dosyasi core sanildi. Ayrica mutlak yolda ust/komsu depoya tirmanis ACIKTI (ayri fixture'la kanitlandi). SIRA KRITIK: isaretler ONCE, sinir SONRA — tersi AV-21'i geri getirir | CI komutu yerelde 1 ihlal -> 0; korpus 45->48; ARA-SURUM mutasyonu (frenler sokulu) yeni 2 FP vakasini FAIL veriyor; worktree pozitifi hala exit 2; lider bagimsiz 8-vaka sonda sapma 0 | tests/fixtures/pre_tool_guard (AV-21c/d + agac/komsu_proje, DOTGIT->.git) | core#75 · GEVSETME: komsu-depo ve goreli-yol FP'leri kalkti (kuralin kendi (4) sartnamesi) |
| 2026-08-01 | `run_fixture_tests.py` UC bolume ayrildi (validator bad/good + regresyon vektorleri + guard payload korpusu) — tek giris noktasi korundu | Uc paralel bug-avi fix'i ayni dosyaya bolum ekledi; rebase catismasi birlesim olarak cozuldu. TEK komut ilkesi bilincli: ikinci bir CI adimi eklemek 'kablolamayi unutma' riskini artirir (bu turda test_commit_message_leak_gate tam boyle 3 gun kablosuz kalmisti) | TOPLAM 75/75 (12 validator + 15 regresyon + 48 guard payload); her bolumun kendi mutasyon testi korundu | tests/run_fixture_tests.py | core#75 |
| 2026-08-01 | pre_tool_guard + pull_before_edit: savunmaci giris indirgeme (`_sozluk`/`_metin`; dict/str varsayimi kaldirildi) | W2-VH-01/02: `json.load` sariliydi ama SONRASI girdinin dict ve str oldugunu VARSAYIYORDU. Olculdu: 10 bozuk payload'in pre_tool_guard'da 6'sinda, pull_before_edit'te 5'inde uncaught AttributeError/TypeError -> exit 1 + traceback. Sozlesme exit 2 = blok oldugu icin exit 1 'blokladi' DEGIL: o cagrida guard'in 9 kurali da devre disi. Kontrol grubu ayni kosumda SAGLAMDI (hedefsiz gh -> exit 2, ls -> exit 0) ve config_change_guard 10/10 COKMEDI -> ortam artefakti degil, savunmasiz giris isleme | P: kontrol vakalari degismedi (2/2) · N: 10 bozuk payload -> 0 cokme (once 6 ve 5) · REGRESYON: korpus 48->55, konformans 0 ihlal, spec 12 senaryo, paket 83/83 · MUTASYON: fix-oncesi guard'a karsi 49/55 (yeni 7 vakanin 6'si duser) | tests/fixtures/pre_tool_guard/serbest.json (SEKILSIZ vakalari) + run_guard_fixture_tests `ham_payload` destegi | core#79 |

## scripts/hooks/recall_inject.py + build_recall_index.py (JIT-recall)
| 2026-08-01 | Doğuş (radar ADOPT-1) — eşik=5, TOP_K=3, MIN_PROMPT=40, fail-open | "Cevap yazılıydı-okunmadı" tekrar sınıfı (classrun 1-ay vakası); eşik/kısa-prompt filtresi = alarm-yorgunluğu freni (D7 dersi) | P: classrun-derdi→#19, RAP→3-ders; N: selam sessiz, bozuk-indeks exit0; E-CANLI: ilk gerçek olayda blok göründü | fixture yok (hook LLM'siz-deterministik; sentetik-payload komutları howto'da) | core#69 |
| 2026-08-01 | Builder'a howto-kaynağı + **Tetik-satırı** önceliği + öz×2 | İnfra-howto'su "validator/hook" sorgularında eşiği aşamıyordu; vaka-özel eşik-GEVŞETMEK yerine kaynak-zenginleştirme (F2-ruhu: sınıf-çözümü) | P: infra-sorgusunda howto ilk-sıra; N: alakasız sessiz | aynı | core#71 |

## scripts/hooks/post_validate.py
| 2026-08-01 | subprocess-capture'lara encoding=utf-8 (EXPRESS) | Alt-validator UTF-8 çıktısı cp1252 decode → hook-relay mojibake ("BAYAT â€”"); changelog-gate'in ilk canlı tetiklemesinde görüldü | P: sentetik Türkçe-çıktılı child capture eş | — | core#72 |
| 2026-08-01 | TRIGGER'a dosya-sınıfı seçiciliği (HIZLI_KUME 5 sınıf; eşleşmeyen=TAM tur fail-closed) | Kural-edit'i başına 13sn tam-tur (denetim §3B); fail-open'a düşmeme şartıyla daraltıldı | P: rules-edit 0,55sn; N: bozuk-CORE-INDEX yakalandı + tablo-dışı=tam-tur; E: pre-commit/CI değişmedi | tests/fixtures (P1 sınıf-fixture'ları) | proje#62 |

## scripts/validators/run_all_validators.py + 4 yavaş validator
| 2026-08-01 | rglob→pruned-walk (node_modules/attic dışla) + ThreadPool paralellik | quick 13,6sn'nin %60'ı 4 validator'dı; kök: rglob node_modules yürüyordu (1,38→0,06sn kanıtı) | P: 13,6→2,5sn; N: kirli-fixture hâlâ FAIL + workers=1 bayt-eş; E: exit-semantiği aynı | run_fixture_tests 10/10 | proje#62 |

## mcp_servers/sap_adt (tools/atom.py + _reviewer.py)
| 2026-08-01 | `_ACTIVATION_URI_SEG` += include/prog-i | Klasik program+include co-activation'ı unsupported_type veriyordu (T1.6 gateway saha-bulgusu) | N-canlı: var-olmayan include'a activate → unsupported_type GİTTİ (URI çözüldü) | — (canlı-SAP testi) | core#67 |
| 2026-08-01 | Reviewer SKIP-görünürlüğü ("PRE-FLIGHT KOŞMADI (sebep) — PASS sanma") | doma/dtel/prog tiplerinde pre-flight SESSİZCE atlanıyordu (denetim G2; "reviewer PASS dedi" yanılsaması) | P: DTEL-simülasyonda satır var; N: class_push'ta yok; E: BLOCKER mantığı değişmedi | — | core#69 |

## mcp_servers/sap_adt/_conn.py + guardrails.py + data_guard.py + scripts/switch_tier.py + statusline.py (ADR 0010 tier)
| 2026-08-01 | **FAIL-CLOSED tier** (`TIER_UNKNOWN`; çözülemezse mutasyon RED) + **TAM-ANAHTAR** satır eşleşmesi (`_conn_line_value`); aynı düzeltme switch_tier/_field_of_file, statusline/sap_system, sap_doctor; `require_writable_tier`/`require_data_access` içindeki `(tier or "DEV")` İKİNCİ fail-open katmanı kaldırıldı; conn-şablonlarına `ADT_SAP_TIER` satırı eklendi | Bug-avı KAYIT-1 (kullanıcı kararı: "fail-closed + tam eşleşme"): (a) tier hiçbir yerde bulunamazsa fonksiyon **DEV** dönüyordu — koruma katmanı, girdisi eksikken korumayı KAPATIYORDU; (b) `s.startswith("ADT_SAP_TIER")` öneki, `ADT_SAP_TIER_OLD=DEV` satırının gerçek `ADT_SAP_TIER=PRD` satırını GASP etmesine izin veriyordu (statusline'da en tehlikeli yön: PRD sisteminde ekranda "DEV") | 24 senaryo / 3 bağlam: MCP (`get_active_tier` 4) + guard katmanı (`require_writable_tier`/`require_data_access` 9, None ve "" dahil) + GÖREV-DIŞI (switch_tier 4, statusline 6, sentetik proje kökünde). **Kontrol-grubu: aynı fixture eski kodda 14/24 — 10 ayırt edici FAIL** | `tests/fixtures/tier_fail_closed/run.py` (run_fixture_tests OZEL_TESTLER) | — |

## scripts/inspector.py (v2)
| 2026-08-01 | B5 üçlü-kıyas (fark_raporu TEK-kaynak) + [bilgi]-sınıfı + A2 malformed-eşiği(4) + gerçek negatif-test sayacı | 6 overlay-sapmasının 1'i görünüyordu; "0/45" ölçümsüz sabitti; A3 her-oturum alarm-yorgunluğuydu (denetim R5) | P: canary; N: kasıtlı-sapma 1→0; eşik-4 gerekçesi tarihli (geçiş-dönemi satırı) | inspector --self-test | core#69 |

## scripts/git-hooks/core_precommit.py
| 2026-08-01 | ~~4.kontrol: İNFRA-CHANGELOG gate~~ **BU KAYIT SAHTEYDİ — kod merge EDİLMEDİ** (aşağıdaki dürüstlük notu) | — | — | — | core#72 |
| 2026-08-01 (2. deneme, GERÇEK) | 4.kontrol: İNFRA-CHANGELOG gate — staged infra KODU (`scripts/**.py`, `mcp_servers/**.py`, `tests/**.py`, `scripts/git-hooks/pre-commit`) varsa aynı commit'te bu dosya da değişmeli; kaçış `IX_NO_CHANGELOG=1`. Muaf: `.md`/doküman, `tests/fixtures/**`, `attic/**`, `--all`/CI modu | Kullanıcı talebi: kayıt-güncelliği GARANTİ (nudge yetmez); moratoryum şart-5 açık-onay ALINMIŞTI. İkinci sebep: kapının kaybı 1 gün fark edilmedi → fixture'sız gate kaybolur | Sandbox git reposunda 13 senaryo: S1 infra+kayıtsız→BLOK · S2 kayıtlı→SERBEST · S3 yalnız-doküman→SERBEST · S4 kaçış→SERBEST+uyarı · S5 fixture-verisi muaf · S6 mcp_servers→BLOK · S7 `--all`→susar · **S8 GERÇEK commit BLOKLANDI · S9 kayıt eklenince GERÇEK commit GEÇTİ** (commit sayısı 1→2). Kontrol-grubu: aynı fixture eski kodda 7/13 (kapı yoktu) | `tests/fixtures/changelog_gate/run.py` (run_fixture_tests OZEL_TESTLER) | — |

> ⚠ **DÜRÜSTLÜK NOTU (2026-08-01, bug-avı KAYIT-2):** Yukarıdaki İLK satır, hiçbir zaman
> merge edilmemiş bir kodu "canlı test edildi" diye anlatıyordu. Kök sebep: değişiklik
> yerel `main` üzerinde commit'lendi (66b7d02/e598018), sonra `reset --hard origin/main`
> ile silindi; changelog satırı AYRI bir PR'la hayatta kaldı, kod kayboldu. Sonuç:
> `core_precommit.py` 3 kontrol koşarken doküman 4 kontrol vaat etti (sahte-koruma sınıfı,
> R9/R10 vakasının kardeşi). Kanıt: `git log --all -S IX_NO_CHANGELOG -- scripts/` → 0 eşleşme;
> dosyanın son dokunuşu e2fcef2 (2026-07-13). **Ders:** "eklendi" satırı, kalıcı bir
> fixture-ref'i olmadan yazılmamalı — fixture olmayan gate sessizce kaybolur ve kayıt yalan söyler.

## scripts/utils/claude_overlay.py + team_setup.py
| 2026-08-01 | fark_raporu() + materyalize(onayli) kapısı + --overlay-onayli | Senkron elle-düzeltmeleri SESSİZCE eziyordu (B5 5-günde-yeniden-bayat vakası; R4c) | N: bayraksız koşum 4-fark listesiyle RED; P: onaylı 6-dosya; +NameError(a/args) EXPRESS-fix'i | — (koşum-kanıtları plan T2.5) | core#69 |

## scripts/hooks/watchdog_launch.py (brifing-lint)
| 2026-08-01 | R2-şablon izi nudge'ı (≥400kr, 2-iz, bloklamaz) + NFKD-katlama + debug-log | Şablonsuz-brifing sessiz-kayıp sınıfı; İLK canlı ateşlemede FP çıktı → kök mojibake'ydi (yukarı bkz) — FP-bütçesi ilkesiyle önce teşhis-logu eklendi | P/N: temiz/kötü/kısa-muaf 3-varyant | sentetik-payload | core#69+#71 |

## playbook/checklists (bug-checklist-*)
| 2026-08-01 | BE-63/64/65 + FE-36/37 (R6) ve BE-66/FE-39 (infra-kapsam) | #16/#18 6'şar tekrar (denetim R6); infra nokta-fix sınıfı (howto-infra-fix) | coverage-gate yeşil (59 iddia); FE-38 numara-çakışması yakalandı→FE-39 | check_rule_gate_coverage | core#69/#71 |

## claude/agents/* (kanonikler)
| 2026-08-01 | PATTERN#20 terfileri (syntax_check gerçeği ×3 + abaplint çıkış-şartı + tool-listeleri) + batch-talimatı + model-beyanları | Core kendi-kendini-yalanlayan talimat dağıtıyordu (denetim R4); model-miras bilinçsizdi (P8) | Deneme-spawn echo'ları + yeni-oturum transcript (BE=opus/FE=sonnet) + grep=0 eski-talimat | — | core#65/#66/#69 |


## scripts/behavior_manifest.py (F2 davranis-yuzeyi)
| 2026-08-01 | `.claude/settings.local.json` yuzeyden CIKARILDI (⚠GEVSETME, kullanici acik onayi) | Bug avi AV-20: dosyayi Claude Code her izin onayinda yeniden yaziyor -> F2 alarmi KALICI aciktı; alarm-yorgunlugu F2'nin varlik amacini (gercek tamper tespiti) ortadan kaldiriyordu | P: temiz->OK; P2: settings.local.json'a dokun->alarm YOK; **N: settings.json'a dokun->alarm VAR (exit 1)**; geri-al->OK | — (elle P/N komutlari test-recipes'te) | (bu PR) |
Test-senaryosu: (1) `python core/scripts/behavior_manifest.py generate` (2) dogrula -> `[ OK ]` (3) `.claude/settings.local.json`'a bosluk ekle -> **alarm CIKMAMALI** (4) `.claude/settings.json`'a bosluk ekle -> **alarm CIKMALI, exit 1** (5) geri al -> `[ OK ]`. Adim-4 bu gevsetmenin sinir bekcisidir: FAIL vermezse yuzey fazla daralmis demektir.

## scripts/create_transport.py (SILINDI)
| 2026-08-01 | Script SILINDI | Bug avi E2 olu-kod taramasi: core=0/proje=0 gercek cagiran (grep eslesmelerinin hepsi alakasiz `create_transport_doc` RAP action'i ve `SAPClient.create_transport` kutuphane metodu). Ayrica ADR 0005-C transport yaratmayi ZATEN YASAKLIYOR -> varligi tutarsizlik sinyaliydi | Referans sayimi + eslesme satirlarinin tek tek incelenmesi (ham grep sayisi YANILTICIYDI: 5 core / 10 proje eslesme vardi, hicbiri script'e ait degildi) | — | (bu PR) |
## scripts/utils/project_config.py (+ .conn_adt okuyuculari: mcp _conn, pre_tool_guard)
| 2026-08-01 | utf-8 -> utf-8-sig (BOM sinif-fix'i, 4 okuyucu) | AV-02: BOM'lu project.yaml'da anahtar SILINMEZ, ADI BOZULUR -> cfg() None -> MCP fail-closed -> tum SAP tool yuzeyi sessizce ping'e iner. Tetikleyici bilinen PowerShell-BOM tuzagi. Sinif yayilimi OLCULDU: BOM'lu .conn_adt'de ADT_SAP_TIER=PRD sessizce DEV'e dusuyordu; pre_tool_guard'da ADR-0010 baglanti-gate'i yalniz-host farkinda FAIL-OPEN oluyordu | 7 vektor + KABLOLAMA (MCP 19/18/1 matrisi BOM'lu yaml ile korunuyor); mutasyon M1 -> 4 FAIL | tests/fixtures/av02_project_config_bom | core#74 |
Test-senaryosu: (1) `python tests/run_fixture_tests.py` -> 24/24 (2) MUTASYON: `utf-8-sig`->`utf-8` -> exit 1 + AV-02 adiyla FAIL (vermezse test bostur) (3) BOM'lu project.yaml ile MCP profil matrisi: s4_private -> 19 tool (1'e duserse AV-02 geriledi).

## scripts/genericize_common.py (SAP_USER_PAT + SAP_USER_BAGLAMLI_PAT)
| 2026-08-01 | Yazim-varyantina gore AYRI SIDDET: BUYUK harf baglamsiz + rakam soneki; kucuk/karisik harf YALNIZ kimlik baglaminda (ayni satirda user/kullanici/login/hesap/owner). Placeholder muafiyeti korundu | AV-03: kucuk-harf ve rakam-sonekli gercek kimlikler son kapidan kaciyordu (D1 2026-07-10 sinifi, geri-alinamaz). ILK TASLAK topyekun IGNORECASE'ti ve olagan `d_` onekli degisken adlarini (veri/satir/toplam gibi) kimlik saniyordu -> FP seli/bypass riski (PATTERN #14). ⚠ Ilk turun "FP=0" olcumu YONTEM HATASIYDI: `--all` git ls-files kullanir = YALNIZ TAKIPLI dosyalar, yeni fixture'lar gorulmedi; gercek commit 4 ihlalle bloklandi | Kapsam ACIK (iki agacin TUM dosyalari, takipsiz+tests dahil): FP 4->0 (cekirdek 505 dosyada nihai eslesme 0, lider bagimsiz olcumu de 0), FN artisi yok (2/2 gercek kimlik). Rakam-soneki ayri olculdu: +2 token, ikisi de gercek kimlik, 0 FP. Mutasyon 7/7 (M2b = hatali ilk taslak, NEGATIF vektorlerce yakalaniyor). KABUL: git add -A + staged gate -> exit 0 | tests/fixtures/av03_genericize_sap_user | core#76 |
Test-senaryosu: (1) suite 25/25 (2) MUTASYON M2b: baglam SARTINI kaldir -> NEGATIF vektorler yakalamali (yakalamiyorsa FP korumasi test altinda DEGIL) (3) KABUL TESTI yeni dosya ekleyen her fix icin ZORUNLU ve `--all` DEGIL: `git add -A && python scripts/git-hooks/core_precommit.py` -> exit 0. `--all` git ls-files kullanir = takipli dosyalar; yeni/takipsiz dosyani YAPISAL OLARAK GOREMEZ ("yesil" verir). (4) Baglam ayrimi capasi: `d_` onekli sira-disi olmayan bir degisken adi baglamsiz satirda SESSIZ; ayni ad `ADT_SAP_USER=` gibi bir kimlik anahtarinin yanindayken YAKALANIR.

## scripts/worklist_audit.py
| 2026-08-01 | Uc-degerli mantik onarimi (_version_exists + _classify + _exit_kodu) | AV-13: `and`->`or` hatasi nedeniyle biri-None digeri-False -> PHANTOM ("silinmis") -> --discard-phantoms gercek WIP objeyi discard ediyordu (VERI KAYBI); ters yon (True,None)->STALE -> commit-gate sahte-YESIL. Alt katman: `status==200` sunucu arizasini "yok" sayiyordu | 9 siniflama + 9 durum-kodu + cikis-kodu vektoru; mutasyon M4/M5/M6 | tests/fixtures/av13_worklist_classify | core#74 |
Test-senaryosu: (1) suite 24/24 (2) MUTASYON: `_classify` `or`->`and` -> exit 1 (3) CIKTI-BUTUNLUGU: suite ciktisi >=22 satir olmali; 6 satira duserse worklist_audit'in import-ani stdout devralmasi geri gelmistir (sayac yine "24/24" der - SAYIYA degil SATIRLARA bak).

## scripts/create_package.py (SILINDI)
| 2026-08-01 | Script SILINDI + 3 atif mekanizma diline cevrildi | Bug-avi E2: tek isi SAP paketi yaratmak = ADR 0005-C yasagi. `check_package.py` paket yoksa kullaniciya 'create_package.py kullan' diye YAZDIRIYORDU — yani yasagi cigneme talimati araciimizin kendi ciktisindaydi. Kullanici karari: ajan paket yaratmamali | KIRIK-REFERANS SUPURMESI: import eden yok (0) · check_package.py compile+--help OK ve paket-yok dali artik operatore yonlendiriyor · MCP'de paket yaratan tool YOK · sap_adt_lib/sap_client'ta `create_package` metodu YOK · compileall OK · run_fixture_tests 27/27 | — | core#77 |
Test-senaryosu: (1) `grep -rn create_package` -> yalniz 3 tarihsel not (silindigini soyleyenler) (2) `python scripts/check_package.py --help` -> exit 0 (3) paket-yok dali metninde 'create_package' GECMEMELI (4) MCP tool listesinde paket yaratan tool ARANMALI ve BULUNMAMALI.

## SIR-DOSYASI kapsami (check_core_not_committed + core_precommit 5.kontrol)
| 2026-08-01 | Pathspec JOKERLI (`*.conn_adt`) + core_precommit'e 5. kontrol (SIR-DOSYASI, her iki modda) + `scripts/.conn_adt` SILINDI | CANLI IHLAL: `scripts/.conn_adt` ilk cekirdek commit'inden beri (f85e3fd, 2026-07-08) PUBLIC repoda TAKIPLIYDI. Iki bagimsiz sebep: (a) validator'un pathspec'i JOKERSIZDI -> `git ls-files -- .conn_adt` YALNIZ koku esler, alt dizini GORMEZ (kontrol grubu: `"*.conn_adt"` aninda buldu); (b) o validator PROJE repolarinda kosar, DEV_CORE'un KENDISINI hicbir katman denetlemiyordu (core-ci'da adim yok, pre-commit'te kontrol yoktu). Dosyanin degerleri placeholder'di (kendi sizinti-desenimizle 0 eslesme) -> kimlik SIZMADI; ama kanal aciktI: `create_conn_file()` cwd'ye `.conn_adt` YAZAR | P: agac temiz -> exit 0; N: sentetik repoda kok/derin/turev/.csrf staged -> BLOK; FP: `conn_adt.template` (degersiz sablon) SERBEST; S5: sir cikarilinca serbest | tests/fixtures/sir_gate (6 senaryo, run_fixture_tests bolum-OZEL) | core#78 |
Test-senaryosu: (1) `python tests/fixtures/sir_gate/run.py` -> 6/6 (2) `git ls-files -- "*.conn_adt"` -> BOS olmali (3) MUTASYON: pathspec'ten joker kaldir -> S2 (derin) FAIL vermeli; vermiyorsa fixture korelmis. (4) ⚠ Fixture ORTAM IZOLASYONU sart (`CLAUDE_PROJECT_DIR` mirasi gate'e baska repoyu cozduruyor) ve gate yolu `parents[3]`; ikisi de ilk kurulumda yanlisti ve fixture 6/6 FAIL verip sebebi KOD sanildi.

## mcp_servers/sap_adt/_reviewer.py (tip kapsami)
| 2026-08-01 | OBJECT_TYPE_TO_TASK: push'un kabul ettigi TUM tipler BEYAN edildi (esanlamli + explicit None) + senkron testi | W2-MCPT-03/MG-02: push katmani tip esanlamlilarini kabul ediyordu (_TYPE_KEY_CANON, _ACTIVATION_URI_SEG), reviewer haritasi yalniz kanonik adlari taniyordu -> eksik anahtar = .get() None = ADR 0006 pre-flight SESSIZCE atlanir. Olculdu: ddls -> BLOCKER+RED, cds/cdsview/ddl -> SKIP+GECTI (ayni obje, ayni ADT URL'i). tabl <-> table/structure asimetrisi daha agirdi: table_update zinciri check_table_field_drop (VERI-KAYBI BLOCKER'i) tasir -> table yazimiyla o guard HIC kosmuyordu. ASIL KUSUR tek eksik anahtar degil, IKI TABLONUN SESSIZCE AYRISABILMESIYDI | Fixture push tablolarini (30 tip) reviewer haritasiyla capraz kontrol eder + esanlamli-esitligi + task_for_push cozumlemesi; MUTASYON: eski harita ile 2/7, 19 tip eksik listelendi | tests/fixtures/reviewer_tip_kapsam | core#80 |
Test-senaryosu: (1) `python tests/fixtures/reviewer_tip_kapsam/run.py` -> 7/7 (2) MUTASYON: haritadan cds/table satirlarini sil -> FAIL + eksik listesi (3) AYRIM: 'eksik anahtar' ile 'bilincli None' AYNI SEY DEGIL — test ANAHTAR VARLIGI arar, deger dolulugu degil; yeni tip push'a eklenip harita unutulursa test kirilir.

## mcp_servers/sap_adt/_conn.py (cift-anahtar ayrismasi)
| 2026-08-01 | SON-KAZANIR + cakisma tespiti: tier cakisikta UNKNOWN (fail-closed), `_conn_value` dotenv ile hizalandi | W2-MG-01: ayni dosyayi IKI okuyucu FARKLI okuyordu — `_conn.py` ilk-kazanir, `sap_adt_lib` `load_dotenv` ile SON-kazanir (GERCEK BAGLANTI). Olculdu (DEV ustte / PRD altta): `get_active_tier()`=DEV (guard 'mutasyon serbest' der) ama dotenv/istemci=PRD (baglanti PRD'ye gider) -> SESSIZ YANLIS-SISTEM YAZIMI. Tetikleyici bizim KENDI mesajimiz: tier fail-closed uyarisi ".conn_adt'ye ADT_SAP_TIER=... EKLE" diyor, ekleyen cift anahtar uretir (`switch_tier` dosyanin tamamini kopyaladigi icin cift URETMEZ) | 6 senaryo: kontrol tek-DEV / tek-PRD · cift-cakisik->UNKNOWN · cift-ayni->zararsiz · onek-tuzagi REGRESYONU · tier-yok->UNKNOWN; her senaryoda `_conn_value(URL)==dotenv(URL)` capasi. MUTASYON: eski okuyucu ile 5/6 (cift-cakisik vakasi duser) | tests/fixtures/conn_cift_anahtar | core#81 |
Test-senaryosu: (1) `python tests/fixtures/conn_cift_anahtar/run.py` -> 6/6 (2) MUTASYON: `_conn.py`'yi eski surume al -> cift-cakisik vakasi FAIL (3) YAN-ETKI: `tier_fail_closed` 1e vakasinin GIRDISI guncellendi (iddiasi degil) — o girdi farkinda olmadan ILK-KAZANIR sozlesmesini de kodluyordu; vaka onek-gaspi amacina indirgendi, cift-anahtar davranisi ayri fixture'da test edilir ki iki sozlesme birbirini GIZLEMESIN (4) ⚠ Fixture `get_conn_path` YONLENDIRMESI olmadan HICBIR SEY olcmez (gercek proje dosyasi okunur, hepsi DEV doner) — ilk kurulumda tam bu oldu, kontrol grubu (tek-PRD->PRD) yakaladi.

## mcp_servers/sap_adt/tools/atom.py (adt_get DDIC dali)
| 2026-08-01 | DDIC dalinda `exists: xml is not None` KALDIRILDI -> `_miss_or_unreachable` siniflandirmasi + siniflandiriciya 'yokluk kaniti' sarti | W2-MCPT-01: alt katman (`sap_client.get_ddic_object`) HER istisnayi yutup None donduruyor -> ust kattaki except dali DDIC tipleri icin HIC atesLENMIYOR. Olculdu (stub'li kontrol grubu): 404 -> exists:false (dogru) ama HTTP 500 / 403-logon / ReadTimeout / baglanti-kopmasi da exists:false + ok:true -> ajan 'yok' sanip YENIDEN YARATIR (ADR 0005-A siniri) ya da mevcut objeyi ezer. Ayni sinif `class` yolunda 2026-07-31'de kapatilmisti, DDIC geride kalmisti. AYRICA `_UNREACHABLE_MARKERS` yalniz AG katmanini taniyordu: sunucu/yetki hatalari (500/403) o listeye girmedigi icin yine exists:false'e dusuyordu | 6 vaka + KONTROL GRUBU (obje-VAR -> exists:true, gercek-404 -> exists:false KORUNDU); hata siniflari artik ok:false + belirsiz/unreachable. MUTASYON: eski atom.py ile 2/6 | tests/fixtures/adtget_yokluk_kaniti | core#82 |
Test-senaryosu: (1) `python tests/fixtures/adtget_yokluk_kaniti/run.py` -> 6/6 (2) MUTASYON: atom.py'yi eski surume al -> 2/6 (3) ⚠ KONTROL GRUBU OMURGADIR: '404 hala exists:false' satiri kaldirilirsa test asiri-siki olur ve GERCEK yokluk tespitini de bozar — o satir korunur.

## scripts/create_rap_service.py (aktivasyon dogrulamasi)
| 2026-08-01 | HTTP durum kodu ONCE kontrol edilir + fallback'e 'ADT yaniti mi' sarti | W2-MCPT-02: `activate_and_verify` yanit GOVDESINI ayristiriyordu ama `r.status_code`'a HIC bakmiyordu; `_activation_failures` fallback'i de 'hata isareti YOKSA basarili' diyordu. Olculdu (kontrol grubuyla): 200+basari -> dogru, 200+type=E -> dogru reddedildi, ama HTTP 500 / HTTP 403-logon / 200+BOS govde -> 'AKTIVE EDILDI'. Ustelik fonksiyonun kendi docstring'i 'sahte OK imkansiz' diyordu — DOKUMAN DAVRANISI YALANLIYORDU. Aktivasyon geri-alinamaz zincirin son adimi; sahte-OK readback/publish/sonraki objeyi yanlis temele oturtur | 11 vaka (6 saf-ayristirici + 5 uctan-uca), KONTROL GRUBU dahil: 200+basari GECER ve ESKI-STIL chkl yaniti GECER (asiri-sikilasma capasi). MUTASYON: eski surumle 5/11 | tests/fixtures/aktivasyon_sahte_ok | core#83 |
Test-senaryosu: (1) `python tests/fixtures/aktivasyon_sahte_ok/run.py` -> 11/11 (2) MUTASYON: `create_rap_service.py`'yi eski surume al -> 5/11 (3) ⚠ KONTROL GRUBU OMURGADIR: '200+basari -> gecer' ve 'eski-stil chkl -> gecer' satirlari korunur; kaldirilirsa test GERCEK aktivasyonu da reddeder.

---

# GEÇMİŞ BACKFILL (2026-07-08 → 07-31) — infra-expert arkeolojisi 2026-08-01

> Kanıt: DEV_CORE git-log (--follow, 40+ dosya) + 30 commit + removed-controls + 23 ADR + lessons.
> PR sütununda **sha KANONİKTİR** (repo taşınırken PR-no sıfırlandı, #1/#2/#3 çakışır).
> Kapsam-sınırı: DEV_CORE geçmişi f85e3fd (2026-07-08) ile başlar; daha eski evrim proje
> reposunda (hook doğuşu 2026-06-02 660a5bbf) — repo-sınırı --follow'u kırar, o dönem AYRI tur.
> Satır: tarih · değişiklik · NEDEN · NASIL-test · sha/PR. (Tam ayrıntı: infra-expert raporu,
> transcript 2026-08-01; test-reçeteleri aşağıdaki TEST-REÇETELERİ bölümünde.)
| 2026-08-01 | adtget fixture'ina MCP-SDK KOPRUSU (CI pip'ine `mcp` EKLENMEDI — denendi, geri alindi) | Fixture MCP tool KATMANINI gercekten import edip davranisini olcuyor (stub'li istemci); AST ile okunamaz cunku olculen sey CALISMA-ZAMANI sinifi. Once `pip install mcp` denendi: gelen paket `mcp.server.fastmcp` SAGLAMADI (yanlis/eski dagitim) -> ikinci CI kirmizisi. Cozum: `atom -> _app -> FastMCP` zincirini karsilayan asgari SAHTE modul, YALNIZ SDK eksikse kurulur; gercek SDK varsa dokunulmaz. Sinir yoruma yazildi: kopru FastMCP davranisini test ETMEZ, onu MCP import-smoke yakalar | Iki eksende dogrulandi: yerelde gercek SDK ile 6/6, `mcp` import'u BLOKLANMIS CI-simulasyonunda da 6/6 | tests/fixtures/adtget_yokluk_kaniti | core#82 |

## pre_tool_guard.py
- 2026-07-08 · 4-katman doğuş + proje-kökü env-first · junction __file__ daima DEV_CORE'a çözülüyordu (yanlış ağaç korunuyordu) · 9-senaryo sentetik · 1ae10b1
- 2026-07-08 · KESİN-YASAKLAR damga hard-blok · @import junction kırılınca talimat-yasaklar sessizce düşüyordu · _PROVA: damga-sil→FAIL, tamper→FAIL, push-eş=0 · a6142d8 core#3
- 2026-07-09 · fiil→hedef-tabanlı + matcher +PowerShell/MCP + fail-open→fail-closed(2) · guard TERSİNE çalışıyordu (kök okunamıyor ama YAZILABİLİYORDU); PS matcher'da yoktu; return-1 blok değildir · canlı A/B + ix_doctor + MultiEdit-kanıt · 0d0e28d core#4
- 2026-07-09 · _canon_path çoklu-slash · project.yaml çift-backslash unescape edilmiyordu → R10 tamamen ölüydü · freeze_probe 5/5 RED + 4/4 zararsız · 2957057
- 2026-07-09 · fiil araması tırnak-dışı segmentte · tırnak-içi VERİ komut sanılıyordu · test-kaydı yok (tarihsel) · 7d78a49 core#5
- 2026-07-10 · **13→8 kural** (R9/R10/sızıntı/applies_to SİL; 789→450 satır) · merdiven ilkesi: runtime-guard yalnız geri-alınamaz+sessiz için; silinenlerin statik ikizi vardı ya da hiç korumuyordu · YENİ META-GATE guard_conformance + Z4 öz-test + 2-proje matrisi · ce64d1d core#7 · ⚠GEVŞETME(tarihsel)
- 2026-07-10 · Kural-9: repo-değiştiren her gh'de hedef AÇIK · hedefsiz gh cwd'den çıkarır + core junction → private→public yayın (geri-alınamaz, gh başarı döner) · meta-gate 2× yakaladı; 7/7 çapa; konformans 5+6 · 7b4bcec core#13
- 2026-07-10 · Kural-10 KALDIRILDI + docs_mirror silindi · kullanıcı: "kural kuralı mı doğuruyor?" — kök gereksiz-çoğaltmaydı; kopya kalkınca zincir çöktü → GATE-MORATORYUMU doğdu · guard+konformans+precommit-all · c5d59a5 core#15 · ⚠GEVŞETME(tarihsel)
- 2026-07-28 · commit-MESAJI sızıntı-gate'i · PR-gövdesi yakalandı ama aynı ad commit-mesajındaydı ve push'luydu; iki koruma da bu yolu görmüyordu · test_commit_message_leak_gate (CI) · 8ac1dd5 core#47
- 2026-07-30 · _win_yol POSIX-cd normalizasyonu · cd /c/... çözülemiyor → fail-closed → PRIVATE repo PUBLIC sanılıp meşru commit BLOKLANDI (FP bypass-alışkanlığı doğurur) · 6-vaka + LIVE-gated + MUTASYON-testi (fix bozuldu→FAIL) + konformans-69 · 08bb6e6 core#57

## session_start + behavior_manifest + config_change_guard
- 2026-07-08 · yeniden-yazım: D25 4-junction TEK-TEK + F2 manifest + O3 throttle + YENİ manifest/config-guard · toplu doğrulama tek kırığı gizliyordu; seans-içi davranış-yüzeyi sessiz değişebiliyordu · 6-senaryo smoke · 6d88d84
- 2026-07-10 · ham-hash → anlamlı-imza (_comment*/CRLF hariç; bozuk-imza SESSİZ-GEÇMEZ) · birebir-aynı kablolamada tek yorum-anahtarı HER OTURUM sahte-SAPMA bağırtıyordu (FP → gerçek drift görülmez) · 6 negatif: yorum→AYNI · CRLF→AYNI · hook-sil→FARKLI · matcher→FARKLI · bozuk→"?" · sıra→AYNI · 02922c3 core#17 · ⚠GEVŞETME(tarihsel; kapsam-kaybı 6-testle SIFIR ölçüldü)

## pull_before_edit.py
- 2026-07-09 · erp-hardcode → source_root parametrik · K12 rename sonrası hook HİÇ tetiklenmiyordu (ADR-0016 ölüydü) · 4/4 fixture · 2957057
- 2026-07-09 · proje-kökü project_config'e · damga DEV_CORE'a yazılıyordu (projeler-arası tazelik-sızıntısı); git-status yanlış repoya → git_dirty daima False (WIP-muafiyeti ölü) · smoke: bayat→exit2, damga proje-kökünde · d2d326d
- 2026-07-29 · blok-mesajı yolu scripts/ → core/scripts/ · projeden bakınca script core/ altında; komutu kopyalayan ajan "dosya yok" alıyordu · sentetik payload (printf; echo ters-eğik-çizgiyi bozup fail-safe-0 tuzağı üretti — kayda geçti) · 5d6b90d core#51

## skill_injector + sap_worktype_hint + intake_triage + itg_backstop
- 2026-07-09 · otomatik-event filtresi · task-notification'da yanlış tetikleniyordu · notif-sessiz + gerçek-çalışır · 2957057
- 2026-07-10 · keşif NATIVE'e, enforcement TOOL-ADINA: 12-regex söküldü + YENİ deterministik sap_worktype_hint · regex kırılgandı ("CDS view yarat" kaçıyor, "public transport" yanlış-tetikliyor); ekosistem kanıtı: herkes description-native · 8/8 + 8/9 (9. test-beklenti hatası) · 6ceaf62 core#9 · ⚠GEVŞETME(tarihsel; yüzeyi native+deterministik devraldı)
- 2026-07-08 · ITG çekirdeği (ADR-0022) + s2-signoff zinciri · geliştirme-alım katmanı yoktu · doğuş test-kaydı yok / signoff coverage-53 + 4-smoke · fb83359 + f3b5e3d
- 2026-07-10 · diyakritik-katlama + 3-katman (native-skill + marker + SAP-tool-backstop) · ASCII "gelistir" kaçıyordu; keyword-dışı 5/5 GERÇEK talep ITG'yi hiç tetiklemiyordu · 6/6 + A/B/C marker-koordinasyon · 6ceaf62 + f77b1c6 core#9-10

## instructions_loaded_log + claude/rules (L1b)
- 2026-07-10 · globs:→paths: + logger gerçek-şema onarımı (SEMA-DEĞİŞTİ dalı) · Claude Code YALNIZ paths okur; globs sessizce koşulsuz-yükleme demekti; ölçüm-aleti de kördü ("? ?") · gözlem-kanıtı: asla-eşleşmez-glob'lu README bile yükleniyordu; AÇIK-KALEM: paths-tembel-yükleme hâlâ görülmedi (#17204) · 10e2daa core#16
- 2026-07-31 · atomik append (O_APPEND tek write) · eşzamanlı hook'lar satır bölüyordu (150'de 3 malformed) · 10-eşzamanlı → 10 tam satır · 31cef4a core#64

## watchdog + pre_compact
- 2026-07-08 · generic-probes + hardcoded-host söküm + pre_compact systemMessage · probes yokken SAHTE-ALERT; additionalContext PreCompact'ta şema-geçersiz (canlı hatayla kanıtlı) · sentetik üçlü · c5d02bc
- 2026-07-09 · level→edge-triggered (alerted bayrağı + recovery-reset) · kopuklukta her tur modal-spam · aynı dizide 1 alert · 2957057

## run_all_validators + project_config + validator ailesi
- 2026-07-08 · project_config doğuşu (K12 tek-okuma-noktası) + run_all yeniden-yazım + check_core_not_committed + 41 dosya ERP→SOURCE_ROOT · hardcode her yerde ayrı okunuyordu; K12 rename sessizce kırdı · CORE-modu SMOKE + compileall-0 · 25cd694
- 2026-07-09 · 11 validator project_config API'sine + YENİ check_project_root_resolution (AST) · SINIF-HATA: junction'da __file__→DEV_CORE; dizin-yok → 0-dosya → GATE YEŞİL YANAR (bilerek-konan type_c ihlaline "OK" dedi) · 5-ihlal-deseni + 0-FP + gate kendi doğuş-bug'ını yakaladı; probe'lar 0→1 ×3 · d2d326d
- 2026-07-09 · utils/console tek-kaynak + 21 dosya + C-ENC-01 · cp1252'de non-ASCII ÇÖKER (exit-1 = gerçek FAIL'den ayrılmaz); aynı gün 3 script çöktü, biri validator'dı ve negatif-testi hiçbir şey kanıtlamadı · negatif: korumayı kaldır→ADIYLA FAIL · 7d78a49 core#5
- 2026-07-10 · C-MEM-01 + C-REG-01 + C-TPL-01 gate'leri · MEMORY-bütçesi ölçülmüyordu; şablon 3-hook gerideydi (init_project GERİDE proje üretirdi) · 3/3 + negatif · facd86a + 794bec6 core#11-12
- 2026-07-10 · core_not_committed'a SIR-KİLİDİ (.conn_adt/.csrf/.local.yaml; TAM-SATIR + index-yok) · K3: üç dosya AYLARCA commit'lendi, hiçbir katman uyarmadı; alt-dizge kontrolü yanlış-güvence olurdu · 4 kirli senaryo (alt-dizge-tuzağı C yakalandı) · eddc9be core#18
- 2026-07-28 · check_cds_srvd_comment_syntax (BE-58/61) · .cds'te ABAP-yorum → SAP kaynağı HİÇ ALMAZ ama "uploaded+activated" der; .srvd'de sessizce SİLER; BEŞ katman yeşil verdi — yakalayan tek şey READBACK · PATTERN#14 devreye-alma: 25 ihlal → temizlik → taban-0 → HARD · 3fc2451 core#45
- 2026-07-29 · check_bdef_backtick (BİLİNÇLİ-DAR: yalnız .bdef) · backtick .bdef'te ÇOĞALIYOR (repo-2 iken canlı-8); .abap DIŞARIDA (geçerli literal = YP olur); .cds ölçülmedi (kanıtsız genişletme yok) · yan-bulgu: reviewer bdef için hiç koşmuyor (→ 0f9bbf0) · 0f2c6d5 core#54
- 2026-07-31 · bdef+cds_srvd rglob→prune-walk · aynı-215-dosya 1,38→0,06sn; ⚠SINIF-TEKRARI: aynı ders 06-24'te proje-reposunda 5 validator'da alınmıştı — bu ikisi 5 hafta SONRA yazılıp deseni geri getirdi (ders dosyalara kodlanmış, sınıfa değil) · N: kirli-.bdef hâlâ exit-1 · 9939063
- 2026-07-31 · ThreadPool paralellik + AMDP tek-artifact · quick 8,4→2,5sn; AMDP DÜRÜST-NOT: kazanç ~0, rapor-iddiası ölçümsüz tahminmiş · 3-koşum bayt-eş; WORKERS=1 seri=paralel · 9608f9d + cd4d2b8

## run_review.py (ADR-0006 zinciri)
- 2026-07-29 · OBJECT_TYPE_TO_TASK'a class/bdef/srvd + eş-anlamlılar · harita yalnız ddls/tabl taşıyordu → task=None → zincir SESSİZCE atlandı; class_push 6-validator/2-BLOCKER ile yazılmış, HİÇ otomatik koşmamıştı ("dokümante ama kablosuz kural = kuralsız") · blast ÖNCEDEN: 5-sınıf 0-BLOCKER; 20-bdef → 1 GERÇEK BLOCKER; kirli→BLOCKER/temiz→PASS; kullanıcı-onayı 07-29 · 0f9bbf0 core#55

## mcp_servers/sap_adt
- 2026-07-09 · object_exists + where_used yoksa-Error (count anahtarı DÖNMEZ) · SAP var-olmayan objeye HTTP-200+BOŞ-LİSTE döner → "tüketicisiz" ile "yok" AYNIYDI; orphan-sweep komşuyu yanlış silebilirdi · canlı-5/5 (varlık-sondası=get_object_structure) · PATTERN#11 · 723e6fa
- 2026-07-10 · profil-bazlı tool-blok (fail-closed: yalnız ping) · CLAUDE.core'un yazıp KODLAMADIĞI kural; tek matris-kanıtlı daraltma transport∉btp_abap · s4_private-19 / btp-18 / profilsiz-1 · facd86a core#11
- 2026-07-12 · adt_msgclass_read + 11 read-only tool · msag okunamıyordu → ajan inline-MESSAGE-literal fallback'ine düşüyordu; sql SELECT-only+PII guard · canlı-doğrulamalar (T100 WHERE-5/COUNT-54; UPDATE-red; .v2+xml→406 "sunucudan doğrula" dersi) · fe21ae8 + 3a3a3de core#24-25
- 2026-07-13 · create_structure deterministik ham-PUT + KOŞULSUZ içerik-verify · create-POST blue:source FLAKY (bazen shell bırakır, "activated" maskeler); boş dataType sessizce CHAR(1) · 21-vaka offline; DÜRÜST-BOŞLUK: canlı-negatif ERTELENDİ (single-writer yarışı) · e2fcef2 core#31
- 2026-07-28 · search tip-filtresi İSTEMCİ→SUNUCU + kırpma-uyarısı; push readback-farkı=BAŞARISIZLIK · search(TABL)→count:0 "yok"tan ayrılmıyordu (alfabetik-kırpma; "geniş-dene" sorunu BÜYÜTÜYORDU → kaldırıldı); readback-farkı yalnız WARNING+success=True idi · 2 CI-testi · 8ac1dd5 core#47
- 2026-07-29 · adt_unit_run options-ÖNEKSİZ + parser-ns; inactive_objects TADIR-DELFLAG çaprazı · unit: daima-0-test, SE24 kontrol-grubu 9 buldu → ARAÇ bozuktu (öneksiz→9; İKİ bug birlikte şart) · inactive: 2 "bekleyen" obje SİLİNMİŞTİ, neredeyse TADIR silme-kayıtları temizlenecekti (GERÇEK-HASAR; kullanıcı 2 müdahaleyle durdurdu); ioc:deleted alanı YETMİYOR · canlı iki-yön + hata-yolu tadir_check=FAILED · c5036b0 + 95a41de core#53,56
- 2026-07-31 · CSRF header-enjeksiyonu (çağıranın dict'i güncellenir) · classrun sağlam sınıfa "does not implement" dedi; 14+ çağıran header'ı retry-ÖNCESİ kuruyor → soğuk-session token'sız; "taze class adı" hipotezi YANLIŞTI · test_csrf_header_injection (CI) · 2f6ae4e core#63

## claude_overlay + team_setup + init_project
- 2026-07-09 · agents-local overlay (opt-in) + REGRESYON-FIX (damga frontmatter-SONRA + LF + FORMAT-GATE) · junction'da proje-özel agent TANIMLANAMIYORDU (genericize → ajan tahmine itiliyordu); ilk sürümde damga BAŞA girdi → 6/6 agent yüklenemedi — "SAYI ≠ YÜKLENEBİLİRLİK" · negatifler: core-değişti→WARN, yeni-agent→EKSİK, yorum-öne→BOZUK, CRLF→FAIL · 7d78a49 + e983eb1 core#5-6
- 2026-07-10 · şablon-zincirinde 7 boşluk + guard.yml→reusable-workflow · template SIFIRDAN üretilip PROVA edildi: 3-gün-geride proje çıkıyordu (sır-commit'li, kontrolsüz); guard.yml kopyası yapısal bayatlıyordu · canlı-leak exit-1; C-TPL-01 doğdu · 794bec6 + eddc9be core#12,18
- 2026-07-26 · init_project şablonundan frozen_readonly_paths ÇIKARILDI · silinen R9/R10 hâlâ 10 dokümanda "aktif" ilan ediliyordu — koruma-SANISI, olmadığını bilmekten tehlikeli · sentetik: donmuş-köke Write→exit-0 (SERBEST) + POZİTİF-KONTROL hedefsiz-gh→exit-2 (yöntem sağlam) · 15e314c core#37

## git-hooks/core_precommit
- 2026-07-08 · doğuş: genericize+link+applies_to (staged) + hooksPath · public'e kimlik-sızma · 3-yol sentetik · a583575
- 2026-07-10 · genericize FAIL-CLOSED + Z-obje/D_-user desenleri + gh-yan-kapılar + tek-kaynak genericize_common · SON-KAPI KÖRDÜ: blocklist .git'te yaşar ve KLONLANMAZ → CI müşteri/sistem/kişi adına tamamen kördü (canlı ölçüldü: üçü de exit-0 geçti) · D1-D5 12/12 + gh 13/13; HEAD'deki gerçek izler temizlendi (git-geçmişi bilinçli bırakıldı) · facd86a core#11
- 2026-07-31 · adım-2 (index --check) kaldırıldı · run_all C-IDX-01 aynı işi yapıyor (çoğaltma-kaldırma) · removed-controls kaydı · 31cef4a core#64 · ⚠GEVŞETME(tarihsel; ikiz-katman durur)

## inspector.py
- 2026-07-10 · v1 doğuş (rapor-only; canary'li) + HEARTBEAT-REDDİ (bilinçli) · arıza-sınıfı "kod doğru ama HİÇ ÇALIŞMADI" — diskte hiçbir şey yanlış görünmüyordu; "guard fiilen koştu mu" ÖLÇÜLEMEZ bırakıldı (heartbeat 16-hook geçiş-noktasını sessiz-izin-verir'e çevirebilirdi — kötü takas) · canary 5/5; ilk gerçek koşu 3 bulgu (B5=FP çıktı → iddia yeniden yazıldı) · aa6b5a0 core#20

## tests/ + scripts/tests/
- 2026-07-28..30 · 5 regresyon-testi CI'a (guard/csrf/readback/leak/search) · her biri YAŞANMIŞ canlı vakanın yeniden-koşulabilir hali (başlıklarında vaka-tarihi+kök yazılı) · core-ci.yml adımları · 8ac1dd5, 2f6ae4e, 08bb6e6

## ⚠ LİDER-DÜZELTMELERİ (infra-expert C-bölümünün yakaladıkları — dürüstlük kaydı)
- C1: brifing-hatam — "06-14..23 = lessons#10" eşlemesi YANLIŞTI (#10 = junction-__file__, 07-09).
- C4: bugünkü bazı kayıtların PR-sütunu yanlış repoyu gösteriyordu (gerçek sha'lar: 9939063 / 9608f9d / 3c9999f; hook_shim proje-tarafı 96695a8b) → sha-kanonik ilkesi benimsendi.
- C5: SINIF-AÇIK — rglob→walk dersi dosyalara kodlanmış, sınıfa değil; yeni validator deseni tekrarlayabilir → infra-findings'e [ÖNERİ] yazıldı (gate ancak moratoryum-5-şartla).
- Kanıt-sınırı: guardrails.py / data_guard.py / run_ui_smoke.py yalnız doğuş-commit'i taşıyor (bileşen-özel gerekçe YOK — satır yazılmadı); 2026-07-08 öncesi dönem proje-reposunda (ayrı tur).
