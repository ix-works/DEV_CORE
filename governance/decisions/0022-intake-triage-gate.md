---
adr: 0022
title: Intake Triage Gate — geliştirme talebi alım-sınıflama ve modül-persona katmanı
status: accepted
date: 2026-07-08
deciders: <SAP_USER>, lider-ajan
supersedes: —
superseded-by: —
---

# ADR 0022 — Intake Triage Gate (ITG)

## Bağlam

Bir geliştirme talebi (prompt / Excel / FS) geldiğinde, farklı kişiler aynı araçları
kullanınca **kalite sapması** oluşuyor: ajan kimi zaman modül-uzmanı gözüyle davranıp
isterleri netleştiriyor, etki/risk çıkarıyor, ilgili birikimi tarıyor; kimi zaman atlıyor.
İhtiyaç: kapsamına **orantılı**, kişiden bağımsız **tutarlı**, **atlanamaz** (isteğe bağlı
değil) bir alım-süreci — hız/kaliteyi bozmadan.

Karar 7-turluk kullanıcı co-design + 6 araştırma ajanı (web best-practice + 17 SAP-AI repo +
mevcut-mimari gap analizi) sonucu şekillendi. İki bulgu tasarımı belirledi:

1. **Persona placebo'su:** serbest "act as SAP SD danışmanı" promptlama olgusal doğruluğu
   güvenilir biçimde artırmaz, düşürebilir (2024-2026 sistematik çalışmalar). Değer yalnız
   persona **yapılandırılmış prosedüre** (kontrol-listesi + kaynak-işaretçisi) bağlıysa çıkar.
2. **Determinizm:** kullanıcılar-arası tutarlılık serbest prompt'la olmaz; **yapılandırılmış
   intake şablonu + rubrik/gate** ile olur (olasılıksal çıktıyı doğrulanabilir artefakta çevir).

## Karar

Geliştirme talebini işleyen, üç katmanlı **Intake Triage Gate** kurulur (ADR 0019 "hook-
enjeksiyon + içerik + gate" 3-eksen desenine oturur):

**1. Enjeksiyon (atlanamaz tetik).** `scripts/hooks/intake_triage.py` (UserPromptSubmit;
skill_injector'a kardeş). Geliştirme-niyeti sinyali görünce ITG protokolünü enjekte eder +
kaba modül-ipucu verir. **Hook DURUM TUTMAZ ve SINIFLAMA YAPMAZ** — yalnız tetikler ve
protokolü dayatır; kapsam-sınıflama (S0/S1/S2), konu-çıkarımı ve araştırmayı AJAN yapar
(regex kapsam-büyüklüğünü kestiremez → LLM muhakemesi + gerekçe gerekir). Gerekçe-beyanı +
kullanıcı-görünürlüğü yanlış-sınıflamayı dizginler.

**2. İçerik.** `playbook/intake-triage.md` (genel 6-adım protokol + kalite kilidi + S0/S1/S2
akışları + S2 intake-artefaktı şeması) + `playbook/modules/<modül>.md` (modül kural-paketleri).
**Kural-paketi = bilgi-deposu DEĞİL, "tetik-haritası + araştırma protokolü + kaynak-işaretçisi".**
Domain-olgusu GÖMÜLMEZ (eskir + yanıltır + LLM zaten bilir); paket ajanı doğru kaynağa yönlendirir.

**3. Zorlama (kademeli, S2'ye sınırlı).** Protokolün *devreye girmesi* zaten atlanamaz (hook).
*Tamamlanma* için: Faz-1 = `run_review.py` S2 ITG-mutabakat pre-flight (reviewer, ADR 0006);
Faz-2 = deterministik `pre_tool_guard` state-gate (pilot kanıtlarsa). S0/S1 hafif kalır (over-gating yok).

**Model (6 adım + enine kesen kalite kuralı):** sınıfla → isterlerden konu çıkar →
3-eksen araştır (domain + canlı-sistem + prior-art) → kanıtlı değerlendir → kapsam-orantılı
soru+aksiyon → çıkışta öğrenileni kaydet. **Kalite kuralı:** TAHMİN YASAK/kanıt-çıpası +
Z-obje'de canlı-doğrulama (ADR 0016). Hafıza = hipotez, canlı = otorite.

**Mimari = hibrit:** genel ITG iskeleti (modül-bağımsız, her işte) + modül kural-paketleri
(iskelete tetik-örnekleri besler). Kapsam sınıfı = 3. Pilot = core-jenerik + TD/SD.

## Reddedilen alternatifler

- **14 ağır modül-danışman ajanı** (sc4sap deseni): her modül için ayrı agent-dosyası.
  Reddedildi — LAZY/6-rol modelinden sapma + bakım/context maliyeti; kural-overlay yeterli.
- **Serbest "act as X danışmanı" persona:** placebo/zarar riski (yukarıda). Yapılandırılmış
  kural-paketi aktivasyonu tercih edildi.
- **Domain-olgusunu kural-paketine gömme:** eskir + yanıltır + LLM zaten taşır. Paket yalnız
  yönlendirir; olgu kaynak-zincirinden (canlı + docs-MCP + hafıza) gelir.
- **Tek-beden ağır intake (her işe):** hız öldürür; over-gating (Anthropic "karmaşıklığı
  yalnız kanıtlanabilir iyileştiriyorsa ekle"). Kapsam-orantılı S0/S1/S2 tercih edildi.
- **4+ kapsam sınıfı:** sınıf-sınırı bulanıklaşır, triage kararı zorlaşır. 3 sınıf yeterli.

## Sonuçlar

- **Yaz-bir-kez-DEV_CORE, devral-her-yerde:** junction'la tüm projeler otomatik alır; yeni
  proje `init_project` template'inden hook-kaydını devralır; mevcut projeler settings.json'a
  bir kez hook-satırı ekler (D7 drift bunu yakalar).
- **Yeterlilik objektif ölçülür:** ITG-var/yok eval (skill-creator) — placebo mı katkı mı görünür.
- **Kaynak-zincirine bağımlı:** docs-MCP (radar adopt-adayı) + canlı-okuma + memory birlikte;
  paket tek başına yetmez, zinciri tetikler.
- **Gate coverage:** ITG kuralları `check_rule_gate_coverage`'a beyan (ADR 0019 §5).
- **İlişkili:** ADR 0006 (reviewer), 0016 (source-drift), 0019 (gate coverage), 0020 (canlı çekirdek).
