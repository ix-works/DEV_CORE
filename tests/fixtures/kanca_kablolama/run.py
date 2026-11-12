#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kanca_kablolama — Q406 / Q408 İP-2: ix_doctor 4h (ad düzeyi kanca kablolaması) · 4i (tüm
kancalara gerçek giriş noktasından smoke) · 4j (fail-open recall_inject sağlığı) +
`team_setup --tazele-settings` (yalnız EKSİK şablon kancasını ekler) + parity_probe satırı.

KUSUR (core 8565c9d, ölçüldü): şablon 16 kanca / 19 bağlantı taşır; ix_doctor yalnız 2 kancayı
koşuyor (4d), yalnız pre_tool_guard'ın matcher'ına bakıyordu (4f); 4a tüm dosyayı tek imzayla
kıyasladığı için `recall_inject`'in düşmesi ad vermeyen "template'ten SAPMIŞ" WARN'ı üretiyordu
— zararsız proje ekiyle AYNI satır. settings.json için onarım yolu yoktu ("elle birleştir").

K1 MATRİSİ (Q408 KAPANIŞ KOŞULU; boş dizin DEĞİL — eski durumlu sahte "mevcut proje", gerçek
`core` bağı, gerçek `scripts/hook_shim.py`, kancalar gerçek alt süreçte):
  M1  2026-08-01 öncesi settings (recall_inject + intake_triage YOK)
      M1a önce: 4h FAIL + iki kanca ADIYLA + `--tazele-settings` + §6a ①
      M1b önce: 4j FAIL "kablolu DEĞİL" ama kanca kodu öneri DÖNDÜRDÜ (iki eksen ayrı)
      M1c onarım: settings_tazele → FARK RAPORU yazımdan ÖNCE · yedek · EKLENDİ
      M1d sonra: 4h PASS 19/19 · 4i PASS · 4j PASS
      M1e ikinci koşum: DOKUNULMADI + bayt-eş (idempotent)
      M1f GERÇEK CLI: `team_setup.py --project <kum> --tazele-settings` alt süreç rc 0 + eksik 0
  M2  proje-özel kanca + allow + env eki, pre_compact eksik (2026-08-22 ters yön vakası)
      M2a önce: FAIL pre_compact ADIYLA + proje eki BİLGİ olarak aynı satırda
      M2b yalnız ek (eksik yok): tek satır PASS (WARN DEĞİL) + "proje eki"
      M2c onarım: proje eki/allow/env KORUNUR, pre_compact eklenir, 4i PASS (ek kanca çalışıyor)
      M2d eşleyici farklı: WARN (FAIL değil) · onarım dokunmaz (bayt-eş) · "DOKUNULMAYACAK"
      V1  doğrulayıcı: kayıplı ekleme (monkeypatch) → FAIL "DOĞRULANAMADI" + yedekten geri, bayt-eş
  M3  recall: M3a indeks YOK → kanca tazeler → PASS "önce YOK" · M3b bozuk JSON (taze mtime) →
      FAIL BOZUK + build_recall_index onarımı (GERÇEK alt süreç) → PASS · M3c bayat → PASS "önce
      BAYAT" · M3d kayıt var ama öneri dönmüyor → FAIL "öneri DÖNDÜRMEDİ" (exit 0 kanıt değil)
  M5  M5a yorumlayıcı başlamıyor (stub, rc 49) → FAIL "BAŞLAMIYOR" §6a ② + kod sys.executable ile
      ölçüldü · M5b projede kablolu ama çekirdekte olmayan kanca → FAIL §6a ② · M5c kanca çöküyor
      (PYTHONPATH'e zehirli `datetime`) → FAIL "ÇÖKTÜ" §6a ③ · M5d fail-open SESSİZ (log yolu
      dizin) → FAIL "SESSİZ kaldı" §6a ③
  DÜZELTME TURU (bug-gate PR #429, 2026-11-12):
  U5  Ö1 kanca_adi: tırnaklı kabuk adı · `hook_shim.py --x ad` = `--x` (shim argv[1]) · yönlendirme
  U6  Ö1 tırnaklı biçimde kablolu recall_inject EKSİK DEĞİL · tazeleme İKİNCİ kopya EKLEMEZ
  U7  Ö1 emniyet ağı: adı ayrıştırılamayan (`?…`) biçim → biçim farkı, EKLENMEZ · U7b 4h WARN +
      özet "tamamı projede" DEMEZ (F7)
  U10 F7 adı ayrıştırılmış ama BAŞKA adı koşturan kanca (`--flag recall_inject` · `pull_before_edit
      infra_write_guard`) → EKSİK + eklenir (shim yalnız argv[1]'i koşturur) · U10b 4h FAIL ADIYLA
  U11 F7 kontrol (fazla daraltma): kabuk zincirinde İKİNCİ shim çağrısı (`… a && … recall_inject`)
      gerçekten koşar → biçim farkı, EKLENMEZ (çift koşum yok)
  J1  F7 4j: recall_inject yalnız tanınmayan biçimde → FAIL, onarım `--tazele-settings` DEĞİL (§6a ②)
  Y1  F8 4i PASS özeti PATH sınırını taşır (`--layer 4` 1g satırını basmaz)
  U8  Ö2 birleşik eşleyici (Bash|…|Edit|…|NotebookEdit) ⊇ şablon → KAPSANAN, eksik 0, eklenen 0
  U9  Ö2 kontrol: kısmi kapsama → kapsanan + eşleyici farkı + YALNIZ kapsanmayan EKSİK eklenir
  M6  Ö2 4h birleşik eşleyicide FAIL YOK + tazeleme bayt-eş "KAPSANIYOR"
  R1  Ö3 ilk kayıt dönmüyor, ikincisi dönüyor → 4j PASS (eski kod: tek kayıt → FAIL)
  D1  Ö4 `disableAllHooks: true` → 4h FAIL · D2 `"true"` dizgesi → 4h WARN "bool DEĞİL … ÖLÇÜLMEDİ"
  L1  F2a settings.local.json disableAllHooks + kanca → WARN (FAIL DEĞİL)
  S2  F2c shim dışı proje kancası → 4i SKIP satırı + özette "ÖLÇÜLMEDİ … shim dışı 1"
  F3  settings D7 onarım metni: ix_doctor 4a + team_setup sablon_sapmasi `--tazele-settings`
      der, "template'ten yenile" DEMEZ
  I1  F1 smoke log satırı inspector A1'i SUSTURMAZ (gerçek smoke + gerçek logger + inspector)
      I2 kontrol: gerçek oturum satırı A1'i susturur (süzgeç fazla maskelemez)
      I3 session_start `_oturum_olcumu` smoke satırını oturum SAYMAZ
  U1-U4 utils.kanca_kablolari birim · T1 şablonun her kancasının smoke örneği VAR ·
  W1 katman4 üç kolu ÇAĞIRIR (AST) · C3 ÜÇÜNCÜ BAĞLAM: kabuk biçimli settings (ad + yorumlayıcı
  komut dizgesinden) · P1 parity_probe `kanca_sablondan_eksik` (GERÇEK alt süreç, --no-doctor)

MUTASYON (çapa tam 1 kez bulunmazsa exit 2; ilan edilen vektörler düşmezse SAPMA exit 2):
  --mutasyon-ad-yok          4h eksik dalı ölü                     → M1a · M2a
  --mutasyon-ek-warn         proje eki WARN olur                   → M2b
  --mutasyon-ezerek-tazele   eksikleri_ekle hooks'u şablonla EZER  → U3 · M2c
  --mutasyon-dogrulama-yok   settings_tazele doğrulaması kapalı    → V1
  --mutasyon-sys-executable  4i settings yorumlayıcısını yok sayar → M5a
  --mutasyon-exit0-yeter     4i log içerik sondası kapalı          → M5d
  --mutasyon-traceback-kor   4i Traceback ayrımı kapalı            → M5c
  --mutasyon-recall-exit0    4j exit 0'ı öneri sayar               → M3d
  --mutasyon-kablosuz        katman4 4h'yi çağırmaz                → W1
  --mutasyon-tirnak-kor      kanca_adi tırnak/shlex ayrıştırmaz    → U5
  --mutasyon-ham-ag-yok      Ö1 emniyet ağı kapalı                 → U7
  --mutasyon-kapsama-yok     Ö2 ⊇ kapsama kapalı                   → U8 · M6
  --mutasyon-tek-kayit       Ö3 4j yalnız 1 kayıt dener            → R1
  --mutasyon-kapali-kor      hepsi_kapali hep False                → D1
  --mutasyon-dizge-kor       bool dışı disableAllHooks görülmez    → D2
  --mutasyon-smoke-sayilir   inspector smoke satırını sayar        → I1
  --mutasyon-local-kor       4h settings.local.json'a bakmaz       → L1
  --mutasyon-shimdisi-sessiz 4i shim dışı SKIP satırı yok          → S2
  --mutasyon-genel-sapma     settings çifti eski genel metne döner → F3
  --mutasyon-ag-taninana     F7 ağ adı tanınan kancaya da bakar    → U10 · U10b
  --mutasyon-zincir-kor      F7 zincirdeki 2. shim çağrısı görülmez → U11
  --mutasyon-bicim-pass      F7 biçim farkında özet PASS "tamamı"  → U7b
  --mutasyon-recall-bicim-kor F7 4j tanınmayan biçimi görmez       → J1
  --mutasyon-path-siniri-yok F8 4i PASS özetinde PATH sınırı yok   → Y1
TABAN (eski kod, KIRMIZI beklenir): --kaynak <ix_doctor.py> · --kaynak-inspector <inspector.py> ·
  --kaynak-kk <utils/kanca_kablolari.py>

Çıkış: 0 hepsi beklendiği gibi · 1 sapma (mutasyonda: ilan edilenler DÜŞTÜ) · 2 KURULAMADI/SAPMA
"""
from __future__ import annotations

import ast
import contextlib
import copy
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import types
from collections import Counter
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DOCTOR = REPO / "scripts" / "ix_doctor.py"
TEAM = REPO / "scripts" / "team_setup.py"
KKYOL = REPO / "scripts" / "utils" / "kanca_kablolari.py"
DRIFT = REPO / "scripts" / "utils" / "drift_imzasi.py"
INSP = REPO / "scripts" / "inspector.py"
SSTART = REPO / "scripts" / "hooks" / "session_start.py"
SABLON = REPO / "claude" / "settings.template.json"
WINDOWS = os.name == "nt"

ILAN = {
    "--mutasyon-ad-yok": {"M1a", "M2a"},
    "--mutasyon-ek-warn": {"M2b"},
    "--mutasyon-ezerek-tazele": {"U3", "M2c"},
    "--mutasyon-dogrulama-yok": {"V1"},
    "--mutasyon-sys-executable": {"M5a"},
    "--mutasyon-exit0-yeter": {"M5d"},
    "--mutasyon-traceback-kor": {"M5c"},
    "--mutasyon-recall-exit0": {"M3d"},
    "--mutasyon-kablosuz": {"W1"},
    "--mutasyon-tirnak-kor": {"U5"},
    "--mutasyon-ham-ag-yok": {"U7"},
    "--mutasyon-kapsama-yok": {"U8", "M6"},
    "--mutasyon-tek-kayit": {"R1"},
    "--mutasyon-kapali-kor": {"D1"},
    "--mutasyon-dizge-kor": {"D2"},
    "--mutasyon-smoke-sayilir": {"I1"},
    "--mutasyon-local-kor": {"L1"},
    "--mutasyon-shimdisi-sessiz": {"S2"},
    "--mutasyon-genel-sapma": {"F3"},
    "--mutasyon-ag-taninana": {"U10", "U10b"},
    "--mutasyon-zincir-kor": {"U11"},
    "--mutasyon-bicim-pass": {"U7b"},
    "--mutasyon-recall-bicim-kor": {"J1"},
    "--mutasyon-path-siniri-yok": {"Y1"},
}
GECERLI_KIP = ("--mutasyon-ad-yok", "--mutasyon-ek-warn", "--mutasyon-ezerek-tazele",
               "--mutasyon-dogrulama-yok", "--mutasyon-sys-executable", "--mutasyon-exit0-yeter",
               "--mutasyon-traceback-kor", "--mutasyon-recall-exit0", "--mutasyon-kablosuz",
               "--mutasyon-tirnak-kor", "--mutasyon-ham-ag-yok", "--mutasyon-kapsama-yok",
               "--mutasyon-tek-kayit", "--mutasyon-kapali-kor", "--mutasyon-dizge-kor",
               "--mutasyon-smoke-sayilir", "--mutasyon-local-kor", "--mutasyon-shimdisi-sessiz",
               "--mutasyon-genel-sapma", "--mutasyon-ag-taninana", "--mutasyon-zincir-kor",
               "--mutasyon-bicim-pass",
               "--mutasyon-recall-bicim-kor", "--mutasyon-path-siniri-yok")
KIP: str | None = None
TABAN: Path | None = None
TABAN_INSP: Path | None = None
TABAN_KK: Path | None = None
_a = sys.argv[1:]
while _a:
    x = _a.pop(0)
    if x == "--kaynak" and _a:
        TABAN = Path(_a.pop(0)).resolve()
    elif x == "--kaynak-inspector" and _a:
        TABAN_INSP = Path(_a.pop(0)).resolve()
    elif x == "--kaynak-kk" and _a:
        TABAN_KK = Path(_a.pop(0)).resolve()
    elif x in GECERLI_KIP and KIP is None:
        KIP = x
    else:
        print(f"[DURDU] bilinmeyen/ikinci arguman: {x!r} — gecerli: {list(GECERLI_KIP)} + --kaynak")
        sys.exit(2)

SONUC: dict[str, bool] = {}


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    kimlik = ad.split()[0]
    SONUC[kimlik] = SONUC.get(kimlik, True) and bool(kosul)
    print(f"  [{'PASS' if kosul else 'FAIL'}] {ad}" + (f"  -- {detay[:700]}" if not kosul and detay else ""))


def _degistir(metin: str, eski: str, yeni: str, ad: str) -> str:
    n = metin.count(eski)
    if n != 1:
        print(f"[DURDU] KURULAMADI: {ad} capasi {n} kez bulundu (1 bekleniyordu): {eski[:80]!r}")
        sys.exit(2)
    return metin.replace(eski, yeni)


# ── mutasyonlu kaynaklar (GERÇEK dosyaya YAZILMAZ; bellekte derlenir) ──────────
def _kaynak_doctor() -> str:
    if TABAN is not None:
        return TABAN.read_text(encoding="utf-8")
    m = DOCTOR.read_text(encoding="utf-8")
    if KIP == "--mutasyon-ad-yok":
        m = _degistir(m, '    if k["eksik"]:\n        r.append((FAIL, f"kanca kablolaması: şablonun',
                      '    if False:\n        r.append((FAIL, f"kanca kablolaması: şablonun', KIP)
    if KIP == "--mutasyon-ek-warn":
        m = _degistir(m, '        r.append((PASS, f"kanca kablolaması: şablonun {n} bağlantısının',
                      '        r.append((WARN if k["ek"] else PASS, f"kanca kablolaması: şablonun {n} bağlantısının', KIP)
    if KIP == "--mutasyon-sys-executable":
        m = _degistir(m, "    yol, ysatir, ynot = _smoke_yorumlayici(p if p is not None else s, KK)\n",
                      '    yol, ysatir, ynot = None, None, "sys.executable"\n', KIP)
    if KIP == "--mutasyon-exit0-yeter":
        m = _degistir(m, '    if beklenti and beklenti[0] == "log":\n', "    if False:\n", KIP)
    if KIP == "--mutasyon-traceback-kor":
        m = _degistir(m, '    if "Traceback (most recent call last)" in out:\n', "    if False:\n", KIP)
    if KIP == "--mutasyon-recall-exit0":
        m = _degistir(m, '    dondu = "[JIT-RECALL]" in out and baslik[:30] in out\n',
                      "    dondu = rc == 0\n", KIP)
    if KIP == "--mutasyon-kablosuz":
        m = _degistir(m, "    r.extend(_kanca_kablolama())\n", "", KIP)
    if KIP == "--mutasyon-tek-kayit":
        m = _degistir(m, "_RECALL_DENEME = 3\n", "_RECALL_DENEME = 1\n", KIP)
    if KIP == "--mutasyon-local-kor":
        m = _degistir(m, '    r.extend(_yerel_ayar_kancalari(ayar.with_name("settings.local.json"), KK))\n',
                      "", KIP)
    if KIP == "--mutasyon-shimdisi-sessiz":
        m = _degistir(m, "    if shim_disi:\n        # F2c", "    if False:\n        # F2c", KIP)
    if KIP == "--mutasyon-bicim-pass":
        m = _degistir(m, '    if not k["eksik"] and not KK.hepsi_kapali(p) and k["bicim_farki"]:\n',
                      "    if False:\n", KIP)
    if KIP == "--mutasyon-recall-bicim-kor":
        m = _degistir(m, '                kablolu = "bicim"\n', "                pass\n", KIP)
    if KIP == "--mutasyon-path-siniri-yok":
        m = _degistir(m, 'else f" [{_PATH_SINIRI}]"\n', 'else ""\n', KIP)
    return m


def _kaynak_kk() -> str:
    if TABAN_KK is not None:
        return TABAN_KK.read_text(encoding="utf-8")
    m = KKYOL.read_text(encoding="utf-8")
    if KIP == "--mutasyon-ag-taninana":
        m = _degistir(m, "            if shim_kancasi_mi(kanca_adi(kanca)):\n                # shim yalnız",
                      "            if False:\n                # shim yalnız", KIP)
    if KIP == "--mutasyon-zincir-kor":
        m = _degistir(m, 'if tk[i].lower().endswith("hook_shim.py")][1:]:\n',
                      'if tk[i].lower().endswith("hook_shim.py")][0:0]:\n', KIP)
    if KIP == "--mutasyon-ezerek-tazele":
        m = _degistir(m, '    yeni = copy.deepcopy(proje)\n    hooks = yeni.setdefault("hooks", {})\n',
                      '    yeni = copy.deepcopy(proje)\n    yeni["hooks"] = copy.deepcopy(sablon.get("hooks") or {})\n'
                      '    hooks = yeni.setdefault("hooks", {})\n', KIP)
    if KIP == "--mutasyon-tirnak-kor":
        m = _degistir(m, "        kalan = _tokenler(komut[m.end():].lstrip(_TIRNAK))\n",
                      "        kalan = komut[m.end():].split()\n", KIP)
    if KIP == "--mutasyon-ham-ag-yok":
        m = _degistir(m, "        ham = _ham_iceren(proje, b[0], b[2])\n", "        ham = None\n", KIP)
    if KIP == "--mutasyon-kapsama-yok":
        m = _degistir(m, "    hedef = _eslik_kumesi(eslik)\n    birlesim: set = set()\n",
                      "    return False\n", KIP)
    if KIP == "--mutasyon-kapali-kor":
        m = _degistir(m, '    return isinstance(veri, dict) and veri.get("disableAllHooks") is True\n',
                      "    return False\n", KIP)
    if KIP == "--mutasyon-dizge-kor":
        m = _degistir(m, "    return None if isinstance(d, bool) else d\n", "    return None\n", KIP)
    return m


def _kaynak_drift() -> str:
    m = DRIFT.read_text(encoding="utf-8")
    if KIP == "--mutasyon-genel-sapma":
        m = _degistir(m, "     _SETTINGS_SAPMA),\n", "     _GENEL_SAPMA),\n", KIP)
    return m


def _kaynak_insp() -> str:
    if TABAN_INSP is not None:
        return TABAN_INSP.read_text(encoding="utf-8")
    m = INSP.read_text(encoding="utf-8")
    if KIP == "--mutasyon-smoke-sayilir":
        m = _degistir(m, "        if len(p) >= 2 and p[1] == SMOKE_NEDENI:\n            continue\n", "", KIP)
    return m


def _kaynak_team() -> str:
    m = TEAM.read_text(encoding="utf-8")
    if KIP == "--mutasyon-dogrulama-yok":
        m = _degistir(m, '                "kanca dışı alanlar değişti" if not dis_esit else "")\n',
                      '                "kanca dışı alanlar değişti" if not dis_esit else "")\n        hata = ""\n',
                      KIP)
    return m


def _modul(ad: str, yol: Path, kaynak: str) -> types.ModuleType:
    m = types.ModuleType(ad)
    m.__file__ = str(yol)
    exec(compile(kaynak, str(yol), "exec"), m.__dict__)
    return m


# ── kum ──────────────────────────────────────────────────────────────────────
def _bag(link: Path, hedef: Path) -> None:
    """Windows'ta junction, POSIX'te dizin symlink'i (d7_drift_imzasi deseni)."""
    if WINDOWS:
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(hedef)],
                       capture_output=True, text=True, timeout=60)
    else:
        os.symlink(hedef, link, target_is_directory=True)


