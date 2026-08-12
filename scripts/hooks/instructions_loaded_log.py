#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""InstructionsLoaded hook — hangi talimat dosyası, NE ZAMAN, NEDEN yüklendi?

NEDEN: `CLAUDE.md` / `.claude/rules/*.md` yüklemesi **sessizdir**. Bir kural hiç yüklenmese
de kimse fark etmez — 2026-07-10 denetiminde `AGENTS.md`'nin 356 satırı aylarca ölü kaldı ve
ekran teyidi her oturum "yüklendi" dedi. Ve `core/` bir junction'dır — junction ardındaki
kuralların yüklenip yüklenmediği KANIT ister (D29).

Bu hook karar vermez, bloklamaz. Yalnız `.tmp/instructions-loaded.log`'a satır yazar:
    <ISO-zaman>  <load_reason>  <memory_type>  <file_path>  [globs]

PAYLOAD ŞEMASI (Claude Code 2.1.206 binary'sinden okundu, tahmin DEĞİL):
    hook_event_name · file_path · memory_type · load_reason · globs? · trigger_file_path?
`load_reason` ∈ {session_start, nested_traversal, path_glob_match, include, compact}
`memory_type` ∈ {User, Project, Local, Managed}

⚠ 2026-07-10 dersi: bu hook önce `matcher`/`paths` anahtarlarını arıyordu — İKİSİ DE YOK.
Log aylarca `?  ?` yazdı ve "ölçüyoruz" sanıldı. Sessiz yüklemeyi yakalayan aletin kendisi
sessizce başarısızdı. Tanımadığın anahtarı ASLA varsayma → `_ham` alanı bu yüzden var.

Doğrulama: bir `.abap` dosyası okut → log'da `path_glob_match ... sap-source-protokolu.md`
satırı çıkmalı. Çıkmıyorsa kural ÖLÜDÜR (`paths:` yanlış ya da junction takip edilmiyor).

2026-07-31 (T0.7): eşzamanlı hook süreçleri TextIOWrapper append'inde satır bölüyordu
(150 satırlık logda 3 malformed). Yazım tek `os.write` + O_APPEND'e çevrildi — format
DEĞİŞMEDİ. Eski malformed satırlar veri olarak bırakıldı.

⚠ 2026-08-12: **T0.7 düzeltmesi Windows'ta İŞE YARAMADI** — dayandığı varsayım
(*"Windows'ta append-modlu WriteFile bu boyutta bölünmez"*) yanlıştı. Python'un `O_APPEND`'i
Windows'ta CRT `_O_APPEND`'e düşer ve bu, her yazımda **seek-to-end + write** yapar; iki
süreç arasında ATOMİK DEĞİLDİR. POSIX `O_APPEND` garantisi burada yoktur. Sonuç bölünme
değil **üzerine yazma = SATIR KAYBI**: aynı ofseti bulan iki hook süreci birbirini eziyordu.
Kontrol gruplu ölçüm (12 süreç × 300 satır): `os.write`+O_APPEND → 3600 satırdan **739 kayıp**;
`CreateFileW(FILE_APPEND_DATA)`+`WriteFile` → **0 kayıp**. Canlı logda 68 oturum açılışının
14 satırı eksikti (%6,9) ve bir kısmı hiç kırıntı bırakmadan yok olmuştu — yani bu defter
tam da kurulma amacı olan soruda (*"kural gerçekten yüklendi mi?"*) yanlış-negatif verebiliyordu.
⇒ Windows yolu `FILE_APPEND_DATA` handle'ına çevrildi (OS append'i tek işlemde yapar).
Format DEĞİŞMEDİ; POSIX yolu (gerçek O_APPEND) aynen korundu; hata halinde eski yola düşer.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass


def _win_append(yol: str, veri: bytes) -> bool:
    """Windows'ta ATOMİK append: `CreateFileW(FILE_APPEND_DATA)` + `WriteFile`.

    FILE_APPEND_DATA erişimiyle açılan handle'da yazım konumunu **çekirdek** belirler —
    "sonu bul + yaz" tek işlemdir, araya başka süreç giremez (MSDN, CreateFile/dwDesiredAccess).
    Python'un `O_APPEND`'i bu garantiyi VERMEZ (CRT her yazımda ayrıca seek eder).
    Dönüş: yazım tam olarak yapıldıysa True; aksi halde False (çağıran eski yola düşer).
    """
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                                wintypes.HANDLE)
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.WriteFile.argtypes = (wintypes.HANDLE, wintypes.LPCVOID, wintypes.DWORD,
                              ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID)
    k32.WriteFile.restype = wintypes.BOOL
    k32.CloseHandle.argtypes = (wintypes.HANDLE,)

    FILE_APPEND_DATA = 0x0004
    FILE_SHARE_READ_WRITE = 0x0003          # başka hook süreçleri aynı anda açabilsin
    OPEN_ALWAYS = 4                          # yoksa yarat, varsa aç
    FILE_ATTRIBUTE_NORMAL = 0x80
    GECERSIZ = ctypes.c_void_p(-1).value     # INVALID_HANDLE_VALUE

    h = k32.CreateFileW(yol, FILE_APPEND_DATA, FILE_SHARE_READ_WRITE, None,
                        OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, None)
    if not h or h == GECERSIZ:
        return False
    try:
        yazilan = wintypes.DWORD(0)
        ok = k32.WriteFile(h, veri, len(veri), ctypes.byref(yazilan), None)
        return bool(ok) and yazilan.value == len(veri)
    finally:
        k32.CloseHandle(h)


def _append(log: Path, satir: str) -> None:
    """Log satırını KAYIPSIZ ekle. Windows → FILE_APPEND_DATA · POSIX → gerçek O_APPEND."""
    veri = satir.encode("utf-8")
    if os.name == "nt":
        try:
            if _win_append(str(log), veri):
                return
        except Exception:
            pass  # ctypes yoksa/başarısızsa aşağıdaki eski yola düş (kayıplı ama sessiz kalmaz)
    fd = os.open(str(log), os.O_APPEND | os.O_CREAT | os.O_WRONLY)
    try:
        os.write(fd, veri)
    finally:
        os.close(fd)


def main() -> int:
    try:
        veri = json.load(sys.stdin)
    except Exception:
        return 0  # hiçbir zaman bloklamaz

    kok = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
    log = kok / ".tmp" / "instructions-loaded.log"
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        zaman = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

        sebep = veri.get("load_reason")
        yol = veri.get("file_path")
        tip = veri.get("memory_type")

        if sebep is None or yol is None:
            # Şema beklenenden farklı → SESSİZ KALMA, ham payload'ı dök.
            # (Bu dalın erişilemez olması yüzünden aylarca `? ?` yazıldı.)
            satir = f"{zaman}\tSEMA-DEGISTI\t?\t?\t_ham={json.dumps(veri, ensure_ascii=False)[:500]}\n"
        else:
            globs = veri.get("globs") or []
            tetik = veri.get("trigger_file_path") or ""
            ek = f"\tglobs={','.join(globs)}" if globs else ""
            ek += f"\ttrigger={tetik}" if tetik else ""
            satir = f"{zaman}\t{sebep}\t{tip or '?'}\t{yol}{ek}\n"

        # Atomik append — satır komple oluşturuldu, tek işlemde eklenir (bkz. `_append`).
        # ⚠ Buradaki eski `os.write`+O_APPEND yolu Windows'ta ATOMİK DEĞİLDİ ve satır
        # kaybettiriyordu (2026-08-12 ölçümü, docstring). Yol `_append`'e taşındı.
        _append(log, satir)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
