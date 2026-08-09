# -*- coding: utf-8 -*-
"""proje_slug_tek_kaynak — Claude Code proje-slug'ı: TEK sözleşme, TEK kaynak (KAYIT S4).

KÖK: `~/.claude/projects/<slug>/` adının türetimi BEŞ script'te bağımsız yazılmıştı ve
İKİ sözleşme oluşmuştu:
    A  re.sub(r"[^A-Za-z0-9]", "-", yol)                              (alt çizgi -> '-')
    B  yol.replace(":", "-").replace("\\\\", "-").replace("/", "-")     (alt çizgiyi KORUR)
B, yolunda alt çizgi/nokta olmayan projelerde A ile AYNI sonucu verir — bu yüzden sapma
`C:\\IX\\DEV_CORE` ya da `<KOK>\\template_project` gibi yollara kadar GÖRÜNMEZ kaldı; orada
var-olmayan bir dizin gösterip sessizce boş sonuç üretiyordu.

ÖLÇÜM (kontrol grubu): Claude Code'un KENDİ yazdığı transcript'lerde her satırda `cwd`
alanı var → "dizin adı ↔ gerçek yol" eşlemesi doğrudan okunur. Transcript TAŞIYAN 4 dizinde
A 4/4, B 2/4 tutturdu → **kanonik = A**. Aşağıdaki vektörler o ölçümün dondurulmuş halidir
(yol/proje adları jenerikleştirildi; belirleyici olan ŞEKİL: alt çizgi '-' oluyor mu).

⚠ Alt çizgi TAŞIYAN bir dizin "CC alt çizgiyi korur" sanılmıştı; o dizinde HİÇ `*.jsonl`
YOK — CC onu yazmamış (içinde yalnız script'le konmuş `memory/` var). Konvansiyonu,
konvansiyonu uygulayan aracın ÇIKTISI belirler.

Koşum:  python tests/fixtures/proje_slug_tek_kaynak/run.py
MUTASYON: claude_paths._SLUG_RE'yi `[^A-Za-z0-9_]` yap (alt çizgiyi koru) → V1/V2 FAIL.
          Herhangi bir çağıranı kendi yerel slug'ına döndür → V3 FAIL.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

KOK = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(KOK / "scripts"))
from utils.claude_paths import auto_memory_dizini, proje_slug, transcript_dizini  # noqa: E402

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, ok, detay))


# ── V1 — DONDURULMUŞ ÖLÇÜM: gözlenen (yol -> dizin adı) çiftleri ────────────────
#   Belirleyici olan üç vektörde ayıraç DIŞINDA da alfanümerik-olmayan karakter var.
VEKTORLER = [
    (r"C:\KOK_ALT\PROJE1",      "C--KOK-ALT-PROJE1"),   # alt çizgi -> '-'  (B burada X)
    (r"C:\KOK_ALT\PROJE2",      "C--KOK-ALT-PROJE2"),   # aynı (2. gözlem)
    (r"C:\IX\PROJE3",           "C--IX-PROJE3"),        # A ve B eşit (ayırt etmez)
    (r"C:\PROJE4",              "C--PROJE4"),           # A ve B eşit (ayırt etmez)
    (r"C:\IX\DEV_CORE",         "C--IX-DEV-CORE"),      # bu repo: sapmanın vurduğu şekil
    (r"C:\IX\template_project", "C--IX-template-project"),
]
sapan = [f"{y} -> {proje_slug(y)!r} (beklenen {b!r})" for y, b in VEKTORLER if proje_slug(y) != b]
kontrol("V1 dondurulmuş ölçüm: 6 vektörün hepsi kanonik A sözleşmesini veriyor",
        not sapan, "; ".join(sapan))

# ── V2 — AYIRT EDİCİ vektör: alt çizgi KORUNMAMALI (B sözleşmesi reddedilir) ────
B = lambda p: p.replace(":", "-").replace("\\", "-").replace("/", "-")  # noqa: E731
ayirt = r"C:\IX\DEV_CORE"
kontrol("V2 ayırt edici: alt çizgili yolda kanonik ≠ eski-B sözleşmesi",
        proje_slug(ayirt) != B(ayirt) and "_" not in proje_slug(ayirt),
        f"kanonik={proje_slug(ayirt)!r} eskiB={B(ayirt)!r}")

# ── V3 — TEK KAYNAK: hiçbir çağıran kendi slug'ını yeniden türetmiyor ──────────
#   (Sınıfın kendisi buydu: kural dağınıkken iki sözleşme sessizce ayrıştı.)
CAGIRANLAR = ["seed_memory.py", "agent_log.py", "ix_doctor.py", "inspector.py",
              "agent_time_report.py", "build_recall_index.py"]
YEREL_DESEN = re.compile(
    r"""re\.sub\(\s*r?["']\[\^A-Za-z0-9\]|"""            # yerel A kopyası
    r"""replace\(\s*["']:["']\s*,\s*["']-["']\s*\)""")   # yerel B kopyası
kirli = []
for ad in CAGIRANLAR:
    p = KOK / "scripts" / ad
    if not p.is_file():
        kirli.append(f"{ad}: DOSYA YOK")
        continue
    govde = p.read_text(encoding="utf-8", errors="replace")
    # yorum satırlarını çıkar (tarihçe anlatan yorumlar meşru)
    kod = "\n".join(s for s in govde.splitlines() if not s.lstrip().startswith("#"))
    if YEREL_DESEN.search(kod):
        kirli.append(ad)
kontrol("V3 TEK KAYNAK: 6 çağıranın hiçbirinde yerel slug türetimi kalmadı",
        not kirli, f"yerel türetim taşıyan={kirli}")

# ── V4 — çağıranlar claude_paths'i GERÇEKTEN import ediyor (kod ≠ kablolama) ───
kablosuz = [ad for ad in CAGIRANLAR
            if "claude_paths" not in (KOK / "scripts" / ad).read_text(encoding="utf-8",
                                                                     errors="replace")]
kontrol("V4 KABLOLAMA: 6 çağıranın hepsi utils.claude_paths'i import ediyor",
        not kablosuz, f"import etmeyen={kablosuz}")

# ── V5 — yol birleştirme sözleşmesi (memory dizini transcript dizininin altında) ─
ornek = r"C:\IX\DEV_CORE"
kontrol("V5 auto_memory_dizini == transcript_dizini/memory",
        auto_memory_dizini(ornek) == transcript_dizini(ornek) / "memory"
        and auto_memory_dizini(ornek).name == "memory",
        f"{auto_memory_dizini(ornek)}")

# ── V6 — 3. BAĞLAM (görev-dışı): POSIX yol şekli de tek-sözleşmeye uyuyor ──────
kontrol("V6 3.BAĞLAM: POSIX yol (/home/x/dev_core) da aynı kuralla türetiliyor",
        proje_slug("/home/x/dev_core") == "-home-x-dev-core",
        f"alınan={proje_slug('/home/x/dev_core')!r}")

# ── V7 — modül gerçekten TEK tanım taşıyor (kopyala-yapıştır regresyonu) ──────
agac = ast.parse((KOK / "scripts" / "utils" / "claude_paths.py").read_text(encoding="utf-8"))
adlar = [d.name for d in agac.body if isinstance(d, ast.FunctionDef)]
kontrol("V7 claude_paths tek tanım kümesi (mükerrer def yok)",
        len(adlar) == len(set(adlar)), f"tanımlar={adlar}")

gecen = sum(1 for _, ok, _ in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok:
        print(f"         -> {detay}")
print(f"\n{gecen}/{len(SONUC)} OK")
sys.exit(0 if gecen == len(SONUC) else 1)
