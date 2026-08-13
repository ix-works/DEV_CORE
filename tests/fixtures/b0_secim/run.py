#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""b0_secim — `run_fixture_tests.py --degisen` iş-özel seçim modunun korpusu.

KÖK (2026-08-13 kuyruk kaydı "infra B0 tam-süite kuralı"): süite 12 → 113 vektöre
büyüdü (TAM koşum **169,7 sn** ölçüldü) ama B0 reçetesi "tam süiteyi koş" diyordu.
İnfra-expert bir fix-seansında bunu 2× koşuyordu (~6 dk sabit vergi) — üstelik CI
aynı süiteyi TAM koşuyor ve lider merge öncesi bir kez daha koşuyor: **aynı sigorta
3-4×**. Seçim modu ARA adımların vergisini düşürür; sigortayı KALDIRMAZ.

⚠ BU KORPUSUN SINIRI (bilinçli): seçim **MANTIĞINI** ölçer, süitenin kendisini
KOŞMAZ (koşsaydı ölçtüğü verimi yerdi). Tek istisna V12/V13: seçimin gerçekten
KOŞUMA bağlandığını kanıtlamak için koşucu iki kez subprocess olarak çağrılır —
`kod ≠ kablolama` (bir "seçim listesi" doğru olabilir ve yine de hiçbir şeyi
etkilemiyor olabilir).

TASARIM — FAIL-CLOSED ÇAPALARI OMURGADIR: bir seçim mekanizmasının tehlikeli
hâli yanlış seçmesi değil, **sessizce daraltmasıdır**. Bu yüzden N vektörleri
(bilinmeyen dosya · boş liste · tanınmayan fixture dizini · repo dışı yol) P
vektörleri kadar ağırlıklıdır ve iki MUTASYON ikisini de ayrı ayrı çivilir.

MUTASYON (D2 mutasyon-dostu; `git show <sha>` YOK — gerekçe aşağıda):
    python tests/fixtures/b0_secim/run.py --mutasyon-failopen
        → `_eslesme` bilinmeyen dosyada None yerine BOŞ küme döndürür ("sessiz
          daraltma" tasarımı). Beklenen: N1/N4/N5 düşer, P vektörleri AYAKTA.
    python tests/fixtures/b0_secim/run.py --mutasyon-tamlik
        → `harita_tamlik` her zaman "ok" döndürür (kontrolün sökülmüş hâli).
          Beklenen: N2/N3 düşer, gerisi AYAKTA.
⚠ Neden SHA'ya pinlenmiş `git show` mutasyonu YOK: bu kod tabanda (0b3fff4) HİÇ
yoktu — mutasyonun hedefi geçmiş bir commit değil, **reddedilen tasarım kararının
kendisidir** (fail-open + törensel tamlık kontrolü). O yüzden mutasyon burada
enjekte edilir; koşucunun kaynağı EZİLMEZ, çalışma ağacı kirlenmez.

Koşum:  python tests/fixtures/b0_secim/run.py      (exit 0 = hepsi beklendiği gibi)
Koşucu: tests/run_fixture_tests.py (OZEL_TESTLER)
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

KOK = Path(__file__).resolve().parents[3]
KOSUCU = KOK / "tests" / "run_fixture_tests.py"
if not KOSUCU.is_file():
    raise SystemExit(f"[fixture-hatasi] koşucu bulunamadı: {KOSUCU}")

# Koşucuyu AYRI adla yükle: `tests/` sys.path'e girmesin, isim çakışması olmasın.
_spec = importlib.util.spec_from_file_location("rft_fx", KOSUCU)
R = importlib.util.module_from_spec(_spec)                    # type: ignore[arg-type]
sys.modules["rft_fx"] = R
_spec.loader.exec_module(R)                                   # type: ignore[union-attr]

MUT_FAILOPEN = "--mutasyon-failopen" in sys.argv
MUT_TAMLIK = "--mutasyon-tamlik" in sys.argv

if MUT_FAILOPEN:
    _asil_eslesme = R._eslesme

    def _mutant_eslesme(rel: str):
        br, gerekce = _asil_eslesme(rel)
        # "Bilmiyorsan hiçbir şey koşma" — sessiz daraltma tasarımı.
        return (set(), gerekce) if br is None else (br, gerekce)

    R._eslesme = _mutant_eslesme

if MUT_TAMLIK:
    R.harita_tamlik = lambda: [("HARİTA-TAMLIK/kapsam", "sökülmüş", True, ""),
                               ("HARİTA-TAMLIK/hayalet", "sökülmüş", True, "")]

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(ok), detay))


