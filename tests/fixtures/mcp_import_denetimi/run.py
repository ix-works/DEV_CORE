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
FastMCP · v2 = gerçek 2.x shim'inin mesajını taklit eden ModuleNotFoundError) yardımcının
YALNIZ-TEST `ek_yol` parametresiyle "kurulu paket" yerine koyar (`.mcp.json` PYTHONPATH'inin
ARKASINA — site-packages benzeri); import edilen `mcp_servers.sap_adt.server` → `_app.py`
zinciri GERÇEKTİR (proje `core` bağı → bu depo). CLI vektörlerinde (ix_doctor/team_setup)
`ek_yol`'u `_kosucu.py` verir (`_IX_TEST_EK_YOL`; üretim kodu bu adı OKUMAZ). CI mcp KURMAZ
(core-ci.yml, bilinçli) ⇒ gerçek SDK'ye bağımlı bir vektör CI'da koşamazdı.
⛔ Denetim ortamı = `.mcp.json` ortamı: kullanıcının PYTHONPATH'i EZİLİR (çalışma zamanı gibi).
CLI vektörlerinde kullanıcı PYTHONPATH'ine BİLEREK TERS sürüm konur (v2 ölçülürken v1, v1
ölçülürken v2) ⇒ sonuç kullanıcı yolundan gelseydi her vektör TERSİNE dönerdi.
⚠ Gerçek 2.x ile ölçüm (tek sefer, 2026-09-18, scratch venv mcp 2.2.0) changelog'dadır;
burada TEKRARLANMAZ (ağ + pip ister).

