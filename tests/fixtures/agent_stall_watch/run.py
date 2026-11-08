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

  -- IKI TAKILMA IMZASI (2026-10-03) — bekleyen tool_use OLMAYAN takilmalar --
  S18 ⭐ DONGU: 2 ardisik max_tokens turu, arada tool_use yok -> DONGU? (#97647 bicimi;
      bu makinenin 881 alt-ajan transkriptinde ORNEK YOK -> bicim issue'dan alindi)
  S18b FP: TEK max_tokens turu PARCALI 2 kayit (ayni message.id) -> SESSIZ
  S18c imza ASILI? URETMEZ (iki kural ayri kanal)
  S19 FP: max_tokens, tool_use, max_tokens -> SESSIZ (ilerleme seriyi kirar)
  S20 ⭐ IPTAL: tool_result'tan 600,014 sn sonra "[Request interrupted by user for tool
      use]" -> IPTAL? (#84346 bicimi; bu korpusta pencereye dusen vaka 0)
  S21 FP: GERCEK KORPUS BICIMI — kesme tool_result'tan 0 sn / 43 sn sonra (lider
      TaskStop/ESC) -> SESSIZ
  S22 taban ONCESI imzalar varsayilan tabanda SESSIZ (kalinti kurali imzalara da uyar)
  S22b AYNI dosya, taban geriye alininca iki imza da basilir (susturma degil KURAL)
  S17b ozet + IMZALAR satiri "DONGU?"/"IPTAL?" token'larini TASIMAZ
  S23 ⭐ KARISIK DAMGA: ayni transkriptte Z'siz (tz'siz) + Z'li damgalar -> arac
      COKMEZ (taban kiyasi + imza araligi TypeError'i), BITTI basar, ASILI? + IPTAL? yine
      uretilir (bug-gate #313: tek transkript tum bekciyi olduruyordu)

  -- IZIN-BEKLIYOR / MUDAHALE-ZAMANI (2026-11-08) — on plan Bash/PowerShell --
  S24 ⭐ 4 dk'lik on plan Bash (limit 2 dk + 1) -> IZIN-BEKLIYOR (ad + dk + komut ozu)
  S24b 2 dk'lik on plan Bash -> SESSIZ (esigin altinda; komut hala kosuyor olabilir)
  S25 run_in_background=true 20 dk -> IZIN-BEKLIYOR YOK · S25b ayni cagri icin ASILI? VAR
  S26 timeout=600000 komut 4 dk'da -> SESSIZ (limit 10 + 1 dk) · S26b 12 dk'da -> VAR
  S27 ⭐ dongu kipinde (cok yoklama) IZIN-BEKLIYOR ve MUDAHALE-ZAMANI cagri basina BIR KEZ
  S28 13 dk -> MUDAHALE-ZAMANI (aksiyon TaskStop + SendMessage) · S28b 5 dk -> IZIN var,
      MUDAHALE yok · S28c ayni 13 dk'lik cagri icin ASILI? yine basilir (eski kanal degismez)
  S29a ask eslesmesi `rm -rf` · S29b bilesik komutun alt komutu `pkill` · S29c eslesme yok -> ask=yok
  S30 ayar dosyasi yok -> ask=OLCULEMEDI(dosya-yok ..) · S30b bozuk JSON -> ask=OLCULEMEDI(okunamadi ..)
  S31 Read araci 20 dk -> IZIN-BEKLIYOR YOK (yalniz Bash/PowerShell), ASILI? VAR
  S32 ⭐ GERCEK BICIM (lider kontrollu deneyi 2026-11-08, genericize): ek alanli assistant
      kaydi (wireToolInputs, requestId, ...) + once tamamlanmis cagri -> IZIN + ask=Bash(rm -r:*)
  S32b PowerShell + PowerShell(...) ask kurali
  S33 KAPSAM/IZIN SINYALI/BITTI satirlari IZIN-BEKLIYOR / MUDAHALE-ZAMANI token'ini TASIMAZ
  S34 varsayilan tabanda (5 dk) 3 gun onceki kalinti SESSIZ, 4 dk'lik cagri VAR (cift yon)

KOSUM:
    python tests/fixtures/agent_stall_watch/run.py
    ... --mutasyon             (esik kontrolu sokulur          -> 26/27: S2)
    ... --mutasyon-eslestirme  (tool_result eslestirmesi no-op -> 24/27: S3/S5/S11)
    ... --mutasyon-taban       (taban filtresi sokulur         -> 26/27: S4a)
    ... --mutasyon-kapsam      (OLCULEMEDI susturulur -> S6/S6b/S7/S9/S13/S14)
    ... --mutasyon-dongu       (DONGU esigi sokulur            -> S18)
    ... --mutasyon-dongu-seri  (tool_use seriyi KIRMAZ          -> S19)
    ... --mutasyon-dongu-parca (parcali kayit ayri tur sayilir  -> S18b)
    ... --mutasyon-iptal       (kesme kaydi hic algilanmaz      -> S20)
    ... --mutasyon-iptal-pencere (~600 sn penceresi kalkar     -> S21)
    ... --mutasyon-imza-taban  (imzalarin taban filtresi sokulur -> S22)
    ... --mutasyon-tz          (tz'siz damga UTC'ye cevrilmez    -> S23/S23b)
    ... --mutasyon-izin / -izin-limit / -izin-arkaplan / -izin-arac / -izin-tekil /
        -mudahale / -ask / -ask-olculemedi / -izin-taban   (kume: BEKLENEN_DUSUS)
⛔ CORE-07: mutasyon kipinde dusen vektor kumesi BEKLENEN_DUSUS ile ESITLIKLE kiyaslanir
   (eksik de fazla da sapma) -> sapma exit 2 (DOGRULANAMADI).
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
               "--mutasyon-kapsam", "--mutasyon-dongu", "--mutasyon-dongu-seri",
               "--mutasyon-dongu-parca", "--mutasyon-iptal", "--mutasyon-iptal-pencere",
               "--mutasyon-imza-taban", "--mutasyon-tz", "--mutasyon-izin",
               "--mutasyon-izin-limit", "--mutasyon-izin-arkaplan", "--mutasyon-izin-arac",
               "--mutasyon-izin-tekil", "--mutasyon-mudahale", "--mutasyon-ask",
               "--mutasyon-ask-olculemedi", "--mutasyon-izin-taban"}

# Fix'in SOKUMU (mutasyon capalari): (kip) -> (eski metin, yeni metin)
CAPA = {
    "--mutasyon": (
        "            if dk < self.esik_dk:\n",
        "            if False:  # MUTASYON: esik kontrolu sokuldu\n"),
    "--mutasyon-eslestirme": (
        "                    sonuclar.add(sonuc_kimlik)\n",
        "                    pass  # MUTASYON: tool_result eslestirmesi no-op\n"),
    # 2026-11-08: ayni taban satiri izin dongusunde de var (--mutasyon-izin-taban) ->
    # capa ASILI dongusunun onceki satiriyla tekillestirildi (ilk kosum: 2 eslesme, KURULAMADI).
    "--mutasyon-taban": (
        "            if anahtar in self.bildirilen:\n                continue\n"
        '            if self.taban is not None and b["ts"] < self.taban:\n',
        "            if anahtar in self.bildirilen:\n                continue\n"
        "            if False:  # MUTASYON: taban filtresi sokuldu\n"),
    "--mutasyon-kapsam": (
        '                olaylar.append(f"OLCULEMEDI {s}")\n',
        "                pass  # MUTASYON: kapsam beyani susturuldu\n"),
    "--mutasyon-dongu": (
        '            if len(imza["seri"]) >= DONGU_ESIK:\n',
        "            if False:  # MUTASYON: DONGU esigi sokuldu\n"),
    "--mutasyon-dongu-seri": (
        '            imza["seri"] = []                       # ilerleme var -> seri kirilir\n',
        "            pass  # MUTASYON: tool_use seriyi kirmiyor\n"),
    "--mutasyon-dongu-parca": (
        '            if kimlik not in [k for k, _ in imza["seri"]]:\n',
        "            if True:  # MUTASYON: parcali kayit ayri tur\n"),
    "--mutasyon-iptal": (
        "        if kesme and onceki is not None:\n",
        "        if False:  # MUTASYON: kesme algilanmiyor\n"),
    "--mutasyon-iptal-pencere": (
        "            if IPTAL_ARALIK_SN[0] <= aralik <= IPTAL_ARALIK_SN[1]:\n",
        "            if True:  # MUTASYON: pencere kalkti\n"),
    "--mutasyon-imza-taban": (
        '                    self.taban is not None and o["ts"] < self.taban):\n',
        "                    False):  # MUTASYON: imza taban filtresi sokuldu\n"),
    "--mutasyon-tz": (
        "    return z if z.tzinfo is not None else z.replace(tzinfo=_dt.timezone.utc)\n",
        "    return z  # MUTASYON: tz'siz damga oldugu gibi\n"),
    "--mutasyon-izin": (
        '                olaylar.append(f"IZIN-BEKLIYOR {ad} {dk:.0f} dk | {ozet} "\n'
        '                               f"-> kullaniciya bildir (operating-model §4D)")\n',
        "                pass  # MUTASYON: izin olayi basilmiyor\n"),
    "--mutasyon-izin-limit": (
        "        return float(t) / 60000.0\n",
        "        return VARSAYILAN_LIMIT_DK  # MUTASYON: input.timeout yok sayildi\n"),
    "--mutasyon-izin-arkaplan": (
        '    if isinstance(girdi, dict) and girdi.get("run_in_background"):\n        return None\n',
        "    if False:  # MUTASYON: arka plan ayrimi sokuldu\n        return None\n"),
    "--mutasyon-izin-arac": (
        "    if arac not in IZIN_ARACLARI:\n        return None\n",
        "    if False:  # MUTASYON: arac filtresi sokuldu\n        return None\n"),
    "--mutasyon-izin-tekil": (
        "                self.bildirilen_izin.add(anahtar)\n",
        "                pass  # MUTASYON: tekillik sokuldu\n"),
    "--mutasyon-mudahale": (
        "            if dk >= max(self.mudahale_dk, esik) and anahtar not in self.bildirilen_mudahale:\n",
        "            if anahtar not in self.bildirilen_mudahale:  # MUTASYON: esik sokuldu\n"),
    "--mutasyon-ask": (
        "    return uyan\n\n\ndef _imza_izle",
        "    return []  # MUTASYON: eslesme yok\n\n\ndef _imza_izle"),
    "--mutasyon-ask-olculemedi": (
        '            return f"OLCULEMEDI({self.ask_sebep})"\n',
        '            return "yok"  # MUTASYON: okunamayan ayar sessizce yok\n'),
    "--mutasyon-izin-taban": (
        '            if self.taban is not None and b["ts"] < self.taban:\n'
        "                continue\n            esik = izin_esigi_dk(",
        "            if False:  # MUTASYON: izin taban filtresi sokuldu\n"
        "                continue\n            esik = izin_esigi_dk("),
}
# OLCULDU (2026-09-17, tahmin DEGIL — `python tests/run_battery.py agent_stall_watch`):
# taban 27/27 · --mutasyon 26/27 · --mutasyon-eslestirme 24/27 ·
# --mutasyon-taban 26/27 · --mutasyon-kapsam 21/27
# 2026-10-03 (iki imza eklendi, ayni komut; dusen vektorler .tmp/battery/ ham ciktisindan):
# taban 37/37 · --mutasyon-eslestirme +S18c (eslestirme olunce DONGU dosyasindaki donmus
# Read cagrisi ASILI? olur) · --mutasyon-dongu S18+S22b · --mutasyon-iptal S20+S20b+S22b
# · --mutasyon-iptal-pencere S21+S20b (pencere disi kesmeler de sayilir -> iptal=3)
# · #313 duzeltme turu (S23/S23b + --mutasyon-tz, ESITLIK kiyasi): taban 39/39 ·
#   --mutasyon-dongu ve --mutasyon-iptal ayrica S23b (karisik damga vektoru de
#   DONGU?/IPTAL? bekler) — esitlik kiyasi bu fazlayi ilk kosumda yakaladi.
BEKLENEN_DUSUS = {
    "--mutasyon": ("S2",),
    "--mutasyon-eslestirme": ("S3", "S5", "S11", "S18c"),
    "--mutasyon-taban": ("S4a",),
    "--mutasyon-kapsam": ("S6", "S6b", "S7", "S9", "S13", "S14"),
    "--mutasyon-dongu": ("S18", "S22b", "S23b"),
    "--mutasyon-dongu-seri": ("S19",),
    "--mutasyon-dongu-parca": ("S18b",),
    "--mutasyon-iptal": ("S20", "S20b", "S22b", "S23b"),
    "--mutasyon-iptal-pencere": ("S21", "S20b"),
    "--mutasyon-imza-taban": ("S22",),
    "--mutasyon-tz": ("S23", "S23b"),
    # 2026-11-08 izin kanali — kume olcumden ONCE ilan edildi (gerekce: hangi vektor o
    # degismezi ayni kosumda okuyor).
    "--mutasyon-izin": ("S24", "S26b", "S27", "S28b", "S29a", "S29b", "S29c", "S30",
                        "S30b", "S32", "S32b", "S34"),
    "--mutasyon-izin-limit": ("S26",),
    "--mutasyon-izin-arkaplan": ("S25",),
    "--mutasyon-izin-arac": ("S31",),
    "--mutasyon-izin-tekil": ("S27",),
    "--mutasyon-mudahale": ("S28b",),
    "--mutasyon-ask": ("S29a", "S29b", "S32", "S32b"),
    "--mutasyon-ask-olculemedi": ("S30", "S30b"),
    "--mutasyon-izin-taban": ("S34",),
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


def _tur(ts: str, stop: str | None, msg_id: str, bloklar: list[dict]) -> str:
    """Assistant kaydi — stop_reason + message.id ile (DONGU imzasi)."""
    return json.dumps({"type": "assistant", "timestamp": ts, "uuid": "u-" + msg_id + ts,
                       "message": {"role": "assistant", "id": msg_id, "stop_reason": stop,
                                   "content": bloklar}})


def _kesme(ts: str, metin: str = "[Request interrupted by user for tool use]") -> str:
    """User-rolunde kesme kaydi (#84346 / gercek korpus bicimi)."""
    return json.dumps({"type": "user", "timestamp": ts, "uuid": "kesme-" + ts,
                       "message": {"role": "user",
                                   "content": [{"type": "text", "text": metin}]}})


def iso_sn(sn_once: float, simdi: _dt.datetime) -> str:
    return (simdi - _dt.timedelta(seconds=sn_once)).isoformat().replace("+00:00", "Z")


def dongu_satirlari(cikti: str) -> list[str]:
    return [s for s in cikti.splitlines() if "] DONGU?" in s]


def iptal_satirlari(cikti: str) -> list[str]:
    return [s for s in cikti.splitlines() if "] IPTAL?" in s]


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


def izin_satirlari(cikti: str) -> list[str]:
    return [s for s in cikti.splitlines() if "] IZIN-BEKLIYOR " in s]


def mudahale_satirlari(cikti: str) -> list[str]:
    return [s for s in cikti.splitlines() if "] MUDAHALE-ZAMANI " in s]


def _kullanim_g(kimlik: str, arac: str, girdi: dict, ts: str, ek: dict | None = None) -> str:
    """Girdili tool_use kaydi; `ek` gercek bicimdeki ust-duzey alanlari tasir."""
    o: dict = {"type": "assistant", "timestamp": ts,
               "message": {"role": "assistant",
                           "content": [{"type": "tool_use", "id": kimlik, "name": arac,
                                        "input": girdi}]}}
    if ek:
        o.update(ek)
    return json.dumps(o, ensure_ascii=False)


def izin_senaryolari(arac: Path, simdi: _dt.datetime, taban_uzak: str) -> None:
    kok = _tmp() / "projects"
    ayar = _tmp() / "settings.json"
    ayar.write_text(json.dumps({"permissions": {"ask": [
        "Bash(rm -rf:*)", "Bash(rm -r:*)", "Bash(pkill:*)", "PowerShell(Remove-Item:*)"]}}),
        encoding="utf-8", newline="\n")
    m = {"agentType": "backend-expert", "description": "izin rm"}
    transkript(kok, "PROJE", "s1", "i01", [_kullanim_g("u01", "Bash",
               {"command": "rm -rf /tmp/x/y", "description": "temizle"}, iso(4, simdi))], meta=m)
    transkript(kok, "PROJE", "s1", "i02", [_kullanim_g("u02", "Bash", {"command": "ls"},
               iso(2, simdi))], meta={"agentType": "bug-expert", "description": "genc"})
    transkript(kok, "PROJE", "s1", "i03", [_kullanim_g("u03", "Bash",
               {"command": "srv", "run_in_background": True}, iso(20, simdi))],
               meta={"agentType": "adt-gateway", "description": "arka plan"})
    transkript(kok, "PROJE", "s1", "i04", [_kullanim_g("u04", "Bash",
               {"command": "make", "timeout": 600000}, iso(4, simdi))],
               meta={"agentType": "frontend-expert", "description": "uzun limit"})
    transkript(kok, "PROJE", "s1", "i05", [_kullanim_g("u05", "Bash",
               {"command": "make all", "timeout": 600000}, iso(12, simdi))],
               meta={"agentType": "sap-research", "description": "uzun limit asildi"})
    transkript(kok, "PROJE", "s1", "i06", [_kullanim_g("u06", "Bash",
               {"command": "cd /tmp/x && pkill -f srv"}, iso(13, simdi))],
               meta={"agentType": "infra-expert", "description": "mudahale"})
    transkript(kok, "PROJE", "s1", "i07", [_kullanim_g("u07", "Bash", {"command": "ls /tmp/x"},
               iso(5, simdi))], meta={"agentType": "doc-expert", "description": "mudahale yok"})
    transkript(kok, "PROJE", "s1", "i08", [_kullanim_g("u08", "Read", {"file_path": "/tmp/x"},
               iso(20, simdi))], meta={"agentType": "sap-feature", "description": "read"})
    # S32: lider kontrollu deneyinin kayit BICIMI (2026-11-08) — yol/kimlik genericize.
    gercek_ek = {"isSidechain": True, "agentId": "a0000000000000000", "cwd": "/tmp/x",
                 "userType": "external", "version": "0.0.0", "toolInputStreamMs": 221,
                 "serverClassifierRequest": "00000000-0000-0000-0000-000000000000",
                 "apiBlockIndex": 1, "requestId": "req_0000",
                 "wireToolInputs": {"u09": {"command": "rm -r /tmp/x/alt",
                                            "description": "Remove test directory tree"}}}
    transkript(kok, "PROJE", "s1", "i09", [
        _kullanim_g("u09a", "Bash", {"command": "echo KELIME > /tmp/x/a.txt"}, iso(6, simdi),
                    gercek_ek),
        _sonuc("u09a", iso(5.9, simdi), "(Bash completed with no output)"),
        _kullanim_g("u09", "Bash", {"command": "rm -r /tmp/x/alt",
                                    "description": "Remove test directory tree"},
                    iso(4, simdi), gercek_ek)],
        meta={"agentType": "general-purpose", "description": "izin deneyi"})
    transkript(kok, "PROJE", "s1", "i10", [_kullanim_g("u10", "PowerShell",
               {"command": "Remove-Item -Recurse C:/tmp/x"}, iso(4, simdi))],
               meta={"agentType": "ps-expert", "description": "powershell"})
    transkript(kok, "PROJE", "s1", "i11", [_kullanim_g("u11", "Bash", {"command": "rm -rf /tmp/z"},
               iso(3 * 24 * 60, simdi))], meta={"agentType": "kalinti", "description": "eski"})

    rc, out = kos(arac, ["--kok", str(kok), "--baslangic", taban_uzak, "--ayar", str(ayar)], simdi)
    iz, mu, asl = izin_satirlari(out), mudahale_satirlari(out), asili_satirlari(out)

    def bir(lst: list[str], ad: str) -> list[str]:
        return [x for x in lst if f" {ad}/" in x]

    kayit("S24 4 dk'lik on plan Bash -> IZIN-BEKLIYOR (ad + dk + komut ozu)",
          any(" 4 dk | rm -rf /tmp/x/y |" in x for x in bir(iz, "backend-expert")), f"izin={iz}")
    kayit("S24b 2 dk'lik on plan Bash SESSIZ", not bir(iz, "bug-expert"), f"izin={iz}")
    kayit("S25 arka plan komutu IZIN-BEKLIYOR uretmez", not bir(iz, "adt-gateway"), f"izin={iz}")
    kayit("S25b ayni arka plan cagrisi icin ASILI? yine basilir", bool(bir(asl, "adt-gateway")),
          f"asili={asl}")
    kayit("S26 timeout=600000 komut 4 dk'da SESSIZ", not bir(iz, "frontend-expert"), f"izin={iz}")
    kayit("S26b timeout=600000 komut 12 dk'da IZIN-BEKLIYOR", bool(bir(iz, "sap-research")),
          f"izin={iz}")
    kayit("S28 13 dk -> MUDAHALE-ZAMANI + aksiyon",
          any("TaskStop + SendMessage" in x for x in bir(mu, "infra-expert")), f"mudahale={mu}")
    kayit("S28b 5 dk -> IZIN var, MUDAHALE yok",
          bool(bir(iz, "doc-expert")) and not bir(mu, "doc-expert"), f"izin={iz} mudahale={mu}")
    kayit("S28c ayni 13 dk'lik cagri icin ASILI? yine basilir", bool(bir(asl, "infra-expert")),
          f"asili={asl}")
    kayit("S29a ask eslesmesi rm -rf",
          any("ask=Bash(rm -rf:*)" in x for x in bir(iz, "backend-expert")), f"izin={iz}")
    kayit("S29b bilesik komutta alt komut pkill eslesir",
          any("ask=Bash(pkill:*)" in x for x in bir(iz, "infra-expert")), f"izin={iz}")
    kayit("S29c eslesme yok -> ask=yok", any("| ask=yok -> kullaniciya bildir" in x for x in bir(iz, "doc-expert")),
          f"izin={iz}")
    kayit("S31 Read 20 dk -> IZIN yok, ASILI var",
          not bir(iz, "sap-feature") and bool(bir(asl, "sap-feature")), f"izin={iz}")
    kayit("S32 gercek bicim: ek alanli kayit -> IZIN + ask=Bash(rm -r:*)",
          any("rm -r /tmp/x/alt" in x and "ask=Bash(rm -r:*)" in x
              for x in bir(iz, "general-purpose")), f"izin={iz}")
    kayit("S32b PowerShell + PowerShell(...) ask kurali",
          any("ask=PowerShell(Remove-Item:*)" in x for x in bir(iz, "ps-expert")), f"izin={iz}")
    ozet = [x for x in out.splitlines() if x.startswith("[bekci] ")]
    kayit("S33 kapsam/ozet satirlari olay token'ini tasimaz + sayac basilir",
          not any("IZIN-BEKLIYOR" in x or "MUDAHALE-ZAMANI" in x for x in ozet)
          and any("[bekci] IZIN SINYALI" in x for x in ozet)
          and any("izin=" in x and "mudahale=" in x for x in ozet if "BITTI" in x), str(ozet)[:300])
    rc34, out34 = kos(arac, ["--kok", str(kok), "--ayar", str(ayar)], simdi)   # varsayilan taban
    iz34 = izin_satirlari(out34)
    kayit("S34 varsayilan tabanda kalinti SESSIZ, 4 dk'lik cagri VAR",
          not bir(iz34, "kalinti") and bool(bir(iz34, "backend-expert")), f"izin={iz34}")
    _, out30 = kos(arac, ["--kok", str(kok), "--baslangic", taban_uzak,
                          "--ayar", str(_tmp() / "yok.json")], simdi)
    kayit("S30 ayar dosyasi yok -> ask=OLCULEMEDI(dosya-yok",
          any("ask=OLCULEMEDI(dosya-yok" in x for x in izin_satirlari(out30)),
          str(izin_satirlari(out30))[:200])
    bozuk = _tmp() / "bozuk.json"
    bozuk.write_text("{bozuk", encoding="utf-8")
    _, out30b = kos(arac, ["--kok", str(kok), "--baslangic", taban_uzak, "--ayar", str(bozuk)], simdi)
    kayit("S30b bozuk ayar -> ask=OLCULEMEDI(okunamadi",
          any("ask=OLCULEMEDI(okunamadi" in x for x in izin_satirlari(out30b)),
          str(izin_satirlari(out30b))[:200])

    # S27: dongu kipi — cok yoklamada olay cagri basina BIR KEZ.
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    pr = subprocess.Popen(
        [sys.executable, str(arac), "--kok", str(kok), "--baslangic", taban_uzak,
         "--simdi", simdi.isoformat(), "--aralik-sn", "0.3", "--sure-dk", "0.04",
         "--ayar", str(ayar)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace", env=env)
    try:
        out27 = pr.communicate(timeout=60)[0] or ""
    except subprocess.TimeoutExpired:
        pr.kill()
        out27 = pr.communicate()[0] or ""
    yoklama = out27.split("BITTI - ", 1)[-1].split(" yoklama", 1)[0].strip()
    kayit("S27 dongu kipinde IZIN ve MUDAHALE cagri basina BIR KEZ",
          yoklama.isdigit() and int(yoklama) >= 2
          and len(bir(izin_satirlari(out27), "backend-expert")) == 1
          and len(bir(mudahale_satirlari(out27), "infra-expert")) == 1,
          f"yoklama={yoklama} izin={bir(izin_satirlari(out27), 'backend-expert')} "
          f"mudahale={bir(mudahale_satirlari(out27), 'infra-expert')}")


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

    kayit("S17b ozet + IMZALAR satiri DONGU?/IPTAL? token'larini TASIMAZ",
          "DONGU?" not in out7 and "IPTAL?" not in out7 and "[bekci] IMZALAR" in out7,
          out7[-300:])

    # ── S18-S22: iki takilma imzasi (bekleyen tool_use YOK) ────────────────
    dusun = {"type": "thinking", "thinking": "..."}
    kok11 = _tmp() / "projects"
    transkript(kok11, "PROJE", "seans1", "dongu01",
               [_kullanim("tu_d0", "Read", iso(40, simdi)), _sonuc("tu_d0", iso(40, simdi)),
                _tur(iso(30, simdi), "max_tokens", "msg_d1", [dusun]),
                _tur(iso(20, simdi), "max_tokens", "msg_d2", [dusun])],
               meta={"agentType": "backend-expert", "description": "dusunme dongusu"})
    transkript(kok11, "PROJE", "seans1", "parca01",
               [_tur(iso(30, simdi), "max_tokens", "msg_p1", [dusun]),
                _tur(iso(30, simdi), "max_tokens", "msg_p1", [{"type": "text", "text": "x"}])],
               meta={"agentType": "bug-expert", "description": "parcali tek tur"})
    transkript(kok11, "PROJE", "seans1", "kirilan01",
               [_tur(iso(30, simdi), "max_tokens", "msg_k1", [dusun]),
                _tur(iso(25, simdi), None, "msg_k2",
                     [{"type": "tool_use", "id": "tu_k2", "name": "Bash", "input": {}}]),
                _sonuc("tu_k2", iso(24, simdi)),
                _tur(iso(20, simdi), "max_tokens", "msg_k3", [dusun])],
               meta={"agentType": "adt-gateway", "description": "arada ilerleme"})
    rc18, out18 = kos(arac, ["--kok", str(kok11), "--baslangic", taban_uzak], simdi)
    d18 = dongu_satirlari(out18)
    kayit("S18 2 ardisik max_tokens (arada tool_use yok) -> DONGU? (ad + sayi + aksiyon)",
          any("backend-expert" in s and " 2 ardisik" in s and "TaskStop" in s for s in d18),
          f"satirlar={d18}")
    kayit("S18b TEK tur parcali 2 kayit (ayni message.id) -> SESSIZ",
          not any("bug-expert" in s for s in d18), f"satirlar={d18}")
    kayit("S19 max_tokens / tool_use / max_tokens -> SESSIZ (ilerleme seriyi kirar)",
          not any("adt-gateway" in s for s in d18), f"satirlar={d18}")
    kayit("S18c imza ASILI? URETMEZ (iki kural ayri kanal)",
          not asili_satirlari(out18), f"asili={asili_satirlari(out18)}")

    kok12 = _tmp() / "projects"
    transkript(kok12, "PROJE", "seans1", "iptal01",
               [_kullanim("tu_i1", "Bash", iso_sn(700, simdi)),
                _sonuc("tu_i1", iso_sn(650.0, simdi)),
                _kesme(iso_sn(49.986, simdi))],            # +600,014 sn (#84346 vakasi)
               meta={"agentType": "frontend-expert", "description": "watchdog iptali"})
    transkript(kok12, "PROJE", "seans1", "taskstop01",
               [_kullanim("tu_i2", "Bash", iso_sn(300, simdi)),
                _sonuc("tu_i2", iso_sn(200.0, simdi)),
                _kesme(iso_sn(200.0, simdi))],             # +0 sn (gercek korpus bicimi)
               meta={"agentType": "sap-research", "description": "lider TaskStop"})
    transkript(kok12, "PROJE", "seans1", "esc01",
               [_metin(iso_sn(300, simdi)),
                _kesme(iso_sn(257.3, simdi), "[Request interrupted by user]")],   # +42,7 sn
               meta={"agentType": "doc-expert", "description": "kullanici ESC"})
    rc20, out20 = kos(arac, ["--kok", str(kok12), "--baslangic", taban_uzak], simdi)
    i20 = iptal_satirlari(out20)
    kayit("S20 tool_result'tan 600 sn sonra kesme -> IPTAL? (ad + sn + aksiyon)",
          any("frontend-expert" in s and " 600 sn" in s and "yeniden spawn" in s for s in i20),
          f"satirlar={i20}")
    kayit("S21 pencere DISI kesmeler (0 sn TaskStop / 43 sn ESC) -> SESSIZ",
          not any("sap-research" in s or "doc-expert" in s for s in i20), f"satirlar={i20}")
    kayit("S20b ozet satiri imza sayacini tasir (iptal=1)",
          "iptal=1" in out20.split("BITTI", 1)[-1], out20[-200:])

    # S22: AYNI iki imza 3 saat once -> varsayilan taban (simdi - 5 dk) oncesinde kalir.
    kok13 = _tmp() / "projects"
    transkript(kok13, "PROJE", "seans1", "eskiimza01",
               [_sonuc("tu_e0", iso_sn(3 * 3600 + 600.0, simdi)),
                _kesme(iso_sn(3 * 3600, simdi)),                       # +600 sn ama ESKI
                _tur(iso(170, simdi), "max_tokens", "msg_e1", [dusun]),
                _tur(iso(160, simdi), "max_tokens", "msg_e2", [dusun])],
               meta={"agentType": "infra-expert", "description": "eski imza kalintisi"})
    rc22, out22 = kos(arac, ["--kok", str(kok13)], simdi)     # varsayilan taban (5 dk)
    rc22b, out22b = kos(arac, ["--kok", str(kok13), "--baslangic", taban_uzak], simdi)
    kayit("S22 taban ONCESI imzalar varsayilan tabanda SESSIZ",
          not iptal_satirlari(out22) and not dongu_satirlari(out22),
          f"iptal={iptal_satirlari(out22)} dongu={dongu_satirlari(out22)}")
    kayit("S22b AYNI dosya, taban geriye alininca iki imza da basilir (kural olculuyor)",
          bool(iptal_satirlari(out22b)) and bool(dongu_satirlari(out22b)),
          f"iptal={iptal_satirlari(out22b)} dongu={dongu_satirlari(out22b)}")

    # ── S23: karisik damga (Z'siz + Z'li) — cokme yok ─────────────────────
    def _ciplak(ts: str) -> str:            # tz'siz bicim: "Z" atilir
        return ts[:-1] if ts.endswith("Z") else ts
    kok14 = _tmp() / "projects"
    transkript(kok14, "PROJE", "seans1", "karisik01",
               [_kullanim("tu_t1", "Bash", _ciplak(iso(20, simdi))),          # ASILI yolu
                _tur(_ciplak(iso(30, simdi)), "max_tokens", "msg_t1", [dusun]),  # DONGU yolu
                _tur(iso(25, simdi), "max_tokens", "msg_t2", [dusun])],
               meta={"agentType": "backend-expert", "description": "karisik damga"})
    transkript(kok14, "PROJE", "seans1", "karisik02",
               [_sonuc("tu_t9", _ciplak(iso_sn(650.0, simdi))),               # tz'siz
                _kesme(iso_sn(49.986, simdi))],                               # Z'li, +600 sn
               meta={"agentType": "frontend-expert", "description": "karisik iptal"})
    rc23, out23 = kos(arac, ["--kok", str(kok14), "--baslangic", taban_uzak], simdi)
    kayit("S23 karisik damga: arac COKMEZ, BITTI basar, exit 0",
          rc23 == 0 and "[bekci] BITTI" in out23 and "Traceback" not in out23,
          f"rc={rc23} cikti={out23[-300:]}")
    kayit("S23b karisik damgada ASILI? + DONGU? + IPTAL? yine uretilir",
          bool(asili_satirlari(out23)) and bool(dongu_satirlari(out23))
          and bool(iptal_satirlari(out23)),
          f"asili={asili_satirlari(out23)} dongu={dongu_satirlari(out23)} "
          f"iptal={iptal_satirlari(out23)}")

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

    izin_senaryolari(arac, simdi, taban_uzak)

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
    # `N/M OK` satiri: TAM suit ozeti bu bicimi ayristirir (run_fixture_tests
    # `^\s*\d+/\d+ OK`), yoksa tablo hucresi BOS kalir ve skor gorunmez.
    print(f"{len(SONUC) - dusen}/{len(SONUC)} OK  (P+N iceride)")
    print(f"TOPLAM: {len(SONUC) - dusen} PASS / {dusen} FAIL")
    temizle()
    if not kip:
        return 1 if dusen else 0
    # CORE-07: dusen kume BEKLENEN ile ESIT olmali (eksik de fazla da sapma).
    dusen_kume = {ad.split(" ", 1)[0] for ad, ok, _ in SONUC if not ok}
    beklenen = set(BEKLENEN_DUSUS[kip])
    if dusen_kume != beklenen:
        print(f"[DOGRULANAMADI] MUTASYON {kip}: dusen kume BEKLENENDEN FARKLI -> "
              f"eksik={sorted(beklenen - dusen_kume)} fazla={sorted(dusen_kume - beklenen)}")
        return 2
    print(f"  (MUTASYON {kip}: beklenen kume {sorted(beklenen)} AYNEN dustu)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
