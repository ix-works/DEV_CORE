# -*- coding: utf-8 -*-
"""Boş-sonuç sınıflandırıcı — BAĞIMLILIKSIZ (MCP SDK gerektirmez).

⛔ NEDEN AYRI MODÜL (2026-09-03): bu sınıflandırıcı `tools/atom.py` içinde yaşıyordu;
atom.py ise `mcp_servers.sap_adt._app` üzerinden **MCP SDK'sını** import eder. `scripts/`
altındaki CLI araçları (ör. `sap_doctor.py`) sınıflandırmayı kullanmak istediğinde SDK'yı da
zorunlu kılmış oluyordu — SDK'sız ortamda (CI `pip install requests urllib3 python-dotenv`)
`ImportError` düşüyor ve araç "ağ mı, yetki mi" sorusuna **"probe hatası"** diye yanlış cevap
veriyordu (ölçüldü: PR'ın CI koşusu). Mantık TEK YERDE kalsın diye kopyalanmadı, TAŞINDI;
`atom.py` buradan re-export eder ⇒ mevcut `from ...tools.atom import _bos_sonuc_sinifi`
çağrıları AYNEN çalışır.

⚠ Bu modül hiçbir şey import etmez (`re` hariç) ve hiçbir şey BASMAZ — öyle kalmalı.
"""
from __future__ import annotations

import re

# "BULUNAMADI != YOK" (ölçüldü 2026-07-31, dört ayrı vaka aynı gün).
# adt_get, ulaşılamayan SAP'te de `ok:true, exists:false` döndürüyordu; obje CANLIDA
# VARDI ve client_log'da NameResolutionError yazıyordu. Bir ajan buna dayanıp
# "obje yok, yaratayım" derse ADR 0005-A sınırına dayanır.
_UNREACHABLE_MARKERS = (
    "NameResolutionError", "getaddrinfo", "ConnectionError", "ConnectTimeout",
    "Max retries exceeded", "ReadTimeout", "SSLError", "ProxyError",
    "Connection refused", "Connection aborted",
)


def _bos_sonuc_sinifi(log_text: str) -> str:
    """Alt katmanın YUTTUĞU boş sonucu ÜÇ-DEĞERLİ sınıflandır.

    Döner: `"yok"` (yokluk KANITLI) · `"ulasilamadi"` (ağ/erişim) · `"belirsiz"`
    (hata var ama yokluk imzası YOK — ör. HTTP 500/403).

    ⛔ SINIF-KURALI (2026-08-01 bug-avı, "doğrulama koşamadı = doğrulandı"):
    `sap_client` katmanındaki okuyucular (`get_ddic_object`, `get_object_metadata`, ...)
    HER istisnayı yutup `None` döndürür ve sebebi yalnız stdout'a `[ERROR] ...` diye basar.
    Bu yüzden üst kattaki `except` dalları o yollarda HİÇ ateşlenmez; `None`'ı doğrudan
    "obje yok" saymak, "sunucu patladı"yı "yok"la AYNI cevaba düşürür. Kanıt tek yerden
    üretilsin diye sınıflandırma bu TEK fonksiyonda toplandı; `adt_get` (DDIC + klasik),
    delete-readback ve lock-probe aynı kaynağı kullanır.

    Kanıt kaynağı: `SAPADTError.__str__` = `"[<status>] <mesaj>"` → durum kodu log'a
    DÜŞER. 404 = yokluk kanıtı; 4xx/5xx = kanıt DEĞİL.
    """
    lt = log_text or ""
    if any(m in lt for m in _UNREACHABLE_MARKERS):
        return "ulasilamadi"
    dusuk = lt.lower()
    kodlar = set(re.findall(r"\[(\d{3})\]", lt))
    if kodlar - {"404"}:            # 500/403/502... → yokluk BEYAN EDİLMEZ
        return "belirsiz"
    if "404" in kodlar:
        return "yok"
    yokluk_imzasi = any(s in dusuk for s in
                        ("not found", "notfound", "404", "does not exist",
                         "bulunamadı", "bulunamadi"))
    hata_izi = "[error]" in dusuk
    if hata_izi and not yokluk_imzasi:
        return "belirsiz"
    # Temiz-boş yanıt (hata izi yok) ya da kesin bulunamadı imzası.
    return "yok"


