#!/usr/bin/env python3
# ENFORCES: ADR-0019  (ADR 0019 coverage binding)
"""PreToolUse guard — çok-katman, 9 kural (2026-07-10 sadeleştirmesi).

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


# ═══════════════════════════════════════════════════════════════════════════════
# KABUK SÖZDİZİMİ MODELİ (2026-08-01, adversarial bug-avı AV-16/17/18)
#
# SINIF-HATA: kurallar komut metnini SERBEST REGEX'le tarıyordu; kabuk dilbilgisinin
# iki yapısı hiç modellenmemişti → aynı kökten ÜÇ atlatma çıktı (üçü de canlı repro):
#   AV-16 `git commit -am '<iz>'`   → exit 0  (kontrol: `-m` → exit 2)
#         kök: `_GIT_M` lookbehind'i `(?<![\w-])` KÜMELENMİŞ kısa bayrağın (`-am`) içindeki
#         `m`'yi reddediyordu → mesaj HİÇ çıkarılmadı → taranacak metin yok → gate boş döndü.
#         "Metin bulunamadı" ile "metin temiz" AYNI sonuca (geç) düşüyordu.
#   AV-17 `git commit --file=<f>`   → exit 0  (kontrol: `-F <f>` → exit 2)
#         kök: `_ARG_BODYFILE` git'in `--file` uzun biçimini hiç tanımıyordu.
#   AV-18 `gh repo view --repo O/R && gh pr create -t t -b b` → exit 0
#         kök: kural-9 `--repo`yu KOMUTUN TAMAMINDA arıyordu; zincirdeki BAŞKA (hatta
#         salt-okuma) bir komuttaki hedef, sonraki HEDEFSİZ mutasyonu serbest bırakıyordu.
#
# ORTAK KÖK: "bayrak biçimi" ve "komut zinciri" modellenmemiş. Vaka-vaka yamamak
# (bir `-am` alternasyonu eklemek) sınıfı kapatmaz — `-qam`, `-mF`, `--file=`, `;`
# zinciri hepsi ayrı ayrı geri gelir. Bu yüzden İKİ ortak ilkel kuruluyor:
#   ① `_kelimeler()`  — tırnak-duyarlı kelime bölme (kabuk word-splitting'in dar modeli)
#   ② `_segmentler()` — tırnak-DIŞI ayraçlardan segment bölme (her komut kendi bağlamı)
# ve üstlerine `_bayrak_degerleri()` (POSIX/git/pflag bayrak dilbilgisi) oturuyor.
#
# ⚠ PATTERN #12 (tırnak-içi VERİ komut sanılır, 7d78a49): bölme TIRNAK-DUYARLIDIR —
# `echo 'git commit -am x'` TEK kelimedir, komut değildir; `git commit -m "a && b"`
# TEK segmenttir. Bu, 2026-07-09'da bir kez çözülmüş sınıfın geri gelmemesi içindir.
# ═══════════════════════════════════════════════════════════════════════════════
_ATAMA = re.compile(r"^[A-Za-z_]\w*=")
_SEG_AYRAC_KARAKTER = ";|&\n()"

# ── KABUK LEHÇESİ (repo-maskeleme düzeltme turu, 2026-10-14) ─────────────────────────
# VAKA (bug-gate, ölçüldü): tek tırnaklı metinde Bash'in `'\''` kaçışından (ve `$'…\'…'`
# ANSI-C biçiminden) SONRAKİ içerik ayrı token'a düşüyordu ⇒ `git commit -m 'it'\''s <iz>'`
# ve `gh pr create … -b 'main'\''e <iz>'` gövdesi TARANMADAN geçiyordu (main ve önceki tur
# rc 0); aynı sebeple `--title 'PR'\''i duzelt' --repo org/x` GH-HEDEF'te FP blok oldu.
# Üç lehçe: "eski" = bu turdan ÖNCEKİ model, birebir (sızıntı gate'leri onu BİRLEŞİMİN bir
# kolu olarak koşar ⇒ yeni modelin çizdiği farklı sınır sessiz geçiş üretemez, PATTERN #12) ·
# "bash" · "ps" (PowerShell). `main()` araç adına göre seçer; varsayılan "eski" (bu modülü
# kullanan diğer kurallar ve doğrudan çağıran testler DEĞİŞMEZ).
#   bash: tırnak dışı `\'` `\"` = harf (`\\` iki karakteriyle birim — Windows yolu `C:\\IX`
#         eskisi gibi; `\;` gibi diğerleri DEĞİŞMEZ) · `$'…'` ANSI-C (`\'` tırnak) · çift
#         tırnakta `\` yalnız `$ \` " \\` önünde kaçış (aksi hâlde harf: `"C:\IX"` korunur).
#   ps:   backtick kaçışı (tırnak dışı + çift tırnak) · tek tırnakta `''`, çift tırnakta `""`
#         = harf · `\` HİÇBİR yerde kaçış değil.
_LEHCE = "eski"
_ANSI_C = {"n": "\n", "t": "\t", "r": "\r", "'": "'", '"': '"', "\\": "\\"}
_PS_KACIS = {"n": "\n", "t": "\t", "r": "\r"}

# ── KABUĞUN ARGÜMAN SAYMADIĞI METİN (repo-maskeleme tur-4, 2026-10-14) ─────────────────
# VAKA (bug-gate BLOCKER, lider bağımsız teyit, ölçüldü): bash/ps lehçesi tırnaksız yorumu,
# `\<boşluk>` kaçışını ve yönlendirme işlenenini modellemiyordu ⇒ kabuğun gh'ye HİÇ
# geçirmediği `-R<org>/<repo>` metni açık hedef sayılıyordu: `gh release delete v1 --yes
# # -R<org>/<repo>` · `gh pr create -t x -b b <<< -R<org>/<repo>` · `-t \ -R<org>/<repo>`
# (main rc 2 → önceki tur rc 0). Sızıntı yönünde aynı kör nokta: yorumdaki private `-R`
# gerçek hedef sanılıyor, cwd adayı eklenmiyor, gövde taranmıyordu (main ve önceki tur rc 0).
# Kabuk gerçekliği (ölçüldü: GNU bash 5.3.9 · Windows PowerShell 5.1, argv dökümüyle):
#   yorum   : kelime BAŞINDA tırnaksız `#` satır sonuna kadar yorumdur (`a#b`, `'x'#y`, URL
#             içi `#` yorum DEĞİL) · PS ayrıca kelime başında `<#…#>` blok yorum.
#   bash    : tırnaksız `\X` X'i harf yapar — burada yalnız boşluk/sekme/`#`/`<`/`>` eklendi
#             (diğerleri bilerek eski: Windows yolu `C:\IX`) · HER tırnaksız `<`/`>`
#             yönlendirmedir, kelime ortasında da (`a>b` → argv `a`); hemen önündeki TÜMÜ
#             RAKAM kelime fd numarasıdır (`2>x`, `x2>y` değil) · işlenen bir sonraki kelime.
#   ps      : `\` kaçış değil · yönlendirme YALNIZ kelime başında (`-t a>f` → argv `a>f`):
#             `>` `>>` `n>` `*>` · kelime başı `<` ayrıştırma hatasıdır (komut koşmaz).
# İşlenensiz operatör (segment sonu: `2>&1` `&`'de, `<(…)` `(`'de bölünür) eskisi gibi
# TOKEN kalır — bu turdan önceki davranış (FP üretmesin). Lehçe `eski` DEĞİŞMEZ.
_YONL_BASH = re.compile(r"<<<|<<-|<<|<>|>>|<|>")
_YONL_PS = re.compile(r"[0-9*]?>>?|<")
_BASH_HARF_KACIS = "'\"\\ \t#<>"


def _kelimeler(s: str, lehce: str = None) -> list:
    """Tırnak-duyarlı kelime bölme. `--m="a b"` → tek kelime (`--m=a b`).

    Bilerek `shlex` DEĞİL: `shlex(posix=True)` Windows yollarındaki ters-eğik çizgiyi
    kaçış sayıp yutar (`C:\\IX\\x` → `C:IXx`) ve dengesiz tırnakta ValueError atar —
    guard'ın girdisi keyfi/kirli metindir, ayrıştırıcı ASLA patlamamalı.
    `lehce` verilmezse `_LEHCE` (bkz. KABUK LEHÇESİ).
    """
    return [k for k, _ in _kelimeler_ham(s, lehce)]


def _kelimeler_ham(s: str, lehce: str = None) -> list:
    """`_kelimeler` + her kelimenin komut metnindeki HAM yazımı: [(kelime, ham)].

    Ham yazım, bir muafiyeti metne değil onu DOĞURAN token'ın kendi kaynağına bağlamak
    içindir (bitişik `-R<değer>` freni, tur-4). bash/ps lehçesinde yorum, yönlendirme
    işleneni ve `\\<boşluk>` kabuğun yaptığı gibi ele alınır (bkz. yukarıdaki blok)."""
    lehce = lehce or _LEHCE
    s = s or ""
    yeni = lehce in ("bash", "ps")
    kelimeler, cur, tirnak_gordu, bas = [], [], False, None
    yonl = None                       # işleneni beklenen yönlendirme: (metin, başlangıç)
    i, n = 0, len(s)

    def bitir(son: int) -> None:
        nonlocal cur, tirnak_gordu, bas, yonl
        if cur or tirnak_gordu:
            if yonl is not None:
                yonl = None           # yönlendirme işleneni: argüman DEĞİL
            else:
                kelimeler.append(("".join(cur), s[bas:son]))
        cur, tirnak_gordu, bas = [], False, None

    def yonlendirme(metin: str, bas_: int) -> None:
        nonlocal yonl
        if yonl is not None:          # işlenensiz önceki operatör (kabukta sözdizimi hatası)
            kelimeler.append((yonl[0], yonl[0]))
        yonl = (metin, bas_)

    while i < n:
        c = s[i]
        if yeni and not cur and not tirnak_gordu:
            if c == "#":
                break                 # yorum: segmentin kalanı argüman değil
            if lehce == "ps" and s.startswith("<#", i):
                j = s.find("#>", i + 2)
                i = n if j < 0 else j + 2
                continue
            m = _YONL_PS.match(s, i) if lehce == "ps" else None
            if m:
                yonlendirme(m.group(0), i)
                i = m.end()
                continue
        if lehce == "bash" and c in "<>":
            m = _YONL_BASH.match(s, i)
            k = "".join(cur)
            if cur and not tirnak_gordu and k.isdigit():
                metin, bas_ = k + m.group(0), bas     # fd numarası operatöre aittir
                cur, bas = [], None
            else:
                bitir(i)
                metin, bas_ = m.group(0), i
            yonlendirme(metin, bas_)
            i = m.end()
            continue
        if c.isspace():
            bitir(i)
            i += 1
            continue
        if bas is None:
            bas = i
        if lehce == "bash" and c == "\\" and i + 1 < n and s[i + 1] in _BASH_HARF_KACIS:
            cur.append(s[i:i + 2] if s[i + 1] == "\\" else s[i + 1])
            i += 2
            continue
        if lehce == "bash" and c == "$" and i + 1 < n and s[i + 1] == "'":
            i += 2
            tirnak_gordu = True
            while i < n and s[i] != "'":
                if s[i] == "\\" and i + 1 < n:
                    cur.append(_ANSI_C.get(s[i + 1], s[i:i + 2]))
                    i += 2
                    continue
                cur.append(s[i])
                i += 1
            i += 1
            continue
        if lehce == "ps" and c == "`" and i + 1 < n:
            cur.append(_PS_KACIS.get(s[i + 1], s[i + 1]))
            i += 2
            continue
        if c in "'\"":
            q = c
            i += 1
            tirnak_gordu = True
            while i < n:
                ch = s[i]
                if lehce == "ps":
                    if ch == q and i + 1 < n and s[i + 1] == q:
                        cur.append(q)                 # '' / "" = harf
                        i += 2
                        continue
                    if ch == q:
                        break
                    if q == '"' and ch == "`" and i + 1 < n:
                        cur.append(_PS_KACIS.get(s[i + 1], s[i + 1]))
                        i += 2
                        continue
                    cur.append(ch)
                    i += 1
                    continue
                if ch == q:
                    break
                if q == '"' and ch == "\\" and i + 1 < n:
                    if lehce == "bash" and s[i + 1] not in '$`"\\\n':
                        cur.append(ch)                # bash: `"C:\IX"` ters çizgiyi KORUR
                        i += 1
                        continue
                    cur.append(s[i + 1])
                    i += 2
                    continue
                cur.append(ch)
                i += 1
            i += 1                      # kapanış tırnağı (yoksa dizge sonu)
            continue
        cur.append(c)
        i += 1
    bitir(min(i, n))
    if yonl is not None:              # işlenensiz operatör: eskisi gibi token (FP üretmesin)
        kelimeler.append((yonl[0], yonl[0]))
    return kelimeler


def _segmentler(s: str, lehce: str = None) -> list:
    """Komutu tırnak-DIŞI ayraçlardan (`&& || ; | & \\n ( )`) segmentlere böler.

    Segment = "kendi hedefi/bağlamı olan tek komut". Ayraç kümesi bilerek kuralların
    komut-başı çapası `(?:^|[\\n;|&(])` ile AYNI: her segmentin başında `^` çapası
    tutar → mevcut desenler segment üzerinde DEĞİŞMEDEN çalışır (kapsam kaybı yok).
    Lehçe `_kelimeler` ile AYNI kuralla (iki ayrıştırıcı sınırı farklı çizmesin).
    """
    lehce = lehce or _LEHCE
    segler, buf = [], []
    i, n, q = 0, len(s or ""), ""
    yeni, kb = lehce in ("bash", "ps"), True        # kb: kelime başı (tur-4 yorum modeli)
    while i < n:
        c = s[i]
        # Tur-4: yorum içindeki tırnak/ayraç segment sınırı ÇİZMEZ (ölçüldü: `… # it's`
        # satırındaki apostrof eskiden tırnak açıp SONRAKİ satırın hedefsiz gh'sini yutuyordu;
        # bash o satırı ayrı komut olarak koşar). Yorum metni segmentte kalır; ayraç değildir.
        if yeni and not q and kb and c == "#":
            j = s.find("\n", i)
            j = n if j < 0 else j
            buf.append(s[i:j])
            i = j
            continue
        if yeni and not q and kb and lehce == "ps" and s.startswith("<#", i):
            j = s.find("#>", i + 2)
            j = n if j < 0 else j + 2
            buf.append(s[i:j])
            i, kb = j, False
            continue
        kb = (not q) and (c.isspace() or c in _SEG_AYRAC_KARAKTER)
        if q:
            buf.append(c)
            if lehce == "ps" and c == q and i + 1 < n and s[i + 1] == q:
                buf.append(s[i + 1])          # '' / "" = harf, tırnak sürer
                i += 2
                continue
            if c == q[-1]:
                q = ""
            elif lehce == "ps" and q == '"' and c == "`" and i + 1 < n:
                buf.append(s[i + 1])
                i += 1
            elif lehce != "ps" and q in ('"', "$'") and c == "\\" and i + 1 < n:
                buf.append(s[i + 1])
                i += 1
            i += 1
            continue
        if lehce == "bash" and c == "\\" and i + 1 < n and s[i + 1] in _BASH_HARF_KACIS:
            buf.append(s[i:i + 2])
            i += 2
            continue
        if lehce == "bash" and c == "$" and i + 1 < n and s[i + 1] == "'":
            q = "$'"
            buf.append(s[i:i + 2])
            i += 2
            continue
        if lehce == "ps" and c == "`" and i + 1 < n:
            buf.append(s[i:i + 2])
            i += 2
            continue
        if c in "'\"":
            q = c
            buf.append(c)
            i += 1
            continue
        if c in _SEG_AYRAC_KARAKTER:
            segler.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(c)
        i += 1
    segler.append("".join(buf))
    return [x for x in (t.strip() for t in segler) if x]


def _kabuk_baglami(segler: list, idx: int) -> str:
    """<idx>'ten ÖNCEKİ **SON** `cd` segmenti (görünürlük sorgusu doğru repoya baksın).

    Segment-bazlı değerlendirmeye geçerken `cd /c/core && git commit …` zincirinde
    `cd` bağlamı kaybolur → `_repo_public_mu` proje köküne düşer → YANLIŞ repo
    görünürlüğü (hem FP hem FN üretir). Bağlam açıkça taşınır.

    **SON** olmasının sebebi: kabukta geçerli dizin son `cd`dir. `_repo_public_mu`
    kendisi `_CD_PREFIX.search` ile İLK eşleşmeyi alır; bütün `cd`leri taşısaydık
    `cd A && git commit … && cd B && git commit …` zincirinde ikinci commit A'nın
    görünürlüğüyle değerlendirilirdi (yanlış repo → sessiz kaçak).
    """
    onceki = [s for s in segler[:idx] if re.match(r"^\s*cd\s+", s)]
    return (onceki[-1] + "\n") if onceki else ""


def _bayrak_degerleri(tokenlar: list, uzun: set, kisa: set) -> list:
    """Bayrak DEĞERLERİ: `--ad X` · `--ad=X` · `-x X` · `-xX` · KÜMELENMİŞ `-abx X`.

    AV-16'nın kökü tam burasıydı: kümelenmiş kısa bayrak (`-am`, `-qam`) hiçbir
    regex'te modellenmemişti. Kümede değer ALAN harf bulunursa, ondan SONRAKİ kalan
    değerdir; kalan boşsa değer bir SONRAKİ token'dır (git/pflag davranışı birebir).
    `--` sonrası bayrak ayrıştırması durur (POSIX).
    """
    degerler, i, n = [], 0, len(tokenlar)
    while i < n:
        t = tokenlar[i]
        if t == "--":
            break
        if t.startswith("--") and len(t) > 2:
            ad, esittir, deger = t[2:].partition("=")
            if ad in uzun:
                if esittir:
                    degerler.append(deger)
                elif i + 1 < n:
                    degerler.append(tokenlar[i + 1])
                    i += 1
        elif t.startswith("-") and len(t) > 1:
            harfler = t[1:]
            for k, ch in enumerate(harfler):
                if ch in kisa:
                    kalan = harfler[k + 1:]
                    if kalan.startswith("="):
                        kalan = kalan[1:]
                    if kalan:
                        degerler.append(kalan)
                    elif i + 1 < n:
                        degerler.append(tokenlar[i + 1])
                        i += 1
                    break
        i += 1
    return degerler


# `git <ust-opsiyon> commit` — değer ALAN üst-seviye opsiyonlar (atlanmalı ki alt-komut
# doğru bulunsun): `git -C <yol> commit -am 'x'` gerçek bir vakadır (worktree/çoklu repo).
_GIT_UST_DEGERLI = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace",
                              "--exec-path", "--config-env"})
_GIT_MSG_UZUN, _GIT_MSG_KISA = frozenset({"message"}), frozenset({"m"})
_GIT_DOSYA_UZUN, _GIT_DOSYA_KISA = frozenset({"file"}), frozenset({"F"})


def _git_commit_arg_dizileri(komut: str) -> list:
    """`git commit` segmentlerinin ARGÜMAN token listeleri (commit'ten SONRASI).

    `git` KOMUT KONUMUNDA olmalı (segment başı, yalnız `VAR=deger` önekleri atlanır) →
    `echo "git commit -am x"` (tek kelime, tırnaklı) ve `grep -am 3 …` / `tar -am …`
    buraya HİÇ girmez: yanlış-pozitif yapısal olarak imkânsız, "-am" kara-listesi değil.
    """
    ciktilar = []
    for seg in _segmentler(komut):
        t = _kelimeler(seg)
        i = 0
        while i < len(t) and _ATAMA.match(t[i]):
            i += 1
        if i >= len(t):
            continue
        ad = t[i].replace("\\", "/").rsplit("/", 1)[-1].lower()
        if ad not in ("git", "git.exe"):
            continue
        i += 1
        while i < len(t) and t[i].startswith("-"):
            i += 2 if t[i] in _GIT_UST_DEGERLI else 1
        if i < len(t) and t[i].lower() == "commit":
            ciktilar.append(t[i + 1:])
    return ciktilar


# TEK KAYNAK (D9): desenler `scripts/genericize_common.py`'de; `core_precommit` de aynı
# modülü kullanır. Eskiden iki guard iki AYRI dosyadan besleniyordu (biri
# `<proje>/.claude/...`, diğeri `<git-dir>/...`) → biri güncellenip diğeri unutulabiliyordu.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from genericize_common import (  # noqa: E402
    AJAN_IMZA_SATIRI, ATIF_ADRES_PAT, ATIF_SATIRI, sizintilari_bul, tembel_id_pattern,
)

# TEMBEL (2026-08-13, süre-vergisi): eskiden burada `id_pattern(...)` DOĞRUDAN çağrılıyordu
# → modül her yüklendiğinde `git rev-parse` subprocess'i (ölçüldü: ~100 ms) koşuyordu, yani
# HER araç çağrısında. Desen yalnız 3 dalda kullanılır (commit-mesajı / `gh` yayın / core'a
# yazma taraması); çoğunluk yolu onu hiç okumaz. Sarmalayıcı deseni İLK KULLANIMDA kurar —
# içerik ve kaynaklar aynı, yalnız zamanlama değişti. Kullanım yerleri DEĞİŞMEDİ.
_CORE_LEAK = tembel_id_pattern(proje_koku=_PROJ_ROOT)  # IGNORECASE (D2)

# Desen tanımlayan dosyalar: taranırlarsa kendi desenlerine takılırlar. Dosya ADIYLA
# eşleşir — yol makineye göre değişir.
# ⚠ Q329 (2026-09-18): `core_precommit`in eşdeğer dosya-bazlı muafiyeti (`SCAN_EXEMPT`)
# KALDIRILDI — orada muafiyet artık SATIR bazlı ve gerekçe ZORUNLU. Buradaki dosya-bazlı
# muafiyet DURUYOR (yazım-anı guard'ı; kapsam dışı bırakıldı, ayrı karar) ⇒ iki katman
# ARTIK AYNI DEĞİL: bu dosyalara yazılan bir kimlik yazım anında görünmez, commit anında
# görünür. Bu asimetri bilinçlidir ve kayıt Q329'da yazılıdır.
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
_KOMUT_BASI = r"(?:^|[\n;|&(])\s*(?:[A-Za-z_]\w*=\S+\s+)*gh\s+"

# GRUP A — hedefi `--repo`/`-R` BAYRAĞIYLA alan, bayraksız cwd'ye düşen mutasyonlar.
_GH_A = re.compile(
    _KOMUT_BASI + r"("
    r"pr\s+(create|edit|comment|merge|close|reopen|ready|review)"
    r"|issue\s+(create|edit|comment|close|reopen|delete)"
    r"|release\s+(create|edit|delete|upload)"
    r"|secret\s+(set|delete)"
    r"|variable\s+(set|delete)"
    r"|workflow\s+(run|enable|disable)"
    r"|ruleset\b"
    r"|label\s+(create|edit|delete|clone)"
    r")", re.IGNORECASE)
# ⚠ `_GH_A_ACIK` / `_GH_B_ACIK` TEK BAŞINA HÜKÜM VERMEZ (repo-maskeleme turu, 2026-10-14):
# ikisi segment METNİNDE arıyordu ⇒ başlık/gövde içindeki `--repo x` ya da `org/x` hedefsiz
# mutasyonu "açık hedefli" sayıyordu (PATTERN #12: "komut" ile "komuttan bahis"). IGNORECASE
# ayrıca `-r <reviewer>`'ı da `-R` sayıyordu. Hüküm pflag çözümlemesinden verilir
# (`_gh_acik_bayrak` · `_gh_konumsal_hedef_var`); iki desen orada yalnız FREN olarak (VE ile)
# kalır ⇒ sonuç main'in geçirdiği kümenin dışına çıkamaz (onaylı bitişik `-RX` hariç).
_GH_A_ACIK = re.compile(r"(?<![\w-])(--repo[= ]\S+|-R[= ]\S+)", re.IGNORECASE)

# GRUP B — hedefi KONUMSAL `<owner>/<name>` olarak alan `gh repo <alt>` komutları.
# `gh repo create org/XYZ` meşrudur (PROJECT_BOOTSTRAP STEP 1); `gh repo edit` (argümansız)
# cwd'ye düşer.
_GH_B = re.compile(_KOMUT_BASI + r"repo\s+(create|edit|rename|delete|archive|deploy-key)\b",
                   re.IGNORECASE)
# `<owner>/<name>` konumsal hedefi. `:` ve `//` lookbehind'i URL'i (https://a/b) hedef
# sanmayı önler; `<ORG>/XYZ` gibi DOLDURULMAMIŞ placeholder da hedef sayılmaz (bilinçli:
# şablon metni birebir çalıştırılırsa durur).
_GH_B_ACIK = re.compile(r"(?<![\w/:.-])[A-Za-z0-9][\w.-]*/[A-Za-z0-9][\w.-]*(?![\w/])")

# GRUP C — `gh api`. Burada `--repo` diye bir bayrak YOKTUR; hedef yolda yazar. Cwd çıkarımı
# YALNIZ `{owner}` / `{repo}` placeholder'larıyla olur → tehlike tam olarak orasıdır.
# `gh api user`, `gh api graphql`, `gh api rate_limit` repo-hedefsizdir, serbesttir.
_GH_C = re.compile(_KOMUT_BASI + r"api\b", re.IGNORECASE)
_GH_C_CWD = re.compile(r"\{(owner|repo)\}", re.IGNORECASE)

_GH_MUTASYON = _GH_A  # geriye dönük ad

# ── HEDEF YALNIZ GERÇEK TOKEN'DAN (repo-maskeleme turu, 2026-10-14) ─────────────────────
# Eskiden `--repo`/`-R`/konumsal hedef segment METNİNDE aranıyordu: tırnaklı başlık/gövde
# içinde geçen `--repo <ORG>/<PRIVATE>` gerçek `--repo <ORG>/<PUBLIC>`'i maskeliyor (sızıntı
# gate'i private sanıp gövdeyi taramıyordu) ya da hedefsiz mutasyonu "açık hedefli"
# sayıyordu (GH-HEDEF). Token'lar tırnak-duyarlı `_kelimeler`'den gelir; `gh` KOMUT
# KONUMUNDA değilse (tırnak içi veri, `bash -c "…"`) `None` döner ve çağıran eski davranışa
# kalır — o biçim bu turun kapsamı dışıdır (bkz. B82d açık sınır listesi).
_GH_KISA_REPO = re.compile(r"^-([A-Za-z]*)R(.*)$", re.DOTALL)
_GH_KONUMSAL = re.compile(r"[A-Za-z0-9][\w.-]*/[A-Za-z0-9][\w.-]*")


def _gh_komut_tokenlari(seg: str, ham: bool = False):
    """`gh` komut konumundaysa ondan SONRAKİ token'lar; değilse None.
    `ham=True`: [(token, ham yazım)] (bkz. `_kelimeler_ham`)."""
    th = _kelimeler_ham(seg)
    t = [k for k, _ in th]
    i = 0
    while i < len(t) and _ATAMA.match(t[i]):
        i += 1
    if i >= len(t) or t[i].replace("\\", "/").rsplit("/", 1)[-1].lower() not in ("gh", "gh.exe"):
        return None
    return th[i + 1:] if ham else t[i + 1:]


# ── gh BAYRAK TABLOSU (repo-maskeleme düzeltme turu, 2026-10-14) ─────────────────────
# VAKA (bug-gate F1, ölçüldü): "açık hedef" hükmü her token'ı BAĞIMSIZ tarıyordu ⇒ önceki
# bayrağın DEĞERİ olan tırnaklı token (`-t "--repo" -b b` · `--body "-Rorg/x"` ·
# `--subject "-Rorg/x"` · `-c "--repo"`) açık hedef sayılıyor, hedefsiz mutasyon geçiyordu
# (main rc 2 → önceki tur rc 0). pflag modeli: DEĞER ALAN bayrak bir sonraki token'ı
# (`--` dahil her şeyi) TÜKETİR. Hangi bayrağın değer aldığını gh'nin KENDİ yardım çıktısı
# söyler; tablo elle yazılmadı, ÜRETİLDİ:
#   kaynak: gh version 2.96.0 (2026-07-02) · `gh help <grup> <alt>` FLAGS + INHERITED FLAGS
#   (tip sütunu olan = değer alır; `--repo`/`--help` tabloda yok, ayrı ele alınır)
#   üretim: `python tests/fixtures/guard_hedef_maskeleme/gh_bayrak_uret.py` (ağsız)
#   reçete + tazelik: governance/infra-test-recipes.md B82e
# Alan biçimi: `<kısa>:<uzun>` ya da yalnız `<uzun>` (boşlukla ayrılmış).
# ⛔ BAYATLIK GEVŞETME ÜRETMEZ (lider koşulu): tabloda OLMAYAN alt-komut ya da tanınmayan
# bayrak/harf ⇒ çözümleme `kesin=False` ⇒ GH-HEDEF "açık hedef DEĞİL" (blok) · sızıntı
# gate'inde cwd aday kümesine KATILIR. Yeni gh sürümü bir bayrak eklerse sonuç en fazla FP'dir.
_GH_BAYRAK_TABLOSU = {
    ("pr", "create"): (
        "a:assignee B:base b:body F:body-file H:head l:label m:milestone p:project "
        "recover r:reviewer T:template t:title",
        "d:draft dry-run e:editor f:fill fill-first fill-verbose no-maintainer-edit w:web",
    ),
    ("pr", "edit"): (
        "add-assignee add-label add-project add-reviewer B:base b:body F:body-file "
        "m:milestone remove-assignee remove-label remove-project remove-reviewer t:title",
        "remove-milestone",
    ),
    ("pr", "comment"): (
        "b:body F:body-file",
        "create-if-none delete-last edit-last e:editor w:web yes",
    ),
    ("pr", "merge"): (
        "A:author-email b:body F:body-file match-head-commit t:subject",
        "admin auto d:delete-branch disable-auto m:merge r:rebase s:squash",
    ),
    ("pr", "close"): (
        "c:comment",
        "d:delete-branch",
    ),
    ("pr", "reopen"): (
        "c:comment",
        "",
    ),
    ("pr", "ready"): (
        "",
        "undo",
    ),
    ("pr", "review"): (
        "b:body F:body-file",
        "a:approve c:comment r:request-changes",
    ),
    ("issue", "create"): (
        "a:assignee blocked-by blocking b:body F:body-file l:label m:milestone parent "
        "p:project recover T:template t:title type",
        "e:editor w:web",
    ),
    ("issue", "edit"): (
        "add-assignee add-blocked-by add-blocking add-label add-project add-sub-issue "
        "b:body F:body-file m:milestone parent remove-assignee remove-blocked-by "
        "remove-blocking remove-label remove-project remove-sub-issue t:title type",
        "remove-milestone remove-parent remove-type",
    ),
    ("issue", "comment"): (
        "b:body F:body-file",
        "create-if-none delete-last edit-last e:editor w:web yes",
    ),
    ("issue", "close"): (
        "c:comment duplicate-of r:reason",
        "",
    ),
    ("issue", "reopen"): (
        "c:comment",
        "",
    ),
    ("issue", "delete"): (
        "",
        "yes",
    ),
    ("release", "create"): (
        "discussion-category n:notes F:notes-file notes-start-tag target t:title",
        "d:draft fail-on-no-commits generate-notes latest notes-from-tag p:prerelease "
        "verify-tag",
    ),
    ("release", "edit"): (
        "discussion-category n:notes F:notes-file tag target t:title",
        "draft latest prerelease verify-tag",
    ),
    ("release", "delete"): (
        "",
        "cleanup-tag y:yes",
    ),
    ("release", "upload"): (
        "",
        "clobber",
    ),
    ("secret", "set"): (
        "a:app b:body e:env f:env-file o:org r:repos v:visibility",
        "no-repos-selected no-store u:user",
    ),
    ("secret", "delete"): (
        "a:app e:env o:org",
        "u:user",
    ),
    ("variable", "set"): (
        "b:body e:env f:env-file o:org r:repos v:visibility",
        "",
    ),
    ("variable", "delete"): (
        "e:env o:org",
        "",
    ),
    ("workflow", "run"): (
        "F:field f:raw-field r:ref",
        "json",
    ),
    ("workflow", "enable"): (
        "",
        "",
    ),
    ("workflow", "disable"): (
        "",
        "",
    ),
    ("ruleset", "list"): (
        "L:limit o:org",
        "p:parents w:web",
    ),
    ("ruleset", "view"): (
        "o:org",
        "p:parents w:web",
    ),
    ("ruleset", "check"): (
        "",
        "default w:web",
    ),
    ("label", "create"): (
        "c:color d:description",
        "f:force",
    ),
    ("label", "edit"): (
        "c:color d:description n:name",
        "",
    ),
    ("label", "delete"): (
        "",
        "yes",
    ),
    ("label", "clone"): (
        "",
        "f:force",
    ),
    ("repo", "create"): (
        "d:description g:gitignore h:homepage l:license r:remote s:source t:team "
        "p:template",
        "add-readme c:clone disable-issues disable-wiki include-all-branches internal "
        "private public push",
    ),
    ("repo", "edit"): (
        "add-topic default-branch d:description h:homepage remove-topic "
        "squash-merge-commit-message visibility",
        "accept-visibility-change-consequences allow-forking allow-update-branch "
        "delete-branch-on-merge enable-advanced-security enable-auto-merge "
        "enable-discussions enable-issues enable-merge-commit enable-projects "
        "enable-rebase-merge enable-secret-scanning "
        "enable-secret-scanning-push-protection enable-squash-merge enable-wiki template",
    ),
    ("repo", "rename"): (
        "",
        "y:yes",
    ),
    ("repo", "delete"): (
        "",
        "yes",
    ),
    ("repo", "archive"): (
        "",
        "y:yes",
    ),
    ("repo", "deploy-key add"): (
        "t:title",
        "w:allow-write",
    ),
    ("repo", "deploy-key delete"): (
        "",
        "",
    ),
}


def _gh_tablo_ac(alan: str) -> tuple:
    uzun, kisa = set(), {}
    for parca in alan.split():
        k, _, u = parca.rpartition(":")
        uzun.add(u)
        if k:
            kisa[k] = u
    return uzun, kisa


_GH_BAYRAK = {anahtar: _gh_tablo_ac(d) + _gh_tablo_ac(b)
              for anahtar, (d, b) in _GH_BAYRAK_TABLOSU.items()}
_GH_BITISIK_R = re.compile(r"(?<![\w-])-R[^\s=]")
_GH_BITISIK_DEGER = re.compile(r"[\w.:/-]+")


def _gh_bayrak_cozumle(seg: str):
    """`gh` segmentinin pflag çözümlemesi; `gh` komut konumunda değilse None.

    Dönüş: {"kesin", "repolar": [(değer, biçim)], "degerler": {uzun: [..]}, "konumsal"}.
    Biçim: uzun (`--repo X`) · esit (`--repo=X`) · kisa (`-R X` / `-R=X`) · bitisik (`-RX`)
    · kume (`-dR X` / `-dRX`). `kesin` = alt-komut tabloda VE her bayrak/harf tanındı VE
    değer alan her bayrağın değeri var."""
    th = _gh_komut_tokenlari(seg, ham=True)
    if th is None:
        return None
    t = [k for k, _ in th]
    giris, bas = None, min(len(t), 2)
    if len(t) >= 2:
        g, a = t[0].lower(), t[1].lower()
        if g == "repo" and a == "deploy-key" and len(t) >= 3:
            giris, bas = _GH_BAYRAK.get(("repo", "deploy-key " + t[2].lower())), 3
        else:
            giris = _GH_BAYRAK.get((g, a))
    kesin = giris is not None
    taninmayan = [] if kesin else ["alt-komut `" + " ".join(t[:bas]) + "`"]
    du, dk, bu, bk = giris or (set(), {}, set(), {})
    repolar, degerler, konumsal = [], {}, []
    i = bas
    while i < len(t):
        tok = t[i]
        if tok == "--":
            konumsal += t[i + 1:]
            break
        if tok.startswith("--") and len(tok) > 2:
            ad, esit, deger = tok[2:].partition("=")
            if ad == "repo" or ad in du:
                if esit:
                    v = deger
                elif i + 1 < len(t):
                    v = t[i + 1]
                    i += 1
                else:
                    v, kesin = None, False
                    taninmayan.append(f"`{tok}` (değersiz)")
                if v is not None:
                    if ad == "repo":
                        repolar.append((v, "esit" if esit else "uzun"))
                    else:
                        degerler.setdefault(ad, []).append(v)
            elif not (ad in bu or ad == "help"):
                kesin = False                 # tanınmayan uzun bayrak
                taninmayan.append(f"`--{ad}`")
        elif tok.startswith("-") and len(tok) > 1:
            harfler = tok[1:]
            for k, ch in enumerate(harfler):
                if ch == "R" or ch in dk:
                    kalan = harfler[k + 1:]
                    esit = kalan.startswith("=")
                    kalan = kalan[1:] if esit else kalan
                    if kalan:
                        v = kalan
                    elif i + 1 < len(t):
                        v = t[i + 1]
                        i += 1
                    else:
                        v, kesin = None, False
                        taninmayan.append(f"`{tok}` (değersiz)")
                    if v is not None:
                        if ch == "R":
                            bicim = "kume" if k else ("kisa" if (esit or not kalan) else "bitisik")
                            # Tur-4: onaylı bitişik biçim token'ın KENDİ ham yazımında birebir
                            # `-R<değer>` olmalı (segmentin başka yerindeki yorum/işlenen/başlık
                            # metni sayılmaz) ve değer düz `[\w.:/-]` (kaçış/ikame/tırnak yok).
                            if bicim == "bitisik" and not (
                                    ("-R" + v) in th[i][1] and _GH_BITISIK_DEGER.fullmatch(v)):
                                bicim = "bitisik-dolayli"
                            repolar.append((v, bicim))
                        else:
                            degerler.setdefault(dk[ch], []).append(v)
                    break
                if ch not in bk:
                    kesin = False             # tanınmayan kısa harf
                    taninmayan.append(f"`-{ch}` (`{tok}` içinde)")
                    break
        else:
            konumsal.append(tok)
        i += 1
    return {"kesin": kesin, "repolar": repolar, "degerler": degerler, "konumsal": konumsal,
            "taninmayan": taninmayan}


def _gh_acik_bayrak(seg: str) -> bool:
    """GH-HEDEF "açık hedef" hükmü: pflag çözümlemesinde GERÇEK `--repo`/`-R` değeri var mı.

    Üç koşul birden: ① çözümleme `kesin` (bayatlık ⇒ blok) ② değer boşluksuz ve biçim
    `kume` DEĞİL (`-dR` eskisi gibi blok) ③ main'in metin deseni (`_GH_A_ACIK`) de tutuyor
    YA DA GERÇEK bir `-R` token'ı bitişik biçimde VE metinde birebir `-R<değer>` olarak
    yazılı (kullanıcı onaylı TEK gevşeme, 2026-10-14). ③ main'e göre gevşemeyi YAPISAL
    olarak o tek biçime sınırlar (PowerShell ``--re`po`` / ``-R`org/x`` gibi metinde
    görünmeyen bir hedef eskisi gibi bloklanır). `gh` komut konumunda değilse eski desen.
    ⛔ Bitişik muafiyeti METİN deseniyle (`-R[^\\s=]` herhangi bir yerde) VERİLMEZ (tur-3
    düzeltmesi, ölçüldü): gerçek hedef `"--repo" org/x` iken başlıktaki `-t '-Rx'` metni
    freni açıyordu ⇒ main'in blokladığı biçim onaysız geçiyordu. Muafiyet, muafiyeti
    DOĞURAN token'a bağlıdır.
    ⛔ Tur-4: "metinde birebir" = token'ın KENDİ ham yazımında (biçim `bitisik`, bkz.
    `_gh_bayrak_cozumle`); segmentin herhangi bir yeri DEĞİL — `-R''org/x … # -Rorg/x`
    (yorum) · `-R"org/x" … <<< -Rorg/x` (işlenen) · `-t ' -Rorg/x'` (başlık) metni freni
    açıyordu (main rc 2 → önceki tur rc 0, ölçüldü). Kabuğun gh'ye geçirmediği metin
    (yorum, yönlendirme işleneni) token bile değildir (`_kelimeler_ham`)."""
    c = _gh_bayrak_cozumle(seg)
    if c is None:
        return bool(_GH_A_ACIK.search(seg or ""))
    gercek = [(v, b) for v, b in c["repolar"]
              if b != "kume" and v and not any(x.isspace() for x in v)]
    bitisik = any(b == "bitisik" and _GH_BITISIK_R.search("-R" + v) for v, b in gercek)
    return bool(c["kesin"] and gercek and (_GH_A_ACIK.search(seg) or bitisik))


def _gh_repo_degerleri(seg: str, kesin: bool = False) -> list:
    """`gh` segmentindeki `--repo X` · `--repo=X` · `-R X` · `-RX` · `-R=X` DEĞERLERİ.

    Her token konumu BAĞIMSIZ taranır — bilerek değer TÜKETMEZ: sızıntı gate'inin FAZLA
    aday kümesidir (`-t -R <public>` gibi bir dizide gerçek hedef olmayan `-R`yi de aday
    sayar ⇒ yalnız DAHA ÇOK tarama; bayat bayrak tablosuna karşı sigorta). Kümelenmiş
    `-dR X` de sayılır.
    ⛔ HÜKÜM İÇİN KULLANILMAZ: GH-HEDEF "açık hedef" kararı `_gh_acik_bayrak`'tadır (pflag
    çözümlemesi) — bağımsız tarama orada, bayrak DEĞERİ olan `"--repo"` metnini hedef sayıp
    GEVŞETME üretiyordu (bug-gate F1, 2026-10-14). `kesin=True` kipi geriye dönük durur.
    """
    t = _gh_komut_tokenlari(seg)
    if t is None:
        if kesin:
            m = _GH_A_ACIK.search(seg or "")
            return [m.group(1)] if m else []
        return []
    out = []
    for k, tok in enumerate(t):
        if kesin and any(c.isspace() for c in tok):
            continue
        sonraki = t[k + 1] if k + 1 < len(t) else None
        if tok == "--repo":
            if sonraki is not None:
                out.append(sonraki)
        elif tok.startswith("--repo="):
            out.append(tok[len("--repo="):])
        elif not tok.startswith("--"):
            m = _GH_KISA_REPO.match(tok)
            if not m or (kesin and m.group(1)):
                continue
            kalan = m.group(2)[1:] if m.group(2).startswith("=") else m.group(2)
            if kalan:
                out.append(kalan)
            elif sonraki is not None:
                out.append(sonraki)
    return [v for v in out if v.strip()] if kesin else out


def _gh_konumsal_hedef_var(seg: str) -> bool:
    """`gh repo <alt> <ORG>/<REPO>` — konumsal hedef BÜTÜN bir KONUMSAL token olarak var mı.

    Eskiden `_GH_B_ACIK` `<alt>`tan sonraki METİNDE aranıyordu ⇒ `--description "bkz
    org/x"` hedef sayılıyordu. Token tam olarak `<owner>/<name>` biçiminde olmalı (URL ve
    doldurulmamış `<ORG>/…` yer tutucusu tam eşleşmez — eski desenin iki dışlaması korunur)
    ve bir bayrağın DEĞERİ olmamalı (`--description org/x` hedef DEĞİL — pflag tablosu,
    2026-10-14). `_gh_acik_bayrak` ile aynı iki fren: çözümleme `kesin` olmalı ve main'in
    metin deseni de tutmalı. `gh` komut konumunda değilse eski metin deseni korunur."""
    t = _gh_komut_tokenlari(seg)
    b = _GH_B.search(seg or "")
    eski = bool(b and _GH_B_ACIK.search((seg or "")[b.end():]))
    if t is None or len(t) < 2 or t[0].lower() != "repo":
        return eski
    c = _gh_bayrak_cozumle(seg)
    return bool(eski and c and c["kesin"]
                and any(_GH_KONUMSAL.fullmatch(tok) for tok in c["konumsal"]))



def _gh_hedef_belirsiz(komut: str) -> str:
    """Repoyu DEĞİŞTİREN `gh` komutunda hedef açıkça verilmemişse RED gerekçesi döner.

    ⚠ SEGMENT BAŞINA (2026-08-01, AV-18): hedef-açıklık KOMUT ZİNCİRİNİN TAMAMINDA değil,
    **her mutasyon komutunun KENDİ segmentinde** aranır. Eski hâlinde komutun herhangi bir
    yerinde geçen bir `--repo` (salt-okuma bir `gh repo view` dahil) sonraki HEDEFSİZ
    mutasyonu serbest bırakıyordu:
        gh repo view --repo O/R && gh pr create -t t -b b   → exit 0 (canlı repro)
    Yeni davranış eskisinin ÜST KÜMESİDİR: aynı segmentte hedef varsa yine geçer;
    hiçbir yerde yoksa yine bloklanır — yalnız "başka segmentten ödünç hedef" kapanır.
    """
    # Segment kümesi = eski model ∪ lehçe modeli (2026-10-14): lehçe sınırı farklı çizerse
    # (ör. `\'`) main'in gördüğü bir mutasyon segmenti kaybolmasın — hüküm ikisinde de
    # lehçe token'larıyla verilir.
    for seg in dict.fromkeys(_segmentler(komut, "eski") + _segmentler(komut)):
        neden = _gh_hedef_belirsiz_segment(seg)
        if neden:
            return neden
    return ""


def _gh_hedef_belirsiz_segment(komut: str) -> str:
    """TEK segment için hedef-açıklık kararı (üç grup ayrı ele alınır).

    ⚠ İlk sürüm `api`'yi de `--repo` istiyordu ve `gh repo create org/X`'i blokluyordu →
    `gh api user` / `graphql` / `rate_limit` ve PROJECT_BOOTSTRAP STEP 1 kırılıyordu
    (2026-07-10 regresyon testi).
    """
    acik_bayrak = _gh_acik_bayrak(komut)
    if _GH_A.search(komut) and not acik_bayrak:
        c = _gh_bayrak_cozumle(komut)
        if c and c["repolar"] and not c["kesin"]:
            # `--repo` VAR ama komutun bayrakları çözülemedi — "--repo ver" demek yanıltır.
            return ("hedef repo ÇÖZÜMLENEMEDİ — tanınmayan " + ", ".join(c["taninmayan"][:3])
                    + ": hangi token'ın bayrak DEĞERİ olduğu bilinmeden `--repo`nun gerçek "
                    "hedef olduğu söylenemez (fail-closed). Bayrağı düzelt; gh yeni bir bayrak "
                    "eklediyse tabloyu yeniden üret (infra-test-recipes B82e).")
        return ("hedef repo BELİRSİZ — `gh` repoyu cwd'den çıkarır ve `core/` bir junction'dır; "
                "yanlış repoya yazma/yayın GERİ ALINAMAZ. `--repo <ORG>/<REPO>` AÇIKÇA ver.")
    if _GH_B.search(komut):
        if not (_gh_konumsal_hedef_var(komut) or acik_bayrak):
            return ("hedef repo BELİRSİZ — `gh repo <alt>` argümansız kaldığında cwd'ye düşer. "
                    "Hedefi konumsal ver: `gh repo <alt> <ORG>/<REPO>`.")
    if _GH_C.search(komut) and _GH_C_CWD.search(komut):
        return ("`gh api` yolunda `{owner}`/`{repo}` placeholder'ı var — bunlar cwd'den çözülür "
                "ve `core/` bir junction'dır. Hedefi AÇIK yaz: `repos/<ORG>/<REPO>/...`.")
    return ""

# BAŞLIK SATIRI KORUNUR (grup 1): eski `.*?` DOTALL ilk satırdaki yönlendirmeyi de yutardı.
_HEREDOC = re.compile(r"(<<-?\s*(['\"]?)(\w+)\2[^\n]*)\n(.*?)^\3$", re.MULTILINE | re.DOTALL)
_PS_HERESTRING = re.compile(r"@(['\"])[\s\S]*?^\1@", re.MULTILINE)


def _komut_govdesi(s: str) -> str:
    s = _HEREDOC.sub(lambda m: m.group(1) + " <HEREDOC-STRIPPED>", s)
    return _PS_HERESTRING.sub(" <HERESTRING-STRIPPED> ", s)


def _heredoc_govdeleri(s: str) -> str:
    return "\n".join(m.group(4) for m in _HEREDOC.finditer(s))


# ── KOMUT İKAMESİ İÇİNDEKİ HEREDOC (bug-gate P-1, 2026-10-14) ──────────────────────────
# Claude Code'un VARSAYILAN commit ve PR biçimi:  -m "$(cat <<'EOF' … EOF\n)"  /
# --body "$(cat <<'EOF' … EOF\n)". `_komut_govdesi` heredoc gövdesini `<HEREDOC-STRIPPED>`
# ile değiştirir (komut-niyeti kuralları için DOĞRU — gövde veri, komut değil) ama yayın
# metnini o kırpılmış komuttan okuyan iki gate gövdeyi HİÇ görmüyordu: değer
# `$(cat <<'EOF' <HEREDOC-STRIPPED>\n)` kalıyordu. ÖLÇÜLDÜ: gövdede e-posta / ajan-dışı
# trailer → rc 0; aynı içerik `-F - <<'EOF'` / `--body-file -` biçiminde rc 2.
# Çare YALNIZ iki yayın gate'inde: ham metindeki SAF `$(cat <<[-]X … X)` aralıkları önce
# sayılı yer tutucuya çevrilir, SONRA `_komut_govdesi` uygulanır; değerdeki yer tutucu ham
# gövdeyle çözülür. `komut` (diğer kuralların girdisi) DEĞİŞMEZ.
# Sınırlayıcı tırnaklı/tırnaksız; `<<-` biçiminde kapanış satırı TAB ile girintili olabilir
# (bash'in kuralı; `_HEREDOC` bu biçimi hiç tanımıyordu). Kapanış satırı bash'teki gibi
# YALNIZ sınırlayıcıdır.
# ⛔ GÖVDE İLK SINIRLAYICI SATIRINI GEÇEMEZ (bug-gate turu 3, 2026-10-14 — ölçülmüş
# GEVŞETME kapandı): gövde eskiden tembel `(.*?)` + DOTALL idi. İlk `EOF` satırından sonra
# `)` gelmezse (`$(cat <<'EOF'\nok\nEOF\necho)`) eşleşme bir SONRAKİ `EOF\n)`'e kadar
# uzuyordu; bash ise heredoc'u İLK `EOF` satırında bitirir. Aradaki `cd` / `git commit` /
# `gh pr create` segmentleri yer tutucunun içinde kalıyor ve TARANMIYORDU (canlı CLI: rc 0,
# taban rc 2). Temperlenmiş gövde (`(?:(?!^…\3$).)*?`) ilk kapanış satırında durur; o
# satırdan sonra `)` yoksa bu aralık hiç eşleşmez ve `_komut_govdesi`'nin olağan yoluna
# kalır (heredoc kırpılır, sonraki segmentler TARANIR). İkinci normalizasyonun kuralı:
# segment sınırını `_komut_govdesi`'nden FARKLI çizmemek (lessons-learned PATTERN #12).
_CAT_HEREDOC = re.compile(
    r"\$\(\s*cat\s+<<(-)?\s*(['\"]?)(\w+)\2[ \t]*\n"
    r"((?:(?!^(?(1)\t*)\3$).)*?)^(?(1)\t*)\3$\s*\)",
    re.MULTILINE | re.DOTALL)
_CAT_YER = "\x00CATHD{}\x00"
_CAT_YER_RX = re.compile(r"\x00CATHD(\d+)\x00")
_KIRPIK_ISARET = ("<HEREDOC-STRIPPED>", "<HERESTRING-STRIPPED>")
# LİTERAL İŞARET KAÇIŞI (bug-gate turu 3 G2, 2026-10-14): kullanıcının KENDİ yazdığı
# `<HEREDOC-STRIPPED>` dizgesi (guard'ı anlatan commit/PR metni) normalizasyonun ürettiği
# işaretle ayırt edilemiyordu ⇒ tırnaklı değer FAIL-CLOSED bloklanıyordu (PATTERN #12
# dogfood'u). Ham metindeki literal işaret normalizasyondan ÖNCE \x00 yer tutucuya alınır;
# değerde kalan GERÇEK işaret yalnız `_komut_govdesi`'nin kırpmasından gelebilir. Karar
# verildikten sonra literal geri konur (taranan metin kullanıcının yazdığıdır).
# Seçilmeyen alternatif — "işaret ham değerde de var mı" kıyası: ham ile normalize komutun
# değer listeleri hizalanamaz (stdin heredoc'u ham'da ayrı segmentler üretir) ve küme
# kıyası, aynı komutta BAŞKA bir değerdeki literal işaretle gerçek bir ikameyi maskeler.
_LIT_YER = "\x00CATLIT{}\x00"
_LIT_YER_RX = re.compile(r"\x00CATLIT(\d)\x00")
# Çıplak `$` değeri yalnız tırnaksız `$(` ikamesinin `(`'te bölünmesinden doğar ⇒ segment
# tırnaksız bir `$` ile BİTER. `-m '$'` (kullanıcının yazdığı tek karakter) tırnakla biter.
# ⛔ ÖNKOŞUL YOK (bug-gate turu 4 G4-1, 2026-10-14 — ölçülmüş GEVŞETME kapandı): desen
# eskiden `(?:^|[\s=])\$` idi ⇒ BİTİŞİK kısa bayrakta (`-m$(…)` · `-am$(…)` · `-qam$(…)` ·
# PowerShell `-m$(Get-Content …)` · `-m$((…))`) segment `m$` ile bitiyor, koşul tutmuyor ve
# FAIL-CLOSED atlanıyordu (gerçek CLI: public hedefte rc 0, `1f2860a` rc 2). Tırnaklı
# `'$'` / `"$"` / `-m"$"` zaten tırnakla biter — onaylı daraltma bu desensiz de korunur.
_CIPLAK_DOLAR_SONU = re.compile(r"\$\s*$")


def _literal_kac(s: str) -> str:
    for i, isaret in enumerate(_KIRPIK_ISARET):
        s = s.replace(isaret, _LIT_YER.format(i))
    return s


def _literal_geri(s: str) -> str:
    return _LIT_YER_RX.sub(lambda m: _KIRPIK_ISARET[int(m.group(1))], s or "")


def _ikame_cozumlu_komut(ham: str) -> tuple:
    """(yayın-gate komutu, cat-heredoc gövdeleri). Komut = `_komut_govdesi` ile AYNI
    normalizasyon; tek fark saf `$(cat <<X … X)` aralıklarının sayılı yer tutucu olması."""
    govdeler: list = []

    def _yer(govde: str) -> str:
        govdeler.append(_literal_geri(govde))
        return _CAT_YER.format(len(govdeler) - 1)

    s = _CAT_HEREDOC.sub(lambda m: _yer(m.group(4)), _literal_kac(ham or ""))
    # PowerShell here-string (`-m @'…'@`) aynı sınıf: kırpılırsa değer `<HERESTRING-STRIPPED>`
    # kalır. Gövdesi doğrudan okunur (yer tutucu) — fail-closed'a düşürüp meşru PowerShell
    # commit'ini bloklamamak için.
    s = _PS_HERESTRING.sub(lambda m: _yer(m.group(0)[2:-2]), s)
    return _komut_govdesi(s), govdeler


def _ikame_degerlerini_coz(degerler: list, govdeler: list, seg: str = None) -> tuple:
    """Bayrak değerlerindeki cat-heredoc yer tutucusunu ham gövdeyle değiştirir.
    Dönüş: (değerler, hata). ÇÖZÜLEMEYEN biçim FAIL-CLOSED:
      · değerde kırpılmış heredoc/here-string işareti kaldıysa (saf `cat` olmayan ikame:
        `$(sed … <<X)`, `$(cat <<X | …)`) gövde bilinemez — kullanıcının yazdığı literal
        işaret `_ikame_cozumlu_komut`'ta kaçırılmıştır, burada işaret SAYILMAZ;
      · değer çıplak `$` ise VE segment tırnaksız `$` ile bitiyorsa tırnaksız `$( … )`
        ikamesi segmentlere bölünmüştür (`seg` verilmezse eski geniş kural: her `$`)."""
    ciplak_ikame = seg is None or bool(_CIPLAK_DOLAR_SONU.search(seg))
    cozulen = []
    for v in degerler:
        if any(i in v for i in _KIRPIK_ISARET) or (v.strip() == "$" and ciplak_ikame):
            return [], ("deger bir komut ikamesi ve govdesi cozulemedi (yalniz "
                        "`\"$(cat <<'X' … X)\"` bicimi okunur). FAIL-CLOSED: bu bicimi, "
                        "heredoc'lu stdin'i ya da dosyayi kullan.")
        cozulen.append(_literal_geri(_CAT_YER_RX.sub(
            lambda m: govdeler[int(m.group(1))] if int(m.group(1)) < len(govdeler) else "",
            v)))
    return cozulen, ""


_KABUK_TOOLLARI = ("Bash", "PowerShell")
_ARG_REPO = re.compile(r"--repo[= ]+([^\s'\"]+)")
_ARG_BODYFILE = re.compile(
    r"(?:--body-file|--notes-file|(?<![\w-])-F)[= ]+(?:'([^']+)'|\"([^\"]+)\"|(\S+))")
_CD_PREFIX = re.compile(r"\bcd\s+([^\s;&|]+)")
_AYRAC = re.compile(r"\s*(?:\|\||&&|[;|&\n])\s*")
_POSIX_SURUCU = re.compile(r"^/([A-Za-z])/(.*)$")


def _win_yol(yol: str) -> str:
    """Git-Bash POSIX yolunu Windows yoluna çevirir (`/c/IX/X` → `C:\\IX\\X`).

    NEDEN (2026-07-30 vakası): Bash tool'unda `cd /c/IX/<proje> && git commit …` yazıldığında
    `_CD_PREFIX` POSIX yolu yakalıyor, `subprocess(cwd=...)` Windows'ta bu yolu bulamıyor →
    exception → görünürlük sorulamıyor → fail-closed → PRIVATE repo public sayılıp meşru
    commit bloklanıyordu. Yön güvenliydi ama yanlış-pozitif bypass alışkanlığı doğurur.
    """
    yol = (yol or "").strip().strip("'\"")
    m = _POSIX_SURUCU.match(yol)
    if m:
        return f"{m.group(1).upper()}:\\" + m.group(2).replace("/", "\\")
    return yol


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


def _yayinlanan_metin(komut: str, ham: str, govdeler: list = ()) -> tuple:
    """--title/--body/--notes (+ kısa bayraklar) + --body-file/--notes-file İÇERİĞİ.
    `--body-file -` (stdin) heredoc'tan çözülür (eski sürüm fail-closed ediyordu →
    meşru PR durdu, 2026-07-09). `gh api` için gövde çıkarılamaz → TÜM komut taranır
    (fail-closed). `govdeler`: `_ikame_cozumlu_komut`'un cat-heredoc gövdeleri — değerdeki
    yer tutucu bunlarla çözülür (P-1 kardeşi, 2026-10-14). Dönüş: (metin, hata)."""
    if re.search(r"(?<!\w)gh\s+api\b", komut, re.IGNORECASE):
        # Komutun tamamı taranır: yer tutucu da gövdesiyle açılır (`<<-` gövdesi `_HEREDOC`
        # kümesinde yoktur — açılmasaydı eskiden taranan ham metin görünmez olurdu).
        acik = _literal_geri(_CAT_YER_RX.sub(
            lambda m: govdeler[int(m.group(1))] if int(m.group(1)) < len(govdeler) else "",
            komut))
        return acik + "\n" + _heredoc_govdeleri(ham), ""

    # BİRLEŞİM (bug-gate kol b, 2026-10-14): regex değerleri METNİN İLK eşleşmesidir ve tek
    # tırnakta apostrofta KESİLİR (`-b 'main'\''e <iz>'` → `main`; `--title 'bkz --body x'
    # --body '<iz>'` → `x'`) ⇒ gövde TARANMIYORDU. Lehçe kolunda pflag çözümlemesinin
    # GERÇEK değerleri de eklenir (eski kol AYNEN: Windows yolunu bozan eski çift-tırnak
    # kaçışı yeni dosya okuma hatası üretmesin). Fazla değer = yalnız daha çok tarama.
    regex_degerleri = [_arg_deger_kisa(komut, "title"), _arg_deger_kisa(komut, "body"),
                       _arg_deger_kisa(komut, "notes")]
    bf = _ARG_BODYFILE.search(komut)
    yollar = [bf.group(1) or bf.group(2) or bf.group(3)] if bf else []
    c = _gh_bayrak_cozumle(komut) if _LEHCE != "eski" else None
    if c:
        for ad in ("title", "body", "notes"):
            regex_degerleri += c["degerler"].get(ad, [])
        for ad in ("body-file", "notes-file"):
            yollar += c["degerler"].get(ad, [])
    parcalar, hata = _ikame_degerlerini_coz(
        [v for v in dict.fromkeys(regex_degerleri) if v], list(govdeler), komut)
    if hata:
        return "", hata
    for yol in dict.fromkeys(yollar):
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


def _lehce_ile(lehce: str, fn, *args):
    """`fn`'i verilen kabuk lehçesiyle koşar (`_LEHCE` geri yüklenir)."""
    global _LEHCE
    onceki = _LEHCE
    _LEHCE = lehce
    try:
        return fn(*args)
    finally:
        _LEHCE = onceki


