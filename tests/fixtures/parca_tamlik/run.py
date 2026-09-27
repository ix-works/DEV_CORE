#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""parca_tamlik — `run_fixture_tests.py --parca i/N` + `--parca-birlestir` korpusu (Q354 Faz 1).

NEDEN VAR: CI'da suit N matris isine bolunur. Her parca yalniz KENDI listesini kosar ve
yesil doner; bir birim HICBIR parcada kosmasa bile hicbir parca kirmizi olmaz. Bu sinifin
tek panzehiri toplayicidaki TAMLIK denetimidir: parcalarin KOSTUGU birimlerin birlesimi,
kayittan bagimsiz turetilen EVRENLE birebir olmali (eksik yok, cift yok, fazla yok).

⛔ Denetim `parcala()`ya GUVENMEZ: bolme kusurluysa (birim dusuren / cogaltan) toplayici
ayni kusurlu plani yeniden hesaplar ve plan kiyasi "tutarli" der — onu yalniz EVREN kiyasi
yakalar. N2/N3 bu yuzden bolmeyi BOZARAK kurulur (monkeypatch), rapor yazimini degil.

SENARYOLAR
  P1  evren KAYDI yansitir (V=VALIDATORS, O=OZEL_TESTLER, R=REGRESYON, G, H, K=kipli kosucular), mukerrer yok
  P2  bolme: n=1,2,3,4,7 icin birlesim=evren, ayrik, deterministik, girdi SIRASINDAN bagimsiz
  P3  n=1 tek parca = evren (TAM esdegeri)
  P4  temiz raporlar -> birlestir PASS (kontrol grubu)
  N1  parca raporu YOK -> FAIL
  N2  BOZUK BOLME birim DUSURUR -> FAIL (yalniz evren kiyasi yakalar)       [--mutasyon-eksik]
  N3  BOZUK BOLME birim COGALTIR -> FAIL (yalniz cift kiyasi yakalar)       [--mutasyon-cift]
  N4  kosumda dusen birim (planlanan var, kosulan yok) -> FAIL
  N5  birim YANLIS parcada kostu (birlesim tam, cift yok) -> FAIL           [--mutasyon-parca-ici]
  N6  evren disi birim -> FAIL · N7 evren ozeti farkli -> FAIL · N8 parca rc!=0 -> FAIL
  N9  N uyusmazligi -> FAIL · N10 bos dizin -> FAIL · N11 ayni parca iki rapor -> FAIL
  B1  3.BAGLAM (gorev-disi): KAYIT BUYUR (yeni OZEL satiri) -> evrende + bir parcada;
      BAYAT plandan gelen raporlar yeni evrene karsi FAIL (yeni fixture sessizce dusmez)
  A1-A6  ATLA ozet ayristiricisi (`N/M PASS · K ATLA`, `[ATLA]` isareti, FP capalari)
  C1-C2  arguman ayrimi: bayraksiz cagri BUGUNKU yol (None, False); gecersiz bicimler exit 2
  K1-K2  KABLOLAMA (gercek CLI alt sureci; mutasyon kipinde ATLANIR — alt surec mutasyonu gormez)

Kosucu: tests/run_fixture_tests.py (OZEL_TESTLER). Batarya: python tests/run_battery.py parca_tamlik
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import random
import shutil
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
SUIT = KOK / "tests" / "run_fixture_tests.py"

KIPLER = ("--mutasyon-eksik", "--mutasyon-cift", "--mutasyon-parca-ici")
# (kip, capa, yerine) — capa TAM SATIR ve dosyada TAM 1 kez olmali (yoksa KURULAMADI).
MUTASYONLAR = {
    "--mutasyon-eksik": ("    eksik = sorted(evren_k - birlesim)\n", "    eksik = []\n"),
    "--mutasyon-cift": ("    cift = sorted(b for b, c in sayac.items() if c > 1)\n",
                        "    cift = []\n"),
    "--mutasyon-parca-ici": ("        eksik_i = sorted(planlanan - set(kos))\n"
                             "        fazla_i = sorted(set(kos) - planlanan)\n",
                             "        eksik_i = fazla_i = []\n"),
}

KIP = None
for _a in sys.argv[1:]:
    if _a in KIPLER:
        KIP = _a
    else:
        print(f"[KULLANIM] bilinmeyen arguman {_a!r}; kipler: {', '.join(KIPLER)}")
        sys.exit(2)

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(ok), detay))


