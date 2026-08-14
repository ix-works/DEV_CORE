"""
check_abaplint.py — ABAP class/program source'unu abaplint (tuned config) ile lint eder.
class_push reviewer zincirinde WARNING (gürültüsüz: yapısal/mantık + hijyen; parser_error,
unreachable_code, identical_conditions, empty_statement, contains_tab...).

KAPSAM: class (.clas.abap / "CLASS ... DEFINITION") + program (.prog.abap). FM/diğer → SKIP
(abaplint function-group layout ister; otoriter syntax zaten adt_syntax_check'te).
abaplint yoksa (npx/offline) → SKIP (reviewer'ı kırma).

Config: scripts/abaplint/abaplint.json (check_syntax/keyword_case/7bit_ascii KAPALI — bkz config _comment).

Kullanım: python scripts/validators/check_abaplint.py <artifact.clas.abap> [--strict]
Exit: 0 temiz/skip · 1 en az 1 lint bulgusu VEYA ÖLÇÜM YAPILAMADI (chain'de WARNING → bloklamaz)

⛔ FAIL-OPEN KİLİDİ (2026-08-14): "temiz" verdict'i yalnız abaplint'in KENDİ özet satırı
(`N issue(s) found, M file(s) analyzed`, M≥1) görüldüğünde verilir. Özet yoksa / 0 dosya
analiz edildiyse / özetteki sayı ayrıştırdığımızla tutmuyorsa → FAIL. Öncesinde bu kod
"bulgu satırı görmedim" ile "temiz"i aynı sayıyordu ve aynı bozuk dosya için iki farklı
verdict verebiliyordu (bkz SUMMARY_RE bloğu). `exit 0` + "SKIP" metni = ölçülmedi, ≠ temiz.
"""
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path

if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

CONFIG = Path(__file__).resolve().parents[1] / 'abaplint' / 'abaplint.json'

# Sürüm PİNLİ (2026-07-26). Pin'siz `@abaplint/cli` her koşumda upstream latest'i çeker →
# lint davranışı bizden habersiz değişir (upstream'de 2 haftada 43 commit) + tedarik-zinciri
# yüzeyi. Bump = BİLİNÇLİ karar: burayı güncelle, bir class/program üzerinde koş, farkı gör.
# Fetch edilemezse (offline/cache yok) aşağıdaki except → SKIP (reviewer kırılmaz, mevcut davranış).
ABAPLINT_PIN = '@abaplint/cli@2.120.5'
ISSUE_RE = re.compile(r'^(.*\.abap)\[(\d+),\s*(\d+)\]\s*-\s*(.+?)\s*\(([a-z_]+)\)\s*\[[EWI]\]\s*$')

