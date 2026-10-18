#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ADT XML gövdesi için ortak kaçış ve `adtcore:responsible` çözümü (TEK KAYNAK).

NEDEN AYRI MODÜL (Issue #339, 2026-10-18): `attr_escape` önce yalnız
`populate_message_class.py` içinde tanımlıydı. Kardeş araçlar (`populate_domains`,
`populate_dataelements`, `sap_adt_lib`) ise öznitelik değerlerini KAÇIŞSIZ ya da çıplak
`xml_escape()` ile yazıyordu. Kardeşlerin `populate_message_class`'ı import etmesi çözüm
DEĞİL: o modül import anında `sys.stdout`'u yeniden sarar ve önceki sarmalayıcı çöp
toplanınca alttaki tamponu KAPATIR (B22/B25 dersi). Bu modülün yan etkisi yoktur.

`populate_message_class` `attr_escape`'i buradan import eder ve aynı adla yeniden
dışa verir; davranış değişmedi.
"""
from __future__ import annotations

from xml.sax.saxutils import escape as xml_escape

# `"` + satır/sekme karakterleri: XML öznitelik değeri NORMALLEŞTİRMESİ çıplak TAB/LF/CR'yi
# boşluğa çevirir ⇒ kaçışlanmazsa gönderilen metin canlıdakinden FARKLI okunur (öz-denetim
# yanıltıcı "öznitelik farkı" ile dururdu).
_ATTR_KACIS = {'"': '&quot;', '\t': '&#9;', '\n': '&#10;', '\r': '&#13;'}


def attr_escape(metin: str) -> str:
    """XML ÖZNİTELİK değeri kaçışı: `& < >` + ÇİFT TIRNAK.

    ⛔ Çıplak `xml_escape()` `"` işaretini KAÇIRMAZ (ölçüldü 2026-09-24:
    `escape('a"b')` -> `'a"b'`). Öznitelikler çift tırnakla yazıldığı için tırnaklı
    bir mesaj metni gövdeyi BOZUYORDU. Silme kipi canlı metni olduğu gibi geri
    gönderir ⇒ tırnaklı tek bir canlı mesaj bütün silmeyi düşürürdü.
    """
    return xml_escape(metin, _ATTR_KACIS)


def sorumlu_coz(verilen, client) -> str | None:
    """`adtcore:responsible` değeri: `--responsible` verildiyse o, yoksa bağlantı kullanıcısı.

    `sap_adt_lib.create_object` deseninin aynısı (`responsible or self.user`). İkisi de
    boşsa `None` döner; çağıran YAZMADAN durur (exit 2).

    ⛔ Sessiz yer tutucu YOK. Eskiden üç `populate_*` aracının varsayılanı genericize
    göçünden kalan `'<SAP_USER>'` dizesiydi ve kaçışsız yazıldığı için argümansız çağrı
    iyi biçimli olmayan XML üretiyordu (XML 1.0'da öznitelik değerinde `<` yasaktır).
    Kaçış buradan YAPILMAZ: değer ham döner, gövdeyi yazan yer `attr_escape` uygular.
    """
    deger = verilen or getattr(client, 'user', None)
    if not isinstance(deger, str) or not deger.strip():
        return None
    return deger


SORUMLU_YOK_MESAJI = (
    '[FAIL] adtcore:responsible ÇÖZÜLEMEDİ: --responsible verilmedi ve bağlantı kullanıcısı '
    '(.conn_adt ADT_SAP_USER) boş. Yer tutucu yazılmaz; --responsible <kullanıcı> ver '
    'ya da bağlantı dosyasını düzelt. HİÇBİR ŞEY YAZILMADI.')
