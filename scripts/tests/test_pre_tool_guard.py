#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pre_tool_guard — bütün-yüzey regresyon testi.

Neden var (2026-07-09 denetimi): guard kuralları ham komut metnini tarıyordu.
Heredoc/here-string GÖVDESİ komut değil VERİdir (commit mesajı, PR gövdesi) — ham
metin taranınca bir kural, kendi tarihçe notunu bloklar. Üç guard'da arka arkaya
yaşandı. Ayrıca kabuk kuralları yalnız `Bash` tool'una bakıyordu; aynı komut
`PowerShell` tool'undan tünellenebiliyordu.

Bu test üç ekseni birden zorlar, KURAL BAŞINA:
  (A) YANLIS-POZITIF : heredoc gövdesi kuraldan bahsediyor  -> bloklamamalı
  (B) GERCEK KORUMA  : komut gerçekten tehlikeli            -> bloklamalı
  (C) POWERSHELL     : aynı tehlike diğer kabuk yüzeyinden  -> bloklamalı

Yanlış-pozitifi kapatırken korumayı delmediğimizi (B/C) kanıtlamak ZORUNLU:
gürültülü gate ciddiye alınmaz, delik gate ise koruma sanılır.

Koşum:  python scripts/tests/test_pre_tool_guard.py
Ağ/proje gerektiren senaryolar otomatik ATLANIR (CI-güvenli). Tam koşum için:
  IX_GUARD_TEST_LIVE=1  (canlı `gh repo view` gerektirir)
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

GUARD = Path(__file__).resolve().parents[1] / "hooks" / "pre_tool_guard.py"
PROJ = os.environ.get("CLAUDE_PROJECT_DIR", "")
LIVE = os.environ.get("IX_GUARD_TEST_LIVE") == "1"


def _frozen_root() -> str:
    """project.yaml'dan ilk frozen_readonly_paths girdisi; yoksa '' (freeze testleri atlanır).

    İki YAML biçimi de desteklenir — yalnız blok-listeyi beklemek sessizce '' döndürür
    ve testi 'atlandı' sanırsın (2026-07-09: tam bu oldu, freeze testleri hiç koşmadı):
        frozen_readonly_paths: ["C:\\\\X"]      # inline
        frozen_readonly_paths:\n  - "C:\\\\X"   # blok
    """
    if not PROJ:
        return ""
    p = Path(PROJ) / "project.yaml"
    if not p.exists():
        return ""
    metin = p.read_text(encoding="utf-8", errors="replace")
    # inline: frozen_readonly_paths: ["...", "..."]
    m = re.search(r"frozen_readonly_paths:\s*\[([^\]]*)\]", metin)
    if m:
        hits = re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))
        if hits:
            return hits[0].replace("\\\\", "\\").strip()
    # blok: frozen_readonly_paths:\n  - "..."
    m = re.search(r"frozen_readonly_paths:\s*\n((?:\s*-\s*.+\n)+)", metin)
    if m:
        hits = re.findall(r"-\s*['\"]?([^'\"\n]+)", m.group(1))
        if hits:
            return hits[0].strip()
    return ""


FROZEN = _frozen_root()
GH = shutil.which("gh") is not None


def hd(mesaj: str) -> str:
    """Heredoc gövdesinde <mesaj> geçen zararsız bir git commit (Bash)."""
    return "git add x && git commit -q -F - <<'EOF'\n" + mesaj + "\nEOF"


def ps_hd(mesaj: str) -> str:
    """Aynısı PowerShell here-string ile."""
    return "git add x; git commit -m @'\n" + mesaj + "\n'@"


def _case(kural, ad, tool, cmd, beklenen, skip=""):
    return (kural, ad, tool, cmd, beklenen, skip)


