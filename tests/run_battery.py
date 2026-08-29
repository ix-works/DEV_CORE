#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_battery.py — TEK komutla fixture BATARYASI (taban + tüm mutasyon kipleri).

**Neden (ölçüldü, 30 gün):** infra-expert koşularında test bataryası koşu başına medyan
8 kez tekrarlanıyor ve her batarya 4-6 AYRI kabuk turu harcıyordu (taban koşumu · her
mutasyon kipi · kardeş fixture · `core_precommit --all`). Tur başına model süresi
med 3,3 dk. Bu araç bataryayı TEK tura indirir; ham çıktılar `.tmp/battery/` altına
yazılır, ekrana yalnız özet tablo çıkar (bağlam ekonomisi).

⛔ **Bu bir KAPI DEĞİLDİR.** Hiçbir kuralı zorlamaz, hiçbir gate'in yerine geçmez.
Tam süit (`tests/run_fixture_tests.py`) ve CI aynen yerinde durur; bu araç yalnız
ARA adımların koşum maliyetini düşürür. Teslimden önce tam süit YİNE koşulur.

──────────────────────────────────────────────────────────────────────────────
KİP KEŞFİ — ÜÇ KATMANLI, `--help`e GÜVENMEZ (korpusa karşı ölçüldü: 90 koşucu,
33'ünde mutasyon kipi var (102 kip); üçü birlikte 33/33 koşucuyu çözüyor, 0 hayalet):

  ① BEYAN   — kaynakta, elemanlarının HEPSİ `--mutasyon…` olan bir küme/liste/demet/
              sözlük-anahtarı literali (`GECERLI_KIP`, `_GECERLI_KIP`, yerel `gecerli`,
              `gecerli_kipler`, `{"--mutasyon": …}` eşlemesi …). Ad-bağımsızdır:
              yazım-bağımlı arama sınıfı taramaz. Mevcut korpusta 15 koşucu buradan
              çözülür. ⛔ Kıyas operandı (`set(k) == {"--mutasyon-x"}`) BEYAN SAYILMAZ:
              bir kipi TARİF eden literal onu BEYAN etmiş olmaz (yapısal filtre; mevcut
              33 koşucuda etkisi ÖLÇÜLDÜ = 0 fark, yani daraltma değil FP düzeltmesi).
  ② AST     — beyan yoksa: docstring OLMAYAN string sabitleri (yorumlar AST'te YOKTUR
              ⇒ `--mutasyon-ZIRVA` gibi *bilinmeyen-kip örneği* yorumları kendiliğinden
              elenir; ölçüldü: 8 koşucuda ZIRVA yorumu var, hiçbiri keşfe sızmadı).
              Mevcut korpusta 15 koşucu bu katmandan çözülür.
  ③ DOKÜMAN — ikisi de boşsa: modül docstring'i. ⚠ Bu katman ŞART: üç koşucu
              (`atc_p1_sonuc` · `fs_docstd` · `post_tool_failure_bash`) kipleri
              `a.startswith("--mutasyon-")` + son-ek ile ÇÖZER; geçerli kip listesi
              YALNIZ docstring'de yaşar. Yalnız ①+② ile bu üçü "mutasyon yok" derdi —
              16 kip sessizce kapsam dışı kalırdı (exit 0 iki anlamlı olurdu).

Keşif SIRALIDIR (birleşim DEĞİL): ① varsa ② ve ③ okunmaz. Gerekçe ölçüldü — bazı
koşucularda docstring'de anılan bir kip kodda geçerli DEĞİLDİR; birleşim alsaydık
geçersiz kip koşulur ve koşucu onu reddederdi (sahte-KIRMIZI). Keşif kaynağı her
satırda yazılır: kaynağı bilmeden sonucu okuma.

──────────────────────────────────────────────────────────────────────────────
SATIR SONUCU — "exit 0" TEK BAŞINA ANLAM TAŞIMAZ (bu araç dört ayrı hâli ayırır):

  TABAN:      YESIL(exit 0) · KIRMIZI(exit≠0) · COKTU(Traceback) · YOK(koşucu yok)
  MUTASYON:   DUSTU(exit≠0 = korpus mutasyonu yakaladı)  → beklenen
              AYIRDI(exit 0 ama skor tabandan FARKLI = kendi mutasyon öz-testini
                     koşan koşucu; ölçüldü, korpusta yaygın)                → beklenen
              KACTI(exit 0 ve skor tabanla AYNI = korpus o değişmezi ölçmüyor) → FAIL
              OLCULEMEDI(exit 0 ama skor okunamadı = kıyas yapılamadı)         → FAIL
              KURULAMADI(exit 2 = koşucu SAYI RAPORLAMADAN durdu)            → FAIL
              KIP-RED([DURDU]/[KULLANIM] = koşucu kipi tanımadı)             → FAIL
              COKTU(Traceback)                                              → FAIL
  ⛔ "kurulamadı", "kaçtı" DEĞİLDİR ve "çökme", "FAIL" değildir — üçü ayrı satır
     etiketi taşır, çünkü üçünün onarımı ayrıdır.

NİHAİ EXIT: 1 — taban YEŞİL değilse · bir kip KACTI/KURULAMADI/KIP-RED/COKTU ise ·
            koşucu yoksa · `--precommit` verildi ve gate exit≠0 ise. Aksi hâlde 0.

ÇOCUK ORTAMI: `run_fixture_tests.py::run_ozel` ile BİREBİR aynı (IX_* ve
CLAUDE_PROJECT_DIR temizlenir, cwd = repo kökü). ⛔ `PYTHONUTF8` ENJEKTE EDİLMEZ:
enjekte edilseydi burada yeşil olan bir koşucu CI'da (env'siz) kırmızı olabilirdi —
"lokal yeşil ≠ CI yeşil" sınıfı. Aracın KENDİ çıktısı env'siz de çalışır (reconfigure).

