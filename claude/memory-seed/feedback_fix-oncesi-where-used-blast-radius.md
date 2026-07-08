---
name: feedback_fix-oncesi-where-used-blast-radius
description: "Her düzeltme öncesi değişen obje/programın where-used + blast-radius'unu analiz et; başka yerde kullanılıyorsa orada da problem var mı kontrol et"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 1420ec34-9257-4b0a-aef4-aee509c5b810
---

Bir düzeltme/değişiklik uygularken, değişeceğin obje/program/CDS/VH/class'ın **başka yerlerde kullanılıp kullanılmadığını** ve değişikliğin **etkilerini (blast-radius)** İYİ analiz et — sonra uygula. Başka yerde de kullanılıyorsa, **o kullanımda da problem var mı / değişiklik orayı bozar mı** kontrol et.

**Why:** Bu projedeki VH'ler (generic `ZSD000_I_*`), wrapper view'lar, ortak class'lar (ZSD000_CL_*) ve plumbing **çok yerde paylaşılır**. Tek bir raporu düzeltirken paylaşılan objeyi değiştirmek sessizce başka app'i bozabilir; ya da aynı bug zaten başka app'te de vardır (tek yeri düzeltmek eksik kalır). Kullanıcı kuralı (2026-06-22, konteyner raporu VH bug'ı bağlamında).

**How to apply:** Düzeltmeden ÖNCE → (a) `adt_where_used` / Grep ile objenin tüm tüketicilerini çıkar; (b) değişikliğin additive mi breaking mi olduğunu belirle (paylaşılan objede breaking = DUR, app-spesifik çözüm ara); (c) paylaşılan obje değişiyorsa diğer tüketicilerde regresyon kontrolü yap; (d) aynı kök-sebep diğer tüketicilerde de varsa kullanıcıya bildir (tek-yer-düzelt eksik). İlgili: [[feedback_bpname-customer-vendor-sweep]] tarzı paylaşılan-anti-pattern temizliği; UI plumbing reuse [[feedback_ui5-v2-plumbing-reuse-traps]].
