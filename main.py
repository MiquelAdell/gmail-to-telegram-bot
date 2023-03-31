# requirements
# pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

import base64
import os
import requests
import urllib.parse
import io
import mimetypes
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv


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


def send_telegram_photo(photo_data, caption=None):
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    url = f'https://api.telegram.org/{bot_token}/sendPhoto'

    files = {'photo': ('image.jpg', photo_data, 'image/jpeg')}
    data = {'chat_id': chat_id}
    if caption:
        data['caption'] = caption

    response = requests.post(url, files=files, data=data)

    if response.status_code == 200:
        print("Photo sent to Telegram successfully.")
    else:
        print(
            f"Failed to send photo to Telegram. Response status code: {response.status_code}")


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
                userId='me', id=message['id'], format='full').execute()

            # Extract subject and sender
            subject = ""
            sender = ""
            for header in msg['payload']['headers']:
                if header['name'] == "Subject":
                    subject = header['value']
                elif header['name'] == "From":
                    sender = header['value']

            if 'parts' in msg['payload']:
                body, images = process_parts(msg['payload']['parts'])

                # Send images to Telegram
                for image_data in images:
                    print("Sending image to Telegram")  # Debugging statement
                    send_telegram_photo(image_data)

            print(f"Subject: {subject}\nSender: {sender}\nBody: {body}\n")

            text = f"From: {sender}\nSubject: {subject}\nBody:\n{body}"
            send_telegram_message(text)


def process_parts(parts):
    images = []
    body = ""
    for part in parts:
        if part['mimeType'] == 'text/plain' and 'data' in part['body']:
            body = base64.urlsafe_b64decode(
                part['body']['data']).decode('utf-8')
        elif part['mimeType'].startswith('image/') and 'data' in part['body']:
            print("Found image part")  # Debugging statement
            image_data = base64.urlsafe_b64decode(part['body']['data'])
            images.append(image_data)
        elif 'parts' in part:
            sub_body, sub_images = process_parts(part['parts'])
            body = body or sub_body
            images.extend(sub_images)
    return body, images


def send_telegram_message(text):
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    encoded_text = urllib.parse.quote(text)
    url = f'https://api.telegram.org/{bot_token}/sendMessage?chat_id={chat_id}&text={encoded_text}'

    response = requests.post(url)

    if response.status_code == 200:
        print("Message sent to Telegram successfully.")
    else:
        print(
            f"Failed to send message to Telegram. Response status code: {response.status_code} to url {url}")


def main():
    load_dotenv()
    creds = get_credentials()
    service = build('gmail', 'v1', credentials=creds)
    get_unread_emails(service)


if __name__ == '__main__':
    main()
