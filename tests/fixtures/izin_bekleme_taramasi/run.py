#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IZIN BEKLEME TARAMASI — `scripts/izin_bekleme_taramasi.py` korpusu (sentetik oturum kayitlari).

NEDEN BU KORPUS VAR
-------------------
Arac bir GOZLEMCIDIR: hicbir seyi bloklamaz, cikis kodu hukum tasimaz ⇒ kusurlari SESSIZDIR.
Uc sessiz kusur sinifi civilenir:
  · SAHTE OLAY      : aracin kendi ciktisindaki imza metni (dosya okuyan grep), isletim sistemi
                      "Permission denied", komut zaman asimi, api-request-blob kopyasi olay sanilir
  · SESSIZ KACIS    : imza ya da alan bicimi degisince olay dusurulur (SINIFLANMADI'ya bile
                      dusmeden kaybolur)
  · SESSIZ TEMIZ    : kok yok / pencerede dosya yok → arac susar, okuyucu "temiz" sanir
Olculen sey cikis kodu degil, `--json` olay listesi ve `[izin] ` satirlaridir.

VEKTORLER (kok A = ana senaryo, kok B = UCUNCU BAGLAM: baska sekil)
  V01 ZAMAN-ASIMI metin+alan (safetyCheck + circuitBreaker), alt ajan adi meta'dan, bekleme 0,3 sn
  V02 ZAMAN-ASIMI yalniz METIN (alan yok — eski bicim); uzun komut 120 kr'de kesilir (…)
  V03 ZAMAN-ASIMI yalniz ALAN (metin bilinmeyen ifade — bicim kaymasi)
  V04 KULLANICI-REDDI metin + "the user said:" notu → detay notu tasir
  V05 KULLANICI-REDDI yalniz alan (toolDenialKind=user-rejected) → detay "TaskStop olabilir"
  V06 SINIFLANDIRICI-REDDI metin+alan, detay = "Reason: [<Kategori>]"
  V06b SINIFLANDIRICI-REDDI yalniz alan, detay = classifierCategory
  V07 GECICI yalniz metin · V07b GECICI yalniz alan (automode-unavailable)
  V08 KURAL-REDDI yalniz metin · V08b KURAL-REDDI yalniz alan (subcommandResults)
  V09 HOOK-BLOKU yalniz metin · V09b HOOK-BLOKU yalniz alan (source=hook)
  V10 ONAYLANDI (accept + user_temporary, is_error YOK), detay kapsam=once
  V11 SINIFLANMADI: taninmayan toolDenialKind — SESSIZCE DUSURULMEZ
  V11b SINIFLANMADI: alan yok, metin izin-benzeri ama hicbir imzaya uymuyor
  V12 FP: is_error=false sonuc imza metni tasiyor (ajan dosya okumus) → olay YOK
  V13 FP: accept+config (arac KOSTU) hata ciktisinda red metni → olay YOK
  V14 FP: api-request-blob kopyasi → V01 TEK kez, kopya sayaci 1, damgasiz 0
  V15 FP: isletim sistemi "Permission denied" → olay YOK (SINIFLANMADI da degil)
  V16 FP: "Command timed out after 2m" (komutun kendi zaman asimi) → olay YOK
  V17 GEC-ONAY: on plan Bash, limit yok (2 dk), bosluk 400 sn, sonunda KOSTU
  V17b timeout=600000 komut 400 sn'de GEC-ONAY DEGIL (limit + 1 dk = 11 dk)
  V17c run_in_background komut 400 sn'de GEC-ONAY DEGIL
  V17d Read araci 400 sn'de GEC-ONAY DEGIL (yalniz Bash/PowerShell)
  V17e 400 sn sonra KULLANICI reddi → KULLANICI-REDDI kalir (GEC-ONAY ret kategorisini EZMEZ)
  V17f bosluk 179 sn (< 180) → GEC-ONAY DEGIL (esik)
  V19 metin/alan CELISKISI: metin kullanici reddi, alan siniflandirici → kategori metinden, celiski sayilir
  V20 eslesmeyen tool_use_id → arac "?", bekleme None, COKMEZ
  V21 ana oturum dosyasinda olay → ajan_turu "ana"
  V22 (kok B) PowerShell + icerik BLOK LISTESI + CRLF satir sonu + meta.json YOK (ad = dosya adi)
  V23 (kok B) U+2028 tasiyan GECERLI kayit bozuk satir sayilmaz; kasitli bozuk orta satir 1 sayilir
  V24 (kok B) tz'siz damga → COKMEZ, olay pencerede bulunur
  V25 (kok B) son satir yarim → bozuk SAYILMAZ (canli yazici)
  V26a 3 gun once dogmus olay --gun 1'de YOK (pencere_disi_olay) · V26b --gun 5'te VAR (cift yon)
  V27a (kok C) mtime'i eski dosya atlanir → kapsam-sifir OLCULEMEDI + exit 2 · V27b --gun 60'ta taranir
  V28 kok yok → OLCULEMEDI kok-yok + exit 2 + KAPSAM satiri YINE basilir
  V29 (kok D) olay yokken de KAPSAM + BAKILMAYANLAR basilir, exit 0
  V30 ozet/ajan/kapsam satirlari kategori adini BUYUK HARFLE tekrarlamaz (grep korlugu)
  V31 --json ozet sayilari olay listesiyle ve metin OZET satiriyla ayni
  V32 --proje / --seans filtreleri
  V33 kullanim hatasi (--gun 0) → exit 1
  V34 metin OLAY satiri ajan + arac + bekleme_sn + katman tasir
  -- KUYRUK + KARAR KAYNAGI (bug-gate PR #403 F1, 2026-11-08; kok E) --
  V35 ⭐ GERCEK VAKA BICIMI: ayni message.id'de 1. Bash (timeout=600000) 214 sn kostu, 2. Bash
      (grep) 218 sn sonra sonuc aldi, karar config/classifier -> GEC olayi YOK (sira beklemesi)
  V35b ayni mesajda kardes 30 sn kostu, 2. cagri ondan 300 sn sonra sonuc aldi (user_temporary)
      -> GEC-ONAY, bekleme_sn=300 (kardesin sonucundan), kuyruk_sn=30
  V35c FARKLI message.id: ayni zamanlama sira SAYILMAZ -> GEC-ONAY bekleme_sn=218, kuyruk_sn=0
  V36 tek cagri 400 sn, karar accept/config/classifier -> GEC-OTOKABUL (GEC-ONAY DEGIL)
  V36b tek cagri 400 sn, permissionDecision YOK -> GEC-ONAY kalir (alansiz vaka ayirt edilemez)
  V37 ⭐ KORUMA YONU (bug-gate-2 #403 F1b): tek cagri 400 sn, karar accept/user_permanent -> GEC-ONAY
      (kalici kullanici onayi da kullanici kararidir; GEC-OTOKABUL'a kaymaz)

KOSUM:
    python tests/fixtures/izin_bekleme_taramasi/run.py
    ... --mutasyon-<kip>   (kipler + dusmesi ILAN edilen kume: BEKLENEN_DUSUS)
⛔ Mutasyonda dusen kume BEKLENEN_DUSUS ile ESITLIKLE kiyaslanir (eksik de fazla da sapma).
⛔ Mutasyon GERCEK kaynaga yazilmaz: gecici agaca kurulur; once ayni konumdaki MUTASYONSUZ ikiz
   kosulur ve gercek dosyayla ayni olay listesini vermezse sonuc DOGRULANAMADI'dir.
Cikis: 0 taban hepsi PASS · 1 taban FAIL ya da mutasyon kumesi AYNEN dustu · 2 mutasyon SAPMASI ·
       3 capa bayat / kontrol grubu bozuk (KURULAMADI)
"""
from __future__ import annotations

import datetime as _dt
import json
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

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ARAC = REPO / "scripts" / "izin_bekleme_taramasi.py"
SIMDI = _dt.datetime(2026, 11, 8, 12, 0, 0, tzinfo=_dt.timezone.utc)
KATEGORILER = ("ZAMAN-ASIMI", "GEC-ONAY", "GEC-OTOKABUL", "KULLANICI-REDDI",
               "SINIFLANDIRICI-REDDI", "GECICI", "KURAL-REDDI", "HOOK-BLOKU", "ONAYLANDI",
               "SINIFLANMADI")

GECERLI_KIP = {"--mutasyon-zaman-imza", "--mutasyon-zaman-alan", "--mutasyon-kullanici-imza",
               "--mutasyon-siniflandirici-imza", "--mutasyon-gecici-imza",
               "--mutasyon-kural-imza", "--mutasyon-hook-imza", "--mutasyon-is-error",
               "--mutasyon-kabul", "--mutasyon-blob", "--mutasyon-siniflanmadi",
               "--mutasyon-pencere", "--mutasyon-mtime", "--mutasyon-kapsam",
               "--mutasyon-satir", "--mutasyon-tz", "--mutasyon-gec-onay",
               "--mutasyon-gec-limit", "--mutasyon-gec-arkaplan", "--mutasyon-gec-ret",
               "--mutasyon-kuyruk", "--mutasyon-kuyruk-mesaj", "--mutasyon-otokabul",
               "--mutasyon-kullanici-kaynak"}

ASLA = 're.compile(r"(?!x)x")'
CAPA = {
    "--mutasyon-zaman-imza": (
        'IMZA_ZAMAN = re.compile(r"permission prompt timed out|built-in claude code safety check")',
        f"IMZA_ZAMAN = {ASLA}"),
    "--mutasyon-zaman-alan": (
        '        if sebep == "safetyCheck" or pd.get("circuitBreaker"):\n',
        "        if False:  # MUTASYON\n"),
    "--mutasyon-kullanici-imza": (
        'IMZA_KULLANICI = re.compile(r"doesn\'t want to proceed with this tool use"\n'
        '                            r"|the tool use was rejected")',
        f"IMZA_KULLANICI = {ASLA}"),
    "--mutasyon-siniflandirici-imza": (
        'IMZA_SINIFLANDIRICI = re.compile(r"denied by the (?:claude code )?auto mode classifier")',
        f"IMZA_SINIFLANDIRICI = {ASLA}"),
    "--mutasyon-gecici-imza": (
        'IMZA_GECICI = re.compile(r"auto mode cannot determine the safety|classifier gave no verdict")',
        f"IMZA_GECICI = {ASLA}"),
    "--mutasyon-kural-imza": (
        'IMZA_KURAL = re.compile(r"^permission to use \\S+ .*has been denied")',
        f"IMZA_KURAL = {ASLA}"),
    "--mutasyon-hook-imza": (
        'IMZA_HOOK = re.compile(r"^pretooluse:\\S* hook error")',
        f"IMZA_HOOK = {ASLA}"),
    "--mutasyon-is-error": (
        '    if blok.get("is_error") is not True:\n        return None\n',
        "    if False:  # MUTASYON\n        return None\n"),
    "--mutasyon-kabul": (
        "    if kabul:\n",
        "    if False:  # MUTASYON\n"),
    "--mutasyon-blob": (
        '            if kayit.get("type") == "api-request-blob":\n',
        "            if False:  # MUTASYON\n"),
    "--mutasyon-siniflanmadi": (
        '    if alan == "?" or IZIN_BENZERI.search(norm[:IZIN_BENZERI_ON_EK]):\n',
        "    if False:  # MUTASYON\n"),
    "--mutasyon-pencere": (
        "                if not (self.bas <= ts <= self.simdi):\n",
        "                if False:  # MUTASYON\n"),
    "--mutasyon-mtime": (
        "            if _dt.datetime.fromtimestamp(dosya.stat().st_mtime, _dt.timezone.utc) < self.bas:\n",
        "            if False:  # MUTASYON\n"),
    "--mutasyon-kapsam": (
        "    return 2 if olculemedi else 0\n",
        "    return 0  # MUTASYON\n"),
    "--mutasyon-satir": (
        '        satirlar = ham.split("\\n")\n',
        "        satirlar = ham.splitlines()  # MUTASYON\n"),
    "--mutasyon-tz": (
        "    return z if z.tzinfo is not None else z.replace(tzinfo=_dt.timezone.utc)\n",
        "    return z  # MUTASYON\n"),
    "--mutasyon-gec-onay": (
        "    return bekleme > komut_limiti_sn(girdi) + GEC_ONAY_PAY_SN\n",
        "    return False  # MUTASYON\n"),
    "--mutasyon-gec-limit": (
        "        return float(t) / 1000.0\n",
        "        return VARSAYILAN_LIMIT_MS / 1000.0  # MUTASYON\n"),
    "--mutasyon-gec-arkaplan": (
        "        return False          # arka plan komutu: sonuc kaydi baslatma aninda yazilir\n",
        "        pass  # MUTASYON\n"),
    "--mutasyon-gec-ret": (
        '                ezilebilir = sonuc is None or sonuc[0] in ("ONAYLANDI", "SINIFLANMADI")\n',
        "                ezilebilir = True  # MUTASYON\n"),
    "--mutasyon-kuyruk": (
        "                bas_kul = max(ts_kul, kuyruk) if (ts_kul and kuyruk) else ts_kul\n",
        "                bas_kul = ts_kul  # MUTASYON\n"),
    "--mutasyon-kuyruk-mesaj": (
        '                        mid = mesaj.get("id") if isinstance(mesaj.get("id"), str) else None\n',
        '                        mid = "TEK" if mesaj.get("id") else None  # MUTASYON\n'),
    "--mutasyon-otokabul": (
        "            and pd.get(\"source\") not in KULLANICI_KAYNAKLARI:\n",
        "            and False:  # MUTASYON\n"),
    # bug-gate-2 #403 F1b: kalici kullanici onayi kullanici kaynagi sayilmaz (bug-gate mutantinin birebiri).
    "--mutasyon-kullanici-kaynak": (
        'KULLANICI_KAYNAKLARI = ("user_temporary", "user_permanent")\n',
        'KULLANICI_KAYNAKLARI = ("user_temporary",)  # MUTASYON\n'),
}
# Dusmesi ILAN edilen kume (olcumden ONCE gerekceyle yazildi; gerekce satir sonunda).
# ILK KOSUM (2026-11-08) ilan edilenden FAZLA dusurdu ve fazlalarin hepsi ayni mekanizmanin
# ikinci olcumudur, kaza degil: V34 (metin satirinda V01'in katman=metin+alan'i) · V23/V32a
# (kok B ve --seans kosumundaki yalniz-metin kullanici reddi) · V24 (kok B yalniz-metin kural
# reddi) · V25 (bozuk satir sayaci V23 ile ortak). Kume bu gerekceyle genisletildi.
BEKLENEN_DUSUS = {
    "--mutasyon-zaman-imza": ("V01", "V02", "V22", "V34"),      # V01 katman metin+alan -> alan; V02/V22 yalniz metin
    "--mutasyon-zaman-alan": ("V01", "V03", "V34"),             # V01 katman -> metin; V03 yalniz alan
    "--mutasyon-kullanici-imza": ("V04", "V19", "V21", "V23", "V32a"),  # yalniz-metin vakalar + celiski metinden kalkar
    "--mutasyon-siniflandirici-imza": ("V06",),          # alan tutar, katman metin+alan -> alan
    "--mutasyon-gecici-imza": ("V07",),
    "--mutasyon-kural-imza": ("V08", "V24"),
    "--mutasyon-hook-imza": ("V09",),
    "--mutasyon-is-error": ("V12",),
    "--mutasyon-kabul": ("V10", "V13"),
    "--mutasyon-blob": ("V14",),
    "--mutasyon-siniflanmadi": ("V11", "V11b"),
    "--mutasyon-pencere": ("V26a",),
    "--mutasyon-mtime": ("V27a",),
    "--mutasyon-kapsam": ("V27a", "V28"),
    "--mutasyon-satir": ("V23", "V25"),
    "--mutasyon-tz": ("V22", "V23", "V24", "V25", "V32b"),  # kok B kosumu coker
    # V35b/V35c/V36/V36b: kok E'nin GEC olaylari ayni gec_onay_mi esigini okur (ayni mekanizma).
    "--mutasyon-gec-onay": ("V17", "V35b", "V35c", "V36", "V36b", "V37"),
    "--mutasyon-gec-limit": ("V17b",),
    "--mutasyon-gec-arkaplan": ("V17c",),
    "--mutasyon-gec-ret": ("V17e",),
    # 2026-11-08 kuyruk + karar kaynagi (bug-gate #403 F1) — kume olcumden ONCE ilan edildi.
    "--mutasyon-kuyruk": ("V35", "V35b"),       # sira beklemesi cagriya yazilir
    "--mutasyon-kuyruk-mesaj": ("V35c",),       # farkli mesajlar tek sira sayilir
    "--mutasyon-otokabul": ("V36",),            # config kabulu GEC-ONAY'a duser
    # bug-gate-2 #403 F1b (koruma yonu) — kume olcumden ONCE ilan edildi.
    "--mutasyon-kullanici-kaynak": ("V37",),   # user_permanent GEC-OTOKABUL'a kayar
}

SONUC: list[tuple[str, bool, str]] = []
_GECICI: list[str] = []


def kayit(ad: str, ok: bool, not_: str = "") -> None:
    SONUC.append((ad, bool(ok), not_))


def _tmp() -> Path:
    d = Path(tempfile.mkdtemp(prefix="izinbekleme_"))
    _GECICI.append(str(d))
    return d


def temizle() -> None:
    for d in _GECICI:
        shutil.rmtree(d, ignore_errors=True)


def iso(sn_once: float, z: bool = True) -> str:
    t = SIMDI - _dt.timedelta(seconds=sn_once)
    if z:
        return t.isoformat().replace("+00:00", "Z")
    return t.replace(tzinfo=None).isoformat()


def kul(kimlik: str, arac: str, girdi: dict, ts: str) -> dict:
    return {"type": "assistant", "timestamp": ts,
            "message": {"role": "assistant",
                        "content": [{"type": "tool_use", "id": kimlik, "name": arac, "input": girdi}]}}


def son(kimlik: str, ts: str, metin, hata: bool | None = True, tur: str | None = None,
        karar: dict | None = None, kayit_tipi: str = "user") -> dict:
    blok: dict = {"type": "tool_result", "tool_use_id": kimlik, "content": metin}
    if hata is not None:
        blok["is_error"] = hata
    o: dict = {"type": kayit_tipi, "message": {"role": "user", "content": [blok]}}
    if kayit_tipi == "user":
        o["timestamp"] = ts
    if tur is not None:
        o["toolDenialKind"] = tur
    if karar is not None:
        o["permissionDecision"] = karar
    return o


def cift(kimlik: str, arac: str, girdi: dict, bekleme: float, metin, yas: float = 3600, **kw):
    """(tool_use, tool_result) — sonuc `yas` sn once, kullanim `yas + bekleme` sn once."""
    return [kul(kimlik, arac, girdi, iso(yas + bekleme)), son(kimlik, iso(yas), metin, **kw)]


def yaz(dosya: Path, kayitlar: list, crlf: bool = False, ek: str = "") -> None:
    dosya.parent.mkdir(parents=True, exist_ok=True)
    satirlar = [k if isinstance(k, str) else json.dumps(k, ensure_ascii=False) for k in kayitlar]
    ayr = "\r\n" if crlf else "\n"
    dosya.write_bytes((ayr.join(satirlar) + ayr + ek).encode("utf-8"))


ZAMAN_METNI = ("Permission for this command was denied by a built-in Claude Code safety check, "
               "not by the user. Only a person may approve such a removal, and no person did "
               "(the permission prompt timed out, or none was shown). The command was NOT run.")
KULLANICI_METNI = ("The user doesn't want to proceed with this tool use. The tool use was rejected "
                   "(eg. if it was a file edit, the new_string was NOT written to the file).")
SINIF_METNI = ("Permission for this action was denied by the Claude Code auto mode classifier. "
               "Reason: [Credential Exploration] reads a secret file. If you have other tasks ...")
GECICI_METNI = ("model-x is temporarily unavailable, so auto mode cannot determine the safety "
                "of Bash right now. Wait briefly and then try this action again.")


def kok_a(kok: Path) -> None:
    s = kok / "PROJE"
    alt = s / "s1" / "subagents" / "agent-a1.jsonl"
    (alt.parent).mkdir(parents=True, exist_ok=True)
    (alt.parent / "agent-a1.meta.json").write_text(
        json.dumps({"agentType": "backend-expert", "description": "ornek is"}), encoding="utf-8")
    uzun = "echo V02 " + "x" * 200
    R = []
    v01 = cift("t01", "Bash", {"command": "rm -rf $X/V01"}, 0.3, ZAMAN_METNI,
               tur="permission-rule", karar={"decision": "reject", "source": "config",
                                             "reasonType": "safetyCheck",
                                             "circuitBreaker": "dangerousRemoval"})
    R += v01
    R.append(son("t01", iso(3600), ZAMAN_METNI, kayit_tipi="api-request-blob"))   # V14
    R += cift("t02", "Bash", {"command": uzun}, 0.3, ZAMAN_METNI)
    R += cift("t03", "Bash", {"command": "rm -r $Y V03"}, 0.3, "Yeni bicim: guvenlik denetimi onay istedi.",
              tur="permission-rule", karar={"decision": "reject", "source": "config",
                                            "reasonType": "safetyCheck"})
    R += cift("t04", "Bash", {"command": "git clean -fd V04"}, 74,
              KULLANICI_METNI + " To tell you how to proceed, the user said:\ndur, once sor")
    R += cift("t05", "Edit", {"file_path": "/tmp/x/V05.txt"}, 30, "Rejected.", tur="user-rejected")
    R += cift("t06", "Bash", {"command": "cat /tmp/x/V06.env"}, 12, SINIF_METNI,
              tur="automode-blocked", karar={"decision": "reject", "source": "config",
                                             "reasonType": "classifier"})
    R += cift("t06b", "Bash", {"command": "rm -r /tmp/x/V06b"}, 12, "blocked",
              tur="automode-blocked", karar={"decision": "reject", "source": "config",
                                             "reasonType": "classifier",
                                             "classifierCategory": "irreversible_local_destruction"})
    R += cift("t07", "Bash", {"command": "ls V07"}, 60, GECICI_METNI)
    R += cift("t07b", "Bash", {"command": "ls V07b"}, 60, "try later", tur="automode-unavailable")
    R += cift("t08", "Bash", {"command": "rm -r /tmp/x V08"}, 0.5,
              "Permission to use Bash with command rm -r /tmp/x V08 has been denied.")
    R += cift("t08b", "Bash", {"command": "rm -r /tmp/y V08b"}, 0.5, "denied",
              tur="permission-rule", karar={"decision": "reject", "source": "config",
                                            "reasonType": "subcommandResults"})
    R += cift("t09", "Write", {"file_path": "/tmp/x/V09.py"}, 0.5,
              "PreToolUse:Write hook error: [python hook]: BLOK — kural ihlali")
    R += cift("t09b", "Write", {"file_path": "/tmp/x/V09b.py"}, 0.5, "engellendi",
              tur="permission-rule", karar={"decision": "reject", "source": "hook",
                                            "reasonType": "hook"})
    R += cift("t10", "Read", {"file_path": "/tmp/x/V10.txt"}, 9, "dosya icerigi", hata=None,
              karar={"decision": "accept", "source": "user_temporary", "grantScope": "once"})
    R += cift("t11", "Bash", {"command": "ls V11"}, 1, "Something new happened.", tur="yeni-tur")
    R += cift("t11b", "Bash", {"command": "ls V11b"}, 1, "Permission prompt was dismissed by policy.")
    R += cift("t12", "Read", {"file_path": "/tmp/x/V12.log"}, 0.2, ZAMAN_METNI, hata=False)
    R += cift("t13", "Bash", {"command": "grep proceed /tmp/x/V13.log"}, 0.4,
              "Exit code 1\n" + KULLANICI_METNI,
              karar={"decision": "accept", "source": "config", "reasonType": "rule"})
    R += cift("t15", "Bash", {"command": "cp a /tmp/x/V15"}, 0.4,
              "Exit code 1\ncp: cannot create regular file '/tmp/x/V15': Permission denied")
    R += cift("t16", "Bash", {"command": "sleep 999 V16"}, 120.5,
              "Exit code 143\nCommand timed out after 2m 0s")
    R += cift("t17", "Bash", {"command": "rm -rf /tmp/x/V17a"}, 400, "", hata=False,
              karar={"decision": "accept", "source": "user_temporary"})
    R += cift("t17b", "Bash", {"command": "make V17b", "timeout": 600000}, 400, "ok", hata=False,
              karar={"decision": "accept", "source": "config", "reasonType": "rule"})
    R += cift("t17c", "Bash", {"command": "serve V17c", "run_in_background": True}, 400, "id 1",
              hata=False, karar={"decision": "accept", "source": "config"})
    R += cift("t17d", "Read", {"file_path": "/tmp/x/V17d"}, 400, "ok", hata=False,
              karar={"decision": "accept", "source": "config"})
    R += cift("t17e", "Bash", {"command": "rm -rf /tmp/x/V17e"}, 400, KULLANICI_METNI,
              tur="user-rejected")
    R += cift("t17f", "Bash", {"command": "make V17f"}, 179, "ok", hata=False,
              karar={"decision": "accept", "source": "config"})
    R += cift("t19", "Bash", {"command": "ls V19"}, 5, KULLANICI_METNI, tur="automode-blocked")
    R.append(son("yok-boyle-cagri", iso(3600), "Rejected.", tur="user-rejected"))   # V20
    R += cift("t26", "Bash", {"command": "ls V26"}, 0.3, ZAMAN_METNI, yas=3 * 86400)
    yaz(alt, R)
    ana = s / "s1.jsonl"
    yaz(ana, cift("t21", "Bash", {"command": "git reset --hard V21"}, 20, KULLANICI_METNI))


def kok_b(kok: Path) -> None:
    """UCUNCU BAGLAM: baska proje, meta YOK, PowerShell, blok listesi icerik, CRLF, tz'siz damga."""
    f = kok / "PROJE2" / "s2" / "subagents" / "agent-b7.jsonl"
    kayitlar = []
    kayitlar += [kul("p22", "PowerShell", {"command": "Remove-Item -Recurse $env:X V22"}, iso(100.3)),
                 son("p22", iso(100), [{"type": "text", "text": ZAMAN_METNI}])]
    kayitlar.append(kul("p23", "Bash", {"command": "echo V23\u2028satir"}, iso(90.5)))
    kayitlar.append("{bozuk json satiri")
    kayitlar.append(son("p23", iso(90), KULLANICI_METNI + " the user said: tamam\u2028 V23"))
    kayitlar += [kul("p24", "Bash", {"command": "ls V24"}, iso(80.3, z=False)),
                 son("p24", iso(80, z=False), "Permission to use Bash with command ls V24 has been denied.")]
    yaz(f, kayitlar, crlf=True, ek='{"type": "user", "yarim')


def kulm(kimlik: str, arac: str, girdi: dict, ts: str, mid: str) -> dict:
    """Gercek bicim: cok-cagrili mesajin her tool_use blogu AYRI kayitta, ayni message.id ile."""
    k = kul(kimlik, arac, girdi, ts)
    k["message"]["id"] = mid
    return k


def kok_e(kok: Path) -> None:
    """KUYRUK + KARAR KAYNAGI: her senaryo ayri dosyada (mesaj-anahtari mutasyonu dosya icinde kalir)."""
    d = kok / "PROJE" / "s5" / "subagents"
    sinif = {"decision": "accept", "source": "config", "reasonType": "classifier"}
    kul_on = {"decision": "accept", "source": "user_temporary"}
    yaz(d / "agent-e1.jsonl", [
        kulm("e35a", "Bash", {"command": "make kardes-a-uzun", "timeout": 600000}, iso(3600 + 220), "msg_e1"),
        kulm("e35b", "Bash", {"command": "grep -n V35-grep a.py"}, iso(3600 + 218), "msg_e1"),
        son("e35a", iso(3600 + 6), "ok", hata=False, karar={"decision": "accept", "source": "config"}),
        son("e35b", iso(3600), "ok", hata=False, karar=sinif)])
    yaz(d / "agent-e2.jsonl", [
        kulm("e36a", "Bash", {"command": "ls kardes-b-ilk"}, iso(3600 + 331), "msg_e2"),
        kulm("e36b", "Bash", {"command": "rm -rf /tmp/x/V35b"}, iso(3600 + 330), "msg_e2"),
        son("e36a", iso(3600 + 300), "ok", hata=False, karar={"decision": "accept", "source": "config"}),
        son("e36b", iso(3600), "", hata=False, karar=kul_on)])
    yaz(d / "agent-e3.jsonl", [
        kulm("e37a", "Bash", {"command": "make kardes-c-uzun", "timeout": 600000}, iso(3600 + 220), "msg_e3a"),
        kulm("e37b", "Bash", {"command": "rm -rf /tmp/x/V35c"}, iso(3600 + 218), "msg_e3b"),
        son("e37a", iso(3600 + 6), "ok", hata=False, karar={"decision": "accept", "source": "config"}),
        son("e37b", iso(3600), "", hata=False, karar=kul_on)])
    yaz(d / "agent-e4.jsonl",
        cift("e38", "Bash", {"command": "make V36-oto"}, 400, "ok", hata=False, karar=sinif)
        + cift("e39", "Bash", {"command": "make V36b-alansiz"}, 400, "ok", hata=False))
    # V37 (bug-gate-2 #403 F1b): KORUMA YONU — kalici kullanici onayi da kullanici kararidir.
    yaz(d / "agent-e5.jsonl",
        cift("e40", "Bash", {"command": "rm -rf /tmp/x/V37-kalici"}, 400, "", hata=False,
             karar={"decision": "accept", "source": "user_permanent"}))


def kos(arac: Path, ek: list[str]) -> tuple[int, str]:
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CONFIG_DIR"}
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, str(arac), "--simdi", SIMDI.isoformat()] + ek,
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=120)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def jkos(arac: Path, ek: list[str]) -> tuple[int, dict | None, str]:
    rc, out = kos(arac, ek + ["--json"])
    try:
        return rc, json.loads(out), out
    except Exception:
        return rc, None, out


def bul(d: dict | None, isaret: str) -> list[dict]:
    if not d:
        return []
    return [o for o in d.get("olaylar", []) if isaret in o.get("komut", "")]


def tek(d: dict | None, isaret: str) -> dict:
    x = bul(d, isaret)
    return x[0] if len(x) == 1 else {}


def senaryolar(arac: Path) -> None:
    ka = _tmp() / "projects"
    kok_a(ka)
    rc, d, ham = jkos(arac, ["--kok", str(ka)])
    o = tek(d, "V01")
    kayit("V01 ZAMAN-ASIMI metin+alan + alt ajan adi + bekleme",
          o.get("kategori") == "ZAMAN-ASIMI" and o.get("katman") == "metin+alan"
          and o.get("ajan") == "backend-expert/ornek is" and o.get("ajan_turu") == "alt"
          and o.get("bekleme_sn") == 0.3 and o.get("detay") == "circuitBreaker=dangerousRemoval",
          f"{o} rc={rc} {ham[:200] if d is None else ''}")
    o = tek(d, "V02")
    kayit("V02 ZAMAN-ASIMI yalniz metin + komut ozu kesilir",
          o.get("kategori") == "ZAMAN-ASIMI" and o.get("katman") == "metin"
          and o.get("komut", "").endswith("…") and len(o.get("komut", "")) == 121, str(o)[:200])
    o = tek(d, "V03")
    kayit("V03 ZAMAN-ASIMI yalniz alan", o.get("kategori") == "ZAMAN-ASIMI" and o.get("katman") == "alan",
          str(o))
    o = tek(d, "V04")
    kayit("V04 KULLANICI-REDDI metin + not detayda",
          o.get("kategori") == "KULLANICI-REDDI" and "kullanici notu: dur" in o.get("detay", "")
          and o.get("bekleme_sn") == 74, str(o))
    o = tek(d, "V05")
    kayit("V05 KULLANICI-REDDI yalniz alan + TaskStop uyarisi",
          o.get("kategori") == "KULLANICI-REDDI" and o.get("katman") == "alan"
          and "TaskStop" in o.get("detay", ""), str(o))
    o = tek(d, "V06.env")
    kayit("V06 SINIFLANDIRICI-REDDI metin+alan, detay Reason kategorisi",
          o.get("kategori") == "SINIFLANDIRICI-REDDI" and o.get("katman") == "metin+alan"
          and o.get("detay") == "Credential Exploration", str(o))
    o = tek(d, "V06b")
    kayit("V06b SINIFLANDIRICI-REDDI yalniz alan, detay classifierCategory",
          o.get("kategori") == "SINIFLANDIRICI-REDDI" and o.get("katman") == "alan"
          and o.get("detay") == "irreversible_local_destruction", str(o))
    o = tek(d, "ls V07b")
    kayit("V07b GECICI yalniz alan", o.get("kategori") == "GECICI" and o.get("katman") == "alan", str(o))
    o = [x for x in bul(d, "ls V07") if not x["komut"].endswith("b")]
    kayit("V07 GECICI yalniz metin", len(o) == 1 and o[0]["kategori"] == "GECICI"
          and o[0]["katman"] == "metin", str(o))
    o = tek(d, "x V08")
    kayit("V08 KURAL-REDDI yalniz metin", o.get("kategori") == "KURAL-REDDI" and o.get("katman") == "metin",
          str(o))
    o = tek(d, "V08b")
    kayit("V08b KURAL-REDDI yalniz alan", o.get("kategori") == "KURAL-REDDI" and o.get("katman") == "alan",
          str(o))
    o = tek(d, "V09.py")
    kayit("V09 HOOK-BLOKU yalniz metin", o.get("kategori") == "HOOK-BLOKU" and o.get("katman") == "metin",
          str(o))
    o = tek(d, "V09b")
    kayit("V09b HOOK-BLOKU yalniz alan", o.get("kategori") == "HOOK-BLOKU" and o.get("katman") == "alan",
          str(o))
    o = tek(d, "V10")
    kayit("V10 ONAYLANDI (accept + user_temporary)",
          o.get("kategori") == "ONAYLANDI" and o.get("detay") == "kapsam=once"
          and o.get("bekleme_sn") == 9, str(o))
    o = [x for x in bul(d, "ls V11") if not x["komut"].endswith("b")]
    kayit("V11 SINIFLANMADI: taninmayan toolDenialKind dusurulmez",
          len(o) == 1 and o[0]["kategori"] == "SINIFLANMADI" and o[0]["katman"] == "alan", str(o))
    o = tek(d, "V11b")
    kayit("V11b SINIFLANMADI: izin-benzeri taninmayan metin",
          o.get("kategori") == "SINIFLANMADI" and o.get("katman") == "metin", str(o))
    kayit("V12 FP: is_error=false sonuctaki imza metni olay DEGIL", not bul(d, "V12"), str(bul(d, "V12")))
    kayit("V13 FP: arac kostu (accept), ciktidaki red metni olay DEGIL", not bul(d, "V13"),
          str(bul(d, "V13")))
    kap = (d or {}).get("kapsam", {})
    kayit("V14 FP: api-request-blob kopyasi sayilmaz",
          len(bul(d, "V01")) == 1 and kap.get("kopya_kayit_atlanan") == 1
          and kap.get("damgasiz_sonuc") == 0, f"V01={len(bul(d, 'V01'))} kapsam={kap}")
    kayit("V15 FP: isletim sistemi Permission denied olay DEGIL", not bul(d, "V15"), str(bul(d, "V15")))
    kayit("V16 FP: komutun kendi zaman asimi olay DEGIL", not bul(d, "V16"), str(bul(d, "V16")))
    o = tek(d, "V17a")
    kayit("V17 GEC-ONAY: limit + 1 dk asildi, komut kostu",
          o.get("kategori") == "GEC-ONAY" and o.get("katman") == "sure" and o.get("bekleme_sn") == 400
          and "limit=2 dk" in o.get("detay", "") and "user_temporary" in o.get("detay", ""), str(o))
    kayit("V17b timeout=600000 komut 400 sn'de GEC-ONAY degil", not bul(d, "V17b"), str(bul(d, "V17b")))
    kayit("V17c arka plan komutu GEC-ONAY degil", not bul(d, "V17c"), str(bul(d, "V17c")))
    kayit("V17d Read araci GEC-ONAY degil", not bul(d, "V17d"), str(bul(d, "V17d")))
    o = tek(d, "V17e")
    kayit("V17e uzun bekleme sonrasi red KULLANICI-REDDI kalir",
          o.get("kategori") == "KULLANICI-REDDI" and o.get("bekleme_sn") == 400, str(o))
    kayit("V17f 179 sn esigin altinda", not bul(d, "V17f"), str(bul(d, "V17f")))
    o = tek(d, "V19")
    kayit("V19 metin/alan celiskisi: kategori metinden + sayac",
          o.get("kategori") == "KULLANICI-REDDI" and o.get("celiski") is True
          and kap.get("metin_alan_celiskisi") == 1, f"{o} celiski={kap.get('metin_alan_celiskisi')}")
    o = [x for x in (d or {}).get("olaylar", []) if x.get("arac") == "?"]
    kayit("V20 eslesmeyen tool_use_id: arac ? + bekleme None, cokmez",
          len(o) == 1 and o[0]["bekleme_sn"] is None and o[0]["kategori"] == "KULLANICI-REDDI", str(o))
    o = tek(d, "V21")
    kayit("V21 ana oturum olayi", o.get("ajan_turu") == "ana" and o.get("kategori") == "KULLANICI-REDDI",
          str(o))
    kayit("V26a pencere disi olay (3 gun once) --gun 1'de YOK",
          not bul(d, "V26") and kap.get("pencere_disi_olay") == 1, f"{bul(d, 'V26')} {kap}")
    _, d5, _ = jkos(arac, ["--kok", str(ka), "--gun", "5"])
    kayit("V26b ayni olay --gun 5'te VAR (cift yon)", len(bul(d5, "V26")) == 1, str(bul(d5, "V26")))
    if d:
        sayim = {k: 0 for k in KATEGORILER}
        for x in d["olaylar"]:
            sayim[x["kategori"]] += 1
        json_ok = sayim == d["ozet"]
    else:
        json_ok, sayim = False, {}
    rc_t, metin = kos(arac, ["--kok", str(ka)])
    ozet_satir = next((s for s in metin.splitlines() if s.startswith("[izin] OZET")), "")
    metin_ok = all(f"{k.lower().replace('-', '_')}={n}" in ozet_satir for k, n in sayim.items()) \
        and f"olay={sum(sayim.values())}" in ozet_satir
    kayit("V31 --json ozet = olay listesi = metin OZET", json_ok and metin_ok and rc == 0 and rc_t == 0,
          f"json={json_ok} metin={metin_ok} ozet={ozet_satir[:200]}")
    olay_disi = [s for s in metin.splitlines() if not s.startswith("[izin] OLAY ")]
    sizan = [s for s in olay_disi for k in KATEGORILER if k in s]
    kayit("V30 olay disi satirlar kategori adini buyuk harfle tekrarlamaz",
          not sizan and not any("OLAY " in s for s in olay_disi), str(sizan[:2]))
    v01_satir = next((s for s in metin.splitlines() if "V01" in s and s.startswith("[izin] OLAY ")), "")
    kayit("V34 OLAY satiri ajan + arac + bekleme + katman tasir",
          "alt:backend-expert/ornek is" in v01_satir and "arac=Bash" in v01_satir
          and "bekleme_sn=0.3" in v01_satir and "katman=metin+alan" in v01_satir
          and v01_satir.startswith("[izin] OLAY ZAMAN-ASIMI "), v01_satir)
    kayit("V29a KAPSAM + BAKILMAYANLAR olay varken basilir",
          "[izin] KAPSAM kok=" in metin and "[izin] KAPSAM BAKILMAYANLAR:" in metin, metin[-300:])

    # ── kok E: kuyruk + karar kaynagi (bug-gate #403 F1) ─────────────────────
    ke = _tmp() / "projects"
    kok_e(ke)
    rce, de, hame = jkos(arac, ["--kok", str(ke)])
    kayit("V35 ayni mesajda sira beklemesi GEC olayi uretmez (gercek vaka bicimi)",
          de is not None and rce == 0 and not bul(de, "V35-grep"), f"rc={rce} {bul(de, 'V35-grep')} {hame[-200:] if de is None else ''}")
    o = tek(de, "V35b")
    kayit("V35b bekleme kardesin sonucundan: GEC-ONAY bekleme 300, kuyruk 30",
          o.get("kategori") == "GEC-ONAY" and o.get("bekleme_sn") == 300 and o.get("kuyruk_sn") == 30,
          str(o))
    o = tek(de, "V35c")
    kayit("V35c farkli message.id sira sayilmaz: GEC-ONAY bekleme 218, kuyruk 0",
          o.get("kategori") == "GEC-ONAY" and o.get("bekleme_sn") == 218 and o.get("kuyruk_sn") == 0,
          str(o))
    o = tek(de, "V36-oto")
    kayit("V36 config/classifier kabulu GEC-OTOKABUL (GEC-ONAY degil)",
          o.get("kategori") == "GEC-OTOKABUL" and "config" in o.get("detay", ""), str(o))
    o = tek(de, "V36b")
    kayit("V36b karar alani yok -> GEC-ONAY kalir", o.get("kategori") == "GEC-ONAY", str(o))
    o = tek(de, "V37-kalici")
    kayit("V37 user_permanent karari GEC-ONAY (GEC-OTOKABUL degil)",
          o.get("kategori") == "GEC-ONAY" and o.get("bekleme_sn") == 400
          and "user_permanent" in o.get("detay", ""), str(o))

    # ── kok B: ucuncu baglam ────────────────────────────────────────────────
    kb = _tmp() / "projects"
    kok_b(kb)
    rcb, db, hamb = jkos(arac, ["--kok", str(kb)])
    o = tek(db, "V22")
    kayit("V22 PowerShell + blok listesi + CRLF + meta yok",
          o.get("kategori") == "ZAMAN-ASIMI" and o.get("arac") == "PowerShell"
          and o.get("ajan") == "agent-b7" and o.get("bekleme_sn") == 0.3, f"{o} rc={rcb} {hamb[-300:] if db is None else ''}")
    kb_kap = (db or {}).get("kapsam", {})
    o = tek(db, "V23")
    kayit("V23 U+2028 gecerli kayit bozuk sayilmaz, kasitli bozuk satir 1",
          o.get("kategori") == "KULLANICI-REDDI" and kb_kap.get("bozuk_satir") == 1,
          f"{o} bozuk={kb_kap.get('bozuk_satir')}")
    o = tek(db, "V24")
    kayit("V24 tz'siz damga cokmez, olay bulunur", o.get("kategori") == "KURAL-REDDI", str(o))
    kayit("V25 yarim son satir bozuk sayilmaz", db is not None and kb_kap.get("bozuk_satir") == 1, str(kb_kap))

    # ── filtreler ───────────────────────────────────────────────────────────
    birlesik = _tmp() / "projects"
    kok_a(birlesik)
    kok_b(birlesik)
    _, dp, _ = jkos(arac, ["--kok", str(birlesik), "--proje", "PROJE2"])
    _, ds, _ = jkos(arac, ["--kok", str(birlesik), "--seans", "s1"])
    kayit("V32a --seans s1 yalniz s1 (ana + alt)",
          ds is not None and bool(bul(ds, "V01")) and bool(bul(ds, "V21")) and not bul(ds, "V22"), "")
    kayit("V32b --proje PROJE2 yalniz o proje",
          dp is not None and bool(bul(dp, "V22")) and not bul(dp, "V01"), str((dp or {}).get("ozet")))

    # ── kok C: mtime ────────────────────────────────────────────────────────
    kc = _tmp() / "projects"
    f = kc / "PROJE" / "eski.jsonl"
    yaz(f, cift("e1", "Bash", {"command": "rm -rf V27"}, 0.3, ZAMAN_METNI, yas=30 * 86400))
    eski = (SIMDI - _dt.timedelta(days=30)).timestamp()
    os.utime(f, (eski, eski))
    rc_c, out_c = kos(arac, ["--kok", str(kc)])
    kayit("V27a mtime'i eski dosya atlanir -> OLCULEMEDI kapsam-sifir + exit 2",
          rc_c == 2 and "[izin] OLCULEMEDI kapsam-sifir" in out_c and "mtime ile atlanan=1" in out_c,
          f"rc={rc_c} {out_c[:300]}")
    rc_c2, dc2, _ = jkos(arac, ["--kok", str(kc), "--gun", "60"])
    kayit("V27b ayni dosya --gun 60'ta taranir",
          rc_c2 == 0 and len(bul(dc2, "V27")) == 1, f"rc={rc_c2} {bul(dc2, 'V27')}")

    # ── kok yok / olay yok ──────────────────────────────────────────────────
    rc_y, out_y = kos(arac, ["--kok", str(_tmp() / "yok")])
    kayit("V28 kok yok -> OLCULEMEDI + exit 2 + KAPSAM yine basilir",
          rc_y == 2 and "[izin] OLCULEMEDI kok-yok" in out_y and "[izin] KAPSAM BAKILMAYANLAR:" in out_y,
          f"rc={rc_y} {out_y[:200]}")
    kd = _tmp() / "projects"
    yaz(kd / "PROJE" / "temiz.jsonl", cift("n1", "Read", {"file_path": "/tmp/x/a"}, 0.1, "ok",
                                         hata=False, karar={"decision": "accept", "source": "config"}))
    rc_d, out_d = kos(arac, ["--kok", str(kd)])
    kayit("V29 olay yokken KAPSAM + BAKILMAYANLAR basilir, exit 0",
          rc_d == 0 and "olay=0" in out_d and "taranan dosya=1" in out_d
          and "[izin] KAPSAM BAKILMAYANLAR:" in out_d and "TaskStop" in out_d, f"rc={rc_d} {out_d[:200]}")
    rc_u, _ = kos(arac, ["--kok", str(kd), "--gun", "0"])
    kayit("V33 kullanim hatasi -> exit 1", rc_u == 1, f"rc={rc_u}")


def mutant_kur(kip: str) -> Path:
    eski, yeni = CAPA[kip]
    src = ARAC.read_text(encoding="utf-8")
    if src.count(eski) != 1:
        print(f"[DOGRULANAMADI] mutasyon capasi bayat ({kip}): {src.count(eski)} eslesme "
              "(1 bekleniyordu)", flush=True)
        temizle()
        sys.exit(3)
    kok = _tmp()
    (kok / "scripts").mkdir(parents=True)
    hedef = kok / "scripts" / "izin_bekleme_taramasi.py"
    hedef.write_text(src.replace(eski, yeni), encoding="utf-8", newline="\n")
    ikiz = kok / "scripts" / "izin_bekleme_taramasi__taban.py"
    ikiz.write_text(src, encoding="utf-8", newline="\n")
    try:
        compile(hedef.read_text(encoding="utf-8"), str(hedef), "exec")
    except SyntaxError as e:
        print(f"[DOGRULANAMADI] mutant derlenmiyor ({kip}): {e}", flush=True)
        temizle()
        sys.exit(3)
    # KONTROL GRUBU: gecici konumdaki MUTASYONSUZ ikiz, gercek dosyayla ayni olay listesini vermeli.
    kk = _tmp() / "projects"
    kok_a(kk)
    _, a, _ = jkos(ARAC, ["--kok", str(kk)])
    _, b, _ = jkos(ikiz, ["--kok", str(kk)])
    if a is None or b is None or a.get("olaylar") != b.get("olaylar"):
        print("[DOGRULANAMADI] kontrol grubu bozuk: gecici agactaki MUTASYONSUZ kopya gercek "
              "dosyadan FARKLI davraniyor -> olculen sey ORTAM olurdu", flush=True)
        temizle()
        sys.exit(3)
    return hedef


def main() -> int:
    if any(x in ("-h", "--help") for x in sys.argv[1:]):
        print(__doc__)
        return 0
    arg = sys.argv[1:]
    kip = ""
    if arg:
        if arg[0] not in GECERLI_KIP:
            print(f"[KULLANIM] bilinmeyen kip: {arg[0]} (gecerli: {sorted(GECERLI_KIP)})", flush=True)
            return 3
        kip = arg[0]
    arac = mutant_kur(kip) if kip else ARAC
    try:
        senaryolar(arac)
    finally:
        temizle()
    print("=" * 78)
    print(f"IZIN BEKLEME TARAMASI — kip: {kip or 'taban'}")
    print("=" * 78)
    dusen = 0
    for ad, ok, not_ in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + (f"   -> {not_}" if not_ and not ok else ""))
        dusen += 0 if ok else 1
    print(f"{len(SONUC) - dusen}/{len(SONUC)} OK")
    print(f"TOPLAM: {len(SONUC) - dusen} PASS / {dusen} FAIL")
    if not kip:
        return 1 if dusen else 0
    dusen_kume = {ad.split(" ", 1)[0] for ad, ok, _ in SONUC if not ok}
    beklenen = set(BEKLENEN_DUSUS[kip])
    if dusen_kume != beklenen:
        print(f"[DOGRULANAMADI] MUTASYON {kip}: dusen kume BEKLENENDEN FARKLI -> "
              f"eksik={sorted(beklenen - dusen_kume)} fazla={sorted(dusen_kume - beklenen)}")
        return 2
    print(f"  (MUTASYON {kip}: ilan edilen kume {sorted(beklenen)} AYNEN dustu)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
