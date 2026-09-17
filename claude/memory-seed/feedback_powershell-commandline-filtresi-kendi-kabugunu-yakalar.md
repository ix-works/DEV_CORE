---
name: feedback_powershell-commandline-filtresi-kendi-kabugunu-yakalar
description: "Get-CimInstance Win32_Process | Where CommandLine -like '*X*' filtresi, X'i içeren KENDİ PowerShell aracı kabuğunu da döndürür → Stop-Process kendini öldürür (exit 255, çıktı yok) ve 'kalan: 1' sahte sayım verir. $PID ve ParentProcessId -ne $PID ile dışla. 2026-08-29 watchdog daemon temizliğinde 5 tur kaybettirdi"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 199aed41-f1ec-4c03-ae34-a0b1b09c15be
---

**Süreç ararken kendi kabuğunu dışla.** `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*watchdog_daemon.sh*' }` sorgusu, komut satırında o literal'i taşıyan **PowerShell aracı sürecinin kendisini** de döndürür. Sonuçlar (2026-08-29, ölçüldü):
- `Stop-Process` döngüsü kendi kabuğunu öldürdü → araç **exit 255, çıktı kesik**, "Stop-Process çalışmıyor" sanıldı.
- Sayım hep **"kalan: 1"** gösterdi (o 1 = kendi kabuğum); gerçek daemon'lar çoktan ölmüştü. 5 ayrı kill turu + `taskkill` denemeleri boşa gitti.
- `taskkill /PID <bash $$>`: MSYS bash'in `$$`'ı Windows PID **değildir** ("process not found").

**How to apply:**
- Filtreye daima `-and $_.ProcessId -ne $PID -and $_.ParentProcessId -ne $PID` ekle; ya da literal'i değişkende tutup `-like "*$x*"` kullanma — komut satırında yine görünür. En sağlamı: hedef sürecin **ebeveyn ilişkisiyle** kökü bulmak.
- Bir daemon'ı öldürmeden önce **kendi durdurma mekanizmasını** ara (watchdog: `.tmp/claude_watchdog/stop_<sid>` sentinel) — temiz ve PID'siz.
- Bayat kalıntı ölçümü: `.tmp/claude_watchdog/` altında 110 `stop_*` + 3 heartbeat (eski oturumlar) — daemon kendi sentinel'ini silmiyordu.
İlgili: [[feedback_exit0-degil-cikti-kaniti]] · [[feedback_auto-mode-deny-kararsiz-yeniden-dene]] (aynı gün: ruleset PUT 3. denemede geçti)
