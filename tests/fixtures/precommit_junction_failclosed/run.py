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

  S1  validator VAR + geciyor  -> rc 0 + kapanis satiri NE kostugunu soyler
  S2  ⭐ validator YOK         -> rc 1 + GORUNUR mesaj (eskiden: rc 0 + "OK")
  S3  FP capasi: core-sizinti kontrolu HALA calisiyor (staged core/ -> rc 1)
  S4  3. BAGLAM: validator VAR ama DUSUYOR -> rc 1 (eski davranis KORUNDU)
  M1-M2  fix'i sok -> korpus KIRMIZI olmali

Kosum: python tests/fixtures/precommit_junction_failclosed/run.py   (exit 0 = PASS)
"""
from __future__ import annotations

import os
import shutil
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


def _git(depo: Path, *a):
    return subprocess.run(["git", *a], cwd=str(depo), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def sentetik_depo(sablon_metni: str, validator_var: bool,
                  validator_rc: int = 0, core_sizintisi: bool = False) -> tuple[int, str]:
    """Gercek bir git deposu kurup sablonu GERCEK KABUKLA kosar -> (rc, cikti).

    ⚠ Sablon `git rev-parse --show-toplevel` cagirir ⇒ gercek depo SART; sahte dizin
    sessizce baska bir agaci gosterirdi ("kod != kablolama"nin kabuk yuzu).
    """
    d = Path(tempfile.mkdtemp(prefix="pcgate_"))
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
    shutil.rmtree(d, ignore_errors=True)
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


def main() -> int:
    print("=" * 78)
    print("precommit_junction_failclosed — `core/` yoksa SESSIZCE ATLAMA YOK")
    print("=" * 78)
    if not SH:
        print("[DOGRULANAMADI] sh/bash bulunamadi — korpus kosulamadi (sessiz gecme YOK)")
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
