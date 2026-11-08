#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BAdI enhancement spot (ENHS/XSB) + BAdI tanimi yarat / guncelle (DEV_CORE #413).

AKIS (her yazma): ad denetimi (ADR 0005-A) -> GET -> [404 ise bos kabuk POST] -> GET belgesini
modele ayristir -> YALNIZ verilen alanlari degistir -> TAM belge PUT (kilit -> PUT -> unlock)
-> aktive et (hukum: activationExecuted + worklist sondasi; `adtcore:version` DEGIL) ->
readback kiyasi (gonderilen <-> okunan).

⛔ PUT TAM BELGEDIR: gonderilmeyen filtre/tanim sunucuda SILINIR (olculdu). Bu yuzden belge
   daima GET'ten kurulur; kaldirma YALNIZ acik bayrakla (--remove-*) yapilir. GET belgesi
   aracin modellemedigi bir alan tasiyorsa yazma YAPILMAZ (alan sessizce silinirdi).
⛔ SIRA: arabirim + fallback/ornek siniflar ONCE aktif olmali; BAdI'ye atif yapan siniflar
   (implementasyon / cagiran) spot aktive edildikten SONRA. Recete:
   playbook/adt-enhancement-spot-badi.md. MCP yuzeyi YOK — bu CLI kullanilir.

Kullanim:
  python populate_badi_spot.py --spot ZSD001_ES_ORNEK --show
  python populate_badi_spot.py --spot ZSD001_ES_ORNEK --transport <TR> \\
      --package ZSD001 --description "Ornek BAdI noktasi" \\
      --badi ZSD001_BADI_ORNEK --interface ZIF_SD001_BADI_ORNEK --shorttext "Ornek BAdI" \\
      --fallback-class ZCL_SD001_BADI_ORNEK_FB --sample-class ZCL_SD001_BADI_ORNEK_EX \\
      --filter ULKE C "Ulke" --filter-check ULKE LAND
  python populate_badi_spot.py --spot ZSD001_ES_ORNEK --transport <TR> \\
      --badi ZSD001_BADI_ORNEK --remove-filter ULKE
  python populate_badi_spot.py --spot ZSD001_ES_ORNEK --transport <TR> --spec tanimlar.json

COKLU TANIM: PUT spot'un TUM BAdI listesini degistirir (SAP kaynagi: once hepsi silinir). Arac
yalniz verilen tanim(lar)i ekler/gunceller, digerlerini okunan belgeden aynen tasir; tanim silme
yalniz --remove-badi. Govde sirasi: canlida olan tanimlar once, yeniler sonda (SAP calisma alani
tuzagi — `sap_adt_lib.enhs_govde_sirasi`). `--coklu-kullanim evet` => singleUse="false" (TERS).

