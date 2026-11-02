#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UI5 FREESTYLE SABLONU (Issue #381) — kopyalanan şablon gate'lerden geçer + sürüm yüzeyi kuralı.

=== NEYI OLCER ===
`playbook/templates/ui5-freestyle/` bir kopyalama şablonudur: `app/` ORTAK gövde + `surum/<v>/` sürüm
parçası (tek dosya `webapp/util/SurumParca.js`). Bu koşucu şablonu iki sürüm parçasıyla ayrı ayrı
SENTETİK bir projeye kopyalar (`<kum>/SOURCE_CODES/SD/ZSD001_CLC/ui/sablon_<v>/`) ve:

  V1  ⭐ GATE      üç UI validator'ı GERÇEK giriş noktasından (alt süreç, CLAUDE_PROJECT_DIR=kum)
                   koşar → exit 0 VE "N ... tarandı" satırındaki N, kopyadan sayılan dosya sayısına
                   EŞİT (0 dosya = "temiz" değil, ölçülmedi — K1 kapsam sözleşmesi)
  V2  ⭐ YÜZEY     ortak gövdede (kopyada sürüm parçasının GETİRMEDİĞİ her dosya — parça kümesi
                   surum/<v>/webapp listesinden türetilir) sürüme bağlı desen YOK (YASAK listesi, 11):
                   IllustratedMessage · rowmodes · sap/m/VariantManagement · sap.m.VariantManagement ·
                   IAsyncContentCreation · addValidateToken · _validateOnPaste ·
                   data-sap-ui- (bootstrap öznitelik biçimi sürüme bağlı → index.html parçada) ·
                   "bundleUrl" (sap.app.i18n nesne biçimi 1.71'de yok) · rowsUpdated (Table olayı @since 1.86) ·
                   getSortOrder() ==/!= "None" (1.71 sortOrder varsayılanı Ascending, enum'da None yok)
  V3  ⭐ İMZA      iki SurumParca aynı üye kümesini verir; ortak gövdenin çağırdığı her üye iki parçada var
  V4  TAMLIK       manifest routing hedefi → view dosyası · view controllerName → controller dosyası ·
                   uygulama-içi sap.ui.define bağımlılığı → dosya (sürüm parçası bindirildikten SONRA) ·
                   view olay işleyicisi ".onX" → controller'da (ya da BaseController'da) tanımlı
  V2/V3 yorumları AYIKLANMIŞ metni ölçer: şablon yorumları sürüm API'lerini bilerek adıyla anar
                   (kural KODU ölçer). Ayıklama kaba bir regex'tir (JS "//" yalnız satır başı/boşluk sonrası).
  V5  TAMLIK       kullanılan her i18n anahtarı iki dilde de var; iki dosyanın anahtar kümesi aynı
  V6  ⭐ BOOTSTRAP index.html sürüm parçasından gelir (app/ kaynağında YOK) ve öznitelik biçimi sürüme uyar:
                   1.71 → tek kelime küçük harf (oninit · resourceroots · compatversion; tireli çok-kelime YOK —
                   1.71.85 tire→camel dönüşümü yapmaz) · 1.120 → kebab (on-init · resource-roots · compat-version)
  V7  MANIFEST     sap.app.i18n DİZGİ (1.71.85 Manifest._loadI18n `new URI(sI18n)` — nesne desteklenmez)
  V8  ⭐ EXCEL     ortak gövdede (Spreadsheet geçen .js) her `dataSource:` değeri `dataUrl` anahtarlı NESNE
                   DEĞİŞMEZİ — 1.71.85 Spreadsheet ListBinding kabul etmez (Spreadsheet-dbg.js:431-444; binding
                   dalı @since 1.73). V2 ad listesi bunu GÖREMEZ (Spreadsheet iki sürümde de var; fark kabul
                   edilen girdide). SINIR: sözdizimseldir — nesnenin içeriğinin (URL, count) doğruluğunu ölçmez.
  V9  ⭐ AYRIŞTIRMA kolon filtresi metni ham filtre değeri OLMAZ (sözdizimsel; davranış ölçümü DEĞİL):
                   V9a ortak gövdedeki her `DateFormat.getDateInstance(…)` çağrısı `strictParsing: true` taşır
                       (gevşek ayrıştırma 31.11 → 1 Aralık kaydırır; iki sürümde tarayıcıda ölçüldü, README §4)
                   V9b ortak gövdede `NumberFormat.getFloatInstance(…)` çağrısı var ve `parseAsString: true` taşır
                   V9c TablePersonalizer `_onColumnFilter` gövdesi `Tarih.metindenGun(` + `Sayi.metindenSayi(`
                       çağırır ve ham `v`'yi değer yapan `new Filter(…, FilterOperator.X, v)` YOK
                   SINIR: ayrıştırıcının DOĞRU sonuç verdiğini ölçmez (o, README §0 tarayıcı sondasıdır)
  N1-N3 ⭐ POZ.KONTROL validator'lar KOPYAYI gerçekten tarıyor: kopyaya bilinen kusur sokulunca
                   ilgili validator exit≠0 (N1 caseSensitive:false · N2 liste view sap.m.Table ·
                   N3 V2 nav "/_X")

=== MUTASYON KIPLERI (şablon kopyasını bozar; koşucu exit 1 = DÜŞTÜ beklenir) ===
  --mutasyon-yasak-api       ortak List.controller kopyasına IllustratedMessage bağımlılığı → V2
  --mutasyon-parca-eksik     sürüm parçası bindirilmez → V4 (util/SurumParca çözülmez)
  --mutasyon-hedef-view      kopyadan Change.view.xml silinir → V4
  --mutasyon-i18n            kopyanın i18n_tr dosyasından bir kullanılan anahtar silinir → V5
  --mutasyon-imza            1.71 parçasından bilesenArayuzleri silinir → V3
  --mutasyon-kapsam-sifir    kopya "ui"/"webapp" segmenti OLMAYAN yere konur → V1 (N=0 ⇒ FAIL)
  --mutasyon-index-ortakta   index.html ortak gövdede yaşıyormuş gibi (parça kümesinden çıkarılır) → V2 data-sap-ui- + V6a
  --mutasyon-index-bicim     1.71 kopyasında oninit → on-init (1.120 biçimi) → V6b
  --mutasyon-i18n-nesne      kopya manifest sap.app.i18n → {"bundleUrl": …} nesnesi → V2 "bundleUrl" + V7
  --mutasyon-rowsupdated     kopya List.view tablosuna rowsUpdated=".onRefresh" (var olan işleyici) → V2
  --mutasyon-sortorder-none  kopya List.controller siraliMi çağrısı → getSortOrder() === "None" → V2
  --mutasyon-spreadsheet-binding  kopya List.controller Spreadsheet dataSource nesnesi → oRowBinding → V8
  --mutasyon-tarih-gevsek    kopya util/Tarih getDateInstance({ strictParsing: true }) → getDateInstance() → V9a
  --mutasyon-sayi-ham        kopya TablePersonalizer sayı dalı filtre değeri sSayi → ham v → V9c

TAMAMEN CEVRIMDISI. SAP'ye / CDN'e istek YOK. Sürüm API kanıtı (CDN ölçümü) şablon README §4'tedir;
bu koşucu onu yeniden ölçmez, yalnız ortak gövdenin o yüzeye SIZMADIĞINI zorlar.

Kosum: python tests/fixtures/ui5_freestyle_sablon/run.py          (exit 0 = PASS)
Kosucu: tests/run_fixture_tests.py (OZEL_TESTLER)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

GECERLI_KIP = {"--mutasyon-yasak-api", "--mutasyon-parca-eksik", "--mutasyon-hedef-view",
               "--mutasyon-i18n", "--mutasyon-imza", "--mutasyon-kapsam-sifir",
               "--mutasyon-index-ortakta", "--mutasyon-index-bicim", "--mutasyon-i18n-nesne",
               "--mutasyon-rowsupdated", "--mutasyon-sortorder-none", "--mutasyon-spreadsheet-binding",
               "--mutasyon-tarih-gevsek", "--mutasyon-sayi-ham"}
for _a in sys.argv[1:]:
    if _a not in GECERLI_KIP:
        print(f"[DURDU] bilinmeyen kip: {_a!r} — gecerli: {sorted(GECERLI_KIP)}")
        sys.exit(2)
KIP = set(sys.argv[1:])

CORE = Path(__file__).resolve().parents[3]
SABLON = CORE / "playbook" / "templates" / "ui5-freestyle"
VALIDATORS = CORE / "scripts" / "validators"
SURUMLER = ("1.120", "1.71")
NS_YOL = "com/example/alan/uygulama/"
NS_NOKTA = "com.example.alan.uygulama."

# (etiket, desen) — etiketler README §4 listesiyle birebir; desen yorumu ayıklanmış metne uygulanır.
YASAK = tuple((d, re.compile(re.escape(d))) for d in (
    "IllustratedMessage", "rowmodes", "sap/m/VariantManagement", "sap.m.VariantManagement",
    "IAsyncContentCreation", "addValidateToken", "_validateOnPaste",
    "data-sap-ui-", '"bundleUrl"', "rowsUpdated")) + (
    ('getSortOrder() == "None"', re.compile(r"""getSortOrder\(\)\s*[!=]==?\s*["']None["']""")),)
PARCA_UYELERI = ("surum", "satirModu", "bosDurum", "yapistirmaBagla", "bilesenArayuzleri", "siraliMi",
                 "dogrulayiciMetni")
# V6: index.html bootstrap öznitelikleri (sürüm → zorunlu ad kümesi)
BOOT_ZORUNLU = {"1.71": {"oninit", "resourceroots", "compatversion"},
                "1.120": {"on-init", "resource-roots", "compat-version"}}

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul), detay))


