---
name: feedback_classrun-teshis-yanlis-surum-ve-bayat-oturum
description: "adt_classrun bayatlığının İKİ yüzü: (1) 'does not implement' mesajı DOĞRUDUR (aktive edilmemiş VEYA bayat oturum; 'taze class adı' reçetesi YANLIŞ), (2) ⚠ HTTP 200 + dolu + akla yatkın çıktı da ESKİ kodun sonucu olabilir — inactive_objects=0 iken bile. Push sonrası TAZE oturumda koştur."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 598061c3-5f77-4639-8ca3-249a886c563a
---

**`adt_classrun` bozuk değildir.** `"Class does not implement if_oo_adt_classrun~main"`
mesajı geldiğinde mesaj **DOĞRUDUR** — sıraya göre şunlara bak:

1. **Sınıf AKTİVE EDİLMEMİŞ.** En sık sebep. Push edildi ama aktive edilmedi → aktif sürüm
   `adt_post_shell` boş kabuğu (≈192 bayt, arayüz yok). `adt_activate` çalıştır.
2. **Bayat oturum.** Obje **başka bir süreçte** aktive edildiyse (ör. `push_object.py`),
   MCP/istemci sürecinin tek uzun-ömürlü `stateful` oturumu aktivasyonu görmez ve eski
   class-load'a bağlı kalır. Çare **oturum RESET** (`new_session()` / `/mcp` restart) —
   **retry DEĞİL** (aynı oturumda retry ölçüldü, etkisiz).
3. Sınıf gerçekten arayüzü implemente etmiyordur.

⛔ **"TAZE (kullanılmamış) class adı ile yeniden yarat" reçetesi YANLIŞTIR.** İki kez denendi,
işe yaramadı, yalnız çöp obje bıraktı. Bu reçeteyi gördüğün yerde sil.

📌 **`adtcore:version="active"` TEK BAŞINA AKTİVASYON KANITI DEĞİLDİR** — create ile yaratılan
boş kabuk da "active" der. Güvenilir kanıt: **`adt_inactive_objects`** (0 olmalı).

**Why:** Kök sebep bir okuma hatasıydı — teşhis fonksiyonu (`_diagnose_classrun_binding`)
`source/main`'i **`version=` parametresi vermeden** GET ediyordu ve **ADT varsayılanı İNAKTİF
sürümdür**. Ölçüm: parametresiz 10.659 bayt (arayüz VAR) ↔ `version=active` 192 bayt (arayüz
YOK). Sınıf hiç aktive edilmemişken bile "yapısal olarak geçerli" diyordu; oradan "araç bozuk"
sonucu ve yanlış reçete doğuyordu. **Tek eksik parametre → 6 dokümana yanlış bilgi, 2 gereksiz
obje, saatlerce yanlış arama.**
⚠ **RECURRENCE (T4):** aynı yanlış sonuca **2026-06-30'da da varılmıştı** ve o gün de
düzeltilmişti ([[project_docu-f1-help-all-reports]] — *"BOZUK YANLIŞTI, bayat süreç, `/mcp`
reconnect"*). Cevap bir aydır hafızadaydı; 2026-07-30'da okunmadı ve üstüne yanlış sonuç
yazıldı. **Tanıdık bir semptomda önce hafızayı ara.**

## ⚠ VARYANT 2 (2026-08-19) — BAYATLIK **HATA VERMEDEN** DE GELİR

Yukarıdaki iki sebep **hata mesajı** üretir; bu varyant **üretmez.** `adt_classrun` push + activate
sonrası **HTTP 200 + dolu + akla yatkın** çıktı döndürdü — ama **eski kodun** davranışıydı (yeni
eklenen `c_docnum` sabiti sanki **boş**tu). **İkinci çağrı aynı bayat çıktıyı** verdi ⇒ tek seferlik
aksaklık değil.

📌 **Bu vaka yukarıdaki "güvenilir kanıt" hükmünü NİTELER:** `adt_inactive_objects` **count 0** idi ve
`source/main` = `?version=active` = `?version=inactive` **aynı sha** idi — yani **kaynak tarafı dört
yoldan temizdi** ve buna rağmen koşum bayattı. ⇒ `inactive_objects = 0` **aktivasyonu** kanıtlar,
**koşumun yeni kodu çalıştırdığını kanıtlamaz.** İkisi ayrı sorudur.

**Kanıt:** **taze oturumdan** (`SAPClient().run_classrun`, kendi süreç + yeni logon) aynı sınıf
**doğru** çalıştı.

**Tehlikesi:** *"araç OK dedi"* ailesinin en sinsi üyesi — `adt_transport_list` sahte-sıfır ve
`adt_post_shell` sahte-400'de araç **yanlış görünür**; burada **doğru görünür.** Vakada lider ajana
*"IDoc çıkmazsa dönüşüm kırıktır"* diye bir teşhis kısayolu vermişti; ajan şartı **körlemesine
uygulasa** "dönüşüm kırık" diye **yanlış BLOCKER** doğacak ve **çalışan kod bozulacaktı.** Ajan şartı
uygulamak yerine **ölçtü** — doğru davranış.

**Uygula:**
- Push/activate sonrası `adt_classrun` sonucu **tek başına kanıt değildir.** Ya **taze oturumda
  koştur** (`python -c "...; SAPClient().run_classrun(...)"`), ya çıktıyı **kaynakla çapraz kontrol
  et** (yeni koda özgü bir imza — yeni başlık satırı, yeni sabitin değeri — çıktıda görünüyor mu?).
- **"Beklediğim çıktı gelmedi ⇒ kod kırık" çıkarımını YAPMA.** Önce *"çalıştırdığım şey gerçekten yeni
  kod muydu?"*yu ölç.
- Ajana *"X çıkmazsa Y kırıktır"* biçiminde kısayol verirken **bayatlık olasılığını da yaz** — yoksa
  şart yanlış teşhisi kurumsallaştırır.

**How to apply:** Bir teşhis/analiz fonksiyonunun **çıktısına** dayanıp "araç bozuk" sonucuna
varmadan önce, **teşhisin kendisinin doğru veriyi okuduğunu kanıtla.** Yanlış veri okuyan bir
teşhis, güvenle yanlış bir reçete üretir ve o reçete "araç bozuk" sonucuna terfi eder.
Somut: sürüm-duyarlı bir uçta (`active`/`inactive`) **sürümü açıkça belirt**; varsayılanın ne
olduğunu ÖLÇ, varsayma.

İlgili: [[feedback_dogrulama-sezgileri-dort-kural]] · [[feedback_arac-basarisizligini-zararsiz-sayma]] ·
[[feedback_ajan-olumsuz-donusu-kanitla-sorgula]] · [[feedback_push-ok-mesaji-sahte-readback-esitligi]] ·
[[project_docu-f1-help-all-reports]] · [[feedback_resolved-tooling-bugs]] ·
[[feedback_exit0-degil-cikti-kaniti]]
