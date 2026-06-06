import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load env variables from backend/.env
load_dotenv()

smtp_server = "smtp.gmail.com"
smtp_port = 587
sender_email = os.getenv("SMTP_USER")
sender_password = os.getenv("SMTP_PASSWORD")

print("--- SMTP Diagnostic Tool ---")
print(f"SMTP_USER: {sender_email}")
print(f"SMTP_PASSWORD Configured: {bool(sender_password)}")

if not sender_email or not sender_password:
    print("ERROR: SMTP_USER or SMTP_PASSWORD is not set in backend/.env file!")
    exit(1)

# Prompt for recipient email to send a test message
recipient = input("Enter recipient email address to send a test OTP: ").strip()
if not recipient:
    print("ERROR: Recipient email cannot be empty!")
    exit(1)

try:
    print("\nConnecting to smtp.gmail.com:587...")
    server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
    
    print("Sending EHLO...")
    server.ehlo()
    
    print("Starting TLS...")
    server.starttls()
    server.ehlo()
    
    print(f"Attempting to log in as {sender_email}...")
    server.login(sender_email, sender_password)
    print("Login SUCCESSFUL! Connected and authenticated successfully.")
    
    # Send test message
    print("Composing test email...")
    msg = MIMEMultipart()
    msg['From'] = f"Promptro Test <{sender_email}>"
    msg['To'] = recipient
    msg['Subject'] = "Promptro SMTP Test OTP"
    body = "Hello! If you are reading this, your Gmail SMTP configuration is working perfectly. Your test OTP is: 123456"
    msg.attach(MIMEText(body, 'plain'))
    
    print(f"Sending test email to {recipient}...")
    server.send_message(msg)
    server.quit()
    print("SUCCESS: Test email sent successfully! Please check your inbox.")

except smtplib.SMTPAuthenticationError as e:
    print("\nERROR: Authentication Failed!")
    print("Google rejected the login. Please double-check:")
    print("1. Your SMTP_USER email is correct.")
    print("2. Your SMTP_PASSWORD is a 16-character Google App Password (not your main account password).")
    print("3. You did not include spaces in the App Password.")
    print(f"Details: {e}")
except Exception as e:
    print(f"\nERROR: Something went wrong: {e}")
