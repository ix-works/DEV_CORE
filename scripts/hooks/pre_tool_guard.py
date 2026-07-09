#!/usr/bin/env python3
"""PreToolUse (matcher: Bash|Edit|Write|MultiEdit|mcp__sap-adt__*) — çok-katman guard.

SAP katmanı (eskiden beri):
1) ADR 0005-C: transport/package YARATMA ve TR RELEASE etme yasak (Bash/script dahil).
2) ADR 0010 BAGLANTI TUTARSIZLIGI: MCP eski sisteme bagliyken ADT islemi RED.
3) Inline-aktivasyon / yalin-fiori-deploy / app-ici-npm-install dersleri.

Mimari katmanı (ADR 0020, B9 — v3 yan-kurulum):
4) FREEZE-GUARD (R10): project.yaml `frozen_readonly_paths` köklerine YAZMA teşebbüsü RED
   (Edit/Write hedefi veya Bash'te yazma-fiili + dondurulmus yol). OKUMA serbest.
5) ÖZYİNELEMELİ-SİLME BLOĞU (R9): core-junction / .claude/{agents,skills,commands} /
   DEV_CORE hedefli rm -rf / Remove-Item -Recurse / rimraf / rmdir /s / git clean RED
   (guncel toolchain junction'a inmiyor [2.8 kanıtı] ama arac-cesitliligi sigortasi).
6) CORE-YAZIM TARAMASI (Ö5, string-hizli): core/'a Edit/Write anında genericize-leak
   (musteri/sistem/kullanici izi) RED; standards|playbook'a YENİ .md Write'ında
   applies_to frontmatter yoksa RED. Kesin gate commit-hook+CI'da; bu erken-uyarı.
7) SIZINTI-COMMIT KİLİDİ (2.7/F1 lokal): `git add/commit` kapsamında core-path RED.

Tehlikeli/tutarsiz degilse sessiz (exit 0). Blokta exit 2 (stderr → Claude'a geri besler).
Hız ilkesi (Ö5): tum yeni kontroller string/regex — sicak yolda dosya-sistemi taramasi YOK
(yaml okuma module-load'da 1 kez, cache'li).
"""
import io
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

if sys.platform == "win32" and hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# SADECE gerçek release/create-transport ENDPOINT/komut/FM token'ları.
# Prose-greedy (.*) desen YOK — git commit mesajı/grep/echo gibi metinleri yanlış
# bloklamamak için yalnızca normal yazıda geçmeyecek somut sinyaller (false-positive fix).
_DANGER = re.compile(
    r"(newreleasejobs"                       # ADT transport release endpoint segmenti
    r"|\breleaseTransport\b"                  # tool/fonksiyon adı
    r"|\bcreateTransport\b"
    r"|\btrint_release_request\b"             # release FM
    r"|\btr_release_request\b"
    r"|\bSCC1\b"                              # client copy by request (riskli)
    r"|/cts/transportrequests/\S+/newreleasejobs)",
    re.IGNORECASE,
)


# App-içi `npm install/ci/add` (npm run DEĞİL) — paket-seviye ui/ workspace ihlali (standards/03).
_NPM_INSTALL = re.compile(r"\bnpm\s+(?:install|ci|add|i)\b", re.IGNORECASE)

# Yalın `fiori deploy` — build YAPMAZ, eski dist'i yükler + "Successful" yalanı söyler
# (2026-07-06 stale-dist dersi). Kanonik yol scripts/deploy_ui.py (build+deploy+canlı-doğrulama).
# deploy_ui.py'nin kendi `npx fiori deploy` çağrısı Python subprocess'te → Bash tool'a görünmez (muaf).
_FIORI_DEPLOY = re.compile(r"\bfiori\s+deploy\b", re.IGNORECASE)


def _ui_app_subdir(path: str):
    """path bir UI app alt-dizini mi (`.../ui/<app>`, ui/ workspace kökü DEĞİL)?

    Dönüş: (ui_root, app) veya None. ui/ kökü `package.json` içinde 'workspaces' içeriyorsa
    onaylar (workspace olmayan repo'da false-positive yok). FS kontrolü yalnız npm-install
    görülünce çalışır (nadir) → sıcak-yol maliyeti yok."""
    if not path:
        return None
    p = path.replace("\\", "/")
    m = re.search(r"(.*/ui)/([^/]+)", p)
    if not m:
        return None
    ui_root, app = m.group(1), m.group(2).strip()
    if not app or app in (".", ".."):
        return None
    root = _proje_koku()  # B9-fix: __file__ junction'la DEV_CORE'a çözülür — env/cwd kullan
    ui_path = Path(ui_root) if Path(ui_root).is_absolute() else (root / ui_root)
    pkg = ui_path / "package.json"
    try:
        if pkg.exists() and "workspaces" in pkg.read_text(encoding="utf-8", errors="ignore"):
            return (ui_root, app)
    except Exception:
        return None
    return None


