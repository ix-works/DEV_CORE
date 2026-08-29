#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""std_tablo_include_kapsami — `check_standard_table_fields.py` INCLUDE kapsamı (kayıt #66).

SINIF: "gördüğünü çözemedi" DEĞİL, **"hiç görmedi"**. İkisi aynı şey değildir ve fark
tam olarak sahte-pozitifin doğduğu yerdir.

ÖLÇÜLMÜŞ VAKA (sap-research, canlı sistem, 2026-08-29):
  · Kayıt 2026-08-22'de beş alanı sahte-pozitif diyordu: `KNA1.loevm` · `.sperr` ·
    `.aufsd` · `.lifsd` · `.faksd`.
  · KNA1'in canlı DDL gövdesi DÖRT include taşır; `INCLUDE_LINE` deseni canlı metne
    koşulduğunda YALNIZ ÜÇÜNÜ döndürüyordu — `si_kna1` YOKTU. Sebep: desen kuyruğu
    `\\s*;?\\s*$` ile demirliyor, `include si_kna1 **not null**;` satırındaki ek o demiri
    kırıyor. Diğer üç include'da ek yok, onlar yakalanıyor.
  · `si_kna1` (406 satır) beş alanın BEŞİNİ de taşır (aufsd:8 · faksd:31 · lifsd:73 ·
    loevm:78 · sperr:107).
  · ⭐ ASIL KIRILAN GARANTİ: kaçırılan include `cozulemeyen` listesine DE düşmüyordu —
    desen onu hiç görmediği için "çözülemedi" bile denmiyordu ⇒ 2026-07-30'un
    "çözülemezse DOĞRULANAMADI de" garantisi HİÇ DEVREYE GİRMİYOR ⇒ 5 alan doğrudan
    `[BULGU]` oluyordu. Kayıttaki "30.07 fix'inin garantisi TUTMADI" gözleminin açıklaması budur.

⛔ REDDEDİLEN GENİŞ ÇARE (ölçümle): kuyruk demirini tamamen kaldırıp `\\b` ile kesmek.
   Yerel korpusta ölçüldü — 1.552 dosya / 490.365 satır (`node_modules` HARİÇ; 263'ü `.cds`):
       eski desen 0 eşleşme · GENİŞ varyant **124 YENİ eşleşme** · uygulanan DAR varyant **0**.
   124'ün tamamı DDIC include DEĞİLDİ: klasik ABAP `INCLUDE <prog>_f01.` deyimleri (nokta
   ile biter, `;` ile değil) ve README/SPEC düzyazısı (`include the` · `include one` ·
   `include any` · `include nested`). Yani geniş varyant, kapatmaya çalıştığı sahte-pozitif
   sınıfını BAŞKA BİR YERDE yeniden üretirdi.
   ⇒ N4 bu reddi KALICI kılar: geniş varyant geri gelirse korpus KIRILIR.

⚠ KAPSAM NİTELEYİCİSİ: kısıt-eki olarak CANLI ÖLÇÜLEN tek biçim `not null`dur. Desen
   ek-metnini genel tutar ama iddia yalnız `not null` için ölçülmüştür.

⚠ SAP'YE BAĞLANMAZ: `_fetch_source` sahte bir kaynakla değiştirilir ve `sap_adt_lib`
   `sys.modules`'e main() çağrılmadan ÖNCE enjekte edilir (import-anı yan etkisinden
   GEÇ kalmamak için). Kullanılan DDL metinleri canlı ölçümün birebir kopyasıdır.

Koşum:  python tests/fixtures/std_tablo_include_kapsami/run.py      (exit 0 = PASS)
MUTASYON — İKİ AYRI DEĞİŞMEZ (biri diğerini KAPSAMAZ):
  --mutasyon-kuyruk  → desen 2026-08-29 ÖNCESİNE döner (yalnız `\\s*;?\\s*$`)
                       ⇒ N1/N2/N3 DÜŞMELİ (si_kna1 kaçar, 5 alan [BULGU] olur),
                         N4/N5/N6 AYAKTA (FP çapaları + `cozulemeyen` yolu).
  --mutasyon-genis   → REDDEDİLEN geniş varyant (`\\b`) kurulur
                       ⇒ N4 DÜŞMELİ (düzyazı/klasik-ABAP INCLUDE yakalanır),
                         N1/N2/N3 AYAKTA (bu varyant recall'ı da çözer — FP'si sorundur).
