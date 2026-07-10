# -*- coding: utf-8 -*-
"""inspector.py — v1: davranış katmanının GERÇEKTEN canlı olduğunu KANITLA (rapor-only).

NEDEN VAR (2026-07-10, iki günlük denetimin çıktısı):
Bizi yakan arıza sınıfı "kod yanlış" değil, **"kod doğru ama hiç çalışmadı"**:
  · `AGENTS.md` aylarca yüklenmiyordu — ekran teyidi her oturum "yüklendi" diyordu.
  · `.claude/rules/*` `globs:` yazıyordu; Claude Code `paths:` okur → kural tembel değil,
    sessizce KOŞULSUZ yükleniyordu. Hata mesajı yok.
  · `pre_tool_guard` kodu PowerShell'i tanıyordu ama `settings.json` matcher'ı yalnız `Bash`'ti
    → PowerShell'den geçen komut hiç guard görmedi. Canlı A/B ile kanıtlandı.
  · `pre-commit.template` var olmayan bir gate'i "Gate:" diye anıyordu.
  · `InstructionsLoaded` logger'ı yanlış payload anahtarları arıyordu → log `?  ?` yazıp
    "ölçüyoruz" hissi veriyordu.

Bu beşinin ortak yanı: **diskte hiçbir şey "yanlış" görünmüyordu.** Üstelik transcript de
yardımcı olmuyor — Claude Code yalnız KONUŞAN hook'u kaydeder (`hook_success`,
`hook_additional_context`, `hook_blocking_error`). Sessizce izin veren `pre_tool_guard`'ın
tek bir kaydı yoktur. Yani "koştu ve izin verdi" ile "hiç koşmadı" **ayırt edilemez**.

⚠ BU BOŞLUK v1'de KAPATILMADI ve bilerek kapatılmadı. `hook_shim`'e bir heartbeat eklemek
düşünüldü (tool adını yazabilmesi için stdin'i okuyup gerçek hook'a geri enjekte etmesi
gerekirdi). `hook_shim` 16 hook'un tek geçiş noktasıdır ve içlerinde `pre_tool_guard` vardır:
re-enjeksiyondaki ince bir hata hook'ları payload'sız bırakır, payload'sız bir guard ise
büyük ihtimalle SESSİZCE İZİN VERİR. Gözlemlenebilirlik için tüm guard katmanını riske atmak
kötü bir takastır. Dolayısıyla Inspector, "guard fiilen koştu mu" sorusuna ✓ değil
**ÖLÇÜLEMEZ** der. Ölçülemeyene ✓ koymak, bu aletin var oluş sebebini çiğner.

TASARIM İLKELERİ (ihlal etme):
  1. **Rapor-only.** Hiçbir şeyi bloklamaz, hiçbir şeyi düzeltmez. Exit daima 0
     (yalnız `--self-test` başarısızlığı hariç: o zaman ALETİN kendisi bozuktur).
  2. **Geçerse SESSİZ.** Yanlış-pozitif üreten uyarı, uyarıya karşı bağışıklık yaratır
     (2026-07-10: D7 her oturum bir yorum farkı için "SAPMIS" diye bağırıyordu).
  3. **Asla çıplak ✓ basma.** Her rapor kapsam kesri taşır. "Inspector OK dedi" cümlesi
     yeni "activated" olmasın.
  4. **Çoğaltma yok.** Orphan validator kapsamını `check_rule_gate_coverage.py` zaten
     zorluyor → burada TEKRARLANMAZ.
  5. **Varsayma, KAYDET.** `InstructionsLoaded`'ın oturum-başında hangi dosyalar için
     ateşlendiği DOĞRULANMADI (5 dosya yüklenirken 2 olay gözlendi; sebebi kaynakta
     bulunamadı). Bu yüzden A-katmanı önce `.tmp/inspector-baseline.json`'a gerçeği
     yazar, sonra ona karşı SAPMA arar. Sayı iddiası UYDURULMAZ.
  6. **Kendini denetle.** `--self-test` kasten bozuk bir fixture kurar; iddialar orada
     FAIL vermezse KOŞUCU BOZUKTUR ve bu gürültülü biter.

ZAMANLAMA (ölçüldü): `session_start` hook'u 14:50:51'de koşuyor, `InstructionsLoaded`
olayları 14:50:53'te düşüyor. Yani oturum-başı denetçi KENDİ oturumunun yükleme kanıtını
göremez → daima ÖNCEKİ oturumun izini denetler.

Kullanım:
    python core/scripts/inspector.py                 # rapor (bulgu yoksa sessiz)
    python core/scripts/inspector.py --self-test     # canary: aletin kendisi çalışıyor mu
    python core/scripts/inspector.py --json          # makine-okunur
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

# ── Sabitler ────────────────────────────────────────────────────────────────────
# `Gate:` beyanı YALNIZ satır başında (yorum işaretinden sonra) aranır. Aksi hâlde
# "burada 'Gate: X' yazıyordu" gibi TARİHSEL açıklamalar yanlış-pozitif üretir.
GATE_BEYANI = re.compile(r"^\s*#?\s*Gate:\s*(check_\w+\.py)", re.MULTILINE)
FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
JUNCTION_ADLARI = ("agents", "skills", "commands", "rules")
GUARD_TOOL_KABUKLARI = ("Bash", "PowerShell")


class Bulgu:
    def __init__(self, kod: str, mesaj: str, kanit: str = "") -> None:
        self.kod, self.mesaj, self.kanit = kod, mesaj, kanit

    def __str__(self) -> str:
        return f"[{self.kod}] {self.mesaj}" + (f"\n      kanıt: {self.kanit}" if self.kanit else "")


def _oku(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _settings_hooklari(proj: Path) -> list[tuple[str, str, str]]:
    """(olay, matcher, hook_adi) üçlüleri. hook_adi = args'ın son elemanı."""
    try:
        d = json.loads(_oku(proj / ".claude" / "settings.json"))
    except Exception:
        return []
    out = []
    for olay, bloklar in (d.get("hooks") or {}).items():
        if olay.startswith("_"):
            continue
        for b in bloklar if isinstance(bloklar, list) else []:
            matcher = b.get("matcher", "*")
            for h in b.get("hooks", []):
                args = h.get("args") or []
                if args:
                    out.append((olay, matcher, str(args[-1])))
    return out


