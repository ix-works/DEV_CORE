#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TOHUM YAYILIM M4 korpusu (Q407 / Q408 K1-M4, 2026-11-12).

NEDEN BU KORPUS VAR
-------------------
Q407 tohumu tazeledi (yeni dersler + evrilmis derslerin geri akisi). "Tohumda duruyor" ile
"kurulu bir makineye ULASTI" ayni sey degildir (memory dersi: merge-safe dagitimda satir yalniz
ONARILAN dosyaya ulasir). Bu korpus GERCEK tohumla, GERCEK `seed_memory.py` ile sahte bir
"mevcut tuketici makine" kurar ve yeni tohumun oraya ne kadarinin ulastigini OLCER.

SAHNE (gercek eski durum — bos dizin DEGIL):
  1) Eski tohum = `git archive <TABAN_SHA> claude/memory-seed` (Q407 oncesi core main).
     Sandbox core'da eski tohumla `seed_memory` kosulur -> makine manifest'iyle kurulur.
  2) Kullanici dokunuslari: bir tohum dersi yerelde duzenlenir (ZLI) · bir konu hub'i yerelde
     duzenlenir (HUB_DUZ) · kullanici kendi dersini + MEMORY.md satirini ekler.
  3) Yeni tohum = calisma agacinin `claude/memory-seed` (satir sonu LF'ye normalize — indeksteki
     icerik) + iki SONDA satiri: biri yerelde DOKUNULMAMIS hub'a (HUB_TEMIZ), biri yerelde
     DUZENLENMIS hub'a (HUB_DUZ). `seed_memory` yeniden kosulur.

CIVILENEN SOZLESME
  M1  yerelde dokunulmamis + tohumda evrilmis dersler YENI govdeyi alir (B kumesi)
  M2  yerelde duzenlenmis ders EZILMEZ (a) ve uyarida ADIYLA gorunur (b)
  M3  yeni dersler (A+C) + yeni tarihli hub makineye eklenir ("Eklendi" tam sayi)
  M4  yeni dersler hedef MEMORY.md'den ERISILIR (tarihli hub satiri `_index_onar` ile eklendi;
      olcum gercek `check_memory_index._butunluk` ile)
  M5  kullanicinin kendi satiri/dersi korunur · M6 MEMORY.md 200 satir / 25.600 bayt icinde
  S1  dokunulmamis hub'a konan sonda satiri ULASIR (S1 govde guncellemesi, #318)
  S2  NEGATIF KONTROL: duzenlenmis hub'a konan sonda satiri ULASMAZ (hub ezilmez, uyarida adi
      var, sonda dersi diskte ama erisilemez) — bu yuzden yeni dersler mevcut hub'a DEGIL
      tarihli hub'a yazilir (2026-10-18 emsali).
  X   3. baglam: manifest'i OLMAYAN eski makine — evrilmis ders ezilmez ("ayirt edilemez"),
      yeni dersler yine eklenir ve erisilir.

KOSUM:  python tests/fixtures/tohum_yayilim_m4/run.py [--mutasyon-eski-tohum | --mutasyon-duzenleneni-ez]
  --mutasyon-eski-tohum      "duzeltme geri alinca KIRMIZI": yeni tohum yerine ESKI tohum uygulanir
  --mutasyon-duzenleneni-ez seed_memory'de duzenlenmis kontrolu kalkar (kullanici duzenlemesi ezilir)
Cikis (CORE-07): 0 taban yesil · 1 taban kirmizi YA DA kipte dusen kume == pinli kume ·
        2 SAPMA (dusen kume pinli kumeden farkli) · 3 DOGRULANAMADI (git tabani yok / capa != 1)

⚠ TABAN_SHA bir dal adi DEGIL, pinli commit'tir (merge sonrasi kaymaz). Sig klonda yoksa
DOGRULANAMADI (exit 3) — sessiz yesil degil.
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import os
import shutil
import stat
import subprocess
import sys
import tarfile
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
TABAN_SHA = "8565c9d"          # Q407 oncesi core main (tohum 299 feedback)

