#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DDIC `populate_*` ailesi icin AKTIVASYON KAPANIS NOTU (tek kaynak).

⛔ NEDEN VAR — "exit 0 != kanit" sinifi (2026-08-19 olcumu):
`populate_domains.py` · `populate_dataelements.py` · `populate_tables.py` objeyi
YARATIR ama AKTIVE ETMEZ (`activate` cagrisi: 0 eslesme). Uculu de sonunda
`=== Sonuc: N basarili, 0 hatali ===` yazip `exit 0` doner. Cagiran bunu
"is bitti" diye okur; oysa objeler INAKTIF kalir ve bosluk ancak SONRAKI katman
(DTEL -> tablo -> aktivasyon) *"tip yok"* ile dustugunde gorunur -- yani hatanin
BELIRDIGI yer, DOGDUGU yer degildir.

⚠ AILE ICI TUTARSIZLIK: `populate_lock_objects.py` AKTIVE EDER
(`activate_lock_object()`, playbook §29.6 -- `activate_object.py` ENQU/DL
desteklemedigi icin kendi yolunu tasir). Yani ayni ailede iki farkli sozlesme
var ve hicbiri yazili degildi.

⛔ NEDEN AKTIVASYON EKLENMEDI (bilincli karar, 2026-08-20):
Tuketiciler bu scriptlerin aktive ETMEDIGI varsayimina gore kendi aktivasyon
adimlarini KURMUS durumda (olculdu: bir DDIC is-listesinde her `populate_*`
adiminin ardina ayri `activate_object.py` satiri yazilmis). Scriptlere aktivasyon
eklemek onlarda CIFT AKTIVASYON yaratirdi. Bu yuzden davranis AYNEN korundu;
degisen tek sey CIKTININ DURUSTLUGU. Opt-in bir `--activate` bayragi ayri bir
YETENEK kararidir (canli SAP dogrulamasi ister) ve bu turda BILEREK yapilmadi.

⚠ Bu metin TEK KAYNAKTIR: uc script de buradan cagirir. Kopyalayip ucune
yapistirma -- bu bilesen ailesinde "elle kopyalanmis ikinci literal" kusuru
daha once yasandi (bkz. sap_sync_pull `_DDIC_XML_TYPES` kaydi).
"""
from __future__ import annotations

# populate script'i -> `activate_object.py --type` degeri.
# ⚠ Deger UYDURULMAZ: `activate_object.py --type` argparse `choices`indan gelir.
AKTIVASYON_TIPI = {
    "domain": "doma",
    "dataelement": "dtel",
    "table": "tabl",
}


def aktivasyon_notu(tip: str, adlar: list[str], cwd: str | None = None) -> str:
    """Yaratilan ama AKTIVE EDILMEYEN objeler icin GORUNUR kapanis notu uretir.

    Args:
        tip: 'domain' | 'dataelement' | 'table'
        adlar: bu kosumda BASARIYLA ISLENEN obje adlari
        cwd: --cwd degeri (varsa komuta aynen konur)

    ⚠ "ISLENEN" bilerek "YARATILAN" degil: `create_one` zaten var olan objede
    `[SKIP] zaten var` deyip **True** doner, yani liste yaratilmayan obje de
    icerebilir. "N obje yaratildi" demek o vakada YANLIS olurdu; aktivasyon
    onerisi ise her iki halde de dogrudur (aktif objeyi yeniden aktive etmek
    zararsizdir, inaktif kalani ise kurtarir).

    Returns:
        Basilacak cok satirli metin. `adlar` bossa BOS STRING doner
        (yaratilan obje yoksa uyari da gurultudur).
    """
    if not adlar:
        return ""

    t = AKTIVASYON_TIPI.get(tip)
    if t is None:
        # Bilinmeyen tip: SESSIZ KALMA. Sessizlik tam da kapatmaya calistigimiz
        # kusurdur; tipi cozemedigimizi soyleyip yine de uyarmak dogrusudur.
        t = "<tip>"

    cwd_ek = f" --cwd {cwd}" if cwd else ""
    komutlar = "\n".join(
        f"    python core/scripts/activate_object.py --name {ad} --type {t}{cwd_ek}"
        for ad in adlar
    )
    # ⚠ URETILEN METIN SAF ASCII'DIR — bilincli (C-ENC-01).
    # Windows konsolu/pipe'i cp1252'dir; `⚠` gibi bir karakter cagiranin stdout'u
    # UTF-8'e sabitlenmemisse `UnicodeEncodeError` ile ÇÖKERTIR. Bir UYARI metninin
    # kosumu cokertmesi, kapatmaya calistigimiz kusurun daha kotu bir cesididir.
    # Bugunku uc cagiran da UTF-8 kurar, ama bu yardimci cagiranin konsol kurulumuna
    # BAGIMLI OLMAMALI. Non-ASCII eklemek istersen once C-ENC-01'i oku.
    return (
        "\n"
        "  " + "=" * 72 + "\n"
        f"  [!] {len(adlar)} obje ISLENDI -- AKTIVASYON YAPILMADI.\n"
        "  " + "=" * 72 + "\n"
        "  Bu script AKTIVE ETMEZ (bilincli: cagiranlarin cogu kendi aktivasyon\n"
        "  adimini kurmus durumda; buraya eklemek CIFT AKTIVASYON yaratirdi).\n"
        "  [!] Simdi aktive ETMEZSEN bir sonraki katman 'tip yok' ile duser ve\n"
        "      hata BURADA degil ORADA gorunur.\n"
        "\n"
        "  Kosulacak:\n"
        f"{komutlar}\n"
        "  " + "=" * 72
    )
