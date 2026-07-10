---
name: feedback_rap-editablefieldfor-key-create
description: "Released RAP BO'da mevcut belgeye CREATE BY _assoc ile child eklerken semantik key salt-okunur → key'in <Key>ForEdit (@ObjectModel.editableFieldFor) muadili set edilir; takılınca ÖNCE projeksiyon CDS source oku"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a1b6afef-4b32-4db8-92e7-c8825dc4ffa1
---

Released RAP BO'da (`I_SalesOrderTP`) **mevcut** belgeye `CREATE BY \_assoc` ile child (partner) eklerken semantik **key alanı salt-okunur** → create'te yazmak için projeksiyonda tanımlı **`<Key>ForEdit`** muadilini set et, key'i değil. ZSD001: partner eklerken `partnerfunction` (key) yazınca `parvw` boş kaldı → "Muhatap için muhatap rolünü girin"; `partnerfunctionforedit` yazınca düzeldi. Projeksiyonda işaret: `@ObjectModel.editableFieldFor: 'PartnerFunction'` → `PartnerFunctionForEdit`. **Yeni belge deep-create'te (`%cid_ref` root'a) key DOĞRUDAN çalışır** — fark yalnız "mevcut belgeye EKLEME"de.

**Why:** Saatlerce patinaj yaşandı (NOT_FOUND → key-create boş fonksiyon → "FIELDS'e key konmaz" → ayrı/ana MODIFY scope hipotezi etkisiz → yanlışlıkla "released-BO kısıtı, BAPI'ye geç" sonucu; kullanıcı reddetti: "iyi araştır önce, yapılamıyor olması mümkün değil"). Tek gereken projeksiyon CDS source'unu okuyup `editableFieldFor`'u görmekti — tahmin/alternatif-arama değil. [[feedback_playbook-once-oku]] + [[feedback_arastir-once-patinaj-uretim-gorev]]'in RAP-EML tekrarı.

**How to apply:** `CREATE BY \_assoc` bir alanı **yok sayıyor/boş bırakıyorsa** veya `FIELDS(key)` aktivasyonda "not a valid field" diyorsa → tahmin etme, BAPI/scope'a kaçma. **ÖNCE** `adt_get <Entity>TP cds include_source=true` ile projeksiyon source'u oku; `@ObjectModel.editableFieldFor`, `@ObjectModel.readonly`, suppress'li alanları tespit et. Released BO'da yazılamayan key ≈ daima bir `...ForEdit` alanı vardır. Mevcut-belgeye-ekleme'de önce mevcut child key'lerini oku → route: varsa UPDATE, yoksa CREATE BY \_assoc (ForEdit'le), kaldırıldıysa DELETE. `customer` gibi BP alanları ALPHA-pad (10 hane). Tam reçete + denenen-başarısız: `playbook/adt-rap.md` §35, `playbook/checklists/rap-troubleshoot.md`. İlgili: [[project_zsd001-rap-fittings]] [[project_nakliye-dugumu-tvkn]] [[feedback_done-tam-kapsam-dogrula]].
