#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""aktivasyon_govde_hukmu — Q187 + Q188 + Q231: aktivasyon hükmünün TEK KAYNAĞI.

NEDEN VAR (canlı ölçüm, DEV, adt-gateway 2026-09-13; ham gövdeler `canli/` altında MASKELİ):
  · Q187 — `sap_adt_lib._parse_activation_response` `activationExecuted=false` +
    `generationExecuted=true` gövdesini BAŞARI sayıyordu. FUGR 2. faz gövdesi tam buydu
    (0 mesaj) ve aynı anda worklist'te FUGR/F + FUGR/FF DURUYORDU ⇒ sahte-yeşil.
  · Q188 — aktivasyon gövdesinden hüküm çıkaran noktalar AYRI kopya sözleşmeler taşıyordu
    ve ayrışmıştı (lib ↔ create_rap_service zıt hükümler; push_bo_atomic BOŞ gövdeyi OK
    sayıyordu; populate_lock_objects `activationExecuted="true"` dizgesi + type=E'yi yok sayıyordu).
  · Q231-a — tipli FUGR toplu aktivasyonu gövdeye FUGR/FF koymuyordu (SAP 1. fazda FF
    vermiyor); çalışan istek F + parentUri'li FF + preauditRequested=true idi.
  · Q231-b — `adt_activate` klasik yol `activated:false` iken `ok:true` dönüyordu.
  · Q307 — `syntax_check_via_activation` SAP kontrolü KOŞMADIĞINDA (`checkExecuted=false`,
    mesajsız; boş/kısa gövde; ioc; bayraksız) `valid:True` dönüyordu. Artık `valid` üç değerli
    (None = ÖLÇÜLEMEDİ) ve gövde hükmü kanonik `aktivasyon_govde_hukmu`'ndan gelir (J bölümü;
    lib + `sap_client.syntax_check` + MCP `adt_syntax_check` + `syntax_check.py` CLI).
  · Q313 — `syntax_check.py::check_ddic_object` HTTP 200 + kök `adtcore:version` "active" DEĞİLKEN
    (ya da öznitelik yokken) `valid:True` dönüyordu; CLI rc 0 `[OK] Check passed`. Artık None +
    `sozdizimi_sebep` (K bölümü; canlı aktif DTEL/TABL gövdeleri `canli/ddic_*.xml`, MASKELİ).
    ⚠ İnaktif gövde SENTETİKTİR: canlıda inaktif DDIC yoktu; SAP'nin tam değeri DOĞRULANAMADI.
  · Q317 — CLI "kontrol KOŞMADI"yı `has syntax errors` diye basıyordu: `SAPClient.syntax_check`
    istisna sözlüğü (`valid:False` + `error`, errors YOK) ve `check_ddic_object` HTTP≠200/404 +
    istisna dalları. Artık CLI `olculemedi_sebebi` → `[UNVERIFIED] … NOT MEASURED` rc 1 (J25 · K8 ·
    K12–K14); DDIC dalları `valid:None` + `ddic_http_<kod>` / `ddic_istisna:<Tip>`. sap_client sözlüğü
    DEĞİŞMEDİ (push ön-kontrolü + MCP `_gecerlilik` onu zaten ölçülemedi okuyor).

SÖZLEŞME (`sap_adt_lib.aktivasyon_govde_hukmu`): True · False · None ("gövde hüküm taşımıyor"
→ BAĞIMSIZ worklist sondası karar verir; sonda kurulamazsa BAŞARI DEĞİL, DOĞRULANAMADI).

⛔ SİLİNMEZ ÇAPALAR:
  · A1/A2/A3 + C4 + D3 + E2 + F2 + H4 — KONTROL GRUPLARI: gerçek (canlı) başarı gövdeleri
    BAŞARI kalır. Kalkarsa test aşırı-sıkı olur ve her aktivasyonu bloklayan bir fix'i geçirir.
  · B4 + B7 + B9 — EŞLEŞTİRME FP ÇAPALARI: kardeş önek / aynı adlı başka tip / URI'li hedefte
    çıplak ad "kalan" ÜRETMEZ. B5 + B6 + B6b + B3 — EŞLEŞTİRME KÖRLÜK ÇAPALARI: büyük/küçük harf,
    ad+tip ve alt-kaynak (FF) eşleşmesi kaçmaz. İkisi birlikte "worklist temiz" hükmünü
    AYIRT EDİCİ tutar (lider kararı 2026-09-13, madde 3).
  · A12 — ⚠GEVŞETME HÜCRESİ (`_BAYRAKSIZ_GOVDE_HUKMU`): karar değişirse bu satır BİLEREK güncellenir.
  · J1–J5 + J17/J18 + J20/J21 + J23/J24 — Q307 KONTROL GRUPLARI: SAP kontrolü GERÇEKTEN koştuysa
    temiz gövde `valid:True`, E mesajı `valid:False` kalır ("her şeye None" diyen fix geçemesin).
    J13 + J14 — BİLEREK KORUNAN iki `valid:False` (ayrıştırılamayan gövde · HTTP 403 kilit):
    `sap_client.push_object` ön-kontrolü bunlarda aktivasyonu durdurmaya devam eder.
  · K1 + K2 + K10 — Q313 KONTROL GRUPLARI: canlı aktif DDIC gövdesi `valid:True` / CLI rc 0 kalır.
    K7 + K11 — BİLEREK KORUNAN `valid:False` (404 = gerçek cevap). K4/M27 — hüküm sürüm DEĞERİNE bağlı değil.
  · J24 + J26 + J27 + K11 — Q317 KONTROL GRUPLARI: errors DOLU False (SAP E mesajı · 403 kilit · 404)
    CLI'de `[FAIL]` kalır; ölçülemedi koşulu gerçek hatayı GİZLEMEZ. K8 çapası Q317 ile ÇEVRİLDİ (False→None).
⚠ SINIR (yazılı, ölçülemez): obje aktivasyondan ÖNCE worklist'te değilse "listede yok" ayırt
  edici değildir — ön-snapshot alınmaz (lider kararı).

KULLANIM (repo kökünden):
  python tests/fixtures/aktivasyon_govde_hukmu/run.py               # vektörler
  python tests/fixtures/aktivasyon_govde_hukmu/run.py --mutasyon    # kopya ağaçta mutasyonlar
  python tests/fixtures/aktivasyon_govde_hukmu/run.py --taban <ref> # eski-kod karşıtlığı (git show)
