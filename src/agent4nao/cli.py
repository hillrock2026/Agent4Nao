"""Minimal interactive desktop chat entry point.

Thin by design: conversation, session, and provider logic live in the package
and remain testable without this CLI. Argument parsing uses only the standard
library and is deliberately minimal.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from agent4nao.config import DEFAULT_MODEL, load_config
from agent4nao.conversation import ConversationSession
from agent4nao.log import configure_logging, get_logger
from agent4nao.model.ollama import OllamaProvider

EXIT_COMMANDS = {"/exit", "/quit", "/q"}

BANNER = (
    "Agent4NAO Phase 1 - desktop local conversation\n"
    "No robot tools or physical actions are enabled.\n"
    "Type '/exit' (or Ctrl-D) to quit.\n"
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent4nao",
        description=(
            "Agent4NAO Phase 1 - desktop local conversation with a local model."
        ),
        epilog=(
            f"Default model tag: {DEFAULT_MODEL}. "
            "Configuration is via AGENT4NAO_* environment variables "
            "(see the Phase 1 runbook). No robot tools or physical actions "
            "are enabled."
        ),
    )
    return parser


def _read_line() -> Optional[str]:
    sys.stderr.write("you> ")
    sys.stderr.flush()
    line = sys.stdin.readline()
    if line == "":
        return None
    return line.rstrip("\n")


def main(argv: Optional[List[str]] = None) -> int:
    # Consume argv up front so that --help/-h (and unknown options) are
    # handled without loading configuration or instantiating the provider.
    parser = _build_parser()
    try:
        parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        if isinstance(code, int):
            return code
        return 0 if code is None else 1

    config = load_config()
    configure_logging(config.log_level)
    logger = get_logger("agent4nao.cli")

    provider = OllamaProvider(config.ollama)
    session = ConversationSession(provider=provider, config=config, logger=logger)

    sys.stderr.write(BANNER)
    try:
        while True:
            line = _read_line()
            if line is None:
                break
            if line.strip() in EXIT_COMMANDS:
                break

            result = session.send(line)
            if result.ok:
                sys.stdout.write(f"assistant> {result.message}\n")
                sys.stdout.flush()
            else:
                sys.stdout.write(
                    f"[{result.status.value}] {result.detail}\n")
                sys.stdout.flush()
    except KeyboardInterrupt:
        sys.stderr.write("\n")
    finally:
        session.close()

    return 0
