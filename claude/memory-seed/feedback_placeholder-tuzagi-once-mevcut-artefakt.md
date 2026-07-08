---
name: feedback_placeholder-tuzagi-once-mevcut-artefakt
description: "Obje-tipi playbook placeholder ise \"pattern yok\" deme; repo'da mevcut çalışan artefaktı (aynı tip .abap) + adt-foundation.md ara, formatı kopyala"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c874b6ce-b5f4-4780-8a44-b99611c71492
---

Bir SAP obje-tipi (FM, class, CDS...) için işlem yaparken, o tipe ait playbook dosyası **placeholder/boş** olabilir — bu "çalışan pattern yok" demek DEĞİL. Çalışan pattern başka yerde olabilir: `playbook/adt-foundation.md` (genel push/lock/activate §'leri) ve/veya repo'da daha önce başarıyla yaratılmış **canlı artefakt** (aynı tipte `.abap` dosyası).

**Why:** 2026-06-02 C1'de FM imza+gövde push'unu (daha önce ZSD001/ZSD001'te ÇALIŞMIŞ bir iş) "ADT'den yapılamaz" sanıp saatlerce 400/423/500 deneme-yanılma yaptım. Çalışan yöntem `adt-foundation.md §3.2` + `ERP/SD/ZSD001_CLC/functions/ZSD001_FM_SO_CREATE.abap`'taydı; ben sadece adı eşleşen boş `adt-fugr-functions.md`'e bakıp pes ettim. Ayrıca register'ın yanlış hipotezine (imza `*"` comment-block ile) demir atıp, `*"` reddedilince "olmaz" diye yanlış genelledim — doğru yöntem **satır-içi ABAP imzası** (`FUNCTION name` sonrası `IMPORTING/EXPORTING...`). Kullanıcı "geçmişte yapılmış iş için neden uğraşıyorsun, playbook'ta yok mu yoksa sen mi okumuyorsun" diye uyardı.

**How to apply:** Obje işi öncesi: (1) tip-playbook placeholder ise DURMA → `adt-foundation.md` oku + `grep -r "FUNCTION\|aynı-tip" ERP/**/functions/*.abap` ile mevcut çalışan örnek bul, **formatı birebir kopyala**. (2) "X ADT'den yapılamaz" demeden önce repo'da X'in canlı örneği var mı kontrol et. (3) deferred-triggers/register notu KANIT değil HİPOTEZ — doğrula. (4) Kök kural [[feedback_playbook-once-oku]] ile aynı: tahmin yapma, önce oku. Detay: playbook/lessons-learned.md PATTERN #7.
