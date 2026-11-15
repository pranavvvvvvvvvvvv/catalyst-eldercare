import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

def send_notification_email(to_email: str, subject: str, body_text: str):
    """
    Sends an automated email notification to the caretaker or patient.
    Will silently skip if SMTP credentials are not configured (useful for local dev).
    """
    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        print(f"Skipped sending email to {to_email}: SMTP credentials not configured.")
        return

    msg = MIMEMultipart()
    msg['From'] = settings.SENDER_EMAIL or settings.SMTP_USERNAME
    msg['To'] = to_email
    msg['Subject'] = f"[Catalyst ElderCare] {subject}"

    msg.attach(MIMEText(body_text, 'plain'))

    try:
        # Using SMTP_SSL for port 465
        with smtplib.SMTP_SSL(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
            print(f"Successfully sent notification email to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")