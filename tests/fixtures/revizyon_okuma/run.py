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

AYNI SINIF, İKİ KARDEŞ (2026-11-02, Q350 + Q351):
  · H-vektörleri: `find_ghost_transports` (E070 freestyle sorgusu) — 200-dışı · ağ hatası · XML olmayan
    gövde · kolonsuz VE `totalRows` 0 olmayan gövde · TRKORR kolonu yok → SAPADTError; `[]` YALNIZ
    geçerli boş yanıtta (kolonlu boş dataSet · kolonsuz `totalRows`=0). Değer `<dataSet><data>X</data>`
    ELEMAN METNİNDEN okunur (kardeş `sap_client._find_existing_transport` biçimi; eski kod doğrudan-çocuk
    `data` + `value` özniteliği okuyup DOLU yanıtta da [] dönüyordu). Canlı freestyle yanıt biçimi bu
    turda ÖLÇÜLMEDİ (POST; biçim kanıtı kardeş ayrıştırıcıdır).
  · P-vektörleri: GERÇEK çağıran `sap_client.push_object` 409 `SAPLockError` dalı, süreç İÇİNDE
    (kilit sorgusu 409 fırlatır, `find_ghost_transports` gerçek kütüphaneden sahte POST oturumuyla koşar):
    okunamazsa "hayalet transport listesi okunamadı — SE10'da elle bakın" satırı; push sonucu (result)
    okunabilen boş yanıttakiyle BİREBİR aynı.
  · L4/L5: `list_revisions.py --name … --type table|tabl` → `/sap/bc/adt/ddic/tables/<ad>` (Q351).

KULLANIM:
    python tests/fixtures/revizyon_okuma/run.py        # vektörler + mutasyonlar, exit 0
    python tests/fixtures/revizyon_okuma/run.py --kaynak <sap_adt_lib> [--lr-kaynak <list_revisions>]
                                                [--sc-kaynak <sap_client>]
        # vektörleri BAŞKA kaynakta koş (mutasyon yok) — eski kod karşıtlığı:
        #   git show <taban>:scripts/sap_adt_lib.py > <kum>/eski_lib.py
        #   git show <taban>:scripts/list_revisions.py > <kum>/eski_lr.py
        #   git show <taban>:scripts/sap_client.py > <kum>/eski_sc.py
        #   → --kaynak <kum>/eski_lib.py --lr-kaynak <kum>/eski_lr.py --sc-kaynak <kum>/eski_sc.py
        # beklenen: taban 635ad3e (#302 öncesi) → V/L için yalnız KONTROL grubu (V4·V5·V6·V21·L3;
        # 2026-09-25 ölçümü, H/P vektörleri o tarihte yoktu) · taban b5b8040 (#302 sonrası, Q350/Q351
        # öncesi) → 28/41: kırmızı YALNIZ H2·H3·H4·H4b·H5·H6·H6b·H7·P1·P3·P4·L4·L5 (ölçüldü 2026-11-02).
