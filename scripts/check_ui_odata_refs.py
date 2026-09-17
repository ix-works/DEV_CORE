#!/usr/bin/env python3
"""
check_ui_odata_refs.py — UI5 freestyle app'in OData referanslarini canli $metadata ile
statik karsilastirir. Kopyalanan/uyarlanan UI'larda (ozellikle SEGW->RAP gocu) hatalari
TARAYICIDA TEK TEK tiklamadan, tek seferde yakalar.

Kontroller (tek VE cift tirnak — acilis ve kapanis tirnagi AYNI olmali):
  • callFunction("/X", {...})  -> X function import mi? urlParameters anahtarlari FI param mi?
  • .read("/X") / path:"/X" / entitySet="X" -> X entity set mi? (yoksa function-import uyarisi)
  • {m>/X} / path:"m>/X"       -> m manifest'te bir OData modeli ise X, O servisin entity set'i mi?
  • var|let|const V = "/X"     -> X entity set mi? Bulunamazsa KIRMIZI DEGIL, [?] UYARI:
                                  degiskenin hangi modele gittigi statik olarak bilinmez.
  • new Filter("P") / $orderby / $select -> P metadata property mi?

COK SERVIS (Q299): manifest `sap.app.dataSources` + `sap.ui5.models` ile model adi -> servis
haritasi kurulur. JS'te referansin ALICI ifadesi cozulur (`getModel("x")` · `getModel()` ·
`this._yardimci()` [govdesi `return ...getModel("x")`] · en yakin `oX = ...` atamasi · dialog
icin en yakin `oX.setModel(...)`) ve referans O modelin servisine karsi olculur. Modeli
statik cozulemeyen referans BUGUNKU gibi ANA servise karsi olculur (gevsetme yok) ve
sayisi beyan edilir.

OLCULMEYENLER (her kosumda sayilariyla basilir — "TEMIZ" bunlari KAPSAMAZ):
  • degiskenli filtre `new Filter(sProp, ...)` · view/fragment `{Prop}` binding'leri ·
    yukaridaki desenlere uymayan diger "/X" literalleri (JSON model yolu, nesne alani,
    fonksiyon argumani) · KAPSANAN disindaki dosyalar (Component.js, model/*, util/* ...).
  ⚠ Bu dosyanin docstring'i 2026-09-13'e kadar "view {P} binding -> property mi?" diyordu;
    kod bunu HIC yapmiyordu (yorum kodu yalanliyordu). Duzeltildi, genisletilmedi.

Kullanim:
  python scripts/check_ui_odata_refs.py --app <source_root>/SD/ZSD001_CLC/ui/order_app_rap \
      --service ZSD001_UI_SO_O2
  (baglanti: .conn_adt; --service yoksa manifest mainService uri'sinden cikarilir)

Cikis kodu: 0 = KIRMIZI YOK (hukum satiri TEMIZ mi, OLCULMEYEN eksen mi, UYARI mi — okuyun),
            1 = en az bir KIRMIZI (yapisal) uyumsuzluk,
            2 = OLCEMEDIM (servis adi cozulemedi · taranacak dosya bulunamadi · .conn_adt
                okunamadi · $metadata alinamadi [ag/HTTP/zaman asimi/EDMX olmayan govde] ·
                KIRMIZI yokken ikincil servisin $metadata'si alinamadi).

⛔ Q232 (2026-09-04) — "0 dosya taradim" ile "temiz" AYNI CIKTIYI veriyordu:
   olmayan bir `--app` yolunda `glob` sessizce `[]` doner, hicbir kontrol calismaz ve
   arac `TEMIZ` + exit 0 basardi. Iki kosumun ciktisi BAYT-BIREBIR AYNIYDI (olculdu
   2026-09-02: `--app <musteri-d>_mesaj` [yol YOK] ile `--app <tam yol>` [4 dosya]) ⇒
   cagiran tarafin ayirt etmesi IMKANSIZDI ve bir bug-expert'i fiilen yanilti.
   Artik: (a) cozulmeyen `--app`/`webapp` = HATA (exit 2), (b) payda HER kosumda
   basilir, (c) 0 dosya "TEMIZ" DEGIL "OLCUM YOK"tur.

⛔ Q284 (2026-09-13) — dosya VAR ama BINDING gorulmuyordu, yine "TEMIZ":
   desenler yalniz CIFT tirnakti; XML'deki `rows="{ path: '/X', ... }"` (tek tirnak) ve
   JS'teki `var ENTITY = "/X"` + `bindRows({ path: sPath })` hicbir desene uymuyordu.
   Olculdu (19 app'lik gercek korpus, canli $metadata): 7/19 app'te entity bolumu BOS
   iken hukum `TEMIZ` + exit 0. Tek tirnakli `path:` 16 isabet / 9 app — 16'si de ana
   servisin EntitySet'i (0 FP). Genel `"/[A-Z]..."` literal kurali REDDEDILDI: 512
   adayin 67'si JSON-model yolu, 37'si baska servisin seti ⇒ KIRMIZI yapilsaydi yanlis
   alarm yagardi. Dar kural (`var X = "/Y"`): 16 aday, 14 ana servis ES, 2 baska servis
   ⇒ UYARI sinifinda. Artik: (a) yedi desenin hepsi tirnak SINIFI (geri-referansli),
   (b) degisken yolu ekseni, (c) her bolum paydasini basar; entity/property ekseni 0
   ise hukum "TEMIZ" DEGIL "OLCULMEDI"dir (exit 0 — K1/X1: olcmemek ihlal degildir),
   (d) olculmeyen yuzeyler koddan SAYILARAK beyan edilir.

⛔ Q299 (2026-09-13) — arac TEK servisi kiyasliyordu: coklu dataSource'lu app'te
   `getModel("driver").read("/CountryVH")` ana serviste aranip "ENTITY SET YOK" basiyordu.
   Olculdu (canli, 6 app): 27 KIRMIZI — sahte KIRMIZI alarm yorgunlugu uretir, gercek
   bulgu aralarinda kaybolur. Artik yukaridaki COK SERVIS bolumu.

⛔ Q300 (2026-09-13) — `fetch_metadata` try/except ve timeout tasimiyordu: SAP'ye
   ulasilamayinca traceback + exit 1 (= "KIRMIZI var" ile AYNI kod). Olculdu (yerel
   sahte sunucu): 401/404/500/baglanti reddi/.conn_adt yok -> traceback rc=1; EDMX
   olmayan 200 govdesi -> "2 KIRMIZI" rc=1; asili sunucu -> 90 sn bekledi. Artik
   `[FAIL] OLCEMEDIM` + exit 2, zaman asimi `ZAMAN_ASIMI`.
"""
import argparse, glob, json, os, re, sys
import requests, urllib3
urllib3.disable_warnings()
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

