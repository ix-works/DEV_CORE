#!/usr/bin/env python3
"""
check_ui_odata_refs.py — UI5 freestyle app'in OData referanslarini canli $metadata ile
statik karsilastirir. Kopyalanan/uyarlanan UI'larda (ozellikle SEGW->RAP gocu) hatalari
TARAYICIDA TEK TEK tiklamadan, tek seferde yakalar.

Kontroller (tek VE cift tirnak — acilis ve kapanis tirnagi AYNI olmali):
  • callFunction("/X", {...})  -> X function import mi? urlParameters anahtarlari FI param mi?
  • .read("/X") / path:"/X" / entitySet="X" -> X entity set mi? (yoksa function-import uyarisi)
  • var|let|const V = "/X"     -> X entity set mi? Bulunamazsa KIRMIZI DEGIL, [?] UYARI:
                                  degiskenin hangi modele gittigi statik olarak bilinmez.
  • new Filter("P") / $orderby / $select -> P metadata property mi?

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
            2 = OLCEMEDIM (servis adi cozulemedi VEYA taranacak dosya bulunamadi).

⛔ Q232 (2026-09-04) — "0 dosya taradim" ile "temiz" AYNI CIKTIYI veriyordu:
   olmayan bir `--app` yolunda `glob` sessizce `[]` doner, hicbir kontrol calismaz ve
   arac `TEMIZ` + exit 0 basardi. Iki kosumun ciktisi BAYT-BIREBIR AYNIYDI (olculdu
   2026-09-02: `--app volvo_mesaj` [yol YOK] ile `--app <tam yol>` [4 dosya]) ⇒
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
"""
import argparse, glob, os, re, sys
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
# OLCULMEYEN yuzeylerin SAYACLARI (kontrol DEGIL — kapsam beyaninin paydasi).
RE_FILTER_DEGISKEN = re.compile(r'new Filter\(\s*(?!["\'{])[A-Za-z_$][\w$.]*\s*,')
RE_LITERAL = re.compile(r'(["\'])/([A-Z][A-Za-z0-9_]*)\1')

ENTITY_DESENLERI = ".read('/X') · path: '/X' · entitySet='X' · var X = '/X' (tek/cift tirnak)"


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
    r = s.get(url, params={"sap-client": cfg.get("ADT_SAP_CLIENT", "100")})
    r.raise_for_status()
    return r.text


def parse_metadata(md):
    entitysets = set(re.findall(r'<EntitySet Name="([^"]+)"', md))
    funcimports = {}
    for m in re.finditer(r'<FunctionImport Name="([^"]+)"(.*?)</FunctionImport>', md, re.S):
        funcimports[m.group(1)] = set(re.findall(r'<Parameter Name="([^"]+)"', m.group(2)))
    allprops = set(re.findall(r'<Property Name="([^"]+)"', md))
    return entitysets, funcimports, allprops


