#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_fixture_tests.py — bozuk-girdi (negatif-test) korpuslarinin TEK giris noktasi.

BOLUM 1 — validator bad/good fixture ciftleri (G1/T3.6).
BOLUM 2 — pre_tool_guard PAYLOAD korpusu (2026-08-01 bug-avi AV-16/17/18/18b/21;
          detay + mutasyon-testi: tests/run_guard_fixture_tests.py).
OZEL    — kendi kosucusunu tasiyan fixture'lar (tier_fail_closed, changelog_gate)
          ayni tabloya raporlanir.
Hepsi CI'da bu tek komutla kosar (core-ci.yml "Validator fixture testleri").

Her validator icin tests/fixtures/<validator>/{bad,good}/ altinda gercekci bir mini
"proje koku" bulunur (SOURCE_CODES/... veya docs/...). Bu dizin CLAUDE_PROJECT_DIR
olarak validator subprocess'ine verilir; validator boylece kendi normal (argumansiz,
repo-geneli tarama) modunda calisir:

  - bad/  -> validator FAIL vermeli (exit != 0)
  - good/ -> validator PASS vermeli (exit == 0)

Herhangi bir cift beklenenin tersini verirse (ya da fixture eksikse) NIHAI exit 1.

OZEL_TESTLER (2026-08-01, bug-avi): bazi infra kusurlari "bad/good proje dizini" seklinde
ifade EDILEMEZ (ornegin tier cozumleme = kod-yolu; changelog gate = gercek git reposu).
Bunlar `tests/fixtures/<ad>/run.py` olarak yasar, kendi P/N senaryolarini icinde tasir ve
exit 0/1 doner. Burada ayni tabloya raporlanirlar (tek kosucu = CI'da tek adim).

Kullanim:
    python tests/run_fixture_tests.py                         # TAM suite (CI + lider)
    python tests/run_fixture_tests.py --degisen <dosya> ...    # ISE-OZEL secim (infra-expert)
    python tests/run_fixture_tests.py --degisen <dosya> --listele   # kuru kosum (ne kosardim)
Cikis: 0 -- hepsi beklendigi gibi, 1 -- en az bir sapma.

`--degisen` FAIL-CLOSED'dir: verilen dosyalardan BIRI bile haritada yoksa TAM suite
kosar (gorunur satirla). Sozlesme + gerekce: asagidaki HARITA blogu.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
VALIDATORS_DIR = HERE.parent / "scripts" / "validators"

# G1/T3.6 ilk-10: hepsi CLAUDE_PROJECT_DIR + argumansiz repo-geneli tarama modunu
# destekler (proje_root()/source_dir() -> env). ATLANDI: check_rap_byassoc_keys_only
# (kod her zaman `return 0` -- SOFT, fixture'la FAIL uretilemez) ve check_console_utf8
# (CORE = Path(__file__).resolve().parents[2] hard-code -- kendi scripts/ agacini tarar,
# CLAUDE_PROJECT_DIR/cwd'den BAGIMSIZ -- fixture ile izole edilemez).
VALIDATORS = [
    "check_bdef_backtick",
    "check_cds_srvd_comment_syntax",
    "check_list_view_grid",
    "check_ui5_freestyle_traps",
    "check_filter_search_pattern",
    "check_decimal_write_to",
    "check_method_param_type_c",
    "check_no_rap_commit",
    "check_amdp_comment_apostrophe",
    "check_kd_no_raw_mermaid",
]

# Kendi kosucusunu tasiyan fixture'lar: tests/fixtures/<ad>/run.py (exit 0 = tum senaryolar OK).
# Her biri kendi icinde HEM bozuk->BLOK HEM temiz->SERBEST senaryolarini kosar.
OZEL_TESTLER = [
    ("tier_fail_closed", "ADR 0010 tier: fail-closed + tam-anahtar (KAYIT-1)"),
    ("changelog_gate", "pre-commit 4. kontrol: infra-changelog gate (KAYIT-2)"),
    ("instruction_budget", "C-BUD-01: talimat-butcesi warn-first (soyma+tekrar, 7 vektor)"),
    ("sir_gate", "pre-commit 5. kontrol: sir-dosyasi (canli ihlalle bulundu)"),
    ("reviewer_tip_kapsam", "ADR 0006 pre-flight: push-tipi <-> reviewer haritasi senkronu"),
    ("conn_cift_anahtar", "ADR 0010: cift-anahtarli .conn_adt (guard <-> baglanti ayrismasi)"),
    ("adtget_yokluk_kaniti", "BULUNAMADI != YOK: adt_get DDIC dalinda hata <-> yokluk"),
    ("aktivasyon_sahte_ok", "HTTP hatasi da KANIT DEGIL: aktivasyon sahte-OK'i"),
    ("worktree_blocklist", "kimlik blocklist'i worktree'de de bulunmali (commit-blogu)"),
    ("negatif_test_harness", "hook parse-fail gorunurlugu: exit 0 KORUNUR + stderr'de not (bozuk girdi ARTIK ayirt edilebilir)"),
    ("tembel_desen", "sizinti deseni TEMBEL kurulur: hiz kazanci korumayi OLU'ye cevirmiyor"),
    ("infra_write_guard", "infra yuzeyine ANA-OTURUM yazimi BLOK; infra-expert MUAF (kimlik olculdu)"),
    ("abaplint_failopen", "check_abaplint: OLCEMEDIM != TEMIZ (ozet satiri zorunlu kanit, 9 senaryo)"),
    ("prior_art_kb01", "KB-01 ONCE-ARA tur-ici: brifingde adi gecen script'in recetesi SPAWN aninda yuzeye cikar (metin-izi DEGIL arama)"),
    # ⚠ 2026-08-01: `adtget_yokluk_kaniti` bir ara bu listede IKI KEZ yaziliydi (PR birlesme
    # artigi) -> ayni fixture iki kez kosuyor ve TOPLAM sayiyi sisiriyordu. "N/N PASS"
    # sayisina guvenmenin bedeli: sayaci degil SATIRLARI oku.
    # ⛔ 2026-08-10: yukaridaki not GECMIS ZAMANLA yazilmisti ama MUKERRER SATIR DURUYORDU
    # (dersin kendi fix'i eksik kalmis; yorum "duzelttik" demiyor, "olmustu" diyor ve
    # okuyan onu duzelmis saniyor). Satir bugun SILINDI. Artik bir korpus vektoru bunu
    # bekliyor: tests/fixtures/sessiz_olumsuzlama_2026_08_10 E1 -> mukerrer kayit = FAIL.
    ("dogrulama_kosamadi", "DOGRULAMA KOSAMADI != DOGRULANDI (5 kayit, tek kok)"),
    ("veri_yetki_guardlari", "ADR 0011 PII normalizasyonu + guard'siz mutasyon tool'u (K-1/2/3)"),
    # 2026-08-01 kuyruk-turu (scripts/ + run_review):
    ("reviewer_skip_sozlesmesi", "run_review SKIP sozlesmesi: cokme + sahte-PASS (S1+S2)"),
    ("core_index_kapsam", "CORE-INDEX governance duz dosyalari GORUYOR mu (S3)"),
    ("proje_slug_tek_kaynak", "Claude Code proje-slug'i: tek sozlesme, tek kaynak (S4)"),
    ("git_sorgu_sessiz_bos", "deploy_ui --all-changed: git arizasi != 'degisiklik yok' (S5)"),
    ("conn_yazici_encoding", ".conn_adt YAZICI tarafi acik encoding tasir (S6)"),
    # 2026-08-01 kuyruk-turu (validator ailesi, V1-V6):
    ("cds_curr_satir_yorumu", "CURR/QUAN: satir-sonu // yorumu alani/degeri gizliyordu (V1)"),
    ("cds_curr_kaynak_tipi",
     "CURR/QUAN kaynak-tipi: 'define root view entity' alt-diziye takilmiyordu -> rc=0 SESSIZ (V2)"),
    ("populate_tables_unit_kind",
     "B-13: CSV 'type' kolonu ABAP tipi saniliyordu -> CURR dali ULASILAMAZ olu koddu"),
    ("paket_uzanti_kapsami", "paket naming + paket-siniri: .bdef/.srvd allow-list'te YOKTU (V2)"),
    ("itg_alan_dolulugu", "ITG S2: bos sablon + [x] BLOCKER gate'ini geciyordu (V3)"),
    ("gitignore_tam_satir", "core-sizinti kilidi: yorumlu/negatif satir 'kilit var' saniliyordu (V4)"),
    ("proje_koku_varyantlari", "__file__-koku: glob/joinpath/str-concat/transitive kaciyordu (V5)"),
    ("ui5_t1_tirnak_sinifi", "UI5 T1: template-literal `_X` tirnak sinifindan kaciyordu (V6)"),
    # 2026-08-01 amend-FP (kullanici-onayli GEVSETME — kiyas birimi commit -> dal):
    ("changelog_amend", "INFRA-CHANGELOG gate: amend/cok-commit dalinda FP; taze dalda birebir-eski"),
    # 2026-08-09 DDIC okuma-yolu (table/structure `/source/main` VAR; diger uc tipte YOK):
    ("ddic_okuma_yolu", "adt_get + sap_sync_pull: DDIC tipi basina dogru uc (XML vs DDL)"),
    # 2026-08-09 lock yaniti: NoModification -> acik hata; BOS/eksik/taninmayan -> AYNEN eski:
    ("lock_modification_support", "lock MODIFICATION_SUPPORT: 423'un sinyali (fail-safe)"),
    # 2026-08-10 arac-kusurlari turu (7 kusur, 2 kok):
    ("sessiz_olumsuzlama_2026_08_10",
     "aracin false/0'i gormedigi katman icin 'hayir' DEGIL (transport/lock/deploy_ui)"),
    ("class_include_push",
     "sinif alt-include'u (ccau/ccimp): POST != PUT ve 201 != 'yazildi'"),
    # 2026-08-10 ui-smoke proje-koku (arac + gate ayni sinifin iki yuzu):
    ("conn_adt_proje_koku",
     ".conn_adt PROJE kokundedir: run_ui_smoke kok cozumlemesi + CORE-01 dedektoru"),
    # 2026-08-12 talimat-bakim turu (K2): C-MEM-01 olcum modeli + SKIP gorunurlugu:
    ("memory_yukleme_butcesi",
     "C-MEM-01: butce HAM bayti degil YUKLENEN govdeyi olcer (+ KOSMADI != TEMIZ)"),
    # 2026-08-13 guard CI cift-tetik: dalsiz `push:` + `pull_request` AYNI SHA'yi iki kez
    # dogruluyordu (PR basina 3 job israf). Fixture sablonun DOSYASINI okur (kablolama).
    ("workflow_tetik_dupe",
     "guard tetigi: dalsiz push + pull_request = ayni SHA iki kosuda (sablon capasi)"),
    # 2026-08-13 overlay ezme-kapisinin KIYAS TABANI: kopya-simdi <-> en son URETILEN
    # (manifest `uretilen_hash`). Eski taban "bugun uretilecek" idi -> core her degistiginde
    # elle-duzeltme yokken de kapi kapaniyordu (kurt masali). Iki mutasyon modu tasir:
    #   --mutasyon (taban SHA) -> P vektorleri duser · --mutasyon-gevsek -> N capalari duser.
    ("overlay_kiyas_tabani",
     "claude_overlay T2.5: 'core degisti' ile 'kopya elle duzeltildi' ayrisir"),
    # 2026-08-13 ikinci yari: kiyas tabani "fark yok" diyebildigi ICIN senkron artik
    # kullanici komutuna bagli degil -- session_start her acilista otomatik tazeler,
    # fark DOLU iken dokunmaz ve her iki dal da GORUNUR satir basar (sessiz tazeleme yok).
    #   --mutasyon (taban SHA, oto_tazele yok) -> P duser · --mutasyon-gevsek -> N capalari duser.
    ("overlay_oto_tazeleme",
     "overlay bayatligi komutsuz kapanir; elle duzeltme varken DOKUNMAZ"),
    # 2026-08-13 B0 is-ozel secim modu: `--degisen` haritasinin KENDI korpusu
    # (secim MANTIGI olculur — suite gercekten kosulmaz; kuru-kosum `--listele`).
    ("b0_secim",
     "--degisen: dogru alt-kume, birlesim, bilinmeyen->TAM (fail-closed), harita-tamlik"),
    # 2026-08-14: patinaj-kesici hook'un BASH yuzeyi. Hook mcp__sap-adt__.* matcher'ina
    # bagliydi; 12 push denemesi Bash'ten kostu ve hook HIC atesle(n)medi. Iki degismez:
    # ATESLEME (SAP komutu + hata imzasi) ve SESSIZLIK (diger her sey).
    ("post_tool_failure_bash",
     "Bash yuzeyi: iki kapi (komut imzasi + hata imzasi); FP capalari + MCP dali regresyonu"),
    # 2026-08-17: FS dokuman-standardi UCLUSU (validator + post_validate doc-fs dali +
    # denklik araci). Iki yon ayni korpusta: YAKALAMA (analiz-gunlugu izi) ve SESSIZLIK
    # (belgenin kendi kimlik satiri / mesru hata kodu / katman-2 dosyasi). FP capalari
    # olculmus bir vakadan gelir: gate ilk halinde 21 dokumanin 16'sini kirli gosteriyordu.
    ("fs_docstd",
     "DOC-FS-05/06/07 uclusu: yakalama + FP capalari + hook kablolamasi + komsu dal regresyonu"),
    # 2026-08-18: paylasilan ABAP uretecinin imzasi <-> kilavuzu. Iki yon ayni korpusta:
    # YAKALAMA (EKSIK/HAYALET/OLCULEMEDI) ve SESSIZLIK (blok DISI API token'lari, markdown
    # bicim varyantlari, farkli imza sekilleri). "Bakamadim" ile "temiz" AYRI exit'e duser.
    ("fm_imza_doc_sync",
     "CLC-SCR7: FM imzasi <-> kilavuz senkronu; 3 durum ayrimi + FP capalari (11 vektor)"),
    # 2026-08-19 ADT teshis gorunurlugu (iki kalem, tek tema: SAP'nin SEBEBI cagirana ulasmali)
    ("retry_500_govde",
     "retry adapter'i SAP'nin 500 GOVDESINI yutuyordu (429/502/503/504 tekrar KORUNDU)"),
    ("sorgu_basarisizligi_gorunur",
     "adt_sql_query/adt_table_read: alt katman None -> ok:false (ok:true + 0 satir = sahte yesil)"),
]


# =============================================================================
# DOSYA → FIXTURE HARİTASI (`--degisen` iş-özel seçim modu, 2026-08-13)
#
# NEDEN: süite 12 → 112+ kontrole büyüdü (ölçüldü 2026-08-13: TAM koşum 169,7 sn /
# 113 vektör). İnfra-expert bir fix-seansında B0'ı 2× koşuyordu (~6 dk sabit vergi),
# üstelik CI aynı süiteyi zaten TAM koşuyor. Bu mod **ARA adımların** vergisini düşürür;
# sigortayı KALDIRMAZ: lider merge-öncesi 1× TAM + CI TAM (bkz.
# `playbook/howto-infra-fix-proseduru.md` ADIM-3 · `governance/infra-test-recipes.md` B0).
#
# SÖZLEŞME (fail-closed):
#   · Harita AÇIK sabittir — fixture docstring'lerinden ÜRETİLMEZ. (Üretilen harita
#     bayatladığında bayatlığı görünmez olur; açık tablo en azından okunabilir.)
#   · Verilen dosyalardan BİRİ bile haritada yoksa → TAM süite + GÖRÜNÜR satır.
#     Sessiz daraltma ASLA.
#   · Birden çok desen eşleşirse BİRLEŞİM koşulur (yön daima genişletme).
#   · TAM koşumda `harita_tamlik()` bir vektör olarak koşar: haritada hiç anılmayan
#     fixture varsa süite FAIL verir (yeni fixture + güncellenmemiş harita = sessizce
#     kapsam dışı kalmasın). Yeni gate DEĞİL — mevcut süitenin içinde bir vektör.
#
# BİRİM KİMLİKLERİ: `V:<validator>` (bölüm-1 bad/good çifti) · `O:<fixture>`
# (OZEL_TESTLER) · `R:<AV-nn>` (bölüm-2 regresyon) · `G` (bölüm-3 guard korpusu) ·
# `TAM` (özel: tam süite).
#
# ⚠ Harita "hangi fixture bu dosyaya BAKIYOR" sorusunun cevabıdır — kanıtı fixture'ın
# kendi kaynağıdır (import/`spec_from_file_location`/subprocess hedefi), docstring'i
# değil. Yeni bir fixture yazarken buraya SATIR EKLE; unutursan TAM koşum FAIL verir.
# =============================================================================
TAM = "TAM"

HARITA: list[tuple[str, tuple[str, ...], str]] = [
    # ── koşucunun kendisi ───────────────────────────────────────────────────
    ("tests/run_fixture_tests.py", (TAM, "O:b0_secim"),
     "seçim mantığı burada yaşar; koşucu değişince kıyas tabanı TAM olmalı"),
    ("tests/run_guard_fixture_tests.py", ("G",), "guard payload korpusunun koşucusu"),
    ("scripts/hooks/post_tool_failure.py", ("O:post_tool_failure_bash",),
     "patinaj-kesici hook: ATEŞLEME + SESSİZLİK değişmezleri (Bash + MCP dalları)"),
    ("scripts/hooks/post_validate.py", ("O:fs_docstd", "O:negatif_test_harness"),
     "doc-fs dalı (OKU-işaretçisi + gate özeti) + komşu dalların regresyonu + parse-fail sözleşmesi"),
    ("scripts/hooks/watchdog_launch.py",
     ("O:prior_art_kb01", "O:negatif_test_harness"),
     "KB-01 prior-art ekseni + brifing-lint regresyonu + parse-fail sözleşmesi"),
    ("scripts/validators/check_abaplint.py", ("O:abaplint_failopen",),
     "fail-open kilidi: 'ölçemedim' ile 'temiz' AYNI çıkışa düşmemeli (özet satırı zorunlu kanıt)"),
    ("scripts/abaplint/abaplint.json", ("O:abaplint_failopen",),
     "config kapsamı değişirse 'M file(s) analyzed' ölçütü de etkilenir"),

    # ── bölüm-1 validator bad/good çiftleri ─────────────────────────────────
    ("scripts/validators/check_bdef_backtick.py", ("V:check_bdef_backtick",), "G1 çifti"),
    ("scripts/validators/check_cds_srvd_comment_syntax.py",
     ("V:check_cds_srvd_comment_syntax",), "G1 çifti"),
    ("scripts/validators/check_list_view_grid.py", ("V:check_list_view_grid",), "G1 çifti"),
    ("scripts/validators/check_ui5_freestyle_traps.py",
     ("V:check_ui5_freestyle_traps", "O:ui5_t1_tirnak_sinifi"),
     "G1 çifti + T1 tırnak-sınıfı korpusu aynı validator'ı ölçer"),
    ("scripts/validators/check_filter_search_pattern.py",
     ("V:check_filter_search_pattern",), "G1 çifti"),
    ("scripts/validators/check_decimal_write_to.py", ("V:check_decimal_write_to",), "G1 çifti"),
    ("scripts/validators/check_method_param_type_c.py",
     ("V:check_method_param_type_c",), "G1 çifti"),
    ("scripts/validators/check_no_rap_commit.py", ("V:check_no_rap_commit",), "G1 çifti"),
    ("scripts/validators/check_amdp_comment_apostrophe.py",
     ("V:check_amdp_comment_apostrophe",), "G1 çifti"),
    ("scripts/validators/check_kd_no_raw_mermaid.py", ("V:check_kd_no_raw_mermaid",), "G1 çifti"),
    ("scripts/validators/check_fs_no_analysis_log.py", ("O:fs_docstd",),
     "DOC-FS-05/06 sayacı: yakalama + kimlik-satırı FP çapaları (fixture kendi sandbox'ını kurar)"),
    ("scripts/validators/check_fm_signature_doc_sync.py", ("O:fm_imza_doc_sync",),
     "imza ayrıştırma + EKSİK/HAYALET + ÖLÇÜLEMEDİ ayrımı (fixture kendi sandbox'ını kurar)"),
    ("playbook/howto-dynpro-gui-status-generation.md", ("O:fm_imza_doc_sync",),
     "kılavuzun FM-IMZA bloğu gate'in girdisidir; blok bozulursa gate ÖLÇÜLEMEDİ vermeli"),
    ("playbook/adt-fugr-functions.md", ("O:fm_imza_doc_sync",),
     "§6 imza bloğu aynı gate'in ikinci belgesidir"),
    ("scripts/doc_equivalence_check.py", ("O:fs_docstd",),
     "DOC-FS-07 denklik ölçümü: kayıplı/kayıpsız çift + TR harf katlaması FP çapası"),

    # ── validator ailesi: kendi koşucusunu taşıyan korpuslar ────────────────
    ("scripts/validators/check_cds_currency_reference.py",
     ("O:cds_curr_satir_yorumu", "O:cds_curr_kaynak_tipi", "O:populate_tables_unit_kind"),
     "V1 korpusu bu validator'ı import eder; V2 korpusu CLI'yi subprocess ile koşup "
     "KAYNAK-TİPİ tespitini + çıkış-kodu sözleşmesini (0/1/2) ölçer; B-13 korpusu ise "
     "ÜRETİCİ↔DENETÇİ mutabakatını ölçer (ikisi aynı DTEL sözlüğünü kullanır)"),
    ("scripts/populate_tables.py", ("O:populate_tables_unit_kind",),
     "B-13/B-9/B-14: unit_kind kararı + CSV kolon sözleşmesi"),
    ("scripts/utils/ddic_semantics.py",
     ("O:populate_tables_unit_kind", "O:cds_curr_satir_yorumu"),
     "DTEL sözlüğü TEK KAYNAK: hem üretici hem denetçi bu modülü import eder"),
    ("scripts/validators/check_project_root_resolution.py",
     ("O:proje_koku_varyantlari", "O:conn_adt_proje_koku"),
     "V5 yazım-varyantları + CORE-01 dedektörünün ikinci yüzü"),
    ("scripts/validators/check_package_naming.py", ("O:paket_uzanti_kapsami",), "V2 korpusu"),
    ("scripts/validators/check_object_in_correct_pkg.py",
     ("O:paket_uzanti_kapsami",), "V2 korpusu (ikinci gate)"),
    ("scripts/validators/check_core_not_committed.py",
     ("O:gitignore_tam_satir",), "V4 korpusu"),
    ("scripts/validators/check_itg_signoff.py", ("O:itg_alan_dolulugu",), "V3 korpusu"),
    ("scripts/validators/check_instruction_budget.py",
     ("O:instruction_budget",), "C-BUD-01 korpusu"),
    ("scripts/validators/check_memory_index.py",
     ("O:memory_yukleme_butcesi",), "C-MEM-01 korpusu"),
    ("scripts/validators/run_review.py",
     ("O:reviewer_skip_sozlesmesi", "O:reviewer_tip_kapsam"),
     "SKIP sözleşmesi + push-tipi/reviewer haritası"),

    # ── git-hooks + guard yüzeyi ────────────────────────────────────────────
    ("scripts/git-hooks/core_precommit.py",
     ("O:changelog_gate", "O:sir_gate", "O:changelog_amend", "O:worktree_blocklist"),
     "pre-commit kontrollerinin dördü de bu dosyayı subprocess ile koşar"),
    ("scripts/genericize_common.py",
     ("O:worktree_blocklist", "O:tembel_desen", "R:AV-03", "G"),
     "kimlik/sızıntı deseni: guard + precommit + blocklist aynı modülü kullanır; tembel kurulum korpusu da burada"),
    ("scripts/hooks/pre_tool_guard.py",
     ("G", "O:negatif_test_harness", "O:tembel_desen"),
     "payload korpusu + parse-fail görünürlüğü + tembel desen-kurulumu"),
    ("scripts/hooks/session_start.py",
     ("O:overlay_oto_tazeleme", "O:negatif_test_harness"),
     "oto-tazeleme kablolaması + parse-fail notu"),
    ("scripts/hooks/*.py", ("O:negatif_test_harness",),
     "16 hook'un parse-fail sözleşmesi tek korpusta ölçülür"),
    ("scripts/hooks/infra_write_guard.py",
     ("O:infra_write_guard", "O:negatif_test_harness"),
     "kimlik ayrımı + korunan yüzey listesi + fail-closed degrade; parse-fail sözleşmesi"),
    ("claude/settings.template.json", ("O:infra_write_guard",),
     "kablolama korpusun K6 vektöründe ölçülür (kod ≠ kablolama)"),

    # ── overlay / proje-kurulum yüzeyi ──────────────────────────────────────
    ("scripts/utils/claude_overlay.py",
     ("O:overlay_kiyas_tabani", "O:overlay_oto_tazeleme"), "T2.5 kıyas tabanı + oto-tazeleme"),
    ("scripts/utils/claude_paths.py", ("O:proje_slug_tek_kaynak",), "slug tek-kaynak korpusu"),
    ("scripts/utils/project_config.py",
     ("R:AV-02", "O:workflow_tetik_dupe"),
     "BOM'lu yaml parse + workflow fixture'ının yaml-lite çözümleyicisi"),
    ("mcp_servers/sap_adt/_profile.py", ("R:AV-02",), "AV-02 kablolama ucu (tool yüzeyi)"),

    # ── SAP araç zinciri ────────────────────────────────────────────────────
    ("scripts/sap_adt_lib.py",
     ("O:conn_cift_anahtar", "O:conn_yazici_encoding", "O:dogrulama_kosamadi",
      "O:lock_modification_support", "O:class_include_push",
      "O:sessiz_olumsuzlama_2026_08_10", "O:retry_500_govde"),
     "yedi korpus bu modülü import/mutasyon eder"),
    ("scripts/sap_client.py",
     ("O:adtget_yokluk_kaniti", "O:class_include_push", "O:dogrulama_kosamadi",
      "O:sessiz_olumsuzlama_2026_08_10", "O:veri_yetki_guardlari",
      "O:sorgu_basarisizligi_gorunur"),
     "MCP tool'larının alt katmanı (`run_sql_query` None sözleşmesi dahil)"),
    ("scripts/create_rap_service.py", ("O:aktivasyon_sahte_ok",), "activate_and_verify"),
    ("scripts/sap_sync_pull.py", ("O:ddic_okuma_yolu",), "DDIC okuma-yolu ikinci tüketici"),
    ("scripts/push_object.py", ("O:class_include_push",), "ccau/ccimp push sırası"),
    ("scripts/push_textpool.py", ("O:lock_modification_support",), "lock sinyali tüketicisi"),
    ("scripts/sap_set_object_description.py",
     ("O:lock_modification_support",), "lock sinyali tüketicisi"),
    ("scripts/object_types.py",
     ("O:class_include_push", "O:reviewer_tip_kapsam"), "tip normalizasyonu"),
    ("scripts/deploy_ui.py",
     ("O:git_sorgu_sessiz_bos", "O:sessiz_olumsuzlama_2026_08_10"),
     "git sorgusu + sessiz olumsuzlama"),
    ("scripts/worklist_audit.py", ("R:AV-13",), "üç-değerli sınıflama"),
    ("scripts/build_core_index.py", ("O:core_index_kapsam",), "indeks kapsamı"),
    ("scripts/switch_tier.py", ("O:tier_fail_closed",), "tier çözümleme"),
    ("scripts/statusline.py", ("O:tier_fail_closed",), "tier göstergesi"),
    ("scripts/ui-smoke/run_ui_smoke.py", ("O:conn_adt_proje_koku",), "proje-kökü çözümlemesi"),
    ("mcp_servers/sap_adt/_conn.py",
     ("O:tier_fail_closed", "O:conn_cift_anahtar", "O:veri_yetki_guardlari"),
     ".conn_adt okuyucusu"),
    ("mcp_servers/sap_adt/guardrails.py", ("O:tier_fail_closed",), "require_writable_tier"),
    ("mcp_servers/sap_adt/data_guard.py",
     ("O:veri_yetki_guardlari", "O:tier_fail_closed"), "ADR 0011 PII + yetki"),
    ("mcp_servers/sap_adt/_reviewer.py", ("O:reviewer_tip_kapsam",), "push-tipi ↔ reviewer"),
    ("mcp_servers/sap_adt/tools/atom.py",
     ("O:adtget_yokluk_kaniti", "O:ddic_okuma_yolu", "O:dogrulama_kosamadi",
      "O:reviewer_tip_kapsam"),
     "adt_get/adt_push/adt_delete uçları"),
    ("mcp_servers/sap_adt/tools/query.py",
     ("O:dogrulama_kosamadi", "O:veri_yetki_guardlari", "O:sorgu_basarisizligi_gorunur"),
     "where_used/ATC + veri sorgusu + başarısızlık görünürlüğü"),

    # ── CI / şablon tetikleri ───────────────────────────────────────────────
    ("claude/workflows/*.yml", ("O:workflow_tetik_dupe",), "şablon tetik sözleşmesi"),
    (".github/workflows/*.yml", ("O:workflow_tetik_dupe",), "core-ci + reusable tetikleri"),
    ("claude/kesin-yasaklar.canonical.md", ("G", "O:worktree_blocklist"),
     "core kimliğinin İŞARET DOSYASI (AV-21): guard bu dosyadan core'u tanır"),

    # ── indekslenen dokümantasyon ───────────────────────────────────────────
    # `build_core_index.uret()` GERÇEK repo ağacını tarar (ALANLAR + DUZ_ALANLAR) →
    # bu dizinlerdeki bir doküman eklemek/silmek indeksi değiştirir (çiftleme/hariç
    # tutma çapaları). Diğer korpuslar bu .md'lere BAKMAZ (hepsi sentetik ağaç kurar).
    ("governance/**", ("O:core_index_kapsam",), "CORE-INDEX düz + decisions alanı"),
    ("playbook/**", ("O:core_index_kapsam",), "CORE-INDEX alanı"),
    ("standards/**", ("O:core_index_kapsam",), "CORE-INDEX alanı"),
    ("profiles/**", ("O:core_index_kapsam",), "CORE-INDEX alanı"),
]

# Fixture DİZİNİNE dokunulduğunda o fixture koşar. Bölüm-1/OZEL adları dizin adıyla
# birebirdir; bölüm-2/3 korpuslarının dizin adları farklı olduğu için burada eşlenir.
# ⚠ Bu kural harita-tamlık kontrolünde SAYILMAZ (yoksa kontrol boş bir tören olurdu:
# her fixture kendi dizini üzerinden "kapsanmış" görünürdü).
FIXTURE_DIZIN_BIRIMI: dict[str, tuple[str, ...]] = {
    "av02_project_config_bom": ("R:AV-02",),
    "av03_genericize_sap_user": ("R:AV-03",),
    "av13_worklist_classify": ("R:AV-13",),
    "pre_tool_guard": ("G",),
}


def _desen_regex(desen: str) -> re.Pattern:
    """`**` = herhangi (bölü dahil) · `*` = tek segment içi · gerisi literal."""
    parca, i = [], 0
    while i < len(desen):
        if desen.startswith("**", i):
            parca.append(".*")
            i += 2
        elif desen[i] == "*":
            parca.append("[^/]*")
            i += 1
        else:
            parca.append(re.escape(desen[i]))
            i += 1
    return re.compile("^" + "".join(parca) + "$")


def _repo_goreli(yol: str) -> str | None:
    """Verilen yolu repo-köküne göreli POSIX yoluna çevir; repo dışıysa None."""
    kok = HERE.parent
    try:
        p = Path(yol)
        mutlak = p if p.is_absolute() else (Path.cwd() / p)
        # resolve(): junction/symlink ve `..` normalize edilir. Dosya var olmak
        # ZORUNDA değil (silinmiş dosya da geçerli girdidir) → strict=False.
        return mutlak.resolve().relative_to(kok.resolve()).as_posix()
    except Exception:
        return None


def _eslesme(rel: str) -> tuple[set[str] | None, str]:
    """(birimler | None, gerekçe). None = haritada YOK → çağıran TAM süiteye düşer."""
    parca = rel.split("/")
    if len(parca) >= 3 and parca[0] == "tests" and parca[1] == "fixtures":
        ad = parca[2]
        if ad in {a for a, _ in OZEL_TESTLER}:
            return {f"O:{ad}"}, "fixture dizini"
        if ad in VALIDATORS:
            return {f"V:{ad}"}, "fixture dizini (bölüm-1)"
        if ad in FIXTURE_DIZIN_BIRIMI:
            return set(FIXTURE_DIZIN_BIRIMI[ad]), "fixture dizini (bölüm-2/3)"
        return None, f"tanınmayan fixture dizini: {ad}"

    birimler: set[str] = set()
    gerekceler: list[str] = []
    for desen, br, gerekce in HARITA:
        if _desen_regex(desen).match(rel):
            birimler |= set(br)
            gerekceler.append(gerekce)
    if not gerekceler:
        return None, "haritada desen yok"
    return birimler, " + ".join(dict.fromkeys(gerekceler))


def birimleri_sec(dosyalar: list[str]) -> tuple[set[str] | None, list[str]]:
    """(seçim | None, görünür notlar). None = TAM süite (fail-closed)."""
    notlar: list[str] = []
    if not dosyalar:
        return None, ["--degisen listesi BOŞ → TAM süite (fail-closed)"]

    secim: set[str] = set()
    tam = False
    for ham in dosyalar:
        rel = _repo_goreli(ham)
        if rel is None:
            notlar.append(f"repo DIŞI/çözülemeyen yol: {ham} → TAM süite")
            tam = True
            continue
        br, gerekce = _eslesme(rel)
        if br is None:
            notlar.append(f"bilinmeyen dosya {rel} → TAM süite ({gerekce})")
            tam = True
            continue
        if TAM in br:
            notlar.append(f"{rel} → TAM süite ({gerekce})")
            tam = True
            continue
        if not br:
            # AÇIKÇA boş bildirilmiş desen (bugün HARITA'da örneği yok — dal, gelecekte
            # "bu korpusu hiç ilgilendirmeyen" bir alan eklenirse diye duruyor ve
            # b0_secim N6'da ölçülüyor). Sessizlik yok: karar satır olarak basılır.
            notlar.append(f"{rel} → bu korpusta ilgili fixture YOK ({gerekce})")
            continue
        notlar.append(f"{rel} → {', '.join(sorted(br))}")
        secim |= br
    return (None, notlar) if tam else (secim, notlar)


def harita_tamlik() -> list[tuple[str, str, bool, str]]:
    """TAM koşumda vektör: (kısa-ad, açıklama, ok, detay).

    Her fixture haritada anılıyor mu (yeni fixture + güncellenmemiş harita = sessiz
    kapsam-dışı) + haritada tanımsız birim var mı (yazım hatası = sessiz seçmeme).
    """
    tanimli = ({f"V:{n}" for n in VALIDATORS}
               | {f"O:{a}" for a, _ in OZEL_TESTLER}
               | {f"R:{k}" for k, _, _ in REGRESYON}
               | {"G"})
    anilan: set[str] = set()
    for _, br, _ in HARITA:
        anilan |= {b for b in br if b != TAM}

    kapsanmayan = sorted(tanimli - anilan)
    hayalet = sorted(anilan - tanimli)
    return [
        ("HARİTA-TAMLIK/kapsam", "her fixture haritada anılıyor", not kapsanmayan,
         f"haritada anılmayan birim(ler)={kapsanmayan} → `--degisen` bunları ASLA seçemez; "
         f"HARITA'ya satır ekle"),
        ("HARİTA-TAMLIK/hayalet", "haritada tanımsız birim yok", not hayalet,
         f"tanımsız birim(ler)={hayalet} (yazım hatası?)"),
    ]


def run_validator(name: str, fixture_dir: Path) -> tuple[int, str]:
    script = VALIDATORS_DIR / f"{name}.py"
    env = os.environ.copy()
    # Sizinti onleme: parent surecten IX_*/CLAUDE_PROJECT_DIR miras alinmaz.
    for k in list(env):
        if k == "CLAUDE_PROJECT_DIR" or k.startswith("IX_"):
            env.pop(k, None)
    env["CLAUDE_PROJECT_DIR"] = str(fixture_dir)
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(fixture_dir),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def run_ozel(ad: str) -> tuple[int, str]:
    """tests/fixtures/<ad>/run.py — kendi P/N senaryolarini kosan bagimsiz fixture."""
    script = FIXTURES / ad / "run.py"
    env = os.environ.copy()
    for k in list(env):
        if k == "CLAUDE_PROJECT_DIR" or k.startswith("IX_"):
            env.pop(k, None)
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(HERE.parent),          # repo koku (fixture kendi izolasyonunu kurar)
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
# =============================================================================
# BÖLÜM 2 — REGRESYON VEKTÖRLERİ (bug-avı 2026-08-01: AV-02 / AV-03 / AV-13)
#
# Bunlar validator DEĞİL, kütüphane-seviyesi davranışlardır (yaml-parser, sızıntı-deseni,
# üç-değerli sınıflama) → yukarıdaki bad/good subprocess kalıbına girmezler. Aynı TEK
# giriş noktasından koşsunlar diye buraya kablolandılar: `python tests/run_fixture_tests.py`.
# =============================================================================
REPO = HERE.parent
for _p in (REPO / "scripts", REPO / "scripts" / "utils"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def _sonuc(ad: str, ok: bool, detay: str = "") -> tuple:
    return (ad, ok, detay)


def av02_kontrolleri() -> list[tuple]:
    """BOM'lu project.yaml ilk anahtarı BOZMAMALI (AV-02).

    Kök: `read_text(encoding="utf-8")` BOM'u metnin İÇİNDE bırakır → ilk anahtar
    '\\ufeffsap_profile' olur → cfg("sap_profile") None → MCP profil katmanı fail-closed'a
    düşer ve TÜM SAP tool yüzeyi sessizce yalnız `ping`e iner.
    """
    import tempfile
    from utils import project_config as pc  # type: ignore

    fx = FIXTURES / "av02_project_config_bom"
    out = []

    beklenen = {"sap_profile": "s4_private", "release": "2025",
                "master_language": "TR", "source_root": "SOURCE_CODES"}

    for ad in ("bomsuz.yaml", "bomlu.yaml"):
        pc._yaml_lite.cache_clear()
        d = pc._yaml_lite(str(fx / ad))
        out.append(_sonuc(f"AV-02 parse {ad}", d == beklenen, f"alındı={d}"))

    # En güçlü ifade: BOM'lu ve BOM'suz AYNI sözlüğü vermeli (bayt-eş davranış).
    pc._yaml_lite.cache_clear(); a = pc._yaml_lite(str(fx / "bomsuz.yaml"))
    pc._yaml_lite.cache_clear(); b = pc._yaml_lite(str(fx / "bomlu.yaml"))
    out.append(_sonuc("AV-02 BOM'lu == BOM'suz (regresyon çapası)", a == b, f"{a} vs {b}"))

    # 3. BAĞLAM — CRLF: git `.gitattributes`'ta `*.yaml text eol=lf` olduğu için CRLF'li
    # bir fixture DOSYAYA YAZILAMAZ (commit'te LF'e normalize edilir → test sessizce
    # anlamsızlaşırdı). Bu yüzden CRLF varyantı KOŞUM ANINDA türetilir.
    tmp = Path(tempfile.mkdtemp())
    ham = (fx / "bomlu.yaml").read_bytes().replace(b"\n", b"\r\n")
    (tmp / "crlf.yaml").write_bytes(ham)
    pc._yaml_lite.cache_clear()
    d = pc._yaml_lite(str(tmp / "crlf.yaml"))
    out.append(_sonuc("AV-02 3.bağlam BOM+CRLF (Windows/PowerShell şekli)",
                      d == beklenen, f"alındı={d}"))

    # Yozlaşmış girdiler: çökmemeli, boş sözlük dönmeli.
    for ad in ("yalniz_bom.yaml", "bos.yaml"):
        pc._yaml_lite.cache_clear()
        d = pc._yaml_lite(str(fx / ad))
        out.append(_sonuc(f"AV-02 yozlaşmış {ad} → {{}} (çökme yok)", d == {}, f"alındı={d}"))

    # KABLOLAMA (kod ≠ kablolama): asıl sonuç zinciri — BOM'lu project.yaml ile MCP
    # tool yüzeyi çökmemeli. `_profile.aktif_profil()` None dönerse yalnız `ping` açılır.
    eski = os.environ.get("CLAUDE_PROJECT_DIR")
    try:
        proj = Path(tempfile.mkdtemp())
        (proj / "project.yaml").write_bytes((fx / "bomlu.yaml").read_bytes())
        os.environ["CLAUDE_PROJECT_DIR"] = str(proj)
        pc._yaml_lite.cache_clear()
        prof_okundu = pc.sap_profile()
        sys.path.insert(0, str(REPO / "mcp_servers" / "sap_adt"))
        import _profile  # type: ignore
        aktif = _profile.aktif_profil()
        acik = _profile.uygun_mu(("all",), aktif)
        out.append(_sonuc("AV-02 KABLOLAMA: BOM'lu yaml → MCP tool yüzeyi AÇIK kalır",
                          prof_okundu == "s4_private" and aktif == "s4_private" and acik,
                          f"cfg={prof_okundu!r} aktif_profil={aktif!r} tool_acik={acik}"))
    finally:
        if eski is None:
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
        else:
            os.environ["CLAUDE_PROJECT_DIR"] = eski
        pc._yaml_lite.cache_clear()

    return out


def _av03_vektorler(p: Path) -> list[tuple[int, str]]:
    """`<beklenen-sayı>\\t<metin>` satırlarını oku; {{D}}/{{d}} ikame et."""
    ciftler = []
    for ham in p.read_text(encoding="utf-8-sig").splitlines():
        if not ham.strip() or ham.lstrip().startswith("#"):
            continue
        sayi, _, metin = ham.partition("\t")
        ciftler.append((int(sayi.strip()), metin.replace("{{D}}", "D").replace("{{d}}", "d")))
    return ciftler


def av03_kontrolleri() -> list[tuple]:
    """SAP kullanıcı-adı deseni: küçük harf + rakam soneki YAKALANMALI, placeholder MUAF."""
    import genericize_common as G  # type: ignore

    fx = FIXTURES / "av03_genericize_sap_user"
    out = []
    for dosya, etiket in (("sizinti.txt", "POZİTİF"), ("temiz.txt", "NEGATİF")):
        sapan = []
        for beklenen, metin in _av03_vektorler(fx / dosya):
            bulunan = G.sap_user_sizintilari(metin)
            if len(bulunan) != beklenen:
                sapan.append(f"{metin!r}: beklenen={beklenen} bulunan={bulunan}")
        out.append(_sonuc(f"AV-03 {etiket} vektörler ({dosya})", not sapan,
                          "; ".join(sapan[:4])))

    # ⚠ Bu dosyadaki örnek token'lar da PARÇALI kurulur — bu dosya da taranıyor
    # (ilk taslakta buraya literal yazmıştım; gerçek commit onu ihlal saydı).
    d, U = chr(100), chr(68)
    # KABLOLAMA: desen tek başına değil, gate'in çağırdığı `sizintilari_bul` üzerinden
    # de görünmeli (guard'lar bu fonksiyonu kullanır — kod ≠ kablolama).
    idp = G.id_pattern()
    bulgular = G.sizintilari_bul("kullanici " + d + "_sampleuser sisteme baglandi", idp)
    turler = {tur for _, tur in bulgular}
    out.append(_sonuc("AV-03 KABLOLAMA: sizintilari_bul bağlamlı küçük-harf kimliği raporlar",
                      "SAP kullanıcı adı" in turler, f"bulgular={bulgular}"))

    # ŞİDDET/BAĞLAM AYRIMI — FP'yi 4'ten 0'a indiren tasarım kararının birebir çapası:
    # aynı küçük-harf token bağlamsız satırda SESSİZ, kimlik satırında YAKALANIR.
    baglamsiz = "toplam = " + d + "_total + " + d + "_rows"
    baglamli = "ADT_SAP_USER=" + d + "_svcuser01"
    out.append(_sonuc("AV-03 bağlam ayrımı: bağlamsız SESSİZ / bağlamlı YAKALANIR",
                      G.sap_user_sizintilari(baglamsiz) == []
                      and len(G.sap_user_sizintilari(baglamli)) == 1,
                      f"bağlamsız={G.sap_user_sizintilari(baglamsiz)} "
                      f"bağlamlı={G.sap_user_sizintilari(baglamli)}"))

    # 3. BAĞLAM — placeholder muafiyetinin GERÇEK kaynağı: şablon projesi metni.
    # (2026-07-10 vakası: kendi README şablonumuz FP'ye takılmıştı; muafiyet o yüzden var.)
    sablon = ("ADT_SAP_USER=" + U + "_XXXXXXX\n# ornek: " + U + "_NNNNNN\n"
              "kucuk yazim (user satiri): " + d + "_xxxx\n")
    out.append(_sonuc("AV-03 3.bağlam: şablon placeholder'ları hâlâ MUAF (FP yok)",
                      G.sap_user_sizintilari(sablon) == [],
                      f"bulunan={G.sap_user_sizintilari(sablon)}"))
    return out


def av13_kontrolleri() -> list[tuple]:
    """Üç-değerli sınıflama: okunamayan sürüm ASLA PHANTOM/STALE'e katlanmamalı."""
    import json as _json

    import worklist_audit as W  # type: ignore

    fx = FIXTURES / "av13_worklist_classify" / "siniflama.json"
    veri = _json.loads(fx.read_text(encoding="utf-8-sig"))
    out = []

    # --- sınıflama matrisi (9 vektör) ---
    orijinal_ve, orijinal_op = W._version_exists, W._object_package
    sapan = []
    try:
        W._object_package = lambda *a, **k: None
        for c in veri["siniflama"]:
            sirali = iter([c["has_active"], c["has_inactive"]])
            W._version_exists = lambda adt, uri, ver, _s=sirali: next(_s)
            r = W._classify(None, None, {"uri": "/x", "name": "N", "type": "CLAS/OC"})
            if r["class"] != c["beklenen"]:
                sapan.append(f"({c['has_active']},{c['has_inactive']}) "
                             f"beklenen={c['beklenen']} alınan={r['class']}")
    finally:
        W._version_exists, W._object_package = orijinal_ve, orijinal_op
    out.append(_sonuc("AV-13 sınıflama matrisi (9 vektör)", not sapan, "; ".join(sapan)))

    # --- 3. BAĞLAM: bir alt katman — HTTP durum kodu → üç değer eşlemesi ---
    class _SahteCevap:
        def __init__(self, kod): self.status_code = kod

    class _SahteOturum:
        def __init__(self, kod): self.kod = kod
        def get(self, *a, **k):
            if self.kod == "EXCEPTION":
                raise OSError("ağ koptu")
            return _SahteCevap(self.kod)

    class _SahteAdt:
        def __init__(self, kod): self.session, self.url = _SahteOturum(kod), "http://x"

    sapan = []
    for c in veri["durum_kodlari"]:
        alinan = orijinal_ve(_SahteAdt(c["status"]), "/uri", "active")
        if alinan is not c["beklenen"]:
            sapan.append(f"status={c['status']} beklenen={c['beklenen']} alınan={alinan}")
    out.append(_sonuc("AV-13 3.bağlam: HTTP durum → üç-değer eşlemesi (9 kod)",
                      not sapan, "; ".join(sapan)))

    # --- çıkış-kodu sözleşmesi: bilinmeyen varken "commit güvenli" (0) DENMEZ ---
    sapan = []
    for real, unknown, beklenen in (([], [], 0), ([], ["u"], 2), (["r"], [], 1), (["r"], ["u"], 1)):
        alinan = W._exit_kodu(real, unknown)
        if alinan != beklenen:
            sapan.append(f"real={bool(real)} unknown={bool(unknown)} "
                         f"beklenen={beklenen} alınan={alinan}")
    out.append(_sonuc("AV-13 çıkış-kodu sözleşmesi (0/1/2)", not sapan, "; ".join(sapan)))
    return out


# (birim-kimliği, başlık, fonksiyon) — kimlik `--degisen` haritasında `R:<id>` olarak anılır.
REGRESYON = [
    ("AV-02", "AV-02 project_config BOM", av02_kontrolleri),
    ("AV-03", "AV-03 genericize SAP kullanıcı deseni", av03_kontrolleri),
    ("AV-13", "AV-13 worklist üç-değerli sınıflama", av13_kontrolleri),
]


def regresyon_kos(secim: set[str] | None = None) -> tuple[int, int]:
    """(gecen, toplam) — ayrıntıyı basar. `secim` verilirse yalnız seçili AV'ler koşar."""
    gecen = toplam = 0
    print("\n=== REGRESYON VEKTÖRLERİ (bug-avı 2026-08-01) ===")
    # ⚠ ZORUNLU FLUSH — `worklist_audit` import-ANINDA sys.stdout'u YENİ bir
    # TextIOWrapper ile değiştiriyor (worklist_audit.py:36-40, win32 dalı). Eski
    # wrapper'daki henüz boşaltılmamış çıktı bu sırada KAYBOLUYOR: ilk koşumda bu
    # dosyanın 24 satırlık raporu 6 satıra düşmüş, buna rağmen "24/24 PASS" yazmıştı
    # (sessiz çıktı kaybı — "PASS ≠ baktı"). Import'lardan ÖNCE boşalt.
    sys.stdout.flush()
    sys.stderr.flush()
    for birim, baslik, fn in REGRESYON:
        if secim is not None and f"R:{birim}" not in secim:
            print(f"  [ATLANDI — seçim modu] {baslik}")
            continue
        try:
            sonuclar = fn()
        except Exception as exc:  # noqa: BLE001
            print(f"  [DOĞRULANAMADI] {baslik}: {type(exc).__name__}: {exc}")
            toplam += 1
            continue
        for ad, ok, detay in sonuclar:
            toplam += 1
            gecen += 1 if ok else 0
            print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
            if not ok:
                print(f"         -> {detay}")
        # Her blok sonunda boşalt: SONRAKİ bileşenin import'u stdout'u değiştirebilir
        # ve bu bloğun çıktısını yutabilir (yukarıdaki worklist_audit notu).
        sys.stdout.flush()
    return gecen, toplam


def _argumanlari_coz(argv: list[str]) -> tuple[list[str] | None, bool]:
    """(degisen | None, listele). `None` = argümansız TAM koşum (bugünkü davranış)."""
    degisen: list[str] | None = None
    listele = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--degisen":
            degisen = []
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                degisen.append(argv[i])
                i += 1
            continue
        if a == "--listele":
            listele = True
        else:
            print(f"[HATA] bilinmeyen argüman: {a}\n{__doc__}")
            raise SystemExit(2)
        i += 1
    if listele and degisen is None:
        # Kuru koşum yalnız seçim modunun anlamlıdır; argümansız kuru koşum "TAM" der.
        degisen = []
    return degisen, listele


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:]) if argv is None else list(argv)
    degisen, listele = _argumanlari_coz(argv)

    secim: set[str] | None = None
    if degisen is not None:
        secim, notlar = birimleri_sec(degisen)
        print("=== SEÇİM MODU (--degisen) — TAM SÜİTE DEĞİL ===")
        for n in notlar:
            print(f"  · {n}")
        if secim is None:
            print("  ⇒ KARAR: TAM süite koşulacak (fail-closed)\n")
        else:
            print(f"  ⇒ KARAR: {len(secim)} birim — {', '.join(sorted(secim)) or '(yok)'}")
            print("  ⚠ Bu bir ARA-ADIM koşumudur; merge öncesi 1× TAM süite ZORUNLU.\n")
        if listele:
            return 0

    rows = []  # (name, bad_desc, good_desc, verdict, detail)
    all_ok = True
    atlanan = 0
    # ⛔ TEŞHİS EDİLEBİLİRLİK (2026-08-19): başarısız birimin YAKALANAN çıktısı tablodan
    # sonra TAM basılır. Öncesinde yalnız son 400 karakter tabloya sığdırılıyordu; fixture
    # kendi 38 alt vakasını basıyor olsa da CI logunda GÖRÜNMÜYORDU (kuyruk traceback'e
    # gidiyordu) ⇒ yalnız Windows'ta çalışan bir ekip, Linux runner'da düşen vakayı
    # teşhis EDEMİYORDU. Bu bir fail-open değil, ama ölçüm aletinin kör noktasıydı.
    # ⚠ Yalnız BAŞARISIZLIKTA basılır (yeşil koşumda log şişmez).
    basarisiz_ciktilar: list[tuple[str, str]] = []

    for name in VALIDATORS:
        if secim is not None and f"V:{name}" not in secim:
            atlanan += 1
            continue
        script = VALIDATORS_DIR / f"{name}.py"
        bad_dir = FIXTURES / name / "bad"
        good_dir = FIXTURES / name / "good"

        if not script.is_file():
            rows.append((name, "n/a", "n/a", "DOĞRULANAMADI", f"validator bulunamadı: {script}"))
            all_ok = False
            continue
        if not bad_dir.is_dir() or not good_dir.is_dir():
            rows.append((name, "n/a", "n/a", "DOĞRULANAMADI", "fixture bad/good dizini eksik"))
            all_ok = False
            continue

        try:
            bad_rc, bad_out = run_validator(name, bad_dir)
            good_rc, good_out = run_validator(name, good_dir)
        except Exception as exc:  # pragma: no cover -- gercek calisma-zamani hatasi
            rows.append((name, "n/a", "n/a", "DOĞRULANAMADI", f"çalıştırma hatası: {exc}"))
            all_ok = False
            continue

        bad_ok = bad_rc != 0
        good_ok = good_rc == 0
        ok = bad_ok and good_ok
        all_ok = all_ok and ok

        detail = ""
        if not bad_ok:
            detail += f" | bad BEKLENMEDİK exit={bad_rc} çıktı: {bad_out.strip()[:200]}"
        if not good_ok:
            detail += f" | good BEKLENMEDİK exit={good_rc} çıktı: {good_out.strip()[:200]}"
        if not ok:
            if not bad_ok:
                basarisiz_ciktilar.append((f"V:{name} [bad]", bad_out))
            if not good_ok:
                basarisiz_ciktilar.append((f"V:{name} [good]", good_out))

        rows.append((
            name,
            f"exit={bad_rc} ({'OK' if bad_ok else 'TERS'})",
            f"exit={good_rc} ({'OK' if good_ok else 'TERS'})",
            "PASS" if ok else "FAIL",
            detail,
        ))

    for ad, aciklama in OZEL_TESTLER:
        if secim is not None and f"O:{ad}" not in secim:
            atlanan += 1
            continue
        script = FIXTURES / ad / "run.py"
        if not script.is_file():
            rows.append((ad, "n/a", "n/a", "DOĞRULANAMADI", f"özel fixture yok: {script}"))
            all_ok = False
            continue
        try:
            rc, out = run_ozel(ad)
        except Exception as exc:  # pragma: no cover
            rows.append((ad, "n/a", "n/a", "DOĞRULANAMADI", f"çalıştırma hatası: {exc}"))
            all_ok = False
            continue
        ok = rc == 0
        all_ok = all_ok and ok
        if not ok:
            basarisiz_ciktilar.append((f"O:{ad}", out))
        # Ozel fixture P ve N senaryolarini KENDI icinde tasir → tek exit kodu raporlanir.
        ozet = [s for s in out.splitlines() if re.match(r"^\s*\d+/\d+ OK", s)][-1:] or [""]
        rows.append((
            ad,
            f"P+N içeride ({aciklama[:18]}…)",
            f"exit={rc} ({'OK' if ok else 'SAPMA'})",
            "PASS" if ok else "FAIL",
            "" if ok else f" | {out.strip()[-400:]}",
        ))
        if ok:
            rows[-1] = (rows[-1][0], f"P+N içeride: {ozet[0].strip()}", rows[-1][2],
                        rows[-1][3], rows[-1][4])

    # ── HARİTA-TAMLIK (yalnız TAM koşumda; seçim modunda kıyas tabanı yok) ──
    if secim is None:
        for kisa, aciklama, ok, detay in harita_tamlik():
            all_ok = all_ok and ok
            rows.append((kisa, aciklama, "harita ↔ fixture listesi",
                         "PASS" if ok else "FAIL", "" if ok else f" | {detay}"))

    if rows:
        name_w = max(len(r[0]) for r in rows) + 2
        print(f"{'validator':<{name_w}} {'bad (fail beklenir)':<26} "
              f"{'good (pass beklenir)':<26} sonuç")
        print("-" * (name_w + 26 + 26 + 8))
        for name, bad_s, good_s, verdict, detail in rows:
            print(f"{name:<{name_w}} {bad_s:<26} {good_s:<26} {verdict}")
            if detail:
                print(f"    -> {detail.strip(' |')}")
    else:
        print("(bölüm 1/OZEL: seçim modunda koşulacak birim yok)")

    # ── BAŞARISIZ BİRİMLERİN TAM ÇIKTISI (yalnız FAIL'de) ──────────────────────
    # Kırmızı bir koşum LOGDAN teşhis edilebilir olmalı: hangi alt vaka düştü, hangi
    # ortam varsayımı patladı. Kırpma varsa GÖRÜNÜR ("[KIRPILDI]") — sessiz kesme yok.
    KIRPMA = 20000
    for birim, ciktı in basarisiz_ciktilar:
        gövde = (ciktı or "").rstrip() or "(çıktı YOK — süreç hiçbir şey basmadı)"
        kirpildi = len(gövde) > KIRPMA
        print(f"\n{'=' * 78}\nBAŞARISIZ BİRİM ÇIKTISI (tam): {birim}\n{'=' * 78}")
        print(gövde[-KIRPMA:] if kirpildi else gövde)
        if kirpildi:
            print(f"[KIRPILDI] çıktının ilk {len(gövde) - KIRPMA} karakteri atlandı "
                  f"(toplam {len(gövde)}); yereldeyken fixture'ı doğrudan koş.")
        print("=" * 78)

    n_pass = sum(1 for r in rows if r[3] == "PASS")
    print(f"\n{n_pass}/{len(rows)} PASS  (bölüm 1: validator bad/good"
          f"{' + harita-tamlık' if secim is None else ''})")

    # ── BÖLÜM 2: regresyon vektörleri (AV-02/03/13 — kütüphane seviyesi) ──
    r_gecen, r_toplam = regresyon_kos(secim)
    print(f"\nregresyon vektörleri: {r_gecen}/{r_toplam} PASS  (bölüm 2)")

    # ── BÖLÜM 3: pre_tool_guard payload korpusu (AV-16/17/18/18b/21) ──
    # Ayrı dosyada yaşar (kendi mutasyon-modu var) ama TEK komutla koşsun diye buradan
    # çağrılır: CI adımı zaten bu dosyayı işaret ediyor; ikinci bir CI adımı eklemek
    # "kablolamayı unutma" riskini artırırdı (kod ≠ kablolama dersi — bu turda
    # test_commit_message_leak_gate tam olarak böyle 3 gün kablosuz kalmıştı).
    g_gecen = g_toplam = 0
    g_hatalar: list = []
    if secim is None or "G" in secim:
        sys.path.insert(0, str(HERE))
        try:
            from run_guard_fixture_tests import kosum as guard_kosum
        except Exception as exc:
            print(f"\n[DOĞRULANAMADI] guard payload korpusu yüklenemedi: {exc}")
            return 1
        print("\n" + "-" * 60)
        print("pre_tool_guard payload korpusu (blok + serbest)")
        g_gecen, g_toplam, g_hatalar = guard_kosum(sessiz=True)
        for h in g_hatalar:
            print(f"  [FAIL] {h}")
        print(f"{g_gecen}/{g_toplam} PASS  (bölüm 3: guard payload)")
    else:
        print("\n[ATLANDI — seçim modu] bölüm 3: pre_tool_guard payload korpusu")

    print(f"\nTOPLAM: {n_pass + r_gecen + g_gecen}/{len(rows) + r_toplam + g_toplam} PASS")
    if secim is not None:
        print(f"⚠ SEÇİLİ KOŞUM ({atlanan} fixture atlandı; bölüm-2/3 atlamaları yukarıda "
              f"satır satır) — TAM SÜİTE SONUCU DEĞİLDİR. "
              f"Merge öncesi: python tests/run_fixture_tests.py")
    return 0 if (all_ok and r_gecen == r_toplam and not g_hatalar) else 1


if __name__ == "__main__":
    sys.exit(main())
