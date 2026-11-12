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
# `hook_shim.py --x ad` biçiminin adı `--x`tir (shim onu arar, bulamaz → 4i "çekirdekte YOK")
# ve `ad` 4h'de EKSİK sayılır, onarım onu ekler — o kanca gerçekten koşmuyor (F7).
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


def _ham_iceren(proje: dict, olay: str, ad: str) -> list[tuple[str, str]]:
    """Emniyet ağı (Ö1, 2026-11-12): `olay` altında shim'e giden, adı AYRIŞTIRILAMAYAN (`?…`)
    ve ham token'larından biri `ad` olan kanca komutları → [(BLOK EŞLEYİCİSİ, komut metni)].

    ⛔ Eşleyici bağlantının parçasıdır (F10, 2026-11-13): ağ bulduğu komutu, içinde durduğu
    bloğun eşleyicisiyle birlikte döndürür; hangi şablon bağlantısını karşıladığına `kiyas`
    eşleyiciye göre karar verir. Eskiden yalnız komut dönüyordu ⇒ `Edit|Write|MultiEdit`
    bloğundaki zincir çağrısı, `Bash` bloğunda gerçekten EKSİK olan aynı kancayı "biçim farkı"
    sayıp maskeliyordu (ölçüldü: 8e94e17 ve 8ab2594'te `eksik []`, onarım eklemiyordu).

    NEDEN: ad okunamayan bir biçim "eksik" sayılırsa `eksikleri_ekle` aynı kancayı İKİNCİ KEZ
    ekleyebilir (ölçüldü: tırnaklı kabuk biçiminde 2 canlı recall_inject — o biçim artık
    `kanca_adi`'nde ayrıştırılıyor; ağ, ayrıştırıcının kaçırdığı biçimler için durur).
    ⛔ Adı AYRIŞTIRILMIŞ shim kancasına BAKMAZ (F7, 2026-11-12): shim yalnız `sys.argv[1]`'i
    koşturur ⇒ `hook_shim.py pull_before_edit infra_write_guard` infra_write_guard'ı HİÇ
    koşturmaz, `hook_shim.py --flag recall_inject` recall_inject'i HİÇ koşturmaz. Ağ bunlara da
    bakınca gerçek EKSİK "biçim farkı" sayılıyor, onarım onu eklemiyor ve 4h "tamamı projede"
    diyordu (ölçüldü: abd227b'de FAIL + onarım vardı, 8e94e17'de WARN + PASS).
    Adı ayrıştırılmış kancada yalnız ZİNCİRDEKİ İKİNCİ+ shim çağrısı sayılır
    (`… hook_shim.py a && … hook_shim.py b` → b gerçekten koşar; `kanca_adi` yalnız a'yı okur
    ⇒ b'yi EKSİK saymak onu çift koşturur)."""
    out: list[tuple[str, str]] = []
    bloklar = (yorumsuz(proje).get("hooks") or {}).get(olay) if isinstance(proje, dict) else None
    for blok in bloklar if isinstance(bloklar, list) else []:
        if not isinstance(blok, dict):
            continue
        eslik = str(blok.get("matcher") or "")
        for kanca in blok.get("hooks") or []:
            if not isinstance(kanca, dict):
                continue
            ham = " ".join([str(kanca.get("command") or ""),
                            *[str(a) for a in (kanca.get("args") or [])]])
            if not _SHIM.search(ham):
                continue
            tk = _tokenler(ham.replace("\\", "/"))
            if shim_kancasi_mi(kanca_adi(kanca)):
                # shim yalnız argv[1]'i koşturur: aynı çağrının sonraki token'ları koşmaz.
                if ad in [tk[i + 1] for i in range(len(tk) - 1)
                          if tk[i].lower().endswith("hook_shim.py")][1:]:
                    out.append((eslik, ham.strip()))
            elif ad in tk:
                out.append((eslik, ham.strip()))
    return out


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


