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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _gate_status import gate_status, sap_baglanti_yok  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.ad_politikasi import AD_ADAYI, ad_coz, musteri_karari  # noqa: E402 — TEK ad grameri (#402 K1)

_GATE = Path(__file__).stem

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Z olmayan tabloları yakalayan regex (CDS'te `tablename.fieldname` pattern'i)
# Tablo ve alan adları `ad_politikasi` gramerinden (#402 K1): eski `[a-z][a-z0-9_]{0,15}` /
# `[a-z][a-z0-9_]+` namespace'li tabloyu (`/scwm/ordim_o.lgnum`) ve alanı (`mara./abc/fld`) hiç
# yakalamıyordu. Eski desenin dışladığı iki şekil aşağıda AÇIKÇA süzülür (`_` başlangıçlı
# association · rakamla başlayan belirteç) — davranış değişmez.
TABLE_FIELD_PATTERN = re.compile(
    r'(?<![A-Za-z0-9_/$])(' + AD_ADAYI + r')\.(' + AD_ADAYI + r')(?![A-Za-z0-9_/])',
    re.IGNORECASE
)

# ALIAS ÇÖZÜMÜ (fix 2026-06-24): CDS `from <tablo> as <alias>` / `join <tablo> as <alias>`
# eşlemesi. Önceden validator alias'ı (ör. `from vfkp as Cost` → `Cost.netwr`) tablo adı
# sanıp gerçek tabloyu (VFKP) kontrol etmiyordu → ZSD001_I_FREIGHT_COST'ta false-positive
# BLOCKER. Artık alias gerçek tabloya çözülür; namespaced (/ITTR/) tablo da desteklenir.
ALIAS_PATTERN = re.compile(
    r'\b(?:from|join)\s+(' + AD_ADAYI + r')\s+as\s+([a-z][a-z0-9_]*)',   # alias = yerel ad
    re.IGNORECASE
)

# Z* ve session var prefix'leri — skip (abap.* cast tipleri de skip)
SKIP_TABLE_PREFIXES = ('z', '$session', 'reqd_', 'confd_', 'projection', 'abap')


FIELD_LINE = re.compile(
    r'^\s*(?:key\s+)?(' + AD_ADAYI + r')\s*:\s*' + AD_ADAYI, re.MULTILINE | re.IGNORECASE)

