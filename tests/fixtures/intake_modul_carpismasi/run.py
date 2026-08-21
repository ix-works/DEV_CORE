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
            if QM_YENI not in yamali:
                print("[DOGRULANAMADI] asiri-dar mutasyonunun QM ayagi tutmadi.")
                return 2
            yamali = yamali.replace(QM_YENI, r'        r"ZZZ_ASLA_ESLESMEZ_MUT|"', 1)
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
