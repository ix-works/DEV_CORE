#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fixture — hook parse-fail dalının GÖRÜNÜRLÜĞÜ (kök-fix 2026-08-13).

**Sınıf:** stdin'den JSON okuyan hook'lar bozuk girdide `except: return 0`/`data = {}` ile
fail-safe davranır. 2026-08-13'e kadar bu dal **SESSİZDİ** ⇒ *"guard bu payload'ı GEÇİRDİ"*
ile *"guard payload'ı HİÇ OKUYAMADI"* aynı çıktıyı üretiyordu ve ikincisi düzenli olarak
"guard bypass edildi" diye raporlanıyordu. Tetikleyici tuzak: elle yazılan `\\` kabuğa tek
`\` olarak ulaşır → JSON'da geçersiz escape → parse-fail → 0.

**Kök-fix:** `exit 0` **KORUNUR** (fail-safe bilinçli: bozuk/yabancı girdi hiçbir aracı
bloklamamalı); yalnız sessizlik kalkar — stderr'e `GIRDI-PARSE-EDILEMEDI` notu basılır.
Not **DAİMA stderr'e** gider: hook'ların bir kısmı stdout'a JSON sözleşmesi basar ve
harness onu PARSE eder; stdout'a tek bayt sızıntı sözleşmeyi kırar (V14/V15 bunu ölçer).

⚠ **Gösterim harness'a bağlıdır.** Bu korpus stderr'in kullanıcıya NASIL gösterildiğini
iddia ETMEZ (ölçülemez); sözleşme yalnız **stderr'de notun VARLIĞI**dır.

**Bu korpus neyi çivilliyor:** (a) guard'ın gerçekten yaşadığı (FP çapaları V1-V4),
(b) exit-0 fail-safe'inin KORUNDUĞU (V5), (c) bozuk girdinin meşru-serbestten artık
AYIRT EDİLEBİLİR olduğu (V6/V7), (d) bunun tek hook'un vakası değil SINIF olduğu
(V8/V9 + V13 tüm hook'lar, İÇ KONTROL GRUBU'yla), (e) stdout sözleşmesinin
KİRLENMEDİĞİ (V14/V15), (f) sınıfın sessizce yeniden büyüyemeyeceği (V16),
(g) uyarının üç dokümanda DURDUĞU (V12).

⚠ **Taşıyıcılar arası exit EŞİTLİĞİ assert EDİLMEZ** — ölçüldü ki ortam-bağımlıdır
(2026-08-13, iki bağımsız koşum zıt sonuç verdi; §D bloğundaki nota bak). Taşıyıcı
exit'leri BİLGİ olarak basılır, hükme esas alınmaz.

Vektör numaraları KİMLİKTİR, sıra değil: **V11 bilerek BOŞTUR** (eski "PS borusu bash ile
aynı exit'i verir" vektörü ortam-bağımlı çıkınca kaldırıldı; kalanlar yeniden numaralanmadı
ki dokümandaki atıflar kaymasın).

Koşum:  python tests/fixtures/negatif_test_harness/run.py
MUTASYON — İKİ AYRI DEĞİŞMEZ, ikisi de koşulmalı (biri diğerini kapsamaz):
  --mutasyon         → stdin fail-safe'i `return 0` → `return 2` (EXIT değişmezi)
  --mutasyon-notsuz  → `_parse_fail_notu()` çağrısı → `pass`  (NOT değişmezi = fix'in sökümü)
Mutasyon git ref'inden DEĞİL, BUGÜNKÜ kaynaktan üretilir — "fix merge olunca taban kayar"
tuzağı (B20 dersi) bu korpusta yapısal olarak yoktur. Desen bulunamazsa koşucu SAYI
RAPORLAMADAN durur (sahte-yeşil yerine görünür duruş).
"""
from __future__ import annotations

import json
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

REPO = Path(__file__).resolve().parents[3]
HOOKS = REPO / "scripts" / "hooks"
MUTASYON = "--mutasyon" in sys.argv
MUTASYON_NOTSUZ = "--mutasyon-notsuz" in sys.argv

# Parse-fail notunun makine-okunur çapası. ASCII: hook'ların bir kısmında stderr'in utf-8
# sarmalayıcısı win32'ye koşulludur; Türkçe harf cp1252/locale'de UnicodeEncodeError → exit 1
# üretip fail-safe'i BOZARDI (C-ENC-01 sınıfı). Bu yüzden hem not hem çapa ASCII.
TOKEN = "GIRDI-PARSE-EDILEMEDI"

# Guard'ın SAP-kullanıcı desenini tetikleyen sentetik iz. Parça parça kurulur: bu dosya
# core'a commit'lenir ve düz yazılsa kendi GENERICIZE-LEAK gate'imize takılırdı.
IZ = "D_" + "TESTUSR"

# ── SINIF KAYDI: stdin'den JSON okuyan HER hook + not BEKLENİYOR mu (+ beklenmiyorsa NEDEN)
# `not_bekleniyor=False` olanlar İÇ KONTROL GRUBUDUR: V13'ü "her yerde token ara" gibi
# trivial bir vektör olmaktan çıkarır (gate gevşerse fixture boşalır dersi).
HOOK_KAYDI: list[tuple[str, bool, str]] = [
    ("config_change_guard.py", True, ""),
    ("infra_write_guard.py", True, ""),
    ("instructions_loaded_log.py", True, ""),
    ("intake_triage.py", True, ""),
    ("itg_backstop.py", True, ""),
    ("post_tool_failure.py", True, ""),
    ("post_validate.py", True, ""),
    ("pre_tool_guard.py", True, ""),
    ("pull_before_edit.py", True, ""),
    ("recall_inject.py", True, ""),
    ("sap_worktype_hint.py", True, ""),
    ("session_start.py", True, ""),
    ("skill_injector.py", True, ""),
    ("watchdog_launch.py", True, ""),
    ("watchdog_stop.py", True, ""),
    # ── KAPSAM DIŞI (bilinçli): stdin yalnızca BOŞALTILIR, hiçbir karara girmez →
    #    parse-fail'de KAYBOLAN bir şey yok, not gürültü olurdu.
    ("pre_compact.py", False, "stdin bosaltilir; mesaj statik"),
    ("tooling_radar_check.py", False, "nudge'lar dosya tazeliginden; payload karara girmez"),
]

SONUC: list[tuple[bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((bool(kosul), f"{ad}{(' -> ' + detay) if detay else ''}"))


def kos(hook: Path, govde: bytes) -> tuple[int, str]:
    """Payload'ı BAYT olarak verir — kabuk/echo katmanı bilinçli olarak devre dışı."""
    r = subprocess.run([sys.executable, str(hook)], input=govde, capture_output=True)
    return r.returncode, r.stderr.decode("utf-8", errors="replace")


def kos_tam(hook: Path, govde: bytes) -> tuple[int, bytes, str]:
    """stdout'u BAYT olarak da döndürür (sözleşme kirlenmesi bayt düzeyinde ölçülür)."""
    r = subprocess.run([sys.executable, str(hook)], input=govde, capture_output=True)
    return r.returncode, r.stdout, r.stderr.decode("utf-8", errors="replace")


def _oku(p: Path) -> str:
    """BOM'a bakarak çöz — kabuklar yönlendirilmiş akışı farklı kodlamalarla yazar."""
    if not p.exists():
        return ""
    ham = p.read_bytes()
    for bom, kod in ((b"\xff\xfe", "utf-16-le"), (b"\xfe\xff", "utf-16-be"),
                     (b"\xef\xbb\xbf", "utf-8-sig")):
        if ham.startswith(bom):
            return ham.decode(kod, errors="replace")
    return ham.decode("utf-8", errors="replace")


def payload(yol: str, icerik: str) -> bytes:
    return json.dumps({"tool_name": "Write",
                       "tool_input": {"file_path": yol, "content": icerik}}).encode()


# Tek `\I` = geçersiz JSON escape; elle yazılan `\\`nin kabuktan sonraki hali.
BOZUK = ('{"tool_name":"Write","tool_input":{"file_path":"C:\\IX\\d.md",'
         '"content":"kullanici ' + IZ + '"}}').encode()


def mutant_exit(kaynak: Path) -> Path | None:
    """EXIT değişmezi mutasyonu: stdin fail-safe'inin `return 0`ını `return 2` yapar.

    Çapa DAR tutulur: dosyadaki ilk `except Exception: return 0`ı vurmak pre_tool_guard'da
    ALAKASIZ bir yardımcıyı bozup koşucuyu ÇÖKERTİYORDU — ve çökme, FAIL gibi okunuyordu.
    `data = {}` ile devam eden hook'larda bu çapa YOKTUR → None (o hook bu mutasyonun
    kapsamında değildir; NOT değişmezini `--mutasyon-notsuz` ölçer).
    """
    satirlar = kaynak.read_text(encoding="utf-8").splitlines(keepends=True)
    bas = next((i for i, s in enumerate(satirlar)
                if "json.load" in s and "sys.stdin" in s), None)
    if bas is None:
        return None
    for i in range(bas + 1, min(bas + 6, len(satirlar))):
        if re.match(r"^\s*return 0\b", satirlar[i]):
            satirlar[i] = satirlar[i].replace("return 0", "return 2", 1)
            h = kaynak.with_name("_mutant_" + kaynak.name)
            h.write_text("".join(satirlar), encoding="utf-8")
            return h
    return None


def mutant_notsuz(kaynak: Path) -> Path | None:
    """NOT değişmezi mutasyonu = FİX'İN SÖKÜMÜ: `_parse_fail_notu()` çağrısı → `pass`.

    Yalnız ÇAĞRI sökülür (tanım kalır): davranışsal fark tam olarak "not basılıyor mu".
    Çağrı yoksa None → çağıran bunu "fix zaten yok" diye ele alır.
    """
    ham = kaynak.read_text(encoding="utf-8")
    yeni, adet = re.subn(r"^(\s*)_parse_fail_notu\(\)\s*$", r"\1pass",
                         ham, flags=re.MULTILINE)
    if not adet:
        return None
    h = kaynak.with_name("_notsuz_" + kaynak.name)
    h.write_text(yeni, encoding="utf-8")
    return h


def main() -> int:
    if MUTASYON and MUTASYON_NOTSUZ:
        raise SystemExit("[KULLANIM] iki mutasyon aynı anda koşulmaz — değişmezler ayrı ölçülür.")
    tmp = Path(tempfile.mkdtemp(prefix="neg_harness_"))
    uretilen: list[Path] = []

    def coz(ad: str) -> Path:
        """Koşulacak dosyayı verir: mutasyon modunda mutant, değilse orijinal."""
        asil = HOOKS / ad
        if not (MUTASYON or MUTASYON_NOTSUZ):
            return asil
        m = mutant_exit(asil) if MUTASYON else mutant_notsuz(asil)
        if m is None:
            return asil          # bu hook bu mutasyonun kapsamında değil → orijinal koşar
        uretilen.append(m)
        return m

    try:
        return _kos_vektorler(coz, tmp)
    finally:
        # Mutant kopyalar CANLI hooks/ dizinine yazılır (hook'lar komşularını `__file__`ten
        # bulur; temp dizindeki kopya import'ta çöker ve "FAIL" sanılır) → artık bırakmak
        # repoyu kirletir. Çökme dahil temizle.
        for m in uretilen:
            m.unlink(missing_ok=True)
        shutil.rmtree(tmp, ignore_errors=True)


def _kos_vektorler(coz, tmp: Path) -> int:
    guard = coz("pre_tool_guard.py")
    komsular = [coz("pull_before_edit.py"), coz("skill_injector.py")]

    # Hedef, koşum anında hesaplanan GERÇEK core kökü — sabit yol yazmak fixture'ı
    # başka checkout'ta sahte-kırmızı yapardı (worktree/klon adı tutmaz).
    kok = str(REPO).replace("\\", "/")

    # ── A) FP ÇAPALARI: guard yaşıyor mu, aşırı mı blokluyor? (fix'ten ETKİLENMEZ)
    rc, err = kos(guard, payload(f"{kok}/deneme.md", f"kullanici {IZ} yazdi"))
    kontrol("V1 gecerli JSON + '/' yol + sizinti -> BLOK",
            rc == 2 and "GENERICIZE-LEAK" in err, f"exit={rc}")

    rc, err = kos(guard, payload(str(REPO / "deneme.md"), f"kullanici {IZ} yazdi"))
    kontrol("V2 ayni payload BACKSLASH'li (bayt-tam) -> AYNI BLOK",
            rc == 2 and "GENERICIZE-LEAK" in err, f"exit={rc}")

    # ⛔ FP ÇAPASININ KALBİ: MEŞRU serbest yol HÂLÂ TAM SESSİZ olmalı. Not yalnız
    # parse-fail dalından çıkar; buraya sızarsa her temiz araç çağrısı gürültü basar.
    temiz_rc, temiz_err = kos(guard, payload(f"{kok}/deneme.md", "tamamen jenerik icerik"))
    kontrol("V3 sizintisiz gecerli payload -> SERBEST + SESSIZ (not SIZMAMALI)",
            temiz_rc == 0 and temiz_err.strip() == "", f"exit={temiz_rc}")

    rc, _ = kos(guard, json.dumps(
        {"tool_name": "Bash",
         "tool_input": {"command": "gh pr create --title x --body y"}}).encode())
    kontrol("V4 pozitif kontrol sozlesmesi (gh hedefsiz) -> BLOK", rc == 2, f"exit={rc}")

    # ── B) FİX'İN KALBİ: exit 0 KORUNUR ama artık AYIRT EDİLEBİLİR
    bozuk_rc, bozuk_err = kos(guard, BOZUK)
    kontrol("V5 BOZUK JSON -> exit 0 KORUNDU (fail-safe bilincli)",
            bozuk_rc == 0, f"exit={bozuk_rc}")
    kontrol("V6 bozuk JSON -> stderr'de PARSE-FAIL NOTU + hook adi (artik sessiz DEGIL)",
            TOKEN in bozuk_err and "pre_tool_guard" in bozuk_err,
            f"token={TOKEN in bozuk_err} stderr={len(bozuk_err)}b")
    kontrol("V7 AYIRT EDICILIK: bozuk-girdi ciktisi MESRU-serbestten FARKLI "
            "(= 'exit 0' artik tek anlamli)",
            bozuk_err.strip() != temiz_err.strip(),
            f"bozuk={len(bozuk_err)}b temiz={len(temiz_err)}b")

    # ── C) 3. BAĞLAM: tek hook'un vakası mı, SINIF mı?
    for i, hk in enumerate(komsular, start=8):
        rc, err = kos(hk, BOZUK)
        kontrol(f"V{i} 3.baglam {hk.name}: bozuk JSON -> exit 0 + NOT var",
                rc == 0 and TOKEN in err, f"exit={rc} token={TOKEN in err}")

    # ── D) TAŞIYICI EKSENİ — ⚠ EŞİTLİK ASSERT EDİLMEZ (ORTAM-BAĞIMLI, 2026-08-13)
    # İlk yazımda buradaki iki vektör "aynı payload her taşıyıcıda AYNI exit'i verir" diye
    # assert ediyordu ve yazarın makinesinde 2==2==2 ile geçti. LİDERİN BAĞIMSIZ KOŞUMU
    # DÜŞÜRDÜ: aynı worktree, aynı makine, FARKLI süreç-zinciri → `cat|boru`=255 (taşıyıcı
    # hiç koşmamış), PowerShell=0. Yani eşitlik bir DAVRANIŞ DEĞİŞMEZİ değil, yazarın
    # ortamının kazasıydı. Doğru sınıf: BORU HARNESS'ININ GÜVENİLİRLİĞİ ORTAM-BAĞIMLIDIR.
    pj = tmp / "payload.json"
    pj.write_bytes(payload(str(REPO / "deneme.md"), f"kullanici {IZ} yazdi"))
    IMZA = "GENERICIZE-LEAK"
    tasiyicilar: list[tuple[str, int, str]] = []

    with pj.open("rb") as fh:
        r = subprocess.run([sys.executable, str(guard)], stdin=fh, capture_output=True)
    tasiyicilar.append(("dogrudan '<dosya'", r.returncode,
                        r.stderr.decode("utf-8", errors="replace")))

    r = subprocess.run(f'cat "{pj}" | "{sys.executable}" "{guard}"', shell=True,
                       capture_output=True)
    err_b = r.stderr.decode("utf-8", errors="replace")
    # Taşıyıcının KENDİSİ koşamadıysa (cat yok / kabuk farklı) bu bir GUARD sonucu DEĞİLDİR.
    kosmadi = r.returncode == 255 or "not recognized" in err_b or "command not found" in err_b
    tasiyicilar.append((f"kabuk borusu{' [TASIYICI KOSMADI]' if kosmadi else ''}",
                        r.returncode, "" if kosmadi else err_b))

    ps = shutil.which("powershell") or shutil.which("pwsh")
    if ps:
        betik = tmp / "ps.ps1"
        hata_dosyasi = tmp / "ps_stderr.txt"
        betik.write_text(
            f'Get-Content "{pj}" -Raw | & "{sys.executable}" "{guard}" '
            f'2> "{hata_dosyasi}" | Out-Null\nexit $LASTEXITCODE\n', encoding="utf-8")
        r = subprocess.run([ps, "-NoProfile", "-ExecutionPolicy", "Bypass",
                            "-File", str(betik)], capture_output=True)
        # ⚠ PS 5.1 yönlendirilmiş stderr'i UTF-16LE + BOM yazar (ölçüldü: ilk baytlar
        # FF FE). utf-8 varsayıp okumak imzayı GÖRÜNMEZ yapar ve "guard blok mesajı
        # basmadı" diye okunur — harness'ın kendi kodlama tuzağı.
        tasiyicilar.append(("PowerShell borusu", r.returncode, _oku(hata_dosyasi)))
    else:
        print("[ATLANDI] PowerShell ekseni — powershell/pwsh bulunamadi (PATH)")

    print("  [BİLGİ] taşıyıcı ekseni (eşitlik BEKLENMEZ — ortam-bağımlı): "
          + " · ".join(f"{ad}={rc}" for ad, rc, _ in tasiyicilar))

    # ⛔ SÖZLEŞME YALNIZ REFERANS TAŞIYICIDA ASSERT EDİLİR (tasiyicilar[0] = doğrudan
    # stdin). Boru taşıyıcıları BİLGİDİR: exit kodunu düşürebilir, hiç koşmayabilir (255)
    # ya da stderr'i başka kodlamayla yazabilir (PS 5.1 → UTF-16LE). Bunlardan birini
    # FAIL'e çevirmek guard'ın davranışı yerine KOŞUM ORTAMINI test etmek olurdu.
    # V10 — ÇİFT YÖNLÜ SÖZLEŞME: blok imzası VAR <=> exit 2. Fix'ten SONRA bu vektörün
    # ikinci bir işi daha var: parse-fail notunun BLOK İMZASI SAYILMADIĞINI kanıtlar
    # (bozuk girdi artık stderr'e yazıyor ama exit 0 ve imzasız).
    olcumler = [("referans/sizintili", *tasiyicilar[0][1:]),
                ("referans/temiz", temiz_rc, temiz_err),
                ("referans/bozuk", bozuk_rc, bozuk_err)]
    ihlal = [f"{ad}(exit={rc},imza={IMZA in err})"
             for ad, rc, err in olcumler if (IMZA in err) != (rc == 2)]
    kontrol("V10 CIFT-YONLU SOZLESME: blok imzasi VAR <=> exit 2 (3 referans olcumu)",
            not ihlal, ", ".join(ihlal) or "3/3 tutarli")

    # ── E) DOKÜMAN KABLOLAMASI: uyarı silinirse sınıf sessizce geri gelir
    beklenen = {
        REPO / "governance" / "infra-test-recipes.md": ["B0b", "exit 0", TOKEN],
        REPO / "CLAUDE.core.md": ["exit 0"],
        REPO / "scripts" / "hooks" / "README.md": ["exit 0", "pozitif kontrol", TOKEN],
    }
    eksik = [f"{p.name}:{t}" for p, tokenlar in beklenen.items() for t in tokenlar
             if t.casefold() not in p.read_text(encoding="utf-8").casefold()]
    kontrol("V12 uyari + TOKEN uc dokumanda da duruyor", not eksik, ", ".join(eksik) or "tam")

    # ── F) SINIF KABLOLAMASI (V13) — kayıttaki HER hook davranışsal olarak ölçülür.
    # İÇ KONTROL GRUBU: `not_bekleniyor=False` olan 2 hook not BASMAMALI. Böylece vektör
    # "her yerde token var mı" değil, "DOĞRU YERLERDE var, yanlış yerlerde YOK" der.
    sapma: list[str] = []
    for ad, not_bekleniyor, _neden in HOOK_KAYDI:
        hk = coz(ad)
        rc, err = kos(hk, BOZUK)
        var = TOKEN in err
        if rc != 0:
            sapma.append(f"{ad}(exit={rc}!=0)")
        if var != not_bekleniyor:
            sapma.append(f"{ad}(not={var},beklenen={not_bekleniyor})")
    kontrol(f"V13 SINIF: {len(HOOK_KAYDI)} hook bozuk girdide exit 0 + not DOGRU YERDE "
            "(14 var / 2 kontrol-grubu yok)",
            not sapma, ", ".join(sapma) or f"{len(HOOK_KAYDI)}/{len(HOOK_KAYDI)} uyumlu")

    # ── G) STDOUT SÖZLEŞMESİ (V14) — not stderr'e gitti, stdout KİRLENMEDİ.
    # Hook'ların bir kısmı stdout'a JSON basar ve harness onu PARSE eder; oraya düşen tek
    # bayt sözleşmeyi kırar. Kural: parse-fail'de stdout ya BOŞ ya GEÇERLİ JSON olmalı.
    kirli: list[str] = []
    for ad, _b, _n in HOOK_KAYDI:
        hk = coz(ad)
        _rc, cikti, _err = kos_tam(hk, BOZUK)
        if not cikti.strip():
            continue
        try:
            json.loads(cikti.decode("utf-8"))
        except Exception as e:
            kirli.append(f"{ad}({type(e).__name__})")
    kontrol("V14 STDOUT SOZLESMESI: parse-fail'de stdout BOS ya da GECERLI JSON",
            not kirli, ", ".join(kirli) or "16/16 temiz")

    # ── H) 3. BAĞLAM / GÖREV-DIŞI EKSEN (V15) — fix'in stdout'a DOKUNMADIĞI, aynı payload
    # üzerinde FİX'Lİ ve FİX'SİZ sürüm KARŞILAŞTIRILARAK ölçülür (iddia değil, ölçüm):
    # stdout BAYT-EŞ olmalı, fark YALNIZ stderr'de olmalı.
    ref = HOOKS / "session_start.py"          # stdout'a JSON sözleşmesi basan bir hook
    fixli = coz("session_start.py")
    notsuz = mutant_notsuz(fixli)
    try:
        if notsuz is None:
            kontrol("V15 3.BAGLAM stdout bayt-esitligi (fix-li vs fix-siz)",
                    False, "fix sokulemedi: _parse_fail_notu() cagrisi YOK (fix zaten yok)")
        else:
            _r1, out1, err1 = kos_tam(fixli, BOZUK)
            _r2, out2, err2 = kos_tam(notsuz, BOZUK)
            kontrol("V15 3.BAGLAM (session_start, stdout-JSON sozlesmeli): fix stdout'u "
                    "BAYT-ESIT birakir, fark YALNIZ stderr'de",
                    out1 == out2 and (TOKEN in err1) and (TOKEN not in err2),
                    f"stdout_esit={out1 == out2} fixli_not={TOKEN in err1} "
                    f"fixsiz_not={TOKEN in err2}")
    finally:
        if notsuz is not None:
            notsuz.unlink(missing_ok=True)
    del ref

    # ── I) KAYIT TAMLIĞI (V16) — sınıf sessizce yeniden büyüyemesin.
    # stdin'den JSON okuyan YENİ bir hook eklenirse kayda girmeden bu vektör düşer;
    # yoksa "16 hook temiz" diyen bir korpus 17. hook'u hiç görmezdi (sahte güven).
    diskte = {p.name for p in sorted(HOOKS.glob("*.py"))
              if not p.name.startswith(("_mutant_", "_notsuz_"))
              and "sys.stdin" in p.read_text(encoding="utf-8")}
    kayitli = {ad for ad, _b, _n in HOOK_KAYDI}
    kontrol("V16 KAYIT TAMLIGI: stdin okuyan her hook SINIF KAYDINDA",
            diskte == kayitli,
            f"kayitsiz={sorted(diskte - kayitli)} fazla={sorted(kayitli - diskte)}"
            if diskte != kayitli else f"{len(diskte)} hook")

    etiket = " [MUTASYON-EXIT]" if MUTASYON else (" [MUTASYON-NOTSUZ]" if MUTASYON_NOTSUZ else "")
    gecen = sum(1 for ok, _ in SONUC if ok)
    print(f"\n=== negatif_test_harness{etiket} ===")
    for ok, ad in SONUC:
        print(f"  [{'OK  ' if ok else 'FAIL'}] {ad}")
    print(f"{gecen}/{len(SONUC)} PASS")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
