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
# NOT: eski `_FIORI_DEPLOY` düz string-araması KALDIRILDI — `grep -rn 'fiori deploy' docs/`
# gibi ARAMA komutlarını bloklıyordu. Yerine `_komut_konumunda()` (tırnak-dışı, komut konumu).


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

# NOT: eski `_YAZMA_FIILI` (fiil kara-listesi) KALDIRILDI — hedefi sormuyordu, iki yönde
# birden bozuktu. Yerine `_frozen_yazma_hedefi()` (yazma-hedefi analizi) geçti.

_SILME_FIILI = re.compile(
    r"(\brm\s+-[a-z]*r[a-z]*f?|\brm\s+-[a-z]*f[a-z]*r|Remove-Item[^\n|;]*-Recurse"
    r"|\brimraf\b|\brmdir\s+/s|\bgit\s+clean\b(?![^\n]*-n)"
    # Kabuk-dışı silme yolları: `rm -rf` yakalanıp `shutil.rmtree` kaçıyordu (2026-07-09)
    r"|shutil\.rmtree|os\.removedirs|\bfind\b[^\n]*-delete\b)", re.IGNORECASE)

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

    Kaynak: proje-özel liste **BİRLEŞİR**, ezmez.
      1. env `IX_GENERICIZE_BLOCKLIST` (virgülle ayrılmış) VEYA
         `<proje>/.claude/genericize-blocklist.txt` (satır başına bir desen; `#` yorum;
         **.gitignore'lu** — repoya girmez)
      2. + jenerik yapısal desenler (aşağıda) — HER ZAMAN eklenir

    ⚠ Eskiden "ilk bulunan kazanır"dı: proje bir blocklist tanımladığı anda jenerik
    desenler DÜŞÜYORDU. Sonuç tersineydi — daha fazla yapılandırma, daha az koruma:
    blocklist'li bir projede makine-lokal kullanıcı yolu ve gerçek e-posta core'a
    sızabiliyordu (2026-07-09 denetimi, canlı ölçümle doğrulandı). Artık birleşim.

    Kısaltma/obfuscation (ör. ilk 4 harf) ÇÖZÜM DEĞİL: bağlamda tahmin edilir ve
    masum kelimeleri bloklar (yanlış-pozitif).
    """
    # Jenerik yapısal desenler: isim YOK. PLACEHOLDER muaftır — dokümantasyon örnekleri
    # yanlış-pozitif üretiyordu (`C:\Users\<USER>`, `user@example.com`).
    jenerik = [
        r"C:[/\\]+Users[/\\]+(?!<)[^/\\ ]+",                 # makine-lokal kullanıcı yolu
        # e-posta: RFC 2606 rezerve/örnek domainleri HARİÇ
        r"[A-Za-z0-9._%+-]+@(?!example\.(?:com|org|net)\b)(?!test\b)(?!localhost\b)"
        r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    ]

    proje: list[str] = []
    env = os.environ.get("IX_GENERICIZE_BLOCKLIST", "").strip()
    if env:
        proje = [p.strip() for p in env.split(",") if p.strip()]
    else:
        dosya = _PROJ_ROOT / ".claude" / "genericize-blocklist.txt"
        if dosya.exists():
            try:
                satirlar = dosya.read_text(encoding="utf-8", errors="replace").splitlines()
                proje = [s.strip() for s in satirlar
                         if s.strip() and not s.lstrip().startswith("#")]
            except Exception:
                proje = []

    return proje + jenerik


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


# Kabuk yüzeyleri: bir kural yalnız Bash'i kapatırsa, aynı komut PowerShell'den geçer.
# (2026-07-09 denetimi: freeze-guard ve R9-silme bloğu `tool_name == "Bash"` ile
# sınırlıydı → `Remove-Item -Recurse core` PowerShell aracından HİÇ bloklanmıyordu.)
_KABUK_TOOLLARI = ("Bash", "PowerShell")
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

    SINIR ŞARTI: kökten sonra ya metin biter ya ayraç gelir. Çıplak substring kıyası
    `<LEGACY_SOURCE>_YENI` gibi BAŞKA bir kökü de eşleştiriyordu (2026-07-09 denetimi).
    """
    if not _FROZEN or not metin:
        return ""
    duz = _canon_path(metin)
    for kok in _FROZEN:
        if not kok:
            continue
        i = 0
        while True:
            i = duz.find(kok, i)
            if i < 0:
                break
            son = i + len(kok)
            if son == len(duz) or duz[son] in "/ \"'\t":
                return kok
            i = son
    return ""


# ── FREEZE-GUARD yeniden tasarımı (2026-07-09 denetimi) ────────────────────────
# ESKİ TASARIM: "komutta yazma-FİİLİ var mı + donmuş kök geçiyor mu" → ikisi de
# doğruysa blokla. Hedefi hiç sormuyordu; İKİ YÖNDE birden bozuktu:
#   YANLIŞ-POZİTİF: `ls <FROZEN> 2>&1`      → `2>&1`'deki `>` "yazma fiili" sayıldı
#                   `cp <FROZEN>/x ./y`     → kaynak okuma, hedef yerel
#                   `grep x <FROZEN> > o.txt` → yazma hedefi o.txt
#   YANLIŞ-NEGATİF: `python -c "open('<FROZEN>/x','w')"` → fiil listesinde yok, GEÇTİ
#                   `tar -xzf y.tgz -C <FROZEN>`         → GEÇTİ
# YENİ SORU: "yazma fiili var mı" DEĞİL → **"yazmanın HEDEFİ donmuş kök mü?"**
_AYRAC = re.compile(r"\s*(?:\|\||&&|[;|&\n])\s*")
_REDIRECT = re.compile(r"(?:\d*>>?|&>)\s*(\S+)")           # `> x`, `2> x`, `>> x`, `&> x`
_SIL_FIIL = re.compile(r"\b(rm|rmdir|rimraf|unlink|del)\b|Remove-Item|shutil\.rmtree"
                       r"|os\.remove|os\.unlink|\.unlink\(|-delete\b", re.IGNORECASE)
_TASI_FIIL = re.compile(r"\bmv\b|Move-Item", re.IGNORECASE)
_KOPYA_FIIL = re.compile(r"\bcp\b|\bcopy\b|Copy-Item|robocopy|xcopy", re.IGNORECASE)
_ARSIV = re.compile(r"\b(tar|unzip|7z|gunzip)\b", re.IGNORECASE)
_YARAT_FIIL = re.compile(r"\b(touch|mkdir|tee)\b|\bsed\s+-i\b|Set-Content|Out-File"
                         r"|Add-Content|New-Item", re.IGNORECASE)
_YORUMLAYICI = re.compile(r"\b(python3?|node|perl|ruby|pwsh)\b|\b(?:bash|sh|powershell)\s+-c",
                          re.IGNORECASE)
# Yorumlayıcı gövdesinde YAZMA göstergesi. Yoksa okuma sayılır →
# `python -c "print(open(f).read())"` meşru kalır.
_KOD_YAZMA = re.compile(r"""['"][wax]\+?['"]|write_text|write_bytes|writelines|\.write\("""
                        r"""|rmtree|remove\(|unlink\(|makedirs|mkdir\(|copy2?\(|move\(""",
                        re.IGNORECASE)


def _yol_argumanlari(seg: str) -> list:
    """Segmentteki yol-benzeri argümanlar (bayrak değil, tırnaksız)."""
    out = []
    for t in seg.split():
        t = t.strip("\"'")
        if t.startswith("-") or not t:
            continue
        out.append(t)
    return out


def _korunan_hedefe_mi(seg: str, fiil: "re.Pattern", cwd_korunan: bool = False) -> bool:
    """<fiil> segmentte var VE korunan hedef (core/junction) o segmentin ARGÜMANI mı?

    Eski kontrol `fiil.search(cmd) and hedef.search(cmd)` idi: `cd <CORE_REPO> && rm -rf
    .tmp/x` bloklanıyordu (silme hedefi .tmp; core yalnız `cd` argümanı). Hedefe bak,
    satıra değil. Segmentin TÜM yol argümanlarına bakmak güvenlidir: `cd <CORE_REPO>`
    ayrı bir segmenttir, silme segmentinde geçmez.

    `find <hedef> ... -delete` biçiminde hedef fiilden ÖNCE gelir → "fiilden sonrası"na
    bakmak onu kaçırıyordu (2026-07-09 denetimi).
    """
    if not fiil.search(seg):
        return False
    for a in _yol_argumanlari(seg):
        if _KORUNAN_SILME_HEDEF.search(a):
            return True
    # `git clean` argümansızdır ama CWD'yi siler → cwd korunan alandaysa blokla.
    if re.search(r"git\s+clean", seg, re.IGNORECASE) and cwd_korunan:
        return True
    return False


def _cwd_korunan_mi(komut: str) -> bool:
    """Komutun herhangi bir yerinde korunan alana `cd` var mı (git clean için cwd riski)."""
    for c in _CD_PREFIX.finditer(komut):
        if _KORUNAN_SILME_HEDEF.search(c.group(1)):
            return True
    return False


def _komut_konumunda(seg: str, desen: str) -> bool:
    """Desen KOMUT konumunda mı (satır başı / ayraç sonrası), yoksa tırnak içinde bir arg mı?

    `grep -rn 'fiori deploy' docs/` fiori'yi ÇALIŞTIRMAZ — string olarak arar.
    """
    tırnaksız = re.sub(r"'[^']*'|\"[^\"]*\"", " ", seg)      # tırnaklı bölgeleri düşür
    return re.search(r"(?:^|[\n;|&(])\s*(?:\w+\s+)?" + desen, tırnaksız, re.IGNORECASE) is not None


def _frozen_yazma_hedefi(komut: str) -> str:
    """Komut donmuş köke YAZIYOR mu? Yazıyorsa kökü, yazmıyorsa '' döndürür.

    Segment segment (`;` `&&` `||` `|` ile bölünür): donmuş kök geçen HER segment için
    "bu kök bir yazma HEDEFİ mi, yoksa okuma ARGÜMANI mı" sorulur.
    """
    if not _FROZEN:
        return ""
    for seg in _AYRAC.split(komut):
        kok = _frozen_hit(seg)
        if not kok:
            continue

        # 1) Yönlendirme hedefi donmuş kök mü? (`2>&1` ve `>/dev/null` hedefi donmuş DEĞİL)
        for hedef in _REDIRECT.findall(seg):
            if _frozen_hit(hedef):
                return kok

        # 2) Silme/taşıma: donmuş kök argümansa yazmadır (mv kaynağı da siler)
        if _SIL_FIIL.search(seg) or _TASI_FIIL.search(seg):
            return kok

        # 3) Kopyalama: yalnız HEDEF (son yol argümanı) donmuşsa yazma; kaynak okumadır
        if _KOPYA_FIIL.search(seg):
            yollar = [t for t in seg.split() if "/" in t or "\\" in t]
            if yollar and _frozen_hit(yollar[-1]):
                return kok
            continue                                   # kaynak okuma → segment temiz

        # 4) Arşiv: listeleme okuma; diğer her kullanım fail-closed.
        #    `-t` birleşik bayrak kümesinde olabilir (`tar -tzf`) → `-t\b` YETMEZ.
        if _ARSIV.search(seg):
            if re.search(r"(?:^|\s)-[a-zA-Z]*t[a-zA-Z]*(?:\s|$)|--list\b", seg):
                continue
            return kok

        # 5) Dosya yaratma/yerinde-değiştirme fiilleri
        if _YARAT_FIIL.search(seg):
            return kok

        # 6) Yorumlayıcı: gövdede yazma göstergesi VARSA blokla, yoksa okuma say
        if _YORUMLAYICI.search(seg) and _KOD_YAZMA.search(seg):
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

    # ---- TEK NORMALİZASYON: komut-niyeti kuralları `komut` üzerinde çalışır ----
    # `hay` ham metindir: heredoc/here-string GÖVDESİ de içindedir. O gövde VERİdir
    # (commit mesajı, PR gövdesi), komut değil. Ham metin üzerinde desen aramak, bir
    # kuralın kendi dokümantasyonunu bloklamasına yol açar — 2026-07-09'da üç ayrı
    # guard'da (freeze / R9-silme / PUBLIC-PR) arka arkaya yaşandı; tek tek yamamak
    # yerine burada BİR KEZ çözülür. Yeni komut-niyeti kuralı `komut` kullanmalıdır.
    #
    # Kabuk yüzeyi TEK DEĞİL: Bash'te bloklanan komut PowerShell'den tünellenebilir
    # (aynı gün denendi). Kabuk-kuralları her iki araca da uygulanır.
    komut = _komut_govdesi(hay) if tool_name in _KABUK_TOOLLARI else hay

    # ---- B9-4 FREEZE-GUARD (R10): dondurulmuş köke YAZMA teşebbüsü ----
    # NotebookEdit'in hedef anahtarı `notebook_path` (file_path DEĞİL) — yalnız file_path
    # okumak o tool'u sessizce muaf tutuyordu (2026-07-09 denetimi).
    dosya_hedefi = ""
    if isinstance(ti, dict):
        dosya_hedefi = ti.get("file_path", "") or ti.get("notebook_path", "") or ""
    if tool_name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        kok = _frozen_hit(dosya_hedefi)
        if kok:
            sys.stderr.write(
                f"⛔ FREEZE-GUARD (R10): '{kok}' DONDURULMUŞ SALT-OKUNUR yedek — yazma "
                f"YASAK (hedef: {dosya_hedefi}). Okuma serbesttir. Çalışma yeni dünyada "
                "(C:\\IX) yapılır. İŞLEM REDDEDİLDİ.\n")
            return 2
    if tool_name in _KABUK_TOOLLARI:
        kok = _frozen_yazma_hedefi(komut)
        if kok:
            sys.stderr.write(
                f"⛔ FREEZE-GUARD (R10): komut dondurulmuş köke ('{kok}') YAZIYOR — eski "
                "dünyaya yazma YASAK. OKUMA serbesttir (ls/cat/grep/find/diff, `cp <FROZEN>/x .`, "
                "`python -c \"open(f).read()\"`, `tar -t`). İŞLEM REDDEDİLDİ.\n"
                "Not: yazma-hedefi analizi yapılır — `2>&1` / `>/dev/null` yazma sayılmaz, "
                "ama `> <FROZEN>/x`, `tar -C <FROZEN>`, `open(...,'w')` sayılır.\n")
            return 2

    # ---- PUBLIC-PR SIZINTI GATE: gh pr create → public repo → govde taramasi ----
    # Bash VE PowerShell birlikte: tek yuzeyi kapatmak gate degil, yavaslatmadir
    # (2026-07-09: Bash'te reddedilen komut PowerShell'den tunellenmeye calisildi).
    if tool_name in _KABUK_TOOLLARI:
        sorun = _gh_pr_public_leak(komut)
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
    _cwd_kor = _cwd_korunan_mi(komut) if tool_name in _KABUK_TOOLLARI else False
    if tool_name in _KABUK_TOOLLARI and any(
            _korunan_hedefe_mi(seg, _SILME_FIILI, _cwd_kor) for seg in _AYRAC.split(komut)):
        sys.stderr.write(
            "⛔ SİLME BLOĞU (R9): Özyinelemeli silme/clean komutu core-junction veya "
            ".claude/{agents,skills,commands} hedefini içeriyor. Güncel toolchain junction "
            "içine inmiyor (kanıtlı) ama araç-çeşitliliği sigortası olarak BLOKLU. "
            "Junction'ı kaldırmak istiyorsan: `cmd /c rmdir <link>` (yalnız linki kaldırır). "
            "git clean gerekiyorsa önce `-n` ile önizle + core junction'ını geçici kaldır. "
            "İŞLEM REDDEDİLDİ.\n")
        return 2

    # ---- B9-7 SIZINTI-COMMIT KİLİDİ (2.7/F1): proje reposunda core-path stage'leme ----
    # HEDEF-tabanlı: `git add`/`stage`/`commit`'in ARGÜMANLARINDA core var mı? Satırda
    # başka amaçla geçen `core/...` (ör. `git add p.py && python core/scripts/x.py`)
    # staging kapsamı DEĞİLDİR (2026-07-09 denetimi: bu yanlış-pozitif canlı yakalandı).
    _CORE_ARG = re.compile(r"(^|[/\\])core[/\\]|^core$|[/\\]?\.claude[/\\](agents|skills|commands)")
    def _stage_kapsaminda_core(seg: str) -> bool:
        m = _GIT_STAGE.search(seg)
        if not m:
            return False
        return any(_CORE_ARG.search(a) for a in _yol_argumanlari(seg[m.end():]))

    if tool_name in _KABUK_TOOLLARI and any(
            _stage_kapsaminda_core(seg) for seg in _AYRAC.split(komut)):
        sys.stderr.write(
            "⛔ SIZINTI-COMMIT KİLİDİ (F1/2.7): `git add/commit` kapsamında core-junction "
            "içeriği var — core proje reposuna COMMIT'LENEMEZ (fikri-sermaye sızıntısı, R1). "
            "core/ zaten .gitignore'ludur; bu komut kasıtlı zorlama olurdu. İŞLEM REDDEDİLDİ.\n")
        return 2

    # ---- B9-6 CORE-YAZIM TARAMASI (Ö5): core'a yazım anında leak + applies_to ----
    if tool_name in ("Edit", "Write", "MultiEdit", "NotebookEdit") and _core_hedef_mi(dosya_hedefi):
        # MultiEdit içeriği `edits[].new_string` altındadır; NotebookEdit `new_source`.
        # Yalnız content/new_string okumak ikisini de SESSİZCE muaf tutuyordu → core'a
        # kimlik izi yazma kapısı açıktı (2026-07-09 denetimi, kanıtlı).
        parcalar = []
        if isinstance(ti, dict):
            for anahtar in ("content", "new_string", "new_source"):
                v = ti.get(anahtar)
                if isinstance(v, str):
                    parcalar.append(v)
            for e in (ti.get("edits") or []):
                if isinstance(e, dict) and isinstance(e.get("new_string"), str):
                    parcalar.append(e["new_string"])
        icerik = "\n".join(parcalar)
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

    if _DANGER.search(komut):
        sys.stderr.write(
            "⛔ ADR 0005-C İHLALİ (PreToolUse guard): transport release/create veya "
            "package create teşebbüsü tespit edildi. Bu YASAK — transport'u kullanıcı "
            "release eder, yeni transport/package yaratılmaz. DUR → kullanıcıya bildir.\n"
        )
        return 2  # blokla

    # INLINE AKTİVASYON guard (2026-06-11 dersi / adt-rap §34-D): Bash içinde elle
    # '/sap/bc/adt/activation' POST'u activationExecuted'ı parse ETMEZ → HTTP 200 sahte-OK
    # üretir (metadata eski kalır, saatler kayboldu). Helper'a zorla.
    if (tool_name in _KABUK_TOOLLARI and "adt/activation" in komut and ".post(" in komut
            and "activate_and_verify" not in komut and "_activation_failures" not in komut):
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
    # KOMUT konumunda mı, yoksa tırnak içinde ARANAN bir string mi? `grep -rn 'fiori deploy'
    # docs/` deploy ETMEZ (2026-07-09 denetimi).
    if tool_name in _KABUK_TOOLLARI and "deploy_ui.py" not in komut and any(
            _komut_konumunda(seg, r"(?:npx\s+)?fiori\s+deploy") for seg in _AYRAC.split(komut)):
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
    if tool_name in _KABUK_TOOLLARI and _NPM_INSTALL.search(komut):
        cdm = re.search(r"\bcd\s+(?:\"([^\"]+)\"|'([^']+)'|([^\s&|;]+))", komut)
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
