#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fixture — `tests/run_battery.py` (batarya koşucusu, 2026-08-29).

**Sınıf:** batarya aracı bir KAPI DEĞİL, bir ÖLÇÜM ALETİDİR — ve bozuk bir ölçüm aleti
"her şey yeşil" der. Bu korpusun tek işi aracın **sessiz-yeşil üretmediğini** çivilemektir:
mutasyon kaçtığında · koşucu kurulamadığında · koşucu çöktüğünde · koşucu hiç
bulunamadığında araç bunları AYRI etiketlerle ve exit 1 ile bildirmeli.

**Bu korpus neyi çivilliyor:**
  (a) KEŞİF üç katmanlı ve DOKÜMAN katmanı ŞART                     → P1, P2, P3, P8
  (b) FP ÇAPASI: yorumdaki `--mutasyon-ZIRVA` örneği keşfe SIZMAZ   → P4
  (c) GERÇEK koşucuda uçtan uca: `exit 0` + skor farkı = AYIRDI     → P5, P6
      (⛔ "mutasyon exit≠0 vermeli" kuralı YANLIŞ olurdu: canlı korpusta 33 kipin
       15'i exit 0 döner — naif kural %45 sahte-FAIL üretirdi, ölçüldü 2026-08-29)
  (d) kip YOKSA araç çökmez, "KIP YOK" der ve exit 0               → N1
  (e) mutasyon KAÇARSA (exit 0 + AYNI skor) exit 1                 → N2
  (f) taban KIRMIZI ise mutasyonlar KOŞULMAZ + exit 1              → N3, N3b
  (g) `[DURDU]`/`[KULLANIM]` = KIP-RED · exit 2 VEYA 3 = KURULAMADI ·
      Traceback = COKTU — üçü "düştü" SAYILMAZ                     → N4, N4b, N5
  (h) koşucu YOKSA sessiz atlama yok (exit 0 iki anlamlıdır)        → N6
  (i) skor okunamıyorsa "KACTI" değil "OLCULEMEDI"                 → N8
  (j) `--precommit` gate'i yoksa SESSİZ atlanmaz                    → N9
  (k) kardeş fixture VARSAYILAN olarak yalnız TABAN koşar           → N10
  (l) `PYTHONUTF8` OLMADAN da çalışır (Windows cp1254 tuzağı)      → N11
  (m) özet BÜTÇELİ (bağlam ekonomisi) + ham çıktı diske yazılır     → P6, P7

⚠ **Sentetik koşucular KUM İÇİNDE yaşar** (`tempfile.TemporaryDirectory`); gerçek
`tests/fixtures/` ağacına hiçbir şey yazılmaz. Gerçek repoya karşı koşan vektörler
(P1-P6) yalnız OKUR; aracın kendi `.tmp/battery/` çıktısı gitignore'ludur.

Koşum:  python tests/fixtures/run_battery/run.py
MUTASYON — ALTI AYRI DEĞİŞMEZ (hiçbiri diğerini kapsamaz; her biri TEK çapayı keser):
  --mutasyon-kacak-kor     KACTI kararı PASS sayılır          → N2 DÜŞMELİ
  --mutasyon-kurulum-kor   KURULAMADI(exit 2/3) PASS sayılır  → N4b + N4c DÜŞMELİ
  --mutasyon-uc-kor        exit 3 yeniden "DUSTU" sayılır     → N4c DÜŞMELİ (yalnız o)
  --mutasyon-red-kor       KIP-RED (marker) PASS sayılır      → N4 DÜŞMELİ
  --mutasyon-cokme-kor     Traceback görmezden gelinir        → N5 DÜŞMELİ
  --mutasyon-olcum-kor     OLCULEMEDI PASS sayılır            → N8 DÜŞMELİ
  --mutasyon-kesif-kor     DOKÜMAN keşif katmanı sökülür      → P2 DÜŞMELİ
Mutasyon git ref'inden DEĞİL **bugünkü kaynaktan** üretilir (taban kayması tuzağı yapısal
olarak yok — merge sonrası da aynı ölçer). Desen 1 kez bulunmazsa koşucu SAYI RAPORLAMADAN
durur (`exit 2`): "kurulamadı", "kaçtı" değildir.
"""
from __future__ import annotations

import importlib.util
import io
import os
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
ARAC = REPO / "tests" / "run_battery.py"

# ⛔ BİLİNMEYEN KİP SESSİZCE YEŞİL GEÇMESİN (negatif_test_harness sözleşmesi).
GECERLI_KIP = {"--mutasyon-kacak-kor", "--mutasyon-kurulum-kor", "--mutasyon-red-kor",
               "--mutasyon-cokme-kor", "--mutasyon-olcum-kor", "--mutasyon-kesif-kor",
               "--mutasyon-uc-kor"}
for _a in sys.argv[1:]:
    if _a not in GECERLI_KIP:
        print(f"[DURDU] bilinmeyen kip: {_a!r} — gecerli: {sorted(GECERLI_KIP)}")
        sys.exit(2)
KIP = set(sys.argv[1:])

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul), detay))


def dur(neden: str) -> None:
    """SAYI RAPORLAMADAN duruş — kurulum sessiz başarısız olamaz."""
    print(f"[DURDU] KURULAMADI: {neden}")
    sys.exit(2)


# ── MUTASYON: BUGÜNKÜ kaynaktan türetilir ────────────────────────────────────
MUTASYONLAR = {
    "--mutasyon-kacak-kor": ('    return "KACTI", False', '    return "KACTI", True'),
    "--mutasyon-kurulum-kor": ('        return "KURULAMADI", False',
                               '        return "KURULAMADI", True'),
    "--mutasyon-red-kor": ('        return "KIP-RED", False', '        return "KIP-RED", True'),
    # exit 3 kapsamı SÖKÜLÜR → eski (bugün ölçülen) sahte-yeşil geri gelir: N4c düşer,
    # N4b AYAKTA kalır ⇒ iki kodun AYRI değişmez olduğu kanıtlanır.
    "--mutasyon-uc-kor": ("_KURULAMADI_KODLARI = (2, 3)", "_KURULAMADI_KODLARI = (2,)"),
    # ⚠ ÇAPA 2026-08-29'da TAZELENDİ: `if kod == 2:` satırı `_KURULAMADI_KODLARI`ye döndü.
    # Bayatlığı süitin YENİ BÖLÜM 4'ü ilk koşumda yakaladı (dogfooding: kip koşabilirliği
    # tam da bu sınıf içindir — çapası bayatlamış mutasyon sessizce koşmaz olur).
    "--mutasyon-cokme-kor": ('    if COKME_IZI in cikti:\n        return "COKTU", False\n'
                             '    if kod in _KURULAMADI_KODLARI:',
                             '    if False and COKME_IZI in cikti:\n        return "COKTU", False\n'
                             '    if kod in _KURULAMADI_KODLARI:'),
    "--mutasyon-olcum-kor": ('        return "OLCULEMEDI", False',
                             '        return "OLCULEMEDI", True'),
    "--mutasyon-kesif-kor": ('    if belge:\n        return sorted(belge), "DOKUMAN"',
                             '    if False and belge:\n        return sorted(belge), "DOKUMAN"'),
}


def arac_kaynagi() -> str:
    if not ARAC.is_file():
        dur(f"arac yok: {ARAC}")
    kaynak = ARAC.read_text(encoding="utf-8")
    for kip in sorted(KIP):
        eski, yeni = MUTASYONLAR[kip]
        if kaynak.count(eski) != 1:
            dur(f"{kip}: desen {kaynak.count(eski)} kez bulundu (1 bekleniyor) — "
                f"arac degisti, mutasyon bayatladi")
        kaynak = kaynak.replace(eski, yeni)
    return kaynak


TMP = tempfile.TemporaryDirectory(prefix="run_battery_fx_")
KOK = Path(TMP.name)
ARAC_YOLU = KOK / "run_battery_test.py"
ARAC_YOLU.write_text(arac_kaynagi(), encoding="utf-8", newline="")

# Modülü İÇERİ AL (keşif vektörleri için) — stdout gaspı korumasıyla (2026-08-09 dersi).
_yedek = (sys.stdout, sys.stderr)
sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
sys.stderr = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
try:
    _spec = importlib.util.spec_from_file_location("_battery_ut", ARAC_YOLU)
    M = importlib.util.module_from_spec(_spec)          # type: ignore[arg-type]
    _spec.loader.exec_module(M)                          # type: ignore[union-attr]
finally:
    sys.stdout, sys.stderr = _yedek

if KIP and all(getattr(M, "mutasyon_karari", None) for _ in [0]):
    pass  # modül yüklendi; mutasyonun etkisi vektörlerde ölçülür


def arac_kos(argv: list[str], repo: Path, utf8: bool = True) -> tuple[int, str]:
    env = os.environ.copy()
    env.pop("CLAUDE_PROJECT_DIR", None)
    if utf8:
        env["PYTHONUTF8"] = "1"
    else:
        env.pop("PYTHONUTF8", None)
        env.pop("PYTHONIOENCODING", None)
    p = subprocess.run([sys.executable, str(ARAC_YOLU), *argv, "--repo", str(repo)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=300)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def satir(cikti: str, parca: str) -> str:
    for s in cikti.splitlines():
        if parca in s:
            return s
    return ""


# ═════════════════════════ P — GERÇEK KORPUS (yalnız okur) ═══════════════════
def _kesif(ad: str) -> tuple[list[str], str]:
    yol = REPO / "tests" / "fixtures" / ad / "run.py"
    if not yol.is_file():
        dur(f"gercek kosucu yok: {yol} (korpus tasindi mi?)")
    return M.kipleri_kesfet(yol.read_text(encoding="utf-8", errors="replace"))

k1, kay1 = _kesif("session_start_compact_dali")
kontrol("P1 BEYAN katmani: acik kip kumesi okunur",
        kay1 == "BEYAN" and set(k1) == {"--mutasyon-capasiz", "--mutasyon-dalsiz",
                                        "--mutasyon-state"},
        f"kaynak={kay1} kip={k1}")

k2, kay2 = _kesif("fs_docstd")
# ⚠ SAYI KORPUSA PİNLİ (b0_secim P2/P3 ile aynı sözleşme): `fs_docstd`e kip eklenirse
# (2026-08-29: 10→13, kayıt Q209 koşucu mutasyonları) BU SATIR da güncellenir. Sayıyı
# gevşetmek (`>=`) çapayı öldürür: keşif katmanının SESSİZ daralması tam burada görünür.
kontrol("P2 DOKUMAN katmani SART: son-ekle cozen kosucunun 13 kipi bulunur",
        kay2 == "DOKUMAN" and len(k2) == 13 and "--mutasyon-katman0" in k2,
        f"kaynak={kay2} n={len(k2)}")

k3, kay3 = _kesif("worktree_yasam_dongusu")
kontrol("P3 AST katmani: beyansiz kosucunun kipi kod sabitinden gelir",
        kay3 == "AST" and k3 == ["--mutasyon"], f"kaynak={kay3} kip={k3}")

# FP ÇAPASI — `--mutasyon-ZIRVA` YORUMLARDA yaşar; hiçbir katman onu keşfetmemeli.
zirva_yorumu, zirva_kesif = 0, []
for _k in sorted((REPO / "tests" / "fixtures").glob("*/run.py")):
    _src = _k.read_text(encoding="utf-8", errors="replace")
    if "--mutasyon-ZIRVA" in _src:
        zirva_yorumu += 1
    if "--mutasyon-ZIRVA" in M.kipleri_kesfet(_src)[0]:
        zirva_kesif.append(_k.parent.name)
kontrol("P4 FP CAPASI: yorumdaki ZIRVA ornegi keside SIZMAZ",
        zirva_yorumu >= 5 and not zirva_kesif,
        f"ZIRVA yorumu olan kosucu={zirva_yorumu} · kesfe sizan={zirva_kesif}")

# Uçtan uca GERÇEK koşum: `--mutasyon` exit 0 + skor farkı → AYIRDI (naif kural burada patlar).
rc5, c5 = arac_kos(["statusline_token_esikleri"], REPO)
kontrol("P5 GERCEK kosucu uctan uca: taban YESIL + mutasyon AYIRDI, exit 0",
        rc5 == 0 and "YESIL(rc=0)" in c5 and "AYIRDI(rc=0)" in c5,
        f"rc={rc5} · {satir(c5, '--mutasyon').strip()[:90]}")
kontrol("P5b naif kural reddi: exit 0 doner ama KACTI DEMEZ",
        "KACTI" not in c5, satir(c5, "KACTI"))
kontrol("P6 ozet BUTCELI (<= 25 satir) ve TOPLAM satiri var",
        len(c5.strip().splitlines()) <= 25 and "TOPLAM:" in c5,
        f"{len(c5.strip().splitlines())} satir")
ham = REPO / ".tmp" / "battery" / "statusline_token_esikleri-taban.txt"
kontrol("P7 ham cikti diske yazildi (baglam kirletilmez)",
        ham.is_file() and ham.stat().st_size > 0, str(ham))
kontrol("P8 kesif kaynagi RAPORLANIR (kaynagi bilmeden sonuc okunmaz)",
        "kesif=" in c5, satir(c5, "kesif="))

# P9 — ÖZ-KEŞİF: bu dosyada `{"--mutasyon-dalsiz", …}` gibi literaller BAŞKA koşucuların
# kiplerini TARİF eder (P1/P3 kıyasları). Onlar BEYAN sayılırsa araç kendi korpusunda
# hayalet kip koşar ve KIP-RED sahte-FAIL'i üretir — 2026-08-29'da bizzat ölçüldü.
k9, kay9 = M.kipleri_kesfet(Path(__file__).read_text(encoding="utf-8", errors="replace"))
kontrol("P9 FP CAPASI: kiyas operandi BEYAN sayilmaz (oz-kesif tam olarak 6 kip)",
        kay9 == "BEYAN" and set(k9) == GECERLI_KIP, f"kaynak={kay9} n={len(k9)} kip={k9}")

# P10 — KAPSAM TABANI: metninde `--mutasyon` geçen HER koşucu en az 1 kip vermeli.
# ⚠ Sayı PİNLENMEZ (korpus haftalık büyüyor, pin bayatlar): iddia "sessiz 0 kip YOK".
# DOKÜMAN katmanı sökülürse üç koşucu buraya düşer — kapsam kaybı görünür olur.
kipsizler = []
for _k in sorted((REPO / "tests" / "fixtures").glob("*/run.py")):
    _src = _k.read_text(encoding="utf-8", errors="replace")
    if "--mutasyon" in _src and not M.kipleri_kesfet(_src)[0]:
        kipsizler.append(_k.parent.name)
kontrol("P10 KAPSAM: '--mutasyon' gecen hicbir kosucu SESSIZ 0 kip vermiyor",
        not kipsizler, f"kesif bos donen kosucular={kipsizler}")

# ═════════════════════════ N — SENTETİK KUM ══════════════════════════════════
KUM = KOK / "kum"
(KUM / "tests" / "fixtures").mkdir(parents=True)
IZ = KUM / "kip-kosuldu.iz"


def kosucu(ad: str, govde: str) -> None:
    d = KUM / "tests" / "fixtures" / ad
    d.mkdir(parents=True, exist_ok=True)
    (d / "run.py").write_text(textwrap.dedent(govde), encoding="utf-8")


kosucu("kipsiz", """
    import sys
    print("3/3 OK")
    sys.exit(0)
