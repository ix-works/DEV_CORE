"""
check_fs_no_analysis_log.py — FS gövdesine "analiz günlüğü" sızması kontrolü (DOC-FS-05/06, İLKE-2b).

Neden: Çok sürümlü bir FS'te her tur "v1.x'te şu değişti", "(doc-gate H-C netleşme)", "DEV'de canlı
ölçüldü — ilk turda alan adı yanlıştı, 400 döndü", "kullanıcı: '…'" gibi izler GÖVDEYE yazılınca
belge, yapılacak işi tarif eden bir spesifikasyon olmaktan çıkıp danışmanın çalışma defterine döner
(2026-08-17 dersi: 9 sürümlük FS gövdesinde satırların ~%25'i işaretliydi; kullanıcı onaya sunulamaz
buldu). Dünya pratiği 3 katman ister: gövde = kapanmış hedef durum · karar günlüğü (11-A/11-B/EK) ·
analiz süreci (RESEARCH/notlar). Bu gate katman-1'e sızmayı SAYAR.

Kapsam: proje `**/docs/FS-*.md` ve `**/docs/EK-*.md` (FS ekleri). Gövde = §1.1 versiyon geçmişi
tablosu, 11-A/11-B bölümleri ve başlığında "Karar" + ("Günlü"|"Açık"|"Öneri") geçen bölümler
(katman-2 alanı) HARİÇ kalan her şey. §1.1 için ayrıca satır-uzunluğu eşiği (DOC-FS-06).

Sayılan işaretler (satır bazında, sınıf sınıf raporlanır):
  A sürüm-etiketi   : v1.5 / v1.5-taslak / "(YENİ, ...)" / "eklendi|revize edildi|düzeltildi" + sürüm
  B gate-bulgu ID   : doc-gate · H-A..H-D · H-1..9 / M-1..9 / L-1..9 (tek hane; L-01 gibi hata kodları DEĞİL)
  C süreç ifadesi   : canlı ölçüldü/ölçüm · DEV'de ölçüldü · ilk turda · yazılmıştı/okumuştu · 400 döndü ·
                      ADT preview · RESEARCH-0n ters/yanlış · "önceden/eskiden … yerine"
  D kullanıcı alıntı: tırnaklı "kullanıcı: '…'" · tarihli "kullanıcı notu/kararı/teyidi GG.AA" (kısa atıf "kullanıcı kararı §9" MEŞRU)

Warn-first (ADR 0019): varsayılan exit 0 + WARN listesi; `--strict` → bulgu varsa exit 1.
`--selftest` → gömülü kırmızı-fixture ile kendi kendini test eder (yakalamazsa exit 1).
Kullanım: python scripts/validators/check_fs_no_analysis_log.py [--strict] [--selftest] [--max-examples N]
"""
# ENFORCES: DOC-FS-05, DOC-FS-06  (ADR 0019 coverage binding)
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.project_config import project_root  # noqa: E402

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO = project_root()
_SKIP = {"node_modules", "dist", "tmp", ".tmp", ".git", "fixtures", "attic", "archive"}

_TR = "A-Za-zÇĞİÖŞÜçğıöşü"
PATTERNS = {
    "A sürüm-etiketi": re.compile(
        r"(?<![A-Za-z0-9])v\d\.\d{1,2}(?:[a-c])?(?:-taslak)?(?![0-9])"      # v1.5, v1.5c, v1.8-taslak
        r"|\(\*{0,2}YENİ[,\s]"                                                # (YENİ, R-26) / (**YENİ, ...
        r"|\bv\d\.\d'(?:te|de|da|ta)\b",                                       # v1.6'da
        re.IGNORECASE),
    "B gate-bulgu ID": re.compile(
        r"doc-gate|\bH-[A-D]\b|(?<![%s0-9-])[HML]-[1-9](?![0-9])" % _TR),
    "C süreç ifadesi": re.compile(
        r"canlı ölç|canlı teyit|DEV'de ölç|DEV canlı|ilk turda|yazılmıştı(?!r)|okumuştu|okunmuştu|sanılmış"
        r"|400 döndü|\b400 verdi|ADT preview|adt_sql|RESEARCH-0\d[^|]{0,40}(?:ters|yanlış)"
        r"|(?:önceden|eskiden|daha önce)[^|]{0,60}(?:yerine|artık)", re.IGNORECASE),
    "D kullanıcı alıntı": re.compile(
        r"[Kk]ullanıcı(?:\s+\d\d\.\d\d)?\s*:\s*[\"“']|[Kk]ullanıcı (?:notu|kararı|teyidi|geri bildirimi)\s+\d\d\.\d\d"),
}
VERSION_ROW_MAX = 400  # §1.1 satırı (karakter) — 1-2 satır ≈ ≤400

_LOG_HEADING = re.compile(r"karar", re.IGNORECASE)
_LOG_HEADING2 = re.compile(r"günlü|açık|öneri|11-A|11-B", re.IGNORECASE)


def _iter_docs(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d.lower() not in _SKIP]
        if Path(dirpath).name.lower() != "docs":
            continue
        for fn in filenames:
            low = fn.lower()
            if low.endswith(".md") and (low.startswith("fs-") or low.startswith("ek-")):
                yield Path(dirpath) / fn


def _is_log_heading(h: str) -> bool:
    return bool(_LOG_HEADING.search(h) and _LOG_HEADING2.search(h)) or "11-A" in h or "11-B" in h


