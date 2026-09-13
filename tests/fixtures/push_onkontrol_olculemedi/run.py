#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""push_onkontrol_olculemedi — Q312: push sözdizimi ön-kontrolü ÖLÇÜLEMEDİĞİNDE görünür iz.

NEDEN VAR (kod okuması 2026-09-13, Q307 sonrası):
  `SAPClient.push_object` aktivasyondan önce class/interface için sözdizimi kontrolü koşar ve
  YALNIZ `valid is False and errors` durumunda aktivasyonu durdurur. Kontrolün KOŞMADIĞI üç
  giriş push'u SÜRDÜRÜR ve sonuç sözlüğünde hiçbir alan bırakmaz:
    ① `valid is None` (Q307: SAP kontrolü koşmadı — boş/kısa gövde, yalnız generation …)
    ② `SAPClient.syntax_check` istisna yakalayıcısı → `{'valid': False, 'error': …}`, errors YOK
    ③ `self.syntax_check` istisna fırlatır → `_pre = None`
  Davranış (devam) DOĞRUDUR — ENGELLEMEK sahte-HATA üretir (PATTERN #20: None vakalarının bir
  kısmı çağrının kendisinin aktive ettiği temiz sürümdür; canlı sıklık ölçülmedi). Eksik olan
  GÖRÜNÜRLÜKTÜR: `syntax_precheck: 'olculemedi'` + `sozdizimi_sebep` + `[UNVERIFIED]` satırı;
  MCP `adt_push_source` üst seviyeye taşır, CLI `push_object.py` hükmün yanına basar.

⛔ SİLİNMEZ ÇAPALAR:
  · K5 · K6 · K10 · K14 — KONTROL: gerçek sözdizimi hatası ve 403 kilit aktivasyonu DURDURMAYA
    devam eder (`failed`, `ok/success` false). "Her şeye olculemedi" diyen fix geçemesin.
  · K7 · K11 · K13 — KONTROL: SAP kontrolü koştu ve temiz → işaret YOK ("her push'a uyarı"
    diyen fix geçemesin; uyarı yorgunluğu da bir körlüktür).
  · K1 · K9 — `activate_object` ÇAĞRILDI + `ok/success` true: None'da ENGELLEME yok
    (M2 aşırı-sıkı mutasyonunun tek ayırt edicisi).
  · K8 — kapsam dışı tip (prog) işaretlenmez: ön-kontrol bilinçli dışlanmış (BE-46), ölçülemedi DEĞİL.

KULLANIM (repo kökünden):
  python tests/fixtures/push_onkontrol_olculemedi/run.py               # vektörler
  python tests/fixtures/push_onkontrol_olculemedi/run.py --mutasyon    # kopya ağaçta mutasyonlar
  python tests/fixtures/push_onkontrol_olculemedi/run.py --taban <ref> # eski-kod karşıtlığı (git show)
