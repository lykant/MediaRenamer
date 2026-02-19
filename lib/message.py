import lib.logger as logger
import lib.constants as cons
import lib.metadata as meta
from pathlib import Path
from datetime import datetime

APP_TITLE = "MEDIA RENAMER"
MSG_PREFIX = "{no}- {name}" + str.rjust(">> ", 5)  # type: ignore
LENGTH_PREFIX = 20


def print_app_header():
    """Print an app header for the start of the renaming process."""
    # Log the start of the renaming process with a timestamped header
    log.info(cons.ENTER + cons.EQUAL * cons.LINE_LENGTH)
    log.info(
        str.center(
            f"{datetime.now().strftime(cons.ISO_FORMAT)} - {APP_TITLE} STARTED",
            cons.LINE_LENGTH,
            " ",
        )
    )


def print_app_footer():
    """Print an app footer for the end of the renaming process."""
    # Final log entry to indicate completion of the renaming process
    log.info(cons.EQUAL * cons.LINE_LENGTH)
    log.info(f"{datetime.now().strftime(cons.ISO_FORMAT)} - {APP_TITLE} FINISHED")
    log.info(cons.EQUAL * cons.LINE_LENGTH)


def print_folder_title(folder: Path):
    """Print a title for the current folder being processed."""
    log.info(cons.EQUAL * cons.LINE_LENGTH)
    log.info(str.center(f" {str(folder).upper()} ", cons.LINE_LENGTH))


def print_conflict_title():
    """Print a header for the conflict processing phase."""
    log.info(cons.EQUAL * cons.LINE_LENGTH)
    # Centered header for conflict processing
    log.info(str.center("CONFLICTS RUNNING", cons.LINE_LENGTH, " "))
    log.info(cons.HYPHEN * cons.LINE_LENGTH)


def print_processing_title(meta: meta.Metadata, dict_file_counts: dict):
    """Print a header for the current file extension being processed."""
    # Get the number of files being processed for the current extension
    file_number = dict_file_counts.get(meta.ext, 0)  # type: ignore
    if file_number == 0 or meta.no > 1:
        return

    # Visual separator for processing phase
    log.info(str.center(f" {meta.ext.upper()} ", cons.LINE_LENGTH, cons.HYPHEN))  # type: ignore
    log.info(f"{file_number} file(s) being processed... ")
    log.info(cons.HYPHEN * cons.LINE_LENGTH)


def print_processing_message(meta: meta.Metadata):
    """Print a message indicating the current file being processed."""
    log.info(
        str.ljust(
            MSG_PREFIX.format(no=meta.no, name=meta.actual_full_name), LENGTH_PREFIX
        )
        + "Processing..."
    )


def print_rename_message(meta: meta.Metadata):
    """Print a message indicating the file is renamed successfully."""
    log.info(
        str.ljust(
            MSG_PREFIX.format(no=meta.no, name=meta.actual_full_name), LENGTH_PREFIX
        )
        + f"Renamed to {meta.new_full_name}."
    )


def print_name_remains_same(meta: meta.Metadata):
    """Print a message indicating the file name remains the same."""
    log.info(
        str.ljust(
            MSG_PREFIX.format(no=meta.no, name=meta.actual_full_name), LENGTH_PREFIX
        )
        + "File name remains the same."
    )


def print_file_path_none(meta: meta.Metadata):
    """Print a message indicating the file path is None, which is an error."""
    log.error(
        str.ljust(
            MSG_PREFIX.format(no=meta.no, name=meta.actual_full_name), LENGTH_PREFIX
        )
        + "Error: File path cannot be none!"
    )


def print_rename_error(meta: meta.Metadata):
    """Print a message indicating the rename operation failed."""
    log.error(
        str.ljust(
            MSG_PREFIX.format(no=meta.no, name=meta.actual_full_name), LENGTH_PREFIX
        )
        + f"Failed to rename to {meta.new_full_name}."
    )


def print_separator():
    """Print a visual separator in the logs."""
    log.info(cons.HYPHEN * cons.LINE_LENGTH)


def setup_logger(app_name: str):
    """Set up the logger for the application."""
    global log
    log = logger.setup_logging(app_name)
