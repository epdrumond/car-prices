# Example configuration templates

Each `*.example.yaml` file is a **placeholder** you copy into `config/local/` (drop the `.example` part or keep a name you prefer). The `config/local/` directory is **gitignored**; put real keys, tokens, and source-specific field maps there.

| File | Purpose |
|------|---------|
| `discovery.example.yaml` | Generic data contract (entities, `field_map`, etc.) |
| `mercadolivre.example.yaml` | Public REST API (vehicles) — [developers](https://developers.mercadolivre.com.br/) |
| `icarros.example.yaml` | OAuth / partner API — [apidocs](https://www.icarros.com.br/apidocs/apiOauth.html) |
| `olx.example.yaml` | Official developer areas — [developers](https://developers.olx.com.br/) |
| `fipe.example.yaml` | Reference prices (complement to listings) — choose a provider and document its `base_url` and auth |

```bash
mkdir -p config/local
cp config/examples/mercadolivre.example.yaml config/local/mercadolivre.yaml
# edit config/local/mercadolivre.yaml
```
