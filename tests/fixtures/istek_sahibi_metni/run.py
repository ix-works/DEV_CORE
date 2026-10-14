#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""istek_sahibi_metni fixture — Q362: `IS_LINK_UP=''` hata metni sahibi ADLANDIRIR.

NEDEN VAR (2026-10-12)
  `_verify_and_return_lock` CORRNR uyuşmazlığında `IS_LINK_UP` boşsa "The object is in your
  own transport <K>" diyordu. `IS_LINK_UP=''`'in anlamı "o istek altında SENİN GÖREVİN var"dır;
  isteğin KENDİSİ başkasına ait olabilir (dış kaynakta ölçülmüş vaka: istek başkasının, görev
  bizim; push o isteğe inip `ok:true` döndü). Ayrıca Fix metni "SM12 → release enqueue lock"
  öneriyordu (ADR 0005-C: kilit silmek ajanın işi değildir).

SÖZLEŞME (⚠ RİSK bloğu = kabul ölçütü)
  · Davranış DEĞİŞMEZ: aynı istisna sınıfı (`SAPLockError`), aynı `status_code` (409), aynı akış.
  · Sahip sorgusu (E070.AS4USER) DÜŞERSE (500 / bozuk XML / istisna) metin "sahip okunamadı"
    der ve dal YİNE aynı istisnayı fırlatır — sorgu hatası istisnayı DEĞİŞTİRMEZ.
  · Fix metninde SM12 kilit silme/bırakma önerisi YOK.
  · `sap_client` Bug-11 WARN'ı sahibi adlandırır; kurtarma (yeniden kilit) AYNEN.

BÖLÜMLER (SAP yok; lib'in GERÇEK `_verify_and_return_lock`'u sahte yanıt + sahte `run_query`)
  I  lib hata dalı · J  sap_client Bug-11 WARN · K  tüketici envanteri ("own transport" 0)

KULLANIM
  python tests/fixtures/istek_sahibi_metni/run.py
  python tests/fixtures/istek_sahibi_metni/run.py --mutasyon
