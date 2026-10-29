---
name: feedback_yeni-gelistirmede-ts-builddan-once-yazilir
description: "Yeni geliştirmede sıra FS onayı → TS → build'dir; 'doküman donmuş kod ister' dersi TS'i build sonrasına ERTELEMEZ. Build brifinde TS yoksa brif eksiktir. TS'i kodlayan ajan yazmaz."
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: bae16578-3da1-492d-bdf1-1b485f1ef5d8
  modified: 2026-10-29T00:00:00.000Z
---

**KURAL:** Yeni bir geliştirmede (yeni ekran/pencere/rapor işlevi) sıra **FS onayı → TS →
build → bug-gate → SAP yazımı**dır. TS, geliştiricinin "satır-1'den önce neyi bilmem gerekir"
sorusunu cevaplayan **tasarım** belgesidir (`core/standards/04-documentation-fs-ts.md` §3.0;
`core/playbook/howto-belge-canli-teyit-turu.md`: "TS mutabakatından SONRA, build kapısından ÖNCE").
Build brifi TS yolunu ve sürümünü taşır; TS yoksa brif **eksiktir**. Önce TS yazdırılır.

**Why:** Vaka (bir projede, 2026-10-28; yeni bir maliyet penceresi, FS onaylı): lider build
ajanının brifine "kod DONDUKTAN sonra TS hizalaması" yazdı; ajan TS'siz kodladı. Kullanıcı sordu:
*"ts i yazmadan mı kodlamaya geçti anlamadım"* → *"bundan sonra bu şekilde olmamasını nasıl
sağlarız"*. Kök neden: [[feedback_dokuman-turu-donmus-kod-ister-paralel-kosturma]] dersi
**kapsamı dışında** uygulandı. O ders, düzeltme turu uçuştayken koşan **sonradan-belge**
turları (KD, ekran görüntüsü, PDF, TS hizalaması) içindir; yeni build'in **tasarım TS'i**
için değil. Kural standartta zaten yazılıydı — eksik olan, brif yazılırken sıranın sorulmasıydı.
Sonuç: SAP'ye yazım yoktu, kod yerelde kaldı; telafi = SAP yazımından önce TS yazılıp kodla
birlikte bug-gate'e verildi (kod TS'e uymazsa TS'e göre düzeltilir).

**TS YAZARI ≠ KODLAYAN (kullanıcı kuralı 2026-10-28):** *"TS'i yeni bir bağlam ve context ile
yazması gerek, kodlamadan etkilenmeden."* TS, kodu yazan ajana yazdırılmaz; taze bağlamlı ayrı
bir ajan FS + mevcut (değişiklik öncesi) kod + canlı sistemden yazar. Kodlayan ajanın TS'i,
yazdığı kodu belgeler — tasarımı değil; kodun TS'e uyup uymadığını ölçmenin anlamı kalmaz.

**How to apply:**
- TS ajanı ile build ajanı **ayrı spawn**dır; TS ajanına yeni kodun dosyaları/diff'i verilmez.
- Build ajanı spawn etmeden önce sor: **bu işin TS'i var mı ve FS'in son sürümüne hizalı mı?**
  Değilse önce TS turu (ayrı ajan), sonra build.
- Brifte TS'i **girdi** olarak ver (yol + sürüm). "Kod bitince TS'i hizala" cümlesi yalnız
  build sırasında küçük sapmaların TS'e geri yazılması içindir; TS'in kendisinin yerini tutmaz.
- "Donmuş kod" dersini yalnız **build sonrası** belge turlarına uygula.

Yapısal önlem (ajan tanımına "TS yoksa DUR" + brif şablonuna TS girdisi satırı) önerildi;
kullanıcı 2026-10-28: *"buna gerek yok şimdilik"* — önlem bu ders + lider disiplinidir.
Nüks ederse yapısal önlem yeniden önerilir.

Son-doğrulama: 2026-10-29
Applies-to: yeni geliştirme/genişletme (klasik ALV, Dynpro, RAP, UI) — FS'i olan her build; tüm profiller
prior-art: bulundu `core/standards/04-documentation-fs-ts.md` §3.0 + `core/playbook/howto-belge-canli-teyit-turu.md` (kural yazılı; brif şablonunda TS girdisi satırı yok — `core/claude/templates/spawn-brief.md` taraması 0 eşleşme)
