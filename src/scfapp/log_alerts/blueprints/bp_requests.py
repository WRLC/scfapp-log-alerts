""" Azure Function Blueprint for SCFApp Requests Log Alert. """
import azure.functions as func

import src.scfapp.log_alerts.config as config
from src.scfapp.log_alerts.services.requests_service import RequestsService

bp: func.Blueprint = func.Blueprint()

REQUESTS_NCRON = config.REQUESTS_NCRON
DISABLE_EMAIL = config.DISABLE_EMAIL


# noinspection PyUnusedLocal,PyTypeChecker
@bp.timer_trigger(
    schedule=REQUESTS_NCRON,
    arg_name="applog_timer",
    run_on_startup=False
)
def RequestLogAlert(applog_timer: func.TimerRequest) -> None:
    """
    Azure Function to query Application Insights for the previous 24 hours' requests in the SCF App and send an
    email report.

    Args:
        applog_timer (func.TimerRequest): timer trigger

    """
    if DISABLE_EMAIL:  # If email is disabled, skip
        return

    requests_service = RequestsService()  # Instance of requests service
    scfapp_requests: list[dict] | None = requests_service.get_requests()  # Get requests

    if scfapp_requests:
        requests_service.send_email_wrapper(scfapp_requests)  # Send email