⚠ V4/V5/V6/V21/H1/H1b/P2/P5/L3 KONTROL GRUBU — silinmez (meşru boş/yok da istisnaya çevrilirse onlar kırılır).
Mutasyonlar yalnız `get_object_revisions` gövdesinde (segment-kapsamlı çapa, tam 1 eşleşme) ve
`list_revisions.py`'de uygulanır; kaynak dosyalara YAZILMAZ (bellekte / geçici kum).
"""
from __future__ import annotations

import contextlib
import io
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
SC = KOK / "scripts" / "sap_client.py"
if not HEDEF.is_file() or not LR.is_file() or not SC.is_file():
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
TABLO = "/sap/bc/adt/ddic/tables/zsd001_t_ornek"

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
    # Q351: --name/--type table|tabl → DDIC tablo ucu (PR #303 canlı ölçümü: tablo `blue:blueSource`,
    # href `./<ad>/source/main/versions`). Eski eşleme ddl/sources → sahte oturumda 404 → [FAIL].
    "L4": dict(objeler={TABLO: _obje([_link("./zsd001_t_ornek/source/main/versions")],
                                     kok="blue:blueSource", ns=BDEF_NS)},
               feedler={TABLO + "/source/main/versions": (200, _feed(1))}, url=TABLO,
               argv=["--name", "ZSD001_T_ORNEK", "--type", "table"]),
    "L5": dict(objeler={TABLO: _obje([_link("./zsd001_t_ornek/source/main/versions")],
                                     kok="blue:blueSource", ns=BDEF_NS)},
               feedler={TABLO + "/source/main/versions": (200, _feed(1))}, url=TABLO,
               argv=["--name", "ZSD001_T_ORNEK", "--type", "tabl"]),
}
TERS_BOLU_N = "\\" + "n"  # ekranda LITERAL ters-bölü + n (kaçış hatası izi)
CLI_VEKTORLER = [
    ("L1 CLI: surum var -> rc 0 + 'Revision History' + ekranda literal \\n YOK", "L1",
     lambda rc, o: rc == 0 and "Revision History" in o and "Revision 2:" in o and TERS_BOLU_N not in o),
    ("L2 CLI: obje 406 -> rc 1 + [FAIL] (sessiz 'No revisions' DEGIL)", "L2",
     lambda rc, o: rc == 1 and "[FAIL]" in o and "No revisions" not in o),
    ("L3 CLI KONTROL: baglanti yok -> rc 0 + '[INFO] No revisions'", "L3",
     lambda rc, o: rc == 0 and "[INFO] No revisions found" in o),
    ("L4 CLI --type table -> /ddic/tables/<ad> (rc 0 + 'Revision 1:')", "L4",
     lambda rc, o: rc == 0 and "Revision 1:" in o and "[FAIL]" not in o),
    ("L5 CLI --type tabl -> /ddic/tables/<ad> (rc 0 + 'Revision 1:')", "L5",
     lambda rc, o: rc == 0 and "Revision 1:" in o and "[FAIL]" not in o),
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
    ("ML3 'table' eski DDLS ucuna dondu (Q351 geri)",
     "'table': '/sap/bc/adt/ddic/tables',", "'table': '/sap/bc/adt/ddic/ddl/sources',"),
    ("ML4 'tabl' eski DDLS ucuna dondu (Q351 geri)",
     "'tabl': '/sap/bc/adt/ddic/tables',", "'tabl': '/sap/bc/adt/ddic/ddl/sources',"),
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


# ─────────────────────────────────────────────────────────────────────────────
# H — find_ghost_transports (Q350) · P — gerçek çağıran push_object 409 dalı
# ─────────────────────────────────────────────────────────────────────────────
DP_NS = 'xmlns:dataPreview="http://www.sap.com/adt/dataPreview"'


def _dp(kolonlar, toplam=None):
    """kolonlar: [(ad, [değer, …])] — kardeş ayrıştırıcıların okuduğu biçim (`<dataSet><data>X</data>`)."""
    parca = "".join(
        f'<dataPreview:columns><dataPreview:metadata dataPreview:name="{ad}"/><dataPreview:dataSet>'
        + "".join(f"<dataPreview:data>{v}</dataPreview:data>" for v in degerler)
        + "</dataPreview:dataSet></dataPreview:columns>" for ad, degerler in kolonlar)
    say = f"<dataPreview:totalRows>{toplam}</dataPreview:totalRows>" if toplam is not None else ""
    return (f'<?xml version="1.0" encoding="utf-8"?><dataPreview:tableData {DP_NS}>{say}'
            f'<dataPreview:queryExecutionTime>1</dataPreview:queryExecutionTime>{parca}'
            '</dataPreview:tableData>')


HAYALET_1, HAYALET_2 = "SAHK900101", "SAHK900102"
H_YANIT = {
    "bos": (200, _dp([("TRKORR", []), ("AS4TEXT", [])], toplam=0)),
    "kolonsuz_sifir": (200, _dp([], toplam=0)),
    "dolu": (200, _dp([("TRKORR", [HAYALET_1, HAYALET_2]), ("AS4TEXT", ["x", "y"])], toplam=2)),
    "500": (500, "dump"),
    "html": (200, HTML),
    "xml_degil": (200, "<html><body>Logon<br></body></html>"),
    "ag": None,
    "kolonsuz": (200, _dp([])),
    "kolonsuz_uc": (200, _dp([], toplam=3)),
    "trkorrsuz": (200, _dp([("AS4TEXT", ["x"])], toplam=1)),
}


class _PostOturum:
    def __init__(self, kip):
        self.kip, self.istekler = kip, []

    def post(self, url, headers=None, params=None, data=None, timeout=None, **kw):
        self.istekler.append(url[len(BASE):] if url.startswith(BASE) else url)
        if H_YANIT[self.kip] is None:
            raise requests.exceptions.ConnectionError("sahte: ad cozulemedi")
        kod, govde = H_YANIT[self.kip]
        return _Yanit(kod, govde)

    def get(self, *a, **k):  # salt-okur kanıtı: bu yolda GET beklenmez
        raise AssertionError("find_ghost_transports GET cagirmamali")


def _hayalet_istemci(mod, kip):
    c = object.__new__(mod.SAPADTClient)
    c.url, c.user, c.client = BASE, "SAHTE_KULLANICI", "000"
    c.csrf_token, c.timeout_default, c.debug_enabled = "sahte-token", 5, False
    c._get_headers = lambda *a, **k: {}
    c.session = _PostOturum(kip)
    return c


H_VEKTORLER = [
    ("H1 KONTROL: gecerli bos yanit (kolonlu, bos dataSet) -> mesru []", "bos", ("liste", [])),
    ("H1b KONTROL: kolonsuz ama totalRows=0 -> mesru []", "kolonsuz_sifir", ("liste", [])),
    ("H2 KONTROL: gecerli DOLU yanit -> 2 hayalet (deger <data> METNINDEN)", "dolu",
     ("liste", [HAYALET_1, HAYALET_2])),
    ("H3 freestyle 500 -> SAPADTError (sessiz [] DEGIL)", "500", ("istisna", "SAPADTError", 500)),
    ("H4 200 ama iyi-bicimli HTML giris sayfasi -> SAPADTError (kolon kapisi)", "html",
     ("istisna", "SAPADTError", 200)),
    ("H4b 200 ama XML olarak AYRISTIRILAMAYAN govde -> SAPADTError (ParseError kapisi)", "xml_degil",
     ("istisna", "SAPADTError", 200)),
    ("H5 ag hatasi -> SAPADTError", "ag", ("istisna", "SAPADTError", None)),
    ("H6 kolonsuz + totalRows YOK -> SAPADTError", "kolonsuz", ("istisna", "SAPADTError", 200)),
    ("H6b kolonsuz + totalRows=3 -> SAPADTError (sayi var, kolon yok)", "kolonsuz_uc",
     ("istisna", "SAPADTError", 200)),
    ("H7 TRKORR kolonu yok -> SAPADTError", "trkorrsuz", ("istisna", "SAPADTError", 200)),
]


def _hayalet_degerlendir(mod):
    sonuc = []
    for ad, kip, beklenen in H_VEKTORLER:
        c = _hayalet_istemci(mod, kip)
        try:
            gorulen = ("liste", list(c.find_ghost_transports()))
        except Exception as e:  # noqa: BLE001 — tür hükmün parçası
            gorulen = ("istisna", type(e).__name__, getattr(e, "status_code", None))
        dogru_uc = c.session.istekler == ["/sap/bc/adt/datapreview/freestyle"]
        sonuc.append((ad, gorulen == beklenen and dogru_uc,
                      f"beklenen {beklenen} · gorulen {gorulen} · istekler {c.session.istekler}"))
    return sonuc


OKUNAMADI_SATIRI = "hayalet transport listesi okunamadı — SE10'da elle bakın"
PUSH_AD = "ZSD001_CL_ORNEK"


def _sc_modul(sc_metni: str, lib_mod):
    """sap_client METNİNİ, test edilen lib modülüyle (sys.modules) exec et."""
    onceki = sys.modules.get("sap_adt_lib")
    sys.modules["sap_adt_lib"] = lib_mod
    m = types.ModuleType("sap_client")
    m.__file__ = str(SC)
    try:
        exec(compile(sc_metni, str(SC), "exec"), m.__dict__)
    finally:
        if onceki is not None:
            sys.modules["sap_adt_lib"] = onceki
        else:
            sys.modules.pop("sap_adt_lib", None)
    return m


def _push_409(lib_mod, sc_mod, kip, kilit_kodu=409):
    """push_object: kilit sorgusu SAPLockError(kilit_kodu) fırlatır → except dalı.

    `find_ghost_transports` GERÇEK lib gövdesidir (sahte POST oturumu, `kip` yanıtı)."""
    adt = _hayalet_istemci(lib_mod, kip)

    def _kilitli(url):
        raise lib_mod.SAPLockError("sahte kilit catismasi", status_code=kilit_kodu)

    adt.is_object_locked = _kilitli
    ist = object.__new__(sc_mod.SAPClient)
    ist.adt_client, ist.debug_enabled = adt, False
    kum = Path(tempfile.mkdtemp(prefix="revizyon_okuma_push_"))
    try:
        dosya = kum / f"{PUSH_AD}.clas.abap"
        dosya.write_bytes(b"CLASS zsd001_cl_ornek DEFINITION PUBLIC.\nENDCLASS.\n")
        ist.local_base = kum
        tampon = io.StringIO()
        onceki = sys.modules.get("sap_adt_lib")
        sys.modules["sap_adt_lib"] = lib_mod      # except dalındaki `from sap_adt_lib import SAPLockError`
        try:
            with contextlib.redirect_stdout(tampon), contextlib.redirect_stderr(tampon):
                r = ist.push_object(PUSH_AD, object_type="class", transport="SAHK900001",
                                    source_file=str(dosya))
            kacti = None
        except Exception as e:  # noqa: BLE001 — push hata akışını DEĞİŞTİRMEMELİ
            r, kacti = None, f"{type(e).__name__}: {e}"
        finally:
            if onceki is not None:
                sys.modules["sap_adt_lib"] = onceki
            else:
                sys.modules.pop("sap_adt_lib", None)
        return r, tampon.getvalue(), kacti, adt.session.istekler
    finally:
        shutil.rmtree(kum, ignore_errors=True)


def _sonuc_ozu(r):
    """Push sonucunun okunabilen-boş ile kıyaslanacak çekirdeği (yol/md5 kum dizinine bağlı → hariç)."""
    if not isinstance(r, dict):
        return r
    return {k: r.get(k) for k in ("success", "error", "error_type", "source_uploaded",
                                  "activated", "lock_released")}


def _push_degerlendir(lib_mod, sc_metni: str):
    try:
        sc_mod = _sc_modul(sc_metni, lib_mod)
    except Exception as e:  # noqa: BLE001 — çökme != FAIL: ölçülür
        return [("P* sap_client kurulamadi", False, f"{type(e).__name__}: {e}")]
    s = {k: _push_409(lib_mod, sc_mod, k) for k in ("dolu", "bos", "500", "ag")}
    s["423"] = _push_409(lib_mod, sc_mod, "500", kilit_kodu=423)
    ozet = {k: _sonuc_ozu(v[0]) for k, v in s.items()}
    taban = ozet["bos"]
    sonuc = []
    r, log, kacti, ist = s["dolu"]
    sonuc.append(("P1 KONTROL: 409 + dolu yanit -> iki hayalet 'delete in SE10' ile listelenir",
                  kacti is None and f"{HAYALET_1} — delete in SE10" in log
                  and f"{HAYALET_2} — delete in SE10" in log and OKUNAMADI_SATIRI not in log,
                  f"kacti={kacti} log_sonu={log.strip()[-300:]!r}"))
    r, log, kacti, ist = s["bos"]
    sonuc.append(("P2 KONTROL: 409 + gecerli bos yanit -> ne liste ne 'okunamadi'; error_type SAPLockError",
                  kacti is None and "delete in SE10" not in log and OKUNAMADI_SATIRI not in log
                  and isinstance(r, dict) and r.get("error_type") == "SAPLockError"
                  and r.get("success") is False and ist == ["/sap/bc/adt/datapreview/freestyle"],
                  f"kacti={kacti} sonuc={taban} istekler={ist}"))
    for anahtar, etiket in (("500", "P3 409 + freestyle 500"), ("ag", "P4 409 + ag hatasi")):
        r, log, kacti, ist = s[anahtar]
        sonuc.append((f"{etiket} -> 'okunamadi — SE10'da elle bakin' satiri + push sonucu P2 ile AYNI",
                      kacti is None and OKUNAMADI_SATIRI in log and "delete in SE10" not in log
                      and ozet[anahtar] == taban,
                      f"kacti={kacti} sonuc={ozet[anahtar]} taban={taban} log_sonu={log.strip()[-300:]!r}"))
    r, log, kacti, ist = s["423"]
    sonuc.append(("P5 KONTROL: 409 DISI kilit hatasi -> hayalet sorgusu HIC yapilmaz",
                  kacti is None and ist == [] and OKUNAMADI_SATIRI not in log,
                  f"kacti={kacti} istekler={ist}"))
    return sonuc


# (ad, eski, yeni) — çapa find_ghost_transports gövdesinde TAM 1 kez geçmeli
H_SEG_BAS = "    def find_ghost_transports("
H_SEG_SON = "    def _parse_activation_response("
H_MUTASYONLAR = [
    ("MG1 freestyle 200-disi sessiz [] (Q350 geri)",
     "        if response.status_code != 200:\n            raise SAPADTError(okunamadi,",
     "        if response.status_code != 200:\n            return []\n            raise SAPADTError(okunamadi,"),
    ("MG2 ag hatasi sessiz [] (Q350 geri)",
     "        except requests.exceptions.RequestException as e:\n            raise SAPADTError(",
     "        except requests.exceptions.RequestException as e:\n            return []\n"
     "            raise SAPADTError("),
    ("MG3 XML olmayan govde sessiz [] (Q350 geri)",
     "        except ET.ParseError as e:\n            raise SAPADTError(",
     "        except ET.ParseError as e:\n            return []\n            raise SAPADTError("),
    ("MG4 kolonsuz govde sessiz [] (Q350 geri)",
     "            raise SAPADTError(f\"{okunamadi}: no column metadata",
     "            return []\n            raise SAPADTError(f\"{okunamadi}: no column metadata"),
    ("MG5 TRKORR kolonu yok sessiz [] (Q350 geri)",
     "            raise SAPADTError(f\"{okunamadi}: TRKORR column missing",
     "            return []\n            raise SAPADTError(f\"{okunamadi}: TRKORR column missing"),
    ("MG6 deger dogrudan-cocuk data'dan okunuyor (eski ayristirma)",
     "trkorr_col.findall('.//dp:data', ns)", "trkorr_col.findall('dp:data', ns)"),
    ("MG7 deger 'value' OZNITELIGINDEN okunuyor (eski ayristirma)",
     "val = (cell.text or '').strip()",
     "val = cell.get('{http://www.sap.com/adt/dataPreview}value', '').strip()"),
    ("MG8 kolonsuz totalRows=0 mesru bos dali yok",
     "if toplam is not None and (toplam.text or '').strip() == '0':", "if False:"),
    ("MG9 kolonsuz govde totalRows'a bakilmadan bos sayiliyor",
     "if toplam is not None and (toplam.text or '').strip() == '0':", "if True:"),
]
# sap_client.py mutasyonları (çapa dosyada TAM 1 kez)
SC_MUTASYONLAR = [
    ("MP1 cagiran 'okunamadi' ipucunu basmiyor",
     "print(f\"[HINT] hayalet transport listesi okunamadı — SE10'da elle bakın\")", "pass"),
    ("MP2 ic except daraldi -> okuma hatasi dis 'pass'e duser (eski sessizlik)",
     "except Exception as ghost_err:", "except ValueError as ghost_err:"),
    ("MP3 okuma hatasi push sonucunu degistiriyor",
     "                        ghosts = None\n",
     "                        ghosts = None\n                        result['error_type'] = 'GhostReadError'\n"),
]


# İLAN EDİLEN hedef vektörler: mutasyon bunları KIRMIZI yapmazsa (başka bir vektör kırılsa bile)
# HEDEF-KACTI = FAIL ("rc != 0" yakalama kanıtı değildir).
MUT_HEDEF = {
    "MG1": {"H3", "P3"}, "MG2": {"H5", "P4"}, "MG3": {"H4b"}, "MG4": {"H6"}, "MG5": {"H7"},
    "MG6": {"H2", "P1"}, "MG7": {"H2", "P1"}, "MG8": {"H1b"}, "MG9": {"H6"},
    "MP1": {"P3", "P4"}, "MP2": {"P3", "P4"}, "MP3": {"P3", "P4"},
    "ML3": {"L4"}, "ML4": {"L5"},
}


def _hedef_denetle(mad, kiranlar, kirik):
    beklenen = MUT_HEDEF.get(mad.split()[0])
    if beklenen and not beklenen <= set(kiranlar):
        print(f"  [HEDEF-KACTI] {mad} -> ilan edilen {sorted(beklenen)} · kirilan {sorted(kiranlar)}")
        kirik.append(mad + " (HEDEF-KACTI)")


def _mutant_seg(ham: str, bas_capa: str, son_capa: str, eski: str, yeni: str):
    bas = ham.find(bas_capa)
    son = ham.find(son_capa, bas + 1) if bas >= 0 else -1
    if bas < 0 or son < 0:
        return None, -1
    seg = ham[bas:son]
    adet = seg.count(eski)
    if adet != 1:
        return None, adet
    return ham[:bas] + seg.replace(eski, yeni) + ham[son:], 1


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
    sys.argv = [str(LR)] + kur.get("argv", ["--url", kur["url"]])
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
    sc_yolu = Path(_arg("--sc-kaynak")).resolve() if _arg("--sc-kaynak") else SC
    lib_ham = lib_yolu.read_text(encoding="utf-8")
    lr_ham = lr_yolu.read_text(encoding="utf-8")
    sc_ham = sc_yolu.read_text(encoding="utf-8")
    print("=" * 78)
    print(f"revizyon_okuma (Issue #302 + Q350/Q351) — lib: {lib_yolu} · cli: {lr_yolu} · client: {sc_yolu}")
    print("KAPSAM: get_object_revisions + find_ghost_transports + push_object 409 dali + "
          "list_revisions CLI; SAP'SIZ (sahte oturum). Canli SAP davranisi bu fixture'da OLCULMEZ "
          "(docstring'deki canli olcum ayridir; freestyle yanit bicimi canlida OLCULMEDI). "
          "list_revisions 'view'/'viewd' eslemesi KAPSAM DISI (karar bekliyor).")
    print("=" * 78)
    lib_mod = _modul(lib_ham)
    lib_d = _lib_degerlendir(lib_mod)
    h_d = _hayalet_degerlendir(lib_mod)
    p_d = _push_degerlendir(lib_mod, sc_ham)
    cli_d = _cli_degerlendir(lib_ham, lr_ham)
    _yaz("-- V: get_object_revisions (surec ici)", lib_d)
    _yaz("-- H: find_ghost_transports (surec ici)", h_d)
    _yaz("-- P: gercek cagiran sap_client.push_object 409 dali (surec ici)", p_d)
    _yaz("-- L: gercek cagiran list_revisions.py (ayri surec)", cli_d)
    deger = lib_d + h_d + p_d + cli_d
    gecen = sum(1 for _, ok, _ in deger if ok)
    print(f"\n{gecen}/{len(deger)} OK")
    if lib_yolu != HEDEF or lr_yolu != LR or sc_yolu != SC:
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
        _hedef_denetle(mad, kiranlar, kirik)
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
        _hedef_denetle(mad, kiranlar, kirik)
    for mad, eski, yeni in H_MUTASYONLAR:
        mutant, adet = _mutant_seg(lib_ham, H_SEG_BAS, H_SEG_SON, eski, yeni)
        if mutant is None:
            print(f"  [KURULAMADI] {mad} -> capa find_ghost_transports icinde {adet} kez (beklenen 1)")
            kirik.append(mad + " (KURULAMADI)")
            continue
        try:
            m_lib = _modul(mutant)
            m_deger = _hayalet_degerlendir(m_lib) + _push_degerlendir(m_lib, sc_ham)
        except Exception as e:  # noqa: BLE001
            print(f"  [KURULAMADI] {mad} -> {type(e).__name__}: {e}")
            kirik.append(mad + " (KURULAMADI)")
            continue
        kiranlar = [a.split()[0] for a, ok, _ in m_deger if not ok]
        print(f"  [{'YAKALANDI' if kiranlar else 'KACTI'}] {mad}"
              + (f"  <- {', '.join(kiranlar)}" if kiranlar else ""))
        if not kiranlar:
            kirik.append(mad)
        _hedef_denetle(mad, kiranlar, kirik)
    for mad, eski, yeni in SC_MUTASYONLAR:
        adet = sc_ham.count(eski)
        if adet != 1:
            print(f"  [KURULAMADI] {mad} -> capa sap_client.py icinde {adet} kez (beklenen 1)")
            kirik.append(mad + " (KURULAMADI)")
            continue
        m_deger = _push_degerlendir(lib_mod, sc_ham.replace(eski, yeni))
        kiranlar = [a.split()[0] for a, ok, _ in m_deger if not ok]
        print(f"  [{'YAKALANDI' if kiranlar else 'KACTI'}] {mad}"
              + (f"  <- {', '.join(kiranlar)}" if kiranlar else ""))
        if not kiranlar:
            kirik.append(mad)
        _hedef_denetle(mad, kiranlar, kirik)
    toplam_mut = len(MUTASYONLAR) + len(LR_MUTASYONLAR) + len(H_MUTASYONLAR) + len(SC_MUTASYONLAR)
    print("\n" + "=" * 78)
    if gecen != len(deger) or kirik:
        if kirik:
            print("FAIL — mutasyon KACTI/KURULAMADI: " + "; ".join(kirik))
        return 1
    print(f"PASS — {len(deger)} vektor + {toplam_mut} mutasyon")
    return 0


if __name__ == "__main__":
    sys.exit(main())
