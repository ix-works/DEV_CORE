#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VALIDATOR — auto-memory bütçesi + indeks bütünlüğü (C-MEM-01).

NEDEN (2026-07-10 memory/recall denetimi):

1) **SESSİZ KESİLME.** Claude Code `MEMORY.md`'nin yalnız **ilk 200 satırını VEYA ilk
   25 KB'ını** (hangisi önce gelirse) oturum başında yükler; gerisi **yüklenmez, uyarı
   verilmez** (code.claude.com/docs/en/memory). Türkçe metinde bağlayıcı kısıt satır
   değil **BAYT**tır (çoğu harf 2 bayt). Denetimde MEMORY.md 20.192/25.600 bayt = %79
   doluydu ve kimse ölçmüyordu. Tavan aşılınca dosyanın SONU düşer — yani en alttaki
   davranış kuralları sessizce hafızadan silinir. Tam da "AI hatırlamıyor" şikâyeti.

2) **ÖLÜ İNDEKS LİNKİ.** `MEMORY.md` var olmayan bir dosyayı gösteriyordu; o hatıranın
   gövdesi erişilemez hâldeydi (yalnız tek satırlık özeti kalmış).

3) **ERİŞİLEMEZ HATIRA.** İndeksten (doğrudan ya da tek hop `[[wiki-link]]` ile)
   ulaşılamayan memory dosyası, model için YOK hükmündedir.

