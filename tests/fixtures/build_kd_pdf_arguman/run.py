#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_kd_pdf_arguman — `scripts/build_kd_pdf.py` argüman sözleşmesi + davranış eşdeğerliği (B85, 2026-10-18).

VAKA: betik `sys.argv` okumuyordu ve tüm gövdesi modül seviyesindeydi; `--help` dahil HER çağrı
(ve import) normal çalıştırmaydı → project.yaml'daki dizinlere md geri yazımı + kırpma + HTML +
webapp/help senkronu. İki kez (2026-10-05, 2026-10-18) bir tüketici projenin kapalı paketindeki
görseller yeniden yazıldı. Girdi/çıktı adı da tek bir tüketici KD'sine sabitti.

Her vektör TAZE bir sahte proje ağacında koşar (`project.yaml` kd_docs_dir/kd_help_dir dolu,
help/ dizini VAR, kökte ham kd-01-liste.png VAR) — yani eski kod yazacak her şeyi bulur.
"Dokunulmadı" = ağaçtaki her dosyanın (boyut, mtime_ns, sha256) + dizin kümesi önce == sonra.

SENARYOLAR (S/H/Y/B/I/D: yalnız standart kütüphane — CI'da koşar; G/E: markdown + PIL ister,
yoksa ATLANDI; E ayrıca taban commit'i ister)
  S1  araç kaynağında sabit KD dosya adı (`KD-XX-NNN`) yok                      [--mutasyon-eski-kod]
  H1  `--help` → exit 0, kullanım basılır, ağaçta HİÇBİR değişiklik yok        [--mutasyon-eski-kod]
  H1b geçerli argümanlar + `-h` → exit 0, değişiklik yok
  H2  argümansız → exit 2, değişiklik yok                                      [--mutasyon-eski-kod]
  H3  olmayan girdi → exit 2, değişiklik yok              [--mutasyon-eski-kod, --mutasyon-girdi-kontrol]
  H3b olmayan çıktı dizini (+ --md-yerinde-yaz) → exit 2, md DAHİL değişiklik yok
  H3c girdi == çıktı → exit 2, değişiklik yok
  Y1  olmayan --yardim-dizini → exit 2, değişiklik yok                         [--mutasyon-sessiz-yardim]
  Y2  olmayan --kirp-kaynak → exit 2, değişiklik yok
  B1  bilinmeyen bayrak + kısaltılmış bayrak (`--yardim`) → exit 2, değişiklik yok
  I1  modülü import etmek hiçbir şey yazmaz (exit 0)                           [--mutasyon-eski-kod]
  D1  markdown/PIL YOKKEN `--help` 0 · argümansız 2 · olmayan girdi 2         [--mutasyon-erken-import]
  G1  geçerli girdi → yalnız <cikti.html> doğar; md bayt-aynı, help/ ve kırpma dokunulmadı,
      <title> = çıktı adının gövdesi, figür sayısı beklenen              [--mutasyon-yerinde-varsayilan]
  E1  EŞDEĞERLİK (kontrol grubu — eski kodda da geçer): eski kod (taban `git show`) argümansız ↔
      yeni kod tüm bayraklarla (`--baslik <eski başlık> --md-yerinde-yaz --kirp-kaynak --yardim-dizini`)
      → HTML · geri yazılan md · help HTML · screenshots/ ve help/screenshots/ PNG'leri BAYT-AYNI
                                                                          [--mutasyon-baslik-yok-sayilir]
  E2  yerinde yazma kapalıyken HTML, E1'deki HTML ile bayt-aynı (geri yazma HTML'i etkilemez)

Eski başlık ve eski dosya adları taban kaynağından/çıktısından ÇALIŞMA ANINDA okunur — bu
fixture'a tüketici proje adı yazılmaz.