SAP GEREKTİRMEZ: HTTP oturumu ve lock/upload/aktivasyon uçları sahtedir; GERÇEK
`SAPClient.push_object` · `SAPClient.syntax_check` · `SAPADTClient.syntax_check_via_activation` ·
MCP `atom.adt_push_source` · CLI `push_object.main` gövdeleri koşar.
"""
from __future__ import annotations

import io
import os
import re
import shutil
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

BURASI = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[3]
if not (REPO / "scripts" / "sap_client.py").is_file():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")

# ÜRETİM DOSYALARI — `--taban` bunları eski sürümle değiştirir.
URETIM = ["scripts/sap_client.py", "mcp_servers/sap_adt/tools/atom.py", "scripts/push_object.py"]

# AYIRT EDİCİ ÇAPALAR (inkâr cümlesi tuzağı: "olculemedi" metni "BLOCK"/"errors" İÇERMEZ,
# çapa bu yüzden işaretin KENDİ dizgesidir, genel bir kelime değil).
CAPA_SC = "on-kontrolu OLCULEMEDI"            # sap_client push satırı
CAPA_CLI = "PUSH SOZDIZIMI ON-KONTROLU OLCULEMEDI"  # push_object.py hüküm satırı
CAPA_BLOCK = "[BLOCK] Aktivasyon-oncesi syntax-check BASARISIZ"

GOVDE_TRUE = ('<?xml version="1.0" encoding="utf-8"?><chkl:messages xmlns:chkl="http://www.sap.com/'
              'abapxml/checklist"><chkl:properties checkExecuted="true" activationExecuted="true" '
              'generationExecuted="false"/></chkl:messages>')
GOVDE_GEN = ('<?xml version="1.0" encoding="utf-8"?><chkl:messages xmlns:chkl="http://www.sap.com/'
             'abapxml/checklist"><chkl:properties checkExecuted="false" activationExecuted="false" '
             'generationExecuted="true"/></chkl:messages>')
GOVDE_E = ('<?xml version="1.0" encoding="utf-8"?><chkl:messages xmlns:chkl="http://www.sap.com/'
           'abapxml/checklist"><chkl:properties checkExecuted="true" activationExecuted="false" '
           'generationExecuted="false"/><msg type="E" line="3"><shortText><txt>Ornek sozdizimi '
           'hatasi</txt></shortText></msg></chkl:messages>')
KILIT_403 = ('<?xml version="1.0"?><exc:exception xmlns:exc="http://www.sap.com/abapxml/types/'
             'communicationframework"><properties><entry key="T100KEY-V1">SAP_USER_B</entry>'
             '</properties></exc:exception>')
AD = "ZCL_SD001_ORNEK_PUSH"
KAYNAK = "CLASS zcl_sd001_ornek_push DEFINITION.\nENDCLASS.\nCLASS zcl_sd001_ornek_push IMPLEMENTATION.\nENDCLASS.\n"


class _Y:
    def __init__(self, kod, metin="", url=""):
        self.status_code, self.text, self.url = kod, metin, url
        self.headers = {}


# ─────────────────────────────────────────────────────────────────────────────
# ORTAM (import-anı yan etkileri geçici köke)
# ─────────────────────────────────────────────────────────────────────────────
_TMP = tempfile.mkdtemp(prefix="push_onkontrol_")
os.environ["CLAUDE_PROJECT_DIR"] = _TMP
Path(_TMP, "project.yaml").write_text(
    "sap_profile: s4_private\nrelease: '2025'\nsource_root: SOURCE_CODES\n", encoding="utf-8")
os.chdir(_TMP)
for _p in (REPO / "scripts" / "utils", REPO / "scripts", REPO):
    sys.path.insert(0, str(_p))

try:  # pragma: no cover - ortam kosullu
    import mcp.server.fastmcp  # type: ignore  # noqa: F401
except Exception:
    _mcp = types.ModuleType("mcp")
    _srv = types.ModuleType("mcp.server")
    _fast = types.ModuleType("mcp.server.fastmcp")

    class _FastMCP:
        def __init__(self, *a, **k):
            pass

        def tool(self, *a, **k):
            return lambda fn: fn

    _fast.FastMCP = _FastMCP                       # type: ignore[attr-defined]
    _srv.fastmcp = _fast                           # type: ignore[attr-defined]
    _mcp.server = _srv                             # type: ignore[attr-defined]
    sys.modules.setdefault("mcp", _mcp)
    sys.modules.setdefault("mcp.server", _srv)
    sys.modules.setdefault("mcp.server.fastmcp", _fast)

_TUTUCULAR: list = []   # import-anında stdout'u sarmalayan modüllerin sarmalayıcısı GC'de buffer kapatmasın


def _sessiz_import(ad):
    eski = (sys.stdout, sys.stderr)
    atik = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
    sys.stdout = sys.stderr = atik
    try:
        import importlib
        return importlib.import_module(ad)
    finally:
        _TUTUCULAR.append((sys.stdout, sys.stderr, atik))
        sys.stdout, sys.stderr = eski


def _yakala(fn, *a, **k):
    eski = (sys.stdout, sys.stderr)
    tampon = io.StringIO()
    sys.stdout = sys.stderr = tampon
    try:
        return fn(*a, **k), tampon.getvalue()
    finally:
        sys.stdout, sys.stderr = eski


S: list = []


def ekle(ad, kosul, detay=""):
    S.append((ad, bool(kosul), str(detay)[:240]))


def bolum(ad):
    def dek(fn):
        def sar(*a, **k):
            try:
                fn(*a, **k)
            except Exception as exc:                   # çökme != FAIL: ölçülür
                ekle(f"[BOLUM COKTU] {ad}", False, f"{type(exc).__name__}: {exc}")
        return sar
    return dek


# ─────────────────────────────────────────────────────────────────────────────
# Sahte ADT: GERÇEK `syntax_check_via_activation` (HTTP sahte) + sahte lock/upload/aktivasyon
# ─────────────────────────────────────────────────────────────────────────────
class _SozSunucu:
    """Sözdizimi kontrolü POST'u (`preauditRequested=true`): sabit (kod, gövde) döner."""

    def __init__(self, kod, govde):
        self.kod, self.govde, self.postlar = kod, govde, []

    def request(self, method, url, headers=None, timeout=None, **kw):
        if method.lower() == "post" and url.endswith("/sap/bc/adt/activation"):
            self.postlar.append(dict(kw.get("params") or {}))
            return _Y(self.kod, self.govde, url)
        return _Y(599, "beklenmeyen istek", url)


