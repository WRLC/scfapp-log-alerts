""" Service for parsing request data """
from datetime import timedelta, datetime, timezone
import logging
from zoneinfo import ZoneInfo

from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.monitor.query import (
    LogsQueryClient, LogsQueryStatus, LogsQueryResult, LogsQueryPartialResult, LogsTable, LogsQueryError
)
from pandas import DataFrame

from src.scfapp.log_alerts.config import (
    LOGS_RESOURCE_ID, REQUEST_TYPES, REQUESTS_TO_EMAIL_STR, REQUESTS_CC_EMAIL_BASE_STR
)
from src.scfapp.log_alerts.services.email_service import EmailService


# noinspection PyMethodMayBeStatic
class RequestsService:
    """ Service for parsing request data """
    def __init__(self):
        self.request_types: list[dict] = REQUEST_TYPES

    def get_requests(self) -> DataFrame | None:
        """
        Get the previous day's requests

        """
        ny_timezone: ZoneInfo = ZoneInfo('America/New_York')  # New York timezone
        today_start_ny: datetime = datetime.now(ny_timezone).replace(hour=0, minute=0, second=0, microsecond=0)  # Today
        yesterday_start_ny: datetime = today_start_ny - timedelta(days=1)  # Yesterday
        query_timespan: tuple[datetime, datetime] = (yesterday_start_ny, today_start_ny)  # Yesterday time span

        scfapp_requests: list[dict] = []  # List to store request data

        credential: DefaultAzureCredential = DefaultAzureCredential()  # Azure credential
        # noinspection PyTypeChecker
        client: LogsQueryClient = LogsQueryClient(credential)  # Application Insights query client

        for rtype in self.request_types:  # Iterate through each request type
            try:
                query: str = f"traces | where message has '{rtype['query_string']}'"  # Set query

                response: LogsQueryResult | LogsQueryPartialResult = client.query_resource(
                    # Query Application Insights
                    LOGS_RESOURCE_ID,
                    query,
                    timespan=query_timespan
                )

                df: DataFrame = DataFrame()  # Default to empty dataframe
                if response.status == LogsQueryStatus.SUCCESS:  # If query was successful
                    if response.tables:  # If there's data
                        table: LogsTable = response.tables[0]  # Get first table
                        df: DataFrame = DataFrame(data=table.rows, columns=table.columns)  # Convert to dataframe
                else:  # If query failed
                    error: LogsQueryError = response.partial_error  # Get error
                    logging.error(f"Query for '{rtype['type']}' failed with error: {error}")  # Log errir
                    if response.partial_data:  # If there's partial data, use it
                        table: LogsTable = response.partial_data[0]  # Get first table
                        df: DataFrame = DataFrame(data=table.rows, columns=table.columns)  # Convert to dataframe

                request_summary: dict[str, DataFrame] = {  # Create request summary
                    'type': rtype['type'],  # Request type
                    'data': df  # Request data
                }
                scfapp_requests.append(request_summary)  # Add request summary to list

            except HttpResponseError as e:  # Handle HTTP errors
                logging.error(f"HTTP error while querying for '{rtype['type']}': {e}")
                continue

            except Exception as e:  # Handle other errors
                logging.error(f"An unexpected error occurred for '{rtype['type']}': {e}", exc_info=True)
                continue

        if not scfapp_requests:  # If no request data found
            logging.info("No request data found in the specified timespan.")  # Log message
            return None

        return scfapp_requests  # Return request data

    def generate_email_body(self, scfapp_requests: list[dict], report_date: str) -> str:
        """
        Parses request data to generate a plain text email body.

        Args:
            scfapp_requests: A list of dictionaries, each containing a request type
                             and its corresponding DataFrame.
            report_date: The date for the report title.

        Returns:
            A string containing the formatted email body.
        """
        summary_data = {}
        total_requests = 0

        # Process each request type's data
        for request_info in scfapp_requests:
            req_type = request_info['type']
            df = request_info['data']
            count = len(df)
            total_requests += count

            ids = []
            if not df.empty and 'message' in df.columns:
                # Extract identifier from the end of the message string
                ids = df['message'].str.split(':').str[-1].str.strip().tolist()

            summary_data[req_type] = {
                'count': count,
                'ids': ids
            }

        # Build the email body
        body_lines = [f"Remote Storage App Requests for {report_date}\n"]

        # Summary section
        for req_type, data in summary_data.items():
            body_lines.append(f"{data['count']} - {req_type} Requests")

        body_lines.append("----")
        body_lines.append(f"{total_requests} - Total\n")

        # Details section
        for req_type, data in summary_data.items():
            if data['ids']:
                # Determine the identifier name from the request type
                if "Item" in req_type:
                    id_name = "Barcodes"
                elif "Bib" in req_type:
                    id_name = "Mms Ids"
                elif "User" in req_type:
                    id_name = "User Ids"
                else:
                    id_name = "IDs"  # Fallback

                body_lines.append(f"{req_type} Request {id_name}:")
                for req_id in data['ids']:
                    body_lines.append(f"    {req_id}")
                body_lines.append("")  # Add a blank line for spacing

        return "\n".join(body_lines).strip()

    def send_email_wrapper(self, scfapp_requests: list[dict]) -> None:
        """
        Construct and send email

        Args:
            scfapp_requests: A list of dictionaries, each containing a request type and its corresponding DataFrame.
        """
        report_date: str = (datetime.now(timezone.utc).date() - timedelta(days=1)).strftime('%Y-%m-%d')  # Report date
        email_body_text: str = self.generate_email_body(scfapp_requests, report_date)  # Create email body

        if email_body_text:  # If email body is not empty
            logging.info("Generated email body. Preparing to send email.")  # Log message

            email_service: EmailService = EmailService()  # Create email service instance

            subject: str = f"Remote Stg App Requests - {report_date}"  # Email subject
            html_body: str = f"<pre>{email_body_text}</pre>"  # Email body
            to_recipients_list: list[str] = email_service.create_email_recipients(REQUESTS_TO_EMAIL_STR)  # Email To

            if REQUESTS_CC_EMAIL_BASE_STR:
                cc_list_final: list[str] | None = email_service.create_email_recipients(  # Email CC
                    REQUESTS_CC_EMAIL_BASE_STR
                )
            else:
                cc_list_final = None

            email_service.send_email_with_acs(  # Send email using ACS
                subject=subject,
                html_body=html_body,
                to_recipients=to_recipients_list,
                cc_recipients=cc_list_final
            )
        else:  # If email body is empty
            logging.info("Email body is empty. Skipping email.")  # Log message
