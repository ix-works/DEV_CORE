# -*- coding: utf-8 -*-
"""gitignore_tam_satir — core-sızıntı kilidi ALT-DİZGE mi TAM SATIR mı arıyor (KAYIT V4).

KÖK: `check_core_not_committed` içinde İKİ kilit kontrolü vardı, FARKLI titizlikte:
  • (2) core-sızıntı kilidi  → `s not in icerik`  (ALT-DİZGE, tüm dosya metninde)
  • (4) SIR kilidi           → tam-satır kümesi   (DOĞRU teknik, gerekçesi de yazılı:
        "`.conn_adt` alt-dizgesi `conn/.conn_adt.bak` içinde de geçer", K3/2026-07-10)
Yani doğru teknik AYNI DOSYADA duruyordu ve ikinci kontrole uygulanmamıştı. Alt-dizge
araması şu satırların hepsini "kilit VAR" sayar:
    `#/core/`                   → YORUM, hiçbir etkisi yok
    `!.claude/agents/ozel.md`   → NEGASYON, ignore'u KALDIRIR
    `docs/core/README.md`       → alakasız bir yol; içinde `/core/` dizgesi geçiyor
Kilidi SÖKÜLMÜŞ bir repoda gate `[OK] core-sızıntı kilidi sağlam` diyordu. Bu, gate'in
koruduğunu iddia ettiği tam senaryodur: junction'lı core içeriğinin proje reposuna
commit'lenmesi — sonucu SESSİZ ve (push'landıysa) GERİ ALINAMAZ.

FIX SINIFI: `etkin_satirlar()` tek kaynağı — yorum (`#`) ve negasyon (`!`) satırları
elenir, karşılaştırma TAM SATIR üzerinden yapılır; iki kontrol de aynı kümeyi kullanır.

⚠ FP ÇAPALARI OMURGADIR: `kilit_var()` eşdeğer yazımları (`core/` ~ `/core/` ~ `/core`)
kabul eder. Bunlar düşerse gate, FİİLEN korunan bir repoya sahte FAIL basar — ve sahte
FAIL bypass alışkanlığı doğurur (08bb6e6, `_win_yol` vakası: meşru commit bloklanmıştı).
N4 (gerçek proje `.gitignore`'unun şekli) bu kararın canlı çapasıdır.

⚠ KONTROL GRUBU (K1/K2): satırın HİÇ olmaması ve sır satırının yorumlanması — eskiden de
yakalanan varyantlar. İki tarafta da FAIL vermeli (PATTERN#19).

Koşum:  python tests/fixtures/gitignore_tam_satir/run.py
MUTASYON: `git show <taban-sha>:scripts/validators/check_core_not_committed.py` →
          P1/P2/P3 düşer, K1/K2/N* ayakta kalır.
"""
from __future__ import annotations

import os
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

KOK = Path(__file__).resolve().parents[3]
GATE = KOK / "scripts" / "validators" / "check_core_not_committed.py"

SONUC: list[tuple[bool, str]] = []


def kontrol(ok: bool, ad: str, detay: str = "") -> None:
    SONUC.append((ok, ad + (f" — {detay}" if detay else "")))


# Kanonik (init_project şablonu) kilit bloğu — testlerin temiz tabanı.
KANONIK = """# proje ignore
node_modules/
.tmp/

# SIZINTI KILIDI
/core/
.claude/agents/
.claude/skills/
.claude/commands/
.claude/rules/

# SIR
.conn_adt
.csrf_token.json
.claude/project.local.yaml
"""


def repo_kur(kok: Path, gitignore: str) -> Path:
    """Sentetik bir git reposu kurar (gate `.git` yoksa SKIP eder — o yol test edilmez)."""
    kok.mkdir(parents=True, exist_ok=True)
    (kok / ".gitignore").write_text(gitignore, encoding="utf-8")
    for c in (["init", "-q"], ["config", "user.email", "fixture@example.com"],
              ["config", "user.name", "fixture"]):
        subprocess.run(["git", "-C", str(kok), *c], capture_output=True, text=True)
    return kok


def kos(proje: Path) -> tuple[int, str]:
    env = os.environ.copy()
    for k in list(env):
        if k == "CLAUDE_PROJECT_DIR" or k.startswith("IX_"):
            env.pop(k, None)
    env["CLAUDE_PROJECT_DIR"] = str(proje)
    try:
        r = subprocess.run([sys.executable, str(GATE)], cwd=str(proje), env=env,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=120)
    except Exception as e:  # noqa: BLE001  (mutasyon-dostu)
        return (-1, f"KOŞULAMADI: {type(e).__name__}: {e}")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# ── P1: kilit satırı YORUMLANMIŞ (etkisiz) ama alt-dizge olarak dosyada var ─────────
P1 = KANONIK.replace("/core/\n", "#/core/\n")

# ── P2: kilit satırı NEGASYONA çevrilmiş (ters etki) ───────────────────────────────
P2 = KANONIK.replace(".claude/agents/\n", "!.claude/agents/ozel.md\n")

