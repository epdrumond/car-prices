# Example configuration (committed templates)

Copy into `config/local/` (gitignored). See the root [README.md](../README.md) and [discovery/README.md](../discovery/README.md).

| File | Purpose |
|------|---------|
| `discovery.example.yaml` | Canonical `field_map` / `entities` for the data model |
| `listings_page.example.yaml` | `listings_page_url` + optional `source_label` for the generic HTML discovery script |
| `webmotors.example.yaml` | Copy to `config/local/webmotors.yaml` for `python -m discovery.run --source webmotors` |
| `webmotors_data_contract.example.yaml` | Field map for JSON-LD list extraction (complement `discovery.example.yaml`) |

The FIPE sample URL is set in `discovery/sources/fipe.py` (`FIPE_BASE`); add a `config/local/` override there only if you later wire one.
