# SCFApp Log Alerts

Azure Function App written in Python to provide automated monitoring and alerting for the Alma Remote Storage App. Runs on a schedule to check for application errors and request logs, sending summary emails to designated recipients.

## How It Works

The application is composed of two main functions, each running on a timer trigger:

1.  **Error Log Alerts**:
    *   On a daily schedule (defined by `ERRORS_NCRON`), this function scans a specific path in an Azure File Share for new CSV error logs.
    *   It processes logs for a configurable list of error types (e.g., `RequestHandler`, `ItemsHandler`).
    *   If a log file for a specific error type is found, it parses the data using `pandas` and generates a distinct HTML email report.
    *   The email is sent to a configurable list of recipients using Azure Communication Services.
    *   After processing, the log file is automatically moved to an `OLD` directory to prevent reprocessing.

2.  **Request Log Alerts**:
    *   On a separate daily schedule (defined by `REQUESTS_NCRON`), this function queries Azure Application Insights.
    *   It gathers statistics for various application request types (e.g., `Physical Item`, `User Digitization`).
    *   It sends a single, consolidated HTML email report summarizing the daily request counts.

## Technology Stack

-   **Cloud Platform**: Microsoft Azure
-   **Compute**: Azure Functions
-   **Language**: Python
-   **Data Sources**: Azure File Share, Azure Application Insights
-   **Notifications**: Azure Communication Services
-   **Key Libraries**: `pandas`, `azure-functions`, `azure-storage-fileshare`, `azure-communication-email`, `azure-monitor-query`

## Configuration

This application is configured entirely through environment variables. For local development, these should be placed in `local.settings.json`.

| Variable                       | Description                                                              |
| ------------------------------ | ------------------------------------------------------------------------ |
| `STORAGE_CONNECTION_STRING`    | Connection string for the Azure Storage Account.                         |
| `SHARE_NAME`                   | The name of the Azure File Share where logs are stored.                  |
| `REPORT_PATH`                  | The directory path within the file share containing the CSV logs.        |
| `LOGS_RESOURCE_ID`             | The full resource ID for the Application Insights instance.              |
| `ACS_CONNECTION_STRING`        | Connection string for the Azure Communication Services resource.         |
| `ACS_SENDER_ADDRESS`           | The "From" email address configured in ACS.                              |
| `ERRORS_NCRON`                 | The NCronTab expression for the error alert schedule (e.g., `0 0 5 * * *`). |
| `REQUESTS_NCRON`               | The NCronTab expression for the request alert schedule.                  |
| `*_TO_EMAIL_STR` / `*_CC_EMAIL_STR` | Comma-separated strings of email addresses for various alerts.           |
| `DISABLE_EMAIL`                | Disable email reports (e.g., in non-production deployment slot)          |

## Local Development

### Prerequisites

-   Python 3.9+
-   Azure Functions Core Tools
-   An Azure Storage emulator like Azurite, or a connection to a live Azure Storage account.
 
## License

This project is licensed under the MIT License. See the `LICENSE` file for details.