KAPSAM BEYANI: PDF adımı (html_to_pdf.js) ve ```mermaid render'ı (mmdc) ÖLÇÜLMEZ — girdi md'de
mermaid bloğu yoktur; ikisi de bu değişiklikte dokunulmayan modüllerdedir.

Koşum:  python tests/fixtures/build_kd_pdf_arguman/run.py [--mutasyon-<kip>]
"""
import hashlib
import importlib.util
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

if sys.platform == "win32":
    for _a in (sys.stdout, sys.stderr):
        try:
            _a.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

KOK = Path(__file__).resolve().parents[3]
ARAC = KOK / "scripts" / "build_kd_pdf.py"
GIRDI = Path(__file__).resolve().parent / "KD-SD-001_Ornek_Kullanici_Kilavuzu.md"
TABAN_SHA = "998e739"  # argüman okumayan son sürüm (main'de; CI fetch-depth 0)

MUTASYON = {
    # olmayan --yardim-dizini denetimini söker → Y1 düşmeli (bağımlılıksız)
    "--mutasyon-sessiz-yardim": (
        '    if a.yardim_dizini is not None and not os.path.isdir(a.yardim_dizini):\n'
        '        p.error("--yardim-dizini yok: %s" % a.yardim_dizini)\n', ''),
    # girdi varlık denetimini söker → H3 düşmeli
    "--mutasyon-girdi-kontrol": (
        '    if not os.path.isfile(a.girdi_md):\n'
        '        p.error("girdi md bulunamadı: %s" % a.girdi_md)\n', ''),
    # ağır import'u modül başına taşır → D1 düşmeli
    "--mutasyon-erken-import": ('import os\nimport re\nimport sys\n',
                                'import os\nimport re\nimport sys\nimport markdown\n'),
    # yerinde yazmayı varsayılan yapar → G1 düşmeli (bağımlılık ister)
    "--mutasyon-yerinde-varsayilan": ('    if a.md_yerinde_yaz:\n', '    if True:\n'),
    # --baslik yok sayılır → E1 düşmeli (bağımlılık + taban ister)
    "--mutasyon-baslik-yok-sayilir": ('a.baslik if a.baslik is not None else ', ''),
    # eski kod (taban) → S1, H1, H2, H3, I1, D1 düşmeli
    "--mutasyon-eski-kod": None,
}
GECERLI_KIP = ("--mutasyon-sessiz-yardim", "--mutasyon-girdi-kontrol", "--mutasyon-erken-import",
               "--mutasyon-yerinde-varsayilan", "--mutasyon-baslik-yok-sayilir", "--mutasyon-eski-kod")
_kip = [a for a in sys.argv[1:] if a.startswith("--")]
for _a in _kip:
    if _a not in GECERLI_KIP:
        print(f"[DURDU] bilinmeyen kip: {_a}")
        sys.exit(2)
KIP = _kip[0] if _kip else None

TMP = Path(tempfile.mkdtemp(prefix="kdpdf_fx_"))
SONUC, ATLANAN = [], []


def _sil(p):
    """Windows R özniteliği rmtree'yi durdurur → izni açıp yeniden dene."""
    def _hata(fn, yol, _):
        try:
            os.chmod(yol, stat.S_IWRITE)
            fn(yol)
        except Exception:
            pass
    if Path(p).exists():
        shutil.rmtree(p, onerror=_hata)


def kontrol(ad, ok, detay=""):
    SONUC.append((ad, bool(ok), detay))


def _taban_kaynak():
    r = subprocess.run(["git", "-C", str(KOK), "show", f"{TABAN_SHA}:scripts/build_kd_pdf.py"],
                       capture_output=True)
    return r.stdout.decode("utf-8") if r.returncode == 0 and r.stdout else None


TABAN = _taban_kaynak()
DEPS = all(importlib.util.find_spec(m) is not None for m in ("markdown", "PIL"))


def _arac_yolu():
    """Koşulacak aracın yolu: taban/mutant geçici dosyaya yazılır, normal kipte GERÇEK yol."""
    if KIP is None:
        return ARAC
    if KIP == "--mutasyon-eski-kod":
        if TABAN is None:
            print(f"[KURULAMADI] taban {TABAN_SHA} okunamadı (git geçmişi yok) — mutasyon ÖLÇÜLMEDİ")
            sys.exit(3)
        src = TABAN
    else:
        eski, yeni = MUTASYON[KIP]
        src = ARAC.read_text(encoding="utf-8")
        if src.count(eski) != 1:
            print(f"[DURDU] mutasyon çapası bulunamadı/çoğul ({KIP}): {eski!r}")
            sys.exit(3)
        src = src.replace(eski, yeni)
    d = TMP / "arac"
    d.mkdir(exist_ok=True)
    p = d / "build_kd_pdf.py"
    p.write_bytes(src.encode("utf-8"))
    return p


A = _arac_yolu()
_TABAN_YOLU = None
if TABAN is not None:
    _TABAN_YOLU = TMP / "taban" / "build_kd_pdf.py"
    _TABAN_YOLU.parent.mkdir(exist_ok=True)
    _TABAN_YOLU.write_bytes(TABAN.encode("utf-8"))
ESKI_MD = ESKI_HTML = None
if TABAN is not None:
    _m = re.search(r"MD = os\.path\.join\(DOCS, '([^']+)'\)", TABAN)
    _h = re.search(r"HTML = os\.path\.join\(DOCS, '([^']+)'\)", TABAN)
    ESKI_MD, ESKI_HTML = (_m.group(1) if _m else None), (_h.group(1) if _h else None)

# Sahte bağımlılık dizini: markdown / PIL import'u ImportError verir (D1)
SAHTE_DEP = TMP / "sahte_dep"
for _ad in ("markdown", "PIL"):
    (SAHTE_DEP / _ad).mkdir(parents=True, exist_ok=True)
    (SAHTE_DEP / _ad / "__init__.py").write_text(f"raise ImportError('sahte: {_ad} yok')\n", encoding="utf-8")

_PNG_SAYAC = [0]


def _png(yol, beyaz_kenar=True):
    """Kırpma için beyaz kenarlı küçük PNG; PIL yoksa sabit 1x1 PNG baytı."""
    yol.parent.mkdir(parents=True, exist_ok=True)
    if DEPS:
        from PIL import Image
        im = Image.new("RGB", (80, 60), (255, 255, 255))
        for x in range(30, 50):
            for y in range(20, 40):
                im.putpixel((x, y), (20, 60, 120))
        im.save(yol, "PNG")
    else:
        yol.write_bytes(bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
            "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"))


def kur(ad, ek_md_adi=None):
    """Taze sahte proje: project.yaml + docs/(md, screenshots/onceki.png) + help/ + kökte ham PNG."""
    r = TMP / ad
    (r / "docs" / "screenshots").mkdir(parents=True)
    (r / "help").mkdir()
    (r / "project.yaml").write_bytes(b"kd_docs_dir: docs\nkd_help_dir: help\n")
    icerik = GIRDI.read_bytes()
    (r / "docs" / GIRDI.name).write_bytes(icerik)
    if ek_md_adi:
        (r / "docs" / ek_md_adi).write_bytes(icerik)
    _png(r / "docs" / "screenshots" / "onceki.png")
    _png(r / "kd-01-liste.png")
    return r


def foto(r):
    out = {}
    for kok, dizinler, dosyalar in os.walk(r):
        for d in dizinler:
            out[os.path.relpath(os.path.join(kok, d), r).replace("\\", "/") + "/"] = "DIR"
        for f in dosyalar:
            p = os.path.join(kok, f)
            st = os.stat(p)
            out[os.path.relpath(p, r).replace("\\", "/")] = (
                st.st_size, st.st_mtime_ns, hashlib.sha256(Path(p).read_bytes()).hexdigest())
    return out


def fark(once, sonra):
    return sorted(k for k in set(once) | set(sonra) if once.get(k) != sonra.get(k))


def kos(arac, args, cwd, ek_pythonpath=None, kod=None):
    env = dict(os.environ)
    for k in ("PYTHONUTF8", "PYTHONIOENCODING"):
        env.pop(k, None)          # Windows'ta gerçek cp1252 pipe koşulu
    env["CLAUDE_PROJECT_DIR"] = str(cwd)
    yollar = ([str(ek_pythonpath)] if ek_pythonpath else []) + [str(KOK / "scripts")]
    env["PYTHONPATH"] = os.pathsep.join(yollar)
    komut = [sys.executable, "-c", kod] if kod else [sys.executable, str(arac)] + list(args)
    r = subprocess.run(komut, cwd=str(cwd), env=env, capture_output=True, timeout=300)
    dec = lambda b: b.decode("utf-8", errors="replace")
    return r.returncode, dec(r.stdout), dec(r.stderr)


def dokunmaz(ad, args, beklenen_rc, metin=None, ek_pythonpath=None, md_adi_eski=False):
    r = kur(ad.split()[0], ek_md_adi=ESKI_MD if (KIP == "--mutasyon-eski-kod" or md_adi_eski) else None)
    once = foto(r)
    rc, out, err = kos(A, [x.replace("{R}", str(r)) for x in args], r, ek_pythonpath)
    sonra = foto(r)
    df = fark(once, sonra)
    ok = rc == beklenen_rc and not df and (metin is None or metin in out + err)
    kontrol(ad, ok, f"rc={rc} (beklenen {beklenen_rc}) degisen={df[:8]} out={out[-160:]!r} err={err[-200:]!r}")


MD_ARG = f"docs/{GIRDI.name}"
HTML_ARG = f"docs/{GIRDI.stem}.html"

try:
    # ── S: statik ────────────────────────────────────────────────────────────
    src = Path(A).read_text(encoding="utf-8")
    sabit = re.findall(r"KD-[A-Z]{2}-\d{3}", src)
    kontrol("S1 araç kaynağında sabit KD dosya adı yok", not sabit, f"bulunan={sabit[:4]}")

    # ── H/Y/B: kullanım sözleşmesi (bağımlılıksız) ───────────────────────────
    dokunmaz("H1 --help: exit 0 + kullanım, HİÇBİR dosya değişmez", ["--help"], 0, metin="--yardim-dizini")
    dokunmaz("H1b geçerli argümanlar + -h: exit 0, değişiklik yok", [MD_ARG, HTML_ARG, "-h"], 0,
             metin="--yardim-dizini")
    dokunmaz("H2 argümansız: exit 2, değişiklik yok", [], 2, metin="usage")
    dokunmaz("H3 olmayan girdi: exit 2, değişiklik yok", ["docs/YOK.md", HTML_ARG], 2)
    dokunmaz("H3b olmayan çıktı dizini (+--md-yerinde-yaz): exit 2, md dahil değişiklik yok",
             [MD_ARG, "yok_dizin/c.html", "--md-yerinde-yaz"], 2)
    dokunmaz("H3c girdi == çıktı: exit 2, değişiklik yok", [MD_ARG, MD_ARG], 2)
    dokunmaz("Y1 olmayan --yardim-dizini: exit 2, değişiklik yok",
             [MD_ARG, HTML_ARG, "--yardim-dizini", "yok_help"], 2)
    dokunmaz("Y2 olmayan --kirp-kaynak: exit 2, değişiklik yok",
             [MD_ARG, HTML_ARG, "--kirp-kaynak", "yok_kirp"], 2)
    dokunmaz("B1a bilinmeyen bayrak: exit 2, değişiklik yok", [MD_ARG, HTML_ARG, "--zirva"], 2)
    dokunmaz("B1b kısaltılmış bayrak (--yardim): exit 2, değişiklik yok",
             [MD_ARG, HTML_ARG, "--yardim", "help"], 2)

    # ── I: import yan etkisiz ────────────────────────────────────────────────
    r = kur("i1", ek_md_adi=ESKI_MD if KIP == "--mutasyon-eski-kod" else None)
    once = foto(r)
    kod = ("import importlib.util,sys\n"
           f"s=importlib.util.spec_from_file_location('kdpdf_fx', r'{A}')\n"
           "m=importlib.util.module_from_spec(s); s.loader.exec_module(m)\n")
    rc, out, err = kos(A, [], r, kod=kod)
    df = fark(once, foto(r))
    kontrol("I1 modülü import etmek hiçbir şey yazmaz", rc == 0 and not df,
            f"rc={rc} degisen={df[:8]} err={err[-200:]!r}")

    # ── D: bağımlılık yokken kullanım yolu ───────────────────────────────────
    sonuc_d = []
    for etiket, args, bek in (("help", ["--help"], 0), ("arg-yok", [], 2), ("girdi-yok", ["docs/YOK.md", HTML_ARG], 2)):
        r = kur(f"d1-{etiket}", ek_md_adi=ESKI_MD if KIP == "--mutasyon-eski-kod" else None)
        once = foto(r)
        rc, out, err = kos(A, args, r, ek_pythonpath=SAHTE_DEP)
        sonuc_d.append((etiket, rc, bek, fark(once, foto(r)), err[-160:]))
    kontrol("D1 markdown/PIL yokken --help 0 · argümansız 2 · olmayan girdi 2 (değişiklik yok)",
            all(rc == bek and not df for _, rc, bek, df, _ in sonuc_d), f"{sonuc_d}")

    # ── G: geçerli girdi (markdown + PIL) ────────────────────────────────────
    if not DEPS:
        ATLANAN.append(("G1", "markdown/PIL kurulu değil"))
    else:
        r = kur("g1", ek_md_adi=ESKI_MD if KIP == "--mutasyon-eski-kod" else None)
        once = foto(r)
        rc, out, err = kos(A, [MD_ARG, HTML_ARG], r)
        sonra = foto(r)
        df = fark(once, sonra)
        h = (r / HTML_ARG)
        html = h.read_text(encoding="utf-8") if h.exists() else ""
        baslik = re.search(r"<title>(.*?)</title>", html)
        kontrol("G1 geçerli girdi: yalnız çıktı HTML doğar; md/help/kırpma dokunulmadı; başlık = çıktı adı",
                rc == 0 and df == [HTML_ARG] and baslik and baslik.group(1) == GIRDI.stem
                and html.count("<figure>") == 9 and "kd-07-portal.png" in html
                and 'id="1-bu-kilavuz-hakkinda"' in html and "①" not in html,
                f"rc={rc} degisen={df} baslik={baslik.group(1) if baslik else None} "
                f"figure={html.count('<figure>')} err={err[-200:]!r}")

    # ── E: eşdeğerlik (kontrol grubu) ────────────────────────────────────────
    if not DEPS:
        ATLANAN.append(("E1/E2", "markdown/PIL kurulu değil"))
    elif TABAN is None or not (ESKI_MD and ESKI_HTML):
        ATLANAN.append(("E1/E2", f"taban {TABAN_SHA} okunamadı ya da eski ad sabitleri bulunamadı"))
    else:
        ea = kur("e-eski", ek_md_adi=ESKI_MD)
        rc_e, out_e, err_e = kos(_TABAN_YOLU, [], ea)
        eski_html_b = (ea / "docs" / ESKI_HTML).read_bytes() if (ea / "docs" / ESKI_HTML).exists() else b""
        eb = re.search(r"<title>(.*?)</title>", eski_html_b.decode("utf-8", "replace"))
        eski_baslik = eb.group(1) if eb else ""

        ya = kur("e-yeni", ek_md_adi=ESKI_MD)
        rc_y, out_y, err_y = kos(A, [f"docs/{ESKI_MD}", f"docs/{ESKI_HTML}", "--baslik", eski_baslik,
                                     "--md-yerinde-yaz", "--kirp-kaynak", str(ya),
                                     "--yardim-dizini", str(ya / "help")], ya)

        def oku(r, rel):
            p = r / rel
            return p.read_bytes() if p.exists() else None

        def pngler(r, rel):
            d = r / rel
            return {p.name: p.read_bytes() for p in sorted(d.glob("*.png"))} if d.is_dir() else {}

        esler = {
            "html": (oku(ea, f"docs/{ESKI_HTML}"), oku(ya, f"docs/{ESKI_HTML}")),
            "md": (oku(ea, f"docs/{ESKI_MD}"), oku(ya, f"docs/{ESKI_MD}")),
            "help-html": (oku(ea, "help/kullanici-kilavuzu.html"), oku(ya, "help/kullanici-kilavuzu.html")),
            "screenshots": (pngler(ea, "docs/screenshots"), pngler(ya, "docs/screenshots")),
            "help-screenshots": (pngler(ea, "help/screenshots"), pngler(ya, "help/screenshots")),
        }
        farkli = [k for k, (x, y) in esler.items() if x != y or x in (None, {}, b"")]
        md_degisti = esler["md"][0] != GIRDI.read_bytes()
        kirpildi = "kd-01-liste.png" in esler["screenshots"][0]
        kontrol("E1 eşdeğerlik: eski (argümansız) ↔ yeni (tüm bayraklar) HTML/md/help/PNG bayt-aynı",
                rc_e == 0 and rc_y == 0 and not farkli and bool(eski_baslik) and md_degisti and kirpildi,
                f"rc_eski={rc_e} rc_yeni={rc_y} farkli={farkli} baslik_var={bool(eski_baslik)} "
                f"md_geri_yazildi={md_degisti} kirpildi={kirpildi} err_y={err_y[-200:]!r} err_e={err_e[-200:]!r}")

        yb = kur("e2", ek_md_adi=ESKI_MD)
        rc2, _, err2 = kos(A, [f"docs/{ESKI_MD}", f"docs/{ESKI_HTML}", "--baslik", eski_baslik], yb)
        kontrol("E2 yerinde yazma kapalı: HTML E1 ile bayt-aynı, md dokunulmadı",
                rc2 == 0 and oku(yb, f"docs/{ESKI_HTML}") == esler["html"][0]
                and oku(yb, f"docs/{ESKI_MD}") == GIRDI.read_bytes(),
                f"rc={rc2} err={err2[-200:]!r}")
finally:
    _sil(TMP)

# ── rapor ────────────────────────────────────────────────────────────────────
print(f"build_kd_pdf_arguman{(' ' + KIP) if KIP else ''}")
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok:
        print(f"         -> {detay}")
for ad, sebep in ATLANAN:
    print(f"  [ATLANDI] {ad} — {sebep}")
print("  KAPSAM: PDF adımı (html_to_pdf.js) ve mermaid render (mmdc) ÖLÇÜLMEDİ — bu değişikliğin dışında")
gecen = sum(1 for _, ok, _ in SONUC if ok)
print(f"TOPLAM: {gecen}/{len(SONUC)} PASS · {len(ATLANAN)} ATLANDI (ölçülmedi; PASS sayılmaz)")
sys.exit(0 if gecen == len(SONUC) else 1)
