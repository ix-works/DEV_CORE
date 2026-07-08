# SAP ADT MCP Server

Typed tool layer over `scripts/sap_adt_lib.py` for SAP ABAP Development Tools (ADT) operations.

**ADR**: [`governance/decisions/0007-sap-adt-mcp-server.md`](../../governance/decisions/0007-sap-adt-mcp-server.md)

## Tools (v1)

| Tool | Tip | Açıklama |
|---|---|---|
| `adt_get` | Atom | Obje GET (var mı, aktif mi, source) |
| `adt_post_shell` | Atom | Boş Z obje shell yarat |
| `adt_push_source` | Atom | Source body push |
| `adt_activate` | Atom | Aktivasyon |
| `adt_domain_create` | Composite | shell + push + activate + verify (rollback'li) |
| `adt_dtel_create` | Composite | shell + push + activate + verify (rollback'li) |
| `adt_struct_create` | Composite | shell + push + activate + verify (rollback'li) |
| `adt_search_objects` | Query | İsim/açıklama ara |
| `adt_transport_list` | Query | Transport içerik listele |
| `adt_lock_check` | Query | Lock kontrolü |

## Server-Side Guardrails (ADR 0005, hardcoded)

| Kontrol | Reject |
|---|---|
| Z prefix yoksa | Standart obje yaratma yasak |
| TR text eksik/non-TR | 4 label dolu zorunlu |
| Std obje delete | Reject |
| Transport release | Tool listesinde yok |
| Package create | Tool listesinde yok |

Bypass yok. Değişiklik için `mcp_servers/sap_adt/guardrails.py` commit edilmeli.

## Kurulum

```powershell
pip install -r mcp_servers/sap_adt/requirements.txt
```

## Diğer Geliştiriciler İçin Setup (Yeni Katılan Biri)

Bu repo paylaşımlı — birden fazla geliştirici farklı modüllerde çalışıyor. MCP server kodu ve registration repo'da paylaşılır; çalıştırma her makinede lokal.

**Tek komut:**

```powershell
python scripts/team_setup.py
```

Bu script şunları sırayla yapar:
1. Python versiyonu kontrol (3.10+)
2. git pull (eğer değişiklik varsa uyarır)
3. `pip install -r mcp_servers/sap_adt/requirements.txt`
4. `.claude/active_package` wizard — kendi modülünü gir (örn. ZMM004_CLC)
5. `.conn_adt` kontrol et (yoksa template göster)
6. Statusline + MCP server smoke test

**Sonra:** VS Code'da `Ctrl+Shift+P` → `Reload Window` (Claude Code restart).

**Flag'ler:**
- `--no-pull`: git pull yapma
- `--no-install`: pip install yapma
- `--pkg ZMM004_CLC`: paket wizard'ı atla, direkt set et

Sonra:
- ✅ Statusline alt çubukta görünür (kendi paketin + sprint + transport + VPN)
- ✅ MCP tool'ları (`adt_get`, `adt_struct_create` vd.) coordinator'a açılır
- ✅ Kendi `.conn_adt` ile kendi SAP sistemine bağlanır

**Diğer repolar etkilenmez:** `.claude/settings.json` repo-spesifik. Bu repo açıldığında aktif, başka repoya geçtiğinde devre dışı. Global Claude Code ayarlarına dokunmaz.

**Python ortamı sorunu:** Eğer virtualenv kullanıyorsan ve sistem Python'unda `mcp` yoksa, kendi `.claude/settings.local.json` dosyana command override koy:

```json
{
  "mcpServers": {
    "sap-adt": {
      "command": "C:/path/to/your/venv/Scripts/python.exe",
      "args": ["-m", "mcp_servers.sap_adt.server"]
    }
  }
}
```

`settings.local.json` gitignore'da — sadece sana ait kalır.

## Çalıştırma

Claude Code repo kökündeki `.mcp.json` üzerinden otomatik başlatır (stdio transport).

`.mcp.json` registry komutuyla yaratıldı:

```powershell
claude mcp add -s project sap-adt python -- -m mcp_servers.sap_adt.server
```

Repo'da paylaşılan dosya — `git pull` ile gelir, ek manuel adım yok.

## Manuel Test

```powershell
# Server'ı stdio modunda ayağa kaldır
python -m mcp_servers.sap_adt.server
# Sonra JSON-RPC mesajları gönder (test/smoke.py kullan)
```

## Dosya Yapısı

```
mcp_servers/sap_adt/
├── README.md              (bu dosya)
├── requirements.txt
├── __init__.py
├── server.py              (MCP server entry point)
├── guardrails.py          (ADR 0005 hardcoded)
├── tools/
│   ├── __init__.py
│   ├── atom.py            (adt_get, adt_post_shell, adt_push_source, adt_activate)
│   ├── composite.py       (adt_*_create)
│   └── query.py           (adt_search, adt_transport_list, adt_lock_check)
└── tests/
    └── smoke.py
```
