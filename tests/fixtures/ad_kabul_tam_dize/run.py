#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ad_kabul_tam_dize fixture — Q363②: KABUL listesi regex'leri tam-dize (`\\Z`) çapalıdır.

NEDEN VAR (2026-10-12)
  Python'da `$` dizenin sonundaki TEK `\\n`'in ÖNÜNDE de eşleşir: `re.match(r"^[ZY][A-Z0-9_]*$",
  "ZFOO\\n")` bir eşleşme döndürür. Kabul (allow) yönündeki ad doğrulayıcılar bu yüzden
  sonu satır-sonlu bir adı geçerli sayıyordu. Düzeltme: `$` → `\\Z` (yalnız KABUL yönü).

  ⛔ RED (deny/sınıflandırıcı) yönü DEĞİŞTİRİLMEDİ — orada `$`'ın gevşekliği güvenli taraftadır
  (`_SENSITIVE_TABLE.match("KNA1\\n")` hassas der ⇒ engeller; `\\Z` bu adı HASSAS DEĞİL yapardı =
  GEVŞETME). Bu fixture o yönü de ölçer (R bölümü) — biri "tutarlılık" için çevirirse düşer.

KAPSAM (kabul yönü, 7 desen / 3 dosya)
  guardrails `_CUSTOMER_PREFIX` · `_LOCK_PREFIX` · sap_adt_lib `validate_object_name` ·
  `validate_package_name` · `SAPADTClient._validate_object_name` · query `_TABLO_ADI` · `_KOLON_ADI`

KULLANIM
  python tests/fixtures/ad_kabul_tam_dize/run.py
  python tests/fixtures/ad_kabul_tam_dize/run.py --mutasyon
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
REPO = BURASI.parents[2]
if not (REPO / "scripts").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")
TABAN_SHA = "6b6c11d"
_GIT_KOK = Path(os.environ.get("AD_KABUL_GIT_KOK") or REPO)
_TMP = tempfile.mkdtemp(prefix="ad_kabul_")
os.environ["CLAUDE_PROJECT_DIR"] = _TMP
Path(_TMP, "project.yaml").write_text(
    "sap_profile: s4_private\nrelease: '2025'\nsource_root: SOURCE_CODES\n", encoding="utf-8")
for _p in (REPO / "scripts" / "utils", REPO / "scripts", REPO / "scripts" / "hooks", REPO):
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

S: list = []
_TUT: list = []
NL = chr(10)


def ekle(ad, kosul, detay=""):
    S.append((ad, bool(kosul), str(detay)[:260]))


def _sessiz(fn, *a, **k):
    eski = (sys.stdout, sys.stderr)
    atik = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
    sys.stdout = sys.stderr = atik
    try:
        try:
            return fn(*a, **k), None
        except Exception as exc:                      # noqa: BLE001 — istisna ÖLÇÜLÜR
            return None, exc
    finally:
        _TUT.append(atik)
        sys.stdout, sys.stderr = eski


def _imp(ad):
    import importlib
    m, exc = _sessiz(importlib.import_module, ad)
    if m is None:
        raise SystemExit(f"[fixture-hatasi] {ad} import edilemedi: {exc!r}")
    return m


def _reddeder(fn, *a, **k):
    r, exc = _sessiz(fn, *a, **k)
    return exc is not None and type(exc).__name__ in ("SAPValidationError", "GuardrailViolation")


def _kabul_eder(fn, *a, **k):
    r, exc = _sessiz(fn, *a, **k)
    return exc is None


def bolum_g(G):
    ns = G._is_customer_namespace
    ekle("G1 ⭐ guardrails: 'ZFOO\\n' customer namespace DEGIL; 'ZFOO'/'zfoo'/'Y_X' kabul (eski vektor)",
         ns("ZFOO" + NL) is False and ns("ZFOO") is True and ns("zfoo") is True and ns("Y_X") is True,
         [ns("ZFOO" + NL), ns("ZFOO"), ns("zfoo"), ns("Y_X")])
    ekle("G2 ⭐ lock istisnasi: 'EZSD001_LOCK' (enqu) kabul, 'EZSD001_LOCK\\n' red; enqu-disi 'EZ..' red",
         ns("EZSD001_LOCK", "enqu") is True and ns("EZSD001_LOCK" + NL, "enqu") is False
         and ns("EZSD001_LOCK", "class") is False,
         [ns("EZSD001_LOCK", "enqu"), ns("EZSD001_LOCK" + NL, "enqu"), ns("EZSD001_LOCK", "class")])
    ekle("G3 require_customer_namespace: 'ZFOO\\n' -> GuardrailViolation; 'MARA' -> red; 'ZFOO' serbest",
         _reddeder(G.require_customer_namespace, "ZFOO" + NL)
         and _reddeder(G.require_customer_namespace, "MARA")
         and _kabul_eder(G.require_customer_namespace, "ZFOO"), "")


