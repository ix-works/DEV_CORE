"""
check_package_naming.py — Her paketin `.rules.md`'sindeki regex'lere göre dosya adlarını doğrular.

Mantık:
1. `.rules.md` içindeki "Naming" tablosundan obje tipi → regex eşlemesini okur
2. Paket altındaki alt klasörlerdeki dosya adlarını regex'le karşılaştırır
3. Paket root'undaki `.txt` dosyaları muaf (legacy/draft konvansiyonu)
4. Standart `_CLC` paketlerindeki obje klasörleri: cds/, classes/, programs/, structures/, tables/, functions/

Kullanım:
    python scripts/validators/check_package_naming.py
    python scripts/validators/check_package_naming.py --package ZSD001_CLC

Exit kodu:
    0 — Tüm dosya adları paket regex'lerine uyumlu
    1 — Bir veya birden çok ihlal var (liste stderr'de)
"""
# ENFORCES: C-CDS-NAME-01, C-RAP-NAME-01, C-STR-NAME-01, C-TBL-NAME-01, C-INC-NAME-01, BE-49  (ADR 0019 coverage binding)
import argparse
import re
import sys
from pathlib import Path
import sys as _pc_sys
from pathlib import Path as _pc_Path
_pc_sys.path.insert(0, str(_pc_Path(__file__).resolve().parents[1]))
from utils.project_config import project_root,  SOURCE_ROOT_NAME, cfg  # K12: kaynak-klasor adi config'ten
from utils.ad_politikasi import ad_namespace, dosya_adindan_ad  # TEK ad politikası (#402/#405)

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Obje tipi → klasör adları eşlemesi (.rules.md "Obje Tipi" satırı → klasör)
TYPE_TO_FOLDERS = {
    "program": ["programs"],
    "include": ["programs"],
    "class": ["classes"],
    "interface": ["classes"],
    "function module": ["functions"],
    "function group": ["functions"],
    "cds": ["cds"],
    "cds root view": ["cds"],
    "cds interface view": ["cds"],
    "ddl source": ["cds"],
    "ddl source (cds)": ["cds"],
    "structure": ["structures"],
    "data element": [],  # DDIC objelerinin lokal kopyası nadir
    "domain": [],
    "tablo": ["tables"],
    "table": ["tables"],
    "table type": [],
    "lock object": [],
    "message class": [],
}

# Paket root'undaki dosyalar için muafiyet (legacy/draft konvansiyonu)
ROOT_EXEMPT_EXTENSIONS = {".txt", ".md"}  # spec/draft dosyaları regex'ten muaf

# --- C-INC-NAME-01: klasik program include türetme kuralı (standards/01-naming §4.1) ---
# Klasik report/module-pool include'ları program-adından TÜREMELİ (kısaltma YOK):
#   program Z<n>_P_<BASE>  →  include Z<n>_I_<BASE>_<SUFFIX>  (SUFFIX = _T01/_S01/_C01/_O01/_I01/_F01...)
# Ayrıca program adı ≤26 karakter (include = 26 + _T01(4) = 30 limitine sığsın).
# NEDEN gate: skill router (sap-abap-dev) + naming standardı BU kuralı taşıyordu ama build-unit
# atladı (ZSD001 klasik build, kısaltılmış include adı) → doküman-tek-başına kanıtlı yetersiz (moratoryum §4).
# Grandfather (standart-öncesi kısaltmalar) PROJE-LOKAL: project.yaml `include_naming_exempt: [...]`
# — core generic kalır, proje kendi legacy adlarını muaf tutar (rename edilince listeden sil).
_INCLUDE_SUFFIX_RE = re.compile(r"_[A-Z]\d{2}$")  # klasik report-include suffix


