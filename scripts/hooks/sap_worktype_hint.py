#!/usr/bin/env python3
# ENFORCES: ADR-0006  (ADR 0019 coverage binding)
"""PreToolUse (SAP-yazma MCP tool'ları) — DETERMİNİSTİK worktype-checklist hatırlatması.

NEDEN (2026-07-10 skill-injection redizaynı): eski `skill_injector` "bu SAP işi mi + hangi
checklist" tespitini prompt-KEYWORD regex'iyle yapıyordu → kırılgan ("CDS view yarat"
kaçtı, İngilizce "public transport" yanlış-tetikledi). Referans ekosistemin tamamı keşfi
`description`-semantik native mekanizmayla yapıyor; keyword-hook azınlık ve en kırılgan.

REDİZAYN:
  (A) KEŞİF ("bu SAP işi mi + hangi skill") → native `sap-abap-dev` skill `description`'ı
      (943 char, zaten devrede). skill_injector'dan SAP-tespiti KALDIRILDI.
  (B) ENFORCEMENT ("worktype checklist yazımdan önce oku") → BU HOOK. Prompt'tan niyet
      tahmin ETMEZ; GERÇEK SAP-yazma anında, GERÇEK obje-tipinden (tool argümanı) checklist'i
      adıyla söyler. "CDS view yarat"ın nasıl yazıldığı önemsizleşir — deterministik.

Non-blocking (exit 0 + additionalContext). Gerçek gate ADR 0006 run_review'dur; bu, doğru
checklist'i doğru anda hatırlatan fail-closed sigortadır. Session+worktype başına BİR kez
(gürültü olmasın) — pre-flight semantiği.
"""
import json
import os
import re
import sys
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass


# Tool → (worktype-grup, obje-tipi belirsizse). Dedicated create tool'ları tipi ima eder.
_TOOL_TIPI = {
    "mcp__sap-adt__adt_dtel_create": "dtel",
    "mcp__sap-adt__adt_domain_create": "doma",
    "mcp__sap-adt__adt_struct_create": "struct",
    "mcp__sap-adt__adt_publish_service": "srvb",
}
# push_source / activate: obje-tipi tool_input.object_type'tan gelir.
_TIP_TOOLLARI = {"mcp__sap-adt__adt_push_source", "mcp__sap-adt__adt_activate"}

# obje-tipi (küçük harf, ilk 4+) → (worktype-grup, checklist satırı). Grup = dedup anahtarı.
def _checklist(otype: str):
    t = (otype or "").lower().strip()
    if t.startswith("ddls") or "cds" in t or t.startswith("view"):
        return ("cds", "CDS view → OKU: playbook/checklists/cds-creation.md "
                       "(+ playbook/adt-cds.md 'TEK CDS YARATMA') · standards/05")
    if t.startswith(("bdef", "srvd", "srvb", "beh")) or "behavior" in t or "service" in t:
        return ("rap", "RAP (BDEF/behavior/SRVD/SRVB) → OKU: "
                       "playbook/checklists/rap-creation.md · standards/05 · adt-rap §32/§35")
    if t.startswith(("doma", "dtel")):
        return ("ddic-dd", "DDIC domain/DTEL → OKU: playbook/checklists/domain-dtel-creation.md "
                           "· standards/01 §5B (reuse-gate, TR-4-label)")
    if t.startswith("struct") or t.startswith("tabl") or t == "stru":
        return ("ddic-st", "DDIC struct/tablo → OKU: playbook/checklists/struct-creation.md "
                           "/ table-update.md · standards/01 §5B (+ check_td_cancelled_fields)")
    if t.startswith("prog") or "report" in t or "dynpro" in t:
        return ("classic", "Klasik dialog/report → OKU: playbook/checklists/classic-dialog-creation.md "
                           "· standards/06 (§1 include-böl ZORUNLU)")
    return (None, "")


