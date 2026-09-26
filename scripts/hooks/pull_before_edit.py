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
    None → bu dosya benim değil · dict → {"nesne": str, "tip": str, "komut": str,
    ["not": str]}
    · `komut` = YALNIZ çalıştırılabilir komut (nesne çözülemiyorsa argüman yer tutucusu,
      ör. `<BSP_ADI>`). ⛔ Eklenti `--session` BASMAZ: kapı seans kimliğini komutun SONUNA
      kendisi ekler — marker başka seansı gösterirken damga yanlış seansa gidip kapı
      döngüye giriyordu (bug gate N1, 2026-09-26). Komutta FARKLI bir `--session X` varsa
      kapı onu KENDİ kimliğiyle DEĞİŞTİRİR + görünür not basar (kapının okuduğu tek değer
      budur; başka değer döngüyü garanti eder). Aynı değer → dokunulmaz.
      Komut hiç verilmezse gösterilen yer tutucuya `--session` EKLENMEZ.
    · `not` (opsiyonel) = açıklama/kaçış (`--offline` vb.); iki uçtan kırpılıp blok
      mesajında komuttan sonra basılır. Eksik anahtar = eski davranış.
    Tazelik AYNI store'dan, AYNI anahtarla (`tazelik_anahtari`) okunur; çekici damgayı
    `source_drift.tazelik_damgala` ile yazar.
  · Eklenti dosyası YOKSA (tam o adla ModuleNotFoundError) → sessiz atla (kapsam yok).
  · Eklenti yüklenemezse (başka hata, `SystemExit` DAHİL; yalnız KeyboardInterrupt hariç) →
    görünür `EKLENTI-YUKLENEMEDI` notu, o dosya için fail-safe SERBEST.
  · `sinifla()` hata atarsa (`SystemExit` DAHİL) → `EKLENTI-HATA: <ad>: <tip>` notu; o eklenti bu dosyayı
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
import re
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
_EK_DENETCILER = ("_pbe_ui", "_pbe_msag_textpool")


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
        except KeyboardInterrupt:
            raise
        except BaseException as exc:  # noqa: BLE001 — kapı asla çökmemeli
            # Bug gate M2: `SystemExit` `Exception` DEĞİLDİR — import anında `sys.exit(2)`
            # ilgisiz HER dosya edit'ini rc 2 BLOKLUYORDU (brick). Not yolu + devam.
            _ek_yukleme_notu(ad, exc)
            continue
        fn = getattr(mod, "sinifla", None)
        if not callable(fn):
            _ek_yukleme_notu(ad, AttributeError("sinifla() yok"))
            continue
        try:
            sonuc = fn(p, ROOT)
        except KeyboardInterrupt:
            raise
        except BaseException as exc:  # noqa: BLE001 — M2: SystemExit(0) sessiz açık bırakmasın
            # Lider kararı 2026-09-26: fail-open ama GÖRÜNÜR (sessiz geçiş "kapsam yok"
            # ile ayırt edilemezdi). Blok YOK; bu eklenti bu dosyayı tanımadı sayılır.
            _ek_hata_notu(ad, exc)
            sonuc = None
        if isinstance(sonuc, dict):
            komut = sonuc.get("komut")
            yer_tutucu = not isinstance(komut, str) or not komut.strip()
            if yer_tutucu:
                komut = f"<{ad}: canlıdan-çekme komutu verilmedi>"
            not_ = sonuc.get("not")
            return {"tur": "eklenti", "ad": str(sonuc.get("nesne") or "<AD>"),
                    "tip": str(sonuc.get("tip") or ad), "aile": None, "komut": komut.strip(),
                    "komut_yer_tutucu": yer_tutucu, "eklenti": ad,
                    "not": not_.strip() if isinstance(not_, str) else ""}
    return None