def bolum_l(L):
    ekle("L1 ⭐ validate_object_name: 'ZSD001_X\\n' red; 'ZSD001_X' + sinif 'ZSD001_CL_X' kabul",
         _reddeder(L.validate_object_name, "ZSD001_X" + NL, "program")
         and _kabul_eder(L.validate_object_name, "ZSD001_X", "program")
         and _kabul_eder(L.validate_object_name, "ZSD001_CL_X", "class"), "")
    ekle("L2 ⭐ validate_package_name: 'ZSD001_CLC\\n' red; 'ZSD001_CLC' ve '$TMP' kabul",
         _reddeder(L.validate_package_name, "ZSD001_CLC" + NL)
         and _kabul_eder(L.validate_package_name, "ZSD001_CLC")
         and _kabul_eder(L.validate_package_name, "$TMP"), "")
    c = L.SAPADTClient.__new__(L.SAPADTClient)
    ekle("L3 ⭐ SAPADTClient._validate_object_name: 'ZSD001_X\\n' red; 'ZSD001_X' kabul",
         _reddeder(c._validate_object_name, "ZSD001_X" + NL, "Table")
         and _kabul_eder(c._validate_object_name, "ZSD001_X", "Table"), "")


def bolum_q(Q):
    t, k = Q._TABLO_ADI, Q._KOLON_ADI
    ekle("Q1 ⭐ query _TABLO_ADI: 'T000\\n' red; 'T000' ve '/SCWM/AQUA' kabul",
         t.match("T000" + NL) is None and t.match("T000") and t.match("/SCWM/AQUA"), "")
    ekle("Q2 ⭐ query _KOLON_ADI: 'MANDT\\n' red; 'MANDT' ve 'A~B' kabul",
         k.match("MANDT" + NL) is None and k.match("MANDT") and k.match("A~B"), "")


def bolum_r(DG, PB):
    ekle("R1 RED YONU DEGISMEDI: _SENSITIVE_TABLE 'KNA1\\n' -> HALA hassas (gevseme yok)",
         bool(DG._SENSITIVE_TABLE.match("KNA1" + NL)) and bool(DG._SENSITIVE_TABLE.match("KNA1")), "")
    ekle("R2 RED YONU DEGISMEDI: data_guard table_candidates('KNA1') hassas aday uretir",
         "KNA1" in DG.table_candidates("KNA1"), DG.table_candidates("KNA1"))
    ekle("R3 siniflandirici _SAP_AD_RE degismedi (`$` capali; dosya adindan gelir)",
         PB._SAP_AD_RE.pattern.endswith("$"), PB._SAP_AD_RE.pattern)


def bolum_k():
    g = subprocess.run(["git", "-C", str(_GIT_KOK), "show",
                        f"{TABAN_SHA}:mcp_servers/sap_adt/guardrails.py"], capture_output=True)
    if g.returncode != 0:
        ekle("K1 KONTROL GRUBU taban okunamadi (OLCULEMEDI)", False,
             g.stderr.decode("utf-8", "replace")[:160])
        return
    mod = types.ModuleType("guardrails_taban")
    mod.__file__ = str(REPO / "mcp_servers" / "sap_adt" / "guardrails.py")
    _sessiz(lambda: exec(compile(g.stdout.decode("utf-8"), mod.__file__, "exec"), mod.__dict__))
    ekle("K1 ⭐ KONTROL GRUBU: taban guardrails 'ZFOO\\n'i KABUL ediyordu (vektor ayirt edici)",
         mod._is_customer_namespace("ZFOO" + NL) is True, "")


def main() -> int:
    G = _imp("mcp_servers.sap_adt.guardrails")
    L = _imp("sap_adt_lib")
    Q = _imp("mcp_servers.sap_adt.tools.query")
    DG = _imp("mcp_servers.sap_adt.data_guard")
    PB = _imp("_pbe_msag_textpool")
    for fn, a in ((bolum_g, (G,)), (bolum_l, (L,)), (bolum_q, (Q,)), (bolum_r, (DG, PB)),
                  (bolum_k, ())):
        try:
            fn(*a)
        except Exception as exc:                       # çökme != FAIL: ölçülür
            ekle(f"[BOLUM COKTU] {fn.__name__}", False, f"{type(exc).__name__}: {exc}")
    for ad, ok, d in S:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         -> {d}"))
    n = sum(1 for _, ok, _ in S if ok)
    print(f"\n{n}/{len(S)} OK")
    shutil.rmtree(_TMP, ignore_errors=True)
    return 0 if n == len(S) else 1


