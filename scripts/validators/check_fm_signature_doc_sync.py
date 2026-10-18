# -*- coding: utf-8 -*-
"""check_fm_signature_doc_sync.py — PAYLAŞILAN ABAP üreteçlerinin İMZASI ile KILAVUZU arasındaki sapma.

NEDEN (sınıf, vaka değil): paylaşılan bir Z objesinin (üreteç FM) parametreleri canlıda
değişince, o objenin KULLANIM KILAVUZU (core/playbook) kimsenin sorumluluğunda olmadan
bayatlar. Bayat kılavuz "bulunamadı" gibi görünmez — bir sonraki ajan/geliştirici onu
BULUR ve EKSİK bilgiyle çağrı kurar. Ölçülmüş iki vaka (`ZSD000_FM_SCREEN_GEN`):
  • 2026-07-31 — `IT_BUTTONS` imzada VARDI, kılavuzda YOKTU; bir ajan "üreteç buton
    üretemiyor" varsayıp yanlış yola (ALV-toolbar event'i) girdi.
  • 2026-08-14/18 — `IV_SRC_PROG` · `IV_SRC_STATUS` · `IV_CUA_MERGE` · `IV_NAV_REMAP`
    eklendi; 4 gün boyunca hiçbir belgeye yansımadı. Kılavuzdaki örnek zarf birebir
    kopyalansaydı VARSAYILAN (minimal) DONÖR devreye girecek, onun `&F2..&F5` fcode'larını
    `WHEN 'BACK'` bekleyen PAI yakalamayacaktı (sessiz; ekran GUI'de denenene kadar görünmez).
İki vaka aynı sınıftandır: "obje değişti, kılavuz değişmedi" — ve ikisini de HİÇBİR
kontrol görmedi (`check_playbook_freshness` yalnız `create_/populate_/run_*.py` script
değişimine bakar; ABAP kaynağı ile kılavuz arasında hiçbir bağ yoktu).

NASIL (exact-logic; sezgisel eşleştirme YOK):
  1. ABAP kaynağından FM imzası ayrıştırılır (IMPORTING/EXPORTING/CHANGING/TABLES).
  2. Kılavuzdaki MAKİNE-OKUNUR imza bloğundan belgelenen parametreler okunur:
         <!-- FM-IMZA: ZSD000_FM_SCREEN_GEN -->
         ... (tablo/metin; büyük harfli IV_/IT_/EV_/… token'ları sayılır)
         <!-- /FM-IMZA -->
     Blok SINIRI bilinçlidir: belgenin geri kalanında başka API'lerin parametreleri
     (`IS_LAYOUT`, `IT_OUTTAB` …) geçer; blok dışını saymak yanlış-pozitif üretirdi.
  3. Fark iki yönde raporlanır:
       EKSİK   : imzada VAR, belgede YOK  (bayat kılavuz — asıl vaka)
       HAYALET : belgede VAR, imzada YOK  (kaldırılmış/yanlış yazılmış parametre)

ÜÇ DURUM AYRI ÇIKIŞA DÜŞER ("bakamadım" ≠ "temiz"):
  TEMİZ        → exit 0, tek satır özet
  BULGU        → exit 0 + WARN (warn-first, ADR 0019 §54) · `--bulguda-exit1` ile exit 1
  ÖLÇÜLEMEDİ   → exit 2  (belge yok · imza bloğu yok · imza ayrıştırılamadı/çapa düştü)
  ATLANDI      → exit 0 + `[SKIP] … ÖLÇÜLMEDİ` satırı (proje bu üreteci SAĞLAMIYOR: kaynak
                 yolu `project.yaml` `fm_doc_sync_sources`'ta beyan edilmemiş — sessiz "OK"
                 basılmaz; `run_all --ozet` bu satırı da gösterir)
  Beyan VAR ama dosya YOK → ÖLÇÜLEMEDİ (exit 2): bağ kopuk, "üreteç yok" ile aynı şey değil.

KAYNAK YOLU YAPILANDIRMADIR, KOD DEĞİL (2026-10-18): üreteç FM'in ABAP kaynağı PROJENİN
reposunda yaşar (core yalnız kılavuzu taşır). Yol önceden burada sabit yazılıydı — bir
tüketici projenin dosya düzenine kablolu bir core kapısı (ters yön sızıntı). Artık proje
beyan eder (`MAINTENANCE.md` §6 kataloğu):
    fm_doc_sync_sources: ["screen_gen:<MOD>/<PKG>/functions/<FM>.func.abap"]
(`<kayıt-id>:<source_root-göreli yol>`; env override `IX_FM_DOC_SYNC_SOURCES`, virgülle).

`--strict` BİLEREK NO-OP'tur: `run_all_validators --strict` bayrağını TÜM validator'lara
iletir; bu gate'i oradan hard'a terfi ettirmek terfi kararını kazara bir çağıranın eline
verirdi (kardeş warn-first gate'lerin sözleşmesiyle aynı: check_fs_no_analysis_log).
⚠ Dosya adında "freshness" GEÇMEZ — `run_all_validators --quick` (pre-commit) adında
"freshness" geçen validator'ları ATLAR; bu gate'in pre-commit'te koşması ŞARTTIR.

Kullanım:
    python scripts/validators/check_fm_signature_doc_sync.py [--bulguda-exit1] [--selftest]
                                                             [--kayit <id>] [--core <yol>]
Kablolama: run_all_validators (PROJE modu; CORE modunda SKIP — proje kaynağı gerekir).
Kalıcı korpus: tests/fixtures/fm_imza_doc_sync (15 vektör, 7 mutasyon).
"""
# ENFORCES: CLC-SCR7
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

