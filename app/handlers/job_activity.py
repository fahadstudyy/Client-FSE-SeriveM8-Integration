import os
import logging
import requests
from dotenv import load_dotenv
from datetime import datetime
from app.handlers.job import get_job
from app.utility.hubspot import (
    find_hubspot_deal_by_job_uuid,
    update_hubspot_deal,
    CLOSED_WON_PIPELINE_ID,
    CONSULT_VISIT_SCHEDULED_PIPELINE_ID,
)


load_dotenv()

SERVICEM8_API_KEY = os.getenv("SERVICEM8_API_KEY")
HUBSPOT_API_TOKEN = os.getenv("HUBSPOT_API_TOKEN")

def get_job_activity(uuid):
    url = f"https://api.servicem8.com/api_1.0/jobactivity/{uuid}.json"
    headers = {"accept": "application/json", "X-Api-Key": SERVICEM8_API_KEY}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error fetching job activity: {e}")
        return None


def handle_job_activity(data):
    entry = data.get("entry", [{}])[0]
    job_activity_uuid = entry.get("uuid")
    if not job_activity_uuid:
        logging.error("No uuid in JobActivity entry.")
        return

    job_activity = get_job_activity(job_activity_uuid)
    if not job_activity:
        logging.error(f"Could not fetch JobActivity with uuid: {job_activity_uuid}")
        return

    if str(job_activity.get("activity_was_scheduled")) == "1":
        job_uuid = job_activity.get("job_uuid")
        if not job_uuid:
            logging.error("No job_uuid in JobActivity.")
            return

        sm8_job = get_job(job_uuid)
        sm8_job_status = sm8_job.get("status", "").strip().lower()

        start_date_str = job_activity.get("start_date")
        formatted_date = datetime.strptime(
            start_date_str, "%Y-%m-%d %H:%M:%S"
        ).strftime("%Y-%m-%d")

        deal_id = find_hubspot_deal_by_job_uuid(job_uuid)
        if deal_id:
            if sm8_job_status == "work order":
                dealstage_id = CLOSED_WON_PIPELINE_ID
            elif sm8_job_status == "quote":
                dealstage_id = CONSULT_VISIT_SCHEDULED_PIPELINE_ID
            else:
                logging.info(
                    f"Job status '{sm8_job_status}' does not trigger a dealstage update."
                )
                return

            properties_to_update = {
                "consult_visit_date": formatted_date,
                "dealstage": dealstage_id,
            }
            update_hubspot_deal(deal_id, properties_to_update)
        else:
            logging.warning(f"No HubSpot deal found with sm8_job_uuid = {job_uuid}")
