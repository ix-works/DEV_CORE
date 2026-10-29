#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sql_sure_birimi fixture — `run_sql_query` süre BİRİMİ (2026-10-29).

NEDEN VAR
  `run_sql_query.py` tablo çıktısı `Execution time: {…:.3f}s` basıyordu; değer SAP'nin
  `dp:queryExecutionTime` alanından gelir ve bu alan MİLİSANİYEDİR. Canlı ölçüm (bir on-prem
  S/4 DEV, salt-okur SELECT, aynı süreçte duvar saatiyle): değer 24.407 iken isteğin duvar
  saati 0.224 s — saniye olsaydı istek 24 s sürerdi ⇒ birim ms. Yanlış etiket "sorgu 150 s
  sürdü" gibi sahte performans bulgusu üretir.
  Düzeltme: tablo satırı `… ms (SAP server-side)`; `SAPClient.run_sql_query` sonucuna ve JSON
  çıktısına birim taşıyan `execution_time_ms` eklendi; ESKİ `execution_time` anahtarı AYNI
  değerle (ms) korunur (geriye uyumluluk — JSON tüketicisi kırılmaz).

  S1 SAPClient.run_sql_query: execution_time_ms == execution_time == SAP değeri (ms)
  S2 GERÇEK giriş noktası (alt süreç, sahte SAP): tablo satırı "24.407 ms", "s" etiketi YOK
  S3 JSON: execution_time_ms VAR + eski execution_time anahtarı AYNI değerle (geriye uyum)
  S4 ÜÇÜNCÜ BAĞLAM: alan YOKSA 0 → "0.000 ms" (çökme yok) · CSV çıktısında meta satırı yok

KULLANIM
  python tests/fixtures/sql_sure_birimi/run.py [--mutasyon-saniye-etiketi | ...]
Kosucu: tests/run_fixture_tests.py (OZEL_TESTLER)
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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

# kip: (dosya, capa, yerine, ilan edilen düşen vektörler)
MUTASYONLAR = {
    "--mutasyon-saniye-etiketi": (
        "run_sql_query.py",
        "print(f\"Execution time: {result['execution_time']:.3f} ms (SAP server-side)\")",
        "print(f\"Execution time: {result['execution_time']:.3f}s\")", {"S2"}),
    "--mutasyon-ms-anahtari-yok": (
        "sap_client.py",
        "                'execution_time_ms': exec_ms,\n", "", {"S1"}),
    "--mutasyon-json-eski-anahtar-yok": (
        "run_sql_query.py",
        "        'execution_time': result['execution_time'],\n", "", {"S3"}),
}
GECERLI_KIP = set(MUTASYONLAR)
KIP = None
for _a in sys.argv[1:]:
    if _a in GECERLI_KIP:
        KIP = _a
    else:
        print(f"[KULLANIM] bilinmeyen kip: {_a} (gecerli: {sorted(GECERLI_KIP)})")
        raise SystemExit(2)


def _sil(d: Path) -> None:
    """Q319: Windows'ta salt-okur girdi `rmtree(ignore_errors=True)` ile SESSİZCE kalır."""
    def _ac(func, path, _exc):                       # noqa: ANN001
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass

    kw = {"onexc": _ac} if sys.version_info >= (3, 12) else {"onerror": _ac}
    try:
        shutil.rmtree(d, **kw)                       # type: ignore[arg-type]
    except Exception:
        shutil.rmtree(d, ignore_errors=True)


_TMP = Path(tempfile.mkdtemp(prefix="sql_sure_birimi_"))
(_TMP / "project.yaml").write_text(
    "sap_profile: s4_private\nrelease: '2025'\nsource_root: SOURCE_CODES\n", encoding="utf-8")
