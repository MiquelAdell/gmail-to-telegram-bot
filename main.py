# requirements
# pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

import base64
import os
import requests
import urllib.parse
import io
import mimetypes
import re
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv


# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

SENDERS_TO_SKIP = ['mailer@doodle.com']


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
    query = "is:unread -label:Telegram"
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

            # Skip processing the email if the sender is in the list of senders to skip
            if sender in SENDERS_TO_SKIP:
                print(f"Skipping email from: {sender}")
                continue

            if 'parts' in msg['payload']:
                body, images = process_parts(
                    msg['payload']['parts'], service, msg)

                # Send text to Telegram
                filtered_body = filter_replies(body)
                send_telegram_message(subject, sender, filtered_body)

                # Send images to Telegram
                for image_data in images:
                    print("Sending image to Telegram")  # Debugging statement
                    send_telegram_photo(image_data)

            # Add "telegram" label
            label_id = get_label_id(service, "Telegram")
            if label_id:
                modify_request = {'addLabelIds': [label_id]}
                service.users().messages().modify(
                    userId='me', id=msg['id'], body=modify_request).execute()
            else:
                print(
                    "Label 'Telegram' not found. Please create the label in Gmail first.")

            print(f"Subject: {subject}\nSender: {sender}\n")


def get_label_id(service, label_name):
    labels = service.users().labels().list(userId='me').execute()
    for label in labels['labels']:
        if label['name'] == label_name:
            return label['id']
    return None


def process_parts(parts, service, msg):
    images = []
    body = ""
    for part in parts:
        if part['mimeType'].startswith('image/'):
            print("part mimeType "+part['mimeType'])  # Debugging statement

        if part['mimeType'] == 'text/plain' and 'data' in part['body']:
            body = base64.urlsafe_b64decode(
                part['body']['data']).decode('utf-8')
        elif part['mimeType'].startswith('image/') and 'filename' in part and 'body' in part:
            print("Found image part")  # Debugging statement
            if 'data' in part['body']:
                image_data = base64.urlsafe_b64decode(part['body']['data'])
            else:
                attachment_id = part['body']['attachmentId']
                attachment = service.users().messages().attachments().get(
                    userId='me', messageId=msg['id'], id=attachment_id).execute()
                image_data = base64.urlsafe_b64decode(attachment['data'])
            images.append(image_data)
        elif 'parts' in part:
            sub_body, sub_images = process_parts(part['parts'], service, msg)
            body = body or sub_body
            images.extend(sub_images)
    return body, images


def filter_replies(body):
    # Find lines starting with '>', lines starting with 'On ... wrote:', and lines starting with a date pattern followed by the sender's email
    reply_pattern = re.compile(
        r'(^>.*$)|(^(On\s.*\s?wrote:)$)|(^El\s\d{1,2}\s\w+\s\d{4},\s[a-zA-Z]+.*<.*@.*>)(?:\n?.*)*', re.MULTILINE)
    filtered_body = re.sub(reply_pattern, '', body)
    return filtered_body.strip()


def send_telegram_message(subject, sender, body, retry_count=0):

    print("Sending message to Telegram with body length " +
          str(len(body)))  # Debugging statement
    text = f"From: {sender}\nSubject: {subject}\nBody:\n{body}"

    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    encoded_text = urllib.parse.quote(text)
    url = f'https://api.telegram.org/{bot_token}/sendMessage?chat_id={chat_id}&text={encoded_text}'

    response = requests.post(url)

    if response.status_code == 200:
        print("Message sent to Telegram successfully.")
    elif (response.status_code == 400 or response.status_code == 401) and retry_count == 0:
        if len(body) > 1000:
            body = body[0:1000] + "…"

        print(
            f"Failed to send message to Telegram with status code 400. Retrying... (Retry {retry_count + 1})")
        print(
            f"Body: {body}"
        )
        send_telegram_message(subject, sender, body,
                              retry_count=retry_count + 1)

    elif (response.status_code == 400 or response.status_code == 401) and retry_count == 1:
        body = "Sending failed. Please check the email in the web browser."

        print(
            f"Failed to send message to Telegram with status code 400. Retrying... (Retry {retry_count + 1})")
        send_telegram_message(subject, sender, body,
                              retry_count=retry_count + 1)

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