VEKTÖRLER
  M1  requirements: `mcp` satırı 2.x'i DIŞLAR (`<2`), alt sınır korunur
  M2  yardımcı, "kurulu" v2'de (False, SON anlamlı satır) döner — traceback başlığı DEĞİL
  M3  yardımcı, "kurulu" v1'de (True, import-ok) döner (KONTROL GRUBU)
  M4a denetim ortamı == `.mcp.json` ortamı (PYTHONPATH genişletilmiş değer, kullanıcı yolu YOK;
      PYTHONIOENCODING; miras env korunur; kaynak = dosya) + fixture'ın `.mcp.json`'u
      `init_project.py::MCP_JSON`'un sap-adt env'iyle BİREBİR (şekil çapası)
  M4b EZME: kullanıcı PYTHONPATH'inde çalışan v1 + "kurulu" v2 ⇒ (False) — sahte-yeşil YOK
  M4c EZME ters yön: kullanıcı PYTHONPATH'inde v2 + "kurulu" v1 ⇒ (True)
  M4d `.mcp.json` YOK ⇒ `init_project` şablonuna düşer (PYTHONPATH = <proje>/core, kaynak şablon)
  M4e ne `.mcp.json` ne şablon ⇒ (False, ÖLÇÜLEMEDİ) — fail-closed
  M4f `.mcp.json` VAR ama geçersiz JSON ⇒ (False, ÖLÇÜLEMEDİ + neden) — şablona DÜŞMEZ
  M4g `.mcp.json` VAR ama `sap-adt` sunucusu yok ⇒ (False, ÖLÇÜLEMEDİ) — şablona DÜŞMEZ
  M4h `.mcp.json` VAR, `sap-adt.env` nesne değil (liste) ⇒ (False, ÖLÇÜLEMEDİ)
  M4i `sap-adt` var ama `env` anahtarı YOK ⇒ `{}` = kullanıcı ortamı (şablona düşmez, ÖLÇÜLEMEDİ değil)
      (M4f/M4g/M4h'de "kurulu" mcp v1'dir ⇒ şablona düşülseydi `import-ok` dönerdi)
  M5  yardımcı: zaman aşımı → (False, TIMEOUT) · stderr boşsa stdout'un son satırı — sahte core
      `.mcp.json`'da MUTLAK yol olarak verilir ⇒ değer dosyadan okunmazsa iki vektör de düşer
  M6  ix_doctor CLI `--layer 5` ("kurulu" v2, kullanıcı v1): import satırı FAIL + son satır;
      `.conn_adt` YOKKEN de koşar (rc'ye bakılmaz — 5a FAIL'i de rc'yi 1 yapar, ayırt etmez)
  M7  ix_doctor CLI `--layer 5` ("kurulu" v1, kullanıcı v2, .conn_adt dolu): import satırı PASS
  M8  team_setup CLI ("kurulu" v2, kullanıcı v1): FAIL satırı + son satır, `team_setup TAMAM`
      YOK, exit ≠ 0
  M9  team_setup CLI ("kurulu" v1, kullanıcı v2): OK satırı + `team_setup TAMAM` + exit 0
  M10 team_setup CLI (v2, --no-smoke): `--no-smoke` sözleşmesi değişmedi (TAMAM + exit 0)
  M11 ix_doctor CLI: proje `core` bağı YOK ⇒ `No module named 'mcp_servers'` ⇒ FAIL satırındaki
      çare `.mcp.json`/`core` bağıdır, `pip install` DEĞİL (M6: `mcp` hatasında çare pip)
  M12 team_setup CLI: `.mcp.json` PYTHONPATH olmayan dizini gösteriyor ⇒ aynı ayrım team_setup'ta
      (M8: `mcp` hatasında çare pip)

MUTASYON (bugünkü kaynaktan üretilir; çapa tam 1 kez bulunmazsa exit 2 = KURULAMADI):
  --mutasyon-ilk-satir      yardımcı İLK anlamlı satırı alır         → M2·M4b·M5b·M6·M8·M11·M12 düşer
  --mutasyon-one-ekle       yardımcı kullanıcı PYTHONPATH'ini KORUR   → M4a·M4b·M4c·M6·M7·M8·M9 düşer
                            (ilk sürümün reddedilen davranışı — bug-gate F1)
  --mutasyon-yeniden-turet  yardımcı `.mcp.json`'u okumaz, core kökünü yazar
                            → M4a·M4d·M4e·M4f·M4g·M4h·M4i·M5a·M5b·M11·M12 düşer
  --mutasyon-doctor-kablosuz ix_doctor 5b2 satırı çağrılmaz           → M6·M7·M11 düşer
  --mutasyon-warn           team_setup eski sözleşme (WARN + TAMAM)   → M8·M12 düşer
  --mutasyon-pinsiz         requirements `<2` sınırı yok             → M1 düşer
  --mutasyon-bozuk-sablona  bozuk `.mcp.json`'da şablona düşer (ilk sürüm) → M4f·M4g·M4h düşer
  --mutasyon-envsiz-sablona `env` anahtarı yoksa ÖLÇÜLEMEDİ der          → M4i düşer
  --mutasyon-tek-care       çare metni her durumda pip                  → M11·M12 düşer
TABAN (eski kod, tek seferlik ölçüm): --kaynak-dizini <DIR> → DIR içindeki `team_setup.py`,
  `ix_doctor.py`, `requirements.txt` (varsa) GERÇEK `__file__` ile koşulur.
  ⚠ Tabanda M8 Issue senaryosunu ÜRETMEZ: eski smoke PYTHONPATH'i core'a EZER ve yardımcıyı
  çağırmaz ⇒ `ek_yol` hiç uygulanmaz, makinede kurulu GERÇEK `mcp` import edilir (bu makinede
  1.x ⇒ import-ok ⇒ M8 "OK" diye düşer; kurulu mcp yoksa hiç import edemez). M6/M7 tabanda
  5b2 satırı OLMADIĞI için düşer (satir={}); gerçek 2.x kanıtı changelog'daki venv ölçümüdür.
  Taban `ab68ba9`: 15/21 — düşenler M1·M6·M7·M8·M11·M12 (M11/M12: eski kodda çare ayrımı ve
  `.mcp.json` okuması yok).

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

GECERLI_KIP = ("--mutasyon-ilk-satir", "--mutasyon-one-ekle", "--mutasyon-yeniden-turet",
               "--mutasyon-doctor-kablosuz",
               "--mutasyon-warn", "--mutasyon-pinsiz", "--mutasyon-bozuk-sablona",
               "--mutasyon-envsiz-sablona", "--mutasyon-tek-care")
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
    if "--mutasyon-one-ekle" in KIP:
        m = _degistir(m, "        env[k] = _genislet(v, env)\n",
                      "        _y = _genislet(v, env)\n"
                      "        env[k] = (_y + os.pathsep + env[k]) if k == 'PYTHONPATH' and env.get(k) else _y\n",
                      "one-ekle")
    if "--mutasyon-yeniden-turet" in KIP:
        m = _degistir(m, "    ham, kaynak = mcp_calisma_env(core_root, proje)\n",
                      "    ham, kaynak = {'PYTHONPATH': str(core_root), 'PYTHONIOENCODING': 'utf-8'}, 'turetildi'\n",
                      "yeniden-turet")
    if "--mutasyon-bozuk-sablona" in KIP:
        m = _degistir(m, '        return None, f"{mj} bozuk: {neden} — şablona DÜŞÜLMEZ (çalışma zamanı bu dosyayla açılmaz)"\n',
                      "", "bozuk-sablona")
    if "--mutasyon-envsiz-sablona" in KIP:
        m = _degistir(m, '        return {}, "env yok (kullanıcı ortamı)"\n',
                      '        return None, "env yok"\n', "envsiz-sablona")
    if "--mutasyon-tek-care" in KIP:
        m = _degistir(m, "    if _MCP_SERVERS_YOK.search(ayrinti):\n",
                      "    if False and _MCP_SERVERS_YOK.search(ayrinti):\n", "tek-care")
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


# fixture'ın `.mcp.json` sap-adt env'i — LİTERAL (üretim fonksiyonundan türetilmez); M4a bunun
# `init_project.py::MCP_JSON` ile birebir olduğunu ayrıca çiviler (şekil çapası).
MCP_ENV = {"PYTHONIOENCODING": "utf-8", "PYTHONPATH": "${CLAUDE_PROJECT_DIR:-.}/core"}


def mcp_json_yaz(proje: Path, env: dict) -> None:
    _yaz(proje / ".mcp.json", json.dumps({"mcpServers": {"sap-adt": {
        "type": "stdio", "command": "python", "args": ["-m", "mcp_servers.sap_adt.server"],
        "env": env}}}, indent=2))


def bag_kur(bag: Path, hedef: Path) -> None:
    """`bag` → `hedef` dizin bağı (Windows junction, aksi hâlde symlink). Silme bağ-ÖNCE."""
    bag.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        import _winapi  # type: ignore
        _winapi.CreateJunction(str(hedef), str(bag))
    else:
        os.symlink(str(hedef), str(bag), target_is_directory=True)


def sablon_env() -> dict | None:
    """`init_project.py::MCP_JSON` sap-adt env'i — fixture'ın KENDİ ayrıştırması (AST)."""
    import ast
    agac = ast.parse((REPO / "scripts" / "init_project.py").read_text(encoding="utf-8"))
    for d in agac.body:
        if isinstance(d, ast.Assign) and any(getattr(h, "id", "") == "MCP_JSON" for h in d.targets):
            return json.loads(ast.literal_eval(d.value))["mcpServers"]["sap-adt"].get("env")
    return None


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


def _ortam(kurulu: Path, kullanici: Path, proje: Path | None = None) -> dict:
    """CLI ortamı: `kurulu` = "kurulu mcp" (kosucu → `ek_yol`), `kullanici` = kullanıcının
    PYTHONPATH'i (BİLEREK ters sürüm — denetim onu EZMELİ)."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONPATH=str(kullanici),
               _IX_TEST_EK_YOL=str(kurulu))
    if proje is not None:
        env["CLAUDE_PROJECT_DIR"] = str(proje)
    return env


def _kullanici_yolu(yol: Path | None):
    """os.environ PYTHONPATH'ini geçici olarak `yol` yap (None = kaldır); geri alan fonksiyon döner."""
    onceki = os.environ.get("PYTHONPATH")
    if yol is None:
        os.environ.pop("PYTHONPATH", None)
    else:
        os.environ["PYTHONPATH"] = str(yol)

    def geri() -> None:
        if onceki is None:
            os.environ.pop("PYTHONPATH", None)
        else:
            os.environ["PYTHONPATH"] = onceki
    return geri


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

        # ── M2/M3 yardımcı: gerçek core (proje `core` bağı) + "kurulu" sahte mcp ─────
        pj = tmp / "yard_proje"
        bag_kur(pj / "core", REPO)                        # `.mcp.json` YOK ⇒ şablon (M4d)
        geri = _kullanici_yolu(None)
        try:
            ok2, ayr2 = yard.mcp_import_denetimi(REPO, pj, ek_yol=[str(v2)])
            ok1, ayr1 = yard.mcp_import_denetimi(REPO, pj, ek_yol=[str(v1)])
        finally:
            geri()
        kontrol("M2 v2: (False, SON anlamli satir) — shim mesaji tasinir, traceback basligi DEGIL",
                ok2 is False and ayr2.endswith(V2_CAPA) and TRACEBACK_BASLIK not in ayr2,
                f"ok={ok2} ayrinti={ayr2[:160]!r}")
        kontrol("M3 v1 (KONTROL GRUBU): (True, import-ok)", ok1 is True and ayr1 == "import-ok",
                f"ok={ok1} ayrinti={ayr1[:160]!r}")

        # ── M4 ortam = .mcp.json ortamı ──────────────────────────────────────────
        pm = tmp / "mcpjson_proje"
        bag_kur(pm / "core", REPO)
        mcp_json_yaz(pm, MCP_ENV)
        taban = {"PYTHONPATH": str(v1), "IX_MIRAS": "korunur", "PYTHONIOENCODING": "cp1252"}
        e_a, k_a = yard.alt_surec_ortami(REPO, pm, taban)
        beklenen_pp = str(pm) + "/core"
        sablon = sablon_env()
        kontrol("M4a denetim ortami == .mcp.json ortami (kullanici PYTHONPATH'i YOK) + sekil capasi",
                e_a is not None and e_a.get("PYTHONPATH") == beklenen_pp
                and e_a.get("PYTHONIOENCODING") == "utf-8" and e_a.get("IX_MIRAS") == "korunur"
                and e_a.get("CLAUDE_PROJECT_DIR") == str(pm) and k_a == str(pm / ".mcp.json")
                and sablon == MCP_ENV,
                f"PYTHONPATH={None if e_a is None else e_a.get('PYTHONPATH')!r} beklenen={beklenen_pp!r} "
                f"kaynak={k_a!r} sablon_env={sablon!r}")
        geri = _kullanici_yolu(v1)
        try:
            okb, ayrb = yard.mcp_import_denetimi(REPO, pm, ek_yol=[str(v2)])
        finally:
            geri()
        kontrol("M4b EZME: kullanici PYTHONPATH'inde calisan v1 + kurulu v2 → (False) — sahte-yesil YOK",
                okb is False and ayrb.endswith(V2_CAPA), f"ok={okb} ayrinti={ayrb[:160]!r}")
        geri = _kullanici_yolu(v2)
        try:
            okc, ayrc = yard.mcp_import_denetimi(REPO, pm, ek_yol=[str(v1)])
        finally:
            geri()
        kontrol("M4c EZME ters yon: kullanici PYTHONPATH'inde v2 + kurulu v1 → (True)",
                okc is True and ayrc == "import-ok", f"ok={okc} ayrinti={ayrc[:160]!r}")
        e_d, k_d = yard.alt_surec_ortami(REPO, pj, {})
        kontrol("M4d .mcp.json YOK → init_project sablonu (PYTHONPATH = <proje>/core)",
                e_d is not None and e_d.get("PYTHONPATH") == str(pj) + "/core" and "şablon" in k_d,
                f"PYTHONPATH={None if e_d is None else e_d.get('PYTHONPATH')!r} kaynak={k_d!r}")
        bos_core = tmp / "bos_core"
        bos_core.mkdir()
        oke, ayre = yard.mcp_import_denetimi(bos_core, tmp / "bos_proje")
        kontrol("M4e ne .mcp.json ne sablon → (False, OLCULEMEDI) — fail-closed",
                oke is False and "ÖLÇÜLEMEDİ" in ayre, f"ok={oke} ayrinti={ayre!r}")

        def bozuk(etiket: str, metin: str) -> tuple[bool, str]:
            pb = tmp / f"bozuk_{etiket}"
            bag_kur(pb / "core", REPO)
            _yaz(pb / ".mcp.json", metin)
            geri_ = _kullanici_yolu(None)
            try:
                return yard.mcp_import_denetimi(REPO, pb, ek_yol=[str(v1)])   # kurulu = v1
            finally:
                geri_()

        okf, ayrf = bozuk("json", "{not json")
        kontrol("M4f .mcp.json VAR + gecersiz JSON → (False, OLCULEMEDI + neden), sablona DUSMEZ",
                okf is False and "ÖLÇÜLEMEDİ" in ayrf and "geçersiz JSON" in ayrf,
                f"ok={okf} ayrinti={ayrf[:200]!r}")
        okg, ayrg = bozuk("sunucusuz", json.dumps({"mcpServers": {"sap-gui": {"command": "python"}}}))
        kontrol("M4g .mcp.json VAR + sap-adt sunucusu YOK → (False, OLCULEMEDI), sablona DUSMEZ",
                okg is False and "ÖLÇÜLEMEDİ" in ayrg and "sunucusu YOK" in ayrg,
                f"ok={okg} ayrinti={ayrg[:200]!r}")
        okh, ayrh = bozuk("envliste", json.dumps({"mcpServers": {"sap-adt": {"env": ["PYTHONPATH"]}}}))
        kontrol("M4h .mcp.json sap-adt.env LISTE → (False, OLCULEMEDI)",
                okh is False and "ÖLÇÜLEMEDİ" in ayrh and "nesne değil" in ayrh,
                f"ok={okh} ayrinti={ayrh[:200]!r}")
        pi = tmp / "envsiz_proje"
        _yaz(pi / ".mcp.json", json.dumps({"mcpServers": {"sap-adt": {"command": "python"}}}))
        e_i, k_i = yard.alt_surec_ortami(REPO, pi, {"PYTHONPATH": "KULLANICI-YOLU-CAPASI"})
        kontrol("M4i sap-adt var, env YOK → {} = kullanici ortami (sablon DEGIL, OLCULEMEDI DEGIL)",
                e_i is not None and e_i.get("PYTHONPATH") == "KULLANICI-YOLU-CAPASI"
                and k_i == str(pi / ".mcp.json"),
                f"PYTHONPATH={None if e_i is None else e_i.get('PYTHONPATH')!r} kaynak={k_i!r}")

        # ── M5 kenar dalları (sahte core, .mcp.json'da MUTLAK yol) ───────────────
        sc = sahte_core(tmp)
        ps = tmp / "sahte_proje"
        mcp_json_yaz(ps, {"PYTHONIOENCODING": "utf-8", "PYTHONPATH": str(sc)})
        os.environ["SAHTE_DAVRANIS"] = "uyu"
        try:
            okt, ayrt = yard.mcp_import_denetimi(REPO, ps, timeout=2)
            os.environ["SAHTE_DAVRANIS"] = "stdout"
            oks, ayrs = yard.mcp_import_denetimi(REPO, ps, timeout=30)
        finally:
            os.environ.pop("SAHTE_DAVRANIS", None)
        kontrol("M5a zaman asimi → (False, TIMEOUT) — sessiz gecmez",
                okt is False and "TIMEOUT" in ayrt, f"ok={okt} ayrinti={ayrt!r}")
        kontrol("M5b stderr bossa stdout'un SON satiri + exit kodu",
                oks is False and ayrs == "exit 3: STDOUT-SON-SATIR-CAPASI", f"ayrinti={ayrs!r}")

        # ── M6/M7 ix_doctor CLI ────────────────────────────────────────────────
        pd = tmp / "doctor_proje"
        bag_kur(pd / "core", REPO)          # 5b junction PASS olsun; import satırı ayrık ölçülür
        rc6, c6 = _kos(DOCTOR, _doctor_metni(), ["--layer", "5", "--json"],
                       _ortam(v2, v1, pd), tmp, pd)
        s6 = _doctor_import_satiri(c6)
        conn_fail = '".conn_adt YOK' in c6 or ".conn_adt YOK" in c6
        kontrol("M6 ix_doctor --layer 5 (kurulu v2, kullanici v1, .conn_adt YOK): import satiri FAIL + son satir",
                bool(s6) and s6.get("tag") == "FAIL" and V2_CAPA in s6.get("mesaj", "")
                and TRACEBACK_BASLIK not in s6.get("mesaj", "") and conn_fail
                and "pip install -r" in s6.get("mesaj", "") and "YOLDA YOK" not in s6.get("mesaj", ""),
                f"rc={rc6} satir={s6!r} conn_fail={conn_fail} cikti_sonu={c6[-300:]!r}")
        (pd / ".conn_adt").write_text(
            "ADT_SAP_URL=https://ornek.invalid:44300\nADT_SAP_USER=ornek\n"
            "ADT_SAP_PASSWORD=ornek\nADT_SAP_CLIENT=100\n", encoding="utf-8")
        rc7, c7 = _kos(DOCTOR, _doctor_metni(), ["--layer", "5", "--json"],
                       _ortam(v1, v2, pd), tmp, pd)
        s7 = _doctor_import_satiri(c7)
        kontrol("M7 ix_doctor --layer 5 (kurulu v1, kullanici v2, .conn_adt dolu; KONTROL GRUBU): import satiri PASS",
                bool(s7) and s7.get("tag") == "PASS", f"rc={rc7} satir={s7!r} cikti_sonu={c7[-300:]!r}")

        # ── M11 ix_doctor: proje `core` bağı YOK ⇒ mcp_servers yolda yok ⇒ çare pip DEĞİL
        pn = tmp / "bagsiz_proje"
        pn.mkdir()
        rc11, c11 = _kos(DOCTOR, _doctor_metni(), ["--layer", "5", "--json"],
                         _ortam(v1, v1, pn), tmp, pn)
        s11 = _doctor_import_satiri(c11)
        m11 = (s11 or {}).get("mesaj", "")
        kontrol("M11 ix_doctor (core bagi YOK → No module named 'mcp_servers'): care .mcp.json/core bagi, pip DEGIL",
                bool(s11) and s11.get("tag") == "FAIL" and "No module named 'mcp_servers" in m11
                and "YOLDA YOK" in m11 and "pip install -r" not in m11,
                f"rc={rc11} satir={s11!r}")

        # ── M8/M9/M10/M12 team_setup CLI ───────────────────────────────────────
        def ts(etiket: str, kurulu: Path, kullanici: Path, ek: list[str],
               mcp_env: dict | None = None) -> tuple[int, str]:
            p = tmp / f"ts_{etiket}"
            p.mkdir()
            if mcp_env is not None:
                mcp_json_yaz(p, mcp_env)
            return _kos(TS, _ts_metni(), ["--project", str(p), "--no-install", "--no-plugins",
                                          "--no-seed", *ek], _ortam(kurulu, kullanici), tmp, p)

        rc8, c8 = ts("v2", v2, v1, [])
        fail8 = [s for s in c8.splitlines() if s.startswith("[FAIL] MCP server import smoke")]
        kontrol("M8 team_setup (kurulu v2, kullanici v1): FAIL + son satir, `team_setup TAMAM` YOK, exit != 0",
                len(fail8) == 1 and V2_CAPA in fail8[0] and TRACEBACK_BASLIK not in fail8[0]
                and "team_setup TAMAM" not in c8 and rc8 != 0
                and "team_setup BAŞARISIZ (MCP server import smoke)" in c8
                and "pip install -r" in fail8[0] and "YOLDA YOK" not in fail8[0],
                f"rc={rc8} fail_satirlari={fail8!r} cikti_sonu={c8[-400:]!r}")
        rc9, c9 = ts("v1", v1, v2, [])
        kontrol("M9 team_setup (kurulu v1, kullanici v2; KONTROL GRUBU): OK + `team_setup TAMAM` + exit 0",
                rc9 == 0 and "[ OK ] MCP server import smoke" in c9 and "team_setup TAMAM" in c9,
                f"rc={rc9} cikti_sonu={c9[-400:]!r}")
        rc10, c10 = ts("nosmoke", v2, v1, ["--no-smoke"])
        kontrol("M10 team_setup --no-smoke (v2): sozlesme degismedi (smoke yok, TAMAM, exit 0)",
                rc10 == 0 and "team_setup TAMAM" in c10 and "MCP server import smoke" not in c10,
                f"rc={rc10} cikti_sonu={c10[-400:]!r}")
        rc12, c12 = ts("yolsuz", v1, v1, [], {"PYTHONIOENCODING": "utf-8",
                                               "PYTHONPATH": "${CLAUDE_PROJECT_DIR:-.}/olmayan_core"})
        fail12 = [s for s in c12.splitlines() if s.startswith("[FAIL] MCP server import smoke")]
        kontrol("M12 team_setup (.mcp.json PYTHONPATH olmayan dizin): care .mcp.json/core bagi, pip DEGIL",
                len(fail12) == 1 and "No module named 'mcp_servers" in fail12[0]
                and "YOLDA YOK" in fail12[0] and "pip install -r" not in fail12[0] and rc12 != 0,
                f"rc={rc12} fail_satirlari={fail12!r} cikti_sonu={c12[-300:]!r}")
    finally:
        _sil(tmp)

    ok = sum(1 for _, k, _ in SONUC if k)
    etiket = (" [TABAN " + str(KAYNAK_DIZINI) + "]") if KAYNAK_DIZINI else \
        (" [" + " ".join(sorted(KIP)) + "]" if KIP else "")
    print(f"\nmcp_import_denetimi{etiket}: {ok}/{len(SONUC)} PASS")
    return 0 if ok == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
