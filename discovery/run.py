from __future__ import annotations

"""
Run one or all discovery sample collectors. Writes JSON under discovery/output/.

    python -m discovery.run
    python -m discovery.run --source fipe
    python -m discovery.run --source http_scrape   # set SCRAPE_URL
"""

import argparse
import sys

from discovery.paths import OUTPUT_DIR
from discovery.sources.fipe import collect_fipe_sample
from discovery.sources.http_scrape import collect_http_scrape_sample
from discovery.sources.icarros import collect_icarros_sample
from discovery.sources.mercadolivre import collect_mercadolivre_sample
from discovery.sources.olx import collect_olx_sample

# `all` does not include `http_scrape` (optional URL, long delay, user-triggered only).
ALL_SOURCES = ("fipe", "mercadolivre", "icarros", "olx")

COLLECTORS = {
    "fipe": collect_fipe_sample,
    "mercadolivre": collect_mercadolivre_sample,
    "icarros": collect_icarros_sample,
    "olx": collect_olx_sample,
    "http_scrape": collect_http_scrape_sample,
}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Write small raw JSON samples to discovery/output/")
    p.add_argument(
        "--source",
        choices=["all", *COLLECTORS.keys()],
        default="all",
    )
    args = p.parse_args(argv)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.source == "all":
        to_run = list(ALL_SOURCES)
    else:
        to_run = [args.source]
    for name in to_run:
        path = COLLECTORS[name]()
        print(f"wrote {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
