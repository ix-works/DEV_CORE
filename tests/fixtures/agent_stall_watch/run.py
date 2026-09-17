#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AGENT STALL WATCH (Q322) — alt-ajan takilma bekcisinin korpusu.

NEDEN BU KORPUS VAR
-------------------
`scripts/agent_stall_watch.py` bir GOZLEMCIDIR: hicbir seyi bloklamaz, cikis kodu
"hukum" tasimaz ⇒ kusurlari SESSIZDIR. Uc sessiz kusur sinifi mumkundur:
  · SAHTE-ASILI (FP)  : bitmis/genc/eski bir cagri "asili" diye bildirilir
                        -> uyari korlugu (kaldirilan SAP watchdog daemon'unun
                           kok kusuru; removed-controls satir 25)
  · SESSIZ KACIS (FN) : gercek takilma hic bildirilmez
  · SESSIZ TEMIZ      : kok yok / 0 transkript / okunamayan dosya halinde arac
                        susar ve okuyucu "temiz" saniyor (core §7 KAPSAM BEYANI)
Ucunun de capasi bu korpustadir; cikis kodu DEGIL **basilan OLAY SATIRI** olculur.

SENARYOLAR (S1-S16)
  S1  ⭐ TABAN: 20 dk yasinda eslesmemis tool_use -> ASILI? (ajan adi + arac + dk)
  S2  FP CAPASI: 3 dk yasinda eslesmemis tool_use -> SESSIZ (esik mesru cagriyi yakmaz)
  S3  FP CAPASI: sonucu GELMIS cagri (eski) -> SESSIZ  (= canlilik degil ILERLEME olculur)
  S4a ⭐ TABAN FILTRESI: 3 gun once dogmus kalinti -> SESSIZ (korpusta 19 tane var)
  S4b ⭐ AYNI DOSYA, taban geriye alinir -> ASILI?  (kural OLCULUR; susturma degil)
  S5  ⭐ COZULDU: dongu kipinde asili bildirilir, sonra tool_result eklenir -> COZULDU
  S6  ⭐ OLCULEMEDI kok-yok -> satir basilir VE exit 2 (sessiz temiz DEGIL)
  S7  ⭐ OLCULEMEDI kapsam-sifir (kok var, 0 transkript) -> satir + exit 2
  S8  ⭐ SATIR BOLME (gercek korpustan dogdu): payload'i \x0b \x1c   tasiyan
      GECERLI kayit -> "bozuk-satir" BASILMAZ ve takilma YINE yakalanir
  S9  TERS CAPA: gercekten bozuk ORTA satir -> OLCULEMEDI bozuk-satir BASILIR
      (S8'in cozumu "hic bakma" olmamali)
  S10 FP CAPASI: SON satir yarim (canli yazici flush ediyor) -> OLCULEMEDI BASILMAZ
  S11 ⭐ 3. BAGLAM (gorev-DISI sekil): 2 proje x 2 seans, PARALEL batch (5 tool_use /
      4 tool_result) -> yalniz bekleyen 1 cagri bildirilir + --proje filtresi otekini
      kapsam disi birakir
  S12 meta.json YOK -> ad dosya adina duser, YINE atesler (yokluk != hata)
  S13 kimliksiz tool_result -> OLCULEMEDI kimliksiz-tool_result (sahte-ASILI sessiz kalmaz)
  S14 kimliksiz tool_use    -> OLCULEMEDI kimliksiz-tool_use    (sessiz KACIS gorunur)
  S15 KAPSAM BEYANI bulgu YOKKEN de basilir (en kritik an sifir-bulgu anidir)
  S16 CANLI KORPUS SONDASI (ortam-bagimli, salt-okur): gercek transkript koku varsa
      arac ona karsi kosulur; taban ONCESI kalintilar bildirilmemeli. Kok yoksa
      satir "OLCULEMEDI" yazar ve **FAIL uretmez** (CI'da transkript yok — bilincli).

  S17 OZET satiri olay token'larini ("ASILI?" vb.) TEKRARLAMAZ — yoksa liderin
      `grep ASILI?` okumasi bulgu YOKKEN de satir dondurur (uyari korlugu). Bu
      vektor bir OLCUMDEN dogdu: korpusun ilk surumu tam bu yuzden 4 sahte sonuc
      uretti (2026-09-17).

KOSUM:
    python tests/fixtures/agent_stall_watch/run.py
    ... --mutasyon             (esik kontrolu sokulur          -> 26/27: S2)
    ... --mutasyon-eslestirme  (tool_result eslestirmesi no-op -> 24/27: S3/S5/S11)
    ... --mutasyon-taban       (taban filtresi sokulur         -> 26/27: S4a)
    ... --mutasyon-kapsam      (OLCULEMEDI susturulur -> 21/27: S6/S6b/S7/S9/S13/S14)
  (Sayilar OLCULDU, tahmin degil — `python tests/run_battery.py agent_stall_watch`.)
Cikis: 0 hepsi beklendigi gibi · 1 sapma · 2 DOGRULANAMADI (capa bayat / kontrol grubu bozuk)

⛔ MUTASYON GERCEK KAYNAGA YAZILMAZ: mutasyonlu kopya gecici bir agaca kurulur ve
   HER mutasyon kipinde ONCE ayni konumdaki MUTASYONSUZ ikiz kosulur; gercek dosyayla
   ayni cevabi vermezse sonuc "dustu" degil DOGRULANAMADI'dir (exit 2) — olculen sey
   mutasyon degil ORTAM olurdu.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ARAC = REPO / "scripts" / "agent_stall_watch.py"

GECERLI_KIP = {"--mutasyon", "--mutasyon-eslestirme", "--mutasyon-taban",
               "--mutasyon-kapsam"}

# Fix'in SOKUMU (mutasyon capalari): (kip) -> (eski metin, yeni metin)
CAPA = {
    "--mutasyon": (
        "            if dk < self.esik_dk:\n",
        "            if False:  # MUTASYON: esik kontrolu sokuldu\n"),
    "--mutasyon-eslestirme": (
        "                    sonuclar.add(sonuc_kimlik)\n",
        "                    pass  # MUTASYON: tool_result eslestirmesi no-op\n"),
    "--mutasyon-taban": (
        '            if self.taban is not None and b["ts"] < self.taban:\n',
        "            if False:  # MUTASYON: taban filtresi sokuldu\n"),
    "--mutasyon-kapsam": (
        '                olaylar.append(f"OLCULEMEDI {s}")\n',
        "                pass  # MUTASYON: kapsam beyani susturuldu\n"),
}
# OLCULDU (2026-09-17, tahmin DEGIL — `python tests/run_battery.py agent_stall_watch`):
# taban 27/27 · --mutasyon 26/27 · --mutasyon-eslestirme 24/27 ·
# --mutasyon-taban 26/27 · --mutasyon-kapsam 21/27
BEKLENEN_DUSUS = {
    "--mutasyon": ("S2",),
    "--mutasyon-eslestirme": ("S3", "S5", "S11"),
    "--mutasyon-taban": ("S4a",),
    "--mutasyon-kapsam": ("S6", "S6b", "S7", "S9", "S13", "S14"),
}

SONUC: list[tuple[str, bool, str]] = []
_GECICI: list[str] = []


def kayit(ad: str, ok: bool, not_: str = "") -> None:
    SONUC.append((ad, ok, not_))


def _tmp() -> Path:
    d = Path(tempfile.mkdtemp(prefix="stallwatch_"))
    _GECICI.append(str(d))
    return d


def temizle() -> None:
    for d in _GECICI:
        shutil.rmtree(d, ignore_errors=True)


def iso(dk_once: float, simdi: _dt.datetime) -> str:
    return (simdi - _dt.timedelta(minutes=dk_once)).isoformat().replace("+00:00", "Z")


def _kullanim(kimlik: str | None, arac: str, ts: str) -> str:
    blok: dict = {"type": "tool_use", "name": arac, "input": {}}
    if kimlik is not None:
        blok["id"] = kimlik
    return json.dumps({"type": "assistant", "timestamp": ts,
                       "message": {"role": "assistant", "content": [blok]}})


def _sonuc(kimlik: str | None, ts: str, govde: str = "ok") -> str:
    blok: dict = {"type": "tool_result", "content": govde}
    if kimlik is not None:
        blok["tool_use_id"] = kimlik
    return json.dumps({"type": "user", "timestamp": ts,
                       "message": {"role": "user", "content": [blok]}})


def _metin(ts: str, govde: str = "bitti") -> str:
    return json.dumps({"type": "assistant", "timestamp": ts,
                       "message": {"role": "assistant",
                                   "content": [{"type": "text", "text": govde}]}})


def transkript(kok: Path, proje: str, seans: str, ajan: str, satirlar: list[str],
               meta: dict | None = None) -> Path:
    d = kok / proje / seans / "subagents"
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"agent-{ajan}.jsonl"
    f.write_text("\n".join(satirlar) + "\n", encoding="utf-8", newline="\n")
    if meta is not None:
        (d / f"agent-{ajan}.meta.json").write_text(
            json.dumps(meta), encoding="utf-8", newline="\n")
    return f


def kos(arac: Path, ek: list[str], simdi: _dt.datetime | None = None,
        zaman_asimi: int = 90) -> tuple[int, str]:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    cmd = [sys.executable, str(arac), "--tek-atim"] + ek
    if simdi is not None:
        cmd += ["--simdi", simdi.isoformat()]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env, timeout=zaman_asimi)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def asili_satirlari(cikti: str) -> list[str]:
    """YALNIZ olay satirlari. `"] ASILI?"` capasi bilincli: ozet satiri olay
    token'ini TEKRARLAMAMALIDIR (S17) — ilk surumde tekrarliyordu ve bu extractor
    ozet satirini da sayip 4 sahte sonuc uretti."""
    return [s for s in cikti.splitlines() if "] ASILI?" in s]


def olculemedi_satirlari(cikti: str) -> list[str]:
    return [s for s in cikti.splitlines() if "] OLCULEMEDI" in s]


def cozuldu_satirlari(cikti: str) -> list[str]:
    return [s for s in cikti.splitlines() if "] COZULDU" in s]


# ─────────────────────────────────────────────────────────────────────────────
def senaryolar(arac: Path) -> None:
    simdi = _dt.datetime(2026, 9, 17, 12, 0, 0, tzinfo=_dt.timezone.utc)
    taban_uzak = (simdi - _dt.timedelta(days=30)).isoformat()

    # ── S1/S2/S3: tek kok, uc ajan ──────────────────────────────────────────
    kok = _tmp() / "projects"
    transkript(kok, "PROJE", "seans1", "asili01",
               [_kullanim("tu_1", "Bash", iso(20, simdi))],
               meta={"agentType": "backend-expert", "description": "uzun is"})
    transkript(kok, "PROJE", "seans1", "genc01",
               [_kullanim("tu_2", "Read", iso(3, simdi))],
               meta={"agentType": "bug-expert", "description": "genc cagri"})
    transkript(kok, "PROJE", "seans1", "bitmis01",
               [_kullanim("tu_3", "Bash", iso(40, simdi)),
                _sonuc("tu_3", iso(39, simdi)),
                _metin(iso(38, simdi))],
               meta={"agentType": "adt-gateway", "description": "bitmis"})
    rc, out = kos(arac, ["--kok", str(kok), "--baslangic", taban_uzak], simdi)
    asili = asili_satirlari(out)
    kayit("S1 asili cagri bildirilir (ad + arac + dk)",
          any("backend-expert" in s and "Bash" in s and " 20 dk" in s for s in asili),
          f"asili satirlari: {asili}")
    kayit("S1b olay satiri AKSIYONU tasir (SendMessage probe / TaskStop)",
          all("SendMessage probe" in s and "TaskStop" in s for s in asili) and bool(asili),
          f"asili satirlari: {asili}")
    kayit("S2 FP: 3 dk'lik genc cagri SESSIZ",
          not any("bug-expert" in s for s in asili), f"asili satirlari: {asili}")
    kayit("S3 FP: sonucu GELMIS cagri SESSIZ (canlilik degil ilerleme)",
          not any("adt-gateway" in s for s in asili), f"asili satirlari: {asili}")
    kayit("S15 KAPSAM BEYANI her kosumda basilir",
          "[bekci] KAPSAM" in out and "BAKMADIGI" in out, out[:200])
    kayit("S1c exit kodu hukum TASIMAZ (olcum yapildi -> 0)", rc == 0, f"rc={rc}")

    # ── S4a/S4b: taban filtresi (KURAL, blocklist degil) ────────────────────
    kok2 = _tmp() / "projects"
    transkript(kok2, "PROJE", "seans1", "kalinti01",
               [_kullanim("tu_k", "Bash", iso(3 * 24 * 60, simdi))],
               meta={"agentType": "infra-expert", "description": "3 gun onceki kalinti"})
    rc_a, out_a = kos(arac, ["--kok", str(kok2)], simdi)      # varsayilan taban
    rc_b, out_b = kos(arac, ["--kok", str(kok2), "--baslangic", taban_uzak], simdi)
    kayit("S4a kalinti (3 gun once dogmus) varsayilan tabanda SESSIZ",
          not asili_satirlari(out_a), f"satirlar: {asili_satirlari(out_a)}")
    kayit("S4b AYNI dosya, taban geriye alininca ASILI? (kural olculuyor)",
          bool(asili_satirlari(out_b)), f"satirlar: {asili_satirlari(out_b)}")

    # ── S5: COZULDU (GERCEK dongu kipi; --tek-atim DEGIL) ───────────────────
    kok3 = _tmp() / "projects"
    f5 = transkript(kok3, "PROJE", "seans1", "cozulen01",
                    [_kullanim("tu_c", "Bash", iso(20, simdi))],
                    meta={"agentType": "frontend-expert", "description": "cozulecek"})
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.Popen(
        [sys.executable, str(arac), "--kok", str(kok3), "--baslangic", taban_uzak,
         "--simdi", simdi.isoformat(), "--aralik-sn", "0.4", "--sure-dk", "0.08"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace", env=env)
    time.sleep(1.2)
    with f5.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(_sonuc("tu_c", iso(1, simdi)) + "\n")
    try:
        out5 = p.communicate(timeout=60)[0] or ""
    except subprocess.TimeoutExpired:
        p.kill()
        out5 = p.communicate()[0] or ""
    kayit("S5 asili bildirilir, sonuc gelince COZULDU basilir",
          bool(asili_satirlari(out5)) and bool(cozuldu_satirlari(out5)),
          f"cikti: {out5[-300:]}")
    kayit("S5b ASILI? ayni cagri icin TEKRARLANMAZ (uyari korlugu yok)",
          len(asili_satirlari(out5)) == 1, f"asili sayisi: {len(asili_satirlari(out5))}")

    # ── S6/S7: OLCULEMEDI — sessiz temiz YOK ───────────────────────────────
    yok = _tmp() / "hic-olmayan-kok"
    rc6, out6 = kos(arac, ["--kok", str(yok)], simdi)
    kayit("S6 kok yoksa OLCULEMEDI + exit 2",
          rc6 == 2 and any("kok-yok" in s for s in olculemedi_satirlari(out6)),
          f"rc={rc6} satirlar={olculemedi_satirlari(out6)}")
    kayit("S6b kok yokken 'temiz' izlenimi veren satir YOK",
          not asili_satirlari(out6) and bool(olculemedi_satirlari(out6)), out6[-200:])
    bos = _tmp() / "projects"
    bos.mkdir(parents=True, exist_ok=True)
    rc7, out7 = kos(arac, ["--kok", str(bos)], simdi)
    kayit("S7 kapsam-sifir -> OLCULEMEDI + exit 2",
          rc7 == 2 and any("kapsam-sifir" in s for s in olculemedi_satirlari(out7)),
          f"rc={rc7} satirlar={olculemedi_satirlari(out7)}")
    kayit("S17 OZET satiri olay token'larini TEKRARLAMAZ (grep uyari korlugu yok)",
          all(tok not in out7.split("BITTI", 1)[-1]
              for tok in ("ASILI?", "COZULDU", "OLCULEMEDI")),
          f"ozet: {out7.split('BITTI', 1)[-1][:120]}")

    # ── S8/S9/S10: satir bolme ve bozuk satir ──────────────────────────────
    kok4 = _tmp() / "projects"
    gurultu = "kontrol \x0b \x0c \x1c \x1d \x1e \x85     karakterleri"
    transkript(kok4, "PROJE", "seans1", "bolunen01",
               [_sonuc("tu_onceki", iso(60, simdi), govde=gurultu),
                _kullanim("tu_b", "Bash", iso(20, simdi))],
               meta={"agentType": "backend-expert", "description": "kontrol karakterli"})
    rc8, out8 = kos(arac, ["--kok", str(kok4), "--baslangic", taban_uzak], simdi)
    kayit("S8 Unicode satir-siniri tasiyan GECERLI kayit bozuk sayilmaz",
          not any("bozuk-satir" in s for s in olculemedi_satirlari(out8)),
          f"satirlar={olculemedi_satirlari(out8)}")
    kayit("S8b ayni dosyadaki takilma YINE yakalanir",
          bool(asili_satirlari(out8)), f"satirlar={asili_satirlari(out8)}")

    kok5 = _tmp() / "projects"
    d5 = kok5 / "PROJE" / "seans1" / "subagents"
    d5.mkdir(parents=True)
    (d5 / "agent-bozuk01.jsonl").write_text(
        _kullanim("tu_x", "Bash", iso(20, simdi)) + "\n"
        + "{bu gecerli json DEGIL\n"
        + _metin(iso(19, simdi)) + "\n", encoding="utf-8", newline="\n")
    rc9, out9 = kos(arac, ["--kok", str(kok5), "--baslangic", taban_uzak], simdi)
    kayit("S9 ORTADAKI bozuk satir OLCULEMEDI uretir",
          any("bozuk-satir" in s for s in olculemedi_satirlari(out9)),
          f"satirlar={olculemedi_satirlari(out9)}")

    kok6 = _tmp() / "projects"
    d6 = kok6 / "PROJE" / "seans1" / "subagents"
    d6.mkdir(parents=True)
    (d6 / "agent-yarim01.jsonl").write_text(
        _kullanim("tu_y", "Bash", iso(20, simdi)) + "\n"
        + '{"type":"assistant","timesta', encoding="utf-8", newline="\n")
    rc10, out10 = kos(arac, ["--kok", str(kok6), "--baslangic", taban_uzak], simdi)
    kayit("S10 FP: SON satir yarim (canli yazici) -> bozuk-satir BASILMAZ",
          not any("bozuk-satir" in s for s in olculemedi_satirlari(out10)),
          f"satirlar={olculemedi_satirlari(out10)}")
    kayit("S10b yarim son satira ragmen takilma yakalanir",
          bool(asili_satirlari(out10)), f"satirlar={asili_satirlari(out10)}")

    # ── S11: 3. BAGLAM — 2 proje x 2 seans + PARALEL batch ──────────────────
    kok7 = _tmp() / "projects"
    batch = [_kullanim(f"tu_p{i}", f"Arac{i}", iso(25 - i, simdi)) for i in range(5)]
    batch += [_sonuc(f"tu_p{i}", iso(10, simdi)) for i in range(1, 5)]  # 0 bekliyor
    transkript(kok7, "PROJE-A", "seansA", "paralel01", batch,
               meta={"agentType": "adt-gateway", "description": "paralel batch"})
    transkript(kok7, "PROJE-B", "seansB", "oteki01",
               [_kullanim("tu_z", "Bash", iso(30, simdi))],
               meta={"agentType": "sap-research", "description": "baska proje"})
    rc11, out11 = kos(arac, ["--kok", str(kok7), "--baslangic", taban_uzak], simdi)
    a11 = asili_satirlari(out11)
    kayit("S11 paralel batch: YALNIZ bekleyen cagri bildirilir (4 donen sessiz)",
          sum(1 for s in a11 if "adt-gateway" in s) == 1, f"satirlar={a11}")
    kayit("S11b bekleyen cagrinin ARACI dogru (Arac0, en eski bekleyen)",
          any("adt-gateway" in s and "Arac0" in s for s in a11), f"satirlar={a11}")
    rc11b, out11b = kos(arac, ["--kok", str(kok7), "--baslangic", taban_uzak,
                               "--proje", "PROJE-A"], simdi)
    kayit("S11c --proje filtresi oteki projeyi kapsam disi birakir",
          not any("sap-research" in s for s in asili_satirlari(out11b))
          and bool(asili_satirlari(out11b)),
          f"satirlar={asili_satirlari(out11b)}")

    # ── S12/S13/S14: ad cozumu + kimliksiz bloklar ─────────────────────────
    kok8 = _tmp() / "projects"
    transkript(kok8, "PROJE", "seans1", "metasiz01",
               [_kullanim("tu_m", "Bash", iso(20, simdi))], meta=None)
    rc12, out12 = kos(arac, ["--kok", str(kok8), "--baslangic", taban_uzak], simdi)
    kayit("S12 meta.json yoksa ad dosya adina duser, YINE atesler",
          any("agent-metasiz01" in s for s in asili_satirlari(out12)),
          f"satirlar={asili_satirlari(out12)}")

    kok9 = _tmp() / "projects"
    transkript(kok9, "PROJE", "seans1", "kimliksiz_sonuc01",
               [_kullanim("tu_s", "Bash", iso(20, simdi)),
                _sonuc(None, iso(19, simdi))],
               meta={"agentType": "backend-expert", "description": "kimliksiz sonuc"})
    rc13, out13 = kos(arac, ["--kok", str(kok9), "--baslangic", taban_uzak], simdi)
    kayit("S13 kimliksiz tool_result -> OLCULEMEDI (sahte-ASILI sessiz kalmaz)",
          any("kimliksiz-tool_result" in s for s in olculemedi_satirlari(out13)),
          f"satirlar={olculemedi_satirlari(out13)}")

    kok10 = _tmp() / "projects"
    transkript(kok10, "PROJE", "seans1", "kimliksiz_kullanim01",
               [_kullanim(None, "Bash", iso(20, simdi))],
               meta={"agentType": "backend-expert", "description": "kimliksiz cagri"})
    rc14, out14 = kos(arac, ["--kok", str(kok10), "--baslangic", taban_uzak], simdi)
    kayit("S14 kimliksiz tool_use -> OLCULEMEDI (sessiz KACIS gorunur olur)",
          any("kimliksiz-tool_use" in s for s in olculemedi_satirlari(out14)),
          f"satirlar={olculemedi_satirlari(out14)}")

    # ── S16: CANLI KORPUS SONDASI (ortam-bagimli, salt-okur) ───────────────
    ev = os.environ.get("CLAUDE_CONFIG_DIR")
    canli = (Path(ev) if ev else Path.home() / ".claude") / "projects"
    if not canli.exists() or not any(canli.glob("*/*/subagents/*.jsonl")):
        kayit("S16 canli korpus sondasi", True,
              "OLCULEMEDI: bu makinede alt-ajan transkripti yok (CI) — FAIL uretmez")
        print("  [NOT] S16 OLCULEMEDI: canli transkript koku yok/bos "
              f"({canli}) — ortam-bagimli vektor, FAIL uretmez", flush=True)
    else:
        rc16, out16 = kos(ARAC, [])   # GERCEK arac, varsayilan taban, salt-okur
        eski_kalinti = [s for s in asili_satirlari(out16)]
        kayit("S16 canli korpus: varsayilan tabanda eski kalintilar bildirilmez",
              rc16 == 0 and len(eski_kalinti) <= 2,
              f"rc={rc16} asili={eski_kalinti}")
        kayit("S16b canli korpusta KAPSAM BEYANI basilir",
              "[bekci] KAPSAM" in out16, out16[:160])


# ─────────────────────────────────────────────────────────────────────────────
def mutant_kur(kip: str) -> Path:
    eski, yeni = CAPA[kip]
    src = ARAC.read_text(encoding="utf-8")
    if src.count(eski) != 1:
        print(f"[DOGRULANAMADI] mutasyon capasi bayat ({kip}): "
              f"{src.count(eski)} eslesme (1 bekleniyordu)", flush=True)
        temizle()
        sys.exit(2)
    kok = _tmp()
    (kok / "scripts").mkdir(parents=True)
    hedef = kok / "scripts" / "agent_stall_watch.py"
    hedef.write_text(src.replace(eski, yeni), encoding="utf-8", newline="\n")
    ikiz = kok / "scripts" / "agent_stall_watch__taban.py"
    ikiz.write_text(src, encoding="utf-8", newline="\n")
    # KONTROL GRUBU: gecici konumdaki MUTASYONSUZ ikiz, gercek dosyayla AYNI
    # cevabi vermeli; vermezse olculen sey mutasyon degil ORTAMDIR.
    simdi = _dt.datetime(2026, 9, 17, 12, 0, 0, tzinfo=_dt.timezone.utc)
    kk = _tmp() / "projects"
    transkript(kk, "PROJE", "seans1", "kontrol01",
               [_kullanim("tu_kg", "Bash", iso(20, simdi))],
               meta={"agentType": "backend-expert", "description": "kontrol grubu"})
    ek = ["--kok", str(kk), "--baslangic",
          (simdi - _dt.timedelta(days=30)).isoformat()]
    _, a = kos(ARAC, ek, simdi)
    _, b = kos(ikiz, ek, simdi)
    # ⛔ Kiyas DUVAR SAATINDEN arindirilir: olay satiri `[HH:MM:SS] ` oneki tasir ve
    # iki kosum bir saniye sinirini strattlerse kiyas SAHTE-DOGRULANAMADI verir
    # (olculdu 2026-09-17: batarya kosumunda 1/4 kipte tam bu oldu, dogrudan
    # kosumda hic olmadi = klasik ortam-bagimli flaky).
    def _cip(satirlar: list[str]) -> list[str]:
        return [s.split("] ", 1)[-1] for s in satirlar]

    if _cip(asili_satirlari(a)) != _cip(asili_satirlari(b)):
        print("[DOGRULANAMADI] kontrol grubu bozuk: gecici agactaki MUTASYONSUZ kopya "
              "gercek dosyadan FARKLI davraniyor -> olculen sey ORTAM olurdu", flush=True)
        temizle()
        sys.exit(2)
    return hedef


def main() -> int:
    arg = [a for a in sys.argv[1:] if a not in ("-h", "--help")]
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print(__doc__)
        return 0
    kip = ""
    if arg:
        if arg[0] not in GECERLI_KIP:
            print(f"[KULLANIM] bilinmeyen kip: {arg[0]} (gecerli: {sorted(GECERLI_KIP)})",
                  flush=True)
            return 2
        kip = arg[0]

    arac = mutant_kur(kip) if kip else ARAC
    senaryolar(arac)

    print("=" * 78)
    print(f"AGENT STALL WATCH (Q322) — kip: {kip or 'taban'}")
    print("=" * 78)
    dusen = 0
    for ad, ok, not_ in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + (f"   -> {not_}" if not_ and not ok else ""))
        if not ok:
            dusen += 1
    if kip:
        print(f"  (beklenen dususler: {', '.join(BEKLENEN_DUSUS[kip])})")
    # `N/M OK` satiri: TAM suit ozeti bu bicimi ayristirir (run_fixture_tests
    # `^\s*\d+/\d+ OK`), yoksa tablo hucresi BOS kalir ve skor gorunmez.
    print(f"{len(SONUC) - dusen}/{len(SONUC)} OK  (P+N iceride)")
    print(f"TOPLAM: {len(SONUC) - dusen} PASS / {dusen} FAIL")
    temizle()
    return 1 if dusen else 0


if __name__ == "__main__":
    raise SystemExit(main())
