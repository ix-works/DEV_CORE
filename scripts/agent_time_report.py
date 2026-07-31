#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""agent_time_report.py — ajan duvar-saati ayristirma raporu (T1.1, denetim 2026-07-31).

NEDEN: "Ajanlar neden yavas?" sorusu OLCUMLE cevaplanir (Ek-A.5, DENETIM-2026-07-31).
Bu script o olcumu tekrarlanabilir kilar: transcript dizinindeki alt-ajan kayitlarindan
sure dagilimi, duvar-saati ayrismasi (uretim/arac/bosta), tur-basina uretim, batch-medyani,
tekrar-okuma orani, mukerrer-cagri sayisi ve rol->model dagilimini basar.

KULLANIM:
  python core/scripts/agent_time_report.py [--days N] [--transcript-dir YOL]
  --days N          : yalniz son N gunun ajanlari (varsayilan: tumu)
  --transcript-dir  : varsayilan ~/.claude/projects/<proje-slug>/ (cwd'den turetilir)

SALT-OKUNUR: hicbir dosya yazmaz; cikti stdout. Radar turu metrikleri (P6/P7/P8 trend)
buradan okunur — baseline 2026-07-31: medyan 9,6dk · %50 uretim · %33 bosta · batch=1 ·
tekrar-okuma %63 · 8,4 sn/tur.

YONTEM NOTU (Ek-A.5 ile ayni): olaylar zaman-damgasiyla siralanir; iki olay arasi bosluk
KENDISINI IZLEYEN olayin turune atfedilir (assistant->uretim, tool_result->arac, diger
user->lider-bekleme); >600 sn bosluklar "bosta" sayilir. Tek makine, yaklasik olcum.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

IDLE_ESIK_SN = 600


def _varsayilan_dizin() -> Path:
    # Claude Code proje-slug'i: mutlak yolun ayirac/':' karakterleri '-' olur.
    cwd = str(Path.cwd().resolve())
    slug = cwd.replace(":", "-").replace("\\", "-").replace("/", "-")
    return Path.home() / ".claude" / "projects" / slug


def _pts(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def _analiz(p: Path):
    evler = []
    model = None
    try:
        with p.open(encoding="utf-8") as fh:
            for satir in fh:
                try:
                    d = json.loads(satir)
                except Exception:
                    continue
                if d.get("type") not in ("user", "assistant"):
                    continue
                ts = d.get("timestamp")
                if not ts:
                    continue
                m = d.get("message") or {}
                adlar, girdiler, turler = [], [], set()
                if isinstance(m.get("content"), list):
                    for c in m["content"]:
                        turler.add(c.get("type"))
                        if c.get("type") == "tool_use":
                            adlar.append(c.get("name", "?"))
                            girdiler.append(str(c.get("input"))[:100])
                if d.get("type") == "assistant" and m.get("model") and not model:
                    model = m["model"]
                evler.append((_pts(ts), d["type"], adlar, girdiler, turler))
    except OSError:
        return None
    if len(evler) < 4:
        return None
    evler.sort(key=lambda e: e[0])
    r = dict(dur=evler[-1][0] - evler[0][0], gen=0.0, arac=0.0, bosta=0.0, bekle=0.0,
             tur=0, batch=[], okuma=0, okunan=set(), cagri=0, gorulen={}, model=model)
    for i in range(1, len(evler)):
        bosluk = evler[i][0] - evler[i - 1][0]
        t, adlar, turler = evler[i][1], evler[i][2], evler[i][4]
        if bosluk > IDLE_ESIK_SN:
            r["bosta"] += bosluk
            continue
        if t == "assistant":
            r["gen"] += bosluk
            r["tur"] += 1
            if adlar:
                r["batch"].append(len(adlar))
        elif "tool_result" in turler:
            r["arac"] += bosluk
        else:
            r["bekle"] += bosluk
        for ad, gi in zip(adlar, evler[i][3]):
            r["cagri"] += 1
            r["gorulen"][(ad, gi)] = r["gorulen"].get((ad, gi), 0) + 1
            if ad == "Read":
                r["okuma"] += 1
                r["okunan"].add(gi)
    r["mukerrer"] = sum(v - 1 for v in r["gorulen"].values() if v > 1)
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=0)
    ap.add_argument("--transcript-dir", default="")
    a = ap.parse_args()
    kok = Path(a.transcript_dir) if a.transcript_dir else _varsayilan_dizin()
    if not kok.is_dir():
        print(f"[BILGI] transcript dizini yok: {kok} — olculecek ajan kaydi bulunamadi.")
        return 0
    esik = time.time() - a.days * 86400 if a.days else 0
    dosyalar = [p for p in kok.glob("*/subagents/agent-*.jsonl") if p.stat().st_mtime >= esik]
    sonuc = [r for p in dosyalar if (r := _analiz(p))]
    if not sonuc:
        print(f"[BILGI] {kok} altinda cozumlenebilir alt-ajan kaydi yok"
              f"{f' (son {a.days} gun)' if a.days else ''}.")
        return 0
    surel = sorted(r["dur"] for r in sonuc if r["dur"] > 30)
    D = sum(r["dur"] for r in sonuc) or 1
    G, T = sum(r["gen"] for r in sonuc), sum(r["arac"] for r in sonuc)
    B, W = sum(r["bosta"] for r in sonuc), sum(r["bekle"] for r in sonuc)
    turlu = [r["gen"] / r["tur"] for r in sonuc if r["tur"] > 5]
    batch = [b for r in sonuc for b in r["batch"]]
    okuma = sum(r["okuma"] for r in sonuc)
    tekil = len(set().union(*(r["okunan"] for r in sonuc))) if sonuc else 0
    print(f"AJAN ZAMAN RAPORU — {len(sonuc)} ajan"
          f"{f' (son {a.days} gun)' if a.days else ''} · {kok}")
    if surel:
        print(f"  sure: medyan {statistics.median(surel)/60:.1f} dk · "
              f"p90 {surel[int(len(surel)*.9)]/60:.1f} dk · toplam {D/3600:.1f} saat")
    print(f"  ayrisim: uretim %{100*G/D:.0f} · arac %{100*T/D:.0f} · "
          f"bosta(>10dk) %{100*B/D:.0f} · lider-bekleme %{100*W/D:.0f}")
    if turlu:
        print(f"  uretim/tur: medyan {statistics.median(turlu):.1f} sn · "
              f"tur/ajan medyan {statistics.median([r['tur'] for r in sonuc]):.0f}")
    if batch:
        print(f"  batch-medyani (tur basina arac-cagri): {statistics.median(batch):.0f} "
              f"(hedef >=2, P6)")
    if okuma:
        print(f"  tekrar-okuma: {okuma} Read / {tekil} tekil girdi "
              f"(~%{100*(1-tekil/okuma):.0f})")
    print(f"  mukerrer ayni-cagri: {sum(r['mukerrer'] for r in sonuc)} / "
          f"{sum(r['cagri'] for r in sonuc)} toplam cagri")
    modeller = {}
    for r in sonuc:
        modeller[r["model"] or "?"] = modeller.get(r["model"] or "?", 0) + 1
    print("  model dagilimi: " + " · ".join(f"{k}:{v}" for k, v in
                                            sorted(modeller.items(), key=lambda x: -x[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