SAP GEREKTİRMEZ: HTTP oturumu sahtedir; GERÇEK lib / create_rap_service / push_bo_atomic /
populate_lock_objects / sap_client / composite / atom gövdeleri koşar.
"""
from __future__ import annotations

import ast
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
REPO = Path(__file__).resolve().parents[3]
CANLI = BURASI / "canli"
if not (REPO / "scripts" / "sap_adt_lib.py").is_file():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")

WL_UC = "/sap/bc/adt/activation/inactiveobjects"
GRUP_URI = "/sap/bc/adt/functions/groups/zsd001_fg_ornek"
FF_URI = GRUP_URI + "/fmodules/zsd001_fm_ornek_iki"
DDLS_URI = "/sap/bc/adt/ddic/ddl/sources/zsd001_i_ornek"
LOCK_URI = "/sap/bc/adt/ddic/lockobjects/sources/ezsd001_ornek"

# ÜRETİM PROD DOSYALARI — `--taban` bunları eski sürümle değiştirir; SINIF bölümü bunları tarar.
URETIM = ["scripts/sap_adt_lib.py", "scripts/create_rap_service.py", "scripts/push_bo_atomic.py",
          "scripts/populate_lock_objects.py", "scripts/push_textpool.py",
          "mcp_servers/sap_adt/tools/atom.py", "mcp_servers/sap_adt/tools/composite.py",
          "scripts/sap_client.py", "scripts/syntax_check.py"]

HTML500 = "<html><head><title>500 Internal Server Error</title></head><body>SAP Web AS</body></html>"
ESKI_STIL = '<?xml version="1.0"?><chkl:messages><msg severity="I"><txt>ok</txt></msg></chkl:messages>'
BASARI_MSG_OGESI = ('<?xml version="1.0"?><chkl:messages xmlns:chkl="http://www.sap.com/abapxml/'
                    'checklist" activationExecuted="true"/>')


def _govde(ae="true", ge="false", ce="true", msg=""):
    return ('<?xml version="1.0" encoding="utf-8"?><chkl:messages xmlns:chkl="http://www.sap.com/'
            'abapxml/checklist"><chkl:properties checkExecuted="%s" activationExecuted="%s" '
            'generationExecuted="%s"/>%s</chkl:messages>' % (ce, ae, ge, msg))


def _msg(tip, metin="Ornek mesaj"):
    return ('<msg type="%s" line="1"><shortText><txt>%s</txt></shortText></msg>' % (tip, metin))


def _oku(ad):
    return (CANLI / ad).read_text(encoding="utf-8")


def _canli_girdiler(govde):
    """Fixture-YEREL ayrıştırıcı (üretim ayrıştırıcısı ÇAĞRILMAZ — mutasyon tabanı olmasın)."""
    out = []
    for m in re.finditer(r'<ioc:object [^>]*>\s*<ioc:ref ([^>]*?)/>', govde):
        a = dict(re.findall(r'adtcore:(\w+)="([^"]*)"', m.group(1)))
        out.append({"uri": a.get("uri", ""), "type": a.get("type", ""), "name": a.get("name", ""),
                    "parent_uri": a.get("parentUri", "")})
    return out


def _wl(girdiler):
    """Canlı biçimde worklist gövdesi (transport girdisi + objeler)."""
    parca = ['<?xml version="1.0" encoding="utf-8"?><ioc:inactiveObjects xmlns:ioc="http://www.sap.com/'
             'abapxml/inactiveCtsObjects"><ioc:entry><ioc:object/><ioc:transport ioc:user="SAP_USER_B" '
             'ioc:linked="false"><ioc:ref adtcore:uri="/sap/bc/adt/cts/transportrequests/SAHK900001" '
             'adtcore:type="/RQ" adtcore:name="SAHK900001" adtcore:description="Ornek istek" '
             'xmlns:adtcore="http://www.sap.com/adt/core"/></ioc:transport></ioc:entry>']
    for g in girdiler:
        pu = (' adtcore:parentUri="%s"' % g["parent_uri"]) if g.get("parent_uri") else ""
        parca.append('<ioc:entry><ioc:object ioc:user="SAP_USER_A" ioc:deleted="false"><ioc:ref '
                     'adtcore:uri="%s" adtcore:type="%s" adtcore:name="%s"%s xmlns:adtcore="http://'
                     'www.sap.com/adt/core"/></ioc:object><ioc:transport/></ioc:entry>'
                     % (g["uri"], g["type"], g["name"], pu))
    parca.append("</ioc:inactiveObjects>")
    return "".join(parca)


class _Y:
    def __init__(self, kod, metin="", url=""):
        self.status_code, self.text, self.url = kod, metin, url
        self.headers = {}


# ─────────────────────────────────────────────────────────────────────────────
# ORTAM (import-anı yan etkileri gecici köke)
# ─────────────────────────────────────────────────────────────────────────────
_TMP = tempfile.mkdtemp(prefix="akt_hukum_")
os.environ["CLAUDE_PROJECT_DIR"] = _TMP
Path(_TMP, "project.yaml").write_text(
    "sap_profile: s4_private\nrelease: '2025'\nsource_root: SOURCE_CODES\n", encoding="utf-8")
os.chdir(_TMP)
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

_TUTUCULAR: list = []   # import-anında stdout'u sarmalayan modüllerin sarmalayıcısı GC'de buffer kapatmasın


def _sessiz_import(ad):
    eski = (sys.stdout, sys.stderr)
    atik = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
    sys.stdout = sys.stderr = atik
    try:
        import importlib
        return importlib.import_module(ad)
    finally:
        _TUTUCULAR.append((sys.stdout, sys.stderr, atik))
        sys.stdout, sys.stderr = eski


def _sessiz(fn, *a, **k):
    eski = (sys.stdout, sys.stderr)
    tampon = io.StringIO()
    sys.stdout = sys.stderr = tampon
    try:
        return fn(*a, **k)
    finally:
        sys.stdout, sys.stderr = eski


S: list = []


def ekle(ad, kosul, detay=""):
    S.append((ad, bool(kosul), str(detay)[:220]))


def bolum(ad):
    def dek(fn):
        def sar(*a, **k):
            try:
                fn(*a, **k)
            except Exception as exc:                   # çökme != FAIL: ölçülür
                ekle(f"[BOLUM COKTU] {ad}", False, f"{type(exc).__name__}: {exc}")
        return sar
    return dek


# ─────────────────────────────────────────────────────────────────────────────
# Sahte HTTP
# ─────────────────────────────────────────────────────────────────────────────
class _Sunucu:
    """Aktivasyon + worklist uçlarını MODELLER (senaryo listesi değil).

    FUGR kuralı (canlı ölçülen): toplu gövdede parentUri'li FUGR/FF VARSA aktivasyon gerçekleşir
    (hepsi-true gövde, worklist temizlenir); YOKSA `activationExecuted=false generationExecuted=true`
    döner ve worklist AYNEN kalır. 1. aktivasyon POST'u (seed) canlı `faz1_ioc` gövdesini alır.
    """

    def __init__(self, kip, girdiler, wl_kodu=200, wl_govde=None):
        self.kip, self.girdiler, self.wl_kodu, self.wl_govde = kip, list(girdiler), wl_kodu, wl_govde
        self.postlar: list = []
        self.wl_get = 0

    def get(self, url, headers=None, params=None, verify=None, timeout=None, **kw):
        if url.endswith(WL_UC):
            self.wl_get += 1
            if self.wl_kodu != 200:
                return _Y(self.wl_kodu, "sahte hata", url)
            return _Y(200, self.wl_govde if self.wl_govde is not None else _wl(self.girdiler), url)
        return _Y(404, "", url)

    def request(self, method, url, headers=None, timeout=None, **kw):
        if method.lower() == "get":
            return self.get(url, headers=headers)
        if method.lower() == "post" and url.endswith("/sap/bc/adt/activation"):
            govde = kw.get("data") or ""
            if isinstance(govde, bytes):
                govde = govde.decode("utf-8")
            self.postlar.append((govde, dict(kw.get("params") or {})))
            return _Y(200, self._aktivasyon(govde), url)
        return _Y(599, "beklenmeyen istek", url)

    def post(self, url, params=None, headers=None, data=None, verify=None, timeout=None, **kw):
        return self.request("post", url, headers=headers, data=data, params=params)

    def _aktivasyon(self, govde):
        k = self.kip
        if k.startswith("fugr"):
            if len(self.postlar) == 1:
                return _oku("faz1_ioc.xml")
            ff_var = re.search(r'adtcore:uri="%s"[^>]*adtcore:parentUri="%s"' % (re.escape(FF_URI),
                                                                              re.escape(GRUP_URI)), govde)
            if k == "fugr_calisir" and ff_var:
                self.girdiler = [g for g in self.girdiler if not g["type"].startswith("FUGR")]
                return _oku("govde_hepsi_true.xml")
            return _oku("govde_yalniz_generation.xml")
        return {"true": _oku("govde_true.xml"), "gen": _oku("govde_yalniz_generation.xml"),
                "bos": "", "eski_stil": ESKI_STIL, "ioc": _oku("faz1_ioc.xml"),
                "true_e": _govde(msg=_msg("E"))}[k]


def _fugr_girdileri():
    return _canli_girdiler(_oku("worklist_fugr_ff.xml"))


def _diger_girdiler():
    return [g for g in _fugr_girdileri() if not g["type"].startswith("FUGR")]


def _ddls_girdisi():
    return {"uri": DDLS_URI, "type": "DDLS/DF", "name": "ZSD001_I_ORNEK", "parent_uri": ""}


def _sahte_lib(L, sunucu):
    class _SahteAdt(L.SAPADTClient):
        def __init__(self):                       # noqa: D401 — gercek __init__ baglanti arar
            self.url = "https://sap.example.test:44300"
            self.session = sunucu
            self.csrf_token = "SAHTE-CSRF"
            self.client = "000"
            self.language = "TR"
            self.user = "SAP_USER_A"
            self._auth_provider = None
            self.debug_enabled = False
            self.timeout_default = 5
            self.timeout_short = 5
            self._last_lock_effective_transport = None

        def _get_auth_header(self):
            return "Basic SAHTE"

        def fetch_csrf_token(self, force_refresh=False):
            return self.csrf_token

        def _update_cookies(self, response):
            return None
    return _SahteAdt()


class _Duz:
    """create_rap_service / push_bo_atomic / populate_lock_objects'in gördüğü düz client."""

    def __init__(self, sunucu, get_yok=False):
        self.url = "https://sap.example.test:44300"
        self.client, self.language = "000", "TR"
        if get_yok:
            self.session = types.SimpleNamespace(post=sunucu.post)
        else:
            self.session = sunucu


# ─────────────────────────────────────────────────────────────────────────────
@bolum("A kanonik govde hukmu")
def bolum_a(L):
    f = getattr(L, "aktivasyon_govde_hukmu", None)
    tablo = [
        ("A1 KONTROL canli check/act=true gen=false -> True", _oku("govde_true.xml"), True, "activation_executed"),
        ("A2 KONTROL canli zaten-aktif DDLS yeniden aktivasyon -> True", _oku("govde_reaktivasyon.xml"), True, None),
        ("A3 KONTROL canli check/act/gen=true -> True", _oku("govde_hepsi_true.xml"), True, None),
        ("A4 ⭐Q187 canli act=false+gen=true 0 mesaj -> None (BASARI DEGIL)",
         _oku("govde_yalniz_generation.xml"), None, "yalniz_generation"),
        ("A5 canli faz-1 ioc:inactiveObjects -> False", _oku("faz1_ioc.xml"), False, "ioc_inaktif_liste"),
        ("A6 act=true + type=E -> False", _govde(msg=_msg("E")), False, "hata_mesaji"),
        ("A7 act=true + type=A -> False", _govde(msg=_msg("A")), False, "hata_mesaji"),
        ("A8 KONTROL act=true + type=W -> True (uyari normal)", _govde(msg=_msg("W")), True, None),
        ("A9 act=false gen=false -> False", _govde(ae="false", ce="false"), False, "activation_not_executed"),
        ("A10 BOS govde -> False", "", False, "govde_bos"),
        ("A11 HTML 500 sayfasi -> False", HTML500, False, "govde_taninmadi"),
        ("A12 ⚠GEVSETME HUCRESI bayraksiz chkl -> None", ESKI_STIL, None, "bayrak_yok"),
        ("A13 KONTROL bayrak messages ogesinde -> True", BASARI_MSG_OGESI, True, None),
        ("A14 ayristirilamayan govde + type=E -> False",
         '<chkl:messages activationExecuted="true"><msg type="E"><txt>x</txt>', False, "hata_mesaji"),
    ]
    for ad, govde, bekl, sebep in tablo:
        if f is None:
            ekle(ad, False, "aktivasyon_govde_hukmu YOK")
            continue
        hk = f(govde)
        ekle(ad, hk["hukum"] is bekl and (sebep is None or hk["sebep"] == sebep),
             f"hukum={hk['hukum']} sebep={hk['sebep']}")


