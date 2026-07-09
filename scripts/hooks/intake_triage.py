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
from pathlib import Path

# B5: otomatik-event işaretleri (task-notification/sistem-bildirimi = kullanıcı-turn'ü DEĞİL).
# Kullanıcı bunları yazmaz → filtrelemek yanlış-negatif üretmez. system-reminder HARİÇ (her promptta).
_AUTO_EVENT_MARKERS = (
    "<task-notification>",
    "This is an automated background-task event",
    "[SYSTEM NOTIFICATION - NOT USER INPUT]",
)

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
# NOT (TR-çekim tuzağı): kapanış \b KULLANMA — "merkez"+\b Türkçe eki ("merkezi") kaçırır.
# Kök-eşleşme (prefix) kullan; kısa/riskli token'ları tekil \b...\b ile koru (\bWM\b, \bHU\b).
_MODULES = [
    ("sd", "SD (Satış-Dağıtım)", re.compile(
        # NOT: çıplak "sipariş" KULLANMA — MM "satın alma siparişi" / PP "üretim siparişi"ne
        # takılıp yanlış-pozitif SD-ipucu üretir. SD-bağlamlı sipariş terimleri kullan.
        r"(\bsatış|\bsatis|\bmüşteri\s+sipariş|\bsipariş\s+kalem|\bsipariş\s+belge|\bteslimat|\bsevkiyat|\bfatura|"
        r"\bsevk\s*emri|\bdelivery\b|\bbilling\b|\bpricing\b|\bfiyatland|\bkondisyon|"
        r"\bVA0\d|\bVL0\d|\bVF0\d|\bVBAK\b|\bVBAP\b|\bLIKP\b|\bLIPS\b|\bVBRK\b|kullanılabilir\s+stok|\bavailability)", re.I)),
    ("mm", "MM (Malzeme Yönetimi)", re.compile(
        r"(\bsatın\s*al|\bsatinal|\bmalzeme\s+belge|\bmal\s+giriş|\bstok\s+hareket|"
        r"\bME2\d|\bMIGO\b|\bMIRO\b|\bsatıcı\s+fatura|\bpurchase\s+order|\bEKKO\b|\bEKPO\b|\bMSEG\b)", re.I)),
    ("ewm", "WM/EWM (Depo Yönetimi)", re.compile(
        # EWM (Extended) + klasik WM (LE-WM) terimleri birlikte — hangi sistem olduğunu
        # ajan canlı-araştırmada belirler (bazı sistemlerde WM, bazılarında EWM).
        r"(\bdepo\s+yönet|\bdepo\s+görev|\bdepo\s+tip|\bhandling\s+unit|\bHU\b|\bhu_ident|\bmal\s+kabul|\byerleştir|"
        r"\btoplama\s+görev|\baktarım\s+emri|\btransfer\s+order|\btransit\s+depo|\bputaway|\bpicking|"
        r"\bstorage\s+(bin|type)|\bwarehouse\s+task|/SCWM/|\blgnum\b|\bEWM\b|\bWM\b|"
        r"\bLTAK\b|\bLTAP\b|\bLT0\d|\bLX\d\d|\bdepo\s+stok|\bdepo\s+birim)", re.I)),
    ("pp", "PP (Üretim Planlama)", re.compile(
        r"(\büretim\s+sipariş|\bimalat|\biş\s+emri|\bplanlı\s+sipariş|\bCO0\d|\büretim\s+planla|"
        r"\bürün\s+ağac|\bBOM\b|\breçete|\byönlendirme|\brouting\b|\bMRP\b|\bproduction\s+order|\bAFKO\b|\bAFPO\b|\bRESB\b)", re.I)),
    ("fi", "FI (Mali Muhasebe)", re.compile(
        r"(\bmuhasebe\s+belge|\bmali\s+belge|\bhesap\s+plan|\bborç|\balacak|\bmizan|\bFB0\d|\bFBL\d|"
        r"\bana\s+hesap|\bBSEG\b|\bBKPF\b|\bGL\s+hesab)", re.I)),
    ("co", "CO (Maliyet-Kontrol)", re.compile(
        r"(\bmaliyet\s+merkez|\bmasraf\s+yer|\biç\s+sipariş|\bmaliyet\s+unsur|\bkarlılık|\bkârlılık|"
        r"\bkâr\s+merkez|\bkar\s+merkez|\bCO-?PA\b|\bcost\s+center|\binternal\s+order|\bKS0\d|\bKO0\d|\bCOEP\b|\bmaliyet\s+analiz)", re.I)),
    ("qm", "QM (Kalite Yönetimi)", re.compile(
        r"(\bkalite\s+yönet|\bkalite\s+kontrol|\bkalite\s+bildirim|\bmuayene\s+lot|\bmuayene\s+plan|"
        r"\binspection\s+lot|\bquality\s+notification|\bkusur|\bred\s+karar|\busage\s+decision|"
        r"\bQA0\d|\bQE\d\d|\bQPMK\b|\bQALS\b|\bQMEL\b)", re.I)),
    ("pm", "PM (Bakım Onarım)", re.compile(
        r"(\bbakım\s+emri|\bbakım\s+sipariş|\barıza\s+bildirim|\bekipman\b|\bfonksiyon\s+yer|"
        r"\bteknik\s+yer|\bmaintenance\s+order|\bmalfunction|\bfunctional\s+location|\bwork\s+order|"
        r"\bIW3\d|\bIW2\d|\bIE0\d|\bEQUI\b|\bAUFK\b|\byedek\s+parça)", re.I)),
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

    # B5 fix (2026-07-09): OTOMATİK-EVENT filtresi — task-notification / sistem-bildirimi
    # gerçek kullanıcı promptu DEĞİL; içeriğinde "geliştir/rapor" geçse de ITG tetiklenmemeli
    # (health-check yanlış-pozitif bulgusu). Bu işaretleri kullanıcı YAZMAZ (harness enjekte
    # eder) → yanlış-negatif riski yok. NOT: <system-reminder> DAHİL EDİLMEZ (her promptta olur).
    if any(mk in prompt for mk in _AUTO_EVENT_MARKERS):
        return 0

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

    # Enjekte edilen metodoloji yolları `core/` junction'ı altındadır; öneksiz yol
    # Read()'te çözülmez (2026-07-09 denetimi). Tek kaynak: utils/inject_paths.py
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # core/scripts
    from utils.inject_paths import core_onekle  # type: ignore
    nudge = core_onekle(nudge)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": nudge,
        }
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