def _sahte_adt(L, sunucu, aktif_kaynak):
    class _SahteAdt(L.SAPADTClient):
        def __init__(self):                       # noqa: D401 — gerçek __init__ bağlantı arar
            self.url = "https://sap.example.test:44300"
            self.session = sunucu
            self.csrf_token = "SAHTE-CSRF"
            self.client = "000"
            self.language = "TR"
            self.user = "SAP_USER_A"
            self._auth_provider = None
            self.debug_enabled = False
            self.timeout_default = 5
            self.timeout_short = 5
            self._last_lock_effective_transport = "SAHK900001"
            self._last_lock_is_link_up = ""
            self.aktivasyon = 0

        def _get_auth_header(self):
            return "Basic SAHTE"

        def fetch_csrf_token(self, force_refresh=False):
            return self.csrf_token

        def _update_cookies(self, response):
            return None

        # --- push_object'in çağırdığı yazma uçları (sahte; SAP'ye hiçbir şey gitmez) ---
        def get_transport_info(self, url):
            return "SAHK900001"

        def is_object_locked(self, url):
            return {"locked": False}

        def register_object_in_transport(self, name, transport, object_type):
            return {"registered": True, "method": "sahte"}

        def fetch_source_etag(self, url):
            return "etag-sahte"

        def lock_object(self, url, transport=None, **kw):
            return "LOCK1"

        def set_object_source(self, url, src, lock, transport, etag=None):
            return True

        def unlock_object(self, url, lock):
            return True

        def activate_object(self, name, url):
            self.aktivasyon += 1
            return {"success": True}

        def get_object_source(self, url, return_etag=False, version=None):
            return aktif_kaynak
    return _SahteAdt()


def _istemci(L, SC, kod, govde, aktif_kaynak=KAYNAK, sc_istisna=False):
    sv = _SozSunucu(kod, govde)
    ist = object.__new__(SC.SAPClient)
    ist.adt_client = _sahte_adt(L, sv, aktif_kaynak)
    ist.debug_enabled = False
    ist.local_base = Path(_TMP)
    ist._find_existing_transport = lambda name, otype, transport: transport
    if sc_istisna:
        def _patlar(*a, **k):
            raise RuntimeError("sahte cagri istisnasi (ornek)")
        ist.syntax_check = _patlar
    return ist, sv


def _kaynak_dosyasi():
    p = Path(_TMP) / f"{AD}.clas.abap"
    p.write_text(KAYNAK, encoding="utf-8")
    return str(p)


