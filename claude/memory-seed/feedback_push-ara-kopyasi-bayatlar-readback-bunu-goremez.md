---
name: feedback_push-ara-kopyasi-bayatlar-readback-bunu-goremez
description: "Push aracına verilen ARA KOPYA (scratch/staging) düzeltme turunda bayat kalır; readback kapısı bunu YAPISAL OLARAK göremez çünkü kıyas canlı↔kopya, canlı↔repo değildir"
metadata:
  node_type: memory
  type: feedback
---

**Vaka (2026-09-01, yakalandı — patlamadan):** `.ccau` push'unda araç `--source-file` ile
çağrılınca izin sınıflandırıcısı tetikleniyordu; gateway dosyayı aracın **varsayılan okuduğu**
yola kopyalayıp (`.tmp/sap_scratch/classes/…`) öyle push etti. Aktivasyon derleme hatasıyla
düştü ⇒ düzeltme turu açıldı ⇒ `backend-expert` **repo** dosyasını düzeltti.
**Ölçüm:** repo `2951e732…` · scratch kopya hâlâ `e55e095c…` (**bozuk sürüm**).
İkinci push o kopyadan gitseydi **eski hatalı gövde sessizce yeniden yazılırdı** — ve
**readback "EŞİT" derdi.**

**Why — kapı yapısal olarak kör:** readback `canlı ↔ push edilen kaynak` kıyaslar.
Ara kopya push edilen kaynağın **kendisi** olduğu için kıyas her zaman tutar. Kapı
*"doğru içeriği mi yazdım"* sorusunu değil, *"yazdığımı yazabildim mi"* sorusunu yanıtlar.
Doğruluk kapısı **repo ↔ kopya** ekseninde olmalıydı ve o eksende **hiç kapı yoktu**.
Bu, `[[feedback_exit0-degil-cikti-kaniti]]` ailesinin sinsi hâli: kapı **çalışıyor**, sadece
**yanlış şeyi** ölçüyor.

⭐ **Önce şunu sor: kopya GEREKLİ MİYdİ?** Bu vakada değildi — araç zaten `--source-file` ile
repo dosyasını doğrudan okuyabiliyordu; kopya bir **izin-sınıflandırıcısından kaçınma refleksiydi**.
En ucuz çözüm kopyayı kapatmak değil, **hiç üretmemektir**.

**How to apply:**
1. **Ara kopyayı kalıcı sayma.** Push'tan hemen önce repo → staging **yeniden kopyala**;
   sonra `md5` al ve **üreticinin bildirdiği md5** ile karşılaştır
   ([[feedback-kapi-kosarken-dosya-donar-md5-teyidi]] — çapa üreticinindir, seninki değil).
2. **Düzeltme turu bitince bayat kopyayı SİL.** Dosya yoksa araç *"Local file not found"* ile
   **gürültülü** düşer; varsa **sessiz yanlış** yapar. Gürültülü hata her zaman tercih edilir.
3. **Brife yaz:** yeni gateway'e ilk talimat *"push'tan önce repo'dan yeniden kopyala + md5
   doğrula"* olsun. Bir önceki turun bıraktığı artefaktı **devralınan durum** olarak işaretle.
4. ⭐ **Genel kural:** bir aracın girdisi *"şu yoldaki dosya"* ise ve o yol **kaynağın kendisi
   değilse**, aradaki eşitlik **her turda yeniden kanıtlanır**. Tek seferlik kopya, ikinci turda
   bir **varsayıma** dönüşür.
5. Kaynağı kopyalamaya zorlayan şey bir **izin/araç kısıtıysa** bunu ayrıca infra kaydına geç —
   kısıt, güvenlik kazandırırken yeni bir sessiz-hata yüzeyi açmış olabilir.

Son-doğrulama: 2026-09-01 — iki md5 fiilen ayrışmış hâlde ölçüldü; kopya silindi.
prior-art: BULUNDU — [[feedback-kapi-kosarken-dosya-donar-md5-teyidi]] (kapı bayat sürüm ölçer)
aynı aileden ama **farklı mekanizma**: orada kapı geriden okur, burada kapı **doğru okur ama
yanlış ekseni** ölçer. İlgili: [[feedback_push-ok-mesaji-sahte-readback-esitligi]] ·
[[feedback_duzeltme-turu-kendi-regresyonunu-uretir]]
