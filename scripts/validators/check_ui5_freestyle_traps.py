"""
check_ui5_freestyle_traps.py — Freestyle UI5 + OData V2 statik TUZAK kontrolü (G3, ADR 0017).

Neden: Booking post-mortem (2026-06-16). Çalışan kardeş deseni (sip_se/ihr_se = oModel.update)
yerine sıfırdan yazılınca tekrar eden RUNTIME hatalar çıktı; bunlar yalnız kullanıcı test edince
ortaya çıkıyordu. Bu validator o tuzakların STATİK olanlarını build sırasında — kullanıcı
testinden ÖNCE — yakalar. (Runtime olanlar G1 smoke-test gate'inin işi.)

Tuzaklar:
  T1 (ERROR) V2 nav adı `_X` — RAP composition OData V2'de `to_X` olur (to_Container/to_Destination).
             createEntry("_..") / $expand:"_.." / path ".../_Cap" → Create kaydet + $expand
             SESSİZCE kırılır. (Booking: _Container → to_Container, _Destination → to_Destination.)
  T2 (WARN)  editable Input `type="Number"` — grid/miktar input'unda ok-tuşu değeri artırır +
             grid satır-gezmeyi bozar → type="Text" + liveChange (feedback_numeric-input-no-type-number).
             (Filtre "kaç kayıt" sayaç input'u meşru istisna → WARN, elle ayır.)
  T3 (WARN)  `<core:Title` view'de — VBox/HBox/CSSGrid child'ı olarak GEÇERSİZ → runtime crash
             ("not valid for aggregation items"). sap.m.Title kullan. (Form içinde geçerli → WARN.)
  T4 (ERROR) `sap.ui.layout.form` `<f:fields>` içinde LAYOUT-CONTAINER (HBox/VBox/FlexBox/Panel) —
             ColumnLayout form-content yalnız kontrol kabul eder → "Element sap.m.HBox is not a
             valid Form content" → diyalog/view RENDER-CRASH (AÇILMAZ). FE-33. Aynı container
             CSSGrid/VBox'ta GEÇERLİ (booking) → yalnız `<f:fields>` kapsamında flag (yanlış-poz yok).
             Çoklu-kontrol: HBox yerine sibling f:fields veya ayrı f:FormElement. XML-valid → node-check
             YAKALAMAZ; bu statik gate + runtime açılış (FE-17) birlikte. (shipment 2026-07-02.)

Kapsam: <source_root>/**/ui/**/webapp altındaki *.xml (view/fragment) + *.js (controller). node_modules,
dist, test elenir. JS'te yorumlar (satır + ÇOK-SATIRLI `/* */`) taramadan düşer — 2026-08-28
(B2-06) öncesi yalnız `//` ve hizalı `*` satırları atlanıyordu, yıldızsız blok yorumunun
içindeki ölü kod T1 ERROR (build DURDURAN yanlış-pozitif) üretiyordu.
XML'de `<!-- -->` yorumları T2/T3/T4 taramasından ÖNCE maskelenir (`_xml_yorum_maskele`,
2026-11-02 Q386): yorumdaki `<f:fields>` metni bir sonraki GERÇEK `</f:fields>`'e kadar
eşleşip aradaki form-dışı `VBox`/`HBox`/`Panel`'i T4 ERROR sayıyordu (build DURDURAN
yanlış-pozitif); T2/T3 aynı sınıftan WARN üretiyordu. Maske satır sonlarını KORUR ⇒
satır numaraları ham dosyayla aynıdır; ekrana basılan metin yine HAM satırdır.
Sınır (bilerek): kapanmamış `<!--` maskelenmez (taranmaya devam eder, fail-closed yön).
Aynı maskeleme `checklist_check._xml_kod` (FE-07/FE-33) ile birebir aynıdır.

Kullanım:
    python scripts/validators/check_ui5_freestyle_traps.py
    python scripts/validators/check_ui5_freestyle_traps.py --strict   # WARN'ları da fail say

Exit kodu:
    0 — ERROR yok (WARN olabilir; --strict ile WARN da fail)
    1 — En az bir ERROR (T1/T2) tuzağı
"""
import argparse
import re
import sys
from pathlib import Path
import sys as _pc_sys
from pathlib import Path as _pc_Path
_pc_sys.path.insert(0, str(_pc_Path(__file__).resolve().parents[1]))
from utils.project_config import project_root, source_dir  # K12: kaynak-klasor adi config'ten
# K1 (2026-08-20): ORTAK kapsam sozlesmesi — 'ihlal yok' ile 'bakacak dosya yok'
# ayrilir. 0 dosya FAIL URETMEZ (mesru olabilir), ama SESSIZ de gecmez.
from utils.kapsam import Kapsam  # noqa: E402
# B2-06 (2026-08-28): JS blok yorumu ORTAK katmanda, DOSYA GENELİNDE durumlu.
from utils.kaynak_tarama import js_kod  # noqa: E402

