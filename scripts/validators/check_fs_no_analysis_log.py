"""
check_fs_no_analysis_log.py — FS gövdesine "analiz günlüğü" sızması kontrolü (DOC-FS-05/06, İLKE-2b).

Neden: Çok sürümlü bir FS'te her tur "v1.x'te şu değişti", "(doc-gate H-C netleşme)", "DEV'de canlı
ölçüldü — ilk turda alan adı yanlıştı, 400 döndü", "kullanıcı: '…'" gibi izler GÖVDEYE yazılınca
belge, yapılacak işi tarif eden bir spesifikasyon olmaktan çıkıp danışmanın çalışma defterine döner
(2026-08-17 dersi: 9 sürümlük FS gövdesinde satırların ~%25'i işaretliydi; kullanıcı onaya sunulamaz
buldu). Dünya pratiği 3 katman ister: gövde = kapanmış hedef durum · karar günlüğü (11-A/11-B/EK) ·
analiz süreci (RESEARCH/notlar). Bu gate katman-1'e sızmayı SAYAR.

Kapsam: proje `**/docs/FS-*.md` ve `**/docs/EK-*.md` (FS ekleri; H1'i "Karar ve Kanıt Günlüğü" olan EK = katman-2, tamamı atlanır). Gövde = §1.1 versiyon geçmişi
tablosu, 11-A/11-B bölümleri ve başlığında "Karar" + ("Günlü"|"Açık"|"Öneri") geçen bölümler
(katman-2 alanı) HARİÇ kalan her şey. §1.1 için ayrıca satır-uzunluğu eşiği (DOC-FS-06).

Sayılan işaretler (satır bazında, sınıf sınıf raporlanır):
  A sürüm-etiketi   : v1.5 / v1.5-taslak / "(YENİ, ...)" / "eklendi|revize edildi|düzeltildi" + sürüm
  B gate-bulgu ID   : doc-gate · H-A..H-D · H-1..9 / M-1..9 / L-1..9 (tek hane; L-01 gibi hata kodları DEĞİL)
  C süreç ifadesi   : canlı ölçüldü/ölçüm · DEV'de ölçüldü · ilk turda · yazılmıştı/okumuştu · 400 döndü ·
                      ADT preview · RESEARCH-0n ters/yanlış · "önceden/eskiden … yerine"
  D kullanıcı alıntı: tırnaklı "kullanıcı: '…'" · tarihli "kullanıcı notu/kararı/teyidi GG.AA" (kısa atıf "kullanıcı kararı §9" MEŞRU)
  E önceden→şimdi   : "önceden/eskiden … yerine" · "artık … değil/gösterilmez" · "R-6 revizyonu/
                      düzeltmesi" · "bu revizyonla" · "ilk taslakta"  (doc-gate v2.0, 2026-08-17)

BAŞLIK satırları da taranır (katman-2 ve §1.1 başlıkları hariç; H1 = belgenin kendi kimliği,
taranmaz) — süreç izleri en çok başlık parantezinde saklanıyordu: "## 6. ETKİLENEN OBJELER
(canlı-doğrulanmış …)".

Warn-first (ADR 0019 §54: "yeni gate warn/dryrun DOĞAR → FP shakeout → temizse hard'a
TERFİ"): bulgu VARKEN bile exit 0 + WARN listesi. `--strict` BİLEREK NO-OP'tur —
`run_all_validators --strict` bayrağı TÜM validator'lara iletilir; bu gate'i oradan hard'a
terfi ettirmek terfi kararını kazara bir çağıranın eline verirdi (kardeş warn-first
gate'lerde de aynı sözleşme: check_object_in_correct_pkg / check_package_naming /
check_package_rules_present "--strict … no-op"). Bulguda exit 1 İSTEYEN tek tüketici
post_validate hook'udur → `--bulguda-exit1`. ÖLÇÜLEMEDİ (okunamayan dosya) = exit 2.
`--selftest` → gömülü kırmızı-fixture ile kendi kendini test eder (yakalamazsa exit 1).
Kullanım: python scripts/validators/check_fs_no_analysis_log.py [--bulguda-exit1] [--selftest] [--max-examples N] [--file YOL]
Kablolama: run_all_validators (PROJE, pre-commit — warn-first, çıktı görünür ama FAIL etmez) + hooks/post_validate.py `doc-fs` sınıfı (FS/TS/KD/EK md düzenlenince o dosya için `--file --bulguda-exit1`; bulgu → yazara stderr özeti + OKU-işaretçisi, exit 2 = geri besleme). Kalıcı korpus: tests/fixtures/fs_docstd (38 vektör, 9 mutasyon).
"""
# ENFORCES: DOC-FS-05, DOC-FS-06  (ADR 0019 coverage binding)
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.project_config import project_root  # noqa: E402

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO = project_root()
#
# ⚠⚠ GEVŞETME (2026-08-20, kullanıcı onaylı): `worktrees` prune'a eklendi.
# ÖLÇÜLEN FP: infra-expert bir worktree'de çalışırken pre-commit koştu ve bu gate'in
# özeti **87 işaretli satır / 22 doküman → 174 satır / 44 doküman** oldu; HER bulgu
# İKİ KEZ listelendi (bir kez gerçek yoldan, bir kez `.claude/worktrees/**` kopyasından).
# ⛔ Worktree GEÇİCİ bir checkout'tur: oradaki bulgu AYNI bulgudur, düzeltilecek ayrı
# bir şey yoktur. Daha kötüsü ters yön: worktree'de DÜZELTİLMİŞ bir dosya varken ana
# ağaçtaki bozuk sürüm de sayılır (ya da tersi) ⇒ *"kaç ihlal kaldı"* sorusu YANILTICI
# cevap verir. Bu warn-first bir gate'te fark edilmedi; HARD bir gate'te aynı çiftlenme
# commit'i haksız yere bloklar ya da sayı-eşikli bir kontrolü sessizce bozardı.
#
# ⛔ NE GEVŞEMEDİ — ana ağaçtaki GERÇEK ihlal AYNEN yakalanır (korpus pozitif kontrolle
# kanıtlar). Ayrıca kural KENDİLİĞİNDEN doğru yönü seçer: worktree İÇİNDEN koşulduğunda
# tarama kökü worktree'nin KENDİSİDİR ve altında `worktrees/` bulunmaz ⇒ kendi ağacı
# tam taranır. Kaydın istediği davranış buydu: *"ana ağaçtan koşulduğunda worktree'ler
# hariç; worktree içinden koşulduğunda yalnız kendi ağacı."*
#
# ⚠ SINIF NOTU: bu prune kümesi repoda ÜÇ FARKLI ADLA sekiz validator'da yaşıyor
# (`_SKIP_SEGMENTS` ×4 · `_SKIP` ×1 · `_prune` ×3) + `behavior_manifest.prune`.
# Sekizine de eklendi. ⚠ Ada göre arama (`rg _SKIP_SEGMENTS`) sınıfın YARISINI ıskalar —
# walk-prune noktalarını `dirnames[:]` ile ara. Birleştirme AYRI bir karardır: kümeler
# bilinçli olarak FARKLI (ör. ui5 dar, fs_docstd `archive` taşır).
_SKIP = {"node_modules", "dist", "tmp", ".tmp", ".git", "fixtures", "attic", "archive", "worktrees"}

