#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OLCUM-YOKLUGU SOZLESMESI — "0 birim taradim" ile "ihlal yok" AYNI CIKTIYI vermez.

=== OLCULMUS KUSUR (Q232 · Q250 · Q254 — uc vaka, TEK sinif) ===
Bir kapi hicbir sey olcmediginde "temiz" diye raporluyordu; `exit 0` *"kontrol edildi,
ihlal yok"* diye okunuyordu, oysa olculen sey **hicbir seyin olculmedigi**.

  Q232  scripts/check_ui_odata_refs.py
        `--app <olmayan yol>` -> `glob` sessizce `[]` -> hicbir kontrol kosmaz -> `TEMIZ`
        + exit 0. Olculdu 2026-09-02: yol YOK (0 dosya) ile yol VAR (4 dosya) kosumlarinin
        ciktilari **BAYT-BIREBIR AYNI**ydi ⇒ cagiranin ayirt etmesi IMKANSIZ. Bir
        bug-expert'i fiilen yanilti.
  Q250  tests/run_battery.py --precommit
        `core_precommit --all` `git ls-files` kullanir = **INDEX**. Izlenmeyen (henuz
        `git add` edilmemis) dosyalar YAPISAL OLARAK gorunmez. Batarya bunu
        `OK(rc=0) ... PASS` diye basiyordu — sahte-yesil bir **kapi tablosunun icinde**.
        POZITIF KONTROL (canli, 2026-09-04): makine-lokal yol izi tasiyan izlenmeyen
        sonda -> `--all` rc=0 (639 dosya, 68 s) · `git add` sonrasi -> rc=1 GENERICIZE-LEAK.
  Q254  scripts/validators/check_hook_injected_paths.py
        `if not toplam: print("[WARN] ..."); return 0` ⇒ HARD gate, payda 0 iken yesil.

=== SINIF, VAKA DEGIL — ve YENI MEKANIZMA ICAT EDILMEDI ===
Ev sozlesmesi ZATEN VARDI, ikiye bolunmus halde; fix her vakayi DOGRU olana bagladi:
  (1) `scripts/utils/kapsam.py::kapsam_eki`  — insan-okur PAYDA ("N tarandi" / KAPSAM SIFIR)
  (2) `scripts/validators/_gate_status.py`   — makine-okur beyan (`measured=true|false`)
Ucuncusu bu turda dogdu, cunku batarya bir VALIDATOR degil bir RAPORLAYICIDIR:
  (3) `run_battery` uclu isaret: PASS / FAIL / **ATLA** (olculmedi)

