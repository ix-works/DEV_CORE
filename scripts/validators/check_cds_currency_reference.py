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


# ---------------------------------------------------------------------------
# EKSİK-annotation tespiti (DERİNLİK, 2026-08-20)
# ---------------------------------------------------------------------------
# ⛔ ESKİ KUSUR: `check_cds` yalnız VAR OLAN annotation'ın BİÇİMİNİ denetliyordu;
# EKSİKLİĞİNİ hiç aramıyordu. Sonuç: bilerek kirletilmiş bir dosya (CURR alan +
# `@Semantics` YOK + CUKY YOK) `rc=0 "temiz"` dönüyordu ⇒ *"13/13 rc=0"* gibi bir
# sonuç BİLGİ TAŞIMIYORDU (annotation hiç yoksa da yeşil). Kapsam kusuru `ea1abf1`
# ile kapandı, DERİNLİK kusuru açıktı.
#
# ⚠ TASARIM ÖLÇÜMLE SEÇİLDİ (tahmin değil). İlk aday "DTEL sözlüğünden çöz" idi;
# gerçek korpus onu çürüttü: proje CDS'leri `klm_kalem_tutari_vh` gibi ÖZEL kolon
# adları kullanıyor, sözlükteki standart adları değil ⇒ tek başına sözlük neredeyse
# hiç ateşlemezdi (ölü gate). Ölçüm (233 CDS): açık `abap.curr(`/`abap.quan(` cast'i
# **117 geçiş / 20 dosya**, sözlük-adlı kolon **81 geçiş / 23 dosya** ⇒ İKİ sinyal de
# gerçek, ikisi birlikte kullanılır.
_CAST_CURR = re.compile(r"abap\.curr\s*\(", re.I)
_CAST_QUAN = re.compile(r"abap\.quan\s*\(", re.I)
# `x as Y` · `tbl.x as Y` · `cast( … ) as Y` — son `as <alias>` ayrımı
_ELEMAN = re.compile(r"^\s*(?:key\s+)?(?P<ifade>.+?)\s+as\s+(?P<alias>\w+)\s*,?\s*$", re.I)
# Yalnız SADE alan referansı (ifade DEĞİL): sözlük eşlemesi yalnız burada güvenli
_SADE_ALAN = re.compile(r"^(?:(\w+)\.)?(\w+)$")
# Eleman OLMAYAN ama `as` içerebilen yapısal satırlar — bunlar bekleyen annotation
# bloğunu SIFIRLAMAZ (ör. `as select from`, association tanımları)
_YAPISAL = ("{", "}", "define", "as select", "association", "left outer",
            "inner join", "right outer", "cross join", "*", "//")

# ── ÇOK-SATIRLI ifade + `union` dalı (2026-09-04, kuyruk Q234 + Q237) ─────────
# ⛔ ÖLÇÜLMÜŞ KUSUR (tüketici projede canlı korpus, 316 CDS/DDL):
#   Q234 — Tarama FİZİKSEL satır üzerindeydi. `@Semantics…` satırından sonra gelen
#     çok-satırlı `cast( … )` ifadesinin ARA satırları ne `_ELEMAN`'a uyuyor ne de
#     `_YAPISAL` ile başlıyordu ⇒ `bekleyen = []` bloğu SİLİYOR, ifadenin SON
#     satırındaki `as <Alias>` annotation'sız sanılıyordu. Aynı dosya içinde kontrol
#     grubu: TEK satırlık kardeş eleman aynı annotation'la uyarı ÜRETMİYOR — tek fark
#     satır sayısı. Sınıf envanteri: **20 çok-satırlı annotation'lı eleman / 11 dosya**
#     (16'sı CURR/QUAN cast'i taşıyor / 9 dosya) — yani ZSD001 tekil bir vaka DEĞİL.
#   Q237 — `union [all]` tanınmıyordu. CDS'te element-level `@Semantics.*` **YALNIZ
#     1. SELECT dalında** yazılabilir (playbook `adt-cds.md` T4-b: 2. dalda
#     `Annotations are not allowed in this branch`); sonuç-elemanın annotation'ı
#     1. daldan MİRAS alınır. Kapı 2.+ dalın elemanını ayrı eleman sanıp
#     "annotation YOK" diyordu ⇒ uyarıyı susturmanın tek yolu **aktivasyonu kıran**
#     bir düzeltmeydi. Envanter: `^union` satırı taşıyan **12 dosya / 20 dal**,
#     hepsi tek biçimde (`union all` satır başında, tek başına).
#
# ⚠ BU BİR DARALTMADIR (F4). İki koruma bilerek YERİNDE bırakıldı:
#   ① 1. dalda da annotation yoksa uyarı YİNE çıkar — 1. dalın kendi satırında.
#   ② 2.+ dalın alias'ı 1. dalda HİÇ görülmediyse (miras kanıtlanamıyor) uyarı çıkar
#      ve mesaj bunu AÇIKÇA söyler; sessiz yutma YOK.
_UNION_BASI = re.compile(r'^\s*union\b(?:\s+(?:all|distinct))?', re.I)
# Kapanmayan ayraç tüm dosyayı yutmasın: bozuk kaynakta birleştirme bu sınırda
# BIRAKILIR ve satırlar tek tek işlenir — yani degrade yönü "sessizlik" değil
# "eski davranış (uyarı üret)"tir.
_MAX_BIRLESIM_SATIR = 80
# Select-listesi elemanı burada BİTER (parantez derinliği 0 iken).
_BITIS_KARAKTERLERI = (',', '{', '}', ';')
# Bu sözcüklerle BAŞLAYAN satır YENİ bir birim açar ⇒ birikmiş tampon ÖNCE boşaltılır.
# ⚠ ZORUNLU: select listesinin SON elemanında virgül YOKTUR (`… as SnapTarih` ↵ `}`);
# boşaltılmazsa o eleman `}` ile birleşir, `_ELEMAN` deseni kırılır ve eleman
# SESSİZCE kaybolur (fix'in kendi üreteceği en tehlikeli gerileme buydu).
_AYRAC_BASI = re.compile(r'^(?:union\b|\})', re.I)


