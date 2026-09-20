from typesafe_sdk import TypeSafeClient, Noul
from dotenv import load_dotenv
import os

if not os.getenv("TYPESAFE_API_KEY"):
    raise RuntimeError("TYPESAFE_API_KEY is missing from .env")

client = TypeSafeClient()

from typesafe_sdk import TypeSafeClient, Noul


client = TypeSafeClient()


def classify_email(email):
    state = f"""
    Sender: {email["sender"]}
    Subject: {email["subject"]}

    Body:
    {email["body"]}
    """

    response = client.system_one(
        state=state,
        questions={
            "needs_reply": Noul(
    instructions="Does this email require the user to send a reply?"
),

"requires_action": Noul(
    instructions="Does this email require the user to take some action?"
),
            "job_related": Noul(
                instructions="Is this email related to a job opportunity, recruitment, or job search?"
            ),
            "newsletter": Noul(
                instructions="Is this primarily a newsletter, digest, or recurring content email?"
            ),
        },
    )

    return {
        "needs_reply": response.answers["needs_reply"].noul,
        "requires_action": response.answers["requires_action"].noul,
        "job_related": response.answers["job_related"].noul,
        "newsletter": response.answers["newsletter"].noul,
    }

email = {
    "sender": "noreply@glassdoor.com",
    "subject": "Associate Software Engineer at SG1 Consulting Services and 6 more jobs in Hyderabad for you. Apply Now.",
    "body": """
    SimCorp is hiring
    Job alert: Software Engineer
    Your job listings for 19 September 2026

    Software Engineer
    Hyderabad
    SG1 Consulting Services
    Associate Software Engineer

    Crowe Capability Center - India
    Senior Software Engineer 2

    Arcesium
    Software Engineer III - Linux

    Amazon
    Senior Software Engineer
    """
}

result = classify_email(email)

for key, value in result.items():
    print(f"{key:15}: {value}")