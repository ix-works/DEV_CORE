---
name: feedback_olcum-duzeyi-kayit-ici-mi-kayitlar-arasi-mi
description: "Bir ölçümün ÇÜRÜTME gücü, hangi DÜZEYDE saydığına bağlıdır — kayıt İÇİNDE ölçmek, kusuru kayıtlar ARASINDA olan bir hatayı asla göremez. Yanlış düzeyde yapılmış ölçüm 'kusur yok' hükmüne dönüşür."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 861ca50c-63ab-4fdb-9003-e77ece277765
---

**KURAL:** Bir iddiayı çürütmeden önce sor: *kusur, tek kaydın İÇİNDE mi yaşayabilir, yoksa
kayıtlar ARASINDA mı?* Ölçümü yanlış düzeyde kurarsan sonuç temiz çıkar ve bu **temizlik
sahtedir** — kapsam dışında kalan yeri hiç görmemişsindir.

**Ölçülmüş vaka (2026-09-07, ZSD001 <MUSTERI-A> CPI mapping).**
İddia: *"kalem düzeyindeki `RFF+ON` başlığa (`E1EDK09/VTRNR`) basılıyor, yanlış çift doğuyor."*
Ben bunu **mesajın içinde** ölçerek çürüttüm: her `UNH` bloğunda 1 `LIN` + 1 `RFF+ON` var
(10.071/10.071) ⇒ *"tek aday var, karışma imkânsız, mapping'de kusur yok"* yazdım ve bu hüküm
`CLAUDE.md` + çapa + PR ile main'e girdi.

⛔ **Kusur mesajın içinde değil, mesajlar ARASINDAYDI.** CPI'nın girdisi tek mesaj değil **tüm
UNB zarfı**dır; bir dosyada 1–100 mesaj vardır ve `removeContexts` kuyruğu **belge boyunca**
düzleştirir ⇒ her IDoc dosyanın **1. mesajının** başlığını alır. Kanıt: 11 mesajlı dosyanın
11 IDoc'unun **11'inde de** `VTRNR`/`LABNK` aynı, oysa orijinalde mesaj bazında değişiyor.
Sonuç 997 IDoc'luk tetiklemede kitlesel `V4 034` oldu. Kullanıcı: *"sen bunları kontrol edip
OK demedin mi?"*

**İkinci tuzak — "tek vaka" seçimi.** Aynı gün *"`206833` uçtan uca kanıt"* dedim; o kayıt
17 mesajlı dosyanın **1. mesajı**ydı — kusurun tanım gereği görünemediği **tek** konum.
Kör kanıt. (Korpusun 225/746 dosyası tek mesajlı; bu bölge kusuru sistematik olarak gizliyor.)

**Why:** Yeşil bir ölçüm psikolojik olarak kapatıcıdır; kapsamını sorgulatmaz. Oysa "0 bulgu"
iki farklı şeyin çıktısı olabilir: (a) gerçekten kusur yok (b) kusurun yaşadığı düzeye hiç
bakılmadı. İkisi **aynı görünür**.

**How to apply:**
- Ölçüm kurarken **düzeyi açıkça yaz**: *"mesaj İÇİNDE saydım"* / *"mesajlar ARASINDA saydım"*.
  Düzey yazılmamış bir sayı, çürütme için kullanılamaz.
- **Kapsayıcının çokluğunu önce ölç.** Dosya→mesaj, belge→kalem, IDoc→segment: taşıyıcı birim
  kaç kez tekrar ediyor? `1` ise gölge bölgedesin. (Burada: dosya başına 1–100 mesaj.)
- **Tek vaka seçerken ilk kaydı SEÇME.** Çoklu-kayıt yapıda hizalama/bağlam hataları 1. kayıtta
  görünmez. Ortadan ve sondan seç; tercihen en kalabalık kabı seç.
- **Karşıt kontrol kur:** aynı kaynaktan beslenen ama farklı düzeyde tekrarlayan bir alan bul.
  (Burada `REFINT` doğru çıktı çünkü dosyada zaten tek `UNB` var — bu, mekanizmayı kanıtladı.)
- "Bugün doğru çıkıyor" ≠ doğru kurgulanmış: `ARKTX` yalnızca `IMD+F`'nin **daima ilk** gelmesi
  sayesinde yarısında doğruydu; sıra değişse sessizce bozulurdu.

İlgili: [[feedback_yabanci-runtime-artefakti-once-tek-vaka-turu]] ·
[[feedback_curutme-de-bir-iddiadir-yerine-yazilan-sayi-olculur]] ·
[[feedback_kapsam-niteleyicisini-dusurme]] · [[feedback_bulgu-listesi-ornektir-sinif-duzeltmesi-tarama-ister]] ·
[[feedback_edi-tasariminda-otorite-orijinal-mesaj-dosyasi]] ·
[[feedback_yesil-regresyon-suiti-duzeltmenin-kaniti-degildir]]
