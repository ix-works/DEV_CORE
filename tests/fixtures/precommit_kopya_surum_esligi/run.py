#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SABLON SERTLESTI != KOPYA SERTLESTI — `pre-commit` kopyalarinin surum esligi (Q245).

KOK MEKANIZMA (olculdu 2026-09-03, `scripts/init_project.py`):
  `precommit = (tpl / "git-hooks" / "pre-commit.template").read_text(...)`      (:246)
  `uret(proje / "scripts" / "git-hooks" / "pre-commit", precommit, a.force)`   (:260)
  `def uret(...)`: `if hedef.exists() and not force: return "[ATLA] ..."`      (:215-216)
⇒ Dosya DOGUMDA BIR KEZ yazilir. `team_setup.py` yalnizca `core.hooksPath`i KABLOLAR
  (:295-314), icerige HIC bakmaz. Sablon her sertlestiginde DOGMUS projelerdeki kopya
  SESSIZCE geride kalir; hicbir katman bunu olcmez. Sablonda placeholder YOKTUR
  (`grep -n "{[a-z_]*}"` -> 0) ⇒ sapma "proje-ozel uyarlama" ile aciklanamaz.

⛔ KARDES KORPUSLARLA FARK (ucu ayni dosyayi okur, UC AYRI SEY olcer):
  * `precommit_junction_failclosed` -> SABLONUN adim-2'si (2026-08-20 sertlestirmesi)
  * `precommit_coreleak_failclosed` -> SABLONUN adim-1'i (Q199(1) sertlestirmesi)
  * BU KORPUS               -> ikisinin BIRLESIMI + DOGUM YUZEYI: sertlestirmeler
    kopyaya ULASIYOR MU, ve ULASMAMIS bir kopya ne yapiyor. Kardeslerin HICBIRI iki
    sertlestirmenin AYNI ANDA sokulmus halini (= canli repolarda YASAYAN surum) olcmez.

