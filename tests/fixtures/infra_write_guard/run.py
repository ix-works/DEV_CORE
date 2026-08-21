#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fixture — `scripts/hooks/infra_write_guard.py` (İNFRA YAZIMI ana-oturumda BLOK).

**Sınıf:** "kural VARDI ama ateşlemedi" (PATTERN #30). Kullanıcının 2026-08-19 talimatı —
infra işi AYRI ve AÇIK onay ister, lider pas geçip kendisi yapamaz — auto-memory'ye
yazıldı ama hiçbir YÜZEYE bağlı değildi; hafıza tur BAŞINDA yüklenir, tur ORTASINDA
davranışı korumaz. Bu korpus, kuralın konuma bağlandığını çivilliyor.

**Ayrımın kanıt tabanı (ölçüldü 2026-08-19, `claude -p` + stdin-döken sonda hook):**
ana oturum payload'ında `agent_type`/`agent_id` YOK; alt-ajan payload'ında İKİSİ DE VAR
ve `agent_type` ajan tanımının `name:`idir. PreToolUse hook'ları alt-ajan çağrılarında da
ateşler ⇒ kimlik ayrımı olmasa guard infra-expert'i de bloklar, işlevsiz olurdu.

**Bu korpus neyi çiviliyor:**
  (a) B1-B10  korunan yüzeye ana-oturum/vekil-ajan yazımı BLOKLANIR (+ mesaj "AYRI ve AÇIK onay" der),
  (b) S1      infra-expert AYNI dosyada SERBEST ve stderr TAM SESSİZ (guard işlevsiz olmuyor),
  (c) S2-S3   KAYIT yazmak serbest (`infra-findings.md`, `*-RESUME.md`) — engellenen İCRA'dır,
  (d) S4-S9   FP çapaları: fixture/kaynak-kod/playbook/komşu-ağaç/scripts-dokümanı,
  (e) S7/B6   kimlik İŞARET DOSYASINDAN okunur (AV-21) — ad-tabanlı tanıma FP'si üretmez,
  (f) B9/S9   `.md` muafiyeti YALNIZ `scripts/**` altındadır; `claude/rules/*.md` korunur,
  (g) K1-K7   sözleşmeler: parse-fail görünürlüğü · stdout temizliği · GERÇEK KABLOLAMA
              (hook_shim/runpy) · kopuk-junction · mesaj yollarının çözülmesi · settings
              kablolaması · sınıf kaydı.

⚠ **KAPSAM SINIRI, korpusta AÇIKÇA duruyor (S8):** kabuk üzerinden yazım (`Bash` +
`sed -i`/heredoc) KAPSANMAZ. Fiil-kara-listesi bu evde bir kez denendi ve 6 yoldan sızdı
(pre_tool_guard R10, 2026-07-10 kaldırma gerekçesi). S8 bu boşluğu "bilinmiyor" değil
"ÖLÇÜLDÜ ve açık" hâlinde tutar.

Koşum:  python tests/fixtures/infra_write_guard/run.py
MUTASYON — İKİ AYRI DEĞİŞMEZ (biri diğerini KAPSAMAZ; ikisi de koşulmalı):
  --mutasyon-blok    → blok kolu `return 2` → `return 0` (BLOK değişmezi = fix'in sökümü)
  --mutasyon-cokme   → `_sinif()` istisna atar (FAIL-CLOSED DEGRADE değişmezi):
                       blok vektörleri KABA AĞ ile AYAKTA kalmalı (sessiz geçiş YOK),
                       bedeli S4/S9'un yanlış-pozitife düşmesidir — bilinçli yön.
Mutasyon BUGÜNKÜ kaynaktan üretilir (git ref'inden DEĞİL: "fix merge olunca taban kayar"
tuzağı, B20). Desen bulunamazsa koşucu SAYI RAPORLAMADAN durur.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
HOOKS = REPO / "scripts" / "hooks"
KAYNAK = HOOKS / "infra_write_guard.py"
SABLON_AYAR = REPO / "claude" / "settings.template.json"
SIM_SABLON = REPO / "claude" / "hook_shim.template.py"
NEGATIF_KORPUS = REPO / "tests" / "fixtures" / "negatif_test_harness" / "run.py"

# ⛔ BILINMEYEN KIP SESSIZCE YESIL GECMESIN (2026-08-22): `--mutasyon-ZIRVA` gibi bir yazim
# hatasi eskiden HIC mutasyon kurmadan TAM PUAN uretiyordu (exit 0). Kardes: atc_p1_sonuc.
_GECERLI_KIP = {"--mutasyon-blok", "--mutasyon-cokme"}
for _a in sys.argv[1:]:
    if _a.startswith("--mutasyon") and _a not in _GECERLI_KIP:
        raise SystemExit(f"[KULLANIM] bilinmeyen mutasyon kipi: {_a} — gecerli: "
                         + ", ".join(sorted(_GECERLI_KIP)))

MUT_BLOK = "--mutasyon-blok" in sys.argv
MUT_COKME = "--mutasyon-cokme" in sys.argv

BLOK_CAPA = "İNFRA YAZIMI BLOKLANDI"
ONAY_CAPA = "AYRI ve AÇIK onay"
COKME_CAPA = "GUARD-COKTU"
PARSE_CAPA = "GIRDI-PARSE-EDILEMEDI"
METODOLOJI = "core/playbook/howto-infra-fix-proseduru.md"

SONUC: list[tuple[bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((bool(kosul), f"{ad}{(' -> ' + detay) if detay else ''}"))


# ── MUTANT ÜRETİMİ ───────────────────────────────────────────────────────────────
# Mutant kopya KAYNAĞIN YANINDA yaşar (temp'te değil): hook'lar komşularını `__file__`ten
# türetir; temp'teki kopya import'ta çöker ve exit 1 "FAIL" diye okunur (2026-08-13 dersi).
_MUT_BLOK_ESKI = "    sys.stderr.write(_blok_mesaji(etiket, kanit, kim, tip))\n    return 2\n"
_MUT_BLOK_YENI = "    sys.stderr.write(_blok_mesaji(etiket, kanit, kim, tip))\n    return 0\n"
_MUT_COKME_ESKI = '    norm = ham.replace("\\\\", "/")\n    if _HARIC.search(norm):\n'
_MUT_COKME_YENI = ('    raise RuntimeError("mutasyon-cokme")  # noqa\n'
                   '    norm = ham.replace("\\\\", "/")\n    if _HARIC.search(norm):\n')


def hazirla_hook() -> Path:
    """Ölçülecek hook dosyası: gerçek kaynak ya da mutant kopyası."""
    if not (MUT_BLOK or MUT_COKME):
        return KAYNAK
    metin = KAYNAK.read_text(encoding="utf-8")
    eski, yeni = (_MUT_BLOK_ESKI, _MUT_BLOK_YENI) if MUT_BLOK else (_MUT_COKME_ESKI, _MUT_COKME_YENI)
    if metin.count(eski) != 1:
        print(f"⛔ MUTASYON DESENİ BULUNAMADI/ÇOK EŞLEŞTİ ({metin.count(eski)}x) — "
              f"SAYI RAPORLANMIYOR (sahte-yeşil yerine görünür duruş).")
        sys.exit(3)
    hedef = HOOKS / "_mutant_infra_write_guard.py"
    hedef.write_text(metin.replace(eski, yeni), encoding="utf-8")
    return hedef


def payload(yol: str, arac: str = "Edit", ajan: str | None = None) -> bytes:
    d: dict = {
        "session_id": "sndbx-0001",
        "cwd": str(Path(yol).parent),
        "hook_event_name": "PreToolUse",
        "tool_name": arac,
        "tool_input": {"file_path": yol},
    }
    if arac == "Bash":
        d["tool_input"] = {"command": f"python - <<'PY'\nopen(r'{yol}','w').write('x')\nPY"}
    if ajan:
        d["agent_type"] = ajan
        d["agent_id"] = "a" + ajan[:6]
    return json.dumps(d, ensure_ascii=False).encode("utf-8")


def kos(hook: Path, govde: bytes, env: dict | None = None) -> tuple[int, str, str]:
    r = subprocess.run([sys.executable, str(hook)], input=govde, capture_output=True,
                       env=env or os.environ.copy())
    return (r.returncode,
            r.stdout.decode("utf-8", "replace"),
            r.stderr.decode("utf-8", "replace"))


def agac_kur(kok: Path) -> None:
    """Üç ayrı ağaç şekli: CORE deposu · PROJE deposu · YABANCI komşu (işaretsiz)."""
    (kok / "core_A").mkdir(parents=True, exist_ok=True)
    (kok / "core_A" / "CLAUDE.core.md").write_text("# core isareti\n", encoding="utf-8")
    (kok / "core_A" / "claude").mkdir(exist_ok=True)
    (kok / "core_A" / "claude" / "kesin-yasaklar.canonical.md").write_text("x\n", encoding="utf-8")
    for alt in ("proje_B/scripts/validators-local", "proje_B/governance",
                "proje_B/SOURCE_CODES/MOD/PKG", "proje_B/core/scripts/hooks",
                "proje_B/scripts", "komsu_C/DEV_CORE_benzeri/scripts/hooks"):
        (kok / alt).mkdir(parents=True, exist_ok=True)
    # GERÇEK KABLOLAMA ayağı: proje-lokal shim + core altında hook'un kopyası (K3/K4).
    shutil.copyfile(SIM_SABLON, kok / "proje_B" / "scripts" / "hook_shim.py")


def main() -> int:
    hook = hazirla_kaynak = hazirla_hook()
    tmp = Path(tempfile.mkdtemp(prefix="iwg_"))
    try:
        agac_kur(tmp)
        shutil.copyfile(hazirla_kaynak,
                        tmp / "proje_B" / "core" / "scripts" / "hooks" / "infra_write_guard.py")
        A = (tmp / "core_A").as_posix()
        B = (tmp / "proje_B").as_posix()
        C = (tmp / "komsu_C").as_posix()

        # ── ① BİLİNEN-BOZUK: korunan yüzeye ana-oturum/vekil yazımı → BLOK ──────────
        bloklar = [
            ("B1 lider→core validator (run_review)", f"{A}/scripts/validators/run_review.py", "Edit", None),
            ("B2 lider→core hook (yeni dosya)", f"{A}/scripts/hooks/yeni_guard.py", "Write", None),
            ("B3 lider→proje validators-local", f"{B}/scripts/validators-local/check_x.py", "Edit", None),
            ("B4 lider→git-hook (UZANTISIZ)", f"{A}/scripts/git-hooks/pre-commit", "Write", None),
            ("B5 lider→MCP script (MultiEdit)", f"{A}/mcp_servers/sap_adt/tools/atom.py", "MultiEdit", None),
            ("B6 lider→junction yolu (ISARET YOK)", f"{B}/core/scripts/hooks/post_validate.py", "Edit", None),
            ("B7 VEKİL alt-ajan (bug-expert)", f"{A}/scripts/validators/run_review.py", "Edit", "bug-expert"),
            ("B8 lider→hook_shim (yükleyici)", f"{B}/scripts/hook_shim.py", "Edit", None),
            ("B9 lider→claude/rules/*.md (davranış)", f"{A}/claude/rules/sap-source-protokolu.md", "Edit", None),
            ("B10 lider→paylaşılan core aracı", f"{A}/scripts/utils/project_config.py", "Edit", None),
        ]
        for ad, yol, arac, ajan in bloklar:
            rc, out, err = kos(hook, payload(yol, arac, ajan))
            kontrol(ad, rc == 2 and BLOK_CAPA in err and ONAY_CAPA in err,
                    f"exit={rc} blok={BLOK_CAPA in err} onay-metni={ONAY_CAPA in err}")

        # ── ② BİLİNEN-TEMİZ: FP çapaları → SERBEST (S1 ayrıca TAM SESSİZ olmalı) ────
        rc, out, err = kos(hook, payload(f"{A}/scripts/validators/run_review.py", "Edit", "infra-expert"))
        kontrol("S1 ⭐ infra-expert AYNI dosyada SERBEST + stderr TAM SESSİZ",
                rc == 0 and err.strip() == "", f"exit={rc} stderr={len(err)}b")

        serbestler = [
            ("S2 ⭐ lider→governance/infra-findings.md (KAYIT)", f"{B}/governance/infra-findings.md", "Edit", None),
            ("S3 lider→governance/*-RESUME.md", f"{B}/governance/ZSD000-RESUME.md", "Write", None),
            ("S4 lider→core/tests/fixtures/**", f"{A}/tests/fixtures/ornek/scripts/hooks/kopya.py", "Edit", None),
            ("S5 lider→SOURCE_CODES kaynak", f"{B}/SOURCE_CODES/MOD/PKG/z_ornek.abap", "Edit", None),
            ("S6 lider→core/playbook/*.md", f"{A}/playbook/lessons-learned.md", "Edit", None),
            ("S7 KOMŞU AĞAÇ (işaret YOK, ad benzer)", f"{C}/DEV_CORE_benzeri/scripts/hooks/a.py", "Edit", None),
            ("S9 lider→scripts/hooks/README.md (doküman)", f"{A}/scripts/hooks/README.md", "Edit", None),
        ]
        for ad, yol, arac, ajan in serbestler:
            rc, out, err = kos(hook, payload(yol, arac, ajan))
            kontrol(ad, rc == 0 and BLOK_CAPA not in err, f"exit={rc} blok={BLOK_CAPA in err}")

        # S8 — KAPSAM SINIRI, ölçülmüş hâlde: kabuk yüzeyi guard'ın matcher'ında YOK.
        rc, out, err = kos(hook, payload(f"{A}/scripts/hooks/yeni_guard.py", "Bash", None))
        kontrol("S8 ⚠ AÇIK KALEM: Bash ile yazım KAPSANMAZ (sessiz geçer; R10 dersi)",
                rc == 0 and err.strip() == "", f"exit={rc} stderr={len(err)}b")

        # ── ③ SÖZLEŞMELER ──────────────────────────────────────────────────────────
        rc, out, err = kos(hook, b'{"tool_name": "Edit", ')      # bozuk JSON
        kontrol("K1 parse-fail: exit 0 KORUNUR + stderr'de ASCII not (sınıf sözleşmesi)",
                rc == 0 and PARSE_CAPA in err, f"exit={rc} not={PARSE_CAPA in err}")

        rc, out, err = kos(hook, payload(f"{A}/scripts/validators/run_review.py"))
        kontrol("K2 STDOUT SÖZLEŞMESİ: blokta stdout BOŞ (harness JSON parse eder)",
                out.strip() == "", f"stdout={len(out)}b")

        # K3 — GERÇEK KABLOLAMA: hook_shim + runpy (kod ≠ kablolama; sibling-import ölümü)
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(tmp / "proje_B")
        shim = tmp / "proje_B" / "scripts" / "hook_shim.py"
        r = subprocess.run([sys.executable, str(shim), "infra_write_guard"],
                           input=payload(f"{A}/scripts/validators/run_review.py"),
                           capture_output=True, env=env)
        s_err = r.stderr.decode("utf-8", "replace")
        kontrol("K3 GERÇEK KABLOLAMA (hook_shim/runpy) blok üretiyor",
                r.returncode == 2 and BLOK_CAPA in s_err, f"exit={r.returncode}")

        # K4 — KOPUK JUNCTION: shim'in fail-closed listesi bu hook'u tanıyor mu? (bilgi+sınır)
        gizli = tmp / "proje_B" / "core_gizli"
        (tmp / "proje_B" / "core").rename(gizli)
        r2 = subprocess.run([sys.executable, str(shim), "infra_write_guard"],
                            input=payload(f"{A}/scripts/validators/run_review.py"),
                            capture_output=True, env=env)
        gizli.rename(tmp / "proje_B" / "core")
        kontrol("K4 kopuk junction: shim exit ∈ {1,2} (1 = AÇIK KALEM: hook_shim._FAIL_CLOSED "
                "listesinde DEĞİL — meta-infra, lider kararı)", r2.returncode in (1, 2),
                f"exit={r2.returncode}" + (" ← AÇIK KALEM" if r2.returncode == 1 else " ← kapatılmış"))

        # K5 — C-HOOK-01 sınıfı: mesajdaki metodoloji yolu `core/` önekli VE gerçekten var
        rc, out, err = kos(hook, payload(f"{A}/scripts/validators/run_review.py"))
        hedef = REPO / METODOLOJI[len("core/"):]
        kontrol("K5 mesajdaki metodoloji yolu `core/` önekli + dosya GERÇEKTEN var",
                METODOLOJI in err and hedef.is_file(), f"metin={METODOLOJI in err} dosya={hedef.is_file()}")

        # K6 — KABLOLAMA (kod ≠ kablolama): settings.template'te Edit|Write|MultiEdit blokunda
        ayar = json.loads(SABLON_AYAR.read_text(encoding="utf-8"))
        kablolu = any(
            "infra_write_guard" in json.dumps(h)
            for blok in ayar.get("hooks", {}).get("PreToolUse", [])
            if all(t in str(blok.get("matcher", "")) for t in ("Edit", "Write", "MultiEdit"))
            for h in blok.get("hooks", []))
        kontrol("K6 settings.template.json: Edit|Write|MultiEdit matcher'ında KABLOLU", kablolu)

        # K7 — SINIF KAYDI: stdin okuyan yeni hook, parse-fail korpusunun kaydında olmalı (V16)
        kontrol("K7 negatif_test_harness HOOK_KAYDI'nda kayıtlı (V16 sessizce büyümesin)",
                "infra_write_guard.py" in NEGATIF_KORPUS.read_text(encoding="utf-8"))

        if MUT_COKME:
            rc, out, err = kos(hook, payload(f"{A}/scripts/validators/run_review.py"))
            kontrol("M1 (yalnız --mutasyon-cokme) çökme SESSİZ DEĞİL: GUARD-COKTU izi var",
                    COKME_CAPA in err, f"iz={COKME_CAPA in err}")
    finally:
        if hook != KAYNAK:
            hook.unlink(missing_ok=True)
        shutil.rmtree(tmp, ignore_errors=True)

    etiket = " [MUTASYON-BLOK]" if MUT_BLOK else (" [MUTASYON-COKME]" if MUT_COKME else "")
    gecen = sum(1 for ok, _ in SONUC if ok)
    print(f"\n=== infra_write_guard{etiket} ===")
    for ok, ad in SONUC:
        print(f"  [{'OK  ' if ok else 'FAIL'}] {ad}")
    dusen = [ad.split(" ")[0] for ok, ad in SONUC if not ok]
    if dusen:
        print("DÜŞEN VEKTÖRLER: " + ", ".join(dusen))
    print(f"{gecen}/{len(SONUC)} OK")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
