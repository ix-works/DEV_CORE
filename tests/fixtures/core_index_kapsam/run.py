# -*- coding: utf-8 -*-
"""core_index_kapsam — CORE-INDEX hangi core dokümanlarını GÖRÜYOR (KAYIT S3 + Q331).

KÖK (S3): `build_core_index.ALANLAR` yalnız `governance/decisions`'ı taşıyordu; `core/governance/`
DÜZ dosyaları indekse HİÇ girmiyordu. Görünmeyenlerin arasında `infra-changelog.md` ve
`infra-test-recipes.md` de vardı — yani infra-expert'in F0'da okumak ZORUNDA olduğu iki
dosya, tam da junction-körlüğünü kapatmak için var olan artefaktın kendisinde yoktu
(D29: kökten arama core'u görmez; sıfır sonuç "böyle bir kural yok" diye okunur).

KÖK (Q331, 2026-09-18): aynı körlüğün İKİ yüzeyi daha. Bir tüketici projenin indeksinde
`claude/`=0 · `tests/`=0 · `run_battery`=0 · `mutasyon`=0 · `spawn-brief`=0 eşleşme ölçüldü;
24 ajanlık bir turda spawn şablonu ve mutasyon altyapısı bulunamadı, sıfırdan icat edildi.
Fix: (a) `claude/templates` doküman alanı · (b) `tests/*.py` (DÜZ) için AYRI önekli
KOD İŞARETÇİSİ bölümü (doküman sayacına girmez; fixture'lar tek tek listelenmez).

FP ÇAPASI (bu fixture'ın omurgası): indeks ŞİŞMEMELİ. `governance`'ı `rglob` ile eklemek
`decisions/`i ÇİFTLERDİ; `CORE-INDEX.md`'nin kendisi de üretilmiş bir dosyadır ve indekse
girerse ajanı kendi indeksine yönlendirir. Q331 ile iki yeni FP çapası: `core/claude/`'un
templates DIŞI kalanı hâlâ yasak (V5) · `tests/fixtures/` altı TEK TEK listelenmez (V12 —
churn: her infra PR'ı fixture ekler, liste basılsaydı her PR tüketen tüm projelerde C-IDX-01'i
"bayat"a düşürürdü) · işaretçiler doküman sayacına GİRMEZ (V13).

Koşum:  python tests/fixtures/core_index_kapsam/run.py [--mutasyon-<kip>]
Çıkış:  0 hepsi geçti · 1 vektör düştü (mutasyon kipinde BEKLENEN) · 2 DOGRULANAMADI
        (çapa `count != 1` · mutant derlenmiyor · kontrol grubu bozuk · beklenen vektör
        mutasyonda DÜŞMEDİ — başka vektörün düşmesi "doğru test kırıldı" demek değildir)

MUTASYON (fixture-içi; üreticinin kaynağı BELLEKTE değiştirilip exec edilir — çalışma
ağacına HİÇBİR dosya yazılmaz, `__file__` gerçek yol kalır ki `CORE` gerçek ağacı tarasın;
kardeş `core_index_siralama` ile aynı desen):
  --mutasyon-templates-yok   ALANLAR'dan "claude/templates" çıkar          -> V9
  --mutasyon-isaretci-yok    ISARETCI_ALANLAR boşaltılır                  -> V10 + V10b
  --mutasyon-dokuman-onekli  işaretçi öneki doküman önekine çakışır       -> V5 + V13
  --mutasyon-ozyineli        işaretçi taraması rglob (fixtures sızar)      -> V11 + V12
  --mutasyon-dar-istisna     `_kod_ozeti` yalnız OSError yakalar (çöker)   -> V14
  --mutasyon-bos-bolum       boş işaretçi alanı yine başlık basar         -> V15
  --mutasyon-kirpmasiz       özet satırı kenar boşluğu kırpılmaz          -> V14
  --mutasyon-sira            işaretçi satırları ters sırada               -> V16
  (Listelenen = BEKLENEN düşüşler; fixture her kipte bunların GERÇEKTEN düştüğünü ayrıca
  denetler, düşmediyse exit 2.)
Fix-ÖNCESİ üretici (e0e58ba) bu korpusta: 12/19 (V9-V11, V13-V15 düşer; çökmez).
Vektörler: V1-V8 S3 · V9-V13 Q331 kapsam/çapa · V14 bozuk-girdi çökmezliği (3. bağlam,
sentetik ağaç) · V15 eksik dizin (kırpılmış tüketici klonu) · V16 platform determinizmi.
Tarihsel (S3, elle yapılmıştı): DUZ_ALANLAR'ı boşalt → V1/V2 · HARIC'i boşalt → V4 ·
DUZ_ALANLAR yerine ALANLAR'a "governance" ekle (rglob) → V3.
"""
from __future__ import annotations