Mutant BUGÜNKÜ kaynaktan üretilir; desen bulunamazsa koşucu SAYI RAPORLAMADAN durur.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
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
KAYNAK = KOK / "scripts" / "validators" / "check_standard_table_fields.py"

_GECERLI_KIP = {"--mutasyon-kuyruk", "--mutasyon-genis"}
for _a in sys.argv[1:]:
    if _a.startswith("--mutasyon") and _a not in _GECERLI_KIP:
        raise SystemExit(f"[KULLANIM] bilinmeyen mutasyon kipi: {_a} — gecerli: "
                         + ", ".join(sorted(_GECERLI_KIP)))
KIP = next((a for a in sys.argv[1:] if a in _GECERLI_KIP), "")

# ── CANLI ÖLÇÜLMÜŞ DDL GÖVDELERİ (sap-research 2026-08-29 — birebir include satırları) ──
KNA1 = """@EndUserText.label : 'General Data in Customer Master'
define structure kna1 {
  key mandt : mandt not null;
  key kunnr : kunnr not null;
  include si_kna1 not null;
  include incl_eew_kna1;
  include incl_eew_kna1_addr;
  include bus000_data_ctrlr;
}
"""
SI_KNA1 = """define structure si_kna1 {
  aufsd : aufsd;
  faksd : faksd;
  lifsd : lifsd;
  loevm : loevm_kna1;
  sperr : sperb_x;
  name1 : name1_gp;
}
"""
BOS = ""
# ⚠ FIXTURE SADAKATİ (ilk yazımda BU YANLIŞTI, ölçümle yakalandı): canlı sistemde KNA1'in
# DİĞER ÜÇ include'u ÇÖZÜLÜYOR (HTTP 200) — yalnız `si_kna1` deseni tarafından HİÇ
# GÖRÜLMÜYORDU. Bu üçü fixture'da "" (çözülemez) bırakılırsa `cozulemeyen` dolar,
# main() `[DOĞRULANAMADI]` yoluna girer ve `--mutasyon-kuyruk` altında N3 SAHTE-YEŞİL
# kalır (ölçüldü: mutasyon N3'ü kırmıyordu). Yani fixture, kusuru maskeliyordu.
# ⇒ Üçü de GEÇERLİ ama alan taşımayan gövdelerle çözülür: tek değişken `si_kna1`ın
#   GÖRÜLÜP GÖRÜLMEDİĞİDİR.
EEW = "define structure incl_eew_kna1 {\n}\n"
EEW_ADDR = "define structure incl_eew_kna1_addr {\n}\n"
CTRLR = "define structure bus000_data_ctrlr {\n}\n"
# 2026-07-30 canlı ölçümünün iki biçimi — REGRESYON ÇAPASI (fix bunları bozmamalı)
MARA = "define structure mara {\n  key mandt : mandt;\n  key matnr : matnr;\n  include emara\n}\n"
EMARA = "define structure emara {\n  matkl : matkl;\n  meins : meins;\n}\n"
LIKP = "define structure likp {\n  key vbeln : vbeln_vl;\n  likp_status : include likp_status;\n}\n"
LIKP_STATUS = "define structure likp_status {\n  wbstk : wbstk;\n}\n"
# Çözülemeyen zincir: include GÖRÜLÜR ama kaynağı gelmez → `cozulemeyen` dolmalı
KOTU = "define structure kotu {\n  key mandt : mandt;\n  include hic_gelmeyen_incl;\n}\n"

DDL = {"kna1": KNA1, "si_kna1": SI_KNA1, "incl_eew_kna1": EEW,
       "incl_eew_kna1_addr": EEW_ADDR, "bus000_data_ctrlr": CTRLR,
       "mara": MARA, "emara": EMARA, "likp": LIKP, "likp_status": LIKP_STATUS,
       "kotu": KOTU, "hic_gelmeyen_incl": BOS}

