#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pre_tool_guard — hedef repo METİNDEN çözülmez (repo-maskeleme turu, 2026-10-14).

NEDEN BU KORPUS VAR
-------------------
İki sızıntı gate'i (PUBLIC-PR · COMMIT-MESAJI) yayın/commit hedefinin görünürlüğünü
komut METNİNDEKİ ilk `--repo` / ilk `cd` / ilk `git -C` eşleşmesinden çözüyordu. Tırnaklı
başlık/gövde/mesaj içine yazılmış bir private hedef gerçek PUBLIC hedefi maskeliyor, gövde
TARANMADAN geçiyordu (ağsız probe + gerçek CLI: rc 0). gh'nin kısa bayrağı `-R` hiç
tanınmıyordu: `gh pr create -R <public>` private proje kökünden cwd'ye düşüp geçiyordu.
Kardeş: GH-HEDEF kuralı "açık hedef" hükmünü de metinden veriyordu (`--title 'bkz --repo
x'` hedefsiz mutasyonu serbest bırakıyordu; IGNORECASE `-r <reviewer>`'ı `-R` sayıyordu).

DÜZELTME (ölçülen değişmezler)
  · Sızıntı gate'i: aday kümesi = ESKİ tek-aday (main'in birebir sorgusu) ∪ GERÇEK token
    adayları (`--repo`/`--repo=`/`-R`/`-RX`/`-dR`, `gh api` yolu, `git -C`/`--git-dir`/
    `--work-tree`/`GIT_DIR=`, son gerçek `cd`, yoksa proje kökü). Biri public ise public.
  · Eski aday TUTULUR ⇒ main'e göre gevşeme yapısal olarak 0; mevcut FP'ler (metinde public
    geçen private hedef) aynen kalır — K11/K13/K14 bunu çiviler (lider kararı).
  · Tekil aday > 5 ⇒ sorgusuz FAIL-CLOSED (T1).
  · GH-HEDEF: açık hedef yalnız gerçek token'dan; küme yok, boşluklu token bayrak değil,
    büyük/küçük harf duyarlı. ⚠GEVŞETME (bayraklı, kullanıcıya sunulur): `-Rorg/x`
    bitişik biçim artık açık hedeftir (H5 — eskiden FP blok).

BÖLÜMLER
  M  maskeleme/tanınmayan gerçek hedef: BLOKLANIR + gövde TARANDI (sentinel bulgusu)
  K  kontrol: gerçek hedef private ⇒ GEÇER · public ⇒ BLOK · mevcut FP'ler KALIR
  H  GH-HEDEF: metin hedef sayılmaz (BLOK) · gerçek token hedeftir (GEÇER)
  T  aday tavanı FAIL-CLOSED
  3. BAĞLAM: PowerShell yüzeyi (M1f, M3e, H13) + heredoc/`$(cat)` gövde (M1g, M1h, M2c)

Görünürlük: `gh repo view` alt süreci taklit edilir — repo ARGÜMANI "public" içeriyorsa
public; argüman yoksa cwd yolu "public" içeriyorsa public (ağ yok). Tarayıcı sentinel.
Guard + genericize_common GEÇİCİ kuma kopyalanır; mutasyon yalnız kopyaya uygulanır.
Tüm vektörler TEK alt süreçte koşar (`_PROJ_ROOT` vaka başına atanır).

