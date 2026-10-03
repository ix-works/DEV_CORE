#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bootstrap_modul_klasoru — `bootstrap_package` modül klasörü YOKKEN (yeni-proje akışı F1).

KUSUR (yeni-proje akışı denetimi 2026-10-03, F1): taze projede `SOURCE_CODES/` boştur;
`bootstrap_package.py ZSD001_CLC --module SD ...` geçerli modülde bile
"HATA: Modül klasörü ... yok" + exit 1 veriyordu ⇒ PROJECT_BOOTSTRAP STEP 6'yı izleyen
ilk denemede takılıyordu.

DÜZELTME: modül klasörü yoksa ve `--module` GECERLI_MODULLER'deyse script yaratır ve
`[ OK ] Modül klasörü yaratıldı` satırı basar. Liste dışı ad ⇒ hata, klasör YARATILMAZ.
⛔ DARALTMA YOK: VAR OLAN modül klasörü listeden bağımsız kabul edilir (M4 kontrol grubu).

VEKTÖRLER (GERÇEK `main()` + argparse, geçici ağaçta; gerçek projeye yazmaz):
  M1  SD, klasör yok                → rc 0, klasör+paket yaratıldı, `[ OK ] Modül klasörü` satırı
  M2  'XX' (liste dışı), klasör yok → rc 1, klasör YARATILMADI, hata liste dışı diyor
  M3  'sd' (küçük harf), klasör yok → M2 ile aynı (yazım hatası yeni ağaç açmaz)
  M4  KONTROL 'BC' liste dışı, klasör VAR → rc 0, paket yaratıldı, "yaratıldı" satırı YOK
  M5  KONTROL SD klasör VAR         → rc 0, "yaratıldı" satırı YOK
  M6  SD, klasör yok, şablon kökü YOK → rc 1, modül klasörü de YARATILMADI (yaratma en sonda)
  M7  kaynak kökü (`<source_root>`) YOK → rc 1, HİÇBİR ŞEY yaratılmaz (bug-gate #320 MEDIUM:
      yanlış cwd'den koşum kökü + iskeleti sessizce açıyordu; kök `init_project`'in işidir)
  M7b aynı koşumda hata metni KÖKÜ söyler (modül klasörü değil)

MUTASYON (bugünkü kaynaktan, bellekte; çapa tam 1 kez bulunmazsa exit 2):
  --mutasyon-liste-yok       liste denetimi kalkar (her ad yaratılır)   → M2, M3 düşer
  --mutasyon-mevcut-daralt   var olan klasörde de liste şartı           → M4 düşer
  --mutasyon-erken-yarat     modül klasörü şablon denetiminden ÖNCE     → M6 düşer
  --mutasyon-kok-yarat       kök denetimi kalkar + `parents=True`       → M7, M7b düşer
