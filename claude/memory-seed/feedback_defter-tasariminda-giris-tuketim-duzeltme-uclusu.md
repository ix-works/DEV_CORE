---
name: feedback_defter-tasariminda-giris-tuketim-duzeltme-uclusu
description: "FS'te bir defter/havuz (beyanname lotu, tahsis, bakiye) tasarlanıyorsa GİRİŞ (lot nasıl doğar, kaynak, tarih, miktar) + TÜKETİM + DÜZELTME/İSTİSNA/GEÇİŞ (açılış bakiyesi) üçü birden yazılmalı — yalnız tüketim yazmak kullanıcı bulgusu oldu (ZSD001 v1.5)"
metadata:
  type: feedback
---

**Kural (kullanıcı bulgusu, 2026-08-17, ZSD001 FS v1.5):** "Beyanname eşleşmesinde tüketilecek beyanname bilgisinin nasıl alınacağı, nereden türetileceği net değil — tüketim tarafı tarif edilmiş, giriş/üretim tarafı tarif edilmemiş."

**Why:** Defter tasarımlarında (FIFO havuzu, tahsis, bakiye) tüketim akışı "asıl iş" gibi görünür ve giriş tarafı "zaten SAP'te var" diye atlanır; ama giriş lotunun **kaynağı (hangi belge/kalem), doğma anı, tarih alanı, miktar, iptal/yeniden kesim davranışı, /ITTR gibi dış zincir gecikmesi ve geçiş anındaki açılış bakiyeleri** yazılmazsa TS yazılamaz ve build'de her biri ayrı soru olur.

**How to apply — FS'te her defter için üç blok zorunlu:**
1. **GİRİŞ:** lot = hangi belge/kalem (anahtar), doğma olayı (türetilir mi/yazılır mı — ZSD000 kalıbı: SAP'in bildiğini yazma), tarih kuralı (öncelik zinciri, ör. override › CEDDT › FKDAT), miktar, iptal/yeniden kesim, dış kaynak gecikmesi durumu (CEDNO BEKLİYOR).
2. **TÜKETİM:** FIFO kuralı, tetik anı, snapshot, kilit.
3. **DÜZELTME / İSTİSNA / GEÇİŞ:** override, manuel lot, açılış bakiyeleri (Excel yükleme — yalnız Z, stok hareketi yok), yetim/snapshot-farkı durumları, aktarım (faz).
+ Senaryo tablosu ("ne olur / ne yazılır") — 15-20 satır; kullanıcı "her senaryoyu düşünerek anlat" istedi.
Doc-checklist'e aday madde: "defter/havuz varsa GİRİŞ+TÜKETİM+DÜZELTME üçlüsü tam mı?"

İlgili: [[project_zsd001-<MUSTERI-D>-konsinye]], [[project_zsd000-beyanname-eslesme]], [[feedback_fs-ts-iki-zihniyet-disiplini]]
