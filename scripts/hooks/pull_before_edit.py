#!/usr/bin/env python3
# ENFORCES: ADR-0016  (ADR 0019 coverage binding)
"""PreToolUse (matcher: Edit|Write) — PULL-BEFORE-EDIT gate (ADR 0016 revize).

Yönetilen bir SAP source dosyasını (<source_root>/ altı, source uzantısı) düzenlemeden ÖNCE,
o DOSYANIN canlı GÜNCEL hali bu SEANSTA çekilmiş olmalı. Değilse edit BLOKLANIR (exit 2) ve
agent önce `core/scripts/sap_sync_pull.py` ile çeker. Böylece working-copy daima TAZE
canlıdan türer → push, canlıdaki belgelenmemiş bir değişikliği sessizce ezmez.

Q352 (2026-09-26) — iki değişiklik:
  · Damga ANAHTARI obje adı değil DOSYADIR (`source_drift.tazelik_anahtari`). Ad-anahtarı
    aynı adı taşıyan her dosyayı birlikte taze sayıyordu: sınıf ana kaynağı çekilince
    `.ccimp/.ccau` (hiç okunmamış), DDLS çekilince aynı adlı BDEF taze görünüyordu.
  · Sınıf alt-include'ları ARTIK KAPSAMDA (eskiden "ana sınıfla gelir" diye muaftı; gelmiyordu).
    Tipi dosya adından kesin çıkmayan dosyalar (`.abap`, `.prog.abap`, `.func.abap`, DDL
    ailesi) için önerilen komut `--type auto`dur — tip canlı ADT aramasıyla çözülür.
  Sınıflandırma + anahtar TEK KAYNAK: `scripts/source_drift.py` (pbe_siniflandir /
  tazelik_anahtari). Yükleyemezse kapı KARAR VEREMEZ → fail-safe SERBEST + görünür not.

EKLENTİ KAYDI (Q352 arayüz, 2026-09-26) — `_EK_DENETCILER`: çekirdek sınıflandırma bir
dosyayı TANIMAZSA (None) kayıtlı eklentilere sırayla sorulur. Eklenti = `scripts/hooks/<ad>.py`,
tek fonksiyon: `sinifla(path: Path, root: Path) -> Optional[dict]`
    None → bu dosya benim değil · dict → {"nesne": str, "tip": str, "komut": str}
    (`komut` = blok mesajında gösterilecek canlıdan-çekme komutu; nesne çözülemiyorsa
    açıklayıcı yer tutucu). Tazelik AYNI store'dan, AYNI anahtarla (`tazelik_anahtari`)
    okunur; çekici damgayı `source_drift.tazelik_damgala` ile yazar.
  · Eklenti dosyası YOKSA (tam o adla ModuleNotFoundError) → sessiz atla (kapsam yok).
  · Eklenti yüklenemezse (başka hata) → görünür not, o dosya için fail-safe SERBEST.
  · `sinifla()` hata atarsa → `EKLENTI-HATA: <ad>: <tip>` notu; o eklenti bu dosyayı
    tanımadı sayılır (fail-open ama GÖRÜNÜR, blok YOK — lider kararı 2026-09-26).
  Öncelik: çekirdek sınıflandırma önce; eklenti yalnız çekirdeğin tanımadığı dosyaya bakar.

MUAFİYET (sessiz GEÇ, exit 0):
  - SAP source DEĞİL (doküman/script/governance/ADR vb.) — gate yok.
  - ref_docs/ docs/ .tmp/ ... (deploy edilebilir kaynak değil).
  - Dosya YOK (yeni obje/yaratım — çekecek bir şey yok).
  - git-DIRTY (commit'siz yerel değişiklik = zaten üstünde çalışıyorsun; pull onu EZER → DOKUNMA).
  - session_id yoksa / store okunamıyorsa → fail-safe (editlemeyi brick'leme).

Bayatsa exit 2 (stderr → agent'a geri besler, ne yapacağını söyler).
"""
import io
import json
import os
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ADR 0020: junction'da __file__ DEV_CORE'a çözülür → kanonik project_root().
# Hook asla patlamamalı → import başarısızsa env/cwd fallback.
try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # core/scripts
    from utils.project_config import project_root as _project_root  # type: ignore
    ROOT = _project_root()
except Exception:
    ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or ".").resolve()
FRESH_STORE = ROOT / ".claude" / ".session_fresh.json"

# Q352: sınıflandırma + anahtar TEK KAYNAKTAN. (B2 2026-07-09 source_root dinamikliği
# `source_drift.PBE_KOK_SEGMENTLERI`e taşındı: güncel source_root + geçiş-eski "erp".)
# ⚠ `hook_shim` hook'u `runpy` ile koşturur → import kökü `__file__`ten türetilir (yukarıda).
_SINIF_HATASI = ""
try:
    from source_drift import pbe_siniflandir, tazelik_anahtari  # type: ignore
