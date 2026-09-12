#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_recall_index.py — U1 JIT-recall için hafif ders-indeksi üretici (radar 2026-08-01).

NE ÜRETİR: <proje>/.tmp/recall-index.json — her kayıt: {id, kaynak, baslik, oz, anahtar[]}.
KAYNAKLAR (pilot kapsamı, bilinçli dar):
  1. Auto-memory indeks satırları — `MEMORY.md` + aynı dizindeki `_indeks-*.md` HUB'ları.
     İki satır biçimi: `- [Başlık](dosya.md) — öz` ve `- [[slug]] — öz` (slug → `<slug>.md`).
     Özsüz satır → hedef dosyanın frontmatter `description:`ı. Hiçbir indekste geçmeyen
     (YETİM) dosya da `description:`ı varsa girer; sayısı CLI/status'ta `yetim=N` görünür.
  2. core/playbook/lessons-learned.md PATTERN başlıkları (+ ilk açıklama cümlesi)
  3. core/playbook/howto-*.md H1 + tetik/ilk düzyazı

⭐ NEDEN HUB (Q287, 2026-09-12, ölçüldü): memory bütçe diyetiyle kayıtların çoğu `MEMORY.md`'den
`_indeks-*.md` hub'larına taşındı; üreteç yalnız `MEMORY.md`'yi okuyordu → diskteki **294** ders
dosyasının yalnız **107**'si indekse girebiliyordu, üstelik **5 hub dosyasının KENDİSİ** ders
kaydı sayılıyordu (112 = 107 + 5). Biçim değişti, okuyucu güncellenmedi — sessiz körleşme.
Hub'lar ve `MEMORY.md` KAYIT DEĞİLDİR (içerikleri başka dosyalara işaretçidir).

TAZELEME: `recall_inject` hook'u her uzun prompt'ta `kaynak_mtime()` ile bayatlığı ölçer ve
bayatsa `uret()`'i AYNI SÜREÇTE çağırır (ayrıntı: o dosyanın docstring'i). Bayatlık kaynak
listesinin TEK tanımı bu dosyadaki `kaynak_mtime()`'dır — hook ikinci bir liste tutmaz.

TASARIM İLKELERİ:
  · LLM YOK, embedding YOK — saf sözcük-eşleşme indeksi (Türkçe katlama: İ→i, ı→i,
    ş→s, ğ→g, ü→u, ö→o, ç→c; küçük harf). BM25 yerine ağırlıklı token-kesişimi
    (başlık-token'ı ×3, öz-token'ı ×1) — pilot için yeterli, bakımı sıfır.
  · İndeks İÇERİK taşımaz (tam metin değil) — yalnız başlık+tek-cümle öz+işaretçi.
    Recall-hook bunlardan top-K SATIR enjekte eder; ajan gerekirse kaynağı okur
    (progressive-disclosure; claude-mem "index, not full details" deseni).
  · Üretilmiş artefakt: .tmp/ altında, git'e girmez. Yazım ATOMİKTİR (geçici dosya +
    `os.replace`) — eşzamanlı okuyucu yarım JSON görmez.

Kullanım:  python core/scripts/build_recall_index.py   (proje kökünden; `--help` üretmez)
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
import time
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

_TR = str.maketrans("İIıŞşĞğÜüÖöÇç", "iiissgguuoocc")
_STOP = {"ve", "ile", "icin", "için", "bir", "bu", "da", "de", "the", "for", "and",
         "yok", "var", "olan", "her", "gate", "check"}


def katla(s: str) -> str:
    return s.translate(_TR).lower()


def tokenle(s: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9_çğıöşü]{3,}", katla(s)) if t not in _STOP]


_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+\.md)\)")   # geriye uyum; iç kullanım `_HER_LINK`

