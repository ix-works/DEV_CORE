---
name: feedback_dev-verisi-yapi-olcer-dagilim-olcmez
description: "DEV'de ölçülen YAPI geçerlidir, DAĞILIM/HACİM değildir — tasarım eşiği (limit, tavan, varsayılan) DEV yüzdelerinden TÜRETİLEMEZ"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 78c7bae5-81aa-4c75-a44f-1fc2d4679222
---

Çalışma sistemi DEV'dir ve **verisi üretimi temsil etmez** (kullanıcı, 2026-09-08:
*"dev sistem burası, sistem verileri gerçeğe yaklaşmaz, yansıtmaz"*). Bu yüzden DEV'de
yapılan ölçümler **iki sınıfa ayrılır ve geçerlilikleri farklıdır**:

- **YAPI ölçümü — GEÇERLİ, üretime taşınır.** Alan var mı · anahtarda mı · domain sabit
  değerleri ve metinleri ne · hangi CDS hangi alanı taşıyor · iki numara birbirine eşit mi ·
  köprü zinciri çalışıyor mu · sorgu 400 mü veriyor. Bunlar **sistem yapılandırmasıdır**,
  veri hacminden bağımsızdır.
- **HACİM/DAĞILIM ölçümü — YALNIZ DEV'İN O ANKİ HÂLİ.** Yüzde · oran · p90/p95 · "kaç
  ürün kaç gözde" · "%29'unda HU yok" · "%95,3 serbest" · "bugün N teslimat açık".
  Bunlardan **tasarım eşiği, tavan, varsayılan değer veya kapasite kararı TÜRETİLEMEZ.**

**Why:** Bir dağılım ölçümü "canlı ölçüm" görüntüsü taşır ve tahmin-yasağı disiplinine
uyuyormuş gibi görünür — ama temsil etmeyen bir evrenden alınan p95, tahminden daha
tehlikelidir: yanlış sayıya **kanıt kılığı** giydirir. 2026-09-08 (ZSD001 toplama listesi):
çıktıdaki göz sayısı tavanını canlı dağılımla kalibre etmek üzere ölçüm (M6) başlatıldı;
kullanıcı DEV verisinin temsil etmediğini hatırlatınca ölçüm **iptal edildi**. Tasarım
dağılımdan **bağımsız** kuruldu (sabit tavan + yetmezse genişle) — bu, doğru dağılımı
bilmeye ihtiyaç duymayan ve üretimde de kırılmayan çözümdür.

**How to apply:**
1. Bir sayıyı tasarıma sokmadan önce sor: **bu sayı yapıdan mı, veriden mi geliyor?**
   Veriden geliyorsa DEV'de ölçülmüş olması onu geçerli kılmaz.
2. Dağılıma bağlı bir eşik gerekiyorsa iki yol var: ya **kullanıcıya sor** (depoyu/işi
   bilen taraf), ya da tasarımı **dağılımdan bağımsız** kur (kendini uyarlayan kural:
   "sabit N, yetmezse genişle" gibi). Üçüncü yol — DEV'den kalibre etmek — yoktur.
3. Raporlarda ve kayıtlarda dağılım sayılarının yanına **"DEV verisi — üretimi temsil
   etmez"** etiketini yaz. Sayıyı silme: sorgunun çalıştığını ve alanın dolabildiğini
   kanıtlar (yapı kanıtı), oranın kendisi değil.
4. Alt-ajan brifingine bu ayrımı **açıkça** koy; yoksa ajan yüzdeyi bulgu olarak döner ve
   lider onu eşik sanır.

prior-art: bulundu — [[feedback_edi-tasariminda-otorite-orijinal-mesaj-dosyasi]] (aynı kök:
DEV bir test sistemidir; o kayıt EDI/IDoc'a özel, bu genel). İlgili:
[[feedback_kapsam-niteleyicisini-dusurme]] · [[feedback_ham-satir-sayisi-is-nesnesi-sayisi-degildir]] ·
[[project_dev-sistem-prd-tasima-kullanici-talimati]] (o kayıt taşımayı düzenler, bu ölçümün geçerliliğini).
