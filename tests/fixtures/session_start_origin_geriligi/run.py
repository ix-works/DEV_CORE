#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""session_start_origin_geriligi — core gerilik sayısı ÖNBELLEKTEN değil, YERELDEN (Q337).

KUSUR (Issue #276, 2026-09-18): `_origin_kontrol` önbelleğe (`.tmp/.core_fetch_cache.json`)
`{"ts", "behind"}` yazıyor ve `behind`'i 1 SAAT yeniden kullanıyordu. Araya giren
`git -C core pull` önbelleği geçersiz kılmadığı için pull SONRASI açılan oturum olmayan
bir geriliği bildiriyordu (ölçülen: bildirilen 10, gerçek 0). Ters yön de aynı mekanizma:
elle `git fetch` sonrası gerilik 1 saat görünmüyordu.

FIX: önbellek YALNIZ son fetch zamanını tutar; sayı HER çağrıda yerel
`rev-list --count HEAD..origin/main` (ağsız). Throttle'lanan şey AĞDIR (fetch, saatte 1) —
o DEĞİŞMEDİ ve S4 bunu çiviler.

⭐ GERÇEK GİRİŞ NOKTASI: hook ALT SÜREÇTE koşulur (`CLAUDE_PROJECT_DIR` = sandbox). Sandbox
proje `core` + `.claude/{agents,skills,commands}` BAĞLARINI taşır — yoksa `_junction_kontrol`
⛔ dalına düşer ve `_origin_kontrol` HİÇ çağrılmaz (kablolama ölçülmemiş olurdu). `core`
bağının hedefi yerel bir çıplak `origin`'in klonudur; ağ kullanılmaz.

VEKTÖRLER
  S1  ISSUE VAKASI: HEAD==origin/main (gerçek 0) + TAZE eski-biçim önbellek `behind:10`
      → gerilik satırı YOK (eski kod "10 commit" derdi)
  S2  TERS YÖN: elle fetch sonrası origin/main 2 ileride + TAZE önbellek `behind:0` → "2 commit"
  S3  PULL: ff-merge sonrası (gerçek 0) + TAZE önbellek → satır YOK
  S4  THROTTLE KORUNDU: upstream'e yeni commit + TAZE önbellek → fetch YAPILMAZ
      (origin/main ref'i ve önbellek `ts`'i DEĞİŞMEZ) ⇒ satır YOK
  S5  SÜRESİ DOLMUŞ önbellek → fetch yapılır → "1 commit"; yeni önbellek YALNIZ `ts` taşır
  S6  BOZUK önbellek → süresi dolmuş sayılır (çökmeden) → sayım doğru
  S7  her koşumda exit 0 + geçerli JSON (oturum açılışı BOZULMAZ)
  S8  3. BAĞLAM: origin'siz core deposu → satır YOK, exit 0
MUTASYON (bugünkü kaynaktan; çapa tam 1 kez bulunmazsa exit 2):
  --mutasyon-onbellek-sayi  sayı önbellekteki `behind`'den okunur → S1 · S2 düşer
  --mutasyon-her-fetch      throttle kalkar (her çağrıda fetch)   → S4 düşer
TABAN (eski kod): --kaynak <session_start.py>

Çıkış: 0 beklendiği gibi · 1 sapma · 2 KURULAMADI
"""
from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
HOOK = REPO / "scripts" / "hooks" / "session_start.py"
GERI_RE = re.compile(r"DEV_CORE origin'in (\d+) commit GERISINDE")

GECERLI_KIP = ("--mutasyon-onbellek-sayi", "--mutasyon-her-fetch")
KIP: set[str] = set()
TABAN: Path | None = None
_a = sys.argv[1:]
while _a:
    x = _a.pop(0)
    if x == "--kaynak" and _a:
        TABAN = Path(_a.pop(0)).resolve()
    elif x in GECERLI_KIP:
        KIP.add(x)
    else:
        print(f"[DURDU] bilinmeyen arguman: {x!r} — gecerli: {list(GECERLI_KIP)} + --kaynak")
        sys.exit(2)

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul), detay))
    print(f"  [{'OK' if kosul else 'FAIL'}] {ad}" + (f"  -- {detay}" if not kosul and detay else ""))


def _dur(neden: str) -> None:
    print(f"[DURDU] KURULAMADI: {neden} (sayi raporlanmiyor — KURULAMADI != KACTI)")
    sys.exit(2)


def _degistir(metin: str, eski: str, yeni: str, ad: str) -> str:
    n = metin.count(eski)
    if n != 1:
        _dur(f"{ad} capasi {n} kez bulundu (1 bekleniyordu): {eski[:70]!r}")
    return metin.replace(eski, yeni)


def _kaynak() -> str | None:
    if TABAN is not None:
        return TABAN.read_text(encoding="utf-8")
    if not KIP:
        return None
    m = HOOK.read_text(encoding="utf-8")
    if "--mutasyon-onbellek-sayi" in KIP:
        m = _degistir(m, "    behind = _core_geri_sayisi()\n",
                      "    try:\n        behind = int(json.loads(cache.read_text(encoding='utf-8'))"
                      ".get('behind', _core_geri_sayisi()))\n    except Exception:\n"
                      "        behind = _core_geri_sayisi()\n", "onbellek-sayi")
    if "--mutasyon-her-fetch" in KIP:
        m = _degistir(m, "    if simdi - son_fetch > 3600:  # saatte 1\n", "    if True:\n", "her-fetch")
    return m


def _hook_yolu(tmp: Path) -> Path:
    """Taban/mutant KUM `scripts/hooks/`e yazılır (utils kopyası komşu) — hook, D7 imzasını
    `Path(__file__).resolve().parents[1]`den import eder; gerçek kaynağa DOKUNULMAZ."""
    m = _kaynak()
    if m is None:
        return HOOK
    hooks = tmp / "kum" / "scripts" / "hooks"
    hooks.mkdir(parents=True)
    shutil.copytree(REPO / "scripts" / "utils", hooks.parent / "utils",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    p = hooks / "session_start_kum.py"
    p.write_text(m, encoding="utf-8", newline="\n")
    return p


def _git(d: Path, *args: str, check: bool = True) -> str:
    r = subprocess.run(["git", "-C", str(d), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    if check and r.returncode != 0:
        _dur(f"git {' '.join(args)} (rc={r.returncode}): {r.stderr.strip()[:200]}")
    return (r.stdout or "").strip()


def _kimlik(d: Path) -> None:
    # ⚠ e-posta BİÇİMLİ değer yazma — GENERICIZE guard'ı kimlik izi sayar.
    _git(d, "config", "user.email", "fixture")
    _git(d, "config", "user.name", "fixture")


def _commit(d: Path, ad: str) -> None:
    (d / f"{ad}.txt").write_text(ad + "\n", encoding="utf-8")
    _git(d, "add", "-A")
    _git(d, "commit", "-q", "-m", ad)
    _git(d, "push", "-q", "origin", "HEAD:main")


def _bag(link: Path, hedef: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        import _winapi  # type: ignore
        _winapi.CreateJunction(str(hedef), str(link))
    else:
        os.symlink(str(hedef), str(link), target_is_directory=True)


def _bag_mi(p: Path) -> bool:
    try:
        os.readlink(p)
        return True
    except (OSError, ValueError):
        return False


def _sil(d: Path) -> None:
    for dp, dns, _ in os.walk(d):                     # önce BAĞLAR (hedefe girilmez)
        for dn in list(dns):
            p = Path(dp) / dn
            if _bag_mi(p):
                try:
                    os.rmdir(p)
                except OSError:
                    try:
                        os.unlink(p)
                    except OSError:
                        pass
                dns.remove(dn)

    def _ac(func, path, _exc):  # noqa: ANN001
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass
    kw = {"onexc": _ac} if sys.version_info >= (3, 12) else {"onerror": _ac}
    try:
        shutil.rmtree(d, **kw)  # type: ignore[arg-type]
    except Exception:
        shutil.rmtree(d, ignore_errors=True)


def sandbox(tmp: Path, ad: str, core_hedef: Path) -> Path:
    p = tmp / ad
    (p / ".claude").mkdir(parents=True)
    _bag(p / "core", core_hedef)
    for t in ("agents", "skills", "commands"):
        (tmp / f"bos_{ad}_{t}").mkdir()
        _bag(p / ".claude" / t, tmp / f"bos_{ad}_{t}")
    return p


def onbellek(p: Path, veri) -> Path:
    c = p / ".tmp" / ".core_fetch_cache.json"
    c.parent.mkdir(parents=True, exist_ok=True)
    c.write_text(veri if isinstance(veri, str) else json.dumps(veri), encoding="utf-8")
    return c


def kos(hook: Path, p: Path) -> tuple[int, str, int | None]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("IX_")}
    env["CLAUDE_PROJECT_DIR"] = str(p)
    r = subprocess.run([sys.executable, str(hook)], input=b"{}", capture_output=True,
                       cwd=str(p), env=env, timeout=120)
    out = (r.stdout or b"").decode("utf-8", "replace")
    try:
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    except Exception:
        ctx = None
    if ctx is None:
        return r.returncode, "", None
    m = GERI_RE.search(ctx)
    return r.returncode, ctx, (int(m.group(1)) if m else 0)


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="ix_origin_"))
    kodlar: list[tuple[int, bool]] = []
    try:
        hook = _hook_yolu(tmp)
        origin = tmp / "origin.git"
        _git(tmp, "init", "-q", "--bare", "-b", "main", str(origin))
        yazar = tmp / "yazar"
        _git(tmp, "clone", "-q", str(origin), str(yazar), check=False)
        _kimlik(yazar)
        _git(yazar, "symbolic-ref", "HEAD", "refs/heads/main")
        _commit(yazar, "c1")
        core = tmp / "core_klon"
        _git(tmp, "clone", "-q", "-b", "main", str(origin), str(core))
        p = sandbox(tmp, "proje", core)

        def kayit(rc, ctx, n):
            kodlar.append((rc, ctx is not None and n is not None))

        # S1 — issue vakası
        onbellek(p, {"ts": time.time(), "behind": 10})
        rc, ctx, n = kos(hook, p)
        kayit(rc, ctx, n)
        kontrol("S1 HEAD==origin/main + TAZE eski-bicim onbellek behind:10 → gerilik satiri YOK",
                n == 0, f"bildirilen={n} rc={rc} ctx_sonu={ctx[-200:]!r}")

        # S2 — ters yön
        _commit(yazar, "c2")
        _commit(yazar, "c3")
        _git(core, "fetch", "-q", "origin", "main")
        onbellek(p, {"ts": time.time(), "behind": 0})
        rc, ctx, n = kos(hook, p)
        kayit(rc, ctx, n)
        kontrol("S2 elle fetch (origin/main +2) + TAZE onbellek behind:0 → '2 commit'",
                n == 2, f"bildirilen={n} rc={rc}")

        # S3 — pull
        _git(core, "merge", "-q", "--ff-only", "origin/main")
        c = onbellek(p, {"ts": time.time()})
        rc, ctx, n = kos(hook, p)
        kayit(rc, ctx, n)
        kontrol("S3 ff-pull sonrasi + TAZE onbellek → satir YOK", n == 0, f"bildirilen={n}")

        # S4 — throttle korundu
        _commit(yazar, "c4")
        ref_once = _git(core, "rev-parse", "refs/remotes/origin/main")
        ts_once = json.loads(c.read_text(encoding="utf-8"))["ts"]
        rc, ctx, n = kos(hook, p)
        kayit(rc, ctx, n)
        ref_sonra = _git(core, "rev-parse", "refs/remotes/origin/main")
        ts_sonra = json.loads(c.read_text(encoding="utf-8"))["ts"]
        kontrol("S4 THROTTLE: taze onbellekte fetch YAPILMAZ (ref + ts degismez) → satir YOK",
                n == 0 and ref_once == ref_sonra and ts_once == ts_sonra,
                f"bildirilen={n} ref_degisti={ref_once != ref_sonra} ts_degisti={ts_once != ts_sonra}")

        # S5 — süresi dolmuş
        onbellek(p, {"ts": time.time() - 7200, "behind": 99})
        rc, ctx, n = kos(hook, p)
        kayit(rc, ctx, n)
        yeni = json.loads(c.read_text(encoding="utf-8"))
        kontrol("S5 suresi dolmus → fetch → '1 commit'; yeni onbellek YALNIZ `ts` tasir",
                n == 1 and set(yeni) == {"ts"} and time.time() - float(yeni["ts"]) < 120,
                f"bildirilen={n} onbellek={yeni}")

        # S6 — bozuk önbellek
        onbellek(p, "{bozuk")
        rc, ctx, n = kos(hook, p)
        kayit(rc, ctx, n)
        kontrol("S6 BOZUK onbellek → cokmeden suresi dolmus sayilir, sayim dogru ('1 commit')",
                n == 1, f"bildirilen={n} rc={rc}")

        # S8 — 3. bağlam: origin'siz core
        yalin = tmp / "originsiz_core"
        yalin.mkdir()
        _git(yalin, "init", "-q", "-b", "main")
        _kimlik(yalin)
        (yalin / "x.txt").write_text("x\n", encoding="utf-8")
        _git(yalin, "add", "-A")
        _git(yalin, "commit", "-q", "-m", "x")
        p8 = sandbox(tmp, "proje8", yalin)
        rc, ctx, n = kos(hook, p8)
        kayit(rc, ctx, n)
        kontrol("S8 3. BAGLAM origin'siz core → satir YOK, exit 0", n == 0 and rc == 0,
                f"bildirilen={n} rc={rc}")

        kontrol("S7 her kosumda exit 0 + gecerli JSON (oturum acilisi BOZULMAZ)",
                bool(kodlar) and all(rc == 0 and ok for rc, ok in kodlar), f"{kodlar}")
    finally:
        _sil(tmp)

    ok = sum(1 for _, k, _ in SONUC if k)
    etiket = f" [TABAN {TABAN}]" if TABAN else (f" [{' '.join(sorted(KIP))}]" if KIP else "")
    print(f"\nsession_start_origin_geriligi{etiket}: {ok}/{len(SONUC)} PASS")
    return 0 if ok == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
