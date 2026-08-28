#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C-08 — `adt_unit_run`: namespace guard YOKTU + riskli test bandi ACIKTI.

=== KOK (iki eksen, tek tool) ===
1) NAMESPACE KAPISI: tool ABAP KODU CALISTIRIR (ABAP Unit). Kardeslerinin UCU de
   (`adt_classrun` · `adt_syntax_check` · `adt_post_shell`) `require_customer_namespace`
   kapisindan geciyordu; `adt_unit_run` GECMIYORDU -> standart (Z/Y olmayan) obje adiyla
   cagrilabiliyordu. Tier guard'i vardi, namespace guard'i YOKTU (asimetri).
2) RISKLI BANT: istek govdesi `testRiskLevels harmless dangerous critical` UCUNU DE
   `true` yolluyordu. `dangerous`/`critical` SAP'nin "bu test KALICI VERI DEGISTIREBILIR"
   sinifidir. Salt-okunur beklentisiyle cagrilan bir tool'un VARSAYILANI bu olamaz.

=== SIKILASTIRMA (gevsetme DEGIL) ===
Bu tur bir KAPI EKLER ve bir varsayilani KAPATIR. Bedeli gorunurluk ile odenir:
`method_count == 0` + riskli bant kapali ise yanit `risk_notice` tasir — "0 test" ile
"0 HARMLESS test" ayirt edilebilsin (sessiz sifir YOK).

  G1 ⭐ AYIRT EDICI  standart obje adi -> guardrail_violation (ADR_0005_A) ve HTTP HIC atilmaz
  G2 pozitif kontrol Z objesi -> ESKISI GIBI kosar; sonuc sozlesmesi (7 alan) korunur
  G3 ⭐SINIF (AST)   ABAP KOSTURAN dort tool'un DORDU de namespace kapisindan geciyor
  R1 ⭐ AYIRT EDICI  varsayilan govde: dangerous="false" critical="false" + risk_levels
  R2 opt-in         allow_risky_tests=True -> bant ACILIR ve YANITTA GORUNUR
  R3 sessiz sifir   0 test + kapali bant -> `risk_notice`; ACIK bantta uyari YOK (FP capasi)
  N1 FP capasi      tier kapisi hala calisiyor (PRD -> ADR_0010_TIER)
  N2 FP capasi      desteklenmeyen tip sozlesmesi degismedi (unsupported_type)
  N3 FP capasi      2026-07-29 parser olcumu korunuyor (SARMALAYICI sayilmaz: 2 metot, 3 degil)
  M1-M5             fix'i sok -> korpus KIRMIZI olmali

