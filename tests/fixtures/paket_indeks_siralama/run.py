# -*- coding: utf-8 -*-
"""paket_indeks_siralama — package-registry SIRASI platformdan bağımsız mı (KAYIT Q248).

KÖK: `build_package_index.collect_packages` İKİ yerde anahtarsız `sorted(...)` yapıyordu
(modül dizinleri + paket dizinleri) — yani `Path` nesneleri KENDİ `__lt__`'leriyle
kıyaslanıyordu. O kıyas platformun flavour'ına bağlıdır: `WindowsPath` parçaları `str.lower()`
ile katlar, `PosixPath` katlamaz (Py 3.11 `_cparts`; Py 3.12+ `_str_normcase`). Aynı paket
ağacı iki platformda FARKLI sıralanır ⇒ Windows'ta üretilip commit'lenen `package-registry.md`
Linux'ta `--check` ile "BAYAT" görünür: C-REG-01 (`check_package_registry_fresh.py`, HARD,
run_all_validators) tazelik değil ÜRETİCİNİN PLATFORMUNU ölçer.

FIX: `key=_siralama_anahtari` = `p.name`. ⛔ YENİ İLKE DEĞİL — Q214'te (2026-09-02)
`build_core_index` için seçilen `rel.as_posix()` anahtarının TEK SEGMENTLİ hâlidir (burada
sıralanan şey kardeş dizinlerdir, göreli posix dizesi = ad). Reddedilen alternatifler
(`parts`, `as_posix().lower()`) ve ölçülmüş gerekçeleri `build_core_index._siralama_anahtari`
docstring'indedir — geri çevirmeden önce oku.
⛔ DOĞAL/SAYISAL SIRA (PKG2 < PKG10) BİLEREK YOK: byte-sırası `PKG001 < PKG10 < PKG2` verir.
Bu "yanlış" değil KARARLIDIR; sayısal sıra ikinci bir ilke olurdu ve Q214 ile ayrışırdı
(V6 bunu ÇİVİLER — sessizce doğal sıraya kayarsa düşer).

⚠ PLATFORM DÜRÜSTLÜĞÜ (bu korpusun en önemli satırı): kusur tek-segmentli adlarda
YAPISAL OLARAK yalnız Windows'ta GÖRÜNÜR — POSIX'te anahtarsız `sorted(Path)` zaten
byte-sırası verir (Q214'teki `alt/` ↔ `alt-ek.md` ön-ek ekseninin buradaki karşılığı YOKTUR,
çünkü tek seviye sıralanıyor). Bu yüzden mutasyonun İKİ PLATFORMDA da ölmesini V4 sağlar:
üreticiye, `iterdir()`'ü Windows-flavour `__lt__` taşıyan nesneler veren SAHTE bir kök
verilir ⇒ "sıra nesnenin kendi kıyasına düşerse platform karar verir" mekanizması
dosya sisteminden BAĞIMSIZ ölçülür. V4b o sahte kıyası KALİBRE eder (yoksa V4 boş tören).
Beklenen düşenler: V4 (her platform) · V1/V1b/V5 (yalnız Windows).

Koşum:  python tests/fixtures/paket_indeks_siralama/run.py
MUTASYON: `--mutasyon` → üreticinin kaynağından İKİ `key=_siralama_anahtari` de SÖKÜLÜR
  (kusurun bugünkü koda enjekte edilmiş hâli; bellekte exec edilir, repoya HİÇBİR dosya
  yazılmaz). ⛔ Pinli-SHA / `git show HEAD:` tabanı KULLANILMAZ: fix merge edilince
  taban=fix olur ve mutasyon sessizce ölür (core-ci.yml'de yazılı yasak).
"""
from __future__ import annotations

import os
import shutil
import subprocess
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
URETICI = KOK / "scripts" / "build_package_index.py"
sys.path.insert(0, str(KOK / "scripts"))
import build_package_index as B  # noqa: E402

GECERLI_KIP = {"--mutasyon"}

# Fix'in İKİ satırlık imzası — mutasyon İKİSİNİ de söker (tek satır sökmek yarım ölçerdi:
# modül sırası düzelir paket sırası bozulur, ya da tersi ⇒ "iki değişmez, iki çapa").
FIX_IMZA_1 = "for module_dir in sorted(erp_root.iterdir(), key=_siralama_anahtari):"
MUT_IMZA_1 = "for module_dir in sorted(erp_root.iterdir()):"
FIX_IMZA_2 = "for pkg in sorted(module_dir.iterdir(), key=_siralama_anahtari):"
MUT_IMZA_2 = "for pkg in sorted(module_dir.iterdir()):"

