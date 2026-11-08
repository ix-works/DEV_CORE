#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""csrf_tanima_ortak — CSRF reddi TEK yuklemde tanınır (DEV_CORE #411, 2026-11-08).

NEDEN VAR
  `SAPADTClient._should_retry` (create_* yollarinin `_retry_request` dongusu) CSRF reddini
  YALNIZ Ingilizce `'CSRF token validation failed'` gövdesinden taniyordu. Kardes yol
  `_request_with_csrf_retry` dilden bagimsizdi: 403 + (gövdede 'CSRF' VEYA
  `x-csrf-token: Required` başlığı). Ayrica `lock_object` + `create_object` kendi kopyalarini
  tasiyordu (403 + 'CSRF', başlıksız). Dördü artik `_csrf_reddi_mi`yi paylasir.
  Ikinci kusur (ayni sinif — retry'da TAZE token): `create_table`'in `make_request`'i header'i
  closure DISINDA bir kez kuruyordu ⇒ `_retry_request` token'i tazelese de tekrar istegi ESKI
  token'la gidiyordu (DTEL/domain/yapi/CDS closure icinde kuruyor; tablo tek istisnaydi).
  Canli olcum (lider, 2026-11-08, salt-okur uc, gecersiz token): TR/EN/DE uc dilde de 403 +
  `x-csrf-token: Required`, gövde hep Ingilizce. Almanca gövdeli sunucu OLCULMEDI.

VEKTORLER
  S1-S4  `_should_retry` CSRF reddini tanir: EN gövde · DE gövde · başlık + DE gövde · yalniz başlık
  N1-N3  tanimaz: CSRF disi 403 (yetki, başlıksız) · 200 + 'CSRF' gövde · 500 + EN CSRF metni
         (⚠ N3 DAVRANIS DEGISIKLIGI: eski yuklem 403 aramadan metne bakiyordu; ortak yuklem 403 ister)
  Q1-Q3  `_request_with_csrf_retry`: DE gövde -> 2 istek (2. TAZE token) · yalniz başlık -> 2 ·
         yetki 403 -> 1 istek (retry YOK)
  T1-T2  GERCEK GIRIS `create_table` (`_retry_request` uzerinden): DE CSRF 403 -> 2 POST, 2. POST
         TAZE token tasir · yetki 403 -> 1 POST
  W1     kablolama: `self._csrf_reddi_mi(response)` TAM 4 cagri; eski Ingilizce yuklem kodda YOK

KIPLER (BEYAN) — dusen kume ilanla AYNI -> exit 1 · farkli -> exit 2 SAPMA · capa != 1 /
yukleme hatasi -> exit 3 KURULAMADI.
  --mutasyon-should-eski   `_should_retry` eski Ingilizce-yalniz yukleme doner
  --mutasyon-baslik-yok    ortak yuklemin başlık dali sokulur
  --mutasyon-403siz        ortak yuklemin 403 sarti sokulur
  --mutasyon-tablo-bayat   create_table header'i closure DISINA tasinir (bayat token)
  --mutasyon-taban         3353fca sap_adt_lib (git show; sig klonda exit 2 DOGRULANAMADI)
SAP GEREKTIRMEZ: oturum ve token sahtedir.
"""
from __future__ import annotations

import importlib.util
import io
import os
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

_GERCEK_ERR = sys.stderr
KOK = Path(__file__).resolve().parents[3]
LIB = KOK / "scripts" / "sap_adt_lib.py"
if not LIB.is_file():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {KOK}")
TABAN_SHA = "3353fca"

GECERLI_KIP = ("--mutasyon-should-eski", "--mutasyon-baslik-yok", "--mutasyon-403siz",
               "--mutasyon-tablo-bayat", "--mutasyon-taban")
KIPLER = [a for a in sys.argv[1:] if a.startswith("--")]
if len(KIPLER) > 1 or (KIPLER and KIPLER[0] not in GECERLI_KIP):
    print(f"[KULLANIM] gecerli kipler: {', '.join(GECERLI_KIP)} (en fazla bir tane)")
    sys.exit(2)
KIP = KIPLER[0] if KIPLER else ""

MUTASYONLAR = {
    "--mutasyon-should-eski": (
        ("        if self._csrf_reddi_mi(response):\n            if self.retry_on_csrf_fail:\n",
         "        if 'CSRF token validation failed' in response.text:\n"
         "            if self.retry_on_csrf_fail:\n"),),
    "--mutasyon-baslik-yok": (
        ("        return any(str(k).lower() == 'x-csrf-token' and str(v).lower() == 'required'\n",
         "        return False and any(str(k).lower() == 'x-csrf-token' and str(v).lower() == 'required'\n"),),
    "--mutasyon-403siz": (
        ("        if getattr(response, 'status_code', None) != 403:\n            return False\n",
         ""),),
    "--mutasyon-tablo-bayat": (
        ("        def make_request():\n"
         "            # #411 (2026-11-08): header'lar closure İÇİNDE kurulur.",
         "        _bayat = self._get_headers(\n"
         "            'application/vnd.sap.adt.tables.v2+xml',\n"
         "            'application/vnd.sap.adt.tables.v2+xml'\n"
         "        )\n\n"
         "        def make_request():\n"
         "            # #411 (2026-11-08): header'lar closure İÇİNDE kurulur."),
        ("            )\n            return self.session.post(\n"
         "                f\"{self.url}/sap/bc/adt/ddic/tables\",\n",
         "            )\n            headers = _bayat\n            return self.session.post(\n"
         "                f\"{self.url}/sap/bc/adt/ddic/tables\",\n"),),
}
BEKLENEN_DUSEN = {
    # W1 de duser: eski yuklem kodda 1 kez geri gelir + ortak cagri 3'e iner (olcumle eklendi)
    "--mutasyon-should-eski": {"S2", "S3", "S4", "N3", "T1", "W1"},
    "--mutasyon-baslik-yok": {"S3", "S4", "Q2"},
    "--mutasyon-403siz": {"N2", "N3"},
    "--mutasyon-tablo-bayat": {"T1"},
    "--mutasyon-taban": {"S2", "S3", "S4", "N3", "T1", "W1"},
}

KUM = Path(tempfile.mkdtemp(prefix="csrftanima_"))
_eski_cwd = os.getcwd()
os.environ["CLAUDE_PROJECT_DIR"] = str(KUM)
(KUM / ".conn_adt").write_text(
    "ADT_SAP_URL=https://ornek.invalid\nADT_SAP_USER=TESTUSER\n"
    "ADT_SAP_PASSWORD=x\nADT_SAP_CLIENT=100\nADT_SAP_TIER=DEV\n", encoding="utf-8")
os.chdir(KUM)
for _p in (KOK / "scripts", KOK / "scripts" / "utils"):
    sys.path.insert(0, str(_p))


def _bitir(kod: int) -> None:
    try:
        os.chdir(_eski_cwd)
    except Exception:
        pass
    shutil.rmtree(KUM, ignore_errors=True)
    sys.exit(kod)


def _kaynak() -> str:
    canli = LIB.read_text(encoding="utf-8")
    if KIP == "":
        return canli
    if KIP == "--mutasyon-taban":
        r = subprocess.run(["git", "-C", str(KOK), "show", f"{TABAN_SHA}:scripts/sap_adt_lib.py"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print(f"[DOGRULANAMADI] git show {TABAN_SHA} -> {r.stderr.strip()[:160]}", file=_GERCEK_ERR)
            _bitir(2)
        if "'CSRF token validation failed' in response.text" not in r.stdout:
            print(f"[DOGRULANAMADI] taban {TABAN_SHA} kusurlu surum DEGIL", file=_GERCEK_ERR)
            _bitir(2)
        return r.stdout
    metin = canli
    for capa, yerine in MUTASYONLAR[KIP]:
        n = metin.count(capa)
        if n != 1:
            print(f"[KURULAMADI] {KIP}: capa {n} kez bulundu (1 bekleniyordu): {capa.strip()[:70]}",
                  file=_GERCEK_ERR)
            _bitir(3)
        metin = metin.replace(capa, yerine)
    return metin


def _yukle():
    src = _kaynak()
    yol = KUM / "sap_adt_lib_csrf_olcum.py"
    yol.write_text(src, encoding="utf-8")
    yedek = sys.stdout, sys.stderr
    sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
    try:
        spec = importlib.util.spec_from_file_location("sap_adt_lib_csrf_olcum", yol)
        m = importlib.util.module_from_spec(spec)            # type: ignore[arg-type]
        sys.modules["sap_adt_lib_csrf_olcum"] = m
        spec.loader.exec_module(m)                           # type: ignore[union-attr]
        return m, src
    except Exception as exc:                                 # noqa: BLE001
        sys.stdout, sys.stderr = yedek
        print(f"[KURULAMADI] modul yuklenemedi: {type(exc).__name__}: {exc}", file=_GERCEK_ERR)
        _bitir(3)
    finally:
        sys.stdout, sys.stderr = yedek


L, KAYNAK = _yukle()
print(f"### kip: {KIP or '(duzeltilmis modul)'}")
SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(ok), detay))


class Y:
    def __init__(self, status, text="", headers=None):
        self.status_code = status
        self.text = text
        self.headers = headers or {}
        self.content = text.encode("utf-8")


EN = "CSRF token validation failed"
DE = "CSRF-Token-Überprüfung fehlgeschlagen"
DE_CSRFSIZ = "Token-Überprüfung fehlgeschlagen"
YETKI = "Keine Berechtigung für Objekt S_DEVELOP (Aktivität 02)"
YENI = "TAZE-TOKEN-411"
ESKI = "ESKI-TOKEN-411"


def istemci(yanitlar):
    c = L.SAPADTClient.__new__(L.SAPADTClient)
    c.csrf_token = ESKI
    c.url = "https://ornek.invalid"
    c.language = "TR"
    c.timeout_default = 5
    c.debug_enabled = False
    c.max_retries = 3
    c.retry_delay = 0
    c.retry_on_timeout = c.retry_on_csrf_fail = c.retry_on_5xx = True
    c._update_cookies = lambda r: None
    c.yenilemeler = []

    def _fetch(force_refresh=False):
        c.yenilemeler.append(force_refresh)
        c.csrf_token = YENI
        return YENI
    c.fetch_csrf_token = _fetch
    c._get_headers = lambda *a, **k: {"Accept": "x", "X-CSRF-Token": c.csrf_token}

    class Oturum:
        def __init__(self):
            self.giden = []
            self.kalan = list(yanitlar)

        def _yanit(self, headers):
            self.giden.append(dict(headers or {}))
            return self.kalan.pop(0) if self.kalan else Y(200, "ok")

        def request(self, method, url, headers=None, timeout=None, **kw):
            return self._yanit(headers)

        def post(self, url, headers=None, data=None, params=None, timeout=None, **kw):
            return self._yanit(headers)
    c.session = Oturum()
    return c


def tekrar(y):
    c = istemci([])
    try:
        return c._should_retry(y, 0, "olcum")
    except Exception as exc:                                 # noqa: BLE001
        return ("COKTU", f"{type(exc).__name__}: {exc}")


for ad, y, bekle in (
        ("S1 403 + EN gövde -> CSRF retry", Y(403, EN), True),
        ("S2 403 + DE gövde ('CSRF' gecer, başlık yok) -> CSRF retry", Y(403, DE), True),
        ("S3 403 + `x-csrf-token: Required` + DE gövde ('CSRF' yok) -> CSRF retry",
         Y(403, DE_CSRFSIZ, {"x-csrf-token": "Required"}), True),
        ("S4 403 + yalniz başlık (buyuk harfli ad), bos gövde -> CSRF retry",
         Y(403, "", {"X-CSRF-Token": "Required"}), True),
        ("N1 CSRF DISI 403 (yetki gövdesi, başlık yok) -> RETRY YOK", Y(403, YETKI), False),
        ("N2 200 + gövdede 'CSRF' -> RETRY YOK", Y(200, "CSRF hakkinda bilgi"), False),
        ("N3 500 + EN CSRF metni -> CSRF retry YOK (403 sarti; 500 zaten tekrar edilmez)",
         Y(500, EN), False)):
    r = tekrar(y)
    csrf_mi = bool(r[0]) and "CSRF" in str(r[1] or "")
    kontrol(ad, csrf_mi == bekle and r[0] != "COKTU", f"donus={r}")


def iste(yanitlar):
    c = istemci(yanitlar)
    try:
        c._request_with_csrf_retry("post", "https://ornek.invalid/x", headers={"Accept": "x"})
    except Exception as exc:                                 # noqa: BLE001
        return None, f"COKTU {type(exc).__name__}: {exc}"
    return c, ""


c, h = iste([Y(403, DE), Y(200, "ok")])
kontrol("Q1 _request_with_csrf_retry DE gövde -> 2 istek, 2. TAZE token",
        c is not None and len(c.session.giden) == 2
        and c.session.giden[1].get("X-CSRF-Token") == YENI,
        h or f"giden={c.session.giden}")
c, h = iste([Y(403, "", {"x-csrf-token": "Required"}), Y(200, "ok")])
kontrol("Q2 _request_with_csrf_retry yalniz başlık -> 2 istek",
        c is not None and len(c.session.giden) == 2, h or f"giden={len(c.session.giden)}")
c, h = iste([Y(403, YETKI)])
kontrol("Q3 _request_with_csrf_retry yetki 403 -> 1 istek (retry YOK)",
        c is not None and len(c.session.giden) == 1 and c.yenilemeler == [],
        h or f"giden={len(c.session.giden)} yenileme={c.yenilemeler}")


def tablo(yanitlar):
    c = istemci(yanitlar)
    yedek = sys.stdout
    sys.stdout = io.StringIO()
    try:
        r = c.create_table("ZSD001_T_ORNEK", "Ornek tablo", "ZSD001_CLC",
                           fields=[{"name": "ID", "type": "abap.char(10)", "key": True}])
        return c, r, ""
    except Exception as exc:                                 # noqa: BLE001
        return c, None, f"{type(exc).__name__}: {exc}"
    finally:
        sys.stdout = yedek


c, r, h = tablo([Y(403, DE), Y(201, "", {"Location": "/sap/bc/adt/ddic/tables/zsd001_t_ornek"})])
giden = c.session.giden
kontrol("T1 create_table DE CSRF 403 -> 2 POST, 2. POST TAZE token, basari",
        not h and len(giden) == 2 and giden[0].get("X-CSRF-Token") == ESKI
        and giden[1].get("X-CSRF-Token") == YENI and bool(r and r.get("success")),
        h or f"post={len(giden)} tokenlar={[g.get('X-CSRF-Token') for g in giden]} r={r}")
c, r, h = tablo([Y(403, YETKI)])
kontrol("T2 create_table yetki 403 -> 1 POST (retry YOK)",
        len(c.session.giden) == 1, h or f"post={len(c.session.giden)}")

n_cagri = KAYNAK.count("self._csrf_reddi_mi(response)")
eski_yuklem = KAYNAK.count("'CSRF token validation failed' in response.text")
kontrol("W1 kablolama: `self._csrf_reddi_mi(response)` 4 cagri, eski Ingilizce yuklem 0",
        n_cagri == 4 and eski_yuklem == 0, f"cagri={n_cagri} eski={eski_yuklem}")

basarisiz = [s for s in SONUC if not s[1]]
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"  -> {detay}"))
print(f"\nSONUC: {len(SONUC) - len(basarisiz)}/{len(SONUC)} PASS")
if KIP == "":
    _bitir(1 if basarisiz else 0)
dusen = {s[0].split()[0] for s in basarisiz}
ilan = BEKLENEN_DUSEN[KIP]
if dusen and dusen == ilan:
    print(f"[DUSTU] {KIP}: dusen kume ilanla AYNI: {', '.join(sorted(dusen))}")
    _bitir(1)
print(f"[SAPMA] {KIP}: ilan edilmeyen dusen={sorted(dusen - ilan)} · "
      f"ilan edilip dusmeyen={sorted(ilan - dusen)}")
_bitir(2)
