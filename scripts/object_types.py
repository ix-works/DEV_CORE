#!/usr/bin/env python3
"""
SAP ABAP Object Types Helper
Centralized mapping of object types to URLs and metadata
"""
import sys

# Windows konsolu/pipe'i cp1252'dir: non-ASCII basmak UnicodeEncodeError ile COKER
# (exit 1 -> gercek FAIL'den ayirt edilemez). C-ENC-01 / check_console_utf8.py
for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

# Object type mappings
OBJECT_TYPES = {
    'class': {
        'adt_type': 'CLAS/OC',
        'url_path': 'oo/classes',
        'xml_namespace': 'class',
        'description': 'ABAP Class',
        'supports_create': True,
        'file_extension': '.clas.abap'
    },
    'interface': {
        'adt_type': 'INTF/OI',
        'url_path': 'oo/interfaces',
        'xml_namespace': 'interface',
        'description': 'ABAP Interface',
        'supports_create': True,
        'file_extension': '.intf.abap'
    },
    'program': {
        'adt_type': 'PROG/P',
        'url_path': 'programs/programs',
        'xml_namespace': 'program',
        'description': 'ABAP Program (Report)',
        'supports_create': True,
        'file_extension': '.prog.abap'
    },
    'include': {
        'adt_type': 'PROG/I',
        'url_path': 'programs/includes',
        'xml_namespace': 'include',
        'description': 'ABAP Include',
        'supports_create': True,
        'file_extension': '.prog.abap'
    },
    'functiongroup': {
        'adt_type': 'FUGR/F',
        'url_path': 'functions/groups',
        'xml_namespace': 'functiongroup',
        'description': 'Function Group',
        'supports_create': True,
        'file_extension': '.fugr.abap'
    },
    # GENERIC URL YOK -- `url_path: None` BILINCLIDIR (Q221/Q228; canli olculdu
    # 2026-09-03, DEV, salt-GET):
    #     /sap/bc/adt/functions/modules/<fm>                           -> HTTP 404 (26 bayt)
    #     /sap/bc/adt/functions/groups/<fg>/fmodules/<fm>              -> HTTP 406 (obje VAR)
    #     /sap/bc/adt/functions/groups/<fg>/fmodules/<fm>/source/main  -> HTTP 200 (27721 bayt)
    # Bu tablo eskiden birinci satiri uretiyordu; 404 "obje YOK" diye okunuyordu (sessiz
    # yanlis teshis). url_path'i 'functions/groups' YAPMAK COZUM DEGIL: dogru uc FONKSIYON
    # GRUBUNU icerir ve grup adi FM adindan TURETILEMEZ -> tek-parametreli
    # get_object_url(name, type) onu URETEMEZ. Ayni yapisal gerekce sinif alt-include'larinda
    # da vardir (bkz. CLASS_INCLUDE_TYPES basligi); orada cozum "tabloya KOYMA + yonlendiren
    # ValueError" idi. Burada girdi KALIR (adt_type/file_extension/_TYPE_TO_SUBDIR tuketicileri
    # var) ama URL uretimi FAIL-CLOSED: yanlis adres uretmektense anlasilir ret.
    'function': {
        'adt_type': 'FUNC/FF',
        'url_path': None,
        'xml_namespace': 'function',
        'description': 'Function Module',
        'supports_create': False,  # Use create_function_module() instead (requires function group)
        'file_extension': '.func.abap',
        'generic_url_ret': (
            "FM'in ADT ucu fonksiyon grubunu ICERIR "
            "(/sap/bc/adt/functions/groups/<FG>/fmodules/<FM>[/source/main]) ve grup adi FM "
            "adindan TURETILEMEZ. Yaz: sap_adt_lib.SAPADTClient.set_function_module_source(); "
            "yarat: scripts/create_function_module.py; oku/ATC: adt_search_objects ile GERCEK "
            "URI'yi al ve o URI ile cagir. Bkz. playbook/adt-fugr-functions.md."
        ),
    },
    # DDIC types
    'dataelement': {
        'adt_type': 'DTEL/DE',
        'url_path': 'ddic/dataelements',
        'xml_namespace': 'dataelement',
        'description': 'Data Element',
        'supports_create': True,
        'file_extension': '.dtel.xml'
    },
    'domain': {
        'adt_type': 'DOMA/DD',
        'url_path': 'ddic/domains',
        'xml_namespace': 'domain',
        'description': 'Domain',
        'supports_create': True,
        'file_extension': '.doma.xml'
    },
    'table': {
        'adt_type': 'TABL/DT',
        'url_path': 'ddic/tables',
        'xml_namespace': 'table',
        'description': 'Database Table',
        'supports_create': True,
        'file_extension': '.tabl.xml'
    },
    'structure': {
        'adt_type': 'TABL/DS',
        'url_path': 'ddic/structures',
        'xml_namespace': 'structure',
        'description': 'Structure',
        'supports_create': True,
        'file_extension': '.tabl.xml'
    },
    'tabletype': {
        'adt_type': 'TTYP/DA',
        'url_path': 'ddic/tabletypes',
        'xml_namespace': 'tabletype',
        'description': 'Table Type',
        'supports_create': True,
        'file_extension': '.ttyp.xml'
    },
    'cds': {
        'adt_type': 'DDLS/DF',
        'url_path': 'ddic/ddl/sources',
        'xml_namespace': 'ddl',
        'description': 'CDS View (DDL Source)',
        'supports_create': True,
        'file_extension': '.ddls.asddls'
    },
    'metadataextension': {
        'adt_type': 'DDLX/EX',
        'url_path': 'ddic/ddlx/sources',
        'xml_namespace': 'ddlx',
        'description': 'CDS Metadata Extension (DDLX)',
        'supports_create': True,
        'file_extension': '.ddlx.asddlxs'
    },
    'accesscontrol': {
        'adt_type': 'DCLS/DL',
        'url_path': 'acm/dcl/sources',
        'xml_namespace': 'dcl',
        'description': 'CDS Access Control (DCL)',
        'supports_create': True,
        'file_extension': '.dcls.asdcls'
    },
    # RAP service definition — source-based DDL (/source/main), CDS gibi push/get/activate.
    'servicedefinition': {
        'adt_type': 'SRVD/SRV',
        'url_path': 'ddic/srvd/sources',
        'xml_namespace': 'srvd',
        'description': 'Service Definition',
        'supports_create': True,
        'file_extension': '.srvd'
    },
    'package': {
        'adt_type': 'DEVC/K',
        'url_path': 'packages',
        'xml_namespace': 'package',
        'description': 'ABAP Package',
        'supports_create': True,
        'file_extension': ''
    }
}