_TR = "A-Za-zÇĞİÖŞÜçğıöşü"
PATTERNS = {
    "A sürüm-etiketi": re.compile(
        r"(?<![A-Za-z0-9])[vV]\d\.\d{1,2}(?:[a-c])?(?:-taslak)?(?![0-9])"    # v1.5, v1.5c, v1.8-taslak
        r"|\(\*{0,2}YENİ[,\s]"                                                # (YENİ, R-26) / (**YENİ, ... — BÜYÜK; "(yeni parça" değil
        r"|\b[vV]\d\.\d'(?:te|de|da|ta)\b"),                                   # v1.6'da  (case-sensitive)
    "B gate-bulgu ID": re.compile(
        r"doc-gate|\bH-[A-D]\b|(?<![%s0-9-])[HML]-[1-9](?![0-9])" % _TR),
    "C süreç ifadesi": re.compile(
        # geçmiş-zaman süreç anlatısı; ileriye dönük "TS'te canlı ölçülür/teyit edilir" MEŞRU (sayılmaz)
        r"canlı ölç(?!ül(?:ür|ecek|meli|sün))|canlı teyit(?: edildi|li)|DEV'de ölç|DEV canlı|ilk turda"
        r"|yazılmıştı(?!r)|okumuştu|okunmuştu|sanılmış|sanıyordu"
        r"|400 döndü|\b400 verdi|ADT preview|adt_sql|RESEARCH-0\d[^|]{0,40}(?:ters|yanlış)"
        # doc-gate v2.0 bulgusu (2026-08-17): "kanıt/ölçüm anlatısı" gövdede kalıyordu.
        # `doğrulanmış(?!\s*ol)` → ileriye dönük "doğrulanmış OLMALI" gereksinimi MEŞRU.
        r"|doğrulanmıştır|doğrulanmış(?!\s*ol)|ölçümüyle|ölçümü ile|koddan (?:doğrulan|teyit|okun)"
        r"|(?:kontrol|test) edilmedi|sorgulanmadı|ölçülmedi", re.IGNORECASE),
    # E — "önceden→şimdi" anlatısı. ⚠ ÇIPLAK `\bartık\b` KULLANILMAZ: ölçüldü (2026-08-17,
    # 22 doküman) → 48 satır, çoğunluğu Türkçe İSİM "artık" (= bakiye/kalıntı: "bölünmeyen
    # artık miktar", "artık = ana miktar − …") ve meşru iş cümleleri. Sinyal "artık"ta değil,
    # onu izleyen DEĞİŞİM YÜKLEMİNDE (değil/yerine/kalktı/gösterilmez/yazılmaz). Aynı sebeple
    # `[RS]-\d` revizyon atfı alınır ama `[HML]-\d` ALINMAZ — o B sınıfının işi ve belge-içi
    # tanımlı gap ID muafiyeti oradadır (A5 çapası).
    "E önceden→şimdi": re.compile(
        r"(?:önceden|eskiden|daha önce|eski(?:si|sinde))\b[^|]{0,60}(?:yerine|artık|değişti\b|kalktı|kaldırıldı)"
        r"|\bartık\b[^|]{0,50}(?:değil|kalktı|kalkar|gösterilmez|yazılmaz|üretilmez|kullanılmaz)"
        r"|\b[RS]-\d{1,2}\s*(?:revizyonu|düzeltmesi|teyidi|netleşmesi|revizyonuyla)"
        r"|\bbu revizyon(?:la|dan|da)\b|\bönceki sürümde\b|\bilk taslakta\b", re.IGNORECASE),
    # ⛔ ÜÇ ADAY ÖLÇÜLDÜ ve ELENDİ (2026-08-17, 22 doküman) — kanıtsız geri eklenmesin:
    #  · çıplak `bu turda`  → Türkçede İKİ anlamı var: "bu analiz turunda" (TP) ama aynı
    #    korpusta "sürecin bu turunda/geçişinde" (FP: FS-SD-022:1806 "O-02/O-04/M-02 bu
    #    turda da AYRICA çalışır" = iş kuralı). Liderin verdiği örnek "Bu turda kontrol
    #    edilmedi" C sınıfındaki `(?:kontrol|test) edilmedi` ile ZATEN yakalanıyor ⇒
    #    belirsiz desen gerekmiyor.
    #  · `değişti` (sınırsız) → "değiştirilir" içinde eşleşiyordu (FS-SD-022:1914 "Daha önce
    #    tahsis edilmiş bir lotun … sonradan değiştirilir" = iş kuralı) ⇒ `\b` eklendi.
    #  · `artık … yerine`   → tasarım gerekçesinde meşru (EK-A:1077 "onu 'düzeltmek' yerine
    #    silip yeniden yaratmak") ⇒ `yerine` yalnız "önceden/eskiden" kolunda kaldı.
    "D kullanıcı alıntı": re.compile(
        r"[Kk]ullanıcı(?:\s+\d\d\.\d\d)?\s*:\s*[\"“']|[Kk]ullanıcı (?:notu|kararı|teyidi|geri bildirimi)\s+\d\d\.\d\d"),
}
VERSION_ROW_MAX = 400  # §1.1 satırı (karakter) — 1-2 satır ≈ ≤400

