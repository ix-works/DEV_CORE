"""
source_drift.py — Repo ↔ canlı SAP kaynak DRIFT tespiti (ADR 0016).

Sorun: Yerel `.srvd`/`.cds`/`.ddls`/`.abap` dosyaları canlı SAP aktif sürümünden
ayrışabiliyor (ör. ZSD001_UI_BOOKING.srvd yerelde 8 expose, canlıda 13). Yereli
push etmek canlıdaki belgelenmemiş değişiklikleri SESSİZCE EZER/SİLER. Bu modül
push'tan ÖNCE drift'i tespit eder ve hard-block için (is_drift=True) sinyal verir.

Bu modül SAP'ye bağlanmaz — saf yardımcı mantık (repo dosya bulma + normalizasyon
+ kıyas). Canlı source'u çağıran taraf, fetch_active callback ile verir
(MCP push akışı `sap_adt_lib.detect_source_drift` üzerinden; validator standalone).

Reuse: repo dosya eşleme `check_object_in_correct_pkg.py`'deki <source_root>/<MODULE>/<PKG>/
<folder> + rglob desenini genişletir (uzantı seti daha geniş: .srvd/.srvb/.bdef
dahil).
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Callable, Optional
import sys as _pc_sys
from pathlib import Path as _pc_Path
_pc_sys.path.insert(0, str(_pc_Path(__file__).resolve().parents[0]))
from utils.project_config import SOURCE_ROOT_NAME  # K12: kaynak-klasor adi config'ten
from utils.project_config import project_root as _project_root  # ADR 0020: junction-guvenli kok


def _git_working_copy_dirty(path: Path) -> bool:
    """True = dosyada COMMIT EDİLMEMİŞ değişiklik var (modified/staged/untracked).

    MANUEL pull yolunu (sap_sync_pull elle/gateway çağrısı) korur: canlı aktif source'u
    yereldeki commit'lenmemiş emeğin üzerine SESSİZCE yazmasını önler (2026-06-21 gateway
    kaybı kanıtı). pull_before_edit HOOK'u zaten dirty'yi MUAF tutar (Edit/Write yolu);
    bu, hook'un kapsamadığı manuel/script yolunu tamamlar (FIX-B; res-driftarch analizi).
    Konservatif: git çalışmazsa True (kaybetmektense koru — caller --force ile geçebilir)."""
    try:
        p = path.resolve()
        out = subprocess.run(
            ["git", "status", "--porcelain", "--", p.name],
            cwd=str(p.parent), capture_output=True, text=True, timeout=15,
        )
    except Exception:
        return True
    if out.returncode != 0:
        return True
    return bool(out.stdout.strip())


def _norm_for_compare(data) -> bytes:
    """Satır-sonu ve dosya-sonu newline farklarını eleyerek karşılaştırma normali üret.

    Gerekli çünkü pull yolu CRLF/LF'i koruyor ve include pull'u EOF newline'ını
    düşürebiliyor (ölçüldü 2026-07-31) — bunlar İÇERİK farkı değildir ve
    "canlı geride mi?" sorusunu kirletmemeli.
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n").rstrip(b"\n")


