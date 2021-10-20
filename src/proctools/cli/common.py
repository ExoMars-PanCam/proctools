import logging
import sys
import time

import typer
from click import ClickException

from .. import __project__, __version__, logger
from ..util import ExitCode, ExitCodes

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"], max_content_width=88)


def cli_runner(cli: typer.Typer):
    start = time.time()
    log = logging.getLogger(__name__)
    log.info(f"Invocation started of: {' '.join(sys.argv)}")
    try:
        # prevent Typer from catching and printing (click) exceptions (standalone_mode)
        status = cli(standalone_mode=False)
        if not isinstance(status, ExitCode):
            log.warning(
                f"Invalid exit code {status} ({type(status)}); falling back to"
                f" {ExitCodes.INTERNAL_ERROR}"
            )
            status = ExitCodes.INTERNAL_ERROR

    except ClickException as e:
        log.critical(f"{e.format_message()}")
        status = ExitCodes.CLI_ERROR
    except Exception as e:
        import traceback

        limit = None if logger.level is None or logger.level <= logging.DEBUG else -2
        tb = "".join(traceback.format_exception(e.__class__, e, e.__traceback__, limit))
        log.critical(f"Uncaught exception {e.__class__.__name__}: {e}\n{tb}")
        status = getattr(e, "code", None)
        if not isinstance(status, ExitCode):
            log.warning(
                f"Invalid exit code {status} ({type(status)}); falling back to"
                f" {ExitCodes.INTERNAL_ERROR}"
            )
            status = ExitCodes.INTERNAL_ERROR

    if not logger.initialised:
        if status != 0:
            log.warning(
                "Logger not initialised; writing debug log to fallback:"
                f" '{logger.FALLBACK_LOG}'"
            )
        logger.init(
            file=logger.FALLBACK_LOG,
            stdout=bool(status),
            mode="a",
            log_level=logging.DEBUG,
        )

    log.info(f"Invocation took {time.time() - start:6f}s")
    log.info(f"Exiting with code {status}")
    logging.shutdown()
    sys.exit(status.code)


def version_callback(value: bool):
    if value:
        typer.echo(f"{__project__} v{__version__}")
        raise typer.Exit()