# ---------------- B9 mimari-katman yardımcıları ----------------

def _proje_koku() -> Path:
    """PROJE kökü. DİKKAT (ADR 0020): bu hook junction üzerinden CORE'dan koşar —
    __file__.resolve() junction'ı DEV_CORE'a çözer, PROJEYE DEĞİL. Tek doğru kaynak:
    env CLAUDE_PROJECT_DIR (hook'lara verilir) → cwd fallback."""
    import os as _os
    env = _os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(env) if env else Path.cwd()


_PROJ_ROOT = _proje_koku()

_YAZMA_FIILI = re.compile(
    r"(\brm\b|\bmv\b|\bcp\b|>>|(?<![-=<>])>(?!>)|\bdel\b|\brmdir\b|\bmkdir\b|\btouch\b"
    r"|\btee\b|\bsed\s+-i\b|\brobocopy\b|Set-Content|Out-File|Add-Content|New-Item"
    r"|Remove-Item|Move-Item|Copy-Item\s)", re.IGNORECASE)

_SILME_FIILI = re.compile(
    r"(\brm\s+-[a-z]*r[a-z]*f?|\brm\s+-[a-z]*f[a-z]*r|Remove-Item[^\n|;]*-Recurse"
    r"|\brimraf\b|\brmdir\s+/s|\bgit\s+clean\b(?![^\n]*-n))", re.IGNORECASE)

# Silme hedefi: core/ · /core · ÇIPLAK `core` argümanı (rm -rf core) · .claude/{alt} · DEV_CORE
_KORUNAN_SILME_HEDEF = re.compile(
    r"(\bcore[/\\]|[/\\]core\b|(?<![\w/\\.])core(?![\w/\\.])"
    r"|\.claude[/\\](agents|skills|commands)|DEV_CORE)",
    re.IGNORECASE)

def _leak_desenleri() -> list[str]:
    """Core'a girmesi yasak proje/müşteri/kişi izleri.

    ⚠ LİSTE CORE'DA TUTULMAZ. DEV_CORE **public**tir; müşteri adını, sistem
    kimliğini veya kişi adını buraya yazmak, tam da engellemeye çalıştığımız
    sızıntının kendisidir. (2026-07-09: guard'ın kendi filtre listesi public
    repoda müşteri ve kişi adlarını ilan ediyordu — bu fonksiyon o yüzden var.)

    Kaynak sırası (ilk bulunan kazanır):
      1. env `IX_GENERICIZE_BLOCKLIST`  (virgülle ayrılmış)
      2. `<proje>/.claude/genericize-blocklist.txt`  (satır başına bir desen;
         `#` yorum; **.gitignore'lu** — repoya girmez)
      3. jenerik varsayılan (aşağıda) — isim içermez, yalnız yapısal desenler

    Kısaltma/obfuscation (ör. ilk 4 harf) ÇÖZÜM DEĞİL: bağlamda tahmin edilir ve
    masum kelimeleri bloklar (yanlış-pozitif).
    """
    env = os.environ.get("IX_GENERICIZE_BLOCKLIST", "").strip()
    if env:
        return [p.strip() for p in env.split(",") if p.strip()]

    dosya = _PROJ_ROOT / ".claude" / "genericize-blocklist.txt"
    if dosya.exists():
        try:
            satirlar = dosya.read_text(encoding="utf-8", errors="replace").splitlines()
            desenler = [s.strip() for s in satirlar
                        if s.strip() and not s.lstrip().startswith("#")]
            if desenler:
                return desenler
        except Exception:
            pass

    # Jenerik varsayılan: isim YOK, yalnız yapısal sızıntı desenleri.
    # Her ikisi de PLACEHOLDER'ı muaf tutar — dokümantasyon örnekleri yanlış-pozitif
    # üretiyordu (2026-07-09 CI bulgusu: `C:\Users\<USER>` ve `user@example.com`).
    return [
        r"C:[/\\]+Users[/\\]+(?!<)[^/\\ ]+",                 # makine-lokal kullanıcı yolu
        # e-posta: RFC 2606 rezerve/örnek domainleri HARİÇ
        r"[A-Za-z0-9._%+-]+@(?!example\.(?:com|org|net)\b)(?!test\b)(?!localhost\b)"
        r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    ]