def dur(neden: str) -> None:
    print(f"[DURDU] KURULAMADI: {neden}")
    sys.exit(2)


if not (SABLON / "app" / "webapp" / "manifest.json").is_file():
    dur(f"şablon yok: {SABLON}")
for _v in SURUMLER:
    if not (SABLON / "surum" / _v / "webapp" / "util" / "SurumParca.js").is_file():
        dur(f"sürüm parçası yok: surum/{_v}")


def oku(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def yaz(p: Path, s: str) -> None:
    p.write_text(s, encoding="utf-8", newline="\n")


def parca_kumesi(surum: str) -> set[str]:
    """Sürüm parçasının kopyaya GETİRDİĞİ dosyalar (uygulama köküne göre, '/' ayraçlı)."""
    kok = SABLON / "surum" / surum
    return {p.relative_to(kok).as_posix() for p in (kok / "webapp").rglob("*") if p.is_file()}


def kur(kum: Path, surum: str, alt: str = "ui", bindir: bool = True) -> Path:
    """Şablonu sentetik projeye kopyalar; uygulama kökünü (webapp'in üstü) döndürür."""
    (kum / "project.yaml").write_text("source_root: SOURCE_CODES\n", encoding="utf-8")
    hedef = kum / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / alt / f"sablon_{surum.replace('.', '_')}"
    shutil.copytree(SABLON / "app", hedef)
    if bindir:
        shutil.copytree(SABLON / "surum" / surum / "webapp", hedef / "webapp", dirs_exist_ok=True)
    return hedef


def validator(kum: Path, ad: str) -> tuple[int, str]:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(kum)
    for k in list(env):
        if k.startswith("IX_"):
            env.pop(k)          # project_config IX_<KEY> önceliği kumu ezmesin
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, str(VALIDATORS / f"{ad}.py")], cwd=str(kum), env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def tarandi(cikti: str) -> int | None:
    m = re.findall(r"\((\d+)\s[^()]*tarandı\)", cikti)
    return int(m[-1]) if m else None


