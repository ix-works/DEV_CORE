#!/usr/bin/env python3
# ENFORCES: C-ITG-01, C-ITG-02, C-ITG-03, C-ITG-04  (ADR 0019 coverage binding)
"""check_itg_signoff.py — ITG S2 intake-artefaktı + mutabakat gate (ADR 0022, Faz-1).

S2 (kapsamlı) bir iş SAP-yazmasına geçmeden ÖNCE, intake-artefaktının üretildiğini VE
kullanıcı sign-off'unun alındığını deterministik doğrular. run_review task `itg_s2_signoff`
üzerinden çağrılır (artifact = intake-artefaktı .md yolu).

Kontroller (playbook/intake-triage.md S2 şeması):
  - MUTABAKAT satırında işaret [x]/[X] var mı (kullanıcı sign-off)?
  - Zorunlu alanlar dolu mu: KAPSAM, Etkilenen objeler, Prior-art, Kabul kriterleri.
  - Prior-art alanı boş bırakılamaz (bulundu:<ref> VEYA yok — aramayı mecbur kılar).

Bulgu varsa exit 1 (run_review BLOCKER → SAP-yazma YASAK). Temizse exit 0.
NOT (Faz-1): bu YARGI+deterministik-artefakt gate'idir; hangi işin S2 olduğunu ajan/lider
belirler (hook durum-tutmaz — ADR 0022). Faz-2 pre_tool_guard state-gate pilot-kanıtına bağlı.
"""
import argparse
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

