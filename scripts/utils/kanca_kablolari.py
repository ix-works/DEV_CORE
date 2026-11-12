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
import shlex
from collections import Counter

# `_comment*` eleme kuralının TEK evi D7 ortak modülüdür (Q212; d7_drift_imzasi V16 kopya
# tanımı yasaklar). Çağıranlar (ix_doctor · team_setup · parity_probe) `scripts/`i sys.path'e
# koyar; modül yoksa import HATASI yükselir ⇒ tüketici "ÖLÇÜLEMEDİ" der (sessiz geçmez).
from utils.drift_imzasi import yorumsuz

# Kabuk biçimi: `python "${CLAUDE_PROJECT_DIR}/scripts/hook_shim.py" recall_inject`
# (ad tırnaklı da olabilir: `… hook_shim.py" "recall_inject"`). Ad = shim'den SONRAKİ İLK
# argüman — `hook_shim.py` da `sys.argv[1]`i kanca adı sayar (bayrak ayrıştırmaz); bu yüzden
# `hook_shim.py --x ad` biçiminin adı `--x`tir (shim onu arar, bulamaz → 4i "çekirdekte YOK").
_SHIM = re.compile(r"hook_shim\.py", re.I)
_TIRNAK = "\"'"
SHIM_DISI_ONEK = "?"


def _tokenler(metin: str) -> list[str]:
    try:
        parca = shlex.split(metin, posix=True)
    except ValueError:                                   # dengesiz tırnak: kaba bölme
        parca = metin.split()
    return [t.strip(_TIRNAK) for t in parca if t.strip(_TIRNAK)]


def kanca_adi(kanca: dict) -> str:
    """Tek kanca girdisinin adı; shim dışı komut için `?<komut>`."""
    args = [str(a) for a in (kanca.get("args") or [])]
    for i, a in enumerate(args):
        if a.strip(_TIRNAK).replace("\\", "/").lower().endswith("hook_shim.py") and i + 1 < len(args):
            ad = args[i + 1].strip(_TIRNAK)
            if ad:
                return ad
    komut = str(kanca.get("command") or "")
    m = _SHIM.search(komut)
    if m:
        # Shim yolunu kapatan tırnak (`…hook_shim.py" ad`) kalanın başında kalır → at.
        kalan = _tokenler(komut[m.end():].lstrip(_TIRNAK))
        if kalan:
            return kalan[0]
    return SHIM_DISI_ONEK + " ".join([komut, *args]).strip()


def shim_kancasi_mi(ad: str) -> bool:
    return not ad.startswith(SHIM_DISI_ONEK)


def _ham_iceren(proje: dict, olay: str, ad: str) -> str | None:
    """Emniyet ağı (Ö1, 2026-11-12): `olay` altında shim'e giden ve ham token'larından biri
    `ad` olan bir kanca komutu var mı (ayrıştırıcının TANIMADIĞI biçim) → komut metni.

    NEDEN: ad okunamayan bir biçim (`?…` ya da yanlış ad) "eksik" sayılırsa `eksikleri_ekle`
    aynı kancayı İKİNCİ KEZ ekler (ölçüldü: tırnaklı kabuk biçiminde 2 canlı recall_inject).
    Bu ağ, ayrıştırıcı hangi biçimi kaçırırsa kaçırsın çift eklemeyi imkânsız kılar."""
    bloklar = (yorumsuz(proje).get("hooks") or {}).get(olay) if isinstance(proje, dict) else None
    for blok in bloklar if isinstance(bloklar, list) else []:
        for kanca in (blok.get("hooks") or []) if isinstance(blok, dict) else []:
            if not isinstance(kanca, dict) or kanca_adi(kanca) == ad:
                continue        # adı TANINAN kanca eşleyici mantığına aittir (kapsama/fark)
            ham = " ".join([str(kanca.get("command") or ""),
                            *[str(a) for a in (kanca.get("args") or [])]])
            if _SHIM.search(ham) and ad in _tokenler(ham.replace("\\", "/")):
                return ham.strip()
    return None


def _eslik_kumesi(eslik: str) -> frozenset | None:
    """`A|B|C` → {A, B, C}; boş ya da `*` → None (= HER araç)."""
    e = (eslik or "").strip()
    if e in ("", "*"):
        return None
    return frozenset(x.strip() for x in e.split("|") if x.strip())


def _kapsar(proje_eslikleri: list[str], eslik: str) -> bool:
    """Projedeki eşleyicilerin BİRLEŞİMİ şablon eşleyicisini ⊇ kapsıyor mu (Ö2).

    Öğeler LİTERAL kıyaslanır (`mcp__x__.*` yalnız kendisine eşittir — regex çözümlemesi
    YAPILMAZ ⇒ şüphede "kapsamıyor" der, otomatik ekleme yerine eşleyici-farkı WARN'ı çıkar)."""
    hedef = _eslik_kumesi(eslik)
    birlesim: set = set()
    for pe in proje_eslikleri:
        k = _eslik_kumesi(pe)
        if k is None:
            return True
        birlesim |= k
    return hedef is not None and hedef <= birlesim


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


