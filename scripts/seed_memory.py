# -*- coding: utf-8 -*-
"""seed_memory.py — Repo'daki committed memory tohumunu, bu makinedeki Claude Code
proje-hafıza klasörüne kopyalar (merge-safe).

NEDEN: Claude Code'un "auto-memory" dosyaları repo DIŞINDA, kullanıcı profilinde tutulur:
    ~/.claude/projects/<proje-slug>/memory/*.md  +  MEMORY.md (index)
Bunlar version-control'de OLMADIĞI için clone'da gelmez. Bu script, repoya committed
`.claude/memory-seed/` içeriğini (davranış/feedback kuralları) o klasöre tohumlar →
yeni geliştirici, proje sahibinin çalışma disiplinini (feedback memory) devralır.

KAPSAM: SADECE feedback (nasıl-çalışırsın) memory'leri tohumlanır. Projeye-özel work-state
(project-type memory) tohuma DAHİL DEĞİLDİR (başka projeye yanıltıcı).

MERGE-SAFE: Hedefte zaten var olan dosyayı EZMEZ (yerel daha taze olabilir). Yalnız eksik
dosyaları ekler. --force ile üzerine yazılabilir.

RENAME/SİLME İZİ (2026-07-10 template provası): script eskiden yalnız EKLİYORDU. Seed'de bir
dosya yeniden adlandırılınca (ör. kimlik sızdıran ad temizlenince) daha önce tohumlanmış her
projede ESKİ dosya + BAYAT indeks satırı kalıyordu; kimse görmüyordu. Artık:

  * `.seed-manifest.json` hedefte tutulur (tohumlanan ad → sha1).
  * Manifest'te olup seed'de OLMAYAN dosya = seed'den kalkmış. İçeriği hâlâ manifest'teki
    sha ile aynıysa (kullanıcı DOKUNMAMIŞ) `--prune` ile silinir + indeks satırı düşer.
    Kullanıcı düzenlemişse SİLİNMEZ, yalnız uyarılır.
  * MEMORY.md index'i: eksik seed satırları `## Feedback` altına EKLENİR (mevcut satırlara
    dokunulmaz). Ölü seed linkleri temizlenir.

Gate: `check_memory_index.py` (C-MEM-01) bu bayatlığı zaten FAIL eder — bu script onarır.

Proje-slug: repo kök yolundaki alfanümerik-olmayan her karakter '-' ile değiştirilir
(Claude Code konvansiyonu). Ör: C:\\IX\\<PROJECT_NAME> -> C--IX--PROJECT-NAME-

Kullanım (repo kökünde):
    python scripts/seed_memory.py            # eksikleri ekle + indeksi onar, raporla
    python scripts/seed_memory.py --dry-run  # ne yapacağını göster, yazma
    python scripts/seed_memory.py --prune    # seed'den kalkmış, dokunulmamış dosyaları sil
    python scripts/seed_memory.py --force    # var olanları da seed'le ez (DİKKAT)
    python scripts/seed_memory.py --target <yol>  # hedef memory klasörünü elle ver
    python scripts/seed_memory.py --terfi-adaylari  # SALT-OKUNUR: ters yönü (yerel → tohum) listele

TERS YÖN / TERFİ GÖRÜNÜRLÜĞÜ (Q325, 2026-09-18): yukarıdaki akışın tamamı tohum → makine
yönündedir. Bu makinede yazılan metodoloji-nitelikli bir dersin tohuma girip girmediğini
söyleyen hiçbir yüzey YOKTU. `--terfi-adaylari` o boşluğu KAPATMAZ, GÖRÜNÜR kılar:
listeler, karar vermez, kopyalamaz (hedef repo PUBLIC; genericize yargı ister).
Kararın kendisi ders YAZILIRKEN `metadata.seed: evet|hayir` alanına konur — CLAUDE.core §5.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Seed KAYNAĞI = core (script core'da yaşar; __file__.resolve() junction'da DEV_CORE'a
# çözülür — kaynak için DOĞRU). Yeni yerleşim claude/, eski .claude/ fallback.
CORE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CORE_ROOT / "scripts"))
from utils.claude_paths import auto_memory_dizini, proje_slug  # noqa: E402
# Q289: "indekste var" tanımı (MEMORY.md + `_indeks-*.md` hub'ları, `[[slug]]` + `[x](x.md)`)
# JIT-recall üretecinden PAYLAŞILIR, kopyalanmaz. utils'e taşınmadı: Q287 korpusunun mutasyon
# çapaları o satırlardadır ve mutant builder kopyası utils'teki regex'i mutasyona sokamazdı.
import build_recall_index as _recall  # noqa: E402
SEED_DIR = CORE_ROOT / "claude" / "memory-seed"
if not SEED_DIR.exists():
    SEED_DIR = CORE_ROOT / ".claude" / "memory-seed"

# Seed HEDEFİ = PROJE (env-first; __file__ KULLANMA — projenin slug'ı lazım)
PROJECT_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def project_slug(path: Path) -> str:
    """Claude Code proje-hafıza klasör adı — TEK KAYNAK: utils/claude_paths.proje_slug.

    (2026-08-01 KAYIT S4: bu kural beş dosyada bağımsız yazılmıştı, ikisi alt çizgiyi
    korumaya çalışıyordu ve YANLIŞ dizini gösteriyordu. Ölçüm + karşı-kanıt: claude_paths.)
    """
    return proje_slug(path)


def default_target() -> Path:
    return auto_memory_dizini(PROJECT_ROOT)


MANIFEST_ADI = ".seed-manifest.json"
LINK_RE = re.compile(r"\]\(([^)]+\.md)\)")


def _sha(p: Path) -> str:
    return hashlib.sha1(p.read_bytes()).hexdigest()


def _manifest_oku(target: Path) -> dict:
    p = target / MANIFEST_ADI
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _yetimleri_bul(target: Path, seed_adlari: set, manifest: dict) -> tuple[list, list]:
    """(silinebilir, elle-bakılacak) — seed'den kalkmış tohum dosyaları.

    Manifest YOKSA (manifest özelliğinden önce tohumlanmış proje) hangi dosyanın tohum
    olduğunu bilemeyiz → hiçbir şey SİLİNMEZ, yalnız uyarılır. Yaratmadığımız dosyayı
    silmeyiz.
    """
    if not manifest:
        supheli = [p.name for p in sorted(target.glob("feedback_*.md"))
                   if p.name not in seed_adlari]
        return [], supheli
    silinebilir, dokunulmus = [], []
    for ad, sha in manifest.items():
        if ad in seed_adlari:
            continue
        dst = target / ad
        if not dst.is_file():
            continue
        (silinebilir if _sha(dst) == sha else dokunulmus).append(ad)
    return silinebilir, dokunulmus


def _index_onar(target: Path, seed_index: Path, seed_adlari: set,
                silinen: list, dry: bool) -> list:
    """Eksik seed satırlarını ekle, ölü seed linklerini çıkar. Kullanıcı satırlarına dokunma."""
    dst = target / "MEMORY.md"
    if not dst.is_file() or not seed_index.is_file():
        return []
    metin = dst.read_text(encoding="utf-8")
    seed_metin = seed_index.read_text(encoding="utf-8")
    islem = []

    # 1) silinen/ölü seed linklerini at
    yeni_satirlar = []
    for s in metin.split("\n"):
        m = LINK_RE.search(s)
        if m:
            hedef = m.group(1)
            if hedef in silinen or (hedef not in seed_adlari and not (target / hedef).is_file()):
                islem.append(f"indeksten düştü: {hedef}")
                continue
        yeni_satirlar.append(s)
    metin = "\n".join(yeni_satirlar)

    # 2) indekste olmayan seed dosyaları için seed'in kendi satırını ekle.
    #    Q289: "indekste var" = (adım-1 sonrası) MEMORY.md + `_indeks-*.md` hub'ları, iki link
    #    biçimi. Eskiden yalnız MEMORY.md `](x.md)` görülüyordu → hub'a taşınmış 45 satır her
    #    kurulumda MEMORY.md'ye GERİ ekleniyordu (ölçüldü, canlı kopya --dry-run).
    #    ⚠ Builder'ın YETİM semantiği (diskte olup indekste olmayan) burada "var" DEĞİLDİR.
    var_olan = _recall.metin_linkleri(metin)
    for hub in _recall.indeks_hublari(dst):
        try:
            var_olan |= _recall.metin_linkleri(hub.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    eklenecek = []
    for s in seed_metin.split("\n"):
        m = LINK_RE.search(s)
        if m and m.group(1) in seed_adlari and m.group(1) not in var_olan:
            eklenecek.append(s)
            islem.append(f"indekse eklendi: {m.group(1)}")
    if eklenecek:
        if "## Feedback" in metin:
            metin = metin.replace("## Feedback\n", "## Feedback\n\n" + "\n".join(eklenecek) + "\n", 1)
        else:
            metin = metin.rstrip() + "\n\n## Feedback\n\n" + "\n".join(eklenecek) + "\n"

    if islem and not dry:
        dst.write_text(metin, encoding="utf-8")
    return islem


# ─────────────────────── TERFİ ADAYLARI (SALT-OKUNUR listeleyici, Q325) ────────────
# NEDEN (kayıt Q325, 2026-09-18): bu script TEK YÖNLÜDÜR — tohum → makine. Ters yön
# (yerelde doğan metodoloji dersi → tohum) ne araçta ne kontrol listesinde vardı; karar
# hiçbir yerde kaydedilmiyordu. Sonuç ölçüldü: tohum bayatladığında yalnız yeni kurulum
# değil, MEVCUT tüketici makinelerin her güncellemesi eksik kalır (tohum merge-safe'tir,
# eksiği kimse fark etmez).
#
# ⛔ BU BİR KAPI DEĞİLDİR ve KOPYALAMA YAPMAZ (ADR 0019 merdiveni + kullanıcı kararı):
# hedef repo PUBLIC, genericize yargı ister. Araç LİSTELER, insan KARAR VERİR.
#
# ⚠ `genericize_common` import'u FONKSİYON İÇİNDEDİR, modül başında değil: o modülün
# `id_pattern()` zinciri `git rev-parse` çağırır (~100 ms, tembel_desen korpusunda
# ölçüldü). Normal tohumlama yolunun bu bedeli ödemesi için hiçbir sebep yok.
SEED_ETIKET_RE = re.compile(r"^\s*seed:\s*(\S+)\s*$", re.MULTILINE)


def _frontmatter(metin: str) -> str:
    """Dosyanın EN BAŞINDAKİ `---` bloğu. Yoksa boş dize (etiket 'YOK' sayılır)."""
    if not metin.startswith("---"):
        return ""
    son = metin.find("\n---", 3)
    return metin[:son] if son != -1 else ""


def _seed_etiketi(metin: str) -> tuple[str, str]:
    """(kova, ham-değer). Kova: 'evet' | 'hayir' | '<YOK>'.

    `hayir:proje-ozel` gibi tek kelimelik gerekçe SERBEST ama zorunlu değil → kova
    değerin ilk `:`'inden ÖNCEki parçadır. Tanınmayan değer kendi adıyla kovalanır
    (sessizce 'YOK' saymak, yazım hatasını "karar verilmedi"ye çevirirdi).
    """
    m = SEED_ETIKET_RE.search(_frontmatter(metin))
    if not m:
        return "<YOK>", ""
    ham = m.group(1).strip().strip('"\'')
    return ham.split(":", 1)[0].lower(), ham


def terfi_adaylari(target: Path) -> int:
    from genericize_common import id_pattern, proje_desenleri, sizintilari_bul

    seed_adlari = {p.name for p in SEED_DIR.glob("feedback_*.md")}
    print("\n=== TERFİ ADAYLARI (SALT-OKUNUR — hiçbir dosya yazılmaz/kopyalanmaz) ===")
    print(f"[INFO] Yerel memory : {target}")
    print(f"[INFO] Tohum        : {SEED_DIR}")
    if not target.is_dir():
        print("[ÖLÇÜLEMEDİ] Yerel memory dizini YOK — bu makinede henüz tohumlanmamış ya da "
              "proje kökü yanlış (CLAUDE_PROJECT_DIR). Karşılaştırma yapılamaz.")
        print(f"             (aranan slug kaynağı: {PROJECT_ROOT})")
        return 0

    yerel = sorted(target.glob("feedback_*.md"))
    eksik = [p for p in yerel if p.name not in seed_adlari]
    print("\n--- SAYIM ---")
    print(f"  yerel feedback_*.md      : {len(yerel)}")
    print(f"  tohumdaki feedback_*.md  : {len(seed_adlari)}")
    print(f"  yerelde VAR, tohumda YOK : {len(eksik)}")

    # --- etiket kovaları: karar YAZIM ANINDA verilir, burada yalnız OKUNUR ---
    kova: dict[str, list[Path]] = {}
    gerekce: dict[str, int] = {}
    for p in eksik:
        try:
            metin = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            kova.setdefault("<OKUNAMADI>", []).append(p)
            continue
        k, ham = _seed_etiketi(metin)
        kova.setdefault(k, []).append(p)
        if ":" in ham:
            gerekce[ham.split(":", 1)[1]] = gerekce.get(ham.split(":", 1)[1], 0) + 1
    print("\n--- ETİKET KOVALARI (`metadata.seed:`) — yalnız tohumda OLMAYAN dosyalar ---")
    for k in sorted(kova, key=lambda x: (x != "<YOK>", x)):
        ek = "   ← karar VERİLMEDİ (asıl iş bu)" if k == "<YOK>" else ""
        print(f"  {k:12}: {len(kova[k]):4}{ek}")
    if gerekce:
        print("  gerekçeler: " + ", ".join(f"{g}×{n}" for g, n in sorted(gerekce.items())))

    # --- kimlik ön-taraması: KAPI İLE AYNI KAYNAK (kopya desen değil) ---
    desenler = proje_desenleri(proje_koku=PROJECT_ROOT)
    idp = id_pattern(proje_koku=PROJECT_ROOT)
    aday = sorted(kova.get("evet", []) + kova.get("<YOK>", []), key=lambda p: p.name)
    izli, izsiz = [], []
    for p in aday:
        try:
            metin = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Dosya ADI da taranır (D5): ad kimlik taşıyabilir, gövde temiz olabilir.
        bulgu = sizintilari_bul(metin, idp) + sizintilari_bul(p.name, idp)
        (izli if bulgu else izsiz).append((p, bulgu))
    print(f"\n--- KİMLİK ÖN-TARAMASI (kova 'evet' + '<YOK>' = {len(aday)} dosya) ---")
    print(f"  blocklist girdi sayısı   : {len(desenler)}"
          + ("  ⚠ BOŞ → kimlik taraması YARIM (yalnız yapısal desenler)" if not desenler else ""))
    print(f"  kimlik izi TAŞIYAN       : {len(izli)}   → genericize gerekir, elle çevrilir")
    print(f"  izsiz (doğrudan aday)    : {len(izsiz)}")
    for p, bulgu in izli:
        turler = ", ".join(sorted({f"{ad}:'{tok}'" for tok, ad in bulgu}))
        print(f"    · {p.name}  [{turler}]")
    for p, _ in izsiz:
        print(f"    ✓ {p.name}")

    # --- tohumlanmış dosyalarda SAPMA (iki yön) ---
    manifest = _manifest_oku(target)
    print("\n--- TOHUMLANMIŞ DOSYALARDA SAPMA (iki yön) ---")
    if not manifest:
        print("  [ÖLÇÜLEMEDİ] `.seed-manifest.json` YOK → hangi dosyanın tohumdan geldiği "
              "bilinemez; sapma yönü hesaplanamaz (yön ayrımı manifest sha'sına dayanır).")
    else:
        # ⚠ SATIR-SONU GÜRÜLTÜSÜ AYRI SAYILIR (ölçüldü 2026-09-18, canlı memory):
        # ham sha ile bakınca (b) kovası 26 dosya gösteriyordu; CRLF↔LF normalize edilince
        # GERÇEK içerik farkı **0** çıktı — yani rapor, hiç iş olmayan yerde 26 kalemlik iş
        # uydurmuş olurdu. (a) kovasında da 168'in 8'i yalnız satır-sonuydu. Kaynak: tohum
        # `shutil.copy2` ile bayt-bayt kopyalanır, yerel kopyayı düzenleyen editör CRLF
        # yazabilir. Gürültüyü ayırmayan bir liste, okunmamaya mahkûmdur.
        a_gercek, a_gurultu, b_gercek, b_gurultu = [], [], [], []
        for ad, man_sha in sorted(manifest.items()):
            dst, src = target / ad, SEED_DIR / ad
            if not dst.is_file() or not src.is_file():
                continue
            yb, tb = dst.read_bytes(), src.read_bytes()
            if yb == tb:
                continue
            gurultu = yb.replace(b"\r\n", b"\n") == tb.replace(b"\r\n", b"\n")
            if hashlib.sha1(yb).hexdigest() != man_sha:   # (a) yerelde düzenlenmiş
                (a_gurultu if gurultu else a_gercek).append(ad)
            else:                                          # (b) tohum ilerledi, yerel eski
                (b_gurultu if gurultu else b_gercek).append(ad)
        print(f"  (a) yerelde DÜZENLENMİŞ (geri akış adayı) : {len(a_gercek)}"
              f"   [+{len(a_gurultu)} yalnız satır-sonu farkı = gürültü]")
        for ad in a_gercek:
            print(f"    · {ad}")
        print(f"  (b) tohum İLERLEMİŞ, yerel kopya ESKİ     : {len(b_gercek)}"
              f"   [+{len(b_gurultu)} yalnız satır-sonu farkı = gürültü]")
        print("      ⚠ Normal tohumlama mevcut dosyayı EZMEZ (merge-safe) ⇒ bu sapma bugün "
              "başka hiçbir yüzeyde GÖRÜNMEZ; `--force` bilinçli bir karardır.")
        for ad in b_gercek:
            print(f"    · {ad}")

    # --- KAPSAM BEYANI (core §7: 'bakmadığım yüzey' de yazılır) ---
    print("\n--- KAPSAM BEYANI (neye BAKMADIM) ---")
    print("  · Bu rapor metodoloji/proje ayrımına KARAR VERMEZ — kovalar yalnız yazım anında")
    print("    konmuş `metadata.seed:` etiketini OKUR. '<YOK>' = etiket yok, 'terfi etmeli' DEĞİL.")
    print("  · YALNIZ `feedback_*.md` taranır. `project_*` / `reference_*` / `user_*` dosyaları")
    print("    ve `_indeks-*.md` hub'ları KAPSAM DIŞIDIR (tohum da yalnız feedback taşır).")
    print(f"  · Kimlik taraması BLOCKLIST'E BAĞLIDIR ({len(desenler)} girdi): listede olmayan bir")
    print("    müşteri/sistem adı 'TEMİZ' görünür. 'izsiz' = 'yayına hazır' DEĞİL, 'bu listeyle")
    print("    iz bulunamadı' demektir. Yapısal desenler (makine yolu, e-posta, Z-obje adı,")
    print("    SAP kullanıcı adı) listeden bağımsız çalışır.")
    print("  · Genericize YAPMAZ, dosya KOPYALAMAZ, PR AÇMAZ. Çıktı bir iş listesidir.")
    print("  · Sapma yalnız CRLF↔LF normalize edilerek gürültüden ayrılır; başka hiçbir")
    print("    normalizasyon (boşluk, sıra, biçim) yapılmaz — 'gerçek fark' kovası biçimsel")
    print("    değişiklikleri de içerebilir.")
    print("  · Tohumdaki ama yerelde OLMAYAN dosyalar bu raporun konusu değildir (o yön")
    print("    `--dry-run`'ın 'Eklendi' sayısıdır).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Repo memory tohumunu makineye seed et")
    ap.add_argument("--target", default=None, help="Hedef memory klasörü (vermezsen otomatik hesaplanır)")
    ap.add_argument("--dry-run", action="store_true", help="Yalnız raporla, yazma")
    ap.add_argument("--force", action="store_true", help="Var olan dosyaları da seed ile ez")
    ap.add_argument("--prune", action="store_true",
                    help="Seed'den kalkmış + kullanıcı dokunmamış tohum dosyalarını sil")
    ap.add_argument("--terfi-adaylari", action="store_true",
                    help="SALT-OKUNUR: yerelde olup tohumda olmayan dersleri `metadata.seed:` "
                         "kovalarıyla + kimlik ön-taramasıyla listele (hiçbir şey yazmaz)")
    args = ap.parse_args()

    if not SEED_DIR.exists():
        print(f"[FAIL] Seed klasörü yok: {SEED_DIR}", file=sys.stderr)
        return 1

    # ⚠ Bu dal HER YAZMA ADIMINDAN ÖNCE döner: aşağıdaki `target.mkdir(...)` bile
    # koşmaz. Listeleyicinin salt-okunurluğu SÖZDE değil, AKIŞTA garanti edilir.
    if args.terfi_adaylari:
        return terfi_adaylari(Path(args.target) if args.target else default_target())

    # Q289+: hub indeksleri (`_indeks-*.md`) de tohuma dahildir. Aksi hâlde MEMORY.md'nin
    # hub satırları hedefte BOŞA düşer (dosya yok) ve hub'daki dersler indekssiz kalır —
    # üstelik `_index_onar` hub satırını `seed_adlari`'nda bulamadığı için mevcut bir
    # MEMORY.md'ye hiç EKLEYEMEZ. Ölçüldü 2026-09-17: hub'sız kopyada 108 ders yetim.
    seed_files = sorted(list(SEED_DIR.glob("feedback_*.md"))
                        + list(SEED_DIR.glob("_indeks-*.md")))
    seed_index = SEED_DIR / "MEMORY.md"
    if not seed_files:
        print(f"[WARN] {SEED_DIR} içinde feedback_*.md yok — tohumlanacak bir şey yok.")
        return 0

    target = Path(args.target) if args.target else default_target()
    print(f"[INFO] Proje kök: {PROJECT_ROOT}  (seed kaynağı core: {CORE_ROOT})")
    print(f"[INFO] Seed     : {SEED_DIR} ({len(seed_files)} feedback dosyası)")
    print(f"[INFO] Hedef    : {target}")
    print(f"[INFO] Mod      : {'DRY-RUN' if args.dry_run else ('FORCE' if args.force else 'merge (eksikleri ekle)')}")

    added, skipped, forced = [], [], []

    if not args.dry_run:
        target.mkdir(parents=True, exist_ok=True)

    for f in seed_files:
        dst = target / f.name
        if dst.exists() and not args.force:
            skipped.append(f.name)
            continue
        if dst.exists() and args.force:
            forced.append(f.name)
        else:
            added.append(f.name)
        if not args.dry_run:
            shutil.copy2(f, dst)

    # MEMORY.md index — yalnız hedefte yoksa kopyala (kullanıcı index'ini koru)
    index_action = "atlandı (zaten var)"
    if seed_index.exists():
        dst_index = target / "MEMORY.md"
        if not dst_index.exists() or args.force:
            index_action = "kopyalandı" if not dst_index.exists() else "EZİLDİ (--force)"
            if not args.dry_run:
                shutil.copy2(seed_index, dst_index)

    # --- seed'den kalkmış (yeniden adlandırılmış/silinmiş) tohum dosyaları ---
    seed_adlari = {f.name for f in seed_files}
    manifest = _manifest_oku(target)
    silinebilir, dokunulmus = _yetimleri_bul(target, seed_adlari, manifest)
    silinen: list = []
    if silinebilir:
        if args.prune and not args.dry_run:
            for ad in silinebilir:
                (target / ad).unlink(missing_ok=True)
            silinen = silinebilir
        # --prune yoksa dosya durur ama indeks onarımında ölü link temizlenir

    # --- indeks onarımı: eksik seed satırlarını ekle, ölü linkleri at ---
    index_islem = _index_onar(target, seed_index, seed_adlari, silinen, args.dry_run)

    # --- manifest'i yaz (tohumlanan adlar → sha) ---
    if not args.dry_run:
        yeni_manifest = {f.name: _sha(f) for f in seed_files}
        (target / MANIFEST_ADI).write_text(
            json.dumps(yeni_manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n--- ÖZET ---")
    print(f"  Eklendi : {len(added)}")
    if forced:
        print(f"  Ezildi  : {len(forced)} (--force)")
    print(f"  Atlandı : {len(skipped)} (zaten mevcut, korundu)")
    print(f"  MEMORY.md index: {index_action}")
    for i in index_islem:
        print(f"    · {i}")
    if silinen:
        print(f"  Budandı : {len(silinen)} (seed'den kalkmış, kullanıcı dokunmamış)")
    elif silinebilir:
        print(f"  [WARN] {len(silinebilir)} tohum dosyası seed'den kalkmış (yeniden adlandırılmış?):")
        for ad in silinebilir:
            print(f"    · {ad}   → silmek için: --prune")
    if dokunulmus:
        neden = ("manifest yok (bu proje manifest özelliğinden önce tohumlandı) → tohum mu, "
                 "kullanıcı hatırası mı AYIRT EDİLEMEZ"
                 if not manifest else "seed'den kalkmış AMA yerel olarak DÜZENLENMİŞ")
        print(f"  [WARN] {len(dokunulmus)} dosya seed'de yok — {neden}. SİLİNMEDİ:")
        for ad in dokunulmus:
            print(f"    · {ad}")
        print("    (yaratmadığımız dosyayı silmeyiz; gerekiyorsa elle sil)")

    if args.dry_run:
        print("\n  (DRY-RUN — hiçbir dosya yazılmadı)")
    elif added or forced or silinen or index_islem:
        print("\n[OK] Feedback memory tohumlandı/onarıldı. Yeni Claude oturumunda kurallar yüklenir.")
    else:
        print("\n[OK] Her şey güncel.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
