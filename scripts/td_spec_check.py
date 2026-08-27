#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TD Spec Disiplin Checker — proje spec otoritesi gate'i (tüm paketler için).

KURAL (Playbook §1 §6️⃣):
  1. Yeni obje yarat/değiştirme → ÖNCE TD (target-design) spec'i ara
  2. TD spec VARSA: TD karar otoritesi, "Silinen Alanlar"/"Kaldırılan" uygulanır,
     legacy kaynak sadece structural pattern referansı
  3. TD spec YOKSA: Operatör onayı şart, otomatik legacy fallback YASAK

Konfig (project.yaml): `active_package` (öncelikli arama) · `legacy_spec_roots`
(eski-sistem spec kökleri, liste; yoksa legacy fallback araması yapılmaz).

KULLANIM (populate scripts veya TempScripts converter'larında):
    from td_spec_check import require_td_spec, find_deleted_items, scan_source_for_deleted

    # Spec yoksa script ölür (operator approval mesajı)
    spec_text = require_td_spec('ZSD<NNN>_DDL_ORDER_ITEMS', 'cds')

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
from utils.project_config import cfg, project_root, source_dir  # K12 config tek-nokta

# Windows konsolu/pipe'i cp1252'dir: non-ASCII basmak UnicodeEncodeError ile COKER
# (exit 1 -> gercek FAIL'den ayirt edilemez). C-ENC-01 / check_console_utf8.py
for _akis in (_pc_sys.stdout, _pc_sys.stderr):   # 2026-07-10: 'sys' hiç import edilmemişti
    try:                                          # → satır import-anında NameError ile ÇÖKÜYORDU
        _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

# Proje kökü — env-first (junction'da __file__ core'a çözülür, KULLANMA)
PROJECT_ROOT = project_root()

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

def _module_roots() -> List[Path]:
    """Spec aranacak kökler — İKİ SEVİYE (2026-08-27 düzeltmesi).

    Kaynak ağacı gerçekte `<source_root>/<MODÜL>/<PAKET>` (ör. `SD/ZMOD001_CLC`)
    olabilir. Eski kod yalnız `source_dir().iterdir()` ile TEK seviye iniyordu →
    eline MODÜL klasörü geçiyordu, PAKET klasörü değil; docstring "paket kökleri"
    dediği hâlde paket kökü hiç listelenmiyordu ve `active_package` önceliği ÖLÜ
    daldı (config'teki paket adı tek-katmanda aranıyordu, gerçekte iki-katmandaydı).

    Sıra (yön DAİMA genişletme — hiçbir eski aday KALDIRILMADI):
      1. active_package — hem `<kök>/<paket>` hem `<kök>/<modül>/<paket>`
      2. tek seviye: `<kök>/<x>` (eski davranışın TAMAMI, aynı sırayla —
         düz `<kök>/<paket>` yapısı kullanan projeler için geriye-uyum)
      3. iki seviye: `<kök>/<modül>/<paket>`
    (2) tamamen (3)'ten önce gelir: daha önce BULUNAN hiçbir spec'in çözümü
    kaymaz; yalnız daha önce HİÇ bulunamayanlar bulunur.
    """
    roots: List[Path] = []
    src = source_dir()
    if not src.is_dir():
        return roots

    def _ekle(p: Path) -> None:
        if p.is_dir() and p not in roots:
            roots.append(p)

    def _alt_dizinler(p: Path) -> List[Path]:
        try:
            return sorted(d for d in p.iterdir() if d.is_dir())
        except OSError:
            return []

    birinci_seviye = _alt_dizinler(src)

    # 1) active_package önceliği — iki katmanda da ara
    aktif = str(cfg('active_package') or '').strip()
    if aktif:
        _ekle(src / aktif)
        for d in birinci_seviye:
            _ekle(d / aktif)

    # 2) tek seviye (eski davranış, aynı sıra)
    for d in birinci_seviye:
        _ekle(d)

    # 3) iki seviye: <modül>/<paket>
    for d in birinci_seviye:
        for alt in _alt_dizinler(d):
            _ekle(alt)

    return roots


# Spec dosyasının kök ALTINDAKİ konumu: düz `<folder>/` (tarihsel) veya
# `ref_docs/<folder>/` (paket ağacının bugünkü yerleşimi). Sıra = arama sırası;
# düz yapı ÖNCE denenir (geriye-uyum: eski çözümler kaymaz).
_SPEC_ALT_YOLLAR: tuple = ((), ('ref_docs',))


def _aday_yollar(object_name: str, folder: str) -> List[Path]:
    """Aranacak TÜM aday yollar (TD kökleri + legacy fallback), sırayla.

    `find_td_spec` ve `require_td_spec`in hata mesajı BU listeyi kullanır —
    tek kaynak: "aranan yollar" raporu ile fiilen aranan yollar ayrışamaz.
    """
    adaylar: List[Path] = []
    for kok in _module_roots():
        for ara in _SPEC_ALT_YOLLAR:
            adaylar.append(kok.joinpath(*ara, folder, f'{object_name}.md'))
    for leg_root in _legacy_roots():
        for ara in _SPEC_ALT_YOLLAR:
            adaylar.append(leg_root.joinpath(*ara, folder, f'{object_name}.md'))
    return adaylar


def _legacy_roots() -> List[Path]:
    """Eski-sistem spec kökleri. Tanımsızsa legacy fallback araması YAPILMAZ (fail-safe).

    Kaynak sırası (2026-07-10): legacy kök MAKİNEYE ÖZGÜ mutlak yoldur (ör. eski dünyanın
    <LEGACY_SOURCE> kökü) → project.yaml'da COMMIT'lenirse klonlayan geliştiricide o klasör
    yoktur ve spec-arama sessizce yanlış davranır. Bu yüzden önce git-DIŞI lokal config:
      1. env IX_LEGACY_SPEC_ROOTS (virgülle ayrılmış)
      2. <proje>/.claude/project.local.yaml → legacy_spec_roots:  (.gitignore'lu)
      3. project.yaml legacy_spec_roots  (geriye-uyum; opsiyonel)
    """
    import os as _os
    env = _os.environ.get("IX_LEGACY_SPEC_ROOTS", "").strip()
    if env:
        return [Path(p.strip()) for p in env.split(",") if p.strip()]
    try:
        proj = Path(_os.environ.get("CLAUDE_PROJECT_DIR") or _os.getcwd())
        loc = proj / ".claude" / "project.local.yaml"
        if loc.exists():
            roots = []
            icinde = False
            for line in loc.read_text(encoding="utf-8", errors="replace").splitlines():
                s = line.strip()
                if s.startswith("legacy_spec_roots:"):
                    kalan = s.split(":", 1)[1].strip()
                    if kalan.startswith("[") and kalan.endswith("]"):
                        return [Path(x.strip().strip("'\""))
                                for x in kalan[1:-1].split(",") if x.strip()]
                    icinde = True
                    continue
                if icinde:
                    if s.startswith("- "):
                        roots.append(Path(s[2:].strip().strip("'\"")))
                    elif s and not s.startswith("#"):
                        break
            if roots:
                return roots
    except Exception:
        pass
    return [Path(str(p)) for p in (cfg('legacy_spec_roots') or [])]


def find_td_spec(object_name: str, object_type: str) -> Optional[Path]:
    """TD ve fallback klasörlerinde spec MD dosyası ara.

    Arama sırası (kökler için bkz. `_module_roots`; her kökte İKİ yerleşim denenir):
      1. <TD kök>/<folder>/<object_name>.md              ← düz yapı (tarihsel)
      2. <TD kök>/ref_docs/<folder>/<object_name>.md     ← paket ağacı yerleşimi
      3. <legacy_spec_roots[i]>/[ref_docs/]<folder>/<object_name>.md  ← fallback

    TD kökleri: active_package öncelikli, sonra tek seviye, sonra `<modül>/<paket>`.

    Returns: Path | None
    """
    folder = OBJECT_TYPE_FOLDER.get(object_type.lower())
    if not folder:
        return None
    for candidate in _aday_yollar(object_name, folder):
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
        # Aranan yollar FİİLEN aranan listeden üretilir (kopya mantık YOK — mesaj
        # ile davranış ayrışamaz). `_aday_yollar` boş dönerse hiç kök yok demektir.
        _legacy_kok = {str(r) for r in _legacy_roots()}
        searched = []
        for _ad in _aday_yollar(object_name, folder):
            _legacy_mi = any(str(_ad).startswith(k) for k in _legacy_kok)
            searched.append(f'  - {_ad}' + (' (legacy fallback)' if _legacy_mi else ''))
        if not searched:
            searched = ['  - (arama kökü yok: source_root altında paket klasörü ve '
                        'legacy_spec_roots tanımı bulunamadı — project.yaml kontrol et)']
        msg = (
            f'\n[FAIL] TD spec EKSİK: {object_name} ({object_type}) — action={action}\n'
            f'\n'
            f'Aranan yollar:\n' + '\n'.join(searched) + '\n'
            f'\n'
            f'⚠️ Playbook §1 §6️⃣ — TD Spec Disiplini:\n'
            f'  • TD spec bulunmazsa legacy source\'a otomatik fallback YASAK.\n'
            f'  • Operatöre rapor et:\n'
            f'      "{object_name} için TD spec yok. Legacy kaynakta X referansı var.\n'
            f'       Legacy\'yi fallback alabilir miyim? Onay ver."\n'
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
        print('Örnek:    python td_spec_check.py ZSD<NNN>_DDL_ORDER_ITEMS cds')
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
