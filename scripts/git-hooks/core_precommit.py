#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEV_CORE pre-commit gate (B11 — D19/D21). STAGED dosyalar üzerinde 4 kontrol:

1) GENERICIZE-LEAK: proje/müşteri kimliği core'a COMMIT'LENEMEZ. İçerik VE dosya adı
   taranır (D5). Kapsam: isim listesi (env/<git-dir>/<proje>.claude, IGNORECASE) +
   yapısal desenler — makine-yolu, e-posta, Z-obje adı (`genericize_common.ORNEK_Z`
   allowlist'i dışındakiler), SAP kullanıcı adı (`D_XXXX`).
   Desenler `scripts/genericize_common.py`'de; `pre_tool_guard` AYNI kaynağı kullanır (D9).
   İsim listesi yoksa `--all` (CI) modunda FAIL-CLOSED (D1).
   pre_tool_guard yazım-anı erken-uyarıdır; KESİN gate budur (+ CI'da aynısı).
   MUAFİYET (Q329, 2026-09-18): dosya-bazlı `SCAN_EXEMPT` KALDIRILDI; yerine SATIR
   bazlı, GEREKÇESİ ZORUNLU `genericize-allow: <gerekçe>` işaretçisi geldi. Muaf
   satır sayısı her koşumda basılır (KAPSAM BEYANI) — ayrıntı: `MUAF_ISARET` bloğu.
2) LINK-AUDIT: staged .md'lerdeki göreli linkler çözülmeli (dosya-dizininden VEYA
   repo-kökünden). Kopuk link = FAIL.
3) APPLIES_TO ŞEMASI (D21): standards/ + playbook/ altındaki her .md frontmatter'ında
   `applies_to:` olmalı ve değerler enum'da olmalı (profiles/*.yaml adları + 'all').
   Typo = sessiz profil-kaybı — şema doğrulaması bunu yakalar.
4) İNFRA-CHANGELOG (2026-08-01): staged dosyalar arasında paylaşılan-altyapı KODU varsa
   aynı commit'te `governance/infra-changelog.md` de değişmiş olmalı. Gerekçe: infra
   bileşeninin bugünkü hali eski bir vakanın çözümüdür; kaydı olmayan değişiklik
   infra-expert'in F0 (geçmiş-okuma) adımını sessizce körleştirir. Kaçış:
   `IX_NO_CHANGELOG=1` (gerekçe commit mesajına). Yalnız pre-commit modunda koşar
   (`--all`/CI'da anlamsız: tüm ağaç "staged" görünür).
6) FRONTMATTER (2026-10-18, PR #347 vakası): `claude/{agents,commands,skills,rules}/`
   altındaki tanım dosyalarının YAML frontmatter'ı GEÇERLİ olmalı. Tek kaynak:
   `scripts/utils/frontmatter_lint.py` (ix_doctor K4 aynı modülü okur). ENGEL sınıfı
   (`: ` · ` #` · `#` ile başlayan değer · kapanmayan tırnak · frontmatter yok/kapanmıyor
   · değerde `---` · ayrışmayan YAML) commit'i bloklar; UYARI sınıfı (`*`/`&` ile başlayan
   tırnaksız değer — eski `paths:` biçimi, lider kararı B) yalnız basılır. Staged ve
   `--all`/CI modunda koşar. Vaka: tırnaksız `description:` içindeki `: ` LF'te tolere
   edildi, CRLF checkout'ta 4 ajanı SESSİZCE düşürdü; Linux CI'da (LF) hiçbir katman
   görmedi. Düzey 2 (PyYAML) CI'da kurulu değildir ⇒ KAPSAM satırı ÖLÇÜLEMEDİ der.

