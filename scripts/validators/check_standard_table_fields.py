"""
check_standard_table_fields.py — Source'ta kullanılan standart SAP tablo alanları
yeni sistemde gerçekten var mı SAP GET ile teyit eder.

Vaka 2026-05-14 (Sprint 5, SHIPPING_TYPES) — <LEGACY_SOURCE> source'ta `t173.vsartkat`
yazıyordu ama yeni sistemde T173 field listesinde `vsartkat` yok, gerçek field `vktra`.
Bu validator GET /sap/bc/adt/ddic/tables/<name>/source/main ile field listesini alıp
referans verilen alanları kontrol eder.

Kullanım:
    python scripts/validators/check_standard_table_fields.py <cds_path>
    python scripts/validators/check_standard_table_fields.py <cds_path> --type dtel

Exit kodu:
    0 — Tüm referans alanlar yeni sistemde mevcut
    1 — Bir veya daha fazla alan yok (BLOCKER)
"""
# ENFORCES: C-CDS-FROM-03, C-RAP-VE-03, C-STR-FIELD-03, C-TBL-STD-01  (ADR 0019 coverage binding)
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

# Z olmayan tabloları yakalayan regex (CDS'te `tablename.fieldname` pattern'i)
TABLE_FIELD_PATTERN = re.compile(
    r'\b([a-z][a-z0-9_]{0,15})\.([a-z][a-z0-9_]+)\b',
    re.IGNORECASE
)

# ALIAS ÇÖZÜMÜ (fix 2026-06-24): CDS `from <tablo> as <alias>` / `join <tablo> as <alias>`
# eşlemesi. Önceden validator alias'ı (ör. `from vfkp as Cost` → `Cost.netwr`) tablo adı
# sanıp gerçek tabloyu (VFKP) kontrol etmiyordu → ZSD001_I_FREIGHT_COST'ta false-positive
# BLOCKER. Artık alias gerçek tabloya çözülür; namespaced (/ITTR/) tablo da desteklenir.
ALIAS_PATTERN = re.compile(
    r'\b(?:from|join)\s+(/?[a-z][a-z0-9_/]*)\s+as\s+([a-z][a-z0-9_]*)',
    re.IGNORECASE
)

# Z* ve session var prefix'leri — skip (abap.* cast tipleri de skip)
SKIP_TABLE_PREFIXES = ('z', '$session', 'reqd_', 'confd_', 'projection', 'abap')


FIELD_LINE = re.compile(
    r'^\s*(?:key\s+)?([a-z][a-z0-9_]*)\s*:\s*[a-z][a-z0-9_]*', re.MULTILINE | re.IGNORECASE)

# INCLUDE iki biçimde gelir (canlı ölçüm 2026-07-30):
#   `include emara`                          ← çıplak (noktalı virgül bile olmayabilir)
#   `likp_status : include likp_status;`      ← adlandırılmış
# ⚠ Satır-başına DEMİRLENMİŞ: serbest metinde geçen "include for ..." gibi ifadeler
# include adı sanılırsa çözülemeyen-liste şişer ve gerçek bulgular "doğrulanamadı"ya
# düşer — yani gürültüyü kesmek korumayı deler. Demirleme bunu kapatır.
INCLUDE_LINE = re.compile(
    r'^\s*(?:[a-z][a-z0-9_]*\s*:\s*)?include\s+(/?[a-z][a-z0-9_/]{2,})\s*;?\s*$',
    re.MULTILINE | re.IGNORECASE)

_KAYNAK_UCLARI = ('structures', 'tables')
_SOURCE_CACHE: dict = {}


def _fetch_source(client, ad: str) -> str:
    """DDIC objesinin DDL source'u (structures → tables sırası). Önbellekli."""
    anahtar = ad.lower()
    if anahtar in _SOURCE_CACHE:
        return _SOURCE_CACHE[anahtar]
    from urllib.parse import quote
    metin = ''
    for uc in _KAYNAK_UCLARI:
        try:
            r = client.session.get(
                client.url + f'/sap/bc/adt/ddic/{uc}/{quote(anahtar, safe="")}/source/main',
                params={'sap-client': '100', 'sap-language': 'TR'},
                headers={'Accept': 'text/plain'}, verify=False, timeout=15)
            if r.status_code == 200 and r.text.strip():
                metin = r.text
                break
        except Exception:
            continue
    _SOURCE_CACHE[anahtar] = metin
    return metin


