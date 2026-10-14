#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pre_tool_guard commit-mesaji gate'i — AJAN IMZA ayiklamasinin DARLIGI (2026-10-12).

NEDEN BU KORPUS VAR
-------------------
`pre_tool_guard._git_imza_satirlari_ayikla` eskiden `Co-Authored-By|Claude-Session|
Signed-off-by|Reviewed-by|Cc` anahtarli HER satiri (ve "Generated with" ile baslayan her
uretici satirini) adresten bagimsiz TARAMADAN DUSURUYORDU. Sonuc: public cekirdege giden
bir commit mesajinda baska bir kisinin e-postasini tasiyan trailer sizinti taramasindan
SESSIZCE geciyordu. Kardes `core_precommit._ATIF_SATIRI` ayni gun daraltilmisti; guard
geride kalmisti. Artik iki taraf da TEK KAYNAKTAN beslenir (`genericize_common`).

BOLUMLER
  P  pozitif: ajan DISI trailer'daki e-posta GERCEK tarayiciyla BLOKLANIR (exit 2 + imza)
  N  negatif/kontrol: yalniz ajan atif + oturum + uretici satiri olan mesru commit /
     PR govdesi GECER (exit 0)
  K  kontrol: (K1) muaf satir GERCEK tarayiciya tek basina TAKILIR — yani N vektorleri
     muafiyete BAGLIDIR, bos-yesil degildir · (K2) tek kaynak: guard kendi trailer desenini
     TASIMAZ, core_precommit `_ATIF_SATIRI`'yi genericize_common'dan alir (AST)
  3. BAGLAM: PowerShell yuzeyi + `-F <dosya>` + CRLF satir sonlu mesaj dosyasi
  bug-gate 2026-10-14:
  P11-P12  son capalar (atif / oturum satiri + SONDA e-posta)
  P13 · N9 atif satirinin AD bolumu taranir (yalniz uretici adresi maskelenir) + olculen
           mesru ad bicimleri gecer
  P14-P17c Claude Code'un varsayilan commit bicimi `-m "$(cat <<'EOF' … EOF)"` (tirnakli /
           tirnaksiz sinirlayici, `<<-` + TAB kapanis, tirnaksiz ikame, PowerShell here-string)
           — govde GERCEKTEN taranmali (FAIL-CLOSED ile bloklamak bu vektoru gecirmez)
  P18-P20 · N8  ayni sinif PR / issue / release govdesi (PUBLIC-PR gate'i)
  N7       mesru `$(cat)` commit'i · F1-F3 cozulemeyen ikame FAIL-CLOSED · K3 `-F -` eski yol
  bug-gate turu 3 (2026-10-14):
  P21      `gh api … -f body="$(cat <<-EOF … \tEOF)"` govdesi yer tutucu acilimiyla taranir (G3)
  P22-P25  ilk `EOF` satirindan sonra `)` gelmeyen `$(cat)` sonraki segmentleri YUTMAZ (G1)
  N10-N12 · P26  kullanicinin yazdigi literal isaret / `-m '$'` ikame sayilmaz, taranir (G2)
  F4-F5    tirnaksiz `$(` ve literal isaretin yaninda gercek ikame FAIL-CLOSED kalir (G2 siniri)
  bug-gate turu 4 (2026-10-14):
  F6-F11 · N13-N14  BITISIK kisa bayrak `-m$(…)` / `-am$(…)` / `-qam$(…)` / PS `-m$(Get-Content)`
           / `-m$((…))` FAIL-CLOSED (ikame sebebiyle); bitisik TIRNAKLI `-m"$"` / `-am'$'` gecer (G4-1)
  Gorunurluk mock'u: `cd /c/private-proj` baglamli segment PRIVATE, gerisi PUBLIC.

Gorunurluk sorgusu (`gh repo view`) SABITLENIR (public) — ag yok; tarayici GERCEKTIR.
Guard ve genericize_common GECICI dizine kopyalanir; mutasyon yalniz kopyaya uygulanir.

⚠ ORNEK DIZGELER LITERAL YAZILMAZ: bu dosya da tarayici tarafindan taranir; e-posta
adresleri PARCADAN kurulur.

KOSUM:  python tests/fixtures/git_imza_ayiklama_dar/run.py [--mutasyon-<kip>]
Cikis:  0 hepsi beklendigi gibi · 1 sapma · 2 DOGRULANAMADI (capa tutmadi / mutant bozuk)
"""
from __future__ import annotations

import ast
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
SCRIPTS = REPO / "scripts"

# Eski (genis) desen — mutasyon "eski koda don" bunu birebir geri koyar.
_ESKI_DESEN = (r're.match(r"^[ \t]*(?:Co-Authored-By|Claude-Session|Signed-off-by|'
               r'Reviewed-by|Cc)[ \t]*:.*$|^[ \t]*\U0001F916[ \t]*Generated with .*$", '
               r's, re.IGNORECASE)')

# kip -> (hedef, eski, yeni) — YALNIZ sandbox kopyasina uygulanir
MUTLAR = {
    # Eski koda donus: trailer anahtari adresten bagimsiz duser => P vektorleri KACAR.
    "--mutasyon-eski-desen": ("ptg", "AJAN_IMZA_SATIRI.match(s)", _ESKI_DESEN),
    # Muafiyet tumden kalkar => ajan atif satiri (noreply adresi) bloklanir => N1-N3,N5-N8.
    # (F3'ten beri atif satiri ayri dalda maskelenir ⇒ mutasyon fonksiyonun BASINDA keser.)
    "--mutasyon-muafiyet-yok": ("ptg", "def _git_imza_satiri(s: str) -> str:\n",
                                "def _git_imza_satiri(s: str) -> str:\n    return s\n"),
    # ── bug-gate 2026-10-14 ───────────────────────────────────────────────────
    # F1: AJAN_IMZA_SATIRI son capasi kalkar => satir ONEKI eslesir, sondaki e-posta
    # satirla birlikte bosalir => P11 (atif + sonda e-posta) · P12 (oturum + sonda e-posta).
    "--mutasyon-son-capa-yok": ("gc", '+ r")\\s*$",', '+ r")",'),
    # F3: atif satiri yeniden tumden BOSALTILIR => ad bolumundeki obje adi gecer => P13.
    "--mutasyon-atif-bosalt": ("ptg", 'return ATIF_ADRES_PAT.sub("", s, count=1)',
                               'return ""'),
    # P-1: commit mesaji yeniden KIRPILMIS komuttan okunur => P14-P17.
    "--mutasyon-kirpik-komut": (
        "ptg", "commit_komutu, govdeler = _ikame_cozumlu_komut(ham) if ham else (komut, [])",
        "commit_komutu, govdeler = komut, []"),
    # P-1 kardesi: PR/issue/release govdesi yeniden kirpilmis komuttan okunur => P18-P20.
    "--mutasyon-pr-kirpik-komut": (
        "ptg", "yayin_komutu, govdeler = _ikame_cozumlu_komut(ham) if ham else (komut, [])",
        "yayin_komutu, govdeler = komut, []"),
    # Cozulemeyen ikame sessizce gecer (fail-OPEN) => F1-F5 (fail-closed vektorleri).
    "--mutasyon-cozulemez-gecer": (
        "ptg", 'if any(i in v for i in _KIRPIK_ISARET) or (v.strip() == "$" and ciplak_ikame):',
        "if False:"),
    # ── bug-gate turu 3 (2026-10-14) ──────────────────────────────────────────
    # G1: `_CAT_HEREDOC` govdesi yeniden TEMPERLENMEMIS `(.*?)` olur => ilk `EOF` satirindan
    # sonra `)` gelmeyen aralik bir SONRAKI `EOF\n)`'e uzar, aradaki segmentler yer tutucuya
    # gomulur => P22-P25 (olculmus GEVSETME; ara durumdaki kod tam olarak buydu).
    "--mutasyon-cat-heredoc-genis": (
        "ptg", 'r"((?:(?!^(?(1)\\t*)\\3$).)*?)^(?(1)\\t*)\\3$\\s*\\)",',
        'r"(.*?)^(?(1)\\t*)\\3$\\s*\\)",'),
    # G3: `gh api` dalinda yer tutucu govdesiyle ACILMAZ => `<<-EOF` + TAB kapanisli govde
    # (`_HEREDOC` o bicimi tanimaz) hic taranmaz => P21.
    "--mutasyon-gh-api-yer-tutucu-acilmaz": (
        "ptg", "acik = _literal_geri(_CAT_YER_RX.sub(", "acik = komut or _literal_geri(_CAT_YER_RX.sub("),
    # G2: literal isaret kacisi kalkar => kullanicinin yazdigi `<HEREDOC-STRIPPED>` yeniden
    # ikame isareti sayilir => N10/N11 (FAIL-CLOSED'a duser).
    "--mutasyon-literal-kacis-yok": (
        "ptg", "_CAT_HEREDOC.sub(lambda m: _yer(m.group(4)), _literal_kac(ham or \"\"))",
        "_CAT_HEREDOC.sub(lambda m: _yer(m.group(4)), (ham or \"\"))"),
    # G2: cıplak `$` her bicimde ikame sayilir (eski genislik) => N12 `-m '$'`.
    "--mutasyon-ciplak-dolar-genis": (
        "ptg", "ciplak_ikame = seg is None or bool(_CIPLAK_DOLAR_SONU.search(seg))",
        "ciplak_ikame = True"),
    # G2 daraltmasinin ters yonu: tirnaksiz `$(` ikamesi de literal sayilir => F4 + F6-F11.
    "--mutasyon-ciplak-dolar-dar": (
        "ptg", "ciplak_ikame = seg is None or bool(_CIPLAK_DOLAR_SONU.search(seg))",
        "ciplak_ikame = False"),
    # ── bug-gate turu 4 (2026-10-14) ──────────────────────────────────────────
    # G4-1: `b37751f` deseni geri gelir (`[\s=]` onkosulu) => bitisik `-m$(…)` F6-F11 gecer.
    "--mutasyon-ciplak-dolar-bitisik": (
        "ptg", '_CIPLAK_DOLAR_SONU = re.compile(r"\\$\\s*$")',
        '_CIPLAK_DOLAR_SONU = re.compile(r"(?:^|[\\s=])\\$\\s*$")'),
    # Oturum satiri genisler => URL'ye saklanan e-posta muaf olur => P7.
    "--mutasyon-oturum-genis": ("gc", "session_[A-Za-z0-9]+", r"\S*"),
    # Uretici satiri genisler => baglantiya saklanan e-posta muaf olur => P8.
    "--mutasyon-uretici-genis": ("gc", r"\(https://claude\.(?:com/claude-code|ai/code)\)",
                                 r"\(.*\)"),
    # Tek kaynak bozulur: core_precommit kendi (genis) desenini tasir => K2b.
    "--mutasyon-kopya-desen": ("pc", "_ATIF_SATIRI = ATIF_SATIRI",
                               '_ATIF_SATIRI = re.compile(r"^\\s*Co-Authored-By:.*$", '
                               're.IGNORECASE)'),
}

EPOSTA = "birisi" + "@" + "ornek-firma.com.tr"
NOREPLY = "noreply" + "@" + "anthropic.com"
ATIF = "Co-Authored-By: Claude Opus 5.5 (1M context) <" + NOREPLY + ">"
ATIF_KUCUK = "Co-authored-by: Claude Opus 5 <" + NOREPLY + ">"     # GitHub yazimi
OTURUM = "Claude-Session: https://claude.ai/code/session_01AbCdEfGh"
URETICI = "\U0001F916 Generated with [Claude Code](https://claude.com/claude-code)"
Z_ADI = "Z" + "XY" + "022"                     # allowlist disi Z-obje adi (bloklayici sinif)
ISARET = "<HEREDOC-" + "STRIPPED>"             # normalizasyon isaretinin LITERAL yazimi

_SURUCU = r'''
import importlib.util, io, json, sys
guard, payload_yolu = sys.argv[1:3]
spec = importlib.util.spec_from_file_location("ptg_imza_dar", guard)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
# Gorunurluk sabit PUBLIC; yalniz `cd /c/private-proj` baglamli segment PRIVATE (G1 zincir
# vektorleri "once private commit, sonra public commit" bicimini ister — 2026-10-14).
m._repo_public_mu = lambda hay: ((False, "org/private-proj") if "private-proj" in (hay or "")
                                 else (True, "org/public-core"))
payload = open(payload_yolu, encoding="utf-8").read()
_err = io.StringIO()
_ge, _gi = sys.stderr, sys.stdin
sys.stderr, sys.stdin = _err, io.StringIO(payload)
try:
    rc = m.main()
finally:
    sys.stderr, sys.stdin = _ge, _gi
sys.stdout.write("<<SONUC>>" + json.dumps({"rc": rc, "err": _err.getvalue()}))
'''

IMZA = "COMMIT-MESAJI SIZINTI GATE"
SONUC: list[tuple[str, bool, str]] = []


def ekle(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(ok), detay))


def _sil(d: Path) -> None:
    """Q319: Windows'ta salt-okur girdi `rmtree(ignore_errors=True)` ile SESSIZCE kalir."""
    def _ac(func, path, _exc):                       # noqa: ANN001
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass
    kw = {"onexc": _ac} if sys.version_info >= (3, 12) else {"onerror": _ac}
    try:
        shutil.rmtree(d, **kw)                       # type: ignore[arg-type]
    except Exception:
        shutil.rmtree(d, ignore_errors=True)


def main() -> int:
    gecerli = set(MUTLAR)
    for a in sys.argv[1:]:
        if a.startswith("--mutasyon") and a not in gecerli:
            raise SystemExit(f"[KULLANIM] bilinmeyen mutasyon kipi: {a} -> gecerli: "
                             + " ".join(sorted(gecerli)))
    secili = next((a for a in sys.argv[1:] if a in gecerli), None)

    tmp = Path(tempfile.mkdtemp(prefix="imza_dar_"))
    try:
        kum = tmp / "kum"
        (kum / "scripts" / "hooks").mkdir(parents=True)
        (kum / "scripts" / "git-hooks").mkdir(parents=True)
        shutil.copy2(SCRIPTS / "genericize_common.py", kum / "scripts")
        shutil.copy2(SCRIPTS / "hooks" / "pre_tool_guard.py", kum / "scripts" / "hooks")
        shutil.copy2(SCRIPTS / "git-hooks" / "core_precommit.py",
                     kum / "scripts" / "git-hooks")
        hedefler = {"gc": kum / "scripts" / "genericize_common.py",
                    "ptg": kum / "scripts" / "hooks" / "pre_tool_guard.py",
                    "pc": kum / "scripts" / "git-hooks" / "core_precommit.py"}
        if secili:
            h, eski, yeni = MUTLAR[secili]
            hedef = hedefler[h]
            kaynak = hedef.read_bytes().decode("utf-8").replace("\r\n", "\n")
            if kaynak.count(eski) != 1:
                print(f"[DOGRULANAMADI] mutasyon capasi {kaynak.count(eski)} kez bulundu "
                      f"({secili}) -> mutasyon UYGULANMADI; 'gecti' sonucu ANLAMSIZ olurdu.")
                return 2
            hedef.write_bytes(kaynak.replace(eski, yeni, 1).encode("utf-8"))
            try:
                compile(hedef.read_text(encoding="utf-8"), str(hedef), "exec")
            except SyntaxError as e:
                print(f"[DOGRULANAMADI] mutant SOZDIZIMI BOZUK ({secili}): {e}")
                return 2

        calisma = tmp / "calisma"                  # guard cwd'si: proje koku DEGIL
        calisma.mkdir()
        env = dict(os.environ)
        for k in ("CLAUDE_PROJECT_DIR", "IX_GENERICIZE_BLOCKLIST"):
            env.pop(k, None)
        sayac = [0]

        def guard(tool: str, komut: str) -> tuple:
            sayac[0] += 1
            p = tmp / f"payload_{sayac[0]}.json"
            p.write_text(json.dumps({"tool_name": tool, "tool_input": {"command": komut}},
                                    ensure_ascii=False), encoding="utf-8")
            r = subprocess.run([sys.executable, "-", str(hedefler["ptg"]), str(p)],
                               input=_SURUCU, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=120,
                               env=env, cwd=str(calisma))
            if "<<SONUC>>" not in (r.stdout or ""):
                return None, (r.stderr or r.stdout or "")[-300:]
            d = json.loads(r.stdout.split("<<SONUC>>", 1)[1])
            return d["rc"], d["err"]

        def heredoc(govde: str) -> str:
            return "cd /c/core && git commit -q -F - <<'EOF'\n" + govde + "\nEOF"

        def blok(ad: str, tool: str, komut: str) -> None:
            rc, err = guard(tool, komut)
            ekle(ad + " -> BLOKLANIR (exit 2 + imza)",
                 rc == 2 and IMZA in (err or ""),
                 f"rc={rc} err={(err or '')[-200:]!r}")

        def gecer(ad: str, tool: str, komut: str) -> None:
            rc, err = guard(tool, komut)
            ekle(ad + " -> GECER (exit 0)", rc == 0,
                 f"rc={rc} err={(err or '')[-200:]!r}")

        baslik = "fix(tooling): readback esitligi\n\n"

        # ── P: POZITIF — ajan DISI trailer TARANIR ─────────────────────────────
        blok("P1 Signed-off-by baska adres", "Bash",
             heredoc(baslik + ATIF + "\nSigned-off-by: Biri <" + EPOSTA + ">"))
        blok("P2 Reviewed-by baska adres", "Bash",
             heredoc(baslik + "Reviewed-by: Biri <" + EPOSTA + ">\n" + ATIF))
        blok("P3 Cc baska adres", "Bash", heredoc(baslik + "Cc: " + EPOSTA))
        blok("P4 insan co-author (GitHub yazimi)", "Bash",
             heredoc(baslik + "Co-authored-by: Biri <" + EPOSTA + ">"))
        blok("P5 ad Claude ama adres BASKA", "Bash",
             heredoc(baslik + "Co-Authored-By: Claude Opus <" + EPOSTA + ">"))
        blok("P6 ad-adres arasina saklanan e-posta", "Bash",
             heredoc(baslik + "Co-Authored-By: Claude " + EPOSTA + " <" + NOREPLY + ">"))
        blok("P7 oturum satirina saklanan e-posta", "Bash",
             heredoc(baslik + "Claude-Session: https://claude.ai/code/x?u=" + EPOSTA))
        blok("P8 uretici satirina saklanan e-posta", "Bash",
             heredoc(baslik + "\U0001F916 Generated with [Claude Code](mailto:" + EPOSTA + ")"))
        blok("P9 -m bicimi (ayri cikarim yolu)", "Bash",
             "cd /c/core && git commit -m 'baslik' -m 'Signed-off-by: Biri <"
             + EPOSTA + ">'")

        # ── N: NEGATIF / KONTROL — mesru ajan commit'i ve PR govdesi ──────────
        gecer("N1 ajan atif + oturum satiri", "Bash",
              heredoc(baslik + ATIF + "\n" + OTURUM))
        gecer("N2 GitHub yazimli atif + uretici satiri", "Bash",
              heredoc(baslik + URETICI + "\n\n" + ATIF_KUCUK))
        gecer("N3 -m bicimi + atif", "Bash",
              "cd /c/core && git commit -m 'baslik' -m '" + ATIF + "'")
        gecer("N4 PR govdesi (uretici satiri) — gh yayin yolu", "Bash",
              "gh pr create --repo org/public-core --title 'fix: x' --body-file - <<'B'\n"
              "## Ozet\njenerik\n\n" + URETICI + "\nB")

        # ── 3. BAGLAM: PowerShell + `-F <dosya>` + CRLF mesaj dosyasi ─────────
        kirli = tmp / "kirli_crlf.txt"
        kirli.write_bytes((baslik + ATIF + "\nSigned-off-by: Biri <" + EPOSTA + ">\n")
                          .replace("\n", "\r\n").encode("utf-8"))
        temiz = tmp / "temiz_crlf.txt"
        temiz.write_bytes((baslik + ATIF + "\n" + OTURUM + "\n")
                          .replace("\n", "\r\n").encode("utf-8"))
        kp, tp = str(kirli).replace("\\", "/"), str(temiz).replace("\\", "/")
        blok("P10 3.BAGLAM PowerShell + -F CRLF dosya + Signed-off-by", "PowerShell",
             "git -C /c/core commit -F " + kp)
        gecer("N5 3.BAGLAM PowerShell + -F CRLF dosya + yalniz ajan satirlari", "PowerShell",
              "git -C /c/core commit -F " + tp)
        gecer("N6 3.BAGLAM Bash + --file= CRLF dosya + yalniz ajan satirlari", "Bash",
              "cd /c/core && git commit --file=" + tp)

        # ── bug-gate 2026-10-14: F1 son capalar · F3 ad bolumu · P-1 $(cat) bicimi ──
        def cat_m(govde: str, ac: str = "<<'EOF'", kapa: str = "EOF") -> str:
            """Claude Code'un VARSAYILAN commit bicimi: -m "$(cat <<'EOF' … EOF\\n)"."""
            return ('cd /c/core && git commit -m "$(cat ' + ac + "\n" + govde + "\n"
                    + kapa + '\n)"')

        def blok_tarandi(ad: str, tool: str, komut: str, imza: str = IMZA) -> None:
            """Blok + govde GERCEKTEN tarandi (bulgu turu stderr'de). Yalniz imza yetmez:
            cozulemeyen ikame de FAIL-CLOSED ile ayni imzayla bloklar — o zaman govde
            hic okunmamistir ve vektor P-1'i olcmez (ilk kosumda `--mutasyon-kirpik-komut`
            P14-P17'yi bu yuzden DUSURMEDI)."""
            rc, err = guard(tool, komut)
            ekle(ad + " -> BLOKLANIR + govde TARANDI (kimlik izi)",
                 rc == 2 and imza in (err or "") and "kimlik izi" in (err or "")
                 and "FAIL-CLOSED" not in (err or ""),
                 f"rc={rc} err={(err or '')[-200:]!r}")

        def cat_pr(alt: str, bayrak: str, govde: str) -> str:
            # `issue comment` `--title` ALMAZ (gh 2.96.0) — geçersiz bayrak GH-HEDEF'te
            # "çözümlenemedi" bloğuna düşer (2026-10-14, bayrak tablosu); vektör gövde
            # taramasını ölçer, bu yüzden yalnız geçerli bayrak taşır.
            baslik = "" if alt.startswith("issue comment") else "--title 'fix: x' "
            return ("gh " + alt + " --repo org/public-core " + baslik + bayrak
                    + ' "$(cat <<\'EOF\'\n' + govde + '\nEOF\n)"')

        blok("P11 F1 atif satiri + SONDA e-posta (son capa)", "Bash",
             heredoc(baslik + ATIF + " " + EPOSTA))
        blok("P12 F1 oturum satiri + SONDA e-posta (son capa)", "Bash",
             heredoc(baslik + OTURUM + " " + EPOSTA))
        blok("P13 F3 atif satirinin AD bolumunde obje adi", "Bash",
             heredoc(baslik + "Co-Authored-By: Claude " + Z_ADI + " <" + NOREPLY + ">"))
        blok_tarandi("P14 P-1 $(cat <<'EOF') + Signed-off-by baska adres", "Bash",
             cat_m(baslik + ATIF + "\nSigned-off-by: Biri <" + EPOSTA + ">"))
        blok_tarandi("P15 P-1 $(cat <<'EOF') + govdede duz e-posta", "Bash",
             cat_m(baslik + "iletisim " + EPOSTA))
        blok_tarandi("P16 P-1 $(cat <<EOF) tirnaksiz sinirlayici", "Bash",
             cat_m(baslik + "Cc: " + EPOSTA, ac="<<EOF"))
        blok_tarandi("P17 P-1 $(cat <<-'EOF') + TAB girintili kapanis", "Bash",
             cat_m(baslik + "\tCc: " + EPOSTA, ac="<<-'EOF'", kapa="\tEOF"))
        blok_tarandi("P17b P-1 tirnaksiz ikame -m $(cat <<'EOF' …)", "Bash",
             "cd /c/core && git commit -m $(cat <<'EOF'\n" + EPOSTA + "\nEOF\n)")
        blok_tarandi("P17c P-1 3.BAGLAM PowerShell here-string -m @'…'@", "PowerShell",
             "git -C /c/core commit -m @'\n" + baslik + "Cc: " + EPOSTA + "\n'@")
        # PR/issue/release gövdesi — PUBLIC-PR gate'i aynı sınıf (lider kararı 2026-10-14).
        for ad_, alt_, bay_ in (("P18 pr create --body", "pr create", "--body"),
                                ("P19 issue comment -b", "issue comment 1", "-b"),
                                ("P20 release create --notes", "release create v1", "--notes")):
            blok_tarandi(ad_ + " $(cat) e-posta [PUBLIC-PR]", "Bash",
                         cat_pr(alt_, bay_, "## Ozet\niletisim " + EPOSTA),
                         imza="PUBLIC-PR SIZINTI GATE")
        gecer("N7 P-1 $(cat) + yalniz ajan atif + oturum satiri", "Bash",
              cat_m(baslik + ATIF + "\n" + OTURUM))
        gecer("N8 P-1 PR --body $(cat) + uretici satiri (mesru gunluk bicim)", "Bash",
              cat_pr("pr create", "--body", "## Ozet\njenerik\n\n" + URETICI))
        gecer("N9 F3 KONTROL: korpusta olculen 6 atif ad bicimi + Sonnet GECER", "Bash",
              heredoc(baslik + "\n".join(
                  "Co-Authored-By: Claude " + a + " <" + NOREPLY + ">"
                  for a in ("Opus 4.8 (1M context)", "Opus 5 (1M context)",
                            "Opus 5.5 (1M context)", "Fable 5", "Opus 4.7 (1M context)",
                            "Opus 5", "Sonnet 5"))))
        # Çözülemeyen ikame: gövde bilinemez ⇒ FAIL-CLOSED (sessiz geçiş DEĞİL).
        for ad_, kmt_ in (
                ("F1 -m $(sed … <<EOF) saf cat degil",
                 'cd /c/core && git commit -m "$(sed s/a/b/ <<\'EOF\'\ntemiz\nEOF\n)"'),
                ("F2 -m $(cat <<EOF | tr …) boru",
                 'cd /c/core && git commit -m "$(cat <<\'EOF\' | tr a b\ntemiz\nEOF\n)"'),
                ("F3 --body $(sed … <<EOF) PR",
                 "gh pr create --repo org/public-core --title x --body "
                 '"$(sed s/a/b/ <<\'EOF\'\ntemiz\nEOF\n)"'),
                # bug-gate turu 3 (G2 daraltmasinin GECIRMEMESI gerekenler):
                ("F4 tirnaksiz -m $(git log …) (ciplak `$` segment sonunda)",
                 "cd /c/core && git commit --amend -m $(git log -1 --format=%B)"),
                ("F5 $(sed) + BASKA -m'de literal isaret (isaret kacisi gercek ikameyi "
                 "maskelemez)",
                 'cd /c/core && git commit -m "$(sed s/a/b/ <<\'EOF\'\n' + EPOSTA
                 + "\nEOF\n)\" -m 'not: " + ISARET + "'")):
            rc_, err_ = guard("Bash", kmt_)
            ekle(ad_ + " -> FAIL-CLOSED (exit 2)",
                 rc_ == 2 and "FAIL-CLOSED" in (err_ or ""),
                 f"rc={rc_} err={(err_ or '')[-200:]!r}")
        blok("K3 KONTROL: -F - heredoc eski yol (degismedi)", "Bash",
             heredoc(baslik + "Cc: " + EPOSTA))

        # ── bug-gate turu 3 (2026-10-14) ──────────────────────────────────────
        # G3: `gh api` dalında yer tutucu GÖVDESİYLE açılır. `<<-EOF` + TAB kapanış seçildi,
        # çünkü `_HEREDOC` o biçimi tanımaz ⇒ gövdeyi yalnız yer tutucu açılımı taşır.
        blok_tarandi("P21 G3 gh api -f body=\"$(cat <<-EOF … \\tEOF)\" e-posta", "Bash",
                     "cd /c/core && gh api repos/org/public-core/pulls -f title=x -f body="
                     '"$(cat <<-EOF\n\tiletisim ' + EPOSTA + '\n\tEOF\n)"',
                     imza="PUBLIC-PR SIZINTI GATE")
        # G1: ilk `EOF` satırından sonra `)` gelmeyen aralık bir SONRAKİ `EOF\n)`'e uzamamalı
        # (bash heredoc'u ilk sınırlayıcı satırında bitirir). Ara durumdaki kodda dördü rc 0.
        eof_echo = "\"$(cat <<'EOF'\nok\nEOF\necho)\""
        blok_tarandi("P22 G1 private $(cat)EOF-echo ⇒ public -m e-posta ⇒ sonra $(cat)", "Bash",
                     "cd /c/private-proj && git commit -m " + eof_echo
                     + " && cd /c/core && git commit -m 'fix " + EPOSTA + "'"
                     + " && git commit --amend -m \"$(cat <<'EOF'\nx\nEOF\n)\"")
        blok_tarandi("P23 G1 public echo $(cat)EOF-echo ⇒ -m e-posta ⇒ git log $(cat)", "Bash",
                     "cd /c/core && echo " + eof_echo + " && git commit -m 'fix " + EPOSTA
                     + "' && git log -1 --format=\"$(cat <<'EOF'\n%B\nEOF\n)\"")
        blok_tarandi("P24 G1 PR: echo $(cat)EOF-echo ⇒ gh pr create --body e-posta", "Bash",
                     "echo " + eof_echo + " && gh pr create --repo org/public-core --title x "
                     "--body 'ozet " + EPOSTA + "' && echo \"$(cat <<'EOF'\ny\nEOF\n)\"",
                     imza="PUBLIC-PR SIZINTI GATE")
        blok_tarandi("P25 G1 private $(cat)EOF-echo ⇒ public $(cat) e-posta", "Bash",
                     "cd /c/private-proj && git commit -m " + eof_echo
                     + " && cd /c/core && git commit -m \"$(cat <<'EOF'\nfix " + EPOSTA
                     + "\nEOF\n)\"")
        # G2: kullanıcının KENDİ yazdığı literal işaret / tek `$` ikame sayılmaz (dogfood FP).
        gecer("N10 G2 -m tek tirnak literal isaret (guard'i anlatan mesaj)", "Bash",
              "cd /c/core && git commit -m 'fix(guard): " + ISARET + " isareti'")
        gecer("N11 G2 PR --body tek tirnak literal isaret", "Bash",
              "gh pr create --repo org/public-core --title x --body 'deger " + ISARET
              + " kalir'")
        gecer("N12 G2 -m '$' (tirnakli tek karakter)", "Bash",
              "cd /c/core && git commit -m '$'")
        blok_tarandi("P26 G2 KONTROL: literal isaret + e-posta ayni degerde TARANIR", "Bash",
                     "cd /c/core && git commit -m 'fix " + ISARET + " " + EPOSTA + "'")

        # ── bug-gate turu 4 (2026-10-14) ──────────────────────────────────────
        def fail_closed_ikame(ad: str, tool: str, komut: str) -> None:
            """FAIL-CLOSED + SEBEBI ikame (baska bir fail-closed dali — `-F` okunamadi vb. —
            ayni imzayla bloklar; o zaman vektor G4-1'i olcmez)."""
            rc, err = guard(tool, komut)
            ekle(ad + " -> FAIL-CLOSED (komut ikamesi)",
                 rc == 2 and IMZA in (err or "") and "FAIL-CLOSED" in (err or "")
                 and "komut ikamesi" in (err or ""),
                 f"rc={rc} err={(err or '')[-200:]!r}")

        # G4-1: BITISIK kisa bayrakta segment `m$` ile biter (`b37751f`'de rc 0).
        for ad_, tool_, kmt_ in (
                ("F6 G4-1 -m$(echo …) bitisik", "Bash",
                 "cd /c/core && git commit -m$(echo " + EPOSTA + ")"),
                ("F7 G4-1 -am$(printf …) kumeli", "Bash",
                 "cd /c/core && git commit -am$(printf '" + EPOSTA + "')"),
                ("F8 G4-1 -qam$(…) kumeli", "Bash",
                 "cd /c/core && git commit -qam$(echo " + EPOSTA + ")"),
                ("F9 G4-1 -m$(cat dosya)", "Bash",
                 "cd /c/core && git commit -m$(cat /tmp/m.txt)"),
                ("F10 G4-1 3.BAGLAM PowerShell -m$(Get-Content …)", "PowerShell",
                 "git -C /c/core commit -m$(Get-Content C:/tmp/m.txt)"),
                ("F11 G4-1 -m$((…)) aritmetik", "Bash",
                 "cd /c/core && git commit -m$((1+2))")):
            fail_closed_ikame(ad_, tool_, kmt_)
        # Onayli (a) daraltmasi bitisik tirnakli bicimde de korunur (tirnakla biter).
        gecer("N13 G4-1 -m\"$\" bitisik tirnakli tek karakter", "Bash",
              "cd /c/core && git commit -m\"$\"")
        gecer("N14 G4-1 -am'$' bitisik tirnakli kumeli", "Bash",
              "cd /c/core && git commit -am'$'")

        # ── K: KONTROLLER ─────────────────────────────────────────────────────
        sys.path.insert(0, str(kum / "scripts"))
        try:
            import importlib.util as _iu
            spec = _iu.spec_from_file_location("gc_imza_dar", hedefler["gc"])
            g = _iu.module_from_spec(spec)
            sys.modules["gc_imza_dar"] = g
            spec.loader.exec_module(g)
            idp = g.id_pattern(proje_koku=calisma, cwd=calisma)
            ekle("K1 KONTROL: ajan atif satiri GERCEK tarayiciya tek basina TAKILIR "
                 "(N vektorleri muafiyete bagli)",
                 [t for _, t in g.sizintilari_bul(ATIF, idp)] == ["kimlik izi"])
        finally:
            sys.path.pop(0)
            sys.modules.pop("gc_imza_dar", None)

        # K2a: guard Co-Authored-By iceren bir re.compile TASIMAZ (tek kaynak, AST).
        agac = ast.parse(hedefler["ptg"].read_text(encoding="utf-8"))
        yerel = [n.lineno for n in ast.walk(agac)
                 if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "compile"
                 and any(isinstance(a, ast.Constant) and isinstance(a.value, str)
                         and "co-authored-by" in a.value.lower()
                         for a in ast.walk(n))]
        ekle("K2a tek kaynak: pre_tool_guard kendi trailer desenini TASIMAZ",
             yerel == [], f"yerel re.compile satirlari={yerel}")
        # K2b: core_precommit `_ATIF_SATIRI` = genericize_common'dan alinan ad.
        agac = ast.parse(hedefler["pc"].read_text(encoding="utf-8"))
        ithal = {a.asname or a.name for n in ast.walk(agac)
                 if isinstance(n, ast.ImportFrom) and n.module == "genericize_common"
                 for a in n.names}
        atama = [n.value for n in ast.walk(agac) if isinstance(n, ast.Assign)
                 and any(getattr(t, "id", "") == "_ATIF_SATIRI" for t in n.targets)]
        ekle("K2b tek kaynak: core_precommit `_ATIF_SATIRI` genericize_common'dan",
             len(atama) == 1 and isinstance(atama[0], ast.Name)
             and atama[0].id in ithal,
             f"atama={[ast.dump(a)[:60] for a in atama]} ithal={sorted(ithal)}")
    finally:
        _sil(tmp)

    gecen = sum(1 for _, ok, _ in SONUC if ok)
    print(f"\n=== GIT IMZA AYIKLAMA DARLIGI (pre_tool_guard commit-mesaji) "
          f"{'[' + secili + ']' if secili else '[taban]'} ===")
    for ad, ok, detay in SONUC:
        print(f"  [{'OK ' if ok else 'FAIL'}] {ad}" + (f"   -> {detay}" if not ok else ""))
    print(f"\n{gecen}/{len(SONUC)} OK")
    if secili:
        print(f"  (MUTASYON {secili} — dusmesi BEKLENEN vektorler var; "
              "tam skor 'mutasyon KACTI' demektir)")
    print(f"[kum-temizligi] kalan={'evet' if tmp.exists() else 'hayir'}")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
