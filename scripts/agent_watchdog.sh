#!/usr/bin/env bash
# Agent watchdog — dış-gözlemlenebilir sağlık izleyici (transcript'e GÜVENMEZ; agent .output buffered/geç yazılır).
# Kullanım: agent_watchdog.sh   (iş-özel probe'lar $PROJ/.claude/watchdog_probes dosyasından okunur)
#   watchdog_probes satır formatı:  <url-path>|<beklenen-desen>
#     - url-path: $H'ye eklenir (örn. /sap/bc/adt/ddic/ddl/sources/zXXX/source/main)
#     - desen DOLU  → gövdede grep -c sayımı (metadata'da alan var mı gibi)
#     - desen BOŞ   → yalnız HTTP kodu (obje var/yok — 200/404 ilerleme sinyali)
#     - '#' ile başlayan / boş satır atlanır. Dosya YOKSA yalnız reach-kontrolü yapılır.
# Her ~100s: SAP/ADT erişimi + probe fingerprint'i. Değişmezse stall sayacı artar.
# YAYIN (stdout satırı = Monitor bildirimi → lider'e ulaşır):
#   - ALERT: SAP erişilemez  VEYA  ~5dk ilerleme yok (stall)  → lider müdahale eder
#   - STATUS: her ~5dk periyodik sağlık (kullanıcı istediği 5dk kontrol)
# Amaç: 20-dk körlük yerine ≤5dk'da stall tespiti + garantili periyodik check-in.

set -u
# B10/B-6: proje-koku env-first; host .conn_adt'ten; probe listesi opsiyonel dosyadan
PROJ="${CLAUDE_PROJECT_DIR:-$PWD}"
CONN="$PROJ/.conn_adt"
U=$(grep -i '^ADT_SAP_USER=' "$CONN" | cut -d= -f2 | tr -d '\r')
P=$(grep -i '^ADT_SAP_PASSWORD=' "$CONN" | cut -d= -f2- | tr -d '\r')
H="$(grep -m1 '^ADT_SAP_URL' "$CONN" 2>/dev/null | cut -d= -f2- | tr -d ' ')"
[ -z "$H" ] && { echo "watchdog: .conn_adt/ADT_SAP_URL yok — izleme kapali"; exit 0; }
PROBES_FILE="$PROJ/.claude/watchdog_probes"   # satir: <url-path>|<beklenen-desen> (başlıktaki format notu)

probe() {
  # ADT erişimi (VPN/MCP ölümü burada 200!=reach ile yakalanır)
  local reach line path pat c n out
  reach=$(curl -sk -o /dev/null -w "%{http_code}" -u "$U:$P" "$H/sap/bc/adt/discovery" --max-time 12 2>/dev/null)
  out="reach=$reach"
  if [ -f "$PROBES_FILE" ]; then
    n=0
    while IFS='|' read -r path pat || [ -n "$path" ]; do
      path="${path%$'\r'}"; pat="${pat%$'\r'}"
      case "$path" in ''|'#'*) continue;; esac
      n=$((n+1))
      if [ -n "$pat" ]; then
        c=$(curl -sk -u "$U:$P" "$H$path" --max-time 15 2>/dev/null | grep -c -- "$pat")
        out="$out p$n=$c"
      else
        c=$(curl -sk -o /dev/null -w "%{http_code}" -u "$U:$P" "$H$path" --max-time 10 2>/dev/null)
        out="$out p$n=http$c"
      fi
    done < "$PROBES_FILE"
  fi
  echo "$out"
}

prev=""; stall=0; cyc=0
probes_info="yalniz-reach"; [ -f "$PROBES_FILE" ] && probes_info="probes=$PROBES_FILE"
echo "STATUS $(date +%H:%M:%S) watchdog basladi ($probes_info) — ~100s poll, 5dk STATUS, stall/erisimsiz ALERT"
while true; do
  cyc=$((cyc+1))
  fp=$(probe)
  reach=$(echo "$fp" | sed -n 's/.*reach=\([0-9]*\).*/\1/p')
  if [ "$reach" != "200" ]; then
    echo "ALERT $(date +%H:%M:%S) SAP/ADT ERISILEMEZ (reach=$reach) — MCP/VPN/oturum kontrol et. [$fp]"
  fi
  # Stall tespiti YALNIZ probe'lu modda anlamlı (reach-only fingerprint hep sabittir → sahte ALERT olur)
  if [ -f "$PROBES_FILE" ]; then
    if [ "$fp" = "$prev" ]; then stall=$((stall+1)); else stall=0; prev="$fp"; fi
    if [ "$stall" -ge 3 ]; then
      echo "ALERT $(date +%H:%M:%S) STALL — ~5dk SAP ilerlemesi YOK: [$fp] — agent takilmis olabilir (MCP olu?), probe+mudahale et."
      stall=0
    fi
  fi
  if [ $((cyc % 3)) -eq 0 ]; then
    echo "STATUS $(date +%H:%M:%S) [$fp] (stall_sayaci=$stall)"
  fi
  sleep 100
done
