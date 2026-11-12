#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kanca_kablolari.py — `settings.json` kanca kablolamasının AD DÜZEYİ okuması (TEK KAYNAK).

NEDEN VAR (Q406, 2026-11-12): şablon `claude/settings.template.json` 16 kanca bağlar; ama
kurulumdaki kablolamayı ad düzeyinde okuyan tek bir tanım yoktu:
  · `ix_doctor` 4a (D7) dosyanın TAMAMINI tek imzayla kıyaslıyordu ⇒ bir kancanın düşmesi
    yalnız ad vermeyen "template'ten SAPMIŞ" WARN'ı üretiyordu ve zararsız bir proje ayarı
    (ek `allow`) aynı satırı basıyordu — "kanca düştü" ile "proje eki" ayırt edilemiyordu.
  · `ix_doctor` 4f yalnız `pre_tool_guard`ın matcher'ına bakıyordu.
  · `team_setup` `settings.json` için onarım yolu sunmuyordu (tam-dosya tazeleme proje
    eklerini silerdi — F12b, 2026-10-03) ⇒ eski kurulumda eksik kalan kanca ELLE birleştirilirdi.
Bu modül üç tüketiciye AYNI okumayı verir: `ix_doctor` (4h teşhis · 4i smoke) ·
`team_setup --tazele-settings` (yalnız EKSİK şablon bağlantısını ekler) · `parity_probe`.

BAĞLANTI = (olay, eşleyici, kanca adı). Ad, `hook_shim.py`'den sonraki argümandır (exec
biçimi `args`, kabuk biçimi komut dizgesi). Shim üzerinden GİTMEYEN bir komut (projeye özel
betik) `?<komut>` adıyla taşınır: kıyasta birebir eşleşir, hiçbir zaman "şablon kancası" sayılmaz.

