---
name: feedback_karar-sormadan-once-erisilebilirlik-olc
description: "Bir bulguyu kullanıcı kararına çevirmeden önce arıza yolunun ERİŞİLEBİLİR olduğunu ölç — statik olarak doğru bir bulgu, ulaşılamaz bir dalda ise karar sorusu değildir"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 135c882f-c5bd-4a31-994f-f5aa4f3fd199
---

**KURAL:** Bir kapı/ajan bulgusunu **kullanıcıya karar sorusu** olarak getirmeden önce, arızanın
oluştuğu **kod yolunun çalışma-zamanında ERİŞİLEBİLİR olduğunu ÖLÇ.** Statik olarak doğru bir
bulgu, **ulaşılamaz** bir dalda duruyorsa bir karar değil, en fazla bir temizlik notudur.

**Ölçülmüş vaka (2026-08-22, ZSD001 `A-13`):** Bug gate `M1` verdi — mesaj `177`
(*"… &4 günlük eşik aşıldı."*) eşik tanımsızken `&4`'ü boş bırakıyor ⇒ *"var olmayan bir eşiğin
aşıldığı"* iddia ediliyor. **Statik analiz doğruydu.** Lider bunu kullanıcıya **üç seçenekli
karar sorusu** olarak getirdi, kullanıcı karar verdi, düzeltme koşuldu.

**Re-gate erişilebilirliği ölçtü ve dal ÖLÜ çıktı:** `ZCL_SD022_LOG:1017` — `BEYAN_YAS_GUN`
`read_params`'ın **zorunlu alan listesinde**; boşsa `ev_ok=false` → `get_param` `:1053`'te erken
`RETURN` → `send_daily_summary` maili **hiç göndermeden** döner. ⇒ `lv_esik_var = abap_false`
dalına **hiçbir veri giremez**; `M1`'in arıza senaryosu **oluşamaz**.

**Bedel:** Zarar yok (düzeltme zararsız, hatta gereksiz bir dalı temizledi) ama **kullanıcının
karar bütçesi** oluşamayacak bir senaryoya harcandı. Üstelik aynı turda yazılan yorum
*"operatör `053` uyarısından öğrenir"* diyordu — o kanal da ölçüldü: `053` `ct_msg`'e gider,
mail gövdesi `lt_body_msg`'ten üretilir, **ters yön yok** ve günlük özetin kullanıcı yüzü yoktur
⇒ iddia **iki kez** yanlıştı.

**NASIL UYGULA:**
1. Bulgu → karar sorusu **dönüşümünden ÖNCE** tek soru: *"bu dala hangi veri/koşulla girilir ve
   o koşul bugün oluşabilir mi?"* Cevap ölçümle verilir — çağıran zinciri yukarı doğru izle
   (guard, erken `RETURN`, zorunlu-alan kapısı, `IF` kapsayıcısı).
2. Ulaşılamazsa: **karar sorusu değildir.** Ya "ölü savunma dalı" diye işaretle, ya sessiz
   temizliğe bırak — kullanıcıya götürme.
3. ⛔ **Ulaşılamazlık da bir iddiadır** — o da ölçülür. Bugün ölü olan dal, bir guard
   gevşetilince canlanır ⇒ işaretlemeyi *"bugün `<şu guard>` yüzünden ulaşılamaz"* diye
   **guard'ın adıyla** yaz, yoksa bakımda sessizce yanlış yönlendirir.
4. Kapıya bunu **isteyerek** yaptır: *"bulgunun arıza yolu erişilebilir mi — çağıran zinciri
   ölç"* brifing maddesi olsun. Kapı 1 statik doğruydu ama erişilebilirliği ölçmemişti.

⚠ Bunun tersi de tuzaktır: *"hiç ateşlenmemiş"* ile *"ateşlenemez"* **aynı şey değildir** —
birincisi latent kusurdur ([[feedback_kod-yolu-vardi-veri-gecmemisti]]), ikincisi ölü koddur.
Ayrım **guard var mı** sorusuyla yapılır, sıklıkla değil.

[[feedback_dogrula-once-flag-spekulatif-blocker-yasak]] · [[feedback_yesil-sinyalin-kapsamini-sor]] ·
[[feedback_kontrolun-kapsami-is-akisinin-seklinE-bagli]] · [[feedback_sorulari-tek-tek-sor-oneriyle]]