def _live_matches_older_commit(path: Path, live_body: bytes, max_commits: int = 30):
    """Canlı içerik, bu dosyanın GEÇMİŞ bir commit'indeki hâliyle eşleşiyor mu?

    FIX-D'nin sinyali. Eşleşme varsa canlı **kesinlikle geride**: repo'da bir zamanlar
    tam olarak bu içerik vardı, sonra üzerine yazıldı ve commit'lendi. Yani pull
    "tazeleme" değil, kendi geçmişimize dönüş = yerel yeni işin ezilmesi.

    Neden bu sinyal seçildi (alternatifler ölçülüp elendi, 2026-07-31):
      * zaman karşılaştırması (canlı changedAt ↔ commit tarihi): timezone, saat
        sapması ve rebase yüzünden hem yanlış pozitif hem yanlış negatif üretir.
      * "fark varsa blokla": canlı ile repo'nun farklı olması NORMAL (başkası
        canlıyı değiştirmiş olabilir) → her pull bloklanırdı, araç kullanılamaz olurdu.
      * içerik-eşleşmesi: canlı içerik geçmişte VARDI ise başka yorum yok.
        **Yanlış pozitif üretmez.** Eşleşme yoksa canlıda gerçekten yeni bir şey var
        demektir ve pull meşrudur — o hâlde sessizce geçer.

    Returns: eşleşen commit'in kısa SHA'sı (str) ya da None.
    """
    target = _norm_for_compare(live_body)
    try:
        p = path.resolve()
        log = subprocess.run(
            ["git", "log", f"-{max_commits}", "--format=%h", "--", p.name],
            cwd=str(p.parent), capture_output=True, text=True, timeout=20,
        )
        if log.returncode != 0:
            return None  # git yok / shallow / detached → sinyal ölçülemez, FIX-C devrede
        shas = [s for s in log.stdout.split() if s]
        # HEAD'in kendisi atlanır: canlı == HEAD zaten no-op dalında yakalanıyor;
        # burada aranan "DAHA ESKİ bir hâle dönüş" durumu.
        for sha in shas[1:]:
            show = subprocess.run(
                ["git", "show", f"{sha}:./{p.name}"],
                cwd=str(p.parent), capture_output=True, timeout=20,
            )
            if show.returncode == 0 and _norm_for_compare(show.stdout) == target:
                return sha
    except Exception:
        return None  # ölçemedik → sessizce geç (FIX-B/FIX-C korumaları duruyor)
    return None


# Repo'da bir SAP objesinin kaynağını taşıyan dosya uzantıları.
# Çift uzantılar (.ddls.asddls) suffix-zinciri ile değil, basename eşlemesiyle
# yakalanır (aşağıda find_repo_source_file). .md companion dosyaları (ör.
# *.srvb.md) KASITLI dışarıda — onlar source değil dokümantasyon.
SOURCE_EXTENSIONS = (
    ".srvd",          # service definition
    ".srvb",          # service binding (source taşımaz ama tutarlılık için)
    ".bdef",          # behavior definition
    ".cds",           # CDS view (proje konvansiyonu)
    ".ddls",          # CDS DDL source
    ".asddls",        # CDS DDL source (SAP native ext)
    ".abap",          # class/program/include/fugr
    ".dcl",           # access control
    ".asdcls",        # access control (SAP native ext)
    ".ddlx",          # metadata extension
    ".asddlxs",       # metadata extension (SAP native ext)
)

# .md/.txt gibi dosyalar source değil — find sırasında elenir.
_NON_SOURCE_SUFFIXES = (".md", ".txt", ".json", ".xml")

# Obje TİPİ → o tipin repo source dosyası uzantı(lar)ı. AYNI obje-adı birden çok
# tip dosyası paylaşabilir (ör. ZSD001_I_BOOKING: `.cds`=DDLS interface + `.bdef`=BDEF).
# object_type verilince DOĞRU dosyayı seçmek için filtre uygulanır; yoksa isim-only
# eşleme tiebreak'i (SOURCE_EXTENSIONS sırası) YANLIŞ tip dosyasını seçip iki farklı
# objeyi kıyaslar → SAHTE drift (2026-06-16 railway ADIM 1 bloğu: DDLS push'unda .bdef
# seçildi). Bilinmeyen/None tip → filtre uygulanmaz (eski rank-fallback, geriye-uyumlu).
_TYPE_TO_EXTENSIONS = {
    # CDS / DDL source (interface, consumption, DB-view, struct/table-as-DDL)
    "ddls": (".cds", ".asddls", ".ddls"), "cds": (".cds", ".asddls", ".ddls"),
    "cdsview": (".cds", ".asddls", ".ddls"), "ddl": (".cds", ".asddls", ".ddls"),
    "structure": (".asddls", ".ddls", ".cds"),
    "table": (".asddls", ".ddls", ".cds"), "tabl": (".asddls", ".ddls", ".cds"),
    # Behavior definition
    "bdef": (".bdef",), "behaviordefinition": (".bdef",), "bdo": (".bdef",),
    # Service definition / binding
    "srvd": (".srvd",), "servicedefinition": (".srvd",),
    "srvb": (".srvb",), "servicebinding": (".srvb",),
    # ABAP source (class/program/interface/include/fugr) — hepsi .abap (alt-uzantı .clas/.prog ile)
    "class": (".abap",), "clas": (".abap",), "program": (".abap",), "prog": (".abap",),
    "interface": (".abap",), "intf": (".abap",), "include": (".abap",),
    "fugr": (".abap",), "functiongroup": (".abap",),
    # Access control (DCL)
    "accesscontrol": (".dcl", ".asdcls"), "dcls": (".dcl", ".asdcls"), "dcl": (".dcl", ".asdcls"),
    # Metadata extension
    "metadataextension": (".ddlx", ".asddlxs"), "ddlx": (".ddlx", ".asddlxs"), "mde": (".ddlx", ".asddlxs"),
}