Z = chr(92) + "Z"
MUTASYONLAR = [
    ("M1 _CUSTOMER_PREFIX `$`a doner", "mcp_servers/sap_adt/guardrails.py",
     '_CUSTOMER_PREFIX = re.compile(r"^[ZY][A-Z0-9_]*' + Z + '"',
     '_CUSTOMER_PREFIX = re.compile(r"^[ZY][A-Z0-9_]*$"'),
    ("M2 _LOCK_PREFIX `$`a doner", "mcp_servers/sap_adt/guardrails.py",
     '_LOCK_PREFIX = re.compile(r"^E[ZY][A-Z0-9_]*' + Z + '"',
     '_LOCK_PREFIX = re.compile(r"^E[ZY][A-Z0-9_]*$"'),
    ("M3 validate_object_name `$`a doner", "scripts/sap_adt_lib.py",
     "re.match(r'^[A-Z][A-Z0-9_]*" + Z + "', name_upper)",
     "re.match(r'^[A-Z][A-Z0-9_]*$', name_upper)"),
    ("M4 validate_package_name `$`a doner", "scripts/sap_adt_lib.py",
     "re.match(r'^[A-Z$][A-Z0-9_$]*" + Z + "', package_upper)",
     "re.match(r'^[A-Z$][A-Z0-9_$]*$', package_upper)"),
    ("M5 _validate_object_name `$`a doner", "scripts/sap_adt_lib.py",
     "re.match(r'^[A-Z][A-Z0-9_]*" + Z + "', name)",
     "re.match(r'^[A-Z][A-Z0-9_]*$', name)"),
    ("M6 _TABLO_ADI `$`a doner", "mcp_servers/sap_adt/tools/query.py",
     '_TABLO_ADI = re.compile(r"^[A-Za-z_/][A-Za-z0-9_/]*' + Z + '")',
     '_TABLO_ADI = re.compile(r"^[A-Za-z_/][A-Za-z0-9_/]*$")'),
    ("M7 _KOLON_ADI `$`a doner", "mcp_servers/sap_adt/tools/query.py",
     '_KOLON_ADI = re.compile(r"^[A-Za-z_][A-Za-z0-9_~/]*' + Z + '")',
     '_KOLON_ADI = re.compile(r"^[A-Za-z_][A-Za-z0-9_~/]*$")'),
    ("M8 RED yonu 'tutarlilik' icin `\\Z`e cevrilir (gevseme)", "mcp_servers/sap_adt/data_guard.py",
     '    r")$",\n    re.IGNORECASE,\n)\n_SENSITIVE_FIELD',
     '    r")' + Z + '",\n    re.IGNORECASE,\n)\n_SENSITIVE_FIELD'),
]


def _mutasyon() -> int:
    kok = Path(tempfile.mkdtemp(prefix="ad_kabul_kum_"))
    kotu = []
    try:
        for d in ("scripts", "mcp_servers"):
            shutil.copytree(REPO / d, kok / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        hedef = kok / "tests" / "fixtures" / BURASI.name
        hedef.mkdir(parents=True)
        shutil.copy2(Path(__file__), hedef / "run.py")
        env = dict(os.environ)
        env["AD_KABUL_GIT_KOK"] = str(REPO)
        for ad, yol, eski, yeni in MUTASYONLAR:
            dosya = kok / yol
            asil = dosya.read_bytes().decode("utf-8")
            if asil.count(eski) != 1:
                print(f"  [KURULAMADI] {ad} -> parca {asil.count(eski)} kez")
                kotu.append(ad)
                continue
            dosya.write_bytes(asil.replace(eski, yeni, 1).encode("utf-8"))
            try:
                r = subprocess.run([sys.executable, str(hedef / "run.py")], capture_output=True,
                                   text=True, encoding="utf-8", errors="replace", timeout=300,
                                   cwd=str(kok), env=env)
            finally:
                dosya.write_bytes(asil.encode("utf-8"))
            m = re.search(r"^(\d+)/(\d+) OK$", r.stdout, re.M)
            durum = "COKTU" if not m else ("YAKALANDI" if r.returncode else "KACTI")
            if durum != "YAKALANDI":
                kotu.append(ad)
            print(f"--> [{ad}] rc={r.returncode} {m.group(0) if m else '-'} -> {durum}")
            for s in [x.strip() for x in r.stdout.splitlines() if x.strip().startswith("[FAIL]")][:3]:
                print(f"      {s[:150]}")
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    print(f"\nMUTASYON OZETI: {len(MUTASYONLAR) - len(kotu)}/{len(MUTASYONLAR)} yakalandi")
    return 1 if kotu else 0


if __name__ == "__main__":
    if "--mutasyon" in sys.argv:
        sys.exit(_mutasyon())
    sys.exit(main())
