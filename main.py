"""Entry point for the Equalizer service.

This script boots the long-running process and is intended to be
managed by systemd. It reads the API key from the ``EQUALIZER_API_KEY``
environment variable and logs lifecycle events to
``/var/log/equalizer/equalizer.log``.
"""

import logging
import os
import signal
import sys
import time
from pathlib import Path


LOG_PATH = Path("/var/log/equalizer/equalizer.log")


def configure_logging() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


def main() -> None:
    configure_logging()

    api_key = os.environ.get("EQUALIZER_API_KEY")
    if not api_key:
        logging.error("EQUALIZER_API_KEY is not set. Exiting.")
        sys.exit(1)

    logging.info("Equalizer service starting.")

    should_run = True

    def _handle_signal(signum: int, _) -> None:
        nonlocal should_run
        logging.info("Received signal %s; stopping.", signum)
        should_run = False

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    while should_run:
        # Placeholder for the actual processing loop.
        time.sleep(5)
        logging.debug("Service heartbeat.")

    logging.info("Equalizer service stopped.")


if __name__ == "__main__":
    main()
