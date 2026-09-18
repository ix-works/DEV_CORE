#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GENERICIZE MUAFIYETI — SATIR BAZLI + GEREKCE ZORUNLU (Q329, 2026-09-18).

NEDEN BU KORPUS VAR
-------------------
`core_precommit` sizinti kapisinin muafiyeti DOSYA bazliydi (`SCAN_EXEMPT`): uc dosya
(`pre_tool_guard` · `core_precommit` · `genericize_common`) taramadan KOMPLE muafti.
Gerekce *"kendileri desen tanimlar"* idi ve desen LITERALLERI icin dogrudur — ama
muafiyet dosyanin TAMAMINI kapsadigi icin o dosyalarin DUZ-YAZI yorum ve
docstring'leri de muaf oluyordu. Bu kor noktadan **8 gercek kimlik izi** gecti; en
eskisi **38 gun** public cekirdekte kaldi (icerik #267 ile temizlendi; muafiyetin
KENDISI bu degisikligin konusu).

⭐ SINIF (korpusun civiledigi sey tek vaka degil BUDUR): *bilincli bir muafiyetin
gerekcesi bir ALT-KUMEYE (desen literalleri) uyarken muafiyet UST-KUMEYE (dosyanin
tamami) yazilirsa, muafiyet kor noktaya doner — ve dokunulmazligi yuzunden en uzun
yasayan kor nokta olur.*

YENI SOZLESME (uc ayagi da burada olculur):
  1. Muafiyet SATIR bazlidir  -> `genericize-allow: <gerekce>` YALNIZ kendi satirini
     muaf tutar; blok/bolge/dosya muafiyeti YOKTUR.
  2. GEREKCE ZORUNLUDUR       -> bos/yetersiz gerekce = isaretci YOK SAYILIR, satir
     yine bloklanir (mekanizmanin sessiz bir `# noqa`ya donmesini engeller).
  3. GORUNURLUK               -> muaf satir sayisi HER kosumda basilir (KAPSAM BEYANI,
     CLAUDE.core §7 + checklist CORE-06): *"0 bulgu"* asla *"hicbir sey muaf degil"*
     diye okunamaz. Muaf kova, temiz kovaya KARISMAZ.
  ⛔ Dosya ADI taramasi (D5) MUAFIYET DISIDIR — dosya adina isaretci konamaz.

OLCUM YONTEMI — GERCEK GIRIS NOKTASI (kod != kablolama)
-------------------------------------------------------
Hicbir vektor fonksiyonu elle cagirmaz: her vektor SENTETIK bir git deposunda,
GERCEK `core_precommit.py` surecini staged yolda (ya da `--all` ile) kosturur.
Ucuncu baglam icin kasten gorev-DISI sekiller kullanilir (`.py` `#` yorumu · CRLF
satir sonu · derin `.yaml` yolu · `--all` CI kipi).

⭐ TERS YON (E bolumu): ayni vektor, muafiyet mekanizmasi TARIHI HALINE (dosya-bazli
`SCAN_EXEMPT`) dondurulmus bir kapi kopyasinda da kosturulur. Eski kapi AYNI izi
SESSIZCE geciriyor; bu, "yesil suit" degil KARSITLIK uretir.

⚠ KIMLIK LITERALI YAZILMAZ: bu dosya da kapidan gecer. Z adlari `_z()` ile parca
parca kurulur; isaretci sozcugu de birlestirilerek yazilir ki bu dosyadaki ornek
satirlar canli birer muafiyete donusmesin.

KOSUM:  python tests/fixtures/genericize_muafiyet_satir_bazli/run.py [--mutasyon-<kip>]
Cikis:  0 hepsi beklendigi gibi · 1 sapma · 2 DOGRULANAMADI (capa tutmadi/mutant bozuk)

MUTASYONLAR (korpusun bos-yesil olmadigini kanitlar):
  --mutasyon-gerekcesiz-kabul  gerekce olcutu kaldirilir (her isaretci gecerli sayilir)
  --mutasyon-beyan-yok         KAPSAM BEYANI cagrisi sokulur (gorunurluk olur)
  --mutasyon-dosya-muafiyeti   isaretci SATIRDA degil TUM METINDE aranir (bolge muafiyeti)
  --mutasyon-scan-exempt-geri  dosya-bazli `SCAN_EXEMPT` geri konur (tarihi tasarim)
