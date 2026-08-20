#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""behavior_manifest: I-1 `generate` CERRAHI DEGILDI + I-2 worktree/CRLF SAHTE POZITIFI.

I-1 — `generate` tum yuzeyi bastan damgaliyordu ⇒ o an bekleyen HER sapmayi topluca
"onaylanmis" yapiyordu. Bir turda olculdu: `verify` **6 sapma** listeliyordu ve
`generate` altisini da SESSIZCE aklardi (bilincli olanlari da olmayanlari da). Bu,
koruma mekanizmasini "ya hep ya hic" hale getirir ve pratikte KULLANILAMAZ kilar.
⭐ TASARIM KISITI: `behavior-manifest.json` **gitignore'dadir** (makine-lokal) ⇒
degisikligi bir PR'da kimse GOREMEZ. Tek denetim yuzeyi script'in CIKTISIDIR — bu
yuzden `generate` artik NEYI onayladigini ve NEYI beklemede biraktigini satir satir basar.

I-2 — tarayici `.claude/worktrees/**`i kapsiyordu ⇒ SAHTE POZITIF. Olculdu: 3 worktree
`CLAUDE.md`si kokun CRLF'li kopyasi — kok `888e7624…` (5841 B, LF=71) · worktree
`337bd842…` (5912 B, CRLF=71) · **kok LF→CRLF cevrilince sha `337bd842…`** ⇒ icerik
farki SIFIR. Her yeni ajan worktree'si ayni uyariyi yeniden uretirdi = UYARI KORLUGU.

⚠⚠ IKI GEVSETME (bilincli, kullanici onayli) — POZITIF KONTROLLU:
   (a) `worktrees` prune'a eklendi  -> S1 FP kaniti · **S2 gercek ihlal HALA yakalanir**
   (b) `_hash` satir-sonu normalize -> S3 FP kaniti · **S4 tek karakterlik gercek
       degisiklik HALA yakalanir**
   Gevsetmenin kapiyi KORLETMEDIGI iddiasi S2/S4 ile KANITLANIR; ikisi de mutasyonla
   sinanir. (Kapsam daraldi, DEDEKTOR sagl.)

  S1-S2  worktree dislama: FP gider · ⭐ ana agactaki GERCEK dosya taranir
  S3-S4  CRLF normalize: FP gider · ⭐ tek karakterlik GERCEK degisiklik yakalanir
  S5-S6  `--only`: yalniz verileni onaylar · digeri BEKLEMEDE (verify hala rc=1)
  S7     duz `generate` onayladiklarini LISTELER + TOPLU ONAY uyarisi
  S8-S9  fail-closed: bilinmeyen yol · manifest yokken `--only`
  M1-M4  fix'i sok -> korpus KIRMIZI olmali