# ⛔ FAIL-OPEN KİLİDİ (2026-08-14) — "bulgu satırı görmedim" ≠ "temiz".
# Vaka: aynı BOZUK dosya için bir koşumda `exit 0 "temiz"`, ikincisinde `exit 1 parser_error`
# alındı. Sebep: ISSUE_RE'ye uyan satır yoksa kod KOŞULSUZ "temiz" diyordu — npx soğuk-başlatma,
# ağ hatası, sürüm-fetch gürültüsü ya da abaplint'in çıktı biçimini değiştirmesi hâlinde
# ÖLÇÜM YAPILMAMIŞ olmasına rağmen yeşil dönüyordu (returncode'a da hiç bakılmıyordu).
# Çare: abaplint'in KENDİ özet satırı zorunlu kanıt sayılır. Ölçüldü (2026-08-14, 2.120.5):
#   temiz  → stdout: 'abaplint: 0 issue(s) found, 1 file(s) analyzed'  rc=0
#   bozuk  → stdout: '<dosya>[42, 3] - ... (parser_error) [E]' + 'abaplint: 2 issue(s) found, 1 file(s) analyzed'  rc=1
# Özet yoksa / 0 dosya analiz edildiyse / özetteki sayı ile ayrıştırdığımız sayı tutmuyorsa
# → "temiz" DEME, FAIL ver. "Ölçemedim" ile "temiz" ASLA aynı çıkışa düşmez.
SUMMARY_RE = re.compile(
    r'^abaplint:\s*(\d+)\s*issue\(s\)\s*found,\s*(\d+)\s*file\(s\)\s*analyzed\s*$', re.M)


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
            r = subprocess.run(['npx', '--yes', ABAPLINT_PIN], cwd=str(tdp),
                               capture_output=True, text=True, timeout=180, shell=(sys.platform == 'win32'))
        except Exception as e:
            # ⚠ Bu SKIP "temiz" DEĞİLDİR — yalnız "koşturamadım"dır (offline/npx yok). Bilinçli
            # olarak exit 0 kalıyor ki offline reviewer zinciri kırılmasın; ama metin bunu ASLA
            # "temiz" diye okutmamalı. Ölçüm YAPILDIYSA sessiz-yeşil artık imkânsız (SUMMARY_RE kilidi).
            print(f'SKIP — abaplint KOŞTURULAMADI ({type(e).__name__}) → lint ÖLÇÜLMEDİ; '
                  '"temiz" anlamına GELMEZ (offline/npx yok?). Reviewer zinciri bilerek kırılmadı.')
            return 0
        out = (r.stdout or '') + (r.stderr or '')
        rc = r.returncode

    issues = []
    for line in out.splitlines():
        m = ISSUE_RE.match(line.strip())
        if m:
            issues.append((m.group(2), m.group(4), m.group(5)))  # line, msg, rule

    # ── FAIL-OPEN KİLİDİ: abaplint'in özet satırı ZORUNLU kanıttır (bkz SUMMARY_RE notu) ──
    sm = SUMMARY_RE.search(out)
    if not sm:
        print(f'\n--- {path.name} — abaplint ÖLÇÜLEMEDİ (C-ABLINT-FAILOPEN) ---', file=sys.stderr)
        print(f'  [FAIL] abaplint özet satırı ("N issue(s) found, M file(s) analyzed") ÇIKMADI '
              f'→ dosya analiz EDİLMEMİŞ olabilir. Bu "temiz" DEĞİLDİR (returncode={rc}).', file=sys.stderr)
        print(f'  Ham çıktı (son 400 kr): {out[-400:]!r}', file=sys.stderr)
        print('  Olası sebep: npx soğuk-başlatma/ağ · pin fetch edilemedi · abaplint çıktı biçimi değişti '
              '(SUMMARY_RE güncellenmeli). Tekrar koş; ısrar ederse ÖNCE bunu çöz, sonucu "temiz" sayma.',
              file=sys.stderr)
        return 1

    said_issues, files_analyzed = int(sm.group(1)), int(sm.group(2))
    if files_analyzed < 1:
        print(f'\n--- {path.name} — abaplint HİÇBİR DOSYA ANALİZ ETMEDİ (C-ABLINT-FAILOPEN) ---', file=sys.stderr)
        print(f'  [FAIL] özet "0 file(s) analyzed" diyor → lint fiilen koşmadı; "temiz" DEĞİLDİR. '
              f'(src/ yerleşimi ya da config kapsamı bozuk olabilir; returncode={rc})', file=sys.stderr)
        return 1
    if said_issues != len(issues):
        print(f'\n--- {path.name} — abaplint ÇIKTI AYRIŞTIRMA UYUŞMAZLIĞI (C-ABLINT-FAILOPEN) ---', file=sys.stderr)
        print(f'  [FAIL] abaplint "{said_issues} issue" diyor, biz {len(issues)} satır ayrıştırabildik '
              '→ ISSUE_RE çıktı biçimiyle DESYNC. Ayrıştıramadığımız bulgular sessizce kaybolurdu.',
              file=sys.stderr)
        print(f'  Ham çıktı (son 800 kr): {out[-800:]!r}', file=sys.stderr)
        return 1

    if not issues:
        print(f'OK — {path.name} abaplint temiz (tuned; {said_issues} issue / {files_analyzed} file(s) analyzed)')
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