KAPSAM = Kapsam('webapp .js/.xml')   # K1: taranan dosya sayaci

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ADR 0020: junction'da __file__ DEV_CORE'a çözülür → kanonik project_root()/source_dir()
REPO = project_root()
ERP = source_dir()

_SKIP_SEGMENTS = {"node_modules", "dist", "tmp", ".tmp", "worktrees"}

# --- T1: V2 nav `_X` (entity adı DEĞİL; nav property). Entity-set'ler /Z ile başlar,
#     nav property'ler `_Cap` bare token veya `/_Cap` path segmenti. `/Z...` ve `to_...`
#     yanlış-pozitif vermez (regex'ler kasıtlı dar). ---
_T1_PATTERNS = [
    re.compile(r'createEntry\(\s*["\'`]_[A-Z]'),          # createEntry("_Container", ...)
    re.compile(r'/_[A-Z]'),                                # "/_Container", "')/_Destination"
    re.compile(r'\$expand["\'`]?\s*:\s*["\'`]_[A-Z]'),     # "$expand": "_Container"
]
# T1'i koda özgü tutmak için: yorum satırlarını ve $batch/url olmayanları azaltmak yerine
# pattern'leri dar tuttuk. `to_` zaten `_` ile başlamaz → güvenli.
#
# TIRNAK SINIFI `["\'`]` — ters-tırnak 2026-08-01'de EKLENDİ (bug-avı V6). Sınıf `["\']`
# iken ES6 template literal'i (`createEntry(`_Container`)` / ``$expand: `_Container` ``)
# desenin DIŞINDA kalıyordu; modern UI5 controller'ları template literal'i rutin kullanır,
# yani kaçış tesadüfi değil zamanla BÜYÜYEN bir boşluktu. T1 bir ERROR'dur (build DURUR):
# kaçan `_X` nav adı OData V2'de SESSİZCE kırılır (V2'de `to_X` olur) — tam olarak
# "gate var ama görmüyor" hâli.
# ⚠ KAPSAM DAR TUTULDU: 2. desen (`/_[A-Z]` yol segmenti) tırnaktan ZATEN bağımsızdır ve
# DEĞİŞTİRİLMEDİ — ölçüldü, ters-tırnaklı yol ifadelerini hâlihazırda yakalıyor.
# Kaçış YALNIZ `createEntry` ve `$expand` desenlerindeydi; kapsamı abartmak FP üretirdi.
# Canlı ölçüm: proje UI kodunda `createEntry(` HİÇ yok → 0 yeni bulgu, 0 FP (LATENT).

_T2_PATTERN = re.compile(r'type\s*=\s*"Number"')
_T3_PATTERN = re.compile(r'<core:Title\b')

# --- T4 (ERROR, FE-33): sap.ui.layout.form `<f:fields>` içinde LAYOUT-CONTAINER → render-crash.
#     Multiline: her `<f:fields>...</f:fields>` bloğunu yakala, içinde HBox/VBox/FlexBox/Panel ara.
#     Kapsam `f:fields` (Form field aggregation) → CSSGrid/VBox layout'taki geçerli container'lar
#     (booking) flag EDİLMEZ. `f` namespace prefix'i genelde `f:` ama esnek bıraktık. ---
_T4_FIELDS_RE = re.compile(r'<(?:\w+:)?fields\b[^>]*>(.*?)</(?:\w+:)?fields\s*>', re.DOTALL)
_T4_CONTAINER_RE = re.compile(r'<(?:\w+:)?(HBox|VBox|FlexBox|Panel)\b')

# --- XML yorum maskesi (Q386, 2026-11-02): T2/T3/T4 yalnız yorum DIŞINI görür. Yorumun
#     satır sonu dışındaki her karakteri boşluk olur → satır sayısı ve ofsetler değişmez.
_XML_YORUM_RE = re.compile(r'<!--.*?-->', re.DOTALL)


def _xml_yorum_maskele(metin: str) -> str:
    return _XML_YORUM_RE.sub(lambda m: re.sub(r'[^\n]', ' ', m.group(0)), metin)


