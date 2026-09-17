"""Process entrypoints: all-in-one, api, worker, once."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
import time
from typing import Optional

import uvicorn

from notify_hub.ack import run_escalate_ticker_stub
from notify_hub.api import create_app
from notify_hub.bot_handler import get_offset, process_updates_batch
from notify_hub.config import get_settings
from notify_hub.db import init_db, session_scope
from notify_hub.outbox import process_outbox_batch
from notify_hub.telegram_api import get_updates

logger = logging.getLogger(__name__)

_stop = threading.Event()


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
    )


def _handle_signal(signum: int, _frame: object) -> None:
    logger.info("Signal %s received, shutting down…", signum)
    _stop.set()


def run_poller_loop(token: str) -> None:
    """Long-poll getUpdates for one token until stop."""
    settings = get_settings()
    logger.info("Telegram poller started (token …%s)", token[-4:] if len(token) >= 4 else "????")
    while not _stop.is_set():
        try:
            with session_scope() as session:
                offset = get_offset(session, token)
            updates = get_updates(token, offset=offset or None, timeout=25)
            if updates:
                with session_scope() as session:
                    process_updates_batch(session, token, updates, settings=settings)
        except Exception:
            logger.exception("Poller error; backing off")
            _stop.wait(5)


def run_worker_loop() -> None:
    settings = get_settings()
    logger.info("Outbox + ack worker started")
    last_ack = 0.0
    while not _stop.is_set():
        try:
            with session_scope() as session:
                sent = process_outbox_batch(session, settings=settings)
            if sent:
                logger.info("Outbox sent=%s", sent)
            now = time.time()
            if now - last_ack >= settings.ack_check_interval_seconds:
                with session_scope() as session:
                    n = run_escalate_ticker_stub(
                        session, settings.default_ack_timeout_minutes
                    )
                if n:
                    logger.info("Ack escalate stub transitions=%s", n)
                last_ack = now
        except Exception:
            logger.exception("Worker error; backing off")
            _stop.wait(3)
            continue
        _stop.wait(1)


def run_once() -> int:
    """Fetch and process one getUpdates batch per unique token."""
    settings = get_settings()
    init_db()
    tokens = settings.unique_tokens()
    if not tokens:
        logger.error("No TELEGRAM_BOT_TOKEN configured")
        return 1
    for token in tokens:
        with session_scope() as session:
            offset = get_offset(session, token)
        updates = get_updates(token, offset=offset or None, timeout=0)
        with session_scope() as session:
            process_updates_batch(session, token, updates, settings=settings)
        logger.info("once: token …%s updates=%s", token[-4:], len(updates))
    return 0


def run_api(blocking: bool = True) -> Optional[uvicorn.Server]:
    settings = get_settings()
    init_db()
    app = create_app(settings)
    config = uvicorn.Config(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    if blocking:
        server.run()
        return None
    thread = threading.Thread(target=server.run, name="uvicorn", daemon=True)
    thread.start()
    return server


def run_all() -> None:
    settings = get_settings()
    init_db()
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    worker = threading.Thread(target=run_worker_loop, name="worker", daemon=True)
    worker.start()

    pollers: list[threading.Thread] = []
    for token in settings.unique_tokens():
        t = threading.Thread(
            target=run_poller_loop, args=(token,), name=f"poller-{token[-4:]}", daemon=True
        )
        t.start()
        pollers.append(t)

    if not settings.unique_tokens():
        logger.warning("No Telegram tokens — API only (pollers disabled)")

    # blocking API in main thread
    run_api(blocking=True)
    _stop.set()


def run_worker_only() -> None:
    settings = get_settings()
    init_db()
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    for token in settings.unique_tokens():
        threading.Thread(
            target=run_poller_loop, args=(token,), name=f"poller-{token[-4:]}", daemon=True
        ).start()

    run_worker_loop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="notify_hub", description="DimKava Notify Hub")
    parser.add_argument(
        "mode",
        nargs="?",
        default="all",
        choices=["all", "api", "worker", "once"],
        help="all (default) | api | worker | once",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    setup_logging(settings.log_level)

    if args.mode == "all":
        run_all()
        return 0
    if args.mode == "api":
        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)
        run_api(blocking=True)
        return 0
    if args.mode == "worker":
        run_worker_only()
        return 0
    if args.mode == "once":
        return run_once()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
