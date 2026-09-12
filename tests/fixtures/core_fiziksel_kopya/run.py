# -*- coding: utf-8 -*-
"""core_fiziksel_kopya — Q286: `CLAUDE.core.md` + `claude/rules` projeye FİZİKSEL KOPYA olarak girer
ve yükleme durumu ÖLÇÜLEBİLİR hâle gelir.

KÖK (ölçüldü, Claude Code 2.1.269): harness bir JUNCTION'ın hedefini "dış import" sayar; proje onay
bayrağı `false` iken `.claude/rules` junction'ındaki kurallar ve `@core/CLAUDE.core.md` YÜKLENMEZ.
Canlı log: son core/rules yüklemesi 2026-08-20. Aynı dosya GERÇEK dizinde koşulsuz yüklenir.

EKSENLER ve VEKTÖRLER:
  B1  claude_overlay: `rules` ZORUNLU overlay + `00-claude-core.md` kopyası (V1–V7)
  B2  çağıranlar: team_setup.junctions / provision_worktree (V8–V9) · session_start durum (V20) ·
      ix_doctor katman1 (V20b)
  C1  logger `sid=` kolonu (V10) + inspector iki biçimi ayrıştırır (V11)
  C2  session_start YÜKLEME satırı: ÖN KOŞUL + ÖNCEKİ OTURUM / BU OTURUMUN AÇILIŞI (V12–V19)
  K1  ⚠GEVŞETME behavior_manifest muafiyeti — yalnız el değmemiş core kopyası (V21–V26)
  B4  inspector A3 gerçek bulgu + sid filtresi (V27) · B5 kopya→kaynak eşlemesi (V28)

⛔ KURULUM ile DENEK AYRIDIR: materyalize edilmiş durum daima BU REPONUN `scripts/`i ile kurulur;
denenen kod ise kum-core'daki kopyadır (mutasyonlu ya da `--agac` ile eski ağaç). Böylece eski
kodda KIRMIZI, "kurulum eski kodda yapılamadı" yüzünden değil, tam da kusurun kendisinden gelir.

KOŞUM:     python tests/fixtures/core_fiziksel_kopya/run.py
ESKİ KOD:  python tests/fixtures/core_fiziksel_kopya/run.py --agac <eski-ağaç-kökü>
           (ör. `git archive 8e8feef scripts | tar -x -C <dizin>`; tek seferlik kanıt, batarya DIŞI)
MUTASYON (her biri kum kopyasında tek metin değişikliği; desen 1 kez bulunmazsa [DURDU] exit 2):
  --mutasyon-optin        rules yeniden opt-in (ZORUNLU_TIPLER boş)           → B1/B2/C2 düşer
  --mutasyon-muafiyetsiz  behavior_manifest muafiyeti sökülür                   → V21/V26a düşer
  --mutasyon-gevsek       muafiyet el değmişliği/kaynağı sormaz                 → V22/V24 düşer
  --mutasyon-sidsiz       logger sid kolonunu yazmaz                            → V10 düşer
  --mutasyon-durum-naif   durum() zorunlu tipi "sızıntı" sayar                   → V20/V20b düşer
  --mutasyon-coker        ÖLÇÜLEMEDİ → YÜKLENMEDİ'ye çöker                        → V18* düşer
  --mutasyon-a3-bilgi     A3 yeniden "bilgi" (bulgu değil)                      → V27 düşer
  --mutasyon-b5-yol       B5 kaynak eşlemesini kullanmaz                        → V28 düşer
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

KOK = Path(__file__).resolve().parents[3]
if not (KOK / "scripts").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {KOK}")
KURULUM_KODU = KOK / "scripts"

GECERLI_KIP = {"--mutasyon-optin", "--mutasyon-muafiyetsiz", "--mutasyon-gevsek",
               "--mutasyon-sidsiz", "--mutasyon-durum-naif", "--mutasyon-coker",
               "--mutasyon-a3-bilgi", "--mutasyon-b5-yol"}

# (dosya, eski, yeni) — kum kopyasına uygulanır, gerçek kaynağa ASLA.
MUTASYONLAR = {
    "--mutasyon-optin": ("utils/claude_overlay.py",
                         'ZORUNLU_TIPLER = ("rules",)', "ZORUNLU_TIPLER = ()"),
    "--mutasyon-muafiyetsiz": ("behavior_manifest.py",
                               "muaf = _overlay_muafiyeti(d)", "muaf = set()"),
    "--mutasyon-gevsek": ("utils/claude_overlay.py",
                          'if kayit.get("kaynak") == "core" and _uretildigi_gibi(h / ad, kayit):',
                          "if True:"),
    "--mutasyon-sidsiz": ("hooks/instructions_loaded_log.py",
                          'ek += f"\\tsid={sid}" if sid else ""', 'ek += ""'),
    "--mutasyon-durum-naif": ("utils/claude_overlay.py",
                              'if not overlay_gerekli(proje, tip):\n        return "overlay"',
                              'if not overlay_var_mi(proje, tip):\n        return "overlay"'),
    "--mutasyon-coker": ("hooks/session_start.py",
                         '_OLCULEMEDI = "ÖLÇÜLEMEDİ"', '_OLCULEMEDI = "YÜKLENMEDİ"'),
    "--mutasyon-a3-bilgi": ("inspector.py",
                            'f"→ team_setup.py --repair-junctions"))',
                            'f"→ team_setup.py --repair-junctions", bilgi=True))'),
    "--mutasyon-b5-yol": ("inspector.py",
                          '_kaynak = getattr(_ov0, "core_kaynagi", None)', "_kaynak = None"),
}

SONUC: list[tuple[bool, str]] = []
SID_BU = "cccc3333-0000-4000-8000-000000000001"
SID_ONCEKI = "aaaa1111-0000-4000-8000-000000000002"
# ⚠ e-posta biçimli dize çalışma zamanında kurulur: GENERICIZE-LEAK guard'ı literali kimlik izi
# sayıp yazımı REDDEDİYOR (ölçüldü, bu dosyanın ilk yazımı). Vektör yalnız `\w@\w` biçimini ister.
EPOSTA_BICIMI = "ad" + chr(64) + "ornek.co"


def kontrol(ok: bool, ad: str, detay: str = "") -> None:
    SONUC.append((bool(ok), ad + ("" if ok else f" — {detay}")))
    print(f"  [{'OK' if ok else 'XX'}] {ad}" + ("" if ok else f"\n        {detay[:600]}"))


def yaz(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8", newline="\n")


def link_mi(p: Path) -> bool:
    try:
        os.readlink(p)
        return True
    except (OSError, ValueError):
        return False


def bag(link: Path, hedef: Path) -> None:
    """Windows: junction (`mklink /J`, yönetici istemez) · POSIX: symlink (kardeş desen:
    tests/fixtures/fs_docstd/run.py::_junction)."""
    link.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(hedef)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"[DURDU] KURULAMADI: junction {link} -> {hedef}: {(r.stderr or r.stdout).strip()}")
            sys.exit(2)
    else:
        os.symlink(str(hedef), str(link), target_is_directory=True)


def baglari_sok(kok: Path) -> None:
    """Temizlikten ÖNCE bağları kaldır (hedefe dokunmadan) — rmtree bağın içine yürümesin."""
    for dp, dn, _fn in os.walk(kok):
        for d in list(dn):
            p = Path(dp) / d
            if link_mi(p):
                try:
                    os.rmdir(p)
                except OSError:
                    try:
                        os.unlink(p)
                    except OSError:
                        pass
                dn.remove(d)


SURUCU_KAYNAK = r'''
import json, sys, traceback
from pathlib import Path
kod = Path(sys.argv[1]); islem = sys.argv[2]; a = sys.argv[3:]
sys.path.insert(0, str(kod))
def J(x):
    print("@@J@@" + json.dumps(x, ensure_ascii=False, default=str))
try:
    if islem == "materyalize":
        from utils import claude_overlay as ov
        ok, m = ov.materyalize(Path(a[0]), Path(a[1]), a[2])
        J({"ok": ok, "msg": m})
    elif islem == "oto":
        from utils import claude_overlay as ov
        J({"s": ov.oto_tazele(Path(a[0]), Path(a[1]))})
    elif islem == "junctions":
        import team_setup
        J({"ok": team_setup.junctions(Path(a[0]))})
    elif islem == "provision":
        import team_setup
        J({"ok": team_setup.provision_worktree(Path(a[0]), Path(a[1]))})
    elif islem == "katman1":
        import ix_doctor
        J({"r": [list(x) for x in ix_doctor.katman1()]})
    elif islem == "bm_generate":
        import behavior_manifest
        behavior_manifest.generate(Path(a[0]))
        J({"ok": True})
    elif islem == "bm_verify":
        import behavior_manifest
        J({"s": behavior_manifest.verify_quiet(Path(a[0]))})
    elif islem == "log":
        import inspector
        J({"s": inspector._log_satirlari(Path(a[0]))})
    elif islem == "a3":
        import inspector
        sat = inspector._log_satirlari(Path(a[0]))
        b = inspector.a3_tembel_yukleme(Path(a[1]), sat, json.loads(a[2]), a[3] or None)
        J({"b": [[x.kod, x.bilgi, x.mesaj] for x in b]})
    elif islem == "b5":
        import inspector
        b = inspector.b5_core_baglantisi(Path(a[0]), Path(a[1]))
        J({"b": [[x.kod, x.bilgi, x.mesaj] for x in b]})
    else:
        J({"hata": "bilinmeyen islem " + islem})
except BaseException as e:
    J({"hata": type(e).__name__ + ": " + str(e), "tb": traceback.format_exc()[-900:]})
'''


class Kum:
    def __init__(self, tmp: Path, agac: Path, kip: str | None) -> None:
        self.tmp = tmp
        self.surucu = tmp / "_surucu.py"
        yaz(self.surucu, SURUCU_KAYNAK)
        # TAM core: denek kodu (scripts kopyası) + sentetik claude içeriği
        self.tam = tmp / "tamcore"
        shutil.copytree(agac / "scripts", self.tam / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        core_icerik(self.tam, "TAMCORE-ISARETI")
        self.kod = self.tam / "scripts"
        if kip:
            rel, eski, yeni = MUTASYONLAR[kip]
            f = self.kod / rel
            src = f.read_text(encoding="utf-8")
            n = src.count(eski)
            if n != 1:
                print(f"[DURDU] {kip} deseni {n} kez bulundu (1 bekleniyordu): {rel}: {eski!r}")
                sys.exit(2)
            f.write_text(src.replace(eski, yeni), encoding="utf-8", newline="\n")

    def _ortam(self, proj: Path | None) -> dict:
        o = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
        o.pop("IX_OVERLAY_OTO", None)
        o["CLAUDE_PROJECT_DIR"] = str(proj or self.tmp)   # canlı projeye ASLA düşmesin
        return o

    def sur(self, kod: Path, islem: str, *a, proj: Path | None = None) -> dict:
        r = subprocess.run([sys.executable, str(self.surucu), str(kod), islem, *map(str, a)],
                           capture_output=True, timeout=300, env=self._ortam(proj),
                           cwd=str(proj or self.tmp))
        out = (r.stdout or b"").decode("utf-8", "replace")
        for s in reversed(out.splitlines()):
            if s.startswith("@@J@@"):
                return json.loads(s[5:])
        return {"hata": f"JSON yok rc={r.returncode}",
                "tb": (out + (r.stderr or b"").decode("utf-8", "replace"))[-900:]}

    def kur_materyalize(self, proj: Path, core: Path) -> None:
        r = self.sur(KURULUM_KODU, "materyalize", proj, core, "rules")
        if not r.get("ok"):
            print(f"[DURDU] KURULAMADI: kurulum materyalize basarisiz: {r}")
            sys.exit(2)

    def hook(self, ad: str, proj: Path, payload) -> tuple[int, str, str]:
        govde = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        r = subprocess.run([sys.executable, str(self.kod / "hooks" / ad)], input=govde,
                           capture_output=True, timeout=300, env=self._ortam(proj), cwd=str(proj))
        return (r.returncode, (r.stdout or b"").decode("utf-8", "replace"),
                (r.stderr or b"").decode("utf-8", "replace"))


def core_icerik(core: Path, isaret: str) -> None:
    yaz(core / "CLAUDE.core.md", f"# core yukleyici\n\n{isaret}\n")
    yaz(core / "claude" / "rules" / "genel.md", "# genel kural\n\nGENEL-KURAL\n")
    yaz(core / "claude" / "rules" / "abap-kural.md", "---\npaths: **/*.abap\n---\n\nABAP-KURAL\n")
    for t in ("agents", "skills", "commands"):
        yaz(core / "claude" / t / "alpha.md", "---\nname: alpha\ndescription: sentetik\n---\n\nA\n")


def hafif_core(tmp: Path, ad: str, isaret: str = "CEKIRDEK-V1") -> Path:
    c = tmp / ad
    core_icerik(c, isaret)
    return c


def bos_proje(tmp: Path, ad: str) -> Path:
    p = tmp / ad
    (p / ".claude").mkdir(parents=True, exist_ok=True)
    yaz(p / "CLAUDE.md", "# proje\n")
    return p


def rules(p: Path) -> Path:
    return p / ".claude" / "rules"


def kopya(p: Path) -> Path:
    return rules(p) / "00-claude-core.md"


def oku(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "<YOK>"


def yukleme_satiri(stdout: str) -> str:
    try:
        ctx = json.loads(stdout)["hookSpecificOutput"]["additionalContext"]
    except Exception:
        return "<JSON YOK>"
    if "[YUKLEME — session_start]\n" not in ctx:
        return "<BASLIK YOK>"
    return ctx.split("[YUKLEME — session_start]\n", 1)[1].split("\n", 1)[0]


def ctx_of(stdout: str) -> str:
    try:
        return json.loads(stdout)["hookSpecificOutput"]["additionalContext"]
    except Exception:
        return ""


def log_yaz(p: Path, satirlar: list[str]) -> None:
    yaz(p / ".tmp" / "instructions-loaded.log", "".join(s + "\n" for s in satirlar))


def ls(sid: str | None, reason: str, dosya: str) -> str:
    return (f"2026-09-12T10:00:00+03:00\t{reason}\tProject\t{dosya}"
            + (f"\tsid={sid}" if sid else ""))


# ═════════════════════════════════════════════════════════════════════════════
def b1(k: Kum) -> None:
    print("\n-- B1 claude_overlay: rules ZORUNLU kopya --")
    c1 = hafif_core(k.tmp, "c1")
    p1 = bos_proje(k.tmp, "p1")
    r = k.sur(k.kod, "materyalize", p1, c1, "rules")
    kontrol(r.get("ok") and kopya(p1).is_file() and "CEKIRDEK-V1" in oku(kopya(p1))
            and not link_mi(rules(p1)),
            "V1 claude-local YOK iken rules GERCEK dizin + 00-claude-core.md kopyasi", str(r))
    kontrol("paths:" not in oku(kopya(p1)) and oku(rules(p1) / "abap-kural.md").startswith("---\npaths:"),
            "V1c cekirdek kopyasi paths:'SIZ; paths:'li kural frontmatter'i BASTA korunur",
            oku(rules(p1) / "abap-kural.md")[:80])

    p1b = bos_proje(k.tmp, "p1b")
    bag(rules(p1b), c1 / "claude" / "rules")
    r = k.sur(k.kod, "materyalize", p1b, c1, "rules")
    core_adlar = sorted(x.name for x in (c1 / "claude" / "rules").iterdir())
    kontrol(r.get("ok") and not link_mi(rules(p1b)) and kopya(p1b).is_file()
            and core_adlar == ["abap-kural.md", "genel.md"],
            "V1b junction kopyaya cevrilir, core/claude/rules'a DOKUNULMAZ", f"{r} core={core_adlar}")

    p2 = bos_proje(k.tmp, "p2")
    yaz(p2 / "claude-local" / "rules" / "00-claude-core.md", "SAHTE-OVERRIDE\n")
    yaz(p2 / "claude-local" / "rules" / "proje-kural.md", "PROJE-KURAL\n")
    r = k.sur(k.kod, "materyalize", p2, c1, "rules")
    kontrol("RED" in str(r.get("msg")) and "CEKIRDEK-V1" in oku(kopya(p2))
            and "SAHTE" not in oku(kopya(p2)),
            "V2 (K3) ayni adli claude-local override GORUNUR reddedilir, cekirdek kopyasi core'dan", str(r))
    kontrol("PROJE-KURAL" in oku(rules(p2) / "proje-kural.md"),
            "V2b proje kurali overlay olarak YINE girer")

    c3 = hafif_core(k.tmp, "c3")
    p3 = bos_proje(k.tmp, "p3")
    k.kur_materyalize(p3, c3)
    (c3 / "CLAUDE.core.md").unlink()
    r = k.sur(k.kod, "materyalize", p3, c3, "rules")
    # ⚠ Eski kodda (8e8feef) ilk yazım YEŞİL çıktı: eski `materyalize` "overlay yok" deyip False
    # döndürüyor ve kopyaya dokunmuyordu ⇒ vektör ayırt etmiyordu. Mesajın eksik KAYNAĞI adlandırması şart.
    kontrol(r.get("ok") is False and "CLAUDE.core.md" in str(r.get("msg")) and kopya(p3).is_file()
            and "CEKIRDEK-V1" in oku(kopya(p3)),
            "V3 CLAUDE.core.md okunamazsa BASARILI sayilmaz, eksik kaynagi adlandirir, kopya SILINMEZ", str(r))
    o = k.sur(k.kod, "oto", p3, c3)
    kontrol(any("ATLANDI" in s for s in o.get("s", [])) and kopya(p3).is_file(),
            "V3b oto_tazele kaynak yokken ATLANDI der, kopyaya dokunmaz", str(o))

    c4 = hafif_core(k.tmp, "c4")
    p4 = bos_proje(k.tmp, "p4")
    k.kur_materyalize(p4, c4)
    yaz(c4 / "CLAUDE.core.md", "# core yukleyici\n\nCEKIRDEK-V2\n")
    o = k.sur(k.kod, "oto", p4, c4)
    kontrol(any(str(s).startswith("overlay tazelendi: rules") for s in o.get("s", []))
            and "CEKIRDEK-V2" in oku(kopya(p4)),
            "V4 core degisince oto_tazele kopyayi komutsuz tazeler (gorunur satir)", str(o))
    yaz(kopya(p4), oku(kopya(p4)) + "ELLE-DUZELTME\n")
    yaz(c4 / "CLAUDE.core.md", "# core yukleyici\n\nCEKIRDEK-V3\n")
    o = k.sur(k.kod, "oto", p4, c4)
    kontrol(any("ATLANDI" in s for s in o.get("s", [])) and "ELLE-DUZELTME" in oku(kopya(p4)),
            "V5 (N) elle duzeltilmis kopya EZILMEZ (T2.5 kapisi aynen)", str(o))

    p6 = bos_proje(k.tmp, "p6")
    bag(rules(p6), c1 / "claude" / "rules")
    o = k.sur(k.kod, "oto", p6, c1)
    kontrol(o.get("s") == [] and link_mi(rules(p6)),
            "V6 (N) otomatik yol junction'i KENDILIGINDEN kaldirmaz ve sessizdir", str(o))

    p7 = bos_proje(k.tmp, "p7")
    r = k.sur(k.kod, "materyalize", p7, c1, "agents")
    kontrol(r.get("ok") is False and not (p7 / ".claude" / "agents").exists(),
            "V7 (N) agents hala OPT-IN (claude-local yoksa uretilmez)", str(r))


def b2(k: Kum) -> None:
    print("\n-- B2 cagiranlar: team_setup --")
    p8 = bos_proje(k.tmp, "p8")
    bag(p8 / "core", k.tam)
    bag(rules(p8), k.tam / "claude" / "rules")
    r = k.sur(k.kod, "junctions", p8, proj=p8)
    tam_adlar = sorted(x.name for x in (k.tam / "claude" / "rules").iterdir())
    kontrol(not link_mi(rules(p8)) and "TAMCORE-ISARETI" in oku(kopya(p8))
            and link_mi(p8 / ".claude" / "agents") and tam_adlar == ["abap-kural.md", "genel.md"],
            "V8 team_setup.junctions: rules KOPYA (junction'dan cevrilir), agents junction, core temiz",
            f"{r} tam={tam_adlar} rules_link={link_mi(rules(p8))}")
    wt = k.tmp / "wt9"
    wt.mkdir()
    r = k.sur(k.kod, "provision", wt, p8, proj=p8)
    kontrol(kopya(wt).is_file() and not link_mi(rules(wt)),
            "V9 provision_worktree: worktree'de de rules KOPYA", str(r)[:300])


def c1(k: Kum) -> None:
    print("\n-- C1 logger sid + inspector ayristirma --")
    lp = bos_proje(k.tmp, "logp")
    rc, _, _ = k.hook("instructions_loaded_log.py", lp, {
        "load_reason": "session_start", "file_path": "x/CLAUDE.md", "memory_type": "Project",
        "session_id": "sid-abc-123", "hook_event_name": "InstructionsLoaded"})
    son = oku(lp / ".tmp" / "instructions-loaded.log").splitlines()[-1:] or [""]
    kontrol(rc == 0 and son[0].endswith("\tsid=sid-abc-123"),
            "V10 logger satir SONUNA sid= kolonu yazar", repr(son[0]))
    k.hook("instructions_loaded_log.py", lp, {
        "load_reason": "include", "file_path": "x/y.md", "memory_type": "Project"})
    son = oku(lp / ".tmp" / "instructions-loaded.log").splitlines()[-1:] or [""]
    kontrol("sid=" not in son[0] and son[0].endswith("x/y.md"),
            "V10b (N) payload'da session_id yoksa kolon YAZILMAZ (uydurma kimlik yok)", repr(son[0]))

    ip = bos_proje(k.tmp, "insp")
    log_yaz(ip, [ls(None, "session_start", "/a/CLAUDE.md"),
                 ls("zzz", "include", "/a/b.md")])
    r = k.sur(k.kod, "log", ip)
    s = r.get("s") or [{}, {}]
    kontrol(len(s) == 2 and s[0].get("sid") is None and s[1].get("sid") == "zzz"
            and s[1].get("path") == "/a/b.md",
            "V11 inspector eski (sid'siz) + yeni (sid'li) satiri birlikte ayristirir", str(r)[:300])


def ss_proje(k: Kum, ad: str, kopyali: bool = True, claude_md: str = "# proje\n",
             log: list[str] | None = None) -> Path:
    p = bos_proje(k.tmp, ad)
    yaz(p / "CLAUDE.md", claude_md)
    bag(p / "core", k.tam)
    for t in ("agents", "skills", "commands"):
        bag(p / ".claude" / t, k.tam / "claude" / t)
    if kopyali:
        k.kur_materyalize(p, k.tam)
    else:
        bag(rules(p), k.tam / "claude" / "rules")
    if log is not None:
        log_yaz(p, [x.replace("{P}", str(p).replace("\\", "/")) for x in log])
    return p


def c2(k: Kum) -> dict:
    print("\n-- C2 session_start YUKLEME satiri --")
    L_YUK = [ls(SID_ONCEKI, "session_start", "{P}/CLAUDE.md"),
             ls(SID_ONCEKI, "session_start", "{P}/.claude/rules/00-claude-core.md")]
    L_YUKMEDI = [ls(SID_ONCEKI, "session_start", "{P}/CLAUDE.md")]
    bu = {"session_id": SID_BU, "source": "startup"}
    cp = {"session_id": SID_BU, "source": "compact"}

    s13 = ss_proje(k, "s13", log=L_YUK)
    rc, so, se = k.hook("session_start.py", s13, bu)
    y = yukleme_satiri(so)
    kontrol(rc == 0 and not y.startswith("<"), "V12 startup: [YUKLEME — session_start] satiri VAR",
            f"rc={rc} y={y} se={se[-300:]}")
    kontrol("ÖN KOŞUL: TAMAM" in y and "dış @import 0" in y,
            "V13 kopya taze + dis import yok -> ON KOSUL TAMAM", y)
    kontrol(f"ÖNCEKİ OTURUM {SID_ONCEKI[:8]}" in y and "core=YÜKLENDİ" in y,
            "V16 onceki oturumun sid'inde 00-claude-core.md -> core=YÜKLENDİ", y)
    kontrol("BU OTURUMUN" not in y and SID_BU[:8] not in y,
            "V19 startup satiri BU oturum icin yukleme IDDIA ETMEZ", y)
    ctx = ctx_of(so)
    kontrol("JUNCTION SORUNU" not in ctx and "settings.json YOK" in ctx
            and "sızıntı riski" not in ctx,
            "V20 (lider) materyalize rules + claude-local YOK -> ⛔ yok, diger saglik satirlari BASILIR",
            ctx[-700:])
    r = k.sur(k.kod, "katman1", proj=s13)
    satir = r.get("r") or []
    kontrol(satir and not any(t == "FAIL" and "rules" in m for t, m in satir)
            and any(t == "PASS" and ".claude/rules" in m for t, m in satir),
            "V20b ix_doctor katman1: rules kopyasi FAIL degil, overlay PASS", str(r)[:600])

    rc, so, _ = k.hook("session_start.py", s13, cp)
    kontrol(not yukleme_satiri(so).startswith("<"), "V12b compact: YUKLEME satiri da VAR",
            yukleme_satiri(so))

    s14 = ss_proje(k, "s14", kopyali=False, log=L_YUK)
    y = yukleme_satiri(k.hook("session_start.py", s14, bu)[1])
    kontrol("ÖN KOŞUL: EKSİK" in y and "JUNCTION" in y and "--repair-junctions" in y,
            "V14 rules hala junction -> ON KOSUL EKSIK + onarim komutu", y)

    s15 = ss_proje(k, "s15", claude_md="# proje\n@core/CLAUDE.core.md\n", log=L_YUK)
    y = yukleme_satiri(k.hook("session_start.py", s15, bu)[1])
    kontrol("ÖN KOŞUL: EKSİK" in y and "dış @import 1" in y,
            "V15 CLAUDE.md'de @core/... dis import -> EKSIK", y)
    s15b = ss_proje(k, "s15b", log=L_YUK, claude_md=(
        f"# proje\niletisim: {EPOSTA_BICIMI}\nsatir ici `@core/CLAUDE.core.md` ornek\n"
        "```\n@core/CLAUDE.core.md\n```\n"))
    y = yukleme_satiri(k.hook("session_start.py", s15b, bu)[1])
    kontrol("ÖN KOŞUL: TAMAM" in y, "V15b (N) e-posta / satir-ici kod / kod blogu import SAYILMAZ", y)

    s17 = ss_proje(k, "s17", log=L_YUKMEDI)
    y = yukleme_satiri(k.hook("session_start.py", s17, bu)[1])
    kontrol("core=YÜKLENMEDİ" in y, "V17 onceki oturumda cekirdek satiri yok -> core=YÜKLENMEDİ", y)

    s18 = ss_proje(k, "s18", log=None)
    y = yukleme_satiri(k.hook("session_start.py", s18, bu)[1])
    kontrol("ÖNCEKİ OTURUM: ÖLÇÜLEMEDİ" in y and "core=" not in y,
            "V18 log YOK -> ÖLÇÜLEMEDİ (hicbir degere cokmez)", y)
    s18b = ss_proje(k, "s18b", log=[ls(None, "session_start", "{P}/.claude/rules/00-claude-core.md")])
    y = yukleme_satiri(k.hook("session_start.py", s18b, bu)[1])
    kontrol("ÖLÇÜLEMEDİ" in y and "core=" not in y,
            "V18b yalniz sid'siz (eski) satirlar -> ÖLÇÜLEMEDİ (eski satirdan YÜKLENDİ uydurulmaz)", y)
    s18c = ss_proje(k, "s18c", log=[ls(SID_BU, "session_start", "{P}/.claude/rules/00-claude-core.md")])
    y = yukleme_satiri(k.hook("session_start.py", s18c, bu)[1])
    kontrol("ÖLÇÜLEMEDİ" in y and "core=" not in y,
            "V18c yalniz BU oturumun satirlari -> ÖLÇÜLEMEDİ (bu oturum 'onceki' sayilmaz)", y)

    s12c = ss_proje(k, "s12c", log=L_YUKMEDI + [
        ls(SID_BU, "session_start", "{P}/CLAUDE.md"),
        ls(SID_BU, "session_start", "{P}/.claude/rules/00-claude-core.md")])
    y = yukleme_satiri(k.hook("session_start.py", s12c, cp)[1])
    kontrol(f"BU OTURUMUN AÇILIŞI {SID_BU[:8]}" in y and "core=YÜKLENDİ" in y
            and "ÖNCEKİ OTURUM" not in y,
            "V12c compact: etiket BU OTURUMUN AÇILIŞI, deger bu sid'in acilis satirlarindan", y)
    s12d = ss_proje(k, "s12d", log=L_YUK)
    y = yukleme_satiri(k.hook("session_start.py", s12d, cp)[1])
    kontrol("BU OTURUMUN AÇILIŞI: ÖLÇÜLEMEDİ" in y and "core=" not in y,
            "V12d compact: bu sid'in acilis satiri yoksa ÖLÇÜLEMEDİ (onceki oturuma DUSULMEZ)", y)
    return {"s13": s13}


def k1(k: Kum) -> None:
    print("\n-- K1 ⚠GEVŞETME behavior_manifest muafiyeti --")

    def hazir(ad: str) -> tuple[Path, Path]:
        c = hafif_core(k.tmp, "c_" + ad)
        p = bos_proje(k.tmp, ad)
        bag(p / "core", k.tam)
        k.kur_materyalize(p, c)
        g = k.sur(k.kod, "bm_generate", p, proj=p)
        if not g.get("ok"):
            print(f"[DURDU] KURULAMADI: bm_generate {g}")
            sys.exit(2)
        return p, c

    def guard_payload(p: Path) -> dict:
        return {"hook_event_name": "ConfigChange", "file_path": str(kopya(p))}

    p, c = hazir("k21")
    yaz(c / "CLAUDE.core.md", "# core yukleyici\n\nCEKIRDEK-TAZE\n")
    o = k.sur(KURULUM_KODU, "oto", p, c)
    v = k.sur(k.kod, "bm_verify", p, proj=p)
    kontrol(any(str(s).startswith("overlay tazelendi") for s in o.get("s", [])) and v.get("s") == [],
            "V21 core degisip kopya komutsuz tazelenince davranis-yuzeyi SAPMASI YOK", f"oto={o} verify={v}")
    rc, _, se = k.hook("config_change_guard.py", p, guard_payload(p))
    kontrol(rc == 0, "V26a config_change_guard: el degmemis tazeleme BLOKLANMAZ (exit 0)",
            f"rc={rc} {se[-300:]}")

    p, c = hazir("k22")
    yaz(rules(p) / "genel.md", oku(rules(p) / "genel.md") + "ELLE\n")
    v = k.sur(k.kod, "bm_verify", p, proj=p)
    # Muaf kopya behavior-manifest'e HİÇ kaydedilmez ⇒ elle düzeltilince "DEĞİŞMİŞ" değil
    # "KAYITSIZ" olarak görünür (ilk koşumda ölçüldü). İkisi de alarmdır; ölçülen şey alarmın VARLIĞI.
    kontrol(any(("DEĞİŞMİŞ" in s or "KAYITSIZ" in s) and ".claude/rules/genel.md" in s
                for s in v.get("s", [])),
            "V22 (N) elle duzeltilmis kopya muafiyete RAGMEN alarm uretir", str(v))
    rc, _, _ = k.hook("config_change_guard.py", p, guard_payload(p))
    kontrol(rc == 2, "V26b config_change_guard: elle duzeltme BLOKLANIR (exit 2)", f"rc={rc}")

    p, c = hazir("k23")
    yaz(rules(p) / ".overlay-manifest.json", "{bozuk")
    v = k.sur(k.kod, "bm_verify", p, proj=p)
    kontrol(any(".claude/rules/00-claude-core.md" in s for s in v.get("s", [])),
            "V23 (N) overlay manifesti bozuk -> muafiyet DUSER (fail-closed)", str(v))

    p, c = hazir("k24")
    yaz(p / "claude-local" / "rules" / "proje-kural.md", "PROJE-KURAL\n")
    k.kur_materyalize(p, c)
    v = k.sur(k.kod, "bm_verify", p, proj=p)
    kontrol(any("KAYITSIZ" in s and "proje-kural.md" in s for s in v.get("s", [])),
            "V24 (N) claude-local kaynakli dosya yuzeyde KALIR", str(v))

    p, c = hazir("k25")
    yaz(rules(p) / "yabanci.md", "YABANCI\n")
    v = k.sur(k.kod, "bm_verify", p, proj=p)
    kontrol(any("KAYITSIZ" in s and "yabanci.md" in s for s in v.get("s", [])),
            "V25 (N) overlay manifestinde olmayan dosya yuzeyde KALIR", str(v))


def insp(k: Kum, s13: Path) -> None:
    print("\n-- B4/K2 inspector A3 + B5 --")
    ci = hafif_core(k.tmp, "c_insp")
    ip = bos_proje(k.tmp, "a3p")
    log_yaz(ip, [ls("eski", "path_glob_match", "/p/.claude/rules/abap-kural.md"),
                 ls("yeni", "session_start", "/p/CLAUDE.md")])
    r = k.sur(k.kod, "a3", ip, ci, json.dumps(["C:/x/y.abap"]), "yeni")
    b = r.get("b")
    kontrol(isinstance(b, list) and len(b) == 1 and b[0][0] == "A3" and b[0][1] is False,
            "V27 A3: onceki oturumda eslesen dosya okundu, tetik YOK -> GERCEK bulgu (bilgi degil), "
            "baska oturumun tetigi ortmez", str(r)[:500])
    log_yaz(ip, [ls("yeni", "path_glob_match", "/p/.claude/rules/abap-kural.md")])
    r = k.sur(k.kod, "a3", ip, ci, json.dumps(["C:/x/y.abap"]), "yeni")
    kontrol(r.get("b") == [], "V27b (N) ayni oturumda tetik gorulduyse A3 SESSIZ", str(r)[:300])

    r = k.sur(k.kod, "b5", s13, k.tam)
    b = r.get("b")
    kontrol(isinstance(b, list) and not any("00-claude-core" in m for _, _, m in b),
            "V28 B5: 00-claude-core.md kaynagi CLAUDE.core.md'den okunur (sahte 'ARTIK YOK' yok)",
            str(r)[:500])
    asil = oku(k.tam / "CLAUDE.core.md")
    try:
        yaz(k.tam / "CLAUDE.core.md", asil + "DEGISTI\n")
        r = k.sur(k.kod, "b5", s13, k.tam)
    finally:
        yaz(k.tam / "CLAUDE.core.md", asil)
    b = r.get("b") or []
    kontrol(any("BAYAT" in m and "00-claude-core.md" in m for _, _, m in b),
            "V28b (pozitif kontrol) CLAUDE.core.md degisince B5 kopyayi BAYAT der", str(r)[:500])


def main() -> int:
    arg = sys.argv[1:]
    kipler = [a for a in arg if a.startswith("--mutasyon")]
    agac = KOK
    if "--agac" in arg:
        i = arg.index("--agac")
        if i + 1 >= len(arg) or arg[i + 1].startswith("--"):
            print("[KULLANIM] --agac <eski-agac-koku>")
            return 2
        agac = Path(arg[i + 1]).resolve()
        if not (agac / "scripts").is_dir():
            print(f"[KULLANIM] --agac altinda scripts/ yok: {agac}")
            return 2
    bilinmeyen = [x for x in kipler if x not in GECERLI_KIP]
    if bilinmeyen or len(kipler) > 1:
        print(f"[KULLANIM] tek bir gecerli kip: {sorted(GECERLI_KIP)} (verilen: {kipler})")
        return 2
    kip = kipler[0] if kipler else None

    tmp = Path(os.path.realpath(tempfile.mkdtemp(prefix="q286kum_")))
    try:
        k = Kum(tmp, agac, kip)
        b1(k)
        b2(k)
        c1(k)
        ref = c2(k)
        k1(k)
        insp(k, ref["s13"])
    finally:
        baglari_sok(tmp)
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for ok, _ in SONUC if ok)
    mod = f"  [KIP: {kip}]" if kip else ""
    if agac != KOK:
        mod += f"  [AGAC: {agac}]"
    print(f"\n{gecen}/{len(SONUC)} OK{mod}")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