# ── KATMAN-0: DOKÜMAN-KONTROL METADATASI (belgenin KENDİ kimliği, analiz günlüğü DEĞİL) ──
# Ölçüldü 2026-08-17 (21 FS/EK, infra-expert F1-F5 turu): işaretlerin bir bölümü kapak
# tablosu satırı (`| Versiyon | v1.3 |`), §1.3 ilgili-doküman satırı (`| KD-SD-021 | … |
# Yazıldı (v0.9) |`, `| RESEARCH-02 | S/4 DEV canlı teyit | …`) ve altbilgi
# (`*Doküman sonu — FS-SD-008 v1.0*`) idi. Bunlar HER FS'te bulunmak ZORUNDA → yazar
# temizleyemez → gate'in yeşili ERİŞİLEMEZ olur; erişilemez yeşil = ölü gate
# (aynı sınıf: "gürültü yapan hook ölü hooktur", post_tool_failure 2026-08-14).
_META_CELL0 = {"versiyon", "sürüm", "version", "doküman sürümü", "belge sürümü"}
_DOC_REF_CELL0 = re.compile(
    r"^\s*[*_`]*\s*(?:FS|TS|KD|EK|RESEARCH|INTAKE|SPEC|ADR|PRD)[-–—]|\.md[`*_\s)]*$", re.IGNORECASE)
