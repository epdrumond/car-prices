from __future__ import annotations

"""
Run one or all discovery collectors. Writes JSON under discovery/output/.

    python -m discovery.run
    python -m discovery.run --source fipe
    python -m discovery.run --source listings_page
"""

import argparse
import sys

from discovery.paths import OUTPUT_DIR
from discovery.sources.fipe import collect_fipe_sample
from discovery.sources.listings_page import collect_listings_page_sample

ALL_SOURCES = ("fipe", "listings_page")

COLLECTORS = {
    "fipe": collect_fipe_sample,
    "listings_page": collect_listings_page_sample,
}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Write discovery samples to discovery/output/")
    p.add_argument(
        "--source",
        choices=["all", *COLLECTORS.keys()],
        default="all",
    )
    args = p.parse_args(argv)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    to_run = list(ALL_SOURCES) if args.source == "all" else [args.source]
    for name in to_run:
        path = COLLECTORS[name]()
        print(f"wrote {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