# Bu validator CORE dosyalarını (playbook) okur → core kökünü __file__'dan türetmek
# MEŞRU ve zorunludur (check_project_root_resolution: "core-içi yollar İHLAL DEĞİL").
# PROJE tarafı (ABAP kaynağı) ASLA __file__'dan türetilmez → utils.project_config.
CORE_ROOT = Path(__file__).resolve().parents[2]


class Kayit:
    """Bir paylaşılan üreteç: ABAP kaynağı ↔ onu belgeleyen kılavuz(lar)."""

    def __init__(self, kid: str, fm: str, belgeler: tuple, capa: str):
        self.id = kid            # kısa ad (--kayit ile seçilir) = config anahtarındaki kayıt-id
        self.fm = fm             # FM adı (imza bloğu etiketi de budur)
        self.belgeler = belgeler  # CORE-göreli belge yolları; her biri FM-IMZA bloğu TAŞIMALI
        self.capa = capa         # imza ayrıştırması bu parametreyi bulmazsa ÖLÇÜLEMEDİ
        # ⛔ Kaynak yolu burada YOK: proje beyan eder (`fm_doc_sync_sources`), bkz. docstring.


CONFIG_ANAHTARI = "fm_doc_sync_sources"

KAYITLAR = [
    Kayit(
        kid="screen_gen",
        fm="ZSD000_FM_SCREEN_GEN",   # core'un ortak-paket demo ad alanı (ZSD000 istisnası)
        belgeler=(
            "playbook/howto-dynpro-gui-status-generation.md",   # adım-adım kullanım kılavuzu
            "playbook/adt-fugr-functions.md",                   # §6 derin iç-mekanik referansı
        ),
        capa="IV_PROGRAM",
    ),
]

# --- imza ayrıştırma ---------------------------------------------------------
_BOLUM = re.compile(r"^\s*(IMPORTING|EXPORTING|CHANGING|TABLES)\s*$", re.IGNORECASE)
_VALUE = re.compile(r"\b(?:VALUE|REFERENCE)\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)")
_DUZ = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+(?:TYPE|LIKE|STRUCTURE)\b", re.IGNORECASE)
_TOKEN = re.compile(r"\b(?:IV|IT|IS|IO|IR|EV|ET|ES|CV|CT|CS|EX)_[A-Z][A-Z0-9_]*\b")
_BLOK = "<!-- FM-IMZA: {fm} -->"
_BLOK_SON = "<!-- /FM-IMZA -->"