=== ⚠ IKI ALT-SINIF AYRIDIR — sinir burada cizilir ===
  KAPSAM-SIFIR  "bakacak birim mesru sekilde yok"  -> GORUNUR ol, ama FAIL ETME.
                (kapsam.py K1 karari: `.bdef`i olmayan proje 0 `.bdef` tarar; bunu
                 FAIL yapmak her mesru-bos projede kalici kirmizi uretirdi.)
  OLCEMEDIM     "olcum aygitinin KENDISI calismadi"  -> FAIL-CLOSED.
                (byassoc_advisory S6 · abaplint fail-open fix'i · sap_doctor
                 "ulasilamadi" — evin bu ucta karari zaten FAIL'dir.)
  Q254 IKINCI gruptadir: sonda hook'lari core'un KENDI agacindan cagirir ve payload'lari
  kendi uretir ⇒ payda proje kurulumundan BAGIMSIZDIR (olculdu 2026-09-04: toplam=8).
  `toplam == 0` yalnizca 11 alt-surecin TAMAMI bos donerse olur = sonda kirik.
  X1/X2 vektorleri bu siniri civiler: **silinirlerse** sinif bir gun sessizce
  ya gevsetilir ya da mesru-bos kapsam kirmiziya cevrilir.

  A1  ⭐ AYIRT EDICI  --app yolu YOK          -> exit 2 + "--app yolu YOK"  (once: TEMIZ/exit 0)
  A2  ⭐ AYIRT EDICI  webapp/ YOK             -> exit 2 + "webapp/ dizini YOK"
  A3  ⭐ AYIRT EDICI  webapp var, 0 dosya     -> exit 2 + "OLCUM YOK" + "KAPSAM SIFIR"
  A4  ⭐ AYIRT EDICI  A1 ile A3 ciktilari FARKLI (eski kusur: bayt-birebir ayni)
  A5  FP capasi       dolu agac -> kapsam kabul edilir, payda N>0, "KAPSAM SIFIR" YOK
  A6  niteleyici      payda satiri kapsanan DESENLERI de yazar (Q232 ikinci ekseni)
  B1  ⭐ AYIRT EDICI  toplam=0 -> exit 1 + measured=false (once: [WARN] + exit 0)
  B2  FP capasi       gercek kosum -> sifir-dali GIRILMEZ + measured=true
  B3  ⭐ POZ.KONTROL  `enjekte edilen <N>` capasi duruyor (kardes korpus ona baglidir)
  C1  ⭐ AYIRT EDICI  izlenmeyen dosya varken -> satir ATLA + "IZLENMEYEN" (once: PASS)
  C2  FP capasi       temiz index + izlenmeyen YOK -> yine PASS (fix bunu bozmadi)
  C3  ⭐ POZ.KONTROL  gate rc=1 -> hala FAIL (uclu isaret gercek ihlali yutmadi)
  C4  3. BAGLAM      git OLMAYAN kok -> "PAYDA OLCULEMEDI" + ATLA (0 diye raporlamaz)
  C5  aritmetik      ATLA satiri PASS payina girmez ("N/M PASS · 1 ATLA")
  X1  ⭐ SINIR        ATLA cikis kodunu DEGISTIRMEZ (olcmemek ihlal degildir)
  X2  ⭐ SINIR        kapsam.py K1 karari duruyor: `kapsam_eki(0,..)` FAIL uretmez
  M1..M5             fix'i sok -> korpus KIRMIZI olmali

Kosum: python tests/fixtures/olcum_yoklugu_sozlesmesi/run.py          (exit 0 = PASS)
Kipler: --mutasyon-q232-sessiz · --mutasyon-q232-yol · --mutasyon-q254-warn ·
        --mutasyon-q250-atla   · --mutasyon-q250-payda
Kosucu: tests/run_fixture_tests.py (OZEL_TESTLER)
"""
from __future__ import annotations

import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
UI_ARAC = REPO / "scripts" / "check_ui_odata_refs.py"
HOOK_GATE = REPO / "scripts" / "validators" / "check_hook_injected_paths.py"
BATARYA = REPO / "tests" / "run_battery.py"
KAPSAM_MOD = REPO / "scripts" / "utils" / "kapsam.py"

# ⛔ BILINMEYEN KIP SESSIZCE YESIL GECMESIN (negatif_test_harness sozlesmesi).
GECERLI_KIP = {"--mutasyon-q232-sessiz", "--mutasyon-q232-yol", "--mutasyon-q254-warn",
               "--mutasyon-q250-atla", "--mutasyon-q250-payda"}
for _a in sys.argv[1:]:
    if _a not in GECERLI_KIP:
        print(f"[DURDU] bilinmeyen kip: {_a!r} — gecerli: {sorted(GECERLI_KIP)}")
        sys.exit(2)
KIP = set(sys.argv[1:])

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul), detay))


def dur(neden: str) -> None:
    """SAYI RAPORLAMADAN durus — kurulum sessiz basarisiz olamaz.

    ⚠ `KURULAMADI` != `KACTI`: batarya bu ikisini AYRI etiketler, cunku onarimlari
    ayridir (biri korpusu, oteki fix'i suclar).
    """
    print(f"[DURDU] KURULAMADI: {neden}")
    sys.exit(2)


# ══════════════════════════════════════════════════════════════════════════════
# MUTASYON — BUGUNKU kaynaktan turetilir (pinli SHA / `git show` YOK: bu korpusun
# koruduğu fix bu daldadir; tabana bagli capalar merge aninda bayatlar).
# Her desen TAM 1 kez bulunmali; bulunamazsa `KURULAMADI` (sessiz kacak yok).
# ══════════════════════════════════════════════════════════════════════════════
MUTASYONLAR: dict[str, tuple[Path, str, str]] = {
    # Q232: 0 dosya yine "TEMIZ" + exit 0 desin (kusurun BIREBIR eski hali)
    "--mutasyon-q232-sessiz": (
        UI_ARAC,
        '        print("\\nOLCUM YOK — \'TEMIZ\' DEGIL: webapp/ var ama taranacak dosya bulunamadi.")',
        '        print("\\nTEMIZ"); sys.exit(0)  # MUTASYON'),
    # Q232: cozulmeyen `--app` yolu yine SESSIZ gecsin
    "--mutasyon-q232-yol": (
        UI_ARAC,
        "def kapsam_dogrula(app):",
        "def kapsam_dogrula(app):\n    return  # MUTASYON"),
    # Q254: payda 0 iken yine yesil donsun
    "--mutasyon-q254-warn": (
        HOOK_GATE,
        '        print("         hiçbir checklist tetiklemiyor · STDERR_PAYLOADLARI bayatladı.")\n'
        "        return 1",
        '        print("         hiçbir checklist tetiklemiyor · STDERR_PAYLOADLARI bayatladı.")\n'
        "        return 0  # MUTASYON"),
    # Q250: ATLA yine PASS diye okunsun (uclu isaret sokulur)
    "--mutasyon-q250-atla": (
        BATARYA,
        '        isaret = "PASS" if ok is True else ("FAIL" if ok is False else "ATLA")',
        '        isaret = "PASS" if ok is not False else "FAIL"  # MUTASYON'),
    # Q250: payda hic olculmesin (izlenmeyen dosyalar yine gorunmez olsun)
    "--mutasyon-q250-payda": (
        BATARYA,
        "            izlenen, izlenmeyen = _precommit_paydasi(repo)",
        "            izlenen, izlenmeyen = 0, 0  # MUTASYON"),
}


def kaynak(dosya: Path) -> str:
    """Dosyanin BUGUNKU kaynagi + bu kosumda gecerli mutasyonlar uygulanmis hali."""
    if not dosya.is_file():
        dur(f"kaynak yok: {dosya}")
    metin = dosya.read_text(encoding="utf-8")
    for kip in sorted(KIP):
        hedef, eski, yeni = MUTASYONLAR[kip]
        if hedef != dosya:
            continue
        if metin.count(eski) != 1:
            dur(f"{kip}: capa {metin.count(eski)} kez bulundu (1 bekleniyor) — "
                f"{dosya.name} degisti, mutasyon BAYATLADI")
        metin = metin.replace(eski, yeni)
    return metin


TMP = tempfile.TemporaryDirectory(prefix="olcum_yoklugu_")
KOK = Path(TMP.name)


# ══════════════════════════════════════════════════════════════════════════════
# A — check_ui_odata_refs (Q232).  TAMAMEN CEVRIMDISI: kapsam karari artik
#     `fetch_metadata`dan ONCE verilir, dolayisiyla hicbir vektor aga gitmez.
# ══════════════════════════════════════════════════════════════════════════════
# Mutasyonlu kopya IZOLE bir agacta yasar — gercek kaynaga yazmak komsu korpuslari
# kirletir (kalinti BIRIKIR) ve bu korpusu tek-kullanimlik yapardi.
A_KOK = KOK / "a" / "scripts"
(A_KOK / "utils").mkdir(parents=True)
(A_KOK / "utils" / "__init__.py").write_text("", encoding="utf-8")
shutil.copyfile(KAPSAM_MOD, A_KOK / "utils" / "kapsam.py")
A_ARAC = A_KOK / "check_ui_odata_refs.py"
A_ARAC.write_text(kaynak(UI_ARAC), encoding="utf-8", newline="")


def ui_kos(app: Path | str) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(A_ARAC), "--app", str(app),
                        "--service", "ZORNEK_SRV"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


A_AGAC = KOK / "a" / "agac"
(A_AGAC / "yok_webapp").mkdir(parents=True)                       # webapp'i olmayan app
(A_AGAC / "bos_webapp" / "webapp" / "controller").mkdir(parents=True)   # 0 eslesen dosya
(A_AGAC / "bos_webapp" / "webapp" / "i18n").mkdir(parents=True)
(A_AGAC / "bos_webapp" / "webapp" / "i18n" / "i18n.properties").write_text(
    "title=x\n", encoding="utf-8")   # ⭐ KAPSAM DISI dosya: "dizin bos" ile karistirilmasin
_dolu = A_AGAC / "dolu" / "webapp"
(_dolu / "controller").mkdir(parents=True)
(_dolu / "view").mkdir(parents=True)
(_dolu / "controller" / "Main.controller.js").write_text(
    'sap.ui.define([], function(){ return { f: function(){ this.getModel().read("/ZORNEK_SET"); } }; });\n',
    encoding="utf-8")
(_dolu / "view" / "Main.view.xml").write_text(
    '<mvc:View xmlns:mvc="sap.ui.core.mvc"><Text text="{Alan}"/></mvc:View>\n', encoding="utf-8")

rc_yok, c_yok = ui_kos(A_AGAC / "hic_boyle_bir_dizin_yok")
kontrol("A1 ⭐ --app yolu YOK -> exit 2 + gorunur hata (once: TEMIZ + exit 0)",
        rc_yok == 2 and "--app yolu YOK" in c_yok and "OLCUM DEGILDIR" in c_yok,
        f"rc={rc_yok} cikti={c_yok.strip()[:160]!r}")

rc_nw, c_nw = ui_kos(A_AGAC / "yok_webapp")
kontrol("A2 ⭐ webapp/ YOK -> exit 2 (app dizini var diye olculmus sayilmaz)",
        rc_nw == 2 and "webapp/ dizini YOK" in c_nw,
        f"rc={rc_nw} cikti={c_nw.strip()[:160]!r}")

rc_bos, c_bos = ui_kos(A_AGAC / "bos_webapp")
kontrol("A3 ⭐ webapp var ama 0 eslesen dosya -> exit 2 + OLCUM YOK + KAPSAM SIFIR",
        rc_bos == 2 and "OLCUM YOK" in c_bos and "KAPSAM SIFIR" in c_bos,
        f"rc={rc_bos} cikti={c_bos.strip()[:200]!r}")

kontrol("A4 ⭐ 'yol yok' ile '0 dosya' ciktilari FARKLI "
        "(eski kusur: iki hal bayt-birebir AYNI okunuyordu)",
        c_yok.strip() != c_bos.strip(),
        f"esit_mi={c_yok.strip() == c_bos.strip()}")

# A5 FP capasi: dolu agacta kapsam KABUL edilir. Aga gidilecegi icin exit 2 OLMAMALI
# ve sifir-kapsam mesaji BASILMAMALI. (Ag yoksa arac baska bir yerde patlar — vektor
# "kapsam kapisindan GECTI mi" sorusunu olcer, "SAP'ye ulasti mi"yi degil.)
rc_dolu, c_dolu = ui_kos(A_AGAC / "dolu")
kontrol("A5 FP capasi: dolu agac kapsam kapisindan GECER (KAPSAM SIFIR yok, exit 2 yok)",
        "KAPSAM SIFIR" not in c_dolu and "OLCUM YOK" not in c_dolu
        and "--app yolu YOK" not in c_dolu,
        f"rc={rc_dolu} cikti={c_dolu.strip()[:200]!r}")

kontrol("A6 niteleyici: sifir-kapsam satiri KAPSANAN desenleri de yazar "
        "(Q232 ikinci ekseni — 'TEMIZ' kapsami oldugundan genis gosteriyordu)",
        "webapp/controller/*.js" in c_bos and "webapp/view/*.xml" in c_bos,
        f"cikti={c_bos.strip()[:200]!r}")


# ══════════════════════════════════════════════════════════════════════════════
# B — check_hook_injected_paths (Q254). Modul BELLEKTE calistirilir; `__file__`
#     GERCEK yola set edilir ki `parents[2]` core kokunu dogru cozsun (kopyalamak
#     zorunda kalmadan mutasyon uygulanabilsin).
# ══════════════════════════════════════════════════════════════════════════════
def gate_modulu():
    spec = importlib.util.spec_from_loader("_oy_gate", loader=None)
    mod = importlib.util.module_from_spec(spec)          # type: ignore[arg-type]
    mod.__file__ = str(HOOK_GATE)
    try:
        exec(compile(kaynak(HOOK_GATE), str(HOOK_GATE), "exec"), mod.__dict__)
    except Exception as exc:                              # kurulum hatasi != kacan mutasyon
        dur(f"gate modulu yuklenemedi: {exc!r}")
    return mod


def gate_kos(mod) -> tuple[int, str]:
    """main()'i cagir, stdout'u TAMPONLA yakala (CLI import'u stdout'u gasp eder)."""
    tampon = io.StringIO()
    yedek = sys.stdout
    sys.stdout = tampon
    try:
        rc = mod.main()
    finally:
        sys.stdout = yedek
    return int(rc), tampon.getvalue()

_G = gate_modulu()

# B1: PAYDAYI SIFIRLA — sondanin hicbir sey uretemedigi hali.
# ⚠ Sonda GERCEKCI bicimde sifirlanir: hook LISTESI bosaltilmaz, hook'lar KOSAR ama
#    BOS doner. Gerekce olculdu: listeyi bosaltmak `ThreadPoolExecutor(max_workers=0)`
#    ile ValueError atiyor — yani "kurulum coktu", "payda 0" DEGIL; o vektor kusuru
#    olcmez, korpusu coktururdu (COKTU != FAIL). Gercek kusur hook'larin bos donmesidir
#    (`_hook_ciktisi` rc!=0 / bos stdout hallerinde zaten "" dondurur).
# ⚠ Yama CAGRI aninda cozulur (main() globalden okur) — import-anindaki yan etkiye
#    gec kalma riski yok.
_eski = (_G._hook_ciktisi, _G._stderr_ciktisi)
_G._hook_ciktisi = lambda *a, **k: ""
_G._stderr_ciktisi = lambda *a, **k: ""
try:
    rc_sifir, c_sifir = gate_kos(_G)
finally:
    _G._hook_ciktisi, _G._stderr_ciktisi = _eski

kontrol("B1 ⭐ payda 0 -> exit 1 + measured=false beyani (once: [WARN] + exit 0)",
        rc_sifir == 1
        and "measured=false" in c_sifir
        and "status=FAIL" in c_sifir
        and "ÖLÇÜM YOK" in c_sifir,
        f"rc={rc_sifir} cikti={c_sifir.strip()[:200]!r}")

# B2 FP capasi: gercek kosum. ⚠ SONUC ORTAMA BAGLIDIR (bu agacta kirik yol
# olabilir/olmayabilir) -> vektor cikis koduna DEGIL, "sifir dalina girilmedi ve
# olcum BEYAN EDILDI"e bakar. Ortam-bagimli sayiya capalamak korpusu bayatlatirdi.
rc_ger, c_ger = gate_kos(_G)
kontrol("B2 FP capasi: gercek kosumda sifir-dali GIRILMEZ + measured=true beyan edilir",
        "ÖLÇÜM YOK" not in c_ger and "measured=true" in c_ger,
        f"rc={rc_ger} cikti={c_ger.strip()[:200]!r}")

kontrol("B3 ⭐ POZ.KONTROL: `enjekte edilen <N>` capasi duruyor "
        "(kardes korpus hook_bash_ve_stderr_kapsami B1b/B2 ONA baglidir)",
        bool(re.search(r"enjekte edilen (\d+)", c_ger)),
        f"cikti={c_ger.strip()[:200]!r}")


# ══════════════════════════════════════════════════════════════════════════════
# C — run_battery --precommit (Q250). Sentetik KUM repolar; gercek core_precommit
#     KOSTURULMAZ (68 s surer ve bu korpusun konusu RAPORLAMA, kapinin kendisi degil).
# ══════════════════════════════════════════════════════════════════════════════
C_ARAC = KOK / "run_battery_test.py"
C_ARAC.write_text(kaynak(BATARYA), encoding="utf-8", newline="")


def kum_repo(ad: str, gate_rc: int, izlenmeyen: bool, git: bool = True) -> Path:
    kum = KOK / "kum" / ad
    (kum / "tests" / "fixtures" / "kipsiz").mkdir(parents=True)
    (kum / "tests" / "fixtures" / "kipsiz" / "run.py").write_text(
        "import sys\nprint('1/1 OK')\nsys.exit(0)\n", encoding="utf-8")
    (kum / "scripts" / "git-hooks").mkdir(parents=True)
    (kum / "scripts" / "git-hooks" / "core_precommit.py").write_text(
        f"import sys\nprint('sahte gate')\nsys.exit({gate_rc})\n", encoding="utf-8")
    # ⭐ ORTAM DA KOPYALANIR: gercek repoda `.tmp/` GITIGNORE'LUDUR (olculdu:
    #    `git check-ignore .tmp/battery/...` rc=0). Batarya ham ciktilarini oraya
    #    yazar; .gitignore'suz bir kumda kendi artefakti "izlenmeyen dosya" diye
    #    sayilir ve C2 (mesru yesil) SAHTE-KIRMIZI olurdu — kusur degil, kum eksigi.
    (kum / ".gitignore").write_text(".tmp/\n", encoding="utf-8")
    if git:
        for arg in (["init", "-q"], ["add", "-A"],
                    ["-c", "user.email=t@example.com", "-c", "user.name=t",
                     "commit", "-qm", "taban"]):
            r = subprocess.run(["git", *arg], cwd=str(kum), capture_output=True, text=True)
            if r.returncode != 0 and arg[0] != "-c":
                dur(f"git {arg[0]} basarisiz ({ad}): {r.stderr[:120]}")
    if izlenmeyen:
        (kum / "yeni_izlenmeyen_dosya.py").write_text("x = 1\n", encoding="utf-8")
    return kum


def batarya_kos(kum: Path) -> tuple[int, str]:
    env = os.environ.copy()
    env.pop("CLAUDE_PROJECT_DIR", None)
    env["PYTHONUTF8"] = "1"
    p = subprocess.run([sys.executable, str(C_ARAC), "kipsiz", "--precommit",
                        "--repo", str(kum)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env, timeout=300)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def kapi_satiri(cikti: str) -> str:
    for s in cikti.splitlines():
        if "core_precommit" in s and ("PASS" in s or "FAIL" in s or "ATLA" in s):
            return s
    return ""


rc_c1, c_c1 = batarya_kos(kum_repo("izlenmeyenli", 0, izlenmeyen=True))
s_c1 = kapi_satiri(c_c1)
kontrol("C1 ⭐ izlenmeyen dosya varken kapi satiri ATLA + IZLENMEYEN "
        "(once: OK(rc=0) ... PASS — sahte-yesil KAPI TABLOSUNUN ICINDE)",
        s_c1.rstrip().endswith("ATLA") and "IZLENMEYEN" in s_c1,
        f"satir={s_c1.strip()!r}")

kontrol("X1 ⭐ SINIR: ATLA cikis kodunu DEGISTIRMEZ (olcmemek bir ihlal degildir; "
        "aksi halde arac isin normal ortasinda kullanilamaz olurdu)",
        rc_c1 == 0, f"rc={rc_c1}")

kontrol("C5 aritmetik: ATLA satiri PASS payina GIRMEZ (TOPLAM satiri ayri sayar)",
        "ATLA (OLCULMEDI)" in c_c1 and "2/2 PASS" not in c_c1,
        f"toplam={[x for x in c_c1.splitlines() if x.startswith('TOPLAM')]}")

rc_c2, c_c2 = batarya_kos(kum_repo("temiz", 0, izlenmeyen=False))
s_c2 = kapi_satiri(c_c2)
kontrol("C2 FP capasi: izlenmeyen YOK + gate rc=0 -> yine PASS "
        "(duzeltme mesru yesili BOZMAMALI)",
        s_c2.rstrip().endswith("PASS") and "IZLENMEYEN" not in s_c2 and rc_c2 == 0,
        f"rc={rc_c2} satir={s_c2.strip()!r}")

rc_c3, c_c3 = batarya_kos(kum_repo("ihlalli", 1, izlenmeyen=False))
s_c3 = kapi_satiri(c_c3)
kontrol("C3 ⭐ POZ.KONTROL: gate rc=1 -> hala FAIL + exit 1 "
        "(uclu isaret GERCEK ihlali yutmadi)",
        s_c3.rstrip().endswith("FAIL") and rc_c3 == 1,
        f"rc={rc_c3} satir={s_c3.strip()!r}")

rc_c4, c_c4 = batarya_kos(kum_repo("gitsiz", 0, izlenmeyen=False, git=False))
s_c4 = kapi_satiri(c_c4)
kontrol("C4 3.BAGLAM: git OLMAYAN kok -> 'PAYDA OLCULEMEDI' + ATLA "
        "(olculemeyen payda '0' diye raporlanmaz)",
        "PAYDA OLCULEMEDI" in s_c4 and s_c4.rstrip().endswith("ATLA"),
        f"satir={s_c4.strip()!r}")


# ══════════════════════════════════════════════════════════════════════════════
# X2 — SINIR: kapsam.py K1 karari DURUYOR (bu tur onu TERSINE CEVIRMEDI)
# ══════════════════════════════════════════════════════════════════════════════
# ⚠ Bu vektor SILINEMEZ. Turun yonu "sikilastirma" oldugu icin, birileri gunun
# birinde `kapsam_eki(0,..)`yi de FAIL'e cevirmek isteyebilir — o an kapsami MESRU
# sekilde bos olan her projede kalici kirmizi doğar. Sinir burada civilidir.
sys.path.insert(0, str(REPO / "scripts"))
from utils.kapsam import kapsam_eki  # type: ignore  # noqa: E402

_sifir = kapsam_eki(0, ".bdef")
_dolu_ek = kapsam_eki(5, ".bdef")
# ⚠ CAPA "FAIL kelimesi gecmesin" DEGILDIR — metin zaten "bu bir FAIL degil" diyor;
#   oyle bir capa kendi kendini yalanlardi. Capa METNIN HUKMUDUR: sifir kapsam
#   (a) "ihlal yok" diye okunmamali, (b) acikca FAIL OLMADIGI soylenmeli.
kontrol("X2 ⭐ SINIR: kapsam_eki(0,..) GORUNUR uyari basar ama bir FAIL sinyali DEGIL "
        "(K1 karari: sifir kapsam mesru olabilir; kapatilan sey SESSIZLIKTIR)",
        "KAPSAM SIFIR" in _sifir
        and "BAKILACAK DOSYA BULUNAMADI" in _sifir
        and "FAIL değil" in _sifir
        and _dolu_ek.strip() == "(5 .bdef tarandı)",
        f"sifir={_sifir[:90]!r} dolu={_dolu_ek!r}")


# ══════════════════════════════════════════════════════════════════════════════
print()
gecen = sum(1 for _, ok, _ in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + (f" -- {detay}" if (detay and not ok) else ""))
mod = f"  (kip: {' '.join(sorted(KIP))})" if KIP else ""
print(f"\n{gecen}/{len(SONUC)} OK{mod}")
TMP.cleanup()
sys.exit(0 if gecen == len(SONUC) else 1)