# ⛔ FP KORPUSU — biçimler yerel korpusta ÖLÇÜLDÜ (bkz. docstring); obje adları
#    jenerikleştirilmiştir (core PUBLIC repodur, gerçek Z adı taşınmaz).
FP_METIN = (
    "INCLUDE zsd001_i_ornek_f01.\n"                   # klasik ABAP: `.` ile biter
    "INCLUDE zsd001_i_ornek_top.\n"
    "This section will include the header fields\n"   # README duzyazisi
    "include one preprocessor directive\n"
    "  // include si_kna1 not null;\n"                # yorum satiri
)

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(ok), detay))


def _modul():
    """Ölçülecek modül: gerçek kaynak ya da mutant kopyası (temp'te; kardeş-import YOK)."""
    yol = KAYNAK
    if KIP:
        metin = KAYNAK.read_text(encoding="utf-8")
        eski = ("    r'(?:\\s*;?\\s*$'                          # (a) ek YOK: "
                "`include emara` / `include x;`\n"
                "    r'|(?:\\s+[a-z][a-z0-9_]*)+\\s*;\\s*$)',    # (b) DDL kısıt-eki VAR "
                "→ `;` ZORUNLU\n")
        yeni = ("    r'\\s*;?\\s*$',\n" if KIP == "--mutasyon-kuyruk" else "    r'\\b',\n")
        if metin.count(eski) != 1:
            print(f"⛔ MUTASYON DESENİ BULUNAMADI/ÇOK EŞLEŞTİ ({metin.count(eski)}x) "
                  f"[{KIP}] — SAYI RAPORLANMIYOR (sahte-yeşil yerine görünür duruş).")
            sys.exit(3)
        d = Path(tempfile.mkdtemp(prefix="cstf_mut_"))
        yol = d / "check_standard_table_fields.py"
        yol.write_text(metin.replace(eski, yeni), encoding="utf-8")
    spec = importlib.util.spec_from_file_location("cstf_fx", yol)
    m = importlib.util.module_from_spec(spec)                     # type: ignore[arg-type]
    sys.modules["cstf_fx"] = m
    spec.loader.exec_module(m)                                    # type: ignore[union-attr]
    return m


M = _modul()
M._fetch_source = lambda client, ad: DDL.get(ad.lower(), "")      # SAP'ye GİTMEZ
DISPUTED = ("loevm", "sperr", "aufsd", "lifsd", "faksd")

# ── N1 ⭐ ASIL FIX — `include ... not null;` görülüyor mu (recall) ────────────────
inc = M.INCLUDE_LINE.findall(KNA1)
kontrol("N1 ⭐ KNA1'in DÖRT include'unun DÖRDÜ de yakalanıyor (`not null` eki dahil)",
        [i.lower() for i in inc] == ["si_kna1", "incl_eew_kna1",
                                     "incl_eew_kna1_addr", "bus000_data_ctrlr"],
        f"bulunan={inc}")

# ── N2 — beş disputed alan ARTIK bulunuyor (sahte-pozitifin kökü kapandı) ────────
alanlar, cozulemeyen = M.fetch_table_fields(None, "kna1")
eksik = [f for f in DISPUTED if f not in alanlar]
kontrol("N2 ⭐ 5 disputed KNA1 alanının 5'i de çözülen zincirde BULUNUYOR",
        not eksik, f"alan={len(alanlar)} eksik={eksik or 'yok'}")

# ── N3 — UÇTAN UCA: sahte `[BULGU]` üretilmiyor (asıl kullanıcı-görünür sonuç) ───
sb = Path(tempfile.mkdtemp(prefix="cstf_"))
art = sb / "ZSD001_TEST_DDL.cds"
art.write_text("define view ZTest as select from kna1 {\n  " +
               ",\n  ".join(f"kna1.{f}" for f in DISPUTED) + "\n}\n", encoding="utf-8")
