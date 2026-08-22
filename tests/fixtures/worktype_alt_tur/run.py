#!/usr/bin/env python3
"""ALT-TUR ekseni (sap_worktype_hint._alt_tur) — is turu OBJE TIPINDE BITMEZ.

NEDEN BU KORPUS VAR (olculmus vaka 2026-08-22, kuyruk Q5)
---------------------------------------------------------
11 soyut varlik (`define abstract entity`) `object_type='ddls'` ile SAP'ye push edildi.
`sap_worktype_hint` obje-tipini gordu ve KANONIK CDS satirini basti:
"playbook/adt-cds.md 'TEK CDS YARATMA'". Oysa `playbook/adt-cds.md` §ABSTRACT ENTITY tam
da o bolumun onerdigi araclarin (`create_cds_view.py` / `populate_cds_views.py`) abstract
entity'de CALISMADIGINI yazar ve su kurali koyar: *"yeni DDLS gorunce TURUNE bak - SELECT
var mi? ... Tahminle arac secme."* Yani hatirlatici, recetenin KENDI kuralini uygulamiyor;
obje tipinde duruyor, ALT-TURE bakmiyordu. (`checklists/cds-creation.md` icinde "abstract"
kelimesi HIC gecmiyor - olculdu.) Bedel: 1 gateway turu + gereksiz bir infra fix onayi.

⛔ NEDEN BRIFING METNI DEGIL KAYNAK: alt-tur brifingden TAHMIN edilmez; artefaktin KENDI
bildirimi onu SOYLER ve o bildirim bu tool'un payload'inda zaten vardir. Ayni evde
brifing-metni tahmini iki kez olculup curutuldu (eski `skill_injector` 12-regex'i;
2026-08-21 `brifing-lint` D2 kancalari, precision 0).

⛔ SOZLUK YOK: alt-tur -> bolum eslemesi ELLE tutulmaz; `_checklist()`in ZATEN andigi
recete dosyalarinin KENDI BASLIKLARINDAN turetilir. Belirsizse (birden cok baslik) SUSAR.

⛔ SILINMEZ FP CAPALARI (ikisi de bu turda GERCEKTEN kirmiziya dustu, sonra duzeltildi):
  · N1b `define view entity ... as select from` -> eski hal `§T3 read-only consumption`
    tuzak notuna yolluyordu (o baslikta ifade KOD PARCASI icinde; ayni suzgec kapatti).
  · N2  `define root view entity ...`           -> eski hal §ABSTRACT ENTITY'ye yolluyordu
    (baslikta gecen `define [root] abstract entity` KOD PARCASI yuzunden; 292 gercek
    artefaktin 30'u bu FP'ye dusuyordu; simdi basliklarin kod parcalari sozluge girmez).

KOSUM:  python tests/fixtures/worktype_alt_tur/run.py
        ... --mutasyon            (alt-tur cozumunu SOK)
        ... --mutasyon-kodspan    (baslik kod-parcasi suzgecini geri al)
        ... --mutasyon-pencere    (bildirim taramasini ilk 60 satira dusur)
        ... --mutasyon-dedup      (dedup anahtarindan alt-turu cikar)
Cikis:  0 hepsi beklendigi gibi · 1 sapma · 2 DOGRULANAMADI (mutasyon capasi tutmadi)
"""
from __future__ import annotations

import json
import os
import re
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
REPO = HERE.parent.parent.parent            # <repo>/tests/fixtures/<ad>/run.py
HOOK = REPO / "scripts" / "hooks" / "sap_worktype_hint.py"

# --- mutasyon capalari (ICERIK capasi; taban SHA degil) ----------------------
MUT_SOK = (
    "    alt = _alt_tur(_kaynak_metni(ti) if isinstance(ti, dict) else \"\",",
    "    alt = None if True else _alt_tur(_kaynak_metni(ti) if isinstance(ti, dict) else \"\",",
)
MUT_KODSPAN = (
    '                    duz = re.sub(r"`[^`]*`", " ", m.group(1))',
    '                    duz = m.group(1)  # MUTASYON: kod-parcasi suzgeci sokuldu',
)
MUT_PENCERE = (
    '    for ln in (source or "").splitlines():',
    '    for ln in (source or "").splitlines()[:60]:',
)
MUT_DEDUP = (
    '    anahtar = grup if not alt else "%s:%s" % (grup, alt[0])',
    '    anahtar = grup  # MUTASYON: alt-tur dedup anahtarindan cikarildi',
)
# ⚠ MUTASYONU OLMAYAN IKINCI SAVUNMA (durustluk notu): `_ikili` bildirimi obje adindan
# ONCE keser. Bu koruma bugun BAGIMSIZ OLARAK OLCULEMIYOR — kesme sokulunca 293 gercek
# artefaktta sonuc DEGISMIYOR (42 abstract / 251 sessiz), cunku basliklarin kod-parcasi
# suzgeci ayni yolu zaten kapatiyor (savunma-derinligi ortusmesi). Kesme kaldirilmadi:
# kod-parcasi ICERMEYEN bir baslik yazildigi gun tek savunma o olacak.
# Gercek artefaktlarda bildirim uzun banner yorumunun ALTINDA olur (olculdu: 92./117. satir)
BANNER = "\n".join(["// " + "=" * 70] +
                   ["// aksiyon parametre varligi - aciklama satiri %d" % i
                    for i in range(1, 88)] +
                   ["// " + "=" * 70])