# Bu klasör adları altındaki dosyalar DEPLOY edilebilir kaynak DEĞİL — referans
# snapshot / dokümantasyon / scratch. Drift kıyasından muaf (ör. ref_docs/cds/
# ZSD001_DDL_BOOKING_HEADER.cds eski FS reçetesi, canlıyla bilinçli ayrışık).
_EXCLUDED_DIR_SEGMENTS = {"ref_docs", "docs", ".tmp", "legacy", "_archive", "archive", "drafts"}

# FIX-C içerik-kaybı koruması (write_repo_from_live). Canlı AKTİF sürüm yerelden bu
# oranın altına düşerse pull ATLAR (yerel yeni iş ezilmesin) — --force ile geçilir.
# Eşikler bilinçli GEVŞEK: amaç normal tazelemeyi engellemek değil, YIKIMI yakalamak.
# Ölçülen vakalar (2026-07-31): 267→113 (%42 kaldı) · 141→1 (%0.7 kaldı).
_SHRINK_MIN_LINES = 10     # bu satırın altındaki dosyalarda kontrol yapılmaz
_SHRINK_KEEP_RATIO = 0.7   # canlı, yerelin %70'inin altındaysa → blocked_shrink

# Class ALT-source include'ları ayrı ADT URL'lerine map olur (/includes/...),
# /source/main DEĞİL. Bunları ana-source ile kıyaslamak SAHTE drift verir → basename
# eşlemesinde elenir. (.clas.abap = ana source, GEÇ.)
#   .ccimp / .clas.locals_imp = local implementation (RAP behavior pool gövdesi)
#   .ccdef / .clas.locals_def = local definitions
#   .ccau  / .clas.testclasses = test classes
#   .clas.macros             = macros
# Hem abapGit (.clas.locals_imp.abap) hem ADT/araç (.ccimp.abap) adlandırması kapsanır.
_CLASS_SUBSOURCE_MARKERS = (
    ".clas.locals_def.abap",
    ".clas.locals_imp.abap",
    ".clas.testclasses.abap",
    ".clas.macros.abap",
    ".ccdef.abap",
    ".ccimp.abap",
    ".ccau.abap",
    ".ccmac.abap",
)


def _is_excluded_path(f: Path, erp_root: Path) -> bool:
    """Dosya muaf klasör altında mı (ref_docs/docs/.tmp ...)?"""
    try:
        rel_parts = {p.lower() for p in f.relative_to(erp_root).parts[:-1]}
    except Exception:
        rel_parts = {p.lower() for p in f.parts}
    return bool(rel_parts & _EXCLUDED_DIR_SEGMENTS)


def _is_class_subsource(fname_lower: str) -> bool:
    """Dosya bir class alt-include'ı mı (locals/testclasses/macros)?"""
    return fname_lower.endswith(_CLASS_SUBSOURCE_MARKERS)


def repo_root() -> Path:
    """PROJE repo kökü (env CLAUDE_PROJECT_DIR → cwd; kanonik: utils.project_config).

    ⚠ ASLA `__file__` kullanma: core script'leri proje içinden `core/` junction'ı
    üzerinden koşar ve `Path(__file__).resolve()` DEV_CORE'a çözülür — proje kökü
    DEĞİL (ADR 0020). Bu fonksiyon 2026-07-08 çoklu-proje geçişinde sessizce
    bozulmuştu: `repo_root()/SOURCE_CODES` = `DEV_CORE/SOURCE_CODES` (yok) →
    `find_repo_source_file()` daima None → `sap_sync_pull` "taze damgalanMADI" →
    PULL-BEFORE-EDIT (ADR 0016) hook'u HER SAP source Edit'ini bloklar hale geldi.
    """
    return _project_root()


