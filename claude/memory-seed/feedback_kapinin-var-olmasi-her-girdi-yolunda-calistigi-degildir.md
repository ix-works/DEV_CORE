---
name: feedback_kapinin-var-olmasi-her-girdi-yolunda-calistigi-degildir
description: "Bir kapının/muhafızın kodda VAR olduğunu ölçmek, HER GİRDİ YOLUNDA çalıştığını ölçmez — kapanış ilanı bu yüzden sahte çıkabilir"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 276c51e4-6137-42af-afb9-b43b2613eac7
---

Bir kaydı "KAPANDI-DOĞRULANDI" ilan eden ölçüm, **kapatan kodun hangi girdi yolunu
kapsadığını** da yazmalıdır. Muhafızın kaynakta göründüğünü doğrulamak yeterli değildir:
aynı fonksiyona **birden fazla dal** giriyorsa, düzeltme yalnız birini kapatmış olabilir.

**Ölçülmüş vaka (2026-09-04, Q206 / Q106①):** `adt_grep_source`'un FUGR iskelet muhafızı
`query.py:1230`'da `if at == "functiongroup":` diye duruyordu ve iki ayrı denetim onu
"kapandı" saydı. Ama tip normalizasyonu (`_GREP_TYPE_MAP`, `query.py:1106-1107`)
**yalnız `package=` dalında** uygulanıyordu; `objects=` dalı (`:1170-1177`) tipi
`t.strip().lower()` ile **ham** geçiriyordu ⇒ `objects="SCV0:FUGR"` çağrısında `at="fugr"`
oluyor, muhafız **tutmuyordu**. Üstelik URL haritaları (`:873`, `:1350`) `"fugr"`yi de
kabul ettiği için obje **yine okunuyordu** ⇒ kusur **sessiz**: `coverage_complete` yine
`true`, `coverage_warning` **hiç basılmıyor**. Kaydın kendi orijinal vakası tam da
kapanmayan daldan geçiyordu.

**Why:** Sahte kapanış, gerçek açık kayıttan **daha zararlıdır** — sonraki tur onu otorite
sayıp o eksende hiç ölçüm yapmaz, ve failure-mode sessizce yaşamaya devam eder.
Yanlış "kapandı" ilanı, yanlış "açık" ilanının aksine **kendini göstermez**.

**How to apply:** Bir kapıyı/muhafızı "kapandı" yazmadan önce **girdi yollarını say**:
o fonksiyona kaç dal giriyor, normalizasyon/dönüşüm **hangi dalda** yapılıyor? Kapatan
commit'in dokunduğu dal ile **kaydın kendi vakasının geçtiği dal** aynı mı? Değilse
kapanış kısmidir — DURUM satırına niteleyiciyi yaz ("yalnız `package=` dalı"), gövdeye
değil. Fixture yazarken her girdi yolunu **ayrı vektör** yap; tek yolu test eden korpus
bu sınıfı yakalayamaz. İlgili: [[feedback_onay-da-bir-iddiadir-mekanizmayi-olcmeden-net-deme]] ·
[[feedback_kapsam-niteleyicisini-dusurme]] · [[feedback_bulgu-listesi-ornektir-sinif-duzeltmesi-tarama-ister]]
