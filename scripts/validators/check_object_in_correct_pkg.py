"""
check_object_in_correct_pkg.py — Bir paketin alt klasörlerindeki dosyaların prefix'i
paket adıyla uyumlu mu kontrol eder.

Örnek ihlal: <source_root>/ZSD000_CLC/cds/ZSD001_DDL_FOO.cds (yanlış paket)

Whitelist (.rules.md "Bilinen İstisnalar / Legacy" bölümünden okunur — gelecek):
- ZSD001_CLC: ZCL_Z<...>_* (farklı-namespace istisna örneği)
- ZSD000_CLC: Z<MOD>_I_* (başka-modül namespace örneği, paket root'unda .txt olarak)

Kullanım:
    python scripts/validators/check_object_in_correct_pkg.py

Exit kodu:
    0 — Tüm dosyalar doğru pakette
    1 — Cross-package sızıntı tespit edildi
"""
# ENFORCES: C-RAP-PKG-01  (ADR 0019 coverage binding)
import argparse
import re
import sys
from pathlib import Path
import sys as _pc_sys
from pathlib import Path as _pc_Path
_pc_sys.path.insert(0, str(_pc_Path(__file__).resolve().parents[1]))
from utils.project_config import project_root,  SOURCE_ROOT_NAME  # K12: kaynak-klasor adi config'ten

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Paket bazlı istisnalar (adlandırma rehberince onaylı veya legacy)
# B10/K12: paket-istisnalari PROJE-CONFIG'ten. project.yaml:
#   package_exceptions: ["ZSD001_CLC:^ZCL_SD001_", "ZSD001_CLC:^ZIF_SD001_"]
from utils.project_config import cfg as _cfg
PACKAGE_EXCEPTIONS: dict = {}
for _e in (_cfg('package_exceptions') or []):
    if ':' in str(_e):
        _pkg, _rx = str(_e).split(':', 1)
        PACKAGE_EXCEPTIONS.setdefault(_pkg.strip(), []).append(_rx.strip())

# Sadece bu klasörlerde obje adı doğrulanır (root'taki .md/.txt'ler ve docs/ muaf)
CHECK_FOLDERS = {"cds", "classes", "programs", "structures", "tables", "functions", "auth"}

# Obje dosyası sayılan uzantılar (Path.suffix = SON nokta sonrası).
#
# ⚠ KAPSAM = BEYAN (2026-08-01 bug-avı, V2). Gate'in beyanı "paket klasöründeki obje
# dosyaları doğru paket prefix'ini taşır". Listede olmayan uzantı hiç GÖRÜLMEZ ve çıktı
# yine "[OK] ... doğru paket altında" der — "bakmadım" ile "temiz" ayırt edilemez.
# Canlı ölçüm: eski küme 340 dosya görüyordu, gerçek obje sayısı 392'ydi → 52 dosya
# (26 `.bdef`, 15 `.srvd`, 7 `.tabl.ddl`, 3 `.dcl`, 1 `.tabl`) hiçbir zaman kontrol
# edilmemişti; yanlış-paket-prefiksli bir BDEF/SRVD bu gate'ten sessizce geçerdi.
# Genişletme sonrası ihlal sayısı 0 → taban temiz, HARD kalabilir (PATTERN#14).
# Yeni bir SAP obje-uzantısı repoya girdiğinde BURAYA da eklenir (aksi hâlde sessiz boşluk).
OBJE_UZANTILARI = {".abap", ".cds", ".ddls", ".asddls", ".xml",
                   ".bdef", ".srvd", ".ddl", ".dcl", ".tabl"}

# Tooling scratch dizini artık .tmp/sap_scratch (ERP DIŞI, gitignored) — ZAI default'u
# KALDIRILDI (2026-06-18). <source_root>/ZAI ARTIK YASAK: belirirse bu check onu flag'ler
# (ZAI-resurgence guard). Başka scratch-modül yok → exclude kümesi BOŞ.
SCRATCH_MODULES: set = set()


def get_pkg_prefix(pkg_name: str) -> str:
    """ZSD001_CLC → ZSD001"""
    return pkg_name.replace("_CLC", "")


# NAMESPACE'Lİ PAKET (DEV_CORE Issue #391, 2026-11-07). abapGit gösteriminde `/NSPC/` → `#NSPC#`;
# namespace'li nesne adı paket kısa adıyla BAŞLAMAZ (`#NSPC#CL_SD001_X` ∈ `#NSPC#SD001`), ad alanı
# öneki önce gelir ⇒ önek kuralı her nesneyi "sızıntı" sayıyordu. Kabul YALNIZ iki şart birlikte
# sağlanınca: ① nesne paketle AYNI namespace önekini taşır ② paketin `.rules.md` Naming tablosundaki
# regex'lerden birine uyar. Ad kuralı burada YAZILMAZ — `check_package_naming.parse_rules_md`
# yeniden kullanılır (tek kaynak). `.rules.md` yok / tablo boş / regex derlenmiyor ⇒ kabul YOK
# (fail-closed, bugünkü davranış). Z paketlerinde bu dal hiç çalışmaz (davranış DEĞİŞMEDİ).
# Namespace gövdesi TEK gramerden (`ad_politikasi.NS_GOVDE`, 3-8 karakter — DEV_CORE #402). Eski
# `[A-Z0-9_]+` uzunluk sınırsızdı; gramer dışı `#AB#X` paketi artık namespace'li SAYILMAZ ⇒
# namespace kabul dalına girmez, önek kuralına düşer (fail-closed yön, ⚠ SIKILAŞTIRMA).
from utils.ad_politikasi import NS_GOVDE  # noqa: E402
_NS_RE = re.compile(r"^#" + NS_GOVDE + r"#")