def yukle():
    """Suiti MODUL olarak yukle (main calismaz). Mutasyonda kaynak METNI degistirilip
    gercek `__file__` ile exec edilir (HERE/FIXTURES gercek agaci gostersin)."""
    kaynak = SUIT.read_text(encoding="utf-8")
    if KIP:
        capa, yerine = MUTASYONLAR[KIP]
        adet = kaynak.count(capa)
        if adet != 1:
            print(f"[KURULAMADI] {KIP}: capa {adet} kez bulundu (1 bekleniyor) — mutasyon BAYATLADI")
            sys.exit(2)
        kaynak = kaynak.replace(capa, yerine)
    mod = types.ModuleType("rft_parca_tamlik_altinda")
    mod.__file__ = str(SUIT)
    exec(compile(kaynak, str(SUIT), "exec"), mod.__dict__)
    return mod


R = yukle()
KUM = Path(tempfile.mkdtemp(prefix="parca_tamlik_"))


def raporlari_yaz(dizin: Path, plan: list[set[str]], evren: list[str], n: int,
                  duzelt=None) -> None:
    """Her parca icin `--parca-rapor` bicimiyle rapor; `duzelt(i, rapor)` bozar."""
    if dizin.exists():
        shutil.rmtree(dizin)
    dizin.mkdir(parents=True)
    for i in range(1, n + 1):
        r = {"surum": 1, "parca": i, "toplam_parca": n,
             "evren_ozeti": R.evren_ozeti(evren), "evren_boyu": len(evren),
             "planlanan": sorted(plan[i - 1]),
             "kosulan": {b: 0.1 for b in sorted(plan[i - 1])},
             "rc": 0, "fixture_ici_atla": 0}
        if duzelt:
            r = duzelt(i, r)
            if r is None:
                continue
        (dizin / f"parca-{i}.json").write_text(json.dumps(r, ensure_ascii=False),
                                               encoding="utf-8")


def birlestir(dizin: Path, n: int) -> tuple[bool, str]:
    ok, bilgi, hatalar, _ = R.parca_birlestir(n, dizin)
    return ok, " | ".join(hatalar) or " | ".join(bilgi)[:200]