# ── ALT-TÜR ekseni (2026-08-22, kuyruk Q5) ───────────────────────────────────
# ⛔ ÖLÇÜLMÜŞ VAKA: 11 soyut varlık (`define abstract entity`) `object_type='ddls'` ile
# push edildi. Bu hook `ddls` görüp KANONİK CDS satırını bastı: "playbook/adt-cds.md
# 'TEK CDS YARATMA'". Oysa `adt-cds.md:180` (§ ⚡ ABSTRACT ENTITY) tam da o bölümün
# önerdiği araçların (`create_cds_view.py` · `populate_cds_views.py`) abstract entity'de
# ÇALIŞMADIĞINI yazar ve şu kuralı koyar: *"yeni DDLS görünce TÜRÜNE bak — SELECT var mı?
# ... Tahminle araç seçme."* Yani hatırlatıcı, reçetenin kendi kuralını uygulamıyordu:
# obje-tipinde duruyor, ALT-TÜRE bakmıyordu. (`checklists/cds-creation.md` içinde
# "abstract" kelimesi HİÇ geçmiyor — ölçüldü.)
#
# ⛔ NEDEN BRİFİNG-METNİ DEĞİL KAYNAK: alt-tür brifingden TAHMİN edilmez; artefaktın KENDİ
# bildirimi (`define [root] abstract entity ...`) onu SÖYLER ve o bildirim bu tool'un
# payload'ında zaten vardır (`tool_input.source` / `file_path`). Aynı evde brifing-metni
# tahmini iki kez ölçülüp çürütüldü (eski `skill_injector` 12-regex'i; 2026-08-21 D2).
#
# ⛔ SÖZLÜK YOK (kuyruk kaydının tasarım kısıtı): alt-tür → bölüm eşlemesi ELLE
# tutulmaz. Eşleşme, `_checklist()`in ZATEN andığı reçete dosyalarının KENDİ BAŞLIK
# satırlarından türetilir. Yeni bir alt-tür bölümü yazıldığı gün kendiliğinden kapsama
# girer; bölüm silinirse eşleşme kendiliğinden düşer (bayatlayacak ikinci liste yok).
#
# ⛔ BELİRSİZSE SUSAR: aynı ifadeyi taşıyan BİRDEN ÇOK başlık varsa hiçbir şey söylenmez
# (yanlış bölüme yollamak, hiç yollamamaktan pahalıdır).

# ABAP/DDL bildirim açıcıları — SÖZDİZİMİ (eşleme değil): rot etmez. Tanınmayan bir açıcı
# çıkarsa dal SESSİZ düşer (fail-open), yanlış işaretçi üretmez.
_ACICILAR = ("define", "extend", "annotate", "managed", "unmanaged", "projection",
             "class", "interface", "report", "program", "function", "form")
_TOKEN = re.compile(r"[a-z][a-z0-9_]*")
_MD_YOL = re.compile(r"(?:playbook/)?(?:checklists/)?[\w-]+\.md")
_MD_CIPLAK = re.compile(r"\badt-[a-z0-9-]+\b")
_BASLIK = re.compile(r"^#{2,6}\s+(.*\S)\s*$")


def _ikili(satir: str):
    """Bildirim satırının TÜR bölümünden ardışık 2'li token demeti (küçük harf).

    ⛔ YALNIZ OBJE ADINDAN ÖNCESİ: bir artefaktın TÜRÜ adından önce bildirilir; adından
    sonrası (`as select from ...`) gövdedir. Ölçülmüş FP (bu turda, düzeltildi): tüm
    satır alınınca düz bir view-entity `select from` üzerinden `adt-cds.md § T3
    (read-only consumption)` tuzak notuna yollanıyordu — YANLIŞ bölüm. Kesme ölçütü
    sözdizimseldir: `_`/rakam taşıyan token (obje adı), `z`/`y` ile başlayan ad, ya da
    gövde açıcıları (`as` · `{` · `(` · `;`).
    """
    t = []
    for ham in re.split(r"[\s,]+", satir.strip()):
        h = ham.strip("`'\"")
        d = h.lower()
        if not d:
            continue
        if d in ("as", "with", "provider") or d[:1] in "{(;":
            break
        if "_" in d or any(c.isdigit() for c in d) or (d[:1] in "zy" and len(d) > 3):
            break
        m = _TOKEN.match(d)
        if not m:
            break
        t.append(m.group(0))
    return [" ".join(t[i:i + 2]) for i in range(len(t) - 1)]


