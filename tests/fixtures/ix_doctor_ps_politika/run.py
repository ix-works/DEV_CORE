#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ix_doctor_ps_politika — K1 1e: PowerShell yürütme politikası × npm `.ps1` shim'i (Q339).

KUSUR (Issue #278, 2026-09-18): K1 1d `shutil.which` ile `npm.CMD`yi bulur ve PASS der;
PowerShell ise çıplak `npm`i `npm.ps1`e çözer ve `Restricted`/`AllSigned` politikası onu
BLOKLAR (UnauthorizedAccess). Araç kurulu, ama kullanıcının birincil kabuğunda çağrılamıyor.

⛔ TASARIM ÇİVİSİ: politika KAYIT DEFTERİNDEN okunur, ALT SÜREÇ AÇILMAZ. Alt süreçteki
`Get-ExecutionPolicy` çağıranın SÜREÇ kapsamını (env `PSExecutionPolicyPreference`, örn.
araçların `Bypass`'ı) devralır ⇒ kullanıcının etkin politikası yerine onu raporlar = yanlış
PASS. P9 bunu çiviler: sahte alt süreç "Bypass" döndürse bile hüküm WARN kalmalı ve hiçbir
alt süreç denenmemeli.

Bu korpus kayıt defterini SAHTE okuyucuyla besler (CI Linux'tur, `winreg` yok) ve
`_WINDOWS`'u zorlar. C3 GERÇEK platformu ölçer: Windows'ta gerçek kayıt okuması bir politika
satırı üretmeli (ÖLÇÜLEMEDİ değil); Windows-dışında 1e HİÇBİR satır eklememeli.

VEKTÖRLER
  P1  kayıt yok + shim      → WARN (varsayılan Restricted) + çare + shim adı
  P2  HKCU RemoteSigned     → PASS
  P3  GPO(HKLM) Restricted + HKCU RemoteSigned → WARN (GPO öncelikli) + "EZEMEZ" çaresi
  P4  GPO(HKCU) EnableScripts=0 → WARN
  P5  HKLM LocalMachine AllSigned → WARN
  P6  okuyucu hata verir    → WARN "ÖLÇÜLEMEDİ" (sessiz geçmez, PASS değil)
  P7  Restricted ama .ps1 shim YOK → PASS (FP çapası: gereksiz WARN yok)
  P8  Windows-dışı          → [] (hiçbir satır)
  P9  env Bypass + sahte alt süreç "Bypass" → yine WARN + alt süreç DENENMEDİ
  P10 hiçbir vektörde FAIL etiketi yok
  P11 HKCU Unrestricted + HKLM Restricted → PASS (CurrentUser > LocalMachine)
  W1  KABLOLAMA: `katman1()` 1e satırını üretir (gerçek 1d `shutil.which` + sahte PATH)
  C3  GERÇEK platform (3. bağlam)

MUTASYON (bugünkü kaynaktan; çapa tam 1 kez bulunmazsa exit 2):
  --mutasyon-kablosuz   katman1 1e'yi çağırmaz             → W1 düşer
  --mutasyon-alt-surec  politika `powershell` alt sürecinden → P9 düşer
  --mutasyon-gpo-yok    GPO anahtarları okunmaz              → P3 · P4 düşer
  --mutasyon-sessiz     okuma hatası sessizce [] döner       → P6 düşer
TABAN (eski kod): --kaynak <ix_doctor.py>

Çıkış: 0 beklendiği gibi · 1 sapma · 2 KURULAMADI
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
REPO = HERE.parents[2]
DOCTOR = REPO / "scripts" / "ix_doctor.py"
GPO = r"SOFTWARE\Policies\Microsoft\Windows\PowerShell"
SHELLID = r"SOFTWARE\Microsoft\PowerShell\1\ShellIds\Microsoft.PowerShell"

GECERLI_KIP = ("--mutasyon-kablosuz", "--mutasyon-alt-surec", "--mutasyon-gpo-yok",
               "--mutasyon-sessiz")
KIP: set[str] = set()
TABAN: Path | None = None
_a = sys.argv[1:]
while _a:
    x = _a.pop(0)
    if x == "--kaynak" and _a:
        TABAN = Path(_a.pop(0)).resolve()
    elif x in GECERLI_KIP:
        KIP.add(x)
    else:
        print(f"[DURDU] bilinmeyen arguman: {x!r} — gecerli: {list(GECERLI_KIP)} + --kaynak")
        sys.exit(2)

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul), detay))
    print(f"  [{'OK' if kosul else 'FAIL'}] {ad}" + (f"  -- {detay}" if not kosul and detay else ""))


