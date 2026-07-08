"""
check_released_objects.py — Clean Core: CDS/ABAP source'ta non-released STANDART
tablo kullanımını (FROM/JOIN) yakalar ve released CDS successor önerir (MARA->I_Product).

⚠️ KAPSAM = yalnız TABLO→CDS (Clean Core ailelerinden 1'i). TÜM obje-tipi (class/IF/FM)
released-API kontrolü için OTORİTE yol = SAP yerel ATC "Usage of APIs" check'i
(`adt_atc_check`, S/4 2025+PCE; objectClassifications JSON). Dil-versiyonu / no-classic
aileleri BİZE UYGULANMAZ (dual-track on-prem; SAP klasik için hariç tutuyor).
Detay: governance/research/sap-ai-tooling-comparison.md "Clean Core kural AİLELERİ".

KURAL (Clean Core Level A TERCİHİ; ADR 0005-B std-tablo READ'i yasaklamaz, bu yüzden
SEVERITY = WARNING — bloklamaz, yönlendirir):
  CDS/ABAP'ta `from <std_tablo>` / `join <std_tablo>` → released successor öner.
  Z* tabloları (bizim) + zaten released I_* viewlar atlanır.

Veri: governance/reference/released_successors.json (curated; SAP resmi JSON ile refresh).

Kullanım:
    python scripts/validators/check_released_objects.py <artifact_path> [--strict]

Exit:
    0 — non-released tablo kullanımı yok (veya veri dosyası yok → skip)
    1 — en az 1 öneri (WARNING; reviewer zincirinde severity=WARNING ile bloklamaz)
"""
# ENFORCES: BE-03, C-CDS-FROM-04, C-RAP-REL-01  (ADR 0019 coverage binding)
import argparse
import json
import re
import sys
from pathlib import Path

if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# repo kökü: scripts/validators/ -> ../../
DATA_PATH = Path(__file__).resolve().parents[2] / 'governance' / 'reference' / 'released_successors.json'

# FROM / JOIN <name> — CDS ve ABAP SQL (case-insensitive)
REF_RE = re.compile(r'\b(?:from|join)\s+([a-zA-Z_]\w*)', re.IGNORECASE)


def load_map() -> dict:
    if not DATA_PATH.exists():
        return {}
    try:
        data = json.loads(DATA_PATH.read_text(encoding='utf-8'))
        return {k.upper(): v for k, v in data.get('tables', {}).items()}
    except Exception:
        return {}


def scan(text: str, table_map: dict) -> list[dict]:
    findings = []
    seen = set()
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        # yorum satırlarını atla (CDS // , ABAP * veya ")
        stripped = line.lstrip()
        if stripped.startswith('//') or stripped.startswith('*') or stripped.startswith('"'):
            continue
        for m in REF_RE.finditer(line):
            name = m.group(1).upper()
            if name in seen:
                continue
            entry = table_map.get(name)
            if entry:
                seen.add(name)
                # otoriter şema: successors=[...] ; eski curated: successor="X"
                succ = entry.get('successors') or ([entry['successor']] if entry.get('successor') else [])
                findings.append({
                    'line': i,
                    'table': name,
                    'successors': succ or ['?'],
                    'state': entry.get('state', ''),
                    'note': entry.get('note', ''),
                })
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description='Clean Core released-object / successor check')
    ap.add_argument('artifact')
    ap.add_argument('--strict', action='store_true')
    args = ap.parse_args()

    path = Path(args.artifact)
    if not path.exists():
        print(f'HATA: {path} bulunamadı', file=sys.stderr)
        return 1

    table_map = load_map()
    if not table_map:
        print(f'SKIP — successor veri dosyası yok/boş ({DATA_PATH.name}); released-check atlandı')
        return 0

    findings = scan(path.read_text(encoding='utf-8', errors='replace'), table_map)
    if not findings:
        print(f'OK — {path.name} non-released standart tablo kullanımı yok')
        return 0

    print(f'\n--- {path.name} — {len(findings)} non-released tablo (Clean Core önerisi) ---',
          file=sys.stderr)
    for f in findings:
        succ = ' / '.join(f['successors'])
        note = f' ({f["note"]})' if f['note'] else ''
        print(f"  [WARNING] line {f['line']} (C-CC-REL-01): '{f['table']}' non-released"
              f" → released successor: {succ}{note}", file=sys.stderr)
    print("    Not: ADR 0005-B READ'i yasaklamaz; Clean Core Level A için released CDS tercih edilir "
          "(öneri, hard kural değil). Kaynak: SAP resmi cloudification repo (PCE).", file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
