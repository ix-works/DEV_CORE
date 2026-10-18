#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""frontmatter_lint.py — Claude Code tanım dosyalarının YAML frontmatter'ı GEÇERLİ mi?

TÜKETİCİLER (tek kaynak — kopya tanım AÇILMAZ):
  · `scripts/git-hooks/core_precommit.py` — DEV_CORE'a giriş (staged + `--all`/CI);
    ENGEL sınıfı commit'i bloklar (exit 1), UYARI sınıfı yalnız basılır.
  · `scripts/ix_doctor.py` katman 4 — kurulu makinede `.claude/{agents,commands,skills,rules}`
    + `claude-local/` taraması; her şey WARN'dır (düzeltme önerisiyle, otomatik düzeltme YOK).

NEDEN VAR (ölçüldü 2026-10-18, çekirdek PR #347): dört ajan tanımının tırnaksız
`description:` değerinde `: ` vardı (geçersiz YAML). Claude Code dosya LF iken bunu tolere
etti, CRLF iken (Windows checkout, `* text=auto`) ajanı UYARISIZ düşürdü: 7 ajandan 3'ü
listelendi. Linux CI'da dosyalar LF olduğu için hiçbir katman görmedi.

MEKANİZMA (statik okuma, Claude Code 2.1.302 ikilisi; ÖLÇÜLEN vakayla tutarlı):
  frontmatter önce `Bun.YAML.parse` ile ayrıştırılır; başarısız olursa YEDEK yol her satırı
  `/^([a-zA-Z_-]+):\\s+(\\S.*)$/` ile eşleyip özel karakterli (`{}[]*&#!|>%@` + backtick
  ya da `: `) değeri çift tırnağa alır ve yeniden dener. JS'te `.` `\\r`'yi eşlemez ⇒ CRLF
  dosyada yedek yol HİÇBİR satırı tırnaklayamaz ⇒ ayrıştırma başarısız ⇒ frontmatter `{}`.
  Ajan için bu "tanım yok" (sessiz düşme); `paths:`'li kural için `paths` yok ⇒ kural
  KOŞULSUZ yüklenir — ÖLÇÜLDÜ 2026-10-18 (2.1.302, `claude -p` + InstructionsLoaded logu,
  2×2 matris): tırnaksız `paths: **/*.abap` LF → `path_glob_match`, CRLF → `session_start`
  (globs yok, koşulsuz); tırnaklı `paths: "**/*.abap"` LF ve CRLF → `path_glob_match`.
  Yani LF'te "çalışıyor" görünen geçersiz
  YAML, satır sonuna bağlı bir saatli bombadır; kapı geçersizliği satır sonundan BAĞIMSIZ
  yakalar.

İKİ DÜZEY:
  Düzey 1 (bağımlılıksız, HER ZAMAN): hedefli tarama — ölçülmüş/okunmuş sınıflar.
  Düzey 2 (PyYAML import edilebilirse): `yaml.safe_load`. Kurulu değilse KAPSAM beyanı
  "ÖLÇÜLEMEDİ" der (çekirdek PyYAML'a bağımlı değildir; CI onu kurmaz).
  ⚠ PyYAML Claude Code'un ayrıştırıcısı (Bun.YAML) DEĞİLDİR, vekildir. Claude Code'un baştaki
  sekme girintisini iki boşluğa çevirdiği bilindiği için (yedek yol) düzey 2 aynısını yapar.

SEVİYE (lider kararı 2026-10-18, seçenek B):
  ENGEL — `: ` · ` #` (değerin gerisi YORUM olur, sessiz kırpma) · `#` ile başlayan değer
          (değer boş olur) · kapanmayan tırnak · frontmatter yok (zorunlu türde) /
          kapanmıyor · değerde `---` · ayrılmış karakterle başlama · çift tırnakta geçersiz
          kaçış · düzey-2 ayrıştırma hatası.
  UYARI — `*`/`&` ile başlayan tırnaksız düz değer (çekirdeğin 2026-10-18 öncesi
          `paths: **/*.abap, …` biçimi; çekirdek kuralları artık tırnaklı): LF'te yedek
          ayrıştırıcı kurtarır, CRLF'te kural koşulsuz yüklenir (ölçüm yukarıda). Seviye
          lider kararıyla UYARI (B) — proje/eski kopyalar için. Aynı satır düzey 2'ye
          NÖTRLENEREK verilir ⇒ PyYAML'ın o satırdaki hatası ENGEL'e dönüşmez.
"""
from __future__ import annotations

import re
from pathlib import PurePath
from typing import NamedTuple

try:
    import yaml as _yaml  # type: ignore
    YAML_TAM = True
except Exception:  # noqa: BLE001 — ImportError + bozuk kurulum aynı sonuç: düzey 2 ÖLÇÜLEMEDİ
    _yaml = None
    YAML_TAM = False

ENGEL = "ENGEL"
UYARI = "UYARI"


class Bulgu(NamedTuple):
    satir: int          # dosyadaki 1-tabanlı satır no (git'in saydığıyla aynı)
    seviye: str         # ENGEL | UYARI
    sorun: str
    oneri: str


TURLER = ("agents", "commands", "skills", "rules")

KAPSAM_BEYANI = (
    "bakilan: tanim dosyasinin frontmatter blogu (agents/<ad>.md · skills/<ad>/SKILL.md "
    "zorunlu; commands/**.md · rules/**.md varsa) — duzey 1: ust-duzey `anahtar: deger` "
    "satirlari + duz deger devam satirlari + tirnakli degerler + her satirda `---`; "
    "duzey 2: PyYAML safe_load (kuruluysa). BAKILMAYAN: zorunlu anahtarlar (name/description) "
    "· yinelenen anahtar · ic ice harita/liste degerleri duzey 1'de (yalniz duzey 2) · "
    "Claude Code'un kendi ayristiricisi (Bun.YAML) — PyYAML vekildir · govde (frontmatter "
    "disi) icerik")

_ANAHTAR = re.compile(r"^([A-Za-z0-9_][\w .-]*?)\s*:(?:[ \t]+(.*))?$")
_BLOK_BASLIK = re.compile(r"^[|>](?:[+-]?[1-9]?|[1-9][+-])?(?:[ \t]+#.*)?$")
_AYRILMIS_BAS = ("@", "`", "%", ",", "]", "}")
_GECERLI_KACIS = set("0abt\tnvfre \"/\\N_LP")
_HEX_UZUNLUK = {"x": 2, "u": 4, "U": 8}

_UYARI_YILDIZ = ("tirnaksiz deger '{c}' ile basliyor — gecersiz YAML; Claude Code LF dosyada "
                 "yedek ayristiriciyla kurtarir, CRLF dosyada kurtaramaz (paths'li kural "
                 "KOSULSUZ yuklenir — olculdu 2026-10-18)")


def tanim_turu(yol) -> tuple[str, bool] | None:
    """(tür, frontmatter_zorunlu) ya da None. Son yol parçalarına bakar; önek serbesttir
    (`claude/` · `.claude/` · `claude-local/`). Önek kısıtı ÇAĞIRANIN işidir."""
    p = PurePath(str(yol).replace("\\", "/"))
    parca = p.parts
    if p.suffix.lower() != ".md" or len(parca) < 2:
        return None
    if parca[-2] == "agents":
        return "agents", True
    if len(parca) >= 3 and parca[-1] == "SKILL.md" and parca[-3] == "skills":
        return "skills", True
    for tur in ("commands", "rules"):            # alt klasör serbest (ad alanı)
        if tur in parca[:-1]:
            return tur, False
    return None


def _cift_tirnakla(anahtar: str, deger: str) -> str:
    kacisli = deger.replace("\\", "\\\\").replace('"', '\\"')
    return f'{anahtar}: "{kacisli}"'


def _tirnak_tara(metin: str, tur: str) -> tuple[int, str | None]:
    """`metin` açılış tırnağından SONRAKİ içerik. (kapanış_sonrası_indeks | -1, kaçış_hatası)."""
    i = 0
    while i < len(metin):
        c = metin[i]
        if tur == "'":
            if c == "'":
                if i + 1 < len(metin) and metin[i + 1] == "'":
                    i += 2
                    continue
                return i + 1, None
        else:
            if c == "\\":
                if i + 1 >= len(metin):
                    return -1, None
                k = metin[i + 1]
                if k == "\n":
                    i += 2
                    continue
                if k in _HEX_UZUNLUK:
                    n = _HEX_UZUNLUK[k]
                    hx = metin[i + 2:i + 2 + n]
                    if len(hx) != n or not all(h in "0123456789abcdefABCDEF" for h in hx):
                        return -1, f"\\{k} kacisi {n} onaltilik hane ister"
                    i += 2 + n
                    continue
                if k not in _GECERLI_KACIS:
                    return -1, f"gecersiz kacis '\\{k}'"
                i += 2
                continue
            if c == '"':
                return i + 1, None
        i += 1
    return -1, None


def _duz_deger(anahtar: str, deger: str, no: int, out: list[Bulgu]) -> bool:
    """Tırnaksız düz değer. True = devam satırları bu skalerin parçası olabilir."""
    oneri = _cift_tirnakla(anahtar, deger)
    if deger[0] == "#":
        out.append(Bulgu(no, ENGEL, f"'{anahtar}' degeri '#' ile basliyor — YORUM sayilir, "
                                    f"deger BOS (null) olur", oneri))
        return False
    if deger[0] in "*&":
        out.append(Bulgu(no, UYARI, f"'{anahtar}': " + _UYARI_YILDIZ.format(c=deger[0]), oneri))
        return False
    if deger.startswith(_AYRILMIS_BAS) or deger in ("-", "?") or deger.startswith(("- ", "? ")):
        out.append(Bulgu(no, ENGEL, f"'{anahtar}' degeri ayrilmis karakterle basliyor "
                                    f"('{deger[0]}') — gecersiz YAML", oneri))
        return False
    if deger[0] in "|>":
        if not _BLOK_BASLIK.match(deger):
            out.append(Bulgu(no, ENGEL, f"'{anahtar}' blok skaler basligi gecersiz ('{deger[:6]}') "
                                        f"— '|'/'>' sonrasinda metin olamaz", oneri))
        return False
    if deger[0] in "[{!":
        return False                              # akış / etiket: düzey 2'nin işi
    if ": " in deger or deger.endswith(":"):
        out.append(Bulgu(no, ENGEL, f"'{anahtar}': tirnaksiz degerde ': ' (iki nokta + bosluk) "
                                    f"— gecersiz YAML", oneri))
    if " #" in deger or "\t#" in deger:
        out.append(Bulgu(no, ENGEL, f"'{anahtar}': tirnaksiz degerde ' #' — sonrasi YORUM "
                                    f"sayilir, deger SESSIZCE kirpilir", oneri))
    return True


def _cerceve(metin: str) -> tuple[list[str], int | None, list[Bulgu] | None]:
    """(satırlar, kapanış_indeksi, erken_bulgu). Satırlar LF'e normalize, BOM soyulur."""
    if metin.startswith("﻿"):
        metin = metin[1:]
    satirlar = metin.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not satirlar or satirlar[0].rstrip() != "---":
        return satirlar, None, None
    for i in range(1, len(satirlar)):
        if satirlar[i].rstrip() == "---":
            return satirlar, i, None
    return satirlar, None, [Bulgu(1, ENGEL, "frontmatter acildi ama '---' satiriyla KAPANMIYOR "
                                            "— govdenin tamami frontmatter sanilir",
                                  "frontmatter'in sonuna yalniz '---' iceren bir satir ekle")]


def bulgular(metin: str, zorunlu: bool) -> list[Bulgu]:
    """Frontmatter bulguları (satır sırasıyla). Boş liste = bakılan yüzeyde bulgu yok."""
    satirlar, kapanis, erken = _cerceve(metin)
    if erken is not None:
        return erken
    if kapanis is None:
        if zorunlu:
            return [Bulgu(1, ENGEL, "frontmatter YOK — ilk satir '---' degil; bu tanim "
                                    "Claude Code'da YUKLENMEZ",
                          "dosyayi '---' / name: … / description: … / '---' ile baslat")]
        return []

    out: list[Bulgu] = []
    notrle: dict[int, str] = {}                   # düzey 2'ye nötrlenerek verilecek satırlar
    devam = None                                  # devam satırı alabilecek düz skalerin anahtarı
    i = 1
    while i < kapanis:
        satir = satirlar[i]
        no = i + 1
        if "---" in satir:
            out.append(Bulgu(no, ENGEL, "frontmatter satirinda '---' — Claude Code frontmatter'i "
                                        "ilk '---' dizisinde KAPATIR (satir icinde bile); gerisi "
                                        "govdeye kayar (statik okuma 2.1.302, OLCULMEDI)",
                             "degerde '---' yazma (ornegin ' — ' kullan)"))
        govde = satir.strip()
        if not govde or govde.startswith("#"):
            i += 1
            continue
        if satir[0] in " \t":
            if devam is not None:
                if ": " in govde or govde.endswith(":"):
                    out.append(Bulgu(no, ENGEL, f"'{devam}' devam satirinda ': ' — gecersiz YAML",
                                     "degeri tek satira al ve cift tirnakla"))
                if " #" in govde or "\t#" in govde:
                    out.append(Bulgu(no, ENGEL, f"'{devam}' devam satirinda ' #' — sonrasi YORUM, "
                                                f"deger SESSIZCE kirpilir",
                                     "degeri tek satira al ve cift tirnakla"))
            elif govde.startswith(("- *", "- &")):
                out.append(Bulgu(no, ENGEL, f"liste ogesi '{govde[2]}' ile basliyor — gecersiz "
                                            f"YAML; Claude Code'un yedek ayristiricisi liste "
                                            f"ogesini tirnaklamaz",
                                 f'- "{govde[2:].strip()}"'))
            i += 1
            continue
        devam = None
        if govde.startswith("-"):
            i += 1                                # sütun-0 dizi: düzey 2'nin işi
            continue
        m = _ANAHTAR.match(satir)
        if not m:
            out.append(Bulgu(no, ENGEL, "satir 'anahtar: deger' biciminde degil — gecersiz YAML",
                             "satiri 'anahtar: deger' yap ya da sil"))
            i += 1
            continue
        anahtar, deger = m.group(1), (m.group(2) or "").rstrip()
        if not deger:
            i += 1
            continue
        if deger[0] in "\"'":
            # Çok satırlı tırnaklı değer geçerlidir → kapanışı sonraki satırlarda da ara.
            parca, j = deger[1:], i
            while True:
                son, hata = _tirnak_tara(parca, deger[0])
                if hata or son != -1 or j + 1 >= kapanis:
                    break
                j += 1
                parca += "\n" + satirlar[j]
            if hata:
                out.append(Bulgu(no, ENGEL, f"'{anahtar}' cift tirnakli degerde {hata} — "
                                            f"gecersiz YAML",
                                 "ters egik cizgiyi ikile (\\\\) ya da degeri tek tirnaga al"))
            elif son == -1:
                out.append(Bulgu(no, ENGEL, f"'{anahtar}' degerinin tirnagi ({deger[0]}) "
                                            f"KAPANMIYOR", "tirnagi kapat"))
            else:
                kalan = parca[son:].split("\n", 1)[0]
                if kalan.strip() and not re.match(r"^[ \t]+#", kalan):
                    out.append(Bulgu(j + 1, ENGEL, f"'{anahtar}' kapanan tirnaktan SONRA metin "
                                                   f"var — gecersiz YAML",
                                     "degerin tamamini tek tirnak cifti icine al"))
            i = j + 1
            continue
        once = len(out)
        if _duz_deger(anahtar, deger, no, out):
            devam = anahtar
        if any(b.seviye == UYARI for b in out[once:]):
            notrle[i] = _cift_tirnakla(anahtar, deger)
        i += 1

    if YAML_TAM and not any(b.seviye == ENGEL for b in out):
        govde_satir = [notrle.get(k, satirlar[k]) for k in range(1, kapanis)]
        # Claude Code yedek yolu baştaki sekmeyi 2 boşluğa çevirir — vekil de aynısını yapar.
        metin2 = re.sub(r"(?m)^\t+", lambda mm: "  " * len(mm.group(0)), "\n".join(govde_satir))
        try:
            veri = _yaml.safe_load(metin2)
            if veri is not None and not isinstance(veri, dict):
                out.append(Bulgu(2, ENGEL, "frontmatter bir harita degil (liste ya da tek deger)",
                                 "frontmatter 'anahtar: deger' satirlarindan olusmali"))
        except Exception as exc:  # noqa: BLE001 — yaml.YAMLError + beklenmeyen tip hataları
            mark = getattr(exc, "problem_mark", None)
            satir_no = (mark.line + 2) if mark is not None else 2
            sorun = getattr(exc, "problem", None) or str(exc).split("\n", 1)[0]
            out.append(Bulgu(satir_no, ENGEL, f"PyYAML ayristiramadi: {sorun}",
                             "degeri cift tirnakla (ic tirnak/ters egik cizgiyi kacir)"))
    out.sort(key=lambda b: b.satir)
    return out


def satir_sonu_notu(metin: str) -> str:
    """ENGEL bulgusunun yanına konacak etki notu — satır sonuna göre."""
    if "\r\n" in metin:
        return ("dosya CRLF: Claude Code'un yedek ayristiricisi calismaz, tanim SESSIZCE "
                "duser (ajanda olculdu 2026-10-18)")
    return ("dosya LF: Claude Code bugun yedek ayristiriciyla tolere edebilir; Windows "
            "checkout'unda (CRLF) tanim SESSIZCE duser")


def dosya_bulgulari(yol, metin: str) -> list[Bulgu] | None:
    """Kolaylık: tanım dosyası değilse None, ise bulgu listesi."""
    tur = tanim_turu(yol)
    if tur is None:
        return None
    return bulgular(metin, tur[1])


def duzey2_durumu() -> str:
    return ("AÇIK (PyYAML safe_load)" if YAML_TAM
            else "ÖLÇÜLEMEDİ (PyYAML kurulu değil — yalnız düzey 1 bağımlılıksız tarama koştu)")
