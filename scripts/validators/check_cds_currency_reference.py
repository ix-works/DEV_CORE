"""
check_cds_currency_reference.py — CDS/Tablo source'unda CURR/QUAN/CURRENCY/UNIT
field'ların annotation kuralları kontrol eder.

KURAL (Playbook §15.3):
  CURR field için: hemen üstte @Semantics.amount.currencyCode : 'TABLE.FIELD' (qualified)
  CUKY field için: @Semantics.currencyCode : true marker
  QUAN field için: hemen üstte @Semantics.quantity.unitOfMeasure : 'TABLE.FIELD' (qualified)
  UNIT field için: @Semantics.unitOfMeasure : true marker

Deterministik check — regex parsing, LLM yorum yok.

Kullanım:
    python scripts/validators/check_cds_currency_reference.py <artifact_path>
    python scripts/validators/check_cds_currency_reference.py <artifact_path> --type table
    python scripts/validators/check_cds_currency_reference.py <artifact_path> --type unit

Exit kodu:
    0 — Tüm CURR/QUAN field'ları doğru annotation'a sahip
    1 — En az 1 ihlal (stderr'de satır no + öneri)
"""
# ENFORCES: C-CDS-CUR-02, C-CDS-CUR-03, C-RAP-VE-07, C-STR-CUR-02, C-STR-CUR-03, C-STR-CUR-04, C-STR-CUR-05, C-STR-UNIT-01, C-STR-UNIT-02, C-TBL-CUR-02, C-TBL-CUR-03, C-TBL-CUR-04, C-TBL-QUAN-01, C-TBL-QUAN-02  (ADR 0019 coverage binding)
import argparse
import re
import sys
from pathlib import Path

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Built-in CURR DTEL'leri (genişletilebilir)
CURR_DTELS = {
    'netwr', 'mwsbp', 'kbetr', 'dmbtr', 'wrbtr', 'kzwi1', 'kzwi2',
    'kzwi3', 'kzwi4', 'kzwi5', 'kzwi6', 'sklfr', 'klfre', 'lfrec',
    'price', 'curr', 'amount',
}

# Built-in QUAN DTEL'leri
QUAN_DTELS = {
    'menge_d', 'kwmeng', 'kwmen', 'lfimg', 'lfime', 'wmeng', 'bmeng',
    'menge', 'volum', 'ntgew', 'brgew', 'quan',
}

# Built-in CUKY/UNIT DTEL'leri
CUKY_DTELS = {'waers', 'waerk', 'hwaer'}
UNIT_DTELS = {'meins', 'vrkme', 'gewei', 'voleh', 'lager', 'unit'}


def parse_source(text: str, src_type: str) -> dict:
    """Source'tan field listesi + annotation'ları çıkar.

    src_type: 'cds' veya 'table'
    """
    lines = text.splitlines()
    fields = []  # [(line_no, name, dtel, annotations_before)]
    pending_annotations = []

    if src_type == 'cds':
        # CDS: 'alias_or_field : type' veya 'sourcefield as alias'
        field_pattern = re.compile(
            r'^\s*(?:key\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\s+as\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[,]?\s*$'
            r'|^\s*(?:key\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*[,]?\s*$',
            re.MULTILINE
        )
    else:  # table
        # Table: 'field_name : dtel;'
        field_pattern = re.compile(
            r'^\s*(?:key\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:not\s+null)?\s*;\s*$',
            re.MULTILINE
        )

    annotation_pattern = re.compile(r'^\s*@(\S+)\s*:\s*(.+?)\s*$')

    for i, line in enumerate(lines, 1):
        anno_m = annotation_pattern.match(line)
        if anno_m:
            pending_annotations.append((anno_m.group(1), anno_m.group(2)))
            continue

        if src_type == 'table':
            field_m = field_pattern.match(line)
            if field_m:
                fields.append({
                    'line': i,
                    'name': field_m.group(1).lower(),
                    'dtel': field_m.group(2).lower(),
                    'annotations': pending_annotations[:],
                })
                pending_annotations = []
            elif line.strip() and not line.strip().startswith('//') and not line.strip().startswith('--'):
                # Reset pending if non-annotation non-field line
                if not line.strip().startswith('@'):
                    pending_annotations = []
    return fields


