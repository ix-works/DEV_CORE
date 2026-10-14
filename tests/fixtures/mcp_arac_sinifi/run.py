#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mcp_arac_sinifi fixture — Q369④: her MCP aracı SINIFLANDIRILMIŞ olmalı (tamlık testi).

NEDEN VAR (2026-10-12)
  Dış kaynak vakası: sınıflandırılmamış (ne yazma-korumalı ne salt-okur ilan edilmiş) araçlar
  başka bir makinede, başka tier'da patladı. Bizim kuralımız:
    · Her `@mcp.tool` / `@profil_tool` aracı ya gövdesinde `require_writable_tier` çağırır
      (YAZMA-KORUMALI) ya da `guardrails.SALT_OKUR_ARACLAR` listesindedir (SALT-OKUR).
    · İkisinde de olmayan araç = SINIFLANDIRILMAMIŞ → FAIL.
    · Listede olup kodda olmayan ad (bayat girdi) → FAIL (liste kendi kendine çürümez).
  Davranış ölçümü (örneklem değil, TÜM yazma araçları): QA tier'da her yazma aracı
  `ADR_0010_TIER` ile reddedilir ve istemciye ULAŞMAZ; DEV kontrolünde tier kapısı geçilir.
  ⛔ `tools/list`'ten tier'a göre gizleme YAPILMAZ (kapsam dışı, bilinçli).

KULLANIM
  python tests/fixtures/mcp_arac_sinifi/run.py
  python tests/fixtures/mcp_arac_sinifi/run.py --mutasyon
