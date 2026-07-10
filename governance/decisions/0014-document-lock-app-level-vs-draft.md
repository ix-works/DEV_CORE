# 14. Belge Kilidi: App-Level Kilit Tablosu (Draft yerine, bilinçli istisna)

Tarih: 2026-06-10
Durum: Kabul edildi

## Bağlam

RAP managed BO'larında (ZSD001 sevk emri, ZSD001 sipariş) kullanıcı belgeyi
**Değiştir** ile açtığında **VA02-tarzı** davranış isteniyor: "açarken kilit var mı
bak; yoksa kilitle; başkası tutuyorsa 'X düzenliyor' de; silmeden önce de kontrol et."

Mevcut durum: managed BO + `lock master` + `etag master LastChangedAt` → **optimistic
(ETag)** koruma var (ikinci kaydeden 412 alır, veri bozulmaz), ama **stateless OData'da
open→save arası kalıcı kilit YOK** (her request ayrı; lock sadece save LUW'unda tutulur).

### Değerlendirilen seçenekler

1. **Sadece ETag (RAP default).** Veri güvende ama open'da "X düzenliyor" uyarısı yok
   (çakışma sadece save'de görülür). Yetersiz — istenen UX bu değil.
2. **Klasik ENQUEUE'i request'ler arası tutmak.** Stateless'te ÇALIŞMAZ (lock her
   request sonunda düşer) — anti-pattern.
3. **Draft (`with draft` + `lock master total etag`).** RAP'ın **best practice**'i:
   framework-managed exclusive lock + "kaldığın yerden devam". **AMA** asıl Fiori
   Elements + OData V4 dünyasının özelliği. Bizim **freestyle UI5 + OData V2** +
   **draft'sız pilot** (standards/05) bağlamımızda: Edit/Activate/Discard yaşam
   döngüsü + `IsActiveEntity` anahtarı + 3 controller + List = **ciddi rework**, üstelik
   pilot kararını ZSD001 dahil tersine çevirir.
4. **App-level kilit tablosu (DB satırı) + timeout.** Stateless'te çalışır (commit'li
   satır tüm request'lere görünür), VA02 UX'ini verir, freestyle'a uyar.

Kullanıcı ile "kaldığın yerden devam" (draft'ın asıl ek değeri) **değerli bulunmadı** →
draft'ın ana cazibesi düştü.

## Karar

**Seçenek 4 — ortak app-level kilit mekanizması (ZSD000)** + mevcut ETag birlikte.
Draft'a geçilmedi; bu **bilinçli istisna** olarak belgelenir. Draft, greenfield/FE
senaryolar için **hâlâ standart best practice**'tir (bkz. standards/05).

### Mimari (ortak — ZSD001, ZSD001, gelecek app'ler)

- **`ZSD000_T_LOCK`** (mandt + lock_object + lock_key key; locked_by, locked_at).
- **`ZSD000_CL_APP_LOCK`**: `acquire` (boş / timeout / aynı-kullanıcı → kilitle;
  başkası → locked_by) · `release` (kendi kilidi) · `check`. `c_timeout_seconds = 300`.
- Her BO'da **`AcquireLock` / `ReleaseLock` static action** (root) → sınıfa delege
  (COMMIT WORK yok; action LUW'unda RAP commit eder).
- UI (freestyle): Değiştir aç → AcquireLock; başkası tutuyorsa **read-only + uyarı**.
  Kaydet/Geri → ReleaseLock. **`beforeunload` → senkron ReleaseLock** (temiz kapanış).
  **2 dk heartbeat** (sekme açıkken kilidi tazeler → bekleyen kullanıcı devralınmaz).
  List Sil → önce AcquireLock (kilitliyse silinmez).

### Senaryo davranışları

| # | Senaryo | Çözüm |
|---|---|---|
| S1 | user-1 içeride, user-2 giriyor | user-2 **read-only + uyarı**; heartbeat user-1'i korur |
| S2 | user-1 başka browser/PC'den tekrar | **izin** (aynı kullanıcı; ETag korur) — S3'ü temiz tutar |
| S3 | user-1 kapatıp tekrar giriyor | beforeunload bıraktı; bırakmadıysa `sahibi=sen` → anında girer |
| S4 | user-1 kapattı, user-2 giriyor | beforeunload → **anında**; çökmede **5 dk** timeout sonra devralır |

### İki katman (neden yeterli)

- **Kilit (pessimistic, app-level):** erken uyarı "X düzenliyor" — best-effort
  (nadir milisaniye yarışında kaçabilir; istenirse `acquire` içinde tek-request DB
  lock ile sıfırlanabilir).
- **ETag (optimistic):** veri bütünlüğü — **kesin** (ikinci kaydeden 412). Yarış olsa
  bile bozulma imkansız.

## Sonuçlar

**Artı:** VA02 UX freestyle+V2'de; ortak/yeniden-kullanılabilir (ZSD001); az bakım;
pilot/governance kararını bozmaz; draft'a geçiş ileride açık.
**Eksi:** custom tablo+sınıf bizim bakımımızda; "kaldığın yerden devam" yok (kabul
edildi); küçük yarış penceresi (ETag kapatır); tarayıcı sert-çökmede 5 dk gecikme.

**Standart notu:** Yeni greenfield + Fiori Elements RAP app'lerinde **draft** tercih
edilir (framework-managed lock + resume). Bu ADR, freestyle+V2+draft'sız bağlama özgü
bilinçli bir sapmadır.

İlgili: ADR 0005 (C — enqueue), standards/05 §Lock, [[project_zsd001-ui-paradigm-all-or-nothing]].