_DOC_FOOTER = re.compile(r"^[*_\s>]*doküman sonu\b", re.IGNORECASE)
# §1.1 versiyon tablosu BAŞLIK-YAZIMINDAN BAĞIMSIZ tanınır. Ölçüldü: 21 dokümanın 8'inde
# tablo "## B1. Doküman Kontrolü" altında, ayrı "1.1 Versiyon Geçmişi" başlığı OLMADAN
# duruyor → tüm sürüm satırları GÖVDE sayılıyordu (tek başına 37 işaret, FS-SD-006).
# Sınıf: "denetim yazım-bağımlıysa sınıfı taramaz" — burada tersi: ATLAMA yazım-bağımlıydı.
# ⚠ YAZIM VARYANTLARI: canlı korpusta `| Versiyon | Tarih |` ve `| Ver. | Tarih |` ikisi de
# geçiyor (FS-EWM-000). Tek yazıma bağlanan bir ATLAMA, sınıfın yarısını ıskalar — ilk
# turda tam bu yüzden 8 doküman kaçmıştı. İkinci hücrenin Tarih/Date olma şartı `v`/`ver`
# gibi kısa varyantları güvenli kılar.
_VTABLE_HEADER = re.compile(
    r"^\|\s*[*_`]*\s*(?:versiyon|sürüm|version|ver\.?|v\.?)\s*[*_`]*\s*\|"
    r"\s*[*_`]*\s*(?:tarih|date)\b", re.IGNORECASE)


# BELGENİN KENDİ tanımladığı ID'ler: bazı FS'ler mevcut-durum eksiklerini `| **H-1** | …`
# satırlarıyla TANIMLAR ve gövdede onlara atıf yapar (ölçüldü: FS-SD-014-v2, H-1..H-3,
# 8 satır). Bu iç izlenebilirliktir, doc-gate bulgu numarası DEĞİLDİR. Ayırt edici:
# aynı satırda "doc-gate" geçiyorsa muafiyet YOK (o zaman gerçekten gate bulgusudur).
_ID_TANIM_SATIRI = re.compile(r"^\|\s*[*_`]*\s*([HML]-[1-9])\s*[*_`]*\s*\|")
_B_TOKEN = re.compile(r"[HML]-[1-9]")


def _belge_ici_tanimli(lines) -> set:
    return {m.group(1) for ln in lines for m in [_ID_TANIM_SATIRI.match(ln.strip())] if m}


