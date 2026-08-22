# -*- coding: utf-8 -*-
"""Q5 OLCUM ALETI — "brifing metninden IS TURU cikarilabilir mi?" (2026-08-22).

NE ISPATLAR: kuyruk kaydi `Q5`, spawn brifinginin METNINDEN is-turu anahtar kelimeleri
cikarip playbook bolumune eslemeyi oneriyordu. Bu alet, o yonu **TURETILMIS** (elle
bakimli olmayan) dort sozlukle olcer ve atesleme oranini evin bandiyla (%13,9-18,4)
kiyaslar. 2026-08-22 sonucu (612 gercek brif): 4 tasarimin 4'u de bandi asiyor ya da
kapsami ~0 -> yon ELENDI. Ayrintili karar: `governance/infra-changelog.md`
(`sap_worktype_hint` ALT-TUR satiri) + `governance/removed-controls.md` uc-ayakli olcut.

⛔ KORPUS COMMIT EDILMEZ: brifingler musteri/proje icerigi tasir. Korpus, transcript'lerden
YEREL uretilir (`--korpus` ile yolu verilir); bu dosya yalnizca YONTEMI tasir.

KORPUS URETIMI (ozet): `<CLAUDE_HOME>/projects/<slug>/*.jsonl` icindeki `tool_use`
bloklarindan `name in ("Agent","Task")` olanlarin `input.prompt` alani (>=400 karakter).

KULLANIM:
  python governance/research/q5-is-turu-olcumu-2026-08-22/olcum.py \
      --korpus <yol>/brif-korpus.jsonl --core <core-koku>
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_TR = str.maketrans("İIıŞşĞğÜüÖöÇçÂâÎî", "iiissgguuoocciiii")
_TEMIZ = re.compile(r"[^a-z0-9şğüöçı_]+")
_BASLIK = re.compile(r"^#{2,4} ")
_FENCE = re.compile(r"^\s*```")
_INLINE = re.compile(r"`([^`\n]{3,80})`")
_CAPS = re.compile(r"([A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜ0-9_]{2,}(?:[ /-][A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜ0-9_]{2,})+)")
_DOSYA = re.compile(r"\b[\w.-]+\.(?:py|md|abap|json|ya?ml)\b", re.IGNORECASE)
_STOP = set("""ve ile icin bir bu da de den dan gibi ama the for and with from into not
adim kural recete ornek genel not checklist faz bolum ozet giris cikis sonuc tanim liste
zorunlu onemli kritik uyari dikkat hata sorun cozum yontem surec akis test dogrulama
kontrol olcum rapor durum vaka sinif tur tum tam yeni eski dogru yanlis ilk son tek""".split())


def katla(s):
    return s.translate(_TR).lower()


def tokenle(s):
    return [t for t in _TEMIZ.sub(" ", katla(s)).split() if t]


def _pb_dosyalar(core):
    for r, dirs, fs in os.walk(os.path.join(core, "playbook")):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "attic", ".git")]
        for f in sorted(fs):
            if f.endswith(".md"):
                yield os.path.join(r, f)


def sozluk_baslik_ngram(core, esik=2):
    """(A) Playbook BASLIKLARINDAN 2-3'lu n-gram, nadirlik <= esik dosya."""
    aday = {}
    for y in _pb_dosyalar(core):
        for ln in open(y, encoding="utf-8", errors="replace"):
            if not _BASLIK.match(ln):
                continue
            t = tokenle(ln)
            for n in (2, 3):
                for i in range(len(t) - n + 1):
                    p = t[i:i + n]
                    if any(x in _STOP or len(x) < 3 or x.isdigit() for x in p):
                        continue
                    aday.setdefault(" ".join(p), set()).add(y)
    return {k: v for k, v in aday.items() if len(v) <= esik}