def find_repo_source_file(
    object_name: str,
    erp_root: Optional[Path] = None,
    object_type: Optional[str] = None,
) -> Optional[Path]:
    """Bir SAP obje adına karşılık gelen repo kaynak dosyasını bul.

    Strateji: <source_root>/ altında `<NAME>.<source-ext>` ile eşleşen dosyayı ara
    (case-insensitive basename). `.md`/`.txt`/`.json`/`.xml` companion'lar elenir.
    object_type verilirse, eşleşen dosyalar o tipin uzantı setine (_TYPE_TO_EXTENSIONS)
    göre FİLTRELENİR — aynı ada sahip farklı-tip dosyalardan (ör. ZSD001_I_BOOKING'in
    `.cds` DDLS'i vs `.bdef` BDEF'i) doğru olanı seçer. object_type yoksa/bilinmiyorsa
    veya filtre boş kalırsa, SOURCE_EXTENSIONS öncelik sırasıyla tiebreak (geriye-uyumlu).

    Args:
        object_name: SAP obje adı (büyük/küçük harf önemsiz).
        erp_root: ERP kök dizini (test için override; varsayılan repo/ERP).
        object_type: ADT obje tipi (ddls/bdef/srvd/class/...) — isim çakışmasını çözer.

    Returns:
        Eşleşen dosya Path'i, yoksa None.
    """
    if erp_root is None:
        erp_root = repo_root() / SOURCE_ROOT_NAME
    if not erp_root.exists():
        return None

    name_lower = object_name.lower()
    candidates: list[Path] = []

    for f in erp_root.rglob("*"):
        if not f.is_file():
            continue
        fname = f.name.lower()
        # companion doküman/metadata dosyalarını ele
        if fname.endswith(_NON_SOURCE_SUFFIXES):
            continue
        # muaf klasör (ref_docs/docs/.tmp ...) → deploy kaynağı değil
        if _is_excluded_path(f, erp_root):
            continue
        # class alt-include'ları (/source/main değil) → sahte drift kaynağı
        if _is_class_subsource(fname):
            continue
        # basename (ilk '.'a kadar) obje adıyla birebir eşleşmeli
        base = fname.split(".", 1)[0]
        if base != name_lower:
            continue
        # gerçekten source uzantısı mı?
        if not any(fname.endswith(ext) for ext in SOURCE_EXTENSIONS):
            continue
        candidates.append(f)

    # object_type verilmişse aynı-adlı farklı-tip dosyaları ele (isim çakışması fix):
    # ZSD001_I_BOOKING → DDLS push'unda .cds, BDEF push'unda .bdef seçilmeli; tip
    # bilgisi olmadan tiebreak yanlış dosyayı alır → iki farklı objeyi kıyaslar.
    if object_type and candidates:
        exts = _TYPE_TO_EXTENSIONS.get(object_type.lower().strip())
        if exts:
            typed = [c for c in candidates if c.name.lower().endswith(exts)]
            if typed:  # tipe uyan dosya bulundu → yalnız onları değerlendir
                candidates = typed
            # typed boş → bu tipte dosya yok; tüm adayları koru (rank-fallback)

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    # Çoklu eşleşme → SOURCE_EXTENSIONS önceliği + yol (deterministik)
    def rank(p: Path) -> tuple:
        pl = p.name.lower()
        for idx, ext in enumerate(SOURCE_EXTENSIONS):
            if pl.endswith(ext):
                return (idx, str(p).lower())
        return (len(SOURCE_EXTENSIONS), str(p).lower())

    return sorted(candidates, key=rank)[0]


