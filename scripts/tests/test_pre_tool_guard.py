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

# Windows konsolu cp1252'dir: Türkçe karakterli çıktı UnicodeEncodeError ile ÇÖKER ve
# test "hata" gibi görünür (2026-07-09: CI'da fark edilmezdi, yerelde çöktü).
for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

GUARD = Path(__file__).resolve().parents[1] / "hooks" / "pre_tool_guard.py"
PROJ = os.environ.get("CLAUDE_PROJECT_DIR", "")
LIVE = os.environ.get("IX_GUARD_TEST_LIVE") == "1"


def _fixture_proje() -> tuple:
    """FREEZE testleri için KENDİ proje fixture'ını kurar → (proje_dizini, donmus_kok).

    Eskiden gerçek `project.yaml`'a bağlıydı; CI'da `CLAUDE_PROJECT_DIR` yok diye FREEZE'in
    5 senaryosunun TAMAMI sessizce SKIP oluyordu — üstelik ekrana "GUARD YUZEYI TUTUYOR"
    yazıp exit 0 veriyordu (2026-07-09 denetimi). En çok yanlış-pozitif üreten kural,
    hiç test edilmiyordu. Fixture ile bağımlılık kalkar: senaryolar HER ORTAMDA koşar.
    """
    import tempfile
    d = Path(tempfile.mkdtemp(prefix="ix_guard_fixture_"))
    kok = "C:" + chr(92) + "IX_FROZEN_TEST"
    (d / "project.yaml").write_text(
        'frozen_readonly_paths: ["' + kok.replace(chr(92), chr(92) * 2) + '"]\n',
        encoding="utf-8")
    return d, kok.replace(chr(92), "/")


