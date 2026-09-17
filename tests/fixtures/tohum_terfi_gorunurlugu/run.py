#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TOHUM TERFI GORUNURLUGU korpusu (Q325, 2026-09-18).

NEDEN BU KORPUS VAR
-------------------
`seed_memory.py` TEK YONLUDUR: tohum -> makine. Bu makinede yazilan bir metodoloji
dersinin tohuma girip girmedigini soyleyen HICBIR yuzey yoktu; karar hicbir yerde
kaydedilmiyordu. Sonuc olculdu: tohum `team_setup` zincirinde kosar ve merge-safe'tir,
yani tohum bayatsa yalniz yeni kurulum degil MEVCUT makinelerin her guncellemesi eksik
kalir — ve bu eksiklik hicbir kapida gorunmez.

`--terfi-adaylari` bir KAPI DEGILDIR (ADR 0019 merdiveni + kullanici karari): hedef repo
PUBLIC, genericize yargi ister. Arac LISTELER, insan KARAR VERIR. Bu korpus tam da bunu
civiler — "yazmadigi" bir sozlesme oldugu icin, once SALT-OKUNURLUK olculur.

CIVILENEN DORT SOZLESME
  S  SALT-OKUNURLUK : hicbir dosya yazilmaz/yaratilmaz. `main()` icindeki erken donus
                      `target.mkdir()`ten ONCE olmali (akista garanti, sozde degil).
  K  KOVA SEMANTIGI : etiket YOKSA bu "hayir" DEGIL "karar verilmedi"dir. Bu ayrim
                      kaydin kendisidir: onceki turlarda BILEREK disarida birakilan
                      dersler ile hic bakilmamislar birbirine karismisti.
  D  SAPMA + GURULTU: iki yon (yerelde duzenlenmis / tohum ilerlemis) AYRI sayilir ve
                      CRLF-only fark GURULTU kovasina duser. Olculdu (canli memory):
                      ham sha ile (b)=26 gorunuyordu, normalize edilince GERCEK fark 0 —
                      yani arac 26 kalemlik HAYALI is uretecekti.
  B  KAPSAM BEYANI  : core §7 — "0 bulgu" != "dogru". Blocklist girdi sayisi ve
                      taranmayan dosya turleri HER kosumda basilir.

KOSUM:  python tests/fixtures/tohum_terfi_gorunurlugu/run.py [--mutasyon-<kip>]
Cikis:  0 hepsi beklendigi gibi · 1 sapma · 2 DOGRULANAMADI (capa tutmadi / mutant bozuk)

MUTASYON (korpusun bos-yesil olmadigini kanitlar):
  --mutasyon-yazar          erken donus etkisizlesir (yazma yoluna duser)  -> S DUSMELI
  --mutasyon-etiketsiz-hayir etiket yoksa "hayir" sayilir                   -> K DUSMELI
  --mutasyon-gurultu-sayilir CRLF normalizasyonu kalkar                     -> D DUSMELI
  --mutasyon-beyansiz        blocklist kapsam satiri silinir                -> B DUSMELI
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
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
SCRIPTS = REPO / "scripts"

# Kimlik sondasi: GERCEK bir musteri/sistem adi bu dosyaya YAZILAMAZ (core public).
# Blocklist `IX_GENERICIZE_BLOCKLIST` ile sabitlenir -> agsiz, makineden bagimsiz,
# ve "blocklist bos" fail-closed dali ile karistirilamaz.
SENTINEL = "SENTINEL" + "-MUSTERI"

MUTLAR = {
    "--mutasyon-yazar": ("    if args.terfi_adaylari:",
                         "    if args.terfi_adaylari and False:"),
    "--mutasyon-etiketsiz-hayir": ('        return "<YOK>", ""',
                                   '        return "hayir", ""'),
    "--mutasyon-gurultu-sayilir": (
        'gurultu = yb.replace(b"\\r\\n", b"\\n") == tb.replace(b"\\r\\n", b"\\n")',
        'gurultu = False'),
    "--mutasyon-beyansiz": (
        'print(f"  · Kimlik taraması BLOCKLIST\'E BAĞLIDIR ({len(desenler)} girdi): '
        'listede olmayan bir")',
        'print("  · (kapsam notu)")'),
}