# Q407 PR-1'in ici (sahnenin olctugu somut dosyalar)
B_GUNCEL = [  # tohumda evrilen, hedefte dokunulmamis -> yeni govde gelmeli
    "feedback_agent-briefing-sendmessage-main.md",
    "feedback_ajan-bulgusu-dogru-mekanizmasi-yanlis.md",
    "feedback_arac-kod-fix-lider-isi.md",
    "feedback_bash-heredoc-kacis-ve-utf8-bozulmasi.md",
    "feedback_infra-turunda-yeni-acilan-maddeye-baslama-mevcutlari-bitir.md",
    "feedback_kararlari-once-topla-sonra-dispatch.md",
    "feedback_lider-ajan-paralel-yazim-cakismasi.md",
    "feedback_merge-safe-dagitimda-satir-yalniz-onarilan-dosyaya-ulasir.md",
]
ZLI = "feedback_zli-obje-text-tahmin-yasak.md"          # tohumda evrildi + hedefte DUZENLENDI
YENI_HUB = "_indeks-terfi-2026-11-12.md"
YENI_DERSLER = [
    "feedback_infra-brifinde-kardes-kipleri-kod-dondu-oncesi.md",
    "feedback_isaret-sozdizimi-onermeden-once-prior-art-ara.md",
    "feedback_python-ile-dosya-duzenlerken-bayt-kipi-kullan-eol-korunur.md",
    "feedback_seed-alanina-satir-ici-yorum-yazma.md",
    "feedback_deploy-ui-yarida-kesilince-bsp-yine-yaratilmis-olabilir.md",
    "feedback_fugr-include-push-fugr-i-yolu-tmg-olay.md",
    "feedback_is-parametresini-koda-gomme-onerme.md",
    "feedback_kapi-raporu-kaydi-verify-report-tuzaklari.md",
    "feedback_test-yazmadan-once-acik-onay.md",
    "feedback_exit-include-e-az-yorum.md",
    "feedback_kullaniciya-her-mesaj-turkce.md",
]
HUB_TEMIZ = "_indeks-ajan-takim.md"          # hedefte dokunulmaz
HUB_DUZ = "_indeks-karar-iletisim.md"        # hedefte kullanici duzenler
SONDA_TEMIZ = "feedback_m4-sonda-temiz-hub.md"
SONDA_DUZ = "feedback_m4-sonda-duzenli-hub.md"
KENDI = "feedback_m4-kullanicinin-kendi-dersi.md"
KENDI_SATIR = "- [Kullanicinin kendi dersi](feedback_m4-kullanicinin-kendi-dersi.md) — yerel not"

_MUT = {
    "--mutasyon-duzenleneni-ez": ("    if yerel_sha != eski_sha:\n", "    if False:\n"),
}
_GECERLI_KIP = {"--mutasyon-eski-tohum", "--mutasyon-duzenleneni-ez"}   # run_battery BEYAN katmani