def _denge(s: str, acilar: str, kapatanlar: str) -> int:
    """TIRNAK DIŞINDAKİ ayraç dengesi.

    Tırnak içi ayraç sayılırsa (`@EndUserText.label: 'Miktar (adet)'`) ifade sınırı
    yanlış hesaplanır ve sonraki satırlar ifadeye YUTULUR — `yorumu_kirp` ile aynı
    sınıfın ayraç yüzü.
    """
    d, q = 0, None
    for c in s:
        if q is not None:
            if c == q:
                q = None
        elif c in "'\"":
            q = c
        elif c in acilar:
            d += 1
        elif c in kapatanlar:
            d -= 1
    return d


def _mantiksal_satirlar(text: str):
    """(ilk_satir_no, birleştirilmiş_metin) üretir — ifade sınırına kadar birleştirir.

    ⚠ SINIR ÖLÇÜLEREK SEÇİLDİ, tahminle değil. İlk tasarım *"parantez dengesi
    kapanınca biter"* idi; canlı korpus onu ÇÜRÜTTÜ: kusurun İKİNCİ yazım biçimi
    `case when … then currency_conversion( … ) else cast( 0 as abap.curr(15,2) ) end
    as <Alias>,` şeklindedir ve **ilk satırı parantez bakımından DENGELİDİR**
    (`case when x <> '' and x is not null`) ⇒ paren-tabanlı sınır onu hiç
    birleştirmez, uyarı ayakta kalırdı. Ölçüm: paren-biçimi 20 vaka / 11 dosya,
    `case`-biçimi 18 vaka daha / 3 dosya. Doğru sınır CDS grameridir:
    **eleman, derinlik 0'daki ayraçta (`,` `{` `}` `;`) biter.**

    `@…` birimleri ayrıca ele alınır: annotation gövdesi `[ { (` dengesi kapanana
    kadar birleşir (çok satırlı `@UI.lineItem: [ { … } ]` bir SONRAKİ elemanı
    yutmasın diye).

    Raporlanan satır no ifadenin **İLK** satırıdır (eskiden alias'ın bulunduğu SON
    satırdı): düzeltme talimatı *"elemanın HEMEN ÜSTÜNE ekle"* der, dolayısıyla
    okuyucunun görmesi gereken yer ifadenin başıdır.
    """
    buf: list[str] = []
    ilk = 0
    derinlik = 0
    anot = False
    for i, raw_line in enumerate(text.splitlines(), 1):
        s = yorumu_kirp(raw_line).strip()
        if not s:
            continue
        if buf and not anot and _AYRAC_BASI.match(s):
            yield ilk, ' '.join(buf)
            buf, derinlik = [], 0
        if not buf:
            ilk, anot = i, s.startswith('@')
        buf.append(s)
        derinlik += (_denge(s, '([{', ')]}') if anot else _denge(s, '(', ')'))
        tam = derinlik <= 0 and (anot or s.endswith(_BITIS_KARAKTERLERI))
        if not tam and len(buf) < _MAX_BIRLESIM_SATIR:
            continue
        yield ilk, ' '.join(buf)
        buf, derinlik, anot = [], 0, False
    if buf:
        yield ilk, ' '.join(buf)


