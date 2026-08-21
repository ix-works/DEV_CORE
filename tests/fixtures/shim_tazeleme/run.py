#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HOOK_SHIM TAZELEME YOLU (team_setup.shim_tazele) — 2026-08-22, N7.

NEDEN BU KORPUS VAR
-------------------
KILITLENME (olculmus): prosedur *"META-INFRA (hook_shim) = yalniz LIDER"* der;
`infra_write_guard` ise *"muaf yalniz infra-expert"* der ⇒ **kesisim BOS, kimse mesru
yazamiyordu.** `team_setup.dosya_tamamla` idempotenttir ve mevcut dosyayi EZMEZ ⇒
suruklenen bir shim'i tazeleyecek ONAYLI yol YOKTU. Kullanici karari: **"arac yazsin,
rol degil"** ⇒ `--tazele-shim` bayragi.

⛔ KORPUSUN ASIL ISI IKI DEGISMEZI CIVILEMEK (biri otekini KAPSAMAZ):
  (a) **VARSAYILAN DEGISMEDI** — bayraksiz kosumda mevcut shim EZILMEZ. Bu yolun
      sessizce "farkliysa ez"e donmesi, kurulumun rutin bir adimini ezme aracina
      cevirirdi (kardes ders: `claude_overlay` kapisi, elle duzeltmeyi sessizce ezme).
  (b) **TERS YON GORUNUR** — proje kopyasi sablondan ILERIDE olabilir. Tam bu yasandi
      (2026-08-22): `infra_write_guard` projedeki shim'de kabloluydu, SABLONDA YOKTU ⇒
      korlemesine tazeleme AKTIF BIR KORUMAYI sessizce fail-open yapardi.
      Bu yuzden tazeleme FARKI EKRANA BASMADAN yapilmaz.

⛔ IZOLASYON: mutasyon GERCEK kaynaga YAZILMAZ — kardes `_mutant_team_setup.py`
dosyasinda yasar (CORE_ROOT ayni cozulsun diye ayni dizinde). Gercek agaca yazan
mutasyon komsu korpuslari kirletir (bu evde olculmus sinif).

KOSUM:  python tests/fixtures/shim_tazeleme/run.py
        ... --mutasyon-varsayilan-ez   ((a) sokumu: dosya_tamamla farkliysa EZER)
        ... --mutasyon-fark-sessiz     (fark raporu basilmadan tazelenir)
        ... --mutasyon-ters-yon-kor    ((b) sokumu: proje ILERIDE uyarisi susar)
        ... --mutasyon-dogrulama-yok   (tazeleme sonrasi SHA esitligi DOGRULANMAZ)
Cikis:  0 hepsi beklendigi gibi · 1 sapma · 2 DOGRULANAMADI (mutasyon capasi tutmadi)
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
ARAC = REPO / "scripts" / "team_setup.py"
SABLON = REPO / "claude" / "hook_shim.template.py"

# --- mutasyon capalari (ICERIK capasi; taban SHA DEGIL) ----------------------
CAPA_VARSAYILAN = """    for hedef, kaynak in hedefler:
        if hedef.exists():
            say(OK, f"mevcut: {hedef.name} (drift denetimi: session_start D7)")"""
CAPA_FARK = """    for satir in fark:
        print("  " + satir.rstrip("\\n"))"""
CAPA_TERS = "    if proje_ozel:\n"
# ⚠ RAPORLAMA sozlesmesinin capasi (asagidaki SINIR notuna bak).
CAPA_DOGRULAMA = ('    say(OK, f"hook_shim.py TAZELENDİ — doğrulandı: '
                  'sonuç sha256 == şablon sha256 "')

