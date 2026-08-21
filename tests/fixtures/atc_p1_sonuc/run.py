#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FIXTURE — `post_tool_failure` hook'unun **ATC Priority-1 SONUÇ ekseni** (2026-08-21).

NİÇİN VAR (ölçülmüş vaka 2026-08-21): bir bug-gate turu `adt_atc_check`'in döndürdüğü
ATC **Priority-1** bulgusunu **LOW** derecelendirdi ve ilerleme sürdü. Ev politikası
(`playbook/checklists/rap-troubleshoot.md` §3 · `bug-checklist-backend.md` BE-12) ise
*"Priority 1 ZORUNLU düzeltilir, susturma YASAK"* diyor. Kural YAZILIYDI; kimse dayatmıyordu.
Brifing METNİNİ denetleyen alternatifler 605 gerçek brif üzerinde ölçülüp ELENDİ (metin-izi
bu sınıfta ölü) ⇒ tetik **YAPISAL alandır**: `priority_1_count > 0` / `must_fix: true`.

DÖRT DEĞİŞMEZ (her biri AYRI mutasyonla ölçülür — hiçbiri diğerini kapsamaz):
  ① ATEŞLEME-SAYI  — `priority_1_count > 0` → not ÜRETİLİR.
  ② ATEŞLEME-BAYRAK— sayı alanı yokken `must_fix: true` → not ÜRETİLİR (eşdeğer alan).
  ③ SESSİZLİK      — `priority_1_count == 0` dâhil diğer HER durumda çıktı YOK.
  ④ UTF-8 STDIN    — taşınan `policy` METNİ bozulmadan ulaşır (aşağıya bak).
③ birincisi kadar önemlidir: her başarılı ATC koşumunda konuşan bir hook = gürültü = uyarı
körlüğü = hook'un ölümü. Bu yüzden FP çapaları (N1-N6) DÖRT mutasyonda da AYAKTA kalmalı.

⛔ POLİTİKA ÇAPASI (C1/C2): hook politikayı ÜRETMEZ, aracın `policy` alanını TAŞIR. `policy`
yoksa uydurmaz. Bu, "ATC politikasını CORE'a gömme" sınırının test edilebilir hâlidir.

⚠ ④ NİÇİN VAR (ölçüldü 2026-08-21): bu hook stdin'den gelen METNİ geri basan İLK tüketicidir.
Doğrudan çağrıda Windows `sys.stdin` cp1252'ye düşer ve `policy` mojibake olur
("düzeltilir"→"dÃ¼zeltilir"). Canlı yolda `hook_shim` stdin'i UTF-8'e çeviriyor — AMA bunu
`sys.stderr.encoding != "utf-8"` KOŞULUNA bağlar ⇒ garanti değil. Hook artık ham byte okuyup
UTF-8 decode ediyor (`intake_triage` + `skill_injector` ile AYNI kardeş desen).

Koşum:  python tests/fixtures/atc_p1_sonuc/run.py
Mutasyon (DÖRDÜ DE koşulur):
  --mutasyon-sayi     `priority_1_count` dalını söker           → P2/P5/C2/C5 DÜŞMELİ
                      (P1/P6 AYAKTA kalır: `must_fix` de taşıyorlar — bu yüzden ② ayrı
                       mutasyon ister; tek mutasyon iki ateşleme yolunu kapsamaz)
  --mutasyon-bayrak   `must_fix` eşdeğerini söker               → P3/P4 DÜŞMELİ
  --mutasyon-esik     `p1 > 0` → `p1 >= 0` (GEVŞETME yönü)      → N1/N2/N3 DÜŞMELİ
  --mutasyon-stdin    ham-byte okumayı söker (`json.load`)      → C1 DÜŞMELİ
Herhangi biri tam puan verirse korpus O DEĞİŞMEZ için BOŞTUR.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    for _akis in (sys.stdout, sys.stderr):
        try:
            _akis.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

KOK = Path(__file__).resolve().parents[3]
HOOK = KOK / "scripts" / "hooks" / "post_tool_failure.py"

# Aracın GERÇEK `policy` metni (mcp_servers/sap_adt/tools/query.py, adt_atc_check dönüşü).
POLICY = ("Priority 1 ZORUNLU düzeltilir; Priority 2/3 yalnızca kullanıcının "
          "açık onayıyla pass geçilebilir (proje kuralı).")


