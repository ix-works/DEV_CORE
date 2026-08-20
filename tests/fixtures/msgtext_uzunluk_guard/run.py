#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""populate_message_class: T100-TEXT (CHAR 73) uzunluk guard'i YOKTU (sessiz-veri-bozan).

KOK: script CSV'den okudugu `msgtext`i uzunluk denetimi YAPMADAN XML govdesine koyup
PUT ediyordu. `DD03L` -> T100-TEXT = CHAR 73. Sinir asilinca iki sonuc var, ikisi de
kotu: ya cagri duser, ya SAP metni SESSIZCE KIRPAR. Kirpilan mesaj ekranda YARIM
CUMLEDIR ve "onayli metin buydu" diye kimse suphelenmez -> hata, dogdugu yerde degil
KULLANICININ EKRANINDA belirir. Olculmus vaka (2026-08-20): onayli 143 metnin 14'u
siniri asiyordu (en uzunu 94); arac sayesinde DEGIL, CSV ureticisinin kendi kontrolu
sayesinde yakalandi.

FIX: guard `load_messages_from_csv` icinde, yani URETIM NOKTASINDA (main()'e konsaydi
fonksiyonu dogrudan import eden cagiran atlardi). Asan satir varsa `MesajMetniUzunError`
firlatir -> CSRF/LOCK/PUT'a HIC gidilmez ve TUM ihlaller tek seferde raporlanir.

