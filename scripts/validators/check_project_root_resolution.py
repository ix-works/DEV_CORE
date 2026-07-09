# -*- coding: utf-8 -*-
"""check_project_root_resolution — core script'lerinde PROJE kökünü `__file__`'dan türetme YASAĞI.

# ENFORCES: CORE-01, CORE-02  (ADR 0019 coverage binding)

NEDEN (ADR 0020 · junction mimarisi):
  Core script'leri proje içinden `core/` junction'ı üzerinden koşar. Bu yüzden
  `Path(__file__).resolve().parent*` DAİMA `<DEV_CORE>`'a çözülür — proje köküne ASLA.
  Proje kökü/kaynağı/state'i `__file__`'dan türeten her satır SESSİZCE yanlış yere bakar:
  dizin yoksa tarama 0 dosya bulur ve validator "[OK]" der (SAHTE PASS), ya da state
  ortak core'a yazılıp projeler arasında sızar.

KANIT (2026-07-09, bu gate'in doğuş sebebi):
  • `source_drift.repo_root()` → DEV_CORE ⇒ `find_repo_source_file()` daima None ⇒
    PULL-BEFORE-EDIT (ADR 0016) TÜM projede her SAP source Edit'ini blokladı.
  • `check_method_param_type_c.py` → `DEV_CORE/SOURCE_CODES` (yok) ⇒ 0 dosya taradı;
    projeye bilerek konan `TYPE c LENGTH 10` ihlaline "[OK] ihlal yok" dedi.
  • `sap_sync_pull` / `pull_before_edit` tazelik damgasını `DEV_CORE/.claude/`'a yazdı
    (proje `.gitignore` o yolu proje kökünde ignore'lu ⇒ tasarım niyeti proje kökü).
  Aynı tuzağa 3 kez düşüldü. `project_config.py` docstring'i zaten uyarıyordu —
  ama YORUM GATE DEĞİLDİR (ADR 0019). Bu script o yorumu zorlayıcı hâle getirir.

KANONİK API (`scripts/utils/project_config.py`):
  project_root()      → env CLAUDE_PROJECT_DIR → cwd
  source_root_name()  → project.yaml `source_root`
  source_dir()        → project_root() / source_root_name()

TESPİT (AST; regex değil):
  1) `<AD> = <... Path(__file__) ...>`  → "file-derived" kök adayı (transitive DEĞİL:
     `X = REPO / "scripts"` file-derived sayılmaz ⇒ core-içi alt-yollar FP üretmez).
  2) O adın PROJE-anlamlı tüketimi İHLAL'dir:
       a. `<AD> / SOURCE_ROOT_NAME` · `/ "SOURCE_CODES"` · `/ "ERP"`
       b. `<AD> / ".claude"`  (seans state / davranış-yüzeyi)
       c. `<AD> / "project.yaml"`
       d. `os.walk(<AD>)` · `<AD>.rglob(...)`  (proje geneli tarama)
  `sys.path.insert(0, str(Path(__file__)...))` bir ATAMA DEĞİL → hiç görülmez (meşru).
  Core-içi yollar (`<AD> / "playbook"`, `/ "governance"`, `/ "abaplint"` ...) İHLAL DEĞİL.

MUAF: `utils/project_config.py` — kanonik kaynağın kendisi (project_root'u o tanımlar).
"""
from __future__ import annotations

import ast
import io
import sys
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.platform == "win32" and hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Bu validator CORE dosyalarını tarar → kökü __file__'dan türetmesi MEŞRU ve zorunludur
# (proje değil, core'un kendisi hedef). Kendi kuralının istisnası değil: kuralın konusu
# PROJE kökü; burada hedef CORE kökü.
CORE_ROOT = Path(__file__).resolve().parents[2]
SCAN_DIR = CORE_ROOT / "scripts"

MUAF = {"utils/project_config.py"}

# `<file-derived-kök> / <ilk-segment>` = proje kökü varsayımı
PROJE_SEGMENT_SABIT = {"SOURCE_CODES", "ERP", "project.yaml"}
PROJE_SEGMENT_NAME = {"SOURCE_ROOT_NAME"}

# `.claude/` özel: proje state'i (settings/manifest/seans damgası) PROJE kökündedir.
# TEK meşru core-içi istisna: `claude/memory-seed` template'inin nokta'lı fallback'i
# (`seed_memory.py`; core'un KENDİ tohum dizini, hedef proje ayrıca env'den çözülür).
CLAUDE_DIZIN = ".claude"
CLAUDE_MUAF_ALT = {"memory-seed"}

# `<file-derived-kök>` üzerinde proje-geneli tarama
TARAMA_ATTR = {"rglob"}


def _iceriyor_file(node: ast.AST) -> bool:
    """Bu ifade `__file__` adını içeriyor mu?"""
    return any(isinstance(n, ast.Name) and n.id == "__file__" for n in ast.walk(node))


