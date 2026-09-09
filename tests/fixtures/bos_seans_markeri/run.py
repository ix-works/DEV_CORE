#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BOS SEANS MARKERI — cozulemeyen oturum kimligi dedup ANAHTARI olarak yazilirsa
kapi SESSIZCE ve KALICI OLARAK olur (kayit Q253, 2026-09-04).

NEDEN BU KORPUS VAR
-------------------
`itg_backstop._session_id()` oturum kimligi cozulemedigi zaman **bos dize** donuyordu.
O bos dize `.claude/.itg_shown.json` markerina `{"session": ""}` olarak YAZILIYORDU ve
bir sonraki cozulemeyen oturumda karsilastirma `"" == ""` ⇒ **True** ⇒ "ITG bu oturumda
zaten gosterildi" ⇒ hook susuyordu. Susma **sessizdir** (cikti yok, rc 0) ve **kalicidir**
(marker diskte durur). ADR 0022 ITG'yi *"atlanamaz"* ilan ederken kapi olu duruyordu.

⛔ `exit 0` BURADA IKI ANLAMLIDIR — bu korpusun varlik sebebi budur:
   · "SAP tool'u degil / zaten gosterildi"  → mesru sessizlik, rc 0
   · "kapi zehirli marker yuzunden oldu"    → KUSUR, yine rc 0
   Ayirt edici olcut cikis kodu DEGIL, **stdout'ta ITG metni var mi** + **diske yazilan
   marker'in `session` degeri bos mu**.

SINIF (statik envanter, `.current_session` okuyan `scripts/hooks/*.py`):
   1. `itg_backstop.py`      — okur, `==` ile dedup, marker yazar        → KUSURLU (Q253)
   2. `sap_worktype_hint.py` — okur, `!=` ile SIFIRLAMA, marker yazar    → AYNI SINIF
   3. `intake_triage.py`     — okur, PAYLASILAN marker'i YAZAR           → ZEHIRLI URETICI
   4. `session_start.py`     — `.current_session`in KENDISINI yazar; bos kimlikte
                               HIC YAZMAZ (`if not sid: return`) ⇒ bos anahtar
                               uretmez, sinifin uyesi DEGIL (beyaz liste, S8'de civili)
   EVIN EMSALI (dokunulmadi, IC KONTROL GRUBU): `post_validate.py:306-311` ayni sinifi
   ZATEN cozmus (gun damgasi) ve gerekcesi kod icinde yazili; `sap_sync_pull.py:43-50`
   cozulemeyen kimligi `"default"`e dusurur. Ikisi de "bos DEGIL, dejenere ANAHTAR" der.

SENARYOLAR
  S1  taban: temiz proje + SAP tool -> ITG ATESLER (kapi hic olmemisken calisiyor)
  S2  ⭐ KOK VAKA: diskte zehirli `{"session": ""}` + kimlik cozulemez -> ATESLEMELI
  S3  ⭐ MARKER ICERIGI: kimlik cozulemezken yazilan marker BOS OLMAMALI
  S4  FP CAPASI: gercek kimlik + eslesen marker -> SUSAR (dedup bozulmadi)
  S5  FP CAPASI: ayni gun ikinci kosum -> SUSAR (kabul edilen SINIRLI degrade)
  S6  ⭐ GUN SINIRI: dunun damgasi + kimlik cozulemez -> ATESLER (susma kalici DEGIL)
  S7  FP CAPASI: SAP olmayan tool -> cikti YOK **ve marker dosyasi YARATILMAZ**
  S8  FP CAPASI: `mcp__sap-adt__ping` -> sessiz (baglanti testi is degildir)
  S9  ⭐ 3. BAGLAM (gorev-DISI hook): `sap_worktype_hint` + zehirli
      `.worktype_hinted.json` -> hatirlatici HALA konusur
  S10 3. BAGLAM FP CAPASI: ayni hook, gercek kimlik, ayni oturumda ikinci kez -> SUSAR
  S11 ⭐ ZEHIRLI URETICI: `intake_triage` kimlik cozulemezken PAYLASILAN marker'a
      BOS anahtar YAZMAMALI
  S12 ⭐ KOORDINASYON: intake_triage fire etti -> itg_backstop SUSMALI (cifte-fire yok).
      Bu vektor YAZAN ile OKUYAN'in AYNI kurali kullandigini civller.
  S13 SINIF ENVANTERI (statik): `.current_session` okuyan her hook ya beyaz-listedeki
      YAZAR olmali ya da bos-olmayan dejenere anahtar kuralini tasimali. Sinif
      sessizce yeniden BUYUYEMEZ.
  S14 KURAL-KAYNAGI TAZELIGI: fix'in gerekce olarak andigi iki emsal (post_validate
      gun damgasi · sap_sync_pull "default") bugunku agacta HALA duruyor mu.

