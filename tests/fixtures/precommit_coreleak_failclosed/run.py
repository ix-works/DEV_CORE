#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PROJE pre-commit: core-SIZINTI adiminin VERI TOPLAMASI cokerse "sizinti yok" saniliyordu.

KOK (Q199①): `claude/git-hooks/pre-commit.template` adim-1 soyle yaziliydi:

    BAD=$(git diff --cached --name-only -- 'core/**' … 2>/dev/null || true)
    if [ -n "$BAD" ]; then … exit 1; fi

`git diff --cached` COKERSE (bozuk/kilitli `.git/index` · bozuk pathspec magic ·
pathspec'i tanimayan git surumu · yanlis `GIT_INDEX_FILE`), `2>/dev/null` SEBEBI ve
`|| true` de rc'yi (128) YUTAR ⇒ `BAD=''` ⇒ `[ -n "$BAD" ]` YANLIS ⇒ hukum
***"sizinti yok"*** ⇒ commit GECER. Yani *"eslesme yok"* ile *"komut coktu"*
AYIRT EDILEMIYORDU.

⛔ FARK (kardes korpus `precommit_junction_failclosed` ile karistirma): O korpus adim-2'yi
(validator zinciri ATLANIYOR) olcer. BU korpus adim-1'i (core-sizinti kapisinin KENDI
olcumu COKUYOR) olcer. Ikisi AYRI kusur, AYRI dal; kardes korpusun S3'u yalniz "adim-1
hala blokluyor" FP capasidir — cokme eksenini HIC olcmez.

⭐ ASIL AGIRLASTIRICI: kapanis satiri ("[pre-commit] OK — core-sizinti kontrolu + …")
2026-08-20'de tam da *"NE kostugunu soylesin"* diye eklenmisti; taban surumde o satir
HIC YAPILMAMIS bir kontrolu RAPORLUYOR. Yani payda eklemek fail-open'i kapatmiyor.

FIX: rc AYRI yakalanir (`|| SIZ_RC=$?`; `||` listesi oldugu icin `set -e` tetiklenmez ve
rc kaybolmaz), stderr YUTULMAZ ve BAD'e KARISTIRILMAZ (hic yonlendirilmez ⇒ git'in kendi
hata metni kullaniciya akar; `2>&1` ile karistirmak rc=0'daki bir uyariyi "sizinti"
sanma riski dogururdu), rc≠0 ⇒ COKME BULGUDUR → fail-closed `exit 1` + gorunur sebep.

⚖ Kontrol grubu (bu repoda ZATEN dogru yazilmis kardes): `project-guard.yml`
`MERGED_PR=$(gh api … || echo 0)` — yokluk *"temiz"* degil ***"suclu"*** demektir.

  S1  ⭐ BILINEN-BOZUK: `.git/index` bozuk  -> gate rc 1 + gorunur sebep (taban: rc 0 + "OK")
  S2  ⭐ POZITIF KONTROL: gercek sizinti staged -> hala rc 1 + junction mesaji (sertlesme
      gercek bulguyu OLDURMEDI)
  S3  FP CAPASI: saglam + temiz depo -> rc 0, yanlis-pozitif YOK, kapanis satiri basiliyor
  S4  ⭐ 3. BAGLAM (gorev-disi): depo SAGLAM, yalniz gate'in KENDI pathspec'i bozuk
      (kaydin birebir vektoru) -> gate rc 1
  S5  UCTAN UCA: S4 kosulunda + sizinti staged iken GERCEK `git commit` -> taban surumde
      commit GECIYOR (sizinti repoya giriyor), fix'li surumde BLOKLANIYOR
  S6  STDERR GORUNURLUGU: cokmede git'in KENDI hata metni kullaniciya ulasiyor
      (`2>/dev/null` onu yutuyordu)
  S7  `set -e` CAPASI: cokmede script 128 ile sessizce olmuyor, KENDI mesajiyla rc 1 duser
  S8  TARIHI TABAN (kusur birebir yeniden uretilir): eski desen geri konunca AYNI bozuk
      depoda rc 0 + "[pre-commit] OK"  ⇒ S1'in "eskiden geciyordu" iddiasi KANIT
  M1-M4  fix'in HER katmanini ayri ayri sok -> korpus KIRMIZI olmali