def _kos(hook_yolu: Path, payload) -> tuple:
    """Hook'u GERÇEK giriş noktasından (stdin JSON) çağır."""
    ham = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    p = subprocess.run([sys.executable, str(hook_yolu)], input=ham,
                       capture_output=True, text=True, encoding="utf-8")
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def _baglam(out: str) -> str:
    """stdout'tan GERÇEK `additionalContext`i çöz.

    ⚠ Ham stdout'ta içerik ARANMAZ: hook `json.dumps(...)` varsayılanıyla (ensure_ascii=True)
    basar ⇒ 'SONUÇ' tel üzerinde 'SONU\\u00c7' olur. Ham dizgede substring arayan bir çapa
    Türkçe her ifadede SAHTE-KIRMIZI verir (bu korpusun ilk koşumunda birebir yaşandı:
    6 ateşleme vektörü 'atc_notu=YOK' dedi, oysa not ÜRETİLMİŞTİ).
    """
    if not out:
        return ""
    try:
        return json.loads(out)["hookSpecificOutput"]["additionalContext"]
    except Exception:
        return ""


def _atc(resp: dict, arac: str = "mcp__sap-adt__adt_atc_check") -> dict:
    return {"tool_name": arac, "tool_input": {"name": resp.get("name", "ZCL_X")},
            "tool_response": resp}


def _temiz_atc(**ek) -> dict:
    """`ok:true` ATC yanıtının TEMİZ hâli — vektörler yalnız farkı yazar."""
    d = {"ok": True, "name": "ZCL_SD022_PROCESSOR", "type": "class",
         "variant": "ZZNDBS_ATC", "finding_count": 0, "priority_1_count": 0,
         "other_priority_count": 0, "must_fix": False, "policy": POLICY, "findings": []}
    d.update(ek)
    return d


# (ad, payload, KONUŞMALI mı)
VEKTORLER = [
    # ── ① ATEŞLEME-SAYI çapaları ───────────────────────────────────────────
    ("P1 gerçek vaka: priority_1_count=2 + must_fix=true (ZCL_SD022_PROCESSOR)",
     _atc(_temiz_atc(finding_count=50, priority_1_count=2, other_priority_count=48,
                     must_fix=True)), True),
    ("P2 priority_1_count=1, must_fix alanı HİÇ YOK (sayı tek başına yeter)",
     _atc({"ok": True, "name": "ZCL_Y", "priority_1_count": 1, "policy": POLICY}), True),

    # ── ② ATEŞLEME-BAYRAK çapaları (sayı alanı YOK) ────────────────────────
    ("P3 must_fix=True (bool), priority_1_count alanı YOK — eşdeğer alan",
     _atc({"ok": True, "name": "ZCL_Z", "must_fix": True, "policy": POLICY}), True),
    ("P4 must_fix='true' (dizge şekli), sayı alanı YOK",
     _atc({"ok": True, "name": "ZCL_W", "must_fix": "true", "policy": POLICY}), True),

    # ── ŞEKİL TOLERANSI (sayı ekseninde) ───────────────────────────────────
    ("P5 priority_1_count='3' (dizge sayı)",
     _atc(_temiz_atc(priority_1_count="3", must_fix=False)), True),
    ("P6 tool_response JSON DİZGE olarak gelmiş (mevcut parse yolu yeniden kullanılır)",
     {"tool_name": "mcp__sap-adt__adt_atc_check", "tool_input": {"name": "ZCL_V"},
      "tool_response": json.dumps(_temiz_atc(priority_1_count=4, must_fix=True),
                                  ensure_ascii=False)}, True),

    # ── ③ SESSİZLİK (FP) çapaları — ÜÇ mutasyonda da AYAKTA kalmalı ────────
    ("N1 TEMİZ ATC: priority_1_count=0, must_fix=false (POZİTİF KONTROL — DoD ③)",
     _atc(_temiz_atc()), False),
    ("N2 Prio 2/3 DOLU ama P1=0 — kapsam dışı, konuşturmaz",
     _atc(_temiz_atc(finding_count=31, other_priority_count=31)), False),
    # ⚠ N3, "yapısal alan mı prose mu" ayrımını çivilir: findings[] içinde priority='1'
    #   var ama yapısal sayaç 0. Metin/liste taransaydı burada KONUŞURDU.
    ("N3 findings[] içinde priority='1' VAR ama priority_1_count=0 (prose/liste TARANMAZ)",
     _atc(_temiz_atc(finding_count=1,
                     findings=[{"priority": "1", "message": "Nested Reading DB OP"}])), False),
    ("N4 priority_1_count ayrıştırılamıyor ('bilinmiyor') — KARAR DEĞİL, sessiz",
     _atc({"ok": True, "name": "ZCL_Q", "priority_1_count": "bilinmiyor"}), False),
    ("N5 must_fix='X' (rastgele truthy dizge) — açık 'true' değil, sessiz",
     _atc({"ok": True, "name": "ZCL_R", "must_fix": "X"}), False),
    # ⚠ N6, Bash yüzeyinin BİLİNÇLİ kapsam-dışılığını çivilir: `scripts/run_atc_check.py`
    #   yapısal alan basmaz (yalnız '  ERROR: 2' prose'u) ⇒ metin taramasına dönmemek için
    #   kapsam dışı bırakıldı. Bu vektör düşerse biri prose'a kaymış demektir.
    ("N6 Bash ATC CLI çıktısı (prose 'ERROR: 2') — bilinçli kapsam dışı, sessiz",
     {"tool_name": "Bash",
      "tool_input": {"command": "python core/scripts/run_atc_check.py --object-name ZCL_X"},
      "tool_response": {"stdout": "[OK] ATC check completed\n  ERROR: 2\n  WARNING: 5",
                        "stderr": ""}}, False),

    # ── REGRESYON: mevcut iki dal bozulmadı ────────────────────────────────
    ("R1 MCP fail (ok:false) → patinaj merdiveni HÂLÂ konuşur",
     {"tool_name": "mcp__sap-adt__adt_push_source", "tool_input": {"name": "ZCL_X"},
      "tool_response": {"ok": False, "error": "sap_error"}}, True),
    ("R2 MCP başarılı adt_get → sessiz",
     {"tool_name": "mcp__sap-adt__adt_get", "tool_input": {"name": "ZCL_X"},
      "tool_response": {"ok": True, "exists": True}}, False),
    ("R3 Bash yazma-aracı + hata imzası → Bash dalı HÂLÂ konuşur",
     {"tool_name": "Bash", "tool_input": {"command": "python push_object.py --name ZCL_X"},
      "tool_response": {"stdout": "[ERROR] [423] Failed to set source", "stderr": ""}}, True),
]


