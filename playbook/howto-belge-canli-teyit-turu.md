---
applies_to: [all]
---

# HOWTO — Belge ↔ Canlı Teyit Turu (TS build'e girmeden önce)

> **KURAL (MUST):** Bir teknik tasarım belgesi build'e girmeden önce, içindeki **her
> *"canlıda mevcut / kurulu / bağlı / zaten yapıldı / yapılacak"* iddiası ÖLÇÜLÜR.**
> Ölçülmemiş bir canlı-iddia, belgenin geri kalanı kusursuz olsa bile build'i yanlış
> yöne sokar — çünkü developer onu **veri** olarak okur, tahmin olarak değil.
>
> **Kim:** taze/bağımsız bir göz (yazar kendi iddiasını teyit edemez — doc-gate bağımsızlık
> kuralının aynısı). **Ne zaman:** TS mutabakatından SONRA, build kapısından ÖNCE.
> **Çıktı:** ölçüm tablosu + çürüyen her iddia için belge düzeltmesi + **İKİNCİ KAPI**
> (`checklists/doc-checklist.md` §İKİNCİ KAPI — düzeltme kendi kapısını da koşar).

**Neden var (2026-08-19, ölçülmüş tur):** bir RAP TS'i için koşulan teyit turu **7 bulgu**
(F-1…F-7) üretti; **üçü belgenin normatif iddiasını çürüttü** — ① reuse edilecek FM'in
**imzası belgenin kendi normatif kuralını ihlal ediyordu** ve gövdesi **boştu** ② *"yapılacak"*
denen uyarlama adımlarının **4'ü DEV'de zaten yapılmıştı** ③ *"geri dönüşün son noktası"*
denen eşik **zaten geçilmişti**. Hiçbiri belgeyi okuyarak görülemezdi.

## Ölçüm başlıkları (beşi de koşulur; atlanan başlık rapora "ÖLÇÜLMEDİ" diye yazılır)

| # | Başlık | Ne ölçülür | Yöntem / tuzak |
|---|---|---|---|
| C-1 | **Ad çakışması** | Belgede yaratılacak denen her ad canlıda **gerçekten boş mu**; mevcut denen her ad **gerçekten var mı** | `adt_search_objects` + paket içeriği. ⛔ **POZİTİF KONTROL ZORUNLU:** aramanın var olduğunu bildiğin bir adı bulduğunu önce kanıtla — yoksa "bulunamadı" *"yok"* değil, **"arama çalışmadı"** olabilir (bulunamadı ≠ yok) |
| C-2 | **Reuse iddiaları** | "Şu FM/class/CDS yeniden kullanılacak" denen her obje: var mı · **imzası belgenin kendi kuralına uyuyor mu** · **gövdesi dolu mu** | `adt_get` ile **kaynağı** oku. ⛔ Varlık ≠ kullanılabilirlik: obje aktif görünüp gövdesi boş olabilir; imza (parametre tipi/adı) belgedeki normatif kuralı ihlal edebilir |
| C-3 | **Uyarlama durumu** | *"Yapılacak"* denen her uyarlama adımı DEV'de **zaten yapılmış olabilir** (ve tersi: "hazır" denen yapılmamış olabilir) | İlgili uyarlama tablosunu **oku**. ⛔ Bu ikizin ters yönü de koşulur (DOC-CR-01) — yalnız "eksik mi" değil, "zaten var mı" |
| C-4 | **Paket / inaktif** | Objeler doğru pakette mi; **sessiz inaktif** obje var mı | `adt_package_contents` + inactive-worklist. ⛔ "aktif" metadata'sı ≠ **kodun** aktif |
| C-5 | **Transport** | Açık TR var mı, hangi objeleri taşıyor | ⛔ **`adt_transport_list` SAHTE-SIFIR döndürebilir** — `count: 0` + `shape_recognized: true` iken bile sistemde açık transport bulunduğu **ölçüldü (2026-08-19)**. Transport **`E070` / `E071`'den** okunur; `adt_transport_list`'in sıfırı tek başına kanıt DEĞİLDİR *(kısmi kök-fix 2026-08-10 `infra-changelog`'ta; bu tarihten sonraki nüks bu satırın gerekçesi — **bu turda bağımsız repro edilmedi**, lider ölçümüdür)* |

## Rapor biçimi (belgeye EK olarak işlenir)

| İddia (belge §) | Ölçüm yöntemi | Sonuç | Belge etkisi |
|---|---|---|---|
| §x.y "… canlıda kurulu" | `adt_get <obje>` | ÇÜRÜDÜ — gövde boş | §x.y yeniden yazıldı, reuse iptal |

- **"Doğrulandı" demek için çıktı gerekir** — ölçüm komutu + dönen değer. *"Okudum, doğru"* kanıt değildir.
- **Çürüyen iddia belgeyi düzeltir, düzeltme İKİNCİ KAPI'yı tetikler** (dar kapsam: değişen satırlar
  + değişen sayı/adın diğer geçtiği yerler + kararın yayılım listesi).
- Ölçülemeyen başlık **"ÖLÇÜLEMEDİ"** yazılır — sessizce atlanmaz (ölçülemedi ≠ temiz).

📌 İlgili: `checklists/doc-checklist.md` **DOC-CR-03** (kapı üyeliği) · `standards/04-documentation-fs-ts.md`
§3.0 İLKE-5 (build-time teyit ≠ fonksiyonel karar) · `CLAUDE.core.md` §7 KAPSAM BEYANI.
