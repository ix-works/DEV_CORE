#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""INTAKE MODUL-IPUCU / METODOLOJI SOZLUGU CARPISMASI (2026-08-21).

NEDEN BU KORPUS VAR
-------------------
`intake_triage._MODULES` PP regex'i `\\breçete`, QM regex'i `\\bkusur` tasiyordu.
Bu iki kelime bu evin **metodoloji sozlugudur**:
  · "recete" = playbook tarifi (`governance/infra-test-recipes.md` = TEST RECETELERI)
  · "kusur"  = defect / kusur-sinifi (infra-changelog · lessons-learned · bug-checklist)
Sonuc: bir infra turu konusuldugunda hook "muhtemel modul: PP/QM" diye YANLIS ipucu
veriyordu. Olculdu (3.048 GERCEK kullanici promptu, transcript korpusu):
  PP atesleme 141 -> 90 (51 dusen, hepsi infra duzyazisi)
  QM atesleme 218 ->  6 (212 dusen, hepsi infra duzyazisi)

⛔⛔ BU BIR DARALTMADIR -> KAPSAM KAYBI RISKI TASIR.
Bu yuzden korpusun POZITIF KONTROL bolumu (B*) **SILINEMEZ**: "artik ateslemiyor"
kanitI TEK BASINA YETMEZ; "gercek uretim/kalite talebini HALA yakaliyor" da
gosterilmelidir. `--mutasyon-asiri-dar` tam olarak bu borcu sinar.

KOSUM:  python tests/fixtures/intake_modul_carpismasi/run.py
        ... --mutasyon-pp-geri     (PP: cok-kelimeli capa -> tek-kelimelik `\\brecete`)
        ... --mutasyon-qm-geri     (QM: cok-kelimeli capa -> tek-kelimelik `\\bkusur`)
        ... --mutasyon-asiri-dar   (SINIR: yeni capalar TUMDEN kaldirilir = kapsam kaybi)
        ... --mutasyon-bom-geri    (BOM: cok-kelimeli capa -> ciplak `\\bBOM\\b`)
        ... --mutasyon-kk-geri     (QM: cok-kelimeli capa -> ciplak `\\bkalite\\s+kontrol`)
        ... --mutasyon-agac-diyakritik (PP: `ürün ağac` YALNIZ diyakritikli hale doner)
Cikis:  0 hepsi beklendigi gibi · 1 sapma · 2 DOGRULANAMADI (mutasyon capasi tutmadi)

⚠ UC MUTASYON, HICBIRI DIGERINI KAPSAMAZ: ikisi FP-dususunu, ucuncusu POZITIF KONTROLU
  civilliyor. Ucuncusu olmadan daraltmanin "kapiyi korletmedigi" iddiasi KANITSIZ kalir.
⚠ Her vektor bir GELISTIRME-NIYETI kelimesi tasir ("ekleyelim"/"gelistir"/"yeni rapor").
  Tasimasa hook zaten sessiz kalirdi ve FP vektorleri TRIVIAL-YESIL olurdu.
