---
name: feedback_transport-numarasi-istek-mi-gorev-mi-rules-md-otoritedir
description: "Push araçlarına İSTEK (K-tipi) numarası verilir, GÖREV (S-tipi) değil — ve doğru numaranın otoritesi çapa değil paketin .rules.md'sidir (aynı hata 3 kez)"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 147413fa-85a8-4e1e-8abc-7c28606ff1f5
---

**Vaka (2026-09-01, ÜÇÜNCÜ tekrar):** Gateway brifine transport olarak `<TRANSPORT-GOREV>` yazdım —
**çapadan (`*-RESUME.md`) kopyaladım.** Araç `409` verdi: *"SAP assigned transport <TRANSPORT> but
<TRANSPORT-GOREV> was requested"*. Ajan üç bağımsız kaynakla düzeltti; SAP'ye hiçbir şey yazılmadı.

| Kaynak | Ölçüm |
|---|---|
| `E070` | `<TRANSPORT>` = **`TRFUNCTION='K'`** (istek) · `<TRANSPORT-GOREV>` = **`'S'`** (görev), `STRKORR='<TRANSPORT>'` |
| `<source_root>/<MODULE>/<PKG>/.rules.md:176` | *"**Aktif TR: `<TRANSPORT>`** (workbench isteği) — objeler `<SAP_USER>`'ın **`<TRANSPORT-GOREV>`** görevine yazılır"* |
| `SESSION_NOTES:1414` · `:2602` | Aynı hata daha önce **iki kez**: *"lider alt görev `<TRANSPORT-GOREV>`'e çevirdi ⇒ `populate_tables.py` 9/9 `409`"* · *"bu evde İKİNCİ KEZ"* |

**Why:** SAP'nin kilit/atama yanıtı **daima K-tipi isteği** döndürür. Araca S-tipi görev verilirse
araç "istediğim bu değildi" diye `409` atar — **doğru davranış**, ama teşhis pahalıdır: her
tekrarında bir ajan turu yandı. Asıl kök neden numaranın kendisi değil, **hangi belgenin otorite
olduğu**: çapa/`SESSION_NOTES` çalışma anının numarasını yazar (çoğu zaman **görev**, çünkü objeler
oraya düşer), oysa **araca verilecek olan İSTEKTİR**. İki farklı doğru cümle, iki farklı bağlam.

**How to apply:**
1. **Transport numarasını çapadan ALMA.** Otorite sırası: paketin **`.rules.md` → Transport** bölümü
   → `E070` canlı ölçümü → (yalnız ikisi yoksa) çapa. Çapa bir zaman fotoğrafıdır
   ([[feedback_capadaki-acik-madde-devralmadan-once-olculur]]).
2. **Araca `TRFUNCTION='K'` olanı ver.** Objenin hangi göreve düştüğü SAP'nin işidir; sen kabı
   söylersin. Emin değilsen tek sorgu yeter:
   `SELECT trkorr, trfunction, strkorr FROM e070 WHERE trkorr IN ( ... )` — `S` görürsen
   `STRKORR`'daki numarayı kullan.
3. **Brif yazarken transport satırını ölçüm olarak işaretle** — *"`.rules.md:176`'dan"* gibi. Kaynağı
   yazılmamış bir numara, alt-ajan için bir **emirdir** ve sorgulanmadan kullanılır
   ([[feedback_aktardigin-olcum-emre-donusunce-kanitini-tasi]]).
4. ⛔ `409` gördüğünde **yeni istek/görev AÇMA** — ADR 0005-C. Doğru tepki numarayı düzeltmektir.
5. ⚠ **Sessiz kurtarma teşhisi geciktirir:** ilk vakada `push_object.py`'nin numarayı sessizce
   düzeltmesi kusuru **maskeledi**; hata ancak düzeltmesiz bir araçta (`populate_tables.py`)
   göründü. Bir araç "kendiliğinden çalışıyorsa" bu, girdinin doğru olduğunu KANITLAMAZ
   ([[feedback_exit0-degil-cikti-kaniti]]).

Son-doğrulama: 2026-09-01 (E070 + `.rules.md` + SESSION_NOTES, üç kaynak) · prior-art: arandı —
memory'de transport-kabı kaydı YOKTU; bilgi yalnız proje dosyalarında duruyordu ve **üç kez
atlandı**. Applies-to: transport kabı olan tüm projeler.