_CORE_LEAK = re.compile("(" + "|".join(_leak_desenleri()) + ")")

_GIT_STAGE = re.compile(r"\bgit\s+(add|commit|stage)\b", re.IGNORECASE)

# ---- PUBLIC-PR SIZINTI GATE (2026-07-09) -------------------------------------
# DEV_CORE public oldu. `gh pr create` gövdesi HİÇBİR gate'ten geçmiyordu:
# core_precommit yalnız COMMIT içeriğini tarar, PR başlığı/gövdesi commit değildir.
# Somut vaka: PR gövdesi gerçek Z-paket adı taşıyordu; onu auto-mode tesadüfen
# durdurdu (genericize kontrolü olduğu için değil, "public surface" refleksiyle).
# Yayınlanan içerik cache'lenir/indexlenir — silmek geri almaz → FAIL-CLOSED.
# `gh pr create` KOMUT olarak mı geçiyor, yoksa metin içinde ondan BAHSEDİLİYOR mu?
# Naif `\bgh\s+pr\s+create\b` ikisini ayırt etmez: bu gate'i tanıtan commit mesajı
# ("`gh pr create` gövdesi ...") gate'in kendisini bloklamıştı (2026-07-09, dogfood).
# Komut-sınırı şart: satır başı ya da ayraç (; | & ( newline) sonrası.
_GH_PR_CREATE = re.compile(
    r"(?:^|[\n;|&(])\s*(?:[A-Za-z_]\w*=\S+\s+)*gh\s+pr\s+create\b", re.IGNORECASE)

# Heredoc/here-string gövdeleri KOMUT DEĞİL, veridir (git commit -F -, --body "$(cat <<EOF)").
# Taramadan önce çıkarılır; aksi halde commit mesajındaki örnek komut "çalıştırılıyor" sanılır.
_HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1.*?^\2$", re.MULTILINE | re.DOTALL)
_PS_HERESTRING = re.compile(r"@(['\"])[\s\S]*?^\1@", re.MULTILINE)


def _komut_govdesi(s: str) -> str:
    """Heredoc/here-string gövdelerini düşür — geriye yalnız çalıştırılacak komut kalsın."""
    s = _HEREDOC.sub(" <<HEREDOC-STRIPPED> ", s)
    return _PS_HERESTRING.sub(" <HERESTRING-STRIPPED> ", s)
# core_precommit.py::ZSD_PAT ile AYNI desen (tek doğruluk kaynağı olmalı; ikisi
# ayrışırsa commit'te yakalanan PR gövdesinde kaçar). ZSD000/001 = demo, serbest.
_ZSD_PAT = re.compile(r"\bzsd0(?!00|01)\d{2}", re.IGNORECASE)
_ARG_REPO = re.compile(r"--repo[= ]+([^\s'\"]+)")
_ARG_BODYFILE = re.compile(r"--body-file[= ]+(?:'([^']+)'|\"([^\"]+)\"|(\S+))")
_CD_PREFIX = re.compile(r"\bcd\s+([^\s;&|]+)")


def _arg_deger(s: str, ad: str) -> str:
    """--<ad> değerini çıkar (tek/çift tırnaklı veya tırnaksız). Yoksa ''."""
    m = re.search(rf"--{ad}[= ]+(?:'([^']*)'|\"((?:[^\"\\]|\\.)*)\"|(\S+))", s)
    if not m:
        return ""
    return m.group(1) or m.group(2) or m.group(3) or ""