def sec(*dosyalar: str):
    return R.birimleri_sec(list(dosyalar))


def kos_kosucu(*args: str) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(KOSUCU), *args],
                       cwd=str(KOK), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# ══════════════════════════════════════════════════════════════════════════════
# P — DOĞRU ALT-KÜME
# ══════════════════════════════════════════════════════════════════════════════
# P1: bilinen dosya → TAM DEĞİL, tam olarak beklenen alt-küme. "Alt-küme boş
#     değil" demek yetmez: fazla seçmek vergiyi geri getirir, eksik seçmek
#     korumayı sessizce kaldırır → EŞİTLİK ölçülür.
secim, _ = sec("scripts/build_core_index.py")
kontrol("P1 bilinen dosya → yalnız ilgili fixture ({O:core_index_kapsam})",
        secim == {"O:core_index_kapsam"}, f"alınan={secim}")

secim, _ = sec("scripts/validators/check_bdef_backtick.py")
kontrol("P1b bölüm-1 validator → yalnız kendi bad/good çifti",
        secim == {"V:check_bdef_backtick"}, f"alınan={secim}")

# P2: BİRLEŞİM — iki dosya verildiğinde kümeler toplanır (biri diğerini yutmaz).
secim, _ = sec("scripts/build_core_index.py",
               "scripts/validators/check_ui5_freestyle_traps.py")
kontrol("P2 çok dosya → BİRLEŞİM (3 birim)",
        secim == {"O:core_index_kapsam", "O:ui5_t1_tirnak_sinifi",
                  "V:check_ui5_freestyle_traps"}, f"alınan={secim}")

# P3: bir dosya birden çok fixture'ı besliyorsa hepsi seçilir (tek-fixture varsayımı
#     seçim modunun en olası sessiz-daraltma kaynağıdır).
secim, _ = sec("scripts/sap_adt_lib.py")
kontrol("P3 çok-tüketicili kaynak → 6 korpusun hepsi",
        secim is not None and len(secim) == 6
        and {"O:lock_modification_support", "O:conn_cift_anahtar"} <= secim,
        f"alınan={sorted(secim) if secim else secim}")

# P4: mutlak yol + ters-bölü (Windows'ta ajanın vereceği gerçek biçim) aynı sonucu verir.
mutlak = str(KOK / "scripts" / "build_core_index.py")
secim, _ = sec(mutlak)
kontrol("P4 mutlak/Windows yolu göreli yolla AYNI kararı verir",
        secim == {"O:core_index_kapsam"}, f"girdi={mutlak} alınan={secim}")

# P5: fixture DİZİNİNE dokunmak o fixture'ı seçer (bölüm-2/3 dâhil).
s1, _ = sec("tests/fixtures/tier_fail_closed/run.py")
s2, _ = sec("tests/fixtures/av02_project_config_bom/bomlu.yaml")
s3, _ = sec("tests/fixtures/pre_tool_guard/agac/x.md")
kontrol("P5 fixture dizini → kendi birimi (OZEL / R:AV-02 / G)",
        s1 == {"O:tier_fail_closed"} and s2 == {"R:AV-02"} and s3 == {"G"},
        f"{s1} | {s2} | {s3}")

