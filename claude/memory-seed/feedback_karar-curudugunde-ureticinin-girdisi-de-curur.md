---
name: feedback_karar-curudugunde-ureticinin-girdisi-de-curur
description: "Bir karar çürüdüğünde teslimat dosyasını düzeltmek YETMEZ — 'otorite dosya değil ÜRETİCİDİR' kuralı o an tersine döner: üreticinin girdisi hâlâ eski değeri taşıyorsa, baştan üretmek hatayı geri getirir. Üreticiyi de ölç."
metadata:
  node_type: memory
  type: feedback
---

**KURAL:** *"Otorite dosya değil ÜRETİCİDİR — teslimat canlıdan baştan üretilebilir"* kuralı,
kararın **kendisi çürüdüğünde tersine döner**. Üretici zincir kararı **veri olarak** taşır;
karar değişip zincir güncellenmezse "baştan üret" komutu artık bir **onarım değil, hatayı geri
getirme** işlemidir. ⇒ Karar çürütme turunda **üreticinin girdisini de ölç**, yalnız çıktıyı değil.

**ÖLÇÜLMÜŞ VAKA (2026-09-09, ZSD001 <MUSTERI-A> `<CARI-1>`).** Kullanıcı TP'leri yanlış belge
türüyle (`ZE02`) açtığımızı söyledi, doğrusu **`ZE06`**'ydı; hepsini silip yeniden yarattı ve
yükleme dosyasının 202 satırını kendi değiştirdi. Çıktıyı commit'leyip kayıtları kapatmak
**yetmiyordu**: `.tmp/tp-veri-2026-09-07/tp_acilis_satirlari.tsv` <MUSTERI-A> satırlarında hâlâ
`ZE02`=204 / `ZE04`=100 duruyordu ve `build_tp_files.py` `AUART`'ı **sabit basmıyor**, tam da o
TSV'nin `AUART` kolonundan okuyordu (`:60` `r["AUART"]`). Yani dosya bugün yeniden üretilseydi
202 satır sessizce `ZE02`'ye dönecekti. Düzeltmenin yeri çıktı değil **TSV'nin üreticisiydi**.

**Why:** "Üretici otoritedir" kuralı, üreticinin **canlıdan** okuduğu varsayımına dayanır. Ama
zincirde bir yerde karar **dondurulmuş veri** olarak oturuyorsa (sabit değil — *girdi dosyası*,
bu yüzden `grep 'ZE02'` ile kodda aranınca **bulunmaz**), üretici artık canlıyı değil eski
kararı yansıtır. Kusur sessizdir: script hatasız koşar, biçim doğrudur, satır sayısı tutar.

**How to apply:**
- Karar çürütme turunda üç şeyi ayrı ayrı kapat: **(1)** teslimat çıktısı · **(2)** kayıtlar
  (kaç yerde yaşıyorsa — [[feedback_iddia-kac-yerde-yasiyorsa-o-kadar-yerde-kapatilir]]) ·
  **(3) üretici zincirin girdisi**. Üçüncüsü en çok atlanandır.
- Değeri kodda arama, **veri akışını izle**: `grep 'ZE02' *.py` bu vakada **boş döndü** ve
  "üretici temiz" yanılsaması üretecekti. Doğru ölçüm, üreticinin okuduğu dosyada o kolonun
  dağılımını saymaktı.
- Zincir güncellenemiyorsa (üretici script bugün diskte yok gibi) bunu **açık tuzak** olarak
  kaydet: *"bu dosya baştan üretilecekse önce X'i çek"*. [[feedback_kapsam-niteleyicisini-dusurme]]
- Aynı turda **çürüyenin sınırını da ölç**: burada çürüyen yalnız `AUART`'tı; satış alanı
  (`1100/30/20`) doğruydu ve değişmemişti. Kararı bütün olarak çöpe atmak yeni hata üretir —
  [[feedback_ayni-sinif-ayni-duzeltme-degildir]].