try:
    # ── P1 evren ────────────────────────────────────────────────────────────────
    evren = R.parca_evreni()
    siniflar: dict[str, set[str]] = {}
    for b in evren:
        siniflar.setdefault(b.split(":", 1)[0], set()).add(b)
    kipli = R._kipli_kosucular()
    # Hiz: evren kesfi ~2 sn (131 run.py AST); P1 gercek fonksiyonu olctu, gerisi ayni
    # listeyi kullanir (toplayici her cagrida evreni YENIDEN kurar).
    R._kipli_kosucular = lambda: list(kipli)
    beklenen = {
        "V": {f"V:{v}" for v in R.VALIDATORS},
        "O": {f"O:{a}" for a, _ in R.OZEL_TESTLER},
        "R": {f"R:{k}" for k, _, _ in R.REGRESYON},
        "G": {"G"}, "H": {"H"},
        "K": {f"K:{k}" for k in kipli},
    }
    kontrol("P1 evren KAYDI yansitir (V/O/R/G/H/K kumeleri birebir)",
            all(siniflar.get(k, set()) == v for k, v in beklenen.items())
            and set(siniflar) == set(beklenen),
            f"siniflar={ {k: len(v) for k, v in siniflar.items()} } "
            f"beklenen={ {k: len(v) for k, v in beklenen.items()} }")
    kontrol("P1b evrende mukerrer yok + K kumesi gercek run.py dizinleri",
            len(evren) == len(set(evren))
            and all((KOK / "tests" / "fixtures" / k / "run.py").is_file() for k in kipli)
            and len(kipli) > 10,
            f"evren={len(evren)} kume={len(set(evren))} kipli={len(kipli)}")

    # ── P2/P3 bolme ─────────────────────────────────────────────────────────────
    sureler, _ = R.agirliklari_yukle()
    sorunlar = []
    for n in (1, 2, 3, 4, 7):
        p1, y1 = R.parcala(evren, n, sureler)
        p2, _ = R.parcala(list(reversed(evren)), n, sureler)
        karisik = list(evren)
        random.Random(354).shuffle(karisik)
        p3, _ = R.parcala(karisik, n, sureler)
        birlesim = set().union(*p1)
        toplam = sum(len(p) for p in p1)
        if birlesim != set(evren) or toplam != len(evren):
            sorunlar.append(f"n={n}: birlesim/ayriklik bozuk ({toplam} vs {len(evren)})")
        if not (p1 == p2 == p3):
            sorunlar.append(f"n={n}: girdi sirasina BAGIMLI")
        if len(p1) != n:
            sorunlar.append(f"n={n}: parca sayisi {len(p1)}")
    kontrol("P2 bolme: birlesim=evren, ayrik, deterministik, siradan bagimsiz (n=1,2,3,4,7)",
            not sorunlar, "; ".join(sorunlar))
    p_tek, _ = R.parcala(evren, 1, sureler)
    kontrol("P3 n=1 tek parca = evren (TAM esdegeri)", p_tek[0] == set(evren),
            f"{len(p_tek[0])} vs {len(evren)}")

    N = 4
    plan, _ = R.parcala(evren, N, sureler)
    d = KUM / "rapor"

    # ── P4 kontrol grubu ────────────────────────────────────────────────────────
    raporlari_yaz(d, plan, evren, N)
    ok, det = birlestir(d, N)
    kontrol("P4 temiz raporlar -> birlestir PASS (kontrol grubu)", ok, det)

    # ── N1 rapor yok ────────────────────────────────────────────────────────────
    raporlari_yaz(d, plan, evren, N, lambda i, r: None if i == 3 else r)
    ok, det = birlestir(d, N)
    kontrol("N1 parca 3 raporu YOK -> FAIL", not ok and "RAPORU YOK" in det, det)

    # ── N2/N3 BOZUK BOLME (plan kiyasi tutarli der; yalniz evren/cift kiyasi yakalar) ──
    gercek_parcala = R.parcala
    kurban = sorted(plan[1])[0]

    def dusuren(ev, n, sr):
        ps, yk = gercek_parcala(ev, n, sr)
        return [set(p) - ({kurban} if k == 1 else set()) for k, p in enumerate(ps)], yk

    def cogaltan(ev, n, sr):
        ps, yk = gercek_parcala(ev, n, sr)
        ek = sorted(ps[0])[0]
        return [set(p) | ({ek} if k == 1 else set()) for k, p in enumerate(ps)], yk

    try:
        R.parcala = dusuren
        bozuk, _ = R.parcala(evren, N, sureler)
        raporlari_yaz(d, bozuk, evren, N)
        ok, det = birlestir(d, N)
        kontrol("N2 BOZUK BOLME birim dusurur -> FAIL (evren kiyasi: HICBIR parcada kosmayan)",
                not ok and "HİÇBİR parçada koşmayan" in det and kurban in det, det)
        R.parcala = cogaltan
        bozuk, _ = R.parcala(evren, N, sureler)
        raporlari_yaz(d, bozuk, evren, N)
        ok, det = birlestir(d, N)
        kontrol("N3 BOZUK BOLME birim cogaltir -> FAIL (cift kiyasi: BIRDEN COK parcada)",
                not ok and "BİRDEN ÇOK parçada" in det, det)
    finally:
        R.parcala = gercek_parcala

    # ── N4 kosumda dusen birim ─────────────────────────────────────────────────
    hedef = sorted(plan[1])[0]

    def dusur(i, r):
        if i == 2:
            r["kosulan"].pop(hedef)
        return r
    raporlari_yaz(d, plan, evren, N, dusur)
    ok, det = birlestir(d, N)
    kontrol("N4 planlanip KOSMAYAN birim -> FAIL", not ok and hedef in det, det)

    # ── N5 yanlis parcada kosan (birlesim TAM, cift YOK: yalniz parca-ici kiyas yakalar) ──
    gocmen = sorted(plan[0])[0]

    def tasi(i, r):
        if i == 1:
            r["kosulan"].pop(gocmen)
        if i == 2:
            r["kosulan"][gocmen] = 0.1
        return r
    raporlari_yaz(d, plan, evren, N, tasi)
    ok, det = birlestir(d, N)
    kontrol("N5 birim YANLIS parcada kostu -> FAIL (parca-ici planlanan != kosulan)",
            not ok and "KOŞMAYAN" in det and "planda olmayıp" in det, det)

    # ── N6..N11 ────────────────────────────────────────────────────────────────
    def hayalet(i, r):
        if i == 4:
            r["kosulan"]["O:hayalet_q354"] = 0.1
            r["planlanan"].append("O:hayalet_q354")
        return r
    raporlari_yaz(d, plan, evren, N, hayalet)
    ok, det = birlestir(d, N)
    kontrol("N6 evren DISI birim -> FAIL", not ok and "evrende OLMAYAN" in det, det)

    raporlari_yaz(d, plan, evren, N,
                  lambda i, r: dict(r, evren_ozeti="0000000000000000") if i == 2 else r)
    ok, det = birlestir(d, N)
    kontrol("N7 evren ozeti farkli -> FAIL", not ok and "evren özeti" in det, det)

    raporlari_yaz(d, plan, evren, N, lambda i, r: dict(r, rc=1) if i == 1 else r)
    ok, det = birlestir(d, N)
    kontrol("N8 parca rc=1 -> FAIL", not ok and "rc=1" in det, det)

    raporlari_yaz(d, plan, evren, N)
    ok, det = birlestir(d, N - 1)
    kontrol("N9 N uyusmazligi (4 parca raporu, toplayici 3 bekliyor) -> FAIL", not ok, det)

    bos = KUM / "bos"
    bos.mkdir()
    ok, det = birlestir(bos, N)
    kontrol("N10 bos dizin -> FAIL", not ok and "RAPORU YOK" in det, det)

    raporlari_yaz(d, plan, evren, N)
    (d / "alt").mkdir()
    shutil.copy(d / "parca-1.json", d / "alt" / "parca-1.json")
    ok, det = birlestir(d, N)
    kontrol("N11 ayni parca IKI rapor -> FAIL", not ok and "İKİ raporla" in det, det)

    # ── B1 3.BAGLAM: kayit buyur ───────────────────────────────────────────────
    eski_ozel = R.OZEL_TESTLER
    try:
        eski_evren, eski_plan = evren, plan
        R.OZEL_TESTLER = list(eski_ozel) + [("yeni_fx_q354", "sentetik: sonradan eklenen satir")]
        yeni_evren = R.parca_evreni()
        yeni_plan, _ = R.parcala(yeni_evren, N, sureler)
        yerlesti = sum(1 for p in yeni_plan if "O:yeni_fx_q354" in p)
        kontrol("B1 kayda eklenen fixture OTOMATIK evrende ve TAM BIR parcada",
                "O:yeni_fx_q354" in yeni_evren and yerlesti == 1, f"parca sayisi={yerlesti}")
        raporlari_yaz(d, eski_plan, eski_evren, N)
        ok, det = birlestir(d, N)
        kontrol("B1b BAYAT plan raporlari (yeni satirdan once) -> FAIL (yeni fixture sessizce dusmez)",
                not ok and "O:yeni_fx_q354" in det, det)
        raporlari_yaz(d, yeni_plan, yeni_evren, N)
        ok, det = birlestir(d, N)
        kontrol("B1c taze plan raporlari -> PASS (FP capasi)", ok, det)
    finally:
        R.OZEL_TESTLER = eski_ozel

    # ── A: ATLA ozet ayristiricisi ─────────────────────────────────────────────
    vektorler = [
        ("A1 `ad: N/M PASS · K ATLA`", "\npbe_ui: 58/59 PASS · 1 ATLA\n",
         ("58/59 PASS · 1 ATLA", 1, "ozet")),
        ("A2 bugunku `N/M OK` (ATLA yok) DEGISMEDI", "  [PASS] x\n\n26/26 OK\n",
         ("26/26 OK", 0, "")),
        ("A3 `[ATLA]` satir isareti sayilir", "  [ATLA] H1-H5 x\n  [ATLANDI] y\n\n30/30 OK\n",
         ("30/30 OK", 2, "isaret")),
        ("A4 FP: suitin kendi `[ATLANDI — secim modu]` satiri SAYILMAZ",
         "  [ATLANDI — seçim modu] AV-02\n5/5 OK\n", ("5/5 OK", 0, "")),
        ("A5 FP: `TOPLAM: N PASS / M FAIL` ozet DEGIL", "TOPLAM: 5 PASS / 0 FAIL\n", ("", 0, "")),
        ("A6 `N/M OK · K ATLA` bugunku desene de uyar, K tasinir", "\n12/12 OK · 3 ATLA\n",
         ("12/12 OK · 3 ATLA", 3, "ozet")),
    ]
    for ad, girdi, bek in vektorler:
        alinan = R.ozet_ve_atla(girdi)
        kontrol(ad, alinan == bek, f"alinan={alinan} beklenen={bek}")

    # ── C: arguman ayrimi ──────────────────────────────────────────────────────
    kalan, sec = R._parca_argumanlarini_ayir([])
    kontrol("C1 bayraksiz cagri -> parca YOK ve `_argumanlari_coz([])` == (None, False) (bugunku yol)",
            kalan == [] and sec == {"parca": None, "rapor": None, "birlestir": None}
            and R._argumanlari_coz([]) == (None, False), f"kalan={kalan} sec={sec}")
    kotu = []
    _sessiz = io.StringIO()
    for argv in (["--parca", "5/4"], ["--parca", "0/4"], ["--parca", "abc"], ["--parca"],
                 ["--parca", "1/4", "--degisen", "x.py"], ["--parca-rapor", "x.json"],
                 ["--parca-birlestir", "4"], ["--parca-birlestir", "4", "d", "--listele"]):
        try:
            with contextlib.redirect_stdout(_sessiz):
                R._parca_argumanlarini_ayir(argv)
            kotu.append(f"{argv}: KABUL edildi")
        except SystemExit as exc:
            if exc.code != 2:
                kotu.append(f"{argv}: exit {exc.code}")
    kontrol("C2 gecersiz parca bicimleri exit 2 (8 vektor)", not kotu, "; ".join(kotu))

    # ── K: KABLOLAMA (gercek CLI) ──────────────────────────────────────────────
    if KIP:
        kontrol("K1/K2 KABLOLAMA — mutasyon kipinde ATLANDI (alt surec mutasyonu gormez)",
                True, "bilincli atlama")
    else:
        env = os.environ.copy()
        for k in list(env):
            if k == "CLAUDE_PROJECT_DIR" or k.startswith("IX_"):
                env.pop(k, None)

        def cli(*a: str) -> tuple[int, str]:
            p = subprocess.run([sys.executable, str(SUIT), *a], cwd=str(KOK), env=env,
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=300)
            return p.returncode, (p.stdout or "") + (p.stderr or "")

        rc, out = cli("--parca", "2/4", "--listele")
        listelenen = {s.strip()[2:] for s in out.splitlines() if s.startswith("    · ")}
        kontrol("K1 CLI `--parca 2/4 --listele` birim listesi = modul plani",
                rc == 0 and listelenen == plan[1], f"rc={rc} fark={sorted(listelenen ^ plan[1])[:5]}")

        # Her sinif icin bir ucuz birim: N = evren boyu ⇒ her parca TEK birim (LPT).
        tekil, _ = R.parcala(evren, len(evren), sureler)
        secilen = ["V:check_bdef_backtick", "R:AV-02", "H", "O:sir_gate"]
        rdir = KUM / "cli"
        sorun = []
        for b in secilen:
            idx = next(k for k, p in enumerate(tekil) if b in p) + 1
            rp = rdir / f"parca-{idx}.json"
            rc, out = cli("--parca", f"{idx}/{len(evren)}", "--parca-rapor", str(rp))
            try:
                r = json.loads(rp.read_text(encoding="utf-8"))
            except Exception as exc:       # noqa: BLE001
                sorun.append(f"{b}: rapor yok ({type(exc).__name__}) rc={rc}")
                continue
            if set(r["kosulan"]) != {b} or r["rc"] != 0 or rc != 0 \
                    or r["evren_ozeti"] != R.evren_ozeti(evren):
                sorun.append(f"{b}: kosulan={sorted(r['kosulan'])} rc={rc}/{r['rc']}")
        kontrol("K2 gercek CLI parcasi YALNIZ planini kosar + raporlar (V/R/H/O)", not sorun,
                "; ".join(sorun))
        ok, det = birlestir(rdir, len(evren))
        kontrol("K2b yalniz 4 parca raporuyla birlestir -> FAIL (eksik parcalar gorunur)",
                not ok and "RAPORU YOK" in det, det[:200])
finally:
    shutil.rmtree(KUM, ignore_errors=True)

gecen = sum(1 for _, ok, _ in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok:
        print(f"         -> {detay[:600]}")
print(f"\n{gecen}/{len(SONUC)} OK" + (f"  [MUTASYON {KIP}]" if KIP else ""))
sys.exit(0 if gecen == len(SONUC) else 1)