def _metadata_satiri(s: str) -> bool:
    """Tablo satırı belgenin KİMLİĞİNİ mi bildiriyor (katman-0)? → gövde sayılmaz."""
    if not s.startswith("|") or s.startswith("|---"):
        return False
    hucreler = [c.strip() for c in s.strip("|").split("|")]
    if not hucreler:
        return False
    c0 = re.sub(r"[*_`]+", "", hucreler[0]).strip().lower()
    return c0 in _META_CELL0 or bool(_DOC_REF_CELL0.search(hucreler[0]))

_LOG_HEADING = re.compile(r"karar", re.IGNORECASE)
# "açık(?!lama)": "Açıklama" içeren bir GÖVDE başlığı (ör. "4.3 Karar Kuralları ve
# Açıklamaları") eskiden katman-2 sayılıp BÖLÜM BOYU taranmıyordu (sessiz FN deliği).
_LOG_HEADING2 = re.compile(r"günlü|açık(?!lama)|öneri|11-A|11-B", re.IGNORECASE)


def _iter_docs(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d.lower() not in _SKIP]
        if Path(dirpath).name.lower() != "docs":
            continue
        for fn in filenames:
            low = fn.lower()
            if low.endswith(".md") and (low.startswith("fs-") or low.startswith("ek-")):
                yield Path(dirpath) / fn


def _is_log_heading(h: str) -> bool:
    return bool(_LOG_HEADING.search(h) and _LOG_HEADING2.search(h)) or "11-A" in h or "11-B" in h


def scan_text(text: str):
    """→ (findings: {cls: [(lineno, snippet)]}, version_rows_too_long: [(lineno, len)], body_lines: int)"""
    lines = text.splitlines()
    findings = {k: [] for k in PATTERNS}
    long_rows = []
    ic_tanimli = _belge_ici_tanimli(lines)
    # Dosyanın kendisi katman-2 ise (EK "Karar ve Kanıt Günlüğü": H1'de "karar" + "günlü") tamamı atlanır.
    for ln in lines[:15]:
        if ln.startswith("# ") and _is_log_heading(ln):
            return findings, long_rows, 0
    in_log = False
    in_version = False
    in_vtable = False          # başlıksız §1.1 tablosu (tablo BAŞLIK SATIRINDAN tanınır)
    in_code = False
    body_lines = 0
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if s.startswith("#"):
            h = s.lstrip("#").strip()
            level = len(s) - len(s.lstrip("#"))
            if level <= 3:
                in_version = bool(re.match(r"1\.1\b", h)) or "versiyon geçmişi" in h.lower()
                in_log = _is_log_heading(h) and not in_version
            in_vtable = False
            # doc-gate v2.0: BAŞLIK satırları da gövdedir — "## 6. ETKİLENEN OBJELER
            # (canlı-doğrulanmış …)" gibi süreç izleri başlıkta saklanıyordu ve gate
            # onları HİÇ görmüyordu (satır `continue` ile atlanıyordu).
            if not in_log and not in_version and not in_code and level > 1:
                # level 1 = belgenin KENDİ başlığı (katman-0 kimlik: "# FS-SD-014 v2.0 — …")
                body_lines += 1
                for k, rx in PATTERNS.items():
                    if rx.search(ln):
                        findings[k].append((i, s[:110]))
            continue
        if in_version:
            if s.startswith("|") and not s.startswith("|---") and "Versiyon" not in s and len(s) > VERSION_ROW_MAX:
                long_rows.append((i, len(s)))
            continue
        if not s:
            # ⚠ DURUM SIZMASI: boş satır tabloyu KAPATIR. Aksi hâlde versiyon tablosundan
            # sonra gelen (boş satırla ayrılmış) SONRAKİ tablolar da §1.1 sanılır ve
            # bölüm bölüm taranmadan geçer — ölçüldü: canlı korpus 168 → 73 işarete
            # düşmüştü (sahte temizlik). Sessiz FN, en pahalı kusur tipi.
            in_vtable = False
        if in_log or in_code or not s:
            continue
        if s.startswith("|"):
            if _VTABLE_HEADER.match(s):
                in_vtable = True
                continue
        else:
            in_vtable = False
        if in_vtable:                        # başlıksız versiyon tablosunun satırları = §1.1
            if not s.startswith("|---") and len(s) > VERSION_ROW_MAX:
                long_rows.append((i, len(s)))
            continue
        if _metadata_satiri(s) or _DOC_FOOTER.match(s):
            # katman-0: belgenin kendi kimlik bilgisi. Uzunluk ölçütü YİNE uygulanır —
            # yoksa "anlatıyı kapak satırına taşı" diye bir kaçış yolu açılırdı.
            if len(s) > VERSION_ROW_MAX:
                long_rows.append((i, len(s)))
            continue
        body_lines += 1
        for k, rx in PATTERNS.items():
            if not rx.search(ln):
                continue
            if k == "B gate-bulgu ID" and "doc-gate" not in ln.lower():
                bulunan = set(_B_TOKEN.findall(ln))
                if bulunan and bulunan <= ic_tanimli:
                    continue                 # belgenin KENDİ tanımladığı ID'ye atıf
            findings[k].append((i, s[:110]))
    return findings, long_rows, body_lines