def _yayinlanan_metin(hay: str) -> tuple:
    """PR'da GERÇEKTEN yayınlanacak metin: --title + --body + --body-file İÇERİĞİ.

    Komutun tamamını taramak YANLIŞ: `--body-file` YOLU yayınlanmaz ama içinde
    proje/müşteri adı geçebilir (ör. `C:/IX/<Musteri>/.tmp/body.md`) → gate kendi
    yolunu sızıntı sanır (2026-07-09 dogfood: ikinci yanlış-pozitif). Yanlış-pozitif
    üreten gate gürültüye döner, gürültülü gate ciddiye alınmaz.
    Dönüş: (metin, hata) — hata doluysa FAIL-CLOSED.
    """
    parcalar = [_arg_deger(hay, "title"), _arg_deger(hay, "body")]
    bf = _ARG_BODYFILE.search(hay)
    if bf:
        yol = bf.group(1) or bf.group(2) or bf.group(3)
        try:
            parcalar.append(Path(yol).read_text(encoding="utf-8", errors="replace"))
        except Exception:
            return "", (f"--body-file okunamadi ({yol}) — govde taranamadi. "
                        "FAIL-CLOSED: dosyayi okunur yap veya --body kullan.")
    return "\n".join(p for p in parcalar if p), ""


def _repo_public_mu(hay: str) -> tuple:
    """Hedef repo public mi? -> (public_mu, etiket). Kararsızsa FAIL-CLOSED (public say).

    Görünürlük CANLI sorulur (`gh repo view`), listeden okunmaz: bugün private olan
    repo yarın public olabilir (2026-07-09'da tam bu oldu) ve bayat liste gate'i
    sessizce susturur — korumanın en kötü başarısızlık biçimi.
    """
    import subprocess
    m = _ARG_REPO.search(hay)
    argv = ["gh", "repo", "view", "--json", "isPrivate,nameWithOwner"]
    cwd = None
    if m:
        argv.insert(3, m.group(1))
    else:
        c = _CD_PREFIX.search(hay)
        cwd = c.group(1) if c else str(_PROJ_ROOT)
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=15,
                           cwd=cwd, shell=False)
        if r.returncode != 0:
            return True, "gorunurluk-sorulamadi(fail-closed)"
        d = json.loads(r.stdout)
        return (not d.get("isPrivate", True)), d.get("nameWithOwner", "?")
    except Exception:
        return True, "gorunurluk-sorulamadi(fail-closed)"


def _gh_pr_public_leak(hay: str) -> str:
    """`gh pr create` public repoya gidiyorsa başlık+gövdede proje/müşteri izi ara."""
    komut = _komut_govdesi(hay)
    if not _GH_PR_CREATE.search(komut):
        return ""
    hay = komut  # arg çıkarımı da yalnız komut üzerinden (heredoc verisi arg değildir)
    public, repo = _repo_public_mu(hay)
    if not public:
        return ""  # private repo (ör. proje reposu): gerçek obje adı MEŞRU, tarama yok

    # YALNIZ yayınlanacak metin taranır — komutun kendisi (yollar, flag'ler) değil.
    metin, hata = _yayinlanan_metin(hay)
    if hata:
        return f"public repo '{repo}' — {hata}"

    bulgular = []
    for pat, ad in ((_CORE_LEAK, "kimlik izi"), (_ZSD_PAT, "ZSD-numarali paket adi")):
        for mm in pat.finditer(metin):
            bulgular.append(f"{ad}: '{mm.group(0)}'")
            if len(bulgular) >= 6:
                break
    if not bulgular:
        return ""
    return (f"public repo '{repo}' — PR basligi/govdesinde " + "; ".join(bulgular))


def _frozen_paths() -> list[str]:
    """project.yaml frozen_readonly_paths (basit satır-parse; pyyaml bağımlılığı yok)."""
    py = _PROJ_ROOT / "project.yaml"
    if not py.exists():
        return []
    out: list[str] = []
    try:
        icinde = False
        for line in py.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = line.strip()
            if s.startswith("frozen_readonly_paths:"):
                kalan = s.split(":", 1)[1].strip()
                # satır-sonu yorumunu soy (` # ...`); yol içinde '#' beklenmez
                kalan = re.sub(r"\s+#.*$", "", kalan).strip()
                if kalan.startswith("[") and kalan.endswith("]"):
                    out += [x.strip().strip("'\"") for x in kalan[1:-1].split(",") if x.strip()]
                    return out
                icinde = True
                continue
            if icinde:
                if s.startswith("- "):
                    out.append(re.sub(r"\s+#.*$", "", s[2:]).strip().strip("'\""))
                elif s and not s.startswith("#"):
                    break
    except Exception:
        return []
    return out