Kosum: python tests/fixtures/precommit_coreleak_failclosed/run.py   (exit 0 = PASS)
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
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[2]
SABLON = CORE / "claude" / "git-hooks" / "pre-commit.template"

SH = shutil.which("sh") or shutil.which("bash")

# Gate'in kendi pathspec listesindeki ilk oge; S4 bunu bozuk-magic'e cevirir.
_PATHSPEC_CAPA = "'core/**' '.claude/agents/**'"


def _sil(d: Path) -> None:
    """Sentetik depoyu GERCEKTEN siler.

    ⚠ Duz `shutil.rmtree(d, ignore_errors=True)` Windows'ta SESSIZCE BASARISIZ olur:
    git `.git/objects/**` altindaki blob'lari SALT-OKUNUR yazar, `os.unlink` PermissionError
    verir ve `ignore_errors` onu yutar ⇒ `%TEMP%` sentetik depo YIGAR (olculdu 2026-09-02:
    kardes korpusun 2026-08-20'den beri biraktigi `pcgate_*` dizin sayisi **1992**).
    Kalinti "zararsiz" degildir: sonraki turlarda disk/dizin taramalarini yavaslatir ve
    "kosum kalintisi birikmiyor" varsayimini sessizce yanlislar.
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
        # Son care: kalintiyi birakiriz ama KORPUSU DUSURMEYIZ (temizlik bir
        # iddia degil, hijyen adimidir). ⛔ Burada `_sil` cagirma = sonsuz ozyineleme.
        shutil.rmtree(d, ignore_errors=True)


def _git(depo: Path, *a):
    return subprocess.run(["git", *a], cwd=str(depo), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def _depo_kur(validator_rc: int = 0, sizinti: bool = False,
              bozuk_index: bool = False) -> Path:
    """GERCEK git deposu (sablon `git rev-parse --show-toplevel` cagirir; sahte dizin
    sessizce BASKA bir agaci gosterirdi — 'kod != kablolama'nin kabuk yuzu)."""
    d = Path(tempfile.mkdtemp(prefix="q199_"))
    _git(d, "init", "-q")
    _git(d, "config", "user.email", "t@t")
    _git(d, "config", "user.name", "t")
    _git(d, "config", "commit.gpgsign", "false")

    (d / "dosya.txt").write_text("x\n", encoding="utf-8")
    _git(d, "add", "dosya.txt")

    # Sahte validator: adim-2 bu korpusun konusu DEGIL, sabit tutulur (rc disaridan).
    vdir = d / "core" / "scripts" / "validators"
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / "run_all_validators.py").write_text(
        "import sys\nprint('[sahte-validator] kostu')\nsys.exit(%d)\n" % validator_rc,
        encoding="utf-8")

    if sizinti:
        (d / "core" / "sizinti.md").write_text("gizli-core-icerigi\n", encoding="utf-8")
        _git(d, "add", "-f", "core/sizinti.md")

    if bozuk_index:
        # Gercekci cokme vektoru: index okunamaz hale gelir. `git rev-parse
        # --show-toplevel` (sablonun ilk cagrisi) BUNDAN ETKILENMEZ — olculdu.
        (d / ".git" / "index").write_bytes(b"BOZUK-INDEX-VERISI" * 8)

    return d


def _kos(d: Path, sablon_metni: str) -> tuple[int, str, str]:
    hook = d / "pre-commit.sh"
    hook.write_text(sablon_metni, encoding="utf-8")
    r = subprocess.run([SH, str(hook)], cwd=str(d), capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode, r.stdout, r.stderr


def gate(sablon_metni: str, **kw) -> tuple[int, str]:
    """-> (rc, stdout+stderr). Depo her cagrida kurulur ve silinir (kalinti BIRIKMEZ)."""
    d = _depo_kur(**kw)
    try:
        rc, out, err = _kos(d, sablon_metni)
        return rc, out + err
    finally:
        _sil(d)


def uctan_uca(sablon_metni: str) -> tuple[int, bool, int]:
    """S5: gate GECERSE gercekten commit oluyor mu? -> (gate_rc, commit_oldu, commit_sayisi)

    Depo SAGLAM, sizinti STAGED, ama gate'in KENDI pathspec'i bozuk ⇒ olcum cokuyor.
    Taban surumde bu 'sizinti yok' diye okunur ve commit GERCEKTEN gecer.
    """
    d = _depo_kur(sizinti=True)
    try:
        rc, out, err = _kos(d, sablon_metni)
        commit_oldu = False
        if rc == 0:
            c = _git(d, "commit", "-q", "-m", "sizintili commit")
            commit_oldu = (c.returncode == 0)
        say = _git(d, "rev-list", "--count", "HEAD")
        n = int(say.stdout.strip()) if say.returncode == 0 and say.stdout.strip().isdigit() else -1
        return rc, commit_oldu, n
    finally:
        _sil(d)


def _pathspec_boz(s: str) -> str:
    """Gate'in KENDI pathspec listesini gecersiz magic'e cevirir (S4/S5 vektoru)."""
    return s.replace(_PATHSPEC_CAPA, "':(gecersizsihir)core/**' '.claude/agents/**'", 1)


# ── TARIHI TABAN: fix'i BUGUNKU kaynaktan sokerek turetilir ────────────────────
# ⛔ `git show <sha>:` ile TARIHTEN cekilmez: sig klonda/merge sonrasi cozulmez.
_ESKI_YAKALAMA = (
    "SIZ_RC=0\n"
    "BAD=$(git diff --cached --name-only -- \\\n"
    "        'core/**' '.claude/agents/**' '.claude/skills/**' '.claude/commands/**' '.claude/rules/**' \\\n"
    "      ) || SIZ_RC=$?\n"
)
_ESKI_YERINE = (
    "BAD=$(git diff --cached --name-only -- \\\n"
    "        'core/**' '.claude/agents/**' '.claude/skills/**' '.claude/commands/**' '.claude/rules/**' \\\n"
    "        2>/dev/null || true)\n"
)
_FAILCLOSED_BLOK_BAS = 'if [ "$SIZ_RC" -ne 0 ]; then'
_FAILCLOSED_BLOK_SON = 'if [ -n "$BAD" ]; then'


def _fix_sok(s: str) -> str:
    """Adim-1 fix'inin TAMAMINI (rc yakalama + fail-closed dali) geri alir = 2026-09-02 oncesi."""
    if _ESKI_YAKALAMA not in s:
        raise AssertionError("capa yok: rc yakalama blogu (_ESKI_YAKALAMA)")
    s = s.replace(_ESKI_YAKALAMA, _ESKI_YERINE, 1)
    i = s.index(_FAILCLOSED_BLOK_BAS)
    j = s.index(_FAILCLOSED_BLOK_SON, i)
    return s[:i] + s[j:]


