#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""team_setup_gitignore_blok — `.gitignore` YÖNETİLEN BLOK senkronu (Q365④).

KUSUR (ölçüldü 2026-10-12, iki tüketici proje): `.gitignore` `init_project` ile BİR KEZ yazılır
ve bayatlar. Q241 (2026-09-02) `conn/` altını topyekûn kilitledi; Q241 öncesi kurulan projelerde
`git check-ignore --no-index conn/.gmail_app_password` rc=1 (sır dosyası commit'e AÇIK).

TASARIM (PR #326 sadeleştirme turu): blok dosyanın BAŞINDA; projenin satırları bloktan SONRA,
sırası ve baytı DEĞİŞMEDEN. Aynı dosyada SON eşleşen satır kazandığı için blok projenin gizlediği
hiçbir yolu AÇAMAZ — iddia kurala dayanır; bu korpus onu gerçek `git check-ignore` ile ÖLÇER.
(Önceki tasarım bloğu SONA koyup etkiyi geçici repoda ölçüyor, gerekirse proje negasyonunu
yeniden yazıyordu; iki bug-gate turu üst üste sessiz gevşetme buldu — K4b vakası.)

⛔ DEĞİŞMEZ ÜÇLÜSÜ (her `D:` vektöründe ayrı ayrı ölçülür):
  ① projenin KENDİ satırlarında (blok çıkarılmış taban) IGNORE olan yollardan blok sonrası AÇILAN = 0
     (`git check-ignore -v -n --no-index --stdin`, PROBE yol kümesi)
  ② proje bölümü BAYT-EŞ: [BOM] + [blok] + <taban> ; blok yalnız başta
  ③ ikinci koşum bayt-eş (yazmaz)
YALITIM: süreç ortamı `GIT_CONFIG_GLOBAL=os.devnull` · `GIT_CONFIG_NOSYSTEM=1` · `git init --template=`
(global `core.excludesFile` / şablon `info/exclude` ölçüme karışmaz); `GIT_*` değişkenleri temizlenir.

VEKTÖRLER
  D:K1 `conn/secret[12].template` · D:K2 `*secret*` · D:K3 `conn/*_PRD.*` · D:K4b `*.zip`/`!keep*.zip`/
  `*secret*` (önceki tasarımda keep-secret.zip AÇILIYORDU) · D:K4c sade tekrar · D:K6 `conn/**/x.template`
  D:E1 `/conn/*` · D:E2 `conn/**` · D:E3 `*.template` · D:E4 `conn/*.env`+`!conn/README.md` (README açık
  KALIR) · D:E5 `conn/` · D:E6 bloklu dosyaya proje SONRADAN `/conn/*` ekler (blok ortada → başa)
  D:C3 (3. bağlam) şablon-dışı elle yazılmış (`core/` · `*.zip` · `!keep.zip`) → keep.zip AÇIK kalır
  D:G1 bayat (Q241 öncesi) LF → conn/* eklenir, sır dosyaları açık→IGNORE, conn/a.template açık
  D:G2 CRLF → blok CRLF, yalın LF yok   · D:G5 `conn/*` var, `!conn/.gitkeep` yok → .gitkeep IGNORE kalır
  D:G6 ORTADAKİ bayat blok → başa taşınır, eski satır gider   · D:G6b SONDAKİ blok (eski tasarım çıktısı)
  D:G9 sonda satır sonu yok → son proje satırı EOL'süz aynen   · D:G14 BOM → BOM başta, blok arkasında,
       projenin ilk satırı hâlâ etkili   · D:G15 proje tüm şablon satırlarını içerir → eski blok KALDIRILIR
  G3 güncel dosya (şablonun kendisi) → YAZILMAZ    · G7 bozuk işaret → YAZILMAZ + WARN BOZUK
       (G7 çift başlangıç · G7b ters sıra · G7c yalnız başlangıç 1/0 · G7d yalnız bitiş 0/1)
  Y1 GERÇEK salt-okunur (.gitignore özniteliği / POSIX dizin 0o555) · Y2 os.replace OSError enjeksiyonu
     → WARN YAZILAMADI, `.gitignore.ix-tmp` YOK, dosya aynı
  W2/W3 main uçtan uca: gitignore adımı yazamaz / beklenmeyen istisna → exit 0 + sonraki kablolama
     adımları (hookspath_core · hookspath_proje · sablon_sapmasi · _core_index_yenile) KOŞAR
  OL1 `git ls-files -o` zaman aşımı → WARN "görünürlüğü ÖLÇÜLEMEDİ"
  S3/S4 (SINIR d — çerçeve) değişmez projenin KENDİ satırlarına göre: bloğun ÜSTÜNDEKİ `!conn/x.env`
     blok başa taşınınca kazanır (S3, metinde (1a)) · eski bloktan çıkan satırın gizlediği yol açılır
     (S4: eski blok BAŞTA ⇒ metin "başta değildi" öncülünü İÇERMEZ, (1b) kendi başına) → GÖRÜNÜR WARN
     (d)+excludes nedenleriyle; S1'de (eski blok yok) (d) nedeni YOK   · S5 proje sır negasyonu açık kalır
  G8 source_root yok → `{source_root}` literal yazılmaz   · G10 yeni gizlenen izlenmeyen dosya → WARN
  G11 şablon TEK KAYNAK   · G12 .gitignore yok + git → bloklu dosya doğar   · G13 git değil → YARATILMAZ
  S2 (SINIR ②) `!.claude/agents/mine.md` + blok `.claude/agents/` → açılan 0; yol IGNORE olur ve
     izlenmeyen dosya "artık IGNORE" WARN'ında GÖRÜNÜR
  S1 (SINIR ①) `.git/info/exclude` README'yi gizler, bloktaki `!conn/README.md` açar → "GÖRÜNÜR" WARN
  M1 makineden bağımsız: global `core.excludesFile` (*.zip, conn/) VARKEN aynı dosya bayt-eş blok alır
  KP KAPSAM satırı her koşumda (yazım · değişiklik yok · bozuk · atlandı) basılır
  W1 KABLOLAMA: main() `dosya_tamamla` sonrası `gitignore_senkron` çağırır (AST), `--no-gitignore`

MUTASYON (bugünkü kaynaktan; çapa tam 1 kez bulunmazsa exit 2):
  --mutasyon-blok-sona     blok proje satırlarının SONUNA      → K*/E1–E3/E6/D② düşer
  --mutasyon-proje-degisir proje satırları normalize edilir     → G9/G2 (D②) düşer
  --mutasyon-idempotens    proje kümesi blok içini de sayar     → D③ düşer
  --mutasyon-kapsam-yok    KAPSAM satırı basılmaz               → KP düşer
  --mutasyon-bom           BOM ayrı tutulmaz                    → G14 düşer
  --mutasyon-crlf          eol sabit LF                         → G2 düşer
  --mutasyon-kablosuz      main çağırmaz                        → W1 düşer
  --mutasyon-gorunurluk    gizlenen dosya uyarısı susar         → G10 · S2 düşer
  --mutasyon-ters-isaret   ters sıra kabul                      → G7b düşer
  --mutasyon-bos-isaret-ok yalnız çoklu işaret bozuk sayılır    → G7b/c/d düşer
  --mutasyon-olculemedi-yok ÖLÇÜLEMEDİ WARN'ı susar             → OL1 düşer
  --mutasyon-kapsam-sinirsiz / -kapsam-cercevesiz KAPSAM ① (a) / ③ metni silinir → KP düşer
  --mutasyon-yazim-yakalanmaz OSError yakalanmaz                → Y1 · Y2 · W2 düşer
  --mutasyon-gecici-kalir  geçici dosya silinmez                → Y2 · W2 düşer (her platform) ·
                           Y1 YALNIZ Windows'ta (POSIX dalında dizin 0o555 ⇒ geçici dosya hiç doğmaz)
  --mutasyon-main-yakalanmaz main'deki koruma yok               → W3 düşer
  --mutasyon-gorunur-tek-neden / -gorunur-hep-iki GÖRÜNÜR nedeni yanlış → S3/S4 / S1 düşer
  --mutasyon-acilan-sus    GÖRÜNÜR WARN susar                   → S1 · S3 · S4 düşer
  --mutasyon-neg-bloga-girmez şablon negasyonu bloğa girmez     → G1 · S1 düşer
TABAN (eski kod): --kaynak <team_setup.py>

Çıkış: 0 beklendiği gibi · 1 sapma · 2 KURULAMADI
"""
from __future__ import annotations

import ast
import contextlib
import io
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TS = REPO / "scripts" / "team_setup.py"

GECERLI_KIP = ("--mutasyon-blok-sona", "--mutasyon-proje-degisir", "--mutasyon-idempotens",
               "--mutasyon-kapsam-yok", "--mutasyon-bom", "--mutasyon-crlf",
               "--mutasyon-kablosuz", "--mutasyon-gorunurluk",
               "--mutasyon-ters-isaret", "--mutasyon-bos-isaret-ok", "--mutasyon-olculemedi-yok",
               "--mutasyon-kapsam-sinirsiz", "--mutasyon-kapsam-cercevesiz", "--mutasyon-yazim-yakalanmaz",
               "--mutasyon-gecici-kalir", "--mutasyon-main-yakalanmaz", "--mutasyon-gorunur-tek-neden",
               "--mutasyon-gorunur-hep-iki", "--mutasyon-acilan-sus", "--mutasyon-neg-bloga-girmez")
KIP: set[str] = set()
TABAN: Path | None = None
_a = sys.argv[1:]
while _a:
    x = _a.pop(0)
    if x == "--kaynak" and _a:
        TABAN = Path(_a.pop(0)).resolve()
    elif x in GECERLI_KIP:
        KIP.add(x)
    else:
        print(f"[DURDU] bilinmeyen arguman: {x!r} — gecerli: {list(GECERLI_KIP)} + --kaynak")
        sys.exit(2)

# ── YALITIM: kullanıcının/sistemin git config'i ölçüme KARIŞMAZ (süreç geneli — test edilen kod dahil)
for _k in [k for k in os.environ if k.startswith("GIT_")]:
    os.environ.pop(_k, None)
os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"

SONUC: list[tuple[str, bool, str]] = []
PROBE = sorted({
    "conn/README.md", "conn/.gitkeep", "conn/a.template", "conn/x.env", "conn/mail_list.txt",
    "conn/.gmail_app_password", "conn/DEV.conn_adt", "conn/sub/README.md", "conn/sub/x.template",
    "conn/secret1.template", "conn/secret2.template", "conn/secretx.template", "conn/my-secret.template",
    "conn/sys_PRD.template", "conn/x.template", "conn/a/x.template", "conn/a/b/x.template",
    "keep.zip", "yedek.zip", "keep1.zip", "keep-secret.zip", "a/b.zip", "ix-ornek.template",
    "a/b.template", ".conn_adt", "core/x.md", "a/core/x.md", ".claude/agents/mine.md",
    ".claude/settings.json", "CLAUDE.local.md", ".tmp/x", "x.pyc", "node_modules/x.js",
    "SOURCE_CODES/SD/ZSD001/ui/app/dist/x.js", "benim-ozel.txt", "benim/ozel/x"})

BAYAT = (  # Q241 öncesi şablon şekli (çekirdeğin kendi eski metni)
    "# ==== SIZINTI KİLİDİ ====\n/core/\n.claude/agents/\n.claude/skills/\n.claude/commands/\n"
    ".claude/rules/\n.claude/memory-seed/\n\n# ==== SIRLAR ====\n.conn_adt\nconn/*.env\n"
    "conn/.conn_adt.bak\n.csrf_token.json\n.claude/genericize-blocklist.txt\n"
    ".claude/project.local.yaml\n")


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul), detay))
    print(f"  [{'OK' if kosul else 'FAIL'}] {ad}" + (f"  -- {detay}" if not kosul and detay else ""))


def _degistir(metin: str, eski: str, yeni: str, ad: str) -> str:
    n = metin.count(eski)
    if n != 1:
        print(f"[DURDU] KURULAMADI: {ad} capasi {n} kez bulundu (1 bekleniyordu): {eski[:70]!r}")
        sys.exit(2)
    return metin.replace(eski, yeni)


def _kaynak() -> str:
    if TABAN is not None:
        return TABAN.read_text(encoding="utf-8")
    m = TS.read_text(encoding="utf-8")
    if "--mutasyon-blok-sona" in KIP:
        m = _degistir(m, '    yeni = bom + govde + "".join(proje)\n',
                      '    yeni = bom + "".join(proje) + govde\n', "blok-sona")
    if "--mutasyon-proje-degisir" in KIP:
        m = _degistir(m, '    yeni = bom + govde + "".join(proje)\n',
                      '    yeni = bom + govde + "".join(s.rstrip("\\r\\n") + "\\n" for s in proje)\n',
                      "proje-degisir")
    if "--mutasyon-idempotens" in KIP:
        m = _degistir(m, '    var = {s.rstrip("\\r\\n") for s in proje}\n',
                      '    var = {s.rstrip("\\r\\n") for s in satirlar}\n', "idempotens")
    if "--mutasyon-kapsam-yok" in KIP:
        m = _degistir(m, "        say(INFO, GI_KAPSAM)\n", "        pass\n", "kapsam-yok")
    if "--mutasyon-bom" in KIP:
        m = _degistir(m, '    bom = "\\ufeff" if mevcut.startswith("\\ufeff") else ""\n',
                      '    bom = ""\n', "bom")
    if "--mutasyon-crlf" in KIP:
        m = _degistir(m, '    eol = "\\r\\n" if "\\r\\n" in mevcut else "\\n"\n',
                      '    eol = "\\n"\n', "crlf")
    if "--mutasyon-kablosuz" in KIP:
        m = _degistir(m, "        gitignore_senkron(proje)\n", "        pass\n", "kablosuz")
    if "--mutasyon-gorunurluk" in KIP:
        m = _degistir(m, "        if gizlenen:\n", "        if False and gizlenen:\n", "gorunurluk")
    # ── PR #326 bug-gate 3. tur (bulgular 1–5): her yeni dal için ayrı kip ──
    isaret = "    if (len(bas), len(son)) not in ((0, 0), (1, 1)) or (bas and son[0] < bas[0]):\n"
    if "--mutasyon-ters-isaret" in KIP:
        m = _degistir(m, isaret, "    if (len(bas), len(son)) not in ((0, 0), (1, 1)):\n", "ters-isaret")
    if "--mutasyon-bos-isaret-ok" in KIP:
        m = _degistir(m, isaret, "    if len(bas) > 1 or len(son) > 1:\n", "bos-isaret-ok")
    if "--mutasyon-olculemedi-yok" in KIP:
        m = _degistir(m, "    if git_var and (once is None or sonra is None):\n", "    if False:\n",
                      "olculemedi-yok")
    if "--mutasyon-kapsam-sinirsiz" in KIP:
        m = _degistir(m, '"ile gizlenen yolu açabilir (yalnız MEVCUT izlenmeyen dosyalar yazım öncesi/sonrası "',
                      '"x "', "kapsam-sinirsiz")
    if "--mutasyon-kapsam-cercevesiz" in KIP:
        m = _degistir(m, '"dahil EDEMEZ (yol IGNORE olur) ③ garanti dosyanın O ANKİ hâline göre DEĞİL: eski blok "',
                      '"dahil EDEMEZ (yol IGNORE olur) eski blok "', "kapsam-cercevesiz")
    if "--mutasyon-yazim-yakalanmaz" in KIP:
        m = _degistir(m, '    except OSError as e:\n        kalan = ""\n',
                      '    except ImportError as e:\n        kalan = ""\n', "yazim-yakalanmaz")
    if "--mutasyon-gecici-kalir" in KIP:
        m = _degistir(m, "            gecici.unlink(missing_ok=True)\n", "            pass\n", "gecici-kalir")
    if "--mutasyon-main-yakalanmaz" in KIP:
        m = _degistir(m, "        except Exception as e:  # noqa: BLE001 — gözlem adımı",
                      "        except ImportError as e:  # noqa: BLE001 — gözlem adımı", "main-yakalanmaz")
    if "--mutasyon-gorunur-tek-neden" in KIP:
        m = _degistir(m, "            if eski_blok:\n", "            if False:\n", "gorunur-tek-neden")
    if "--mutasyon-gorunur-hep-iki" in KIP:
        m = _degistir(m, "            if eski_blok:\n", "            if True:\n", "gorunur-hep-iki")
    if "--mutasyon-acilan-sus" in KIP:
        m = _degistir(m, "        if acilan:\n", "        if False and acilan:\n", "acilan-sus")
    if "--mutasyon-neg-bloga-girmez" in KIP:
        m = _degistir(m, "        if ham not in var:\n", '        if ham not in var and not ham.startswith("!"):\n',
                      "neg-bloga-girmez")
    return m


def _yukle() -> tuple[dict, str]:
    kaynak = _kaynak()
    g = {"__name__": "team_setup_gi", "__file__": str(TS), "__builtins__": __builtins__}
    exec(compile(kaynak, str(TS), "exec"), g)
    return g, kaynak


def _sil(d: Path) -> None:
    def _ac(func, path, _exc):  # noqa: ANN001
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass
    kw = {"onexc": _ac} if sys.version_info >= (3, 12) else {"onerror": _ac}
    try:
        shutil.rmtree(d, **kw)  # type: ignore[arg-type]
    except Exception:
        shutil.rmtree(d, ignore_errors=True)


def _repo(kok: Path, ad: str, gitignore: bytes | None, *, git: bool = True,
          source_root: str | None = "SOURCE_CODES") -> Path:
    d = kok / ad
    d.mkdir()
    if git:
        subprocess.run(["git", "-c", "core.autocrlf=false", "init", "-q", "--template=", str(d)],
                       check=True)
    if gitignore is not None:
        (d / ".gitignore").write_bytes(gitignore)
    if source_root:
        (d / "project.yaml").write_bytes(f"source_root: {source_root}\n".encode())
    return d


def _ignore(d: Path, yol: str) -> bool:
    return subprocess.run(["git", "-C", str(d), "check-ignore", "-q", "--no-index", yol]).returncode == 0


def _karar(d: Path, yollar=PROBE) -> dict[str, bool]:
    """yol → IGNORE mu (`-v -n`: negasyonla eşleşen yol AÇIK, eşleşmeyen AÇIK)."""
    r = subprocess.run(["git", "-C", str(d), "check-ignore", "--no-index", "-v", "-n", "--stdin", "-z"],
                       input=("\0".join(yollar) + "\0").encode("utf-8"), capture_output=True)
    if r.returncode not in (0, 1):
        print(f"[DURDU] KURULAMADI: git check-ignore rc={r.returncode} {r.stderr[:200]!r}")
        sys.exit(2)
    p = r.stdout.decode("utf-8").split("\0")
    return {p[i + 3]: bool(p[i + 2]) and not p[i + 2].startswith("!") for i in range(0, len(p) - 1, 4)}


def _kos(fn, d: Path) -> tuple[object, str]:
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        try:
            r = fn(d)
        except Exception as e:  # noqa: BLE001
            r = f"HATA {type(e).__name__}: {e}"
    return r, tampon.getvalue()


def _bol(metin: str, bas: str, son: str) -> tuple[str, str | None, str]:
    """(bom, blok-metni|None, proje-bölümü) — test edilen koddan BAĞIMSIZ ayrıştırma."""
    bom = "\ufeff" if metin.startswith("\ufeff") else ""
    sat = metin[len(bom):].splitlines(keepends=True)
    b = [i for i, s in enumerate(sat) if s.rstrip("\r\n") == bas]
    e = [i for i, s in enumerate(sat) if s.rstrip("\r\n") == son]
    if not b:
        return bom, None, "".join(sat)
    return bom, "".join(sat[b[0]:e[0] + 1]), "".join(sat[:b[0]] + sat[e[0] + 1:])


class _Vekil:
    """Modül vekili: verilen öznitelikleri değiştirir, gerisini gerçek modüle devreder."""

    def __init__(self, gercek, **degis) -> None:  # noqa: ANN001
        self._gercek, self._degis = gercek, degis

    def __getattr__(self, ad: str):  # noqa: ANN204
        return self._degis[ad] if ad in self._degis else getattr(self._gercek, ad)


@contextlib.contextmanager
def _yama(g: dict, **degis):  # noqa: ANN202
    """Test edilen modülün globallerini geçici değiştir (çıkışta geri al)."""
    eski = {k: g.get(k) for k in degis}
    g.update(degis)
    try:
        yield
    finally:
        g.update(eski)


def _salt_okunur(d: Path, kapat: bool) -> bool:
    """kapat=True: `.gitignore`'u yazılamaz yap (Windows: dosya özniteliği → os.replace
    PermissionError · POSIX: dizin 0o555 → geçici dosya yazılamaz; dosya özniteliği POSIX'te
    os.replace'i DURDURMAZ). Dönüş: koruma ETKİLİ mi (root/ACL'de değildir). kapat=False: geri al."""
    gi = d / ".gitignore"
    if not kapat:
        if os.name != "nt":
            os.chmod(d, 0o755)
        os.chmod(gi, stat.S_IREAD | stat.S_IWRITE)
        return True
    os.chmod(gi, stat.S_IREAD)
    if os.name != "nt":
        os.chmod(d, 0o555)
    return not os.access(gi if os.name == "nt" else d, os.W_OK)


def main() -> int:
    g, kaynak = _yukle()
    sen = g.get("gitignore_senkron")
    sab = g.get("gitignore_sablonu")
    tmp = Path(tempfile.mkdtemp(prefix="ts_gi_"))
    try:
        if sen is None or sab is None or "GI_BAS" not in g:
            kontrol("G* gitignore_senkron/gitignore_sablonu VAR", False, "yok (eski kod)")
        else:
            sablon = sab()
            bas, son = g["GI_BAS"], g["GI_SON"]

            def degismez(ad: str, metin: str, *, ek=None, hazirla=None) -> tuple[Path, str]:
                """Değişmez üçlüsü + vektöre özel `ek(d, once, sonra, cikti)` koşulu."""
                d = _repo(tmp, f"d{len(SONUC)}", metin.encode("utf-8"))
                if hazirla:
                    hazirla(d)
                b0, _, taban = _bol(metin, bas, son)
                (d / ".gitignore").write_bytes((b0 + taban).encode("utf-8"))
                once = _karar(d)
                (d / ".gitignore").write_bytes(metin.encode("utf-8"))
                r, out = _kos(sen, d)
                yeni_b = (d / ".gitignore").read_bytes()
                sonra = _karar(d)
                r2, _ = _kos(sen, d)
                ikinci_b = (d / ".gitignore").read_bytes()
                yeni = yeni_b.decode("utf-8")
                b1, blok, proje = _bol(yeni, bas, son)
                acilan = sorted(y for y in PROBE if once[y] and not sonra[y])
                yerlesim = (b1 == b0 and proje == taban and yeni.count(bas) <= 1
                            and (blok is None or yeni[len(b1):].startswith(blok)))
                ozel, ozel_detay = (ek(d, once, sonra, out) if ek else (True, ""))
                kontrol(f"D:{ad} ① acilan=0 ② proje bolumu bayt-es + blok basta ③ 2. kosum bayt-es"
                        + (" + vektore ozel" if ek else ""),
                        not acilan and yerlesim and r2 is False and ikinci_b == yeni_b and ozel,
                        f"acilan={acilan} yerlesim={yerlesim} r={r} r2={r2} "
                        f"idem={ikinci_b == yeni_b} ozel={ozel} {ozel_detay} out={out[-160:]!r}")
                return d, out

            # ── bug-gate vakaları (K*) + E* + C3 ──
            degismez("K1 conn/secret[12].template", "conn/secret[12].template\n",
                     ek=lambda d, o, s, _: (s["conn/secret1.template"] and s["conn/x.env"], ""))
            degismez("K2 *secret*", "*secret*\n",
                     ek=lambda d, o, s, _: (s["conn/my-secret.template"], ""))
            degismez("K3 conn/*_PRD.*", "conn/*_PRD.*\n",
                     ek=lambda d, o, s, _: (s["conn/sys_PRD.template"], ""))
            degismez("K4b *.zip/!keep*.zip/*secret*", "*.zip\n!keep*.zip\n*secret*\n",
                     ek=lambda d, o, s, _: (s["keep-secret.zip"] and not s["keep1.zip"],
                                            f"keep-secret={s['keep-secret.zip']} keep1={s['keep1.zip']}"))
            degismez("K4c sade tekrar", "*.zip\n!keep*.zip\nkeep-secret.zip\n",
                     ek=lambda d, o, s, _: (s["keep-secret.zip"] and not s["keep1.zip"], ""))
            degismez("K6 conn/**/x.template", "conn/**/x.template\n",
                     ek=lambda d, o, s, _: (s["conn/x.template"] and s["conn/a/b/x.template"], ""))
            degismez("E1 /conn/*", "/conn/*\n",
                     ek=lambda d, o, s, _: (s["conn/README.md"] and s["conn/.gitkeep"], ""))
            degismez("E2 conn/**", "conn/**\n",
                     ek=lambda d, o, s, _: (s["conn/.gitkeep"] and s["conn/a.template"], ""))
            degismez("E3 *.template", "*.template\n",
                     ek=lambda d, o, s, _: (s["conn/a.template"] and s["conn/x.env"], ""))
            degismez("E4 conn/*.env + !conn/README.md", "conn/*.env\n!conn/README.md\n",
                     ek=lambda d, o, s, _: (not s["conn/README.md"] and s["conn/mail_list.txt"]
                                            and s["conn/x.env"], ""))
            degismez("E5 conn/ dizin", "conn/\n",
                     ek=lambda d, o, s, _: (s["conn/README.md"] and s["conn/a.template"], ""))
            e6 = "/conn/*\n" + f"conn/*.env\n{bas}\nconn/*\n!conn/*.template\n!conn/README.md\n{son}\n"
            degismez("E6 bloklu dosyaya proje SONRADAN /conn/* (blok ortada → basa)", e6,
                     ek=lambda d, o, s, _: (s["conn/README.md"] and s["conn/a.template"], ""))
            elle = "# elle yazilmis — sablon disi\ncore/\nnode_modules/\n*.zip\n!keep.zip\n# son\n"
            degismez("C3 sablon-disi elle yazilmis", elle,
                     ek=lambda d, o, s, _: (not s["keep.zip"] and s["yedek.zip"] and s["conn/x.env"]
                                            and b"\n/core/\n" in (d / ".gitignore").read_bytes(), ""))

            # ── yerleşim / satır sonu / BOM ──
            sir = ("conn/.gmail_app_password", "conn/mail_list.txt")
            degismez("G1 bayat (Q241 oncesi) LF", BAYAT,
                     ek=lambda d, o, s, _: (all(not o[y] and s[y] for y in sir) and s["conn/x.env"]
                                            and s["conn/DEV.conn_adt"] and not s["conn/a.template"]
                                            and b"\nconn/*\n!conn/*.template\n" in (d / ".gitignore").read_bytes(),
                                            f"once={[o[y] for y in sir]} sonra={[s[y] for y in sir]}"))
            degismez("G2 CRLF", BAYAT.replace("\n", "\r\n"),
                     ek=lambda d, o, s, _: ((lambda b: b.count(b"\n") == b.count(b"\r\n")
                                             and (bas + "\r\n").encode() in b)((d / ".gitignore").read_bytes()), ""))
            degismez("G5 conn/* var, !conn/.gitkeep yok", BAYAT + "conn/*\n!conn/*.template\n!conn/README.md\n",
                     ek=lambda d, o, s, _: (s["conn/.gitkeep"] and not s["conn/README.md"], ""))
            on, arka = "/core/\n# kullanici satiri\n", "# arka\nbenim/ozel/\n"
            degismez("G6 ORTADAKI bayat blok → basa", on + f"{bas}\neski-satir-1\n{son}\n" + arka,
                     ek=lambda d, o, s, _: ((lambda t: "eski-satir-1" not in t and t.endswith(on + arka)
                                             and t.startswith(bas))((d / ".gitignore").read_text("utf-8")), ""))
            degismez("G6b SONDAKI blok (eski tasarim ciktisi) → basa",
                     BAYAT + f"\n{bas}\nconn/*\n!conn/*.template\n{son}\n",
                     ek=lambda d, o, s, _: ((d / ".gitignore").read_text("utf-8").startswith(bas), ""))
            degismez("G9 sonda satir sonu yok", BAYAT.rstrip("\n"),
                     ek=lambda d, o, s, _: ((d / ".gitignore").read_bytes().endswith(b"\n.claude/project.local.yaml"), ""))
            degismez("G14 BOM", "\ufeffbenim-ozel.txt\nconn/*.env\n",
                     ek=lambda d, o, s, _: ((d / ".gitignore").read_bytes().startswith(b"\xef\xbb\xbf" + bas.encode())
                                            and s["benim-ozel.txt"], f"benim-ozel={s['benim-ozel.txt']}"))
            tam = sablon.replace("{source_root}", "SOURCE_CODES")
            d15, out15 = degismez("G15 proje tum sablon satirlarini icerir → eski blok KALDIRILIR",
                                  f"{bas}\nconn/*\n{son}\n" + tam,
                                  ek=lambda d, o, s, _: ((d / ".gitignore").read_text("utf-8") == tam, ""))

            # ── G3 güncel ──
            d = _repo(tmp, "g3", tam.encode())
            r3, out3 = _kos(sen, d)
            kontrol("G3 guncel dosya → YAZILMAZ + 'eksik satır yok'",
                    r3 is False and (d / ".gitignore").read_bytes() == tam.encode() and "eksik satır yok" in out3,
                    f"r={r3} out={out3[-200:]!r}")

            # ── G7 bozuk işaret (dört biçim: çift başlangıç · ters sıra · yalnız başlangıç · yalnız bitiş) ──
            bozuk = f"/core/\n{bas}\nx\n{bas}\n{son}\n".encode()
            d = _repo(tmp, "g7", bozuk)
            r7, out7 = _kos(sen, d)
            kontrol("G7 bozuk isaret → YAZILMAZ + WARN BOZUK",
                    r7 is False and (d / ".gitignore").read_bytes() == bozuk and "BOZUK" in out7, out7[-200:])
            for ek7, metin7 in (("b ters sira (bitis once)", f"a\n{son}\nx\n{bas}\ny\n"),
                                ("c yalniz baslangic (1/0)", f"a\n{bas}\nx\n"),
                                ("d yalniz bitis (0/1)", f"a\n{son}\nx\n")):
                d = _repo(tmp, f"g7{ek7[0]}", metin7.encode())
                rr, oo = _kos(sen, d)
                kontrol(f"G7{ek7} → YAZILMAZ + WARN BOZUK",
                        rr is False and (d / ".gitignore").read_bytes() == metin7.encode() and "BOZUK" in oo,
                        f"r={rr} out={oo[-200:]!r}")

            # ── Y yazma yolu korunur: OSError → WARN, geçici dosya yok, .gitignore değişmez ──
            def _patla(*_a, **_k):
                raise PermissionError(13, "simule: salt-okunur hedef", ".gitignore")

            def _yazilamadi(ad: str, d: Path, r, out: str, once_b: bytes) -> None:
                kontrol(ad, r is False and (d / ".gitignore").read_bytes() == once_b
                        and not (d / ".gitignore.ix-tmp").exists() and "YAZILAMADI" in out,
                        f"r={r} ix-tmp={(d / '.gitignore.ix-tmp').exists()} out={out[-220:]!r}")

            d = _repo(tmp, "y1", BAYAT.encode())
            etkili = _salt_okunur(d, True)
            try:
                ry1, outy1 = _kos(sen, d)
            finally:
                _salt_okunur(d, False)
            if not etkili:
                kontrol("Y1 GERCEK salt-okunur .gitignore", False,
                        "KURULAMADI: salt-okunurluk etkisiz (root/ACL?) — vektor olculemedi")
            else:
                _yazilamadi("Y1 GERCEK salt-okunur .gitignore (Windows: dosya oznitelik · POSIX: dizin 0o555) "
                            "→ WARN YAZILAMADI + .ix-tmp YOK + dosya ayni", d, ry1, outy1, BAYAT.encode())
            d = _repo(tmp, "y2", BAYAT.encode())
            with _yama(g, os=_Vekil(os, replace=_patla)):
                ry2, outy2 = _kos(sen, d)
            _yazilamadi("Y2 os.replace OSError (her platform; gecici YAZILMIS) → temizlenir", d, ry2, outy2,
                        BAYAT.encode())

            # ── W2/W3 main uçtan uca: gitignore adımı başarısız → sonraki kablolama adımları KOŞAR ──
            def _main_kos(d: Path, **yama):
                kayit: list[str] = []
                adim = {ad: (lambda *_a, _ad=ad, **_k: kayit.append(_ad))
                        for ad in ("hookspath_core", "hookspath_proje", "sablon_sapmasi", "_core_index_yenile")}
                eski_argv = sys.argv
                sys.argv = ["team_setup.py", "--project", str(d), "--no-install", "--no-seed",
                            "--no-plugins", "--no-smoke"]
                try:
                    with _yama(g, junctions=lambda *_a, **_k: True, dosya_tamamla=lambda *_a, **_k: None,
                               **adim, **yama):
                        r, out = _kos(lambda _d: g["main"](), d)
                finally:
                    sys.argv = eski_argv
                return r, out, kayit

            beklenen = ["hookspath_core", "hookspath_proje", "sablon_sapmasi", "_core_index_yenile"]
            d = _repo(tmp, "w2", BAYAT.encode())
            rw2, outw2, kw2 = _main_kos(d, os=_Vekil(os, replace=_patla))
            kontrol("W2 main: .gitignore YAZILAMADI → exit 0 + hookspath/sablon_sapmasi/CORE-INDEX koştu + .ix-tmp YOK",
                    rw2 == 0 and kw2 == beklenen and "YAZILAMADI" in outw2
                    and not (d / ".gitignore.ix-tmp").exists(), f"r={rw2!r} adimlar={kw2} out={outw2[-200:]!r}")

            def _bozul(*_a, **_k):
                raise RuntimeError("simule: beklenmeyen")
            d = _repo(tmp, "w3", BAYAT.encode())
            rw3, outw3, kw3 = _main_kos(d, gitignore_blok_hesapla=_bozul)
            kontrol("W3 main: gitignore adimi beklenmeyen istisna → WARN DURDU + exit 0 + sonraki adimlar koştu",
                    rw3 == 0 and kw3 == beklenen and "beklenmeyen hatayla DURDU" in outw3,
                    f"r={rw3!r} adimlar={kw3} out={outw3[-200:]!r}")

            # ── OL1 görünürlük ölçülemedi: `git ls-files -o` zaman aşımı → WARN ÖLÇÜLEMEDİ ──
            def _ls_asim(args, *a, **k):
                if "ls-files" in args:
                    raise subprocess.TimeoutExpired(args, 120)
                return subprocess.run(args, *a, **k)
            d = _repo(tmp, "ol1", BAYAT.encode())
            with _yama(g, subprocess=_Vekil(subprocess, run=_ls_asim)):
                rol, outol = _kos(sen, d)
            kontrol("OL1 ls-files zaman asimi → yazar + WARN 'görünürlüğü ÖLÇÜLEMEDİ'",
                    rol is True and "görünürlüğü ÖLÇÜLEMEDİ" in outol and "temiz demek DEĞİL" in outol,
                    f"r={rol} out={outol[-220:]!r}")

            # ── G8 source_root yok ──
            d = _repo(tmp, "g8", BAYAT.encode(), source_root=None)
            r8, out8 = _kos(sen, d)
            t8 = (d / ".gitignore").read_text(encoding="utf-8")
            kontrol("G8 source_root yok → {source_root} satirlari atlanir, literal yazilmaz + not",
                    r8 is True and "{source_root}" not in t8 and "source_root yok" in out8, out8[-200:])

            # ── G10 yeni gizlenen dosya görünür ──
            d = _repo(tmp, "g10", BAYAT.encode())
            (d / "yedek.zip").write_bytes(b"PK")
            r10, out10 = _kos(sen, d)
            kontrol("G10 kokte izlenmeyen yedek.zip → WARN 'artık IGNORE' listesinde",
                    "artık IGNORE" in out10 and "yedek.zip" in out10, out10[-300:])

            # ── G11 tek kaynak ──
            ip = REPO / "scripts" / "init_project.py"
            agac = ast.parse(ip.read_text(encoding="utf-8"))
            bag = next((ast.literal_eval(n.value) for n in agac.body if isinstance(n, ast.Assign)
                        and any(getattr(h, "id", "") == "GITIGNORE" for h in n.targets)), None)
            kontrol("G11 sablon TEK KAYNAK: gitignore_sablonu() == init_project.GITIGNORE",
                    bag is not None and sablon == bag and "conn/*" in sablon, "")

            # ── G12 / G13 ──
            d = _repo(tmp, "g12", None)
            r12, _ = _kos(sen, d)
            kontrol("G12 .gitignore yok + git → bloklu dosya dogar, conn/x.env + /core/ IGNORE",
                    r12 is True and (d / ".gitignore").is_file() and _ignore(d, "conn/x.env")
                    and _ignore(d, "core/x.md"), f"r={r12}")
            d = _repo(tmp, "g13", None, git=False)
            r13, out13 = _kos(sen, d)
            kontrol("G13 git degil + .gitignore yok → dosya YARATILMAZ",
                    r13 is False and not (d / ".gitignore").exists(), f"r={r13}")

            # ── S2 SINIR ②: dışlanmış dizin altındaki proje negasyonu (sıkılaştırma, GÖRÜNÜR) ──
            def _mine(d: Path) -> None:
                (d / ".claude" / "agents").mkdir(parents=True)
                (d / ".claude" / "agents" / "mine.md").write_bytes(b"x")
            degismez("S2 SINIR ② !.claude/agents/mine.md + blok .claude/agents/", "!.claude/agents/mine.md\n",
                     hazirla=_mine,
                     ek=lambda d, o, s, out: (not o[".claude/agents/mine.md"] and s[".claude/agents/mine.md"]
                                              and "artık IGNORE" in out and ".claude/agents/" in out
                                              and "yeniden dahil EDEMEZ" in out, ""))

            # ── S1 SINIR ①: .git/info/exclude ile gizlenen yolu bloktaki şablon negasyonu açar → WARN ──
            d = _repo(tmp, "s1", b"benim/\n")
            (d / ".git" / "info").mkdir(parents=True, exist_ok=True)
            (d / ".git" / "info" / "exclude").write_bytes(b"conn/README.md\n")
            (d / "conn").mkdir()
            (d / "conn" / "README.md").write_bytes(b"x")
            once_s1 = _ignore(d, "conn/README.md")
            r_s1, out_s1 = _kos(sen, d)
            kontrol("S1 SINIR ① info/exclude'un gizledigi README blok negasyonuyla acilir → 'GÖRÜNÜR' WARN",
                    r_s1 is True and once_s1 and not _ignore(d, "conn/README.md")
                    and "GÖRÜNÜR" in out_s1 and "conn/README.md" in out_s1 and "excludes" in out_s1
                    and "SINIR d" not in out_s1,  # eski blok YOK ⇒ (d) nedeni metne girmez
                    f"once={once_s1} out={out_s1[-300:]!r}")

            # ── S3/S4 SINIR d (çerçeve): değişmez projenin KENDİ satırlarına göre — dosyanın O ANKİ
            #    hâline göre değil. Eski blok başta değilse yol AÇILABİLİR; GÖRÜNÜR WARN doğru nedenle.
            def _s3_neden(out: str) -> bool:
                return "GÖRÜNÜR" in out and "SINIR d" in out and "excludes" in out  # iki neden birlikte

            durum: dict[str, bool] = {}

            def _x_env(d: Path) -> None:
                (d / "conn").mkdir()
                (d / "conn" / "x.env").write_bytes(b"x")
                durum["s3_once"] = _ignore(d, "conn/x.env")  # dosyanın O ANKİ hâli (blok ortada)
            degismez("S3 SINIR d ustteki proje negasyonu + ortadaki blok → conn/x.env ACILIR, GÖRÜNÜR WARN (d)",
                     "!conn/x.env\n" + f"{bas}\nconn/*\n{son}\n" + "/core/\n", hazirla=_x_env,
                     ek=lambda d, o, s, out: (durum.get("s3_once") is True and not s["conn/x.env"]
                                              and "conn/x.env" in out and _s3_neden(out) and "(1a)" in out,
                                              f"o_anki_once={durum.get('s3_once')} sonra={s['conn/x.env']}"))

            def _eski_gizli(d: Path) -> None:
                (d / "eski-gizli.txt").write_bytes(b"x")
                durum["s4_once"] = _ignore(d, "eski-gizli.txt")
            # S4'te eski blok dosyanın BAŞINDADIR ⇒ metin "başta değildi" ÖNCÜLÜNÜ ileri süremez;
            # (1b) alt nedeni (şablondan çıkarılan satır) kendi başına söylenmeli (PR #326 gate-3 L1).
            degismez("S4 SINIR d sablondan cikan satir (eski blok BASTA) → yalniz blogun gizledigi yol acilir, "
                     "neden metni 'basta degildi' onculu ileri surmez",
                     f"{bas}\neski-gizli.txt\n{son}\n/core/\n", hazirla=_eski_gizli,
                     ek=lambda d, o, s, out: (durum.get("s4_once") is True
                                              and not _ignore(d, "eski-gizli.txt")
                                              and "eski-gizli.txt" in out and _s3_neden(out)
                                              and "başta değildi" not in out and "(1b)" in out
                                              and "şablondan çıkarılan" in out,
                                              f"o_anki_once={durum.get('s4_once')} "
                                              f"oncul={'başta değildi' in out} 1b={'(1b)' in out}"))

            # ── S5 ÖNERİ: proje negasyonu sır yolunu açıyorsa blok onu KAPATMAZ (projenin kararı) ──
            degismez("S5 proje !conn/.gmail_app_password → acik KALIR (blok kapatmaz)",
                     "conn/*\n!conn/.gmail_app_password\n",
                     ek=lambda d, o, s, _: (not s["conn/.gmail_app_password"] and s["conn/mail_list.txt"], ""))

            # ── M1 makineden bağımsız: global excludesFile varken blok bayt-eş ──
            ex = tmp / "global_excludes"
            ex.write_bytes(b"*.zip\nconn/\n")
            cfg = tmp / "global_cfg"
            cfg.write_bytes(f"[core]\n\texcludesFile = {ex.as_posix()}\n".encode())
            ref = _repo(tmp, "m1a", b"/conn/*\n*.template\n")
            _kos(sen, ref)
            d = _repo(tmp, "m1b", b"/conn/*\n*.template\n")
            os.environ["GIT_CONFIG_GLOBAL"] = str(cfg)
            try:
                etkin = _ignore(d, "conn/zz")  # global config GERÇEKTEN okunuyor mu (kontrol)
                _kos(sen, d)
            finally:
                os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
            kontrol("M1 global core.excludesFile VARKEN blok bayt-es (makineden bagimsiz)",
                    etkin and (d / ".gitignore").read_bytes() == (ref / ".gitignore").read_bytes(),
                    f"global_etkin={etkin}")

            # ── KP KAPSAM satırı her koşumda ──
            # Her ayak ayrı çivilenir: ① (a) metni · ② · ③ çerçeve · ÖNERİ · üst-dizin niteleyicisi.
            ayaklar = ("KAPSAMI", "AÇAMAZ", "ile gizlenen yolu açabilir", "yalnız MEVCUT izlenmeyen",
                       "yeniden dahil EDEMEZ", "O ANKİ", "üst dizini blok tarafından dışlanmadıkça",
                       "sır yolunu açıyorsa blok onu kapatmaz")
            kp = {"yazim": out15, "degisiklik-yok": out3, "bozuk": out7, "atlandi": out13, "yazilamadi": outy2}
            eksik = [f"{k}:{a}" for k, v in kp.items() for a in ayaklar if a not in v]
            kontrol("KP KAPSAM satiri her kosumda, her ayagiyla (yazim · degisiklik yok · bozuk · atlandi · yazilamadi)",
                    not eksik, f"eksik={eksik[:6]}")

        # W1 kablolama (AST: main içinde dosya_tamamla'dan SONRA, bayrakla korunan çağrı)
        try:
            agac = ast.parse(kaynak)
            mn = next(n for n in agac.body if isinstance(n, ast.FunctionDef) and n.name == "main")
            cagrilar = [(n.lineno, n.func.id) for n in ast.walk(mn)
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                        and n.func.id in ("dosya_tamamla", "gitignore_senkron")]
            sira = [ad for _, ad in sorted(cagrilar)]
            bayrak = "--no-gitignore" in kaynak and "a.no_gitignore" in kaynak
            kontrol("W1 KABLOLAMA: main dosya_tamamla → gitignore_senkron (bayrakla korunur)",
                    "gitignore_senkron" in sira and sira.index("gitignore_senkron") > sira.index("dosya_tamamla")
                    and bayrak, f"sira={sira} bayrak={bayrak}")
        except Exception as e:  # noqa: BLE001
            kontrol("W1 KABLOLAMA", False, f"{type(e).__name__}: {e}")
    finally:
        _sil(tmp)

    ok = sum(1 for _, k, _ in SONUC if k)
    etiket = f" [TABAN {TABAN}]" if TABAN else (f" [{' '.join(sorted(KIP))}]" if KIP else "")
    print(f"\nteam_setup_gitignore_blok{etiket}: {ok}/{len(SONUC)} PASS")
    return 0 if ok == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
