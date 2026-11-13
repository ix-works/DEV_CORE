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
    """`A|B|C` → {A, B, C}; boş ya da `*` → None (= HER araç).

    ⛔ Dizge bütün olarak KIRPILMAZ (P9, 2026-11-13): Claude Code eşleyiciyi kırpmadan okur
    (2.1.323: settings şeması `matcher:o().optional()`, `r8` `!n||n==="*"` tam eşitlik) ⇒ `" "`
    "her araç" DEĞİLDİR; `s8` olaylarında (PreToolUse dahil) boş listedir, kanca HİÇ koşmaz. Eskiden `" "` → None
    ⇒ ① KAPSANAN, 4h PASS (sessiz)."""
    e = eslik or ""
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


# Claude Code eşleyici okuması (2.1.323 ikilisinden ölçüldü 2026-11-13, `Owt`/`r8`/`s8`): `""`/`*`
# = her araç (tam eşitlik, kırpma YOK) · `Owt(eşleyici, s8.has(olay))`: olay `s8` kümesindeyse
# `[A-Za-z0-9_|, -]` taşıyan eşleyici TAM AD listesidir (`|`/`,` ile bölünür, öğe kırpılır, boş öğe
# atılır), değilse yalnız `[A-Za-z0-9_|]` (`|` ile). Liste DEĞİLSE → JS RegExp, ÇAPASIZ `test` (alt
# dizgi araması), araç adı VE eski adlarıyla denenir. Bir eşleyici olaya göre TEK okuma alır — liste
# ya da regex; ikisi birden değil. Liste öğesi eski adla yazılmışsa kanonik ada çevrilir (`Task`
# bloğu `Agent` aracında koşar).
_LISTE_DAR = re.compile(r"[A-Za-z0-9_|]+")
_LISTE_GENIS = re.compile(r"[A-Za-z0-9_|, -]+")
# İkilideki `var s8=new Set([...])` OLDUĞU GİBİ (21 olay; 2.1.323). Yalnız araç olayları değildir —
# SessionStart · Notification · ConfigChange · InstructionsLoaded · PreCompact da içindedir.
# Başka sürümde küme değişebilir (ÖLÇÜLMEDİ).
_GENIS_LISTE_OLAYLARI = frozenset({
    "PreToolUse", "PostToolUse", "PostToolUseFailure", "PermissionRequest", "PermissionDenied",
    "UserPromptExpansion", "SessionStart", "SessionEnd", "Setup", "PreCompact", "PostCompact",
    "PreModelSwitch", "PostModelSwitch", "Notification", "SubagentStart", "SubagentStop",
    "Elicitation", "ElicitationResult", "ConfigChange", "InstructionsLoaded", "DirectoryAdded"})
# Çapalı, alternatifleri yalnız literal ad olan desen: `^ad$` · `^(a|b)$` · `^(?:a|b)$`. Claude
# Code'da regex'tir ama yalnız adı TAM bu dizgelerden biri olan araçta tutar ⇒ ad listesine
# indirgenir (F2, 2026-11-13). `^a|b$` (öncelik: `(^a)|(b$)`) bu biçime UYMAZ, regex kalır.
_AD = r"[A-Za-z0-9_-]+"
_CAPALI_LITERAL = re.compile(rf"\^(?:({_AD})|\((?:\?:)?({_AD}(?:\|{_AD})*)\))\$")
_ESKI_AD = {"Task": "Agent", "KillShell": "TaskStop", "KillBash": "TaskStop",
            "ListPeers": "ListAgents", "Brief": "SendUserMessage",
            "ListMcpResources": "ListMcpResourcesTool", "ReadMcpResource": "ReadMcpResourceTool",
            "ReadMcpResourceDir": "ReadMcpResourceDirTool"}


def _kanonik(ad: str) -> str:
    return _ESKI_AD.get(ad, ad)


def _ad_ailesi(ad: str) -> set[str]:
    """Kanonik ad + ona giden eski adlar (regex Claude Code'da hepsiyle denenir)."""
    k = _kanonik(ad)
    return {ad, k, *[e for e, y in _ESKI_AD.items() if y == k]}