# CORE-03: core'un KENDI agaci icin `__file__` turevi MESRU kullanimdir (proje koku
# DEGIL, `scripts/` import koku araniyor). Ortak kapsam sozlesmesi orada yasar.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.kapsam import kapsam_eki  # noqa: E402

JS_KEYS = {"method", "headers", "success", "error", "urlParameters", "filters", "sorters"}

# Q232 IKINCI EKSEN — kapinin GERCEK kapsami artik BELGELI ve CIKTIDA gorunur.
# `TEMIZ` sozu "bu app'in butun OData referanslari uyumlu" DEMEK DEGILDIR; asagidaki
# uc desen disinda kalan her sey (Component.js · model/models.js · util/*.js · i18n/* ·
# localService/*) KAPSAM DISIDIR. Okuyanin bunu cikti satirindan gormesi gerekir.
KAPSANAN = ("webapp/controller/*.js", "webapp/view/*.xml", "webapp/fragment/*.xml")
BIRIM = "UI dosyasi [" + " · ".join(KAPSANAN) + "]"

# Q300: (baglanti, okuma) saniye. Asili bir sunucuda arac SURESIZ beklemesin.
ZAMAN_ASIMI = (10, 60)

# Q284 — TIRNAK SINIFI. `(["'])` acilis tirnagini yakalar, `\1` AYNI tirnakla kapanmayi
# zorlar: `'/X"` gibi dengesiz bir dizi referans sayilmaz. Yedi desenin HEPSI bu sinifta;
# biri cift-tirnakta kalirsa sinif yine vaka-duzeyinde kapanmis olur.
RE_CALLFN = re.compile(r'callFunction\(\s*(["\'])/([A-Za-z0-9_]+)\1\s*,\s*\{(.*?)\n\s*\}\s*\)', re.S)
RE_READ = re.compile(r'\.read\(\s*(["\'])/([A-Za-z0-9_]+)\1')
RE_PATH = re.compile(r'path:\s*(["\'])/([A-Za-z0-9_]+)\1')
RE_ENTITYSET = re.compile(r'(?:entitySet|EntitySet)=(["\'])([A-Za-z0-9_]+)\1')
RE_FILTER = re.compile(r'new Filter\(\s*(["\'])([A-Za-z_][A-Za-z0-9_]*)\1')
RE_ORDERBY = re.compile(r'\$orderby["\']?\s*:\s*(["\'])((?:(?!\1).)+)\1')
RE_SELECT = re.compile(r'\$select["\']?\s*:\s*(["\'])((?:(?!\1).)+)\1')
# Degiskene atanmis entity yolu. BUYUK harfle baslayan tek segment + satir/ifade sonu:
# `var PATH = "/busy"` (JSON model) ve `var s = "/A/B"` (ic ice yol) BILEREK disarida.
RE_DEGISKEN = re.compile(
    r'\b(?:var|let|const)\s+[A-Za-z_$][\w$]*\s*=\s*(["\'])/([A-Z][A-Za-z0-9_]*)\1\s*[;,\n]')
