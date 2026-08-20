#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K2 — `check_console_utf8` kokU `parents[2]`e CIVILIYDI: gate OLCULEMIYORDU.

=== KOK ===
    CORE = Path(__file__).resolve().parents[2]

Tek kok kaynagi. Sonuc "izole edilemiyor"dan daha kotusu: gate KANITSIZ duruyordu.
Dedektorun gercekten yakalayip yakalamadigini gostermenin tek yolu CANLI core'a
kasten bozuk bir script koymakti — kimse yapmaz ⇒ C-ENC-01 yillarca "yesil" dedi
ama yakalama gucu HIC olculmedi. (Gate'in kendi dedektorunu olcememesi, bu turun
K1 kalemiyle ayni sinif: yesil ekranin PAYDASI bilinmiyordu.)

=== FIX ===
`core_kok()`: `--kok <yol>` → env `IX_CORE_ROOT` → `parents[2]` (VARSAYILAN AYNEN).
Davranis degismez; yalnizca gate artik sentetik bir agaca yoneltilebilir.

⚠ `project_root()` BILEREK KULLANILMADI. Gate CORE'un kendi script'lerini olcer;
projeye cevirmek onu sessizce BOSALTIRDI (projede `scripts/` bambaska bir agactir).
X1 + M2 bu siniri civiler — **SILINEMEZLER**.

  P1 ⭐ AYIRT EDICI  sentetik agac + korumasiz non-ASCII script -> FAIL, dosya LISTELENIR
  N1               ayni script korumali -> temiz
  N2 FP capasi     non-ASCII VAR ama cikti basmiyor -> suclanmaz
  N3 FP capasi     cikti basiyor ama ASCII -> suclanmaz
  N4 FP capasi     `tests/` altindaki bozuk script ATLANIR (ATLA_DIZIN korundu)
  W1               oncelik: `--kok` > env `IX_CORE_ROOT` > `__file__` turevi
  X1 ⭐ SINIR       argumansiz kosum GERCEK core'u tarar (varsayilan sentetige KAYMADI)
  M1-M3            fix'i sok -> korpus KIRMIZI olmali

Kosum: python tests/fixtures/console_utf8_kok_izolasyonu/run.py     (exit 0 = PASS)
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
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

KOK = Path(__file__).resolve().parents[3]
GATE = KOK / "scripts" / "validators" / "check_console_utf8.py"

# Dort script sinifi — ikisi FP capasi. Gate "non-ASCII **VE** cikti basan" ariyor;
# tek sart aranirsa (mutasyon M3) N2 ya da N3 yanar.
BOZUK = 'print("Türkçe çıktı — koruma YOK")\n'
KORUMALI = ('import sys\nsys.stdout.reconfigure(encoding="utf-8", errors="replace")\n'
            'print("Türkçe çıktı — koruma VAR")\n')
SESSIZ_NONASCII = 'MESAJ = "Türkçe sabit — hiçbir şey basmıyor"\n'
ASCII_BASAN = 'print("plain ascii output")\n'


def _sentetik(ekstra: dict[str, str] | None = None) -> Path:
    """Sahte bir CORE agaci: `<kok>/scripts/**.py`."""
    d = Path(tempfile.mkdtemp(prefix="k2_"))
    (d / "scripts").mkdir()
    for rel, icerik in (ekstra or {}).items():
        p = d / "scripts" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(icerik, encoding="utf-8")
    return d