def senaryolar(sablon: str) -> list[tuple[str, bool, str]]:
    out: list[tuple[str, bool, str]] = []

    def ekle(ad, kosul, detay=""):
        out.append((ad, bool(kosul), detay))

    # --- S1 ⭐ BILINEN-BOZUK: index cokmesi -------------------------------------
    rc, o = gate(sablon, bozuk_index=True)
    ekle("S1 bozuk .git/index -> gate rc 1 + 'KOSTURULAMADI' (taban: rc 0 + OK)",
         rc == 1 and "KOŞTURULAMADI" in o and "[pre-commit] OK" not in o,
         "rc=%s cikti=%r" % (rc, o[-220:]))

    # --- S2 ⭐ POZITIF KONTROL: gercek sizinti hala yakalaniyor ------------------
    rc, o = gate(sablon, sizinti=True)
    ekle("S2 POZITIF KONTROL: gercek sizinti -> rc 1 + junction mesaji (sertlesme onu oldurmedi)",
         rc == 1 and "junction" in o.lower() and "core/sizinti.md" in o,
         "rc=%s cikti=%r" % (rc, o[-220:]))

    # --- S3 FP CAPASI: saglam + temiz -------------------------------------------
    rc, o = gate(sablon)
    ekle("S3 FP capasi: saglam+temiz depo -> rc 0, yanlis-pozitif YOK",
         rc == 0 and "[pre-commit] OK" in o and "KOŞTURULAMADI" not in o
         and "junction" not in o.lower(),
         "rc=%s cikti=%r" % (rc, o[-220:]))

    # --- S4 ⭐ 3. BAGLAM: depo saglam, gate'in KENDI pathspec'i bozuk ------------
    bozuk_gate = _pathspec_boz(sablon)
    if bozuk_gate == sablon:
        ekle("S4 3.baglam: bozuk pathspec magic -> gate rc 1", False,
             "KURULAMADI: pathspec capasi (%r) sablonda bulunamadi" % _PATHSPEC_CAPA)
    else:
        rc, o = gate(bozuk_gate)
        ekle("S4 3.baglam: depo SAGLAM ama gate pathspec'i bozuk -> rc 1 (cokme = bulgu)",
             rc == 1 and "KOŞTURULAMADI" in o and "[pre-commit] OK" not in o,
             "rc=%s cikti=%r" % (rc, o[-220:]))

    # --- S5 ⭐ UCTAN UCA: gate gecerse sizinti GERCEKTEN commit oluyor -----------
    if bozuk_gate == sablon:
        ekle("S5 uctan uca: sizintili commit BLOKLANIR", False, "KURULAMADI (S4 ile ayni)")
    else:
        g_rc, oldu, n = uctan_uca(bozuk_gate)
        ekle("S5 uctan uca: cokmus olcum + staged sizinti -> commit BLOKLANDI (0 commit)",
             g_rc == 1 and oldu is False and n in (0, -1),
             "gate_rc=%s commit_oldu=%s commit_sayisi=%s" % (g_rc, oldu, n))

    # --- S6 STDERR GORUNURLUGU ---------------------------------------------------
    rc, o = gate(sablon, bozuk_index=True)
    ekle("S6 cokmede git'in KENDI hata metni kullaniciya ULASIYOR (2>/dev/null yutuyordu)",
         "index file corrupt" in o.lower(),
         "cikti=%r" % o[-260:])

    # --- S7 `set -e` CAPASI ------------------------------------------------------
    #  Ciplak `BAD=$(cmd)` yazilsaydi `set -e` scripti 128 ile SESSIZCE oldururdu:
    #  bloklardi ama TESHIS URETMEZDI. rc 1 + kendi mesaji ⇒ dogru dal.
    rc, o = gate(sablon, bozuk_index=True)
    ekle("S7 `set -e` capasi: rc 128 ile sessiz olum YOK; KENDI mesajiyla rc 1",
         rc == 1 and rc != 128 and "[pre-commit] core-sızıntı" in o,
         "rc=%s cikti=%r" % (rc, o[-220:]))

    # --- S8 TARIHI TABAN: kusur birebir yeniden uretilir -------------------------
    try:
        eski = _fix_sok(sablon)
    except (AssertionError, ValueError) as e:
        ekle("S8 tarihi taban: eski desende rc 0 + 'OK' (kusur yeniden uretilir)", False,
             "KURULAMADI: %s" % e)
    else:
        rc_e, o_e = gate(eski, bozuk_index=True)
        g_rc, oldu, n = uctan_uca(_pathspec_boz(eski))
        ekle("S8 TARIHI TABAN: eski desen AYNI bozuk depoda rc 0 + '[pre-commit] OK' ⇒ "
             "ve uctan uca sizintili commit GERCEKTEN geciyordu",
             rc_e == 0 and "[pre-commit] OK" in o_e and g_rc == 0 and oldu is True and n == 1,
             "eski_rc=%s eski_cikti=%r | uctanuca gate_rc=%s commit_oldu=%s n=%s"
             % (rc_e, o_e[-160:], g_rc, oldu, n))

    return out