⛔ KÖR TAZELEME YOK (2026-08-22 ters yön vakası: projede kablolu `infra_write_guard`
şablonda yoktu): `eksikleri_ekle` hiçbir öğeyi SİLMEZ ve DEĞİŞTİRMEZ; yalnız şablonda olup
projede olmayan bağlantıyı ekler. `permissions` · `env` · `statusLine` · yorum anahtarları
ve proje-özel kancalar dokunulmadan kalır (korpus: tests/fixtures/kanca_kablolama M2).
"""
from __future__ import annotations

import copy
import re
from collections import Counter

# `_comment*` eleme kuralının TEK evi D7 ortak modülüdür (Q212; d7_drift_imzasi V16 kopya
# tanımı yasaklar). Çağıranlar (ix_doctor · team_setup · parity_probe) `scripts/`i sys.path'e
# koyar; modül yoksa import HATASI yükselir ⇒ tüketici "ÖLÇÜLEMEDİ" der (sessiz geçmez).
from utils.drift_imzasi import yorumsuz

# Kabuk biçimi: `python "${CLAUDE_PROJECT_DIR}/scripts/hook_shim.py" recall_inject`
_KABUK_AD = re.compile(r"hook_shim\.py[\"']?\s+([A-Za-z0-9_][\w-]*)")
SHIM_DISI_ONEK = "?"


def kanca_adi(kanca: dict) -> str:
    """Tek kanca girdisinin adı; shim dışı komut için `?<komut>`."""
    args = [str(a) for a in (kanca.get("args") or [])]
    for i, a in enumerate(args):
        if a.replace("\\", "/").endswith("hook_shim.py") and i + 1 < len(args):
            return args[i + 1]
    komut = str(kanca.get("command") or "")
    m = _KABUK_AD.search(komut)
    if m:
        return m.group(1)
    return SHIM_DISI_ONEK + " ".join([komut, *args]).strip()


def shim_kancasi_mi(ad: str) -> bool:
    return not ad.startswith(SHIM_DISI_ONEK)


def baglantilar(veri: dict) -> list[tuple[str, str, str]]:
    """-> [(olay, eşleyici, ad)] — sıra korunur, tekrar KORUNUR (çokluküme)."""
    out: list[tuple[str, str, str]] = []
    hooks = yorumsuz(veri).get("hooks") if isinstance(veri, dict) else None
    if not isinstance(hooks, dict):
        return out
    for olay, bloklar in hooks.items():
        if not isinstance(bloklar, list):
            continue
        for blok in bloklar:
            if not isinstance(blok, dict):
                continue
            eslik = str(blok.get("matcher") or "")
            for kanca in blok.get("hooks") or []:
                if isinstance(kanca, dict):
                    out.append((olay, eslik, kanca_adi(kanca)))
    return out


def hepsi_kapali(veri: dict) -> bool:
    """`disableAllHooks: true` — kablolama ne olursa olsun HİÇBİR kanca koşmaz."""
    return isinstance(veri, dict) and veri.get("disableAllHooks") is True


def kiyas(proje: dict, sablon: dict) -> dict:
    """Ad düzeyi kıyas.

    -> {"eksik": [(olay, eşleyici, ad)]   şablonda var, projede (olay, ad) HİÇ yok
        "eslesik_farki": [((olay, ş_eşleyici, ad), p_eşleyici)]  aynı olay+ad, başka eşleyici
        "ek": [(olay, eşleyici, ad)]      yalnız projede (BİLGİ)
        "sablon_sayisi": int, "sablon_kanca": [ad]}
    Çokluküme farkıdır; aynı (olay, ad) çiftinin şablonda olmayan eşleyicili proje bağlantısı
    "eşleyici farklı" diye eşlenir (yeniden adlandırılmış/genişletilmiş eşleyici olabilir —
    otomatik karar VERİLMEZ), eşi bulunmayan şablon bağlantısı EKSİK'tir.
    """
    s, p = Counter(baglantilar(sablon)), Counter(baglantilar(proje))
    eksik_ham = list((s - p).elements())
    ek_ham = list((p - s).elements())
    eksik: list[tuple[str, str, str]] = []
    farkli: list[tuple[tuple[str, str, str], str]] = []
    for b in eksik_ham:
        es = next((e for e in ek_ham if e[0] == b[0] and e[2] == b[2]), None)
        if es is None:
            eksik.append(b)
        else:
            ek_ham.remove(es)
            farkli.append((b, es[1]))
    sablon_adlar: list[str] = []
    for _o, _m, ad in baglantilar(sablon):
        if ad not in sablon_adlar:
            sablon_adlar.append(ad)
    return {"eksik": eksik, "eslesik_farki": farkli, "ek": ek_ham,
            "sablon_sayisi": sum(s.values()), "sablon_kanca": sablon_adlar}


def eksikleri_ekle(proje: dict, sablon: dict) -> tuple[dict, list[tuple[str, str, str]]]:
    """Projeye YALNIZ eksik şablon bağlantılarını ekler -> (yeni veri, eklenenler).

    Girdi DEĞİŞTİRİLMEZ (derin kopya). Eklenen kanca aynı olay + aynı eşleyicili ilk proje
    bloğuna eklenir; yoksa şablon bloğunun kopyası (yorum alanıyla, yalnız eksik kancalarla)
    olayın SONUNA eklenir. "Eşleyici farklı" bağlantılar EKLENMEZ (kıyas onları EKSİK
    saymaz; karar kullanıcınındır). `hooks` bir sözlük değilse ValueError (sessiz ezme yok).
    """
    yeni = copy.deepcopy(proje)
    hooks = yeni.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("projede `hooks` bir nesne değil — ekleme yapılmadı")
    hedef = Counter(kiyas(proje, sablon)["eksik"])
    eklenen: list[tuple[str, str, str]] = []
    olaylar = yorumsuz(sablon).get("hooks") or {}        # yorum OLAY anahtarı değildir
    for olay, bloklar in (sablon.get("hooks") or {}).items():
        if olay not in olaylar or not isinstance(bloklar, list):
            continue
        for blok in bloklar:
            if not isinstance(blok, dict):
                continue
            eslik = str(blok.get("matcher") or "")
            for kanca in blok.get("hooks") or []:
                if not isinstance(kanca, dict):
                    continue
                b = (olay, eslik, kanca_adi(kanca))
                if hedef[b] <= 0:
                    continue
                hedef[b] -= 1
                p_bloklar = hooks.setdefault(olay, [])
                if not isinstance(p_bloklar, list):
                    raise ValueError(f"projede hooks.{olay} bir liste değil — ekleme yapılmadı")
                hedef_blok = next((x for x in p_bloklar if isinstance(x, dict)
                                   and str(x.get("matcher") or "") == eslik
                                   and isinstance(x.get("hooks"), list)), None)
                if hedef_blok is None:
                    hedef_blok = {k: copy.deepcopy(v) for k, v in blok.items() if k != "hooks"}
                    hedef_blok["hooks"] = []
                    p_bloklar.append(hedef_blok)
                hedef_blok["hooks"].append(copy.deepcopy(kanca))
                eklenen.append(b)
    return yeni, eklenen


def bicim(b: tuple[str, str, str]) -> str:
    olay, eslik, ad = b
    return f"{ad} ({olay}" + (f" [{eslik}]" if eslik else "") + ")"