# Q287: hub satır biçimi `- [[slug]] — öz`. Kaçış deseni `[ \t]*` (ASLA `\s*`: satır sonunu
# yutar → komşu satırın metni `oz` olur; C6 dersinin wiki ikizi).
_WIKI_OZLU = re.compile(r"^- \[\[([^\]|#]+)\]\][ \t]*[—-][ \t]*(.+)$", re.M)
# Satır içindeki TÜM linkler, GÖRÜNÜŞ SIRASIYLA: wiki `[[slug]]` ya da `[Başlık](dosya.md)`.
# Başlıkta TEK düzey iç köşeli parantez serbest (`[Push "[OK]" sahte](x.md)`): eski `[^\]]+`
# ilk `]`de durup linki HİÇ görmüyordu (ölçüldü: bir hub'da 1 ders bu yüzden "yetim" çıktı).
_HER_LINK = re.compile(r"\[\[([^\]|#]+)\]\]|\[((?:[^\[\]]|\[[^\]]*\])+)\]\(([^)]+\.md)\)")
_HUB_DESENI = "_indeks-*.md"
_TIP_ONEKI = re.compile(r"^(?:feedback|project|reference|user)[_-]")


def _oz_kes(oz: str) -> str:
    """Özü satırdaki SONRAKİ linkte keser. `- [A](a.md) — öz A · [B](b.md) — öz B` satırında
    A'nın özü `öz A`dır; eskiden `öz A · [B](b.md) — öz B` giriyordu → B'nin sözcükleri A'ya
    puan veriyordu (C6 satır-atlamalı kirlenmenin SATIR-İÇİ ikizi; ölçüldü: hub'larda 2 kayıt).
    Kesim sonrası öz boş kalırsa çağıran satırı özsüz sayar (description geri-düşüşü)."""
    m = _HER_LINK.search(oz)
    if m:
        oz = oz[:m.start()]
    return oz.strip().rstrip("·—-|,;").strip()


def _hub_mi(dosya: str) -> bool:
    """MEMORY.md ve `_indeks-*.md` hub'ları İŞARETÇİDİR, ders kaydı değildir (Q287)."""
    ad = Path(dosya).name
    return ad == "MEMORY.md" or fnmatch.fnmatch(ad, _HUB_DESENI)


def _wiki_dosya(slug: str) -> str:
    slug = slug.strip()
    return slug if slug.endswith(".md") else slug + ".md"


def _slug_basligi(slug: str) -> str:
    """`[[feedback_x-y-z]]` → `x y z`. Wiki satırında köşeli başlık YOKTUR; satırın özü
    ×3 ağırlıklı başlık yapılsaydı (ort. ~100 karakter) eşik rastgele aşılırdı. Slug ise
    yazım sözleşmesiyle kısa ve anlamlı tutulan, zaten ASCII-katlanmış bir addır."""
    s = _wiki_dosya(slug)[:-3]
    return _TIP_ONEKI.sub("", s).replace("-", " ").replace("_", " ").strip()


def _satir_linkleri(satir: str) -> list[tuple[str, str]]:
    out = []
    for m in _HER_LINK.finditer(satir):
        if m.group(1) is not None:
            out.append((_slug_basligi(m.group(1)), _wiki_dosya(m.group(1))))
        else:
            out.append((m.group(2), m.group(3)))
    return out


def indeks_hublari(memory_md: Path) -> list[Path]:
    """`MEMORY.md` ile aynı dizindeki `_indeks-*.md` hub'ları — indeks KAYNAĞI tanımının tek yeri.

    Dışa açık (Q289): `seed_memory._index_onar` "indekste var" kümesini buradan kurar; tanım
    kopyalanırsa iki okuyucu yeniden ayrışır (Q287'nin sınıfı). ⛔ Mutasyon çapası: aşağıdaki
    `hub_lar = sorted(...)` satırı `recall_index_ozetsiz --mutasyon-hub-yok` tarafından aranır."""
    hub_lar = sorted(p for p in memory_md.parent.glob(_HUB_DESENI) if p.is_file())
    return hub_lar


def metin_linkleri(metin: str) -> set[str]:
    """Metindeki TÜM memory linklerinin DOSYA ADLARI — iki biçim (`[[slug]]` · `[Başlık](x.md)`),
    liste-satırı şartı YOK (düzyazı satırı da sayılır). Tanım `_satir_linkleri`dir (Q289).

    ⚠ Bu bir "link var" kümesidir, KAYIT kümesi değil: builder'ın yetim geri-düşüşü (hiçbir
    indekste geçmeyen dosya) burada YOKTUR — çağıran indekste-var semantiğini buna bağlar."""
    return {Path(d.strip()).name for s in metin.splitlines() for _b, d in _satir_linkleri(s)}


