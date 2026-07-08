---
applies_to: [s4_private]
layer: L3
type: playbook
scope: project-wide
status: active
purpose: Geliştirme talebi alım protokolü — kapsam-sınıflama + 3-eksen araştırma + kanıtlı değerlendirme
---

# INTAKE TRIAGE GATE (ITG) — Geliştirme Talebi Alım Protokolü

> **Ne zaman:** Bir geliştirme talebi / revizyon / FS / Excel-ister / rapor isteği geldiğinde
> `intake_triage.py` hook'u bu protokolü ZORUNLU olarak enjekte eder (atlanamaz).
> **Amaç:** kapsamına orantılı, tutarlı (kişiden bağımsız), kanıtlı bir alım-süreci —
> hız/kaliteyi bozmadan. **Karar mimarisi (ADR 0022).**

> **🧭 ÇEKİRDEK İLKE:** Ajan her domain'i ezbere bilmez — beklenti bu DEĞİL. İş geldiğinde
> onu **sınıflar → isterlerden bilmesi gereken konuları çıkarır → hedefli araştırır →
> ancak bilgilendikten SONRA** değerlendirir + doğru soruları sorar + aksiyon alır. Hepsi
> kapsamla orantılı. **Persona = "act as X" DEĞİL** — yapılandırılmış kural-paketi
> aktivasyonu (hangi objeyi kontrol et, hangi soruyu sor, hangi kaynağı araştır).

---

## 6 ADIM

### 1. SINIFLA (modül + iş-tipi + KAPSAM) — gerekçeyle
Talebi üç eksende etiketle:
- **Fonksiyonel modül:** SD / MM / FI / … (hook kaba ipucu verir; kesin sınıfı SEN belirle).
  Modül kural-paketi varsa (`playbook/modules/<kod>.md`) OKU. Yoksa genel iskeletle ilerle.
