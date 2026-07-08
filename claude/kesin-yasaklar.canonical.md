```
████████████████████████████████████████████████████████████████
█  ⛔  KESİN YASAKLAR — BYPASS YOK, İSTİSNA YOK (ADR 0005)  ⛔  █
████████████████████████████████████████████████████████████████
```

| Kategori | Yasak |
|---|---|
| **A — Standart SAP objeleri** (Z/Y ile başlamayan) | Hiçbir şekilde yarat/değiştir/sil. Append struct, alan ekleme, FM/BAdI/program değişikliği, message class değişikliği = YASAK. Bunları yapan script çalıştırma da YASAK. **Append field/DTEL adını AI ÖNERMEZ — kullanıcı belirler, sonucu AI'a bildirir.** |
| **B — Standart tablo verileri** | Direkt `INSERT/UPDATE/DELETE/MODIFY` YASAK (Z'li programda yazdığın kod içinde bile). Sıralı arama: BAPI → RFC FM → transaction (BDC) → kullanıcıdan manuel. Asla direkt SQL. |
| **C — Sistem state** | Transport request yaratma, release etme YASAK. Package yaratma YASAK. Enqueue lock silme YASAK. |
| **D — Z'li obje yaratma** | Login dili = projenin **master_language**'idir (`project.yaml`). Tüm 4 field label (short/medium/long/heading) o dilde ve TAM yazılır. Title/description boş bırakılmaz. Activate öncesi REST GET ile doğrulanır. |

**Yapılması gerekiyorsa:** DUR → AÇIKLA → ÖNERİ SUN → KULLANICIDAN İSTE → BEKLE → DEVAM. "Küçük dokunuş" istisnası YOK.

> **🧭 ÇEKİRDEK DAVRANIŞ — lider + TÜM alt-ajanlar:** **TAHMİN YASAK = kanıtlı hareket et.** Yöntem/pattern/syntax/alan-adını mevcut artefakt + playbook/standard'dan doğrula, canlı teyit et; "activated/uploaded/çalıştı" mesajına güvenme; emin değilsen DUR → sor; DTEL/append adı önerme (kullanıcı verir).

📖 Detay: `core/governance/decisions/0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md` · Bu blok her projenin kök `CLAUDE.md`'sine FİZİKSEL damgalıdır (junction'dan bağımsız daima yüklü); `check_kesin_yasaklar.py` guard'ı kanonikle eşliğini zorlar. Değişiklik: kanoniği düzenle → `sync_yasaklar.py` tüm projeleri yeniden damgalar.