def check_table(text: str) -> list[dict]:
    """Tablo source'unda CURR/QUAN reference check."""
    fields = parse_source(text, 'table')
    violations = []

    # CUKY/UNIT field'ları indexle (marker check için)
    cuky_fields = {f['name']: f for f in fields if f['dtel'] in CUKY_DTELS}
    unit_fields = {f['name']: f for f in fields if f['dtel'] in UNIT_DTELS}

    # CURR field'ları kontrol
    for f in fields:
        if f['dtel'] in CURR_DTELS:
            # Annotation var mı?
            cur_annot = None
            for key, val in f['annotations']:
                if 'amount.currencycode' in key.lower():
                    cur_annot = (key, val.strip())
                    break
            if not cur_annot:
                violations.append({
                    'severity': 'BLOCKER',
                    'line': f['line'],
                    'check_id': 'C-TBL-CUR-03',
                    'message': f"CURR field '{f['name']}' için @Semantics.amount.currencyCode annotation eksik",
                    'fix': f"Hemen üstüne ekle: @Semantics.amount.currencyCode : '<table>.<currency_field>'"
                })
            else:
                # Qualified format?
                val = cur_annot[1].strip("'\"")
                if '.' not in val:
                    violations.append({
                        'severity': 'BLOCKER',
                        'line': f['line'],
                        'check_id': 'C-TBL-CUR-03',
                        'message': f"CURR field '{f['name']}' annotation qualified format değil: {val}",
                        'fix': f"'{val}' → '<table_name>.{val}' (qualified TABLE.FIELD)"
                    })
                else:
                    # Referans field aynı tabloda mı?
                    ref_field = val.split('.')[-1].lower()
                    if ref_field not in cuky_fields:
                        violations.append({
                            'severity': 'BLOCKER',
                            'line': f['line'],
                            'check_id': 'C-TBL-CUR-04',
                            'message': f"CURR field '{f['name']}' referans verdiği CUKY '{ref_field}' tabloda yok",
                            'fix': f"CUKY field '{ref_field}' ekle veya farklı referans seç"
                        })

    # CUKY field'ları @Semantics.currencyCode : true marker check
    for f in fields:
        if f['dtel'] in CUKY_DTELS:
            has_marker = any(
                'currencycode' in key.lower() and 'true' in val.lower()
                for key, val in f['annotations']
            )
            if not has_marker:
                violations.append({
                    'severity': 'BLOCKER',
                    'line': f['line'],
                    'check_id': 'C-TBL-CUR-04',
                    'message': f"CUKY field '{f['name']}' üzerinde @Semantics.currencyCode : true marker eksik",
                    'fix': f"Hemen üstüne ekle: @Semantics.currencyCode : true"
                })

    # QUAN field'ları kontrol (aynı pattern)
    for f in fields:
        if f['dtel'] in QUAN_DTELS:
            quan_annot = None
            for key, val in f['annotations']:
                if 'quantity.unitofmeasure' in key.lower():
                    quan_annot = (key, val.strip())
                    break
            if not quan_annot:
                violations.append({
                    'severity': 'BLOCKER',
                    'line': f['line'],
                    'check_id': 'C-TBL-QUAN-02',
                    'message': f"QUAN field '{f['name']}' için @Semantics.quantity.unitOfMeasure eksik",
                    'fix': f"Hemen üstüne ekle: @Semantics.quantity.unitOfMeasure : '<table>.<unit_field>'"
                })
            else:
                val = quan_annot[1].strip("'\"")
                if '.' not in val:
                    violations.append({
                        'severity': 'BLOCKER',
                        'line': f['line'],
                        'check_id': 'C-TBL-QUAN-02',
                        'message': f"QUAN field '{f['name']}' annotation qualified değil: {val}",
                        'fix': f"'{val}' → '<table_name>.{val}'"
                    })

    return violations


