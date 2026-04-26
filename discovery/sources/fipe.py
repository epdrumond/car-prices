"""
FIPE reference table (not marketplace listings): chain marcas -> modelos -> anos -> valor.

Uses the public API at parallelum.com.br (same data flow as the common /fipe community APIs).
Respect the service: few requests, small sample only.
"""
from __future__ import annotations

import requests
from discovery.http_utils import DEFAULT_HEADERS, DEFAULT_TIMEOUT
from discovery.paths import OUTPUT_DIR
from discovery.writers import write_json

FIPE_BASE = "https://parallelum.com.br/fipe/api/v1"
OUTPUT_FILE = OUTPUT_DIR / "fipe_sample.json"


def collect_fipe_sample(
    brand_marca_id: int = 21,
    max_marcas_in_excerpt: int = 12,
) -> str:
    """
    Build a small FIPE sample: excerpt of marcas, then full chain for one model/year.
    Returns path to the written file.
    """
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    r_marcas = session.get(f"{FIPE_BASE}/carros/marcas", timeout=DEFAULT_TIMEOUT)
    r_marcas.raise_for_status()
    marcas: list[dict] = r_marcas.json()

    excerpt = marcas[:max_marcas_in_excerpt]
    m_mod = session.get(
        f"{FIPE_BASE}/carros/marcas/{brand_marca_id}/modelos", timeout=DEFAULT_TIMEOUT
    )
    m_mod.raise_for_status()
    mod_body: dict = m_mod.json()
    modelos: list[dict] = mod_body.get("modelos", [])
    if not modelos:
        raise RuntimeError("FIPE: no modelos returned for brand")

    first = modelos[0]
    mid = first["codigo"]
    r_years = session.get(
        f"{FIPE_BASE}/carros/marcas/{brand_marca_id}/modelos/{mid}/anos",
        timeout=DEFAULT_TIMEOUT,
    )
    r_years.raise_for_status()
    years: list[dict] = r_years.json()
    if not years:
        raise RuntimeError("FIPE: no years returned for model")

    y0 = years[0]["codigo"]
    r_price = session.get(
        f"{FIPE_BASE}/carros/marcas/{brand_marca_id}/modelos/{mid}/anos/{y0}",
        timeout=DEFAULT_TIMEOUT,
    )
    r_price.raise_for_status()
    price: dict = r_price.json()

    out = {
        "source": "fipe_tabela_referencia",
        "api_base": FIPE_BASE,
        "note": "Reference month price (FIPE), not an asking price from a listing.",
        "requests_made": 4,
        "marcas_excerpt": excerpt,
        "cadeia_exemplo": {
            "marca_id": brand_marca_id,
            "primeiro_modelo": first,
            "anos_disponiveis_primeiro_modelo": years[:5],
            "ano_escolhido": y0,
            "veiculo_tabela_fipe": price,
        },
    }
    write_json(OUTPUT_FILE, out)
    return str(OUTPUT_FILE)
