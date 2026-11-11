"""
check_table_field_drop.py — Z tablo ALTER'da mevcut alanın DROP / RENAME / TİP
değişikliğini SAP'ye yazmadan önce yakalar (DDIC veri kaybı koruması).

Sorun (2026-06-10, reviewer-kör vakası): run_review.py 'table_update' zinciri
sadece CURR/QUAN + deprecated-annotation çalıştırıyordu. Bir ALTER source'u ~15
alanı DROP edip var olmayan DTEL'e referans verdiği halde reviewer PASS verdi.
Checklist'te C-TBL-DROP-01 / C-TBL-RENAME-01 / C-TBL-TYPE-01 "BLOCKER" yazıyordu
ama arkalarında çalıştırılabilir bir script YOKTU. Bu validator o boşluğu kapatır.

Yöntem: yeni source'tan tablo adını + (alan → TAM tip metni) haritasını çıkar; SAP'den
CANLI source'u GET ile çek, onun haritasıyla karşılaştır.
  - Mevcut alan yeni source'ta YOK            → DROP        → BLOCKER
  - Mevcut alanın tip metni değişmiş → iki taraf FİZİKSEL tipe çözülür
    (yerleşik `abap.char(10)` doğrudan; DTEL ADT veri öğesi meta verisinden:
    `dataType` · `dataTypeLength` · `dataTypeDecimals`) ve kıyaslanır:
      · tür değişti (CHAR→NUMC, INT2→INT4 dahil) ya da daralma → BLOCKER
      · genişleme (uzunluk / tam sayı hanesi / ondalık büyüdü)  → WARNING (rc 0, stderr)
      · aynı fiziksel tip ("DTEL değişti, tip aynı")            → INFO (rc 0) ⚠GEVŞETME
      · fiziksel tip çözülemedi (DTEL 404/okunamadı/tip yok)    → BLOCKER + "ÖLÇÜLEMEDİ"
  - Yeni alan eklenmiş (additive)             → OK (ALTER'ın amacı)
  - Tablo SAP'de yok (yeni yaratım) / bağlantı yok → OK (skip, kapsam dışı)

#408 / Q399 (2026-11-11, kullanıcı onayı 2026-11-08): eski tip deseni tip konumunu ilk ad
parçasında kesiyordu ⇒ HER yerleşik tip `abap` diye kaydediliyordu ⇒ `abap.int4`→`abap.int2`,
`abap.char(100)`→`abap.char(10)` daralması GÖRÜNMÜYORDU (sessiz veri kaybı). Ters yönde ad metni
kıyası, fiziksel tipi aynı kalan DTEL→DTEL / yerleşik→DTEL geçişini BLOCKER yapıyordu.
⚠GEVŞETME (bilinçli, removed-controls kaydı): ① aynı fiziksel tip artık BLOCKER değil INFO
② yalnız çözülemeyen DTEL BLOCKER'ı varsa `measured=false` basılır ⇒ checklist_check BE-16 o
dar vakada FAIL yerine ÖLÇÜLEMEDİ der (run_review rc≠0'da beyanı okumaz ⇒ BLOCKER kalır).
Ölçülmüş drop/daralma/tür değişikliği yanındaysa `measured=false` BASILMAZ.

KAPSAM BEYANI (her koşumda basılır): bakılan = canlı DDL kaynağı + değişen alanların DTEL meta
verisi (SAP'deki GÜNCEL tanım; DTEL'in kendisi değiştiyse tarihçesi bilinmez). Bakılmayan:
include / append yapılarının alanları · klasik `*.tabl.xml` · canlı DD03L.

Kullanım:
    python scripts/validators/check_table_field_drop.py <tablo_ddl_path>
    # Bilinçli (kullanıcı+lider onaylı) DROP — yalnız ADI VERİLEN alanlar geçer:
    python scripts/validators/check_table_field_drop.py <path> --ack-drop order_amount,order_currency

--ack-drop NOTU (ADR 0005-B): Sadece açıkça onaylanmış, ADI YAZILAN alanların DROP'u
BLOCKER yerine ACK-WARNING olur. İsmi verilmeyen herhangi bir DROP veya herhangi bir
TYPE/RENAME değişikliği YİNE BLOCKER kalır (kör/blanket bypass DEĞİL — hedefli ack).

Exit kodu: 0 temiz/skip/ack/genişleme/aynı-tip · 1 BLOCKER (onaysız DROP · daralma · tür
değişikliği · çözülemeyen fiziksel tip)
"""
# ENFORCES: C-TBL-DROP-01, C-TBL-RENAME-01, C-TBL-TYPE-01, BE-15, BE-16  (ADR 0019 coverage binding)
import argparse
import re
import sys
import urllib3
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _gate_status import gate_status, sap_baglanti_yok  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.ad_politikasi import AD_ADAYI, ad_coz  # noqa: E402 — TEK ad grameri (#402 K1)

