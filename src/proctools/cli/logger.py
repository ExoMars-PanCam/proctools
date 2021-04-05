import logging
import logging.handlers
import sys
import time
from pathlib import Path
from typing import Optional

from . import __processor_id__

FALLBACK_LOG = Path(f"/tmp/{__processor_id__}_fallback.log")

# need to keep this at the top due to it being an annotated global (python issue34939)
initialised: bool = False


def init(
    file: Optional[Path] = None,
    stdout: bool = True,
    mode: str = "a",
    level: int = logging.INFO,
):
    global buffer, initialised, root

    if initialised:
        root.warning("Attempting to reinitialise the log; ignoring")
        return
    elif file is None and not stdout:
        # still commit critical entries to the buffer so they can be retrieved if needed
        logging.disable(logging.CRITICAL)
        return
    elif level not in (
        logging.DEBUG,
        logging.INFO,
        logging.WARNING,
        logging.ERROR,
        logging.CRITICAL,
    ):
        raise ValueError(f"'{level}' is not a valid log level")

    if file is not None:
        fh = None
        try:
            fh = logging.FileHandler(file, mode=mode)
        except PermissionError as e:
            log = logging.getLogger("logger")
            log.warning(f"{e.__class__.__name__}: {e}")
            log.warning(f"Attempting to use fallback: '{FALLBACK_LOG}'")
            try:
                fh = logging.FileHandler(FALLBACK_LOG, mode=mode)
            except PermissionError as e:
                log.warning(f"{e.__class__.__name__}: {e}")
                log.error("Unable to log to primary or fallback file; forcing stdout")
                stdout = True
        if fh is not None:
            fh.setLevel(level)
            logging.Formatter.converter = time.gmtime
            fh_fmt = logging.Formatter(
                fmt="%(asctime)s.%(msecs)03dZ %(name)-18s %(levelname)-8s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
            fh.setFormatter(fh_fmt)
            root.addHandler(fh)

    if stdout:
        fmt = "%(name)-18s %(levelname)-8s %(message)s"
        try:
            import coloredlogs

            coloredlogs.install(level=level, logger=root, fmt=fmt, stream=sys.stdout)
        except ImportError:
            sh = logging.StreamHandler(sys.stdout)
            sh.setLevel(level)
            sh_fmt = logging.Formatter(fmt)
            sh.setFormatter(sh_fmt)
            root.addHandler(sh)

    # flush the temporary log record buffer to the new handler(s)
    buffer.set_targets([h for h in root.handlers if h is not buffer])  # ok if empty
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
                        # note: getLevelName actually goes both ways (here: str -> int)
                        if logging.getLevelName(record.levelname) < target.level:
                            continue
                        target.handle(record)
                self.buffer = []
        finally:
            self.release()

    def close(self):
        try:
            self.flush()
        finally:
            logging.Handler.close(self)


# direct log entries to temporary buffer on import;
# subsequently redirected to proper handler(s) by `init`
root = logging.getLogger("")
root.setLevel(logging.DEBUG)
buffer = _BufferHandler()
root.addHandler(buffer)
