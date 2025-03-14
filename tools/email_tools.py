# Sending emails
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import sqlite3
# Reading emails
from azure.identity import ManagedIdentityCredential
import requests

EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', '')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')

CLIENT_ID = os.getenv("CLIENT_ID", "")
REDIRECT_URI = os.getenv("REDIRECT_URI", "")
TENANT_ID = os.getenv('TENANT_ID', '')

def get_access_token(user_id: str):
    conn = sqlite3.connect("ai_employee.db")
    cursor = conn.cursor()
    cursor.execute("SELECT access_token FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0]
    else:
        return None


# def send(subject, recipient, message, attachments=None):
#     '''
#     Function to send an email with the given subject, recipient, message body, and optional attachments.
    
#     Args:
#         subject (str): The subject of the email.
#         recipient (str): The email address of the recipient.
#         message (str): The body message of the email (can include HTML).
#         attachments (list): Optional list of file paths to attach to the email.
    
#     Returns:
#         str: success string.
#     '''
#     try:
#         # Prepare the message (MIME type multipart for email)
#         msg = MIMEMultipart()
#         msg['Subject'] = subject
#         msg['From'] = EMAIL_ADDRESS  # Replace with your email address
#         msg['To'] = recipient

#         # Attach the main message body (HTML or plain text)
#         msg.attach(MIMEText(message, 'html'))  # Assuming HTML message

#         # Handle attachments (if any)
#         if attachments:
#             for attachment in attachments:
#                 try:
#                     # Open the file in binary mode
#                     with open(attachment, 'rb') as file:
#                         part = MIMEBase('application', 'octet-stream')
#                         part.set_payload(file.read())
#                         encoders.encode_base64(part)
#                         part.add_header('Content-Disposition', f'attachment; filename={attachment}')
#                         msg.attach(part)
#                 except Exception as e:
#                     return f"Error attaching file {attachment}: {e}"

#         # Send the email via Gmail SMTP
#         with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
#             smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
#             smtp.send_message(msg)
#             return f"Email successfully sent to {recipient}"

#     except Exception as e:
#         return f"Failed to send email: {e}"

def send(user_id: str, subject: str, recepient: str, message: str):
    try:
        GRAPH_API_URL = "https://graph.microsoft.com/v1.0"

        if not user_id:
            return "Error: Missing user ID."

        access_token = get_access_token(user_id)

        if not access_token:
            oauth_url = (
                f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/authorize"
                f"?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}"
                f"&scope=User.Read%20Mail.Read%20Mail.Send&prompt=consent&state={user_id}"
            )
            return f"The user isn't authenticated, please provide them with this URL: {oauth_url} and tell them to let you know when they have authenticated so you can carry on."

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # Always set content type to 'HTML'
        content_type = "HTML"

        # Compose the email message in the required JSON format
        email_data = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": content_type,
                    "content": message
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": recepient
                        }
                    }
                ]
            }
        }

        # Send the email via POST request to /sendMail
        response = requests.post(f"{GRAPH_API_URL}/me/sendMail", headers=headers, json=email_data)

        if response.status_code == 202:
            return "Email sent successfully!"
        else:
            return f"Error sending email: {response.status_code} {response.text}"

    except Exception as e:
        return f"Error: {e}"


def read(user_id: str, number_of_emails: int):
    try:
        GRAPH_API_URL = "https://graph.microsoft.com/v1.0"

        if not user_id:
            return "Error: Missing user ID."
        
        access_token = get_access_token(user_id)

        if not access_token:
            oauth_url = (
                f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/authorize"
                f"?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}"
                f"&scope=User.Read%20Mail.Read%20Mail.Send&prompt=consent&state={user_id}"
            )
            return f"The user isn't authenticated, please provide them with this URL: {oauth_url} and tell them to let you know when they have authenticated so you can carry on."

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        response = requests.get(f"{GRAPH_API_URL}/me/messages?$top={number_of_emails}", headers=headers)

        if response.status_code == 200:
            emails = response.json()
            messages = [
                f"Subject: {email['subject']}\nFrom: {email['from']['emailAddress']['address']}\nBody Preview: {email['bodyPreview']}"
                for email in emails.get("value", [])
            ]
            return messages if messages else ["No emails found."]
        else:
            return f"Error fetching emails: {response.status_code} {response.text}"

    except Exception as e:
        return f"Error: {e}"