except Exception as _exc:  # noqa: BLE001 — kapı asla çökmemeli
    pbe_siniflandir = None      # type: ignore[assignment]
    tazelik_anahtari = None     # type: ignore[assignment]
    _SINIF_HATASI = f"{type(_exc).__name__}: {_exc}"


# Eklenti modül adları (scripts/hooks/<ad>.py). Sıra = sorulma sırası; ilk dict dönen kazanır.
_EK_DENETCILER = ("pbe_ui", "pbe_msag_textpool")


def _ek_yukleme_notu(ad: str, exc: BaseException) -> None:
    """Var olan bir eklenti yüklenemedi → görünür not (ASCII), exit 0 korunur."""
    try:
        sys.stderr.write(
            "[pull_before_edit] EKLENTI-YUKLENEMEDI: " + ad + " ("
            + f"{type(exc).__name__}: {exc}".encode("ascii", "replace").decode("ascii")
            + ") -> bu eklentinin dosyalari icin fail-safe SERBEST (exit 0); KARAR DEGILDIR.\n")
    except Exception:
        pass


def _ek_hata_notu(ad: str, exc: BaseException) -> None:
    """Eklentinin `sinifla()`ı istisna attı → görünür not (ASCII), exit 0 korunur."""
    try:
        sys.stderr.write(
            "[pull_before_edit] EKLENTI-HATA: " + ad + ": " + type(exc).__name__
            + " -> bu dosya icin eklenti karari YOK, fail-safe SERBEST (exit 0).\n")
    except Exception:
        pass


def _ek_sinifla(p: Path):
    """Kayıtlı eklentilere sor → ilk geçerli dict ya da None (bkz. modül başlığı)."""
    import importlib
    hooks_dizini = str(Path(__file__).resolve().parent)
    if hooks_dizini not in sys.path:
        sys.path.append(hooks_dizini)          # sona: mevcut modülleri gölgelemesin
    for ad in _EK_DENETCILER:
        try:
            mod = importlib.import_module(ad)
        except ModuleNotFoundError as exc:
            if exc.name == ad:
                continue                       # eklenti henüz yok → kapsam yok (sessiz)
            _ek_yukleme_notu(ad, exc)
            continue
        except Exception as exc:  # noqa: BLE001 — kapı asla çökmemeli
            _ek_yukleme_notu(ad, exc)
            continue
        fn = getattr(mod, "sinifla", None)
        if not callable(fn):
            _ek_yukleme_notu(ad, AttributeError("sinifla() yok"))
            continue
        try:
            sonuc = fn(p, ROOT)
        except Exception as exc:  # noqa: BLE001
            # Lider kararı 2026-09-26: fail-open ama GÖRÜNÜR (sessiz geçiş "kapsam yok"
            # ile ayırt edilemezdi). Blok YOK; bu eklenti bu dosyayı tanımadı sayılır.
            _ek_hata_notu(ad, exc)
            sonuc = None
        if isinstance(sonuc, dict):
            komut = sonuc.get("komut")
            if not isinstance(komut, str) or not komut.strip():
                komut = f"<{ad}: canlıdan-çekme komutu verilmedi>"
            return {"tur": "eklenti", "ad": str(sonuc.get("nesne") or "<AD>"),
                    "tip": str(sonuc.get("tip") or ad), "aile": None, "komut": komut,
                    "eklenti": ad}
    return None


def _git_dirty(p: Path) -> bool:
    """Working-tree'de commit'siz değişiklik var mı? (WIP → pull EZMESİN)."""
    try:
        r = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain", "--", str(p)],
            capture_output=True, text=True, timeout=8,
        )
        return bool(r.stdout.strip())
    except Exception:
        return False   # git yoksa/çalışmazsa dirty sayma (fail-safe: gate'i koru)


def _is_fresh(session_id: str, obj: str) -> bool:
    try:
        store = json.loads(FRESH_STORE.read_text(encoding="utf-8"))
    except Exception:
        return False
    if store.get("session_id") != session_id:   # store başka seanstan → bayat
        return False
    return obj in (store.get("objects") or {})


def _parse_fail_notu() -> None:
    """Parse-fail dalinin SESSIZLIGINI kaldirir; exit 0 fail-safe'i AYNEN korunur.

    Gerekce + sinif kaydi: scripts/hooks/README.md S4. ASCII-only yazilir (stderr'in
    utf-8 sarmalayicisi bu dosyada win32'ye kosulludur). Yazma hatasi fail-safe'i
    BOZMAMALI -> except: pass.
    """
    try:
        sys.stderr.write(
            "[pull_before_edit] GIRDI-PARSE-EDILEMEDI: stdin JSON okunamadi -> fail-safe "
            "SERBEST (exit 0); KARAR DEGILDIR (girdi hic okunamadi). "
            "Negatif-test: governance/infra-test-recipes.md B0b\n")
    except Exception:
        pass


