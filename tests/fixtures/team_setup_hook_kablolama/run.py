#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E-05 — overlay ONAY KAPISI git-hook kablolamasini DURDURMAMALI (+ Q303 onarim metni).

KUSUR (2026-08-01 bug-avi, `E-05`; 2026-08-28'de duzeltildi):
`team_setup.main()` icinde `if not junctions(...): return 1` vardi. `junctions()`
overlay farki ONAY BEKLIYORSA da False doner (`claude_overlay.materyalize`:
*"FARK VAR - onaysiz ezme YOK (T2.5)"*) - yani TAMAMEN NORMAL bir onay kapisi.
Sonuc: kendisiyle ilgisi olmayan dort adim SESSIZCE dusuyordu:

    dosya_tamamla · hookspath_core · hookspath_proje · _core_index_yenile

`hookspath_proje` PROJE reposunun `core.hooksPath`ini set eder; set edilmezse git
`scripts/git-hooks/pre-commit`i **ASLA calistirmaz** => yeni klonda pre-commit
gate'leri KURULMAMIS olur ve bunu hicbir sey soylemez ("kod != kablolama"; ayni sinif
`hookspath_proje` docstring'inde zaten belgeli).

UC AYAK:
  KIRMIZI - taban surum (`git show HEAD:`) + onay bekleyen overlay -> hooksPath SET DEGIL
  YESIL   - duzeltilmis surum + AYNI kosul            -> hooksPath SET (rc HALA 1)
  POZITIF - overlay YOKken normal kurulum akisi BOZULMADI (her iki surumde de rc=0
  KONTROL   ve hooksPath set) => fix "hatayi yutarak" calismiyor.

Q303 (2026-09-13) — `hookspath_proje`nin "pre-commit yok" uyarisi operatoru
`init_project --force`a yolluyordu; `--force` CLAUDE.md · README.md · project.yaml ·
governance/infra-findings.md dahil HER uretilen dosyayi ezer. Yeni metin D7'nin tek
kaynagindan (`utils.drift_imzasi.D7_CIFTLERI`) okunur: sablondan KOPYALA -> kurulumu
yeniden kos. Vektorler:
  Q1 fix: satir tek dosyalik onarimi gosterir, `--force` ONERMEZ (yalniz "KULLANMA" uyarisi)
  Q2 taban (Q303 fix'i SOKULMUS guncel kaynak): eski oneri geri gelir -> KIRMIZI ayak canli
  Q3 metin TEK KAYNAK: satir `D7_CIFTLERI`deki pre-commit YOK metnini AYNEN tasir
  Q4 onarim GERCEKTEN isler: mesajdaki iki yol projede cozulur; sablon kopyalanip kurulum
     yeniden kosulunca hooksPath set ve uyari kaybolur
  Q5 3. BAGLAM — git WORKTREE'si olan proje (`.git` DOSYA): ayni metin + ayni onarim

⛔ Bu korpus SAP'ye baglanmaz, ag kullanmaz. Sandbox proje temp dizindedir.

Kosum:
    python tests/fixtures/team_setup_hook_kablolama/run.py
    python tests/fixtures/team_setup_hook_kablolama/run.py --mutasyon-erken-donus
    python tests/fixtures/team_setup_hook_kablolama/run.py --mutasyon-force-onerisi
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

CORE = Path(__file__).resolve().parents[3]
TS = CORE / "scripts" / "team_setup.py"
TABAN_AD = "_zz_taban_team_setup.py"   # gecici; finally'de SILINIR
TABAN_Q303_AD = "_zz_taban_q303_team_setup.py"
MUT_AD = "_zz_mut_team_setup.py"

SONUC: list[tuple[bool, str]] = []

# E-05 fix'inin CAPASI: `junctions()` FALSE dondugunde erken `return 1` YOKTUR
# (kablolama adimlari yine kosar). Taban/mutasyon bu capayi SOKER.
_E05_CAPA = ("    kurulum_ok = junctions(proje, overlay_onayli=a.overlay_onayli)\n"
             "    if not kurulum_ok:\n")

# Q303 fix'inin CAPASI: uyari metni tek kaynaktan gelir. Taban/mutasyon eski literali geri koyar.
_Q303_CAPA = ('        say(WARN, f"proje scripts/git-hooks/pre-commit yok — '
              '{_precommit_yok_onarimi()}")\n')
_Q303_ESKI = ('        say(WARN, "proje scripts/git-hooks/pre-commit yok — '
              'init_project --force ile üret")\n')
_PC_SABLON_REL = "core/claude/git-hooks/pre-commit.template"


def _fix_sok(kaynak: str, nicin: str) -> str:
    """Guncel team_setup.py'den E-05 fix'ini SOK (erken `return 1` geri gelir).

    ⛔ Zamandan bagimsiz: girdi calisma agacindaki GUNCEL dosyadir, git gecmisi DEGIL.
    Capa bulunamazsa GURULTULU dur — sessizce 'taban == fix' durumuna dusmek, kirmizi
    ayagi olu birakir (tam olarak 2026-08-28 regresyonu).
    """
    if _E05_CAPA not in kaynak:
        raise SystemExit(
            f"TABAN URETILEMEDI ({nicin}): E-05 capasi (`kurulum_ok` kontrolu) "
            f"team_setup.py icinde bulunamadi. Fix'in yazimi degismis => uretilen "
            f"'taban' ARTIK kusuru uretmiyor olabilir. _E05_CAPA'yi GUNCELLE.")
    return kaynak.replace(
        _E05_CAPA,
        "    kurulum_ok = junctions(proje, overlay_onayli=a.overlay_onayli)\n"
        "    if not kurulum_ok:\n"
        "        return 1  # TABAN/MUTASYON: E-05 oncesi erken donus geri kondu\n"
        "    if not kurulum_ok:\n", 1)


def _q303_sok(kaynak: str, nicin: str) -> str:
    """Guncel team_setup.py'den Q303 fix'ini SOK (eski `--force` onerisi geri gelir).

    E-05 ile ayni sozlesme: girdi GUNCEL dosya (git gecmisi degil); capa yoksa GURULTULU dur.
    """
    if _Q303_CAPA not in kaynak:
        raise SystemExit(
            f"TABAN URETILEMEDI ({nicin}): Q303 capasi (`_precommit_yok_onarimi()` cagrisi) "
            f"team_setup.py icinde bulunamadi. _Q303_CAPA'yi GUNCELLE.")
    return kaynak.replace(_Q303_CAPA, _Q303_ESKI, 1)


def _d7_precommit_yok_metni() -> str:
    """Tek kaynagi DOGRUDAN oku (team_setup'in cevirisine guvenmeden)."""
    sys.path.insert(0, str(CORE / "scripts"))
    from utils.drift_imzasi import D7_CIFTLERI  # type: ignore
    for rel_y, _t, _ad, yok, _s in D7_CIFTLERI:
        if rel_y == "scripts/git-hooks/pre-commit":
            return yok
    raise SystemExit("D7_CIFTLERI'nde pre-commit cifti yok — Q303 tek kaynagi kayip")


def _sil(d: Path) -> None:
    """Windows'ta `.git/objects` SALT-OKUNUR yazilir; duz `ignore_errors` SESSIZCE basarisiz
    olur ve `%TEMP%` altinda depo YIGAR. Desen: `precommit_kopya_surum_esligi/run.py::_sil`.
    Q303 olcumu (2026-09-13): Q5'in `commit`i 3 salt-okur nesne birakiyordu -> koşum basina
    1 artik `ix_e05_*` dizini (bir gunde 12). Junction'lara GIRMEZ (rmtree link'i izlemez)."""
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


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((kosul, ad))
    print(f"  [{'OK' if kosul else 'FAIL'}] {ad}" + (f"  -- {detay}" if detay else ""))


def sandbox_proje(kok: Path, overlay: bool, etiket: str, precommit: bool = True) -> Path:
    """Sahte proje: git reposu + pre-commit dosyasi (+ istege bagli ONAY BEKLEYEN overlay)."""
    p = kok / f"proje_{etiket}"
    (p / "scripts" / "git-hooks").mkdir(parents=True)
    if precommit:
        (p / "scripts" / "git-hooks" / "pre-commit").write_text(
            "#!/bin/sh\nexit 0\n", encoding="utf-8", newline="\n")
    subprocess.run(["git", "init", "-q", str(p)], check=True, capture_output=True)
    # commit sart degil; hookspath_proje yalniz `.git` varligina ve dosyaya bakar.

    if overlay:
        # `claude-local/agents/*.md` => overlay VAR. Ayrica `.claude/agents` GERCEK dizin
        # ve icerigi uretilecekten FARKLI => `fark_raporu` dolu => materyalize onaysiz
        # URETMEZ => junctions() False. Bu bir HATA DEGIL, ONAY KAPISIDIR.
        (p / "claude-local" / "agents").mkdir(parents=True)
        (p / "claude-local" / "agents" / "zz-deney.md").write_text(
            "---\nname: zz-deney\ndescription: fixture overlay\n---\n\ngovde\n",
            encoding="utf-8", newline="\n")
        (p / ".claude" / "agents").mkdir(parents=True)
        (p / ".claude" / "agents" / "zz-deney.md").write_text(
            "ESKI VE FARKLI ICERIK — fark_raporu bunu yakalar\n",
            encoding="utf-8", newline="\n")
    return p


def kos(script: Path, proje: Path) -> tuple[int, str]:
    r = subprocess.run(
        [sys.executable, str(script), "--project", str(proje),
         "--no-install", "--no-plugins", "--no-seed", "--no-smoke"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=300, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def hookspath(proje: Path) -> str:
    r = subprocess.run(["git", "-C", str(proje), "config", "--local", "core.hooksPath"],
                       capture_output=True, text=True)
    return (r.stdout or "").strip()


def pc_yok_satirlari(cikti: str) -> list[str]:
    return [s for s in cikti.splitlines() if "pre-commit yok" in s]


def tek_dosya_onarimi(satirlar: list[str]) -> bool:
    """Q303 olcutu: TEK satir · sablon yolu + KOPYALA · `--force` yalniz 'KULLANMA' uyarisi olarak.

    ⚠ Kaydin literal vektoru "metin `--force` icermez" idi; tek kaynak metni `init_project
    --force KULLANMA` uyarisini TASIR (operatore tuzagi adiyla soyler). Olcut bu yuzden
    ONERIYI yakalar: 'KULLANMA' ile izlenmeyen her `--force` = oneri.
    """
    if len(satirlar) != 1:
        return False
    s = satirlar[0]
    return (re.search(r"--force(?! KULLANMA)", s) is None
            and _PC_SABLON_REL in s and "KOPYALA" in s)


def q303_onarimi_uygula(proje: Path) -> bool:
    """Mesajin soyledigini AYNEN yap: projedeki (junction'li) sablonu kopyala. Yol yoksa False."""
    sablon = proje.joinpath(*_PC_SABLON_REL.split("/"))
    if not sablon.is_file():
        return False
    hedef = proje / "scripts" / "git-hooks" / "pre-commit"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(sablon, hedef)
    return hedef.read_bytes() == sablon.read_bytes()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutasyon-erken-donus", action="store_true",
                    help="fix'i SOK: erken `return 1`u geri getir (taban davranis)")
    ap.add_argument("--mutasyon-force-onerisi", action="store_true",
                    help="Q303 fix'ini SOK: uyari yine `init_project --force` onerir")
    a = ap.parse_args()
    mutasyon = a.mutasyon_erken_donus or a.mutasyon_force_onerisi

    print(__doc__.strip().splitlines()[0])
    kip = ("MUTASYON --erken-donus" if a.mutasyon_erken_donus else
           "MUTASYON --force-onerisi" if a.mutasyon_force_onerisi else "NORMAL")
    print(f"MOD: {kip}\n")

    taban_yol = CORE / "scripts" / TABAN_AD
    taban_q303_yol = CORE / "scripts" / TABAN_Q303_AD
    mut_yol = CORE / "scripts" / MUT_AD
    tmpdir = tempfile.mkdtemp(prefix="ix_e05_")
    try:
        tmp = Path(tmpdir)

        # ── TABAN (KIRMIZI ayak) — KAYNAKTAN TURETILIR, REPO DURUMUNDAN DEGIL ──
        # ⛔ `git show HEAD:` KULLANILMAZ (2026-08-28'de main'i kirdi): fix merge
        #    edilince HEAD *fix*'i icerir => taban = fix => kirmizi ayak yesile doner.
        # ✅ Guncel `team_setup.py` kopyalanir ve E-05 fix'i SOKULUR: `kurulum_ok`
        #    kontrolune erken `return 1` geri konur = duzeltme oncesi davranis.
        #    (Dosya CORE/scripts/ icine yazilir cunku `CORE_ROOT = __file__/../..`;
        #     temp dizinde CORE_ROOT yanlis cozulurdu. `finally` blogu SILER.)
        kaynak = TS.read_text(encoding="utf-8")
        taban_yol.write_text(_fix_sok(kaynak, "taban"), encoding="utf-8", newline="")
        taban_q303_yol.write_text(_q303_sok(kaynak, "taban-q303"), encoding="utf-8", newline="")

        # ── kosulacak "fix" surumu (mutasyonluysa ilgili fix sokulur) ───────────
        fix_yol = TS
        if a.mutasyon_erken_donus:
            mut_yol.write_text(_fix_sok(kaynak, "mutasyon"), encoding="utf-8", newline="")
            fix_yol = mut_yol
        elif a.mutasyon_force_onerisi:
            mut_yol.write_text(_q303_sok(kaynak, "mutasyon-q303"), encoding="utf-8", newline="")
            fix_yol = mut_yol

        # ══ KIRMIZI ════════════════════════════════════════════════════════════
        print("-- KIRMIZI: taban surum + ONAY BEKLEYEN overlay --")
        p1 = sandbox_proje(tmp, overlay=True, etiket="r1_taban")
        rc, cikti = kos(taban_yol, p1)
        hp = hookspath(p1)
        kontrol("R1 taban: overlay onay bekliyor -> rc=1", rc == 1, f"rc={rc}")
        kontrol("R1b taban: git-hook kablolamasi HIC YAPILMADI (hooksPath BOS)",
                hp == "", f"hooksPath={hp!r}")

        # ══ YESIL ══════════════════════════════════════════════════════════════
        print("\n-- YESIL: duzeltilmis surum + AYNI kosul --")
        p2 = sandbox_proje(tmp, overlay=True, etiket="v1_fix")
        rc2, cikti2 = kos(fix_yol, p2)
        hp2 = hookspath(p2)
        kontrol("V1 fix: git-hook kablolamasi YAPILDI (pre-commit artik canli)",
                hp2 == "scripts/git-hooks", f"hooksPath={hp2!r}")
        kontrol("V1b fix: HATA YUTULMADI — kurulum yine BASARISIZ (rc=1)",
                rc2 == 1, f"rc={rc2}")
        kontrol("V1c fix: onay kapisi hala ISLIYOR (overlay onaysiz EZILMEDI)",
                (p2 / ".claude" / "agents" / "zz-deney.md").read_text(
                    encoding="utf-8").startswith("ESKI VE FARKLI"),
                "overlay dosyasi degismemis olmali")

        # ══ POZITIF KONTROL — normal akis bozulmadi mi? ════════════════════════
        print("\n-- POZITIF KONTROL: overlay YOK, normal kurulum akisi --")
        p3 = sandbox_proje(tmp, overlay=False, etiket="p1_taban")
        rc3, cikti3 = kos(taban_yol, p3)
        hp3 = hookspath(p3)
        p4 = sandbox_proje(tmp, overlay=False, etiket="p2_fix")
        rc4, cikti4 = kos(fix_yol, p4)
        hp4 = hookspath(p4)
        kontrol("P1 taban: overlaysiz kurulum rc=0 + hooksPath set",
                rc3 == 0 and hp3 == "scripts/git-hooks", f"rc={rc3} hooksPath={hp3!r}")
        kontrol("P2 fix: overlaysiz kurulum AYNI sonuc (rc + hooksPath BIREBIR)",
                rc4 == rc3 and hp4 == hp3, f"rc={rc4} hooksPath={hp4!r}")
        kontrol("P3 fix normal akista CORE-INDEX adimina da ULASIYOR",
                "CORE-INDEX" in cikti4, "cikti CORE-INDEX satiri icermeli")

        # ══ 3. BAGLAM — git reposu OLMAYAN proje (repo_mode=none) ══════════════
        print("\n-- 3. BAGLAM: git reposu olmayan proje --")
        p5 = tmp / "proje_gitsiz"
        (p5 / "scripts" / "git-hooks").mkdir(parents=True)
        (p5 / "scripts" / "git-hooks" / "pre-commit").write_text(
            "#!/bin/sh\nexit 0\n", encoding="utf-8", newline="\n")
        rc5, cikti5 = kos(fix_yol, p5)
        kontrol("V2 gitsiz proje: cokmez, uyari verir (repo_mode=none dali)",
                rc5 in (0, 1) and "pre-commit kablolamas" in cikti5,
                f"rc={rc5}")

        # ══ Q303 — "pre-commit yok" uyarisi tek dosyalik onarimi gostermeli ════
        print("\n-- Q303: pre-commit YOK uyarisi --force ONERMEMELI --")
        q_fix = sandbox_proje(tmp, overlay=False, etiket="q303_fix", precommit=False)
        _rcq, ciktiq = kos(fix_yol, q_fix)
        satir_fix = pc_yok_satirlari(ciktiq)
        kontrol("Q1 fix: uyari TEK dosyalik onarimi gosterir (sablon yolu + KOPYALA), "
                "`--force` ONERMEZ", tek_dosya_onarimi(satir_fix), f"satir={satir_fix}")

        q_tab = sandbox_proje(tmp, overlay=False, etiket="q303_taban", precommit=False)
        _rct, ciktit = kos(taban_q303_yol, q_tab)
        satir_tab = pc_yok_satirlari(ciktit)
        kontrol("Q2 taban (Q303 fix'i sokulmus): eski `init_project --force` onerisi GERI "
                "GELIR ve Q1 olcutu onu REDDEDER (kirmizi ayak canli)",
                len(satir_tab) == 1 and "init_project --force ile" in satir_tab[0]
                and not tek_dosya_onarimi(satir_tab), f"satir={satir_tab}")

        d7_metin = _d7_precommit_yok_metni()
        kontrol("Q3 metin TEK KAYNAK: satir `D7_CIFTLERI` pre-commit YOK metnini AYNEN tasir",
                len(satir_fix) == 1 and satir_fix[0].rstrip().endswith(d7_metin),
                f"d7={d7_metin!r}")

        ts_proje = q_fix / "core" / "scripts" / "team_setup.py"
        kopyalandi = q303_onarimi_uygula(q_fix)
        hp_q_once = hookspath(q_fix)
        _rcq2, ciktiq2 = kos(fix_yol, q_fix)
        hp_q = hookspath(q_fix)
        kontrol("Q4 onarim GERCEKTEN isler: mesajdaki iki yol projede cozulur, sablon "
                "kopyalanip kurulum yeniden kosulunca hooksPath set + uyari KAYBOLUR",
                kopyalandi and ts_proje.is_file() and hp_q_once == ""
                and hp_q == "scripts/git-hooks" and not pc_yok_satirlari(ciktiq2),
                f"kopya={kopyalandi} ts={ts_proje.is_file()} once={hp_q_once!r} "
                f"sonra={hp_q!r} uyari={pc_yok_satirlari(ciktiq2)}")

        # ══ Q303 3. BAGLAM — git WORKTREE'si (`.git` DOSYA, dizin degil) ═══════
        print("\n-- Q303 3. BAGLAM: pre-commit'siz projenin git worktree'si --")
        ana = sandbox_proje(tmp, overlay=False, etiket="q303_ana", precommit=False)
        (ana / "README.md").write_text("x\n", encoding="utf-8", newline="\n")
        for komut in (["add", "README.md"],
                      ["-c", "user.email=fixture", "-c", "user.name=fixture",
                       "commit", "-q", "-m", "ilk"],
                      ["worktree", "add", "-q", str(tmp / "q303_wt"), "-b", "q303wt"]):
            subprocess.run(["git", "-C", str(ana), *komut], check=True, capture_output=True)
        wt = tmp / "q303_wt"
        _rcw, ciktiw = kos(fix_yol, wt)
        satir_wt = pc_yok_satirlari(ciktiw)
        wt_kopya = q303_onarimi_uygula(wt)
        _rcw2, ciktiw2 = kos(fix_yol, wt)
        hp_wt = hookspath(wt)
        kontrol("Q5 worktree (`.git` DOSYA): ayni tek-dosya onarimi + onarim sonrasi uyari "
                "KAYBOLUR ve hooksPath set",
                (wt / ".git").is_file() and tek_dosya_onarimi(satir_wt) and wt_kopya
                and not pc_yok_satirlari(ciktiw2) and hp_wt == "scripts/git-hooks",
                f".git_dosya={(wt / '.git').is_file()} satir={satir_wt} kopya={wt_kopya} "
                f"hooksPath={hp_wt!r}")
    finally:
        for y in (taban_yol, taban_q303_yol, mut_yol):
            try:
                y.unlink()
            except FileNotFoundError:
                pass
        _sil(Path(tmpdir))

    gecen = sum(1 for ok, _ in SONUC if ok)
    print(f"\n{'=' * 62}\nSONUC: {gecen}/{len(SONUC)}")
    if gecen != len(SONUC):
        print("Dusen: " + ", ".join(ad for ok, ad in SONUC if not ok))
    if mutasyon:
        print("(MUTASYON: dusus BEKLENIR)")
        return 0
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    raise SystemExit(main())
