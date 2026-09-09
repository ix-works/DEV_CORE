#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PROJE pre-commit sablonu: `core/` cozulemezse validator adimi SESSIZCE ATLANIYORDU.

KOK: `claude/git-hooks/pre-commit.template` adim-2'yi yalniz `if [ -f … ]` ile
sariyordu ve `else` YOKTU. `core/` junction'i cozulemeyen bir ortamda (yeni klon ·
worktree · kirik junction · baska makine) validator zinciri HIC KOSMUYOR, ama hemen
ardindaki satir `[pre-commit] OK` basiyordu ⇒ commit DENETIMSIZ geciyor ve HICBIR
belirti uretmiyordu. Fail-open'in en kotu turu: BASARI GIBI GORUNEN YOKLUK.
⛔ Bu, ADR 0019'un *"gate'lenmemis kural ~ kuralsiz"* hukmunun SESSIZ ihlalidir.

⭐ KAYIT DUZELTMESI (2026-08-20): kuyruk bu kusuru PROJE dosyasinda gosteriyordu, ama
ayni kusur CORE SABLONUNDA duruyordu ⇒ `init_project` ile kurulan HER YENI PROJE onu
MIRAS ALIYORDU. Gorunen ornegi duzeltmek sinifi kapatmazdi.

FIX: `else` dali eklendi — GORUNUR mesaj + `exit 1` (fail-closed). Kardes desen:
core'un KENDI `scripts/git-hooks/pre-commit`i, python bulunamazsa ATLAMAZ, BLOKLAR.
Kapanis satiri artik NE kostugunu soyler (paydasiz "OK" bu kusurun yarisiydi).

⚠ KALAN BOSLUK (bu fix KAPATMAZ, bilincli-bilinen): `core.hooksPath` unset ise bu
DOSYA hic calismaz ve yine hicbir sey uyarmaz (B13 recetesi bunu ayri kalem olarak
beyan eder). Burada kapanan yalniz `core/` COZUMLEME katmanidir.

⭐ HIJYEN KUSURU (Q247, 2026-09-09): korpus senaryo basina GERCEK bir `git init` deposu
kurar ve `shutil.rmtree(d, ignore_errors=True)` ile silerdi. Windows'ta git gevsek
objeleri (`.git/objects/**`) SALT-OKUNUR yazar; `rmtree` o dosyayi silemez, `ignore_errors`
hatayi YUTAR ve dizin `%TEMP%`de KALIR. Olculdu: tek kosum **+12 dizin** (4 senaryo x
[taban + 2 mutasyon]), 2026-09-02'de 2040 -> 2026-09-09'da 2412 birikmis kalinti.
⛔ Bu, korpusun KENDI dersinin ihlaliydi: "sessiz yutma" tam da S2'nin olctugu kusur.
FIX: `_sil()` — `onexc`/`onerror` geri cagirmasi salt-okunur bayragini temizleyip yeniden
dener; BASARISIZLIK YUTULMAZ, `TEMIZLIK_HATALARI`ya yazilir ve korpusu KIRMIZI yapar.
Desen ICAT EDILMEDI: ayni repoda `tests/fixtures/guard_f1_taban_failclosed/run.py:172`
zaten boyle siliyordu (kardes artefakt).

  S1  validator VAR + geciyor  -> rc 0 + kapanis satiri NE kostugunu soyler
  S2  ⭐ validator YOK         -> rc 1 + GORUNUR mesaj (eskiden: rc 0 + "OK")
  S3  FP capasi: core-sizinti kontrolu HALA calisiyor (staged core/ -> rc 1)
  S4  3. BAGLAM: validator VAR ama DUSUYOR -> rc 1 (eski davranis KORUNDU)
  M1-M2  fix'i sok -> korpus KIRMIZI olmali
  H1  ⭐HIJYEN  kurulan HER sentetik depo diskte YOK (koşum sonu, sayarak)
  H2  ⭐HIJYEN  `%TEMP%/pcgate_*` sayisi koşumla ARTMADI (once/sonra farki <= 0)
  H3  ⭐TABAN   [win32] eski desen (`rmtree(ignore_errors=True)`) kusuru YENIDEN URETIR
  H4  ⭐GORUNURLUK  temizlik basarisiz olursa SESSIZCE yutulmaz (sahte `rmtree` ile)