def _bag_mi(p: Path) -> bool:
    if p.is_symlink():
        return True
    try:
        os.readlink(p)
        return True
    except (OSError, ValueError):
        return False


def _sil(kok: Path) -> None:
    """ÖNCE bağlar (hedefe dokunmadan), SONRA ağaç — rmtree bağa girerse HEDEFİ siler."""
    for dp, dn, _fn in os.walk(kok):
        for d in list(dn):
            p = Path(dp) / d
            if _bag_mi(p):
                try:
                    p.unlink() if p.is_symlink() else os.rmdir(p)
                except OSError:
                    pass
                dn.remove(d)

    def _ac(func, path, _exc):  # noqa: ANN001
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass
    kw = {"onexc": _ac} if sys.version_info >= (3, 12) else {"onerror": _ac}
    shutil.rmtree(kok, **kw)  # type: ignore[arg-type]


KOK = Path(tempfile.mkdtemp(prefix="kanca_kbl_"))
T = json.loads(SABLON.read_text(encoding="utf-8"))


def _shim(ad: str) -> dict:
    return {"type": "command", "command": "python",
            "args": ["${CLAUDE_PROJECT_DIR}/scripts/hook_shim.py", ad]}


def kum(ad: str, ayar: dict, crlf: bool = False) -> Path:
    p = KOK / ad
    (p / ".claude").mkdir(parents=True)
    (p / "scripts").mkdir()
    _bag(p / "core", REPO)
    if not (p / "core" / "scripts" / "hooks").is_dir():
        print(f"[DURDU] KURULAMADI: core bağı kurulamadı ({p / 'core'})")
        sys.exit(2)
    shutil.copyfile(REPO / "claude" / "hook_shim.template.py", p / "scripts" / "hook_shim.py")
    metin = json.dumps(ayar, indent=2, ensure_ascii=False) + "\n"
    (p / ".claude" / "settings.json").write_bytes(
        (metin.replace("\n", "\r\n") if crlf else metin).encode("utf-8"))
    return p