def paket_namespace(pkg_name: str) -> str | None:
    """`#NSPC#SD001` → `#NSPC#`; namespace'siz paket → None."""
    m = _NS_RE.match(pkg_name.upper())
    return m.group(0) if m else None


def namespace_kurallari(pkg_dir: Path) -> list[str]:
    """Namespace'li paketin `.rules.md` Naming regex'leri (yoksa boş liste)."""
    if paket_namespace(pkg_dir.name) is None:
        return []
    _here = str(Path(__file__).resolve().parent)
    if _here not in sys.path:
        sys.path.insert(0, _here)
    from check_package_naming import parse_rules_md  # noqa: E402 (tek kaynak; kopyalanmaz)
    return [rx for _, rx in parse_rules_md(pkg_dir / ".rules.md")]


def matches_package(filename: str, pkg_prefix: str, pkg_name: str,
                    ns_kurallari: list[str] | None = None) -> bool:
    """Dosya adı paket prefix'iyle veya istisna pattern'iyle eşleşiyor mu?

    `ns_kurallari`: namespace'li paketin `.rules.md` Naming regex'leri
    (`namespace_kurallari`); verilmezse namespace dalı kapalıdır.
    """
    base = filename.split(".")[0].upper()
    if base.startswith(pkg_prefix.upper() + "_") or base == pkg_prefix.upper():
        return True

    # Paket-spesifik istisnalar
    for pattern in PACKAGE_EXCEPTIONS.get(pkg_name, []):
        if re.match(pattern, base):
            return True

    # Namespace'li paket: aynı namespace öneki + `.rules.md` Naming regex'i (ikisi birlikte)
    ns = paket_namespace(pkg_name)
    if ns and ns_kurallari and base.startswith(ns):
        for rx in ns_kurallari:
            try:
                if re.match(rx, base):
                    return True
            except re.error:
                continue        # derlenmeyen regex kabul ÜRETMEZ (fail-closed)

    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Obje paket sınır kontrolü")
    parser.add_argument("--source-root", default=SOURCE_ROOT_NAME, help="ERP root dizini")
    parser.add_argument("--strict", action="store_true", help="run_all_validators ile uyum için, no-op")
    args = parser.parse_args()

    _p = Path(args.source_root)
    erp_root = _p if _p.is_absolute() else (project_root() / _p)
    if not erp_root.exists():
        print(f"HATA: {erp_root} bulunamadı", file=sys.stderr)
        return 1

    violations = []
    # <source_root>/<MODULE>/<PKG>/ pattern'i
    packages = []
    for module_dir in sorted(erp_root.iterdir()):
        if not module_dir.is_dir() or module_dir.name.startswith("."):
            continue
        if module_dir.name in SCRATCH_MODULES:
            continue
        for pkg in sorted(module_dir.iterdir()):
            if pkg.is_dir() and not pkg.name.startswith("."):
                packages.append((module_dir.name, pkg))

    ns_paket = 0           # namespace'li paket sayısı
    ns_kurallsiz: list[str] = []   # namespace'li ama `.rules.md` Naming regex'i yok
    ns_kabul = 0           # yalnız namespace dalıyla kabul edilen dosya
    for module_name, pkg in packages:
        pkg_prefix = get_pkg_prefix(pkg.name)
        ns_kur = namespace_kurallari(pkg)
        if paket_namespace(pkg.name):
            ns_paket += 1
            if not ns_kur:
                ns_kurallsiz.append(f"{module_name}/{pkg.name}")

        for folder_name in CHECK_FOLDERS:
            folder = pkg / folder_name
            if not folder.exists():
                continue

            for f in folder.rglob("*"):
                if not f.is_file():
                    continue
                # Sadece kod/obje uzantılarını kontrol et
                if f.suffix.lower() not in OBJE_UZANTILARI:
                    continue
                # .ddls.asddls çift uzantı
                if f.name.endswith(".ddls.asddls"):
                    pass

                if not matches_package(f.name, pkg_prefix, pkg.name, ns_kur):
                    ek = ""
                    if paket_namespace(pkg.name):
                        ek = (" · namespace'li paket: `.rules.md` Naming regex'i YOK — namespace "
                              "kabulü uygulanmadı" if not ns_kur else
                              " · namespace'li paket: aynı namespace öneki + `.rules.md` Naming "
                              "regex'i birlikte sağlanmadı")
                    violations.append(
                        f"{module_name}/{pkg.name}/{folder_name}/{f.name}: "
                        f"paket prefix'i '{pkg_prefix}' veya istisna pattern'iyle eşleşmiyor{ek}"
                    )
                elif ns_kur and not matches_package(f.name, pkg_prefix, pkg.name):
                    ns_kabul += 1

    # KAPSAM BEYANI — namespace yolu her koşumda görünür (sıfır-bulgu anı dahil)
    kapsam = (f"namespace'li paket: {ns_paket} (`.rules.md` Naming regex'iyle kabul edilen dosya: "
              f"{ns_kabul}; regex'siz paket: {len(ns_kurallsiz)}"
              + (f" → {', '.join(ns_kurallsiz)}" if ns_kurallsiz else "") + ")")

    if violations:
        print("HATA — Cross-package sızıntı:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        print(f"  KAPSAM: {kapsam}", file=sys.stderr)
        return 1

    print(f"OK — {len(packages)} paketteki obje dosyaları doğru paket altında. KAPSAM: {kapsam}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