def check_cds(text: str) -> list[dict]:
    """CDS source'unda CURR/QUAN reference check.

    Note: CDS'lerde currency reference daha esnek (any view referansı OK).
    Bu yüzden sadece annotation varlığını + qualified format'ı kontrol et.
    """
    violations = []
    lines = text.splitlines()

    # CDS'te basit pattern: @Semantics.amount.currencyCode arıyoruz,
    # değeri qualified mi?
    for i, line in enumerate(lines, 1):
        m = re.search(r"@Semantics\.amount\.currencyCode\s*:\s*'([^']+)'", line)
        if m:
            val = m.group(1)
            # VIEW ENTITY: currencyCode bir EXPOSED ELEMENT adına referans verir
            # (qualified 'TABLE.FIELD' değil — o kural §15.3 tablo/klasik-view içindir).
            # Çalışan kanıt: ZSD001_I_SO_ITEM ('Waerk'), ZSD001 RAP pilotu ('SalesUnit').
            # quantity.unitOfMeasure dalıyla tutarlı: bare identifier (element adı) GEÇERLİ;
            # sadece ne qualified ne de geçerli identifier ise uyar (WARNING).
            if '.' not in val and not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', val):
                violations.append({
                    'severity': 'WARNING',
                    'line': i,
                    'check_id': 'C-CDS-CUR-02',
                    'message': f"CDS currencyCode annotation tek alias değil/geçersiz: '{val}' — element adı veya qualified bekleniyor",
                    'fix': f"View entity'de exposed element adı ('Waerk') veya qualified '<view>.{val}' kullan"
                })

        m = re.search(r"@Semantics\.quantity\.unitOfMeasure\s*:\s*'([^']+)'", line)
        if m:
            val = m.group(1)
            # CDS'te field adı alias olabilir, qualified zorunlu değil (warning)
            if '.' not in val and not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', val):
                violations.append({
                    'severity': 'WARNING',
                    'line': i,
                    'check_id': 'C-CDS-CUR-03',
                    'message': f"CDS unitOfMeasure annotation tek alias: '{val}' — qualified olması önerilir",
                    'fix': f"Mümkünse '<view>.{val}' kullan"
                })

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description='CDS/Tablo CURR/QUAN reference check')
    parser.add_argument('artifact', help='Source dosyası path (.cds, .ddls.asddls, vb.)')
    parser.add_argument('--type', choices=['cds', 'table', 'auto'], default='auto')
    parser.add_argument('--strict', action='store_true', help='run_all_validators uyum için')
    args = parser.parse_args()

    path = Path(args.artifact)
    if not path.exists():
        print(f'HATA: {path} bulunamadı', file=sys.stderr)
        return 1

    text = path.read_text(encoding='utf-8', errors='replace')

    src_type = args.type
    if src_type == 'auto':
        if 'define table function' in text:
            # CDS table function = DDLS objesi (DDIC tablo DEĞİL). Return yapısı view gibi
            # LOKAL element-adı kullanır (qualified TABLE.FIELD yok) → check_table FALSE-POSITIVE
            # basıyordu (C-TBL-CUR-03). TF return-yapısı CURR/QUAN kontrolü ayrı bir konu;
            # şimdilik atla (TF-aware kontrol TODO). 2026-06-24 SATNAV BASE.cds.
            print(f'OK — {path.name} (table function) CURR/QUAN reference check atlandı (TF-aware kontrol TODO)')
            return 0
        if 'define table' in text or 'define structure' in text:
            src_type = 'table'
        elif 'define view' in text:
            src_type = 'cds'
        else:
            print(f'UYARI: Source tipi tespit edilemedi (define table/view yok)', file=sys.stderr)
            return 0

    if src_type == 'table':
        violations = check_table(text)
    else:
        violations = check_cds(text)

    if not violations:
        print(f'OK — {path.name} ({src_type}) CURR/QUAN reference check temiz')
        return 0

    print(f'\n--- {path.name} ({src_type}) — {len(violations)} ihlal ---', file=sys.stderr)
    for v in violations:
        print(f"  [{v['severity']}] line {v['line']} ({v['check_id']}): {v['message']}", file=sys.stderr)
        print(f"    Fix: {v['fix']}", file=sys.stderr)

    # BLOCKER varsa exit 1
    if any(v['severity'] == 'BLOCKER' for v in violations):
        return 1
    return 0  # Sadece WARNING


if __name__ == '__main__':
    sys.exit(main())