Kullanım:
    python tests/run_battery.py <fixture-adi>
    python tests/run_battery.py <fixture-adi> --kardes <ad> [<ad> …] --precommit
    python tests/run_battery.py <fixture-adi> --liste          # yalnız keşif (koşum yok)
    python tests/run_battery.py <fixture-adi> --kip --mutasyon-x   # elle kip seçimi
    python tests/run_battery.py <fixture-adi> --repo <yol>      # kök enjeksiyonu (test)
Korpus: tests/fixtures/run_battery/run.py
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

VARSAYILAN_REPO = Path(__file__).resolve().parents[1]

KIP_RE = re.compile(r"--mutasyon(-[A-Za-z0-9_]+)*\Z")
TOKEN_RE = re.compile(r"--mutasyon[-A-Za-z0-9_]*")
SKOR_RE = re.compile(r"(\d+)\s*/\s*(\d+)")
PASSFAIL_RE = re.compile(r"(\d+)\s*PASS\s*/\s*(\d+)\s*FAIL")
COKME_IZI = "Traceback (most recent call last)"
DURUS_MARKORLERI = ("[DURDU]", "[KULLANIM]")
OZET_SATIR_BUTCESI = 22
NOTLAR: list[str] = []


# ── KEŞİF ────────────────────────────────────────────────────────────────────
def _literal_kipler(dugum: ast.AST) -> list[str] | None:
    """Elemanlarının HEPSİ mutasyon kipi olan bir koleksiyon literali mi?"""
    if isinstance(dugum, (ast.Set, ast.List, ast.Tuple)):
        ogeler = list(dugum.elts)
    elif isinstance(dugum, ast.Dict):
        ogeler = [k for k in dugum.keys if k is not None]
    else:
        return None
    if not ogeler:
        return None
    bulunan: list[str] = []
    for o in ogeler:
        if isinstance(o, ast.Constant) and isinstance(o.value, str) and KIP_RE.fullmatch(o.value):
            bulunan.append(o.value)
        else:
            return None          # tek yabancı öğe → bu bir kip beyanı değildir
    return bulunan


