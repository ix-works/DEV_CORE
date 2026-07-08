---
applies_to: [s4_private]
---
# How-To: VA02-Tarzı Belge Kilidi (App-Level, ortak ZSD000)

> **Ne zaman:** Bir RAP belgesinde (managed veya unmanaged) "açarken kilit var mı
> bak; başkası düzenliyorsa salt-okunur; kaydet/çık'ta bırak" (VA02 davranışı) gerektiğinde.
> Karar gerekçesi + alternatifler (draft, ETag): **ADR 0014**. Bu dosya **uygulama reçetesi**dir.

## 0. Karar: hangi katman?
| Durum | Yaklaşım |
|---|---|
| Sadece veri bütünlüğü yeter | RAP default **ETag** (`etag master`) — açılışta uyarı YOK, çakışma save'de 412. Custom gerekmez. |
| VA02-tarzı "X düzenliyor" + **draft uygun** (FE/V4, "kaldığın yerden devam" değerli) | **Draft** (`with draft` + `lock master total etag`) — framework-managed. |
| VA02-tarzı + **freestyle/V2 / draft'sız pilot** | **App-level kilit (bu doküman)** — ortak `ZSD000_CL_APP_LOCK`. |
| Belge **gerçek SAP belgesi** (VA02 de açar: satış sip., teslimat…) | App-level + **ENQUEUE_READ** (aşağıda §3b). |

## 1. Ortak altyapı (zaten CANLI — yeniden yaratma)
- **Tablo `ZSD000_T_LOCK`**: mandt + lock_object(`ZSD000_E_LOCK_OBJ` CHAR30) + lock_key
  (`ZSD000_E_LOCK_KEY` CHAR10 generic — vbeln/teslimat-no/belnr… tüm 10-char belge
  no'ları; vbeln'e bağlı DEĞİL) [key]; locked_by(syuname), locked_at(timestampl).
- **Sınıf `ZSD000_CL_APP_LOCK`** (CLASS-METHODS): `acquire(iv_object,iv_key)→{acquired,locked_by}`
  · `release(iv_object,iv_key)` · `check(iv_object,iv_key)→locked_by`. `c_timeout_seconds=300` (5 dk).
  COMMIT WORK YOK → RAP action LUW commit eder.
- **lock_object konvansiyonu:** `<PKG>_<DOC>` (örn. `ZSD001_SE`, `ZSD001_SO`). lock_key = belge no.

## 2. Backend — managed BO (örn. ZSD001)
**Instance action** (key = belge anahtarı):
```
// interface BDEF
action AcquireLock;     // DİKKAT: 'Lock'/'Unlock' RAP'te REZERVE → Acquire/Release
action ReleaseLock;
// projection BDEF
use action AcquireLock;  use action ReleaseLock;
```
```abap
" behavior ccimp
METHODS AcquireLock FOR MODIFY IMPORTING keys FOR ACTION DocRoot~AcquireLock.
METHOD AcquireLock.
  LOOP AT keys INTO DATA(k).
    DATA(r) = zsd000_cl_app_lock=>acquire( iv_object = 'ZSD001_SE' iv_key = CONV #( k-DocumentId ) ).
    IF r-acquired = abap_false.
      APPEND VALUE #( %tky = k-%tky ) TO failed-docroot.
      APPEND VALUE #( %tky = k-%tky %msg = new_message_with_text(
        severity = if_abap_behv_message=>severity-error
        text = |Belge { r-locked_by } tarafından düzenleniyor| ) ) TO reported-docroot.
    ENDIF.
  ENDLOOP.
ENDMETHOD.
" ReleaseLock → zsd000_cl_app_lock=>release( ... ).
```
UI: success = kilit alındı; error = kilitli (mesaj `%msg`).

## 3. Backend — unmanaged + gerçek belge (örn. ZSD001 satış siparişi)
### 3a. Static action (param entity ile)
```
// abstract entity ZSD001_I_LOCK_P { IvSalesOrder : vbeln_va; }
static action AcquireLock parameter ZSD001_I_LOCK_P;   // result YOK (success/error semantiği)
static action ReleaseLock parameter ZSD001_I_LOCK_P;
```
### 3b. ENQUEUE_READ — VA02/klasik kilidini gör (KRİTİK)
App-level kilit sadece bizim app'i bilir. Gerçek belge VA02 de açar → **VA02 enqueue'unu oku**:
```abap
METHOD AcquireLock.
  LOOP AT keys INTO DATA(k).
    DATA(lv_vbeln) = CONV vbeln_va( k-%param-IvSalesOrder ).
    DATA lt_enq TYPE STANDARD TABLE OF seqg3. DATA lv_subrc TYPE sy-subrc.
    CALL FUNCTION 'ENQUEUE_READ'
      EXPORTING gclient = sy-mandt gname = 'VBAK' guname = ' '
      IMPORTING subrc = lv_subrc TABLES enq = lt_enq.
    " self-exclusion YOK — aynı kullanıcının kendi VA02 oturumu da app'i bloklar (read_lock'tan
    " gelirse hata). App authoritative; VA02 enqueue'u BAPI-save'i zaten fail ettirir.
    DELETE lt_enq WHERE garg NS lv_vbeln.   " garg vbeln'i içerir (format-güvenli CS filtre)
    IF lt_enq IS NOT INITIAL.
      " → failed + "Belge { lt_enq[1]-guname } tarafından düzenleniyor (VA02)"
    ENDIF.
    " sonra: zsd000_cl_app_lock=>acquire( 'ZSD001_SO', lv_vbeln )  (app↔app)
  ENDLOOP.
ENDMETHOD.
```
- `gname` = kilit objesinin tablosu (satış sip. = `VBAK`, teslimat = `LIKP`…).
- **Sert garanti:** save'de BAPI (örn. `BAPI_SALESORDER_CHANGE`) zaten enqueue alır → çakışmada fail (ETag'in karşılığı).