def sozluk_kod_ngram(core, esik=2):
    """(B) Playbook KOD PARCALARINDAN (fence + inline) 2-3'lu n-gram."""
    aday = {}
    for y in _pb_dosyalar(core):
        fence = False
        for ln in open(y, encoding="utf-8", errors="replace"):
            if _FENCE.match(ln):
                fence = not fence
                continue
            parcalar = ([ln] if fence else []) + _INLINE.findall(ln)
            for parca in parcalar:
                t = re.findall(r"[a-z_][a-z0-9_]*", katla(parca))
                for n in (2, 3):
                    for i in range(len(t) - n + 1):
                        aday.setdefault(" ".join(t[i:i + n]), set()).add(y)
    return {k: v for k, v in aday.items() if len(v) <= esik}


def sozluk_caps(core, esik=2, kod_kesisimi=False):
    """(C) Basliktaki BUYUK-HARF terim demetleri; istege bagli KOD baglami kesisimi."""
    aday = {}
    for y in _pb_dosyalar(core):
        for ln in open(y, encoding="utf-8", errors="replace"):
            if not _BASLIK.match(ln):
                continue
            for m in _CAPS.findall(ln):
                ifade = " ".join(tokenle(m))
                if len(ifade.split()) >= 2:
                    aday.setdefault(ifade, set()).add(y)
    sz = {k: v for k, v in aday.items() if len(v) <= esik}
    if not kod_kesisimi:
        return sz
    kod = []
    for y in _pb_dosyalar(core):
        fence = False
        for ln in open(y, encoding="utf-8", errors="replace"):
            if _FENCE.match(ln):
                fence = not fence
                continue
            if fence:
                kod.append(katla(ln))
            kod.extend(katla(x) for x in _INLINE.findall(ln))
    KOD = "\n".join(kod)
    return {k: v for k, v in sz.items() if k in KOD}


def sozluk_script(core):
    """(D) scripts/ envanterinden turetilmis is-turu ifadeleri (fiil oneki atilir)."""
    fiil = {"create", "populate", "push", "deploy", "build", "check", "run", "get", "list",
            "download", "fetch", "sync", "gen", "scaffold", "refresh", "init", "delete",
            "activate", "doc", "send", "capture", "html", "make", "update", "add"}
    sz = {}
    for r, dirs, fs in os.walk(os.path.join(core, "scripts")):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "attic", ".git")]
        for f in fs:
            if not f.endswith(".py"):
                continue
            t = f[:-3].lower().split("_")
            while t and t[0] in fiil:
                t = t[1:]
            if len(t) >= 2:
                sz.setdefault(" ".join(t), set()).add(f)
    return sz


def olc(brifler, sz):
    ates = 0
    for d in brifler:
        p = katla(d["prompt"])
        anilan = {x.lower() for x in _DOSYA.findall(d["prompt"])}
        for ifade, yollar in sz.items():
            if ifade not in p:
                continue
            if any(os.path.basename(str(y)).lower() in anilan for y in yollar):
                continue
            ates += 1
            break
    return ates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--korpus", required=True, help="brif-korpus.jsonl (git'e GIRMEZ)")
    ap.add_argument("--core", required=True, help="core koku (playbook/ + scripts/ burada)")
    a = ap.parse_args()
    brifler = [json.loads(x) for x in open(a.korpus, encoding="utf-8")]
    print("korpus: %d brif" % len(brifler))
    print("EV BANDI (kiyas): %13,9 - %18,4 atesleme")
    for ad, sz in (("A baslik n-gram", sozluk_baslik_ngram(a.core)),
                   ("B kod n-gram", sozluk_kod_ngram(a.core)),
                   ("C CAPS baslik", sozluk_caps(a.core)),
                   ("D CAPS n KOD", sozluk_caps(a.core, kod_kesisimi=True)),
                   ("E script envanteri", sozluk_script(a.core))):
        n = olc(brifler, sz)
        print("%-20s ifade=%-6d atesleme=%4d  %%%.1f" %
              (ad, len(sz), n, 100.0 * n / max(len(brifler), 1)))


if __name__ == "__main__":
    main()
