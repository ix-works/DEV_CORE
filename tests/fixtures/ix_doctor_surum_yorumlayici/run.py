#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ix_doctor_surum_yorumlayici — K1 1f (Claude Code sürümü) + 1g (hook yorumlayıcısı) (Q365①).

KUSUR (dış repo karşılaştırması 2026-10-12): 1d `claude`'un yalnız PATH VARLIĞINA bakıyordu;
4d hook smoke'u hook'u `sys.executable` ile koşuyordu. Claude Code ise settings'teki
`"command": "python"`ı KENDİ PATH çözümüyle başlatır. Windows'ta `WindowsApps\\python.exe`
Microsoft Store yönlendiricisidir (ölçüldü: `-c` ile rc=9009/49, "Python was not found") —
PATH'te önde olursa hiçbir hook başlamaz, `pre_tool_guard` bloklamaz ve 4d yine PASS der.

⛔ TASARIM ÇİVİLERİ: (a) ikisi de FAIL ÜRETMEZ (ölçüm aracı, gate değil — ADR 0019)
(b) ayrıştırılamayan sürüm ÖLÇÜLEMEDİ'dir, sahte FAIL/PASS değil (c) prob, settings'teki
komutun PATH ÇÖZÜMÜNÜ koşar — `sys.executable`'ı DEĞİL (d) satırdaki rastgele sayı
(node uyarısı, yol) sürüm sanılmaz.

VEKTÖRLER
  S1..S11 `_claude_surum_ayristir` bilinen/bozuk dizgiler
  K1 taban üstü → PASS · K2 tabana eşit → PASS · K3 altı → WARN · K4 rc≠0 → WARN ÖLÇÜLEMEDİ
  K5 tanınmayan biçim → WARN ÖLÇÜLEMEDİ · K6 claude yok → SKIP
  Y1 exec + kabuk biçimi ayrıştırma (statusLine dahil)
  Y2 çalışan yorumlayıcı → PASS · Y3 PATH'te yok → WARN · Y4 yönlendirici-stub (rc≠0) → WARN
  Y5 eski sürüm (işaret 3.8) → WARN · Y6 bozuk settings → WARN ÖLÇÜLEMEDİ
  Y7 taban TEK KAYNAK: `_min_py()` == team_setup.py `MIN_PY` (bağımsız regex okuması)
  Y8 python ailesi DIŞI (sahte `nodejs_sahte`, çalışır) → SKIP ÖLÇÜLEMEDİ (sahte WARN değil)
  Y9 `${HOME}/bin/python` · Y10 `%PYDIR%\\python.exe` (genişletilmemiş) → SKIP ÖLÇÜLEMEDİ
  Z  hiçbir vektörde FAIL etiketi yok
  W1 KABLOLAMA: `katman1()` 1f + 1g satırlarını üretir
  C3 GERÇEK platform (3. bağlam): şablon settings + gerçek PATH → `python` satırı PASS;
     Windows'ta WindowsApps yönlendiricisi varsa GERÇEK stub → WARN (+ ipucu);
     `claude` PATH'teyse satır ÖLÇÜLEMEDİ değil

MUTASYON (bugünkü kaynaktan; çapa tam 1 kez bulunmazsa exit 2):
  --mutasyon-kablosuz       katman1 1g'yi çağırmaz              → W1 düşer
  --mutasyon-sys-executable prob `sys.executable`'ı koşar        → Y4 · Y5 düşer
  --mutasyon-gevsek-desen   tam-satır deseni gevşek arama olur   → S6 düşer
  --mutasyon-fail           taban altı FAIL döner                → K3 · Z düşer
  --mutasyon-aile-yok       python-ailesi süzgeci kapalı          → Y8 düşer
  --mutasyon-degisken-yok   genişletilmemiş değişken süzgeci kapalı → Y9 · Y10 düşer
TABAN (eski kod): --kaynak <ix_doctor.py>