import re
import shutil
import sys
import tempfile
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

KOK = Path(__file__).resolve().parents[3]
URETICI = KOK / "scripts" / "build_core_index.py"
sys.path.insert(0, str(KOK / "scripts"))
import build_core_index as B  # noqa: E402

# kip -> (eski, yeni) — YALNIZ bellekteki kopyaya uygulanır
MUTLAR = {
    "--mutasyon-templates-yok": (', "claude/templates"]', "]"),
    "--mutasyon-isaretci-yok": ('ISARETCI_ALANLAR = ["tests"]', "ISARETCI_ALANLAR = []"),
    "--mutasyon-dokuman-onekli": ('ISARETCI_ONEK = "- (kod) "', 'ISARETCI_ONEK = "- "'),
    "--mutasyon-ozyineli": ('_dosyalar(alan, False, "*.py")', '_dosyalar(alan, True, "*.py")'),
    "--mutasyon-dar-istisna": (
        "except Exception:  # noqa: BLE001 — bilinçli: yukarıdaki ÇÖKMEZLİK notu",
        "except (OSError, UnicodeDecodeError):"),
    "--mutasyon-bos-bolum": (
        'dosyalar = _dosyalar(alan, False, "*.py")\n        if not dosyalar:\n'
        '            continue\n',
        'dosyalar = _dosyalar(alan, False, "*.py")\n'),
    "--mutasyon-kirpmasiz": ("            return satir.strip()\n", "            return satir\n"),
    "--mutasyon-sira": (
        "        for f in dosyalar:\n            rel = f.relative_to(CORE).as_posix()\n"
        "            ozet = _kod_ozeti(f)",
        "        for f in reversed(dosyalar):\n            rel = f.relative_to(CORE).as_posix()\n"
        "            ozet = _kod_ozeti(f)"),
}
BEKLENEN_DUSUS = {
    "--mutasyon-templates-yok": ("V9",),
    "--mutasyon-isaretci-yok": ("V10", "V10b"),
    "--mutasyon-dokuman-onekli": ("V5", "V13"),
    "--mutasyon-ozyineli": ("V11", "V12"),
    "--mutasyon-dar-istisna": ("V14",),
    "--mutasyon-bos-bolum": ("V15",),
    "--mutasyon-kirpmasiz": ("V14",),
    "--mutasyon-sira": ("V16",),
}

# Tüketicinin gördüğü METİN sözleşmesi — üreticinin sabitine BAKILMAZ (sabit değişirse
# çapa onu izlemesin, yakalasın).
DOKUMAN_ONEK = "- [`core/"
ISARETCI_ONEK = "- (kod) [`core/"

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(ok), detay))


def _yol(satir: str) -> str:
    return satir.split("`")[1]          # "core/<rel>"


def _bellekte_yukle(kaynak: str, ad: str) -> types.ModuleType:
    m = types.ModuleType(ad)
    m.__file__ = str(URETICI)
    exec(compile(kaynak, str(URETICI), "exec"), m.__dict__)  # noqa: S102
    return m


