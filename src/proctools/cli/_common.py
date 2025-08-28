import logging
import sys
import time
from typing import Callable

# typer is a library for building CLI applications. It
# uses "click" (which is another library for building CLI
# applications!) internally.
#
# Having taken "click" and wapped it with "typer", we'll now
# wrap it with our own "cli.run" function below!

import typer
from click import ClickException

from . import logger
from .status import ExitCode, ExitCodes

# These are Click context settings which will be passed down via Typer.
# max_content_width specifies how wide Click will allow help text to get.
CONTEXT_SETTINGS = dict(
    help_option_names = ["-h", "-?", "--help" ],
    max_content_width = 88
)

# Call this with a Typer object, which is your actual command line tool.
def run(cli: typer.Typer):
    """
    This is a wrapper for a Typer object which will run the relevant
    command, time it and handle exceptions and log output.
    """

    # Log command line and note dstart time.
    start = time.time()
    log = logging.getLogger(__name__)
    log.info(f"Invocation started of: {' '.join(sys.argv)}")

    # Run the Typer object with standalone_mode=False. This prevents
    # Typer from catching exceptions from Click and lets us handle
    # them ourselves.
    try:
        status = cli(standalone_mode=False)

        # Your Typer object *should* be returning an ExitCode object.
        if not isinstance(status, ExitCode):
            log.warning(
                f"Invalid exit code {status} ({type(status)}); falling back to"
                f" {ExitCodes.INTERNAL_ERROR}"
            )
            status = ExitCodes.INTERNAL_ERROR

    except ClickException as e:
        # Click raised an exception. Log it and set our own status to
        # CLI_ERROR.
        log.critical(f"{e.format_message()}")
        status = ExitCodes.CLI_ERROR
    except Exception as e:
        # Any other exception - we'll print a (partial) trace.
        import traceback

        # The logging module treats lower levels as "more debugging". So the
        # following line limits traceback output to the last two entries
        # when we've requested less than "DEBUG" logging. If we've not
        # specified a log level, it's treated as "DEBUG".
        limit = None if logger.level is None or logger.level <= logging.DEBUG else -2

        # Build the traceback.
        tb = "".join(traceback.format_exception(e.__class__, e, e.__traceback__, limit))

        # Log it as a critical error.
        log.critical(f"Uncaught exception {e.__class__.__name__}: {e}\n{tb}")

        # If the exception was thrown with an ExitCode object, use that as
        # our state. If not (or invalid) then we'll use INTERNAL_ERROR.
        status = getattr(e, "code", None)
        if not isinstance(status, ExitCode):
            log.warning(
                f"Invalid exit code {status} ({type(status)}); falling back to"
                f" {ExitCodes.INTERNAL_ERROR}"
            )
            status = ExitCodes.INTERNAL_ERROR

    # Log processing time from start to here.
    log.info(f"Invocation took {time.time() - start:6f}s")

    # For non-success, we'll force the collected log info to be written,
    # retrospectively, to *somewhere*.
    if status != ExitCodes.SUCCESS and not logger.initialised:
        # Invent a location for the log.
        from datetime import datetime
        timestamp = datetime.utcnow().strftime("%Y%m%dt%H%M%Sz")
        fallback = logger.fallback_dir() / f"processing_failure_{timestamp}.log"

        # Warn what we're up to.
        log.warning(
            "Logger not initialised; writing debug log to fallback location:"
            f" '{fallback}'"
        )

        # And write the log.
        logger.init(
            file=fallback,
            stdout=(status == ExitCodes.CLI_ERROR),
            mode="a",
            log_level=logging.DEBUG,
        )

    log.info(f"Exiting with code {status}")
    logging.shutdown()

    # Finally return with our exit code.
    sys.exit(status.code)


def version_callback_for(name: str, version: str) -> Callable[[bool], None]:
    """
    This function makes a closure which will output a name and version when
    requested. It allows module users to create a typer.Option callback without
    having to create their own function or lambda.
    """
    def version_callback(value: bool) -> None:
        if value:
            typer.echo(f"{name} v{version}")
            raise typer.Exit()

    return version_callback
