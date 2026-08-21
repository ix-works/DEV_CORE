#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ENFORCES: C-INFRA-01  (ADR 0019 coverage binding)
"""PreToolUse (matcher: Edit|Write|MultiEdit) — İNFRA YÜZEYİNE DOĞRUDAN YAZIM BLOĞU.

KURAL (kullanıcı talimatı 2026-08-19): infra işi (hook · validator · gate · pre-commit ·
MCP script · paylaşılan `core/scripts` aracı) — yaratma da değiştirme de — kullanıcıdan
**AYRI ve AÇIK** onay ister; onay başka bir onayın içine gömülemez; **lider infra'yı pas
geçip kendisi yapamaz**. Gerekçe kullanıcının kendi cümlesi: bu dosyalar *"senin ve
ajanlarının çalışmalarını organize eden"* katmandır — yanlış bir teşhis burada kalıcılaşır.

NEDEN RUNTIME BLOK (ADR 0019 merdiveni — "geri alınamaz VE sessiz"):
  * Geri alınamayan şey dosyanın BAYTLARI değil (git geri alır) — **onay ANI**dır. Yazım
    başladıktan sonra "önce sorulmalıydı" telafi edilemez; teşhis yanlışsa iş zaten yapılmıştır.
  * Sessizdir: bugüne kadar hiçbir yüzey "bunu sen mi yapıyorsun?" diye sormuyordu;
    statik ikizi (pre-commit/CI) yalnız COMMIT anında konuşur — o an iş bitmiştir.
  * PATTERN #30 (2026-08-17): kullanıcı mesajına/hafızaya bağlı hatırlatıcı TUR-İÇİ
    davranışı korumaz. Kuralı hatırlatan şey KONUMDUR.
Kardeş katman: `post_validate` `infra-express` dalı AYNI yüzeyde oturumda bir kez
"EXPRESS mi kuyruk mu?" diye sorar ama BLOKLAMAZ ve yazımdan SONRA konuşur.

YAZAN KİM? — ÖLÇÜLDÜ (2026-08-19, `claude -p` + stdin-döken sonda hook, 2 koşum):
  * ana oturum (lider) payload'ında `agent_type`/`agent_id` anahtarları **YOK**;
  * alt-ajan payload'ında **İKİSİ DE VAR** ve `agent_type` = ajan tanımının `name:`i
    (sonda: özel `infra-expert` tanımı → `agent_type == "infra-expert"`).
  * PreToolUse hook'ları alt-ajan araç çağrılarında da ATEŞLER (aynı sonda ile ölçüldü) —
    yani kimlik ayrımı YAPILMASAYDI bu guard infra-expert'i de bloklar, işlevsiz olurdu.
Ayrım bu yüzden YOL'a değil KİMLİĞE dayanır: infra-expert'in worktree'si de, canlı core da
aynı sınıftır; muafiyeti veren şey ÇALIŞMA YERİ değil KİM olduğudur.

MUAF (sessiz geç, exit 0):
  * `agent_type` ∈ MUAF_AJANLAR (infra-expert) — üretim zaten onun görevi.
  * Korunan sınıfa girmeyen her yol: `governance/**` (özellikle `infra-findings.md` —
    KAYIT yazmak serbest ve teşviklidir), `docs/`, `playbook/`, `standards/`,
    `SOURCE_CODES/**`, paket `.rules.md`, `tests/`, `attic/`, `TempScripts/`, `.tmp/`.
  * Okuma: guard yalnız Edit/Write/MultiEdit yüzeyindedir; Read/Grep/Glob DOKUNULMAZ.

KAPSAM SINIRI (bilerek): kabuk üzerinden yazım (`Bash` ile `sed -i`/heredoc redirect)
KAPSANMAZ. Fiil-kara-listesi bu evde bir kez denendi ve 6 yoldan sızdı (pre_tool_guard
R10 FREEZE-GUARD, 2026-07-10 kaldırma gerekçesi). Kanıtsız ikinci deneme yapılmadı;
boşluk raporda AÇIK KALEM olarak durur.

⛔ BYPASS BAYRAĞI YOKTUR (bilinçli): bayrak kuralı anlamsızlaştırır. Çıkış yolu tek:
kullanıcıdan AYRI ve AÇIK onay istemek.
⭐ ÖNYÜKLEME PARADOKSU kabul: bu dosyanın kendisi de korunan sınıftadır; bir sonraki
değişikliği de ayrı onay ister. Doğru davranış budur.

Test: tests/fixtures/infra_write_guard/run.py (+ `--mutasyon-blok`, `--mutasyon-cokme`)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

# Core deposunun KİMLİĞİ ada/yol-dizgesine değil İŞARET DOSYASINA bakar (AV-21, 2026-08-01:
# `git worktree`/farklı adlı klonda ad-tabanlı tanıma SESSİZCE kapanıyordu).
_CORE_ISARETLERI = ("CLAUDE.core.md", "claude/kesin-yasaklar.canonical.md")
_ARAMA_DERINLIGI = 12               # ata-dizin taraması üst sınırı (patolojik yol koruması)

# Bu sınıfa giren yollar İNFRA KARARI DEĞİLDİR: fixture/arşiv/scratch/derleme artığı.
_HARIC = re.compile(r"/(tests|attic|TempScripts|__pycache__|\.tmp)/", re.IGNORECASE)

# `scripts/**` altındaki DOKÜMAN korunmaz: `scripts/hooks/README.md` hook ENVANTERİNİ
# ANLATIR, davranış TAŞIMAZ (kablolama `settings.template.json`'dadır) — liderin envanter
# tazeliğini yazması gereken bir iştir, bloklanırsa tablo bayatlar (2026-08-13 bayatlığı).
# ⚠ Muafiyet YALNIZ `scripts/` altındadır: `claude/rules/*.md` bir DAVRANIŞ yüzeyidir ve
# korunur (aşağıdaki S9/B9 vektör çifti bu ayrımı çiviler).
_DOKUMAN_MUAF = re.compile(r"^scripts/.+\.md$", re.IGNORECASE)

# CORE deposu içinde korunan yüzeyler (yol core köküne GÖRELİ, posix).
_KORUNAN_CORE = (
    (re.compile(r"^scripts/hooks/"), "hook"),
    (re.compile(r"^scripts/validators/"), "validator"),
    (re.compile(r"^scripts/git-hooks/"), "pre-commit / git-hook"),
    (re.compile(r"^claude/git-hooks/"), "pre-commit şablonu"),
    (re.compile(r"^claude/rules/"), "davranış kuralı (L1b)"),
    (re.compile(r"^mcp_servers/"), "MCP script"),
    (re.compile(r"^scripts/.+\.py$"), "paylaşılan core/scripts aracı"),
)

# CORE DIŞI (proje deposu) korunan yüzeyler — tam yolun SONUNA bakılır.
_KORUNAN_PROJE = (
    (re.compile(r"/scripts/validators-local/[^/]+\.py$", re.IGNORECASE), "proje-lokal validator"),
    (re.compile(r"/\.claude/hooks/", re.IGNORECASE), "proje-lokal hook"),
    (re.compile(r"/scripts/git-hooks/", re.IGNORECASE), "proje git-hook"),
    (re.compile(r"/scripts/hook_shim\.py$", re.IGNORECASE), "hook yükleyicisi (hook_shim)"),
)

# Guard'ın kendi sınıflandırıcısı çökerse kullanılan KABA ağ (fail-closed yönü). Bilerek
# aptal: tek bir alt-dizge testi; yanlış-pozitifi yanlış-negatife tercih eder.
_KABA = ("/scripts/hooks/", "/scripts/validators/", "/scripts/validators-local/",
         "/scripts/git-hooks/", "/claude/git-hooks/", "/claude/rules/", "/mcp_servers/",
         "/hook_shim.py", "/.claude/hooks/")

MUAF_AJANLAR = frozenset({"infra-expert"})

_ARACLAR = ("Edit", "Write", "MultiEdit")


def _parse_fail_notu() -> None:
    """Parse-fail dalinin SESSIZLIGINI kaldirir; exit 0 fail-safe'i AYNEN korunur.

    Sinif kaydi + gerekce: scripts/hooks/README.md S4 (14 hook'un ortak sozlesmesi).
    ASCII zorunlu (C-ENC-01) ve yazma hatasi fail-safe'i BOZMAMALI.
    """
    try:
        sys.stderr.write(
            "[infra_write_guard] GIRDI-PARSE-EDILEMEDI: stdin JSON okunamadi -> fail-safe "
            "SERBEST (exit 0); KARAR DEGILDIR (girdi hic okunamadi). "
            "Negatif-test: governance/infra-test-recipes.md B0b\n")
    except Exception:
        pass


def _core_koku(p: Path):
    """Dosyanın üstündeki ilk CORE deposu kökü (işaret dosyasıyla) ya da None."""
    for i, ana in enumerate(p.parents):
        if i >= _ARAMA_DERINLIGI:
            break
        for isaret in _CORE_ISARETLERI:
            if (ana / isaret).is_file():
                return ana
    return None


def _sinif(ham: str):
    """→ (etiket, kanit) korunan infra yüzeyi ise; değilse None. DETERMİNİSTİK."""
    norm = ham.replace("\\", "/")
    if _HARIC.search(norm):
        return None                      # fixture/arşiv/scratch: infra KARARI değil
    p = Path(ham)
    kok = _core_koku(p)
    if kok is None:
        # `<proje>/core/...` junction'ı: işaret dosyası junction'ın ardındadır ve bazı
        # kurulumlarda `is_file()` çözülmeyebilir → yol-segmenti YEDEK yol olarak kalır.
        m = re.search(r"/core/(.+)$", norm, re.IGNORECASE)
        rel = m.group(1) if m else None
    else:
        try:
            rel = p.resolve().relative_to(kok.resolve()).as_posix()
        except Exception:
            rel = None
    if rel and not _DOKUMAN_MUAF.match(rel):
        for desen, etiket in _KORUNAN_CORE:
            if desen.search(rel):
                return etiket, "core:" + rel
    for desen, etiket in _KORUNAN_PROJE:
        if desen.search(norm):
            return etiket, "proje:" + norm
    return None


def _yazan(data: dict):
    """→ ('ana-oturum', '') ya da ('alt-ajan', <agent_type>). ÖLÇÜLMÜŞ şemaya dayanır."""
    tip = data.get("agent_type")
    tip = tip.strip() if isinstance(tip, str) else ""
    kimlik = data.get("agent_id")
    kimlik = kimlik.strip() if isinstance(kimlik, str) else ""
    if not tip and not kimlik:
        return "ana-oturum", ""
    return "alt-ajan", tip


def _blok_mesaji(etiket: str, kanit: str, kim: str, tip: str) -> str:
    kimlik = "ANA OTURUM (lider)" if kim == "ana-oturum" else f"alt-ajan '{tip or '?'}'"
    return (
        f"⛔ İNFRA YAZIMI BLOKLANDI — {kimlik} korunan bir infra yüzeyine DOĞRUDAN yazıyor.\n"
        f"   Yüzey: {etiket}  ({kanit})\n"
        "KURAL (kullanıcı talimatı 2026-08-19): infra işi — hook · validator · gate · "
        "pre-commit · MCP script · paylaşılan core/scripts aracı — YARATMA da DEĞİŞTİRME de "
        "kullanıcıdan AYRI ve AÇIK onay ister. Onay BAŞKA BİR ONAYIN İÇİNE GÖMÜLEMEZ ve "
        "lider bu adımı pas geçip kendisi yapamaz.\n"
        "ÇIKIŞ YOLU (bypass bayrağı YOKTUR):\n"
        "  1) BULGUYU KAYDET — serbest ve teşvikli: governance/infra-findings.md'ye tek satır "
        "(tarih | bileşen | semptom | kontrol-grubu | sınıf | görev-bağlamı | önerilen-yön). "
        "Bu blok KAYDI değil İCRAYI durdurur; görev DEVAM eder.\n"
        "  2) KULLANICIDAN AYRI ONAY İSTE — tetikleyici + kapsam + neden şimdi + onaylamazsa "
        "ne olur + öneri.\n"
        "  3) ONAY GELİRSE üretimi TAZE bir `infra-expert` yapar (core/playbook/"
        "howto-infra-fix-proseduru.md ADIM 3: F0 geçmiş-okuma · F1 blast-radius · F2 sınıf-mı "
        "· F3 üç-bağlam + kalıcı fixture · F4 gevşetme-cetveli).\n"
        "NEDEN BLOK: bu dosyalar senin ve ajanların çalışmalarını ORGANİZE EDER; yanlış bir "
        "teşhis burada kalıcılaşır (2026-08-19 vakası: 'run_review'da DDIC görevi yok' bir "
        "boşluk sanıldı, oysa iş bölümünün parmak iziydi).\n"
        "OKUMA serbesttir; bu blok yalnız Edit/Write/MultiEdit yazımınadır.\n"
    )


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        _parse_fail_notu()
        return 0                         # sınıf sözleşmesi: fail-safe AMA sessiz DEĞİL

    if not isinstance(data, dict):
        return 0
    arac = data.get("tool_name")
    if not isinstance(arac, str) or arac not in _ARACLAR:
        return 0
    ti = data.get("tool_input")
    if not isinstance(ti, dict):
        return 0
    yol = ti.get("file_path") or ti.get("path") or ""
    if not isinstance(yol, str) or not yol:
        return 0

    kim, tip = _yazan(data)
    if kim == "alt-ajan" and tip in MUAF_AJANLAR:
        return 0                         # üretim zaten onun görevi (charter'ı ayrı sınırlar)

    try:
        vurgu = _sinif(yol)
    except Exception as exc:
        # ÇÖKME SESSİZ GEÇMEZ: kaba ağ korunan sınıfı gösteriyorsa fail-CLOSED blokla,
        # göstermiyorsa serbest bırak AMA görünür not bas (exit 1 = "çökme ≠ FAIL" tuzağı,
        # bilerek üretilmez; harness için 1 belirsizdir).
        kaba = yol.replace("\\", "/").lower()
        korunan = any(k in kaba for k in _KABA)
        sys.stderr.write(
            f"[infra_write_guard] GUARD-COKTU ({type(exc).__name__}): siniflandirici hata "
            f"verdi -> KABA AG devrede; korunan={korunan}. Bu bir KARAR DEGIL, "
            f"bozulmus guard'in fail-closed davranisidir.\n")
        if korunan:
            sys.stderr.write(_blok_mesaji("KABA-AG (siniflandirici coktu)", yol, kim, tip))
            return 2
        return 0

    if vurgu is None:
        return 0                         # korunan sınıfta değil → sessiz geç

    etiket, kanit = vurgu
    sys.stderr.write(_blok_mesaji(etiket, kanit, kim, tip))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