def _kontroller(hook_yolu: Path) -> list:
    """İçerik/sözleşme çapaları — 'konuştu' yetmez, NE dediği ölçülür."""
    c = []

    # C1 — hook politikayı ÜRETMEZ, aracın `policy` alanını AYNEN TAŞIR
    _, ham, _ = _kos(hook_yolu, VEKTORLER[0][1])
    out = _baglam(ham)
    c.append(("C1 aracın `policy` metni çıktıda AYNEN var (hook politika ÜRETMİYOR)",
              POLICY in out, f"baglam_uzunluk={len(out)}"))

    # C2 — `policy` alanı YOKSA uydurulmaz, yokluğu bildirilir
    _, ham2, _ = _kos(hook_yolu, _atc({"ok": True, "name": "ZCL_P", "priority_1_count": 1}))
    out2 = _baglam(ham2)
    c.append(("C2 `policy` YOKken uydurmuyor ('UYDURMA' + doğrulama yolu veriyor)",
              "UYDURMA" in out2 and "rap-troubleshoot.md" in out2,
              f"baglam_uzunluk={len(out2)}"))

    # C3 — obje kimliği çıktıda (eyleme geçirilebilirlik)
    c.append(("C3 obje adı + variant çıktıda (hangi obje olduğu belli)",
              "ZCL_SD022_PROCESSOR" in out and "ZZNDBS_ATC" in out,
              f"ad={'VAR' if 'ZCL_SD022_PROCESSOR' in out else 'YOK'}"))

    # C4 — enjekte edilen doküman yolları `core/` önekli (C-HOOK-01 sınıfı: öneksiz yol
    #      proje kökünden ÇÖZÜLMEZ ve "o dosya yok" gibi okunur)
    yollar = re.findall(r"[\w/\-.]+\.md", out)
    oneksiz = [y for y in yollar if y.startswith("playbook/") or y.startswith("standards/")]
    c.append(("C4 enjekte edilen .md yolları `core/` önekli (C-HOOK-01 sınıfı)",
              bool(yollar) and not oneksiz, f"yollar={yollar} oneksiz={oneksiz}"))

    # C5 — ATC notu FAIL dalıyla BİRLİKTE de çıkar (ok:false + P1 aynı yanıtta)
    _, ham5, _ = _kos(hook_yolu, _atc({"ok": False, "error": "sap_error", "name": "ZCL_K",
                                       "priority_1_count": 2, "policy": POLICY}))
    out5 = _baglam(ham5)
    merdiven = "PATİNAJ" in out5
    atc5 = "ATC SONUÇ KAPISI" in out5
    c.append(("C5 fail + P1 aynı yanıtta → HEM merdiven HEM ATC notu",
              merdiven and atc5,
              f"merdiven={'VAR' if merdiven else 'YOK'} atc={'VAR' if atc5 else 'YOK'}"))

    # C6 — bozuk girdi sözleşmesi (B0b): exit 0 fail-safe + stderr NOTU, stdout SESSİZ
    rc, out6, err6 = _kos(hook_yolu, "{bozuk-json")
    c.append(("C6 bozuk JSON → exit 0 + stderr NOTU (fail-safe korundu)",
              rc == 0 and "GIRDI-PARSE-EDILEMEDI" in err6 and not out6,
              f"exit={rc} not={'VAR' if 'GIRDI-PARSE-EDILEMEDI' in err6 else 'YOK'}"))

    # C7 — çıktı GEÇERLİ hook sözleşmesi (PostToolUse/additionalContext) mi
    try:
        d = json.loads(ham)
        sema = d["hookSpecificOutput"]["hookEventName"] == "PostToolUse" and \
            bool(d["hookSpecificOutput"]["additionalContext"])
    except Exception:
        sema = False
    c.append(("C7 çıktı geçerli PostToolUse/additionalContext şeması", sema, f"sema={sema}"))
    return c