def _iki_lehce(lehce: str, fn, *args) -> str:
    """Sızıntı gate'i BİRLEŞİMİ: önce eski model (önceki davranış birebir ⇒ main'e göre
    gevşeme yapısal olarak 0), sonra aracın lehçesi (`'\''` · `$'…'` · backtick). İlk
    bulgu döner."""
    for l in dict.fromkeys(("eski", lehce)):
        sorun = _lehce_ile(l, fn, *args)
        if sorun:
            return sorun
    return ""


# `gh api` değer ALAN bayrakları (uç token'ı bunların değerinden ayırt edilsin).
_GH_API_DEGERLI = frozenset({"-X", "--method", "-f", "--raw-field", "-F", "--field", "-H",
                             "--header", "--input", "-q", "--jq", "-t", "--template",
                             "--hostname", "--cache", "-p", "--preview"})
_GH_API_REPO_YOLU = re.compile(
    r"^(?:https?://[^/\s]+)?/?repos/([A-Za-z0-9][\w.-]*)/([A-Za-z0-9][\w.-]*)(?:[/?#]|$)",
    re.IGNORECASE)


def _gh_api_hedef_repo(seg: str) -> str:
    """`gh api <uç>` segmentinde uç yolundaki `<ORG>/<REPO>` ("" = yol yok / yer tutucu)."""
    m = _GH_API_REPO_YOLU.match(_gh_api_ucu(seg))
    return f"{m.group(1)}/{m.group(2)}" if m else ""


