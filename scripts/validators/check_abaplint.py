"""
check_abaplint.py — ABAP class/program source'unu abaplint (tuned config) ile lint eder.
class_push reviewer zincirinde WARNING (gürültüsüz: yapısal/mantık + hijyen; parser_error,
unreachable_code, identical_conditions, empty_statement, contains_tab...).

KAPSAM: class (.clas.abap / "CLASS ... DEFINITION") + program (.prog.abap). FM/diğer → SKIP
(abaplint function-group layout ister; otoriter syntax zaten adt_syntax_check'te).
abaplint yoksa (npx/offline) → SKIP (reviewer'ı kırma).

Config: scripts/abaplint/abaplint.json (check_syntax/keyword_case/7bit_ascii KAPALI — bkz config _comment).

Kullanım: python scripts/validators/check_abaplint.py <artifact.clas.abap> [--strict]
Exit: 0 temiz/skip · 1 en az 1 lint bulgusu (chain'de WARNING → bloklamaz)
"""
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path

if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

CONFIG = Path(__file__).resolve().parents[1] / 'abaplint' / 'abaplint.json'
ISSUE_RE = re.compile(r'^(.*\.abap)\[(\d+),\s*(\d+)\]\s*-\s*(.+?)\s*\(([a-z_]+)\)\s*\[[EWI]\]\s*$')


def detect(name: str, text: str):
    """(suffix, objname) veya (None, None) -> desteklenmiyor."""
    low = name.lower()
    if low.endswith('.clas.abap') or re.search(r'\bclass\s+\w+\s+definition', text, re.I):
        m = re.search(r'\bclass\s+(\w+)\s+definition', text, re.I)
        return '.clas.abap', (m.group(1).lower() if m else 'zcl_lint_probe')
    if low.endswith('.prog.abap') or re.search(r'^\s*report\s+\w+', text, re.I | re.M):
        m = re.search(r'^\s*report\s+(\w+)', text, re.I | re.M)
        return '.prog.abap', (m.group(1).lower() if m else 'zlint_probe')
    return None, None


def main() -> int:
    ap = argparse.ArgumentParser(description='abaplint (tuned) lint — class/program')
    ap.add_argument('artifact')
    ap.add_argument('--strict', action='store_true')
    args = ap.parse_args()

    path = Path(args.artifact)
    if not path.exists():
        print(f'HATA: {path} bulunamadı', file=sys.stderr); return 1
    if not CONFIG.exists():
        print(f'SKIP — abaplint config yok ({CONFIG})'); return 0

    text = path.read_text(encoding='utf-8', errors='replace')
    suffix, objname = detect(path.name, text)
    if not suffix:
        print(f'SKIP — abaplint class/program değil ({path.name}); FM/diğer için adt_syntax_check')
        return 0

    cfg = json.loads(CONFIG.read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        (tdp / 'src').mkdir()
        (tdp / 'src' / f'{objname}{suffix}').write_text(text, encoding='utf-8')
        (tdp / 'abaplint.json').write_text(json.dumps(cfg), encoding='utf-8')
        try:
            r = subprocess.run(['npx', '--yes', '@abaplint/cli'], cwd=str(tdp),
                               capture_output=True, text=True, timeout=180, shell=(sys.platform == 'win32'))
        except Exception as e:
            print(f'SKIP — abaplint çalıştırılamadı ({type(e).__name__}); offline? reviewer kırılmadı')
            return 0
        out = (r.stdout or '') + (r.stderr or '')

    issues = []
    for line in out.splitlines():
        m = ISSUE_RE.match(line.strip())
        if m:
            issues.append((m.group(2), m.group(4), m.group(5)))  # line, msg, rule
    if not issues:
        print(f'OK — {path.name} abaplint temiz (tuned)')
        return 0

    print(f'\n--- {path.name} — {len(issues)} abaplint bulgusu (tuned) ---', file=sys.stderr)
    parser_errs = [(ln, msg) for ln, msg, rule in issues if rule == 'parser_error']
    for ln, msg, rule in issues:
        if rule == 'parser_error':
            # parser_error'ı jenerik WARNING olarak GÖMME: modern-syntax (EML/RAP/source-based)
            # class'ta abaplint desync olur ve GERÇEK save/aktivasyon hatalarını (string-template
            # escape BE-47, METHODS param sırası BE-48) parser_error olarak gösterir. Kör
            # false-positive sayma → CANLI adt_syntax_check ile DOĞRULA (bug-checklist BE-36/47/48).
            print(f'  [DOĞRULA-CANLI] line {ln} (C-ABLINT parser_error — GERÇEK OLABİLİR): {msg}', file=sys.stderr)
        else:
            print(f'  [WARNING] line {ln} (C-ABLINT): {msg} ({rule})', file=sys.stderr)
    if parser_errs:
        print(f'    ⚠ {len(parser_errs)} parser_error VAR — modern-class ise abaplint desync gerçek hatayı '
              'gizleyebilir/kaydırabilir; "modern-ABAP false-positive" diye ELEME → CANLI adt_syntax_check '
              'ZORUNLU (bug-checklist BE-36/47/48; ZSD001 EXCUPL 2026-07-12).', file=sys.stderr)
    print('    Not: tuned kural seti (yapısal/mantık+hijyen). Otoriter syntax = adt_syntax_check.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