_GATE = Path(__file__).stem
_KAPSAM_BEYANI = ("KAPSAM: bakılan = canlı DDL kaynağı + tip metni değişen alanların fiziksel tipi "
                  "(DTEL: SAP'deki güncel veri öğesi meta verisi) · BAKILMAYAN: include/append "
                  "yapılarının alanları · klasik *.tabl.xml · canlı DD03L")

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 'key fieldname : dtel ...;' veya 'fieldname : dtel ...;'
# Tablo/alan/DTEL adları `ad_politikasi` gramerinden (#402 K1). Eski `[a-z][a-z0-9_]*` iki kör
# nokta üretiyordu: ① namespace'li tablo "define table yok, kapsam dışı" (measured=TRUE!) ·
# ② namespace'li ALAN (`/nspc/fld : …`) haritaya girmiyordu ⇒ canlıdaki o alanın DROP'u GÖRÜNMEZDİ.
# #408 / Q399: tip konumu TAM metinle alınır (`abap.char(100)`, `abap.dec( 15, 3 )`) — eski
# grup ilk ad parçasında (`.`) duruyordu, her yerleşik tip `abap` oluyordu.
FIELD_RE = re.compile(
    r'^\s*(?:key\s+)?(' + AD_ADAYI + r')\s*:\s*(' + AD_ADAYI
    + r'(?:\s*\.\s*[A-Za-z0-9_]+(?:\s*\(\s*\d+\s*(?:,\s*\d+\s*)?\))?)?)',
    re.IGNORECASE | re.MULTILINE)
# `define table function` bir DDLS'tir (TABL değil) — `function` tablo adı sanılmasın (kardeş:
# check_sap_active_version 2026-07-30 vakası).
TABLE_NAME_RE = re.compile(r'define\s+table\s+(?!function\b)(' + AD_ADAYI + r')', re.IGNORECASE)
TABLE_KW_RE = re.compile(r'define\s+table\s+(?!function\b)', re.IGNORECASE)
# Alan satırı OLMAYAN anahtar kelimeler (yanlış yakalamayı önle)
_NON_FIELD = {'define', 'table', 'with', 'include'}


def cozulemeyen_alanlar(text: str) -> list[str]:
    """Alan konumunda olup katı ad gramerine UYMAYAN adlar (`/ab/x : …`)."""
    return [fld for fld, _ in FIELD_RE.findall(text) if not ad_coz(fld)[0]]


def tip_metni(ham: str) -> str:
    """Tip metninin karşılaştırma biçimi: boşluksuz + küçük harf (`abap.dec( 15, 3 )` → `abap.dec(15,3)`)."""
    return re.sub(r'\s+', '', ham).lower()


def parse_fields(text: str) -> dict:
    """source metninden {field_lower: tip_metni} haritası (gramere uymayan alan hariç).

    Tip metni DTEL adı (`zsd001_e_x`) ya da TAM yerleşik tiptir (`abap.char(10)`)."""
    out = {}
    for fld, tip in FIELD_RE.findall(text):
        if fld.lower() in _NON_FIELD or not ad_coz(fld)[0]:
            continue
        out[fld.lower()] = tip_metni(tip)
    return out


