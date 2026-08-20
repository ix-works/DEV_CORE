"""
check_rap_byassoc_keys_only.py — RAP ccimp/class'larda keys-only BY-assoc read tuzağı (ADVISORY).

Tuzak (standards/05 §5 · bug-checklist BE-20 · feedback_rap-by-assoc-read-all-fields):
  READ ENTITIES ... ENTITY parent BY \\_child FROM <key> RESULT lt
  -> child'ın YALNIZ KEY alanlarını döner; non-key (tarih/durum/tip/tutar) INITIAL kalır
  -> validation/determination SESSİZCE yanlış çalışır (syntax 0-error, RUNTIME'da çıkar).
  Non-key okuyacaksan ALL FIELDS WITH / FIELDS (...) WITH (FROM değil) ŞART.

Bu validator HARD blok DEĞİL (her FROM read bug değil — yalnız existence/line_exists için meşru).
`READ ENTITIES ... BY \\_assoc ... FROM ...` read'lerini (ALL FIELDS / FIELDS ( olmayan) WARNING
olarak listeler → reviewer/bug-expert BE-20 ile "non-key alan okunuyor mu" doğrular.

⚠ NEDEN ADVISORY (tasarım kararı, kusur DEĞİL — standards/05 §5.1 satırı bunu AÇIKÇA yazar:
"Yalnız existence/key kontrolü (line_exists) gerekiyorsa `FROM` yeterli"): desen, meşru
existence-read ile hatalı non-key-read'i AYIRT EDEMEZ — ayrım okunan alanın kullanımındadır,
statik olarak görülemez. Ölçüldü (2026-08-20, canlı korpus): 2 bulgu var, İKİSİ DE MEŞRU
(ZCL_SD015_BOOKING.ccimp.abap:191 ve :316; kodun kendi yorumu "Sayım için KEY okuma yeterli").
Default'u FAIL yapmak 2 DOĞRU kodu bloklardı ⇒ exit 0 KORUNUR.

EXIT SÖZLEŞMESİ (kardeş warn-first gate'lerle aynı — prior-art check_fs_no_analysis_log):
  · default              : bulgu olsa da exit 0 (advisory; run_all_validators'da görünür, bloklamaz)
  · `--strict`           : BİLEREK NO-OP. `run_all_validators --strict` bayrağı TÜM validator'lara
                           iletilir; bu gate'i oradan hard'a terfi ettirmek terfi kararını kazara
                           bir ÇAĞIRANIN eline verirdi (ADR 0019 §54 shakeout dersi).
  · `--bulguda-exit1`    : bulgu varsa exit 1 (opt-in; fixture/korpus ve bilinçli çağıran için).
  · ÖLÇÜLEMEDİ           : okunamayan dosya → exit 2. "ÖLÇEMEDİM" != "TEMİZ" (fail-closed);
                           eskiden sessizce `continue` edilip altta "[OK] ... aday'ı yok" basılıyordu.
  · `--selftest`         : gömülü kırmızı/yeşil fixture ile kendi kendini test eder.

Kullanım: python scripts/validators/check_rap_byassoc_keys_only.py [--bulguda-exit1] [--selftest]
"""
# ENFORCES: BE-20  (ADR 0019 coverage binding)
# GATE-SEVERITY: advisory  (default exit 0 — coverage özetinde "bloklayıcı" sayılMAZ)
import re
import sys
from pathlib import Path
import sys as _pc_sys
from pathlib import Path as _pc_Path
_pc_sys.path.insert(0, str(_pc_Path(__file__).resolve().parents[1]))
from utils.project_config import project_root, source_dir  # K12: kaynak-klasor adi config'ten
# K1 (2026-08-20): ORTAK kapsam sozlesmesi — 'ihlal yok' ile 'bakacak dosya yok'
# ayrilir. 0 dosya FAIL URETMEZ (mesru olabilir), ama SESSIZ de gecmez.
from utils.kapsam import Kapsam  # noqa: E402

KAPSAM = Kapsam('.abap')   # K1: taranan dosya sayaci

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ADR 0020: junction'da __file__ DEV_CORE'a çözülür → kanonik project_root()/source_dir()
REPO = project_root()
ERP = source_dir()

# READ ENTITIES ... BY \_assoc ... (FROM | ALL FIELDS WITH | FIELDS ( ) ... RESULT
# Statement = "READ ENTITIES" ... "RESULT" arası (çok satır).
READ_STMT = re.compile(
    r"READ\s+ENTITIES\b.*?\bRESULT\b", re.IGNORECASE | re.DOTALL)
BY_ASSOC = re.compile(r"BY\s+\\_\w+", re.IGNORECASE)
SAFE = re.compile(r"\bALL\s+FIELDS\s+WITH\b|\bFIELDS\s*\(", re.IGNORECASE)
USES_FROM = re.compile(r"\bFROM\b", re.IGNORECASE)


def scan_text(txt: str):
    """→ [(line_no, assoc)] — tek kaynak metinde keys-only BY-assoc read adayları.

    Dosya sisteminden BAĞIMSIZ (selftest ve fixture bunu doğrudan çağırır).
    """
    out = []
    for m in READ_STMT.finditer(txt):
        stmt = m.group(0)
        m_assoc = BY_ASSOC.search(stmt)
        if not m_assoc:
            continue          # BY-assoc read değil
        if SAFE.search(stmt):
            continue          # ALL FIELDS WITH / FIELDS ( -> güvenli
        if not USES_FROM.search(stmt):
            continue
        out.append((txt[: m.start()].count("\n") + 1, m_assoc.group(0)))
    return out


