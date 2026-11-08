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
  · değer liste değil · bir öğe ASCII `^/[A-Z0-9_]{1,8}/\\Z` değil (eğik çizgiler dahil ≤10;
    `/_/` gibi harfsiz/rakamsız öğe de RED) · anahtar project.yaml'da BİRDEN ÇOK kez yazılı
    ⇒ HATA listesi döner ve TÜM liste devre dışı kalır (kısmen geçerli liste yarı açık
    kapı demektir). Hata sessiz düşmez: `red_gerekcesi` metnine girer.
  · HANGİ project.yaml (bug-gate F2, 2026-11-08): sürecin ÇÖZDÜĞÜ `.conn_adt`'nin dizinindeki.
    Yazma hangi sisteme gidiyorsa izin listesi o projeden gelir ⇒ `CLAUDE_PROJECT_DIR=<başka
    dizin>` öneki ya da `--cwd B` listeyi bağlantıdan ayıramaz. Açık `root` verilir ve bağlantı
    dizininden farklıysa ⇒ namespace kabulü KAPALI. Bağlantı dosyası çözülemezse de KAPALI
    (bug-gate-2 F3 ölçümü: `.conn_adt`'siz dizin + env `ADT_SAP_URL=…` + `CLAUDE_PROJECT_DIR=<listesi
    /SCWM/ olan dizin>` ⇒ eski "project_root'a düş" kuralı `/SCWM/X_TABLE`'ı KABUL ediyordu; kimlik
    env'den gelebildiği için "dosya yoksa yazım da yok" varsayımı YANLIŞTI). Z/Y kabulü etkilenmez.
  · ⛔ env `IX_CUSTOMER_NAMESPACES` BİLEREK OKUNMAZ (`project_config.cfg` env'i önceler):
    bir komutun önüne env koyarak izin listesini genişletmek guard'ı aşmanın en kısa yolu
    olurdu. (Önceki metin "kaynak yalnız proje kökü" diyordu ve `CLAUDE_PROJECT_DIR` önekini
    atlıyordu — YANLIŞTI; düzeltme yukarıdaki madde.)
  · Önbellek: dosyanın (mtime, boyut)'u değişince yeniden okunur — uzun ömürlü MCP sürecinde
    silinen namespace /mcp yeniden başlatması BEKLEMEDEN kapanır (`_yaml_lite`'a dokunulmaz).
  · ⚠ SINIR: çekirdek hangi namespace'in SAP'ye ait olduğunu bilmez ⇒ `["/SCWM/"]` gibi
    yanlış bir bildirim burada YAKALANAMAZ. Bildirim kullanıcı beyanıdır; yanlış bildirim
    ADR 0005-A ihlalidir (A-EK). Sistemde doğrulama (TRNSPACE) Parti 3'ün işidir.

FONKSİYON GRUBU (FUGR) ADLARI — canlı ölçüm 2026-11-08 (DEV, salt-GET)
  · namespace'siz grup `ZFG`: include `LZFG…`, ana program `SAPLZFG`.
  · namespace'li grup `/NS/FG`: include `/NS/LFG…`, ana program `/NS/SAPLFG`
    (ör. `/NS/LFGTOP`, `…U01`, `…UXX`).

ADT YOL PARÇASI (`url_segmenti`, Parti 2a — canlı ölçüm 2026-11-08, DEV salt-GET)
  `/sap/bc/adt/ddic/structures/%2f<ns>%2f<ad>` (ve `%2F…`) → 200 · aynı uç kodlamasız (`…/structures//<ns>/<ad>`)
  → 404 "No suitable resource found". SAP kendi yanıtında da `packageRef adtcore:uri` değerini
  `%2f` kodlu verir. Z/Y adında çıktı eski `ad.lower()` ile BAYT BAYT aynıdır (özel karakter yok).
  İdempotent: önce `unquote` edilir ⇒ zaten kodlanmış ad (`%2fns%2fx`) `%252f`'ye ÇİFT KODLANMAZ
  (SAP adında `%` geçmez). Küçük harf: ADT yolları küçük harfle kurulur (eski davranış).

PARTİ 2 İÇİN YER AYRILDI (Issue #397 parti planı — gövde BU modülde yazılacak, burada YOK):
  · `dosya_adi(ad)`      — yerel dosya adı `/` ↔ `#` (abapGit gösterimi `#ns#`) dönüşümü (2b)
  · `uzunluk_siniri(tip)`— tip bazlı ad uzunluğu (namespace dahil) (2c)
  Bunları yazacak olan, AYNI `ad_namespace` / `namespace_yapilandirmasi` fonksiyonlarını
  kullanır; namespace biçimini ikinci kez tanımlamaz.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from urllib.parse import quote as _quote, unquote as _unquote


def url_segmenti(ad) -> str:
    """ADT URL'inin tek yol parçası: `ZSD001_T01` → `zsd001_t01` · `/NS/X` → `%2Fns%2Fx`.

    `quote(safe='')` büyük harfli kaçış üretir (`%2F`) — `object_types.get_object_url` ile aynı.
    """
    return _quote(_unquote(str(ad)).lower(), safe="")


def url_parcasindan_ad(parca) -> str:
    """`url_segmenti`'nin tersi: `%2Fns%2Fx` / `%2fns%2fx` → `/NS/X` (büyük harf)."""
    return _unquote(str(parca)).upper()

ANAHTAR = "customer_namespaces"

_ZY = re.compile(r"^[ZY][A-Z0-9_]*\Z", re.IGNORECASE)
_KILIT_ZY = re.compile(r"^E[ZY][A-Z0-9_]*\Z", re.IGNORECASE)
_NS_BICIM = re.compile(r"^/(?=[A-Z0-9_]*[A-Z0-9])[A-Z0-9_]{1,8}/\Z")  # `/_/` RED: en az bir harf/rakam
_AD_NS = re.compile(r"^(/[A-Za-z0-9_]{1,8}/)")
KILIT_TIPLERI = frozenset({"enqu", "lock", "lockobject", "lockobjects"})


def _baglanti_dizini() -> Path | None:
    """Sürecin ÇÖZDÜĞÜ `.conn_adt`'nin dizini (dosya yoksa / çözülemezse None).

    Yazma hangi sisteme gidecekse izin listesi de O projeden okunur (bug-gate F2, 2026-11-08):
    `CLAUDE_PROJECT_DIR=<başka dizin>` öneki ya da `--cwd B` listeyi bağlantıdan AYIRAMAZ.
    """
    lib = sys.modules.get("sap_adt_lib")
    if lib is None:
        try:
            import sap_adt_lib as lib  # type: ignore  # noqa: F811 — lazy, scripts/ sys.path'te
        except Exception:  # noqa: BLE001 — bağlantı modülü yok ⇒ bu süreçte SAP yazımı da yok
            return None
    try:
        p = lib.get_conn_path()
    except Exception:  # noqa: BLE001
        return None
    if not p:
        return None
    p = Path(p)
    return p.parent.resolve() if p.exists() else None


def _kok_coz(root) -> tuple[Path | None, str | None]:
    """(kök, hata). Bağlantı dosyası varsa kök ONUN dizinidir; verilen `root` ondan ayrışırsa
    hata (namespace kabulü KAPALI — fail-closed). Bağlantı dosyası çözülemezse de KAPALI: kimlik
    `.conn_adt` olmadan env'den (`ADT_SAP_*`) gelebilir ⇒ listenin hangi projeye ait olduğu
    bilinemez (bug-gate-2 F3, 2026-11-08 ölçüldü)."""
    baglanti = _baglanti_dizini()
    if baglanti is None:
        return None, (f"{ANAHTAR}: bağlantı dosyası (.conn_adt) çözülemedi — liste hangi projeye "
                      f"ait belirsiz (kimlik env'den gelebilir), namespace kabulü KAPALI")
    if root and Path(root).resolve() != baglanti:
        return None, (f"{ANAHTAR}: proje kökü ({Path(root).resolve()}) bağlantı dosyasının "
                      f"dizininden ({baglanti}) farklı — namespace kabulü KAPALI")
    return baglanti, None


_YAML_ONBELLEK: dict = {}


def _yaml_oku(yol: Path) -> tuple[dict, int]:
    """(ayrıştırılmış project.yaml, `customer_namespaces` anahtarının satır sayısı).

    `project_config._yaml_lite` süreç ömrünce önbelleklidir (lru_cache) ⇒ namespace silinse de
    uzun ömürlü süreçte (MCP) kabul sürerdi (bug-gate F5). Burada önbellek anahtarı dosyanın
    (mtime_ns, boyut)'udur; `_yaml_lite`'ın önbelleğine ve `sap_profile` davranışına DOKUNULMAZ.
    """
    from utils.project_config import _yaml_lite  # mevcut ayrıştırıcı (#391 tırnak düzeltmesi)
    try:
        st = os.stat(yol)
        anahtar = (st.st_mtime_ns, st.st_size)
    except OSError:
        anahtar = None
    kayit = _YAML_ONBELLEK.get(str(yol))
    if kayit is not None and kayit[0] == anahtar:
        return kayit[1], kayit[2]
    cozumle = getattr(_yaml_lite, "__wrapped__", _yaml_lite)
    veri = cozumle(str(yol))
    tekrar = 0
    if anahtar is not None:
        metin = Path(yol).read_text(encoding="utf-8-sig", errors="replace")
        tekrar = len(re.findall(r"^" + ANAHTAR + r"[ \t]*:", metin, re.M))
    _YAML_ONBELLEK[str(yol)] = (anahtar, veri, tekrar)
    return veri, tekrar


def namespace_yapilandirmasi(root=None) -> tuple[tuple[str, ...], list[str]]:
    """`project.yaml` → (geçerli namespace'ler, hatalar). Hata varsa namespace'ler BOŞTUR."""
    try:
        kok, kok_hatasi = _kok_coz(root)
        if kok_hatasi:
            return (), [kok_hatasi]
        veri, tekrar = _yaml_oku(kok / "project.yaml")
        ham = veri.get(ANAHTAR)
    except Exception as exc:  # noqa: BLE001 — okunamayan yapılandırma = namespace YOK
        return (), [f"{ANAHTAR} okunamadı ({type(exc).__name__}) — yalnız Z/Y geçerli"]
    if tekrar > 1:
        return (), [f"{ANAHTAR} project.yaml'da {tekrar} kez tanımlı — hangisinin geçerli olduğu "
                    f"belirsiz, namespace kabulü KAPALI"]
    if ham is None:
        return (), []
    if not isinstance(ham, list):
        return (), [f"{ANAHTAR} bir LİSTE olmalı (örn. {ANAHTAR}: [\"/<NS>/\"]); "
                    f"verilen: {ham!r} — namespace kabulü KAPALI"]
    gecerli: list[str] = []
    hatalar: list[str] = []
    for oge in ham:
        s = str(oge).upper()
        if not str(oge).isascii() or not _NS_BICIM.match(s):
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
    # re.ASCII: namespace yolunda `[A-Z]` Unicode harf kabul ETMEZ ('ı'/'ſ'/'K' → I/S/K eşlemesi
    # IGNORECASE'te sızardı). Z/Y yolu (`_ZY`) tabanla aynı bırakıldı — bkz. changelog notu.
    return re.match(r"^" + re.escape(ns) + r"[A-Z0-9_]+\Z", ad, re.IGNORECASE | re.ASCII) is not None


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
