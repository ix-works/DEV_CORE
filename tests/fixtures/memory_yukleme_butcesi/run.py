# -*- coding: utf-8 -*-
"""memory_yukleme_butcesi — C-MEM-01'in ÖLÇÜM MODELİ: ham bayt mı, yüklenen gövde mi (K2).

KÖK: `check_memory_index._butce` bütçeyi `idx.read_bytes()` ile HAM ölçüyordu. Üst harness
(Claude Code ≥2.1.211) MEMORY.md'yi yüklemeden ÖNCE baştaki YAML frontmatter'ı ve BLOK
seviyesindeki HTML yorumlarını SOYAR — yani bunlar 200-satır/25KB bütçesine SAYILMAZ.
Öncül RESMÎ kaynakla doğrulandı (code.claude.com/docs/en/memory: *"…are stripped before
the index is loaded… Before v2.1.211, Claude Code measured the raw file"*) — bu korpusun
yönü oraya dayanır; kaynak değişirse (sürüm semantiği geri alınırsa) P vektörleri yanlış
yöne bakar, N/K çapaları ise her hâlükârda geçerli kalır.
Sonuç: indekse bakım-notu (kanca kuralı, sıkıştırma tarihçesi) yazan herkes gate'i SAHTE
ALARMA sürüklüyordu. Sahte alarmın bedeli çift: (a) gereksiz sıkıştırma turu, (b) alarm
yorgunluğu — gerçek doluluk aynı mesajın içinde görünmez olur.

İKİNCİ KUSUR (aynı dosya): memory dizini yokken çıktı `[SKIP] … yok` satırını basıyordu
AMA hemen altına `[OK] auto-memory bütçesi + indeks bütünlüğü` yazıyordu. CI log'unda tek
başına okunan o satır "denetim koştu, sorun yok" demektir. **KOŞMADI ≠ TEMİZ.**

ÖLÇÜT (mutasyon etiketi): "fix'ten ÖNCE de doğru muydu?"
  * P/W/S1/U  → fix'in getirdiği ayrım. Mutasyonda DÜŞMELİ.
  * N/K       → FP çapaları + kontrol grupları. Mutasyonda AYAKTA kalmalı; düşerlerse
                fix "ölçmüyor" demektir (soyma fazla agresif → gerçek şişme gizlenir).

⚠ FP ÇAPALARI OMURGADIR: soyma fazla agresifse gate sessizleşir ve dosyanın SONU (yani en
alttaki davranış kuralları) uyarısız düşer — gate'in var olma sebebi tam da budur. Bu
yüzden N3 (kod-fence içi), N4 (kapanmamış yorum), N5 (ortadaki `---`), N6 (satır-içi
yorum) vektörleri SİLİNMEZ.

Koşum:    python tests/fixtures/memory_yukleme_butcesi/run.py
MUTASYON: python tests/fixtures/memory_yukleme_butcesi/run.py --mutasyon [--ref <SHA>]
          (varsayılan taban 3d4b649 = fix ÖNCESİ sürüm; ⛔ DAL ADI VERME — bu dal merge
          edilince `origin/main` "fix sonrası"na kayar ve korpus ayırt etmiyormuş gibi
          görünür. Koşucu tabanın gerçekten kusurlu olduğunu ÖN-DOĞRULAR, değilse durur.)
"""
from __future__ import annotations

import argparse
import importlib.util
import os
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

KOK = Path(__file__).resolve().parents[3]
GATE_REL = "scripts/validators/check_memory_index.py"
TABAN_SHA = "3d4b649"

SONUC: list[tuple[bool, str]] = []


def kontrol(ok: bool, ad: str, detay: str = "") -> None:
    SONUC.append((ok, ad + (f" — {detay}" if detay else "")))


# ─────────────────────────────────────────────────────────────────────────────
# Sentetik MEMORY.md üreteçleri (bayt/satır hedefleri KOD İÇİNDE ölçülür — sabit
# sayı yazmak bayatlar; aşağıdaki `_kur` her senaryonun ham/soyulmuş boyutunu basar)
# ─────────────────────────────────────────────────────────────────────────────
def _govde(satir: int, uzunluk: int = 120) -> str:
    """Bütçe dolduran gövde. ⚠ md-LİNK İÇERMEZ: link koyulursa `_butunluk` ölü-link FAIL'i
    basar ve bütçe vektörleri ÖLÇTÜĞÜNÜ SANDIĞIN şeyi ölçmez (ilk koşumda tam bu oldu —
    P1/P1b/P1c/W1 'exit 1' veriyordu, sebebi bütçe değil ölü linkti)."""
    return "".join(f"- Kayit {i:03d}: {'x' * uzunluk}\n" for i in range(satir))


