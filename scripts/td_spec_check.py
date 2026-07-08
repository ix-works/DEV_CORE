#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TD Spec Disiplin Checker — <PROJECT_NAME> ZSD015 ve gelecek modüller için.

KURAL (Playbook §1 §6️⃣):
  1. Yeni obje yarat/değiştirme → ÖNCE TD spec'i ara
  2. TD spec VARSA: TD karar otoritesi, "Silinen Alanlar"/"Kaldırılan" uygulanır,
     <LEGACY_SOURCE> sadece structural pattern referansı
  3. TD spec YOKSA: Operatör onayı şart, otomatik <LEGACY_SOURCE> fallback YASAK

KULLANIM (populate scripts veya TempScripts converter'larında):
    from td_spec_check import require_td_spec, find_deleted_items, scan_source_for_deleted

    # Spec yoksa script ölür (operator approval mesajı)
    spec_text = require_td_spec('ZSD015_DDL_ORDER_ITEMS', 'cds')

    # Spec'teki "Silinen" item'ları çıkar
    deleted = find_deleted_items(spec_text)
    # → {'fields': ['POSNumber', 'ProjectCode', ...], 'joins': ['tvv3t', ...]}

    # Source'ta varsa rapor
    issues = scan_source_for_deleted(source_text, deleted)
    if issues:
        # exit 1 with issue list
"""
import re
from pathlib import Path
from typing import Dict, List, Optional
import sys as _pc_sys
from pathlib import Path as _pc_Path
_pc_sys.path.insert(0, str(_pc_Path(__file__).resolve().parents[0]))
from utils.project_config import SOURCE_ROOT_NAME  # K12: kaynak-klasor adi config'ten

# Modül kökü — <PROJECT_NAME> project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Obje tipi → spec klasörü adı eşlemesi
OBJECT_TYPE_FOLDER = {
    'cds':       'cds',
    'class':     'classes',
    'classes':   'classes',
    'program':   'programs',
    'programs':  'programs',
    'structure': 'structures',
    'structures':'structures',
    'table':     'tables',
    'tables':    'tables',
    'auth':      'auth',
}

# Modül kök yolları (gelecek modüller için ekle: ZSD016_CLC vb.)
MODULE_ROOTS = [
    PROJECT_ROOT / SOURCE_ROOT_NAME / 'ZSD015_CLC',
]

# <LEGACY_SOURCE> referans kök (eski sistem source'ları + spec'leri)
# 2026-05-13: TD/ZSD015_CLC/SEVKEMRI klasörü silindi, tek referans burası.
<LEGACY_SOURCE>_ROOTS = [
    Path(r'C:/<LEGACY_ROOT>/<LEGACY_SOURCE>/SEVKEMRI'),
]


def find_td_spec(object_name: str, object_type: str) -> Optional[Path]:
    """TD ve fallback klasörlerinde spec MD dosyası ara.

    Arama sırası (2026-05-13 TD/ subfolder kaldırıldı, klasör yapısı düzleştirildi):
      1. <module>/<folder>/<object_name>.md              ← TD karar (öncelik)
      2. <<LEGACY_SOURCE>>/<folder>/<object_name>.md           ← <LEGACY_SOURCE> referansı (fallback)

    Returns: Path | None
    """
    folder = OBJECT_TYPE_FOLDER.get(object_type.lower())
    if not folder:
        return None
    # 1) TD karar otoritesi (modül kökü altında düz yapı)
    for module_root in MODULE_ROOTS:
        candidate = module_root / folder / f'{object_name}.md'
        if candidate.exists():
            return candidate
    # 2) <LEGACY_SOURCE> referans fallback
    for kap_root in <LEGACY_SOURCE>_ROOTS:
        candidate = kap_root / folder / f'{object_name}.md'
        if candidate.exists():
            return candidate
    return None


def require_td_spec(object_name: str, object_type: str,
                    action: str = 'create') -> str:
    """TD spec dosyasını bul ve içeriği döndür. Yoksa exit 1.

    Args:
        object_name: Obje adı (case-sensitive, dosya adıyla eşleşmeli)
        object_type: 'cds' | 'class' | 'program' | 'structure' | 'table' | 'auth'
        action: 'create' | 'modify' | 'delete' (sadece hata mesajı için)

    Returns:
        Spec MD dosyasının tam içeriği (UTF-8 string)

    Raises SystemExit: spec yoksa, operator approval mesajıyla.
    """
    spec_path = find_td_spec(object_name, object_type)
    if spec_path is None:
        folder = OBJECT_TYPE_FOLDER.get(object_type.lower(), '<unknown>')
        searched = [
            f'  - <source_root>/ZSD015_CLC/{folder}/{object_name}.md',
            f'  - C:/<LEGACY_ROOT>/<LEGACY_SOURCE>/SEVKEMRI/{folder}/{object_name}.md (<LEGACY_SOURCE> fallback)',
        ]
        msg = (
            f'\n[FAIL] TD spec EKSİK: {object_name} ({object_type}) — action={action}\n'
            f'\n'
            f'Aranan yollar:\n' + '\n'.join(searched) + '\n'
            f'\n'
            f'⚠️ Playbook §1 §6️⃣ — TD Spec Disiplini:\n'
            f'  • TD spec bulunmazsa <LEGACY_SOURCE> source\'a otomatik fallback YASAK.\n'
            f'  • Operatöre rapor et:\n'
            f'      "{object_name} için TD spec yok. <LEGACY_SOURCE>\'da X referansı var.\n'
            f'       <LEGACY_SOURCE>\'ı fallback alabilir miyim? Onay ver."\n'
            f'  • Onay alınmadan obje yaratılmaz/değiştirilmez.\n'
        )
        raise SystemExit(msg)

    return spec_path.read_text(encoding='utf-8')


def find_deleted_items(spec_text: str) -> Dict[str, List[str]]:
    """TD spec MD'sinden "Silinen Alanlar" / "Kaldırılan" item'larını çıkar.

    Spec format örnekleri:
      | Alan | Source | Kategori | Karar |
      |---|---|---|---|
      | `POSNumber` | OrderItem.POSNumber | feature iptal | ❌ |

      | `ProjectCode` | aufk join kaldırıldı |

    Returns:
        {'fields': [...], 'joins': [...], 'raw': [...]}
    """
    result = {'fields': [], 'joins': [], 'raw': []}

    # Section'ları bul: "Silinen Alanlar", "Kaldırılan N Alan", "Kaldırılan N Join"
    section_patterns = [
        (r'##+\s*Silinen Alanlar[^\n]*\n(.*?)(?=\n##+\s|\Z)',          'fields'),
        (r'##+\s*Kaldırılan\s+\d+\s+Alan[^\n]*\n(.*?)(?=\n##+\s|\Z)', 'fields'),
        (r'##+\s*Kaldırılan\s+\d+\s+Join[^\n]*\n(.*?)(?=\n##+\s|\Z)', 'joins'),
        # Geçmiş bölümü (master ORDER_ITEMS spec'i için)
        (r'##+\s*Geçmiş\s*—\s*Kaldırılan[^\n]*Alan[^\n]*\n(.*?)(?=\n##+\s|\Z)', 'fields'),
        (r'##+\s*Geçmiş\s*—\s*Kaldırılan[^\n]*Join[^\n]*\n(.*?)(?=\n##+\s|\Z)', 'joins'),
    ]

    for pattern, category in section_patterns:
        for m in re.finditer(pattern, spec_text, re.DOTALL | re.IGNORECASE):
            section_body = m.group(1)
            # Her tablo satırında backtick içindeki TÜM identifier'ları yakala
            for row in re.finditer(r'^\|(.+)\|.*$', section_body, re.MULTILINE):
                row_text = row.group(0)
                # Header/separator satırlarını skip
                if re.match(r'^\|[\s\-:|]+\|?\s*$', row_text):
                    continue
                if re.search(r'\|\s*(#|Alan|Join|Alan/Join|Sebep|Karar|Kategori)\s*\|', row_text):
                    continue
                # Backtick'li tüm identifier'ları çek
                for hit in re.finditer(r'`([^`]+)`', row_text):
                    raw = hit.group(1).strip()
                    # "y_yanpanmonr/l(_text)" → ['y_yanpanmonr', 'y_yanpanmonr_text',
                    #                          'y_yanpanmonl', 'y_yanpanmonl_text']
                    expanded = _expand_compact(raw)
                    for name in expanded:
                        if not name or len(name) < 2:
                            continue
                        if category == 'fields':
                            result['fields'].append(name)
                        elif category == 'joins':
                            result['joins'].append(name)
                        result['raw'].append(name)

    result['fields'] = list(dict.fromkeys(result['fields']))  # dedupe preserve order
    result['joins']  = list(dict.fromkeys(result['joins']))
    result['raw']    = list(dict.fromkeys(result['raw']))

    return result


def _expand_compact(name: str) -> List[str]:
    """Compact identifier formatlarını expand et.

    'y_yanpanmonr/l(_text)' → ['y_yanpanmonr', 'y_yanpanmonr_text',
                               'y_yanpanmonl', 'y_yanpanmonl_text']
    'OrderItemStatus(Text)' → ['OrderItemStatus', 'OrderItemStatusText']
    'POSNumber'             → ['POSNumber']
    'tvv3t, tvv4t'          → ['tvv3t', 'tvv4t']
    """
    # Comma ile multi-name
    if ',' in name:
        out = []
        for part in name.split(','):
            out.extend(_expand_compact(part.strip()))
        return out

    # Slash variant: y_yanpanmonr/l → y_yanpanmonr + y_yanpanmonl
    m = re.match(r'^(.+?)([a-z])/([a-z])(\(_text\)|_text)?$', name)
    if m:
        base, ch1, ch2, suffix = m.group(1), m.group(2), m.group(3), m.group(4) or ''
        if suffix == '(_text)':
            return [base + ch1, base + ch1 + '_text',
                    base + ch2, base + ch2 + '_text']
        elif suffix == '_text':
            return [base + ch1 + '_text', base + ch2 + '_text']
        else:
            return [base + ch1, base + ch2]

    # Parenthesis variant: OrderItemStatus(Text) → OrderItemStatus + OrderItemStatusText
    m = re.match(r'^(.+?)\(([^)]+)\)$', name)
    if m:
        base, suffix = m.group(1), m.group(2)
        return [base, base + suffix]

    return [name]


def scan_source_for_deleted(source_text: str, deleted: Dict[str, List[str]]) -> List[str]:
    """Source'ta silinen alan/join referansı var mı?

    Returns:
        Hata mesajları listesi (boş = OK).
    """
    issues = []

    # Field check: `as <Name>,` veya `as <Name>\n`
    for field in deleted.get('fields', []):
        pat = re.compile(r'\bas\s+' + re.escape(field) + r'\b', re.IGNORECASE)
        for m in pat.finditer(source_text):
            line_no = source_text[:m.start()].count('\n') + 1
            issues.append(f'  satır {line_no}: silinen alan hala source\'ta: "{field}"')

    # Join check: `join <table>` veya `from <table>`
    for join in deleted.get('joins', []):
        pat = re.compile(r'\b(?:join|from)\s+' + re.escape(join) + r'\b', re.IGNORECASE)
        for m in pat.finditer(source_text):
            line_no = source_text[:m.start()].count('\n') + 1
            issues.append(f'  satır {line_no}: silinen join/from hala source\'ta: "{join}"')

    return issues


def validate_source_against_spec(source_text: str, object_name: str,
                                  object_type: str) -> List[str]:
    """Tam akış: spec'i yükle, silinenleri çıkar, source'ta ara.

    Returns: hata mesajı listesi (boş = OK).
    SystemExit: spec yoksa.
    """
    spec_text = require_td_spec(object_name, object_type)
    deleted = find_deleted_items(spec_text)
    return scan_source_for_deleted(source_text, deleted)


# ─── CLI test ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print('Kullanım: python td_spec_check.py <object_name> <object_type> [source_file]')
        print('Örnek:    python td_spec_check.py ZSD015_DDL_ORDER_ITEMS cds')
        sys.exit(2)
    name, otype = sys.argv[1], sys.argv[2]
    spec = require_td_spec(name, otype)
    deleted = find_deleted_items(spec)
    print(f'TD spec bulundu: {name} ({otype})')
    print(f'  Silinen alanlar: {len(deleted["fields"])}')
    for f in deleted['fields']:
        print(f'    - {f}')
    print(f'  Silinen join\'ler: {len(deleted["joins"])}')
    for j in deleted['joins']:
        print(f'    - {j}')
    if len(sys.argv) >= 4:
        source = Path(sys.argv[3]).read_text(encoding='utf-8')
        issues = scan_source_for_deleted(source, deleted)
        print(f'\nSource scan ({sys.argv[3]}):')
        if issues:
            print(f'  {len(issues)} sorun:')
            for i in issues:
                print(i)
        else:
            print('  ✓ Temiz, silinen item bulunamadı')
