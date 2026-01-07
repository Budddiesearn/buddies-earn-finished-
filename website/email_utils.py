import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _smtp_config():
    host = os.environ.get('SMTP_HOST')
    port = int(os.environ.get('SMTP_PORT', '587'))
    username = os.environ.get('SMTP_USERNAME')
    password = os.environ.get('SMTP_PASSWORD')
    use_tls = os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'
    sender = os.environ.get('SMTP_SENDER', username)
    return host, port, username, password, use_tls, sender


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    host, port, username, password, use_tls, sender = _smtp_config()

    if not host or not username or not password or not sender:
        # Email not configured
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to_email
    msg.attach(MIMEText(html_body, 'html'))

    try:
        server = smtplib.SMTP(host, port)
        if use_tls:
            server.starttls()
        server.login(username, password)
        server.sendmail(sender, [to_email], msg.as_string())
        server.quit()
        return True
    except Exception:
        return False


def send_activation_email(user) -> bool:
    subject = 'Payment Successful – Welcome to Buddies Earn Arena!'
    body = f'''
    <div style="font-family: Inter, Arial, sans-serif; color:#1f2937;">
      <h2 style="margin:0 0 12px; color:#0b3b8c;">Welcome, {user.first_name}!</h2>
      <p>Your payment has been <strong>successfully verified</strong> and your account is now activated.</p>
      <p>You can now access your dashboard and start earning through referrals.</p>
      <p style="margin:16px 0;">
        <a href="{os.environ.get('APP_BASE_URL', '')}" style="background:#0b3b8c; color:#fff; text-decoration:none; padding:10px 16px; border-radius:6px; display:inline-block;">Go to Dashboard</a>
      </p>
      <p style="font-size:13px; color:#6b7280;">If you didn’t expect this email, please ignore it.</p>
    </div>
    '''
    return send_email(user.email, subject, body)