def _eslik_yorumlari(eslik: str, olay: str) -> list[tuple[str, object]] | None:
    """None = her araç. Aksi hâlde eşleyicinin Claude Code'daki TEK okuması, tek öğeli liste
    olarak: [("liste", frozenset kanonik ad)] ya da [("regex", desen)].

    Okuma OLAYA bağlıdır (F1, 2026-11-13): `,` / boşluk / `-` taşıyan düz eşleyici `s8`
    olaylarında (`_GENIS_LISTE_OLAYLARI`) YALNIZ liste, diğer olaylarda YALNIZ regex. Eskiden iki
    okumayı birden alıyordu; regex okuması regex şablonla hep "kesişir" verdiği için ayrık çiftler
    (`Edit, Write` ↔ `Bash|PowerShell|mcp__sap-adt__.*` · `mcp__other-srv__x` ↔ SWH) biçim farkına
    düşüyor, onarım eksik kancayı eklemiyordu (4d6cca6 EKSİK + onarım veriyordu).
    Çapalı literal desen (`^(a|b)$`, `_CAPALI_LITERAL`) ad listesine indirgenir (F2).
    Dizge KIRPILMAZ (P9): `" "` `s8` olayında boş listedir (hiçbir araç), başka olayda regex."""
    e = eslik or ""
    if e in ("", "*"):
        return None
    genis = olay in _GENIS_LISTE_OLAYLARI
    if (_LISTE_GENIS if genis else _LISTE_DAR).fullmatch(e):
        ayrac = r"[|,]" if genis else r"\|"
        return [("liste", frozenset(_kanonik(x.strip()) for x in re.split(ayrac, e) if x.strip()))]
    capali = _CAPALI_LITERAL.fullmatch(e)
    if capali:
        return [("liste", frozenset(_kanonik(x) for x in (capali.group(1) or capali.group(2)).split("|")))]
    return [("regex", e)]


def _yorum_kesisir(x: tuple[str, object], y: tuple[str, object]) -> bool:
    if x[0] == y[0] == "liste":
        return bool(x[1] & y[1])  # type: ignore[operator]
    if x[0] == y[0] == "regex":
        return True    # iki çapasız desen: ayrıklık KANITLANAMAZ → şüphe yönü
    desen, adlar = (x[1], y[1]) if x[0] == "regex" else (y[1], x[1])
    try:
        r = re.compile(str(desen))
    except re.error:
        return True    # Python derleyemedi; JS okuması bilinmiyor → şüphe yönü
    return any(r.search(n) for ad in adlar for n in _ad_ailesi(ad))  # type: ignore[union-attr]


