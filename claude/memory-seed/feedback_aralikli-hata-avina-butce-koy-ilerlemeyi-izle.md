---
name: aralikli-hata-avina-butce-koy-ilerlemeyi-izle
description: "Aralıklı (flaky) yarış/hata avını ajana verirken deneme/süre bütçesi koy; bekçi yalnız takılmayı görür, \"ilerleme yok ama koşuyor\" durumunu lider kendisi izler"
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

Bir rapordaki aralıklı UI yarışını ("bağlama dolu, tablo boş") alt ajana kapsam olarak verdim ve süre ya da deneme sınırı koymadım. Ajan saatlerce aynı yarışı canlı açılışla saydı. Ara notlar erkenden şunu söylüyordu: hata nadir (3 denemede 1), kendiliğinden düzelebiliyor, kod kusuru kanıtlanamıyor. Ben ise yalnız takılma bekçisine (`agent_stall_watch`) bakıyordum. Kullanıcı durumu fark edip sordu: "neden bu kadar bekledin".

**Why:** Takılma bekçisi yalnız asılı kalan ya da onay bekleyen ajanı yakalar. Koşmaya devam eden ama karara yaklaşmayan ajanı görmez. Üstelik her yeni ölçüm "biraz daha veri" gibi görünür; kendiliğinden durmaz.

**How to apply:**
- Aralıklı hata ya da yarış avı brifine baştan bütçe yaz. Örnek: "en çok N deneme / X dk. Kök neden bulunmazsa dur, bilinen kısıt olarak raporla."
- Uzun koşan ajanın ara notlarını lider kendisi aralıkla okur. Okurken şunu sorar: "son ölçüm kararı değiştirdi mi?". Cevap hayırsa ölçümü keser.
- Kendi kodumuzun kusuru kanıtlanamayan, nadir ve kendiliğinden düzelen bir hata kullanıcı testini bekletmez. Bilinen kısıt olarak yazılır, kullanıcı testine gidilir.

Son-doğrulama: 2026-11-15 · Applies-to: alt-ajanla canlı ölçüm/teşhis turları (UI5 yarışları dahil)
İlgili: [[agent-stall-watchdog-mekanizmasi]] · [[performans-onerisi-de-bir-iddiadir-maliyeti-once-olc]]