def _kayit(dosya: str, baslik: str, oz: str) -> dict:
    return {"id": f"mem:{dosya}", "kaynak": f"memory/{dosya}",
            "baslik": baslik, "oz": oz[:160],
            "anahtar": tokenle(baslik) * 3 + tokenle(oz)}


def _fm_description(yol: Path) -> str:
    """Memory dosyasinin frontmatter `description:` alani.

    ⭐ NEDEN VAR (2026-08-21, olculdu): ureteç YALNIZ `- [Baslik](dosya) — ozet` seklindeki
    satirlari goruyordu. Canli MEMORY.md'de **146 liste satiri / 163 link** var, indekse giren **90**
    ⇒ **73 kayit JIT-RECALL'a HIC girmiyordu** ve bunu kimse gormuyordu (sessiz kayip;
    "0 kayit" ile "0 eslesme" ayni cikti). Ozet-cumlesi elle yazilan bir alandir ve
    unutulur; `description:` ise memory YAZIM SOZLESMESININ zorunlu alanidir (olculdu:
    214 dosyanin 213'unde var) ⇒ dogru geri-dusus kaynagi budur, 57 cumleyi elle yazmak
    degil.
    """
    try:
        t = yol.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    if not t.startswith("---"):
        return ""
    son = t.find("\n---", 3)
    if son < 0:
        return ""
    m = re.search(r"^description:\s*(.+)$", t[:son], re.M)
    if not m:
        return ""
    return m.group(1).strip().strip('"').strip("'")