def say(kok: Path, suz) -> int:
    n = 0
    for dp, dn, fn in os.walk(kok):
        dn[:] = [d for d in dn if d.lower() not in {"node_modules", "dist"}]
        for f in fn:
            if suz(Path(dp) / f):
                n += 1
    return n


def define_bagimliliklari(js: str) -> list[str]:
    m = re.search(r"sap\.ui\.define\(\s*\[(.*?)\]", js, re.S)
    return re.findall(r'"([^"]+)"', m.group(1)) if m else []


def i18n_anahtarlari(p: Path) -> set[str]:
    out = set()
    for ln in oku(p).splitlines():
        s = ln.strip()
        if s and not s.startswith("#") and "=" in s:
            out.add(s.split("=", 1)[0].strip())
    return out


def kullanilan_anahtarlar(webapp: Path) -> set[str]:
    out: set[str] = set()
    for p in webapp.rglob("*"):
        if p.suffix == ".xml":
            out |= set(re.findall(r"i18n>([\w.]+)", oku(p)))
        elif p.suffix == ".js":
            s = oku(p)
            out |= set(re.findall(r'(?:i18n|_txt)\(\s*"([\w.]+)"', s))
            out |= set(re.findall(r'\b(?:i18n|lbl)\s*:\s*"([\w.]+)"', s))
        elif p.name == "manifest.json":
            out |= set(re.findall(r"\{\{(\w+)\}\}", oku(p)))
    return out


