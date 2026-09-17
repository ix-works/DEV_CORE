#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Z-OBJE DESEN KAPSAMI korpusu (Q326 / D7, 2026-09-18).

NEDEN BU KORPUS VAR
-------------------
`genericize_common.Z_OBJ_PAT` public cekirdege Z obje adi sizmasini onleyen kapinin
yapisal ayagidir. Desen `Z[A-Z]{2}\\d{3}` idi — yani YALNIZ 2 harfli modul kodu.
SAP modul/uygulama kisaltmasi 2 harfle sinirli DEGILDIR (iki harfliler var ama uc ve
dort harfliler de var) => 3-4 harfli her Z adi kapidan GORUNMEDEN geciyordu.

KONTROL GRUBU (kusurun "kapsam" oldugunu, "mekanizma" olmadigini kanitlar):
  ayni kapi, ayni cagri yolu -> 2 harfli ad YAKALANIYORDU, 4 harfli ad YAKALANMIYORDU.

SINIF TEKRARI: bu desen UCUNCU kez genisliyor (D3 alt-cizgi siniri · D4 yalniz-tek-modul
kapsami · D7 yalniz-2-harf). Ortak ders: desen, yazildigi gun karsilastigi kumeye gore
daraltiliyor. Korpus bu yuzden TEK vakayi degil SINIFI civiliyor: "3 ve 4 harfli modul
kodu gorulur" + "allowlist'e alinan her ad GERCEKTEN desene uymali".

⛔ ALLOWLIST'IN OLCUTU (K bolumu): `ORNEK_Z`'ye bir ad koymak, o ad icin kapiyi KALICI
olarak kapatmaktir. Bu yuzden allowlist yalnizca GERCEK bir projeye ait OLMAYAN jenerik
yer-tutuculari tasiyabilir. Q326 kaydi 4 harfli bir adi "jenerik" sayiyordu; olcum
curuttu (gercek bir musteri paketiydi). K2 bu karari civiler — o ad allowlist'e sessizce
geri eklenirse bu korpus duser.

⚠ ORNEK ADLAR LITERAL YAZILMAZ: bu dosya da genericize kapisi tarafindan taranir; desene
uyan ve allowlist'te olmayan bir ad burada duz yazilirsa KENDI commit'imiz bloklanir
(AV-03 kosucusunun ayni dersi). Adlar `_z()` ile parca parca kurulur.

KOSUM:  python tests/fixtures/z_obje_desen_kapsami/run.py [--mutasyon-<kip>]
Cikis:  0 hepsi beklendigi gibi · 1 sapma · 2 DOGRULANAMADI (capa tutmadi / mutant bozuk)

MUTASYON (korpusun bos-yesil olmadigini kanitlar):
  --mutasyon-dar-desen      desen `{2,4}` -> `{2}` (D7 oncesi hal); A/W bolumu DUSMELI
  --mutasyon-zewm-allowlist gercek 4 harfli ad allowlist'e sokulur; K/W bolumu DUSMELI
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
SCRIPTS = REPO / "scripts"


def _z(modul: str, no: str) -> str:
    """Z obje adini PARCADAN kurar (yukaridaki ⚠ notu)."""
    return "Z" + modul + no


Z_GERCEK_4 = _z("EWM", "000")   # 4 harfli — gercek bir proje paketi; YAKALANMALI
Z_GERCEK_3 = _z("CRM", "007")   # 3 harfli sentetik;                 YAKALANMALI
Z_GERCEK_2 = _z("XY", "022")    # 2 harfli (D4 ekseni) — bozulmamali; YAKALANMALI
Z_JENERIK = _z("MOD", "001")    # allowlist (D7 ile eklendi)  -> sessiz
Z_DEMO = _z("SD", "001")        # allowlist (eski demo)       -> sessiz

# kip -> (eski, yeni) — YALNIZ sandbox kopyasina uygulanir
MUTLAR = {
    "--mutasyon-dar-desen": (r"Z[A-Z]{2,4}\d{3}", r"Z[A-Z]{2}\d{3}"),
    "--mutasyon-zewm-allowlist": ('    "ZMOD001",',
                                  '    "Z" "EWM" "000",\n    "ZMOD001",'),
}

SONUC: list[tuple[str, bool, str]] = []


def ekle(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(ok), detay))


def _sil(d: Path) -> None:
    """Q319: Windows'ta salt-okur girdi `rmtree(ignore_errors=True)` ile SESSIZCE kalir."""
    def _ac(func, path, _exc):                       # noqa: ANN001
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass
    kw = {"onexc": _ac} if sys.version_info >= (3, 12) else {"onerror": _ac}
    try:
        shutil.rmtree(d, **kw)                       # type: ignore[arg-type]
    except Exception:
        shutil.rmtree(d, ignore_errors=True)


