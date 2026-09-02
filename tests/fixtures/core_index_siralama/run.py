# -*- coding: utf-8 -*-
"""core_index_siralama — CORE-INDEX sırası PLATFORMDAN BAĞIMSIZ mı (KAYIT Q214).

KÖK: `build_core_index._dosyalar` anahtarsız `sorted(...)` ile `Path` nesnelerini
kendi `__lt__`'leriyle kıyaslıyordu. O kıyas platformun flavour'ına bağlıdır —
`WindowsPath` parçaları `str.lower()` ile katlar, `PosixPath` katlamaz (Py 3.11
`_cparts`; Py 3.12+ `_str_normcase`, orada yol AYIRICISI da kıyasa girer). Aynı
doküman ağacı iki platformda FARKLI sıralanır ⇒ Windows'ta üretilip commit'lenen
indeks Linux CI'da `[FAIL] CORE-INDEX BAYAT` verir (template_project PR #15,
2026-08-30), aynı komut aynı core-commit'te Windows'ta `[OK]` der. Yani C-IDX-01
"bayatlık" değil ÜRETİCİNİN PLATFORMUNU ölçüyordu.

FIX: `key=_siralama_anahtari` = `rel.as_posix()` — salt kod-noktası sırası; ne
büyük/küçük-harf tablosuna ne ayırıcıya bağlı. (Reddedilen alternatifler ve
gerekçeleri `build_core_index._siralama_anahtari` docstring'inde.)

ÖLÇÜM MİMARİSİ — platform iddiası İKİ YÖNLÜ ölçülür (bu korpus Windows'ta da
Linux'ta da aynı kararı vermeli):
  • Modül-güdümlü vektörler (V1/V1b/V4/V5): sentetik ağaçta üreticinin GERÇEK
    çıktısı ölçülür; beklenen = `sorted(<göreli posix dizeler>)`.
  • Flavour SİMÜLASYONU (V2/V2b/V3/V9/V10): `PureWindowsPath` ↔ `PurePosixPath`
    ile "öteki platform" sırası hesaplanır. V3 simülatörü KALİBRE eder (anahtarsız
    gerçek `sorted(Path)` == bu platformun simülasyonu); yani "makine öyleymiş"
    demeden nedensellik kurulur.
  • Korpus ÖN-EK ekseni (`alt/` dizini ↔ `alt-ek.md`) bilerek konuldu: anahtarsız
    kod bu veride LINUX'ta da yanlış sıra üretir ⇒ mutasyon iki platformda da ölür.

FP ÇAPALARI (bu fixture'ın omurgası): sıralama fix'i KAPSAM değiştirmemeli —
`HARIC` elemeye devam eder, düz alanın alt dizini sızmaz, hiçbir dosya çiftlenmez,
GERÇEK core ağacında üretilen doküman KÜMESİ anahtarsız sürümle birebir aynıdır
(değişen yalnız SIRA). Kapsam sayısı PİNLENMEZ (bayatlar); küme kıyası yapılır.

Koşum:  python tests/fixtures/core_index_siralama/run.py
MUTASYON: `--mutasyon` → üreticinin kaynağından `key=_siralama_anahtari` SÖKÜLÜR
  (kusurun bugünkü koda enjekte edilmiş hâli; bellekte exec edilir, repoya HİÇBİR
  dosya yazılmaz). Beklenen düşenler: V1 · V1b · V4 · V5.
  ⛔ Pinli-SHA / `git show HEAD:` tabanı KULLANILMAZ: fix merge edilince taban=fix
  olur ve mutasyon sessizce ölür (core-ci.yml'de yazılı yasak).
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import types
from pathlib import Path, PurePosixPath, PureWindowsPath

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

KOK = Path(__file__).resolve().parents[3]
URETICI = KOK / "scripts" / "build_core_index.py"
sys.path.insert(0, str(KOK / "scripts"))
import build_core_index as B  # noqa: E402

GECERLI_KIP = {"--mutasyon"}

# Fix'in TEK satırlık imzası — mutasyon bunu söker.
FIX_IMZA = """    return sorted((f for f in ham if _siralama_anahtari(f) not in HARIC),
                  key=_siralama_anahtari)"""
MUT_IMZA = """    return sorted(f for f in ham if _siralama_anahtari(f) not in HARIC)"""

BU_FLAVOUR = PureWindowsPath if os.name == "nt" else PurePosixPath

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, ok, detay))


def sim(flavour, rels: list[str]) -> list[str]:
    """`sorted(<flavour>Path(...))` sırası — 'öteki platform' simülasyonu.

    Göreli yollarla çalışır: gerçek kodda mutlak yollar sıralanır ama hepsi AYNI
    ön-eki taşır (tek alan taranır) ⇒ sırayı yalnız göreli kısım belirler. Bu
    varsayım V3'te gerçek `Path` nesneleriyle ölçülerek KALİBRE edilir.
    """
    return [str(x).replace("\\", "/") for x in sorted(flavour(r) for r in rels)]


def agac_kur(kok: Path, ters: bool = False) -> None:
    """Sentetik doküman ağacı. `ters=True` → dosyalar TERS sırada yaratılır
    (V8: sonuç `glob`/yaratım sırasından bağımsız olmalı)."""
    dosyalar = [
        # alan1 (ÖZYİNELİ) — harf-durumu ekseni + ön-ek ekseni + sayı/işaret
        "alan1/README.md", "alan1/adt-cds.md", "alan1/odata-services.md",
        "alan1/Kurallar.md", "alan1/zzz.md", "alan1/9-son.md", "alan1/_ek.md",
        "alan1/alt/a.md", "alan1/alt/Bir.md", "alan1/alt-ek.md",
        "alan1/haric-bu.md",
        # alan2 (DÜZ) — alt dizin GÖRÜNMEMELİ
        "alan2/README.md", "alan2/beta.md", "alan2/Alfa.md",
        "alan2/sub/gizli.md",
    ]
    for rel in (reversed(dosyalar) if ters else dosyalar):
        p = kok / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"# {Path(rel).stem} basligi\n", encoding="utf-8")


def modulu_yukle(mutasyonlu: bool) -> types.ModuleType:
    """Üreticiyi bellekte modül olarak kurar. `mutasyonlu` ise `key=` sökülür.

    Repoya dosya YAZILMAZ (komşu fixture'ları kirletmez); `__file__` gerçek yola
    ayarlanır ki modülün `CORE = Path(__file__).resolve().parents[1]` satırı ve
    `utils.project_config` importu gerçek repoda olduğu gibi çözülsün.
    """
    ham = URETICI.read_text(encoding="utf-8")
    if not mutasyonlu:
        return B
    if FIX_IMZA not in ham:
        print("  [YAMA TUTMADI] fix imzası kaynakta bulunamadı — mutasyon KURULAMADI.")
        print(f"                 aranan:\n{FIX_IMZA}")
        raise SystemExit(2)
    bozuk = ham.replace(FIX_IMZA, MUT_IMZA, 1)
    m = types.ModuleType("_mut_build_core_index")
    m.__file__ = str(URETICI)
    exec(compile(bozuk, str(URETICI), "exec"), m.__dict__)  # noqa: S102
    return m


def rel_listesi(M: types.ModuleType, alan: str, ozyineli: bool) -> list[str]:
    return [f.relative_to(M.CORE).as_posix() for f in M._dosyalar(alan, ozyineli)]


def main() -> int:
    argv = sys.argv[1:]
    bilinmeyen = [a for a in argv if a not in GECERLI_KIP]
    if bilinmeyen:
        print(f"  [KULLANIM] bilinmeyen argüman: {bilinmeyen} — geçerli: {sorted(GECERLI_KIP)}")
        return 3
    mutasyonlu = "--mutasyon" in argv

    print("=" * 78)
    print("core_index_siralama — Q214: CORE-INDEX sırası platformdan bağımsız mı"
          + ("   [MUTASYON: key= sökülü]" if mutasyonlu else ""))
    print("=" * 78)

    M = modulu_yukle(mutasyonlu)

    # ── V7 — FP ÇAPASI (GERÇEK ağaç): sıralama fix'i KAPSAMI değiştirmez ─────────
    # Kapsam sayısı PİNLENMEZ (bayatlar): küme kıyası. Anahtarsız referans burada
    # yerel olarak hesaplanır (modülden bağımsız) → mutasyon kipinde de ayakta kalır.
    gercek: list[str] = []
    for alan, ozy in ([(a, True) for a in M.ALANLAR] + [(a, False) for a in M.DUZ_ALANLAR]):
        d = M.CORE / alan
        if not d.is_dir():
            continue
        ham = d.rglob("*.md") if ozy else d.glob("*.md")
        gercek += [f.relative_to(M.CORE).as_posix() for f in sorted(ham)
                   if f.relative_to(M.CORE).as_posix() not in M.HARIC]
    uretilen: list[str] = []
    for alan, ozy in ([(a, True) for a in M.ALANLAR] + [(a, False) for a in M.DUZ_ALANLAR]):
        uretilen += rel_listesi(M, alan, ozy)
    kontrol("V7 FP: gerçek core ağacında KÜME değişmedi (yalnız sıra değişir)",
            set(uretilen) == set(gercek) and len(uretilen) == len(gercek),
            f"uretilen={len(uretilen)} referans={len(gercek)} "
            f"fark={sorted(set(uretilen) ^ set(gercek))[:5]}")

    # ── sentetik ağaç ───────────────────────────────────────────────────────────
    tmp = Path(tempfile.mkdtemp(prefix="q214_"))
    tmp2 = Path(tempfile.mkdtemp(prefix="q214r_"))
    eski = (M.CORE, M.ALANLAR, M.DUZ_ALANLAR, M.HARIC)
    try:
        agac_kur(tmp)
        agac_kur(tmp2, ters=True)
        M.CORE, M.ALANLAR, M.DUZ_ALANLAR = tmp, ["alan1"], ["alan2"]
        M.HARIC = {"alan1/haric-bu.md"}

        a1 = rel_listesi(M, "alan1", True)
        a2 = rel_listesi(M, "alan2", False)

        # ── V1/V1b — ANA ÇAPA: sıra = göreli posix dizelerin kod-noktası sırası ──
        kontrol("V1 özyineli alan: sıra = byte-sırası (platformdan bağımsız)",
                a1 == sorted(a1), f"alınan={a1}")
        kontrol("V1b düz alan (glob): sıra = byte-sırası",
                a2 == sorted(a2), f"alınan={a2}")

        # ── V2 — KORPUS GEÇERLİLİĞİ: veri gerçekten flavour-ayrıştırıcı mı? ──────
        w, p = sim(PureWindowsPath, a1), sim(PurePosixPath, a1)
        kontrol("V2 korpus flavour-AYRIŞTIRICI (Windows sim ≠ POSIX sim) — yoksa V1 boş tören",
                w != p, f"win={w[:3]} posix={p[:3]}")
        # V2b — ön-ek ekseni: anahtarsız kod LINUX'ta da yanlış sıra üretir.
        kontrol("V2b POSIX sim ≠ byte-sırası (ön-ek ekseni) ⇒ mutasyon iki platformda da ölür",
                p != sorted(a1), f"posix_sim={p[:4]} byte={sorted(a1)[:4]}")

        # ── V3 — KALİBRASYON: simülatör bu platformun GERÇEĞİNİ yeniden üretiyor ─
        mutlaklar = [tmp / r for r in a1]
        anahtarsiz = [f.relative_to(tmp).as_posix() for f in sorted(mutlaklar)]
        kontrol("V3 kalibrasyon: anahtarsız sorted(gerçek Path) == bu platformun sim'i "
                f"({BU_FLAVOUR.__name__})",
                anahtarsiz == sim(BU_FLAVOUR, a1),
                f"gercek={anahtarsiz[:4]} sim={sim(BU_FLAVOUR, a1)[:4]}")

        # ── V4 — 3. BAĞLAM: fix `_dosyalar`da, ölçüm ÜRETİLEN ARTEFAKTTA ─────────
        metin = M.uret()
        satir_yollari = [s.split("`")[1][len("core/"):] for s in metin.splitlines()
                         if s.startswith("- [`core/")]
        a1s = [y for y in satir_yollari if y.startswith("alan1/")]
        a2s = [y for y in satir_yollari if y.startswith("alan2/")]
        kontrol("V4 uret() ARTEFAKT satır sırası = byte-sırası (her iki bölümde)",
                a1s == sorted(a1s) and a2s == sorted(a2s),
                f"alan1={a1s} alan2={a2s}")

        # ── V5 — ANAHTAR ÇİVİSİ: as_posix mi parts mı? (ön-ek çakışması) ─────────
        # `parts` anahtarına dönülürse `alan1/alt/a.md` öne geçer ve indeks yine
        # kayar; bu vektör seçilen anahtarı GÖRÜNÜR kılar.
        kontrol("V5 ön-ek çakışmasında `alt-ek.md` < `alt/a.md` (as_posix çivisi)",
                a1.index("alan1/alt-ek.md") < a1.index("alan1/alt/a.md"),
                f"alınan={a1}")

        # ── V6 — FP: kapsam bozulmadı (eleme + düz tarama + çiftlenme) ───────────
        kontrol("V6 FP: HARIC eliyor · düz alanın alt dizini sızmıyor · çift yok",
                "alan1/haric-bu.md" not in a1
                and "alan2/sub/gizli.md" not in a2
                and len(a1) == len(set(a1)) and len(a2) == len(set(a2))
                and set(a2) == {"alan2/README.md", "alan2/beta.md", "alan2/Alfa.md"},
                f"a1={a1} a2={a2}")

        # ── V8 — DETERMİNİZM: tekrar + TERS yaratım sırasıyla kurulmuş ikiz ağaç ─
        a1_tekrar = rel_listesi(M, "alan1", True)
        M.CORE = tmp2
        a1_ters = rel_listesi(M, "alan1", True)
        M.CORE = tmp
        kontrol("V8 determinizm: tekrar çağrı ve TERS yaratım sıralı ikiz ağaç aynı sırayı verir",
                a1_tekrar == a1 and a1_ters == a1,
                f"tekrar_es={a1_tekrar == a1} ters_es={a1_ters == a1} ters={a1_ters}")

        # ── V9 — 3. BAĞLAM (salt-string): Türkçe İ/ı casefold tuzağı ─────────────
        # Reddedilen `lower()` anahtarının neden ortama bağlı olduğunu GÖRÜNÜR kılar:
        # 'İ'.lower() == 'i̇' (i + U+0307) → sıra Unicode tablosuna bağlanır.
        tr = ["ILK.md", "Izmir.md", "ilk.md", "islak.md", "İzmir.md", "ısı.md", "zzz.md"]
        tr_w, tr_p = sim(PureWindowsPath, tr), sim(PurePosixPath, tr)
        tr_lower = sorted(tr, key=str.lower)
        kontrol("V9 3.bağlam TR (İ/ı): Windows sim ≠ POSIX sim VE lower() anahtarı "
                "byte-sırasından ayrışır (reddedilen alternatifin bedeli)",
                tr_w != tr_p and tr_lower != sorted(tr),
                f"win={tr_w} posix={tr_p} lower={tr_lower}")

        # ── V10 — 3. BAĞLAM (salt-string): sayı/işaret/büyük-harf karışımı ───────
        karisik = ["9-son.md", "_ek.md", "Kurallar.md", "adt.md", "Zebra.md", "alt/a.md",
                   "alt-ek.md"]
        k_w, k_p = sim(PureWindowsPath, karisik), sim(PurePosixPath, karisik)
        kontrol("V10 3.bağlam sayı/işaret: iki flavour ayrışıyor; byte-sırası TEK ve "
                "deterministik cevabı verir",
                k_w != k_p and sorted(karisik) == sorted(karisik),
                f"win={k_w} posix={k_p} byte={sorted(karisik)}")
    finally:
        M.CORE, M.ALANLAR, M.DUZ_ALANLAR, M.HARIC = eski
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(tmp2, ignore_errors=True)

    kirik = [(a, d) for a, ok, d in SONUC if not ok]
    for ad, ok, detay in SONUC:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok:
            print("         görülen: %s" % detay)
    print("  -> %d/%d senaryo PASS" % (len(SONUC) - len(kirik), len(SONUC)))
    return 1 if kirik else 0


if __name__ == "__main__":
    raise SystemExit(main())
