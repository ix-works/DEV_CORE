# -*- coding: utf-8 -*-
"""ad_politikasi — "bu SAP adı MÜŞTERİNİN mi?" kararının TEK KAYNAĞI (ADR 0005-A, A-EK).

NEDEN VAR (DEV_CORE Issue #397 / Q393, 2026-11-08)
  ADR 0005-A standart nesneye yazmayı yasaklar. Eski uygulama "müşteri adı" = Z/Y önekli ad
  diyordu ve bu karar on bir ayrı dosyada ayrı ayrı (`^[ZY]…`, `startswith(('Z','Y'))`)
  yazılıydı. Müşteriye KAYITLI bir namespace (`/<NS>/`, SE03 kaydı + geliştirici lisansı) Z/Y
  kadar meşru müşteri ad alanıdır; SAP'nin kendi namespace'leri (`/SCWM/` …) standarttır.
  Ayrım "önek Z/Y mi" değil "ad alanı müşteriye mi ait" sorusudur ⇒ kayıtlı namespace'ler
  PROJEDEN okunur: `project.yaml` → `customer_namespaces: ["/<NS>/"]`.

KARAR (`musteri_adi_mi`)
  müşteri adı ⇔  `^[ZY][A-Z0-9_]*\\Z`
             ∨  kilit nesnesi (ENQU) ise `^E[ZY][A-Z0-9_]*\\Z`   (SAP: kilit nesnesi E ile başlar)
             ∨  `^<kayıtlı NS>[A-Z0-9_]+\\Z`                      (kilit nesnesi DAHİL — aşağıda)
  Büyük/küçük harf duyarsız (eski `re.IGNORECASE` korunur). `\\Z` (`$` DEĞİL): `$` sondaki
  tek `\\n`'i kabul eder (Q363②).
  Kilit nesnesi namespace'te ayrı kural ALMAZ: canlı ölçüm (2026-11-08, DEV, TADIR ENQU)
  namespace'li 1555 kilit nesnesinin 144'ünün `/<NS>/E…` biçiminde OLMADIĞINI gösterdi; ad
  zaten kayıtlı namespace ile başladığı için müşteri kararı E'ye bağlı değildir. `E/<NS>/…`
  biçimi tanınmaz (red, fail-closed).

YAPILANDIRMA (`namespace_yapilandirmasi`) — FAIL-CLOSED
  · anahtar yok / boş liste / project.yaml okunamıyor ⇒ () ⇒ bugünkü Z/Y davranışı BİREBİR.
  · değer liste değil ya da bir öğe `^/[A-Z0-9_]{1,8}/\\Z` değil (eğik çizgiler dahil ≤10)
    ⇒ HATA listesi döner ve TÜM liste devre dışı kalır (kısmen geçerli liste yarı açık
    kapı demektir). Hata sessiz düşmez: `red_gerekcesi` metnine girer.
  · ⛔ env `IX_CUSTOMER_NAMESPACES` BİLEREK OKUNMAZ (`project_config.cfg` env'i önceler):
    bir komutun önüne env koyarak izin listesini genişletmek guard'ı aşmanın en kısa yolu
    olurdu. Kaynak yalnız proje kökündeki `project.yaml`'dır.
  · ⚠ SINIR: çekirdek hangi namespace'in SAP'ye ait olduğunu bilmez ⇒ `["/SCWM/"]` gibi
    yanlış bir bildirim burada YAKALANAMAZ. Bildirim kullanıcı beyanıdır; yanlış bildirim
    ADR 0005-A ihlalidir (A-EK). Sistemde doğrulama (TRNSPACE) Parti 3'ün işidir.

FONKSİYON GRUBU (FUGR) ADLARI — canlı ölçüm 2026-11-08 (DEV, salt-GET)
  · namespace'siz grup `ZFG`: include `LZFG…`, ana program `SAPLZFG`.
  · namespace'li grup `/NS/FG`: include `/NS/LFG…`, ana program `/NS/SAPLFG`
    (ör. `/NS/LFGTOP`, `…U01`, `…UXX`).

PARTİ 2 İÇİN YER AYRILDI (Issue #397 parti planı — gövde BU modülde yazılacak, burada YOK):
  · `dosya_adi(ad)`      — yerel dosya adı `/` ↔ `#` (abapGit gösterimi `#ns#`) dönüşümü
  · `url_segmenti(ad)`   — ADT yol parçası (`/` → `%2F`) — bugün dağınık `quote(safe='')`
  · `uzunluk_siniri(tip)`— tip bazlı ad uzunluğu (namespace dahil)
  Bunları yazacak olan, AYNI `ad_namespace` / `namespace_yapilandirmasi` fonksiyonlarını
  kullanır; namespace biçimini ikinci kez tanımlamaz.
"""
from __future__ import annotations

import re
from pathlib import Path

ANAHTAR = "customer_namespaces"

