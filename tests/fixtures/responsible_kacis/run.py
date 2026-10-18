#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""responsible_kacis — `adtcore:responsible` yer tutucusu + kaçışsız öznitelik (Issue #339).

KUSUR (ölçüldü, main 998e739, kod okuması + bu korpusun `--eski-kod` kipi):
  · `populate_message_class` / `populate_dataelements` / `populate_domains`:
    `--responsible` varsayılanı genericize göçünden kalan `'<SAP_USER>'` dizesiydi ve
    `adtcore:responsible="{responsible}"` özniteliğine KAÇIŞSIZ yazılıyordu ⇒ argümansız
    çağrı iyi biçimli olmayan XML üretiyordu (XML 1.0'da öznitelik değerinde `<` yasak).
  · Kardeş (aynı dosyalar): DTEL/DOMA `adtcore:description` çıplak `xml_escape` ile
    yazılıyordu — `"` kaçmaz, tırnaklı açıklama gövdeyi bozar.
  · Kardeş (`sap_adt_lib`, MCP yolu): `create_object` responsible/description,
    `create_dataelement` responsible/description/etiketler kaçışsız.

FIX: varsayılan `None` → bağlantı kullanıcısı (`utils/xml_kacis.sorumlu_coz`, sap_adt_lib
`responsible or self.user` deseni) · çözülemezse YAZMADAN exit 2 (kütüphanede
`SAPValidationError`) · her öznitelik `utils/xml_kacis.attr_escape` (TEK KAYNAK).

ÖLÇÜM YÜZEYİ: script'lerde GERÇEK giriş noktası `main()` (`--dry-run`); istemci
`SAPADTClient.__new__` ile kurulur (ağ YOK — `session` dokunulursa AssertionError).
Gövde `build_xml` sarmalanarak yakalanır (önizleme 1200/1500 karakterde kesilir).
Kütüphanede gerçek `create_object` / `create_dataelement`; `session.post` gövdeyi kaydeder.
`.conn_adt` OKUNMAZ: modüller geçici dizindeki sahte bağlantı dosyasıyla yüklenir.

KİPLER: taban (argümansız) · `--mutasyon-<ad>` (aşağıdaki GECERLI_KIP; her biri DÜŞECEK
vektörü İLAN eder — ilan edilen düşmezse exit 3) · `--eski-kod <ref>` (negatif koşu:
eski kodda kusurun GÖRÜNDÜĞÜNÜ ölçer; git ister, CI'da sığ klonda koşmaz → elle).

Çıkış: taban 0 = PASS · 1 = FAIL · mutasyon 1 = YAKALANDI · 2 = çapa kurulamadı ·
3 = ilan edilen vektör düşmedi (KAÇTI).
"""
from __future__ import annotations

import csv
import io
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import types
import xml.etree.ElementTree as ET
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[2]
SCRIPTS = CORE / "scripts"
YOLLAR = {
    "pmc": SCRIPTS / "populate_message_class.py",
    "dtel": SCRIPTS / "populate_dataelements.py",
    "doma": SCRIPTS / "populate_domains.py",
    "lib": SCRIPTS / "sap_adt_lib.py",
    "kacis": SCRIPTS / "utils" / "xml_kacis.py",
}
NS_CORE = "{http://www.sap.com/adt/core}"
NS_DTEL = "{http://www.sap.com/adt/dictionary/dataelements}"
TESTUSER = "TESTUSER"
ZOR = 'A&B<x>"y'          # brif değeri `A&B<x>` + tırnak: attr_escape ↔ xml_escape ayrımı
ETIKET = "K&<1"           # eleman metni: `&` ve `<`

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

_mod_refs: list = []      # GC-koruma: modüllerin import anında kurduğu stdout sarmalayıcıları


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


# ---------------------------------------------------------------------------
# Yükleyici: kaynak METNİ (mutasyonlu ya da eski ref) TAZE modüle; gerçek __file__.
# `kacis` metni değiştirilmişse `sys.modules['utils.xml_kacis']`e konur (script'ler ve
# kütüphanenin tembel import'u onu bağlar) ve iş bitince geri alınır.
# ---------------------------------------------------------------------------
_ANAHTAR = "utils.xml_kacis"


def _yukle(anahtar: str, src: str):
    yol = YOLLAR[anahtar]
    saved_out, saved_err = sys.stdout, sys.stderr
    cop_out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    cop_err = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    sys.stdout, sys.stderr = cop_out, cop_err
    try:
        mod = types.ModuleType("_rk_" + anahtar)
        mod.__file__ = str(yol)
        exec(compile(src, str(yol), "exec"), mod.__dict__)
    finally:
        sys.stdout, sys.stderr = saved_out, saved_err
        _mod_refs.append((cop_out, cop_err))
    return mod


def moduller(kaynaklar: dict) -> dict:
    import utils  # noqa: F401 — üst paket yüklü olmalı (sys.modules enjeksiyonu için)
    if "kacis" in kaynaklar:
        sys.modules[_ANAHTAR] = _yukle("kacis", kaynaklar["kacis"])
    return {k: _yukle(k, kaynaklar[k]) for k in ("pmc", "dtel", "doma", "lib")}


# ---------------------------------------------------------------------------
# Sahte istemci (ağ YOK)
# ---------------------------------------------------------------------------
class _Yasak:
    def __getattr__(self, ad):
        raise AssertionError("ag yuzeyine dokunuldu: session.%s" % ad)


def script_istemci(L, user):
    c = L.SAPADTClient.__new__(L.SAPADTClient)
    c.user = user
    c.session = _Yasak()
    return c


class _Yanit:
    status_code = 201
    headers: dict = {}
    text = ""


def lib_istemci(L, user):
    c = L.SAPADTClient.__new__(L.SAPADTClient)
    c.user, c.language, c.url = user, "TR", "https://sahte.invalid"
    c.csrf_token, c.timeout_default = "x", 5
    c.govdeler = []

    def _post(url, headers=None, data=None, params=None, timeout=None):  # noqa: ARG001
        c.govdeler.append(data.decode("utf-8"))
        return _Yanit()

    def _ag(*a, **k):
        raise AssertionError("ag: fetch_csrf_token")

    c.session = types.SimpleNamespace(post=_post)
    c._get_headers = lambda *a, **k: {}
    c._retry_request = lambda f, ad: f()
    c._get_domain_typeinfo = lambda d: ("CHAR", "000010", "000000")
    c.fetch_csrf_token = _ag
    return c


# ---------------------------------------------------------------------------
# main() koşucusu — gövde build_xml sarmalanarak yakalanır
# ---------------------------------------------------------------------------
def kos(mod, L, argv: list, user) -> tuple:
    govdeler: list = []
    asil = mod.build_xml
    mod.build_xml = lambda *a, **k: (govdeler.append(asil(*a, **k)), govdeler[-1])[1]
    mod.SAPADTClient = lambda *a, **k: script_istemci(L, user)
    eski_argv, eski_out = sys.argv[:], sys.stdout
    tut = io.StringIO()
    sys.argv = ["x.py"] + argv
    sys.stdout = tut
    try:
        try:
            rc = mod.main()
        except SystemExit as e:
            rc = e.code if isinstance(e.code, int) else 9
        except BaseException as e:      # çökme != FAIL: ayırt edilebilir kalsın
            rc = "COKTU:%s:%s" % (type(e).__name__, e)
    finally:
        sys.argv, sys.stdout = eski_argv, eski_out
        mod.build_xml = asil
    return rc, tut.getvalue(), govdeler


def ayristir(govde: str):
    """(kök, None) ya da (None, hata)."""
    try:
        return ET.fromstring(govde.encode("utf-8")), None
    except ET.ParseError as e:
        return None, "ParseError: %s" % e


def csv_yaz(tmp: Path, ad: str, baslik: list, satir: list) -> Path:
    p = tmp / ad
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(baslik)
        w.writerow(satir)
    return p


def script_argv(tur: str, tmp: Path, aciklama: str = "Ornek aciklama") -> list:
    if tur == "pmc":
        p = csv_yaz(tmp, "m.csv", ["msgno", "msgtext", "selfexplainatory"],
                    ["001", "Ornek mesaj", "false"])
        return ["--name", "ZSD001", "--package", "ZSD001_CLC", "--transport", "<TRANSPORT>",
                "--description", aciklama, "--messages-csv", str(p), "--dry-run"]
    if tur == "dtel":
        p = csv_yaz(tmp, "e.csv",
                    ["name", "type_kind", "type_name", "datatype", "length", "decimals",
                     "description", "short", "medium", "long", "heading"],
                    ["ZSD001_E_ORNEK", "domain", "ZSD001_D_ORNEK", "CHAR", "10", "0",
                     aciklama, "Kisa", "Orta metin", "Uzun metin", "Baslik metni"])
    else:
        p = csv_yaz(tmp, "d.csv",
                    ["name", "datatype", "length", "decimals", "description", "fixed_values"],
                    ["ZSD001_D_ORNEK", "CHAR", "10", "0", aciklama, ""])
    return ["--package", "ZSD001_CLC", "--transport", "<TRANSPORT>", "--csv", str(p),
            "--dry-run"]


def oznitelik(kok, ad: str):
    return None if kok is None else kok.get(NS_CORE + ad)


# ---------------------------------------------------------------------------
# VEKTÖRLER — ad önekleri MUTASYON ilanlarıyla eşleşir (V1-pmc …, L2 …)
# ---------------------------------------------------------------------------
def senaryolar(M: dict, tmp: Path) -> list:
    out: list = []

    def ekle(ad, kosul, detay=""):
        out.append((ad, bool(kosul), detay))

    L = M["lib"]
    for tur in ("pmc", "dtel", "doma"):
        mod = M[tur]
        d = tmp / tur
        d.mkdir(exist_ok=True)
        # V1 argümansız → bağlantı kullanıcısı
        rc, cikti, g = kos(mod, L, script_argv(tur, d), TESTUSER)
        kok, hata = ayristir(g[0]) if len(g) == 1 else (None, "govde sayisi=%d" % len(g))
        ekle("V1-%s argumansiz: rc 0 + XML ayristirilir + responsible == baglanti kullanicisi"
             % tur, rc == 0 and kok is not None and oznitelik(kok, "responsible") == TESTUSER,
             "rc=%r hata=%s responsible=%r" % (rc, hata, oznitelik(kok, "responsible")))
        # V2 --responsible ZOR → kaçışlı, birebir geri okunur
        rc, cikti, g = kos(mod, L, script_argv(tur, d) + ["--responsible", ZOR], TESTUSER)
        kok, hata = ayristir(g[0]) if len(g) == 1 else (None, "govde sayisi=%d" % len(g))
        ekle("V2-%s --responsible %r: rc 0 + ayristirilir + deger birebir" % (tur, ZOR),
             rc == 0 and kok is not None and oznitelik(kok, "responsible") == ZOR,
             "rc=%r hata=%s responsible=%r" % (rc, hata, oznitelik(kok, "responsible")))
        # V3 kullanıcı çözülemedi → exit 2, gövde YOK
        for etiket, user in (("None", None), ("bosluk", "   ")):
            rc, cikti, g = kos(mod, L, script_argv(tur, d), user)
            ekle("V3-%s kullanici cozulemedi (%s): exit 2 + govde URETILMEDI + mesaj"
                 % (tur, etiket),
                 rc == 2 and not g and "ÇÖZÜLEMEDİ" in cikti,
                 "rc=%r govde=%d cikti=%r" % (rc, len(g), cikti[-200:]))
        # V4 açıklama özniteliği (tırnak dahil) birebir
        rc, cikti, g = kos(mod, L, script_argv(tur, d, aciklama=ZOR), TESTUSER)
        kok, hata = ayristir(g[0]) if len(g) == 1 else (None, "govde sayisi=%d" % len(g))
        ekle("V4-%s description %r: ayristirilir + birebir" % (tur, ZOR),
             rc == 0 and kok is not None and oznitelik(kok, "description") == ZOR,
             "rc=%r hata=%s description=%r" % (rc, hata, oznitelik(kok, "description")))

    # V5 — silme kipi (3. bağlam, PMC): canlıdan gelen HAM responsible TEK kez kaçışlanır
    canli = {"name": "ZSD001", "description": "Paket", "package": "ZSD001_CLC",
             "responsible": ZOR, "masterLanguage": "TR"}
    try:
        govde = M["pmc"].silme_govdesi(canli, ["002"], [("001", "Kalan", "false", "false")])
        kok, hata = ayristir(govde)
    except BaseException as e:
        kok, hata = None, "COKTU:%s" % type(e).__name__
    ekle("V5-pmc silme govdesi: canli responsible birebir (cift kacis YOK)",
         kok is not None and oznitelik(kok, "responsible") == ZOR,
         "hata=%s responsible=%r" % (hata, oznitelik(kok, "responsible")))

    # L — kütüphane (MCP yolu: atom.adt_create_object / composite DTEL → sap_client → bunlar)
    c = lib_istemci(L, TESTUSER)
    try:
        c.create_object("CLAS/OC", "ZCL_ORNEK", "ZSD001_CLC", "Ornek", "/sap/bc/adt/packages/x")
        kok, hata = ayristir(c.govdeler[0])
    except BaseException as e:
        kok, hata = None, "COKTU:%s:%s" % (type(e).__name__, e)
    ekle("L1 create_object responsible yok: baglanti kullanicisi + ayristirilir",
         kok is not None and oznitelik(kok, "responsible") == TESTUSER,
         "hata=%s responsible=%r" % (hata, oznitelik(kok, "responsible")))
    for tip in ("PROG/P", "PROG/I", "INTF/OI", "CLAS/OC"):
        c = lib_istemci(L, TESTUSER)
        try:
            c.create_object(tip, "ZORNEK", "ZSD001_CLC", ZOR, "/sap/bc/adt/packages/x",
                            responsible=ZOR)
            kok, hata = ayristir(c.govdeler[0])
        except BaseException as e:
            kok, hata = None, "COKTU:%s:%s" % (type(e).__name__, e)
        ekle("L2 create_object %s responsible+description %r birebir" % (tip, ZOR),
             kok is not None and oznitelik(kok, "responsible") == ZOR
             and oznitelik(kok, "description") == ZOR,
             "hata=%s r=%r d=%r" % (hata, oznitelik(kok, "responsible"),
                                    oznitelik(kok, "description")))
    c = lib_istemci(L, None)
    try:
        c.create_object("CLAS/OC", "ZCL_ORNEK", "ZSD001_CLC", "Ornek", "/x")
        sonuc = "hata YOK"
    except L.SAPValidationError:
        sonuc = "SAPValidationError"
    except BaseException as e:
        sonuc = "COKTU:%s" % type(e).__name__
    ekle("L3 create_object kullanici cozulemedi: SAPValidationError + POST YOK",
         sonuc == "SAPValidationError" and not c.govdeler,
         "sonuc=%s post=%d" % (sonuc, len(c.govdeler)))
    c = lib_istemci(L, ZOR)
    try:
        c.create_dataelement("ZSD001_E_ORNEK", "ZSD001_D_ORNEK", ZOR, "ZSD001_CLC",
                             short_label=ETIKET, medium_label=ETIKET, long_label=ETIKET,
                             heading_label=ETIKET)
        kok, hata = ayristir(c.govdeler[0])
    except BaseException as e:
        kok, hata = None, "COKTU:%s:%s" % (type(e).__name__, e)
    etiketler = [] if kok is None else [
        (kok.find(".//" + NS_DTEL + a) is not None and kok.find(".//" + NS_DTEL + a).text)
        for a in ("shortFieldLabel", "mediumFieldLabel", "longFieldLabel", "headingFieldLabel")]
    ekle("L4 create_dataelement responsible/description/etiketler birebir",
         kok is not None and oznitelik(kok, "responsible") == ZOR
         and oznitelik(kok, "description") == ZOR and etiketler == [ETIKET] * 4,
         "hata=%s r=%r d=%r etiket=%r" % (hata, oznitelik(kok, "responsible"),
                                          oznitelik(kok, "description"), etiketler))
    c = lib_istemci(L, None)
    try:
        c.create_dataelement("ZSD001_E_ORNEK", "ZSD001_D_ORNEK", "Ornek", "ZSD001_CLC")
        sonuc = "hata YOK"
    except L.SAPValidationError:
        sonuc = "SAPValidationError"
    except BaseException as e:
        sonuc = "COKTU:%s" % type(e).__name__
    ekle("L5 create_dataelement kullanici cozulemedi: SAPValidationError + POST YOK",
         sonuc == "SAPValidationError" and not c.govdeler,
         "sonuc=%s post=%d" % (sonuc, len(c.govdeler)))
    return out


# ---------------------------------------------------------------------------
# MUTASYONLAR — (hedef, eski, yeni, DÜŞECEK vektör öneki). Çapa TAM bir kez eşleşmeli.
# ---------------------------------------------------------------------------
_DUR = "    if responsible is None:\n        print(SORUMLU_YOK_MESAJI)\n        return 2\n"
_DUR_YOK = "    if False:\n        print(SORUMLU_YOK_MESAJI)\n        return 2\n"
_RESP = 'adtcore:responsible="{attr_escape(responsible)}"'
_RESP_CIPLAK = 'adtcore:responsible="{responsible}"'
_ACIK = 'adtcore:description="{attr_escape(description)}"\n'
_ACIK_XE = 'adtcore:description="{xml_escape(description)}"\n'
_ARG = "    parser.add_argument('--responsible', default=None,\n"
_ARG_ESKI = "    parser.add_argument('--responsible', default='<SAP_USER>',\n"

MUTASYON = {
    "--mutasyon-pmc-kacis": ("pmc", _RESP, _RESP_CIPLAK, "V2-pmc"),
    "--mutasyon-dtel-kacis": ("dtel", _RESP, _RESP_CIPLAK, "V2-dtel"),
    "--mutasyon-doma-kacis": ("doma", _RESP, _RESP_CIPLAK, "V2-doma"),
    "--mutasyon-dtel-aciklama": ("dtel", _ACIK, _ACIK_XE, "V4-dtel"),
    "--mutasyon-doma-aciklama": ("doma", _ACIK, _ACIK_XE, "V4-doma"),
    "--mutasyon-pmc-varsayilan": ("pmc", _ARG, _ARG_ESKI, "V1-pmc"),
    "--mutasyon-dtel-varsayilan": ("dtel", _ARG, _ARG_ESKI, "V1-dtel"),
    "--mutasyon-doma-varsayilan": ("doma", _ARG, _ARG_ESKI, "V1-doma"),
    "--mutasyon-pmc-dur": ("pmc", _DUR, _DUR_YOK, "V3-pmc"),
    "--mutasyon-dtel-dur": ("dtel", _DUR, _DUR_YOK, "V3-dtel"),
    "--mutasyon-doma-dur": ("doma", _DUR, _DUR_YOK, "V3-doma"),
    "--mutasyon-coz-sessiz": ("kacis", "        return None\n    return deger\n",
                              "        return '<SAP_USER>'\n    return deger\n", "V3-pmc"),
    "--mutasyon-pmc-cift-kacis": ("pmc", "                     canli['responsible'], kalan,\n",
                                  "                     attr_escape(canli['responsible']), kalan,\n",
                                  "V5-pmc"),
    "--mutasyon-lib-obje-sorumlu": ("lib", "        responsible_xml = attr_escape(sorumlu)\n",
                                    "        responsible_xml = sorumlu\n", "L2"),
    "--mutasyon-lib-obje-aciklama": ("lib", "        description_xml = attr_escape(description or '')\n",
                                     "        description_xml = description\n", "L2"),
    "--mutasyon-lib-obje-dur": ("lib", "        sorumlu = sorumlu_coz(responsible, self)\n"
                                       "        if sorumlu is None:\n",
                                "        sorumlu = sorumlu_coz(responsible, self)\n"
                                "        if False:\n", "L3"),
    "--mutasyon-lib-dtel-sorumlu": ("lib", '<blue:wbobj adtcore:responsible="{attr_escape(sorumlu)}"',
                                    '<blue:wbobj adtcore:responsible="{sorumlu}"', "L4"),
    "--mutasyon-lib-dtel-aciklama": ("lib", '            adtcore:description="{attr_escape(description)}"\n',
                                     '            adtcore:description="{description}"\n', "L4"),
    "--mutasyon-lib-etiket": ("lib", "<dtel:shortFieldLabel>{_xe(short_label)}</dtel:shortFieldLabel>",
                              "<dtel:shortFieldLabel>{short_label}</dtel:shortFieldLabel>", "L4"),
    "--mutasyon-lib-dtel-dur": ("lib", "        sorumlu = sorumlu_coz(None, self)\n"
                                       "        if sorumlu is None:\n",
                                "        sorumlu = sorumlu_coz(None, self)\n"
                                "        if False:\n", "L5"),
}
# Beyan (run_battery keşif katmanı ①): sıra = koşum sırası; ilk kip git İSTEMEZ.
GECERLI_KIP = (
    "--mutasyon-pmc-kacis", "--mutasyon-dtel-kacis", "--mutasyon-doma-kacis",
    "--mutasyon-dtel-aciklama", "--mutasyon-doma-aciklama",
    "--mutasyon-pmc-varsayilan", "--mutasyon-dtel-varsayilan", "--mutasyon-doma-varsayilan",
    "--mutasyon-pmc-dur", "--mutasyon-dtel-dur", "--mutasyon-doma-dur",
    "--mutasyon-coz-sessiz", "--mutasyon-pmc-cift-kacis",
    "--mutasyon-lib-obje-sorumlu", "--mutasyon-lib-obje-aciklama", "--mutasyon-lib-obje-dur",
    "--mutasyon-lib-dtel-sorumlu", "--mutasyon-lib-dtel-aciklama", "--mutasyon-lib-etiket",
    "--mutasyon-lib-dtel-dur",
)
assert set(GECERLI_KIP) == set(MUTASYON), "GECERLI_KIP ile MUTASYON ayni kume olmali"


def diskten() -> dict:
    return {k: p.read_text(encoding="utf-8") for k, p in YOLLAR.items()}


def git_show(ref: str, yol: Path) -> str | None:
    rel = yol.relative_to(CORE).as_posix()
    r = subprocess.run(["git", "-C", str(CORE), "show", "%s:%s" % (ref, rel)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else None


def kum_kur() -> tuple:
    """Sahte bağlantı dosyalı geçici dizin; modüller `.conn_adt`'i BURADAN okur."""
    for k in [k for k in os.environ if k.startswith("ADT_SAP_")]:
        os.environ.pop(k, None)
    kum = Path(tempfile.mkdtemp(prefix="resp_kacis_"))
    (kum / ".conn_adt").write_text(
        "ADT_SAP_URL=https://sahte.invalid\nADT_SAP_USER=%s\nADT_SAP_PASSWORD=x\n"
        "ADT_SAP_CLIENT=100\nADT_SAP_LANGUAGE=TR\n" % TESTUSER, encoding="utf-8")
    eski = (os.getcwd(), os.environ.get("CLAUDE_PROJECT_DIR"))
    os.environ["CLAUDE_PROJECT_DIR"] = str(kum)
    os.chdir(kum)
    return kum, eski


def kum_kaldir(kum: Path, eski: tuple) -> None:
    os.chdir(eski[0])
    if eski[1] is None:
        os.environ.pop("CLAUDE_PROJECT_DIR", None)
    else:
        os.environ["CLAUDE_PROJECT_DIR"] = eski[1]
    _sil(kum)


def bas(sonuc: list, ayrinti: bool = False) -> int:
    kirik = [a for a, ok, _ in sonuc if not ok]
    for ad, ok, detay in sonuc:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok or ayrinti:
            print("         gorulen: %s" % detay)
    print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))
    return len(kirik)


