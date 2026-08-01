#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_fixture_tests.py — bozuk-girdi (negatif-test) korpuslarinin TEK giris noktasi.

BOLUM 1 — validator bad/good fixture ciftleri (G1/T3.6).
BOLUM 2 — pre_tool_guard PAYLOAD korpusu (2026-08-01 bug-avi AV-16/17/18/18b/21;
          detay + mutasyon-testi: tests/run_guard_fixture_tests.py).
OZEL    — kendi kosucusunu tasiyan fixture'lar (tier_fail_closed, changelog_gate)
          ayni tabloya raporlanir.
Hepsi CI'da bu tek komutla kosar (core-ci.yml "Validator fixture testleri").

Her validator icin tests/fixtures/<validator>/{bad,good}/ altinda gercekci bir mini
"proje koku" bulunur (SOURCE_CODES/... veya docs/...). Bu dizin CLAUDE_PROJECT_DIR
olarak validator subprocess'ine verilir; validator boylece kendi normal (argumansiz,
repo-geneli tarama) modunda calisir:

  - bad/  -> validator FAIL vermeli (exit != 0)
  - good/ -> validator PASS vermeli (exit == 0)

Herhangi bir cift beklenenin tersini verirse (ya da fixture eksikse) NIHAI exit 1.

OZEL_TESTLER (2026-08-01, bug-avi): bazi infra kusurlari "bad/good proje dizini" seklinde
ifade EDILEMEZ (ornegin tier cozumleme = kod-yolu; changelog gate = gercek git reposu).
Bunlar `tests/fixtures/<ad>/run.py` olarak yasar, kendi P/N senaryolarini icinde tasir ve
exit 0/1 doner. Burada ayni tabloya raporlanirlar (tek kosucu = CI'da tek adim).

Kullanim:
    python tests/run_fixture_tests.py
Cikis: 0 -- hepsi beklendigi gibi, 1 -- en az bir sapma.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
VALIDATORS_DIR = HERE.parent / "scripts" / "validators"

# G1/T3.6 ilk-10: hepsi CLAUDE_PROJECT_DIR + argumansiz repo-geneli tarama modunu
# destekler (proje_root()/source_dir() -> env). ATLANDI: check_rap_byassoc_keys_only
# (kod her zaman `return 0` -- SOFT, fixture'la FAIL uretilemez) ve check_console_utf8
# (CORE = Path(__file__).resolve().parents[2] hard-code -- kendi scripts/ agacini tarar,
# CLAUDE_PROJECT_DIR/cwd'den BAGIMSIZ -- fixture ile izole edilemez).
VALIDATORS = [
    "check_bdef_backtick",
    "check_cds_srvd_comment_syntax",
    "check_list_view_grid",
    "check_ui5_freestyle_traps",
    "check_filter_search_pattern",
    "check_decimal_write_to",
    "check_method_param_type_c",
    "check_no_rap_commit",
    "check_amdp_comment_apostrophe",
    "check_kd_no_raw_mermaid",
]

# Kendi kosucusunu tasiyan fixture'lar: tests/fixtures/<ad>/run.py (exit 0 = tum senaryolar OK).
# Her biri kendi icinde HEM bozuk->BLOK HEM temiz->SERBEST senaryolarini kosar.
OZEL_TESTLER = [
    ("tier_fail_closed", "ADR 0010 tier: fail-closed + tam-anahtar (KAYIT-1)"),
    ("changelog_gate", "pre-commit 4. kontrol: infra-changelog gate (KAYIT-2)"),
    ("sir_gate", "pre-commit 5. kontrol: sir-dosyasi (canli ihlalle bulundu)"),
    ("reviewer_tip_kapsam", "ADR 0006 pre-flight: push-tipi <-> reviewer haritasi senkronu"),
    ("conn_cift_anahtar", "ADR 0010: cift-anahtarli .conn_adt (guard <-> baglanti ayrismasi)"),
    ("adtget_yokluk_kaniti", "BULUNAMADI != YOK: adt_get DDIC dalinda hata <-> yokluk"),
    ("aktivasyon_sahte_ok", "HTTP hatasi da KANIT DEGIL: aktivasyon sahte-OK'i"),
    ("worktree_blocklist", "kimlik blocklist'i worktree'de de bulunmali (commit-blogu)"),
    ("adtget_yokluk_kaniti", "BULUNAMADI != YOK: adt_get DDIC dalinda hata <-> yokluk"),
]


def run_validator(name: str, fixture_dir: Path) -> tuple[int, str]:
    script = VALIDATORS_DIR / f"{name}.py"
    env = os.environ.copy()
    # Sizinti onleme: parent surecten IX_*/CLAUDE_PROJECT_DIR miras alinmaz.
    for k in list(env):
        if k == "CLAUDE_PROJECT_DIR" or k.startswith("IX_"):
            env.pop(k, None)
    env["CLAUDE_PROJECT_DIR"] = str(fixture_dir)
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(fixture_dir),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def run_ozel(ad: str) -> tuple[int, str]:
    """tests/fixtures/<ad>/run.py — kendi P/N senaryolarini kosan bagimsiz fixture."""
    script = FIXTURES / ad / "run.py"
    env = os.environ.copy()
    for k in list(env):
        if k == "CLAUDE_PROJECT_DIR" or k.startswith("IX_"):
            env.pop(k, None)
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(HERE.parent),          # repo koku (fixture kendi izolasyonunu kurar)
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
# =============================================================================
# BÖLÜM 2 — REGRESYON VEKTÖRLERİ (bug-avı 2026-08-01: AV-02 / AV-03 / AV-13)
#
# Bunlar validator DEĞİL, kütüphane-seviyesi davranışlardır (yaml-parser, sızıntı-deseni,
# üç-değerli sınıflama) → yukarıdaki bad/good subprocess kalıbına girmezler. Aynı TEK
# giriş noktasından koşsunlar diye buraya kablolandılar: `python tests/run_fixture_tests.py`.
# =============================================================================
REPO = HERE.parent
for _p in (REPO / "scripts", REPO / "scripts" / "utils"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def _sonuc(ad: str, ok: bool, detay: str = "") -> tuple:
    return (ad, ok, detay)


def av02_kontrolleri() -> list[tuple]:
    """BOM'lu project.yaml ilk anahtarı BOZMAMALI (AV-02).

    Kök: `read_text(encoding="utf-8")` BOM'u metnin İÇİNDE bırakır → ilk anahtar
    '\\ufeffsap_profile' olur → cfg("sap_profile") None → MCP profil katmanı fail-closed'a
    düşer ve TÜM SAP tool yüzeyi sessizce yalnız `ping`e iner.
    """
    import tempfile
    from utils import project_config as pc  # type: ignore

    fx = FIXTURES / "av02_project_config_bom"
    out = []

    beklenen = {"sap_profile": "s4_private", "release": "2025",
                "master_language": "TR", "source_root": "SOURCE_CODES"}

    for ad in ("bomsuz.yaml", "bomlu.yaml"):
        pc._yaml_lite.cache_clear()
        d = pc._yaml_lite(str(fx / ad))
        out.append(_sonuc(f"AV-02 parse {ad}", d == beklenen, f"alındı={d}"))

    # En güçlü ifade: BOM'lu ve BOM'suz AYNI sözlüğü vermeli (bayt-eş davranış).
    pc._yaml_lite.cache_clear(); a = pc._yaml_lite(str(fx / "bomsuz.yaml"))
    pc._yaml_lite.cache_clear(); b = pc._yaml_lite(str(fx / "bomlu.yaml"))
    out.append(_sonuc("AV-02 BOM'lu == BOM'suz (regresyon çapası)", a == b, f"{a} vs {b}"))

    # 3. BAĞLAM — CRLF: git `.gitattributes`'ta `*.yaml text eol=lf` olduğu için CRLF'li
    # bir fixture DOSYAYA YAZILAMAZ (commit'te LF'e normalize edilir → test sessizce
    # anlamsızlaşırdı). Bu yüzden CRLF varyantı KOŞUM ANINDA türetilir.
    tmp = Path(tempfile.mkdtemp())
    ham = (fx / "bomlu.yaml").read_bytes().replace(b"\n", b"\r\n")
    (tmp / "crlf.yaml").write_bytes(ham)
    pc._yaml_lite.cache_clear()
    d = pc._yaml_lite(str(tmp / "crlf.yaml"))
    out.append(_sonuc("AV-02 3.bağlam BOM+CRLF (Windows/PowerShell şekli)",
                      d == beklenen, f"alındı={d}"))

    # Yozlaşmış girdiler: çökmemeli, boş sözlük dönmeli.
    for ad in ("yalniz_bom.yaml", "bos.yaml"):
        pc._yaml_lite.cache_clear()
        d = pc._yaml_lite(str(fx / ad))
        out.append(_sonuc(f"AV-02 yozlaşmış {ad} → {{}} (çökme yok)", d == {}, f"alındı={d}"))

    # KABLOLAMA (kod ≠ kablolama): asıl sonuç zinciri — BOM'lu project.yaml ile MCP
    # tool yüzeyi çökmemeli. `_profile.aktif_profil()` None dönerse yalnız `ping` açılır.
    eski = os.environ.get("CLAUDE_PROJECT_DIR")
    try:
        proj = Path(tempfile.mkdtemp())
        (proj / "project.yaml").write_bytes((fx / "bomlu.yaml").read_bytes())
        os.environ["CLAUDE_PROJECT_DIR"] = str(proj)
        pc._yaml_lite.cache_clear()
        prof_okundu = pc.sap_profile()
        sys.path.insert(0, str(REPO / "mcp_servers" / "sap_adt"))
        import _profile  # type: ignore
        aktif = _profile.aktif_profil()
        acik = _profile.uygun_mu(("all",), aktif)
        out.append(_sonuc("AV-02 KABLOLAMA: BOM'lu yaml → MCP tool yüzeyi AÇIK kalır",
                          prof_okundu == "s4_private" and aktif == "s4_private" and acik,
                          f"cfg={prof_okundu!r} aktif_profil={aktif!r} tool_acik={acik}"))
    finally:
        if eski is None:
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
        else:
            os.environ["CLAUDE_PROJECT_DIR"] = eski
        pc._yaml_lite.cache_clear()

    return out


def _av03_vektorler(p: Path) -> list[tuple[int, str]]:
    """`<beklenen-sayı>\\t<metin>` satırlarını oku; {{D}}/{{d}} ikame et."""
    ciftler = []
    for ham in p.read_text(encoding="utf-8-sig").splitlines():
        if not ham.strip() or ham.lstrip().startswith("#"):
            continue
        sayi, _, metin = ham.partition("\t")
        ciftler.append((int(sayi.strip()), metin.replace("{{D}}", "D").replace("{{d}}", "d")))
    return ciftler


def av03_kontrolleri() -> list[tuple]:
    """SAP kullanıcı-adı deseni: küçük harf + rakam soneki YAKALANMALI, placeholder MUAF."""
    import genericize_common as G  # type: ignore

    fx = FIXTURES / "av03_genericize_sap_user"
    out = []
    for dosya, etiket in (("sizinti.txt", "POZİTİF"), ("temiz.txt", "NEGATİF")):
        sapan = []
        for beklenen, metin in _av03_vektorler(fx / dosya):
            bulunan = G.sap_user_sizintilari(metin)
            if len(bulunan) != beklenen:
                sapan.append(f"{metin!r}: beklenen={beklenen} bulunan={bulunan}")
        out.append(_sonuc(f"AV-03 {etiket} vektörler ({dosya})", not sapan,
                          "; ".join(sapan[:4])))

    # ⚠ Bu dosyadaki örnek token'lar da PARÇALI kurulur — bu dosya da taranıyor
    # (ilk taslakta buraya literal yazmıştım; gerçek commit onu ihlal saydı).
    d, U = chr(100), chr(68)
    # KABLOLAMA: desen tek başına değil, gate'in çağırdığı `sizintilari_bul` üzerinden
    # de görünmeli (guard'lar bu fonksiyonu kullanır — kod ≠ kablolama).
    idp = G.id_pattern()
    bulgular = G.sizintilari_bul("kullanici " + d + "_sampleuser sisteme baglandi", idp)
    turler = {tur for _, tur in bulgular}
    out.append(_sonuc("AV-03 KABLOLAMA: sizintilari_bul bağlamlı küçük-harf kimliği raporlar",
                      "SAP kullanıcı adı" in turler, f"bulgular={bulgular}"))

    # ŞİDDET/BAĞLAM AYRIMI — FP'yi 4'ten 0'a indiren tasarım kararının birebir çapası:
    # aynı küçük-harf token bağlamsız satırda SESSİZ, kimlik satırında YAKALANIR.
    baglamsiz = "toplam = " + d + "_total + " + d + "_rows"
    baglamli = "ADT_SAP_USER=" + d + "_svcuser01"
    out.append(_sonuc("AV-03 bağlam ayrımı: bağlamsız SESSİZ / bağlamlı YAKALANIR",
                      G.sap_user_sizintilari(baglamsiz) == []
                      and len(G.sap_user_sizintilari(baglamli)) == 1,
                      f"bağlamsız={G.sap_user_sizintilari(baglamsiz)} "
                      f"bağlamlı={G.sap_user_sizintilari(baglamli)}"))

    # 3. BAĞLAM — placeholder muafiyetinin GERÇEK kaynağı: şablon projesi metni.
    # (2026-07-10 vakası: kendi README şablonumuz FP'ye takılmıştı; muafiyet o yüzden var.)
    sablon = ("ADT_SAP_USER=" + U + "_XXXXXXX\n# ornek: " + U + "_NNNNNN\n"
              "kucuk yazim (user satiri): " + d + "_xxxx\n")
    out.append(_sonuc("AV-03 3.bağlam: şablon placeholder'ları hâlâ MUAF (FP yok)",
                      G.sap_user_sizintilari(sablon) == [],
                      f"bulunan={G.sap_user_sizintilari(sablon)}"))
    return out


def av13_kontrolleri() -> list[tuple]:
    """Üç-değerli sınıflama: okunamayan sürüm ASLA PHANTOM/STALE'e katlanmamalı."""
    import json as _json

    import worklist_audit as W  # type: ignore

    fx = FIXTURES / "av13_worklist_classify" / "siniflama.json"
    veri = _json.loads(fx.read_text(encoding="utf-8-sig"))
    out = []

    # --- sınıflama matrisi (9 vektör) ---
    orijinal_ve, orijinal_op = W._version_exists, W._object_package
    sapan = []
    try:
        W._object_package = lambda *a, **k: None
        for c in veri["siniflama"]:
            sirali = iter([c["has_active"], c["has_inactive"]])
            W._version_exists = lambda adt, uri, ver, _s=sirali: next(_s)
            r = W._classify(None, None, {"uri": "/x", "name": "N", "type": "CLAS/OC"})
            if r["class"] != c["beklenen"]:
                sapan.append(f"({c['has_active']},{c['has_inactive']}) "
                             f"beklenen={c['beklenen']} alınan={r['class']}")
    finally:
        W._version_exists, W._object_package = orijinal_ve, orijinal_op
    out.append(_sonuc("AV-13 sınıflama matrisi (9 vektör)", not sapan, "; ".join(sapan)))

    # --- 3. BAĞLAM: bir alt katman — HTTP durum kodu → üç değer eşlemesi ---
    class _SahteCevap:
        def __init__(self, kod): self.status_code = kod

    class _SahteOturum:
        def __init__(self, kod): self.kod = kod
        def get(self, *a, **k):
            if self.kod == "EXCEPTION":
                raise OSError("ağ koptu")
            return _SahteCevap(self.kod)

    class _SahteAdt:
        def __init__(self, kod): self.session, self.url = _SahteOturum(kod), "http://x"

    sapan = []
    for c in veri["durum_kodlari"]:
        alinan = orijinal_ve(_SahteAdt(c["status"]), "/uri", "active")
        if alinan is not c["beklenen"]:
            sapan.append(f"status={c['status']} beklenen={c['beklenen']} alınan={alinan}")
    out.append(_sonuc("AV-13 3.bağlam: HTTP durum → üç-değer eşlemesi (9 kod)",
                      not sapan, "; ".join(sapan)))

    # --- çıkış-kodu sözleşmesi: bilinmeyen varken "commit güvenli" (0) DENMEZ ---
    sapan = []
    for real, unknown, beklenen in (([], [], 0), ([], ["u"], 2), (["r"], [], 1), (["r"], ["u"], 1)):
        alinan = W._exit_kodu(real, unknown)
        if alinan != beklenen:
            sapan.append(f"real={bool(real)} unknown={bool(unknown)} "
                         f"beklenen={beklenen} alınan={alinan}")
    out.append(_sonuc("AV-13 çıkış-kodu sözleşmesi (0/1/2)", not sapan, "; ".join(sapan)))
    return out


REGRESYON = [
    ("AV-02 project_config BOM", av02_kontrolleri),
    ("AV-03 genericize SAP kullanıcı deseni", av03_kontrolleri),
    ("AV-13 worklist üç-değerli sınıflama", av13_kontrolleri),
]


def regresyon_kos() -> tuple[int, int]:
    """(gecen, toplam) — ayrıntıyı basar."""
    gecen = toplam = 0
    print("\n=== REGRESYON VEKTÖRLERİ (bug-avı 2026-08-01) ===")
    # ⚠ ZORUNLU FLUSH — `worklist_audit` import-ANINDA sys.stdout'u YENİ bir
    # TextIOWrapper ile değiştiriyor (worklist_audit.py:36-40, win32 dalı). Eski
    # wrapper'daki henüz boşaltılmamış çıktı bu sırada KAYBOLUYOR: ilk koşumda bu
    # dosyanın 24 satırlık raporu 6 satıra düşmüş, buna rağmen "24/24 PASS" yazmıştı
    # (sessiz çıktı kaybı — "PASS ≠ baktı"). Import'lardan ÖNCE boşalt.
    sys.stdout.flush()
    sys.stderr.flush()
    for baslik, fn in REGRESYON:
        try:
            sonuclar = fn()
        except Exception as exc:  # noqa: BLE001
            print(f"  [DOĞRULANAMADI] {baslik}: {type(exc).__name__}: {exc}")
            toplam += 1
            continue
        for ad, ok, detay in sonuclar:
            toplam += 1
            gecen += 1 if ok else 0
            print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
            if not ok:
                print(f"         -> {detay}")
        # Her blok sonunda boşalt: SONRAKİ bileşenin import'u stdout'u değiştirebilir
        # ve bu bloğun çıktısını yutabilir (yukarıdaki worklist_audit notu).
        sys.stdout.flush()
    return gecen, toplam


def main() -> int:
    rows = []  # (name, bad_desc, good_desc, verdict, detail)
    all_ok = True

    for name in VALIDATORS:
        script = VALIDATORS_DIR / f"{name}.py"
        bad_dir = FIXTURES / name / "bad"
        good_dir = FIXTURES / name / "good"

        if not script.is_file():
            rows.append((name, "n/a", "n/a", "DOĞRULANAMADI", f"validator bulunamadı: {script}"))
            all_ok = False
            continue
        if not bad_dir.is_dir() or not good_dir.is_dir():
            rows.append((name, "n/a", "n/a", "DOĞRULANAMADI", "fixture bad/good dizini eksik"))
            all_ok = False
            continue

        try:
            bad_rc, bad_out = run_validator(name, bad_dir)
            good_rc, good_out = run_validator(name, good_dir)
        except Exception as exc:  # pragma: no cover -- gercek calisma-zamani hatasi
            rows.append((name, "n/a", "n/a", "DOĞRULANAMADI", f"çalıştırma hatası: {exc}"))
            all_ok = False
            continue

        bad_ok = bad_rc != 0
        good_ok = good_rc == 0
        ok = bad_ok and good_ok
        all_ok = all_ok and ok

        detail = ""
        if not bad_ok:
            detail += f" | bad BEKLENMEDİK exit={bad_rc} çıktı: {bad_out.strip()[:200]}"
        if not good_ok:
            detail += f" | good BEKLENMEDİK exit={good_rc} çıktı: {good_out.strip()[:200]}"

        rows.append((
            name,
            f"exit={bad_rc} ({'OK' if bad_ok else 'TERS'})",
            f"exit={good_rc} ({'OK' if good_ok else 'TERS'})",
            "PASS" if ok else "FAIL",
            detail,
        ))

    for ad, aciklama in OZEL_TESTLER:
        script = FIXTURES / ad / "run.py"
        if not script.is_file():
            rows.append((ad, "n/a", "n/a", "DOĞRULANAMADI", f"özel fixture yok: {script}"))
            all_ok = False
            continue
        try:
            rc, out = run_ozel(ad)
        except Exception as exc:  # pragma: no cover
            rows.append((ad, "n/a", "n/a", "DOĞRULANAMADI", f"çalıştırma hatası: {exc}"))
            all_ok = False
            continue
        ok = rc == 0
        all_ok = all_ok and ok
        # Ozel fixture P ve N senaryolarini KENDI icinde tasir → tek exit kodu raporlanir.
        ozet = [s for s in out.splitlines() if re.match(r"^\s*\d+/\d+ OK", s)][-1:] or [""]
        rows.append((
            ad,
            f"P+N içeride ({aciklama[:18]}…)",
            f"exit={rc} ({'OK' if ok else 'SAPMA'})",
            "PASS" if ok else "FAIL",
            "" if ok else f" | {out.strip()[-400:]}",
        ))
        if ok:
            rows[-1] = (rows[-1][0], f"P+N içeride: {ozet[0].strip()}", rows[-1][2],
                        rows[-1][3], rows[-1][4])

    name_w = max(len(r[0]) for r in rows) + 2
    print(f"{'validator':<{name_w}} {'bad (fail beklenir)':<26} {'good (pass beklenir)':<26} sonuç")
    print("-" * (name_w + 26 + 26 + 8))
    for name, bad_s, good_s, verdict, detail in rows:
        print(f"{name:<{name_w}} {bad_s:<26} {good_s:<26} {verdict}")
        if detail:
            print(f"    -> {detail.strip(' |')}")

    n_pass = sum(1 for r in rows if r[3] == "PASS")
    print(f"\n{n_pass}/{len(rows)} PASS  (bölüm 1: validator bad/good)")

    # ── BÖLÜM 2: regresyon vektörleri (AV-02/03/13 — kütüphane seviyesi) ──
    r_gecen, r_toplam = regresyon_kos()
    print(f"\nregresyon vektörleri: {r_gecen}/{r_toplam} PASS  (bölüm 2)")

    # ── BÖLÜM 3: pre_tool_guard payload korpusu (AV-16/17/18/18b/21) ──
    # Ayrı dosyada yaşar (kendi mutasyon-modu var) ama TEK komutla koşsun diye buradan
    # çağrılır: CI adımı zaten bu dosyayı işaret ediyor; ikinci bir CI adımı eklemek
    # "kablolamayı unutma" riskini artırırdı (kod ≠ kablolama dersi — bu turda
    # test_commit_message_leak_gate tam olarak böyle 3 gün kablosuz kalmıştı).
    sys.path.insert(0, str(HERE))
    try:
        from run_guard_fixture_tests import kosum as guard_kosum
    except Exception as exc:
        print(f"\n[DOĞRULANAMADI] guard payload korpusu yüklenemedi: {exc}")
        return 1
    print("\n" + "-" * 60)
    print("pre_tool_guard payload korpusu (blok + serbest)")
    g_gecen, g_toplam, g_hatalar = guard_kosum(sessiz=True)
    for h in g_hatalar:
        print(f"  [FAIL] {h}")
    print(f"{g_gecen}/{g_toplam} PASS  (bölüm 3: guard payload)")

    print(f"\nTOPLAM: {n_pass + r_gecen + g_gecen}/{len(rows) + r_toplam + g_toplam} PASS")
    return 0 if (all_ok and r_gecen == r_toplam and not g_hatalar) else 1


if __name__ == "__main__":
    sys.exit(main())
