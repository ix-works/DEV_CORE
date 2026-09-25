#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""revizyon_okuma — `SAPADTClient.get_object_revisions` sürüm geçmişini okur; "okuyamadım" ≠ "sürüm yok" (Issue #302).

CANLI ÖLÇÜLEN MEKANİZMA (2026-09-25, s4_private DEV, salt-okur GET; sınıf · program include'u · arayüz):
  · obje GET'i `Accept: application/vnd.sap.adt.objectstructure+xml` ve `application/xml` ile 406,
    `*/*` ile 200 döner
  · sürüm bağlantısı `<atom:link … rel="http://www.sap.com/adt/relations/versions">` — `atom:` önekli,
    href GÖRELİ (`source/main/versions`); sınıfta 4 bağlantı (`includes/definitions|implementations|
    macros|main/versions`), ana kaynak `includes/main/versions` (sınıfta `source/main/versions` 404)
  · feed (`application/atom+xml;type=feed`) 200, `<atom:entry>` başına bir sürüm
  · göreli href İKİ biçimli (6 tip ölçüldü, hiçbirinde `xml:base` yok): `./<obje_adı>/source/main/versions`
    (BDEF · tablo `blue:blueSource` · SRVD) RFC çözümüyle (ebeveyn-göreli) `<obje>/source/main/versions`;
    diğer göreli (`source/main/versions` · `includes/main/versions` · DDLS `versions`) obje URL'inin ALTINA
    — RFC çözümü bunlarda YANLIŞ (ebeveyne düşer, 404)
ESKİ KOD: 406'yı, çözülmeyen bağlantıyı ve her istisnayı `[]` yapıyordu ⇒ çağıran "sürüm yok" sanıyordu
(canlıda üç obje tipinde 0/0/0 kayıt; düzeltmeyle 1/1/1).

SÖZLEŞME: `[]` YALNIZ iki meşru boşta (obje sürüm bağlantısı taşımıyor · geçerli Atom feed'i 0 entry).
404 → SAPObjectNotFoundError. Okunamayan her şey (200-dışı · ağ hatası · 200 ama XML/feed olmayan gövde ·
tanınmayan entry biçimi) → SAPADTError.

İKİ KATMAN:
  · V-vektörleri: fonksiyon süreç İÇİNDE, sahte `session` ile (SAP'siz).
  · L-vektörleri: GERÇEK çağıran `scripts/list_revisions.py` AYRI süreçte koşar; `sap_client` sahte
    modülle değiştirilir, `adt_client` = test edilen kaynaktan kurulmuş gerçek `SAPADTClient` + sahte
    oturum. Alt süreç boş bir kum dizininde koşar (`.conn_adt` yüklenmez).

KULLANIM:
    python tests/fixtures/revizyon_okuma/run.py        # vektörler + mutasyonlar, exit 0
    python tests/fixtures/revizyon_okuma/run.py --kaynak <sap_adt_lib> [--lr-kaynak <list_revisions>]
        # vektörleri BAŞKA kaynakta koş (mutasyon yok) — eski kod karşıtlığı:
        #   git show <taban>:scripts/sap_adt_lib.py > <kum>/eski_lib.py
        #   git show <taban>:scripts/list_revisions.py > <kum>/eski_lr.py
        #   → --kaynak <kum>/eski_lib.py --lr-kaynak <kum>/eski_lr.py
        # beklenen: yalnız KONTROL grubu (V4 · V5 · V6 · V21 · L3) geçer.
⚠ V4/V5/V6/V21/L3 KONTROL GRUBU — silinmez (meşru boş/yok da istisnaya çevrilirse onlar kırılır).
Mutasyonlar yalnız `get_object_revisions` gövdesinde (segment-kapsamlı çapa, tam 1 eşleşme) ve
`list_revisions.py`'de uygulanır; kaynak dosyalara YAZILMAZ (bellekte / geçici kum).
"""
from __future__ import annotations

import os
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

KOK = Path(__file__).resolve().parents[3]
HEDEF = KOK / "scripts" / "sap_adt_lib.py"
LR = KOK / "scripts" / "list_revisions.py"
if not HEDEF.is_file() or not LR.is_file():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {KOK}")
sys.path.insert(0, str(KOK / "scripts"))

import requests  # noqa: E402

BASE = "https://sahte.example:44300"
SINIF = "/sap/bc/adt/oo/classes/zdemo_cl_ornek"
ARAYUZ = "/sap/bc/adt/oo/interfaces/zif_demo_ornek"
REL = 'rel="http://www.sap.com/adt/relations/versions"'
HTML = "<!DOCTYPE html><html><body>Logon</body></html>"


def _link(href, rel_once=False, onek="atom:"):
    if rel_once:
        return f'<{onek}link {REL} href="{href}" xmlns:atom="http://www.w3.org/2005/Atom"/>'
    return f'<{onek}link href="{href}" {REL} xmlns:atom="http://www.w3.org/2005/Atom"/>'


def _obje(linkler, kok="class:abapClass", ns='xmlns:class="http://www.sap.com/adt/oo/classes"'):
    return (f'<?xml version="1.0" encoding="utf-8"?><{kok} {ns}>'
            + "".join(linkler) + '<atom:link href="source/main" rel="http://www.sap.com/adt/relations/source"/>'
            f'</{kok}>')


def _feed(n, entry_ac="<atom:entry>"):
    girdiler = "".join(
        f'{entry_ac}<atom:author><atom:name>SAHTE_KULLANICI</atom:name></atom:author>'
        f'<atom:content type="text/plain" src="/x/versions/{i}/content"/><atom:id>0000{i}</atom:id>'
        f'<atom:updated>2026-01-0{i + 1}T00:00:00Z</atom:updated></atom:entry>' for i in range(n))
    return f'<?xml version="1.0" encoding="utf-8"?><atom:feed xmlns:atom="http://www.w3.org/2005/Atom">{girdiler}</atom:feed>'


# öneksiz (varsayılan ad alanlı) Atom — bu ayrıştırıcı entry'leri TANIMAZ ⇒ "boş" değil, okunamadı
ONEKSIZ_FEED = ('<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom">'
                '<entry><id>00001</id><updated>2026-01-01T00:00:00Z</updated></entry></feed>')


class _Yanit:
    def __init__(self, kod, govde=""):
        self.status_code = kod
        self.text = govde


class _Oturum:
    """objeler: {yol: gövde}; feedler: {yol: (kod, gövde)}; ag_hatasi: False | 'hepsi' | 'feed'."""

    def __init__(self, objeler, feedler, obje_kodu=None, ag_hatasi=False):
        self.objeler, self.feedler = objeler, feedler
        self.obje_kodu, self.ag_hatasi = obje_kodu, ag_hatasi
        self.istekler = []

    def get(self, url, headers=None, timeout=None, **kw):
        yol = url[len(BASE):] if url.startswith(BASE) else url
        acc = (headers or {}).get("Accept", "")
        self.istekler.append((yol, acc))
        if self.ag_hatasi == "hepsi" or (self.ag_hatasi == "feed" and yol in self.feedler):
            raise requests.exceptions.ConnectionError("sahte: ad cozulemedi")
        if yol in self.objeler:
            if self.obje_kodu:
                return _Yanit(self.obje_kodu, "sahte hata")
            if acc != "*/*":  # canlı ölçüm: objectstructure+xml / application/xml → 406
                return _Yanit(406, "Not Acceptable")
            return _Yanit(200, self.objeler[yol])
        if yol in self.feedler:
            kod, govde = self.feedler[yol]
            return _Yanit(kod, govde)
        return _Yanit(404, "not found")


SINIF_LINKLERI = [_link(f"includes/{a}/versions") for a in ("definitions", "implementations", "macros", "main")]
AR_FEED = ARAYUZ + "/source/main/versions"
# BDEF / tablo (`blue:blueSource`) / SRVD biçimi: href `./<obje_adı>/source/main/versions` — RFC çözümü
# (ebeveyn-göreli) `<obje>/source/main/versions` verir; "obje altına ekle" `<obje>/./<ad>/…` → 404.
BDEF = "/sap/bc/adt/bo/behaviordefinitions/zdemo_r_ornek"
BDEF_NS = 'xmlns:blue="http://www.sap.com/wbobj/blue"'
DDLS = "/sap/bc/adt/ddic/ddl/sources/zdemo_i_ornek"

VEKTORLER = [
    ("V1 sinif: 4 atom:link, goreli, ana kaynak SONDA -> includes/main feed'i (2 surum)",
     dict(objeler={SINIF: _obje(SINIF_LINKLERI)},
          feedler={SINIF + "/includes/main/versions": (200, _feed(2))}, url=SINIF),
     ("sayi", 2)),
    ("V2 arayuz: tek goreli source/main/versions (1 surum)",
     dict(objeler={ARAYUZ: _obje([_link("source/main/versions")])},
          feedler={AR_FEED: (200, _feed(1))}, url=ARAYUZ),
     ("sayi", 1)),
    ("V3 onek'siz <link>, rel href'ten ONCE, kok-goreli mutlak yol",
     dict(objeler={ARAYUZ: _obje([_link(AR_FEED, rel_once=True, onek="")])},
          feedler={AR_FEED: (200, _feed(3))}, url=ARAYUZ),
     ("sayi", 3)),
    ("V4 KONTROL: surum baglantisi yok -> mesru []",
     dict(objeler={ARAYUZ: _obje([])}, feedler={}, url=ARAYUZ), ("sayi", 0)),
    ("V5 KONTROL: gecerli atom:feed, 0 entry -> mesru []",
     dict(objeler={ARAYUZ: _obje([_link("source/main/versions")])},
          feedler={AR_FEED: (200, _feed(0))}, url=ARAYUZ),
     ("sayi", 0)),
    ("V6 KONTROL: obje yok (404) -> SAPObjectNotFoundError",
     dict(objeler={}, feedler={}, url=ARAYUZ), ("istisna", "SAPObjectNotFoundError", 404)),
    ("V7 obje GET 406 -> SAPADTError (sessiz [] DEGIL)",
     dict(objeler={ARAYUZ: _obje([])}, feedler={}, url=ARAYUZ, obje_kodu=406),
     ("istisna", "SAPADTError", 406)),
    ("V8 feed 500 -> SAPADTError (sessiz [] DEGIL)",
     dict(objeler={ARAYUZ: _obje([_link("source/main/versions")])},
          feedler={AR_FEED: (500, "dump")}, url=ARAYUZ),
     ("istisna", "SAPADTError", 500)),
    ("V9 obje isteginde ag hatasi -> SAPADTError (sessiz [] DEGIL)",
     dict(objeler={ARAYUZ: _obje([])}, feedler={}, url=ARAYUZ, ag_hatasi="hepsi"),
     ("istisna", "SAPADTError", None)),
    ("V10 feed isteginde ag hatasi -> SAPADTError (sessiz [] DEGIL)",
     dict(objeler={ARAYUZ: _obje([_link("source/main/versions")])},
          feedler={AR_FEED: (200, _feed(1))}, url=ARAYUZ, ag_hatasi="feed"),
     ("istisna", "SAPADTError", None)),
    ("V11 obje 200 ama HTML (giris sayfasi) -> SAPADTError, 'baglanti yok' DEGIL",
     dict(objeler={ARAYUZ: HTML}, feedler={}, url=ARAYUZ),
     ("istisna", "SAPADTError", 200)),
    ("V12 feed 200 ama HTML -> SAPADTError, 'bos feed' DEGIL",
     dict(objeler={ARAYUZ: _obje([_link("source/main/versions")])},
          feedler={AR_FEED: (200, HTML)}, url=ARAYUZ),
     ("istisna", "SAPADTError", 200)),
    ("V13 feed entry'leri taninmayan bicimde (oneksiz <entry>) -> SAPADTError",
     dict(objeler={ARAYUZ: _obje([_link("source/main/versions")])},
          feedler={AR_FEED: (200, ONEKSIZ_FEED)}, url=ARAYUZ),
     ("istisna", "SAPADTError", 200)),
    ("V14 oznitelikli <atom:entry xml:lang> TANINIR (2 surum)",
     dict(objeler={ARAYUZ: _obje([_link("source/main/versions")])},
          feedler={AR_FEED: (200, _feed(2, entry_ac='<atom:entry xml:lang="EN">'))}, url=ARAYUZ),
     ("sayi", 2)),
    ("V15 http(s) mutlak href aynen kullanilir (1 surum)",
     dict(objeler={ARAYUZ: _obje([_link(BASE + AR_FEED)])},
          feedler={AR_FEED: (200, _feed(1))}, url=ARAYUZ),
     ("sayi", 1)),
    ("V16 BDEF/tablo bicimi './<ad>/source/main/versions' -> RFC cozumu <obje>/source/main/versions (2 surum)",
     dict(objeler={BDEF: _obje([_link("./zdemo_r_ornek/source/main/versions")],
                               kok="blue:blueSource", ns=BDEF_NS)},
          feedler={BDEF + "/source/main/versions": (200, _feed(2))}, url=BDEF),
     ("sayi", 2)),
    ("V17 DDLS bicimi 'versions' (main'siz) -> obje ALTINA <obje>/versions (1 surum)",
     dict(objeler={DDLS: _obje([_link("versions")], kok="ddl:ddlSource",
                               ns='xmlns:ddl="http://www.sap.com/adt/ddic/ddlsources"')},
          feedler={DDLS + "/versions": (200, _feed(1))}, url=DDLS),
     ("sayi", 1)),
    ("V18 surum iliskisi var ama TEK TIRNAKLI oznitelik (ayristirilamaz) -> SAPADTError, 'baglanti yok' DEGIL",
     dict(objeler={ARAYUZ: _obje(["<atom:link href='source/main/versions' "
                                  "rel='http://www.sap.com/adt/relations/versions'/>"])},
          feedler={AR_FEED: (200, _feed(1))}, url=ARAYUZ),
     ("istisna", "SAPADTError", 200)),
    ("V19 surum iliskisi var ama 'atom:' disi onek (<a:link>) -> SAPADTError",
     dict(objeler={ARAYUZ: _obje([_link("source/main/versions", onek="a:")])},
          feedler={AR_FEED: (200, _feed(1))}, url=ARAYUZ),
     ("istisna", "SAPADTError", 200)),
    ("V20 './' bicimi + obje URL'i SONDA '/' ile -> ad iki kez eklenmez (2 surum)",
     dict(objeler={BDEF + "/": _obje([_link("./zdemo_r_ornek/source/main/versions")],
                                     kok="blue:blueSource", ns=BDEF_NS)},
          feedler={BDEF + "/source/main/versions": (200, _feed(2))}, url=BDEF + "/"),
     ("sayi", 2)),
    ("V21 KONTROL: oneksiz (varsayilan ad alanli) BOS feed <feed xmlns=Atom></feed> -> mesru []",
     dict(objeler={ARAYUZ: _obje([_link("source/main/versions")])},
          feedler={AR_FEED: (200, '<?xml version="1.0" encoding="utf-8"?>'
                                  '<feed xmlns="http://www.w3.org/2005/Atom"></feed>')}, url=ARAYUZ),
     ("sayi", 0)),
]

CLI_SENARYOLARI = {
    "L1": dict(objeler={SINIF: _obje(SINIF_LINKLERI)},
               feedler={SINIF + "/includes/main/versions": (200, _feed(2))}, url=SINIF),
    "L2": dict(objeler={ARAYUZ: _obje([])}, feedler={}, url=ARAYUZ, obje_kodu=406),
    "L3": dict(objeler={ARAYUZ: _obje([])}, feedler={}, url=ARAYUZ),
}
TERS_BOLU_N = "\\" + "n"  # ekranda LITERAL ters-bölü + n (kaçış hatası izi)
CLI_VEKTORLER = [
    ("L1 CLI: surum var -> rc 0 + 'Revision History' + ekranda literal \\n YOK", "L1",
     lambda rc, o: rc == 0 and "Revision History" in o and "Revision 2:" in o and TERS_BOLU_N not in o),
    ("L2 CLI: obje 406 -> rc 1 + [FAIL] (sessiz 'No revisions' DEGIL)", "L2",
     lambda rc, o: rc == 1 and "[FAIL]" in o and "No revisions" not in o),
    ("L3 CLI KONTROL: baglanti yok -> rc 0 + '[INFO] No revisions'", "L3",
     lambda rc, o: rc == 0 and "[INFO] No revisions found" in o),
]

# (ad, eski, yeni) — çapa get_object_revisions gövdesinde TAM 1 kez geçmeli
MUTASYONLAR = [
    ("M1 obje GET eski Accept'e dondu",
     "headers['Accept'] = '*/*'", "headers['Accept'] = 'application/vnd.sap.adt.objectstructure+xml'"),
    ("M2 atom: oneki taninmiyor", r"r'<(?:atom:)?link\b([^>]*)>'", r"r'<link\b([^>]*)>'"),
    ("M3 goreli href cozulmuyor",
     "revisions_url = f\"{self.url}{object_url.rstrip('/')}/{revisions_href}\"",
     "revisions_url = revisions_href"),
    ("M4 ana kaynak secimi yok (ilk baglanti)",
     "revisions_href = main_hrefs[0] if main_hrefs else hrefs[0]", "revisions_href = hrefs[0]"),
    ("M5 obje 200-disi sessiz []",
     "        if response.status_code != 200:\n            raise SAPADTError(\n"
     "                f\"Object could not be read for revisions:",
     "        if response.status_code != 200:\n            return []\n            raise SAPADTError(\n"
     "                f\"Object could not be read for revisions:"),
    ("M6 feed 200-disi sessiz []",
     "        if response.status_code != 200:\n            raise SAPADTError(\n"
     "                f\"Revisions feed could not be read:",
     "        if response.status_code != 200:\n            return []\n            raise SAPADTError(\n"
     "                f\"Revisions feed could not be read:"),
    ("M7 obje ag hatasi sessiz []",
     "        except requests.exceptions.RequestException as e:\n            raise SAPADTError(\n"
     "                f\"Object could not be read for revisions:",
     "        except requests.exceptions.RequestException as e:\n            return []\n"
     "            raise SAPADTError(\n                f\"Object could not be read for revisions:"),
    ("M8 feed ag hatasi sessiz []",
     "        except requests.exceptions.RequestException as e:\n            raise SAPADTError(\n"
     "                f\"Revisions feed could not be read:",
     "        except requests.exceptions.RequestException as e:\n            return []\n"
     "            raise SAPADTError(\n                f\"Revisions feed could not be read:"),
    ("M9 404 dali yok (yokluk genel hataya karisir)",
     "if response.status_code == 404:", "if False:"),
    ("M10 obje XML kapisi yok (HTML 'baglanti yok' sayilir)",
     r"if not re.match(r'\s*<(?:\?xml\b", r"if False and not re.match(r'\s*<(?:\?xml\b"),
    ("M11 feed kok kapisi yok (HTML 'bos feed' sayilir)",
     r"if not re.search(r'<(?:[\w.-]+:)?feed\b', response.text):", "if False:"),
    ("M12 taninmayan entry kapisi yok",
     r"if re.search(r'<(?:[\w.-]+:)?entry\b', response.text):", "if False:"),
    ("M13 oznitelikli entry taninmiyor (eski desen)",
     r"r'<atom:entry\b[^>]*>(.*?)</atom:entry>'", r"r'<atom:entry>(.*?)</atom:entry>'"),
    ("M14 './' dali yok (BDEF/tablo href'i obje altina eklenir -> 404)",
     "elif revisions_href.startswith('./'):", "elif False:"),
    ("M15 TUM goreli href'ler RFC-cozumlu (obje=dizin bicimi ebeveyne duser)",
     "revisions_url = f\"{self.url}{object_url.rstrip('/')}/{revisions_href}\"",
     "revisions_url = f\"{self.url}{__import__('urllib.parse').parse.urljoin(object_url, revisions_href)}\""),
    ("M16 ayristirilamayan surum iliskisi sessiz [] (F1 geri)",
     "if 'relations/versions' in response.text:", "if False:"),
    ("M17 './' dalinda sondaki '/' soyulmuyor (F2 geri)",
     "urljoin(object_url.rstrip('/'), revisions_href)", "urljoin(object_url, revisions_href)"),
    ("M18 feed kok kapisi yalniz 'atom:' onekine daraldi",
     r"if not re.search(r'<(?:[\w.-]+:)?feed\b', response.text):",
     r"if not re.search(r'<atom:feed\b', response.text):"),
]
# list_revisions.py mutasyonları (çapa dosyada TAM 1 kez)
LR_MUTASYONLAR = [
    ("ML1 list_revisions ust ayirici literal \\n'e dondu",
     r'''print(f"\n{'='*80}")''', r'''print(f"\\n{'='*80}")'''),
    ("ML2 list_revisions alt ayirici literal \\n'e dondu",
     r'''print(f"{'='*80}\n")''', r'''print(f"{'='*80}\\n")'''),
]

SEG_BAS = "    def get_object_revisions("
SEG_SON = "    def fetch_source_etag("


def _mutant_lib(ham: str, eski: str, yeni: str):
    """Yalnız get_object_revisions gövdesinde değiştir. (metin | None, çapa sayısı)."""
    bas = ham.find(SEG_BAS)
    son = ham.find(SEG_SON, bas + 1) if bas >= 0 else -1
    if bas < 0 or son < 0:
        return None, -1
    seg = ham[bas:son]
    adet = seg.count(eski)
    if adet != 1:
        return None, adet
    return ham[:bas] + seg.replace(eski, yeni) + ham[son:], 1


def _modul(kaynak_metni: str):
    """Kaynak METNİ her zaman gerçek `__file__` ile exec edilir (kardeş import'lar gerçek dizinden)."""
    m = types.ModuleType("sap_adt_lib")
    m.__file__ = str(HEDEF)
    exec(compile(kaynak_metni, str(HEDEF), "exec"), m.__dict__)
    return m


def _istemci(mod, kur):
    c = object.__new__(mod.SAPADTClient)
    c.url = BASE
    c.timeout_short = 5
    c.debug_enabled = False
    c._get_headers = lambda: {}
    c.session = _Oturum(kur["objeler"], kur["feedler"], kur.get("obje_kodu"), kur.get("ag_hatasi", False))
    return c


def _kos_vektor(mod, kur):
    try:
        return ("sayi", len(_istemci(mod, kur).get_object_revisions(kur["url"])))
    except Exception as e:  # noqa: BLE001 — tür hükmün parçası
        return ("istisna", type(e).__name__, getattr(e, "status_code", None))


def _lib_degerlendir(mod):
    sonuc = []
    for ad, kur, beklenen in VEKTORLER:
        gorulen = _kos_vektor(mod, kur)
        sonuc.append((ad, gorulen == beklenen, f"beklenen {beklenen} · gorulen {gorulen}"))
    return sonuc


def _cli_degerlendir(lib_metni: str, lr_metni: str):
    """L-vektörleri: gerçek list_revisions.py ayrı süreçte; kum dizini boş (conn yüklenmez)."""
    kum = Path(tempfile.mkdtemp(prefix="revizyon_okuma_"))
    try:
        (kum / "lib.py").write_bytes(lib_metni.encode("utf-8"))
        (kum / "lr.py").write_bytes(lr_metni.encode("utf-8"))
        env = dict(os.environ)
        for k in ("CLAUDE_CWD", "INIT_CWD", "COPILOT_CWD"):
            env.pop(k, None)
        env["CLAUDE_PROJECT_DIR"] = str(kum)
        env["PYTHONIOENCODING"] = "utf-8"
        sonuc = []
        for ad, senaryo, olcut in CLI_VEKTORLER:
            p = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--cli", senaryo,
                 "--lib", str(kum / "lib.py"), "--lr", str(kum / "lr.py")],
                cwd=str(kum), env=env, capture_output=True, timeout=120)
            cikti = (p.stdout + p.stderr).decode("utf-8", errors="replace")
            ok = olcut(p.returncode, cikti)
            sonuc.append((ad, ok, f"rc={p.returncode} cikti_sonu={cikti.strip()[-300:]!r}"))
        return sonuc
    finally:
        shutil.rmtree(kum, ignore_errors=True)


def _cli_surucu(senaryo: str, lib_yolu: str, lr_yolu: str) -> None:
    """Alt süreç: sahte sap_client + test edilen lib ile GERÇEK list_revisions.py'yi koşar."""
    mod = _modul(Path(lib_yolu).read_text(encoding="utf-8"))
    sys.modules["sap_adt_lib"] = mod
    kur = CLI_SENARYOLARI[senaryo]

    class SAPClient:  # list_revisions'in kullandığı tek yüzey: .adt_client
        def __init__(self):
            self.adt_client = _istemci(mod, kur)

    sahte = types.ModuleType("sap_client")
    sahte.SAPClient = SAPClient
    sys.modules["sap_client"] = sahte
    sys.argv = [str(LR), "--url", kur["url"]]
    lr_metni = Path(lr_yolu).read_text(encoding="utf-8")
    exec(compile(lr_metni, str(LR), "exec"), {"__name__": "__main__", "__file__": str(LR)})


def _yaz(baslik, deger):
    print(baslik)
    for ad, ok, detay in deger:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
        if not ok:
            print(f"         {detay}")


def _arg(ad):
    return sys.argv[sys.argv.index(ad) + 1] if ad in sys.argv else None


def main() -> int:
    if "--cli" in sys.argv:
        _cli_surucu(_arg("--cli"), _arg("--lib"), _arg("--lr"))
        return 0  # list_revisions SystemExit ile çıkar; buraya düşmek = çıkış yapmadı

    lib_yolu = Path(_arg("--kaynak")).resolve() if _arg("--kaynak") else HEDEF
    lr_yolu = Path(_arg("--lr-kaynak")).resolve() if _arg("--lr-kaynak") else LR
    lib_ham = lib_yolu.read_text(encoding="utf-8")
    lr_ham = lr_yolu.read_text(encoding="utf-8")
    print("=" * 78)
    print(f"revizyon_okuma (Issue #302) — lib: {lib_yolu} · cli: {lr_yolu}")
    print("KAPSAM: yalniz get_object_revisions + list_revisions CLI; SAP'SIZ (sahte oturum). "
          "Canli SAP davranisi bu fixture'da OLCULMEZ (docstring'deki canli olcum ayridir).")
    print("=" * 78)
    lib_d = _lib_degerlendir(_modul(lib_ham))
    cli_d = _cli_degerlendir(lib_ham, lr_ham)
    _yaz("-- V: fonksiyon (surec ici)", lib_d)
    _yaz("-- L: gercek cagiran list_revisions.py (ayri surec)", cli_d)
    deger = lib_d + cli_d
    gecen = sum(1 for _, ok, _ in deger if ok)
    print(f"\n{gecen}/{len(deger)} OK")
    if lib_yolu != HEDEF or lr_yolu != LR:
        return 0 if gecen == len(deger) else 1

    print("\n--- MUTASYONLAR (her biri en az bir vektoru KIRMIZI yapmali) ---")
    kirik = []
    for mad, eski, yeni in MUTASYONLAR:
        mutant, adet = _mutant_lib(lib_ham, eski, yeni)
        if mutant is None:
            print(f"  [KURULAMADI] {mad} -> capa get_object_revisions icinde {adet} kez (beklenen 1)")
            kirik.append(mad + " (KURULAMADI)")
            continue
        try:
            m_deger = _lib_degerlendir(_modul(mutant))
        except Exception as e:  # noqa: BLE001
            print(f"  [KURULAMADI] {mad} -> {type(e).__name__}: {e}")
            kirik.append(mad + " (KURULAMADI)")
            continue
        kiranlar = [a.split()[0] for a, ok, _ in m_deger if not ok]
        print(f"  [{'YAKALANDI' if kiranlar else 'KACTI'}] {mad}"
              + (f"  <- {', '.join(kiranlar)}" if kiranlar else ""))
        if not kiranlar:
            kirik.append(mad)
    for mad, eski, yeni in LR_MUTASYONLAR:
        adet = lr_ham.count(eski)
        if adet != 1:
            print(f"  [KURULAMADI] {mad} -> capa list_revisions.py icinde {adet} kez (beklenen 1)")
            kirik.append(mad + " (KURULAMADI)")
            continue
        m_deger = _cli_degerlendir(lib_ham, lr_ham.replace(eski, yeni))
        kiranlar = [a.split()[0] for a, ok, _ in m_deger if not ok]
        print(f"  [{'YAKALANDI' if kiranlar else 'KACTI'}] {mad}"
              + (f"  <- {', '.join(kiranlar)}" if kiranlar else ""))
        if not kiranlar:
            kirik.append(mad)
    toplam_mut = len(MUTASYONLAR) + len(LR_MUTASYONLAR)
    print("\n" + "=" * 78)
    if gecen != len(deger) or kirik:
        if kirik:
            print("FAIL — mutasyon KACTI/KURULAMADI: " + "; ".join(kirik))
        return 1
    print(f"PASS — {len(deger)} vektor + {toplam_mut} mutasyon")
    return 0


if __name__ == "__main__":
    sys.exit(main())
