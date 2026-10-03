#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RECALL TEKRAR BASTIRMA (K1) — `scripts/hooks/recall_inject.py` oturum-ici tekrar korpusu.

NEDEN BU KORPUS VAR
-------------------
JIT-recall'un oturum bellegi yoktu: ayni ders ayni baglam penceresinde her prompt'ta (ajan
mesajlari dahil) yeniden basiliyordu (radar 2026-10-03: compaction'da sifirlanarak sayildiginda
karakterlerin %41'i ayni pencerede tekrar). K1: `.tmp/recall-shown/<session_id>.json` kaydi +
transkriptteki `compact_boundary` satiri pencere siniri. Kusurlar SESSIZDIR (hook exit 0 doner,
yalniz ne basildigi degisir) ⇒ korpus BASILAN DERS LISTESINI olcer, exit kodunu degil.

Uc sessiz kusur sinifi:
  · TEKRAR (eski davranis)      : ayni ders ayni pencerede yine basilir           -> B2/B4/B19a
  · KAYIP DERS (gevsetme yonu)  : compact sonrasi ders GERI GELMEZ                 -> B5/B6/B19b/B21
  · SAHTE SIFIRLAMA / FAIL-CLOSED: kaçisli metin sinir sanilir · kanitlanamayan pencerede
                                  bastirilir · yazma hatasi dersi yutar           -> B7-B9 · B14 · B15

VEKTORLER
  B1  ilk prompt: TOP_K (alfa,bravo,carli) basilir, kayit dogar
  B2  ayni prompt ayni pencere: CIKTI YOK (rc 0)
  B3  ONE CIKARMA YOK: P0 uc dersi basti; P1'de delta 4. aday -> bastirma onu one CIKARMAZ
  B3b BASILMAMIS ders "gosterildi" sayilmaz: ayni pencerede delta kendi prompt'unda basilir
  B4  kismi ortusme: P2 -> bravo dusulur, ekko+foxt AYNI SIRAYLA basilir
  B5  ⭐ compact_boundary (trigger=manual) -> P1 YENIDEN basilir
  B5b sifirlamadan sonra pencere yeniden kurulur (P1 tekrar -> cikti yok)
  B6  ⭐ compact_boundary (trigger=auto) -> P2'nin uc dersi YENIDEN basilir
  B7  NEGATIF: kacisli STRING icinde "compact_boundary" (tool_result metni) SIFIRLAMAZ
  B8  NEGATIF: YAPISAL ama ic ice nesne (ust duzey type=user) SIFIRLAMAZ  [satir dogrulamasi]
  B9  NEGATIF: yarim son satir, yalniz kacisli metin tasiyor -> SIFIRLAMAZ   [tirnakli desen]
  B10 paralel oturum (ayri sid + ayri transkript) digerinin kaydindan etkilenmez
  B10b ⭐ ARALI oturumlar (sid1 · sid2 · sid1): sid1'in kaydi sid2 tarafindan EZILMEZ
  B11 session_id YOK -> bugunku davranis (iki kez de basar)
  B12 transcript_path YOK -> bugunku davranis
  B13 bozuk kayit -> fail-open basar + kayit gecerli JSON olarak yeniden yazilir
  B14 transkript KUCULDU (ofset > boyut) -> pencere kanitlanamaz -> basar
  B14b iki enjeksiyon arasi buyume tarama tavanini (64 MB) asar -> kanitlanamaz -> basar
  B15 kayit dizini YAZILAMAZ (ayni adda DOSYA) -> iki kez de basar, rc 0, traceback yok
  B16 bayat kayit budamasi: yeni oturum dogarken 8 gunluk kayit silinir, 1 gunluk kalir
  B17 ⭐ GERCEK GIRIS NOKTASI: hook_shim (claude/hook_shim.template.py kopyasi) uzerinden
      bas · bastir · compact sonrasi yeniden bas  (kod != kablolama)
  B19 SENTETIK OLCUM (radar K1 olcutunun temsili dizisi): 30 prompt, 3 prompt dongusu,
      15'ten sonra compact -> (a) ayni pencerede tekrar = 0 (b) compact sonrasi her ders
      yeniden gorunur; karakter ozeti bilgi olarak basilir
  B21 3. BAGLAM: CRLF satir sonlu transkriptte compact_boundary yine sifirlar

KOSUM:
    python tests/fixtures/recall_tekrar_bastirma/run.py [--mutasyon-<kip>]
    python tests/run_battery.py recall_tekrar_bastirma
Cikis: 0 hepsi beklendigi gibi · 1 mutasyon BEKLENEN kumeyle AYNEN dustu · 2 DOGRULANAMADI
(capa bayat/derlenmedi/kontrol grubu bozuk/dusen kume BEKLENEN_DUSUS'ten farkli — CORE-07)

⛔ MUTASYON GERCEK KAYNAGA YAZILMAZ: mutant gecici agaca (hook + uretec kopyasi) kurulur; ONCE
ayni agactaki MUTASYONSUZ ikiz kosulur ve gercek dosyayla ayni ders listesini vermezse sonuc
DOGRULANAMADI'dir (olculen sey mutasyon degil ortam olurdu).
"""
from __future__ import annotations

import json
import os
import py_compile
import shutil
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
HOOK = REPO / "scripts" / "hooks" / "recall_inject.py"
URETEC = REPO / "scripts" / "build_recall_index.py"
SHIM = REPO / "claude" / "hook_shim.template.py"

# (eski, yeni) — CORE-07: eski TAM 1 kez eslesmeli.
CAPA = {
    "--mutasyon-dedup-yok": (
        "        basilacak = [x for x in adaylar if _ders_kimligi(x[1]) not in gosterilen]\n",
        "        basilacak = list(adaylar)  # MUTASYON: tekrar bastirma sokuldu\n"),
    "--mutasyon-sifirlama-yok": (
        "        if _sinir_satiri_mi(blok[bas:son]):\n            return True, boy\n",
        "        if False:  # MUTASYON: compact sifirlamasi sokuldu\n            return True, boy\n"),
    "--mutasyon-satir-dogrulama-yok": (
        '    return isinstance(d, dict) and d.get("type") == "system" and d.get("subtype") == "compact_boundary"\n',
        "    return True  # MUTASYON: satir dogrulamasi sokuldu\n"),
    "--mutasyon-tirnaksiz-desen": (
        "_SINIR = b'\"subtype\":\"compact_boundary\"'\n",
        "_SINIR = b'compact_boundary'  # MUTASYON: tirnaksiz desen\n"),
    "--mutasyon-sid-ortak": (
        '        yol = dizin / (sid + ".json")\n',
        '        yol = dizin / "ortak.json"  # MUTASYON: oturum anahtari yok\n'),
    "--mutasyon-kanitsiz-bastir": (
        "            if sinir is False:\n",
        "            if sinir is not True:  # MUTASYON: kanitlanamayan pencerede de bastir\n"),
    "--mutasyon-one-cikar": (
        "    secilen = _tekrar_bastir(proj, data if isinstance(data, dict) else {}, skorlu[:TOP_K])\n",
        "    secilen = _tekrar_bastir(proj, data if isinstance(data, dict) else {}, skorlu)[:TOP_K]"
        "  # MUTASYON\n"),
    "--mutasyon-budama-yok": (
        "            if yeni_dosya:\n                _bayatlari_sil(dizin)\n",
        "            if False:  # MUTASYON: budama sokuldu\n                _bayatlari_sil(dizin)\n"),
    "--mutasyon-yazma-fail-closed": (
        "            pass                                # yazılamadı",
        "            return []  # MUTASYON: yazma hatasi dersi yutar"),
}
# CORE-07: kip -> dusmesi BEKLENEN vektor kimlikleri (ESITLIK; alt-kume degil). OLCULDU.
# sid-ortak: B1/B13/B16 kayit DOSYA ADINI (= oturum anahtarini) olcer; B10b davranisi olcer.
# one-cikar: mutant TUM adaylari "gosterildi" yazar -> B3 (one cikti) + B3b (basilmayan yutuldu).
BEKLENEN_DUSUS = {
    "--mutasyon-dedup-yok": {"B2", "B3", "B4", "B5b", "B7", "B8", "B9", "B10b", "B17b", "B19a"},
    "--mutasyon-sifirlama-yok": {"B5", "B6", "B17c", "B19b", "B21"},
    "--mutasyon-satir-dogrulama-yok": {"B8"},
    "--mutasyon-tirnaksiz-desen": {"B9"},
    "--mutasyon-sid-ortak": {"B1", "B10b", "B13", "B16"},
    "--mutasyon-kanitsiz-bastir": {"B14", "B14b"},
    "--mutasyon-one-cikar": {"B3", "B3b"},
    "--mutasyon-budama-yok": {"B16"},
    "--mutasyon-yazma-fail-closed": {"B15"},
}

SONUC: list[tuple[str, bool, str]] = []
_GECICI: list[str] = []


def ekle(kimlik: str, ad: str, ok: bool, not_: str = "") -> None:
    SONUC.append((kimlik, ok, f"{ad}" + (f"   -> {not_}" if not ok and not_ else "")))


def _tmp(onek: str = "recalltekrar_") -> Path:
    d = Path(tempfile.mkdtemp(prefix=onek))
    _GECICI.append(str(d))
    return d


def temizle() -> None:
    for d in _GECICI:
        shutil.rmtree(d, ignore_errors=True)


# ── indeks: her ders tek, benzersiz bir token tasir; tekrar sayisi skoru (ve sirayi) belirler ──
def _k(ad: str, tekrar: int) -> dict:
    return {"id": f"mem:{ad}.md", "kaynak": f"memory/{ad}.md", "baslik": f"{ad} dersi",
            "oz": f"{ad} ozeti", "anahtar": [ad] * tekrar}


KAYITLAR = [_k("alfa", 7), _k("bravo", 6), _k("carli", 5), _k("delta", 5), _k("ekko", 5),
            _k("foxt", 5), _k("golf", 5), _k("hotel", 5), _k("indi", 5), _k("julet", 5)]
P0 = "alfa bravo carli konusunda bir sey soracagim lutfen bak"
P1 = "alfa bravo carli delta konusunda bir sey soracagim lutfen bak"
P4 = "delta konusunda ayrica bir sey soracagim lutfen bak"
P2 = "bravo ekko foxt konusunda bir sey soracagim lutfen bak"
P3 = "golf hotel indi julet konusunda bir sey soracagim lutfen bak"


def proje_kur(kok: Path) -> Path:
    proj = kok / "proje"
    (proj / ".tmp").mkdir(parents=True, exist_ok=True)
    hp = proj / ".tmp" / "recall-index.json"
    hp.write_text(json.dumps({"v": 1, "kayit": KAYITLAR}), encoding="utf-8")
    ileri = time.time() + 30 * 86400       # gelecege damga -> tazeleme KOSMAZ, yalniz secim olculur
    os.utime(hp, (ileri, ileri))
    (kok / "cfg").mkdir(exist_ok=True)
    return proj


def ortam(proj: Path, cfg: Path) -> dict:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(proj)
    env["CLAUDE_CONFIG_DIR"] = str(cfg)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def hook_kos(hook: Path, proj: Path, prompt: str, sid: str | None = None,
             tp: Path | None = None, via: Path | None = None) -> tuple[int, str, str]:
    data: dict = {"prompt": prompt, "hook_event_name": "UserPromptSubmit"}
    if sid is not None:
        data["session_id"] = sid
    if tp is not None:
        data["transcript_path"] = str(tp)
    cmd = [sys.executable, str(hook)] if via is None else [sys.executable, str(via), "recall_inject"]
    p = subprocess.run(cmd, input=json.dumps(data).encode("utf-8"), env=ortam(proj, proj.parent / "cfg"),
                       cwd=str(proj), capture_output=True, timeout=120)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def dersler(out: str) -> list[str] | None:
    """Basilan derslerin SIRALI listesi; cikti yoksa []; gecersiz JSON ise None."""
    if not out.strip():
        return []
    try:
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    except Exception:
        return None
    return [ln.split("[memory/", 1)[1].split(".md]", 1)[0] for ln in ctx.splitlines() if "[memory/" in ln]


def tp_ekle(tp: Path, satirlar: list[str], son: str = "\n") -> None:
    with tp.open("a", encoding="utf-8", newline="") as f:
        for s in satirlar:
            f.write(s + son)


def _kullanici(metin: str) -> str:
    return json.dumps({"type": "user", "message": {"role": "user", "content": metin}})


def _asistan(metin: str) -> str:
    return json.dumps({"type": "assistant", "message": {"role": "assistant",
                                                        "content": [{"type": "text", "text": metin}]}})


def _sinir(tetik: str) -> str:
    # Gercek satirin alan sirasi ve alanlari (ham transkriptten, 2.1.288; kimlikler sentetik)
    return json.dumps({"parentUuid": None, "logicalParentUuid": "00000000-0000-0000-0000-000000000001",
                       "isSidechain": False, "type": "system", "subtype": "compact_boundary",
                       "content": "Conversation compacted", "level": "info",
                       "compactMetadata": {"trigger": tetik, "preTokens": 345313, "postTokens": 10552}},
                      separators=(",", ":"))


# ─────────────────────────────────────────────────────────────────────────────
def vektorler(hook: Path) -> None:
    kok = _tmp()
    proj = proje_kur(kok)
    tp = kok / "s1.jsonl"                     # ilk prompt'ta transkript YOK (canli olcum boyle)
    kayit = proj / ".tmp" / "recall-shown" / "sid-1.json"

    rc, out, err = hook_kos(hook, proj, P1, "sid-1", tp)
    d = dersler(out)
    ekle("B1", "ilk prompt TOP_K basar + kayit dogar",
         rc == 0 and d == ["alfa", "bravo", "carli"] and kayit.is_file(),
         f"rc={rc} d={d} kayit={kayit.is_file()} err={err[:160]!r}")
    tp_ekle(tp, [_kullanici(P1), _asistan("cevap 1")])

    rc, out, _ = hook_kos(hook, proj, P1, "sid-1", tp)
    d = dersler(out)
    ekle("B2", "ayni prompt ayni pencere -> CIKTI YOK", rc == 0 and d == [], f"rc={rc} d={d}")
    tp_ekle(tp, [_kullanici(P1), _asistan("cevap 2")])

    # B3/B3b ayri pencerede: P0 (delta'siz) uc dersi basar; sonra P1'de delta 4. aday
    kok3 = _tmp()
    proj3 = proje_kur(kok3)
    tp3 = kok3 / "s3.jsonl"
    hook_kos(hook, proj3, P0, "sid-b3", tp3)
    tp_ekle(tp3, [_kullanici(P0)])
    d = dersler(hook_kos(hook, proj3, P1, "sid-b3", tp3)[1])
    ekle("B3", "TOP_K disindaki 4. aday (delta) bastirma ile one CIKARILMAZ", d == [], f"d={d}")
    tp_ekle(tp3, [_kullanici(P1)])
    d = dersler(hook_kos(hook, proj3, P4, "sid-b3", tp3)[1])
    ekle("B3b", "BASILMAMIS ders 'gosterildi' sayilmaz (delta kendi prompt'unda basilir)",
         d == ["delta"], f"d={d}")

    rc, out, _ = hook_kos(hook, proj, P2, "sid-1", tp)
    d = dersler(out)
    ekle("B4", "kismi ortusme: bravo duser, ekko+foxt sirayla", d == ["ekko", "foxt"], f"d={d}")
    tp_ekle(tp, [_kullanici(P2), _asistan("cevap 3")])

    tp_ekle(tp, [_sinir("manual")])
    rc, out, _ = hook_kos(hook, proj, P1, "sid-1", tp)
    d = dersler(out)
    ekle("B5", "compact (manual) -> P1 yeniden basilir", d == ["alfa", "bravo", "carli"], f"d={d}")
    tp_ekle(tp, [_kullanici(P1), _asistan("cevap 4")])
    rc, out, _ = hook_kos(hook, proj, P1, "sid-1", tp)
    d = dersler(out)
    ekle("B5b", "sifirlama sonrasi pencere yeniden kurulur", d == [], f"d={d}")

    tp_ekle(tp, [_sinir("auto")])
    rc, out, _ = hook_kos(hook, proj, P2, "sid-1", tp)
    d = dersler(out)
    ekle("B6", "compact (auto) -> P2'nin uc dersi yeniden", d == ["bravo", "ekko", "foxt"], f"d={d}")

    # B7-B9: P1 bu pencerede once basilsin (alfa,carli; bravo zaten basildi)
    hook_kos(hook, proj, P1, "sid-1", tp)
    tp_ekle(tp, [json.dumps({"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "t1",
         "content": 'grep ciktisi: {"type":"system","subtype":"compact_boundary"} satiri'}]}})])
    rc, out, _ = hook_kos(hook, proj, P1, "sid-1", tp)
    d = dersler(out)
    ekle("B7", "kacisli string icindeki sinir metni SIFIRLAMAZ", d == [], f"d={d}")

    tp_ekle(tp, [json.dumps({"type": "user", "toolUseResult": {"type": "system",
                                                               "subtype": "compact_boundary"}},
                            separators=(",", ":"))])
    rc, out, _ = hook_kos(hook, proj, P1, "sid-1", tp)
    d = dersler(out)
    ekle("B8", "ic ice YAPISAL nesne (ust duzey user) SIFIRLAMAZ", d == [], f"d={d}")

    yarim = json.dumps({"type": "user", "message": {"content": 'x {"subtype":"compact_boundary"} y'}})
    tp_ekle(tp, [yarim[: len(yarim) - 6]], son="")          # yarim son satir, newline yok
    rc, out, _ = hook_kos(hook, proj, P1, "sid-1", tp)
    d = dersler(out)
    ekle("B9", "yarim son satir (kacisli metin) SIFIRLAMAZ", d == [], f"d={d}")
    tp_ekle(tp, ["", _asistan("devam")])

    # B10/B10b paralel ve arali oturumlar
    tp2 = kok / "s2.jsonl"
    rc, out, _ = hook_kos(hook, proj, P1, "sid-2", tp2)
    d = dersler(out)
    ekle("B10", "paralel oturum kendi ilk gosterimini alir", d == ["alfa", "bravo", "carli"], f"d={d}")
    tp_ekle(tp2, [_kullanici(P1)])
    rc, out, _ = hook_kos(hook, proj, P1, "sid-1", tp)
    d = dersler(out)
    ekle("B10b", "arali oturum: sid1 kaydi sid2 tarafindan ezilmez", d == [], f"d={d}")

    # B11/B12 kimliksiz -> bugunku davranis
    d1 = dersler(hook_kos(hook, proj, P1)[1])
    d2 = dersler(hook_kos(hook, proj, P1)[1])
    ekle("B11", "session_id yok -> iki kez de basar", d1 == d2 == ["alfa", "bravo", "carli"], f"{d1} {d2}")
    d1 = dersler(hook_kos(hook, proj, P1, "sid-3")[1])
    d2 = dersler(hook_kos(hook, proj, P1, "sid-3")[1])
    ekle("B12", "transcript_path yok -> iki kez de basar", d1 == d2 == ["alfa", "bravo", "carli"], f"{d1} {d2}")

    # B13 bozuk kayit
    tp4 = kok / "s4.jsonl"
    tp_ekle(tp4, [_kullanici("x")])
    k4 = proj / ".tmp" / "recall-shown" / "sid-4.json"
    k4.parent.mkdir(parents=True, exist_ok=True)   # eski kodda dizin hic dogmaz (kurulum cokmesin)
    k4.write_text("{bozuk", encoding="utf-8")
    rc, out, err = hook_kos(hook, proj, P1, "sid-4", tp4)
    d = dersler(out)
    try:
        gecerli = isinstance(json.loads(k4.read_text(encoding="utf-8")).get("gosterilen"), list)
    except Exception:
        gecerli = False
    ekle("B13", "bozuk kayit -> basar + kayit yeniden gecerli",
         rc == 0 and d == ["alfa", "bravo", "carli"] and gecerli, f"rc={rc} d={d} gecerli={gecerli}")

    # B14 transkript kuculdu
    tp_ekle(tp4, [_kullanici("uzun " * 200)])
    hook_kos(hook, proj, P1, "sid-4", tp4)                  # ofset buyuk dosyada kayitli
    tp4.write_text(_kullanici("kisa") + "\n", encoding="utf-8")
    rc, out, _ = hook_kos(hook, proj, P1, "sid-4", tp4)
    d = dersler(out)
    ekle("B14", "transkript kuculdu -> kanitlanamaz -> basar", d == ["alfa", "bravo", "carli"], f"d={d}")

    # B14b iki enjeksiyon arasi buyume _TARAMA_TAVANI'ni (64 MB) asar -> kanitlanamaz -> basar
    tp_ekle(tp4, [_kullanici(P1)])
    with tp4.open("r+b") as f:
        f.seek(65 * 1024 * 1024)
        f.write(b"\n")
    rc, out, _ = hook_kos(hook, proj, P1, "sid-4", tp4)
    d = dersler(out)
    ekle("B14b", "tarama tavani asildi -> kanitlanamaz -> basar", d == ["alfa", "bravo", "carli"], f"d={d}")
    tp4.unlink()

    # B15 yazilamaz kayit dizini
    kok5 = _tmp()
    proj5 = proje_kur(kok5)
    (proj5 / ".tmp" / "recall-shown").write_text("dizin degil", encoding="utf-8")
    tp5 = kok5 / "s5.jsonl"
    tp_ekle(tp5, [_kullanici("x")])
    r1 = hook_kos(hook, proj5, P1, "sid-5", tp5)
    r2 = hook_kos(hook, proj5, P1, "sid-5", tp5)
    ekle("B15", "kayit yazilamaz -> iki kez de basar, rc 0, traceback yok",
         r1[0] == r2[0] == 0 and dersler(r1[1]) == dersler(r2[1]) == ["alfa", "bravo", "carli"]
         and "Traceback" not in r1[2] + r2[2], f"{dersler(r1[1])} {dersler(r2[1])} err={r2[2][:160]!r}")

    # B16 budama
    kok6 = _tmp()
    proj6 = proje_kur(kok6)
    dz = proj6 / ".tmp" / "recall-shown"
    dz.mkdir(parents=True)
    eski, taze = dz / "eski-oturum.json", dz / "taze-oturum.json"
    for f, gun in ((eski, 8), (taze, 1)):
        f.write_text('{"tp":"x","tp_ofs":0,"gosterilen":[]}', encoding="utf-8")
        t = time.time() - gun * 86400
        os.utime(f, (t, t))
    hook_kos(hook, proj6, P1, "sid-6", kok6 / "s6.jsonl")
    ekle("B16", "yeni oturum dogarken 8 gunluk kayit silinir, 1 gunluk kalir",
         not eski.exists() and taze.exists() and (dz / "sid-6.json").exists(),
         f"eski={eski.exists()} taze={taze.exists()}")

    # B17 GERCEK GIRIS NOKTASI: hook_shim
    kok7 = _tmp()
    proj7 = proje_kur(kok7)
    (proj7 / "scripts").mkdir()
    shutil.copy2(SHIM, proj7 / "scripts" / "hook_shim.py")
    (proj7 / "core" / "scripts" / "hooks").mkdir(parents=True)
    shutil.copy2(hook, proj7 / "core" / "scripts" / "hooks" / "recall_inject.py")
    shutil.copy2(URETEC, proj7 / "core" / "scripts" / "build_recall_index.py")
    via = proj7 / "scripts" / "hook_shim.py"
    tp7 = kok7 / "s7.jsonl"
    rc, out, err = hook_kos(hook, proj7, P1, "sid-7", tp7, via=via)
    ekle("B17a", "hook_shim: ilk prompt basar", rc == 0 and dersler(out) == ["alfa", "bravo", "carli"],
         f"rc={rc} out={out[:120]!r} err={err[:200]!r}")
    tp_ekle(tp7, [_kullanici(P1)])
    rc, out, _ = hook_kos(hook, proj7, P1, "sid-7", tp7, via=via)
    ekle("B17b", "hook_shim: ayni pencerede bastirir", rc == 0 and dersler(out) == [], f"d={dersler(out)}")
    tp_ekle(tp7, [_sinir("auto")])
    rc, out, _ = hook_kos(hook, proj7, P1, "sid-7", tp7, via=via)
    ekle("B17c", "hook_shim: compact sonrasi yeniden basar",
         rc == 0 and dersler(out) == ["alfa", "bravo", "carli"], f"d={dersler(out)}")

    # B19 sentetik olcum: 30 prompt, 15'ten sonra compact
    kok8 = _tmp()
    proj8 = proje_kur(kok8)
    tp8 = kok8 / "s8.jsonl"
    dizi = [P1, P2, P3] * 10
    pencere: set = set()
    tekrar = 0
    eski_kar = yeni_kar = 0
    compact_sonrasi_gorulen: set = set()
    once_gorulen: set = set()
    for i, pr in enumerate(dizi):
        if i == 15:
            tp_ekle(tp8, [_sinir("auto")])
            pencere = set()
        o_yeni = hook_kos(hook, proj8, pr, "sid-8", tp8)[1]
        o_eski = hook_kos(hook, proj8, pr)[1]                # sid'siz = bugunku davranis
        yeni_kar += len(o_yeni)
        eski_kar += len(o_eski)
        dd = dersler(o_yeni) or []
        tekrar += sum(1 for x in dd if x in pencere)
        pencere |= set(dd)
        (compact_sonrasi_gorulen if i >= 15 else once_gorulen).update(dd)
        tp_ekle(tp8, [_kullanici(pr), _asistan("cevap")])
    print(f"  [OLCUM] B19: 30 prompt / 1 compact — cikti karakteri bastirmasiz {eski_kar} -> "
          f"bastirmali {yeni_kar} (%{100 * (eski_kar - yeni_kar) / max(eski_kar, 1):.0f} azalma) · "
          f"ayni pencerede tekrar eden ders satiri {tekrar}", flush=True)
    ekle("B19a", "ayni pencerede tekrar eden ders satiri = 0", tekrar == 0, f"tekrar={tekrar}")
    ekle("B19b", "compact sonrasi compact oncesi gorulen HER ders yeniden gorunur",
         bool(once_gorulen) and once_gorulen <= compact_sonrasi_gorulen,
         f"once={sorted(once_gorulen)} sonra={sorted(compact_sonrasi_gorulen)}")

    # B21 3. baglam: CRLF satir sonlu transkript
    kok9 = _tmp()
    proj9 = proje_kur(kok9)
    tp9 = kok9 / "s9.jsonl"
    hook_kos(hook, proj9, P1, "sid-9", tp9)
    tp_ekle(tp9, [_kullanici(P1), _sinir("manual")], son="\r\n")
    rc, out, _ = hook_kos(hook, proj9, P1, "sid-9", tp9)
    ekle("B21", "CRLF transkriptte compact_boundary sifirlar", dersler(out) == ["alfa", "bravo", "carli"],
         f"d={dersler(out)}")


# ─────────────────────────────────────────────────────────────────────────────
def _agac(metin: str, ad: str) -> Path:
    kok = _tmp("recalltekrar_kum_")
    (kok / "scripts" / "hooks").mkdir(parents=True)
    shutil.copy2(URETEC, kok / "scripts" / "build_recall_index.py")
    h = kok / "scripts" / "hooks" / ad
    h.write_text(metin, encoding="utf-8", newline="")
    return h


def mutant_kur(kip: str) -> Path:
    eski, yeni = CAPA[kip]
    src = HOOK.read_bytes().decode("utf-8")
    n = src.count(eski)
    if n != 1:
        print(f"[DOGRULANAMADI] mutasyon capasi bayat ({kip}): {n} eslesme (1 bekleniyordu)", flush=True)
        temizle()
        sys.exit(2)
    mutant = _agac(src.replace(eski, yeni, 1), "recall_inject.py")
    try:
        py_compile.compile(str(mutant), doraise=True)
    except py_compile.PyCompileError as e:
        print(f"[DOGRULANAMADI] mutant derlenmedi ({kip}): {e}", flush=True)
        temizle()
        sys.exit(2)
    # KONTROL GRUBU: gecici agactaki MUTASYONSUZ ikiz gercek dosyayla ayni ders listesini vermeli
    ikiz = _agac(src, "recall_inject.py")
    sonuclar = []
    for h in (HOOK, ikiz):
        kok = _tmp()
        proj = proje_kur(kok)
        tp = kok / "k.jsonl"
        a = dersler(hook_kos(h, proj, P1, "kg", tp)[1])
        tp_ekle(tp, [_kullanici(P1)])
        b = dersler(hook_kos(h, proj, P1, "kg", tp)[1])
        sonuclar.append((a, b))
    if sonuclar[0] != sonuclar[1] or sonuclar[0][0] != ["alfa", "bravo", "carli"]:
        print(f"[DOGRULANAMADI] kontrol grubu bozuk: gercek={sonuclar[0]} ikiz={sonuclar[1]}", flush=True)
        temizle()
        sys.exit(2)
    return mutant


def main() -> int:
    argv = sys.argv[1:]
    if any(a in ("-h", "--help") for a in argv):
        print(__doc__)
        return 0
    bilinmeyen = [a for a in argv if a not in CAPA]
    if bilinmeyen or len(argv) > 1:
        print(f"[KULLANIM] gecersiz arguman: {argv} — gecerli: {sorted(CAPA)}", flush=True)
        return 2
    kip = argv[0] if argv else ""
    hook = mutant_kur(kip) if kip else HOOK
    try:
        vektorler(hook)
    except Exception as e:                  # noqa: BLE001 — cokme FAIL degil, OLCUM YOK (exit 2)
        print(f"[DOGRULANAMADI] korpus COKTU ({type(e).__name__}: {e}) — sonuc yok", flush=True)
        return 2
    finally:
        temizle()

    print("=" * 78)
    print(f"RECALL TEKRAR BASTIRMA (K1) — kip: {kip or 'taban'}")
    print("=" * 78)
    dusen = set()
    for kimlik, ok, ad in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {kimlik} {ad}")
        if not ok:
            dusen.add(kimlik)
    gecen = len(SONUC) - len(dusen)
    print(f"{gecen}/{len(SONUC)} OK")
    print("KAPSAM: bakilan = basilan ders listesi (sira dahil) · kayit dosyasi varligi/gecerliligi · "
          "rc · stderr traceback. BAKILMAYAN: gercek Claude Code oturumunda compact (canli olcum "
          "N=1, changelog K1) · eszamanli AYNI-oturum hook cagrilari (harness prompt'lari sirali isler).")
    if not kip:
        return 0 if not dusen else 1
    beklenen = BEKLENEN_DUSUS[kip]
    if dusen != beklenen:
        print(f"[DOGRULANAMADI] MUTASYON {kip}: dusen kume BEKLENEN'den farkli — "
              f"eksik={sorted(beklenen - dusen)} fazla={sorted(dusen - beklenen)}", flush=True)
        return 2
    print(f"  (MUTASYON {kip}: beklenen dusus kumesi {sorted(beklenen)} AYNEN gerceklesti)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