"""
from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
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
_TMP = tempfile.mkdtemp(prefix="istek_sahibi_")
os.environ["CLAUDE_PROJECT_DIR"] = _TMP
for _p in (REPO / "scripts" / "utils", REPO / "scripts", REPO):
    sys.path.insert(0, str(_p))

S: list = []
_TUT: list = []
ISTEK, ISTENEN = "SAHK900077", "SAHK900001"
# ⚠ `kilit_birakma_durustlugu/run.py` `_ONERI_RE` ile BİREBİR AYNI desen (oradaki E5 kopya
# kaymasını ölçer). 2026-10-14 re-gate Ö1 kardeşi: buradaki eski dar desen "delete/remove
# lock", "kilidi sil", "clear the enqueue lock", "SM12 -> unlock" yazımlarını görmüyordu;
# Fix metnini TÜM gövdesiyle taradığı için (I2/I5) sonraki-satır fiilini görebilen tek vektör.
_ONERI_RE = re.compile(
    r"(release (the )?(enqueue )?lock|(delete|remove) (the )?(enqueue )?lock|delete the enqueue|"
    r"SM12\s*(→|->)\s*(release|delete)|use SM12 to|kilidi sil|kilidi bırak\b|kilidi birak\b|"
    r"(?<!to )clear (the )?(enqueue )?lock|SM12\s*(→|->)\s*(clear|unlock|remove|drop)|"
    r"kilid[iı] (kaldır|kaldir|temizle)|kilid[iı]n[iı] (sil|bırak\b|birak\b|kaldır|kaldir|temizle))",
    re.IGNORECASE)


def ekle(ad, kosul, detay=""):
    S.append((ad, bool(kosul), str(detay)[:260]))


def _yakala(fn, *a, **k):
    eski = (sys.stdout, sys.stderr)
    t = io.StringIO()
    sys.stdout = sys.stderr = t
    try:
        try:
            return fn(*a, **k), None, t.getvalue()
        except Exception as exc:                      # noqa: BLE001 — istisna ÖLÇÜLÜR
            return None, exc, t.getvalue()
    finally:
        sys.stdout, sys.stderr = eski


def _sessiz_import(ad):
    eski = (sys.stdout, sys.stderr)
    atik = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
    sys.stdout = sys.stderr = atik
    try:
        import importlib
        return importlib.import_module(ad)
    finally:
        _TUT.append(atik)
        sys.stdout, sys.stderr = eski


class _Y:
    def __init__(self, text):
        self.text, self.status_code, self.headers = text, 200, {}


def lock_xml(corrnr, is_link_up):
    return ('<asx:abap xmlns:asx="http://www.sap.com/abapxml"><asx:values><DATA>'
            f"<LOCK_HANDLE>LH-1</LOCK_HANDLE><CORRNR>{corrnr}</CORRNR>"
            f"<IS_LINK_UP>{is_link_up}</IS_LINK_UP></DATA></asx:values></asx:abap>")


def dp_xml(sahip):
    return ('<dataPreview:tableData xmlns:dataPreview="http://www.sap.com/adt/dataPreview">'
            '<dataPreview:columns><dataPreview:metadata dataPreview:name="AS4USER"/>'
            f'<dataPreview:dataSet><dataPreview:data>{sahip}</dataPreview:data>'
            '</dataPreview:dataSet></dataPreview:columns></dataPreview:tableData>')


def _istemci(L, sorgu):
    c = L.SAPADTClient.__new__(L.SAPADTClient)
    c.debug_enabled = False
    c.user = "SAP_USER_A"
    c.sorgular = []
    c.unlock_object = lambda url, h: True

    def _rq(sql, row_number=100, decode=False):
        c.sorgular.append(sql)
        if isinstance(sorgu, Exception):
            raise sorgu
        return sorgu
    c.run_query = _rq
    return c


def bolum_i(L):
    URL = "/sap/bc/adt/oo/classes/zsd001_cl_ornek"

    def kos(is_link_up, sorgu, transport=ISTENEN, corrnr=ISTEK):
        c = _istemci(L, sorgu)
        r, exc, log = _yakala(c._verify_and_return_lock, _Y(lock_xml(corrnr, is_link_up)), URL, transport)
        return r, exc, log, c

    r, exc, log, c = kos("", dp_xml("SAP_USER_B"))
    m = str(exc or "")
    ekle("I1 ⭐ IS_LINK_UP bos + sahip okundu -> SAPLockError/409 AYNI + 'sahibi SAP_USER_B' + "
         "'own transport' YOK",
         type(exc).__name__ == "SAPLockError" and getattr(exc, "status_code", None) == 409
         and f"Istek {ISTEK} (sahibi SAP_USER_B)" in m and "own transport" not in m
         and c._last_lock_istek_sahibi == "SAP_USER_B",
         f"exc={type(exc).__name__} kod={getattr(exc, 'status_code', None)} sahip={c._last_lock_istek_sahibi}")
    ekle("I2 ⭐ Fix metninde SM12 silme/birakma ONERISI YOK, 'KONTROL ET' VAR",
         not _ONERI_RE.search(m) and "KONTROL ET" in m, m[m.find("Fix"):][:160])
    r, exc, log, c = kos("", L.SAPADTError("sahte E070 hatasi", status_code=500))
    m = str(exc or "")
    ekle("I3 ⭐ RISK: sahip sorgusu 500 -> YINE SAPLockError/409 + 'sahip okunamadı'",
         type(exc).__name__ == "SAPLockError" and getattr(exc, "status_code", None) == 409
         and "sahip okunamadı" in m and c._last_lock_istek_sahibi is None,
         f"exc={type(exc).__name__} metin={m[:120]!r}")
    r, exc, log, c = kos("", "<bozuk")
    ekle("I4 sahip sorgusu bozuk XML -> yine SAPLockError + 'sahip okunamadı'",
         type(exc).__name__ == "SAPLockError" and "sahip okunamadı" in str(exc),
         f"exc={type(exc).__name__}")
    r, exc, log, c = kos("X", dp_xml("SAP_USER_C"))
    m = str(exc or "")
    ekle("I5 yabanci dal (X) -> SAPLockError/409 AYNI + sahip adlandirildi + SM12 onerisi YOK",
         type(exc).__name__ == "SAPLockError" and getattr(exc, "status_code", None) == 409
         and "sahibi SAP_USER_C" in m and "FOREIGN" in m and not _ONERI_RE.search(m),
         f"exc={type(exc).__name__}")
    r, exc, log, c = kos("", dp_xml("SAP_USER_B"), transport=ISTEK)
    ekle("I6 KONTROL CORRNR == istenen -> istisna YOK + handle doner + sahip sorgusu KOSMADI",
         exc is None and r == "LH-1" and not c.sorgular, f"r={r!r} exc={exc!r} sorgu={len(c.sorgular)}")
    r, exc, log, c = kos("", dp_xml("SAP_USER_B"), corrnr="X'; DROP")
    ekle("I7 istek no bicimi tanınmadı -> SQL GITMEZ + 'sahip okunamadı' + yine SAPLockError",
         type(exc).__name__ == "SAPLockError" and not c.sorgular and "sahip okunamadı" in str(exc),
         f"sorgu={c.sorgular}")


def bolum_j(L, SC):
    AD = "ZSD001_CL_ORNEK"
    KAYNAK = "CLASS zsd001_cl_ornek DEFINITION.\nENDCLASS.\n"

    def kos(sahip):
        class _A(L.SAPADTClient):
            def __init__(self):
                self.url, self.user, self.debug_enabled = "https://x", "SAP_USER_A", False
                self._last_lock_effective_transport = ISTENEN
                self._last_lock_is_link_up = ""
                self._last_lock_istek_sahibi = None
                self.kilit = 0

            def is_object_locked(self, url):
                return {"locked": False}

            def register_object_in_transport(self, *a):
                return {"registered": True, "method": "sahte"}

            def fetch_source_etag(self, url):
                return None

            def lock_object(self, url, transport=None, **kw):
                self.kilit += 1
                if self.kilit == 1:
                    self._last_lock_effective_transport = ISTEK
                    self._last_lock_is_link_up = ""
                    self._last_lock_istek_sahibi = sahip
                    raise L.SAPLockError("sahte uyusmazlik", status_code=409)
                self._last_lock_effective_transport = ISTEK
                return "LH-2"

            def set_object_source(self, *a, **k):
                return True

            def unlock_object(self, url, h):
                return True

            def activate_object(self, *a):
                return {"success": True}

            def get_object_source(self, *a, **k):
                return KAYNAK
        ist = object.__new__(SC.SAPClient)
        ist.adt_client = _A()
        ist.debug_enabled = False
        ist.local_base = Path(_TMP)
        ist._find_existing_transport = lambda n, t, tr: tr
        ist.syntax_check = lambda *a, **k: {"valid": True}
        p = Path(_TMP) / f"{AD}.clas.abap"
        p.write_bytes(KAYNAK.encode("utf-8"))
        r, exc, log = _yakala(ist.push_object, AD, object_type="class", transport=ISTENEN,
                              source_file=str(p))
        return r, log, ist.adt_client

    r, log, a = kos("SAP_USER_B")
    ekle("J1 ⭐ Bug-11 WARN sahibi ADLANDIRIR + BASKA kullanici uyarisi; kurtarma AYNEN (2 kilit, success)",
         f"istek {ISTEK}: sahibi SAP_USER_B" in log and "BAŞKA kullanıcıya ait" in log
         and a.kilit == 2 and (r or {}).get("success") is True,
         [s.strip() for s in log.splitlines() if "WARN" in s][:2])
    r, log, a = kos(None)
    ekle("J2 sahip okunamadı -> WARN 'sahip okunamadı' + BASKA uyarisi YOK; kurtarma AYNEN",
         "sahip okunamadı" in log and "BAŞKA kullanıcıya" not in log and a.kilit == 2,
         [s.strip() for s in log.splitlines() if "WARN" in s][:1])
    r, log, a = kos("SAP_USER_A")
    ekle("J3 KONTROL sahip = mevcut kullanici -> BASKA uyarisi YOK",
         "sahibi SAP_USER_A" in log and "BAŞKA kullanıcıya" not in log, "")


def bolum_k():
    bulgu = []
    for kok in ("scripts", "mcp_servers"):
        for p in (REPO / kok).rglob("*.py"):
            try:
                t = p.read_text(encoding="utf-8")
            except Exception:
                continue
            for i, s in enumerate(t.splitlines(), 1):
                if re.search(r"own transport", s, re.IGNORECASE) and not s.lstrip().startswith("#"):
                    bulgu.append(f"{p.relative_to(REPO).as_posix()}:{i}")
    ekle("K1 tuketici envanteri: uretimde 'own transport' METNI 0 (yorum haric)", not bulgu, bulgu[:5])


def bolum_s():
    """S1: `_ONERI_RE` kopyası `kilit_birakma_durustlugu` deseniyle BİREBİR (iki yönlü: orada E5).
    `--degisen` bir fixture dizinini yalnız KENDİ birimine eşler ⇒ kopya kayması her iki
    fixture düzenlendiğinde de kendi koşusunda görünsün diye çift taraflıdır."""
    import ast
    kardes = REPO / "tests" / "fixtures" / "kilit_birakma_durustlugu" / "run.py"
    kdesen, kbayrak = None, None
    if kardes.is_file():
        for n in ast.walk(ast.parse(kardes.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_ONERI_RE"
                                                 for t in n.targets) and isinstance(n.value, ast.Call):
                kdesen = ast.literal_eval(n.value.args[0])
                kbayrak = ast.unparse(n.value.args[1]) if len(n.value.args) > 1 else None
    ekle("S1 _ONERI_RE kopyasi kilit_birakma_durustlugu deseniyle BIREBIR (kopya kaymasi yok)",
         kdesen == _ONERI_RE.pattern and kbayrak == "re.IGNORECASE",
         f"kardes_var={kardes.is_file()} ayni={kdesen == _ONERI_RE.pattern} bayrak={kbayrak}")


def main() -> int:
    L = _sessiz_import("sap_adt_lib")
    SC = _sessiz_import("sap_client")
    for ad, fn, arg in (("I", bolum_i, (L,)), ("J", bolum_j, (L, SC)), ("K", bolum_k, ()),
                        ("S", bolum_s, ())):
        try:
            fn(*arg)
        except Exception as exc:
            ekle(f"[BOLUM COKTU] {ad}", False, f"{type(exc).__name__}: {exc}")
    gecen = sum(1 for _, ok, _ in S if ok)
    for ad, ok, detay in S:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad} -> {detay}")
    print(f"\n{gecen}/{len(S)} OK")
    return 0 if gecen == len(S) else 1


MUTASYONLAR = [
    ("M1 sahip yardimcisi istisnayi yutmuyor (hata dali bozulur)", "scripts/sap_adt_lib.py",
     "        except Exception as e:\n            return f\"sahip okunamadı: {type(e).__name__}\"",
     "        except KeyError as e:\n            return f\"sahip okunamadı: {type(e).__name__}\""),
    ("M2 eski 'own transport' metni geri", "scripts/sap_adt_lib.py",
     "f\"Bu 'senin istegin' demek DEGILDIR — istegin sahibi baskasi olabilir.\\n\"",
     "f\"The object is in your own transport.\\n\""),
    ("M3 Fix'e SM12 release onerisi geri", "scripts/sap_adt_lib.py",
     "                    f\"  2. SM12'de bu objenin kilidini KONTROL ET (silme/birakma karari\\n\"\n"
     "                    f\"     kullanicidadir — ADR 0005-C; ajan kilit silmez)\\n\"\n"
     "                    f\"  3. Retry the push with transport {transport}\\n\\n\"\n"
     "                    f\"  Or:",
     "                    f\"  2. SM12 → release enqueue lock for this object\\n\"\n"
     "                    f\"  3. Retry the push with transport {transport}\\n\\n\"\n"
     "                    f\"  Or:"),
    ("M4 Bug-11 WARN sahibi okumuyor", "scripts/sap_client.py",
     "_sahip = getattr(self.adt_client, '_last_lock_istek_sahibi', None)", "_sahip = None"),
    ("M5 istek no dogrulamasi yok (ham SQL)", "scripts/sap_adt_lib.py",
     "            if not re.fullmatch(r'[A-Z0-9]{10}', t):", "            if False:"),
    # re-gate Ö1 kardeşi (2026-10-14): eşanlamlı fiil SM12'siz SONRAKİ satırda (FOREIGN Fix metni).
    # Eski dar desen bunu görmüyordu; I5 tüm metni taradığı için yeni desenle düşer.
    ("M6 FOREIGN Fix: 'clear the enqueue lock' SM12'siz sonraki satirda", "scripts/sap_adt_lib.py",
     "                    f\"     (only if authorised — coordinate with the transport owner)\\n\"\n"
     "                    f\"  2. SM12'de bu objenin kilidini KONTROL ET (silme/birakma karari\\n\"\n"
     "                    f\"     kullanicidadir — ADR 0005-C; ajan kilit silmez)\\n\"\n",
     "                    f\"     (only if authorised — coordinate with the transport owner)\\n\"\n"
     "                    f\"  2. SM12'de bu objenin kilidini KONTROL ET (silme/birakma karari\\n\"\n"
     "                    f\"     kullanicidadir), then clear the enqueue lock\\n\"\n"),
    ("M7 bu fixture'in _ONERI_RE kopyasi daralir (kopya kaymasi -> S1)",
     "tests/fixtures/istek_sahibi_metni/run.py",
     "    r\"kilid[iı] (kaldır|kaldir|temizle)|kilid[iı]n[iı] (sil|bırak\\b|birak\\b|kaldır|kaldir|temizle))\",\n",
     "    r\"kilid[iı] (kaldır|kaldir|temizle))\",\n"),
]


def _mutasyon() -> int:
    kok = Path(tempfile.mkdtemp(prefix="istek_sahibi_kum_"))
    kotu = []
    try:
        for d in ("scripts", "mcp_servers"):
            shutil.copytree(REPO / d, kok / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        hedef = kok / "tests" / "fixtures" / BURASI.name
        hedef.mkdir(parents=True)
        shutil.copy2(Path(__file__), hedef / "run.py")
        # S1 kardeş fixture'ın desenini okur ⇒ kumda da bulunmalı (yoksa her mutant sahte-YAKALANDI)
        kardes = kok / "tests" / "fixtures" / "kilit_birakma_durustlugu"
        kardes.mkdir(parents=True)
        shutil.copy2(REPO / "tests" / "fixtures" / "kilit_birakma_durustlugu" / "run.py", kardes / "run.py")
        r0 = subprocess.run([sys.executable, str(hedef / "run.py")], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=300, cwd=str(kok))
        if r0.returncode:
            print(f"  [KURULAMADI] kum tabani kirmizi: rc={r0.returncode}")
            return 1
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
    sys.exit(main())