# ── B KATMANI — kablolama (statik, bu oturum) ───────────────────────────────────

def b1_hayalet_hook(proj: Path, core: Path) -> list[Bulgu]:
    """settings.json'da adı geçen her hook'un script'i diskte var mı?"""
    b = []
    for olay, _m, ad in _settings_hooklari(proj):
        if not (core / "scripts" / "hooks" / f"{ad}.py").is_file():
            b.append(Bulgu("B1", f"HAYALET HOOK: settings.json `{olay}` → `{ad}` script'i YOK",
                           f"beklenen: core/scripts/hooks/{ad}.py"))
    return b


def b2_hayalet_gate(proj: Path, core: Path) -> list[Bulgu]:
    """Dokümanlarda `Gate: check_x.py` diye BEYAN edilen her dosya diskte var mı?

    2026-07-10: `pre-commit.template` `check_project_precommit_wired.py`'yi anıyordu;
    o dosya hiç var olmadı. Var olmayan gate'i anmak, koruma var sandırır.
    """
    b = []
    kokler = [core / "claude", core / "scripts", core / "playbook", core / "standards",
              proj / "governance", proj / "scripts"]
    for kok in kokler:
        if not kok.is_dir():
            continue
        for f in kok.rglob("*"):
            if not f.is_file() or f.suffix.lower() not in (".md", ".py", ".template", ".yml", ""):
                continue
            if "__pycache__" in f.parts:
                continue
            for ad in GATE_BEYANI.findall(_oku(f)):
                varmi = any((core / "scripts" / alt / ad).is_file()
                            for alt in ("validators", "hooks", "")) or \
                        (proj / "scripts" / "validators-local" / ad).is_file()
                if not varmi:
                    b.append(Bulgu("B2", f"HAYALET GATE: `{ad}` beyan edilmiş ama diskte YOK",
                                   f"{f.relative_to(f.anchor)}"))
    return b


