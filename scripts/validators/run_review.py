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

Kullanım:
    # CDS yaratma öncesi
    python scripts/validators/run_review.py --task cds_creation --artifact ERP/SD/ZSD001_CLC/cds/ZSD001_DDL_X.cds

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
import subprocess
import sys
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

VALIDATORS_DIR = Path(__file__).parent

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
    'dtel_update': [
        # DTEL update için spesifik validator henüz yok — manual review
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
        # Diğer BDEF kontrolleri (C-RAP-BD-*) checklist + manual.
    ],
    'rap_service_binding': [
        # Service Definition/Binding/Publish — make-or-break, deterministik
        # validator yok. Manual + checklist C-RAP-SB-* (publish AI-otonom kanıtı).
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
}


# Repo-geneli tarayıcılar: ERP/** üzerinde kendileri os.walk yapar, POZİSYONEL artifact
# KABUL ETMEZ (argparse yalnız --strict/--quick). run_validator bunlara artifact GEÇMEZ
# (yoksa "unrecognized arguments" → crash → sahte BLOCKER). Gate korunur: check yine
# repo-geneli (yeni artifact da ERP içinde olduğundan kapsanır) çalışır + gate'ler.
REPO_WIDE_SCANNERS = {
    'check_amdp_comment_apostrophe.py',
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


def main() -> int:
    parser = argparse.ArgumentParser(description='Reviewer Agent Orchestrator')
    parser.add_argument('--task', required=True, choices=list(TASK_VALIDATORS.keys()),
                        help='Görev tipi')
    parser.add_argument('--artifact', required=True, help='İncelenecek dosya path')
    parser.add_argument('--json', action='store_true', help='JSON çıktı (programatik)')
    parser.add_argument('--strict', action='store_true', help='WARNING\'i de BLOCKER say')
    parser.add_argument('--ack-drop', default='',
                        help='Onaylı tablo DROP alanları (virgülle) — check_table_field_drop\'a '
                             'iletilir. SADECE adı verilen alanlar ACK-WARNING; isimsiz drop/tip '
                             'değişikliği yine BLOCKER. Kullanıcı+lider bilinçli onayı (ADR 0005-B).')
    args = parser.parse_args()

    artifact_path = Path(args.artifact)
    if not artifact_path.exists():
        print(f'HATA: {artifact_path} bulunamadı', file=sys.stderr)
        return 2

    validators = TASK_VALIDATORS.get(args.task, [])
    if not validators:
        print(f'UYARI: {args.task} için validator zinciri tanımlı değil. '
              f'Manual review gereklidir.', file=sys.stderr)

    # Validator zincirini çalıştır
    results = []
    for script_name, default_severity, description in validators:
        script_path = VALIDATORS_DIR / script_name
        if not script_path.exists():
            results.append({
                'validator': script_name,
                'severity': default_severity,
                'status': 'SKIP',
                'message': f'Script {script_name} bulunamadı',
            })
            continue

        # Tablo tipi için --type table extra arg
        extra_args = []
        if args.task in ('table_creation', 'table_update') and 'cds_currency' in script_name:
            extra_args = ['--type', 'table']
        # Onaylı DROP bayrağı yalnız drop-guard'a iletilir (hedefli ack)
        if script_name == 'check_table_field_drop.py' and args.ack_drop:
            extra_args = extra_args + ['--ack-drop', args.ack_drop]

        # Repo-geneli tarayıcılar (kendileri ERP/** os.walk eder) pozisyonel artifact KABUL ETMEZ
        # → artifact=None geç (yoksa "unrecognized arguments" → sahte BLOCKER).
        review_artifact = None if script_name in REPO_WIDE_SCANNERS else args.artifact
        rc, out, err = run_validator(script_path, review_artifact, extra_args)
        status = 'PASS' if rc == 0 else 'FAIL'
        results.append({
            'validator': script_name,
            'severity': default_severity,
            'status': status,
            'description': description,
            'stdout': out.strip(),
            'stderr': err.strip(),
        })

    # Verdict hesapla
    blocker_count = sum(1 for r in results if r['status'] == 'FAIL' and r['severity'] == 'BLOCKER')
    warning_count = sum(1 for r in results if r['status'] == 'FAIL' and r['severity'] == 'WARNING')

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
            'blocker_count': blocker_count,
            'warning_count': warning_count,
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

        for r in results:
            symbol = '✓' if r['status'] == 'PASS' else ('✗' if r['status'] == 'FAIL' else '⊘')
            print(f"{symbol} [{r['severity']}] {r['validator']}")
            print(f"  {r['description']}")
            if r['status'] == 'FAIL':
                if r['stderr']:
                    for line in r['stderr'].splitlines():
                        print(f"    {line}")
            elif r['stdout']:
                first_line = r['stdout'].splitlines()[0] if r['stdout'] else ''
                print(f"    {first_line}")
            print()

        print(f'{"="*70}')
        print(f'VERDICT: {verdict}')
        print(f'  BLOCKERS: {blocker_count}')
        print(f'  WARNINGS: {warning_count}')
        if checklist:
            print(f'\nManuel checklist (ek kontrol için): {checklist}')
        print(f'{"="*70}\n')

        if verdict == 'BLOCKER':
            print('⛔ COORDINATOR: SAP yazma YASAK. Düzelt ve tekrar review iste.\n',
                  file=sys.stderr)
        elif verdict == 'WARNING':
            print('⚠ COORDINATOR: Yazabilirsin ama kullanıcıya bildir.\n', file=sys.stderr)
        else:
            print('✓ COORDINATOR: PASS, devam edebilirsin.\n')

    return 1 if verdict == 'BLOCKER' else 0


if __name__ == '__main__':
    sys.exit(main())