def _bildirim_ifadeleri(source: str):
    """Kaynağın KENDİ bildirim satırlarından ifade adayları.

    ⛔ SATIR PENCERESİ YOK: ilk deneme "ilk 60 satır" diyordu; gerçek korpusta (292
    artefakt) bu **2 abstract entity'yi KAÇIRDI** — bildirim 92. ve 117. satırdaydı
    (uzun banner yorumu). Dosya boyutu zaten `_kaynak_metni`de sınırlı.
    """
    ifadeler = []
    for ln in (source or "").splitlines():
        s = ln.strip()
        if not s or s.startswith(("//", "*", "@", '"', "/*")):
            continue
        ilk = s.split(None, 1)[0].lower().rstrip(";")
        if ilk in _ACICILAR:
            ifadeler.extend(_ikili(s))
    # tekrarları koru-sırala; uzun ifade önce (daha ayırt edici)
    return sorted(set(ifadeler), key=lambda x: (-len(x), x))


def _recete_dosyalari(satir: str, kok: Path):
    """`_checklist()` satırının ANDIĞI reçete dosyaları — TEK KAYNAK (kopya liste yok)."""
    adaylar = set(_MD_YOL.findall(satir)) | {a + ".md" for a in _MD_CIPLAK.findall(satir)}
    bulunan = []
    for ad in sorted(adaylar):
        temiz = ad.split("/")[-1]
        for alt in ("", "checklists"):
            y = kok / "playbook" / alt / temiz if alt else kok / "playbook" / temiz
            if y.is_file() and y not in bulunan:
                bulunan.append(y)
    return bulunan


def _alt_tur(source: str, satir: str, kok: Path):
    """(ifade, göreli-yol, başlık) — alt-türün AYRI bölümü varsa; yoksa None.

    Belirsizlik (>1 başlık) → None. Hata → None (fail-open; taban satırı bozulmaz).
    """
    try:
        ifadeler = _bildirim_ifadeleri(source)
        if not ifadeler:
            return None
        dosyalar = _recete_dosyalari(satir, kok)
        if not dosyalar:
            return None
        basliklar = []
        for y in dosyalar:
            try:
                metin = y.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for ln in metin.splitlines():
                m = _BASLIK.match(ln)
                if m:
                    # ⛔ Başlıktaki KOD PARÇALARI (`...`) eşleşme sözlüğüne GİRMEZ.
                    # Ölçülmüş FP (292 gerçek artefakt, bu turda yakalandı): §ABSTRACT
                    # ENTITY başlığı örnek sözdizimini `define [root] abstract entity`
                    # olarak taşıyor ⇒ "define root" ikilisi başlığa giriyordu ve DÜZ bir
                    # `define root view entity ...` (30 artefakt) o bölüme yollanıyordu.
                    # Başlığın kod-DIŞI metni türü zaten adlandırır ("ABSTRACT ENTITY").
                    duz = re.sub(r"`[^`]*`", " ", m.group(1))
                    basliklar.append((y, m.group(1), " ".join(_TOKEN.findall(duz.lower()))))
        for ifade in ifadeler:
            vurus = [(y, b) for y, b, d in basliklar if ifade in d]
            if len(vurus) == 1:
                y, b = vurus[0]
                try:
                    goreli = y.relative_to(kok).as_posix()
                except Exception:
                    goreli = y.name
                return (ifade, goreli, b)
        return None
    except Exception:
        return None


def _kaynak_metni(ti: dict) -> str:
    """`source` yoksa `file_path`ten oku (gerçek payload'da iki biçim de görüldü)."""
    s = ti.get("source")
    if isinstance(s, str) and s.strip():
        return s
    fp = ti.get("file_path")
    if isinstance(fp, str) and fp.strip():
        try:
            p = Path(fp)
            if p.is_file() and p.stat().st_size < 400_000:
                return p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass
    return ""