- **İş-tipi:** rapor / RAP-servis / klasik-dialog / DDIC / UI / enhancement / … (skill_injector
  obje-tipi checklist'ini zaten enjekte eder — onu da izle).
- **KAPSAM (en kritik):** aşağıdaki 3 sınıftan biri — **gerekçesini bir cümleyle yaz**
  (kullanıcı görür, yanlışsa düzeltir). Kapsam, sonraki adımların AĞIRLIĞINI belirler.

| Sınıf | Nedir | Örnek | Akış ağırlığı |
|---|---|---|---|
| **S0 · nokta-düzeltme** | tek alan/label/mesaj/kozmetik; davranış değişmez | "şu kolon başlığı yanlış", "mesaj metni düzelt" | HAFİF: where-used → fix → bug-gate. **Soru yok, artefakt yok.** |
| **S1 · lokalize** | tek app/rapor/CDS içi davranış değişimi | "bu rapora X kolonu ekle", "bu ekranda hesap yanlış" | ORTA: kısa etki analizi + hedefli soru(lar) + fix + bug-gate. |
| **S2 · kapsamlı** | yeni program/çok-obje/cross-stack/yeni sprint | "yeni sipariş-kalem raporu", "yeni SE tipi" | TAM: aşağıdaki tam zincir + intake-artefaktı + mutabakat. |

> Sınır belirsizse bir üst sınıfa yuvarla değil — **en makul sınıfı gerekçele**, kullanıcı
> düzeltebilir. Over-triage (küçük işe ağır süreç) da anti-pattern'dir (hız ölür).

### 2. Modül kural-paketini OKU (varsa)
`playbook/modules/<modül>.md` = o modülün **tetik-haritası + kontrol-listesi + soru-şablonu +
kaynak-işaretçisi**. Bilgi-deposu değil — ajanı doğru kaynağa yönlendiren protokol. Domain-
olgusunu ezber sanma; paket "şuna bak, şunu araştır, şunu sor" der.

### 3. İSTERLERDEN KONU ÇIKAR
İsterleri/alanları tara — her anlamlı alan/gereksinim bir **domain-konusu** doğurabilir.
Bunları önden listelemek gerekmez; talebe bakarak türet. Örnekler:
- "kullanılabilir stok" alanı → **availability check / ATP** konusu
- "kredi durumu" → **credit management**
- "teslim tarihi/backorder" → **scheduling**
- "döviz/tutar" → **currency conversion**

Modül kural-paketinin TETİK-HARİTASI bu çıkarımı hızlandırır (örnek-tetikler orada).

### 4. 3-EKSEN ARAŞTIR (bilgilen — sonra değerlendir)
Her çıkan konu için, **hedefli ve ucuz** (kapsam-orantılı derinlik):

- **(a) Domain bilgisi** — nasıl çalışır? Kaynak: docs-MCP / resmi referans / LLM. Syntax
  ve annotation TAHMİN EDİLMEZ → resmi kaynaktan doğrula.
- **(b) CANLI sistem / ilişkili kod** — bu sistemde şu an ne var? `adt_where_used` +
  `adt_package_contents` ile **önce harita** çıkar, sonra *belirleyici* olanları `adt_get`
  ile derin oku. Sorular: ilgili CDS/class/tablo/rapor var mı → **reuse** mi yeni mi;
  kim tüketiyor → **blast-radius**; mevcut mantıkla **tutarlılık**. **Bu eksen aksiyonu
  DEĞİŞTİRİR** (süs bilgi değil — reuse/tutarlılık kararı buradan çıkar).
- **(c) Kurumsal hafıza / prior-art** — biz bunu/benzerini daha önce yaptık mı, ne öğrendik?
  Kaynak: memory + `playbook/lessons-learned.md` + paket `SESSION_NOTES.md`. İki değer:
  işi-tekrar-etme (deseni reuse et) + hatayı-tekrar-etme (dersi uygula).

> **⛔ KALİTE KİLİDİ (enine kesen, atlanamaz):**
> - **TAHMİN YASAK / kanıt-çıpası** (çekirdek davranış): her eksenin çıktısı kanıtlı olmalı;
>   kanıtsız hiçbir bulgu aksiyonu belirlemez. "activated/çalıştı dedi" ≠ kanıt.
> - **Z-obje hatırlanıyorsa CANLI DOĞRULA** (ADR 0016 source-drift / bayatlık): hafıza/prior-art
>   yazıldığı anki gerçeği taşır; Z objeleri değişir. **Hafıza = hipotez (nereye bak), canlı
>   sistem = otorite (ne var).** (c) ekseni bir Z-obje işaret ediyorsa (b) ile canlı-teyit ZORUNLU.
> - **Prior-art "sanırım yaptık" değil:** referansı bul + doğrula, yoksa "yok" say (yanlış-pozitif
>   kopyalamayı önler).

### 5. KANITLI DEĞERLENDİR
Domain + canlı-sistem + prior-art birlikte → aksiyonu belirle: reuse mı yeni mi ·
mevcutla tutarlılık · uygulanacak geçmiş-ders · blast-radius/risk. Kanıtsız ilerleme YOK.

### 6. KAPSAM-ORANTILI SORU + AKSİYON
- **S0:** soru yok — makul-default'la yap, tek satır "şöyle anladım, yapıyorum".
- **S1:** yalnız kritik/belirsiz noktayı sor (belirsizlik-kalibreli — makul-default'ta varsay-bildir).
  Soruyu, adım-4 araştırmasıyla **bilgilenmiş** sor (körlemesine değil).
- **S2:** intake-artefaktı üret (aşağıdaki şema) → EARS/INVEST DoR → kullanıcıyla **MUTABAKAT
  (sign-off)** → ancak sonra build. (Mevcut spec-mutabakat disiplini bu dala gömülüdür.)

### 7. Çıkışta: öğrenileni kaydet
İş bitince yeni ders/desen → mevcut **T1-T11 trigger + gün-sonu terfi** ile kalıcılaşır
(playbook/lessons + modül-paketi + memory). Döngü kapanır: girişte prior-art oku ↔ çıkışta yaz.

---

## S2 INTAKE ARTEFAKTI — sabit şema (determinizmin anahtarı)
Kullanıcı prompt/Excel/FS ne verirse versin, S2'de şu sabit-şemalı artefakta normalize et
(kişiden bağımsız tutarlılık; sonraki tüm adımların girdisi). Yer: paket `docs/` veya SESSION_NOTES entry.

```
# INTAKE — <kısa-ad>  (tarih)
- Modül / iş-tipi / KAPSAM: SD / rapor / S2  (gerekçe: ...)
- İstenen (özet):
- Çıkan domain-konuları: [konu → araştırma özeti (a/b/c eksen)]
- Etkilenen objeler (canlı-doğrulanmış): [obje → reuse/yeni/değişir → blast-radius]
- Prior-art: [bulundu: <ref> / yok]   ← ZORUNLU alan (aramayı mecbur kılar)
- Kabul kriterleri (EARS): "<olay> olduğunda sistem <sonuç> yapmalı" / "<durum> ise ..."
- Açık kararlar / riskler:
- MUTABAKAT: [ ] kullanıcı sign-off
```

**EARS kalıpları** (kabul kriteri): Event-driven ("kullanıcı VA01'de kaydettiğinde sistem X
yapmalı") · Unwanted ("miktar kapasiteyi aşarsa uyar") · State-driven ("... iken ...") ·
Ubiquitous. **INVEST/DoR:** her gereksinim test-edilebilir + kabul-kriterli olmadan build başlamaz.
Backend ve frontend ayrı DoR (BE/FE expert + ayrı bug-checklist).

---

## İlişkili
- Hook: [`../scripts/hooks/intake_triage.py`](../scripts/hooks/intake_triage.py) · obje-tipi kardeşi: `skill_injector.py`
- Modül paketleri: `playbook/modules/<modül>.md` (SD pilot — PR-B ile gelir)
- Çekirdek davranış (tahmin-yasak) + ADR 0016 (source-drift) + ADR 0006 (reviewer) + ADR 0019 (gate coverage)
- Karar: [`../governance/decisions/0022-intake-triage-gate.md`](../governance/decisions/0022-intake-triage-gate.md)