def _m1(t: dict) -> dict:
    """2026-08-01 öncesi: recall_inject bloğu + intake_triage girdisi YOK."""
    d = copy.deepcopy(t)
    ups = d["hooks"]["UserPromptSubmit"]
    d["hooks"]["UserPromptSubmit"] = [b for b in ups if "recall_inject" not in json.dumps(b)]
    for b in d["hooks"]["UserPromptSubmit"]:
        b["hooks"] = [h for h in b["hooks"] if "intake_triage" not in json.dumps(h)]
    return d


def _ekli(t: dict) -> dict:
    d = copy.deepcopy(t)
    d["hooks"]["PreToolUse"].append({"_comment": "proje eki", "matcher": "Read",
                                     "hooks": [_shim("infra_write_guard")]})
    d["hooks"]["Stop"] = [{"hooks": [{"type": "command", "command": "python",
                                      "args": ["${CLAUDE_PROJECT_DIR}/scripts/ozel_kanca.py"]}]}]
    d["permissions"]["allow"].append("Bash(ozel:*)")
    d["env"]["PROJE_OZEL"] = "1"
    return d


def _m2(t: dict) -> dict:
    d = _ekli(t)
    del d["hooks"]["PreCompact"]
    return d


def _m2_eslik(t: dict) -> dict:
    d = copy.deepcopy(t)
    for b in d["hooks"]["PreToolUse"]:
        if b.get("matcher") == "Edit|Write|MultiEdit":
            b["hooks"] = [h for h in b["hooks"] if "pull_before_edit" not in json.dumps(h)]
    d["hooks"]["PreToolUse"].append({"matcher": "Edit|Write", "hooks": [_shim("pull_before_edit")]})
    return d


