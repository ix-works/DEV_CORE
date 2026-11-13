---
name: feedback-zli-obje-text-tahmin-yasak
description: "Z'li obje text'leri (description, label): AI ÖNERİR ve onaya sunar (kullanıcı 2026-09-02) — ama önce kanonik kaynağı arar ve türetimini kalem kalem gösterir; yasak olan SESSİZCE UYDURMAK, öneri üretmek değil"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7091c15c-424a-42a9-bcf8-7c3f51f36d33
---

## ⭐ GÜNCEL USUL (kullanıcı, 2026-09-02) — **AI ÖNERİR, KULLANICI ONAYLAR**

> **Tohum notu (2026-11-12):** bu dersin önceki tohum hâli *"AI HİÇBİR ŞEKİLDE TAHMİN ETMEZ —
> bulunamazsa kullanıcıdan iste"* diyordu. Kural 2026-09-02'de kullanıcı tarafından **esnetildi**;
> eski hâli bu sürümle geçersizdir.

Kullanıcının kendi sözleri: *"aslında AI metin önerir ve onay ister, ben istersem değiştiririm."*
Aynı gün bir emsal kararla uygulandı (iki Z objesinin — bir fonksiyon grubu ve bir IDoc giriş
FM'i — kısa metinleri öneri + onayla yazıldı).

⇒ **Esnetilen:** *"AI öneri üretmez"*. ⇒ **Esnetilmeyen — kuralın asıl derdi:** *"AI sessizce
uydurur"*. Öneri sunmak serbesttir; **türetimi göstermeden** metin yazmak değildir.

**Öneri sunarken zorunlu adımlar:**
1. **Önce kanonik kaynağı ara** (aşağıdaki sıra). Bulunduysa öneri değil **alıntı** yap.
2. **Türetimi kalem kalem göster** — hangi belge, hangi satır, hangi ev emsali (kardeş objenin
   üslubu). Kaynaksız öneri, kılık değiştirmiş tahmindir.
3. ⭐ **Alan uzunluğunu ÖNERİDEN ÖNCE ölç** (canlı `DD03L`). Sığmayan metin **sessizce kırpılır**;
   emsal turda `TLIBT-AREAT` CHAR 40 / `TFTIT-STEXT` CHAR 74 ölçülmeseydi kusur readback'e kadar
   görünmezdi. Yazımdan sonra readback'te **kod-noktası** kıyası yap (mojibake: `ş` U+015F · `ı` U+0131).
4. Onayı **kalıcı bir provenance belgesine** yaz (`docs/METIN-ONAY-EK-<tarih>.md` kalıbı).
   📌 Metni kanonik yapan şey **öneri değil, onaydır**.

⚠ **İstisna — şu hâlâ kullanıcınındır:** yeni bir **iş kavramının** görünen adı/durum metni
(ör. bir durumun *"belirlenemedi"* karşılığı) ölçümle türetilemez; orada öneri sunulur ama
**kullanıcı belirler**. `ADR 0005-D`'nin 4 field label (short/medium/long/heading) TAM yazılma
zorunluluğu **aynen** durur.

---

## Kanonik kaynak sırası (öneri üretmeden ÖNCE)

1. Proje spec dosyaları: `<source_root>/<MODULE>/<PKG>/` altında `SPEC.md`, `*_FS.md`, ad/metin onay
   listeleri, `DESIGN_DIFFERENCES.md` — **yeni sistemin kanonik kaynağı**
2. **Ev emsali:** kardeş objenin canlı kısa metni (üslup birliği için — emsal turda kardeş FUGR'ın
   kısa metninin üslubu alındı)
3. Projede bir legacy/eski sistem kaynağı **tanımlı ve erişilebilirse** oradaki DDIC metinleri
   (tablo alan listelerindeki "Anlamı" sütunu, DTEL 4 label) — kök iptal edildiyse bu adım atlanır
4. Hiçbiri yoksa → **öneri üret, türetimi göster, onaya sun**

**Önemli:** *"DTEL metni = domain description"* (kullanıcı bilgisi, 2026-05-14). Domain description
ile DTEL field label'ları aynı semantik kaynaktan beslenir.

**Yine de YASAK olanlar:**
- Domain/DTEL **adından** anlam uydurup kaynak göstermemek (`<DOMAIN_A>` → *"Lojistik Partneri"*)
- DEPENDENCY_GRAPH kategori başlığını description sanmak (tek kelime — yetersiz)
- İngilizce alan adından TR türetip **teyit etmemek**

**Why — ölçülmüş vaka, 2026-05-14:** AI 27 domain için description **tahmin etti**, kaynak
göstermedi. Kullanıcı: *"txt tahmin etmemen gerek özellikle Z lilerde."* Kanonik karşılıklar
bulununca ~5 tahminden **3'ü yanlış** çıktı (`<DOMAIN_A>` = *"Hat / shipping line"*, `<DOMAIN_B>` =
*"Gecikme sebebi"*). Yanlış text → ekranda/raporda yanlış metin, **sessiz** hata.
⇒ Vakayı kötü yapan **öneri sunmak değildi**; kaynaksız ve onaysız **yazmaktı**. 2026-09-02
güncellemesi bu ayrımı netleştirir.

İlgili: [[feedback_legacy-draft-txt-files]] · [[feedback_onay-isteme-formati]] ·
[[feedback_capayi-ada-cevirmek-de-bir-olcumdur]] · ADR 0005 KATEGORİ D
