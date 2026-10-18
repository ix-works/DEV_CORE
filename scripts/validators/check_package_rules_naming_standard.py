# -*- coding: utf-8 -*-
"""
check_package_rules_naming_standard.py — paket `.rules.md` naming tablosu ↔ KURUMSAL STANDART
eşlik kapısı (C-RULES-NAME-01).

NEDEN VAR — ölçülmüş bir SINIF, vaka değil:
  `{PKG}_DE_*` / `{PKG}_DOM_*` yanlışı paket şablonundan miras alındı ve bir projede **aynı
  düzeltme DÖRT kez ELLE** yapıldı (2026-05-15 · 2026-08-05 · 2026-08-17 · 2026-08-28). Kök
  şablon 2026-08-20'de düzeltildi ama **var olan paketleri kimse ölçmedi** ⇒ 2026-08-29'da
  6 paket hâlâ yanlıştı. `check_package_naming.py` bu ekseni ÖLÇMEZ: o, tablodaki regex'e
  karşı DOSYA ADLARINI doğrular — tablonun KENDİSİ yanlışsa sessizce yanlış kuralı uygular.
  ⇒ Standarda uygun ad yazan geliştirici **validator hatası** alır; ya kural bükülür ya ad bozulur.

KANONİK KAYNAK — TEK: `templates/new-package/.rules.md.tmpl` (naming tablosu)
  ↳ dayanağı `standards/01-naming.md` §4.4.5 (DTEL=`E`, Domain=`D`); şablon ↔ standart eşliğini
    `tests/fixtures/sablon_zorunlu_maddeler` zaten ölçer (ikinci bir parite kapısı AÇILMAZ).
  ⭐ TARİHÇE (2026-10-18 core'a taşındı): bu kapı önce bir projede `validators-local/` altında
  yaşıyordu ve haritayı GÖMÜLÜ taşıyordu (gerekçe: proje worktree'sinde `core/` junction'ı
  yok). Gömülü kopya 2026-09-13'te şablonun `Class` satırı `ZCL_{PKG_NOZ}_*`'e geçince
  BAYATLADI — kapı kendi `HARITA-SAPMASI` uyarısını ve 8 bayat `[BİLGİ]` satırını basıyordu
  (ölçüldü 2026-10-18). Core içinde şablon her koşumda `__file__`'ın yanındadır ⇒ gömme
  gerekçesi düştü, ÇOĞALTMA KALDIRILDI: harita her koşumda şablondan OKUNUR.
  Yer tutucular bootstrap'in KENDİ haritasıyla çözülür (`bootstrap_package.pkg_noz_turet` +
  `substitute`) — desen yeniden türetilmez.

NE ÖLÇER:
  `PREFIX-SAPMASI` — paketin `.rules.md` satırında, kanonik kümede OLMAYAN bir önek var
  (⛔ yalnız `ZORUNLU_EKSEN` için bulgu; gerekçesi aşağıda).
  Kalan eksenler bulgu DEĞİL, `[BİLGİ]` envanteri olarak basılır — görünür kalır, kırmızı yapmaz.

⭐ KAPSAM NEDEN DAR — 23 GERÇEK PAKETE KARŞI ÖLÇÜLDÜ (2026-08-29, bir proje ağacı):
  İlk tasarım "her satır şablonla BİREBİR eşleşsin" diyordu → **17 sapma / 23 paket**.
  Tek tek bakıldığında 16'sı **yanlış pozitifti**:
    · `Class` (9 paket) + `Lock Object` (1): şablon iki alternatif sunuyor; paket birini
      seçiyor ⇒ DARALTMA meşrudur ⇒ karşılaştırma "eşitlik" değil **ALT KÜME**.
    · `Message Class` (5 paket): `{PKG}_MSG` + çıplak `{PKG}` (legacy) ikisi de kanonik;
      eksen `[BİLGİ]` kalır — üçüncü biçimler görünür kalsın diye.
    · `Include`/`Class` metin hücrelerindeki emsal adları önek değil örnek.
  ⛔ Bu bir GEVŞETME DEĞİL, DETEKTÖR DÜZELTMESİDİR: `_DE_`/`_DOM_` ekseni AYNEN bulgu üretir
     (kanıt: tests/fixtures/rules_naming_standard).

OBJE TİPİ ANAHTARI BİÇİMDEN BAĞIMSIZDIR (2026-10-18): `| Data element |`,
  `| **Data Element** |`, `` | `Domain` | `` aynı satırdır (`tip_anahtari`: `*`/backtick
  sökülür, boşluk sadeleşir, `casefold`). Önceden anahtar harfe/biçime duyarlıydı ve böyle
  yazılmış satır SESSİZCE ölçülmüyordu (bir tüketici pakette ölçüldü: `| Data element |`).

PAKET KEŞFİ `check_package_rules_present.find_packages` ile ORTAKTIR (iki seviye:
  `<source_root>/<MODÜL>/<PAKET>/`). Önceki `rglob(".rules.md")` `node_modules` dahil tüm
  ağacı geziyordu ve iç içe bir `.rules.md`'nin üst dizinini PAKET sanıyordu.

ÇIKIŞLAR ("bakamadım" ≠ "temiz"):
  0  temiz · ya da bulgu (warn-first) · ya da `[SKIP] KAPSAM SIFIR` (kaynak kökü VAR ama
     paket `.rules.md`'si yok — görünür satırla; 0 paketli tüketicide YENİ BLOK üretmez,
     ADR 0019)
  1  bulgu + `--bulguda-exit1` (HARD'a terfi LİDER kararı)
  2  ÖLÇÜLEMEDİ — kanonik şablon okunamadı · zorunlu eksen satırı şablonda yok · kaynak
     kökü HİÇ YOK (yanlış `source_root`/cwd: "0 paket" ile aynı şey değildir)
  Eksen satırı (DTEL/Domain) taşımayan paket ÖLÇÜLMEZ; sayısı her koşumda
  `ÖLÇÜLMEDİ: N paket` satırıyla basılır (`run_all --ozet`te görünür).
`--strict` bilinçli NO-OP (run_all bayrağı iletirse kapı kazara sertleşmesin).

Kullanım: python core/scripts/validators/check_package_rules_naming_standard.py [--bulguda-exit1]
Kablolama: run_all_validators (PROJE modu; CORE modunda SKIP — proje kaynağı gerekir).
Kalıcı korpus: tests/fixtures/rules_naming_standard.
"""
# ENFORCES: C-RULES-NAME-01  (.rules.md naming tablosu ↔ kurumsal standart eşliği)
# GATE-SEVERITY: advisory
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

