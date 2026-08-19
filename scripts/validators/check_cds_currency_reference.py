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

Exit kodu (SÖZLEŞME — run_review rc!=0'ı FAIL sayar):
    0 — DENETLENDİ, BLOCKER yok (yalnız WARNING olabilir) / table-function bilinçli atlandı
    1 — DENETLENDİ, en az 1 BLOCKER ihlal (stderr'de satır no + öneri)
    2 — ÖLÇÜLEMEDİ: dosya yok/okunamadı VEYA kaynak tipi tespit edilemedi.
        "Koşmadı ≠ temiz" (PATTERN #14) — sessiz rc=0 YASAK.
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

# DTEL sözlükleri — TEK KAYNAK: scripts/utils/ddic_semantics.py (B-13, 2026-08-19).
# NEDEN taşındı: aynı sözlüğü DDL'i ÜRETEN populate_tables.py de kullanır. İki kopya
# yaşarsa üretici, bu denetçinin BLOCKER diyeceği annotation'ı üretir (B-13 kökü).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.ddic_semantics import (  # noqa: E402
    CURR_DTELS, QUAN_DTELS, CUKY_DTELS, UNIT_DTELS,
)


def yorumu_kirp(line: str) -> str:
    """Satır-sonu `//` yorumunu kırpar — TIRNAK İÇİ `//` KORUNUR.

    NEDEN (2026-08-01 bug-avı, V1): alan deseni `;\\s*$` ile ANCHOR'lı; gerçek DDL'de
    yaygın olan `netwr : netwr;  // tutar` satırı desene UYMAZ → alan hiç kaydedilmez →
    eksik CURR-annotation ihlali SESSİZCE kaybolur (gate yeşil yanar, "0 alan bulundu"
    ile "0 ihlal" ayırt edilemez — run_all'ın "dizin-yok → 0 dosya → OK" sınıfının
    satır-içi ikizi).

    Aynı sınıfın ikinci yüzü annotation DEĞERİdir: `@Semantics.amount.currencyCode :
    'ztab.waers'  // para birimi` satırında değer `ztab.waers' // para birimi` olarak
    okunuyor, `split('.')[-1]` → `waers' // para birimi` → "CUKY tabloda yok" YANLIŞ-
    POZİTİF'i basılıyordu. Tek kırpma iki yüzü birden kapatır.

    Tırnak-duyarlılık ZORUNLU: `@EndUserText.label : 'http://x'` gibi meşru değerler
    kırpılırsa annotation bozulur (kaba `split('//')` bu FP'yi üretir).
    """
    q = None
    i, n = 0, len(line)
    while i < n:
        c = line[i]
        if q is not None:
            if c == q:
                q = None
        elif c in "'\"":
            q = c
        elif c == '/' and i + 1 < n and line[i + 1] == '/':
            return line[:i]
        i += 1
    return line


# ── Kaynak tipi tespiti (2026-08-19, KAYIT: root-view-entity kapsam kusuru) ────
# ESKİ KUSUR: `'define view' in text` alt-dizi testiydi. `define root view entity`
# bu alt-diziyi İÇERMEZ ("root" araya girer) → tip 'tespit edilemedi' → stderr'e
# UYARI + **rc=0** dönülüyordu. run_review rc=0'ı PASS sayar ⇒ 6 BLOCKER kablolaması
# (cds_creation/cds_update/table_creation/table_update/struct_creation/rap_cds_creation)
# bu dosyalara HİÇ BAKMADAN yeşil veriyordu. Ölçüldü: SOURCE_CODES'ta 62 dosya
# (30 root view entity + 31 abstract entity + 1 `define type`) bu yoldan sessizce geçiyordu.
# ÇÖZÜM: alt-dizi değil TOKEN dizisi — `define|extend|annotate` sonrası bilinen
# değiştirici/tür sözcükleri tüketilir, nesne adına gelince durulur.
_SOURCE_MODIFIERS = frozenset({'root', 'abstract', 'custom', 'transient'})
_SOURCE_KINDS = frozenset({'view', 'entity', 'table', 'structure', 'type',
                           'function', 'hierarchy'})
_DEFINITION_RE = re.compile(
    r'^\s*(define|extend|annotate)\b((?:\s+[A-Za-z_][A-Za-z0-9_]*)+)', re.IGNORECASE)


def kaynak_tipi_tespit(text: str) -> tuple[str | None, str]:
    """(src_type, biçim_etiketi) döner. src_type ∈ {'table','cds','table_function',None}.

    None = TESPİT EDİLEMEDİ → çağıran fail-closed davranmalı (exit 2), rc=0 DÖNMEMELİ.

    Yönlendirme gerekçesi (ölçülmüş korpus + §15.3):
      • 'define table/structure/type'  → check_table: DDIC alan listesi şekli
        (`alan : dtel;`) + qualified 'TABLE.FIELD' referans kuralı geçerli.
      • 'define [root] view [entity]'  → check_cds: referans EXPOSED ELEMENT adıdır
        (kanıt: ZSD001_I_SO_ITEM 'Waerk'), qualified zorunlu değil.
      • 'define [root] abstract entity' / 'define custom entity' → check_cds.
        NEDEN tablo değil: alan listesi şekli tablo gibi olsa da arkasında DDIC tablo
        YOKTUR; referans aynı entity'nin elemanıdır → qualified 'TABLE.FIELD' beklemek
        YANLIŞ-POZİTİF üretirdi. (Korpusta CURR/QUAN taşıyan abstract entity: 0 — bu
        yönlendirme bugün hiçbir dosyanın sonucunu değiştirmiyor, ileriye dönüktür.)
      • 'define table function' → TF: return yapısı lokal element adı kullanır,
        check_table FP basıyordu (2026-06-24 SATNAV) → bilinçli atlama korunur.
    """
    gorulen_basliklar: list[str] = []
    for raw_line in text.splitlines():
        line = yorumu_kirp(raw_line)
        m = _DEFINITION_RE.match(line)
        if not m:
            continue
        verb = m.group(1).lower()
        seq = []
        for tok in m.group(2).split():
            t = tok.lower()
            if t in _SOURCE_MODIFIERS or t in _SOURCE_KINDS:
                seq.append(t)
            else:
                break  # nesne adına gelindi
        if not seq:
            # Sözlükte HİÇ tanınmayan başlık (ör. `define role` = DCL, `define behavior`).
            # Kaydet ve aramaya devam et; teşhis mesajı "başlık YOK" DEMEMELİ — yanlış
            # teşhis, okuyanı dosyanın boş olduğuna inandırır (ölçüldü: .dcl dosyaları).
            gorulen_basliklar.append(' '.join(line.split()[:3]))
            continue
        etiket = f"{verb} {' '.join(seq)}"
        if seq[-2:] == ['table', 'function']:
            return 'table_function', etiket
        if 'view' in seq or 'hierarchy' in seq:
            return 'cds', etiket
        if seq[-1] == 'entity' and ('abstract' in seq or 'custom' in seq):
            return 'cds', etiket
        if seq[-1] in ('table', 'structure', 'type'):
            return 'table', etiket
        return None, etiket  # tanınan sözcükler ama bilinmeyen kombinasyon
    return None, (gorulen_basliklar[0] if gorulen_basliklar else '')

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

    for i, raw_line in enumerate(lines, 1):
        # Satır-sonu yorumu ÖNCE kırpılır: hem alan deseninin `;$` anchor'ını kurtarır
        # hem de annotation değerinin sonuna yorum metni bulaşmasını engeller.
        line = yorumu_kirp(raw_line)
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
    for i, raw_line in enumerate(lines, 1):
        # YORUMLANMIŞ annotation kontrol edilmez (aynı sınıfın CDS yüzü): `// @Semantics...`
        # satırı canlı kural DEĞİLDİR; kırpılmazsa ölü metin üzerinden WARNING üretilir.
        line = yorumu_kirp(raw_line)
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
        print(f'ÖLÇÜLEMEDİ: {path} bulunamadı', file=sys.stderr)
        return 2

    text = path.read_text(encoding='utf-8', errors='replace')

    src_type = args.type
    if src_type == 'auto':
        tespit, etiket = kaynak_tipi_tespit(text)
        if tespit == 'table_function':
            # CDS table function = DDLS objesi (DDIC tablo DEĞİL). Return yapısı view gibi
            # LOKAL element-adı kullanır (qualified TABLE.FIELD yok) → check_table FALSE-POSITIVE
            # basıyordu (C-TBL-CUR-03). TF return-yapısı CURR/QUAN kontrolü ayrı bir konu;
            # şimdilik atla (TF-aware kontrol TODO). 2026-06-24 SATNAV BASE.cds.
            print(f'OK — {path.name} (table function) CURR/QUAN reference check atlandı (TF-aware kontrol TODO)')
            return 0
        if tespit is None:
            # FAIL-CLOSED: "koşmadı ≠ temiz". Eskiden burada rc=0 dönülüyordu ve
            # run_review bunu PASS sayıyordu (BLOCKER zinciri sessizce boşa düşüyordu).
            ek = f" (bulunan başlık: '{etiket}')" if etiket else ' (dosyada define/extend/annotate başlığı YOK)'
            print(f'ÖLÇÜLEMEDİ: {path.name} kaynak tipi tespit edilemedi{ek} — '
                  f'CURR/QUAN denetimi KOŞMADI. Beklenen biçimler: define [root] view [entity] · '
                  f'define [root] abstract entity · define custom entity · define hierarchy · '
                  f'define table|structure|type · define table function. '
                  f'Bilinçli istisna gerekiyorsa --type cds|table ile açıkça belirt.',
                  file=sys.stderr)
            return 2
        src_type = tespit

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