# Aliases for convenience
OBJECT_TYPE_ALIASES = {
    'clas': 'class',
    'intf': 'interface',
    'prog': 'program',
    'fugr': 'functiongroup',
    'func': 'function',
    'incl': 'include',
    'report': 'program',
    # DDIC aliases
    'dtel': 'dataelement',
    'doma': 'domain',
    'tabl': 'table',
    'ttyp': 'tabletype',
    # CDS aliases
    'ddls': 'cds',
    'ddl': 'cds',
    'cdsview': 'cds',
    'ddlx': 'metadataextension',
    'mde': 'metadataextension',
    'dcls': 'accesscontrol',
    'dcl': 'accesscontrol',
    # Service definition aliases
    'srvd': 'servicedefinition',
    'srv': 'servicedefinition',
    # Package alias
    'devc': 'package'
}


def normalize_object_type(object_type):
    """Normalize object type string to canonical form"""
    if not object_type:
        return 'class'  # Default

    obj_type = object_type.lower().strip()

    # Check aliases first
    if obj_type in OBJECT_TYPE_ALIASES:
        return OBJECT_TYPE_ALIASES[obj_type]

    # Check direct match
    if obj_type in OBJECT_TYPES:
        return obj_type

    # Sinif ALT-INCLUDE'u mu? (ccau/ccimp/...) — bunlar bagimsiz obje DEGILDIR, bu
    # yuzden OBJECT_TYPES'a KOYULMAZ (URL'leri ana sinifin adini gerektirir; tek
    # parametreli get_object_url() onlari uretemez). Ayri bir yol vardir; hata
    # mesaji cagirani oraya gondersin ki "desteklenmiyor" diye okunmasin.
    if obj_type in CLASS_INCLUDE_TYPES or obj_type in CLASS_INCLUDE_ALIASES:
        raise ValueError(
            f"'{object_type}' bir SINIF ALT-INCLUDE'udur (bagimsiz obje degil). "
            f"get_object_url() onu uretemez: URL ana sinifin adini gerektirir "
            f"(/oo/classes/<CLS>/includes/<seg>). "
            f"Kullan: get_class_include_url(<CLS>, '{obj_type}') / "
            f"SAPClient.push_class_include(). Bkz. playbook/adt-classes.md 24.8."
        )

    # Unknown type
    raise ValueError(f"Unsupported object type: {object_type}. Supported: {', '.join(OBJECT_TYPES.keys())}")


