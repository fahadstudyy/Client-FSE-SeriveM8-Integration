import os
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv
from app.utility.job import update_job_status_to_work_order
from app.utility.hubspot import (
    get_objects_properties,
    update_hubspot_deal,
    QUOTE_SENT_PIPELINE_ID,
    QUOTE_ACCEPTED_PIPELINE_ID,
    find_hubspot_deal_by_job_uuid,
)

load_dotenv()

SERVICEM8_API_KEY = os.getenv("SERVICEM8_API_KEY")
HUBSPOT_API_TOKEN = os.getenv("HUBSPOT_API_TOKEN")


def get_job(uuid):
    url = f"https://api.servicem8.com/api_1.0/job/{uuid}.json"
    headers = {"accept": "application/json", "X-Api-Key": SERVICEM8_API_KEY}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error fetching job: {e}")
        return None


def handle_job_quote_sent(data):
    # First try to extract from Webhook payload
    entry = data.get("entry", [{}])[0]
    job_uuid = entry.get("uuid")

    # Fallback to sm8_job_id (HubSpot payload)
    if not job_uuid:
        job_uuid = data.get("sm8_job_id")

    if not job_uuid:
        logging.error("No job uuid provided (neither in entry nor sm8_job_id).")
        return

    job = get_job(job_uuid)
    if not job:
        logging.error(f"Could not fetch Job with uuid: {job_uuid}")
        return

    if job.get("quote_sent") is True:
        total_amount = job.get("total_invoice_amount")
        quote_date_str = job.get("quote_date")

        print(f"Quote date for job {job_uuid}: {quote_date_str}")
        print(f"Total amount for job {job_uuid}: {total_amount}")

        formatted_date = None
        if quote_date_str and quote_date_str != "0000-00-00 00:00:00":
            formatted_date = datetime.strptime(
                quote_date_str, "%Y-%m-%d %H:%M:%S"
            ).strftime("%Y-%m-%d")

        deal_id = find_hubspot_deal_by_job_uuid(job_uuid)

        if deal_id:
            properties = {}

            properties["dealstage"] = QUOTE_SENT_PIPELINE_ID
            if formatted_date:
                properties["quote_date"] = formatted_date
            if total_amount:
                properties["amount"] = float(total_amount)

            update_hubspot_deal(deal_id, properties)

        else:
            logging.warning(f"No HubSpot deal found with sm8_job_uuid = {job_uuid}")
    else:
        logging.info("Quote not sent yet for this job.")


def handle_sm8_job_quote_accepted(job_uuid):
    sm8_job = get_job(job_uuid)
    sm8_job_status = sm8_job.get("status", "").strip().lower()
    total_amount = sm8_job.get("total_invoice_amount")

    if sm8_job_status == "work order":
        logging.error(f"Job {job_uuid} Status is {sm8_job_status}")

        deal_id = find_hubspot_deal_by_job_uuid(job_uuid)
        if not deal_id:
            logging.warning(f"No HubSpot deal found for job_id: {job_uuid}")
            return

        properties = {}
        properties["dealstage"] = QUOTE_ACCEPTED_PIPELINE_ID
        if total_amount:
            properties["amount"] = float(total_amount)

        logging.info(f"Found deal {deal_id}, updating stage to Quote Accepted.")
        update_hubspot_deal(deal_id, properties)
    else:
        logging.info(f"Job {job_uuid} Status is {sm8_job_status}, no action taken.")

def handle_hubspot_job_quote_accepted(data):
    deal_id = data.get("deal_record_id")
    job_id = data.get("sm8_job_id")
    deal_stage = data.get("dealstage")
    logging.info(f"Handling quote accepted for job: {job_id}")

    if not job_id or not deal_id:
        logging.error("Missing job_id or deal_id.")
        return

    if deal_stage != "1793082865":  # Deposit Paid stage
        logging.info(
            f"Deal {deal_id} is not in 'Deposit Paid' stage. No action required."
        )
        return

    sm8_job = get_job(job_id)
    sm8_job_status = sm8_job.get("status", "").strip().lower()

    if sm8_job_status == "work order":
        logging.info(f"Job {job_id} is already a Work Order. No action needed.")
        return

    update_job_status_to_work_order(job_id)
