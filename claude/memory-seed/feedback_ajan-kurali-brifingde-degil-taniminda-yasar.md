---
name: feedback_ajan-kurali-brifingde-degil-taniminda-yasar
description: "Her yeni ajanın tekrarladığı bir hata varsa kural brifingde değil ajan TANIMINDA eksiktir — brifing uçucu, tanım kalıcıdır"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 276c51e4-6137-42af-afb9-b43b2613eac7
---

Bir davranış kuralını spawn brifingine yazmak onu **o tur için** kurar; sonraki ajan
brifingi görmez. Aynı hatayı **birden fazla ajan** yapıyorsa çözüm brifingi zenginleştirmek
değil, kuralı `claude/agents/<rol>.md` tanımına damgalamaktır (META-İNFRA ⇒ yalnız lider).

**Ölçülmüş vaka (2026-09-03/04):** Otonom gece turunda ajanlar `cd <dizin> && grep -r …`
biçiminde komutlar yazdı. İzin sınıflandırıcı, dizin değiştiren komutta hangi dosyaya
dokunulacağını **statik çözemediği** için fail-closed davranıp kullanıcıya onay sorusu
çıkardı — kullanıcı ekranda olmadığı için tur **durdu**. Kuralı altı denetim ajanına ve
yedi fix ajanının brifingine tek tek yaydım; buna rağmen sonraki turda **yine ihlal edildi**.
Ölçüm: kural `claude/` altında **0 kalıcı satırda** yazılıydı. DEV_CORE #195 ile
`infra-expert.md`'ye damgalandıktan sonra yeni ajanlar onu tanımdan aldı.

**Why:** Brifing, ajanın **o seferki** bağlamıdır ve tur bitince kaybolur; tanım her
spawn'da yüklenir. Aynı hatanın iki kez tekrarı, kuralın yanlış katmanda yaşadığının
kanıtıdır — üçüncü tekrarı beklemeye gerek yok.

**How to apply:** Bir ajan hatası ikinci kez göründüğünde sor: *"bu kural kalıcı olarak
nerede yazılı?"* — `grep` ile ölç. **0 eşleşme** çıkarsa brifingi düzeltmekle yetinme,
tanıma yaz. Yazarken **gerekçeyi de yaz** (neden bu biçim, hangi mekanizma tetikleniyor):
gerekçesiz kural bir sonraki turda "gereksiz katılık" diye gevşetilir. ⛔ Kuralı yazarken
korumayı gevşetme yönüne kayma: yukarıdaki vakada doğru çözüm **komut biçimini**
değiştirmekti, `deny` kurallarını (`.env*`, `credentials*`, `.ssh/**`, `.aws/**`)
gevşetmek değil — koruma gerçekti. İlgili: [[feedback_kural-gate-lenmeli-yoksa-anlamsiz]] ·
[[feedback_agent-briefing-sendmessage-main]] · [[feedback_auto-mode-deny-kararsiz-yeniden-dene]]
