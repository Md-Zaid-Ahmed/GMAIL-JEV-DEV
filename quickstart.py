import json
import os.path
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from email_cleaner import normalize

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Gmail subjects often contain emoji; the Windows console defaults to cp1252.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def get_credentials():
  """Loads saved credentials, running the browser consent flow if needed."""
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())
  return creds


def fetch_unread(service, max_results=10):
  """Returns unread emails as {sender, subject, body} dicts."""
  results = service.users().messages().list(
      userId="me",
      q="is:unread",
      maxResults=max_results,
  ).execute()

  emails = []
  for message in results.get("messages", []):
    msg = service.users().messages().get(
        userId="me",
        id=message["id"],
        format="full",
    ).execute()
    emails.append(normalize(msg))
  return emails


def main():
  try:
    service = build("gmail", "v1", credentials=get_credentials())
    emails = fetch_unread(service, max_results=10)

    if not emails:
      print("No unread emails found.")
      return

    print(json.dumps(emails, indent=2, ensure_ascii=False))

  except HttpError as error:
    # TODO(developer) - Handle errors from gmail API.
    print(f"An error occurred: {error}")


if __name__ == "__main__":
  main()
