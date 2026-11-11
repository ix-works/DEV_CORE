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
  · değer liste değil · bir öğe ASCII `^/[A-Z0-9_]{3,8}/\\Z` değil (eğik çizgiler dahil 5-10;
    `/___/` gibi harfsiz/rakamsız öğe de RED; #402 öncesi `{1,8}` idi) · anahtar project.yaml'da BİRDEN ÇOK kez yazılı
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

YEREL DOSYA ADI (`dosya_adi` — DEV_CORE #416 / Q403, yazma yönü; okuma yönü `dosya_adindan_ad`)
  `/NS/X` → `#ns#x` (abapGit gösterimi, küçük harf) · `ZX` → `zx`. Dosya adında `/` OLAMAZ:
  `Path(out) / "/ns/x.abap"` sürücü köküne kaçar (Windows `C:/ns/x.abap`) ⇒ ad dosya adına
  yalnız bu yardımcıdan geçerek yazılır. `dosya_adindan_ad(dosya_adi(x)) == x.upper()`.

KOMUT SATIRI RED METNİ (`musteri_adi_red_metni` — #416): CLI araçları (push_textpool ·
  pull_msag_textpool · scaffold_classic_program) red metnini TEK yerden alır. Git Bash `/` ile
  başlayan argümanı tırnaklı olsa da yol sanıp çevirir (ölçüldü 2026-11-11: `/NS/PROG` →
  `C:/Program Files/Git/NS/PROG`) ⇒ sürücü harfiyle başlayan adda `MSYS_NO_PATHCONV=1` ipucu.

PARTİ 2 İÇİN YER AYRILDI (Issue #397 parti planı — gövde BU modülde yazılacak, burada YOK):
  · `uzunluk_siniri(tip)`— tip bazlı ad uzunluğu (namespace dahil) (2c)
  Bunu yazacak olan, AYNI `ad_namespace` / `namespace_yapilandirmasi` fonksiyonlarını
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
# Namespace gövdesi — TEK sabit (DEV_CORE #402): yapılandırma (`_NS_BICIM`), ad içinden ayırma
# (`_AD_NS`) ve metinden yakalama (`AD_DESENI`) hepsi buradan türer. İç kısım 3-8 karakter: SAP
# (namespace `/` dahil 5-10) · abaplint `{3,8}` · DEV `TRNSPACE` ölçümü 2026-11-08 (1-2 karakterli 0
# satır). ⚠ SIKILAŞTIRMA (#402): önceki `{1,8}` 2 karakterli `/AB/`'yi kabul ediyordu; artık
# `customer_namespaces` öğesi olarak GEÇERSİZ ⇒ tüm liste kapalı + görünür hata (mevcut fail-closed).
NS_GOVDE = r"[A-Za-z0-9_]{3,8}"
_NS_BICIM = re.compile(r"^/(?=[A-Z0-9_]*[A-Z0-9])" + NS_GOVDE + r"/\Z")  # `/___/` RED: en az bir harf/rakam
_AD_NS = re.compile(r"^(/" + NS_GOVDE + r"/)")
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
                           f"A-Z 0-9 _, 3-8 karakter)")
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


_SURUCU_YOLU = re.compile(r"^[A-Za-z]:[/\\]")


def musteri_adi_red_metni(ad, *, root=None) -> str:
    """CLI araçlarının ortak red metni (#416): karar `musteri_adi_mi`'de, metin burada TEK yerde."""
    a = "" if ad is None else str(ad)
    ipucu = ""
    if _SURUCU_YOLU.match(a):
        ipucu = (" · ad bir Windows yoluna dönüşmüş görünüyor: Git Bash `/` ile başlayan argümanı "
                 "yol sanıp çevirir — komutun önüne MSYS_NO_PATHCONV=1 koy")
    return (f"yalnız müşteri ad alanı (Z/Y ya da bildirilmiş /<NS>/). Verilen: {a}"
            f"{red_gerekcesi(a, root=root)}{ipucu}")


# ── KAYNAK METİNDE AD YAKALAMA — TEK AD GRAMERİ (DEV_CORE #402) ──────────────────────────────
# NEDEN: validator'lar nesne adını kaynak metinden kendi desenleriyle (`(\w+)`, `[a-z][a-z0-9_]*`,
# `Z[A-Z]{2,4}\d{3}_C_\w+` …) yakalıyordu. `\w` `/` eşlemediği için namespace'li ad
# (`/NSPC/SD001_I_X`) hiç yakalanmıyor, kontrol KOŞMADAN "kapsam dışı / OK" dönüyordu (#402).
# Gramer burada TEK yerde yaşar; validator kendi ad desenini YAZMAZ (geri dönüş koruması:
# `tests/fixtures/validator_ad_grameri`).
#
# İKİ KATMAN (abapGit `zcl_abapgit_sap_namespace` + abaplint `allowed_object_naming` deseni):
#  · `AD_ADAYI`  — GEVŞEK yakalama: `/` ile başlayan HER belirteci tutar ki şekli bozuk
#                  namespace denemesi sessizce düşmesin (abapGit: başı `/` olup eşleşmeyen ad = HATA).
#  · `AD_DESENI` — KATI geçerlilik: `(?:/<3-8>/)?<gövde>`, A-Z 0-9 _ (ASCII). Dayanak: abaplint
#                  `{3,8}` · SAP OSPO "3 to 8" · DEV `TRNSPACE` ölçümü (2026-11-08): iç kısmı 1-2
#                  karakterli namespace 0 satır.
#  `ad_coz(aday)` ikisini birleştirir: katıya uyan ad döner, uymayan → ('', 'ad-cozulemedi')
#  ⇒ çağıran IX-GATE-STATUS `measured=false reason=ad-cozulemedi` basar (ÖLÇÜLEMEDİ, "OK" DEĞİL).
#  Yakalama ≠ karar: "müşterinin mi" kararı `musteri_karari` / `musteri_adi_mi`'dedir.
#  Namespace gövdesi `NS_GOVDE` yapılandırma katmanıyla ORTAKTIR (tek gramer).
AD_DESENI = r"(?a:(?:/" + NS_GOVDE + r"/)?[A-Za-z0-9_]+)"
_AD_DURAK = r"\s{}\[\]();,.:'\"<>=|`\-"
AD_ADAYI = r"(?a:/[^" + _AD_DURAK + r"]*|[A-Za-z0-9_]+)"
_AD_TAM = re.compile(r"\A" + AD_DESENI + r"\Z", re.IGNORECASE)
_AD_SINIR_ONCE = r"(?<![A-Za-z0-9_/])"
_AD_SINIR_SONRA = r"(?![A-Za-z0-9_/])"


def ad_gecerli_mi(ad) -> bool:
    """Ad katı gramere TAM uyuyor mu (`/NSPC/X` · `ZSD001_X`; `/AB/X` · `/NSPC/` · `` → False)."""
    return bool(ad) and _AD_TAM.match(str(ad)) is not None


def ad_coz(aday) -> tuple[str, str | None]:
    """(ad, None) ya da ('', 'ad-cozulemedi'). Harf DEĞİŞTİRİLMEZ (çağıran karar verir)."""
    a = "" if aday is None else str(aday)
    return (a, None) if ad_gecerli_mi(a) else ("", "ad-cozulemedi")


def ad_gecis_deseni(ad: str) -> str:
    """Metinde `ad`ın TAM geçişini arayan desen. `\\b` namespace'li adda `/` önünde tutmaz;
    sınır `[A-Za-z0-9_/]` dışıdır (`ZSD001_X` `ZSD001_X_Y` içinde bulunmaz)."""
    return _AD_SINIR_ONCE + re.escape(ad) + _AD_SINIR_SONRA


def musteri_karari(ad, object_type: str | None = None, *, namespaces=None, root=None) -> str:
    """'musteri' · 'standart' · 'namespace-kayitsiz' · 'ad-cozulemedi'.

    'namespace-kayitsiz' = ad katı gramere uyan namespace'li ad ama namespace projede
    `customer_namespaces` ile bildirilmemiş (ya da yapılandırma hatalı ⇒ liste kapalı):
    müşterinin bildirmediği kendi namespace'i mi, SAP'nin mi — buradan BİLİNEMEZ.
    """
    a = "" if ad is None else str(ad)
    if not ad_gecerli_mi(a):
        return "ad-cozulemedi"
    if musteri_adi_mi(a, object_type, namespaces=namespaces, root=root):
        return "musteri"
    return "namespace-kayitsiz" if a.startswith("/") else "standart"


def dosya_adindan_ad(parca) -> str:
    """Yerel dosya adının nesne-adı parçası → SAP adı (OKUMA yönü; #397 Parti 2b'nin yazma yarısı
    `dosya_adi` burada YOK). abapGit `#ns#x` · URL-kodlu `%23ns%23x` · AFF `(ns)x` → `/NS/X`;
    namespace'siz ad büyük harfe çevrilir. Biçim doğrulaması YAPMAZ (`ad_coz`'a ver)."""
    s = _unquote(str(parca or ""))
    m = re.match(r"^#([^#]*)#(.*)\Z", s, re.S) or re.match(r"^\(([^()]*)\)(.*)\Z", s, re.S)
    if m:
        s = "/" + m.group(1) + "/" + m.group(2)
    return s.upper()


def dosya_adi(ad) -> str:
    """SAP adı → yerel dosya adının nesne-adı parçası (YAZMA yönü; tersi `dosya_adindan_ad`).
    `/NS/X` → `#ns#x` (abapGit) · `ZX` → `zx`. Müşteri kararı VERMEZ (önce `musteri_adi_mi`);
    dönüşümden sonra `/` ya da `\\` kalırsa ValueError (dosya adı yol ayıracı taşıyamaz)."""
    a = str(ad or "").strip().upper()
    ns = ad_namespace(a)
    if ns:
        a = "#" + ns[1:-1] + "#" + a[len(ns):]
    if "/" in a or "\\" in a:
        raise ValueError(f"dosya adına çevrilemez (yol ayıracı kalıyor): {ad!r}")
    return a.lower()


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
