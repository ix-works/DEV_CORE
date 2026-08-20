#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K8①② — nudge TETIGI (Bash duzenlemesi) + gate KAPSAMI (stderr nudge'lari).

=== ① post_validate: Bash ile yapilan duzenleme de DUZENLEMEDIR ===
Hook'un TUM nudge'lari `tool_input.file_path`e bakiyordu. `sed -i`, heredoc, `> dosya`
gibi Bash duzenlemelerinde o anahtar YOKTUR ⇒ nudge HIC atesle(n)mez. Bu, 2026-08-14'te
`post_tool_failure`da yasanan sinifin aynisi: **arac degisti, tetik degismedi.**

⚠ SINIR-NOTU (bu turda KURULMADI, RAPORLANDI): hook `settings.template.json`'da
   `matcher: "Edit|Write|MultiEdit"` ile kayitlidir. `Bash` eklenmedikce hook Bash
   cagrilarinda CAGRILMAZ ve asagidaki kod CANLIDA OLU kalir. Matcher META-INFRA'dir
   (infra-expert kapsami disi) ⇒ karar liderin/kullanicinin. A6 bu durumu civiller:
   ya matcher `Bash` icerir YA DA kaynak SINIR-NOTU tasir — ikisi de yoksa birileri
   notu silmis ve kimse kablolamamis demektir (sessiz olu kod).

=== ② check_hook_injected_paths: stderr nudge'lari da ENJEKSIYONDUR ===
Gate yalniz `additionalContext` ureten hook'lari yokluyordu. `post_validate` yolu
**stderr**e yazar ve o metin de ajana geri beslenir (exit 2) — ayni C-HOOK-01 kirilmasi
orada da olur ama gate GORMUYORDU.