"""
from __future__ import annotations

import os
import re
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
# parents: [0]=fixtures [1]=tests [2]=REPO KOKU. Yanlis indeks yazmak dosyayi
# bulunamaz yapar ve korpus "hepsi FAIL" der; sebebi kod sanilir (sir_gate'in dersi).
REPO = HERE.parents[2]
SCRIPTS = REPO / "scripts"
GATE_KAYNAK = SCRIPTS / "git-hooks" / "core_precommit.py"
GC_KAYNAK = SCRIPTS / "genericize_common.py"

for _p in (GATE_KAYNAK, GC_KAYNAK):
    if not _p.exists():                      # sessiz yanlis-sonuc yerine gurultulu hata
        raise SystemExit(f"[fixture-hatasi] kaynak bulunamadi: {_p}")


def _z(modul: str, no: str) -> str:
    """Z obje adini PARCADAN kurar (yukaridaki ⚠ notu)."""
    return "Z" + modul + no


Z_SENTETIK = _z("QWE", "123")     # desene uyar, `ORNEK_Z`de YOK  -> yakalanmali
Z_JENERIK = _z("SD", "001")       # allowlist'te                  -> sessiz
ISARET = "genericize" + "-allow"  # sozlesme literali (asagida S1 ile civilenir)
GEREKCE = "kanonik naming ornegi, gercek obje degil"

SONUC: list[tuple[str, bool, str]] = []


def ekle(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(ok), detay))


# ── TARIHI TABAN / mutasyon yamalari ───────────────────────────────────────────
_D5_CAPA = "    for tok, ad in sizintilari_bul(path, ID_PAT):"
_ESKI_SCAN_EXEMPT = (
    "    if path in {\n"
    "        \"scripts/hooks/pre_tool_guard.py\",\n"
    "        \"scripts/git-hooks/core_precommit.py\",\n"
    "        \"scripts/genericize_common.py\",\n"
    "    }:\n"
    "        return\n"
)


def _tarihi_taban(kaynak: str) -> str:
    """Q329 ONCESI tasarimi birebir geri kurar: dosya-bazli, gerekcesiz muafiyet."""
    if _D5_CAPA not in kaynak:
        raise AssertionError("capa yok: check_generic D5 dali (_D5_CAPA)")
    return kaynak.replace(_D5_CAPA, _ESKI_SCAN_EXEMPT + _D5_CAPA, 1)


MUTLAR = {
    "--mutasyon-gerekcesiz-kabul": lambda s: _degistir(
        s,
        "    return len(g) >= MUAF_MIN_KARAKTER and len(g.split()) >= MUAF_MIN_KELIME",
        "    return True"),
    "--mutasyon-beyan-yok": lambda s: _degistir(
        s, "    kapsam_beyani(sayac)", "    pass  # beyan SOKULDU (mutasyon)"),
    # ⚠ Bu mutasyon `search(satir)` -> `search(text)` DEGILDIR: desende `$` var ve
    #   `re.M` olmadan `search(text)` yalniz METNIN SONUNDAKI isaretciyi gorurdu ⇒
    #   cok satirli dosyada hicbir sey degismez, mutasyon SESSIZCE no-op olur (ilk
    #   taslakta tam bu oldu: KACTI cikti ama korpus degil MUTASYON yanlisti).
    #   Dogru vektor: satir-sonu duyarli (re.M) TUM METIN taramasi = bolge/dosya muafiyeti.
    "--mutasyon-dosya-muafiyeti": lambda s: _degistir(
        s, "        m = MUAF_RE.search(satir)",
        "        m = re.compile(MUAF_RE.pattern, re.M).search(text)"),
    "--mutasyon-scan-exempt-geri": _tarihi_taban,
}


def _degistir(s: str, eski: str, yeni: str) -> str:
    if eski not in s:
        raise AssertionError(f"capa yok: {eski[:60]!r}")
    return s.replace(eski, yeni, 1)


# ── kum / depo yardimcilari ────────────────────────────────────────────────────
_KUMLAR: list[Path] = []


def _sil(d: Path) -> None:
    """Q319: `.git/objects` salt-okurdur; `rmtree(ignore_errors=True)` Windows'ta SESSIZCE kalir."""
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


def _git(depo: Path, *a) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(depo), *a], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def _depo(gate_metni: str) -> Path:
    """Sentetik git deposu + kapinin (mutasyonlu olabilen) kopyasi."""
    d = Path(tempfile.mkdtemp(prefix="q329_"))
    _KUMLAR.append(d)
    _git(d, "init", "-q")
    _git(d, "config", "user.email", "fixture@example.com")
    _git(d, "config", "user.name", "fixture")
    (d / "scripts" / "git-hooks").mkdir(parents=True)
    shutil.copy2(GC_KAYNAK, d / "scripts" / "genericize_common.py")
    (d / "scripts" / "git-hooks" / "core_precommit.py").write_text(
        gate_metni, encoding="utf-8")
    return d


