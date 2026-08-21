#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D2 KURATLI KANCALAR — watchdog_launch._brifing_lint (2026-08-21).

NEDEN BU KORPUS VAR
-------------------
Bugunun en pahali iki ihlali ZATEN YAZILI kurallardi; eksik olan TETIKLEME idi:
  · `YK-4` (21.08): ajan spec'in "dosya butunlugu kurali YOKTUR" hukmune ragmen ROLLBACK
    secti = yok denen kurali FIILEN KOYDU. Kapi BLOCKER verdi, maliyet BIR TAM TUR.
    Ucuncu yol vardi (0 lot yerine 99) ama "iki secenek var, ikisi de kotu" varsayildi.
  · deploy: "lokal test OK'siz deploy yok" kurali yazili, brife konmuyor.

⛔ NEDEN GENEL BIR MEMORY-NUDGE DEGIL: 605 gercek brif olculdu. Evin KENDI skorlayicisi
(`recall_inject`) ajan briflerinde uretim esiginde **%100** atesliyor ve aranan dersi
**0/7** yuzeye cikariyor; banda cekilince yine 0/7. Genel kopru evin gurultu bandinda
COZUMSUZ; gate'lenecek olan "her spawn'a ilgili dersler" degil, IHLALI PAHALI OLAN TEK
TEK KURALLARDIR. (PLAN-2026-08-21-BRIFING-DISIPLINI.md §8.1)

⛔⛔ D2 BUTCESI DOLU — UCUNCU KANCA EKLEME. Atesleme oranlari TOPLANIR:
2 kanca %8,6-26,0 · 3 kanca %19,3-30,2 (BANT USTU) · 7 aday birden %77,9.
Ev bandi %13,9-18,4. Vektor B1 bu butceyi YAPISAL olarak civiller: kaynakta
`[BRIFING-LINT/` markeri 2'den fazlaysa korpus KIRMIZI verir.

KOSUM:  python tests/fixtures/brifing_lint_d2/run.py
        python tests/fixtures/brifing_lint_d2/run.py --mutasyon-kimlik   (kanca A sokulur)
        python tests/fixtures/brifing_lint_d2/run.py --mutasyon-deploy   (kanca B sokulur)
        python tests/fixtures/brifing_lint_d2/run.py --mutasyon-fren     (GEVSETME yonu:
                                                      yeniden-yorum freni sarti kaldirilir)
Cikis:  0 hepsi beklendigi gibi · 1 sapma · 2 DOGRULANAMADI (mutasyon capasi tutmadi)

⚠ UC MUTASYON, HICBIRI DIGERINI KAPSAMAZ — biri A'yi, biri B'yi, biri FP-capasini sinar.
⚠ Capalar HAM stdout'ta degil COZULMUS `additionalContext`te kurulur (json.dumps
  `ensure_ascii=True` -> Turkce substring ham telde bulunmaz = sahte-KIRMIZI).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent          # <repo>/tests/fixtures/<ad>/run.py
HOOK = REPO / "scripts" / "hooks" / "watchdog_launch.py"

A_MK = "[BRIFING-LINT/T3-KIMLIK]"
B_MK = "[BRIFING-LINT/DEPLOY]"
R2_MK = "R2 sablon izleri eksik"
ENG_MK = "BASKA BIR AGACA yazma isi"

# --- mutasyon capalari (taban SHA degil, ICERIK capasi) ----------------------
MUT_KIMLIK = (
    '        kimlik = _re.search(r"\\b(YK|TY|SZ|AK|SNF|D-R|BT|FZ|TG|DA)-?\\d", duz)',
    '        kimlik = None  # MUTASYON: kanca A sokuldu',
)
MUT_DEPLOY = (
    '        deploy = _re.search(r"DEPLOY|DEPLOY_UI|UI5 YAYIN", duz)',
    '        deploy = None  # MUTASYON: kanca B sokuldu',
)
# GEVSETME YONU: fren sarti kaldirilirsa kanca A "kural anilan her yazma isinde" atesler
MUT_FREN = (
    '        if kimlik and k_yazma and not fren:',
    '        if kimlik and k_yazma:  # MUTASYON: yeniden-yorum freni sarti KALDIRILDI',
)