# ── FİZİKSEL TİP (#408 / Q399) ────────────────────────────────────────────────
# Fiziksel tip = (ADT `dataType`, uzunluk, ondalık). Yerleşik `abap.<tip>` adı ADT DTEL XML'inin
# `dataType` değeriyle BİREBİR aynıdır (büyük harf). ÖLÇÜLDÜ 2026-11-11 (salt-okur GET, s4_private):
# CLNT 3 · LANG 1 · INT1 3 · INT2 5 · INT4 10 · DATS 8 · TIMS 6 · FLTP 16/16 · CUKY 5 · UNIT 3 ·
# CHAR · NUMC · RAW · DEC/CURR/QUAN (uzunluk+ondalık) · `STRING`/`RAWSTRING` uzunluk 0 (ADT bu iki
# tip için `STRG`/`RSTR` DEĞİL, tam adı döner). ÖLÇÜLMEDİ: INT8 · DATN · TIMN · UTCL · ACCP · PREC ·
# SSTRING · decfloat aileleri (standart DTEL'i bulunamadı) — sabit-uzunluk kümesine yalnız DDIC
# tanımından alındı; ad farklı çıkarsa sonuç "tür değişti" (BLOCKER) olur, gevşemez.
SABIT_UZUNLUK = frozenset({'CLNT', 'LANG', 'INT1', 'INT2', 'INT4', 'INT8', 'DATS', 'TIMS', 'FLTP',
                           'CUKY', 'DATN', 'TIMN', 'UTCL', 'ACCP', 'PREC'})
SINIRSIZ_SIFIR = frozenset({'STRING', 'RAWSTRING'})   # uzunluk 0 = sınırsız
_YERLESIK_RE = re.compile(r'\Aabap\.([a-z0-9_]+)(?:\((\d+)(?:,(\d+))?\))?\Z')


def yerlesik_fiziksel(tip: str):
    """`abap.char(10)` → ('CHAR', 10, 0); yerleşik değilse None. Uzunluk yoksa uzunluk None."""
    m = _YERLESIK_RE.match(tip)
    if not m:
        return None
    return (m.group(1).upper(), int(m.group(2)) if m.group(2) else None,
            int(m.group(3)) if m.group(3) else 0)


def _xml_alani(govde: str, ad: str) -> str | None:
    m = re.search(r'<(?:\w+:)?' + ad + r'>([^<]*)</(?:\w+:)?' + ad + r'>', govde)
    if m:
        return m.group(1).strip()
    return '' if re.search(r'<(?:\w+:)?' + ad + r'\s*/>', govde) else None


def dtel_fiziksel(govde: str):
    """ADT veri öğesi XML'i → ((dataType, uzunluk, ondalık), None) ya da (None, neden-slug)."""
    dt = _xml_alani(govde, 'dataType')
    if not dt:
        return None, 'dtel-veri-tipi-yok'
    try:
        uz = int(_xml_alani(govde, 'dataTypeLength') or '0')
        on = int(_xml_alani(govde, 'dataTypeDecimals') or '0')
    except ValueError:
        return None, 'dtel-uzunluk-okunamadi'
    return (dt.upper(), uz, on), None


def tip_karsilastir(eski, yeni) -> str:
    """İki fiziksel tip → 'ayni' | 'genisleme' | 'daralma' | 'tur' | 'olculemedi'."""
    if eski[0] != yeni[0]:
        return 'tur'
    dt = eski[0]
    if dt in SABIT_UZUNLUK:
        return 'ayni'
    (_, uz_e, on_e), (_, uz_y, on_y) = eski, yeni
    if dt in SINIRSIZ_SIFIR:
        uz_e = float('inf') if not uz_e else uz_e
        uz_y = float('inf') if not uz_y else uz_y
    if uz_e is None or uz_y is None:
        return 'olculemedi'          # değişken uzunluklu tipte uzunluk yazılmamış
    on_e, on_y = on_e or 0, on_y or 0
    tam_e, tam_y = uz_e - on_e, uz_y - on_y   # tam sayı haneleri (DEC/CURR/QUAN; diğerlerinde ondalık 0)
    if (tam_e, on_e) == (tam_y, on_y):
        return 'ayni'
    if tam_y >= tam_e and on_y >= on_e:
        return 'genisleme'
    return 'daralma'


