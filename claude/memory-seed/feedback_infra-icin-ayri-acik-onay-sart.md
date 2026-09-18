---
name: feedback_infra-icin-ayri-acik-onay-sart
description: "Hook/validator/gate/paylaşılan araç işi — YARATMA ya da DEĞİŞTİRME — kullanıcıdan AYRI ve AÇIK onay ister; başka bir onayın içine gömülemez, lider infra'yı pas geçip kendisi de yapamaz"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 433b9a51-1855-4d19-afef-2da3c1c3376a
---

**KURAL (kullanıcı, 2026-08-19 — bağlayıcı):**

1. ⛔ **İnfra işi başlatmak için AYRI ve AÇIK onay şart.** Hook · validator · gate · pre-commit ·
   MCP script · `run_review` görev tanımı · paylaşılan `core/scripts` aracı — **yeni kurmak da,
   mevcudu değiştirmek de** buna dahildir.
2. ⛔ **Onay BAŞKA BİR ONAYIN İÇİNE GÖMÜLEMEZ.** *"Şu build'i başlat"* ya da *"şu bulguyu düzelt"*
   onayı infra iznini **kapsamaz**. İnfra için **ayrıca ve adıyla** sorulur.
3. ⛔ **Lider infra'yı PAS GEÇİP kendisi de yapamaz.** Özellikle **liderin ve ajanların çalışmasını
   organize eden / yönlendiren** dosyalar (hook, validator, gate, checklist, rules) — bunlara
   liderin doğrudan dokunması **engellenmeli**; gerekiyorsa yine **açık onay** istenir.

**Neden (kullanıcının gerekçesi):** *"bazen kendi karar vererek infra tetikliyorsun, gate/hook/
validator değişikliği yaptırmaya, yeni kurdurmaya çalışıyorsun. Bu sıkıntılı."*

⭐ **GENİŞLETİLDİ 2026-08-23 (kullanıcı): “proje işleri haricinde olan bişey başlatma”**

4. ⛔ **Proje işi olmayan hiçbir şey BAŞLATILMAZ — ÖNERİLMEZ de.** Kural yalnız infra
   değişikliğini değil, **proje dışı her tür turu** kapsar: tooling radar taraması, araç
   keşif turları, metodoloji bakımı, kuyruk temizliği. Bunlar bir hook önerse bile
   **lider kendiliğinden açmaz ve iş arasında kullanıcının önüne getirmez**; kullanıcı
   isterse kendisi ister.
   ⚠ *"Paralel koşar, çakışmaz, ucuz"* **gerekçe değildir** — mesele kaynak değil **odak**.
   ⚠ `SessionStart` hook'unun *"radar bayat, iş-arası öner"* hatırlatması bir **izin değildir**;
   hatırlatma önerme yükümlülüğü doğurmaz. Bayatlığı **sessizce** taşı.

**Vaka (2026-08-23):** lider `A-19` ajanını beklerken *"boş aralık"* diye tooling radarı önerdi.
Kullanıcı: *"proje işleri haricinde olan bişey başlatma"*. ⇒ Bekleme aralığı **doldurulacak
boşluk değildir**; beklemek meşru bir durumdur.

**Vaka (2026-08-19 — kuralın doğduğu gün):** lider aynı gün **iki** infra ajanını **sormadan** açtı.
- `infra-b13-curr` — meşru bir kusurdu (`populate_tables.py` CURR semantiği), ama yine de **izinsiz**.
- `infra-runreview-ddic` — `run_review`'da ENQU/indeks/SNRO görevi olmamasını *"doldurulacak boşluk"*
  sandı. Kullanıcı *"SNRO'ları hep ben yaptım"* deyince ölçüldü: **o boşluk iş bölümünün parmak
  iziydi**, doldurulmamalıydı. Ajan **iptal edildi**. ⇒ İzinsiz infra, yalnız yetki sorunu değil;
  **yanlış teşhisi kalıcı hâle getirme** riski.

**NASIL UYGULA — eylem-bazlı tetikleyici:**
> Bir `infra-expert` **spawn etmeden ÖNCE**, ya da `.claude/`/`hooks/`/`validators/`/`gates`/
> `run_review`/paylaşılan `core/scripts` altında bir dosyayı **değiştirmeden ÖNCE** → **DUR** →
> ne yapılacağını + neden gerektiğini + yapılmazsa ne olacağını yaz → **"infra için açık onay"**
> iste → **BEKLE**.

⚠ Bu kural, kuyruğa **kayıt açmayı** engellemez — `infra-findings.md`'ye bulgu yazmak serbesttir
ve teşviklidir. Engellenen şey **icra**: ajan açmak, dosya değiştirmek, gate kurmak.

[[feedback_yeni-gate-hook-uretimi-infra-expert]] · [[feedback_adt-infra-degisikligi-once-uyar-onay]] ·
[[feedback_arac-kod-fix-lider-isi]] · [[feedback_onay-isteme-formati]]
