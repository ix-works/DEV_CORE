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
       c. `<AD> / "project.yaml"` · `<AD> / ".conn_adt"`  (proje config/bağlantı)
       d. `os.walk(<AD>)` · `<AD>.rglob(...)`  (proje geneli tarama)
  `sys.path.insert(0, str(Path(__file__)...))` bir ATAMA DEĞİL → hiç görülmez (meşru).
  Core-içi yollar (`<AD> / "playbook"`, `/ "governance"`, `/ "abaplint"` ...) İHLAL DEĞİL.

MUAF: `utils/project_config.py` — kanonik kaynağın kendisi (project_root'u o tanımlar).
"""
from __future__ import annotations

import ast
import io
import re
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
#
# `.conn_adt` 2026-08-10'da EKLENDİ (KAYIT: ui-smoke proje-kökü): SAP kimlik dosyası
# PROJE kökündedir (`sap_adt_lib`/`deploy_ui`/`ix_doctor` hepsi env→cwd ile çözer;
# `deploy_ui.py` yorumu bunu açıkça "`__file__`-türetimi YASAK" diye yazar) — ama
# dedektör listesinde YOKTU. Canlı hasar: `run_ui_smoke.py` `REPO/".conn_adt"` ile
# DEV_CORE'a bakıyordu, dosya orada YOK ⇒ G1 UI-smoke gate'i (ADR 0017 deploy
# done-criteria) HER çağrıda "kimlik okunamadı" ile ölüyordu; CORE-01 ise aynı koşuda
# "193 script temiz" diyerek SAHTE GÜVEN üretiyordu.
# FP ÖLÇÜMÜ (ekleme ÖNCESİ, canlı core, validator'ın kendi AST'siyle): taban 0 bulgu →
# `.conn_adt` ile +1 (yalnız `ui-smoke/run_ui_smoke.py:31`, yani gerçek kusur). Komşu
# proje-artefaktları da ölçüldü ve EKLENMEDİ (bugün 0 ihlal + 0 FP → gate-moratoryumu
# ADR 0019: kanıtsız genişletme yok): `conn` · `settings.local.json` · `SESSION_NOTES.md`
# · `.csrf_token.json` · `project.local.yaml` → hepsi +0.
PROJE_SEGMENT_SABIT = {"SOURCE_CODES", "ERP", "project.yaml", ".conn_adt"}
PROJE_SEGMENT_NAME = {"SOURCE_ROOT_NAME"}

# `.claude/` özel: proje state'i (settings/manifest/seans damgası) PROJE kökündedir.
# TEK meşru core-içi istisna: `claude/memory-seed` template'inin nokta'lı fallback'i
# (`seed_memory.py`; core'un KENDİ tohum dizini, hedef proje ayrıca env'den çözülür).
CLAUDE_DIZIN = ".claude"
CLAUDE_MUAF_ALT = {"memory-seed"}

# `<file-derived-kök>` üzerinde proje-geneli tarama
# `glob` 2026-08-01'de EKLENDİ (bug-avı V5): `rglob` yasaklıyken `glob` serbest kalması
# keyfiydi — `KOK.glob("*/*/*.cds")` de aynı yanlış ağacı tarar. Canlı core'da doğrudan
# file-derived bir ad üzerinde `.glob(` çağrısı ÖLÇÜLDÜ: **0 adet** → sıfır FP ile eklendi
# (LATENT kapatma: bugün ihlal yok, desen yarın yazılırsa yakalanır).
TARAMA_ATTR = {"rglob", "glob"}


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


def _gecisli_koklar(tree: ast.AST, koklar: dict[str, int]) -> dict[str, int]:
    """Doğrudan file-derived adlardan TÜRETİLEN adlar (`Y = X / "alt"`, `Y = X.parent`).

    NEDEN SINIRLI KULLANIM (2026-08-01, V5): docstring'de "transitive DEĞİL (bilinçli)"
    yazıyordu ve gerekçesi HAKLIYDI — `PLAYBOOK = CORE / "playbook"` sonra
    `PLAYBOOK.rglob(...)` meşrudur; geçişlilik TARAMA dedektörlerine verilirse core'un
    kendi taramaları yanlış-pozitif olur (canlı ölçüm: 26 türetilmiş ad).
    Buna karşılık `KOK2 = KOK.parent` ardından `KOK2 / "SOURCE_CODES"` GERÇEK bir kaçıştı:
    ara değişken, kusuru bir adım öteye taşıyıp gate'i kör ediyordu.

    ÇÖZÜM — dedektör başına ayrı küme:
      • TARAMA dedektörleri (`rglob`/`glob`/`os.walk`) → YALNIZ doğrudan `koklar`
        (eski davranış; FP koruması aynen durur)
      • YOL-ZİNCİRİ dedektörleri (`/`, `.joinpath`, metin birleştirme) → geçişli küme
        (bunlar zaten PROJE-anlamlı ilk segmentle filtreli: SOURCE_CODES/.claude/...
        → core-içi türetilmiş yollar eşleşemez, FP riski yok)
    """
    out = dict(koklar)
    for _ in range(4):  # sabit noktaya kadar (zincir derinliği pratikte 1-2)
        onceki = len(out)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            deger = node.value
            if deger is None:
                continue
            kaynak = deger
            while isinstance(kaynak, ast.BinOp) and isinstance(kaynak.op, ast.Div):
                kaynak = kaynak.left
            while isinstance(kaynak, ast.Attribute):   # `.parent`, `.parents[n]` vb.
                kaynak = kaynak.value
            while isinstance(kaynak, ast.Subscript):
                kaynak = kaynak.value
                while isinstance(kaynak, ast.Attribute):
                    kaynak = kaynak.value
            if not (isinstance(kaynak, ast.Name) and kaynak.id in out):
                continue
            hedefler = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in hedefler:
                if isinstance(t, ast.Name) and t.id not in out:
                    out[t.id] = node.lineno
        if len(out) == onceki:
            break
    return out


# Metin birleştirmeyle (`+` / f-string) kurulan proje yolları. Yalnız kökün HEMEN ARDINDAN
# proje-anlamlı bir segment gelirse ihlal — canlı core'da 8 f-string + 6 `+` ölçüldü ve
# HEPSİ meşrundu (`print(f"core: {CORE_ROOT}")`, `PYTHONPATH=str(X) + os.pathsep + ...`).
# Segment filtresi olmadan bu 14 satır sahte FAIL olurdu; alarm-yorgunluğu gate'i öldürür.
_METIN_IHLAL_RE = re.compile(
    r"<KÖK>[/\\]+(SOURCE_CODES|ERP|project\.yaml|\.conn_adt|\.claude|SOURCE_ROOT_NAME)\b")


def _metin_sekli(node: ast.AST, koklar: dict[str, int]) -> tuple[str, str] | None:
    """f-string / `+` zincirini "şekil" metnine indirger; kök adı `<KÖK>` ile temsil edilir.

    Döner: (kök_adı, şekil) — ör. `f"{KOK}/{SOURCE_ROOT_NAME}"` → ("KOK", "<KÖK>/SOURCE_ROOT_NAME")
    """
    parcalar: list[str] = []
    bulunan_kok: str | None = None

    def ekle(n: ast.AST) -> bool:
        nonlocal bulunan_kok
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            parcalar.append(n.value)
            return True
        if isinstance(n, ast.Name):
            if n.id in koklar:
                bulunan_kok = bulunan_kok or n.id
                parcalar.append("<KÖK>")
            else:
                parcalar.append(n.id)
            return True
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "str" \
                and len(n.args) == 1:
            return ekle(n.args[0])
        if isinstance(n, ast.FormattedValue):
            return ekle(n.value)
        if isinstance(n, ast.JoinedStr):
            return all(ekle(v) for v in n.values)
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
            return ekle(n.left) and ekle(n.right)
        parcalar.append("?")
        return True

    ekle(node)
    if bulunan_kok is None:
        return None
    return bulunan_kok, "".join(parcalar)


def _zincir_ihlali(segler: list[str]) -> str | None:
    """Segment zinciri PROJE kökü varsayıyor mu? Evetse insan-okur gerekçe döner."""
    ilk = segler[0]
    if ilk == ".conn_adt":
        return "SAP bağlantı dosyası (PROJE kökünde; env CLAUDE_PROJECT_DIR → cwd)"
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
    # Yol-zinciri dedektörleri geçişli kümeyi kullanır; TARAMA dedektörleri `koklar`ı
    # (gerekçe: `_gecisli_koklar` docstring'i — FP koruması bilinçli olarak korunuyor).
    koklar_gecisli = _gecisli_koklar(tree, koklar)

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
                tanim_satiri = koklar_gecisli.get(kok)
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
        # d2: <kök>.rglob(...) / <kök>.glob(...)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr in TARAMA_ATTR and isinstance(node.func.value, ast.Name) \
                and node.func.value.id in koklar:
            bulgular.append((node.lineno,
                             f"`{node.func.value.id}.{node.func.attr}(...)` — proje geneli tarama "
                             f"`__file__` kökünde"))
        # e: <kök>.joinpath("SOURCE_CODES", ...) — `/` operatörünün metot ikizi.
        #    Aynı yolu kurar, aynı hasarı verir; dedektör yalnız `/`ye bakıyordu.
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "joinpath" and isinstance(node.func.value, ast.Name) \
                and node.func.value.id in koklar_gecisli:
            segler = [s for s in (_segment(a) for a in node.args) if s is not None]
            gerekce = _zincir_ihlali(segler) if segler else None
            if gerekce:
                yol = ", ".join(f'"{s}"' if not s.isupper() else s for s in segler)
                bulgular.append((node.lineno,
                                 f"`{node.func.value.id}.joinpath({yol})` — {gerekce} `__file__` "
                                 f"kökünden türetiliyor (kök tanımı satır "
                                 f"{koklar_gecisli[node.func.value.id]})"))
        # f: metin birleştirme — `str(<kök>) + "/SOURCE_CODES"` · `f"{<kök>}/.claude"`.
        #    Path aritmetiği yerine dize kurmak dedektörü tamamen atlatıyordu.
        if isinstance(node, (ast.JoinedStr, ast.BinOp)) and not (
                isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)):
            sonuc = _metin_sekli(node, koklar_gecisli)
            if sonuc:
                kok, sekil = sonuc
                m = _METIN_IHLAL_RE.search(sekil)
                if m:
                    bulgular.append((node.lineno,
                                     f"`{sekil}` — proje yolu METİN BİRLEŞTİRMEYLE `__file__` "
                                     f"kökünden kuruluyor (kök `{kok}`, tanım satır "
                                     f"{koklar_gecisli.get(kok)}); Path aritmetiği olmaması "
                                     f"kuralı geçersiz KILMAZ"))

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