# Şablon CORE varlığıdır → `__file__` türevi MEŞRUDUR (check_rule_gate_coverage CORE-03 ile
# aynı gerekçe). PROJE tarafı (kaynak kökü) ASLA `__file__`'dan türetilmez → utils.project_config.
CORE_ROOT = Path(__file__).resolve().parents[2]
SABLON = CORE_ROOT / "templates" / "new-package" / ".rules.md.tmpl"

# ⛔ BULGU ÜRETEN EKSENLER — ölçülmüş sınıfın kendi ekseni (docstring "KAPSAM NEDEN DAR").
ZORUNLU_EKSEN = ("Data Element", "Domain")

# Markdown tablo satırı: `| Obje Tipi | Prefix | Regex |`
SATIR_RE = re.compile(r"^\|([^|]+)\|([^|]+)\|(.*)\|\s*$")
BACKTICK_RE = re.compile(r"`([^`]+)`")
# Görünür + gerekçeli muafiyet. Sessiz istisna YOK.
ISTISNA_RE = re.compile(r"<!--\s*NAMING-ISTISNA:\s*([^—\-]+?)\s*[—-]+\s*(.+?)\s*-->")


class Olculemedi(Exception):
    """Ölçüm yapılamadı — 'temiz' ile AYNI çıkışa düşmemesi için ayrı sınıf."""


