"""
check_domain_output_length.py — Domain output length formülünü doğrular.

KURAL (Playbook §26.1.1):
  CHAR/NUMC/DATS/TIMS/CLNT → outputLength = length
  INT1 → 4, INT2 → 6, INT4 → 11, INT8 → 20
  DEC/QUAN/CURR → outputLength = length + 4 (sign + decimal + thousand sep)

Vaka 2026-05-14 (Sprint 1A) — populate_domains.py output length'i length ile aynı
atıyordu, QUAN(15,3) için output 15 yerine 19 olmalı. Aktivasyonda warning + display
kesilmesi. 5 domain delete+recreate edildi. Bu validator pre-flight'ta yakalar.

Kullanım:
    python scripts/validators/check_domain_output_length.py <csv_path>
    python scripts/validators/check_domain_output_length.py <xml_path>

Exit kodu:
    0 — Tüm output length'ler doğru
    1 — En az bir hata
"""
import argparse
import csv
import re
import sys
from pathlib import Path

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def expected_output_length(datatype: str, length: int, decimals: int) -> int:
    """SAP'nin domain output length formülü."""
    dt = datatype.upper()
    if dt == 'INT1':
        return 4
    if dt == 'INT2':
        return 6
    if dt == 'INT4':
        return 11
    if dt == 'INT8':
        return 20
    if dt in ('DEC', 'QUAN', 'CURR'):
        return length + 4
    return length


def check_csv(csv_path: Path) -> list[dict]:
    """CSV format: name,datatype,length,decimals,description,fixed_values"""
    violations = []
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                dt = row.get('datatype', '').strip().upper()
                length = int(row.get('length', 0))
                decimals = int(row.get('decimals', 0))
                expected = expected_output_length(dt, length, decimals)
                # CSV'de outputLength field'ı yok — bu OK (populate_domains.py
                # calculate_output_length() ile otomatik hesaplar)
                # Sadece tipi destekleyen formül var mı kontrol et
                if dt not in ('CHAR', 'NUMC', 'DATS', 'TIMS', 'CLNT',
                              'INT1', 'INT2', 'INT4', 'INT8',
                              'DEC', 'QUAN', 'CURR'):
                    violations.append({
                        'name': row.get('name'),
                        'message': f'Bilinmeyen datatype: {dt}',
                        'fix': f'Desteklenen tipler: CHAR, NUMC, DATS, TIMS, CLNT, INT1-8, DEC, QUAN, CURR'
                    })
            except (ValueError, KeyError) as e:
                violations.append({
                    'name': row.get('name', '?'),
                    'message': f'CSV satırı parse hatası: {e}',
                    'fix': 'CSV format kontrol et'
                })
    return violations


def check_xml(xml_path: Path) -> list[dict]:
    """Domain XML — typeInformation/length + outputInformation/length karşılaştırması."""
    text = xml_path.read_text(encoding='utf-8', errors='replace')
    violations = []

    # datatype
    dt_m = re.search(r'<doma:datatype>([^<]+)</doma:datatype>', text)
    # type length
    tl_m = re.search(r'<doma:typeInformation>.*?<doma:length>([^<]+)</doma:length>', text, re.DOTALL)
    # type decimals
    td_m = re.search(r'<doma:typeInformation>.*?<doma:decimals>([^<]+)</doma:decimals>', text, re.DOTALL)
    # output length
    ol_m = re.search(r'<doma:outputInformation>.*?<doma:length>([^<]+)</doma:length>', text, re.DOTALL)

    if not all([dt_m, tl_m, ol_m]):
        return [{'name': xml_path.stem, 'message': 'XML parse edilemedi', 'fix': 'XML format'}]

    dt = dt_m.group(1).strip().upper()
    length = int(tl_m.group(1))
    decimals = int(td_m.group(1)) if td_m else 0
    actual_output = int(ol_m.group(1))
    expected_output = expected_output_length(dt, length, decimals)

    if actual_output != expected_output:
        violations.append({
            'name': xml_path.stem,
            'message': f'{dt}({length},{decimals}): outputLength {actual_output}, beklenen {expected_output}',
            'fix': f'XML output length\'i {expected_output} olarak düzelt'
        })

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description='Domain output length formula kontrolü')
    parser.add_argument('artifact')
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()

    path = Path(args.artifact)
    if not path.exists():
        print(f'HATA: {path} bulunamadı', file=sys.stderr)
        return 1

    if path.suffix == '.csv':
        violations = check_csv(path)
    elif path.suffix == '.xml':
        violations = check_xml(path)
    else:
        print(f'UYARI: {path.suffix} tipi desteklenmiyor (csv/xml)', file=sys.stderr)
        return 0

    if not violations:
        print(f'OK — {path.name} domain output length formula temiz')
        return 0

    print(f'\n[BLOCKER] {path.name} — {len(violations)} ihlal:', file=sys.stderr)
    for v in violations:
        print(f"  {v['name']}: {v['message']}", file=sys.stderr)
        print(f"    Fix: {v['fix']}", file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
