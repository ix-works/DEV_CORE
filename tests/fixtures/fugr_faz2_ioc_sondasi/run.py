#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fugr_faz2_ioc_sondasi fixture — FUGR toplu aktivasyonunda 2. faz `ioc` = hüküm DEĞİL.

NEDEN VAR (2026-10-12)
  Canlı ölçüm (bir fonksiyon grubu): `activate_object` 2. fazda yine `ioc:inactiveObjects`
  (yalnız FUGR/F, grup adı iki kez) aldı ve `success=False` "Activation incomplete — inactive
  sub-objects: <FG>, <FG>" döndü. Oysa obje `version=active` okunuyordu ve aktive-bekleyen
  worklist BOŞTU ⇒ sahte-negatif. FUGR'da bu gövde hüküm taşımıyor; karar Q187 tasarımındaki
  BAĞIMSIZ worklist sondasına bırakıldı.

SÖZLEŞME
  · FUGR + 2. faz ioc + worklist temiz  → success True, sonda `checked_active`, E hatası YOK.
  · FUGR + 2. faz ioc + grup worklist'te → success False + `kalan_inaktif` (gerçek kusur görünür).
  · FUGR + 2. faz ioc + sonda kurulamaz  → success False + `dogrulanamadi` (BAŞARI DEĞİL).
  · FUGR DIŞI (sınıf) + 2. faz ioc       → BİREBİR eski: "Activation incomplete" E, sonda YOK.
  · KONTROL GRUBU: pinli taban `6b6c11d` temiz-worklist senaryosunda False döner (vektör ayırt edici).
  Gövde örnekleri `canli/` — genericize edilmiş canlı biçim (aktivasyon_govde_hukmu korpusundan).
  ⚠ 2. FAZ GÖVDE BİÇİMİ DOĞRULANAMADI: ilk vakanın 2. faz ioc gövdesi kayıtlı değil; vaka
  yeniden koşulduğunda tekrarlanmadı. Vektör 1. faz HAM gövdesinin biçimini kullanır (2026-10-12'de
  yeniden ölçüldü, `canli/faz1_ioc.xml` ile yapı birebir: boş-obje + transport entry'si · FUGR/F grup ·
  parentUri'li FUGR/F `source/main`). "<FG>, <FG>" listesinin bu iki FUGR/F'den geldiği ÇIKARIMDIR.

KULLANIM
  python tests/fixtures/fugr_faz2_ioc_sondasi/run.py
  python tests/fixtures/fugr_faz2_ioc_sondasi/run.py --mutasyon
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
CANLI = BURASI / "canli"
TABAN_SHA = "6b6c11d"
_GIT_KOK = Path(os.environ.get("FUGR_IOC_GIT_KOK") or REPO)
_TMP = tempfile.mkdtemp(prefix="fugr_ioc_")
os.environ["CLAUDE_PROJECT_DIR"] = _TMP
for _p in (REPO / "scripts" / "utils", REPO / "scripts", REPO):
    sys.path.insert(0, str(_p))

S: list = []
_TUT: list = []
GRUP_URI = "/sap/bc/adt/functions/groups/zsd001_fg_ornek"
GRUP_AD = "ZSD001_FG_ORNEK"
SINIF_URI = "/sap/bc/adt/oo/classes/zcl_sd001_ornek_a"
SINIF_AD = "ZCL_SD001_ORNEK_A"
WL_UC = "/sap/bc/adt/activation/inactiveobjects"
SINIF_IOC = ('<?xml version="1.0" encoding="utf-8"?><ioc:inactiveObjects xmlns:ioc="http://www.sap.com/'
             'abapxml/inactiveCtsObjects"><ioc:entry><ioc:object ioc:user="SAP_USER_A" '
             'ioc:deleted="false"><ioc:ref adtcore:uri="%s" adtcore:type="CLAS/OC" '
             'adtcore:name="%s" xmlns:adtcore="http://www.sap.com/adt/core"/></ioc:object>'
             '<ioc:transport/></ioc:entry></ioc:inactiveObjects>' % (SINIF_URI, SINIF_AD))


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


def _oku(ad):
    return (CANLI / ad).read_text(encoding="utf-8")


class _Y:
    def __init__(self, kod, text=""):
        self.status_code, self.text, self.headers = kod, text, {}


class _Sunucu:
    def __init__(self, faz_govdesi, wl_kodu=200, wl_govde=""):
        self.faz_govdesi, self.wl_kodu, self.wl_govde = faz_govdesi, wl_kodu, wl_govde
        self.postlar: list = []
        self.wl_get = 0

    def get(self, url, headers=None, params=None, verify=None, timeout=None, **kw):
        if url.endswith(WL_UC):
            self.wl_get += 1
            return _Y(self.wl_kodu, self.wl_govde if self.wl_kodu == 200 else "sahte hata")
        return _Y(404, "")

    def istek(self, method, url, headers=None, data=None, params=None, **kw):
        if method.lower() == "post" and url.endswith("/sap/bc/adt/activation"):
            self.postlar.append(dict(params or {}))
            return _Y(200, self.faz_govdesi)
        return _Y(599, "beklenmeyen istek")


def _istemci(L, sunucu):
    c = L.SAPADTClient.__new__(L.SAPADTClient)
    c.debug_enabled = False
    c.url = "http://sahte.invalid"
    c.user = "SAP_USER_A"
    c.session = sunucu
    c._get_headers = lambda *a, **k: {}
    c._request_with_csrf_retry = sunucu.istek
    return c


def _aktive(L, sunucu, ad=GRUP_AD, uri=GRUP_URI):
    c = _istemci(L, sunucu)
    r, exc = _sessiz(c.activate_object, ad, uri)
    return r if isinstance(r, dict) else {"_istisna": repr(exc)}


def _e_metinleri(r):
    return [e.get("message", "") for e in (r.get("errors") or []) if e.get("type") == "E"]


def bolum_f(L):
    s = _Sunucu(_oku("faz1_ioc.xml"), wl_govde=_oku("worklist_fugr_temiz.xml"))
    r = _aktive(L, s)
    dg = r.get("aktivasyon_dogrulama") or {}
    ekle("F1 ⭐ FUGR 2. faz ioc + worklist TEMIZ -> success True, sonda checked_active, E yok",
         r.get("success") is True and r.get("aktivasyon_hukmu") is True
         and dg.get("sonda") == "checked_active" and not _e_metinleri(r) and len(s.postlar) == 2,
         f"success={r.get('success')} sonda={dg.get('sonda')} E={_e_metinleri(r)} post={len(s.postlar)}")
    ekle("F1b hukum_sebep FUGR 2. faz ioc'u ADLANDIRIR (iz kaybolmaz)",
         str(r.get("hukum_sebep", "")).startswith("fugr_faz2_ioc_yeniden"), r.get("hukum_sebep"))
    s = _Sunucu(_oku("faz1_ioc.xml"), wl_govde=_oku("worklist_fugr_ff.xml"))
    r = _aktive(L, s)
    dg = r.get("aktivasyon_dogrulama") or {}
    kalan = [k.get("name") for k in dg.get("kalan_inaktif") or []]
    ekle("F2 ⭐ FUGR 2. faz ioc + grup worklist'te -> success False + kalan_inaktif (kusur gorunur)",
         r.get("success") is False and r.get("aktivasyon_hukmu") is False and GRUP_AD in kalan
         and any("GERCEKLESMEDI" in m for m in _e_metinleri(r)),
         f"success={r.get('success')} kalan={kalan}")
    s = _Sunucu(_oku("faz1_ioc.xml"), wl_kodu=500)
    r = _aktive(L, s)
    ekle("F3 FUGR 2. faz ioc + sonda kurulamaz -> success False + dogrulanamadi (BASARI DEGIL)",
         r.get("success") is False and r.get("dogrulanamadi") is True,
         f"success={r.get('success')} dogrulanamadi={r.get('dogrulanamadi')}")
    s = _Sunucu(SINIF_IOC, wl_govde=_oku("worklist_fugr_temiz.xml"))
    r = _aktive(L, s, SINIF_AD, SINIF_URI)
    ekle("F4 KONTROL FUGR DISI (sinif) 2. faz ioc -> BIREBIR eski: 'Activation incomplete' E, sonda YOK",
         r.get("success") is False and any("Activation incomplete" in m for m in _e_metinleri(r))
         and s.wl_get == 0 and "aktivasyon_dogrulama" not in r,
         f"success={r.get('success')} wl_get={s.wl_get} E={_e_metinleri(r)[:1]}")
    g = subprocess.run(["git", "-C", str(_GIT_KOK), "show", f"{TABAN_SHA}:scripts/sap_adt_lib.py"],
                       capture_output=True)
    if g.returncode != 0:
        ekle("F5 KONTROL GRUBU taban okunamadi (OLCULEMEDI)", False,
             g.stderr.decode("utf-8", "replace")[:160])
        return
    LT = types.ModuleType("sap_adt_lib_taban")
    LT.__file__ = str(REPO / "scripts" / "sap_adt_lib.py")
    _sessiz(lambda: exec(compile(g.stdout.decode("utf-8"), LT.__file__, "exec"), LT.__dict__))
    s = _Sunucu(_oku("faz1_ioc.xml"), wl_govde=_oku("worklist_fugr_temiz.xml"))
    r = _aktive(LT, s)
    ekle("F5 ⭐ KONTROL GRUBU: taban ayni senaryoda SAHTE-NEGATIF ('Activation incomplete')",
         r.get("success") is False and any("Activation incomplete" in m for m in _e_metinleri(r)),
         f"taban success={r.get('success')} E={_e_metinleri(r)[:1]}")


def main() -> int:
    import importlib
    L, exc = _sessiz(importlib.import_module, "sap_adt_lib")
    if L is None:
        print(f"[fixture-hatasi] sap_adt_lib import edilemedi: {exc!r}")
        return 2
    bolum_f(L)
    for ad, ok, d in S:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         -> {d}"))
    n = sum(1 for _, ok, _ in S if ok)
    print(f"\n{n}/{len(S)} OK")
    shutil.rmtree(_TMP, ignore_errors=True)
    return 0 if n == len(S) else 1


MUTASYONLAR = [
    ("M1 FUGR istisnasi kaldirilir (eski sahte-negatif)", "scripts/sap_adt_lib.py",
     "        if p2['ioc_refs'] and fugr_bilgi is not None:\n",
     "        if False:\n"),
    ("M2 istisna FUGR disina da yayilir", "scripts/sap_adt_lib.py",
     "        if p2['ioc_refs'] and fugr_bilgi is not None:\n",
     "        if p2['ioc_refs']:\n"),
    ("M3 ioc dogrudan BASARI sayilir (sonda atlanir)", "scripts/sap_adt_lib.py",
     "            p2['aktivasyon_hukmu'] = None\n            p2['hukum_sebep'] = 'fugr_faz2_ioc_yeniden: '",
     "            p2['aktivasyon_hukmu'] = True\n            p2['success'] = True\n"
     "            p2['hukum_sebep'] = 'fugr_faz2_ioc_yeniden: '"),
]


def _mutasyon() -> int:
    kok = Path(tempfile.mkdtemp(prefix="fugr_ioc_kum_"))
    kotu = []
    try:
        shutil.copytree(REPO / "scripts", kok / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        hedef = kok / "tests" / "fixtures" / BURASI.name
        shutil.copytree(BURASI, hedef, ignore=shutil.ignore_patterns("__pycache__"))
        env = dict(os.environ)
        env["FUGR_IOC_GIT_KOK"] = str(REPO)
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