def _git_dirty(p: Path) -> bool:
    """Working-tree'de commit'siz değişiklik var mı? (WIP → pull EZMESİN).

    Bug gate N2: git dosyanın KENDİ dizininde koşar (`-C <dosya.parent>`, yol = dosya adı) —
    `-C ROOT` kök dışındaki dosyada (kanonik `.wt` worktree) "outside repository" hatası
    verip BOŞ dönüyordu ⇒ WIP muafiyeti ölüydü. Kardeş `source_drift._git_working_copy_dirty`
    zaten bu desendedir.
    """
    try:
        r = subprocess.run(
            ["git", "-C", str(p.parent), "status", "--porcelain", "--", p.name],
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


_SESSION_ARG = re.compile(r"(?<!\S)--session(=|\s+)(\S+)")


def _komut(s: dict, p: Path, session_id: str) -> tuple:
    """-> (gösterilecek komut, ek not satırı ya da "")."""
    if s.get("komut"):
        # Eklenti komutu (sözleşme: YALNIZ çalıştırılabilir komut). Seans kimliğini KAPI
        # ekler (bug gate N1: marker başka seansı gösterirken damga yanlış seansa yazılıyor,
        # kapı döngüye giriyordu).
        komut = s["komut"]
        if s.get("komut_yer_tutucu"):
            return komut, ""               # çalıştırılabilir komut YOK → yer tutucuya ekleme
        eski = [m.group(2) for m in _SESSION_ARG.finditer(komut)]
        if not eski:
            return f"{komut} --session {session_id}", ""
        if all(v == session_id for v in eski):
            return komut, ""
        # Takip turu 3: FARKLI kimlik → kapının okuduğu kimlikle DEĞİŞTİR (bırakılsa damga
        # başka seansa yazılır, retry yine bloklanır = N1 döngüsü). Görünür not: sözleşme ihlali.
        komut = _SESSION_ARG.sub(lambda m: f"--session{m.group(1)}{session_id}", komut)
        return komut, (f"(not: eklenti komutundaki --session {', '.join(sorted(set(eski)))} "
                       f"kapının seans kimliğiyle değiştirildi — sözleşme: eklenti --session "
                       f"basmaz, kapı ekler.)\n")
    ad = s.get("ad") or "<AD>"
    return (f"python core/scripts/sap_sync_pull.py {ad} --type {s['tip']} "
            f"--file \"{p}\" --session {session_id}"), ""


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

    cmd, cmd_notu = _komut(s, p, session_id)
    ek = ""
    if s.get("eklenti"):
        # Eklentinin çekicisi `--offline` kaçışını desteklemeyebilir → sözünü veremeyiz.
        kacis = (f"(kapsam eklentisi: {s['eklenti']} · nesne {s.get('ad')} · tip "
                 f"{s.get('tip')}; SAP erişilemiyorsa çekicinin kendi kaçışına bak.)\n")
        # Eklentinin komutu dosyaya YAZMAYABİLİR (ör. canlıyla karşılaştırıp damgalar) →
        # "çeker/yazar" iddiası verilmez; yalnız sözleşme söylenir (damga = tazelik kanıtı).
        baslik = "bu seansta canlıyla TAZE doğrulanMADI. Düzenlemeden ÖNCE:"
        ne_olur = (f"(komutu koş → {p.name} seans-taze damgalanır (canlıyla eşitse); sonra "
                   f"edit'i TEKRAR dene.)\n")
        ne_olur += cmd_notu
        if s.get("not"):
            ne_olur += f"{s['not']}\n"   # eklentinin açıklaması/kaçışı (opsiyonel; kırpılmış)
    else:
        kacis = ("SAP erişilemiyorsa: aynı komuta `--offline` ekle (fetch'siz taze damgalar; "
                 "canlıdan ezme riskini bilerek kabul edersin).\n")
        baslik = "bu seansta SAP'den çekilMEDİ. Düzenlemeden ÖNCE güncel halini al:"
        ne_olur = (f"(canlıyı çeker → {p.name} dosyasına yazar → DOSYAYI seans-taze damgalar; "
                   f"sonra edit'i TEKRAR dene.)\n")
    if s.get("tip") == "auto":
        ek = ("(tip dosya adından KESİN çıkmıyor — `--type auto` canlı ADT aramasıyla çözer; "
              "0 ya da >1 aday çıkarsa DURUR, tahmin etmez.)\n")
    sys.stderr.write(
        f"⛔ PULL-BEFORE-EDIT (PreToolUse guard, ADR 0016 revize): '{p.name}' {baslik}\n"
        f"   {cmd}\n"
        f"{ek}"
        f"{ne_olur}"
        f"AMAÇ: working-copy daima TAZE canlıdan türesin → push, canlıdaki belgelenmemiş "
        f"değişikliği ezmesin. Dosya başına seansta yalnız 1 kez.\n"
        f"{kacis}"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