def normalize_source(text: str) -> str:
    """Source'u kıyas için normalize et.

    CRLF↔LF + satır-sonu trailing whitespace + baştaki/sondaki boş satır farkını
    YOK SAY. Yoksa SAHTE drift olur (template-drift-crlf-inflation dersi: raw diff
    her satırı CRLF↔LF farkıyla sayar → 614 sahte satır). İç boşlukları/içerik
    farkını KORUR — gerçek drift (eklenen/silinen expose vb.) yine yakalanır.
    """
    if text is None:
        return ""
    # SAP get_object_source zaten \r\r\n→\n yapıyor; yine de garantiye al
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in text.split("\n")]
    # baş/son boş satırları kırp
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _diff_summary(live: str, repo: str, max_lines: int = 12) -> str:
    """Kısa, aksiyon-alınabilir diff özeti (normalize edilmiş satır kümeleri)."""
    live_lines = [ln for ln in normalize_source(live).split("\n") if ln.strip()]
    repo_lines = [ln for ln in normalize_source(repo).split("\n") if ln.strip()]
    live_set = set(live_lines)
    repo_set = set(repo_lines)
    only_live = [ln.strip() for ln in live_lines if ln not in repo_set]
    only_repo = [ln.strip() for ln in repo_lines if ln not in live_set]

    parts = []
    parts.append(f"canlı={len(live_lines)} satır, repo={len(repo_lines)} satır")
    if only_live:
        shown = only_live[:max_lines]
        parts.append(
            "SADECE CANLI'da (repo push'u bunları SİLER): "
            + " | ".join(shown)
            + (f" …(+{len(only_live) - len(shown)})" if len(only_live) > len(shown) else "")
        )
    if only_repo:
        shown = only_repo[:max_lines]
        parts.append(
            "SADECE REPO'da (push bunları EKLER): "
            + " | ".join(shown)
            + (f" …(+{len(only_repo) - len(shown)})" if len(only_repo) > len(shown) else "")
        )
    return "  ".join(parts)


def compare_sources(live_source: Optional[str], repo_source: Optional[str]) -> tuple[bool, str]:
    """İki source'u normalize edip kıyasla.

    Returns:
        (is_drift, diff_summary)
        is_drift=False → eşit (veya biri yok → kıyaslanamaz, drift değil).
    """
    if live_source is None or repo_source is None:
        return False, "kıyaslanamadı (taraflardan biri yok)"
    if normalize_source(live_source) == normalize_source(repo_source):
        return False, "eşit (normalize sonrası)"
    return True, _diff_summary(live_source, repo_source)


def detect_drift_with_fetch(
    object_name: str,
    fetch_active: Callable[[], Optional[str]],
    erp_root: Optional[Path] = None,
    object_type: Optional[str] = None,
) -> dict:
    """Drift tespitinin saf çekirdeği — canlı source'u callback ile alır.

    Args:
        object_name: SAP obje adı.
        fetch_active: Argümansız çağrılabilir; canlı AKTİF source'u döndürür.
                      Obje yoksa None döndürmeli (yeni yaratım → drift YOK).
                      Hata fırlatırsa drift tespiti GÜVENLİ tarafta atlanır
                      (is_drift=False, reason).
        erp_root: ERP kökü override (test için).

    Returns:
        {
          "is_drift": bool,
          "repo_path": str|None,
          "diff_summary": str,
          "reason": str,          # PASS/BLOCK gerekçesi (insan-okunur)
        }
    """
    repo_file = find_repo_source_file(object_name, erp_root=erp_root, object_type=object_type)
    if repo_file is None:
        return {
            "is_drift": False,
            "repo_path": None,
            "diff_summary": "",
            "reason": "repo'da kaynak dosya yok — drift kıyası atlandı (GEÇ)",
        }

    try:
        live_source = fetch_active()
    except Exception as exc:  # noqa: BLE001 — fetch hatası push'u bricklemesin
        return {
            "is_drift": False,
            "repo_path": str(repo_file),
            "diff_summary": "",
            "reason": f"canlı source çekilemedi ({exc}) — drift kıyası atlandı (GEÇ)",
        }

    if live_source is None:
        return {
            "is_drift": False,
            "repo_path": str(repo_file),
            "diff_summary": "",
            "reason": "canlı obje yok (404) — yeni yaratım, drift yok (GEÇ)",
        }

    try:
        repo_source = repo_file.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return {
            "is_drift": False,
            "repo_path": str(repo_file),
            "diff_summary": "",
            "reason": f"repo dosyası okunamadı ({exc}) — drift kıyası atlandı (GEÇ)",
        }

    is_drift, summary = compare_sources(live_source, repo_source)
    if is_drift:
        reason = (
            f"DRIFT: canlı {object_name} repo dosyası {repo_file}'ten FARKLI. "
            f"Push canlıdaki belgelenmemiş değişiklikleri EZER. Önce sync-down "
            f"(canlıyı repo'ya çek) + reconcile, SONRA push. [{summary}]"
        )
    else:
        reason = f"repo == canlı ({summary}) — drift yok (GEÇ)"

    return {
        "is_drift": is_drift,
        "repo_path": str(repo_file),
        "diff_summary": summary,
        "reason": reason,
    }