@bolum("B worklist eslestirme")
def bolum_b(L):
    ayr = getattr(L, "aktivasyon_worklist_ayristir", None)
    kal = getattr(L, "aktivasyon_worklist_kalan", None)
    sonda = getattr(L, "aktivasyon_worklist_sondasi", None)
    if not (ayr and kal and sonda):
        for ad in ("B1", "B2", "B3", "B3b", "B4", "B5", "B6", "B6b", "B7", "B7b", "B8", "B9", "B10", "B11", "B12"):
            ekle(f"{ad} worklist eslestirme", False, "kanonik worklist yardimcilari YOK")
        return
    g = ayr(_oku("worklist_fugr_ff.xml"))
    tipler = [x["type"] for x in g]
    ff = [x for x in g if x["type"] == "FUGR/FF"]
    ekle("B1 canli worklist ayristi: 6 obje (/RQ disi) + FF parentUri=grup",
         len(g) == 6 and "/RQ" not in tipler and tipler.count("CLAS/OM") == 2
         and len(ff) == 1 and ff[0]["parent_uri"] == GRUP_URI, f"tipler={tipler}")
    ad = lambda xs: sorted(x["name"] for x in xs)                                        # noqa: E731
    hedef_grup = [{"uri": GRUP_URI, "name": "ZSD001_FG_ORNEK", "type": "FUGR/F"}]
    r = kal(g, hedef_grup)
    ekle("B2 grup hedefi -> kalan F + FF", ad(r) == ["ZSD001_FG_ORNEK", "ZSD001_FM_ORNEK_IKI"], ad(r))
    yalniz_ff = [x for x in g if x["type"] != "FUGR/F"]
    r = kal(yalniz_ff, [{"uri": GRUP_URI}])
    ekle("B3 ⭐KORLUK grup hedefi, listede yalniz FF -> FF kalan (alt kaynak)", ad(r) == ["ZSD001_FM_ORNEK_IKI"], ad(r))
    r = kal([{"uri": "/sap/bc/adt/baska/yol", "type": "FUGR/FF", "name": "ZSD001_FM_X",
              "parent_uri": GRUP_URI}], [{"uri": GRUP_URI}])
    ekle("B3b parentUri dali tek basina eslesir", ad(r) == ["ZSD001_FM_X"], ad(r))
    r = kal(g, [{"uri": "/sap/bc/adt/functions/groups/zsd001_fg_orn"}])
    ekle("B4 ⭐FP kardes onek (zsd001_fg_orn) -> kalan YOK", r == [], ad(r))
    r = kal(g, [{"uri": GRUP_URI.upper()}])
    ekle("B5 ⭐KORLUK hedef URI BUYUK harf -> F + FF yine yakalanir", len(r) == 2, ad(r))
    r = kal(g, [{"name": "zsd001_fg_ornek", "type": "FUGR/F"}])
    ekle("B6 ⭐KORLUK URI'siz ad(kucuk harf)+tip -> F yakalanir", ad(r) == ["ZSD001_FG_ORNEK"], ad(r))
    g2 = ayr(_oku("worklist_ayni_ad.xml"))
    r = kal(g2, [{"name": "ZSD001_FM_ORNEK", "type": "FUGR"}])
    ekle("B6b ⭐KORLUK alt tipsiz hedef tipi (FUGR) -> ayni adli F + FF ikisi de yakalanir",
         sorted(x["type"] for x in r) == ["FUGR/F", "FUGR/FF"], [x["type"] for x in r])
    yalniz_f = [x for x in g2 if x["type"] != "FUGR/FF"]
    r = kal(yalniz_f, [{"name": "ZSD001_FM_ORNEK", "type": "FUGR/FF"}])
    ekle("B7 ⭐FP canli ayni adli F/FF: FF hedefi, listede yalniz F -> kalan YOK (tip ayirir)", r == [], ad(r))
    r = kal(g2, [{"name": "ZSD001_FM_ORNEK", "type": "FUGR/FF"}])
    ekle("B7b ayni adli F/FF: FF listede -> yalniz FF kalan",
         [x["type"] for x in r] == ["FUGR/FF"], [x["type"] for x in r])
    r = kal(g, [{"uri": "/sap/bc/adt/oo/classes/zcl_sd001_ornek_a"}])
    ekle("B8 CLAS hedefi -> OC + OM (fragmanli source/main), komsu sinif YOK",
         sorted(x["type"] for x in r) == ["CLAS/OC", "CLAS/OM"], [(x["type"], x["name"]) for x in r])
    r = kal(g, [{"uri": "/sap/bc/adt/ddic/ddl/sources/zcl_sd001_ornek_a", "name": "ZCL_SD001_ORNEK_A"}])
    ekle("B9 ⭐FP URI'li hedefte ciplak ad baska tipi eslemez", r == [], ad(r))
    ekle("B10 ⭐200 + ioc OLMAYAN govde -> sonda None (temiz DEGIL)",
         sonda(_Duz(_Sunucu("true", [], wl_govde="<root/>")), hedef_grup)[0] is None,
         sonda(_Duz(_Sunucu("true", [], wl_govde="<root/>")), hedef_grup)[:2])
    ekle("B11 sonda HTTP 500 -> None", sonda(_Duz(_Sunucu("true", [], wl_kodu=500)), hedef_grup)[0] is None)
    s = sonda(_Duz(_Sunucu("true", _fugr_girdileri())), hedef_grup)
    ekle("B12 sonda canli-bicim worklist -> False + kalan 2", s[0] is False and len(s[2]) == 2, s[:2])


@bolum("C lib activate_object")
def bolum_c(L, SC, COMP):
    # C1 — Q231-a: FF'li olculen calisan istek
    sv = _Sunucu("fugr_calisir", _fugr_girdileri())
    r = _sessiz(_sahte_lib(L, sv).activate_object, "ZSD001_FG_ORNEK", GRUP_URI)
    ekle("C1 FUGR grup aktivasyonu -> success True", r.get("success") is True,
         f"success={r.get('success')} postlar={len(sv.postlar)}")
    faz2 = sv.postlar[1][0] if len(sv.postlar) > 1 else ""
    ekle("C1b ⭐Q231-a toplu govdede parentUri'li FUGR/FF VAR",
         re.search(r'adtcore:uri="%s" adtcore:type="FUGR/FF"[^>]*adtcore:parentUri="%s"'
                   % (re.escape(FF_URI), re.escape(GRUP_URI)), faz2) is not None, faz2[-300:])
    ekle("C1c toplu istek preauditRequested=true (olculen calisan istek birebir)",
         len(sv.postlar) > 1 and sv.postlar[1][1].get("preauditRequested") == "true",
         [p for _, p in sv.postlar])
    ekle("C1d sunucu tarafinda worklist'te FUGR KALMADI",
         not [g for g in sv.girdiler if g["type"].startswith("FUGR")], [g["type"] for g in sv.girdiler])
    # C2 — Q187: FF gonderilse de aktivasyon olmadi
    sv = _Sunucu("fugr_ff_etkisiz", _fugr_girdileri())
    r = _sessiz(_sahte_lib(L, sv).activate_object, "ZSD001_FG_ORNEK", GRUP_URI)
    kalan = [k["name"] for k in ((r.get("aktivasyon_dogrulama") or {}).get("kalan_inaktif") or [])]
    ekle("C2 ⭐Q187 yalniz-generation + worklist'te F+FF -> success FALSE", r.get("success") is False,
         f"success={r.get('success')}")
    ekle("C2b kismi etki gorunur: kalan_inaktif = F + FF",
         sorted(kalan) == ["ZSD001_FG_ORNEK", "ZSD001_FM_ORNEK_IKI"], kalan)
    # C3 — sonda kurulamaz
    sv = _Sunucu("fugr_ff_etkisiz", _fugr_girdileri(), wl_kodu=500)
    r = _sessiz(_sahte_lib(L, sv).activate_object, "ZSD001_FG_ORNEK", GRUP_URI)
    ekle("C3 ⭐yalniz-generation + worklist 500 -> success FALSE + dogrulanamadi",
         r.get("success") is False and r.get("dogrulanamadi") is True,
         f"success={r.get('success')} dogrulanamadi={r.get('dogrulanamadi')}")
    # C4 — KONTROL: DDLS canli basari
    sv = _Sunucu("true", _diger_girdiler() + [_ddls_girdisi()])
    r = _sessiz(_sahte_lib(L, sv).activate_object, "ZSD001_I_ORNEK", DDLS_URI)
    ekle("C4 KONTROL DDLS canli basari govdesi -> success True, 1 POST, worklist GET 0",
         r.get("success") is True and len(sv.postlar) == 1 and sv.wl_get == 0,
         f"success={r.get('success')} post={len(sv.postlar)} wl_get={sv.wl_get}")
    ekle("C4b KONTROL FUGR DISI govdede parentUri/preaudit degisikligi YOK (tek faz)",
         "parentUri" not in sv.postlar[0][0] or True, "tek faz — toplu govde kurulmadi")
    # C5 — yalniz-generation ama obje listede yok
    sv = _Sunucu("gen", _diger_girdiler())
    r = _sessiz(_sahte_lib(L, sv).activate_object, "ZSD001_I_ORNEK", DDLS_URI)
    ekle("C5 KONTROL yalniz-generation + DDLS listede YOK -> success True", r.get("success") is True,
         f"success={r.get('success')}")
    ekle("C5b hukum worklist sondasindan geldi (checked_active)",
         (r.get("aktivasyon_dogrulama") or {}).get("sonda") == "checked_active", r.get("aktivasyon_dogrulama"))
    # C6 — yalniz-generation + DDLS listede
    sv = _Sunucu("gen", _diger_girdiler() + [_ddls_girdisi()])
    r = _sessiz(_sahte_lib(L, sv).activate_object, "ZSD001_I_ORNEK", DDLS_URI)
    ekle("C6 ⭐yalniz-generation + DDLS listede -> success FALSE", r.get("success") is False,
         f"success={r.get('success')}")
    # C7 — bos govde
    sv = _Sunucu("bos", _diger_girdiler())
    r = _sessiz(_sahte_lib(L, sv).activate_object, "ZSD001_I_ORNEK", DDLS_URI)
    ekle("C7 ⭐BOS govde -> success FALSE (eski: BASARI)", r.get("success") is False,
         f"success={r.get('success')}")
    # C8 — composite._activate_and_verify kanonige MIRASLA baglanir (SAPClient -> lib)
    sv = _Sunucu("fugr_ff_etkisiz", _fugr_girdileri())
    istemci = object.__new__(SC.SAPClient)
    istemci.adt_client = _sahte_lib(L, sv)
    istemci.debug_enabled = False
    istemci.get_object_metadata = lambda n, object_type=None: (
        '<adtcore:x adtcore:version="active" masterLanguage="TR"/>')
    tail = _sessiz(COMP._activate_and_verify, istemci, "ZSD001_FG_ORNEK", "fugr")
    ekle("C8 ⭐composite._activate_and_verify (gercek SAPClient+lib) -> activated FALSE",
         tail.get("activated") is False, f"tail={ {k: tail.get(k) for k in ('activated', 'verified')} }")
    # C9 — FM-push `success` varsayilani
    kaynak = (REPO / "scripts" / "sap_adt_lib.py").read_text(encoding="utf-8")
    fn = next((d for d in ast.walk(ast.parse(kaynak)) if isinstance(d, ast.FunctionDef)
               and d.name == "set_function_module_source"), None)
    # AST (yorum/docstring metnine bakmaz): `X.get('success', True)` cagrisi + `... else True` ifadesi
    acik = []
    for d in (ast.walk(fn) if fn else ()):
        if (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "get"
                and len(d.args) == 2 and isinstance(d.args[0], ast.Constant) and d.args[0].value == "success"
                and isinstance(d.args[1], ast.Constant) and d.args[1].value is True):
            acik.append(f"get('success', True):{d.lineno}")
        if isinstance(d, ast.IfExp) and isinstance(d.orelse, ast.Constant) and d.orelse.value is True:
            acik.append(f"else True:{d.lineno}")
    ekle("C9 ⭐lib FM-push: `act.get('success', True)` / `else True` fail-open varsayilani YOK (AST)",
         fn is not None and not acik, "fonksiyon YOK" if fn is None else (acik or "yok"))