def _gh_api_yayin_mi(seg: str) -> bool:
    """K1 kardeşi (2026-10-14): `_GH_PUBLIC_YAYIN` `gh api` ucunu YALNIZ `api`den hemen
    sonraki token'da arar ⇒ `gh api -X POST repos/<o>/<r>/pulls -f body=…` (bayrak önce)
    yayın sayılmıyor, gövde TARANMIYORDU (taban da rc 0). Uç token'ı bayraklar atlanarak
    bulunur; yayın sınıfı aynı (`pulls|issues|releases`)."""
    return bool(re.search(r"(?:pulls|issues|releases)", _gh_api_ucu(seg), re.IGNORECASE))


def _gh_api_ucu(seg: str) -> str:
    """`gh api` segmentinin UÇ token'ı (değer alan bayraklar atlanır; yoksa "")."""
    t = _kelimeler(seg)
    i = 0
    while i < len(t) and _ATAMA.match(t[i]):
        i += 1
    if (i + 1 >= len(t) or t[i].replace("\\", "/").rsplit("/", 1)[-1].lower()
            not in ("gh", "gh.exe") or t[i + 1].lower() != "api"):
        return ""
    i += 2
    while i < len(t):
        k = t[i]
        if k.startswith("-") and k != "-":
            i += 2 if (k in _GH_API_DEGERLI) else 1
            continue
        return k
    return ""


