import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_test_summary_email(summary_text):
    smtp_server = "s7.itserver.biz"
    smtp_port = 465
    sender_email = "CLAutomation_Alert@inayaat.com"
    sender_password = "x6!493Crz"
    receiver_email = "shafees321@gmail.com"

    subject = "[SUMMARY] Automation Test Summary Report"

    # Email Body
    body = f"""
Hello,

Please find below the latest automation test summary:

{summary_text}

Regards,
Automation System
"""

    # Compose Email
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        print("[PASS] Test summary email sent successfully.")

    except Exception as e:
        print(f" [FAIL] Failed to send email: {e}")