# (kip, desen, yerine) — mutasyon BUGÜNKÜ kaynaktan üretilir (git ref'inden DEĞİL:
# "fix merge olunca taban kayar" tuzağı yok; hedef geçmiş bir commit değil, REDDEDİLEN
# tasarım kararıdır).
_MUTASYONLAR = {
    "sayi":   (r"if not \(\(p1 is not None and p1 > 0\) or _must_fix_mi\(resp\.get\(\"must_fix\"\)\)\):",
               'if not _must_fix_mi(resp.get("must_fix")):'),
    "bayrak": (r"if not \(\(p1 is not None and p1 > 0\) or _must_fix_mi\(resp\.get\(\"must_fix\"\)\)\):",
               "if not (p1 is not None and p1 > 0):"),
    "esik":   (r"\(p1 is not None and p1 > 0\)", "(p1 is not None and p1 >= 0)"),
    # ④ Dördüncü değişmez: UTF-8 stdin. Eski satıra geri dönüş = ATEŞLEME ayakta kalır ama
    #    taşınan `policy` METNİ mojibake olur ⇒ yalnız C1 düşer. Diğer üç mutasyonun
    #    HİÇBİRİ bunu sınamaz (onlar tetiği, bu taşımayı çivilliyor).
    "stdin":  (r"json\.loads\(sys\.stdin\.buffer\.read\(\)\.decode\(\"utf-8\", errors=\"replace\"\)\)",
               "json.load(sys.stdin)"),
}


def _mutant(kip: str) -> Path:
    """Mutantı hook'un KENDİ dizinine yaz — komşu-modül importu kırılmasın (B0 dersi)."""
    if kip not in _MUTASYONLAR:
        raise SystemExit(f"bilinmeyen mutasyon: {kip}")
    desen, yerine = _MUTASYONLAR[kip]
    yeni, n = re.subn(desen, yerine, HOOK.read_text(encoding="utf-8"), count=1)
    if n != 1:
        raise SystemExit(f"[KOSUCU DURDU] mutasyon capasi bulunamadi (kip={kip}) — "
                         "kaynak degismis olabilir; SAYI RAPORLAMIYORUM.")
    hedef = HOOK.parent / "_mutant_atc_p1.py"
    hedef.write_text(yeni, encoding="utf-8")
    return hedef


def main() -> int:
    kip = None
    for a in sys.argv[1:]:
        if a.startswith("--mutasyon-"):
            kip = a.replace("--mutasyon-", "")

    hook_yolu = HOOK
    try:
        if kip:
            hook_yolu = _mutant(kip)
            print(f"  (MUTASYON: {kip} — ayirt edici vektorler DUSMELI)\n")

        sonuc = []
        for ad, payload, konusmali in VEKTORLER:
            rc, ham, _ = _kos(hook_yolu, payload)
            out = _baglam(ham)
            atc_var = "ATC SONUÇ KAPISI" in out
            # ATC vektörlerinde "konuştu" yetmez: notun ATC NOTU olduğu da ölçülür
            # (aksi hâlde R1'in merdiveni her ateşlemeyi sahte-YEŞİL yapardı).
            if ad.startswith(("P", "N")):
                ok = (rc == 0) and (atc_var == konusmali)
                detay = f"exit={rc} atc_notu={'VAR' if atc_var else 'YOK'} beklenen={'VAR' if konusmali else 'YOK'}"
            else:
                ok = (rc == 0) and (bool(ham) == konusmali)
                detay = f"exit={rc} cikti={'VAR' if ham else 'YOK'} beklenen={'VAR' if konusmali else 'YOK'}"
            sonuc.append((ad, ok, detay))

        sonuc.extend(_kontroller(hook_yolu))

        gecen = sum(1 for _, ok, _ in sonuc if ok)
        for ad, ok, detay in sonuc:
            print(f"  [{'OK' if ok else 'FAIL'}] {ad} -> {detay}")
        print(f"\n{gecen}/{len(sonuc)} OK")
        return 0 if gecen == len(sonuc) else 1
    finally:
        if kip:
            try:
                (HOOK.parent / "_mutant_atc_p1.py").unlink()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