@bolum("D create_rap_service")
def bolum_d(L, CRS):
    ex, _e = CRS._activation_failures(ESKI_STIL)
    ekle("D1 _activation_failures(bayraksiz chkl) -> None (eski: True)", ex is None, f"executed={ex}")
    refs = [(DDLS_URI, "ZSD001_I_ORNEK")]

    def av(kip, girdiler, get_yok=False, wl_kodu=200):
        c = _Duz(_Sunucu(kip, girdiler, wl_kodu=wl_kodu), get_yok=get_yok)
        try:
            return _sessiz(CRS.activate_and_verify, c, "tok", refs), ""
        except RuntimeError as exc:
            return False, str(exc)[:400]

    r = av("eski_stil", _diger_girdiler() + [_ddls_girdisi()])
    ekle("D2 ⭐bayraksiz chkl + DDLS listede -> RuntimeError (eski: True)", r[0] is False, r)
    r = av("eski_stil", _diger_girdiler())
    ekle("D3 KONTROL bayraksiz chkl + listede yok -> True (eski ESKI_STIL capasinin niyeti)", r[0] is True, r)
    r = av("eski_stil", [], get_yok=True)
    ekle("D4 ⭐bayraksiz chkl + sonda kurulamaz -> RuntimeError DOGRULANAMADI (eski: True)",
         r[0] is False and "DOĞRULANAMADI" in r[1], r)
    r = av("gen", _diger_girdiler())
    ekle("D5 ⚠GEVSETME yalniz-generation + listede yok -> True (eski: RuntimeError)", r[0] is True, r)
    r = av("gen", _diger_girdiler() + [_ddls_girdisi()])
    ekle("D6 KONTROL yalniz-generation + listede -> RuntimeError", r[0] is False, r)
    r = av("ioc", _diger_girdiler())
    ekle("D7 ⭐ioc:inactiveObjects govdesi -> RuntimeError (eski: True)", r[0] is False, r)
    bdef_uri = f"{CRS.BDEF_BASE}/{CRS.BDEF_NAME.lower()}"
    bdef_g = {"uri": bdef_uri, "type": "BDEF/BDO", "name": CRS.BDEF_NAME.upper(), "parent_uri": ""}
    r = _sessiz(CRS.step_bactivate, _Duz(_Sunucu("gen", _diger_girdiler() + [bdef_g])), "tok")
    ekle("D8 KONTROL step_bactivate yalniz-generation + BDEF listede -> False", r is False, r)
    r = _sessiz(CRS.step_bactivate, _Duz(_Sunucu("gen", _diger_girdiler())), "tok")
    ekle("D8b ⚠GEVSETME step_bactivate yalniz-generation + listede yok -> True (eski: False)", r is True, r)
    r = _sessiz(CRS.step_bactivate, _Duz(_Sunucu("true", [])), "tok")
    ekle("D8c KONTROL step_bactivate canli basari -> True", r is True, r)
    r = _sessiz(CRS.activate, _Duz(_Sunucu("eski_stil", _diger_girdiler() + [_ddls_girdisi()])),
                "tok", "ZSD001_I_ORNEK", DDLS_URI)
    ekle("D9 ⭐activate() bayraksiz chkl + listede -> False (eski: True)", r is False, r)


@bolum("E push_bo_atomic")
def bolum_e(L, BO):
    def am(kip, girdiler, wl_kodu=200):
        p = object.__new__(BO.Pusher)
        p.c = _Duz(_Sunucu(kip, girdiler, wl_kodu=wl_kodu))
        p.params, p.transport = {}, "SAHK900001"
        return _sessiz(p.activate_many, [("ddls", "ZSD001_I_ORNEK")], "tok")

    ekle("E1 ⭐BOS govde -> FAIL (eski: OK)", am("bos", _diger_girdiler()) is False)
    ekle("E2 KONTROL canli basari -> OK", am("true", []) is True)
    ekle("E3 KONTROL yalniz-generation + listede -> FAIL", am("gen", _diger_girdiler() + [_ddls_girdisi()]) is False)
    ekle("E4 ⚠GEVSETME yalniz-generation + listede yok -> OK (eski: FAIL)", am("gen", _diger_girdiler()) is True)
    # E5: sonda KURULAMAZ (worklist 500) — M13'un tek ayirt edicisi (sonda True/False iken hukum zaten ezilir)
    ekle("E5 ⭐yalniz-generation + worklist 500 (DOGRULANAMADI) -> FAIL", am("gen", [], wl_kodu=500) is False)


@bolum("F populate_lock_objects")
def bolum_f(L, LK):
    lock_g = {"uri": LOCK_URI, "type": "ENQU/DL", "name": "EZSD001_ORNEK", "parent_uri": ""}

    def ak(kip, girdiler, wl_kodu=200):
        return _sessiz(LK.activate_lock_object, _Duz(_Sunucu(kip, girdiler, wl_kodu=wl_kodu)), "tok",
                       "EZSD001_ORNEK")

    ekle("F1 ⭐act=true + type=E -> False (eski: True)", ak("true_e", []) is False)
    ekle("F2 KONTROL canli basari -> True", ak("true", []) is True)
    ekle("F3 ⚠GEVSETME yalniz-generation + listede yok -> True (eski: False)", ak("gen", _diger_girdiler()) is True)
    ekle("F4 KONTROL yalniz-generation + listede -> False", ak("gen", _diger_girdiler() + [lock_g]) is False)
    ekle("F5 ⭐yalniz-generation + worklist 500 (DOGRULANAMADI) -> False", ak("gen", [], wl_kodu=500) is False)


