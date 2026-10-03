#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""agent_stall_watch.py — alt-ajan TAKILMA bekcisi (Q322).

NE DEGIL: hook DEGIL · daemon DEGIL · gate DEGIL · kilit YOK · popup YOK.
   Kendini baslatmaz, kendini yeniden dogurmaz, hicbir seyi bloklamaz, hicbir
   dosyaya YAZMAZ (salt-okur). Lider ajan bir alt-ajan spawn ettiginde Monitor
   ile ELLE baslatir; --sure-dk dolunca kendini bitirir (yetim kalmaz).

NEDEN VAR (olculdu, 2026-09-14 lider + 2026-09-17 bu dal):
   Asili ajan rapor GONDEREMEZ; lider yalniz "bitince haber gelir"e guvenir ⇒
   korluk suresi sinirsiz (vakalar: 20 dk gateway v1, 26 dk infra-expert).
   Heartbeat (governance/agent-teams-operating-model.md §4B) bu boslugu KAPATMAZ:
   ajan bir arac cagrisinin ICINDE asilirsa heartbeat de gonderemez. §4B'nin kendi
   cumlesi: "heartbeat = icerik, watchdog = nabiz".

CANLILIK != ILERLEME (kaldirilan SAP watchdog daemon'unun kok kusuru,
   governance/removed-controls.md satir 25): o daemon "heartbeat taze" derken ajan
   26 dk sifir cikti uretmisti. Bu arac NABZI DEGIL ILERLEMEYI olcer:
   sinyal = sonucu gelmemis (eslesmemis) tool_use + yasi.

SINYAL — neden "sessizlik suresi" DEGIL (olculdu, 865 alt-ajan transkripti,
2026-09-17, bu dal; komut: python scripts/agent_stall_watch.py --olcum-korpus):
   · son blok text            : 828 (%95,7) -> normal bitis
   · eslesmemis tool_use      :  19 (%2,2)  -> HEDEF SINIF (arac cagrisinda kalmis)
   · son blok tool_result     :  20 (%2,3)  -> sonuc geldi ama ajan yazmadan durdu
   · son blok tool_use        :  17 (%2,0)
   Yani ciplak sessizlik son iki hali ayirt EDEMEZ; eslesmemis tool_use eder.
   ⚠ Korpus CANLIDIR (kosan ajanlar yazmaya devam eder) ⇒ sayilar kosumdan kosuma
   birkac birim oynar; kanit SAYI DEGIL, komuttur. Liderin 2026-09-14 olcumu
   890/21 (%2,4) idi — ayni buyukluk sinifi.

ESIK — 12 dk (lider olcumu 2026-09-14): Bash p99 ~ 2 dk · SAP araclari max 2,1 dk ·
   Bash timeout ust siniri 10 dk ⇒ 12 dk mesru en uzun cagrinin ustundedir.

TABAN (--baslangic, varsayilan = baslangic - --gecmis-dk): yalnizca TABANDAN SONRA
   dogmus tool_use'lar degerlendirilir. Gerekce OLCULDU: korpustaki 20 eslesmemis
   tool_use KALICIDIR (oldurulmus/durdurulmus ajanlarin kalintisi) ve taban filtresi
   olmasa her yoklamada yeniden atesler = uyari korlugu. Filtre kalintilari BIR
   BLOKLISTEYLE DEGIL, KURALLA eler: "bu bekcinin penceresinde dogmus olmali".

BILINEN SINIR (kaydin kendi kapsam-disi maddesi): turunu bitirmis ama ENGELLENMIS
   ajan (yazacak yeri yok, sessiz bekliyor) bu sinyalle YAKALANMAZ — orada bekleyen
   tool_use yoktur. Onu brifingdeki "ENGELLENIRSEN DERHAL bildir" maddesi kapsar.
   Ayrica taban ONCESI asilmis bir ajan da yakalanmaz (bilincli tasarim).