KAYNAK = {
    "abstract_banner": "@EndUserText.label: 'Iptal parametresi'\n" + BANNER +
                       "\ndefine root abstract entity ZSD001_I_IPTAL_P\n"
                       "{\n  mesaj_no : abap.numc(3);\n}\n",
    "abstract_duz": "define abstract entity ZSD001_I_TAHSIS_P\n{\n  a : abap.char(1);\n}\n",
    "abstract_upper": "DEFINE ABSTRACT ENTITY ZSD001_I_Q\n{\n  A : abap.char(1);\n}\n",
    "view_entity": "@AccessControl.authorizationCheck: #CHECK\n"
                   "define view entity ZSD001_I_KOK as select from vbak\n"
                   "{ key vbeln as Vbeln }\n",
    "root_view": "define root view entity ZSD001_I_DRIVER as select from zsd001_t_drv\n"
                 "{ key uname as Uname }\n",
    "projection": "define view entity ZSD001_C_KOK as projection on ZSD001_I_KOK\n"
                  "{ /*fields*/ }\n",
    "bdef": "managed implementation in class ZBP_SD001_I_KOK unique;\nstrict ( 2 );\n"
            "define behavior for ZSD001_I_KOK alias Kok\n{ }\n",
}

ALT = "ALT-TÜR"
ABS_BOLUM = "ABSTRACT ENTITY"
TABAN_CDS = "playbook/adt-cds.md"           # core/ onekiyle basilir


def kos(hook: Path, proje: Path, payload, ham: bytes | None = None):
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
        gecerli = True
    except Exception:
        ctx, gecerli = "", (out.strip() == "")
    return p.returncode, ctx, err, gecerli


def push(kaynak_ad, otype: str = "ddls", **ek):
    ti = {"object_type": otype, "name": "ZSD001_I_TEST"}
    if kaynak_ad:
        ti["source"] = KAYNAK[kaynak_ad]
    ti.update(ek)
    return {"session_id": "wt-alt", "tool_name": "mcp__sap-adt__adt_push_source",
            "tool_input": ti}


def sifirla(proje: Path):
    f = proje / ".claude" / ".worktype_hinted.json"
    if f.exists():
        f.unlink()