_ZY = re.compile(r"^[ZY][A-Z0-9_]*\Z", re.IGNORECASE)
_KILIT_ZY = re.compile(r"^E[ZY][A-Z0-9_]*\Z", re.IGNORECASE)
_NS_BICIM = re.compile(r"^/[A-Z0-9_]{1,8}/\Z")
_AD_NS = re.compile(r"^(/[A-Za-z0-9_]{1,8}/)")
KILIT_TIPLERI = frozenset({"enqu", "lock", "lockobject", "lockobjects"})


def _kok(root) -> Path:
    if root:
        return Path(root)
    from utils.project_config import project_root  # lazy: komşu taban kopyaları import'u taşımaz
    return project_root()


def namespace_yapilandirmasi(root=None) -> tuple[tuple[str, ...], list[str]]:
    """`project.yaml` → (geçerli namespace'ler, hatalar). Hata varsa namespace'ler BOŞTUR."""
    try:
        from utils.project_config import _yaml_lite  # mevcut ayrıştırıcı (#391 tırnak düzeltmesi)
        yol = _kok(root) / "project.yaml"
        ham = _yaml_lite(str(yol)).get(ANAHTAR)
    except Exception as exc:  # noqa: BLE001 — okunamayan yapılandırma = namespace YOK
        return (), [f"{ANAHTAR} okunamadı ({type(exc).__name__}) — yalnız Z/Y geçerli"]
    if ham is None:
        return (), []
    if not isinstance(ham, list):
        return (), [f"{ANAHTAR} bir LİSTE olmalı (örn. {ANAHTAR}: [\"/<NS>/\"]); "
                    f"verilen: {ham!r} — namespace kabulü KAPALI"]
    gecerli: list[str] = []
    hatalar: list[str] = []
    for oge in ham:
        s = str(oge).upper()
        if not _NS_BICIM.match(s):
            hatalar.append(f"{ANAHTAR} öğesi geçersiz: {oge!r} (beklenen biçim /<NS>/, "
                           f"A-Z 0-9 _, en çok 8 karakter)")
        elif s not in gecerli:
            gecerli.append(s)
    if hatalar:
        return (), hatalar + [f"{ANAHTAR} hatalı olduğu için namespace kabulü KAPALI "
                              f"(yalnız Z/Y geçerli)"]
    return tuple(gecerli), []


def musteri_namespaceleri(root=None) -> tuple[str, ...]:
    return namespace_yapilandirmasi(root)[0]


def ad_namespace(ad: str) -> str | None:
    """`/NSPC/CL_X` → `/NSPC/` (büyük harf); namespace'siz ad → None. Kayıtlılığa BAKMAZ."""
    m = _AD_NS.match(ad or "")
    return m.group(1).upper() if m else None


def musteri_adi_mi(ad: str, object_type: str | None = None, *, namespaces=None, root=None) -> bool:
    """ADR 0005-A: ad müşteri ad alanında mı? (`namespaces` verilmezse projeden okunur)."""
    if not ad:
        return False
    if _ZY.match(ad):
        return True
    if object_type and object_type.lower() in KILIT_TIPLERI and _KILIT_ZY.match(ad):
        return True
    ns = ad_namespace(ad)
    if ns is None:
        return False
    kayitli = musteri_namespaceleri(root) if namespaces is None else tuple(
        str(n).upper() for n in namespaces)
    if ns not in kayitli:
        return False
    return re.match(r"^" + re.escape(ns) + r"[A-Z0-9_]+\Z", ad, re.IGNORECASE) is not None


def red_gerekcesi(ad: str, *, root=None) -> str:
    """Red metnine eklenecek NAMESPACE ayrıntısı ('' = ekleyecek bir şey yok)."""
    ns = ad_namespace(ad or "")
    if ns is None and not (ad or "").startswith("/"):
        return ""
    kayitli, hatalar = namespace_yapilandirmasi(root)
    if hatalar:
        return " · " + " · ".join(hatalar)
    if ns is None:
        return " · namespace biçimi tanınmadı (/<NS>/<AD>)"
    if ns not in kayitli:
        return (f" · namespace {ns} projede {ANAHTAR} ile müşteri namespace'i olarak "
                f"bildirilmemiş (SAP namespace'leri standarttır)")
    return f" · {ns} kayıtlı, ama namespace'ten sonraki ad geçersiz (A-Z 0-9 _, boş olamaz)"


def fugr_include_oneki(grup: str) -> str:
    """Grubun include öneki: `ZFG` → `LZFG` · `/NS/FG` → `/NS/LFG`."""
    g = (grup or "").strip().upper()
    ns = ad_namespace(g)
    return ns + "L" + g[len(ns):] if ns else "L" + g


def fugr_ana_program(grup: str) -> str:
    """Grubun ana programı: `ZFG` → `SAPLZFG` · `/NS/FG` → `/NS/SAPLFG`."""
    g = (grup or "").strip().upper()
    ns = ad_namespace(g)
    return ns + "SAPL" + g[len(ns):] if ns else "SAPL" + g