def _docstring_dugumleri(agac: ast.AST) -> set[int]:
    ids: set[int] = set()
    for n in ast.walk(agac):
        govde = getattr(n, "body", None)
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                and govde and isinstance(govde[0], ast.Expr) \
                and isinstance(govde[0].value, ast.Constant) \
                and isinstance(govde[0].value.value, str):
            ids.add(id(govde[0].value))
    return ids


def kipleri_kesfet(kaynak: str) -> tuple[list[str], str]:
    """(kipler, keşif-kaynağı) — BEYAN > AST > DOKUMAN sırası; birleşim DEĞİL."""
    try:
        agac = ast.parse(kaynak)
    except SyntaxError as e:
        return [], f"AYRISTIRILAMADI ({e.__class__.__name__})"

    # ⛔ KIYAS OPERANDI BEYAN DEĞİLDİR (2026-08-29, bu aracın KENDİ korpusunda ölçüldü):
    # `set(k) == {"--mutasyon-dalsiz", …}` gibi bir literal BAŞKA bir koşucunun kiplerini
    # TARİF eder, bu dosyanın kiplerini BEYAN etmez. Ayrım YAPISALDIR (ada bakmaz):
    # beyan bir isme ATANIR, kıyas operandı atanmaz. Bu filtre olmadan araç kendi
    # korpusunda 10 kip "keşfetti", 4'ü hayaletti ve KIP-RED sahte-FAIL'i üretti.
    kiyas_operandlari: set[int] = set()
    for n in ast.walk(agac):
        if isinstance(n, ast.Compare):
            for o in [n.left, *n.comparators]:
                kiyas_operandlari.add(id(o))

    beyan: set[str] = set()
    for n in ast.walk(agac):
        if id(n) in kiyas_operandlari:
            continue
        d = _literal_kipler(n)
        if d:
            beyan |= set(d)
    if beyan:
        return sorted(beyan), "BEYAN"

    doc_ids = _docstring_dugumleri(agac)
    kod = {n.value for n in ast.walk(agac)
           if isinstance(n, ast.Constant) and isinstance(n.value, str)
           and id(n) not in doc_ids and KIP_RE.fullmatch(n.value)}
    if kod:
        return sorted(kod), "AST"

    doc = ast.get_docstring(agac) or ""
    belge = {t for t in TOKEN_RE.findall(doc) if KIP_RE.fullmatch(t)}
    if belge:
        return sorted(belge), "DOKUMAN"
    return [], "YOK"


# ── KOŞUM ────────────────────────────────────────────────────────────────────
def _cocuk_ortami() -> dict:
    env = os.environ.copy()
    for k in list(env):
        if k == "CLAUDE_PROJECT_DIR" or k.startswith("IX_"):
            env.pop(k, None)
    return env


def _skor(cikti: str) -> str | None:
    """Son skor satırı — İKİ biçim (korpusta ölçüldü, tek desen 90 koşucuyu taramaz).

    ⚠ Skor KARAR vermez, KIYAS ÇAPASIDIR: koşucular 12 farklı biçimde basıyor
    (`N/M OK` · `SONUC: N/M` · `<ad>: N/M` · `TOPLAM: N PASS / M FAIL`). Karar
    çıkış kodundan gelir; skor yalnız "mutasyon bir şeyi DEĞİŞTİRDİ mi" kıyası içindir.
    """
    m = PASSFAIL_RE.findall(cikti)
    if m:
        gecen, kalan = int(m[-1][0]), int(m[-1][1])
        return f"{gecen}/{gecen + kalan}"
    m = SKOR_RE.findall(cikti)
    return f"{m[-1][0]}/{m[-1][1]}" if m else None


def _durus_markoru(cikti: str) -> bool:
    for satir in cikti.splitlines():
        s = satir.strip()
        if any(s.startswith(m) for m in DURUS_MARKORLERI):
            return True
    return False


