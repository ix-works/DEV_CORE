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

  (h) S10-S20 KABUK KOLU (2026-08-29, kayıt #47 — KULLANICI KARARI "dar kapsam + log,
              blok yok"): `sed -i` / `>` / `tee` hedefi korunan yüzeydeyse stderr'e NOT
              basılır ve **exit 0** dönülür; belirsiz kalıp (heredoc · `cp` · `python -c`)
              SUSAR; salt-okuma SUSAR; infra-expert muafiyeti burada da geçerlidir,
  (i) K8      kabuk kolunun KABLOLAMASI (`settings.template.json` ayrı `Bash` bloğu) —
              kod ≠ kablolama: bu satır olmadan S10-S13 CANLIDA ÖLÜDÜR.
  (j) B11-B13 ⭐ **KOŞUCU SINIFI (2026-08-29 daraltması):** fixture'ın KOŞUCUSU korunur
              (`run.py` · `tests/run_*.py` · proje `validators-local/fixtures/**.py`);
              S1b muafiyet, S12b kabuk kolu, **S21-S23 FP çapaları** korpusun SERBEST
              kaldığını çiviler. S23 sınırın kendisidir: `run.py` ADI yetmez, KONUM da
              gerekir — korpus ağacının derinliğindeki `run.py` bir sahte-proje dosyasıdır.

⚠ **KAPSAM SINIRI hâlâ AÇIK ve korpusta ÖLÇÜLÜ (S8/S17/S18):** kabuk kolu **BLOKLAMAZ**
ve YALNIZ üç kesin kalıbı tanır. Heredoc · `cp` · `python -c` KAPSANMAZ — bu bir eksiklik
değil, ölçülmüş bir sınırdır: fiil-kara-listesi bu evde bir kez denendi ve 6 yoldan sızdı
(pre_tool_guard R10, 2026-07-10 kaldırma gerekçesi); yanlış-pozitif üreten bir guard
guard'sızlıktan daha kötüdür.

Koşum:  python tests/fixtures/infra_write_guard/run.py
MUTASYON — YEDİ AYRI DEĞİŞMEZ (hiçbiri diğerini KAPSAMAZ; yedisi de koşulmalı):
  --mutasyon-blok      → blok kolu `return 2` → `return 0` (BLOK değişmezi = fix'in sökümü)
                         ⇒ B1-B10 düşer; kabuk kolu (S10-S13) ETKİLENMEZ — iki kol
                         YAPISAL OLARAK AYRIDIR ve bu ayrım burada ölçülür.
  --mutasyon-cokme     → `_sinif()` istisna atar (FAIL-CLOSED DEGRADE değişmezi):
                         blok vektörleri KABA AĞ ile AYAKTA kalmalı (sessiz geçiş YOK).
                         ÖLÇÜLEN bedel (35/48): B10 + S4/S7/S9 kaba-ağ FP'si + koşucu
                         sınıfı (B11/B12/S12b — `_KABA`'ya `run.py` EKLENMEDİ: alt-dizge
                         testi olduğu için HER projenin `run.py`'ını yakalardı); kabuk kolu
                         S10-S13b susar ve S14 çökme-notunu görür — kabuk kolu bilinçli
                         FAIL-OPEN'dır (uyarı üretmek için çökme YETERLİ SEBEP DEĞİL).
  --mutasyon-bash-kol  → `main()`teki kabuk dalı sökülür (`return _bash_kolu` → `return 0`)
                         ⇒ S10-S13 düşer; B1-B10 + FP çapaları AYAKTA (NO-OP tuzağının
                         doğrudan ölçümü: yalnız `_ARACLAR`a "Bash" eklemek YETMEZ).
  --mutasyon-bash-cwd  → göreceli yolun `cwd` ile mutlaklaştırılması sökülür
                         ⇒ YALNIZ S13 düşer (kabuk komutları yolu göreceli yazar;
                         bu satır olmadan kol canlıda büyük ölçüde ÖLÜDÜR).
  ⭐ KOŞUCU DARALTMASININ ÜÇ PARÇASI — her biri TEK BAŞINA daraltmayı NO-OP yapar
  (`_ARACLAR`/Bash vakasının birebir ikizi; üçü de ayrı ayrı ÖLÇÜLDÜ 2026-08-29):
  --mutasyon-kosucu-haric → `_HARIC` istisnası sökülür  ⇒ B11·B12·S12b düşer (44/47)
  --mutasyon-kosucu-sinif → `_KORUNAN_CORE` deseni sökülür ⇒ AYNI ÜÇÜ düşer (44/47)
  --mutasyon-kosucu-proje → `_KORUNAN_PROJE` deseni sökülür ⇒ YALNIZ B13 (46/47);
                         diğer iki mutasyonun HİÇBİRİ B13'ü düşürmez — proje sınıfı
                         ayrı tabloda yaşar, bu yüzden ayrı mutasyon HAK EDİYOR.
Mutasyon BUGÜNKÜ kaynaktan üretilir (git ref'inden DEĞİL: "fix merge olunca taban kayar"
tuzağı, B20). Desen bulunamazsa koşucu SAYI RAPORLAMADAN durur.
⭐ Bu çapa 2026-08-29'da CANLI ateşledi: `_HARIC` satırı daraltılınca `--mutasyon-cokme`
deseni tutmadı ve koşucu `exit 3` ile durdu — sessiz-yeşil ÜRETMEDİ.
"""
from __future__ import annotations

import json
import os
import re
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
_GECERLI_KIP = {"--mutasyon-blok", "--mutasyon-cokme",
                "--mutasyon-bash-kol", "--mutasyon-bash-cwd",
                "--mutasyon-kosucu-haric", "--mutasyon-kosucu-sinif",
                "--mutasyon-kosucu-proje"}
for _a in sys.argv[1:]:
    if _a.startswith("--mutasyon") and _a not in _GECERLI_KIP:
        raise SystemExit(f"[KULLANIM] bilinmeyen mutasyon kipi: {_a} — gecerli: "
                         + ", ".join(sorted(_GECERLI_KIP)))

MUT_BLOK = "--mutasyon-blok" in sys.argv
MUT_COKME = "--mutasyon-cokme" in sys.argv
MUT_BASH_KOL = "--mutasyon-bash-kol" in sys.argv
MUT_BASH_CWD = "--mutasyon-bash-cwd" in sys.argv
MUT_KOS_HARIC = "--mutasyon-kosucu-haric" in sys.argv
MUT_KOS_SINIF = "--mutasyon-kosucu-sinif" in sys.argv
MUT_KOS_PROJE = "--mutasyon-kosucu-proje" in sys.argv

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
_MUT_COKME_ESKI = ('    norm = ham.replace("\\\\", "/")\n'
                   '    if _HARIC.search(norm) and not _KOSUCU.search(norm):\n')
_MUT_COKME_YENI = ('    raise RuntimeError("mutasyon-cokme")  # noqa\n'
                   '    norm = ham.replace("\\\\", "/")\n'
                   '    if _HARIC.search(norm) and not _KOSUCU.search(norm):\n')
# ⭐ KOŞUCU DARALTMASININ İKİ AYRI DEĞİŞMEZİ — biri diğerini KAPSAMAZ (NO-OP tuzağı,
# `_ARACLAR`/Bash vakasının birebir ikizi; ölçüldü 2026-08-29):
#   `--mutasyon-kosucu-haric` → `_HARIC` istisnası sökülür (sınıflandırma deseni DURUR)
#   `--mutasyon-kosucu-sinif` → `_KORUNAN_CORE` deseni sökülür (istisna DURUR)
# Her biri TEK BAŞINA daraltmayı tamamen etkisizleştirir ⇒ ikisi de ayrı ayrı ölçülür.
# Biri koşulmazsa korpus "yalnız bir yarısını yazdım" hatasını GÖREMEZ.
_MUT_KOSUCU_HARIC_ESKI = "    if _HARIC.search(norm) and not _KOSUCU.search(norm):\n"
_MUT_KOSUCU_HARIC_YENI = "    if _HARIC.search(norm):\n"
_MUT_KOSUCU_SINIF_ESKI = '    (re.compile(r"^" + _KOSUCU_REL), "fixture koşucusu (kanıt aracı)"),\n'
_MUT_KOSUCU_SINIF_YENI = ""
# ÜÇÜNCÜ bağımsız parça: proje-lokal koşucu sınıfı AYRI bir tabloda (`_KORUNAN_PROJE`)
# yaşar ve yukarıdaki iki mutasyonun HİÇBİRİ onu düşürmez (ölçüldü: B13 ikisinde de
# AYAKTA). Mutasyonsuz bırakılsaydı B13'ün ayırt edici olduğu KANITLANMAMIŞ olurdu.
_MUT_KOSUCU_PROJE_ESKI = ('    (re.compile(_KOSUCU_PROJE, re.IGNORECASE), '
                          '"proje-lokal fixture koşucusu (kanıt aracı)"),\n')
_MUT_KOSUCU_PROJE_YENI = ""
# Kabuk kolunun İKİ ayrı değişmezi (biri diğerini kapsamaz):
_MUT_BASH_KOL_ESKI = "    if arac in _LOG_ARACLARI:\n        return _bash_kolu(data, ti)\n"
_MUT_BASH_KOL_YENI = "    if arac in _LOG_ARACLARI:\n        return 0\n"
_MUT_BASH_CWD_ESKI = ('        if not p.is_absolute() and isinstance(cwd, str) and cwd:\n'
                      '            y = (Path(cwd) / p).as_posix()\n')
_MUT_BASH_CWD_YENI = ('        if False:\n'
                      '            y = (Path(cwd) / p).as_posix()\n')


def hazirla_hook() -> Path:
    """Ölçülecek hook dosyası: gerçek kaynak ya da mutant kopyası."""
    if not (MUT_BLOK or MUT_COKME or MUT_BASH_KOL or MUT_BASH_CWD
            or MUT_KOS_HARIC or MUT_KOS_SINIF or MUT_KOS_PROJE):
        return KAYNAK
    metin = KAYNAK.read_text(encoding="utf-8")
    if MUT_BLOK:
        eski, yeni = _MUT_BLOK_ESKI, _MUT_BLOK_YENI
    elif MUT_COKME:
        eski, yeni = _MUT_COKME_ESKI, _MUT_COKME_YENI
    elif MUT_BASH_KOL:
        eski, yeni = _MUT_BASH_KOL_ESKI, _MUT_BASH_KOL_YENI
    elif MUT_KOS_HARIC:
        eski, yeni = _MUT_KOSUCU_HARIC_ESKI, _MUT_KOSUCU_HARIC_YENI
    elif MUT_KOS_SINIF:
        eski, yeni = _MUT_KOSUCU_SINIF_ESKI, _MUT_KOSUCU_SINIF_YENI
    elif MUT_KOS_PROJE:
        eski, yeni = _MUT_KOSUCU_PROJE_ESKI, _MUT_KOSUCU_PROJE_YENI
    else:
        eski, yeni = _MUT_BASH_CWD_ESKI, _MUT_BASH_CWD_YENI
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


def bash_payload(komut: str, cwd: str | None = None, ajan: str | None = None) -> bytes:
    """Bash PreToolUse payload'ı — `tool_input` = {command, description} (yol ALANI YOK).

    ⛔ PLATFORM SÖZLEŞMESİ (DEV_CORE#150 dersi): komut içindeki yol DAİMA `/` biçiminde
    olmalı. Windows yolu (`C:\\...\\x`) gömülürse guard'ın `_sinif()` normalizasyonu
    değil, komut METNİ platforma bağlanır ve mutasyon Linux'ta sessizce KAÇAR.
    """
    if re.search(r"[A-Za-z]:\\|\\\\", komut):
        raise AssertionError(
            "korpus hatasi: Bash komutunda WINDOWS yolu var (`\\`). Yol DAIMA `/` "
            f"olmali (as_posix). Gorulen: {komut[:120]!r}")
    d: dict = {
        "session_id": "sndbx-0001",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": komut, "description": "sandbox"},
    }
    if cwd:
        d["cwd"] = cwd
    if ajan:
        d["agent_type"] = ajan
        d["agent_id"] = "a" + ajan[:6]
    return json.dumps(d, ensure_ascii=False).encode("utf-8")


def kos(hook: Path, govde: bytes, env: dict | None = None,
        calisma_dizini: str | None = None) -> tuple[int, str, str]:
    """⚠ `calisma_dizini` GEREKLİ BİR DEĞİŞKENDİR, süs değil.

    ÖLÇÜLDÜ 2026-08-29: `_sinif()` içindeki `Path.resolve()` GÖRECELİ bir yolu SÜRECİN
    kendi cwd'sine göre çözer. Korpus repo kökünden koşulduğunda bu, payload'ın `cwd`
    alanıyla AYNI sonucu verir ⇒ iki katman ÜST ÜSTE biner ve `--mutasyon-bash-cwd`
    KAÇAR (ilk koşumda tam olarak bu oldu: 38/38, mutasyon hiçbir şey kırmadı).
    Göreceli-yol vektörleri bu yüzden NÖTR bir çalışma dizininde koşulur; ancak o zaman
    ölçülen şey gerçekten payload `cwd` birleştirmesidir.
    """
    r = subprocess.run([sys.executable, str(hook)], input=govde, capture_output=True,
                       env=env or os.environ.copy(), cwd=calisma_dizini)
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
            # ── KOŞUCU SINIFI (2026-08-29 daraltması) ───────────────────────────────
            # Fixture koşucusu KORPUS DEĞİL, kanıt aracının kendisidir: mutasyon kümesini
            # ve TABAN STRATEJİSİNİ taşır ⇒ CI'ın yeşil/kırmızı kararını o belirler.
            ("B11 ⭐ lider→fixture KOŞUCUSU (run.py)", f"{A}/tests/fixtures/ornek/run.py", "Edit", None),
            ("B12 ⭐ lider→süit koşucusu (tests/run_*.py)", f"{A}/tests/run_fixture_tests.py", "Edit", None),
            ("B13 ⭐ lider→proje-lokal fixture koşucusu (AD DEĞİL KONUM)",
             f"{B}/scripts/validators-local/fixtures/q1/kur_ve_kos.py", "Write", None),
        ]
        for ad, yol, arac, ajan in bloklar:
            rc, out, err = kos(hook, payload(yol, arac, ajan))
            kontrol(ad, rc == 2 and BLOK_CAPA in err and ONAY_CAPA in err,
                    f"exit={rc} blok={BLOK_CAPA in err} onay-metni={ONAY_CAPA in err}")

        # ── ② BİLİNEN-TEMİZ: FP çapaları → SERBEST (S1 ayrıca TAM SESSİZ olmalı) ────
        rc, out, err = kos(hook, payload(f"{A}/scripts/validators/run_review.py", "Edit", "infra-expert"))
        kontrol("S1 ⭐ infra-expert AYNI dosyada SERBEST + stderr TAM SESSİZ",
                rc == 0 and err.strip() == "", f"exit={rc} stderr={len(err)}b")

        # ⭐ Daraltmanın ÇIKIŞ YOLU çalışıyor mu: koşucuyu yazması GEREKEN rol MUAF mı?
        # Bu vektör olmadan daraltma "kimse yazamaz"a dönerdi — kural değil kilit olurdu.
        rc, out, err = kos(hook, payload(f"{A}/tests/fixtures/ornek/run.py", "Edit", "infra-expert"))
        kontrol("S1b ⭐ infra-expert KOŞUCUYU yazabilir (muafiyet) + TAM SESSİZ",
                rc == 0 and err.strip() == "", f"exit={rc} stderr={len(err)}b")

        serbestler = [
            ("S2 ⭐ lider→governance/infra-findings.md (KAYIT)", f"{B}/governance/infra-findings.md", "Edit", None),
            ("S3 lider→governance/*-RESUME.md", f"{B}/governance/ZSD000-RESUME.md", "Write", None),
            ("S4 lider→core/tests/fixtures/**", f"{A}/tests/fixtures/ornek/scripts/hooks/kopya.py", "Edit", None),
            ("S5 lider→SOURCE_CODES kaynak", f"{B}/SOURCE_CODES/MOD/PKG/z_ornek.abap", "Edit", None),
            ("S6 lider→core/playbook/*.md", f"{A}/playbook/lessons-learned.md", "Edit", None),
            ("S7 KOMŞU AĞAÇ (işaret YOK, ad benzer)", f"{C}/DEV_CORE_benzeri/scripts/hooks/a.py", "Edit", None),
            ("S9 lider→scripts/hooks/README.md (doküman)", f"{A}/scripts/hooks/README.md", "Edit", None),
            # ── KOŞUCU DARALTMASININ FP ÇAPALARI (korpus SERBEST kalmalı) ───────────
            # ⛔ Bunlar süs değil: daraltma "tests/ altındaki .py" diye yazılsaydı S22
            # KIRMIZI olurdu. Gerçek repoda tam olarak o şekilde bir dosya VAR ve
            # ölçüldü: tests/fixtures/pre_tool_guard/agac/cekirdek_ikizi/scripts/
            # mevcut.py — sahte ağacın içinde `CLAUDE.core.md` işareti taşıdığı için
            # "paylaşılan core/scripts aracı" sınıfına giriyor. Korpus VERİdir.
            ("S21 lider→fixture KORPUSU (bad/ örneği)", f"{A}/tests/fixtures/ornek/bad/kotu.abap", "Edit", None),
            ("S22 ⭐ FP: korpus içindeki sahte ağacın .py'si (gerçek vaka)",
             f"{A}/tests/fixtures/ornek/agac/ikiz/scripts/mevcut.py", "Edit", None),
            # ⭐ SINIRIN KENDİSİ: `run.py` adı YETMEZ, KONUM da gerekir. Korpus ağacının
            # derinliğindeki bir `run.py` KOŞUCU DEĞİL, sahte projenin dosyasıdır.
            ("S23 ⭐ SINIR: korpus ağacının DERİNİNDEKİ run.py koşucu DEĞİL",
             f"{A}/tests/fixtures/ornek/agac/ikiz/run.py", "Edit", None),
        ]
        for ad, yol, arac, ajan in serbestler:
            rc, out, err = kos(hook, payload(yol, arac, ajan))
            kontrol(ad, rc == 0 and BLOK_CAPA not in err, f"exit={rc} blok={BLOK_CAPA in err}")

        # ── ②b KABUK KOLU (2026-08-29, kayıt #47 — KULLANICI KARARI: dar + LOG, blok YOK) ──
        # ⛔ ORTAK ÇAPA: kabuk kolu HİÇBİR vektörde exit 2 üretmez. Blok, yalnız
        #    Edit/Write/MultiEdit'in işidir; iki kol yapısal olarak ayrıdır.
        rc, out, err = kos(hook, payload(f"{A}/scripts/hooks/yeni_guard.py", "Bash", None))
        kontrol("S8 ⚠ SINIR: heredoc (`python - <<PY`) BELİRSİZ kalıp → SESSİZ geçer (R10 dersi)",
                rc == 0 and err.strip() == "", f"exit={rc} stderr={len(err)}b")

        UYARI_CAPA = "BASH-KAPSAM-UYARISI"
        kabuk_log = [
            ("S10 ⭐ `sed -i <infra dosyası>` → LOG + exit 0 (BLOK DEĞİL)",
             f"sed -i 's/a/b/' {A}/scripts/hooks/post_validate.py"),
            ("S11 ⭐ `> <infra dosyası>` yönlendirmesi → LOG",
             f"echo x > {A}/scripts/validators/check_yeni.py"),
            ("S12 ⭐ `tee -a <proje-lokal validator>` → LOG",
             f"echo x | tee -a {B}/scripts/validators-local/check_x.py"),
            # Yeni KOŞUCU sınıfı kabuk kolunda da görünür: iki kol AYRI ama `_sinif()`
            # ORTAK. Bu vektör olmadan sınıfın yalnız yarısı ölçülmüş olurdu.
            ("S12b ⭐ `sed -i <fixture koşucusu>` → LOG (yeni sınıf kabuk kolunda da)",
             f"sed -i 's/a/b/' {A}/tests/fixtures/ornek/run.py"),
        ]
        for ad, komut in kabuk_log:
            rc, out, err = kos(hook, bash_payload(komut))
            kontrol(ad, rc == 0 and UYARI_CAPA in err and BLOK_CAPA not in err,
                    f"exit={rc} uyari={UYARI_CAPA in err} blok={BLOK_CAPA in err}")

        # S13 ⭐ GÖRECELİ yol + payload `cwd` — kabuk komutları yolu böyle yazar.
        #    ⚠ NÖTR çalışma dizini ZORUNLU: aksi hâlde `_sinif()`in `resolve()`ü aynı
        #    işi sürecin cwd'siyle yapar, iki katman üst üste biner ve mutasyon KAÇAR
        #    (ölçüldü — `kos()` docstring'i). Tek değişken: payload'ın `cwd` alanı.
        NOTR = str(tmp)
        rc, out, err = kos(hook, bash_payload("sed -i 's/a/b/' scripts/hooks/post_validate.py",
                                              cwd=A), calisma_dizini=NOTR)
        kontrol("S13 ⭐ GÖRECELİ yol payload `cwd`siyle çözülüyor → LOG (kol ölü değil)",
                rc == 0 and UYARI_CAPA in err, f"exit={rc} uyari={UYARI_CAPA in err}")

        # S13b SINIR BEYANI: payload `cwd` YOKSA ve süreç cwd'si nötrse yol çözülemez →
        #      SUSAR. Bu bir eksiklik değil, kapsamın ÖLÇÜLMÜŞ sınırıdır (tahmin YOK).
        rc, out, err = kos(hook, bash_payload("sed -i 's/a/b/' scripts/hooks/post_validate.py"),
                           calisma_dizini=NOTR)
        kontrol("S13b ⚠ SINIR: `cwd` yok + nötr süreç dizini → göreceli yol çözülemez, SESSİZ",
                rc == 0 and err.strip() == "", f"exit={rc} stderr={err.strip()[:80]!r}")

        # ── FP ÇAPALARI: yanlış-pozitif üreten guard, guard'sızlıktan KÖTÜDÜR ───────
        kabuk_sessiz = [
            ("S14 FP: `sed -i` ama SIRADAN dosya (aynı fiil, tek değişken yol)",
             f"sed -i 's/a/b/' {B}/SOURCE_CODES/MOD/PKG/z_ornek.abap", None),
            ("S15 FP ⭐ İÇ KONTROL: SALT-OKUMA komutu aynı infra dosyasında → SESSİZ",
             f"cat {A}/scripts/hooks/post_validate.py", None),
            ("S16 FP: `> /dev/null` hedefi dosya DEĞİLDİR", "echo x > /dev/null", None),
            ("S17 FP: `cp` BELİRSİZ kalıp (kullanıcı kararı: girme) → SESSİZ",
             f"cp /tmp/a.py {A}/scripts/hooks/yeni.py", None),
            ("S18 FP: `python -c` BELİRSİZ kalıp → SESSİZ",
             f"python -c \"open('{A}/scripts/hooks/y.py','w').write('x')\"", None),
            ("S19 FP: komut YOK/boş → SESSİZ", "", None),
            ("S20 ⭐ MUAFİYET kabuk kolunda da geçerli: infra-expert → TAM SESSİZ",
             f"sed -i 's/a/b/' {A}/scripts/hooks/post_validate.py", "infra-expert"),
        ]
        for ad, komut, ajan in kabuk_sessiz:
            rc, out, err = kos(hook, bash_payload(komut, ajan=ajan))
            kontrol(ad, rc == 0 and err.strip() == "", f"exit={rc} stderr={err.strip()[:90]!r}")

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

        # K8 — KABUK KOLUNUN KABLOLAMASI (2026-08-29, kayıt #47 katman-3). Kod tek başına
        # ÖLÜDÜR: matcher'da `Bash` yoksa hook Bash çağrısında HİÇ çağrılmaz. AYRICA
        # kablolamanın AYRI bir blokta olduğu çivilenir — mevcut `Edit|Write|MultiEdit`
        # bloğuna `Bash` eklemek `pre_tool_guard` + `pull_before_edit`i de her Bash
        # çağrısına bağlardı (ölçülmemiş yayılım; bilinçli olarak YAPILMADI).
        _pre = ayar.get("hooks", {}).get("PreToolUse", [])
        _bash_bloklari = [b for b in _pre if str(b.get("matcher", "")) == "Bash"]
        _bash_kablolu = any("infra_write_guard" in json.dumps(h)
                            for b in _bash_bloklari for h in b.get("hooks", []))
        _bash_yalniz = all(
            {"infra_write_guard"} == {a for h in b.get("hooks", []) for a in h.get("args", [])
                                      if not a.startswith("${")}
            for b in _bash_bloklari) if _bash_bloklari else False
        kontrol("K8 ⭐ settings.template.json: AYRI `Bash` bloğunda KABLOLU ve o blokta "
                "YALNIZ infra_write_guard var (komşu hook'lar Bash'e sızdırılmadı)",
                _bash_kablolu and _bash_yalniz,
                f"blok={len(_bash_bloklari)} kablolu={_bash_kablolu} yalniz={_bash_yalniz}")

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
