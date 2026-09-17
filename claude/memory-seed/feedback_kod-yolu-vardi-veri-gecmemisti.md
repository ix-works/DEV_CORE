---
name: feedback_kod-yolu-vardi-veri-gecmemisti
description: Bir kod dalının/kontrolün hiç ateşlenmemiş olması doğru çalıştığının kanıtı değil, yalnız o veriyle hiç karşılaşmadığının kanıtıdır — "yıllardır sorun çıkmadı" bir güvence değil
metadata:
  type: feedback
---

**KURAL:** *"Bu yıllardır çalışıyor, hiç sorun çıkmadı"* bir **doğruluk kanıtı DEĞİLDİR.**
Bir kod dalı ya da kontrol **hiç ateşlenmemişse**, bu yalnız **o veriyle karşılaşmadığını** gösterir.
Kusur o gün doğmadı — **o gün tetiklendi.**

**Ölçülmüş üç vaka (hepsi 2026-08-19, aynı gün):**

| Vaka | Kod yolu | Neden hiç ısırmamıştı |
|---|---|---|
| `B-13` `populate_tables.py` CURR dalı | `qty_type == 'CURR'` — **ulaşılamaz** (CSV `type` kolonu **DTEL adı** taşır) | Bu script'le yaratılmış **hiçbir Z tabloda CURR alan yoktu**; ZSD001 dala **ilk giren** |
| `check_cds_currency_reference` kapsamı | `'define view' in text` — `'define root view entity'` içinde **yok** | 30 root-view dosyasının **yalnız 2'si** tutar/miktar taşıyordu; A-16 sayıyı 5'e çıkardı |
| `check_cds_currency_reference` derinliği | **eksik** annotation hiç aranmıyor | Kirletilmiş dosya `rc=0` *"temiz"* döndü — pozitif kontrol kurulmasaydı görülmezdi |

**NASIL UYGULA:**
1. *"Neden şimdiye kadar çıkmadı?"* sorusuna **spekülasyonla** cevap verme — **ölç**: o kod yolundan
   bugüne kadar **hangi veri geçti**? Kaç vaka? *(Bu soru üç kez soruldu, üçünde de ölçüm cevabı verdi.)*
2. Bir kontrolün *"temiz"* dönmesi, **ona bakacak veri olduğunu** kanıtlamaz. ⭐ **Pozitif kontrol kur:**
   bilerek kirletilmiş bir vaka **yakalanıyor mu**? Yakalamıyorsa o yeşil **bilgi taşımıyor**.
3. Yeni bir veri sınıfı bir yola **ilk kez** giriyorsa (ilk CURR alan, ilk root view, ilk çoklu kayıt),
   o yolu **kanıtlanmış saymadan** önce ölç.

[[feedback_dogrulama-sezgileri-dort-kural]] · [[feedback_exit0-degil-cikti-kaniti]] ·
[[feedback_yesil-sinyalin-kapsamini-sor]] · [[feedback_arastir-once-patinaj-uretim-gorev]]
