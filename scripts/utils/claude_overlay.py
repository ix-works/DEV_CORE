#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`.claude/{agents,skills,commands}` için PROJE-LOKAL overlay kanalı.

SORUN (2026-07-09 denetimi): bu üç dizin core'a junction'dır. Claude Code proje-seviyesi
agent/skill/command'ı YALNIZ bu dizinlerden okur → **proje-özel agent tanımlanamıyordu.**
Sonuç: core'daki jenerik tanımlar projeye dayatılıyor ve genericize sırasında proje
gerçekleri placeholder'a dönüyor (ör. `backend-expert.md`: gerçek bir örnek obje yerine
var olmayan bir ad). "Tahmin yasak" diyen sistem, ajanı tahmine itiyordu.

ÇÖZÜM — OPT-IN overlay:
    <proje>/claude-local/agents/*.md   (COMMIT'Lİ, proje reposunda)
Bu dizin varsa `team_setup` `.claude/agents`'ı **junction yerine gerçek dizin** olarak
üretir: core dosyaları + üzerine proje dosyaları (aynı ad = override).
Yoksa hiçbir şey değişmez — junction kalır (sıfır blast radius).

GÜVENLİK: `.claude/{agents,skills,commands}/` zaten `.gitignore`'da (R1 sızıntı kilidi,
`check_core_not_committed` zorlar) → üretilen core kopyası proje reposuna GİRMEZ.

DRIFT: overlay manifest'i, override edilen her dosyanın **core'daki hash'ini** saklar.
Core güncellenince `check_claude_overlay` uyarır: "core değişti, overlay'i gözden geçir".
Böylece overlay sessizce bayatlamaz.

EZME KAPISI (T2.5) ayrı bir sorudur ve ayrı bir tabanı vardır: manifest her dosyanın
**üretildiği andaki hash'ini** (`uretilen_hash`) de saklar. `fark_raporu` kopyanın
ŞİMDİKİ hâlini bununla kıyaslar → "core değişti" ile "kopya elle düzeltildi" ayrışır.
(2026-08-13 kök-fix'i; gerekçe `fark_raporu` docstring'inde.)

OTOMATİK TAZELEME (`oto_tazele`, 2026-08-13 ikinci yarı): yukarıdaki taban "fark yok"
diyebildiği İÇİN senkron artık kullanıcı komutuna bağlı değildir — `session_start`
her açılışta çağırır, fark boşsa kopyayı sessizce DEĞİL, **tek görünür satırla** tazeler.
Ölçülmüş sınır: ajan tanımları oturum başında okunur ⇒ tazeleme **bir sonraki oturumdan**
itibaren etkilidir (kanıt: `oto_tazele` docstring'i).

ATOMİKLİK (2026-08-27, Q30): HİÇBİR yol dizini silip yeniden kurmaz. `materyalize` de
`_yerinde_senkron` de "üzerine yaz → fazlalığı tek tek sil → manifest en son → öz-denetle"
sırasını izler. Gerekçe `materyalize` docstring'inde (ölçülmüş kayıp vakası).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

# Otomatik tazelemeyi kapatan acil-fren (F5 geri-alma yolu): "0"/"false" ⇒ eski davranış
# (yalnız raporla, dokunma). Kapalıyken SESSİZDİR — kullanıcı bilerek kapatmıştır.
OTO_ENV = "IX_OVERLAY_OTO"

# "rules" 2026-07-10'da eklendi (L1b glob-tetiklemeli davranış kuralları). Junction'lanmazsa
# yeni projede `.claude/rules` HİÇ kurulmaz → kural yazılır ama hiç yüklenmez (kod≠kablolama).
TIPLER = ("agents", "skills", "commands", "rules")
MANIFEST_ADI = ".overlay-manifest.json"
DAMGA = "<!-- CORE-URETILDI: elle duzenleme; kaynak core/claude/{tip}/{ad} -->\n"

# ⚠ Agent/skill/command dosyaları YAML frontmatter ile BAŞLAMAK ZORUNDADIR (`---`).
# İlk sürümde damga frontmatter'ın ÖNÜNE konmuştu → 6/6 agent yüklenemez oldu ve harness
# "agent types no longer available" dedi. Dosya SAYISI doğruydu, FORMAT bozuktu; içerik
# saymak yetmiyor. Damga artık frontmatter'dan SONRA girer, dosyalar LF yazılır.
_FRONTMATTER = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n", re.S)


def _hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def _junction_mu(p: Path) -> bool:
    try:
        return p.is_dir() and os.path.realpath(p) != os.path.abspath(p)
    except OSError:
        return False


def _damgala(icerik: str, damga: str) -> str:
    """Damgayı frontmatter'dan SONRA yerleştir — dosya `---` ile başlamalı."""
    m = _FRONTMATTER.match(icerik)
    if m:
        return icerik[:m.end()] + damga + icerik[m.end():]
    return damga + icerik          # frontmatter yoksa (command dosyaları) başa


def frontmatter_ile_basliyor(p: Path) -> bool:
    """Agent/skill dosyası `---` ile mi başlıyor? (yüklenebilirlik ön koşulu)"""
    try:
        with p.open("r", encoding="utf-8", errors="replace") as f:
            return f.readline().strip() == "---"
    except OSError:
        return False


def overlay_kaynagi(proje: Path, tip: str) -> Path:
    return proje / "claude-local" / tip


def overlay_var_mi(proje: Path, tip: str) -> bool:
    k = overlay_kaynagi(proje, tip)
    return k.is_dir() and any(k.glob("*.md"))


def hedef(proje: Path, tip: str) -> Path:
    return proje / ".claude" / tip


def _beklenen(proje: Path, core_root: Path, tip: str) -> dict:
    """Üretilecek dosya kümesi: {ad: (kaynak_yolu, core_hash|None)}"""
    out: dict = {}
    core_dizin = core_root / "claude" / tip
    if core_dizin.is_dir():
        for f in sorted(core_dizin.glob("*.md")):
            out[f.name] = (f, _hash(f))
    for f in sorted(overlay_kaynagi(proje, tip).glob("*.md")):
        core_esi = core_dizin / f.name
        out[f.name] = (f, _hash(core_esi) if core_esi.is_file() else None)
    return out


def _uretilecek_icerik(proje: Path, tip: str, ad: str, kaynak: Path) -> str:
    """Bir dosyanın ÜRETİLECEK hâli (damga dahil) — `materyalize`'in TEK kaynağı.

    `tazeleme_gerekli()` "bayat mı" sorusunu bununla cevaplar. Ayrı bir kopya-mantık
    yazılsaydı iki taraf sessizce ayrışabilirdi: yordam "taze" derken üretici başka
    bayt yazar (= her açılışta kendini tetikleyen sonsuz tazeleme, ya da hiç tetiklenmeyen
    ölü kontrol). Tek fonksiyon = tanım gereği tutarlı.
    """
    icerik = kaynak.read_text(encoding="utf-8", errors="replace")
    if kaynak.parent == overlay_kaynagi(proje, tip):
        return icerik                       # proje-lokal dosya damgalanmaz
    return _damgala(icerik, DAMGA.format(tip=tip, ad=ad))


def _yaz(hedef_dosya: Path, icerik: str) -> None:
    """newline="\\n" ŞART: varsayılan (None) Windows'ta CRLF yazar → frontmatter satırları
    `---\\r\\n` olur ve bazı parser'lar bozulur; ayrıca sahte diff üretir."""
    hedef_dosya.write_text(icerik, encoding="utf-8", newline="\n")


def _norm(icerik: str) -> str:
    """Damga satırı + satır-sonu normalizasyonu (fark kıyası için)."""
    satirlar = [s for s in icerik.replace("\r\n", "\n").split("\n")
                if not s.startswith("<!-- CORE-URETILDI")]
    return "\n".join(satirlar).strip()


def _manifest_dosyalari(h: Path) -> dict:
    """`.overlay-manifest.json` → {ad: kayit}. Okunamazsa BOŞ (kanıt yok = muhafazakâr dal)."""
    try:
        return json.loads((h / MANIFEST_ADI).read_text(encoding="utf-8")).get("dosyalar", {})
    except Exception:
        return {}


def _uretildigi_gibi(mevcut: Path, kayit) -> bool:
    """Kopya, EN SON ÜRETİLDİĞİ hâlde mi (bayt-bayt)?

    Bu, fark kıyasının TABANIDIR. `uretilen_hash` yoksa (2026-08-13 öncesi manifest)
    kanıt da yoktur → False döner ve çağıran bugünkü muhafazakâr içerik-kıyasına düşer.
    Sessiz gevşeme olmaz: eski manifestli projeler birebir eski davranışı görür.
    """
    beklenen = (kayit or {}).get("uretilen_hash")
    if not beklenen:
        return False
    try:
        return _hash(mevcut) == beklenen
    except OSError:
        return False


def fark_raporu(proje: Path, core_root: Path, tip: str) -> list:
    """T2.5 (2026-07-31): senkron ÖNCESİ fark raporu — senkronun EZECEĞİ proje emeği
    var mı? Boş liste = güvenli; dolu liste = önce terfi/claude-local kararı ver.

    KIYAS TABANI = kopya-ŞİMDİ ↔ en son ÜRETİLEN (manifest `uretilen_hash`).
    ⚠ 2026-08-13 kök-fix'i: taban eskiden "bugün üretilecek içerik"ti. O taban, ELLE
    DÜZELTME ile CORE GÜNCELLEMESİNİ ayırt edemiyordu → core'da bir ajan dosyası
    değiştiği an, projede hiçbir elle düzeltme olmasa bile kapı kapanıyordu (kurt
    masalı). Bedeli iki katmanlıydı: (a) junction'lı tipler bedavaya tazelenirken
    overlay'li tip her core commit'inde tören istiyordu; (b) `--overlay-onayli` refleks
    hâline gelince gerçek bir elle düzeltmeyi SESSİZCE ezecekti — yani kapı kendi
    koruduğu şeyi aşındırıyordu. Doğru soru "içerik core'dan farklı mı" değil,
    **"kopyaya senkrondan sonra dokunuldu mu"**dur.
    """
    h = hedef(proje, tip)
    if not h.is_dir() or _junction_mu(h):
        return []
    beklenen = _beklenen(proje, core_root, tip)
    kayitlar = _manifest_dosyalari(h)
    farklar = []
    for ad, (kaynak, _ch) in beklenen.items():
        mevcut = h / ad
        if not mevcut.is_file():
            continue  # yeni dosya — ezme değil ekleme
        if _uretildigi_gibi(mevcut, kayitlar.get(ad)):
            continue  # el değmemiş üretim artığı: kaynak değişmiş olabilir, KAYIP yok
        if _norm(mevcut.read_text(encoding="utf-8", errors="replace")) != \
           _norm(kaynak.read_text(encoding="utf-8", errors="replace")):
            farklar.append(f"{tip}/{ad}: mevcut kopya, üretilecek içerikten FARKLI "
                           f"(elle düzeltme olabilir → önce core'a terfi ya da claude-local'e al)")
    for f in sorted(h.glob("*.md")):
        if f.name in beklenen:
            continue
        # Aynı sınıfın ikinci yüzü: core bir dosyayı SİLDİYSE, el değmemiş kopyanın
        # silinmesi zaten doğru sonuçtur (junction'da bedavaya olur). Yalnız manifest
        # onu core-üretimi diye tanıyor VE bayt-bayt el değmemişse sessizce geç.
        kayit = kayitlar.get(f.name) or {}
        if kayit.get("kaynak") == "core" and _uretildigi_gibi(f, kayit):
            continue
        farklar.append(f"{tip}/{f.name}: üretim kümesinde YOK — senkronda SİLİNİR")
    return farklar


def materyalize(proje: Path, core_root: Path, tip: str, onayli: bool = False) -> tuple:
    """`.claude/<tip>`'i gerçek dizin olarak üret (core + overlay). -> (ok, mesaj)
    onayli=False iken mevcut kopyalarda fark varsa ÜRETMEZ (fark-onay kapısı, T2.5).

    ⚠⚠ 2026-08-27 (Q30) — **YIKIM YOK, YERİNDE ÜRETİM.** Eski gövde dizini
    `shutil.rmtree` ile SİLİP yeniden kuruyordu ve bu "kabul edilebilir pencere"
    sayılmıştı (2026-08-13 kararı, `_yerinde_senkron` docstring'i). **Ölçülmüş vaka o
    varsayımı çürüttü:** `rmtree` içerideki 7 ajan tanımını sildi, sonra DİZİNİN
    KENDİSİNİ silerken `PermissionError [WinError 5]` aldı (Windows'ta dizin üstünde
    dışarıdan tutulan anlık bir handle — bu makinede repo kökü bir Drive senkron klasörü altında ve
    `GoogleDriveFS`/Defender/indeksleyici canlı). İstisna `mkdir`+yazma satırlarına
    gelinmesini engelledi ⇒ `.claude/agents` **BOŞ** kaldı; `.gitignore`'lu olduğu için
    `git status` sustu, `git checkout` geri getiremezdi. Kayıp yaptırımlı rollerdi
    (adt-gateway = tek SAP yazıcısı, bug-expert = BUG GATE).

    Kök: yıkım ile inşa AYRI adımlardı ve **arada dizin boş kalıyordu**. Tetik (dış
    handle) ortadan kaldırılamaz; dayanıklılık koda konur. Yeni sıra `_yerinde_senkron`
    ile aynıdır: ① üzerine YAZ (dizin hiç silinmez) ② beklenen kümede olmayanı TEK TEK
    sil ③ manifest EN SON ④ son-durumu ÖZ-DENETLE. En kötü hâlde eski + yeni karışımı
    kalır — **hiçbir noktada boş kalmaz.**

    ⛔ `_yerinde_senkron` ile BİLEREK ayrı tutuldu (birleştirme = `oto_tazele` çağrı
    zincirine `materyalize` sokar, `overlay_oto_tazeleme` V22 AST çapası KIRMIZI verir).
    Semantik de ayrıdır: otomatik yol fazlalığı yalnız KANITLA siler (`kaynak == "core"`
    + el değmemiş), elle yol `fark_raporu`'nun ilan ettiği gibi ("senkronda SİLİNİR")
    kayıtsız siler — üstündeki onay kapısı bunun için vardır.
    """
    if not overlay_var_mi(proje, tip):
        return False, f"overlay yok: {overlay_kaynagi(proje, tip)}"

    if not onayli:
        farklar = fark_raporu(proje, core_root, tip)
        if farklar:
            return False, ("FARK VAR — onaysız ezme YOK (T2.5):\n    "
                           + "\n    ".join(farklar)
                           + "\n    Karar ver (terfi/claude-local) → sonra --overlay-onayli ile koş.")

    # KANIT KAPISI — `oto_tazele`'nin V7 çapasının ELLE-YOL eşi. Core tarafı okunamıyorsa
    # (junction kopuk / dizin boş) "üretilecek küme" core dosyalarını İÇERMEZ ⇒ üretim
    # onları FAZLALIK sayıp silerdi. Üstelik `team_setup.py` tam da kopuk junction'ı
    # onarmak için koşulan komuttur: koruma en çok orada gerek.
    core_dizin = core_root / "claude" / tip
    if not core_dizin.is_dir() or not any(core_dizin.glob("*.md")):
        return False, (f"{tip}: core/claude/{tip} okunamadi (junction kopuk? dizin bos?) — "
                       f"uretim mevcut kopyalari SILERDI, DOKUNULMADI")

    h = hedef(proje, tip)
    if _junction_mu(h):
        try:
            os.rmdir(h)                 # junction'ı kaldır (hedefe DOKUNMAZ)
        except OSError as exc:
            return False, (f"{tip}: junction kaldirilamadi ({type(exc).__name__}: {exc}) — "
                           f"hicbir sey degistirilmedi")
    try:
        h.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, f"{tip}: dizin acilamadi ({type(exc).__name__}: {exc})"

    beklenen = _beklenen(proje, core_root, tip)

    # ① ÜZERİNE YAZ — silme YOK. Tek dosya yazılamazsa diğerleri yerinde kalır.
    yazilamayan = []
    for ad, (kaynak, _ch) in beklenen.items():
        try:
            _yaz(h / ad, _uretilecek_icerik(proje, tip, ad, kaynak))
        except OSError as exc:
            yazilamayan.append(f"{ad} ({type(exc).__name__})")

    # ② FAZLALIKLARI TEK TEK SİL (dizin silme YOK). `.md` dışı dosyalara dokunulmaz —
    # eski `rmtree` onları da siliyordu; bilinmeyen dosyayı kanıtsız silmektense
    # GÖRÜNÜR kılmak seçildi (mesajda listelenir).
    silinemeyen, yabanci = [], []
    for f in sorted(h.iterdir()):
        if f.name in beklenen or f.name == MANIFEST_ADI or not f.is_file():
            continue
        if f.suffix != ".md":
            yabanci.append(f.name)
            continue
        try:
            f.unlink()
        except OSError as exc:
            silinemeyen.append(f"{f.name} ({type(exc).__name__})")

    # ③ MANİFEST EN SON (yarıda kesilirse tutarlı bir geçmişi anlatmaya devam eder)
    manifest = {"tip": tip, "dosyalar": {}}
    for ad, (kaynak, core_hash) in beklenen.items():
        if not (h / ad).is_file():
            continue                    # yazılamadı → kayıt uydurma
        manifest["dosyalar"][ad] = {
            "kaynak": "proje" if kaynak.parent == overlay_kaynagi(proje, tip) else "core",
            "core_hash": core_hash,       # override edilen core dosyasının hash'i (drift için)
            # ÜRETİLEN hâlin hash'i = fark_raporu'nun KIYAS TABANI (2026-08-13).
            # Damga + LF normalizasyonu SONRASI, yani diskteki gerçek bayt: kıyas
            # "yeniden üretsem ne çıkardı" tahminine değil, ölçüme dayansın.
            "uretilen_hash": _hash(h / ad),
        }
    try:
        (h / MANIFEST_ADI).write_text(json.dumps(manifest, indent=1, ensure_ascii=False),
                                      encoding="utf-8")
    except OSError as exc:
        yazilamayan.append(f"{MANIFEST_ADI} ({type(exc).__name__})")

    # ④ SON-DURUM ÖZ-DENETİMİ — "SAYI ≠ YÜKLENEBİLİRLİK" (2026-07-09: damga frontmatter'ın
    # ÖNÜNE girmişti, dosya sayısı doğruydu, 6/6 ajan yüklenemiyordu ve sistem "güncel"
    # diyordu). Üretim kendi çıktısını ölçmeden BAŞARILI demez.
    eksik = sorted(ad for ad in beklenen if not (h / ad).is_file())
    bozuk = sorted(ad for ad in beklenen
                   if tip in ("agents", "skills") and (h / ad).is_file()
                   and not frontmatter_ile_basliyor(h / ad))

    n_proje = sum(1 for v in manifest["dosyalar"].values() if v["kaynak"] == "proje")
    mesaj = f"{tip}: {len(manifest['dosyalar'])}/{len(beklenen)} dosya ({n_proje} proje-lokal override)"
    if yabanci:
        mesaj += f" · .md DISI, dokunulmadi: {yabanci}"
    if silinemeyen:
        mesaj += f" · SILINEMEDI: {silinemeyen}"
    if yazilamayan or eksik or bozuk:
        return False, (mesaj + f" · ⛔ URETIM EKSIK — yazilamayan={yazilamayan} "
                       f"eksik={eksik} frontmatter-bozuk={bozuk}. "
                       f"{hedef(proje, tip)} ELDEN GECIRILMELI: bu dizin harness'in "
                       f"{tip} tanimlarini okudugu YERDIR; eksik/bozuk dosya = o rol YOK.")
    return True, mesaj


def tazeleme_gerekli(proje: Path, core_root: Path, tip: str) -> list:
    """Kopya kümesi BUGÜN üretilecek olandan farklı mı? -> farklı/eksik/fazla dosya adları.

    "Bayat mı" sorusunun tek cevabı budur ve `fark_raporu`'ndan AYRI bir sorudur:
      · `tazeleme_gerekli` → **ne değişti** (kaynak tarafı; iş var mı?)
      · `fark_raporu`      → **ne kaybolur** (kopya tarafı; dokunmak güvenli mi?)
    İkisi karıştırılırsa ya hiç tetiklenmeyen ölü otomatik ya da proje emeğini ezen
    bir otomatik çıkar. Boş liste = yapılacak iş yok (sessiz no-op).
    """
    h = hedef(proje, tip)
    if not h.is_dir() or _junction_mu(h):
        return []
    beklenen = _beklenen(proje, core_root, tip)
    fark = []
    for ad, (kaynak, _ch) in beklenen.items():
        mevcut = h / ad
        try:
            if not mevcut.is_file():
                fark.append(ad)
            elif mevcut.read_bytes() != _uretilecek_icerik(proje, tip, ad, kaynak).encode("utf-8"):
                fark.append(ad)
        except OSError:
            fark.append(ad)
    fark += [f.name for f in sorted(h.glob("*.md")) if f.name not in beklenen]
    return sorted(set(fark))


def _manifest_alansiz(proje: Path, tip: str) -> bool:
    """Manifest 2026-08-13 ÖNCESİ mi (dosya kaydında `uretilen_hash` yok)?

    Bu projeler `fark_raporu`'nun muhafazakâr içerik-kıyasına düşer: core bir dosyayı
    değiştirdiği an kapı kapanır (kurt masalı sürer). Alan yalnız `materyalize` ile
    dolar; kopyalar zaten üretileceğin AYNISIYSA bu, içerik değiştirmeyen bir kayıt
    tazelemesidir — otomatik yapılabilir ve yayılım adımı kendiliğinden kapanır.
    """
    kayitlar = _manifest_dosyalari(hedef(proje, tip))
    if not kayitlar:
        return True
    return any(not k.get("uretilen_hash") for k in kayitlar.values())


def _yerinde_senkron(proje: Path, core_root: Path, tip: str) -> tuple:
    """`materyalize`'in ATOMİK-OLMAYAN penceresi olmadan senkron. -> (ok, mesaj)

    ⚠ TARİHSEL: bu fonksiyon 2026-08-13'te AYRI yazıldı çünkü `materyalize` o gün dizini
    `shutil.rmtree` ile SİLİP yeniden kuruyordu; o pencere "elle/seyrek koşarken kabul
    edilebilir" sayılmış, yalnız otomatik yola kısıt konmuştu. **2026-08-27 (Q30) o
    varsayım ÖLÇÜMLE ÇÜRÜDÜ** (rmtree yarıda kaldı, `.claude/agents` boşaldı) ve
    `materyalize` de yerinde üretime çevrildi. İki fonksiyon YİNE DE ayrıdır: (a)
    `overlay_oto_tazeleme` V22 AST çapası `oto_tazele` zincirinde `materyalize` görmemeli,
    (b) silme semantiği farklı — burada fazlalık yalnız KANITLA silinir, `materyalize`'de
    onay kapısının arkasında kayıtsız silinir.

    Bu yüzden otomatik yol: ① beklenen dosyaları ÜZERİNE yaz (dizin hiç silinmez)
    ② beklenen kümede olmayanları TEK TEK sil — yalnız kanıt varsa (`kaynak == "core"` VE
    üretildiği gibi); kanıtsız dosya KORUNUR ve mesajda görünür ③ manifest'i EN SON yaz
    (yarıda kesilirse manifest tutarlı bir geçmişi anlatmaya devam eder).

    ⛔ ARTIK GEÇERSİZ: *"`materyalize` DEĞİŞMEDİ, kısıt yalnız otomatik yola kondu"* —
    2026-08-27'de (Q30) elle yol da yerinde üretime çevrildi; ikisinin de yıkım penceresi
    YOK. Fark yalnız silme-kanıtı eşiğindedir (yukarı bkz).
    """
    farklar = fark_raporu(proje, core_root, tip)
    if farklar:                       # ikinci savunma katmanı (çağıranın kontrolünden bağımsız)
        return False, "FARK VAR — yerinde senkron da onaysiz EZMEZ (T2.5): " + "; ".join(farklar)

    h = hedef(proje, tip)
    beklenen = _beklenen(proje, core_root, tip)
    kayitlar = _manifest_dosyalari(h)

    for ad, (kaynak, _ch) in beklenen.items():
        icerik = _uretilecek_icerik(proje, tip, ad, kaynak)
        mevcut = h / ad
        if not mevcut.is_file() or mevcut.read_bytes() != icerik.encode("utf-8"):
            _yaz(mevcut, icerik)      # üzerine yaz — silme yok

    korunan = []
    for f in sorted(h.glob("*.md")):
        if f.name in beklenen:
            continue
        kayit = kayitlar.get(f.name) or {}
        if kayit.get("kaynak") == "core" and _uretildigi_gibi(f, kayit):
            f.unlink()                # tek tek: yalnız el değmemiş core artığı
        else:
            korunan.append(f.name)    # kanıt yok → dokunma (fail-safe; kapı zaten elerdi)

    manifest = {"tip": tip, "dosyalar": {}}
    for ad, (kaynak, core_hash) in beklenen.items():
        manifest["dosyalar"][ad] = {
            "kaynak": "proje" if kaynak.parent == overlay_kaynagi(proje, tip) else "core",
            "core_hash": core_hash,
            "uretilen_hash": _hash(h / ad),
        }
    (h / MANIFEST_ADI).write_text(json.dumps(manifest, indent=1, ensure_ascii=False),
                                  encoding="utf-8")          # EN SON
    n_proje = sum(1 for v in manifest["dosyalar"].values() if v["kaynak"] == "proje")
    mesaj = f"{tip}: {len(beklenen)} dosya ({n_proje} proje-lokal override)"
    if korunan:
        mesaj += f" · KANITSIZ, silinmedi: {korunan}"
    return True, mesaj


def oto_tazele(proje: Path, core_root: Path) -> list:
    """Overlay'li tipleri KULLANICI KOMUTU OLMADAN taze tut. -> görünür satırlar.

    KOŞUL (müzakere edilemez): yalnız `fark_raporu(...) == []` iken üretir. Dolu liste =
    kopyada elle düzeltme var ⇒ DOKUNMAZ, kararı insana bırakır (T2.5 kapısı aynen
    yürürlükte — `materyalize` `onayli=False` ile çağrılır, yani kapı bu yolda da açık).

    SESSİZ DEĞİL: her tazeleme/atlama/başarısızlık bir satır döndürür (`session_start`
    bunu oturum açılışına basar). Yapılacak iş yoksa hiçbir şey döndürmez (gürültü yok).

    ⚠ ÖLÇÜLMÜŞ SINIR — "bu oturumda etkili" DEĞİL. Ajan tanımları oturum başında
    okunur; SessionStart hook'unun yazdığı dosya O oturuma yansımaz. 2026-08-13'te
    canlı harness'ta 3 koşumla ölçüldü: (1) hook oturum sırasında yeni bir ajan dosyası
    yazdı → o oturumun subagent_type listesinde YOK; (2) bir SONRAKİ oturumda VAR;
    (3) en sert vaka — hook mevcut bir ajanın İÇERİĞİNİ değiştirdi, aynı oturumda o
    ajan spawn edildi ve ESKİ içerikle davrandı (disk yeniyken). Dolayısıyla vaat
    "artık hiç komut koşmayacaksın"dır, "anında güncellenir" değil. Junction'lı tipler
    de aynı oturum-başı okuma kuralına tabidir ⇒ davranış PARİTE.

    Kapatma: `IX_OVERLAY_OTO=0` (F5 geri-alma yolu).
    """
    if os.environ.get(OTO_ENV, "1").strip().lower() in ("0", "false", "no"):
        return []
    satirlar = []
    for tip in TIPLER:
        try:
            if not overlay_var_mi(proje, tip):
                continue                      # junction'lı/overlay'siz proje → hiç dokunma
            h = hedef(proje, tip)
            if not h.is_dir() or _junction_mu(h):
                continue                      # henüz materyalize edilmemiş: kurulum işi (team_setup)
            core_dizin = core_root / "claude" / tip
            if not core_dizin.is_dir() or not any(core_dizin.glob("*.md")):
                # Core tarafı OKUNAMIYOR (junction kopuk / dizin boş). Bu durumda
                # "üretilecek küme" core dosyalarını İÇERMEZ ⇒ otomatik üretim mevcut
                # kopyaları SİLERDİ. Kanıt yokken silme yok: dur ve görünür uyar.
                satirlar.append(f"overlay tazeleme ATLANDI: {tip} — core/claude/{tip} okunamadi "
                                f"(junction kopuk?), otomatik uretim SILME riski tasir")
                continue

            gerekli = tazeleme_gerekli(proje, core_root, tip)
            if not gerekli and not _manifest_alansiz(proje, tip):
                continue                      # taze — sessiz no-op
            sebep = (f"core/claude-local degisti: {len(gerekli)} dosya" if gerekli
                     else "manifest kaydi eski (uretilen_hash yok)")

            farklar = fark_raporu(proje, core_root, tip)
            if farklar:
                satirlar.append(f"overlay OTO-TAZELEME ATLANDI: {tip} — {len(farklar)} kopyada "
                                f"elle duzeltme var, dokunulmadi ({sebep}). Karar: terfi ya da "
                                f"claude-local → sonra team_setup.py --overlay-onayli")
                continue

            ok, mesaj = _yerinde_senkron(proje, core_root, tip)   # rmtree YOK (atomiklik)
            satirlar.append((f"overlay tazelendi: {mesaj} [{sebep}]" if ok
                             else f"overlay tazeleme BASARISIZ: {tip} — {mesaj}"))
        except Exception as exc:  # noqa: BLE001
            # `except: pass` YASAK — KOŞMADI ≠ TEMİZ. Oturum bozulmaz ama sessizleşmez.
            satirlar.append(f"overlay OTO-TAZELEME KOSAMADI: {tip} — "
                            f"{type(exc).__name__}: {exc} (eski davranis: elle team_setup.py)")
    if any(s.startswith("overlay tazelendi") for s in satirlar):
        satirlar.append("(overlay tazelemesi SONRAKI oturumdan itibaren etkilidir — "
                        "ajan/skill tanimlari oturum basinda okunur; olculdu 2026-08-13)")
    return satirlar


def durum(proje: Path, core_root: Path, tip: str) -> tuple:
    """-> (mod, sorunlar)  mod ∈ {'junction','overlay','yok'}"""
    h = hedef(proje, tip)
    if not h.exists():
        return "yok", [f"{tip}: dizin yok"]
    if _junction_mu(h):
        if overlay_var_mi(proje, tip):
            return "junction", [f"{tip}: claude-local/{tip} VAR ama .claude/{tip} hâlâ junction "
                                f"→ proje agent'ları YÜKLENMİYOR. Onarım: team_setup.py --repair-junctions"]
        return "junction", []

    # gerçek dizin → overlay olmalı ve güncel olmalı
    if not overlay_var_mi(proje, tip):
        return "overlay", [f"{tip}: gerçek dizin ama claude-local/{tip} yok → sızıntı riski, elle incele"]

    mf = h / MANIFEST_ADI
    if not mf.is_file():
        return "overlay", [f"{tip}: overlay manifest yok → team_setup.py --repair-junctions"]
    try:
        m = json.loads(mf.read_text(encoding="utf-8"))
    except Exception:
        return "overlay", [f"{tip}: overlay manifest okunamadı"]

    sorunlar = []

    # FORMAT: agents/skills frontmatter ile BAŞLAMALI. İlk sürümde damga frontmatter'ın
    # önüne girdi → 6/6 agent yüklenemedi, ama dosya SAYISI doğru olduğu için "güncel"
    # raporlandı. Sayı ≠ yüklenebilirlik. (2026-07-09)
    if tip in ("agents", "skills"):
        bozuk = [f.name for f in sorted(h.glob("*.md")) if not frontmatter_ile_basliyor(f)]
        if bozuk:
            sorunlar.append(f"{tip}: FRONTMATTER BOZUK {bozuk} — dosya `---` ile başlamalı, "
                            f"yoksa Claude Code bu {tip[:-1]}'ları HİÇ yüklemez")
        crlf = [f.name for f in sorted(h.glob("*.md")) if b"\r\n" in f.read_bytes()]
        if crlf:
            sorunlar.append(f"{tip}: CRLF satır sonu {crlf} — LF yazılmalı")

    beklenen = _beklenen(proje, core_root, tip)
    eksik = set(beklenen) - set(m["dosyalar"])
    fazla = set(m["dosyalar"]) - set(beklenen)
    if eksik:
        sorunlar.append(f"{tip}: overlay'de EKSİK {sorted(eksik)} (core yeni dosya ekledi?)")
    if fazla:
        sorunlar.append(f"{tip}: overlay'de FAZLA {sorted(fazla)} (core sildi?)")

    for ad, kayit in m["dosyalar"].items():
        if kayit["kaynak"] != "proje" or ad not in beklenen:
            continue
        _, guncel_core_hash = beklenen[ad]
        if guncel_core_hash and kayit.get("core_hash") and guncel_core_hash != kayit["core_hash"]:
            sorunlar.append(f"{tip}/{ad}: CORE GÜNCELLENDİ ({kayit['core_hash']} → {guncel_core_hash}) "
                            f"— proje override'ı bayatlamış olabilir, gözden geçir")
    return "overlay", sorunlar