class Olculemedi(Exception):
    """Ölçüm yapılamadı — 'temiz' ile AYNI çıkışa düşmemesi için ayrı sınıf."""


def imza_parametreleri(metin: str, fm: str) -> set:
    """FM imzasındaki parametre adları (BÜYÜK harf). Ayrıştıramazsa Olculemedi."""
    satirlar = metin.splitlines()
    bas = None
    for i, s in enumerate(satirlar):
        if re.match(rf"^\s*FUNCTION\s+{re.escape(fm)}\b", s, re.IGNORECASE):
            bas = i
            break
    if bas is None:
        raise Olculemedi(f"kaynakta `FUNCTION {fm}` satırı YOK (ad değişmiş ya da dosya yanlış)")

    parametreler, bolumde = set(), False
    for s in satirlar[bas + 1:]:
        ham = s.rstrip()
        govde = ham.split('"', 1)[0]                 # satır-sonu ABAP yorumu
        if ham.lstrip().startswith("*"):             # tam-satır yorum → hiç bakma
            continue
        if _BOLUM.match(govde.strip().rstrip(".")):
            bolumde = True
            if govde.rstrip().endswith("."):
                break
            continue
        if bolumde:
            m = _VALUE.search(govde) or _DUZ.match(govde)
            if m:
                parametreler.add(m.group(1).upper())
        if govde.rstrip().endswith("."):             # imza bloğunun sonu
            break
    if not parametreler:
        raise Olculemedi(f"`FUNCTION {fm}` bulundu ama HİÇ parametre ayrıştırılamadı")
    return parametreler


def belge_parametreleri(metin: str, fm: str) -> set:
    """Belgedeki FM-IMZA bloğunda geçen parametre token'ları. Blok yoksa Olculemedi."""
    bas_etiket = _BLOK.format(fm=fm)
    i = metin.find(bas_etiket)
    if i < 0:
        raise Olculemedi(f"belgede `{bas_etiket}` imza bloğu YOK "
                         f"(bloksuz belge sessizce 'temiz' sayılamaz)")
    j = metin.find(_BLOK_SON, i)
    if j < 0:
        raise Olculemedi(f"`{bas_etiket}` açıldı ama `{_BLOK_SON}` ile KAPATILMADI")
    return set(_TOKEN.findall(metin[i + len(bas_etiket):j]))


def beyanlar() -> dict:
    """`fm_doc_sync_sources` → {kayıt-id: source_root-göreli yol}. Bozuk giriş Olculemedi."""
    from utils.project_config import cfg  # noqa: E402  (proje tarafı = kanonik API)
    ham = cfg(CONFIG_ANAHTARI)
    if ham in (None, "", []):
        return {}
    girdiler = ham.split(",") if isinstance(ham, str) else list(ham)
    out = {}
    for g in (x.strip() for x in girdiler):
        if not g:
            continue
        kid, ayrac, yol = g.partition(":")
        if not ayrac or not kid.strip() or not yol.strip():
            raise Olculemedi(f"`{CONFIG_ANAHTARI}` girişi `<kayıt-id>:<yol>` biçiminde DEĞİL: {g!r}")
        out[kid.strip()] = yol.strip()
    return out


def kaynak_yolu(rel: str) -> Path:
    from utils.project_config import source_dir  # noqa: E402  (proje tarafı = kanonik API)
    return source_dir() / rel


