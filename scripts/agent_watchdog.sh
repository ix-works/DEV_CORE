#!/usr/bin/env bash
# Agent watchdog — dış-gözlemlenebilir sağlık izleyici (transcript'e GÜVENMEZ; agent .output buffered/geç yazılır).
# Kullanım: agent_watchdog.sh <mode>
#   mode=zsd015_batch_removal  → gateway backend söküm ilerlemesini SAP'den yoklar.
# Her ~100s: SAP/ADT erişimi + iş-özel ilerleme fingerprint'i. Değişmezse stall sayacı artar.
# YAYIN (stdout satırı = Monitor bildirimi → lider'e ulaşır):
#   - ALERT: SAP erişilemez  VEYA  ~5dk ilerleme yok (stall)  → lider müdahale eder
#   - STATUS: her ~5dk periyodik sağlık (kullanıcı istediği 5dk kontrol)
# Amaç: 20-dk körlük yerine ≤5dk'da stall tespiti + garantili periyodik check-in.

set -u
CONN="C:/<LEGACY_ROOT>/<PROJECT_NAME>/.conn_adt"
U=$(grep -i '^ADT_SAP_USER=' "$CONN" | cut -d= -f2 | tr -d '\r')
P=$(grep -i '^ADT_SAP_PASSWORD=' "$CONN" | cut -d= -f2- | tr -d '\r')
H="https://<SAP_HOST>.<SAP_DOMAIN>:44300"
MODE="${1:-zsd015_batch_removal}"

BATCH_CDS="zsd015_i_ihrse_stock_batch zsd015_i_sipse_stock_batch zsd015_i_batch_stock zsd015_i_ihrse_alloc zsd015_i_sipse_alloc zsd015_i_mmqty_by_bat zsd015_i_ewmqty_by_bat zsd015_i_ewmphys_by_bat"
PACK_CDS="zsd015_i_item_packing zsd015_c_item_packing zsd015_i_item_packing_p zsd015_i_item_packing_r"

probe() {
  # ADT erişimi (VPN/MCP ölümü burada 200!=reach ile yakalanır)
  local reach cnt sip gip
  reach=$(curl -sk -o /dev/null -w "%{http_code}" -u "$U:$P" "$H/sap/bc/adt/discovery" --max-time 12 2>/dev/null)
  if [ "$MODE" = "zsd015_packing" ]; then
    # ilerleme: YARATILAN packing CDS sayısı (gateway ilerledikçe 0->4) + GetItemPacking $metadata'da mı
    cnt=0
    for v in $PACK_CDS; do
      c=$(curl -sk -o /dev/null -w "%{http_code}" -u "$U:$P" "$H/sap/bc/adt/ddic/ddl/sources/$v/source/main" --max-time 10 2>/dev/null)
      [ "$c" = "200" ] && cnt=$((cnt+1))
    done
    gip=$(curl -sk -u "$U:$P" "$H/sap/opu/odata/sap/ZSD015_UI_IHRSE_O2/\$metadata?sap-client=100" --max-time 15 2>/dev/null | grep -c 'GetItemPacking')
    echo "reach=$reach packCds=$cnt getItemPacking=$gip"
    return
  fi
  # ilerleme: silinmemiş batch-CDS sayısı (STEP3 ilerledikçe 8->0)
  cnt=0
  for v in $BATCH_CDS; do
    c=$(curl -sk -o /dev/null -w "%{http_code}" -u "$U:$P" "$H/sap/bc/adt/ddic/ddl/sources/$v/source/main" --max-time 10 2>/dev/null)
    [ "$c" = "200" ] && cnt=$((cnt+1))
  done
  # ilerleme: SIPSE_O2 $metadata Batch var mı (STEP2.2'de gider)
  sip=$(curl -sk -u "$U:$P" "$H/sap/opu/odata/sap/ZSD015_UI_SIPSE_O2/\$metadata?sap-client=100" --max-time 15 2>/dev/null | grep -c 'Name="Batch"')
  echo "reach=$reach batchCds=$cnt sipBatch=$sip"
}

prev=""; stall=0; cyc=0
echo "STATUS $(date +%H:%M:%S) watchdog basladi (mode=$MODE) — ~100s poll, 5dk STATUS, stall/erisimsiz ALERT"
while true; do
  cyc=$((cyc+1))
  fp=$(probe)
  reach=$(echo "$fp" | sed -n 's/.*reach=\([0-9]*\).*/\1/p')
  if [ "$reach" != "200" ]; then
    echo "ALERT $(date +%H:%M:%S) SAP/ADT ERISILEMEZ (reach=$reach) — MCP/VPN/oturum kontrol et. [$fp]"
  fi
  if [ "$fp" = "$prev" ]; then stall=$((stall+1)); else stall=0; prev="$fp"; fi
  if [ "$stall" -ge 3 ]; then
    echo "ALERT $(date +%H:%M:%S) STALL — ~5dk SAP ilerlemesi YOK: [$fp] — agent takilmis olabilir (MCP olu?), probe+mudahale et."
    stall=0
  fi
  if [ $((cyc % 3)) -eq 0 ]; then
    echo "STATUS $(date +%H:%M:%S) [$fp] (stall_sayaci=$stall)"
  fi
  sleep 100
done
