---
name: feedback_context-yonetimi-compact-clear
description: Context yönetimi — her turn 5-yollu karar (Continue/Rewind/Compact/Clear/Subagent); Rewind>Correcting; rot eşikleri; clear öncesi zorunlu checkpoint
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d6233272-ea94-4d94-bc1d-56e619f9dc11
---

Context'i **%100→autocompact**'a bırakma. Her dallanma noktasında **5-yollu karar** (statusline `ctx <N>%`: yeşil<%50 · sarı %50-74 · kırmızı≥%75):

| Durum | Hamle | Neden |
|---|---|---|
| Aynı görev, context hâlâ geçerli | **Continue** | hepsi yük-taşıyıcı; yeniden kurma israf |
| **Yanlış yola sapıldı / başarısız deneme birikti** | **Rewind (esc esc)** | dosya-okumaları TUT, başarısız denemeyi AT → bilgili tek-prompt'la yeniden |
| Bayat debug/ara-çıktı ile şişti | **`/compact <odak>`** | düşük efor; Claude özetler (pre_compact.py guard hatırlatır) |
| Gerçekten yeni/alakasız görev | **checkpoint → `/clear`** | sıfır rot; ne taşınacağına SEN karar ver |
| Sonraki adım çok ara-çıktı üretecek | **Subagent** | gürültü çocukta kalır, ana context'e yalnız sonuç döner |

**⭐ Rewind > Correcting (en değerli, sık kaçırılan):** Yanlış yola sapınca DÜZELTEREK ilerleme (correcting) — başarısız denemeler + düzeltmeler context'te birikir, rot artar. Bunun yerine **esc esc ile geri sar** + öğrendiğini katıp tek bilgili prompt ver. Correcting context'i = okumalar+2 başarısız+2 düzeltme+fix; Rewind = okumalar+1 bilgili prompt+fix. (Örn: cast-in-join saga'sını correcting yaptık — rewind daha temiz olurdu.)

**Rot eşikleri (somut):** ~300-400k token'da rot başlar (göreve bağlı); **%40-50 doluluk = zeka düşmeye başlar**. İdeal: %50-60'ta proaktif `/compact`. **autocompact'in tuzağı:** uzun debug sonrası en-aptal-anda (rot zirvede) ateşlenir + sonra isteyeceğin detayı özetten düşürür → **proaktif `/compact <ne yapacağımı tarif ederek>`** her zaman daha iyi.

**`/compact` sonra `/clear` ARDIŞIK YAPMA** = israf (özeti üretip çöpe atarsın). İkisi alternatif, sıra değil.

**Why:** Dolu context = rot (kalite↓) + en yavaş/pahalı çıkarım + kayıplı özet. `/clear`'ın **pre_clear guard'ı YOK** (asimetri: `/compact`'ın pre_compact.py guard'ı VAR). Clear'dan sağ çıkan tek şey **disk**: SESSION_NOTES + memory + git commit.

**How to apply:**
- Her dallanma noktasında 5-yollu tabloyu uygula; sarıya varınca kullanıcıya öner (durup karar: devam/rewind/compact/clear/subagent).
- **Yanlış yola sapıldığını fark edince ilk refleks = Rewind**, correcting değil.
- `/clear` niyetinde **önce checkpoint** (disk'te olmayan iş kaybolur).
- Otomatik yüklemeler (CLAUDE.md+MEMORY.md+ADR banner via [[feedback_takim-sureklilik-gun-sonu-resume]]) clear/compact'ta gelir; 4-adım protokol clear sonrası elle, compact sonrası gerekmez.
- İlgili: [[feedback_lider-bloke-olmama-background-dispatch]] · [[feedback_subagent-karar-kurali]].
