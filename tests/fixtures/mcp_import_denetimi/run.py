#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mcp_import_denetimi — MCP sunucusu IMPORT edilemiyorsa kurulum "TAMAM" DEMEZ (Q335).

KUSUR (Issue #274, 2026-09-18 — tüketici makinede ölçüldü, burada yeniden üretildi):
  · `mcp_servers/sap_adt/requirements.txt` `mcp>=1.0.0` üst sınırsızdı → temiz makinede pip
    `mcp 2.x` kurar; 2.x'te `mcp.server.fastmcp` import anında `ModuleNotFoundError: ...
    or pin 'mcp<2' to keep running v1 code.` fırlatan bir SHIM'dir ⇒ sunucu hiç açılmaz.
  · `team_setup` smoke'u bunu GÖRDÜ ama WARN saydı, çıktının İLK 60 karakterini bastı
    (`Traceback (most recent call last): ...` — bilgi taşımaz) ve kurulum `team_setup TAMAM`
    + exit 0 ile bitti.
  · `ix_doctor` bu yüzeye HİÇ bakmıyordu (K5 yalnız `server.py` dosya varlığı).

⭐ SAHTE `mcp` PAKETİ, GERÇEK ZİNCİR: fixture `mcp`'nin iki sahte sürümünü (v1 = asgari
FastMCP · v2 = gerçek 2.x shim'inin mesajını taklit eden ModuleNotFoundError) PYTHONPATH'e
koyar; import edilen `mcp_servers.sap_adt.server` → `_app.py` zinciri GERÇEKTİR. CI mcp
KURMAZ (core-ci.yml, bilinçli) ⇒ gerçek SDK'ye bağımlı bir vektör CI'da koşamazdı. Bu
yol, yardımcının PYTHONPATH'i EZMEyip ÖNE EKLEMESİ sayesinde mümkündür (M4 çiviler).
⚠ Gerçek 2.x ile ölçüm (tek sefer, 2026-09-18, scratch venv mcp 2.2.0) changelog'dadır;
burada TEKRARLANMAZ (ağ + pip ister).

VEKTÖRLER
  M1  requirements: `mcp` satırı 2.x'i DIŞLAR (`<2`), alt sınır korunur
  M2  yardımcı, v2 sahtesinde (False, SON anlamlı satır) döner — traceback başlığı DEĞİL
  M3  yardımcı, v1 sahtesinde (True, import-ok) döner (KONTROL GRUBU)
  M4  PYTHONPATH: core kökü DAİMA İLK; kullanıcı yolu KORUNUR; kullanıcı yolundaki sahte
      `mcp_servers` core'u GÖLGELEYEMEZ
  M5  yardımcı: zaman aşımı → (False, TIMEOUT) · stderr boşsa stdout'un son satırı
  M6  ix_doctor CLI `--layer 5` (v2): import satırı FAIL + son satır; `.conn_adt` YOKKEN de koşar
  M7  ix_doctor CLI `--layer 5` (v1, .conn_adt dolu): import satırı PASS (KONTROL GRUBU)
  M8  team_setup CLI (v2): FAIL satırı + son satır, `team_setup TAMAM` YOK, exit ≠ 0
  M9  team_setup CLI (v1): OK satırı + `team_setup TAMAM` + exit 0 (KONTROL GRUBU)
  M10 team_setup CLI (v2, --no-smoke): `--no-smoke` sözleşmesi değişmedi (TAMAM + exit 0)

MUTASYON (bugünkü kaynaktan üretilir; çapa tam 1 kez bulunmazsa exit 2 = KURULAMADI):
  --mutasyon-ilk-satir      yardımcı İLK anlamlı satırı alır        → M2 · M6 · M8 düşer
  --mutasyon-ezme           yardımcı PYTHONPATH'i EZER (eski davranış)→ M4 (+ M6/M8) düşer
  --mutasyon-doctor-kablosuz ix_doctor 5b2 satırı çağrılmaz          → M6 · M7 düşer
  --mutasyon-warn           team_setup eski sözleşme (WARN + TAMAM)  → M8 düşer
  --mutasyon-pinsiz         requirements `<2` sınırı yok            → M1 düşer
TABAN (eski kod, tek seferlik ölçüm): --kaynak-dizini <DIR> → DIR içindeki `team_setup.py`,
  `ix_doctor.py`, `requirements.txt` (varsa) GERÇEK `__file__` ile koşulur.

⛔ SAP'ye bağlanmaz, ağ kullanmaz. Sandbox proje temp'tedir; team_setup'ın kurduğu
junction'lar silme ÖNCESİ bağ olarak kaldırılır (hedef = gerçek core, ASLA silinmez).
Çıkış: 0 hepsi beklendiği gibi · 1 sapma · 2 KURULAMADI (mutasyon çapası / ortam)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TS = REPO / "scripts" / "team_setup.py"
DOCTOR = REPO / "scripts" / "ix_doctor.py"
YARDIMCI = REPO / "scripts" / "utils" / "mcp_import_denetimi.py"
REQ = REPO / "mcp_servers" / "sap_adt" / "requirements.txt"
KOSUCU = HERE / "_kosucu.py"

GECERLI_KIP = ("--mutasyon-ilk-satir", "--mutasyon-ezme", "--mutasyon-doctor-kablosuz",
               "--mutasyon-warn", "--mutasyon-pinsiz")
KIP: set[str] = set()
KAYNAK_DIZINI: Path | None = None
_a = sys.argv[1:]
while _a:
    x = _a.pop(0)
    if x == "--kaynak-dizini" and _a:
        KAYNAK_DIZINI = Path(_a.pop(0)).resolve()
    elif x in GECERLI_KIP:
        KIP.add(x)
    else:
        print(f"[DURDU] bilinmeyen arguman: {x!r} — gecerli: {list(GECERLI_KIP)} + --kaynak-dizini")
        sys.exit(2)

# v2 sahtesinin mesajı gerçek 2.2.0 shim'inin mesaj KALIBINI taşır (ölçüldü 2026-09-18);
# sondaki [SAHTE-V2] çapası "SON satır basıldı" iddiasını ayırt edici kılar.
V2_CAPA = "or pin 'mcp<2' to keep running v1 code. [SAHTE-V2]"
TRACEBACK_BASLIK = "Traceback (most recent call last)"

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul), detay))
    # ⚠ Detay, ölçülen ÇIKTIYI alıntılar; `--mutasyon-ilk-satir`da o çıktı tam olarak traceback
    # BAŞLIĞIDIR. Ham basılırsa `run_battery` onu KOŞUCUNUN çökmesi sanır (COKME_IZI) ve
    # düşen mutasyonu COKTU sınıflar (ölçüldü 2026-09-18). Alıntı işaretlenir, bilgi korunur.
    detay = detay.replace(TRACEBACK_BASLIK, "<TRACEBACK-BASLIGI>")
    print(f"  [{'OK' if kosul else 'FAIL'}] {ad}" + (f"  -- {detay}" if not kosul and detay else ""))


def _dur(neden: str) -> None:
    print(f"[DURDU] KURULAMADI: {neden} (sayi raporlanmiyor — KURULAMADI != KACTI)")
    sys.exit(2)


def _degistir(metin: str, eski: str, yeni: str, ad: str) -> str:
    n = metin.count(eski)
    if n != 1:
        _dur(f"{ad} capasi {n} kez bulundu (1 bekleniyordu): {eski[:70]!r}")
    return metin.replace(eski, yeni)


# ── kaynaklar (gerçek · taban · mutant) ─────────────────────────────────────────
def _yardimci_metni() -> str:
    m = YARDIMCI.read_text(encoding="utf-8")
    if "--mutasyon-ilk-satir" in KIP:
        m = _degistir(m, 'for satir in reversed((metin or "").splitlines()):',
                      'for satir in (metin or "").splitlines():', "ilk-satir")
    if "--mutasyon-ezme" in KIP:
        m = _degistir(m, 'env["PYTHONPATH"] = str(core_root) + (os.pathsep + onceki if onceki else "")',
                      'env["PYTHONPATH"] = str(core_root)', "ezme")
    return m


def _doctor_metni() -> str | None:
    if KAYNAK_DIZINI is not None:
        return (KAYNAK_DIZINI / "ix_doctor.py").read_text(encoding="utf-8")
    if "--mutasyon-doctor-kablosuz" in KIP:
        m = DOCTOR.read_text(encoding="utf-8")
        return _degistir(m, "    r.append(_mcp_import_kontrol())\n", "", "doctor-kablosuz")
    return None


def _ts_metni() -> str | None:
    if KAYNAK_DIZINI is not None:
        return (KAYNAK_DIZINI / "team_setup.py").read_text(encoding="utf-8")
    if "--mutasyon-warn" in KIP:
        m = TS.read_text(encoding="utf-8")
        m = _degistir(m, 'say(FAIL, f"MCP server import smoke BAŞARISIZ',
                      'say(WARN, f"MCP server import smoke BAŞARISIZ', "warn-1")
        return _degistir(m, "if not a.no_smoke and not smoke(proje):",
                         "if not a.no_smoke and not (smoke(proje) or True):", "warn-2")
    return None


def _req_metni() -> str:
    if KAYNAK_DIZINI is not None and (KAYNAK_DIZINI / "requirements.txt").is_file():
        return (KAYNAK_DIZINI / "requirements.txt").read_text(encoding="utf-8")
    m = REQ.read_text(encoding="utf-8")
    if "--mutasyon-pinsiz" in KIP:
        m = _degistir(m, "mcp>=1.0.0,<2", "mcp>=1.0.0", "pinsiz")
    return m


def _yardimci_modul():
    mod = types.ModuleType("_ix_mcp_import_denetimi")
    mod.__file__ = str(YARDIMCI)
    exec(compile(_yardimci_metni(), str(YARDIMCI), "exec"), mod.__dict__)
    return mod


# ── sandbox parçaları ──────────────────────────────────────────────────────────
def _yaz(p: Path, metin: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(metin, encoding="utf-8", newline="\n")


def sahte_mcp(kok: Path, surum: str) -> Path:
    d = kok / f"sahte_mcp_{surum}"
    _yaz(d / "mcp" / "__init__.py", "")
    _yaz(d / "mcp" / "server" / "__init__.py", "")
    if surum == "v1":
        _yaz(d / "mcp" / "server" / "fastmcp.py",
             "class FastMCP:\n"
             "    def __init__(self, *a, **k):\n        pass\n"
             "    def tool(self, *a, **k):\n        return lambda fn: fn\n"
             "    def run(self, *a, **k):\n        pass\n")
    else:
        _yaz(d / "mcp" / "server" / "fastmcp.py",
             "_MESSAGE = (\"No module named 'mcp.server.fastmcp'. This is mcp 2.x, where FastMCP \"\n"
             f"            \"was renamed to MCPServer ... {V2_CAPA}\")\n"
             "raise ModuleNotFoundError(_MESSAGE, name=__name__)\n")
    return d


def sahte_core(kok: Path) -> Path:
    """Yardımcının kenar dalları için asgari sahte core: server.py davranışı env ile seçilir."""
    c = kok / "sahte_core"
    _yaz(c / "mcp_servers" / "__init__.py", "")
    _yaz(c / "mcp_servers" / "sap_adt" / "__init__.py", "")
    _yaz(c / "mcp_servers" / "sap_adt" / "server.py",
         "import os, sys, time\n"
         "d = os.environ.get('SAHTE_DAVRANIS', '')\n"
         "if d == 'uyu':\n    time.sleep(20)\n"
         "elif d == 'stdout':\n    print('ilk-stdout-satiri'); print('STDOUT-SON-SATIR-CAPASI'); sys.exit(3)\n")
    return c


def golge_mcp_servers(kok: Path) -> Path:
    """Kullanıcı PYTHONPATH'inde core'u GÖLGELEMEYE çalışan sahte `mcp_servers`."""
    g = kok / "golge"
    _yaz(g / "mcp_servers" / "__init__.py", "raise ImportError('GOLGE-MCP-SERVERS-KAZANDI')\n")
    return g


def _bag_mi(p: Path) -> bool:
    try:
        os.readlink(p)
        return True
    except (OSError, ValueError):
        return False


def _baglari_kaldir(kok: Path) -> None:
    """team_setup'ın kurduğu junction/symlink'leri BAĞ olarak kaldır (hedef = gerçek core)."""
    for dp, dns, _ in os.walk(kok):
        for dn in list(dns):
            p = Path(dp) / dn
            if _bag_mi(p):
                try:
                    os.rmdir(p)
                except OSError:
                    try:
                        os.unlink(p)
                    except OSError:
                        pass
                dns.remove(dn)


def _sil(d: Path) -> None:
    _baglari_kaldir(d)

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


def _ortam(pythonpath: Path, proje: Path | None = None) -> dict:
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONPATH=str(pythonpath))
    if proje is not None:
        env["CLAUDE_PROJECT_DIR"] = str(proje)
    return env


def _kos(hedef: Path, hedef_metni: str | None, argumanlar: list[str], env: dict,
         tmp: Path, cwd: Path) -> tuple[int, str]:
    kaynak = "-"
    if hedef_metni is not None:
        kaynak_yol = tmp / f"_kaynak_{hedef.stem}.py"
        kaynak_yol.write_text(hedef_metni, encoding="utf-8", newline="\n")
        kaynak = str(kaynak_yol)
    yard_yol = tmp / "_yardimci.py"
    yard_yol.write_text(_yardimci_metni(), encoding="utf-8", newline="\n")
    r = subprocess.run([sys.executable, str(KOSUCU), str(hedef), kaynak, str(yard_yol),
                        *argumanlar], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env, cwd=str(cwd), timeout=240)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def _doctor_import_satiri(cikti: str) -> dict | None:
    try:
        veri = json.loads(cikti[cikti.index("{"):])
    except Exception:
        return None
    for k in veri.get("katmanlar", []):
        for c in k.get("kontroller", []):
            if "MCP server import" in c.get("mesaj", "") or "MCP server IMPORT" in c.get("mesaj", ""):
                return c
    return {}


# ══════════════════════════════════════════════════════════════════════════════
def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="ix_mcpimp_"))
    try:
        v1, v2 = sahte_mcp(tmp, "v1"), sahte_mcp(tmp, "v2")
        yard = _yardimci_modul()

        # ── M1 requirements ────────────────────────────────────────────────────
        req = _req_metni()
        mcp_satiri = next((s.strip() for s in req.splitlines()
                           if re.match(r"\s*mcp\s*(?:[<>=!~;,\[]|$)", s)), "")
        kontrol("M1 requirements `mcp` satiri 2.x'i DISLAR (<2) + alt sinir korunur",
                bool(re.search(r"<\s*2(?:\.0)*(?![\d.])", mcp_satiri)) and ">=1.0.0" in mcp_satiri,
                f"mcp satiri={mcp_satiri!r}")

        # ── M2/M3 yardımcı, gerçek core + sahte mcp ────────────────────────────
        onceki = os.environ.get("PYTHONPATH")
        try:
            os.environ["PYTHONPATH"] = str(v2)
            ok2, ayr2 = yard.mcp_import_denetimi(REPO, tmp)
            os.environ["PYTHONPATH"] = str(v1)
            ok1, ayr1 = yard.mcp_import_denetimi(REPO, tmp)
        finally:
            if onceki is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = onceki
        kontrol("M2 v2: (False, SON anlamli satir) — shim mesaji tasinir, traceback basligi DEGIL",
                ok2 is False and ayr2.endswith(V2_CAPA) and TRACEBACK_BASLIK not in ayr2,
                f"ok={ok2} ayrinti={ayr2[:160]!r}")
        kontrol("M3 v1 (KONTROL GRUBU): (True, import-ok)", ok1 is True and ayr1 == "import-ok",
                f"ok={ok1} ayrinti={ayr1[:160]!r}")

        # ── M4 PYTHONPATH önceliği ─────────────────────────────────────────────
        e_bos = yard.alt_surec_ortami(REPO, tmp, {})
        e_dolu = yard.alt_surec_ortami(REPO, tmp, {"PYTHONPATH": str(v1)})
        parca = e_dolu["PYTHONPATH"].split(os.pathsep)
        kontrol("M4a core kok DAIMA ILK, kullanici yolu KORUNUR",
                e_bos["PYTHONPATH"] == str(REPO) and parca == [str(REPO), str(v1)],
                f"bos={e_bos['PYTHONPATH']!r} dolu={parca!r}")
        golge = golge_mcp_servers(tmp)
        try:
            os.environ["PYTHONPATH"] = os.pathsep.join([str(golge), str(v1)])
            okg, ayrg = yard.mcp_import_denetimi(REPO, tmp)
        finally:
            if onceki is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = onceki
        kontrol("M4b kullanici yolundaki sahte `mcp_servers` core'u GOLGELEYEMEZ",
                okg is True and "GOLGE" not in ayrg, f"ok={okg} ayrinti={ayrg[:160]!r}")

        # ── M5 kenar dalları (sahte core) ─────────────────────────────────────
        sc = sahte_core(tmp)
        os.environ["SAHTE_DAVRANIS"] = "uyu"
        try:
            okt, ayrt = yard.mcp_import_denetimi(sc, tmp, timeout=2)
            os.environ["SAHTE_DAVRANIS"] = "stdout"
            oks, ayrs = yard.mcp_import_denetimi(sc, tmp, timeout=30)
        finally:
            os.environ.pop("SAHTE_DAVRANIS", None)
        kontrol("M5a zaman asimi → (False, TIMEOUT) — sessiz gecmez",
                okt is False and "TIMEOUT" in ayrt, f"ok={okt} ayrinti={ayrt!r}")
        kontrol("M5b stderr bossa stdout'un SON satiri + exit kodu",
                oks is False and ayrs == "exit 3: STDOUT-SON-SATIR-CAPASI", f"ayrinti={ayrs!r}")

        # ── M6/M7 ix_doctor CLI ────────────────────────────────────────────────
        pd = tmp / "doctor_proje"
        pd.mkdir()
        rc6, c6 = _kos(DOCTOR, _doctor_metni(), ["--layer", "5", "--json"],
                       _ortam(v2, pd), tmp, pd)
        s6 = _doctor_import_satiri(c6)
        conn_fail = '".conn_adt YOK' in c6 or ".conn_adt YOK" in c6
        kontrol("M6 ix_doctor --layer 5 (v2, .conn_adt YOK): import satiri FAIL + son satir",
                bool(s6) and s6.get("tag") == "FAIL" and V2_CAPA in s6.get("mesaj", "")
                and TRACEBACK_BASLIK not in s6.get("mesaj", "") and conn_fail and rc6 == 1,
                f"rc={rc6} satir={s6!r} conn_fail={conn_fail} cikti_sonu={c6[-300:]!r}")
        (pd / ".conn_adt").write_text(
            "ADT_SAP_URL=https://ornek.invalid:44300\nADT_SAP_USER=ornek\n"
            "ADT_SAP_PASSWORD=ornek\nADT_SAP_CLIENT=100\n", encoding="utf-8")
        rc7, c7 = _kos(DOCTOR, _doctor_metni(), ["--layer", "5", "--json"],
                       _ortam(v1, pd), tmp, pd)
        s7 = _doctor_import_satiri(c7)
        kontrol("M7 ix_doctor --layer 5 (v1, .conn_adt dolu; KONTROL GRUBU): import satiri PASS",
                bool(s7) and s7.get("tag") == "PASS", f"rc={rc7} satir={s7!r} cikti_sonu={c7[-300:]!r}")

        # ── M8/M9/M10 team_setup CLI ───────────────────────────────────────────
        def ts(etiket: str, mcp_dizin: Path, ek: list[str]) -> tuple[int, str]:
            p = tmp / f"ts_{etiket}"
            p.mkdir()
            return _kos(TS, _ts_metni(), ["--project", str(p), "--no-install", "--no-plugins",
                                          "--no-seed", *ek], _ortam(mcp_dizin), tmp, p)

        rc8, c8 = ts("v2", v2, [])
        fail8 = [s for s in c8.splitlines() if s.startswith("[FAIL] MCP server import smoke")]
        kontrol("M8 team_setup (v2): FAIL + son satir, `team_setup TAMAM` YOK, exit != 0",
                len(fail8) == 1 and V2_CAPA in fail8[0] and TRACEBACK_BASLIK not in fail8[0]
                and "team_setup TAMAM" not in c8 and rc8 != 0
                and "team_setup BAŞARISIZ (MCP server import smoke)" in c8,
                f"rc={rc8} fail_satirlari={fail8!r} cikti_sonu={c8[-400:]!r}")
        rc9, c9 = ts("v1", v1, [])
        kontrol("M9 team_setup (v1; KONTROL GRUBU): OK + `team_setup TAMAM` + exit 0",
                rc9 == 0 and "[ OK ] MCP server import smoke" in c9 and "team_setup TAMAM" in c9,
                f"rc={rc9} cikti_sonu={c9[-400:]!r}")
        rc10, c10 = ts("nosmoke", v2, ["--no-smoke"])
        kontrol("M10 team_setup --no-smoke (v2): sozlesme degismedi (smoke yok, TAMAM, exit 0)",
                rc10 == 0 and "team_setup TAMAM" in c10 and "MCP server import smoke" not in c10,
                f"rc={rc10} cikti_sonu={c10[-400:]!r}")
    finally:
        _sil(tmp)

    ok = sum(1 for _, k, _ in SONUC if k)
    etiket = (" [TABAN " + str(KAYNAK_DIZINI) + "]") if KAYNAK_DIZINI else \
        (" [" + " ".join(sorted(KIP)) + "]" if KIP else "")
    print(f"\nmcp_import_denetimi{etiket}: {ok}/{len(SONUC)} PASS")
    return 0 if ok == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