# ─────────────────────────────────────────────────────────────────────────────
@bolum("K SAPClient.push_object on-kontrol")
def bolum_k(L, SC):
    dosya = _kaynak_dosyasi()

    def push(kod, govde, tip="class", **kw):
        ist, sv = _istemci(L, SC, kod, govde, **kw)
        r, log = _yakala(ist.push_object, AD, object_type=tip, transport="SAHK900001", source_file=dosya)
        return r, log, ist.adt_client, sv

    def olculemedi_mi(r, log, adt, sebep_on):
        return (r.get("syntax_precheck") == "olculemedi"
                and str(r.get("sozdizimi_sebep") or "").startswith(sebep_on)
                and adt.aktivasyon == 1 and r.get("activated") is True and r.get("success") is True
                and CAPA_SC in log and CAPA_BLOCK not in log)

    def ozet(r, log, adt):
        return (f"precheck={r.get('syntax_precheck')} sebep={r.get('sozdizimi_sebep')!r} "
                f"aktivasyon={adt.aktivasyon} success={r.get('success')} capa={'VAR' if CAPA_SC in log else 'YOK'} "
                f"sc_q307_satiri={'VAR' if 'Syntax NOT measured' in log else 'YOK'}")

    r, log, adt, sv = push(200, GOVDE_GEN)
    ekle("K1 ⭐① valid None (yalniz-generation) -> push DEVAM + syntax_precheck olculemedi + sebep + [UNVERIFIED]",
         olculemedi_mi(r, log, adt, "kontrol_kosmadi") and len(sv.postlar) == 1, ozet(r, log, adt))
    r, log, adt, sv = push(200, "")
    ekle("K2 ⭐① valid None (bos govde) -> olculemedi + sebep govde_bos_veya_kisa",
         olculemedi_mi(r, log, adt, "govde_bos_veya_kisa"), ozet(r, log, adt))
    r, log, adt, sv = push(400, "<html>Bad Request</html>")
    ekle("K3 ⭐② syntax_check istisnasi yutuldu (valid False, errors YOK) -> DURDURMAZ + olculemedi",
         olculemedi_mi(r, log, adt, "kontrol_istisnasi:"), ozet(r, log, adt))
    r, log, adt, sv = push(200, GOVDE_TRUE, sc_istisna=True)
    ekle("K4 ⭐③ syntax_check cagrisi istisna firlatti -> DURDURMAZ + olculemedi",
         olculemedi_mi(r, log, adt, "cagri_istisnasi:"), ozet(r, log, adt))
    r, log, adt, sv = push(200, GOVDE_E)
    ekle("K5 KONTROL E mesaji -> AKTIVE EDILMEDI + failed + olculemedi YOK (degismedi)",
         adt.aktivasyon == 0 and r.get("activated") is False and r.get("success") is False
         and r.get("syntax_precheck") == "failed" and bool(r.get("syntax_errors")) and CAPA_BLOCK in log
         and "sozdizimi_sebep" not in r and CAPA_SC not in log, ozet(r, log, adt))
    r, log, adt, sv = push(403, KILIT_403)
    ekle("K6 KONTROL 403 kilit -> AKTIVE EDILMEDI + failed (degismedi)",
         adt.aktivasyon == 0 and r.get("syntax_precheck") == "failed" and r.get("success") is False,
         ozet(r, log, adt))
    r, log, adt, sv = push(200, GOVDE_TRUE)
    ekle("K7 KONTROL SAP kontrolu kostu + temiz -> aktivasyon + isaret YOK",
         adt.aktivasyon == 1 and r.get("success") is True and "syntax_precheck" not in r
         and "sozdizimi_sebep" not in r and CAPA_SC not in log, ozet(r, log, adt))
    r, log, adt, sv = push(200, GOVDE_GEN, tip="prog")
    ekle("K8 KONTROL kapsam disi tip (prog, BE-46) -> on-kontrol POST'u YOK + isaret YOK",
         len(sv.postlar) == 0 and adt.aktivasyon == 1 and "syntax_precheck" not in r and CAPA_SC not in log,
         f"post={len(sv.postlar)} " + ozet(r, log, adt))