def b3_guard_kabuk_kapsami(proj: Path) -> list[Bulgu]:
    """pre_tool_guard'ın PreToolUse matcher'ı hem Bash hem PowerShell'i kapsıyor mu?

    2026-07-09: guard KODU iki kabuğu da tanıyordu ama matcher yalnız `Bash`'ti →
    Bash'te bloklanan komut PowerShell'den GEÇİYORDU (canlı A/B ile kanıtlandı).
    Kod-seviyesi koruma, kablolanmadan koruma sanılır.
    """
    matcherlar = [m for (olay, m, ad) in _settings_hooklari(proj)
                  if olay == "PreToolUse" and ad == "pre_tool_guard"]
    if not matcherlar:
        return [Bulgu("B3", "pre_tool_guard PreToolUse'a KABLOLU DEĞİL", "settings.json")]
    birlesik = " ".join(matcherlar)
    eksik = [k for k in GUARD_TOOL_KABUKLARI if k not in birlesik]
    if eksik:
        return [Bulgu("B3", f"GUARD KABUK BOŞLUĞU: matcher {eksik} içermiyor → o kabuktan geçen komut guard görmez",
                      f"matcher(lar): {matcherlar}")]
    return []


def b4_rules_frontmatter(core: Path) -> list[Bulgu]:
    """`.claude/rules/*.md` frontmatter anahtarı `paths:` mi?

    2026-07-10: `globs:` yazıyordu. Claude Code 2.1.206 parser'ı (`SQh()`) yalnız `paths`
    okur → kural "koşulsuz" kovasına düşer ve HER OTURUM yüklenir; tembel yükleme hiç
    çalışmaz, hata da vermez.
    """
    b = []
    rd = core / "claude" / "rules"
    for f in sorted(rd.glob("*.md")) if rd.is_dir() else []:
        m = FRONTMATTER.match(_oku(f))
        fm = m.group(1) if m else ""
        if re.search(r"^\s*globs\s*:", fm, re.MULTILINE):
            b.append(Bulgu("B4", f"KURAL SESSİZCE KOŞULSUZ: `{f.name}` frontmatter'ı `globs:` kullanıyor",
                           "Claude Code yalnız `paths:` okur → kural her oturum yüklenir"))
        elif not re.search(r"^\s*paths\s*:", fm, re.MULTILINE):
            b.append(Bulgu("B4", f"KURAL KOŞULSUZ (frontmatter'sız): `{f.name}`",
                           "bilinçliyse sorun yok; değilse `paths:` ekle"))
    return b


def _hash16(p: Path) -> str:
    import hashlib
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    except Exception:
        return ""


def b5_core_baglantisi(proj: Path, core: Path) -> list[Bulgu]:
    """`.claude/{agents,skills,commands,rules}` core'a bağlı mı — ve overlay BAYAT mı?

    İki meşru biçim vardır:
      · symlink/junction → doğrudan core'u gösterir (drift imkânsız).
      · OVERLAY (`.overlay-manifest.json`) → proje bir dosyayı override ettiği için
        dizin materyalize edilmiştir (ör. proje-lokal `backend-expert`). Bu KASITLIDIR.

    Overlay'in bedeli kopyadır → bayatlar. Manifest her dosyanın `core_hash`'ini saklar.
    Burada iki sapma aranır: (a) core dosyası değişmiş, overlay kopyası eski;
    (b) core'a YENİ dosya eklenmiş, overlay'de hiç yok (sessizce eksik ajan/skill).
    """
    b = []
    for ad in JUNCTION_ADLARI:
        p = proj / ".claude" / ad
        core_d = core / "claude" / ad
        if not p.exists():
            b.append(Bulgu("B5", f"`.claude/{ad}` YOK", "python core/scripts/team_setup.py --repair-junctions"))
            continue
        if Path(os.path.realpath(p)) == Path(os.path.realpath(core_d)):
            continue  # symlink/junction — en güvenli biçim

        manifest = p / ".overlay-manifest.json"
        if not manifest.is_file():
            b.append(Bulgu("B5", f"`.claude/{ad}` ne junction ne overlay — gerçek klasör (sızıntı riski)",
                           f"gerçek: {os.path.realpath(p)}"))
            continue
        try:
            m = json.loads(_oku(manifest)).get("dosyalar", {})
        except Exception:
            b.append(Bulgu("B5", f"`.claude/{ad}` overlay manifest'i OKUNAMADI", str(manifest)))
            continue

        for dosya, meta in m.items():
            if meta.get("kaynak") != "core":
                continue  # proje override'ı — bilinçli, hash kıyaslanmaz
            simdiki = _hash16(core_d / dosya)
            if not simdiki:
                b.append(Bulgu("B5", f"overlay `{ad}/{dosya}` core'da ARTIK YOK", "silinmiş mi?"))
            elif simdiki != meta.get("core_hash"):
                b.append(Bulgu("B5", f"OVERLAY BAYAT: `{ad}/{dosya}` core'da değişti, kopya eski",
                               f"core={simdiki} manifest={meta.get('core_hash')} → team_setup.py"))
        if core_d.is_dir():
            eksik = [f.name for f in core_d.glob("*.md") if f.name not in m]
            if eksik:
                b.append(Bulgu("B5", f"OVERLAY EKSİK: core'daki {len(eksik)} dosya `.claude/{ad}`'de yok",
                               ", ".join(eksik[:4])))
    return b