def _degistir(metin: str, eski: str, yeni: str, ad: str) -> str:
    n = metin.count(eski)
    if n != 1:
        print(f"[DURDU] KURULAMADI: {ad} capasi {n} kez bulundu (1 bekleniyordu): {eski[:70]!r}")
        sys.exit(2)
    return metin.replace(eski, yeni)


def _kaynak() -> str:
    if TABAN is not None:
        return TABAN.read_text(encoding="utf-8")
    m = DOCTOR.read_text(encoding="utf-8")
    if "--mutasyon-kablosuz" in KIP:
        m = _degistir(m, "    r += _ps_politika_kontrol(bulunan)\n", "", "kablosuz")
    if "--mutasyon-alt-surec" in KIP:
        m = _degistir(m, "    oku = okuyucu or _kayit_oku\n",
                      "    oku = okuyucu or _kayit_oku\n"
                      "    _p = subprocess.run([\"powershell\", \"-NoProfile\", \"-Command\", "
                      "\"Get-ExecutionPolicy\"], capture_output=True, text=True).stdout.strip()\n"
                      "    if _p:\n        return _p, \"alt-surec\"\n", "alt-surec")
    if "--mutasyon-gpo-yok" in KIP:
        m = _degistir(m, '(("HKLM", "GPO/MachinePolicy"), ("HKCU", "GPO/UserPolicy"))', "()", "gpo-yok")
    if "--mutasyon-sessiz" in KIP:
        m = _degistir(m, '        return [(WARN, f"PowerShell yürütme politikası ÖLÇÜLEMEDİ',
                      '        return []\n        return [(WARN, f"PowerShell yürütme politikası ÖLÇÜLEMEDİ',
                      "sessiz")
    return m


def _yukle(proje: Path) -> dict:
    os.environ["CLAUDE_PROJECT_DIR"] = str(proje)
    g = {"__name__": "ix_doctor_ps", "__file__": str(DOCTOR), "__builtins__": __builtins__}
    exec(compile(_kaynak(), str(DOCTOR), "exec"), g)
    return g


def okuyucu(degerler: dict):
    def oku(kok: str, yol: str, ad: str):
        return degerler.get((kok, yol, ad))
    return oku


def _hatali(*_a):
    raise PermissionError("erisim reddedildi (sahte)")


class _AltSurecIzi:
    """subprocess.run/Popen yerine: çağrıyı kaydeder, çocuğun SÜREÇ kapsamını devraldığını
    taklit ederek 'Bypass' döndürür (ALT SÜREÇ YOLUNUN tam olarak neden yanlış olduğu)."""
    def __init__(self):
        self.cagri = 0

    def run(self, *a, **k):
        self.cagri += 1
        return subprocess.CompletedProcess(a[0] if a else [], 0, stdout="Bypass\n", stderr="")

    def popen(self, *a, **k):
        self.cagri += 1
        raise OSError("alt surec yasak (fixture)")


def _sil(d: Path) -> None:
    def _ac(func, path, _exc):  # noqa: ANN001
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass
    kw = {"onexc": _ac} if sys.version_info >= (3, 12) else {"onerror": _ac}
    try:
        shutil.rmtree(d, **kw)  # type: ignore[arg-type]
    except Exception:
        shutil.rmtree(d, ignore_errors=True)