# ── P3: kilit hiç yok, ama alt-dizgeyi taşıyan ALAKASIZ yollar var ─────────────────
P3 = """node_modules/
docs/core/README.md
build/.claude/agents/notlar.md
.conn_adt
.csrf_token.json
.claude/project.local.yaml
.claude/skills/
.claude/commands/
.claude/rules/
"""

# ── K1 (KONTROL): kilit satırı düpedüz YOK (alt-dizge de yok) → eskiden de FAIL ────
K1 = KANONIK.replace(".claude/skills/\n", "")

# ── K2 (KONTROL): SIR satırı yorumlanmış → tam-satır kontrolü eskiden de yakalardı ─
K2 = KANONIK.replace(".conn_adt\n", "#.conn_adt\n")

# ── N1 (FP ÇAPASI): kanonik blok → PASS ───────────────────────────────────────────
N1 = KANONIK

# ── N2 (FP ÇAPASI): eşdeğer yazım (baştaki eğik çizgi yok) → PASS ────────────────
N2 = KANONIK.replace("/core/\n", "core/\n")

# ── N3 (FP ÇAPASI): satır sonu boşluk + CRLF karışımı → PASS ─────────────────────
N3 = KANONIK.replace("/core/\n", "/core/   \n").replace(
    ".claude/rules/\n", ".claude/rules/\r\n")

# ── N4 (FP ÇAPASI): kilit bloğunun ETRAFINDA yorumlar/negasyonlar var → PASS ─────
#    (gerçek proje .gitignore'ları böyle görünür; eleme fazla agresif olmamalı)
N4 = """# SIZINTI KILIDI (ADR 0020)
# core icerigi proje reposuna ASLA commit'lenmez
/core/
.claude/agents/
.claude/skills/
.claude/commands/
.claude/rules/
!.claude/settings.json
.conn_adt
.csrf_token.json
.claude/project.local.yaml
"""

SENARYOLAR: list[tuple[str, str, bool, str, str]] = [
    # (kod, gitignore, FAIL_bekleniyor, beklenen_mesaj_parcasi, açıklama)
    ("P1", P1, True, "GITIGNORE", "P1 YORUMLANMIŞ kilit satırı → FAIL (alt-dizge tuzağı)"),
    ("P2", P2, True, "GITIGNORE", "P2 NEGASYONA çevrilmiş kilit satırı → FAIL"),
    ("P3", P3, True, "GITIGNORE", "P3 kilit yok; alt-dizge alakasız yollarda → FAIL"),
    ("K1", K1, True, "GITIGNORE", "K1 KONTROL kilit satırı düpedüz yok → FAIL"),
    ("K2", K2, True, "SIR", "K2 KONTROL sır satırı yorumlanmış → FAIL"),
    ("N1", N1, False, "", "N1 FP kanonik kilit bloğu → PASS"),
    ("N2", N2, False, "", "N2 FP eşdeğer yazım `core/` → PASS"),
    ("N3", N3, False, "", "N3 FP satır-sonu boşluk + CRLF → PASS"),
    ("N4", N4, False, "", "N4 FP gerçek .gitignore şekli (yorum + ilgisiz negasyon) → PASS"),
]


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="gitignore_kilit_"))
    try:
        for kod, gi, fail_bekleniyor, parca, ad in SENARYOLAR:
            proje = repo_kur(tmp / kod, gi)
            rc, cikti = kos(proje)
            if rc < 0:
                kontrol(False, ad, cikti)
                continue
            oldu = rc != 0
            ok = oldu == fail_bekleniyor and (not parca or parca in cikti)
            kontrol(ok, ad, f"exit={rc} (beklenen {'1' if fail_bekleniyor else '0'})"
                    + ("" if ok else " :: " + cikti.strip()[:220]))

        # ── Yapısal çapa: tek-kaynak gerçekten TEK mi (iki kontrol aynı kümeyi kullanıyor) ──
        sys.path.insert(0, str(KOK / "scripts" / "validators"))
        try:
            import check_core_not_committed as C  # noqa: PLC0415
            f = getattr(C, "etkin_satirlar", None)
            if f is None:
                kontrol(False, "S1 `etkin_satirlar` tek-kaynağı var", "fonksiyon YOK")
            else:
                s = f("#a\n  # b\n!c\n\n  d  \ne\r\n")
                kontrol(s == {"d", "e"},
                        "S1 etkin_satirlar: yorum(#)+negasyon(!)+boş elenir, CRLF kırpılır",
                        f"gelen={sorted(s)}")
            g = getattr(C, "kilit_var", None)
            if g is None:
                kontrol(False, "S2 `kilit_var` eşdeğer-yazım kabulü", "fonksiyon YOK")
            else:
                kontrol(all(g({v}, "/core/") for v in ("core", "/core", "core/", "/core/"))
                        and not g({"docs/core/x.md"}, "/core/"),
                        "S2 kilit_var: eşdeğer yazımlar kabul, alt-dizge REDDEDİLİR")
        except Exception as e:  # noqa: BLE001
            kontrol(False, "S1/S2 tek-kaynak çapaları", f"{type(e).__name__}: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for ok, _ in SONUC if ok)
    for ok, ad in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    print(f"\ngitignore_tam_satir: {gecen}/{len(SONUC)}")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    raise SystemExit(main())