def _file_derived_adlar(tree: ast.AST) -> dict[str, int]:
    """`X = <... __file__ ...>` atamalarındaki X adları → satır no.

    Transitive DEĞİL (bilinçli): `VALIDATORS_DIR = REPO / "scripts"` file-derived sayılmaz,
    aksi hâlde meşru core-içi alt-yollar yanlış-pozitif üretirdi.
    """
    out: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            hedefler = node.targets if isinstance(node, ast.Assign) else [node.target]
            if node.value is None or not _iceriyor_file(node.value):
                continue
            for t in hedefler:
                if isinstance(t, ast.Name):
                    out[t.id] = node.lineno
    return out


def _file_derived_fonksiyonlar(tree: ast.AST) -> dict[str, int]:
    """`def f(): return <... __file__ ...>` — kök DÖNDÜREN fonksiyonlar → satır no.

    ZORUNLU: bu gate'in doğuş sebebi olan orijinal bug tam bu şekildeydi —
        def repo_root() -> Path:
            return Path(__file__).resolve().parent.parent
    Atama olmadığı için `_file_derived_adlar` görmezdi. Sarmalayıcı fonksiyon, `__file__`
    tuzağını çağrı yerlerinden GİZLER (`repo_root() / SOURCE_ROOT_NAME` masum görünür) —
    en tehlikeli varyant budur.
    """
    out: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for alt in ast.walk(node):
                if isinstance(alt, ast.Return) and alt.value is not None \
                        and _iceriyor_file(alt.value):
                    out[node.name] = node.lineno
                    break
    return out


# Adı PROJE kökü ima eden fonksiyon → `__file__` döndürmesi TEK BAŞINA ihlal
# (çağrısı başka dosyada olabilir; cross-file analiz yapmıyoruz). "core"/"seed" içerenler
# core'un kendi kökünü döndürür → meşru.
_PROJE_IMA = ("repo_root", "project_root", "proje_root", "proje_kok", "source_root", "src_root")
_CORE_IMA = ("core", "seed", "template")


def _ad_proje_koku_ima_ediyor(ad: str) -> bool:
    a = ad.lower().lstrip("_")
    if any(c in a for c in _CORE_IMA):
        return False
    return any(a == p or a.startswith(p) or a.endswith(p) for p in _PROJE_IMA)