def memory_kayitlari(memory_md: Path, sayac: dict | None = None) -> list[dict]:
    out = []
    if not memory_md.is_file():
        return out
    # Q287: KAYNAK = MEMORY.md + ayni dizindeki `_indeks-*.md` hub'lari. Uc gecis TUM kaynaklar
    # uzerinde (dosya bazinda degil) kosar => bir satirdaki ozet, BASKA bir kaynaktaki
    # description geri-dususunu her zaman yener; tekillestirmede MEMORY.md onceliklidir.
    hub_lar = indeks_hublari(memory_md)
    parcalar = [memory_md.read_text(encoding="utf-8", errors="replace")]
    for h in hub_lar:
        try:
            parcalar.append(h.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
    metin = "\n".join(parcalar)
    gorulen: set[str] = set()

    # (1) MEVCUT DAVRANIS — `anahtar` formulu (baslik x3 + oz) bilerek AYNEN korunur:
    #     bu tur skorlama davranisini DEGISTIRMEZ, KAPSAMI acar.
    #
    # ⚠ TEK DAVRANISSAL DUZELTME: `\s*` -> `[ \t]*`. `\s` SATIR SONUNU DA KAPSAR, bu yuzden
    # ozet-cumlesi OLMAYAN bir satir, `\s*`in `\n`i yutmasiyla BIR SONRAKI SATIRIN `-`
    # isaretini ayrac sanip o satirin METNINI kendi `oz`u yapiyordu (satir-atlamali
    # kirlenme). Bu, "47 kayit eksik" kusurunun IKINCI, daha sinsi yuzu: kayit VARDI ama
    # ozeti BASKA BIR DERSE aitti -> skorlama yanlis derse puan veriyordu.
    # Olculdu (canli MEMORY.md, 2026-08-21): eski desende 90 kaydin **42'si** komsu satirdan
    # kirlenmisti (lider bagimsiz olctu; kanonik sayi: infra-changelog). Bu kusuru KENDI fixture'i (P1/N1) yakaladi; korpus yazilmadan once
    # gorunmuyordu cunku eski korpusta ozetsiz satir HIC YOKTU.
    for m in re.finditer(r"^- \[([^\]]+)\]\(([^)]+)\)[ \t]*[—-][ \t]*(.+)$", metin, re.M):
        baslik, dosya, oz = m.group(1).strip(), m.group(2).strip(), _oz_kes(m.group(3))
        if not oz or dosya in gorulen or _hub_mi(dosya):
            continue
        gorulen.add(dosya)
        out.append(_kayit(dosya, baslik, oz))
    # (1b) Q287 — hub'larin wiki bicimi: `- [[slug]] — oz`.
    for m in _WIKI_OZLU.finditer(metin):
        dosya, oz = _wiki_dosya(m.group(1)), _oz_kes(m.group(2))
        if not oz or dosya in gorulen or _hub_mi(dosya):
            continue
        gorulen.add(dosya)
        out.append(_kayit(dosya, _slug_basligi(m.group(1)), oz))

    # (2) GERI DUSUS — ozet-cumlesi OLMAYAN indeks linkleri.
    #     ⚠ Kapsam BILEREK `^- [` deseninden GENIS: canli indekste en degerli dersler
    #     `- ⭐ [Baslik](dosya)` / `- ⛔ [...]` seklinde yaziliyor ve dar desen onlari
    #     GORMUYORDU (olculdu: 9 satirin 4'u ⭐/⛔ isaretli). Ayrica bir satirda BIRDEN
    #     COK link olabilir (gruplu referans satirlari) -> her link ayri kayit.
    #     Q287: LISTE-SATIRI SARTI da KALDIRILDI — hub'larda link DUZYAZI satirinda da duruyor
    #     (olculdu: bir hub'da 9 ders YALNIZ `Alt kayitlar: [[a]] · [[b]] ...` satirindan
    #     linkli; liste-sartiyla "yetim" sayiliyorlardi). C-MEM-01 de erisilebilirligi satir
    #     bicimine bakmadan sayar — iki okuyucu ayni "indekste mi" tanimini kullanmali.
    for satir in metin.splitlines():
        for baslik, dosya in _satir_linkleri(satir):
            baslik, dosya = baslik.strip(), dosya.strip()
            if dosya in gorulen or _hub_mi(dosya):
                continue
            gorulen.add(dosya)
            oz = _fm_description(memory_md.parent / dosya)
            if not oz:
                continue      # ne ozet ne description -> eskisi gibi kapsam disi (sessiz
                              # uydurma YOK; kaynak yoksa kayit da yok)
            baslik = re.sub(r"[*_`]", "", baslik)
            out.append(_kayit(dosya, baslik, oz))

    # (3) Q287 — YETIM: hicbir indekste gecmeyen ders dosyasi. Kaynak (description) GERCEK
    #     oldugu icin eklenir, ama sayisi GORUNUR kalir (`yetim=N`): erisilemezligi tespit
    #     etmek C-MEM-01'in (check_memory_index) isidir, recall onu GIZLEMEMELI.
    gorulen_ad = {Path(d).name for d in gorulen}
    yetim = 0
    for p in sorted(memory_md.parent.glob("*.md")):
        if p.name in gorulen_ad or _hub_mi(p.name):
            continue
        oz = _fm_description(p)
        if not oz:
            continue
        yetim += 1
        out.append(_kayit(p.name, _slug_basligi(p.name), oz))

    if sayac is not None:
        sayac["hub"] = len(hub_lar)
        sayac["yetim"] = yetim
    return out


def lessons_kayitlari(lessons: Path) -> list[dict]:
    out = []
    if not lessons.is_file():
        return out
    t = lessons.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r"^#{2,3}\s*(PATTERN\s*#\d+[^\n]*)\n+([^\n]*)", t, re.M):
        baslik = m.group(1).strip()
        oz = re.sub(r"[*_`>]", "", m.group(2)).strip()[:160]
        out.append({"id": f"pat:{baslik.split(':')[0].strip()}",
                    "kaynak": "core/playbook/lessons-learned.md",
                    "baslik": baslik[:120], "oz": oz,
                    "anahtar": tokenle(baslik) * 3 + tokenle(oz)})
    return out


_KOD_CITI = re.compile(r"^(?:```|~~~)")


