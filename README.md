# car-prices

End-to-end project for the extraction, processing and analysis for car prices in Brazil. **Implementation is in Python 3** (ingestion, processing, database access, and analysis), with config-driven behavior and a kept-small footprint toward external data sources.

**Discovery scripts (Phase 1):** the [`discovery/`](discovery/README.md) folder has Python code that fetches **small samples** from the outlined sources and writes JSON under `discovery/output/` (gitignored). Run from the repo root: `pip install -r discovery/requirements.txt` then `python -m discovery.run`.

**Local discovery and source config:** copy templates from `config/examples/` into `config/local/` (see [config/examples/README.md](config/examples/README.md) and [PROJECT_OUTLINE.md](PROJECT_OUTLINE.md) Phase 1). There are placeholders for the generic data contract (`discovery.example.yaml`) and for each candidate source (`mercadolivre`, `icarros`, `olx`, `fipe`). The `config/local/` directory is in `.gitignore` and is not pushed to the remote.
