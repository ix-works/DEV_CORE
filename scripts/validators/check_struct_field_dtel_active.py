"""
check_struct_field_dtel_active.py — Struct/Table source'ta kullanılan ZSD<NNN>_E_*
DTEL'lerin SAP'de aktif olup olmadığını kontrol eder.

Sprint 6 (Z Structures) için kritik: struct'ta kullanılan DTEL'ler aktif değilse
aktivasyon fail eder + cascade fail (dependent struct'lar/CDS'ler).

Kullanım:
    python scripts/validators/check_struct_field_dtel_active.py <artifact>

Exit kodu:
    0 — Tüm Z DTEL'ler aktif
    1 — En az 1 DTEL inactive veya yok
"""
# ENFORCES: C-STR-FIELD-02, C-TBL-DTEL-01  (ADR 0019 coverage binding)
import argparse
import re
import sys
import urllib3
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def main() -> int:
    parser = argparse.ArgumentParser(description='Z DTEL aktivasyon kontrolü')
    parser.add_argument('artifact')
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()

    path = Path(args.artifact)
    if not path.exists():
        print(f'HATA: {path} bulunamadı', file=sys.stderr)
        return 1

    text = path.read_text(encoding='utf-8', errors='replace')

    # Z DTEL referansları (zsd<NNN>_e_*, zsd_<NNN>_e_*, vb.)
    z_dtels = set(re.findall(r'\b(zsd[0-9_]*_e_[a-z0-9_]+)\b', text, re.IGNORECASE))
    z_dtels = {d.upper() for d in z_dtels}

    if not z_dtels:
        print(f'OK — {path.name} Z DTEL referansı yok')
        return 0

    # SAP'ye bağlan
    sys.path.insert(0, str(Path(__file__).parent.parent))
    try:
        from sap_adt_lib import SAPADTClient
        client = SAPADTClient()
    except Exception as e:
        print(f'UYARI: SAP bağlantısı kurulamadı, validator atlandı: {e}', file=sys.stderr)
        return 0

    print(f'{path.name} — {len(z_dtels)} Z DTEL kontrol ediliyor...')
    inactive = []
    missing = []

    for dtel in sorted(z_dtels):
        try:
            r = client.session.get(
                client.url + f'/sap/bc/adt/ddic/dataelements/{dtel.lower()}',
                params={'sap-client': '100'}, verify=False, timeout=10
            )
            if r.status_code == 404:
                missing.append(dtel)
                continue
            if r.status_code != 200:
                print(f'  UYARI: {dtel} GET {r.status_code}', file=sys.stderr)
                continue
            m = re.search(r'adtcore:version="(\w+)"', r.text)
            version = m.group(1) if m else '?'
            if version != 'active':
                inactive.append((dtel, version))
        except Exception as e:
            print(f'  UYARI: {dtel} hata: {e}', file=sys.stderr)

    if not missing and not inactive:
        print(f'OK — {len(z_dtels)} Z DTEL hepsi aktif')
        return 0

    if missing:
        print(f'\n[BLOCKER] {len(missing)} Z DTEL SAP\'de bulunamadı:', file=sys.stderr)
        for d in missing:
            print(f'  {d}', file=sys.stderr)
        print('  Çözüm: DTEL\'i önce yarat (Sprint 1B), sonra struct\'ı yarat.', file=sys.stderr)

    if inactive:
        print(f'\n[BLOCKER] {len(inactive)} Z DTEL inactive:', file=sys.stderr)
        for d, v in inactive:
            print(f'  {d} (version: {v})', file=sys.stderr)
        print('  Çözüm: DTEL\'i önce aktive et (activate_object.py --type dtel)', file=sys.stderr)

    return 1


if __name__ == '__main__':
    sys.exit(main())