"""
from __future__ import annotations

import json
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
REPO = HERE.parent.parent.parent
HOOK = REPO / "scripts" / "hooks" / "intake_triage.py"

PP_MK = "PP (Üretim Planlama)"
QM_MK = "QM (Kalite Yönetimi)"
ITG_MK = "INTAKE TRIAGE GATE"

# --- mutasyon capalari (ICERIK capasi; taban SHA DEGIL) ----------------------
PP_YENI = (r'        r"\b[üu]retim\s+re[çc]ete|\b[üu]r[üu]n\s+re[çc]ete|'
           r'\bre[çc]ete\s+(?:kalem|bile[şs]en|y[öo]net)|"' + "\n"
           r'        r"\bmaster\s+recipe|"')
QM_YENI = (r'        r"\bkalite\s+kusur|\bkusur\s+(?:bildirim|kod|oran)|'
           r'\b[üu]r[üu]n\s+kusur|\bmalzeme\s+kusur|"' + "\n"
           r'        r"\bdefect\s+code|"')

# --- 2026-08-22 IKINCI DALGA: `\bBOM\b` + `\bkalite\s+kontrol` daraltmasi -----
# ⚠ NEDEN AYRI CAPALAR (ve neden ustteki ikisi YETMEZ): 21.08 turu `reçete`/`kusur`
# kancalarini daraltti ama PP/QM'de KALAN atesLEMELERIN cogunlugu baska iki kelimeden
# geliyordu. Fix ESKI daraltmayi KORUYUP yenisini EKLEDIGI icin `--mutasyon-pp-geri` /
# `--mutasyon-qm-geri` bu yeni davranisi HIC sinamaz (sinif: "iki degismez -> iki
# mutasyon"). Bu yuzden yeni kancalarin KENDI mutasyonlari var.
BOM_YENI = (r'        r"\b[üu]retim\s+BOM|\bBOM\s+(?:patlat|bile[şs]en|kalem|listesi|'
            r'a[ğg]ac|yap[ıi]s)|"' + "\n"
            r'        r"\bbill\s+of\s+material|\bCS0\d|\bSTPO\b|\bSTKO\b|"')
KK_YENI = (r'        r"\bkalite\s+kontrol\s+(?:lot|plan|karar|sonu[çc]|noktas|'
           r'[öo]l[çc][üu]m|karakteristi)|"')

# --- 2026-08-22 UCUNCU DALGA: `ürün ağac` diyakritik-bağımlılığı (N6) -----------
# ⚠ BU DALGA ÖNCEKİLERİN TERSİDİR: önceki ikisi DARALTMA idi, bu GENİŞLETME.
# `\bürün\s+ağac` yalnız diyakritikli yazımı yakalıyordu; ASCII yazan kullanıcı
# KAÇIYORDU (ham prompt'ta da `_fold()`lanmışında da `ü` yok ⇒ çift arama kurtarmaz).
# ⛔ KENDİ MUTASYONU ŞART: mevcut mutasyonların HİÇBİRİ bu ayağı sinamaz
# (`--mutasyon-asiri-dar` PP_YENI'yi söker, bu ayak ONDAN AYRI bir satırdır) —
# sınıf: "iki değişmez -> iki mutasyon".
AGAC_YENI = r'        r"\b[üu]r[üu]n\s+a[ğg]ac|"'

MUTLAR = {
    # fix'in SOKUMU: tek-kelimelik kancaya geri don -> FP vektorleri dusmeli
    "--mutasyon-pp-geri": (PP_YENI, r'        r"\breçete|"'),
    "--mutasyon-qm-geri": (QM_YENI, r'        r"\bkusur|"'),
    # SINIR: yeni capalar TUMDEN kaldirilir -> POZITIF KONTROL vektorleri dusmeli
    # ⚠ Yer-tutucu ASLA-ESLESMEYEN bir token olmali. Ilk denemede `r"|"` yazildi: bu
    # BOS ALTERNATIF uretir, regex HER SEYE eslesir ve mutasyon "asiri-dar" degil
    # "asiri-genis" olur (olcum tersine doner). Kendi kosucusunu okumayan mutasyon
    # olcmez -- bu satir o hatanin kalici kaydidir.
    "--mutasyon-asiri-dar": (PP_YENI, r'        r"ZZZ_ASLA_ESLESMEZ_MUT|"'),
    # 2026-08-22 dalgasinin fix-SOKUMLERI (yeni kancalar tek-kelimelige geri doner)
    "--mutasyon-bom-geri": (BOM_YENI, r'        r"\bBOM\b|"'),
    "--mutasyon-kk-geri": (KK_YENI, r'        r"\bkalite\s+kontrol|"'),
    # N6 fix'in SOKUMU: diyakritik-BAGIMLI hale geri don -> B9b (ASCII) duser,
    # B9 (diyakritikli) PASS kalir. Ikisinin AYRI dusmesi, iki yazimin AYRI
    # olculdugunun kanitidir (tek vektor olsaydi hangi yazimin tuttugu bilinmezdi).
    "--mutasyon-agac-diyakritik": (AGAC_YENI, r'        r"\bürün\s+ağac|"'),
}


def kos(hook: Path, proje: Path, prompt: str):
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(proje)
    env["PYTHONIOENCODING"] = "utf-8"
    girdi = json.dumps({"prompt": prompt}, ensure_ascii=False).encode("utf-8")
    p = subprocess.run([sys.executable, str(hook)], input=girdi, env=env,
                       capture_output=True, cwd=str(proje), timeout=120)
    out = p.stdout.decode("utf-8", "replace")
    try:
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    except Exception:
        ctx = ""
    return p.returncode, ctx


def main() -> int:
    # BILINMEYEN KIP SESSIZCE YESIL GECMESIN (2026-08-22): `--mutasyon-ZIRVA` gibi bir
    # yazim hatasi `secili` bos biraktigi icin HIC mutasyon kurmadan TAM PUAN uretiyordu
    # (exit 0) -- yani "mutasyon yakalandi" sanilan sonuc aslinda mutasyonsuz kosumdu.
    for a in sys.argv[1:]:
        if a.startswith("--mutasyon") and a not in MUTLAR:
            raise SystemExit(f"[KULLANIM] bilinmeyen mutasyon kipi: {a} -> gecerli: "
                             + ", ".join(sorted(MUTLAR)))

    secili = [a for a in sys.argv[1:] if a in MUTLAR]
    hook = HOOK
    mutant = None
    if secili:
        kaynak = HOOK.read_text(encoding="utf-8")
        eski, yeni = MUTLAR[secili[0]]
        if eski not in kaynak:
            print(f"[DOGRULANAMADI] mutasyon capasi tabanda bulunamadi ({secili[0]}) -> "
                  "mutasyon uygulanmadi; 'gecti' sonucu ANLAMSIZ olurdu.")
            return 2
        yamali = kaynak.replace(eski, yeni, 1)
        if secili[0] == "--mutasyon-asiri-dar":
            # SINIR: HER dalganin yeni capalari TUMDEN kaldirilir -> B* pozitif kontrol
            # vektorleri dusmeli. 2026-08-22'de BOM/kalite-kontrol ayaklari EKLENDI:
            # eklenmeseydi B9-B12 hicbir mutasyonda dusmezdi = "kapsam korunuyor" iddiasi
            # KANITSIZ kalirdi (olculmus sinif: capasiz pozitif kontrol trivial-yesildir).
            for ayak, ad in ((QM_YENI, "QM"), (BOM_YENI, "BOM"), (KK_YENI, "kalite-kontrol")):
                if ayak not in yamali:
                    print(f"[DOGRULANAMADI] asiri-dar mutasyonunun {ad} ayagi tutmadi.")
                    return 2
                yamali = yamali.replace(ayak, r'        r"ZZZ_ASLA_ESLESMEZ_MUT|"', 1)
        hook = HOOK.with_name("_mutant_intake_triage.py")
        hook.write_text(yamali, encoding="utf-8")
        mutant = hook

    tmp = Path(tempfile.mkdtemp(prefix="intake_carp_"))
    sonuc: list[tuple[str, bool, str]] = []
    try:
        sb = tmp / "proje"
        (sb / ".claude").mkdir(parents=True, exist_ok=True)

        def ekle(ad, kosul, aciklama=""):
            sonuc.append((ad, bool(kosul), aciklama))

        # === A) FP CAPALARI — INFRA metni artik PP/QM ONERMEMELI ==========
        # ⚠ Her biri gelistirme-NIYETI tasir => hook ATESLER; sinanan sey modul IPUCUDUR.
        A = [
            # ⚠ A1/A2 DIYAKRITIKLI yazilir. Ilk taslakta ASCII ("recete") yazilmisti ve
            # `--mutasyon-pp-geri` altinda YINE PASS veriyorlardi: eski desen `\breçete`
            # diyakritik-bagimliydi, yani ASCII vektor fix-ONCESI de atesLEMEZDI = TRIVIAL
            # YESIL. Gercek korpusta olculen 51 FP'nin hepsi diyakritikli "reçete"dir.
            ("A1 'test reçetesi' (infra) -> PP ipucu YOK",
             "governance/infra-test-recipes.md içindeki reçeteyi bu gate'e de ekleyelim",
             PP_MK),
            ("A2 'reçetesiyle çözüldü' (infra düzyazı) -> PP ipucu YOK",
             "Bir 423 yaşandı, 12.7c reçetesiyle çözüldü; aynı reçeteyi playbook'a ekleyelim",
             PP_MK),
            ("A3 'kusur sinifi' (infra) -> QM ipucu YOK",
             "Ayni kusur sinifi diger eksenlerde de var; bunu duzeltelim ve gate ekleyelim",
             QM_MK),
            ("A4 'tasarim kusuru' (infra) -> QM ipucu YOK",
             "Bu bir tasarim kusuru mu? Oyleyse validator'e yeni bir kontrol ekleyelim",
             QM_MK),
            # --- 2026-08-22 dalgasi: `\bBOM\b` = Byte Order Mark, PP urun agaci DEGIL ---
            # Olculdu (iki depo x *.md): `\bBOM\b` 654 satirda atesliyor, 362'si acikca
            # encoding baglami. Bu vektor o FP sinifinin GERCEK yazim bicimidir.
            ("A5 'UTF-8 BOM' (encoding) -> PP ipucu YOK",
             "PowerShell dosyaya UTF-8 BOM ekliyor; bunu duzeltip yeni bir kontrol ekleyelim",
             PP_MK),
            ("A6 'kalite kontrol listesi' (belge/metodoloji) -> QM ipucu YOK",
             "Commit oncesi kalite kontrol listesi icin yeni bir madde ekleyelim",
             QM_MK),
        ]
        for ad, pr, mk in A:
            rc, ctx = kos(hook, sb, pr)
            ekle(ad, ITG_MK in ctx and mk not in ctx,
                 f"exit={rc}; ITG atesledi mi={ITG_MK in ctx} (atesmediyse vektor TRIVIAL)")

        # === B) POZITIF KONTROL — GERCEK PP/QM talebi HALA yakalanmali ====
        # ⛔⛔ SILINEMEZ. Daraltmanin kapiyi korletmedigi kaniti YALNIZ burasidir.
        B = [
            ("B1 POZ.KONTROL 'uretim recetesi' -> PP ipucu VAR",
             "Uretim recetesine yeni bir bilesen ekleyelim", PP_MK),
            ("B2 POZ.KONTROL 'urun recetesi' (diyakritikli) -> PP ipucu VAR",
             "Ürün reçetesi değişikliği için yeni bir ekran ekleyelim", PP_MK),
            ("B3 POZ.KONTROL 'recete kalemleri' -> PP ipucu VAR",
             "Recete kalemlerini excel'den yukleyecek bir ekran ekleyelim", PP_MK),
            ("B4 POZ.KONTROL 'master recipe' -> PP ipucu VAR",
             "Master recipe alanlarini listeleyen yeni rapor gelistirelim", PP_MK),
            ("B5 POZ.KONTROL 'kalite kusuru' -> QM ipucu VAR",
             "Kalite kusuru bildirimi icin yeni bir ekran gelistirelim", QM_MK),
            ("B6 POZ.KONTROL 'kusur kodu' -> QM ipucu VAR",
             "Kusur kodu bazinda yeni rapor gelistirelim", QM_MK),
            ("B7 POZ.KONTROL 'urun kusuru' -> QM ipucu VAR",
             "Urun kusuru oranlarini gosteren yeni liste ekleyelim", QM_MK),
            ("B8 POZ.KONTROL 'defect code' -> QM ipucu VAR",
             "Defect code listesini ekrana getirecek gelistirme yapalim ve alan ekleyelim",
             QM_MK),
            # --- 2026-08-22 dalgasinin POZITIF KONTROLU ---------------------------
            # ⭐ B10/B11/B12 ayrica ERISILEBILIRLIK kanitidir: yeni capalarin HICBIR
            # gercek ifadeyle eslesmemesi mumkundu (olu kanca). Bunlar o riski kapatir.
            # ⛔ ETIKET DUZELTILDI (2026-08-22/N6): eski ad 'urun agaci' (ASCII) diyordu
            # ama prompt DIYAKRITIKLI idi — yani ASCII yazim HIC olculmemisti ve vektor
            # kapsadigindan FAZLASINI iddia ediyordu. Sinif: "FP/pozitif-kontrol vektoru
            # kusurun GERCEK yazim biciminde yazilir".
            ("B9 POZ.KONTROL ürün ağacı (DIYAKRITIKLI) -> PP ipucu VAR",
             "Ürün ağacı patlatma raporu ekleyelim", PP_MK),
            # ⭐ B9b — N6'nin ASIL vektoru: ASCII yazim. Eski desen bunu KACIRIYORDU.
            ("B9b POZ.KONTROL urun agaci (ASCII) -> PP ipucu VAR (N6 genisletmesi)",
             "Urun agaci patlatma raporu ekleyelim", PP_MK),
            # ⭐ B9c — KARISIK yazim (kullanicilar diyakritigi kismen kullanir).
            ("B9c POZ.KONTROL ürün agaci (KARISIK) -> PP ipucu VAR",
             "Ürün agaci patlatma raporu ekleyelim", PP_MK),
            ("B10 POZ.KONTROL 'bill of materials' -> PP ipucu VAR (YENI capa)",
             "Bill of materials raporu gelistirelim", PP_MK),
            ("B11 POZ.KONTROL 'kalite kontrol plani' -> QM ipucu VAR (YENI capa)",
             "Kalite kontrol plani ekrani gelistirelim", QM_MK),
            ("B12 POZ.KONTROL 'uretim BOM bilesen' -> PP ipucu VAR (YENI capa)",
             "Uretim BOM bilesenlerini listeleyen yeni rapor gelistirelim", PP_MK),
        ]
        for ad, pr, mk in B:
            rc, ctx = kos(hook, sb, pr)
            ekle(ad, mk in ctx, f"exit={rc}; ipucu bulunamadi -> KAPSAM KAYBI")

        # === C) DOKUNULMAYAN TOKEN'LAR (kontrol grubu) ====================
        # Bu tur YALNIZ iki tek-kelimelik kancayi degistirdi; oteki tokenlar AYNEN
        # calismali. Bozulurlarsa daraltma komsuya tasmis demektir.
        C = [
            ("C1 kontrol: 'uretim siparisi' -> PP (dokunulmadi)",
             "Üretim siparişi raporuna kolon ekleyelim", PP_MK),
            ("C2 kontrol: 'muayene lotu' -> QM (dokunulmadi)",
             "Muayene lotu ekranina yeni alan ekleyelim", QM_MK),
            ("C3 kontrol: 'is emri' -> PP (dokunulmadi)",
             "İş emri listesine yeni bir kolon ekleyelim", PP_MK),
            ("C4 kontrol: komsu modul SD bozulmadi",
             "Müşteri siparişi kalemine yeni alan ekleyelim", "SD (Satış-Dağıtım)"),
        ]
        for ad, pr, mk in C:
            rc, ctx = kos(hook, sb, pr)
            ekle(ad, mk in ctx, f"exit={rc}")

        # === D) SOZLESME CAPALARI =========================================
        rc, ctx = kos(hook, sb, "Bugun hava nasil? Sadece merak ettim, bir sey yapma.")
        ekle("D1 gelistirme-niyeti YOK -> hook SESSIZ", rc == 0 and ctx == "",
             f"exit={rc} ctx_uzunluk={len(ctx)}")

        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = str(sb)
        p = subprocess.run([sys.executable, str(hook)], input=b'{"prompt": ',
                           env=env, capture_output=True, cwd=str(sb), timeout=120)
        ekle("D2 3.BAGLAM bozuk payload -> exit 0 + GIRDI-PARSE-EDILEMEDI notu",
             p.returncode == 0 and b"GIRDI-PARSE-EDILEMEDI" in p.stderr,
             f"exit={p.returncode} (B0b sozlesmesi / negatif_test_harness)")

        kaynak = HOOK.read_text(encoding="utf-8")
        ekle("D3 SINIF capasi: tek-kelimelik `\\breçete` / `\\bkusur` GERI GELMEDI",
             r'r"\breçete' not in kaynak and r'r"\bkusur|' not in kaynak
             and "\\breçete|" not in kaynak and "\\bkusur|" not in kaynak,
             "kanca sessizce eski haline donerse bu vektor kirilir")

        # D4 — 2026-08-22 dalgasinin ayni sinif capasi. AYRI vektor: D3 yalnizca ILK
        # dalgayi (reçete/kusur) civiliyor; ikinci dalga geri alinsa D3 YINE PASS verirdi.
        ekle("D4 SINIF capasi: ciplak `\\bBOM\\b` / `\\bkalite\\s+kontrol|` GERI GELMEDI",
             r'\bBOM\b|' not in kaynak and r'\bkalite\s+kontrol|' not in kaynak,
             "ciplak kanca geri gelirse Byte-Order-Mark / belge-kalite FP'si geri doner")

        # D5 — N6 (UCUNCU dalga) sinif capasi. AYRI vektor: D3/D4 yalnizca DARALTMA
        # dalgalarini civiller; diyakritik-bagimli yazim geri gelse ikisi de PASS
        # verirdi. Sinif: "bir desen ailesinde tek ayak stil disi kalirsa o ayak
        # sessizce kapsam kaybeder" (komsulari `[üu]`/`[ğg]` stilindeydi).
        ekle("D5 SINIF capasi: diyakritik-BAGIMLI `\\bürün\\s+ağac` GERI GELMEDI",
             r'\bürün\s+ağac|' not in kaynak
             and r'\b[üu]r[üu]n\s+a[ğg]ac|' in kaynak,
             "diyakritik-bagimli ayak geri gelirse ASCII yazan kullanici yine kacar")

    finally:
        if mutant is not None:
            try:
                mutant.unlink()
            except Exception:
                pass
            print(f"[kalinti-kontrolu] mutant dosya duruyor mu: "
                  f"{'EVET -- TEMIZLIK BASARISIZ' if mutant.exists() else 'hayir'}")
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for _a, k, _c in sonuc if k)
    for ad, k, ac in sonuc:
        print(f"  [{'PASS' if k else 'FAIL'}] {ad}" + (f"  ({ac})" if ac and not k else ""))
    print(f"\nintake_modul_carpismasi: {gecen}/{len(sonuc)}")
    if secili:
        print(f"  (MUTASYON {secili[0]} — dusmesi BEKLENEN vektorler var; "
              f"tam skor 'mutasyon KACTI' demektir)")
    return 0 if gecen == len(sonuc) else 1


if __name__ == "__main__":
    raise SystemExit(main())