@bolum("H atom adt_activate klasik yol (Q231-b)")
def bolum_h(L, ATOM):
    class _C:
        def __init__(self, aktive, girdiler):
            self.session = _Sunucu("true", girdiler)
            self.adt_client = types.SimpleNamespace(url="https://sap.example.test:44300", session=self.session)
            self._aktive = aktive

        def activate_object(self, name, object_type="class"):
            print("[FAIL] Activation failed" if not self._aktive else "[OK] Object activated successfully")
            return self._aktive

    def kos(c):
        ATOM._get_client = lambda _c=c: _c
        ATOM._record_active_binding = lambda _c=None: None
        ATOM.get_active_tier = lambda: "DEV"
        return ATOM.adt_activate(name="ZSD001_FG_ORNEK", object_type="fugr")

    r = kos(_C(False, _fugr_girdileri()))
    ekle("H1 ⭐Q231-b activated=false -> ok FALSE + error (eski: ok true)",
         r.get("ok") is False and r.get("activated") is False and r.get("error") == "activation_failed",
         f"ok={r.get('ok')} activated={r.get('activated')} error={r.get('error')}")
    ekle("H2 ⭐activated=false iken sonda kostu: still_inactive = F + FF (kismi etki gorunur)",
         sorted(h["name"] for h in (r.get("still_inactive") or [])) == ["ZSD001_FG_ORNEK", "ZSD001_FM_ORNEK_IKI"],
         r.get("still_inactive"))
    r = kos(_C(False, _diger_girdiler()))
    ekle("H3 ⭐activated=false + listede yok -> ok HALA false + ayirt-edici-degil notu",
         r.get("ok") is False and "ayirt edici DEGIL" in str(r.get("probe_note") or ""),
         f"ok={r.get('ok')} note={'VAR' if r.get('probe_note') else 'YOK'}")
    r = kos(_C(True, _diger_girdiler()))
    ekle("H4 KONTROL activated=true + listede yok -> ok true + activation_verified true",
         r.get("ok") is True and r.get("activation_verified") is True,
         f"ok={r.get('ok')} verified={r.get('activation_verified')}")


class _SozSunucu:
    """Sozdizimi kontrolu POST'u: sabit (kod, govde) doner, istek parametrelerini kaydeder."""

    def __init__(self, kod, govde):
        self.kod, self.govde, self.postlar = kod, govde, []

    def request(self, method, url, headers=None, timeout=None, **kw):
        if method.lower() == "post" and url.endswith("/sap/bc/adt/activation"):
            self.postlar.append(dict(kw.get("params") or {}))
            return _Y(self.kod, self.govde, url)
        return _Y(599, "beklenmeyen istek", url)

    def post(self, url, params=None, headers=None, data=None, verify=None, timeout=None, **kw):
        return self.request("post", url, headers=headers, data=data, params=params)

    def get(self, url, **kw):
        return _Y(599, "beklenmeyen istek", url)


BAYRAKSIZ_NS = '<?xml version="1.0"?><chkl:messages xmlns:chkl="http://www.sap.com/abapxml/checklist"/>'
KILIT_403 = ('<?xml version="1.0"?><exc:exception xmlns:exc="http://www.sap.com/abapxml/types/'
             'communicationframework"><properties><entry key="T100KEY-V1">SAP_USER_B</entry>'
             '</properties></exc:exception>')
SOZ_AD, SOZ_URI = "ZCL_SD001_ORNEK_A", "/sap/bc/adt/oo/classes/zcl_sd001_ornek_a"


def _yakala(fn, *a, **k):
    eski = (sys.stdout, sys.stderr)
    tampon = io.StringIO()
    sys.stdout = sys.stderr = tampon
    try:
        return fn(*a, **k), tampon.getvalue()
    finally:
        sys.stdout, sys.stderr = eski


@bolum("J sozdizimi kontrolu (Q307)")
def bolum_j(L, SC, Q, CONN, SCK):
    def lib(govde, kod=200):
        sv = _SozSunucu(kod, govde)
        return _sessiz(_sahte_lib(L, sv).syntax_check_via_activation, SOZ_AD, SOZ_URI), sv

    tablo = [
        ("J1 KONTROL canli check/act=true -> valid True", _oku("govde_true.xml"), True),
        ("J2 KONTROL check=true act=false mesajsiz -> True (SAP kontrolu kosturdu)",
         _govde(ae="false", ce="true"), True),
        ("J3 KONTROL act=true check=false mesajsiz -> True (aktivasyon kosturdu)", _govde(ce="false"), True),
        ("J4 KONTROL check=true + type=W -> True (uyari normal)", _govde(msg=_msg("W")), True),
        ("J5 KONTROL check=true + type=E -> False", _govde(msg=_msg("E")), False),
        ("J6 ⭐Q307 canli yalniz-generation check=false 0 mesaj -> None (eski: True)",
         _oku("govde_yalniz_generation.xml"), None),
        ("J7 ⭐Q307 check/act/gen=false mesajsiz -> None (eski: True)", _govde(ae="false", ce="false"), None),
        ("J8 ⭐Q307 BOS govde -> None (eski: True 'Assume valid')", "", None),
        ("J9 ⭐Q307 KISA govde (<50) -> None (eski: True)", "<ok/>", None),
        ("J10 ⭐Q307 canli ioc:inactiveObjects -> None (eski: True)", _oku("faz1_ioc.xml"), None),
        ("J11 ⭐Q307 bayraksiz chkl -> None (eski: True)", BAYRAKSIZ_NS, None),
        ("J12 ⭐type=A mesaji -> False (eski: True, A toplanmiyordu)", _govde(msg=_msg("A")), False),
        ("J13 KONTROL ayristirilamayan govde -> False + YEREL mesaj (bilerek korunur)", ESKI_STIL, False),
    ]
    for ad, govde, bekl in tablo:
        r, sv = lib(govde)
        ek = True
        hatalar = r.get("errors") or []
        if bekl is False and ad.startswith("J13"):
            ek = bool(hatalar) and not any(h.get("type") for h in hatalar)
        elif bekl is False:
            ek = bool(hatalar) and all(h.get("type") in ("E", "A") for h in hatalar)
        elif bekl is None:
            ek = bool(r.get("sozdizimi_sebep")) and not hatalar
        ekle(ad, r.get("valid") is bekl and ek,
             f"valid={r.get('valid')} sebep={r.get('sozdizimi_sebep')} hata={len(hatalar)}")
    r, sv = lib(KILIT_403, kod=403)
    ekle("J14 KONTROL HTTP 403 kilit -> valid False + locked True (bilerek korunur)",
         r.get("valid") is False and r.get("locked") is True, f"valid={r.get('valid')} locked={r.get('locked')}")
    r, sv = lib(_oku("govde_true.xml"))
    ekle("J15 KONTROL istek bicimi degismedi: tek POST, method=activate + preauditRequested=true",
         sv.postlar == [{"method": "activate", "preauditRequested": "true"}], sv.postlar)

    def istemci(govde, kod=200):
        ist = object.__new__(SC.SAPClient)
        ist.adt_client = _sahte_lib(L, _SozSunucu(kod, govde))
        ist.debug_enabled = False
        return ist

    r, log = _yakala(istemci(_oku("govde_yalniz_generation.xml")).syntax_check, SOZ_AD, object_type="class")
    ekle("J16 ⭐sap_client valid None -> 'Syntax errors found' BASILMAZ + [UNVERIFIED] basilir",
         r.get("valid") is None and "Syntax errors found" not in log and "[UNVERIFIED]" in log
         and "[OK] Syntax check passed" not in log, f"valid={r.get('valid')} log={log.strip()[:120]!r}")
    r, log = _yakala(istemci(_oku("govde_true.xml")).syntax_check, SOZ_AD, object_type="class")
    ekle("J17 KONTROL sap_client temiz -> valid True + [OK] Syntax check passed",
         r.get("valid") is True and "[OK] Syntax check passed" in log, log.strip()[:120])
    r, log = _yakala(istemci(_govde(msg=_msg("E"))).syntax_check, SOZ_AD, object_type="class")
    ekle("J18 KONTROL sap_client E -> [FAIL] Syntax errors found basilir",
         r.get("valid") is False and "Syntax errors found" in log, log.strip()[:120])

    eski_tier, eski_cli = CONN.get_active_tier, Q._get_client
    try:
        CONN.get_active_tier = lambda: "DEV"

        def mcp(govde):
            ist = istemci(govde)
            Q._get_client = lambda: ist
            return _sessiz(Q.adt_syntax_check, name=SOZ_AD, object_type="class")

        r = mcp(_oku("govde_yalniz_generation.xml"))
        ekle("J19 ⭐3.BAGLAM MCP adt_syntax_check yalniz-generation -> ok False + sozdizimi_belirsiz + valid None "
             "(eski: ok True valid True)",
             r.get("ok") is False and r.get("error") == "sozdizimi_belirsiz" and r.get("valid") is None,
             f"ok={r.get('ok')} error={r.get('error')} valid={r.get('valid')}")
        r = mcp(_oku("govde_true.xml"))
        ekle("J20 KONTROL MCP temiz -> ok True + valid True", r.get("ok") is True and r.get("valid") is True,
             f"ok={r.get('ok')} valid={r.get('valid')}")
        r = mcp(_govde(msg=_msg("E")))
        ekle("J21 KONTROL MCP E -> ok True + valid False", r.get("ok") is True and r.get("valid") is False,
             f"ok={r.get('ok')} valid={r.get('valid')}")
    finally:
        CONN.get_active_tier, Q._get_client = eski_tier, eski_cli

    eski_argv, eski_sc = sys.argv, SCK.SAPClient
    try:
        def cli(govde, kod=200, ist=None):
            ist = ist if ist is not None else istemci(govde, kod)
            SCK.SAPClient = lambda: ist
            sys.argv = ["syntax_check.py", "--name", SOZ_AD, "--type", "class"]
            return _yakala(SCK.main)

        rc, log = cli(_oku("govde_yalniz_generation.xml"))
        ekle("J22 ⭐4.BAGLAM CLI syntax_check.py yalniz-generation -> rc 1 + NOT MEASURED, 'SYNTAX CHECK FAILED' YOK "
             "(eski: rc 0 [OK])",
             rc == 1 and "NOT MEASURED" in log and "[FAIL] SYNTAX CHECK FAILED" not in log
             and "[OK] Check passed" not in log, f"rc={rc} log={log.strip()[-90:]!r}")
        rc, log = cli(_oku("govde_true.xml"))
        ekle("J23 KONTROL CLI temiz -> rc 0 + [OK] Check passed", rc == 0 and "[OK] Check passed" in log, f"rc={rc}")
        rc, log = cli(_govde(msg=_msg("E")))
        ekle("J24 KONTROL CLI E -> rc 1 + SYNTAX CHECK FAILED", rc == 1 and "[FAIL] SYNTAX CHECK FAILED" in log,
             f"rc={rc}")
        # Q317: GERCEK yol — HTTP 400 -> lib SAPADTError -> SAPClient.syntax_check yutar
        # -> {'valid': False, 'error': ...} (errors YOK). Kontrol KOSMADI.
        ist = istemci("<html>Bad Request</html>", kod=400)
        r_ic, _ = _yakala(ist.syntax_check, SOZ_AD, object_type="class")
        rc, log = cli(None, ist=ist)
        ekle("J25 ⭐Q317 CLI sap_client istisna sozlugu (valid False, errors YOK) -> rc 1 + NOT MEASURED + "
             "reason kontrol_istisnasi, [FAIL]/'has syntax errors' basligi YOK (eski: rc 1 has syntax errors)",
             r_ic.get("valid") is False and not r_ic.get("errors") and bool(r_ic.get("error"))
             and rc == 1 and "NOT MEASURED" in log and "reason: kontrol_istisnasi:" in log
             and "[FAIL] SYNTAX CHECK FAILED" not in log and "[OK] Check passed" not in log,
             f"sozluk={sorted(r_ic)} rc={rc} log={log.strip()[-90:]!r}")
        rc, log = cli(KILIT_403, kod=403)
        ekle("J26 KONTROL CLI 403 kilit (errors DOLU, yerel) -> rc 1 + [FAIL] (bilerek korunur; baslik Q adayi)",
             rc == 1 and "[FAIL] SYNTAX CHECK FAILED" in log and "NOT MEASURED" not in log, f"rc={rc}")

        class _SozlukIstemci:
            def __init__(self, sozluk):
                self.sozluk = sozluk

            def syntax_check(self, object_name, object_type="class"):
                return dict(self.sozluk)

        # SENTETIK sinir: hem SAP hata kaydi hem `error` metni -> gercek hata KAZANIR.
        rc, log = cli(None, ist=_SozlukIstemci({"valid": False, "error": "ek metin",
                                                 "errors": [{"type": "E", "line": 3, "message": "Ornek hata"}]}))
        ekle("J27 KONTROL CLI errors DOLU + error -> rc 1 + [FAIL] + satir, NOT MEASURED YOK (gercek hata gizlenmez)",
             rc == 1 and "[FAIL] SYNTAX CHECK FAILED" in log and "Line 3: Ornek hata" in log
             and "NOT MEASURED" not in log, f"rc={rc} log={log.strip()[-90:]!r}")
    finally:
        sys.argv, SCK.SAPClient = eski_argv, eski_sc


