#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Production tool: Create multiple SAP Z Data Elements (DTEL) via ADT REST in one batch.

Çözüm referansı: SAP_ADT_PLAYBOOK.md §26.2 (DTEL yaratma pattern'i)

KRİTİK NOTLAR (Playbook §26.5):
- Eski namespace `<dtel:wbobj xmlns:dtel="...wbobj/dictionary/dtel">` SILENT EMPTY döner.
  Mutlaka `<blue:wbobj xmlns:blue="...wbobj/dictionary/dtel">` + nested `<dtel:dataElement>` kullan.
- 3 attribute eksikse labels kayıt olmaz: `responsible`, `abapLanguageVersion`, `language`
- `sap-language=TR` hem query param hem header — ikisinde de gönder
- Update gerekirse: DELETE + tekrar CREATE (PUT bu sistemde broken — playbook'ta sabit)

Kullanım:
    python populate_dataelements.py \\
        --package ZSD001_CLC \\
        --transport <TRANSPORT> \\
        --responsible <SAP_USER> \\
        --csv <source_root>/ZSD001_CLC/dataelements.csv \\
        --cwd <PROJECT_ROOT>

CSV format (UTF-8, header'lı):
    name,type_kind,type_name,datatype,length,decimals,description,short,medium,long,heading

    ⛔ TÜM kolonlar ZORUNLUDUR ve hiçbiri boş bırakılamaz (fail-closed; ADR 0005-D
       + gate `check_dtel_creation_labels.py` R1-R5). Boş `decimals` sessizce `0`
       OLMAZ — `0` geçerli bir değerdir (canlı korpus: 90 satırın 87'si açıkça `0`).

    type_kind = **yalnız `domain`**. ⛔ `BUILTIN` KABUL EDİLMEZ: SAP'de öyle bir
                typeKind YOKTUR; `typeKind=BUILTIN` + boş `typeName` aktivasyonda
                *"No domain or data type was defined"* ile düşer
                (playbook/adt-domain-dtel.md §26.6).
    type_name = Domain adı (Z veya SAP standart). Built-in tip için de BURAYA yazılır:
                `DATS` / `TIMS` / `INT1` / `INT2` / `INT4` / `INT8`.
    datatype  = CHAR / NUMC / DATS / INT2 / INT4 / DEC / QUAN
    length    = numeric (e.g. 10)
    decimals  = numeric (e.g. 0 ya da 3)

    Labels (TR):
      short    = max 10 char (kısa)
      medium   = max 20 char (orta)
      long     = max 40 char (uzun)
      heading  = max 55 char (heading)

Örnek satır:
    ZSD001_E_VOYNO,domain,ZSD001_D_VOYNO,NUMC,10,0,Sefer Numarası,Sefer,Sefer No,Sefer Numarası,Sefer Numarası
    ZSD001_E_DEPDATE,domain,DATS,DATS,8,0,Planlanan Kalkış Tarihi,Kalkış,Planlı Kalkış,Planlanan Kalkış Tarihi,Planlanan Kalkış Tarihi
"""

import argparse
import csv
import sys
import io
import urllib3
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))
from sap_adt_lib import set_explicit_working_dir, SAPADTClient
from utils.ddic_aktivasyon import aktivasyon_notu   # "yaratildi != aktif" kapanis notu (tek kaynak)


# CSV sozlesmesi — TEK KAYNAK (docstring ile kodun ayrismasini onler; populate_tables B-9)
REQUIRED_CSV_COLUMNS = ('name', 'type_kind', 'type_name', 'datatype', 'length',
                        'decimals', 'description', 'short', 'medium', 'long', 'heading')
OPTIONAL_CSV_COLUMNS = ()

# playbook/adt-domain-dtel.md — TR label max uzunluklari.
# ⚠ Denetci `scripts/validators/check_dtel_creation_labels.py` (R4) AYNI degerleri
# kullanir. Ureticiyle denetci ayrisirsa gate yesil derken arac metni kirpar.
LABEL_MAX = (('short', 10), ('medium', 20), ('long', 40), ('heading', 55))


class DtelCsvKolonEksikError(ValueError):
    """CSV BASLIGINDA zorunlu kolon YOK — yazma BASLAMADAN durdurulur."""


class DtelSatiriEksikError(ValueError):
    """CSV'de YARIM/GECERSIZ doldurulmus satir(lar) var — yazma BASLAMADAN durdurulur."""


def load_dataelements_from_csv(csv_path: Path) -> list:
    """CSV oku -> [{...}, ...]. ⛔ FAIL-CLOSED, yazma (CSRF/POST) BASLAMADAN.

    Guard'lar bilerek BURADA (uretim noktasinda) duruyor: `main()`e konsaydi bu
    fonksiyonu dogrudan import eden bir cagiran onlari atlardi.

    ⚠ URETICI <-> DENETCI TEK KAYNAK: `scripts/validators/check_dtel_creation_labels.py`
    (`# ENFORCES: C-DTEL-CREATE-01`) DTEL CSV'sinde su kurallari zorluyor:
      R1 `name` dolu + Z/Y ile baslar        R2 4 label'in hicbiri bos degil
      R3 `description` bos degil             R4 label uzunluklari <= 10/20/40/55
      R5 `type_kind=domain` ise `type_name` dolu
    Denetci gate'in gerekce notu ureticiyi ACIKCA sucluyordu: *"populate_dataelements.py
    bu kontrolleri YAPMIYOR: yalniz MAX uzunluga bakiyor ve asarsa `[WARN] (will trim)`
    deyip SESSIZCE kirpiyor; label/description BOSLUGUNU hic kontrol etmiyor"*.
    Bu fonksiyon o bosluğu kapatir — gate ne bekliyorsa uretici artik onu yapar.

    ⚠ HAM alan okunur, NORMALIZASYONDAN ONCE (kardes kusur `populate_message_class`
    #41 Y-1). Ornekler: `int(r.get('decimals','0') or '0')` bos `decimals`i sessizce
    **0** yapardi ve `0` GECERLI bir degerdir (canli korpus: 2 gercek
    `dataelements.csv` / 90 satir -> **87 satir acikca `0`**); bos `type_kind` ise
    `.lower() != 'builtin'` testinden gecip sessizce **'domain'** olurdu ve
    `<dtel:typeName/>` BOS giderdi -> playbook §26.5: *"domain bagi KAYBOLUR"*
    (HTTP 201 doner, DTEL bozuk yaratilir).

    TAMAMEN bos satir dolgu sayilir, sessizce atlanir.
    """
    rows = []
    eksikler = []                      # (satir_no, ad, alan, sebep)
    with open(csv_path, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        basliklar = [(h or '').strip() for h in (reader.fieldnames or [])]
        yok = [c for c in REQUIRED_CSV_COLUMNS if c not in basliklar]
        if yok:
            raise DtelCsvKolonEksikError(
                'CSV zorunlu kolon(lar) eksik: %s\n'
                '  Bulunan baslik: %s\n'
                '  Beklenen      : %s\n'
                '  ⚠ Eskiden eksik kolon `r.get(kolon, <varsayilan>)` ile SESSIZCE\n'
                '    varsayilana dusuyordu (length -> 10, datatype -> CHAR,\n'
                '    type_kind -> domain): label\'siz/yanlis tipli DTEL yaratilir.'
                % (', '.join(yok), ', '.join(basliklar) or '(bos)',
                   ', '.join(REQUIRED_CSV_COLUMNS)))

        for r in reader:
            satir_no = reader.line_num          # CSV'deki GERCEK satir (header dahil)
            ham = {k: str(r.get(k) or '').strip() for k in REQUIRED_CSV_COLUMNS}
            if not any(ham.values()):
                continue                        # dolgu/ayirac satiri — hata DEGIL
            ad = ham['name']
            bos = [a for a in REQUIRED_CSV_COLUMNS if not ham[a]]
            if bos:
                for a in bos:
                    eksikler.append((satir_no, ad, a, 'BOS'))
                continue                        # <- FAIL-CLOSED: satir ISLENMEZ

            hatali = False
            if not ad.upper().startswith(('Z', 'Y')):
                eksikler.append((satir_no, ad, 'name',
                                 'Z/Y ile BASLAMIYOR (KESIN YASAKLAR madde A)'))
                hatali = True
            if ham['type_kind'].lower() != 'domain':
                # ⛔ `BUILTIN` BILEREK REDDEDILIR — playbook/adt-domain-dtel.md §26.6:
                # `typeKind=BUILTIN` + bos `typeName` AKTIVASYONDA duser
                # ("No domain or data type was defined"). SAP'de BUILTIN diye bir
                # typeKind YOKTUR; built-in tip `typeKind=domain` + `type_name=DATS`
                # (INT2/INT4/TIMS...) olarak yazilir. Canli korpusta (90 satir)
                # BUILTIN kullanan **0** satir var -> bu ret 0 FP uretir.
                eksikler.append((satir_no, ad, 'type_kind',
                                 "yalniz 'domain' kabul edilir (gorulen: %r). "
                                 "Built-in tip icin: type_kind=domain + "
                                 "type_name=DATS/TIMS/INT1/INT2/INT4/INT8 "
                                 "(playbook adt-domain-dtel.md §26.6)"
                                 % ham['type_kind']))
                hatali = True
            for alan, sinir in LABEL_MAX:
                if len(ham[alan]) > sinir:
                    eksikler.append((satir_no, ad, alan,
                                     '%d karakter > %d (populate ESKIDEN SESSIZCE '
                                     'kirpiyordu; kirpma ONAYLI metni degistirir)'
                                     % (len(ham[alan]), sinir)))
                    hatali = True
            try:
                uzunluk = int(ham['length'])
                ondalik = int(ham['decimals'])
            except ValueError:
                eksikler.append((satir_no, ad, 'length/decimals',
                                 'SAYI DEGIL (length=%r decimals=%r)'
                                 % (ham['length'], ham['decimals'])))
                hatali = True
            if hatali:
                continue
            rows.append({
                'name': ad,
                'type_kind': ham['type_kind'],
                'type_name': ham['type_name'],
                'datatype': ham['datatype'].upper(),
                'length': uzunluk,
                'decimals': ondalik,
                'description': ham['description'],
                'short': ham['short'],
                'medium': ham['medium'],
                'long': ham['long'],
                'heading': ham['heading'],
            })

    if eksikler:
        detay = '\n'.join('    satir %d (%s): `%s` %s' % (sn, ad or '?', alan, sebep)
                          for sn, ad, alan, sebep in eksikler)
        raise DtelSatiriEksikError(
            '%d CSV alani YARIM/GECERSIZ — HICBIRI yazilmadi (fail-closed).\n'
            '  ⚠ Yazilsaydi: bos 4-label ve bos `description` ADR 0005-D ihlali olan\n'
            '    ETIKETSIZ DTEL yaratirdi; sinir asan label SESSIZCE KIRPILIRDI;\n'
            '    bos `type_kind` sessizce `domain` olur ve BOS `typeName` ile\n'
            '    "domain bagi KAYBOLUR" (HTTP 201 doner ama DTEL bozuktur).\n'
            '  ⛔ Bu arac METIN ONERMEZ (ADR 0005-D): eksik metinleri KULLANICIDAN al.\n'
            '  Eksik/gecersiz alanlar:\n%s\n'
            '  (Not: `0` GECERLI bir decimals degeridir — acikca yazildiginda kabul edilir.)'
            % (len(eksikler), detay))
    return rows


def build_xml(name: str, description: str, package: str, responsible: str,
              type_kind: str, type_name: str,
              datatype: str, length: int, decimals: int,
              short: str, medium: str, long: str, heading: str) -> str:
    """Build DTEL XML — sabahki başarılı pattern (Playbook §26.2).

    ⚠ Burada uzunluk KIRPMASI YOKTUR ve olmamalidir. Eskiden bu fonksiyon
    `[WARN] ... (will trim)` deyip label'i SESSIZCE kirpiyordu; kirpilan etiket
    ekranda YARIM durur ve "onayli metin buydu" diye kimse suphelenmez. Guard artik
    `load_dataelements_from_csv` icinde (TEK zorlama noktasi) ve YAZMADAN ONCE durur
    — kardes arac `populate_message_class.build_xml` de ayni sekilde yalniz bicimler.
    Iki yerde ayni degismezi tutmak, mutasyonla olcumu de imkansiz kilardi.
    """
    name = name.upper()
    package = package.upper()
    length_str = f'{length:06d}'
    decimals_str = f'{decimals:06d}'

    # type_kind: SAP'de yalniz 'domain' vardir (playbook §26.6 — 'BUILTIN' YOK).
    type_kind_str = 'domain'
    type_name_str = type_name

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<blue:wbobj adtcore:responsible="{responsible}"
            adtcore:masterLanguage="TR"
            adtcore:abapLanguageVersion="standard"
            adtcore:name="{name}"
            adtcore:type="DTEL/DE"
            adtcore:description="{xml_escape(description)}"
            adtcore:language="TR"
            xmlns:blue="http://www.sap.com/wbobj/dictionary/dtel"
            xmlns:adtcore="http://www.sap.com/adt/core">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{package.lower()}"
                      adtcore:type="DEVC/K"
                      adtcore:name="{package}"/>
  <dtel:dataElement xmlns:dtel="http://www.sap.com/adt/dictionary/dataelements">
    <dtel:typeKind>{type_kind_str}</dtel:typeKind>
    <dtel:typeName>{xml_escape(type_name_str)}</dtel:typeName>
    <dtel:dataType>{datatype}</dtel:dataType>
    <dtel:dataTypeLength>{length_str}</dtel:dataTypeLength>
    <dtel:dataTypeDecimals>{decimals_str}</dtel:dataTypeDecimals>
    <dtel:shortFieldLabel>{xml_escape(short)}</dtel:shortFieldLabel>
    <dtel:shortFieldLength>{len(short)}</dtel:shortFieldLength>
    <dtel:shortFieldMaxLength>10</dtel:shortFieldMaxLength>
    <dtel:mediumFieldLabel>{xml_escape(medium)}</dtel:mediumFieldLabel>
    <dtel:mediumFieldLength>{len(medium)}</dtel:mediumFieldLength>
    <dtel:mediumFieldMaxLength>20</dtel:mediumFieldMaxLength>
    <dtel:longFieldLabel>{xml_escape(long)}</dtel:longFieldLabel>
    <dtel:longFieldLength>{len(long)}</dtel:longFieldLength>
    <dtel:longFieldMaxLength>40</dtel:longFieldMaxLength>
    <dtel:headingFieldLabel>{xml_escape(heading)}</dtel:headingFieldLabel>
    <dtel:headingFieldLength>{len(heading)}</dtel:headingFieldLength>
    <dtel:headingFieldMaxLength>55</dtel:headingFieldMaxLength>
    <dtel:searchHelp/>
    <dtel:searchHelpParameter/>
    <dtel:setGetParameter/>
    <dtel:defaultComponentName/>
    <dtel:deactivateInputHistory>false</dtel:deactivateInputHistory>
    <dtel:changeDocument>false</dtel:changeDocument>
    <dtel:leftToRightDirection>false</dtel:leftToRightDirection>
    <dtel:deactivateBIDIFiltering>false</dtel:deactivateBIDIFiltering>
  </dtel:dataElement>
</blue:wbobj>'''


def dtel_varlik_sondasi(client: SAPADTClient, name: str) -> tuple:
    """DTEL var mi? UC-DEGERLI: (True,'checked_found') · (False,'checked_absent') ·
    (None,'unavailable:<sebep>').

    ⛔ `None` "YOK" DEGILDIR. Eskiden `return r.status_code == 200` idi: GET 500/403/
    timeout **False** donuyordu ve cagiran "obje yok" okuyup **CREATE** dalina
    sapiyordu (sonuc okuma degil YAZMA). Kanonik ayrim:
    `mcp_servers/sap_adt/tools/atom.py` `_varlik_sondasi`.
    """
    try:
        r = client.session.get(
            client.url + f'/sap/bc/adt/ddic/dataelements/{name.lower()}',
            verify=False, timeout=10
        )
    except Exception as exc:            # noqa: BLE001 — teshis bozulmasin
        return None, 'unavailable:%s' % type(exc).__name__
    kod = getattr(r, 'status_code', None)
    if kod == 200:
        return True, 'checked_found'
    if kod == 404:
        return False, 'checked_absent'
    return None, 'unavailable:http_%s' % kod


def create_one(client: SAPADTClient, csrf: str, row: dict,
               package: str, responsible: str, transport: str,
               force_recreate: bool = False, dry_run: bool = False) -> bool:
    name = row['name'].upper()

    if dry_run:
        exists = False
    else:
        var, sonda = dtel_varlik_sondasi(client, name)
        if var is None:
            # "olculemedi" != "yok" — ne CREATE ne DELETE denenir (fail-closed).
            print(f'  [FAIL] {name} varlik kontrolu OLCULEMEDI — {sonda}')
            print(f'         "olculemedi" != "yok": CREATE/DELETE DENENMEDI (fail-closed).')
            return False
        exists = var

    if exists and not force_recreate:
        print(f'  [SKIP] {name} zaten var')
        return True

    xml_payload = build_xml(
        name=name, description=row['description'],
        package=package, responsible=responsible,
        type_kind=row['type_kind'], type_name=row['type_name'],
        datatype=row['datatype'], length=row['length'], decimals=row['decimals'],
        short=row['short'], medium=row['medium'], long=row['long'], heading=row['heading'],
    )

    if dry_run:
        print(f'\n--- DRY-RUN XML: {name} ---')
        print(xml_payload[:1500])
        return True

    # DELETE first if force_recreate and exists
    if force_recreate and exists:
        del_resp = client.session.delete(
            client.url + f'/sap/bc/adt/ddic/dataelements/{name.lower()}',
            params={'corrNr': transport},
            headers={'X-CSRF-Token': csrf, 'Accept': 'application/xml'},
            verify=False, timeout=20
        )
        if del_resp.status_code not in (200, 204):
            print(f'  [WARN] DELETE {name} failed: {del_resp.status_code}')

    r = client.session.post(
        client.url + '/sap/bc/adt/ddic/dataelements',
        params={'corrNr': transport, 'sap-language': 'TR'},
        headers={
            'X-CSRF-Token': csrf,
            'Content-Type': 'application/vnd.sap.adt.dataelements.v2+xml; charset=utf-8',
            'Accept': 'application/vnd.sap.adt.dataelements.v2+xml',
            'sap-client': '100',
            'sap-language': 'TR',
        },
        data=xml_payload.encode('utf-8'),
        verify=False, timeout=30
    )
    if r.status_code in (200, 201):
        print(f'  [OK]   {name}  ({row["type_kind"]} → {row["type_name"] or row["datatype"]})')
        return True
    else:
        print(f'  [FAIL] {name} status={r.status_code}')
        print(f'         Body: {r.text[:400]}')
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Batch-create SAP Z Data Elements from CSV (Playbook §26.2 pattern)'
    )
    parser.add_argument('--package', required=True, help='Package (e.g. ZSD001_CLC)')
    parser.add_argument('--transport', required=True, help='Transport (e.g. <TRANSPORT>)')
    parser.add_argument('--responsible', default='<SAP_USER>')
    parser.add_argument('--csv', required=True, help='CSV file path')
    parser.add_argument('--cwd', help='Working dir with .conn_adt')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--force-recreate', action='store_true',
                        help='DELETE existing DTELs and re-CREATE (Playbook §26.5 pattern)')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f'[FAIL] CSV bulunamadı: {csv_path}')
        return 1

    # Guard'lar load_dataelements_from_csv ICINDE (uretim noktasi), main()'de DEGIL.
    try:
        rows = load_dataelements_from_csv(csv_path)
    except (DtelCsvKolonEksikError, DtelSatiriEksikError) as e:
        print(f'[FAIL] {e}')
        return 1

    print(f'[INFO] CSV → {len(rows)} DTEL yüklendi')

    if not rows:
        print('[FAIL] CSV boş')
        return 1

    client = SAPADTClient()

    csrf = ''
    if not args.dry_run:
        client._invalidate_csrf_cache()
        r = client.session.get(
            client.url + '/sap/bc/adt/discovery',
            params={'sap-client': '100', 'sap-language': 'TR'},
            headers={'X-CSRF-Token': 'Fetch'},
            verify=False
        )
        csrf = r.headers.get('X-CSRF-Token', '')
        if not csrf:
            print('[FAIL] CSRF token alınamadı')
            return 1
        print(f'[OK] CSRF: {csrf[:24]}...')

    ok = 0
    fail = 0
    islenenler = []
    for row in rows:
        if create_one(client=client, csrf=csrf, row=row,
                      package=args.package, responsible=args.responsible,
                      transport=args.transport, force_recreate=args.force_recreate,
                      dry_run=args.dry_run):
            ok += 1
            islenenler.append(row['name'])
        else:
            fail += 1

    print(f'\n=== Sonuç: {ok} başarılı, {fail} hatalı ===')
    # "exit 0 != kanit": obje islendi ama AKTIF DEGIL. Sessiz [OK] kabul edilemez.
    if not args.dry_run:
        print(aktivasyon_notu('dataelement', islenenler, args.cwd))
    return 0 if fail == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
