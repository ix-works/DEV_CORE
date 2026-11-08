r"""
check_rap_managed_etag.py — Managed RAP BDEF'te optimistic locking (etag) ve
lock master eksikliğini SAP'ye yazmadan yakalar.

Kaynak (gap-analysis #16, SAP topluluğu RAP-demo anekdotu):
  Claude managed RAP demo'da LAST_CHANGED_AT / etag alanını eklemeyi unutunca
  uygulama çalışmadı (managed senaryoda kilitleme/concurrency için hayati).

Kural (managed + BDEF'in herhangi bir bloğunda yazma operasyonu varsa):
  - Root behavior `lock master` tanımlamalı (kilit).            → eksikse BLOCKER
  - `lock master` taşıyan HER blok (KÖK) `etag master <field>` tanımlamalı (optimistic
    concurrency); kökte `etag dependent` GEÇERSİZ. Kökün kendi gövdesinde create/update/delete
    olmasa da (yalnız `action …; association …;`) denetlenir — salt-okunurluk BDEF DÜZEYİNDE
    karar verilir, blok düzeyinde değil (#405 bug-gate F1).         → eksikse BLOCKER
  - Çocuk blok (`lock master` taşımayan): `etag master` ya da `etag dependent` KABUL; etag'siz
    çocuk DENETLENMEZ (ÖLÇÜLMEDİ — KAPSAM satırında sayılır). Yazma operasyonu taşımayan çocuk
    salt-okunur sayılır.
  - İPUCU: etag master alanı CDS root view'da
    `@Semantics.systemDateTime.lastChangedAt: true` olmalı (BDEF dışı; WARNING hatırlatma).

Kapsam dışı (OK): unmanaged (released BAPI/EML), `query`/read-only behavior, .bdef olmayan.

VARLIK (BLOK) DÜZEYİ (DEV_CORE #405, 2026-11-08):
  Eskiden `etag` dosyanın TAMAMINDA aranıyordu: kökten `etag master` silinip çocuktaki
  `etag dependent` kalınca rc=0 (ölçüldü). Artık her `define behavior for` bloğu (bir sonraki
  bloğa kadar) ayrı değerlendirilir:
    · `lock master` taşıyan blok = KÖK → `etag master <alan>` ister (`etag dependent` yetmez).
    · diğer bloklar = ÇOCUK → `etag master` ya da `etag dependent` KABUL; etag'siz çocuk
      DENETLENMEZ (lider kararı 2026-11-08 — tüketici korpusunda DEV'de aktif 6 BDEF'in çocuğu
      etag'siz, SAP zorlamıyor) ⇒ KAPSAM satırı "ÖLÇÜLMEDİ: çocuk blok etag'i" der.
    · yazma operasyonu (create/update/delete) taşımayan ÇOCUK blok etag İSTEMEZ (salt-okunur
      varlık). KÖK bu istisnaya GİRMEZ: BDEF'te herhangi bir blok yazıyorsa her `lock master`
      bloğu denetlenir (bug-gate F1, 2026-11-08: CRUD'suz kök — yalnız `action doIt;
      association _Item;` — + CRUD'lu çocuk + hiç etag yok → taban BLOCKER, ilk #405 sürümü
      rc 0 "temiz" veriyordu = ilan edilmemiş gevşetme; ölçüldü, lider bağımsız yeniden üretti).
  Taban (2026-11-08, 42 BDEF): rc dağılımı değişmez (yalnız mesaj metni blok no + satır taşır).
  Blok adı YAKALANMAZ (#402: bu dosya ad deseni yazmaz) — bulgu blok sırası + satır no ile basılır.
  "En az bir `lock master`" kuralı dosya düzeyinde AYNEN durur. LastChanged semantics WARNING'i
  dosya düzeyinde AYNEN durur.

TANIMA (DEV_CORE #402, 2026-11-08) — ADA DEĞİL ANAHTAR SÖZCÜĞE bakılır:
  · BDEF mi? = `define behavior for` var mı. Eski desen adı `(\w+)` ile de yakalıyordu;
    `\w` `/` eşlemediği için namespace'li (`/NSPC/...`) BDEF "behavior definition değil"
    sayılıp rc=0 dönüyordu. Kontrol adı hiç kullanmadığı için ad yakalaması kaldırıldı.
  · managed mi? = BDEF'in ilk deyimi (uygulama türü) satır başında `managed` ile mi
    başlıyor (`unmanaged` hariç). Eski `managed\s+implementation` deseni
    `managed with additional save ...` / `managed with unmanaged save ...` biçimlerini
    görmüyordu: Z adlı BDEF bile "kapsam dışı" çıkıyordu (#402 EK-1).

Kullanım:
    python scripts/validators/check_rap_managed_etag.py <bdef_path>

Exit kodu: 0 temiz / 1 BLOCKER
"""
import argparse
import re
import sys
from pathlib import Path

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Uygulama türü BDEF'in ilk deyimidir ve satır başında durur: `managed …;` · `managed with
# additional save …;` · `managed with unmanaged save …;` · `unmanaged …;`. Satır-başı çapası
# `field ( numbering : managed )` gibi gövde içi kullanımları dışarıda bırakır; `\b` ise
# `unmanaged` içindeki `managed`ı eşlemez (n-m arasında sözcük sınırı yok).
MANAGED_RE = re.compile(r'^\s*managed\b', re.IGNORECASE | re.MULTILINE)
UNMANAGED_RE = re.compile(r'^\s*unmanaged\b', re.IGNORECASE | re.MULTILINE)
# BDEF mi? = anahtar sözcük. Ad YAKALANMAZ: bu kontrol adı hiç kullanmaz (bkz. docstring).
DEFINE_BEHAVIOR_RE = re.compile(r'\bdefine\s+behavior\s+for\b', re.IGNORECASE)
WRITE_OP_RE = re.compile(r'\b(create|update|delete)\b', re.IGNORECASE)
LOCK_MASTER_RE = re.compile(r'\block\s+master\b', re.IGNORECASE)
LOCK_DEPENDENT_RE = re.compile(r'\block\s+dependent\b', re.IGNORECASE)
ETAG_RE = re.compile(r'\betag\s+(master|dependent)\b', re.IGNORECASE)
LASTCHANGED_SEMANTICS_RE = re.compile(
    r'@Semantics\.systemDateTime\.lastChangedAt', re.IGNORECASE)


