---
name: feedback_merge-safe-dagitimda-satir-yalniz-onarilan-dosyaya-ulasir
description: "Merge-safe bir dağıtıcı (mevcut dosyayı EZMEYEN tohum/şablon kopyalayıcı) yeni bir SATIRI yerelde DÜZENLENMİŞ (ya da manifest'siz, ayırt edilemez) kopyaya ulaştıramaz — oraya ulaşan yüzey yalnız yeni dosya ve özel ONARILAN dosyadır; dokunulmamış kopya S1 ile güncellenir"
metadata:
  node_type: memory
  type: feedback
---

Bir dağıtıcı **merge-safe** ise (hedefte yerelde değiştirilmiş dosyayı ezmez, yalnız eksikleri
ekler), eklediğin **dosya** herkese gider ama eklediğin **satır** yerelde **düzenlenmiş** (ya da
manifest kaydı olmadığı için ayırt edilemeyen) kopyaya gitmez — o dosya ezilmez. Bu kopyalara ulaşan
tek satır-yüzeyi, dağıtıcının **özel olarak onardığı** dosyadır. *(Dokunulmamış kopya gövde
güncellemesi alır — aşağıdaki DARALTMA; `seed_memory` için S1, 2026-10-03.)*

**Ölçülen vaka (2026-09-18, memory tohumu):** `seed_memory.py` merge-safe'tir ve yalnız
`MEMORY.md` için bir `_index_onar` adımı koşar (eksik tohum satırlarını enjekte eder).
`_indeks-*.md` hub'ları ise sıradan dosyalardır. Yerelde ders bir **hub'da** indeksliydi;
aynı yerleşim tohuma taşınsaydı **ders dosyası giderdi, indeks satırı gitmezdi** ⇒ ders
hedefte **indekssiz** kalırdı (JIT-recall'da yetim).

**Kanıt (sahte "mevcut makine", önce/sonra + negatif kontrol):** hedef önce eski tohumla
kuruldu (204 eklendi, 195 ders). Yeni tohum aynı hedefe uygulandı → 3 dosya **ve** 3 indeks
satırı ulaştı (195→198), çünkü satırlar `MEMORY.md`'ye konmuştu. ⭐ **Negatif kontrol:** bir
hub'a konan sonda satırı tohumda kaldı (`1`) ama hedefe **ulaşmadı** (`0`).

**Why:** "dosyayı tohuma ekledim" ile "ders karşı makinede görünür oldu" **aynı şey değildir**.
Merge-safe olmak bir güvenlik özelliğidir (yereli ezmez) ama aynı zamanda sessiz bir yayılım
sınırıdır: hata vermez, yalnız eksik yayar. Bu yüzden `--force` bilinçli bir karardır.

**⚠ DARALTMA (2026-11-12, kod ölçümü):** 2026-09-18 ölçümü S1 ÖNCESİNE aittir. DEV_CORE #318 (`cf30813`, 2026-10-03) ile `seed_memory.py` `_mevcut_dosya_karari` hedefteki dosyanın sha'sı **eski tohum sha'sına eşitse** (yerelde dokunulmamış) gövdeyi `guncelle` eder — hub'lar (`_indeks-*.md`) dahil (fixture `tohum_govde_guncelleme` G4). Bugünkü sınır: hub'a eklenen satır yalnız **yerelde düzenlenmiş** (ya da manifest kaydı olmayan, `ayirt-edilemez`) hub'a ulaşmaz. Pratik kural değişmedi: her iki durumda da ulaşan yüzey **yeni dosya + MEMORY.md satırı**dır (tarihli hub deseni). Daraltmayı yakalayan: bir infra turu (fixture `tohum_yayilim_m4` S1/S2 iki kolu da ölçer).
Son-doğrulama: 2026-11-12 · Applies-to: merge-safe tohum/şablon dağıtıcıları (seed_memory ve benzerleri)

**How to apply:**
- Merge-safe bir dağıtıcıya **satır** eklerken önce sor: *bu dosya hedefte ezilir mi?* Ezilmiyorsa
  satır yalnız **yeni** kurulumlara gider.
- Dağıtıcının **özel-onarım** yaptığı dosyayı koddan bul (`_index_onar` benzeri) — satır oraya
  yazılır. Kaynak yerleşimi (yerelde hangi hub'daydı) **kopyalanmaz**, dağıtım yüzeyi belirler.
- Doğrulamayı **sahte bir "mevcut makine"** üzerinde yap: önce ESKİ sürümle kur, sonra YENİ
  sürümü uygula, farkı ölç. Boş dizine tohumlamak bu sınıfı **göremez** — boş hedefte her dosya
  zaten kopyalanır.
- **Negatif kontrol koy:** ulaşmaması gereken yüzeye bir sonda satırı bırak; ulaşmadığını gör.
- İlgili: [[feedback_yesil-regresyon-suiti-duzeltmenin-kaniti-degildir]] ·
  [[feedback_brifinge-koydugun-yolu-once-kendin-kos]]
