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
_ZORUNLU = [
    ("kapsam", re.compile(r"kapsam\s*:", re.I)),
    ("etkilenen objeler", re.compile(r"etkilenen\s+obje", re.I)),
    ("prior-art", re.compile(r"prior-?art\s*:", re.I)),
    ("kabul kriterleri", re.compile(r"kabul\s+kriter", re.I)),
]
# Alan DEĞERİNİ çeken desenler (başlık + `:` sonrası; satır sonuna dek).
# Değer bir sonraki madde/başlık/kod-çiti'ne kadar SONRAKİ SATIRLARDAN da toplanır —
# gerçek artefaktlarda çok satırlı yazım yaygın; tek-satır varsayımı FP üretirdi.
_ALAN_BASLIK = {
    "kapsam": re.compile(r"^.*?\bkapsam\s*:(?P<deger>.*)$", re.I),
    "etkilenen objeler": re.compile(r"^.*?etkilenen\s+obje[^:]*:(?P<deger>.*)$", re.I),
    "prior-art": re.compile(r"^.*?prior-?art\s*:(?P<deger>.*)$", re.I),
    "kabul kriterleri": re.compile(r"^.*?kabul\s+kriter[^:]*:(?P<deger>.*)$", re.I),
}
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
# Prior-art satırının DOLU olması: "bulundu" veya "yok" içermeli (boş bırakılamaz)
_PRIOR_ART_DOLU = re.compile(r"prior-?art\s*:.*\b(bulundu|yok|none|found)\b", re.I)
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

    eksik = [ad for ad, rx in _ZORUNLU if not rx.search(text)]
    if eksik:
        sys.stderr.write(
            f"⛔ ITG-S2 SIGNOFF: intake-artefaktında zorunlu alan(lar) eksik: {', '.join(eksik)}.\n"
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

    if not _PRIOR_ART_DOLU.search(text):
        sys.stderr.write(
            "⛔ ITG-S2 SIGNOFF: 'Prior-art' alanı boş/belirsiz — 'bulundu: <ref>' VEYA 'yok' "
            "yazılmalı (kurumsal-hafıza araması mecburi; ADR 0022 3-eksen). Referansı doğrula, "
            "yoksa 'yok' de.\n")
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