# ── MUTASYONLAR: fix'in HER katmani AYRI kesilir --------------------------------
#  ⛔ Tek noktali sokum yetmez: savunma-derinliginde bir katman digerini maskeler.
MUTASYONLAR = [
    ("M1 TAM sokum: `2>/dev/null || true` + fail-closed dali geri alinir (2026-09-02 oncesi)",
     _fix_sok),
    ("M2 yalniz rc YUTULUR (`|| SIZ_RC=$?` -> `|| true`); fail-closed dali DURUYOR ama olu",
     lambda s: s.replace("      ) || SIZ_RC=$?", "      ) || true", 1)),
    ("M3 fail-closed dali UYARIYA cevrilir (`exit 1` -> devam)",
     lambda s: s.replace(
         '   Bilerek denetimsiz commit gerekiyorsa (kullanıcı onayıyla): git commit --no-verify" >&2\n'
         '  echo "" >&2\n'
         '  exit 1\n'
         'fi\n'
         'if [ -n "$BAD" ]; then',
         '   Bilerek denetimsiz commit gerekiyorsa (kullanıcı onayıyla): git commit --no-verify" >&2\n'
         '  echo "" >&2\n'
         'fi\n'
         'if [ -n "$BAD" ]; then', 1)),
    ("M4 POZITIF KONTROL sokumu: gercek sizinti dali olduruluyor",
     lambda s: s.replace('if [ -n "$BAD" ]; then', 'if false; then', 1)),
]


