import os
import logging
from datetime import date
from app.utility.create_job import (
    create_servicem8_client,
    create_servicem8_job,
    create_servicem8_job_contact,
    update_hubspot_contact_sm8_client_id,
    update_hubspot_deal_sm8_job_id,
)
from app.utility.hubspot import (
    get_deal_details_with_associations,
    get_objects_properties,
)

SERVICEM8_API_KEY = os.getenv("SERVICEM8_API_KEY")
HUBSPOT_API_TOKEN = os.getenv("HUBSPOT_API_TOKEN")
REQUIRED_DEAL_STAGE_ID = "1800543694"  # Onsite Consult - Send to SM8

def handle_create_job(event_data):
    """
    Handles the job creation process, now with a deal stage check.
    """
    deal_id = event_data.get("deal_record_id")
    if not deal_id:
        logging.error("No deal_record_id provided in the event data.")
        return

    deal_details = get_objects_properties("deals", [deal_id], ["dealstage,sm8_job_id"])
    deal_properties = deal_details[0].get("properties", {})

    sm8_job_id = deal_properties.get("sm8_job_id")
    if sm8_job_id:
        logging.info(
            f"Job already exists for deal {deal_id} with sm8_job_id: {sm8_job_id}"
        )
        return

    current_stage = deal_properties.get("dealstage")
    if current_stage != REQUIRED_DEAL_STAGE_ID:
        logging.warning(
            f"Skipping job creation for deal {deal_id}. "
            f"Stage '{current_stage}' does not match required stage '{REQUIRED_DEAL_STAGE_ID}'."
        )
        return

    logging.info(f"Deal {deal_id} is in the correct stage. Proceeding with job creation.")

    contact_details = get_deal_details_with_associations(deal_id)
    if not contact_details:
        logging.error(f"Could not retrieve details for deal {deal_id}. Aborting.")
        return

    contact_record_id = contact_details.get("id", "")
    contact_props = contact_details.get("contact", {})
    client_uuid = contact_props.get("sm8_client_id")

    if not client_uuid:
        first = contact_details["contact"].get("firstname")
        last = contact_details["contact"].get("lastname")
        full_name = f"{first} {last}".strip()
        client_uuid = create_servicem8_client(full_name)
        if not client_uuid:
            return

        if contact_record_id and client_uuid:
            update_hubspot_contact_sm8_client_id(contact_record_id, client_uuid)

    service_categories = event_data.get("service_category", "")
    service_type = event_data.get("service_type", "")
    enquiry_notes = event_data.get("enquiry_notes", "")
    existing_system = event_data.get("existing_system", "")
    site_address = event_data.get("site_address", "")
    deal_customer_type = event_data.get("deal_customer_type", "")

    def format_value(label, value):
        items = [item.strip() for item in value.split(";") if item.strip()]
        return f"{label}: {', '.join(items)}" if items else f"{label}:"

    job_description = (
        f"{format_value('Service Category', service_categories)}\n"
        f"{format_value('Service Type', service_type)}\n"
        f"Existing System: {existing_system}\n"
        f"Customer Type: {deal_customer_type}\n"
        f"Enquiry Notes: {enquiry_notes.strip()}"
    )

    job_data = {
        "status": "Quote",
        "job_address": site_address,
        "job_description": job_description,
        "date": str(date.today()),
    }

    job_uuid = create_servicem8_job(job_data)
    if not job_uuid:
        return

    contact_data = {
        "firstname": contact_details["contact"].get("firstname"),
        "lastname": contact_details["contact"].get("lastname"),
        "phone": contact_details["contact"].get("phone"),
        "email": contact_details["contact"].get("email"),
    }

    create_servicem8_job_contact(job_uuid, contact_data)
    if deal_id:
        update_hubspot_deal_sm8_job_id(deal_id, job_uuid)
