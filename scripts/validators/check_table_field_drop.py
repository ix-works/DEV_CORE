"""
check_table_field_drop.py — Z tablo ALTER'da mevcut alanın DROP / RENAME / TİP
değişikliğini SAP'ye yazmadan önce yakalar (DDIC veri kaybı koruması).

Sorun (2026-06-10, reviewer-kör vakası): run_review.py 'table_update' zinciri
sadece CURR/QUAN + deprecated-annotation çalıştırıyordu. Bir ALTER source'u ~15
alanı DROP edip var olmayan DTEL'e referans verdiği halde reviewer PASS verdi.
Checklist'te C-TBL-DROP-01 / C-TBL-RENAME-01 / C-TBL-TYPE-01 "BLOCKER" yazıyordu
ama arkalarında çalıştırılabilir bir script YOKTU. Bu validator o boşluğu kapatır.

Yöntem: yeni source'tan tablo adını + (alan → dtel) haritasını çıkar; SAP'den
CANLI source'u GET ile çek, onun (alan → dtel) haritasıyla karşılaştır.
  - Mevcut alan yeni source'ta YOK            → DROP        → BLOCKER
  - Mevcut alanın DTEL'i değişmiş             → TYPE/RENAME → BLOCKER
  - Yeni alan eklenmiş (additive)             → OK (ALTER'ın amacı)
  - Tablo SAP'de yok (yeni yaratım) / bağlantı yok → OK (skip, kapsam dışı)

Kullanım:
    python scripts/validators/check_table_field_drop.py <tablo_ddl_path>
    # Bilinçli (kullanıcı+lider onaylı) DROP — yalnız ADI VERİLEN alanlar geçer:
    python scripts/validators/check_table_field_drop.py <path> --ack-drop order_amount,order_currency

--ack-drop NOTU (ADR 0005-B): Sadece açıkça onaylanmış, ADI YAZILAN alanların DROP'u
BLOCKER yerine ACK-WARNING olur. İsmi verilmeyen herhangi bir DROP veya herhangi bir
TYPE/RENAME değişikliği YİNE BLOCKER kalır (kör/blanket bypass DEĞİL — hedefli ack).

Exit kodu: 0 temiz/skip/ack · 1 BLOCKER (onaysız DROP/RENAME/TYPE)
"""
# ENFORCES: C-TBL-DROP-01, C-TBL-RENAME-01, C-TBL-TYPE-01, BE-15, BE-16  (ADR 0019 coverage binding)
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

# 'key fieldname : dtel ...;' veya 'fieldname : dtel ...;'
FIELD_RE = re.compile(
    r'^\s*(?:key\s+)?([a-z][a-z0-9_]*)\s*:\s*([a-z][a-z0-9_/]*)',
    re.IGNORECASE | re.MULTILINE)
TABLE_NAME_RE = re.compile(r'define\s+table\s+([a-z][a-z0-9_]*)', re.IGNORECASE)
# Alan satırı OLMAYAN anahtar kelimeler (yanlış yakalamayı önle)
_NON_FIELD = {'define', 'table', 'with', 'include'}