def _hay_hedefi(hay: str) -> tuple:
    """`hay`'in TEK sorgu hedefi: ("repo", X) ya da ("cwd", yol). İlk `--repo`, yoksa ilk
    `cd`, yoksa proje kökü. ⚠ Bu bir KARAR değildir — metindeki ilk eşleşmeyi alır; karar
    `_hedef_public_mu`'dadır (aday birleşimi). Yalnız tek-aday sorgusu + tekilleştirme anahtarı."""
    m = _ARG_REPO.search(hay or "")
    if m:
        return "repo", m.group(1)
    c = _CD_PREFIX.search(hay or "")
    cwd = _win_yol(c.group(1)) if c else str(_PROJ_ROOT)
    # ⛔ İSTİSNA = FAIL-CLOSED (bug-gate F3, 2026-10-14): `is_dir()` yalnız "yok" hatalarını
    # yutar; erişim/aygıt hatası (`C:/Windows/System32/config/SAM` → WinError 5 ·
    # `//./PhysicalDrive0` → WinError 31) İSTİSNA atıyordu. `main` yakalamaz, `hook_shim`
    # yalnız SystemExit yakalar ⇒ çökme = guard'ın TÜM kuralları atlanır (fail-open; main'de
    # de `cd //./PhysicalDrive0` çöküyordu). Çözülemeyen aday PUBLIC sayılır.
    try:
        if not Path(cwd).is_dir():          # çözülemeyen cd → proje köküne düş
            cwd = str(_PROJ_ROOT)           #   (yoksa cwd hatası fail-closed'a kaçar)
    except (OSError, ValueError):
        return "cozulemedi", cwd
    return "cwd", cwd


