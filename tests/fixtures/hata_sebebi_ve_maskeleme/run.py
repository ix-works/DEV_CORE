#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hata_sebebi_ve_maskeleme fixture — MCP hata dönüşünde SAP sebebi + kimlik maskeleme.

NEDEN VAR (2026-10-12)
  ① `SAPADTError.__str__` yalnız "[kod] mesaj" basar; SAP gövdesindeki asıl sebep
     (`localizedMessage`, T100 ID/NO) MCP `_err_from_exc` dönüşüne hiç ulaşmıyordu.
     Artık kısa, kimliği maskelenmiş bir `sap_reason` alanı eklenir.
  ② Q363③ ölçümü: parola ASCII dışı karakter içerince temel kimlik yedeği
     `UnicodeEncodeError` fırlatıyordu; metni parolanın bir KARAKTERİNİ + KONUMUNU, `.object`'i
     "kullanıcı:parola"nın TAMAMINI taşıyordu ve MCP bunu `message` olarak döndürüyordu.

SÖZLEŞME
  · Gövde YOK / bozuk / HTML ⇒ `_err_from_exc` çıktısı pinli taban (6b6c11d) ile BİREBİR.
  · `exc:exception` gövdesi ⇒ `sap_reason.metin` (localizedMessage öncelikli), `t100`, `tip`.
  · Sebep metninde kullanıcı adı + parola gizlenir; `message`'da yalnız parola/kimlik başlığı.
  · ASCII-dışı parola ⇒ SAPAuthenticationError, metinde karakter/konum YOK, zincir koparılmış.

KULLANIM
  python tests/fixtures/hata_sebebi_ve_maskeleme/run.py
  python tests/fixtures/hata_sebebi_ve_maskeleme/run.py --mutasyon
