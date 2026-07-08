#!/usr/bin/env python3
"""UserPromptSubmit — INTAKE TRIAGE GATE (ITG) tetik + protokol enjeksiyonu (ADR 0022).

Bir GELİŞTİRME TALEBİ / revizyon / FS-Excel eki / rapor isteği sinyali görülünce, ajanın
izlemesi ZORUNLU olan ITG protokolünü (playbook/intake-triage.md) enjekte eder + varsa
"muhtemel modül" ipucuyla ilgili kural-paketini (playbook/modules/<modül>.md) adıyla söyler.

TASARIM İLKESİ (ADR 0022): hook DURUM TUTMAZ ve SINIFLAMA YAPMAZ. Hook yalnız TETİKLER ve
PROTOKOLÜ DAYATIR; kapsam-sınıflama (S0/S1/S2), konu-çıkarımı ve 3-eksen araştırmayı AJAN
yapar (regex kapsam-büyüklüğünü kestiremez — LLM muhakemesi + isterlere bakış + gerekçe
gerekir). Modül-regex yalnız KABA ipucu ("muhtemel"), kesin sınıf değil.

skill_injector'a KARDEŞ (onu genişletme DEĞİL): skill_injector obje-tipi→checklist işine
odaklı; ITG kapsam+modül+protokol işi — ayrık sorumluluk. Sinyal yoksa sessiz (exit 0).
"""
import json
import re
import sys

# Geliştirme-TALEBİ/NİYETİ sinyali (obje-tipi DEĞİL — iş başlatma/revizyon niyeti).
# Yüksek eşik: gürültü olmasın. skill_injector _STRONG obje-tipini yakalar; bu iş-niyetini.
_INTENT = re.compile(
    r"(\bgeliştir\w*\b|\brevizyon\b|\brevize\b|\bister\w*\b|\btalep\b|\bihtiyac\w*\b|"
    r"\bspec\b|\bFS\b|\bfonksiyonel\s+şartname\b|\byeni\s+(rapor|program|ekran|uygulama|özellik|geliştirme)\b|"
    r"\brapor\s+(iste|yap|çıkar|oluştur|hazırla)\w*|\blisteler?\b\s+(iste|çıkar|ver)\w*|"
    r"\bekle\w*\b|\bdeğiştir\w*\b|\bdüzelt\w*\b|\bböyle\s+bir\s+(özellik|geliştirme|istek)\b|"
    r"\bexcel\b|\.xlsx\b|\bşu\s+alanlar\b|\bkalem\s+listesi\b)",
    re.IGNORECASE,
)

# MODÜL ipucu (KABA — ajana "muhtemel modül", kesin değil). Anahtar kelime → (modül-kodu, etiket).
# Kural-paketi playbook/modules/<kod>.md varsa hook onu adıyla önerir. Şimdilik yalnız SD paketi var;
# diğer modüller ipucu verir ama "paket henüz yok — genel iskeletle ilerle" der.
_MODULES = [
    ("sd", "SD (Satış-Dağıtım)", re.compile(
        r"\b(satış|satis|sipariş|sipiriş|siparis|teslimat|sevkiyat|fatura|faturalandırma|"
        r"sevk\s*emri|müşteri\s+sipariş|delivery|billing|pricing|fiyatland|kondisyon|"
        r"VA0\d|VL0\d|VF0\d|VBAK|VBAP|LIKP|LIPS|VBRK|kullanılabilir\s+stok|availability)\b", re.I)),
    ("mm", "MM (Malzeme Yönetimi)", re.compile(
        r"\b(satın\s*alma|satinalma|satın\s*al|malzeme\s+belge|mal\s+giriş|stok\s+hareket|"
        r"ME2\d|MIGO|MIRO|satıcı\s+fatura|purchase\s+order|EKKO|EKPO|MSEG)\b", re.I)),
    ("fi", "FI (Mali Muhasebe)", re.compile(
        r"\b(muhasebe\s+belge|mali\s+belge|hesap\s+plan|borç|alacak|mizan|FB0\d|FBL\d|"
        r"ana\s+hesap|BSEG|BKPF|GL\s+hesab)\b", re.I)),
]

# Kural-paketi FİİLEN mevcut modüller (dosya core'da → junction'la görünür).
# İçerik katmanı büyüdükçe (T-trigger) bu küme genişler.
_HAZIR_PAKETLER = {"sd"}


def main() -> int:
    try:
        # stdin'i HAM byte olarak UTF-8 decode et — Windows'ta sys.stdin cp1252'ye düşüp
        # Türkçe karakterli prompt'ları ('satış','geliştir') bozar → regex kaçırır (smoke-test bulgusu).
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
    except Exception:
        return 0
    prompt = data.get("prompt", "") or ""

    if not _INTENT.search(prompt):
        return 0  # geliştirme-niyeti sinyali yok → sessiz

    # Muhtemel modül ipuçları (birden çok eşleşebilir — hepsini söyle, ajan seçsin)
    ipuclari = []
    for kod, etiket, rx in _MODULES:
        if rx.search(prompt):
            if kod in _HAZIR_PAKETLER:
                ipuclari.append(f"{etiket} → OKU: playbook/modules/{kod}.md")
            else:
                ipuclari.append(f"{etiket} → kural-paketi henüz YOK; genel iskeletle ilerle "
                                f"(birikim oluşursa T-trigger ile playbook/modules/{kod}.md açılır)")
    modul_notu = ""
    if ipuclari:
        modul_notu = " Muhtemel modül(ler) (KABA ipucu — kesin sınıfı SEN belirle): " + "; ".join(ipuclari) + "."

    nudge = (
        "[Geliştirme talebi tespit edildi] INTAKE TRIAGE GATE — protokolü İZLE "
        "(OKU: playbook/intake-triage.md; atlanamaz):\n"
        "(1) KAPSAM sınıfla — S0 nokta-düzeltme / S1 lokalize / S2 kapsamlı — ve GEREKÇESİNİ yaz.\n"
        "(2) Modül + iş-tipini belirle; modül kural-paketi varsa OKU.\n"
        "(3) İsterleri tara → her anlamlı alan/gereksinim hangi domain-konusunu tetikliyor ÇIKAR "
        "(ör. 'kullanılabilir stok' → availability check/ATP).\n"
        "(4) 3-EKSEN araştır: (a) domain bilgisi (docs-MCP/resmi kaynak) "
        "(b) CANLI sistem/ilişkili kod (adt_where_used/package_contents/adt_get — reuse+blast-radius) "
        "(c) kurumsal hafıza/prior-art (memory + playbook + SESSION_NOTES — 'benzerini yaptık mı'). "
        "Z-obje hatırlanıyorsa CANLI DOĞRULA (hafıza=hipotez, canlı=otorite; ADR 0016).\n"
        "(5) KANITLI değerlendir — reuse + mevcutla tutarlılık + geçmiş-ders + risk. TAHMİN YASAK.\n"
        "(6) Kapsam-orantılı: S0 hafif geç (soru/artefakt yok); S1 hedefli soru; "
        "S2 tam zincir → intake-artefaktı + EARS/INVEST DoR + MUTABAKAT, sonra build."
        + modul_notu
    )

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": nudge,
        }
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