Cikis: 0 tamam · 1 akis hatasi (HTTP / kilit / aktivasyon / readback) · 2 kullanim ya da
koruma reddi (SAP'ye istek gitmeden).
"""
import argparse
import json
import sys
from pathlib import Path

if sys.platform == 'win32' and __name__ == '__main__':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import sap_adt_lib as L  # noqa: E402


def _parser():
    p = argparse.ArgumentParser(description='BAdI enhancement spot (ENHS/XSB) + BAdI tanimi')
    p.add_argument('--spot', required=True, help='Enhancement spot adi (en cok 30 karakter)')
    p.add_argument('--transport', help='Transport istegi (yazmada ZORUNLU)')
    p.add_argument('--cwd', help='.conn_adt iceren proje dizini')
    p.add_argument('--package', help='Spot yoksa: yaratilacak paket')
    p.add_argument('--description', help='Spot yoksa: spot aciklamasi')
    p.add_argument('--show', action='store_true', help='Yalniz oku ve modeli yaz (yazma yok)')
    p.add_argument('--dry-run', action='store_true', help='Belgeyi kur ve bas, YAZMA')
    p.add_argument('--no-activate', action='store_true', help='PUT sonrasi aktive etme')
    p.add_argument('--badi', help='Degistirilecek / eklenecek BAdI tanimi')
    p.add_argument('--remove-badi', action='store_true', help='--badi tanimini spottan KALDIR')
    p.add_argument('--interface', help='BAdI arabirimi (yeni tanimda zorunlu)')
    p.add_argument('--shorttext', help='BAdI kisa metni (yeni tanimda zorunlu)')
    p.add_argument('--coklu-kullanim', choices=('evet', 'hayir'),
                   help='Coklu kullanim: evet -> singleUse=false, hayir -> singleUse=true (TERS esleme)')
    p.add_argument('--spec', help='JSON spec: {"tanimlar": [..]} — N tanimi tek PUT ta ekle/guncelle')
    p.add_argument('--fallback-class', help='Fallback sinifi (useFallbackClass=true olur)')
    p.add_argument('--remove-fallback-class', action='store_true', help='Fallback sinifini kaldir')
    p.add_argument('--sample-class', action='append', default=[], help='Ornek sinif ekle (tekrar)')
    p.add_argument('--remove-sample-class', action='append', default=[], help='Ornek sinif kaldir')
    p.add_argument('--filter', nargs=3, action='append', default=[],
                   metavar=('AD', 'TIP', 'KISA_METIN'), help='Filtre ekle/kisa metnini guncelle')
    p.add_argument('--filter-check', nargs=2, action='append', default=[],
                   metavar=('FILTRE', 'DTEL'), help='Filtre degerini veri ogesiyle kontrol et')
    p.add_argument('--remove-filter', action='append', default=[], help='Filtre kaldir (tekrar)')
    return p


def _degisiklik(a):
    if not a.badi:
        return None
    return {'badi': a.badi, 'kaldir': a.remove_badi, 'shorttext': a.shorttext,
            'interface': a.interface,
            'singleUse': L.enhs_coklu_kullanim(a.coklu_kullanim) if a.coklu_kullanim else None,
            'fallback': a.fallback_class,
            'fallback_kaldir': a.remove_fallback_class, 'ornek_ekle': a.sample_class,
            'ornek_kaldir': a.remove_sample_class,
            'filtre_ekle': [{'name': n, 'type': t, 'shorttext': s} for n, t, s in a.filter],
            'filtre_kontrol': {f.upper(): d for f, d in a.filter_check},
            'filtre_kaldir': a.remove_filter}


def _degisiklik_bayragi_var(a):
    return any([a.remove_badi, a.interface, a.shorttext is not None, a.coklu_kullanim,
                a.fallback_class, a.remove_fallback_class, a.sample_class,
                a.remove_sample_class, a.filter, a.filter_check, a.remove_filter])


def calistir(argv, client=None, root=None):
    """CLI govdesi (fixture'lar istemciyi enjekte eder). Doner: cikis kodu."""
    a = _parser().parse_args(argv)
    spot = a.spot.strip().upper()
    yazma = not a.show
    if a.spec and (a.badi or _degisiklik_bayragi_var(a)):
        print('[FAIL] --spec tek basina verilir (--badi / alan bayraklariyla birlikte DEGIL)')
        return 2
    spec = None
    if a.spec:
        try:
            spec = json.loads(Path(a.spec).read_text(encoding='utf-8'))
        except Exception as exc:  # noqa: BLE001
            print('[FAIL] spec okunamadi: %s' % exc)
            return 2
    if a.show and (_degisiklik_bayragi_var(a) or a.badi or spec is not None):
        print('[FAIL] --show yalniz okur; degisiklik bayragiyla birlikte verilemez')
        return 2
    if yazma and not a.transport:
        print('[FAIL] --transport zorunlu (yazma). list_transports.py --modifiable-only ile '
              'kullaniciya SOR; numara uydurma / hafizadan kullanma.')
        return 2
    if yazma and not a.badi and spec is None and not (a.package and a.description):
        print('[FAIL] degisiklik yok: --badi (+ alanlar) ya da yeni spot icin --package/--description')
        return 2
    if a.badi and not a.remove_badi and not _degisiklik_bayragi_var(a):
        print('[FAIL] --badi icin degistirilecek alan verilmedi')
        return 2
    adlar = [a.badi.strip().upper()] if a.badi else []
    if spec is not None:
        adlar = [str((o or {}).get('badi') or '').strip().upper()
                 for o in (spec.get('tanimlar') or [] if isinstance(spec, dict) else [])]
    hatalar = L.enhs_ad_denetimi(spot, adlar, root=root)
    if hatalar:
        for h in hatalar:
            print('[FAIL] ADR 0005-A / ad siniri: %s' % h)
        return 2

    if client is None:
        if a.cwd:
            L.set_explicit_working_dir(a.cwd)
        client = L.SAPADTClient()

    r = client.get_enhancement_spot(spot)
    yaratildi = False
    if r.status_code == 404:
        if a.show:
            print('[FAIL] spot yok: %s' % spot)
            return 1
        if not (a.package and a.description):
            print('[FAIL] spot yok (%s); yaratmak icin --package ve --description ver' % spot)
            return 2
        if a.dry_run:
            print('[DRY-RUN] spot yok; bos kabuk yaratilacakti:')
            print(L.enhs_bos_kabuk_govdesi(spot, a.description, a.package, client.language))
            return 0
        y = client.create_enhancement_spot(spot, a.description, a.package, a.transport, root=root)
        if not y['ok']:
            print('[FAIL] spot yaratilamadi: HTTP %s %s' % (y['status'], y['text'][:300]))
            return 1
        yaratildi = True
        print('[OK] bos spot yaratildi: %s (%s)' % (spot, y.get('location')))
        r = client.get_enhancement_spot(spot)
    if r.status_code != 200:
        print('[FAIL] spot okunamadi: HTTP %s' % r.status_code)
        return 1
    try:
        model = L.enhs_belgesi_ayristir(r.content)
    except Exception as exc:  # noqa: BLE001
        print('[FAIL] spot belgesi ayristirilamadi: %s' % exc)
        return 1
    if (model['spot'].get('masterSystem') or '').upper() == 'SAP':
        print('[FAIL] standart obje (masterSystem=SAP) — ADR 0005-A, yazma YOK')
        return 2
    if a.show:
        print(json.dumps(model, ensure_ascii=False, indent=1))
        return 0
    if model['modellenmeyen']:
        print('[FAIL] belge aracin modellemedigi alan(lar) tasiyor; TAM-belge PUT bunlari '
              'SILERDI — yazma YOK: %s' % ', '.join(model['modellenmeyen']))
        return 1

    yeni, yapilan = model, []
    d = _degisiklik(a)
    if d is not None:
        try:
            yeni, yapilan = L.enhs_tanim_uygula(model, d)
        except ValueError as exc:
            print('[FAIL] %s' % exc)
            return 2
    elif spec is not None:
        try:
            yeni, yapilan = L.enhs_spec_uygula(model, spec)
        except (ValueError, AttributeError, TypeError) as exc:
            print('[FAIL] spec: %s' % exc)
            return 2
    if not yapilan and not yaratildi:
        print('[OK] degisiklik yok')
        return 0
    govde = L.enhs_belgesi_kur(yeni)
    if a.dry_run:
        print('[DRY-RUN] degisiklikler: %s' % '; '.join(yapilan))
        print(govde)
        return 0
    if yapilan:
        w = client.write_enhancement_spot(spot, yeni, a.transport, root=root)
        if w['lock_released'] is False:
            print(L.kilit_birakilamadi_uyarisi(spot))
        if not w['ok']:
            print('[FAIL] yazma: %s' % w['hata'])
            return 1
        print('[OK] PUT %s: %s' % (w['put_status'], '; '.join(yapilan)))
    if a.no_activate:
        print('[UYARI] --no-activate: spot INAKTIF birakildi (worklist\'te kalir)')
        return 0
    ak = client.activate_enhancement_spot(spot)
    if not ak['aktif']:
        if ak['dogrulanamadi']:
            print('[FAIL] aktivasyon DOGRULANAMADI (worklist sondasi: %s) — aktif SAYILMAZ'
                  % ak['worklist_sonda'])
        else:
            print('[FAIL] aktivasyon olmadi: hukum=%s sebep=%s kalan=%s hatalar=%s' % (
                ak['aktivasyon'].get('aktivasyon_hukmu'), ak['aktivasyon'].get('hukum_sebep'),
                ['%s (%s)' % (k.get('name'), k.get('type')) for k in ak['kalan_inaktif']],
                [e.get('message') for e in ak['errors']][:3]))
        return 1
    print('[OK] aktive: %s (worklist: %s)' % (spot, ak['worklist_sonda']))
    r = client.get_enhancement_spot(spot)
    if r.status_code != 200:
        print('[FAIL] readback HTTP %s' % r.status_code)
        return 1
    try:
        okunan = L.enhs_belgesi_ayristir(r.content)
    except Exception as exc:  # noqa: BLE001
        print('[FAIL] readback ayristirilamadi: %s' % exc)
        return 1
    fark = L.enhs_kiyasla(yeni, okunan)
    if fark:
        print('[FAIL] readback gonderilenle ayni DEGIL:')
        for f in fark:
            print('       - %s' % f)
        return 1
    print('[OK] readback gonderilenle esit (%d tanim)' % len(okunan['tanimlar']))
    if okunan.get('sunucu_ek'):
        print('[BILGI] sunucu ek alanlari (kiyas disi): %s' % ', '.join(sorted(set(okunan['sunucu_ek']))))
    return 0


def main():
    return calistir(sys.argv[1:])


if __name__ == '__main__':
    sys.exit(main())