def _siniflandirma_yok_notu(fp: str) -> None:
    """Tek kaynak yüklenemedi → kapı KARAR VEREMEZ. Sessiz geçmek 'gate yok' ile ayırt
    edilemezdi (parse-fail notuyla aynı sınıf) → görünür not, exit 0 korunur. ASCII."""
    try:
        sys.stderr.write(
            "[pull_before_edit] SINIFLANDIRMA-YUKLENEMEDI: source_drift okunamadi ("
            + _SINIF_HATASI.encode("ascii", "replace").decode("ascii")
            + ") -> fail-safe SERBEST (exit 0); KARAR DEGILDIR. Dosya: "
            + fp.encode("ascii", "replace").decode("ascii") + "\n")
    except Exception:
        pass


def _komut(s: dict, p: Path, session_id: str) -> str:
    if s.get("komut"):
        return s["komut"]              # eklenti kendi çekme komutunu verir
    ad = s.get("ad") or "<AD>"
    return (f"python core/scripts/sap_sync_pull.py {ad} --type {s['tip']} "
            f"--file \"{p}\" --session {session_id}")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        _parse_fail_notu()
        return 0   # input parse edilemedi → fail-safe geç

    # Savunmacı indirgeme (2026-08-01 bug-avı, W2-VH-02). ÖLÇÜLDÜ: 10 bozuk payload'ın
    # 5'inde uncaught istisna → exit 1 + traceback (`null`, `[]`, `"str"`, `42`,
    # `file_path:123` → `TypeError: expected str … not int`). `json.load` sarılıydı ama
    # sonrası dict/str varsayıyordu. Kontrol grubu aynı koşumda sağlamdı; `config_change_guard`
    # 10/10 çökmedi → savunmasız giriş işleme, ortam sorunu değil.
    if not isinstance(data, dict):
        return 0
    tool = data.get("tool_name", "")
    tool = tool if isinstance(tool, str) else ""
    if tool not in ("Edit", "Write", "MultiEdit"):
        return 0

    ti = data.get("tool_input", {})
    if not isinstance(ti, dict):
        return 0
    fp = ti.get("file_path") or ti.get("path") or ""
    if not isinstance(fp, str) or not fp:
        return 0                       # sayı/None/liste → yol yok, incelenecek şey yok
    p = Path(fp)

    if pbe_siniflandir is None or tazelik_anahtari is None:
        _siniflandirma_yok_notu(fp)
        return 0
    try:
        s = pbe_siniflandir(p)
    except Exception:
        s = None                       # sınıflandırılamayan yol → gate yok (eski davranış)
    if not s:
        s = _ek_sinifla(p)             # çekirdek tanımadı → eklentilere sor (Q352 arayüz)
    if not s:
        return 0                       # SAP source değil → gate yok
    if not p.exists():
        return 0                       # yeni dosya/obje → çekecek bir şey yok
    if _git_dirty(p):
        return 0                       # WIP (commit'siz) → zaten üstünde çalışıyorsun

    session_id = str(data.get("session_id") or "")
    if not session_id:
        return 0                       # seans kimliği yok → fail-safe geç

    try:
        anahtar = tazelik_anahtari(p, ROOT)
    except Exception:
        _siniflandirma_yok_notu(fp)
        return 0
    if _is_fresh(session_id, anahtar):
        return 0                       # bu seansta bu DOSYA çekildi → TAZE, geç

    cmd = _komut(s, p, session_id)
    ek = ""
    if s.get("eklenti"):
        # Eklentinin çekicisi `--offline` kaçışını desteklemeyebilir → sözünü veremeyiz.
        kacis = (f"(kapsam eklentisi: {s['eklenti']} · nesne {s.get('ad')} · tip "
                 f"{s.get('tip')}; SAP erişilemiyorsa çekicinin kendi kaçışına bak.)\n")
    else:
        kacis = ("SAP erişilemiyorsa: aynı komuta `--offline` ekle (fetch'siz taze damgalar; "
                 "canlıdan ezme riskini bilerek kabul edersin).\n")
    if s.get("tip") == "auto":
        ek = ("(tip dosya adından KESİN çıkmıyor — `--type auto` canlı ADT aramasıyla çözer; "
              "0 ya da >1 aday çıkarsa DURUR, tahmin etmez.)\n")
    sys.stderr.write(
        f"⛔ PULL-BEFORE-EDIT (PreToolUse guard, ADR 0016 revize): '{p.name}' bu seansta "
        f"SAP'den çekilMEDİ. Düzenlemeden ÖNCE güncel halini al:\n"
        f"   {cmd}\n"
        f"{ek}"
        f"(canlıyı çeker → {p.name} dosyasına yazar → DOSYAYI seans-taze damgalar; sonra "
        f"edit'i TEKRAR dene.)\n"
        f"AMAÇ: working-copy daima TAZE canlıdan türesin → push, canlıdaki belgelenmemiş "
        f"değişikliği ezmesin. Dosya başına seansta yalnız 1 kez.\n"
        f"{kacis}"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
