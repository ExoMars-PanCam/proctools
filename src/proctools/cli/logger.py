import logging
from pathlib import Path
import signal
import sys
import time

# TODO: any need to call logging.shutdown() after exception or signal intercepts?
#  The logging module hooks .shutdown() via atexit anyway and testing has revealed no
#  issues with incomplete log files...


def init(log_path: Path = None, cli_output=True):
    if not log_path and not cli_output:
        logging.disable(logging.CRITICAL)
        return

    root = logging.getLogger("")
    root.setLevel(logging.INFO)

    if cli_output:
        fmt = "%(name)-26s %(levelname)-8s %(message)s"
        try:
            import coloredlogs
            coloredlogs.install(level=logging.INFO, logger=root, fmt=fmt)

        except ImportError:
            cli = logging.StreamHandler()
            # cli.setLevel(logging.INFO)
            cli_fmt = logging.Formatter(fmt)
            cli.setFormatter(cli_fmt)
            root.addHandler(cli)

    if log_path is not None:
        fh = logging.FileHandler(log_path, mode="w")
        # fh.setLevel(logging.INFO)
        logging.Formatter.converter = time.gmtime
        fh_fmt = logging.Formatter(fmt="%(asctime)s.%(msecs)03d "
                                       "%(name)-26s "
                                       "%(levelname)-8s "
                                       "%(message)s",
                                   datefmt="%Y-%m-%dT%H:%M:%S")
        fh.setFormatter(fh_fmt)
        root.addHandler(fh)

    # Log all uncaught exceptions encountered at runtime
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):  # SIGINT
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        root.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
        root.critical("Processing aborted")

    sys.excepthook = handle_exception

    # Log SIGINT (e.g. kill -2 / Ctrl+C) and SIGTERM (e.g. kill -15) events
    def handle_signals(signum, frame):
        signame = {
            2: "SIGINT",
            15: "SIGKILL",
        }.get(signum, "UNKNOWN signal")
        root.critical(f"{signame} received from the system")
        root.critical("Processing aborted")
        sys.exit(1)

    signal.signal(signal.SIGINT, handle_signals)
    signal.signal(signal.SIGTERM, handle_signals)