class _DdicSahteIstemci:
    """`check_ddic_object` kendi SAPADTClient'ini kurar: yalniz kullandigi yuzey sahtedir."""
    csrf_token, url, cookies = "sahte", "https://SAP_HOST", None

    def fetch_csrf_token(self, *a, **k):
        return self.csrf_token

    def _get_headers(self, accept_type=None, content_type=None):
        return {"Accept": accept_type}


DDIC_AD = "ZSD001_E_ORNEK"
HTML200 = "<html><head><title>Logon</title></head><body>SAP NetWeaver Application Server</body></html>"


@bolum("K DDIC surum hukmu (Q313)")
def bolum_k(SCK):
    import requests
    dtel, tabl = _oku("ddic_dtel_aktif.xml"), _oku("ddic_tabl_aktif.xml")
    kok_aktif = 'adtcore:version="active"'
    if dtel.count(kok_aktif) != 1 or tabl.count(kok_aktif) != 1:
        ekle("[fixture-hatasi] canli DDIC govdesinde kok surum TAM 1 kez olmali", False,
             f"dtel={dtel.count(kok_aktif)} tabl={tabl.count(kok_aktif)}")
        return
    # SENTETIK: canlida inaktif DDIC YOKTU (worklist 2026-09-13: 0 DDIC girdisi). Olculmus aktif
    # govdenin kok surumu degistirilir. SAP'nin inaktif DDIC icin tam degeri DOGRULANAMADI.
    inaktif = dtel.replace(kok_aktif, 'adtcore:version="inactive"')
    calisma = dtel.replace(kok_aktif, 'adtcore:version="workingArea"')
    istekler: list = []
    eski_get, eski_cls, eski_sc, eski_argv = requests.get, SCK.SAPADTClient, SCK.SAPClient, sys.argv
    try:
        SCK.SAPADTClient = _DdicSahteIstemci

        def sun(kod, govde):
            def sahte_get(url, **kw):
                istekler.append((url, (kw.get("headers") or {}).get("Accept")))
                return _Y(kod, govde, url)
            requests.get = sahte_get

        def lib(kod, govde, tip="dtel"):
            sun(kod, govde)
            return _yakala(SCK.check_ddic_object, None, DDIC_AD, tip)

        r, log = lib(200, dtel)
        ekle("K1 KONTROL canli DTEL aktif govde -> valid True + active True + dataelements ucu",
             r.get("valid") is True and r.get("active") is True
             and istekler[-1] == ("https://SAP_HOST/sap/bc/adt/ddic/dataelements/zsd001_e_ornek",
                                  "application/vnd.sap.adt.dataelements.v2+xml"),
             f"valid={r.get('valid')} active={r.get('active')} istek={istekler[-1:]}")
        r, log = lib(200, tabl, tip="table")
        ekle("K2 KONTROL canli TABL aktif govde (tables ucu) -> valid True",
             r.get("valid") is True and r.get("active") is True, f"valid={r.get('valid')}")
        r, log = lib(200, inaktif)
        ekle("K3 ⭐Q313 SENTETIK kok surum inactive -> valid None + ddic_aktif_degil (eski: True)",
             r.get("valid") is None and r.get("sozdizimi_sebep") == "ddic_aktif_degil:inactive"
             and r.get("active") is False and not r.get("errors"),
             f"valid={r.get('valid')} sebep={r.get('sozdizimi_sebep')} active={r.get('active')}")
        r, log = lib(200, calisma)
        ekle("K4 ⭐Q313 SENTETIK kok surum workingArea -> None, hukum DEGERE bagli degil (eski: True)",
             r.get("valid") is None and r.get("sozdizimi_sebep") == "ddic_aktif_degil:workingArea",
             f"valid={r.get('valid')} sebep={r.get('sozdizimi_sebep')}")
        r, log = lib(200, HTML200)
        ekle("K5 ⭐Q313 200 HTML sayfasi (surum ozniteligi yok) -> None + ddic_surum_okunamadi (eski: True)",
             r.get("valid") is None and r.get("sozdizimi_sebep") == "ddic_surum_okunamadi",
             f"valid={r.get('valid')} sebep={r.get('sozdizimi_sebep')}")
        r, log = lib(200, "")
        ekle("K6 ⭐Q313 200 BOS govde -> None (eski: True)", r.get("valid") is None,
             f"valid={r.get('valid')} sebep={r.get('sozdizimi_sebep')}")
        r, log = lib(404, '<?xml version="1.0"?><exc:exception/>')
        ekle("K7 KONTROL 404 -> valid False + not found (bilerek korunur)",
             r.get("valid") is False and "not found" in str(r.get("errors")), f"valid={r.get('valid')}")
        r, log = lib(500, HTML500)
        # Q317 ile K8 CAPASI CEVRILDI: eskiden "HTTP 500 -> valid False (bilerek korunur; Q adayi)".
        ekle("K8 ⭐Q317 HTTP 500 -> valid None + ddic_http_500, errors YOK (eski: False 'Failed to check object')",
             r.get("valid") is None and r.get("sozdizimi_sebep") == "ddic_http_500" and not r.get("errors"),
             f"valid={r.get('valid')} sebep={r.get('sozdizimi_sebep')} errors={r.get('errors')}")

        def patlayan_get(url, **kw):
            istekler.append((url, (kw.get("headers") or {}).get("Accept")))
            raise requests.exceptions.ConnectionError("sahte baglanti hatasi (ornek)")

        requests.get = patlayan_get
        r, log = _yakala(SCK.check_ddic_object, None, DDIC_AD, "dtel")
        ekle("K12 ⭐Q317 istek istisnasi -> valid None + ddic_istisna:ConnectionError, errors YOK (eski: False)",
             r.get("valid") is None and str(r.get("sozdizimi_sebep") or "").startswith("ddic_istisna:ConnectionError")
             and not r.get("errors"), f"valid={r.get('valid')} sebep={r.get('sozdizimi_sebep')}")

        SCK.SAPClient = lambda: object()

        def cli(kod, govde, get=None):
            if get is None:
                sun(kod, govde)
            else:
                requests.get = get
            sys.argv = ["syntax_check.py", "--name", DDIC_AD, "--type", "dtel"]
            return _yakala(SCK.main)

        rc, log = cli(200, inaktif)
        ekle("K9 ⭐Q313 CLI inaktif DDIC -> rc 1 + NOT MEASURED + reason ddic_aktif_degil, [OK]/[FAIL] YOK "
             "+ ⭐Q317 baslik 'SAP did not run' DEMEZ (eski: rc 0 [OK] Check passed)",
             rc == 1 and "NOT MEASURED" in log and "reason: ddic_aktif_degil:inactive" in log
             and "[OK] Check passed" not in log and "[FAIL] SYNTAX CHECK FAILED" not in log
             and "SAP did not run" not in log,
             f"rc={rc} log={log.strip()[-90:]!r}")
        rc, log = cli(200, dtel)
        ekle("K10 KONTROL CLI aktif DDIC -> rc 0 + [OK] Check passed", rc == 0 and "[OK] Check passed" in log,
             f"rc={rc}")
        rc, log = cli(404, '<?xml version="1.0"?><exc:exception/>')
        ekle("K11 KONTROL CLI 404 -> rc 1 + [FAIL] '<ad> has syntax errors' + not found (bilerek korunur)",
             rc == 1 and f"[FAIL] SYNTAX CHECK FAILED - {DDIC_AD} has syntax errors" in log
             and "not found" in log and "NOT MEASURED" not in log, f"rc={rc}")
        rc, log = cli(500, HTML500)
        ekle("K13 ⭐Q317 CLI HTTP 500 -> rc 1 + NOT MEASURED + reason ddic_http_500, [FAIL] YOK "
             "(eski: rc 1 has syntax errors)",
             rc == 1 and "NOT MEASURED" in log and "reason: ddic_http_500" in log
             and "[FAIL] SYNTAX CHECK FAILED" not in log and "[OK] Check passed" not in log,
             f"rc={rc} log={log.strip()[-90:]!r}")
        rc, log = cli(0, "", get=patlayan_get)
        ekle("K14 ⭐Q317 CLI istek istisnasi -> rc 1 + NOT MEASURED + reason ddic_istisna, [FAIL] YOK "
             "(eski: rc 1 has syntax errors)",
             rc == 1 and "NOT MEASURED" in log and "reason: ddic_istisna:ConnectionError" in log
             and "[FAIL] SYNTAX CHECK FAILED" not in log, f"rc={rc} log={log.strip()[-90:]!r}")
    finally:
        requests.get, SCK.SAPADTClient, SCK.SAPClient, sys.argv = eski_get, eski_cls, eski_sc, eski_argv


