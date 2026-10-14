#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""transport_yaklasim_sirasi fixture — `set_object_source` PUT transport yaklaşım SIRASI.

NEDEN VAR (2026-10-12)
  `transport_approaches` ilk sırada "yalnız `X-sap-adt-transport` header" deniyordu. Bu sıranın
  yazılı bir gerekçesi yoktu. Ölçülen (on-prem, tek sınıf, ham LOCK→PUT→UNLOCK): yalnız header
  → 409 (geçerli istekle bile), yalnız `corrNr` → 200. known-errors §12.7c'deki vakada ise
  yaklaşım-1 lock handle'ı YAKTI (sonraki 3 yaklaşım 423). Her iki durumda çalışan biçim
  `corrNr` query'si ⇒ sıra PARAM-ÖNCE oldu; header geride yedek kaldı.

SÖZLEŞME
  · İlk PUT: `corrNr=<K>` query, header YOK.
  · Param'ı reddeden (400 "Parameter corrNr could not be found") bir sistemde header yedeği
    hâlâ denenir (yedek SİLİNMEDİ).
  · Hepsi reddedilirse 4 PUT, sıra [param, ikisi, header, transportsuz] + SAPADTError.
  · Transport yoksa ilk PUT'ta ne header ne `corrNr` (davranış değişmedi).
  · KONTROL GRUBU: pinli taban `6b6c11d` aynı sahte sunucuda ilk PUT'u header-only atar ve
    boşa bir 409 alır — yeni kod almaz (vektör ayırt edicidir).

KULLANIM
  python tests/fixtures/transport_yaklasim_sirasi/run.py
  python tests/fixtures/transport_yaklasim_sirasi/run.py --mutasyon
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
TABAN_SHA = "6b6c11d"   # param-önce öncesi (PINLI)
_GIT_KOK = Path(os.environ.get("TRANSPORT_SIRA_GIT_KOK") or REPO)
_TMP = tempfile.mkdtemp(prefix="transport_sira_")
os.environ["CLAUDE_PROJECT_DIR"] = _TMP
for _p in (REPO / "scripts" / "utils", REPO / "scripts", REPO):
    sys.path.insert(0, str(_p))

S: list = []
_TUT: list = []
K = "TRSK900001"
URL = "/sap/bc/adt/oo/classes/zsd001_cl_ornek"


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


def _modul_metinden(src: str, yol: Path, ad: str):
    mod = types.ModuleType(ad)
    mod.__file__ = str(yol)
    _sessiz(lambda: exec(compile(src, str(yol), "exec"), mod.__dict__))
    return mod


class _Yanit:
    def __init__(self, kod, text=""):
        self.status_code, self.text, self.headers = kod, text, {}


def _istemci(L, karar):
    """`karar(headers, params) -> (kod, metin)` — sahte sunucu kuralı."""
    c = L.SAPADTClient.__new__(L.SAPADTClient)
    c.debug_enabled = False
    c.url = "http://sahte.invalid"
    c.istekler = []
    c._get_headers = lambda *a, **k: {}

    def _rq(method, url, headers=None, data=None, params=None, **kw):
        h = dict(headers or {})
        p = dict(params or {})
        c.istekler.append((method, h.get("X-sap-adt-transport"), p.get("corrNr"),
                           p.get("lockHandle")))
        kod, metin = karar(h, p)
        return _Yanit(kod, metin)
    c._request_with_csrf_retry = _rq
    return c


def yalniz_param_kabul(h, p):
    """ölçülen sistem: header dikkate alınmaz; corrNr varsa 200, yoksa 409."""
    return (200, "") if p.get("corrNr") else (409, "CTS_WBO_API 019 sahte bloke")


def param_reddeden(h, p):
    if "corrNr" in p:
        return 400, "Parameter corrNr could not be found"
    return (200, "") if h.get("X-sap-adt-transport") else (409, "sahte")


def hepsi_red(h, p):
    return 409, "sahte catisma"


def her_sey_kabul(h, p):
    return 200, ""


def _kos(L, karar, transport=K):
    c = _istemci(L, karar)
    r, exc = _sessiz(c.set_object_source, URL, "REPORT x.", "LH-1", transport, "ETAG-1")
    return r, exc, c.istekler