# Zorunlu alan başlıkları (intake-artefaktı şeması; büyük/küçük harf duyarsız, esnek eşleşme)
#
# ⚠ BAŞLIK VARLIĞI ≠ ALAN DOLULUĞU (2026-08-01 bug-avı, V3). Bu liste yalnız başlığın
# GEÇTİĞİNİ arıyordu; `playbook/intake-triage.md` şablonu kopyalanıp hiçbir alanı
# doldurmadan `MUTABAKAT: [x]` işaretlenince gate `✓ intake-artefaktı TAM` diyor ve
# exit 0 dönüyordu. Ölçüldü: 8 satırlık boş şablon + `[x]` → PASS. Bu bir BLOCKER
# gate'idir (run_review `itg_s2_signoff` → SAP-yazma kapısı): "kapı var ama bakmıyor"
# hâli, kapı olmamasından TEHLİKELİDİR (koruma sanısı).
#
# Doğru teknik ZATEN AYNI DOSYADAYDI: `prior-art` için değerin dolu olduğunu arayan
# `_PRIOR_ART_DOLU` deseni. Kusur o desende değil, DİĞER ÜÇ ALANA UYGULANMAMASINDAYDI —
# tek dosyada iki farklı titizlik seviyesi. Aşağıda doluluk kontrolü alan-başına
# genelleştirildi (`_deger` + `_dolu_mu`), prior-art kendi ek kuralını korur.
#
# ⚠⚠ GEVŞETME (2026-08-20, kullanıcı onaylı) — YALNIZ **YAZIM BİÇİMİ**, doluluk DEĞİL.
# ÖLÇÜLEN FP: içeriği TAM ve canlı-doğrulanmış bir artefakt bu kapıdan **BLOCKER** aldı.
# İki kusur:
#   ① başlık `## 3. ETKİLENEN / İLGİLİ OBJELER — CANLI DOĞRULANDI` yazıyordu; desen
#      `etkilenen\s+obje` araya giren `/ İLGİLİ` yüzünden **eşleşmedi** ⇒ "alan eksik".
#   ② prior-art `- **Prior-art:** \`ref_docs/RESEARCH-…\`` biçimindeydi (değer **DOLU**)
#      ama kural literal `bulundu`/`yok` sözcüğünü şart koşuyordu ⇒ "alan boş/belirsiz".
# Maliyeti yüksekti: kapı BLOCKER, mesaj *"alan eksik"* diyordu ama alan **VARDI** ⇒
# okuyan kişi belgeyi yeniden yazmaya girişti (bir turda gerçekten değerlendirildi).
#
# ⛔ NE GEVŞEMEDİ: 2026-08-01'de eklenen **DEĞER DOLULUĞU** zinciri (`_deger` + `_dolu_mu`
# + `_YER_TUTUCULAR`) AYNEN duruyor. Boş şablon + `MUTABAKAT: [x]` bu kapıyı HÂLÂ GEÇEMEZ —
# korpus bunu pozitif kontrolle kanıtlar. Tolerans **başlık yazımına** dokunur,
# **varlık/doluluk denetimine** DEĞİL.
#
# Başlıkta araya kelime girebilir ( `/ İLGİLİ`, `VE`, `-` … ) ama satır/`:` sınırını AŞMAZ:
# sınırsız `.*` iki farklı alanın başlığını birbirine bağlar ve alan karışması üretirdi.
_ARA = r"[^\n:]{0,24}"
_ZORUNLU = [
    ("kapsam", re.compile(r"kapsam\s*:", re.I)),
    ("etkilenen objeler", re.compile(r"etkilenen" + _ARA + r"obje", re.I)),
    ("prior-art", re.compile(r"prior-?art", re.I)),
    ("kabul kriterleri", re.compile(r"kabul\s+kriter", re.I)),
]
# Alan DEĞERİNİ çeken desenler (başlık + `:` sonrası; satır sonuna dek).
# Değer bir sonraki madde/başlık/kod-çiti'ne kadar SONRAKİ SATIRLARDAN da toplanır —
# gerçek artefaktlarda çok satırlı yazım yaygın; tek-satır varsayımı FP üretirdi.
_ALAN_BASLIK = {
    "kapsam": re.compile(r"^.*?\bkapsam\s*:(?P<deger>.*)$", re.I),
    "etkilenen objeler": re.compile(r"^.*?etkilenen" + _ARA + r"obje[^:]*:(?P<deger>.*)$", re.I),
    "prior-art": re.compile(r"^.*?prior-?art\s*:(?P<deger>.*)$", re.I),
    "kabul kriterleri": re.compile(r"^.*?kabul\s+kriter[^:]*:(?P<deger>.*)$", re.I),
}
# ⚠ İKİNCİ BİÇİM — MARKDOWN BAŞLIĞI (`## 3. ETKİLENEN / İLGİLİ OBJELER`).
# Gerçek artefaktlar alanı `Alan: değer` satırı yerine BÖLÜM BAŞLIĞI olarak yazıyor;
# o satırda `:` YOKTUR ⇒ yukarıdaki desenler HİÇ eşleşmez, `_deger` boş döner ve alan
# "değeri boş" sanılır. Bu, ölçülen FP'nin İKİNCİ katmanıydı (yalnız `/ İLGİLİ` değil).
# Değer = başlıktan SONRAKİ blok, aynı ya da ÜST seviyeli bir sonraki başlığa kadar.
# ⛔ Başlık satırının KENDİSİ değere DAHİL EDİLMEZ: edilseydi boş bir bölüm bile
# "dolu" görünürdü — yani doluluk denetimi sessizce ölürdü.
_ALAN_MD_BASLIK = {
    "kapsam": re.compile(r"^(?P<d>#{1,6})\s+.*\bkapsam\b.*$", re.I),
    "etkilenen objeler": re.compile(r"^(?P<d>#{1,6})\s+.*etkilenen" + _ARA + r"obje.*$", re.I),
    "prior-art": re.compile(r"^(?P<d>#{1,6})\s+.*prior-?art.*$", re.I),
    "kabul kriterleri": re.compile(r"^(?P<d>#{1,6})\s+.*kabul\s+kriter.*$", re.I),
}
_MD_BASLIK = re.compile(r"^(#{1,6})\s")
# Şablonun KENDİ yer-tutucuları (intake-triage.md S2 şeması). Değer bunlardan biriyle
# birebir (normalize) aynıysa alan DOLDURULMAMIŞ sayılır — "şablonu kopyaladım" hâli.
_YER_TUTUCULAR = {
    "sd / rapor / s2 (gerekçe: ...)",
    "[obje → reuse/yeni/değişir → blast-radius]",
    "[obje -> reuse/yeni/degisir -> blast-radius]",
    "[bulundu: <ref> / yok]",
    '"<olay> olduğunda sistem <sonuç> yapmalı" / "<durum> ise ..."',
    "[konu → araştırma özeti (a/b/c eksen)]",
}
_MUTABAKAT_ISARETLI = re.compile(r"mutabakat.*\[[xX]\]|\[[xX]\].*mutabakat|sign-?off.*\[[xX]\]", re.I)
_MUTABAKAT_SATIR = re.compile(r"mutabakat|sign-?off", re.I)
# Prior-art DEĞERİ kabul edilebilir mi?
#
# ⚠⚠ GEVŞETME (2026-08-20, kullanıcı onaylı) — BİÇİM toleransı, DOLULUK değil.
# ESKİ: `prior-?art\s*:.*\b(bulundu|yok|none|found)\b` — literal sözcük ŞARTTI ve
# TÜM METİNDE aranıyordu. Ölçülen FP: `- **Prior-art:** \`ref_docs/RESEARCH-…\`` —
# değer DOLU ve gerçek bir referans, ama `bulundu` sözcüğü yok ⇒ **BLOCKER**.
# ⛔ `bulundu` bir SİHİRLİ SÖZCÜKTÜ: yazması bedava, hiçbir şey kanıtlamıyordu. Asıl
# kanıt DEĞERİN KENDİSİDİR. Kural artık şunu istiyor — ya (a) AÇIK OLUMSUZ ("yok"),
# ya (b) REFERANS İZİ (yol · dosya uzantısı · backtick · ADR/kayıt no · URL).
# ⇒ "Aramayı mecbur kılma" amacı KORUNUYOR: boş bırakılamaz, düzyazı bir laf da yetmez;
#   ya arayıp bulduğun şeyin İZİNİ ver, ya aradığını ve BULAMADIĞINI açıkça yaz.
_PA_OLUMSUZ = re.compile(r"\b(yok|none|bulunamad|not\s+found)\w*\b", re.I)
_PA_REFERANS = re.compile(
    r"`[^`]+`"                       # `ref_docs/…` backtick'li
    r"|[\w./\\-]+\.(?:md|abap|cds|py|json|ya?ml|txt|pdf)\b"   # dosya uzantısı
    r"|\b(?:ADR|KAYIT|PR|core)[\s#-]?\d+"                     # ADR 0022 · core#145
    r"|https?://\S+"                                          # URL
    r"|[\w-]+/[\w./-]+"                                       # yol izi (a/b/c)
    r"|\b(bulundu|found)\b",                                  # eski biçim KORUNUR
    re.I)