Kosum: python tests/fixtures/precommit_junction_failclosed/run.py   (exit 0 = PASS)
"""
from __future__ import annotations

import glob
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

ONEK = "pcgate_"
# Q247 hijyen defteri: kurulan HER sentetik depo + silinemeyen HER dizin burada.
KURULAN: list[Path] = []
TEMIZLIK_HATALARI: list[str] = []


def _pcgate_sayisi() -> int:
    """`%TEMP%` altindaki `pcgate_*` dizin sayisi (sizinti olcusu)."""
    return len(glob.glob(os.path.join(tempfile.gettempdir(), ONEK + "*")))


def _sil(d: Path) -> bool:
    """Sentetik depoyu GERCEKTEN siler; basarisizligi YUTMAZ -> (silindi mi?).

    ⚠ Duz `rmtree(ignore_errors=True)` Windows'ta SESSIZCE basarisiz olur: git
    `.git/objects/**` altini SALT-OKUNUR yazar => kalinti `%TEMP%`de YIGAR (Q247).
    Kardes desen: `tests/fixtures/guard_f1_taban_failclosed/run.py:172` (`_sil`).
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
    except Exception as e:               # noqa: BLE001
        TEMIZLIK_HATALARI.append("%s -> %s: %s" % (d, type(e).__name__, e))
        return False
    if d.exists():
        # ⛔ Istisna FIRLAMADAN da basarisiz olabilir (geri cagirma yuttu):
        #    "exit 0 != kanit" — SONUCU olc, cagriyi degil.
        TEMIZLIK_HATALARI.append("%s -> silinmedi (istisna YOK, dizin HALA VAR)" % d)
        return False
    return True