def bolum_t(L):
    r, exc, ist = _kos(L, yalniz_param_kabul)
    ekle("T1 ⭐ ilk PUT corrNr query + header YOK; olculen sistemde TEK PUT, bosa 409 yok",
         r is True and exc is None and len(ist) == 1 and ist[0][2] == K and ist[0][1] is None
         and ist[0][3] == "LH-1",
         f"r={r} exc={exc!r} istekler={ist}")
    r, exc, ist = _kos(L, param_reddeden)
    ekle("T2 param'i reddeden sistemde header YEDEGI hala denenir (3. PUT header-only 200)",
         r is True and [(i[1], i[2]) for i in ist] == [(None, K), (K, K), (K, None)],
         f"r={r} exc={exc!r} istekler={ist}")
    r, exc, ist = _kos(L, hepsi_red)
    ekle("T3 hepsi reddedilirse 4 PUT, SIRA [param, ikisi, header, transportsuz] + SAPADTError",
         r is None and type(exc).__name__ == "SAPADTError"
         and [(i[1], i[2]) for i in ist] == [(None, K), (K, K), (K, None), (None, None)],
         f"exc={type(exc).__name__} istekler={ist}")
    r, exc, ist = _kos(L, her_sey_kabul, transport=None)
    ekle("T4 transport YOKKEN ilk PUT ne header ne corrNr tasir (davranis degismedi)",
         r is True and len(ist) == 1 and ist[0][1] is None and ist[0][2] is None,
         f"r={r} istekler={ist}")
    # kontrol grubu: pinli taban lib aynı sunucuda boşa 409 alır (vektör ayırt edici mi?)
    g = subprocess.run(["git", "-C", str(_GIT_KOK), "show", f"{TABAN_SHA}:scripts/sap_adt_lib.py"],
                       capture_output=True)
    if g.returncode != 0:
        ekle("T5 KONTROL GRUBU taban okunamadi (OLCULEMEDI)", False,
             g.stderr.decode("utf-8", "replace")[:160])
        return
    LT = _modul_metinden(g.stdout.decode("utf-8"), REPO / "scripts" / "sap_adt_lib.py",
                         "sap_adt_lib_taban")
    r, exc, ist = _kos(LT, yalniz_param_kabul)
    ekle("T5 ⭐ KONTROL GRUBU: taban ayni sunucuda ilk PUT header-only -> bosa 409, 2 PUT",
         r is True and len(ist) == 2 and ist[0][1] == K and ist[0][2] is None,
         f"taban istekler={ist}")


def main() -> int:
    L = _sessiz(__import__, "sap_adt_lib")[0]
    if L is None:
        print("[fixture-hatasi] sap_adt_lib import edilemedi")
        return 2
    bolum_t(L)
    for ad, ok, d in S:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         -> {d}"))
    n = sum(1 for _, ok, _ in S if ok)
    print(f"\n{n}/{len(S)} OK")
    shutil.rmtree(_TMP, ignore_errors=True)
    return 0 if n == len(S) else 1


MUTASYONLAR = [
    ("M1 eski sira geri (header-only once)", "scripts/sap_adt_lib.py",
     "            (False, True, 'corrNr query parameter only'),\n"
     "            (True, True, 'both header and parameter'),\n"
     "            (True, False, 'X-sap-adt-transport header only'),\n",
     "            (True, False, 'X-sap-adt-transport header only'),\n"
     "            (False, True, 'corrNr query parameter only'),\n"
     "            (True, True, 'both header and parameter'),\n"),
    ("M2 header yedegi silinir", "scripts/sap_adt_lib.py",
     "            (True, False, 'X-sap-adt-transport header only'),\n", ""),
    ("M3 ilk yaklasim header'i da ekler", "scripts/sap_adt_lib.py",
     "            (False, True, 'corrNr query parameter only'),\n",
     "            (True, True, 'corrNr query parameter only'),\n"),
]


def _mutasyon() -> int:
    kok = Path(tempfile.mkdtemp(prefix="transport_sira_kum_"))
    kotu = []
    try:
        shutil.copytree(REPO / "scripts", kok / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        hedef = kok / "tests" / "fixtures" / BURASI.name
        hedef.mkdir(parents=True)
        shutil.copy2(Path(__file__), hedef / "run.py")
        env = dict(os.environ)
        env["TRANSPORT_SIRA_GIT_KOK"] = str(REPO)
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
