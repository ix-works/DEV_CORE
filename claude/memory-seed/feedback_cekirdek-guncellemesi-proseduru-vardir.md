---
name: feedback_cekirdek-guncellemesi-proseduru-vardir
description: "\"core güncelle\" bir komut değil PROSEDÜRDÜR — pull tek başına yetmez; team_setup zinciri, overlay ezme kapısı ve makine-lokal yüzeyler (izin tabanı, gh, git baseline) atlanırsa kurulum çalışır GÖRÜNÜR ama farklı davranır"
metadata: 
  node_type: memory
  type: feedback
---

Kullanıcı *"core güncelle"* dediğinde `git -C core pull` koşup bitirme. Güncellemenin
kanonik prosedürü çekirdektedir: **`core/playbook/howto-cekirdek-guncelleme.md`**
(slash komutu: `/core-guncelle`). Önce onu oku, adımları oradan yürüt.

**Üç kolay kaçırılan nokta — üçü de sessiz:**

1. **Çalışma ağacı kirliyse pull ETME.** Çekirdek paylaşılmıştır; oradaki yerel bir yama
   pull ile çakışır ya da kaybolur. Önce `git -C core status --short`, kirliyse kullanıcıya sor.
2. ⛔ **`team_setup.py` overlay ezme kapısına (T2.5) takılırsa `return 1` ile çıkar ve
   plugin kurulumu + memory tohumunu HİÇ koşmaz.** *"team_setup çalıştı"* yeterli değil —
   çıktının sonunda `team_setup TAMAM` satırını gör. `FARK VAR` yazıyorsa fark raporunu
   kullanıcıya göster, sonra `--overlay-onayli` ile tekrar koş. ⭐ Kapı **her turda
   ateşlemez** (overlay kaynakları değişmediyse hiç çıkmaz) — baştan `--overlay-onayli`
   ile başlama, o bayrak fark raporunu görmeden ezme iznidir.
3. **`team_setup` makine-lokal yüzeyleri ÜRETMEZ:** `~/.claude/settings.json` izin tabanı
   (şablon `core/claude/user-settings.template.json`, **elle** birleştirilir) · `gh`
   kurulumu/auth · git global baseline. Tam liste `core/ONBOARDING.md` §0a.

**Why:** İki makine arasında ölçülen farkların tamamı bu üçüncü maddedeydi — çekirdek
dosyaları birebir aynıydı. Yani *"core güncel"* olması *"kurulum eş"* demek değildir; eksik
yüzey kurulumu bozmaz, **sessizce farklı davranmasını** sağlar (izin tabanı yoksa rutin
komutlar onay sorar ve otonom adımlar yarıda kalır). 2. madde ise zincirin ortasında sessiz
kesilmesidir: tohum hiç koşmaz ama kullanıcı "güncelledim" sanır.

**How to apply:** Prosedürü izle, sonunda **ölç**: `parity_probe` ile önce/sonra karşılaştır,
`run_all_validators` + `ix_doctor` FAIL'siz olsun, oturumu **kapat-aç** (memory/kurallar/izinler
oturum başında yüklenir). Atlanan her adımı nedeniyle raporla; ölçemediğini `ÖLÇÜLEMEDİ: <sebep>`
diye yaz — *ölçülemedi ≠ temiz*. İlgili:
[[feedback_tuketici-klonunda-core-degisikligi-prosedur]] · [[feedback_adt-infra-degisikligi-once-uyar-onay]]