def _strip_comments(text: str) -> str:
    out = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('//'):
            out.append('')      # satır SAYISI korunur: blok bulgusu satır no basar (#405)
            continue
        out.append(line)
    return '\n'.join(out)


def behavior_bloklari(text: str) -> list[tuple[int, str]]:
    """(başlangıç satırı, blok metni) — her `define behavior for`'dan bir sonrakine kadar.

    Bir sonraki bloğa kadar kesmek, bloğun başlığını (lock/etag/persistent table) ve gövdesini
    (`{ create; update; … }`) birlikte tutar. Ad yakalanmaz.
    """
    konumlar = [m.start() for m in DEFINE_BEHAVIOR_RE.finditer(text)]
    out = []
    for i, bas in enumerate(konumlar):
        son = konumlar[i + 1] if i + 1 < len(konumlar) else len(text)
        out.append((text.count('\n', 0, bas) + 1, text[bas:son]))
    return out


def blok_etag_ihlalleri(text: str) -> tuple[list[str], dict]:
    """Varlık düzeyi etag denetimi (#405) → (ihlaller, kapsam sayaçları).

    KÖK (`lock master`; BDEF'te herhangi bir blok yazıyorsa — kökün kendi gövdesi CRUD'suz olsa
    da) → `etag master <alan>` ister; `etag dependent` kökte geçersiz. ÇOCUK blok: etag varsa `master|dependent` KABUL; etag'siz çocuk DENETLENMEZ
    (lider kararı 2026-11-08: tüketici korpusunda DEV'de AKTİF 6 BDEF'in çocuk bloğu etag'siz —
    SAP zorlamıyor; bu kapı onu BLOCKER yapmaz) ⇒ sayılıp ÖLÇÜLMEDİ diye beyan edilir.
    """
    ihlal = []
    say = {"blok": 0, "kok": 0, "cocuk": 0, "etagsiz_cocuk": 0, "salt_okunur": 0}
    # Salt-okunurluk BDEF DÜZEYİNDE (bug-gate F1): herhangi bir blok yazıyorsa kök daima denetlenir.
    bdef_yazmali = bool(WRITE_OP_RE.search(text))
    for sira, (satir, blok) in enumerate(behavior_bloklari(text), 1):
        say["blok"] += 1
        etag = ETAG_RE.search(blok)
        if LOCK_MASTER_RE.search(blok) and bdef_yazmali:
            say["kok"] += 1
            if not etag or etag.group(1).lower() != 'master':
                ihlal.append(
                    f"blok #{sira} (satır {satir}, KÖK — 'lock master'): 'etag master <alan>' YOK"
                    + (" ('etag dependent' kökte geçersiz)" if etag else "")
                    + " — optimistic concurrency için zorunlu. Anekdot: LAST_CHANGED_AT/etag "
                    "unutulunca managed RAP çalışmaz. Köke 'etag master <LastChangedField>' ekle.")
            continue
        if not WRITE_OP_RE.search(blok):
            say["salt_okunur"] += 1
            continue                                  # salt-okunur çocuk varlık: etag gerekmez
        say["cocuk"] += 1
        if not etag:
            say["etagsiz_cocuk"] += 1
    return ihlal, say