"""
from __future__ import annotations

import ast
import inspect
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
_TMP = tempfile.mkdtemp(prefix="mcp_arac_sinifi_")
os.environ["CLAUDE_PROJECT_DIR"] = _TMP
Path(_TMP, "project.yaml").write_text(
    "sap_profile: s4_private\nrelease: '2025'\nsource_root: SOURCE_CODES\n", encoding="utf-8")
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

S: list = []
_TUT: list = []
MCP_KOK = REPO / "mcp_servers" / "sap_adt"


def ekle(ad, kosul, detay=""):
    S.append((ad, bool(kosul), str(detay)[:300]))


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


def arac_envanteri():
    """AST: `mcp_servers/sap_adt/**` içindeki TÜM araçlar → {ad: (dosya, yazma_korumali)}."""
    out = {}
    for f in sorted(MCP_KOK.rglob("*.py")):
        if "__pycache__" in f.parts:
            continue
        agac = ast.parse(f.read_text(encoding="utf-8"))
        for n in agac.body:
            if not isinstance(n, ast.FunctionDef):
                continue
            dek = [ast.unparse(d) for d in n.decorator_list]
            if not any(re.search(r"(^|\.)(tool|profil_tool)\(", d) for d in dek):
                continue
            cagri = {(c.func.id if isinstance(c.func, ast.Name) else getattr(c.func, "attr", ""))
                     for c in ast.walk(n) if isinstance(c, ast.Call)}
            out[n.name] = (str(f.relative_to(REPO)).replace("\\", "/"), "require_writable_tier" in cagri)
    return out


def bolum_t(G):
    env = arac_envanteri()
    salt = set(G.SALT_OKUR_ARACLAR)
    yazma = {a for a, (_, y) in env.items() if y}
    siniflanmamis = sorted(a for a in env if a not in yazma and a not in salt)
    bayat = sorted(salt - set(env))
    ekle("T0 envanter bos DEGIL (tarayici kostu; >= 20 arac)", len(env) >= 20, len(env))
    ekle("T1 ⭐ SINIFLANDIRILMAMIS arac YOK (ya require_writable_tier ya SALT_OKUR_ARACLAR)",
         not siniflanmamis, {a: env[a][0] for a in siniflanmamis})
    ekle("T2 SALT_OKUR_ARACLAR'da kodda OLMAYAN (bayat) ad YOK", not bayat, bayat)
    ekle("T3 yazma aracı listesi beklenen cekirdegi icerir (adt_push_source/adt_delete/adt_activate)",
         {"adt_push_source", "adt_delete", "adt_activate"} <= yazma, sorted(yazma))
    print(f"  [KAPSAM] {len(env)} arac tarandi · yazma-korumali {len(yazma)} · salt-okur listesi "
          f"{len(salt)} · cift-siniflu {sorted(yazma & salt)}")
    return env, yazma


def _sahte_arguman(fn):
    k = {}
    for p in inspect.signature(fn).parameters.values():
        if p.default is not inspect.Parameter.empty:
            continue
        ann = str(p.annotation)
        if "bool" in ann:
            k[p.name] = False
        elif "int" in ann:
            k[p.name] = 1
        elif "list" in ann or "List" in ann:
            k[p.name] = []
        elif "dict" in ann or "Dict" in ann:
            k[p.name] = {}
        else:
            k[p.name] = "ZSD001_ORNEK"
    return k


def bolum_q(env, yazma):
    CONN = _imp("mcp_servers.sap_adt._conn")
    moduller = {}
    for ad in yazma:
        dosya = env[ad][0]
        mod = dosya[:-3].replace("/", ".")
        moduller.setdefault(mod, _imp(mod))
    atom = _imp("mcp_servers.sap_adt.tools.atom")
    query = _imp("mcp_servers.sap_adt.tools.query")
    comp = _imp("mcp_servers.sap_adt.tools.composite")
    ulasti = []

    def _istemci():
        ulasti.append(1)
        raise RuntimeError("SAHTE-ISTEMCI: tier kapisi gecildi")

    # `get_active_tier` modul seviyesinde AD olarak import edilir (atom/composite) ya da
    # fonksiyon icinde `_conn`dan (query) ⇒ her bagin KENDISI yamanir; yalniz `_conn`u yamamak
    # gercek tier okuyucusunu birakir (olculdu: ilk taslak sahte-sizinti uretti).
    tier_sahipleri = [m for m in {CONN, atom, query, comp, *moduller.values()}
                      if hasattr(m, "get_active_tier")]
    eski_tier = {m: m.get_active_tier for m in tier_sahipleri}

    def _tier_ayarla(deger):
        for m in tier_sahipleri:
            m.get_active_tier = lambda d=deger: d

    eski = (atom._get_client, query._get_client, getattr(comp, "_get_client", None))
    atom._get_client = query._get_client = _istemci
    if hasattr(comp, "_get_client"):
        comp._get_client = _istemci
    sizinti, dev_bloklu, olculemedi, dev_ulasan = {}, {}, [], []
    try:
        for ad in sorted(yazma):
            fn = getattr(moduller[env[ad][0][:-3].replace("/", ".")], ad)
            arg = _sahte_arguman(fn)
            _tier_ayarla("QA")
            ulasti.clear()
            r, exc = _sessiz(fn, **arg)
            kod = (r or {}).get("code") if isinstance(r, dict) else None
            # Önce SIZINTI: sahte istemci çağrıldıysa (istisna yayılmış olsa bile) tier kapısı
            # geçilmiştir — bu bir ölçülemedi DEĞİL, ölçülmüş ihlaldir.
            if exc is not None and not isinstance(r, dict) and not ulasti:
                olculemedi.append(f"{ad}:{type(exc).__name__}")
                continue
            if kod != "ADR_0010_TIER" or ulasti:
                sizinti[ad] = {"code": kod, "istemciye_ulasti": bool(ulasti),
                               "error": (r or {}).get("error")}
            _tier_ayarla("DEV")
            ulasti.clear()
            r2, _ = _sessiz(fn, **arg)
            if ulasti:
                dev_ulasan.append(ad)
            if isinstance(r2, dict) and r2.get("code") == "ADR_0010_TIER":
                dev_bloklu[ad] = r2.get("message", "")[:80]
    finally:
        for m, f in eski_tier.items():
            m.get_active_tier = f
        atom._get_client, query._get_client = eski[:2]
        if eski[2] is not None:
            comp._get_client = eski[2]
    ekle("Q0 her yazma araci sahte argumanla CAGRILABILDI (cokme != FAIL)", not olculemedi, olculemedi)
    ekle("Q1 ⭐ QA tier: TUM yazma araclari ADR_0010_TIER ile reddedilir + istemciye ULASILMAZ",
         not sizinti, sizinti)
    ekle("Q2 ⭐ KONTROL GRUBU DEV: hicbir yazma araci tier kapisinda DURMAZ", not dev_bloklu, dev_bloklu)
    ekle("Q3 KONTROL GRUBU DEV: sahte istemciye ULASAN arac var (yama gercekten etkili; >= 5)",
         len(dev_ulasan) >= 5, sorted(dev_ulasan))
    print(f"  [KAPSAM] DEV'de istemciye ulasan {len(dev_ulasan)}/{len(yazma)}: {sorted(dev_ulasan)} "
          "(ulasmayanlar sahte argumanla ad/metin dogrulamasinda durdu — tier DISI ret)")


def main() -> int:
    G = _imp("mcp_servers.sap_adt.guardrails")
    try:
        env, yazma = bolum_t(G)
        bolum_q(env, yazma)
    except Exception as exc:                           # çökme != FAIL: ölçülür
        ekle("[BOLUM COKTU]", False, f"{type(exc).__name__}: {exc}")
    for ad, ok, d in S:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         -> {d}"))
    n = sum(1 for _, ok, _ in S if ok)
    print(f"\n{n}/{len(S)} OK")
    shutil.rmtree(_TMP, ignore_errors=True)
    return 0 if n == len(S) else 1


MUTASYONLAR = [
    ("M1 yazma aracindan tier cagrisi kaldirilir (adt_delete)", "mcp_servers/sap_adt/tools/atom.py",
     None, "adt_delete"),
    ("M2 siniflandirilmamis yeni arac eklenir", "mcp_servers/sap_adt/tools/query.py",
     "\n\n@profil_tool()\ndef adt_get_method(",
     "\n\n@profil_tool()\ndef adt_yeni_siniflanmamis() -> dict:\n    return {}\n\n\n@profil_tool()\ndef adt_get_method("),
    ("M3 salt-okur listesinden bir arac silinir", "mcp_servers/sap_adt/guardrails.py",
     '    "adt_lock_check",           # kilit DURUMU sorgusu (is_object_locked)\n', ""),
    ("M4 listede bayat ad kalir", "mcp_servers/sap_adt/guardrails.py",
     '    "ping",                     # bağlantı yoklaması\n',
     '    "ping",                     # bağlantı yoklaması\n    "adt_kaldirilmis_arac",\n'),
    ("M5 tier cagrisi DURUR ama sabit 'DEV' alir (AST yazim kontrolu gecer; DAVRANIS kirilir)",
     "mcp_servers/sap_adt/tools/atom.py",
     'require_writable_tier(get_active_tier(), what=f"{object_type} delete")',
     'require_writable_tier("DEV", what=f"{object_type} delete")'),
]


def _tier_cagrisini_sok(metin: str, arac: str) -> str | None:
    """`arac` fonksiyonundaki `require_writable_tier(...)` çağrı satırını `pass`e çevir."""
    agac = ast.parse(metin)
    fn = next((n for n in agac.body if isinstance(n, ast.FunctionDef) and n.name == arac), None)
    if fn is None:
        return None
    satirlar = metin.split("\n")
    hedef = [c for c in ast.walk(fn) if isinstance(c, ast.Call)
             and getattr(c.func, "id", getattr(c.func, "attr", "")) == "require_writable_tier"]
    if len(hedef) != 1 or hedef[0].lineno != hedef[0].end_lineno:
        return None
    s = satirlar[hedef[0].lineno - 1]
    girinti = s[:len(s) - len(s.lstrip())]
    satirlar[hedef[0].lineno - 1] = girinti + "pass"
    return "\n".join(satirlar)


def _mutasyon() -> int:
    kok = Path(tempfile.mkdtemp(prefix="mcp_arac_sinifi_kum_"))
    kotu = []
    try:
        for d in ("scripts", "mcp_servers"):
            shutil.copytree(REPO / d, kok / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        hedef = kok / "tests" / "fixtures" / BURASI.name
        hedef.mkdir(parents=True)
        shutil.copy2(Path(__file__), hedef / "run.py")
        for ad, yol, eski, yeni in MUTASYONLAR:
            dosya = kok / yol
            asil = dosya.read_bytes().decode("utf-8")
            if eski is None:
                bozuk = _tier_cagrisini_sok(asil, yeni)
                if bozuk is None:
                    print(f"  [KURULAMADI] {ad} -> tier cagrisi tek-satir/tekil degil")
                    kotu.append(ad)
                    continue
            else:
                if asil.count(eski) != 1:
                    print(f"  [KURULAMADI] {ad} -> parca {asil.count(eski)} kez")
                    kotu.append(ad)
                    continue
                bozuk = asil.replace(eski, yeni, 1)
            dosya.write_bytes(bozuk.encode("utf-8"))
            try:
                r = subprocess.run([sys.executable, str(hedef / "run.py")], capture_output=True,
                                   text=True, encoding="utf-8", errors="replace", timeout=300, cwd=str(kok))
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
