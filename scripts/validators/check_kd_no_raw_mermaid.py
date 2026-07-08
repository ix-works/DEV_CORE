"""
check_kd_no_raw_mermaid.py — KD çıktısına ham diyagram-kaynağı (mermaid) SIZMASI kontrolü (DOC-KD-15).

Neden: Kullanıcı Dökümanı (KD) markdown'ında ` ```mermaid ` fence build sırasında RENDER
EDİLMEZSE, üretilen HTML/app-help'te `<pre><code class="language-mermaid">flowchart…` = ham
KOD olarak görünür → son kullanıcıya çirkin/anlamsız. Diyagram render edilmiş PNG (<img>) olmalı
(doc_tools.preprocess_mermaid_fences / render_mermaid build'e bağlı).

Bu tuzak fit_se'de (2026-06-26) yaşandı, sonra booking+shipment+4 rapor KD'sinde TEKRARLADI
(2026-07-02) — doc bug-gate DOC-KD-11 "broken-image 0" bunu YAKALAMADI (mermaid kod olarak
render olur, KIRIK GÖRSEL değil). Bu yüzden ayrı, atlanamaz statik gate.

Kapsam: KULLANICI-YÜZLÜ çıktı = KD HTML (docs/**/KD-*.html) + app-içi yardım
(ui/**/webapp/help/kullanici-kilavuzu.html). md fence'i KAYNAK olarak meşrudur (build render
ederse) — bu yüzden md DEĞİL, ÇIKTI HTML denetlenir. dist/ build-artefaktı → elenir.

Kullanım:  python scripts/validators/check_kd_no_raw_mermaid.py
Exit: 0 temiz · 1 en az bir KD çıktısında ham mermaid.
"""
# ENFORCES: DOC-KD-15  (ADR 0019 coverage binding)
import os
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent.parent

_SKIP_SEGMENTS = {"node_modules", "dist", "tmp", ".tmp", ".git"}

# Ham (render EDİLMEMİŞ) mermaid işaretleri — marked/markdown-it kod-bloğu çıktısı + çıplak div.
_RAW_MERMAID_RE = re.compile(r'language-mermaid|class="mermaid"|<code[^>]*>\s*flowchart\b', re.IGNORECASE)


def _iter_kd_html():
    """docs/**/KD-*.html + ui/**/webapp/help/kullanici-kilavuzu.html (dist hariç)."""
    for dirpath, dirnames, filenames in os.walk(REPO):
        dirnames[:] = [d for d in dirnames if d.lower() not in _SKIP_SEGMENTS]
        parts = {p.lower() for p in Path(dirpath).parts}
        for fn in filenames:
            low = fn.lower()
            is_kd_doc = low.startswith("kd-") and low.endswith(".html")
            is_app_help = low == "kullanici-kilavuzu.html" and "help" in parts
            if is_kd_doc or is_app_help:
                yield Path(dirpath) / fn


def _scan():
    findings = []  # (file, lineno, snippet)
    for f in _iter_kd_html():
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        for i, ln in enumerate(lines, 1):
            if _RAW_MERMAID_RE.search(ln):
                findings.append((f, i, ln.strip()[:120]))
    return findings


def main() -> int:
    findings = _scan()
    if not findings:
        print("KD ham-mermaid kontrolü: temiz (render edilmemiş diyagram-kaynağı yok).")
        return 0
    for f, ln, snippet in findings:
        rel = f.relative_to(REPO)
        print(f"[İHLAL] {rel}:{ln}  ham mermaid/diyagram-kaynağı (render EDİLMEMİŞ)  → {snippet}")
    print()
    print(f"Özet: {len(findings)} ham-mermaid ihlali (DOC-KD-15).")
    print("Diyagram render edilmiş PNG olmalı: build_kd_pdf_<app>.py'ye doc_tools.preprocess_mermaid_fences")
    print("bağla (```mermaid → <img>). fit_se/screenshots/diagram-01.png kanonik örnek.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
