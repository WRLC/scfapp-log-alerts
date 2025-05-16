"""
Azure Function Blueprint for AppLog VFS Reporter.
This script downloads an application log from Azure VFS, parses it for specific
request types, and emails a summary report. It's a Python conversion of the
applog-vfs.pl Perl script.
"""
import azure.functions as func
import logging
import os
import datetime
import requests
import re
import src.scfapp.log_alerts.config as config
from src.scfapp.log_alerts.services.email_service import EmailService

bp = func.Blueprint()

APP_NAME = config.APP_NAME
AUTH_LOGIN_ENCODED = config.AUTH_LOGIN_ENCODED
API_HOST = config.API_HOST
DEFAULT_LOG_FILENAME = config.DEFAULT_LOG_FILENAME
VFS_LOG_PATH_TEMPLATE = config.VFS_LOG_PATH_TEMPLATE
TO_EMAIL_STR = config.TO_EMAIL_STR
CC_EMAIL_LIST_STR = config.CC_EMAIL_LIST_STR
TEMP_DIR = config.TEMP_DIR
DEBUG_LOG_FILE_NAME_OVERRIDE = config.DEBUG_LOG_FILE_NAME_OVERRIDE
REPORT_HOUR_THRESHOLD = config.REPORT_HOUR_THRESHOLD

SCRIPT_NAME = os.path.basename(__file__)


def get_current_timestamp_str():
    """Returns a string for the current local time for logging."""
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')