def _yorum(satir: int, uzunluk: int = 120) -> str:
    ic = "".join(f"    bakim notu {i:03d}: {'y' * uzunluk}\n" for i in range(satir))
    return "<!--\n" + ic + "-->\n"


BASLIK = "# Hafiza indeksi\n\n"

# P1 — ham >25KB, soyulunca RAHAT sığıyor  (eski kod: FAIL / yeni kod: OK)
P1 = BASLIK + _yorum(160) + _govde(60)

# P1b — satır ekseninin ikizi: ham >200 satır, soyulunca <200  (eski: FAIL / yeni: OK)
P1b = BASLIK + _yorum(150, 10) + _govde(110, 10)

# P1c — YAML frontmatter da soyulur (blok-yorum değil, AYRI dal).
# ⚠ frontmatter TEK BAŞINA tavanı aşmalı: ilk yazımda 60 satırdı ve mutasyonda AYAKTA
# kaldı — yani ayırt edici değil, sessiz bir çapaydı. Etiketi mutasyon belirler.
P1c = ("---\n" + "".join(f"anahtar{i}: {'z' * 200}\n" for i in range(140)) + "---\n"
       + BASLIK + _govde(60))

# W1 — soyulmuş hâli UYARI bandında (%85-95): FAIL değil WARN, exit 0
W1 = BASLIK + _yorum(80) + _govde(155, 130)

# N1 — soyulmuş hâli DE taşıyor → FAIL (soyma bahane olmamalı) + soyma İZİ görünür
N1 = BASLIK + _yorum(40) + _govde(220)

# N2 — ölü indeks linki → FAIL (regresyon çapası; bütçeden bağımsız)
N2 = BASLIK + "- [Yok olan](yok.md) — diskte olmayan dosya\n"

# P2 — temiz ve küçük → OK (FP çapası)
P2 = BASLIK + "- [Ornek](ornek.md) — tek satirlik kanca\n"

# N3 — KOD-FENCE içindeki yorum/frontmatter SOYULMAZ (örnek gösterilen metin de yüktür)
N3 = BASLIK + "```markdown\n" + _yorum(220) + "```\n" + _govde(20)

# N4 — KAPANMAMIŞ `<!--` soyulmaz (fail-safe: fazla ölç)
N4 = BASLIK + "<!--\n" + "".join(f"    kapanmayan {i}: {'y' * 120}\n" for i in range(220)) + _govde(10)

# N5 — ortadaki `---` (yatay çizgi) frontmatter SANILMAZ
N5 = BASLIK + _govde(100) + "\n---\n" + _govde(120)

# N6 — SATIR-İÇİ yorum gövdenin ortasındadır, düşülmez
N6 = BASLIK + "".join(
    f"- Kayit {i:03d} <!-- kisa not --> {'x' * 120}\n" for i in range(220))


def _kur(tmp: Path, ad: str, icerik: str, ek_dosya: bool = False) -> Path:
    d = tmp / ad
    d.mkdir(parents=True, exist_ok=True)
    (d / "MEMORY.md").write_text(icerik, encoding="utf-8")
    if ek_dosya:
        (d / "ornek.md").write_text(
            "---\nname: ornek\ndescription: tek satirlik ornek hatira\nmetadata:\n"
            "  type: feedback\n---\n\nGovde.\n", encoding="utf-8")
    return d


def _kos(gate: Path, mem_dizini: Path | None) -> tuple[int, str]:
    env = os.environ.copy()
    for k in list(env):
        if k == "CLAUDE_PROJECT_DIR" or k.startswith("IX_"):
            env.pop(k, None)
    env["PYTHONIOENCODING"] = "utf-8"
    if mem_dizini is not None:
        env["CLAUDE_AUTO_MEMORY_DIR"] = str(mem_dizini)
    else:
        env["CLAUDE_AUTO_MEMORY_DIR"] = str(gate.parent / "hic-olmayan-dizin")
    try:
        p = subprocess.run([sys.executable, str(gate)], cwd=str(gate.parent), env=env,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=120)
    except Exception as e:  # noqa: BLE001  — çökme ≠ FAIL, görünür kalsın
        return (-1, f"KOŞULAMADI: {type(e).__name__}: {e}")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# (kod, içerik, FAIL_bekleniyor, beklenen_iz, ek_dosya, açıklama)