ENFORCES: C-MEM-01
Kapsam:
  * proje auto-memory dizini  → bütçe + bütünlük  (bulunamazsa sessizce atlanır)
  * `core/claude/memory-seed/` → bütünlük (seed'in bütçesi yok; yeni projeye tohumlanır)

Eşikler: bayt/satır doluluğu %85 → WARNING, %95 → FAIL. Ölü link / erişilemez dosya /
frontmatter şema ihlali → FAIL.
Onarım: MEMORY.md'yi sıkıştır (gövdeyi konu dosyasına taşı, indekste tek satır bırak).

⚠ ÖLÇÜM MODELİ (2026-08-12): bütçe HAM bayt üzerinden ölçülmez. Üst harness (Claude Code
≥2.1.211) MEMORY.md'yi yüklemeden ÖNCE baştaki YAML frontmatter'ı ve BLOK seviyesindeki
HTML yorumlarını (`<!-- ... -->`) SOYAR — bunlar 200-satır/25KB bütçesine SAYILMAZ.
KAYNAK (resmî, doğrulandı 2026-08-12): code.claude.com/docs/en/memory — *"YAML frontmatter
and block-level HTML comments are stripped before the index is loaded… Before v2.1.211,
Claude Code measured the raw file"*. Yani bu, sürüme bağlı bir DAVRANIŞ DEĞİŞİKLİĞİDİR. Ham
ölçüm, bakım-notu eklendiğinde SAHTE ALARM verir (ve alarm-yorgunluğu gerçek dolulukları
görünmez kılar). Ölçüm bu yüzden `_yukleme_govdesi()` çıktısı üzerinden yapılır.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

# Resmî limitler — code.claude.com/docs/en/memory ("first 200 lines or 25KB")
BAYT_TAVAN = 25 * 1024
SATIR_TAVAN = 200
UYARI_ORAN, FAIL_ORAN = 0.85, 0.95

LINK_RE = re.compile(r"\]\(([^)]+\.md)\)")
WIKI_RE = re.compile(r"\[\[([^\]]+)\]\]")
FENCE_RE = re.compile(r"^\s{0,3}(```|~~~)")


def _yukleme_govdesi(metin: str) -> str:
    """Bütçeye GERÇEKTEN sayılan gövde: harness'in soyduğu parçalar düşülmüş metin.

    Soyulanlar: (a) dosyanın EN BAŞINDAKİ YAML frontmatter bloğu, (b) BLOK seviyesinde
    açılan HTML yorumları.

    Sınırlar bilinçli — şüphede **FAZLA ölçmek** doğru yöndür (fazla ölçüm en kötü
    ihtimalle erken uyarı verir; az ölçüm dosyanın SONUNUN sessizce düşmesi demektir):
      * kod-fence (``` / ~~~) İÇİNDE hiçbir şey soyulmaz — örnek olarak gösterilen
        frontmatter/yorum gerçek yüktür;
      * yorum yalnız SATIR BAŞINDA açılıyorsa blok sayılır (satır-içi `metin <!-- x -->`
        yorumu gövdenin ortasındadır, ölçümden düşülmez);
      * KAPANMAMIŞ `<!--` ve kapanmamış frontmatter SOYULMAZ (dosyanın kalanını yutmak
        bütçeyi olduğundan küçük gösterirdi).
    """
    satirlar = metin.splitlines(keepends=True)
    n = len(satirlar)
    i = 0
    if n and satirlar[0].strip() == "---":
        for j in range(1, n):
            if satirlar[j].strip() in ("---", "..."):
                i = j + 1          # kapanmayan frontmatter → i=0 kalır (soyma yok)
                break

    cikti: list[str] = []
    fence: str | None = None
    while i < n:
        s = satirlar[i]
        kirpik = s.strip()
        if fence is not None:
            cikti.append(s)
            if kirpik.startswith(fence):
                fence = None
            i += 1
            continue
        f = FENCE_RE.match(s)
        if f:
            fence = f.group(1)
            cikti.append(s)
            i += 1
            continue
        if kirpik.startswith("<!--"):
            kapanis = next((j for j in range(i, n) if "-->" in satirlar[j]), None)
            if kapanis is None:                    # kapanmamış → soyma YOK
                cikti.append(s)
                i += 1
                continue
            kalan = satirlar[kapanis].split("-->", 1)[1]
            if kalan.strip():
                cikti.append(kalan)
            i = kapanis + 1
            continue
        cikti.append(s)
        i += 1
    return "".join(cikti)


def _memory_dizini(proj: Path) -> tuple[Path | None, str]:
    """Auto-memory dizini: `~/.claude/projects/<slug>/memory/`.

    Slug DETERMİNİSTİK türetilir: proje yolundaki alfanümerik olmayan her karakter '-'.
    (`C:\\IX\\Proje` → `C--IX-Proje`.)

    ⚠ Önceki sürüm "adı içeren tek dizin" sezgisiyle arıyordu; donmuş eski dünyanın
    aynı-adlı dizini de eşleşince İKİ aday çıkıyor ve validator **sessizce atlıyordu**
    — yani asıl bütçe kontrolü hiç koşmadan "[OK]" basıyordu. Bulunamadı ≠ sorun yok.
    """
    ozel = os.environ.get("CLAUDE_AUTO_MEMORY_DIR")
    if ozel:
        p = Path(os.path.expanduser(ozel))
        return (p if p.is_dir() else None), str(p)
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(proj))
    p = Path(os.path.expanduser("~")) / ".claude" / "projects" / slug / "memory"
    return (p if p.is_dir() else None), str(p)


def _butce(idx: Path, hatalar: list[str], uyarilar: list[str]) -> None:
    ham = idx.read_bytes()
    govde = _yukleme_govdesi(ham.decode("utf-8", errors="replace"))
    govde_bayt = len(govde.encode("utf-8", errors="replace"))
    satir = len(govde.splitlines())
    soyulan = len(ham) - govde_bayt
    ek = (f" [ham {len(ham)} B; soyulan frontmatter/HTML-yorum {soyulan} B bütçeye SAYILMAZ]"
          if soyulan > 0 else "")
    for ad, deger, tavan in (("bayt", govde_bayt, BAYT_TAVAN), ("satır", satir, SATIR_TAVAN)):
        oran = deger / tavan
        mesaj = (f"MEMORY.md {ad} doluluğu %{oran*100:.0f} ({deger}/{tavan}). "
                 f"Tavan aşılınca dosyanın SONU sessizce yüklenmez." + ek)
        if oran >= FAIL_ORAN:
            hatalar.append("[FAIL] " + mesaj)
        elif oran >= UYARI_ORAN:
            uyarilar.append("[WARN] " + mesaj)