def _repo_public_mu(hay: str) -> tuple:
    """TEK aday için görünürlük CANLI sorulur (gh repo view). Kararsızsa FAIL-CLOSED
    (public say). ⛔ Hedef KARARI için doğrudan çağırma: `hay`'deki ilk `--repo`/`cd`
    metin içinden gelebilir (maskeleme) — `_hedef_public_mu` kullan."""
    import subprocess
    anahtar = _hay_hedefi(hay)
    if anahtar in _GORUNURLUK:
        return _GORUNURLUK[anahtar]
    tur, deger = anahtar
    if tur == "cozulemedi":
        return True, "hedef-cozulemedi(fail-closed)"
    argv = ["gh", "repo", "view", "--json", "isPrivate,nameWithOwner"]
    cwd = None
    if tur == "repo":
        argv.insert(3, deger)
    else:
        cwd = deger
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=15, cwd=cwd, shell=False)
        if r.returncode != 0:
            return True, "gorunurluk-sorulamadi(fail-closed)"
        d = json.loads(r.stdout)
        sonuc = ((not d.get("isPrivate", True)), d.get("nameWithOwner", "?"))
    except Exception:
        return True, "gorunurluk-sorulamadi(fail-closed)"
    _GORUNURLUK[anahtar] = sonuc
    return sonuc


