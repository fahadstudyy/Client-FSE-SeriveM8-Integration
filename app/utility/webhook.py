from app.handlers.job import handle_job_quote_sent
from app.handlers.job import (
    handle_sm8_job_quote_accepted,
)


def handle_job_event(data):
    entry = data.get("entry", [{}])[0]
    job_uuid = entry.get("uuid")
    changed_fields = entry.get("changed_fields", [])

    # Redirect based on changed fields
    if "status" in changed_fields:
        print(f"Job {job_uuid} had its status updated.")
        handle_sm8_job_quote_accepted(job_uuid)
    if "quote_sent" in changed_fields:
        print(f"Job {job_uuid} had its quote sent.")
        handle_job_quote_sent(data)