def tip_anahtari(ham: str) -> str:
    """Obje tipi hücresinin KARŞILAŞTIRMA anahtarı: `*`/backtick sökülür, boşluk
    sadeleşir, `casefold`. Şablon ve paket tarafı AYNI fonksiyondan geçer."""
    return " ".join(ham.replace("*", " ").replace("`", " ").split()).casefold()


ZORUNLU_ANAHTAR = tuple(tip_anahtari(t) for t in ZORUNLU_EKSEN)


def _satirlar(metin: str) -> list[str]:
    return metin.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def naming_satirlari(metin: str, adlar: dict[str, str] | None = None) -> dict[str, set[str]]:
    """`.rules.md` / şablon naming tablosundan {tip-anahtarı: {önek,...}} çıkarır.

    Anahtar `tip_anahtari` ile normalize edilir (harf/biçim farkı satırı düşürmesin);
    `adlar` verilirse anahtar → tablodaki görünen ad eşlemesi oraya yazılır.
    Önek hücresi ÇOK DEĞERLİ olabilir (`X` veya `Y`) — bu yüzden hücredeki TÜM
    backtick'li token'lar küme olarak alınır. Tek-token karşılaştırması `Class` ve
    `Lock Object` satırlarını sessizce atlardı (ölçüldü: 15 satırın 2'si).
    """
    out: dict[str, set[str]] = {}
    for l in _satirlar(metin):
        m = SATIR_RE.match(l)
        if not m:
            continue
        ham_tip = m.group(1).strip()
        if not ham_tip or set(ham_tip) <= set("- :"):
            continue
        tip = tip_anahtari(ham_tip)
        if not tip or tip == "obje tipi":
            continue
        onekler = set(BACKTICK_RE.findall(m.group(2)))
        if not onekler:
            ham = m.group(2).strip()
            if ham:
                onekler = {ham}
        if onekler and tip not in out:
            out[tip] = onekler
            if adlar is not None:
                adlar[tip] = " ".join(ham_tip.replace("*", " ").replace("`", " ").split())
    return out


def istisnalar(metin: str) -> dict[str, str]:
    """{tip-anahtarı: gerekçe} — anahtar tablo satırıyla AYNI normalizasyondan geçer."""
    return {tip_anahtari(m.group(1)): m.group(2).strip() for m in ISTISNA_RE.finditer(metin)}


def kanonik_harita(sablon: Path, adlar: dict[str, str] | None = None) -> dict[str, set[str]]:
    """Kanonik harita = şablonun naming tablosu (yer tutuculu). Okunamazsa Olculemedi."""
    if not sablon.is_file():
        raise Olculemedi(f"kanonik şablon YOK: {sablon}")
    tablo = naming_satirlari(sablon.read_text(encoding="utf-8", errors="replace"), adlar)
    eksik = [t for t, a in zip(ZORUNLU_EKSEN, ZORUNLU_ANAHTAR) if a not in tablo]
    if eksik:
        raise Olculemedi(f"şablonun naming tablosunda zorunlu eksen satırı YOK: {', '.join(eksik)} "
                         f"(tablo biçimi değişmiş olabilir — 'temiz' sayılamaz)")
    return tablo


def paket_haritasi(pkg_full: str) -> dict[str, str]:
    """Şablon yer tutucularının değeri — bootstrap_package'ın KENDİ türetmesi."""
    from bootstrap_package import pkg_noz_turet  # noqa: E402 (tek kaynak; desen yeniden türetilmez)
    pkg = pkg_full.replace("_CLC", "")       # bootstrap_package.main() ile aynı ifade
    return {"PKG": pkg, "PKG_NOZ": pkg_noz_turet(pkg), "PKG_FULL": pkg_full}


