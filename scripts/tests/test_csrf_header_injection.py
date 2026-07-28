#!/usr/bin/env python3
# ENFORCES: C-CSRF-01  (ADR 0019 coverage binding)
"""test_csrf_header_injection.py — soguk session'da CSRF enjeksiyonu regresyon testi.

VAKA (2026-07-28, canli): `adt_classrun` saglam bir sinif icin
"Class does not implement if_oo_adt_classrun~main!" dondurdu. Sinif her olcute gore
saglamdi; ayni sinif ayni URL'e ELLE POST edilince HTTP 200 + tam cikti verdi.

KOK-NEDEN: cagiranlarin cogu (14+ yer) header'i `_request_with_csrf_retry`'dan ONCE
`_get_headers()` ile kuruyor. Soguk session'da o an token YOK -> `_get_headers()`
`X-CSRF-Token` anahtarini HIC eklemiyor. `_request_with_csrf_retry` icinde token
fetch ediliyordu AMA cagiranin ELINDEKI dict guncellenmiyordu -> ilk istek CSRF'siz
gidiyordu. Bazi ADT uclari buna 403 DEGIL **200 + yaniltici govde** donduruyor ->
403'e bakan retry hic tetiklenmiyor, iki deneme de ayni cikiyor ve hata
"obje bozuk / tooling bozuk" gibi gorunuyor (yanlis teshis maliyeti).

Bu test AGSIZ (offline) kosar: sahte session + stub fetch. CI'da calisir.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sap_adt_lib import SAPADTClient  # noqa: E402

TOKEN = "TAZE-CSRF-TOKEN-123"


class _SahteYanit:
    def __init__(self, status_code=200, text="", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}
        self.content = text.encode("utf-8")


class _SahteSession:
    """Gonderilen header'lari kaydeder; sirayla verilen yanitlari doner."""

    def __init__(self, yanitlar=None):
        self.gonderilen = []
        self._yanitlar = list(yanitlar or [])

    def request(self, method, url, headers=None, timeout=None, **kw):
        self.gonderilen.append(dict(headers or {}))
        return self._yanitlar.pop(0) if self._yanitlar else _SahteYanit()


def _soguk_client(yanitlar=None):
    """Ag/konfig dokunmadan client kur — yalniz test edilen yolun bagimliliklari."""
    c = SAPADTClient.__new__(SAPADTClient)
    c.csrf_token = ""                      # SOGUK session
    c.session = _SahteSession(yanitlar)
    c.timeout_default = 30
    c.debug_enabled = False
    c._update_cookies = lambda r: None
    c._get_headers = lambda **kw: ({"Accept": "x"} | ({"X-CSRF-Token": c.csrf_token} if c.csrf_token else {}))

    def _fetch(force_refresh=False):
        c.csrf_token = TOKEN
    c.fetch_csrf_token = _fetch
    return c


def test_onceden_kurulan_headera_token_enjekte_edilir():
    """ASIL REGRESYON: token fetch'ten ONCE kurulmus header token'siz gitmemeli."""
    c = _soguk_client()
    hdr = c._get_headers()                        # token YOKken kuruldu
    assert "X-CSRF-Token" not in hdr, "on kosul: soguk header token tasimamali"

    c._request_with_csrf_retry("post", "http://x/y", headers=hdr)

    gonderilen = c.session.gonderilen[0]
    assert gonderilen.get("X-CSRF-Token") == TOKEN, (
        f"soguk session'da istek CSRF'siz gitti: {gonderilen.get('X-CSRF-Token')!r}"
    )


def test_cagiranin_dicti_mutasyona_ugramaz():
    c = _soguk_client()
    hdr = c._get_headers()
    c._request_with_csrf_retry("post", "http://x/y", headers=hdr)
    assert "X-CSRF-Token" not in hdr, "cagiranin dict'i degistirilmemeli (kopya alinmali)"


def test_headers_none_yolu_bozulmadi():
    c = _soguk_client()
    c._request_with_csrf_retry("post", "http://x/y", headers=None)
    assert c.session.gonderilen[0].get("X-CSRF-Token") == TOKEN


def test_403_retry_yolu_hala_calisiyor():
    """403 + CSRF -> force refresh + tek retry; enjeksiyon bunu bozmamali."""
    yanitlar = [
        _SahteYanit(403, "CSRF token validation failed"),
        _SahteYanit(200, "ok"),
    ]
    c = _soguk_client(yanitlar)
    hdr = c._get_headers()
    r = c._request_with_csrf_retry("post", "http://x/y", headers=hdr)
    assert r.status_code == 200
    assert len(c.session.gonderilen) == 2, "403 sonrasi tam 1 retry olmali"
    assert c.session.gonderilen[1].get("X-CSRF-Token") == TOKEN


def test_cagiran_ayni_tokeni_verdiyse_bozulmaz():
    c = _soguk_client()
    c.csrf_token = TOKEN                       # session zaten sicak
    hdr = {"Accept": "x", "X-CSRF-Token": TOKEN}
    c._request_with_csrf_retry("post", "http://x/y", headers=hdr)
    assert c.session.gonderilen[0].get("X-CSRF-Token") == TOKEN


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
    print(f"\nCSRF header enjeksiyonu: {len(testler) - hata}/{len(testler)} gecti")
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