"""
from __future__ import annotations

import io
import json
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
_GIT_KOK = Path(os.environ.get("HATA_SEBEBI_GIT_KOK") or REPO)
_TMP = tempfile.mkdtemp(prefix="hata_sebebi_")
os.environ["CLAUDE_PROJECT_DIR"] = _TMP
os.environ.pop("ADT_SAP_PASSWORD", None)
os.environ.pop("ADT_SAP_USER", None)
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
KULLANICI = "SAP_USER_A"
PAROLA = "Gizli" + chr(0x15E) + "ifre9"        # ASCII dışı karakterli sahte parola
ASCII_PAROLA = "SahteParola77"
EXC_GOVDE = (
    '<?xml version="1.0" encoding="utf-8"?><exc:exception xmlns:exc="http://www.sap.com/abapxml/'
    'types/communicationframework"><namespace id="com.sap.adt"/><type id="ExceptionResourceLockConflict"/>'
    '<message lang="EN">Request is blocked</message><localizedMessage lang="TR">Nesne ZSD001_CL_ORNEK '
    'SAP_USER_A kullanicisinin talebinde bloke edildi</localizedMessage><properties>'
    '<entry key="T100KEY-ID">CTS_WBO_API</entry><entry key="T100KEY-NO">019</entry>'
    '<entry key="T100KEY-V1">SAP_USER_A</entry></properties></exc:exception>')
YALNIZ_MESAJ = ('<exc:exception xmlns:exc="http://www.sap.com/abapxml/types/communicationframework">'
                '<message lang="EN">Only english reason</message></exc:exception>')
HTML_GOVDE = "<html><head><title>Application Server Error</title></head><body>500</body></html>"


def ekle(ad, kosul, detay=""):
    S.append((ad, bool(kosul), str(detay)[:260]))


def _sessiz(fn, *a, **k):
    eski = (sys.stdout, sys.stderr)
    atik = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
    sys.stdout = sys.stderr = atik
    try:
        try:
            return fn(*a, **k), None
        except BaseException as exc:                  # noqa: BLE001 — istisna ÖLÇÜLÜR
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


def _taban(yol: str, ad: str, paket: str = ""):
    g = subprocess.run(["git", "-C", str(_GIT_KOK), "show", f"{TABAN_SHA}:{yol}"], capture_output=True)
    if g.returncode != 0:
        return None
    mod = types.ModuleType(ad)
    mod.__file__ = str(REPO / yol)
    if paket:
        mod.__package__ = paket
    _sessiz(lambda: exec(compile(g.stdout.decode("utf-8"), mod.__file__, "exec"), mod.__dict__))
    return mod


def _j(d):
    return json.dumps(d, sort_keys=True, ensure_ascii=False)


class _Istemci:
    def __init__(self, parola, kullanici):
        self.adt_client = types.SimpleNamespace(password=parola, user=kullanici)


def bolum_s(L, A, AT):
    A._client = _Istemci(ASCII_PAROLA, KULLANICI)
    if AT is not None:
        AT._client = A._client
    e = L.SAPLockError("Object is locked", status_code=409, response_text=EXC_GOVDE)
    r = A._err_from_exc(e)
    sr = r.get("sap_reason") or {}
    ekle("S1 ⭐ exc:exception govdesi -> sap_reason: localizedMessage + T100 + tip",
         sr.get("t100") == "CTS_WBO_API/019" and sr.get("tip") == "ExceptionResourceLockConflict"
         and "bloke edildi" in (sr.get("metin") or "") and r.get("message") == str(e),
         _j(r))
    ekle("S2 ⭐ sebepte KULLANICI adi maskeli (<KULLANICI>), ham ad YOK",
         "<KULLANICI>" in (sr.get("metin") or "") and KULLANICI not in _j(sr), sr.get("metin"))
    r = A._err_from_exc(L.SAPADTError("x", status_code=400, response_text=YALNIZ_MESAJ))
    ekle("S3 localizedMessage yoksa <message> kullanilir; t100 yoksa None",
         (r.get("sap_reason") or {}).get("metin") == "Only english reason"
         and (r.get("sap_reason") or {}).get("t100") is None, _j(r))
    uzun = YALNIZ_MESAJ.replace("Only english reason", "A" * 900)
    r = A._err_from_exc(L.SAPADTError("x", status_code=400, response_text=uzun))
    ekle("S4 sebep metni SAP_SEBEP_SINIRI'na kisaltilir",
         len((r.get("sap_reason") or {}).get("metin") or "") == L.SAP_SEBEP_SINIRI, "")
    # KONTROL GRUBU: govde yok / bozuk / HTML -> taban ile BIREBIR
    if AT is None:
        ekle("S5 KONTROL GRUBU taban atom okunamadi (OLCULEMEDI)", False, "")
        return
    vakalar = [
        ("govde_yok", L.SAPADTError("Failed", status_code=500)),
        ("bozuk", L.SAPADTError("Failed", status_code=500, response_text=EXC_GOVDE[:120])),
        ("html", L.SAPADTError("Failed", status_code=500, response_text=HTML_GOVDE)),
        ("kilit", L.SAPLockError("locked", status_code=403, response_text="", lock_owner="SAP_USER_B")),
        ("genel", ValueError("bozuk girdi")),
    ]
    farklar = [ad for ad, ex in vakalar if _j(A._err_from_exc(ex)) != _j(AT._err_from_exc(ex))]
    ekle("S5 ⭐ KONTROL GRUBU: govde yok/bozuk/HTML/kilit/genel -> taban ile BIREBIR (5 vaka)",
         not farklar, f"farkli={farklar}")


def bolum_m(L, A):
    A._client = _Istemci(ASCII_PAROLA, KULLANICI)
    e = L.SAPADTError(f"auth echo password={ASCII_PAROLA} raw {ASCII_PAROLA}", status_code=401)
    r = A._err_from_exc(e)
    ekle("M1 ⭐ message'da PAROLA degeri gizlenir (alan + ham deger)",
         ASCII_PAROLA not in r["message"] and "<PAROLA>" in r["message"], r["message"])
    ekle("M2 message'da KULLANICI adi DEGISMEZ (yalniz parola maskelenir)",
         A._err_from_exc(L.SAPADTError(f"user {KULLANICI} failed"))["message"] == f"user {KULLANICI} failed",
         "")
    km = L.kimlik_maskele
    t = "Authorization: Basic U0FQX1VTRVJfQTpQVw== ve sap-password=abc&x=1"
    ekle("M3 kimlik_maskele: Authorization Basic + sap-password alan degeri gizlenir",
         "U0FQX1VTRVJfQTpQVw" not in km(t) and "abc&" not in km(t) and "x=1" in km(t), km(t))
    duz = "Sozdizimi hatasi satir 12: REPORT eksik"
    ekle("M4 kimlik icermeyen metin BAYT BAYT ayni", km(duz, parola=ASCII_PAROLA, kullanici=KULLANICI) == duz, "")
    ekle("M5 cok kisa parola (<3) maskelenmez (her harfi bozmasin)", km("abc ab", parola="ab") == "abc ab", "")
    # M6 (bug-gate 2026-10-14): kullanici adi ALT DIZE olarak maskeleniyordu → obje adi ve
    # kelimeler bozuluyordu (RISK ③ "diger tani alanlari korunur" ihlali). `_` + alfasayisal
    # kelime ICI sayilir; parola maskesi AYNEN kalir.
    t6 = "Object ZCL_DEV_TOOL locked by DEV in DEVELOPMENT"
    r6 = km(t6, parola="x", kullanici="DEV")
    ekle("M6 ⭐ kullanici adi yalniz BAGIMSIZ kelimede maskelenir (ZCL_DEV_TOOL / DEVELOPMENT korunur)",
         r6 == "Object ZCL_DEV_TOOL locked by <KULLANICI> in DEVELOPMENT", r6)
    r6b = km("dev: DEV, (Dev) dev_x xdev " + ASCII_PAROLA, parola=ASCII_PAROLA, kullanici="DEV")
    ekle("M7 sinir: harf-durumu duyarsiz + noktalama sinir sayilir + parola maskesi aynen",
         r6b == "<KULLANICI>: <KULLANICI>, (<KULLANICI>) dev_x xdev <PAROLA>", r6b)


def bolum_u(L, A, LT):
    c = L.SAPADTClient.__new__(L.SAPADTClient)
    c.user, c.password, c._auth_provider, c.debug_enabled = KULLANICI, PAROLA, None, False
    r, exc = _sessiz(c._get_auth_headers)
    m = str(exc or "")
    ekle("U1 ⭐ ASCII-disi parola -> SAPAuthenticationError; metinde karakter/konum/parola YOK",
         type(exc).__name__ == "SAPAuthenticationError" and chr(0x15E) not in m
         and "position" not in m and PAROLA not in m, f"{type(exc).__name__}: {m}")
    ekle("U2 zincir koparildi: __cause__ None + __suppress_context__ (parola .object'te tasinmaz)",
         exc is not None and exc.__cause__ is None and exc.__suppress_context__ is True, "")
    A._client = _Istemci(PAROLA, KULLANICI)
    out = A._err_from_exc(exc) if exc is not None else {}
    ekle("U3 MCP donusu auth_failed + parolasiz", out.get("error") == "auth_failed"
         and chr(0x15E) not in _j(out), _j(out))
    c.password = ASCII_PAROLA
    h, exc2 = _sessiz(c._get_auth_headers)
    ekle("U4 ASCII parolada baslik DEGISMEDI (Basic, ascii kodlama)",
         exc2 is None and h.get("Authorization", "").startswith("Basic "), repr(exc2))
    if LT is None:
        ekle("U5 KONTROL GRUBU taban lib okunamadi (OLCULEMEDI)", False, "")
        return
    ct = LT.SAPADTClient.__new__(LT.SAPADTClient)
    ct.user, ct.password, ct._auth_provider, ct.debug_enabled = KULLANICI, PAROLA, None, False
    _, exct = _sessiz(ct._get_auth_headers)
    ekle("U5 ⭐ KONTROL GRUBU: taban metni parolanin KARAKTERINI tasiyordu (vektor ayirt edici)",
         type(exct).__name__ == "UnicodeEncodeError" and "position" in str(exct)
         and PAROLA in str(getattr(exct, "object", "")),
         repr(exct))


def main() -> int:
    L = _imp("sap_adt_lib")
    A = _imp("mcp_servers.sap_adt.tools.atom")
    AT = _taban("mcp_servers/sap_adt/tools/atom.py", "atom_taban", "mcp_servers.sap_adt.tools")
    LT = _taban("scripts/sap_adt_lib.py", "sap_adt_lib_taban")
    for fn, a in ((bolum_s, (L, A, AT)), (bolum_m, (L, A)), (bolum_u, (L, A, LT))):
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


MUTASYONLAR = [
    ("M1 sap_reason alani eklenmez", "mcp_servers/sap_adt/tools/atom.py",
     "    if sebep:\n        out[\"sap_reason\"] = sebep\n",
     "    if False:\n        out[\"sap_reason\"] = sebep\n"),
    ("M2 sebepte kullanici maskelenmez", "mcp_servers/sap_adt/tools/atom.py",
     "        s[\"metin\"] = kimlik_maskele(s[\"metin\"], parola=parola, kullanici=kullanici)\n",
     "        s[\"metin\"] = kimlik_maskele(s[\"metin\"], parola=parola)\n"),
    ("M3 message parola maskelemesi kaldirilir", "mcp_servers/sap_adt/tools/atom.py",
     "        \"message\": _kimlik_maskele_guvenli(str(exc), parola),\n",
     "        \"message\": str(exc),\n"),
    ("M4 localizedMessage onceligi kaybolur", "scripts/sap_adt_lib.py",
     "    metin = yerel or mesaj\n", "    metin = mesaj or yerel\n"),
    ("M5 bozuk govdede ham metin sebep sayilir", "scripts/sap_adt_lib.py",
     "    except Exception:  # noqa: BLE001 — bozuk/HTML gövde: sebep YOK\n        return None\n",
     "    except Exception:  # noqa: BLE001 — bozuk/HTML gövde: sebep YOK\n"
     "        return {'metin': str(govde)[:300], 't100': None, 'tip': None}\n"),
    ("M6 zincir koparilmaz (from None silinir)", "scripts/sap_adt_lib.py",
     "iceriyor — karakter ve konumu GIZLENDI.\") from None",
     "iceriyor — karakter ve konumu GIZLENDI.\")"),
    ("M7 ASCII-disi parola yakalanmaz", "scripts/sap_adt_lib.py",
     "        except UnicodeEncodeError:\n            # Q363③",
     "        except KeyError:\n            # Q363③"),
    ("M8 kullanici adi alt dize olarak maskelenir (kelime siniri kalkar)", "scripts/sap_adt_lib.py",
     "re.sub(r'(?<!\\w)' + re.escape(str(kullanici)) + r'(?!\\w)', '<KULLANICI>'",
     "re.sub(re.escape(str(kullanici)), '<KULLANICI>'"),
]


def _mutasyon() -> int:
    kok = Path(tempfile.mkdtemp(prefix="hata_sebebi_kum_"))
    kotu = []
    try:
        for d in ("scripts", "mcp_servers"):
            shutil.copytree(REPO / d, kok / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        hedef = kok / "tests" / "fixtures" / BURASI.name
        hedef.mkdir(parents=True)
        shutil.copy2(Path(__file__), hedef / "run.py")
        env = dict(os.environ)
        env["HATA_SEBEBI_GIT_KOK"] = str(REPO)
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