SENARYOLAR: list[tuple[str, str, bool, str, bool, str]] = [
    ("P1",  P1,  False, "", False,
     "P1 ham >25KB ama SOYULUNCA sığıyor → OK (sahte alarm yok)"),
    ("P1b", P1b, False, "", False,
     "P1b ham >200 satır ama soyulunca <200 → OK (satır ekseni)"),
    ("P1c", P1c, False, "", False,
     "P1c baştaki YAML frontmatter soyulur → OK"),
    ("W1",  W1,  False, "[WARN]", False,
     "W1 soyulmuş hâli %85-95 bandında → WARN + exit 0 (merdiven korunur)"),
    ("N1",  N1,  True,  "soyulan", False,
     "N1 FP çapası: soyulmuş hâli DE taşıyor → FAIL + soyma izi çıktıda"),
    ("N2",  N2,  True,  "ölü link", False,
     "N2 REGRESYON çapası: ölü indeks linki → FAIL"),
    ("P2",  P2,  False, "[OK]", True,
     "P2 FP çapası: temiz + küçük indeks → OK"),
    ("N3",  N3,  True,  "doluluğu", False,
     "N3 FP çapası: KOD-FENCE içi yorum SOYULMAZ → FAIL"),
    ("N4",  N4,  True,  "doluluğu", False,
     "N4 FP çapası: KAPANMAMIŞ `<!--` soyulmaz (fail-safe) → FAIL"),
    ("N5",  N5,  True,  "doluluğu", False,
     "N5 FP çapası: ortadaki `---` frontmatter sanılmaz → FAIL"),
    ("N6",  N6,  True,  "doluluğu", False,
     "N6 FP çapası: satır-içi `<!-- -->` düşülmez → FAIL"),
]


def davranis_testleri(gate: Path, tmp: Path) -> None:
    for kod, icerik, fail_bekleniyor, iz, ek, ad in SENARYOLAR:
        d = _kur(tmp, kod, icerik, ek)
        rc, cikti = _kos(gate, d)
        if rc < 0:
            kontrol(False, ad, cikti)
            continue
        oldu = rc != 0
        ok = oldu == fail_bekleniyor and (not iz or iz in cikti)
        ham = len(icerik.encode("utf-8"))
        kontrol(ok, ad, f"exit={rc} (beklenen {'1' if fail_bekleniyor else '0'}), ham={ham}B"
                + ("" if ok else " :: " + cikti.strip()[:240]))

    # ── S1: SKIP GÖRÜNÜRLÜĞÜ — dizin yok → exit 0 AMA "KOŞMADI" demeli ve
    #    "[OK] auto-memory bütçesi" cümlesini KURMAMALI (koşmadı ≠ temiz).
    rc, cikti = _kos(gate, None)
    kontrol(rc == 0 and "KOŞMADI" in cikti and "[OK] auto-memory bütçesi" not in cikti,
            "S1 dizin yok → exit 0 + 'KOŞMADI' + yanıltıcı '[OK] auto-memory bütçesi' YOK",
            f"exit={rc} :: {cikti.strip()[:240]}")
    kontrol("aranan yol" in cikti or "hic-olmayan-dizin" in cikti,
            "S1b SKIP satırı ARANAN YOLU yazar (nerede baktığımız kaybolmasın)",
            cikti.strip()[:160])

    # ── K1 KONTROL GRUBU: dizin VAR ve temiz → "KOŞMADI" izi OLMAMALI.
    #    (S1 tek başına ölçülürse "her koşumda KOŞMADI yaz" da testi geçerdi.)
    d = _kur(tmp, "K1", P2, ek_dosya=True)
    rc, cikti = _kos(gate, d)
    kontrol(rc == 0 and "KOŞMADI" not in cikti and "[OK]" in cikti,
            "K1 KONTROL: dizin var+temiz → exit 0, 'KOŞMADI' izi YOK",
            f"exit={rc} :: {cikti.strip()[:200]}")