def _env() -> dict:
    # ⚠ ORTAM IZOLASYONU: miras alinan CLAUDE_PROJECT_DIR/IX_* gate'e BASKA bir repoyu
    # cozdurur ve fixture sessizce anlamsizlasir (sir_gate'in ayni dersi).
    env = {k: v for k, v in os.environ.items()
           if k != "CLAUDE_PROJECT_DIR" and not k.startswith("IX_")}
    env["PYTHONIOENCODING"] = "utf-8"
    # Blocklist SABITLENIR: bos liste `--all`da fail-closed dalini acar ve olcum
    # muafiyeti degil listenin YOKLUGUNU olcerdi. Sentinel gercek bir kimlik DEGILDIR.
    env["IX_GENERICIZE_BLOCKLIST"] = "SENTINEL" + "-ISIM"
    # Changelog gate'i (4. kontrol) bu korpusun EKSENI DEGIL: `scripts/**.py` stage
    # eden vektorler onu tetiklerdi ve rc 1 YANLIS sebeple gelirdi (eksen kirlenmesi).
    env["IX_NO_CHANGELOG"] = "1"
    return env


def kos(depo: Path, dosyalar: dict[str, str], all_kip: bool = False,
        satir_sonu: str = "\n") -> tuple[int, str]:
    """dosyalar: {gorece-yol: icerik}. Stage'lenir, GERCEK kapi kosturulur, geri alinir."""
    yazilan: list[Path] = []
    for rel, icerik in dosyalar.items():
        p = depo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        ham = icerik.replace("\n", satir_sonu)
        p.write_bytes(ham.encode("utf-8"))
        yazilan.append(p)
        _git(depo, "add", "-f", rel)
    argv = [sys.executable, str(depo / "scripts" / "git-hooks" / "core_precommit.py")]
    if all_kip:
        argv.append("--all")
    r = subprocess.run(argv, cwd=str(depo), env=_env(), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300)
    for rel in dosyalar:
        _git(depo, "rm", "-q", "--cached", "-f", rel)
    for p in yazilan:
        p.unlink(missing_ok=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# Sayaclari ASCII capalardan okur (Turkce diakritikler bozulsa bile okunur kalir).
_MUAF_RE = re.compile(r"muaf-sat\S*\s+(\d+)")
_GEREKCESIZ_RE = re.compile(r"(\d+)\s*\(YOK SAYILDI\)")


def sayac(cikti: str) -> tuple[int | None, int | None]:
    m = _MUAF_RE.search(cikti)
    g = _GEREKCESIZ_RE.search(cikti)
    return (int(m.group(1)) if m else None), (int(g.group(1)) if g else None)


def main() -> int:
    gecerli = set(MUTLAR)
    for a in sys.argv[1:]:
        if a.startswith("--mutasyon") and a not in gecerli:
            raise SystemExit(f"[KULLANIM] bilinmeyen mutasyon kipi: {a} -> gecerli: "
                             + " ".join(sorted(gecerli)))
    secili = next((a for a in sys.argv[1:] if a in gecerli), None)

    ham = GATE_KAYNAK.read_text(encoding="utf-8")
    gate_metni = ham
    if secili:
        try:
            gate_metni = MUTLAR[secili](ham)
        except AssertionError as e:
            print(f"[DOGRULANAMADI] mutasyon capasi bulunamadi ({secili}): {e} -> "
                  "mutasyon UYGULANMADI; 'gecti' sonucu ANLAMSIZ olurdu.")
            return 2
        if gate_metni == ham:
            print(f"[DOGRULANAMADI] mutasyon kaynagi DEGISTIRMEDI ({secili}) — capa bayat")
            return 2
        try:
            compile(gate_metni, "mutant", "exec")
        except SyntaxError as e:
            print(f"[DOGRULANAMADI] mutant SOZDIZIMI BOZUK ({secili}): {e}")
            return 2

    try:
        _senaryolar(ham, gate_metni)
    finally:
        for d in _KUMLAR:
            _sil(d)

    gecen = sum(1 for _, ok, _ in SONUC if ok)
    print(f"\n=== GENERICIZE MUAFIYETI / SATIR BAZLI (Q329) "
          f"{'[' + secili + ']' if secili else '[taban]'} ===")
    for ad, ok, detay in SONUC:
        print(f"  [{'OK  ' if ok else 'FAIL'}] {ad}" + (f"   -> {detay}" if not ok else ""))
    print(f"\n{gecen}/{len(SONUC)} OK")
    if secili:
        print(f"  (MUTASYON {secili} — dusmesi BEKLENEN vektorler var; "
              "tam skor 'mutasyon KACTI' demektir)")
    return 0 if gecen == len(SONUC) else 1


def _senaryolar(ham: str, gate_metni: str) -> None:
    d = _depo(gate_metni)
    iz = f"vaka: {Z_SENTETIK}_CL_X"
    muaf_satir = f"{iz}  <!-- {ISARET}: {GEREKCE} -->"

    # ── S: SOZLESME ────────────────────────────────────────────────────────────
    ekle("S1 isaretci sozcugu dokumanda yazili olanla AYNI (sessiz yeniden adlandirma yok)",
         f'MUAF_ISARET = "{ISARET}"' in ham,
         "kaynakta `MUAF_ISARET` beyani bulunamadi ya da farkli")
    ekle("S2 dosya-bazli `SCAN_EXEMPT` KALDIRILDI (uc dosya artik taraniyor)",
         "SCAN_EXEMPT = {" not in ham, "kaynakta hala dosya-bazli muafiyet var")

    # ── A: MEKANIZMA (bilinen-bozuk / bilinen-temiz) ───────────────────────────
    rc, o = kos(d, {"docs/a1.md": f"# not\n\n{iz}\n"})
    ekle("A1 BILINEN-BOZUK: isaretcisiz kimlik -> BLOK (exit 1) + dogru satir no",
         rc == 1 and "GENERICIZE-LEAK" in o and "docs/a1.md:3" in o and Z_SENTETIK in o,
         f"rc={rc} cikti={o[-300:]!r}")

    rc, o = kos(d, {"docs/a2.md": f"# not\n\n{muaf_satir}\n"})
    m, g = sayac(o)
    ekle("A2 gerekceli isaretci -> GECER (exit 0) ve muaf-satir sayaci 1",
         rc == 0 and m == 1 and g == 0 and "GENERICIZE-LEAK" not in o,
         f"rc={rc} muaf={m} gerekcesiz={g} cikti={o[-300:]!r}")

    rc, o = kos(d, {"docs/a3.md": f"# not\n\n{iz}  <!-- {ISARET}: x -->\n"})
    m, g = sayac(o)
    ekle("A3 GEREKCESIZ isaretci (tek harf) -> YOK SAYILIR, satir yine BLOK",
         rc == 1 and g == 1 and m == 0 and "YOK SAYILDI" in o,
         f"rc={rc} muaf={m} gerekcesiz={g} cikti={o[-400:]!r}")

    rc, o = kos(d, {"docs/a3b.md": f"# not\n\n{iz}  <!-- {ISARET}: -->\n"})
    ekle("A3b BOS gerekce -> YOK SAYILIR, satir yine BLOK",
         rc == 1 and "GENERICIZE-LEAK" in o, f"rc={rc} cikti={o[-300:]!r}")

    rc, o = kos(d, {"docs/a4.md": f"# baslik  <!-- {ISARET}: {GEREKCE} -->\n\n{iz}\n"})
    ekle("A4 ⭐ isaretci BASKA satirda -> BLOK (blok/bolge/dosya muafiyeti YOK)",
         rc == 1 and "docs/a4.md:3" in o, f"rc={rc} cikti={o[-300:]!r}")

    rc, o = kos(d, {f"docs/{Z_SENTETIK}_not.md": f"# not  <!-- {ISARET}: {GEREKCE} -->\n"})
    ekle("A5 ⭐ DOSYA ADI izi + satirda gerekceli isaretci -> yine BLOK (D5 muafiyet DISI)",
         rc == 1 and "DOSYA ADI" in o, f"rc={rc} cikti={o[-300:]!r}")

    rc, o = kos(d, {"docs/a6.md": f"# not\n\n{iz}  <!-- {ISARET}: aaaaaaaaaaaaaaaa -->\n"})
    ekle("A6 tek KELIMELIK (uzun ama tek sozcuk) gerekce -> yetersiz, BLOK",
         rc == 1 and "YOK SAYILDI" in o, f"rc={rc} cikti={o[-300:]!r}")

    # ── B: FP CAPALARI / KONTROL GRUBU ─────────────────────────────────────────
    rc, o = kos(d, {"docs/b1.md": "# tamamen temiz bir dosya\n\nmetin.\n"})
    m, g = sayac(o)
    ekle("B1 KONTROL GRUBU: temiz dosya -> exit 0, bulgu yok, muaf 0",
         rc == 0 and m == 0 and g == 0, f"rc={rc} muaf={m} cikti={o[-300:]!r}")

    rc, o = kos(d, {"docs/b2.md": f"# not\n\nornek: {Z_JENERIK}\n"})
    m, _ = sayac(o)
    ekle("B2 allowlist'teki jenerik ad isaretcisiz de SESSIZ (muafiyet degisimi "
         "allowlist'i etkilemedi) ve muaf sayacina GIRMEZ",
         rc == 0 and m == 0, f"rc={rc} muaf={m} cikti={o[-300:]!r}")

    rc, o = kos(d, {"docs/b3.md": f"# not  <!-- {ISARET}: {GEREKCE} -->\n\ntemiz metin\n"})
    m, _ = sayac(o)
    ekle("B3 kimlik TASIMAYAN satirdaki isaretci sayaci sismez (sayac bastirilan "
         "BULGUYU sayar, isaretci sayisini degil)",
         rc == 0 and m == 0, f"rc={rc} muaf={m} cikti={o[-300:]!r}")

    # ── C: GORUNURLUK / KAPSAM BEYANI (bu degisikligin ozu) ────────────────────
    rc, o = kos(d, {"docs/c1.md": "# temiz\n"})
    ekle("C1 ⭐ BULGU YOKKEN de KAPSAM BEYANI basiliyor ('0 bulgu' != 'hicbir sey muaf degil')",
         rc == 0 and "[KAPSAM]" in o, f"rc={rc} cikti={o[-300:]!r}")
    ekle("C2 beyan muafiyet bicimini ve 'dosya ADI taramasi muafiyet DISI' sinirini soyluyor",
         ISARET in o and "D5" in o, f"cikti={o[-400:]!r}")

    rc, o = kos(d, {"docs/c3.md": f"# not\n\n{muaf_satir}\n"})
    ekle("C3 ⭐ muaf satir ADIYLA listeleniyor ama TOKEN BASILMIYOR (CI gunlugu PUBLIC)",
         rc == 0 and "MUAF" in o and "docs/c3.md:3" in o and Z_SENTETIK not in o,
         f"rc={rc} cikti={o[-400:]!r}")

    rc, o = kos(d, {"docs/c4.md": "# temiz\n"}, all_kip=True)
    ekle("C4 3.BAGLAM (CI kipi): `--all` yolunda da beyan basiliyor",
         rc == 0 and "[KAPSAM]" in o, f"rc={rc} cikti={o[-300:]!r}")

    # ── D: UCUNCU BAGLAM — gorev-DISI sekiller ─────────────────────────────────
    rc, o = kos(d, {"tools/d1.py": f"# arac\nBAD = '{Z_SENTETIK}'  # {ISARET}: {GEREKCE}\n"})
    m, _ = sayac(o)
    ekle("D1 3.BAGLAM: `.py` + `#` yorumu ile isaretci calisiyor (md'ye ozel degil)",
         rc == 0 and m == 1, f"rc={rc} muaf={m} cikti={o[-300:]!r}")

    rc, o = kos(d, {"docs/d2.md": f"# not\n\n{muaf_satir}\n"}, satir_sonu="\r\n")
    m, _ = sayac(o)
    ekle("D2 3.BAGLAM: CRLF satir sonunda da isaretci calisiyor (split('\\n') artigi "
         "gerekceyi bozmuyor)",
         rc == 0 and m == 1, f"rc={rc} muaf={m} cikti={o[-300:]!r}")

    rc, o = kos(d, {"cok/derin/yol/d3.yaml": f"anahtar: {Z_SENTETIK}  # {ISARET}: {GEREKCE}\n"})
    m, _ = sayac(o)
    ekle("D3 3.BAGLAM: derin yol + `.yaml` -> isaretci calisiyor, satir bazli kaliyor",
         rc == 0 and m == 1, f"rc={rc} muaf={m} cikti={o[-300:]!r}")

    rc, o = kos(d, {"cok/derin/yol/d3b.yaml": f"a: {Z_SENTETIK}  # {ISARET}: {GEREKCE}\n"
                                              f"b: {Z_SENTETIK}\n"})
    ekle("D3b ⭐ ayni dosyada isaretcisiz IKINCI satir hala BLOK ediyor (muafiyet yayilmiyor)",
         rc == 1 and "d3b.yaml:2" in o, f"rc={rc} cikti={o[-300:]!r}")

    # ── E: TERS YON — mekanizma TARIHI haline dondurulunce ne oluyor ───────────
    #  Kapinin KENDI kaynagi, muaf dosyanin GORECE YOLUNDA stage edilir: tarihi
    #  tasarimda bu yol `SCAN_EXEMPT`tedir ⇒ yorumdaki iz SESSIZCE gecerdi.
    kirli_gc = GC_KAYNAK.read_text(encoding="utf-8") + f"\n# vaka notu: {Z_SENTETIK}\n"
    rc_yeni, o_yeni = kos(d, {"scripts/genericize_common.py": kirli_gc})
    try:
        eski_metni = _tarihi_taban(ham)
    except AssertionError as e:
        ekle("E1 TARIHI TABAN kiyasi", False, f"KURULAMADI: {e}")
    else:
        d_eski = _depo(eski_metni)
        rc_eski, o_eski = kos(d_eski, {"scripts/genericize_common.py": kirli_gc})
        ekle("E1 ⭐ TERS YON: muaf dosyanin YORUMUNDAKI iz — tarihi (dosya-bazli) kapida "
             "SESSIZCE gecerdi, bugunku kapida BLOKLANIYOR",
             rc_eski == 0 and "GENERICIZE-LEAK" not in o_eski and rc_yeni == 1
             and "scripts/genericize_common.py" in o_yeni,
             f"eski_rc={rc_eski} yeni_rc={rc_yeni} yeni_cikti={o_yeni[-300:]!r}")
        ekle("E2 tarihi kapi ayni kimligi BASKA bir dosyada yakalayabiliyordu "
             "(kontrol grubu: kusur KAPSAM'daydi, mekanizmada degil)",
             kos(d_eski, {"docs/e2.md": f"# not\n\n{iz}\n"})[0] == 1,
             "tarihi kapi hicbir sey yakalamiyorsa kiyas anlamsizdir")

    # ── K: KABLOLAMA — gercek `git commit` ─────────────────────────────────────
    #  "Kapi rc 1 dondu" ile "commit gercekten BLOKLANDI" ayni sey degildir.
    d2 = _depo(gate_metni)
    (d2 / ".git" / "hooks").mkdir(parents=True, exist_ok=True)
    kanca = d2 / ".git" / "hooks" / "pre-commit"
    kanca.write_text(
        "#!/bin/sh\nexec \"%s\" \"$(dirname \"$0\")/../../scripts/git-hooks/core_precommit.py\"\n"
        % sys.executable.replace("\\", "/"), encoding="utf-8")
    try:
        os.chmod(kanca, 0o755)
    except Exception:
        pass
    (d2 / "docs").mkdir(parents=True, exist_ok=True)
    (d2 / "docs" / "k1.md").write_text(f"# not\n\n{iz}\n", encoding="utf-8")
    _git(d2, "add", "-f", "docs/k1.md")
    c = subprocess.run(["git", "-C", str(d2), "commit", "-m", "sizintili"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=_env())
    say = _git(d2, "rev-list", "--count", "HEAD")
    n = int(say.stdout.strip()) if say.stdout.strip().isdigit() else 0
    ekle("K1 UCTAN UCA: gercek `git commit` BLOKLANDI (0 commit)",
         c.returncode != 0 and n == 0, f"commit_rc={c.returncode} commit_sayisi={n}")

    (d2 / "docs" / "k1.md").write_text(f"# not\n\n{muaf_satir}\n", encoding="utf-8")
    _git(d2, "add", "-f", "docs/k1.md")
    c = subprocess.run(["git", "-C", str(d2), "commit", "-m", "gerekceli muafiyet"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=_env())
    say = _git(d2, "rev-list", "--count", "HEAD")
    n = int(say.stdout.strip()) if say.stdout.strip().isdigit() else 0
    ekle("K2 UCTAN UCA: gerekceli muafiyetle ayni commit GECIYOR (1 commit) — "
         "mekanizma gercekten kullanilabilir",
         c.returncode == 0 and n == 1, f"commit_rc={c.returncode} commit_sayisi={n} "
         f"cikti={(c.stdout or '') + (c.stderr or '')!r}"[:300])


if __name__ == "__main__":
    sys.exit(main())