OLCULEN CANLI DAGILIM (2026-09-03, dort tuketici proje; CRLF-normalize EXEC-satir sayimi):
  | kopya                                    | exec | SIZ_RC | VALIDATOR_DURUM |
  | core/claude/git-hooks/pre-commit.template |  42  |   4    |        2        |
  | <PROJE_D>  (2026-09-03 dogumlu)          |  42  |   4    |        2        | <- BAYT-ES
  | <PROJE_C>                                |  31  |   0    |        2        | <- (1) YOK
  | <PROJE_A> == <PROJE_B>  (ayni blob)      |  19  |   0    |        0        | <- IKISI DE YOK
  ⇒ dort kopya UC ayri surumde. Yalniz sertlestirmelerden SONRA dogan proje sablona esit
    (`git rev-parse HEAD:scripts/git-hooks/pre-commit` = sablonun LF blob'u, bayt-es).

⭐ TABAN SADAKATI (bu korpusun en onemli capasi): asagidaki `_sapik()` sablondan IKI
  sertlestirmeyi sokerek "sapik kopya" turetir. 2026-09-03'te olculdu: turetilen tabanin
  EXEC SATIRLARI, iki projenin gercek HEAD blob'uyla **BIREBIR ESITTIR** (19/19). Yani
  buradaki "bozuk" vektor bir korkuluk degil, canlida calisan surumdur.
  (Tam-bayt esitlik YOKTUR ve ARANMAZ: sertlestirmelerle gelen ACIKLAMA yorumlari
   turetimde kalir — sokum kodu sokar, tarihce yorumunu degil.)
  ⛔ Taban `git show <sha>:` ile TARIHTEN cekilmez (sig klonda cozulmez, merge'de bayatlar).

⚠ SAYIM EXEC-SATIRDA YAPILIR, HAM METINDE DEGIL: sablonun kendi 29. satiri
  *"asagidaki grep isabeti bu YORUM satiridir, kod DEGIL"* diye uyarir. Ham
  `count("SIZ_RC")` turetilen sapik tabanda **1** doner (tarihce yorumu) — yani ham
  sayim bu korpusu SESSIZCE yalanlardi.

  S1 ⭐ DOGUM YUZEYI: gercek `init_project.py` (izole core iskeleti) kosar -> urettigi
     `scripts/git-hooks/pre-commit` sablonla BAYT-ES (LF). Sabit yol + sabit icerik.
  S2 ⭐ BILINEN-BOZUK / FAIL-OPEN KANITI: SAPIK kopya + `core/` COZULMUYOR -> rc 0 +
     "[pre-commit] OK" ve ardindan GERCEK `git commit` GECER (1 commit) — denetimsiz.
  S3 BILINEN-TEMIZ: SABLON ayni depoda -> rc 1 + gorunur mesaj, commit 0.
  S4 ⭐ 3. BAGLAM (gorev-disi eksen): SAPIK kopya + `core/` VAR ama `.git/index` BOZUK
     -> rc 0 + "OK". Iki fail-open ekseni AYNI dosyada BIRLIKTE yasiyor.
  S5 SABLON ayni kosulda -> rc 1.
  S6 POZITIF KONTROL: SABLON + GERCEK staged `core/` sizintisi -> rc 1 + junction mesaji
     (sertlesme gercek bulguyu OLDURMEDI).
  S7 FP CAPASI: SABLON + saglam depo + validator VAR ve geciyor -> rc 0, "KOSTURULAMADI" YOK.
  S8 SAPMA-OLCUSU: exec-satirda SABLON 2/2 sertlestirme capasi tasir, SAPIK taban 0/2.
  S9 TABAN KOZMETIK DEGIL: sapik tabanda IKI fail-closed dalinin ikisi de YOK ve exec
     satir sayisi sablonunkinden KESIN kucuk (turetim NO-OP degil).
  M1-M5 fix'in her katmani + dogum yuzeyi AYRI sokulur -> korpus KIRMIZI olmali.

Kosum: python tests/fixtures/precommit_kopya_surum_esligi/run.py     (exit 0 = PASS)
Cikis kodu: 0 hepsi gecti | 1 dusen var | 2 alet gecersiz (yama tutmadi / sh yok / sablon yok)
"""
from __future__ import annotations

import os
import shutil
import stat
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
CORE = HERE.parents[2]
SABLON = CORE / "claude" / "git-hooks" / "pre-commit.template"
INIT_PROJECT = CORE / "scripts" / "init_project.py"

SH = shutil.which("sh") or shutil.which("bash")

# init_project'in izole iskelette okudugu sablonlar (jeneratorun tam yuzeyi).
_CLAUDE_DOSYALARI = (
    "CLAUDE.project.template.md", "README.project.template.md", "settings.template.json",
    "hook_shim.template.py", "kesin-yasaklar.canonical.md", "CODEOWNERS.template",
    "git-hooks/pre-commit.template", "workflows/guard.template.yml",
)

# ── SERTLESTIRME CAPALARI (sokum = 2026-09-02 / 2026-08-20 oncesi kopya) ───────
# (1) Q199(1): rc AYRI yakalanir + cokme fail-closed
_S1_YENI = (
    "SIZ_RC=0\n"
    "BAD=$(git diff --cached --name-only -- \\\n"
    "        'core/**' '.claude/agents/**' '.claude/skills/**' '.claude/commands/**' '.claude/rules/**' \\\n"
    "      ) || SIZ_RC=$?\n"
)
_S1_ESKI = (
    "BAD=$(git diff --cached --name-only -- \\\n"
    "        'core/**' '.claude/agents/**' '.claude/skills/**' '.claude/commands/**' '.claude/rules/**' \\\n"
    "        2>/dev/null || true)\n"
)
_S1_DAL_BAS = 'if [ "$SIZ_RC" -ne 0 ]; then'
_S1_DAL_SON = 'if [ -n "$BAD" ]; then'

# (2) 2026-08-20: validator adimi ATLANAMAZ (`else` dali) + kapanis satirinda PAYDA
_S2_PAYDA = '  VALIDATOR_DURUM="koştu"\n'
_S2_ELSE = "\nelse\n"
_S2_FI = "fi\n"
_S2_KAPANIS_YENI = ('echo "[pre-commit] OK — core-sızıntı kontrolü + '
                    'run_all_validators --quick ($VALIDATOR_DURUM)"')
_S2_KAPANIS_ESKI = 'echo "[pre-commit] OK"'


class YamaTutmadi(Exception):
    """Capa kaynakta bulunamadi -> ALET gecersiz (sayi BASILMAZ, exit 2)."""


def _sok1(s: str) -> str:
    if _S1_YENI not in s:
        raise YamaTutmadi("sertlestirme(1) capasi yok: rc yakalama blogu")
    s = s.replace(_S1_YENI, _S1_ESKI, 1)
    if _S1_DAL_BAS not in s or _S1_DAL_SON not in s:
        raise YamaTutmadi("sertlestirme(1) capasi yok: fail-closed dal siniri")
    i = s.index(_S1_DAL_BAS)
    j = s.index(_S1_DAL_SON, i)
    return s[:i] + s[j:]


def _sok2(s: str) -> str:
    if _S2_PAYDA not in s or _S2_KAPANIS_YENI not in s:
        raise YamaTutmadi("sertlestirme(2) capasi yok: payda / kapanis satiri")
    i = s.index(_S2_PAYDA)
    try:
        e = s.index(_S2_ELSE, i)
        j = s.index(_S2_FI, e)
    except ValueError as exc:                       # pragma: no cover - capa bayat
        raise YamaTutmadi("sertlestirme(2) capasi yok: else/fi blogu") from exc
    s = s[:i] + s[j:]
    return s.replace(_S2_KAPANIS_YENI, _S2_KAPANIS_ESKI, 1)


def _sapik(sablon: str) -> str:
    """Canli repolarda YASAYAN surum: iki sertlestirme de sokulmus."""
    return _sok2(_sok1(sablon))


def exec_satirlar(metin: str) -> list[str]:
    """Yorum ve bos satirlari AT — capa saymak icin TEK gecerli yuzey.

    Sablonun 29. satiri bu kurali kendisi yazar: tarihce yorumlari sokulen kodun
    metnini ALINTILAR; ham `count()` bu yuzden yalancidir (olculdu: sapik tabanda
    ham `SIZ_RC` sayisi 1, exec sayisi 0).
    """
    return [l for l in metin.replace("\r\n", "\n").split("\n")
            if l.strip() and not l.lstrip().startswith("#")]


def _capa_sayisi(metin: str, capa: str) -> int:
    return "\n".join(exec_satirlar(metin)).count(capa)


# ── SENTETIK DEPO / KABUK ─────────────────────────────────────────────────────
def _sil(d: Path) -> None:
    """Windows'ta `.git/objects` SALT-OKUNUR yazilir; duz `ignore_errors` SESSIZCE
    basarisiz olur ve `%TEMP%` altinda depo YIGAR (olculdu 2026-09-02: 2040 dizin)."""
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


def _git(depo: Path, *a):
    return subprocess.run(["git", *a], cwd=str(depo), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def _depo_kur(core_var: bool = True, validator_rc: int = 0, sizinti: bool = False,
              bozuk_index: bool = False) -> Path:
    """GERCEK git deposu: sablon `git rev-parse --show-toplevel` cagirir; sahte dizin
    sessizce BASKA bir agaci gosterirdi ("kod != kablolama"nin kabuk yuzu)."""
    d = Path(tempfile.mkdtemp(prefix="q245_"))
    _git(d, "init", "-q")
    _git(d, "config", "user.email", "t@t")
    _git(d, "config", "user.name", "t")
    _git(d, "config", "commit.gpgsign", "false")
    _git(d, "config", "core.hooksPath", "scripts/git-hooks")

    (d / "dosya.txt").write_text("x\n", encoding="utf-8")
    _git(d, "add", "dosya.txt")

    if core_var:
        vdir = d / "core" / "scripts" / "validators"
        vdir.mkdir(parents=True, exist_ok=True)
        (vdir / "run_all_validators.py").write_text(
            "import sys\nprint('[sahte-validator] kostu')\nsys.exit(%d)\n" % validator_rc,
            encoding="utf-8")

    if sizinti:
        (d / "core").mkdir(parents=True, exist_ok=True)
        (d / "core" / "sizinti.md").write_text("gizli-core-icerigi\n", encoding="utf-8")
        _git(d, "add", "-f", "core/sizinti.md")

    if bozuk_index:
        (d / ".git" / "index").write_bytes(b"BOZUK-INDEX-VERISI" * 8)

    return d


def _kos(d: Path, hook_metni: str) -> tuple[int, str]:
    hook = d / "pre-commit.sh"
    hook.write_text(hook_metni, encoding="utf-8", newline="\n")
    r = subprocess.run([SH, str(hook)], cwd=str(d), capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def gate(hook_metni: str, **kw) -> tuple[int, str]:
    d = _depo_kur(**kw)
    try:
        return _kos(d, hook_metni)
    finally:
        _sil(d)


def uctan_uca(hook_metni: str, **kw) -> tuple[int, bool, int]:
    """Gate GECERSE denetimsiz commit GERCEKTEN oluyor mu? -> (rc, commit_oldu, sayi)"""
    d = _depo_kur(**kw)
    try:
        rc, _ = _kos(d, hook_metni)
        oldu = False
        if rc == 0:
            c = _git(d, "commit", "-q", "-m", "denetimsiz commit")
            oldu = (c.returncode == 0)
        say = _git(d, "rev-list", "--count", "HEAD")
        n = int(say.stdout.strip()) if say.returncode == 0 and say.stdout.strip().isdigit() else -1
        return rc, oldu, n
    finally:
        _sil(d)


# ── DOGUM YUZEYI: gercek init_project.py, IZOLE core iskeletinde ──────────────
_URETIM_CAGRISI = ('        uret(proje / "scripts" / "git-hooks" / "pre-commit", '
                   'precommit, a.force),\n')


def izole_core(kum: Path, init_kaynagi: str) -> Path:
    """Mutant GERCEK agaca YAZILMAZ: minimal ama CALISIR bir core iskeleti kurulur.
    (`init_project` CORE_ROOT = __file__.parent.parent'ten sablon okur ve
     `utils.yasaklar_stamp` import eder.)"""
    core = kum / "izole_core"
    (core / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copytree(CORE / "scripts" / "utils", core / "scripts" / "utils")
    for rel in _CLAUDE_DOSYALARI:
        hedef = core / "claude" / rel
        hedef.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(CORE / "claude" / rel, hedef)
    (core / "scripts" / "init_project.py").write_text(init_kaynagi, encoding="utf-8",
                                                      newline="\n")
    return core


def _temiz_env() -> dict:
    env = os.environ.copy()
    for k in list(env):
        if k == "CLAUDE_PROJECT_DIR" or k.startswith("IX_"):
            env.pop(k, None)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def dogum_yuzeyi(init_kaynagi: str) -> tuple[bool, str]:
    """-> (uretilen dosya sablonla LF-bayt-es mi, detay)"""
    kum = Path(tempfile.mkdtemp(prefix="q245init_"))
    try:
        core = izole_core(kum, init_kaynagi)
        proje = kum / "prova"
        r = subprocess.run([sys.executable, str(core / "scripts" / "init_project.py"),
                            str(proje), "--name", "PROVA"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=_temiz_env(), timeout=180)
        if r.returncode != 0:
            ozet = " ".join(((r.stdout or "") + (r.stderr or "")).split())[-160:]
            return False, "uretici rc=%s %s" % (r.returncode, ozet)
        hedef = proje / "scripts" / "git-hooks" / "pre-commit"
        if not hedef.is_file():
            return False, "URETILMEDI: %s" % hedef
        uretilen = hedef.read_text(encoding="utf-8").replace("\r\n", "\n")
        beklenen = SABLON.read_text(encoding="utf-8").replace("\r\n", "\n")
        return uretilen == beklenen, ("uretilen=%d satir beklenen=%d satir"
                                      % (len(uretilen.split("\n")), len(beklenen.split("\n"))))
    finally:
        _sil(kum)


# ── SENARYOLAR ────────────────────────────────────────────────────────────────
def senaryolar(sablon: str, init_kaynagi: str) -> list[tuple[str, bool, str]]:
    out: list[tuple[str, bool, str]] = []

    def ekle(ad, kosul, detay=""):
        out.append((ad, bool(kosul), detay))

    # ⚠ TABAN DAIMA PRISTINE sablondan turetilir (mutasyondan BAGIMSIZ).
    sapik = _sapik(SABLON.read_text(encoding="utf-8"))

    # S1 ⭐ DOGUM YUZEYI ------------------------------------------------------
    ok, detay = dogum_yuzeyi(init_kaynagi)
    ekle("S1 DOGUM YUZEYI: init_project'in urettigi kopya sablonla BAYT-ES (LF)", ok, detay)

    # S2 ⭐ BILINEN-BOZUK: sapik kopya + core/ COZULMUYOR ----------------------
    rc, oldu, n = uctan_uca(sapik, core_var=False)
    ekle("S2 FAIL-OPEN KANITI: sapik kopya + core/ YOK -> rc 0 + denetimsiz commit GECTI",
         rc == 0 and oldu is True and n == 1, "rc=%s commit_oldu=%s n=%s" % (rc, oldu, n))

    # S3 BILINEN-TEMIZ: sablon ayni depoda ------------------------------------
    rc, oldu, n = uctan_uca(sablon, core_var=False)
    ekle("S3 BILINEN-TEMIZ: SABLON + core/ YOK -> rc 1, commit YOK",
         rc == 1 and oldu is False and n in (0, -1),
         "rc=%s commit_oldu=%s n=%s" % (rc, oldu, n))

    # S4 ⭐ 3. BAGLAM (gorev-disi eksen): core VAR, .git/index BOZUK -----------
    rc, o = gate(sapik, core_var=True, bozuk_index=True)
    ekle("S4 3.BAGLAM: sapik kopya + core VAR ama .git/index BOZUK -> rc 0 + '[pre-commit] OK'",
         rc == 0 and "[pre-commit] OK" in o, "rc=%s cikti=%r" % (rc, o[-200:]))

    # S5 SABLON ayni kosulda ---------------------------------------------------
    rc, o = gate(sablon, core_var=True, bozuk_index=True)
    ekle("S5 SABLON ayni bozuk-index deposunda -> rc 1 + 'KOSTURULAMADI'",
         rc == 1 and "KOŞTURULAMADI" in o and "[pre-commit] OK" not in o,
         "rc=%s cikti=%r" % (rc, o[-200:]))

    # S6 POZITIF KONTROL: gercek sizinti hala yakalaniyor ----------------------
    rc, o = gate(sablon, core_var=True, sizinti=True)
    ekle("S6 POZITIF KONTROL: gercek core/ sizintisi -> rc 1 + junction mesaji",
         rc == 1 and "junction" in o.lower() and "core/sizinti.md" in o,
         "rc=%s cikti=%r" % (rc, o[-200:]))

    # S7 FP CAPASI -------------------------------------------------------------
    rc, o = gate(sablon, core_var=True)
    ekle("S7 FP capasi: saglam+temiz depo -> rc 0, yanlis-pozitif YOK",
         rc == 0 and "[pre-commit] OK" in o and "KOŞTURULAMADI" not in o
         and "junction" not in o.lower(), "rc=%s cikti=%r" % (rc, o[-200:]))

    # S8 SAPMA-OLCUSU (denetim metriginin kod capasi) --------------------------
    s_siz, s_val = _capa_sayisi(sablon, "SIZ_RC"), _capa_sayisi(sablon, "VALIDATOR_DURUM")
    p_siz, p_val = _capa_sayisi(sapik, "SIZ_RC"), _capa_sayisi(sapik, "VALIDATOR_DURUM")
    # ⚠ Senaryo ADINDA `N/M` YAZILMAZ: run_battery skoru stdout'tan regex'le okur ve
    #   basliktaki "0/2" gibi bir ifadeyi KORPUS SKORU sanir (olculdu 2026-09-04: 9/9
    #   yerine "0/2" raporlandi). Sayilar yalniz `detay` alaninda durur.
    ekle("S8 SAPMA-OLCUSU: sablon IKI sertlestirme capasini da tasir, sapik taban HICBIRINI "
         "(EXEC satirda sayilir)",
         s_siz > 0 and s_val > 0 and p_siz == 0 and p_val == 0,
         "sablon SIZ_RC=%d VALIDATOR_DURUM=%d | sapik SIZ_RC=%d VALIDATOR_DURUM=%d"
         % (s_siz, s_val, p_siz, p_val))

    # S9 TABAN KOZMETIK DEGIL --------------------------------------------------
    se, pe = len(exec_satirlar(sablon)), len(exec_satirlar(sapik))
    ekle("S9 TURETIM NO-OP DEGIL: sapik tabanda iki fail-closed dali da YOK, exec satir < sablon",
         pe < se and _S1_DAL_BAS not in sapik
         and "VALIDATOR ZİNCİRİ KOŞTURULAMADI" not in sapik,
         "sablon_exec=%d sapik_exec=%d" % (se, pe))

    return out


# ── MUTASYONLAR: her katman AYRI kesilir --------------------------------------
#  ⛔ Tek noktali sokum yetmez: savunma-derinliginde bir katman digerini maskeler.
#  ⚠ Mutasyon YALNIZ "sertlesmis" tarafa uygulanir; SAPIK taban daima PRISTINE
#    sablondan turetilir (aksi halde M1/M3 "YAMA TUTMADI" verirdi, "KACTI" degil).
def _yalniz_sablon(f):
    return lambda sab, ini: (f(sab), ini)


MUTASYONLAR = [
    ("M1 sertlestirme(1) sokulur (Q199(1) rc yakalama + fail-closed dal)",
     _yalniz_sablon(_sok1)),
    ("M2 sertlestirme(2) sokulur (2026-08-20 `else` dali + payda)",
     _yalniz_sablon(_sok2)),
    ("M3 IKISI BIRDEN sokulur (= canli repolarda yasayan surum)",
     _yalniz_sablon(_sapik)),
    ("M4 POZITIF KONTROL sokumu: gercek sizinti dali olduruluyor",
     _yalniz_sablon(lambda s: s.replace('if [ -n "$BAD" ]; then', "if false; then", 1))),
    ("M5 DOGUM YUZEYI sokumu: init_project pre-commit'i URETMEZ",
     lambda sab, ini: (sab, ini.replace(_URETIM_CAGRISI, "", 1))),
]


def main() -> int:
    print("=" * 78)
    print("precommit_kopya_surum_esligi — SABLON sertlesti != KOPYA sertlesti (Q245)")
    print("=" * 78)
    if not SH:
        print("[DOGRULANAMADI] sh/bash bulunamadi — korpus kosulamadi (sessiz gecme YOK)")
        return 2
    if not SABLON.is_file() or not INIT_PROJECT.is_file():
        print("[DOGRULANAMADI] sablon/jenerator bulunamadi: %s | %s" % (SABLON, INIT_PROJECT))
        return 2

    ham_sablon = SABLON.read_text(encoding="utf-8")
    ham_init = INIT_PROJECT.read_text(encoding="utf-8")

    # KURULUM CAPASI: taban turetilemiyorsa SAYI BASMA (exit 2).
    try:
        _sapik(ham_sablon)
    except YamaTutmadi as e:
        print("[TABAN URETILEMEDI] %s — sablon elden gecmis olabilir; capayi guncelle. "
              "Hicbir sayi basilmadi." % e)
        return 2
    if _URETIM_CAGRISI not in ham_init:
        print("[TABAN URETILEMEDI] init_project.py'de pre-commit uretim cagrisi capasi YOK "
              "(M5 kurulamaz). Hicbir sayi basilmadi.")
        return 2

    sonuc = senaryolar(ham_sablon, ham_init)
    kirik = [(a, d) for a, ok, d in sonuc if not ok]
    for ad, ok, detay in sonuc:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok:
            print("         gorulen: %s" % detay)
    print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

    print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
    mut_kirik, yama_kirik = [], []
    for ad, mut in MUTASYONLAR:
        try:
            m_sab, m_ini = mut(ham_sablon, ham_init)
        except Exception as e:
            print("  [YAMA TUTMADI] %s (%s: %s)" % (ad, type(e).__name__, e))
            yama_kirik.append(ad)
            continue
        if (m_sab, m_ini) == (ham_sablon, ham_init):
            print("  [YAMA TUTMADI] %s (kaynak degismedi — capa bayat)" % ad)
            yama_kirik.append(ad)
            continue
        try:
            m_res = senaryolar(m_sab, m_ini)
        except BaseException as e:
            # ⛔ KURULAMADI != KACTI: aracin bozulmasini korpusun basarisi sayma.
            print("  [KURULAMADI] %s -> %s: %s" % (ad, type(e).__name__, e))
            yama_kirik.append(ad)
            continue
        kacan = [a for a, ok, _ in m_res if not ok]
        # S2/S4 SAPIK tabani olcer; mutasyon onu DEGISTIRMEZ (taban pristine'den turetilir)
        # -> durumlari mutasyonun ayirt ediciligi hakkinda bilgi TASIMAZ.
        kacan_gecerli = [a for a in kacan if not a.startswith(("S2", "S4"))]
        yakalandi = bool(kacan_gecerli)
        print("  [%s] %s" % ("YAKALANDI" if yakalandi else "KACTI", ad))
        if yakalandi:
            print("         kiran senaryo(lar): %s" % ", ".join(kacan_gecerli[:4]))
        else:
            mut_kirik.append(ad)

    print("\n" + "=" * 78)
    if kirik or mut_kirik or yama_kirik:
        if kirik:
            print("FAIL — senaryo: %s" % ", ".join(a for a, _ in kirik))
        if mut_kirik:
            print("FAIL — mutasyon KACTI: %s" % ", ".join(mut_kirik))
        if yama_kirik:
            print("FAIL — mutasyon yamasi UYMADI/KURULAMADI: %s" % ", ".join(yama_kirik))
        return 1
    print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(MUTASYONLAR)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
