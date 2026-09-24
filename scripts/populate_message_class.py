#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Production tool: Populate SAP Message Class (MSAG) via ADT REST.

Çözüm bulundu: 2026-05-13. Detaylı analiz için bkz. SAP_ADT_PLAYBOOK.md §27.

KRİTİK BULGU: Bu sistemde (S/4 1909) mesaj sınıfı PUT'unda `If-Match` header'ı
göndermek ENQUEUE lock bug'ını tetikliyor (handler kendi enqueue check'ini
yapıp self-collision veriyor). `If-Match`'siz PUT ile precondition check
bypass ediliyor ve mesajlar başarıyla yazılıyor.

WINNING PATTERN:
  1. CSRF fetch (X-CSRF-Token: Fetch)
  2. LOCK parent class (_action=LOCK, accessMode=MODIFY, corrNr, stateful)
  3. PUT /sap/bc/adt/messageclass/{name}
     - Query: corrNr, lockHandle, accessMode=MODIFY
     - Headers: X-CSRF-Token, X-sap-adt-sessiontype: stateful,
                Content-Type: application/vnd.sap.adt.mc.messageclass+xml
     - !!!! If-Match GÖNDERME !!!!
     - Body: <mc:messageClass>...<mc:messages mc:msgno=... mc:msgtext=...>...
  4. UNLOCK (try/finally garantili) + clear_enqueue_lock safety net

