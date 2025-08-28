import logging
import logging.handlers
import sys
import time
from pathlib import Path
from typing import Optional

"""
The "logger" module creates an in-memory log buffer, allowing you to
defer decision as to whether you want log output. All logged records
get stored and, when you call logger.init(), any buffered records
will be output to the destination you've chosen.
"""

# Need to keep this at the top due to it being an annotated global (python issue 34939)
initialised: bool = False
level: Optional[int] = None

def init(
    file: Optional[Path] = None,
    stdout: bool = True,
    mode: str = "a",
    log_level: int = logging.INFO,
    name_col_width: int = 25,
):
    """
    This function configures logging to a file, stdout or both. When called,
    it will funnel any previously-buffered log records through the requested
    handlers. This means you could, for example, run a process and call init()
    at the end of processing, once you've determined the success/fail status
    of the procedure.
    """
    global _buffer, initialised, _root, level

    if initialised:
        _root.warning("Attempting to reinitialise the log; ignoring")
        return

    if file is None and not stdout:
        # No file or stdout output requested. Disable logging of
        # level ERROR and below. Higher errors will still be committed
        # to the buffer so they can be retrieved if needed.
        logging.disable(logging.ERROR)
        return

    if log_level not in (
        logging.DEBUG,
        logging.INFO,
        logging.WARNING,
        logging.ERROR,
        logging.CRITICAL,
    ):
        raise ValueError(f"'{log_level}' is not a valid log level")

    # Save our requested level. Not used within the module,
    # but client code may wish to know what level we're using.
    level = log_level

    if file is not None:
        # Logging to file has been requested.
        fh = None

        try:
            fh = logging.FileHandler(file, mode=mode)
        except PermissionError as e:
            # No permission to write the file in the specified location.
            # Move to the fallback directory, which is a tempfile directory
            # and should therefore be writeable.
            fallback = fallback_dir() / f"fallback_{file.name}"

            # Log the failure (this will be to screen, presumably).
            log = logging.getLogger("logger")
            log.warning(f"{e.__class__.__name__}: {e}")
            log.warning(f"Attempting to use fallback: '{fallback}'")

            # Now try again, with the fallback location.
            try:
                fh = logging.FileHandler(fallback, mode=mode)
            except PermissionError as e:
                # Yet another permission error.
                log.warning(f"{e.__class__.__name__}: {e}")
                log.error("Unable to log to primary or fallback file; forcing stdout")
                stdout = True

        if fh is not None:
            # We've managed to create a file handler. Configure it.
            fh.setLevel(log_level)
            logging.Formatter.converter = time.gmtime
            fh_fmt = logging.Formatter(
                fmt=(
                    f"%(asctime)s.%(msecs)03dZ %(name)-{name_col_width}s"
                    " %(levelname)-8s %(message)s"
                ),
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
            fh.setFormatter(fh_fmt)

            # Finally, add the handler to our default logger,
            # which was created on module import (below).
            _root.addHandler(fh)

    if stdout:
        # If stdout logging was requested, configure it - if possible,
        # use coloredlogs for this.
        fmt = f"%(name)-{name_col_width}s %(levelname)-8s %(message)s"
        try:
            import coloredlogs  # type: ignore
        except ImportError:
            # No coloredlogs available - just create a handler and
            # add it to _root.
            sh = logging.StreamHandler(sys.stdout)
            sh.setLevel(log_level)
            sh_fmt = logging.Formatter(fmt)
            sh.setFormatter(sh_fmt)
            _root.addHandler(sh)
        else:
            # coloredlogs is available. Add it to _root.
            coloredlogs.install(
                level=log_level, logger=_root, fmt=fmt, stream=sys.stdout
            )

    # Hopefully temporary: prevent pds4_tools from violating its quiet setting
    for handler in _root.handlers:
        if handler is not _buffer:
            handler.addFilter(_filter_pds4_tools)

    # Flush the temporary log record buffer to the new handler(s),
    # close and remove it.
    _buffer.set_targets(handlers)  # ok if empty
    _buffer.close()
    _root.removeHandler(_buffer)
    del _buffer

    # Remember we've initialised.
    initialised = True

def fallback_dir() -> Path:
    """
    Return a directory that we can hopefully create files in,
    for the case where the requested location lacks permissions.
    """
    import tempfile

    return Path(tempfile.gettempdir())


def _filter_pds4_tools(record):
    """
    Filter to remove unwanted PDS4 log output.
    """
    if record.name.startswith("PDS4ToolsLogger") and record.levelno < logging.WARNING:
        return False
    return True


class _BufferHandler(logging.Handler):
    """
    This class implements a handler which will capture logging
    output to a memory buffer. When init(), above, is successfully
    called with a usable output stream (file or stdout), the contents
    of this buffer will be flushed. This allows us to defer init until
    we know whether we'll want log output, without losing anything.
    """
    def __init__(self, targets=None):
        super().__init__()
        self.targets = targets
        self.buffer = []

    def emit(self, record):
        """
        This class method merely stores up log records in a list,
        with no formatting being done. When the buffer is closed,
        we'll try to flush all records through any other target
        (other logging.Handler objects) so they can format and
        output as needed.
        """
        self.buffer.append(record)

    def set_targets(self, targets):
        """
        Save a list of logging.Handler objects to which we'll try
        to flush on close().
        """
        self.targets = targets

    def flush(self):
        """
        Flush our requested data to all registered handlers.
        """

        # We need the I/O thread lock to do this bit.
        self.acquire()
        try:
            if self.targets is not None:
                for record in self.buffer:
                    for target in self.targets:
                        # note: getLevelName actually goes both ways (here: str -> int)
                        if logging.getLevelName(record.levelname) >= target.level:
                            target.handle(record)
                # We'll only empty the buffer if we've actually handed off
                # its contents somewhere.
                self.buffer = []
        finally:
            # And release the I/O lock, whether or not an exception
            # happened.
            self.release()

    def close(self):
        """
        Close the buffer - basically just flush it and call
        the parent "close" method.
        """
        try:
            self.flush()
        finally:
            logging.Handler.close(self)


# Direct log entries to temporary buffer on import;
# subsequently redirected to proper handler(s) by `init`
_root = logging.getLogger()
_root.setLevel(logging.DEBUG)
_buffer = _BufferHandler()
_root.addHandler(_buffer)
