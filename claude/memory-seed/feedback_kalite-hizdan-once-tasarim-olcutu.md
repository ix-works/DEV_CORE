---
name: kalite-hizdan-once-tasarim-olcutu
description: "Süreç/ajan/kontrol tasarımında kalite > hız — hızlanma kalite kaybıyla alınmaz; kararlar kanıtlı bulguya dayanır, tahminle ilerlenmez"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 8865df6b-2e94-44e8-8952-84b42fc53742
  modified: 2026-10-18T09:15:47.927Z
---

Ajan/kontrol/süreç değişikliği tasarlarken **öncelik kalitedir** (ajanın işini en doğru şekilde yapması); hız ancak kaliteden ödün vermeden kazanılır. Tasarım girdisi olan her bulgu (araştırma raporu, vaka sayımı) **kaynağından doğrulanmadan** karar dayanağı yapılmaz.

**Why:** Kullanıcı 2026-10-18 (bug-expert / checklist yeniden kurgusu konuşulurken): *"hızlanmak için kaliteden vazgeçemeyiz, kalite yani ajanın yaptığı işi en doğru şekilde yapması daha önemli"* ve araştırma ajanlarının vaka listeleri için *"kanıtlı olması gerek, kanıtlamadan emin olmadan tahmin ile ilerlemeyelim"*. Daha önce performans kaygısını da ayrıca vurgulamıştı ("çok aşırı yavaşlatmaması gerek") — iki ölçüt çelişirse kalite kazanır.

**How to apply:**
- Hız önerisi (paralelleştirme, süzülmüş checklist, tek program) sunarken her birinin **kaliteyi düşürmediğini** ayrıca göster (ör. süzülen maddenin neden ilgisiz olduğu kanıtlı olmalı; kaçırma riski açıkça yazılır).
- Araştırma ajanı raporu = kaynak gösterilmiş iddia; tasarıma girmeden önce bağımsız doğrulama turu (kaynak var mı · kural olaydan önce mi · sınıf doğru mu · maliyet yazılı mı).
- Lider kendi yazdığı düzeltmeyi kendi testiyle kapatmaz; bağımsız delta kapısı.

Son-doğrulama: 2026-10-18 · Applies-to: tüm projeler, ajan/kontrol/süreç tasarımı
İlgili: [[performans-onerisi-de-bir-iddiadir-maliyeti-once-olc]] · [[ajan-bulgusu-dogru-mekanizmasi-yanlis]]