BU_FLAVOUR = PureWindowsPath if os.name == "nt" else PurePosixPath

# ── KORPUS ────────────────────────────────────────────────────────────────────
# Harf-durumu ekseni BİLEREK: byte-sırası büyük harfleri öne alır, Windows katlaması almaz.
# ⚠ Paket adları JENERİKTİR (core PUBLIC repo — gerçek Z-obje adı yazılmaz).
MODULLER = ["SD", "MM", "aXX", "BYY"]
PAKETLER = ["PKG001_CLC", "PKG2_CLC", "PKG10_CLC", "aPKG_CLC", "BPKG_CLC", "NORULES_CLC"]
KURALSIZ = "NORULES_CLC"           # `.rules.md`i YOK — FP çapası (satırı KAYBOLMAMALI)

RULES = """---
status: active
---
# {ad}

- **Modül:** {mod} modülü
- **Owner:** ekip
- **Durum:** aktif
"""

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, ok, detay))


def sim(flavour, adlar: list[str]) -> list[str]:
    """`sorted(<flavour>Path(...))` sırası — 'öteki platform' simülasyonu (V3/V4b kalibre eder)."""
    return [str(x) for x in sorted(flavour(a) for a in adlar)]


def agac_kur(kok: Path, ters: bool = False) -> None:
    """Sentetik <source_root>/<MODUL>/<PKG>/.rules.md ağacı.
    `ters=True` → TERS yaratım sırası (V8: sonuç `iterdir` sırasından bağımsız olmalı)."""
    ciftler = [(m, p) for m in MODULLER for p in PAKETLER]
    for mod, pkg in (reversed(ciftler) if ters else ciftler):
        d = kok / mod / pkg
        d.mkdir(parents=True, exist_ok=True)
        if pkg != KURALSIZ:
            (d / ".rules.md").write_text(RULES.format(ad=pkg, mod=mod), encoding="utf-8")
    # FP gürültüsü: nokta ile başlayan dizin + düz dosya (ikisi de ELENMELİ)
    (kok / ".gizli_modul").mkdir(exist_ok=True)
    (kok / "SD" / ".gizli_pkg").mkdir(exist_ok=True)
    (kok / "duz_dosya.txt").write_text("x", encoding="utf-8")


def modulu_yukle(mutasyonlu: bool) -> types.ModuleType:
    """Üreticiyi bellekte modül olarak kurar. `mutasyonlu` ise İKİ `key=` de sökülür.
    Repoya dosya YAZILMAZ (komşu fixture'ları kirletmez); `__file__` gerçek yola ayarlanır
    ki `sys.path.insert(... parents[0])` + `utils.project_config` importu çözülsün."""
    if not mutasyonlu:
        return B
    ham = URETICI.read_text(encoding="utf-8")
    for imza in (FIX_IMZA_1, FIX_IMZA_2):
        if imza not in ham:
            print("  [YAMA TUTMADI] fix imzası kaynakta bulunamadı — mutasyon KURULAMADI.")
            print(f"                 aranan: {imza}")
            raise SystemExit(2)
    bozuk = ham.replace(FIX_IMZA_1, MUT_IMZA_1, 1).replace(FIX_IMZA_2, MUT_IMZA_2, 1)
    m = types.ModuleType("_mut_build_package_index")
    m.__file__ = str(URETICI)
    exec(compile(bozuk, str(URETICI), "exec"), m.__dict__)  # noqa: S102
    return m


# ── V4: SAHTE FLAVOUR KÖKÜ (platform-bağımsız mutasyon çivisi) ────────────────
class SahteYol:
    """`iterdir()` sonucunu taklit eder; `__lt__` **Windows flavour'ıyla** kıyaslar.

    Üreticinin kullandığı yüzeyin TAMAMI: `iterdir` · `is_dir` · `name` · `/`. Anahtarsız
    `sorted()` bu nesnelerin `__lt__`'sine düşer ⇒ Linux'ta koşulsa bile "platform karar
    verir" mekanizması ölçülebilir. Anahtarlı (fix) kod `key=p.name` kullandığı için
    `__lt__`'ye HİÇ dokunmaz ve byte-sırası verir.
    """

    def __init__(self, gercek: Path) -> None:
        self._g = gercek

    @property
    def name(self) -> str:
        return self._g.name

    def is_dir(self) -> bool:
        return self._g.is_dir()

    def iterdir(self):
        return [SahteYol(c) for c in self._g.iterdir()]

    def __truediv__(self, other: str) -> Path:
        return self._g / other          # `.rules.md` gerçek dosyadır (exists/read_text)

    def __lt__(self, other: "SahteYol") -> bool:
        return PureWindowsPath(self.name) < PureWindowsPath(other.name)