def _eleman_tipi(ifade: str) -> str | None:
    """Bir select-eleman ifadesi CURR/QUAN tipli mi? Çözülemezse None.

    İki kanıt kabul edilir:
      ① AÇIK cast — `cast( … as abap.curr(15,2) )`. İfade içinde geçmesi yeter;
         `case … else cast( 0 as abap.curr(…) ) end` de tutar.
      ② SADE alan referansı (`vbrk.netwr`, `netwr`) ve kolon adı PAYLAŞILAN
         sözlükte. ⛔ İfadelerde sözlüğe BAKILMAZ: `coalesce( x.menge, … )` içinde
         geçen bir ad, elemanın tipini kanıtlamaz (yol ifadesi tahmini = FP kaynağı).
    """
    if _CAST_CURR.search(ifade):
        return 'CURR'
    if _CAST_QUAN.search(ifade):
        return 'QUAN'
    m = _SADE_ALAN.match(ifade.strip())
    if m:
        kolon = m.group(2).lower()
        if kolon in CURR_DTELS:
            return 'CURR'
        if kolon in QUAN_DTELS:
            return 'QUAN'
    return None


def curr_quan_eleman_sayisi(text: str) -> int:
    """Tipi KANITLANABİLEN CURR/QUAN eleman sayısı — "temiz"in PAYDASI.

    ⛔ Bu sayı çıktıya basılır çünkü kusurun kökü tam da paydasızlıktı: *"13/13 rc=0"*
    okunduğunda kimse *"kaç alana bakıldı?"* diye sormuyordu ve cevap **sıfır** olabilirdi.
    `0 eleman denetlendi` ile `7 eleman denetlendi, hepsi temiz` AYNI ŞEY DEĞİLDİR.
    ⚠ Sayı, aracın ÇÖZEBİLDİKLERİDİR: sözlükte olmayan bir DTEL adı (ör. `fkimg`) sade
    referansla geçiyorsa buraya girmez — araç onu tipleyemediğini böylece BEYAN eder,
    "temiz" diye yutmaz. Kapsamı genişletmenin yolu `utils/ddic_semantics` sözlüğüdür
    (genişletilebilir, KISALTILAMAZ) ya da açık `cast( … as abap.curr/quan(…) )`.
    """
    n = 0
    for _i, s in _mantiksal_satirlar(text):
        if s.startswith('@'):
            continue
        m_union = _UNION_BASI.match(s)
        if m_union:
            s = s[m_union.end():].strip()
            if not s:
                continue
        m = _ELEMAN.match(s)
        if m and _eleman_tipi(m.group('ifade')):
            n += 1
    return n