def _ilk_duzyazi(metin: str, baslangic: int) -> str:
    """H1'den SONRAKI ilk anlamli duzyazi satiri (geri-dusus kaynagi).

    ⭐ NEDEN VAR (2026-08-22, olculdu): `howto_kayitlari` ozeti YALNIZ `**Tetik:**` /
    `**Ne:**` / `**Problem:**` kaliplarindan cikariyordu; kalip tutmazsa `oz` SESSIZCE
    bos kaliyordu. Canli indekste 13 `how:` kaydinin **11'i** bos `oz` ile giriyordu
    (204 kaydin TUM bos-`oz`'u bu daldaydi) -> `anahtar` vektoru yalnizca BASLIK
    token'lariyla besleniyor, `tokenle(oz)*2` katkisi SIFIR oluyordu. Yani kayit
    "vardi" ama skorlamaya baslik disinda hicbir sey katmiyordu (sessiz kayip;
    kardes dal `memory_kayitlari` geri-dususunu 2026-08-21'de zaten kazanmisti).

    ⛔ UYDURMA YOK: kaynak metinde anlamli duzyazi yoksa "" doner (cagiran eskisi gibi
    bos birakir). Baslik `oz` diye KOPYALANMAZ -- o, kaynagi olmayan bir ozet uretmek olurdu.
    Kardes desen: `lessons_kayitlari` de H2/H3'ten sonraki ilk satiri ayni mantikla alir.
    """
    kod = False
    for satir in metin[baslangic:].splitlines():
        s = satir.strip()
        if _KOD_CITI.match(s):
            kod = not kod                      # kod bloklari icerik degil
            continue
        if kod or not s:
            continue
        if s.startswith("#") or s.startswith("|"):
            continue                           # alt-baslik / tablo satiri
        if set(s) <= set("-=*_ "):
            continue                           # yatay cizgi (`---`, `***`)
        s = re.sub(r"^\s*[-*·>]+\s*", "", s)   # liste/alinti isareti
        s = re.sub(r"[*_`>]", "", s).strip()
        if len(s) >= 15:                       # tek kelimelik artik satirlari ele
            return s
    return ""


def howto_kayitlari(playbook: Path) -> list[dict]:
    """howto-*.md dosyalarindan H1 baslik + ilk anlamli satir (radar-adopt 2026-08-01 eki)."""
    out = []
    for f in sorted(playbook.glob("howto-*.md")):
        t = f.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^#\s+(.+)$", t, re.M)
        if not m:
            continue
        baslik = m.group(1).strip()[:120]
        m2 = re.search(r"^>?\s*\*\*Tetik:\*\*\s*(.+)$", t, re.M) or              re.search(r"^>?\s*\*\*(?:Ne|Problem[^:]*):\*\*\s*(.+)$", t, re.M)
        oz = (m2.group(1) if m2 else "")[:200]
        if not oz:
            # GERI DUSUS — kalip tutmadi. Kardes dal `memory_kayitlari` ayni sekilde
            # `description:`e duser; burada kaynak H1-sonrasi ilk duzyazidir.
            oz = _ilk_duzyazi(t, m.end())[:200]
        out.append({"id": f"how:{f.name}", "kaynak": f"core/playbook/{f.name}",
                    "baslik": baslik, "oz": oz,
                    "anahtar": tokenle(baslik) * 3 + tokenle(oz) * 2})
    return out