def eski_kod(ref: str, tmp: Path) -> int:
    """NEGATİF KOŞU: eski kodda argümansız script gövdesi AYRIŞTIRILAMAZ olmalı."""
    print("### ESKI KOD @ %s — kusur GORUNMELI (yesil = kusur dogrulandi)" % ref)
    kaynak = diskten()
    for k in ("pmc", "dtel", "doma", "lib"):
        s = git_show(ref, YOLLAR[k])
        if s is None:
            print("[DOGRULANAMADI] git show %s:%s okunamadi (sig klon?)" % (ref, k))
            return 2
        if "sorumlu_coz" in s:
            print("[DOGRULANAMADI] %s @ %s ZATEN fix'li — taban gecersiz" % (k, ref))
            return 2
        kaynak[k] = s
    kaynak.pop("kacis")              # eski kodda bu modul yok/kullanilmaz
    M = moduller(kaynak)
    L = M["lib"]
    sonuc = []
    for tur in ("pmc", "dtel", "doma"):
        d = tmp / ("eski_" + tur)
        d.mkdir(exist_ok=True)
        rc, cikti, g = kos(M[tur], L, script_argv(tur, d), TESTUSER)
        hata = ayristir(g[0])[1] if len(g) == 1 else "govde sayisi=%d" % len(g)
        sonuc.append(("E1-%s argumansiz: ESKI kodda govde AYRISTIRILAMAZ" % tur,
                      rc == 0 and hata is not None and hata.startswith("ParseError"),
                      "rc=%r hata=%s" % (rc, hata)))
    c = lib_istemci(L, TESTUSER)
    try:
        c.create_object("CLAS/OC", "ZORNEK", "ZSD001_CLC", ZOR, "/x", responsible=ZOR)
        hata = ayristir(c.govdeler[0])[1]
    except BaseException as e:
        hata = "COKTU:%s" % type(e).__name__
    sonuc.append(("E2-lib create_object ZOR: ESKI kodda govde AYRISTIRILAMAZ",
                  hata is not None and hata.startswith("ParseError"), "hata=%s" % hata))
    return 1 if bas(sonuc, ayrinti=True) else 0


