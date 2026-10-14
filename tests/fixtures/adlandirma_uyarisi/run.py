#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""adlandirma_uyarisi fixture — Q369⑤ (2026-10-12): DDIC yaratma anında ad uyarısı (GATE DEĞİL).

NEDEN VAR
  Dış kaynak: yaratma anında adlandırma uyarısı ajanın yanlış adı kalıcı kılmasını önlüyor.
  Bizde adlandırma paket `.rules.md` regex'leriyle DOSYA düzeyinde ölçülür; SAP'de yaratılan
  objenin adı o ana kadar hiçbir yerde görünmez. Kural `standards/01-naming.md` §4.4.5'ten:
  nesne öneki adın baş/son parçası dışında `_<ÖNEK>_` olarak geçer (T/A · S · E · D · TT).
  ⛔ YALNIZ UYARI: `naming_warning` alanı eklenir; `ok` ve akış DEĞİŞMEZ.

BÖLÜMLER
  A  kural vektörleri (uyan → None · uymayan → uyarı · kapsam dışı → None · istisna yok)
  W  kablolama: atom.adt_post_shell (davranış, sahte istemci) + 3 composite aracı (AST)
  ⓘ  `--korpus <dizin>`: tüketici kaynak ağacında FP oranını YENİDEN ölçer (salt-okur; CI'da
     koşmaz — korpus çekirdekte yok). 2026-10-12 ölçümü: 212 adda uyarı 0.

KULLANIM
  python tests/fixtures/adlandirma_uyarisi/run.py
  python tests/fixtures/adlandirma_uyarisi/run.py --mutasyon
  python tests/fixtures/adlandirma_uyarisi/run.py --korpus <SOURCE_ROOT>