def memory_md_bul(proj: Path) -> Path | None:
    """Projenin MEMORY.md'si. ÖNCE deterministik slug'dan çözülür (TEK KAYNAK, KAYIT S4); ancak
    bulunamazsa eski "ada göre en taze eşleşme" sezgisi KORUNUR (recall fail-open'dır,
    indeks üretememek sessiz bir kayıptır). ⚠ Sezginin son çaresi "en taze HERHANGİ
    proje"dir → BAŞKA bir projenin hafızası bu projenin recall indeksine girebilir;
    deterministik yol o riski normal durumda tümden kaldırır."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from utils.claude_paths import auto_memory_dizini, claude_projects_dir
    kanonik = auto_memory_dizini(proj) / "MEMORY.md"
    if kanonik.is_file():
        return kanonik
    mem_dir = claude_projects_dir()
    if not mem_dir.is_dir():
        return None
    aday = sorted(mem_dir.glob("*/memory/MEMORY.md"),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    # proje adı geçen en taze eşleşme; yoksa en taze
    isim = katla(proj.name)
    return next((p for p in aday if isim in katla(str(p))), aday[0] if aday else None)


def indeks_yolu(proj: Path) -> Path:
    return proj / ".tmp" / "recall-index.json"


def kaynak_mtime(proj: Path, memory_md: Path | None = None) -> float:
    """Builder'ın okuduğu HER kaynağın en yeni mtime'ı — bayatlık ölçütünün TEK tanımı (Q287).

    Kapsam: memory DİZİNİ (dosya silme/ekleme dizin mtime'ını değiştirir) + memory `*.md`
    (hub'lar dahil) + `lessons-learned.md` + playbook dizini + `howto-*.md` + BU DOSYA (üreteç
    kodu değişirse indeks yeniden üretilmeli). Yalnız `stat` — içerik okunmaz.
    Ölçüm (üretim projesi ölçeği, 300 memory dosyası): medyan ~1,4 ms.
    """
    if memory_md is None:
        memory_md = memory_md_bul(proj)
    en = Path(__file__).stat().st_mtime
    dizinler: list[tuple[Path, str]] = []
    if memory_md is not None and memory_md.parent.is_dir():
        dizinler.append((memory_md.parent, "*.md"))
    pb = proj / "core" / "playbook"
    if pb.is_dir():
        dizinler.append((pb, "howto-*.md"))
        ll = pb / "lessons-learned.md"
        if ll.is_file():
            en = max(en, ll.stat().st_mtime)
    for d, desen in dizinler:
        en = max(en, d.stat().st_mtime)
        with os.scandir(d) as it:
            for e in it:
                if fnmatch.fnmatch(e.name, desen):
                    en = max(en, e.stat().st_mtime)
    return en


def uret(proj: Path) -> dict:
    """İndeksi ATOMİK üretir ve özet sayıları döndürür. ⛔ stdout'a YAZMAZ — hook bunu aynı
    süreçte çağırır; bir `print` hook'un JSON çıktısını bozar (Q287).

    İndeksin mtime'ı, okumaya BAŞLAMADAN önce ölçülen kaynak damgasına çekilir: üretim
    sırasında değişen bir kaynak damgadan yeni kalır ⇒ bir sonraki prompt'ta yeniden
    bayat görünür (değişiklik kaybolmaz). Saat kayması (geleceğe damgalı dosya) da sonsuz
    yeniden-üretim döngüsüne dönüşmez.
    """
    memory_md = memory_md_bul(proj)
    damga = kaynak_mtime(proj, memory_md)
    sayac: dict = {}
    kayitlar: list[dict] = []
    if memory_md:
        kayitlar += memory_kayitlari(memory_md, sayac)
    kayitlar += lessons_kayitlari(proj / "core" / "playbook" / "lessons-learned.md")
    kayitlar += howto_kayitlari(proj / "core" / "playbook")

    hedef = indeks_yolu(proj)
    hedef.parent.mkdir(parents=True, exist_ok=True)
    gecici = hedef.with_name(f"{hedef.name}.{os.getpid()}.tmp")
    try:
        gecici.write_text(json.dumps({"v": 1, "kayit": kayitlar}, ensure_ascii=False, indent=0),
                          encoding="utf-8")
        for deneme in range(5):
            try:
                os.replace(gecici, hedef)
                break
            except PermissionError:
                # Windows: hedef o an bir okuyucuda açıksa replace reddedilir; kısa bekle.
                if deneme == 4:
                    raise
                time.sleep(0.02)
        os.utime(hedef, (damga, damga))
    finally:
        try:
            if gecici.exists():
                gecici.unlink()
        except OSError:
            pass
    return {"hedef": str(hedef), "kayit": len(kayitlar),
            "memory": sum(1 for k in kayitlar if k["id"].startswith("mem:")),
            "pattern": sum(1 for k in kayitlar if k["id"].startswith("pat:")),
            "howto": sum(1 for k in kayitlar if k["id"].startswith("how:")),
            "hub": sayac.get("hub", 0), "yetim": sayac.get("yetim", 0)}


def main() -> int:
    # Q287: argüman okumayan üreteç `--help`te de İNDEKS ÜRETİYORDU (ölçüldü 2026-09-12).
    # argparse: `--help` → exit 0, bilinmeyen bayrak → exit 2; ikisinde de üretim YOK.
    argparse.ArgumentParser(
        description="JIT-recall indeksini <proje>/.tmp/recall-index.json'a üretir "
                    "(proje = CLAUDE_PROJECT_DIR ya da çalışma dizini).").parse_args()
    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    b = uret(proj)
    print(f"[OK] recall-index: {b['kayit']} kayıt "
          f"(memory={b['memory']}, pattern={b['pattern']}, howto={b['howto']}, "
          f"hub={b['hub']}, yetim={b['yetim']}) → {b['hedef']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
