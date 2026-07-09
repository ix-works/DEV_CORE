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
    'function': {
        'adt_type': 'FUNC/FF',
        'url_path': 'functions/modules',
        'xml_namespace': 'function',
        'description': 'Function Module',
        'supports_create': False,  # Use create_function_module() instead (requires function group)
        'file_extension': '.func.abap'
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

    # Unknown type
    raise ValueError(f"Unsupported object type: {object_type}. Supported: {', '.join(OBJECT_TYPES.keys())}")


def get_object_url(object_name, object_type='class'):
    """Generate SAP ADT object URL for any object type"""
    from urllib.parse import quote
    obj_type = normalize_object_type(object_type)
    type_info = OBJECT_TYPES[obj_type]
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
        url_segment = obj_type_info['url_path']
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
        print(f"  URL Path:    {info['url_path']}")
        print(f"  Extension:   {info['file_extension']}")
        print(f"  Can Create:  {info['supports_create']}")

    print("\n" + "=" * 70)
    print("\nAliases:")
    for alias, target in OBJECT_TYPE_ALIASES.items():
        print(f"  {alias} -> {target}")
