#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AJAN/OTURUM MESAJI ONEKI — UserPromptSubmit nudge hook'lari (Q-ITG-PEER, 2026-10-03).

NEDEN BU KORPUS VAR
-------------------
`intake_triage` ve kardesi `skill_injector` otomatik olaylari (`<task-notification>`
vb.) suzuyordu ama ajan/baska-oturum mesajinin teslim oneklerini TANIMIYORDU. Olculdu
(tum proje ana-oturum transkriptleri; ITG eki parentUuid zinciriyle tetikleyen prompta
baglandi): 1450 ITG ateslemesinin 746'si "Another Claude session sent a message", 440'i
"<agent-message from=" ile BASLAYAN promptlardan (origin.kind=peer) => ~%82 FP.
Iki onek 1745 vakanin HEPSINDE metnin BASINDA; insan-origin promptlarda 0 eslesme.

UC EKSEN, HICBIRI DIGERINI KAPSAMAZ:
  P*  FP CAPASI     : gercek korpus biciminde ajan mesaji -> hook SESSIZ
  N*  POZITIF KONTROL: insan talebi (alinti icerse bile) -> hook HALA atesler
      (N2 = kullanici bir ajan mesajini ALINTILAYIP gelistirme ister: onek BASTA
       degil -> atesler. "Icerikte ara" tasarimi bunu yutar; --mutasyon-onek-icerik
       tam bunu sinar.)
  K*  KARDES        : ayni sozlesme skill_injector'da (ayni UPS blogu, ayni yontem)

GERCEK GIRIS NOKTASI: her vektor `hook_shim.py` uzerinden kosulur (settings.template.json
`python ${CLAUDE_PROJECT_DIR}/scripts/hook_shim.py <hook>`). Gecici proje = shim'in
template'den kopyasi + `core/scripts/{hooks,utils}` KOPYASI (junction YOK: fixture
temizliginde junction'a inen silme HEDEFI silebilir; kopya bu riski yapisal kapatir).
Her kosumda stderr'de `GIRDI-PARSE-EDILEMEDI` aranir (varsa olcum gecersiz).

KOSUM:  python tests/fixtures/ajan_mesaji_onek/run.py
        ... --mutasyon-onek-yok-intake   (intake: onek suzgeci sokulur  -> P1/P2/P3 duser)
        ... --mutasyon-onek-yok-skill    (skill : onek suzgeci sokulur  -> K1/K2 duser)
        ... --mutasyon-onek-icerik       (intake: BASTA degil ICERIKTE  -> N2 duser)
        ... --mutasyon-onek-gevsek       (intake: `from=` capasi atilir -> N3 duser)