def coz(onekler: set[str], harita: dict[str, str]) -> set[str]:
    from bootstrap_package import substitute  # noqa: E402
    return {substitute(x, harita) for x in onekler}


def paket_rules_dosyalari(kok: Path) -> list[Path]:
    """Paket keşfi `.rules.md` VARLIK kapısıyla ORTAK (iki seviye; kopya değil, import)."""
    from check_package_rules_present import find_packages  # noqa: E402
    return [p / ".rules.md" for p in find_packages(kok) if (p / ".rules.md").is_file()]


def main() -> int:
    ap = argparse.ArgumentParser(description=".rules.md ↔ kurumsal standart eşlik kapısı")
    ap.add_argument("--bulguda-exit1", action="store_true",
                    help="HARD mod: bulguda exit 1 (terfi kararı LİDERE aittir)")
    ap.add_argument("--strict", action="store_true", help="bilinçli NO-OP")
    ap.add_argument("--sablon", help="kanonik şablon yolu (yalnız fixture/sandbox için)")
    args = ap.parse_args()

    from utils.project_config import project_root, source_dir  # noqa: E402
    proje = project_root()
    sablon = Path(args.sablon).resolve() if args.sablon else SABLON
    adlar: dict[str, str] = {}
    try:
        kanon_ham = kanonik_harita(sablon, adlar)
    except Olculemedi as e:
        print(f"[ÖLÇÜLEMEDİ] {e}", file=sys.stderr)
        return 2

    kok = source_dir()
    if not kok.is_dir():
        # Kök HİÇ yok = yanlış `source_root`/cwd. "0 paket" ile aynı çıkışa düşmez:
        # `init_project` kökü `.gitkeep` ile yaratır, yani gerçek tüketicide bu dal erişilmez.
        print(f"[ÖLÇÜLEMEDİ] kaynak kökü yok: {kok} (yanlış `source_root` ya da çalışma "
              f"dizini — naming eşliği ölçülemedi, 'temiz' DEĞİL)", file=sys.stderr)
        return 2
    dosyalar = paket_rules_dosyalari(kok)
    if not dosyalar:
        # ⚠ Proje-lokal sürüm burada exit 2 veriyordu; core'da 0 paketli tüketicide (yeni
        # proje) run_all'ı kırmızıya boğardı = YENİ BLOK (ADR 0019). Görünür satır + exit 0.
        print("[SKIP] KAPSAM SIFIR — %s altında paket `.rules.md`'si yok; naming eşliği "
              "ÖLÇÜLMEDİ ('temiz' DEĞİL)." % kok)
        return 0

    print("check_package_rules_naming_standard — %d paket `.rules.md` · kanonik: %s (%d satır)"
          % (len(dosyalar), sablon.name, len(kanon_ham)))

    bulgular: list[str] = []
    muaf_sayi = 0
    bilgi: list[str] = []
    olculen_eksen = 0
    olculen_paket = 0
    eksensiz: list[str] = []          # eksen satırı HİÇ olmayan paket → ölçülmedi
    kismi: list[str] = []             # tek eksen satırı olan paket → eksik eksen ölçülmedi
    for p in dosyalar:
        metin = p.read_text(encoding="utf-8", errors="replace")
        harita = paket_haritasi(p.parent.name)
        tablo = naming_satirlari(metin)
        muaf = istisnalar(metin)
        yol = p.relative_to(proje).as_posix() if proje in p.parents else p.as_posix()
        mevcut = [a for a in ZORUNLU_ANAHTAR if a in tablo]
        if not mevcut:
            eksensiz.append(yol)
        else:
            olculen_paket += 1
            if len(mevcut) < len(ZORUNLU_ANAHTAR):
                kismi.append(yol)
        for tip, kanon in kanon_ham.items():
            if tip not in tablo:
                continue          # satır YOKLUĞU bulgu değil; eksen satırı yoksa ÖLÇÜLMEDİ sayılır
            if tip in muaf:
                muaf_sayi += 1
                continue
            beklenen = coz(kanon, harita)
            # ⭐ ALT KÜME kuralı: şablon alternatif sunduğunda (`X` veya `Y`) paketin BİRİNİ
            # seçmesi DARALTMADIR ve meşrudur. Bulgu = kanonik kümede OLMAYAN önek.
            yabanci = tablo[tip] - beklenen
            ad = adlar.get(tip, tip)
            if tip in ZORUNLU_ANAHTAR:
                olculen_eksen += 1
                if yabanci:
                    bulgular.append(
                        "PREFIX-SAPMASI  %s\n      %-20s var=%s · standart=%s"
                        % (yol, ad, ", ".join(sorted(tablo[tip])), ", ".join(sorted(beklenen))))
            elif yabanci:
                bilgi.append("%-46s %-20s var=%s · standart=%s"
                             % (yol, ad, ", ".join(sorted(tablo[tip])),
                                ", ".join(sorted(beklenen))))

    print("  bulgu üreten eksen: %s → %d paket · %d satır ölçüldü"
          % (", ".join(ZORUNLU_EKSEN), olculen_paket, olculen_eksen))
    if muaf_sayi:
        print("  gerekçeli muafiyet (NAMING-ISTISNA): %d satır" % muaf_sayi)
    print("  KAPSAM: yalnız `.rules.md` naming TABLOSU ↔ şablon; dosya/obje ADLARINA bakmaz "
          "(o: check_package_naming) · eksen satırı olmayan paket ÖLÇÜLMEDİ (satır yokluğu "
          "bulgu sayılmaz).")
    if eksensiz:
        print("  ÖLÇÜLMEDİ: %d paket (DTEL/Domain satırı yok)" % len(eksensiz))
        for y in eksensiz:
            print("     - %s" % y)
    if kismi:
        print("  ÖLÇÜLMEDİ (kısmi): %d paket tek eksen satırı taşıyor — eksik eksen ölçülmedi"
              % len(kismi))
        for y in kismi:
            print("     - %s" % y)
    if bilgi:
        print("\n[BİLGİ] kapsam DIŞI eksenlerde %d farklılık (bulgu DEĞİL — bu kapı bunları "
              "adjudike etmez, görünür kalsınlar diye listelenir):" % len(bilgi))
        for b in bilgi:
            print("   %s" % b)

    if not bulgular:
        print("\n[OK] %d paket · %d satır ölçüldü: `%s` satırları kurumsal standartla uyumlu"
              " (%d paket `.rules.md` tarandı)"
              % (olculen_paket, olculen_eksen, "` / `".join(ZORUNLU_EKSEN), len(dosyalar)))
        return 0

    etiket = "[BULGU]" if args.bulguda_exit1 else "[UYARI]"
    print("\n%s %d sapma / %d paket ölçüldü" % (etiket, len(bulgular), olculen_paket))
    for b in bulgular:
        print("  %s" % b)
    print("\n  Çözüm: `.rules.md` satırını standarda çek (`core/standards/01-naming.md` §4.4.5).")
    print("  ⛔ ÖNCE canlı kontrol: o pakette eski önekle YARATILMIŞ obje varsa kural "
          "değişimi canlı objeyi ihlale düşürür — `TADIR`/paket içeriği ölçülmeden değiştirme.")
    print("  Meşru istisna ise satırın yakınına ekle: "
          "`<!-- NAMING-ISTISNA: <Obje Tipi> — <gerekçe> -->`")

    if args.bulguda_exit1:
        print("\nHARD mod (--bulguda-exit1) → exit 1", file=sys.stderr)
        return 1
    print("\n⚠ warn-first: bulguda exit 0. HARD'a terfi LİDER kararıdır.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
