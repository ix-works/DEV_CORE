# SPAWN-BRİFİNG ŞABLONU (R2 — denetim 2026-07-31; Anthropic 4-alan deseni + TD ekleri)

> **Kullanım:** Lider her `Agent(...)` spawn'ından önce bu şablonu DOLDURUR ve prompt olarak
> gönderir. "Yalnız İLGİLİ bölümleri doldur" — körü körüne tam kopya brifi şişirir (hedef
> taban ≤2 KB). Alt-ajan parent geçmişini GÖRMEZ (resmî) → bilmesi gereken her şey burada.
> Kanonik ev BURASI; CLAUDE.core.md §1.1 ve operating-model yalnız ATIF verir.

---

## 1. GÖREV (objective — tek paragraf, belirsizlik yok)
<ne yapılacak + bitti-tanımı (DoD): hangi çıktı, hangi kapsamda>

## 2. GÖREV SINIRLARI (task boundaries — scope-creep freni)
- KAPSAM İÇİ: <...>
- KAPSAM DIŞI: <"şunu da düzelteyim" YOK; bulursan RAPORLA, dokunma>
- Model: <X — rol×kapsam matrisi satırı (operating-model §6); beyan≠fiilî, transcript kanıt>

## 3. ÇIKTI FORMATI (output format)
- Final mesaj = SendMessage({to:"main"}) raporu; şekli: <madde listesi / tablo / diff / dosya-yolu>
- Büyük çıktıyı scratch/dosyaya YAZ, mesajda yolunu ver (mesaj-şişirme yok).

## 4. ARAÇ/KAYNAK KILAVUZU (tool guidance)
- Kullan: <öncelikli araçlar/dosyalar>; `path=core/` kuralı: kökten Grep core'u GÖRMEZ (D29).
- OKU (işe başlamadan): <ilgili playbook/checklist yolları — yalnız gerekli olanlar>
- Efor ölçeği: basit iş ≈ 3-10 araç çağrısı; kapsamlı iş için alt-hedeflere böl.

## 5. HAZIR-BAĞLAM (P6 — liderin zaten bildiği; ajan yeniden KEŞFETMESİN)
<dosya yolları + ilgili satır bölgeleri + kısa alıntılar/özet kararlar. SAP-kaynakları için
taze-oku kuralı GEÇERLİ KALIR — hazır-bağlam yalnız değişmeyen referanslar için.>

## 5b. PLAN-ARTIFACT (yalnız çok-adımlı geri-alınamaz zincirlerde)
<plan dosyası: .tmp/plan-<konu>.md — bu brif o planın hangi adımını kapsıyor: adım N/M>

## 6. GÖREVE-İLİŞKİN DERSLER (R3 — memory köprüsü; ZORUNLU alan)
<MEMORY.md'de görev anahtar-kelimeleriyle tarama → eşleşen 2-5 dersin ÖZÜ (kuralın kendisi,
1-2 satır; dosya adı değil). Eşleşme yoksa AÇIKÇA yaz: "ilgili ders bulunamadı" — boş bırakma.>

## 7. KANIT KURALLARI (değişmez blok — her brife girer)
- TAHMİN YASAK — kanıtla hareket et; emin değilsen DUR ve RAPORLA.
- "bulunamadı ≠ yok" · "çalıştı mesajı ≠ çalıştı" — canlı/ikincil kanıt ara.
- Kanıtsız iddia RAPORA YAZILMAZ; sayı verirken içerik-çapası kullan (satır-no tek başına değil).
- Bağımsız OKUMA çağrılarını tek turda PARALEL gönder; yazma/sıra-bağımlı seri (P6).
- Ara ürünleri DİSKE YAZ (login-expiry/kopma = yazılmamış iş kaybı; vaka #50).

## 8. HEARTBEAT / İLETİŞİM
- Uzun işte her doğal kilometre-taşında 2-3 satır SendMessage({to:"main"}) ("yaptım/sırada/açık-nokta").
- "YAPILAMAZ" demeden önce: repo'da alternatif yol ara + denediklerini kanıtla (kanıtsız olumsuz rapor sorgulanır).