def kos(komut: list[str], repo: Path, zaman_asimi: int) -> tuple[int, str, float]:
    t0 = time.time()
    try:
        p = subprocess.run(komut, cwd=str(repo), env=_cocuk_ortami(),
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=zaman_asimi)
        cikti = (p.stdout or "") + (p.stderr or "")
        kod = p.returncode
    except subprocess.TimeoutExpired:
        cikti, kod = f"[ZAMAN-ASIMI] {zaman_asimi}s icinde bitmedi", 124
    return kod, cikti, round(time.time() - t0, 1)


def taban_karari(kod: int, cikti: str) -> tuple[str, bool]:
    if COKME_IZI in cikti:
        return "COKTU", False
    if kod == 0:
        return "YESIL", True
    return "KIRMIZI", False


def mutasyon_karari(kod: int, cikti: str, skor: str | None,
                    taban_skor: str | None) -> tuple[str, bool]:
    """⛔ SIRA ÖNEMLİ: çökme/duruş/kurulum, "düştü"den ÖNCE elenir."""
    if _durus_markoru(cikti):
        return "KIP-RED", False
    if COKME_IZI in cikti:
        return "COKTU", False
    if kod == 2:
        return "KURULAMADI", False
    if kod != 0:
        return "DUSTU", True
    if skor is None or taban_skor is None:
        return "OLCULEMEDI", False       # skorsuz çıktı: "kaçtı" DEMEK DEĞİL, ölçülemedi
    if skor != taban_skor:
        return "AYIRDI", True
    return "KACTI", False


# ── RAPOR ────────────────────────────────────────────────────────────────────
def _ham_yaz(repo: Path, ad: str, etiket: str, cikti: str) -> str:
    dizin = repo / ".tmp" / "battery"
    dizin.mkdir(parents=True, exist_ok=True)
    guvenli = re.sub(r"[^A-Za-z0-9_.-]", "_", f"{ad}-{etiket}")
    yol = dizin / f"{guvenli}.txt"
    yol.write_text(cikti, encoding="utf-8", errors="replace")
    return str(yol.relative_to(repo)).replace("\\", "/")


