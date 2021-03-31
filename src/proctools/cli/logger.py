import logging
import logging.handlers
from pathlib import Path
import sys
import time
from typing import Optional

initialised: bool = False  # (see python issue 34939 for why this needs to be at the top specifically)


def init(file: Optional[Path] = None, stdout: bool = True, mode: str = "a", level: int = logging.INFO):
    global buffer, initialised, root

    if initialised:
        root.warning("Attempting to reinitialise the log; ignoring")
        return
    elif file is None and not stdout:
        # still commit critical entries to the buffer so they can be retrieved if needed during cleanup
        logging.disable(logging.CRITICAL)
        return
    elif level not in (logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL):
        raise ValueError(f"'{level}' is not a valid log level")

    if stdout:
        fmt = "%(name)-18s %(levelname)-8s %(message)s"
        try:
            import coloredlogs
            coloredlogs.install(level=level, logger=root, fmt=fmt)
        except ImportError:
            cli = logging.StreamHandler(sys.stdout)
            cli.setLevel(level)
            cli_fmt = logging.Formatter(fmt)
            cli.setFormatter(cli_fmt)
            root.addHandler(cli)

    if file is not None:
        fh = logging.FileHandler(file, mode=mode)
        fh.setLevel(level)
        logging.Formatter.converter = time.gmtime
        fh_fmt = logging.Formatter(fmt="%(asctime)s.%(msecs)03dZ "
                                       "%(name)-18s "
                                       "%(levelname)-8s "
                                       "%(message)s",
                                   datefmt="%Y-%m-%dT%H:%M:%S")
        fh.setFormatter(fh_fmt)
        root.addHandler(fh)

    # flush the temporary log record buffer to the new handler(s)
    handlers = [h for h in root.handlers if h is not buffer]
    buffer.set_targets(handlers)
    buffer.close()
    root.removeHandler(buffer)

    initialised = True


class _BufferHandler(logging.Handler):
    def __init__(self, targets=None):
        super().__init__()
        self.targets = targets
        self.buffer = []

    def emit(self, record):
        self.buffer.append(record)

    def set_targets(self, targets):
        self.targets = targets

    def flush(self):
        self.acquire()
        try:
            if self.targets:
                for record in self.buffer:
                    for target in self.targets:
                        target.handle(record)
                self.buffer = []
        finally:
            self.release()

    def close(self):
        try:
            self.flush()
        finally:
            logging.Handler.close(self)


# direct log entries to temporary buffer on import; subsequently redirected to proper handler(s) by `init`
root = logging.getLogger("")
root.setLevel(logging.DEBUG)
buffer = _BufferHandler()
root.addHandler(buffer)