os.environ["CLAUDE_PROJECT_DIR"] = str(_TMP)
LIB = REPO / "scripts"
if KIP:
    dosya, capa, yeni, _ = MUTASYONLAR[KIP]
    _kum = _TMP / "kum_scripts"
    shutil.copytree(REPO / "scripts", _kum, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    _h = _kum / dosya
    _m = _h.read_bytes().decode("utf-8")
    if _m.count(capa) != 1:
        print(f"[KURULAMADI] {KIP}: capa {_m.count(capa)} kez bulundu (1 bekleniyordu)")
        _sil(_TMP)
        raise SystemExit(3)
    _h.write_bytes(_m.replace(capa, yeni, 1).encode("utf-8"))
    LIB = _kum
for _p in (REPO / "scripts" / "utils", REPO / "scripts", LIB):
    sys.path.insert(0, str(_p))

DEGER = "24.407"
S: list = []


def ekle(ad, kosul, detay=""):
    S.append((ad, bool(kosul), str(detay)[:400]))


def _xml(sure_etiketi=True):
    sure = ("<dataPreview:queryExecutionTime>%s</dataPreview:queryExecutionTime>" % DEGER
            if sure_etiketi else "")
    return ('<?xml version="1.0" encoding="utf-8"?><dataPreview:tableData '
            'xmlns:dataPreview="http://www.sap.com/adt/dataPreview">'
            '<dataPreview:totalRows>1</dataPreview:totalRows>' + sure +
            '<dataPreview:columns><dataPreview:metadata dataPreview:name="MANDT"/>'
            '<dataPreview:dataSet><dataPreview:data>100</dataPreview:data></dataPreview:dataSet>'
            '</dataPreview:columns></dataPreview:tableData>')


class _Sunucu(BaseHTTPRequestHandler):
    sure_var = True

    def _c(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n:
            self.rfile.read(n)
        govde = _xml(_Sunucu.sure_var).encode() if "datapreview/freestyle" in self.path else b""
        self.send_response(200)
        self.send_header("x-csrf-token", "SAHTETOKEN")
        self.send_header("Content-Type", "application/xml")
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        if govde:
            self.wfile.write(govde)

    do_GET = do_POST = do_HEAD = _c

    def log_message(self, *a):
        pass


def _kos(kok, *ek):
    proje = _TMP / "proje"
    proje.mkdir(exist_ok=True)
    (proje / ".conn_adt").write_text(
        "ADT_SAP_URL=%s\nADT_SAP_USER=SAP_USER_A\nADT_SAP_PASSWORD=x\nADT_SAP_CLIENT=100\n"
        "ADT_SAP_LANGUAGE=TR\n" % kok, encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("ADT_", "SAP_ADT_"))}
    env.update({"CLAUDE_PROJECT_DIR": str(proje), "ADT_SAP_URL": kok, "ADT_SAP_USER": "SAP_USER_A",
                "ADT_SAP_PASSWORD": "x", "ADT_SAP_CLIENT": "100", "ADT_SAP_LANGUAGE": "TR"})
    return subprocess.run([sys.executable, str(LIB / "run_sql_query.py"), "--cwd", str(proje),
                           "--query", "SELECT MANDT FROM T000", "--max-rows", "1", *ek],
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=120, env=env, cwd=str(proje))


def bolum_s1():
    eski = (sys.stdout, sys.stderr)
    sys.stdout = sys.stderr = io.StringIO()
    try:
        import sap_client as SC  # noqa: N812
    finally:
        sys.stdout, sys.stderr = eski
    c = SC.SAPClient.__new__(SC.SAPClient)
    c.adt_client = type("A", (), {"run_query": lambda self, q, row_number=100: _xml()})()
    r = c.run_sql_query("SELECT MANDT FROM T000", max_rows=1)
    ekle("S1 ⭐ SAPClient.run_sql_query: execution_time_ms == execution_time == 24.407 (ms)",
         isinstance(r, dict) and r.get("execution_time_ms") == 24.407 and r.get("execution_time") == 24.407,
         {k: (r or {}).get(k) for k in ("execution_time", "execution_time_ms")})


def bolum_s2_s4(kok):
    p = _kos(kok)
    satir = re.search(r"^Execution time: .*$", p.stdout, re.M)
    ekle("S2 ⭐ GERCEK run_sql_query.py tablo: 'Execution time: 24.407 ms', saniye ('s') etiketi YOK",
         p.returncode == 0 and satir is not None and "24.407 ms" in satir.group(0)
         and not re.search(r"24\.407s\b", p.stdout),
         f"rc={p.returncode} satir={satir.group(0) if satir else None} err={p.stderr[-160:]!r}")
    pj = _kos(kok, "--format", "json")
    try:
        js = json.loads(pj.stdout[pj.stdout.index("{"):])
    except Exception as exc:                          # noqa: BLE001
        js = {"_hata": repr(exc)}
    ekle("S3 ⭐ JSON: execution_time_ms=24.407 + ESKI execution_time anahtari ayni degerle (geriye uyum)",
         pj.returncode == 0 and js.get("execution_time_ms") == 24.407 and js.get("execution_time") == 24.407,
         f"rc={pj.returncode} js={ {k: js.get(k) for k in ('execution_time', 'execution_time_ms', '_hata')} }")
    _Sunucu.sure_var = False
    try:
        p0 = _kos(kok)
        pc = _kos(kok, "--format", "csv")
    finally:
        _Sunucu.sure_var = True
    ekle("S4 3.BAGLAM: alan YOKSA 0 -> 'Execution time: 0.000 ms' (cokme yok) + CSV'de meta satiri yok",
         p0.returncode == 0 and "Execution time: 0.000 ms" in p0.stdout
         and pc.returncode == 0 and "Execution time" not in pc.stdout and "MANDT" in pc.stdout,
         f"rc0={p0.returncode} rcc={pc.returncode} out0={p0.stdout[-120:]!r}")


def main() -> int:
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Sunucu)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    kok = "http://127.0.0.1:%d" % srv.server_address[1]
    try:
        for ad, fn in (("S1", bolum_s1), ("S2-S4", lambda: bolum_s2_s4(kok))):
            try:
                fn()
            except Exception as exc:                   # çökme != FAIL: ölçülür
                ekle(f"[BOLUM {ad} COKTU]", False, f"{type(exc).__name__}: {exc}")
    finally:
        srv.shutdown()
        _sil(_TMP)
    for ad, ok, d in S:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         -> {d}"))
    n = sum(1 for _, ok, _ in S if ok)
    print("  [KAPSAM] sahte SAP (127.0.0.1) + GERCEK run_sql_query.py alt sureci + SAPClient ayristirma. "
          "Birimin ms oldugunun CANLI kaniti fixture'da DEGIL (changelog olcum satiri).")
    print(f"\n{n}/{len(S)} OK")
    if KIP:
        dusen = {ad.split()[0] for ad, ok, _ in S if not ok}
        beklenen = MUTASYONLAR[KIP][3]
        print(f"[MUTASYON] {KIP} ilan edilen dusus: {sorted(beklenen)} · gercek: {sorted(dusen)}")
        if not dusen:
            return 0
        return 1 if beklenen & dusen else 2
    return 0 if n == len(S) else 1


if __name__ == "__main__":
    sys.exit(main())