def _report(path, findings, long_rows, body_lines, max_examples):
    total = sum(len(v) for v in findings.values())
    if total == 0 and not long_rows:
        return 0
    try:                                 # str-prefix kıyası KOMŞU dizini de eşler
        rel = path.relative_to(REPO)     # (…/Proje2 vs …/Proje) → relative_to ValueError
    except Exception:                    # atardı: çökme "bulgu yok" gibi okunuyordu
        rel = path
    print(f"[WARN] {rel}: gövde {body_lines} satır — analiz-günlüğü işareti {total} satır"
          + (f" · §1.1 uzun satır {len(long_rows)}" if long_rows else ""))
    for k, v in findings.items():
        if not v:
            continue
        print(f"    {k}: {len(v)}")
        for ln, sn in v[:max_examples]:
            print(f"       :{ln}  {sn}")
    for ln, L in long_rows[:max_examples]:
        print(f"    §1.1 :{ln}  {L} karakter (> {VERSION_ROW_MAX}) — 1-2 satıra indir, gerekçeyi EK'e")
    return total + len(long_rows)


RED_FIXTURE = """# FS-XX-999 Örnek
## BÖLÜM 1: DÖKÜMAN KONTROLÜ
### 1.1 Versiyon Geçmişi
| Versiyon | Tarih | Hazırlayan | Açıklama |
|---|---|---|---|
| 1.5-taslak | 01.01.2026 | X | """ + ("uzun anlatı " * 60) + """ |
### 1.2 Dağıtım
| a | b |
## BÖLÜM 3: SÜREÇ
Fatura tipi ZM12 (R-22 — DEV TVAK canlı ölçüm: FKARV=ZM12; ilk turda alan adı yanlış yazılmıştı, 400 döndü).
| C4 | (**YENİ, R-26**) Kontrol Et butonu (doc-gate v1.5 H-C netleşme) |
Kullanıcı: "fiyat koşulumuz Z001 olmalı" — kullanıcı notu 17.08.
Müşteri Malzeme No artık kalem satırında gösterilmez (R-6 revizyonu).
Hata kodu L-01 ve M-02 burada meşru hata kodudur (yakalanmamalı).
Bakiye artık sayılmaz; bölünmeyen artık miktar hesaba katılır (yakalanmamalı).
## BÖLÜM 11-B: AÇIK KARARLAR / SORU SETİ
| S-19 | v1.7'de eklendi, doc-gate M-2 | (burası katman-2, sayılmaz) |
"""