KOSUM:
    python tests/fixtures/bos_seans_markeri/run.py
    ... --mutasyon             (itg_backstop fix'i sokulur     -> S2/S3/S12 duser)
    ... --mutasyon-worktype    (sap_worktype_hint fix'i sokulur-> S9 duser)
    ... --mutasyon-intake      (intake_triage fix'i sokulur    -> S11/S12 duser)
    ... --mutasyon-envanter    (kuralsiz YENI okuyucu enjekte  -> S13 duser)
  (OLCULDU 2026-09-09, tahmin DEGIL: 11/14 · 13/14 · 12/14 · 13/14. S6 hicbir kipte
   dusmez ve bu DOGRUDUR: gun-damgali marker'a karsi fix-ONCESI kod da atesler
   (`"" != "gun-..."`); S6 kalicilik SINIRININ sozlesme capasidir, mutasyon hedefi degil.)
Cikis: 0 hepsi beklendigi gibi · 1 sapma · 2 DOGRULANAMADI (capa bayat / kontrol grubu bozuk)

⛔ MUTASYON GERCEK KAYNAGA YAZILMAZ: mutasyonlu hook gecici bir agaca kopyalanir
   (`<tmp>/scripts/hooks/<ad>.py` + gercek `scripts/utils` kopyasi — `intake_triage`
   `parents[1]`den `utils.inject_paths` import eder ve o import KORUMASIZDIR).
   Her mutasyon kipinde ONCE **mutasyonsuz kopya** ayni gecici konumdan kosulur ve
   gercek dosyayla AYNI cevabi verdigi dogrulanir (kontrol grubu ORTAMI da kopyalar);
   vermezse sonuc "duser" degil **DOGRULANAMADI**dir (exit 2).
"""
from __future__ import annotations

import datetime
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
HOOKS = REPO / "scripts" / "hooks"

GECERLI_KIP = {"--mutasyon", "--mutasyon-worktype", "--mutasyon-intake",
               "--mutasyon-envanter"}

BUGUN = "gun-" + datetime.date.today().isoformat()
DUN = "gun-" + (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

# Fix'in SOKUMU (mutasyon capalari). Anahtar = hook adi.
CAPA = {
    "itg_backstop": (
        '    return sid or ("gun-" + datetime.date.today().isoformat())\n',
        "    return sid  # MUTASYON: bos kimlik geri geldi (Q253 oncesi davranis)\n"),
    "sap_worktype_hint": (
        '    return sid or ("gun-" + datetime.date.today().isoformat())\n',
        "    return sid  # MUTASYON: bos kimlik geri geldi (Q253 oncesi davranis)\n"),
    "intake_triage": (
        '        sid = sid or ("gun-" + datetime.date.today().isoformat())\n',
        "        pass  # MUTASYON: bos anahtar paylasilan marker'a yaziliyor\n"),
}
KIP_HOOK = {
    "--mutasyon": "itg_backstop",
    "--mutasyon-worktype": "sap_worktype_hint",
    "--mutasyon-intake": "intake_triage",
}

SONUC: list[tuple[str, bool, str]] = []
_GECICI: list[str] = []


def kayit(ad: str, ok: bool, not_: str = "") -> None:
    SONUC.append((ad, ok, not_))


def _tmp() -> Path:
    d = Path(tempfile.mkdtemp(prefix="bosseans_"))
    _GECICI.append(str(d))
    return d


def proje(current_session: str | None = None,
          itg_marker: str | None = None,
          worktype_marker: dict | None = None) -> Path:
    """Izole sahte PROJE koku. Gercek `.claude/` ASLA kullanilmaz."""
    p = _tmp() / "proje"
    (p / ".claude").mkdir(parents=True)
    if current_session is not None:
        (p / ".claude" / ".current_session").write_text(
            json.dumps({"session_id": current_session}), encoding="utf-8")
    if itg_marker is not None:
        (p / ".claude" / ".itg_shown.json").write_text(
            json.dumps({"session": itg_marker}), encoding="utf-8")
    if worktype_marker is not None:
        (p / ".claude" / ".worktype_hinted.json").write_text(
            json.dumps(worktype_marker), encoding="utf-8")
    return p


def mutant_yolu(hook: str) -> Path:
    """Mutasyonlu hook'u, `__file__` turevlerini KORUYAN bir gecici agaca kur."""
    kaynak = HOOKS / f"{hook}.py"
    src = kaynak.read_text(encoding="utf-8")
    eski, yeni = CAPA[hook]
    if src.count(eski) != 1:
        print(f"[DOGRULANAMADI] mutasyon capasi bayat: {hook}.py icinde "
              f"{src.count(eski)} eslesme (1 bekleniyordu)")
        temizle()
        sys.exit(2)
    hedef_kok = _tmp()
    (hedef_kok / "scripts" / "hooks").mkdir(parents=True)
    shutil.copytree(REPO / "scripts" / "utils", hedef_kok / "scripts" / "utils")
    hedef = hedef_kok / "scripts" / "hooks" / f"{hook}.py"
    hedef.write_text(src.replace(eski, yeni), encoding="utf-8", newline="\n")
    # KONTROL GRUBU: ayni konuma MUTASYONSUZ kopya da kurulur (ortam kiyasi icin).
    ikiz = hedef_kok / "scripts" / "hooks" / f"{hook}__taban.py"
    ikiz.write_text(src, encoding="utf-8", newline="\n")
    return hedef


def kos(hook_yolu: Path, payload: dict, proj: Path) -> tuple[int, str, str]:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(proj)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, str(hook_yolu)],
                       input=json.dumps(payload), capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=60)
    return r.returncode, r.stdout or "", r.stderr or ""


def atesledi_itg(out: str) -> bool:
    return "INTAKE TRIAGE" in out


def atesledi_worktype(out: str) -> bool:
    return "worktype" in out.lower()


def marker_degeri(proj: Path, dosya: str) -> str | None:
    f = proj / ".claude" / dosya
    if not f.exists():
        return None
    try:
        return str(json.loads(f.read_text(encoding="utf-8")).get("session"))
    except Exception:
        return None


SAP = {"tool_name": "mcp__sap-adt__adt_get", "tool_input": {"name": "ZSD001"}}
PUSH_DDLS = {"tool_name": "mcp__sap-adt__adt_push_source",
             "tool_input": {"object_type": "ddls", "name": "ZSD001_I_X",
                            "source": "define view entity ZSD001_I_X as select from vbak { vbeln }"}}


def temizle() -> None:
    for d in _GECICI:
        shutil.rmtree(d, ignore_errors=True)


# ── SENARYOLAR ───────────────────────────────────────────────────────────────
def senaryolar(itg: Path, worktype: Path, intake: Path, envanter_kok: Path) -> None:
    # S1 — taban: kapi hic olmemisken calisiyor mu
    p = proje()
    _, out, _ = kos(itg, SAP, p)
    kayit("S1 temiz proje + SAP tool -> ITG atesler", atesledi_itg(out),
          "" if atesledi_itg(out) else f"stdout={out[:120]!r}")

    # S2 — ⭐ KOK VAKA: diskte zehirli bos anahtar, kimlik cozulemez
    p = proje(current_session=None, itg_marker="")
    _, out, _ = kos(itg, SAP, p)
    kayit("S2 zehirli bos marker + kimlik yok -> ATESLEMELI", atesledi_itg(out),
          "" if atesledi_itg(out) else "SESSIZ KALDI = kapi olu (Q253)")

    # S3 — ⭐ yazilan marker BOS OLMAMALI
    p = proje()
    kos(itg, SAP, p)
    deg = marker_degeri(p, ".itg_shown.json")
    kayit("S3 kimlik yokken yazilan marker bos DEGIL", bool(deg), f"session={deg!r}")

    # S4 — FP capasi: dedup hala calisiyor
    p = proje(current_session="S-GERCEK", itg_marker="S-GERCEK")
    _, out, _ = kos(itg, SAP, p)
    kayit("S4 gercek kimlik + eslesen marker -> SUSAR", not atesledi_itg(out),
          "" if not atesledi_itg(out) else "asiri-duzeltme: dedup bozuldu")

    # S5 — FP capasi: ayni gun ikinci kosum (kabul edilen SINIRLI degrade)
    p = proje()
    _, o1, _ = kos(itg, SAP, p)
    _, o2, _ = kos(itg, SAP, p)
    kayit("S5 ayni gun 2. kosum -> SUSAR (gunde bir kez sozlesmesi)",
          atesledi_itg(o1) and not atesledi_itg(o2),
          f"1.kosum={atesledi_itg(o1)} 2.kosum={atesledi_itg(o2)}")

    # S6 — ⭐ gun siniri: susma KALICI degil
    p = proje(current_session=None, itg_marker=DUN)
    _, out, _ = kos(itg, SAP, p)
    kayit("S6 dunun damgasi + kimlik yok -> ATESLER", atesledi_itg(out),
          "" if atesledi_itg(out) else "susma KALICI (gunluk degil)")

    # S7 — FP capasi: SAP olmayan tool hicbir sey yazmamali
    p = proje()
    _, out, _ = kos(itg, {"tool_name": "Read", "tool_input": {"file_path": "x.md"}}, p)
    yok = not (p / ".claude" / ".itg_shown.json").exists()
    kayit("S7 SAP disi tool -> cikti YOK ve marker YAZILMAZ",
          (not atesledi_itg(out)) and yok, f"cikti={out[:60]!r} marker_yok={yok}")

    # S8 — FP capasi: ping is degildir
    p = proje()
    _, out, _ = kos(itg, {"tool_name": "mcp__sap-adt__ping", "tool_input": {}}, p)
    kayit("S8 ping -> sessiz", not atesledi_itg(out), f"cikti={out[:60]!r}")

    # S9 — ⭐ 3. BAGLAM: ayri hook, ayri marker, ayri dedup sekli (`!=` sifirlama)
    p = proje(current_session=None,
              worktype_marker={"session": "", "hinted": ["cds"]})
    _, out, err = kos(worktype, PUSH_DDLS, p)
    kayit("S9 3.BAGLAM worktype: zehirli marker -> HALA konusur",
          atesledi_worktype(out),
          "" if atesledi_worktype(out) else f"SESSIZ (ayni sinif) stdout={out[:80]!r} err={err[:80]!r}")

    # S10 — 3. BAGLAM FP capasi: dedup korunuyor
    p = proje(current_session="S-GERCEK")
    _, w1, _ = kos(worktype, PUSH_DDLS, p)
    _, w2, _ = kos(worktype, PUSH_DDLS, p)
    kayit("S10 3.BAGLAM worktype: ayni oturumda 2. kez -> SUSAR",
          atesledi_worktype(w1) and not atesledi_worktype(w2),
          f"1.kosum={atesledi_worktype(w1)} 2.kosum={atesledi_worktype(w2)}")

    # S11 — ⭐ ZEHIRLI URETICI: intake_triage bos anahtar yazmamali
    p = proje()
    kos(intake, {"prompt": "bu ekrana yeni bir kolon ekleyelim, rapora da gelsin"}, p)
    deg = marker_degeri(p, ".itg_shown.json")
    kayit("S11 intake_triage kimlik yokken BOS anahtar yazmaz",
          deg is not None and bool(deg), f"session={deg!r}")

    # S12 — ⭐ KOORDINASYON: yazan ve okuyan AYNI kurali kullanmali
    p = proje()
    kos(intake, {"prompt": "bu ekrana yeni bir kolon ekleyelim, rapora da gelsin"}, p)
    _, out, _ = kos(itg, SAP, p)
    kayit("S12 intake fire etti -> backstop SUSAR (cifte-fire yok)",
          not atesledi_itg(out),
          "" if not atesledi_itg(out) else "yazan/okuyan kural AYRISTI")

    # S13 — SINIF ENVANTERI (statik): sinif sessizce buyuyemez
    okuyucular, kuralsiz = envanter(envanter_kok)
    kayit("S13 sinif envanteri: her okuyucu dejenere-anahtar kuralini tasir",
          not kuralsiz,
          f"okuyucu={sorted(okuyucular)} kuralsiz={sorted(kuralsiz)}")

    # S14 — KURAL-KAYNAGI TAZELIGI: fix'in andigi iki emsal HALA duruyor mu
    pv = (HOOKS / "post_validate.py").read_text(encoding="utf-8")
    sp = (REPO / "scripts" / "sap_sync_pull.py").read_text(encoding="utf-8")
    emsal1 = 'datetime.date.today().isoformat()' in pv and '"gun-"' in pv
    emsal2 = '"default"' in sp and "SESSION_MARKER" in sp
    kayit("S14 emsal tazeligi: post_validate gun-damgasi + sap_sync_pull 'default'",
          emsal1 and emsal2, f"post_validate={emsal1} sap_sync_pull={emsal2}")


# `session_start.py` SINIFIN UYESI DEGIL: `.current_session`i O YAZAR ve bos kimlikte
# hic yazmaz (`if not sid: return`) ⇒ zehirli anahtar uretemez. Beyaz liste TEK uyelidir
# ve gerekcesi burada yazilidir (liste uzarsa gerekce de uzamali).
BEYAZ_LISTE = {"session_start.py"}
KURAL_IZI = ('datetime.date.today().isoformat()', '"gun-"')


def envanter(hooks_dizini: Path) -> tuple[set[str], set[str]]:
    okuyucular: set[str] = set()
    kuralsiz: set[str] = set()
    for f in sorted(hooks_dizini.glob("*.py")):
        try:
            src = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if ".current_session" not in src:
            continue
        okuyucular.add(f.name)
        if f.name in BEYAZ_LISTE:
            continue
        if not all(iz in src for iz in KURAL_IZI):
            kuralsiz.add(f.name)
    return okuyucular, kuralsiz


KURALSIZ_YENI_HOOK = '''#!/usr/bin/env python3
# ENFORCES: SAHTE  (mutasyon: sinifa kuralsiz yeni uye)
"""MUTASYON ARTEFAKTI — gercek agaca ASLA yazilmaz."""
import json
from pathlib import Path


def _session_id(proj: Path) -> str:
    try:
        d = json.loads((proj / ".claude" / ".current_session").read_text(encoding="utf-8"))
        return str(d.get("session_id") or "")
    except Exception:
        return ""
'''


def main() -> int:
    kipler = [a for a in sys.argv[1:] if a.startswith("--")]
    for k in kipler:
        if k not in GECERLI_KIP:
            print(f"[KULLANIM] bilinmeyen kip: {k} · gecerli: {sorted(GECERLI_KIP)}")
            return 3
    mut = kipler[0] if kipler else None

    yollar = {h: HOOKS / f"{h}.py" for h in
              ("itg_backstop", "sap_worktype_hint", "intake_triage")}
    envanter_kok = HOOKS

    if mut in KIP_HOOK:
        hook = KIP_HOOK[mut]
        mutant = mutant_yolu(hook)
        # KONTROL GRUBU: ayni gecici konumdan MUTASYONSUZ kopya, gercek dosyayla
        # AYNI cevabi vermeli. Vermezse olculen sey mutasyon degil ORTAMDIR.
        ikiz = mutant.parent / f"{hook}__taban.py"
        if hook == "sap_worktype_hint":
            kp = proje(current_session=None, worktype_marker={"session": "", "hinted": ["cds"]})
            kp2 = proje(current_session=None, worktype_marker={"session": "", "hinted": ["cds"]})
            _, a, _ = kos(yollar[hook], PUSH_DDLS, kp)
            _, b, _ = kos(ikiz, PUSH_DDLS, kp2)
            esit = atesledi_worktype(a) == atesledi_worktype(b)
        elif hook == "intake_triage":
            kp, kp2 = proje(), proje()
            pl = {"prompt": "bu ekrana yeni bir kolon ekleyelim, rapora da gelsin"}
            kos(yollar[hook], pl, kp)
            kos(ikiz, pl, kp2)
            esit = marker_degeri(kp, ".itg_shown.json") == marker_degeri(kp2, ".itg_shown.json")
        else:
            kp = proje(current_session=None, itg_marker="")
            kp2 = proje(current_session=None, itg_marker="")
            _, a, _ = kos(yollar[hook], SAP, kp)
            _, b, _ = kos(ikiz, SAP, kp2)
            esit = atesledi_itg(a) == atesledi_itg(b)
        if not esit:
            print(f"[DOGRULANAMADI] kontrol grubu bozuk: {hook} gecici agacta gercek "
                  f"dosyadan FARKLI davraniyor -> olculen sey mutasyon degil ORTAM")
            temizle()
            return 2
        yollar[hook] = mutant

    if mut == "--mutasyon-envanter":
        # Sinifa KURALSIZ yeni bir uye eklenirse S13 gormeli (envanter capasi canli mi).
        kok = _tmp() / "hooks"
        shutil.copytree(HOOKS, kok)
        (kok / "zzz_mutasyon_yeni_okuyucu.py").write_text(
            KURALSIZ_YENI_HOOK, encoding="utf-8", newline="\n")
        envanter_kok = kok

    senaryolar(yollar["itg_backstop"], yollar["sap_worktype_hint"],
               yollar["intake_triage"], envanter_kok)

    print("=" * 78)
    print(f"BOS SEANS MARKERI (Q253) — kip: {mut or 'taban'}")
    print("=" * 78)
    dusen = 0
    for ad, ok, not_ in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + (f"   -> {not_}" if not_ and not ok else ""))
        if not ok:
            dusen += 1
    print(f"TOPLAM: {len(SONUC) - dusen} PASS / {dusen} FAIL")
    temizle()
    return 1 if dusen else 0


if __name__ == "__main__":
    raise SystemExit(main())