def _iter_ui_files():
    if not ERP.exists():
        return
    import os
    # PERF: ERP.rglob("*") TÜM node_modules'ı (1184 dizin) dolaşıyordu → os.walk ile
    # ağır dizinleri YÜRÜYÜŞ ANINDA buda (dirnames in-place). Sonuç birebir aynı
    # (node_modules zaten _SKIP_SEGMENTS ile dışlanıyordu), yalnız ~35sn → ~ms.
    for dirpath, dirnames, filenames in os.walk(ERP):
        dirnames[:] = [d for d in dirnames if d.lower() not in _SKIP_SEGMENTS]
        parts = {p.lower() for p in Path(dirpath).parts}
        # yalnız bir webapp ağacının içindekiler
        if "webapp" not in parts:
            continue
        for fn in filenames:
            suf = Path(fn).suffix.lower()
            if suf == ".js" or suf == ".xml":
                yield Path(dirpath) / fn


def _scan():
    findings = []  # (severity, trap, file, lineno, text)
    for f in KAPSAM.say(_iter_ui_files()):
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        is_js = f.suffix.lower() == ".js"
        is_xml = f.suffix.lower() == ".xml"
        # B2-06: eski hâl `stripped.startswith("//")` VEYA `startswith("*")` idi —
        # yalnız JSDoc gibi HİZALI blokları atlıyordu. Yıldızsız çok-satırlı
        # `/* ... */` bloğunun içi KOD sayılıyor ve T1 bir ERROR olduğu için
        # yorumdaki ölü/örnek kod BUILD DURDURUYORDU (yanlış-pozitif). Blok durumu
        # artık dosya genelinde tutuluyor; satır numaraları ham dosyayla AYNI kalır
        # ve ekrana basılan metin yine HAM satırdır (bağlam kaybolmasın).
        js_kodlar = dict(js_kod("\n".join(lines))) if is_js else {}
        # Q386: XML yorumları maskeli içerik — satır sayısı `lines` ile AYNI.
        xml_icerik = _xml_yorum_maskele("\n".join(lines)) if is_xml else ""
        xml_satirlar = xml_icerik.split("\n") if is_xml else []
        for i, ln in enumerate(lines, 1):
            stripped = ln.strip()
            if is_js:
                kod = js_kodlar.get(i, "")
                if not kod.strip():
                    continue
                if any(p.search(kod) for p in _T1_PATTERNS):
                    findings.append(("ERROR", "T1 V2-nav `_X` (→ to_X)", f, i, stripped[:120]))
            if is_xml:
                kod = xml_satirlar[i - 1]
                if _T2_PATTERN.search(kod):
                    # WARN: filtre "kaç kayıt" sayaç input'u meşru istisna; grid/miktar input'u DEĞİL.
                    findings.append(("WARN", "T2 type=Number (grid/miktar ise → type=Text)", f, i, stripped[:120]))
                if _T3_PATTERN.search(kod):
                    findings.append(("WARN", "T3 core:Title (VBox/HBox/CSSGrid child ise crash → sap.m.Title)", f, i, stripped[:120]))
        # T4 (multiline): <f:fields> içi layout-container → Form/ColumnLayout render-crash (FE-33)
        if is_xml:
            content = xml_icerik
            for m in _T4_FIELDS_RE.finditer(content):
                cm = _T4_CONTAINER_RE.search(m.group(1))
                if cm:
                    off = m.start(1) + cm.start()
                    lineno = content.count("\n", 0, off) + 1
                    findings.append(("ERROR", f"T4 <f:fields> içi <{cm.group(1)}> (Form/ColumnLayout geçersiz form-content → diyalog AÇILMAZ, FE-33)", f, lineno, cm.group(0)))
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description="Freestyle UI5 + OData V2 statik tuzak kontrolü (G3)")
    ap.add_argument("--strict", action="store_true", help="WARN'ları da fail say")
    ap.add_argument("--quick", action="store_true", help="(uyumluluk için; bu kontrol zaten hızlı)")
    args = ap.parse_args()

    findings = _scan()
    errors = [x for x in findings if x[0] == "ERROR"]
    warns = [x for x in findings if x[0] == "WARN"]

    if not findings:
        print("Freestyle UI5 tuzak kontrolü: temiz (T1/T2/T3/T4 yok)." + KAPSAM.ek())
        return 0

    for sev, trap, f, ln, text in findings:
        rel = f.relative_to(REPO)
        tag = "[İHLAL]" if sev == "ERROR" else "[UYARI]"
        print(f"{tag} {rel}:{ln}  {trap}  → {text}")

    print()
    print(f"Özet: {len(errors)} ERROR (T1 V2-nav / T4 form-content), {len(warns)} WARN (T2/T3).")
    if errors:
        print("ERROR = T1 V2-nav `_X` sessiz kırılma (`to_X` kullan) VEYA T4 `<f:fields>` içi container (Form render-crash → sibling f:fields/ayrı FormElement). Build DURUR.")
    if warns and not errors:
        print("Yalnız WARN — elle teyit: type=Number grid/miktar mı (filtre-sayaç istisna) · core:Title VBox child mı.")

    if errors:
        return 1
    if warns and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