def _session_id(proj: Path) -> str:
    try:
        d = json.loads((proj / ".claude" / ".current_session").read_text(encoding="utf-8"))
        return str(d.get("session_id") or "")
    except Exception:
        return ""


def _already_hinted(proj: Path, sid: str, grup: str) -> bool:
    """Session+worktype başına BİR kez. Marker .claude/.worktype_hinted.json (git-dışı)."""
    f = proj / ".claude" / ".worktype_hinted.json"
    try:
        st = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        st = {}
    if st.get("session") != sid:                      # yeni session → sıfırla
        st = {"session": sid, "hinted": []}
    if grup in st.get("hinted", []):
        return True
    st.setdefault("hinted", []).append(grup)
    try:
        f.write_text(json.dumps(st), encoding="utf-8", newline="\n")
    except Exception:
        pass
    return False


def _parse_fail_notu() -> None:
    """Parse-fail dalinin SESSIZLIGINI kaldirir; exit 0 fail-safe'i AYNEN korunur.

    Gerekce + sinif kaydi: scripts/hooks/README.md S4. ASCII-only + yazma hatasi
    fail-safe'i BOZMAMALI (except: pass).
    """
    try:
        sys.stderr.write(
            "[sap_worktype_hint] GIRDI-PARSE-EDILEMEDI: stdin JSON okunamadi -> fail-safe "
            "SERBEST (exit 0); KARAR DEGILDIR (girdi hic okunamadi). "
            "Negatif-test: governance/infra-test-recipes.md B0b\n")
    except Exception:
        pass


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        _parse_fail_notu()
        return 0
    tool = data.get("tool_name", "") or ""
    ti = data.get("tool_input", {}) or {}

    if tool in _TOOL_TIPI:
        otype = _TOOL_TIPI[tool]
    elif tool in _TIP_TOOLLARI and isinstance(ti, dict):
        otype = ti.get("object_type", "") or ""
    else:
        return 0                                       # SAP-yazma tool'u değil → sessiz

    grup, satir = _checklist(otype)
    if not grup:
        return 0                                       # checklist'i olan bir worktype değil

    # ALT-TÜR: artefaktın KENDİ bildiriminden (tahmin değil). core kökü = bu dosyanın
    # iki üstü — core'un KENDİ varlığı olduğu için `__file__` türevi meşrudur (CORE-03).
    alt = _alt_tur(_kaynak_metni(ti) if isinstance(ti, dict) else "",
                   satir, Path(__file__).resolve().parents[2])
    if alt:
        satir += (" · ⭐ ALT-TÜR: kaynağın kendi bildirimi `%s` — bu tür için AYRI bölüm "
                  "VAR, ÖNCE ONU OKU: %s § \"%s\" (kanonik bölüm bu alt-türde "
                  "geçerli OLMAYABİLİR)" % (alt[0], alt[1], alt[2]))

    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    sid = _session_id(proj)
    # Dedup ANAHTARI alt-türü TAŞIR: aynı obje-tipinin farklı alt-türü FARKLI reçetedir;
    # tek "cds" anahtarı, ilk view-entity push'undan sonra abstract entity uyarısını
    # sessizce yutardı (ölçülmüş vakanın ikinci yüzü).
    anahtar = grup if not alt else "%s:%s" % (grup, alt[0])
    if _already_hinted(proj, sid, anahtar):
        return 0                                       # bu worktype bu session'da hatırlatıldı

    # Yol öneki: core/ junction (öneksiz Read çözülmez — D29).
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # core/scripts
        from utils.inject_paths import core_onekle  # type: ignore
        satir = core_onekle(satir)
    except Exception:
        pass

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": (
                f"[SAP-yazma worktype hatırlatması — DETERMİNİSTİK, obje-tipi='{otype}'] "
                f"{satir}. SAP-yazma öncesi ADR 0006 run_review pre-flight'ı KOŞ (PASS→yaz). "
                "Bu, checklist'i doğru anda hatırlatan fail-closed sigortadır (session'da 1 kez)."
            ),
        }
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