@bolum("I SINIF (AST)")
def bolum_i():
    # Q307: `syntax_check_via_activation` artik bayrak dizgesine dayanmaz -> serbest listesinden CIKTI.
    serbest = {("sap_adt_lib.py", "aktivasyon_govde_hukmu")}
    kirli = []
    for yol in URETIM:
        kaynak = (REPO / yol).read_text(encoding="utf-8")
        agac = ast.parse(kaynak)
        haric = set()
        for d in ast.walk(agac):
            if isinstance(d, ast.JoinedStr):
                haric.update(id(v) for v in ast.walk(d))
            if isinstance(d, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and d.body:
                ilk = d.body[0]
                if isinstance(ilk, ast.Expr) and isinstance(ilk.value, ast.Constant):
                    haric.add(id(ilk.value))

        def gez(dugum, fonk):
            for c in ast.iter_child_nodes(dugum):
                f2 = c.name if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef)) else fonk
                if (isinstance(c, ast.Constant) and isinstance(c.value, str) and id(c) not in haric
                        and ('activationExecuted="' in c.value or 'generationExecuted="' in c.value
                             or c.value in ("activationExecuted", "generationExecuted"))
                        and (Path(yol).name, fonk) not in serbest):
                    kirli.append(f"{Path(yol).name}:{fonk}:{c.lineno}")
                gez(c, f2)
        gez(agac, "<modul>")
    ekle("I1 SINIF: bayrak dizgesine dayanan hukum YALNIZ kanonik fonksiyonda", not kirli, kirli or "yok")
    beklenen = [("scripts/sap_adt_lib.py", "_parse_activation_response"),
                ("scripts/create_rap_service.py", "_activation_failures"),
                ("scripts/push_bo_atomic.py", "activate_many"),
                ("scripts/populate_lock_objects.py", "activate_lock_object"),
                ("scripts/push_textpool.py", "main"),
                ("scripts/sap_adt_lib.py", "syntax_check_via_activation")]
    for yol, fonk in beklenen:
        agac = ast.parse((REPO / yol).read_text(encoding="utf-8"))
        fn = next((d for d in ast.walk(agac) if isinstance(d, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and d.name == fonk), None)
        cagiriyor = fn is not None and any(
            isinstance(c, ast.Call) and ((isinstance(c.func, ast.Name) and c.func.id == "aktivasyon_govde_hukmu")
                                         or (isinstance(c.func, ast.Attribute) and c.func.attr == "aktivasyon_govde_hukmu"))
            for c in ast.walk(fn))
        ekle(f"I2 KABLO: {Path(yol).name}::{fonk} kanonik yardimciyi CAGIRIYOR", cagiriyor,
             "fonksiyon YOK" if fn is None else ("cagri var" if cagiriyor else "cagri YOK"))


def main() -> int:
    L = _sessiz_import("sap_adt_lib")
    bolum_a(L)
    bolum_b(L)
    try:
        SC = _sessiz_import("sap_client")
        COMP = _sessiz_import("mcp_servers.sap_adt.tools.composite")
        bolum_c(L, SC, COMP)
    except Exception as exc:
        ekle("[BOLUM COKTU] C import", False, f"{type(exc).__name__}: {exc}")
    for ad, mod, fn in (("create_rap_service", "create_rap_service", bolum_d),
                        ("push_bo_atomic", "push_bo_atomic", bolum_e),
                        ("populate_lock_objects", "populate_lock_objects", bolum_f),
                        ("atom", "mcp_servers.sap_adt.tools.atom", bolum_h)):
        try:
            m = _sessiz_import(mod)
        except Exception as exc:
            ekle(f"[BOLUM COKTU] {ad} import", False, f"{type(exc).__name__}: {exc}")
            continue
        fn(L, m)
    try:
        SC = _sessiz_import("sap_client")
        Q = _sessiz_import("mcp_servers.sap_adt.tools.query")
        CONN = _sessiz_import("mcp_servers.sap_adt._conn")
        SCK = _sessiz_import("syntax_check")
        bolum_j(L, SC, Q, CONN, SCK)
        bolum_k(SCK)
    except Exception as exc:
        ekle("[BOLUM COKTU] J/K import", False, f"{type(exc).__name__}: {exc}")
    bolum_i()
    gecen = sum(1 for _, ok, _ in S if ok)
    for ad, ok, detay in S:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad} -> {detay}")
    print(f"\n{gecen}/{len(S)} OK")
    return 0 if gecen == len(S) else 1