MUTLAR = {
    # (a) SOKUMU: varsayilan yol "farkliysa EZ"e doner -> V1 duser
    "--mutasyon-varsayilan-ez": (
        CAPA_VARSAYILAN,
        """    for hedef, kaynak in hedefler:
        if hedef.exists():
            shutil.copyfile(kaynak, hedef)
            say(OK, f"mevcut: {hedef.name} (drift denetimi: session_start D7)")"""),
    # "once FARKI goster" sozlesmesinin sokumu -> V6 duser
    "--mutasyon-fark-sessiz": (CAPA_FARK, "    pass"),
    # (b) SOKUMU: ters-yon uyarisi susar -> V3 duser
    "--mutasyon-ters-yon-kor": (CAPA_TERS, "    if False:  # MUTASYON\n"),
    # RAPORLAMA sokumu: sonuc sha'siz duyurulur -> V2b duser
    "--mutasyon-dogrulama-yok": (
        CAPA_DOGRULAMA, '    say(OK, f"hook_shim.py TAZELENDİ. "'),
}

# ⚠⚠ OLCUM SINIRI — DURUSTLUK KAYDI (silme):
# `shim_tazele` icindeki `if sonraki_sha != sablon_sha:` FAIL-CLOSED dali bu korpusta
# DOGRULANAMAZ: `shutil.copyfile` basarili olduktan sonra hedefin sablondan FARKLI
# olacagi bir senaryo fixture icinde uretilemiyor (bozuk-yazma simule edilemedi).
# Bu yuzden `--mutasyon-dogrulama-yok` o DALI degil, RAPORLAMA sozlesmesini civiller
# ("sonucu SHA ile duyur"). ⛔ Bunu "dogrulama test edildi" diye OKUMA -- olculen sey
# duyurudur; fail-closed dalin kendisi ACIK KALEMDIR.

# Proje kopyasini SABLONDAN AYIRAN, gercek vakayi taklit eden satir.
# ⛔ BAYT olarak calisilir: `read_text`/`write_text` yuvarlagi Windows'ta satir sonlarini
# CEVIRIR ("\n" -> "\r\n") ve "birebir ayni kopya" vektoru SAHTE-KIRMIZI verir --
# olculdu: V4 tam bu yuzden dustu, ARAC dogruydu. Fixture'in KENDI kurulumu olcumu
# bozmamali (bu evde olculmus sinif: sahte-KIRMIZI da bir olcum hatasidir).
PROJE_OZEL_SATIR = b"# PROJE-OZEL: infra_write_guard kablolamasi (sablonda YOK)\n"


def _sha(y: Path) -> str:
    return hashlib.sha256(y.read_bytes()).hexdigest()


def kur(kok: Path, govde: bytes | None) -> Path:
    """Sahte proje: <kok>/scripts/hook_shim.py (govde None ise dosya YOK). BAYT yazar."""
    (kok / "scripts").mkdir(parents=True, exist_ok=True)
    (kok / ".claude").mkdir(parents=True, exist_ok=True)
    hedef = kok / "scripts" / "hook_shim.py"
    if govde is not None:
        hedef.write_bytes(govde)
    return hedef


def kos_bayrakli(arac: Path, proje: Path) -> tuple[int, str]:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, str(arac), "--tazele-shim",
                        "--project", str(proje)], capture_output=True, env=env, timeout=180)
    return p.returncode, (p.stdout.decode("utf-8", "replace")
                          + p.stderr.decode("utf-8", "replace"))


def kos_varsayilan(arac: Path, proje: Path) -> tuple[int, str]:
    """BAYRAKSIZ yol: yalniz `dosya_tamamla` (kurulumun geri kalani kosturulmaz)."""
    src = ("import sys, runpy, pathlib\n"
           "sys.argv = ['team_setup.py']\n"
           "m = runpy.run_path(r'%s')\n"
           "m['dosya_tamamla'](pathlib.Path(r'%s'))\n" % (arac, proje))
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, "-c", src], capture_output=True, env=env, timeout=180)
    return p.returncode, (p.stdout.decode("utf-8", "replace")
                          + p.stderr.decode("utf-8", "replace"))