def birim_testleri(gate: Path) -> None:
    """`_yukleme_govdesi` sözleşmesi (in-process; davranış testlerinin açıklaması)."""
    try:
        spec = importlib.util.spec_from_file_location("chk_mem_idx", gate)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    except Exception as e:  # noqa: BLE001
        kontrol(False, "U0 modül yüklenebiliyor", f"{type(e).__name__}: {e}")
        return
    f = getattr(m, "_yukleme_govdesi", None)
    if f is None:
        kontrol(False, "U1 `_yukleme_govdesi` tek-kaynağı var", "fonksiyon YOK")
        return
    kontrol(f("---\na: 1\n---\ngovde\n") == "govde\n",
            "U1 baştaki frontmatter düşer")
    kontrol(f("<!--\nnot\n-->\ngovde\n") == "govde\n",
            "U2 blok HTML yorumu düşer")
    kontrol(f("```\n<!--\nnot\n-->\n```\n") == "```\n<!--\nnot\n-->\n```\n",
            "U3 FP çapası: kod-fence içi DOKUNULMAZ")
    kontrol(f("<!--\nnot\n") == "<!--\nnot\n",
            "U4 FP çapası: kapanmamış yorum SOYULMAZ (fazla ölç)")
    kontrol(f("govde\n---\nalt\n") == "govde\n---\nalt\n",
            "U5 FP çapası: ortadaki `---` frontmatter değildir")
    kontrol(f("metin <!-- not --> devam\n") == "metin <!-- not --> devam\n",
            "U6 FP çapası: satır-içi yorum düşülmez (blok değil)")
    kontrol(f("<!-- not --> kalan\ngovde\n") == " kalan\ngovde\n",
            "U7 blok yorumun kapanışından SONRAKİ metin korunur")


def _git_show(ref: str, rel: str) -> str | None:
    p = subprocess.run(["git", "-C", str(KOK), "show", f"{ref}:{rel}"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.stdout if p.returncode == 0 else None


def _gate_dosyasi(kaynak: str | None, tmp: Path) -> Path:
    """Ölçülen dosya. Mutasyonda taban sürüm; normalde ÇALIŞMA AĞACININ kendisi.

    ⚠ Her iki mod da aynı kabuktan koşar (`python <dosya>` + env) — ölçüm gerçek CLI
    giriş noktasından yapılır, modül import edilerek DEĞİL.
    """
    if kaynak is None:
        return KOK / GATE_REL
    hedef = tmp / "gate_taban" / "scripts" / "validators" / "check_memory_index.py"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(kaynak, encoding="utf-8")
    return hedef


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutasyon", action="store_true",
                    help="fix'i geri al: TABAN sürümle koş (P/W/S1/U düşmeli)")
    ap.add_argument("--ref", default=TABAN_SHA,
                    help="mutasyon taban SHA'sı (⛔ dal adı DEĞİL)")
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="mem_butce_"))
    try:
        kaynak = None
        if args.mutasyon:
            kaynak = _git_show(args.ref, GATE_REL)
            if kaynak is None:
                print(f"[DOĞRULANAMADI] taban sürüm alınamadı: {args.ref}:{GATE_REL}")
                return 2
            # TABANIN KUSURLU OLDUĞUNU ÖN-DOĞRULA: hareketli/yanlış ref verilirse korpus
            # "ayırt etmiyor" gibi görünür — HATA VERMEDEN. Sayı basmadan dur.
            on = _gate_dosyasi(kaynak, tmp)
            rc, _ = _kos(on, _kur(tmp, "_on", P1))
            if rc == 0:
                print(f"[DOĞRULANAMADI] taban {args.ref} P1'i FAIL etmiyor (exit={rc}) — "
                      f"bu ref fix ÖNCESİ sürüm DEĞİL. Hiçbir sayı raporlanmadı.")
                return 2
            print(f"[MUTASYON] taban {args.ref}: P/W/S1/U DÜŞMELİ, N/K AYAKTA kalmalı\n")

        gate = _gate_dosyasi(kaynak, tmp)
        davranis_testleri(gate, tmp)
        birim_testleri(gate)

        # ── KABLOLAMA: yukarıdaki koşumlar kopya/taban dosya olabilir; canlı ağaçtaki
        #    GERÇEK dosyanın da aynı sözleşmeyi verdiğini bir vektörle doğrula.
        if not args.mutasyon:
            rc, cikti = _kos(KOK / GATE_REL, _kur(tmp, "CANLI", P1))
            kontrol(rc == 0, "K2 KABLOLAMA: çalışma ağacındaki gerçek dosya + P1 → exit 0",
                    f"exit={rc} :: {cikti.strip()[:200]}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for ok, _ in SONUC if ok)
    for ok, ad in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    # ⚠ Özet satırı `^\s*\d+/\d+ OK` ile BAŞLAMALI — `run_fixture_tests` sayıyı bu desenle
    # okur; "ad: 22/22 OK" yazarsan suite tabloda BOŞ özet gösterir (sayı görünmez olur).
    print(f"\n{gecen}/{len(SONUC)} OK — memory_yukleme_butcesi")
    if args.mutasyon:
        return 0          # mutasyonda karar SATIRLARDA (hangi vektör düştü), exit'te değil
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    raise SystemExit(main())