# SAP'ye YAZAN MCP tool'ları (yasaklar-damga gate'i bunlardan önce koşar)
_SAP_YAZMA_TOOLLARI = {
    "mcp__sap-adt__adt_push_source", "mcp__sap-adt__adt_activate",
    "mcp__sap-adt__adt_delete", "mcp__sap-adt__adt_domain_create",
    "mcp__sap-adt__adt_dtel_create", "mcp__sap-adt__adt_struct_create",
    "mcp__sap-adt__adt_post_shell", "mcp__sap-adt__adt_publish_service",
    "mcp__sap-adt__adt_classrun",
}


def _yasaklar_damga_sorunu() -> str:
    """SAP-yazma öncesi: kök CLAUDE.md yasaklar damgası kanonikle eş mi?
    Sorun varsa mesaj, temizse ''. (Kanonik okunamıyorsa=junction sorunu → bu gate
    sessiz geçer; junction'ı zaten shim/junction-guard yakalar — çifte-blok gereksiz.)"""
    kok = _PROJ_ROOT
    cmd = kok / "CLAUDE.md"
    if not (kok / "project.yaml").exists() or not cmd.exists():
        return ""
    try:
        import sys as _s
        _s.path.insert(0, str(kok / "core" / "scripts"))
        from utils import yasaklar_stamp  # type: ignore
        core = kok / "core"
        if not yasaklar_stamp.canonical_path(core).exists():
            return ""  # junction/kanonik yok → bu gate'in işi değil
        ok, mesaj = yasaklar_stamp.check(cmd.read_text(encoding="utf-8"), core)
        return "" if ok else mesaj
    except Exception:
        return ""  # fail-open: kendi hatamız SAP-yazmayı bloklamasın


def _canon_path(s: str) -> str:
    """Yol-kıyas kanonu: hem `<DRIVE>\\<FROZEN_ROOT>` hem git-bash `/<drive>/<root>` aynı forma iner.
    lower · \\→/ · sürücü-iki-noktası düşür · ÇOKLU-slash→tek (B1 fix 2026-07-09):
    project.yaml liste-değeri naif-parser'da çift-backslash unescape edilmeyince `_FROZEN`
    çift-slash oluyordu → gerçek tek-slash yollar eşleşmiyordu (FREEZE-GUARD R10 ölüydü).
    Coklu-slash normalizasyonu HEM _FROZEN'ı HEM gelen yolu aynı forma indirir (format-bağımsız)."""
    return re.sub(r"/{2,}", "/", s.replace("\\", "/").lower().replace(":", ""))


_FROZEN = [_canon_path(p).rstrip("/") for p in _frozen_paths() if p]


def _frozen_hit(metin: str) -> str:
    """Metin (komut/dosya-yolu) dondurulmuş kök içeriyor mu? İlk eşleşen kökü döndür.
    Windows (C:\\<kök>) ve bash (/c/<kök>) yol stilleri kanonlaştırılarak kıyaslanır."""
    if not _FROZEN or not metin:
        return ""
    duz = _canon_path(metin)
    for kok in _FROZEN:
        if kok and kok in duz:
            return kok
    return ""


def _core_hedef_mi(dosya: str) -> bool:
    """Edit/Write hedefi core (junction veya DEV_CORE mutlak) altında mı?"""
    if not dosya:
        return False
    d = dosya.replace("\\", "/").lower()
    return "/core/" in d or d.startswith("core/") or "dev_core" in d


def _host(url: str) -> str:
    if not url:
        return ""
    return (urlparse(url if "://" in url else "https://" + url).hostname or "").lower()