def modulu_kur(kip: str | None) -> types.ModuleType:
    if not kip:
        return B
    eski, yeni = MUTLAR[kip]
    ham = URETICI.read_text(encoding="utf-8")
    n = ham.count(eski)
    if n != 1:
        print(f"[DOGRULANAMADI] mutasyon capasi {n} kez eslesti (1 bekleniyordu) ({kip}) "
              f"-> mutasyon UYGULANMADI; 'gecti' sonucu ANLAMSIZ olurdu.\n  aranan: {eski!r}")
        raise SystemExit(2)
    # KONTROL GRUBU: bellekte exec yolu MUTASYONSUZ kaynakla gerçek import'la AYNI
    # çıktıyı vermeli; vermezse ölçülen şey mutasyon değil yükleme yolu olurdu.
    try:
        ikiz = _bellekte_yukle(ham, "_ikiz_build_core_index")
    except Exception as e:  # noqa: BLE001
        print(f"[DOGRULANAMADI] kontrol grubu yuklenemedi: {e!r}")
        raise SystemExit(2)
    if ikiz.uret() != B.uret():
        print("[DOGRULANAMADI] kontrol grubu bozuk: bellekteki MUTASYONSUZ kopya gercek "
              "modulden FARKLI uretiyor -> olculen sey ORTAM olurdu")
        raise SystemExit(2)
    bozuk = ham.replace(eski, yeni, 1)
    try:
        return _bellekte_yukle(bozuk, "_mut_build_core_index")
    except SyntaxError as e:
        print(f"[DOGRULANAMADI] mutant SOZDIZIMI BOZUK ({kip}): {e}")
        raise SystemExit(2)


