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
- **CORE/worktree'ye yazan roller:** kimlik izini (müşteri adı · sistem-ID · gerçek repo adı ·
  SAP kullanıcı adı) **BAŞTAN placeholder yaz** (`<PROJECT_NAME>`, `<SYS>`, `<SAP_USER>`, ZSD001).
  GENERICIZE-LEAK guard'ı içeriği **üretim BİTTİKTEN sonra** değerlendirir → bedeli düzeltme
  değil, dosyanın **TAM yeniden-üretimidir** (ölçüldü 2026-08-13: 19,5 KB rapor ≈ 140 sn +
  10 KB fixture ≈ 69 sn çöp). Sonradan temizlemeyi planlama; ilk yazımda placeholder kullan.

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

## 9. ENGELLENİRSEN — ZORUNLU MADDE (⛔ yazma işi veren her brifte)
> **Şu satır brife AYNEN girer (ajanın charter'ı bunu tekrarlamaz — brif söylemek zorundadır):**
>
> *"Yazacak yerin yoksa, bir yasakla çakışıyorsan, araç yüzeyin yetmiyorsa ya da bir kalem
> sana yanlış geliyorsa: **TAHMİN ETME, BEKLEME** → **DERHAL `SendMessage(to:"main")`**.
> Sessiz bekleme bu ekipte kusurdur."*

- ⭐ **NEDEN ZORUNLU (ölçülmüş vaka, 2026-08-19):** bir infra ajanı `isolation:"worktree"` ile
  açıldı; worktree **bulunulan projenin** açıldı, iş ise **başka repodaydı** ⇒ ajanın charter'ı
  canlı ağaca yazmayı yasakladığı için **yazacak hiçbir yeri yoktu**. Yasağa uydu, bekledi,
  **haber vermedi**: **26 dakika ölçülebilir çıktı SIFIR**. ⚠ Watchdog *"heartbeat 17s taze"*
  diyordu — çünkü heartbeat **canlılık** ölçer, **ilerleme** ölçmez. Doğru adres brife
  yazılınca aynı iş **~8 dakikada** bitti. Ajanın davranışı şablon açısından **kusursuzdu**;
  kusur **brifteydi**.
- **Çok-repolu işte worktree'yi LİDER açar** ve adresini brife YAZAR:
  `git worktree add -b wip/<konu> <dizin> origin/<dal>` → ajan `git push origin HEAD:<PR-dalı>`.
  ⚠ Aynı dal canlı ağaçta checkout ise git ikinci worktree'ye izin vermez.
- **İstediğin her eylemin ajanın `tools:` listesinde olduğunu ÖLÇ** (aynı gün üç vaka: salt-okur
  role rapor DOSYASI yazdırmak · `SendMessage`'ı olmayan rolden heartbeat istemek).
- ⓘ Bu maddenin varlığını `brifing-lint` denetler — ama yalnız **başka bir ağaca yazma işi
  veren** briflerde (ölçüm: 587 gerçek brif · dar eksen %18,4'ünü kapsıyor, ham "madde var mı"
  kontrolü %86,7 ateşleyip uyarı körlüğü üretirdi).