### 3c. VA02 → bizim app'i görsün (KULLANICI yapar — ADR 0005)
VA02 user-exit'inde (MV45AFZZ / ilgili BAdI) **sadece OKU** (T_LOCK'a YAZMA — cleanup karışmasın):
```abap
" VA02 user-exit (operatör/yetkili ekler — AI standart objeye dokunmaz)
DATA(lv_owner) = zsd000_cl_app_lock=>check( iv_object = 'ZSD001_SO' iv_key = CONV #( vbak-vbeln ) ).
IF lv_owner IS NOT INITIAL.   " self-check YOK — app authoritative; app tutarken VA02 (aynı kullanıcı bile) bloke
  MESSAGE |Sipariş { lv_owner } (uygulama) tarafından düzenleniyor| TYPE 'E'.
ENDIF.
```
Sonuç (4 yön): VA02↔VA02 = SAP enqueue · app↔app = T_LOCK · VA02→app = ENQUEUE_READ ·
app→VA02 = exit check. Kimse diğerinin tablosuna yazmaz → temiz cleanup.

**Çapraz yönde self-exclusion YOK** (app↔VA02): app authoritative → aynı kullanıcı bile çapraz
araçta bloke. **NEDEN: VA02'de ETag YOK.** Managed RAP'ta (ZSD001) ETag iki açılışı save'de
412 ile yakalar → kilit sadece erken-uyarı. VA02'de ETag olmadığından, kilit KAÇARSA BAPI
eski-delta'yı güncel duruma uygular → tutarsızlık (BAPI enqueue yalnız eşzamanlı SAVE'i önler,
stale-read→apply'ı değil). Bu yüzden çapraz kilit **birincil guard** = katı (self-exclusion yok).
**Avantaj: tek kullanıcıyla test edilebilir** — app'te aç→VA02'de aç = hata; VA02'de aç→app'te
aç = read-only. (App↔app ve VA02↔VA02 KENDİ içinde aynı-kullanıcı serbest: T_LOCK
`locked_by=sen→izin` / SAP enqueue.)

## 4. UI (freestyle) — değiştir controller
```js
// onInit: beforeunload → _releaseLockSync ; onExit: _stopHeartbeat + listener kaldır
// route matched: readOnly=true (teyide kadar) → _loadDoc + _acquireLock(id)
_callLock(fn,id){ return new Promise((res,rej)=> oModel.callFunction("/"+fn,{method:"POST",
  urlParameters:{ <KeyParam>: id }, success:()=>res(true), error:rej })); }
_acquireLock(id){ this._callLock("AcquireLock",id)
  .then(()=>{ readOnly=false; lockedBy=""; this._startHeartbeat(id); })
  .catch(e=>{ this._stopHeartbeat(); readOnly=true; lockedBy=this._parseError(e); }); }
_releaseLock(id){ this._stopHeartbeat(); this._callLock("ReleaseLock",id).catch(()=>{}); }
// _releaseLockSync: sync XHR + getSecurityToken() (sendBeacon CSRF set edemez)
// _startHeartbeat: setInterval(120000) → _callLock("AcquireLock",id)  (timeout 5dk'dan kısa)
// onSave success + onNavBack → _releaseLock(id)
```
- `<KeyParam>` = managed'de key alanı (DocumentId), unmanaged'de param (IvSalesOrder).
- View: Save `visible="{= !readOnly }"`, MessageStrip `text="{lockedBy} — salt-okunur" visible="{readOnly}"`,
  tüm edit kontrolleri `editable/enabled="{= !readOnly }"`, tablo `mode="{= readOnly ? 'None':'MultiSelect' }"`.
- List Sil → önce `AcquireLock` (kilitliyse silinmez).

## 5. Senaryolar (S1-S4) ve neden çalışır
| # | Senaryo | Çözüm |
|---|---|---|
| S1 | user-1 içeride, user-2 giriyor | user-2 read-only + uyarı; timer-heartbeat user-1'i korur |
| S2 | aynı kullanıcı başka browser | acquire `sahibi=sen` → izin (ETag/BAPI korur) — S3'ü temiz tutar |
| S3 | kapatıp tekrar giriyor | beforeunload bıraktı; bırakmadıysa `sahibi=sen` → anında girer |
| S4 | kapattı, başkası giriyor | beforeunload anında; çökmede 5dk timeout devralır |

## 6. TUZAKLAR (tekrar etme)
- **`Lock`/`Unlock` RAP'te REZERVE** action adı → `AcquireLock`/`ReleaseLock`.
- **DTEL manuel REST** (create_dataelement.py domain-binding kaybeder → DTEL aktive olmaz):
  v2 XML + `typeKind=domain` + `typeName` (bkz. `scripts/TempScripts/fix_dtel_setype.py`).
- **Abstract entity** `create_cds_view` ile yaratılamaz (SELECT FROM arar) → **ham POST**
  `/sap/bc/adt/ddic/ddl/sources` + LOCK+PUT source (inline-POST boş-source tuzağı).
- **ccimp include push:** `/sap/bc/adt/oo/classes/<cls>/includes/implementations` (`/source/main` YOK).
- **DDIC tablo** inline-POST sadece mandt getirir → tam DDL LOCK+PUT (struct-creation deseni).
- COMMIT WORK handler'da YOK (RAP yasak) — action LUW commit eder.

İlgili: ADR 0014, standards/05 §Lock, [[project_document-lock-app-level]].
