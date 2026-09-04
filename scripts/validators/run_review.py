"""
run_review.py — Reviewer Agent Orchestrator (Pre-Flight Quality Gate)

Coordinator SAP yazma işlemi yapmadan önce çağırır. Görev tipine göre ilgili
validator'ları sırayla çalıştırır, yapılandırılmış rapor üretir.

Mantık:
  - Görev tipi → checklist (playbook/checklists/<task>.md) + validator zinciri
  - Her validator deterministik (LLM-bağımsız)
  - Çıktı: PASS / WARNING / BLOCKER (verdict) + checklist results + blind spots
  - BLOCKER → coordinator yazma yapmadan düzeltmeli (exit 1)
  - WARNING → coordinator yazabilir ama kullanıcıya bildirmeli (exit 0)
  - ⊘ SKIP → o gate ÖLÇÜM ÜRETMEDİ. İKİ ayrı yol aynı sonuca çıkar:
      (a) script bulunamadı  → hiç koşmadı;
      (b) script koştu, `exit 0` döndü ama stdout'ta `IX-GATE-STATUS ... measured=false`
          (2026-08-29, kayıt #5③): "koşturamadım" (config yok / obje tipi desteklenmiyor /
          araç yok) — `exit 0` görülse bile TEMİZ DEĞİL.
    "Koşmadı" ≠ "temiz": SKIP kendi şiddetiyle verdict'e SAYILIR (eksik BLOCKER →
    BLOCKER, eksik WARNING → WARNING). BOŞ ZİNCİL (dtel_update, rap_service_binding)
    bundan AYRIDIR: orada koşacak gate olmadığı BİLİNÇLİ karardır ve PASS kalır —
    kayıtsız eksiklik ile kayıtlı boşluk aynı şey değildir.
  - ~ SESSİZ BULGU (2026-09-04, Q239): gate KOŞTU, ÖLÇTÜ ve BULGU BASTI ama `exit 0`
    döndü (kendi sözleşmesi "yalnız WARNING → rc 0" diyor). Rapor bunu artık `~` ile
    işaretler ve bulgu metnini AYNEN basar. ⛔ Verdict aritmetiğine GİRMEZ — bu bir
    GÖRÜNÜRLÜK kalemidir; şiddet-etiketi ↔ çıkış-kodu hizalaması AYRI bir karardır.
  - ⊘ ZİNCİR YOK (2026-09-04, Q238): boş zincirde verdict `PASS` + exit 0 KALIR ama
    rapor GÖVDESİ (stdout) artık bunu söyler; eskiden yalnız stderr'de bir satır vardı
    ve stdout "✓ COORDINATOR: PASS" diyordu ⇒ iki akışı ayrı yakalayan okuyucu için
    "ölçüldü ve temiz" ile "ölçecek gate yok" AYNI görünüyordu.

Kullanım:
    # CDS yaratma öncesi
    python scripts/validators/run_review.py --task cds_creation --artifact <source_root>/SD/ZSD001_CLC/cds/ZSD001_DDL_X.cds

    # Tablo update öncesi
    python scripts/validators/run_review.py --task table_update --artifact <path>

    # Struct yaratma öncesi (Sprint 6)
    python scripts/validators/run_review.py --task struct_creation --artifact <path>

    # Output JSON (programatik kullanım)
    python scripts/validators/run_review.py --task cds_creation --artifact <path> --json

Exit kodu:
    0 — PASS veya WARNING (coordinator devam edebilir)
    1 — BLOCKER (coordinator durmalı)
    2 — Validator hatası (script çalışmadı)

Bkz. ADR 0006 — Reviewer Agent Pattern.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

VALIDATORS_DIR = Path(__file__).parent
# PROJE kökü: proje-lokal validator'ları (scripts/validators-local/) bulmak için.
# __file__ junction'la CORE'a çözülür → env CLAUDE_PROJECT_DIR öncelikli, cwd fallback.
PROJ_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())

# Görev tipi → validator zinciri
# Her validator: (script_name, severity_default, description)
TASK_VALIDATORS = {
    'cds_creation': [
        ('check_window_function_compatibility.py', 'BLOCKER',
         'Window function (OVER PARTITION BY) yok mu'),
        ('check_deprecated_annotations.py', 'WARNING',
         'preserveKey gibi deprecated annotation kontrolü'),
        ('check_cds_currency_reference.py', 'BLOCKER',
         'CURR/QUAN field annotation qualified format'),
        ('check_released_objects.py', 'WARNING',
         'Clean Core: non-released std tablo (FROM/JOIN) → released successor öner (MARA->I_Product)'),
        ('check_standard_table_fields.py', 'WARNING',
         'Std tablo alanları yeni sistemde gerçekten var mı (SAP GET; C-CDS-FROM-03)'),
    ],
    'cds_update': [
        ('check_window_function_compatibility.py', 'BLOCKER',
         'Window function yok mu'),
        ('check_deprecated_annotations.py', 'WARNING',
         'Deprecated annotation kontrolü'),
        ('check_cds_currency_reference.py', 'BLOCKER',
         'CURR/QUAN annotation kontrolü'),
        ('check_released_objects.py', 'WARNING',
         'Clean Core: non-released std tablo → released successor öner'),
    ],
    'table_creation': [
        ('check_struct_field_dtel_active.py', 'BLOCKER',
         'Kullanılan Z DTEL\'ler SAP\'de aktif mi (var olmayan/inaktif DTEL → aktivasyon fail)'),
        ('check_cds_currency_reference.py', 'BLOCKER',
         'CURR/QUAN field annotation qualified format (--type table)'),
        ('check_deprecated_annotations.py', 'WARNING',
         'Deprecated annotation'),
    ],
    'table_update': [
        ('check_struct_field_dtel_active.py', 'BLOCKER',
         'Kullanılan Z DTEL\'ler SAP\'de aktif mi (var olmayan/inaktif DTEL → aktivasyon fail)'),
        ('check_table_field_drop.py', 'BLOCKER',
         'Mevcut alan DROP / RENAME / TİP değişikliği (canlı SAP source diff — veri kaybı koruması)'),
        ('check_cds_currency_reference.py', 'BLOCKER',
         'Yeni eklenen CURR/QUAN field annotation kontrolü'),
        ('check_deprecated_annotations.py', 'WARNING',
         'Deprecated annotation'),
        ('check_standard_table_fields.py', 'WARNING',
         'Std tablo alanları yeni sistemde var mı (SAP GET; C-TBL-STD-01)'),
    ],
    'struct_creation': [
        ('check_struct_field_dtel_active.py', 'BLOCKER',
         'Kullanılan Z DTEL\'ler aktif mi'),
        ('check_cds_currency_reference.py', 'BLOCKER',
         'CURR/QUAN annotation kontrolü'),
        ('check_td_cancelled_fields.py', 'WARNING',
         'TD-iptal alanlar struct\'a sızmış mı (Sprint 6 T10)'),
        ('check_deprecated_annotations.py', 'WARNING',
         'Deprecated annotation'),
        ('check_standard_table_fields.py', 'WARNING',
         'Std tablo alanları yeni sistemde var mı (SAP GET; C-STR-FIELD-03)'),
    ],
    'struct_post_create': [
        ('check_sap_struct_consistency.py', 'BLOCKER',
         'SAP\'deki struct lokal artifact ile tutarlı mı (placeholder/field count diff)'),
        ('check_sap_active_version.py', 'BLOCKER',
         'SAP\'de version="active" mi'),
    ],
    'sap_active_check': [
        ('check_sap_active_version.py', 'BLOCKER',
         'SAP\'de version="active" mi'),
        ('check_sap_master_language.py', 'WARNING',
         'Z obje masterLanguage=TR mi (ADR 0005-D; post-create; C-RAP-LANG-01)'),
    ],
    'domain_creation_csv': [
        ('check_domain_output_length.py', 'BLOCKER',
         'Domain output length formula kontrolü'),
    ],
    # #30② (2026-08-29): `dtel_update` VARDI ama `dtel_creation` YOKTU → `--task
    # dtel_creation` argparse'ta exit 2 ile reddediliyordu, yani DTEL YARATIMI hiç
    # review edilemiyordu. ⛔ SIRA: önce GERÇEK kontrol (check_dtel_creation_labels.py)
    # yazıldı, görev SONRA bağlandı. Tersi (önce boş görev) exit 2'yi `PASS`+exit 0'a
    # çevirir ve sıfır kontrollü sahte-yeşil üretirdi — geçici bile olsa kabul edilemez.
    'dtel_creation': [
        ('check_dtel_creation_labels.py', 'BLOCKER',
         'DTEL yaratma CSV\'si: 4 label + description DOLU, uzunluklar sınırda, '
         'type_kind=domain ise domain bağı tam (ADR 0005-D / madde D)'),
    ],
    'dtel_update': [
        # DTEL update için spesifik validator henüz yok — manual review.
        # ⚠ BOŞ ZİNCİL BİLİNÇLİDİR (docstring'deki "kayıtlı boşluk" istisnası) ve
        # `dtel_creation` doldurulduğu için buraya OTOMATİK devralınmaz: update'in
        # kendi tuzağı AYRIDIR (adt-domain-dtel.md §3b: `adtcore:description` XML'de
        # İKİ yerde geçer, düz re.sub PAKET açıklamasını da ezer) — o ayrı bir kalem.
    ],
    'class_push': [
        ('check_method_param_type_c.py', 'BLOCKER',
         'Source-based class method-param TYPE c LENGTH n → save-scan kırar (satırsız 400, adt-rap §34-A); TYPE string kullan'),
        ('check_decimal_write_to.py', 'WARNING',
         'API-body sınıfında WRITE..TO → decimal locale tuzağı (binlik ayıraç, Edm.Decimal 400); direkt atama'),
        ('check_amdp_comment_apostrophe.py', 'BLOCKER',
         'AMDP SQLScript `--` yorumunda apostrof → aktivasyon "multi-line literal" FAIL (BE-28c; syntax_check/abaplint görmez, activation-only)'),
        ('check_docu_itf_line_width.py', 'BLOCKER',
         'DOCU/F1 runner ITF iv_line >72 ham char → F1/SE61 görüntülemede kuyruk KIRPILIR (std/08 §3; depolama≤132≠görüntüleme≤72; DOC-F1-01)'),
        ('check_released_objects.py', 'WARNING',
         'Clean Core: ABAP SELECT FROM non-released std tablo → released CDS successor öner'),
        ('check_abaplint.py', 'WARNING',
         'abaplint (tuned): yapısal/mantık+hijyen (parser/unreachable/identical/empty/tab) — class/program'),
        # ⛔ KATEGORİ B (std tablo direkt I/U/D) MCP server-side guardrail + manual review.
        # Otoriter syntax = adt_syntax_check (SAP inactive); abaplint = offline pre-push + clean-code.
    ],
    # ─── RAP (ilk kez — ORDER pilotu; standards/05-coding-rap.md) ──────────────
    'rap_cds_creation': [
        # RAP view entity de DDLS — klasik CDS validator zinciri geçerli.
        # FARK: view entity'de @AbapCatalog.sqlViewName YASAK (checklist C-RAP-VE-02).
        ('check_window_function_compatibility.py', 'BLOCKER',
         'Window function (OVER PARTITION BY) yok mu'),
        ('check_deprecated_annotations.py', 'WARNING',
         'preserveKey gibi deprecated annotation kontrolü'),
        ('check_cds_currency_reference.py', 'BLOCKER',
         'CURR/QUAN field annotation qualified format'),
        ('check_rap_readonly_consumption.py', 'BLOCKER',
         'Read-only consumption: C_ projection join/base + as-projection-without-BO (§32.6k)'),
        ('check_reuse_gate.py', 'WARNING',
         'CBO reuse gate: repo-local duplicate + ortak ZSD000 VH reuse (ADR 0009)'),
        ('check_released_objects.py', 'WARNING',
         'Clean Core: non-released std tablo → released successor öner (MARA->I_Product)'),
        ('check_standard_table_fields.py', 'WARNING',
         'Std tablo alanları yeni sistemde var mı (SAP GET; C-RAP-VE-03)'),
    ],
    'rap_bdef_creation': [
        # Managed BDEF — optimistic locking (etag) + lock master zorunlu (gap-analysis #16).
        ('check_rap_managed_etag.py', 'BLOCKER',
         'Managed RAP: lock master + etag master (LAST_CHANGED_AT) eksik mi'),
        ('check_audit_fields_autofill.py', 'WARNING',
         'Audit alanları (created/changed by-at) var ama setAdmin determination yok (std 05 §9A)'),
        ('check_bdef_backtick.py', 'BLOCKER',
         'bdef yorumunda ters-tırnak → SAP çoğaltıyor (repo 2→canlı 8); sessiz+büyüyen drift (BE-62)'),
        # Diğer BDEF kontrolleri (C-RAP-BD-*) checklist + manual.
    ],
    'rap_service_binding': [
        # Service Definition/Binding/Publish — make-or-break, deterministik
        # validator yok. Manual + checklist C-RAP-SB-* (publish AI-otonom kanıtı).
    ],
    # ─── ITG S2 sign-off (ADR 0022, Faz-1) ── artifact = intake-artefaktı .md ──
    'itg_s2_signoff': [
        ('check_itg_signoff.py', 'BLOCKER',
         'S2 kapsamlı iş: intake-artefaktı tam (KAPSAM/etkilenen-obje/prior-art/kabul-kriteri) '
         '+ kullanıcı MUTABAKAT [x] var mı (ADR 0022; SAP-yazma öncesi)'),
    ],
}

# Checklist dosyaları (manuel/LLM tarafından okunması gereken ek kontroller)
TASK_CHECKLISTS = {
    'cds_creation': 'playbook/checklists/cds-creation.md',
    'cds_update': 'playbook/checklists/cds-creation.md',
    'struct_creation': 'playbook/checklists/struct-creation.md',
    'table_creation': 'playbook/checklists/table-update.md',
    'table_update': 'playbook/checklists/table-update.md',
    'rap_cds_creation': 'playbook/checklists/rap-creation.md',
    'rap_bdef_creation': 'playbook/checklists/rap-creation.md',
    'rap_service_binding': 'playbook/checklists/rap-creation.md',
    'itg_s2_signoff': 'playbook/checklists/itg-s2-signoff.md',
}


# Repo-geneli tarayıcılar: <source_root>/** üzerinde kendileri os.walk yapar, POZİSYONEL artifact
# KABUL ETMEZ (argparse yalnız --strict/--quick). run_validator bunlara artifact GEÇMEZ
# (yoksa "unrecognized arguments" → crash → sahte BLOCKER). Gate korunur: check yine
# repo-geneli (yeni artifact da ERP içinde olduğundan kapsanır) çalışır + gate'ler.
REPO_WIDE_SCANNERS = {
    # (T1.12, 2026-07-31: check_amdp_comment_apostrophe ÇIKARILDI — artık pozisyonel
    #  tek-artifact kabul ediyor; push-anı yalnız push edilen dosyayı tarar, repo-geneli
    #  tarama run_all+CI katmanında sürer. Boş küme meşru — mekanizma yeni üye için durur.)
}


def sonuc_kaydi(validator: str, severity: str, status: str, description: str,
                stdout: str = '', stderr: str = '', message: str = '',
                olcum_yok: bool = False) -> dict:
    """Zincir-sonucu kaydını TEK yerden üret — her kayıt AYNI anahtar kümesini taşır.

    ⛔ SINIF-FIX (2026-08-01, KAYIT S1): SKIP dalı elle kurulmuş bir sözlük döndürüyordu
    ve `stdout`/`stderr` anahtarları YOKTU. Raporlama döngüsü (`elif r['stdout']`) o kaydı
    okuyunca `KeyError: 'stdout'` → süreç çöktü → **VERDICT satırı HİÇ BASILMADI** (exit 1
    ile ayırt edilemez bir "BLOCKER"). Kod yorumu "← KeyError fix" diyordu ama fix eksikti:
    kayda yalnız `description` eklenmişti. Tek-üretici kalıbı bu sınıfı yapısal kapatır —
    yeni bir durum eklendiğinde de anahtar kümesi bozulamaz.
    """
    return {
        'validator': validator,
        'severity': severity,
        'status': status,          # PASS | FAIL | SKIP
        'description': description,
        'stdout': stdout,
        'stderr': stderr,
        'message': message,        # SKIP sebebi (koşmadıysa NEDEN koşmadı)
        # ⛔ SKIP'in İKİ AYRI KÖKENİ VARDIR ve `--cevrimdisi` YALNIZ BİRİNİ indirir:
        #   olcum_yok=True  → gate KOŞTU, exit 0 verdi ama `measured=false` dedi
        #                     ("SAP'ye ulaşamadım") → çevrimdışı modda WARNING'e iner.
        #   olcum_yok=False → gate'in DOSYASI YOK (silinmiş/kurulmamış) → ASLA inmez.
        # İkisini birleştirmek 2026-08-01 S2 dersini geri açardı: "gate'i SİLMEK, onu
        # geçmenin en kolay yolu". Çevrimdışı olmak bir gate'in kaybolmasını affetmez.
        'olcum_yok': olcum_yok,
    }


def run_validator(script_path: Path, artifact: str | None, extra_args: list[str]) -> tuple[int, str, str]:
    """Validator script'ini çalıştır, (exit_code, stdout, stderr) döner.

    artifact=None → pozisyonel artifact geçilmez (repo-geneli tarayıcılar için)."""
    cmd = [sys.executable, str(script_path)] + ([artifact] if artifact else []) + extra_args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=60)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 2, '', f'TIMEOUT: {script_path.name} 60s aşıldı'
    except Exception as e:
        return 2, '', f'EXCEPTION: {script_path.name}: {e}'


# ── IX-GATE-STATUS SÖZLEŞMESİ — TÜKETİCİ UCU (2026-08-29, kayıt #5③) ──────────────
# ÜRETİCİ ucu AYRI dosyadadır (`check_abaplint.py`, 2026-08-29'da eklendi) ve şu tek
# satırı stdout'a basar:
#
#   IX-GATE-STATUS: gate=<ad> status=<OK|FINDING|SKIPPED|FAIL> measured=<true|false> reason=<slug>
#
# SORUN (ölçüldü): burada `status = 'PASS' if rc == 0 else 'FAIL'` yazıyordu. Üretici
# tarafta `exit 0`'ın ÜÇ ayrı anlamı var — "ölçtüm, temiz" · "config yok" · "bu obje
# tipini koşturamıyorum" · "npx yok" — ve üçü de burada `PASS` olarak kaydediliyordu.
# Yani sözleşmenin iki ucu vardı ama BİRBİRİNE DEĞMİYORDU: "koşturamadım" ile "temiz"
# reviewer için AYNI olaydı ("gate'lenmemiş kural ≈ kuralsız").
#
# ⛔ ÇIKIŞ KODU DEĞİŞTİRİLMEDİ (ne burada ne üreticide): üreticinin `return 0`'ı
#    gerekçeli bir karardır (offline reviewer zinciri kırılmasın). Tek taraflı
#    değiştirmek her offline class push'unda yeni bir WARNING üretirdi. Ayırt
#    edilebilirlik ÇIKIŞ KODUNA değil, bu AYRI KANALA dayanır.
#
# SÖZLEŞME JENERİKTİR: `gate=` alanı vardır çünkü ileride başka gate'ler de aynı satırı
# basacak. Aynı aile ÖLÇÜLDÜ (2026-08-29): `check_cds_srvd_comment_syntax` ·
# `check_standard_table_fields` ("SAP bağlantısı kurulamadı → return 0"). Onlar bu turda
# DEĞİŞTİRİLMEDİ; satırı basmaya başladıkları gün bu ayrıştırıcı onları da karşılar.
# (`check_cds_currency_reference` zaten rc=2 sözleşmesi taşır — ayrı ve iyi bir örnek.)
#
# ⚠ MARKÖRÜ TARİF EDEN METİN BEYAN SAYILMAZ — iki ayrı çapa:
#   ① satır-başı çapası (`^`, re.M) → yorum/docstring içindeki girintili örnekler elenir;
#   ② `measured=(true|false)` TAM eşleşme → sözleşmeyi ANLATAN `measured=<true|false>`
#      şablon metni (üreticinin kendi docstring'i) beyan sanılmaz.
_GATE_DURUM_RE = re.compile(
    r'^IX-GATE-STATUS:\s+gate=(?P<gate>\S+)\s+status=(?P<status>\S+)\s+'
    r'measured=(?P<measured>true|false)\s+reason=(?P<reason>\S+)\s*$', re.M)


def gate_durum_beyani(stdout: str, script_name: str) -> dict | None:
    """stdout'taki IX-GATE-STATUS beyanı (yoksa None → BUGÜNKÜ davranış korunur).

    Birden çok beyan varsa: önce `gate=` alanı KOŞAN script'in adıyla eşleşenler
    süzülür (bir validator başka bir gate'in çıktısını iletiyorsa yabancı beyan
    okunmasın), eşleşen yoksa SON beyan alınır (script'in nihai sözü). İki dal da
    korpusta ayrı ayrı ölçülür — ölü dal bırakılmaz.
    """
    beyanlar = [m.groupdict() for m in _GATE_DURUM_RE.finditer(stdout or '')]
    if not beyanlar:
        return None
    kendi = [b for b in beyanlar if b['gate'] == Path(script_name).stem]
    return (kendi or beyanlar)[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description='Reviewer Agent Orchestrator')
    parser.add_argument('--task', required=True, choices=list(TASK_VALIDATORS.keys()),
                        help='Görev tipi')
    parser.add_argument('--artifact', required=True, help='İncelenecek dosya path')
    parser.add_argument('--json', action='store_true', help='JSON çıktı (programatik)')
    parser.add_argument('--strict', action='store_true', help='WARNING\'i de BLOCKER say')
    parser.add_argument('--cevrimdisi', action='store_true',
                        help='BİLİNÇLİ ÇEVRİMDIŞI BEYANI: SAP\'ye ulaşamayan gate\'lerin '
                             '(measured=false) BLOCKER\'ı WARNING\'e iner. Gerçek bulgular '
                             've dosyası olmayan gate\'ler ETKİLENMEZ. Env: IX_CEVRIMDISI=1')
    parser.add_argument('--ack-drop', default='',
                        help='Onaylı tablo DROP alanları (virgülle) — check_table_field_drop\'a '
                             'iletilir. SADECE adı verilen alanlar ACK-WARNING; isimsiz drop/tip '
                             'değişikliği yine BLOCKER. Kullanıcı+lider bilinçli onayı (ADR 0005-B).')
    args = parser.parse_args()

    # ⛔ OTOMATİK ÇIKARIM YOK (bilinçli): `.conn_adt` yokluğuna BAKMIYORUZ. Kullanıcının
    # `.conn_adt`'si VARdır ve yalnız VPN kapalıdır; yokluktan çıkarım tam da TEHLİKELİ
    # vakayı ("bağlıyım sanıyorum ama ölçmedim") sessizce affederdi. Niyet AÇIK olmalı.
    cevrimdisi = args.cevrimdisi or os.environ.get('IX_CEVRIMDISI', '') == '1'

    artifact_path = Path(args.artifact)
    if not artifact_path.exists():
        print(f'HATA: {artifact_path} bulunamadı', file=sys.stderr)
        return 2

    validators = TASK_VALIDATORS.get(args.task, [])
    # ⛔ Q238 (2026-09-04) — BOŞ ZİNCİR: HÜKÜM DEĞİŞMEDİ, GÖRÜNÜRLÜK EKLENDİ.
    # "Koşacak gate yok" BİLİNÇLİ ve KAYITLI bir boşluktur (modül docstring'i;
    # `dtel_update` · `rap_service_binding`) ⇒ verdict `PASS` + exit 0 BİT-BAZINDA
    # KORUNUR (`reviewer_skip_sozlesmesi` V6 bunu çiviler; bozmak meşru push'ları
    # bloklardı — "kayıtsız eksiklik ≠ kayıtlı boşluk").
    # KUSUR HÜKÜMDE DEĞİL, OKUNUŞTAYDI: bu uyarı YALNIZ stderr'e gidiyordu, `PASS`
    # hükmü ise stdout'a ⇒ iki akışı AYRI yakalayan okuyucu (ajan/log/rapor) yalnız
    # "VERDICT: PASS" + "✓ COORDINATOR: PASS" görüyordu (ölçüldü 2026-09-03: SRVD
    # `rap_service_binding` koşumu). Bayrak artık rapor GÖVDESİNE (stdout) da basılır
    # ve JSON'da `zincir_bos` alanı olarak taşınır.
    zincir_bos = not validators
    if zincir_bos:
        print(f'UYARI: {args.task} için validator zinciri tanımlı değil. '
              f'Manual review gereklidir.', file=sys.stderr)

    # Validator zincirini çalıştır
    results = []
    for script_name, default_severity, description in validators:
        # Arama sırası (2026-07-10 düzeltmesi): önce core VALIDATORS_DIR, sonra PROJE
        # scripts/validators-local/. Eskiden yalnız core'a bakılıyordu → proje-lokal
        # validator'lar (ör. check_td_cancelled_fields.py) HER ZAMAN 'bulunamadı' SKIP
        # veriyordu ve SKIP verdict'e sayılmadığı için sahte-PASS üretiyordu.
        script_path = VALIDATORS_DIR / script_name
        if not script_path.exists():
            lokal = PROJ_ROOT / "scripts" / "validators-local" / script_name
            if lokal.exists():
                script_path = lokal
        if not script_path.exists():
            results.append(sonuc_kaydi(
                script_name, default_severity, 'SKIP', description,
                message=f'PRE-FLIGHT KOŞMADI: {script_name} core+validators-local '
                        f'hiçbirinde YOK (aranan: {VALIDATORS_DIR} ve '
                        f'{PROJ_ROOT / "scripts" / "validators-local"}) — PASS SANMA.'))
            continue

        # Tablo tipi için --type table extra arg
        extra_args = []
        if args.task in ('table_creation', 'table_update') and 'cds_currency' in script_name:
            extra_args = ['--type', 'table']
        # Onaylı DROP bayrağı yalnız drop-guard'a iletilir (hedefli ack)
        if script_name == 'check_table_field_drop.py' and args.ack_drop:
            extra_args = extra_args + ['--ack-drop', args.ack_drop]

        # Repo-geneli tarayıcılar (kendileri <source_root>/** os.walk eder) pozisyonel artifact KABUL ETMEZ
        # → artifact=None geç (yoksa "unrecognized arguments" → sahte BLOCKER).
        review_artifact = None if script_name in REPO_WIDE_SCANNERS else args.artifact
        rc, out, err = run_validator(script_path, review_artifact, extra_args)
        # IX-GATE-STATUS tüketimi (kayıt #5③) — YALNIZ `rc == 0` dalında sorulur.
        # Gerekçe (kapsam niteleyicisi): `rc != 0` zaten GÜRÜLTÜLÜ bir sonuçtur (FAIL,
        # verdict'e sayılır) — orada "ölçüldü mü" sorusu sessizlik üretmez. Sessiz olan
        # tek yol `exit 0`'dır ve düzeltilen sınıf odur. `rc != 0` davranışı BİT-BAZINDA
        # korunur; genişletmek ayrı bir karardır (ölçülmedi ⇒ yapılmadı).
        beyan = gate_durum_beyani(out, script_name) if rc == 0 else None
        if beyan is not None and beyan['measured'] == 'false':
            # "Koşmadı" ≠ "temiz" — S2 sözleşmesinin AYNISI, tek farkla: orada gate'in
            # DOSYASI yoktu, burada dosya vardı ama ÖLÇÜM yapılmadı. İkisi de SKIP'tir
            # ve SKIP kendi şiddetiyle verdict'e sayılır (bkz. modül docstring'i).
            # check_abaplint WARNING sınıfı olduğu için sonuç WARNING'dir, BLOCKER DEĞİL.
            status = 'SKIP'
            olcum_yok = True
            mesaj = (f"PRE-FLIGHT ÖLÇMEDİ: {script_name} koştu ve exit 0 döndü ama "
                     f"IX-GATE-STATUS satırı `measured=false` diyor "
                     f"(status={beyan['status']}, reason={beyan['reason']}) — "
                     f"bu 'temiz' DEĞİLDİR, PASS SANMA.")
        else:
            status = 'PASS' if rc == 0 else 'FAIL'
            mesaj = ''
            olcum_yok = False
        results.append(sonuc_kaydi(script_name, default_severity, status, description,
                                   stdout=out.strip(), stderr=err.strip(), message=mesaj,
                                   olcum_yok=olcum_yok))

    # ── Verdict ───────────────────────────────────────────────────────────────
    # ⛔ SKIP VERDICT'E SAYILIR (2026-08-01, KAYIT S2 — S1 ile AYNI kök: SKIP yolunun
    # sözleşmesi). Eskiden yalnız 'FAIL' sayılıyordu: BLOCKER olarak sınıflandırılmış bir
    # gate'in DOSYASI YOKSA (silinmiş / proje-lokal ama kurulmamış / adı değişmiş) zincir
    # sessizce atlanıyor ve VERDICT 'PASS' + exit 0 → "✓ COORDINATOR: PASS, devam
    # edebilirsin" yazıyordu. Yani gate'i SİLMEK, onu geçmenin en kolay yoluydu.
    # "Koşmadı" ≠ "temiz" (bulunamadı ≠ yok): eksik BLOCKER = BLOCKER, eksik WARNING =
    # WARNING. blocker_count/warning_count TOPLAM'dır (FAIL + SKIP); ayrıntı için
    # skipped_* alanları eklendi (tüketiciler: MCP _reviewer → atom.py/composite.py rapor).
    failed_blocker = sum(1 for r in results if r['status'] == 'FAIL' and r['severity'] == 'BLOCKER')
    failed_warning = sum(1 for r in results if r['status'] == 'FAIL' and r['severity'] == 'WARNING')
    skipped_blocker = sum(1 for r in results if r['status'] == 'SKIP' and r['severity'] == 'BLOCKER')
    skipped_warning = sum(1 for r in results if r['status'] == 'SKIP' and r['severity'] == 'WARNING')
    # ── Q239 (2026-09-04) — SESSİZ BULGU: gate KOŞTU, ÖLÇTÜ, BULGU BASTI ama rc=0 ────
    # `status == 'PASS'` + `stderr` DOLU. Bu SKIP DEĞİLDİR (ölçüm yapıldı) ve FAIL de
    # değildir (gate kendi sözleşmesinde "sadece WARNING → rc 0" diyor). Bugüne kadar
    # raporlama döngüsü PASS dalında stderr'i HİÇ OKUMUYORDU ⇒ `✓ [BLOCKER] gate` satırı
    # altında 3 bulgu SESSİZCE yutuluyordu (ölçüldü: `check_cds_currency_reference`,
    # tüketici projede bir CDS → 3 ihlal, `run_review` çıktısında SIFIR satır).
    # ⛔ VERDICT ARİTMETİĞİNE GİRMEZ (bilinçli, ADR 0019 moratoryumu): şiddet-etiketi ile
    # çıkış-kodu sözleşmesini hizalamak AYRI bir karardır (Q239③). Burada YALNIZ bilgi
    # eklenir — hiçbir koşum sınıf değiştirmez, hiçbir exit kodu değişmez.
    sessiz_bulgular = [r for r in results if r['status'] == 'PASS' and r['stderr']]
    # ── ÇEVRİMDIŞI İNDİRİMİ (opt-in) ──────────────────────────────────────────
    # Yalnız ÖLÇÜM ÜRETMEYEN (measured=false) BLOCKER'lar iner. `failed_blocker`
    # (gate koştu, ÖLÇTÜ ve İHLAL BULDU) bu satırların HİÇBİRİNDE geçmez ⇒ gerçek
    # bulgu bayrakla asla WARNING'e düşemez. Sayaçlar KAYBOLMAZ: `skipped_blocker`
    # TOPLAM olarak JSON'da ve ekranda aynen kalır.
    indirilen = [r for r in results
                 if r['status'] == 'SKIP' and r['severity'] == 'BLOCKER'
                 and r.get('olcum_yok')] if cevrimdisi else []
    indirilen_ad = [r['validator'] for r in indirilen]

    blocker_count = failed_blocker + skipped_blocker - len(indirilen)
    warning_count = failed_warning + skipped_warning + len(indirilen)

    if blocker_count > 0:
        verdict = 'BLOCKER'
    elif warning_count > 0:
        verdict = 'WARNING'
    else:
        verdict = 'PASS'

    if args.strict and warning_count > 0:
        verdict = 'BLOCKER'

    # Checklist referansı
    checklist = TASK_CHECKLISTS.get(args.task)

    # JSON output (programatik)
    if args.json:
        output = {
            'timestamp': datetime.now().isoformat(),
            'task': args.task,
            'artifact': str(artifact_path),
            'verdict': verdict,
            # TOPLAM (FAIL + SKIP) — verdict'i süren sayılar. Ayrıntı aşağıda:
            'blocker_count': blocker_count,
            'warning_count': warning_count,
            'failed_blocker_count': failed_blocker,
            'failed_warning_count': failed_warning,
            'skipped_blocker_count': skipped_blocker,
            'skipped_warning_count': skipped_warning,
            # Çevrimdışı beyanı: tüketici kapsamın EKSİK olduğunu bilmeli.
            'cevrimdisi': cevrimdisi,
            'offline_downgraded_count': len(indirilen),
            'offline_downgraded_gates': indirilen_ad,
            # ⚠ KAPSAM GENİŞLETİLDİ (2026-09-04, Q238): boş zincir de "kapsam eksik"tir —
            # HİÇBİR gate koşmadıysa bu koşumun kapsamı sıfırdır. Alanın anlamı aynı
            # kalır ("bu koşum eksik ölçtü"), kaynağı `zincir_bos` ile ayırt edilir.
            'kapsam_eksik': bool(indirilen) or zincir_bos,
            # Q238 — bilinçli boşluk MAKİNECE de okunabilir olsun (verdict PASS kalır).
            'zincir_bos': zincir_bos,
            'kosan_gate_sayisi': len(results),
            # Q239 — rc=0 döndüğü için PASS sayılan ama BULGU BASAN gate'ler.
            # ⛔ Verdict'e SAYILMAZ (görünürlük kalemi); tüketici kendi kararını verir.
            'sessiz_bulgu_count': len(sessiz_bulgular),
            'sessiz_bulgu_gates': [r['validator'] for r in sessiz_bulgular],
            'checklist_reference': checklist,
            'results': results,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        # Human-readable
        print(f'\n{"="*70}')
        print(f'REVIEWER REPORT — {args.task}')
        print(f'Artifact: {artifact_path}')
        print(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        print(f'{"="*70}\n')

        # ⛔ GÖRÜNÜRLÜK SÖZLEŞMESİ (Q239, 2026-09-04): "bir gate'in ÜRETTİĞİ hiçbir metin
        # bu döngüde SESSİZCE DÜŞMEZ." Eski döngü ÜÇ yerde metin düşürüyordu:
        #   ① PASS + stderr DOLU        → stderr HİÇ okunmuyordu (Q239'un ölçülmüş vakası)
        #   ② FAIL + stderr BOŞ         → stdout'a düşülmüyordu ⇒ `✗` satırı GEREKÇESİZ
        #   ③ PASS + çok satırlı stdout → yalnız İLK satır (kapsam/paydaş satırları düşer)
        # Üçü de AYNI sınıf: "kapı konuştu, rapor duymadı". ⚠ Hiçbiri verdict/exit
        # değiştirmez — bilgi eklenir, hüküm eklenmez.
        for r in results:
            sessiz_bulgu = r['status'] == 'PASS' and bool(r['stderr'])
            # `~` = ÜÇÜNCÜ İŞARET: "koştu, ölçtü, BULGU var ama rc=0". `✓` (temiz) ile
            # `✗` (düştü) arasındaki bu boşluk okuyucuyu yanıltan tam yerdi.
            symbol = ('~' if sessiz_bulgu else
                      '✓' if r['status'] == 'PASS' else
                      ('✗' if r['status'] == 'FAIL' else '⊘'))
            print(f"{symbol} [{r['severity']}] {r['validator']}")
            print(f"  {r['description']}")
            if r['status'] == 'FAIL':
                # stderr ÖNCELİKLİ; BOŞSA stdout'a düş (② — gerekçesiz `✗` bırakma).
                for line in (r['stderr'] or r['stdout']).splitlines():
                    print(f"    {line}")
            elif r['status'] == 'SKIP':
                # Görünürlük şartı (B10 reçetesi): koşmayan gate SESSİZ kalmaz.
                print(f"    {r['message']}")
            else:
                if r['stdout']:
                    for line in r['stdout'].splitlines():   # ③ kırpma YOK
                        print(f"    {line}")
                if sessiz_bulgu:                            # ① asıl Q239 düzeltmesi
                    print(f"    ~ EXIT 0 AMA BULGU BASTI ({len(r['stderr'].splitlines())} "
                          f"satır, stderr) — bu 'temiz' DEĞİLDİR; verdict'e SAYILMAZ, "
                          f"OKU ve kendin karar ver:")
                    for line in r['stderr'].splitlines():
                        print(f"    {line}")
            print()

        if zincir_bos:
            # Q238 — hüküm (PASS/exit 0) korunur, SESSİZLİK kaldırılır.
            print(f'⊘ [KAPSAM] {args.task}: VALIDATOR ZİNCİRİ TANIMLI DEĞİL — '
                  f'bu koşumda HİÇBİR gate çalışmadı.')
            print('  Bu, KAYITLI ve bilinçli bir boşluktur (gate yok ⇒ verdict PASS '
                  'kalır), ama "PASS" burada "ölçüldü ve temiz" DEMEK DEĞİLDİR:')
            print('  "ölçülecek gate yok" demektir. Manuel review + checklist ZORUNLU.')
            print()

        print(f'{"="*70}')
        # Q238: hüküm satırı KENDİ kapsamını taşır (değer `PASS` olarak KALIR).
        print(f'VERDICT: {verdict}' + ('  (ZİNCİR YOK — hiçbir gate koşmadı; '
                                       'ölçüm YAPILMADI)' if zincir_bos else ''))
        # ⚠ Aritmetik GÖRÜNÜR olmalı: çevrimdışı indirimi BLOCKER'dan düşüp WARNING'e
        # eklediği için, indirimi yazmadan "BLOCKERS: 0 (… + KOŞMAYAN 1)" çelişkili okunur.
        _b_ek = ''
        if skipped_blocker:
            _b_ek = f'  (koşan-FAIL {failed_blocker} + KOŞMAYAN {skipped_blocker}'
            _b_ek += (f' − ÇEVRİMDIŞI-İNDİRİMİ {len(indirilen)})' if indirilen else ')')
        print(f'  BLOCKERS: {blocker_count}' + _b_ek)
        _w_ek = ''
        if skipped_warning or indirilen:
            _w_ek = f'  (koşan-FAIL {failed_warning} + KOŞMAYAN {skipped_warning}'
            _w_ek += (f' + ÇEVRİMDIŞI-İNDİRİMİ {len(indirilen)})' if indirilen else ')')
        print(f'  WARNINGS: {warning_count}' + _w_ek)
        if sessiz_bulgular:
            # Q239: sayaç `BLOCKERS/WARNINGS` satırlarına KARIŞMAZ — ayrı satır, ayrı
            # işaret. Karıştırmak verdict aritmetiğini değiştirmek olurdu.
            print(f'  ~ {len(sessiz_bulgular)} gate exit 0 döndü AMA BULGU BASTI '
                  f'(yukarıda `~` işaretli): '
                  f'{", ".join(r["validator"] for r in sessiz_bulgular)} — '
                  f'"exit 0" ≠ "temiz"; verdict\'e SAYILMAZ, sen oku.')
        if skipped_blocker or skipped_warning:
            print(f'  ⊘ {skipped_blocker + skipped_warning} gate ÖLÇÜM ÜRETMEDİ '
                  f'(script yok VEYA measured=false) — "koşmadı" ≠ "temiz". '
                  f'Sebep her ⊘ satırının altında yazılıdır.')
        if cevrimdisi:
            print(f'\n  ⚠⚠ ÇEVRİMDIŞI MOD (--cevrimdisi / IX_CEVRIMDISI=1) — '
                  f'BU KOŞUMUN KAPSAMI EKSİKTİR.')
            if indirilen:
                print(f'     {len(indirilen)} BLOCKER gate ölçüm üretemedi ve '
                      f'BİLİNÇLİ olarak WARNING\'e indirildi:')
                for ad in indirilen_ad:
                    print(f'       - {ad}')
                print(f'     Bu gate\'ler SAP\'ye ulaşamadı; ihlal YOK demek DEĞİLDİR. '
                      f'Bağlantı gelince review\'i TEKRARLA.')
            else:
                print('     (indirilen gate yok — ölçüm üretemeyen BLOCKER bulunmadı)')
        if checklist:
            print(f'\nManuel checklist (ek kontrol için): {checklist}')
        print(f'{"="*70}\n')

        if verdict == 'BLOCKER':
            print('⛔ COORDINATOR: SAP yazma YASAK. Düzelt ve tekrar review iste.\n',
                  file=sys.stderr)
        elif verdict == 'WARNING':
            print('⚠ COORDINATOR: Yazabilirsin ama kullanıcıya bildir.\n', file=sys.stderr)
        elif zincir_bos:
            # Q238 — en yanıltıcı satır TAM BURASIYDI: ölçüm yokken "PASS, devam
            # edebilirsin" stdout'a basılıyordu. Hüküm (exit 0) aynı, cümle dürüst.
            print('⊘ COORDINATOR: ÖLÇÜM YAPILMADI (bu görev tipinde validator zinciri '
                  'yok) — devam edebilirsin ama bu bir "kapıdan geçti" DEĞİLDİR; '
                  'manuel review + checklist senin sorumluluğunda.\n')
        else:
            print('✓ COORDINATOR: PASS, devam edebilirsin.\n')

    return 1 if verdict == 'BLOCKER' else 0


if __name__ == '__main__':
    sys.exit(main())