def _conn_field(text: str, key: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(key) and "=" in s:
            return s.split("=", 1)[1].strip()
    return ""


def _binding_mismatch() -> tuple:
    """(.conn_adt) ile (MCP'nin canli baglantisi=.mcp_active_system) ayrisik mi?

    Donus: (mismatch: bool, conn_label, mcp_label). Kanit yoksa (False, '', '')."""
    root = _proje_koku()  # B9-fix: __file__ junction'la DEV_CORE'a çözülür — env/cwd kullan
    conn = root / ".conn_adt"
    state = root / ".claude" / ".mcp_active_system"
    if not conn.exists() or not state.exists():
        return (False, "", "")  # kanit yok → bloklamA
    try:
        ct = conn.read_text(encoding="utf-8", errors="ignore")
        cur_url, cur_cl = _conn_field(ct, "ADT_SAP_URL"), _conn_field(ct, "ADT_SAP_CLIENT")
        cur_sys = _conn_field(ct, "ADT_SAP_SYSTEM_NAME")
        st = json.loads(state.read_text(encoding="utf-8"))
        mcp_url, mcp_cl = st.get("url") or "", str(st.get("client") or "")
        mcp_sys = st.get("system") or ""
    except Exception:
        return (False, "", "")
    ch, mh = _host(cur_url), _host(mcp_url)
    differ = (bool(ch) and bool(mh) and ch != mh) or (bool(cur_cl) and bool(mcp_cl) and str(cur_cl) != mcp_cl)
    conn_label = cur_sys or ch or "?"
    mcp_label = mcp_sys or mh or "?"
    return (differ, conn_label, mcp_label)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    tool_name = data.get("tool_name", "") or ""

    # KESİN YASAKLAR fiziksel-damga gate (ADR 0005): SAP-YAZMA öncesi kök CLAUDE.md
    # damgası kanonikle eş mi? (junction-kopuk zaten shim'de yakalanır; bu, junction
    # SAĞLAMKEN damganın silinmiş/bozulmuş olması — yasaklar context'te yok — halini kapar.)
    if tool_name in _SAP_YAZMA_TOOLLARI:
        sorun = _yasaklar_damga_sorunu()
        if sorun:
            sys.stderr.write(
                "⛔ KESİN YASAKLAR DAMGASI EKSİK/SAPMIŞ (PreToolUse guard, ADR 0005): "
                f"{sorun}\nYasaklar kök CLAUDE.md'de fiziksel damgalı OLMALI (junction-"
                "bağımsız anayasa). Damga yokken/bayatken SAP-YAZMA REDDEDİLDİ. "
                "Çözüm: python core/scripts/sync_yasaklar.py → sonra tekrar dene.\n")
            return 2

    # ADR 0010 — baglanti tutarsizligi gate: MCP eski sisteme bagliyken hicbir ADT islemi yapma.
    if tool_name.startswith("mcp__sap-adt__") and tool_name != "mcp__sap-adt__ping":
        mismatch, conn_label, mcp_label = _binding_mismatch()
        if mismatch:
            sys.stderr.write(
                "⛔ BAĞLANTI TUTARSIZLIĞI (PreToolUse guard, ADR 0010): "
                f".conn_adt artık '{conn_label}' sistemini işaret ediyor ama MCP hâlâ "
                f"'{mcp_label}' sistemine BAĞLI (switch_tier yapıldı, /mcp restart EDİLMEDİ). "
                "Bu durumda ADT isteği YANLIŞ sisteme gider (tier guard'ın okuduğu sistemle "
                "fiili hedef ayrışır → tehlikeli). İŞLEM REDDEDİLDİ. "
                "DUR → kullanıcıya bildir → kullanıcı '/mcp' ile yeniden bağlansın → tekrar dene.\n"
            )
            return 2  # blokla

    ti = data.get("tool_input", {}) or {}
    # Bash komutu veya MCP tool argümanları içinde ara
    hay = ""
    if isinstance(ti, dict):
        hay = ti.get("command", "") or json.dumps(ti, ensure_ascii=False)
    else:
        hay = str(ti)

    # ---- B9-4 FREEZE-GUARD (R10): dondurulmuş köke YAZMA teşebbüsü ----
    dosya_hedefi = ti.get("file_path", "") if isinstance(ti, dict) else ""
    if tool_name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        kok = _frozen_hit(dosya_hedefi)
        if kok:
            sys.stderr.write(
                f"⛔ FREEZE-GUARD (R10): '{kok}' DONDURULMUŞ SALT-OKUNUR yedek — yazma "
                f"YASAK (hedef: {dosya_hedefi}). Okuma serbesttir. Çalışma yeni dünyada "
                "(C:\\IX) yapılır. İŞLEM REDDEDİLDİ.\n")
            return 2
    if tool_name == "Bash":
        kok = _frozen_hit(hay)
        if kok and _YAZMA_FIILI.search(hay):
            sys.stderr.write(
                f"⛔ FREEZE-GUARD (R10): Bash komutu dondurulmuş kökü ('{kok}') yazma-fiiliyle "
                "birlikte içeriyor — eski dünyaya yazma YASAK (okuma: cat/grep/ls serbest). "
                "İŞLEM REDDEDİLDİ. Salt-okuma yapıyorsan komutu yazma-fiilsiz kur.\n")
            return 2

    # ---- PUBLIC-PR SIZINTI GATE: gh pr create → public repo → govde taramasi ----
    # Bash VE PowerShell birlikte: tek yuzeyi kapatmak gate degil, yavaslatmadir
    # (2026-07-09: Bash'te reddedilen komut PowerShell'den tunellenmeye calisildi).
    if tool_name in ("Bash", "PowerShell"):
        sorun = _gh_pr_public_leak(hay)
        if sorun:
            sys.stderr.write(
                f"⛔ PUBLIC-PR SIZINTI GATE: {sorun}\n"
                "PR başlığı/gövdesi PUBLIC repoya yayınlanır ve cache'lenir/indexlenir — "
                "sonradan silmek geri ALMAZ. core_precommit yalnız commit içeriğini tarar; "
                "PR gövdesi commit DEĞİLDİR, bu yüzden ayrı gate. İŞLEM REDDEDİLDİ.\n"
                "Çözüm: gövdeyi genericize et (gerçek paket adı → ZSD<NNN>/ZSD001 demo, "
                "sistem/kişi adı → <SYSTEM_ID>/<USER>), sonra tekrar dene. "
                "Gerçekten istisna ise: kullanıcıya sor, bypass etme.\n")
            return 2

    # ---- B9-5 ÖZYİNELEMELİ-SİLME BLOĞU (R9): core/junction hedefli silme ----
    if tool_name == "Bash" and _SILME_FIILI.search(hay) and _KORUNAN_SILME_HEDEF.search(hay):
        sys.stderr.write(
            "⛔ SİLME BLOĞU (R9): Özyinelemeli silme/clean komutu core-junction veya "
            ".claude/{agents,skills,commands} hedefini içeriyor. Güncel toolchain junction "
            "içine inmiyor (kanıtlı) ama araç-çeşitliliği sigortası olarak BLOKLU. "
            "Junction'ı kaldırmak istiyorsan: `cmd /c rmdir <link>` (yalnız linki kaldırır). "
            "git clean gerekiyorsa önce `-n` ile önizle + core junction'ını geçici kaldır. "
            "İŞLEM REDDEDİLDİ.\n")
        return 2

    # ---- B9-7 SIZINTI-COMMIT KİLİDİ (2.7/F1): proje reposunda core-path stage'leme ----
    if tool_name == "Bash" and _GIT_STAGE.search(hay) and re.search(
            r"(\bcore[/\\]|\s\.claude[/\\](agents|skills|commands))", hay):
        sys.stderr.write(
            "⛔ SIZINTI-COMMIT KİLİDİ (F1/2.7): `git add/commit` kapsamında core-junction "
            "içeriği var — core proje reposuna COMMIT'LENEMEZ (fikri-sermaye sızıntısı, R1). "
            "core/ zaten .gitignore'ludur; bu komut kasıtlı zorlama olurdu. İŞLEM REDDEDİLDİ.\n")
        return 2

    # ---- B9-6 CORE-YAZIM TARAMASI (Ö5): core'a yazım anında leak + applies_to ----
    if tool_name in ("Edit", "Write", "MultiEdit") and _core_hedef_mi(dosya_hedefi):
        icerik = ""
        if isinstance(ti, dict):
            icerik = (ti.get("content", "") or ti.get("new_string", "") or "")
        m = _CORE_LEAK.search(icerik)
        if m:
            sys.stderr.write(
                f"⛔ GENERICIZE-LEAK (Ö5/B9): core'a yazılan içerikte proje/müşteri izi "
                f"tespit edildi: '{m.group(0)}' (hedef: {dosya_hedefi}). Core'a yalnız "
                "jenerik içerik girer (SORU 0: placeholder kullan — <PROJECT_NAME>, "
                "<LEGACY_SOURCE>, <SAP_USER>, ZSD001-örnek). İŞLEM REDDEDİLDİ.\n")
            return 2
        d = dosya_hedefi.replace("\\", "/").lower()
        if (tool_name == "Write" and d.endswith(".md")
                and ("/standards/" in d or "/playbook/" in d)
                and "applies_to:" not in icerik[:500]):
            sys.stderr.write(
                "⛔ APPLIES_TO EKSİK (D21/B9): standards|playbook altına yeni .md, "
                "profil etiketi olmadan yazılamaz. Dosya başına frontmatter ekle:\n"
                "---\napplies_to: [s4_private]\n---\n(SORU 0 4. soru). İŞLEM REDDEDİLDİ.\n")
            return 2

    if _DANGER.search(hay):
        sys.stderr.write(
            "⛔ ADR 0005-C İHLALİ (PreToolUse guard): transport release/create veya "
            "package create teşebbüsü tespit edildi. Bu YASAK — transport'u kullanıcı "
            "release eder, yeni transport/package yaratılmaz. DUR → kullanıcıya bildir.\n"
        )
        return 2  # blokla

    # INLINE AKTİVASYON guard (2026-06-11 dersi / adt-rap §34-D): Bash içinde elle
    # '/sap/bc/adt/activation' POST'u activationExecuted'ı parse ETMEZ → HTTP 200 sahte-OK
    # üretir (metadata eski kalır, saatler kayboldu). Helper'a zorla.
    if (tool_name == "Bash" and "adt/activation" in hay and ".post(" in hay
            and "activate_and_verify" not in hay and "_activation_failures" not in hay):
        sys.stderr.write(
            "⛔ INLINE AKTİVASYON (PreToolUse guard, 2026-06-11 dersi / adt-rap §34-D): "
            "Bash içinde elle '/sap/bc/adt/activation' POST'u tespit edildi. Bu yol "
            "activationExecuted'ı PARSE ETMEZ → HTTP 200 SAHTE-OK üretir (metadata eski kalır). "
            "Bunun yerine create_rap_service.activate_and_verify(client, tok, refs) KULLAN — "
            "activationExecuted!=true VEYA type=E varsa exception fırlatır (sahte-OK imkansiz). "
            "İŞLEM REDDEDİLDİ.\n"
        )
        return 2  # blokla

    # YALIN FIORI DEPLOY guard (2026-07-06 stale-dist dersi): build'siz `fiori deploy` eski
    # dist'i yükler + "Deployment Successful" der ama canlıya bayat gider. Kanonik yol
    # scripts/deploy_ui.py (build ZORUNLU + deploy + canlı Component-preload==dist doğrulaması).
    if tool_name == "Bash" and _FIORI_DEPLOY.search(hay) and "deploy_ui.py" not in hay:
        sys.stderr.write(
            "⛔ YALIN FIORI DEPLOY (PreToolUse guard, 2026-07-06 stale-dist dersi): "
            "Doğrudan 'fiori deploy' BUILD YAPMAZ — eski dist/'i archive edip 'Deployment "
            "Successful' DER ama canlıya BAYAT içerik gider (3 tur sessiz stale, kullanıcı "
            "yakaladı). Bunun yerine KANONİK yolu kullan: "
            "`python scripts/deploy_ui.py --apps <app1,app2>` (build ZORUNLU + deploy + "
            "canlı Component-preload==dist HASH doğrulaması; 'Successful' yalanını yakalar). "
            "İŞLEM REDDEDİLDİ. Bkz. standards/03 §2.4.1 + feedback_ui-deploy-noninteractive madde 8.\n"
        )
        return 2  # blokla

    # APP-İÇİ NPM INSTALL guard (standards/03 §; paket-seviye ui/ npm workspace):
    # app dizininde `npm install/ci/add` YASAK → tooling ui/node_modules'a hoist'lu.
    # Sıcak-yol: npm-install içermeyen Bash'te _NPM_INSTALL.search anında fail (FS'ye dokunmaz).
    if tool_name == "Bash" and _NPM_INSTALL.search(hay):
        cdm = re.search(r"\bcd\s+(?:\"([^\"]+)\"|'([^']+)'|([^\s&|;]+))", hay)
        cd_target = next((g for g in (cdm.groups() if cdm else ()) if g), "") if cdm else ""
        hit = _ui_app_subdir(cd_target) or _ui_app_subdir(data.get("cwd", "") or "")
        if hit:
            ui_root, app = hit
            sys.stderr.write(
                f"⛔ APP-İÇİ NPM INSTALL (PreToolUse guard, standards/03): '{app}' app "
                f"dizininde npm install/ci/add YASAK — '{ui_root}' paket-seviye npm workspace "
                "kökü, tooling zaten ui/node_modules'a hoist'lu. Lokal çalıştırmak için KURULUM "
                "GEREKMEZ: app dizininden `npm run start-noflp` (canlı backend) / `start-mock`. "
                f"Bağımlılık eklemen gerekiyorsa `cd {ui_root} && npm install` (workspace kökü). "
                "İŞLEM REDDEDİLDİ.\n"
            )
            return 2  # blokla
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