def write_repo_from_live(
    object_name: str,
    live_source: str,
    erp_root: Optional[Path] = None,
    object_type: Optional[str] = None,
    force: bool = False,
) -> dict:
    """Pull-before-edit REPO SYNC: canlı aktif source'u repo dosyasına yaz.

    Mevcut dosyanın satır-sonu konvansiyonunu (LF/CRLF) KORUR. Dosya yoksa
    yazmaz (yol tahmini yapmaz — yanlış pakete dosya sızdırmamak için).

    UNCOMMITTED-LOCAL KORUMASI (FIX-B, force=False): yereldeki dosya canlıdan FARKLI
    VE git'te commit'lenmemiş değişiklik içeriyorsa, pull bu yerel emeği SESSİZCE EZERDİ
    (2026-06-21 gateway kaybı). Bu durumda YAZMAZ → {"written": False, "blocked_dirty": True}.
    force=True bilerek canlıya döner (yereli atar). Yerel temiz ise bayat demektir → tazelenir.

    Returns:
        {"written": bool, "repo_path": str|None, "reason": str, "blocked_dirty"?: bool, "noop"?: bool}
    """
    repo_file = find_repo_source_file(object_name, erp_root=erp_root, object_type=object_type)
    if repo_file is None:
        return {
            "written": False,
            "repo_path": None,
            "reason": "repo'da kaynak dosya yok — post-sync atlandı (yeni obje normal akışla eklenir)",
        }

    try:
        existing = repo_file.read_bytes()
    except Exception:
        existing = b""
    # Mevcut satır-sonu konvansiyonunu tespit et (CRLF varsa koru)
    use_crlf = b"\r\n" in existing

    body = live_source.replace("\r\n", "\n").replace("\r", "\n")
    if use_crlf:
        body = body.replace("\n", "\r\n")

    # No-op: yerel zaten canlı ile birebir aynı → yazma (dirty olsa da güvenli).
    if body.encode("utf-8") == existing:
        return {
            "written": True,
            "repo_path": str(repo_file),
            "reason": "repo zaten canlı aktif source ile birebir aynı (no-op)",
            "noop": True,
        }

    # FIX-B: yerel canlıdan FARKLI ve git-dirty ise EZME (commit'siz emeği koru).
    if not force and _git_working_copy_dirty(repo_file):
        return {
            "written": False,
            "repo_path": str(repo_file),
            "reason": (
                "yerelde COMMIT EDİLMEMİŞ değişiklik var ve canlı aktif sürümden FARKLI — "
                "pull canlıyı yazsaydı bu yerel emek SESSİZCE EZİLİRDİ. ATLANDI (WIP korundu). "
                "Yereli koru: önce commit/push et; bilerek canlıya dönmek istiyorsan --force ver."
            ),
            "blocked_dirty": True,
        }

    # FIX-D (ölçüldü 2026-07-31, FIX-C'nin KAÇIRDIĞI vaka): canlı içerik, bu dosyanın
    # GEÇMİŞ bir commit'indeki hâliyle birebir eşleşiyorsa pull "tazeleme" değil,
    # kendi geçmişimize DÖNÜŞtür → yerel yeni iş ezilir.
    # Ölçülen vaka: ZSD001_CL_X pull edildi, araç "[OK]" dedi; HEAD ↔ pull farkı 32 satır,
    # 32'si YORUM, KOD 0 → commit'li bir düzeltme canlının eski hâliyle ezildi. FIX-C bunu
    # YAKALAYAMADI çünkü satır sayısı düşmedi, yalnız içerik geriye gitti.
    # YAPISAL SEBEP: tek-yazıcı (gateway) mimarisinde yerel RUTİN OLARAK canlıdan ileridedir
    # (yazıldı+commit'lendi, henüz push/aktive edilmedi). "Düzenlemeden önce pull et" kuralı
    # o pencerede her seferinde commit'li işi geri alır.
    # Bu sinyal yanlış pozitif üretmez: eşleşme yoksa canlıda gerçekten yeni bir şey vardır.
    if not force:
        _older = _live_matches_older_commit(repo_file, body.encode("utf-8"))
        if _older:
            return {
                "written": False,
                "repo_path": str(repo_file),
                "reason": (
                    f"canlı AKTİF sürüm, bu dosyanın GEÇMİŞ bir commit'iyle ({_older}) BİREBİR "
                    "aynı — yani repo'da bir zamanlar tam olarak bu içerik vardı ve sonra "
                    "üzerine yazılıp commit'lendi. Pull burada 'tazeleme' değil, KENDİ "
                    "GEÇMİŞİMİZE DÖNÜŞ olur ve commit'li yerel iş EZİLİR. Muhtemel sebep: "
                    "obje push edilmemiş ya da push edilip AKTİVE EDİLMEMİŞ (pull AKTİF sürümü "
                    "okur). ATLANDI. Bilerek canlıya dönmek istiyorsan --force ver."
                ),
                "blocked_behind": True,
                "behind_commit": _older,
            }

    # FIX-C (ölçüldü 2026-07-31): "yerel TEMİZ ise BAYAT demektir" varsayımı YANLIŞ.
    # FIX-B yalnız COMMIT EDİLMEMİŞ emeği korur. Ama normal akışımızda yeni sürüm yazılır,
    # COMMIT edilir, henüz push/aktive EDİLMEZ → yerel git'te temizdir ama canlıdan İLERİDİR.
    # O anda pull canlı ESKİYİ yerel YENİNİN üzerine yazıp "[OK]" der (sessiz veri kaybı).
    # Ölçülen iki vaka (ikisi de commit'liydi, FIX-B devreye girmedi):
    #   T01  267 → 113 satır  (canlı AKTİF sürüm v1; v2 push edilmişti ama aktive edilmemişti)
    #   I02  141 →   1 satır  (canlı AKTİF sürüm boş kabuk; pull AKTİF okur, INAKTİF'i görmez)
    # Sinyal: canlıda belirgin İÇERİK KAYBI. Bu "tazeleme" değil, yıkım olabilir.
    # Eşikler bilinçli gevşek: küçük dosyalar ve normal tazeleme etkilenmesin.
    old_lines = len(existing.decode("utf-8", errors="replace").splitlines()) if existing else 0
    new_lines = len(body.splitlines())
    if not force and old_lines >= _SHRINK_MIN_LINES and new_lines < old_lines * _SHRINK_KEEP_RATIO:
        return {
            "written": False,
            "repo_path": str(repo_file),
            "reason": (
                f"canlı AKTİF sürüm yerelden BELİRGİN KÜÇÜK ({old_lines} → {new_lines} satır). "
                "Bu 'bayat yerel tazelendi' DEĞİL, yerel yeni işin EZİLMESİ olabilir: obje henüz "
                "push edilmemiş ya da push edilip AKTİVE EDİLMEMİŞ olabilir (pull AKTİF sürümü "
                "okur, INAKTİF'i görmez). ATLANDI. Canlıyı gerçekten istiyorsan --force ver."
            ),
            "blocked_shrink": True,
        }

    try:
        repo_file.write_text(body, encoding="utf-8", newline="")
    except Exception as exc:  # noqa: BLE001
        return {
            "written": False,
            "repo_path": str(repo_file),
            "reason": f"yazılamadı: {exc}",
        }
    return {
        "written": True,
        "repo_path": str(repo_file),
        "reason": f"repo dosyası canlı aktif source ile senkronlandı ({'CRLF' if use_crlf else 'LF'})",
    }