def _prior_art_ok(deger: str) -> bool:
    """Prior-art değeri kabul edilebilir mi? (boş/yer-tutucu zaten `_dolu_mu`da elenir)"""
    if not _dolu_mu(deger):
        return False
    return bool(_PA_OLUMSUZ.search(deger) or _PA_REFERANS.search(deger))
# Yeni madde / başlık / kod-çiti = değerin bittiği yer
_YENI_MADDE = re.compile(r"^\s*(?:[-*+]\s|#{1,6}\s|```|\|)")


def _deger(metin: str, alan: str) -> str:
    """Alanın değerini çıkarır: başlık satırının kalanı + varsa devam satırları."""
    rx = _ALAN_BASLIK.get(alan)
    if rx is None:
        return ""
    satirlar = metin.splitlines()
    for i, s in enumerate(satirlar):
        m = rx.match(s)
        if not m:
            continue
        parcalar = [m.group("deger")]
        for devam in satirlar[i + 1:]:
            if not devam.strip() or _YENI_MADDE.match(devam):
                break
            parcalar.append(devam)
        return " ".join(parcalar)

    # 2. biçim: MARKDOWN BÖLÜM BAŞLIĞI → başlıktan sonraki blok (başlık HARİÇ).
    brx = _ALAN_MD_BASLIK.get(alan)
    if brx is not None:
        for i, s in enumerate(satirlar):
            bm = brx.match(s)
            if not bm:
                continue
            seviye = len(bm.group("d"))
            govde = []
            for devam in satirlar[i + 1:]:
                hm = _MD_BASLIK.match(devam)
                if hm and len(hm.group(1)) <= seviye:
                    break            # aynı/üst seviye başlık → bölüm bitti
                govde.append(devam)
            return " ".join(govde)
    return ""


def _dolu_mu(deger: str) -> bool:
    """Değer gerçek içerik taşıyor mu?

    Boş / yalnız noktalama / şablonun kendi yer-tutucusu → DOLU DEĞİL.
    ⚠ Bilinçli sınır: bu kontrol "boş şablon"u kapatır, "kötü içerik"i DEĞİL (o yargı
    işidir — gate'in beyanı da 'artefakt üretildi mi'dır). Yer-tutucu listesi birebir
    eşleşme arar; hafifçe düzenlenmiş bir yer-tutucu geçer. Aşırı-agresif bir sezgisel
    (ör. "N harften az") gerçek kısa cevapları ('yok') bloklardı — FP bütçesi.
    """
    d = " ".join(deger.split()).strip().lower()
    if not d:
        return False
    if d in _YER_TUTUCULAR:
        return False
    # yalnız yapısal/noktalama karakteri kalıyorsa içerik yok ("- [ ] : ...", "[]", "—")
    return any(c.isalnum() for c in d)