def vektorler(M: types.ModuleType) -> None:
    metin = M.uret()
    satirlar = metin.split("\n")
    dok = [s for s in satirlar if s.startswith(DOKUMAN_ONEK)]
    yollar = [_yol(s) for s in dok]
    isr = [s for s in satirlar if s.startswith(ISARETCI_ONEK)]
    isr_yol = [_yol(s) for s in isr]

    # ── V1 — F0'ın ZORUNLU iki dosyası indekste ─────────────────────────────────
    F0 = ["core/governance/infra-changelog.md", "core/governance/infra-test-recipes.md"]
    eksik = [y for y in F0 if y not in yollar]
    kontrol("V1 F0 zorunlu dosyaları (infra-changelog + infra-test-recipes) indekste",
            not eksik, f"eksik={eksik}")

    # ── V2 — diğer governance düz dokümanları da görünür ────────────────────────
    BEKLENEN = ["core/governance/agent-teams-operating-model.md",
                "core/governance/tooling-plugins.md",
                "core/governance/removed-controls.md"]
    eksik2 = [y for y in BEKLENEN if y not in yollar]
    kontrol("V2 governance düz dokümanları (operating-model/tooling-plugins/removed-controls)",
            not eksik2, f"eksik={eksik2}")

    # ── V3 — FP ÇAPASI: hiçbir dosya İKİ KEZ listelenmiyor (rglob-çiftleme tuzağı) ──
    hepsi = yollar + isr_yol
    tekrar = sorted({y for y in hepsi if hepsi.count(y) > 1})
    kontrol("V3 FP ÇAPASI: mükerrer satır YOK (governance rglob decisions'ı çiftlemiyor)",
            not tekrar, f"mükerrer={tekrar}")

    # ── V4 — FP ÇAPASI: üretilmiş CORE-INDEX.md kendini listelemiyor ────────────
    kontrol("V4 FP ÇAPASI: `governance/CORE-INDEX.md` indekste YOK (özyineli referans)",
            "core/governance/CORE-INDEX.md" not in yollar,
            f"bulunan={[y for y in yollar if 'CORE-INDEX' in y]}")

    # ── V5 — FP ÇAPASI: kod dizinleri DOKÜMAN olarak hâlâ DIŞARIDA ──────────────
    #   Q331 DARALTMASI: `core/claude/templates/` serbest; `core/claude/` altındaki
    #   DİĞER her şey (memory-seed · rules · agents · settings …) hâlâ yasak.
    #   `core/tests/` doküman satırı olarak YASAK — yalnız işaretçi bölümünde izinli.
    sizinti = [y for y in yollar
               if y.startswith(("core/scripts/", "core/mcp_servers/", "core/tests/",
                                "core/intake/", "core/attic/"))
               or (y.startswith("core/claude/")
                   and not y.startswith("core/claude/templates/"))]
    kontrol("V5 FP ÇAPASI: scripts/mcp_servers/tests + claude/(templates DIŞI) DOKÜMAN "
            "olarak sızmadı", not sizinti, f"sızan={sizinti[:5]}")

    # ── V6 — REGRESYON ÇAPASI: eski kapsam AYNEN duruyor ────────────────────────
    for alan, en_az in (("core/playbook/", 40), ("core/standards/", 8),
                        ("core/governance/decisions/", 20)):
        n = sum(1 for y in yollar if y.startswith(alan))
        kontrol(f"V6 eski kapsam korunuyor: {alan} ≥ {en_az} doküman", n >= en_az,
                f"bulunan={n}")

    # ── V7 — 3. BAĞLAM: --check karşılaştırması damgayı YOK SAYIYOR ─────────────
    damgali = M._damga() + metin
    kontrol("V7 3.BAĞLAM: damga --check kıyasında ayıklanıyor (her koşumda sahte-BAYAT yok)",
            M._DAMGA_RE.sub("", damgali, count=1) == metin,
            f"ayıklanan={M._DAMGA_RE.sub('', damgali, count=1)[:60]!r}")

    # ── V8 — indeks GERÇEKTEN diskteki dosyaları gösteriyor (yol doğruluğu) ─────
    kirik = [y for y in yollar if not (KOK / y[len("core/"):]).is_file()][:5]
    kontrol("V8 indeksteki her yol diskte GERÇEKTEN var (kırık yol = sessiz yanlış yönlendirme)",
            not kirik, f"kırık={kirik}")

    # ── V9 — Q331(a): spawn şablonu DOKÜMAN satırı olarak indekste ──────────────
    kontrol("V9 Q331: `core/claude/templates/spawn-brief.md` doküman satırı VAR",
            "core/claude/templates/spawn-brief.md" in yollar,
            f"claude/ satırları={[y for y in yollar if y.startswith('core/claude/')]}")

    # ── V10 — Q331(b): mutasyon altyapısının giriş noktası işaretçide ───────────
    rb = [s for s in isr if _yol(s) == "core/tests/run_battery.py"]
    kontrol("V10 Q331: işaretçide `core/tests/run_battery.py` VAR ve özetinde 'mutasyon' geçiyor",
            len(rb) == 1 and "mutasyon" in rb[0].split("`)", 1)[-1].lower(),
            f"satır={rb}")

    # ── V10b — bölüm başlığı SABİT metinle yönteme + korpusa yönlendiriyor ──────
    m_bas = re.search(r"^## Kod isaretcileri — `core/tests/`.*?(?=^- \(kod\)|\Z)",
                      metin, re.MULTILINE | re.DOTALL)
    bas = m_bas.group(0) if m_bas else ""
    gerekli = ["howto-infra-fix-proseduru.md", "§D2", "core/tests/fixtures/<ad>/run.py",
               "--mutasyon", "run_battery.py"]
    kontrol("V10b işaretçi başlığı §D2 + fixture korpusu + bulma komutuna yönlendiriyor",
            bool(bas) and all(g in bas for g in gerekli),
            f"bulundu={bool(bas)} eksik={[g for g in gerekli if g not in bas]}")

    # ── V11 — işaretçi yolları diskte var, DÜZ (alt dizin yok), .py ─────────────
    bozuk_isr = [y for y in isr_yol
                 if not (KOK / y[len("core/"):]).is_file()
                 or not y.endswith(".py")
                 or Path(y).parent.as_posix() != "core/tests"]
    kontrol("V11 her işaretçi yolu diskte var · `core/tests/` DÜZ · .py",
            bool(isr_yol) and not bozuk_isr, f"yollar={isr_yol} bozuk={bozuk_isr}")

    # ── V12 — FP/CHURN ÇAPASI: tests/fixtures/ altı TEK TEK listelenmiyor ───────
    fixture_adlari = sorted(d.name for d in (KOK / "tests" / "fixtures").iterdir()
                            if d.is_dir())
    listelenen = [a for a in fixture_adlari if f"core/tests/fixtures/{a}" in metin]
    kontrol("V12 CHURN ÇAPASI: hiçbir `tests/fixtures/<ad>` indekste anılmıyor "
            f"({len(fixture_adlari)} dizin denetlendi)",
            bool(fixture_adlari) and not listelenen, f"anılan={listelenen[:5]}")

    # ── V13 — doküman sayacı işaretçileri SAYMIYOR (üç sayaç aynı ifadeyi kullanır) ─
    sayac = metin.count("\n" + DOKUMAN_ONEK)
    m_top = re.search(r"\*\*Toplam (\d+) dokuman · (\d+) kod isaretcisi\.\*\*", metin)
    kontrol("V13 doküman sayacı = doküman satırı = dipnot; işaretçiler AYRI sayılıyor",
            m_top is not None and sayac == len(dok) == int(m_top.group(1))
            and int(m_top.group(2)) == len(isr)
            and not (set(isr_yol) & set(yollar)),
            f"sayac={sayac} dok={len(dok)} isr={len(isr)} "
            f"dipnot={m_top.groups() if m_top else None}")

    # ── V14 — 3. BAĞLAM (sentetik ağaç): okunamayan .py SESSİZCE atlanmıyor ─────
    #   Görev-dışı dosya şekilleri: sözdizimi bozuk · docstring'siz · BOM + yorum +
    #   boş ilk satırlı docstring · UTF-8 olmayan bayt · alt dizindeki .py (DÜZ kuralı).
    #   Modül SABİTLERİ burada açıkça kurulur (mutasyon kipinde de bu vektör ÜRETİCİNİN
    #   özetleme/çökmezlik davranışını ölçer, mutasyonun boşalttığı listeyi değil).
    tmp = Path(tempfile.mkdtemp(prefix="q331_"))
    bos = Path(tempfile.mkdtemp(prefix="q331b_"))
    # getattr: fix-ÖNCESİ üreticide bu sabit YOK — fixture çökmemeli, ÖLÇMELİ (D2/1)
    eski = (M.CORE, M.ALANLAR, M.DUZ_ALANLAR, M.HARIC, getattr(M, "ISARETCI_ALANLAR", None))
    s_isr: dict[str, str] = {}
    hata14 = hata15 = ""
    sm = sb = ""
    try:
        t = tmp / "tests"
        (t / "fixtures" / "x").mkdir(parents=True)
        (t / "bozuk.py").write_text('"""acilmayan\n', encoding="utf-8")
        (t / "docsuz.py").write_text("x = 1\n", encoding="utf-8")
        (t / "bomlu.py").write_bytes("﻿# yorum\n\"\"\"\n\n  Ilk dolu satir.  \nikinci\n\"\"\"\n"
                                     .encode("utf-8"))
        (t / "latin.py").write_bytes(b'"""caf\xe9"""\n')
        (t / "nullu.py").write_bytes(b'"""null\x00bayt"""\n')
        # autocrlf'li Windows checkout'u taklit: CRLF satır sonlu docstring
        (t / "crlf.py").write_bytes(b'"""CRLF ozet satiri\r\n\r\nikinci\r\n"""\r\nx = 1\r\n')
        (t / "fixtures" / "x" / "run.py").write_text('"""gizli"""\n', encoding="utf-8")
        M.CORE, M.ALANLAR, M.DUZ_ALANLAR, M.HARIC = tmp, [], [], set()
        M.ISARETCI_ALANLAR = ["tests"]
        try:
            sm = M.uret()
        except Exception as e:  # noqa: BLE001 — çökme ÖLÇÜLÜR, fixture çökmez (D2)
            hata14 = repr(e)
        s_isr = {_yol(s): s for s in sm.split("\n") if s.startswith(ISARETCI_ONEK)}

        # V15 — EKSİK DİZİN: `tests/` ve `claude/templates/` OLMAYAN (kırpılmış) klon
        M.CORE, M.ALANLAR, M.DUZ_ALANLAR, M.HARIC = bos, ["claude/templates"], [], set()
        try:
            sb = M.uret()
        except Exception as e:  # noqa: BLE001
            hata15 = repr(e)
    finally:
        M.CORE, M.ALANLAR, M.DUZ_ALANLAR, M.HARIC, M.ISARETCI_ALANLAR = eski
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(bos, ignore_errors=True)
    bek = {f"core/tests/{a}.py" for a in ("bozuk", "docsuz", "bomlu", "latin", "nullu", "crlf")}
    ok14 = (not hata14 and set(s_isr) == bek
            and s_isr["core/tests/bomlu.py"].endswith("— Ilk dolu satir.")
            and s_isr["core/tests/crlf.py"].endswith("— CRLF ozet satiri")
            and all("—" not in s_isr[f"core/tests/{a}.py"]
                    for a in ("bozuk", "docsuz", "latin", "nullu"))
            and not any("\r" in s for s in s_isr.values()))
    kontrol("V14 3.BAĞLAM: bozuk/null-bayt/UTF-8-dışı/docstring'siz .py satırı YİNE basılıyor "
            "(özet boş, üretim ÇÖKMÜYOR) · BOM+yorum+boş satır+CRLF doğru özetleniyor · "
            "alt dizin sızmıyor",
            ok14, f"hata={hata14} satirlar={sorted(s_isr)} "
                  f"bomlu={s_isr.get('core/tests/bomlu.py')!r} crlf={s_isr.get('core/tests/crlf.py')!r}")
    kontrol("V15 EKSİK DİZİN: `tests/` ve `claude/templates/` yokken uret() ÇÖKMÜYOR, "
            "iki bölüm de sessizce atlanıyor",
            not hata15 and bool(sb) and "Kod isaretcileri" not in sb
            and "core/claude/templates/" not in sb
            and "**Toplam 0 dokuman · 0 kod isaretcisi.**" in sb,
            f"hata={hata15} cikti_sonu={sb[-120:]!r}")

    # ── V16 — PLATFORM DETERMİNİZMİ (gerçek ağaç): iki çağrı BAYT-EŞ · `\r` yok ──
    #   Tüketici CI'ı (`--ci-check`) Windows'ta üretilen indeksi Linux'ta aynı
    #   core-commit'te yeniden üretip kıyaslar; çağrıya/ortama bağlı tek bayt = sahte-BAYAT.
    ikinci = M.uret()
    kontrol("V16 determinizm: uret() iki çağrıda bayt-eş · işaretçi/doküman satırlarında `\\r` YOK "
            "· işaretçi sırası = `_siralama_anahtari` sırası",
            ikinci.encode("utf-8") == metin.encode("utf-8")
            and not any("\r" in s for s in isr + dok)
            and isr_yol == sorted(isr_yol),
            f"es={ikinci == metin} r_var={[s[:40] for s in isr + dok if chr(13) in s][:3]}")


