""" Service for parsing error data """
import csv
import io
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.fileshare import ShareFileClient
# noinspection PyProtectedMember
from azure.storage.fileshare._download import StorageStreamDownloader

from src.scfapp.log_alerts.config import STORAGE_CONNECTION_STRING, SHARE_NAME, REPORT_PATH
from src.scfapp.log_alerts.services.email_service import EmailService


# noinspection PyMethodMayBeStatic
class ErrorsService:
    """ Service for parsing error data """
    def __init__(self):
        self.storage_connection_string = STORAGE_CONNECTION_STRING
        self.share_name = SHARE_NAME
        self.report_path = REPORT_PATH

    def get_errors(self, err_type: dict[str, str], yesterday_filestring: str) -> list[dict] | None:
        """
        Get errors from CSV file and move file to OLD folder

        Args:
            err_type (str): Error type
            yesterday_filestring (str): Yesterday filestring

        """
        all_errors: list[dict] = []  # Empty list for errors
        filename: str = f"{err_type['type']}_log_{yesterday_filestring}.csv"  # Filename
        filepath: str = f"{self.report_path}/{filename}"  # Filepath

        try:
            file_client: ShareFileClient = ShareFileClient.from_connection_string(  # File client
                conn_str=self.storage_connection_string,
                share_name=self.share_name,
                file_path=filepath
            )

            stream: StorageStreamDownloader = file_client.download_file()  # Download file
            data: io.StringIO = io.StringIO(stream.readall().decode())  # Decode file
            csv_reader: csv.DictReader = csv.DictReader(data)  # Convert data to dictionary

            for row in csv_reader:  # Iterate through each row
                all_errors.append(row)  # Add error dictionary to list

        except ResourceNotFoundError:  # If file not found
            logging.warning(f"File not found, skipping: {filename}")  # Log message
            return None
        except Exception as e:  # Handle other errors
            logging.error(f"An unexpected error occurred while processing {filename}: {e}")  # Log error
            return None

        return all_errors

    def set_filestring(self) -> str:
        """
        Set yesterday date string for file name

        Returns:
            str: Yesterday filestring
        """
        ny_timezone: ZoneInfo = ZoneInfo('America/New_York')  # New York timezone
        today_start_ny: datetime = datetime.now(ny_timezone).replace(hour=0, minute=0, second=0, microsecond=0)  # Today
        yesterday_start_ny: datetime = today_start_ny - timedelta(days=1)  # Yesterday
        yesterday_filestring: str = datetime.strftime(yesterday_start_ny, "%Y%m%d")

        return yesterday_filestring

    def generate_email_body(self, error_type: dict[str, str], scfapp_errors: list[dict]):
        """
        Parses request data to generate a plain text email body.

        Args:
            error_type (str): Error type
            scfapp_errors (list[dict]): A list of dictionaries, each containing an error

        Returns:
            str: A string containing the formatted email body.
        """
        df = pd.DataFrame(scfapp_errors)
        html_table = df.to_html(index=False, border=0, classes="error-table")

        html_body = f"""
        <html>
        <head>
        <style>
            body {{ font-family: sans-serif; }}
            .error-table {{
                border-collapse: collapse;
                width: 100%;
                font-size: 12px;
            }}
            .error-table th, .error-table td {{
                border: 1px solid #dddddd;
                text-align: left;
                padding: 8px;
            }}
            .error-table th {{
                background-color: #f2f2f2;
                font-weight: bold;
            }}
            .error-table tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
        </style>
        </head>
        <body>
            <p>RSA {error_type['type']} logged ERRORS yesterday</p>
            {html_table}
        </body>
        </html>
        """

        return html_body

    def send_email_wrapper(self, err_type: dict[str, str], all_errors: list[dict]) -> None:
        """
        Construct and send email

        Args:
            err_type (str): Error type
            all_errors (list[dict]): A list of dictionaries, each containing an error
        """
        report_date: str = (datetime.now(timezone.utc).date() - timedelta(days=1)).strftime('%Y-%m-%d')  # Report date
        email_body = self.generate_email_body(err_type, all_errors)  # Email body

        if email_body:
            logging.info("Generated email body. Preparing to send email.")  # Log message

            email_service: EmailService = EmailService()  # Create email service instance

            subject: str = f"Remote Stg App {err_type['type']} Errors - {report_date}"  # Email subject
            html_body: str = email_body
            to_recipients_list: list[str] = email_service.create_email_recipients(err_type['to'])

            if err_type['cc']:
                cc_list_final: list[str] | None = email_service.create_email_recipients(err_type['cc'])

            else:
                cc_list_final = None

            email_service.send_email_with_acs(  # Send email using ACS
                subject=subject,
                html_body=html_body,
                to_recipients=to_recipients_list,
                cc_recipients=cc_list_final
            )
        else:
            logging.info("Email body is empty. Skipping email.")

    def archive_error_log(self, err_type: dict[str, str], yesterday_filestring: str) -> None:
        """
        Moves a processed error log file to the 'OLD' directory within the same share.

        Args:
            err_type (str): The type of error log to move.
            yesterday_filestring (str): The date string for the log file.
        """
        source_filename = f"{err_type['type']}_log_{yesterday_filestring}.csv"
        source_filepath = f"{self.report_path}/{source_filename}"
        destination_filepath = f"{self.report_path}/OLD/{source_filename}"

        logging.info(f"Attempting to move {source_filepath} to {destination_filepath}")
        try:
            file_client = ShareFileClient.from_connection_string(
                conn_str=self.storage_connection_string,
                share_name=self.share_name,
                file_path=source_filepath
            )
            # rename_file with a new path acts as a "move" operation.
            file_client.rename_file(new_name=destination_filepath)
            logging.info(f"Successfully moved log file.")

        except ResourceNotFoundError:
            # This can happen if the file was already moved or never existed.
            logging.warning(f"Could not find file to move: {source_filepath}")
        except Exception as e:
            logging.error(f"Failed to move file {source_filepath}: {e}", exc_info=True)


