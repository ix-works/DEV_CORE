---
name: feedback_isaret-sozdizimi-onermeden-once-prior-art-ara
description: "Bir kaynak dosyaya konacak işaret/sözdizimi (yorum işareti, pragma, anahtar sözcük) ÖNERMEDEN önce o dosya tipinin playbook'unda prior-art ara — #406'da önerilen `// dtel-istisna:` yorumu, yapı DDL'inin `//` kabul etmediği (push 400) ve SAP'nin yorumu sildiği playbook'ta yazılıyken onaya sunuldu"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 661be744-bf24-44a1-a38a-999a39ca6fba
---

⛔ Bir validator/kural tasarlarken kaynağın İÇİNE yaşayacak bir işaret önermek (ör. `// istisna:`
yorumu, pragma, özel anahtar) bir **SINIF iddiasıdır**: "bu dosya tipi bu sözdizimini taşır ve SAP
gidiş-dönüşünde korunur". KB-01 ① ARA bu anda tetiklenir — öneri kullanıcıya gitmeden ÖNCE.

**Vaka 2026-11-08 (DEV_CORE #406 / PR #409):** lider DTEL'siz alan istisnası için
`// dtel-istisna: <gerekçe>` işaretini önerdi, kullanıcı onayladı, ajan uyguladı. Bug-gate
yakaladı: `playbook/adt-tables-structures.md` §12.1 ③ "yapı DDL kaynağı `//` yorumu kabul etmiyor"
(push HTTP 400) ve §12 "SAP `//` yorumlarını normalleştirip siler". Tüketici korpusundaki 125
DTEL'siz alanın tamamı yapılardaydı ⇒ işaret tam hedeflediği yerde kullanılamazdı. Playbook'un
kendi pratik kuralı hazırdı: gerekçe kardeş `<NAME>.README.md`'de.

**Why:** onaylanmış bir öneri kod + fixture + doküman + PR gövdesine yayılır; prior-art kaçağı
bug-gate'e kadar fark edilmez ve tam bir düzeltme turu doğurur. Kullanıcı onayı yanlış
dayanağı düzeltmez ([[feedback_kaydin-onerdigi-fix-yonu-de-bir-iddiadir]]).

**How to apply:** kaynağa yazılacak her işaret/sözdizimi önerisinden önce `Grep path=core/playbook`
ile o obje tipinin dosyasında "yorum", "//", "comment", "normaliz" ara; ayrıca "SAP readback'te
korunuyor mu" sorusunu cevapla. Cevap yoksa öneriyi "DOĞRULANMADI" etiketiyle sun.

Son-doğrulama: 2026-11-08 · Applies-to: core validator/kural tasarımı, DDIC/CDS kaynak işaretleri
prior-art: yok (yakın: [[feedback_kaydin-onerdigi-fix-yonu-de-bir-iddiadir]])
