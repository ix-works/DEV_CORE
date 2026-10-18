# -*- coding: utf-8 -*-
"""fm_imza_doc_sync — check_fm_signature_doc_sync.py KALICI KORPUSU (20 vektör, 11 mutasyon).

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
CORE-07 (2026-10-18 delta kapısı turu): çapa TAM 1 kez eşleşmeli · mutant DERLENMELİ
(`compile`) · her kipin DÜŞMESİ BEKLENEN vektör kümesi `_BEKLENEN_DUSEN`'de pinlidir ve
EŞİTLİKLE kıyaslanır. Önceden yalnız "en az bir vektör düştü mü" bakılıyordu ⇒ sözdizimi
bozuk bir mutant (her vektörü düşürür) "yakalandı" sayılıyordu.
ÇIKIŞ: 0 taban yeşil · 1 taban düşen VAR ya da mutasyon BEKLENEN kümeyle düştü ·
2 SAPMA (düşen küme ≠ beklenen) / kip beyanı ayrıştı · 3 DOGRULANAMADI (çapa ≠1 kez ·
mutant derlenmedi — "düştü" SAYILMAZ).

Kullanım:
    python tests/fixtures/fm_imza_doc_sync/run.py            # 20 vektör
    python tests/fixtures/fm_imza_doc_sync/run.py --mutasyon-capa   (…-eksik/-hayalet/
                                                  -failopen/-blok/-sabityol/-skipok/
                                                  -bosenv/-ciftid/-ayracenv/-gerekce)
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


# Kaynak yolu 2026-10-18'den beri PROJE beyanıdır (`fm_doc_sync_sources`); varsayılan
# sandbox beyanı TAŞIR. Seçenekler (vektörün 8. alanı, isteğe bağlı):
#   beyan : project.yaml'a eklenecek HAM metin (None → anahtar HİÇ yazılmaz)
#   sroot : source_root adı · rel : kaynağın source_root-göreli yolu
#   env   : IX_FM_DOC_SYNC_SOURCES değeri (None → env'de HİÇ yok; "" → boş tanımlı)
VARSAYILAN = {"beyan": f'fm_doc_sync_sources: ["screen_gen:{REL_KAYNAK}"]',
              "sroot": "SOURCE_CODES", "rel": REL_KAYNAK, "env": None}


def sandbox(tmp: Path, abap: str | None, belgeler: dict, sec: dict | None = None) -> tuple:
    """(proje_koku, core_koku) kurar. abap=None → kaynak dosyası HİÇ yaratılmaz."""
    o = dict(VARSAYILAN, **(sec or {}))
    proje = tmp / "proje"
    core = tmp / "core"
    kaynak = proje / o["sroot"] / o["rel"]
    kaynak.parent.mkdir(parents=True)
    yaml = f"sap_profile: s4_private\nsource_root: {o['sroot']}\n"
    if o["beyan"] is not None:
        yaml += o["beyan"] + "\n"
    (proje / "project.yaml").write_text(yaml, encoding="utf-8")
    if abap is not None:
        kaynak.write_text(abap, encoding="utf-8")
    for rel, icerik in belgeler.items():
        p = core / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(icerik, encoding="utf-8")
    return proje, core


def kos(gate: Path, proje: Path, core: Path, ek: list, env_beyan: str | None = None) -> tuple:
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(proje), PYTHONIOENCODING="utf-8")
    for k in ("IX_SOURCE_ROOT", "IX_FM_DOC_SYNC_SOURCES"):
        env.pop(k, None)              # çevre config'ini miras alma (yokluk vektörü dersi)
    if env_beyan is not None:
        env["IX_FM_DOC_SYNC_SOURCES"] = env_beyan
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
    ("V7 BEYAN VAR, ABAP KAYNAĞI YOK → ÖLÇÜLEMEDİ (exit 2; bağ kopuk, 'üreteç yok' DEĞİL)",
     None, {REL_BELGE[0]: BLG_TAM, REL_BELGE[1]: BLG_TAM}, [], 2,
     ["ÖLÇÜLEMEDİ", "beyan ettiği kaynak YOK"], ["EKSİK", "[OK]"]),
    ("V8 ÇAPA DÜŞTÜ (IV_PROGRAM yok) → ÖLÇÜLEMEDİ, sahte-temiz DEĞİL",
     S3, {REL_BELGE[0]: BLG_TAM, REL_BELGE[1]: BLG_TAM}, [], 2, ["ÖLÇÜLEMEDİ", "çapa"], ["[OK]"]),
    ("V9 FP ÇAPASI — blok DIŞI API token'ları (IS_LAYOUT/IT_OUTTAB) HAYALET sayılmaz",
     S1, {REL_BELGE[0]: BLG_TAM_FP, REL_BELGE[1]: BLG_TAM}, [], 0, ["[OK]"], ["HAYALET", "IS_LAYOUT"]),
    ("V10 FP ÇAPASI — markdown biçim varyantları (bold/kod/başlık/HTML) belgeli sayılır",
     S1, {REL_BELGE[0]: BLG_TAM_BICIM, REL_BELGE[1]: BLG_TAM}, [], 0, ["[OK]"], ["EKSİK"]),
    ("V11 ÜÇÜNCÜ BAĞLAM — REFERENCE/CHANGING/yorumlu/karışık-harf imza doğru ayrıştırılır",
     S2, {REL_BELGE[0]: BLG_S2, REL_BELGE[1]: BLG_S2}, [], 0, ["[OK]"], ["EKSİK", "HAYALET"]),
    # ── 2026-10-18: kaynak yolu PROJE beyanı (ters yön kablolama kaldırıldı) ──
    ("V12 BEYAN YOK → görünür [SKIP] ATLANDI + KAPSAM SIFIR, exit 0, '[OK]' YOK",
     S1, {REL_BELGE[0]: BLG_TAM, REL_BELGE[1]: BLG_TAM}, [], 0,
     ["[SKIP] ATLANDI", "ÖLÇÜLMEDİ", "KAPSAM SIFIR",
      "env `IX_FM_DOC_SYNC_SOURCES` tanımsız", "`project.yaml` `fm_doc_sync_sources` yok/boş"],
     ["[OK]", "EKSİK", "boş/tanımsız"], {"beyan": None}),
    ("V13 BOZUK BEYAN (`:` yok) → ÖLÇÜLEMEDİ exit 2",
     S1, {REL_BELGE[0]: BLG_TAM, REL_BELGE[1]: BLG_TAM}, [], 2,
     ["ÖLÇÜLEMEDİ", "biçiminde DEĞİL"], ["[OK]"],
     {"beyan": f'fm_doc_sync_sources: ["{REL_KAYNAK}"]'}),
    ("V14 BİLİNMEYEN KAYIT-ID → ÖLÇÜLEMEDİ exit 2 (yazım hatası sessiz SKIP olmasın)",
     S1, {REL_BELGE[0]: BLG_TAM, REL_BELGE[1]: BLG_TAM}, [], 2,
     ["ÖLÇÜLEMEDİ", "bilinmeyen kayıt-id", "scren_gen"], ["[OK]"],
     {"beyan": f'fm_doc_sync_sources: ["scren_gen:{REL_KAYNAK}"]'}),
    ("V15 ÜÇÜNCÜ BAĞLAM — başka source_root + başka modül/paket yolu, blok-liste beyanı → ölçülür",
     S1, {REL_BELGE[0]: BLG_TAM, REL_BELGE[1]: BLG_TAM}, [], 0, ["[OK] 1 kayıt"], ["[SKIP]", "EKSİK"],
     {"sroot": "ABAP_SRC", "rel": "MM/ZMM001_CLC/functions/ZMM001_FM_EKRAN.func.abap",
      "beyan": "fm_doc_sync_sources:\n  - screen_gen:MM/ZMM001_CLC/functions/ZMM001_FM_EKRAN.func.abap"}),
    # ── 2026-10-18 bug-gate düzeltme turu (F8) ──
    ("V16 BOŞ ENV (`IX_FM_DOC_SYNC_SOURCES=\"\"`) yaml beyanını EZMEZ → ölçülür, kaynak=project.yaml",
     S1, {REL_BELGE[0]: BLG_TAM, REL_BELGE[1]: BLG_TAM}, [], 0,
     ["[OK] 1 kayıt", "beyan: project.yaml"], ["[SKIP]", "env IX_"], {"env": ""}),
    ("V17 DOLU ENV yaml'ı ezer (kontrol) → ölçülür, kaynak=env",
     S1, {REL_BELGE[0]: BLG_TAM, REL_BELGE[1]: BLG_TAM}, [], 0,
     ["[OK] 1 kayıt", "beyan: env IX_FM_DOC_SYNC_SOURCES"], ["[SKIP]", "ÖLÇÜLEMEDİ"],
     {"beyan": 'fm_doc_sync_sources: ["screen_gen:YOK/olmayan.func.abap"]',
      "env": f"screen_gen:{REL_KAYNAK}"}),
    ("V18 AYNI KAYIT-ID İKİ KEZ → ÖLÇÜLEMEDİ exit 2 (sonuncusu sessizce kazanmaz)",
     S1, {REL_BELGE[0]: BLG_TAM, REL_BELGE[1]: BLG_TAM}, [], 2,
     ["ÖLÇÜLEMEDİ", "iki kez", "screen_gen"], ["[OK]"],
     {"beyan": f'fm_doc_sync_sources: ["screen_gen:YOK/olmayan.func.abap", "screen_gen:{REL_KAYNAK}"]'}),
    # ── 2026-10-18 delta kapısı turu (Y2): "boş" kararı env AYRIŞTIRILDIKTAN sonra ──
    ("V19 YALNIZ AYRAÇ ENV (`IX_FM_DOC_SYNC_SOURCES=,`) yaml beyanını EZMEZ → ölçülür, kaynak=project.yaml",
     S1, {REL_BELGE[0]: BLG_TAM, REL_BELGE[1]: BLG_TAM}, [], 0,
     ["[OK] 1 kayıt", "beyan: project.yaml"], ["[SKIP]", "env IX_", "ÖLÇÜLEMEDİ"], {"env": ","}),
    ("V20 AYRAÇ/BOŞLUK ENV + yaml beyanı YOK → [SKIP] gerekçesi GERÇEKTEN bakılan iki kaynağı söyler",
     S1, {REL_BELGE[0]: BLG_TAM, REL_BELGE[1]: BLG_TAM}, [], 0,
     ["[SKIP] ATLANDI", "KAPSAM SIFIR",
      "env `IX_FM_DOC_SYNC_SOURCES` tanımlı ama geçerli giriş yok (değer: ' , ')",
      "`project.yaml` `fm_doc_sync_sources` yok/boş"],
     ["[OK]", "boş/tanımsız", "beyanında bu kayıt yok"], {"beyan": None, "env": " , "}),
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
    # 2026-10-18: sabit yola dönüş (eski ters-yön kablolama) V15'te yakalanmalı
    "sabityol": ("    src = kaynak_yolu(beyan[kayit.id])",
                 '    src = kaynak_yolu("SD/ZSD000_CLC/functions/ZSD000_FM_SCREEN_GEN.func.abap")'),
    # hiçbir kayıt ölçülmediğinde "[OK] senkron" basmak sahte-yeşil — V12'de yakalanmalı
    "skipok": ("    if len(atlanan) == len(kayitlar):", "    if False:"),
    # F8①: tanımlı her env (boş da) yaml'ı ezer (eski `cfg` davranışı) → V16 V19 V20
    "bosenv": ("        if out:\n            return out, kaynak, bakilan\n",
               "        if True:\n            return out, kaynak, bakilan\n"),
    # Y2: "boş" kararı AYRIŞTIRMADAN ÖNCE (`strip()`) verilir — eski kodun birebir hâli:
    # `""` yaml'a düşer (V16 geçer) ama `","` yaml'ı ezer → V19 V20
    "ayracenv": ("        if out:\n            return out, kaynak, bakilan\n",
                 "        if out or env.strip():\n            return out, kaynak, bakilan\n"),
    # Y2: [SKIP] gerekçesi eski sabit metne döner (bakılan kaynakları söylemez) → V12 V20
    "gerekce": ('"beyan yok: " + " · ".join(bakilan or ["bakılan kaynak bildirilmedi"])',
                'f"beyan yok: env `{ENV_ANAHTARI}` boş/tanımsız · `project.yaml` "'
                '                  f"`{CONFIG_ANAHTARI}` yok"'),
    # F8②: çift kayıt-id kontrolü kalkar (sonuncu kazanır) → V18
    "ciftid": ("        if kid.strip() in out:", "        if False:"),
}


# Batarya keşfinin BEYAN katmanı bu literali okur (ad-bağımsız: elemanlarının HEPSİ kip).
# ⛔ `MUTASYONLAR` sözlüğünün anahtarları çıplak addır (`capa`) ⇒ keşif onları GÖREMEZ;
# bu yüzden kipler AYRICA tam biçimleriyle burada BEYAN edilir. İkisi ayrışmasın diye
# `_kip_capasi()` eşliği koşum başında ölçer (bayatlarsa görünür duruş, sessiz değil).
GECERLI_KIP = {"--mutasyon-capa", "--mutasyon-eksik", "--mutasyon-hayalet",
               "--mutasyon-failopen", "--mutasyon-blok", "--mutasyon-sabityol",
               "--mutasyon-skipok", "--mutasyon-bosenv", "--mutasyon-ciftid",
               "--mutasyon-ayracenv", "--mutasyon-gerekce"}

# CORE-07: her kipin DÜŞMESİ BEKLENEN vektör kümesi (ölçüldü 2026-10-18; EŞİTLİKLE kıyaslanır).
# Küme değişirse ÖLÇÜLEN yeni küme yazılır — "en az biri düştü" kabul DEĞİLDİR.
_BEKLENEN_DUSEN = {
    "capa": {"V8"},
    "eksik": {"V1", "V2"},
    "hayalet": {"V4"},
    "failopen": {"V5"},
    "blok": {"V9"},
    "sabityol": {"V15"},
    "skipok": {"V12", "V20"},
    "bosenv": {"V16", "V19", "V20"},
    "ciftid": {"V18"},
    "ayracenv": {"V19", "V20"},
    "gerekce": {"V12", "V20"},
}


def _kip_capasi() -> None:
    """BEYAN ↔ uygulama eşliği: biri güncellenip diğeri unutulursa GÖRÜNÜR duruş."""
    beklenen = {"--mutasyon-" + k for k in MUTASYONLAR}
    if beklenen != GECERLI_KIP:
        print(f"[DURDU] kip beyanı ile MUTASYONLAR sözlüğü ayrıştı: "
              f"yalnız-beyanda={sorted(GECERLI_KIP - beklenen)} "
              f"yalnız-sözlükte={sorted(beklenen - GECERLI_KIP)} — SAYI RAPORLAMIYORUM.",
              file=sys.stderr)
        sys.exit(2)
    if set(_BEKLENEN_DUSEN) != set(MUTASYONLAR):
        print(f"[DURDU] _BEKLENEN_DUSEN ile MUTASYONLAR ayrıştı: "
              f"yalnız-beklenende={sorted(set(_BEKLENEN_DUSEN) - set(MUTASYONLAR))} "
              f"yalnız-sözlükte={sorted(set(MUTASYONLAR) - set(_BEKLENEN_DUSEN))}",
              file=sys.stderr)
        sys.exit(2)


def mutant_kaynagi(ad: str) -> str:
    """Mutant metni — çapa TAM 1 kez + mutant DERLENİR; değilse exit 3 (sayı basılmaz)."""
    capa, yeni = MUTASYONLAR[ad]
    kaynak = GATE.read_text(encoding="utf-8")
    if kaynak.count(capa) != 1:
        print(f"[DOGRULANAMADI] mutasyon '{ad}' çapası kaynakta {kaynak.count(capa)} kez "
              f"geçiyor (1 olmalı) — sessiz no-op mutasyon sahte YEŞİL üretirdi.", file=sys.stderr)
        sys.exit(3)
    mutant = kaynak.replace(capa, yeni, 1)
    try:
        compile(mutant, str(GATE), "exec")
    except SyntaxError as e:
        print(f"[DOGRULANAMADI] mutant '{ad}' DERLENMEDİ ({e}) — her vektörü düşüren bozuk "
              f"kaynak 'yakalandı' SAYILMAZ; hiçbir sayı raporlanmadı.", file=sys.stderr)
        sys.exit(3)
    return mutant


def mutasyonlu_gate(tmp: Path, mutant: str) -> Path:
    hedef = tmp / "mut_gate.py"
    hedef.write_text(mutant, encoding="utf-8")
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

    mutant = mutant_kaynagi(mut) if mut else None
    gecen, dusen = 0, []
    for ad, abap, belgeler, ek, beklenen, olmali, olmamali, *sec in VEKTORLER:
        tmp = Path(tempfile.mkdtemp(prefix="fmimza_"))
        try:
            gate = mutasyonlu_gate(tmp, mutant) if mutant is not None else GATE
            o = sec[0] if sec else {}
            proje, core = sandbox(tmp, abap, belgeler, o)
            rc, cikti = kos(gate, proje, core, ek, o.get("env"))
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
        # CORE-07: düşen küme BEKLENEN kümeye EŞİT olmalı ("en az biri düştü" yetmez:
        # yanlış yerdeki çapa ya da bağımlı vektörler başka bir şeyi düşürür).
        dusen_k = {ad.split()[0] for ad, _s, _c in dusen}
        beklenen_k = _BEKLENEN_DUSEN[mut]
        if not dusen:
            print(f"  [KORPUS ZAYIF] mutasyona rağmen {gecen}/{len(VEKTORLER)} — bu değişmez "
                  f"sınanmıyor!", file=sys.stderr)
        if dusen_k != beklenen_k:
            print(f"  [SAPMA] {mut}: beklenen={sorted(beklenen_k)} düşen={sorted(dusen_k)} "
                  f"fazla={sorted(dusen_k - beklenen_k)} eksik={sorted(beklenen_k - dusen_k)} "
                  f"→ exit 2")
            return 2
        print(f"  [BEKLENEN] {mut}: düşen küme = beklenen {sorted(beklenen_k)}")
        return 1
    return 0 if not dusen else 1


if __name__ == "__main__":
    raise SystemExit(main())