def kapali_belirsiz(veri: dict):
    """`disableAllHooks` VAR ama bool DEĞİL (ör. `"true"` dizgesi) → değer; yoksa None.

    Claude Code'un bool dışı değeri nasıl yorumladığı ÖLÇÜLMEDİ (kapatabilir, yok sayabilir ya
    da ayar dosyasını şema hatasıyla reddedebilir) ⇒ çağıran bunu PASS saymaz, WARN basar."""
    if not isinstance(veri, dict) or "disableAllHooks" not in veri:
        return None
    d = veri.get("disableAllHooks")
    return None if isinstance(d, bool) else d


def kiyas(proje: dict, sablon: dict) -> dict:
    """Ad düzeyi kıyas.

    -> {"eksik": [(olay, eşleyici, ad)]   şablonda var, projede (olay, ad) HİÇ yok
        "eslesik_farki": [((olay, ş_eşleyici, ad), p_eşleyici)]  aynı olay+ad, başka eşleyici
        "kapsanan": [(olay, ş_eşleyici, ad)]  projede aynı kanca, eşleyici BİRLEŞİMİ ⊇ şablonunki
        "bicim_farki": [((olay, ş_eşleyici, ad), komut)]  ad ayrıştırılamadı ama ham komutta VAR
        "ek": [(olay, eşleyici, ad)]      yalnız projede (BİLGİ)
        "sablon_sayisi": int, "sablon_kanca": [ad]}
    Çokluküme farkıdır. Birebir eşi olmayan şablon bağlantısı sırayla: ① projede aynı (olay,
    ad) eşleyicilerinin birleşimi şablon eşleyicisini kapsıyorsa KAPSANAN (Ö2 — birleşik
    `Bash|…|Edit|…` bloğu; yeniden eklemek kancayı İKİ KEZ koşturur) ② aynı (olay, ad) başka
    eşleyiciyle varsa "eşleyici farklı" (genişletilmiş/daraltılmış olabilir — otomatik karar
    VERİLMEZ) ③ ham komutta ad geçiyorsa BİÇİM FARKI (Ö1 emniyet ağı — çift ekleme yok)
    ④ hiçbiri değilse EKSİK. Yalnız ④ `eksikleri_ekle`'nin girdisidir.
    """
    s, p = Counter(baglantilar(sablon)), Counter(baglantilar(proje))
    p_liste = baglantilar(proje)
    eksik_ham = list((s - p).elements())
    ek_ham = list((p - s).elements())
    eksik: list[tuple[str, str, str]] = []
    farkli: list[tuple[tuple[str, str, str], str]] = []
    kapsanan: list[tuple[str, str, str]] = []
    bicim_farki: list[tuple[tuple[str, str, str], str]] = []
    for b in eksik_ham:
        p_esl = [pm for po, pm, pa in p_liste if po == b[0] and pa == b[2]]
        if p_esl and _kapsar(p_esl, b[1]):
            kapsanan.append(b)
            continue
        es = next((e for e in ek_ham if e[0] == b[0] and e[2] == b[2]), None)
        if es is not None:
            ek_ham.remove(es)
            farkli.append((b, es[1]))
            continue
        ham = _ham_iceren(proje, b[0], b[2])
        if ham is not None:
            bicim_farki.append((b, ham))
            continue
        eksik.append(b)
    # Kapsamaya katkı veren proje bağlantısı "proje eki" DEĞİLDİR (şablon kancasının ta kendisi).
    for b in kapsanan:
        hedef = _eslik_kumesi(b[1])
        for e in [e for e in ek_ham if e[0] == b[0] and e[2] == b[2]]:
            k = _eslik_kumesi(e[1])
            if k is None or hedef is None or k & hedef:
                ek_ham.remove(e)
    sablon_adlar: list[str] = []
    for _o, _m, ad in baglantilar(sablon):
        if ad not in sablon_adlar:
            sablon_adlar.append(ad)
    return {"eksik": eksik, "eslesik_farki": farkli, "kapsanan": kapsanan,
            "bicim_farki": bicim_farki, "ek": ek_ham,
            "sablon_sayisi": sum(s.values()), "sablon_kanca": sablon_adlar}


def eksikleri_ekle(proje: dict, sablon: dict) -> tuple[dict, list[tuple[str, str, str]]]:
    """Projeye YALNIZ eksik şablon bağlantılarını ekler -> (yeni veri, eklenenler).

    Girdi DEĞİŞTİRİLMEZ (derin kopya). Eklenen kanca aynı olay + aynı eşleyicili ilk proje
    bloğuna eklenir; yoksa şablon bloğunun kopyası (yorum alanıyla, yalnız eksik kancalarla)
    olayın SONUNA eklenir. "Eşleyici farklı", "kapsanan" ve "biçim farkı" bağlantılar
    EKLENMEZ (kıyas onları EKSİK saymaz — ilki kullanıcı kararı, son ikisi kanca ZATEN
    kablolu: eklemek çift koşum olurdu). `hooks` bir sözlük değilse ValueError (sessiz ezme yok).
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
