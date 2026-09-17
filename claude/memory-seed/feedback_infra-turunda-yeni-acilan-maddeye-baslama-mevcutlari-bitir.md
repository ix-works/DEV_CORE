---
name: feedback_infra-turunda-yeni-acilan-maddeye-baslama-mevcutlari-bitir
description: İnfra kuyruk turunda o tur içinde yeni açılan maddelere başlanmaz; önce mevcut (tur başında açık olan ve uçuştaki) maddeler bitirilir
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cca08bdf-c505-460c-a1ba-8d1635bd8f7c
---

**Kural (kullanıcı, 2026-09-13):** *"yeni madde açılırsa onlara başlama. mevcutları bitirelim."*
Tur sırasında açılan kayıt (ör. kardeş taramasından doğan Q320/Q321) o turda **spawn edilmez**;
kayda alınır ve kullanıcıya raporlanır. Önce uçuştaki PR'lar ve tur başında açık olan maddeler kapanır.

**Why:** Kuyruk bir turda 7 kapandı / 10 açıldı; her yeni madde anında işe dönünce tur hiç bitmiyor
ve "ne kadar iş kaldı" sorusu cevaplanamıyor. [[feedback_kardes-taramasi-spawn-oncesi-kapsama-alinir-kuyruga-yazilmaz]]
açılan madde sayısını azaltır; bu kural açılanın turu uzatmasını engeller.

**How to apply:** Turun sonunda yeni maddeleri listeleyip bir sonraki tur için kullanıcıya sun;
kendiliğinden başlatma. Kapsama alınabilen kardeş (aynı dosya kümesi, uçuştaki işin içinde) bu
kuralın dışındadır — o yeni madde değil, mevcut işin kapsamıdır.

Son-doğrulama: 2026-09-13 · Applies-to: infra kuyruk turları