# =============================================================================
# SINIF ALT-INCLUDE'LARI (ccau / ccimp / ccdef / ccmac) — TEK KAYNAK
# =============================================================================
# NEDEN AYRI TABLO: bunlar bagimsiz SAP objesi DEGILDIR. ADT'de ana sinifin ALTINDA
# yasarlar (/oo/classes/<CLS>/includes/<segment>) ve URL'leri IKI ad ister. OBJECT_TYPES
# girdileri tek-parametreli `get_object_url(name, type)` ile uretildigi icin buraya
# konamazlar; ayri tablo + ayri URL uretici bilincli.
#
# ⛔ 2026-08-10 KUSUR-4: bu tablo HIC YOKTU. Sonuc: `push_object.py` testclasses'i
# TANIMIYORDU (--type choices'ta yok), `normalize_object_type` ValueError firlatiyordu
# ve operator el yordamiyla ham HTTP atmak zorunda kaldi -> dogrudan KUSUR-5/6'ya
# (POST govdeyi yok sayiyor / var olana POST 500) carpti. Yani uc kusur TEK SINIFTIR:
# *push zinciri sinif alt-include'unu bir kavram olarak tanimiyordu.*
#
# 'olculdu' alani DURUSTLUK ICINDIR — hangi segment adinin bu evde CANLI dogrulandigi:
#   testclasses    : ÖLÇÜLDÜ (playbook/adt-classes.md 24.8; 2026-07-29 201/500/56-bayt
#                    olcumu + 2026-08-10'da ZCL_SD015_STOCK_GUARD.ccau canliya girdi)
#   implementations: repo-ici referans var (sap_adt_lib.py, metot-seviyesi include URL'i)
#   definitions/macros: ADT konvansiyonu — BU EVDE CANLI OLCULMEDI. Kullanan ilk kisi
#                    dogrular ve bu alani gunceller (tahmini "olculdu" yazma).
CLASS_INCLUDE_TYPES = {
    'testclasses': {
        'segment': 'testclasses',
        'abap_include': 'CCAU',
        'file_extension': '.ccau.abap',
        'description': 'Class test include (ABAP Unit)',
        'olculdu': True,
    },
    'implementations': {
        'segment': 'implementations',
        'abap_include': 'CCIMP',
        'file_extension': '.ccimp.abap',
        'description': 'Class local implementations include',
        'olculdu': False,
    },
    'definitions': {
        'segment': 'definitions',
        'abap_include': 'CCDEF',
        'file_extension': '.ccdef.abap',
        'description': 'Class local definitions include',
        'olculdu': False,
    },
    'macros': {
        'segment': 'macros',
        'abap_include': 'CCMAC',
        'file_extension': '.ccmac.abap',
        'description': 'Class macros include',
        'olculdu': False,
    },
}

