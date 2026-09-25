#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""worktree_yasam_dongusu — kayit #80 (kanonik kok + gun-sonu denetimi + silme sirasi),
#79 (statusline worktree kopyasini okuyor), #18 (kosulsuz mklink), #39 I-5 (yol oneki).

NIYE AYRI KOSUCU (bad/good proje dizini kalibiyla IFADE EDILEMEZ):
  * olculen sey bir VALIDATOR ciktisi degil, GERCEK bir git deposunun + gercek
    worktree'lerin uzerinde kosan bir denetim akisi (`git worktree list` / `git cherry` /
    `git hash-object`). Sentetik metin dosyasiyla uretilemez.
  * `#79` degismezi bir DIZIN YURUYUSUNUN budanmasidir; ciktisi "hangi dosya bulundu"dur.

MUTASYON: `python run.py --mutasyon` — her degismez icin fix SOKULUR ve vektorun
KIRMIZIYA dondugu olculur. Mutasyon GERCEK KAYNAGA YAZILMAZ (kalinti komsu turlari
kirletir): kaynak metni okunur, bellekte degistirilir, izole bir modul olarak exec edilir.
Kurulum hatasi `KACTI` DEGILDIR -> ucuncu deger `KURULAMADI` basilir.

Issue #280 (2026-09-25): ② hukmu `git cherry`den ICERIK karsilastirmasina tasindi
  (V4 yapisal + V10 gercek-git 5 kollu matris; M10-M12). Issue #284: `--wt-kapat`
  ReadOnly oznitelikli dizinde kalici bloklanmaz + teshis siniflidir (V11; M13-M15).
PR #300 bug-gate (2026-09-25): F1 tag+dal ayni ad (V10h; M17) · F2 `--no-renames`
  yeniden adlandirma + silme kollari (V10g/V10i; M16) · F4 ③ detached ve ② hata kolunda
  da kosar (V12/V12b; M18/M19) · F5 ALARM'a "yerel main bayat olabilir" notu (V10j; M20).

UC BAGLAM (F3):
  (1) bilinen-BOZUK  : fix sokulmus kod (mutasyon dali)
  (2) bilinen-TEMIZ  : bugunku kod
  (3) gorev-DISI 3. baglam: ana repo'dan BAGIMSIZ, gecici dizinde kurulan sentetik bir
      git deposu (kendi `main` dali, kendi worktree'leri, kendi `.gitignore`'u)
"""
from __future__ import annotations

import ast
import contextlib
import io
import os
import stat
import subprocess
import sys
import tempfile
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

KOK = Path(__file__).resolve().parents[3]
TEAM_SETUP = KOK / "scripts" / "team_setup.py"
STATUSLINE = KOK / "scripts" / "statusline.py"
SESSION_START = KOK / "scripts" / "hooks" / "session_start.py"

MUTASYON = "--mutasyon" in sys.argv
_sayac = {"pass": 0, "fail": 0}


def sonuc(ad: str, tamam: bool, not_=None) -> None:
    _sayac["pass" if tamam else "fail"] += 1
    print(f"  [{'PASS' if tamam else 'FAIL'}] {ad}" + (f" -- {not_}" if not_ else ""))


class Kurulamadi(RuntimeError):
    """Mutasyon ENJEKTE EDILEMEDI. `KACTI` ile ayni sey DEGILDIR."""


def mutasyonlu_kaynak(yol: Path, mutasyon=None) -> str:
    src = yol.read_text(encoding="utf-8")
    if mutasyon is not None:
        eski, yeni = mutasyon
        if eski not in src:
            raise Kurulamadi(f"capa bulunamadi: {eski[:70]!r}")
        src = src.replace(eski, yeni, 1)
    return src


def modul(yol: Path, mutasyon=None, ad: str = "mut_modul"):
    """Kaynagi BELLEKTE (gerekirse mutasyonlu) exec et. Gercek dosyaya YAZMAZ."""
    src = mutasyonlu_kaynak(yol, mutasyon)
    m = types.ModuleType(ad)
    m.__file__ = str(yol)
    sys.modules.pop(ad, None)
    sys.modules[ad] = m
    exec(compile(src, str(yol), "exec"), m.__dict__)  # noqa: S102
    return m


def git(cwd: Path, *a: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(cwd), *a], capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# 3. BAGLAM: ana repo'dan BAGIMSIZ, sentetik bir git deposu + gercek worktree'ler
# ---------------------------------------------------------------------------
def kum_kur(kok: Path) -> Path:
    proje = kok / "PROJ"
    pkg = proje / "SOURCE_CODES" / "SD" / "ZSD001_CLC"
    pkg.mkdir(parents=True)
    (pkg / "SESSION_NOTES.md").write_text("Sprint 3 ilerleme 2/5\nKANONIK\n", encoding="utf-8")
    (proje / ".gitignore").write_text(".tmp/\nagent-memory/\n", encoding="utf-8")
    (proje / "ortak.txt").write_text("ayni icerik her yerde\n", encoding="utf-8")
    git(proje, "init", "-q", "-b", "main")
    git(proje, "config", "user.email", "fixture")
    git(proje, "config", "user.name", "fixture")
    git(proje, "add", "-A")
    git(proje, "commit", "-q", "-m", "taban")
    return proje


# ---------------------------------------------------------------------------
# VEKTORLER
# ---------------------------------------------------------------------------
def v1_kanonik_yol(ts) -> None:
    """#80(1): yol TURETILIR (surucu/klasor sabiti YOK), sablon <parent>/.wt/<proje>/<dal>."""
    p = Path(os.sep + os.path.join("x", "y", "PROJ")).resolve()
    beklenen = p.parent / ".wt" / "PROJ" / "a-b"
    olculen = ts.wt_yolu(p, "infra/a-b")
    sonuc("V1 kanonik yol sablonu", olculen == beklenen, olculen)
    # FP CAPASI: baska bir proje/ebeveyn AYNI yolu URETMEMELI (sabit gomulu degil).
    q = Path(os.sep + os.path.join("baska", "kok", "OTEKI")).resolve()
    sonuc("V1b yol PROJEYE gore degisiyor (sabit gomulu degil)",
          ts.wt_yolu(q, "infra/a-b") != olculen, ts.wt_yolu(q, "infra/a-b"))