# ── A KATMANI — canlılık (ÖNCEKİ oturumun izi) ──────────────────────────────────

def _log_satirlari(proj: Path) -> list[dict]:
    out = []
    for satir in _oku(proj / ".tmp" / "instructions-loaded.log").splitlines():
        p = satir.rstrip("\r").split("\t")
        if len(p) >= 4:
            out.append({"ts": p[0], "reason": p[1], "type": p[2], "path": p[3],
                        "ek": "\t".join(p[4:])})
        elif len(p) >= 2:
            out.append({"ts": p[0], "reason": p[1], "type": "?", "path": "?", "ek": ""})
    return out


def a1_logger_canli(proj: Path, satirlar: list[dict]) -> list[Bulgu]:
    if not (proj / ".tmp" / "instructions-loaded.log").exists():
        return [Bulgu("A1", "InstructionsLoaded log'u YOK — hook hiç ateşlenmemiş olabilir",
                      ".tmp/instructions-loaded.log")]
    if not satirlar:
        return [Bulgu("A1", "InstructionsLoaded log'u BOŞ — talimat yüklemesi izlenmiyor",
                      "hook kablolu mu? (settings.json → InstructionsLoaded)")]
    return []


def a2_sema_degismedi(satirlar: list[dict]) -> list[Bulgu]:
    """Logger'ın payload şeması hâlâ tanıdık mı?

    Claude Code sürüm yükseltmesi alan adlarını değiştirirse logger SESSİZCE körleşir.
    Onarılmış logger bu durumda `SEMA-DEGISTI` yazar — o satır varsa alet kör demektir.
    """
    bozuk = [s for s in satirlar if s["reason"] in ("SEMA-DEGISTI", "?")]
    if bozuk:
        return [Bulgu("A2", f"PAYLOAD ŞEMASI DEĞİŞMİŞ ({len(bozuk)} satır) — logger KÖR",
                      f"örnek: {bozuk[0]['ts']} {bozuk[0]['reason']} {bozuk[0].get('ek','')[:120]}")]
    return []


def _kural_desenleri(core: Path) -> dict[str, list[str]]:
    """kural dosyası → paths desenleri (yalnız `paths:` olanlar tembeldir)."""
    out: dict[str, list[str]] = {}
    rd = core / "claude" / "rules"
    for f in sorted(rd.glob("*.md")) if rd.is_dir() else []:
        m = FRONTMATTER.match(_oku(f))
        if not m:
            continue
        mm = re.search(r"^\s*paths\s*:\s*(.+)$", m.group(1), re.MULTILINE)
        if mm:
            out[f.name] = [x.strip() for x in mm.group(1).split(",") if x.strip()]
    return out


def a3_tembel_yukleme(core: Path, satirlar: list[dict], okunanlar: list[str]) -> list[Bulgu]:
    """`paths:`li bir kural, eşleşen dosya okunduğunda GERÇEKTEN yüklendi mi?

    Beklenen kanıt: log'da `path_glob_match  Project  .../<kural>.md`.
    Eşleşen dosya hiç okunmadıysa iddia KURULAMAZ → sessiz kal (UNKNOWN, bulgu değil).
    """
    desenler = _kural_desenleri(core)
    if not desenler or not okunanlar:
        return []
    b = []
    for ad, patlar in desenler.items():
        eslesen = [y for y in okunanlar
                   if any(fnmatch.fnmatch(y.replace("\\", "/"), p) or
                          fnmatch.fnmatch(Path(y).name, Path(p).name) for p in patlar)]
        if not eslesen:
            continue
        goruldu = any(s["reason"] == "path_glob_match" and s["path"].endswith(ad) for s in satirlar)
        if not goruldu:
            b.append(Bulgu("A3", f"TEMBEL YÜKLEME ÖLÜ: `{ad}` eşleşen dosya okundu ama yüklenmedi",
                           f"okunan: {eslesen[0]}  · beklenen log: path_glob_match … {ad}"))
    return b