def main() -> int:
    ap = argparse.ArgumentParser(description="ITG S2 intake-artefaktı + mutabakat gate")
    ap.add_argument("artifact", help="intake-artefaktı .md yolu")
    args = ap.parse_args()

    p = Path(args.artifact)
    if not p.exists():
        sys.stderr.write(
            f"⛔ ITG-S2 SIGNOFF: intake-artefaktı bulunamadı: {args.artifact}\n"
            "S2 (kapsamlı) iş SAP-yazmasına geçmeden ÖNCE intake-artefaktı üretilmeli "
            "(playbook/intake-triage.md S2 şeması) + kullanıcı MUTABAKAT'ı alınmalı.\n")
        return 1

    text = p.read_text(encoding="utf-8", errors="replace")

    eksik = [(ad, rx) for ad, rx in _ZORUNLU if not rx.search(text)]
    if eksik:
        # ⚠ HANGİ DESEN tutmadı, AÇIKÇA yazılır. Eskiden yalnız "alan eksik" deniyordu;
        # eşleşmeyeni bulmak için GATE'İN KAYNAĞINI okumak gerekiyordu (ölçülmüş maliyet).
        detay = "\n".join(f"    · '{ad}' → denenen desen: {rx.pattern}" for ad, rx in eksik)
        sys.stderr.write(
            f"⛔ ITG-S2 SIGNOFF: intake-artefaktında zorunlu alan(lar) eksik: "
            f"{', '.join(ad for ad, _ in eksik)}.\n{detay}\n"
            "  (Başlıkta araya kelime girebilir — ör. 'ETKİLENEN / İLGİLİ OBJELER' geçerlidir.)\n"
            "Şema: KAPSAM · Etkilenen objeler (canlı-doğrulanmış) · Prior-art · Kabul kriterleri (EARS). "
            "Bkz. playbook/intake-triage.md S2 intake-artefaktı.\n")
        return 1

    # Başlık VAR ama DEĞER boş/yer-tutucu → artefakt üretilmiş değil, şablon kopyalanmış.
    bos = [ad for ad, _rx in _ZORUNLU if not _dolu_mu(_deger(text, ad))]
    if bos:
        sys.stderr.write(
            f"⛔ ITG-S2 SIGNOFF: zorunlu alan(lar) BAŞLIK olarak var ama DEĞERİ boş/şablon: "
            f"{', '.join(bos)}.\n"
            "Başlığın varlığı doldurulduğu anlamına gelmez — şablonu kopyalayıp "
            "'MUTABAKAT: [x]' işaretlemek bu kapıyı GEÇMEZ (ADR 0022). Her alanı "
            "kendi içeriğiyle doldur: KAPSAM gerekçesi · canlı-doğrulanmış obje listesi · "
            "prior-art referansı ya da 'yok' · EARS kabul kriterleri.\n")
        return 1

    if not _prior_art_ok(_deger(text, "prior-art")):
        sys.stderr.write(
            "⛔ ITG-S2 SIGNOFF: 'Prior-art' alanı boş/belirsiz. Kabul edilen: ya AÇIK "
            "OLUMSUZ ('yok' / 'bulunamadı'), ya bir REFERANS İZİ (`ref_docs/…` · dosya "
            "adı · ADR/kayıt no · URL · yol). Düzyazı bir cümle YETMEZ — kurumsal-hafıza "
            "araması mecburidir (ADR 0022 3-eksen).\n"
            f"  Okunan değer: {_deger(text, 'prior-art').strip()[:120]!r}\n")
        return 1

    if not _MUTABAKAT_ISARETLI.search(text):
        durum = "MUTABAKAT satırı var ama işaretsiz" if _MUTABAKAT_SATIR.search(text) else "MUTABAKAT satırı yok"
        sys.stderr.write(
            f"⛔ ITG-S2 SIGNOFF: kullanıcı sign-off'u yok ({durum}). S2 işi build'e ancak "
            "'MUTABAKAT: [x]' (kullanıcı onayı) sonrası geçer (ADR 0022). Kullanıcıyla "
            "intake-artefaktını madde-madde mutabık kal, sonra işaretle.\n")
        return 1

    print(f"✓ ITG-S2 SIGNOFF: intake-artefaktı tam + MUTABAKAT işaretli ({p.name}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
