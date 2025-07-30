"""Configuration for SCFApp Log Alerts"""
import os
from typing import Any

# Azure Storage
STORAGE_CONNECTION_STRING: str = os.environ.get("STORAGE_CONNECTION_STRING")
SHARE_NAME: str = os.environ.get("SHARE_NAME")
REPORT_PATH: str = os.environ.get("REPORT_PATH")

# Application Insights
LOGS_RESOURCE_ID: str = os.environ.get("LOGS_RESOURCE_ID")

# Azure Communication Services
ACS_CONNECTION_STRING: str = os.environ.get("ACS_CONNECTION_STRING")
ACS_SENDER_ADDRESS: str = os.environ.get("ACS_SENDER_ADDRESS")

# Requests recipients
REQUESTS_TO_EMAIL_STR: str = os.environ.get("REQUESTS_TO_EMAIL_STR")
REQUESTS_CC_EMAIL_BASE_STR: str | None = None

if os.environ.get("REQUESTS_CC_EMAIL_BASE_STR") and os.environ.get("REQUESTS_CC_EMAIL_BASE_STR") != "":
    REQUESTS_CC_EMAIL_BASE_STR = os.environ.get("REQUESTS_CC_EMAIL_BASE_STR")

# RequestHandler error recipients
RH_ERRORS_TO_EMAIL_STR: str | None = os.environ.get("RH_ERRORS_TO_EMAIL_STR")
RH_ERRORS_CC_EMAIL_STR: str | None = None

if os.environ.get("RH_ERRORS_CC_EMAIL_STR") and os.environ.get("RH_ERRORS_CC_EMAIL_STR") != "":
    RH_ERRORS_CC_EMAIL_STR = os.environ.get("RH_ERRORS_CC_EMAIL_STR")

# ItemHandler error recipients
IH_ERRORS_TO_EMAIL_STR: str | None = os.environ.get("IH_ERRORS_TO_EMAIL_STR")
IH_ERRORS_CC_EMAIL_STR: str | None = None

if os.environ.get("IH_ERRORS_CC_EMAIL_STR") and os.environ.get("IH_ERRORS_CC_EMAIL_STR") != "":
    IH_ERRORS_CC_EMAIL_STR = os.environ.get("IH_ERRORS_CC_EMAIL_STR")

# LoanRequestHandler error recipients
LRH_ERRORS_TO_EMAIL_STR: str | None = os.environ.get("LRH_ERRORS_TO_EMAIL_STR")
LRH_ERRORS_CC_EMAIL_STR: str | None = None

if os.environ.get("LRH_ERRORS_CC_EMAIL_STR") and os.environ.get("LRH_ERRORS_CC_EMAIL_STR") != "":
    LRH_ERRORS_CC_EMAIL_STR = os.environ.get("LRH_ERRORS_CC_EMAIL_STR")

# RequestCanceled error recipients
RC_ERRORS_TO_EMAIL_STR = os.environ.get("RC_ERRORS_TO_EMAIL_STR")
RC_ERRORS_CC_EMAIL_STR = None

if os.environ.get("RC_ERRORS_CC_EMAIL_STR") and os.environ.get("RC_ERRORS_CC_EMAIL_STR") != "":
    RC_ERRORS_CC_EMAIL_STR = os.environ.get("RC_ERRORS_CC_EMAIL_STR")

# Timer Trigger schedules
REQUESTS_NCRON: str = os.environ.get("REQUESTS_NCRON")
ERRORS_NCRON = os.environ.get("ERRORS_NCRON")

# Disable email
DISABLE_EMAIL: bool = False
disable_email_setting: str | None = os.environ.get("DISABLE_EMAIL")

if disable_email_setting and disable_email_setting.strip().lower() in ("true", "1", "yes", "on"):
    DISABLE_EMAIL = True

# Request types to check
REQUEST_TYPES: list[dict[str, Any]] = [
    {
        'type': 'Physical Item',
        'query_string': 'Create Item Request. Barcode:'
    },
    {
        'type': 'Physical Bib',
        'query_string': 'Create Bib Request. Mms Id'
    },
    {
        'type': 'Item Digitization',
        'query_string': 'Create Digitization Item Request. Barcode:'
    },
    {
        'type': 'User Digitization',
        'query_string': 'Create Digitization User Request. User Id'
    }
]

# Error types to check
ERROR_TYPES: list[dict] = [
    {
        'type': 'RequestHandler',
        'to': RH_ERRORS_TO_EMAIL_STR,
        'cc': RH_ERRORS_CC_EMAIL_STR
    },
    {
        'type': 'ItemsHandler',
        'to': IH_ERRORS_TO_EMAIL_STR,
        'cc': IH_ERRORS_CC_EMAIL_STR
    },
    {
        'type': 'LoanRequestHandler',
        'to': LRH_ERRORS_TO_EMAIL_STR,
        'cc': LRH_ERRORS_CC_EMAIL_STR
    },
    {
        'type': 'RequestCanceled',
        'to': RC_ERRORS_TO_EMAIL_STR,
        'cc': RC_ERRORS_CC_EMAIL_STR
    }
]