def kapsam_satiri(say: dict) -> str:
    """KAPSAM BEYANI (CLAUDE.core §7) — sıfır-bulgu anı dahil her koşumda basılır."""
    return (f"KAPSAM: {say['blok']} behavior bloğu · kök {say['kok']} · çocuk {say['cocuk']} · "
            f"salt-okunur {say['salt_okunur']} · ÖLÇÜLMEDİ: çocuk blok etag'i "
            f"(etag'siz çocuk {say['etagsiz_cocuk']}, denetlenmez)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Managed RAP BDEF etag/lock master kontrolü')
    parser.add_argument('artifact')
    parser.add_argument('--strict', action='store_true',
                       help='(uyumluluk; NO-OP — şiddeti DEĞİŞTİRMEZ, run_all --strict kazara terfi ettirmesin; ADR 0019 §54)')
    args = parser.parse_args()

    path = Path(args.artifact)
    if not path.exists():
        print(f'HATA: {path} bulunamadı', file=sys.stderr)
        return 1

    raw = path.read_text(encoding='utf-8', errors='replace')
    text = _strip_comments(raw)

    if not DEFINE_BEHAVIOR_RE.search(text):
        print(f'OK — {path.name} behavior definition değil, kapsam dışı')
        return 0
    if UNMANAGED_RE.search(text) and not MANAGED_RE.search(text):
        print(f'OK — {path.name} unmanaged (released BAPI/EML), etag kapsamı dışı')
        return 0
    if not MANAGED_RE.search(text):
        print(f'OK — {path.name} managed implementation değil, kapsam dışı')
        return 0
    if not WRITE_OP_RE.search(text):
        print(f'OK — {path.name} yazma operasyonu (create/update/delete) yok, '
              f'etag/lock gerekmez')
        return 0

    violations = []
    warnings = []

    if not LOCK_MASTER_RE.search(text):
        # En az bir root 'lock master' olmalı
        violations.append(
            "Root behavior 'lock master' tanımlamıyor — managed senaryoda kilit zorunlu "
            "(child'lar 'lock dependent by _assoc').")

    # #405: dosya düzeyi `ETAG_RE.search(text)` YERİNE blok düzeyi (bkz. docstring)
    blok_ihlal, say = blok_etag_ihlalleri(text)
    violations.extend(blok_ihlal)

    if ETAG_RE.search(text) and not LASTCHANGED_SEMANTICS_RE.search(text):
        warnings.append(
            "BDEF'te etag var ama bu dosyada @Semantics.systemDateTime.lastChangedAt "
            "görülmedi — etag-master alanının CDS ROOT view'da "
            "@Semantics.systemDateTime.lastChangedAt:true (+ created/lastChanged admin "
            "alanları) olduğundan emin ol (BDEF dışı kontrol).")

    if not violations:
        msg = f'OK — {path.name} managed RAP etag/lock temiz'
        if warnings:
            print(msg)
            for w in warnings:
                print(f'  [WARNING] {w}')
        else:
            print(msg)
        print(f'  {kapsam_satiri(say)}')
        return 0

    print(f'\n[BLOCKER] {path.name} — {len(violations)} managed-RAP etag/lock ihlali '
          f'(standards/05 §lock; ADR 0006)', file=sys.stderr)
    for v in violations:
        print(f'  [BLOCKER] {v}', file=sys.stderr)
    for w in warnings:
        print(f'  [WARNING] {w}', file=sys.stderr)
    print(f'  {kapsam_satiri(say)}', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
