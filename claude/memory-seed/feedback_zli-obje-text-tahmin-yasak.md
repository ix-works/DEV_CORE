---
name: feedback-zli-obje-text-tahmin-yasak
description: "Z'li obje text'lerini (description, label) AI TAHMİN ETMEZ — kanonik kaynaktan çıkar (<LEGACY_SOURCE> SEVKEMRI veya proje spec dosyaları)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7091c15c-424a-42a9-bcf8-7c3f51f36d33
---

Z'li (custom) SAP objelerinin metinlerini (description, field label, başlık) **AI HİÇBİR ŞEKİLDE TAHMİN ETMEZ**.

**Kanonik kaynaklar:**
1. **`<LEGACY_SOURCE> — Tablo alan listelerinde her DTEL/domain için "Anlamı" sütununda Türkçe metin var (kanonik).
2. **`<LEGACY_SOURCE> — Struct'lar — tabloda olmayan domain'ler için.
3. **`<LEGACY_SOURCE> — DTEL XML kaynakları (eski sistem) — 4 label (short/medium/long/heading) tam metni var.
4. Proje spec dosyaları: `ERP/<MODULE>/<PKG>/SPEC.md`, `MODULE_FS.md`, `DESIGN_DIFFERENCES.md`

**Önemli:** "DTEL metni = domain description" (kullanıcı bilgisi, 2026-05-14). Domain description ile DTEL field label'ları aynı semantic kaynaktan beslenir.

**Yapılması GEREKMEYEN:**
- Domain/DTEL adından (örn. `D_LPART`) anlam tahmin etmek ("Lojistik Partneri" gibi)
- DEPENDENCY_GRAPH'taki kategori başlığını description olarak almak ("Partner" gibi tek kelime — yetersiz)
- İngilizce alan adından Türkçe tahmin türetmek (DEParture PORT → "Kalkış Limanı" tahmini doğru olabilir ama kanonik kaynaktan teyit şart)

**Yapılması GEREKEN sıralı arama:**
1. Önce `ERP/<MODULE>/<PKG>/` altında spec/structure dosyaları — yeni sistem kanonik kaynağı
2. Sonra `<LEGACY_SOURCE> — domain'in geçtiği tablo dosyalarında "Anlamı" sütunu
3. Sonra `structures\` — struct dosyaları
4. Son çare `sources\ddic\dtel\` — DTEL XML
5. Hiçbiri yoksa **kullanıcıya sor** — AI tahmin etmez

**Why:** 2026-05-14 Sprint 1A başlatılırken AI 27 domain için description tahmini yaptı (D_LPART = "Lojistik Partneri", D_DELRES = "Teslimat Rezervasyonu", vb.). Kullanıcı uyardı: "txt tahmin etmemen gerek özellikle Z lilerde". <LEGACY_SOURCE> tablo dosyalarında kanonik karşılıklar bulundu, ~5 tahminden 3'ü yanlış çıktı (D_LPART = "Hat / shipping line", D_DELRES = "Gecikme sebebi"). Bu, ⛔ KATEGORİ D (Z'li obje TR text zorunluluğu) prensibinin doğrudan ihlali — yanlış text → ekran/rapor'da yanlış metinler.

**How to apply:** Z'li domain/DTEL/CDS/class/program yaratırken description/title/label gerekirse: önce kanonik kaynakları sırayla ara, bulunamazsa kullanıcıdan iste. ASLA tahmin yazma. Eğer obje hiç eski sistemde yoksa (yeni icat), kullanıcıdan TR description'ı al.

İlgili: [[feedback_legacy-draft-txt-files]], ADR 0005 KATEGORİ D
