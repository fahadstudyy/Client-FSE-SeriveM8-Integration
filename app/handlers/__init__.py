from app.utility.webhook import handle_job_event
from .job_activity import handle_job_activity
from .create_job import handle_create_job
from app.handlers.job import (
    handle_hubspot_job_quote_accepted,
    handle_job_quote_sent,
)


webhook_handlers = {
    "JobActivity": handle_job_activity,
    "Job": handle_job_event,
    "CreateJob": handle_create_job,
    "QuoteAccepted": handle_hubspot_job_quote_accepted,
    "ReadyToBeQuoted": handle_job_quote_sent,
}
