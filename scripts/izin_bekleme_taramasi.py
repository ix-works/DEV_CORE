#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""izin_bekleme_taramasi.py — oturum kayitlarindan IZIN / ONAY olaylarini cikaran GOZLEM araci.

NE DEGIL: hook DEGIL · gate DEGIL · hicbir kurali zorlamaz · hicbir dosyaya YAZMAZ, hicbir
   seyi SILMEZ (salt-okur). Gun sonunda lider ELLE kosar: "bugun hangi ajan kullanici
   onayina takildi, hangi eylem onaysiz kaldigi icin dustu?" sorusunun cevabi.

NEDEN VAR: kullanici ekranda degilken alt ajanin bir eylemi onay penceresine takilir;
   ajan ya bekler ya da eylem sessizce duser ve ajan baska yoldan devam eder. Bu iz yalniz
   oturum kaydinda (`<config>/projects/<proje>/<seans>.jsonl` + `<seans>/subagents/*.jsonl`)
   kalir; ajanin raporu cogu zaman ondan soz etmez.

KATEGORILER (ilk eslesen kazanir; ayrinti `KATEGORI_ACIKLAMA`):
   ZAMAN-ASIMI          yerlesik guvenlik denetimi onay istedi, kimse onaylamadi
                        ("permission prompt timed out, or none was shown")
   KULLANICI-REDDI      kullanici pencerede reddetti ("doesn't want to proceed")
                        ⚠ liderin bekleyen cagriya TaskStop'u AYNI kaydi uretir (asagida)
   SINIFLANDIRICI-REDDI otomatik kip siniflandiricisi reddetti ("Reason: [<Kategori>]")
   GECICI               siniflandirici o an karar veremedi ("cannot determine the safety")
   KURAL-REDDI          izin kurali reddetti ("Permission to use <Arac> ... has been denied")
   HOOK-BLOKU           PreToolUse hook'u blokladi (bekleme DEGIL; ayri sayilir)
   ONAYLANDI            pencere acildi, kullanici ONAYLADI (permissionDecision.source=user_temporary)
   SINIFLANMADI         izin isareti tasiyan ama hicbir imzaya uymayan hata (sessizce DUSURULMEZ)
   GEC-ONAY             on plan Bash/PowerShell limit + 1 dk'dan uzun bekleyip KOSTU; karar kullanicidan
                        (user_temporary / user_permanent) ya da kayitta karar alani yok (asagida)
   GEC-OTOKABUL         ayni sure olcutu, ama karar config/siniflandirici/hook — kullanici penceresi yok
   ⚠ Iki GEC kategorisi "ilk eslesen" sirasina GIRMEZ: yalniz ret kategorisi yokken (sonuc yok,
   ONAYLANDI ya da SINIFLANMADI) sure olcutuyle atanir; ret kategorisini EZMEZ.

IKI KATMAN (kayit bicimi resmi bir sozlesme DEGIL — biri degisirse oteki tutsun diye):
   1. METIN IMZASI   — `tool_result` metninde ayirt edici ifade (gevsek ama ayirt edici).
   2. YAPISAL ALAN   — ayni kayitta `toolDenialKind` + `permissionDecision`
                       {decision, source, reasonType, circuitBreaker, classifierCategory}.
   Ikisi de varsa kategori METINDEN alinir, ayri dusunce `celiski` sayilir (bicim kaymasi
   sinyali). `permissionDecision.decision == "accept"` olan sonucta arac GERCEKTEN kosmustur:
   metindeki imza aracin kendi CIKTISIDIR (ornek: kayit dosyasini okuyan bir grep) ⇒ imza
   aranmaz, yalniz ONAYLANDI degerlendirilir.

OLCULDU (2026-11-08, gelistirildigi makine, tum kayitlar, salt-okur; SAYI degil BICIM kanittir):
   · `toolDenialKind` degerleri: permission-rule · automode-blocked · automode-unavailable ·
     user-rejected. `type:"api-request-blob"` kayitlari ayni tool_result'in KOPYASINI tasir
     ⇒ sayilmaz, ayri sayaca yazilir (zaman damgasi tasimadiklari icin "damgasiz" sayilip
     kapsam beyanini kirletirlerdi; damga tasisalardi olay cift sayilirdi).
   · `is_error` olmayan sonuclarda da imza metni gecebiliyor (ajan bir dosyayi okumus) ⇒
     metin imzasi yalniz `is_error: true` sonucta aranir.
   · tool_use -> tool_result araligi: ZAMAN-ASIMI medyan ~0,3 sn (pencere hic GOSTERILMEDI,
     eylem aninda dustu) · KULLANICI-REDDI ~74 sn · SINIFLANDIRICI-REDDI 12–40 sn ·
     GECICI ~60 sn · KURAL-REDDI / HOOK-BLOKU < 1 sn · ONAYLANDI (hizli araclarda, n=3) ~9 sn
     ⇔ ayni araclarda config-kabulu ~0,3 sn. Bu yuzden her olay `bekleme_sn` tasir.