def validate_classic_include_naming(pkg_dir: Path) -> list[str]:
    """C-INC-NAME-01: klasik program include'ları program-adından türer + program ≤26."""
    violations: list[str] = []
    pd = pkg_dir / "programs"
    if not pd.exists():
        return violations
    exempt = {str(x).upper() for x in (cfg("include_naming_exempt") or [])}
    # programlar: programs/ kökünde _P_/_R_ (include alt-klasörü hariç)
    progs = {f.name.split(".prog.")[0].upper() for f in pd.glob("*.prog.abap")
             if re.search(r"_[PR]_", f.name.split(".prog.")[0].upper())}
    for p in sorted(progs):
        if len(p) > 26:
            violations.append(
                f"{pkg_dir.name}/programs/{p}: program adı {len(p)} karakter (>26) — "
                f"include'lar 30 limitine sığmaz (C-INC-NAME-01)")
    # include'lar: programs/ (her derinlik) _I_ + report-suffix'li
    for f in pd.rglob("*.prog.abap"):
        nm = f.name.split(".prog.")[0].upper()
        if "_I_" not in nm or not _INCLUDE_SUFFIX_RE.search(nm):
            continue  # yalnız report-suffix'li include (exit/enhancement include'ları hariç)
        if nm in exempt:
            continue
        parts = nm.split("_")
        try:
            i = parts.index("I")
        except ValueError:
            continue
        if i < 1 or len(parts) < i + 3:
            continue
        pref = "_".join(parts[:i])
        base = "_".join(parts[i + 1:-1])
        if f"{pref}_P_{base}" not in progs and f"{pref}_R_{base}" not in progs:
            violations.append(
                f"{pkg_dir.name}/programs/.../{f.name}: include program-adindan turemiyor "
                f"(beklenen `{pref}_P_{base}` — kisaltma/uyumsuz; C-INC-NAME-01). "
                f"Kural: klasik include = program adi `_P_`->`_I_` + `_<suffix>`, kisaltma YOK (standards/01-naming §4.1)")
    return violations

# Klasörler bazında dosya uzantı filtresi
#
# ⚠ KAPSAM = BEYAN (2026-08-01 bug-avı, V2). Bu tablo "naming kuralı hangi dosyalara
# uygulanır"ı belirler; listede olmayan uzantı SESSİZCE hiç doğrulanmaz — ihlal yoktur
# demez, "bakılmadı" der ve ikisi çıktıda ayırt EDİLEMEZ. Canlı bir projede ölçüldü:
# `cds/` altındaki 26 `.bdef` + `tables/` altındaki 8 `.tabl.ddl`/`.tabl` hiçbir naming
# regex'inden geçmiyordu (aynı sınıf: `check_object_in_correct_pkg` uzantı kümesi).
#
# ⛔ `.srvd` BİLİNÇLİ OLARAK YOK: Service Definition adı `Z<PKG>_UI_*` / `Z<PKG>_API_*`
# konvansiyonundadır ama bu kural paket `.rules.md`'lerinde TABLO satırı değil DÜZ METİN
# olarak yaşıyor → parse edilen regex kümesinde karşılığı yok. Eklenirse doğru adlandırılmış
# 15 dosya "hiçbir regex'le eşleşmiyor" diye suçlanır (ölçüldü). Önkoşul: `.rules.md`
# şablonuna "Service Definition" satırı eklenmesi (proje/şablon tarafı). O yapılmadan
# buraya `*.srvd` EKLEME — PATTERN#14: taban ölçülmeden gate sertleştirilmez.
FOLDER_FILE_GLOBS = {
    # #402 EK-2 kardeşi: `*.asbdef` = abapGit BDEF (`X.bdef.asbdef`); ad "ilk noktaya kadar"
    # normalizasyonuyla `.bdef` ile AYNI ada iner (aşağıda) ⇒ yeni FP sınıfı açmaz.
    # #405 ①: abapGit DDLS (`X.ddls.asddls`) ve DCL (`X.dcls.asdcls`) `cds/` altında HİÇ taranmıyordu.
    # Taban (2026-11-08, 4 tüketici `<source_root>`): `cds/` altında bu uzantıda dosya 0 ⇒ ekleme
    # bugünkü hiçbir sonucu değiştirmez (PATTERN#14 ölçüldü). `*.ddlx.asddlxs` (metadata extension)
    # bilinçli YOK: `.rules.md` tablosunda karşılığı ölçülmedi — KAPSAM satırında "atlanan" sayılır.
    "cds": ["*.cds", "*.bdef", "*.asbdef", "*.dcl", "*.asddls", "*.asdcls"],  # .md muaf; .srvd notu yukarıda
    "classes": ["*.abap"],
    "programs": ["*.abap"],
    "structures": ["*.ddls.asddls", "*.abap"],
    "tables": ["*.abap", "*.ddls.asddls", "*.tabl.ddl", "*.tabl"],
    "functions": ["*.abap"],
}