def main() -> int:
    argv = sys.argv[1:]
    bilinmeyen = [a for a in argv if a not in MUTLAR]
    if bilinmeyen:
        print(f"[KULLANIM] bilinmeyen argüman: {bilinmeyen} — geçerli: {sorted(MUTLAR)}")
        return 2
    kip = argv[0] if argv else None
    M = modulu_kur(kip)
    vektorler(M)

    gecen = sum(1 for _, ok, _ in SONUC if ok)
    print(f"=== core_index_kapsam (S3 + Q331) {'[' + kip + ']' if kip else '[taban]'} ===")
    for ad, ok, detay in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
        if not ok:
            print(f"         -> {detay}")
    print(f"\n{gecen}/{len(SONUC)} OK")
    if not kip:
        return 0 if gecen == len(SONUC) else 1
    dusen = {ad.split(" ", 1)[0] for ad, ok, _ in SONUC if not ok}
    kacan = [v for v in BEKLENEN_DUSUS[kip] if v not in dusen]
    if kacan:
        print(f"[DOGRULANAMADI] MUTASYON {kip}: BEKLENEN vektör(ler) DÜŞMEDİ: {kacan} "
              f"(düşenler={sorted(dusen)}) — başka vektörün düşmesi doğru testin "
              "kırıldığını göstermez.")
        return 2
    print(f"  (MUTASYON {kip}: beklenen düşüş(ler) {list(BEKLENEN_DUSUS[kip])} GERÇEKLEŞTİ; "
          f"düşen tüm vektörler={sorted(dusen)})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