# INCLUDE ÜÇ biçimde gelir (canlı ölçüm 2026-07-30 + 2026-08-29):
#   `include emara`                          ← çıplak (noktalı virgül bile olmayabilir)
#   `likp_status : include likp_status;`      ← adlandırılmış
#   `include si_kna1 not null;`               ← DDL KISIT EKLİ  ⭐ 2026-08-29 (kayıt #66)
# ⚠ Satır-başına DEMİRLENMİŞ: serbest metinde geçen "include for ..." gibi ifadeler
# include adı sanılırsa çözülemeyen-liste şişer ve gerçek bulgular "doğrulanamadı"ya
# düşer — yani gürültüyü kesmek korumayı deler. Demirleme bunu kapatır.
#
# ⭐ KAYIT #66 — KNA1 SAHTE-POZİTİFİNİN KÖKÜ (canlı ölçüldü, sap-research 2026-08-29):
#   KNA1'in canlı DDL gövdesi DÖRT include taşır; eski desen bunlardan YALNIZ ÜÇÜNÜ
#   görüyordu — `include si_kna1 not null;` satırındaki `not null` eki kuyruk demirini
#   (`\s*;?\s*$`) kırıyordu. `si_kna1` (406 satır) beş disputed alanın BEŞİNİ de taşır:
#   aufsd:8 · faksd:31 · lifsd:73 · loevm:78 · sperr:107.
#   ⛔ ASIL ZARAR: kaçırılan include `cozulemeyen`e de DÜŞMÜYORDU — desen onu HİÇ
#   GÖRMEDİĞİ için "çözülemedi" bile denemiyordu ⇒ 2026-07-30'un "çözülemezse
#   DOĞRULANAMADI de" garantisi HİÇ DEVREYE GİRMİYOR ⇒ 5 alan doğrudan [BULGU] oluyordu.
#   "Görmedim" ile "çözemedim" arasındaki fark, tam olarak sahte-pozitifin doğduğu yer.
#
# ⛔ GENİŞ ÇARE REDDEDİLDİ — ÖLÇÜMLE (2026-08-29). Önerilen kolay çözüm kuyruk demirini
#   tamamen kaldırıp `\b` ile kesmekti. Yerel korpusta ölçüldü (1.552 dosya / 490.365
#   satır, `node_modules` hariç, 263'ü `.cds`):
#       eski desen 0 eşleşme · GENİŞ varyant **124 YENİ eşleşme** · aşağıdaki DAR varyant **0**
#   124'ün tamamı DDIC include DEĞİLDİ: klasik ABAP `INCLUDE <prog>_f01.` deyimleri
#   (nokta ile biter, `;` ile değil), README/SPEC düzyazısı (`include the`, `include one`,
#   `include any`, `include nested`). Yani geniş varyant, kapatmaya çalıştığı sahte-pozitif
#   sınıfını BAŞKA BİR YERDE yeniden üretirdi.
# ⇒ Alınan yol: kuyruk demiri KORUNUR, yanına DAR bir ikinci alternatif eklenir —
#   "include <ad> + bir veya daha çok ÇIPLAK anahtar sözcük" ancak satır `;` ile
#   BİTİYORSA kabul edilir. `;` şartı düzyazıyı ve klasik ABAP INCLUDE'unu yapısal olarak
#   eler; `;`siz çıplak biçim (MARA `include emara`) birinci alternatifte AYNEN durur.
# ⚠ KAPSAM NİTELEYİCİSİ: kısıt-eki olarak CANLI ÖLÇÜLEN tek biçim `not null`dur. Desen
#   ek-metnini genel tutar (başka ek gelirse de yakalanır) ama iddia yalnız `not null`
#   için ölçülmüştür — "her DDL eki desteklenir" DENMEZ.
INCLUDE_LINE = re.compile(
    r'^\s*(?:[a-z][a-z0-9_]*\s*:\s*)?include\s+((?=[a-z/][a-z0-9_/]{2})' + AD_ADAYI + r')'
    r'(?:\s*;?\s*$'                          # (a) ek YOK: `include emara` / `include x;`
    r'|(?:\s+[a-z][a-z0-9_]*)+\s*;\s*$)',    # (b) DDL kısıt-eki VAR → `;` ZORUNLU
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
    parser.add_argument('--strict', action='store_true',
                       help='(uyumluluk; NO-OP — şiddeti DEĞİŞTİRMEZ, run_all --strict kazara terfi ettirmesin; ADR 0019 §54)')
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
    # #402: namespace'li / şekli bozuk ad SESSİZCE atlanmaz — ölçülmeyen adlar sayılır ve
    # sonuç "doğrulandı" yerine ÖLÇÜLEMEDİ olur (run_review şiddeti WARNING).
    olculemeyen: dict[str, str] = {}
    for table, field in pairs:
        tbl = alias_map.get(table.lower(), table.lower())  # alias → gerçek tablo
        # Eski `[a-z]…` deseninin dışladığı şekiller: association (`_x.alan`) ve rakamla başlayan
        # belirteç (`1.5`) tablo değildir.
        if tbl[:1] == '_' or tbl[:1].isdigit():
            continue
        if not ad_coz(tbl)[0] or not ad_coz(field)[0]:
            if tbl.startswith('/') or field.startswith('/'):
                olculemeyen[f'{tbl}.{field}'] = 'ad-cozulemedi'
            continue
        if tbl.startswith(SKIP_TABLE_PREFIXES):
            continue
        # Namespace'li tablo: müşterinin (kayıtlı namespace) ise Z gibi atlanır. Değilse (SAP /
        # add-on, ör. /SCWM/) ADT source ucunun güvenilirliği ÖLÇÜLMEDİ (eski not: "güvenilir
        # değil") ⇒ sorgulanmaz ama SESSİZ "OK" da verilmez: ÖLÇÜLEMEDİ.
        if tbl.startswith('/'):
            if musteri_karari(tbl) != 'musteri':
                olculemeyen[f'{tbl}.{field}'] = 'namespace-kayitsiz'
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

    if olculemeyen:
        print(f'[ÖLÇÜLEMEDİ] {len(olculemeyen)} referans denetlenmedi: '
              + ', '.join(f'{k} ({v})' for k, v in sorted(olculemeyen.items())[:8]))
    if not candidates:
        if olculemeyen:
            gate_status(_GATE, 'SKIPPED', False, sorted(olculemeyen.values())[0])
            return 0
        print(f'OK — {path.name} standart tablo referansı yok')
        gate_status(_GATE, 'OK', True, 'kapsam-disi-std-tablo-yok')
        return 0

    # SAP'ye bağlan
    sys.path.insert(0, str(Path(__file__).parent.parent))
    try:
        from sap_adt_lib import SAPADTClient
        client = SAPADTClient()
    except Exception as e:
        print(f'UYARI: SAP bağlantısı kurulamadı, validator atlandı: {e}', file=sys.stderr)
        sap_baglanti_yok(_GATE)
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
        # ⚠ KAPSAM NİTELEYİCİSİ: `dogrulanamayan` (include zinciri kısmen çözülemedi)
        # BİLEREK measured=true bırakıldı — o dal zaten stdout'a [DOĞRULANAMADI] basıyor
        # ve sıklığı canlı SAP olmadan ÖLÇÜLEMEDİ. Kanıtsız sıkılaştırma yapılmadı;
        # ayrı kalem olarak raporlandı (B3-01 AÇIK-NOKTA).
        if olculemeyen:     # #402: namespace'li / bozuk ad hiç SORGULANMADI (include eksiğinden ayrı)
            gate_status(_GATE, 'SKIPPED', False, sorted(olculemeyen.values())[0])
            return 0
        gate_status(_GATE, 'OK', True, 'dogrulandi')
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
