---
name: feedback_git-bash-sap-uri-yol-donusumu-msys-no-pathconv
description: "Git Bash, `/sap/bc/adt/...` gibi `/` ile başlayan argümanları Windows yoluna çevirir (`C:/Program Files/Git/sap/...`) → Python'a bozuk URI gider, InvalidURL; `MSYS_NO_PATHCONV=1` ile koş"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cca08bdf-c505-460c-a1ba-8d1635bd8f7c
---

**Olgu (2026-09-13, adt-gateway, canlı DEV salt-okur):** Bash aracı Git Bash (MSYS) çalıştırır.
MSYS, native `.exe`'ye (python dahil) geçen ve `/` ile başlayan argümanları **POSIX yolu sanıp
Windows yoluna çevirir**. Komut satırından verilen `/sap/bc/adt/ddic/ddl/sources/<ad>` argümanı
betiğe `C:/Program Files/Git/sap/bc/adt/...` olarak ulaştı; DDLS okuması `InvalidURL` ile düştü.
SAP'ye hiçbir istek gitmedi. Aynı turdaki heredoc içi (`python - <<'EOF'`) sabit dizgeler
etkilenmedi; yalnız **komut satırı argümanı** bozuldu.

**Why:** Hata SAP'den değil kabuktan gelir, ama "URL geçersiz / obje yok" gibi okunur. Yanlış
teşhise (ör. "URI biçimi yanlış", "obje bulunamadı") açık bir sessiz dönüşümdür.

**How to apply:**
- SAP ADT URI'sini (`/sap/...`) komut satırı argümanı olarak veren her Bash çağrısında komutun
  başına `MSYS_NO_PATHCONV=1` koy, ya da URI'yi betiğin içinde / heredoc'ta sabit ver.
- Alt-ajan brifinde canlı ölçüm varsa bu satırı brife yaz (ajanlar hafızayı görmez).
- `InvalidURL` ya da `C:/Program Files/Git/` içeren bir yol görürsen önce kabuk dönüşümünü şüphelen.

Son-doğrulama: 2026-09-13
Applies-to: Windows + Git Bash (Claude Code Bash aracı); tüm profiller
İlgili: [[feedback_python-yazdigi-liste-crlf-tasir-xargs-sessizce-bosa-koser]] [[feedback_timeout-rg-shim-sessiz-sifir]]