def a4_baseline(proj: Path, satirlar: list[dict]) -> list[Bulgu]:
    """Oturum-başı yükleme kümesi baseline'dan SAPTI mı?

    ⚠ `InstructionsLoaded`'ın oturum başında hangi dosyalar için ateşlendiği DOĞRULANMADI
    (2026-07-10: 5 talimat dosyası yüklenirken 2 olay gözlendi; sebep kaynakta bulunamadı).
    Bu yüzden burada SAYI İDDİA EDİLMEZ: ilk koşu gerçeği kaydeder, sonrakiler sapma arar.
    """
    yol = proj / ".tmp" / "inspector-baseline.json"
    simdiki = sorted({s["path"] for s in satirlar if s["reason"] == "session_start"})
    if not simdiki:
        return []
    if not yol.exists():
        try:
            yol.parent.mkdir(parents=True, exist_ok=True)
            yol.write_text(json.dumps({"session_start_yollari": simdiki}, ensure_ascii=False, indent=1),
                           encoding="utf-8")
        except Exception:
            pass
        return [Bulgu("A4", f"BASELINE KAYDEDİLDİ ({len(simdiki)} dosya) — bulgu değil, ilk koşu",
                      "sonraki koşular bu kümeden sapmayı arar")]
    try:
        onceki = json.loads(_oku(yol)).get("session_start_yollari", [])
    except Exception:
        return []
    kayip = [x for x in onceki if x not in simdiki]
    if kayip:
        return [Bulgu("A4", f"TALİMAT DOSYASI ARTIK YÜKLENMİYOR: {len(kayip)} adet",
                      "; ".join(kayip[:3]))]
    return []


# ── Transcript — önceki oturumda hangi dosyalar okundu ──────────────────────────

def _onceki_transcript(proj: Path, bu_oturum: str | None) -> Path | None:
    kok = Path.home() / ".claude" / "projects"
    if not kok.is_dir():
        return None
    slug = str(proj).replace(":", "-").replace("\\", "-").replace("/", "-")
    d = kok / slug
    if not d.is_dir():
        adaylar = [x for x in kok.iterdir() if x.is_dir() and proj.name.lower() in x.name.lower()]
        if not adaylar:
            return None
        d = adaylar[0]
    dosyalar = [f for f in d.glob("*.jsonl") if not (bu_oturum and f.stem == bu_oturum)]
    return max(dosyalar, key=lambda f: f.stat().st_mtime, default=None)


def _okunan_dosyalar(tr: Path | None) -> list[str]:
    if not tr or not tr.is_file():
        return []
    out: list[str] = []
    try:
        with tr.open(encoding="utf-8", errors="replace") as fh:
            for satir in fh:
                if '"Read"' not in satir and "file_path" not in satir:
                    continue
                for m in re.finditer(r'"file_path"\s*:\s*"([^"]+)"', satir):
                    out.append(m.group(1))
    except Exception:
        return []
    return out


# ── Canary — aletin kendisi çalışıyor mu ────────────────────────────────────────

