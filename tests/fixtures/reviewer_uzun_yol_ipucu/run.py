#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reviewer_uzun_yol_ipucu — Issue #285: 'validator YOK' teshisi uzun-yol olasiligini anar,
HUKUM DEGISMEZ (SKIP → severity'ye gore verdict; fail-closed).

NIYE AYRI KOSUCU: `reviewer_skip_sozlesmesi` SKIP'in HUKMUNU civiler (ona dokunulmadi);
burada olculen sey TESHIS METNI + hukmun uzun/kisa yolda AYNI kaldigi.

VEKTORLER
  U1 FP CAPASI  : kisa yol (nt) → ipucu YOK (her 'bulunamadi'ya gurultu basilmaz)
  U2            : uzun yol (nt, LongPathsEnabled=0, onekle YOK) → ipucu + uzunluk + LP=0 + YOK
  U3            : uzun yol + `\\\\?\\` onekiyle VAR → 'kurulum eksikligi DEGIL'
  U4 FP CAPASI  : POSIX'te uzun yol → ipucu YOK (MAX_PATH Windows sinirdir)
  U5 HUKUM      : uctan uca main() — uzun ve kisa VALIDATORS_DIR'de verdict + exit AYNI
                  (BLOCKER sinifi eksik validator → BLOCKER + exit 1, iki yolda da)
  U6 (yalniz nt): uctan uca uzun yolda SKIP mesajinda ipucu VAR; kisa yolda YOK
  U7 (yalniz nt): CANLI — `\\\\?\\` onekiyle yaratilan gercek dosya: `Path.exists()` onu
                  GOREMEZSE ipucu 'VAR' der (Issue'nun mekanizmasi) — LongPathsEnabled=1
                  makinede exists() gordugu icin vektor 'OLCULEMEDI' notuyla gecer.

MUTASYON (kaynak BELLEKTE degisir, gercek dosyaya yazilmaz):
  --mutasyon-ipucu-yok    SKIP mesajina ipucu eklenmez          → U6 duser (nt)
  --mutasyon-her-yola     esik kaldirilir (kisa yolda da ipucu)  → U1 (+U6) duser
  --mutasyon-hukum        ipucu varken SKIP → PASS'e kayar        → U5 duser
Ucuncu baglam (F3): U4 (baska platform) + U5 kisa/uzun iki proje koku.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

KOK = Path(__file__).resolve().parents[3]
KAYNAK = KOK / "scripts" / "validators" / "run_review.py"

MUTASYONLAR = {
    "--mutasyon-ipucu-yok": ("                        + ipucu))", "                        ))"),
    "--mutasyon-her-yola": ("if len(str(y)) > WIN_MAX_PATH]", "if len(str(y)) >= 0]"),
    "--mutasyon-hukum": ("                script_name, default_severity, 'SKIP', description,",
                         "                script_name, default_severity,"
                         " 'PASS' if ipucu else 'SKIP', description,"),
}
KIP = next((a for a in sys.argv[1:] if a in MUTASYONLAR), None)
if any(a.startswith("--mutasyon") for a in sys.argv[1:]) and KIP is None:
    print(f"⛔ bilinmeyen kip; gecerli: {sorted(MUTASYONLAR)}")
    sys.exit(3)

_sayac = {"pass": 0, "fail": 0}


def sonuc(ad: str, ok: bool, detay=None) -> None:
    _sayac["pass" if ok else "fail"] += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + (f" -- {str(detay)[:230]}" if detay else ""))


def modul():
    src = KAYNAK.read_text(encoding="utf-8")
    if KIP:
        eski, yeni = MUTASYONLAR[KIP]
        if src.count(eski) != 1:
            print(f"⛔ MUTASYON CAPASI {src.count(eski)}x [{KIP}] {eski[:50]!r} — "
                  f"sahte-yesil yerine gorunur durus")
            sys.exit(3)
        src = src.replace(eski, yeni, 1)
    m = types.ModuleType("rr_uzun_yol")
    m.__file__ = str(KAYNAK)
    exec(compile(src, str(KAYNAK), "exec"), m.__dict__)  # noqa: S102
    return m


def uzun(kok: Path, hedef: int) -> Path:
    """kok altinda toplam uzunlugu ~hedef olan (VAR OLMASI GEREKMEYEN) bir dizin yolu."""
    p = kok
    while len(str(p)) < hedef:
        p = p / ("d" * 40)
    return p


def kos(R, vdir: Path, proj: Path, artifact: Path):
    R.VALIDATORS_DIR = vdir
    R.PROJ_ROOT = proj
    R.TASK_VALIDATORS["cds_creation"] = [
        ("check_uzun_yol_ornek_validator_bulunamaz.py", "BLOCKER", "ornek BLOCKER gate")]
    eski = sys.argv
    sys.argv = ["run_review.py", "--task", "cds_creation", "--artifact", str(artifact), "--json"]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            rc = R.main()
    finally:
        sys.argv = eski
    j = json.loads(buf.getvalue())
    mesaj = " ".join(str(r.get("message", "")) for r in j.get("results", []))
    durum = [r.get("status") for r in j.get("results", [])]
    return rc, j.get("verdict"), durum, mesaj


def main() -> int:
    R = modul()
    print(f"== reviewer_uzun_yol_ipucu — {'MUTASYON ' + KIP if KIP else 'BUGUNKU KOD'} ==")
    kisa = [Path("C:/x/scripts/validators/check_a.py")]
    uz = [Path("C:/" + "u" * 300 + "/check_a.py")]
    ip1 = R.uzun_yol_ipucu(kisa, os_adi="nt", longpaths=0, onek_var=lambda p: False)
    sonuc("U1 FP CAPASI: kisa yol → ipucu YOK", ip1 == "", ip1)
    ip2 = R.uzun_yol_ipucu(uz, os_adi="nt", longpaths=0, onek_var=lambda p: False)
    sonuc("U2 uzun yol → ipucu + uzunluk + LongPathsEnabled=0 + onekle YOK",
          "UZUN-YOL" in ip2 and str(len(str(uz[0]))) in ip2 and "LongPathsEnabled=0" in ip2
          and "önekiyle: YOK" in ip2, ip2)
    ip3 = R.uzun_yol_ipucu(uz, os_adi="nt", longpaths=0, onek_var=lambda p: True)
    sonuc("U3 onekle VAR → 'kurulum eksikliği DEĞİL'",
          "önekiyle: VAR" in ip3 and "kurulum eksikliği DEĞİL" in ip3, ip3)
    ip4 = R.uzun_yol_ipucu(uz, os_adi="posix", longpaths=None, onek_var=lambda p: False)
    sonuc("U4 FP CAPASI: POSIX'te ipucu YOK", ip4 == "", ip4)

    kok = Path(tempfile.mkdtemp(prefix="rw_uzun_"))
    try:
        artifact = kok / "a.cds"
        artifact.write_text("x", encoding="utf-8")
        k_rc, k_v, k_d, k_m = kos(R, kok / "kisa", kok, artifact)
        u_rc, u_v, u_d, u_m = kos(R, uzun(kok, 280), kok, artifact)
        sonuc("U5 HUKUM: kisa ve uzun yolda verdict+exit+status AYNI (BLOCKER, 1, SKIP)",
              (k_rc, k_v, k_d) == (u_rc, u_v, u_d) == (1, "BLOCKER", ["SKIP"]),
              f"kisa=({k_rc},{k_v},{k_d}) uzun=({u_rc},{u_v},{u_d})")
        if os.name == "nt":
            sonuc("U6 uctan uca: uzun yolda ipucu VAR, kisa yolda YOK",
                  "UZUN-YOL" in u_m and "UZUN-YOL" not in k_m,
                  u_m[u_m.find("⚠"):][:160] if "⚠" in u_m else u_m[:160])
            # U7 CANLI: gercek uzun-yol dosyasi, yalniz `\\?\` onekiyle yaratilabilir
            hedef = uzun(kok, 300) / "check_canli.py"
            onekli = "\\\\?\\" + os.path.abspath(str(hedef))
            os.makedirs(os.path.dirname(onekli), exist_ok=True)
            with open(onekli, "w", encoding="utf-8") as f:
                f.write("import sys\n")
            gorunur = hedef.exists()
            ip7 = R.uzun_yol_ipucu([hedef])
            if gorunur:
                sonuc("U7 CANLI: Path.exists() uzun yolu GORDU (LongPathsEnabled=1?) → "
                      "OLCULEMEDI, atlandi", True, f"LP={R._longpaths_enabled()}")
            else:
                sonuc("U7 CANLI: exists()=False iken ipucu 'VAR (… kurulum eksikliği DEĞİL)'",
                      "önekiyle: VAR" in ip7, ip7)
        else:
            sonuc("U6/U7 Windows'a ozgu → bu platformda OLCULEMEDI (atlandi)", True, os.name)
    finally:
        uzun_kok = "\\\\?\\" + os.path.abspath(str(kok)) if os.name == "nt" else str(kok)
        shutil.rmtree(uzun_kok, ignore_errors=True)

    print(f"\nTOPLAM: {_sayac['pass']} PASS / {_sayac['fail']} FAIL")
    return 0 if _sayac["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
