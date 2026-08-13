#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fixture — hook negatif-testinde SAHTE-SERBEST sınıfı (kuyruk kaydı 2026-08-13).

**Neden var:** stdin'den JSON okuyan hook'lar bozuk girdide `except: return 0` ile
fail-safe davranır ("yabancı girdi serbest"). Sonuç: *"guard bu payload'ı GEÇİRDİ"* ile
*"guard payload'ı HİÇ OKUYAMADI"* aynı exit kodunu üretir ve ikincisi düzenli olarak
"guard bypass edildi" diye raporlanır. Tetikleyici tuzak: elle yazılan `\\` kabuğa tek
`\` olarak ulaşır → JSON'da geçersiz escape → parse-fail → 0.

**Bu korpus neyi çivilliyor:** (a) guard'ın gerçekten yaşadığı (FP çapaları), (b) bozuk
girdinin meşru-serbestten AYIRT EDİLEMEZ olduğu, (c) bunun tek hook'un vakası değil
SINIF olduğu (3. bağlam: başka hook'lar), (d) taşıyıcıdan BAĞIMSIZ sözleşme
(`exit 2` ⇔ stderr'de blok imzası), (e) uyarının üç dokümanda DURDUĞU.

⚠ **Taşıyıcılar arası exit EŞİTLİĞİ assert EDİLMEZ** — ölçüldü ki ortam-bağımlıdır
(2026-08-13, iki bağımsız koşum zıt sonuç verdi; §D bloğundaki nota bak). Taşıyıcı
exit'leri BİLGİ olarak basılır, hükme esas alınmaz.

Vektör numaraları KİMLİKTİR, sıra değil: **V11 bilerek BOŞTUR** (eski "PS borusu bash ile
aynı exit'i verir" vektörü ortam-bağımlı çıkınca kaldırıldı; kalanlar yeniden numaralanmadı
ki dokümandaki atıflar kaymasın). Toplam **11 vektör**: V1-V10 + V12.

Koşum:  python tests/fixtures/negatif_test_harness/run.py
Mutasyon: ... --mutasyon   → fail-safe `return 0` → `return 2` yapılır (geçici kopya;
çalışma ağacı KİRLENMEZ). Ayırt edici vektörler düşmeli; hepsi geçerse korpus BOŞTUR.
Mutasyon git ref'inden DEĞİL, BUGÜNKÜ kaynaktan üretilir — "fix merge olunca taban kayar"
tuzağı (B20 dersi) bu korpusta yapısal olarak yoktur.
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

# Guard'ın SAP-kullanıcı desenini tetikleyen sentetik iz. Parça parça kurulur: bu dosya
# core'a commit'lenir ve düz yazılsa kendi GENERICIZE-LEAK gate'imize takılırdı.
IZ = "D_" + "TESTUSR"
SONUC: list[tuple[bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((bool(kosul), f"{ad}{(' -> ' + detay) if detay else ''}"))


def kos(hook: Path, govde: bytes) -> tuple[int, str]:
    """Payload'ı BAYT olarak verir — kabuk/echo katmanı bilinçli olarak devre dışı."""
    r = subprocess.run([sys.executable, str(hook)], input=govde,
                       capture_output=True)
    return r.returncode, r.stderr.decode("utf-8", errors="replace")


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


def mutant_hook(kaynak: Path, hedef_dizin: Path) -> Path:
    """STDIN fail-safe'ini (`json.load(sys.stdin)` → `except` → `return 0`) `return 2` yapar.

    Çapa DAR tutulur: dosyadaki ilk `except Exception: return 0`ı vurmak pre_tool_guard'da
    ALAKASIZ bir yardımcıyı bozup koşucuyu ÇÖKERTİYORDU — ve çökme, FAIL gibi okunuyordu.

    Mutant `scripts/hooks/` İÇİNE yazılır (`hedef_dizin` yok sayılır): hook'lar kendi
    komşularını `__file__`ten türetir, temp dizindeki kopya import'ta çöker (exit 1) ve
    yine "FAIL" sanılır. Silme sorumluluğu çağırana aittir (finally).
    """
    satirlar = kaynak.read_text(encoding="utf-8").splitlines(keepends=True)
    baslangic = next((i for i, s in enumerate(satirlar)
                      if "json.load" in s and "sys.stdin" in s), None)
    hedef_satir = None
    if baslangic is not None:
        for i in range(baslangic + 1, min(baslangic + 5, len(satirlar))):
            if re.match(r"^\s*return 0\b", satirlar[i]):
                hedef_satir = i
                break
    if hedef_satir is None:
        raise SystemExit(f"[TABAN ÖZ-DENETİMİ] {kaynak.name}: stdin fail-safe deseni "
                         "bulunamadı — mutasyon ÜRETİLEMEDİ (kod değişmiş olabilir). "
                         "Hiçbir sayı raporlanmaz.")
    satirlar[hedef_satir] = satirlar[hedef_satir].replace("return 0", "return 2", 1)
    h = kaynak.with_name("_mutant_" + kaynak.name)
    h.write_text("".join(satirlar), encoding="utf-8")
    return h


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="neg_harness_"))
    guard = HOOKS / "pre_tool_guard.py"
    komsular = [HOOKS / "pull_before_edit.py", HOOKS / "skill_injector.py"]
    mutantlar: list[Path] = []
    try:
        if MUTASYON:
            guard = mutant_hook(guard, tmp)
            komsular = [mutant_hook(k, tmp) for k in komsular]
            mutantlar = [guard, *komsular]
        return _kos_vektorler(guard, komsular, tmp)
    finally:
        # Mutant kopyalar CANLI hooks/ dizinine yazılır → artık bırakmak repoyu kirletir
        # (yaşanmış sınıf: fixture artığı komşu fixture'ı düşürdü). Çökme dahil temizle.
        for m in mutantlar:
            m.unlink(missing_ok=True)
        shutil.rmtree(tmp, ignore_errors=True)


def _kos_vektorler(guard: Path, komsular: list[Path], tmp: Path) -> int:

    # Hedef, koşum anında hesaplanan GERÇEK core kökü — sabit yol yazmak fixture'ı
    # başka checkout'ta sahte-kırmızı yapardı (worktree/klon adı tutmaz).
    kok = str(REPO).replace("\\", "/")

    # ── A) FP ÇAPALARI: guard yaşıyor mu, aşırı mı blokluyor? (mutasyondan ETKİLENMEZ)
    rc, err = kos(guard, payload(f"{kok}/deneme.md", f"kullanici {IZ} yazdi"))
    kontrol("V1 gecerli JSON + '/' yol + sizinti -> BLOK",
            rc == 2 and "GENERICIZE-LEAK" in err, f"exit={rc}")

    rc, err = kos(guard, payload(str(REPO / "deneme.md"), f"kullanici {IZ} yazdi"))
    kontrol("V2 ayni payload BACKSLASH'li (bayt-tam) -> AYNI BLOK",
            rc == 2 and "GENERICIZE-LEAK" in err, f"exit={rc}")

    temiz_rc, temiz_err = kos(guard, payload(f"{kok}/deneme.md", "tamamen jenerik icerik"))
    kontrol("V3 sizintisiz gecerli payload -> SERBEST + sessiz",
            temiz_rc == 0 and temiz_err.strip() == "", f"exit={temiz_rc}")

    rc, _ = kos(guard, json.dumps(
        {"tool_name": "Bash",
         "tool_input": {"command": "gh pr create --title x --body y"}}).encode())
    kontrol("V4 pozitif kontrol sozlesmesi (gh hedefsiz) -> BLOK", rc == 2, f"exit={rc}")

    # ── B) AYIRT EDİCİ: bozuk girdi meşru-serbestten ayırt EDİLEMİYOR
    # Tek `\I` = gecersiz JSON escape; elle yazilan `\\`nin kabuktan sonraki hali.
    bozuk = ('{"tool_name":"Write","tool_input":{"file_path":"C:\\IX\\d.md",'
             '"content":"kullanici ' + IZ + '"}}').encode()
    bozuk_rc, bozuk_err = kos(guard, bozuk)
    kontrol("V5 BOZUK JSON (tek-backslash escape) -> exit 0 (fail-safe)",
            bozuk_rc == 0, f"exit={bozuk_rc}")
    kontrol("V6 bozuk JSON stderr BOS (sessiz -> okunamaz)",
            bozuk_err.strip() == "", f"stderr={len(bozuk_err)}b")
    kontrol("V7 ESITLIK CAPASI: bozuk-girdi ciktisi ile MESRU-serbest ciktisi AYNI "
            "(= 'exit 0' iki anlamli)",
            (bozuk_rc, bozuk_err.strip()) == (temiz_rc, temiz_err.strip()),
            f"bozuk={bozuk_rc} temiz={temiz_rc}")

    # ── C) 3. BAĞLAM: tek hook'un vakası mı, SINIF mı?
    for i, hk in enumerate(komsular, start=8):
        rc, err = kos(hk, bozuk)
        kontrol(f"V{i} 3.baglam {hk.name}: bozuk JSON -> exit 0 + sessiz",
                rc == 0 and err.strip() == "", f"exit={rc}")

    # ── D) TAŞIYICI EKSENİ — ⚠ EŞİTLİK ASSERT EDİLMEZ (ORTAM-BAĞIMLI, 2026-08-13)
    # İlk yazımda buradaki iki vektör "aynı payload her taşıyıcıda AYNI exit'i verir" diye
    # assert ediyordu ve yazarın makinesinde 2==2==2 ile geçti. LİDERİN BAĞIMSIZ KOŞUMU
    # DÜŞÜRDÜ: aynı worktree, aynı makine, FARKLI süreç-zinciri → `cat|boru`=255 (taşıyıcı
    # hiç koşmamış), PowerShell=0. Yani eşitlik bir DAVRANIŞ DEĞİŞMEZİ değil, yazarın
    # ortamının kazasıydı — ve "PS pipe bozuk iddiası ÇÜRÜTÜLDÜ" hükmü aşırı-uydurmaydı.
    # Doğru sınıf: BORU HARNESS'ININ GÜVENİLİRLİĞİ ORTAM-BAĞIMLIDIR.
    # Bu yüzden burada yalnız HER ORTAMDA doğru olan sözleşme assert edilir:
    #   exit 2  <=>  stderr'de blok imzası      (2 asla kazara değil; imza asla sessiz değil)
    # Not: bu iki vektör MUTASYONDA ZATEN DÜŞMÜYORDU (ayırt edici değillerdi) → demote
    # etmek korpusun ayırt etme gücünden hiçbir şey götürmez; V5/V7/V8/V9 omurgadır.
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
        # FF FE, harfler arası \0). utf-8 varsayıp okumak imzayı GÖRÜNMEZ yapar ve
        # "guard blok mesajı basmadı" diye okunur — harness'ın kendi kodlama tuzağı.
        tasiyicilar.append(("PowerShell borusu", r.returncode, _oku(hata_dosyasi)))
    else:
        print("[ATLANDI] PowerShell ekseni — powershell/pwsh bulunamadi (PATH)")

    print("  [BİLGİ] taşıyıcı ekseni (eşitlik BEKLENMEZ — ortam-bağımlı): "
          + " · ".join(f"{ad}={rc}" for ad, rc, _ in tasiyicilar))

    # ⛔ SÖZLEŞME YALNIZ REFERANS TAŞIYICIDA ASSERT EDİLİR (tasiyicilar[0] = doğrudan
    # stdin; exit kodunu da stderr'i de Python'ın kendisi toplar). Boru taşıyıcıları
    # BİLGİDİR: exit kodunu düşürebilir (lider ortamında PS=0 ölçüldü), taşıyıcı hiç
    # koşmayabilir (kabuk borusu=255) ya da stderr'i başka kodlamayla yazabilir
    # (PS 5.1 → UTF-16LE). Bunlardan herhangi birini FAIL'e çevirmek, guard'ın davranışı
    # yerine KOŞUM ORTAMINI test etmek olurdu — korpus başka makinede sahte-kırmızı yanar.
    # V10 — ÇİFT YÖNLÜ SÖZLEŞME, referans taşıyıcının ÜÇ ölçümü üzerinde:
    #   imza VAR  <=>  exit 2
    # V1/V2 yalnız "sızıntılı payload bloklanıyor" der; bu vektör ek olarak imzanın
    # bloklamayan yollara SIZMADIĞINI da kapatır (temiz payload ve bozuk payload) —
    # yani "exit 0 sessizdir" iddiasının simetrik yarısı. Taşıyıcıdan bağımsızdır.
    olcumler = [("referans/sizintili", *tasiyicilar[0][1:]),
                ("referans/temiz", temiz_rc, temiz_err),
                ("referans/bozuk", bozuk_rc, bozuk_err)]
    ihlal = [f"{ad}(exit={rc},imza={IMZA in err})"
             for ad, rc, err in olcumler if (IMZA in err) != (rc == 2)]
    kontrol("V10 CIFT-YONLU SOZLESME: imza VAR <=> exit 2 (3 referans olcumu)",
            not ihlal, ", ".join(ihlal) or "3/3 tutarli")

    # ── E) DOKÜMAN KABLOLAMASI: uyarı silinirse sınıf sessizce geri gelir
    beklenen = {
        REPO / "governance" / "infra-test-recipes.md": ["B0b", "exit 0"],
        REPO / "CLAUDE.core.md": ["exit 0"],
        REPO / "scripts" / "hooks" / "README.md": ["exit 0", "pozitif kontrol"],
    }
    eksik = [f"{p.name}:{t}" for p, tokenlar in beklenen.items() for t in tokenlar
             if t.casefold() not in p.read_text(encoding="utf-8").casefold()]
    kontrol("V12 uyari UC dokumanda da duruyor", not eksik, ", ".join(eksik) or "tam")

    gecen = sum(1 for ok, _ in SONUC if ok)
    print(f"\n=== negatif_test_harness{' [MUTASYON]' if MUTASYON else ''} ===")
    for ok, ad in SONUC:
        print(f"  [{'OK  ' if ok else 'FAIL'}] {ad}")
    print(f"{gecen}/{len(SONUC)} PASS")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
