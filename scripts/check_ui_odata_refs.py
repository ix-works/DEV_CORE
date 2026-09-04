#!/usr/bin/env python3
"""
check_ui_odata_refs.py — UI5 freestyle app'in OData referanslarini canli $metadata ile
statik karsilastirir. Kopyalanan/uyarlanan UI'larda (ozellikle SEGW->RAP gocu) hatalari
TARAYICIDA TEK TEK tiklamadan, tek seferde yakalar.

Kontroller:
  • callFunction("/X")        -> X function import mi? urlParameters anahtarlari FI param mi?
  • .read("/X") / path:"/X" / entitySet="X" -> X entity set mi? (yoksa function-import uyarisi)
  • new Filter("P") / $orderby / $select / view {P} binding -> P metadata property mi?

Kullanim:
  python scripts/check_ui_odata_refs.py --app <source_root>/SD/ZSD001_CLC/ui/order_app_rap \
      --service ZSD001_UI_SO_O2
  (baglanti: .conn_adt; --service yoksa manifest mainService uri'sinden cikarilir)

Cikis kodu: 0 = OLCTUM ve temiz, 1 = en az bir KIRMIZI (yapisal) uyumsuzluk,
            2 = OLCEMEDIM (servis adi cozulemedi VEYA taranacak dosya bulunamadi).

⛔ Q232 (2026-09-04) — "0 dosya taradim" ile "temiz" AYNI CIKTIYI veriyordu:
   olmayan bir `--app` yolunda `glob` sessizce `[]` doner, hicbir kontrol calismaz ve
   arac `TEMIZ` + exit 0 basardi. Iki kosumun ciktisi BAYT-BIREBIR AYNIYDI (olculdu
   2026-09-02: `--app volvo_mesaj` [yol YOK] ile `--app <tam yol>` [4 dosya]) ⇒
   cagiran tarafin ayirt etmesi IMKANSIZDI ve bir bug-expert'i fiilen yanilti.
   Artik: (a) cozulmeyen `--app`/`webapp` = HATA (exit 2), (b) payda HER kosumda
   basilir, (c) 0 dosya "TEMIZ" DEGIL "OLCUM YOK"tur.
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
    wf = os.path.join(app, "webapp")
    files = (glob.glob(os.path.join(wf, "controller", "*.js"))
             + glob.glob(os.path.join(wf, "view", "*.xml"))
             + glob.glob(os.path.join(wf, "fragment", "*.xml")))
    callfn, reads, props = {}, set(), set()
    for f in files:
        txt = open(f, encoding="utf-8").read()
        short = f.replace(wf + os.sep, "").replace(os.sep, "/")
        for m in re.finditer(r'callFunction\(\s*"/([A-Za-z0-9_]+)"\s*,\s*\{(.*?)\n\s*\}\s*\)', txt, re.S):
            up = re.search(r'urlParameters:\s*\{(.*?)\}', m.group(2), re.S)
            keys = set(re.findall(r'([A-Za-z_][A-Za-z0-9_]*)\s*:', up.group(1))) if up else set()
            callfn.setdefault(m.group(1), {"keys": set(), "where": short})["keys"].update(keys)
        for pat in (r'\.read\(\s*"/([A-Za-z0-9_]+)"', r'path:\s*"/([A-Za-z0-9_]+)"',
                    r'(?:entitySet|EntitySet)="([A-Za-z0-9_]+)"'):
            for m in re.finditer(pat, txt):
                reads.add((m.group(1), short))
        for m in re.finditer(r'new Filter\(\s*"([A-Za-z_][A-Za-z0-9_]*)"', txt):
            props.add(m.group(1))
        for m in re.finditer(r'\$orderby"?\s*:\s*"([^"]+)"', txt):
            for tok in re.split(r'[ ,]+', m.group(1)):
                tok = tok.replace("desc", "").replace("asc", "").strip()
                if tok: props.add(tok)
        for m in re.finditer(r'\$select"?\s*:\s*"([^"]+)"', txt):
            for tok in m.group(1).split(","):
                if tok.strip(): props.add(tok.strip())
    return callfn, reads, props, len(files)


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
    callfn, reads, props, taranan = scan_ui(a.app)
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

    print("=== callFunction -> function import ===")
    for fn, info in sorted(callfn.items()):
        if fn not in funcimports:
            print(f"  [X] FUNC YOK: {fn} [{info['where']}]"); red += 1
        else:
            bad = (info["keys"] - funcimports[fn] - JS_KEYS) - {""}
            if bad:
                print(f"  [!] {fn}: gecersiz param {sorted(bad)} [{info['where']}]"); red += 1
            else:
                print(f"  [OK] {fn}")

    print("\n=== read/binding -> entity set ===")
    for name, short in sorted(reads):
        if name in entitysets: print(f"  [OK] {name}")
        elif name in funcimports: print(f"  [!] {name}: function import (read degil callFunction olmali) [{short}]"); red += 1
        else: print(f"  [X] ENTITY SET YOK: {name} [{short}]"); red += 1

    print("\n=== property (Filter/$orderby/$select) ===")
    unknown = sorted(p for p in props if p not in allprops)
    if unknown:
        for p in unknown: print(f"  [X] property YOK: {p}"); red += 1
    else:
        print("  [OK] hepsi metadata'da")

    # Niteleyici HUKMUN ICINDE durur: "TEMIZ" tek basina kapsami oldugundan genis
    # gosteriyordu (Q232 ikinci ekseni). Payda ve desen artik ayni satirda.
    print(f"\n{'TEMIZ' if red == 0 else str(red) + ' KIRMIZI uyumsuzluk'} "
          f"({taranan} {BIRIM} tarandi)")
    sys.exit(0 if red == 0 else 1)


if __name__ == "__main__":
    main()