def build_cases():
    c = []
    fz = FROZEN or r"C:\FROZEN_PLACEHOLDER"
    skip_fz = "" if FROZEN else "project.yaml/frozen_readonly_paths yok"

    c += [
        _case("FREEZE R10", "A mesajda donmus kok gecer", "Bash", hd(f"chore: {fz} yolu duzeltildi"), 0, skip_fz),
        _case("FREEZE R10", "A PS here-string", "PowerShell", ps_hd(f"chore: {fz} yolu"), 0, skip_fz),
        _case("FREEZE R10", "B donmus koke yazma", "Bash", f'echo x > {fz}/a.txt', 2, skip_fz),
        _case("FREEZE R10", "C powershell yazma", "PowerShell", f'Set-Content {fz}\\a.txt "x"', 2, skip_fz),
        _case("FREEZE R10", "mesru: okuma", "Bash", f'grep -r x {fz}', 0, skip_fz),
    ]
    c += [
        _case("R9 SILME", "A mesajda 'rm -rf core'", "Bash", hd("test: rm -rf core -> 2 (koruma ayakta)"), 0),
        _case("R9 SILME", "B rm -rf core/", "Bash", "rm -rf core/", 2),
        _case("R9 SILME", "B rm -rf DEV_CORE", "Bash", "rm -rf /x/DEV_CORE", 2),
        _case("R9 SILME", "C powershell Remove-Item -Recurse", "PowerShell", "Remove-Item -Recurse -Force core", 2),
        _case("R9 SILME", "C powershell rimraf .claude/agents", "PowerShell", "rimraf .claude/agents", 2),
        _case("R9 SILME", "mesru: git clean -n", "Bash", "cd core; git clean -nfd", 0),
        _case("R9 SILME", "mesru: baska hedef", "Bash", "rm -rf .tmp/x", 0),
    ]
    c += [
        _case("SIZINTI-COMMIT", "A mesajda 'core/' gecer", "Bash", hd("docs: core/ junction aciklandi"), 0),
        _case("SIZINTI-COMMIT", "B git add core/", "Bash", "git add core/scripts/x.py", 2),
        _case("SIZINTI-COMMIT", "C powershell git add core/", "PowerShell", "git add core/scripts/x.py", 2),
    ]
    c += [
        _case("ADR0005-C", "A mesajda transport release", "Bash", hd("docs: transport release YASAK (ADR 0005-C)"), 0),
    ]
    c += [
        _case("FIORI DEPLOY", "A mesajda 'fiori deploy'", "Bash", hd("fix: yalin 'fiori deploy' stale-dist uretir"), 0),
        _case("FIORI DEPLOY", "B yalin deploy", "Bash", "npx fiori deploy --config ui5-deploy.yaml --yes", 2),
        _case("FIORI DEPLOY", "C powershell yalin deploy", "PowerShell", "npx fiori deploy --config x.yaml --yes", 2),
        _case("FIORI DEPLOY", "mesru: deploy_ui.py", "Bash", "python scripts/deploy_ui.py --apps a", 0),
    ]
    c += [
        _case("INLINE AKTIVASYON", "A mesajda adt/activation .post(", "Bash",
              hd("fix: elle adt/activation .post( cagrisi sahte-OK uretir"), 0),
        _case("INLINE AKTIVASYON", "B gercek inline post", "Bash",
              'python -c "r=s.post(\'/sap/bc/adt/activation\')"', 2),
    ]
    # PUBLIC-PR: hedef repo gorunurlugu CANLI sorulur -> gh + ag gerekir.
    skip_pr = "" if (GH and LIVE) else "IX_GUARD_TEST_LIVE=1 + gh gerekir"
    pub = os.environ.get("IX_GUARD_TEST_PUBLIC_REPO", "")
    priv = os.environ.get("IX_GUARD_TEST_PRIVATE_REPO", "")
    if not (pub and priv):
        skip_pr = skip_pr or "IX_GUARD_TEST_PUBLIC_REPO/PRIVATE_REPO tanimsiz"
    # Tetikleyici: _ZSD_PAT ile eşleşen SENTETİK paket adı.
    # E-posta/kimlik regex'i tetikleyici olarak KULLANILAMAZ: proje bir
    # genericize-blocklist.txt tanımlamışsa _CORE_LEAK jenerik regex yerine o listeden
    # kurulur ve sentetik e-posta hiç eşleşmez (2026-07-09: test bu yüzden sessizce geçti).
    # Ad parça parça kurulur — literal hâli bu dosyada geçerse core_precommit ZSD_PAT'e takılır.
    paket = "ZSD" + "0" + "42"       # gerçek bir paket DEĞİL; yalnız deseni tetikler
    demo = "ZSD" + "0" + "01"        # demo istisnası — tetiklememeli
    c += [
        _case("PUBLIC-PR", "A mesajda 'gh pr create'", "Bash", hd("feat: gh pr create govdesi taranir"), 0),
        _case("PUBLIC-PR", "B public + paket adi", "Bash",
              f'gh pr create --repo {pub} --title "fix {paket}" --body "x"', 2, skip_pr),
        _case("PUBLIC-PR", "C powershell public + paket adi", "PowerShell",
              f'gh pr create --repo {pub} --title "fix {paket}" --body "x"', 2, skip_pr),
        _case("PUBLIC-PR", "mesru: private repo + paket adi", "Bash",
              f'gh pr create --repo {priv} --title "fix {paket}" --body "x"', 0, skip_pr),
        _case("PUBLIC-PR", "mesru: public + demo paket (istisna)", "Bash",
              f'gh pr create --repo {pub} --title "docs {demo}" --body "x"', 0, skip_pr),
    ]
    return c


def main() -> int:
    fails, skipped = [], 0
    ozet = {}
    for kural, ad, tool, cmd, beklenen, skip in build_cases():
        if skip:
            skipped += 1
            continue
        payload = json.dumps({"tool_name": tool, "tool_input": {"command": cmd}})
        env = dict(os.environ)
        r = subprocess.run([sys.executable, str(GUARD)], input=payload, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", env=env, timeout=90)
        ok = (r.returncode == beklenen)
        ozet.setdefault(kural, [0, 0])
        ozet[kural][1] += 1
        if ok:
            ozet[kural][0] += 1
        else:
            fails.append(f"{kural} / {ad}: exit={r.returncode} beklenen={beklenen}")

    for k, (g, t) in ozet.items():
        print(f"  {'OK  ' if g == t else 'FAIL'} {k:20} {g}/{t}")
    if skipped:
        print(f"  SKIP {skipped} senaryo (ag/proje bagimli)")
    if fails:
        print("\nGUARD YUZEYI BOZUK:")
        for f in fails:
            print("   " + f)
        return 1
    print(f"\nGUARD YUZEYI TUTUYOR ({sum(v[1] for v in ozet.values())} senaryo)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