CIKTI — yalniz OLAY basar (STATUS seli yok, popup yok). Bes olay turu:
   ASILI? <ajan> <arac> N dk -> SendMessage probe, cevap yoksa TaskStop
   COZULDU <ajan> <arac> (N dk sonra sonuc geldi)
   DONGU? <ajan> N ardisik max_tokens turu (arada tool_use yok)      [2026-10-03]
   IPTAL? <ajan> ~600 sn sonra 'interrupted' kaydi -> ajan oldu       [2026-10-03]
   OLCULEMEDI <sebep>
   Son ikisi bekleyen tool_use OLMAYAN takilmalardir (ASILI? onlari yapisal olarak
   goremez); gerekce + kaynak: `_imza_izle` ustundeki blok.
   Aksiyon olayin ICINDE yazilidir (aksiyon sahibi = lider; removed-controls satir
   25'in ucuncu yeniden-acma sarti).

"0 bulgu" != "temiz" (core §7 KAPSAM BEYANI): kok yoksa / 0 transkript
   gorulebiliyorsa / bir dosya okunamiyorsa arac SESSIZ KALMAZ, OLCULEMEDI basar
   ve hic olcemediyse exit 2 doner.

CIKIS KODU: 0 = olctu (olay basmis olabilir) · 2 = HIC olcemedi · 1 = kullanim hatasi.
   Hukum SATIRDADIR, cikis kodunda degil — lider olaylari Monitor ile canli okur.

KULLANIM (lider, Monitor ile):
    python core/scripts/agent_stall_watch.py
    python core/scripts/agent_stall_watch.py --esik-dk 12 --aralik-sn 60 --sure-dk 60
    python core/scripts/agent_stall_watch.py --proje C--IX-<PROJECT_NAME>
    python core/scripts/agent_stall_watch.py --tek-atim        # tek yoklama, cik
    python core/scripts/agent_stall_watch.py --olcum-korpus    # korpus dagilimi (salt-okur)

TEST KANCALARI (yalniz fixture icin; uretimde kullanilmaz):
    --simdi <ISO>    YAS hesabinda kullanilacak "simdi" (dongu suresi GERCEK saatte kalir)
    --kok <yol>      transkript kokunu degistir (varsayilan:
                     <CLAUDE_CONFIG_DIR|~/.claude>/projects)
"""
# ENFORCES: -  (yeni gate YOK; bu arac hicbir kurali zorlamaz — ADR 0019 merdiveni)
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

ESIK_DK = 12.0
ARALIK_SN = 60.0
SURE_DK = 60.0
GECMIS_DK = 5.0


def transkript_kok() -> Path:
    """Alt-ajan transkript koku.

    __file__ TUREVI DEGIL (CORE-01) ve proje koku DEGIL: transkriptler
    kullanici-seviyesi <config>/projects/<slug>/<seans>/subagents/ altinda yasar.
    """
    ev = os.environ.get("CLAUDE_CONFIG_DIR")
    kok = Path(ev) if ev else Path.home() / ".claude"
    return kok / "projects"


def _zaman(s: str | None) -> _dt.datetime | None:
    if not s or not isinstance(s, str):
        return None
    try:
        z = _dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None
    # ⛔ tz'siz damga UTC sayilir: tz'li ile tz'siz datetime KIYASLANAMAZ/CIKARILAMAZ
    # (TypeError) -> karisik damgali TEK bir transkript tum bekciyi oldururdu (taban
    # kiyasi `< self.taban` ve imza araligi `ts - onceki`). Bug-gate #313 bulgusu.
    return z if z.tzinfo is not None else z.replace(tzinfo=_dt.timezone.utc)


def ajan_adi(dosya: Path) -> str:
    """<ad>.meta.json'den ajan kimligi; yoksa dosya adina duser (yokluk != hata)."""
    meta = dosya.parent / (dosya.stem + ".meta.json")
    try:
        d = json.loads(meta.read_text(encoding="utf-8"))
        tip = str(d.get("agentType") or "?")
        aciklama = str(d.get("description") or "").strip()
        return (f"{tip}/{aciklama}")[:70] if aciklama else tip
    except Exception:
        return dosya.stem


def transkript_tara(dosya: Path) -> tuple[list[dict], list[str], list[dict]]:
    """Bir transkripti tara -> (bekleyen tool_use, olculemedi sebepleri, imza olaylari)."""
    try:
        ham = dosya.read_text(encoding="utf-8", errors="replace")
    except Exception as e:  # okunamayan dosya SESSIZ GECILMEZ
        return [], [f"okunamadi {dosya.name}: {type(e).__name__}"], []
    sebepler: list[str] = []
    imza: dict = {"seri": [], "olay": [], "onceki": None}
    # ⛔ splitlines() DEGIL (canli korpusta olculdu, 2026-09-17): JSONL kayitlari
    # YALNIZ "\n" ile ayrilir, ama str.splitlines() Unicode satir sinirlarini da
    # boler (\x0b \x0c \x1c \x1d \x1e \x85    ). Bir ajanin Bash komutu
    # bu karakterleri HAM olarak tasidiginda (gercek dosya: 351 satirlik bir
    # transkript) tek bir gecerli kayit 3 parcaya bolunuyor ve arac sahte
    # "bozuk-satir" OLCULEMEDI'si basiyordu (olculdu: 2 sahte bulgu / 865 dosya).
    satirlar = ham.split("\n")
    kullanim: dict[str, dict] = {}
    sonuclar: set[str] = set()
    bozuk_indeks: list[int] = []
    kimliksiz_kullanim = 0
    kimliksiz_sonuc = 0
    for i, satir in enumerate(satirlar):
        satir = satir.strip()
        if not satir:
            continue
        try:
            d = json.loads(satir)
        except Exception:
            bozuk_indeks.append(i)
            continue
        m = d.get("message")
        if not isinstance(m, dict):
            continue
        icerik = m.get("content")
        _imza_izle(d, m, icerik, imza)
        if not isinstance(icerik, list):
            continue
        for b in icerik:
            if not isinstance(b, dict):
                continue
            t = b.get("type")
            if t == "tool_use":
                kimlik = b.get("id")
                if isinstance(kimlik, str):
                    kullanim[kimlik] = {"arac": b.get("name") or "?",
                                        "ts": _zaman(d.get("timestamp"))}
                else:
                    # Kimliksiz cagri IZLENEMEZ -> gercek bir takilma SESSIZCE kacar.
                    kimliksiz_kullanim += 1
            elif t == "tool_result":
                sonuc_kimlik = b.get("tool_use_id")
                if isinstance(sonuc_kimlik, str):
                    sonuclar.add(sonuc_kimlik)
                else:
                    # Kimliksiz sonuc ESLESTIRILEMEZ -> bitmis cagri "asili" gorunur (FP).
                    kimliksiz_sonuc += 1
    # SON satirin bozuk olmasi NORMALDIR (yazici tam o anda flush ediyor olabilir);
    # ORTADAKI bozuk satir olculemeyen bir bolum demektir -> sessiz gecilmez.
    ortada = [i for i in bozuk_indeks if i != len(satirlar) - 1]
    if ortada:
        sebepler.append(f"bozuk-satir {dosya.name}: {len(ortada)} satir cozulemedi")
    # Kimliksiz blok SESSIZCE DUSMEZ: biri sahte-ASILI (FP), oteki sessiz KACIS (FN)
    # uretir. Canli korpusta olculdu (2026-09-17): 58.871 tool_use / 58.851 tool_result
    # icinde 0 vaka ⇒ bu satirlar bugun FP uretmez, koruma ileriye donuktur.
    if kimliksiz_kullanim:
        sebepler.append(f"kimliksiz-tool_use {dosya.name}: {kimliksiz_kullanim} cagri izlenemedi")
    if kimliksiz_sonuc:
        sebepler.append(f"kimliksiz-tool_result {dosya.name}: {kimliksiz_sonuc} sonuc eslestirilemedi")
    bekleyen = [{"dosya": dosya, "id": k, "arac": v["arac"], "ts": v["ts"]}
                for k, v in kullanim.items() if k not in sonuclar]
    if any(b["ts"] is None for b in bekleyen):
        sebepler.append(f"zaman-damgasi-yok {dosya.name}")
        bekleyen = [b for b in bekleyen if b["ts"] is not None]
    return bekleyen, sebepler, [dict(o, dosya=dosya) for o in imza["olay"]]


# ── IKI TAKILMA IMZASI (2026-10-03) — ikisi de ILERLEME olcer, sessizlik DEGIL ──
# DONGU? : art arda >=2 assistant turu `stop_reason: max_tokens` ve aralarinda HIC
#   tool_use yok (Claude Code issue #97647: ajan 4 tur x 64k dusunme tokeni yakti,
#   38 dk dosya/metin uretmedi; akis canli oldugu icin ne harness'in watchdog'u ne
#   ASILI? kurali gordu — bekleyen tool_use YOKTUR). Bu korpusta ornek YOK (881 alt-ajan
#   transkriptinde 0 max_tokens turu, 2026-10-03) -> bicim issue'dan alindi.
# IPTAL? : `[Request interrupted by user...]` metinli user kaydi, onceki user/assistant
#   kaydindan IPTAL_ARALIK_SN icinde (issue #84346: 13/14 vakada 600,0-605,6 sn =
#   harness'in ~600 sn watchdog'u; kullanici kesmesi rastgele aralik verir). Ajan
#   OLMUSTUR ve rapor gelmeyecektir. Bu korpusta 5 kesme kaydi var, araliklari
#   0-43 sn (lider TaskStop/ESC) -> hicbiri pencereye dusmez = negatif kontrol.
DONGU_ESIK = 2
IPTAL_ARALIK_SN = (595.0, 620.0)
KESME_ONEKI = "[Request interrupted by user"


def _imza_izle(d: dict, m: dict, icerik, imza: dict) -> None:
    """Tek kaydi iki imza icin isler; durum `imza` sozlugunde (dosya basina)."""
    ts = _zaman(d.get("timestamp"))
    bloklar = icerik if isinstance(icerik, list) else (
        [{"type": "text", "text": icerik}] if isinstance(icerik, str) else [])
    if d.get("type") == "assistant":
        if any(isinstance(b, dict) and b.get("type") == "tool_use" for b in bloklar) \
                or m.get("stop_reason") in ("tool_use", "end_turn"):
            imza["seri"] = []                       # ilerleme var -> seri kirilir
        elif m.get("stop_reason") == "max_tokens" and ts is not None:
            kimlik = m.get("id") or d.get("uuid")   # parcali kayit tek tur sayilir
            if kimlik not in [k for k, _ in imza["seri"]]:
                imza["seri"].append((kimlik, ts))
            if len(imza["seri"]) >= DONGU_ESIK:
                imza["olay"] = [o for o in imza["olay"]
                                if o["id"] != "dongu:" + str(imza["seri"][0][0])]
                imza["olay"].append({"tur": "DONGU", "id": "dongu:" + str(imza["seri"][0][0]),
                                     "ts": ts, "n": len(imza["seri"])})
    if d.get("type") == "user" and ts is not None:
        kesme = any(isinstance(b, dict) and b.get("type") == "text"
                    and str(b.get("text") or "").lstrip().startswith(KESME_ONEKI)
                    for b in bloklar)
        onceki = imza.get("onceki")
        if kesme and onceki is not None:
            aralik = (ts - onceki).total_seconds()
            if IPTAL_ARALIK_SN[0] <= aralik <= IPTAL_ARALIK_SN[1]:
                imza["olay"].append({"tur": "IPTAL", "id": "iptal:" + str(d.get("uuid")),
                                     "ts": ts, "sn": aralik})
    if d.get("type") in ("user", "assistant") and ts is not None:
        imza["onceki"] = ts


def yokla(kok: Path, proje: str | None,
          seans: str | None) -> tuple[list[dict], list[str], list[dict]]:
    """Tek yoklama -> (bekleyen cagrilar, olculemedi sebepleri, imza olaylari). Salt-okur."""
    if not kok.exists():
        return [], [f"kok-yok {kok}"], []
    desen = f"{proje or '*'}/{seans or '*'}/subagents/*.jsonl"
    dosyalar = sorted(kok.glob(desen))
    if not dosyalar:
        return [], [f"kapsam-sifir {kok} ({desen}) - 0 transkript gorulebilir"], []
    bekleyen: list[dict] = []
    sebepler: list[str] = []
    imzalar: list[dict] = []
    for f in dosyalar:
        b, s, im = transkript_tara(f)
        bekleyen.extend(b)
        sebepler.extend(s)
        imzalar.extend(im)
    return bekleyen, sebepler, imzalar


class Bekci:
    """Olay uretici. Durum SADECE bellekte (dosya yok, kilit yok, yetim yok)."""

    def __init__(self, esik_dk: float = ESIK_DK,
                 taban: _dt.datetime | None = None) -> None:
        self.esik_dk = esik_dk
        self.taban = taban
        self.bildirilen: dict[tuple[str, str], dict] = {}
        self.bildirilen_sebep: set[str] = set()
        self.bildirilen_imza: set[tuple[str, str]] = set()
        self.sayac = {"asili": 0, "cozuldu": 0, "olculemedi": 0, "yoklama": 0,
                      "dongu": 0, "iptal": 0}
        self.olculdu = False

    def imza_olaylari(self, imzalar: list[dict]) -> list[str]:
        """DONGU?/IPTAL? — taban sonrasi + bir kez (ayni seri/kayit tekrar basilmaz)."""
        olaylar: list[str] = []
        for o in sorted(imzalar, key=lambda x: x["ts"]):
            anahtar = (str(o["dosya"]), o["id"])
            if anahtar in self.bildirilen_imza or (
                    self.taban is not None and o["ts"] < self.taban):
                continue
            self.bildirilen_imza.add(anahtar)
            ad = ajan_adi(o["dosya"])
            if o["tur"] == "DONGU":
                self.sayac["dongu"] += 1
                olaylar.append(f"DONGU? {ad} {o['n']} ardisik max_tokens turu, arada arac "
                               f"cagrisi yok -> SendMessage probe, cevap yoksa TaskStop")
            else:
                self.sayac["iptal"] += 1
                olaylar.append(f"IPTAL? {ad} {o['sn']:.0f} sn sonra 'interrupted' kaydi "
                               f"(~600 sn harness watchdog) -> ajan OLDU, rapor gelmez: "
                               f"SendMessage ile surdur ya da yeniden spawn")
        return olaylar

    def tur(self, bekleyen: list[dict], sebepler: list[str],
            simdi: _dt.datetime) -> list[str]:
        """Bir yoklamanin olaylarini uret. Ayni cagri icin ASILI? bir kez basilir."""
        self.sayac["yoklama"] += 1
        olaylar: list[str] = []
        if not any(s.startswith(("kok-yok", "kapsam-sifir")) for s in sebepler):
            self.olculdu = True
        for s in sebepler:
            if s not in self.bildirilen_sebep:
                self.bildirilen_sebep.add(s)
                self.sayac["olculemedi"] += 1
                olaylar.append(f"OLCULEMEDI {s}")
        acik: dict[tuple[str, str], dict] = {}
        for b in bekleyen:
            acik[(str(b["dosya"]), b["id"])] = b
        # COZULDU: onceden bildirilmis bir cagri artik bekleyenler arasinda degil
        for anahtar in list(self.bildirilen):
            if anahtar not in acik:
                kayit = self.bildirilen.pop(anahtar)
                self.sayac["cozuldu"] += 1
                olaylar.append(f"COZULDU {kayit['ajan']} {kayit['arac']} "
                               f"({kayit['dk']:.0f} dk sonra sonuc geldi)")
        # ASILI?: taban sonrasi dogmus + esigi asmis + henuz bildirilmemis.
        # Sira EN ESKIDEN yeniye: ilerlemesi en cok durmus cagri once gorunur.
        for anahtar, b in sorted(acik.items(), key=lambda kv: kv[1]["ts"]):
            if anahtar in self.bildirilen:
                continue
            if self.taban is not None and b["ts"] < self.taban:
                continue
            dk = (simdi - b["ts"]).total_seconds() / 60.0
            if dk < self.esik_dk:
                continue
            ad = ajan_adi(b["dosya"])
            self.bildirilen[anahtar] = {"ajan": ad, "arac": b["arac"], "dk": dk}
            self.sayac["asili"] += 1
            olaylar.append(f"ASILI? {ad} {b['arac']} {dk:.0f} dk "
                           f"-> SendMessage probe, cevap yoksa TaskStop")
        return olaylar


def korpus_olcumu(kok: Path) -> int:
    """Salt-okur dagilim olcumu — sinyalin gerekcesini yeniden uretir.

    Hicbir sey yazmaz; docstring'deki sayilarin komutudur (kanit tazelenebilsin).
    """
    if not kok.exists():
        print(f"OLCULEMEDI kok-yok {kok}", flush=True)
        return 2
    dosyalar = sorted(kok.glob("*/*/subagents/*.jsonl"))
    if not dosyalar:
        print(f"OLCULEMEDI kapsam-sifir {kok} - 0 transkript", flush=True)
        return 2
    son_tip: dict[str, int] = {"text": 0, "tool_result": 0, "tool_use": 0, "?": 0}
    eslesmemis = 0
    imza_say = {"DONGU": 0, "IPTAL": 0}
    for f in dosyalar:
        bekleyen, _, imzalar = transkript_tara(f)
        if bekleyen:
            eslesmemis += 1
        for o in imzalar:
            imza_say[o["tur"]] += 1
        t = "?"
        try:
            for satir in f.read_text(encoding="utf-8", errors="replace").split("\n"):
                satir = satir.strip()
                if not satir:
                    continue
                try:
                    d = json.loads(satir)
                except Exception:
                    continue
                m = d.get("message")
                if isinstance(m, dict) and isinstance(m.get("content"), list):
                    for b in m["content"]:
                        if isinstance(b, dict) and b.get("type") in son_tip:
                            t = str(b["type"])
        except Exception:
            pass
        son_tip[t] = son_tip.get(t, 0) + 1
    n = len(dosyalar)
    print(f"KORPUS {kok} - {n} alt-ajan transkripti", flush=True)
    print(f"  eslesmemis tool_use tasiyan  : {eslesmemis} ({eslesmemis * 100 / n:.1f}%)",
          flush=True)
    for k in ("text", "tool_result", "tool_use", "?"):
        v = son_tip.get(k, 0)
        print(f"  son blok {k:12s}: {v} ({v * 100 / n:.1f}%)", flush=True)
    print(f"  imza dongu (max_tokens seri) : {imza_say['DONGU']} · imza iptal (~600 sn "
          f"kesme): {imza_say['IPTAL']}  (taban filtresiz, tum korpus)", flush=True)
    return 0


def ayristir(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="agent_stall_watch.py",
        description="Alt-ajan takilma bekcisi (Q322) - salt-okur, hook DEGIL, daemon DEGIL.")
    p.add_argument("--esik-dk", type=float, default=ESIK_DK)
    p.add_argument("--aralik-sn", type=float, default=ARALIK_SN)
    p.add_argument("--sure-dk", type=float, default=SURE_DK)
    p.add_argument("--gecmis-dk", type=float, default=GECMIS_DK)
    p.add_argument("--baslangic", default=None,
                   help="taban ISO zamani (varsayilan: simdi - gecmis-dk)")
    p.add_argument("--kok", default=None)
    p.add_argument("--proje", default=None, help="proje slug filtresi")
    p.add_argument("--seans", default=None, help="oturum kimligi filtresi")
    p.add_argument("--tek-atim", action="store_true")
    p.add_argument("--olcum-korpus", action="store_true")
    p.add_argument("--simdi", default=None,
                   help="TEST: yas hesabinda kullanilacak simdi (ISO)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    a = ayristir(argv)
    kok = Path(a.kok) if a.kok else transkript_kok()
    if a.olcum_korpus:
        return korpus_olcumu(kok)

    sabit_simdi = None
    if a.simdi:
        sabit_simdi = _zaman(a.simdi)
        if sabit_simdi is None:
            print("KULLANIM: --simdi cozulemedi (ISO bekleniyor)", flush=True)
            return 1

    def _simdi() -> _dt.datetime:
        return sabit_simdi if sabit_simdi else _dt.datetime.now(_dt.timezone.utc)

    if a.baslangic:
        taban = _zaman(a.baslangic)
        if taban is None:
            print("KULLANIM: --baslangic cozulemedi (ISO bekleniyor)", flush=True)
            return 1
    else:
        taban = _simdi() - _dt.timedelta(minutes=a.gecmis_dk)

    # KAPSAM BEYANI (core §7): her kosumda basilir — en kritik an sifir-bulgu anidir.
    print(f"[bekci] KAPSAM kok={kok} · filtre=proje:{a.proje or '*'}/seans:{a.seans or '*'} · "
          f"esik={a.esik_dk:g} dk · aralik={a.aralik_sn:g} sn · sure={a.sure_dk:g} dk · "
          f"taban={taban.isoformat()}", flush=True)
    # Olay token'lari ("DONGU?"/"IPTAL?") bu satirda GECMEZ (S17: grep uyari korlugu).
    print(f"[bekci] IMZALAR: dongu = >={DONGU_ESIK} ardisik max_tokens turu, arada "
          f"tool_use yok (#97647) · iptal = '{KESME_ONEKI}...' kaydi onceki kayittan "
          f"{IPTAL_ARALIK_SN[0]:g}-{IPTAL_ARALIK_SN[1]:g} sn sonra (#84346)", flush=True)
    print("[bekci] BAKMADIGI: taban ONCESI dogmus arac cagrilari/imzalar (eski transkript "
          "kalintilari) · turunu bitirmis ama ENGELLENMIS ajan (bekleyen tool_use yok) · "
          "ana oturum (yalniz subagents/) · ajanin ICERIGI (yalniz ilerleme olculur) · "
          "TEK max_tokens turu · pencere DISI kesmeler (lider TaskStop/ESC) · harness'in "
          "kaydetmedigi oldurmeler", flush=True)

    bekci = Bekci(esik_dk=a.esik_dk, taban=taban)
    bitis = time.monotonic() + a.sure_dk * 60.0
    while True:
        bekleyen, sebepler, imzalar = yokla(kok, a.proje, a.seans)
        for olay in (bekci.tur(bekleyen, sebepler, _simdi())
                     + bekci.imza_olaylari(imzalar)):
            damga = _dt.datetime.now().strftime("%H:%M:%S")
            print(f"[{damga}] {olay}", flush=True)
        if a.tek_atim or time.monotonic() >= bitis:
            break
        time.sleep(max(0.0, min(a.aralik_sn, bitis - time.monotonic())))
    s = bekci.sayac
    # ⛔ OZET SATIRI OLAY TOKEN'LARINI TEKRARLAMAZ: "ASILI?"/"COZULDU"/"OLCULEMEDI"
    # yalniz OLAY satirlarinda gecer. Ozet de o kelimeleri tasisaydi, liderin
    # `grep ASILI?` ile yaptigi okuma HER kosumda bir satir dondururdu (bulgu yokken
    # bile) = uyari korlugu. Olculdu: fixture'in ilk surumu tam bu yuzden 4 sahte
    # sonuc uretti (2026-09-17).
    print(f"[bekci] BITTI - {s['yoklama']} yoklama · asili={s['asili']} · "
          f"cozuldu={s['cozuldu']} · olculemedi={s['olculemedi']} · "
          f"dongu={s['dongu']} · iptal={s['iptal']}", flush=True)
    return 0 if bekci.olculdu else 2


if __name__ == "__main__":
    raise SystemExit(main())
