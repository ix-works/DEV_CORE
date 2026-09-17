---
name: feedback_rap-validation-operation-trigger
description: "BDEF validation'daki create;/update; OPERASYON tetikleyicisidir — payload'da hangi alan olduğuna bakmaz; FE'den alan çıkarmak validation'ı susturmaz"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 53c98875-36cc-4508-8ced-628721bdc5ab
---

```abap
validation validateVehicleFields on save { field ContainerNo, TractorPlate, ContainerType; create; update; }
```
Buradaki `create;` / `update;` **OPERASYON** tetikleyicisidir: o operasyon olduğunda validation **her hâlükârda** koşar. `field ...` listesi tetikleyiciyi **daraltmaz**. Yani frontend UPDATE gövdesinden o alanları çıkarsa bile validation yine çalışır ve zorunluluk kontrolü yine reddeder.

**Vaka (2026-07-28, ZSD001 booking):** Kilitli bir kalemin 21 alanlık UPDATE gövdesinde tetikleyici alanların **hiçbiri yoktu**, validation yine RET verdi. İlk teşhisim ("FE'ye `ContainerType` alanını da kilit listesine ekle") **yanlıştı**; FE uzmanı ölçümle çürüttü — `aFields` listesinde `ContainerType` zaten yoktu.

**Why:** Sezgi "field listesi = tetikleyici filtresi" der; RAP'te değil. Bu yüzden "alanı payload'dan çıkar" tipi FE-only çözümler bu sınıfta **hiçbir zaman** çalışmaz — kök neden backend'dedir. [[feedback_ajan-olumsuz-donusu-kanitla-sorgula]]'nın tersi de doğru: ajanın **ölçümle çürüttüğü** teşhisimi savunmadan düzelttim.

**How to apply:** (1) Bir validation "olmaması gerektiği hâlde" tetikleniyorsa önce BDEF tetikleyicisini oku — `create;`/`update;` varsa cevap orada. (2) Muafiyet gerekiyorsa **behavior implementation içinde** ver (ör. kalem bazlı `CONTINUE`), FE'de değil. Muafiyeti **kalem seviyesinde** tut; belge seviyesine çıkarırsan denetim komşu kalemlere sızar. (3) Muafiyet ölçütünü ilgili CDS'ten canlı doğrulanmış bir alanla kur (varsayılan alan adı kullanma). (4) FE tarafında ek koruma isteniyorsa doğru desen **dirty-check**: değişmemiş kilitli kalem için UPDATE'i **hiç gönderme** — kanıt, kalemin `update_date`'inin değişmemesidir.