def yorumsuz(p: Path) -> str:
    """Yorumları ayıklanmış metin: yüzey/imza kuralı KODU ölçer, belgeleyen yorumu değil
    (şablon yorumları sürüm API'lerini bilerek ADIYLA anar)."""
    s = oku(p)
    if p.suffix == ".js":
        s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
        s = re.sub(r"(?m)(^|\s)//.*$", r"\1", s)
    elif p.suffix in {".xml", ".html"}:
        s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    elif p.suffix in {".yaml", ".properties"}:
        s = re.sub(r"(?m)^\s*#.*$", "", s)
    return s


def nesne_degismezi(s: str, i: int) -> str | None:
    """s[i]'de başlayan `{...}` nesne değişmezini (dengeli parantez, dizgi içi parantez atlanır) döndürür; s[i] '{'
    değilse ya da kapanmıyorsa None."""
    if i >= len(s) or s[i] != "{":
        return None
    derinlik, tirnak = 0, None
    for j in range(i, len(s)):
        c = s[j]
        if tirnak:
            if c == "\\":
                continue
            if c == tirnak and s[j - 1] != "\\":
                tirnak = None
            continue
        if c in "\"'":
            tirnak = c
        elif c == "{":
            derinlik += 1
        elif c == "}":
            derinlik -= 1
            if derinlik == 0:
                return s[i:j + 1]
    return None


def parca_uyeleri(js: str) -> set[str]:
    govde = js[js.find("return {"):]
    return set(re.findall(r"^\s{4}(\w+)\s*:", govde, re.M))


