# -*- coding: utf-8 -*-
"""fm_imza_doc_sync — check_fm_signature_doc_sync.py KALICI KORPUSU (11 vektör, 5 mutasyon).

Neden bu korpus: gate'in iddiası iki YÖNLÜDÜR ve ikisi de kanıtlanmalı —
  (a) YAKALAMA : imza ↔ kılavuz sapması (EKSİK/HAYALET) ve ÖLÇÜLEMEDİ durumları,
  (b) SESSİZLİK: meşru belgeyi kirli göstermeme (blok DIŞI API token'ları, markdown
      biçim varyantları, farklı imza şekilleri).
Yalnız (a) test edilirse gate "her şeye kırmızı yanan" bir alarma dönüşür ve kapatılır;
yalnız (b) test edilirse hiçbir şey yakalamayan ölü bir gate de YEŞİL verir.

Her vektör KENDİ sandbox'ını kurar (geçici dizin: sahte proje kökü + sahte core kökü).
Gate GERÇEK dosyasından koşar (kopya/mock yok).

MUTASYON: gate kaynağının bir kopyası üzerinde TAM-EŞLEŞMELİ metin cerrahisi yapılır
(çapa metni bulunamazsa koşucu DURUR — sessiz no-op mutasyon = sahte YEŞİL).

Kullanım:
    python tests/fixtures/fm_imza_doc_sync/run.py            # 11 vektör
    python tests/fixtures/fm_imza_doc_sync/run.py --mutasyon-capa   (…-eksik/-hayalet/
                                                  -failopen/-blok)
⛔ KİP BİÇİMİ 2026-08-29'da DEĞİŞTİ (kayıt Q210) — ESKİ `--mutasyon <ad>` (iki argüman)
   KALDIRILDI. Gerekçe ÖLÇÜM: `tests/run_battery.py` kipleri kaynaktan keşfeder ve
   TEK-ARGÜMAN biçimini tanır; bu koşucu tek `"--mutasyon"` sabiti taşıdığı için batarya
   onu DEĞERSİZ çağırıyor, `sys.argv[i+1]` **IndexError** ile Traceback üretiyordu
   (ölçüldü: 34 koşucu / 108 kip taramasında ÇÖKEN 3 kipten biri). Süit yalnız TABANI
   koştuğu için bunu hiçbir kapı görmüyordu. Eski biçim artık `[KULLANIM]` + exit 1 verir
   (görünür RED; sessiz çökme DEĞİL).
⚠ Core AĞACININ DIŞINDA (staging) koşuluyorsa `utils.project_config` bulunabilmesi için
  PYTHONPATH=<gerçek core>/scripts verilmelidir; core içinde koşarken gerekmez.
"""
from __future__ import annotations

import os
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

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[2]
GATE = CORE / "scripts" / "validators" / "check_fm_signature_doc_sync.py"

# --- imza şekilleri ----------------------------------------------------------
# S1: kanonik şekil (VALUE(...) + TABLES) — ZSD000_FM_SCREEN_GEN'in bugünkü şekli.
S1 = """FUNCTION zsd000_fm_screen_gen
  IMPORTING
    VALUE(iv_program) TYPE scrhprog
    VALUE(iv_dynpro) TYPE scrfdynnr DEFAULT '0100'
    VALUE(iv_src_prog) TYPE scrhprog OPTIONAL
    VALUE(iv_cua_merge) TYPE char1 DEFAULT 'X'
  EXPORTING
    VALUE(ev_rc) TYPE i
  TABLES
    it_buttons TYPE zsd000_tt_screen_button OPTIONAL
    it_fields TYPE zsd000_tt_screen_field OPTIONAL.
  CLEAR ev_rc.
ENDFUNCTION.
"""
# S2 (ÜÇÜNCÜ BAĞLAM): başka bir imza ŞEKLİ — REFERENCE(...), CHANGING bölümü,
#     imza içine serpilmiş yorum satırları, TABLES'sız, karışık harf düzeni.
S2 = """*&--- baslik yorumu
FUNCTION Zsd000_Fm_Screen_Gen
  IMPORTING
*   aciklama: hedef program
    REFERENCE(iv_program) TYPE scrhprog
    REFERENCE(IV_MODE) TYPE char10 DEFAULT 'WRITE'
  CHANGING
    REFERENCE(cv_sayac) TYPE i
  EXPORTING
    REFERENCE(ev_message) TYPE string.
ENDFUNCTION.
"""
# S3: FUNCTION satırı var ama ÇAPA (IV_PROGRAM) yok — biçim/ad değişimi sonrası
#     ayrıştırmanın YARIM kalması. "0 fark" = temiz DEĞİL, ölçülemedi olmalı.
S3 = """FUNCTION zsd000_fm_screen_gen
  IMPORTING
    VALUE(iv_prog) TYPE scrhprog
  EXPORTING
    VALUE(ev_rc) TYPE i.
ENDFUNCTION.
"""

