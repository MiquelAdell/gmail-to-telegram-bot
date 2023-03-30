# requirements
# pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

import base64
import os
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


def get_credentials():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds


def get_unread_emails(service):
    # Query unread emails
    query = "is:unread"
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])

    if not messages:
        print("No unread messages found.")
    else:
        print(f"Found {len(messages)} unread messages:")

        for message in messages:
            msg = service.users().messages().get(
                userId='me', id=message['id']).execute()

            # Extract subject and sender
            subject = ""
            sender = ""
            for header in msg['payload']['headers']:
                if header['name'] == "Subject":
                    subject = header['value']
                elif header['name'] == "From":
                    sender = header['value']

            print(f"Subject: {subject}\nSender: {sender}\n")


def main():
    creds = get_credentials()
    service = build('gmail', 'v1', credentials=creds)
    get_unread_emails(service)


if __name__ == '__main__':
    main()