TABAN (eski kod): --kaynak <bootstrap_package.py>  → fadf091: M1, M2, M3, M7b düşer (M7 GEÇER —
  o kod kök yokken de exit 1'di, yalnız mesajı "modül klasörü yok"tu) · a025226: M7, M7b düşer

Çıkış: 0 beklendiği gibi · 1 sapma · 2 KURULAMADI
"""
from __future__ import annotations

import contextlib
import io
import os
import shutil
import stat
import sys
import tempfile
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[2]
BOOT = CORE / "scripts" / "bootstrap_package.py"
TPL_DIR = CORE / "templates" / "new-package"

GECERLI_KIP = ("--mutasyon-liste-yok", "--mutasyon-mevcut-daralt", "--mutasyon-erken-yarat",
               "--mutasyon-kok-yarat")
KIP: set[str] = set()
TABAN: Path | None = None
_a = sys.argv[1:]
while _a:
    x = _a.pop(0)
    if x == "--kaynak" and _a:
        TABAN = Path(_a.pop(0)).resolve()
    elif x in GECERLI_KIP:
        KIP.add(x)
    else:
        print(f"[DURDU] bilinmeyen arguman: {x!r} — gecerli: {list(GECERLI_KIP)} + --kaynak")
        sys.exit(2)

SONUC: list[tuple[str, bool]] = []
YARATILDI = "[ OK ] Modül klasörü yaratıldı"


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul)))
    print(f"  [{'OK' if kosul else 'FAIL'}] {ad}" + (f"  -- {detay}" if not kosul and detay else ""))


def _degistir(metin: str, eski: str, yeni: str, ad: str) -> str:
    n = metin.count(eski)
    if n != 1:
        print(f"[DURDU] KURULAMADI: {ad} capasi {n} kez bulundu (1 bekleniyordu): {eski[:70]!r}")
        sys.exit(2)
    return metin.replace(eski, yeni)


def kaynak_metni() -> str:
    if TABAN is not None:
        return TABAN.read_text(encoding="utf-8")
    m = BOOT.read_text(encoding="utf-8")
    if "--mutasyon-liste-yok" in KIP:
        m = _degistir(m, "    if modul_yarat and args.module not in GECERLI_MODULLER:\n",
                      "    if False:\n", "liste-yok")
    if "--mutasyon-mevcut-daralt" in KIP:
        m = _degistir(m, "    if modul_yarat and args.module not in GECERLI_MODULLER:\n",
                      "    if args.module not in GECERLI_MODULLER:\n", "mevcut-daralt")
    if "--mutasyon-erken-yarat" in KIP:
        m = _degistir(m, "    if pkg_dir.exists():\n        print(f\"HATA: {pkg_dir} zaten mevcut",
                      "    if modul_yarat:\n        module_dir.mkdir(parents=True)\n"
                      "        print('[ OK ] Modül klasörü yaratıldı (erken)')\n"
                      "        modul_yarat = False\n"
                      "    if pkg_dir.exists():\n        print(f\"HATA: {pkg_dir} zaten mevcut",
                      "erken-yarat")
    if "--mutasyon-kok-yarat" in KIP:
        m = _degistir(m, "    if not erp_root.is_dir():\n", "    if False:\n", "kok-yarat/denetim")
        m = _degistir(m, "        module_dir.mkdir(parents=False)", "        module_dir.mkdir(parents=True)",
                      "kok-yarat/parents")
    return m


def boot_yukle(src: str):
    """`__file__` DAİMA gerçek yol (modül `utils`'i parents[0]'dan import eder)."""
    mod = types.ModuleType("bootstrap_package_x")
    mod.__file__ = str(BOOT)
    exec(compile(src, str(BOOT), "exec"), mod.__dict__)
    return mod


def kos(boot, kok: Path, modul: str, *, modul_var: bool, sablon_var: bool = True,
        kok_var: bool = True) -> dict:
    kok.mkdir(parents=True)
    tdir = kok / "tpl"
    if sablon_var:
        shutil.copytree(TPL_DIR, tdir)
    kaynak = kok / "SRC"
    if kok_var:
        kaynak.mkdir()
    if modul_var:
        (kaynak / modul).mkdir()
    argv = ["bootstrap_package.py", "ZSD001_CLC", "--title", "Fixture", "--module", modul,
            "--templates-root", str(tdir), "--source-root", str(kaynak)]
    eski, sys.argv = sys.argv, argv
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = boot.main()
    finally:
        sys.argv = eski
    return {"rc": rc, "out": out.getvalue(), "err": err.getvalue(),
            "modul": (kaynak / modul).is_dir(),
            "paket": (kaynak / modul / "ZSD001_CLC" / ".rules.md").is_file(),
            "dizinler": sorted(p.name for p in kaynak.iterdir()) if kaynak.is_dir() else None,
            "kok": kaynak.exists()}


def _sil(d: Path) -> None:
    """Salt-okur öznitelikli kopyayı da siler (`templates/new-package` + `ref_docs` `R`
    özniteliği taşır, `copytree` onu kopyalar; çıplak `rmtree(ignore_errors)` WinError 5 ile
    %TEMP%'te `boot_modul_*` bırakıyordu). Desen: `ix_doctor_memory_git._sil`."""
    def _ac(func, path, _exc):  # noqa: ANN001
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass
    kw = {"onexc": _ac} if sys.version_info >= (3, 12) else {"onerror": _ac}
    try:
        shutil.rmtree(d, **kw)  # type: ignore[arg-type]
    except Exception:
        shutil.rmtree(d, ignore_errors=True)


def main() -> int:
    boot = boot_yukle(kaynak_metni())
    tmp = Path(tempfile.mkdtemp(prefix="boot_modul_"))
    try:
        s = kos(boot, tmp / "m1", "SD", modul_var=False)
        kontrol("M1 SD + klasör yok → rc 0, klasör+paket yaratıldı, [ OK ] satırı",
                s["rc"] == 0 and s["modul"] and s["paket"] and YARATILDI in s["out"],
                f"rc={s['rc']} modul={s['modul']} paket={s['paket']} err={s['err'][-160:]!r}")

        for ad, modul in (("M2 'XX' liste dışı", "XX"), ("M3 'sd' küçük harf", "sd")):
            s = kos(boot, tmp / modul.lower() / ad[:2], modul, modul_var=False)
            kontrol(f"{ad} + klasör yok → rc 1, klasör YARATILMADI, hata liste dışı diyor",
                    s["rc"] == 1 and s["dizinler"] == [] and "geçerli modül listesinde değil" in s["err"]
                    and "YARATILMADI" in s["err"],
                    f"rc={s['rc']} dizinler={s['dizinler']} err={s['err'][-160:]!r}")

        s = kos(boot, tmp / "m4", "BC", modul_var=True)
        kontrol("M4 KONTROL 'BC' liste dışı ama klasör VAR → rc 0, paket yaratıldı (daraltma yok)",
                s["rc"] == 0 and s["paket"] and YARATILDI not in s["out"],
                f"rc={s['rc']} paket={s['paket']} err={s['err'][-160:]!r}")

        s = kos(boot, tmp / "m5", "SD", modul_var=True)
        kontrol("M5 KONTROL SD klasör VAR → rc 0, 'yaratıldı' satırı YOK",
                s["rc"] == 0 and s["paket"] and YARATILDI not in s["out"],
                f"rc={s['rc']} out={s['out'][-160:]!r}")

        s = kos(boot, tmp / "m6", "SD", modul_var=False, sablon_var=False)
        kontrol("M6 SD + klasör yok + şablon kökü YOK → rc 1, modül klasörü YARATILMADI",
                s["rc"] == 1 and s["dizinler"] == [],
                f"rc={s['rc']} dizinler={s['dizinler']}")

        s = kos(boot, tmp / "m7", "SD", modul_var=False, kok_var=False)
        kontrol("M7 kaynak kökü YOK → rc 1, kök/modül/paket YARATILMADI",
                s["rc"] == 1 and not s["kok"], f"rc={s['rc']} kok={s['kok']}")
        kontrol("M7b kaynak kökü YOK → hata KÖKÜ söylüyor (modül değil) + 'YARATILMADI'",
                "Kaynak kökü" in s["err"] and "YARATILMADI" in s["err"], f"err={s['err'][-160:]!r}")
    finally:
        _sil(tmp)
        if tmp.exists():
            print(f"[UYARI] kum silinemedi: {tmp}")

    ok = sum(1 for _, k in SONUC if k)
    etiket = f" [TABAN {TABAN}]" if TABAN else (f" [{' '.join(sorted(KIP))}]" if KIP else "")
    print(f"\nbootstrap_modul_klasoru{etiket}: {ok}/{len(SONUC)} PASS")
    return 0 if ok == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