def main(argv: list) -> int:
    print("=" * 78)
    print("responsible_kacis — Issue #339 (responsible yer tutucusu + oznitelik kacisi)")
    print("=" * 78)
    kip = argv[0] if argv else None
    if kip not in (None, "--eski-kod") and kip not in MUTASYON:
        print("[KULLANIM] gecersiz kip %r; gecerli: %s · --eski-kod <ref>" % (kip, GECERLI_KIP))
        return 2
    kum, eski = kum_kur()
    try:
        tmp = kum / "csv"
        tmp.mkdir()
        if kip == "--eski-kod":
            if len(argv) < 2:
                print("[KULLANIM] --eski-kod <ref>")
                return 2
            return eski_kod(argv[1], tmp)
        kaynak = diskten()
        if kip is None:
            return 1 if bas(senaryolar(moduller(kaynak), tmp)) else 0
        hedef, e, y, ilan = MUTASYON[kip]
        n = kaynak[hedef].count(e)
        if n != 1:
            print("[DOGRULANAMADI] %s — capa %d kez eslesti (1 olmali)" % (kip, n))
            return 2
        kaynak[hedef] = kaynak[hedef].replace(e, y, 1)
        print("### MUTASYON %s → hedef=%s · ILAN: '%s' DUSMELI" % (kip, hedef, ilan))
        sonuc = senaryolar(moduller(kaynak), tmp)
        bas(sonuc)
        dusen = [a for a, ok, _ in sonuc if not ok and a.startswith(ilan)]
        if dusen:
            print("[YAKALANDI] ilan edilen vektor dustu: %s" % dusen[0])
            return 1
        print("[KACTI] ilan edilen vektor '%s' DUSMEDI" % ilan)
        return 3
    finally:
        sys.modules.pop(_ANAHTAR, None)
        kum_kaldir(kum, eski)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