# ══════════════════════════════════════════════════════════════════════════════
# N — FAIL-CLOSED (bu korpusun asıl işi)
# ══════════════════════════════════════════════════════════════════════════════
# N1: haritada olmayan dosya → TAM süite + GÖRÜNÜR satır. Sessizce "0 birim"
#     seçilmesi en tehlikeli sonuçtur: koşum yeşil yanar, hiçbir şey ölçülmez.
secim, notlar = sec("scripts/hic_boyle_bir_dosya_yok.py")
kontrol("N1 bilinmeyen dosya → TAM süite kararı (fail-closed)",
        secim is None, f"alınan={secim}")
kontrol("N1b kararın GÖRÜNÜR gerekçesi basılıyor (sessiz daraltma yok)",
        any("bilinmeyen dosya" in n and "TAM" in n for n in notlar), f"notlar={notlar}")

# N2: yeni fixture eklenip harita güncellenmezse TAM koşum FAIL vermeli.
#     (Fixture-dizin kuralı bu fixture'ı "kapsıyor" görünürdü — tamlık kontrolü
#     onu bilerek saymaz; yoksa kontrol törenden ibaret olurdu.)
_asil_ozel = R.OZEL_TESTLER
try:
    R.OZEL_TESTLER = list(_asil_ozel) + [("sentetik_haritasiz_fixture", "sentetik")]
    vekt = R.harita_tamlik()
    kapsam_ok = next(ok for kisa, _, ok, _ in vekt if kisa.endswith("kapsam"))
    detay = next(d for kisa, _, _, d in vekt if kisa.endswith("kapsam"))
finally:
    R.OZEL_TESTLER = _asil_ozel
kontrol("N2 haritasız yeni fixture → HARİTA-TAMLIK FAIL",
        kapsam_ok is False and "sentetik_haritasiz_fixture" in detay,
        f"ok={kapsam_ok} detay={detay}")

# N3: haritada TANIMSIZ birim (yazım hatası) → FAIL. Yazım hatası sessiz kalırsa
#     o desen hiçbir zaman hiçbir şey seçmez ve kimse fark etmez.
_asil_harita = R.HARITA
try:
    R.HARITA = list(_asil_harita) + [("scripts/sentetik.py", ("O:boyle_bir_fixture_yok",), "s")]
    vekt = R.harita_tamlik()
    hayalet_ok = next(ok for kisa, _, ok, _ in vekt if kisa.endswith("hayalet"))
finally:
    R.HARITA = _asil_harita
kontrol("N3 haritada tanımsız birim → HARİTA-TAMLIK FAIL", hayalet_ok is False,
        f"ok={hayalet_ok}")

# N4: repo DIŞI yol → TAM (ajan yanlış worktree'den yol verirse daraltma olmaz).
secim, notlar = sec(str(Path(KOK.anchor) / "hicbir" / "yerde" / "x.py"))
kontrol("N4 repo dışı yol → TAM süite", secim is None,
        f"alınan={secim} notlar={notlar}")

# N5: tanınmayan fixture DİZİNİ → TAM (dizin kuralı "her tests/ yolu güvenli" demez).
secim, _ = sec("tests/fixtures/boyle_bir_fixture_yok/run.py")
kontrol("N5 tanınmayan fixture dizini → TAM süite", secim is None, f"alınan={secim}")

# N6: AÇIKÇA boş bildirilmiş desen (bugün HARITA'da örneği yok — dal ölü kalmasın diye
#     sentetik ölçülür). Boş bildirim `None` DEĞİLDİR: TAM'a düşmez ama kararı GÖRÜNÜR
#     satır olarak yazar. Bu ayrım kaybolursa "bilmiyorum" ile "ilgisiz" karışır.
try:
    R.HARITA = list(_asil_harita) + [("sentetik/ilgisiz_alan/**", (), "korpus dışı alan")]
    secim, notlar = sec("sentetik/ilgisiz_alan/x.txt")
finally:
    R.HARITA = _asil_harita
kontrol("N6 açıkça boş bildirilmiş desen → daraltma GÖRÜNÜR satırla (TAM değil)",
        secim == set() and any("ilgili fixture YOK" in n for n in notlar),
        f"alınan={secim} notlar={notlar}")