⛔ SAP'ye BAGLANMAZ: HTTP katmani sahtelenir. Olculen sey KAPI SIRASI ve ISTEK GOVDESIDIR,
SAP'nin bu govdeye verdigi cevap DEGIL (o 2026-07-29 canli olcumunden gelir).
🔴 DOGRULANAMADI: "riskli bant kapaninca bugunku Z testleri hala kosuyor" iddiasi CANLI
olcum ister (bu tur SAP'ye baglanmaz). Kalinti risk raporda beyan edilir.

Kosum: python tests/fixtures/unit_run_guard_riski/run.py     (exit 0 = PASS)
"""
from __future__ import annotations

import ast
import importlib.util
import os
import sys
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
if not (REPO / "mcp_servers").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")
for p in (REPO, REPO / "scripts", REPO / "scripts" / "utils"):
    sys.path.insert(0, str(p))
os.environ.setdefault("CLAUDE_PROJECT_DIR", str(REPO))

# ── MCP SDK KOPRUSU (test-harness'i; uretim kodu DEGIL) ─────────────────────
try:  # pragma: no cover - ortam kosullu
    import mcp.server.fastmcp  # type: ignore  # noqa: F401
except Exception:
    _mcp, _srv, _fast = (types.ModuleType("mcp"), types.ModuleType("mcp.server"),
                         types.ModuleType("mcp.server.fastmcp"))

    class _FastMCP:
        def __init__(self, *a, **k):
            pass

        def tool(self, *a, **k):
            def _dek(fn):
                return fn
            return _dek

    _fast.FastMCP = _FastMCP                                  # type: ignore[attr-defined]
    _srv.fastmcp = _fast                                      # type: ignore[attr-defined]
    _mcp.server = _srv                                        # type: ignore[attr-defined]
    sys.modules.setdefault("mcp", _mcp)
    sys.modules.setdefault("mcp.server", _srv)
    sys.modules.setdefault("mcp.server.fastmcp", _fast)

# `csrf` uretimde `scripts/create_rap_service.py`den gelir ve CANLI token ister.
# Sahte modul YALNIZ o cagriyi karsilar (kutuphane davranisi TEST EDILMEZ).
_crs = sys.modules.get("create_rap_service")
if _crs is None:
    _crs = types.ModuleType("create_rap_service")
    sys.modules["create_rap_service"] = _crs
_crs.csrf = lambda adt: "SAHTE-TOKEN"                          # type: ignore[attr-defined]

from mcp_servers.sap_adt import _conn                          # noqa: E402
from mcp_servers.sap_adt.tools import query as QUERY_TABAN     # noqa: E402

HEDEF = REPO / "mcp_servers" / "sap_adt" / "tools" / "query.py"

# 2026-07-29 canli olcumunun SEKLI: kok <aunit:runResult> ns'li, ic dugumler ONEKSIZ,
# `testClasses`/`testMethods` SARMALAYICILARI var (substring esleme 3 sayardi).
YANIT_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<aunit:runResult xmlns:aunit="http://www.sap.com/adt/aunit"'
    ' xmlns:adtcore="http://www.sap.com/adt/core">'
    '<program adtcore:name="ZCL_ORNEK_TEST" adtcore:type="CLAS/OC">'
    '<testClasses><testClass adtcore:name="LTCL_ORNEK">'
    '<testMethods>'
    '<testMethod adtcore:name="M_GECER"/>'
    '<testMethod adtcore:name="M_DUSER">'
    '<alerts><alert severity="fatal" kind="failedAssertion">'
    '<title>beklenen 1, gelen 2</title></alert></alerts>'
    '</testMethod>'
    '</testMethods></testClass></testClasses>'
    '</program></aunit:runResult>'
)
BOS_XML = ('<aunit:runResult xmlns:aunit="http://www.sap.com/adt/aunit"'
           ' xmlns:adtcore="http://www.sap.com/adt/core"/>')


class _Yanit:
    def __init__(self, metin: str, kod: int = 200):
        self.status_code, self.text = kod, metin


class _Oturum:
    def __init__(self, kayit: dict, metin: str):
        self._kayit, self._metin = kayit, metin

    def post(self, url, headers=None, data=None, verify=True, timeout=None):
        self._kayit["cagrildi"] = self._kayit.get("cagrildi", 0) + 1
        self._kayit["url"] = url
        self._kayit["govde"] = (data or b"").decode("utf-8")
        return _Yanit(self._metin)


class _SahteIstemci:
    """adt_client.session.post disinda HICBIR sey saglamaz (dar yuzey = az yalan)."""

    def __init__(self, kayit: dict, metin: str = YANIT_XML):
        self.debug_enabled = False

        class _Adt:
            def __init__(_s):
                _s.url, _s.client = "https://sap.ornek", "100"
                _s.session = _Oturum(kayit, metin)
        self.adt_client = _Adt()


SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul), detay))


def _kos(q, ad: str, metin: str = YANIT_XML, tier: str = "DEV", **kw):
    kayit: dict = {}
    eski_client, eski_tier = q._get_client, _conn.get_active_tier
    q._get_client = lambda: _SahteIstemci(kayit, metin)
    _conn.get_active_tier = lambda: tier
    try:
        return q.adt_unit_run(name=ad, **kw), kayit
    finally:
        q._get_client, _conn.get_active_tier = eski_client, eski_tier


# =============================================================================
def g_kapi(q) -> None:
    r, kayit = _kos(q, "CL_STANDART_ORNEK")
    kontrol("G1 ⭐ standart obje adi -> guardrail_violation (ADR_0005_A)",
            r.get("error") == "guardrail_violation" and r.get("code") == "ADR_0005_A",
            f"donen={ {k: r[k] for k in list(r)[:4]} }")
    kontrol("G1b ⭐ kapi ISTEKTEN ONCE: HTTP hic atilmadi (sira onemli)",
            kayit.get("cagrildi", 0) == 0, f"post_cagrisi={kayit.get('cagrildi', 0)}")

    r, kayit = _kos(q, "ZCL_ORNEK_TEST")
    sozlesme = {"ok", "name", "method_count", "failed_count", "passed", "classes",
                "client_log"}
    kontrol("G2 pozitif kontrol: Z objesi ESKISI GIBI kosuyor + sonuc sozlesmesi TAM",
            r.get("ok") is True and sozlesme <= set(r)
            and r.get("name") == "ZCL_ORNEK_TEST" and r.get("failed_count") == 1
            and r.get("passed") is False and kayit.get("cagrildi") == 1,
            f"eksik_alan={sorted(sozlesme - set(r))} r={ {k: r.get(k) for k in ('ok','method_count','failed_count','passed')} }")
    kontrol("N3 FP capasi: 2026-07-29 parser olcumu korunuyor (SARMALAYICI sayilmaz)",
            r.get("method_count") == 2,
            f"method_count={r.get('method_count')} (2 olmali; 3 = sarmalayici sayildi)")

    r, _ = _kos(q, "ZCL_ORNEK_TEST", tier="PRD")
    kontrol("N1 FP capasi: tier kapisi hala calisiyor (PRD -> ADR_0010_TIER)",
            r.get("error") == "guardrail_violation" and r.get("code") == "ADR_0010_TIER",
            f"donen={ {k: r.get(k) for k in ('error', 'code')} }")

    r, kayit = _kos(q, "ZCL_ORNEK_TEST", object_type="ddls")
    kontrol("N2 FP capasi: desteklenmeyen tip sozlesmesi degismedi (unsupported_type)",
            r.get("ok") is False and r.get("error") == "unsupported_type"
            and kayit.get("cagrildi", 0) == 0,
            f"donen={r}")


def r_risk(q) -> None:
    r, kayit = _kos(q, "ZCL_ORNEK_TEST")
    govde = kayit.get("govde", "")
    kontrol("R1 ⭐ varsayilan: riskli bant KAPALI (govde) + `risk_levels` yanitta",
            'dangerous="false"' in govde and 'critical="false"' in govde
            and 'harmless="true"' in govde and r.get("risk_levels") == "harmless",
            f"risk_levels={r.get('risk_levels')!r} govde_parcasi="
            f"{govde[govde.find('<testRiskLevels'):govde.find('<testRiskLevels') + 70]!r}")

    r, kayit = _kos(q, "ZCL_ORNEK_TEST", allow_risky_tests=True)
    govde = kayit.get("govde", "")
    kontrol("R2 opt-in: allow_risky_tests=True -> bant ACIK ve yanitta GORUNUR",
            'dangerous="true"' in govde and 'critical="true"' in govde
            and r.get("risk_levels") == "harmless+dangerous+critical",
            f"risk_levels={r.get('risk_levels')!r} govde_parcasi="
            f"{govde[govde.find('<testRiskLevels'):govde.find('<testRiskLevels') + 70]!r}")

    r, _ = _kos(q, "ZCL_ORNEK_TEST", metin=BOS_XML)
    kontrol("R3 ⭐ sessiz sifir YOK: 0 test + kapali bant -> `risk_notice` var",
            r.get("method_count") == 0 and bool(r.get("risk_notice")),
            f"method_count={r.get('method_count')} notice={str(r.get('risk_notice'))[:80]!r}")

    r, _ = _kos(q, "ZCL_ORNEK_TEST", metin=BOS_XML, allow_risky_tests=True)
    kontrol("R3b FP capasi: bant ACIKKEN 0 test -> uyari YOK (alarm yorgunlugu)",
            r.get("method_count") == 0 and "risk_notice" not in r,
            f"notice={r.get('risk_notice', 'YOK')!r}")


def g3_sinif(modul_yolu: Path) -> None:
    """⭐SINIF: vaka bir tool'du; kural TUM ABAP-KOSTURAN tool ailesini baglar."""
    aile = {"adt_unit_run": modul_yolu,
            "adt_syntax_check": modul_yolu,
            "adt_classrun": REPO / "mcp_servers" / "sap_adt" / "tools" / "atom.py",
            "adt_post_shell": REPO / "mcp_servers" / "sap_adt" / "tools" / "atom.py"}
    eksik = []
    for fn_ad, yol in aile.items():
        agac = ast.parse(yol.read_text(encoding="utf-8"))
        fn = next((f for f in ast.walk(agac)
                   if isinstance(f, ast.FunctionDef) and f.name == fn_ad), None)
        if fn is None:
            eksik.append(f"{fn_ad}: FONKSIYON YOK ({yol.name})")
            continue
        cagrilar = {n.func.id for n in ast.walk(fn)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        for gerekli in ("require_customer_namespace", "require_writable_tier"):
            if gerekli not in cagrilar:
                eksik.append(f"{fn_ad}: {gerekli} YOK")
    kontrol("G3 ⭐SINIF: ABAP KOSTURAN dort tool'un DORDU de iki kapidan geciyor "
            "(namespace + tier)", not eksik, f"eksik={eksik}")


def korpus(modul_yolu: Path, ad: str) -> list[tuple[str, bool, str]]:
    global SONUC
    SONUC = []
    if modul_yolu == HEDEF:
        q = QUERY_TABAN
    else:
        sys.modules.pop(ad, None)
        spec = importlib.util.spec_from_file_location(ad, modul_yolu)
        q = importlib.util.module_from_spec(spec)              # type: ignore[arg-type]
        sys.modules[ad] = q
        spec.loader.exec_module(q)                             # type: ignore[union-attr]
    for bolum in ((lambda: g_kapi(q)), (lambda: r_risk(q)), (lambda: g3_sinif(modul_yolu))):
        try:
            bolum()
        except BaseException as exc:                           # noqa: BLE001
            # ⛔ COKME != FAIL: patlayan bolum ADIYLA FAIL yazilir (kanit uretilemedi).
            kontrol("[BOLUM COKTU]", False, f"{type(exc).__name__}: {str(exc)[:200]}")
    return SONUC


# --- MUTASYONLAR ------------------------------------------------------------
_KAPI = '''    ne = "abap unit run (kod çalıştırır)"
    try:
        require_customer_namespace(name, what=ne, object_type=object_type)
        require_writable_tier(get_active_tier(), what=ne)
    except GuardrailViolation as gv:
        return gv.as_dict()'''

MUTASYONLAR = [
    ("M1 kusurun BIREBIR eski hali: namespace kapisini KALDIR (yalniz tier kalir)",
     lambda s: s.replace(
         "        require_customer_namespace(name, what=ne, object_type=object_type)\n"
         "        require_writable_tier(get_active_tier(), what=ne)\n",
         "        require_writable_tier(get_active_tier(), what=ne)\n")),
    ("M2 ⭐SINIR kapiyi ISTEKTEN SONRAYA al (kapi var ama is bitmis olur)",
     lambda s: s.replace(
         _KAPI + "\n    riskli =",
         "    ne = \"abap unit run (kod çalıştırır)\"\n    riskli =").replace(
         "        if r.status_code != 200:\n",
         "        try:\n"
         "            require_customer_namespace(name, what=ne, object_type=object_type)\n"
         "            require_writable_tier(get_active_tier(), what=ne)\n"
         "        except GuardrailViolation as gv:\n"
         "            return gv.as_dict()\n"
         "        if r.status_code != 200:\n")),
    ("M3 riskli bandi yeniden SABIT `true` yap (varsayilan-acik geri gelir)",
     lambda s: s.replace(
         '                \'<testRiskLevels harmless="true" dangerous="\' + riskli +\n'
         '                \'" critical="\' + riskli + \'"/>\'\n',
         '                \'<testRiskLevels harmless="true" dangerous="true" critical="true"/>\'\n')),
    ("M4 ⭐SINIR `risk_notice`i sessizce dusur (0 test = 'test yok' sanilir)",
     lambda s: s.replace(
         "        if mcount == 0 and not allow_risky_tests:\n",
         "        if False and mcount == 0 and not allow_risky_tests:\n")),
    ("M5 ⭐SINIR varsayilani ACIK yap (allow_risky_tests=True)",
     lambda s: s.replace(
         "                 allow_risky_tests: bool = False) -> dict:",
         "                 allow_risky_tests: bool = True) -> dict:")),
]


def main() -> int:
    print("=" * 78)
    print("unit_run_guard_riski — C-08: namespace kapisi + riskli test bandi")
    print("=" * 78)
    if not HEDEF.is_file():
        print(f"FAIL — hedef yok: {HEDEF}")
        return 1
    ham = HEDEF.read_text(encoding="utf-8")

    sonuc = korpus(HEDEF, "query_taban")
    kirik = [(a, d) for a, ok, d in sonuc if not ok]
    for ad, ok, detay in sonuc:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok or os.environ.get("IX_FIXTURE_VERBOSE"):
            print("         -> %s" % detay)
    print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

    print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
    # ⚠ Mutant GERCEK paket dizininde yasar: modul `mcp_servers.sap_adt...` mutlak
    # import'lari kendi paket koku uzerinden cozer.
    mutant = HEDEF.with_name("_mutant_query.py")
    mut_kirik, yama_kirik, kurulamadi = [], [], []
    for i, (ad, mut) in enumerate(MUTASYONLAR):
        bozuk = mut(ham)
        if bozuk == ham:
            print("  [YAMA TUTMADI] %s" % ad)
            yama_kirik.append(ad)
            continue
        try:
            mutant.write_text(bozuk, encoding="utf-8", newline="\n")
            kacan = [a for a, ok, _ in korpus(mutant, "query_mutant_%d" % i) if not ok]
        except BaseException as e:                             # noqa: BLE001
            # ⛔ KURULAMADI != KACTI: olcum HIC yapilamadi.
            kurulamadi.append("%s -> %s: %s" % (ad, type(e).__name__, e))
            print("  [KURULAMADI] %s -> %s: %s" % (ad, type(e).__name__, e))
            continue
        finally:
            mutant.unlink(missing_ok=True)
        print("  [%s] %s" % ("YAKALANDI" if kacan else "KACTI", ad))
        if kacan:
            print("         kiran senaryo(lar): %s" % ", ".join(kacan[:3]))
        else:
            mut_kirik.append(ad)

    print("\n" + "=" * 78)
    if kirik or mut_kirik or yama_kirik or kurulamadi:
        if kirik:
            print("FAIL — senaryo: %s" % ", ".join(a for a, _ in kirik))
        if mut_kirik:
            print("FAIL — mutasyon KACTI: %s" % ", ".join(mut_kirik))
        if yama_kirik:
            print("FAIL — mutasyon yamasi kaynaga UYMADI: %s" % ", ".join(yama_kirik))
        if kurulamadi:
            print("FAIL — mutasyon KURULAMADI (olcum yapilamadi; korpus zayif DEMEK DEGIL): %s"
                  % "; ".join(kurulamadi))
        return 1
    print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(MUTASYONLAR)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