XML ŞEMA (kritik nokta — element ve attribute adları SAP'nin döndüğü formatta):
  - <mc:messages> ÇOĞUL (singular değil!)
  - mc:msgno (number değil!)
  - mc:msgtext (text değil!)
  - mc:selfexplainatory (SAP'de typo — "selfExplanatory" değil!)

Kullanım:
    python populate_message_class.py \\
        --name ZSD001 \\
        --package ZSD000_CLC \\
        --transport <TRANSPORT> \\
        --description "Sevkemri Mesaj Sinifi" \\
        --responsible <SAP_USER> \\
        --messages-csv messages.csv \\
        --cwd <PROJECT_ROOT>

    messages.csv format (UTF-8, ilk satır header):
        msgno,msgtext,selfexplainatory
        001,"Müşteri bulunamadı",false
        002,"Tarih boş olamaz",true

⛔ CSV'DEN ÇIKARMAK MESAJI SİLMEZ (ölçüldü 2026-09-24, s4_private 2025): tam PUT gövdede
OLMAYAN mesaja dokunmaz — SAP'nin "listede olmayanı sil" döngüsü kaynakta YORUM SATIRINDA
(CL_ADT_MC_RES_CONTROLLER=>DO_UPDATE). Silme yalnız gövdedeki `<mc:deletedmessages>`
koleksiyonuyla olur. Playbook: adt-message-class.md §27.5.

SİLME KİPİ (--delete) — mesaj sınıfından TEK TEK mesaj silme:
    python populate_message_class.py --name ZSD001_MSG --transport <TRANSPORT> \\
        --delete 006,011 [--dry-run] [--body-out <dosya.xml>] --cwd <PROJECT_ROOT>

  Akış: canlı GET (sınıf + tüm mesajlar, CANLI öznitelikleriyle) → korumalar → gövde
  (kalan mesajlar birebir + her silinen için `<mc:deletedmessages mc:msgno="NNN"/>`)
  → `populate()` yazma akışı (CSRF → LOCK → KİLİT ALTINDA canlıyı YENİDEN OKU; ÖNCE'den
    farklıysa PUT GÖNDERİLMEZ → PUT, If-Match YOK → UNLOCK finally)
  → ÖNCE/SONRA KAPISI (canlıyı yeniden okur: giden küme == silme kümesi, kalanlar birebir).
  Çıkış kodu: 0 = silindi + kapı tuttu · 2 = YAZMADAN durduruldu (girdi/koruma/okuma/
              kilit altında canlı değişmiş) · 1 = yazma başarısız (PUT gönderilmedi ya da
              reddedildi) · 3 = yazıldı ama kapı TUTMADI ya da ÖLÇÜLEMEDİ (PUT gönderildikten
              sonra istisna dahil — canlıyı elle doğrula).
  Korumalar (hepsi yazmadan ÖNCE): numara tam 3 hane ve BOŞ DEĞİL (boş msgno SAP'de
  `000`'ı siler) · her numara canlıda VAR · liste boş değil · tekrar yok · en az bir
  mesaj KALIR (tüm sınıfı silmek bu aracın işi değil) · sınıfın master dili = oturum dili
  (farklıysa SAP yalnız o dilin T100 satırını siler — yarım silme).
"""

import argparse
import csv
import re
import sys
import io
import tempfile
import urllib3
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# sap_adt_lib path
_PLUGIN_PATH = r'C:\Users\<USER>\.config\opencode\ntt-marketplace\plugins\abaper\skills\sap-adt\scripts'
sys.path.insert(0, _PLUGIN_PATH)

from sap_adt_lib import set_explicit_working_dir, SAPADTClient


# T100-TEXT alan uzunlugu = CHAR 73 (DD03L'den olculdu 2026-08-20).
# ⛔ Uzunluk denetimi YOKTU: script CSV'den okudugu metni oldugu gibi XML govdesine
# koyup PUT ediyordu. Iki sonuc da kotu: ya cagri duser, ya SAP metni SESSIZCE KIRPAR.
# Kirpilan mesaj ekranda YARIM CUMLEDIR ve "onayli metin buydu" diye kimse suphelenmez
# -> sessiz-veri-bozan sinifi. Olculmus vaka (2026-08-20, bir mesaj sinifi turu): onayli
# 143 metnin 14'u siniri asiyordu (en uzunu 94 karakter); arac sayesinde DEGIL, CSV
# ureticisinin kendi kontrolu sayesinde yakalandi -- yani o turda tesadufen kurtuldu.
#
# ⚠ KARAKTER sayilir, BAYT degil: T100-TEXT Unicode kernel'de 73 KARAKTERdir. Bayt
# olcen bir guard (`len(s.encode('utf-8'))`) diakritikli dilde yanlis-pozitif uretir
# (18 karakterlik bir metin 20 bayt olabilir). Python `len()` code-point sayar = dogru.
T100_TEXT_MAXLEN = 73


class MesajMetniUzunError(ValueError):
    """CSV'de T100-TEXT sinirini asan satir(lar) var — YAZMA BASLAMADAN durdurulur."""


class MesajSatiriEksikError(ValueError):
    """CSV'de YARIM doldurulmus satir(lar) var — YAZMA BASLAMADAN durdurulur.

    Iki yon de sessiz-veri-bozandi (bkz. asagidaki kok-sebep notu):
    bos `msgno` -> satir `000` olarak YAZILIYORDU · bos `msgtext` -> satir
    sessizce DUSURULUYORDU. Ikisi de ayni sinifin ornegi: "yazarin mesaj diye
    yazdigi satir, haber verilmeden baska bir seye donusur ya da yok olur".
    """


def load_messages_from_csv(csv_path: Path) -> list:
    """CSV oku → [(msgno, msgtext, selfexplainatory), ...]

    ⛔ FAIL-CLOSED (iki guard, ikisi de CSRF/LOCK/PUT'a HIC gitmeden):
      · `msgtext` T100-TEXT sinirini (73 karakter) asiyorsa -> `MesajMetniUzunError`
      · satir YARIM doldurulmussa (`msgno` XOR `msgtext` bos) -> `MesajSatiriEksikError`
    Guard'lar bilerek BURADA (uretim noktasinda) duruyor: `main()`e konsaydi bu
    fonksiyonu dogrudan import eden bir cagiran onlari atlardi ("gate'lenmemis
    kural ~ kuralsiz"). `--dry-run` da ayni kapiya carpar; amac zaten yazmadan
    once yakalamaktir.

    Tamamen bos satir (her iki alan da bos) dolgu sayilir ve sessizce atlanir.
    """
    messages = []
    asanlar = []
    eksikler = []
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            satir_no = reader.line_num          # CSV'deki GERCEK satir (header dahil)
            # ⛔ HAM alan — `zfill(3)`ten ONCE okunur. Sebep: `''.zfill(3)` == `'000'`
            # ve `'000'` GECERLI bir mesaj numarasidir (serbest metin tasiyicisi).
            # Olculdu 2026-08-29: 7 gercek `messages.csv`nin 5'i satir 2'de ACIKCA
            # `000` tanimliyor. zfill SONRASINA bakan bir kontrol "bos" ile "acikca
            # 000" ayrimini YAPAMAZ -> ya sessiz ezme surer ya 5 paket kirilir.
            ham_no = str(row.get('msgno', '') or '').strip()
            msgtext = str(row.get('msgtext', '') or '').strip()
            self_exp = str(row.get('selfexplainatory', 'false')).strip().lower()
            if self_exp not in ('true', 'false'):
                self_exp = 'false'

            if not ham_no and not msgtext:
                # TAMAMEN bos satir = dolgu/ayirac; sessizce atlanir. Yazarin bir
                # mesaj kastettigine dair HIC iz yok -> yarim satirdan farki budur.
                continue
            if not ham_no or not msgtext:
                eksikler.append((satir_no, ham_no, msgtext))
                continue                        # <- FAIL-CLOSED: satir YAZILMAZ

            msgno = ham_no.zfill(3)             # zero-pad to 3 digits
            if len(msgtext) > T100_TEXT_MAXLEN:
                asanlar.append((satir_no, msgno, len(msgtext), msgtext))
            messages.append((msgno, msgtext, self_exp))

    if eksikler:
        # Uzunluk guard'indan ONCE: yarim satir YAPISAL bir CSV hatasidir.
        # TUM ihlaller tek seferde (#37'nin tasarim karari — tur tur kesif YOK).
        detay = '\n'.join(
            (f'    satir {sn}: msgno BOS — msgtext="{mt[:60]}"'
             if not mn else
             f'    satir {sn}: msgtext BOS — msgno={mn}')
            for sn, mn, mt in eksikler
        )
        raise MesajSatiriEksikError(
            f'{len(eksikler)} CSV satiri YARIM doldurulmus '
            f'— HICBIRI yazilmadi (fail-closed).\n'
            f'  ⚠ Yazilsaydi: bos `msgno` satiri `000` olarak yazilir ve `000`\n'
            f'    (serbest metin tasiyicisi) SESSIZCE EZILIRDI; bos `msgtext`\n'
            f'    satiri ise haber verilmeden DUSURULURDU.\n'
            f'  Eksik satirlar:\n{detay}\n'
            f'  Cozum: satiri tamamla, ya da mesaj degilse CSV\'den tumden cikar.\n'
            f'  (Not: `000` GECERLI bir numaradir — acikca yazildiginda kabul edilir.)'
        )

    if asanlar:
        # TUM ihlaller tek seferde raporlanir: yazar CSV'yi tek turda duzeltsin,
        # her kosumda bir sonrakini kesfetmesin.
        detay = '\n'.join(
            f'    satir {sn}: msgno={mn} — {uz} karakter '
            f'(+{uz - T100_TEXT_MAXLEN}) — "{mt[:T100_TEXT_MAXLEN]}…{mt[T100_TEXT_MAXLEN:]}"'
            for sn, mn, uz, mt in asanlar
        )
        raise MesajMetniUzunError(
            f'{len(asanlar)} mesaj metni T100-TEXT sinirini (CHAR {T100_TEXT_MAXLEN}) asiyor '
            f'— HICBIRI yazilmadi (fail-closed).\n'
            f'  ⚠ Yazilsaydi SAP ya cagriyi duserdi ya metni SESSIZCE kirpardi.\n'
            f'  Asan satirlar ("…" = kirpilma noktasi):\n{detay}\n'
            f'  Cozum: CSV\'deki metinleri {T100_TEXT_MAXLEN} karaktere indir '
            f'(kisaltma ONAYLI metni degistirir — metin sahibine dogrulat).'
        )
    return messages


# `"` + satır/sekme karakterleri: XML öznitelik değeri NORMALLEŞTİRMESİ çıplak TAB/LF/CR'yi
# boşluğa çevirir ⇒ kaçışlanmazsa gönderilen metin canlıdakinden FARKLI okunur (öz-denetim
# yanıltıcı "öznitelik farkı" ile dururdu).
_ATTR_KACIS = {'"': '&quot;', '\t': '&#9;', '\n': '&#10;', '\r': '&#13;'}


def attr_escape(metin: str) -> str:
    """XML ÖZNİTELİK değeri kaçışı: `& < >` + ÇİFT TIRNAK.

    ⛔ Çıplak `xml_escape()` `"` işaretini KAÇIRMAZ (ölçüldü 2026-09-24:
    `escape('a"b')` -> `'a"b'`). Öznitelikler çift tırnakla yazıldığı için tırnaklı
    bir mesaj metni gövdeyi BOZUYORDU. Silme kipi canlı metni olduğu gibi geri
    gönderir ⇒ tırnaklı tek bir canlı mesaj bütün silmeyi düşürürdü.
    """
    return xml_escape(metin, _ATTR_KACIS)


def build_xml(name: str, description: str, package: str, responsible: str,
              messages: list, language: str = 'TR', deleted=()) -> str:
    """Build full message class XML with embedded messages.

    `messages` öğeleri `(msgno, msgtext, selfexplainatory)` ya da — silme kipinde,
    CANLI öznitelikleri korumak için — `(msgno, msgtext, selfexplainatory, documented)`.
    3'lü öğede `documented` eskisi gibi `"false"` yazılır (CSV kipi DEĞİŞMEDİ).

    `deleted`: silinecek numaralar → her biri için `<mc:deletedmessages mc:msgno="NNN"/>`,
    `<mc:messages>` satırlarından SONRA (SAP ST `ST_ADT_MESSAGE_CLASS` sırası).
    """
    satirlar = []
    for m in messages:
        n, t, s = m[0], m[1], m[2]
        d = m[3] if len(m) > 3 else 'false'
        satirlar.append(
            f'  <mc:messages mc:msgno="{n}" mc:msgtext="{attr_escape(t)}" '
            f'mc:selfexplainatory="{s}" mc:documented="{d}" adtcore:name=""/>')
    satirlar += [f'  <mc:deletedmessages mc:msgno="{n}"/>' for n in deleted]
    msgs_xml = '\n'.join(satirlar)

    return f'''<?xml version="1.0" encoding="utf-8"?>
<mc:messageClass adtcore:responsible="{responsible}"
                 adtcore:masterLanguage="{language}"
                 adtcore:name="{name}"
                 adtcore:type="MSAG/N"
                 adtcore:description="{attr_escape(description)}"
                 adtcore:language="{language}"
                 xmlns:mc="http://www.sap.com/adt/MessageClass"
                 xmlns:adtcore="http://www.sap.com/adt/core">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{package.lower()}"
                      adtcore:type="DEVC/K"
                      adtcore:name="{package}"/>
{msgs_xml}
</mc:messageClass>'''


def populate(client: SAPADTClient, name: str, description: str, package: str,
             responsible: str, transport: str, messages: list,
             dry_run: bool = False, language: str = 'TR', sap_client: str = '100',
             xml_payload: str = None, kilit_sonrasi_kontrol=None,
             iz: dict = None) -> bool:
    """
    Lock, PUT messages, unlock. Returns True on success.

    `kilit_sonrasi_kontrol` (silme kipi): LOCK alındıktan SONRA, PUT'tan ÖNCE çağrılır;
    `None` dışında bir metin dönerse PUT GÖNDERİLMEZ (UNLOCK yine `finally`'de) ve metin
    `iz['kilit_sonrasi_red']`e yazılır. Neden: ÖNCE okuması kilitten önce yapılır; arada
    başkası kalan bir mesajın metnini değiştirirse gövde onu ESKİ metne geri çevirirdi
    (SAP metni farklı mesajı günceller) ve kapı bayat ÖNCE'yle kıyaslayıp "tuttu" derdi.
    `iz['put_gonderildi']` PUT isteği başlamadan hemen önce True olur — sonraki bir
    istisnada çağıran "yazılmış olabilir" ile "hiç yazılmadı"yı ayırt edebilsin.

    `language` / `sap_client` varsayılanları eski SABİT değerlerdir (CSV kipi değişmedi);
    silme kipi sınıfın master dilini ve oturumun client'ını açıkça verir.
    `xml_payload` verilirse gövde üretilmez, olduğu gibi gönderilir (silme kipi —
    gövde canlıdan kurulup `silme_govdesi_dogrula` ile doğrulanmış olmalı).
    """
    name = name.upper()
    object_url = f'/sap/bc/adt/messageclass/{name.lower()}'

    # Build payload
    if xml_payload is None:
        xml_payload = build_xml(name, description, package, responsible, messages,
                                language=language)

    if dry_run:
        print('\n=== DRY-RUN — XML preview (first 1500 chars) ===')
        print(xml_payload[:1500])
        return True

    # 1. Fresh CSRF
    client._invalidate_csrf_cache()
    r = client.session.get(
        client.url + '/sap/bc/adt/discovery',
        params={'sap-client': sap_client, 'sap-language': language},
        headers={'X-CSRF-Token': 'Fetch'},
        verify=False, timeout=15
    )
    csrf = r.headers.get('X-CSRF-Token', '')
    if not csrf:
        print('[FAIL] CSRF token alınamadı')
        return False
    print(f'[OK] CSRF: {csrf[:24]}...')

    handle = None
    success = False
    try:
        # 2. LOCK
        print(f'[INFO] LOCK {name}...')
        lock_resp = client.session.post(
            client.url + object_url,
            params={'_action': 'LOCK', 'accessMode': 'MODIFY', 'corrNr': transport},
            headers={
                'X-CSRF-Token': csrf,
                'X-sap-adt-sessiontype': 'stateful',
                'Accept': 'application/*,application/vnd.sap.as+xml;'
                          'dataname=com.sap.adt.lock.result',
            },
            verify=False, timeout=15
        )
        if lock_resp.status_code != 200:
            print(f'[FAIL] LOCK status: {lock_resp.status_code}')
            print(f'       Body: {lock_resp.text[:500]}')
            return False
        m = re.search(r'<LOCK_HANDLE[^>]*>([^<]+)</LOCK_HANDLE>', lock_resp.text)
        handle = m.group(1) if m else None
        if not handle:
            print('[FAIL] LOCK_HANDLE çıkarılamadı')
            return False
        print(f'[OK] Lock handle: {handle[:16]}...')

        # 2b. (silme kipi) kilit ALTINDA canlı yeniden okunur — TOCTOU koruması
        if kilit_sonrasi_kontrol is not None:
            red = kilit_sonrasi_kontrol()
            if red:
                if iz is not None:
                    iz['kilit_sonrasi_red'] = red
                print(f'[FAIL] Kilit sonrası kontrol TUTMADI — PUT GÖNDERİLMEDİ: {red}')
                return False

        # 3. PUT — winning pattern: NO If-Match!
        print(f'[INFO] PUT {len(messages)} message(s)...')
        if iz is not None:
            iz['put_gonderildi'] = True
        r = client.session.put(
            client.url + object_url,
            params={'corrNr': transport, 'lockHandle': handle,
                    'accessMode': 'MODIFY'},
            headers={
                'X-CSRF-Token': csrf,
                'Content-Type': 'application/vnd.sap.adt.mc.messageclass+xml; '
                                'charset=utf-8',
                'Accept': '*/*',
                'X-sap-adt-sessiontype': 'stateful',
                'sap-client': sap_client,
                'sap-language': language,
                # !!! NO If-Match — kritik! !!!
            },
            data=xml_payload.encode('utf-8'),
            verify=False, timeout=60
        )
        if r.status_code in (200, 201, 204):
            print(f'[OK] PUT başarılı — Status: {r.status_code}')
            success = True
        else:
            print(f'[FAIL] PUT status: {r.status_code}')
            print(f'       Body: {r.text[:800]}')

    finally:
        # 4. Guaranteed UNLOCK
        if handle:
            try:
                u = client.session.post(
                    client.url + object_url,
                    params={'_action': 'UNLOCK', 'lockHandle': handle},
                    headers={
                        'X-CSRF-Token': csrf,
                        'X-sap-adt-sessiontype': 'stateful',
                    },
                    verify=False, timeout=10
                )
                print(f'[OK] UNLOCK: {u.status_code}')
            except Exception as e:
                print(f'[WARN] UNLOCK error: {e}')

        # Safety net — clear any lingering enqueue locks
        try:
            client.clear_enqueue_lock(object_url=object_url)
            print('[OK] Enqueue cleanup tamamlandı')
        except Exception as e:
            print(f'[WARN] clear_enqueue_lock skipped: {e}')

    return success


def verify(client: SAPADTClient, name: str) -> list:
    """GET class and return list of (msgno, msgtext) tuples."""
    object_url = f'/sap/bc/adt/messageclass/{name.lower()}'
    r = client.session.get(
        client.url + object_url,
        headers={'Accept': 'application/vnd.sap.adt.mc.messageclass+xml'},
        params={'sap-language': 'TR'},
        verify=False
    )
    if r.status_code != 200:
        return []
    return re.findall(
        r'<mc:messages mc:msgno="([^"]*)" mc:msgtext="([^"]*)"',
        r.text
    )


# ═══════════════════════════ SİLME KİPİ (--delete) ═══════════════════════════
# Kanıt (2026-09-24, s4_private 2025, DEV): 229 mesajlı sınıfta önce 1 (229→228, giden
# tam {006}) sonra 16 mesaj tek PUT'ta silindi (→212); kalanlar metin/bayrak birebir,
# T100U 229→212, silinenin uzun metni (DOKHL) gitti, sınıfın `changedAt`'i DEĞİŞMEDİ.
# SAP kaynağı: DO_UPDATE → `tt_deletedmessage` döngüsü → cl_adt_message_class_api=>
# delete( iv_number = <nr> ) — `iv_number` DAİMA verilir ⇒ "tüm sınıfı sil" dalı bu
# yoldan ULAŞILAMAZ. Ayrıntı + tuzaklar: playbook/adt-message-class.md §27.5-§27.6.

_NS_MC = '{http://www.sap.com/adt/MessageClass}'
_NS_CORE = '{http://www.sap.com/adt/core}'
MSGNO_RE = re.compile(r'^\d{3}$')

# Önce/sonra kapısının KAPSAM BEYANI (core §7): "kapı tuttu" yalnız aşağıdaki
# yüzey için doğrudur. Bakılmayan yüzey "temiz" DEĞİL, ÖLÇÜLMEDİ'dir.
KAPSAM_BAKILAN = (
    'ADT GET /sap/bc/adt/messageclass/<ad> (master dilde) — silmeden ÖNCE ve SONRA: '
    'mesaj numarası kümesi + her kalan mesajın msgtext / selfexplainatory / documented değeri',
)
KAPSAM_BAKILMAYAN = (
    'T100 (SQL) — özellikle master dil DIŞINDAKİ çeviri satırları: ÖLÇÜLMEDİ',
    'T100U (değişiklik kaydı) · DOKHL/DOKTL (uzun metin): ÖLÇÜLMEDİ '
    '(SAP uzun metni transport kaydı AÇMADAN siler — başka sisteme taşımada DOĞRULANMADI)',
    'E071 (transport nesne satırı): ÖLÇÜLMEDİ — tek mesaj silmesinin görev satırı '
    'bu araçla kanıtlanmaz',
    "sınıfın changedAt değeri: BİLEREK kullanılmadı (silme onu GÜNCELLEMİYOR — ölçüldü)",
)


class SilmeGirdiHatasi(ValueError):
    """Silme listesi / canlı durum korumalarından biri tuttu — YAZMADAN durdurulur."""


def sinif_xml_ayristir(metin: str) -> dict:
    """Sınıf GET yanıtı → {'name','masterLanguage','language','description',
    'responsible','package','messages': {msgno: (msgtext, selfexp, documented)}}.

    Öznitelik SIRASINDAN bağımsızdır (ElementTree) — `verify()`'ın regex'i sıraya
    bağlıdır; silme kararı ona dayandırılmaz. Metinler kaçışı çözülmüş hâldedir.
    """
    kok = ET.fromstring(metin)
    if kok.tag != _NS_MC + 'messageClass':
        raise SilmeGirdiHatasi(f'beklenmeyen kök eleman: {kok.tag}')
    paket = kok.find(_NS_CORE + 'packageRef')
    mesajlar = {}
    for m in kok.findall(_NS_MC + 'messages'):
        no = m.get(_NS_MC + 'msgno', '')
        if no in mesajlar:
            raise SilmeGirdiHatasi(f'canlı yanıtta mükerrer msgno: {no!r}')
        mesajlar[no] = (m.get(_NS_MC + 'msgtext', ''),
                        m.get(_NS_MC + 'selfexplainatory', 'false'),
                        m.get(_NS_MC + 'documented', 'false'))
    return {
        'name': kok.get(_NS_CORE + 'name', ''),
        'masterLanguage': kok.get(_NS_CORE + 'masterLanguage', ''),
        'language': kok.get(_NS_CORE + 'language', ''),
        'description': kok.get(_NS_CORE + 'description', ''),
        'responsible': kok.get(_NS_CORE + 'responsible', ''),
        'package': paket.get(_NS_CORE + 'name', '') if paket is not None else '',
        'messages': mesajlar,
        'deleted_in_response': len(kok.findall(_NS_MC + 'deletedmessages')),
    }


def silme_listesi_ayristir(ham: str) -> list:
    """'006,011 , 071' → ['006','011','071']. Normalizasyon YOK (zfill yok, bilerek).

    ⛔ Boş öğe (`"006,,011"`) ve 3 haneli olmayan öğe (`"6"`) REDDEDİLİR: SAP'de boş
    `msgno` ilkel değeri `000`dır ve `000`ı SİLER (DO_UPDATE'teki
    `lv_msg_number EQ 000 AND msgnr EQ 000` dalı). `"6"`yı `"006"`ya çevirmek de
    yazarın niyetini TAHMİN etmektir.
    """
    if ham is None:
        raise SilmeGirdiHatasi('silme listesi verilmedi')
    ogeler = [o.strip() for o in ham.split(',')]
    hatali = [o for o in ogeler if not MSGNO_RE.match(o)]
    if not ham.strip() or hatali:
        raise SilmeGirdiHatasi(
            'silme listesinde geçersiz numara(lar): '
            + ', '.join(repr(o) for o in (hatali or [ham]))
            + ' — her numara TAM 3 hane rakam olmalı (örn. 006). Boş numara SAP\'de '
              '`000`ı siler; bu yüzden yazılmaz.')
    tekrar = sorted({o for o in ogeler if ogeler.count(o) > 1})
    if tekrar:
        raise SilmeGirdiHatasi(f'silme listesinde tekrar eden numara(lar): {tekrar}')
    return ogeler


def silme_planla(canli: dict, silinecek: list, oturum_dili: str) -> list:
    """Korumaları uygular; KALAN mesajları [(no, metin, selfexp, documented), ...] döner.

    TÜM ihlaller tek seferde raporlanır (CSV guard'larıyla aynı tasarım kararı).
    """
    hatalar = []
    mesajlar = canli['messages']
    if not silinecek:
        hatalar.append('silme listesi BOŞ')
    for no in silinecek:
        if not MSGNO_RE.match(no or ''):
            hatalar.append(f'geçersiz numara {no!r} (tam 3 hane rakam; boş numara 000\'ı siler)')
    yok = [no for no in silinecek if no not in mesajlar]
    if yok:
        hatalar.append(f'canlıda OLMAYAN numara(lar): {yok} — sınıf {canli["name"]} '
                       f'içinde {len(mesajlar)} mesaj var')
    kalan = [(no,) + mesajlar[no] for no in sorted(mesajlar) if no not in set(silinecek)]
    if silinecek and not yok and not kalan:
        hatalar.append('silme listesi sınıfın TÜM mesajlarını kapsıyor — en az bir mesaj '
                       'kalmalı (tüm sınıfı silmek bu aracın işi değil)')
    ml = (canli.get('masterLanguage') or '').upper()
    od = (oturum_dili or '').upper()
    if not ml or ml != od:
        hatalar.append(
            f'master dil ({ml or "?"}) ≠ oturum dili ({od or "?"}) — SAP silmeyi gövde dili '
            f'oturum diliyle AYNI değilse yalnız o dilin T100 satırında yapar (yarım silme). '
            f'Oturumu master dilde aç (.conn_adt dil satırı).')
    if hatalar:
        raise SilmeGirdiHatasi('SİLME DURDURULDU — hiçbir şey yazılmadı:\n  - '
                               + '\n  - '.join(hatalar))
    return kalan


def silme_govdesi(canli: dict, silinecek: list, kalan: list) -> str:
    """Canlı başlık + kalan mesajlar (CANLI öznitelikleriyle) + deletedmessages."""
    # `responsible` build_xml'de KAÇIŞSIZ yazılır (CSV kipi davranışı — varsayılan yer
    # tutucusu değişmesin diye); canlıdan gelen değer burada kaçışlanır.
    return build_xml(canli['name'], canli['description'], canli['package'],
                     attr_escape(canli['responsible']), kalan,
                     language=canli['masterLanguage'], deleted=silinecek)


def silme_govdesi_dogrula(govde: str, canli: dict, silinecek: list) -> list:
    """Gönderilecek gövdeyi GERİ AYRIŞTIRIR; hata listesi döner (boş = tamam).

    Ölçtüğü değişmezler: deletedmessages sayısı/numaraları == silme listesi, hiçbirinin
    msgno'su boş değil, hepsi son `<mc:messages>`'tan SONRA; gövdedeki mesajlar ==
    canlı − silinecek ve her kalan canlı öznitelikleriyle BİREBİR (metin değişirse SAP
    o mesajı "güncelle" listesine alır — istenmeyen yan etki).
    """
    hatalar = []
    try:
        kok = ET.fromstring(govde)
    except ET.ParseError as e:
        return [f'gövde XML olarak ayrıştırılamadı: {e}']
    dm = [d.get(_NS_MC + 'msgno') for d in kok.findall(_NS_MC + 'deletedmessages')]
    if dm != list(silinecek):
        hatalar.append(f'deletedmessages {dm} ≠ silme listesi {list(silinecek)}')
    if any(not d for d in dm):
        hatalar.append('boş msgno taşıyan deletedmessages var (SAP 000\'ı silerdi)')
    cocuklar = list(kok)
    son_msg = max((i for i, c in enumerate(cocuklar) if c.tag == _NS_MC + 'messages'),
                  default=-1)
    ilk_del = min((i for i, c in enumerate(cocuklar) if c.tag == _NS_MC + 'deletedmessages'),
                  default=len(cocuklar))
    if ilk_del < son_msg:
        hatalar.append('deletedmessages <mc:messages> satırlarından ÖNCE geliyor')
    gv = sinif_xml_ayristir(govde)['messages']
    beklenen = {no: v for no, v in canli['messages'].items() if no not in set(silinecek)}
    if gv != beklenen:
        eksik = sorted(set(beklenen) - set(gv))
        fazla = sorted(set(gv) - set(beklenen))
        farkli = sorted(n for n in set(gv) & set(beklenen) if gv[n] != beklenen[n])
        hatalar.append(f'gövdedeki mesajlar canlı−silinecek ile aynı değil: '
                       f'eksik={eksik} fazla={fazla} öznitelik-farkı={farkli}')
    return hatalar


def silme_kapisi(once: dict, sonra: dict, silinecek: list) -> list:
    """ÖNCE/SONRA kapısı — hata listesi döner (boş = tuttu). `changedAt` KULLANILMAZ."""
    hatalar = []
    o, s = once['messages'], sonra['messages']
    giden = set(o) - set(s)
    yeni = set(s) - set(o)
    if giden != set(silinecek):
        hatalar.append(f'giden küme {sorted(giden)} ≠ silme kümesi {sorted(silinecek)} '
                       f'(silinmeyen: {sorted(set(silinecek) - giden)} · beklenmeden giden: '
                       f'{sorted(giden - set(silinecek))})')
    if yeni:
        hatalar.append(f'sonradan beliren numara(lar): {sorted(yeni)}')
    if len(s) != len(o) - len(silinecek):
        hatalar.append(f'kalan sayı {len(s)} ≠ önce {len(o)} − {len(silinecek)}')
    degisen = sorted(n for n in set(o) & set(s) if o[n] != s[n])
    if degisen:
        hatalar.append('kalan mesajlarda öznitelik değişimi: ' + '; '.join(
            f'{n}: {o[n]} → {s[n]}' for n in degisen[:10])
            + (f' (+{len(degisen) - 10})' if len(degisen) > 10 else ''))
    return hatalar


def kapsam_beyani_bas() -> None:
    print('\n[KAPSAM] Bakılan:')
    for s in KAPSAM_BAKILAN:
        print(f'  + {s}')
    print('[KAPSAM] BAKILMAYAN (ÖLÇÜLMEDİ — "kapı tuttu" bunları KAPSAMAZ):')
    for s in KAPSAM_BAKILMAYAN:
        print(f'  - {s}')


def sinif_oku(client: SAPADTClient, name: str, language: str = None):
    """Canlı sınıf GET → (http_durum, gövde_metni). Yazma YOK."""
    params = {'sap-language': language} if language else {}
    r = client.session.get(
        client.url + f'/sap/bc/adt/messageclass/{name.lower()}',
        headers={'Accept': 'application/vnd.sap.adt.mc.messageclass+xml'},
        params=params, verify=False, timeout=60)
    return r.status_code, r.text


def mesaj_sil(client: SAPADTClient, name: str, transport: str, silme_ham: str,
              dry_run: bool = False, body_out: str = None,
              package: str = None) -> int:
    """--delete kipinin tamamı. Çıkış kodu: 0 / 2 (yazmadan durdu) / 1 / 3 (docstring)."""
    name = name.upper()
    oturum_dili = getattr(client, 'language', None) or ''
    oturum_client = getattr(client, 'client', None) or ''
    try:
        silinecek = silme_listesi_ayristir(silme_ham)
    except SilmeGirdiHatasi as e:
        print(f'[FAIL] {e}')
        return 2
    if not dry_run and not transport:
        print('[FAIL] --transport verilmedi — LOCK için gerekli; hiçbir şey yazılmadı.')
        return 2
    if not dry_run and not oturum_client:
        print('[FAIL] oturumun sap-client değeri çözülemedi (.conn_adt) — hiçbir şey yazılmadı.')
        return 2

    durum, metin = sinif_oku(client, name, oturum_dili or None)
    if durum != 200:
        print(f'[FAIL] canlı sınıf okunamadı (HTTP {durum}) — ÖLÇÜLEMEDİ, hiçbir şey yazılmadı.')
        return 2
    try:
        once = sinif_xml_ayristir(metin)
        if once['name'].upper() != name:
            raise SilmeGirdiHatasi(f'yanıttaki sınıf adı {once["name"]!r} ≠ {name!r}')
        if package and once['package'].upper() != package.upper():
            raise SilmeGirdiHatasi(f'--package {package} ≠ sınıfın canlı paketi '
                                   f'{once["package"]} — yanlış sınıf olabilir')
        kalan = silme_planla(once, silinecek, oturum_dili)
    except (SilmeGirdiHatasi, ET.ParseError) as e:
        print(f'[FAIL] {e}')
        return 2
    print(f'[INFO] {name}: canlıda {len(once["messages"])} mesaj · silinecek '
          f'{len(silinecek)} {silinecek} · kalacak {len(kalan)} · master dil '
          f'{once["masterLanguage"]}')
    for no in silinecek:
        print(f'  - {no}: {once["messages"][no][0][:90]}')

    govde = silme_govdesi(once, silinecek, kalan)
    hatalar = silme_govdesi_dogrula(govde, once, silinecek)
    if hatalar:
        print('[FAIL] üretilen gövde öz-denetimi TUTMADI — yazılmadı:\n  - '
              + '\n  - '.join(hatalar))
        return 2
    hedef = Path(body_out) if body_out else \
        Path(tempfile.gettempdir()) / f'msag_delete_{name.lower()}.xml'
    hedef.parent.mkdir(parents=True, exist_ok=True)
    with open(hedef, 'w', encoding='utf-8', newline='\n') as f:
        f.write(govde)
    print(f'[OK] gövde yazıldı + öz-denetim tuttu: {hedef}')

    if dry_run:
        print('[DRY-RUN] SAP\'ye YAZILMADI.')
        kapsam_beyani_bas()
        return 0

    def _kilit_alti_yeniden_oku():
        # TOCTOU: ÖNCE kilitten önce okundu. Arada kalan bir mesajın metni değiştiyse
        # gövde onu ESKİ metne geri çevirir (SAP metni farklı mesajı günceller) ve kapı
        # bayat ÖNCE'yle kıyasladığı için bunu GÖREMEZ ⇒ kilit ALTINDA yeniden oku.
        try:
            d2, m2 = sinif_oku(client, name, oturum_dili or None)
            if d2 != 200:
                return f'kilit altında yeniden okuma HTTP {d2} — değişmediği ölçülemedi'
            simdi = sinif_xml_ayristir(m2)
        except Exception as e:  # noqa: BLE001 — ölçülemeyen = yazılmaz
            return f'kilit altında yeniden okuma başarısız ({type(e).__name__}: {e})'
        fark = [a for a in ('description', 'responsible', 'package', 'masterLanguage')
                if simdi[a] != once[a]]
        o, n = once['messages'], simdi['messages']
        fark_no = sorted(k for k in set(o) | set(n) if o.get(k) != n.get(k))
        if fark or fark_no:
            return (f'canlı sınıf ÖNCE okumasından beri DEĞİŞTİ (başlık: {fark} · mesaj: '
                    f'{fark_no[:10]}) — gövde bu değişikliği geri alırdı; yeniden koş')
        return None

    iz = {'put_gonderildi': False, 'kilit_sonrasi_red': None}
    try:
        ok = populate(client=client, name=name, description=once['description'],
                      package=once['package'], responsible=once['responsible'],
                      transport=transport, messages=kalan, dry_run=False,
                      language=once['masterLanguage'], sap_client=oturum_client,
                      xml_payload=govde,
                      kilit_sonrasi_kontrol=_kilit_alti_yeniden_oku,
                      iz=iz)
    except Exception as e:  # noqa: BLE001 — ağ/HTTP istisnası; UNLOCK populate'in finally'sinde
        if iz['put_gonderildi']:
            print(f'[FAIL] PUT gönderildikten sonra istisna ({type(e).__name__}: {e}) — '
                  f'silme GERÇEKLEŞMİŞ OLABİLİR, ÖLÇÜLEMEDİ: canlıyı elle doğrula.')
            kapsam_beyani_bas()
            return 3
        print(f'[FAIL] PUT gönderilmeden istisna ({type(e).__name__}: {e}) — yazılmadı.')
        return 1
    if iz['kilit_sonrasi_red']:
        print('[FAIL] kilit altında canlı değişmiş bulundu — PUT GÖNDERİLMEDİ, hiçbir şey '
              'yazılmadı.')
        return 2
    if not ok:
        print('\n[FAIL] silme yazması başarısız (ayrıntı yukarıda).')
        return 1

    try:
        durum, metin = sinif_oku(client, name, oturum_dili or None)
    except Exception as e:  # noqa: BLE001
        print(f'[FAIL] SONRA okuması istisna verdi ({type(e).__name__}: {e}) — PUT 200 döndü '
              f'ama silme ÖLÇÜLEMEDİ: canlıyı elle doğrula.')
        kapsam_beyani_bas()
        return 3
    if durum != 200:
        print(f'[FAIL] SONRA okunamadı (HTTP {durum}) — PUT 200 döndü ama silme '
              f'ÖLÇÜLEMEDİ. "PUT 200" silindiği anlamına GELMEZ (tam PUT no-op da 200 döner).')
        kapsam_beyani_bas()
        return 3
    try:
        sonra = sinif_xml_ayristir(metin)
    except (SilmeGirdiHatasi, ET.ParseError) as e:
        print(f'[FAIL] SONRA yanıtı ayrıştırılamadı ({e}) — silme ÖLÇÜLEMEDİ.')
        kapsam_beyani_bas()
        return 3
    hatalar = silme_kapisi(once, sonra, silinecek)
    if hatalar:
        print('[FAIL] ÖNCE/SONRA KAPISI TUTMADI:\n  - ' + '\n  - '.join(hatalar))
        kapsam_beyani_bas()
        return 3
    print(f'[OK] KAPI TUTTU: {len(once["messages"])} → {len(sonra["messages"])} · giden tam '
          f'{sorted(silinecek)} · kalan {len(sonra["messages"])} mesaj öznitelikleriyle birebir')
    kapsam_beyani_bas()
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Populate SAP message class with messages via ADT REST '
                    '(uses winning pattern from SAP_ADT_PLAYBOOK §27)'
    )
    parser.add_argument('--name', required=True,
                        help='Message class name (e.g. ZSD001)')
    # --package/--transport/--description/--messages-csv CSV (yazma) kipinde ZORUNLU;
    # zorunluluk asagida kipe gore denetlenir (silme kipi bunlari CANLIDAN alir).
    parser.add_argument('--package',
                        help='Package name (e.g. ZSD000_CLC); --delete ile verilirse '
                             'canli paketle eslesmeli')
    parser.add_argument('--transport',
                        help='Transport request (e.g. <TRANSPORT>)')
    parser.add_argument('--description',
                        help='Class description')
    parser.add_argument('--responsible', default='<SAP_USER>',
                        help='Responsible user (default: <SAP_USER>)')
    parser.add_argument('--messages-csv',
                        help='CSV file: msgno,msgtext,selfexplainatory')
    parser.add_argument('--cwd',
                        help='Working dir with .conn_adt')
    parser.add_argument('--dry-run', action='store_true',
                        help='Build XML and print, do not POST')
    parser.add_argument('--verify-only', action='store_true',
                        help='Skip write, just GET and list current messages')
    parser.add_argument('--delete', metavar='NNN[,NNN...]',
                        help='SILME KIPI: virgulle ayrilmis 3 haneli mesaj numaralari '
                             "(orn. 006,011). CSV'den cikarmak SILMEZ — silmenin tek yolu "
                             'bu kip (playbook adt-message-class.md §27.5)')
    parser.add_argument('--body-out',
                        help='--delete: gonderilecek govdenin yazilacagi dosya '
                             '(varsayilan: sistem temp dizini)')
    args = parser.parse_args()

    if args.delete is not None and args.messages_csv:
        parser.error('--delete ile --messages-csv birlikte verilemez (iki ayri kip)')
    if args.delete is None and not args.verify_only:
        eksik = [f'--{a.replace("_", "-")}' for a in
                 ('package', 'transport', 'description', 'messages_csv')
                 if not getattr(args, a)]
        if eksik:
            parser.error('CSV (yazma) kipinde zorunlu: ' + ', '.join(eksik))

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    client = SAPADTClient()

    if args.delete is not None:
        return mesaj_sil(client, args.name, args.transport, args.delete,
                         dry_run=args.dry_run, body_out=args.body_out,
                         package=args.package)

    if args.verify_only:
        msgs = verify(client, args.name)
        print(f'\n{args.name} içinde {len(msgs)} mesaj var:')
        for nr, txt in msgs:
            print(f'  {nr}: {txt[:80]}')
        return 0

    csv_path = Path(args.messages_csv)
    if not csv_path.exists():
        print(f'[FAIL] CSV bulunamadı: {csv_path}')
        return 1

    try:
        messages = load_messages_from_csv(csv_path)
    except (MesajMetniUzunError, MesajSatiriEksikError) as e:
        # Traceback yerine okunur teshis: hata CSV'nin icerigindedir, kodun degil.
        print(f'[FAIL] {e}')
        return 1
    print(f'[INFO] {csv_path.name} → {len(messages)} mesaj yüklendi')
    if not messages:
        print('[FAIL] CSV boş')
        return 1

    # PRE-state
    if not args.dry_run:
        before = verify(client, args.name)
        print(f'[INFO] Mevcut mesaj sayısı: {len(before)}')
        # UYARI (davranis DEGISMEDI): tam PUT gövdede OLMAYAN mesajı SİLMEZ (ölçüldü
        # 2026-09-24). "CSV nihai liste" varsayımıyla çıkarılan mesaj canlıda KALIR.
        yalniz_canli = sorted({nr for nr, _ in before} - {m[0] for m in messages})
        if yalniz_canli:
            print(f"[UYARI] Canlıda olup CSV'de OLMAYAN {len(yalniz_canli)} mesaj: "
                  f'{yalniz_canli[:20]}{" ..." if len(yalniz_canli) > 20 else ""}')
            print("        CSV'den çıkarmak mesajı SİLMEZ — bu mesajlar canlıda kalacak. "
                  'Silmek için: --delete NNN[,NNN...] (playbook adt-message-class.md §27.5)')

    ok = populate(
        client=client,
        name=args.name,
        description=args.description,
        package=args.package,
        responsible=args.responsible,
        transport=args.transport,
        messages=messages,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        return 0

    if not ok:
        print('\n[FAIL] Mesaj yazma başarısız oldu')
        return 1

    # POST-state
    after = verify(client, args.name)
    print(f'\n[OK] Final mesaj sayısı: {len(after)}')
    if len(after) >= len(messages):
        print(f'[OK] Tüm {len(messages)} mesaj başarıyla yazıldı')
        return 0
    else:
        print(f'[WARN] Beklenen {len(messages)}, gelen {len(after)} — '
              'CSV içeriğini kontrol et')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
