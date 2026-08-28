#!/usr/bin/env python3
"""check_bdef_backtick.py — `.bdef` kaynaginda ters-tirnak (U+0060) yakalar.

NEDEN (ADR 0019 5 sart):

  1. HATA GERCEKTEN YASANDI — IKI KEZ. 2026-07-28'de ogrenildi ve temizlendi;
     2026-07-29'da ayni turun YENI yorumlariyla NUKSETTI (5 bdef).

  2. SONUC SESSIZ *ve* BUYUYOR. Ters-tirnak SAP'de cogaliyor: repo'da 2 iken canlida
     8 olcuLdu (x4 = iki pull+push turu, her tur ikiye katliyor). Hicbir hata mesaji
     yok; push "[OK]" der, aktivasyon type=E vermez. Fark ancak readback'te BAYT
     KIYASI yapilirsa gorulur — ve o kiyas her turda yapilmaz.
     ⚠ Bu, "geri alinabilir ama sessiz" degil: her tur onceki bozulmanin USTUNE
     katlandigi icin fark edilmeden buyuyor.

  3. BASKA KATMAN YAKALAMIYOR — OLCULDU (2026-07-29):
     · reviewer pre-flight bdef icin HIC KOSMUYOR: `OBJECT_TYPE_TO_TASK` icinde
       'bdef' anahtari YOK -> `task_for_push('bdef')` = None -> ADR 0006 zinciri atlanir.
       (Ayni bosluk 'class' ve 'srvd' icin de var — AYRI karar, bkz. deferred-triggers.)
     · adt_syntax_check: ters-tirnak sozdizimi bozmuyor -> valid:true.
     · run_all_validators: boyle bir kontrol yoktu.
     · push "[OK] Source uploaded" + activate "activationExecuted" -> ikisi de yesil.

  4. DOKUMAN DENENDI, YETMEDI. 2026-07-28'de SESSION_NOTES'a yazildi
     ("`.bdef` yorumunda ters-tirnak KULLANMA"). Ertesi gun ayni hata tekrarlandi.
     Dokuman katmaninin yetmedigi ISPATLI.

  5. KULLANICI ACIK ONAYI ALINDI (2026-07-29), artilar/eksiler analiziyle birlikte.

KAPSAM — BILINCLI OLARAK DAR:
  - YALNIZ `.bdef`. Ters-tirnagin bdef'te mesru kullanimi YOKTUR.
  - `.abap` KAPSAM DISI: ABAP'ta `` `metin` `` GECERLI bir string literal sozdizimidir;
    orada yasaklamak yanlis-pozitif uretir ve "guard'i atlatma" refleksi dogurur
    (saglik denetimi 2026-07-09: guard'in asil maliyeti gecikme degil, bu reflekstir).
  - `.cds` / `.srvd` KAPSAM DISI: ayni cogalmanin orada olup olmadigi OLCULMEDI.
    Olcmeden kapsama alinmaz (kanitsiz genisletme yok).

⚠ KOK SEBEP KESIN IZOLE EDILMEDI: cogaltmanin SAP tarafinda mi, bizim push/okuma
  yolumuzda mi oldugu kanitlanmadi. Sebep bizim aracimiz cikarsa DOGRU cozum bu gate
  DEGIL, aracin duzeltilmesidir ve bu gate EMEKLI EDILIR.
  -> `governance/deferred-triggers.md` "backtick kok-sebep izolasyonu".

Kullanim:
    python check_bdef_backtick.py [<path>] [--file <path>] [--strict]
Cikis: 0 temiz, 1 ihlal.
"""
# ENFORCES: BE-62  (ADR 0019 coverage binding)
import argparse
import io
import sys
from pathlib import Path
import sys as _pc_sys
from pathlib import Path as _pc_Path
_pc_sys.path.insert(0, str(_pc_Path(__file__).resolve().parents[1]))
from utils.project_config import SOURCE_ROOT_NAME, project_root  # K12
# K1 (2026-08-20): ORTAK kapsam sozlesmesi — 'ihlal yok' ile 'bakacak dosya yok'
# ayrilir. 0 dosya FAIL URETMEZ (mesru olabilir), ama SESSIZ de gecmez.
from utils.kapsam import Kapsam  # noqa: E402

KAPSAM = Kapsam('.bdef')   # K1: taranan dosya sayaci

if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BACKTICK = "`"


def tara(txt: str) -> list[tuple[int, int, str]]:
    """(satir_no, adet, satir_icerigi) — ters-tirnak iceren her satir."""
    hits = []
    for i, satir in enumerate(txt.splitlines(), 1):
        n = satir.count(BACKTICK)
        if n:
            hits.append((i, n, satir.strip()))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="taranacak dosya (run_review pozisyonel artifact)")
    ap.add_argument("--file")
    ap.add_argument("--strict", action="store_true",
                   help="(uyumluluk; NO-OP — şiddeti DEĞİŞTİRMEZ, run_all --strict kazara terfi ettirmesin; ADR 0019 §54)")
    args, _unknown = ap.parse_known_args()

    root = project_root()
    target = args.file or args.path
    if target:
        files = [Path(target)]
    else:
        # T1.9 (2026-07-31): rglob node_modules/dist'i de yürüyordu → prune'lu walk (23× hız).
        files = []
        import os as _os
        for _r, _ds, _fs in _os.walk(root / SOURCE_ROOT_NAME):
            _ds[:] = [d for d in _ds if d not in ("node_modules", ".git", "dist", "coverage")]
            files += [Path(_r) / f for f in _fs if f.lower().endswith(".bdef")]

    toplam = 0
    dosya_sayisi = 0
    for f in KAPSAM.say(files):
        # run_review artifact'i gecici dosya olabilir (.bdef uzantisi olmayabilir);
        # acik --file/path verildiyse uzanti filtreleme YAPMA, aksi halde sessizce atlar.
        if not target and f.suffix.lower() != ".bdef":
            continue
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        hits = tara(txt)
        if hits:
            dosya_sayisi += 1
        for ln, n, icerik in hits:
            toplam += n
            try:
                rel = f.relative_to(root)
            except ValueError:
                rel = f
            print(f"[İHLAL] {rel}:{ln}  ters-tırnak x{n}\n         → {icerik}")

    if toplam:
        print(
            f"\n{toplam} ters-tırnak / {dosya_sayisi} dosya — `.bdef`'te ters-tırnak (U+0060) "
            f"KULLANILMAZ.\nSAP kaydederken ÇOĞALTIYOR (ölçüm: repo 2 → canlı 8, her pull+push "
            f"turu ikiye katlıyor).\nSESSİZDİR: push '[OK]', aktivasyon temiz, adt_syntax_check "
            f"valid:true — fark ancak\nreadback BAYT kıyasında görülür. İki kez yaşandı "
            f"(2026-07-28 + 2026-07-29).\nÇözüm: yorumda ters-tırnak yerine düz metin ya da tek "
            f"tırnak kullan."
        )
        return 1

    print("bdef ters-tırnak: temiz." + KAPSAM.ek())
    return 0


if __name__ == "__main__":
    sys.exit(main())
