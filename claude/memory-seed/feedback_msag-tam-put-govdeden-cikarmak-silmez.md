---
name: feedback_msag-tam-put-govdeden-cikarmak-silmez
description: "Mesaj sınıfından mesaj SİLMEK: tam PUT gövdesinden çıkarmak SİLMEZ (200 döner, no-op) — silme <mc:deletedmessages> ile; araç populate_message_class.py --delete (önce/sonra kapısı), SE91 tek yol DEĞİL"
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

**Kural:** Bir Z mesaj sınıfından (MSAG) mesaj silmek gerektiğinde gövdeden satır çıkarıp tam PUT
etme — **silmez**. Tek çalışan yol gövdedeki `<mc:deletedmessages mc:msgno="NNN"/>` koleksiyonudur;
çekirdek aracı:

```
python core/scripts/populate_message_class.py --name <MSAG> --transport <TRANSPORT> --delete 006,011 --dry-run
python core/scripts/populate_message_class.py --name <MSAG> --transport <TRANSPORT> --delete 006,011
```

Araç canlıyı okur, kalan mesajları **canlı öznitelikleriyle** geri gönderir, silinecekleri
`deletedmessages` olarak ekler, yazdıktan sonra **önce/sonra kapısını** koşar (exit 0 = tuttu,
3 = TUTMADI/ÖLÇÜLEMEDİ). Yöntem + SAP kaynağı + tuzaklar: `core/playbook/adt-message-class.md` §27.5.

**Why:** 2026-09-24, `s4_private` 2025, DEV: 229 mesajlı sınıfa 17'si çıkarılmış 212'lik tam gövde
gönderildi → LOCK/PUT/UNLOCK üçü de **200**, T100 **229 → 229**. Sebep SAP kaynağında:
`CL_ADT_MC_RES_CONTROLLER=>DO_UPDATE`'teki "listede olmayanı sil" döngüsü **yorum satırı**. Aynı
turda iki yanlış hüküm yazılmıştı (*"PUT REPLACE eder"* · *"ADT'de silme yok, yalnız SE91"*) —
ikisi de çürüdü. `deletedmessages` ile önce 1 (229→228), sonra 16 mesaj (→212) silindi; kalanlar
birebir. Mesaj alt kaynağı `/messages/{nr}` üzerinden LOCK/DELETE 423/403 verdi ve kilit bırakılamamış
kalabildi.

**How to apply:**
1. "mesaj sil / atıl mesaj / SE91'den silinmeli / PUT silmiyor" duyunca → aracın `--delete` kipi.
2. **"PUT 200" silindiği anlamına GELMEZ** — no-op da 200 döner; hüküm yalnız önce/sonra mesaj
   kümesinden verilir. `changedAt` silmede **güncellenmez**, ona bakma.
3. Boş `msgno` SAP'de **`000`'ı siler** — numarayı tahmin/zfill etme, tam 3 hane ver.
4. Oturum dili ≠ master dil ise SAP yalnız o dilin satırını siler (yarım silme) — araç reddeder.
5. Uzun metin silmesi transport kaydı açmaz → başka sisteme taşımada artık kalabilir (DOĞRULANMADI).
6. SAP'ye yazmadır: ADR 0005 çerçevesinde yalnız Z sınıfı + kullanıcı onayı; önce `--dry-run`.

Son-doğrulama: 2026-09-24 · Applies-to: s4_private 2025 (ADT messageclass)
İlgili: [[feedback_arac-basarisizligini-zararsiz-sayma]] · [[feedback_bos-gondermek-hic-gondermemek-degildir]]

⚠ **ARAÇ İDDİASI** — bu ders *"bugün SAP'nin bu ucu böyle davranıyor"* der; başka sürümde
(ör. yorum satırındaki döngü açılırsa) tam PUT silmeye başlayabilir. Dayanmadan önce bir kez ölç.