#: Evde kullanilan dosya-uzantisi adlari (.ccau.abap ...) kanonik ada esler.
CLASS_INCLUDE_ALIASES = {
    'ccau': 'testclasses',
    'ccimp': 'implementations',
    'ccdef': 'definitions',
    'ccmac': 'macros',
    'testclass': 'testclasses',
    'locals_imp': 'implementations',
    'locals_def': 'definitions',
}


def is_class_include(kind) -> bool:
    """`kind` bir sinif alt-include tipi mi? (ValueError FIRLATMAZ.)"""
    if not kind:
        return False
    k = str(kind).lower().strip()
    return k in CLASS_INCLUDE_TYPES or k in CLASS_INCLUDE_ALIASES


def normalize_class_include(kind) -> str:
    """'ccau' / '.ccau.abap' / 'testclasses' -> 'testclasses'."""
    if not kind:
        raise ValueError("Sinif alt-include tipi bos olamaz")
    k = str(kind).lower().strip().lstrip('.')
    if k.endswith('.abap'):                     # '.ccau.abap' gibi verilirse
        k = k[:-len('.abap')].rsplit('.', 1)[-1]
    if k in CLASS_INCLUDE_ALIASES:
        return CLASS_INCLUDE_ALIASES[k]
    if k in CLASS_INCLUDE_TYPES:
        return k
    raise ValueError(
        f"Bilinmeyen sinif alt-include tipi: {kind}. "
        f"Desteklenen: {', '.join(sorted(CLASS_INCLUDE_TYPES))} "
        f"(esanlamli: {', '.join(sorted(CLASS_INCLUDE_ALIASES))})"
    )


def get_class_include_url(class_name, kind) -> str:
    """Sinif alt-include'unun ADT URL'i.

    ⚠ Bu URL AYNI ZAMANDA KAYNAK UCUDUR — sonuna `/source/main` EKLENMEZ
    (siradan objelerden ayrilan nokta; ekleyen 404 alir).
    """
    from urllib.parse import quote
    seg = CLASS_INCLUDE_TYPES[normalize_class_include(kind)]['segment']
    cls = quote(str(class_name).lower(), safe='')
    return f'/sap/bc/adt/oo/classes/{cls}/includes/{seg}'


def is_class_include_url(object_url) -> bool:
    """URL bir SINIF ALT-INCLUDE ucu mu? (`.../oo/classes/<CLS>/includes/<segment>`)

    /programs/includes/<INCL> (KLASIK program include'u) BU DEGILDIR: o siradan bir
    objedir ve kaynagi `/source/main` altindadir. Kaba bir `'/includes/' in url` kontrolu
    ikisini karistirir ve klasik include okumasini KIRAR -- bu yuzden kontrol YAPISALDIR
    (`oo/classes/<ad>/includes/<segment>`) ve segment listesi CLASS_INCLUDE_TYPES'tan
    okunur (ikinci literal ACILMAZ).
    """
    if not object_url:
        return False
    parcalar = [p for p in str(object_url).split('?')[0].split('/') if p]
    if len(parcalar) < 5:
        return False
    if parcalar[-2].lower() != 'includes':
        return False
    if parcalar[-4].lower() != 'classes' or parcalar[-5].lower() != 'oo':
        return False
    return parcalar[-1].lower() in {v['segment'] for v in CLASS_INCLUDE_TYPES.values()}