sahte = types.ModuleType("sap_adt_lib")
sahte.SAPADTClient = lambda *a, **k: object()                     # type: ignore[attr-defined]
sys.modules["sap_adt_lib"] = sahte                                # main()'den ÖNCE
_argv = sys.argv
sys.argv = ["check_standard_table_fields.py", str(art)]
_buf, _hata = io.StringIO(), io.StringIO()
try:
    with contextlib.redirect_stdout(_buf), contextlib.redirect_stderr(_hata):
        rc = M.main()
except Exception as exc:                                          # noqa: BLE001
    rc = -1
    _buf.write(f"COKME:{type(exc).__name__}: {exc}")
finally:
    sys.argv = _argv
cikti = _buf.getvalue() + _hata.getvalue()
kontrol("N3 ⭐ UÇTAN UCA: 5 alan için sahte [BULGU] YOK + exit 0",
        rc == 0 and "[BULGU]" not in cikti and "COKME" not in cikti,
        f"rc={rc} cikti={cikti.strip()[:140]!r}")

# ── N4 ⭐ FP ÇAPASI — REDDEDİLEN geniş varyantın bedeli burada ölçülür ───────────
fp = M.INCLUDE_LINE.findall(FP_METIN)
kontrol("N4 ⭐ FP ÇAPASI: klasik ABAP `INCLUDE x.` + düzyazı + yorum → HİÇBİRİ yakalanmaz",
        fp == [], f"yakalanan={fp}")

# ── N5 REGRESYON — 2026-07-30'un iki biçimi hâlâ çözülüyor ──────────────────────
a_mara, c_mara = M.fetch_table_fields(None, "mara")
a_likp, c_likp = M.fetch_table_fields(None, "likp")
kontrol("N5 REGRESYON: `include emara` (`;`SİZ, çıplak) + `x : include y;` (adlandırılmış)",
        {"matkl", "meins"} <= a_mara and "wbstk" in a_likp and not c_mara and not c_likp,
        f"mara={sorted(a_mara)} likp={sorted(a_likp)} coz={c_mara + c_likp}")

# ── N6 ⭐ KIRILAN GARANTİ — "görüldü ama çözülemedi" yolu HÂLÂ çalışıyor ─────────
#    Kaydın asıl kırılan sözü buydu: çözülemeyen include `cozulemeyen`e DÜŞMELİ ki
#    main() `[BULGU]` yerine `[DOĞRULANAMADI]` yazsın ("bulunamadı ≠ yok").
a_kotu, c_kotu = M.fetch_table_fields(None, "kotu")
kontrol("N6 ⭐ çözülemeyen include `cozulemeyen`e DÜŞÜYOR (DOĞRULANAMADI yolu ayakta)",
        c_kotu == ["hic_gelmeyen_incl"], f"cozulemeyen={c_kotu}")

art2 = sb / "ZSD001_TEST_KOTU.cds"
art2.write_text("define view ZTest2 as select from kotu {\n  kotu.hicyokalan\n}\n",
                encoding="utf-8")
sys.argv = ["check_standard_table_fields.py", str(art2)]
_buf2 = io.StringIO()
try:
    with contextlib.redirect_stdout(_buf2), contextlib.redirect_stderr(io.StringIO()):
        rc2 = M.main()
finally:
    sys.argv = _argv
c2 = _buf2.getvalue()
kontrol("N6b ⭐ UÇTAN UCA: çözülemeyen zincirde çıktı [DOĞRULANAMADI] der, [BULGU] DEMEZ",
        "[DOĞRULANAMADI]" in c2 and "[BULGU]" not in c2 and rc2 == 0,
        f"rc={rc2} cikti={c2.strip()[:140]!r}")

gecen = sum(1 for _, ok, _ in SONUC if ok)
etiket = f" [{KIP}]" if KIP else ""
print(f"\n=== std_tablo_include_kapsami{etiket} ===")
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok:
        print(f"         -> {detay}")
dusen = [ad.split(" ")[0] for ad, ok, _ in SONUC if not ok]
if dusen:
    print("DÜŞEN VEKTÖRLER: " + ", ".join(dusen))
print(f"\n{gecen}/{len(SONUC)} OK")
sys.exit(0 if gecen == len(SONUC) else 1)