# CORE-07: kip basina DUSMESI BEKLENEN vektor kumesi (esitlikle kiyaslanir)
_BEKLENEN_DUSEN: dict[str, set[str]] = {
    # yeni tohum yok: evrilmis govde gelmez, yeni ders/hub yok, sondalar yok, ZLI uyarisi yok
    # (tohum ilerlemedi -> duzenlenmis ders SESSIZ), duzenlenmis hub uyarisi yok; X2: manifest'siz
    # makinede dosya tohumla AYNI kalir -> 'ayırt edilemez' uyarisi da cikmaz (olculdu 2026-11-12)
    "--mutasyon-eski-tohum": {"M1", "M2b", "M3", "M4", "S1", "S2", "X1", "X2"},
    # duzenlenmis ders + duzenlenmis hub EZILIR, uyari cikmaz; sonda duzenlenmis hub'a da ulasir
    "--mutasyon-duzenleneni-ez": {"M2a", "M2b", "S2"},
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


def _lf(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n")


def _eski_tohum() -> dict[str, bytes] | None:
    r = subprocess.run(["git", "-C", str(REPO), "archive", "--format=tar", TABAN_SHA,
                        "claude/memory-seed"], capture_output=True, timeout=120)
    if r.returncode != 0:
        print(f"[DOGRULANAMADI] git archive {TABAN_SHA} basarisiz (sig klon?): "
              f"{r.stderr.decode('utf-8', 'replace')[:300]}")
        return None
    out: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as t:
        for m in t.getmembers():
            if m.isfile() and m.name.endswith(".md"):
                out[Path(m.name).name] = _lf(t.extractfile(m).read())  # type: ignore[union-attr]
    return out


def _yeni_tohum() -> dict[str, bytes]:
    return {p.name: _lf(p.read_bytes()) for p in (REPO / "claude" / "memory-seed").glob("*.md")}


def _sonda_ekle(tohum: dict[str, bytes]) -> None:
    """Iki mevcut hub'a sonda satiri + sonda dersleri (yalniz sandbox tohumunda)."""
    for hub, sonda in ((HUB_TEMIZ, SONDA_TEMIZ), (HUB_DUZ, SONDA_DUZ)):
        ad = sonda[:-3]
        tohum[hub] = tohum[hub].rstrip(b"\n") + f" · [[{ad}]]\n".encode("utf-8")
        tohum[sonda] = (f"---\nname: {ad}\ndescription: M4 sonda dersi\nmetadata:\n"
                        f"  type: feedback\n---\n\nsonda govdesi\n").encode("utf-8")


def _erisilemez(hedef: Path) -> set[str]:
    """Gercek C-MEM-01 `_butunluk` ile hedefte indeksten erisilemeyen dosya adlari."""
    spec = importlib.util.spec_from_file_location(
        "_cmi_m4", SCRIPTS / "validators" / "check_memory_index.py")
    mod = importlib.util.module_from_spec(spec)                      # type: ignore[arg-type]
    spec.loader.exec_module(mod)                                     # type: ignore[union-attr]
    hatalar: list[str] = []
    mod._butunluk(hedef, "m4", hatalar)
    out = set()
    for h in hatalar:
        if "indeksten erişilemez" in h:
            out.add(h.split("'")[1])
    return out


def main(kip: str | None) -> int:
    eski = _eski_tohum()
    if eski is None:
        return 3
    kaynak = (SCRIPTS / "seed_memory.py").read_text(encoding="utf-8")
    if kip in _MUT:
        e, y = _MUT[kip]
        n = kaynak.count(e)
        if n != 1:
            print(f"[DOGRULANAMADI] mutasyon capasi {n} kez eslesti (beklenen 1): {kip}")
            return 3
        kaynak = kaynak.replace(e, y, 1)
    yeni = dict(eski) if kip == "--mutasyon-eski-tohum" else _yeni_tohum()
    if kip != "--mutasyon-eski-tohum":
        _sonda_ekle(yeni)

    tmp = Path(tempfile.mkdtemp(prefix="tohum_m4_"))
    try:
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
        env["IX_GENERICIZE_BLOCKLIST"] = "SENTINEL" + "-M4"

        def tohum_yaz(d: dict[str, bytes]) -> None:
            for p in seed.glob("*.md"):
                p.unlink()
            for ad, b in d.items():
                (seed / ad).write_bytes(b)

        def kos(hedef: Path) -> tuple[int, str]:
            r = subprocess.run([sys.executable, str(betik), "--target", str(hedef)], env=env,
                               cwd=str(tmp), capture_output=True, timeout=300)
            return r.returncode, r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")

        def uyari(o: str) -> list[str]:
            # "elle birlestir" basligi altindaki "    · <ad>  (neden)" satirlari
            satirlar, icinde = [], False
            for s in o.split("\n"):
                if "elle birleştir" in s and not s.strip().startswith("·"):
                    icinde = True
                    continue
                if icinde and s.strip().startswith("·"):
                    satirlar.append(s.strip())
                elif icinde and s.strip() and not s.startswith(" "):
                    icinde = False
            return satirlar

        def makine(ad: str, manifest: bool = True) -> tuple[Path, int, str]:
            h = tmp / ad
            tohum_yaz(eski)
            rc0, o0 = kos(h)                                     # eski tohumla KURULUM
            (h / ZLI).write_bytes((h / ZLI).read_bytes() + b"\n- yerel ek: kullanici duzenlemesi\n")
            (h / HUB_DUZ).write_bytes((h / HUB_DUZ).read_bytes() + b"\n- yerel hub notu\n")
            (h / KENDI).write_bytes(b"---\nname: m4-kendi\ndescription: kullanicinin dersi\n"
                                    b"metadata:\n  type: feedback\n---\n\nyerel\n")
            (h / "MEMORY.md").write_bytes((h / "MEMORY.md").read_bytes().rstrip(b"\n")
                                          + b"\n" + KENDI_SATIR.encode("utf-8") + b"\n")
            if not manifest:
                (h / ".seed-manifest.json").unlink()
            return h, rc0, o0

        # ══ ANA KOL: manifest'li eski makine ═══════════════════════════════════════
        h, rc0, o0 = makine("ana")
        zli_once = (h / ZLI).read_bytes()
        hub_duz_once = (h / HUB_DUZ).read_bytes()
        kendi_once = (h / KENDI).read_bytes()
        erisilemez_once = _erisilemez(h)
        tohum_yaz(yeni)
        rc, out = kos(h)
        erisilemez = _erisilemez(h)
        uy = uyari(out)

        ekle("Z0 kurulum + guncelleme exit 0, Traceback yok",
             rc0 == 0 and rc == 0 and "Traceback" not in o0 + out, f"rc0={rc0} rc={rc} out={out[-300:]!r}")
        fark = [ad for ad in B_GUNCEL if (h / ad).read_bytes() != yeni.get(ad)]
        degisti = [ad for ad in B_GUNCEL if eski.get(ad) != yeni.get(ad)]
        ekle("M1 dokunulmamis evrilmis dersler (B) YENI govdeyi aldi",
             not fark and len(degisti) == len(B_GUNCEL),
             f"yeni-govdeye-esit-degil={fark} tohumda-degismeyen={sorted(set(B_GUNCEL) - set(degisti))}")
        ekle("M2a yerelde duzenlenmis ders EZILMEDI", (h / ZLI).read_bytes() == zli_once)
        ekle("M2b duzenlenmis ders uyarida ADIYLA ('elle birleştir')",
             any(ZLI in s for s in uy), f"uyari={uy[:6]}")
        yeni_adlar = sorted(set(yeni) - set(eski) - {"MEMORY.md"})
        eksik = [ad for ad in YENI_DERSLER + [YENI_HUB] if (h / ad).read_bytes() != yeni.get(ad)
                 ] if all((h / ad).is_file() for ad in YENI_DERSLER + [YENI_HUB]) else ["dosya-yok"]
        ekle("M3 yeni dersler + tarihli hub eklendi ('Eklendi' = tohumdaki yeni dosya sayisi)",
             not eksik and f"Eklendi : {len(yeni_adlar)}" in out,
             f"eksik={eksik} beklenen-eklendi={len(yeni_adlar)} "
             f"satir={[s for s in out.split(chr(10)) if 'Eklendi' in s]}")
        mem = (h / "MEMORY.md").read_bytes().decode("utf-8")
        ulasmayan = sorted(set(YENI_DERSLER) & erisilemez)
        ekle("M4 yeni dersler hedef MEMORY.md'den ERISILIR (tarihli hub satiri eklendi)",
             f"]({YENI_HUB})" in mem and not ulasmayan and YENI_HUB not in erisilemez,
             f"hub-satiri={f']({YENI_HUB})' in mem} ulasmayan={ulasmayan}")
        ekle("M5 kullanicinin kendi satiri + dersi KORUNDU, yeni erisilemezlik yok (sondalar haric)",
             KENDI_SATIR in mem and (h / KENDI).read_bytes() == kendi_once
             and not (erisilemez - erisilemez_once - {SONDA_DUZ}),
             f"yeni-erisilemez={sorted(erisilemez - erisilemez_once)}")
        mb = (h / "MEMORY.md").read_bytes()
        mb_satir = mb.count(b"\n")
        # C-MEM-01 tavani DISK baytidir; Windows checkout'u CRLF'dir -> en kotu durum CRLF esdegeri
        mb_crlf = len(_lf(mb)) + mb_satir
        ekle("M6 hedef MEMORY.md 200 satir / 25.600 bayt icinde (CRLF esdegeri)",
             mb_satir <= 200 and mb_crlf <= 25 * 1024, f"satir={mb_satir} bayt-crlf={mb_crlf}")
        hub_temiz = (h / HUB_TEMIZ).read_bytes().decode("utf-8")
        ekle("S1 dokunulmamis hub'a konan sonda satiri ULASTI + sonda dersi erisilir",
             f"[[{SONDA_TEMIZ[:-3]}]]" in hub_temiz and SONDA_TEMIZ not in erisilemez
             and (h / SONDA_TEMIZ).is_file(), f"erisilemez-mi={SONDA_TEMIZ in erisilemez}")
        ekle("S2 NEGATIF KONTROL: duzenlenmis hub'a konan sonda satiri ULASMADI "
             "(hub ezilmedi + uyarida adi + sonda dersi diskte ama erisilemez)",
             (h / HUB_DUZ).read_bytes() == hub_duz_once and any(HUB_DUZ in s for s in uy)
             and (h / SONDA_DUZ).is_file() and SONDA_DUZ in erisilemez,
             f"hub-ezildi={(h / HUB_DUZ).read_bytes() != hub_duz_once} uyari-hub={any(HUB_DUZ in s for s in uy)} "
             f"sonda-erisilemez={SONDA_DUZ in erisilemez}")

        # ══ X: 3. BAGLAM — manifest'siz eski makine ═══════════════════════════════
        x, _, _ = makine("x", manifest=False)
        ab_once = (x / B_GUNCEL[0]).read_bytes()
        tohum_yaz(yeni)
        rcx, outx = kos(x)
        erx = _erisilemez(x)
        ekle("X1 manifest'siz makine: yeni dersler eklendi + erisilir",
             rcx == 0 and all((x / ad).is_file() for ad in YENI_DERSLER)
             and not (set(YENI_DERSLER) & erx), f"rc={rcx} ulasmayan={sorted(set(YENI_DERSLER) & erx)}")
        ekle("X2 manifest'siz makine: evrilmis ders EZILMEDI + 'ayırt edilemez' uyarisi",
             (x / B_GUNCEL[0]).read_bytes() == ab_once
             and any(B_GUNCEL[0] in s and "ayırt edilemez" in s for s in uyari(outx)),
             f"uyari={[s for s in uyari(outx) if B_GUNCEL[0] in s]}")
    finally:
        _sil(tmp)

    hata = 0
    for ad, ok, detay in SONUC:
        hata += 0 if ok else 1
        print(f"  [{'OK ' if ok else 'FAIL'}] {ad}" + (f"   -> {detay}" if not ok else ""))
    print(f"\n=== TOHUM YAYILIM M4 (Q407) {'[' + kip + ']' if kip else '[taban]'} ===")
    print(f"{len(SONUC) - hata}/{len(SONUC)} OK")
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
    secili = None
    for _a in sys.argv[1:]:
        if _a.startswith("--mutasyon"):
            if _a not in _GECERLI_KIP:
                print("[KULLANIM] bilinmeyen kip: %s · gecerli: %s" % (_a, ", ".join(sorted(_GECERLI_KIP))))
                sys.exit(3)
            secili = _a
    sys.exit(main(secili))