@bolum("L MCP adt_push_source (3. baglam)")
def bolum_l(L, SC, ATOM):
    eski = (ATOM._get_client, ATOM.get_active_tier)
    try:
        ATOM.get_active_tier = lambda: "DEV"

        def mcp(kod, govde):
            ist, _ = _istemci(L, SC, kod, govde)
            ATOM._get_client = lambda _i=ist: _i
            r = ATOM.adt_push_source(name=AD, object_type="class", source=KAYNAK,
                                     transport="SAHK900001", skip_reviewer=True)
            return r, ist.adt_client

        r, adt = mcp(200, GOVDE_GEN)
        ekle("K9 ⭐MCP valid None -> ok TRUE (degismedi) + UST SEVIYE syntax_precheck olculemedi + notice",
             r.get("ok") is True and adt.aktivasyon == 1 and r.get("syntax_precheck") == "olculemedi"
             and CAPA_SC.upper() in str(r.get("syntax_precheck_notice") or "").upper()
             and (r.get("result") or {}).get("syntax_precheck") == "olculemedi",
             f"ok={r.get('ok')} precheck={r.get('syntax_precheck')} notice={'VAR' if r.get('syntax_precheck_notice') else 'YOK'}")
        r, adt = mcp(200, GOVDE_E)
        ekle("K10 KONTROL MCP E -> ok FALSE + failed + notice YOK (degismedi)",
             r.get("ok") is False and r.get("syntax_precheck") == "failed" and bool(r.get("syntax_errors"))
             and "syntax_precheck_notice" not in r and adt.aktivasyon == 0,
             f"ok={r.get('ok')} precheck={r.get('syntax_precheck')}")
        r, adt = mcp(200, GOVDE_TRUE)
        ekle("K11 KONTROL MCP temiz -> ok TRUE + syntax_precheck YOK + notice YOK",
             r.get("ok") is True and "syntax_precheck" not in r and "syntax_precheck_notice" not in r,
             f"ok={r.get('ok')} precheck={r.get('syntax_precheck', 'YOK')}")
    finally:
        ATOM._get_client, ATOM.get_active_tier = eski


@bolum("M CLI push_object.py (4. baglam)")
def bolum_m(L, SC, PO):
    dosya = _kaynak_dosyasi()
    eski_argv, eski_sc = sys.argv, PO.SAPClient
    try:
        def cli(kod, govde, aktif_kaynak=KAYNAK):
            ist, _ = _istemci(L, SC, kod, govde, aktif_kaynak=aktif_kaynak)
            PO.SAPClient = lambda _i=ist: _i
            sys.argv = ["push_object.py", "--name", AD, "--type", "class", "--transport", "SAHK900001",
                        "--source-file", dosya]
            return _yakala(PO.main)

        rc, log = cli(200, GOVDE_GEN)
        i_ok, i_capa = log.find("[OK] Push completed"), log.find(CAPA_CLI)
        ekle("K12 ⭐CLI valid None -> rc 0 + hukum satirinin ARDINDA [UNVERIFIED] satiri",
             rc == 0 and i_ok >= 0 and i_capa > i_ok, f"rc={rc} ok_idx={i_ok} capa_idx={i_capa}")
        rc, log = cli(200, GOVDE_TRUE)
        ekle("K13 KONTROL CLI temiz -> rc 0 + CLI satiri YOK",
             rc == 0 and "[OK] Push completed" in log and CAPA_CLI not in log, f"rc={rc}")
        rc, log = cli(200, GOVDE_E)
        ekle("K14 KONTROL CLI E -> rc 1 + PUSH FAILED + CLI satiri YOK (failed != olculemedi)",
             rc == 1 and "[FAIL] PUSH FAILED" in log and CAPA_CLI not in log, f"rc={rc}")
        rc, log = cli(200, GOVDE_GEN, aktif_kaynak="CLASS baska_icerik DEFINITION.\nENDCLASS.\n")
        i_fail, i_capa = log.find("[FAIL] PUSH FAILED"), log.find(CAPA_CLI)
        ekle("K15 ⭐CLI valid None + readback uyusmazligi -> rc 1 + HATA dalinda da [UNVERIFIED] satiri",
             rc == 1 and i_fail >= 0 and i_capa > i_fail, f"rc={rc} fail_idx={i_fail} capa_idx={i_capa}")
    finally:
        sys.argv, PO.SAPClient = eski_argv, eski_sc