def ensure_source_url(object_url) -> str:
    """Kaynak ucunu garanti et: gerekiyorsa sonuna `/source/main` EKLE.

    SINIF ALT-INCLUDE uclarina EKLENMEZ -- o URL kaynak ucunun KENDISIDIR
    (`get_class_include_url` docstring'i bunu 2026-08-10'dan beri yaziyordu, kod uymuyordu:
    Q217/Q229). CANLI OLCUM 2026-09-03 (DEV, salt-GET): ciplak include ucu HTTP 200
    (154609 bayt), ayni uc + `/source/main` HTTP 404; kontrol grubu ayni sinifin ANA
    kaynagi 200. Yani 404 baglanti/yetki degil, URL kurulusu.

    TANINMAYAN bir include segmenti (ornegin `.../includes/beklenmeyen`) icin `/source/main`
    YINE eklenir: muafiyet TAHMINLE genisletilmez (bu evde canli olculmus segmentler
    CLASS_INCLUDE_TYPES'ta beyanlidir).
    """
    url = str(object_url or '').rstrip('/')
    if url.endswith('/source/main'):
        return url
    if is_class_include_url(url):
        return url
    return url + '/source/main'


def object_name_from_source_url(object_url) -> str:
    """ADT URL'inden insan-okunur obje adi (hata mesajlari icin).

    `url.split('/')[-2]` YAZMA: `/source/main` eklenmis bir uctan 'source', alt-include
    ucundan 'includes' dondurur -- yani hata mesaji VAR OLMAYAN bir obje adi ILAN EDER.
    Olculdu 2026-09-03: include okumasi `[404] Object not found: source` diyordu; okuyan
    bunu "obje yok" diye okur ve teshis "aracin yanlis adresi"nden UZAKLASIR.
    """
    parcalar = [p for p in str(object_url or '').split('?')[0].split('/') if p]
    if len(parcalar) >= 3 and parcalar[-1].lower() == 'main' and parcalar[-2].lower() == 'source':
        parcalar = parcalar[:-2]
    if not parcalar:
        return ''
    if len(parcalar) >= 3 and parcalar[-2].lower() == 'includes':
        return f"{parcalar[-3]} ({parcalar[-1]} include'u)"
    return parcalar[-1]


# =============================================================================
# DDIC OKUMA-YOLU — TEK KAYNAK (2026-08-09)
# =============================================================================
# Bes DDIC tipi ADT'de AYNI degildir: ikisinin GERCEK bir `/source/main` DDL ucu
# vardir, ucunun YOKTUR. Bu ayrim tek yerde tanimlanir cunku iki ayri tuketici
# (`mcp_servers/sap_adt/tools/atom.py::adt_get` ve `scripts/sap_sync_pull.py`) daha
# once AYNI kurali BAGIMSIZ birer literal olarak tasiyordu; biri duzeltilip digeri
# unutuldugunda `adt_get` DDL, `sap_sync_pull` XML donduruyordu (okuma tutarsizligi).
#
# CANLI OLCUM (2026-08-09, s4_private DEV, salt-okuma GET; Z + STANDART objelerle):
#   table       ZSD001_T_*                 XML 200 · /source/main 200 (duz DDL)
#   table       MARA / VBAK / T156         XML 200 · /source/main 200  <- standartta da calisir
#   structure   ZSD001_S_* (2 obje)        XML 200 · /source/main 200
#   structure   BAPIRET2 / SYST            XML 200 · /source/main 200  <- standartta da calisir
#   dataelement ZSD001_E_* (2 obje)        XML 200 · /source/main 404
#   domain      ZSD001_D_*                 XML 200 · /source/main 404
#   tabletype   ZSD001_TT_* (3) / BAPIRET2_T  XML 200 · /source/main 404
# Yani DDL ucu TIPE baglidir, Z-olup-olmamaya DEGIL. Bir tipi asagi tasimadan once
# AYNI olcumu yap (en az bir Z + bir standart obje); playbook/adt-domain-dtel.md ve
# playbook/adt-tables-structures.md ayni ayrimi belgeler.

#: `/source/main` ucu OLMAYAN DDIC tipleri — yalniz obje XML'i okunur (get_ddic_object).
#: Bunlara `/source/main` eklemek 404 verir ve obje YANLISLIKLA "yok" gorunur.
#: ⚠ DUZ KUME LITERALI olarak birakildi (frozenset(...) DEGIL): `reviewer_tip_kapsam`
#: fixture'i bu tablolari `ast.literal_eval` ile OKUR (MCP SDK'siz CI icin) ve bir
#: cagri ifadesini cozemez -> tablo "okunamadi" diye FAIL eder.
DDIC_XML_ONLY_TYPES = {'dataelement', 'domain', 'tabletype'}

