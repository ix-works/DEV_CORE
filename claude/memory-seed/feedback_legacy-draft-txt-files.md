---
name: feedback-legacy-draft-txt-files
description: "ERP/<PKG>/ root'undaki .txt dosyaları \"ilk draft spec / legacy referans\"dır — .abap/.cds'a rename etme, silme"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7091c15c-424a-42a9-bcf8-7c3f51f36d33
---

ERP paket klasörlerinin root'unda bulunan `*.txt` dosyaları **legacy/draft spec** olarak değerlendirilir.

**Karakteristikleri:**
- Eski sistemden (legacy SAP) alınmış kod kaynağı, VEYA
- Kullanıcının manuel yazdığı ilk draft (yeni sistemde yazılacak kod için referans)
- Yeni sistemde **henüz implemente edilmemiş** olabilir veya implementasyona kaynak olmuş olabilir

**Yapılması GEREKMEYEN:**
- `.txt` → `.abap` veya `.cds` rename etme (yanlış sinyal: implemente olduğunu sanırsın)
- `programs/`, `cds/` gibi obje klasörlerine taşıma
- `.abap` versiyonu olduğu için silme (.abap'la birlikte de yaşayabilir — legacy referans)

**Yapılması GEREKEN:**
- Paket root'unda olduğu yerde bırak
- `.rules.md`'ye "Bilinen İstisnalar / Legacy" bölümünde listele
- Validator: paket root'undaki `.txt`'ler naming regex'inden muaf
- `docs/*.txt` ise FARKLI kategori (FS/TS dokümanı), bunlarla karıştırma

**Why:** 2026-05-14 Migration Adım 5A sırasında `ZFI_I_FITT_MIZAN_DATA.txt`, `ZFI_I_FITT_MIZAN_TOP.txt` dosyalarını `.abap` olarak rename edip `programs/`'a taşımayı denedim, `ZSD001_P_SATIS_CIRO.txt`'yi silmiştim. Kullanıcı düzeltti: "txt'ler eski sistemde olan kodlar, yeni sistemde yeniden yazılacak. txt'ler txt olarak kalsın, ilk draft spec gibi düşün." Eğer silseydim/rename'leseydim "yazılacak kaynak" kaybı olurdu.

**How to apply:** ERP/<PKG>/ root'unda `.txt` görürsen — dokunma. Sadece `.rules.md`'de listele. `docs/*.txt` istisna: bunlar FS/TS dokümanı (rename veya .md'ye çevirme her zaman güvenli değildir, içerik düz metin ise .txt kalabilir).

İlgili: standards/01-naming.md