def main() -> int:
    # BILINMEYEN KIP SESSIZCE YESIL GECMESIN: yazim hatasi HIC mutasyon kurmadan
    # TAM PUAN uretirdi ve "mutasyon yakalandi" sanilirdi.
    for a in sys.argv[1:]:
        if a.startswith("--mutasyon") and a not in MUTLAR:
            raise SystemExit(f"[KULLANIM] bilinmeyen mutasyon kipi: {a} -> gecerli: "
                             + ", ".join(sorted(MUTLAR)))

    secili = [a for a in sys.argv[1:] if a in MUTLAR]
    arac, mutant = ARAC, None
    if secili:
        ham = ARAC.read_text(encoding="utf-8")
        eski, yeni = MUTLAR[secili[0]]
        if eski not in ham:
            print(f"[DOGRULANAMADI] mutasyon capasi tabanda bulunamadi ({secili[0]}) -> "
                  "mutasyon uygulanmadi; 'gecti' sonucu ANLAMSIZ olurdu.")
            return 2
        # KARDES dosya: CORE_ROOT = parents[1] oldugu icin ayni dizinde yasamali.
        arac = ARAC.with_name("_mutant_team_setup.py")
        arac.write_text(ham.replace(eski, yeni, 1), encoding="utf-8")
        mutant = arac

    tmp = Path(tempfile.mkdtemp(prefix="shim_tazele_"))
    sonuc: list[tuple[str, bool, str]] = []

    def ekle(ad, kosul, aciklama=""):
        sonuc.append((ad, bool(kosul), aciklama))

    try:
        sablon_govde = SABLON.read_bytes()
        sablon_sha = _sha(SABLON)

        # === V1 ⭐ KONTROL GRUBU — BAYRAKSIZ kosum BUGUNKUYLE AYNI =============
        # ⛔ SILINEMEZ: bu korpusun tamami "yeni bir ezme yolu" ekliyor; varsayilanin
        # DEGISMEDIGINI kanitlayan TEK vektor budur.
        kok = tmp / "v1"
        surukleneN = sablon_govde + PROJE_OZEL_SATIR
        hedef = kur(kok, surukleneN)
        once = _sha(hedef)
        rc, out = kos_varsayilan(arac, kok)
        ekle("V1 BAYRAKSIZ kosum mevcut shim'i EZMEZ (varsayilan DEGISMEDI)",
             rc == 0 and _sha(hedef) == once and "mevcut: hook_shim.py" in out,
             f"exit={rc}; sha degisti mi={_sha(hedef) != once}")

        # === V2 BAYRAKLI — fark basar + tazeler ==============================
        kok = tmp / "v2"
        hedef = kur(kok, sablon_govde.replace(b"import runpy",
                                              b"import runpy  # SURUKLENDI", 1))
        rc, out = kos_bayrakli(arac, kok)
        ekle("V2 --tazele-shim: FARK RAPORU basar + tazeler",
             rc == 0 and "FARK RAPORU" in out and _sha(hedef) == sablon_sha,
             f"exit={rc}; sonuc==sablon mi={_sha(hedef) == sablon_sha}")
        # ⚠ Bu vektor RAPORLAMA sozlesmesini olcer (yukaridaki OLCUM SINIRI notu):
        # sonuc, GERCEK on-disk sha ile duyurulmali -- "tazeledim" demek yetmez.
        ekle("V2b sonuc SHA ile DUYURULUR (gercek on-disk sha ile ayni)",
             "sonuç sha256 == şablon sha256" in out and _sha(hedef)[:12] in out,
             "'tazeledim' demek yetmez; sonuc SAYIYLA duyurulmali")
        ekle("V2c fark raporu HER IKI sha256'yi da basar",
             "şablon sha256" in out and "proje   sha256" in out, "")

        # === V3 ⭐ TERS YON — proje ILERIDE (olculmus vakanin sekli) ===========
        # `infra_write_guard` projede kablolu, sablonda YOK: korlemesine tazeleme
        # AKTIF korumayi sessizce fail-open yapar.
        kok = tmp / "v3"
        hedef = kur(kok, sablon_govde + PROJE_OZEL_SATIR)
        rc, out = kos_bayrakli(arac, kok)
        ekle("V3 TERS YON: proje ILERIDE -> gurultulu uyari + satir sayisi",
             rc == 0 and "TERS YÖN" in out and "1 satır YALNIZ projede" in out,
             f"exit={rc}")
        yedekler = list((kok / "scripts").glob("hook_shim.py.yedek-*"))
        ekle("V3b TERS YONDE YEDEK alinir (tazeleme GERI ALINABILIR)",
             len(yedekler) == 1
             and PROJE_OZEL_SATIR in yedekler[0].read_bytes(),
             f"yedek sayisi={len(yedekler)}")

        # === V4 ZATEN AYNI -> DOKUNULMAZ ====================================
        kok = tmp / "v4"
        hedef = kur(kok, sablon_govde)
        rc, out = kos_bayrakli(arac, kok)
        ekle("V4 kopya zaten sablonla AYNI -> dosyaya DOKUNULMAZ, yedek YOK",
             rc == 0 and "tazeleme gereksiz" in out
             and not list((kok / "scripts").glob("hook_shim.py.yedek-*")),
             f"exit={rc}")

        # === V5 KOPYA YOK -> uretim yoluna yonlendirir (sessiz basari DEGIL) ==
        kok = tmp / "v5"
        kur(kok, None)
        rc, out = kos_bayrakli(arac, kok)
        ekle("V5 tazelenecek kopya YOK -> WARN + uretim yoluna yonlendirir, exit 1",
             rc == 1 and "YOK" in out and not (kok / "scripts" / "hook_shim.py").exists(),
             f"exit={rc}; tazeleme YOKTAN dosya URETMEZ (o dosya_tamamla'nin isi)")

        # === V6 ⭐ SIRA: FARK, tazelemeden ONCE basilir =======================
        # "Tazeleme farki ekrana basmadan YAPMASIN" sozlesmesi bir SIRA sozlesmesidir;
        # ikisinin de ciktida bulunmasi yetmez.
        kok = tmp / "v6"
        kur(kok, sablon_govde + PROJE_OZEL_SATIR)
        rc, out = kos_bayrakli(arac, kok)
        # ⛔ CAPA "FARK RAPORU" BASLIGI DEGIL, GERCEK DIFF GOVDESIDIR (`@@` hunk basligi):
        # ilk yazimda baslik aranıyordu ve `--mutasyon-fark-sessiz` KACIYORDU (10/10) --
        # baslik dongunun DISINDA basiliyor, yani vektor "diff basildi"yi hic olcmemisti.
        i_fark, i_taz = out.find("@@"), out.find("TAZELENDİ")
        ekle("V6 GERCEK diff govdesi (@@ hunk) TAZELENDI'den ONCE basilir",
             i_fark != -1 and i_taz != -1 and i_fark < i_taz,
             f"diff@{i_fark} tazelendi@{i_taz}")

        # === V7 IZOLASYON — korpus GERCEK agaci degistirmedi =================
        ekle("V7 ⭐ IZOLASYON: gercek team_setup.py ve sablon DEGISMEDI",
             _sha(SABLON) == sablon_sha
             and "_mutant_team_setup.py" not in {p.name for p in
                                                 (REPO / "scripts").glob("*.py")}
             if mutant is None else _sha(SABLON) == sablon_sha,
             "mutasyon kardes dosyada yasar; gercek kaynaga YAZILMAZ")

    finally:
        if mutant is not None:
            try:
                mutant.unlink()
            except Exception:
                pass
            print(f"[kalinti-kontrolu] mutant dosya duruyor mu: "
                  f"{'EVET -- TEMIZLIK BASARISIZ' if mutant.exists() else 'hayir'}")
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for _a, k, _c in sonuc if k)
    for ad, k, ac in sonuc:
        print(f"  [{'PASS' if k else 'FAIL'}] {ad}" + (f"  ({ac})" if not k else ""))
    print(f"\nshim_tazeleme: {gecen}/{len(sonuc)}")
    if secili:
        print(f"  (MUTASYON {secili[0]} — dusmesi BEKLENEN vektorler var; "
              f"tam skor 'mutasyon KACTI' demektir)")
        return 0 if gecen < len(sonuc) else 1
    return 0 if gecen == len(sonuc) else 1


if __name__ == "__main__":
    raise SystemExit(main())