# ── Gömülü korpus (--selftest): gate'i korpussuz da kırmızı/yeşil yapabilmek için ──
RED_FIXTURE = """CLASS lcl_x IMPLEMENTATION.
  METHOD bad.
    READ ENTITIES OF zi_root IN LOCAL MODE
      ENTITY Root BY \\_Item
        FROM VALUE #( ( RootId = ls-RootId ) )
      RESULT lt_item.
  ENDMETHOD.
ENDCLASS.
"""
GREEN_FIXTURE = """CLASS lcl_x IMPLEMENTATION.
  METHOD good_all_fields.
    READ ENTITIES OF zi_root IN LOCAL MODE
      ENTITY Root BY \\_Item
        ALL FIELDS WITH VALUE #( ( RootId = ls-RootId ) )
      RESULT lt_item.
  ENDMETHOD.
  METHOD good_selected_fields.
    READ ENTITIES OF zi_root IN LOCAL MODE
      ENTITY Root BY \\_Item
        FIELDS ( Status Amount ) WITH VALUE #( ( RootId = ls-RootId ) )
      RESULT lt_item.
  ENDMETHOD.
  METHOD good_direct_read_no_assoc.
    READ ENTITIES OF zi_root IN LOCAL MODE
      ENTITY Root
        FROM VALUE #( ( RootId = ls-RootId ) )
      RESULT lt_root.
  ENDMETHOD.
  METHOD good_all_fields_with_from_word.
    " SAFE deseninin tek gerçek işi: ifadede `FROM` KELİMESİ geçer ama okuma modu
    " ALL FIELDS WITH'tir (CORRESPONDING ... FROM ...). USES_FROM tek başına eleyemez.
    READ ENTITIES OF zi_root IN LOCAL MODE
      ENTITY Root BY \\_Item
        ALL FIELDS WITH CORRESPONDING #( lt_keys FROM lt_source )
      RESULT lt_item.
  ENDMETHOD.
ENDCLASS.
"""


def selftest() -> int:
    ok = True
    kirmizi = scan_text(RED_FIXTURE)
    if len(kirmizi) != 1:
        print(f"[SELFTEST-FAIL] kırmızı fixture: beklenen 1 bulgu, bulunan {len(kirmizi)}"); ok = False
    yesil = scan_text(GREEN_FIXTURE)
    if yesil:
        print(f"[SELFTEST-FAIL] yeşil fixture FP verdi: {yesil}"); ok = False
    print("[SELFTEST] " + ("OK — kırmızı yakalandı, ALL FIELDS/FIELDS(..)/assoc'suz read'ler serbest"
                           if ok else "FAIL"))
    return 0 if ok else 1


def main() -> int:
    argv = sys.argv[1:]
    if "--selftest" in argv:
        return selftest()
    # "--strict" run_all_validators uyumu için KABUL EDİLİR ama NO-OP'tur (yukarıdaki
    # sözleşme); bulguda exit 1 yalnız bilinçli çağıranın ayrı bayrağıyla gelir.
    bulguda_exit1 = "--bulguda-exit1" in argv

    findings = []
    okunamadi = 0
    import os
    _prune = {"node_modules", "dist", ".tmp", "tmp", ".git", "worktrees"}
    abap_files = []
    for dirpath, dirnames, filenames in os.walk(ERP):  # PERF: node_modules budama
        dirnames[:] = [d for d in dirnames if d.lower() not in _prune]
        abap_files += [Path(dirpath) / fn for fn in filenames if fn.endswith(".abap")]
    for f in KAPSAM.say(abap_files):
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            # FAIL-CLOSED (sınıf: "DOĞRULAMA KOŞAMADI != DOĞRULANDI"): okunamayan dosya
            # eskiden sessizce atlanıyor ve altta "[OK] ... aday'ı yok" basılıyordu —
            # gate ÖLÇMEDİĞİ bir dosya için TEMİZ diyordu.
            print(f"[ÖLÇÜLEMEDİ] {f}: okunamadı ({e.__class__.__name__}: {e}) — "
                  "bu 'temiz' ANLAMINA GELMEZ.")
            okunamadi += 1
            continue
        rel = f.relative_to(REPO).as_posix()
        for line_no, assoc in scan_text(txt):
            findings.append((rel, line_no, assoc))

    if okunamadi:
        print(f"Özet: {okunamadi} dosya OKUNAMADI (ölçüm eksik) — exit 2.")
        return 2

    if findings:
        print("[WARN] keys-only BY-assoc read aday(lar)ı (BE-20 ile doğrula — non-key alan okunuyorsa ALL FIELDS WITH):")
        for rel, ln, assoc in findings:
            print(f"   {rel}:{ln}  READ ENTITIES ... {assoc} ... FROM (ALL FIELDS/FIELDS WITH yok)")
        print("   → Yalnız existence/line_exists ise OK; non-key alan (ls-Field) okunuyorsa ALL FIELDS WITH kullan.")
        return 1 if bulguda_exit1 else 0
    print("[OK] keys-only BY-assoc read aday'ı yok (tüm BY-assoc read'ler ALL FIELDS/FIELDS WITH veya existence-only)." + KAPSAM.ek())
    return 0


if __name__ == "__main__":
    sys.exit(main())