TASKSTOP == KULLANICI-REDDI (kontrollu deney, 2026-11-08): onay bekleyen bir alt ajan cagrisi
   lider tarafindan TaskStop ile durduruldugunda kayda yazilan sentetik sonuc; metin,
   `toolDenialKind: "user-rejected"`, `toolUseResult: "User rejected tool use"` ve
   `permissionDecision` yoklugu acisindan insan reddiyle BIREBIR aynidir ⇒ arac ikisini
   ayirt ETMEZ. Yalniz pencereye not yazilmissa ("... the user said: <not>") insan oldugu
   kesindir; detay bunu gosterir.

GEC-ONAY (lider olcumu + bu arac, 2026-11-08): on plan Bash/PowerShell komutu kendi zaman
   limitinden uzun kosamaz; tool_use -> tool_result araligi limit + 1 dk'yi asip komut sonunda
   KOSMUSSA, komut baslamadan once bekledi. Karar kullanicidan geldiyse (user_temporary /
   user_permanent) ya da kayitta karar alani yoksa GEC-ONAY; karar config/siniflandirici/hook
   ise GEC-OTOKABUL (kullanici penceresi yok). SIRA (bug-gate PR #403 F1): bekleme, ayni
   assistant mesajindaki (message.id) ONCEKI kardes cagrinin sonucundan baslatilir; sira
   beklemesi `kuyruk_sn`'de ayri durur. Olcum (lider + bug-gate, 2026-11-08): 16 aday alt ajan
   boslugunun 15'i onay beklemesi (14 karar kullanicidan, 1 alan yok), 1'i sira beklemesi
   (karar config/classifier — duzeltmeyle esigin altina iner). 15'in 14'unde komut bir
   `permissions.ask` kuralina uyan alt komut tasiyordu (13 `rm -rf`, 1 `pkill`); kayittaki
   `permissionDecision` pencereyi neyin actigini yalniz 2 vakada (`reasonCode`) soyler
   ⇒ arac "hangi kural" sorusunu CEVAPLAMAZ, yalniz bekleyen cagriyi ve suresini gosterir.

"0 olay" != "temiz" (core §7 KAPSAM BEYANI): her kosumda — olay sifirken de — taranan dosya
   sayisi, pencere, atlananlar ve BAKILMAYANLAR basilir. Kok yoksa ya da pencerede hic dosya
   taranamadiysa arac SUSMAZ: `OLCULEMEDI` basar ve exit 2 doner.

CIKIS KODU: 0 = olctu (olay olabilir de olmayabilir de) · 2 = HIC olcemedi · 1 = kullanim hatasi.
   Hukum SATIRDADIR, cikis kodunda degil. Olay satirlari `[izin] OLAY ` ile baslar; ozet,
   ajan ve kapsam satirlari kategori adini BUYUK HARFLE tekrarlamaz (grep korlugu olmasin).

KULLANIM:
    python core/scripts/izin_bekleme_taramasi.py                 # son 1 gun, tum projeler
    python core/scripts/izin_bekleme_taramasi.py --gun 7
    python core/scripts/izin_bekleme_taramasi.py --proje C--IX-<PROJECT_NAME>
    python core/scripts/izin_bekleme_taramasi.py --seans <oturum-kimligi> --json

TEST KANCALARI (yalniz fixture icin):
    --kok <yol>     kayit koku (varsayilan: <CLAUDE_CONFIG_DIR|~/.claude>/projects)
    --simdi <ISO>   pencere hesabindaki "simdi"
Korpus: tests/fixtures/izin_bekleme_taramasi/run.py
"""
# ENFORCES: -  (yeni gate YOK; bu arac hicbir kurali zorlamaz — ADR 0019 merdiveni)
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

KATEGORILER = ("ZAMAN-ASIMI", "GEC-ONAY", "GEC-OTOKABUL", "KULLANICI-REDDI",
               "SINIFLANDIRICI-REDDI", "GECICI", "KURAL-REDDI", "HOOK-BLOKU", "ONAYLANDI",
               "SINIFLANMADI")
KATEGORI_ACIKLAMA = {
    "ZAMAN-ASIMI": "onay gerekti, kimse onaylamadi (pencere zaman asimi ya da hic gosterilmedi)",
    "GEC-ONAY": "on plan komutu kendi zaman limitinden + 1 dk uzun bekledi, sonra KOSTU; karar "
                "kullanicidan (user_temporary/user_permanent) ya da kayitta karar alani yok",
    "GEC-OTOKABUL": "on plan komutu limitinden + 1 dk uzun bekledi ama karar kullanicidan DEGIL "
                    "(config/siniflandirici/hook) — kullanici penceresi yok; bekleme baska "
                    "kaynakli (siniflandirici gecikmesi ya da kayitta gorulmeyen sira)",
    "KULLANICI-REDDI": "kullanici pencerede reddetti",
    "SINIFLANDIRICI-REDDI": "otomatik kip siniflandiricisi reddetti",
    "GECICI": "siniflandirici o an karar veremedi (tekrar denenebilir)",
    "KURAL-REDDI": "izin kurali reddetti (pencere yok)",
    "HOOK-BLOKU": "PreToolUse hook'u blokladi (bekleme degil)",
    "ONAYLANDI": "pencere acildi, kullanici onayladi",
    "SINIFLANMADI": "izin isareti var, imza taninmadi",
}

# ── KATMAN 1: metin imzalari (kucuk harfe indirilmis, bosluklari teklenmis metinde) ──
IMZA_ZAMAN = re.compile(r"permission prompt timed out|built-in claude code safety check")
IMZA_KULLANICI = re.compile(r"doesn't want to proceed with this tool use"
                            r"|the tool use was rejected")
IMZA_SINIFLANDIRICI = re.compile(r"denied by the (?:claude code )?auto mode classifier")
IMZA_GECICI = re.compile(r"auto mode cannot determine the safety|classifier gave no verdict")
IMZA_KURAL = re.compile(r"^permission to use \S+ .*has been denied")
IMZA_HOOK = re.compile(r"^pretooluse:\S* hook error")
METIN_IMZALARI = (
    ("ZAMAN-ASIMI", IMZA_ZAMAN),
    ("KULLANICI-REDDI", IMZA_KULLANICI),
    ("SINIFLANDIRICI-REDDI", IMZA_SINIFLANDIRICI),
    ("GECICI", IMZA_GECICI),
    ("KURAL-REDDI", IMZA_KURAL),
    ("HOOK-BLOKU", IMZA_HOOK),
)
# Izin-benzeri aday (SINIFLANMADI'ya dusurulecek kume): metnin BASINDA aranir — ret metinleri
# isaret ifadesiyle baslar, aracin kendi hata ciktisi ("exit code 1 ...") baslamaz.
# ⛔ Duz "permission denied" BILINCLI olarak yok: isletim sistemi dosya izni hatasidir.
IZIN_BENZERI = re.compile(r"auto mode|classifier|permission prompt|requires approval"
                          r"|permission (?:to use|for this)|has been denied|haven't granted"
                          r"|not been granted|permission rule")
IZIN_BENZERI_ON_EK = 200
SINIFLANDIRICI_SEBEP = re.compile(r"reason:\s*\[([^\]]{1,80})\]", re.I)
KOMUT_KR = 120
# GEC-ONAY: on plan Bash/PowerShell komutu kendi zaman limitinden uzun KOSAMAZ (arac onu
# keser) ⇒ tool_use -> tool_result araligi limit + PAY'i asiyorsa komut baslamadan once
# bekledi demektir. Limit = input.timeout (ms), yoksa varsayilan 2 dk.
GEC_ONAY_ARACLAR = ("Bash", "PowerShell")
VARSAYILAN_LIMIT_MS = 120000
GEC_ONAY_PAY_SN = 60.0
# Karar bu kaynaklardan geldiyse pencere KULLANICIYA gosterilmistir (olculdu: user_temporary
# hizli araclarda ~9 sn, config ~0,3 sn). Baska kaynakli kabul GEC-ONAY degil GEC-OTOKABUL'dur
# (bug-gate PR #403 F1: 218 sn'lik vaka source=config/classifier — kullanici penceresi YOK).
KULLANICI_KAYNAKLARI = ("user_temporary", "user_permanent")


def kayit_koku() -> Path:
    """Kullanici-seviyesi oturum kayitlari koku (proje koku DEGIL, __file__ turevi DEGIL)."""
    ev = os.environ.get("CLAUDE_CONFIG_DIR")
    kok = Path(ev) if ev else Path.home() / ".claude"
    return kok / "projects"


def _zaman(s: object) -> _dt.datetime | None:
    if not isinstance(s, str) or not s:
        return None
    try:
        z = _dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None
    # tz'siz damga UTC sayilir — tz'li ile tz'siz datetime kiyaslanamaz (TypeError).
    return z if z.tzinfo is not None else z.replace(tzinfo=_dt.timezone.utc)


def _metin(icerik: object) -> str:
    if isinstance(icerik, str):
        return icerik
    if isinstance(icerik, list):
        parca = []
        for x in icerik:
            if isinstance(x, dict):
                t = x.get("text")
                if isinstance(t, str):
                    parca.append(t)
            elif isinstance(x, str):
                parca.append(x)
        return "\n".join(parca)
    return ""


def _normal(metin: str) -> str:
    return re.sub(r"\s+", " ", metin.replace("’", "'")).strip().lower()


def metin_kategorisi(norm: str) -> str | None:
    for kat, desen in METIN_IMZALARI:
        if desen.search(norm):
            return kat
    return None


def alan_kategorisi(kayit: dict) -> str | None:
    """Yapisal alanlardan kategori. None = izin isareti YOK · "?" = isaret var, tur taninmadi."""
    tur = kayit.get("toolDenialKind")
    pd = kayit.get("permissionDecision")
    pd = pd if isinstance(pd, dict) else {}
    karar, kaynak, sebep = pd.get("decision"), pd.get("source"), pd.get("reasonType")
    if karar == "accept":
        return "ONAYLANDI" if kaynak == "user_temporary" else None
    if tur == "user-rejected":
        return "KULLANICI-REDDI"
    if tur == "automode-unavailable":
        return "GECICI"
    if tur == "automode-blocked":
        return "SINIFLANDIRICI-REDDI"
    if karar == "reject":
        if sebep == "safetyCheck" or pd.get("circuitBreaker"):
            return "ZAMAN-ASIMI"
        if kaynak == "hook" or sebep == "hook":
            return "HOOK-BLOKU"
        if sebep == "classifier":
            return "SINIFLANDIRICI-REDDI"
        if sebep in ("rule", "subcommandResults"):
            return "KURAL-REDDI"
        return "?"
    if tur is not None or karar is not None:
        return "?"
    return None


def siniflandir(kayit: dict, blok: dict) -> tuple[str, str, bool] | None:
    """(kategori, katman, celiski) ya da None (izin olayi degil)."""
    alan = alan_kategorisi(kayit)
    pd = kayit.get("permissionDecision")
    kabul = isinstance(pd, dict) and pd.get("decision") == "accept"
    if kabul:
        # Arac GERCEKTEN kostu: metindeki imza aracin kendi ciktisidir, aranmaz.
        return ("ONAYLANDI", "alan", False) if alan == "ONAYLANDI" else None
    if blok.get("is_error") is not True:
        return None
    norm = _normal(_metin(blok.get("content")))
    metin = metin_kategorisi(norm)
    somut_alan = alan if alan not in (None, "?") else None
    if metin and somut_alan:
        return metin, ("metin+alan" if metin == somut_alan else "metin"), metin != somut_alan
    if metin:
        return metin, "metin", False
    if somut_alan:
        return somut_alan, "alan", False
    if alan == "?" or IZIN_BENZERI.search(norm[:IZIN_BENZERI_ON_EK]):
        return "SINIFLANMADI", ("alan" if alan == "?" else "metin"), False
    return None


def _detay(kategori: str, kayit: dict, blok: dict) -> str:
    ham = re.sub(r"\s+", " ", _metin(blok.get("content"))).strip()
    pd = kayit.get("permissionDecision")
    pd = pd if isinstance(pd, dict) else {}
    if kategori == "SINIFLANDIRICI-REDDI":
        m = SINIFLANDIRICI_SEBEP.search(ham)
        if m:
            return m.group(1)
        return str(pd.get("classifierCategory") or "(gerekcesiz)")
    if kategori == "KULLANICI-REDDI":
        # "the user said:" eki yalniz insan pencerede not yazinca gelir; eksikligi insan
        # reddini DISLAMAZ, ama liderin TaskStop'u da TAM bu bicimi uretir (olculdu).
        m = re.search(r"the user said:\s*(.*)", ham, re.I)
        return f"kullanici notu: {m.group(1)[:70]}" if m else "not yok (lider TaskStop'u olabilir)"
    if kategori == "ZAMAN-ASIMI" and pd.get("circuitBreaker"):
        return f"circuitBreaker={pd.get('circuitBreaker')}"
    if kategori == "ONAYLANDI":
        return f"kapsam={pd.get('grantScope') or '?'}"
    return ham[:90]


def komut_limiti_sn(girdi: object) -> float:
    t = girdi.get("timeout") if isinstance(girdi, dict) else None
    if isinstance(t, (int, float)) and not isinstance(t, bool) and t > 0:
        return float(t) / 1000.0
    return VARSAYILAN_LIMIT_MS / 1000.0


def gec_onay_mi(arac: str, girdi: object, bekleme: float | None) -> bool:
    if arac not in GEC_ONAY_ARACLAR or bekleme is None:
        return False
    if isinstance(girdi, dict) and girdi.get("run_in_background"):
        return False          # arka plan komutu: sonuc kaydi baslatma aninda yazilir
    return bekleme > komut_limiti_sn(girdi) + GEC_ONAY_PAY_SN


def gec_kategorisi(kayit: dict) -> str:
    """GEC-ONAY mi GEC-OTOKABUL mu: karar alani VARSA ve kaynak kullanici degilse otokabul."""
    pd = kayit.get("permissionDecision")
    if isinstance(pd, dict) and pd.get("decision") == "accept" \
            and pd.get("source") not in KULLANICI_KAYNAKLARI:
        return "GEC-OTOKABUL"
    return "GEC-ONAY"


def kuyruk_baslangici(kimlik: str, mesaj: str | None, mesaj_sirasi: dict[str, list[str]],
                      sonuc_zamani: dict[str, _dt.datetime],
                      ts: _dt.datetime | None) -> _dt.datetime | None:
    """Ayni assistant mesajindaki ONCEKI kardes cagrilarin en gec sonuc damgasi (<= ts).

    Bug-gate PR #403 F1 (korpusta olculdu): ayni mesajda iki on plan Bash; ilki 214 sn kostu,
    ikincisi SIRADA bekleyip 218 sn sonra sonuc aldi. Bekleme tool_use damgasindan olculurse
    sira beklemesi "onay bekledi" sanilir. Bekleme bu damgadan baslatilir."""
    if mesaj is None or ts is None:
        return None
    sira = mesaj_sirasi.get(mesaj, [])
    onceki = sira[:sira.index(kimlik)] if kimlik in sira else []
    zamanlar = [sonuc_zamani[k] for k in onceki if k in sonuc_zamani and sonuc_zamani[k] <= ts]
    return max(zamanlar) if zamanlar else None


def _karar_ozu(kayit: dict) -> str:
    pd = kayit.get("permissionDecision")
    if not isinstance(pd, dict) or not pd:
        return "permissionDecision=yok"
    return "permissionDecision=" + "/".join(
        str(pd.get(k)) for k in ("decision", "source", "reasonType", "reasonCode") if pd.get(k))


def komut_ozu(arac: str, girdi: object) -> str:
    if isinstance(girdi, dict):
        for anahtar in ("command", "file_path", "pattern", "path", "url", "description"):
            v = girdi.get(anahtar)
            if isinstance(v, str) and v.strip():
                s = v
                break
        else:
            s = json.dumps(girdi, ensure_ascii=False)
    else:
        s = "" if girdi is None else str(girdi)
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= KOMUT_KR else s[:KOMUT_KR] + "…"


def ajan_adi(dosya: Path) -> str:
    meta = dosya.parent / (dosya.stem + ".meta.json")
    try:
        d = json.loads(meta.read_text(encoding="utf-8"))
        tur = str(d.get("agentType") or "?")
        aciklama = str(d.get("description") or "").strip()
        return (f"{tur}/{aciklama}")[:70] if aciklama else tur
    except Exception:
        return dosya.stem


class Tarama:
    def __init__(self, bas: _dt.datetime, simdi: _dt.datetime) -> None:
        self.bas, self.simdi = bas, simdi
        self.olaylar: list[dict] = []
        self.sayac = {"ana": 0, "alt": 0, "mtime_disi": 0, "okunamayan": 0, "bozuk_satir": 0,
                      "kopya_kayit": 0, "damgasiz": 0, "celiski": 0, "pencere_disi_olay": 0}
        self.okunamayanlar: list[str] = []

    def dosya_tara(self, dosya: Path, kok: Path, proje: str, seans: str, tur: str) -> None:
        try:
            if _dt.datetime.fromtimestamp(dosya.stat().st_mtime, _dt.timezone.utc) < self.bas:
                self.sayac["mtime_disi"] += 1
                return
            ham = dosya.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            self.sayac["okunamayan"] += 1
            self.okunamayanlar.append(f"{dosya.name}: {type(e).__name__}")
            return
        self.sayac[tur] += 1
        ajan = "ana" if tur == "ana" else ajan_adi(dosya)
        kullanimlar: dict[str, tuple[str, object, _dt.datetime | None, str | None]] = {}
        mesaj_sirasi: dict[str, list[str]] = {}
        sonuc_zamani: dict[str, _dt.datetime] = {}
        # ⛔ str.splitlines() DEGIL: JSONL'i U+2028 / \x1c gibi Unicode satir sinirlarinda
        # da boler ve gecerli kaydi "bozuk satir" yapar (agent_stall_watch'ta olculdu).
        satirlar = ham.split("\n")
        son = len(satirlar) - 1
        for i, satir in enumerate(satirlar):
            if not satir.strip():
                continue
            try:
                kayit = json.loads(satir)
            except Exception:
                if i != son:      # son satir yarim olabilir (canli yazici) — bozuk sayilmaz
                    self.sayac["bozuk_satir"] += 1
                continue
            if not isinstance(kayit, dict):
                continue
            mesaj = kayit.get("message")
            icerik = mesaj.get("content") if isinstance(mesaj, dict) else None
            if not isinstance(icerik, list):
                continue
            if kayit.get("type") == "api-request-blob":
                if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in icerik):
                    self.sayac["kopya_kayit"] += 1
                continue
            ts = _zaman(kayit.get("timestamp"))
            for blok in icerik:
                if not isinstance(blok, dict):
                    continue
                if blok.get("type") == "tool_use":
                    kimlik = blok.get("id")
                    if isinstance(kimlik, str):
                        mid = mesaj.get("id") if isinstance(mesaj.get("id"), str) else None
                        kullanimlar[kimlik] = (str(blok.get("name") or "?"), blok.get("input"), ts,
                                               mid)
                        if mid is not None and kimlik not in mesaj_sirasi.setdefault(mid, []):
                            mesaj_sirasi[mid].append(kimlik)
                    continue
                if blok.get("type") != "tool_result":
                    continue
                kimlik = str(blok.get("tool_use_id"))
                arac, girdi, ts_kul, mid = kullanimlar.get(kimlik, ("?", None, None, None))
                kuyruk = kuyruk_baslangici(kimlik, mid, mesaj_sirasi, sonuc_zamani, ts)
                bas_kul = max(ts_kul, kuyruk) if (ts_kul and kuyruk) else ts_kul
                if ts is not None:
                    sonuc_zamani[kimlik] = ts
                bekleme = round((ts - bas_kul).total_seconds(), 1) if (ts and bas_kul) else None
                kuyruk_sn = round((bas_kul - ts_kul).total_seconds(), 1) \
                    if (ts_kul and bas_kul and bas_kul > ts_kul) else 0.0
                sonuc = siniflandir(kayit, blok)
                # GEC-ONAY: komut sonunda KOSTU (ret kategorisi yok) ama limitinden uzun bekledi.
                ezilebilir = sonuc is None or sonuc[0] in ("ONAYLANDI", "SINIFLANMADI")
                if ezilebilir and gec_onay_mi(arac, girdi, bekleme):
                    sonuc = (gec_kategorisi(kayit), "sure", False)
                if sonuc is None:
                    continue
                kategori, katman, celiski = sonuc
                if ts is None:
                    self.sayac["damgasiz"] += 1
                    continue
                if not (self.bas <= ts <= self.simdi):
                    self.sayac["pencere_disi_olay"] += 1
                    continue
                if celiski:
                    self.sayac["celiski"] += 1
                detay = (f"limit={komut_limiti_sn(girdi) / 60:g} dk · {_karar_ozu(kayit)}"
                         if kategori in ("GEC-ONAY", "GEC-OTOKABUL") else _detay(kategori, kayit, blok))
                self.olaylar.append({
                    "zaman": ts.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "proje": proje, "seans": seans, "ajan_turu": tur, "ajan": ajan,
                    "arac": arac, "komut": komut_ozu(arac, girdi), "kategori": kategori,
                    "detay": detay, "katman": katman,
                    "celiski": celiski, "bekleme_sn": bekleme, "kuyruk_sn": kuyruk_sn,
                    "dosya": dosya.relative_to(kok).as_posix(),
                })


def dosyalari_bul(kok: Path, proje: str | None, seans: str | None):
    """(dosya, proje, seans, tur) ureteci; siralama deterministik."""
    for pdizin in sorted((p for p in kok.iterdir() if p.is_dir()), key=lambda p: p.name):
        if proje and pdizin.name != proje:
            continue
        for f in sorted(pdizin.glob("*.jsonl"), key=lambda p: p.name):
            if seans and f.stem != seans:
                continue
            yield f, pdizin.name, f.stem, "ana"
        for f in sorted(pdizin.glob("**/subagents/*.jsonl"), key=lambda p: p.as_posix()):
            s = f.relative_to(pdizin).parts[0]
            if seans and s != seans:
                continue
            yield f, pdizin.name, s, "alt"


def _anahtar(kategori: str) -> str:
    return kategori.lower().replace("-", "_")


class _Ayristirici(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        self.print_usage(sys.stderr)
        print(f"[izin] KULLANIM: {message}", file=sys.stderr)
        raise SystemExit(1)


def main(argv: list[str] | None = None) -> int:
    ap = _Ayristirici(description="Oturum kayitlarindan izin/onay olaylarini cikarir (salt-okur).")
    ap.add_argument("--gun", type=float, default=1.0, help="pencere: son N gun (varsayilan 1)")
    ap.add_argument("--kok", default=None, help="kayit koku (varsayilan <config>/projects)")
    ap.add_argument("--proje", default=None, help="yalniz bu proje klasoru (slug)")
    ap.add_argument("--seans", default=None, help="yalniz bu oturum kimligi")
    ap.add_argument("--json", action="store_true", help="JSON cikti")
    ap.add_argument("--simdi", default=None, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if a.gun <= 0:
        ap.error("--gun pozitif olmali")

    simdi = _zaman(a.simdi) if a.simdi else _dt.datetime.now(_dt.timezone.utc)
    if simdi is None:
        ap.error(f"--simdi ayristirilamadi: {a.simdi}")
    bas = simdi - _dt.timedelta(days=a.gun)
    kok = Path(a.kok) if a.kok else kayit_koku()
    t = Tarama(bas, simdi)

    olculemedi: list[str] = []
    if not kok.is_dir():
        olculemedi.append(f"kok-yok ({kok})")
    else:
        for f, proje, seans, tur in dosyalari_bul(kok, a.proje, a.seans):
            t.dosya_tara(f, kok, proje, seans, tur)
        if t.sayac["ana"] + t.sayac["alt"] == 0:
            olculemedi.append("kapsam-sifir (pencerede taranan kayit dosyasi yok)")
    t.olaylar.sort(key=lambda o: (o["zaman"], o["dosya"]))

    ozet = {k: 0 for k in KATEGORILER}
    ajanlar: dict[tuple[str, str, str], dict[str, int]] = {}
    for o in t.olaylar:
        ozet[o["kategori"]] += 1
        d = ajanlar.setdefault((o["ajan_turu"], o["ajan"], o["seans"]), {})
        d[o["kategori"]] = d.get(o["kategori"], 0) + 1

    pencere = (f"{bas.astimezone(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M')}Z.."
               f"{simdi.astimezone(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M')}Z")
    bakilmayanlar = [
        "hook bloklari ayri kategori olarak sayilir (hook_bloku) ama bekleme degildir",
        "isletim sistemi dosya izni hatasi ('Permission denied') izin olayi sayilmaz",
        "pencere acikken oturum kesilirse sonuc kaydi yazilmaz -> olay gorunmez "
        "(eslesmemis tool_use: agent_stall_watch'in alani)",
        "yalniz bu makinedeki kok taranir; baska makine / baska CLAUDE_CONFIG_DIR gorulmez",
        "kayit bicimi resmi sozlesme degil: imza ve alan birlikte degisirse olay "
        "siniflanmadi'ya duser ya da hic gorulmez",
        "onaylandi anlami permissionDecision.source=user_temporary alanindan cikarilir "
        "(sure olcumuyle desteklendi, sozlesme degil)",
        "bekleme_sn = tool_use (ya da ayni mesajdaki onceki kardesin sonucu) -> tool_result "
        "damga farki; aracin kosum suresini de icerir; sira beklemesi kuyruk_sn'de ayri durur",
        "sira yalniz ayni message.id'deki ONCEKI kardesin kayitli sonucuyla olculur; kardesin "
        "sonucu kayitta yoksa (oturum kesildi) sira beklemesi gorulmez",
        "paralel (salt-okur) kardes: arac ayni mesajdaki kardeslerin SERI kostugunu varsayar; "
        "paralel kosan kardeste bekleme yine onceki kardesin sonucundan baslatilir, yani "
        "gercek bekleme kisalir ve esigin altinda kalabilir (2026-11-08, gelistirildigi makine: "
        "190 paralel kardes cagrisi — 168 karar config, 22 karar alani yok, kullanici kararli 0; "
        "kacan vaka gorulmedi, kanit kapsami bu korpus)",
        "gec_otokabul: karar kullanicidan gelmedi (config/siniflandirici/hook); beklemenin "
        "kaynagi (siniflandirici gecikmesi mi, gorulmeyen sira mi) ayirt edilmez",
        "komut limiti input.timeout ya da sabit 2 dk; BASH_DEFAULT_TIMEOUT_MS / BASH_MAX_TIMEOUT_MS "
        "ortam degiskenleri ve 180 sn otomatik arka plana alma (surume bagli) hesaba katilmaz",
        "gec_onay yalniz on plan Bash/PowerShell icin olculur (komut limiti + 1 dk); "
        "diger araclarin (Edit/Write/MCP) gec onayi sure esigi olmadigi icin GORULMEZ, "
        "limitine yakin bekleyip kosan komut da esigin altinda kalir",
        "pencereyi HANGI kuralin actigi kayitta cogu zaman yazmaz (permissionDecision.reasonCode "
        "seyrek); arac bunu cikarmaz",
        "pencere UTC'dir; --gun 1 = son 24 saat (takvim gunu degil)",
        "kullanici_reddi ile liderin bekleyen cagriya TaskStop'u AYIRT EDILEMEZ: ikisinde de "
        "metin, toolDenialKind=user-rejected, toolUseResult ve permissionDecision yoklugu "
        "birebir ayni (kontrollu deney 2026-11-08); yalniz 'the user said:' notu insani gosterir",
    ]
    kapsam = {
        "kok": str(kok), "pencere": pencere, "gun": a.gun,
        "proje_filtresi": a.proje, "seans_filtresi": a.seans,
        "taranan_dosya": {"ana": t.sayac["ana"], "alt": t.sayac["alt"]},
        "mtime_penceresi_disi_atlanan": t.sayac["mtime_disi"],
        "okunamayan_dosya": t.sayac["okunamayan"], "okunamayanlar": t.okunamayanlar[:10],
        "bozuk_satir": t.sayac["bozuk_satir"], "kopya_kayit_atlanan": t.sayac["kopya_kayit"],
        "damgasiz_sonuc": t.sayac["damgasiz"], "pencere_disi_olay": t.sayac["pencere_disi_olay"],
        "metin_alan_celiskisi": t.sayac["celiski"], "olculemedi": olculemedi,
        "bakilmayanlar": bakilmayanlar,
    }

    if a.json:
        print(json.dumps({"ozet": ozet, "olaylar": t.olaylar, "kapsam": kapsam,
                          "kategori_aciklama": KATEGORI_ACIKLAMA},
                         ensure_ascii=False, indent=2))
    else:
        print(f"[izin] OZET pencere={pencere} (son {a.gun:g} gun) · olay={len(t.olaylar)} · "
              + " ".join(f"{_anahtar(k)}={ozet[k]}" for k in KATEGORILER))
        for (tur, ad, seans), d in sorted(ajanlar.items()):
            print(f"[izin] AJAN {tur} {ad} seans={seans[:8]} · "
                  + " ".join(f"{_anahtar(k)}={d[k]}" for k in KATEGORILER if k in d))
        for o in t.olaylar:
            bek = "?" if o["bekleme_sn"] is None else f"{o['bekleme_sn']:g}"
            celiski = " CELISKI" if o["celiski"] else ""
            print(f"[izin] OLAY {o['kategori']} {o['zaman']} {o['ajan_turu']}:{o['ajan']} "
                  f"seans={o['seans'][:8]} arac={o['arac']} bekleme_sn={bek} "
                  f"katman={o['katman']}{celiski} | {o['komut']} | {o['detay']}")
        for s in olculemedi:
            print(f"[izin] OLCULEMEDI {s}")
        print(f"[izin] KAPSAM kok={kok} · taranan dosya={t.sayac['ana'] + t.sayac['alt']} "
              f"(ana {t.sayac['ana']} · alt {t.sayac['alt']}) · mtime ile atlanan="
              f"{t.sayac['mtime_disi']} · okunamayan={t.sayac['okunamayan']} · bozuk satir="
              f"{t.sayac['bozuk_satir']} · kopya kayit (api-request-blob)={t.sayac['kopya_kayit']}"
              f" · damgasiz sonuc={t.sayac['damgasiz']} · pencere disi olay="
              f"{t.sayac['pencere_disi_olay']} · metin/alan celiskisi={t.sayac['celiski']} · "
              f"filtre proje={a.proje or '-'} seans={a.seans or '-'}")
        for x in t.okunamayanlar[:10]:
            print(f"[izin] KAPSAM okunamayan: {x}")
        print("[izin] KAPSAM BAKILMAYANLAR: " + " · ".join(
            f"({i}) {s}" for i, s in enumerate(bakilmayanlar, 1)))
    return 2 if olculemedi else 0


if __name__ == "__main__":
    raise SystemExit(main())
