#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TOHUM GOVDE GUNCELLEMESI korpusu (S1, 2026-10-03).

NEDEN BU KORPUS VAR
-------------------
`seed_memory.py` merge-safe kopyalamasi hedefte VAR olan her dosyayi atliyordu: tohumda
govdesi duzeltilen ders kurulu makineye HIC ulasmiyordu ve arac yine "[OK] Her sey guncel"
diyordu. Ustelik manifest atlanan dosyaya da tohumun YENI sha'sini yaziyordu ⇒
`--terfi-adaylari` raporunda dosya "(b) tohum ilerlemis" kovasindan "(a) yerelde
duzenlenmis" kovasina kayiyor, bayatlik izi siliniyordu (olculdu: sahte "mevcut makine",
2026-10-03).

KULLANICI KARARI (civilenen sozlesme)
  G  dokunulmamis (yerel == manifest ESKI sha) + tohum ilerlemis -> GUNCELLENIR, ozette
     "Guncellendi : N" + ad listesi; manifest yeni sha. Yalniz satir-sonu farkli guncelleme
     ETIKETLENIR (G5; canli kopyada 26 guncellemenin 25'i bu sinifti).
  E  elle duzenlenmis (yerel != eski sha) + tohum ilerlemis -> DOKUNULMAZ + "elle birlestir"
     uyarisi + manifest ESKI sha; "[OK] Her sey guncel" DENMEZ.
  Y  elle duzenlenmis + tohum ILERLEMEMIS -> yapilacak is yok, SESSIZ.
  M  manifest yok / dosya manifestte yok + tohumdan farkli -> DOKUNULMAZ, manifeste YAZILMAZ.
  A  tohumla ayni -> sessiz.
  C  CRLF: karar HAM sha'dir (`_yetimleri_bul` deseni) -> CRLF kopya "duzenlenmis" sayilir
     (ezmeme yonunde yanilir); icerik tohumla ayniysa uyari DEGIL bilgi satiri.
  D  `--dry-run` hicbir sey yazmaz ama "Guncellenecek" listesini basar.
  T  `--terfi-adaylari` kovasi kosumdan sonra dogru kalir (kusurun regresyonu).
  B  (#322, 2026-10-18) `--birlestirildi <dosya>`: elle birlestirilmis kopya (tohumun tamami +
     yerel ek) icin "elle birlestir" uyarisi KAPANIR — manifest tohumun guncel sha'si, sonraki
     kosum sessiz; tohum yeniden ilerlerse uyari GERI gelir. Frontmatter'a harness alani
     (`originSessionId`/`modified`) eklenmis kopyada da calisir (bayt-esitlik aranmaz). Gecersiz
     ad (yol · tohumda yok · yerelde yok · dokunulmamis) ve `--force`/`--terfi-adaylari` ile
     birlikte kullanim -> exit 2 + HICBIR sey yazilmaz. `--prune`/`--dry-run` ile serbest.
     Manifestsiz makinede yetim karari degismez (karar AYRI sozlukten).

KOSUM:  python tests/fixtures/tohum_govde_guncelleme/run.py [--mutasyon-<kip>]
        [--seed-kaynak <dosya>]   (eski surumu olcmek icin: `git show <sha>:scripts/seed_memory.py`)
Cikis (CORE-07): 0 taban yesil · 1 taban kirmizi YA DA mutasyonda dusen kume == pinli kume ·
        2 SAPMA (dusen kume pinli kumeden farkli) · 3 DOGRULANAMADI (capa != 1 / derlenmedi)

Mutasyon sandbox KOPYASINA uygulanir (gecici dizin); canli dosyaya yazilmaz.
"""
from __future__ import annotations

import hashlib
import json
import os
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

# kip -> (eski, yeni) — capa kaynakta TAM 1 kez gecmeli
_MUT = {
    # dokunulmamis dosya guncellenmez (kusurun ilk yarisi geri gelir)
    "--mutasyon-guncelleme-yok": (
        '\n    return "guncelle"\n',
        '\n    return "yerel-ileri"\n'),
    # duzenlenmis kontrolu kalkar -> kullanici duzenlemesi EZILIR
    "--mutasyon-duzenleneni-ez": (
        "    if yerel_sha != eski_sha:\n",
        "    if False:\n"),
    # manifest kaydi olmayan dosya "dokunulmamis" sayilir -> ayirt edilemeyen EZILIR
    "--mutasyon-manifestsiz-ez": (
        '        return "ayirt-edilemez"\n',
        '        return "guncelle"\n'),
    # "tohumla ayni" dali kalkar
    "--mutasyon-ayni-yok": (
        '    if yerel_sha == tohum_sha:\n        return "ayni"\n',
        '    pass\n'),
    # kusurun ikinci yarisi: manifest HER tohum dosyasina yeni sha yazar
    "--mutasyon-manifest-hepsi-yeni": (
        "        yeni_manifest = {ad: manifest_sha[ad] for ad in sorted(manifest_sha)}\n",
        "        yeni_manifest = {f.name: _sha(f) for f in seed_files}\n"),
    # atlanan dosyanin ESKI sha'si korunmaz (kayit duser)
    "--mutasyon-atlanan-eski-sha-yok": (
        "            elif eski_sha is not None:\n                manifest_sha[f.name] = eski_sha\n",
        ""),
    # dry-run guncelleme dalinda yazar
    "--mutasyon-dry-yazar": (
        "                if not args.dry_run:\n                    shutil.copy2(f, dst)\n"
        "                continue\n",
        "                shutil.copy2(f, dst)\n                continue\n"),
    # elle-birlestirme bekleyen varken "[OK]" denir
    "--mutasyon-ok-yalan": (
        "    elif elle:\n",
        "    elif False:\n"),
    # guncelleme listesinde satir-sonu etiketi kalkar
    "--mutasyon-guncelleme-etiketsiz": (
        '("   (yalnız satır-sonu farkı)" if ss else "")',
        '""'),
    # satir-sonu etiketi kalkar -> icerigi guncel CRLF kopya "elle birlestir" uyarisi alir
    "--mutasyon-satir-sonu-uyari": (
        "                if _yalniz_satir_sonu(dst, f):\n",
        "                if False:\n"),
    # ── #322 `--birlestirildi` ──
    # isaret karara hic yansimaz (kusur geri gelir: uyari kapanmaz)
    "--mutasyon-isaret-yok": (
        "    karar_manifest.update(isaretli)\n",
        "    pass\n"),
    # isaret ESKI manifeste yazilir -> manifestsiz makinede yetim karari kayar
    "--mutasyon-isaret-eski-manifeste": (
        "    karar_manifest = dict(eski_manifest)\n    karar_manifest.update(isaretli)\n",
        "    eski_manifest.update(isaretli)\n    karar_manifest = eski_manifest\n"),
    # dokunulmamis dosya da isaretlenir -> otomatik guncelleme sessizce bastirilir
    "--mutasyon-dokunulmamis-isaretlenir": (
        '_mevcut_dosya_karari(_sha(dst), tohum_sha, eski_manifest.get(ad)) == "guncelle":',
        '_mevcut_dosya_karari(_sha(dst), tohum_sha, eski_manifest.get(ad)) == "-":'),
    # yol denetimi kalkar (savunma derinligi katmani; tohum-uyelik katmani yine reddeder)
    "--mutasyon-yol-kabul": (
        "        if not _ad_gecerli_mi(ad):\n",
        "        if False:\n"),
    # yerel kopya denetimi kalkar
    "--mutasyon-yerelde-yok-kabul": (
        "        if not dst.is_file():\n            hatalar.append(",
        "        if False:\n            hatalar.append("),
    # --force ile birlikte serbest kalir (yerel birlestirme EZILIR)
    "--mutasyon-force-serbest": (
        "    if args.birlestirildi and args.force:\n",
        "    if False:\n"),
    # --terfi-adaylari ile birlikte serbest kalir (isaret sessizce yok sayilir)
    "--mutasyon-terfi-serbest": (
        "    if args.birlestirildi and args.terfi_adaylari:\n",
        "    if False:\n"),
    # uyari satiri cikis komutunu ONERMEZ
    "--mutasyon-ipucu-yok": (
        'f"python core/scripts/seed_memory.py --birlestirildi {ad}{tgt}")',
        '"")'),
}
_GECERLI_KIP = set(_MUT)

# CORE-07: her kipin DUSMESI BEKLENEN vektor kumesi PINLIDIR, esitlikle kiyaslanir.
_BEKLENEN_DUSEN: dict[str, set[str]] = {
    # #322: B9 da duser — dokunulmamis dosyanin karari artik "guncelle" degil, isaret kabul edilir
    "--mutasyon-guncelleme-yok": {"G1", "G2", "G3", "G4", "G5", "D2", "T2", "B9"},
    # yerel-ileri + iki CRLF kopya da ezilir -> Guncellendi sayisi (G2/D2) ve pozitif kontrol (P1)
    # kayar; E4 DUSMEZ: manifestsiz dosya hala uyari uretir (son satir yine [UYARI]).
    # #322: birlestirilmis kopya da EZILIR (B1/B1h/B4/B10 uyari yok) ve isaret "dokunulmamis"
    # sanilip reddedilir (B2/B13/B14). B3 DUSMEZ: B1 kosumu dosyayi zaten V2'ye ezdi -> sessiz.
    "--mutasyon-duzenleneni-ez": {"E1", "E2", "E3", "Y1", "C1", "C2", "C3", "T4", "G2", "D2", "P1",
                                  "B1", "B1h", "B2", "B4", "B10", "B13", "B14"},
    # #322: manifestsiz makinede ayirt-edilemez kopya "dokunulmamis" sanilir -> isaret reddedilir
    "--mutasyon-manifestsiz-ez": {"M1", "M2", "M3", "X1", "X2", "G2", "D2", "B15"},
    # ayni dosya manifestliyse "guncelle"ye, manifestsizse "ayirt-edilemez"e duser
    # #322: guncel makinede "Her şey güncel" yerine "tohumlandı" (B3/B5/B10)
    "--mutasyon-ayni-yok": {"A1", "P1", "G2", "D2", "R1", "X2", "B3", "B5", "B10"},
    # Y2 DUSMEZ: yerel-ileri'de tohum ilerlemedi, yeni sha == eski sha
    # #322: kusurun TERS yuzu — bayraksiz da uyari kapanir (B1/B1h) ve geri gelen uyaridan
    # sonra manifest V3'e kayar (B4)
    "--mutasyon-manifest-hepsi-yeni": {"E2", "C1", "M2", "X2", "B1", "B1h", "B4"},
    # #322: isaretli dosyanin sha'si da yazilmaz -> sonraki kosum yine uyarir
    "--mutasyon-atlanan-eski-sha-yok": {"E2", "Y2", "C1", "T4",
                                        "B1", "B2", "B3", "B4", "B10", "B14", "B15"},
    "--mutasyon-dry-yazar": {"D1", "T3"},
    "--mutasyon-ok-yalan": {"E4", "B1", "B4", "B10"},
    "--mutasyon-satir-sonu-uyari": {"C2"},
    "--mutasyon-guncelleme-etiketsiz": {"G5"},
    # ── #322 kipleri ──
    "--mutasyon-isaret-yok": {"B2", "B3", "B4", "B10", "B14", "B15"},
    "--mutasyon-isaret-eski-manifeste": {"B15"},
    "--mutasyon-dokunulmamis-isaretlenir": {"B9"},
    "--mutasyon-yol-kabul": {"B6"},
    "--mutasyon-yerelde-yok-kabul": {"B8"},
    "--mutasyon-force-serbest": {"B11"},
    "--mutasyon-terfi-serbest": {"B12"},
    "--mutasyon-ipucu-yok": {"B1h"},
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


def _sha(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()


def _agac(d: Path) -> dict:
    return {str(p.relative_to(d)): hashlib.md5(p.read_bytes()).hexdigest()
            for p in sorted(d.rglob("*")) if p.is_file()}


def _ders(ad: str, govde: str) -> bytes:
    return (f"---\nname: {ad}\ndescription: test dersi {ad}\nmetadata:\n  type: feedback\n"
            f"---\n\n{govde}\n").encode("utf-8")


def _crlf(b: bytes) -> bytes:
    return b.replace(b"\n", b"\r\n")


# ── tohum V1 (makinenin kuruldugu an) ve V2 (tohum ilerledi) ────────────────────
V1 = {
    "feedback_dokunulmamis.md": _ders("dokunulmamis", "ESKI GOVDE"),
    "feedback_duzenlenmis.md": _ders("duzenlenmis", "ESKI GOVDE"),
    "feedback_yerel-ileri.md": _ders("yerel-ileri", "SABIT GOVDE"),
    "feedback_ayni.md": _ders("ayni", "DEGISMEYEN"),
    "feedback_crlf-eski.md": _ders("crlf-eski", "ESKI GOVDE"),
    "feedback_crlf-guncel.md": _ders("crlf-guncel", "ESKI GOVDE"),
    "_indeks-hub.md": b"# hub\n\n- [[dokunulmamis]] eski oz\n",
    "feedback_crlf-tohum.md": _ders("crlf-tohum", "AYNI ICERIK"),
}
V2 = dict(V1)
V2.update({
    "feedback_dokunulmamis.md": _ders("dokunulmamis", "YENI GOVDE (duzeltme)"),
    "feedback_duzenlenmis.md": _ders("duzenlenmis", "YENI GOVDE (duzeltme)"),
    "feedback_crlf-eski.md": _ders("crlf-eski", "YENI GOVDE (duzeltme)"),
    "feedback_crlf-guncel.md": _ders("crlf-guncel", "YENI GOVDE (duzeltme)"),
    "_indeks-hub.md": b"# hub\n\n- [[dokunulmamis]] yeni oz\n",
    "feedback_manifestsiz.md": _ders("manifestsiz", "TOHUM GOVDESI"),
    "feedback_yeni.md": _ders("yeni", "YENI DERS"),
    # tohumun YALNIZ satir sonu degisti (canli kopyada 26 guncellemenin 25'i bu sinifti)
    "feedback_crlf-tohum.md": _crlf(_ders("crlf-tohum", "AYNI ICERIK")),
})
YEREL_DUZENLI = _ders("duzenlenmis", "ESKI GOVDE + YEREL EKLEME")
YEREL_ILERI = _ders("yerel-ileri", "SABIT GOVDE + YEREL NOT")
YEREL_MANIFESTSIZ = _ders("manifestsiz", "KULLANICININ KENDI DOSYASI")
# #322: tohumun (V2) TAMAMI + korunan yerel ek = elle birlestirilmis kopya
YEREL_BIRLESIK = V2["feedback_duzenlenmis.md"] + b"\n- yerel ek (elle birlestirme sonrasi)\n"
# ayni birlestirme + harness'in frontmatter'a ekledigi alanlar (bayt-esitlik imkansiz)
YEREL_BIRLESIK_FM = YEREL_BIRLESIK.replace(
    b"---\nname:", b"---\noriginSessionId: 00000000-test\nmodified: 2026-10-18T00:00:00Z\nname:", 1)
# tohum V2'den sonra BIR KEZ DAHA ilerler (yalniz duzenlenmis dersin govdesi)
V3 = dict(V2)
V3["feedback_duzenlenmis.md"] = _ders("duzenlenmis", "V3 GOVDE (ikinci duzeltme)")


def _index(adlar) -> bytes:
    return ("# Hafiza\n\n## Feedback\n\n" + "".join(
        f"- [{a[:-3]}]({a}) — oz\n" for a in sorted(adlar) if a.startswith("feedback_"))
    ).encode("utf-8")


def _tohum_yaz(seed: Path, dosyalar: dict) -> None:
    for p in seed.glob("*.md"):
        p.unlink()
    for ad, b in dosyalar.items():
        (seed / ad).write_bytes(b)
    (seed / "MEMORY.md").write_bytes(_index(dosyalar))


def _makine(hedef: Path, kurulum: dict, manifest: bool = True) -> None:
    """`kurulum` tohumuyla kurulmus makine: dosyalar bayt-bayt + manifest = kurulum sha'lari."""
    hedef.mkdir(parents=True)
    for ad, b in kurulum.items():
        (hedef / ad).write_bytes(b)
    (hedef / "MEMORY.md").write_bytes(_index(kurulum))
    if manifest:
        (hedef / ".seed-manifest.json").write_text(
            json.dumps({ad: _sha(b) for ad, b in sorted(kurulum.items())}, indent=1),
            encoding="utf-8", newline="\n")


def _man(hedef: Path) -> dict:
    p = hedef / ".seed-manifest.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def _kova(out: str, bas: str) -> list[str]:
    """`--terfi-adaylari` ciktisinda `bas` ile baslayan kovanin `· <ad>` satirlari."""
    adlar, icinde = [], False
    for s in out.split("\n"):
        t = s.strip()
        if t.startswith(bas):
            icinde = True
            continue
        if icinde and (t.startswith("(") or t.startswith("---")):
            break
        if icinde and t.startswith("· "):
            adlar.append(t[2:].strip())
    return adlar


def main(kip: str | None, kaynak_yolu: Path | None) -> int:
    kaynak = (kaynak_yolu or SCRIPTS / "seed_memory.py").read_text(encoding="utf-8")
    if kip:
        eski, yeni = _MUT[kip]
        n = kaynak.count(eski)
        if n != 1:
            print(f"[DOGRULANAMADI] mutasyon capasi {n} kez eslesti (beklenen 1): {kip} "
                  "-> hicbir sayi raporlanmadi.")
            return 3
        kaynak = kaynak.replace(eski, yeni, 1)
        try:
            compile(kaynak, "seed_memory.py", "exec")
        except SyntaxError as e:
            print(f"[DOGRULANAMADI] mutant DERLENMEDI ({kip}): {e}")
            return 3

    tmp = Path(tempfile.mkdtemp(prefix="tohum_govde_"))
    try:
        # ── sandbox core: (mutant) seed_memory + paylasilan moduller + sentetik tohum ──
        core = tmp / "core"
        (core / "scripts" / "utils").mkdir(parents=True)
        seed = core / "claude" / "memory-seed"
        seed.mkdir(parents=True)
        (core / "scripts" / "seed_memory.py").write_text(kaynak, encoding="utf-8", newline="\n")
        for ad in ("genericize_common.py", "build_recall_index.py"):
            shutil.copy2(SCRIPTS / ad, core / "scripts" / ad)
        for p in (SCRIPTS / "utils").glob("*.py"):
            shutil.copy2(p, core / "scripts" / "utils" / p.name)
        betik = core / "scripts" / "seed_memory.py"

        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        env["CLAUDE_PROJECT_DIR"] = str(tmp / "proje")
        env["IX_GENERICIZE_BLOCKLIST"] = "SENTINEL" + "-X"

        def kos(hedef: Path, *bayrak: str) -> tuple[int, str]:
            r = subprocess.run([sys.executable, str(betik), "--target", str(hedef), *bayrak],
                               env=env, cwd=str(tmp), capture_output=True, timeout=180)
            out = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
            return r.returncode, out

        # ── TABAN MAKINE: V1 ile kurulmus, sonra kullanici dokunuslari ─────────────
        taban = tmp / "taban"
        _makine(taban, V1)
        (taban / "feedback_duzenlenmis.md").write_bytes(YEREL_DUZENLI)
        (taban / "feedback_yerel-ileri.md").write_bytes(YEREL_ILERI)
        (taban / "feedback_crlf-eski.md").write_bytes(_crlf(V1["feedback_crlf-eski.md"]))
        (taban / "feedback_crlf-guncel.md").write_bytes(_crlf(V2["feedback_crlf-guncel.md"]))
        (taban / "feedback_manifestsiz.md").write_bytes(YEREL_MANIFESTSIZ)   # manifestte YOK
        _tohum_yaz(seed, V2)
        m_once = _man(taban)

        def kopya(ad: str) -> Path:
            d = tmp / ad
            shutil.copytree(taban, d)
            return d

        # ══ T1 (kontrol grubu): kosumdan ONCE terfi raporu dokunulmamisi (b)'de gosterir ══
        t0 = kopya("t0")
        rc, out_t0 = kos(t0, "--terfi-adaylari")
        b_once = _kova(out_t0, "(b) tohum")
        ekle("T1 kosum ONCESI (b) kovasi dokunulmamis + hub'i gosterir (kontrol grubu)",
             rc == 0 and "feedback_dokunulmamis.md" in b_once and "_indeks-hub.md" in b_once,
             f"rc={rc} (b)={b_once}")

        # ══ A: NORMAL KOSUM ════════════════════════════════════════════════════════
        a = kopya("a")
        rc, out = kos(a)
        m_a = _man(a)
        ekle("Z0 normal kosum exit 0 + Traceback yok", rc == 0 and "Traceback" not in out,
             f"rc={rc} out={out[-400:]!r}")
        ekle("G1 dokunulmamis + tohum ilerlemis -> govde tohumun YENI hali",
             (a / "feedback_dokunulmamis.md").read_bytes() == V2["feedback_dokunulmamis.md"])
        ekle("G2 ozet 'Güncellendi : 3' + adlar listelenir (ders + hub + satir-sonu)",
             "Güncellendi : 3" in out and "· feedback_dokunulmamis.md" in out
             and "· _indeks-hub.md" in out,
             f"satirlar={[s for s in out.split(chr(10)) if 'Güncellen' in s]}")
        ekle("G3 manifest[dokunulmamis] = tohumun YENI sha'si",
             m_a.get("feedback_dokunulmamis.md") == _sha(V2["feedback_dokunulmamis.md"]),
             f"man={m_a.get('feedback_dokunulmamis.md')}")
        ekle("G5 yalniz satir-sonu guncellemesi ETIKETLI, govde guncellemesi etiketsiz",
             "· feedback_crlf-tohum.md   (yalnız satır-sonu farkı)" in out
             and "· feedback_dokunulmamis.md   (" not in out
             and (a / "feedback_crlf-tohum.md").read_bytes() == V2["feedback_crlf-tohum.md"],
             f"satirlar={[s for s in out.split(chr(10)) if 'crlf-tohum' in s]}")
        ekle("G4 hub (_indeks-*.md) de ayni kuralla guncellenir",
             (a / "_indeks-hub.md").read_bytes() == V2["_indeks-hub.md"])
        ekle("E1 duzenlenmis dosyaya DOKUNULMAZ",
             (a / "feedback_duzenlenmis.md").read_bytes() == YEREL_DUZENLI)
        ekle("E2 manifest[duzenlenmis] = ESKI (kurulum) sha korunur",
             m_a.get("feedback_duzenlenmis.md") == m_once.get("feedback_duzenlenmis.md"),
             f"man={m_a.get('feedback_duzenlenmis.md')} once={m_once.get('feedback_duzenlenmis.md')}")
        uyari = [s for s in out.split("\n") if "elle birleştir" in s and "· " in s]
        ekle("E3 uyari satiri: dosya adi + 'elle birleştir'",
             any("feedback_duzenlenmis.md" in s for s in uyari), f"uyari={uyari}")
        son = [s for s in out.strip().split("\n") if s.strip()][-1] if out.strip() else ""
        ekle("E4 'Her şey güncel' DENMEZ ve son satir [UYARI] (team_setup son satiri basar)",
             "Her şey güncel" not in out and son.startswith("[UYARI]"), f"son={son!r}")
        ekle("Y1 tohum ILERLEMEMIS + yerel duzenli -> dokunulmaz, uyari YOK (sessiz)",
             (a / "feedback_yerel-ileri.md").read_bytes() == YEREL_ILERI
             and not any("feedback_yerel-ileri.md" in s for s in out.split("\n")),
             f"uyari={uyari}")
        ekle("Y2 manifest[yerel-ileri] = ESKI sha korunur",
             m_a.get("feedback_yerel-ileri.md") == m_once.get("feedback_yerel-ileri.md"),
             f"man={m_a.get('feedback_yerel-ileri.md')}")
        ekle("A1 tohumla ayni dosya Guncellendi listesinde YOK + manifest sha ayni",
             "· feedback_ayni.md" not in out
             and m_a.get("feedback_ayni.md") == _sha(V2["feedback_ayni.md"]))
        ekle("N1 tohumda yeni ders eklenir ('Eklendi : 1')",
             "Eklendi : 1" in out and (a / "feedback_yeni.md").read_bytes() == V2["feedback_yeni.md"])
        ekle("N2 eklenen dosyanin manifest kaydi = tohum sha (yoksa sonraki tohum ilerlemesi 'ayirt edilemez' kalir)",
             m_a.get("feedback_yeni.md") == _sha(V2["feedback_yeni.md"]),
             f"man={m_a.get('feedback_yeni.md')}")
        ekle("M1 manifestte OLMAYAN mevcut dosyaya DOKUNULMAZ",
             (a / "feedback_manifestsiz.md").read_bytes() == YEREL_MANIFESTSIZ)
        ekle("M2 manifestte olmayan atlanan dosya manifeste YAZILMAZ",
             "feedback_manifestsiz.md" not in m_a, f"man anahtarlari={sorted(m_a)}")
        ekle("M3 ayirt edilemeyen dosya uyarida (sessizce gecilmez)",
             any("feedback_manifestsiz.md" in s and "ayırt edilemez" in s for s in uyari),
             f"uyari={uyari}")
        ekle("C1 CRLF kopya (eski icerik) -> HAM sha 'duzenlenmis': dokunulmaz + uyari + eski sha",
             (a / "feedback_crlf-eski.md").read_bytes() == _crlf(V1["feedback_crlf-eski.md"])
             and any("feedback_crlf-eski.md" in s for s in uyari)
             and m_a.get("feedback_crlf-eski.md") == m_once.get("feedback_crlf-eski.md"),
             f"uyari={uyari} man={m_a.get('feedback_crlf-eski.md')}")
        ekle("C2 CRLF kopya (GUNCEL icerik) -> uyari DEGIL, satir-sonu bilgi satiri",
             not any("feedback_crlf-guncel.md" in s for s in uyari)
             and "satır-sonu (CRLF↔LF)" in out and "· feedback_crlf-guncel.md" in out,
             f"uyari={uyari}")
        ekle("C3 CRLF guncel kopyaya da DOKUNULMAZ (karar ham sha)",
             (a / "feedback_crlf-guncel.md").read_bytes() == _crlf(V2["feedback_crlf-guncel.md"]))

        # ══ T: TERFI RAPORU KOSUMDAN SONRA (kusurun regresyonu) ═══════════════════════
        rc, out_t = kos(a, "--terfi-adaylari")
        a_k, b_k = _kova(out_t, "(a) yerelde"), _kova(out_t, "(b) tohum")
        ekle("T2 guncellenen dosya kosum SONRASI ne (a) ne (b) kovasinda "
             "(kusurda (a)'ya kayiyordu)",
             rc == 0 and "feedback_dokunulmamis.md" not in a_k
             and "feedback_dokunulmamis.md" not in b_k, f"(a)={a_k} (b)={b_k}")
        ekle("T4 duzenlenmis dosya (a) kovasinda kalir (eski sha korundugu icin)",
             "feedback_duzenlenmis.md" in a_k, f"(a)={a_k}")

        # ══ D: DRY-RUN ═════════════════════════════════════════════════════════════
        d = kopya("d")
        once = _agac(d)
        rc, out_d = kos(d, "--dry-run")
        ekle("D1 --dry-run hedef agaci DEGISMEZ (md5 once==sonra)", once == _agac(d),
             f"fark={sorted(k for k in set(once) | set(_agac(d)) if once.get(k) != _agac(d).get(k))}")
        ekle("D2 --dry-run 'Güncellenecek : 3' + ad listesi basar",
             "Güncellenecek : 3" in out_d and "· feedback_dokunulmamis.md" in out_d,
             f"satirlar={[s for s in out_d.split(chr(10)) if 'Güncellen' in s]}")
        rc, out_dt = kos(d, "--terfi-adaylari")
        ekle("T3 dry-run SONRASI dokunulmamis hala (b) kovasinda",
             "feedback_dokunulmamis.md" in _kova(out_dt, "(b) tohum"),
             f"(b)={_kova(out_dt, '(b) tohum')}")

        # ══ R: IKINCI KOSUM (idempotans) ═══════════════════════════════════════════
        rc, out_r = kos(a)
        ekle("R1 ikinci kosumda 'Güncellendi : 0' (guncellenen artik tohumla ayni)",
             rc == 0 and "Güncellendi : 0" in out_r,
             f"satirlar={[s for s in out_r.split(chr(10)) if 'Güncellen' in s]}")

        # ══ X: MANIFEST HIC YOK (manifest ozelligi oncesi kurulmus makine) ══════════
        x = kopya("x")
        (x / ".seed-manifest.json").unlink()
        rc, out_x = kos(x)
        m_x = _man(x)
        ekle("X1 manifest YOKSA dokunulmamis bile EZILMEZ + 'Her şey güncel' denmez",
             (x / "feedback_dokunulmamis.md").read_bytes() == V1["feedback_dokunulmamis.md"]
             and "Her şey güncel" not in out_x, f"out={out_x[-300:]!r}")
        ekle("X2 manifest YOKSA farkli dosya manifeste yazilmaz, tohumla AYNI olan yazilir",
             "feedback_dokunulmamis.md" not in m_x and "feedback_manifestsiz.md" not in m_x
             and m_x.get("feedback_ayni.md") == _sha(V2["feedback_ayni.md"]),
             f"man anahtarlari={sorted(m_x)}")

        # ══ P: POZITIF KONTROL — guncel makine "[OK] Her şey güncel." der ══════════
        p = tmp / "p"
        _makine(p, V2)
        (p / "feedback_yerel-ileri.md").write_bytes(YEREL_ILERI)   # tohum ilerlemedi → sessiz
        rc, out_p = kos(p)
        ekle("P1 guncel makine: 'Güncellendi : 0' + son satir '[OK] Her şey güncel.'",
             rc == 0 and "Güncellendi : 0" in out_p and "[OK] Her şey güncel." in out_p
             and "[UYARI]" not in out_p, f"out={out_p[-400:]!r}")

        # ══ F: --force hâlâ bilincli ezme yoludur (davranis degismedi) ══════════════
        f_ = kopya("f")
        rc, out_f = kos(f_, "--force")
        ekle("F1 --force duzenlenmisi EZER + manifest yeni sha",
             (f_ / "feedback_duzenlenmis.md").read_bytes() == V2["feedback_duzenlenmis.md"]
             and _man(f_).get("feedback_duzenlenmis.md") == _sha(V2["feedback_duzenlenmis.md"]),
             f"rc={rc}")

        # ══ B: #322 `--birlestirildi` — ELLE BIRLESTIRME SONRASI CIKIS ══════════════════
        # Sahne (Issue #322 receti): makine GUNCEL tohumla (V2) kurulu; duzenlenmis dersin
        # manifest kaydi V1'de (tohum o gunden beri ilerledi), yerel kopya V2'nin TAMAMI + ek.
        DUZ = "feedback_duzenlenmis.md"
        sha_v1, sha_v2 = _sha(V1[DUZ]), _sha(V2[DUZ])

        def b_makine(ad: str, yerel: bytes, manifest: bool = True) -> Path:
            d = tmp / ad
            _makine(d, V2, manifest=manifest)
            (d / DUZ).write_bytes(yerel)
            if manifest:
                m = _man(d)
                m[DUZ] = sha_v1
                (d / ".seed-manifest.json").write_text(json.dumps(m, indent=1),
                                                       encoding="utf-8", newline="\n")
            return d

        def son_satir(o: str) -> str:
            s = [x for x in o.strip().split("\n") if x.strip()]
            return s[-1] if s else ""

        def duz_uyari(o: str) -> list[str]:
            return [s for s in o.split("\n") if DUZ in s and "elle birleştir" in s]

        b = b_makine("b1", YEREL_BIRLESIK)
        rc1, o1 = kos(b)
        rc2, o2 = kos(b)
        ekle("B1 sorunlu kol (kontrol): bayraksiz iki kosumda da [UYARI] + manifest V1'de kalir",
             rc1 == rc2 == 0 and son_satir(o1).startswith("[UYARI]")
             and son_satir(o2).startswith("[UYARI]") and duz_uyari(o2)
             and _man(b).get(DUZ) == sha_v1, f"son={son_satir(o2)!r} man={_man(b).get(DUZ)}")
        ekle("B1h uyari satiri cikis komutunu ONERIR (--birlestirildi <ad> --target <hedef>)",
             any(f"--birlestirildi {DUZ}" in s and "--target" in s for s in duz_uyari(o2)),
             f"uyari={duz_uyari(o2)}")
        rc, ob = kos(b, "--birlestirildi", DUZ)
        ekle("B2 --birlestirildi: manifest = tohumun GUNCEL sha'si, yerel kopyaya DOKUNULMAZ",
             rc == 0 and _man(b).get(DUZ) == sha_v2 and (b / DUZ).read_bytes() == YEREL_BIRLESIK
             and "İşaretlendi : 1" in ob and "[UYARI]" not in ob,
             f"rc={rc} man={_man(b).get(DUZ)} out={ob[-400:]!r}")
        rc, o3 = kos(b)
        ekle("B3 sonraki kosum SESSIZ: '[OK] Her şey güncel.' + manifest tohum sha'sinda kalir",
             rc == 0 and son_satir(o3) == "[OK] Her şey güncel." and "[UYARI]" not in o3
             and _man(b).get(DUZ) == sha_v2, f"son={son_satir(o3)!r} man={_man(b).get(DUZ)}")
        _tohum_yaz(seed, V3)
        try:
            rc, o4 = kos(b)
            ekle("B4 tohum YENIDEN ilerler -> uyari GERI gelir, dosyaya dokunulmaz, manifest V2'de",
                 rc == 0 and son_satir(o4).startswith("[UYARI]") and duz_uyari(o4)
                 and (b / DUZ).read_bytes() == YEREL_BIRLESIK and _man(b).get(DUZ) == sha_v2,
                 f"son={son_satir(o4)!r} man={_man(b).get(DUZ)}")
        finally:
            _tohum_yaz(seed, V2)

        k = b_makine("b5", V2[DUZ])
        rc1, o1 = kos(k)
        rc2, o2 = kos(k)
        ekle("B5 kontrol kolu (bayt-ayni, bayraksiz): iki kosumda da '[OK] Her şey güncel.' + "
             "manifest tohum sha", rc1 == rc2 == 0 and son_satir(o1) == "[OK] Her şey güncel."
             and son_satir(o2) == "[OK] Her şey güncel." and _man(k).get(DUZ) == sha_v2,
             f"son1={son_satir(o1)!r} son2={son_satir(o2)!r}")

        # ── gecersiz kullanim: exit 2 + hedef agaci DEGISMEZ + dogru gerekce ──
        def red(d: Path, beklenen: str, *bayrak: str) -> tuple[bool, str]:
            once = _agac(d)
            rc, o = kos(d, *bayrak)
            return (rc == 2 and beklenen in o and once == _agac(d)
                    and "Traceback" not in o), f"rc={rc} out={o[-300:]!r}"

        g = b_makine("b6", YEREL_BIRLESIK)
        sonuc = [red(g, "yol değil", "--birlestirildi", x)
                 for x in ("../" + DUZ, "alt/" + DUZ, str(g / DUZ), "C:" + DUZ)]
        ekle("B6 yol gecisi reddi (`..`, ayirici, mutlak, surucu) -> exit 2 + 'yol değil'",
             all(ok for ok, _ in sonuc), " | ".join(dt for ok, dt in sonuc if not ok))
        sonuc = [red(g, "tohumda yok", "--birlestirildi", x) for x in ("feedback_yok.md", "MEMORY.md")]
        ekle("B7 tohumda olmayan ad (MEMORY.md dahil) -> exit 2 + 'tohumda yok'",
             all(ok for ok, _ in sonuc), " | ".join(dt for ok, dt in sonuc if not ok))
        (g / "feedback_ayni.md").unlink()
        ok, dt = red(g, "hedefte yok", "--birlestirildi", "feedback_ayni.md")
        ekle("B8 yerelde olmayan dosya -> exit 2 + 'hedefte yok'", ok, dt)
        u = b_makine("b9", V1[DUZ])          # dokunulmamis: yerel == manifest (V1) sha
        ok, dt = red(u, "DOKUNULMAMIŞ", "--birlestirildi", DUZ)
        ekle("B9 dokunulmamis dosya isaretlenemez (otomatik guncellemeyi bastirirdi) -> exit 2",
             ok and (u / DUZ).read_bytes() == V1[DUZ], dt)

        fm = b_makine("b10", YEREL_BIRLESIK_FM)
        rc1, o1 = kos(fm)
        rc2, o2 = kos(fm, "--birlestirildi", DUZ)
        rc3, o3 = kos(fm)
        ekle("B10 frontmatter'a originSessionId/modified eklenmis kopya: once [UYARI], "
             "isaret sonrasi SESSIZ + kapsama BILGI satiri",
             YEREL_BIRLESIK_FM != YEREL_BIRLESIK and son_satir(o1).startswith("[UYARI]")
             and rc2 == 0 and "(tohumun tüm satırları yerel kopyada)" in o2
             and rc3 == 0 and son_satir(o3) == "[OK] Her şey güncel."
             and _man(fm).get(DUZ) == sha_v2, f"son1={son_satir(o1)!r} son3={son_satir(o3)!r}")

        e = b_makine("b11", YEREL_BIRLESIK)
        ok, dt = red(e, "--force birlikte verilemez", "--birlestirildi", DUZ, "--force")
        ekle("B11 --force ile birlikte -> exit 2, yerel birlestirme EZILMEZ", ok, dt)
        ok, dt = red(e, "--terfi-adaylari birlikte verilemez", "--birlestirildi", DUZ,
                     "--terfi-adaylari")
        ekle("B12 --terfi-adaylari ile birlikte -> exit 2 (salt-okunur yol yazmaz)", ok, dt)
        once = _agac(e)
        rc, od = kos(e, "--dry-run", "--birlestirildi", DUZ)
        ekle("B13 --dry-run ile birlikte: agac DEGISMEZ + 'İşaretlenecek : 1'",
             rc == 0 and once == _agac(e) and "İşaretlenecek : 1" in od, f"rc={rc}")

        pr = b_makine("b14", YEREL_BIRLESIK)
        yetim = _ders("eski-yetim", "TOHUMDAN KALKMIS")
        (pr / "feedback_eski-yetim.md").write_bytes(yetim)
        m = _man(pr)
        m["feedback_eski-yetim.md"] = _sha(yetim)
        (pr / ".seed-manifest.json").write_text(json.dumps(m, indent=1), encoding="utf-8",
                                                newline="\n")
        rc, op = kos(pr, "--prune", "--birlestirildi", DUZ)
        ekle("B14 --prune ile birlikte: ikisi de uygulanir (yetim budanir + isaret yazilir)",
             rc == 0 and not (pr / "feedback_eski-yetim.md").exists() and "Budandı : 1" in op
             and _man(pr).get(DUZ) == sha_v2 and "[UYARI]" not in op, f"rc={rc} out={op[-300:]!r}")

        ms = b_makine("b15", YEREL_BIRLESIK, manifest=False)
        (ms / "feedback_eski-yetim.md").write_bytes(yetim)        # manifestsiz: tohum mu? bilinmez
        rc, om = kos(ms, "--birlestirildi", DUZ)
        ekle("B15 manifestsiz makine: ayirt-edilemez kopya isaretlenir AMA yetim karari degismez "
             "('manifest yok' gerekcesi + dosya SILINMEZ)",
             rc == 0 and _man(ms).get(DUZ) == sha_v2 and not duz_uyari(om)
             and "feedback_eski-yetim.md" in om and "manifest yok (bu proje manifest" in om
             and (ms / "feedback_eski-yetim.md").exists(), f"rc={rc} out={om[-500:]!r}")
    finally:
        _sil(tmp)

    hata = 0
    for ad, ok, detay in SONUC:
        hata += 0 if ok else 1
        print(f"  [{'OK ' if ok else 'FAIL'}] {ad}" + (f"   -> {detay}" if not ok else ""))
    gecen = len(SONUC) - hata
    print(f"\n=== TOHUM GOVDE GUNCELLEMESI (S1) {'[' + kip + ']' if kip else '[taban]'} ===")
    print(f"{gecen}/{len(SONUC)} OK")
    if kip:
        dusen = {ad.split()[0] for ad, ok, _ in SONUC if not ok}
        beklenen = _BEKLENEN_DUSEN[kip]
        if dusen != beklenen:
            print(f"[SAPMA] {kip}: beklenen={sorted(beklenen)} dusen={sorted(dusen)} "
                  f"fazla={sorted(dusen - beklenen)} eksik={sorted(beklenen - dusen)} -> exit 2")
            return 2
        print(f"[BEKLENEN] {kip}: dusen kume = beklenen {sorted(beklenen)}")
        return 1
    return 1 if hata else 0


if __name__ == "__main__":
    kip = None
    kaynak_yolu = None
    argv = sys.argv[1:]
    for i, _a in enumerate(argv):
        if _a.startswith("--mutasyon"):
            if _a not in _GECERLI_KIP:
                print("[KULLANIM] bilinmeyen mutasyon kipi: %s · gecerli kipler: %s"
                      % (_a, ", ".join(sorted(_GECERLI_KIP))))
                sys.exit(3)
            kip = _a
        elif _a == "--seed-kaynak" and i + 1 < len(argv):
            kaynak_yolu = Path(argv[i + 1])
    sys.exit(main(kip, kaynak_yolu))