def _segment(node: ast.AST) -> str | None:
    """`a / b` ifadesinde b'yi okunabilir segmente çevir (str sabit veya bilinen Name)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return node.id
    return None


def _zincir(node: ast.AST) -> tuple[str, list[str]] | None:
    """`KÖK / "a" / "b"` zincirini (kök_adı, ["a","b"]) olarak çöz.

    En dıştaki BinOp'tan başlar; sol taraf Name olana dek iner. İç içe BinOp'lar da
    ayrıca ziyaret edileceğinden çağıran taraf (lineno, kök) ile dedupe eder ve en uzun
    zinciri saklar — böylece `X/".claude"` ile `X/".claude"/"state.json"` çift raporlanmaz.
    """
    segler: list[str] = []
    cur: ast.AST = node
    while isinstance(cur, ast.BinOp) and isinstance(cur.op, ast.Div):
        seg = _segment(cur.right)
        if seg is None:
            return None
        segler.insert(0, seg)
        cur = cur.left
    if not segler:
        return None
    if isinstance(cur, ast.Name):
        return cur.id, segler
    # `repo_root() / SOURCE_ROOT_NAME` — kök bir fonksiyon çağrısıyla gizlenmiş
    if isinstance(cur, ast.Call) and isinstance(cur.func, ast.Name):
        return f"{cur.func.id}()", segler
    return None


def _zincir_ihlali(segler: list[str]) -> str | None:
    """Segment zinciri PROJE kökü varsayıyor mu? Evetse insan-okur gerekçe döner."""
    ilk = segler[0]
    if ilk in PROJE_SEGMENT_SABIT or ilk in PROJE_SEGMENT_NAME:
        return "proje kaynağı/config yolu"
    if ilk == CLAUDE_DIZIN:
        # core'un kendi tohum dizini (`.claude/memory-seed`) tek istisna
        if len(segler) > 1 and segler[1] in CLAUDE_MUAF_ALT:
            return None
        return "proje state/davranış-yüzeyi yolu"
    return None


def _ihlaller(path: Path) -> list[tuple[int, str]]:
    try:
        kaynak = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(kaynak, filename=str(path))
    except SyntaxError as e:
        print(f"[UYARI] parse edilemedi: {path} ({e})", file=sys.stderr)
        return []

    koklar = _file_derived_adlar(tree)
    kok_fonksiyonlar = _file_derived_fonksiyonlar(tree)
    if not koklar and not kok_fonksiyonlar:
        return []

    bulgular: list[tuple[int, str]] = []

    # B1: adı proje-kökü ima eden fonksiyon `__file__` döndürüyor → tek başına İHLAL.
    #     (Çağrı yeri başka dosyada olabilir; bu gate'in doğuş bug'ı buydu.)
    for fad, satir in kok_fonksiyonlar.items():
        if _ad_proje_koku_ima_ediyor(fad):
            bulgular.append((satir,
                             f"`def {fad}(...)` `__file__` türevi döndürüyor — adı PROJE kökü "
                             f"ima ediyor; junction'da DEV_CORE'a çözülür. "
                             f"KANONİK: `project_config.project_root()`"))
    # (satır, kök) -> (segment_sayısı, mesaj|None). İç içe BinOp'lar aynı satırda birden çok
    # kez ziyaret edilir (`X/".claude"` ⊂ `X/".claude"/"memory-seed"`). Kararı EN UZUN zincir
    # verir: kısa parça "ihlal" görünse de tam yol muaf olabilir (core tohum dizini).
    yol_bulgu: dict[tuple[int, str], tuple[int, str | None]] = {}

    for node in ast.walk(tree):
        # a/b/c: <kök> / "SOURCE_CODES" | SOURCE_ROOT_NAME | ".claude"/... | "project.yaml"
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            cozum = _zincir(node)
            if cozum:
                kok, segler = cozum
                # kök ya file-derived DEĞİŞKEN, ya da `__file__` döndüren fonksiyonun ÇAĞRISI
                tanim_satiri = koklar.get(kok)
                if tanim_satiri is None and kok.endswith("()"):
                    tanim_satiri = kok_fonksiyonlar.get(kok[:-2])
                if tanim_satiri is not None:
                    anahtar = (node.lineno, kok)
                    onceki = yol_bulgu.get(anahtar)
                    if onceki is not None and onceki[0] >= len(segler):
                        continue  # daha uzun (daha bilgili) zincir zaten karar verdi
                    gerekce = _zincir_ihlali(segler)
                    if gerekce is None:
                        yol_bulgu[anahtar] = (len(segler), None)  # muaf — kısa parçayı da bastır
                    else:
                        yol = " / ".join(f'"{s}"' if not s.isupper() else s for s in segler)
                        yol_bulgu[anahtar] = (len(segler),
                                              f"`{kok} / {yol}` — {gerekce} `__file__` kökünden "
                                              f"türetiliyor (kök tanımı satır {tanim_satiri})")
        # d1: os.walk(<kök>)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "walk" and isinstance(node.func.value, ast.Name) \
                and node.func.value.id == "os":
            if node.args and isinstance(node.args[0], ast.Name) and node.args[0].id in koklar:
                bulgular.append((node.lineno,
                                 f"`os.walk({node.args[0].id})` — proje geneli tarama `__file__` kökünde"))
        # d2: <kök>.rglob(...)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr in TARAMA_ATTR and isinstance(node.func.value, ast.Name) \
                and node.func.value.id in koklar:
            bulgular.append((node.lineno,
                             f"`{node.func.value.id}.{node.func.attr}(...)` — proje geneli tarama "
                             f"`__file__` kökünde"))

    # mesaj None = muaf (core-içi yol) → raporlanmaz
    bulgular.extend((satir, mesaj) for (satir, _kok), (_n, mesaj) in yol_bulgu.items()
                    if mesaj is not None)
    return sorted(set(bulgular))


def main() -> int:
    if not SCAN_DIR.is_dir():
        print(f"[UYARI] taranacak dizin yok: {SCAN_DIR}", file=sys.stderr)
        return 0

    toplam = 0
    dosya_sayisi = 0
    for py in sorted(SCAN_DIR.rglob("*.py")):
        if "__pycache__" in py.parts:
            continue
        rel = py.relative_to(CORE_ROOT / "scripts").as_posix()
        if rel in MUAF:
            continue
        dosya_sayisi += 1
        for satir, mesaj in _ihlaller(py):
            if toplam == 0:
                print("PROJE-KÖKÜ `__file__` TÜREVİ (ADR 0020 ihlali):\n")
            print(f"  scripts/{rel}:{satir}")
            print(f"      {mesaj}")
            toplam += 1

    if toplam:
        print(f"\n{toplam} ihlal — BLOCKER (CORE-01).", file=sys.stderr)
        print("Core script'i proje içinden `core/` junction'ıyla koşar; `Path(__file__)` "
              "DEV_CORE'a çözülür.\nKANONİK: `from utils.project_config import project_root, "
              "source_dir, source_root_name`\n"
              "  proje kökü      -> project_root()\n"
              "  proje kaynağı   -> source_dir()          (project_root()/source_root_name())\n"
              "  seans state     -> project_root()/'.claude'/...\n"
              "Core'un KENDİ yolları (playbook/, governance/, scripts/) için `__file__` MEŞRU.",
              file=sys.stderr)
        return 1

    print(f"[OK] proje-kökü çözümlemesi: {dosya_sayisi} core script'inde `__file__`-türevi "
          f"proje yolu yok (CORE-01).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