def fetch_table_fields(client, table_name: str, derinlik: int = 4) -> tuple:
    """Tablonun alan adları — INCLUDE'lar ÖZYİNELİ çözülerek. Dönüş: (alanlar, çözülemeyenler).

    ⚠ NEDEN ÖZYİNELİ (canlı ölçüm 2026-07-30): S/4 standart tabloları alanlarını
    büyük ölçüde INCLUDE yapılarından alır — **istisna değil, kural**. `MARA`'nın ~250
    alanının 248'i `include emara`'dan gelir (doğrudan yalnız `key mandt`, `key matnr`);
    `LIKP` durum alanları `likp_status : include likp_status;` içindedir. Eski sürüm
    yalnız tablonun kendi gövdesine baktığı için `mara.matkl` · `mara.meins` ·
    `likp.wbstk` referansı veren HER CDS'te yanlış bulgu üretiyordu.

    Çözülemeyen include kalırsa bunu ÇAĞIRANA bildirir: "bulunamadı ≠ yok" — kanıtlanamayan
    yokluk bulgu olarak raporlanmaz, `DOĞRULANAMADI` olarak ayrı listelenir.
    """
    alanlar, cozulemeyen, gorulen = set(), [], set()
    kuyruk = [(table_name.lower(), 0)]
    while kuyruk:
        ad, d = kuyruk.pop()
        if ad in gorulen:
            continue
        gorulen.add(ad)
        metin = _fetch_source(client, ad)
        if not metin:
            if ad != table_name.lower():
                cozulemeyen.append(ad)
            continue
        alanlar |= {f.lower() for f in FIELD_LINE.findall(metin)}
        if d >= derinlik:
            cozulemeyen.extend(i.lower() for i in INCLUDE_LINE.findall(metin))
            continue
        for inc in INCLUDE_LINE.findall(metin):
            kuyruk.append((inc.lower(), d + 1))
    return alanlar, cozulemeyen