def _git(depo: Path, *a):
    return subprocess.run(["git", *a], cwd=str(depo), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def sentetik_depo(sablon_metni: str, validator_var: bool,
                  validator_rc: int = 0, core_sizintisi: bool = False) -> tuple[int, str]:
    """Gercek bir git deposu kurup sablonu GERCEK KABUKLA kosar -> (rc, cikti).

    ⚠ Sablon `git rev-parse --show-toplevel` cagirir ⇒ gercek depo SART; sahte dizin
    sessizce baska bir agaci gosterirdi ("kod != kablolama"nin kabuk yuzu).
    """
    d = Path(tempfile.mkdtemp(prefix=ONEK))
    KURULAN.append(d)
    try:
        return _sentetik_depo_govde(d, sablon_metni, validator_var,
                                    validator_rc, core_sizintisi)
    finally:
        # ⚠ try/finally SART: eski kod `subprocess` firlatirsa temizlige HIC gelmiyordu.
        _sil(d)


def _sentetik_depo_govde(d: Path, sablon_metni: str, validator_var: bool,
                         validator_rc: int, core_sizintisi: bool) -> tuple[int, str]:
    _git(d, "init", "-q")
    _git(d, "config", "user.email", "t@t")
    _git(d, "config", "user.name", "t")

    (d / "dosya.txt").write_text("x\n", encoding="utf-8")
    _git(d, "add", "dosya.txt")

    if validator_var:
        vdir = d / "core" / "scripts" / "validators"
        vdir.mkdir(parents=True)
        # Sahte validator: rc'yi disaridan alir (gercek run_all cagrilmaz).
        (vdir / "run_all_validators.py").write_text(
            f"import sys\nprint('[sahte-validator] kostu')\nsys.exit({validator_rc})\n",
            encoding="utf-8")

    if core_sizintisi:
        (d / "core").mkdir(exist_ok=True)
        (d / "core" / "sizinti.md").write_text("x\n", encoding="utf-8")
        _git(d, "add", "-f", "core/sizinti.md")

    hook = d / "pre-commit.sh"
    hook.write_text(sablon_metni, encoding="utf-8")

    r = subprocess.run([SH, str(hook)], cwd=str(d), capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode, (r.stdout + r.stderr)


def senaryolar(sablon: str) -> list[tuple[str, bool, str]]:
    out = []

    def ekle(ad, kosul, detay=""):
        out.append((ad, bool(kosul), detay))

    # --- S1: validator VAR + geciyor ---------------------------------------
    rc, o = sentetik_depo(sablon, validator_var=True, validator_rc=0)
    ekle("S1 validator VAR + geciyor -> rc 0 + kapanis NE kostugunu soyler",
         rc == 0 and "run_all_validators" in o and "koştu" in o,
         "rc=%s cikti=%r" % (rc, o[-140:]))

    # --- S2: ⭐ validator YOK -> BLOKLA (eskiden rc 0 + "OK" idi) -----------
    rc, o = sentetik_depo(sablon, validator_var=False)
    ekle("S2 validator YOK -> rc 1 + GORUNUR mesaj (sessiz atlama YOK)",
         rc == 1 and "KOŞTURULAMADI" in o and "[pre-commit] OK" not in o,
         "rc=%s cikti=%r" % (rc, o[-200:]))

    # --- S3: FP capasi — core-sizinti kontrolu bozulmadi -------------------
    rc, o = sentetik_depo(sablon, validator_var=True, core_sizintisi=True)
    ekle("S3 FP capasi: core-sizinti kontrolu HALA bloklar (adim-1 bozulmadi)",
         rc == 1 and "junction" in o.lower(),
         "rc=%s cikti=%r" % (rc, o[-140:]))

    # --- S4: 3. BAGLAM — validator VAR ama DUSUYOR (eski davranis korundu) -
    rc, o = sentetik_depo(sablon, validator_var=True, validator_rc=1)
    ekle("S4 3.baglam: validator DUSUYOR -> rc 1 (mevcut davranis KORUNDU)",
         rc == 1 and "validator ihlali" in o,
         "rc=%s cikti=%r" % (rc, o[-140:]))

    return out


MUTASYONLAR = [
    ("M1 `else` dalini sok (sessiz atlama geri gelsin)",
     lambda s: s[:s.index("else\n  echo \"\" >&2")] + "fi\n"
               + s[s.index("# ⚠ Kapanış satırı"):]),
    ("M2 kapanis satirini PAYDASIZ 'OK'a dondur",
     lambda s: s.replace(
         'echo "[pre-commit] OK — core-sızıntı kontrolü + run_all_validators --quick ($VALIDATOR_DURUM)"',
         'echo "[pre-commit] OK"')),
]


def hijyen_capalari(once: int) -> list[tuple[str, bool, str]]:
    """Q247 — korpusun KENDI sizintisini olcer (sablonun degil; mutasyonlardan BAGIMSIZ)."""
    out: list[tuple[str, bool, str]] = []

    # --- H1: kurulan her depo GERCEKTEN gitti mi (deterministik capa) -------
    kalan = [str(d) for d in KURULAN if d.exists()]
    out.append(("H1 HIJYEN: kurulan %d sentetik deponun HEPSI silindi" % len(KURULAN),
                not kalan and not TEMIZLIK_HATALARI,
                "kalan=%d %s | temizlik_hatalari=%s" % (len(kalan), kalan[:3],
                                                        TEMIZLIK_HATALARI[:3])))

    # --- H2: %TEMP%/pcgate_* SAYIM farki (kaydin istedigi kanit) -----------
    sonra = _pcgate_sayisi()
    out.append(("H2 HIJYEN: TEMP/pcgate_* sayisi ARTMADI (once=%d sonra=%d)"
                % (once, sonra), (sonra - once) <= 0,
                "fark=%+d" % (sonra - once)))

    # --- H3: TABAN — eski desen kusuru YENIDEN URETIR (win32) --------------
    # ⚠ POSIX'te git objeleri de salt-okunurdur AMA dizin yazilabilir oldugu icin
    #    `rmtree` yine de siler ⇒ kusur PLATFORM-OZELDIR. Linux CI'da iddia
    #    kurulamaz; "olculemedi" ATLA olarak beyan edilir (yesil sayilmaz).
    kok = Path(tempfile.mkdtemp(prefix="pcg_taban_"))
    try:
        d = kok / "depo"
        d.mkdir()
        _git(d, "init", "-q")
        (d / "x.txt").write_text("x\n", encoding="utf-8")
        _git(d, "add", "x.txt")
        shutil.rmtree(d, ignore_errors=True)          # ⬅ ESKI (kusurlu) desen
        eski_kaldi = d.exists()
        _sil(d)                                       # ⬅ YENI desen temizler mi?
        yeni_temiz = not d.exists()
        if sys.platform == "win32":
            out.append(("H3 TABAN: eski `rmtree(ignore_errors=True)` kusuru URETIYOR "
                        "+ yeni `_sil` temizliyor",
                        eski_kaldi and yeni_temiz,
                        "eski_kaldi=%s yeni_temiz=%s" % (eski_kaldi, yeni_temiz)))
        else:
            out.append(("H3 TABAN [ATLA: win32 disi] yeni `_sil` yine de temizliyor",
                        yeni_temiz,
                        "platform=%s eski_kaldi=%s (POSIX'te kusur BEKLENMEZ)"
                        % (sys.platform, eski_kaldi)))
    finally:
        _sil(kok)

    # --- H4: GORUNURLUK — temizlik basarisiz olursa SESSIZCE yutulmaz ------
    d2 = Path(tempfile.mkdtemp(prefix="pcg_gorunur_"))
    isaret = len(TEMIZLIK_HATALARI)
    gercek_rmtree = shutil.rmtree
    try:
        def _daima_dus(*a, **k):                      # noqa: ANN001,ANN002,ANN003
            raise PermissionError("sentetik: silinemedi")
        shutil.rmtree = _daima_dus                    # type: ignore[assignment]
        try:
            dondu = _sil(d2)
        except BaseException as e:                    # noqa: BLE001
            # ⛔ COKME != FAIL: `_sil` istisnayi disari kacirirsa bu bir OLCUMDUR,
            #    korpusu cokertip "kurulamadi"ya cevirmesin — GORUNUR FAIL olsun.
            dondu = "COKTU:%s(%s)" % (type(e).__name__, e)
    finally:
        shutil.rmtree = gercek_rmtree                 # type: ignore[assignment]
    yeni_hata = TEMIZLIK_HATALARI[isaret:]
    out.append(("H4 GORUNURLUK: temizlik dusunce SESSIZCE yutulmuyor "
                "(False doner + defter'e yazar)",
                dondu is False and len(yeni_hata) == 1,
                "dondu=%r yeni_hata=%s" % (dondu, yeni_hata)))
    del TEMIZLIK_HATALARI[isaret:]                    # sentetik hata sonucu KIRLETMEZ
    _sil(d2)
    return out


def main() -> int:
    print("=" * 78)
    print("precommit_junction_failclosed — `core/` yoksa SESSIZCE ATLAMA YOK")
    print("=" * 78)
    if not SH:
        print("[DOGRULANAMADI] sh/bash bulunamadi — korpus kosulamadi (sessiz gecme YOK)")
        return 1

    once = _pcgate_sayisi()
    ham = SABLON.read_text(encoding="utf-8")
    sonuc = senaryolar(ham)
    for ad, ok, detay in sonuc:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok:
            print("         gorulen: %s" % detay)
    print("  -> %d/%d senaryo PASS" % (sum(1 for _, ok, _ in sonuc if ok), len(sonuc)))

    print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
    mut_kirik, yama_kirik = [], []
    for ad, mut in MUTASYONLAR:
        try:
            bozuk = mut(ham)
        except Exception as e:
            print("  [YAMA TUTMADI] %s (%s)" % (ad, type(e).__name__))
            yama_kirik.append(ad)
            continue
        if bozuk == ham:
            print("  [YAMA TUTMADI] %s" % ad)
            yama_kirik.append(ad)
            continue
        try:
            m_res = senaryolar(bozuk)
            yakalandi = any(not ok for _, ok, _ in m_res)
            kacan = [a for a, ok, _ in m_res if not ok]
        except BaseException as e:
            yakalandi, kacan = False, []
            print("  [KURULAMADI] %s -> %s" % (ad, type(e).__name__))
        print("  [%s] %s" % ("YAKALANDI" if yakalandi else "KACTI", ad))
        if yakalandi:
            print("         kiran senaryo(lar): %s" % ", ".join(kacan[:3]))
        else:
            mut_kirik.append(ad)

    # --- Q247 HIJYEN CAPALARI (mutasyonlardan SONRA: tum kosumu kapsamali) ---
    print("\n--- HIJYEN (Q247: korpusun KENDI sizintisi) ---")
    hij = hijyen_capalari(once)
    for ad, ok, detay in hij:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        print("         %s" % detay)
    sonuc = sonuc + hij
    kirik = [(a, d) for a, ok, d in sonuc if not ok]

    print("\n" + "=" * 78)
    if kirik or mut_kirik or yama_kirik:
        if kirik:
            print("FAIL — senaryo: %s" % ", ".join(a for a, _ in kirik))
        if mut_kirik:
            print("FAIL — mutasyon KACTI: %s" % ", ".join(mut_kirik))
        if yama_kirik:
            print("FAIL — mutasyon yamasi kaynaga UYMADI: %s" % ", ".join(yama_kirik))
        return 1
    print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(MUTASYONLAR)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
