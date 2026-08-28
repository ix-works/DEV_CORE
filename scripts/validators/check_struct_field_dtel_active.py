"""
check_struct_field_dtel_active.py — Struct/Table source'ta kullanılan ZSD<NNN>_E_*
DTEL'lerin SAP'de aktif olup olmadığını kontrol eder.

Sprint 6 (Z Structures) için kritik: struct'ta kullanılan DTEL'ler aktif değilse
aktivasyon fail eder + cascade fail (dependent struct'lar/CDS'ler).

Kullanım:
    python scripts/validators/check_struct_field_dtel_active.py <artifact>

Exit kodu:
    0 — Tüm Z DTEL'ler aktif  (VEYA: kapsam dışı / ÖLÇÜLEMEDİ — ayrım exit kodunda DEĞİL,
        `IX-GATE-STATUS` satırındadır; aşağıya bak)
    1 — En az 1 DTEL inactive veya yok

⛔ `exit 0` ÜÇ ANLAMLIDIR — makinece okunur ayrım (2026-08-28, B3-01):
Bu gate `run_review` zincirinde **BLOCKER**'dır (table_creation · table_update ·
struct_creation) ve SAP bağlantısı yokken `return 0` veriyordu ⇒ reviewer bunu "temiz"
sayıyordu: *koruma, girdisi yokken kendini KAPATIYORDU* (fail-open). Çıkış kodu
DEĞİŞTİRİLMEDİ (offline zinciri kırmamak bilinçli bir karardı); bunun yerine her exit-0
yolu `_gate_status.gate_status()` ile `measured=true|false` beyan eder. Tüketici
`run_review.py:271-386` `rc==0 && measured=false` gördüğünde `PASS` değil **`SKIP`**
kaydeder ve SKIP kendi şiddetiyle (burada BLOCKER) verdict'e sayılır.
"""
# ENFORCES: C-STR-FIELD-02, C-TBL-DTEL-01  (ADR 0019 coverage binding)
import argparse
import re
import sys
import urllib3
from pathlib import Path

# Sözleşme yardımcısı script'in KENDİ dizinindedir. `python <yol>/check_...py` ile
# koşulduğunda sys.path[0] zaten o dizindir, ama run_review/run_all subprocess'i,
# `runpy` ve `spec_from_file_location` ile yükleyen fixture'lar bunu GARANTİ ETMEZ —
# açık insert olmadan ImportError alınır (fail-closed olurdu ama gürültülü).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _gate_status import gate_status, sap_baglanti_yok  # noqa: E402

_GATE = Path(__file__).stem

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def main() -> int:
    parser = argparse.ArgumentParser(description='Z DTEL aktivasyon kontrolü')
    parser.add_argument('artifact')
    parser.add_argument('--strict', action='store_true',
                       help='(uyumluluk; NO-OP — şiddeti DEĞİŞTİRMEZ, run_all --strict kazara terfi ettirmesin; ADR 0019 §54)')
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
        # ÖLÇÜLDÜ: dosya okundu, Z DTEL yok ⇒ denetlenecek bir şey YOK. Bu "koşamadım"
        # DEĞİL, gerçek bir kapsam-dışı hükmüdür → measured=true.
        gate_status(_GATE, 'OK', True, 'kapsam-disi-z-dtel-yok')
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

    print(f'{path.name} — {len(z_dtels)} Z DTEL kontrol ediliyor...')
    inactive = []
    missing = []
    # KISMİ KÖRLÜK (B3-01): non-200 ve istisna dalları `continue` ediyordu ⇒ o DTEL HİÇ
    # okunmamış olmasına rağmen aşağıdaki "hepsi aktif" cümlesi basılıyordu. Bu, bağlantı
    # kopukluğundan AYRI ve daha sinsi bir yalandır: bağlantı VARDIR, cevap gelmemiştir.
    okunamayan = []

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
                okunamayan.append(dtel)
                continue
            m = re.search(r'adtcore:version="(\w+)"', r.text)
            version = m.group(1) if m else '?'
            if version != 'active':
                inactive.append((dtel, version))
        except Exception as e:
            print(f'  UYARI: {dtel} hata: {e}', file=sys.stderr)
            okunamayan.append(dtel)

    if not missing and not inactive:
        if okunamayan:
            # "Bulunamadı ≠ yok": okunamayan DTEL inactive OLABİLİR. Yeşil demek yasak.
            print(f'[ÖLÇÜLEMEDİ] {len(okunamayan)}/{len(z_dtels)} Z DTEL okunamadı '
                  f'({", ".join(okunamayan)}) — kalanlar aktif, ama TEMİZ denemez.',
                  file=sys.stderr)
            gate_status(_GATE, 'SKIPPED', False, 'kismi-okunamadi')
            return 0
        print(f'OK — {len(z_dtels)} Z DTEL hepsi aktif')
        gate_status(_GATE, 'OK', True, 'temiz')
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

    # rc=1 dalında tüketici beyanı SORMAZ (gürültülü sonuç zaten verdict'e giriyor); yine
    # de basılır ki sözleşme tam olsun ve doğrudan koşan insan/araç aynı kanalı okusun.
    gate_status(_GATE, 'FINDING', True, f'{len(missing)}-eksik-{len(inactive)}-inaktif')
    return 1


if __name__ == '__main__':
    sys.exit(main())
