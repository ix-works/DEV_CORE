#!/usr/bin/env python3
"""PreToolUse guard — çok-katman, 8 kural (2026-07-10 sadeleştirmesi).

MERDİVEN İLKESİ (ADR 0019 revizyonu): runtime guard YALNIZ
**geri alınamaz VE sessizce başarısız olan** eylemler için meşrudur. Bir kural bu iki
kriterden birini karşılamıyorsa statik kontrole (validator / pre-commit / CI) iner.

KALAN KURALLAR (hepsi kriteri karşılar):
1) KESİN YASAKLAR damgası (ADR 0005) — damga silinirse SESSİZ; anayasasız SAP yazımı.
2) ADR 0010 bağlantı tutarsızlığı — yanlış sisteme yazım GERİ ALINAMAZ, HTTP 200 SESSİZ.
3) ADR 0005-C transport release — GERİ ALINAMAZ, HTTP 200 SESSİZ.
4) PUBLIC-PR sızıntı gate — yayınlanan gövde cache'lenir (GERİ ALINAMAZ); gh sessiz başarı der.
5) INLINE AKTİVASYON — HTTP 200 sahte-OK (SESSİZ).
6) YALIN FIORI DEPLOY — "Successful" der, bayat dist gider (SESSİZ).
7) APP-İÇİ NPM INSTALL — workspace ihlali.
8) GENERICIZE-LEAK — core PUBLIC; yazılan kimlik izi push'lanınca GERİ ALINAMAZ.
9) GH HEDEF BELİRSİZ — `gh` hedefi cwd'den çıkarır ve `core/` bir JUNCTION'dır; yanlış
   repoya yayın/mutasyon GERİ ALINAMAZ ve `gh` başarı döner (SESSİZ). Repoyu DEĞİŞTİREN
   her alt-komutta hedef açık olmalı (`--repo`/`-R` ya da `gh api repos/<o>/<r>/...`).

2026-07-10'da KALDIRILAN 4 kural (sağlık denetimi; her biri için ayrı gerekçe):
- FREEZE-GUARD (R10): donmuş kök git-remote'ta yedekli → yazma GERİ ALINABİLİR. Ayrıca
  fiil-kara-listesi 6 yoldan sızdırıyordu (dd · install · git clean · git checkout ·
  heredoc-redirect · PowerShell değişken ataması). Koruma OS izniyle (① tasarım katmanı)
  yapılır, komut-metni regex'iyle değil.
- SİLME BLOĞU (R9): junction silme GERİ ALINABİLİR (team_setup --repair-junctions) ve
  SESSİZ DEĞİL (hook_shim fail-closed bağırır). Ölçüm: bloklanan `rm -rf` yerine aynı
  dizin `shutil.rmtree` ile silindi → guard aracı değiştirtti, sonucu değil.
- SIZINTI-COMMIT KİLİDİ: `core/` zaten .gitignore'lu; `git reset` ile GERİ ALINABİLİR ve
  iki ikizi var (check_core_not_committed validator + CI core-leak job).
- APPLIES_TO EKSİK: yalnız `Write`'ı tutuyordu; `cp` / `Edit` ile atlanıyordu (yarım
  koruma, tam gürültü). Kesin gate core_precommit + CI'dadır.

ADR 0005-C korundu ama YÜZEYİ daraltıldı — aşağıdaki eş-oluşum notuna bakınız.

Tehlikeli/tutarsız değilse sessiz (exit 0). Blokta exit 2 (stderr → Claude'a geri besler).
ŞARTNAME: scripts/tests/guard_conformance.py — her kural için ③tetiklenmeli / ④tetiklenmemeli
vakaları + kablolama + meta-gate. Kanıtsız kural CI'yı kırar.
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


# ── ADR 0005-C: transport release / create ───────────────────────────────────────
# ESKİ TASARIM (2026-07-10'da değişti): çıplak token araması + `tool_name` kontrolü YOK.
# `hay` Edit/Write için `json.dumps(tool_input)` olduğundan **dosya içeriği** taranıyordu.
# Sonuç: bu kuralı ANLATAN her doküman, her `grep`, her commit mesajı bloklanıyordu
# (canlı: bir oturumda 4 meşru blok; bağımsız korpusta 7 yanlış-pozitif). Guard'ın kendi
# test dosyası yazılamıyordu — koruma in-band test edilemez hâle gelmişti.
#
# YENİ TASARIM: **eş-oluşum (co-occurrence)**. Bir token tek başına metindir; ancak onu
# ÇALIŞTIRAN bağlamla birlikte geçtiğinde komuttur.
#   release endpoint  → yalnız bir HTTP fiiliyle birlikte
#   release FM adı    → yalnız bir ABAP/RFC çağrı bağlamıyla birlikte
#   tool fonksiyonu   → yalnız çağrı parantezi ile
#   client copy       → yalnız ABAP çalıştırma bağlamında (post_shell / classrun)
# Yüzey: kabuk (Bash/PowerShell) + keyfi ABAP çalıştıran iki MCP tool'u.
# Edit/Write/MultiEdit/NotebookEdit ASLA: bir dosya yazmak transport release ETMEZ.
#
# ⚠ Desenler bilerek PARÇALI literal olarak kuruluyor: tek parça yazılsaydı guard'ın
# kendi kuralı bu dosyanın yazılmasını bloklardı (öz-gönderme tuzağı, 2026-07-09).
_TOK_ENDPOINT = re.compile(r"\bnewrelease" r"jobs\b", re.IGNORECASE)
_TOK_FM = re.compile(r"\b(?:trint_release" r"_request|tr_release" r"_request)\b", re.IGNORECASE)
_TOK_FN = re.compile(r"\b(?:create|release)" r"Transport\s*\(", re.IGNORECASE)
_TOK_CLIENTCOPY = re.compile(r"\bSCC" r"1\b", re.IGNORECASE)

_HTTP_FIIL = re.compile(
    r"\b(curl|wget|Invoke-RestMethod|Invoke-WebRequest|httpx)\b"
    r"|requests\.(?:post|put|delete)\b|\.post\(|\.put\(", re.IGNORECASE)
_ABAP_EXEC = re.compile(
    r"\bCALL\s+FUNCTION\b|\bCALL\s+TRANSACTION\b|\bSUBMIT\b|\.rfc\(|call_function",
    re.IGNORECASE)

_ABAP_TOOLLARI = ("mcp__sap-adt__adt_post_shell", "mcp__sap-adt__adt_classrun")


def _adr0005c_sorunu(metin: str, abap_baglami: bool) -> str:
    """Metin bir transport release/create TEŞEBBÜSÜ mü? Değilse ''."""
    if _TOK_FN.search(metin):
        return "transport create/release fonksiyon çağrısı"
    if _TOK_ENDPOINT.search(metin) and _HTTP_FIIL.search(metin):
        return "ADT transport release endpoint'ine HTTP isteği"
    if _TOK_FM.search(metin) and (abap_baglami or _ABAP_EXEC.search(metin)):
        return "transport release function module çağrısı"
    if abap_baglami and _TOK_CLIENTCOPY.search(metin) and _ABAP_EXEC.search(metin):
        return "request-bazlı client copy çalıştırma"
    return ""


_NPM_INSTALL = re.compile(r"\bnpm\s+(?:install|ci|add|i)\b", re.IGNORECASE)


def _proje_koku() -> Path:
    """PROJE kökü. env CLAUDE_PROJECT_DIR → cwd (junction'da __file__ CORE'a çözülür)."""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(env) if env else Path.cwd()


_PROJ_ROOT = _proje_koku()


def _ui_app_subdir(path: str):
    """path bir UI app alt-dizini mi (`.../ui/<app>`, ui/ workspace kökü DEĞİL)?"""
    if not path:
        return None
    p = path.replace("\\", "/")
    m = re.search(r"(.*/ui)/([^/]+)", p)
    if not m:
        return None
    ui_root, app = m.group(1), m.group(2).strip()
    if not app or app in (".", ".."):
        return None
    root = _proje_koku()
    ui_path = Path(ui_root) if Path(ui_root).is_absolute() else (root / ui_root)
    pkg = ui_path / "package.json"
    try:
        if pkg.exists() and "workspaces" in pkg.read_text(encoding="utf-8", errors="ignore"):
            return (ui_root, app)
    except Exception:
        return None
    return None


# TEK KAYNAK (D9): desenler `scripts/genericize_common.py`'de; `core_precommit` de aynı
# modülü kullanır. Eskiden iki guard iki AYRI dosyadan besleniyordu (biri
# `<proje>/.claude/...`, diğeri `<git-dir>/...`) → biri güncellenip diğeri unutulabiliyordu.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from genericize_common import id_pattern, sizintilari_bul  # noqa: E402

_CORE_LEAK = id_pattern(proje_koku=_PROJ_ROOT)  # IGNORECASE (D2)

# Desen tanımlayan dosyalar: taranırlarsa kendi desenlerine takılırlar (core_precommit'te
# SCAN_EXEMPT olarak vardı, burada yoktu). Dosya ADIYLA eşleşir — yol makineye göre değişir.
_DESEN_TANIMLAYAN = frozenset({
    "genericize_common.py",
    "core_precommit.py",
    "pre_tool_guard.py",
})

# D7 (2026-07-10 denetimi): eskiden yalnız `gh pr create` tutuluyordu. Aynı geri-alınamaz
# yayını yapan `pr edit` / `pr comment` / `issue create` / `release create --notes` /
# `api .../pulls` yan kapılardan geçiyordu; `-t`/`-b` kısa bayrakları da görülmüyordu.
_GH_PUBLIC_YAYIN = re.compile(
    r"(?:^|[\n;|&(])\s*(?:[A-Za-z_]\w*=\S+\s+)*gh\s+"
    r"(?:pr\s+(?:create|edit|comment)"
    r"|issue\s+(?:create|edit|comment)"
    r"|release\s+create"
    r"|api\s+\S*(?:pulls|issues|releases)\S*)\b",
    re.IGNORECASE)
_GH_PR_CREATE = _GH_PUBLIC_YAYIN  # geriye dönük ad (guard_conformance şartnamesi)

# 2026-07-10: `gh`, hedef repoyu `--repo` yoksa CWD'den çıkarır. `core/` bir JUNCTION'dır →
# yanlış dizinde çalışan bir mutasyon komutu private proje içeriğini PUBLIC çekirdeğe
# yayınlayabilir ya da yanlış repoyu değiştirebilir. Yayın cache'lenir: GERİ ALINAMAZ.
# Kapsam: repoyu DEĞİŞTİREN alt-komutlar. Okuma komutları (list/view/status) serbesttir.
# ⚠ KOMUT-BAŞI ÇAPASI ŞART: çapasız desen `git commit -m 'gh pr create ...'` gibi bir commit
# MESAJINI komut sanar (guard_conformance ④ vakası bunu yakaladı, 2026-07-10).
_GH_MUTASYON = re.compile(
    r"(?:^|[\n;|&(])\s*(?:[A-Za-z_]\w*=\S+\s+)*gh\s+("
    r"pr\s+(create|edit|comment|merge|close|reopen|ready|review)"
    r"|issue\s+(create|edit|comment|close|reopen|delete)"
    r"|release\s+(create|edit|delete|upload)"
    r"|repo\s+(create|edit|rename|delete|archive|deploy-key)"
    r"|secret\s+(set|delete)"
    r"|variable\s+(set|delete)"
    r"|workflow\s+(run|enable|disable)"
    r"|ruleset\b"
    r"|label\s+(create|edit|delete|clone)"
    r"|api\b"
    r")", re.IGNORECASE)

# Hedefi açıkça bildiren biçimler: `--repo o/r` · `-R o/r` · `gh api repos/o/r/...`
# (ve `orgs/<o>/...` — org-hedefli API çağrıları da açıktır).
_GH_HEDEF_ACIK = re.compile(
    r"(?<![\w-])(--repo[= ]\S+|-R[= ]\S+)"
    r"|(?<![\w/])(repos|orgs)/[\w.-]+/", re.IGNORECASE)


def _gh_hedef_belirsiz(komut: str) -> str:
    """Repoyu değiştiren `gh` komutunda hedef açıkça verilmemişse RED gerekçesi döner."""
    if not _GH_MUTASYON.search(komut):
        return ""
    if _GH_HEDEF_ACIK.search(komut):
        return ""
    return ("hedef repo BELİRSİZ — `gh` repoyu cwd'den çıkarır ve `core/` bir junction'dır; "
            "yanlış repoya yazma/yayın GERİ ALINAMAZ. Hedefi AÇIKÇA ver: "
            "`--repo <ORG>/<REPO>` (ya da `gh api repos/<ORG>/<REPO>/...`).")

# BAŞLIK SATIRI KORUNUR (grup 1): eski `.*?` DOTALL ilk satırdaki yönlendirmeyi de yutardı.
_HEREDOC = re.compile(r"(<<-?\s*(['\"]?)(\w+)\2[^\n]*)\n(.*?)^\3$", re.MULTILINE | re.DOTALL)
_PS_HERESTRING = re.compile(r"@(['\"])[\s\S]*?^\1@", re.MULTILINE)


def _komut_govdesi(s: str) -> str:
    s = _HEREDOC.sub(lambda m: m.group(1) + " <HEREDOC-STRIPPED>", s)
    return _PS_HERESTRING.sub(" <HERESTRING-STRIPPED> ", s)


def _heredoc_govdeleri(s: str) -> str:
    return "\n".join(m.group(4) for m in _HEREDOC.finditer(s))


_KABUK_TOOLLARI = ("Bash", "PowerShell")
_ARG_REPO = re.compile(r"--repo[= ]+([^\s'\"]+)")
_ARG_BODYFILE = re.compile(
    r"(?:--body-file|--notes-file|(?<![\w-])-F)[= ]+(?:'([^']+)'|\"([^\"]+)\"|(\S+))")
_CD_PREFIX = re.compile(r"\bcd\s+([^\s;&|]+)")
_AYRAC = re.compile(r"\s*(?:\|\||&&|[;|&\n])\s*")


def _arg_deger(s: str, ad: str) -> str:
    m = re.search(rf"--{ad}[= ]+(?:'([^']*)'|\"((?:[^\"\\]|\\.)*)\"|(\S+))", s)
    if not m:
        return ""
    return m.group(1) or m.group(2) or m.group(3) or ""


_KISA_BAYRAK = {"title": "t", "body": "b", "notes": "n"}


def _arg_deger_kisa(s: str, ad: str) -> str:
    """--<ad> yoksa kısa bayrağa (-t/-b/-n) bak. `gh pr create -b "..."` eskiden KAÇIYORDU."""
    v = _arg_deger(s, ad)
    if v:
        return v
    ch = _KISA_BAYRAK.get(ad)
    if not ch:
        return ""
    m = re.search(rf"(?<![\w-])-{ch}\s+(?:'([^']*)'|\"((?:[^\"\\]|\\.)*)\"|(\S+))", s)
    if not m:
        return ""
    return m.group(1) or m.group(2) or m.group(3) or ""


def _yayinlanan_metin(komut: str, ham: str) -> tuple:
    """--title/--body/--notes (+ kısa bayraklar) + --body-file/--notes-file İÇERİĞİ.
    `--body-file -` (stdin) heredoc'tan çözülür (eski sürüm fail-closed ediyordu →
    meşru PR durdu, 2026-07-09). `gh api` için gövde çıkarılamaz → TÜM komut taranır
    (fail-closed). Dönüş: (metin, hata)."""
    if re.search(r"(?<!\w)gh\s+api\b", komut, re.IGNORECASE):
        return komut + "\n" + _heredoc_govdeleri(ham), ""

    parcalar = [_arg_deger_kisa(komut, "title"),
                _arg_deger_kisa(komut, "body"),
                _arg_deger_kisa(komut, "notes")]
    bf = _ARG_BODYFILE.search(komut)
    if bf:
        yol = bf.group(1) or bf.group(2) or bf.group(3)
        if yol in ("-", "/dev/stdin"):
            govde = _heredoc_govdeleri(ham)
            if not govde.strip():
                return "", ("--body-file - (stdin) gövdesi çözülemedi. FAIL-CLOSED: gövdeyi "
                            "heredoc ile ver ya da --body-file <dosya> kullan.")
            parcalar.append(govde)
        else:
            try:
                parcalar.append(Path(yol).read_text(encoding="utf-8", errors="replace"))
            except Exception:
                return "", (f"--body-file okunamadi ({yol}). FAIL-CLOSED: okunur yap "
                            "veya --body kullan.")
    return "\n".join(p for p in parcalar if p), ""


def _repo_public_mu(hay: str) -> tuple:
    """Görünürlük CANLI sorulur (gh repo view). Kararsızsa FAIL-CLOSED (public say)."""
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
        r = subprocess.run(argv, capture_output=True, text=True, timeout=15, cwd=cwd, shell=False)
        if r.returncode != 0:
            return True, "gorunurluk-sorulamadi(fail-closed)"
        d = json.loads(r.stdout)
        return (not d.get("isPrivate", True)), d.get("nameWithOwner", "?")
    except Exception:
        return True, "gorunurluk-sorulamadi(fail-closed)"


def _gh_pr_public_leak(komut: str, ham: str) -> str:
    if not _GH_PUBLIC_YAYIN.search(komut):
        return ""
    public, repo = _repo_public_mu(komut)
    if not public:
        return ""
    metin, hata = _yayinlanan_metin(komut, ham)
    if hata:
        return f"public repo '{repo}' — {hata}"
    bulgular = [f"{ad}: '{tok}'" for tok, ad in sizintilari_bul(metin, _CORE_LEAK)][:6]
    if not bulgular:
        return ""
    return f"public repo '{repo}' — yayinlanan baslik/govdede " + "; ".join(bulgular)


_SAP_YAZMA_TOOLLARI = {
    "mcp__sap-adt__adt_push_source", "mcp__sap-adt__adt_activate",
    "mcp__sap-adt__adt_delete", "mcp__sap-adt__adt_domain_create",
    "mcp__sap-adt__adt_dtel_create", "mcp__sap-adt__adt_struct_create",
    "mcp__sap-adt__adt_post_shell", "mcp__sap-adt__adt_publish_service",
    "mcp__sap-adt__adt_classrun",
}


def _yasaklar_damga_sorunu() -> str:
    """FAIL-CLOSED (2026-07-10): eskiden `except: return ""` idi — guard'ın kendi hatası
    korumayı sessizce kapatıyordu. Damganın DOĞRULANAMAMASI = sağlam değildir."""
    kok = _PROJ_ROOT
    cmd = kok / "CLAUDE.md"
    if not (kok / "project.yaml").exists() or not cmd.exists():
        return ""
    core = kok / "core"
    try:
        sys.path.insert(0, str(core / "scripts"))
        from utils import yasaklar_stamp  # type: ignore
    except Exception:
        return ""                    # junction kopuk → shim'in işi
    try:
        if not yasaklar_stamp.canonical_path(core).exists():
            return ""
    except Exception:
        return ""
    try:
        ok, mesaj = yasaklar_stamp.check(cmd.read_text(encoding="utf-8"), core)
    except Exception as e:           # ← fail-CLOSED
        return f"damga doğrulanamadı ({type(e).__name__}: {e})"
    return "" if ok else mesaj


def _core_hedef_mi(dosya: str) -> bool:
    if not dosya:
        return False
    d = dosya.replace("\\", "/").lower()
    return "/core/" in d or d.startswith("core/") or "dev_core" in d


def _komut_konumunda(seg: str, desen: str) -> bool:
    tirnaksiz = re.sub(r"'[^']*'|\"[^\"]*\"", " ", seg)
    return re.search(r"(?:^|[\n;|&(])\s*(?:\w+\s+)?" + desen, tirnaksiz, re.IGNORECASE) is not None


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
    root = _proje_koku()
    conn = root / ".conn_adt"
    state = root / ".claude" / ".mcp_active_system"
    if not conn.exists() or not state.exists():
        return (False, "", "")
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
    differ = (bool(ch) and bool(mh) and ch != mh) or \
             (bool(cur_cl) and bool(mcp_cl) and str(cur_cl) != mcp_cl)
    return (differ, cur_sys or ch or "?", mcp_sys or mh or "?")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    tool_name = data.get("tool_name", "") or ""

    if tool_name in _SAP_YAZMA_TOOLLARI:
        sorun = _yasaklar_damga_sorunu()
        if sorun:
            sys.stderr.write(
                "⛔ KESİN YASAKLAR DAMGASI EKSİK/SAPMIŞ (PreToolUse guard, ADR 0005): "
                f"{sorun}\nYasaklar kök CLAUDE.md'de fiziksel damgalı OLMALI. Damga "
                "yokken/bayatken SAP-YAZMA REDDEDİLDİ. Çözüm: "
                "python core/scripts/sync_yasaklar.py → tekrar dene.\n")
            return 2

    if tool_name.startswith("mcp__sap-adt__") and tool_name != "mcp__sap-adt__ping":
        mismatch, conn_label, mcp_label = _binding_mismatch()
        if mismatch:
            sys.stderr.write(
                "⛔ BAĞLANTI TUTARSIZLIĞI (PreToolUse guard, ADR 0010): "
                f".conn_adt '{conn_label}' işaret ediyor ama MCP '{mcp_label}' sistemine "
                "BAĞLI (switch_tier yapıldı, /mcp restart EDİLMEDİ). ADT isteği YANLIŞ "
                "sisteme gider. İŞLEM REDDEDİLDİ. DUR → kullanıcı '/mcp' ile yeniden bağlansın.\n")
            return 2

    ti = data.get("tool_input", {}) or {}
    ham = ""
    if isinstance(ti, dict):
        ham = ti.get("command", "") or json.dumps(ti, ensure_ascii=False)
    else:
        ham = str(ti)

    komut = _komut_govdesi(ham) if tool_name in _KABUK_TOOLLARI else ham

    dosya_hedefi = ""
    if isinstance(ti, dict):
        dosya_hedefi = ti.get("file_path", "") or ti.get("notebook_path", "") or ""

    if tool_name in _KABUK_TOOLLARI or tool_name in _ABAP_TOOLLARI:
        abap = tool_name in _ABAP_TOOLLARI
        sorun = _adr0005c_sorunu(ham if abap else komut, abap)
        if sorun:
            sys.stderr.write(
                f"⛔ ADR 0005-C İHLALİ (PreToolUse guard): {sorun} tespit edildi. Bu YASAK — "
                "transport'u kullanıcı release eder, yeni transport/package yaratılmaz. "
                "DUR → kullanıcıya bildir.\n"
                "Not: kuralı ANLATAN metin (doküman / commit mesajı / grep) bloklanmaz; "
                "yalnız çalıştırma bağlamı bloklanır.\n")
            return 2

    if tool_name in _KABUK_TOOLLARI:
        belirsiz = _gh_hedef_belirsiz(komut)
        if belirsiz:
            sys.stderr.write(
                f"⛔ GH HEDEF BELİRSİZ: {belirsiz}\n"
                "Bu kural repoyu DEĞİŞTİREN her `gh` alt-komutunda geçerlidir "
                "(pr/issue/release/repo/secret/variable/workflow/ruleset/label/api). "
                "Okuma komutları (list/view/status) serbesttir. İŞLEM REDDEDİLDİ.\n")
            return 2

        sorun = _gh_pr_public_leak(komut, ham)
        if sorun:
            sys.stderr.write(
                f"⛔ PUBLIC-PR SIZINTI GATE: {sorun}\n"
                "PR başlığı/gövdesi PUBLIC repoya yayınlanır ve cache'lenir — silmek geri "
                "ALMAZ. core_precommit yalnız commit içeriğini tarar; PR gövdesi commit "
                "DEĞİLDİR. İŞLEM REDDEDİLDİ. Çözüm: gövdeyi genericize et, tekrar dene.\n")
            return 2

    if (tool_name in _KABUK_TOOLLARI and "adt/activation" in komut and ".post(" in komut
            and "activate_and_verify" not in komut and "_activation_failures" not in komut):
        sys.stderr.write(
            "⛔ INLINE AKTİVASYON (PreToolUse guard, adt-rap §34-D): elle "
            "'/sap/bc/adt/activation' POST'u activationExecuted'ı PARSE ETMEZ → HTTP 200 "
            "SAHTE-OK. Bunun yerine activate_and_verify(client, tok, refs) KULLAN. "
            "İŞLEM REDDEDİLDİ.\n")
        return 2

    if tool_name in _KABUK_TOOLLARI and "deploy_ui.py" not in komut and any(
            _komut_konumunda(seg, r"(?:npx\s+)?fiori\s+deploy") for seg in _AYRAC.split(komut)):
        sys.stderr.write(
            "⛔ YALIN FIORI DEPLOY (PreToolUse guard, stale-dist dersi): 'fiori deploy' "
            "BUILD YAPMAZ — bayat dist gider ama 'Successful' der. KANONİK yol: "
            "`python scripts/deploy_ui.py --apps <app1,app2>`. İŞLEM REDDEDİLDİ.\n")
        return 2

    if tool_name in _KABUK_TOOLLARI and _NPM_INSTALL.search(komut):
        cdm = re.search(r"\bcd\s+(?:\"([^\"]+)\"|'([^']+)'|([^\s&|;]+))", komut)
        cd_target = next((g for g in (cdm.groups() if cdm else ()) if g), "") if cdm else ""
        hit = _ui_app_subdir(cd_target) or _ui_app_subdir(data.get("cwd", "") or "")
        if hit:
            ui_root, app = hit
            sys.stderr.write(
                f"⛔ APP-İÇİ NPM INSTALL (PreToolUse guard, standards/03): '{app}' app "
                f"dizininde npm install/ci/add YASAK — '{ui_root}' workspace kökü. Lokal: "
                f"`npm run start-noflp`. Bağımlılık: `cd {ui_root} && npm install`. "
                "İŞLEM REDDEDİLDİ.\n")
            return 2

    if tool_name in ("Edit", "Write", "MultiEdit", "NotebookEdit") and _core_hedef_mi(dosya_hedefi):
        # Desen-sözlüğü taşıyan dosyalar taranmaz — kendileri deseni TANIMLAR, o yüzden
        # kaçınılmaz olarak "eşleşirler". `core_precommit.SCAN_EXEMPT` ile aynı liste;
        # burada YOKTU → guard kendi düzeltmesini blokluyordu (2026-07-10).
        if Path(str(dosya_hedefi)).name in _DESEN_TANIMLAYAN:
            return 0
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
        # K4a (2026-07-10): bu dal yalnız isim-listesini uyguluyordu; Z-obje adı ve SAP
        # kullanıcı adı core'a Edit/Write ile SESSİZCE yazılabiliyordu. Artık aynı
        # sizintilari_bul() — hedef dosya ADI da taranır (D5).
        # ⚠ TAM YOL değil, yalnız DOSYA ADI taranır: core başka makinede kullanıcı-profili
        # altında olabilir → makine-yolu deseni her core yazımını yanlış-bloklardı.
        hedef_ad = Path(str(dosya_hedefi)).name
        bulgular = sizintilari_bul(icerik, _CORE_LEAK) + sizintilari_bul(hedef_ad, _CORE_LEAK)
        if bulgular:
            tok, ad = bulgular[0]
            sys.stderr.write(
                f"⛔ GENERICIZE-LEAK (Ö5/B9): core'a yazılan içerikte/adda {ad}: "
                f"'{tok}' (hedef: {dosya_hedefi}). Core PUBLIC repodur; yalnız jenerik "
                "içerik girer (placeholder: <PROJECT_NAME>, <SAP_USER>, ZSD001). İŞLEM REDDEDİLDİ.\n")
            return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