# Q299 — ISIMLI model binding'i. Model adi manifest'te bir OData modeline eslenmiyorsa
# (JSON `ui>` · `orderModel>` ...) referans SAYILMAZ. Olculdu: korpusta 3 isabet.
RE_ISIMLI_PATH = re.compile(r'path:\s*(["\'])([A-Za-z0-9_]+)>/([A-Za-z0-9_]+)\1')
RE_ISIMLI_SUSLU = re.compile(r'\{\s*([A-Za-z0-9_]+)>/([A-Za-z0-9_]+)\s*\}')
# OLCULMEYEN yuzeylerin SAYACLARI (kontrol DEGIL — kapsam beyaninin paydasi).
RE_FILTER_DEGISKEN = re.compile(r'new Filter\(\s*(?!["\'{])[A-Za-z_$][\w$.]*\s*,')
RE_LITERAL = re.compile(r'(["\'])/([A-Z][A-Za-z0-9_]*)\1')
RE_SERVIS_URI = re.compile(r'^/sap/opu/odata/sap/([^/"?]+)/?$', re.I)

ENTITY_DESENLERI = ".read('/X') · path: '/X' · entitySet='X' · var X = '/X' (tek/cift tirnak)"

# Q299 — alici cozumu. ODATA: referansin kendisi bu cagrinin argumani. BAGLAMA: dialog/tablo
# binding'i (model, kontrolun `setModel(...)`inden gelir).
ODATA_METOTLARI = {"read", "callFunction", "create", "update", "remove", "createKey"}
BAGLAMA_METOTLARI = {"bindAggregation", "bindRows", "bindItems", "bindList", "bindElement",
                     "bindObject"}
RX_GETMODEL = re.compile(r'getModel\((?:(["\'])([A-Za-z0-9_]+)\1)?\)$')
RX_YARDIMCI = re.compile(r'(?:[A-Za-z_$][\w$]*\.)?([A-Za-z_$][\w$]*)\(\)')
RX_TANIMLAYICI = re.compile(r'(?:(?:this|that|me|self)\.)?[A-Za-z_$][\w$]*')


def load_conn(cwd):
    p = os.path.join(cwd, ".conn_adt")
    cfg = {}
    for line in open(p, encoding="utf-8"):
        if "=" in line:
            k, v = line.split("=", 1); cfg[k.strip()] = v.strip()
    return cfg


def fetch_metadata(cfg, service):
    s = requests.Session(); s.auth = (cfg["ADT_SAP_USER"], cfg["ADT_SAP_PASSWORD"]); s.verify = False
    url = f"{cfg['ADT_SAP_URL']}/sap/opu/odata/sap/{service}/$metadata"
    r = s.get(url, params={"sap-client": cfg.get("ADT_SAP_CLIENT", "100")}, timeout=ZAMAN_ASIMI)
    r.raise_for_status()
    return r.text


def metadata_al(cfg, service):
    """(md, None) ya da (None, neden). Q300: ag/HTTP hatasi KIRMIZI DEGIL, OLCEMEDIM'dir.

    `HTTPError` (401/404/500) `RequestException`in alt sinifidir: servis adi yanlis ya da
    yetki yoksa UI referanslari hakkinda HICBIR sey olculmemistir. `KeyError`: .conn_adt'de
    zorunlu anahtar eksik. EDMX olmayan 200 govdesi (oturum/giris sayfasi) de olcum degildir
    — yoksa her referans "YOK" gorunur (olculdu: sahte "2 KIRMIZI").
    """
    try:
        md = fetch_metadata(cfg, service)
    except (requests.RequestException, KeyError) as exc:
        kod = getattr(getattr(exc, "response", None), "status_code", None)
        return None, type(exc).__name__ + (f" {kod}" if kod else "")
    if "<edmx:Edmx" not in (md or ""):
        return None, "yanit EDMX degil (oturum/giris sayfasi olabilir)"
    return md, None


def parse_metadata(md):
    entitysets = set(re.findall(r'<EntitySet Name="([^"]+)"', md))
    funcimports = {}
    for m in re.finditer(r'<FunctionImport Name="([^"]+)"(.*?)</FunctionImport>', md, re.S):
        funcimports[m.group(1)] = set(re.findall(r'<Parameter Name="([^"]+)"', m.group(2)))
    allprops = set(re.findall(r'<Property Name="([^"]+)"', md))
    return entitysets, funcimports, allprops


