# Sending emails
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
# Reading emails
from azure.identity import ManagedIdentityCredential
import requests


EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', '')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')

def send(subject, recipient, message, attachments=None):
    '''
    Function to send an email with the given subject, recipient, message body, and optional attachments.
    
    Args:
        subject (str): The subject of the email.
        recipient (str): The email address of the recipient.
        message (str): The body message of the email (can include HTML).
        attachments (list): Optional list of file paths to attach to the email.
    
    Returns:
        str: success string.
    '''
    try:
        # Prepare the message (MIME type multipart for email)
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = EMAIL_ADDRESS  # Replace with your email address
        msg['To'] = recipient

        # Attach the main message body (HTML or plain text)
        msg.attach(MIMEText(message, 'html'))  # Assuming HTML message

        # Handle attachments (if any)
        if attachments:
            for attachment in attachments:
                try:
                    # Open the file in binary mode
                    with open(attachment, 'rb') as file:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(file.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f'attachment; filename={attachment}')
                        msg.attach(part)
                except Exception as e:
                    return f"Error attaching file {attachment}: {e}"

        # Send the email via Gmail SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            return f"Email successfully sent to {recipient}"

    except Exception as e:
        return f"Failed to send email: {e}"


def read(number_of_emails: int):
    try:
        # Microsoft Graph API endpoints
        GRAPH_API_URL = 'https://graph.microsoft.com/v1.0'

        # Managed Identity Credential (this will automatically use the managed identity of the Azure resource)
        credential = ManagedIdentityCredential()

        def get_graph_access_token():
            # Get the access token for Microsoft Graph API using Managed Identity
            token = credential.get_token("https://graph.microsoft.com/.default")
            if not token:
                return None
            return token.token
        
        def read_emails():
            token = get_graph_access_token()
            if not token:
                return "Unable to authenticate with Microsoft Graph."

            # Set up the authorization header with the access token
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }

            # Make a request to Microsoft Graph API to read the first 5 emails from the inbox
            response = requests.get(f"{GRAPH_API_URL}/me/messages?$top={number_of_emails}", headers=headers)
            messages = []
            if response.status_code == 200:
                emails = response.json()
                for email in emails['value']:
                    messages.append(f"Subject: {email['subject']} \n From: {email['from']['emailAddress']['address']} \n Body Preview: {email['body']['content']}")
            else:
                return f"Error fetching emails: {response.status_code} {response.text}"
            return messages
        
        return read_emails()
    except Exception as e:
        return f"Error: {e}"