def main() -> int:
    gecerli_kipler = {"--mutasyon", "--mutasyon-kodspan", "--mutasyon-pencere",
                      "--mutasyon-dedup"}
    for a in sys.argv[1:]:
        if a.startswith("--mutasyon") and a not in gecerli_kipler:
            raise SystemExit("[KULLANIM] bilinmeyen mutasyon kipi: %s -> gecerli: %s"
                             % (a, ", ".join(sorted(gecerli_kipler))))
    secilen = [a for a in sys.argv[1:] if a in gecerli_kipler]
    hook, mutant = HOOK, None
    if secilen:
        eski, yeni = {"--mutasyon": MUT_SOK, "--mutasyon-kodspan": MUT_KODSPAN,
                      "--mutasyon-pencere": MUT_PENCERE,
                      "--mutasyon-dedup": MUT_DEDUP}[secilen[0]]
        kaynak = HOOK.read_text(encoding="utf-8")
        if eski not in kaynak:
            print("[DOGRULANAMADI] mutasyon capasi tabanda bulunamadi -> mutasyon "
                  "gercekten uygulanmadi; 'gecti' sonucu ANLAMSIZ olurdu.")
            return 2
        # Mutant KOMSU modulleri (utils.inject_paths) bulabilsin diye ayni dizine yazilir.
        mutant = HOOK.with_name("_mutant_sap_worktype_hint.py")
        mutant.write_text(kaynak.replace(eski, yeni, 1), encoding="utf-8")
        hook = mutant

    sys.path.insert(0, str(REPO / "scripts" / "hooks"))
    modul = __import__(hook.stem)

    tmp = Path(tempfile.mkdtemp(prefix="wt_alt_"))
    sonuc = []

    def ekle(ad, kosul, aciklama):
        sonuc.append((ad, bool(kosul), aciklama))

    try:
        proje = tmp / "proje"
        (proje / ".claude").mkdir(parents=True, exist_ok=True)

        # ── P: AYIRT EDICILER ────────────────────────────────────────────────
        sifirla(proje)
        rc, ctx, _err, ok = kos(hook, proje, push("abstract_banner"))
        ekle("P1 GERCEK VAKA (soyut varlik, bildirim 90. satirdan SONRA)",
             ALT in ctx and ABS_BOLUM in ctx and TABAN_CDS in ctx,
             "kaynak `define root abstract entity` diyor -> AYRI bolum yuzeye cikmali")
        ekle("P1b stdout/exit sozlesmesi", rc == 0 and ok, "exit=%s gecerli-json=%s" % (rc, ok))
        ekle("P1c TABAN SATIRI KORUNUYOR (regresyon)",
             "TEK CDS YARATMA" in ctx and "run_review" in ctx,
             "alt-tur satiri EKLENIR, kanonik satiri EZMEZ")

        sifirla(proje)
        _rc, ctx2, _e, _o = kos(hook, proje, push("abstract_upper"))
        ekle("P2 BUYUK HARF bildirim de cozulur", ALT in ctx2 and ABS_BOLUM in ctx2,
             "ABAP kaynagi buyuk harf yazilabilir")

        sifirla(proje)
        dosya = tmp / "ZSD001_I_IPTAL_P.cds"
        dosya.write_text(KAYNAK["abstract_banner"], encoding="utf-8")
        _rc, ctx3, _e, _o = kos(hook, proje, push(None, file_path=str(dosya)))
        ekle("P3 3.BAGLAM `file_path` payload'i (source alani YOK)",
             ALT in ctx3 and ABS_BOLUM in ctx3,
             "gercek cagrilarda iki bicim de goruldu; ikisi de cozulmeli")

        # ── N: FP CAPALARI (mutasyonlarda AYAKTA KALMALI) ────────────────────
        sifirla(proje)
        _rc, ctxN1, _e, _o = kos(hook, proje, push("view_entity"))
        ekle("N1 FP: duz view-entity -> ALT-TUR YOK (taban satiri var)",
             ALT not in ctxN1 and "TEK CDS YARATMA" in ctxN1,
             "belirsiz alt-tur (3 baslik) -> SUSAR; yanlis bolum, bolumsuzden pahalidir")
        ekle("N1b FP: view-entity T3 tuzak notuna YOLLANMAZ", "T3" not in ctxN1,
             "olculmus regresyon: tum satir taraninca `select from` -> §T3'e yolluyordu")

        sifirla(proje)
        _rc, ctxN2, _e, _o = kos(hook, proje, push("root_view"))
        ekle("N2 FP: `define root view entity` -> ABSTRACT bolumune YOLLANMAZ",
             ABS_BOLUM not in ctxN2 and ALT not in ctxN2,
             "olculmus regresyon: 292 artefaktin 30'u bu FP'ye dusuyordu (baslik kod parcasi)")

        sifirla(proje)
        _rc, ctxN3, _e, _o = kos(hook, proje, push("projection"))
        ekle("N3 FP: projection view -> ALT-TUR YOK", ALT not in ctxN3, "bolumu yok -> susar")

        sifirla(proje)
        _rc, ctxN4, _e, _o = kos(hook, proje, push("bdef", otype="bdef"))
        ekle("N4 3.BAGLAM baska worktype (bdef/RAP): taban satiri var, uydurma bolum YOK",
             "rap-creation.md" in ctxN4 and ALT not in ctxN4,
             "eksen obje tipinden bagimsiz calisir ama uydurmaz")

        sifirla(proje)
        rcK, ctxK, _e, okK = kos(hook, proje, {"session_id": "x", "tool_name": "Read",
                                               "tool_input": {"file_path": "a.md"}})
        ekle("N5 KONTROL GRUBU: SAP-yazma DISI tool -> TAM SESSIZ",
             ctxK == "" and rcK == 0 and okK, "matcher disi cagride hicbir sey basilmaz")

        # ── D: DEDUP GRANULARITESI ───────────────────────────────────────────
        sifirla(proje)
        _r1, c1, _e, _o = kos(hook, proje, push("view_entity"))       # anahtar: cds
        _r2, c2, _e, _o = kos(hook, proje, push("abstract_duz"))      # anahtar: cds:abstract entity
        _r3, c3, _e, _o = kos(hook, proje, push("abstract_banner"))   # ayni alt-tur -> sessiz
        ekle("D1 ayni oturumda ONCE view-entity SONRA abstract -> IKINCISI DE KONUSUR",
             c1 != "" and ALT in c2 and ABS_BOLUM in c2,
             "tek 'cds' anahtari abstract uyarisini sessizce yutuyordu (vakanin 2. yuzu)")
        ekle("D2 ayni alt-tur ikinci kez -> SESSIZ (gurultu siniri korunur)",
             c3 == "", "dedup sozlesmesi bozulmadi")

        # ── F: FAIL-OPEN + TAZELIK ───────────────────────────────────────────
        bos = tmp / "playbooksuz"
        (bos / "playbook").mkdir(parents=True, exist_ok=True)   # BOS recete agaci
        _g, satir_cds = modul._checklist("ddls")
        ekle("F1 FAIL-OPEN: recete agaci bosken alt-tur None (cokme yok)",
             modul._alt_tur(KAYNAK["abstract_banner"], satir_cds, bos) is None,
             "bulunamayan bolum uydurulmaz; taban satiri bozulmaz")
        ekle("F2 FAIL-OPEN: kaynak bozuk/bos tipte -> None",
             modul._alt_tur(None, satir_cds, REPO) is None and
             modul._alt_tur("", satir_cds, REPO) is None,
             "payload sekli bozuksa da cokmez")

        rcB, _ctxB, errB, okB = kos(hook, proje, None, ham=b"{bozuk json")
        ekle("F3 B0b SOZLESMESI (3.baglam): bozuk stdin -> exit 0 + stderr notu",
             rcB == 0 and okB and "GIRDI-PARSE-EDILEMEDI" in errB,
             "parse-fail gorunurlugu bu turda bozulmadi (exit=%s)" % rcB)

        eksik = []
        for otype in ("ddls", "bdef", "doma", "struct", "prog"):
            grup, satir = modul._checklist(otype)
            if not grup:
                continue
            if not modul._recete_dosyalari(satir, REPO):
                eksik.append((grup, "hicbir recete dosyasi cozulmedi"))
            for yol in re.findall(r"playbook/[\w./-]+\.md", satir):
                if not (REPO / yol).is_file():
                    eksik.append((grup, yol))
        ekle("T1 TAZELIK: hatirlaticinin andigi her recete yolu ACILABILIR",
             not eksik, "bayat yol = sessiz yanlis isaretci; eksik: %s" % (eksik or "yok"))

        # ── S: SINIF KANITI (mekanizma nokta-vaka degil) ─────────────────────
        yeni_bolum = REPO / "playbook" / "_fixture_gecici_bolum.md"
        try:
            yeni_bolum.write_text("# gecici\n## SUPER ENTITY recetesi\nicerik\n",
                                  encoding="utf-8")
            satir_test = satir_cds + " (+ playbook/_fixture_gecici_bolum.md)"
            alt_yeni = modul._alt_tur("define super entity ZSD001_I_Y\n{ a : abap.char(1); }",
                                      satir_test, REPO)
            ekle("S1 SINIF: YENI alt-tur bolumu ELLE SOZLUGE eklenmeden cozulur",
                 bool(alt_yeni) and alt_yeni[0] == "super entity",
                 "eslesme playbook basliklarindan TURETILIR (bakimli sozluk YOK): %s"
                 % (alt_yeni,))
        finally:
            yeni_bolum.unlink(missing_ok=True)

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        if mutant is not None:
            mutant.unlink(missing_ok=True)
        kalinti = (list((REPO / "scripts" / "hooks").glob("_mutant_*.py"))
                   + list((REPO / "playbook").glob("_fixture_*.md")))
        if kalinti:
            print("[UYARI] KALINTI (mutant/gecici bolum) — sessiz bozulma riski: %s" % kalinti)

    dusen = [s for s in sonuc if not s[1]]
    for ad, ok, acik in sonuc:
        print("%s %-62s %s" % ("[OK]  " if ok else "[FAIL]", ad, "" if ok else acik))
    print("\n%d/%d PASS%s" % (len(sonuc) - len(dusen), len(sonuc),
                              "" if not dusen else "  (DUSEN: %s)"
                              % ", ".join(s[0].split()[0] for s in dusen)))
    return 0 if not dusen else 1


if __name__ == "__main__":
    raise SystemExit(main())