# noinspection PyUnusedLocal
@bp.timer_trigger(schedule="0 0 7 * * *", arg_name="applog_timer", run_on_startup=False)
def RequestLogAlert(applog_timer: func.TimerRequest) -> None:
    """
    Azure Function triggered on a timer schedule (daily at 7:00 AM UTC by default).
    Downloads, parses application log from VFS and sends a report email.
    """
    start_time_str = get_current_timestamp_str()
    logging.info(f"Starting {SCRIPT_NAME} job at {start_time_str}")

    if not AUTH_LOGIN_ENCODED:
        logging.error("AUTH_LOGIN_ENCODED is not set in config. Aborting job.")
        return

    is_debug_run = False
    log_filename_to_process = DEFAULT_LOG_FILENAME

    if DEBUG_LOG_FILE_NAME_OVERRIDE:
        log_filename_to_process = DEBUG_LOG_FILE_NAME_OVERRIDE
        is_debug_run = True
        logging.info(f"Debug run: Processing specified log file: {log_filename_to_process}")

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    report_date_obj = now_utc
    if now_utc.hour < REPORT_HOUR_THRESHOLD:
        report_date_obj = now_utc - datetime.timedelta(days=1)
    report_date_str = report_date_obj.strftime('%Y-%m-%d')

    email_service = EmailService()
    to_recipients = email_service.create_email_recipients(TO_EMAIL_STR)
    cc_recipients = []

    email_subject = f"Remote Stg App Requests - {report_date_str}"
    email_body_html = f"<p>Remote Storage App Requests for {report_date_str}</p><br/>"

    if is_debug_run:
        email_subject = f"AppLog VFS Python Test Run - {report_date_str} - {log_filename_to_process}"
        email_body_html = f"<p>Remote Storage App Requests from {log_filename_to_process} (Debug Run)</p><br/>"
    else:
        cc_recipients = email_service.create_email_recipients(CC_EMAIL_LIST_STR)

    vfs_log_path = VFS_LOG_PATH_TEMPLATE.format(app_name=APP_NAME)
    resource_url_path = f"{vfs_log_path.rstrip('/')}/{log_filename_to_process}"
    full_api_url = f"{API_HOST.rstrip('/')}{resource_url_path}"

    os.makedirs(TEMP_DIR, exist_ok=True)
    local_logfile_path = os.path.join(TEMP_DIR, log_filename_to_process)

    headers = {
        'Authorization': f"Basic {AUTH_LOGIN_ENCODED}",
        'Connection': 'keep-alive'
    }

    logging.info(f"Attempting to download log file: {full_api_url}")
    downloaded_successfully = False
    try:
        response = requests.get(full_api_url, headers=headers, timeout=60)
        response_code = response.status_code

        if response_code == 200:
            with open(local_logfile_path, 'wb') as f_out:
                f_out.write(response.content)
            logging.info(f"Log file downloaded successfully to {local_logfile_path}")
            downloaded_successfully = True
        else:
            error_text = response.text
            logging.error(
                f"Failed to download log from Kudo API. Status: {response_code}, URL: {full_api_url}, Response: "
                f"{error_text}"
            )
            email_body_html += (
                f"<p><strong>ERROR:</strong> GET({resource_url_path}) returned error code {response_code}</p>"
                f"<pre>{error_text}</pre>"
            )
            email_service.send_email_with_acs(email_subject, email_body_html, to_recipients, cc_recipients)
            raise Exception(f"Kudo API GET failed for {resource_url_path} with status {response_code}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Kudo API RequestException: {e}", exc_info=True)
        email_body_html += f"<p><strong>API Request Exception:</strong> {e}</p>"
        email_service.send_email_with_acs(email_subject, email_body_html, to_recipients, cc_recipients)
        raise

    if not downloaded_successfully:
        logging.error("Log file was not downloaded. Aborting further processing.")
        return

    physical_requests_barcodes = []
    bib_requests_mmsids = []
    digital_requests_barcodes = []
    user_digi_requests_userids = []

    patterns = {
        "physical": (re.compile(r'Create Item Request. Barcode:'), physical_requests_barcodes),
        "bib": (re.compile(r'Create Bib Request. Mms Id'), bib_requests_mmsids),
        "digital": (re.compile(r'Create Digitization Item Request. Barcode:'), digital_requests_barcodes),
        "user_digi": (re.compile(r'Create Digitization User Request. User Id'), user_digi_requests_userids),
    }

    try:
        with open(local_logfile_path, encoding='utf-8', errors='ignore') as lf:
            for line in lf:
                for key, (pattern, data_list) in patterns.items():
                    if pattern.search(line):
                        parts = line.strip().split()
                        if parts:
                            data_list.append(parts[-1])
                        break
    except FileNotFoundError:
        logging.error(f"Downloaded log file {local_logfile_path} not found for parsing.", exc_info=True)
        email_body_html += (
            f"<p><strong>Error:</strong> Downloaded file {log_filename_to_process} disappeared before parsing.</p>"
        )
        email_service.send_email_with_acs(email_subject, email_body_html, to_recipients, cc_recipients)
        raise
    except Exception as e:
        logging.error(f"Error parsing log file {local_logfile_path}: {e}", exc_info=True)
        email_body_html += f"<p><strong>Error:</strong> Failed to parse {log_filename_to_process}. Details: {e}</p>"
        email_service.send_email_with_acs(email_subject, email_body_html, to_recipients, cc_recipients)
        raise

    report_summary_html = "<pre>"
    report_summary_html += f"{len(physical_requests_barcodes):>4} - Physical Item Requests\n"
    report_summary_html += f"{len(bib_requests_mmsids):>4} - Physical Bib Requests\n"
    report_summary_html += f"{len(digital_requests_barcodes):>4} - Item Digitization Requests\n"
    report_summary_html += f"{len(user_digi_requests_userids):>4} - User Digitization Requests\n"
    report_summary_html += "----\n"
    total_requests = (len(physical_requests_barcodes) + len(bib_requests_mmsids) +
                      len(digital_requests_barcodes) + len(user_digi_requests_userids))
    report_summary_html += f"{total_requests:>4} - Total\n"
    report_summary_html += "</pre><br/>"

    email_body_html += report_summary_html

    if physical_requests_barcodes:
        email_body_html += "<p>Physical Item Request Barcodes:</p><pre>"
        for barcode in physical_requests_barcodes:
            email_body_html += f"    {barcode}\n"
        email_body_html += "</pre><br/>"

    if bib_requests_mmsids:
        email_body_html += "<p>Physical Bib Request MMS IDs:</p><pre>"
        for mmsid in bib_requests_mmsids:
            email_body_html += f"    {mmsid}\n"
        email_body_html += "</pre><br/>"

    if digital_requests_barcodes:
        email_body_html += "<p>Item Digitization Request Barcodes:</p><pre>"
        for barcode in digital_requests_barcodes:
            email_body_html += f"    {barcode}\n"
        email_body_html += "</pre><br/>"

    if user_digi_requests_userids:
        email_body_html += "<p>User Digitization Request UserIDs:</p><pre>"
        for userid in user_digi_requests_userids:
            email_body_html += f"    {userid}\n"
        email_body_html += "</pre><br/>"

    try:
        logging.info(
            f"Sending report email to: {TO_EMAIL_STR}, CC: {CC_EMAIL_LIST_STR if not is_debug_run else 'None'}")
        email_service.send_email_with_acs(email_subject, f"<html><body>{email_body_html}</body></html>", to_recipients,
                                          cc_recipients)
        logging.info("Report email sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send final report email: {e}", exc_info=True)

    try:
        if os.path.exists(local_logfile_path):
            os.remove(local_logfile_path)
            logging.info(f"Cleaned up temporary log file: {local_logfile_path}")
    except Exception as e:
        logging.warning(f"Could not clean up temporary file {local_logfile_path}: {e}", exc_info=True)

    end_time_str = get_current_timestamp_str()
    logging.info(f"Job {SCRIPT_NAME} completed at {end_time_str}")