B = "<!-- FM-IMZA: ZSD000_FM_SCREEN_GEN -->"
BS = "<!-- /FM-IMZA -->"

# --- belge şekilleri ---------------------------------------------------------
BLG_TAM = f"""# kılavuz
{B}
| Parametre | Anlam |
|---|---|
| `IV_PROGRAM` | hedef |
| `IV_DYNPRO` | ekran |
| `IV_SRC_PROG` | donör |
| `IV_CUA_MERGE` | merge |
| `EV_RC` | sonuç |
| `IT_BUTTONS` | butonlar |
| `IT_FIELDS` | alanlar |
{BS}
"""
BLG_EKSIK = f"""# kılavuz (2026-08-14 öncesi hâli)
{B}
| `IV_PROGRAM` | hedef |
| `IV_DYNPRO` | ekran |
| `EV_RC` | sonuç |
| `IT_BUTTONS` | butonlar |
| `IT_FIELDS` | alanlar |
{BS}
"""
BLG_HAYALET = BLG_TAM.replace(BS, "| `IV_ESKI_PARAM` | kaldırılmış |\n" + BS)
BLG_BLOKSUZ = "# kılavuz\n\n| `IV_PROGRAM` | hedef |\n| `IV_DYNPRO` | ekran |\n"
# FP çapası: blok DIŞINDA başka API'lerin parametreleri + küçük harf atıflar.
BLG_TAM_FP = BLG_TAM + """
```abap
go_grid->set_table_for_first_display(
  EXPORTING is_layout = gs_layout
  CHANGING it_outtab = gt_data it_fieldcatalog = gt_fcat ).
```
Ayrıca `IS_LAYOUT` / `IT_OUTTAB` / `IV_ESKI_BASKA_FM` yalnız ÖRNEK metindedir; `iv_program`
küçük harfle de anılır. Bunların HİÇBİRİ bu FM'in imzası DEĞİLDİR.
"""
# FP çapası: aynı token kümesi ama markdown biçim varyantlarıyla (bold/kod/başlık/düz).
BLG_TAM_BICIM = f"""# kılavuz
{B}
### IV_PROGRAM
**IV_DYNPRO** ve *IV_SRC_PROG*
`IV_CUA_MERGE` · EV_RC
<b>IT_BUTTONS</b>, IT_FIELDS.
{BS}
"""
# ÜÇÜNCÜ BAĞLAM belgesi (S2 imzasına karşılık)
BLG_S2 = f"""# kılavuz (başka şekil)
{B}
`IV_PROGRAM` `IV_MODE` `CV_SAYAC` `EV_MESSAGE`
{BS}
"""

REL_KAYNAK = "SD/ZSD000_CLC/functions/ZSD000_FM_SCREEN_GEN.func.abap"
REL_BELGE = ("playbook/howto-dynpro-gui-status-generation.md", "playbook/adt-fugr-functions.md")


def sandbox(tmp: Path, abap: str | None, belgeler: dict) -> tuple:
    """(proje_koku, core_koku) kurar. abap=None → kaynak dosyası HİÇ yaratılmaz."""
    proje = tmp / "proje"
    core = tmp / "core"
    (proje / "SOURCE_CODES" / "SD" / "ZSD000_CLC" / "functions").mkdir(parents=True)
    (proje / "project.yaml").write_text("sap_profile: s4_private\nsource_root: SOURCE_CODES\n",
                                        encoding="utf-8")
    if abap is not None:
        (proje / "SOURCE_CODES" / REL_KAYNAK).write_text(abap, encoding="utf-8")
    for rel, icerik in belgeler.items():
        p = core / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(icerik, encoding="utf-8")
    return proje, core