def _kesisir(a: str, b: str, olay: str) -> bool:
    """`olay` altındaki iki eşleyici en az bir aracı ortak tutuyor mu — Claude Code'un okumasıyla
    (yukarıdaki not; okuma olaya bağlıdır, `_eslik_yorumlari`).

    ŞÜPHE YÖNÜ = KESİŞİR (F14, 2026-11-13). `kiyas` ③(a)'da "kesişmiyor" sonucu bağlantıyı EKSİK
    yapar ve `eksikleri_ekle` ikinci bir kopya ekler; kanca zaten koşuyorsa bu görünmez çift
    koşumdur. Bu yüzden "kesişmiyor" yalnız modellenen adlar için kanıtlanınca döner:
      · liste × liste → kanonik ad kümelerinin kesişimi (harf duyarlı, Claude Code gibi);
      · regex × liste → desen her adda ve `_ESKI_AD` eski adlarında `re.search` ile denenir;
      · regex × regex → KESİŞİR (çapasız iki alt dizgi deseninin ayrıklığı kanıtlanamaz) —
        çapalı literal desen (`^(a|b)$`) önce ad listesine indirgenir, bu dala girmez;
      · Python'un derleyemediği desen → KESİŞİR.
    Öğeler `|`'den LİTERAL bölünmez: `mcp__x__adt_(a|b)` tek bir regex'tir (parantez içi `|`).
    ⚠ regex × liste "kesin" DEĞİLDİR (Ö2): Claude Code bir aracı eşleyiciye ayrıca aile adlarıyla
    (`_8n` · `jlo` · `Z7t`), `L9` takma adlarıyla, `q0e`/`Rqr` alternatif adlarıyla ve `Eval→REPL`
    eşlemesiyle de dener; burada YALNIZ kanonik ad + `_ESKI_AD` eski adları denenir ⇒ "kesişmez"
    cevabı, modellenmeyen bir ad üzerinden Claude Code'da kesişebilir (o zaman onarım ikinci kopya
    ekler). Ters yönde: Claude Code eski adı koşullu dener (`P_n` + desende kelime sınırıyla geçmesi),
    burada koşulsuz ⇒ "kesişir" fazla olabilir (şüphe yönü). Şablonun araç adlarında bu adların
    hangisinin dolu olduğu ÖLÇÜLMEDİ.
    ÖLÇÜLMEDİ: JS ↔ Python regex sözdizimi farkı (JS'nin reddettiği desen Claude Code'da hiçbir
    araca eşleşmez; burada şüphe yönüne düşer)."""
    ya, yb = _eslik_yorumlari(a, olay), _eslik_yorumlari(b, olay)
    if ya is None or yb is None:
        return True
    return any(_yorum_kesisir(x, y) for x in ya for y in yb)


def _kapsama_notu(blok: str, eslikler: list[str], sablon: str, olay: str) -> str:
    """Biçim farkı komutunun önüne konan kapsama notu ("" = kapsıyor).

    `(KISMİ: …)` yalnız KANITLANDIĞINDA yazılır: tüm eşleyiciler (olaydaki okumayla) tam ad listesi
    (ya da `*`) ve kanonik ad birleşimi şablonunkini kapsamıyor. Regex eşleyici varsa kapsama
    ölçülemez ⇒ `(KAPSAMA ÖLÇÜLEMEDİ: …)` (F14: `.*` bloğu her aracı kapsar, "⊉" demek yanlış
    olurdu). Not yalnız WARN metnidir; ekleme kararını değiştirmez."""
    if _kapsar(eslikler, sablon):
        return ""
    yorumlar = [_eslik_yorumlari(x, olay) for x in [*eslikler, sablon]]
    if any(y is not None and (len(y) != 1 or y[0][0] != "liste") for y in yorumlar):
        return f"(KAPSAMA ÖLÇÜLEMEDİ: blok `{blok or '*'}` ↔ şablon, regex eşleyici) "
    if any(y is None for y in yorumlar[:-1]):
        return ""
    hedef = yorumlar[-1]
    birlesim: set = set()
    for y in yorumlar[:-1]:
        birlesim |= y[0][1]  # type: ignore[index,operator]
    if hedef is not None and hedef[0][1] <= birlesim:  # type: ignore[operator]
        return ""
    return f"(KISMİ: blok `{blok or '*'}` ⊉ şablon) "


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
                         (⊇) değilse komutun başında `(KISMİ: …)` notu durur (regex
                         eşleyicide `(KAPSAMA ÖLÇÜLEMEDİ: …)`). Kancanın o
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
          o bağlantıyı KARŞILAMAZ ⇒ EKSİK, onarım ekler. ŞÜPHE YÖNÜ (F14): kesişmezlik
          kanıtlanamıyorsa (regex × regex, derlenemeyen desen) KESİŞİR sayılır ⇒ biçim farkı
          (4h WARN), onarım EKLEMEZ. Kapsama notu `_kapsama_notu`: `(KISMİ: …)` yalnız tam ad
          listelerinde kanıtlanınca; regex eşleyicide `(KAPSAMA ÖLÇÜLEMEDİ: …)`.
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
               if e not in p_esl and _kesisir(e, b[1], b[0])]
        if ham:
            e, komut = ham[0]
            komut = _kapsama_notu(e, p_esl + [x for x, _k in ham], b[1], b[0]) + komut
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