def model_haritasi(app):
    """manifest -> ({model_adi: servis}, not). Yalniz OData dataSource'una bagli modeller.

    Harita okunamazsa BOS doner: her referans bugunku gibi ANA servise karsi olculur
    (gevsetme yok) ve `not` ciktida gorunur.
    """
    p = os.path.join(app, "webapp", "manifest.json")
    if not os.path.isfile(p):
        return {}, "manifest.json YOK"
    try:
        m = json.load(open(p, encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return {}, f"manifest.json okunamadi ({type(exc).__name__})"
    servis_ds = {}
    for ad, d in ((m.get("sap.app") or {}).get("dataSources") or {}).items():
        if isinstance(d, dict) and (d.get("type") or "OData") == "OData":
            u = RE_SERVIS_URI.match(d.get("uri") or "")
            if u:
                servis_ds[ad] = u.group(1)
    harita = {}
    for ad, mdl in ((m.get("sap.ui5") or {}).get("models") or {}).items():
        if isinstance(mdl, dict) and mdl.get("dataSource") in servis_ds:
            harita[ad] = servis_ds[mdl["dataSource"]]
    return harita, ""


def maske(txt):
    """Ayni uzunlukta kopya: yorum ve string ICERIGI bosluk (tirnaklar yerinde).

    Yalniz parantez/alici yapisi icindir. SINIR: regex literali (`/[(]/`) tanimaz —
    dengesizlik alici cozumunu bozarsa referans COZULEMEDI'ye duser (ana servis).
    """
    out = list(txt)
    i, n, durum = 0, len(txt), None
    while i < n:
        c = txt[i]
        if durum is None:
            if c in "\"'`":
                durum = c
            elif c == "/" and i + 1 < n and txt[i + 1] in "/*":
                durum = "//" if txt[i + 1] == "/" else "/*"
                out[i] = out[i + 1] = " "
                i += 1
        elif durum == "//":
            if c == "\n":
                durum = None
            else:
                out[i] = " "
        elif durum == "/*":
            if c == "*" and i + 1 < n and txt[i + 1] == "/":
                out[i] = out[i + 1] = " "
                durum = None
                i += 1
            elif c != "\n":
                out[i] = " "
        else:
            if c == "\\" and i + 1 < n:
                out[i] = out[i + 1] = " "
                i += 1
            elif c == durum:
                durum = None
            elif c != "\n":
                out[i] = " "
        i += 1
    return "".join(out)


def _alici_basi(mk, bitis):
    """mk[:bitis] sonundaki `a.b(...).c` ifadesinin baslangic ofseti (yoksa None)."""
    j = bitis
    while True:
        while j > 0 and mk[j - 1].isspace():
            j -= 1
        while j > 0 and mk[j - 1] == ")":
            derin, k = 0, j
            while k > 0:
                k -= 1
                if mk[k] == ")":
                    derin += 1
                elif mk[k] == "(":
                    derin -= 1
                    if derin == 0:
                        break
            if derin != 0:
                return None
            j = k
            while j > 0 and mk[j - 1].isspace():
                j -= 1
        k = j
        while k > 0 and (mk[k - 1].isalnum() or mk[k - 1] in "_$"):
            k -= 1
        if k == j:
            return None if j == bitis else j
        j = k
        k = j
        while k > 0 and mk[k - 1].isspace():
            k -= 1
        if k > 0 and mk[k - 1] == ".":
            j = k - 1
            continue
        return j


def _ifade(txt, bas, bitis):
    return re.sub(r"\s+", "", txt[bas:bitis])


def _coz(ifade, txt, konum, derinlik=0):
    """Alici ifadesi -> model adi ("" = varsayilan model) ya da None (statik cozulemedi)."""
    if derinlik > 3 or not ifade:
        return None
    m = RX_GETMODEL.search(ifade)
    if m:
        return m.group(2) or ""
    m = RX_YARDIMCI.fullmatch(ifade)
    if m:   # this._bkg()  ->  _bkg: function () { return ...getModel("bkg"); }
        d = re.search(r'\b' + re.escape(m.group(1)) +
                      r'\s*(?::\s*function\s*)?\(\s*\)\s*\{\s*return\s+([^;{}]+?)\s*;?\s*\}', txt)
        return _coz(re.sub(r"\s+", "", d.group(1)), txt, d.start(), derinlik + 1) if d else None
    if RX_TANIMLAYICI.fullmatch(ifade):   # oBey  ->  en yakin ONCEKI `oBey = ...;`
        atamalar = [a for a in re.finditer(r'(?<![\w$.])' + re.escape(ifade) +
                                           r'\s*=(?![=>])\s*([^;\n]+)', txt) if a.start() < konum]
        if atamalar:
            a = atamalar[-1]
            return _coz(re.sub(r"\s+", "", a.group(1)), txt, a.start(), derinlik + 1)
    return None


def _setmodel_coz(alici, txt, konum):
    """Kontrolun varsayilan modeli: en yakin ONCEKI tek argumanli `alici.setModel(expr)`."""
    if not RX_TANIMLAYICI.fullmatch(alici):
        return None
    adaylar = [s for s in re.finditer(r'(?<![\w$.])' + re.escape(alici) + r'\.setModel\(([^,;]*?)\)\s*;', txt)
               if s.start() < konum]
    if not adaylar:
        return None
    s = adaylar[-1]
    return _coz(re.sub(r"\s+", "", s.group(1)), txt, s.start())


def cagri_modeli(txt, mk, konum):
    """`konum`daki referansi saran OData/binding cagrisinin modeli (None = cozulemedi).

    Disari dogru yurunur; `(` `[` ve nesne literali `{` gecilir, fonksiyon/blok govdesi
    `{` gecilmez (referans baska bir cagrinin callback'inde olabilir -> cozulemedi).
    """
    derin = {")": 0, "]": 0, "}": 0}
    j = konum
    while j > 0:
        j -= 1
        c = mk[j]
        if c in ")]}":
            derin[c] += 1
        elif c in "([{":
            kapan = {"(": ")", "[": "]", "{": "}"}[c]
            if derin[kapan]:
                derin[kapan] -= 1
                continue
            if c == "{":
                k = j
                while k > 0 and mk[k - 1].isspace():
                    k -= 1
                if k == 0 or mk[k - 1] not in "(,[:=":
                    return None
                continue
            if c == "[":
                continue
            bas = _alici_basi(mk, j)
            if bas is None:
                return None
            ifade = _ifade(txt, bas, j)
            if "." not in ifade:
                continue          # new Filter( / String( / fonksiyon cagrisi: disari devam
            alici, metot = ifade.rsplit(".", 1)
            if metot in ODATA_METOTLARI:
                return _coz(alici, txt, bas)
            if metot in BAGLAMA_METOTLARI:
                return _setmodel_coz(alici, txt, bas)
    return None


def dogrudan_model(txt, mk, nokta):
    """`.read(`/`.callFunction(` referansinin alici modeli; `nokta` metottan onceki `.` ofseti."""
    bas = _alici_basi(mk, nokta)
    return None if bas is None else _coz(_ifade(txt, bas, nokta), txt, bas)


def scan_ui(app, cok_servis=True):
    """Dondurur: (callfn, reads, props, taranan_dosya, ek).

    Q299: her referans MODEL etiketi tasir — "" varsayilan model, "ad" isimli model,
    None statik cozulemedi (cagiran ANA servise karsi olcer ve sayar).
      callfn  {(model, fn): {"keys", "where"}}
      reads   {(model, ad, dosya)}
      props   {(model, property)}
    `ek` OLCULMEYEN yuzeyin paydalarini ve degisken-yolu adaylarini tasir:
      degisken        {(ad, dosya, (model, ...))} — `var X = "/Ad"` adaylari + kullanildigi modeller
      filtre_degisken int — `new Filter(<degisken>, ...)` cagri sayisi
      diger_literal   int — hicbir kapsanan desene girmeyen "/Ad" literal sayisi
      isimli          {(model, ad, dosya)} — `{m>/Ad}` / `path: 'm>/Ad'`
    """
    wf = os.path.join(app, "webapp")
    files = (glob.glob(os.path.join(wf, "controller", "*.js"))
             + glob.glob(os.path.join(wf, "view", "*.xml"))
             + glob.glob(os.path.join(wf, "fragment", "*.xml")))
    callfn, reads, props = {}, set(), set()
    ek = {"degisken": set(), "filtre_degisken": 0, "diger_literal": 0, "isimli": set()}
    for f in files:
        txt = open(f, encoding="utf-8").read()
        short = f.replace(wf + os.sep, "").replace(os.sep, "/")
        js = cok_servis and f.endswith(".js")
        mk = maske(txt) if js else ""

        def model(konum, dogrudan=False):
            if not js:
                return ""          # XML varsayilan binding = gorunumun varsayilan modeli
            if dogrudan:
                k = konum
                while k > 0 and mk[k - 1].isspace():
                    k -= 1
                return dogrudan_model(txt, mk, k - 1) if k > 0 and mk[k - 1] == "." else None
            return cagri_modeli(txt, mk, konum)

        kapsanan_tirnak = set()   # "/Ad" literallerinden bir desene GIREN tirnak konumlari
        for m in RE_CALLFN.finditer(txt):
            kapsanan_tirnak.add(m.start(1))
            up = re.search(r'urlParameters:\s*\{(.*?)\}', m.group(3), re.S)
            keys = set(re.findall(r'([A-Za-z_][A-Za-z0-9_]*)\s*:', up.group(1))) if up else set()
            anahtar = (model(m.start(), dogrudan=True), m.group(2))
            callfn.setdefault(anahtar, {"keys": set(), "where": short})["keys"].update(keys)
        for rx in (RE_READ, RE_PATH, RE_ENTITYSET):
            for m in rx.finditer(txt):
                kapsanan_tirnak.add(m.start(1))
                mdl = model(m.start() + 1, dogrudan=True) if rx is RE_READ else (
                    model(m.start()) if rx is RE_PATH else "")
                reads.add((mdl, m.group(2), short))
        for m in RE_DEGISKEN.finditer(txt):
            kapsanan_tirnak.add(m.start(1))
            ad = re.match(r'\b(?:var|let|const)\s+([A-Za-z_$][\w$]*)', m.group(0)).group(1)
            kullanim = tuple(sorted({model(u.start() + 1, dogrudan=True) for u in re.finditer(
                r'\.(?:read|createKey)\(\s*' + re.escape(ad) + r'\b', txt)} - {None})) if js else ()
            ek["degisken"].add((m.group(2), short, kullanim))
        for rx in (RE_ISIMLI_PATH, RE_ISIMLI_SUSLU):
            for m in rx.finditer(txt):
                g = m.groups()[-2:]
                ek["isimli"].add((g[0], g[1], short))
        for m in RE_FILTER.finditer(txt):
            props.add((model(m.start()), m.group(2)))
        ek["filtre_degisken"] += len(RE_FILTER_DEGISKEN.findall(txt))
        for m in RE_ORDERBY.finditer(txt):
            mdl = model(m.start())
            for tok in re.split(r'[ ,]+', m.group(2)):
                tok = tok.replace("desc", "").replace("asc", "").strip()
                if tok: props.add((mdl, tok))
        for m in RE_SELECT.finditer(txt):
            mdl = model(m.start())
            for tok in m.group(2).split(","):
                if tok.strip(): props.add((mdl, tok.strip()))
        ek["diger_literal"] += sum(1 for m in RE_LITERAL.finditer(txt)
                                   if m.start(1) not in kapsanan_tirnak)
    return callfn, reads, props, len(files), ek


def kapsam_dogrula(app):
    """`--app` GERCEKTEN cozuluyor mu? Cozulmuyorsa SESSIZ `[]` yerine GORUNUR hata.

    Bu, "kapsam mesru sekilde bos" durumu DEGILDIR (utils/kapsam.py K1 sozlesmesi
    onu FAIL yapmaz ve hakli): burada kullanici bir yol VERDI ve o yol tutmadi ⇒
    arac argumani ayristiramadi. Dosyanin kendi konvansiyonu bunu zaten exit 2 ile
    isaretliyor (`--service` cozulemedigi dal).
    """
    if not os.path.isdir(app):
        print(f"[FAIL] --app yolu YOK: {app}")
        print(f"       cozulen mutlak yol: {os.path.abspath(app)}")
        print("       Bu bir OLCUM DEGILDIR — hicbir dosya taranmadi (exit 2).")
        sys.exit(2)
    wf = os.path.join(app, "webapp")
    if not os.path.isdir(wf):
        print(f"[FAIL] webapp/ dizini YOK: {wf}")
        print("       --app, webapp'in UST dizini olmali (ornek: .../ui/<app_adi>).")
        print("       Bu bir OLCUM DEGILDIR — hicbir dosya taranmadi (exit 2).")
        sys.exit(2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", required=True, help="UI app klasoru (webapp ust dizini)")
    ap.add_argument("--service", help="OData servis adi (yoksa manifest'ten)")
    ap.add_argument("--cwd", default=".")
    a = ap.parse_args()

    # ⛔ SIRA ONEMLI: kapsam dogrulamasi AGA BAGLANMADAN once kosar. Yol yanlissa
    #    sonucu degistirecek hicbir sey yok; kullaniciyi bir `$metadata` cagrisi
    #    bekletmek (ve olasi bir 401'i asil hatanin ustune yazmak) anlamsizdir.
    kapsam_dogrula(a.app)

    # ⛔ KAPSAM AGDAN ONCE OLCULUR (Q232). Eskiden UI taramasi `fetch_metadata`dan
    #    SONRA geliyordu; yani arac, kiyaslayacak TEK BIR dosyasi olmadigi hallerde
    #    bile once SAP'ye gidiyor, sonra "TEMIZ" diyordu. Paydayi once olcmek hem
    #    dogru (bos kapsamda kiyas edilecek sey yoktur) hem ucuz (aga hic gidilmez).
    callfn, reads, props, taranan, ek = scan_ui(a.app)
    if taranan == 0:
        # `kapsam_eki` ortak sozlesmesi (K1) — "ihlal yok" ile "bakacak dosya yok"u
        # ayiran KANONIK metin. Yeni mekanizma icat edilmiyor, mevcut katman baglaniyor.
        print(kapsam_eki(0, BIRIM))
        print("\nOLCUM YOK — 'TEMIZ' DEGIL: webapp/ var ama taranacak dosya bulunamadi.")
        print(f"  Beklenen desenler: {' · '.join(KAPSANAN)}")
        sys.exit(2)

    service = a.service
    if not service:
        mani = open(os.path.join(a.app, "webapp", "manifest.json"), encoding="utf-8").read()
        m = re.search(r'"uri":\s*"/sap/opu/odata/sap/([^/"]+)/?"', mani, re.I)
        service = m.group(1) if m else None
    if not service:
        print("[FAIL] servis adi cozulemedi (--service ver)"); sys.exit(2)

    # Q299: model -> servis. Varsayilan model ("") DAIMA ana servistir (--service onu ezer).
    harita, harita_notu = model_haritasi(a.app)
    cozulemedi = 0

    def servis_of(mdl):
        nonlocal cozulemedi
        if mdl == "":
            return service
        if mdl is None or mdl not in harita:
            cozulemedi += 1
            return service
        return harita[mdl]

    reads = {(servis_of(mdl), ad, sh) for mdl, ad, sh in reads}
    reads |= {(harita[mdl], ad, sh) for mdl, ad, sh in ek["isimli"] if mdl in harita}
    birlesik = {}
    for (mdl, fn), info in callfn.items():
        hedef = birlesik.setdefault((servis_of(mdl), fn), {"keys": set(), "where": info["where"]})
        hedef["keys"].update(info["keys"])
    callfn = birlesik
    props = {(servis_of(mdl), p) for mdl, p in props}
    degisken = {(ad, sh, tuple(sorted({service} | {harita.get(k, service) for k in kull})))
                for ad, sh, kull in ek["degisken"]}

    # Q300: .conn_adt / $metadata okunamazsa bu bir OLCUM DEGILDIR (exit 2), KIRMIZI degil.
    try:
        cfg = load_conn(a.cwd)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"[FAIL] OLCEMEDIM: .conn_adt okunamadi ({type(exc).__name__}) — --cwd: {os.path.abspath(a.cwd)}")
        print("       Bu bir OLCUM DEGILDIR — hicbir referans kiyaslanmadi (exit 2).")
        sys.exit(2)
    md, neden = metadata_al(cfg, service)
    if md is None:
        print(f"[FAIL] OLCEMEDIM: $metadata alinamadi ({neden}) — servis {service}")
        print("       Bu bir OLCUM DEGILDIR — hicbir referans kiyaslanmadi (exit 2).")
        sys.exit(2)
    meta = {service: parse_metadata(md)}
    alinamayan = {}
    ikincil = sorted({s for s, _, _ in reads} | {s for s, _ in callfn} | {s for s, _ in props}
                     | {s for _, _, ss in degisken for s in ss})
    for s in ikincil:
        if s in meta:
            continue
        md2, neden2 = metadata_al(cfg, s)
        if md2 is None:
            alinamayan[s] = neden2
        else:
            meta[s] = parse_metadata(md2)

    entitysets, funcimports, allprops = meta[service]
    # PAYDA HER KOSUMDA BASILIR (Q232-b). "Servis su kadar sey iceriyor" satiri
    # metadata tarafinin paydasiydi; UI tarafininki HIC yazilmiyordu — yanlis-yesilin
    # gorunmez olmasinin sebebi tam olarak buydu.
    print(f"Servis {service}: {len(entitysets)} entitySet, {len(funcimports)} functionImport, {len(allprops)} property")
    ters = {}
    for mdl, s in harita.items():
        ters.setdefault(s, []).append(mdl)
    for s in ikincil:
        if s == service:
            continue
        adlar = ", ".join(f"'{x}'" for x in sorted(ters.get(s, [])))
        if s in meta:
            es2, fi2, ap2 = meta[s]
            print(f"Servis {s} (model {adlar}): {len(es2)} entitySet, {len(fi2)} functionImport, {len(ap2)} property")
        else:
            print(f"[FAIL] OLCEMEDIM: servis {s} (model {adlar}) $metadata alinamadi ({alinamayan[s]}) — referanslari OLCULEMEDI")
    ikinci_ad = sorted(f"'{mdl}' -> {s}" for mdl, s in harita.items() if s != service)
    if harita_notu:
        print(f"Model haritasi: {harita_notu} — tum referanslar ANA servise karsi olculdu")
    elif ikinci_ad:
        print(f"Model haritasi (manifest): {' · '.join(ikinci_ad)} · modeli statik cozulemeyen {cozulemedi} referans ANA servise karsi olculdu")
    else:
        print("Model haritasi (manifest): ikincil OData modeli yok — tum referanslar ANA servise karsi olculdu")
    print(f"UI kapsami:{kapsam_eki(taranan, BIRIM)}\n")
    red = 0
    uyari = 0
    olculemedi = 0
    n_entity = len(reads) + len(degisken)

    def etiket(s):
        return "" if s == service else f" (servis {s})"

    # Q284: her bolum KENDI paydasini basar. Bos bolum eskiden hicbir satir basmiyordu —
    # "bu eksende referans yok" ile "bu eksende referansi GOREMEDIM" ayni gorunuyordu.
    print(f"=== callFunction -> function import ===  ({len(callfn)} callFunction tarandi)")
    if not callfn:
        print("  (0 callFunction bulundu — bu eksende kiyaslanacak referans yok)")
    for (s, fn), info in sorted(callfn.items()):
        if s not in meta:
            print(f"  [--] OLCULEMEDI: {fn} [{info['where']}]{etiket(s)}"); olculemedi += 1; continue
        fis = meta[s][1]
        if fn not in fis:
            print(f"  [X] FUNC YOK: {fn} [{info['where']}]{etiket(s)}"); red += 1
        else:
            bad = (info["keys"] - fis[fn] - JS_KEYS) - {""}
            if bad:
                print(f"  [!] {fn}: gecersiz param {sorted(bad)} [{info['where']}]{etiket(s)}"); red += 1
            else:
                print(f"  [OK] {fn}{etiket(s)}")

    print(f"\n=== read/binding -> entity set ===  ({len(reads)} binding tarandi)")
    if n_entity == 0:
        print("  0 binding tarandi — entity ekseni OLCULMEDI")
        print(f"  aranan desenler: {ENTITY_DESENLERI}")
    elif not reads:
        print("  (0 dogrudan binding — entity ekseni yalniz degisken yollariyla olculdu, asagida)")
    for s, name, short in sorted(reads, key=lambda r: (r[1], r[2], r[0])):
        if s not in meta:
            print(f"  [--] OLCULEMEDI: {name} [{short}]{etiket(s)}"); olculemedi += 1; continue
        es, fis = meta[s][0], meta[s][1]
        if name in es: print(f"  [OK] {name}{etiket(s)}")
        elif name in fis: print(f"  [!] {name}: function import (read degil callFunction olmali) [{short}]{etiket(s)}"); red += 1
        else: print(f"  [X] ENTITY SET YOK: {name} [{short}]{etiket(s)}"); red += 1

    # Degisken yolu KIRMIZI URETMEZ: degiskenin hangi modele (ya da hangi cagriya) gittigi
    # statik olarak bilinmez — olculdu, gercek korpusta 2/16 aday BASKA servisin setiydi.
    # Q299: degisken `<alici>.read(DEGISKEN)` ile cozulen bir modelde kullaniliyorsa O servis
    # de aranir; hicbirinde yoksa yine yalniz UYARI.
    if degisken:
        print(f"\n=== degiskene atanmis yol (var X = '/Ad') -> entity set ===  ({len(degisken)} aday tarandi)")
        for name, short, servisler in sorted(degisken):
            sira = [service] + [x for x in servisler if x != service]   # ana servis ONCE
            bulunan = [s for s in sira if s in meta and name in meta[s][0]]
            if bulunan:
                print(f"  [OK] {name} [{short}]{etiket(bulunan[0])}")
            else:
                neden = "function import" if name in funcimports else "servis metadata'sinda yok"
                print(f"  [?] UYARI {name}: {neden} — degisken baska modele gidiyor olabilir [{short}]")
                uyari += 1

    print(f"\n=== property (Filter/$orderby/$select) ===  ({len(props)} property tarandi)")
    unknown = sorted((p, s) for s, p in props if s in meta and p not in meta[s][2])
    kayip = sorted((p, s) for s, p in props if s not in meta)
    if not props:
        print("  0 property tarandi — property ekseni OLCULMEDI")
    elif unknown or kayip:
        for p, s in unknown: print(f"  [X] property YOK: {p}{etiket(s)}"); red += 1
        for p, s in kayip: print(f"  [--] OLCULEMEDI: property {p}{etiket(s)}"); olculemedi += 1
    else:
        print("  [OK] hepsi metadata'da")

    # KAPSAM BEYANI — sayilar KODDAN turer (elle yazilan liste bayatlar). En kritik an
    # sifir-bulgu anidir; bu yuzden HER kosumda basilir.
    olculmeyen = [e for e, n in (("entity", n_entity), ("property", len(props))) if n == 0]
    print("\n=== OLCULMEDI — bu arac asagidakilere BAKMAZ ===")
    if olculmeyen:
        print(f"  · eksen: {' + '.join(olculmeyen)} — 0 referans goruldu (desen korlugu olabilir)")
    print(f"  · {ek['filtre_degisken']} degiskenli new Filter(<degisken>, ...) cagrisi — property adi statik cozulmuyor")
    print("  · view/fragment {Prop} binding'leri — property ekseninde TARANMIYOR")
    print(f"  · {ek['diger_literal']} diger '/Ad' literali (JSON model yolu · nesne alani · fonksiyon argumani) — entity sayilmadi")
    print(f"  · {' · '.join(KAPSANAN)} DISINDAKI dosyalar (Component.js · model/* · util/* ...)")
    if alinamayan:
        print(f"  · {olculemedi} referans OLCULEMEDI — ikincil servis $metadata'si alinamadi: {', '.join(sorted(alinamayan))}")

    # Niteleyici HUKMUN ICINDE durur: "TEMIZ" tek basina kapsami oldugundan genis
    # gosteriyordu (Q232 ikinci ekseni). Payda ve desen artik ayni satirda.
    if red:
        hukum = f"{red} KIRMIZI uyumsuzluk" + (f" · {olculemedi} referans OLCULEMEDI" if olculemedi else "")
    elif olculemedi:
        hukum = f"OLCEMEDIM (kismi) — KIRMIZI YOK ama {olculemedi} referans OLCULEMEDI (ikincil servis $metadata'si alinamadi)"
    elif olculmeyen:
        hukum = f"KIRMIZI YOK — TEMIZ DEGIL: {' + '.join(olculmeyen)} ekseni OLCULMEDI"
    elif uyari:
        hukum = f"KIRMIZI YOK — {uyari} UYARI (degisken yolu servis metadata'sinda yok)"
    else:
        hukum = "TEMIZ"
    print(f"\n{hukum} ({taranan} {BIRIM} tarandi)")
    sys.exit(1 if red else (2 if olculemedi else 0))


if __name__ == "__main__":
    main()
