#!/usr/bin/env python3
# ENFORCES: C-SEARCH-01  (ADR 0019 coverage binding)
"""test_search_objects_type_filter.py — tip filtresi SUNUCUYA gidiyor mu?

VAKA (2026-07-28, canli): `adt_search_objects('ZSD001*', object_type='TABL')`
**ok:true, count:0** dondu — oysa ZSD001_T_BOOKIT canli ve aktif. Ayni sorgu
tip filtresiz calisti. Sonuc "obje YOK" ile AYIRT EDILEMEZ = sessiz yanlis cevap.
Bir arastirma ajani bu yuzden tablolari bulamadi ve "0 sonuc burada KANIT DEGIL"
diye not dusmek zorunda kaldi.

KOK NEDEN (canli probe ile olculdu):
  * uc-nokta sonuclari ALFABETIK dondurur ve `maxResults`ta KIRPAR
  * eski kod tip filtresini ISTEMCI tarafinda, KIRPILMIS sayfa uzerinde uyguluyordu
  * 'ZSD001*' + maxResults=400 -> donen 400 satirin ICINDE HIC TABL YOK
    (son kayit ZSD001_I_*; ZSD001_T_* alfabetik olarak SONRA geliyor)
  * `objectType` parametresi NATIVE DESTEKLENIYOR: objectType=TABL/DT -> 9 TABL
  * eski "genis desenle (Z*) yeniden dene" yolu sorunu BUYUTUYORDU (daha genis
    sorgu daha cok kirpilir) -> KALDIRILDI

⚠ Bu test GERCEK kod yolunu cagirir: sahte bir session ile `search_objects`
calistirilir ve uc-noktaya GIDEN parametreler denetlenir. `if obj_type:` blogu
silinirse test KIRMIZI doner. (Ilk taslakta mantigi testte yeniden uygulamak
cazipti — o "sahte guvence" olurdu; bkz. test_push_readback_mismatch.py dersi.)

Agsiz (offline) kosar — SAP baglantisi GEREKMEZ.
"""
import re
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS))

from sap_adt_lib import SAPADTClient  # noqa: E402


class _FakeResponse:
    status_code = 200
    text = '<?xml version="1.0"?><root/>'


class _FakeSession:
    """Uc-noktaya giden parametreleri yakalar; ag CAGRISI YAPMAZ."""

    def __init__(self):
        self.calls = []

    def get(self, url, headers=None, params=None, timeout=None):
        self.calls.append({"url": url, "params": dict(params or {})})
        return _FakeResponse()


def _client():
    """Ag/konfig OLMADAN gercek sinifi kur (__init__ .conn_adt okur -> atlanir)."""
    c = SAPADTClient.__new__(SAPADTClient)
    c.url = "https://example.invalid:44300"
    c.timeout_short = 1
    c.session = _FakeSession()
    c._get_headers = lambda *a, **k: {}
    return c


def test_obj_type_sunucuya_gidiyor():
    """ASIL REGRESYON: tip verildiginde `objectType` uc-noktaya GITMELI."""
    c = _client()
    c.search_objects("ZSD001*", max_results=50, obj_type="TABL/DT")
    params = c.session.calls[0]["params"]
    assert params.get("objectType") == "TABL/DT", (
        f"objectType uc-noktaya GITMEDI (params={params}) — tip filtresi yine "
        f"istemci tarafinda kirpilmis sayfayi suzer = SESSIZ 0"
    )


def test_kisa_tip_de_gecer():
    """'TABL' (slash'siz) de sunucuya iletilmeli — olcumde ikisi de calisti."""
    c = _client()
    c.search_objects("ZSD001*", obj_type="TABL")
    assert c.session.calls[0]["params"].get("objectType") == "TABL"


def test_tip_yoksa_parametre_HIC_konmaz():
    """Geriye donuk uyum: tip verilmediyse `objectType` gonderilmemeli."""
    c = _client()
    c.search_objects("ZSD001*", max_results=50)
    assert "objectType" not in c.session.calls[0]["params"], \
        "tip verilmediginde objectType gonderilmemeli"


def test_temel_parametreler_korunuyor():
    """Fix, mevcut sozlesmeyi bozmamali."""
    c = _client()
    c.search_objects("ZSD001*", max_results=77)
    p = c.session.calls[0]["params"]
    assert p.get("operation") == "quickSearch"
    assert p.get("query") == "ZSD001*"
    assert p.get("maxResults") == 77


def test_tek_cagri_yapilir():
    """Kaldirilan 'genis desenle yeniden dene' yolu GERI GELMEMELI.

    O yol sonuc bosken IKINCI bir arama yapiyordu (Z* + 10x maxResults) —
    daha genis sorgu daha COK kirpilir, yani sorunu BUYUTUYORDU.
    """
    c = _client()
    c.search_objects("ZSD001*", max_results=50, obj_type="TABL")
    assert len(c.session.calls) == 1, \
        f"tek arama bekleniyordu, {len(c.session.calls)} yapildi (genis-desen retry geri mi geldi?)"


def test_ust_sinir_sabiti_beyanli():
    """Olculen uc-nokta tavani (550) kodda SABIT olarak durmali."""
    assert getattr(SAPADTClient, "MAX_SEARCH_RESULTS", None) == 550, \
        "MAX_SEARCH_RESULTS sabiti yok/degismis — olcum 2026-07-28: 1000 istendi, 550 dondu"


def test_sap_client_obj_type_i_ILETIYOR():
    """Kablolama: ust katman `obj_type`'i alt katmana GECIRMELI.

    Fonksiyon dogru calissa bile cagrilmiyorsa koruma yoktur (kod != kablolama).
    Gevsek 'dosyada gecsin' kontrolu YETMEZ -> cagrinin KENDISINI ara.
    """
    src = (_SCRIPTS / "sap_client.py").read_text(encoding="utf-8")
    m = re.search(r"self\.adt_client\.search_objects\((.*?)\)", src, re.S)
    assert m, "sap_client icinde adt_client.search_objects cagrisi bulunamadi"
    args = m.group(1)
    assert "obj_type" in args, \
        "sap_client, obj_type'i alt katmana GECIRMIYOR — tip filtresi sunucuya ulasmaz"


def test_kirpma_uyarisi_var():
    """Sessiz-eksik karsi-onlemi: tavana dayanan sonucta UYARI basilmali."""
    src = (_SCRIPTS / "sap_client.py").read_text(encoding="utf-8")
    assert "truncated" in src and "KIRPILMIS" in src.upper(), \
        "kirpma uyarisi kaldirilmis — eksik liste yine sessiz doner"


def main() -> int:
    testler = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    hata = 0
    for t in testler:
        try:
            t()
            print(f"  [OK]   {t.__name__}")
        except AssertionError as e:
            hata += 1
            print(f"  [FAIL] {t.__name__}: {e}")
    print(f"\nsearch_objects tip-filtresi: {len(testler) - hata}/{len(testler)} gecti")
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