def _kos(gate: Path, *argv: str, env_kok: str | None = None) -> tuple[int, str]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("IX_CORE_ROOT", None)
    if env_kok:
        env["IX_CORE_ROOT"] = env_kok
    p = subprocess.run([sys.executable, str(gate), *argv], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, timeout=300)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def senaryolar(gate: Path) -> list[tuple[str, bool, str]]:
    r: list[tuple[str, bool, str]] = []

    def ekle(ad: str, ok: bool, detay: str = "") -> None:
        r.append((ad, ok, detay))

    # P1 ⭐ AYIRT EDICI: gate sentetik agaca YONELTILEBILIYOR ve YAKALIYOR
    d = _sentetik({"bozuk.py": BOZUK})
    try:
        rc, out = _kos(gate, "--kok", str(d))
        ekle("P1 ⭐ sentetik agac: korumasiz script YAKALANIR (rc=1 + dosya listelenir)",
             rc == 1 and "scripts/bozuk.py" in out, f"rc={rc} · {out.strip()[:220]!r}")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # N1: ayni script korumaliysa temiz
    d = _sentetik({"korumali.py": KORUMALI})
    try:
        rc, out = _kos(gate, "--kok", str(d))
        ekle("N1 korumali script -> temiz (rc=0)", rc == 0 and "[OK]" in out,
             f"rc={rc} · {out.strip()[:220]!r}")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # N2 FP capasi: non-ASCII var ama CIKTI BASMIYOR
    d = _sentetik({"sessiz.py": SESSIZ_NONASCII})
    try:
        rc, out = _kos(gate, "--kok", str(d))
        ekle("N2 FP capasi: non-ASCII VAR ama cikti basmiyor -> suclanmaz", rc == 0,
             f"rc={rc} · {out.strip()[:220]!r}")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # N3 FP capasi: cikti basiyor ama ASCII
    d = _sentetik({"duz.py": ASCII_BASAN})
    try:
        rc, out = _kos(gate, "--kok", str(d))
        ekle("N3 FP capasi: cikti basiyor ama ASCII -> suclanmaz", rc == 0,
             f"rc={rc} · {out.strip()[:220]!r}")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # N4 FP capasi: ATLA_DIZIN korundu (tests/ altindaki bozuk script sayilmaz)
    d = _sentetik({"tests/bozuk.py": BOZUK})
    try:
        rc, out = _kos(gate, "--kok", str(d))
        ekle("N4 FP capasi: `tests/` altindaki bozuk script ATLANIR (ATLA_DIZIN korundu)",
             rc == 0, f"rc={rc} · {out.strip()[:220]!r}")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # W1: oncelik sirasi — arguman env'i EZER
    d_arg = _sentetik({"korumali.py": KORUMALI})
    d_env = _sentetik({"bozuk.py": BOZUK})
    try:
        rc_a, out_a = _kos(gate, "--kok", str(d_arg), env_kok=str(d_env))
        rc_e, out_e = _kos(gate, env_kok=str(d_env))
        ekle("W1 oncelik: `--kok` env'i EZER; env de `__file__` turevini ezer",
             rc_a == 0 and rc_e == 1 and "scripts/bozuk.py" in out_e,
             f"arg-kazandi rc={rc_a} · env-kazandi rc={rc_e}")
    finally:
        shutil.rmtree(d_arg, ignore_errors=True)
        shutil.rmtree(d_env, ignore_errors=True)

    # X1 ⭐ SINIR: argumansiz kosum GERCEK core'u tarar (varsayilan kaymadi)
    rc, out = _kos(gate)
    # Gercek core >100 script tarar; sentetik agaclar 1. Payda bu yuzden ayirt edici.
    sayi = 0
    for parca in out.replace("/", " ").split():
        if parca.isdigit():
            sayi = max(sayi, int(parca))
    ekle("X1 ⭐ SINIR: argumansiz kosum GERCEK core'u tarar (payda >100; sentetige kaymadi)",
         sayi > 100, f"rc={rc} · en buyuk sayi={sayi} · {out.strip()[:160]!r}")
    return r


MUTASYONLAR = [
    ("M1 kok enjeksiyonunu sok (`parents[2]`e geri don)",
     lambda s: s.replace(
         '    argv = list(sys.argv[1:]) if argv is None else list(argv)\n'
         '    if "--kok" in argv:\n',
         '    return Path(__file__).resolve().parents[2]\n'
         '    argv = list(sys.argv[1:]) if argv is None else list(argv)\n'
         '    if "--kok" in argv:\n')),
    ("M2 ⭐SINIR: varsayilani PROJE kokune cevir (gate'i sessizce bosaltir)",
     lambda s: s.replace(
         '    return Path(__file__).resolve().parents[2]\n\n\nCORE = core_kok()',
         '    import utils.project_config as _pc\n    return _pc.project_root()\n\n\n'
         'CORE = core_kok()')),
    ("M3 `_BASAR` (cikti basiyor mu) sartini sok -> her non-ASCII dosya suclanir",
     lambda s: s.replace('        if not _BASAR.search(s):\n            continue\n', '')),
]


def main() -> int:
    print("=" * 78)
    print("console_utf8_kok_izolasyonu — K2: gate'in kokU enjekte edilebilir mi?")
    print("=" * 78)
    if not GATE.is_file():
        print(f"FAIL — gate yok: {GATE}")
        return 1

    ham = GATE.read_text(encoding="utf-8")
    sonuc = senaryolar(GATE)
    kirik = [(a, d) for a, ok, d in sonuc if not ok]
    for ad, ok, detay in sonuc:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok:
            print("         gorulen: %s" % detay)
    print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

    print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
    mut_kirik, yama_kirik = [], []
    # ⚠ Mutant GERCEK validators/ dizininde yasar (B24): gate komsu `utils.`
    # modullerini kendi konumundan cozer.
    mutant = GATE.with_name("_mutant_console_utf8.py")
    for ad, mut in MUTASYONLAR:
        bozuk = mut(ham)
        if bozuk == ham:
            print("  [YAMA TUTMADI] %s" % ad)
            yama_kirik.append(ad)
            continue
        try:
            mutant.write_text(bozuk, encoding="utf-8")
            m_res = senaryolar(mutant)
            yakalandi = any(not ok for _, ok, _ in m_res)
            kacan = [a for a, ok, _ in m_res if not ok]
        except BaseException as e:  # noqa: BLE001
            yakalandi, kacan = False, []
            print("  [KURULAMADI] %s -> %s: %s" % (ad, type(e).__name__, e))
        finally:
            mutant.unlink(missing_ok=True)
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