def main() -> int:
    print("=" * 78)
    print("precommit_coreleak_failclosed — core-sizinti OLCUMU cokerse 'temiz' SAYILMAZ")
    print("=" * 78)
    if not SH:
        print("[DOGRULANAMADI] sh/bash bulunamadi — korpus kosulamadi (sessiz gecme YOK)")
        return 1
    if not SABLON.is_file():
        print("[DOGRULANAMADI] sablon bulunamadi: %s" % SABLON)
        return 1

    ham = SABLON.read_text(encoding="utf-8")

    sonuc = senaryolar(ham)
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
            bozuk = mut(ham)
        except Exception as e:
            print("  [YAMA TUTMADI] %s (%s: %s)" % (ad, type(e).__name__, e))
            yama_kirik.append(ad)
            continue
        if bozuk == ham:
            print("  [YAMA TUTMADI] %s (kaynak degismedi — capa bayat)" % ad)
            yama_kirik.append(ad)
            continue
        try:
            m_res = senaryolar(bozuk)
        except BaseException as e:
            # ⛔ KURULAMADI != KACTI: aracin bozulmasini korpusun basarisi sayma.
            print("  [KURULAMADI] %s -> %s: %s" % (ad, type(e).__name__, e))
            yama_kirik.append(ad)
            continue
        kacan = [a for a, ok, _ in m_res if not ok]
        # S8 TARIHI TABAN mutant altinda anlamsizdir (taban zaten sokulmus olabilir):
        kacan_gecerli = [a for a in kacan if not a.startswith("S8")]
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
            print("FAIL — mutasyon yamasi kaynaga UYMADI/KURULAMADI: %s" % ", ".join(yama_kirik))
        return 1
    print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(MUTASYONLAR)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