""")
kosucu("kacan", """
    import sys
    _GECERLI_KIP = {"--mutasyon-x"}
    print("5/5 OK")          # kip verilse de AYNI: mutasyon KACTI
    sys.exit(0)
""")
kosucu("kirmizi", f"""
    import sys, pathlib
    _GECERLI_KIP = {{"--mutasyon-y"}}
    if len(sys.argv) > 1:
        pathlib.Path(r"{IZ}").write_text("kosuldu", encoding="utf-8")
    print("2/5 OK")
    sys.exit(1)
""")
kosucu("reddeden", """
    import sys
    _GECERLI_KIP = {"--mutasyon-z"}
    if len(sys.argv) > 1:
        print("[DURDU] bilinmeyen kip: %r" % sys.argv[1])
        sys.exit(2)
    print("6/6 OK")
""")
kosucu("kurulamayan", """
    import sys
    _GECERLI_KIP = {"--mutasyon-t"}
    if len(sys.argv) > 1:
        print("TABAN URETILEMEDI - desen bulunamadi")
        sys.exit(2)
    print("6/6 OK")
""")
kosucu("kurulamayan3", """
    import sys
    _GECERLI_KIP = {"--mutasyon-u"}
    if len(sys.argv) > 1:
        print("MUTASYON DESENI BULUNAMADI - SAYI RAPORLANMIYOR")
        sys.exit(3)
    print("6/6 OK")