def _kesisir(a: str, b: str) -> bool:
    """İki eşleyici en az bir aracı ortak tutuyor mu (boş/`*` = her araç; öğeler LİTERAL)."""
    ka, kb = _eslik_kumesi(a), _eslik_kumesi(b)
    return ka is None or kb is None or bool(ka & kb)


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
        "bicim_farki": [((olay, ş_eşleyici, ad), komut)]  ad, şablon eşleyicisiyle KESİŞEN bir
                         blokta ya adı ayrıştırılamayan (`?…`) shim komutunun ham token'larında
                         ya da kabuk zincirindeki 2.+ shim çağrısında geçiyor. Kesişim kapsama
                         (⊇) değilse komutun başında `(KISMİ: …)` notu durur. Kancanın o
                         eşleyicide KOŞUP KOŞMADIĞI ÖLÇÜLMEDİ (zincir çağrısı koşar; `?…`
                         biçimi bilinmez; KISMİ'de şablonun kesişmeyen kısmı kablosuzdur)
        "ek": [(olay, eşleyici, ad)]      yalnız projede (BİLGİ)
        "sablon_sayisi": int, "sablon_kanca": [ad]}
    Çokluküme farkıdır. Birebir eşi olmayan şablon bağlantısı sırayla: ① projede aynı (olay,
    ad) eşleyicilerinin birleşimi şablon eşleyicisini kapsıyorsa KAPSANAN (Ö2 — birleşik
    `Bash|…|Edit|…` bloğu; yeniden eklemek kancayı İKİ KEZ koşturur) ② aynı (olay, ad) başka
    eşleyiciyle varsa "eşleyici farklı" (genişletilmiş/daraltılmış olabilir — otomatik karar
    VERİLMEZ) ③ BİÇİM FARKI (Ö1 emniyet ağı + F7 zincir istisnası — çift ekleme yok): ad,
    adı ayrıştırılamayan (`?…`) bir shim komutunda ya da kabuk zincirindeki 2.+ shim
    çağrısında geçiyorsa. Adı ayrıştırılmış çağrının argv[2+] token'ları ağa GİRMEZ (shim
    yalnız argv[1]'i koşturur). ④ hiçbiri değilse EKSİK. Yalnız ④ `eksikleri_ekle`'nin
    girdisidir.
    ⛔ ③'ün EŞLEYİCİ KURALI (F10, 2026-11-13): ağın bulduğu komut, içinde durduğu BLOĞUN
    eşleyicisiyle bir bağlantıdır ve yalnız şu iki koşulda sayılır:
      (a) blok eşleyicisi şablon eşleyicisiyle KESİŞİYOR (`_kesisir`; ⊇ ise tam, değilse
          KISMİ). Kesişmeyen blok (`Edit|…` bloğundaki zincir ↔ şablonun `Bash` bağlantısı)
          o bağlantıyı KARŞILAMAZ ⇒ EKSİK, onarım ekler.
      (b) aynı blok eşleyicisi bu adın AYRIŞTIRILMIŞ bağlantıları arasında YOK. O eşleyici
          ①/②'de zaten tartıldı. `pre_tool_guard && pre_tool_guard` gibi aynı-ad zinciri yeni
          bir eşleyici getirmez, eksiği maskeleyemez (8e94e17 davranışı).
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
        ham = [(e, k) for e, k in _ham_iceren(proje, b[0], b[2])
               if e not in p_esl and _kesisir(e, b[1])]
        if ham:
            e, komut = ham[0]
            if not _kapsar(p_esl + [x for x, _k in ham], b[1]):
                komut = f"(KISMİ: blok `{e or '*'}` ⊉ şablon) {komut}"
            bicim_farki.append((b, komut))
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
    EKLENMEZ, çünkü kıyas onları EKSİK saymaz:
      · eşleyici farklı → kullanıcı kararı;
      · kapsanan → kanca ZATEN kablolu, eklemek çift koşum olur;
      · biçim farkı → kanca o eşleyiciyle KESİŞEN bir blokta tanınmayan biçimde ya da kabuk
        zincirinin 2.+ çağrısında duruyor. Koşup koşmadığı ÖLÇÜLMEDİ (zincir çağrısı koşar,
        `?…` biçimi bilinmez). Eklemek çift koşum OLABİLİRDİ; karar kullanıcının (4h WARN).
        KISMİ kesişimde şablonun kesişmeyen kısmı kablosuz kalır. Bu kısım da EKLENMEZ,
        çünkü eklenecek blok kesişen araçlarda kancayı ikinci kez koştururdu.
    Eşleyicisi şablonunkiyle KESİŞMEYEN bloktaki zincir/`?…` çağrısı o bağlantıyı karşılamaz
    ⇒ EKSİK sayılır ve eklenir (F10). `hooks` bir sözlük değilse ValueError (sessiz ezme yok).
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