def parse_fields(text: str) -> dict:
    """source metninden {field_lower: dtel_lower} haritası."""
    out = {}
    for fld, dtel in FIELD_RE.findall(text):
        if fld.lower() in _NON_FIELD:
            continue
        out[fld.lower()] = dtel.lower()
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Z tablo ALTER DROP/RENAME/TYPE guard (canlı SAP source diff)')
    parser.add_argument('path', help='tablo DDL path')
    parser.add_argument('--ack-drop', default='',
                        help='Onaylı DROP alanları (virgülle). Kullanıcı+lider bilinçli '
                             'silme onayı verdiğinde; SADECE bu alanlar ACK-WARNING olur, '
                             'isimsiz drop/type değişikliği yine BLOCKER.')
    args, _ = parser.parse_known_args()
    path = Path(args.path)
    ack = {f.strip().lower() for f in args.ack_drop.split(',') if f.strip()}
    if not path.exists():
        print(f'HATA: {path} bulunamadı', file=sys.stderr)
        return 1

    new_text = path.read_text(encoding='utf-8', errors='replace')
    m = TABLE_NAME_RE.search(new_text)
    if not m:
        print(f'OK — {path.name} bir DDIC tablo tanımı değil (define table yok), kapsam dışı')
        return 0
    table = m.group(1)
    new_fields = parse_fields(new_text)
    if not new_fields:
        print(f'OK — {path.name} alan çıkarılamadı, kapsam dışı')
        return 0

    # SAP'den canlı source çek
    sys.path.insert(0, str(Path(__file__).parent.parent))
    try:
        from sap_adt_lib import SAPADTClient  # type: ignore
        client = SAPADTClient()
        r = client.session.get(
            client.url + f'/sap/bc/adt/ddic/tables/{table.lower()}/source/main',
            params={'sap-client': '100', 'sap-language': 'TR'},
            headers={'Accept': 'text/plain'}, verify=False, timeout=15)
    except Exception as e:
        print(f'UYARI: SAP bağlantısı kurulamadı, DROP-guard atlandı: {e}', file=sys.stderr)
        return 0

    if r.status_code == 404:
        print(f'OK — {table.upper()} SAP\'de yok (yeni yaratım) → DROP-guard kapsam dışı')
        return 0
    if r.status_code != 200:
        print(f'UYARI: canlı source alınamadı (HTTP {r.status_code}), DROP-guard atlandı',
              file=sys.stderr)
        return 0

    live_fields = parse_fields(r.text)
    if not live_fields:
        print(f'UYARI: canlı {table.upper()} source\'undan alan çıkarılamadı, atlandı',
              file=sys.stderr)
        return 0

    dropped = [f for f in live_fields if f not in new_fields]
    type_changed = [(f, live_fields[f], new_fields[f])
                    for f in live_fields if f in new_fields and live_fields[f] != new_fields[f]]
    added = [f for f in new_fields if f not in live_fields]

    if not dropped and not type_changed:
        msg = f'OK — {table.upper()} ALTER additive/güvenli'
        if added:
            msg += f' (+{len(added)} yeni alan: {", ".join(added)})'
        print(msg)
        return 0

    # Onaylı (ack) DROP'ları ayır — kullanıcı+lider bilinçli silme onayı (ADR 0005-B).
    # type_changed ack KAPSAMI DIŞINDA: rename/tip riski ayrı, her zaman BLOCKER.
    unack_dropped = [f for f in dropped if f not in ack]
    ack_dropped = [f for f in dropped if f in ack]

    if not unack_dropped and not type_changed:
        print(f'[ACK-WARNING] {table.upper()} — onaylı DROP (kullanıcı+lider bilinçli, '
              f'ADR 0005-B gate geçildi): {", ".join(ack_dropped)}. '
              f'Diğer drop/tip değişikliği yok; veri-kaybı bilinçli kabul edildi.')
        return 0

    print(f'\n[BLOCKER] {table.upper()} ALTER veri-kaybı riski '
          f'(checklist C-TBL-DROP/RENAME/TYPE-01):', file=sys.stderr)
    for f in unack_dropped:
        print(f'  DROP   : mevcut alan \'{f}\' ({live_fields[f]}) yeni source\'ta YOK '
              f'→ veri kaybı (onaysız — geçmek için --ack-drop {f})', file=sys.stderr)
    for f, old, new in type_changed:
        print(f'  TYPE   : \'{f}\' DTEL değişti {old} → {new} '
              f'(rename/tip değişikliği, veri-dönüşüm riski — ack KAPSAMI DIŞI)', file=sys.stderr)
    if ack_dropped:
        print(f'  NOT    : {", ".join(ack_dropped)} onaylıydı ama başka onaysız drop/tip '
              f'değişikliği var → yine BLOCKER (hedefli ack, blanket değil)', file=sys.stderr)
    print('\nÇözüm: Bilinçli silme ise ilgili alanı --ack-drop <alan> ile onayla (kullanıcı+lider '
          'onayı sonrası). Kazara ise canlı source\'u GET ile alıp sadece additive değişiklik yap.',
          file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