def fiziksel_goster(f) -> str:
    dt, uz, on = f
    if dt in SABIT_UZUNLUK or uz is None or (dt in SINIRSIZ_SIFIR and not uz):
        return dt
    return f'{dt}({uz},{on})' if on else f'{dt}({uz})'


class FizikselCozucu:
    """Tip metni → fiziksel tip; DTEL'ler SAP'den GET ile (ad başına tek istek, önbellekli)."""

    def __init__(self, client, adt_seg):
        self._client, self._seg, self._onbellek = client, adt_seg, {}

    def coz(self, tip: str):
        """((dataType, uzunluk, ondalık), None) ya da (None, neden-slug)."""
        y = yerlesik_fiziksel(tip)
        if y is not None:
            return y, None
        if tip.startswith('abap.'):
            return None, 'yerlesik-tip-ayristirilamadi'
        if not ad_coz(tip)[0]:
            return None, 'dtel-adi-cozulemedi'
        if tip not in self._onbellek:
            self._onbellek[tip] = self._getir(tip)
        return self._onbellek[tip]

    def _getir(self, dtel: str):
        c = self._client
        try:
            r = c.session.get(c.url + f'/sap/bc/adt/ddic/dataelements/{self._seg(dtel)}',
                              params={'sap-client': getattr(c, 'client', None) or '100'},
                              verify=False, timeout=15)
        except Exception as e:  # noqa: BLE001 — okunamadı ≠ yok
            return None, f'dtel-get-hata-{type(e).__name__}'
        if r.status_code != 200:
            return None, f'dtel-get-http-{r.status_code}'
        return dtel_fiziksel(r.text)


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
    table = ad_coz(m.group(1))[0] if m else ''
    if not table and TABLE_KW_RE.search(new_text):
        # #402 K2: `define table` VAR ama ad katı gramere uymadı (ör. `/AB/T`) ⇒ ÖLÇÜLEMEDİ.
        # Eski hâl "kapsam dışı" + measured=TRUE idi: DROP-guard koşmadan "ölçtüm, temiz".
        print(f'ÖLÇÜLEMEDİ — {path.name} `define table` içeriyor ama tablo adı çözülemedi '
              f'→ DROP-guard KOŞMADI')
        gate_status(_GATE, 'SKIPPED', False, 'ad-cozulemedi')
        return 0
    if not table:
        print(f'OK — {path.name} bir DDIC tablo tanımı değil (define table yok), kapsam dışı')
        gate_status(_GATE, 'OK', True, 'kapsam-disi-tablo-degil')
        return 0
    bozuk = cozulemeyen_alanlar(new_text)
    if bozuk:
        print(f'ÖLÇÜLEMEDİ — {path.name}: alan adı çözülemedi {bozuk[:5]} → DROP kıyası eksik '
              f'olurdu, KOŞMADI')
        gate_status(_GATE, 'SKIPPED', False, 'ad-cozulemedi')
        return 0
    new_fields = parse_fields(new_text)
    if not new_fields:
        print(f'OK — {path.name} alan çıkarılamadı, kapsam dışı')
        # ⚠ "alan çıkarılamadı" bir kapsam-dışılık DEĞİL, AYRIŞTIRMA BAŞARISIZLIĞIDIR:
        # DROP-guard yerel alanları okuyamadıysa canlıyla kıyaslayamaz. Metin "kapsam
        # dışı" diyor ama ölçüm YAPILMADI (B3-01).
        gate_status(_GATE, 'SKIPPED', False, 'yerel-alan-cikarilamadi')
        return 0

    # SAP'den canlı source çek
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.ad_politikasi import url_segmenti as _adt_seg  # noqa: E402 — Q393 P2a: ADT yol parcasi tek kaynak
    try:
        from sap_adt_lib import SAPADTClient  # type: ignore
        client = SAPADTClient()
        r = client.session.get(
            client.url + f'/sap/bc/adt/ddic/tables/{_adt_seg(table)}/source/main',
            params={'sap-client': '100', 'sap-language': 'TR'},
            headers={'Accept': 'text/plain'}, verify=False, timeout=15)
    except Exception as e:
        print(f'UYARI: SAP bağlantısı kurulamadı, DROP-guard atlandı: {e}', file=sys.stderr)
        sap_baglanti_yok(_GATE)
        return 0

    if r.status_code == 404:
        print(f'OK — {table.upper()} SAP\'de yok (yeni yaratım) → DROP-guard kapsam dışı')
        # 404 GERÇEK hüküm: canlı tablo yok => DROP edilecek alan da yok. ÖLÇÜLDÜ.
        gate_status(_GATE, 'OK', True, 'yeni-yaratim-canli-tablo-yok')
        return 0
    if r.status_code != 200:
        print(f'UYARI: canlı source alınamadı (HTTP {r.status_code}), DROP-guard atlandı',
              file=sys.stderr)
        gate_status(_GATE, 'SKIPPED', False, f'sap-get-http-{r.status_code}')
        return 0

    if cozulemeyen_alanlar(r.text):
        print(f'UYARI: canlı {table.upper()} source\'unda alan adı çözülemedi '
              f'{cozulemeyen_alanlar(r.text)[:5]} → DROP kıyası eksik olurdu, atlandı', file=sys.stderr)
        gate_status(_GATE, 'SKIPPED', False, 'ad-cozulemedi')
        return 0
    live_fields = parse_fields(r.text)
    if not live_fields:
        print(f'UYARI: canlı {table.upper()} source\'undan alan çıkarılamadı, atlandı',
              file=sys.stderr)
        gate_status(_GATE, 'SKIPPED', False, 'canli-alan-cikarilamadi')
        return 0

    dropped = [f for f in live_fields if f not in new_fields]
    type_changed = [(f, live_fields[f], new_fields[f])
                    for f in live_fields if f in new_fields and live_fields[f] != new_fields[f]]
    added = [f for f in new_fields if f not in live_fields]

    print(_KAPSAM_BEYANI)
    # Tip metni değişen her alan fiziksel tipe çözülür (#408 / Q399). Ad metni farkı tek başına
    # hüküm DEĞİLDİR: hüküm fiziksel tip kıyasından gelir.
    cozucu = FizikselCozucu(client, _adt_seg)
    tip_hukmu = []      # (alan, eski metin, yeni metin, karar, ayrıntı)
    for f, old, new in type_changed:
        fe, ne = cozucu.coz(old)
        fy, ny = cozucu.coz(new)
        if fe is None or fy is None:
            neden = '; '.join(f'{t}: {n}' for t, n in ((old, ne), (new, ny)) if n)
            tip_hukmu.append((f, old, new, 'olculemedi', neden))
            continue
        karar = tip_karsilastir(fe, fy)
        ayrinti = f'{fiziksel_goster(fe)} → {fiziksel_goster(fy)}'
        if karar == 'olculemedi':
            ayrinti += ' (değişken uzunluklu tipte uzunluk yazılmamış)'
        tip_hukmu.append((f, old, new, karar, ayrinti))
    tip_blocker = [h for h in tip_hukmu if h[3] in ('daralma', 'tur', 'olculemedi')]
    genisleme = [h for h in tip_hukmu if h[3] == 'genisleme']
    ayni_tip = [h for h in tip_hukmu if h[3] == 'ayni']

    # Onaylı (ack) DROP'ları ayır — kullanıcı+lider bilinçli silme onayı (ADR 0005-B).
    # Tip değişikliği ack KAPSAMI DIŞINDA: daralma/tür/ölçülemeyen tip her zaman BLOCKER.
    unack_dropped = [f for f in dropped if f not in ack]
    ack_dropped = [f for f in dropped if f in ack]

    for f, old, new, _k, ayrinti in ayni_tip:
        # ⚠GEVŞETME (#408, kullanıcı onayı 2026-11-08): eski hâl BLOCKER'dı (ad metni kıyası).
        print(f'[INFO] {table.upper()} — \'{f}\' DTEL değişti, fiziksel tip aynı: {old} → {new} '
              f'({ayrinti}) — veri dönüşümü yok')
    for f, old, new, _k, ayrinti in genisleme:
        print(f'[WARNING] {table.upper()} — \'{f}\' tip GENİŞLEDİ {old} → {new} ({ayrinti}) — '
              f'veri kaybı beklenmez; tablo dönüşümü (SE14) gerekebilir', file=sys.stderr)

    if not unack_dropped and not tip_blocker:
        if ack_dropped:
            print(f'[ACK-WARNING] {table.upper()} — onaylı DROP (kullanıcı+lider bilinçli, '
                  f'ADR 0005-B gate geçildi): {", ".join(ack_dropped)}. '
                  f'Başka onaysız drop ya da bloklayan tip değişikliği yok; veri-kaybı bilinçli '
                  f'kabul edildi.')
        msg = f'OK — {table.upper()} ALTER additive/güvenli'
        if added:
            msg += f' (+{len(added)} yeni alan: {", ".join(added)})'
        print(msg)
        if genisleme:
            gate_status(_GATE, 'FINDING', True, 'tip-genisleme')
        elif ack_dropped:
            gate_status(_GATE, 'OK', True, 'onayli-drop-ack')
        elif ayni_tip:
            gate_status(_GATE, 'OK', True, 'dtel-degisti-tip-ayni')
        else:
            gate_status(_GATE, 'OK', True, 'additive-guvenli')
        return 0

    print(f'\n[BLOCKER] {table.upper()} ALTER veri-kaybı riski '
          f'(checklist C-TBL-DROP/RENAME/TYPE-01):', file=sys.stderr)
    for f in unack_dropped:
        print(f'  DROP   : mevcut alan \'{f}\' ({live_fields[f]}) yeni source\'ta YOK '
              f'→ veri kaybı (onaysız — geçmek için --ack-drop {f})', file=sys.stderr)
    for f, old, new, karar, ayrinti in tip_blocker:
        if karar == 'olculemedi':
            print(f'  TYPE   : \'{f}\' {old} → {new}: ÖLÇÜLEMEDİ — fiziksel tip çözülemedi '
                  f'({ayrinti}) → BLOCKER kalır (ack KAPSAMI DIŞI)', file=sys.stderr)
        else:
            ad = 'DARALMA' if karar == 'daralma' else 'TÜR DEĞİŞTİ'
            print(f'  TYPE   : \'{f}\' {ad} {old} → {new} ({ayrinti}) '
                  f'(veri-dönüşüm/kayıp riski — ack KAPSAMI DIŞI)', file=sys.stderr)
    if ack_dropped:
        print(f'  NOT    : {", ".join(ack_dropped)} onaylıydı ama başka onaysız drop/tip '
              f'değişikliği var → yine BLOCKER (hedefli ack, blanket değil)', file=sys.stderr)
    print('\nÇözüm: Bilinçli silme ise ilgili alanı --ack-drop <alan> ile onayla (kullanıcı+lider '
          'onayı sonrası). Kazara ise canlı source\'u GET ile alıp sadece additive değişiklik yap.',
          file=sys.stderr)
    # ⚠GEVŞETME 2. hücre (#408): `measured=false` YALNIZ tek BLOCKER nedeni çözülemeyen tip iken.
    # Ölçülmüş drop / daralma / tür değişikliği varsa basılmaz ⇒ tüketici FAIL görmeye devam eder.
    if not unack_dropped and all(h[3] == 'olculemedi' for h in tip_blocker):
        gate_status(_GATE, 'FAIL', False, 'fiziksel-tip-cozulemedi')
    return 1


if __name__ == '__main__':
    sys.exit(main())