# ── uygulama ağacı denetimleri (V2-V5) — KOPYA üzerinde ─────────────────────────────────────
def agac_denetle(app: Path, surum: str, parca: set[str]) -> None:
    w = app / "webapp"
    etiket = f"[{surum}]"

    # V2 sürüm yüzeyi: sürüm parçasının getirmediği (= ortak gövdeden gelen) her metin dosyası
    sizinti, n_ortak = [], 0
    for p in app.rglob("*"):
        if not p.is_file() or p.relative_to(app).as_posix() in parca \
                or p.suffix not in {".js", ".xml", ".json", ".html", ".yaml", ".properties"}:
            continue
        n_ortak += 1
        s = yorumsuz(p)
        for d, rx in YASAK:
            if rx.search(s):
                sizinti.append(f"{p.relative_to(app).as_posix()}:{d}")
    kontrol(f"V2 {etiket} ortak gövdede ({n_ortak} dosya) sürüme bağlı desen YOK", not sizinti and n_ortak > 0,
            ", ".join(sizinti[:6]))

    # V6 bootstrap: index.html parçadan gelir, öznitelik biçimi sürüme uyar
    kontrol(f"V6a {etiket} index.html sürüm parçasından gelir", "webapp/index.html" in parca
            and (w / "index.html").is_file(), f"parça: {sorted(parca)}")
    if (w / "index.html").is_file():
        adlar = set(re.findall(r"\bdata-sap-ui-([a-z][a-z-]*)\s*=", yorumsuz(w / "index.html")))
        if surum == "1.71":
            hata = sorted(a for a in adlar if "-" in a) + sorted(BOOT_ZORUNLU[surum] - adlar)
        else:
            hata = sorted(BOOT_ZORUNLU[surum] - adlar)
        kontrol(f"V6b {etiket} bootstrap öznitelik biçimi sürüme uyar ({len(adlar)} öznitelik)",
                bool(adlar) and not hata, f"uymayan/eksik: {hata}")

    # V7 manifest sap.app.i18n dizgi
    i18n_kip = json.loads(oku(w / "manifest.json"))["sap.app"].get("i18n")
    kontrol(f"V7 {etiket} manifest sap.app.i18n dizgi", isinstance(i18n_kip, str),
            f"tip: {type(i18n_kip).__name__}")

    # V8 Spreadsheet dataSource: ortak gövdede `dataUrl` anahtarlı nesne değişmezi (binding/değişken DEĞİL)
    ds_hata, n_ds = [], 0
    for p in app.rglob("*.js"):
        rel = p.relative_to(app).as_posix()
        if rel in parca:
            continue
        s = yorumsuz(p)
        if "Spreadsheet" not in s:
            continue
        for m in re.finditer(r"\bdataSource\s*:\s*", s):
            n_ds += 1
            lit = nesne_degismezi(s, m.end())
            if lit is None or not re.search(r"\bdataUrl\s*:", lit):
                ds_hata.append(f"{rel}: dataSource: {s[m.end():m.end() + 24]!r}")
    kontrol(f"V8 {etiket} Spreadsheet dataSource ({n_ds}) dataUrl'li nesne değişmezi", n_ds > 0 and not ds_hata,
            "; ".join(ds_hata[:3]) or "ortak gövdede Spreadsheet dataSource bulunamadı")

    # V9 kolon filtresi ayrıştırması: tarih SIKI, sayı oturum biçimiyle, ham metin filtre değeri DEĞİL
    gevsek, n_dt, float_ok, n_fl = [], 0, [], 0
    for p in app.rglob("*.js"):
        rel = p.relative_to(app).as_posix()
        if rel in parca:
            continue
        s = yorumsuz(p)
        for m in re.finditer(r"\bgetDateInstance\(", s):
            n_dt += 1
            arg = s[m.end():s.find(")", m.end())]
            if not re.search(r"\bstrictParsing\s*:\s*true\b", arg):
                gevsek.append(f"{rel}: getDateInstance({arg.strip()[:30]})")
        for m in re.finditer(r"\bgetFloatInstance\(", s):
            n_fl += 1
            arg = s[m.end():s.find(")", m.end())]
            float_ok.append(bool(re.search(r"\bparseAsString\s*:\s*true\b", arg)))
    kontrol(f"V9a {etiket} getDateInstance ({n_dt}) strictParsing: true taşır", n_dt > 0 and not gevsek,
            "; ".join(gevsek[:3]) or "ortak gövdede getDateInstance yok")
    kontrol(f"V9b {etiket} getFloatInstance ({n_fl}) parseAsString: true taşır", n_fl > 0 and all(float_ok),
            f"parseAsString'siz: {float_ok.count(False)}")
    tp = yorumsuz(w / "util" / "TablePersonalizer.js")
    i0 = tp.find("_onColumnFilter:")
    i1 = tp.find("_parseSearchTerm:", i0)
    govde_cf = tp[i0:i1] if i0 >= 0 and i1 > i0 else ""
    ham = re.findall(r"new Filter\(\s*\w+\s*,\s*FilterOperator\.\w+\s*,\s*v\s*\)", govde_cf)
    eksik_cf = [c for c in ("Tarih.metindenGun(", "Sayi.metindenSayi(") if c not in govde_cf]
    kontrol(f"V9c {etiket} kolon filtresi tarih/sayı ayrıştırır, ham metin filtre değeri yok",
            bool(govde_cf) and not ham and not eksik_cf,
            f"gövde: {'var' if govde_cf else 'YOK'} · ham: {ham[:2]} · eksik çağrı: {eksik_cf}")

    # V3 imza: ortak gövdenin çağırdığı her SurumParca üyesi bu parçada var
    parca = w / "util" / "SurumParca.js"
    uyeler = parca_uyeleri(oku(parca)) if parca.is_file() else set()
    cagrilan = set()
    for p in w.rglob("*.js"):
        if p.name != "SurumParca.js":
            cagrilan |= set(re.findall(r"SurumParca\.(\w+)", yorumsuz(p)))
    eksik_uye = sorted((cagrilan | set(PARCA_UYELERI)) - uyeler)
    kontrol(f"V3 {etiket} parça üyeleri tam (çağrılan {len(cagrilan)})", bool(not eksik_uye and cagrilan),
            f"eksik: {eksik_uye}")

    # V4a manifest hedefi → view
    man = json.loads(oku(w / "manifest.json"))
    hedefler = man["sap.ui5"]["routing"]["targets"]
    yok_view = [t["name"] for t in hedefler.values() if not (w / "view" / f"{t['name']}.view.xml").is_file()]
    kok_view = man["sap.ui5"]["rootView"]["viewName"].replace(NS_NOKTA, "").replace(".", "/") + ".view.xml"
    if not (w / kok_view).is_file():
        yok_view.append(kok_view)
    kontrol(f"V4a {etiket} {len(hedefler)} hedef + rootView → view dosyası", not yok_view, f"yok: {yok_view}")

    # V4b view controllerName → controller
    yok_ctrl = []
    for v in (w / "view").glob("*.view.xml"):
        m = re.search(r'controllerName="([^"]+)"', oku(v))
        if m and not (w / (m.group(1).replace(NS_NOKTA, "").replace(".", "/") + ".controller.js")).is_file():
            yok_ctrl.append(v.name)
    kontrol(f"V4b {etiket} view → controller dosyası", not yok_ctrl, f"yok: {yok_ctrl}")

    # V4d view olay işleyicisi ".onX" → controller'da (ya da BaseController'da) tanımlı
    yok_isl = []
    taban = oku(w / "controller" / "BaseController.js")
    for v in (w / "view").glob("*.view.xml"):
        c = w / "controller" / (v.name[: -len(".view.xml")] + ".controller.js")
        govde = (oku(c) if c.is_file() else "") + taban
        for h in sorted(set(re.findall(r'="\.(\w+)"', yorumsuz(v)))):
            if not re.search(r"\b" + h + r"\s*:\s*function", govde):
                yok_isl.append(f"{v.name}:{h}")
    kontrol(f"V4d {etiket} view olay işleyicileri controller'da var", not yok_isl, f"yok: {yok_isl}")

    # V4c uygulama-içi define bağımlılığı → dosya
    yok_dep = []
    n_dep = 0
    for p in w.rglob("*.js"):
        for d in define_bagimliliklari(oku(p)):
            if d.startswith(NS_YOL):
                n_dep += 1
                if not (w / (d[len(NS_YOL):] + ".js")).is_file():
                    yok_dep.append(f"{p.name}→{d[len(NS_YOL):]}")
    kontrol(f"V4c {etiket} {n_dep} uygulama-içi bağımlılık çözülür", n_dep > 0 and not yok_dep,
            f"çözülmeyen: {sorted(set(yok_dep))}")

    # V5 i18n
    en = i18n_anahtarlari(w / "i18n" / "i18n.properties")
    tr = i18n_anahtarlari(w / "i18n" / "i18n_tr.properties")
    kul = kullanilan_anahtarlar(w)
    kontrol(f"V5a {etiket} {len(kul)} kullanılan anahtar iki dilde de var",
            bool(kul) and kul <= en and kul <= tr,
            f"EN eksik: {sorted(kul - en)[:5]} · TR eksik: {sorted(kul - tr)[:5]}")
    kontrol(f"V5b {etiket} EN/TR anahtar kümesi aynı", en == tr, f"fark: {sorted(en ^ tr)[:5]}")


