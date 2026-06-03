"""Pipeline entry point: run every catalog analysis for a server, then export.

Replaces the old ``Master_run_HOS.py`` / ``Master_run_RF.py`` pair. The server
is now a command-line argument instead of a duplicated script, and the catalog
analyses run in-process (no subprocess spawning), which is simpler and avoids
the Windows console encoding crash the old emoji ``print`` statements caused.

Examples::

    python main.py HOS
    python main.py RF --country IN US --modality CT MR
    python main.py all
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime

import config
from catalogs import run_all
from dashboard_export import build_dashboard_feed


def _configure_logging(server: str) -> None:
    """Log to both the console and ``<output>/run_log_<server>.txt``."""
    paths = config.server_paths(server)
    paths["output"].mkdir(parents=True, exist_ok=True)
    log_file = paths["output"] / f"run_log_{server}.txt"

    handlers = [logging.StreamHandler(), logging.FileHandler(log_file, encoding="utf-8")]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
        force=True,
    )


def run_server(server, country=None, modality=None) -> None:
    """Run all catalogs for one server and rebuild its dashboard feed."""
    _configure_logging(server)
    paths = config.server_paths(server)
    log = logging.getLogger(__name__)

    log.info("Run started for %s at %s", server, datetime.now())
    run_all(server, paths["i_files"], paths["b_files"], paths["output"], country, modality)
    build_dashboard_feed(paths["output"], server)
    log.info("Run completed for %s", server)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "server",
        choices=(*config.SERVERS, "all"),
        help="Server to process, or 'all' for every server",
    )
    parser.add_argument("--country", nargs="*", help="Optional country filter, e.g. IN US")
    parser.add_argument("--modality", nargs="*", help="Optional modality filter, e.g. CT MR")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    servers = config.SERVERS if args.server == "all" else (args.server,)
    for server in servers:
        run_server(server, args.country, args.modality)


if __name__ == "__main__":
    main()