SONUC: list[tuple[str, bool, str]] = []


def ekle(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(ok), detay))


def _sil(d: Path) -> None:
    """Q319: Windows'ta salt-okur girdi `rmtree(ignore_errors=True)` ile SESSIZCE kalir."""
    def _ac(func, path, _exc):                       # noqa: ANN001
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass
    kw = {"onexc": _ac} if sys.version_info >= (3, 12) else {"onerror": _ac}
    try:
        shutil.rmtree(d, **kw)                       # type: ignore[arg-type]
    except Exception:
        shutil.rmtree(d, ignore_errors=True)


def _agac(d: Path) -> dict:
    return {str(p.relative_to(d)): hashlib.md5(p.read_bytes()).hexdigest()
            for p in sorted(d.rglob("*")) if p.is_file()}


def _ders(ad: str, govde: str = "govde", seed: str | None = None) -> str:
    meta = f"  type: feedback\n" + (f"  seed: {seed}\n" if seed else "")
    return (f"---\nname: {ad}\ndescription: test dersi\nmetadata:\n{meta}---\n\n{govde}\n")


def main() -> int:
    gecerli = set(MUTLAR)
    for a in sys.argv[1:]:
        if a.startswith("--mutasyon") and a not in gecerli:
            raise SystemExit(f"[KULLANIM] bilinmeyen mutasyon kipi: {a} -> gecerli: "
                             + " ".join(sorted(gecerli)))
    secili = next((a for a in sys.argv[1:] if a in gecerli), None)

    tmp = Path(tempfile.mkdtemp(prefix="tohum_terfi_"))
    try:
        # ── sandbox core: gercek script'ler + sentetik tohum ────────────────────
        core = tmp / "core"
        (core / "scripts" / "utils").mkdir(parents=True)
        (core / "claude" / "memory-seed").mkdir(parents=True)
        for ad in ("seed_memory.py", "genericize_common.py", "build_recall_index.py"):
            shutil.copy2(SCRIPTS / ad, core / "scripts" / ad)
        for p in (SCRIPTS / "utils").glob("*.py"):
            shutil.copy2(p, core / "scripts" / "utils" / p.name)
        betik = core / "scripts" / "seed_memory.py"

        if secili:
            eski, yeni = MUTLAR[secili]
            kaynak = betik.read_text(encoding="utf-8")
            if eski not in kaynak:
                print(f"[DOGRULANAMADI] mutasyon capasi bulunamadi ({secili}) -> "
                      "mutasyon UYGULANMADI; 'gecti' sonucu ANLAMSIZ olurdu.")
                return 2
            betik.write_text(kaynak.replace(eski, yeni, 1), encoding="utf-8", newline="\n")
            try:
                compile(betik.read_text(encoding="utf-8"), str(betik), "exec")
            except SyntaxError as e:
                print(f"[DOGRULANAMADI] mutant SOZDIZIMI BOZUK ({secili}): {e}")
                return 2

        seed = core / "claude" / "memory-seed"
        # tohumda OLAN dersler (sapma eksenleri burada kurulur)
        (seed / "feedback_ayni.md").write_text(_ders("ayni"), encoding="utf-8", newline="\n")
        (seed / "feedback_yerel-duzenli.md").write_text(_ders("yerel-duzenli", "TOHUM"),
                                                        encoding="utf-8", newline="\n")
        (seed / "feedback_tohum-ilerledi.md").write_text(_ders("tohum-ilerledi", "YENI TOHUM"),
                                                         encoding="utf-8", newline="\n")
        (seed / "feedback_satir-sonu.md").write_text(_ders("satir-sonu", "GOVDE"),
                                                     encoding="utf-8", newline="\n")
        (seed / "MEMORY.md").write_text("## Feedback\n\n- [a](feedback_ayni.md) — oz\n",
                                        encoding="utf-8", newline="\n")

        # ── hedef memory: tohumda OLMAYAN dersler (kova + kimlik eksenleri) ─────
        hedef = tmp / "mem"
        hedef.mkdir()
        for ad in ("ayni", "yerel-duzenli", "tohum-ilerledi", "satir-sonu"):
            shutil.copy2(seed / f"feedback_{ad}.md", hedef / f"feedback_{ad}.md")
        # manifest = "tohumlandigi andaki" sha (yerel duzenleme ONCESI)
        import json
        man = {p.name: hashlib.sha1(p.read_bytes()).hexdigest()
               for p in sorted(seed.glob("feedback_*.md"))}
        (hedef / ".seed-manifest.json").write_text(json.dumps(man, indent=1),
                                                   encoding="utf-8", newline="\n")
        # (a) yerelde DUZENLENMIS: yerel != tohum ve yerel != manifest sha
        (hedef / "feedback_yerel-duzenli.md").write_text(_ders("yerel-duzenli", "YEREL EKLEME"),
                                                         encoding="utf-8", newline="\n")
        # (b) tohum ILERLEMIS: yerel == manifest sha, tohum farkli
        (seed / "feedback_tohum-ilerledi.md").write_text(_ders("tohum-ilerledi", "TOHUM V2"),
                                                         encoding="utf-8", newline="\n")
        # GURULTU: yalniz satir-sonu farki (yerel CRLF) — (a) yonunde gorunur ama GERCEK degil
        (hedef / "feedback_satir-sonu.md").write_bytes(
            (seed / "feedback_satir-sonu.md").read_bytes().replace(b"\n", b"\r\n"))

        # kova eksenleri (hepsi tohumda YOK)
        (hedef / "feedback_kova-evet.md").write_text(_ders("kova-evet", seed="evet"),
                                                     encoding="utf-8", newline="\n")
        (hedef / "feedback_kova-hayir.md").write_text(_ders("kova-hayir", seed="hayir"),
                                                      encoding="utf-8", newline="\n")
        (hedef / "feedback_kova-hayir-gerekce.md").write_text(
            _ders("kova-hayir-gerekce", seed="hayir:proje-ozel"), encoding="utf-8", newline="\n")
        (hedef / "feedback_kova-bilinmeyen.md").write_text(
            _ders("kova-bilinmeyen", seed="belki"), encoding="utf-8", newline="\n")
        (hedef / "feedback_kova-yok.md").write_text(_ders("kova-yok"), encoding="utf-8", newline="\n")
        # kimlik eksenleri
        (hedef / "feedback_izli-govde.md").write_text(
            _ders("izli-govde", f"musteri {SENTINEL} vakasi", seed="evet"), encoding="utf-8", newline="\n")
        (hedef / f"feedback_izli-ad-{SENTINEL.lower()}.md").write_text(
            _ders("izli-ad", "temiz govde", seed="evet"), encoding="utf-8", newline="\n")
        # KAPSAM DISI olmasi gereken dosyalar
        (hedef / "project_kapsam-disi.md").write_text(
            _ders("kapsam-disi", f"{SENTINEL} burada TARANMAZ"), encoding="utf-8", newline="\n")
        (hedef / "_indeks-a.md").write_text("- [[kova-yok]] — oz\n", encoding="utf-8", newline="\n")
        (hedef / "MEMORY.md").write_text("## Feedback\n\n- [a](feedback_ayni.md) — oz\n",
                                         encoding="utf-8", newline="\n")

        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        env["CLAUDE_PROJECT_DIR"] = str(tmp / "proje")
        env["IX_GENERICIZE_BLOCKLIST"] = SENTINEL

        def kos(target: Path | None, cwd: Path):
            arg = ["--target", str(target)] if target else []
            r = subprocess.run([sys.executable, str(betik), "--terfi-adaylari", *arg],
                               env=env, cwd=str(cwd), capture_output=True, timeout=180)
            return (r.returncode, r.stdout.decode("utf-8", "replace"),
                    r.stderr.decode("utf-8", "replace"))

        # ══ S: SALT-OKUNURLUK ══════════════════════════════════════════════════
        once_h, once_s = _agac(hedef), _agac(seed)
        rc, out, err = kos(hedef, tmp)
        sonra_h, sonra_s = _agac(hedef), _agac(seed)
        ekle("S0 exit 0 + Traceback yok", rc == 0 and "Traceback" not in err,
             f"rc={rc} err={err[:400]!r}")
        ekle("S1 HEDEF agaci DEGISMEZ (md5 once==sonra)", once_h == sonra_h,
             f"fark={sorted(k for k in set(once_h) | set(sonra_h) if once_h.get(k) != sonra_h.get(k))}")
        ekle("S2 TOHUM agaci DEGISMEZ", once_s == sonra_s,
             f"fark={sorted(k for k in set(once_s) | set(sonra_s) if once_s.get(k) != sonra_s.get(k))}")

        # ══ K: KOVA SEMANTIGI ══════════════════════════════════════════════════
        def kova_sayisi(metin: str, ad: str) -> int | None:
            m = re.search(rf"^\s*{re.escape(ad)}\s*:\s*(\d+)", metin, re.MULTILINE)
            return int(m.group(1)) if m else None

        ekle("K1 SAYIM satiri: yerelde-var-tohumda-yok dogru (11 yerel - 4 tohumlu = 7)",
             "yerelde VAR, tohumda YOK : 7" in out,
             f"cikti={[l for l in out.split(chr(10)) if 'tohumda YOK' in l]}")
        ekle("K2 kova 'evet' = 3 (2 kimlik ekseni + 1 duz)", kova_sayisi(out, "evet") == 3,
             f"bulunan={kova_sayisi(out, 'evet')}")
        ekle("K3 kova 'hayir' = 2 (gerekceli + gerekcesiz AYNI kovada)",
             kova_sayisi(out, "hayir") == 2, f"bulunan={kova_sayisi(out, 'hayir')}")
        ekle("K4 gerekce GORUNUR ama zorunlu DEGIL", "proje-ozel×1" in out,
             f"cikti={[l for l in out.split(chr(10)) if 'gerekçe' in l]}")
        ekle("K5 ETIKETSIZ ders '<YOK>' kovasinda — 'hayir' DEGIL (kaydin kendisi)",
             kova_sayisi(out, "<YOK>") == 1, f"bulunan={kova_sayisi(out, '<YOK>')}")
        ekle("K6 TANINMAYAN deger kendi kovasinda (yazim hatasi 'karar verilmedi' olmaz)",
             kova_sayisi(out, "belki") == 1, f"bulunan={kova_sayisi(out, 'belki')}")

        # ══ I: KIMLIK ON-TARAMASI ══════════════════════════════════════════════
        ekle("I1 govdede kimlik izi olan ders IZLI sayilir",
             "feedback_izli-govde.md" in out
             and re.search(r"·\s*feedback_izli-govde\.md\s*\[", out) is not None,
             "izli satirlari '· <ad> [tur:...]' bicimindedir")
        ekle("I2 yalniz DOSYA ADINDA iz tasiyan ders de IZLI (D5)",
             re.search(rf"·\s*feedback_izli-ad-{SENTINEL.lower()}\.md\s*\[", out) is not None,
             f"cikti={[l for l in out.split(chr(10)) if 'izli-ad' in l]}")
        ekle("I3 temiz dersler IZSIZ kovasinda", "✓ feedback_kova-yok.md" in out,
             f"cikti={[l for l in out.split(chr(10)) if 'kova-yok' in l]}")
        ekle("I4 izli + izsiz = aday kumesi (kayip dosya yok)",
             (lambda i, z, a: i is not None and z is not None and a is not None and i + z == a)(
                 *(int(m.group(1)) if m else None for m in (
                     re.search(r"kimlik izi TAŞIYAN\s*:\s*(\d+)", out),
                     re.search(r"izsiz \(doğrudan aday\)\s*:\s*(\d+)", out),
                     re.search(r"kova 'evet' \+ '<YOK>' = (\d+) dosya", out)))),
             f"cikti={[l for l in out.split(chr(10)) if 'izsiz' in l or 'TAŞIYAN' in l]}")
        ekle("I5 KAPSAM DISI dosya (project_*) hic taranmaz",
             "project_kapsam-disi" not in out, "project_* dosyasi ciktida gorunmemeli")

        # ══ D: SAPMA + GURULTU ═════════════════════════════════════════════════
        ekle("D1 (a) yerelde duzenlenmis: 1 gercek + 1 gurultu AYRI",
             "(a) yerelde DÜZENLENMİŞ (geri akış adayı) : 1   [+1 yalnız satır-sonu" in out,
             f"cikti={[l for l in out.split(chr(10)) if '(a)' in l]}")
        ekle("D2 (b) tohum ilerlemis: 1 gercek (bugun gorunmeyen yon)",
             "(b) tohum İLERLEMİŞ, yerel kopya ESKİ     : 1" in out,
             f"cikti={[l for l in out.split(chr(10)) if '(b)' in l]}")
        ekle("D3 gercek sapan dosya ADLARI listelenir",
             "· feedback_yerel-duzenli.md" in out and "· feedback_tohum-ilerledi.md" in out)
        ekle("D4 GURULTU dosyasi gercek kovada LISTELENMEZ",
             "· feedback_satir-sonu.md" not in out,
             "CRLF-only fark is degildir; listelenirse hayali is uretilir")

        # ══ B: KAPSAM BEYANI ═══════════════════════════════════════════════════
        for anahtar, etiket in (
                ("KAPSAM BEYANI", "baslik"),
                ("blocklist girdi sayısı", "blocklist sayisi"),
                ("KARAR VERMEZ", "karar vermez"),
                ("KAPSAM DIŞIDIR", "taranmayan dosya turleri"),
                ("BLOCKLIST'E BAĞLIDIR", "blocklist bagimliligi"),
                ("KOPYALAMAZ", "kopyalamaz")):
            ekle(f"B:{etiket} beyanda VAR", anahtar in out, f"aranan={anahtar!r}")

        # ══ 3. BAGLAM: hic tohumlanmamis makine sekli (hedef dizin YOK) ════════
        # Ayri bir EV: baska cwd, baska proje slug'i, hedef dizin hic yok. Bu sekil
        # `--target`siz cagrida olusur ve "sessizce 0" ile karistirilmamalidir.
        yok = tmp / "proje-yok" / "memory"
        rc2, out2, err2 = kos(yok, tmp)
        ekle("C1 hedef dizin YOKSA exit 0 ama ÖLÇÜLEMEDİ basar (sessiz '0' degil)",
             rc2 == 0 and "ÖLÇÜLEMEDİ" in out2 and "SAYIM" not in out2,
             f"rc={rc2} cikti={out2[-300:]!r}")
        ekle("C2 hedef dizin YARATILMAZ (salt-okunurluk yokluk dalinda da gecerli)",
             not yok.exists(), f"yaratildi mi={yok.exists()}")

        # manifest YOKSA: sapma 'ÖLÇÜLEMEDİ' — 'sapma yok' DEGIL
        hedef2 = tmp / "mem2"
        hedef2.mkdir()
        shutil.copy2(seed / "feedback_ayni.md", hedef2 / "feedback_ayni.md")
        rc3, out3, _ = kos(hedef2, tmp)
        ekle("C3 manifest YOKSA sapma 'ÖLÇÜLEMEDİ' (0 sapma diye okunamaz)",
             rc3 == 0 and "ÖLÇÜLEMEDİ" in out3 and "seed-manifest" in out3,
             f"rc={rc3} cikti={out3[-300:]!r}")
    finally:
        _sil(tmp)

    gecen = sum(1 for _, ok, _ in SONUC if ok)
    print(f"\n=== TOHUM TERFI GORUNURLUGU (Q325) "
          f"{'[' + secili + ']' if secili else '[taban]'} ===")
    for ad, ok, detay in SONUC:
        print(f"  [{'OK ' if ok else 'FAIL'}] {ad}" + (f"   -> {detay}" if not ok else ""))
    print(f"\n{gecen}/{len(SONUC)} OK")
    if secili:
        print(f"  (MUTASYON {secili} — dusmesi BEKLENEN vektorler var; "
              "tam skor 'mutasyon KACTI' demektir)")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