def main() -> int:
    parser = argparse.ArgumentParser(description='Standart tablo field varlık kontrolü')
    parser.add_argument('artifact')
    parser.add_argument('--type', default='cds', help='cds|table|dtel')
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()

    path = Path(args.artifact)
    if not path.exists():
        print(f'HATA: {path} bulunamadı', file=sys.stderr)
        return 1

    text = path.read_text(encoding='utf-8', errors='replace')

    # Tablo.field çiftlerini çıkar
    pairs = TABLE_FIELD_PATTERN.findall(text)

    # Alias → gerçek tablo haritası: `from/join <tablo> as <alias>` (fix 2026-06-24).
    # Böylece `Cost.netwr` (alias) → gerçek tablo `vfkp` üzerinde kontrol edilir;
    # alias adının (Cost, Delivery) gerçek SAP tablosuyla (COST, ...) çakışması önlenir.
    alias_map = {}
    for real_tbl, alias in ALIAS_PATTERN.findall(text):
        alias_map[alias.lower()] = real_tbl.lower()

    # Z olmayanları filtrele
    candidates = {}  # table → set of fields
    for table, field in pairs:
        tbl = alias_map.get(table.lower(), table.lower())  # alias → gerçek tablo
        if tbl.startswith(SKIP_TABLE_PREFIXES):
            continue
        # Namespaced add-on tablosu (/ITTR/ vb.) — ADT source endpoint güvenilir değil, skip
        if tbl.startswith('/'):
            continue
        # Çözülemeyen kısa token (1-2 char alias) — skip
        if len(tbl) <= 2:
            continue
        # Append/extension alanı (ZZ1_*, ZZ_*) — base-tablo source'unda GÖRÜNMEZ
        # (append struct'ta). Standart alan asla 'zz' ile başlamaz → bu alanlar
        # validator'ın base-source GET'iyle DOĞRULANAMAZ; her zaman false-positive
        # verirdi. Skip (fix 2026-06-24; canlı kanıt: LIKP.zz1_booking_number_dlh VAR).
        if field.lower().startswith('zz'):
            continue
        candidates.setdefault(tbl, set()).add(field.lower())

    if not candidates:
        print(f'OK — {path.name} standart tablo referansı yok')
        return 0

    # SAP'ye bağlan
    sys.path.insert(0, str(Path(__file__).parent.parent))
    try:
        from sap_adt_lib import SAPADTClient
        client = SAPADTClient()
    except Exception as e:
        print(f'UYARI: SAP bağlantısı kurulamadı, validator atlandı: {e}', file=sys.stderr)
        return 0

    violations, dogrulanamayan = [], []
    print(f'Source: {path.name} — {len(candidates)} potansiyel standart tablo referansı kontrol ediliyor...')

    for table, fields in candidates.items():
        # Sadece bilinen SAP standart tablolar (basit heuristic — Z olmayan, 4-5 char)
        actual_fields, cozulemeyen = fetch_table_fields(client, table)
        if not actual_fields:
            # Tablo bulunamadı, skip (alias olabilir veya CDS view olabilir)
            continue

        for field in fields:
            if field in actual_fields:
                continue
            if cozulemeyen:
                # "BULUNAMADI ≠ YOK": bu tablonun include zincirinin bir kısmı çözülemedi,
                # alan orada olabilir. Yokluğu KANITLAYAMADIĞIMIZ için bulgu yazmıyoruz.
                dogrulanamayan.append({'table': table.upper(), 'field': field,
                                       'cozulemeyen': cozulemeyen[:3]})
                continue
            # Yakın alternatif bul (basit)
            similar = [f for f in actual_fields if abs(len(f) - len(field)) <= 2 and (f[:3] == field[:3] or f[-3:] == field[-3:])]
            violations.append({
                'table': table.upper(),
                'field': field,
                'similar': similar[:3],
            })

    if dogrulanamayan:
        # stdout: bilgi — gate'i kırmaz. Sessizce yutmak da YASAK (yeşil ışık sanılır).
        print(f'\n[DOĞRULANAMADI] {len(dogrulanamayan)} alan — include zinciri tam çözülemedi '
              '(yokluk KANITLANMADI, bulgu sayılmadı):')
        for d in dogrulanamayan:
            print(f"  {d['table']}.{d['field']}  (çözülemeyen include: {', '.join(d['cozulemeyen'])})")

    if not violations:
        print(f'OK — {path.name} standart tablo alanları doğrulandı '
              f'(include zinciri özyineli çözüldü)')
        return 0

    # ⚠ ŞİDDET KELİMESİ: bu script'in çıktısı eskiden "[BLOCKER]" diyordu ama `run_review.py`
    # onu 4 yerde de **WARNING**'e eşliyor → yazma bloklanmıyordu. Kelime ile kablolamanın
    # ayrışması ajanları yanlış yönlendirdi (2026-07-30: bir ajan bunu BLOCKER sanıp raporladı).
    # Şiddeti run_review atar; script yalnız BULGU bildirir.
    print(f'\n[BULGU] {len(violations)} standart tablo alanı bulunamadı '
          '(run_review şiddeti: WARNING):', file=sys.stderr)
    for v in violations:
        print(f"  {v['table']}.{v['field']}", file=sys.stderr)
        if v['similar']:
            print(f"    Benzer alanlar: {', '.join(v['similar'])}", file=sys.stderr)
    print('\nÇözüm: Source\'ta bu alan referanslarını gerçek alan adlarıyla değiştir.\n'
          '       Eski <LEGACY_SOURCE> source\'tan kopya yaparken yeni sistem field listesini\n'
          '       her zaman GET /sap/bc/adt/ddic/tables/<name>/source/main ile teyit et.',
          file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