def main() -> int:
    try:
        L = _sessiz_import("sap_adt_lib")
        SC = _sessiz_import("sap_client")
    except Exception as exc:
        ekle("[BOLUM COKTU] lib/sap_client import", False, f"{type(exc).__name__}: {exc}")
        L = SC = None
    if SC is not None:
        bolum_k(L, SC)
        try:
            ATOM = _sessiz_import("mcp_servers.sap_adt.tools.atom")
            bolum_l(L, SC, ATOM)
        except Exception as exc:
            ekle("[BOLUM COKTU] atom import", False, f"{type(exc).__name__}: {exc}")
        try:
            PO = _sessiz_import("push_object")
            bolum_m(L, SC, PO)
        except Exception as exc:
            ekle("[BOLUM COKTU] push_object import", False, f"{type(exc).__name__}: {exc}")
    gecen = sum(1 for _, ok, _ in S if ok)
    for ad, ok, detay in S:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad} -> {detay}")
    print(f"\n{gecen}/{len(S)} OK")
    return 0 if gecen == len(S) else 1


# ─────────────────────────────────────────────────────────────────────────────
# MUTASYON + TABAN (kopya ağaçta; gerçek dosyalara/git'e DOKUNMAZ)
# Çapa parçası TAM 1 kez geçmezse KURULAMADI (KAÇTI değil).
# ─────────────────────────────────────────────────────────────────────────────
MUTASYONLAR = [
    ("M1 isaret sokuldu (sonuc sozlugu alani yok)", "scripts/sap_client.py",
     "result['syntax_precheck'] = 'olculemedi'", "pass"),
    ("M2 asiri-siki: olculemedi'de ENGELLE (durdurma kosulu valid True degilse)", "scripts/sap_client.py",
     "if isinstance(_pre, dict) and _pre.get('valid') is False and _pre.get('errors'):",
     "if not (isinstance(_pre, dict) and _pre.get('valid') is True):"),
    ("M3 asiri-genis: temiz kontrolde de isaret", "scripts/sap_client.py",
     "if not (isinstance(_pre, dict) and _pre.get('valid') is True):\n", "if True:\n"),
    ("M4 sebep aktarimi sokuldu", "scripts/sap_client.py",
     "result['sozdizimi_sebep'] = _pre_sebep", "result['sozdizimi_sebep'] = ''"),
    ("M5 daraltma: yalniz valid None isaretlenir (②/③ sessiz kalir)", "scripts/sap_client.py",
     "if not (isinstance(_pre, dict) and _pre.get('valid') is True):\n",
     "if isinstance(_pre, dict) and _pre.get('valid') is None:\n"),
    ("M6 sap_client [UNVERIFIED] satiri sokuldu", "scripts/sap_client.py",
     "print(f\"      [UNVERIFIED] Aktivasyon-oncesi sozdizimi on-kontrolu OLCULEMEDI",
     "(f\"      [UNVERIFIED] Aktivasyon-oncesi sozdizimi on-kontrolu OLCULEMEDI"),
    ("M7 MCP ust seviye tasima sokuldu", "mcp_servers/sap_adt/tools/atom.py",
     'resp["syntax_precheck"] = "olculemedi"', 'pass'),
    ("M8 CLI satiri sokuldu", "scripts/push_object.py",
     "if isinstance(result, dict) and result.get('syntax_precheck') == 'olculemedi':",
     "if False:"),
    ("M9 CLI satiri yalniz basari dalinda (hata dali sessiz)", "scripts/push_object.py",
        "        for satir in kaynak_izi:\n            print(satir)\n        for satir in onkontrol_izi:\n"
        "            print(satir)\n        print(\"\")",
        "        for satir in kaynak_izi:\n            print(satir)\n        print(\"\")"),
]