def paket_adlari(M: types.ModuleType, kok) -> tuple[list[str], list[str]]:
    """(modül sırası, SD paketlerinin sırası) — üreticinin GERÇEK çıktısından."""
    paketler = M.collect_packages(kok)
    moduller: list[str] = []
    for p in paketler:
        if p["module"] not in moduller:
            moduller.append(p["module"])
    return moduller, [p["name"] for p in paketler if p["module"] == "SD"]


def main() -> int:
    argv = sys.argv[1:]
    bilinmeyen = [a for a in argv if a not in GECERLI_KIP]
    if bilinmeyen:
        print(f"  [KULLANIM] bilinmeyen argüman: {bilinmeyen} — geçerli: {sorted(GECERLI_KIP)}")
        return 3
    mutasyonlu = "--mutasyon" in argv

    print("=" * 78)
    print("paket_indeks_siralama — Q248: package-registry sırası platformdan bağımsız mı"
          + ("   [MUTASYON: iki `key=` de sökülü]" if mutasyonlu else ""))
    print("=" * 78)

    M = modulu_yukle(mutasyonlu)

    tmp = Path(tempfile.mkdtemp(prefix="q248_"))
    tmp2 = Path(tempfile.mkdtemp(prefix="q248r_"))
    try:
        agac_kur(tmp)
        agac_kur(tmp2, ters=True)

        moduller, sd = paket_adlari(M, tmp)

        # ── V1/V1b — ANA ÇAPA: sıra = adların kod-noktası (byte) sırası ──────────
        kontrol("V1 modül sırası = byte-sırası (platformdan bağımsız)",
                moduller == sorted(MODULLER), f"alınan={moduller}")
        kontrol("V1b modül İÇİNDE paket sırası = byte-sırası",
                sd == sorted(PAKETLER), f"alınan={sd}")

        # ── V2 — KORPUS GEÇERLİLİĞİ: veri gerçekten flavour-ayrıştırıcı mı? ──────
        mw, mp = sim(PureWindowsPath, MODULLER), sim(PurePosixPath, MODULLER)
        pw, pp = sim(PureWindowsPath, PAKETLER), sim(PurePosixPath, PAKETLER)
        kontrol("V2 korpus flavour-AYRIŞTIRICI (Win sim ≠ POSIX sim, İKİ seviyede) — "
                "yoksa V1/V1b boş tören",
                mw != mp and pw != pp, f"modul_win={mw} modul_posix={mp} pkg_win={pw[:3]}")

        # ── V3 — KALİBRASYON: simülatör bu platformun GERÇEĞİNİ yeniden üretiyor ─
        gercek_anahtarsiz = [p.name for p in sorted(d for d in tmp.iterdir()
                                                    if d.is_dir() and not d.name.startswith("."))]
        kontrol(f"V3 kalibrasyon: anahtarsız sorted(gerçek Path) == bu platformun sim'i "
                f"({BU_FLAVOUR.__name__})",
                gercek_anahtarsiz == sim(BU_FLAVOUR, MODULLER),
                f"gercek={gercek_anahtarsiz} sim={sim(BU_FLAVOUR, MODULLER)}")

        # ── V4 — ⭐ PLATFORM-BAĞIMSIZ ÇİVİ: sıra nesnenin `__lt__`'sine DÜŞMEMELİ ──
        sahte_mod, sahte_sd = paket_adlari(M, SahteYol(tmp))
        kontrol("V4 sahte Windows-flavour kökü: üretici YİNE byte-sırası verir "
                "(mutasyon İKİ platformda da burada ölür)",
                sahte_mod == sorted(MODULLER) and sahte_sd == sorted(PAKETLER),
                f"modul={sahte_mod} pkg={sahte_sd}")
        sahte_sirali = [x.name for x in sorted(SahteYol(tmp / m) for m in MODULLER)]
        kontrol("V4b sahte kıyas KALİBRASYONU: `__lt__` gerçekten Windows sırası üretiyor "
                "(yoksa V4 boş tören)",
                sahte_sirali == sim(PureWindowsPath, MODULLER),
                f"sahte={sahte_sirali} win_sim={sim(PureWindowsPath, MODULLER)}")

        # ── V5 — 3. BAĞLAM: fix `collect_packages`ta, ölçüm ÜRETİLEN ARTEFAKTTA ──
        tablo = M.render_table(M.collect_packages(tmp))
        satir_sd = [s.split("`")[3] for s in tablo.splitlines() if s.startswith("| `SD`")]
        satir_mod: list[str] = []
        for s in tablo.splitlines():
            if not s.startswith("| `"):
                continue
            mod = s.split("`")[1]
            if mod not in satir_mod:
                satir_mod.append(mod)
        kontrol("V5 ARTEFAKT (render_table) satır sırası = byte-sırası (modül + paket)",
                satir_mod == sorted(MODULLER) and satir_sd == sorted(PAKETLER),
                f"modul={satir_mod} sd={satir_sd}")

        # ── V6 — ANAHTAR ÇİVİSİ: byte-sırası, DOĞAL/SAYISAL sıra DEĞİL ───────────
        kontrol("V6 `PKG001 < PKG10 < PKG2` (byte) — doğal/sayısal sıraya sessiz kayış YOK",
                sd.index("PKG001_CLC") < sd.index("PKG10_CLC") < sd.index("PKG2_CLC"),
                f"alınan={sd}")

        # ── V7 — FP: kapsam bozulmadı (eleme + kuralsız paket + çiftlenme) ───────
        hepsi = M.collect_packages(tmp)
        adlar = [(p["module"], p["name"]) for p in hepsi]
        kuralsiz = [p for p in hepsi if p["name"] == KURALSIZ]
        kontrol("V7 FP: nokta-dizin ve düz dosya eleniyor · `.rules.md` yok satırı DURUYOR · "
                "çift yok · küme tam",
                len(adlar) == len(set(adlar)) == len(MODULLER) * len(PAKETLER)
                and all("yok" in k["status"] for k in kuralsiz)
                and len(kuralsiz) == len(MODULLER)
                and not any(a[0].startswith(".") or a[1].startswith(".") for a in adlar),
                f"n={len(adlar)} beklenen={len(MODULLER) * len(PAKETLER)} "
                f"kuralsiz={len(kuralsiz)}")

        # ── V8 — DETERMİNİZM: tekrar + TERS yaratım sırasıyla kurulmuş ikiz ağaç ─
        mod_tekrar, sd_tekrar = paket_adlari(M, tmp)
        mod_ters, sd_ters = paket_adlari(M, tmp2)
        kontrol("V8 determinizm: tekrar çağrı ve TERS yaratım sıralı ikiz ağaç aynı sırayı verir",
                (mod_tekrar, sd_tekrar) == (moduller, sd) == (mod_ters, sd_ters),
                f"tekrar_es={(mod_tekrar, sd_tekrar) == (moduller, sd)} "
                f"ters_es={(mod_ters, sd_ters) == (moduller, sd)} ters_mod={mod_ters}")

        # ── V9 — 3. BAĞLAM (salt-string): Türkçe İ/ı + sayı/işaret karışımı ──────
        tr = ["PIK_CLC", "Pık_CLC", "PİK_CLC", "pik_CLC", "P_ALT_CLC", "P2_CLC", "P10_CLC"]
        tw, tp = sim(PureWindowsPath, tr), sim(PurePosixPath, tr)
        kontrol("V9 3.bağlam TR (İ/ı) + sayı/işaret: iki flavour AYRIŞIYOR; byte-sırası TEK ve "
                "deterministik cevabı verir",
                tw != tp, f"win={tw} posix={tp} byte={sorted(tr)}")

        # ── V10 — 3. BAĞLAM (GERÇEK KABLOLAMA): CLI `--dry-run` artefaktı ────────
        if mutasyonlu:
            # Mutasyon modül-içi enjeksiyondur; subprocess onu GÖRMEZ → koşmak sahte-PASS
            # üretirdi (b0_secim V12 ile aynı sözleşme).
            kontrol("V10 KABLOLAMA — mutasyon modunda ATLANDI (subprocess mutasyonu görmez)",
                    True, "bilinçli atlama")
        else:
            reg = tmp / "registry.md"
            reg.write_text("---\nlast-updated: 2000-01-01\n---\n\n"
                           "## Aktif Paketler\n\nESKI\n\n## Son\n", encoding="utf-8")
            p = subprocess.run([sys.executable, str(URETICI), "--source-root", str(tmp),
                                "--registry", str(reg), "--dry-run"],
                               cwd=str(KOK), capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            cli_mod: list[str] = []
            for s in p.stdout.splitlines():
                if s.startswith("| `"):
                    m0 = s.split("`")[1]
                    if m0 not in cli_mod:
                        cli_mod.append(m0)
            kontrol("V10 KABLOLAMA: CLI `--dry-run` artefaktı da byte-sırası (exit 0)",
                    p.returncode == 0 and cli_mod == sorted(MODULLER),
                    f"exit={p.returncode} modul={cli_mod}")
    finally:
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
