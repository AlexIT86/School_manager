import os
import logging
from typing import List, Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
except Exception:  # pragma: no cover - optional dependency in dev
    SendGridAPIClient = None
    Mail = None


logger = logging.getLogger(__name__)


def send_email(to_emails: List[str], subject: str, html_content: str, from_email: Optional[str] = None) -> None:
    """Send an email using SendGrid.

    Requires SENDGRID_API_KEY in settings. No-op if dependency or key missing.
    """
    sender = from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'SENDGRID_FROM_EMAIL', 'no-reply@example.com'))

    # 1) Try SMTP via Django if EMAIL_HOST_PASSWORD is set (or backend not console)
    try:
        if getattr(settings, 'EMAIL_HOST_PASSWORD', ''):
            logger.info('Sending email via SMTP: host=%s port=%s to=%s subject=%s', settings.EMAIL_HOST, settings.EMAIL_PORT, to_emails, subject)
            connection = get_connection(
                backend=settings.EMAIL_BACKEND,
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD,
                use_tls=getattr(settings, 'EMAIL_USE_TLS', True),
                use_ssl=getattr(settings, 'EMAIL_USE_SSL', False),
            )
            msg = EmailMultiAlternatives(subject=subject, to=to_emails, from_email=sender, connection=connection)
            msg.attach_alternative(html_content, 'text/html')
            msg.send(fail_silently=False)
            return
    except Exception as smtp_err:
        logger.warning('SMTP send failed, will try SendGrid API: %s', smtp_err)

    # 2) Fallback to SendGrid API
    api_key = getattr(settings, 'SENDGRID_API_KEY', '')
    if not api_key or SendGridAPIClient is None or Mail is None:
        logger.error('SendGrid API unavailable (missing key or dependency). Email not sent.')
        return

    message = Mail(from_email=sender, to_emails=to_emails, subject=subject, html_content=html_content)

    logger.info('Sending email via SendGrid API: to=%s subject=%s from=%s', to_emails, subject, sender)
    sg = SendGridAPIClient(api_key)
    if getattr(settings, 'SENDGRID_EU_RESIDENCY', False):
        try:
            sg.set_sendgrid_data_residency("eu")
            logger.info('SendGrid EU residency enabled')
        except Exception as e:
            logger.warning('Failed to enable EU residency: %s', e)

    response = sg.send(message)
    logger.info('SendGrid API response: status=%s', getattr(response, 'status_code', 'unknown'))