KOŞUM:  python tests/fixtures/guard_hedef_maskeleme/run.py [--mutasyon-<kip>]
Çıkış:  0 hepsi beklendiği gibi · 1 sapma · 2 DOĞRULANAMADI (çapa tutmadı / mutant bozuk)
"""
from __future__ import annotations

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

# kip -> (eski, yeni) — YALNIZ kumdaki guard kopyasına uygulanır. Yorum = düşmesi gereken.
MUTLAR = {
    # Karar yeniden YALNIZ eski (metin) adaydan => tüm M vektörleri KAÇAR.
    "--mutasyon-eski-tek-aday": (
        "    for h in [eski_hay] + list(adaylar):\n",
        "    for h in [eski_hay]:\n"),
    # Eski aday birleşimden düşer => mevcut FP'ler kalkar (main'e göre GEVŞEME) => K11/K13/K14.
    "--mutasyon-eski-aday-yok": (
        "    for h in [eski_hay] + list(adaylar):\n",
        "    for h in list(adaylar):\n"),
    # gh gerçek bayrak adayı yok (yalnız api yolu) => M1*, M2b, M4*.
    "--mutasyon-gh-bayrak-adayi-yok": (
        "    repolar = _gh_repo_degerleri(seg) + ([api_repo] if api_repo else [])\n",
        "    repolar = [api_repo] if api_repo else []\n"),
    # `-R` hiç tanınmaz (eski `_ARG_REPO` körlüğü) => M1e, M2b, M4, M4b-M4e; H5/H6 BLOK olur.
    "--mutasyon-kisa-r-yok": (
        '_GH_KISA_REPO = re.compile(r"^-([A-Za-z]*)R(.*)$", re.DOTALL)',
        '_GH_KISA_REPO = re.compile(r"^-([A-Za-z]*)\\x00R(.*)$", re.DOTALL)'),
    # git üst seçenek/ortam adayı yok => M5, M5b, M5c, M5d.
    "--mutasyon-git-hedef-yok": (
        "    baglam = _baglam_cwd_hay(segler, idx)\n    if not yollar:\n",
        "    baglam = _baglam_cwd_hay(segler, idx)\n    yollar = []\n    if not yollar:\n"),
    # Aday tavanı etkisiz => T1 (6 private aday) GEÇER.
    "--mutasyon-tavan-yok": ("_HEDEF_ADAY_TAVANI = 5", "_HEDEF_ADAY_TAVANI = 99"),
    # GH-HEDEF yeniden METİNDEN (eski `_GH_A_ACIK`) => H1, H2, H4, H9, H13, H16 GEÇER; H5 BLOK.
    "--mutasyon-ghhedef-metin": (
        "    acik_bayrak = bool(_gh_repo_degerleri(komut, kesin=True))\n",
        "    acik_bayrak = bool(_GH_A_ACIK.search(komut))\n"),
    # Kesin kipte küme kabul edilir => H7 (-dR) · H8 (-tRelease = başlık) GEÇER.
    "--mutasyon-ghhedef-kume": (
        "            if not m or (kesin and m.group(1)):\n",
        "            if not m:\n"),
    # Boşluklu (tırnaklı metin) token bayrak sayılır => H16 (`--subject "-R org/x"`) GEÇER.
    "--mutasyon-ghhedef-bosluk": (
        "        if kesin and any(c.isspace() for c in tok):\n            continue\n", ""),
    # `-r` (reviewer) `-R` sayılır => H4 GEÇER.
    "--mutasyon-ghhedef-buyuk-kucuk": (
        '_GH_KISA_REPO = re.compile(r"^-([A-Za-z]*)R(.*)$", re.DOTALL)',
        '_GH_KISA_REPO = re.compile(r"^-([A-Za-z]*)R(.*)$", re.DOTALL | re.IGNORECASE)'),
    # Konumsal hedef yeniden METİNDEN => H3 (`--description 'bkz org/x'`) GEÇER.
    "--mutasyon-ghhedef-konumsal-metin": (
        "    return any(_GH_KONUMSAL.fullmatch(tok) for tok in t[2:])\n",
        "    return bool(_GH_B_ACIK.search(seg[_GH_B.search(seg).end():]))\n"),
}

S = "SIZINTI" + "-SENTINEL"
PR, CM, GH = "PUBLIC-PR SIZINTI GATE", "COMMIT-MESAJI SIZINTI GATE", "GH HEDEF BELİRSİZ"

# (ad, proje: "pub"|"priv", tool, komut, beklenen: imza | 0)
# Komutlarda <PUB>/<PRIV> = kumdaki gerçek dizinler (POSIX eğik çizgi), <ROOT> = üstleri.
VEKTORLER = [
    # ── M: maskeleme — gerçek PUBLIC hedef, metinde private hedef ─────────────
    ("M1 baslikta --repo private ONCE, gercek --repo public", "pub", "Bash",
     f"gh pr create --title 'bkz --repo org/private-proj' --repo org/public-core --body '{S}'", PR),
    ("M1b --repo= bicimi, cift tirnak", "pub", "Bash",
     f'gh pr create --title "bkz --repo=org/private-proj" --repo=org/public-core --body "{S}"', PR),
    ("M1c -b govdede once", "pub", "Bash",
     f"gh pr create -t t -b 'x --repo org/private-proj {S}' --repo org/public-core", PR),
    ("M1d issue comment", "pub", "Bash",
     f"gh issue comment 5 --body 'bkz --repo org/private-proj {S}' --repo org/public-core", PR),
    ("M1e -R gercek + metinde --repo private", "priv", "Bash",
     f"gh pr create -t 'bkz --repo org/private-proj' -R org/public-core -b '{S}'", PR),
    ("M1f 3.BAGLAM PowerShell", "pub", "PowerShell",
     f"gh pr create --title 'bkz --repo org/private-proj' --repo org/public-core --body '{S}'", PR),
    ("M1g 3.BAGLAM --body-file heredoc + baslikta --repo private", "priv", "Bash",
     f"gh pr create --title 'bkz --repo org/private-proj' --repo org/public-core "
     f"--body-file - <<'B'\n{S}\nB", PR),
    ("M1h 3.BAGLAM $(cat) govde + baslikta --repo private", "priv", "Bash",
     f"gh pr create --title 'bkz --repo org/private-proj' --repo org/public-core "
     f"--body \"$(cat <<'EOF'\n{S}\nEOF\n)\"", PR),
    ("M1i release --notes + metinde --repo private", "priv", "Bash",
     f"gh release create v1 --title 'bkz --repo org/private-proj' --notes '{S}' "
     f"--repo org/public-core", PR),
    ("M2 commit mesajinda cd <private>, cwd public", "pub", "Bash",
     f"git commit -m 'not: cd <PRIV> sonra {S}'", CM),
    ("M2b gh -R public + baslikta cd <private>", "priv", "Bash",
     f"gh pr create -R org/public-core -t 'cd <PRIV>' -b '{S}'", PR),
    ("M2c 3.BAGLAM $(cat) mesajda cd <private>, cwd public", "pub", "Bash",
     f"git commit -m \"$(cat <<'EOF'\nbaslik\n\ncd <PRIV>\n{S}\nEOF\n)\"", CM),
    ("M3 commit mesajinda --repo private, cwd public", "pub", "Bash",
     f"git commit -m 'bkz --repo org/private-proj {S}'", CM),
    ("M3b mesajda yeni satir + git -C <private>", "pub", "Bash",
     f"git commit -m 'baslik\ngit -C <PRIV> log {S}'", CM),
    ("M3c cd public && commit, mesajda --repo private", "priv", "Bash",
     f"cd <PUB> && git commit -m 'bkz --repo org/private-proj {S}'", CM),
    ("M3d -F heredoc + -m'de --repo private", "pub", "Bash",
     f"git commit -m 'bkz --repo=org/private-proj' -F - <<'M'\n{S}\nM", CM),
    ("M3e 3.BAGLAM PowerShell commit mesajinda --repo private", "pub", "PowerShell",
     f"git commit -m 'bkz --repo org/private-proj {S}'", CM),
    ("M4 -R public, proje koku private", "priv", "Bash",
     f"gh pr create -R org/public-core -t t -b '{S}'", PR),
    ("M4b -Rorg/public bitisik", "priv", "Bash",
     f"gh pr create -Rorg/public-core -t t -b '{S}'", PR),
    ("M4c -R=org/public", "priv", "Bash", f"gh pr create -R=org/public-core -t t -b '{S}'", PR),
    ("M4d issue comment -R public", "priv", "Bash",
     f"gh issue comment 5 -R org/public-core --body '{S}'", PR),
    ("M4e -dR kume + --repo private (iki deger: fail-closed)", "priv", "Bash",
     f"gh pr create -dR org/public-core -t t -b '{S}' --repo org/private-proj", PR),
    ("M4f iki --repo, ikincisi public", "priv", "Bash",
     f"gh pr create --repo org/private-proj --repo org/public-core -t t -b '{S}'", PR),
    ("M5 GIT_DIR public, cwd private", "priv", "Bash",
     f"GIT_DIR=<PUB>/.git git commit -m '{S}'", CM),
    ("M5b --git-dir= public, cwd private", "priv", "Bash",
     f"git --git-dir=<PUB>/.git commit -m '{S}'", CM),
    ("M5c --work-tree public, cwd private", "priv", "Bash",
     f"git --work-tree <PUB> commit -m '{S}'", CM),
    ("M5d git -C goreli (cd baglami + alt dizin public)", "priv", "Bash",
     f"cd <ROOT> && git -C public-core commit -m '{S}'", CM),
    # ── K: kontroller ────────────────────────────────────────────────────────
    ("K1 --repo public", "priv", "Bash", f"gh pr create --repo org/public-core -t t -b '{S}'", PR),
    ("K2 --repo private, cwd public", "pub", "Bash",
     f"gh pr create --repo org/private-proj -t t -b '{S}'", 0),
    ("K3 commit cwd public", "pub", "Bash", f"git commit -m '{S}'", CM),
    ("K4 commit cwd private", "priv", "Bash", f"git commit -m '{S}'", 0),
    ("K5 cd private && commit (cwd public)", "pub", "Bash", f"cd <PRIV> && git commit -m '{S}'", 0),
    ("K6 cd public && commit (cwd private)", "priv", "Bash", f"cd <PUB> && git commit -m '{S}'", CM),
    ("K7 git -C private commit (cwd public)", "pub", "Bash", f"git -C <PRIV> commit -m '{S}'", 0),
    ("K8 git -C public commit (cwd private)", "priv", "Bash", f"git -C <PUB> commit -m '{S}'", CM),
    ("K9 gh api repos/public", "priv", "Bash", f"gh api repos/org/public-core/issues -f body='{S}'", PR),
    ("K10 cd public && gh api repos/private (yol kazanir)", "priv", "Bash",
     f"cd <PUB> && gh api repos/org/private-proj/issues -f body='{S}'", 0),
    ("K11 -R private, cwd public — mevcut FP KALIR (eski aday)", "pub", "Bash",
     f"gh pr create -R org/private-proj -t t -b '{S}'", PR),
    ("K12 temiz govde --repo public", "priv", "Bash", "gh pr create --repo org/public-core -t t -b temiz", 0),
    ("K13 metinde --repo public ONCE, gercek private — mevcut FP KALIR", "priv", "Bash",
     f"gh pr create --title 'bkz --repo org/public-core' --repo org/private-proj --body '{S}'", PR),
    ("K14 mesajda cd <public>, cwd private — mevcut FP KALIR", "priv", "Bash",
     f"git commit -m 'not: cd <PUB> {S}'", CM),
    ("K15 metinde ve gercekte private, cwd public", "pub", "Bash",
     f"gh pr create --title 'bkz --repo org/private-proj' --repo org/private-proj --body '{S}'", 0),
    ("K16 private proje, mesajda --repo private", "priv", "Bash",
     f"git commit -m 'bkz --repo org/private-proj {S}'", 0),
    # ── T: aday tavani ────────────────────────────────────────────────────────
    ("T1 alti private --repo adayi -> FAIL-CLOSED", "priv", "Bash",
     "gh pr create " + " ".join(f"--repo org/private-{n}" for n in range(6)) + f" -t t -b '{S}'",
     "aday-tavani"),
    # ── H: GH-HEDEF ──────────────────────────────────────────────────────────
    ("H1 baslikta --repo, gercek hedef yok", "priv", "Bash", "gh pr create -t 'bkz --repo org/x' -b b", GH),
    ("H2 pr merge subject'te -R", "priv", "Bash", "gh pr merge 5 --squash --subject 'x -R org/x'", GH),
    ("H3 repo edit description'da org/x", "priv", "Bash", "gh repo edit --description 'bkz org/x'", GH),
    ("H4 -r reviewer (buyuk/kucuk harf)", "priv", "Bash", "gh pr create -r someone -t t -b b", GH),
    ("H5 -Rorg/x bitisik (GEVSETME: FP kalkar)", "priv", "Bash", "gh pr create -Rorg/x -t t -b b", 0),
    ("H6 -R=org/x", "priv", "Bash", "gh pr create -R=org/x -t t -b b", 0),
    ("H7 -dR kume (eskisi gibi BLOK)", "priv", "Bash", "gh pr create -dR org/x -t t -b b", GH),
    ("H8 -tRelease = baslik, hedef DEGIL", "priv", "Bash", "gh pr create -tRelease -b b", GH),
    ("H9 body'de tirnakli --repo", "priv", "Bash", 'gh pr comment 5 --body "--repo org/x"', GH),
    ("H10 commit mesajinda gh satiri + --repo (eskisi gibi GECER)", "priv", "Bash",
     'git commit -m "x\ngh pr create --repo org/x"', 0),
    ("H11 repo edit konumsal", "priv", "Bash", "gh repo edit org/x --description d", 0),
    ("H12 repo create URL (eskisi gibi BLOK)", "priv", "Bash", "gh repo create https://github.com/org/x", GH),
    ("H13 3.BAGLAM PowerShell baslikta --repo", "priv", "PowerShell",
     "gh issue create --title 'bkz --repo org/x' --body b", GH),
    ("H14 repo delete --yes konumsal", "priv", "Bash", "gh repo delete --yes org/x", 0),
    ("H15 --repo gercek + baslikta -R metni", "priv", "Bash", "gh pr create --repo org/x -t 'bkz -R org/y' -b b", 0),
    ("H16 subject tamamen '-R org/x' (bosluklu token)", "priv", "Bash",
     'gh pr merge 5 --squash --subject "-R org/x"', GH),
]

_SURUCU = r'''
import importlib.util, io, json, sys, subprocess as sp, types
from pathlib import Path
guard, vek_yolu = sys.argv[1:3]
gercek = sp.run
CAGRI = []
def sahte(argv, *a, **k):
    if isinstance(argv, (list, tuple)) and list(argv[:3]) == ["gh", "repo", "view"]:
        hedef = str(argv[3]) if len(argv) > 3 and not str(argv[3]).startswith("-") else ""
        cwd = str(k.get("cwd") or "")
        pub = ("public" in hedef.lower()) if hedef else ("public" in Path(cwd).name.lower())
        CAGRI.append(hedef or "cwd")
        return types.SimpleNamespace(returncode=0, stderr="", stdout=json.dumps(
            {"isPrivate": not pub, "nameWithOwner": hedef or Path(cwd).name}))
    return gercek(argv, *a, **k)
sp.run = sahte
spec = importlib.util.spec_from_file_location("ptg_hedef_maske", guard)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
S = "SIZINTI" + "-SENTINEL"
m.sizintilari_bul = lambda metin, desen: [(S, "yapay-kategori")] if S in (metin or "") else []
out = []
for v in json.load(open(vek_yolu, encoding="utf-8")):
    m._PROJ_ROOT = Path(v["proje"])
    del CAGRI[:]
    e = io.StringIO(); ge, gi = sys.stderr, sys.stdin
    sys.stderr, sys.stdin = e, io.StringIO(json.dumps(
        {"tool_name": v["tool"], "tool_input": {"command": v["komut"]}}))
    try:
        rc = m.main()
    except BaseException as x:
        rc = "COKTU:" + repr(x)[:80]
    finally:
        sys.stderr, sys.stdin = ge, gi
    out.append({"rc": rc, "err": e.getvalue(), "cagri": list(CAGRI)})
sys.stdout.write("<<SONUC>>" + json.dumps(out))
'''


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

    tmp = Path(tempfile.mkdtemp(prefix="hedef_maske_"))
    sonuc: list = []
    try:
        if ("public" in str(tmp).lower() or "private" in str(tmp).lower()
                or any(c.isspace() for c in str(tmp))):
            print(f"[DOGRULANAMADI] gecici yol gorunurluk taklidini bozar: {tmp}")
            return 2
        kum = tmp / "kum"
        (kum / "scripts" / "hooks").mkdir(parents=True)
        shutil.copy2(SCRIPTS / "genericize_common.py", kum / "scripts")
        ptg = kum / "scripts" / "hooks" / "pre_tool_guard.py"
        shutil.copy2(SCRIPTS / "hooks" / "pre_tool_guard.py", ptg)
        if secili:
            eski, yeni = MUTLAR[secili]
            kaynak = ptg.read_bytes().decode("utf-8").replace("\r\n", "\n")
            if kaynak.count(eski) != 1:
                print(f"[DOGRULANAMADI] mutasyon capasi {kaynak.count(eski)} kez bulundu "
                      f"({secili}) -> mutasyon UYGULANMADI; 'gecti' sonucu ANLAMSIZ olurdu.")
                return 2
            ptg.write_bytes(kaynak.replace(eski, yeni, 1).encode("utf-8"))
            try:
                compile(ptg.read_text(encoding="utf-8"), str(ptg), "exec")
            except SyntaxError as e:
                print(f"[DOGRULANAMADI] mutant SOZDIZIMI BOZUK ({secili}): {e}")
                return 2

        root = tmp / "ws"
        pub, priv = root / "public-core", root / "private-proj"
        for d in (pub, priv):
            d.mkdir(parents=True)
        yer = {"<PUB>": pub.as_posix(), "<PRIV>": priv.as_posix(), "<ROOT>": root.as_posix()}

        def coz(s: str) -> str:
            for k, v in yer.items():
                s = s.replace(k, v)
            return s

        vek = [{"proje": str(pub if p == "pub" else priv), "tool": tool, "komut": coz(k)}
               for _, p, tool, k, _ in VEKTORLER]
        vy = tmp / "vek.json"
        vy.write_text(json.dumps(vek, ensure_ascii=False), encoding="utf-8")
        calisma = tmp / "calisma"
        calisma.mkdir()
        env = dict(os.environ)
        for k in ("CLAUDE_PROJECT_DIR", "IX_GENERICIZE_BLOCKLIST"):
            env.pop(k, None)
        r = subprocess.run([sys.executable, "-", str(ptg), str(vy)], input=_SURUCU,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=240, env=env, cwd=str(calisma))
        if "<<SONUC>>" not in (r.stdout or ""):
            print(f"[DOGRULANAMADI] surucu sonuc uretmedi: {(r.stderr or r.stdout)[-400:]}")
            return 2
        cikti = json.loads(r.stdout.split("<<SONUC>>", 1)[1])
        for (ad, _, _, _, bek), c in zip(VEKTORLER, cikti):
            rc, err = c["rc"], c["err"] or ""
            if bek == 0:
                ok = rc == 0
                beklenti = "GECER (exit 0)"
            elif bek in (PR, CM):
                # Blok SIZINTI TARAMASINDAN gelmeli (bulgu turu stderr'de) — gorunurluk
                # sorulamadi fail-closed'u ya da baska kural ayni rc'yi verir, olcmez.
                ok = (rc == 2 and bek in err and "yapay-kategori" in err
                      and "FAIL-CLOSED" not in err and "gorunurluk-sorulamadi" not in err)
                beklenti = "BLOKLANIR + govde TARANDI"
            elif bek == "aday-tavani":
                ok = rc == 2 and "hedef-aday-tavani-asildi" in err and not c["cagri"]
                beklenti = "FAIL-CLOSED (aday tavani, gh SORULMADI)"
            else:
                ok = rc == 2 and bek in err
                beklenti = "BLOKLANIR (GH-HEDEF)"
            sonuc.append((f"{ad} -> {beklenti}", ok,
                          f"rc={rc} cagri={c['cagri']} err={err[-160:]!r}"))
    finally:
        _sil(tmp)

    gecen = sum(1 for _, ok, _ in sonuc if ok)
    print(f"\n=== GUARD HEDEF MASKELEME (pre_tool_guard sizinti gate'leri + GH-HEDEF) "
          f"{'[' + secili + ']' if secili else '[taban]'} ===")
    for ad, ok, detay in sonuc:
        print(f"  [{'OK ' if ok else 'FAIL'}] {ad}" + (f"   -> {detay}" if not ok else ""))
    print(f"\n{gecen}/{len(sonuc)} OK")
    if secili:
        print(f"  (MUTASYON {secili} — dusmesi BEKLENEN vektorler var; "
              "tam skor 'mutasyon KACTI' demektir)")
    print(f"[kum-temizligi] kalan={'evet' if tmp.exists() else 'hayir'}")
    return 0 if sonuc and gecen == len(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