def self_test() -> int:
    """Kasten bozuk fixture: iddialar burada FAIL vermezse KOŞUCU BOZUKTUR."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        proj, core = Path(td) / "proj", Path(td) / "core"
        (proj / ".claude").mkdir(parents=True)
        (core / "claude" / "rules").mkdir(parents=True)
        (core / "scripts" / "hooks").mkdir(parents=True)
        (proj / ".claude" / "settings.json").write_text(json.dumps({"hooks": {
            "PreToolUse": [
                {"matcher": "Bash", "hooks": [{"args": ["shim.py", "pre_tool_guard"]}]},
                {"matcher": "Edit", "hooks": [{"args": ["shim.py", "yok_boyle_bir_hook"]}]},
            ]}}), encoding="utf-8")
        (core / "claude" / "rules" / "kotu.md").write_text("---\nglobs: **/*.abap\n---\n", encoding="utf-8")
        (core / "claude" / "git-hooks").mkdir(parents=True)
        (core / "claude" / "git-hooks" / "x.template").write_text("# Gate: check_olmayan_gate.py\n", encoding="utf-8")

        beklenen = {
            "B1": b1_hayalet_hook(proj, core),      # yok_boyle_bir_hook
            "B2": b2_hayalet_gate(proj, core),      # check_olmayan_gate.py
            "B3": b3_guard_kabuk_kapsami(proj),     # matcher'da PowerShell yok
            "B4": b4_rules_frontmatter(core),       # globs:
            "B5": b5_core_baglantisi(proj, core),    # .claude/agents hic yok
        }
        kacan = [k for k, v in beklenen.items() if not v]
        if kacan:
            print("⛔ CANARY BAŞARISIZ — Inspector KÖR. Bozuk fixture'da FAIL vermeyen iddialar: "
                  + ", ".join(kacan), file=sys.stderr)
            return 1
        print(f"[OK] canary: {len(beklenen)} iddianın hepsi bozuk fixture'da FAIL verdi (alet çalışıyor)")
        return 0


# ── Giriş noktası ───────────────────────────────────────────────────────────────

def denetle(proj: Path, core: Path, oturum: str | None = None) -> tuple[list[Bulgu], dict]:
    satirlar = _log_satirlari(proj)
    okunanlar = _okunan_dosyalar(_onceki_transcript(proj, oturum))

    bulgular: list[Bulgu] = []
    bulgular += b1_hayalet_hook(proj, core)
    bulgular += b2_hayalet_gate(proj, core)
    bulgular += b3_guard_kabuk_kapsami(proj)
    bulgular += b4_rules_frontmatter(core)
    bulgular += b5_core_baglantisi(proj, core)
    bulgular += a1_logger_canli(proj, satirlar)
    if satirlar:
        bulgular += a2_sema_degismedi(satirlar)
        bulgular += a3_tembel_yukleme(core, satirlar, okunanlar)
        bulgular += a4_baseline(proj, satirlar)

    gate_sayisi = len(list((core / "scripts" / "validators").glob("check_*.py")))
    istat = {"iddia_A": 4, "iddia_B": 5, "gate_toplam": gate_sayisi, "negatif_testli_gate": 0,
             "onceki_oturum_okunan_dosya": len(okunanlar), "log_satiri": len(satirlar)}
    return bulgular, istat


def kesir_metni(istat: dict) -> str:
    """ASLA çıplak ✓ basma — kapsam her raporda görünür."""
    return (f"iddia: A={istat['iddia_A']} · B={istat['iddia_B']} · "
            f"negatif-testli gate: {istat['negatif_testli_gate']}/{istat['gate_toplam']} (v2 bekliyor)")


def rapor_yaz(proj: Path, bulgular: list[Bulgu], istat: dict) -> None:
    """Bulguları `.tmp/inspector-report.md`'ye yaz. Çağıran "detay şurada" diyorsa dosya VAR olmalı."""
    if not bulgular:
        return
    govde = ["# Inspector v1 — bulgular", "", kesir_metni(istat), ""] + [f"- {b}" for b in bulgular]
    try:
        (proj / ".tmp").mkdir(parents=True, exist_ok=True)
        (proj / ".tmp" / "inspector-report.md").write_text("\n".join(govde) + "\n", encoding="utf-8")
    except Exception:
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Inspector v1 — davranış katmanı canlılık denetimi (rapor-only)")
    ap.add_argument("--self-test", action="store_true", help="canary: aletin kendisi çalışıyor mu")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--session-id", default=None)
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    core = proj / "core"
    if not core.is_dir():
        return 0  # junction yok → session_start zaten bağırıyor; burada gürültü yapma

    bulgular, istat = denetle(proj, core, a.session_id)

    if a.json:
        print(json.dumps({"bulgular": [{"kod": b.kod, "mesaj": b.mesaj, "kanit": b.kanit} for b in bulgular],
                          "istat": istat}, ensure_ascii=False, indent=1))
        return 0

    if not bulgular:
        return 0  # SESSİZ — geçerse konuşma

    rapor_yaz(proj, bulgular, istat)
    for b in bulgular:
        print(str(b))
    print(kesir_metni(istat))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