def _yorumlayici_degis(t: dict, yeni: str) -> dict:
    d = copy.deepcopy(t)
    for bl in d["hooks"].values():
        for b in bl:
            for h in b["hooks"]:
                h["command"] = yeni
    return d


def _kabuk(t: dict) -> dict:
    d = copy.deepcopy(t)
    for bl in d["hooks"].values():
        for b in bl:
            b["hooks"] = [{"type": "command",
                           "command": f'python "${{CLAUDE_PROJECT_DIR}}/scripts/hook_shim.py" {h["args"][1]}'}
                          for h in b["hooks"]]
    return d


def _recall_bicim(t: dict, kanca: dict) -> dict:
    """recall_inject girdisini verilen biçimle DEĞİŞTİR (Ö1 — tanınmayan/tırnaklı biçim)."""
    d = copy.deepcopy(t)
    for b in d["hooks"]["UserPromptSubmit"]:
        b["hooks"] = [copy.deepcopy(kanca) if "recall_inject" in json.dumps(h) else h for h in b["hooks"]]
    return d


TIRNAKLI = {"type": "command",
            "command": 'python "${CLAUDE_PROJECT_DIR}/scripts/hook_shim.py" "recall_inject"'}
BAYRAKLI = {"type": "command", "command": "python",
            "args": ["${CLAUDE_PROJECT_DIR}/scripts/hook_shim.py", "--flag", "recall_inject"]}
# Adı AYRIŞTIRILAMAYAN biçim (komut dizgesi shim'de biter, ad `args`ta) → `?…` (Ö1 ağının hedefi).
AYRISMAZ = {"type": "command", "command": "python ${CLAUDE_PROJECT_DIR}/scripts/hook_shim.py",
            "args": ["recall_inject"]}


def _bash_iki_ad(t: dict) -> dict:
    """F7 sonda biçimi: şablonun `Bash` bloğunda `hook_shim.py pull_before_edit infra_write_guard`
    — shim yalnız argv[1]'i (pull_before_edit) koşturur, infra_write_guard Bash'te HİÇ koşmaz."""
    d = copy.deepcopy(t)
    for b in d["hooks"]["PreToolUse"]:
        if b.get("matcher") == "Bash":
            b["hooks"] = [{"type": "command", "command": "python",
                           "args": ["${CLAUDE_PROJECT_DIR}/scripts/hook_shim.py",
                                    "pull_before_edit", "infra_write_guard"]}]
    return d


def _recall_adedi(d: dict) -> int:
    return sum(1 for bl in d["hooks"].values() if isinstance(bl, list) for b in bl
               for h in b.get("hooks", []) if "recall_inject" in json.dumps(h))


def _birlesik(t: dict, eslik: str) -> dict:
    """pre_tool_guard'ı şablonun üç bloğundan çıkarıp TEK birleşik eşleyicili bloğa koy (Ö2)."""
    d = copy.deepcopy(t)
    yeni = []
    for b in d["hooks"]["PreToolUse"]:
        b["hooks"] = [h for h in b["hooks"] if "pre_tool_guard" not in json.dumps(h)]
        if b["hooks"]:
            yeni.append(b)
    yeni.insert(0, {"matcher": eslik, "hooks": [_shim("pre_tool_guard")]})
    d["hooks"]["PreToolUse"] = yeni
    return d


TAM_BIRLESIK = "Bash|PowerShell|mcp__sap-adt__.*|Edit|Write|MultiEdit|NotebookEdit"
KISMI_BIRLESIK = "Bash|PowerShell|mcp__sap-adt__.*|Edit|Write"


def _stub(ad: str, cikti: str, rc: int) -> Path:
    d = KOK / "bin"
    d.mkdir(exist_ok=True)
    if WINDOWS:
        p = d / f"{ad}.cmd"
        p.write_bytes(f"@echo off\r\necho {cikti}\r\nexit /b {rc}\r\n".encode("ascii"))
    else:
        p = d / ad
        p.write_bytes(f"#!/bin/sh\necho '{cikti}'\nexit {rc}\n".encode("ascii"))
        p.chmod(0o755)
    return p


# ── yükleme ──────────────────────────────────────────────────────────────────
def yukle():
    sys.path.insert(0, str(REPO / "scripts"))
    import utils  # type: ignore
    dr = _modul("utils.drift_imzasi", DRIFT, _kaynak_drift())
    sys.modules["utils.drift_imzasi"] = dr
    utils.drift_imzasi = dr  # type: ignore[attr-defined]
    kk = _modul("utils.kanca_kablolari", KKYOL, _kaynak_kk())
    sys.modules["utils.kanca_kablolari"] = kk
    utils.kanca_kablolari = kk  # type: ignore[attr-defined]
    os.environ["CLAUDE_PROJECT_DIR"] = str(KOK)
    os.environ["CLAUDE_CONFIG_DIR"] = str(KOK / "cfg")
    g: dict = {"__name__": "ix_doctor_q406", "__file__": str(DOCTOR), "__builtins__": __builtins__}
    exec(compile(_kaynak_doctor(), str(DOCTOR), "exec"), g)
    ts: dict = {"__name__": "team_setup_q406", "__file__": str(TEAM), "__builtins__": __builtins__}
    exec(compile(_kaynak_team(), str(TEAM), "exec"), ts)
    ins = _modul("inspector_q406", INSP, _kaynak_insp())
    return kk, g, ts, ins


def _cagir(g: dict, ad: str, proj: Path) -> list:
    if ad not in g:
        return [("YOK", f"{ad} tanımsız (eski kod)")]
    g["PROJ"] = proj
    os.environ["CLAUDE_PROJECT_DIR"] = str(proj)
    try:
        return list(g[ad]())
    except Exception as e:  # noqa: BLE001
        return [("HATA", f"{type(e).__name__}: {e}")]


def _tazele(ts: dict, proj: Path) -> tuple[bool | None, str]:
    if "settings_tazele" not in ts:
        return None, "settings_tazele yok (eski kod)"
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        try:
            ok = ts["settings_tazele"](proj)
        except Exception as e:  # noqa: BLE001
            ok = None
            print(f"HATA {type(e).__name__}: {e}")
    return ok, tampon.getvalue()


def tag(r: list) -> list[str]:
    return [t for t, _ in r]


def bul(r: list, parca: str, t: str | None = None) -> list[str]:
    return [m for tt, m in r if parca in m and (t is None or tt == t)]


