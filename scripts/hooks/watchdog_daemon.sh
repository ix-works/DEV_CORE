#!/usr/bin/env bash
# Detached watchdog daemon — SAP/ADT reachability'yi Claude/lider'den BAĞIMSIZ izler.
# Kopukluk (VPN/MCP ölümü) veya erişimsizlikte kullanıcıya doğrudan ALERT verir:
#   (1) Windows MessageBox popup (best-effort)  (2) .tmp/watchdog-alerts.log satırı.
# Heartbeat dosyası her tur güncellenir → launcher "zaten çalışıyor mu" kontrolü.
# Kullanım: watchdog_daemon.sh <session_id> [<proje_koku>]   (watchdog_launch.py DETACHED başlatır).
# Yaşam: ~2 saat (72 x 100s) VEYA stop-sentinel → çıkar. SessionEnd hook sentinel yazar.
set -u

SID="${1:-nosid}"
# Proje kökü: arg2 > env > BASH_SOURCE-türetimi. DİKKAT: bu dosya core'da yaşar; junction'lı
# projede BASH_SOURCE ../.. DEV_CORE'a çözülür (proje DEĞİL) → launcher arg2 geçirir.
PROJ="${2:-${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}}"
CONN="$PROJ/.conn_adt"
WD="$PROJ/.tmp/claude_watchdog"; mkdir -p "$WD"
LOG="$PROJ/.tmp/watchdog-alerts.log"
HB="$WD/heartbeat_$SID"
STOP="$WD/stop_$SID"
H="$(grep -m1 '^ADT_SAP_URL' "$CONN" 2>/dev/null | cut -d= -f2- | tr -d ' \r')"
U=$(grep -i '^ADT_SAP_USER=' "$CONN" 2>/dev/null | cut -d= -f2 | tr -d '\r')
P=$(grep -i '^ADT_SAP_PASSWORD=' "$CONN" 2>/dev/null | cut -d= -f2- | tr -d '\r')
[ -z "$H" ] && { echo "$(date '+%Y-%m-%d %H:%M:%S') END .conn_adt/ADT_SAP_URL yok — daemon kapali (proj=$PROJ)" >> "$LOG"; exit 0; }

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG"; }

alert() {
  local m="$1"
  log "ALERT $m"
  # Bağımsız Windows popup (best-effort; başarısız olursa log yeter).
  powershell.exe -NoProfile -WindowStyle Hidden -Command \
    "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('$m','SAP WATCHDOG ALERT',0,48) | Out-Null" \
    >/dev/null 2>&1 &
}

log "START watchdog daemon (sid=$SID pid=$$)"
touch "$HB"
fails=0
alerted=0   # B4 fix (2026-07-09): EDGE-triggered alert — kopuklugun BASINDA bir kez uyar,
            # kopuk sürerken SUS, recovery'de resetle. Eskiden level-triggered idi (fails>=2 → alert →
            # fails=0 → ~3dk sonra TEKRAR alert) → uzun kopuklukta Windows MessageBox SPAM (health-check B4).
for i in $(seq 1 72); do
  [ -f "$STOP" ] && { log "STOP sentinel → cikiyor"; rm -f "$STOP"; break; }
  reach=$(curl -sk -o /dev/null -w "%{http_code}" -u "$U:$P" "$H/sap/bc/adt/discovery" --max-time 12 2>/dev/null)
  date '+%s' > "$HB"
  if [ "$reach" != "200" ]; then
    fails=$((fails+1))
    log "reach=$reach (fails=$fails)"
    if [ "$fails" -ge 2 ] && [ "$alerted" -eq 0 ]; then
      alert "SAP/ADT ERISILEMEZ (reach=$reach) — VPN/MCP kopmus olabilir. Arka-plan agent STALL riski; kontrol et."
      alerted=1   # tek uyari; kopuk sürerken tekrar basma (fails'i sifirLAMA — recover'da temizlenir)
    fi
  else
    # recovery: onceki turda uyarilmissa "toparlandi" satiri + alert-bayragi reset (sonraki kopmada yine uyar).
    if [ "$alerted" -eq 1 ]; then
      log "reach=200 OK — TOPARLANDI (SAP erisim geri geldi; alert reset, tur=$i/72, sid=$SID)"
      alerted=0
    elif [ "$fails" -gt 0 ] || [ $(( i % 6 )) -eq 1 ]; then
      log "reach=200 OK (tur=$i/72, sid=$SID)"
    fi
    fails=0
  fi
  # ~100s uyu ama her 10s'te stop-sentinel kontrol et (SessionEnd hizli tepki).
  for s in $(seq 1 10); do
    [ -f "$STOP" ] && break
    sleep 10
  done
done
log "END watchdog daemon (sid=$SID)"
rm -f "$HB"