def _yukle(yol: Path):
    """Sandbox kopyasini AYRI modul adiyla yukle — gercek `genericize_common`
    `sys.modules`'ta kalirsa mutant hic olculmezdi (sahte-YESIL sinifi)."""
    ad = "gc_sandbox_kopya"
    sys.modules.pop(ad, None)
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    spec.loader.exec_module(m)
    return m


def main() -> int:
    gecerli = set(MUTLAR)
    for a in sys.argv[1:]:
        if a.startswith("--mutasyon") and a not in gecerli:
            raise SystemExit(f"[KULLANIM] bilinmeyen mutasyon kipi: {a} -> gecerli: "
                             + " ".join(sorted(gecerli)))
    secili = next((a for a in sys.argv[1:] if a in gecerli), None)

    tmp = Path(tempfile.mkdtemp(prefix="z_desen_"))
    try:
        core = tmp / "core"
        (core / "scripts" / "git-hooks").mkdir(parents=True)
        shutil.copy2(SCRIPTS / "genericize_common.py", core / "scripts")
        shutil.copy2(SCRIPTS / "git-hooks" / "core_precommit.py",
                     core / "scripts" / "git-hooks")
        hedef = core / "scripts" / "genericize_common.py"

        if secili:
            eski, yeni = MUTLAR[secili]
            kaynak = hedef.read_text(encoding="utf-8")
            if eski not in kaynak:
                print(f"[DOGRULANAMADI] mutasyon capasi bulunamadi ({secili}) -> "
                      "mutasyon UYGULANMADI; 'gecti' sonucu ANLAMSIZ olurdu.")
                return 2
            hedef.write_text(kaynak.replace(eski, yeni, 1), encoding="utf-8")
            try:
                compile(hedef.read_text(encoding="utf-8"), str(hedef), "exec")
            except SyntaxError as e:
                print(f"[DOGRULANAMADI] mutant SOZDIZIMI BOZUK ({secili}): {e}")
                return 2

        G = _yukle(hedef)

        # ── A: DESEN KAPSAMI (birim) ───────────────────────────────────────────
        ekle("A1 4 harfli modul kodu YAKALANIR (D7 ekseni)",
             G.z_obje_sizintilari(Z_GERCEK_4) == [Z_GERCEK_4],
             f"bulunan={G.z_obje_sizintilari(Z_GERCEK_4)}")
        ekle("A2 3 harfli modul kodu YAKALANIR",
             G.z_obje_sizintilari(Z_GERCEK_3) == [Z_GERCEK_3],
             f"bulunan={G.z_obje_sizintilari(Z_GERCEK_3)}")
        ekle("A3 2 harfli eksen BOZULMADI (D4 gerilemesi yok)",
             G.z_obje_sizintilari(Z_GERCEK_2) == [Z_GERCEK_2],
             f"bulunan={G.z_obje_sizintilari(Z_GERCEK_2)}")
        ekle("A4 alt-cizgiye bitisik ad YAKALANIR (D3 gerilemesi yok)",
             G.z_obje_sizintilari("project_" + Z_GERCEK_4.lower()) != [],
             f"bulunan={G.z_obje_sizintilari('project_' + Z_GERCEK_4.lower())}")
        ekle("A5 kucuk harf de YAKALANIR (IGNORECASE / D2)",
             G.z_obje_sizintilari(Z_GERCEK_4.lower() + "_cl_item") != [])

        # NEGATIF eksen: desen genisledi diye SINIRLAR gevsemedi mi
        ekle("N1 allowlist'teki jenerik ad SESSIZ (yeni)",
             G.z_obje_sizintilari(Z_JENERIK) == [], f"bulunan={G.z_obje_sizintilari(Z_JENERIK)}")
        ekle("N2 allowlist'teki eski demo SESSIZ (gerileme yok)",
             G.z_obje_sizintilari(Z_DEMO) == [])
        ekle("N3 5 harfli govde ESLESMEZ (ust sinir korunur)",
             G.z_obje_sizintilari(_z("ABCDE", "123")) == [])
        ekle("N4 2 haneli rakam ESLESMEZ (alt sinir korunur)",
             G.z_obje_sizintilari(_z("XY", "01")) == [])
        ekle("N5 4 haneli rakam ESLESMEZ (`(?!\\d)` korunur)",
             G.z_obje_sizintilari(Z_GERCEK_2 + "1") == [])

        # ── K: ALLOWLIST OLCUTU (kapinin KENDI sozlesmesi) ─────────────────────
        # Bu bolum deseni degil, allowlist'in ANLAMINI olcer: allowlist'e konan her ad
        # desene uymalidir, yoksa o satir OLU'dur (kimseyi muaf tutmaz ama "muaf
        # tuttuk" sanilir — erisilemez-yesil sinifi).
        olu = sorted(a for a in G.ORNEK_Z if not G.Z_OBJ_PAT.fullmatch(a))
        ekle("K1 ORNEK_Z'deki her ad desene UYAR (olu allowlist satiri yok)",
             not olu, f"desene uymayan={olu}")
        ekle("K2 GERCEK proje paketi allowlist'te DEGIL (Q326 karari)",
             Z_GERCEK_4 not in {a.upper() for a in G.ORNEK_Z},
             "allowlist'e gercek bir obje adi girerse kapi o ad icin KALICI kapanir")
        ekle("K3 allowlist muafiyeti desen genislemesinden BAGIMSIZ calisir",
             all(G.z_obje_sizintilari(a) == [] for a in G.ORNEK_Z),
             f"sizan={[a for a in G.ORNEK_Z if G.z_obje_sizintilari(a)]}")

        # ── W: KABLOLAMA — GERCEK GIRIS NOKTASI (kod != kablolama) ─────────────
        # Desenin dogru olmasi yetmez: kapinin onu CAGIRDIGI kanitlanmali.
        # `core_precommit` GERCEK bir git deposunda, GERCEK staged yolda kosturulur.
        # (3. BAGLAM: bu, birim cagrisindan da fixture kabugundan da ayri bir evdir —
        #  ayri surec, ayri cwd, ayri git deposu, gercek index okumasi.)
        proje = tmp / "repo"
        (proje / "docs").mkdir(parents=True)
        (proje / "scripts" / "git-hooks").mkdir(parents=True)
        shutil.copy2(hedef, proje / "scripts")
        shutil.copy2(core / "scripts" / "git-hooks" / "core_precommit.py",
                     proje / "scripts" / "git-hooks")
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        # Blocklist'i SABITLE: bos liste fail-closed dalini acar ve olcum deseni degil
        # listenin YOKLUGUNU olcerdi. Sentinel gercek bir kimlik DEGILDIR.
        env["IX_GENERICIZE_BLOCKLIST"] = "SENTINEL" + "-ISIM"

        def git(*a):
            return subprocess.run(["git", "-C", str(proje), *a], capture_output=True,
                                  text=True, encoding="utf-8", errors="replace")

        git("init", "-q")
        git("config", "user.email", "fixture@example.com")
        git("config", "user.name", "fixture")

        def precommit(dosya_adi: str, icerik: str):
            p = proje / "docs" / dosya_adi
            p.write_text(icerik, encoding="utf-8")
            git("add", "docs/" + dosya_adi)
            r = subprocess.run(
                [sys.executable, str(proje / "scripts" / "git-hooks" / "core_precommit.py")],
                cwd=str(proje), env=env, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=180)
            git("rm", "-q", "--cached", "docs/" + dosya_adi)
            p.unlink(missing_ok=True)
            return r.returncode, (r.stdout or "") + (r.stderr or "")

        rc_k, out_k = precommit("temiz.md", "# not\n\nornek: " + Z_JENERIK + "\n")
        ekle("W0 KONTROL GRUBU: jenerik ad tasiyan dosya commit'i BLOKLAMAZ",
             rc_k == 0, f"rc={rc_k} cikti={out_k[-500:]!r}")

        rc_s, out_s = precommit("sizinti.md", "# not\n\nvaka: " + Z_GERCEK_4 + "_CL_X\n")
        ekle("W1 4 harfli Z adi GERCEK kapida BLOKLANIR (exit 1)",
             rc_s == 1, f"rc={rc_s} cikti={out_s[-500:]!r}")
        ekle("W2 imza dogru: bulgu 'Z-obje' turunde ve dogru token",
             "GENERICIZE-LEAK" in out_s and Z_GERCEK_4 in out_s and "Z-obje" in out_s,
             f"cikti={out_s[-500:]!r}")
    finally:
        _sil(tmp)

    gecen = sum(1 for _, ok, _ in SONUC if ok)
    print(f"\n=== Z-OBJE DESEN KAPSAMI (Q326/D7) "
          f"{'[' + secili + ']' if secili else '[taban]'} ===")
    for ad, ok, detay in SONUC:
        print(f"  [{'OK ' if ok else 'FAIL'}] {ad}" + (f"   -> {detay}" if not ok else ""))
    print(f"\n{gecen}/{len(SONUC)} OK")
    if secili:
        print(f"  (MUTASYON {secili} — dusmesi BEKLENEN vektorler var; "
              "tam skor 'mutasyon KACTI' demektir)")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