# Tek `main()` çağrısı içinde (sorgu anahtarı → sonuç). İki lehçe kolu aynı hedefi yeniden
# sormasın; yalnız BAŞARILI sorgu saklanır (fail-closed sonuç her seferinde yeniden denenir).
# `main()` başında boşaltılır (fixture'lar tek süreçte çok vaka koşar).
_GORUNURLUK: dict = {}


# ── ADAY BİRLEŞİMİ (repo-maskeleme turu, 2026-10-14) ───────────────────────────────────
# VAKA (ölçüldü, ağsız + canlı CLI): yayın/commit segmentinin hedefi `hay` METNİNDEKİ ilk
# `--repo` / ilk `cd` / ilk `git -C`'den çözülüyordu. Tırnaklı başlık/gövde/mesaj içindeki
# `--repo <ORG>/<PRIVATE>` (ya da `cd <private-yol>`, ya da çok satırlı mesajda
# `\ngit -C <private-yol>`) gerçek PUBLIC hedefi maskeliyor, gövde TARANMADAN geçiyordu
# (rc 0). Ayrıca gh'nin kısa bayrağı `-R` hiç tanınmıyordu: `gh pr create -R <public>`
# private proje kökünden cwd'ye düşüp aynı şekilde geçiyordu.
_HEDEF_ADAY_TAVANI = 5


def _hedef_public_mu(eski_hay: str, adaylar: list) -> tuple:
    """Sızıntı gate'lerinin hedef KARARI. Aday kümesi = ESKİ tek-aday (`eski_hay`: main'in
    birebir sorgusu, metnin ilk `--repo`/`cd`'si) ∪ GERÇEK token adayları (`adaylar`: her
    biri `--repo X` · `cd <yol>` · "" = proje kökü). BİRİ public ise public.

    Eski aday neden tutuluyor: (1) main'e göre gevşeme YAPISAL olarak 0 — main'in public
    dediği her girdide aynı sorgu aynen sorulur; (2) PATTERN #12 — yeni token görüşü
    kelime/segment sınırını eskisinden farklı çizerse sonuç en fazla DAHA ÇOK taramadır,
    sessiz geçiş olamaz. Bedel (bilinçli, lider kararı 2026-10-14): metinde public geçen
    private hedefli yayının/commit'in mevcut FP'si aynen KALIR (daraltma = gevşetme).
    Maliyet: anahtar (`_hay_hedefi`) başına TEKİL `gh repo view`, ilk public'te durur;
    tekil aday sayısı `_HEDEF_ADAY_TAVANI`'nı aşarsa sorgusuz FAIL-CLOSED."""
    sorgular, gorulen = [], set()
    for h in [eski_hay] + list(adaylar):
        anahtar = _hay_hedefi(h)
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        sorgular.append(h)
    if len(sorgular) > _HEDEF_ADAY_TAVANI:
        return True, "hedef-aday-tavani-asildi(fail-closed)"
    ilk_repo = ""
    for h in sorgular:
        public, repo = _repo_public_mu(h)
        if public:
            return True, repo
        ilk_repo = ilk_repo or repo
    return False, ilk_repo or "?"


def _baglam_cwd_hay(segler: list, idx: int) -> str:
    """Gerçek kabuk bağlamının cwd adayı: <idx>'ten önceki SON `cd` segmentinin YOL
    token'ı (`cd <yol>`); bağlam yoksa "" (= proje kökü). `_kabuk_baglami`'nın token hâli."""
    onceki = [s for s in segler[:idx] if re.match(r"^\s*cd\s+", s)]
    if not onceki:
        return ""
    t = _kelimeler(onceki[-1])
    return f"cd {t[1]}" if len(t) > 1 else ""


def _gh_hedef_adaylari(segler: list, idx: int, seg: str, api_repo: str = "") -> list:
    """`gh` yayın segmentinin hedef adayları: FAZLA bağımsız tarama (`_gh_repo_degerleri`)
    ∪ pflag çözümlemesinin gerçek `--repo`/`-R` değerleri (+ `gh api` yol hedefi).

    Gerçek cwd (gh `--repo`suz cwd'ye düşer) KESİN bir gerçek hedef yoksa EKLENİR (bug-gate
    P1, 2026-10-14): eskiden aday listesinde herhangi bir `--repo` metni varsa cwd hiç
    sorulmuyordu ⇒ kök public iken `-t "--repo=org/private" -b '<iz>'` (değer, hedef değil)
    gövdeyi taramadan geçiyordu (main ve önceki tur rc 0). Çözümleme `kesin` değilse (bayat
    tablo) de cwd eklenir — bayatlık en fazla fazla taramadır."""
    c = _gh_bayrak_cozumle(seg)
    gercek = [v for v, _ in c["repolar"]] if c else []
    repolar = _gh_repo_degerleri(seg) + gercek + ([api_repo] if api_repo else [])
    adaylar = [f"--repo {r}" for r in dict.fromkeys(repolar)]
    if not (api_repo or (c and c["kesin"] and gercek)):
        adaylar.append(_baglam_cwd_hay(segler, idx))
    return adaylar


_GIT_HEDEF_UST = frozenset({"-C", "--git-dir", "--work-tree"})
_GIT_HEDEF_ORTAM = frozenset({"GIT_DIR", "GIT_WORK_TREE"})


def _mutlak_yol_mu(y: str) -> bool:
    return bool(os.path.isabs(y) or _POSIX_SURUCU.match(y) or re.match(r"^[A-Za-z]:[\\/]", y))