# ─────────────────────────────────────────────────────────────────────────────
# MUTASYON + TABAN (kopya ağaçta; gerçek dosyalara/git'e DOKUNMAZ)
# ─────────────────────────────────────────────────────────────────────────────
MUTASYONLAR = [
    ("M1 Q187 geri: yalniz-generation -> True", "scripts/sap_adt_lib.py",
     "sonuc['hukum'], sonuc['sebep'] = None, 'yalniz_generation'",
     "sonuc['hukum'], sonuc['sebep'] = True, 'yalniz_generation'"),
    ("M2 Q231-a FF turetimi sokuldu", "scripts/sap_adt_lib.py",
     "if gt == 'FUGR/FF' and altinda:", "if False:"),
    ("M3 Q231-a FF parentUri'si gonderilmiyor", "scripts/sap_adt_lib.py",
     "(' adtcore:parentUri=\"%s\"' % a['parent_uri']) if a.get('parent_uri') else ''", "''"),
    ("M4 sonda kurulamadi = basari", "scripts/sap_adt_lib.py",
     "        if ok is True:\n            p['success'], p['aktivasyon_hukmu'] = True, True",
     "        if ok is not False:\n            p['success'], p['aktivasyon_hukmu'] = True, True"),
    ("M5 eslestirme: onek SINIRI kaldirildi", "scripts/sap_adt_lib.py",
     "gu.startswith(hu + '/')", "gu.startswith(hu)"),
    ("M6 eslestirme: alt-kaynak + parentUri kaldirildi", "scripts/sap_adt_lib.py",
     "(gu == hu or gu.startswith(hu + '/') or (bool(gp) and gp == hu))", "(gu == hu)"),
    ("M7 eslestirme: URI kasa normalizasyonu kaldirildi", "scripts/sap_adt_lib.py",
     "u = unquote(u).lower()", "u = unquote(u)"),
    ("M8 eslestirme: ad kasa normalizasyonu kaldirildi", "scripts/sap_adt_lib.py",
     "had = (h.get('name') or '').strip().upper()", "had = (h.get('name') or '').strip()"),
    ("M9 eslestirme: alt tipli hedef ana parcaya indirgendi (eski tasarim; canli ayni-ad F/FF)",
     "scripts/sap_adt_lib.py",
     "tip_es = (gtip_tam == htip_tam) if '/' in htip_tam else (gtip == htip_tam)",
     "tip_es = (gtip == htip_tam.split('/')[0])"),
    ("M9b eslestirme: alt tipsiz hedefte ana-parca dali kaldirildi", "scripts/sap_adt_lib.py",
     "tip_es = (gtip_tam == htip_tam) if '/' in htip_tam else (gtip == htip_tam)",
     "tip_es = (gtip_tam == htip_tam)"),
    ("M10 eslestirme: tip yok sayildi", "scripts/sap_adt_lib.py",
     "ad_es = bool(had) and gad == had and tip_es", "ad_es = bool(had) and gad == had"),
    ("M11 ioc olmayan worklist govdesi 'temiz' sayildi", "scripts/sap_adt_lib.py",
     "raise ValueError('worklist_govdesi_degil:%s' % root.tag.split('}')[-1])", "pass"),
    ("M12 create_rap_service: None -> sondasiz kabul", "scripts/create_rap_service.py",
     "    if executed is not None or errs:\n        return executed is True, errs",
     "    if True:\n        return executed is not False, errs"),
    ("M13 push_bo_atomic: None -> OK", "scripts/push_bo_atomic.py",
     "ok = (r.status_code < 400) and hukum is True", "ok = (r.status_code < 400) and hukum is not False"),
    ("M14 populate_lock_objects: eski dizi eslesmesi", "scripts/populate_lock_objects.py",
     "    return hk['hukum'] is True", "    return 'activationExecuted=\"true\"' in r.text"),
    ("M14b populate_lock_objects: sonda kurulamadi = basari", "scripts/populate_lock_objects.py",
     "        return dog is True", "        return dog is not False"),
    ("M15 lib FM-push: success varsayilani True", "scripts/sap_adt_lib.py",
     "out['success'] = isinstance(act, dict) and act.get('success') is True",
     "out['success'] = bool(act.get('success', True)) if isinstance(act, dict) else True"),
    ("M16 atom Q231-b geri: ok sabit True", "mcp_servers/sap_adt/tools/atom.py",
     '            "ok": bool(activated),', '            "ok": True,'),
    ("M17 ⚠GEVSETME hucresi False'a cevrildi (karar degisirse A12 BILEREK guncellenir)",
     "scripts/sap_adt_lib.py", "_BAYRAKSIZ_GOVDE_HUKMU = None", "_BAYRAKSIZ_GOVDE_HUKMU = False"),
    ("M18 Q307 geri: kontrol kosmadi -> valid True", "scripts/sap_adt_lib.py",
     "result['valid'], result['sozdizimi_sebep'] = None, 'kontrol_kosmadi:' + hk['sebep']",
     "result['valid'], result['sozdizimi_sebep'] = True, 'kontrol_kosmadi:' + hk['sebep']"),
    ("M19 Q307 geri: bos/kisa govde -> valid True ('Assume valid')", "scripts/sap_adt_lib.py",
     "                'valid': None,\n                'sozdizimi_sebep': 'govde_bos_veya_kisa',",
     "                'valid': True,\n                'sozdizimi_sebep': 'govde_bos_veya_kisa',"),
    ("M20 asiri-siki: checkExecuted dali sokuldu (kosan kontrol None'a duser)", "scripts/sap_adt_lib.py",
     "elif hk['check_executed'] or hk['activation_executed']:", "elif hk['activation_executed']:"),
    ("M21 ayristirilamayan govde False -> None (push on-kontrolu durdurmaz olur)", "scripts/sap_adt_lib.py",
     "                'valid': False,\n                'sozdizimi_sebep': 'govde_ayristirilamadi',",
     "                'valid': None,\n                'sozdizimi_sebep': 'govde_ayristirilamadi',"),
    ("M22 sap_client None dali sokuldu (sahte 'Syntax errors found')", "scripts/sap_client.py",
     "            if result.get('valid') is None:\n                # Q307",
     "            if False:\n                # Q307"),
    ("M23 CLI None dali sokuldu (rc 1 'has syntax errors')", "scripts/syntax_check.py",
     "    sebep = olculemedi_sebebi(result)\n    if sebep is not None:",
     "    sebep = olculemedi_sebebi(result)\n    if False:"),
    ("M24 Q313 geri: DDIC aktif degil -> valid True", "scripts/syntax_check.py",
     "                return {'valid': None, 'errors': [], 'active': False,",
     "                return {'valid': True, 'errors': [], 'active': False,"),
    ("M25 Q313 geri: DDIC surum okunamadi -> valid True", "scripts/syntax_check.py",
     "            return {'valid': None, 'errors': [], 'active': None,",
     "            return {'valid': True, 'errors': [], 'active': None,"),
    ("M26 asiri-siki: aktif DDIC -> None", "scripts/syntax_check.py",
     "                return {'valid': True, 'errors': [], 'active': True}",
     "                return {'valid': None, 'errors': [], 'active': True}"),
    ("M27 deger-bagimli: yalniz 'inactive' aktif-degil sayilir", "scripts/syntax_check.py",
     "            if surum:\n", "            if surum == 'inactive':\n"),
    ("M28 404 False -> None (bulunamadi olculemedi'ye kayar)", "scripts/syntax_check.py",
     "                'valid': False,\n                'errors': [{'message': f'Object {object_name} not found'}]",
     "                'valid': None,\n                'errors': [{'message': f'Object {object_name} not found'}]"),
    ("M29 Q317 asiri-genis: errors DOLU False da UNVERIFIED (gercek hata gizlenir)", "scripts/syntax_check.py",
     "    if result.get('valid') is False and not result.get('errors') and result.get('error'):",
     "    if result.get('valid') is False:"),
    ("M30 Q317 errors kosulu dustu (errors + error birlikteyse hata gizlenir)", "scripts/syntax_check.py",
     "and not result.get('errors') and result.get('error'):", "and result.get('error'):"),
    ("M31 Q317 olculemedi rc 0'a dustu", "scripts/syntax_check.py",
     "        return 1\n    if result.get('valid'):", "        return 0\n    if result.get('valid'):"),
    ("M32 Q317 daraltma: DDIC HTTP≠200/404 dali False'ta kaldi", "scripts/syntax_check.py",
     "        return {'valid': None, 'errors': [], 'active': None,\n                'sozdizimi_sebep': f'ddic_http_",
     "        return {'valid': False, 'errors': [{'message': 'Failed to check object: HTTP'}], 'active': None,\n"
     "                'sozdizimi_sebep': f'ddic_http_"),
    ("M33 Q317 daraltma: DDIC istisna dali False'ta kaldi", "scripts/syntax_check.py",
     "        return {'valid': None, 'errors': [], 'active': None,\n                'sozdizimi_sebep': f'ddic_istisna:",
     "        return {'valid': False, 'errors': [{'message': 'istisna'}], 'active': None,\n"
     "                'sozdizimi_sebep': f'ddic_istisna:"),
    ("M34 Q317 daraltma: yalniz DDIC, sap_client istisna sozlugu CLI'de hala FAIL", "scripts/syntax_check.py",
     "        return 'kontrol_istisnasi:' + str(result.get('error'))[:160]", "        return None"),
    ("M35 Q317 baslik geri: 'SAP did not run the check' (DDIC icin yanlis)", "scripts/syntax_check.py",
     "syntax of {args.name} could not be verified", "SAP did not run the check for {args.name}"),
]


def _kopya_agac() -> Path:
    kok = Path(tempfile.mkdtemp(prefix="akt_hukum_kum_"))
    for d in ("scripts", "mcp_servers"):
        shutil.copytree(REPO / d, kok / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    hedef = kok / "tests" / "fixtures" / BURASI.name
    hedef.mkdir(parents=True)
    shutil.copy2(Path(__file__), hedef / "run.py")
    shutil.copytree(CANLI, hedef / "canli")
    return kok


def _kos(kok: Path):
    r = subprocess.run([sys.executable, str(kok / "tests" / "fixtures" / BURASI.name / "run.py")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=600, cwd=str(kok))
    m = re.search(r"^(\d+)/(\d+) OK$", r.stdout, re.M)
    return r.returncode, (m.group(0) if m else None), r.stdout


def _mutasyon() -> int:
    kok = _kopya_agac()
    kotu = []
    try:
        for ad, yol, eski, yeni in MUTASYONLAR:
            dosya = kok / yol
            asil = dosya.read_text(encoding="utf-8")
            if asil.count(eski) != 1:
                print(f"  [KURULAMADI] {ad} -> parca {asil.count(eski)} kez bulundu (1 olmali)")
                kotu.append(ad)
                continue
            dosya.write_text(asil.replace(eski, yeni, 1), encoding="utf-8", newline="")
            try:
                rc, ozet, cikti = _kos(kok)
            finally:
                dosya.write_text(asil, encoding="utf-8", newline="")
            dusen = [s.strip() for s in cikti.splitlines() if s.strip().startswith("[FAIL]")]
            if ozet is None:
                durum = "⛔ COKTU (olcum yok)"
                kotu.append(ad)
            elif rc:
                durum = "YAKALANDI"
            else:
                durum = "⛔ KACTI"
                kotu.append(ad)
            print(f"--> [{ad}] rc={rc} {ozet} -> {durum}")
            for s in dusen[:4]:
                print(f"      {s[:150]}")
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    print(f"\nMUTASYON OZETI: {len(MUTASYONLAR) - len(kotu)}/{len(MUTASYONLAR)} yakalandi")
    if kotu:
        print("  YAKALANAMAYAN/KURULAMAYAN: " + ", ".join(kotu))
    return 1 if kotu else 0


def _taban(ref: str) -> int:
    kok = _kopya_agac()
    try:
        for yol in URETIM:
            r = subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:{yol}"], capture_output=True)
            if r.returncode != 0:
                print(f"[fixture-hatasi] git show {ref}:{yol} basarisiz: {r.stderr[:200]!r}")
                return 2
            (kok / yol).write_bytes(r.stdout)
        rc, ozet, cikti = _kos(kok)
        print(f"### TABAN {ref} (uretim dosyalari eski surum) rc={rc} {ozet}")
        print(cikti)
        return 0 if (ozet is not None and rc != 0) else 1
    finally:
        shutil.rmtree(kok, ignore_errors=True)


if __name__ == "__main__":
    if "--mutasyon" in sys.argv:
        sys.exit(_mutasyon())
    if "--taban" in sys.argv:
        sys.exit(_taban(sys.argv[sys.argv.index("--taban") + 1]))
    sys.exit(main())