#: GERCEK `/source/main` DDL ucu OLAN DDIC tipleri — kaynak olarak duz DDL okunur.
#: (Repo konvansiyonu da DDL'dir: source_drift._TYPE_TO_EXTENSIONS table/structure ->
#: .asddls/.ddls/.cds, ve create yolu DDL'i `PUT /source/main` ile yazar.)
DDIC_DDL_SOURCE_TYPES = {'table', 'structure'}


def ddic_read_mode(object_type):
    """DDIC okuma-yolunu sinifla: `'ddl'` | `'xml'` | `None` (DDIC degil/bilinmiyor).

    Esanlamlilar (tabl/ttyp/dtel/doma) `normalize_object_type` ile cozulur; boylece
    cagiranlar kendi takma-ad tablolarini TASIMAZ (o kopyalar ayrisma kaynagiydi).

    Returns:
        (mode, canonical_type): mode `'ddl'`/`'xml'` ise canonical_type kanonik DDIC
        tipidir (`table`/`structure`/`dataelement`/`domain`/`tabletype`).
        DDIC olmayan ya da cozulemeyen tipte `(None, None)`.
    """
    try:
        canonical = normalize_object_type(object_type)
    except Exception:
        return (None, None)
    if canonical in DDIC_DDL_SOURCE_TYPES:
        return ('ddl', canonical)
    if canonical in DDIC_XML_ONLY_TYPES:
        return ('xml', canonical)
    return (None, None)


def get_object_url(object_name, object_type='class'):
    """Generate SAP ADT object URL for any object type

    Her tipin tek-parametreli generic bir ucu YOKTUR. `url_path` bos olan tip
    FAIL-CLOSED reddedilir (ValueError + kanonik yolu SOYLEYEN mesaj): yanlis bir adres
    uretmek 404 dogurur ve 404 "obje YOK" diye okunur -- sessiz yanlis teshis. Bugun bu
    durumda olan tek tip `function` (FM); gerekce tablodaki yorumda.
    """
    from urllib.parse import quote
    obj_type = normalize_object_type(object_type)
    type_info = OBJECT_TYPES[obj_type]
    if not type_info.get('url_path'):
        raise ValueError(
            f"'{object_type}' icin generic ADT URL'i URETILEMEZ "
            f"(get_object_url tek-parametrelidir). "
            + (type_info.get('generic_url_ret') or
               "Bu tipin ADT ucu obje adindan turetilemiyor; kanonik aracini kullan.")
        )
    # Namespaced objects (e.g. /SCWM/DE_HUIDENT) carry slashes in the name; ADT
    # expects these encoded as %2f in the path segment. quote(safe='') leaves
    # plain names (letters/digits/_.-~) untouched and only encodes the slashes.
    name_lower = quote(object_name.lower(), safe='')

    return f'/sap/bc/adt/{type_info["url_path"]}/{name_lower}'


def get_source_url(object_name, object_type='class'):
    """Generate source URL with /source/main suffix"""
    base_url = get_object_url(object_name, object_type)
    return f'{base_url}/source/main'


def get_adt_type(object_type):
    """Get ADT type identifier (e.g., CLAS/OC)"""
    obj_type = normalize_object_type(object_type)
    return OBJECT_TYPES[obj_type]['adt_type']


def get_file_extension(object_type):
    """Get recommended file extension"""
    obj_type = normalize_object_type(object_type)
    return OBJECT_TYPES[obj_type]['file_extension']


def supports_creation(object_type):
    """Check if object type can be created via API"""
    obj_type = normalize_object_type(object_type)
    return OBJECT_TYPES[obj_type]['supports_create']