def v2_v3_yetim(cikti: str) -> None:
    """#80(2)a/d: kayitsiz yetim BULUNUR; yetimde OZGUN icerik ayirt edilir."""
    sonuc("V2 kayitsiz yetim sayisi 2", "KAYITSIZ YETIM: 2" in cikti,
          next((s.strip() for s in cikti.splitlines() if "YETIM:" in s), None))
    ozgun_sat = [s for s in cikti.splitlines() if "yetim-ozgun" in s]
    git_sat = [s for s in cikti.splitlines() if "yetim-gitte" in s]
    sonuc("V3 OZGUN icerikli yetim: 1 dosya",
          bool(ozgun_sat) and "1 dosya" in ozgun_sat[0],
          ozgun_sat[0].strip() if ozgun_sat else None)
    # CAPA: icerigi git'te OLAN yetim 0 gostermeli. Bu capa olmadan "her yetimde is var"
    # diyen bir denetim de V3'u gecerdi (uyari korlugu -> hasat hic yapilmaz).
    sonuc("V3b icerigi git'te OLAN yetim: 0 dosya",
          bool(git_sat) and "0 dosya" in git_sat[0],
          git_sat[0].strip() if git_sat else None)


def v4_cherry(src: str) -> None:
    """#80(2)b + Issue #280: hukum ICERIK karsilastirmasindan; `--is-ancestor` YOK.

    Eski capa "`git cherry` cagriliyor" idi — Issue #280 ile `cherry` yalniz EK SINYAL
    oldu (cok commit'li squash'ta yanlis alarm). Hukmun DAVRANISI V10'da gercek git
    matrisiyle olculur; burasi yalniz yapisal capadir.
    ⛔ `src` PARAMETRE olarak gelir, diskten OKUNMAZ: mutasyon bellekte uygulaniyor;
    kaynagi burada yeniden okumak mutasyonu SAHTE-KACIRIR (olculdu: M3+M4 ilk koşumda
    "korpus gormedi" dedi, oysa vektor mutasyonsuz metni olcuyordu).
    """
    agac = ast.parse(src)
    fns = {n.name: n for n in ast.walk(agac) if isinstance(n, ast.FunctionDef)
           and n.name in ("wt_denetim", "_dal_hukmu_bas", "_dal_icerik_farki")}
    if "wt_denetim" not in fns:
        sonuc("V4 wt_denetim AST'te bulundu", False, "fonksiyon yok")
        return
    # CAPA AST-TABANLI: duz `"cherry" in src` docstring'e/yoruma takilirdi. Burada YALNIZ
    # fonksiyon govdesindeki dizge SABITLERI sayilir (yorumlar AST'e girmez).
    sabitler = [n.value for f in fns.values() for n in ast.walk(f)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    # ② hukmu PR #300 F4 ile `_dal_hukmu_bas`a tasindi (③ hicbir ② kolunda atlanmasin)
    # => cagri zinciri wt_denetim + _dal_hukmu_bas birlikte taranir.
    cagrilar = {n.func.id for ad in ("wt_denetim", "_dal_hukmu_bas") if ad in fns
                for n in ast.walk(fns[ad])
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    sonuc("V4 hukum `_dal_icerik_farki` (merge-base + `diff --name-only`) ile",
          "_dal_icerik_farki" in cagrilar and "merge-base" in sabitler
          and "--name-only" in sabitler)
    sonuc("V4b `--is-ancestor` KULLANILMIYOR",
          not any("is-ancestor" in s for s in sabitler), "squash-merge'de yaniltir")


def kum_icerik_kur(kok: Path, ts) -> tuple[Path, dict]:
    """Issue #280 matrisi — izole depo, her kol KENDI dosyalarina dokunur (kollar ayrik).

    K1 tek commit+squash · K2 cok commit+squash · K3 squash + main SONRA AYNI dosya ·
    K4 squash + main SONRA BASKA dosya · K5 birlesmemis dal. Her dal gercek bir worktree'dir.
    """
    proje = kok / "ICPROJ"
    proje.mkdir()
    (proje / "taban.txt").write_text("taban\n", encoding="utf-8")
    # K6/K8 icin taban dosyalari (diger kollar bunlara DOKUNMAZ — kollar ayrik kalir)
    (proje / "eski.txt").write_text(ESKI_ICERIK, encoding="utf-8")
    (proje / "sil.txt").write_text("silinecek\n", encoding="utf-8")
    git(proje, "init", "-q", "-b", "main")
    git(proje, "config", "user.email", "fixture")
    git(proje, "config", "user.name", "fixture")
    git(proje, "add", "-A")
    git(proje, "commit", "-q", "-m", "taban")

    def yaz_commit(dosyalar, mesaj):
        for ad, icerik in dosyalar:
            (proje / ad).write_text(icerik, encoding="utf-8")
        git(proje, "add", "-A")
        git(proje, "commit", "-q", "-m", mesaj)

    def dal(ad, commitler, squash=True):
        git(proje, "checkout", "-q", "-b", ad, "main")
        for i, c in enumerate(commitler):
            yaz_commit(c, f"{ad} c{i + 1}")
        git(proje, "checkout", "-q", "main")
        if squash:
            git(proje, "merge", "-q", "--squash", ad)
            git(proje, "commit", "-q", "-m", f"squash {ad}")

    dal("k1-tek", [[("a1.txt", "k1\n")]])
    dal("k2-cok", [[("b1.txt", "1\n")], [("b2.txt", "2\n")]])
    dal("k3-ayni", [[("d.txt", "dal\n")], [("d2.txt", "x\n")]])
    yaz_commit([("d.txt", "dal\nmain-sonra-ekledi\n")], "main d.txt'ye dokundu")
    dal("k4-baska", [[("e1.txt", "1\n")], [("e2.txt", "2\n")]])
    yaz_commit([("f_main.txt", "main\n")], "main baska dosya")
    dal("k5-yok", [[("g.txt", "g\n")]], squash=False)
    # K6 (F2): dal eski.txt -> yeni.txt YENIDEN ADLANDIRDI; main yalniz yeni.txt'yi aldi
    #   (eski.txt main'de duruyor) => is main'de DEGIL. `--no-renames` olmadan dalin
    #   degistirdigi dosyalar yalniz [yeni.txt] gorunur => sahte "icerik main'de".
    git(proje, "checkout", "-q", "-b", "k6-ren", "main")
    git(proje, "mv", "eski.txt", "yeni.txt")
    git(proje, "commit", "-q", "-m", "k6 yeniden adlandirma")
    git(proje, "checkout", "-q", "main")
    yaz_commit([("yeni.txt", ESKI_ICERIK)], "main yalniz yeni.txt'yi aldi")
    # K7 (F1): dal ile AYNI ADDA bir tag, main ucunda. Kisa ad tag'e cozulurse
    #   merge-base = tag = diff bos => sahte "icerik main'de".
    git(proje, "tag", "k7-tag", "main")
    dal("k7-tag", [[("h.txt", "h\n")]], squash=False)
    # K8 (F2 istege bagli): birlesmemis SILME => ALARM (silinen yol main'de duruyor)
    git(proje, "checkout", "-q", "-b", "k8-sil", "main")
    git(proje, "rm", "-q", "sil.txt")
    git(proje, "commit", "-q", "-m", "k8 silme")
    git(proje, "checkout", "-q", "main")
    yollar = {}
    for d in ("k1-tek", "k2-cok", "k3-ayni", "k4-baska", "k5-yok", "k6-ren", "k7-tag",
              "k8-sil"):
        w = ts.wt_yolu(proje, d)
        w.parent.mkdir(parents=True, exist_ok=True)
        git(proje, "worktree", "add", "-q", str(w), d)
        yollar[d] = w
    return proje, yollar


ESKI_ICERIK = "".join(f"satir {i}\n" for i in range(12))   # rename tespiti icin %100 benzer


def v10_icerik_matrisi(cikti: str, ts=None, proje=None) -> None:
    """Issue #280: hukum ICERIK karsilastirmasi — cherry yalniz ek sinyal."""
    def sat(dal):
        return [s for s in cikti.splitlines() if f"② {dal}:" in s]

    def tamam(dal):
        return any("icerik main'de" in s for s in sat(dal)) and \
            not any("FARKLI" in s for s in sat(dal))

    def alarm(dal):
        return any("main'den FARKLI" in s and s.startswith("[FAIL]") for s in sat(dal))

    ilk = lambda d: (sat(d) or [None])[0]  # noqa: E731
    sonuc("V10 K1 tek commit+squash -> PASS", tamam("k1-tek"), ilk("k1-tek"))
    # KONTROL GRUBU ayni satirda: cherry burada '+2/2' der (eski hukum ALARM verirdi).
    sonuc("V10b K2 cok commit+squash -> PASS (cherry +2/2 iken)",
          tamam("k2-cok") and any("+2/2" in s for s in sat("k2-cok")), ilk("k2-cok"))
    sonuc("V10c K4 squash + main BASKA dosyaya ilerledi -> PASS",
          tamam("k4-baska"), ilk("k4-baska"))
    # FP CAPASI (ters yon): gercek pozitif hala yakalanmali — "her seye PASS" diyen
    # bir denetim V10/V10b/V10c'yi gecerdi.
    sonuc("V10d K5 birlesmemis dal -> ALARM", alarm("k5-yok"), ilk("k5-yok"))
    sonuc("V10e K3 squash + main AYNI dosyaya dokundu -> ALARM",
          alarm("k3-ayni"), ilk("k3-ayni"))
    sonuc("V10f K3 ALARM'i 'BEKLENEBILIR' + 'sessiz onay degildir' notu tasir",
          any("BEKLENEBILIR" in s and "sessiz onay degildir" in s for s in sat("k3-ayni")),
          next((s for s in sat("k3-ayni") if "BEKLENEBILIR" in s), None))
    # --- PR #300 bug-gate ---
    # F2: ALARM yetmez, ESKI yolun farkli listesinde olmasi da olculur (hukmu belirleyen
    # tam o yol). Dogrudan cagri: cikti yalniz ilk 5 yolu basar, satir-capasi kirilgan.
    farkli6 = ts._dal_icerik_farki(proje, "k6-ren")[1] if ts is not None else None
    sonuc("V10g K6 yeniden adlandirma, main yalniz yeniyi aldi -> ALARM + farkli'da eski.txt",
          alarm("k6-ren") and farkli6 is not None and "eski.txt" in farkli6,
          f"{ilk('k6-ren')} · farkli={farkli6}")
    sonuc("V10h K7 dal ile AYNI ADDA tag (main'de), is main'de degil -> ALARM",
          alarm("k7-tag"), ilk("k7-tag"))
    sonuc("V10i K8 birlesmemis silme -> ALARM", alarm("k8-sil"), ilk("k8-sil"))
    # F5: ALARM satiri yerel-main-bayat notunu tasir (FP capasi: OK dalinda YOK)
    sonuc("V10j ALARM 'yerel main BAYAT olabilir … git fetch' notunu tasir; OK dal tasimaz",
          any("BAYAT" in s and "git fetch" in s for s in sat("k5-yok"))
          and not any("BAYAT" in s for s in sat("k1-tek")),
          next((s for s in sat("k5-yok") if "BAYAT" in s), None))


def v12_kirli_her_kolda(ts, kok: Path) -> None:
    """PR #300 F4: ③ (kirli agac) ②'nin detached ve hata kollarinda da KOSAR.

    Risk: ③ atlanirsa operator `--zorla` ile commit'lenmemis isi siler. Iki kol:
    (a) detached HEAD worktree + izlenmeyen dosya · (b) ② HATA kolu (main ile ortak
    atasi olmayan dal => merge-base hatasi) + izlenmeyen dosya.
    """
    proje = kok / "KIRPROJ"
    proje.mkdir()
    (proje / "a.txt").write_text("a\n", encoding="utf-8")
    git(proje, "init", "-q", "-b", "main")
    git(proje, "config", "user.email", "fixture")
    git(proje, "config", "user.name", "fixture")
    git(proje, "add", "-A")
    git(proje, "commit", "-q", "-m", "taban")
    det = ts.wt_yolu(proje, "det-kirli")
    det.parent.mkdir(parents=True, exist_ok=True)
    git(proje, "worktree", "add", "-q", "--detach", str(det), "main")
    (det / "kirli.txt").write_text("commit'lenmemis is\n", encoding="utf-8")
    # ortak atasiz dal: bos agacli kok commit (checkout'suz; ana agaca dokunmaz)
    bos = subprocess.run(["git", "-C", str(proje), "mktree"], input="", capture_output=True,
                         text=True).stdout.strip()
    kc = git(proje, "commit-tree", bos, "-m", "iliskisiz kok").stdout.strip()
    git(proje, "branch", "hata-kirli", kc)
    hk = ts.wt_yolu(proje, "hata-kirli")
    git(proje, "worktree", "add", "-q", str(hk), "hata-kirli")
    (hk / "kirli2.txt").write_text("commit'lenmemis is\n", encoding="utf-8")
    cikti = denetim_kos(ts, proje)

    def uc(ad):
        return next((s for s in cikti.splitlines()
                     if s.startswith("[FAIL]") and f"③ {ad}:" in s), None)
    # KONTROL: kurulum gercekten ②'nin o kollarina dustu mu (yoksa vektor bos olcer)
    kol_det = any("detached HEAD" in s for s in cikti.splitlines())
    kol_hata = any("② icerik karsilastirmasi hata (hata-kirli)" in s
                   for s in cikti.splitlines())
    sonuc("V12 detached HEAD + kirli agac -> ② WARN VE ③ FAIL (izlenmeyen 1)",
          kol_det and uc("det-kirli") is not None
          and "izlenen/izlenmeyen 1 kayit" in (uc("det-kirli") or ""),
          uc("det-kirli") or f"② detached kolu={kol_det}; ③ satiri YOK")
    sonuc("V12b ② HATA kolu (ortak atasiz dal) + kirli agac -> ③ FAIL (izlenmeyen 1)",
          kol_hata and uc("hata-kirli") is not None
          and "izlenen/izlenmeyen 1 kayit" in (uc("hata-kirli") or ""),
          uc("hata-kirli") or f"② hata kolu={kol_hata}; ③ satiri YOK")
    for w in (det, hk):
        git(proje, "worktree", "remove", "--force", str(w))


def _salt_okunur_yap(d: Path) -> None:
    os.chmod(d, stat.S_IREAD if os.name == "nt" else (stat.S_IREAD | stat.S_IEXEC))


def _yazilabilir_geri(kok: Path) -> None:
    for dp, dn, fn in os.walk(kok):
        for x in dn + fn:
            try:
                os.chmod(os.path.join(dp, x), stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
            except OSError:
                pass


def v11_salt_okunur_silme(ts, kok: Path) -> None:
    """Issue #284: ReadOnly oznitelikli dizin `--wt-kapat`i KALICI bloklamamali."""
    # KONTROL GRUBU: kurulum hatayi GERCEKTEN uretiyor mu? (duz rmtree birakmali)
    kontrol = kok / "ro_kontrol"
    (kontrol / "alt").mkdir(parents=True)
    (kontrol / "alt" / "b.txt").write_text("b", encoding="utf-8")
    _salt_okunur_yap(kontrol / "alt")
    ts.shutil.rmtree(kontrol, ignore_errors=True)
    uretildi = kontrol.exists()
    _yazilabilir_geri(kok)
    if not uretildi:
        sonuc("V11 kontrol: ReadOnly kurulumu hatayi URETEMEDI -> DOGRULANAMADI (atlandi)",
              True, "platform/yetki (root?) salt-okunur dizini silmeyi engellemedi")
        return
    sonuc("V11 kontrol: duz rmtree(ignore_errors) ReadOnly dizini BIRAKIYOR (hata uretildi)",
          uretildi)
    # V11a: yardimci dogrudan
    a = kok / "ro_a"
    (a / "alt").mkdir(parents=True)
    (a / "alt" / "b.txt").write_text("b", encoding="utf-8")
    _salt_okunur_yap(a / "alt")
    kalan = ts._agac_sil(a)
    sonuc("V11a `_agac_sil` ReadOnly dizini SILDI", not a.exists(),
          f"kalan={[(p, type(e).__name__) for p, e in kalan][:3]}")
    _yazilabilir_geri(kok)
    # V11b: uctan uca `wt_kapat` (gercek git worktree, --zorla)
    proje = kok / "ROPROJ"
    (proje / "alt").mkdir(parents=True)
    (proje / "a.txt").write_text("a\n", encoding="utf-8")
    (proje / "alt" / "b.txt").write_text("b\n", encoding="utf-8")
    git(proje, "init", "-q", "-b", "main")
    git(proje, "config", "user.email", "fixture")
    git(proje, "config", "user.name", "fixture")
    git(proje, "add", "-A")
    git(proje, "commit", "-q", "-m", "taban")
    w = ts.wt_yolu(proje, "ro-dal")
    w.parent.mkdir(parents=True, exist_ok=True)
    git(proje, "worktree", "add", "-q", "-b", "ro-dal", str(w), "main")
    _salt_okunur_yap(w / "alt")
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        ok = ts.wt_kapat(proje, str(w), zorla=True)
    kalan_sat = [s for s in tampon.getvalue().splitlines() if "KALDI" in s]
    sonuc("V11b `wt_kapat --zorla` ReadOnly alt dizinli worktree'yi KAPATTI",
          ok and not w.exists(), kalan_sat[0].strip() if kalan_sat else None)
    _yazilabilir_geri(kok)
    # V11c: siniflandirma — handle kilidi ile ReadOnly AYRI teshis
    class _Kilit(PermissionError):
        winerror = 32
    ro = kok / "ro_c"
    ro.mkdir()
    (ro / "f.txt").write_text("x", encoding="utf-8")
    _salt_okunur_yap(ro / "f.txt")
    _salt_okunur_yap(ro)
    s_kilit = ts._silme_hatasi_sinifi(str(kok / "yok.txt"), _Kilit(13, "kilitli"))
    s_ro = ts._silme_hatasi_sinifi(str(ro / "f.txt"), PermissionError(13, "erisim"))
    _yazilabilir_geri(kok)
    sonuc("V11c WinError 32 -> HANDLE KILIDI", "HANDLE" in s_kilit, s_kilit)
    sonuc("V11d salt-okunur yol -> ReadOnly (handle kilidi DEGIL)",
          "ReadOnly" in s_ro and "HANDLE" not in s_ro, s_ro)


def v5_siddet(cikti: str) -> None:
    """#80(2)c: gitignore'lu SCRATCH kapiyi kirmiziya boyamaz; HASAT ADAYI boyar."""
    # CAPA AYIRT EDICI OLMALI: duz `"w1:" in s` `② feat/w1:` satirina da takiliyordu
    # (olculdu: V5/V5b sahte-KIRMIZI dondu). Ayirt edici alan `izlenen/izlenmeyen` ibaresi.
    sat = [s for s in cikti.splitlines() if "izlenen/izlenmeyen" in s and " w1:" in s]
    sonuc("V5 scratch-only worktree izlenen=0",
          bool(sat) and "izlenen/izlenmeyen 0 kayit" in sat[0],
          sat[0].strip() if sat else None)
    sonuc("V5b yok-sayilanlar GORUNUR ama HASAT ADAYI 0",
          bool(sat) and "yok-sayilan" in sat[0] and "0'i HASAT ADAYI" in sat[0],
          sat[0].strip() if sat else None)
    hasat = [s for s in cikti.splitlines() if "3b" in s or "③b" in s]
    sonuc("V5c gitignore'lu ama scratch-DEGIL -> HASAT ADAYI raporlanir",
          any("w2" in s for s in hasat), hasat[0].strip() if hasat else None)


def v6_bag_kaldir(ts, kok: Path) -> None:
    """#80(3): bag ONCE kaldirilir ve HEDEFE DOKUNULMAZ (platform-guvenli)."""
    hedef = kok / "hedef_agac"
    hedef.mkdir()
    (hedef / "degerli.txt").write_text("SILINMEMELI\n", encoding="utf-8")
    bag = kok / "bag"
    kuruldu = False
    if os.name == "nt":
        kuruldu = subprocess.run(["cmd", "/c", "mklink", "/J", str(bag), str(hedef)],
                                 capture_output=True).returncode == 0
    if not kuruldu:
        try:
            os.symlink(str(hedef), str(bag), target_is_directory=True)
            kuruldu = True
        except OSError:
            kuruldu = False
    if not kuruldu:
        sonuc("V6 bag kurulamadi -> DOGRULANAMADI (atlandi)", True, "platform bag desteklemedi")
        return
    # ⛔ COKME != FAIL: `_bag_kaldir` patlarsa bu bir OLCUM sonucudur, harness arizasi
    # degil -> kirmizi vektore cevrilir (aksi halde mutasyon "cokme" diye YUTULUR).
    try:
        ts._bag_kaldir(bag)
    except Exception as exc:  # noqa: BLE001
        sonuc("V6 bag kaldirildi", False, f"{type(exc).__name__}: {exc}")
        sonuc("V6b HEDEF DOKUNULMADAN duruyor", (hedef / "degerli.txt").is_file())
        return
    sonuc("V6 bag kaldirildi", not bag.exists() and not bag.is_symlink())
    sonuc("V6b HEDEF DOKUNULMADAN duruyor", (hedef / "degerli.txt").is_file(),
          "rm -rf/rmtree bir junction'a girerse HEDEFI siler")


def v7_platform(src: str) -> None:
    """#18: `mklink` KOSULSUZ degil; POSIX dalinda `os.symlink` var. (`src` -> v4 notu)"""
    fn = next((n for n in ast.walk(ast.parse(src))
               if isinstance(n, ast.FunctionDef) and n.name == "junction_kur"), None)
    if fn is None:
        sonuc("V7 junction_kur AST'te bulundu", False)
        return
    nt_dali = any("os.name" in (ast.get_source_segment(src, n.test) or "")
                  for n in ast.walk(fn) if isinstance(n, ast.If))
    symlink = any(isinstance(n, ast.Attribute) and n.attr == "symlink" for n in ast.walk(fn))
    sonuc("V7 `os.name` platform dali VAR", nt_dali)
    sonuc("V7b POSIX dalinda `os.symlink` VAR", symlink)


def v8_statusline(kok: Path, mut=None) -> None:
    """#79: worktree KOPYASI degil KANONIK dosya cozulur."""
    sl = modul(STATUSLINE, mut, ad="mut_statusline")
    proje = kok / "SLPROJ"
    kanonik = proje / "SOURCE_CODES" / "SD" / "ZSD001_CLC"
    kanonik.mkdir(parents=True)
    (kanonik / "SESSION_NOTES.md").write_text("KANONIK\n", encoding="utf-8")
    # BAYAT KOPYA: `.claude/` alfabetik olarak `SOURCE_CODES`ten ONCE gelir -- gercek
    # vakada da (olculdu 2026-08-28) once o donuyordu.
    bayat = proje / ".claude" / "worktrees" / "agent-x" / "SOURCE_CODES" / "SD" / "ZSD001_CLC"
    bayat.mkdir(parents=True)
    (bayat / "SESSION_NOTES.md").write_text("BAYAT\n", encoding="utf-8")
    bulunan = sl._find_session_notes_by_name(proje, "ZSD001_CLC")
    metin = bulunan.read_text(encoding="utf-8").strip() if bulunan else "<YOK>"
    sonuc("V8 ada-gore arama KANONIK dosyayi buldu", metin == "KANONIK", metin)
    en_yeni = sl._latest_session_notes(proje)
    sonuc("V8b en-yeni arama worktree kopyasina DUSMEDI",
          en_yeni is not None and "worktrees" not in str(en_yeni).replace("\\", "/"), en_yeni)


def v9_yol_oneki(mut=None) -> None:
    """#39 I-5: hook metnindeki isaretci PROJE kokunden cozulebilmeli -> `core/` oneki."""
    src = SESSION_START.read_text(encoding="utf-8")
    if mut is not None:
        if mut[0] not in src:
            raise Kurulamadi(f"capa yok: {mut[0][:60]!r}")
        src = src.replace(mut[0], mut[1], 1)
    # CAPA `"core/governance" in src` DEGIL (dosyanin BASKA yerinde gecebilir):
    # `agent-teams-operating-model` gecen HER satirin onekli olmasi olculur.
    satirlar = [s for s in src.splitlines() if "agent-teams-operating-model" in s]
    oneksiz = [s.strip() for s in satirlar if "core/governance/agent-teams" not in s]
    sonuc("V9 hook isaretcisi `core/` onekli", bool(satirlar) and not oneksiz,
          oneksiz[0] if oneksiz else f"{len(satirlar)} satir")


# ---------------------------------------------------------------------------
def denetim_kos(ts, proje: Path) -> str:
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        ts.wt_denetim(proje)
    return tampon.getvalue()


def tur(ts_mut=None, sl_mut=None, ss_mut=None, sadece=None) -> None:
    ts_kaynak = mutasyonlu_kaynak(TEAM_SETUP, ts_mut)   # AST vektorleri BUNU olcer
    ts = modul(TEAM_SETUP, ts_mut, ad="mut_team_setup")
    with tempfile.TemporaryDirectory() as t:
        kok = Path(t)
        if sadece in (None, "denetim", "yol", "bag", "platform"):
            proje = kum_kur(kok)
            # w1: YALNIZ gitignore'lu scratch -> kapiyi kirmiziya BOYAMAMALI
            w1 = ts.wt_yolu(proje, "feat/w1")
            w1.parent.mkdir(parents=True, exist_ok=True)
            git(proje, "worktree", "add", "-q", "-b", "feat/w1", str(w1), "main")
            (w1 / ".tmp").mkdir()
            (w1 / ".tmp" / "scratch.txt").write_text("x", encoding="utf-8")
            # w2: gitignore'lu ama SCRATCH DEGIL -> HASAT ADAYI (kayit #39 I-4 sinifi)
            w2 = ts.wt_yolu(proje, "feat/w2")
            git(proje, "worktree", "add", "-q", "-b", "feat/w2", str(w2), "main")
            (w2 / "agent-memory").mkdir()
            (w2 / "agent-memory" / "MEMORY.md").write_text("ders", encoding="utf-8")
            # git'e KAYITSIZ yetimler
            yo = ts.wt_kok(proje) / "yetim-ozgun"
            yo.mkdir(parents=True)
            (yo / "ozgun.txt").write_text("BU ICERIK HICBIR COMMIT'TE YOK\n", encoding="utf-8")
            yg = ts.wt_kok(proje) / "yetim-gitte"
            yg.mkdir(parents=True)
            (yg / "ortak.txt").write_text("ayni icerik her yerde\n", encoding="utf-8")

            cikti = denetim_kos(ts, proje)
            if sadece in (None, "denetim"):
                v2_v3_yetim(cikti)
                v5_siddet(cikti)
            if sadece in (None, "yol"):
                v1_kanonik_yol(ts)
                v4_cherry(ts_kaynak)
            if sadece in (None, "bag"):
                v6_bag_kaldir(ts, kok)
            if sadece in (None, "platform"):
                v7_platform(ts_kaynak)
            for w in (w1, w2):
                git(proje, "worktree", "remove", "--force", str(w))
        if sadece in (None, "icerik"):
            icproje, icyollar = kum_icerik_kur(kok, ts)
            v10_icerik_matrisi(denetim_kos(ts, icproje), ts, icproje)
            for w in icyollar.values():
                git(icproje, "worktree", "remove", "--force", str(w))
        if sadece in (None, "kirli3"):
            v12_kirli_her_kolda(ts, kok)
        if sadece in (None, "silme"):
            v11_salt_okunur_silme(ts, kok)
        if sadece in (None, "statusline"):
            v8_statusline(kok, sl_mut)
        if sadece in (None, "yol_oneki"):
            v9_yol_oneki(ss_mut)


MUTASYONLAR = [
    ("M1 #79 prune kumesinden `worktrees` cikarilir", "statusline",
     ('"__pycache__", "worktrees", "attic", "fixtures"}',
      '"__pycache__", "attic", "fixtures"}'), "statusline"),
    ("M2 #79 budanmis yuruyus yerine HAM rglob", "statusline",
     ("    for dirpath, dirnames, filenames in os.walk(kok):",
      "    for _p in sorted(kok.rglob(SESSION_NOTE_NAME)):\n        yield _p\n"
      "    for dirpath, dirnames, filenames in []:"), "statusline"),
    ("M3 #18 platform dali sokulur (mklink KOSULSUZ)", "team_setup",
     ('    if os.name == "nt":\n        r = subprocess.run(["cmd", "/c", "mklink"',
      '    if True:\n        r = subprocess.run(["cmd", "/c", "mklink"'), "platform"),
    ("M4 #80 `git cherry` yerine `--is-ancestor`", "team_setup",
     ('c = _git(proje, "cherry", "-v", "main", f"refs/heads/{dal}")',
      'c = _git(proje, "merge-base", "--is-ancestor", "main", dal)'), "yol"),
    # ⛔ MUTASYON KUM DISINA YAZMAMALI. Ilk yazim `Path(os.sep + 'sabit')` idi ve
    # olculdu: mutasyon turu diskin KOKUNDE (`C:\sabit\.wt\PROJ\...`) 25 girdilik gercek
    # bir agac yaratti — worktree sinirinin disinda kalinti. Ayni "kalinti komsuyu
    # kirletir" sinifi, farkli yuzey. Mutasyon artik proje adini SABITLER: yol hala
    # projeye-bagimsiz olur (V1/V1b kirmizi doner) ama kum dizininin ICINDE kalir.
    ("M5 #80 kanonik kok proje adindan BAGIMSIZ hale gelir", "team_setup",
     ("    return proje.parent / WT_KOK_ADI / proje.name",
      '    return proje.parent / WT_KOK_ADI / "SABIT"'), "yol"),
    ("M6 #80 silme sirasi bozulur (bag yerine AGAC silinir)", "team_setup",
     ("    if link.is_symlink():\n        link.unlink()\n    else:\n        link.rmdir()",
      "    shutil.rmtree(link)"), "bag"),
    ("M7 #39 `core/` oneki sokulur", "session_start",
     ("Detay: core/governance/agent-teams-operating-model.md",
      "Detay: governance/agent-teams-operating-model.md"), "yol_oneki"),
    ("M8 #80 siddet ayrimi sokulur (`!!` de FAIL uretir)", "team_setup",
     ('        izlenen = [s for s in satir3 if not s.startswith("!!")]',
      "        izlenen = list(satir3)"), "denetim"),
    ("M9 #80 yetim olcumu nesne-veritabanina SORMAZ", "team_setup",
     ('            if _git(proje, "cat-file", "-e", sha).returncode != 0:\n'
      "                ozgun.append",
      "            if True:\n                ozgun.append"), "denetim"),
    # --- Issue #280: hukum icerikten, cherry yalniz ek sinyal ---
    ("M10 #280 hukum yeniden `git cherry`ye baglanir", "team_setup",
     ("    if not farkli:\n", "    if not c_arti:\n"), "icerik"),
    ("M11 #280 icerik main'e degil ortak ataya kiyaslanir", "team_setup",
     ('"-z", "main", ref, "--")', '"-z", taban, ref, "--")'), "icerik"),
    ("M12 #280 ALARM'dan 'BEKLENEBILIR' notu duser", "team_setup",
     ('    say(WARN, f"② {dal}: {ICERIK_FARKI_NOTU}")\n', ""), "icerik"),
    # --- Issue #284: ReadOnly oznitelik silmeyi kalici bloklamaz ---
    ("M13 #284 onarici isleyici chmod YAPMAZ", "team_setup",
     ("                os.chmod(hedef, os.stat(hedef).st_mode | stat.S_IWRITE)",
      "                pass"), "silme"),
    ("M14 #284 wt_kapat eski `rmtree(ignore_errors=True)`a doner", "team_setup",
     ("            kalan = _agac_sil(yol)",
      "            shutil.rmtree(yol, ignore_errors=True)"), "silme"),
    ("M15 #284 siniflandirma her seye 'handle kilidi' der", "team_setup",
     ('    if getattr(exc, "winerror", None) in (32, 33):',
      "    if True:"), "silme"),
    # --- PR #300 bug-gate F1/F2/F4/F5 ---
    ("M16 F2 dalin-dosyalari diff'inden `--no-renames` duser", "team_setup",
     ('"diff", "--no-renames", "--name-only", "-z", taban, ref, "--")',
      '"diff", "--name-only", "-z", taban, ref, "--")'), "icerik"),
    ("M17 F1 `refs/heads/` oneki duser (kisa ad tag'e cozulebilir)", "team_setup",
     ('    ref = f"refs/heads/{dal}"\n', "    ref = dal\n"), "icerik"),
    ("M18 F4 detached kolunda `continue` geri gelir (③ atlanir)", "team_setup",
     ("            bulgu = 1\n        elif _dal_hukmu_bas(proje, dal):\n",
      "            bulgu = 1\n            continue\n        elif _dal_hukmu_bas(proje, dal):\n"),
     "kirli3"),
    ("M19 F4 ② ALARM/hata kolunda `continue` geri gelir (③ atlanir)", "team_setup",
     ("        elif _dal_hukmu_bas(proje, dal):\n            bulgu = 1\n",
      "        elif _dal_hukmu_bas(proje, dal):\n            bulgu = 1\n            continue\n"),
     "kirli3"),
    ("M20 F5 ALARM'dan 'yerel main bayat' notu duser", "team_setup",
     ('    say(WARN, f"② {dal}: {BAYAT_MAIN_NOTU}")\n', ""), "icerik"),
]


def main() -> int:
    if not MUTASYON:
        print("== worktree_yasam_dongusu -- BUGUNKU KOD (bilinen-TEMIZ) ==")
        tur()
        print(f"\nTOPLAM: {_sayac['pass']} PASS / {_sayac['fail']} FAIL")
        return 0 if _sayac["fail"] == 0 else 1

    print("== MUTASYON TURU: her fix SOKULUR, vektor KIRMIZIYA donmeli ==")
    kacan = 0
    for ad, hedef, mut, sadece in MUTASYONLAR:
        _sayac["pass"] = _sayac["fail"] = 0
        gizli = io.StringIO()
        try:
            with contextlib.redirect_stdout(gizli):
                tur(ts_mut=mut if hedef == "team_setup" else None,
                    sl_mut=mut if hedef == "statusline" else None,
                    ss_mut=mut if hedef == "session_start" else None,
                    sadece=sadece)
        except Kurulamadi as exc:
            print(f"  [KURULAMADI] {ad} -- {exc}   (KACTI DEGILDIR)")
            kacan += 1
            continue
        except Exception as exc:  # noqa: BLE001
            print(f"  [YAKALANDI] {ad} -- mutasyon COKME uretti: {type(exc).__name__}: {exc}")
            continue
        if _sayac["fail"] == 0:
            print(f"  [KACTI] {ad} -- korpus bu mutasyonu GORMEDI "
                  f"({_sayac['pass']} vektor hala yesil)")
            kacan += 1
        else:
            print(f"  [YAKALANDI] {ad} -- {_sayac['fail']} vektor kirmizi")
    print(f"\nMUTASYON SONUCU: {len(MUTASYONLAR) - kacan}/{len(MUTASYONLAR)} yakalandi")
    return 0 if kacan == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