def _git_hedef_adaylari(segler: list, idx: int, seg: str) -> list:
    """`git commit` segmentinin GERÇEK depo adayları: komut konumundaki `git`in üst
    seçenekleri `-C` · `--git-dir` · `--work-tree` (+ `GIT_DIR=`/`GIT_WORK_TREE=` önekleri);
    yoksa gerçek bağlam cwd'si. Göreli yol bağlam `cd`sine göre çözülür. `.git` ile biten
    git-dir'in üst dizini sorulur (gh depo kökünden görünürlük okur)."""
    t = _kelimeler(seg)
    yollar, i = [], 0
    while i < len(t) and _ATAMA.match(t[i]):
        ad, _, deger = t[i].partition("=")
        if ad in _GIT_HEDEF_ORTAM and deger:
            yollar.append(deger)
        i += 1
    if i < len(t) and t[i].replace("\\", "/").rsplit("/", 1)[-1].lower() in ("git", "git.exe"):
        i += 1
        while i < len(t) and t[i].startswith("-"):
            ad, esit, deger = t[i].partition("=")
            if ad in _GIT_HEDEF_UST:
                if esit:
                    yollar.append(deger)
                elif i + 1 < len(t):
                    yollar.append(t[i + 1])
                    i += 1
            elif t[i] in _GIT_UST_DEGERLI:
                i += 1
            i += 1
    baglam = _baglam_cwd_hay(segler, idx)
    if not yollar:
        return [baglam]
    taban = baglam[3:] if baglam else ""
    out = []
    for y in yollar:
        y = re.sub(r"[\\/]\.git[\\/]?$", "", y) or y
        if taban and not _mutlak_yol_mu(y):
            y = taban.rstrip("/\\") + "/" + y
        out.append(f"cd {y}")
    return out


def _gh_pr_public_leak(komut: str, ham: str) -> str:
    """SEGMENT BASINA (2026-08-01, AV-18b — CANLI kanitli sinif-kardesi).

    Eskiden gorunurluk KOMUTUN TAMAMINDAKI ilk `--repo`dan cozuluyordu. Zincirin ilk
    komutu PRIVATE bir repoyu isaret ediyorsa (salt-okuma bile olsa) gate "private"
    diyip SUSUYOR, oysa ikinci komut PUBLIC repoya yayin yapiyordu:
        gh pr view 1 --repo <PRIVATE> && gh pr create --repo <PUBLIC> -b '<iz>'
    Canli olcum (2026-08-01, gercek iki repo): blok=False — SIZDI. Artik her yayin
    segmenti KENDI hedefiyle degerlendirilir.

    Segmentler kırpılmış `komut`tan DEĞİL, `_ikame_cozumlu_komut(ham)`dan alınır
    (bug-gate P-1 kardeşi, 2026-10-14): `--body "$(cat <<'EOF' … EOF)"` gövdesi kırpılmış
    komutta yoktu ⇒ PR/issue/release gövdesi taranmadan yayınlanıyordu.
    """
    yayin_komutu, govdeler = _ikame_cozumlu_komut(ham) if ham else (komut, [])
    segler = _segmentler(yayin_komutu)
    for i, seg in enumerate(segler):
        if not (_GH_PUBLIC_YAYIN.search(seg) or _gh_api_yayin_mi(seg)):
            continue
        hay = _kabuk_baglami(segler, i) + seg
        # K1 (bug-gate turu 3, 2026-10-14): `gh api` hedefi cwd'den DEĞİL uç yolundan gelir.
        # Eskiden `cd`/`--repo` yoksa görünürlük proje kökünden soruluyordu ⇒ private proje
        # içinden `gh api repos/<public>/…/pulls -f body=…` gövdesi TARANMADAN geçiyordu.
        # Yol `repos/<ORG>/<REPO>` taşıyorsa o repo sorulur (`--repo` öneki `_ARG_REPO`'nun
        # İLK eşleşmesidir); yol yoksa / `{owner}` yer tutuculuysa eski davranış (o durumu
        # GH-HEDEF kuralı ayrıca bloklar).
        api_repo = _gh_api_hedef_repo(seg)
        if api_repo:
            hay = f"--repo {api_repo}\n" + hay
        # Repo-maskeleme (2026-10-14): `hay` yalnız ESKİ aday; karar gerçek token
        # adaylarıyla birleşimden (`_hedef_public_mu`).
        public, repo = _hedef_public_mu(hay, _gh_hedef_adaylari(segler, i, seg, api_repo))
        if not public:
            continue
        metin, hata = _yayinlanan_metin(seg, ham, govdeler)
        if hata:
            return f"public repo '{repo}' — {hata}"
        bulgular = [f"{ad}: '{tok}'" for tok, ad in sizintilari_bul(metin, _CORE_LEAK)][:6]
        if bulgular:
            return f"public repo '{repo}' — yayinlanan baslik/govdede " + "; ".join(bulgular)
    return ""


# ---------------------------------------------------------------------------
# COMMIT MESAJI SIZINTI GATE (2026-07-28 — yasanmis bosluk)
#
# VAKA: DEV_CORE'a (PUBLIC) atilan bir commit'in MESAJINDA proje obje adi vardi.
# `core_precommit` commit'in ICERIGINI (dosyalari) tarar — MESAJINI TARAMAZ.
# `_gh_pr_public_leak` ise yalniz `gh` yayin komutlarina bakar. Arada kalan
# commit mesaji push'la birlikte PUBLIC repoya gider ve GitHub'da kalicidir.
# Gercekten yasandi: PR govdesi guard'a takildi, ama AYNI ad zaten commit
# mesajiyla push edilmisti (amend + force-push ile temizlendi).
#
# Neden commit ANINDA: mesaji o an degistirmek bedavadir; push'tan sonra
# gecmisi yeniden yazmak gerekir (ve baskasi cektiyse artik gec kalinmistir).
# ---------------------------------------------------------------------------
_GIT_COMMIT = re.compile(
    r"(?:^|[\n;|&(])\s*(?:[A-Za-z_]\w*=\S+\s+)*git\s+(?:-C\s+\S+\s+)*commit\b",
    re.IGNORECASE)
_GIT_C_PATH = re.compile(r"(?:^|[\n;|&(])\s*git\s+-C\s+(?:'([^']+)'|\"([^\"]+)\"|(\S+))")
_GIT_M = re.compile(r"(?<![\w-])(?:-m|--message)[= ]+(?:'([^']*)'|\"((?:[^\"\\]|\\.)*)\"|(\S+))")


# AJAN IMZA SATIRLARI taramadan cikarilir — YANLIS-POZITIF onlemi.
# Ajan atif trailer'i (`Co-Authored-By: Claude … <ureticinin noreply adresi>`) her ajan
# commit'inde ZORUNLU boilerplate'tir ve e-posta yapisal desenine UYAR; muafiyetsiz gate
# TUM core commit'lerini bloklar -> kapatilir -> koruma sifirlanir.
# ⛔ DARALTILDI (2026-10-12, Part E kardesi): eskiden `Co-Authored-By|Claude-Session|
# Signed-off-by|Reviewed-by|Cc` anahtarli HER satir adresten bagimsiz dusuyordu ⇒ baska
# bir kisinin e-postasini tasiyan trailer taramadan SESSIZCE geciyordu. Artik yalniz ajanin
# kendi uc satiri (atif · oturum · uretici) muaftir; baska adres/ad tasiyan her trailer
# TARANIR. Desen TEK KAYNAKTA: `genericize_common.AJAN_IMZA_SATIRI` (core_precommit'in
# `_ATIF_SATIRI`'yla ayni cekirdek). Satir satir uygulanir; satir numarasi korunur.
# ⛔ ATIF SATIRI BOSALTILMAZ (bug-gate F3, 2026-10-14): ad bolumu `@` disinda her seyi
# tasiyabilir; satiri bosaltmak oraya yazilan obje/paket adini taramadan geciriyordu.
# Yalniz uretici adresi silinir, satirin geri kalani TARANIR.
def _git_imza_satiri(s: str) -> str:
    """Tek satir: atif satirinda YALNIZ uretici adresi silinir · oturum/uretici satiri bosalir."""
    if ATIF_SATIRI.match(s):
        return ATIF_ADRES_PAT.sub("", s, count=1)
    return "" if AJAN_IMZA_SATIRI.match(s) else s


def _git_imza_satirlari_ayikla(metin: str) -> str:
    """Ajan imza satirlarini notrler (atif: adres · oturum/uretici: satir); geri kalan TARANIR."""
    return "\n".join(_git_imza_satiri(s) for s in (metin or "").split("\n"))


def _git_commit_mesaji(komut: str, ham: str, govdeler: list = ()) -> tuple:
    """`git commit` mesajini cikarir. Donus: (metin, hata); cozulemezse FAIL-CLOSED.

    `-m "$(cat <<'EOF' … EOF)"` (Claude Code'un varsayilan bicimi): deger yer tutucu
    tasir, `govdeler`den (ham metin) cozulur; saf `cat` olmayan ikame FAIL-CLOSED
    (`_ikame_degerlerini_coz`, bug-gate P-1 2026-10-14).

    TOKEN-TABANLI (2026-08-01, AV-16/17): tum bayrak bicimleri TEK dilbilgisinden
    cozulur — `-m X` · `-mX` · `-am X` (KUMELENMIS) · `-qam X` · `--message X` ·
    `--message=X` · COKLU `-m a -m b` · `-F f` · `-F -` · `--file f` · `--file=f`.
    Eski regex yolu (`_GIT_M` + `_ARG_BODYFILE`) AYRISTIRICI-SIGORTASI olarak durur:
    tokenizer bir `git commit` segmenti bulamazsa (beklenmedik sozdizimi) eski yol
    kosar → kapsam kaybi olmaz, yalnizca EKLENIR.
    """
    diziler = _git_commit_arg_dizileri(komut)
    parcalar, dosyalar = [], []
    for t in diziler:
        parcalar += _bayrak_degerleri(t, _GIT_MSG_UZUN, _GIT_MSG_KISA)
        dosyalar += _bayrak_degerleri(t, _GIT_DOSYA_UZUN, _GIT_DOSYA_KISA)
    if not diziler:                       # sigorta: eski (regex) yol
        parcalar += [(m.group(1) or m.group(2) or m.group(3) or "")
                     for m in _GIT_M.finditer(komut)]
        bf = _ARG_BODYFILE.search(komut)
        if bf:
            dosyalar.append(bf.group(1) or bf.group(2) or bf.group(3))
    parcalar, hata = _ikame_degerlerini_coz(parcalar, list(govdeler), komut)
    if hata:
        return "", "-m " + hata
    for yol in dosyalar:
        if yol in ("-", "/dev/stdin"):
            govde = _heredoc_govdeleri(ham)
            if not govde.strip():
                return "", ("-F - (stdin) commit mesaji cozulemedi. FAIL-CLOSED: mesaji "
                            "heredoc ile ver ya da -F <dosya> kullan.")
            parcalar.append(govde)
        else:
            try:
                parcalar.append(Path(yol).read_text(encoding="utf-8", errors="replace"))
            except Exception:
                return "", (f"-F/--file dosyasi okunamadi ({yol}). FAIL-CLOSED: okunur "
                            "yap veya -m kullan.")
    return _git_imza_satirlari_ayikla("\n".join(p for p in parcalar if p)), ""