def scan_text(text: str):
    """→ (findings: {cls: [(lineno, snippet)]}, version_rows_too_long: [(lineno, len)], body_lines: int)"""
    lines = text.splitlines()
    findings = {k: [] for k in PATTERNS}
    long_rows = []
    in_log = False
    in_version = False
    in_code = False
    body_lines = 0
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if s.startswith("#"):
            h = s.lstrip("#").strip()
            level = len(s) - len(s.lstrip("#"))
            if level <= 3:
                in_version = bool(re.match(r"1\.1\b", h)) or "versiyon geçmişi" in h.lower()
                in_log = _is_log_heading(h) and not in_version
            continue
        if in_version:
            if s.startswith("|") and not s.startswith("|---") and "Versiyon" not in s and len(s) > VERSION_ROW_MAX:
                long_rows.append((i, len(s)))
            continue
        if in_log or in_code or not s:
            continue
        body_lines += 1
        for k, rx in PATTERNS.items():
            if rx.search(ln):
                findings[k].append((i, s[:110]))
    return findings, long_rows, body_lines


def _report(path, findings, long_rows, body_lines, max_examples):
    total = sum(len(v) for v in findings.values())
    if total == 0 and not long_rows:
        return 0
    rel = path.relative_to(REPO) if str(path).startswith(str(REPO)) else path
    print(f"[WARN] {rel}: gövde {body_lines} satır — analiz-günlüğü işareti {total} satır"
          + (f" · §1.1 uzun satır {len(long_rows)}" if long_rows else ""))
    for k, v in findings.items():
        if not v:
            continue
        print(f"    {k}: {len(v)}")
        for ln, sn in v[:max_examples]:
            print(f"       :{ln}  {sn}")
    for ln, L in long_rows[:max_examples]:
        print(f"    §1.1 :{ln}  {L} karakter (> {VERSION_ROW_MAX}) — 1-2 satıra indir, gerekçeyi EK'e")
    return total + len(long_rows)


RED_FIXTURE = """# FS-XX-999 Örnek
## BÖLÜM 1: DÖKÜMAN KONTROLÜ
### 1.1 Versiyon Geçmişi
| Versiyon | Tarih | Hazırlayan | Açıklama |
|---|---|---|---|
| 1.5-taslak | 01.01.2026 | X | """ + ("uzun anlatı " * 60) + """ |
### 1.2 Dağıtım
| a | b |
## BÖLÜM 3: SÜREÇ
Fatura tipi ZM12 (R-22 — DEV TVAK canlı ölçüm: FKARV=ZM12; ilk turda alan adı yanlış yazılmıştı, 400 döndü).
| C4 | (**YENİ, R-26**) Kontrol Et butonu (doc-gate v1.5 H-C netleşme) |
Kullanıcı: "fiyat koşulumuz Z001 olmalı" — kullanıcı notu 17.08.
Hata kodu L-01 ve M-02 burada meşru hata kodudur (yakalanmamalı).
## BÖLÜM 11-B: AÇIK KARARLAR / SORU SETİ
| S-19 | v1.7'de eklendi, doc-gate M-2 | (burası katman-2, sayılmaz) |
"""


def selftest() -> int:
    f, lr, _ = scan_text(RED_FIXTURE)
    ok = True
    exp = {"A sürüm-etiketi": 1, "B gate-bulgu ID": 1, "C süreç ifadesi": 1, "D kullanıcı alıntı": 1}
    for k, n in exp.items():
        if len(f[k]) < n:
            print(f"[SELFTEST-FAIL] {k}: beklenen ≥{n}, bulunan {len(f[k])}"); ok = False
    if any("L-01" in sn or "M-02" in sn for k in ("B gate-bulgu ID",) for _, sn in f[k]):
        print("[SELFTEST-FAIL] hata kodu L-01/M-02 gate-ID sanıldı"); ok = False
    if any(ln > 15 for k in f for ln, _ in f[k]):
        print("[SELFTEST-FAIL] 11-B (katman-2) satırı gövde sayıldı"); ok = False
    if not lr:
        print("[SELFTEST-FAIL] §1.1 uzun satır yakalanmadı"); ok = False
    print("[SELFTEST] " + ("OK — kırmızı fixture yakalandı, meşru kodlar/katman-2 atlandı" if ok else "FAIL"))
    return 0 if ok else 1


def main() -> int:
    argv = sys.argv[1:]
    if "--selftest" in argv:
        return selftest()
    strict = "--strict" in argv
    max_examples = 3
    if "--max-examples" in argv:
        max_examples = int(argv[argv.index("--max-examples") + 1])
    total = 0
    n_docs = 0
    for p in _iter_docs(REPO):
        n_docs += 1
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        f, lr, bl = scan_text(text)
        total += _report(p, f, lr, bl, max_examples)
    if total == 0:
        print(f"FS analiz-günlüğü kontrolü (DOC-FS-05/06): temiz — {n_docs} FS/EK dokümanı, gövdede işaret yok.")
        return 0
    print()
    print(f"Özet: {total} işaretli satır ({n_docs} doküman). Kural: gövde = kapanmış hedef durum; sürüm etiketi/"
          "gate-ID/süreç ifadesi/kullanıcı alıntısı → EK 'Karar ve Kanıt Günlüğü' (std 04 §2.0 İLKE-2b).")
    print("Warn-first (ADR 0019): bloklamaz" + (" — --strict ile exit 1" if strict else "") + ".")
    return 1 if strict else 0


if __name__ == "__main__":
    sys.exit(main())