def _butunluk(dizin: Path, etiket: str, hatalar: list[str]) -> None:
    idx = dizin / "MEMORY.md"
    if not idx.is_file():
        hatalar.append(f"[FAIL] {etiket}: MEMORY.md yok")
        return
    metin = idx.read_text(encoding="utf-8", errors="replace")
    dosyalar = {p.name for p in dizin.glob("*.md") if p.name != "MEMORY.md"}

    # 1) ölü indeks linki
    linkli = set(LINK_RE.findall(metin))
    for l in sorted(linkli - dosyalar):
        hatalar.append(f"[FAIL] {etiket}: MEMORY.md ölü link → '{l}' diskte yok")

    # 2) erişilebilirlik: indeksten doğrudan VEYA tek-hop wiki-link ile
    erisilir = set(linkli) & dosyalar
    for ad in list(erisilir):
        govde = (dizin / ad).read_text(encoding="utf-8", errors="replace")
        for w in WIKI_RE.findall(govde):
            aday = w if w.endswith(".md") else w + ".md"
            if aday in dosyalar:
                erisilir.add(aday)
    for ad in sorted(dosyalar - erisilir):
        hatalar.append(f"[FAIL] {etiket}: '{ad}' indeksten erişilemez "
                       f"(MEMORY.md'ye satır ekle ya da bir hatıradan [[link]] ver)")

    # 3) frontmatter şeması
    for ad in sorted(dosyalar):
        bas = (dizin / ad).read_text(encoding="utf-8", errors="replace")[:600]
        if not bas.startswith("---"):
            hatalar.append(f"[FAIL] {etiket}: '{ad}' frontmatter yok")
            continue
        for alan in ("name:", "description:"):
            if alan not in bas:
                hatalar.append(f"[FAIL] {etiket}: '{ad}' frontmatter'ında '{alan}' yok")
        if not re.search(r"type:\s*(user|feedback|project|reference)", bas):
            hatalar.append(f"[FAIL] {etiket}: '{ad}' metadata.type yok/geçersiz")


def main() -> int:
    core = Path(__file__).resolve().parents[2]
    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()

    hatalar: list[str] = []
    uyarilar: list[str] = []

    mem, beklenen_yol = _memory_dizini(proj)
    atlandi = mem is None
    if mem is not None:
        if (mem / "MEMORY.md").is_file():
            _butce(mem / "MEMORY.md", hatalar, uyarilar)
        _butunluk(mem, "auto-memory", hatalar)
    else:
        # SESSİZ ATLAMA YASAK: "KOŞMADI" ile "sorun yok" ayırt edilebilir olmalı — SKIP
        # satırı vardı ama alttaki tek başına okunan "[OK]" onu yutuyordu (CI log'unda
        # denetim koşmuş sanılır). Nerede aradığımızı da yaz.
        print("  [SKIP] auto-memory dizini yok (CI ortamı olabilir) — bütçe denetimi "
              "bu ortamda KOŞMADI")
        print(f"         aranan yol: {beklenen_yol}")

    seed = core / "claude" / "memory-seed"
    if seed.is_dir():
        _butunluk(seed, "memory-seed", hatalar)

    for u in uyarilar:
        print("  " + u)
    for h in hatalar:
        print("  " + h)
    if hatalar:
        print(f"\n  Toplam {len(hatalar)} ihlal (C-MEM-01).")
        return 1
    if atlandi:
        print("  [OK] memory-seed bütünlüğü — auto-memory bütçesi KOŞMADI (yukarıdaki SKIP)")
    else:
        print("  [OK] auto-memory bütçesi + indeks bütünlüğü")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