⚠ KAPSAM GENISLEMESI (ADR 0019) — OLCULDU: gercek projede yol sayisi **4 -> 8**,
   kirik **0 -> 0**. Yani genisleme ne OLU (4 yeni yol goruyor) ne de GECILEMEZ
   (0 ihlal) ⇒ HARD siddeti korunabildi. M4 ⭐ POZITIF KONTROL bunun bedelidir:
   genisleyen kapsam GERCEKTEN yakaliyor mu? (Sayi artisi "yakaliyor" demek DEGILDIR.)

  A1 ⭐ AYIRT EDICI  `sed -i ... docs/KD-*.md` -> nudge ATESLER (once: sessiz)
  A2               `> dosya` YONLENDIRMESI de duzenlemedir -> nudge ATESLER
  A3 FP capasi     salt-OKUMA Bash (`cat ...`) -> nudge YOK (gurultu = olu hook)
  A4 FP capasi     `> /dev/null` / uzantisiz hedef -> yol CIKARILMAZ
  A5 FP capasi     Edit payload'i AYNEN calisir (regresyon yok)
  A6 ⭐ SINIR       matcher `Bash` icerir YA DA kaynak SINIR-NOTU tasir
  B1               gate stderr sondasi KABLOLU (AST) ve BOS DONMUYOR
  B2 ⭐ SINIR       sonda DETERMINISTIK (dedup marker'a takilip sessizce bosalmiyor)
  M1..M4           fix'i sok -> korpus KIRMIZI olmali (M4 = genislemenin POZITIF KONTROLU)

Kosum: python tests/fixtures/hook_bash_ve_stderr_kapsami/run.py     (exit 0 = PASS)
"""
from __future__ import annotations

import ast
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

KOK = Path(__file__).resolve().parents[3]
HOOK = KOK / "scripts" / "hooks" / "post_validate.py"
GATE = KOK / "scripts" / "validators" / "check_hook_injected_paths.py"
SETTINGS = KOK / "claude" / "settings.template.json"


def _kum() -> Path:
    d = Path(tempfile.mkdtemp(prefix="k8_"))
    (d / "project.yaml").write_text(
        "sap_profile: s4_private\nsource_root: SOURCE_CODES\nmaster_language: TR\n",
        encoding="utf-8")
    return d


def _hook_kos(hook: Path, payload: dict, kum: Path) -> tuple[int, str]:
    r = subprocess.run([sys.executable, str(hook)], input=json.dumps(payload),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=600,
                       env=dict(os.environ, CLAUDE_PROJECT_DIR=str(kum),
                                PYTHONIOENCODING="utf-8"))
    return r.returncode, (r.stderr or "") + (r.stdout or "")


def _bash(komut: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": komut}}


def senaryolar(hook: Path, gate: Path) -> list[tuple[str, bool, str]]:
    r: list[tuple[str, bool, str]] = []

    def ekle(ad: str, ok: bool, detay: str = "") -> None:
        r.append((ad, ok, detay))

    # --- A: Bash tetigi -----------------------------------------------------
    kum = _kum()
    try:
        kd = kum / "docs" / "KD-ORNEK.md"
        kd.parent.mkdir(parents=True, exist_ok=True)
        kd.write_text("# ornek\n", encoding="utf-8")
        rc, out = _hook_kos(hook, _bash(f"sed -i 's/a/b/' {kd}"), kum)
        ekle("A1 ⭐ `sed -i ... KD-*.md` -> nudge ATESLER (once: HIC atesle(n)mezdi)",
             rc == 2 and "doc-checklist" in out, f"rc={rc} · {out.strip()[:200]!r}")
    finally:
        shutil.rmtree(kum, ignore_errors=True)

    kum = _kum()
    try:
        # ⚠ Bu vektor YONLENDIRME cikarimini olcer, "hangi nudge atesler"i DEGIL.
        #    Ilk surumde bir FS dosyasi kullanilmisti ve A2 FAIL verdi — sebep Bash
        #    cikarimi degildi: FS nudge'i o yol icin Edit payload'iyla da atesle(n)miyor.
        #    Yani capa YANLIS SEYI olcuyordu. Nudge'i ATESLEDIGI BILINEN bir doku
        #    (KD) kullanmak, degiskeni tek basina birakir: fark YALNIZ `sed -i` vs `>`.
        kd = kum / "docs" / "KD-ORNEK2.md"
        kd.parent.mkdir(parents=True, exist_ok=True)
        kd.write_text("# ornek\n", encoding="utf-8")
        rc, out = _hook_kos(hook, _bash(f"cat <<'EOF' > {kd}\nicerik\nEOF"), kum)
        ekle("A2 `> dosya` YONLENDIRMESI de duzenlemedir -> nudge ATESLER",
             rc == 2 and "doc-checklist" in out, f"rc={rc} · {out.strip()[:200]!r}")
    finally:
        shutil.rmtree(kum, ignore_errors=True)

    kum = _kum()
    try:
        rc, out = _hook_kos(hook, _bash("cat docs/KD-ORNEK.md | head -20"), kum)
        ekle("A3 FP capasi: salt-OKUMA Bash -> nudge YOK (her komutta gurultu = olu hook)",
             rc == 0 and not out.strip(), f"rc={rc} · {out.strip()[:200]!r}")
    finally:
        shutil.rmtree(kum, ignore_errors=True)

    kum = _kum()
    try:
        rc1, o1 = _hook_kos(hook, _bash("python x.py > /dev/null 2>&1"), kum)
        rc2, o2 = _hook_kos(hook, _bash("echo merhaba > ciktilar"), kum)
        ekle("A4 FP capasi: `/dev/null` ve UZANTISIZ hedef -> yol CIKARILMAZ",
             rc1 == 0 and rc2 == 0, f"devnull rc={rc1} · uzantisiz rc={rc2}")
    finally:
        shutil.rmtree(kum, ignore_errors=True)

    kum = _kum()
    try:
        kd = kum / "docs" / "KD-ORNEK.md"
        kd.parent.mkdir(parents=True, exist_ok=True)
        kd.write_text("# ornek\n", encoding="utf-8")
        rc, out = _hook_kos(hook, {"tool_name": "Edit",
                                   "tool_input": {"file_path": str(kd)}}, kum)
        ekle("A5 FP capasi: Edit payload'i AYNEN calisir (regresyon yok)",
             rc == 2 and "doc-checklist" in out, f"rc={rc} · {out.strip()[:200]!r}")
    finally:
        shutil.rmtree(kum, ignore_errors=True)

    # A6 ⭐ SINIR: kablolama YA kurulmus YA DA acikca not edilmis olmali
    kaynak = hook.read_text(encoding="utf-8")
    bash_kayitli = False
    try:
        d = json.loads(SETTINGS.read_text(encoding="utf-8"))
        for grup in d.get("hooks", {}).get("PostToolUse", []):
            if "post_validate" in json.dumps(grup) and "Bash" in (grup.get("matcher") or ""):
                bash_kayitli = True
    except Exception:
        pass
    ekle("A6 ⭐ SINIR: matcher `Bash` icerir YA DA kaynak `SINIR-NOTU` tasir "
         "(ikisi de yoksa: kimse kablolamamis + not silinmis = sessiz olu kod)",
         bash_kayitli or "SINIR-NOTU" in kaynak,
         f"matcher_bash={bash_kayitli} · not_var={'SINIR-NOTU' in kaynak}")

    # --- B: gate kapsami ----------------------------------------------------
    gate_src = gate.read_text(encoding="utf-8")
    agac = ast.parse(gate_src)
    sonda_tanimli = any(isinstance(n, ast.FunctionDef) and n.name == "_stderr_ciktisi"
                        for n in ast.walk(agac))
    sonda_cagrili = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                        and n.func.id == "_stderr_ciktisi" for n in ast.walk(agac))
    ekle("B1a KABLOLAMA (AST): `_stderr_ciktisi` hem TANIMLI hem CAGRILI "
         "(tanimli-ama-cagrilmayan = olu kapsam)",
         sonda_tanimli and sonda_cagrili,
         f"tanimli={sonda_tanimli} cagrili={sonda_cagrili}")

    # B1b/B2: gate'in KENDI CIKTISINDAN olc — fonksiyonu tek basina cagirmak YETMEZ.
    # ⚠ Ilk surumde B vektorleri `_stderr_ciktisi`yi DOGRUDAN cagiriyordu; sondayi
    #   main()'de OLU bir donguye baglayan mutasyon (M3) KACTI: fonksiyon calisiyordu,
    #   ama gate onu kullanmiyordu. Klasik "kod != kablolama".
    # ⚠ SABIT SAYI YOK (bayatlar): olcut KENDINE GORELIDIR — stderr sondasi kapaliyken
    #   ve acikken gate'in raporladigi TOPLAM kiyaslanir. Fark yoksa sonda olu demektir.
    import contextlib
    import importlib.util
    import io
    import re as _re

    spec = importlib.util.spec_from_file_location("_k8_gate", gate)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_k8_gate"] = mod

    def _toplam(m) -> int:
        tampon = io.StringIO()
        with contextlib.redirect_stdout(tampon):
            m.main()
        eslesme = _re.search(r"enjekte edilen (\d+)", tampon.getvalue())
        return int(eslesme.group(1)) if eslesme else 0

    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        eski_hooklar = getattr(mod, "STDERR_HOOKLAR", ())
        mod.STDERR_HOOKLAR = ()
        sondasiz = _toplam(mod)
        mod.STDERR_HOOKLAR = eski_hooklar
        sondali_1 = _toplam(mod)
        sondali_2 = _toplam(mod)
        ekle("B1b KABLOLAMA: stderr sondasi gate'in TOPLAMINA katkida bulunuyor "
             "(sondasiz < sondali) — fonksiyon calisiyor ama main() kullanmiyor DEGIL",
             sondali_1 > sondasiz, f"sondasiz={sondasiz} sondali={sondali_1}")
        ekle("B2 ⭐ SINIR: sonda DETERMINISTIK — ardisik iki kosum AYNI toplami verir "
             "(dedup marker'a takilip sessizce bosalmiyor)",
             sondali_1 == sondali_2 and sondali_2 > 0,
             f"1.kosum={sondali_1} · 2.kosum={sondali_2}")
    finally:
        sys.modules.pop("_k8_gate", None)
    return r


MUTASYONLAR = [
    ("M1 ⭐ Bash yol cikarimini sok (fix oncesi hali)", "hook",
     lambda s: s.replace(
         '    if not path and (data.get("tool_name") or "") == "Bash":\n'
         "        path = _bash_duzenlenen_yol(tool_input)\n", "")),
    ("M2 Bash cikarimini ACGOZLU yap (salt-okuma komutlarindan da yol uret)", "hook",
     lambda s: s.replace(
         '    komut = tool_input.get("command") or ""\n',
         '    komut = tool_input.get("command") or ""\n'
         '    import re as _re\n'
         '    _m = _re.search(r"[\\w/\\-.]+\\.md", komut)\n'
         '    if _m:\n        return _m.group(0)\n')),
    ("M3 gate'in stderr sondasini sok (kapsam eski haline doner)", "gate",
     lambda s: s.replace('    for _hook in STDERR_HOOKLAR:', '    for _hook in ():')),
    # ⭐ M4 = KAPSAM GENISLEMESININ POZITIF KONTROLU. Sayi artisi ("4 -> 8 yol")
    #    "yakaliyor" DEMEK DEGILDIR: gate yollari sayip hicbirini dogrulamiyor da
    #    olabilirdi. Bu mutasyon bir nudge'a CIPLAK `playbook/...md` koyar (2026-08-17'de
    #    gercekte olan kusurun birebir hali) ve gate'in FAIL vermesini bekler.
    ("M4 ⭐POZ.KONTROL: nudge'a CIPLAK `playbook/...md` koy -> gate FAIL vermeli", "hook",
     lambda s: s.replace(
         '"+ §2.3 · playbook/checklists/doc-checklist.md §B DOC-FS-01…07 (TS için §C). "',
         '"+ §2.3 · playbook/checklists/doc-checklist.md §B DOC-FS-01…07 (TS için §C). "\n'
         '                             "playbook/ciplak-yol-ornegi.md "')),
]


def _m4_gate_karari(mutant_hook: Path) -> tuple[bool, list]:
    """M4: GERCEK gate'i, MUTANT hook'u yoklayacak sekilde in-process kos.

    Gate `STDERR_HOOKLAR` icindeki ADLARI `scripts/hooks/<ad>.py` diye cozer; adi
    mutant kardese cevirmek gercek dosyaya dokunmadan ayni yolu olcer.
    """
    import contextlib
    import importlib.util
    import io

    spec = importlib.util.spec_from_file_location("_k8_gate_m4", GATE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_k8_gate_m4"] = mod
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        mod.STDERR_HOOKLAR = (mutant_hook.stem,)
        tampon = io.StringIO()
        with contextlib.redirect_stdout(tampon):
            rc = mod.main()
        cikti = tampon.getvalue()
        return (rc == 1 and "ciplak-yol-ornegi.md" in cikti), ["gate rc=%s" % rc]
    finally:
        sys.modules.pop("_k8_gate_m4", None)


def _gate_kos(gate: Path) -> tuple[int, str]:
    r = subprocess.run([sys.executable, str(gate)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900,
                       env=dict(os.environ, CLAUDE_PROJECT_DIR=str(KOK),
                                PYTHONIOENCODING="utf-8"))
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main() -> int:
    print("=" * 78)
    print("hook_bash_ve_stderr_kapsami — K8①② tetik + kapsam")
    print("=" * 78)
    for eksik in (HOOK, GATE):
        if not eksik.is_file():
            print(f"FAIL — dosya yok: {eksik}")
            return 1

    ham = {"hook": HOOK.read_text(encoding="utf-8"),
           "gate": GATE.read_text(encoding="utf-8")}
    # ⛔ 2026-08-20 DERSI: mutasyon GERCEK dosyaya YAZILMAZ. Ilk surum post_validate.py
    #    ve gate'i yerinde eziyordu; art arda kosumlarda kalinti BIRIKTI (ciplak yol
    #    satiri iki kez eklendi) ve KOMSU korpus `fs_docstd` bu kalintiyi gercek bir
    #    ihlal sanip FAIL verdi. Mutant artik KARDES bir dosyada yasar (`_mutant_*.py`),
    #    gercek dosyalar korpus boyunca SALT-OKUNURDUR (F1 vektoru civiler).
    yol = {"hook": HOOK, "gate": GATE}
    kardes = {"hook": HOOK.with_name("_mutant_post_validate.py"),
              "gate": GATE.with_name("_mutant_chip.py")}

    sonuc = senaryolar(HOOK, GATE)
    kirik = [(a, d) for a, ok, d in sonuc if not ok]
    for ad, ok, detay in sonuc:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok:
            print("         gorulen: %s" % detay)
    print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

    print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
    mut_kirik, yama_kirik = [], []
    for ad, hedef, mut in MUTASYONLAR:
        bozuk = mut(ham[hedef])
        if bozuk == ham[hedef]:
            print("  [YAMA TUTMADI] %s" % ad)
            yama_kirik.append(ad)
            continue
        mutant = kardes[hedef]
        try:
            mutant.write_text(bozuk, encoding="utf-8")
            if ad.startswith("M4"):
                # M4 senaryo listesiyle degil, GATE'in KENDI kararayla olculur:
                # "nudge'a ciplak yol kondu -> gate FAIL veriyor mu?"
                # Gate MUTANT hook'u yoklasin diye STDERR_HOOKLAR in-process degistirilir;
                # gercek `post_validate.py` DOKUNULMADAN kalir.
                yakalandi, kacan = _m4_gate_karari(mutant)
            elif hedef == "hook":
                m_res = senaryolar(mutant, GATE)
                yakalandi = any(not ok for _, ok, _ in m_res)
                kacan = [a for a, ok, _ in m_res if not ok]
            else:
                m_res = senaryolar(HOOK, mutant)
                yakalandi = any(not ok for _, ok, _ in m_res)
                kacan = [a for a, ok, _ in m_res if not ok]
        except BaseException as e:  # noqa: BLE001
            yakalandi, kacan = False, []
            print("  [KURULAMADI] %s -> %s: %s" % (ad, type(e).__name__, e))
        finally:
            mutant.unlink(missing_ok=True)
        print("  [%s] %s" % ("YAKALANDI" if yakalandi else "KACTI", ad))
        if yakalandi:
            print("         kiran senaryo(lar): %s" % ", ".join(kacan[:3]))
        else:
            mut_kirik.append(ad)

    # F1 ⭐ IZOLASYON KANITI: korpus GERCEK dosyalari degistirmemis olmali.
    for k, p in yol.items():
        if p.read_text(encoding="utf-8") != ham[k]:
            print(f"FAIL — F1: {p} korpus tarafindan DEGISTIRILDI (izolasyon kirik)")
            return 1
    for k, p in kardes.items():
        if p.exists():
            print(f"FAIL — F1: mutant kardes dosya kaldi: {p}")
            return 1
    print("  [PASS] F1 ⭐ izolasyon: gercek post_validate.py/gate DEGISMEDI, "
          "mutant kardes dosya KALMADI")

    print("\n" + "=" * 78)
    if kirik or mut_kirik or yama_kirik:
        if kirik:
            print("FAIL — senaryo: %s" % ", ".join(a for a, _ in kirik))
        if mut_kirik:
            print("FAIL — mutasyon KACTI: %s" % ", ".join(mut_kirik))
        if yama_kirik:
            print("FAIL — mutasyon yamasi kaynaga UYMADI: %s" % ", ".join(yama_kirik))
        return 1
    print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(MUTASYONLAR)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