def parse_rules_md(rules_path: Path) -> list[tuple[str, str]]:
    """`.rules.md`'den (obje_tipi, regex) listesini çıkarır."""
    if not rules_path.exists():
        return []

    rules = []
    table_started = False
    text = rules_path.read_text(encoding="utf-8", errors="replace")

    for line in text.splitlines():
        line = line.strip()
        # Naming bölümünü ve tablosunu yakala
        if line.startswith("## Naming"):
            table_started = True
            continue
        if table_started and line.startswith("## "):
            # Yeni section başladı, tabloyu bırak
            break
        if table_started and line.startswith("|") and "|" in line[1:]:
            # Tablo satırı. Regex hücresi `\|` (escape edilmiş pipe) içerebilir —
            # bu bir kolon ayıracı DEĞİL (ör. alternation `(A\|B)`). Split etmeden
            # önce sentinel ile koru, sonra geri yükle (aksi halde regex hücresi
            # parçalanır ve satır sessizce düşer → naming kuralı kaybolur).
            _SENT = "\x00PIPE\x00"
            cells = [c.strip().replace(_SENT, "|")
                     for c in line.replace("\\|", _SENT).split("|")[1:-1]]
            if len(cells) >= 3 and cells[2].startswith("`") and cells[2].endswith("`"):
                obj_type = cells[0].strip().lower()
                regex_str = cells[2].strip("`")
                rules.append((obj_type, regex_str))

    return rules


def yeni_kapsam() -> dict:
    """KAPSAM BEYANI sayaçları (#405 ①): taranan · uzantısı listede olmayan · regex'siz klasör ·
    ÖLÇÜLEMEDİ (namespace'li ad, paketin tablosu o namespace'i hiç anmıyor)."""
    return {"taranan": 0, "atlanan": 0, "atlanan_uzanti": {}, "regexsiz_klasor": 0,
            "olculemedi": []}


def _tablo_ns_aniyor(regexler, ns: str) -> bool:
    """Paketin regex'lerinden biri namespace'i (`/NS/` ya da abapGit `#NS#`) metin olarak anıyor mu?

    Anıyorsa tablo bu namespace'teki adları denetlemeyi ÜSTLENMİŞTİR ⇒ eşleşmeme gerçek ihlaldir.
    Kaçışlar (`\\/`, `\\#`) düşürülerek, büyük harfle bakılır.
    """
    ic = ns.strip("/").upper()
    for _t, rx in regexler:
        duz = rx.pattern.replace("\\", "").upper()
        if f"/{ic}/" in duz or f"#{ic}#" in duz:
            return True
    return False


def _uzanti(ad: str) -> str:
    i = ad.find(".")
    return ad[i:].lower() if i >= 0 else "(uzantısız)"