# Dolgu: 400 karakter muafiyet esigini asmak icin. ⛔ Hicbir tetik/bastirma terimi
# TASIMAZ (FIX/DUZELT/UYGULA/PUSH/DOKUNMA/ONAY/DEPLOY/LOKAL TEST/WORKTREE yok) -- yoksa
# vektorlerin hangi eksenden atesledigi belirsizlesir.
_DOLGU = (" Bagimsiz okuma cagrilarini tek turda paralel gonder; ara urunleri diske "
          "kaydet; kanitsiz iddia rapora girmez; bulunamadi ile mevcut-degil ayni sey "
          "degildir. Cikti: SendMessage(to:main) ile tek mesaj. ")


def _uzun(govde: str) -> str:
    while len(govde) < 520:
        govde += _DOLGU
    return govde


def kos(hook: Path, proje: Path, payload: dict | None, ham: bytes | None = None):
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(proje)
    env["PYTHONIOENCODING"] = "utf-8"
    girdi = ham if ham is not None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    p = subprocess.run([sys.executable, str(hook)], input=girdi, env=env,
                       capture_output=True, cwd=str(proje), timeout=120)
    out = p.stdout.decode("utf-8", "replace")
    err = p.stderr.decode("utf-8", "replace")
    try:
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        gecerli_json = True
    except Exception:
        ctx, gecerli_json = "", (out.strip() == "")
    return p.returncode, ctx, err, gecerli_json


def payload(prompt: str, sid: str = "d2-test") -> dict:
    return {"session_id": sid, "tool_name": "Agent", "tool_input": {"prompt": prompt}}


# --- GERCEK VAKA (2026-08-21 YK-4) -------------------------------------------
# Brifin ozu: onayli bir kural kimligi aniliyor + duzeltme/uygulama isi veriliyor +
# "kendi yorumunu uygulama, SOR" freni YOK. O gun ajan tam bu boslugu kullandi.
# (Obje adi jenerik tutuldu: core PUBLIC repodur.)
VAKA_YK4 = (
    "GOREV: ZSD001 A-13 kaleminde YK-4 kuralinin gerektirdigi duzeltmeyi UYGULA. "
    "Spec TS-04:1443 dosya butunlugu icin ayrica bir kural TANIMLAMIYOR; sen yine de "
    "tutarli bir sonuc uret ve sonucu beyan et. Lot alani bos gelen kayitlarda ne "
    "yapacagina karar ver ve devam et. KANIT KURALLARI gecerlidir; her iddiaya kaynak "
    "ver. GOREV SINIRLARI: yalniz A-13; baska pakete gecme. "
)