FIXTURE_PROJE, FROZEN = _fixture_proje()   # freeze senaryoları artık HER ORTAMDA koşar
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
    fz = FROZEN
    skip_fz = ""     # fixture sayesinde koşulsuz

    c += [
        _case("FREEZE R10", "A mesajda donmus kok gecer", "Bash", hd(f"chore: {fz} yolu duzeltildi"), 0, skip_fz),
        _case("FREEZE R10", "A PS here-string", "PowerShell", ps_hd(f"chore: {fz} yolu"), 0, skip_fz),
        _case("FREEZE R10", "B donmus koke yazma", "Bash", f'echo x > {fz}/a.txt', 2, skip_fz),
        _case("FREEZE R10", "C powershell yazma", "PowerShell", f'Set-Content {fz}/a.txt "x"', 2, skip_fz),
        _case("FREEZE R10", "mesru: okuma", "Bash", f'grep -r x {fz}', 0, skip_fz),
        # Denetimde yakalanan iki yön (2026-07-09): salt-okuma bloklanıyordu, gerçek yazma geçiyordu
        _case("FREEZE R10", "mesru: okuma + 2>&1 redirect", "Bash", f'ls {fz} 2>&1', 0, skip_fz),
        _case("FREEZE R10", "mesru: kaynak kopyalama", "Bash", f'cp {fz}/x.abap ./y', 0, skip_fz),
        _case("FREEZE R10", "B python ile yazma", "Bash", f'python -c "open(\'{fz}/x\',\'w\')"', 2, skip_fz),
        _case("FREEZE R10", "B tar -C donmus kok", "Bash", f'tar -xzf y.tgz -C {fz}', 2, skip_fz),
        _case("FREEZE R10", "mesru: tar listeleme", "Bash", f'tar -tzf {fz}/a.tgz', 0, skip_fz),
        _case("FREEZE R10", "mesru: prefix cakismasi", "Bash", f'rm -rf {fz}_YENI/tmp', 0, skip_fz),
        _case("FREEZE R10", "B NotebookEdit (notebook_path)", "NotebookEdit", None, 2, skip_fz),
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


def test_zsd_pat_tek_dogruluk_kaynagi() -> str:
    """`_ZSD_PAT` iki dosyada ayrı tanımlı — AYNI kalmalarını bu test zorlar.

    core_precommit COMMIT içeriğini, pre_tool_guard PR gövdesini tarar. Desenler
    ayrışırsa commit'te yakalanan bir iz PR gövdesinden kaçar (ya da tersi). Yorumla
    "bilerek aynı" demek yetmez — hiçbir şey aynı kalmalarını zorlamıyordu.
    """
    kok = Path(__file__).resolve().parents[1]
    def _desen(dosya: str, ad: str) -> str:
        metin = (kok / dosya).read_text(encoding="utf-8", errors="replace")
        m = re.search(rf"{ad}\s*=\s*re\.compile\(\s*r?(['\"])(.+?)\1", metin)
        return m.group(2) if m else ""
    a = _desen("git-hooks/core_precommit.py", "ZSD_PAT")
    b = _desen("hooks/pre_tool_guard.py", "_ZSD_PAT")
    if not a or not b:
        return "ZSD_PAT desenlerinden biri okunamadi (yeniden adlandirilmis olabilir)"
    if a != b:
        return f"ZSD_PAT DRIFT: core_precommit={a!r} != pre_tool_guard={b!r}"
    return ""


def test_blocklist_jenerigi_EZMEZ() -> str:
    """Proje blocklist'i jenerik yapısal desenleri düşürmemeli (birleşim).

    Eski davranış "ilk bulunan kazanır"dı: blocklist tanımlayan proje, makine-lokal
    kullanıcı yolu ve e-posta korumasını SESSİZCE kaybediyordu. Daha fazla yapılandırma
    = daha az koruma. Bu test o gerilemeyi yakalar.
    """
    # Guard'ı in-process import ETME: modül düzeyinde stdout/stderr sarmalar, reload
    # onları kapatır ("lost sys.stderr"). Diğer senaryolar gibi subprocess ile sür.
    #
    # Sızıntı dizgeleri PARÇA PARÇA kurulur: literal hâlleri bu dosyada geçerse guard'ın
    # kendi core-yazım taraması bu test dosyasını reddeder (denendi, reddetti — doğru
    # davranış). Test, koruduğu şeyin kurbanı olmamalı.
    kul_yolu = "C:" + "\\Users\\" + "gercekkisi" + "\\gizli"
    ph_yolu = "C:" + "\\Users\\" + "<USER>" + "\\x"
    gercek_eposta = "birisi" + "@" + "sirket.com.tr"
    ornek_eposta = "user" + "@" + "example.com"

    core_dosya = str(GUARD.resolve().parents[2] / "scripts" / "_leak_probe.py")
    kontroller = [
        (kul_yolu, 2, "makine-lokal kullanici yolu"),
        (gercek_eposta, 2, "gercek e-posta"),
        ("AcmeCorp", 2, "blocklist token'i"),
        (ph_yolu, 0, "placeholder yol (muaf olmali)"),
        (ornek_eposta, 0, "RFC 2606 ornek domain (muaf olmali)"),
    ]
    env = dict(os.environ, IX_GENERICIZE_BLOCKLIST="AcmeCorp,WIDGET01")
    for icerik, beklenen, ad in kontroller:
        payload = json.dumps({"tool_name": "Write",
                              "tool_input": {"file_path": core_dosya, "content": icerik}})
        r = subprocess.run([sys.executable, str(GUARD)], input=payload, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", env=env, timeout=60)
        if r.returncode != beklenen:
            return (f"{ad}: exit={r.returncode} beklenen={beklenen} "
                    f"({'yakalanmaliydi' if beklenen == 2 else 'muaf olmaliydi'})")
    return ""


def main() -> int:
    fails, skipped = [], 0
    ozet = {}

    birlesim = test_blocklist_jenerigi_EZMEZ()
    ozet["LEAK BIRLESIMI"] = [0 if birlesim else 1, 1]
    if birlesim:
        fails.append("LEAK BIRLESIMI / " + birlesim)

    drift = test_zsd_pat_tek_dogruluk_kaynagi()
    ozet["ZSD_PAT DRIFT"] = [0 if drift else 1, 1]
    if drift:
        fails.append("ZSD_PAT / " + drift)
    atlananlar = []
    for kural, ad, tool, cmd, beklenen, skip in build_cases():
        if skip:
            skipped += 1
            atlananlar.append(f"{kural} / {ad} ({skip})")
            continue
        if tool == "NotebookEdit":
            ti = {"notebook_path": FROZEN + "/x.ipynb", "new_source": "a"}
        else:
            ti = {"command": cmd}
        payload = json.dumps({"tool_name": tool, "tool_input": ti})
        env = dict(os.environ)
        if kural.startswith("FREEZE"):
            env["CLAUDE_PROJECT_DIR"] = str(FIXTURE_PROJE)   # fixture: her ortamda koşsun
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
        # SESSİZ ATLAMA YASAK: eskiden "SKIP 9" yazıp "GUARD YUZEYI TUTUYOR" diyordu ve
        # exit 0 veriyordu — atlananların 5'i FREEZE'in TAMAMI idi (2026-07-09 denetimi).
        print(f"  SKIP {skipped} senaryo — ATLANANLAR (yeşil ışık DEĞİL):")
        for a in atlananlar:
            print(f"       - {a}")
    print("\n⚠ BU TEST GUARD'I DOĞRUDAN ÇAĞIRIR — KABLOLAMAYI (settings.json PreToolUse\n"
          "  matcher'ı) TEST ETMEZ. 'C powershell' senaryoları guard KODUNUN o tool'u\n"
          "  tanıdığını gösterir, üretimde hook'un tetiklendiğini DEĞİL. Kablolama gate'i:\n"
          "  `python core/scripts/ix_doctor.py` → 'kablolama' satırı.")
    if fails:
        print("\nGUARD YUZEYI BOZUK:")
        for f in fails:
            print("   " + f)
        return 1
    print(f"\nGUARD YUZEYI TUTUYOR ({sum(v[1] for v in ozet.values())} senaryo)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