Kosum: python tests/fixtures/manifest_secici_onay/run.py     (exit 0 = PASS)
"""
from __future__ import annotations

import io
import shutil
import sys
import tempfile
import types
from contextlib import redirect_stdout
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[2]
BM_PATH = CORE / "scripts" / "behavior_manifest.py"


def _yukle(src: str):
    mod = types.ModuleType("behavior_manifest_x")
    mod.__file__ = str(BM_PATH)
    exec(compile(src, str(BM_PATH), "exec"), mod.__dict__)
    return mod


def _proje() -> Path:
    """Sentetik proje: kok CLAUDE.md + rules + settings + worktree KOPYASI (CRLF)."""
    d = Path(tempfile.mkdtemp(prefix="bmfix_"))
    (d / ".claude" / "rules").mkdir(parents=True)
    (d / ".claude" / "worktrees" / "agent-x").mkdir(parents=True)
    (d / "CLAUDE.md").write_bytes(b"kok talimat\nikinci satir\n")
    (d / ".claude" / "rules" / "a.md").write_bytes(b"kural bir\n")
    (d / ".claude" / "settings.json").write_bytes(b"{}\n")
    # worktree kopyasi: AYNI icerik, CRLF (gercek vakanin birebir sekli)
    (d / ".claude" / "worktrees" / "agent-x" / "CLAUDE.md").write_bytes(
        b"kok talimat\r\nikinci satir\r\n")
    return d


def senaryolar(mod) -> list[tuple[str, bool, str]]:
    out = []

    def ekle(ad, kosul, detay=""):
        out.append((ad, bool(kosul), detay))

    d = _proje()
    try:
        # --- S1: worktree dislandi (FP kaniti) -----------------------------
        kayit = mod._topla(d)
        wt = [k for k in kayit if "worktrees" in k]
        ekle("S1 GEVSETME-FP: worktree CLAUDE.md manifest'e GIRMEZ",
             not wt and "CLAUDE.md" in kayit, "worktree_anahtarlari=%s" % wt)

        # --- S2: ⭐ POZITIF KONTROL — ana agacta GERCEK dosya taranir ------
        (d / "alt").mkdir()
        (d / "alt" / "CLAUDE.md").write_bytes(b"alt agac talimati\n")
        kayit2 = mod._topla(d)
        ekle("S2 POZITIF KONTROL: ana agactaki GERCEK nested CLAUDE.md TARANIR",
             "alt/CLAUDE.md" in kayit2,
             "anahtarlar=%s" % sorted(kayit2)[:5])
        shutil.rmtree(d / "alt")

        # --- S3: CRLF farki sapma URETMEZ (FP kaniti) ----------------------
        with redirect_stdout(io.StringIO()):
            mod.generate(d)
        (d / "CLAUDE.md").write_bytes(b"kok talimat\r\nikinci satir\r\n")   # yalniz CRLF
        ekle("S3 GEVSETME-FP: yalniz satir-sonu degisiminde SAPMA YOK",
             mod.verify_quiet(d) == [], "sapma=%s" % mod.verify_quiet(d))

        # --- S4: ⭐ POZITIF KONTROL — TEK KARAKTER degisiklik YAKALANIR ----
        (d / "CLAUDE.md").write_bytes(b"kok talimat\r\nikinci satirX\r\n")
        s4 = mod.verify_quiet(d)
        ekle("S4 POZITIF KONTROL: tek karakterlik GERCEK degisiklik YAKALANIR",
             any("CLAUDE.md" in x and "DEĞİŞMİŞ" in x for x in s4), "sapma=%s" % s4)
        (d / "CLAUDE.md").write_bytes(b"kok talimat\nikinci satir\n")

        # --- S5/S6: `--only` secici onay -----------------------------------
        with redirect_stdout(io.StringIO()):
            mod.generate(d)
        (d / "CLAUDE.md").write_bytes(b"kok DEGISTI\n")
        (d / ".claude" / "rules" / "a.md").write_bytes(b"kural DEGISTI\n")
        with redirect_stdout(io.StringIO()):
            _, onaylanan, bekleyen = mod.generate(d, only=["CLAUDE.md"])
        ekle("S5 --only: YALNIZ verilen yol onaylanir, digeri BEKLEMEDE kalir",
             onaylanan == ["CLAUDE.md"] and len(bekleyen) == 1
             and "rules/a.md" in bekleyen[0],
             "onaylanan=%s bekleyen=%s" % (onaylanan, bekleyen))
        kalan = mod.verify_quiet(d)
        ekle("S6 --only sonrasi verify HALA sapma gosterir (toplu aklama YOK)",
             len(kalan) == 1 and "rules/a.md" in kalan[0], "kalan=%s" % kalan)

        # --- S7: duz `generate` NE ONAYLADIGINI basar ----------------------
        buf = io.StringIO()
        with redirect_stdout(buf):
            mod.main_test_yardimcisi = None
            _, ona, _ = mod.generate(d)
        # main() ciktisini ayrica olcmek icin dogrudan cagri:
        ekle("S7 duz generate onayladigi sapmalari DONDURUR (gorunurluk)",
             len(ona) >= 1, "onaylanan=%s" % ona)

        # --- S8/S9: fail-closed dallar -------------------------------------
        try:
            with redirect_stdout(io.StringIO()):
                mod.generate(d, only=["olmayan/yol.md"])
            s8 = False
        except SystemExit:
            s8 = True
        ekle("S8 fail-closed: bilinmeyen --only yolu -> SystemExit (sessiz gecmez)", s8)

        d2 = _proje()
        try:
            try:
                with redirect_stdout(io.StringIO()):
                    mod.generate(d2, only=["CLAUDE.md"])
                s9 = False
            except SystemExit:
                s9 = True
            ekle("S9 fail-closed: manifest YOKKEN --only -> SystemExit", s9)
        finally:
            shutil.rmtree(d2, ignore_errors=True)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    return out


MUTASYONLAR = [
    ("M1 worktree prune'unu geri al (I-2 sahte pozitifi geri gelsin)",
     lambda s: s.replace('"__pycache__", "worktrees"}', '"__pycache__"}')),
    ("M2 satir-sonu normalizasyonunu sok (CRLF FP'si geri gelsin)",
     lambda s: s.replace(
         '    normal = ham.replace(b"\\r\\n", b"\\n").replace(b"\\r", b"\\n")\n'
         "    h = hashlib.sha256()\n    h.update(normal)",
         "    h = hashlib.sha256()\n    h.update(ham)")),
    ("M3 --only'yi yok say (her zaman TAM generate = I-1 geri)",
     lambda s: s.replace("    if only is None:\n", "    if True:\n")),
    ("M4 onaylanan listesini BOSALT (gorunurluk kalksin)",
     lambda s: s.replace("        onaylanan = sorted(set(canli) -",
                         "        onaylanan = []; _ = sorted(set(canli) -")),
]


def main() -> int:
    print("=" * 78)
    print("manifest_secici_onay — I-1 cerrahi onay + I-2 worktree/CRLF sahte pozitifi")
    print("=" * 78)

    ham = BM_PATH.read_text(encoding="utf-8")
    mod = _yukle(ham)
    sonuc = senaryolar(mod)
    kirik = [(a, d) for a, ok, d in sonuc if not ok]
    for ad, ok, detay in sonuc:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok:
            print("         gorulen: %s" % detay)
    print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

    print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
    mut_kirik, yama_kirik = [], []
    for ad, mut in MUTASYONLAR:
        bozuk = mut(ham)
        if bozuk == ham:
            print("  [YAMA TUTMADI] %s" % ad)
            yama_kirik.append(ad)
            continue
        try:
            m_res = senaryolar(_yukle(bozuk))
            yakalandi = any(not ok for _, ok, _ in m_res)
            kacan = [a for a, ok, _ in m_res if not ok]
        except BaseException as e:
            yakalandi, kacan = False, []
            print("  [KURULAMADI] %s -> %s: %s" % (ad, type(e).__name__, e))
        print("  [%s] %s" % ("YAKALANDI" if yakalandi else "KACTI", ad))
        if yakalandi:
            print("         kiran senaryo(lar): %s" % ", ".join(kacan[:3]))
        else:
            mut_kirik.append(ad)

    print("\n" + "=" * 78)
    if kirik or mut_kirik or yama_kirik:
        if kirik:
            print("FAIL — senaryo: %s" % ", ".join(a for a, _ in kirik))
        if mut_kirik:
            print("FAIL — mutasyon KACTI: %s" % ", ".join(mut_kirik))
        if yama_kirik:
            print("FAIL — mutasyon yamasi kaynaga UYMADI: %s" % ", ".join(yama_kirik))
        return 1
    print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(MUTASYONLAR)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