Bu korpus S(enaryo) + M(utasyon) tasir:
  S1-S2  uc-baglam: bilinen-BOZUK yakalanir / bilinen-TEMIZ gecer
  S3-S4  esik ikizi: tam 73 PASS · 74 FAIL (off-by-one capasi)
  S5     3. BAGLAM — BAYT != KARAKTER: 73 karakter ama >73 bayt diakritikli metin GECMELI
  S6     3. BAGLAM — atlanan satir (msgno bos): guard tetiklenmemeli
  S7-S8  GERCEK GIRIS NOKTASI (main + --dry-run): bozuk -> rc=1 ve XML'e HIC ulasilmaz /
         temiz -> rc=0 ve XML uretilir (FP capasi, S7'den AYRI tutulur)
  M1-M3  fix'i sok -> korpus KIRMIZI olmali (yesil kalirsa korpus o degismezi olcmuyor)

Kosum: python tests/fixtures/msgtext_uzunluk_guard/run.py     (exit 0 = PASS)
"""
from __future__ import annotations

import io
import sys
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[2]
SCRIPTS = CORE / "scripts"
PMC_PATH = SCRIPTS / "populate_message_class.py"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

_mod_refs: list = []   # GC-koruma: modulun kurdugu stdout wrapper'lari


class _SahteClient:
    """SAPADTClient yerine gecer. HERHANGI bir kullanimi kaydeder.

    Amac cift yonlu: (a) korpus SAP'siz kossun, (b) "yazmaya HIC gidilmedi"
    iddiasi OLCULEBILIR olsun -- `dokunuldu` bos kalmali.
    """

    def __init__(self, *a, **k):
        self.dokunuldu: list[str] = []

    def __getattr__(self, ad):
        self.dokunuldu.append(ad)
        raise AssertionError(
            "SAP yuzeyine dokunuldu (%r) — guard yazma baslamadan durdurmaliydi" % ad
        )


def load(mut=None):
    """populate_message_class'i TAZE namespace'e yukler; mutasyon KAYNAK METNINE uygulanir.

    ⚠ Modul import aninda `io.TextIOWrapper(sys.stdout.buffer)` kurar (win32 dali).
    Sadece sys.stdout'u geri koymak YETMEZ: o wrapper GC'ye girince sardigi GERCEK
    buffer'i KAPATIR -> sonraki print "I/O operation on closed file" ile patlar
    (kardes fixture'da olculdu, B22). Bu yuzden import sirasinda stdout'u ATILABILIR
    bir BytesIO'ya bagliyoruz; gercek stdout'a hic dokunulmaz.
    """
    src = PMC_PATH.read_text(encoding="utf-8")
    if mut:
        src = mut(src)

    saved_out, saved_err = sys.stdout, sys.stderr
    cop_out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    cop_err = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    sys.stdout, sys.stderr = cop_out, cop_err
    try:
        mod = types.ModuleType("populate_message_class")
        mod.__file__ = str(PMC_PATH)
        exec(compile(src, str(PMC_PATH), "exec"), mod.__dict__)
    finally:
        sys.stdout, sys.stderr = saved_out, saved_err
        _mod_refs.append((cop_out, cop_err))
    return mod


def csv_yaz(tmp: Path, ad: str, satirlar: list[tuple[str, str]]) -> Path:
    """satirlar = [(msgno, msgtext), ...] -> UTF-8 CSV dosyasi."""
    p = tmp / ad
    govde = ["msgno,msgtext,selfexplainatory"]
    govde += ['%s,"%s",false' % (n, t.replace('"', '""')) for n, t in satirlar]
    p.write_text("\n".join(govde) + "\n", encoding="utf-8")
    return p


def main_calistir(mod, csv_path: Path) -> tuple[int, str]:
    """GERCEK giris noktasi: main() + --dry-run. (rc, yakalanan_cikti) doner.

    --dry-run bilerek: temiz CSV'de PUT'a gitmeden XML onizlemesi basar, yani
    "guard'a takilmadan payload'a ULASTI" izi olculebilir olur.
    """
    argv = sys.argv[:]
    saved_out = sys.stdout
    tut = io.StringIO()
    sys.argv = [
        "populate_message_class.py",
        "--name", "ZSD001",
        "--package", "ZSD001_CLC",
        "--transport", "<TRANSPORT>",
        "--description", "Test",
        "--messages-csv", str(csv_path),
        "--dry-run",
    ]
    sahte = _SahteClient()
    mod.SAPADTClient = lambda *a, **k: sahte
    sys.stdout = tut
    try:
        rc = mod.main()
    finally:
        sys.stdout = saved_out
        sys.argv = argv
    return rc, tut.getvalue()


# ---------------------------------------------------------------------------
# Sekiller — adlar jenerik (ZSD001 = core placeholder)
# ---------------------------------------------------------------------------
TAM73 = "A" * 73
ASAN74 = "B" * 74
# 73 KARAKTER ama utf-8'de 73'ten FAZLA BAYT (her 'ı'/'ş'/'ğ' 2 bayt).
# Bayt olcen bir guard bunu yanlis-pozitif yakalardi; karakter olcen gecirmeli.
DIAKRITIK73 = ("şığüöç" * 12) + "A"          # 12*6 + 1 = 73 karakter


def senaryolar(mod, tmp: Path) -> list[tuple[str, bool, str]]:
    out = []

    def ekle(ad, kosul, detay=""):
        out.append((ad, bool(kosul), detay))

    Hata = mod.MesajMetniUzunError

    # --- S1: bilinen-BOZUK -> yakalanir + TUM ihlaller raporlanir -------------
    p = csv_yaz(tmp, "bozuk.csv", [
        ("001", "X" * 80), ("002", "kisa metin"), ("003", "Y" * 94), ("004", "Z" * 74),
    ])
    try:
        mod.load_messages_from_csv(p)
        ekle("S1 bozuk CSV yakalanir", False, "hata FIRLATILMADI")
    except Hata as e:
        metin = str(e)
        # Ayirt edici: UC ihlalin UCU de raporda. Biri eksikse yazar CSV'yi
        # tur tur duzeltmek zorunda kalir (fix'in acik tasarim karari).
        hepsi = all(("msgno=%s" % n) in metin for n in ("001", "003", "004"))
        temiz_yok = "msgno=002" not in metin
        ekle("S1 bozuk CSV yakalanir + 3 ihlalin 3'u raporlanir",
             hepsi and temiz_yok,
             "hepsi=%s temiz_disarida=%s" % (hepsi, temiz_yok))

    # --- S2: bilinen-TEMIZ -> gecer (FP capasi) ------------------------------
    p = csv_yaz(tmp, "temiz.csv", [("001", "Kisa mesaj"), ("002", "Bir digeri")])
    try:
        msgs = mod.load_messages_from_csv(p)
        ekle("S2 temiz CSV gecer (2 mesaj)", len(msgs) == 2, "gorulen=%d" % len(msgs))
    except Hata as e:
        ekle("S2 temiz CSV gecer (2 mesaj)", False, "beklenmedik hata: %s" % e)

    # --- S3/S4: esik ikizi ---------------------------------------------------
    p = csv_yaz(tmp, "tam73.csv", [("001", TAM73)])
    try:
        mod.load_messages_from_csv(p)
        ekle("S3 tam 73 karakter PASS", True)
    except Hata:
        ekle("S3 tam 73 karakter PASS", False, "73 karakter yanlis-pozitif yakalandi")

    p = csv_yaz(tmp, "asan74.csv", [("001", ASAN74)])
    try:
        mod.load_messages_from_csv(p)
        ekle("S4 74 karakter FAIL", False, "74 karakter KACTI")
    except Hata:
        ekle("S4 74 karakter FAIL", True)

    # --- S5: 3. BAGLAM — bayt != karakter ------------------------------------
    bayt = len(DIAKRITIK73.encode("utf-8"))
    p = csv_yaz(tmp, "diakritik.csv", [("001", DIAKRITIK73)])
    try:
        mod.load_messages_from_csv(p)
        ekle("S5 3.baglam: 73 karakter / %d bayt diakritikli metin PASS" % bayt,
             len(DIAKRITIK73) == 73 and bayt > 73,
             "karakter=%d bayt=%d" % (len(DIAKRITIK73), bayt))
    except Hata:
        ekle("S5 3.baglam: 73 karakter / %d bayt diakritikli metin PASS" % bayt,
             False, "BAYT olcen guard yanlis-pozitif verdi")

    # --- S6: 3. BAGLAM — AYRISTIRILMIS alan olculur, HAM SATIR degil ---------
    # Virgul + tirnak tasiyan bir metin: ham CSV satiri 73'u ASAR ama `msgtext`
    # alani 70 karakterdir. Satir-uzunlugu olcen naif bir guard burada yanlis-pozitif
    # verirdi; alan-uzunlugu olcen gecirmeli. (Ayrica CSV ayristirmasinin dogru
    # yerde yapildiginin kaniti: 'X,"a,b""c",false' tek alandir.)
    metin70 = 'Musteri, siparis ve teslimat kontrolu: "acil" kaydi gozden gecir'  # < 73
    metin70 = metin70 + "." * (70 - len(metin70)) if len(metin70) < 70 else metin70[:70]
    p = csv_yaz(tmp, "virgullu.csv", [("001", metin70)])
    ham_satir_uz = max(len(s) for s in p.read_text(encoding="utf-8").splitlines())
    try:
        msgs = mod.load_messages_from_csv(p)
        ekle("S6 3.baglam: ham satir %d > 73, alan %d <= 73 -> PASS"
             % (ham_satir_uz, len(metin70)),
             len(msgs) == 1 and ham_satir_uz > 73 and len(metin70) <= 73,
             "mesaj=%d ham=%d alan=%d" % (len(msgs), ham_satir_uz, len(metin70)))
    except Hata:
        ekle("S6 3.baglam: ham satir %d > 73, alan %d <= 73 -> PASS"
             % (ham_satir_uz, len(metin70)),
             False, "SATIR uzunlugu olcen guard yanlis-pozitif verdi")

    # --- S7: GERCEK giris noktasi, bozuk -> rc=1 + XML'e HIC ulasilmaz -------
    p = csv_yaz(tmp, "main_bozuk.csv", [("001", "X" * 90)])
    rc, cikti = main_calistir(mod, p)
    xml_yok = "mc:messageClass" not in cikti and "DRY-RUN" not in cikti
    ekle("S7 main(--dry-run) bozuk: rc=1 ve payload'a HIC ulasilmaz",
         rc == 1 and xml_yok, "rc=%s xml_uretilmedi=%s" % (rc, xml_yok))

    # --- S8: FP capasi — AYRI vektor (S7 ile birlestirilmez) -----------------
    p = csv_yaz(tmp, "main_temiz.csv", [("001", "Kisa mesaj")])
    rc, cikti = main_calistir(mod, p)
    xml_var = "mc:messageClass" in cikti
    ekle("S8 main(--dry-run) temiz: rc=0 ve XML URETILIR",
         rc == 0 and xml_var, "rc=%s xml_uretildi=%s" % (rc, xml_var))

    return out


# ---------------------------------------------------------------------------
# MUTASYONLAR — kaynagin BUGUNKU metnine uygulanir (git ref'i YOK: "fix merge
# olunca taban kayar" tuzagi yapisal olarak yok). Uc degismez -> uc mutasyon.
# ---------------------------------------------------------------------------
MUTASYONLAR = [
    ("M1 guard'i tumden sok (tespit degismezi)",
     lambda s: s.replace("                if len(msgtext) > T100_TEXT_MAXLEN:",
                         "                if False:")),
    ("M2 yalniz ILK ihlali raporla (tamlik degismezi)",
     lambda s: s.replace("            for sn, mn, uz, mt in asanlar\n",
                         "            for sn, mn, uz, mt in asanlar[:1]\n")),
    ("M3 esigi gevset 73 -> 200 (deger degismezi)",
     lambda s: s.replace("T100_TEXT_MAXLEN = 73", "T100_TEXT_MAXLEN = 200")),
]


def main() -> int:
    import tempfile

    print("=" * 78)
    print("msgtext_uzunluk_guard — T100-TEXT (CHAR 73) fail-closed korpusu")
    print("=" * 78)

    tmp = Path(tempfile.mkdtemp(prefix="msgtext_guard_"))

    mod = load()
    sonuc = senaryolar(mod, tmp)
    kirik = [(a, d) for a, ok, d in sonuc if not ok]
    for ad, ok, detay in sonuc:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok:
            print("         gorulen: %s" % detay)
    print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

    print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
    mut_kirik = []
    for ad, mut in MUTASYONLAR:
        try:
            m_mod = load(mut=mut)
            m_res = senaryolar(m_mod, tmp)
            yakalandi = any(not ok for _, ok, _ in m_res)
            kacan = [a for a, ok, _ in m_res if not ok]
        except BaseException as e:   # cokme != FAIL: ayirt edilebilir kalsin
            yakalandi, kacan = True, ["yukleme hatasi: %s" % type(e).__name__]
        print("  [%s] %s" % ("YAKALANDI" if yakalandi else "KACTI", ad))
        if yakalandi:
            print("         kiran senaryo(lar): %s" % ", ".join(kacan[:3]))
        else:
            mut_kirik.append(ad)

    # Mutasyonun GERCEKTEN uygulandigini kanitla (yama tutmazsa sahte-YESIL olur)
    print("\n--- yama-tuttu kanidi ---")
    ham = PMC_PATH.read_text(encoding="utf-8")
    yama_kirik = []
    for ad, mut in MUTASYONLAR:
        degisti = mut(ham) != ham
        print("  [%s] %s" % ("degisti" if degisti else "YAMA TUTMADI", ad))
        if not degisti:
            yama_kirik.append(ad)

    print("\n" + "=" * 78)
    if kirik or mut_kirik or yama_kirik:
        if kirik:
            print("FAIL — senaryo: %s" % ", ".join(a for a, _ in kirik))
        if mut_kirik:
            print("FAIL — mutasyon KACTI (korpus bu degismezi olcmuyor): %s" % ", ".join(mut_kirik))
        if yama_kirik:
            print("FAIL — mutasyon yamasi kaynaga UYMADI (sahte-yesil riski): %s" % ", ".join(yama_kirik))
        return 1
    print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(MUTASYONLAR)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