def _cli_dizini(kok: Path, ps1: bool) -> Path:
    d = kok / ("cli_ps1" if ps1 else "cli_cmd")
    d.mkdir()
    for ad in ("npm", "npm.CMD") + (("npm.ps1",) if ps1 else ()):
        p = d / ad
        p.write_text("@echo off\n" if ad.endswith(".CMD") else "#!/bin/sh\nexit 0\n", encoding="utf-8")
        p.chmod(0o755)
    return d


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="ix_pspol_"))
    eski_path = os.environ.get("PATH", "")
    eski_pp = os.environ.get("PSExecutionPolicyPreference")
    try:
        (tmp / "proje").mkdir()
        g = _yukle(tmp / "proje")
        fn = g.get("_ps_politika_kontrol")
        gercek_windows = g.get("_WINDOWS")
        ps1_dir, cmd_dir = _cli_dizini(tmp, True), _cli_dizini(tmp, False)
        shim = {"npm": str(ps1_dir / "npm.CMD")}
        shimsiz = {"npm": str(cmd_dir / "npm.CMD")}

        def kos(bulunan, oku):
            if fn is None:
                return None
            g["_WINDOWS"] = True
            try:
                return fn(bulunan, oku)
            finally:
                g["_WINDOWS"] = gercek_windows

        def tag(r):
            return [t for t, _ in r] if r is not None else None

        tum: list = []
        r1 = kos(shim, okuyucu({}))
        tum.append(r1)
        kontrol("P1 kayit yok + shim → WARN (varsayilan Restricted) + care + shim adi",
                tag(r1) == ["WARN"] and "Restricted" in r1[0][1] and "varsayılan" in r1[0][1]
                and "Set-ExecutionPolicy -Scope CurrentUser RemoteSigned" in r1[0][1]
                and "npm" in r1[0][1], f"{r1}")
        r2 = kos(shim, okuyucu({("HKCU", SHELLID, "ExecutionPolicy"): "RemoteSigned"}))
        tum.append(r2)
        kontrol("P2 HKCU RemoteSigned → PASS", tag(r2) == ["PASS"] and "RemoteSigned" in r2[0][1], f"{r2}")
        r3 = kos(shim, okuyucu({("HKLM", GPO, "ExecutionPolicy"): "Restricted",
                                ("HKCU", SHELLID, "ExecutionPolicy"): "RemoteSigned"}))
        tum.append(r3)
        kontrol("P3 GPO(HKLM) Restricted > HKCU RemoteSigned → WARN + GPO 'EZEMEZ' caresi",
                tag(r3) == ["WARN"] and "GPO/MachinePolicy" in r3[0][1] and "EZEMEZ" in r3[0][1], f"{r3}")
        r4 = kos(shim, okuyucu({("HKCU", GPO, "EnableScripts"): 0,
                                ("HKCU", SHELLID, "ExecutionPolicy"): "RemoteSigned"}))
        tum.append(r4)
        kontrol("P4 GPO(HKCU) EnableScripts=0 → WARN", tag(r4) == ["WARN"] and "EnableScripts=0" in r4[0][1], f"{r4}")
        r5 = kos(shim, okuyucu({("HKLM", SHELLID, "ExecutionPolicy"): "AllSigned"}))
        tum.append(r5)
        kontrol("P5 HKLM LocalMachine AllSigned → WARN", tag(r5) == ["WARN"] and "AllSigned" in r5[0][1], f"{r5}")
        r6 = kos(shim, _hatali)
        tum.append(r6)
        kontrol("P6 okuyucu hata → WARN 'ÖLÇÜLEMEDİ' (PASS degil, sessiz degil)",
                tag(r6) == ["WARN"] and "ÖLÇÜLEMEDİ" in r6[0][1], f"{r6}")
        r7 = kos(shimsiz, okuyucu({}))
        tum.append(r7)
        kontrol("P7 Restricted ama .ps1 shim YOK → PASS (FP capasi)",
                tag(r7) == ["PASS"] and "shim'i yok" in r7[0][1], f"{r7}")
        r8 = fn(shim, okuyucu({})) if (fn is not None and not gercek_windows) else None
        if fn is not None and gercek_windows:
            g["_WINDOWS"] = False
            try:
                r8 = fn(shim, okuyucu({}))
            finally:
                g["_WINDOWS"] = gercek_windows
        kontrol("P8 Windows-disi → [] (hicbir satir)", r8 == [], f"{r8}")

        iz = _AltSurecIzi()
        os.environ["PSExecutionPolicyPreference"] = "Bypass"
        esk_run, esk_popen = subprocess.run, subprocess.Popen
        subprocess.run, subprocess.Popen = iz.run, iz.popen  # type: ignore[assignment]
        try:
            r9 = kos(shim, okuyucu({}))
        finally:
            subprocess.run, subprocess.Popen = esk_run, esk_popen  # type: ignore[assignment]
            if eski_pp is None:
                os.environ.pop("PSExecutionPolicyPreference", None)
            else:
                os.environ["PSExecutionPolicyPreference"] = eski_pp
        tum.append(r9)
        kontrol("P9 env Bypass + alt surec 'Bypass' → yine WARN, alt surec DENENMEDI",
                tag(r9) == ["WARN"] and iz.cagri == 0, f"{r9} alt_surec_cagri={iz.cagri}")
        r11 = kos(shim, okuyucu({("HKCU", SHELLID, "ExecutionPolicy"): "Unrestricted",
                                 ("HKLM", SHELLID, "ExecutionPolicy"): "Restricted"}))
        tum.append(r11)
        kontrol("P11 HKCU Unrestricted > HKLM Restricted → PASS", tag(r11) == ["PASS"], f"{r11}")
        kontrol("P10 hicbir vektorde FAIL etiketi yok",
                fn is not None and all(r is not None and "FAIL" not in tag(r) for r in tum), "")

        # ── W1 kablolama: gerçek katman1 → gerçek 1d `shutil.which` (sahte PATH) → 1e
        # ⛔ Yamalar finally'de GERİ ALINIR: ilk yazımda `_kayit_oku` geri alınmıyordu ve C3
        # "gerçek kayıt defteri" diye SAHTE okuyucuyu ölçtü (bu makinede HKCU=RemoteSigned
        # iken C3 "varsayılan Restricted" bastı ve YEŞİL geçti — sahte-yeşil, 2026-09-18).
        gercek_oku, gercek_run = g["_kayit_oku"], g["_run"]
        os.environ["PATH"] = str(ps1_dir)
        g["_WINDOWS"], g["_kayit_oku"] = True, okuyucu({})
        g["_run"] = lambda *a, **k: (0, "")          # setup_plugins --list (claude CLI) atlanır
        try:
            k1 = g["katman1"]()
        except Exception as e:  # noqa: BLE001
            k1 = [("HATA", f"{type(e).__name__}: {e}")]
        finally:
            os.environ["PATH"] = eski_path
            g["_WINDOWS"], g["_kayit_oku"], g["_run"] = gercek_windows, gercek_oku, gercek_run
        satir = [(t, m) for t, m in k1 if "PowerShell yürütme politikası" in m]
        kontrol("W1 KABLOLAMA: katman1 1e satirini uretir (1d which → .ps1 shim → WARN)",
                len(satir) == 1 and satir[0][0] == "WARN" and "npm" in satir[0][1], f"{satir or k1[-3:]}")

        # ── C3 gerçek platform ─────────────────────────────────────────────────
        if fn is None:
            kontrol("C3 GERCEK platform", False, "_ps_politika_kontrol yok (eski kod)")
        elif gercek_windows:
            gr = fn(shim)                             # GERÇEK `_kayit_oku` (winreg)
            # Kontrol grubu: aynı değeri `reg query` (ayrı araç, alt süreç YALNIZ fixture'da)
            # okur — ÜRETİM kodu okumuyor. HKCU ShellIds'te değer varsa satır onu taşımalı.
            rq = subprocess.run(["reg", "query", "HKCU\\" + SHELLID, "/v", "ExecutionPolicy"],
                                capture_output=True, text=True, errors="replace")
            hkcu = (rq.stdout.split("REG_SZ")[-1].strip() if rq.returncode == 0 and "REG_SZ" in rq.stdout
                    else "")
            gpo_var = any(subprocess.run(["reg", "query", kok + "\\" + GPO], capture_output=True
                                         ).returncode == 0 for kok in ("HKLM", "HKCU"))
            if gpo_var:
                hkcu = ""                             # GPO HKCU'yu ezer → kıyas anlamsız
            kontrol("C3 GERCEK Windows kayit defteri → politika satiri (OLCULEMEDI degil; "
                    "HKCU degeri varsa satir onu tasir — `reg query` kontrol grubu)",
                    len(gr) == 1 and gr[0][0] in ("PASS", "WARN") and "ÖLÇÜLEMEDİ" not in gr[0][1]
                    and (not hkcu or f"yürütme politikası {hkcu} " in gr[0][1]),
                    f"{gr} reg_query_hkcu={hkcu!r}")
            print(f"  [BILGI] bu makine: {gr[0][1][:140] if gr else '-'}")
        else:
            kontrol("C3 GERCEK Windows-disi platform → 1e hicbir satir eklemez", fn(shim) == [], "")
    finally:
        os.environ["PATH"] = eski_path
        _sil(tmp)

    ok = sum(1 for _, k, _ in SONUC if k)
    etiket = f" [TABAN {TABAN}]" if TABAN else (f" [{' '.join(sorted(KIP))}]" if KIP else "")
    print(f"\nix_doctor_ps_politika{etiket}: {ok}/{len(SONUC)} PASS")
    return 0 if ok == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
