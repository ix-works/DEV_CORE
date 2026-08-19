#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cds_curr_kaynak_tipi — check_cds_currency_reference KAYNAK TİPİ tespiti (V2).

VAKA (2026-08-19 kuyruk-kaydı): tespit ALT-DİZİ testiydi —
`if 'define table' in text ... elif 'define view' in text ... else: UYARI; return 0`.
`define root view entity` bu alt-diziyi İÇERMEZ ("root" araya girer) → tip bulunamaz →
stderr'e UYARI basılır ama **rc=0** dönülür. `run_review` rc=0'ı PASS sayar ⇒ validator
6 yerde BLOCKER kablolu olmasına rağmen (cds_creation · cds_update · table_creation ·
table_update · struct_creation · rap_cds_creation) o dosyalara **hiç bakmadan yeşil**
veriyordu. RAP'ın asıl kök görünüm biçimi denetim dışıydı.

ÖLÇÜM (bir tüketici projenin `<source_root>`'u, 273 CDS/DDL dosyası): **62 dosya** bu
yoldan sessizce geçiyordu — 30 `define root view entity` + 31 `define abstract entity`
+ 1 `define type`.

İKİ DEĞİŞMEZ → İKİ AYRI MUTASYON (howto-infra-fix D2):
  (a) yeni biçimler TANINIR            → M1 (eski alt-dizi mantığını geri getir)
  (b) tanınmayan tip SESSİZ GEÇMEZ     → M2 (fail-open: rc=2 yerine rc=0)
Ek: M3 yönlendirme kararı (abstract entity = cds, tablo DEĞİL — FP koruması),
    M4 table-function'ın BİLİNÇLİ atlanması korunuyor mu.

⚠ MUTASYON-DOSTU TASARIM: vektörler CLI üzerinden (subprocess) ölçülür — ölçülen şey
`run_review`'in gördüğü ÇIKIŞ KODU'dur. Fix'ten ÖNCEKİ sürüme karşı koşulduğunda koşucu
ÇÖKMEZ, kaç vektörün düştüğünü ÖLÇER.

⚠ MUTANT NEREDE YAŞAR: mutasyon kopyası **gerçek `scripts/validators/` dizinine**
`_mutant_*.py` adıyla yazılır (finally'de silinir). NEDEN: validator kendi yolundan
`parents[1]` ile `utils.ddic_semantics`'i import eder; tempdir'e kopyalanırsa import
ÖLÜR ve her mutasyon "yakalandı" görünür — SAHTE-KIRMIZI.

Kullanım:
    python tests/fixtures/cds_curr_kaynak_tipi/run.py              → exit 0 = tüm vektörler OK
    python tests/fixtures/cds_curr_kaynak_tipi/run.py --mutasyon   → 4 mutasyon ayırt edici mi
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
VALIDATOR = REPO / "scripts" / "validators" / "check_cds_currency_reference.py"

SONUC: list[tuple[bool, str]] = []


# ─────────────────────────── VEKTÖRLER ───────────────────────────
# Şekiller canlı-aktif artefaktlardan örneklendi (obje adları jenerikleştirildi):
#   root view entity  → bir tüketici projenin RAP interface view'ı
#   define type       → canlı DDIC structure'ın raw ADT `source/main` çıktısı
#   abstract entity   → playbook/adt-cds.md §ABSTRACT ENTITY (action param/result)

A1 = ("A1.cds", """@AbapCatalog.viewEnhancementCategory : [#NONE]
@EndUserText.label : 'Sevk Havuzu'
define root view entity ZSD001_I_POOL
  as select from vbap
{
  key vbeln as Vbeln,
      @Semantics.quantity.unitOfMeasure : 'SalesUnit'
      kwmeng as Kwmeng,
      vrkme  as SalesUnit
}
""")

# A2 — AYNI biçim, GEÇERSİZ annotation değeri: ne qualified ne geçerli identifier.
A2 = ("A2.cds", """@EndUserText.label : 'Bozuk referans'
define root view entity ZSD001_I_BOZUK
  as select from vbap
{
  key vbeln as Vbeln,
      @Semantics.amount.currencyCode : '99 gecersiz!'
      netwr  as Netwr,
      waerk  as Waerk
}
""")

# A3 — A2'nin DÜZELTİLMİŞ hâli (view entity'de referans = EXPOSED ELEMENT adı)
A3 = ("A3.cds", A2[1].replace("'99 gecersiz!'", "'Waerk'").replace("ZSD001_I_BOZUK", "ZSD001_I_DUZGUN"))

# A4 — abstract entity: alan listesi ŞEKLİ tablo gibi ama arkasında DDIC tablo YOK →
# referans aynı entity'nin ELEMANI'dır. 'table' yoluna yönlendirilirse "qualified değil"
# YANLIŞ-POZİTİF'i basılır (M3 mutasyonunun mezar taşı).
A4 = ("A4.cds", """@EndUserText.label : 'Action parametresi'
define abstract entity ZSD001_A_PARAM
{
  @Semantics.amount.currencyCode : 'Waerk'
  netwr : netwr;
  waerk : waerk;
}
""")

# A5a — `define type` (canlı DDIC structure biçimi) TEMİZ: qualified + CUKY marker
A5a = ("A5a.struct.ddls", """@EndUserText.label : 'Rapor Structure'
define type zsd001_s_rapor_ok {
  key mandt : mandt;
  @Semantics.amount.currencyCode : 'zsd001_s_rapor_ok.waers'
  netwr     : netwr;
  @Semantics.currencyCode : true
  waers     : waers;
}
""")

# A5b — AYNI biçim, CURR annotation EKSİK → BLOCKER. "Erişilemez yeşil = ölü gate"
# dersinin karşılığı: yeni kapsam gerçekten KIRMIZI üretebiliyor mu?
A5b = ("A5b.struct.ddls", """@EndUserText.label : 'Rapor Structure'
define type zsd001_s_rapor_kotu {
  key mandt : mandt;
  netwr     : netwr;
  @Semantics.currencyCode : true
  waers     : waers;
}
""")

# ── B: FAIL-CLOSED (tanınmayan tip SESSİZ GEÇMEZ) ──
B1 = ("B1.cds", """@EndUserText.label : 'Taninmayan'
define zorbafish zsd001_x
{
  key a : mandt;
}
""")
B2 = ("B2.cds", """-- bu dosyada hic tanim yok
@EndUserText.label : 'bos'
""")
# B3 — sözcükler TANIDIK ama kombinasyon bilinmiyor (CAP-tarzı `entity`); ABAP CDS'te
# geçerli bir biçim değil → ÖLÇÜLEMEDİ, sessiz 'cds' varsayımı YASAK.
B3 = ("B3.cds", """define entity zsd001_x {
  key a : mandt;
}
""")
# B4 — DCL (`define role`): sözlükte HİÇ tanınmayan başlık. rc=2 doğru, ama TEŞHİS de
# doğru olmalı: "başlık YOK" demek okuyanı dosyanın boş olduğuna inandırır (ölçüldü:
# gerçek .dcl dosyalarında bu yanlış teşhis basılıyordu). ⚠ DCL bu validator'a otomatik
# YÖNLENMEZ (`_reviewer.OBJECT_TYPE_TO_TASK['dcl'] = None`); vektör elle çağrım içindir.
B4 = ("B4.dcl", """define role ZSD001_C_TEST {
  grant select on ZSD001_C_TEST where (bukrs) = aspect pfcg_auth;
}
""")

# ── C: KONTROL GRUBU — fix ÖNCESİ de çalışan davranışlar BOZULMADI mı ──
C1 = ("C1.cds", A1[1].replace("define root view entity", "define view entity"))
C2 = ("C2.cds", A2[1].replace("define root view entity", "define view entity"))
C3 = ("C3.tabl.ddl", """@EndUserText.label : 'Test Tablosu'
@AbapCatalog.tableCategory : #TRANSPARENT
define table zsd001_t_test {
  key mandt : mandt not null;
  netwr     : netwr;
  @Semantics.currencyCode : true
  waers     : waers;
}
""")
C4 = ("C4.asddls", """@EndUserText.label : 'Struct'
define structure zsd001_s_test {
  key mandt : mandt;
  @Semantics.quantity.unitOfMeasure : 'zsd001_s_test.meins'
  menge     : menge;
  @Semantics.unitOfMeasure : true
  meins     : meins;
}
""")
C5 = ("C5.cds", """@EndUserText.label : 'TF'
define table function ZSD001_TF_BASE
  returns { key mandt : mandt; netwr : netwr; }
  implemented by method zcl_x=>tf;
""")
# C6 — klasik DDIC view (`define view` + sqlViewName): eski kodun TEK tanıdığı CDS biçimi
C6 = ("C6.cds", """@AbapCatalog.sqlViewName: 'ZSD001VSOI'
@EndUserText.label : 'Klasik view'
define view zsd001_ddl_test as select from vbap {
  key vbeln as Vbeln,
      @Semantics.amount.currencyCode : 'Waerk'
      netwr as Netwr,
      waerk as Waerk
}
""")

# ── D: YANLIŞ-YÖNLENDİRME + FP ÇAPALARI (desen genişledi, tipi kaydırmıyor mu) ──
# D1 — annotation METNİ içinde 'define view' geçiyor ama dosya bir TABLO. İÇİNDE gerçek
# bir tablo ihlali VAR: tip 'cds'e kayarsa BLOCKER sessizce kaybolur (rc 1→0) — yani bu
# vektör hem tip-izini hem de ihlalin YAŞADIĞINI ölçer (rc'ye tek başına güvenilmez).
D1 = ("D1.tabl.ddl", """@EndUserText.label : 'define view eski surumdu'
@AbapCatalog.tableCategory : #TRANSPARENT
define table zsd001_t_tuzak {
  key mandt : mandt not null;
  netwr     : netwr;
  @Semantics.currencyCode : true
  waers     : waers;
}
""")
# D2 — nesne adı sözlük sözcüğü İÇERİR (`..._TABLE_...`): token yutan bir ayrıştırıcı
# tipi kaydırabilir.
D2 = ("D2.cds", """@EndUserText.label : 'Ad tuzagi'
define root view entity ZSD001_I_TABLE_VIEW_ENTITY_X
  as select from vbap
{
  key vbeln as Vbeln,
      @Semantics.amount.currencyCode : 'Waerk'
      netwr  as Netwr,
      waerk  as Waerk
}
""")


def _yaz(tmp: Path, v: tuple[str, str]) -> Path:
    p = tmp / v[0]
    p.write_text(v[1], encoding="utf-8")
    return p


def kos(validator: Path, dosya: Path, *ek: str) -> tuple[int, str]:
    """(rc, iz) — iz = stdout+stderr birleşimi (ayırt edicilik ÇIKTI-İZİ'nde, rc'de değil)."""
    r = subprocess.run([sys.executable, str(validator), str(dosya), *ek],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=60)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# (ad, vektör, beklenen_rc, izde_OLMALI, izde_OLMAMALI)
BEKLENTI: list[tuple[str, tuple[str, str], int, tuple[str, ...], tuple[str, ...]]] = [
    ("A1 root view entity DENETLENİYOR", A1, 0, ("(cds)",), ("tespit edilemedi", "ÖLÇÜLEMEDİ")),
    ("A2 root view entity GEÇERSİZ değer YAKALANIR", A2, 0, ("C-CDS-CUR-02",), ("ÖLÇÜLEMEDİ",)),
    ("A3 A2 düzeltilince TEMİZ", A3, 0, ("OK", "(cds)"), ("C-CDS-CUR-02", "ÖLÇÜLEMEDİ")),
    ("A4 abstract entity element-referansı FP ÜRETMEZ", A4, 0, ("(cds)",), ("BLOCKER", "ÖLÇÜLEMEDİ")),
    ("A5a define type temiz", A5a, 0, ("OK", "(table)"), ("BLOCKER", "ÖLÇÜLEMEDİ")),
    ("A5b define type EKSİK annotation → BLOCKER", A5b, 1, ("C-TBL-CUR-03", "netwr"), ()),
    ("B1 tanınmayan başlık → ÖLÇÜLEMEDİ", B1, 2, ("ÖLÇÜLEMEDİ",), ("OK —",)),
    ("B2 hiç tanım yok → ÖLÇÜLEMEDİ", B2, 2, ("ÖLÇÜLEMEDİ",), ("OK —",)),
    ("B3 bilinen sözcük/bilinmeyen kombinasyon → ÖLÇÜLEMEDİ", B3, 2, ("ÖLÇÜLEMEDİ",), ("OK —",)),
    ("B4 DCL: rc=2 VE teşhis başlığı DOĞRU raporlar", B4, 2,
     ("ÖLÇÜLEMEDİ", "define role"), ("başlığı YOK", "OK —")),
    ("C1 KONTROL view entity denetleniyor", C1, 0, ("(cds)",), ("ÖLÇÜLEMEDİ",)),
    ("C2 KONTROL view entity geçersiz değer", C2, 0, ("C-CDS-CUR-02",), ("ÖLÇÜLEMEDİ",)),
    ("C3 KONTROL define table BLOCKER", C3, 1, ("C-TBL-CUR-03", "netwr"), ("ÖLÇÜLEMEDİ",)),
    ("C4 KONTROL define structure temiz", C4, 0, ("OK", "(table)"), ("BLOCKER", "ÖLÇÜLEMEDİ")),
    ("C5 KONTROL table function bilinçli atlanır", C5, 0, ("table function",), ("ÖLÇÜLEMEDİ",)),
    ("C6 KONTROL klasik define view", C6, 0, ("(cds)",), ("ÖLÇÜLEMEDİ",)),
    ("D1 annotation metninde 'define view' — TABLO kalır, ihlal YAŞAR", D1, 1,
     ("(table)", "C-TBL-CUR-03"), ("(cds)",)),
    ("D2 FP nesne adı sözlük sözcüğü içerir", D2, 0, ("(cds)",), ("ÖLÇÜLEMEDİ", "(table)")),
]


def vektorleri_kos(validator: Path, tmp: Path) -> list[tuple[bool, str]]:
    out = []
    for ad, vek, brc, olmali, olmamali in BEKLENTI:
        p = _yaz(tmp, vek)
        try:
            rc, iz = kos(validator, p)
        except Exception as e:  # noqa: BLE001 — çökme ≠ FAIL; ölçülen sonuca çevir
            out.append((False, f"{ad} — KOŞUM ÇÖKTÜ: {type(e).__name__}: {e}"))
            continue
        eksik = [s for s in olmali if s not in iz]
        fazla = [s for s in olmamali if s in iz]
        ok = (rc == brc) and not eksik and not fazla
        detay = f"rc={rc} (beklenen {brc})"
        if eksik:
            detay += f" · izde YOK: {eksik}"
        if fazla:
            detay += f" · izde OLMAMALI: {fazla}"
        out.append((ok, f"{ad} — {detay}"))
    # Açık --type override auto'yu bypass etmeye devam ediyor mu (sözleşme korunumu)
    p = _yaz(tmp, B1)
    rc, iz = kos(validator, p, "--type", "cds")
    out.append((rc == 0 and "ÖLÇÜLEMEDİ" not in iz,
                f"E1 --type ile açık override tanınmayan dosyayı da denetler — rc={rc}"))
    return out


# ─────────────────────────── MUTASYONLAR ───────────────────────────
# (ad, eski_parça, yeni_parça, düşmesi_BEKLENEN vektör kodları)
MUTASYONLAR: list[tuple[str, str, str, tuple[str, ...]]] = [
    ("M1 eski ALT-DİZİ mantığı geri gelsin (kusurun kendisi)",
     "    for raw_line in text.splitlines():\n        line = yorumu_kirp(raw_line)\n        m = _DEFINITION_RE.match(line)",
     "    if True:\n        return (('cds' if 'define view' in text else\n"
     "                 ('table' if ('define table' in text or 'define structure' in text) else None)), 'MUT-M1')\n"
     "    for raw_line in text.splitlines():\n        line = yorumu_kirp(raw_line)\n        m = _DEFINITION_RE.match(line)",
     ("A1", "A2", "A3", "A4", "A5a", "A5b")),
    ("M2 FAIL-OPEN: tanınmayan tip yine rc=0 dönsün",
     "                  file=sys.stderr)\n            return 2",
     "                  file=sys.stderr)\n            return 0",
     ("B1", "B2", "B3")),
    ("M3 abstract entity 'table' yoluna sürülsün (FP kapısı)",
     "        if seq[-1] == 'entity' and ('abstract' in seq or 'custom' in seq):\n            return 'cds', etiket",
     "        if seq[-1] == 'entity' and ('abstract' in seq or 'custom' in seq):\n            return 'table', etiket",
     ("A4",)),
    ("M4 table-function bilinçli atlaması sökülsün",
     "        if seq[-2:] == ['table', 'function']:\n            return 'table_function', etiket",
     "        if False:\n            return 'table_function', etiket",
     ("C5",)),
]


def mutasyon_kos() -> int:
    kaynak = VALIDATOR.read_text(encoding="utf-8")
    tmp = Path(tempfile.mkdtemp(prefix="cdscurr_mut_"))
    mutant = VALIDATOR.parent / "_mutant_check_cds_currency_reference.py"
    hepsi_ok = True
    try:
        for ad, eski, yeni, beklenen in MUTASYONLAR:
            # ⚠ "yama tuttu mu" kanıtı: sessiz NO-OP mutasyon "hiçbir vektör düşmedi"
            # der ve korpus güçlü sanılır.
            if eski not in kaynak:
                print(f"  [FAIL] {ad} — YAMA TUTMADI (çapa metin bulunamadı; kod değişmiş)")
                hepsi_ok = False
                continue
            mutant.write_text(kaynak.replace(eski, yeni, 1), encoding="utf-8")
            dusen = {satir[1].split(" ")[0] for satir in vektorleri_kos(mutant, tmp)
                     if not satir[0]}
            ok = set(beklenen) <= dusen
            hepsi_ok = hepsi_ok and ok
            print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
            print(f"         düşen={sorted(dusen)} | beklenen={sorted(beklenen)} altkume: {ok}")
    finally:
        if mutant.exists():
            mutant.unlink()
        pyc = mutant.parent / "__pycache__"
        if pyc.exists():
            for f in pyc.glob("_mutant_*"):
                f.unlink()
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\ncds_curr_kaynak_tipi MUTASYON: {'4/4 ayırt edici' if hepsi_ok else 'EKSİK'}")
    return 0 if hepsi_ok else 1


def main() -> int:
    if "--mutasyon" in sys.argv:
        return mutasyon_kos()
    if not VALIDATOR.exists():
        print(f"  [FAIL] validator YOK: {VALIDATOR}")
        return 1
    tmp = Path(tempfile.mkdtemp(prefix="cdscurr_"))
    try:
        SONUC.extend(vektorleri_kos(VALIDATOR, tmp))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    gecen = sum(1 for ok, _ in SONUC if ok)
    for ok, ad in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    print(f"\ncds_curr_kaynak_tipi: {gecen}/{len(SONUC)}")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    raise SystemExit(main())