""")
kosucu("coken", """
    import sys
    _GECERLI_KIP = {"--mutasyon-c"}
    if len(sys.argv) > 1:
        raise RuntimeError("mutasyon kurulumu patladi")
    print("4/4 OK")
""")
kosucu("ayiran", """
    import sys
    _GECERLI_KIP = {"--mutasyon-a"}
    print("4/9 OK" if len(sys.argv) > 1 else "9/9 OK")
    sys.exit(0)
""")
kosucu("skorsuz", """
    import sys
    _GECERLI_KIP = {"--mutasyon-s"}
    print("hepsi tamam" if len(sys.argv) > 1 else "hepsi tamam (taban)")
    sys.exit(0)
""")

rc, c = arac_kos(["kipsiz"], KUM)
kontrol("N1 kipsiz kosucu: 'KIP YOK' + exit 0 (cokme YOK)",
        rc == 0 and "KIP YOK" in c, f"rc={rc} · {satir(c, 'KIP YOK').strip()[:80]}")

rc, c = arac_kos(["kacan"], KUM)
kontrol("N2 mutasyon KACTI (exit 0 + AYNI skor) -> exit 1",
        rc == 1 and "KACTI" in c, f"rc={rc} · {satir(c, 'mutasyon-x').strip()[:80]}")

rc, c = arac_kos(["kirmizi"], KUM)
kontrol("N3 taban KIRMIZI -> exit 1 + mutasyonlar ATLANDI",
        rc == 1 and "KIRMIZI(rc=1)" in c and "ATLANDI" in c,
        f"rc={rc} · {satir(c, 'ATLANDI').strip()[:80]}")
kontrol("N3b taban kirmiziyken kip GERCEKTEN kosulmadi (yan-etki izi yok)",
        not IZ.exists(), f"iz={IZ.exists()}")

rc, c = arac_kos(["reddeden"], KUM)
kontrol("N4 [DURDU] markoru -> KIP-RED (exit 2'yi de ezer) + exit 1",
        rc == 1 and "KIP-RED" in c, f"rc={rc} · {satir(c, 'mutasyon-z').strip()[:80]}")

rc, c = arac_kos(["kurulamayan"], KUM)
kontrol("N4b exit 2 (markorsuz) -> KURULAMADI, 'DUSTU' DEGIL + exit 1",
        rc == 1 and "KURULAMADI" in c and "DUSTU" not in c,
        f"rc={rc} · {satir(c, 'mutasyon-t').strip()[:80]}")

# ⭐ N4c — GERÇEK VAKA (2026-08-29, kayıt Q210): "durdum" sinyali olarak exit 3 kullanan
# DÖRT koşucu var; araç 3'ü "DUSTU" sayınca çapası bayatlamış mutasyon YEŞİL geçiyordu.
# Bu vektör tam olarak o sahte-yeşili çiviler ("kurulamadı", "düştü" DEĞİLDİR).
rc, c = arac_kos(["kurulamayan3"], KUM)
kontrol("N4c ⭐ exit 3 (markorsuz) -> KURULAMADI, 'DUSTU' DEGIL + exit 1",
        rc == 1 and "KURULAMADI" in c and "DUSTU" not in c,
        f"rc={rc} · {satir(c, 'mutasyon-u').strip()[:80]}")

rc, c = arac_kos(["coken"], KUM)
kontrol("N5 Traceback -> COKTU (cokme != FAIL/DUSTU) + exit 1",
        rc == 1 and "COKTU" in c and "DUSTU" not in c,
        f"rc={rc} · {satir(c, 'mutasyon-c').strip()[:80]}")

rc, c = arac_kos(["ayiran"], KUM)
kontrol("N7 exit 0 + FARKLI skor -> AYIRDI, exit 0 (sahte-FAIL yok)",
        rc == 0 and "AYIRDI" in c, f"rc={rc} · {satir(c, 'mutasyon-a').strip()[:80]}")

rc, c = arac_kos(["skorsuz"], KUM)
kontrol("N8 skor okunamadi -> OLCULEMEDI ('KACTI' DEGIL) + exit 1",
        rc == 1 and "OLCULEMEDI" in c and "KACTI" not in c,
        f"rc={rc} · {satir(c, 'mutasyon-s').strip()[:80]}")

rc, c = arac_kos(["yok_boyle_bir_fixture"], KUM)
kontrol("N6 kosucu YOK -> 'YOK' satiri + exit 1 (sessiz atlama yok)",
        rc == 1 and "YOK" in c, f"rc={rc} · {satir(c, 'YOK').strip()[:80]}")

rc, c = arac_kos(["kipsiz", "--precommit"], KUM)
kontrol("N9 --precommit gate'i yoksa SESSIZ atlanmaz -> exit 1",
        rc == 1 and "core_precommit" in c, f"rc={rc} · {satir(c, 'core_precommit').strip()[:80]}")

IZ.unlink(missing_ok=True)
rc, c = arac_kos(["kipsiz", "--kardes", "kirmizi"], KUM)
kontrol("N10 kardes VARSAYILAN olarak yalniz TABAN kosar (kip yan-etkisi yok)",
        not IZ.exists() and "kirmizi/taban" in c, f"iz={IZ.exists()} rc={rc}")

rc, c = arac_kos(["ayiran"], KUM, utf8=False)
kontrol("N11 PYTHONUTF8 OLMADAN da kosar (Turkce ozet, UnicodeEncodeError yok)",
        rc == 0 and "AYIRDI" in c and "UnicodeEncodeError" not in c,
        f"rc={rc} · UnicodeEncodeError={'UnicodeEncodeError' in c}")

# ── RAPOR ────────────────────────────────────────────────────────────────────
gecen = sum(1 for _, ok, _ in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + (f" -- {detay}" if (detay and not ok) else ""))
mod = f"   (mutasyon: {' '.join(sorted(KIP))})" if KIP else ""
print(f"\n{gecen}/{len(SONUC)} OK{mod}")
TMP.cleanup()
sys.exit(0 if gecen == len(SONUC) else 1)