def main() -> int:
    kk, g, ts, ins = yukle()
    try:
        # ── U: birim ─────────────────────────────────────────────────────────
        kontrol("U1 kanca_adi: exec · kabuk · shim-dışı",
                kk.kanca_adi(_shim("recall_inject")) == "recall_inject"
                and kk.kanca_adi({"command": 'python "${X}/scripts/hook_shim.py" session_start'}) == "session_start"
                and kk.kanca_adi({"command": "python", "args": ["ozel.py"]}).startswith("?"))
        k2 = kk.kiyas(_m2_eslik(T), T)
        k1 = kk.kiyas(_m1(T), T)
        kontrol("U2 kiyas: eşleyici farkı EKSİK sayılmaz · M1 eksikleri ADIYLA",
                k2["eksik"] == [] and [b[2] for b, _ in k2["eslesik_farki"]] == ["pull_before_edit"]
                and sorted(b[2] for b in k1["eksik"]) == ["intake_triage", "recall_inject"]
                and k1["sablon_sayisi"] == 19 and len(k1["sablon_kanca"]) == 16, f"{k1} {k2}")
        giris = _m2(T)
        giris_kopya = copy.deepcopy(giris)
        yeni, eklenen = kk.eksikleri_ekle(giris, T)
        kontrol("U3 eksikleri_ekle: girdi değişmez · eski bağlantılar ⊆ yeni · allow/env aynı · yalnız pre_compact",
                giris == giris_kopya
                and not (Counter(kk.baglantilar(giris)) - Counter(kk.baglantilar(yeni)))
                and yeni["permissions"] == giris["permissions"] and yeni["env"] == giris["env"]
                and eklenen == [("PreCompact", "", "pre_compact")]
                and kk.kiyas(yeni, T)["eksik"] == [], f"eklenen={eklenen}")
        _y, ek4 = kk.eksikleri_ekle(_m2_eslik(T), T)
        kontrol("U4 eşleyici farklı bağlantı EKLENMEZ (karar kullanıcının)", ek4 == [], f"{ek4}")
        u5 = (kk.kanca_adi(TIRNAKLI), kk.kanca_adi(BAYRAKLI),
              kk.kanca_adi({"command": 'python "${X}/scripts/hook_shim.py" recall_inject 2>nul'}),
              kk.kanca_adi({"command": "python ${X}/scripts/hook_shim.py --flag recall_inject"}))
        kontrol("U5 Ö1 kanca_adi: tırnaklı ad · `--flag ad`=`--flag` (shim argv[1]) · yönlendirme",
                u5 == ("recall_inject", "--flag", "recall_inject", "--flag"), f"{u5}")
        d6 = _recall_bicim(T, TIRNAKLI)
        k6 = kk.kiyas(d6, T)
        y6, e6 = kk.eksikleri_ekle(d6, T)
        kontrol("U6 Ö1 tırnaklı biçimde kablolu recall_inject EKSİK DEĞİL · İKİNCİ kopya EKLENMEZ",
                k6["eksik"] == [] and e6 == [] and _recall_adedi(y6) == 1, f"{k6['eksik']} {e6}")
        d7 = _recall_bicim(T, AYRISMAZ)
        k7 = kk.kiyas(d7, T)
        y7, e7 = kk.eksikleri_ekle(d7, T)
        kontrol("U7 Ö1 emniyet ağı: adı ayrıştırılamayan (`?…`) biçim → biçim farkı, EKSİK değil, EKLENMEZ",
                kk.kanca_adi(AYRISMAZ).startswith("?")
                and k7["eksik"] == [] and [b[2] for b, _ in k7["bicim_farki"]] == ["recall_inject"]
                and e7 == [] and _recall_adedi(y7) == 1, f"{k7['eksik']} {k7['bicim_farki']} {e7}")
        d10 = _recall_bicim(T, BAYRAKLI)
        k10 = kk.kiyas(d10, T)
        y10, e10 = kk.eksikleri_ekle(d10, T)
        d10b = _bash_iki_ad(T)
        k10b = kk.kiyas(d10b, T)
        _y10b, e10b = kk.eksikleri_ekle(d10b, T)
        kontrol("U10 F7 adı ayrıştırılmış, başka adı koşturan kanca → EKSİK + eklenir "
                "(`--flag recall_inject` · `pull_before_edit infra_write_guard`)",
                [b[2] for b in k10["eksik"]] == ["recall_inject"] and k10["bicim_farki"] == []
                and [b[2] for b in e10] == ["recall_inject"] and _recall_adedi(y10) == 2
                and k10b["eksik"] == [("PreToolUse", "Bash", "infra_write_guard")]
                and k10b["bicim_farki"] == [] and e10b == [("PreToolUse", "Bash", "infra_write_guard")],
                f"{k10['eksik']} {k10['bicim_farki']} {e10} | {k10b['eksik']} {k10b['bicim_farki']} {e10b}")
        zincir = {"type": "command",
                  "command": 'python "${CLAUDE_PROJECT_DIR}/scripts/hook_shim.py" proje_ozel_kanca && '
                             'python "${CLAUDE_PROJECT_DIR}/scripts/hook_shim.py" recall_inject'}
        d11 = _recall_bicim(T, zincir)
        k11 = kk.kiyas(d11, T)
        y11, e11 = kk.eksikleri_ekle(d11, T)
        kontrol("U11 F7 kontrol: zincirde İKİNCİ shim çağrısı (recall_inject) → biçim farkı, EKLENMEZ",
                kk.kanca_adi(zincir) == "proje_ozel_kanca" and k11["eksik"] == []
                and [b[2] for b, _ in k11["bicim_farki"]] == ["recall_inject"]
                and e11 == [] and _recall_adedi(y11) == 1, f"{k11['eksik']} {k11['bicim_farki']} {e11}")
        d8 = _birlesik(T, TAM_BIRLESIK)
        k8 = kk.kiyas(d8, T)
        _y8, e8 = kk.eksikleri_ekle(d8, T)
        kontrol("U8 Ö2 birleşik eşleyici ⊇ şablon → KAPSANAN 3, eksik 0, ek 0, eklenen 0",
                k8["eksik"] == [] and e8 == [] and k8["ek"] == [] and k8["eslesik_farki"] == []
                and sorted(b[1] for b in k8["kapsanan"]) == sorted(
                    ["Bash|PowerShell|mcp__sap-adt__.*", "Edit|Write|MultiEdit", "NotebookEdit"]),
                f"{k8}")
        d9 = _birlesik(T, KISMI_BIRLESIK)
        k9 = kk.kiyas(d9, T)
        _y9, e9 = kk.eksikleri_ekle(d9, T)
        kontrol("U9 Ö2 kontrol: kısmi kapsama → kapsanan + eşleyici farkı + YALNIZ NotebookEdit eklenir",
                [b[1] for b in k9["kapsanan"]] == ["Bash|PowerShell|mcp__sap-adt__.*"]
                and [b[1] for b, _ in k9["eslesik_farki"]] == ["Edit|Write|MultiEdit"]
                and e9 == [("PreToolUse", "NotebookEdit", "pre_tool_guard")]
                and k9["bicim_farki"] == [], f"{k9} {e9}")

        # ── T1 / W1 ──────────────────────────────────────────────────────────
        if "_smoke_ornekleri" in g:
            g["PROJ"] = KOK
            anahtar = set(g["_smoke_ornekleri"]("t")) | set(g.get("_SMOKE_4D", ()))
            kontrol("T1 şablonun HER kancasının smoke örneği var (yoksa 4i FAIL basar)",
                    set(k1["sablon_kanca"]) <= anahtar, f"eksik={set(k1['sablon_kanca']) - anahtar}")
        else:
            kontrol("T1 şablonun HER kancasının smoke örneği var", False, "_smoke_ornekleri yok")
        agac = ast.parse(_kaynak_doctor())
        k4 = next((d for d in agac.body if isinstance(d, ast.FunctionDef) and d.name == "katman4"), None)
        cagri = {n.func.id for n in ast.walk(k4) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name)} if k4 else set()
        kontrol("W1 KABLOLAMA: katman4 _kanca_kablolama + _kanca_smoke + _recall_saglik ÇAĞIRIR",
                {"_kanca_kablolama", "_kanca_smoke", "_recall_saglik"} <= cagri, f"{sorted(cagri)}")

        # ── M1 ───────────────────────────────────────────────────────────────
        p1 = kum("m1", _m1(T))
        r = _cagir(g, "_kanca_kablolama", p1)
        f = bul(r, "kanca kablolaması", "FAIL")
        kontrol("M1a önce: 4h FAIL + recall_inject + intake_triage ADIYLA + --tazele-settings + §6a ①",
                len(f) == 1 and "recall_inject" in f[0] and "intake_triage" in f[0]
                and "--tazele-settings" in f[0] and "§6a ①" in f[0], f"{r}")
        r = _cagir(g, "_recall_saglik", p1)
        kontrol("M1b önce: 4j FAIL 'kablolu DEĞİL' — kanca kodu öneri DÖNDÜRDÜ (iki eksen ayrı)",
                tag(r) == ["FAIL"] and "kablolu DEĞİL" in r[0][1] and "öneri DÖNDÜRDÜ" in r[0][1], f"{r}")
        ok, out = _tazele(ts, p1)
        yedekler = list((p1 / ".claude").glob("settings.json.yedek-*"))
        kontrol("M1c onarım: FARK RAPORU yazımdan ÖNCE · yedek · 2 kanca EKLENDİ",
                ok is True and 0 <= out.find("FARK RAPORU") < out.find("EKLENDİ")
                and "+ EKLENECEK      recall_inject" in out and len(yedekler) == 1, out[-900:])
        r_k = _cagir(g, "_kanca_kablolama", p1)
        r_s = _cagir(g, "_kanca_smoke", p1)
        r_r = _cagir(g, "_recall_saglik", p1)
        kontrol("M1d sonra: 4h PASS 19 bağlantı · 4i son satır PASS · 4j PASS",
                tag(r_k) == ["PASS"] and "19 bağlantısının" in r_k[0][1]
                and r_s and r_s[-1][0] == "PASS" and "FAIL" not in tag(r_s)
                and tag(r_r) == ["PASS"], f"{r_k} | {r_s[-2:]} | {r_r}")
        once = (p1 / ".claude" / "settings.json").read_bytes()
        ok2, out2 = _tazele(ts, p1)
        kontrol("M1e ikinci koşum: DOKUNULMADI + bayt-eş",
                ok2 is True and "DOKUNULMADI" in out2
                and (p1 / ".claude" / "settings.json").read_bytes() == once, out2[-300:])
        p1f = kum("m1f", _m1(T), crlf=True)
        cp = subprocess.run([sys.executable, str(TEAM), "--project", str(p1f), "--tazele-settings"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace",
                            timeout=120, env=dict(os.environ, CLAUDE_PROJECT_DIR=str(p1f)))
        yaz = (p1f / ".claude" / "settings.json").read_bytes()
        kontrol("M1f GERÇEK CLI `team_setup --tazele-settings`: rc 0 · eksik 0 · CRLF korundu",
                cp.returncode == 0 and kk.kiyas(json.loads(yaz.decode("utf-8")), T)["eksik"] == []
                and b"\r\n" in yaz, f"rc={cp.returncode} {(cp.stdout + cp.stderr)[-500:]}")

        # ── M2 ───────────────────────────────────────────────────────────────
        p2 = kum("m2", _m2(T))
        r = _cagir(g, "_kanca_kablolama", p2)
        f = bul(r, "kanca kablolaması", "FAIL")
        kontrol("M2a önce: FAIL pre_compact ADIYLA + proje eki BİLGİ",
                len(f) == 1 and "pre_compact" in f[0] and "proje eki 2" in f[0] and "BİLGİ" in f[0], f"{r}")
        r = _cagir(g, "_kanca_kablolama", kum("m2b", _ekli(T)))
        kontrol("M2b yalnız proje eki: tek satır PASS (WARN DEĞİL) + 'proje eki'",
                tag(r) == ["PASS"] and "proje eki 2" in r[0][1], f"{r}")
        eski = json.loads((p2 / ".claude" / "settings.json").read_text(encoding="utf-8"))
        ok, out = _tazele(ts, p2)
        yeni = json.loads((p2 / ".claude" / "settings.json").read_text(encoding="utf-8"))
        r_s = _cagir(g, "_kanca_smoke", p2)
        kontrol("M2c onarım: proje eki/allow/env KORUNDU · pre_compact eklendi · 4i PASS",
                ok is True and not (Counter(kk.baglantilar(eski)) - Counter(kk.baglantilar(yeni)))
                and "Bash(ozel:*)" in yeni["permissions"]["allow"] and yeni["env"].get("PROJE_OZEL") == "1"
                and kk.kiyas(yeni, T)["eksik"] == [] and "KORUNACAK" in out
                and r_s and r_s[-1][0] == "PASS", f"ok={ok} {out[-500:]} | {r_s[-2:]}")
        p2d = kum("m2d", _m2_eslik(T))
        r = _cagir(g, "_kanca_kablolama", p2d)
        once = (p2d / ".claude" / "settings.json").read_bytes()
        ok, out = _tazele(ts, p2d)
        kontrol("M2d eşleyici farklı: WARN (FAIL değil) · onarım bayt-eş · DOKUNULMAYACAK",
                "FAIL" not in tag(r) and bul(r, "eşleyicisi şablondan FARKLI", "WARN")
                and ok is True and "DOKUNULMAYACAK" in out
                and (p2d / ".claude" / "settings.json").read_bytes() == once, f"{r} {out[-300:]}")
        p6 = kum("m6", _birlesik(T, TAM_BIRLESIK))
        r = _cagir(g, "_kanca_kablolama", p6)
        once = (p6 / ".claude" / "settings.json").read_bytes()
        ok, out = _tazele(ts, p6)
        kontrol("M6 Ö2 birleşik eşleyici: 4h FAIL/WARN YOK + 'KAPSANAN 3' · tazeleme bayt-eş 'KAPSANIYOR'",
                tag(r) == ["PASS"] and "KAPSANAN 3" in r[0][1] and ok is True
                and "KAPSANIYOR" in out and (p6 / ".claude" / "settings.json").read_bytes() == once,
                f"{r} {out[-400:]}")
        r = _cagir(g, "_kanca_kablolama", kum("u7k", _recall_bicim(T, AYRISMAZ)))
        kontrol("U7b Ö1 4h: tanınmayan biçim → WARN 'TANINMAYAN', FAIL YOK · F7 özet PASS DEĞİL, "
                "'tamamı projede' DEMEZ, 'DOĞRULANAMADI'",
                "FAIL" not in tag(r) and "PASS" not in tag(r) and len(bul(r, "TANINMAYAN", "WARN")) == 1
                and not bul(r, "tamamı projede") and len(bul(r, "tamamı DOĞRULANAMADI", "WARN")) == 1,
                f"{r}")
        r = _cagir(g, "_kanca_kablolama", kum("u10", _bash_iki_ad(T)))
        f = bul(r, "kanca kablolaması", "FAIL")
        kontrol("U10b F7 4h: `pull_before_edit infra_write_guard` → FAIL infra_write_guard ADIYLA + "
                "--tazele-settings · TANINMAYAN/‘tamamı projede’ YOK",
                len(f) == 1 and "infra_write_guard (PreToolUse [Bash])" in f[0]
                and "--tazele-settings" in f[0] and not bul(r, "TANINMAYAN")
                and not bul(r, "tamamı projede"), f"{r}")
        dd = copy.deepcopy(T)
        dd["disableAllHooks"] = True
        r = _cagir(g, "_kanca_kablolama", kum("d1", dd))
        kontrol("D1 Ö4 `disableAllHooks: true` (bool) → 4h FAIL 'disableAllHooks'",
                len(bul(r, "disableAllHooks: true", "FAIL")) == 1, f"{r}")
        dd["disableAllHooks"] = "true"
        r = _cagir(g, "_kanca_kablolama", kum("d2", dd))
        kontrol("D2 Ö4 `disableAllHooks: \"true\"` (dizge) → 4h WARN 'bool DEĞİL' + ÖLÇÜLMEDİ (sessiz PASS değil)",
                len([m for m in bul(r, "bool DEĞİL", "WARN") if "ÖLÇÜLMEDİ" in m]) == 1, f"{r}")
        pl = kum("l1", T)
        (pl / ".claude" / "settings.local.json").write_text(json.dumps(
            {"disableAllHooks": True, "hooks": {"Stop": [{"hooks": [_shim("yerel_kanca")]}]}}),
            encoding="utf-8")
        r = _cagir(g, "_kanca_kablolama", pl)
        kontrol("L1 F2a settings.local.json disableAllHooks + kanca → iki WARN, FAIL YOK",
                "FAIL" not in tag(r) and len(bul(r, "settings.local.json `disableAllHooks", "WARN")) == 1
                and len(bul(r, "4h kıyasına ve 4i smoke'a GİRMEDİ", "WARN")) == 1, f"{r}")
        r = _cagir(g, "_kanca_smoke", kum("s2", _ekli(T)))
        kontrol("S2 F2c shim dışı proje kancası → 4i SKIP 'shim dışı 1' + özet 'ÖLÇÜLMEDİ'",
                len(bul(r, "shim dışı 1 proje kancası", "SKIP")) == 1 and r[-1][0] == "PASS"
                and "ÖLÇÜLMEDİ 1 (shim dışı 1" in r[-1][1], f"{r[-3:]}")
        pv = kum("v1", _m2(T))
        once = (pv / ".claude" / "settings.json").read_bytes()
        asil = kk.eksikleri_ekle
        kk.eksikleri_ekle = lambda p, s: (copy.deepcopy(s), [("PreCompact", "", "pre_compact")])
        try:
            ok, out = _tazele(ts, pv)
        finally:
            kk.eksikleri_ekle = asil
        kontrol("V1 doğrulayıcı: kayıplı ekleme → FAIL DOĞRULANAMADI + yedekten geri (bayt-eş)",
                ok is False and "DOĞRULANAMADI" in out and "GERİ YÜKLENDİ" in out
                and (pv / ".claude" / "settings.json").read_bytes() == once, out[-400:])

        # ── M3 recall ────────────────────────────────────────────────────────
        p3 = kum("m3", T)
        r = _cagir(g, "_recall_saglik", p3)
        kontrol("M3a indeks YOK → kanca tazeler → PASS 'önce YOK → sonra TAZE'",
                tag(r) == ["PASS"] and "önce YOK → sonra TAZE" in r[0][1], f"{r}")
        idx = p3 / ".tmp" / "recall-index.json"
        idx.parent.mkdir(parents=True, exist_ok=True)   # eski kodda M3a indeksi üretmez
        idx.write_text("{bozuk", encoding="utf-8")
        gelecek = time.time() + 3600
        os.utime(idx, (gelecek, gelecek))
        r = _cagir(g, "_recall_saglik", p3)
        cp = subprocess.run([sys.executable, str(p3 / "core" / "scripts" / "build_recall_index.py")],
                            cwd=str(p3), capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=120, env=dict(os.environ, CLAUDE_PROJECT_DIR=str(p3)))
        r2 = _cagir(g, "_recall_saglik", p3)
        kontrol("M3b bozuk JSON → FAIL BOZUK + build_recall_index onarımı → (GERÇEK alt süreç) PASS",
                tag(r) == ["FAIL"] and "BOZUK" in r[0][1] and "build_recall_index" in r[0][1]
                and cp.returncode == 0 and tag(r2) == ["PASS"], f"{r} | rc={cp.returncode} | {r2}")
        eski_t = time.time() - 30 * 86400
        os.utime(idx, (eski_t, eski_t))
        r = _cagir(g, "_recall_saglik", p3)
        kontrol("M3c bayat → kanca tazeler → PASS 'önce BAYAT → sonra TAZE'",
                tag(r) == ["PASS"] and "önce BAYAT → sonra TAZE" in r[0][1], f"{r}")
        gercek = json.loads(idx.read_text(encoding="utf-8"))
        sahte = {"id": "how:000-ix-sahte", "kaynak": "k", "baslik": "Zzqx Yyqw sonda basligi uzun",
                 "oz": "anlamsiz", "anahtar": ["qqqqq"]}
        gercek["kayit"] = [sahte] + list(gercek.get("kayit") or [])
        idx.write_text(json.dumps(gercek, ensure_ascii=False), encoding="utf-8")
        os.utime(idx, (gelecek, gelecek))
        r = _cagir(g, "_recall_saglik", p3)
        kontrol("R1 Ö3 ilk kayıt dönmüyor, sonraki dönüyor → 4j PASS (denenen ≥2)",
                tag(r) == ["PASS"] and "how:000-ix-sahte" in r[0][1] and "denenen 1:" not in r[0][1],
                f"{r}")
        idx.write_text(json.dumps({"v": 1, "kayit": [{"id": "how:x", "kaynak": "k",
                                                      "baslik": "Zzqx Yyqw sonda basligi uzun",
                                                      "oz": "anlamsiz", "anahtar": ["qqqqq"]}]}),
                       encoding="utf-8")
        os.utime(idx, (gelecek, gelecek))
        r = _cagir(g, "_recall_saglik", p3)
        kontrol("M3d kayıt var, öneri dönmüyor (exit 0) → FAIL 'öneri DÖNDÜRMEDİ'",
                tag(r) == ["FAIL"] and "öneri DÖNDÜRMEDİ" in r[0][1], f"{r}")
        r = _cagir(g, "_recall_saglik", kum("j1", _recall_bicim(T, AYRISMAZ)))
        kontrol("J1 F7 4j: yalnız tanınmayan biçimde kablolu → FAIL 'TANINMAYAN' · `--tazele-settings` "
                "onarım olarak GÖSTERİLMEZ ('DOKUNMAZ' + §6a ②)",
                tag(r) == ["FAIL"] and "TANINMAYAN" in r[0][1] and "DOKUNMAZ" in r[0][1]
                and "§6a ②" in r[0][1] and "onarım (§6a ①)" not in r[0][1], f"{r}")

        # ── M5 ───────────────────────────────────────────────────────────────
        stub = _stub("python_stub", "Python was not found", 49)
        r = _cagir(g, "_kanca_smoke", kum("m5a", _yorumlayici_degis(T, str(stub))))
        f = bul(r, "BAŞLAMIYOR", "FAIL")
        kontrol("M5a yorumlayıcı başlamıyor → FAIL §6a ② + kod sys.executable yedeğiyle ölçüldü",
                len(f) == 1 and "§6a ②" in f[0] and bul(r, "sys.executable yedeği")
                and "Claude Code'un hook ortamının PATH'i ÖLÇÜLMEDİ" in f[0], f"{r[:2]} {r[-1:]}")
        d5b = copy.deepcopy(T)
        d5b["hooks"]["Stop"] = [{"hooks": [_shim("eski_kaldirilmis_kanca")]}]
        r = _cagir(g, "_kanca_smoke", kum("m5b", d5b))
        f = bul(r, "eski_kaldirilmis_kanca", "FAIL")
        kontrol("M5b projede kablolu, çekirdekte YOK → FAIL §6a ②",
                len(f) == 1 and "çekirdekte YOK" in f[0] and "§6a ②" in f[0], f"{r}")
        zehir = KOK / "zehir"
        zehir.mkdir(exist_ok=True)
        (zehir / "datetime.py").write_text("raise RuntimeError('ix-test-cokme')\n", encoding="utf-8")
        p5c = kum("m5c", T)
        eski_pp = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = str(zehir)
        try:
            r = _cagir(g, "_kanca_smoke", p5c)
        finally:
            if eski_pp is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = eski_pp
        f = bul(r, "ÇÖKTÜ (Traceback", "FAIL")
        kontrol("M5c kanca çöküyor (zehirli datetime) → FAIL 'ÇÖKTÜ' §6a ③ + özet FAIL",
                len(f) >= 1 and all("§6a ③" in m for m in f) and r[-1][0] == "FAIL",
                f"{[m[:120] for _, m in r]}")
        p5d = kum("m5d", T)
        (p5d / ".tmp" / "instructions-loaded.log").mkdir(parents=True)
        r = _cagir(g, "_kanca_smoke", p5d)
        f = bul(r, "instructions_loaded_log", "FAIL")
        kontrol("M5d fail-open SESSİZ (log yazılamıyor, exit 0) → FAIL 'SESSİZ kaldı' §6a ③",
                len(f) == 1 and "SESSİZ kaldı" in f[0] and "§6a ③" in f[0], f"{r}")

        # ── C3 üçüncü bağlam: kabuk biçimli settings ─────────────────────────
        pc = kum("c3", _kabuk(T))
        r_k = _cagir(g, "_kanca_kablolama", pc)
        r_s = _cagir(g, "_kanca_smoke", pc)
        kontrol("C3 kabuk biçimi: 4h PASS 19 · 4i PASS (yorumlayıcı komut dizgesinden çözüldü)",
                tag(r_k) == ["PASS"] and "19 bağlantısının" in r_k[0][1]
                and r_s and r_s[-1][0] == "PASS" and "yorumlayıcı `python`" in r_s[-1][1],
                f"{r_k} | {r_s[-1:]}")
        kontrol("Y1 F8 4i PASS özeti PATH sınırını taşır (`--layer 4` 1g satırını basmaz)",
                bool(r_s) and r_s[-1][0] == "PASS"
                and "Claude Code'un hook ortamının PATH'i ÖLÇÜLMEDİ" in r_s[-1][1], f"{r_s[-1:]}")

        # ── F3 settings D7 onarım metni ──────────────────────────────────────
        pf = kum("f3", _m1(T))
        r = _cagir(g, "_d7_drift", pf)
        d7s = bul(r, "settings.json")
        tampon = io.StringIO()
        g_ts_proj = ts.get("sablon_sapmasi")
        with contextlib.redirect_stdout(tampon):
            try:
                g_ts_proj(pf) if g_ts_proj else print("sablon_sapmasi YOK")
            except Exception as e:  # noqa: BLE001
                print(f"HATA {type(e).__name__}: {e}")
        ts_out = [s_ for s_ in tampon.getvalue().splitlines() if "settings.json" in s_ and "SAPMI" in s_]
        kontrol("F3 settings D7 onarımı (ix_doctor 4a + team_setup): --tazele-settings + git diff, "
                "'template'ten yenile' YOK",
                len(d7s) == 1 and "--tazele-settings" in d7s[0] and "git diff --no-index" in d7s[0]
                and "template'ten yenile" not in d7s[0]
                and len(ts_out) == 1 and "--tazele-settings" in ts_out[0]
                and "template'ten yenile" not in ts_out[0], f"{d7s} | {ts_out}")

        # ── I1-I3 smoke log satırı A katmanını susturmaz (F1) ───────────────
        pi = kum("i1", T)
        _cagir(g, "_kanca_smoke", pi)
        logp = pi / ".tmp" / "instructions-loaded.log"
        ham = logp.read_text(encoding="utf-8") if logp.is_file() else ""
        a1 = list(ins.a1_logger_canli(pi, ins._log_satirlari(pi)))
        kontrol("I1 F1 log YALNIZ smoke satırı (gerçek logger yazdı) → inspector A1 HÂLÂ ateşler",
                "ix_doctor_smoke" in ham and len(a1) == 1, f"ham={ham[-200:]!r} a1={a1}")
        with logp.open("a", encoding="utf-8") as fh:
            fh.write("2026-11-12T10:00:00+03:00\tsession_start\tProject\t/x/CLAUDE.md\tsid=ix-gercek-oturum\n")
        a1b = list(ins.a1_logger_canli(pi, ins._log_satirlari(pi)))
        kontrol("I2 kontrol: gerçek oturum satırı eklenince A1 SUSAR (süzgeç fazla maskelemez)",
                a1b == [], f"{a1b}")
        logp.write_text(ham, encoding="utf-8")
        try:
            ss = _modul("session_start_q406", SSTART, SSTART.read_text(encoding="utf-8"))
            ss.PROJ = pi
            olc = ss._oturum_olcumu("ix-bu-oturum", False)
        except Exception as e:  # noqa: BLE001
            olc = f"YUKLENEMEDI {type(e).__name__}: {e}"
        kontrol("I3 session_start YÜKLEME ölçümü smoke satırını oturum SAYMAZ (ÖLÇÜLEMEDİ, sid yok)",
                "ÖLÇÜLEMEDİ" in olc and "sid'li log satırı yok" in olc, olc)

        # ── P1 parity_probe (GERÇEK alt süreç) ──────────────────────────────
        pp = kum("p1", _m1(T))
        cikti = KOK / "parity.json"
        cp = subprocess.run([sys.executable, str(REPO / "scripts" / "parity_probe.py"), "--no-doctor",
                             "--proje", str(pp), "--out", str(cikti)],
                            capture_output=True, text=True, encoding="utf-8", errors="replace",
                            timeout=300, env=dict(os.environ, CLAUDE_PROJECT_DIR=str(pp)))
        try:
            eks = json.loads(cikti.read_text(encoding="utf-8"))["claude_katmani"]["kanca_sablondan_eksik"]
        except Exception as e:  # noqa: BLE001
            eks = f"OKUNAMADI {type(e).__name__}"
        kontrol("P1 parity_probe kanca_sablondan_eksik: recall_inject + intake_triage ADIYLA",
                isinstance(eks, list) and any("recall_inject" in x for x in eks)
                and any("intake_triage" in x for x in eks), f"rc={cp.returncode} {eks} {cp.stderr[-300:]}")
    finally:
        try:
            _sil(KOK)
        except Exception:
            pass

    dusen = {k for k, v in SONUC.items() if not v}
    ok = len(SONUC) - len(dusen)
    tabanlar = [str(x) for x in (TABAN, TABAN_INSP, TABAN_KK) if x]
    etiket = f" [TABAN {' + '.join(tabanlar)}]" if tabanlar else (f" [{KIP}]" if KIP else "")
    print(f"\nkanca_kablolama{etiket}: {ok}/{len(SONUC)} PASS")
    if KIP:
        ilan = ILAN[KIP]
        if not dusen:
            print(f"[KACTI] {KIP}: hiçbir vektör düşmedi (ilan: {sorted(ilan)})")
            return 0
        if not ilan <= dusen:
            print(f"[SAPMA] {KIP}: ilan edilen {sorted(ilan)} düşmedi; düşen {sorted(dusen)}")
            return 2
        print(f"[DUSTU] {KIP}: ilan edilen {sorted(ilan)} düştü (toplam düşen {sorted(dusen)})")
        return 1
    return 0 if not dusen else 1


if __name__ == "__main__":
    sys.exit(main())