def scan_ui(app):
    """Dondurur: (callfn, reads, props, taranan_dosya, ek).

    `ek` OLCULMEYEN yuzeyin paydalarini ve degisken-yolu adaylarini tasir:
      degisken        {(ad, dosya)} — `var X = "/Ad"` adaylari
      filtre_degisken int — `new Filter(<degisken>, ...)` cagri sayisi
      diger_literal   int — hicbir kapsanan desene girmeyen "/Ad" literal sayisi
    """
    wf = os.path.join(app, "webapp")
    files = (glob.glob(os.path.join(wf, "controller", "*.js"))
             + glob.glob(os.path.join(wf, "view", "*.xml"))
             + glob.glob(os.path.join(wf, "fragment", "*.xml")))
    callfn, reads, props = {}, set(), set()
    ek = {"degisken": set(), "filtre_degisken": 0, "diger_literal": 0}
    for f in files:
        txt = open(f, encoding="utf-8").read()
        short = f.replace(wf + os.sep, "").replace(os.sep, "/")
        kapsanan_tirnak = set()   # "/Ad" literallerinden bir desene GIREN tirnak konumlari
        for m in RE_CALLFN.finditer(txt):
            kapsanan_tirnak.add(m.start(1))
            up = re.search(r'urlParameters:\s*\{(.*?)\}', m.group(3), re.S)
            keys = set(re.findall(r'([A-Za-z_][A-Za-z0-9_]*)\s*:', up.group(1))) if up else set()
            callfn.setdefault(m.group(2), {"keys": set(), "where": short})["keys"].update(keys)
        for rx in (RE_READ, RE_PATH, RE_ENTITYSET):
            for m in rx.finditer(txt):
                kapsanan_tirnak.add(m.start(1))
                reads.add((m.group(2), short))
        for m in RE_DEGISKEN.finditer(txt):
            kapsanan_tirnak.add(m.start(1))
            ek["degisken"].add((m.group(2), short))
        for m in RE_FILTER.finditer(txt):
            props.add(m.group(2))
        ek["filtre_degisken"] += len(RE_FILTER_DEGISKEN.findall(txt))
        for m in RE_ORDERBY.finditer(txt):
            for tok in re.split(r'[ ,]+', m.group(2)):
                tok = tok.replace("desc", "").replace("asc", "").strip()
                if tok: props.add(tok)
        for m in RE_SELECT.finditer(txt):
            for tok in m.group(2).split(","):
                if tok.strip(): props.add(tok.strip())
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

    cfg = load_conn(a.cwd)
    md = fetch_metadata(cfg, service)
    entitysets, funcimports, allprops = parse_metadata(md)

    # PAYDA HER KOSUMDA BASILIR (Q232-b). "Servis su kadar sey iceriyor" satiri
    # metadata tarafinin paydasiydi; UI tarafininki HIC yazilmiyordu — yanlis-yesilin
    # gorunmez olmasinin sebebi tam olarak buydu.
    print(f"Servis {service}: {len(entitysets)} entitySet, {len(funcimports)} functionImport, {len(allprops)} property")
    print(f"UI kapsami:{kapsam_eki(taranan, BIRIM)}\n")
    red = 0
    uyari = 0
    degisken = ek["degisken"]
    n_entity = len(reads) + len(degisken)

    # Q284: her bolum KENDI paydasini basar. Bos bolum eskiden hicbir satir basmiyordu —
    # "bu eksende referans yok" ile "bu eksende referansi GOREMEDIM" ayni gorunuyordu.
    print(f"=== callFunction -> function import ===  ({len(callfn)} callFunction tarandi)")
    if not callfn:
        print("  (0 callFunction bulundu — bu eksende kiyaslanacak referans yok)")
    for fn, info in sorted(callfn.items()):
        if fn not in funcimports:
            print(f"  [X] FUNC YOK: {fn} [{info['where']}]"); red += 1
        else:
            bad = (info["keys"] - funcimports[fn] - JS_KEYS) - {""}
            if bad:
                print(f"  [!] {fn}: gecersiz param {sorted(bad)} [{info['where']}]"); red += 1
            else:
                print(f"  [OK] {fn}")

    print(f"\n=== read/binding -> entity set ===  ({len(reads)} binding tarandi)")
    if n_entity == 0:
        print("  0 binding tarandi — entity ekseni OLCULMEDI")
        print(f"  aranan desenler: {ENTITY_DESENLERI}")
    elif not reads:
        print("  (0 dogrudan binding — entity ekseni yalniz degisken yollariyla olculdu, asagida)")
    for name, short in sorted(reads):
        if name in entitysets: print(f"  [OK] {name}")
        elif name in funcimports: print(f"  [!] {name}: function import (read degil callFunction olmali) [{short}]"); red += 1
        else: print(f"  [X] ENTITY SET YOK: {name} [{short}]"); red += 1

    # Degisken yolu KIRMIZI URETMEZ: degiskenin hangi modele (ya da hangi cagriya) gittigi
    # statik olarak bilinmez — olculdu, gercek korpusta 2/16 aday BASKA servisin setiydi.
    if degisken:
        print(f"\n=== degiskene atanmis yol (var X = '/Ad') -> entity set ===  ({len(degisken)} aday tarandi)")
        for name, short in sorted(degisken):
            if name in entitysets:
                print(f"  [OK] {name} [{short}]")
            else:
                neden = "function import" if name in funcimports else "servis metadata'sinda yok"
                print(f"  [?] UYARI {name}: {neden} — degisken baska modele gidiyor olabilir [{short}]")
                uyari += 1

    print(f"\n=== property (Filter/$orderby/$select) ===  ({len(props)} property tarandi)")
    unknown = sorted(p for p in props if p not in allprops)
    if not props:
        print("  0 property tarandi — property ekseni OLCULMEDI")
    elif unknown:
        for p in unknown: print(f"  [X] property YOK: {p}"); red += 1
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

    # Niteleyici HUKMUN ICINDE durur: "TEMIZ" tek basina kapsami oldugundan genis
    # gosteriyordu (Q232 ikinci ekseni). Payda ve desen artik ayni satirda.
    if red:
        hukum = f"{red} KIRMIZI uyumsuzluk"
    elif olculmeyen:
        hukum = f"KIRMIZI YOK — TEMIZ DEGIL: {' + '.join(olculmeyen)} ekseni OLCULMEDI"
    elif uyari:
        hukum = f"KIRMIZI YOK — {uyari} UYARI (degisken yolu servis metadata'sinda yok)"
    else:
        hukum = "TEMIZ"
    print(f"\n{hukum} ({taranan} {BIRIM} tarandi)")
    sys.exit(0 if red == 0 else 1)


if __name__ == "__main__":
    main()
