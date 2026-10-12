# diagnosing-bugs — kaynak ve gümrük kaydı (`intake/README.md` süreci)

| Alan | Değer |
|---|---|
| Kaynak | https://github.com/mattpocock/skills — `skills/engineering/diagnosing-bugs/SKILL.md` |
| Sürüm | commit `f3fc5632f401156837ee3872f14fe33ccf1024ea` (2026-10-12'de okundu) |
| Lisans | MIT — Copyright (c) 2026 Matt Pocock; tam metin [`LICENSE.upstream`](LICENSE.upstream) |
| Neden | Sebebi bilinmeyen hata avı için yapılandırılmış bir yol yoktu; intake-triage bu boşluğu değişiklik talebi gibi ele alıyordu. |

**Gümrük adımları:**
1. **İndirme:** yalnız `SKILL.md` okundu (oturum geçici dizini, karantina); repo'ya ham kopya alınmadı. Upstream dizinindeki `scripts/` (HITL döngü şablonu) ve `agents/` ALINMADI.
2. **Güvenlik:** içerik düz markdown; çalıştırılabilir parça, ağ çağrısı, dosya silme, gizli veri okuma yok. Upstream'in anıldığı tek betik (`scripts/hitl-loop.template.sh`) alınmadı, metinden çıkarıldı.
3. **Lisans:** MIT yeniden dağıtıma uygun; telif satırı + izin metni bu dizinde (`LICENSE.upstream`) ve `SKILL.md` başındaki kaynak notunda.
4. **Genericize:** kaynakta kimlik izi yok; uyarlamada tüketici proje adı/sistem kimliği kullanılmadı.
5. **Uyarlama:** Türkçe çeviri-uyarlama — faz yapısı ve birçok madde çevrildi; çekirdeğin araçları (ADT MCP uçları, fixture bataryası), yasakları (ADR 0005, tek SAP yazıcısı), kanıt kuralları (kontrol grubu, ÖNCE-ARA) ve RCA hipotez tablosu eklendi.
