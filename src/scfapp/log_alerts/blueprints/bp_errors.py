"""Blueprint for SCFApp Error Alerts"""
import azure.functions as func

import src.scfapp.log_alerts.config as config
from src.scfapp.log_alerts.services.errors_service import ErrorsService

bp = func.Blueprint()

ERRORS_NCRON = config.ERRORS_NCRON
ERROR_TYPES = config.ERROR_TYPES


# noinspection PyUnusedLocal
@bp.timer_trigger(
    schedule=ERRORS_NCRON,
    arg_name="mytimer",
    run_on_startup=False
)
def ErrorLogAlert(mytimer: func.TimerRequest) -> None:
    """
    Azure Function triggered on a timer schedule to check  for error logs, process them, and send email alerts via
    Azure Communication Services.

    Args:
        mytimer (func.TimerRequest): timer trigger
    """
    errors_service: ErrorsService = ErrorsService()  # Instance of errors service

    yesterday_filestring: str = errors_service.set_filestring()  # Yesterday's date string

    for err_type in ERROR_TYPES:  # Iterate through each error type
        all_errors: list[dict] | None = errors_service.get_errors(err_type, yesterday_filestring)  # Get all errors

        if not all_errors:  # If no errors found, skip
            continue

        errors_service.send_email_wrapper(err_type, all_errors)  # Send email

        errors_service.archive_error_log(err_type, yesterday_filestring)  # Archive error log