def _batarya(repo: Path, ad: str, kipler: list[str] | None, zaman_asimi: int,
             mutasyonlu: bool) -> list[tuple[str, str, str, str, float, bool]]:
    """(birim, beklenen, sonuc, skor, sure, ok) satırları."""
    kosucu = repo / "tests" / "fixtures" / ad / "run.py"
    if not kosucu.is_file():
        return [(f"{ad}/taban", "tam yesil", "YOK", "-", 0.0, False)]

    kod, cikti, sure = kos([sys.executable, str(kosucu)], repo, zaman_asimi)
    t_skor = _skor(cikti)
    etiket, ok = taban_karari(kod, cikti)
    _ham_yaz(repo, ad, "taban", cikti)
    satirlar = [(f"{ad}/taban", "tam yesil", f"{etiket}(rc={kod})", t_skor or "-", sure, ok)]

    if not mutasyonlu:
        return satirlar
    if kipler is None:
        kipler, kaynak = kipleri_kesfet(kosucu.read_text(encoding="utf-8", errors="replace"))
    else:
        kaynak = "ELLE"
    if not kipler:
        NOTLAR.append(f"{ad}: kesif={kaynak} · kip YOK")
        satirlar.append((f"{ad}/mutasyon", "-", f"KIP YOK (kesif={kaynak})", "-", 0.0, True))
        return satirlar
    if not ok:
        satirlar.append((f"{ad}/mutasyon", "dusmeli",
                         f"ATLANDI ({len(kipler)} kip; taban {etiket})", "-", 0.0, False))
        return satirlar

    for k in kipler:
        mk, mc, ms = kos([sys.executable, str(kosucu), k], repo, zaman_asimi)
        m_skor = _skor(mc)
        m_etiket, m_ok = mutasyon_karari(mk, mc, m_skor, t_skor)
        _ham_yaz(repo, ad, k.lstrip("-"), mc)
        satirlar.append((f"{ad} {k}", "dusmeli", f"{m_etiket}(rc={mk})",
                         m_skor or "-", ms, m_ok))
    NOTLAR.append(f"{ad}: kesif={kaynak} · {len(kipler)} kip")
    return satirlar


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("fixture")
    ap.add_argument("--kardes", nargs="*", default=[])
    ap.add_argument("--kardes-tam", action="store_true",
                    help="kardes fixture'larin mutasyon kiplerini de kos (varsayilan: yalniz taban)")
    ap.add_argument("--kip", nargs="*", default=None, help="kesfi atla, verilen kipleri kos")
    ap.add_argument("--precommit", action="store_true")
    ap.add_argument("--liste", action="store_true", help="yalniz kesif; hicbir sey kosulmaz")
    ap.add_argument("--repo", default=None, help="repo koku (varsayilan: bu dosyanin ustu)")
    ap.add_argument("--zaman-asimi", type=int, default=300)
    a = ap.parse_args(argv)

    repo = Path(a.repo).resolve() if a.repo else VARSAYILAN_REPO

    if a.liste:
        cikis = 0
        for ad in [a.fixture] + list(a.kardes):
            k = repo / "tests" / "fixtures" / ad / "run.py"
            if not k.is_file():
                print(f"  {ad:34s} KOSUCU YOK: {k}")
                cikis = 1
                continue
            kipler, kaynak = kipleri_kesfet(k.read_text(encoding="utf-8", errors="replace"))
            print(f"  {ad:34s} kesif={kaynak:8s} n={len(kipler)}  {kipler}")
        return cikis

    t0 = time.time()
    satirlar = _batarya(repo, a.fixture, a.kip, a.zaman_asimi, mutasyonlu=True)
    for kardes in a.kardes:
        satirlar += _batarya(repo, kardes, None, a.zaman_asimi, mutasyonlu=a.kardes_tam)

    if a.precommit:
        gate = repo / "scripts" / "git-hooks" / "core_precommit.py"
        if not gate.is_file():
            satirlar.append(("core_precommit --all", "exit 0", "YOK", "-", 0.0, False))
        else:
            kod, cikti, sure = kos([sys.executable, str(gate), "--all"], repo, a.zaman_asimi)
            _ham_yaz(repo, "core_precommit", "all", cikti)
            satirlar.append(("core_precommit --all", "exit 0",
                             f"{'OK' if kod == 0 else 'IHLAL'}(rc={kod})", "-", sure, kod == 0))

    dusuk = [s for s in satirlar if not s[5]]
    gosterilecek = satirlar
    kisaltildi = 0
    if len(satirlar) > OZET_SATIR_BUTCESI:
        gecen = [s for s in satirlar if s[5]]
        gosterilecek = dusuk + gecen[:max(0, OZET_SATIR_BUTCESI - len(dusuk))]
        kisaltildi = len(satirlar) - len(gosterilecek)

    print(f"\nBATARYA — {a.fixture}" + (f" (+kardes: {', '.join(a.kardes)})" if a.kardes else ""))
    print(f"{'BIRIM':44s} {'BEKLENEN':10s} {'SONUC':22s} {'SKOR':9s} {'SURE':>7s}  ")
    for birim, beklenen, sonuc, skor, sure, ok in gosterilecek:
        isaret = "PASS" if ok else "FAIL"
        print(f"{birim[:44]:44s} {beklenen:10s} {sonuc[:22]:22s} {skor:9s} {sure:6.1f}s  {isaret}")
    if kisaltildi:
        print(f"... +{kisaltildi} PASS satiri gizlendi (ham cikti: .tmp/battery/)")
    for n in NOTLAR:
        print(f"  ↳ {n}")
    print(f"TOPLAM: {len(satirlar) - len(dusuk)}/{len(satirlar)} PASS  "
          f"[{round(time.time() - t0, 1)}s]  ham cikti: .tmp/battery/")
    if dusuk:
        print("DUSEN: " + " · ".join(f"{s[0]}→{s[2]}" for s in dusuk[:8]))
    print("⚠ BATARYA TAM SUIT DEGILDIR — teslimden once: python tests/run_fixture_tests.py")
    return 1 if dusuk else 0


if __name__ == "__main__":
    raise SystemExit(main())