# ── V1: gate'ler kopyayı tarar ve temiz der ─────────────────────────────────────────────────
GATE_SAYICI = {
    "check_ui5_freestyle_traps": lambda p: "webapp" in {x.lower() for x in p.parts} and p.suffix.lower() in {".js", ".xml"},
    "check_list_view_grid": lambda p: "ui" in {x.lower() for x in p.parts} and p.name.lower().endswith(".view.xml"),
    # bu gate .js + yalnız adı "filter.view.xml" olan view'i tarar (scripts/validators/check_filter_search_pattern.py)
    "check_filter_search_pattern": lambda p: "ui" in p.parts
    and (p.suffix == ".js" or p.name.lower() == "filter.view.xml"),
}


with tempfile.TemporaryDirectory(prefix="ui5sablon_") as _t:
    kok = Path(_t)

    # ── Ana kum: iki sürüm aynı sentetik projede ──
    kum = kok / "ana"
    kum.mkdir()
    alt = "x" if "--mutasyon-kapsam-sifir" in KIP else "ui"
    uygulamalar, parcalar = {}, {}
    for v in SURUMLER:
        app = kur(kum, v, alt=alt, bindir="--mutasyon-parca-eksik" not in KIP)
        uygulamalar[v] = app
        parcalar[v] = parca_kumesi(v) if "--mutasyon-parca-eksik" not in KIP else set()
        w = app / "webapp"
        if "--mutasyon-index-ortakta" in KIP:
            parcalar[v].discard("webapp/index.html")   # F1 geri dönüşü: index.html app/'te yaşıyormuş gibi
        if "--mutasyon-index-bicim" in KIP and v == "1.71":
            p = w / "index.html"
            yaz(p, oku(p).replace("data-sap-ui-oninit=", "data-sap-ui-on-init=", 1))
        if "--mutasyon-i18n-nesne" in KIP:
            p = w / "manifest.json"
            yaz(p, oku(p).replace('"i18n": "i18n/i18n.properties",',
                                  '"i18n": { "bundleUrl": "i18n/i18n.properties", "supportedLocales": ["", "tr"] },', 1))
        if "--mutasyon-rowsupdated" in KIP:
            p = w / "view" / "List.view.xml"
            yaz(p, oku(p).replace('threshold="200"', 'threshold="200"\n                   rowsUpdated=".onRefresh"', 1))
        if "--mutasyon-sortorder-none" in KIP:
            p = w / "controller" / "List.controller.js"
            yaz(p, oku(p).replace("!SurumParca.siraliMi(oCol)", 'oCol.getSortOrder() === "None"', 1))
        if "--mutasyon-spreadsheet-binding" in KIP:
            p = w / "controller" / "List.controller.js"
            s = oku(p)
            m = re.search(r"dataSource:\s*", s)
            lit = nesne_degismezi(s, m.end()) if m else None
            if not lit:
                dur("spreadsheet-binding: çapa 'dataSource: {' List.controller içinde yok")
            yaz(p, s[:m.end()] + "oRowBinding" + s[m.end() + len(lit):])
        if "--mutasyon-tarih-gevsek" in KIP:
            p = w / "util" / "Tarih.js"
            s = oku(p)
            if s.count("getDateInstance({ strictParsing: true })") != 1:
                dur("tarih-gevsek: çapa 'getDateInstance({ strictParsing: true })' util/Tarih içinde tek değil")
            yaz(p, s.replace("getDateInstance({ strictParsing: true })", "getDateInstance()"))
        if "--mutasyon-sayi-ham" in KIP:
            p = w / "util" / "TablePersonalizer.js"
            s = oku(p)
            if s.count("new Filter(sProp, FilterOperator.EQ, sSayi)") != 1:
                dur("sayi-ham: çapa 'new Filter(sProp, FilterOperator.EQ, sSayi)' TablePersonalizer içinde tek değil")
            yaz(p, s.replace("new Filter(sProp, FilterOperator.EQ, sSayi)", "new Filter(sProp, FilterOperator.EQ, v)"))
        if "--mutasyon-yasak-api" in KIP:
            p = w / "controller" / "List.controller.js"
            s = oku(p)
            yaz(p, s.replace('"sap/m/MessageBox",', '"sap/m/MessageBox",\n  "sap/m/IllustratedMessage",', 1))
        if "--mutasyon-hedef-view" in KIP:
            (w / "view" / "Change.view.xml").unlink()
        if "--mutasyon-i18n" in KIP:
            p = w / "i18n" / "i18n_tr.properties"
            yaz(p, "\n".join(ln for ln in oku(p).splitlines() if not ln.startswith("msg.saved=")) + "\n")
        if "--mutasyon-imza" in KIP and v == "1.71":
            p = w / "util" / "SurumParca.js"
            yaz(p, re.sub(r"\n\s{4}bilesenArayuzleri:[^\n]*\n", "\n", oku(p)))

    for ad, suz in GATE_SAYICI.items():
        rc, out = validator(kum, ad)
        beklenen = say(kum / "SOURCE_CODES", suz)
        n = tarandi(out)
        kontrol(f"V1 {ad} exit 0", rc == 0, out.strip().splitlines()[-1][:160] if out.strip() else "çıktı yok")
        kontrol(f"V1 {ad} kapsam N={n} == kopyadaki {beklenen} > 0", n is not None and n == beklenen and n > 0,
                "kapsam satırı okunamadı" if n is None else "")

    for v, app in uygulamalar.items():
        agac_denetle(app, v, parcalar[v])

    # ── N1-N3: bilinen kusur kopyaya sokulunca validator ısırır (ayrı kum, 1.120 kopyası) ──
    NEG = [
        ("N1", "check_filter_search_pattern", "controller/List.controller.js",
         "return new Filter(sProp, sOp, v1);", "return new Filter({ path: sProp, operator: sOp, value1: v1, caseSensitive: false });"),
        ("N2", "check_list_view_grid", "view/List.view.xml", None, None),
        ("N3", "check_ui5_freestyle_traps", "controller/Change.controller.js",
         'mParams["$expand"] = C.nav;', 'mParams["$expand"] = C.nav; var sYanlis = "/_Item";'),
    ]
    for kod, ad, dosya, eski, yeni in NEG:
        nk = kok / f"neg_{kod}"
        nk.mkdir()
        app = kur(nk, "1.120")
        p = app / "webapp" / dosya
        s = oku(p)
        if kod == "N2":
            yeni_s = re.sub(r"<table:Table\b.*?</table:Table>",
                            '<Table id="listTable" items="{/ZSD001_C_LIST}"><columns>'
                            + "".join(f"<Column><Text text=\"k{i}\"/></Column>" for i in range(7))
                            + "</columns></Table>", s, flags=re.S)
            yeni_s = yeni_s.replace('xmlns:table="sap.ui.table"', "")
        else:
            if s.count(eski) != 1:
                dur(f"{kod}: çapa {eski!r} {dosya} içinde {s.count(eski)} kez")
            yeni_s = s.replace(eski, yeni)
        if yeni_s == s:
            dur(f"{kod}: kusur sokulamadı ({dosya})")
        yaz(p, yeni_s)
        rc, out = validator(nk, ad)
        kontrol(f"{kod} {ad} kopyadaki kusuru yakalar (exit≠0)", rc != 0 and "Traceback" not in out,
                f"rc={rc} · {out.strip().splitlines()[-1][:120] if out.strip() else ''}")

gecen = sum(1 for _, ok, _ in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'OK' if ok else 'FAIL'}] {ad}" + (f"  — {detay}" if (detay and not ok) else ""))
mod = f"  (kip: {' '.join(sorted(KIP))})" if KIP else ""
print(f"\n{gecen}/{len(SONUC)} OK{mod}")
sys.exit(0 if gecen == len(SONUC) else 1)
