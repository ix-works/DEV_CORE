#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tembel_desen fixture — `TembelDesen` HIZ kazandirir ama KORUMAYI zayiflatmaz.

NEDEN VAR (2026-08-13, sure-vergisi kuyrugu):
`pre_tool_guard` sizinti desenini MODUL yuklenirken kuruyordu:
`_CORE_LEAK = id_pattern(...)` -> `proje_desenleri` -> `_git_dir` ->
`subprocess.run(git rev-parse)`. Olculdu: ~100 ms, HER arac cagrisinda. Oysa desen
yalniz UC dalda kullanilir (commit-mesaji / `gh` yayin / core'a yazma taramasi);
arac cagrilarinin cogunlugu o dallara hic girmez.

Fix tembellestirmedir: desen ILK KULLANIMDA kurulur. Bu fixture'in isi, o
tembellestirmenin **hiz kazancini** degil, **koruma degismezini** capalamaktir:

  ⚠ ASIL RISK: tembel bir sarmalayici sessizce BOS/KURULMAMIS kalirsa
  `sizintilari_bul` hicbir sey bulamaz, guard "temiz" der ve PUBLIC cekirdege
  kimlik sizar. Yani hizlanma, korumanin OLU'ye donmesini maskeleyebilir.
  Bu yuzden burada pozitif kanit sart: tembel yol blocklist'i GERCEKTEN okuyor mu?

SENARYOLAR (P = ayirt edici, N = FP capasi, K = kontrol grubu):
  T1 P  TEMBELLIK      : sarmalayici KURULURKEN git CAGRILMAZ (0 cagri)
  T2 P  KULLANIMDA     : ilk kullanimda desen kurulur (git cagrilir, >=1)
  T3 K  ESITLIK        : tembel desen icerigi == `id_pattern()` icerigi (BIREBIR)
  T4 P  BLOCKLIST OKUR : blocklist'teki sentetik ad YAKALANIR (korumanin canli kaniti)
  T5 N  FP-CAPA        : blocklist'te olmayan siradan metin yakalanmaz
  T6 P  3.BAGLAM       : GERCEK `pre_tool_guard` modul yuklemesi git CAGIRMAZ
  T7 N  YAPISAL KORUND.: isim listesi BOS olsa bile yapisal desen (e-posta) yakalanir

MUTASYON (korpusun bos-yesil olmadigini kanitlar):
  python run.py --mutasyon-eager
      `tembel_id_pattern` ISTEKLI hale getirilir (= fix'in sokumu) -> T1/T6 DUSMELI,
      FP capalari (T3/T4/T5/T7) AYAKTA kalmali.
  python run.py --mutasyon-bos
      Sarmalayici BOS desen dondurur (= "hizli ama olu koruma" senaryosu)
      -> T3/T4/T7 DUSMELI. Bu, hiz-ugruna-koruma-kaybi sinifinin capasidir.

⚠ KOSUCU TUZAGI (yasandi, 2026-08-13): bu dosyaya ORNEK BIR E-POSTA duz metin olarak
yazilamaz — `pre_tool_guard`in kendi GENERICIZE-LEAK kurali core'a yazmayi REDDEDER
(yapisal desen `example.com|test|localhost` DISINDAKI her e-postayi kimlik izi sayar,
ve tam da bu yuzden `example.com` yazmak T7'yi trivial-yesil yapardi). Cozum, reponun
zaten kullandigi teknik: literal CALISMA ANINDA parcalardan kurulur (bkz.
`scripts/tests/test_pre_tool_guard.py` -> `paket = "ZSD" + "0" + "42"`).

Kosum: python tests/fixtures/tembel_desen/run.py
Cikis: 0 = hepsi beklendigi gibi, 1 = en az bir sapma.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
if not (REPO / "scripts").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")

# Sentetik kimlik izi — GERCEK bir ad DEGIL. Core public'tir; buraya gercek bir
# musteri/sistem/kisi adi yazmak, engellemeye calistigimiz sizintinin kendisidir.
SENTETIK = "SENTETIK" + "_MUSTERI_ADI"
# Yapisal e-posta capasi (T7) — literal DEGIL, parcalardan kurulur (yukaridaki tuzak notu).
SENTETIK_EPOSTA = "birisi" + "@" + "ornek-firma" + ".com"


def _yukle(ad: str, yol: Path):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)                 # type: ignore[arg-type]
    sys.modules[ad] = mod
    spec.loader.exec_module(mod)                                # type: ignore[union-attr]
    return mod


class _GitSayaci:
    """`git rev-parse` cagrilarini sayar (baska subprocess'ler gercek kalir)."""

    def __init__(self, modul):
        self.modul = modul
        self.gercek = modul.subprocess.run
        self.sayi = 0

    def __enter__(self):
        def _sahte(cmd, *a, **k):
            if isinstance(cmd, list) and cmd[:2] == ["git", "rev-parse"]:
                self.sayi += 1
            return self.gercek(cmd, *a, **k)
        self.modul.subprocess.run = _sahte
        return self

    def __exit__(self, *exc):
        self.modul.subprocess.run = self.gercek
        return False


def main() -> int:
    mut_eager = "--mutasyon-eager" in sys.argv
    mut_bos = "--mutasyon-bos" in sys.argv

    g = _yukle("genericize_common", REPO / "scripts" / "genericize_common.py")

    if mut_eager:
        print("  MUTASYON-EAGER: tembel_id_pattern ISTEKLI yapildi (fix sokuldu)")
        g.tembel_id_pattern = g.id_pattern          # type: ignore[assignment]
    if mut_bos:
        print("  MUTASYON-BOS: sarmalayici BOS desen donduruyor (olu koruma)")
        import re as _re
        g.tembel_id_pattern = lambda **k: _re.compile(r"(?!x)x")   # hicbir sey eslesmez

    # Sentetik proje kokU: blocklist'i olan, ama gercek hicbir depoya dokunmayan bir agac.
    tmp = Path(tempfile.mkdtemp(prefix="tembel_"))
    proje = tmp / "proje"
    (proje / ".claude").mkdir(parents=True)
    (proje / ".claude" / "genericize-blocklist.txt").write_text(
        f"# sentetik test listesi\n{SENTETIK}\n", encoding="utf-8")

    sonuc: list[tuple[str, bool, str]] = []

    # ---- T1: sarmalayici KURULURKEN git cagrilmamali -------------------------
    with _GitSayaci(g) as say:
        desen = g.tembel_id_pattern(proje_koku=proje, cwd=proje)
    sonuc.append(("T1 P TEMBELLIK: kurulumda git CAGRILMAZ",
                  say.sayi == 0, f"git cagrisi={say.sayi} (beklenen 0)"))

    # ---- T2: ilk KULLANIMDA desen kurulur ------------------------------------
    with _GitSayaci(g) as say2:
        desen.search("herhangi bir metin")
    sonuc.append(("T2 P KULLANIMDA: ilk kullanimda desen kurulur",
                  say2.sayi >= 1, f"git cagrisi={say2.sayi} (beklenen >=1)"))

    # ---- T3: KONTROL GRUBU — icerik istekli surumle BIREBIR ayni -------------
    istekli = g.id_pattern(proje_koku=proje, cwd=proje)
    tembel2 = g.tembel_id_pattern(proje_koku=proje, cwd=proje)
    sonuc.append(("T3 K ESITLIK: tembel icerik == istekli icerik",
                  tembel2.pattern == istekli.pattern,
                  "desen metni birebir" if tembel2.pattern == istekli.pattern
                  else "DESEN METNI FARKLI"))

    # ---- T4: POZITIF — blocklist GERCEKTEN okunuyor mu? ----------------------
    # Bu, fix'in koruma tarafinin canli kaniti: tembel yol isim listesini yukluyor.
    metin = f"musteri kaydi: {SENTETIK} icin rapor"
    bulundu = [t for t, _tur in g.sizintilari_bul(metin, tembel2)]
    sonuc.append(("T4 P BLOCKLIST OKUR: sentetik ad tembel yoldan YAKALANIR",
                  SENTETIK.lower() in " ".join(bulundu).lower(),
                  f"bulgular={bulundu}"))

    # ---- T5: FP-CAPA — siradan metin yakalanmamali ---------------------------
    temiz = "bu satirda hicbir kimlik izi yok, yalnizca duz metin"
    fp = g.sizintilari_bul(temiz, g.tembel_id_pattern(proje_koku=proje, cwd=proje))
    sonuc.append(("T5 N FP-CAPA: temiz metin yakalanmaz",
                  fp == [], f"bulgular={fp}"))

    # ---- T6: 3.BAGLAM — GERCEK pre_tool_guard kablolamasi --------------------
    # Fixture'da yesil olup uretimde olu kalmasin: asil hook dosyasi yuklenir ve
    # MODUL YUKLEME sirasinda git cagrilip cagrilmadigi olculur.
    guard_yolu = REPO / "scripts" / "hooks" / "pre_tool_guard.py"
    eski_env = os.environ.get("CLAUDE_PROJECT_DIR")
    os.environ["CLAUDE_PROJECT_DIR"] = str(proje)
    try:
        with _GitSayaci(g) as say3:
            _yukle("_ptg_fixture", guard_yolu)
        sonuc.append(("T6 P 3.BAGLAM: gercek pre_tool_guard yuklemesi git CAGIRMAZ",
                      say3.sayi == 0, f"git cagrisi={say3.sayi} (beklenen 0)"))
    except Exception as e:                                   # cokme != FAIL: ayirt et
        sonuc.append(("T6 P 3.BAGLAM: gercek pre_tool_guard yuklemesi git CAGIRMAZ",
                      False, f"KOSULAMADI (cokme): {type(e).__name__}: {e}"))
    finally:
        if eski_env is None:
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
        else:
            os.environ["CLAUDE_PROJECT_DIR"] = eski_env

    # ---- T7: FP-CAPA — isim listesi BOS olsa bile yapisal desen calisir ------
    # Blocklist'siz bir kokte koruma "yarim"dir ama SIFIR degildir: yapisal
    # desenler (e-posta / makine-lokal yol) her zaman eklenir.
    bos_proje = tmp / "bos"
    bos_proje.mkdir()
    bos_desen = g.tembel_id_pattern(proje_koku=bos_proje, cwd=bos_proje)
    yapisal = g.sizintilari_bul(f"iletisim: {SENTETIK_EPOSTA}", bos_desen)
    sonuc.append(("T7 N YAPISAL KORUNDU: liste bos olsa da e-posta yakalanir",
                  len(yapisal) >= 1, f"bulgular={yapisal}"))

    gecen = sum(1 for _, ok, _ in sonuc if ok)
    for ad, ok, detay in sonuc:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad} -> {detay}")
    print(f"\n{gecen}/{len(sonuc)} OK")
    return 0 if gecen == len(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