Cikis:  0 hepsi beklendigi gibi · 1 sapma · 2 DOGRULANAMADI (capa tutmadi / mutant derlenmedi)
"""
from __future__ import annotations

import json
import os
import py_compile
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

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SHIM = REPO / "claude" / "hook_shim.template.py"
HOOKS = REPO / "scripts" / "hooks"
UTILS = REPO / "scripts" / "utils"

ITG_MK = "INTAKE TRIAGE GATE"
SKILL_MK = "doğrulama tespit edildi]"
PARSE_MK = "GIRDI-PARSE-EDILEMEDI"

FILTRE = "    if prompt.lstrip().startswith(_AUTO_EVENT_ONEKLER):   # ajan/oturum mesajı (Q-ITG-PEER)\n"
MUTLAR = {
    "--mutasyon-onek-yok-intake": ("intake_triage.py", FILTRE, "    if False:  # MUTASYON\n"),
    "--mutasyon-onek-yok-skill": ("skill_injector.py", FILTRE, "    if False:  # MUTASYON\n"),
    "--mutasyon-onek-icerik": (
        "intake_triage.py", FILTRE,
        "    if any(o in prompt for o in _AUTO_EVENT_ONEKLER):  # MUTASYON\n"),
    "--mutasyon-onek-gevsek": ("intake_triage.py", '    "<agent-message from=",\n',
                               '    "<agent-message",  # MUTASYON\n'),
}
BEKLENEN_DUSUS = {
    "--mutasyon-onek-yok-intake": ("P1", "P2", "P3"),
    "--mutasyon-onek-yok-skill": ("K1", "K2"),
    "--mutasyon-onek-icerik": ("N2",),
    "--mutasyon-onek-gevsek": ("N3",),
}

# Gercek korpus bicimleri (kimlik izleri placeholder).
ANOTHER = ('Another Claude session sent a message:\n'
           '<teammate-message teammate_id="<AJAN>" color="blue">\n'
           'Rapor hazir. Yeni rapor geliştirme talebi için şu alanları ekleyelim: VBELN, POSNR.\n'
           '</teammate-message>')
AGENT_MSG = ('<agent-message from="<AJAN>">\n'
             'Gate turu bitti; şu alanı da ekleyelim ve kodu düzeltelim.\n'
             '</agent-message>')


def proje_kur(kok: Path, kip: str) -> Path:
    """Gecici proje: scripts/hook_shim.py + core/scripts/{hooks,utils} kopyasi."""
    p = kok / "proje"
    (p / "scripts").mkdir(parents=True)
    (p / ".claude").mkdir()
    shutil.copyfile(SHIM, p / "scripts" / "hook_shim.py")
    hedef = p / "core" / "scripts"
    shutil.copytree(UTILS, hedef / "utils",
                    ignore=shutil.ignore_patterns("__pycache__"))
    (hedef / "hooks").mkdir(parents=True)
    for ad in ("intake_triage.py", "skill_injector.py"):
        shutil.copyfile(HOOKS / ad, hedef / "hooks" / ad)
    if kip:
        dosya, eski, yeni = MUTLAR[kip]
        f = hedef / "hooks" / dosya
        src = f.read_text(encoding="utf-8")
        if src.count(eski) != 1:   # CORE-07: capa TAM BIR KEZ eslesmeli
            raise SystemExit(f"[DOGRULANAMADI] mutasyon capasi {src.count(eski)} kez "
                             f"eslesti ({kip}, {dosya}); 1 bekleniyordu")
        f.write_text(src.replace(eski, yeni, 1), encoding="utf-8", newline="\n")
        try:
            py_compile.compile(str(f), doraise=True)
        except py_compile.PyCompileError as e:
            raise SystemExit(f"[DOGRULANAMADI] mutant derlenmedi ({kip}): {e}")
    return p


def kos(proje: Path, hook: str, prompt: str) -> tuple[int, str, str]:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(proje)
    env["PYTHONIOENCODING"] = "utf-8"
    girdi = json.dumps({"prompt": prompt, "hook_event_name": "UserPromptSubmit"},
                       ensure_ascii=False).encode("utf-8")
    r = subprocess.run([sys.executable, str(proje / "scripts" / "hook_shim.py"), hook],
                       input=girdi, env=env, capture_output=True, cwd=str(proje),
                       timeout=120)
    out = r.stdout.decode("utf-8", "replace")
    try:
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    except Exception:
        ctx = ""
    return r.returncode, ctx, r.stderr.decode("utf-8", "replace")


def main() -> int:
    arg = sys.argv[1:]
    if any(a in ("-h", "--help") for a in arg):
        print(__doc__)
        return 0
    for a in arg:
        if a.startswith("--mutasyon") and a not in MUTLAR:
            print(f"[KULLANIM] bilinmeyen mutasyon kipi: {a} -> gecerli: {sorted(MUTLAR)}")
            return 2
    kip = next((a for a in arg if a in MUTLAR), "")

    tmp = Path(tempfile.mkdtemp(prefix="ajan_onek_"))
    sonuc: list[tuple[str, bool, str]] = []
    try:
        proje = proje_kur(tmp, kip)

        def vektor(ad: str, hook: str, prompt: str, isaret: str, atesmeli: bool) -> None:
            rc, ctx, err = kos(proje, hook, prompt)
            if PARSE_MK in err:
                sonuc.append((ad, False, f"OLCUM GECERSIZ: {PARSE_MK} (girdi okunmadi)"))
                return
            atesledi = isaret in ctx
            sonuc.append((ad, rc == 0 and atesledi == atesmeli,
                          f"rc={rc} atesledi={atesledi} beklenen={atesmeli} err={err[-160:]!r}"))

        # P — FP capasi: gercek korpus biciminde ajan mesaji -> SESSIZ
        vektor("P1 'Another Claude session' (teammate) -> ITG SESSIZ",
               "intake_triage", ANOTHER, ITG_MK, False)
        vektor("P2 '<agent-message from=' (queued peer) -> ITG SESSIZ",
               "intake_triage", AGENT_MSG, ITG_MK, False)
        vektor("P3 bastaki bosluk/satir sonu onekin onunde -> ITG SESSIZ",
               "intake_triage", "\n  " + ANOTHER, ITG_MK, False)
        # N — pozitif kontrol: insan talebi HALA atesler
        vektor("N1 insan gelistirme talebi -> ITG ATESLER",
               "intake_triage", "Sevk emri ekranına yeni rapor geliştir, şu alanları ekleyelim.",
               ITG_MK, True)
        vektor("N2 insan bir ajan mesajini ALINTILAYIP gelistirme ister -> ITG ATESLER",
               "intake_triage", "Şu mesaja göre ekranı geliştir:\n" + ANOTHER, ITG_MK, True)
        vektor("N3 insan '<agent-message>' etiketinden soz eder (from= yok) -> ITG ATESLER",
               "intake_triage", "<agent-message> etiketini rapora ekleyelim, geliştir.",
               ITG_MK, True)
        vektor("N4 eski B5 isareti korunur: <task-notification> -> ITG SESSIZ",
               "intake_triage", "<task-notification>\n<status>completed</status>\nyeni rapor "
               "geliştir</task-notification>", ITG_MK, False)
        # K — kardes: skill_injector ayni sozlesme
        vektor("K1 skill_injector: 'Another Claude session' + playwright -> SESSIZ",
               "skill_injector", ANOTHER + "\nplaywright ile ekran görüntüsü al", SKILL_MK, False)
        vektor("K2 skill_injector: '<agent-message from=' + screenshot -> SESSIZ",
               "skill_injector", AGENT_MSG + "\nscreenshot alip UI doğrula", SKILL_MK, False)
        vektor("K3 skill_injector: insan 'playwright ile UI doğrula' -> ATESLER",
               "skill_injector", "playwright ile UI doğrula", SKILL_MK, True)
        vektor("K4 skill_injector: insan alintisi (onek basta degil) -> ATESLER",
               "skill_injector", "playwright ile bak:\n" + AGENT_MSG, SKILL_MK, True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)   # kopya agac; junction YOK

    print("=" * 78)
    print(f"AJAN MESAJI ONEKI (Q-ITG-PEER) — kip: {kip or 'taban'}")
    print("=" * 78)
    dusen = 0
    for ad, ok, not_ in sonuc:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"   -> {not_}"))
        dusen += 0 if ok else 1
    if kip:
        print(f"  (beklenen dususler: {', '.join(BEKLENEN_DUSUS[kip])})")
    print(f"{len(sonuc) - dusen}/{len(sonuc)} OK  (P+N+K iceride)")
    print(f"TOPLAM: {len(sonuc) - dusen} PASS / {dusen} FAIL")
    return 1 if dusen else 0


if __name__ == "__main__":
    raise SystemExit(main())