def kos(gate: Path, proje: Path, core: Path, ek: list) -> tuple:
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(proje), PYTHONIOENCODING="utf-8")
    yollar = [str(CORE / "scripts")]
    if os.environ.get("PYTHONPATH"):
        yollar.append(os.environ["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(yollar)
    r = subprocess.run([sys.executable, str(gate), "--core", str(core), *ek],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env, cwd=str(proje))
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# (ad, abap, belgeler, ek-argümanlar, beklenen-exit, çıktıda-OLMALI, çıktıda-OLMAMALI)
VEKTORLER = [
    ("V1 EKSİK yakalanır (asıl vaka: 4 yeni parametre belgeye yansımadı)",
     S1, {REL_BELGE[0]: BLG_EKSIK, REL_BELGE[1]: BLG_TAM}, [], 0, ["EKSİK", "IV_SRC_PROG", "IV_CUA_MERGE"], []),
    ("V2 EKSİK + --bulguda-exit1 → exit 1 (hook/CI tüketicisi)",
     S1, {REL_BELGE[0]: BLG_EKSIK, REL_BELGE[1]: BLG_TAM}, ["--bulguda-exit1"], 1, ["EKSİK"], []),
    ("V3 TEMİZ (tam belge) → exit 0, bulgu YOK",
     S1, {REL_BELGE[0]: BLG_TAM, REL_BELGE[1]: BLG_TAM}, [], 0, ["[OK]"], ["EKSİK", "HAYALET"]),
    ("V4 HAYALET yakalanır (belgede var, imzada yok)",
     S1, {REL_BELGE[0]: BLG_HAYALET, REL_BELGE[1]: BLG_TAM}, [], 0, ["HAYALET", "IV_ESKI_PARAM"], []),
    ("V5 İMZA BLOĞU YOK → ÖLÇÜLEMEDİ (exit 2), 'temiz' DEĞİL",
     S1, {REL_BELGE[0]: BLG_BLOKSUZ, REL_BELGE[1]: BLG_TAM}, [], 2, ["ÖLÇÜLEMEDİ", "imza bloğu YOK"], ["[OK]"]),
    ("V6 BELGE DOSYASI YOK → ÖLÇÜLEMEDİ (exit 2)",
     S1, {REL_BELGE[1]: BLG_TAM}, [], 2, ["ÖLÇÜLEMEDİ", "belge YOK"], ["[OK]"]),
    ("V7 ABAP KAYNAĞI YOK → ATLANDI + sebep (exit 0; başka projede kayıt yok)",
     None, {REL_BELGE[0]: BLG_TAM, REL_BELGE[1]: BLG_TAM}, [], 0, ["ATLANDI", "bu projede YOK"], ["EKSİK"]),
    ("V8 ÇAPA DÜŞTÜ (IV_PROGRAM yok) → ÖLÇÜLEMEDİ, sahte-temiz DEĞİL",
     S3, {REL_BELGE[0]: BLG_TAM, REL_BELGE[1]: BLG_TAM}, [], 2, ["ÖLÇÜLEMEDİ", "çapa"], ["[OK]"]),
    ("V9 FP ÇAPASI — blok DIŞI API token'ları (IS_LAYOUT/IT_OUTTAB) HAYALET sayılmaz",
     S1, {REL_BELGE[0]: BLG_TAM_FP, REL_BELGE[1]: BLG_TAM}, [], 0, ["[OK]"], ["HAYALET", "IS_LAYOUT"]),
    ("V10 FP ÇAPASI — markdown biçim varyantları (bold/kod/başlık/HTML) belgeli sayılır",
     S1, {REL_BELGE[0]: BLG_TAM_BICIM, REL_BELGE[1]: BLG_TAM}, [], 0, ["[OK]"], ["EKSİK"]),
    ("V11 ÜÇÜNCÜ BAĞLAM — REFERENCE/CHANGING/yorumlu/karışık-harf imza doğru ayrıştırılır",
     S2, {REL_BELGE[0]: BLG_S2, REL_BELGE[1]: BLG_S2}, [], 0, ["[OK]"], ["EKSİK", "HAYALET"]),
]

# çapa-metni → değişim (TAM eşleşme; bulunamazsa koşucu DURUR)
MUTASYONLAR = {
    "capa": ("        if kayit.capa.upper() not in imza:",
             "        if False:"),
    "eksik": ("        eksik = sorted(imza - belgelenen)",
              "        eksik = []"),
    "hayalet": ("        hayalet = sorted(belgelenen - imza)",
                "        hayalet = []"),
    "failopen": ('        raise Olculemedi(f"belgede `{bas_etiket}` imza bloğu YOK "\n'
                 '                         f"(bloksuz belge sessizce \'temiz\' sayılamaz)")',
                 "        return set(_TOKEN.findall(metin))"),
    "blok": ("    return set(_TOKEN.findall(metin[i + len(bas_etiket):j]))",
             "    return set(_TOKEN.findall(metin))"),
}


# Batarya keşfinin BEYAN katmanı bu literali okur (ad-bağımsız: elemanlarının HEPSİ kip).
# ⛔ `MUTASYONLAR` sözlüğünün anahtarları çıplak addır (`capa`) ⇒ keşif onları GÖREMEZ;
# bu yüzden kipler AYRICA tam biçimleriyle burada BEYAN edilir. İkisi ayrışmasın diye
# `_kip_capasi()` eşliği koşum başında ölçer (bayatlarsa görünür duruş, sessiz değil).
GECERLI_KIP = {"--mutasyon-capa", "--mutasyon-eksik", "--mutasyon-hayalet",
               "--mutasyon-failopen", "--mutasyon-blok"}


def _kip_capasi() -> None:
    """BEYAN ↔ uygulama eşliği: biri güncellenip diğeri unutulursa GÖRÜNÜR duruş."""
    beklenen = {"--mutasyon-" + k for k in MUTASYONLAR}
    if beklenen != GECERLI_KIP:
        print(f"[DURDU] kip beyanı ile MUTASYONLAR sözlüğü ayrıştı: "
              f"yalnız-beyanda={sorted(GECERLI_KIP - beklenen)} "
              f"yalnız-sözlükte={sorted(beklenen - GECERLI_KIP)} — SAYI RAPORLAMIYORUM.",
              file=sys.stderr)
        sys.exit(2)


def mutasyonlu_gate(tmp: Path, ad: str) -> Path:
    capa, yeni = MUTASYONLAR[ad]
    kaynak = GATE.read_text(encoding="utf-8")
    if kaynak.count(capa) != 1:
        print(f"[DUR] mutasyon '{ad}' çapası kaynakta {kaynak.count(capa)} kez geçiyor "
              f"(1 olmalı) — sessiz no-op mutasyon sahte YEŞİL üretirdi.", file=sys.stderr)
        sys.exit(3)
    hedef = tmp / "mut_gate.py"
    hedef.write_text(kaynak.replace(capa, yeni), encoding="utf-8")
    return hedef


def main() -> int:
    _kip_capasi()
    mut = None
    for a in sys.argv[1:]:
        if not a.startswith("--mutasyon"):
            continue
        if a not in GECERLI_KIP:
            # ⛔ SESSİZ ÇÖKME YERİNE GÖRÜNÜR RED: eski `--mutasyon <ad>` biçimi de,
            # yazım hatası da, bilinmeyen kip de AYNI kapıdan çıkar (kayıt Q210).
            print(f"[KULLANIM] gecersiz mutasyon kipi: {a} — gecerli: "
                  f"{', '.join(sorted(GECERLI_KIP))}. "
                  "ESKI bicim `--mutasyon <ad>` KALDIRILDI (tek argüman kullanın).",
                  file=sys.stderr)
            return 1
        mut = a[len("--mutasyon-"):]
    if not GATE.is_file():
        print(f"[DUR] gate bulunamadı: {GATE}", file=sys.stderr)
        return 3

    gecen, dusen = 0, []
    for ad, abap, belgeler, ek, beklenen, olmali, olmamali in VEKTORLER:
        tmp = Path(tempfile.mkdtemp(prefix="fmimza_"))
        try:
            gate = mutasyonlu_gate(tmp, mut) if mut else GATE
            proje, core = sandbox(tmp, abap, belgeler)
            rc, cikti = kos(gate, proje, core, ek)
            sorun = []
            if rc != beklenen:
                sorun.append(f"exit {rc} ≠ {beklenen}")
            for t in olmali:
                if t not in cikti:
                    sorun.append(f"çıktıda YOK: {t!r}")
            for t in olmamali:
                if t in cikti:
                    sorun.append(f"çıktıda OLMAMALIYDI: {t!r}")
            if sorun:
                dusen.append((ad, "; ".join(sorun), cikti.strip()[:300]))
            else:
                gecen += 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    baslik = f"fm_imza_doc_sync — {gecen}/{len(VEKTORLER)}" + (f" [mutasyon: {mut}]" if mut else "")
    print(baslik)
    for ad, sorun, cikti in dusen:
        print(f"  DÜŞTÜ: {ad}\n         {sorun}\n         çıktı: {cikti}")
    if mut:
        # Mutasyonlu koşumda EN AZ BİR vektör DÜŞMELİ; hepsi geçerse korpus o değişmezi
        # sınamıyor demektir (mutasyon testinin varlık sebebi).
        if not dusen:
            print("  [KORPUS ZAYIF] mutasyona rağmen 10/10 — bu değişmez sınanmıyor!",
                  file=sys.stderr)
            return 1
        return 0
    return 0 if not dusen else 1


if __name__ == "__main__":
    raise SystemExit(main())
