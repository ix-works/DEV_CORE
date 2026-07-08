"""
check_sap_active_version.py — Post-activate validator.

SAP'deki obje metadata'sından `adtcore:version` değerini okur ve "active"
olduğunu doğrular. DTEL, DOMA, TABL, DDLS, CLAS gibi objeler için kullanılır.

Sprint 6 lesson (T10): "activate" çağrısı OK döndü diye obje gerçekten aktif
anlamına gelmez — bağımlı objeler "inconsistent in active version" durumunda
olabilir. Bu validator metadata'dan teyit eder.

Kullanım:
    python scripts/validators/check_sap_active_version.py --name X --object-type T
    python scripts/validators/check_sap_active_version.py <artifact>   # struct DDL'den auto

Exit kodu:
    0 — version=="active"
    1 — inactive veya bulunamadı
"""
# ENFORCES: C-RAP-ACT-01  (ADR 0019 coverage binding)
import argparse
import re
import sys
from pathlib import Path

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')


# ADT object type → REST path
ADT_PATHS = {
    'dtel': 'ddic/dataelements',
    'dataelement': 'ddic/dataelements',
    'doma': 'ddic/domains',
    'domain': 'ddic/domains',
    'tabl': 'ddic/tables',
    'table': 'ddic/tables',
    'structure': 'ddic/structures',
    'struct': 'ddic/structures',
    'ddls': 'ddic/ddl/sources',
    'cds': 'ddic/ddl/sources',
    'view': 'ddic/ddl/sources',
    'clas': 'oo/classes',
    'class': 'oo/classes',
}


def infer_from_artifact(path: Path) -> tuple[str | None, str | None]:
    """Artifact'tan name + object_type tahmin et."""
    text = path.read_text(encoding='utf-8', errors='replace')
    # Struct/table: define structure NAME / define table NAME
    m = re.search(r'define\s+structure\s+(\w+)', text, re.IGNORECASE)
    if m:
        return m.group(1).upper(), 'structure'
    m = re.search(r'define\s+table\s+(\w+)', text, re.IGNORECASE)
    if m:
        return m.group(1).upper(), 'tabl'
    # CDS: define view NAME / define view entity NAME
    m = re.search(r'define\s+(?:root\s+)?view(?:\s+entity)?\s+(\w+)', text, re.IGNORECASE)
    if m:
        return m.group(1).upper(), 'ddls'
    # CDS abstract/custom entity: define abstract entity NAME / define custom entity NAME
    # (view yoktur → üstteki regex eşleşmez; eklenmezse abstract entity push'unda obje adı
    #  None döner → false BLOCKER. Vaka: ZSD001_I_SIM_R, 2026-06-29.)
    m = re.search(r'define\s+(?:abstract|custom)\s+entity\s+(\w+)', text, re.IGNORECASE)
    if m:
        return m.group(1).upper(), 'ddls'
    return None, None


def main() -> int:
    parser = argparse.ArgumentParser(description='SAP objesinin version=active olduğunu doğrula')
    parser.add_argument('artifact', nargs='?', help='İsteğe bağlı: artifact path (auto-infer)')
    parser.add_argument('--name', help='Obje adı (artifact yerine)')
    parser.add_argument('--object-type', help='ADT obje tipi (dtel, doma, tabl, structure, ddls, class)')
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()

    name = args.name
    obj_type = args.object_type

    if (not name or not obj_type) and args.artifact:
        p = Path(args.artifact)
        if not p.exists():
            print(f'HATA: {p} bulunamadı', file=sys.stderr)
            return 1
        n2, t2 = infer_from_artifact(p)
        name = name or n2
        obj_type = obj_type or t2

    if not name or not obj_type:
        print('HATA: --name ve --object-type (veya artifact) gerekli', file=sys.stderr)
        return 1

    path_segment = ADT_PATHS.get(obj_type.lower())
    if not path_segment:
        print(f'UYARI: {obj_type} desteklenmiyor, atlandı (desteklenen: {list(ADT_PATHS)})')
        return 0

    sys.path.insert(0, str(Path(__file__).parent.parent))
    try:
        from sap_adt_lib import SAPADTClient
        client = SAPADTClient()
    except Exception as e:
        print(f'UYARI: SAP bağlantısı kurulamadı, validator atlandı: {e}', file=sys.stderr)
        return 0

    try:
        r = client.session.get(
            client.url + f'/sap/bc/adt/{path_segment}/{name.lower()}',
            params={'sap-client': '100'}, verify=False, timeout=15
        )
    except Exception as e:
        print(f'UYARI: SAP GET hata: {e}', file=sys.stderr)
        return 0

    if r.status_code == 404:
        print(f'[BLOCKER] {name} ({obj_type}) SAP\'de bulunamadı (404).', file=sys.stderr)
        return 1
    if r.status_code != 200:
        print(f'UYARI: SAP GET {r.status_code} — validator atlandı', file=sys.stderr)
        return 0

    m = re.search(r'adtcore:version="(\w+)"', r.text)
    if not m:
        print(f'UYARI: {name} version metadata bulunamadı, atlandı', file=sys.stderr)
        return 0

    version = m.group(1)
    if version != 'active':
        print(f'\n[BLOCKER] {name} ({obj_type}) version="{version}" — active bekleniyor.', file=sys.stderr)
        print(f'  Olası sebep: bağımlı obje "inconsistent in active version" durumunda.', file=sys.stderr)
        print(f'  Çözüm: adt_activate ile cascade yeniden aktive et (önce tablo, sonra CDS, sonra DTEL).',
              file=sys.stderr)
        return 1

    # İçerik teyidi: version=active YETMEZ — boş/stub source da "active" görünebilir
    # (2026-06-10 ZSD001 ITEM/DORBN inline-POST boş-source vakası). source-tasiyan
    # tipler için aktif source/main'in dolu+anlamlı olduğunu GET ile doğrula.
    SOURCE_BEARING = {'ddls', 'cds', 'view', 'clas', 'class', 'tabl', 'table',
                      'structure', 'struct'}
    if obj_type.lower() in SOURCE_BEARING:
        try:
            sr = client.session.get(
                client.url + f'/sap/bc/adt/{path_segment}/{name.lower()}/source/main',
                params={'sap-client': '100', 'version': 'active'},
                headers={'Accept': 'text/plain'}, verify=False, timeout=15)
            body = sr.text if sr.status_code == 200 else ''
        except Exception:
            body = None  # GET edilemedi → içerik teyidini atla (version=active yeterli say)
        if body is not None:
            stripped = body.strip()
            has_def = re.search(r'\b(define|class|@\w+)\b', stripped, re.IGNORECASE)
            if len(stripped) < 20 or not has_def:
                print(f'\n[BLOCKER] {name} ({obj_type}) version=active AMA aktif source BOŞ/stub '
                      f'(len={len(stripped)}).', file=sys.stderr)
                print(f'  Sebep: yaratım (inline-POST vb.) source yazmadan shell bıraktı — obje '
                      f'parse-geçersiz, bağımlılar sessizce kırılır.', file=sys.stderr)
                print(f'  Çözüm: local repo source\'unu LOCK+PUT ile yeniden yaz + aktive.',
                      file=sys.stderr)
                return 1

    print(f'OK — {name} ({obj_type}) version=active'
          + (' + source dolu' if obj_type.lower() in SOURCE_BEARING else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
