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
    0 — version=="active"  (VEYA: ÖLÇÜLEMEDİ — ayrım exit kodunda DEĞİL, `IX-GATE-STATUS`
        satırındadır; aşağıya bak)
    1 — inactive veya bulunamadı

⛔ `exit 0` ÇOK ANLAMLIDIR — makinece okunur ayrım (2026-08-28, B3-01):
Bu gate `run_review` zincirinde **BLOCKER**'dır (struct_post_create · sap_active_check).
BEŞ ayrı yol `return 0` veriyordu ve hiçbiri "obje aktif" demiyordu: desteklenmeyen tip ·
SAP bağlantısı kurulamadı · GET istisnası · non-200 · version metadata yok. Reviewer
beşini de "temiz" sayıyordu ⇒ *post-activate doğrulaması, doğrulayamadığı anda yeşil
yanıyordu*. Çıkış kodu DEĞİŞTİRİLMEDİ; ayrım `_gate_status` kanalından gelir ve
`run_review.py:271-386` `measured=false` gördüğünde `SKIP` (=BLOCKER) kaydeder.
"""
# ENFORCES: C-RAP-ACT-01  (ADR 0019 coverage binding)
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _gate_status import gate_status, sap_baglanti_yok  # noqa: E402

_GATE = Path(__file__).stem

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


# Müşteri ad-alanı (ADR 0005-D): Z*/Y* ya da /NS/ ile başlayan namespace'li ad.
# `adt_push_source` zaten `require_customer_namespace` ile bunu ZORLUYOR ⇒ artefakttan
# ÇIKARILAN ad bu kalıba uymuyorsa, ortada var olmayan bir obje değil BAŞARISIZ BİR
# AYRIŞTIRMA vardır. Kullanım yeri: `main()` içindeki "AD ÇÖZÜLEMEDİ ≠ OBJE YOK" dalı.
# ⛔ Yalnız ÇIKARILAN ada uygulanır; `--name` ile gelen ad operatörün beyanıdır ve
#    filtrelenmez (aksi hâlde kapı, operatörün bilerek sorduğu objeyi sessizce atlardı).
_MUSTERI_AD_RE = re.compile(r'^(?:[ZY]\w*|/\w+/\w+)$', re.IGNORECASE)

# CDS DDL yorum biçimleri. `//` ve `--` TAM SATIR yorumları boşaltılır, `/* */` blok
# yorumu satır sayısı korunarak silinir.
_BLOK_YORUM_RE = re.compile(r'/\*.*?\*/', re.DOTALL)


def _yorumlari_siyir(text: str) -> str:
    """Obje adı çıkarımından ÖNCE yorumları sıyır (Q240, 2026-09-04).

    ⛔ VAKA (canlı, ölçüldü): projeksiyon view'ların başlık yorumunda
    ``//   `define root view entity` (temel `root`, projeksiyon da `root` olmalı).``
    kalıbı geçiyor. `re.search` İLK eşleşmeyi alır, yorum gerçek `define`'dan önce
    gelir, ve `(?:\\s+entity)?` grubu kapanış backtick'inde geri-izleyip **`entity`
    sözcüğünü obje adı sanar** → `/sap/bc/adt/ddic/ddl/sources/entity` → 404 →
    `[BLOCKER] ENTITY (ddls) SAP'de bulunamadı`. Bu bir SAHTE BLOCKER'dır: aynı obje
    `--name` ile sorulduğunda `version=active`. Tüketici projede 300 `.cds`'in **3'ü**
    bu hâldeydi (ölçüm 2026-09-04); ifade bir AÇIKLAMA KALIBI olduğu için tesadüf değil.

    Ev deseni (yeni tasarım DEĞİL): `check_rap_managed_etag._strip_comments` ve
    `check_rap_readonly_consumption._strip_comments` — iki kardeş kapı da kimlik
    çıkarmadan ÖNCE yorumu sıyırır. Buradaki tek fark blok yorumun da kapsanması.
    Ayrıca `playbook/lessons-learned.md` (2026-07-30, "1 eşleşme de 'var' demek
    değildir") aynı sınıfı yazıyor: *token'ı YORUM içinde bulan arama sinyal üretir*;
    önerdiği korunma da aynı — "iddiayı TANIMLAYICI satırdan doğrula".

    ⚠ String literalleri BİLEREK sıyrılmaz (`@EndUserText.label: 'define root view
    entity örneği'` gibi): literal ayrıştırmak yeni bir FP sınıfı açar. O vektör
    `_MUSTERI_AD_RE` katmanında yakalanır — ayrı değişmez, ayrı mutasyon.

    Satır SAYISI korunur (yorum satırı silinmez, boşaltılır): ileride satır numarası
    raporlanırsa kaymasın.
    """
    text = _BLOK_YORUM_RE.sub(lambda m: '\n' * m.group(0).count('\n'), text)
    out = []
    for line in text.splitlines():
        s = line.lstrip()
        out.append('' if (s.startswith('//') or s.startswith('--')) else line)
    return '\n'.join(out)


def infer_from_artifact(path: Path) -> tuple[str | None, str | None]:
    """Artifact'tan name + object_type tahmin et (YORUMLAR SIYRILMIŞ metinden)."""
    text = _yorumlari_siyir(path.read_text(encoding='utf-8', errors='replace'))
    # Struct/table: define structure NAME / define table NAME
    m = re.search(r'define\s+structure\s+(\w+)', text, re.IGNORECASE)
    if m:
        return m.group(1).upper(), 'structure'
    # ⚠ TABLE FUNCTION, `define table`'DAN ÖNCE denenmeli (2026-07-30 vakası).
    # `define table function ZSD001_I_X` metni `define\s+table\s+(\w+)` ile eşleşiyor ve
    # **"function"** kelimesini TABLO ADI sanıyordu → URL `/sap/bc/adt/ddic/tables/function`
    # → obje bulunamıyor → **false BLOCKER**. Vaka: bir AMDP table function'ın push'u
    # `activated:true` + "Active source verified" derken üst seviyede BLOCKER döndü;
    # aktivasyon gerçekte BAŞARILIYDI (içerik bayt-eşit doğrulandı).
    # Table function bir DDLS'tir (CDS ailesi), TABL değil.
    m = re.search(r'define\s+table\s+function\s+(\w+)', text, re.IGNORECASE)
    if m:
        return m.group(1).upper(), 'ddls'
    # Negatif lookahead: sıra bozulsa bile "function" tablo adı sanılmasın (çift emniyet).
    m = re.search(r'define\s+table\s+(?!function\b)(\w+)', text, re.IGNORECASE)
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
    parser.add_argument('--strict', action='store_true',
                       help='(uyumluluk; NO-OP — şiddeti DEĞİŞTİRMEZ, run_all --strict kazara terfi ettirmesin; ADR 0019 §54)')
    args = parser.parse_args()

    name = args.name
    obj_type = args.object_type

    if (not name or not obj_type) and args.artifact:
        p = Path(args.artifact)
        if not p.exists():
            print(f'HATA: {p} bulunamadı', file=sys.stderr)
            return 1
        n2, t2 = infer_from_artifact(p)
        # ── AD ÇÖZÜLEMEDİ ≠ OBJE YOK (Q240 ③, 2026-09-04) ────────────────────────
        # İki yol da buraya düşer: (a) hiç `define` bulunamadı (ör. `adt_push_source`
        # DTEL/DOMA çağrısı — kaynak XML'dir, ölçüldü: bugün `HATA: --name ... gerekli`
        # + rc=1 ⇒ her DTEL/DOMA push'unda verdict BLOCKER, failed_blocker=1) ·
        # (b) çıkarılan ad müşteri ad-alanında değil (ör. annotation literalinden
        # gelen `ORNEGI`). İkisi de bir ÖLÇÜM DEĞİL bir AYRIŞTIRMA BAŞARISIZLIĞIDIR;
        # bunu `rc=1` (=FAIL, "ölçtüm ve ihlal buldum") ya da 404 BLOCKER'ı ile
        # raporlamak kapıya söylemediği bir şey söyletir. Sözleşme gereği ölçemeyen
        # gate `measured=false` beyan eder; bloklama kararını TÜKETİCİ verir
        # (BLOCKER severity ⇒ `run_review` bunu yine SKIP=BLOCKER sayar; sessiz yeşil
        # DEĞİLDİR — yalnız GEREKÇE dürüstleşir ve `--cevrimdisi` indirimine girer).
        if not name and (not n2 or not _MUSTERI_AD_RE.match(n2)):
            print(f'SKIP — {p.name}: obje adı artefakttan çözülemedi '
                  f'(çıkarılan: {n2!r}); SAP sorgulanMADI. "404 = obje yok" demek '
                  f'sahte BLOCKER üretir. Adı biliyorsan --name/--object-type ver.',
                  file=sys.stderr)
            gate_status(_GATE, 'SKIPPED', False, 'ad-cozulemedi')
            return 0
        name = name or n2
        obj_type = obj_type or t2

    if not name or not obj_type:
        print('HATA: --name ve --object-type (veya artifact) gerekli', file=sys.stderr)
        return 1

    path_segment = ADT_PATHS.get(obj_type.lower())
    if not path_segment:
        print(f'UYARI: {obj_type} desteklenmiyor, atlandı (desteklenen: {list(ADT_PATHS)})')
        # Tip tanınmadı ⇒ obje SAP'de HİÇ sorgulanmadı. "Desteklemiyorum" bir aktiflik
        # hükmü DEĞİLDİR.
        gate_status(_GATE, 'SKIPPED', False, f'desteklenmeyen-tip-{obj_type.lower()}')
        return 0

    sys.path.insert(0, str(Path(__file__).parent.parent))
    try:
        from sap_adt_lib import SAPADTClient
        client = SAPADTClient()
    except Exception as e:
        print(f'UYARI: SAP bağlantısı kurulamadı, validator atlandı: {e}', file=sys.stderr)
        sap_baglanti_yok(_GATE)
        return 0

    try:
        r = client.session.get(
            client.url + f'/sap/bc/adt/{path_segment}/{name.lower()}',
            params={'sap-client': '100'}, verify=False, timeout=15
        )
    except Exception as e:
        print(f'UYARI: SAP GET hata: {e}', file=sys.stderr)
        gate_status(_GATE, 'SKIPPED', False, 'sap-get-istisnasi')
        return 0

    if r.status_code == 404:
        print(f'[BLOCKER] {name} ({obj_type}) SAP\'de bulunamadı (404).', file=sys.stderr)
        return 1
    if r.status_code != 200:
        print(f'UYARI: SAP GET {r.status_code} — validator atlandı', file=sys.stderr)
        gate_status(_GATE, 'SKIPPED', False, f'sap-get-http-{r.status_code}')
        return 0

    m = re.search(r'adtcore:version="(\w+)"', r.text)
    if not m:
        print(f'UYARI: {name} version metadata bulunamadı, atlandı', file=sys.stderr)
        gate_status(_GATE, 'SKIPPED', False, 'version-metadata-yok')
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
    gate_status(_GATE, 'OK', True, 'aktif')
    return 0


if __name__ == '__main__':
    sys.exit(main())