def _git_commit_public_leak(komut: str, ham: str) -> str:
    """SEGMENT BASINA degerlendirilir (2026-08-01): `cd A && git commit …` zincirinde
    gorunurluk o segmentin BAGLAMIYLA sorulur; birden fazla commit varsa HER BIRI taranir.
    Eskiden komutun tamami tek parca sayiliyordu → zincirdeki ilk `--repo`/`cd`
    yanlis repoyu gosterebiliyordu (AV-18 ile ayni sinif).

    Segmentler kirpilmis `komut`tan DEGIL, `_ikame_cozumlu_komut(ham)`dan alinir (bug-gate
    P-1, 2026-10-14): `-m "$(cat <<'EOF' … EOF)"` mesaji kirpilmis komutta yoktu."""
    commit_komutu, govdeler = _ikame_cozumlu_komut(ham) if ham else (komut, [])
    segler = _segmentler(commit_komutu)
    for i, seg in enumerate(segler):
        diziler = _git_commit_arg_dizileri(seg)
        if not (diziler or _GIT_COMMIT.search(seg)):
            continue
        # `git -C <yol> commit` hedefi: _repo_public_mu `cd` onekine bakar, `-C`'ye bakmaz.
        # Yolu ona `cd <yol>` gibi gostererek dogru repoyu sorgulatiyoruz.
        hay = _kabuk_baglami(segler, i) + seg
        gc = _GIT_C_PATH.search(seg)
        if gc:
            hay = f"cd {gc.group(1) or gc.group(2) or gc.group(3)}\n" + hay
        # Repo-maskeleme (2026-10-14): `_GIT_C_PATH` ve `_repo_public_mu` METİNDE arar
        # (mesajdaki `--repo x` / `cd x` / `\ngit -C x` hedef olurdu) ⇒ `hay` yalnız ESKİ
        # aday; gerçek adaylar komut konumundaki `git`in üst seçeneklerinden.
        public, repo = _hedef_public_mu(hay, _git_hedef_adaylari(segler, i, seg))
        if not public:
            continue
        metin, hata = _git_commit_mesaji(seg, ham, govdeler)
        if hata:
            return f"public repo '{repo}' — {hata}"
        if not metin.strip():
            continue       # -m/-F yok (editor acilacak) -> taranacak metin yok
        bulgular = [f"{ad}: '{tok}'" for tok, ad in sizintilari_bul(metin, _CORE_LEAK)][:6]
        if bulgular:
            return f"public repo '{repo}' — commit MESAJINDA " + "; ".join(bulgular)
    return ""


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


# AV-21 (2026-08-01, KRİTİK): core kimliği YOL-DİZGESİNDEN okunuyordu (`/core/`,
# `dev_core`). Bir `git worktree` core'un TAM KOPYASIDIR ama adı tutmaz
# (`C:\IX\_wt\guard`) → GENERICIZE-LEAK kuralı orada SESSİZCE kapalıydı. Üstelik
# worktree, infra-expert'in ZORUNLU çalışma alanıdır: çekirdeği düzenlediğimiz tek
# yerde yazım-anı koruması yoktu (ölçüm: aynı payload DEV_CORE'da exit 2, worktree'de
# exit 0). Hafifletici (CANLI doğrulandı 2026-08-01): commit anında `core_precommit`
# worktree'de ÇALIŞIYOR (`git rev-parse --show-toplevel` → repo-göreli) — sızıntılı
# dosya stage'lenip koşuldu, **exit 1**. Yani son kapı ayaktaydı, delik yazım-anındaydı.
#
# ÇÖZÜM: yol-dizgesi KALDIRILMADI (junction senaryosunda `<proje>/core/...` yolu
# çalışan tek ipucu olabilir) — üstüne **işaret-dosyası** ekseni eklendi: bir üst-dizin
# hem `CLAUDE.core.md` hem `claude/kesin-yasaklar.canonical.md` taşıyorsa orası core
# deposudur (worktree/klon/yeniden-adlandırma fark etmez). İki işaret birden aranır:
# tek dosya (kopyalanmış bir CLAUDE.core.md) bir projeyi yanlışlıkla "core" saydırıp
# meşru proje yazımlarını bloklardı.
_CORE_ISARETLERI = ("CLAUDE.core.md", "claude/kesin-yasaklar.canonical.md")
_CORE_ARAMA_DERINLIGI = 12          # ata-dizin taraması üst sınırı (patolojik yol koruması)


def _core_deposu_mu(dizin: Path) -> bool:
    try:
        return all((dizin / isaret).exists() for isaret in _CORE_ISARETLERI)
    except Exception:
        return False


def _core_hedef_mi(dosya: str) -> bool:
    """Hedef core deposunda mı? (yol-dizgesi hızlı yolu + işaret-dosyası ekseni)

    ⚠ İKİ YANLIŞ-POZİTİF FRENİ — ikisi de ÖLÇÜLDÜ (2026-08-01 PR #75 CI kırmızısı;
    konformans ④ "core DIŞI hedef taranmaz" vakası `template_project` ekseninde düştü):

    ① **MUTLAKLAŞTIRMA.** Göreli yolun `parents`'ı `..` ve `.` ile biter; `.` = ÇALIŞMA
       DİZİNİ, yani core checkout'unun ta kendisi. Konformans hedefi `docs/x.md` (göreli)
       + `--project ../template_project` (göreli) verince tırmanış komşu projeden çıkıp
       **core'un kendi köküne** varıyor ve proje dosyası "core" sanılıyordu. Ölçüm:
       `parents = ['..\\_tp_probe\\docs', '..\\_tp_probe', '..', '.']` → sonuncusu
       `C:\\IX\\_wt\\guard` (işaretli) → True. Yol ÖNCE mutlaklaştırılır.
    ② **DEPO SINIRI.** Mutlak yolda bile tırmanış komşu/üst bir depoya girebilir. Hedefin
       KENDİ deposunun kökünde durulur: bir dizinde `.git` varsa (worktree'de `.git` bir
       DOSYADIR ve gerçek depoyu gösterir) orası köktür → daha yukarı BAKILMAZ.
       Sıra önemli: işaretlere ÖNCE bakılır (core'un kendi kökü de `.git` taşır), sınır
       SONRA uygulanır — tersi olsaydı AV-21 (worktree = core) geri gelirdi.
    """
    if not dosya:
        return False
    d = dosya.replace("\\", "/").lower()
    if "/core/" in d or d.startswith("core/") or "dev_core" in d:
        return True                 # hızlı yol: dosya-sistemi erişimi YOK (eski davranış aynen)
    try:
        p = Path(dosya)
        if not p.is_absolute():
            p = _PROJ_ROOT / p
        p = Path(os.path.abspath(str(p)))          # ① `.` / `..` çözülür
        for ata in list(p.parents)[:_CORE_ARAMA_DERINLIGI]:
            if _core_deposu_mu(ata):
                return True                        # core deposu (klon/worktree/junction farketmez)
            if (ata / ".git").exists():
                return False                       # ② hedefin KENDİ deposunun kökü — dur
    except Exception:
        return False                # ayrıştırılamayan yol: erken-uyarı katmanı sessiz kalır
    return False


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
        # utf-8-sig ZORUNLU: BOM'lu .conn_adt'de ilk satır ADT_SAP_URL ise `cur_url` BOŞ
        # kalır → yalnız-host farkı olan senaryoda differ=False → bu ADR-0010 gate'i
        # SESSİZCE FAIL-OPEN olur (ölçüldü 2026-08-01, AV-02 sınıfı).
        ct = conn.read_text(encoding="utf-8-sig", errors="ignore")
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


def _sozluk(x) -> dict:
    """Payload'ı güvenli sözlüğe indirger (2026-08-01 bug-avı, W2-VH-01).

    ÖLÇÜLDÜ: `json.load` sarılıydı ama SONRASI girdinin dict/str olduğunu VARSAYIYORDU.
    10 bozuk payload'ın **6'sında** uncaught `AttributeError` → exit 1 + traceback
    (`null`, `[]`, `"str"`, `42`, `tool_name:123`, `file_path:123`). Sözleşme exit **2**
    = blok olduğu için exit 1 "blokladı" DEĞİLDİR: guard'ın 9 kuralı da o çağrıda
    devre dışı kalır. Kontrol grubu aynı koşumda sağlamdı (hedefsiz `gh` → exit 2,
    `ls` → exit 0) ve `config_change_guard` 10/10 bozuk girdide ÇÖKMEDİ — yani bu bir
    ortam artefaktı değil, savunmasız giriş işlemesiydi.

    Politika: çözülemeyen/şekilsiz girdi = **inceleyecek bir şey yok** → kurallar boş
    girdi görür ve serbest bırakır. Bu, `json.load` hatasındaki mevcut `return 0`
    politikasıyla TUTARLIDIR; şekilsiz payload'da bloklamak harness tuhaflığında
    oturumu kilitlerdi. Asıl kazanç: ÇÖKME yok → diğer alanlar hâlâ denetlenir
    (ör. `file_path` bozuk ama `command` geçerliyse komut yine taranır).
    """
    return x if isinstance(x, dict) else {}


def _metin(x) -> str:
    """Alanı güvenli metne indirger — sayı/None/liste gelirse çökmek yerine taranabilir kıl."""
    if isinstance(x, str):
        return x
    if x is None or isinstance(x, (dict, list)):
        return ""
    return str(x)


def _parse_fail_notu() -> None:
    """Parse-fail dalinin SESSIZLIGINI kaldirir; exit 0 fail-safe'i AYNEN korunur.

    Gerekce + sinif kaydi: scripts/hooks/README.md S4. ASCII-only yazilir (stderr'in
    utf-8 sarmalayicisi bu dosyada win32'ye kosulludur). Yazma hatasi fail-safe'i
    BOZMAMALI -> except: pass.
    """
    try:
        sys.stderr.write(
            "[pre_tool_guard] GIRDI-PARSE-EDILEMEDI: stdin JSON okunamadi -> fail-safe "
            "SERBEST (exit 0); KARAR DEGILDIR (girdi hic okunamadi). "
            "Negatif-test: governance/infra-test-recipes.md B0b\n")
    except Exception:
        pass


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        _parse_fail_notu()
        return 0
    data = _sozluk(data)

    tool_name = _metin(data.get("tool_name", ""))

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

    ti_ham = data.get("tool_input", {})
    ti = _sozluk(ti_ham)
    if ti:
        ham = _metin(ti.get("command", "")) or json.dumps(ti, ensure_ascii=False)
    else:
        # dict DEĞİL (liste/str/sayı/None): metne indir, yine de tara — çökme YOK.
        ham = "" if ti_ham is None else _metin(ti_ham) or json.dumps(ti_ham, ensure_ascii=False, default=str)

    komut = _komut_govdesi(ham) if tool_name in _KABUK_TOOLLARI else ham

    dosya_hedefi = _metin(ti.get("file_path", "")) or _metin(ti.get("notebook_path", ""))

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
        lehce = "ps" if tool_name == "PowerShell" else "bash"
        _GORUNURLUK.clear()
        belirsiz = _lehce_ile(lehce, _gh_hedef_belirsiz, komut)
        if belirsiz:
            sys.stderr.write(
                f"⛔ GH HEDEF BELİRSİZ: {belirsiz}\n"
                "Bu kural repoyu DEĞİŞTİREN her `gh` alt-komutunda geçerlidir "
                "(pr/issue/release/repo/secret/variable/workflow/ruleset/label/api). "
                "Okuma komutları (list/view/status) serbesttir. İŞLEM REDDEDİLDİ.\n")
            return 2

        sorun = _iki_lehce(lehce, _gh_pr_public_leak, komut, ham)
        if sorun:
            sys.stderr.write(
                f"⛔ PUBLIC-PR SIZINTI GATE: {sorun}\n"
                "PR başlığı/gövdesi PUBLIC repoya yayınlanır ve cache'lenir — silmek geri "
                "ALMAZ. core_precommit yalnız commit içeriğini tarar; PR gövdesi commit "
                "DEĞİLDİR. İŞLEM REDDEDİLDİ. Çözüm: gövdeyi genericize et, tekrar dene.\n")
            return 2

        sorun = _iki_lehce(lehce, _git_commit_public_leak, komut, ham)
        if sorun:
            sys.stderr.write(
                f"⛔ COMMIT-MESAJI SIZINTI GATE: {sorun}\n"
                "Commit MESAJI push ile PUBLIC repoya gider ve GitHub'da KALICIDIR. "
                "core_precommit commit'in İÇERİĞİNİ (dosyaları) tarar — MESAJINI TARAMAZ; "
                "PR gate'i de yalnız `gh` yayın komutlarına bakar. Arada kalan bu yol "
                "2026-07-28'de fiilen sızdırdı. İŞLEM REDDEDİLDİ.\n"
                "Çözüm: mesajı genericize et, tekrar dene. Zaten commit'lediysen ve HENÜZ "
                "PUSH ETMEDİYSEN: `git commit --amend` ile mesajı düzelt.\n")
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
        # kaçınılmaz olarak "eşleşirler". Bu liste 2026-07-10'da `core_precommit`in
        # `SCAN_EXEMPT`iyle eş kurulmuştu (burada YOKTU → guard kendi düzeltmesini
        # blokluyordu). ⚠ Q329'dan beri EŞ DEĞİL: `core_precommit` tarafı satır-bazlı
        # gerekçeli muafiyete geçti, bu dal dosya-bazlı kaldı (bkz. `_DESEN_TANIMLAYAN`).
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