def eksik_annotation_bul(text: str) -> list[dict]:
    """CURR/QUAN tipli olduğu KANITLANAN ama `@Semantics`'i olmayan elemanlar.

    ⚠ ŞİDDET = WARNING, BLOCKER DEĞİL — ve bu ÖLÇÜLEREK seçildi:
    gerçek korpusta (233 CDS) **129 CURR/QUAN eleman** tespit ediliyor ve bunların
    **46'sı / 15 dosyada** annotation taşımıyor. Bu dosyalar CANLIDA AKTİF —
    yani SAP aktivasyonu bu annotation'ı zorlamıyor. BLOCKER yapmak, çalışan 15
    dosyayı anında kırmızıya çevirir ve kapı "geçilemez" olduğu için ilk refleks
    onu KAPATMAK olurdu (erişilemez yeşil = ölü gate). Önce görünürlük, sonra
    (birikmiş 46 kalem temizlenince) şiddet kararı — o karar kullanıcınındır.

    ⭐ KAPSAM BEYANI (2026-09-04, Q234+Q237 — ev kuralı: kapı kendi kapsamını İLAN eder):
      • Eleman ifadesi ÇOK SATIRA yayılabilir; eşleme fiziksel satır değil
        **parantez dengesiyle kapanan mantıksal satır** üzerinden yapılır.
      • `union [all|distinct]` görüldüğünde dal sayacı artar. **2.+ dallarda eleman
        annotation'ı ARANMAZ** — CDS orada annotation yazılmasını YASAKLAR ve değer
        1. daldan miras alınır. Karar 1. dalda verilir: orada annotation yoksa uyarı
        1. dalın satırında çıkar.
      • ⛔ SESSİZ YUTMA YOK: 2.+ daldaki bir alias 1. dalda HİÇ görülmediyse (miras
        kanıtlanamıyor) uyarı yine basılır ve mesaj bunu açıkça yazar.
      • ⚠ ÖLÇÜLMEYEN: `union`'ın iki dalının alan SIRASI/TİPİ uyumu bu kapının konusu
        DEĞİLDİR (SAP aktivasyonu zorlar).
    """
    violations = []
    bekleyen: list[str] = []
    dal = 0                          # 0 = 1. SELECT dalı (annotation'ın YAŞADIĞI yer)
    dal0_annotasyonlu: set[str] = set()   # 1. dalda annotation'ı OLAN alias'lar
    dal0_bulgulu: set[str] = set()        # 1. dalda ZATEN raporlanmış alias'lar
    for i, s in _mantiksal_satirlar(text):
        if s.startswith('@'):
            bekleyen.append(s)
            continue
        m_union = _UNION_BASI.match(s)
        if m_union:
            dal += 1
            bekleyen = []
            s = s[m_union.end():].strip()
            if not s:
                continue
        m = _ELEMAN.match(s)
        if not m:
            if not s.startswith(_YAPISAL):
                bekleyen = []
            continue
        alias, ifade = m.group('alias'), m.group('ifade')
        tip = _eleman_tipi(ifade)
        if tip:
            blok = ' '.join(bekleyen)
            gerekli = ('@Semantics.amount.currencyCode' if tip == 'CURR'
                       else '@Semantics.quantity.unitOfMeasure')
            eksik, ek = gerekli not in blok, ''
            if dal == 0:
                (dal0_bulgulu if eksik else dal0_annotasyonlu).add(alias.lower())
            elif eksik:
                # MİRAS KURALI (adt-cds.md T4-b): 2.+ dalda annotation YAZILAMAZ.
                # 1. dalda alias biliniyorsa karar orada verilmiştir (ya annotation
                # var ya da uyarı orada BASILDI) → burada mükerrer/yanlış uyarı YOK.
                eksik = alias.lower() not in (dal0_annotasyonlu | dal0_bulgulu)
                # ⚠ Niteleyici ASCII bir jetonla başlar (`[union-miras-yok]`): korpus
                # çapaları Türkçe harfe (ı/İ) bağlanırsa sahte-KIRMIZI üretir.
                ek = (f" [union-miras-yok] {dal + 1}. dalda tanımlı '{alias}' alias'ı "
                      f"1. dalda BULUNAMADI — annotation mirası kanıtlanamadı")
            if eksik:
                violations.append({
                    'severity': 'WARNING',
                    'line': i,
                    'check_id': 'C-CDS-CUR-05' if tip == 'CURR' else 'C-CDS-QUAN-05',
                    'message': (f"{tip} tipli '{alias}' elemanında "
                                f"{gerekli} annotation'ı YOK "
                                f"(kanıt: {ifade.strip()[:60]}){ek}"),
                    'fix': (f"Elemanın HEMEN ÜSTÜNE `{gerekli}: '<BirimElemani>'` ekle; "
                            f"birim/para-birimi elemanı da view'da EXPOSED olmalı."),
                })
        bekleyen = []
    return violations


def check_cds(text: str) -> list[dict]:
    """CDS source'unda CURR/QUAN reference check.

    İKİ SORU birden sorulur:
      ① VAR OLAN annotation'ın biçimi geçerli mi (C-CDS-CUR-02/03)
      ② ⭐ CURR/QUAN tipli bir eleman annotation'ı EKSİK Mİ (C-CDS-CUR/QUAN-05)
    ②'siz hâlde *"rc=0 temiz"* hiçbir bilgi taşımıyordu — bkz. `eksik_annotation_bul`.
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

    # ② DERİNLİK: annotation'ın EKSİKLİĞİ (biçimi değil) — 2026-08-20
    violations.extend(eksik_annotation_bul(text))
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
        # ⛔ PAYDASIZ "temiz" BASMA: kaç elemana bakıldığı yazılmazsa `0 eleman` ile
        # `7 eleman, hepsi doğru` aynı satıra düşer — kusurun kökü buydu.
        if src_type == 'cds':
            n = curr_quan_eleman_sayisi(text)
            kapsam = (f'{n} CURR/QUAN elemanı denetlendi' if n else
                      'tipi ÇÖZÜLEBİLEN CURR/QUAN elemanı YOK — bu "temiz" bir '
                      'KAPSAMA iddiası DEĞİLDİR')
            print(f'OK — {path.name} ({src_type}) CURR/QUAN reference check temiz · {kapsam}')
        else:
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
