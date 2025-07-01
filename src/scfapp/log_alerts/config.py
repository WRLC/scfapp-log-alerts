"""Configuration for SCFApp Log Alerts"""
import os


# Azure Storage
STORAGE_CONNECTION_STRING = os.environ.get("STORAGE_CONNECTION_STRING")  # Azure Storage connection string
SHARE_NAME = os.environ.get("SHARE_NAME")  # Azure Storage fileshare name
REPORT_PATH = os.environ.get("REPORT_PATH")  # Path to report files


# Application Insights
LOGS_RESOURCE_ID = os.environ.get("LOGS_RESOURCE_ID")  # Azure Application Insights resource ID


# Azure Communication Services
ACS_CONNECTION_STRING = os.environ.get("ACS_CONNECTION_STRING")  # Azure Communication Services connection string
ACS_SENDER_ADDRESS = os.environ.get("ACS_SENDER_ADDRESS")  # ACS sender address


# Requests Alert
REQUESTS_TO_EMAIL_STR = os.environ.get("REQUESTS_TO_EMAIL_STR")  # Requests to recipients

if os.environ.get("REQUESTS_CC_EMAIL_BASE_STR") and os.environ.get("REQUESTS_CC_EMAIL_BASE_STR") != "":
    REQUESTS_CC_EMAIL_BASE_STR = os.environ.get("REQUESTS_CC_EMAIL_BASE_STR")  # Requests CC recipients
else:
    REQUESTS_CC_EMAIL_BASE_STR = None

REQUESTS_NCRON = os.environ.get("REQUESTS_NCRON")  # Requests alert timer trigger

REQUEST_TYPES = [  # Request types to check
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


# Error Alerts
RH_ERRORS_TO_EMAIL_STR = os.environ.get("RH_ERRORS_TO_EMAIL_STR")  # RequestHandler error to recipients

if os.environ.get("RH_ERRORS_CC_EMAIL_STR") and os.environ.get("RH_ERRORS_CC_EMAIL_STR") != "":
    RH_ERRORS_CC_EMAIL_STR = os.environ.get("RH_ERRORS_CC_EMAIL_STR")  # RequestHandler error CC recipients
else:
    RH_ERRORS_CC_EMAIL_STR = None

IH_ERRORS_TO_EMAIL_STR = os.environ.get("IH_ERRORS_TO_EMAIL_STR")  # ItemsHandler error to recipients

if os.environ.get("IH_ERRORS_CC_EMAIL_STR") and os.environ.get("IH_ERRORS_CC_EMAIL_STR") != "":
    IH_ERRORS_CC_EMAIL_STR = os.environ.get("IH_ERRORS_CC_EMAIL_STR")  # ItemsHandler error CC recipients
else:
    IH_ERRORS_CC_EMAIL_STR = None

LRH_ERRORS_TO_EMAIL_STR = os.environ.get("LRH_ERRORS_TO_EMAIL_STR")  # LoanRequestHandler error to recipients

if os.environ.get("LRH_ERRORS_CC_EMAIL_STR") and os.environ.get("LRH_ERRORS_CC_EMAIL_STR") != "":
    LRH_ERRORS_CC_EMAIL_STR = os.environ.get("LRH_ERRORS_CC_EMAIL_STR")  # LoanRequestHandler error CC recipients
else:
    LRH_ERRORS_CC_EMAIL_STR = None

RC_ERRORS_TO_EMAIL_STR = os.environ.get("RC_ERRORS_TO_EMAIL_STR")  # RequestCanceled error to recipients

if os.environ.get("RC_ERRORS_CC_EMAIL_STR") and os.environ.get("RC_ERRORS_CC_EMAIL_STR") != "":
    RC_ERRORS_CC_EMAIL_STR = os.environ.get("RC_ERRORS_CC_EMAIL_STR")  # RequestCanceled error CC recipients
else:
    RC_ERRORS_CC_EMAIL_STR = None

ERRORS_NCRON = os.environ.get("ERRORS_NCRON")  # Error alerts timer trigger

ERROR_TYPES = [  # Error types to check
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