Çıkış: 0 beklendiği gibi · 1 sapma · 2 KURULAMADI
"""
from __future__ import annotations

import json
import os
import re
import shutil
import stat
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
WINDOWS = os.name == "nt"

GECERLI_KIP = ("--mutasyon-kablosuz", "--mutasyon-sys-executable", "--mutasyon-gevsek-desen",
               "--mutasyon-fail", "--mutasyon-aile-yok", "--mutasyon-degisken-yok")
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
        m = _degistir(m, "    r += _yorumlayici_kontrol()\n", "", "kablosuz")
    if "--mutasyon-sys-executable" in KIP:
        m = _degistir(m, '        rc, out = _run([yol, "-c", ',
                      '        rc, out = _run([sys.executable, "-c", ', "sys-executable")
    if "--mutasyon-gevsek-desen" in KIP:
        m = _degistir(m, '    re.compile(r"^\\s*v?(\\d+)\\.(\\d+)\\.(\\d+)(?:[-+][0-9A-Za-z.]+)?\\s*$"),',
                      '    re.compile(r"v?(\\d+)\\.(\\d+)\\.(\\d+)"),', "gevsek-desen")
    if "--mutasyon-fail" in KIP:
        m = _degistir(m, '        return [(WARN, f"Claude Code {s} < ölçülmüş taban',
                      '        return [(FAIL, f"Claude Code {s} < ölçülmüş taban', "fail")
    if "--mutasyon-aile-yok" in KIP:
        m = _degistir(m, "        if not _YORUMLAYICI_PY_AILE.fullmatch(", "        if False and not _YORUMLAYICI_PY_AILE.fullmatch(",
                      "aile-yok")
    if "--mutasyon-degisken-yok" in KIP:
        m = _degistir(m, "        if _YORUMLAYICI_DEGISKEN.search(ad):", "        if False:", "degisken-yok")
    return m


def _yukle(proje: Path) -> dict:
    os.environ["CLAUDE_PROJECT_DIR"] = str(proje)
    g = {"__name__": "ix_doctor_surum", "__file__": str(DOCTOR), "__builtins__": __builtins__}
    exec(compile(_kaynak(), str(DOCTOR), "exec"), g)
    return g


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


def _sahte_yorumlayici(d: Path, ad: str, *, cikti: str, rc: int) -> Path:
    """Argümanları YOK SAYAN sahte yorumlayıcı: `cikti`yı basar, `rc` ile çıkar."""
    if WINDOWS:
        p = d / f"{ad}.cmd"
        satirlar = ["@echo off"] + [f"echo {s}" for s in cikti.splitlines()] + [f"exit /b {rc}"]
        p.write_bytes(("\r\n".join(satirlar) + "\r\n").encode("ascii"))
    else:
        p = d / ad
        satirlar = ["#!/bin/sh"] + [f"echo '{s}'" for s in cikti.splitlines()] + [f"exit {rc}"]
        p.write_bytes(("\n".join(satirlar) + "\n").encode("ascii"))
        p.chmod(0o755)
    return p


def _ayar(d: Path, ad: str, komut: str) -> Path:
    p = d / ad
    p.write_text(json.dumps({"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
        {"type": "command", "command": komut, "args": ["x.py"]}]}]}}), encoding="utf-8")
    return p


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="ix_surum_"))
    eski_path = os.environ.get("PATH", "")
    try:
        (tmp / "proje").mkdir()
        g = _yukle(tmp / "proje")
        ayr = g.get("_claude_surum_ayristir")
        kon = g.get("_claude_surum_kontrol")
        yor = g.get("_yorumlayici_kontrol")
        hk = g.get("_hook_komutlari")
        tum: list = []

        def tag(r):
            return [t for t, _ in r] if r is not None else None

        # ── S: ayrıştırma vektörleri ───────────────────────────────────────────
        vektor = [
            ("S1 '2.1.296 (Claude Code)' (olculmus bicim)", "2.1.296 (Claude Code)\n", (2, 1, 296)),
            ("S2 '2.1.269 (Claude Code)' CRLF", "2.1.269 (Claude Code)\r\n", (2, 1, 269)),
            ("S3 '1.0.128 (Claude Code)' (eski seri)", "1.0.128 (Claude Code)", (1, 0, 128)),
            ("S4 on-surum ekli '2.1.300-beta.1 (Claude Code)'", "2.1.300-beta.1 (Claude Code)", (2, 1, 300)),
            ("S5 yalin satir 'v2.1.296'", "v2.1.296\n", (2, 1, 296)),
            ("S6 node uyarisi icindeki v18.17.0 SURUM SANILMAZ",
             "(node:1234) Warning: built with v18.17.0 runtime\n2.1.296 (Claude Code)\n", (2, 1, 296)),
            ("S7 'command not found' → None", "bash: claude: command not found", None),
            ("S8 bos cikti → None", "", None),
            ("S9 eksik parca '2.1 (Claude Code)' → None", "2.1 (Claude Code)", None),
            ("S10 tanimsiz bicim 'Claude Code 3.0.0' TAHMIN EDILMEZ → None", "Claude Code 3.0.0", None),
            ("S11 yol icindeki sayi '/opt/app-1.2.3/bin' → None", "/opt/app-1.2.3/bin/claude", None),
        ]
        for ad, girdi, bek in vektor:
            got = ayr(girdi) if ayr else "YOK"
            kontrol(ad, got == bek, f"beklenen={bek} alinan={got}")

        # ── K: hüküm (sahte _run) ─────────────────────────────────────────────
        def kon_kos(rc: int, cikti: str, yol: str | None = "/sahte/claude"):
            if kon is None:
                return None
            esk = g["_run"]
            g["_run"] = lambda *a, **k: (rc, cikti)
            try:
                return kon(yol)
            finally:
                g["_run"] = esk

        k1 = kon_kos(0, "2.1.296 (Claude Code)"); tum.append(k1)
        kontrol("K1 taban USTU → PASS", tag(k1) == ["PASS"] and "2.1.296" in k1[0][1], f"{k1}")
        k2 = kon_kos(0, "2.1.269 (Claude Code)"); tum.append(k2)
        kontrol("K2 tabana ESIT → PASS", tag(k2) == ["PASS"], f"{k2}")
        k3 = kon_kos(0, "2.1.200 (Claude Code)"); tum.append(k3)
        kontrol("K3 taban ALTI → WARN + `claude update` caresi",
                tag(k3) == ["WARN"] and "claude update" in k3[0][1], f"{k3}")
        k4 = kon_kos(1, "2.1.296 (Claude Code)"); tum.append(k4)
        kontrol("K4 rc!=0 → WARN ÖLÇÜLEMEDİ (cikti gecerli gorunse de)",
                tag(k4) == ["WARN"] and "ÖLÇÜLEMEDİ" in k4[0][1], f"{k4}")
        k5 = kon_kos(0, "garip cikti"); tum.append(k5)
        kontrol("K5 taninmayan bicim → WARN ÖLÇÜLEMEDİ", tag(k5) == ["WARN"] and "ÖLÇÜLEMEDİ" in k5[0][1], f"{k5}")
        k6 = kon_kos(0, "", yol=None); tum.append(k6)
        kontrol("K6 claude PATH'te yok → SKIP", tag(k6) == ["SKIP"], f"{k6}")

        # ── Y: yorumlayıcı ────────────────────────────────────────────────────
        d = tmp / "bin"; d.mkdir()
        cfg = tmp / "cfg"; cfg.mkdir()
        y1_ayar = cfg / "karisik.json"
        y1_ayar.write_text(json.dumps({
            "statusLine": {"type": "command", "command": 'python "${CLAUDE_PROJECT_DIR}/core/x.py"'},
            "hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "python", "args": ["a"]},
                                                {"type": "command", "command": "py3x", "args": []}]}],
                      "Stop": [{"hooks": [{"type": "command", "command": '"C:/Py Dir/python.exe" -X'}]}]}}),
            encoding="utf-8")
        y1 = hk(y1_ayar) if hk else None
        kontrol("Y1 exec + kabuk bicimi ayristirma (statusLine dahil, tirnakli yol)",
                y1 == {"python": 2, "py3x": 1, "C:/Py Dir/python.exe": 1}, f"{y1}")

        y2 = yor(_ayar(cfg, "y2.json", sys.executable)) if yor else None
        tum.append(y2)
        kontrol("Y2 calisan yorumlayici → PASS (surum basilir)",
                tag(y2) == ["PASS"] and "çalışıyor (Python" in y2[0][1], f"{y2}")
        y3 = yor(_ayar(cfg, "y3.json", "ix-olmayan-yorumlayici-q365")) if yor else None
        tum.append(y3)
        kontrol("Y3 PATH'te yok → WARN 'PATH'te YOK' + fail-open uyarisi",
                tag(y3) == ["WARN"] and "PATH'te YOK" in y3[0][1] and "fail-open" in y3[0][1], f"{y3}")
        stub = _sahte_yorumlayici(d, "stub_python", cikti="Python was not found", rc=49)
        y4 = yor(_ayar(cfg, "y4.json", str(stub))) if yor else None
        tum.append(y4)
        kontrol("Y4 yonlendirici-stub (rc!=0, isaret yok) → WARN 'BAŞLAMIYOR'",
                tag(y4) == ["WARN"] and "BAŞLAMIYOR" in y4[0][1], f"{y4}")
        eski = _sahte_yorumlayici(d, "eski_python", cikti="IX-YORUMLAYICI-OK 3 8 10", rc=0)
        y5 = yor(_ayar(cfg, "y5.json", str(eski))) if yor else None
        tum.append(y5)
        kontrol("Y5 eski surum (3.8.10) → WARN < MIN_PY",
                tag(y5) == ["WARN"] and "3.8.10" in y5[0][1] and "MIN_PY" in y5[0][1], f"{y5}")
        bozuk = cfg / "bozuk.json"
        bozuk.write_text("{ bozuk json", encoding="utf-8")
        y6 = yor(bozuk) if yor else None
        tum.append(y6)
        kontrol("Y6 bozuk settings → WARN ÖLÇÜLEMEDİ (PASS degil)",
                tag(y6) == ["WARN"] and "ÖLÇÜLEMEDİ" in y6[0][1], f"{y6}")
        ts = (REPO / "scripts" / "team_setup.py").read_text(encoding="utf-8")
        mt = re.search(r"^MIN_PY\s*=\s*\((\d+),\s*(\d+)\)", ts, re.M)
        bagimsiz = (int(mt.group(1)), int(mt.group(2))) if mt else None
        mp = g["_min_py"]() if "_min_py" in g else "YOK"
        kontrol("Y7 taban TEK KAYNAK: _min_py() == team_setup.py MIN_PY",
                bagimsiz is not None and mp == bagimsiz, f"_min_py={mp} team_setup={bagimsiz}")
        nd = _sahte_yorumlayici(d, "nodejs_sahte", cikti="v20.11.0", rc=0)
        y8 = yor(_ayar(cfg, "y8.json", str(nd))) if yor else None
        tum.append(y8)
        kontrol("Y8 python ailesi DISI (calisir) → SKIP ÖLÇÜLEMEDİ, WARN degil",
                tag(y8) == ["SKIP"] and "ÖLÇÜLEMEDİ" in y8[0][1] and "python ailesi" in y8[0][1], f"{y8}")
        y9 = yor(_ayar(cfg, "y9.json", "${HOME}/bin/python")) if yor else None
        tum.append(y9)
        kontrol("Y9 `${HOME}/bin/python` → SKIP ÖLÇÜLEMEDİ (genislemis gibi davranilmaz)",
                tag(y9) == ["SKIP"] and "genişletilmemiş" in y9[0][1], f"{y9}")
        y10 = yor(_ayar(cfg, "y10.json", "%PYDIR%\\python.exe")) if yor else None
        tum.append(y10)
        kontrol("Y10 `%PYDIR%\\python.exe` → SKIP ÖLÇÜLEMEDİ",
                tag(y10) == ["SKIP"] and "genişletilmemiş" in y10[0][1], f"{y10}")
        kontrol("Z hicbir vektorde FAIL etiketi yok",
                all(r is not None and "FAIL" not in tag(r) for r in tum), "")

        # ── W1 kablolama: gerçek katman1 → 1f + 1g satırları ──────────────────
        w1_ad = "W1 KABLOLAMA: katman1 1f (Claude Code surumu) + 1g (hook yorumlayicisi) satirini uretir"
        if "katman1" not in g or "_run" not in g:
            kontrol(w1_ad, False, "katman1/_run yok")
        else:
            sahte_claude = _sahte_yorumlayici(d, "claude", cikti="2.1.296 (Claude Code)", rc=0)
            (tmp / "proje" / ".claude").mkdir()
            _ayar(tmp / "proje" / ".claude", "settings.json", str(eski))
            gercek_run = g["_run"]

            def sahte_run(args, *a, **k):
                if "--version" in args:
                    return 0, "2.1.296 (Claude Code)"
                if "-c" in args:
                    return 0, "IX-YORUMLAYICI-OK 3 11 9"
                return 0, ""                          # setup_plugins --list vb.
            os.environ["PATH"] = str(d)
            g["_run"] = sahte_run
            try:
                k1r = g["katman1"]()
            except Exception as e:  # noqa: BLE001
                k1r = [("HATA", f"{type(e).__name__}: {e}")]
            finally:
                os.environ["PATH"] = eski_path
                g["_run"] = gercek_run
            cc = [m for t, m in k1r if "ölçülmüş taban" in m]
            yy = [m for t, m in k1r if "hook yorumlayıcısı" in m]
            kontrol(w1_ad, len(cc) == 1 and len(yy) == 1 and sahte_claude.exists(),
                    f"cc={cc} yy={yy} son={k1r[-3:]}")

        # ── C3 gerçek platform ─────────────────────────────────────────────────
        if yor is None or kon is None:
            kontrol("C3 GERCEK platform", False, "1f/1g fonksiyonlari yok (eski kod)")
        else:
            gr = yor(REPO / "claude" / "settings.template.json")
            py = [(t, m) for t, m in gr if "`python`" in m]
            kontrol("C3a GERCEK sablon settings + gercek PATH → `python` satiri PASS",
                    len(py) == 1 and py[0][0] == "PASS", f"{gr}")
            wa = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WindowsApps" / "python3.exe"
            if WINDOWS and os.environ.get("LOCALAPPDATA") and os.path.lexists(wa):
                gs = yor(_ayar(cfg, "c3b.json", str(wa)))
                kontrol("C3b GERCEK WindowsApps yonlendiricisi → WARN 'BAŞLAMIYOR' + ipucu",
                        tag(gs) == ["WARN"] and "BAŞLAMIYOR" in gs[0][1]
                        and "YÖNLENDİRİCİSİ" in gs[0][1], f"{gs}")
            else:
                print("  [BILGI] C3b atlandi: bu platformda WindowsApps python3.exe yok")
            cl = shutil.which("claude")
            if cl:
                gc = kon(cl)
                kontrol("C3c GERCEK `claude --version` → satir OLCULEMEDI degil",
                        len(gc) == 1 and "ÖLÇÜLEMEDİ" not in gc[0][1], f"{gc}")
                print(f"  [BILGI] bu makine: {gc[0][1][:90]}")
            else:
                print("  [BILGI] C3c atlandi: `claude` PATH'te yok (CI beklenen)")
    finally:
        os.environ["PATH"] = eski_path
        _sil(tmp)

    ok = sum(1 for _, k, _ in SONUC if k)
    etiket = f" [TABAN {TABAN}]" if TABAN else (f" [{' '.join(sorted(KIP))}]" if KIP else "")
    print(f"\nix_doctor_surum_yorumlayici{etiket}: {ok}/{len(SONUC)} PASS")
    return 0 if ok == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