def _kopya_agac() -> Path:
    kok = Path(tempfile.mkdtemp(prefix="push_onkontrol_kum_"))
    for d in ("scripts", "mcp_servers"):
        shutil.copytree(REPO / d, kok / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    hedef = kok / "tests" / "fixtures" / BURASI.name
    hedef.mkdir(parents=True)
    shutil.copy2(Path(__file__), hedef / "run.py")
    return kok


def _kos(kok: Path):
    r = subprocess.run([sys.executable, str(kok / "tests" / "fixtures" / BURASI.name / "run.py")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=600, cwd=str(kok))
    m = re.search(r"^(\d+)/(\d+) OK$", r.stdout, re.M)
    return r.returncode, (m.group(0) if m else None), r.stdout


def _sil(kok: Path):
    def _yazilabilir(fn, yol, _exc):
        try:
            os.chmod(yol, 0o700)
            fn(yol)
        except OSError:
            pass
    shutil.rmtree(kok, onerror=_yazilabilir)
    if kok.exists():
        print(f"  [UYARI] kum dizini silinemedi: {kok}")


def _mutasyon() -> int:
    kok = _kopya_agac()
    kotu = []
    try:
        for ad, yol, eski, yeni in MUTASYONLAR:
            dosya = kok / yol
            asil = dosya.read_bytes().decode("utf-8")
            if asil.count(eski) != 1:
                print(f"  [KURULAMADI] {ad} -> parca {asil.count(eski)} kez bulundu (1 olmali)")
                kotu.append(ad)
                continue
            dosya.write_bytes(asil.replace(eski, yeni, 1).encode("utf-8"))
            try:
                rc, ozet, cikti = _kos(kok)
            finally:
                dosya.write_bytes(asil.encode("utf-8"))
            dusen = [s.strip() for s in cikti.splitlines() if s.strip().startswith("[FAIL]")]
            if ozet is None:
                durum = "⛔ COKTU (olcum yok)"
                kotu.append(ad)
            elif rc:
                durum = "YAKALANDI"
            else:
                durum = "⛔ KACTI"
                kotu.append(ad)
            print(f"--> [{ad}] rc={rc} {ozet} -> {durum}")
            for s in dusen[:4]:
                print(f"      {s[:150]}")
    finally:
        _sil(kok)
    print(f"\nMUTASYON OZETI: {len(MUTASYONLAR) - len(kotu)}/{len(MUTASYONLAR)} yakalandi")
    if kotu:
        print("  YAKALANAMAYAN/KURULAMAYAN: " + ", ".join(kotu))
    return 1 if kotu else 0


def _taban(ref: str) -> int:
    kok = _kopya_agac()
    try:
        for yol in URETIM:
            r = subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:{yol}"], capture_output=True)
            if r.returncode != 0:
                print(f"[fixture-hatasi] git show {ref}:{yol} basarisiz: {r.stderr[:200]!r}")
                return 2
            (kok / yol).write_bytes(r.stdout)
        rc, ozet, cikti = _kos(kok)
        print(f"### TABAN {ref} (uretim dosyalari eski surum) rc={rc} {ozet}")
        print(cikti)
        return 0 if (ozet is not None and rc != 0) else 1
    finally:
        _sil(kok)


if __name__ == "__main__":
    if "--mutasyon" in sys.argv:
        sys.exit(_mutasyon())
    if "--taban" in sys.argv:
        sys.exit(_taban(sys.argv[sys.argv.index("--taban") + 1]))
    sys.exit(main())
