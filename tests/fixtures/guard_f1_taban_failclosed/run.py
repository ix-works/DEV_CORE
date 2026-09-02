#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CORE CI `behavior-surface` (F1): olcum COKERSE / taban ERISILEMEZSE "temiz" SAYILMAZ.

KOK (Q199(2)): `.github/workflows/project-guard.yml` soyle yaziliydi:

    list_touched() { git diff --name-only "$1" "$2" -- $SURFACE 2>/dev/null || true; }

`2>/dev/null` SEBEBI, `|| true` de rc'yi (128) YUTUYORDU => `TOUCHED=''` =>
`[ -n "$TOUCHED" ]` YANLIS => hukum ***"OK — davranis-yuzeyi dokunusu yok"*** =>
F1 (main'e DOGRUDAN push davranis-yuzeyine dokunamaz) SESSIZCE ACILIYORDU.
Yani *"eslesme yok"* ile *"komut coktu"* AYIRT EDILEMIYORDU.

OLCULMUS TETIK: main'e **force-push** sonrasi `github.event.before` ERISILEMEZ bir
objedir (`fetch-depth: 0` erisilemeyeni GETIRMEZ) => `git diff $BEFORE $AFTER` rc=128
`fatal: bad object`. Bu korpus o force-push'u SAHTE SHA ile degil, gercek bir bare
origin'e gercek `push --force` atarak ve `clone --no-local` ile taze checkout alarak
uretir (yerel klon hardlink'le ERISILEMEZ objeleri de tasirdi => vektor sahte olurdu).

FIX (KULLANICI KARARI = secenek (c), 2026-09-02):
  (1) taban ERISILEBILIR mi ONCE olculur (`git cat-file -e`),
  (2) erisilemezse taban `$AFTER^` olur ve bu **GORUNUR** bir `::notice::` ile bildirilir
      (pencere daralir: yalniz son commit) — force-push tek basina KIRMIZI YAPMAZ,
  (3) `$AFTER^` de yoksa (kok commit / sig klon) artik gercekten bakamadik =>
      `::error::` + `exit 1` (fail-closed son care),
  (4) `git diff` ve `git rev-list` rc'leri AYRI yakalanir; stderr YUTULMAZ ve TOUCHED'e
      KARISTIRILMAZ (git'in kendi metni log'a akar; `2>&1` rc=0'daki bir uyariyi
      "dokunuldu" sanma riski dogururdu — Q199(1)'de de ayni gerekce ile reddedildi).
  (5) `olcemedim`/`taban_belirle`/`list_touched` `$( )` ICINDE CAGRILAMAZ: `exit 1`
      yalniz alt-kabugu oldurur **ve** `::error::` metni yakalanip KAYBOLUR (olculdu)
      => sonuclarini GLOBAL degiskene yazarlar.

(-) Kontrol grubu (AYNI dosyada ZATEN dogru yazilmis kardes): `MERGED_PR=$(gh api …
|| echo 0)` — yokluk *"temiz"* degil ***"suclu"*** demektir. TAKLIT edildi, BOZULMADI;
S5 tam da onun hala calistigini olcer.

KAPSAM: bu is akisi `on: workflow_call`'dir — DEV_CORE'un KENDI push'unda KOSMAZ.
Cagiranlari `claude/workflows/guard.template.yml`den uretilen proje `guard.yml`leridir
(`push: branches:[main]` + `pull_request`), hepsi `@main`e sabitli => fix bir sonraki
kosuda otomatik yayilir.

  S1   * BILINEN-BOZUK: force-push + yuzey dokunuldu -> ::notice:: yedek taban + ::error:: rc 1
  S2   * POZITIF KONTROL: normal push + yuzey dokunuldu -> DAVRANIS BIREBIR ESKISI (rc 1)
  S3   FP CAPASI: normal push + yuzey TEMIZ -> rc 0, uydurma-kirmizi YOK, ::notice:: YOK
  S4   * FP CAPASI-2: force-push ama yuzey TEMIZ -> rc 0 + GORUNUR ::notice::
       (secenek (b) "her force-push kirmizi"nin REDDEDILDIGININ capasi)
  S5   * 3. BAGLAM: squash-merge yolu (PARENTS<3 + MERGED_PR>0) -> rc 0, "MERGED PR'dan geldi"
  S6   * 3. BAGLAM: kok commit — $AFTER^ de YOK -> fail-closed son care (rc 1, ÖLÇÜLEMEDİ)
  S7   PR yolu FP: base erisilebilir + yuzey temiz -> rc 0, "dokunusu yok"
  S7b  PR yolu POZITIF: yuzey dokunuldu -> ::warning:: ama rc 0 (PR yolu BLOKLAMAZ - sozlesme)
  S8   PR yolu: base.sha ERISILEMEZ (base force-push'lanmis) -> yedek taban + ::warning::
  S9   * TARIHI TABAN: S1 vektoru ESKI desende -> rc 0 + sessiz "OK" (kusur yeniden uretilir)
  S10  * 3. BAGLAM: gate'in KENDI pathspec'i bozuk -> rc 1 + git'in KENDI `fatal:` metni GORUNUR
  S10t TARIHI TABAN: ayni bozuk pathspec ESKI desende -> rc 0 + sessiz "OK"
  S11  KAPSAM CAPASI: merge-commit push (PARENTS>=3) -> blok ATLANIR (degismedi)
  S12  KAPSAM CAPASI: feature dal push (REF != main) -> blok ATLANIR (degismedi)
  S13  KAPSAM CAPASI: BEFORE=0000… (ilk push) -> blok ATLANIR (degismedi)
  M1-M6  fix'in HER katmani AYRI sokulur -> korpus KIRMIZI olmali

Kosum: python tests/fixtures/guard_f1_taban_failclosed/run.py   (exit 0 = PASS,
       exit 1 = vektor dustu, exit 2 = ALET GECERSIZ / DOGRULANAMADI)
"""
from __future__ import annotations

import os
import re
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
CORE = HERE.parents[2]
AKIS = CORE / ".github" / "workflows" / "project-guard.yml"

BASH = shutil.which("bash")

SIFIR = "0000000000000000000000000000000000000000"


# ══════════════════════════════════════════════════════════════════════════════
# 0 — IS AKISI DOSYASINDAN `run:` GOVDESINI CIKAR  (kod != kablolama)
# ══════════════════════════════════════════════════════════════════════════════
# ⛔ Betik literal olarak buraya KOPYALANMAZ: kopya ikinci bir gercek olur ve
# is akisi degistiginde korpus sessizce ESKI metni olcmeye devam eder.
# ⛔ `import yaml` YOK: repo pyyaml tasimaz (core-ci yalniz requests/urllib3/
# python-dotenv kurar) => CI'da COKERDI. Elde, dar ve kontrollu ayristirma.
def govde_cikar(metin: str) -> str:
    satirlar = metin.splitlines()
    try:
        i = next(k for k, s in enumerate(satirlar) if s.strip() == "behavior-surface:")
    except StopIteration:
        raise AssertionError("`behavior-surface:` job'u bulunamadi: %s" % AKIS)
    try:
        j = next(k for k in range(i, len(satirlar)) if satirlar[k].strip() == "run: |")
    except StopIteration:
        raise AssertionError("`behavior-surface` altinda `run: |` bulunamadi")
    girinti = len(satirlar[j]) - len(satirlar[j].lstrip(" ")) + 2
    govde: list[str] = []
    for s in satirlar[j + 1:]:
        if not s.strip():
            govde.append("")
            continue
        if len(s) - len(s.lstrip(" ")) < girinti:
            break
        govde.append(s[girinti:])
    if not govde:
        raise AssertionError("`run:` govdesi BOS cikti (girinti cozumlemesi bozuk)")
    return "\n".join(govde) + "\n"


# ══════════════════════════════════════════════════════════════════════════════
# 1 — TARIHI TABAN: fix BUGUNKU kaynaktan SOKULEREK turetilir
# ══════════════════════════════════════════════════════════════════════════════
# ⛔ `git show <sha>:` KULLANILMAZ — pinli SHA sig klonda cozulmez ve merge sonrasi
# kayar (2026-08-29'da CI'i iki kez kirdi). Her sokum ADET kontrollu: capa bayatlarsa
# senaryo "KURULAMADI" der, sessizce PASS OLMAZ.
_SOKUMLER: list[tuple[str, str, object, int]] = [
    ("yardimci blok -> eski tek satirlik list_touched",
     r"(?ms)^([ \t]*)# ── Q199② FAIL-CLOSED ÖLÇÜM \(2026-09-02\) — BAŞLANGIÇ.*?"
     r"^[ \t]*# ── Q199② FAIL-CLOSED ÖLÇÜM — BİTİŞ[^\n]*\n",
     lambda m: ('{0}list_touched() {{\n'
                '{0}  git diff --name-only "$1" "$2" -- $SURFACE 2>/dev/null || true\n'
                '{0}}}\n').format(m.group(1)), 1),
    ("PR yolu cagri yeri",
     r'(?m)^([ \t]*)taban_belirle "\$BASE" "PR base\.sha"\n[ \t]*list_touched "\$TABAN" "\$AFTER"\n',
     lambda m: '%sTOUCHED=$(list_touched "$BASE" "$AFTER")\n' % m.group(1), 1),
    ("push yolu cagri yeri",
     r'(?m)^([ \t]*)taban_belirle "\$BEFORE" "github\.event\.before"\n[ \t]*list_touched "\$TABAN" "\$AFTER"\n',
     lambda m: '%sTOUCHED=$(list_touched "$BEFORE" "$AFTER")\n' % m.group(1), 1),
    ("parent sayimi fail-closed'i",
     r"(?ms)^([ \t]*)# Parent sayımı da bir ÖLÇÜMDÜR.*?"
     r"^[ \t]*PARENTS=\$\(printf '%s' \"\$RL_OUT\" \| wc -w\)\n",
     lambda m: '%sPARENTS=$(git rev-list --parents -n 1 "$AFTER" | wc -w)\n' % m.group(1), 1),
    ("PR yolu 'dokunusu yok' satirinin PAYDASI",
     r'echo "OK — davranış-yüzeyi dokunuşu yok \(taban: \$TABAN_ETIKET\)"',
     'echo "OK — davranış-yüzeyi dokunuşu yok"', 1),
    ("kapanis satirinin PAYDASI",
     r'(?ms)^([ \t]*)# ⚠ PAYDA:.*?^[ \t]*echo "OK — F1 kontrolü tamamlandı[^\n]*\n',
     lambda m: '%secho "OK"\n' % m.group(1), 1),
]


def fix_sok(s: str) -> str:
    """Q199(2) fix'inin TAMAMINI geri alir = 2026-09-02 oncesi is akisi."""
    for ad, desen, yerine, adet in _SOKUMLER:
        s, n = re.subn(desen, yerine, s)
        if n != adet:
            raise AssertionError("sokum capasi bayat (%s): beklenen %d, bulunan %d" % (ad, adet, n))
    return s


def surface_boz(s: str) -> str:
    """Gate'in KENDI pathspec listesini gecersiz magic'e cevirir (S10 vektoru)."""
    capa = "SURFACE='CLAUDE.md "
    if capa not in s:
        raise AssertionError("SURFACE capasi bulunamadi")
    return s.replace(capa, "SURFACE=':(gecersizsihir)CLAUDE.md ", 1)


# ══════════════════════════════════════════════════════════════════════════════
# 2 — GERCEK GIT DEPOLARI (senaryo basina BIR kez kurulur, tum kosumlarda paylasilir)
# ══════════════════════════════════════════════════════════════════════════════
def _sil(d: Path) -> None:
    """Sentetik depoyu GERCEKTEN siler.

    ⚠ Duz `rmtree(ignore_errors=True)` Windows'ta SESSIZCE basarisiz olur: git
    `.git/objects/**` altini SALT-OKUNUR yazar => kalinti `%TEMP%`de YIGAR.
    """
    def _ac(func, path, _exc):           # noqa: ANN001 - shutil geri cagirma imzasi
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass

    kw = {"onexc": _ac} if sys.version_info >= (3, 12) else {"onerror": _ac}
    try:
        shutil.rmtree(d, **kw)           # type: ignore[arg-type]
    except Exception:
        shutil.rmtree(d, ignore_errors=True)


def _g(d: Path, *a: str, kontrol: bool = True) -> str:
    r = subprocess.run(["git", *a], cwd=str(d), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if kontrol and r.returncode != 0:
        raise AssertionError("git %s -> rc=%s\n%s%s" % (" ".join(a), r.returncode,
                                                        r.stdout, r.stderr))
    return r.stdout.strip()


def _origin(kok: Path) -> Path:
    o = kok / "origin"
    o.mkdir(parents=True)
    _g(o, "init", "--bare", "-q", "-b", "main")
    return o


def _work(kok: Path) -> Path:
    w = kok / "work"
    w.mkdir(parents=True)
    _g(w, "init", "-q", "-b", "main")
    _g(w, "config", "user.email", "t@t")
    _g(w, "config", "user.name", "t")
    _g(w, "config", "commit.gpgsign", "false")
    return w


def _c(d: Path, dosya: str, icerik: str, mesaj: str) -> str:
    p = d / dosya
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(icerik, encoding="utf-8")
    _g(d, "add", "-A")
    _g(d, "commit", "-q", "-m", mesaj)
    return _g(d, "rev-parse", "HEAD")


def _ci(kok: Path, origin: Path, dal: str = "main") -> Path:
    """CI checkout'u: `actions/checkout@v5` + `fetch-depth: 0` esdegeri.

    ⛔ `--no-local` SART: yerel klon hardlink'le ERISILEMEZ objeleri de tasir ve
    force-push vektorunu SAHTE yapardi (taban 'erisilemez' olmazdi).
    """
    _g(kok, "clone", "--no-local", "-q", "--branch", dal, str(origin), "ci")
    return kok / "ci"


# ── senaryo kurucular ─────────────────────────────────────────────────────────
YUZEY = "CLAUDE.md"          # SURFACE listesinin ilk ogesi
DISI = "docs/notlar.md"      # SURFACE'te OLMAYAN dosya


def kur_normal_push(kok: Path, yuzey: bool):
    o, w = _origin(kok), _work(kok)
    _g(w, "remote", "add", "origin", str(o))
    r = _c(w, "README.md", "r1\n", "R")
    _g(w, "push", "-q", "origin", "main")
    s = _c(w, YUZEY if yuzey else DISI, "degisti\n", "S")
    _g(w, "push", "-q", "origin", "main")
    return _ci(kok, o), {"EVENT": "push", "REF": "refs/heads/main",
                         "BEFORE": r, "AFTER": s}


def kur_force_push(kok: Path, yuzey: bool):
    o, w = _origin(kok), _work(kok)
    _g(w, "remote", "add", "origin", str(o))
    r = _c(w, "README.md", "r1\n", "R")
    _g(w, "push", "-q", "origin", "main")
    x = _c(w, "docs/gecici.md", "x\n", "X (force-push ile SILINECEK)")
    _g(w, "push", "-q", "origin", "main")
    _g(w, "reset", "--hard", "-q", r)
    s = _c(w, YUZEY if yuzey else DISI, "degisti\n", "S (yeniden yazilan tepe)")
    _g(w, "push", "-q", "--force", "origin", "main")
    # BEFORE = X: origin'de artik ERISILEMEZ; `--no-local` klon onu GETIRMEZ.
    return _ci(kok, o), {"EVENT": "push", "REF": "refs/heads/main",
                         "BEFORE": x, "AFTER": s}


def kur_force_push_kok(kok: Path):
    """Force-push + AFTER'in PARENT'i da YOK (kok commit) -> son care dali."""
    o, w = _origin(kok), _work(kok)
    _g(w, "remote", "add", "origin", str(o))
    x = _c(w, "README.md", "r1\n", "X (tek commit, SILINECEK)")
    _g(w, "push", "-q", "origin", "main")
    _g(w, "checkout", "-q", "--orphan", "yeni")
    _g(w, "rm", "-rq", "--cached", ".")
    for p in w.iterdir():
        if p.name != ".git":
            _sil(p) if p.is_dir() else p.unlink()
    s = _c(w, YUZEY, "yepyeni\n", "S (koksuz yeni tepe)")
    _g(w, "branch", "-M", "main")
    _g(w, "push", "-q", "--force", "origin", "main")
    return _ci(kok, o), {"EVENT": "push", "REF": "refs/heads/main",
                         "BEFORE": x, "AFTER": s}


def kur_merge_commit(kok: Path):
    o, w = _origin(kok), _work(kok)
    _g(w, "remote", "add", "origin", str(o))
    r = _c(w, "README.md", "r1\n", "R")
    _g(w, "push", "-q", "origin", "main")
    _g(w, "checkout", "-q", "-b", "f")
    _c(w, YUZEY, "dal degisikligi\n", "F")
    _g(w, "checkout", "-q", "main")
    _g(w, "merge", "-q", "--no-ff", "f", "-m", "merge f")
    m = _g(w, "rev-parse", "HEAD")
    _g(w, "push", "-q", "origin", "main")
    return _ci(kok, o), {"EVENT": "push", "REF": "refs/heads/main",
                         "BEFORE": r, "AFTER": m}


def kur_feature_dal(kok: Path):
    o, w = _origin(kok), _work(kok)
    _g(w, "remote", "add", "origin", str(o))
    r = _c(w, "README.md", "r1\n", "R")
    _g(w, "push", "-q", "origin", "main")
    _g(w, "checkout", "-q", "-b", "ozellik")
    s = _c(w, YUZEY, "dalda degisti\n", "S")
    _g(w, "push", "-q", "origin", "ozellik")
    return _ci(kok, o, dal="ozellik"), {"EVENT": "push", "REF": "refs/heads/ozellik",
                                        "BEFORE": r, "AFTER": s}


def kur_before_sifir(kok: Path):
    o, w = _origin(kok), _work(kok)
    _g(w, "remote", "add", "origin", str(o))
    s = _c(w, YUZEY, "ilk\n", "S (ilk push)")
    _g(w, "push", "-q", "origin", "main")
    return _ci(kok, o), {"EVENT": "push", "REF": "refs/heads/main",
                         "BEFORE": SIFIR, "AFTER": s}


def kur_pr(kok: Path, yuzey: bool, base_erisilir: bool = True):
    """`pull_request`: AFTER = refs/pull/N/merge tepesi (birlesmis agac),
    `$AFTER^` = 1. parent = BASE dalinin tepesi."""
    o, w = _origin(kok), _work(kok)
    _g(w, "remote", "add", "origin", str(o))
    r = _c(w, "README.md", "r1\n", "R")
    _g(w, "push", "-q", "origin", "main")
    b1 = _c(w, "docs/temel.md", "b1\n", "B1 (PR acildiginda base tepesi)")
    _g(w, "push", "-q", "origin", "main")

    # PR dali: erisilebilir vakada B1'den, erisilemez vakada R'den dallanir
    # (yoksa B1, PR dali uzerinden yine ERISILEBILIR olurdu => vektor sahte).
    _g(w, "checkout", "-q", "-b", "prhead", b1 if base_erisilir else r)
    _c(w, YUZEY if yuzey else DISI, "PR degisikligi\n", "PR head")

    if base_erisilir:
        base_tepe = b1
    else:
        _g(w, "checkout", "-q", "main")
        _g(w, "reset", "--hard", "-q", r)
        base_tepe = _c(w, "docs/temel.md", "b2\n", "B2 (base FORCE-PUSH'landi)")
        _g(w, "push", "-q", "--force", "origin", "main")

    _g(w, "checkout", "-q", "-b", "prmerge", base_tepe)
    _g(w, "merge", "-q", "--no-ff", "prhead", "-m", "Merge PR")
    m = _g(w, "rev-parse", "HEAD")
    _g(w, "push", "-q", "origin", "prmerge")
    ci = _ci(kok, o, dal="prmerge")
    return ci, {"EVENT": "pull_request", "REF": "refs/pull/1/merge",
                "BEFORE": "", "AFTER": m, "BASE": b1}


# ══════════════════════════════════════════════════════════════════════════════
# 3 — KOSUM  (GitHub Actions varsayilan kabugu: `bash -e {0}`)
# ══════════════════════════════════════════════════════════════════════════════
def _gh_stub(kok: Path) -> Path:
    b = kok / "stubbin"
    b.mkdir(parents=True, exist_ok=True)
    (b / "gh").write_text("#!/bin/sh\nprintf '%s\\n' \"${Q199_GH_MERGED:-0}\"\n",
                          encoding="utf-8", newline="\n")
    os.chmod(b / "gh", 0o755)
    return b


def kos(betik: str, ci: Path, ortam: dict, stub: Path, gh_merged: str = "0"):
    """-> (rc, stdout+stderr).  stderr AYRI TOPLANMAZ cunku F1'in sozlesmesi
    'sebep KULLANICIYA ULASSIN'dir; Actions log'unda ikisi tek akistir."""
    f = ci.parent / "adim.sh"
    f.write_text(betik, encoding="utf-8", newline="\n")
    env = {**os.environ,
           "PATH": str(stub) + os.pathsep + os.environ.get("PATH", ""),
           "Q199_GH_MERGED": gh_merged,
           "EVENT": "", "BEFORE": "", "AFTER": "", "REF": "", "BASE": "",
           "REPO": "orgadi/repoadi", "GH_TOKEN": "sahte",
           "PYTHONIOENCODING": "utf-8", "LC_ALL": "C.UTF-8"}
    env.update({k: str(v) for k, v in ortam.items()})
    r = subprocess.run([BASH, "-e", str(f)], cwd=str(ci), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=env)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# ══════════════════════════════════════════════════════════════════════════════
# 4 — SENARYOLAR
# ══════════════════════════════════════════════════════════════════════════════
NOTICE = "::notice::F1 TABANI DEĞİŞTİ"
ERR_OLC = "::error::F1 ÖLÇÜLEMEDİ"
ERR_F1 = "::error::main'e DOĞRUDAN push davranış-yüzeyine dokunuyor"
OK_TEMIZ = "OK — davranış-yüzeyi dokunuşu yok"
OK_SON = "OK — F1 kontrolü tamamlandı"
MERGED = "MERGED PR'dan geldi"
UYARI_PR = "::warning::PR davranış-yüzeyi dosyası içeriyor"
TABAN_SATIRI = "F1 tabanı:"


def senaryolar(betik: str, depo: dict, stub: Path, tarihi: bool = True):
    out: list[tuple[str, bool, str]] = []

    def ekle(ad, kosul, rc=None, o=""):
        out.append((ad, bool(kosul), "rc=%s cikti=%r" % (rc, o[-300:])))

    def K(ad):
        return depo[ad]

    # --- S1 * BILINEN-BOZUK -----------------------------------------------------
    ci, env = K("force_yuzey")
    rc, o = kos(betik, ci, env, stub)
    ekle("S1 * force-push + yuzey dokunuldu -> yedek taban GORUNUR + F1 BLOKLUYOR",
         rc == 1 and NOTICE in o and YUZEY in o and ERR_F1 in o, rc, o)

    # --- S2 * POZITIF KONTROL ---------------------------------------------------
    ci, env = K("normal_yuzey")
    rc, o = kos(betik, ci, env, stub)
    ekle("S2 * POZITIF KONTROL: normal push + yuzey -> rc 1 (davranis BIREBIR eskisi, yedek tabana DUSMEDI)",
         rc == 1 and ERR_F1 in o and NOTICE not in o
         and (TABAN_SATIRI + " github.event.before") in o, rc, o)

    # --- S3 FP CAPASI -----------------------------------------------------------
    ci, env = K("normal_temiz")
    rc, o = kos(betik, ci, env, stub)
    ekle("S3 FP capasi: normal push + yuzey TEMIZ -> rc 0, uydurma-kirmizi YOK",
         rc == 0 and OK_SON in o and "::error::" not in o and NOTICE not in o
         and (TABAN_SATIRI + " github.event.before") in o, rc, o)

    # --- S4 * FP CAPASI-2 (secenek (b) reddinin capasi) -------------------------
    # ⚠ HUKUM ile GORUNURLUK AYRI DEGISMEZLERDIR, ayri vektorle olculurler: birlestirilseydi
    # "yedek taban var ama SESSIZ" mutasyonu (M5) ile "yedek taban YOK" mutasyonu (M3)
    # ayni capayla kesilirdi ve kullanicinin sart kostugu GORUNURLUK bedava gecerdi.
    ci, env = K("force_temiz")
    rc, o = kos(betik, ci, env, stub)
    ekle("S4a * HUKUM: force-push ama yuzey TEMIZ -> rc 0 (force-push tek basina KIRMIZI DEGIL; "
         "secenek (b)'nin reddinin capasi)",
         rc == 0 and "::error::" not in o and OK_SON in o, rc, o)
    ekle("S4b * GORUNURLUK: ayni kosumda yedek taban ::notice:: ile BILDIRILIYOR "
         "(hangi tabanla olculdugu insana gorunur)",
         NOTICE in o and "$AFTER^" in o, rc, o)

    # --- S5 * 3. BAGLAM: squash-merge yolu (MERGED_PR emsali BOZULMADI) ---------
    ci, env = K("normal_yuzey")
    rc, o = kos(betik, ci, env, stub, gh_merged="1")
    ekle("S5 * 3.BAGLAM squash-merge (MERGED_PR>0) -> rc 0, 'MERGED PR'dan geldi' (dogru emsal AYAKTA)",
         rc == 0 and MERGED in o and "::error::" not in o, rc, o)

    # --- S6 * 3. BAGLAM: kok commit, $AFTER^ de YOK -> son care ------------------
    ci, env = K("force_kok")
    rc, o = kos(betik, ci, env, stub)
    ekle("S6 * 3.BAGLAM kok commit ($AFTER^ YOK) -> fail-closed son care rc 1 + 'ÖLÇÜLEMEDİ'",
         rc == 1 and ERR_OLC in o and "karşılaştırma tabanı YOK" in o, rc, o)

    # --- S7 / S7b / S8  PR yolu --------------------------------------------------
    ci, env = K("pr_temiz")
    rc, o = kos(betik, ci, env, stub)
    ekle("S7 PR yolu FP: base erisilebilir + temiz -> rc 0 + 'dokunusu yok'",
         rc == 0 and OK_TEMIZ in o and (TABAN_SATIRI + " PR base.sha") in o
         and "::error::" not in o, rc, o)

    ci, env = K("pr_yuzey")
    rc, o = kos(betik, ci, env, stub)
    ekle("S7b PR yolu POZITIF: yuzey dokunuldu -> ::warning:: ama rc 0 (PR yolu BLOKLAMAZ)",
         rc == 0 and UYARI_PR in o and YUZEY in o, rc, o)

    ci, env = K("pr_base_erisilemez")
    rc, o = kos(betik, ci, env, stub)
    ekle("S8 PR yolu: base.sha ERISILEMEZ -> yedek taban GORUNUR + dokunus YAKALANDI",
         rc == 0 and NOTICE in o and UYARI_PR in o and YUZEY in o, rc, o)

    # --- S10 * 3. BAGLAM: gate'in KENDI pathspec'i bozuk -------------------------
    try:
        bozuk = surface_boz(betik)
    except AssertionError as e:
        ekle("S10 * gate'in KENDI pathspec'i bozuk -> rc 1 + git'in metni GORUNUR",
             False, "KURULAMADI", str(e))
    else:
        ci, env = K("normal_yuzey")
        rc, o = kos(bozuk, ci, env, stub)
        ekle("S10 * 3.BAGLAM gate'in KENDI pathspec'i bozuk -> rc 1 + 'ÖLÇÜLEMEDİ' + git'in KENDI 'fatal:' metni GORUNUR",
             rc == 1 and ERR_OLC in o and "git diff rc=" in o and "fatal:" in o, rc, o)

    # --- S11 / S12 / S13  KAPSAM CAPALARI (bilincli no-op yollari) --------------
    ci, env = K("merge_commit")
    rc, o = kos(betik, ci, env, stub)
    ekle("S11 kapsam: merge-commit push (PARENTS>=3) -> blok ATLANIR, rc 0",
         rc == 0 and OK_SON in o and TABAN_SATIRI not in o and "::error::" not in o, rc, o)

    ci, env = K("feature_dal")
    rc, o = kos(betik, ci, env, stub)
    ekle("S12 kapsam: feature dal push (REF != main) -> blok ATLANIR, rc 0",
         rc == 0 and OK_SON in o and TABAN_SATIRI not in o and "::error::" not in o, rc, o)

    ci, env = K("before_sifir")
    rc, o = kos(betik, ci, env, stub)
    ekle("S13 kapsam: BEFORE=0000… (ilk push) -> blok ATLANIR, rc 0",
         rc == 0 and OK_SON in o and TABAN_SATIRI not in o and "::error::" not in o, rc, o)

    # --- S9 / S10t  TARIHI TABAN (mutant altinda ANLAMSIZ: taban zaten sokuk) ---
    if tarihi:
        try:
            eski = fix_sok(betik)
        except AssertionError as e:
            ekle("S9 * TARIHI TABAN: eski desende sessiz 'OK' (kusur yeniden uretilir)",
                 False, "KURULAMADI", str(e))
            ekle("S10t TARIHI TABAN: bozuk pathspec eski desende sessiz 'OK'",
                 False, "KURULAMADI", str(e))
        else:
            # ⚠ PUSH yolunda eski desenin sessizligi CIPLAK "OK"tur: dokunus bulunmayinca
            # push dali HICBIR SEY basmaz, adim yalniz kapanis satiriyla biter. Kusurun
            # "payda" yarisi tam da buydu — bu yuzden esitlik (`== "OK"`) araniyor,
            # icerme degil.
            ci, env = K("force_yuzey")
            rc, o = kos(eski, ci, env, stub)
            ekle("S9 * TARIHI TABAN: AYNI force-push vektorunde ESKI desen rc 0 + CIPLAK 'OK' "
                 "=> 'eskiden F1 SESSIZCE aciliyordu' KANIT",
                 rc == 0 and o.strip() == "OK" and "::error::" not in o and NOTICE not in o, rc, o)

            ci, env = K("normal_yuzey")
            rc, o = kos(surface_boz(eski), ci, env, stub)
            ekle("S10t TARIHI TABAN: gate'in KENDI pathspec'i bozukken ESKI desen rc 0 + CIPLAK 'OK' "
                 "(git'in 'fatal:' metni de YUTULMUS)",
                 rc == 0 and o.strip() == "OK" and "fatal:" not in o, rc, o)

            # PR yolunda ise eski desen kaydin BIREBIR sikayet ettigi YANLIS CUMLEYI kurar.
            ci, env = K("pr_base_erisilemez")
            rc, o = kos(eski, ci, env, stub)
            ekle("S8t * TARIHI TABAN (PR yolu): erisilemez base.sha -> ESKI desen "
                 "'OK — davranış-yüzeyi dokunuşu yok' diyor OYSA CLAUDE.md DEGISMIS (sahte-temiz)",
                 rc == 0 and OK_TEMIZ in o and YUZEY not in o, rc, o)

    return out


# ══════════════════════════════════════════════════════════════════════════════
# 5 — MUTASYONLAR: fix'in HER katmani AYRI kesilir
# ══════════════════════════════════════════════════════════════════════════════
# ⛔ Tek noktali sokum yetmez: savunma-derinliginde bir katman digerini maskeler.
# ⛔ Mutant GERCEK dosyaya YAZILMAZ — bellekte donusturulup gecici depoya kosulur.
def _tek(desen, yerine, adet=1):
    def _uygula(s: str) -> str:
        s2, n = re.subn(desen, yerine, s)
        if n != adet:
            raise AssertionError("mutasyon capasi bayat: beklenen %d, bulunan %d" % (adet, n))
        return s2
    return _uygula


MUTASYONLAR = [
    ("M1 TAM sokum: Q199(2) fix'i butunuyle geri alinir (2026-09-02 oncesi)", fix_sok),
    ("M2 yalniz `git diff` rc'si YUTULUR (`|| LT_RC=$?` -> `|| true`)",
     _tek(r'\) \|\| LT_RC=\$\?', ") || true")),
    ("M3 YEDEK TABAN sokulur ($AFTER^ dali kalkar; erisilemez taban dogrudan son careye duser)",
     _tek(r'(?ms)^[ \t]*if erisilir "\$\{AFTER\}\^"; then\n.*?^[ \t]*fi\n', "")),
    ("M4 POZITIF KONTROL sokumu: `[ -n \"$TOUCHED\" ]` -> `false` (her iki yolda)",
     _tek(r'if \[ -n "\$TOUCHED" \]; then', "if false; then", 2)),
    ("M5 GORUNURLUK sokumu: yedek tabani bildiren `::notice::` susturulur",
     _tek(r'(?m)^([ \t]*)echo "::notice::F1 TABANI DEĞİŞTİ[^\n]*\n', lambda m: "%s:\n" % m.group(1))),
    ("M6 SON CARE sokumu: `olcemedim` artik `exit 1` yerine DEVAM eder",
     _tek(r'(?m)^([ \t]*)exit 1\n([ \t]*)\}\n', lambda m: "%sreturn 0\n%s}\n" % (m.group(1), m.group(2)))),
]


# ══════════════════════════════════════════════════════════════════════════════
def main() -> int:
    print("=" * 78)
    print("guard_f1_taban_failclosed — F1 olcumu cokerse/taban erisilemezse 'temiz' SAYILMAZ")
    print("=" * 78)
    if not BASH:
        print("[DOGRULANAMADI] bash bulunamadi — korpus kosulamadi (sessiz gecme YOK)")
        return 2
    if not AKIS.is_file():
        print("[DOGRULANAMADI] is akisi bulunamadi: %s" % AKIS)
        return 2

    try:
        betik = govde_cikar(AKIS.read_text(encoding="utf-8"))
    except AssertionError as e:
        print("[DOGRULANAMADI] `run:` govdesi cikarilamadi: %s" % e)
        return 2

    kok = Path(tempfile.mkdtemp(prefix="q199b_"))
    try:
        stub = _gh_stub(kok)

        # ── OZ-DENETIM 1: `gh` stub'i GERCEKTEN kablolu mu? -------------------
        p = subprocess.run([BASH, "-c", 'gh api sahte/yol --jq x'],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace",
                           env={**os.environ,
                                "PATH": str(stub) + os.pathsep + os.environ.get("PATH", ""),
                                "Q199_GH_MERGED": "7"})
        if p.stdout.strip() != "7":
            print("[DOGRULANAMADI] `gh` stub'i PATH'ten cozulmedi (alinan=%r rc=%s) — "
                  "S5 olculemez, sessiz PASS YOK" % (p.stdout.strip(), p.returncode))
            return 2

        # ── OZ-DENETIM 2: sokum capalari BUGUNKU kaynakta tutuyor mu? ---------
        try:
            fix_sok(betik)
        except AssertionError as e:
            print("[DOGRULANAMADI] tarihi taban turetilemedi: %s" % e)
            return 2

        print("  [kurulum] `run:` govdesi %d satir · gh stub OK · sokum capalari OK"
              % betik.count("\n"))

        kurucular = {
            "normal_yuzey": lambda d: kur_normal_push(d, yuzey=True),
            "normal_temiz": lambda d: kur_normal_push(d, yuzey=False),
            "force_yuzey": lambda d: kur_force_push(d, yuzey=True),
            "force_temiz": lambda d: kur_force_push(d, yuzey=False),
            "force_kok": kur_force_push_kok,
            "merge_commit": kur_merge_commit,
            "feature_dal": kur_feature_dal,
            "before_sifir": kur_before_sifir,
            "pr_temiz": lambda d: kur_pr(d, yuzey=False),
            "pr_yuzey": lambda d: kur_pr(d, yuzey=True),
            "pr_base_erisilemez": lambda d: kur_pr(d, yuzey=True, base_erisilir=False),
        }
        depo: dict = {}
        for ad, f in kurucular.items():
            d = kok / ad
            d.mkdir(parents=True)
            try:
                depo[ad] = f(d)
            except AssertionError as e:
                print("[DOGRULANAMADI] senaryo deposu kurulamadi (%s): %s" % (ad, e))
                return 2

        # ── OZ-DENETIM 3: 'erisilemez taban' iddiasi GERCEKTEN dogru mu? ------
        #    (Kurulum yanlissa tum force-push vektorleri sahte olurdu.)
        for ad in ("force_yuzey", "force_temiz", "force_kok"):
            ci, env = depo[ad]
            r = subprocess.run(["git", "cat-file", "-e", env["BEFORE"] + "^{commit}"],
                               cwd=str(ci), capture_output=True)
            if r.returncode == 0:
                print("[DOGRULANAMADI] %s: BEFORE (%s) taze checkout'ta HALA ERISILEBILIR — "
                      "force-push vektoru SAHTE olurdu" % (ad, env["BEFORE"][:12]))
                return 2
        ci, env = depo["pr_base_erisilemez"]
        r = subprocess.run(["git", "cat-file", "-e", env["BASE"] + "^{commit}"],
                           cwd=str(ci), capture_output=True)
        if r.returncode == 0:
            print("[DOGRULANAMADI] pr_base_erisilemez: BASE hala erisilebilir — vektor SAHTE")
            return 2
        print("  [kurulum] erisilemezlik OZ-DENETIMI: 4/4 taban taze checkout'ta YOK")

        # ── taban kosum ------------------------------------------------------
        sonuc = senaryolar(betik, depo, stub, tarihi=True)
        kirik = [(a, d) for a, ok, d in sonuc if not ok]
        for ad, ok, detay in sonuc:
            print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
            if not ok:
                print("         gorulen: %s" % detay)
        print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

        # ── mutasyonlar ------------------------------------------------------
        print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
        mut_kirik, yama_kirik = [], []
        for ad, mut in MUTASYONLAR:
            try:
                bozuk = mut(betik)
            except Exception as e:
                print("  [YAMA TUTMADI] %s (%s: %s)" % (ad, type(e).__name__, e))
                yama_kirik.append(ad)
                continue
            if bozuk == betik:
                print("  [YAMA TUTMADI] %s (kaynak degismedi — capa bayat)" % ad)
                yama_kirik.append(ad)
                continue
            try:
                m_res = senaryolar(bozuk, depo, stub, tarihi=False)
            except BaseException as e:
                # ⛔ KURULAMADI != KACTI: aracin bozulmasini korpusun basarisi sayma.
                print("  [KURULAMADI] %s -> %s: %s" % (ad, type(e).__name__, e))
                yama_kirik.append(ad)
                continue
            kacan = [a.split(" ")[0] for a, ok, _ in m_res if not ok]
            print("  [%s] %s" % ("YAKALANDI" if kacan else "KACTI", ad))
            if kacan:
                print("         kesilen senaryo kumesi: {%s}" % ", ".join(kacan))
            else:
                mut_kirik.append(ad)

        print("\n" + "=" * 78)
        if kirik or mut_kirik or yama_kirik:
            if kirik:
                print("FAIL — senaryo: %s" % ", ".join(a.split(" ")[0] for a, _ in kirik))
            if mut_kirik:
                print("FAIL — mutasyon KACTI: %s" % ", ".join(mut_kirik))
            if yama_kirik:
                print("FAIL — mutasyon yamasi UYMADI/KURULAMADI: %s" % ", ".join(yama_kirik))
            return 1
        print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(MUTASYONLAR)))
        return 0
    finally:
        _sil(kok)


if __name__ == "__main__":
    raise SystemExit(main())