def selftest() -> int:
    f, lr, _ = scan_text(RED_FIXTURE)
    ok = True
    f2, lr2, bl2 = scan_text("# EK-B — Karar ve Kanıt Günlüğü\n\n## R-22\n(doc-gate v1.5 H-C) canlı ölçüldü, kullanıcı: \"x\"\n")
    if sum(len(v) for v in f2.values()) or lr2 or bl2:
        print("[SELFTEST-FAIL] katman-2 dosyası (Karar ve Kanıt Günlüğü) taranmamalıydı"); ok = False
    exp = {"A sürüm-etiketi": 1, "B gate-bulgu ID": 1, "C süreç ifadesi": 1,
           "D kullanıcı alıntı": 1, "E önceden→şimdi": 1}
    for k, n in exp.items():
        if len(f[k]) < n:
            print(f"[SELFTEST-FAIL] {k}: beklenen ≥{n}, bulunan {len(f[k])}"); ok = False
    if any("L-01" in sn or "M-02" in sn for k in ("B gate-bulgu ID",) for _, sn in f[k]):
        print("[SELFTEST-FAIL] hata kodu L-01/M-02 gate-ID sanıldı"); ok = False
    if any("Bakiye artık sayılmaz" in sn for k in f for _, sn in f[k]):
        print("[SELFTEST-FAIL] iş cümlesindeki 'artık' önceden→şimdi sanıldı"); ok = False
    if any(ln > 15 for k in f for ln, _ in f[k]):
        print("[SELFTEST-FAIL] 11-B (katman-2) satırı gövde sayıldı"); ok = False
    if not lr:
        print("[SELFTEST-FAIL] §1.1 uzun satır yakalanmadı"); ok = False
    print("[SELFTEST] " + ("OK — kırmızı fixture yakalandı, meşru kodlar/katman-2 atlandı" if ok else "FAIL"))
    return 0 if ok else 1


def main() -> int:
    argv = sys.argv[1:]
    if "--selftest" in argv:
        return selftest()
    # "--strict" run_all_validators uyumu için KABUL EDİLİR ama NO-OP'tur (yukarıdaki
    # sözleşme); bulguda exit 1 yalnız hook'un kullandığı ayrı bayrakla gelir.
    bulguda_exit1 = "--bulguda-exit1" in argv
    max_examples = 3
    if "--max-examples" in argv:
        try:
            max_examples = int(argv[argv.index("--max-examples") + 1])
        except (IndexError, ValueError):
            print("[HATA] --max-examples sayısal bir değer ister."); return 2
    single = None
    if "--file" in argv:                       # tek doküman (post_validate edit-anı nudge'ı)
        i_f = argv.index("--file") + 1
        if i_f >= len(argv):
            print("[HATA] --file için yol verilmedi."); return 2
        single = Path(argv[i_f])
    total = 0
    n_docs = 0
    okunamadi = 0
    for p in ([single] if single else _iter_docs(REPO)):
        n_docs += 1
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            # FAIL-CLOSED (sınıf: "DOĞRULAMA KOŞAMADI != DOĞRULANDI"): okunamayan dosya
            # eskiden sessizce atlanıyor ve alttaki "temiz" satırı basılıyordu — gate
            # ölçmediği bir dosya için TEMİZ diyordu (hook da sessiz kalıyordu).
            print(f"[ÖLÇÜLEMEDİ] {p}: okunamadı ({e.__class__.__name__}: {e}) — "
                  "bu 'temiz' ANLAMINA GELMEZ.")
            okunamadi += 1
            continue
        f, lr, bl = scan_text(text)
        total += _report(p, f, lr, bl, max_examples)
    if okunamadi:
        print(f"Özet: {okunamadi} doküman OKUNAMADI (ölçüm eksik) — exit 2.")
        return 2
    if total == 0:
        print(f"FS analiz-günlüğü kontrolü (DOC-FS-05/06): temiz — {n_docs} FS/EK dokümanı, gövdede işaret yok.")
        return 0
    print()
    print(f"Özet: {total} işaretli satır ({n_docs} doküman). Kural: gövde = kapanmış hedef durum; sürüm etiketi/"
          "gate-ID/süreç ifadesi/kullanıcı alıntısı → EK 'Karar ve Kanıt Günlüğü' (std 04 §2.0 İLKE-2b).")
    print("Warn-first (ADR 0019): bloklamaz — hard'a terfi shakeout sonrası, AYRI kararla "
          "(--strict bu gate'te NO-OP).")
    return 1 if bulguda_exit1 else 0


if __name__ == "__main__":
    sys.exit(main())
