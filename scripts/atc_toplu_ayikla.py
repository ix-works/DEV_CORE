#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""atc_toplu_ayikla.py — ATC TOPLU AYIKLAMA: çok hedef topla · kümele · CSV · önce/sonra kıyası.

SALT-OKUR teşhis aracı (gate DEĞİL; SAP'ye yazmaz). Q371① (2026-10-12).

  topla       --paket <P> … / --obje <TIP:AD> … → her hedefte ATC (run_atc_check.atc_bulgulari)
              → JSON rapor (+ --csv). Hedef başına KAPSAM satırı basılır.
  kume        --girdi <rapor.json> [--csv]  → kaydedilmiş raporu yeniden kümeler (SAP'siz).
  karsilastir --once <a.json> --sonra <b.json> [--csv] → çözülen / kalan / yeni (parmak izine göre).

TASARIM KARARLARI (her biri ölçülmüş bir tuzağın karşılığı):
  · KÜME ANAHTARI = (checkId, mesaj ŞEKLİ). ADT `checkId` bir GUID'dir; metin alt-dizgesi arayan
    sınıflandırıcılar (dış örneklerdeki desen) GUID'de hiçbir şey bulamaz ve her şeyi "elle karar"
    kovasına düşürür. Mesaj şekli = sayılar `#`, tırnaklı tanımlayıcılar `<>` (aynı kuralın farklı
    değişken adıyla verdiği bulgular tek kümede).
  · PARMAK İZİ SATIR NUMARASI İÇERMEZ = sha1(birim + checkId + sayısı-maskelenmiş mesaj
    [+ üye: konumdaki `name=` (metot), VARSA]). Satır no'lu parmak izi, kodun üstüne satır
    eklenince HER bulguyu "çözüldü + yeni" gösterir (sahte delta). Aynı birimde aynı bulgu
    birden çok kez geçebilir ⇒ kıyas ÇOKLU-KÜMEDİR (sayım). Üye girmezse aynı sınıfın
    METOT_A'sında çözülüp METOT_C'sinde doğan bulgu "değişmedi" görünür (bug-gate 2026-10-12).
    `karsilastir` izleri JSON'dan OKUMAZ, konum + checkId + mesajdan YENİDEN hesaplar
    (eski sürüm raporu yeni sürümle kıyaslanabilsin).
  · OBJE = bulgunun KENDİ konumundan (location URI) türetilir, ATC'ye verilen hedeften DEĞİL:
    "nested DB read" gibi bulgular SELECT'i içeren sınıfa yazılır, döngüyü içerene değil.
  · "Incorrect Pretty Print state" birim başına YALNIZ İLK farkı bildirir ⇒ düzeltme sonrası aynı
    birimde başka satıra kayar. Satırsız parmak izi bunu "kalan" sayar (doğru: birim hâlâ kirli).
    ⚠ SINIR: konum `name=` (üye) taşıyorsa ve ilk fark BAŞKA metoda kayarsa "çözülen + yeni"
    görünür — kıyas bunu ayrıca `uye_kaymasi` olarak sayar ve basar (Pretty Print konumunun
    `name=` taşıyıp taşımadığı canlıda ÖLÇÜLMEDİ; checkId'ye göre özel kural KONMADI).
  · KIYASLANABİLİRLİK: iki raporun hedef kümesi / variant / tavan / muaf politikası farklıysa
    ya da bir hedef koşamadı · kesik · worklist ayrıştırılamadı ise "KIYAS EKSIK" + çıkış 1.
  · TAVAN: ADT run isteği `maximumVerdicts` taşır (lib varsayılanı 100). Bu araç tavanı AÇIK
    verir (varsayılan 5000) ve dönen bulgu sayısı tavana EŞİTSE "KESİLMİŞ OLABİLİR" basar,
    JSON'a işaretler ve çıkış kodunu 4 yapar — kesik sonuç "temiz/az" diye okunmasın.
  · ZAMAN AŞIMI: ATC `runs` çağrısı SENKRONDUR ve paket ölçeğinde lib varsayılanını
    (`ADT_TIMEOUT_DEFAULT`=60 sn) aşar (ölçüldü 2026-10-12, bir tüketici paketinde ReadTimeout).
    `topla` bu yüzden `--zaman-asimi` (varsayılan 900 sn) ile ortam değişkenini İSTEMCİ
    KURULMADAN ÖNCE ayarlar; dışarıdan verilmiş bir değer EZİLMEZ.
  · CSV: UTF-8 BOM'lu (Excel TR), ayraç `;`, satır sonu AÇIKÇA `\\n` (platforma bırakılmaz).

KAPSAM BEYANI (her koşumda basılır): muaf (exempted) bulgular DAHİL DEĞİL (lib
`includeExemptedFindings=false`); yalnız verilen hedefler; ATC varyantı tek.

ÇIKIŞ: 0 tamam · 1 en az bir hedef KOŞAMADI (hata raporda) · 2 kullanım/girdi hatası ·
       4 en az bir hedefte sonuç KESİLMİŞ OLABİLİR ya da worklist yanıtı ayrıştırılamadı
       (ilk worklist okundu — "0 bulgu" sahte-temiz olabilir).
       karsilastir: 0 kıyas tam · 1 KIYAS EKSIK (güvenilmez hedef ya da koşul farkı).

Kullanım:
  python scripts/atc_toplu_ayikla.py topla --paket ZSD001 --cwd <PROJE_KOKU> --json a.json --csv a.csv
  python scripts/atc_toplu_ayikla.py kume --girdi a.json
  python scripts/atc_toplu_ayikla.py karsilastir --once a.json --sonra b.json --csv delta.csv
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter, OrderedDict
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

if sys.platform == "win32":
    for _a in (sys.stdout, sys.stderr):
        try:
            _a.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

SURUM = "atc_toplu_ayikla/2"   # 2: parmak izine üye (name=), fallback çıkış 4, kıyaslanabilirlik
VARSAYILAN_TAVAN = 5000
VARSAYILAN_ZAMAN_ASIMI = 900   # sn — ADT_TIMEOUT_DEFAULT (lib 60 sn paket ATC'sine yetmez)
ONCELIK_AD = {"1": "P1", "2": "P2", "3": "P3"}
CSV_SUTUNLAR = ["oncelik", "checkId", "mesaj", "obje_tipi", "obje_adi", "birim", "uye", "satir",
                "kume_no", "parmak_izi", "hedef"]

_SATIR_RE = re.compile(r"(?:^|[#;&])start=(\d+)")
# Canlı konumdaki üye (metot) adı: `#type=CLAS%2FOM;name=<METOT>;start=n` — bug-gate 2026-10-12:
# atılınca aynı sınıfın METOT_A'sında çözülüp METOT_C'sinde doğan bulgu "değişmedi" görünüyordu.
_UYE_AD_RE = re.compile(r"(?:^|[#;&])name=([^;&#]+)")
_SAYI_RE = re.compile(r"\d+")
_TIRNAK_RE = re.compile(r"'[^']*'|\"[^\"]*\"|`[^`]*`")
# `SINIF=>METOT` / `SINIF->METOT` — canlı mesajda ölçüldü (2026-10-12): bir ATC mesajı
# "... at Method <SINIF>=><METOT> line 103" biçiminde konum TAŞIR; maskelenmezse aynı kural
# her metotta ayrı küme olur.
_UYE_RE = re.compile(r"[A-Za-z0-9_/~]+\s*(?:=>|->)\s*[A-Za-z0-9_/~]+")
_BOSLUK_RE = re.compile(r"\s+")


# ── saf mantık (SAP'siz, fixture'la ölçülür) ─────────────────────────────────
def konum_coz(location: str) -> dict:
    """ATC `location` URI'sini (birim, obje tipi/adı, satır) parçalarına ayırır.

    `/sap/bc/adt/oo/classes/zcl_x/includes/testclasses#start=27,0`
      → birim `/sap/bc/adt/oo/classes/zcl_x/includes/testclasses`, tip `classes`,
        ad `ZCL_X`, satır 27. Satır YALNIZ bilgi sütunudur — parmak izine girmez.
    Canlıda ölçülen biçim (2026-10-12): `…/source/main#type=CLAS%2FOM;name=<METOT>;start=140`
    (sütunsuz, `;` ayraçlı) — `start=` her iki biçimde de okunur; `name=` varsa `uye` olur
    (yoksa boş dize — üyesiz konumda bulgu BİRİM düzeyinde kimliklenir).
    """
    loc = location or ""
    yol, _, frag = loc.partition("#")
    yol = yol.rstrip("/")
    m = _SATIR_RE.search(frag)
    satir = int(m.group(1)) if m else None
    u = _UYE_AD_RE.search(frag)
    uye = unquote(u.group(1)).upper() if u else ""
    obje_yolu = re.split(r"/(?:source|includes)(?:/|$)", yol, maxsplit=1)[0]
    parca = [p for p in obje_yolu.split("/") if p]
    ad = unquote(parca[-1]).upper() if parca else ""
    tip = parca[-2] if len(parca) >= 2 else ""
    return {"birim": yol.lower(), "uye": uye, "obje_tipi": tip, "obje_adi": ad, "satir": satir}


def mesaj_sekli(mesaj: str) -> str:
    """Küme anahtarının mesaj ayağı: tırnaklı tanımlayıcı / `SINIF=>METOT` → `<>`, sayı → `#`."""
    m = _TIRNAK_RE.sub("<>", mesaj or "")
    m = _UYE_RE.sub("<>", m)
    m = _SAYI_RE.sub("#", m)
    return _BOSLUK_RE.sub(" ", m).strip()


def parmak_izi(birim: str, check_id: str, mesaj: str, uye: str = "") -> str:
    """Satır numarası İÇERMEYEN kimlik. Mesajdaki sayılar da maskelenir (ör. "satır 42").
    `uye` (konumdaki `name=`, ör. metot) VARSA kimliğe girer: aynı birimde başka metoda geçen
    bulgu "çözülen + yeni" görünür. Üyesiz konumda bulgu birim düzeyinde kalır (eski davranış)."""
    norm = _BOSLUK_RE.sub(" ", _SAYI_RE.sub("#", mesaj or "")).strip()
    parca = [birim or "", check_id or "", norm] + ([uye] if uye else [])
    return hashlib.sha1("\x1f".join(parca).encode("utf-8")).hexdigest()[:16]


def izler(b: dict) -> tuple[str, str]:
    """(parmak izi, ÜYESİZ birim izi) — kayıtlı JSON'daki izlere GÜVENİLMEZ, konum + checkId +
    mesajdan YENİDEN hesaplanır (eski sürümün raporu yeni sürümle kıyaslanınca izler tutarlı kalsın)."""
    if "konum" not in b:          # elle/eksik kayıt: kayıtlı ize düş
        return b.get("parmak_izi", ""), b.get("parmak_izi", "")
    k = konum_coz(b.get("konum", ""))
    cid, msg = b.get("checkId", "") or "", b.get("mesaj", "") or ""
    return parmak_izi(k["birim"], cid, msg, k["uye"]), parmak_izi(k["birim"], cid, msg)


def zenginlestir(ham: dict, hedef: str) -> dict:
    k = konum_coz(ham.get("location", ""))
    cid = ham.get("checkId", "") or ""
    msg = ham.get("message", "") or ""
    return {
        "hedef": hedef,
        "oncelik": str(ham.get("priority", "") or ""),
        "checkId": cid,
        "mesaj": msg,
        "konum": ham.get("location", "") or "",
        **k,
        "mesaj_sekli": mesaj_sekli(msg),
        "parmak_izi": parmak_izi(k["birim"], cid, msg, k["uye"]),
    }


def kume_anahtari(b: dict) -> tuple:
    """Küme kimliği: checkId (GUID) + mesaj ŞEKLİ. Metin tek başına DEĞİL (GUID'siz birleşme)."""
    return (b["checkId"], b["mesaj_sekli"])


def kumele(bulgular: list[dict]) -> list[dict]:
    """(checkId, mesaj şekli) kümeleri: en yüksek öncelik önce, sonra adet (azalan)."""
    gruplar: "OrderedDict[tuple, dict]" = OrderedDict()
    for b in bulgular:
        a = kume_anahtari(b)
        g = gruplar.setdefault(a, {"checkId": a[0], "mesaj_sekli": a[1], "adet": 0,
                                    "oncelik": b["oncelik"] or "?", "objeler": set(),
                                    "ornek_mesaj": b["mesaj"], "_anahtar": a})
        g["adet"] += 1
        g["objeler"].add(b["obje_adi"])
        if b["oncelik"] and (g["oncelik"] == "?" or b["oncelik"] < g["oncelik"]):
            g["oncelik"] = b["oncelik"]
    out = sorted(gruplar.values(), key=lambda g: (g["oncelik"], -g["adet"], g["checkId"], g["mesaj_sekli"]))
    for i, g in enumerate(out, 1):
        g["kume_no"] = i
        g["objeler"] = sorted(g["objeler"])
        g.pop("_anahtar")
    return out


def kume_no_ata(bulgular: list[dict], kumeler: list[dict]) -> None:
    harita = {}
    for b in bulgular:
        for g in kumeler:
            if g["checkId"] == b["checkId"] and g["mesaj_sekli"] == b["mesaj_sekli"]:
                harita[kume_anahtari(b)] = g["kume_no"]
                break
    for b in bulgular:
        b["kume_no"] = harita.get(kume_anahtari(b))


def karsilastir(once: list[dict], sonra: list[dict]) -> dict:
    """Parmak izi ÇOKLU-KÜMESİ kıyası: çözülen = önce−sonra · yeni = sonra−önce · kalan = kesişim.

    ÜYE KAYMASI (ayrıca sayılır, çözülen/yeni'den DÜŞÜLMEZ): bir çözülen ile bir yeni aynı
    birim + checkId + mesajı taşıyıp yalnız üyede (`name=` metot) ayrışıyorsa. Gerçek "A'da
    düzeltildi, C'de doğdu" da budur, birim başına TEK bulgu veren kontroller (Pretty Print)
    de — ikisini ayırmak kontrolün anlamını ister; araç ayırmaz, sayıyı basar."""
    ia = [izler(x) for x in once]
    ib = [izler(x) for x in sonra]
    a, b = Counter(p for p, _ in ia), Counter(p for p, _ in ib)
    ornek, birim_izi = {}, {}
    for x, (p, bi) in list(zip(once, ia)) + list(zip(sonra, ib)):
        ornek.setdefault(p, x)
        birim_izi.setdefault(p, bi)

    def liste(c: Counter) -> list[dict]:
        return [{**ornek[k], "adet": n} for k, n in sorted(c.items()) if n > 0]

    coz, yeni = a - b, b - a
    cb, yb = Counter(), Counter()
    for k, n in coz.items():
        cb[birim_izi[k]] += n
    for k, n in yeni.items():
        yb[birim_izi[k]] += n
    return {"cozulen": liste(coz), "yeni": liste(yeni), "kalan": liste(a & b),
            "sayim": {"once": sum(a.values()), "sonra": sum(b.values()),
                      "cozulen": sum(coz.values()), "yeni": sum(yeni.values()),
                      "kalan": sum((a & b).values()), "uye_kaymasi": sum((cb & yb).values())}}


def kiyaslanabilirlik(once: dict, sonra: dict) -> list[str]:
    """İki rapor AYNI ölçüm koşullarında mı? Farklıysa 'çözülen/yeni' koşul farkını ölçer, kodu değil."""
    sorun = []
    hk = lambda r: sorted({(h.get("tip"), h.get("hedef")) for h in r.get("hedefler", [])})
    if hk(once) != hk(sonra):
        sorun.append("hedef kumesi farkli: %s <> %s" % (hk(once), hk(sonra)))
    for alan in ("variant", "tavan", "muaf_bulgular"):
        if once.get(alan) != sonra.get(alan):
            sorun.append("%s farkli: %r <> %r" % (alan, once.get(alan), sonra.get(alan)))
    return sorun


def guvenilmez_hedefler(rapor: dict) -> list[dict]:
    """Sonucu 'tam' sayılamayan hedefler: koşamadı · kesilmiş olabilir · worklist ayrıştırılamadı."""
    return [h for h in rapor["hedefler"]
            if h.get("hata") or h.get("kesilmis_olabilir") or h.get("worklist_parse_fallback")]


def csv_yaz(satirlar: list[dict], yol: Path, ek_sutun: list[str] | None = None) -> None:
    sutun = CSV_SUTUNLAR + (ek_sutun or [])
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        w.writerow(sutun)
        for s in satirlar:
            w.writerow(["" if s.get(c) is None else s.get(c) for c in sutun])


# ── toplama (SAP) ────────────────────────────────────────────────────────────
def _varsayilan_kosucu(ad: str, tip: str, varyant: str, tavan: int) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    # run_atc_check Windows'ta import anında sys.stdout'u YENİ bir sarmalayıcıyla değiştirir;
    # eskisinde tamponda kalan satırlar (ör. ZAMAN-ASIMI) kaybolur — ölçüldü 2026-10-12.
    sys.stdout.flush()
    sys.stderr.flush()
    from run_atc_check import atc_bulgulari  # tek yol: deseni yeniden türetme
    return atc_bulgulari(ad, tip, variant=varyant, max_verdicts=tavan)


def topla(hedefler: list[tuple[str, str]], varyant: str, tavan: int, kosucu=None) -> dict:
    kosucu = kosucu or _varsayilan_kosucu
    rapor = {"_surum": SURUM, "_zaman": datetime.now().isoformat(timespec="seconds"),
             "variant": varyant, "tavan": tavan, "muaf_bulgular": "DAHIL DEGIL",
             "hedefler": [], "bulgular": []}
    for tip, ad in hedefler:
        h = {"hedef": ad, "tip": tip, "bulgu_sayisi": None, "kesilmis_olabilir": None,
             "worklist_parse_fallback": False, "hata": None}
        try:
            sonuc = kosucu(ad, tip, varyant, tavan)
            if not isinstance(sonuc, dict) or not isinstance(sonuc.get("findings"), list):
                raise ValueError("ATC sonucu beklenen bicimde degil: %r" % (type(sonuc).__name__,))
            ham = sonuc["findings"]
            h["bulgu_sayisi"] = len(ham)
            h["kesilmis_olabilir"] = len(ham) >= tavan
            h["worklist_parse_fallback"] = bool(sonuc.get("worklist_parse_fallback"))
            rapor["bulgular"].extend(zenginlestir(x, ad) for x in ham)
        except Exception as e:  # hedef başına: biri düşerse diğerleri yine ölçülür, hata RAPORDA
            h["hata"] = "%s: %s" % (type(e).__name__, str(e)[:300])
            govde = getattr(e, "response_text", None)
            if govde:
                h["hata"] += " | govde: " + re.sub(r"\s+", " ", str(govde))[:300]
            if "timed out" in str(e).lower() or "timeout" in type(e).__name__.lower():
                h["hata"] += " — IPUCU: --zaman-asimi buyut (ATC runs senkron; sonuc 'temiz' DEGIL)"
        rapor["hedefler"].append(h)
    return rapor


def rapor_cikis_kodu(rapor: dict) -> int:
    if any(h.get("hata") for h in rapor["hedefler"]):
        return 1
    # worklist ayrıştırılamadıysa İLK worklist okunmuştur — yanlışsa "0 bulgu" sahte-temizdir
    # (sap_adt_lib run_atc_check yorumu). Kesik sonuçla aynı sınıf: sonuç TAM değil.
    if any(h.get("kesilmis_olabilir") or h.get("worklist_parse_fallback") for h in rapor["hedefler"]):
        return 4
    return 0


# ── yazdırma ─────────────────────────────────────────────────────────────────
def kapsam_bas(rapor: dict) -> None:
    print("KAPSAM: variant=%s · tavan(maximumVerdicts)=%s · muaf bulgular %s · yalniz verilen hedefler"
          % (rapor.get("variant"), rapor.get("tavan"), rapor.get("muaf_bulgular", "?")))
    for h in rapor["hedefler"]:
        if h.get("hata"):
            print("  [OLCULEMEDI] %s %s — %s" % (h["tip"], h["hedef"], h["hata"]))
            continue
        ek = []
        if h.get("kesilmis_olabilir"):
            ek.append("⚠ KESILMIS OLABILIR (bulgu sayisi tavana esit; --tavan buyut)")
        if h.get("worklist_parse_fallback"):
            ek.append("⚠ worklist yaniti ayristirilamadi — ilk worklist okundu, 'temiz' sanma")
        print("  [OLCULDU] %s %s — %s bulgu %s" % (h["tip"], h["hedef"], h["bulgu_sayisi"], " · ".join(ek)))


def kumeleri_bas(kumeler: list[dict], ust: int = 40) -> None:
    print("KUMELER (checkId + mesaj sekli): %d" % len(kumeler))
    for g in kumeler[:ust]:
        print("  #%-3d %-3s x%-4d %s | %s | obje=%d"
              % (g["kume_no"], ONCELIK_AD.get(g["oncelik"], "P" + str(g["oncelik"])), g["adet"],
                 g["checkId"][:36], g["mesaj_sekli"][:70], len(g["objeler"])))
    if len(kumeler) > ust:
        print("  … %d kume daha (CSV/JSON'da tam liste)" % (len(kumeler) - ust))


def _rapor_oku(yol: str) -> dict:
    try:
        r = json.loads(Path(yol).read_text(encoding="utf-8"))
    except Exception as e:
        print("[KULLANIM] rapor okunamadi: %s (%s)" % (yol, e))
        sys.exit(2)
    if not isinstance(r, dict) or not isinstance(r.get("bulgular"), list) or "hedefler" not in r:
        print("[KULLANIM] %s bu aracin raporu degil (bulgular/hedefler yok)" % yol)
        sys.exit(2)
    return r


def _json_yaz(rapor: dict, yol: Path) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(rapor, ensure_ascii=False, indent=1) + "\n")


def _hedef_ayristir(a) -> list[tuple[str, str]]:
    out = [("package", p.upper()) for p in (a.paket or [])]
    for o in a.obje or []:
        tip, sep, ad = o.partition(":")
        if not sep or not tip or not ad:
            print("[KULLANIM] --obje TIP:AD biciminde olmali (ornek class:ZCL_ZSD001_X): %r" % o)
            sys.exit(2)
        out.append((tip, ad.upper()))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="ATC toplu ayiklama (salt-okur)")
    alt = ap.add_subparsers(dest="komut", required=True)
    t = alt.add_parser("topla")
    t.add_argument("--paket", action="append")
    t.add_argument("--obje", action="append", help="TIP:AD (tip: class/interface/program/…)")
    t.add_argument("--variant", default="DEFAULT")
    t.add_argument("--tavan", type=int, default=VARSAYILAN_TAVAN)
    t.add_argument("--zaman-asimi", type=int, default=VARSAYILAN_ZAMAN_ASIMI,
                   help="ADT istek zaman asimi sn (ADT_TIMEOUT_DEFAULT; ortamda varsa o kullanilir)")
    t.add_argument("--cwd", help=".conn_adt'nin bulundugu proje koku")
    t.add_argument("--json")
    t.add_argument("--csv")
    k = alt.add_parser("kume")
    k.add_argument("--girdi", required=True)
    k.add_argument("--csv")
    c = alt.add_parser("karsilastir")
    c.add_argument("--once", required=True)
    c.add_argument("--sonra", required=True)
    c.add_argument("--csv")
    a = ap.parse_args(argv)

    if a.komut == "topla":
        hedefler = _hedef_ayristir(a)
        if not hedefler:
            print("[KULLANIM] en az bir --paket ya da --obje ver")
            return 2
        if a.tavan < 1:
            print("[KULLANIM] --tavan >= 1 olmali")
            return 2
        if "ADT_TIMEOUT_DEFAULT" not in os.environ:
            os.environ["ADT_TIMEOUT_DEFAULT"] = str(a.zaman_asimi)
        print("ZAMAN-ASIMI: ADT_TIMEOUT_DEFAULT=%s sn" % os.environ["ADT_TIMEOUT_DEFAULT"])
        if a.cwd:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from sap_adt_lib import set_explicit_working_dir
            set_explicit_working_dir(a.cwd)
        rapor = topla(hedefler, a.variant, a.tavan)
    else:
        rapor = _rapor_oku(a.girdi if a.komut == "kume" else a.once)

    if a.komut in ("topla", "kume"):
        kumeler = kumele(rapor["bulgular"])
        kume_no_ata(rapor["bulgular"], kumeler)
        rapor["kumeler"] = kumeler
        kapsam_bas(rapor)
        kumeleri_bas(kumeler)
        if a.komut == "topla":
            hedef = Path(a.json) if a.json else Path(tempfile.gettempdir()) / (
                "atc-toplu-%s.json" % datetime.now().strftime("%Y%m%d-%H%M%S"))
            _json_yaz(rapor, hedef)
            print("JSON: %s" % hedef)
        if a.csv:
            csv_yaz(rapor["bulgular"], Path(a.csv))
            print("CSV : %s (%d satir)" % (a.csv, len(rapor["bulgular"])))
        rc = rapor_cikis_kodu(rapor)
        print("SONUC: %d bulgu · %d kume · cikis=%d" % (len(rapor["bulgular"]), len(kumeler), rc))
        return rc

    sonra = _rapor_oku(a.sonra)
    d = karsilastir(rapor["bulgular"], sonra["bulgular"])
    print("ONCE:"); kapsam_bas(rapor)
    print("SONRA:"); kapsam_bas(sonra)
    s = d["sayim"]
    print("KARSILASTIRMA (coklu-kume; parmak izi = birim + uye[name=, varsa] + checkId + sayisi maskeli "
          "mesaj, SATIR NO YOK): once=%d sonra=%d · cozulen=%d · kalan=%d · yeni=%d · uye_kaymasi=%d"
          % (s["once"], s["sonra"], s["cozulen"], s["kalan"], s["yeni"], s["uye_kaymasi"]))
    print("  SINIR: uyesiz konumda ayni birimdeki ayni bulgu yer degistirse 'kalan' sayilir; "
          "uye_kaymasi>0 ise bir kismi ayni bulgunun baska metoda gecmesidir (birim basina TEK bulgu "
          "veren kontrollerde — or. Pretty Print — 'kalan' oku)")
    for etiket in ("yeni", "cozulen"):
        for x in d[etiket][:20]:
            print("  [%s] x%d %s%s %s | %s" % (etiket.upper(), x["adet"], x["obje_adi"],
                                              ("=>" + x["uye"]) if x.get("uye") else "", x["checkId"][:36],
                                              x["mesaj"][:70]))
    eksik = [h for r in (rapor, sonra) for h in guvenilmez_hedefler(r)]
    kosul = kiyaslanabilirlik(rapor, sonra)
    if eksik:
        print("⚠ KIYAS EKSIK: %d hedef olculemedi / kesilmis olabilir / worklist ayristirilamadi — "
              "'cozulen' sayisi GUVENILMEZ" % len(eksik))
    for k in kosul:
        print("⚠ KIYAS EKSIK: olcum kosullari farkli — %s ('cozulen/yeni' kod degil kosul farkini olcer)" % k)
    eksik = eksik or kosul
    if a.csv:
        satir = [{**x, "durum": e} for e in ("cozulen", "kalan", "yeni") for x in d[e]]
        csv_yaz(satir, Path(a.csv), ek_sutun=["durum", "adet"])
        print("CSV : %s (%d satir)" % (a.csv, len(satir)))
    return 1 if eksik else 0


if __name__ == "__main__":
    raise SystemExit(main())