def validate_package(pkg_dir: Path, verbose: bool = False, kapsam: dict | None = None) -> list[str]:
    """Bir paket için tüm dosya adlarını doğrular, ihlal listesini döner.

    `kapsam` (opsiyonel, `yeni_kapsam()`): taranan/atlanan/ÖLÇÜLEMEDİ sayaçları buraya eklenir.
    """
    kapsam = yeni_kapsam() if kapsam is None else kapsam
    violations = []
    rules_path = pkg_dir / ".rules.md"
    rules = parse_rules_md(rules_path)

    if not rules:
        violations.append(f"{pkg_dir.name}: .rules.md'den naming kuralı çıkarılamadı")
        return violations

    # Obje tipi → regex sözlüğü (lowercase key)
    type_regex = {t: re.compile(r) for t, r in rules}

    if verbose:
        print(f"\n=== {pkg_dir.name} ===")
        for t, r in rules:
            print(f"  {t} → {r}")

    # Her alt klasör için ilgili obje tipini bul, dosyaları doğrula
    for folder_name, file_globs in FOLDER_FILE_GLOBS.items():
        folder = pkg_dir / folder_name
        if not folder.exists():
            continue

        # Bu klasöre uygun obje tipini bul
        applicable_regexes = []
        for obj_type, regex in type_regex.items():
            for canonical_type, folders in TYPE_TO_FOLDERS.items():
                if canonical_type in obj_type and folder_name in folders:
                    applicable_regexes.append((obj_type, regex))
                    break

        if not applicable_regexes:
            kapsam["regexsiz_klasor"] += 1
            continue  # Bu klasör için regex yok, atla

        # Dosyaları topla (aynı dosya iki glob'a uyabilir — `*.asddls` · `*.ddls.asddls` — tekille)
        files = []
        for glob in file_globs:
            files.extend(p for p in folder.glob(glob) if p not in files)
        # KAPSAM: klasörün DOĞRUDAN içindeki, hiçbir glob'a uymayan dosyalar (glob özyinelemesiz)
        for p in folder.iterdir():
            if p.is_file() and p not in files and p.suffix.lower() != ".md":
                kapsam["atlanan"] += 1
                u = _uzanti(p.name)
                kapsam["atlanan_uzanti"][u] = kapsam["atlanan_uzanti"].get(u, 0) + 1
        kapsam["taranan"] += len(files)

        for f in files:
            # Uzantıyı kaldır, basename'i regex'le
            name = f.name
            # SAP ADT multi-part source konvansiyonu: <OBJE>.<kind>[.<sub>].<ext>
            # — obje adı her zaman ilk marker'dan önceki segment.
            #   class pool : .clas.abap / .clas.locals_imp.abap / .clas.testclasses.abap
            #   RAP behavior pool : .ccimp.abap (CCIMP) / .ccdef.abap (CCDEF) /
            #                       .ccmac.abap (CCMAC) — behavior class lokal include'ları
            #   test include : .ccau.abap (CCAU) — ADR 0016 + source_drift.py +
            #                  check_no_rap_commit.py ile AYNI konvansiyon. 2026-07-28'e
            #                  kadar bu listede YOKTU; repodaki ilk .ccau dosyası yazılınca
            #                  "hiçbir regex'le eşleşmiyor" FAIL'i verdi (obje adı
            #                  kırpılamadığı için). Marker listesi konvansiyonla eş tutulmalı.
            #   BDEF : .bdef.abap
            #   program : .prog.abap   function module : .func.abap   FUGR : .fugr.abap
            _sap_markers = (".clas.", ".ccimp.", ".ccdef.", ".ccmac.", ".ccau.", ".bdef.",
                            ".intf.", ".prog.", ".func.", ".fugr.")
            _hit = next((m for m in _sap_markers if m in name), None)
            if _hit:
                name = name.split(_hit)[0]
            else:
                for ext in (".ddls.asddls", ".abap", ".cds"):
                    if name.endswith(ext):
                        name = name[: -len(ext)]
                        break
            # GENEL NORMALİZASYON (2026-08-01, V2): yukarıdaki iki liste BİLİNEN uzantıları
            # sayar; bilinmeyen bir uzantı kırpılmadan kalır ve ad NOKTA taşıdığı için
            # `^Z..._[A-Z0-9_]+$` regex'lerinin HİÇBİRİ eşleşemez → doğru adlandırılmış
            # dosya "hiçbir regex'le eşleşmiyor" diye SUÇLANIR. `.bdef` glob'a eklenince
            # ölçüldü: 26 dosyanın 26'sı da FP (adları zaten `_I_`/`_C_` kuralına uygundu).
            # SAP obje adları NOKTA İÇEREMEZ (namespace `/NS/AD` ile eğik çizgi kullanır) →
            # "ilk noktaya kadar" kanonik ve uzantıdan bağımsızdır. Bu, 2026-07-28'deki
            # `.ccau` vakasının (listeye eklenmemiş uzantı → sahte FAIL) tekrarını sınıf
            # olarak kapatır; marker listesi belgeleme/çapa olarak KALIR.
            if "." in name:
                name = name.split(".", 1)[0]

            # #405 ①: dosya adı gövdesi → SAP adı TEK yardımcıdan (`dosya_adindan_ad`: `#ns#x` ·
            # `%23ns%23x` · `(ns)x` → `/NS/X`). Ham gövde AYNEN denenir (namespace paketlerinin
            # tabloları `^#NSPC#…` biçiminde yazılı — #391); YALNIZ namespace'li adda iki ek aday:
            # çözülmüş SAP adı (`/NS/X`, tablo `^/NS/…` yazdıysa) ve BÜYÜK harfli ham gövde
            # (`#NS#X`: abapGit dosya adını küçük harfle yazar, `^#NS#…` tablosu büyük harflidir —
            # kardeş `check_object_in_correct_pkg.matches_package` aynı `.upper()`'ı uygular;
            # ölçüldü 2026-11-08: bu aday olmadan `#xns#i_good` `^#XNS#I_GOOD$`'a uymuyordu).
            # Z adında büyük harfe çevrilmiş ad denenmez: küçük harfli Z dosya adı bugün olduğu
            # gibi reddedilir — G1 sınırı korunur.
            sap_ad = dosya_adindan_ad(name)
            adaylar = [name] + ([sap_ad, name.upper()] if sap_ad.startswith("/") else [])
            if any(rx.match(a) for a in adaylar for _, rx in applicable_regexes):
                continue
            if sap_ad.startswith("/"):
                ns = ad_namespace(sap_ad)
                if not ns or not _tablo_ns_aniyor(applicable_regexes, ns):
                    # #402 ilkesi: `/` taşıyan ad ya denetlenir ya ÖLÇÜLEMEDİ döner. Tablo bu
                    # namespace'i hiç anmıyor ⇒ hiçbir regex bu adı DEĞERLENDİREMEZ (FAIL değil).
                    neden = ("namespace biçimi tanınmadı (ad grameri)" if not ns else
                             f"paketin Naming tablosu {ns} namespace'ini hiç anmıyor")
                    kapsam["olculemedi"].append(
                        f"{pkg_dir.name}/{folder_name}/{f.name} → {sap_ad}: {neden}")
                    continue
            violations.append(
                f"{pkg_dir.name}/{folder_name}/{f.name}: "
                f"hiçbir regex'le eşleşmiyor "
                f"(denenenler: {', '.join(t for t, _ in applicable_regexes)})"
            )

    # C-INC-NAME-01: klasik include türetme (regex prefix'in ötesinde — program-adı türetme + ≤26)
    violations.extend(validate_classic_include_naming(pkg_dir))

    return violations