def supports_generic_url(object_type):
    """Tip tek-parametreli `get_object_url()` ile adreslenebilir mi?

    TEK GERCEKTEN turer (`url_path`); ikinci bir bayrak TUTULMAZ -- iki alan ayrisirsa
    biri bayatlar. Cagiran `get_object_url`u cagirmadan ONCE sorabilsin diye var.
    """
    obj_type = normalize_object_type(object_type)
    return bool(OBJECT_TYPES[obj_type].get('url_path'))


def list_supported_types():
    """List all supported object types"""
    return list(OBJECT_TYPES.keys())


def get_type_description(object_type):
    """Get human-readable description of object type"""
    obj_type = normalize_object_type(object_type)
    return OBJECT_TYPES[obj_type]['description']


def get_adt_type_from_url(object_url):
    """Reverse-lookup ADT type from an object URL path.

    This is the single source of truth for URL-to-type mapping, used by
    activation and syntax-check XML builders.

    Args:
        object_url: URL path like '/sap/bc/adt/oo/classes/zcl_test'

    Returns:
        ADT type string (e.g., 'CLAS/OC') or 'UNKNOWN' if not matched
    """
    # Build reverse map from url_path -> adt_type
    for obj_type_info in OBJECT_TYPES.values():
        url_segment = obj_type_info.get('url_path')
        if not url_segment:          # generic ucu olmayan tip (bkz. 'function') -- atla
            continue
        if f'/{url_segment}/' in object_url:
            return obj_type_info['adt_type']
    return 'UNKNOWN'


# Map of type -> local subdirectory for workspace file storage
_TYPE_TO_SUBDIR = {
    'class': 'classes', 'clas': 'classes',
    'interface': 'classes', 'intf': 'classes',
    'program': 'progs', 'prog': 'progs', 'report': 'progs',
    'include': 'progs', 'incl': 'progs',
    'functiongroup': 'fugr', 'fugr': 'fugr',
    'function': 'fugr', 'func': 'fugr',
    'dataelement': 'ddic', 'dtel': 'ddic',
    'domain': 'ddic', 'doma': 'ddic',
    'table': 'ddic', 'tabl': 'ddic',
    'structure': 'ddic',
    'tabletype': 'ddic', 'ttyp': 'ddic',
    'cds': 'cds', 'ddls': 'cds', 'ddl': 'cds', 'cdsview': 'cds',
    'metadataextension': 'cds', 'ddlx': 'cds', 'mde': 'cds',
    'accesscontrol': 'cds', 'dcls': 'cds', 'dcl': 'cds',
    'servicedefinition': 'cds', 'srvd': 'cds', 'srv': 'cds',
    'package': 'packages', 'devc': 'packages',
}


def get_local_subdir(object_type):
    """Get local subdirectory name for storing files of this object type.

    Args:
        object_type: Object type string (canonical or alias)

    Returns:
        Subdirectory name like 'classes', 'progs', 'fugr', 'ddic'
    """
    return _TYPE_TO_SUBDIR.get(object_type.lower(), 'classes')


def format_object_name(name, object_type='class'):
    """Format object name with type prefix for display"""
    obj_type = normalize_object_type(object_type)
    desc = OBJECT_TYPES[obj_type]['description']
    return f"{desc}: {name}"


if __name__ == '__main__':
    # Test/demo
    print("Supported SAP Object Types:")
    print("=" * 70)
    for obj_type in OBJECT_TYPES:
        info = OBJECT_TYPES[obj_type]
        print(f"\n{obj_type.upper()}")
        print(f"  Description: {info['description']}")
        print(f"  ADT Type:    {info['adt_type']}")
        print(f"  URL Path:    {info['url_path'] or '(generic URL YOK -- kanonik arac gerekir)'}")
        print(f"  Extension:   {info['file_extension']}")
        print(f"  Can Create:  {info['supports_create']}")

    print("\n" + "=" * 70)
    print("\nAliases:")
    for alias, target in OBJECT_TYPE_ALIASES.items():
        print(f"  {alias} -> {target}")