def main() -> int:
    mutlar = {"--mutasyon-kimlik": MUT_KIMLIK,
              "--mutasyon-deploy": MUT_DEPLOY,
              "--mutasyon-fren": MUT_FREN}
    secili = [a for a in sys.argv[1:] if a in mutlar]
    hook = HOOK
    mutant_dosya = None

    if secili:
        kaynak = HOOK.read_text(encoding="utf-8")
        eski, yeni = mutlar[secili[0]]
        if eski not in kaynak:
            print(f"[DOGRULANAMADI] mutasyon capasi tabanda bulunamadi ({secili[0]}) -> "
                  "mutasyon gercekten uygulanmadi; 'gecti' sonucu ANLAMSIZ olurdu.")
            return 2
        # Mutant KOMSULARINI bulabilsin diye scripts/hooks ICINE yazilir (runpy/import
        # sinifi). `_` onekli => C-TPL-01 hook envanterinden elenir. finally'de SILINIR.
        hook = HOOK.with_name("_mutant_watchdog_launch.py")
        hook.write_text(kaynak.replace(eski, yeni, 1), encoding="utf-8")
        mutant_dosya = hook

    tmp = Path(tempfile.mkdtemp(prefix="brif_d2_"))
    sonuc: list[tuple[str, bool, str]] = []
    try:
        sb = tmp / "proje"
        sb.mkdir(parents=True, exist_ok=True)

        def ekle(ad, kosul, aciklama=""):
            sonuc.append((ad, bool(kosul), aciklama))

        # === KANCA A — T3-KIMLIK ==========================================
        rc, ctx, _e, ok = kos(hook, sb, payload(_uzun(
            "GOREV: YK-4 kuralina gore alan hesabini FIX et ve sonucu bildir. "
            "KANIT KURALLARI: her iddiaya kaynak ver. ")))
        ekle("A-P1 kimlik(YK-4) + yazma + fren YOK -> ATESLER",
             A_MK in ctx and "YK-4" in ctx,
             "not, ANILAN kimligi geri tasimali (hangi kural oldugu gorunsun)")
        ekle("A-P1b stdout sozlesmesi korunur", rc == 0 and ok, f"exit={rc} json={ok}")

        rc, ctx, _e, _ok = kos(hook, sb, payload(_uzun(VAKA_YK4)))
        ekle("A-P2 GERCEK VAKA (2026-08-21 YK-4 brifi) YAKALANIR",
             A_MK in ctx and "ucuncu yolu ara" in ctx.lower(),
             "o gun BIR TAM TUR kaybettiren bosluk spawn aninda yuzeye cikmali")

        rc, ctx, _e, _ok = kos(hook, sb, payload(_uzun(
            "GOREV: D-R17 ve SNF-6 kalemlerini IMPLEMENT et. KANIT KURALLARI gecerli. ")))
        ekle("A-P3 kimlik AILESI (D-R17/SNF-6) da taninir", A_MK in ctx,
             "desen tek bir onekle sinirli degil")

        # --- A FP CAPALARI (mutasyonlarda AYAKTA KALMALI) -----------------
        rc, ctx, _e, _ok = kos(hook, sb, payload(_uzun(
            "GOREV: YK-4 kuralina gore alan hesabini FIX et. Onayli bir kural sana "
            "uygulanamaz geliyorsa KENDI YORUMUNU uygulama -> SOR. KANIT KURALLARI. ")))
        ekle("A-N1 FP: fren YAZILMIS -> SESSIZ", A_MK not in ctx,
             "brif zaten dogru yazilmis; ikinci kez durtme (mutasyon-fren bunu KIRAR)")

        rc, ctx, _e, _ok = kos(hook, sb, payload(_uzun(
            "GOREV: YK-4 kuralinin bugunku kapsamini ARASTIR ve raporla. Salt-okuma "
            "turudur; hicbir dosya degistirilmeyecek. KANIT KURALLARI gecerlidir. ")))
        ekle("A-N2 FP: kimlik VAR ama YAZMA isi YOK -> SESSIZ", A_MK not in ctx,
             "eksen 'kural anilmis' degil 'kural anilmis VE yazma veriliyor' der")

        rc, ctx, _e, _ok = kos(hook, sb, payload(_uzun(
            "GOREV: raporun tablo bolumunu DUZELT ve PUSH et. KANIT KURALLARI. ")))
        ekle("A-N3 FP: yazma VAR ama kural kimligi YOK -> SESSIZ", A_MK not in ctx)

        # === KANCA B — DEPLOY =============================================
        rc, ctx, _e, _ok = kos(hook, sb, payload(_uzun(
            "GOREV: musteri UI uygulamasini DEPLOY et (deploy_ui.py kanonik yol). "
            "KANIT KURALLARI gecerlidir; her iddiaya kaynak ver. ")))
        ekle("B-P1 deploy + sart YOK -> ATESLER",
             B_MK in ctx and "bug-gate" in ctx.lower())

        rc, ctx, _e, _ok = kos(hook, sb, payload(_uzun(
            "GOREV: yeni surumu UI5 YAYIN adimindan gecir ve bitir. KANIT KURALLARI. ")))
        ekle("B-P2 'UI5 YAYIN' yazimi da taninir", B_MK in ctx)

        # --- B FP CAPALARI -------------------------------------------------
        rc, ctx, _e, _ok = kos(hook, sb, payload(_uzun(
            "GOREV: uygulamayi DEPLOY et. Once LOKAL TEST kos, sonuc OK ise ilerle. "
            "KANIT KURALLARI gecerlidir. ")))
        ekle("B-N1 FP: 'LOKAL TEST' yazilmis -> SESSIZ", B_MK not in ctx)

        rc, ctx, _e, _ok = kos(hook, sb, payload(_uzun(
            "GOREV: uygulamayi DEPLOY et. BUG-GATE zincirini kos, sonra ilerle. "
            "KANIT KURALLARI gecerlidir. ")))
        ekle("B-N2 FP: 'BUG-GATE' yazilmis -> SESSIZ", B_MK not in ctx)

        rc, ctx, _e, _ok = kos(hook, sb, payload(_uzun(
            "GOREV: CDS goruntumunu olustur ve aktive et. KANIT KURALLARI gecerlidir. ")))
        ekle("B-N3 FP: deploy isi YOK -> SESSIZ", B_MK not in ctx)

        # === KONTROL GRUBU — mevcut UC eksen degismedi ====================
        temiz = _uzun("GOREV: paket icerigini listele ve ozetle. KANIT KURALLARI "
                      "gecerlidir; kanitsiz iddia yazma. ")
        rc, ctx, _e, _ok = kos(hook, sb, payload(temiz))
        ekle("K1 temiz brif -> HICBIR lint notu yok",
             A_MK not in ctx and B_MK not in ctx and R2_MK not in ctx and ENG_MK not in ctx,
             "yeni kancalar tabana gurultu EKLEMEDI")

        rc, ctx, _e, _ok = kos(hook, sb, payload(_uzun(
            "Su paketi incele ve bir ozet cikar. Sonuclari bana bildir. ")))
        ekle("K2 mevcut GOREV/KANIT-KURAL ekseni HALA calisir", R2_MK in ctx,
             "yeni kancalar mevcut ekseni bozmadi")

        rc, ctx, _e, _ok = kos(hook, sb, payload(_uzun(
            "GOREV: WORKTREE C:/IX/_wt/x altinda duzeltmeyi UYGULA ve dosyalari OLUSTUR. "
            "KANIT KURALLARI gecerlidir. ")))
        ekle("K3 mevcut ENGELLENIRSEN ekseni HALA calisir", ENG_MK in ctx)

        # === EMIT YOLU: idempotent (heartbeat taze) dalinda da not cikar ===
        hb = sb / ".tmp" / "claude_watchdog"
        hb.mkdir(parents=True, exist_ok=True)
        (hb / "heartbeat_d2-test").write_text("x", encoding="utf-8")
        os.utime(hb / "heartbeat_d2-test", (time.time(), time.time()))
        rc, ctx, _e, _ok = kos(hook, sb, payload(_uzun(
            "GOREV: YK-4 kuralina gore alan hesabini FIX et. KANIT KURALLARI. ")))
        ekle("E1 idempotent-dal (heartbeat taze) da yeni notu tasir",
             A_MK in ctx and "Zaten canli" in ctx,
             "not daemon basarisindan BAGIMSIZ olmali (_ek_notlar 4 emit yolunda)")
        shutil.rmtree(hb, ignore_errors=True)

        # === 3. BAGLAM (gorev-DISI): komsu parse-fail sozlesmesi ===========
        rc, ctx, err, ok = kos(hook, sb, None, ham=b'{"tool_input": {"prompt": ')
        ekle("E2 3.BAGLAM bozuk payload -> exit 0 + GIRDI-PARSE-EDILEMEDI notu",
             rc == 0 and "GIRDI-PARSE-EDILEMEDI" in err,
             f"exit={rc}; B0b sozlesmesi (negatif_test_harness) bozulmadi")

        # === BUTCE CAPASI (sinif korumasi) ================================
        kaynak = HOOK.read_text(encoding="utf-8")
        d2_sayisi = kaynak.count('"[BRIFING-LINT/')
        ekle("B1 D2 BUTCESI: kaynakta EN FAZLA 2 kuratli kanca",
             d2_sayisi == 2,
             f"bulunan={d2_sayisi}; 3. kanca birlesik orani BANT USTUNE cikarir "
             f"(olculdu: 3 kanca %19,3-30,2 vs ev bandi %13,9-18,4)")

    finally:
        if mutant_dosya is not None:
            try:
                mutant_dosya.unlink()
            except Exception:
                pass
            kalinti = mutant_dosya.exists()
            print(f"[kalinti-kontrolu] mutant dosya duruyor mu: "
                  f"{'EVET -- TEMIZLIK BASARISIZ' if kalinti else 'hayir'}")
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for _a, k, _c in sonuc if k)
    for ad, k, ac in sonuc:
        print(f"  [{'PASS' if k else 'FAIL'}] {ad}" + (f"  ({ac})" if ac and not k else ""))
    print(f"\nbrifing_lint_d2: {gecen}/{len(sonuc)}")
    if secili:
        print(f"  (MUTASYON {secili[0]} — dusmesi BEKLENEN vektorler var; "
              f"tam skor 'mutasyon KACTI' demektir)")
    return 0 if gecen == len(sonuc) else 1


if __name__ == "__main__":
    raise SystemExit(main())