# Tooling scratch dizini artık .tmp/sap_scratch (ERP DIŞI, gitignored) — ZAI default'u
# KALDIRILDI (2026-06-18). <source_root>/ZAI ARTIK YASAK: belirirse bu check onu flag'ler
# (ZAI-resurgence guard). Başka scratch-modül yok → exclude kümesi BOŞ.
SCRATCH_MODULES: set = set()


def find_packages(erp_root: Path) -> list[Path]:
    """<source_root>/<MODULE>/<PKG>/ — modül seviyesi altındaki paketleri döner."""
    if not erp_root.exists():
        return []
    packages = []
    for module_dir in sorted(erp_root.iterdir()):
        if not module_dir.is_dir() or module_dir.name.startswith("."):
            continue
        if module_dir.name in SCRATCH_MODULES:
            continue
        for pkg in sorted(module_dir.iterdir()):
            if pkg.is_dir() and not pkg.name.startswith("."):
                packages.append(pkg)
    return packages


def find_package_by_name(erp_root: Path, pkg_name: str) -> Path | None:
    """Modülleri tarayarak paketi bulur."""
    for module_dir in erp_root.iterdir():
        if not module_dir.is_dir():
            continue
        candidate = module_dir / pkg_name
        if candidate.exists():
            return candidate
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Paket naming kurallarını doğrula")
    parser.add_argument("--source-root", default=SOURCE_ROOT_NAME, help="ERP root dizini")
    parser.add_argument("--package", default=None, help="Sadece bu paketi doğrula")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--strict", action="store_true", help="run_all_validators ile uyum için, no-op")
    args = parser.parse_args()

    _p = Path(args.source_root)
    erp_root = _p if _p.is_absolute() else (project_root() / _p)
    if args.package:
        pkg = find_package_by_name(erp_root, args.package)
        if pkg is None:
            print(f"HATA: {args.package} <source_root>/ altında bulunamadı", file=sys.stderr)
            return 1
        packages = [pkg]
    else:
        packages = find_packages(erp_root)

    all_violations = []
    kapsam = yeni_kapsam()
    for pkg in packages:
        if not pkg.exists():
            print(f"UYARI: {pkg} bulunamadı, atlanıyor", file=sys.stderr)
            continue
        violations = validate_package(pkg, verbose=args.verbose, kapsam=kapsam)
        all_violations.extend(violations)

    # KAPSAM BEYANI (#405 ①, CLAUDE.core §7) — her koşumda, sıfır-bulgu anı DAHİL.
    # "atlanan" = regex'li klasörün DOĞRUDAN içinde olup glob listesinde OLMAYAN dosya (`.md` hariç;
    # alt klasörler glob'un da dışındadır, sayılmaz). Atlanan dosyanın adı DENETLENMEDİ.
    au = ", ".join(f"{u}×{n}" for u, n in sorted(kapsam["atlanan_uzanti"].items(),
                                                 key=lambda x: (-x[1], x[0])))
    kapsam_satiri = (f"KAPSAM: taranan {kapsam['taranan']} dosya · atlanan {kapsam['atlanan']}"
                     + (f" ({au})" if au else "")
                     + f" · regex'siz klasör {kapsam['regexsiz_klasor']}"
                     + f" · ÖLÇÜLEMEDİ {len(kapsam['olculemedi'])}"
                     + " · BAKILMAYAN: alt klasörler, .srvd/.ddlx (yukarıdaki not)")
    for o in kapsam["olculemedi"]:
        print(f"  ÖLÇÜLEMEDİ — {o}")

    if all_violations:
        print("HATA — Naming ihlalleri:", file=sys.stderr)
        for v in all_violations:
            print(f"  {v}", file=sys.stderr)
        print(f"  {kapsam_satiri}", file=sys.stderr)
        return 1

    print(f"OK — {len(packages)} paket, naming ihlali yok. {kapsam_satiri}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
