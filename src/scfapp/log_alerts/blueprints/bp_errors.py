"""Blueprint for SCFApp Error Alerts"""
from azure.functions import Blueprint
import logging
import os
import datetime
import requests
import csv
import azure.functions as func
from src.scfapp.log_alerts.services.email_service import EmailService
import src.scfapp.log_alerts.config as config

bp = Blueprint()

APP_NAME = config.APP_NAME
AUTH_LOGIN_ENCODED = config.AUTH_LOGIN_ENCODED
API_HOST = config.API_HOST
VFS_REPORTS_PATH = config.VFS_REPORTS_PATH
HANDLER_NAME = config.HANDLER_NAME
TO_EMAIL_STR = config.TO_EMAIL_STR
CC_EMAIL_BASE_STR = config.CC_EMAIL_BASE_STR
CC_EMAIL_ITEMSHANDLER_STR = config.CC_EMAIL_ITEMSHANDLER_STR
CC_EMAIL_REQUESTHANDLER_STR = config.CC_EMAIL_REQUESTHANDLER_STR
TEMP_DIR = config.TEMP_DIR


@bp.timer_trigger(schedule="0 0 5 * * *", arg_name="mytimer", run_on_startup=False)
def ErrorLogAlert(mytimer: func.TimerRequest) -> None:
    """
    Azure Function triggered on a timer schedule to check Kudu VFS for error logs,
    process them, and send email alerts via Azure Communication Services.
    CRON for schedule: "Second Minute Hour Day Month DayOfWeek"
    Example: "0 0 5 * * *" -> 5:00 AM UTC daily
    Example: "0 */15 * * * *" -> Every 15 minutes
    """
    utc_timestamp = datetime.datetime.now(datetime.UTC).isoformat()
    if mytimer.past_due:
        logging.info('The timer is past due!')
    logging.info(f'Python timer trigger function KuduLogProcessor ran at {utc_timestamp} for handler: {HANDLER_NAME}')

    if not AUTH_LOGIN_ENCODED:
        logging.error("AUTH_LOGIN_ENCODED is not set. Aborting KuduLogProcessor.")
        return

    now = datetime.datetime.now()
    date_str_yyyymmdd = now.strftime('%Y%m%d')
    target_filename = f"{HANDLER_NAME}_log_{date_str_yyyymmdd}.csv"

    logging.info(f"Processing for handler: {HANDLER_NAME}, target file: {target_filename}")
    os.makedirs(TEMP_DIR, exist_ok=True)

    email_subject_prefix = f"Remote Stg App {HANDLER_NAME}"
    email_subject = f"{email_subject_prefix} Errors - {date_str_yyyymmdd}"

    email_service = EmailService()

    cc_list_final = email_service.create_email_recipients(CC_EMAIL_BASE_STR)
    if HANDLER_NAME == "ItemsHandler" and CC_EMAIL_ITEMSHANDLER_STR:
        cc_list_final.extend(email_service.create_email_recipients(CC_EMAIL_ITEMSHANDLER_STR))
    if HANDLER_NAME == "RequestHandler" and CC_EMAIL_REQUESTHANDLER_STR:
        cc_list_final.extend(email_service.create_email_recipients(CC_EMAIL_REQUESTHANDLER_STR))

    to_recipients_list = email_service.create_email_recipients(TO_EMAIL_STR)
    report_body_html = f"<body>\nRSA {HANDLER_NAME} logged ERRORS on {date_str_yyyymmdd}:\n<pre>\n"

    vfs_file_path_on_server = f"{VFS_REPORTS_PATH}{target_filename}"
    local_file_path = os.path.join(TEMP_DIR, target_filename)

    headers = {
        'Authorization': f"Basic {AUTH_LOGIN_ENCODED}",
        'Connection': 'keep-alive'
    }
    api_url = f"{API_HOST}{vfs_file_path_on_server}"

    logging.info(f"Attempting to download: {api_url}")
    # noinspection PyUnusedLocal
    file_downloaded = False
    try:
        response = requests.get(api_url, headers=headers, timeout=60)
        response_code = response.status_code

        if response_code == 200:
            with open(local_file_path, 'wb') as f_out:
                f_out.write(response.content)
            logging.info(f"File downloaded successfully to {local_file_path}")
            file_downloaded = True
        elif response_code == 404:
            logging.info(f"No {HANDLER_NAME} error log found for {date_str_yyyymmdd} at {api_url}")
            return
        else:
            error_text = response.text
            logging.error(
                f"Failed to download file from Kudu API. Status: {response_code}, URL: {api_url}, Response: "
                f"{error_text}"
            )
            report_body_html += f"API Error: Could not download {target_filename}.\n"
            report_body_html += f"URL: {api_url}\nStatus Code: {response_code}\nResponse: {error_text}\n</pre>\n</body>"
            email_service.send_email_with_acs(email_subject, report_body_html, to_recipients_list, cc_list_final)
            raise Exception(f"Kudu API GET failed with status {response_code}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Kudu API RequestException: {e}", exc_info=True)
        report_body_html += f"API Request Exception: {e}\n</pre>\n</body>"
        email_service.send_email_with_acs(email_subject, report_body_html, to_recipients_list, cc_list_final)
        raise

    if not file_downloaded:
        logging.error("File was not downloaded, but no exception was caught earlier. Aborting processing.")
        return

    logging.info(f"Processing downloaded file: {local_file_path}")
    separator_line = "--------------------+----------------+--------------------\n"
    errors_found_in_csv = False
    try:
        if os.path.getsize(local_file_path) == 0:
            logging.info(f"File {target_filename} is empty. No errors to process.")
        else:
            with open(local_file_path, newline='', encoding='utf-8-sig') as fh_in:
                csv_reader = csv.reader(fh_in)
                for i, row in enumerate(csv_reader):
                    if i == 0 and "Level" in row and "Logger" in row and "Message" in row:
                        logging.info(f"CSV Header: {row}")
                        continue

                    if len(row) >= 3:
                        errors_found_in_csv = True
                        col0 = str(row[0])
                        col1 = str(row[1])
                        col2 = str(row[2])

                        line = col0.ljust(19)
                        line += " | "
                        line += col1
                        line = line.ljust(36 + 19)
                        line += " | "
                        line += col2

                        report_body_html += f"{line}\n"
                        report_body_html += separator_line
                    elif row:
                        logging.warning(f"Skipping malformed row in CSV (row {i + 1}): {row}")

        if not errors_found_in_csv and os.path.getsize(local_file_path) > 0:
            logging.info(
                f"File {target_filename} was downloaded but contained no processable error rows (e.g., only header or "
                f"empty data rows)."
            )

    except FileNotFoundError:
        logging.error(f"Downloaded file '{local_file_path}' not found for processing.", exc_info=True)
        report_body_html += f"Error: Downloaded file {target_filename} disappeared before processing.\n</pre>\n</body>"
        email_service.send_email_with_acs(email_subject, report_body_html, to_recipients_list, cc_list_final)
        raise
    except csv.Error as e:
        logging.error(f"CSV parsing error in '{local_file_path}': {e}", exc_info=True)
        report_body_html += f"Error: CSV parsing failed for {target_filename}.\nDetails: {e}\n</pre>\n</body>"
        email_service.send_email_with_acs(email_subject, report_body_html, to_recipients_list, cc_list_final)
        raise
    except Exception as e:
        logging.error(f"Error processing CSV file '{local_file_path}': {e}", exc_info=True)
        report_body_html += f"Error: Failed to process {target_filename}.\nDetails: {e}\n</pre>\n</body>"
        email_service.send_email_with_acs(email_subject, report_body_html, to_recipients_list, cc_list_final)
        raise

    delete_headers = headers.copy()
    delete_headers['If-Match'] = '*'
    try:
        logging.info(f"Attempting to DELETE {vfs_file_path_on_server} from VFS...")
        del_response = requests.delete(api_url, headers=delete_headers, timeout=30)
        logging.info(f"DELETE {vfs_file_path_on_server} => {del_response.status_code}")
        if del_response.status_code not in [200, 204]:
            # noinspection SqlNoDataSourceInspection
            logging.warning(
                f"DELETE from VFS was not successful. Status: {del_response.status_code}, "
                f"Response: {del_response.text}"
            )
            report_body_html += (
                f"\nWarning: Failed to delete {target_filename} from VFS. Status: {del_response.status_code}\n"
            )
    except requests.exceptions.RequestException as e:
        logging.warning(f"DELETE request for {vfs_file_path_on_server} failed: {e}", exc_info=True)
        report_body_html += f"\nWarning: DELETE request for {target_filename} from VFS failed: {e}\n"

    if errors_found_in_csv:
        report_body_html += f"\n</pre>\nSource file processed: {target_filename} (attempted delete from VFS)\n"
    else:
        report_body_html = (
            f"<body>\nRSA {HANDLER_NAME}: No specific error lines found in {target_filename} on {date_str_yyyymmdd} ("
            f"file might be empty, header-only, or contain no parsable errors).\n")

        report_body_html += (
            f"The file {target_filename} has been processed and an attempt was made to delete it from VFS.\n"
        )
        email_subject = f"{email_subject_prefix} - No Errors Reported in Log - {date_str_yyyymmdd}"

    report_body_html += "</body>\n"
    email_service.send_email_with_acs(email_subject, report_body_html, to_recipients_list, cc_list_final)

    try:
        if os.path.exists(local_file_path):
            os.remove(local_file_path)
            logging.info(f"Cleaned up temporary file: {local_file_path}")
    except Exception as e:
        logging.warning(f"Could not clean up temporary file {local_file_path}: {e}", exc_info=True)

    logging.info(
        f"Python timer trigger function KuduLogProcessor finished for handler: {HANDLER_NAME} at "
        f"{datetime.datetime.now(datetime.UTC).isoformat()}"
    )