# ══════════════════════════════════════════════════════════════════════════════
# FP ÇAPALARI — "aşırı sıkılaşmadı" kanıtı
# ══════════════════════════════════════════════════════════════════════════════
# F1: ARGÜMANSIZ davranış BİREBİR eski hâl — mevcut tüketiciler (CI, lider) etkilenmez.
kontrol("F1 argümansız çağrı → seçim YOK (TAM süite yolu)",
        R._argumanlari_coz([]) == (None, False), f"alınan={R._argumanlari_coz([])}")

# F2: gerçek harita BUGÜN tam — kontrol hem FAIL üretebiliyor (N2/N3) hem de
#     doğru durumda SESSİZ (yoksa her koşumda gürültü = alarm yorgunluğu).
vekt = R.harita_tamlik()
kontrol("F2 mevcut harita TAM (pozitif kontrol: kontrol sahte-alarm vermiyor)",
        all(ok for _, _, ok, _ in vekt), f"detay={[d for _, _, ok, d in vekt if not ok]}")

# F3: koşucunun KENDİSİ değişirse TAM (seçim mantığının kıyas tabanı kaybolmasın).
secim, _ = sec("tests/run_fixture_tests.py")
kontrol("F3 koşucunun kendisi → TAM süite", secim is None, f"alınan={secim}")

# F4: indekslenen doküman alanı → yalnız CORE-INDEX korpusu (doküman değişikliği
#     TAM süite tetiklerse mod işe yaramaz; hiçbir şey tetiklemezse indeks çürür).
secim, _ = sec("governance/infra-test-recipes.md")
kontrol("F4 governance dokümanı → yalnız O:core_index_kapsam",
        secim == {"O:core_index_kapsam"}, f"alınan={secim}")

# ══════════════════════════════════════════════════════════════════════════════
# KABLOLAMA — seçim gerçekten KOŞUMU değiştiriyor mu (kod ≠ kablolama)
# ══════════════════════════════════════════════════════════════════════════════
if MUT_FAILOPEN or MUT_TAMLIK:
    # Mutasyonlar modül-içi enjeksiyondur; subprocess onları GÖRMEZ → koşmak
    # yanıltıcı "PASS" üretirdi (sahte-PASS). Açıkça atlanır.
    kontrol("V12/V13 KABLOLAMA — mutasyon modunda ATLANDI (subprocess mutasyonu görmez)",
            True, "bilinçli atlama")
else:
    rc, cikti = kos_kosucu("--degisen", "scripts/build_core_index.py")
    kontrol("V12 KABLOLAMA: seçili koşum yalnız seçilen fixture'ı KOŞAR",
            rc == 0 and "core_index_kapsam" in cikti
            and "tier_fail_closed" not in cikti
            and "TOPLAM: 1/1 PASS" in cikti,
            f"exit={rc} son={cikti.strip()[-200:]!r}")
    kontrol("V12b seçili koşum kendini TAM sanmıyor (görünür uyarı satırı)",
            "TAM SÜİTE SONUCU DEĞİLDİR" in cikti, f"çıktı={cikti[-200:]!r}")

    rc, cikti = kos_kosucu("--degisen", "scripts/hic_yok.py", "--listele")
    kontrol("V13 KABLOLAMA: bilinmeyen dosya kararı CLI'da da TAM (fail-closed)",
            rc == 0 and "TAM süite koşulacak" in cikti, f"exit={rc} çıktı={cikti[:200]!r}")

# ── rapor ──────────────────────────────────────────────────────────────────────
gecen = sum(1 for _, ok, _ in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok:
        print(f"         -> {detay}")
mod = ("  [MUTASYON: fail-open]" if MUT_FAILOPEN else
       "  [MUTASYON: tamlık sökülü]" if MUT_TAMLIK else "")
print(f"\n{gecen}/{len(SONUC)} OK{mod}")
sys.exit(0 if gecen == len(SONUC) else 1)