"""
from __future__ import annotations

import ast
import csv
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
_TMP = tempfile.mkdtemp(prefix="adlandirma_")
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


def ekle(ad, kosul, detay=""):
    S.append((ad, bool(kosul), str(detay)[:300]))


def _imp(ad):
    import importlib
    eski = (sys.stdout, sys.stderr)
    sys.stdout = sys.stderr = io.StringIO()
    try:
        return importlib.import_module(ad)
    finally:
        sys.stdout, sys.stderr = eski


UYAN = [
    ("ZSD001_T_ORNEK", "table"), ("ZSD001_T_ORNEK", "tabl"), ("ZSD001_A_ORNEK_D", "table"),
    ("ZFI001_CLC_T_BOYUT", "table"), ("ZSD001_S_RAPOR", "structure"), ("ZSD001_E_TUTAR", "dataelement"),
    ("ZSD001_E_TUTAR", "dtel"), ("ZSD001_D_TUTAR", "domain"), ("ZSD001_D_TUTAR", "doma"),
    ("ZSD001_TT_FATURA", "tabletype"), ("ZSD001_TT_FATURA", "ttyp"), ("zsd001_s_kucuk", "structure"),
    ("YSD001_T_ORNEK", "table"),
]
UYMAYAN = [
    ("ZSD001_ORNEK", "table", "_T_"), ("ZSD001_S_RAPOR", "table", "_T_"),
    ("ZSD001_RAPOR", "structure", "_S_"), ("ZSD001_T_RAPOR", "structure", "_S_"),
    ("ZSD001_TUTAR", "dataelement", "_E_"), ("ZSD001_D_TUTAR", "dtel", "_E_"),
    ("ZSD001_E_TUTAR", "domain", "_D_"), ("ZSD001_T_FATURA", "tabletype", "_TT_"),
    ("ZSD001_T", "table", "_T_"),           # önek SON parça: ad gövdesi yok
]
KAPSAM_DISI = [
    ("ZSD001_CL_ORNEK", "class"), ("/NS1/ORNEK", "table"), ("ZZMARA_EK", "structure"),
    ("", "table"), (None, "table"), ("ZSD001_ORNEK", None), ("KNA1", "table"),
]


def bolum_a(G):
    f = G.adlandirma_uyarisi
    kotu = [(a, t, f(a, t)) for a, t in UYAN if f(a, t) is not None]
    ekle("A1 ⭐ standarda UYAN adlar uyari URETMEZ (13 vektor; esanlamli tipler dahil)", not kotu, kotu)
    kotu = []
    for a, t, bek in UYMAYAN:
        u = f(a, t)
        if not (isinstance(u, str) and u.startswith("ADLANDIRMA UYARISI") and bek in u
                and "ENGELLENMED" in u and "ZSD001_" in u):
            kotu.append((a, t, u))
    ekle("A2 ⭐ UYMAYAN adlar uyari uretir + beklenen onek + 'ENGELLENMEDI' + ornek (9 vektor)", not kotu, kotu)
    kotu = [(a, t, f(a, t)) for a, t in KAPSAM_DISI if f(a, t) is not None]
    ekle("A3 kapsam disi (sinif / ad alanli / ZZ append / bos / None / standart ad) -> None",
         not kotu, kotu)
    try:
        r = f(object(), object())        # type: ignore[arg-type]
        ekle("A4 garip girdide istisna ATMAZ (None)", r is None, r)
    except Exception as exc:              # noqa: BLE001
        ekle("A4 garip girdide istisna ATMAZ (None)", False, repr(exc))
    u = f("ZSD001_ORNEK", "table")
    ekle("A5 uyari metni yalniz-uyari ve ENGELLENMEDI ifadesini acikca tasir",
         "yalnız uyarı" in (u or "") and "ENGELLEN" in (u or ""), u)


class _SahteIstemci:
    def __init__(self):
        self.cagri = []

    def create_object(self, **k):
        self.cagri.append(k)
        return "/sap/bc/adt/ddic/tables/" + k["name"].lower()


def bolum_w():
    atom = _imp("mcp_servers.sap_adt.tools.atom")
    eski = (atom._get_client, atom.get_active_tier)
    try:
        atom.get_active_tier = lambda: "DEV"
        for ad, tip, bek_uyari in (("ZSD001_ORNEK", "tabl", True), ("ZSD001_T_ORNEK", "tabl", False),
                                   ("ZSD001_CL_ORNEK", "class", False)):
            c = _SahteIstemci()
            atom._get_client = lambda _c=c: _c
            eski_o = (sys.stdout, sys.stderr)
            sys.stdout = sys.stderr = io.StringIO()
            try:
                r = atom.adt_post_shell(object_type=tip, name=ad, package="ZSD001_CLC",
                                        transport="NPLK900001", description="Örnek nesne")
            finally:
                sys.stdout, sys.stderr = eski_o
            ekle(f"W1 adt_post_shell {tip}:{ad} -> ok True + uyari {'VAR' if bek_uyari else 'YOK'}",
                 r.get("ok") is True and len(c.cagri) == 1 and (("naming_warning" in r) is bek_uyari),
                 {k: r.get(k) for k in ("ok", "error", "naming_warning")})
    finally:
        atom._get_client, atom.get_active_tier = eski
    # composite: davranış zinciri (yarat+it+aktive+doğrula) burada koşturulmaz → AST kablolama
    agac = ast.parse((REPO / "mcp_servers/sap_adt/tools/composite.py").read_text(encoding="utf-8"))
    bek = {"adt_domain_create": "domain", "adt_dtel_create": "dataelement", "adt_struct_create": "structure"}
    bulunan = {}
    for n in agac.body:
        if isinstance(n, ast.FunctionDef) and n.name in bek:
            for c in ast.walk(n):
                if (isinstance(c, ast.Call) and getattr(c.func, "id", "") == "adlandirma_uyarisi"
                        and len(c.args) == 2 and isinstance(c.args[1], ast.Constant)):
                    bulunan[n.name] = c.args[1].value
    ekle("W2 ⭐ 3 composite DDIC araci dogru tiple adlandirma_uyarisi cagirir (AST)", bulunan == bek, bulunan)
    # uyarı `ok`a dokunmaz: composite'te atandığı satır yalnız `naming_warning` anahtarına yazar
    yazilan = set()
    for n in agac.body:
        if isinstance(n, ast.FunctionDef) and n.name in bek:
            for c in ast.walk(n):
                if isinstance(c, ast.Assign) and any(
                        isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and t.value.id == "out"
                        and isinstance(t.slice, ast.Constant) for t in c.targets):
                    if isinstance(c.value, ast.Name) and c.value.id == "ad_uyari":
                        yazilan |= {t.slice.value for t in c.targets}
    ekle("W3 composite'te uyari YALNIZ 'naming_warning' anahtarina yazilir (ok DEGISMEZ)",
         yazilan == {"naming_warning"}, yazilan)


def main() -> int:
    G = _imp("mcp_servers.sap_adt.guardrails")
    for ad, fn in (("A", lambda: bolum_a(G)), ("W", bolum_w)):
        try:
            fn()
        except Exception as exc:                       # çökme != FAIL: ölçülür
            ekle(f"[BOLUM {ad} COKTU]", False, f"{type(exc).__name__}: {exc}")
    for ad, ok, d in S:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         -> {d}"))
    n = sum(1 for _, ok, _ in S if ok)
    print("  [KAPSAM] kural vektorleri + atom adt_post_shell davranisi + composite AST. Composite "
          "araclarin uctan uca zinciri KOSTURULMADI; FP orani yalniz --korpus ile (yerel) olculur.")
    print(f"\n{n}/{len(S)} OK")
    shutil.rmtree(_TMP, ignore_errors=True)
    return 0 if n == len(S) else 1


def _korpus(kok: Path) -> int:
    """Salt-okur FP ölçümü: paket `tables/` · `structures/` dosya adları + DDIC CSV `name` kolonu."""
    G = _imp("mcp_servers.sap_adt.guardrails")
    adlar = {"table": set(), "structure": set(), "dataelement": set(), "domain": set()}
    for p in kok.glob("*/*/tables/*"):
        if p.suffix.lower() in (".ddl", ".tabl", ".abap") and p.name[:1].upper() in "ZY":
            adlar["table"].add(p.name.split(".")[0].upper())
    for p in list(kok.glob("*/*/structures/*.asddls")) + list(kok.glob("*/*/tables/*.asddls")):
        adlar["structure"].add(p.name.split(".")[0].upper())
    for f in kok.rglob("*.csv"):
        if "node_modules" in f.parts:
            continue
        tip = "domain" if "domain" in f.name.lower() else ("dataelement" if "dataelement" in f.name.lower() else None)
        if not tip:
            continue
        with open(f, encoding="utf-8", errors="replace") as h:
            for satir in csv.DictReader(h):
                v = (satir.get("name") or "").strip().upper()
                if v[:1] in ("Z", "Y"):
                    adlar[tip].add(v)
    top = uyari = 0
    for tip, kume in adlar.items():
        u = sorted(a for a in kume if G.adlandirma_uyarisi(a, tip))
        top += len(kume)
        uyari += len(u)
        print(f"  {tip}: {len(u)}/{len(kume)} uyari" + (f" -> {u[:10]}" if u else ""))
    print(f"KORPUS: {uyari}/{top} uyari (FP adayi; her biri elle siniflanmali)")
    return 0


MUTASYONLAR = [
    ("M1 kural hep None (uyari olu)", "mcp_servers/sap_adt/guardrails.py",
     "        if set(parcalar[1:-1]) & set(izinli):\n", "        if True:\n"),
    ("M2 onek SON parcada da kabul (ZSD001_T gecer)", "mcp_servers/sap_adt/guardrails.py",
     "if set(parcalar[1:-1]) & set(izinli):", "if set(parcalar[1:]) & set(izinli):"),
    ("M3 ZZ append muafiyeti kalkar", "mcp_servers/sap_adt/guardrails.py",
     'or ad[:2] in ("ZZ", "YY") ', ""),
    ("M4 uyari atom'da ok'u False yapar (GATE'e donusur)", "mcp_servers/sap_adt/tools/atom.py",
     '                sonuc["naming_warning"] = ad_uyari\n',
     '                sonuc["naming_warning"] = ad_uyari\n                sonuc["ok"] = False\n'),
    ("M5 composite yapi araci yanlis tip", "mcp_servers/sap_adt/tools/composite.py",
     'ad_uyari = adlandirma_uyarisi(name, "structure")', 'ad_uyari = adlandirma_uyarisi(name, "table")'),
    ("M6 atom kablolamasi kaldirilir", "mcp_servers/sap_adt/tools/atom.py",
     "            ad_uyari = adlandirma_uyarisi(name, object_type)\n", "            ad_uyari = None\n"),
]


def _mutasyon() -> int:
    kok = Path(tempfile.mkdtemp(prefix="adlandirma_kum_"))
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
            if asil.count(eski) != 1:
                print(f"  [KURULAMADI] {ad} -> parca {asil.count(eski)} kez")
                kotu.append(ad)
                continue
            dosya.write_bytes(asil.replace(eski, yeni, 1).encode("utf-8"))
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
    if "--korpus" in sys.argv:
        sys.exit(_korpus(Path(sys.argv[sys.argv.index("--korpus") + 1])))
    sys.exit(main())