def kayit_kos(kayit: Kayit, core: Path, beyan: dict) -> tuple:
    """(durum, satirlar) döner. durum ∈ {TEMİZ, BULGU, ATLANDI, ÖLÇÜLEMEDİ}."""
    out = []
    if kayit.id not in beyan:
        return ("ATLANDI", [f"  [SKIP] ATLANDI({kayit.id}): {kayit.fm} kaynağı bu projede beyan "
                            f"edilmemiş (`project.yaml` `{CONFIG_ANAHTARI}`) — imza↔kılavuz "
                            f"senkronu ÖLÇÜLMEDİ. Proje bu üreteci sağlıyorsa yolu beyan et."])
    src = kaynak_yolu(beyan[kayit.id])
    if not src.is_file():
        return ("ÖLÇÜLEMEDİ", [f"  ÖLÇÜLEMEDİ({kayit.id}): `{CONFIG_ANAHTARI}` beyan ettiği "
                               f"kaynak YOK → {src} (beyan bayat ya da yol yanlış)"])
    try:
        imza = imza_parametreleri(src.read_text(encoding="utf-8", errors="replace"), kayit.fm)
        # ÇAPA: ayrıştırma sessizce yarım kalırsa (biçim değişimi) sonuç 'temiz' görünürdü.
        if kayit.capa.upper() not in imza:
            raise Olculemedi(f"çapa parametresi {kayit.capa} imzada bulunamadı "
                             f"(ayrıştırma yarım kalmış olabilir; bulunanlar: {sorted(imza)})")
    except Olculemedi as e:
        return ("ÖLÇÜLEMEDİ", [f"  ÖLÇÜLEMEDİ({kayit.id}): kaynak — {e}"])

    bulgu = False
    for rel in kayit.belgeler:
        doc = core / rel
        if not doc.is_file():
            return ("ÖLÇÜLEMEDİ", [f"  ÖLÇÜLEMEDİ({kayit.id}): belge YOK → {doc}"])
        try:
            belgelenen = belge_parametreleri(doc.read_text(encoding="utf-8", errors="replace"),
                                             kayit.fm)
        except Olculemedi as e:
            return ("ÖLÇÜLEMEDİ", [f"  ÖLÇÜLEMEDİ({kayit.id}): {rel} — {e}"])

        eksik = sorted(imza - belgelenen)
        hayalet = sorted(belgelenen - imza)
        if eksik:
            bulgu = True
            out.append(f"  EKSİK  {rel}: imzada VAR, belgede YOK → {', '.join(eksik)}")
        if hayalet:
            bulgu = True
            out.append(f"  HAYALET {rel}: belgede VAR, imzada YOK → {', '.join(hayalet)}")
        if not eksik and not hayalet:
            out.append(f"  OK     {rel}: {len(imza)} parametrenin tamamı belgeli")
    return ("BULGU" if bulgu else "TEMİZ", out)


# --- selftest (gömülü kırmızı fixture) ---------------------------------------
_SELFTEST_ABAP = """FUNCTION zselftest_fm_ornek
  IMPORTING
    VALUE(iv_bir) TYPE char10
    VALUE(iv_iki) TYPE char10 DEFAULT 'X'
  EXPORTING
    VALUE(ev_rc) TYPE i
  TABLES
    it_uc TYPE ztt_ornek OPTIONAL.
  WRITE iv_bir.
ENDFUNCTION.
"""