Yalnız staged içerik taranır (git show :path) — working-tree kirliliği gate'i etkilemez.
CI modu: `--all` ile TÜM tracked dosyalar taranır (core-ci.yml full-tree gate'i).
Çıkış: ihlal varsa 1 (commit/CI bloklanır), yoksa 0.

WARN-FIRST katman (Q361 + Q365⑤, 2026-10-12 — ADR 0019; terfi AYRI karar):
· Yapısal UYARI desenleri (`genericize_common.uyari_sizintilari`: bulut tenant host'u ·
  transport numarası) staged ve `--all` modunda satır satır taranır; bulgu `UYARI` olarak
  basılır, ÇIKIŞ KODUNU DEĞİŞTİRMEZ. Token BASILMAZ (CI günlüğü public; bloklamayan bir
  bulgunun izi her koşumda log'a yeniden yazılırdı) — yalnız `yol:satır (tür)`.
· `--ref <ref>`: o ref'in AĞACI (`git ls-tree`) + o commit'in MESAJI taranır (sızıntı +
  uyarı desenleri + sır dosyası adı). Bulgu UYARI'dır; çıkış 0 (çözülemeyen ref → 2).
· `--msg <dosya|->`: commit mesajı taranır (ajan atıf trailer'ında yalnız üreticinin
  adresi maskelenir, satırın geri kalanı taranır — `_ATIF_SATIRI` gerekçesi; `#`
  satırları TARANIR, `mesaj_satirlari` gerekçesi).
  Bulgu UYARI'dır; çıkış 0 (okunamayan dosya / boş mesaj → 2 + ÖLÇÜLEMEDİ).
· Bu iki modda da token BASILMAZ; isim listesi yoksa satır ÖLÇÜLEMEDİ notu basılır.
· `--all` · `--ref` · `--msg` birbirini DIŞLAR: ikisi birlikte verilirse kullanım hatası
  (rc 2) — eskiden biri sessizce kazanıyor, öbürü hiç koşmuyordu.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from genericize_common import (  # noqa: E402  (sys.path bootstrap'tan SONRA)
    ATIF_ADRES_PAT, ATIF_SATIRI, blocklist_var_mi, id_pattern, sizintilari_bul,
    uyari_sizintilari,
)
try:  # 6. kontrol — tek kaynak. Yüklenemezse ÇÖKME YOK, tanım dosyasında fail-closed (aşağıda).
    from utils import frontmatter_lint as FM  # noqa: E402
    _FM_HATA = ""
except Exception as _fm_exc:  # noqa: BLE001
    FM = None  # type: ignore[assignment]
    _FM_HATA = f"{type(_fm_exc).__name__}: {_fm_exc}"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")   # `--msg -` (Q365⑤)

# Tek kaynak: scripts/genericize_common.py (D9). İsim listesi env + <git-dir> +
# <proje>/.claude birleşimi; yapısal desenler (makine-yolu, e-posta, Z-obje, SAP
# kullanıcı adı) her zaman devrede. IGNORECASE → listedeki ad küçük harfle de yakalanır (D2).
ID_PAT = id_pattern()

# Dosya-bazlı izinli token'lar (taramadan ÖNCE içerikten çıkarılır; kalan yine taranır)
ALLOWED_TOKENS = {
    # mimari şemadaki placeholder (gerçek proje/müşteri adı YASAK)
    "README.md": ["<PROJECT_NAME>"],
}
# ── SATIR-BAZLI MUAFİYET (Q329, 2026-09-18 — kullanıcı onaylı DARALTMA) ─────────
# ⛔ ESKİ HAL: `SCAN_EXEMPT` üç dosyayı (`pre_tool_guard` · `core_precommit` ·
# `genericize_common`) sızıntı taramasından KOMPLE muaf tutuyordu. Gerekçesi
# *"tarama anlamsız — kendileri desen tanımlar"* idi ve desen LİTERALLERİ için
# doğrudur; ama muafiyet DOSYANIN TAMAMINI kapsadığı için o dosyaların düz-yazı
# yorum ve docstring'leri de muaf oluyordu. Bu kör noktadan **8 gerçek kimlik izi**
# geçti; dördü, ironik biçimde *"bu ad allowlist'e ALINMADI"* diyen gerekçe
# yorumlarının içinde (#266), en eskisi **38 gün** public çekirdekte kaldı (#267 ile
# temizlendi — içerik ayağı; muafiyetin kendisi bu commit'in konusu).
# ⭐ SINIF: *bilinçli bir muafiyetin gerekçesi bir ALT-KÜME için geçerliyken muafiyet
# ÜST-KÜMEye yazılırsa, muafiyet kör noktaya döner — ve dokunulmazlığı yüzünden en
# uzun yaşayan kör nokta olur.*
#
# ÖLÇÜLDÜ (2026-09-18, 802 takipli dosya, `check_generic` tüm ağaçta koşuldu):
# `SCAN_EXEMPT` DOLU iken **0 bulgu**, BOŞ iken de **0 bulgu**. Üç dosyada Z-obje
# desenine uyan **11 satır** var ve **11'i de** `ORNEK_Z` allowlist'inde; YAPISAL
# desenler (makine-yolu, e-posta) üçünün hiçbir satırında eşleşmiyor ⇒ muafiyet
# bugün HİÇBİR ŞEYİ korumuyordu. Kaldırılması saf DARALTMADIR (gevşetme değil).
#
# YENİ HAL — muafiyet SATIR bazlıdır ve GEREKÇESİ ZORUNLUDUR:
#     <yorum-karakteri> genericize-allow: <bu satırdaki iz neden meşru>
# · Yalnız İŞARETÇİNİN BULUNDUĞU SATIR muaf olur; blok/bölge/dosya muafiyeti YOKTUR.
# · Gerekçe yoksa/yetersizse işaretçi YOK SAYILIR → satır yine bloklanır. Bu şart,
#   mekanizmanın sessiz bir `# noqa`ya dönüşmesini engeller (`post_tool_failure.py`:
#   *"Susturma YASAK (pseudo-comment / pragma / '#EC' ile sessiz pass)"*).
# · Dosya ADI taraması (D5) MUAFİYET DIŞIDIR — dosya adına işaretçi konamaz.
# · Muaf satır sayısı HER koşumda basılır (`kapsam_beyani`; CLAUDE.core §7 KAPSAM
#   BEYANI + checklist CORE-06): *"0 bulgu"* asla *"hiçbir şey muaf değil"* diye
#   okunamaz. Muaf kova, temiz kovaya KARIŞMAZ.
MUAF_ISARET = "genericize-allow"
# ⚠ Literal, `MUAF_ISARET + ":"` biçiminde KURULUR: tek parça yazılsaydı aşağıdaki
# satırın kendisi geçerli bir işaretçi olurdu (kapının kendi desenine takılması sınıfı).
MUAF_RE = re.compile(re.escape(MUAF_ISARET) + r":[ \t]*(.*)$")
# Gerekçe ölçütü. Eşik BİLİNÇLİ DÜŞÜK: amaç "iyi gerekçe" yargılamak DEĞİL, tek
# harflik pragmayı (`... genericize-allow: x`) elemektir. Bugünkü FP riski ölçülebilir
# biçimde SIFIR — ağaçta hiç işaretçi yok (yukarıdaki ölçüm).
MUAF_MIN_KARAKTER = 10
MUAF_MIN_KELIME = 2
# Gerekçenin sonundaki yorum-kapatıcıları (`-->`, `*/`, `#`) gerekçeden sayılmaz.
_GEREKCE_KIRP = " \t-–—*/#>"


def gerekce_gecerli(gerekce: str) -> bool:
    """Gerekçe ZORUNLU: boş/yetersiz ise işaretçi yok sayılır (satır yine taranır)."""
    g = gerekce.strip().strip(_GEREKCE_KIRP).strip()
    return len(g) >= MUAF_MIN_KARAKTER and len(g.split()) >= MUAF_MIN_KELIME

# Link-check muafiyeti: build_core_index.py'nin ÜRETTİĞİ CORE-INDEX kasıtlı olarak PROJE-göreli
# `../core/...` link'leri taşır (proje-kökünden junction ile çözülür; core-repo-kökünden çözülmez).
# build_core_index gerçek dosyaları listeler → link hedefleri garanti var. Bu index'i link-check'ten
# muaf tut (aksi halde her regen 70+ false-positive KOPUK-LINK verir). Genericize-scan'e TABİ kalır.
LINK_EXEMPT = {
    "governance/CORE-INDEX.md",
}

# ── 4. kontrol: İNFRA-CHANGELOG gate ────────────────────────────────────────────
# SINIF TANIMI (dar ve açık tutulur; geniş gate = sürtünme = kaçış-kültürü):
# "İnfra" = ÇALIŞAN, davranış taşıyan paylaşılan kod. Doküman DEĞİL, veri DEĞİL.
CHANGELOG_PATH = "governance/infra-changelog.md"
INFRA_KOD_KOKLERI = ("scripts/", "mcp_servers/", "tests/")
# Kod-dışı/veri istisnaları (yol öneki ile):
INFRA_MUAF_KOKLER = (
    "tests/fixtures/",   # test VERİSİ — bileşen davranışı değil (fixture ekleme teşvik edilir)
    "attic/",            # fosil arşivi (çalıştırılmıyor)
)
# Uzantısız ama çalışan kabuk hook'ları (tam yol):
INFRA_TAM_YOLLAR = {"scripts/git-hooks/pre-commit"}

# B11-GENİŞLETME (2026-08-12, kullanıcı onayı — talimat-hijyeni paketi): TALİMAT dosyaları
# `.md` olsalar da DAVRANIŞ taşır (her oturum context'e yüklenir) — "md = kaydın kendi ortamı"
# muafiyet gerekçesi governance-dokümanları içindir, bunlar için GEÇERSİZDİR. Kayıtsız bir
# rules/CLAUDE.core değişikliği, sonraki bakımcının (infra-expert F0 geçmiş-okuması) gözünde
# görünmez kalır — bugüne kadar tam da böyle %55 blok-tekrarı birikti (ölçüldü).
# Sınır bilinçli DAR: agents/templates/memory-seed KAPSAM DIŞI (genişletme = gerekçeli PR).
TALIMAT_KOKLERI = ("claude/rules/",)
TALIMAT_TAM_YOLLAR = {"CLAUDE.core.md"}


def infra_dosyalari(paths: list[str]) -> list[str]:
    """Staged listesinden İNFRA KODU + TALİMAT DOSYASI olanları döndür.

    Neden `.py` + uzantısız git-hook'u: changelog "bileşenin davranışı neden böyle"
    kaydıdır. Governance `.md` dokümanı ZATEN kaydın kendi ortamıdır (özyineleme +
    gürültü olurdu); fixture'lar veridir; attic çalıştırılmayan fosildir.
    2026-08-12 genişletmesi: `claude/rules/*.md` + `CLAUDE.core.md` İSTİSNADIR —
    `.md` olsalar da her oturum yüklenen DAVRANIŞ dosyalarıdır, kod gibi kayıt ister
    (gerekçe: TALIMAT_KOKLERI üstündeki blok). Sınır hâlâ bilinçli DAR.
    """
    out = []
    for p in paths:
        q = p.replace("\\", "/")
        if q in INFRA_TAM_YOLLAR or q in TALIMAT_TAM_YOLLAR:
            out.append(q)
            continue
        if any(q.startswith(m) for m in INFRA_MUAF_KOKLER):
            continue
        if q.startswith(INFRA_KOD_KOKLERI) and q.endswith(".py"):
            out.append(q)
            continue
        # talimat dosyaları: .md ama davranış taşır (yukarıdaki B11-GENİŞLETME notu)
        if q.startswith(TALIMAT_KOKLERI) and q.endswith(".md"):
            out.append(q)
    return out


def _changelog_dalda_degisti() -> bool:
    """Changelog, DAL genelinde (merge-base(origin/main)..staged-tree) değişti mi?

    ⚠GEVŞETME (kullanıcı onayı 2026-08-01, bug-avı kuyruğu 'amend FP' kaydı):
    Kıyas birimi COMMIT'ten DAL'a çevrildi. Eski davranışın yanlış-pozitifi:
    `git commit --amend`'de staged-diff HEAD'e göredir; changelog satırı amend
    edilen commit'in İÇİNDE olsa bile "bu commit'te değişmiyor" sayılıp
    bloklanıyordu (3 kez yaşandı, 3 kez IX_NO_CHANGELOG kaçışı kullanıldı —
    FP'nin normalleştirdiği kaçış, gate'in kendisinden tehlikeli). Aynı FP
    çok-commit'li dalda da vardı (commit-1 changelog, commit-2 kod → blok).
    Sınır: TAZE dalda (merge-base == HEAD == origin/main) davranış ESKİSİYLE
    BİREBİR — gevşeme yalnız dal-içi. origin/main çözülemezse fail-closed
    (False döner → eski katı yol).
    """
    base = _git("merge-base", "HEAD", "origin/main").strip()
    if not base:
        return False
    out = _git("diff", "--cached", "--name-only", base, "--", CHANGELOG_PATH)
    return bool(out.strip())


def check_changelog(paths: list[str], hatalar: list[str]) -> None:
    if os.getenv("IX_NO_CHANGELOG") == "1":
        sys.stderr.write(
            "⚠ IX_NO_CHANGELOG=1 — infra-changelog gate ATLANDI. "
            "Gerekçeyi commit mesajına yaz (denetim izi).\n")
        return
    infra = infra_dosyalari(paths)
    if not infra:
        return
    if CHANGELOG_PATH in [p.replace("\\", "/") for p in paths]:
        return
    if _changelog_dalda_degisti():
        return
    ornek = ", ".join(infra[:4]) + (" …" if len(infra) > 4 else "")
    hatalar.append(
        f"INFRA-CHANGELOG-YOK  {ornek}  ({len(infra)} infra dosyası) — paylaşılan altyapı "
        f"kodu değişiyor ama `{CHANGELOG_PATH}` bu commit'te DEĞİŞMİYOR.\n"
        f"      Neden: bileşenin bugünkü hali eski bir vakanın çözümüdür; kaydı olmayan "
        f"değişiklik infra-expert'in F0 geçmiş-okumasını sessizce körleştirir.\n"
        f"      Yap: ilgili bileşen bölümüne `| tarih | değişiklik | NEDEN | NASIL test "
        f"edildi | fixture-ref | PR |` satırı ekle ve stage'le.\n"
        f"      Gerçekten kayıt gerektirmiyorsa: IX_NO_CHANGELOG=1 git commit … "
        f"(gerekçe commit mesajına).")


# 5. kontrol — SIR DOSYASI (2026-08-01 bug-avı, CANLI ihlalle bulundu).
# `check_core_not_committed.py` bu sınıfı PROJE repolarında koruyordu; DEV_CORE'un KENDİSİNİ
# hiçbir katman denetlemiyordu (core-ci'da adım yok, pre-commit'te kontrol yoktu). Sonuç:
# `scripts/.conn_adt` ilk çekirdek commit'inden beri (f85e3fd) PUBLIC repoda TAKİPLİYDİ.
# O dosyanın değerleri placeholder'dı (sızıntı-desenimizle 0 eşleşme) — ama kanal açıktı:
# `create_conn_file()` cwd'ye `.conn_adt` YAZAR, yani herhangi bir alt dizinde GERÇEK bir
# bağlantı dosyası oluşup commit'lenebilirdi. Public repoya giden sır GERİ ALINAMAZ (K3).
# Kaçış YOK: bu sınıfta "gerekçeli istisna" diye bir şey olmamalı.
SIR_DESENLERI = (".conn_adt", ".csrf_token.json", "project.local.yaml", ".env.local")


def check_sir(paths: list[str], hatalar: list[str]) -> None:
    """Staged yollarda sır/kimlik dosyası var mı (herhangi bir derinlikte)."""
    for p in paths:
        ad = p.replace("\\", "/").rsplit("/", 1)[-1]
        # `.conn_adt.bak`/`.conn_adt.ornek` gibi türevler de sayılır: baştaki adı taşıyorsa yakala.
        if any(ad == d or ad.startswith(d + ".") for d in SIR_DESENLERI):
            hatalar.append(
                f"SIR-DOSYASI  {p} — bağlantı/kimlik dosyası commit'lenemez (K3).\n"
                f"      DEV_CORE PUBLIC'tir; push'lanan sır GERİ ALINAMAZ (silmek geçmişten "
                f"kaldırmaz, cache'lenmiş olabilir).\n"
                f"      Yap: `git rm --cached {p}` + `.gitignore`'a ekle. Şablon gerekiyorsa "
                f"`claude/conn_adt.template` kullan (değer YOK, yalnız alan adları).")


BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".ico", ".woff",
              ".woff2", ".ttf", ".xlsx", ".docx", ".pptx", ".exe", ".dll"}

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def _git(*args: str) -> str:
    r = subprocess.run(["git", *args], capture_output=True)
    return r.stdout.decode("utf-8", errors="replace")


def staged_files(all_tracked: bool = False) -> list[str]:
    if all_tracked:
        out = _git("ls-files", "-z")
    else:
        out = _git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    return [p for p in out.split("\0") if p]


def staged_content(path: str, ref: str | None = None) -> str | None:
    """Staged (index) içerik — `ref` verilirse o ref'teki içerik; binary ise None."""
    if Path(path).suffix.lower() in BINARY_EXT:
        return None
    r = subprocess.run(["git", "show", (ref or "") + ":" + path], capture_output=True)
    if r.returncode != 0:
        return None
    raw = r.stdout
    if b"\0" in raw[:8000]:
        return None
    return raw.decode("utf-8", errors="replace")


def profile_enum(repo: Path) -> set[str]:
    enum = {"all"}
    prof = repo / "profiles"
    if prof.is_dir():
        enum |= {p.stem for p in prof.glob("*.yaml")}
    return enum


def yeni_sayac() -> dict:
    """KAPSAM BEYANI sayaçları — `muaf` kovası `temiz` kovasına KARIŞMAZ (CORE-06)."""
    return {"dosya": 0, "ikili": 0, "muaf": 0, "gerekcesiz": 0, "muaf_satir": [],
            "uyari": []}


def _tok(tok: str, token_bas: bool) -> str:
    """Bloklamayan modlarda (`--ref`/`--msg`) token yerine tür yazılır (public günlük)."""
    return f"'{tok}' " if token_bas else ""


def check_generic(path: str, text: str, hatalar: list[str],
                  sayac: dict | None = None, token_bas: bool = True) -> None:
    """Sızıntı taraması — Q329'dan beri SATIR SATIR (muafiyet satır bazlı olduğu için).

    ⚠ `str.splitlines()` KULLANILMAZ: o, Unicode satır sınırlarında da (U+0B, U+1C,
    U+2028 …) böler ⇒ satır numaraları git'in saydığıyla AYRIŞIR ve tek kayıt iki
    satır sanılır. `split("\\n")` git'in satır kavramıyla birebirdir.

    Satır-satır taramanın ikinci etkisi bir SIKILAŞTIRMADIR: eski kod isim-listesi
    eşleşmesini `idp.search(text)` ile dosya başına YALNIZ BİR KEZ raporluyordu
    (ilk eşleşme); artık her satır ayrı raporlanır ve satır numarası token'ın GERÇEK
    yerini gösterir (eskiden `re.search(token)` ile ilk geçtiği satır yazılıyordu).
    """
    # D5: dosya ADI da taranır. İçeriği genericize edilmiş ama adı unutulmuş dosyalar
    # (ör. `feedback_<müşteri>-full-dump.md`) eskiden gate'ten geçiyordu — canlı oldu.
    # ⛔ MUAFİYET DIŞI: dosya adına işaretçi konamaz, dolayısıyla bu dal susturulamaz.
    for tok, ad in sizintilari_bul(path, ID_PAT):
        hatalar.append(
            f"GENERICIZE-LEAK  {path}  (DOSYA ADI) {_tok(tok, token_bas)}({ad}) — core'a "
            f"proje/müşteri izi giremez; dosyayı yeniden adlandır.")
    if sayac is not None:
        for _, ad in uyari_sizintilari(path):
            sayac["uyari"].append((path, "DOSYA ADI", ad))

    izinli = ALLOWED_TOKENS.get(path, [])
    for no, ham in enumerate(text.split("\n"), 1):
        satir = ham
        for tok in izinli:
            satir = satir.replace(tok, "")
        bulgular = sizintilari_bul(satir, ID_PAT)
        # WARN-FIRST (Q361): uyarı desenleri ayrı kovada — `hatalar`a GİRMEZ (çıkış kodu sabit).
        uyarilar = uyari_sizintilari(satir)
        if not bulgular and not uyarilar:
            continue
        m = MUAF_RE.search(satir)
        if m and gerekce_gecerli(m.group(1)):
            bulgular = bulgular + uyarilar     # muaf satır uyarıyı da susturur (aynı sözleşme)
            if sayac is not None:
                sayac["muaf"] += len(bulgular)
                # ⚠ TOKEN BASILMAZ, yalnız TÜRÜ: bu satır her YEŞİL koşumda da basılır ve
                # CI günlüğü PUBLIC'tir — muaf tutulan bir izi her koşumda log'a yazmak
                # kapının kendisini sızıntı kanalına çevirirdi.
                sayac["muaf_satir"].append(
                    (path, no, sorted({ad for _, ad in bulgular}),
                     m.group(1).strip().strip(_GEREKCE_KIRP).strip()))
            continue
        if sayac is not None:
            for _, ad in uyarilar:
                sayac["uyari"].append((path, no, ad))
        if not bulgular:
            continue
        ek = ""
        if m:
            if sayac is not None:
                sayac["gerekcesiz"] += 1
            ek = (f"\n      ⚠ Bu satırda `{MUAF_ISARET}:` işaretçisi VAR ama gerekçesi "
                  f"yok/yetersiz (en az {MUAF_MIN_KARAKTER} karakter ve "
                  f"{MUAF_MIN_KELIME} kelime) → YOK SAYILDI. Gerekçesiz muafiyet sessiz "
                  f"bir pragmadır; bu kapı onu kabul etmez.")
        for tok, ad in bulgular:
            hatalar.append(
                f"GENERICIZE-LEAK  {path}:{no}  {_tok(tok, token_bas)}({ad}) — core'a "
                f"proje/müşteri izi giremez; placeholder'la (<SYSTEM_ID>, <SAP_USER>, "
                f"ZSD001 ...)" + ek)


def kapsam_beyani(sayac: dict) -> None:
    """HER koşumda basılır — bulgu olsun olmasın (CLAUDE.core §7 · checklist CORE-06).

    ÇIKIŞ KODU POLİTİKASI (yazılı olması CORE-06 şartıdır):
      · geçerli işaretçili MUAF satır çıkış kodunu DEĞİŞTİRMEZ — bilinçli, gerekçeli
        ve diff'te görünür bir istisnadır; ama *"temiz"* SAYILMAZ, ayrı basılır.
      · GEREKÇESİZ işaretçi bulguyu AYAKTA bırakır ⇒ exit 1 (susturma yok).
      · Taranamayan (ikili) dosya ÖLÇÜLEMEDİ'dir — *"temiz"* değil.
    """
    print(f"[KAPSAM] genericize-scan: {sayac['dosya']} dosya (içerik, satır satır) + "
          f"dosya ADI (D5) · muaf-satır {sayac['muaf']} · "
          f"gerekçesiz işaretçi {sayac['gerekcesiz']} (YOK SAYILDI)")
    print(f"         muafiyet biçimi `{MUAF_ISARET}: <gerekçe>` (aynı satır, gerekçe "
          f"ZORUNLU) · dosya ADI taraması muafiyet DIŞI")
    if sayac["ikili"]:
        print(f"         ÖLÇÜLEMEDİ: {sayac['ikili']} ikili/okunamayan dosya — içeriği DE "
              f"adı DA taranmadı (bugünkü sınır; 'temiz' demek değildir)")
    for path, no, turler, gerekce in sayac["muaf_satir"]:
        print(f"         MUAF  {path}:{no}  ({', '.join(turler)}) ← {gerekce}")
    uyari_beyani(sayac["uyari"])


def uyari_beyani(uyarilar: list[tuple]) -> None:
    """WARN-FIRST kova (Q361) — HER koşumda sayısı basılır; 0 da yazılır (KAPSAM BEYANI).
    Token BASILMAZ: yalnız `yol:satır (tür)`. Çıkış kodunu DEĞİŞTİRMEZ."""
    turler: dict[str, int] = {}
    for _, _, ad in uyarilar:
        turler[ad] = turler.get(ad, 0) + 1
    dokum = " · ".join(f"{ad} {n}" for ad, n in sorted(turler.items())) or "bulgu yok"
    print(f"[UYARI-DESENLERI] tenant host · transport no (warn-first, ADR 0019 — çıkış kodunu "
          f"DEĞİŞTİRMEZ): {len(uyarilar)} ({dokum})")
    for path, no, ad in uyarilar:
        print(f"         UYARI  {path}:{no}  ({ad}) — yer tutucuya çevir (<tenant>, "
              f"<TRANSPORT>; fixture'da sahte SID)")


def check_links(path: str, text: str, repo: Path, hatalar: list[str]) -> None:
    if path in LINK_EXEMPT:
        return
    # Kod-bloğu (```...```) ve inline-kod (`...`) içindeki linkler ÖRNEKTİR — tarama dışı
    # (satır numarası korunsun diye newline'lar bırakılarak boşaltılır).
    text = re.sub(r"```.*?```", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", lambda m: " " * len(m.group(0)), text)
    base = (repo / path).parent
    for m in LINK_RE.finditer(text):
        hedef = m.group(1).split("#", 1)[0]
        if (not hedef or hedef.startswith(("http://", "https://", "mailto:"))
                or "<" in hedef or hedef.startswith("/") or re.match(r"^[A-Za-z]:", hedef)):
            continue
        if not ((base / hedef).exists() or (repo / hedef).exists()):
            satir = text[: m.start()].count("\n") + 1
            hatalar.append(f"KOPUK-LINK  {path}:{satir}  '{m.group(1)}' — ne dosya-dizininden "
                           f"ne repo-kökünden çözülüyor")


def check_applies_to(path: str, text: str, enum: set[str], hatalar: list[str]) -> None:
    bas = text[:500]
    m = re.search(r"applies_to:\s*\[([^\]]*)\]", bas)
    if not m:
        hatalar.append(
            f"APPLIES_TO-YOK  {path}  — standards/playbook .md'leri frontmatter'da "
            f"`applies_to: [...]` beyan etmek zorunda (D21; enum: {sorted(enum)})")
        return
    for tok in (t.strip().strip("'\"") for t in m.group(1).split(",")):
        if tok and tok not in enum:
            hatalar.append(
                f"APPLIES_TO-GECERSIZ  {path}  — '{tok}' enum'da yok {sorted(enum)}; "
                f"typo = sessiz profil-kaybı (D21)")


# 6) FRONTMATTER — yalnız çekirdeğin KENDİ tanım dizinleri (`claude/<tür>/`). Önek kısıtı
# bilinçli: fixture'lar, şablonlar ve memory-seed bu kapının konusu değildir (fixture'lar
# kasıtlı bozuk tanım taşıyabilir). Kural ve sınıflar `frontmatter_lint` docstring'inde.
# Modül yüklenemezse (ör. kapıyı `utils/`suz kopyalayan kum) kapı ÇÖKMEZ ama tanım dosyası
# görürse FAIL-CLOSED'dur: ölçülemeyen tanım TEMİZ sayılmaz. Tür listesi modülden gelir;
# yedek demet yalnız modül yokken öneki bilmek içindir.
FM_TURLER = FM.TURLER if FM is not None else ("agents", "commands", "skills", "rules")
FM_ONEK = tuple(f"claude/{t}/" for t in FM_TURLER)


def check_frontmatter(path: str, text: str, hatalar: list[str], fm: dict) -> None:
    if not path.startswith(FM_ONEK):
        return
    if FM is None:
        if path.endswith(".md"):
            hatalar.append(f"FRONTMATTER-OLCULEMEDI  {path}  — scripts/utils/frontmatter_lint.py "
                           f"yüklenemedi ({_FM_HATA}); tanım dosyası ölçülmeden geçmez")
        return
    tur = FM.tanim_turu(path)
    if tur is None:
        return
    fm["dosya"][tur[0]] = fm["dosya"].get(tur[0], 0) + 1
    for b in FM.bulgular(text, tur[1]):
        oneri = b.oneri if len(b.oneri) <= 120 else b.oneri[:117] + "…"
        satir = f"{path}:{b.satir}  — {b.sorun} · öneri: {oneri}"
        if b.seviye == FM.ENGEL:
            hatalar.append("FRONTMATTER-GECERSIZ  " + satir)
        else:
            fm["uyari"].append("FRONTMATTER-UYARI  " + satir)


def frontmatter_beyani(fm: dict, hatalar: list[str]) -> None:
    """HER koşumda basılır — sıfır tanım dosyasında da (KAPSAM BEYANI, CLAUDE.core §7)."""
    if FM is None:
        print(f"[KAPSAM] frontmatter: ÖLÇÜLEMEDİ — scripts/utils/frontmatter_lint.py yüklenemedi "
              f"({_FM_HATA}); `claude/<tür>/` altındaki tanım dosyası varsa commit BLOKLANIR")
        return
    dokum = " · ".join(f"{t} {fm['dosya'].get(t, 0)}" for t in FM.TURLER)
    n_engel = sum(1 for h in hatalar if h.startswith("FRONTMATTER-GECERSIZ"))
    print(f"[KAPSAM] frontmatter: {sum(fm['dosya'].values())} tanım dosyası ({dokum}; yalnız "
          f"`claude/<tür>/`) · ENGEL {n_engel} · UYARI {len(fm['uyari'])} (çıkış kodunu "
          f"DEĞİŞTİRMEZ) · düzey 2: {FM.duzey2_durumu()}")
    print(f"         {FM.KAPSAM_BEYANI}")
    for u in fm["uyari"]:
        print("         " + u)


def _bayrak_degeri(bayrak: str) -> str | None:
    """`--bayrak <değer>` ya da `--bayrak=<değer>`; değer yoksa None."""
    for i, a in enumerate(sys.argv[1:], 1):
        if a == bayrak:
            return sys.argv[i + 1] if i + 1 < len(sys.argv) else None
        if a.startswith(bayrak + "="):
            return a.split("=", 1)[1]
    return None


def _liste_notu(repo: Path) -> None:
    if not blocklist_var_mi(proje_koku=repo):
        print("         ÖLÇÜLEMEDİ: kimlik isim listesi yüklenemedi — müşteri/sistem/kişi "
              "ADLARI taranmadı (yalnız yapısal + uyarı desenleri)")


def _uyari_bas(mod: str, hatalar: list[str], uyarilar: list[tuple]) -> None:
    """`--ref`/`--msg` ortak çıktısı. WARN-FIRST: bloklayıcı sınıftaki bulgular da burada
    UYARI'dır (bu modlar bugün hiçbir şeyi bloklamaz); hiçbirinde token basılmaz."""
    print(f"[{mod}] sızıntı-sınıfı bulgu {len(hatalar)} (warn-first — çıkış kodu 0)")
    for h in hatalar:
        print("  UYARI  " + h.split("\n", 1)[0])
    uyari_beyani(uyarilar)


# Commit mesajında tarama DIŞI satırlar. ÖLÇÜLDÜ (2026-10-12, `--ref` tabanda): ajan atıf
# trailer'ı (`Co-Authored-By: Claude …` + üreticinin noreply adresi) e-posta yapısal desenine
# uyar ve HER ajan commit'inde bulunur ⇒ muafiyetsiz `--msg` her mesajda sahte bulgu
# üretirdi (uyarı körlüğü). Muafiyet YALNIZ bu biçime işler; başka adres/ad taşıyan
# trailer TARANIR (o satırlar gerçek kimlik izi olabilir). Atlanan satır sayısı basılır.
# Ad ile adres ARASI `@` taşıyamaz: `Claude <başka-adres> <noreply…>` biçimi aksi hâlde
# ikinci bir e-postayı muafiyetin içine saklardı (bug-gate 2026-10-12, M10).
# TEK KAYNAK: desen `genericize_common.ATIF_SATIRI` (2026-10-12) — `pre_tool_guard`'ın
# commit-mesajı gate'i AYNI çekirdeği kullanır; burada yalnız atıf trailer'ı muaftır
# (guard'ın ek iki satırı — oturum / üretici — bu uçta taranmaya devam eder).
# ⛔ Satır BOŞALTILMAZ, yalnız adresi maskelenir (bug-gate F3, 2026-10-14): ad bölümüne
# yazılan bir obje/paket adı aksi hâlde taramadan geçerdi (`genericize_common` ⛔ notu).
_ATIF_SATIRI = ATIF_SATIRI


def mesaj_satirlari(metin: str) -> tuple[str, int]:
    """Taranacak mesaj metni (satır numarası korunur) + adresi maskelenen satır sayısı.

    `#` satırları TARANIR (bug-gate 2026-10-12). ÖLÇÜLDÜ (git 2.54, `commit.cleanup`
    ayarsız): `-m`, `-F <dosya>` ve `-F -` ile yazılan mesajda `#` satırı KAYITLI mesajda
    KALIR (varsayılan cleanup editörsüz `whitespace`'tir, yorum silmez) ve `commit-msg`
    hook'u da onu görür. `--ref`'in okuduğu kayıtlı mesajda zaten git yorumu yoktur ⇒ `#`
    ile başlayan her satır yayına giden metindir. Editörle yazılan mesajda git'in kendi
    yardım yorumları taranır (FP riski, sızıntı riskinden ucuz). Muaf tek parça: atıf
    trailer'ındaki üretici adresi (ad bölümü taranır)."""
    out, atlanan = [], 0
    for s in metin.split("\n"):
        if _ATIF_SATIRI.match(s):
            out.append(ATIF_ADRES_PAT.sub("", s, count=1))
            atlanan += 1
        else:
            out.append(s)
    return "\n".join(out), atlanan


def msg_modu(kaynak: str, repo: Path) -> int:
    """Q365⑤ — commit mesajı taraması (`commit-msg` hook'unun ileride çağıracağı uç)."""
    try:
        if kaynak == "-":
            metin = sys.stdin.read()
        else:
            metin = Path(kaynak).read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"[MSG] ÖLÇÜLEMEDİ: mesaj okunamadı ({e.__class__.__name__}) — tarama YAPILMADI")
        return 2
    if not metin.strip():
        # Boş girdi "temiz" DEĞİLDİR: yanlış dosya / boş boru da buraya düşer (ölçülemedi ≠ temiz).
        print("[MSG] boş mesaj — ÖLÇÜLEMEDİ: taranacak metin yok (yanlış dosya ya da boş "
              "stdin olabilir) — tarama YAPILMADI")
        return 2
    taranan, atlanan = mesaj_satirlari(metin)
    hatalar: list[str] = []
    sayac = yeni_sayac()
    check_generic("<commit-mesajı>", taranan, hatalar, sayac, token_bas=False)
    print(f"[KAPSAM] --msg: {len(metin.split(chr(10)))} satır · adresi maskelenen {atlanan} "
          f"(yalnız ajan atıf trailer'ının üretici adresi; satırın geri kalanı ve `#` "
          f"satırları TARANIR)")
    _uyari_bas("MSG", hatalar, sayac["uyari"])
    _liste_notu(repo)
    return 0


def ref_modu(ref: str, repo: Path) -> int:
    """Q365⑤ — belirli bir ref'in AĞACI + commit MESAJI (yayına giden şeyin kendisi)."""
    r = subprocess.run(["git", "rev-parse", "--verify", "--quiet", ref + "^{commit}"],
                       capture_output=True, text=True)
    sha = r.stdout.strip()
    if r.returncode != 0 or not sha:
        print(f"[REF] ÖLÇÜLEMEDİ: '{ref}' bir commit'e çözülmedi — tarama YAPILMADI")
        return 2
    hatalar: list[str] = []
    sayac = yeni_sayac()
    dosyalar = [p for p in _git("ls-tree", "-r", "-z", "--name-only", sha).split("\0") if p]
    check_sir(dosyalar, hatalar)
    for path in dosyalar:
        text = staged_content(path, ref=sha)
        if text is None:
            sayac["ikili"] += 1
            continue
        sayac["dosya"] += 1
        check_generic(path, text, hatalar, sayac, token_bas=False)
    mesaj, atlanan = mesaj_satirlari(_git("log", "-1", "--format=%B", sha))
    check_generic("<commit-mesajı>", mesaj, hatalar, sayac, token_bas=False)
    print(f"[KAPSAM] --ref {sha[:12]}: {sayac['dosya']} dosya + commit mesajı "
          f"(adresi maskelenen {atlanan} satır: yalnız ajan atıf trailer'ı) · "
          f"muaf-satır {sayac['muaf']} · ikili/okunamayan {sayac['ikili']} (ÖLÇÜLEMEDİ)")
    _uyari_bas("REF", hatalar, sayac["uyari"])
    _liste_notu(repo)
    return 0


def main() -> int:
    all_tracked = "--all" in sys.argv
    modlar = [m for m in ("--all", "--ref", "--msg")
              if m in sys.argv or any(a.startswith(m + "=") for a in sys.argv)]
    if len(modlar) > 1:
        print(f"[KULLANIM] {' + '.join(modlar)} birlikte verilemez — bu modlar birbirini "
              f"dışlar (biri sessizce kazanır, öbürü HİÇ koşmazdı). Tek mod seç.")
        return 2
    if "--msg" in sys.argv or any(a.startswith("--msg=") for a in sys.argv):
        kaynak = _bayrak_degeri("--msg")
        if not kaynak:
            print("[KULLANIM] --msg <dosya|->")
            return 2
        return msg_modu(kaynak, Path(_git("rev-parse", "--show-toplevel").strip() or "."))
    if "--ref" in sys.argv or any(a.startswith("--ref=") for a in sys.argv):
        ref = _bayrak_degeri("--ref")
        if not ref:
            print("[KULLANIM] --ref <ref>")
            return 2
        return ref_modu(ref, Path(_git("rev-parse", "--show-toplevel").strip() or "."))
    repo = Path(_git("rev-parse", "--show-toplevel").strip() or ".")
    enum = profile_enum(repo)

    # D1 (2026-07-10 denetimi) — FAIL-CLOSED. İsim listesi `.git/genericize-blocklist`'te
    # yaşar; `.git/` ASLA klonlanmaz. CI runner taze klon yaptığı için liste hiç
    # yüklenmiyordu → public repoya giden SON KAPI müşteri/sistem/kişi adına KÖRDÜ
    # (canlı ölçüldü: müşteri adı, sistem kimliği ve kullanıcı adı exit 0 ile geçti).
    # Artık: CI/full-tree modunda liste yoksa DUR. Lokal pre-commit'te yalnız uyar
    # (geliştiriciyi bloklamak yerine kurulum eksiğini bildir).
    if not blocklist_var_mi(proje_koku=repo):
        if all_tracked:
            print("⛔ GENERICIZE GATE — kimlik blocklist'i YÜKLENEMEDİ (fail-closed).\n")
            print("  Yapısal desenler (makine-yolu, e-posta, Z-obje, SAP kullanıcı adı)")
            print("  devrede; ama müşteri/sistem/kişi ADLARI için isim listesi ŞART.\n")
            print("  CI için: repository secret `IX_GENERICIZE_BLOCKLIST` tanımla")
            print("  (virgülle ayrılmış regex listesi) ve workflow adımına env olarak geçir.")
            print("  Lokal için: `<git-dir>/genericize-blocklist` ya da")
            print("  `<proje>/.claude/genericize-blocklist.txt` oluştur.")
            return 1
        sys.stderr.write(
            "⚠ genericize blocklist bulunamadı — yalnız yapısal desenler devrede. "
            "Müşteri/sistem/kişi adı YAKALANMAZ. `<git-dir>/genericize-blocklist` kur.\n")

    hatalar: list[str] = []
    dosyalar = staged_files(all_tracked)

    # 4) İNFRA-CHANGELOG — yalnız pre-commit (staged) modunda. `--all`/CI'da tüm ağaç
    #    "staged" görünür → her koşumda tetiklenirdi (anlamsız + fail-open baskısı).
    if not all_tracked:
        check_changelog(dosyalar, hatalar)

    # 5) SIR DOSYASI — HER İKİ modda (staged + `--all`/CI). `--all`'da da koşar, çünkü
    #    asıl vaka tam olarak buydu: dosya ZATEN takipliydi ve hiçbir staged-koşum onu
    #    bir daha görmedi. CI'nın tam-ağaç taraması bu sınıfın tek yakalayıcısıdır.
    check_sir(dosyalar, hatalar)

    sayac = yeni_sayac()
    fm: dict = {"dosya": {}, "uyari": []}
    for path in dosyalar:
        text = staged_content(path)
        if text is None:
            sayac["ikili"] += 1
            continue
        sayac["dosya"] += 1
        check_generic(path, text, hatalar, sayac)
        if path.endswith(".md"):
            check_links(path, text, repo, hatalar)
            if path.startswith(("standards/", "playbook/")):
                check_applies_to(path, text, enum, hatalar)
            check_frontmatter(path, text, hatalar, fm)

    # KAPSAM BEYANI — bulgu olsun olmasın, HER koşumda (en kritik an sıfır-bulgu anıdır).
    kapsam_beyani(sayac)
    frontmatter_beyani(fm, hatalar)

    if hatalar:
        print("⛔ pre-commit GATE (B11) — commit BLOKLANDI:\n")
        for h in hatalar:
            print("  " + h)
        print(f"\n  Toplam {len(hatalar)} ihlal. Düzelt → tekrar commit. "
              f"(Bypass YASAK — ADR 0005 kültürü; sızıntı taramasında gerçekten meşru "
              f"TEK BİR satır varsa o satıra `{MUAF_ISARET}: <gerekçe>` yaz — gerekçe "
              f"ZORUNLU, muafiyet yalnız o satıra işler ve her koşumda sayılıp basılır.)")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