def selftest() -> int:
    kirli = ("<!-- FM-IMZA: ZSELFTEST_FM_ORNEK -->\n| `IV_BIR` | ... |\n"
             "| `IV_ESKI` | kaldırılmış |\n<!-- /FM-IMZA -->\n"
             "Blok DIŞI: `IS_LAYOUT` / `IT_OUTTAB` sayılmamalı.\n")
    imza = imza_parametreleri(_SELFTEST_ABAP, "zselftest_fm_ornek")
    belg = belge_parametreleri(kirli, "ZSELFTEST_FM_ORNEK")
    eksik, hayalet = imza - belg, belg - imza
    sorun = []
    if imza != {"IV_BIR", "IV_IKI", "EV_RC", "IT_UC"}:
        sorun.append(f"imza ayrıştırma HATALI: {sorted(imza)}")
    if eksik != {"IV_IKI", "EV_RC", "IT_UC"}:
        sorun.append(f"EKSİK sınıfı yakalanmadı: {sorted(eksik)}")
    if hayalet != {"IV_ESKI"}:
        sorun.append(f"HAYALET sınıfı yakalanmadı: {sorted(hayalet)}")
    if "IS_LAYOUT" in belg or "IT_OUTTAB" in belg:
        sorun.append("blok DIŞI token sayıldı (FP)")
    try:
        belge_parametreleri("bloksuz belge", "ZSELFTEST_FM_ORNEK")
        sorun.append("bloksuz belge ÖLÇÜLEMEDİ vermedi (fail-open)")
    except Olculemedi:
        pass
    if sorun:
        print("[SELFTEST FAIL]\n  " + "\n  ".join(sorun), file=sys.stderr)
        return 1
    print("[SELFTEST OK] imza ayrıştırma + EKSİK + HAYALET + blok-sınırı + fail-closed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="FM imzası ↔ kılavuz senkron kontrolü")
    ap.add_argument("--bulguda-exit1", action="store_true",
                    help="bulgu varsa exit 1 (hook/CI tüketicisi için)")
    ap.add_argument("--strict", action="store_true",
                    help="BİLEREK NO-OP (run_all --strict kazara terfi ettirmesin)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--kayit", help="yalnız bu kayıt")
    ap.add_argument("--core", help="core kökü (yalnız fixture/sandbox için)")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    core = Path(a.core).resolve() if a.core else CORE_ROOT
    kayitlar = [k for k in KAYITLAR if not a.kayit or k.id == a.kayit]
    if not kayitlar:
        print(f"ÖLÇÜLEMEDİ: `--kayit {a.kayit}` diye bir kayıt yok "
              f"(mevcut: {', '.join(k.id for k in KAYITLAR)})", file=sys.stderr)
        return 2

    try:
        beyan = beyanlar()
    except Olculemedi as e:
        print(f"ÖLÇÜLEMEDİ: {e}", file=sys.stderr)
        return 2
    bilinmeyen = sorted(set(beyan) - {k.id for k in KAYITLAR})
    if bilinmeyen:
        print(f"ÖLÇÜLEMEDİ: `{CONFIG_ANAHTARI}` bilinmeyen kayıt-id taşıyor: {', '.join(bilinmeyen)} "
              f"(mevcut: {', '.join(k.id for k in KAYITLAR)})", file=sys.stderr)
        return 2

    bulgulu, olculemedi, atlanan, satirlar = [], [], [], []
    for k in kayitlar:
        durum, cikti = kayit_kos(k, core, beyan)
        satirlar += cikti
        if durum == "BULGU":
            bulgulu.append(k.id)
        elif durum == "ÖLÇÜLEMEDİ":
            olculemedi.append(k.id)
        elif durum == "ATLANDI":
            atlanan.append(k.id)

    for s in satirlar:
        print(s)

    if olculemedi:
        print(f"\nÖLÇÜLEMEDİ ({len(olculemedi)}): {', '.join(olculemedi)} — "
              f"bu 'temiz' DEĞİLDİR; belge/kaynak bağı kopuk.", file=sys.stderr)
        return 2
    if bulgulu:
        print(f"\nUYARI — {len(bulgulu)} üreteçte kılavuz↔imza sapması: {', '.join(bulgulu)}.\n"
              f"  Kılavuzun `<!-- FM-IMZA: ... -->` bloğunu KAYNAKTAN güncelle "
              f"(bayat kılavuz sessizce yanlış çağrı ürettirir).", file=sys.stderr)
        return 1 if a.bulguda_exit1 else 0
    if len(atlanan) == len(kayitlar):
        # Hiçbir kayıt ölçülmedi → "[OK] senkron" basmak sahte-yeşil olurdu.
        print(f"[SKIP] {len(kayitlar)} kaydın hiçbiri bu projede beyan edilmemiş — "
              f"KAPSAM SIFIR (ÖLÇÜLMEDİ, 'temiz' DEĞİL).")
        return 0
    print(f"[OK] {len(kayitlar) - len(atlanan)} kayıt: imza ↔ kılavuz senkron"
          + (f" · {len(atlanan)} kayıt beyan edilmemiş (ÖLÇÜLMEDİ)." if atlanan else "."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
