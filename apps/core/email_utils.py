import os
import logging
from typing import List, Optional

from django.conf import settings

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
    api_key = getattr(settings, 'SENDGRID_API_KEY', '')
    if not api_key:
        logger.warning('SendGrid disabled: missing SENDGRID_API_KEY')
        return
    if SendGridAPIClient is None or Mail is None:
        logger.error('SendGrid client not available: dependency missing')
        return

    sender = from_email or getattr(settings, 'SENDGRID_FROM_EMAIL', 'no-reply@example.com')

    message = Mail(
        from_email=sender,
        to_emails=to_emails,
        subject=subject,
        html_content=html_content,
    )

    logger.info('Sending email via SendGrid: to=%s subject=%s from=%s', to_emails, subject, sender)
    sg = SendGridAPIClient(api_key)
    # EU Residency pinning if configured
    if getattr(settings, 'SENDGRID_EU_RESIDENCY', False):
        try:
            sg.set_sendgrid_data_residency("eu")
            logger.info('SendGrid EU residency enabled')
        except Exception as e:
            logger.warning('Failed to enable EU residency: %s', e)

    try:
        response = sg.send(message)
        logger.info('SendGrid response: status=%s', getattr(response, 'status_code', 'unknown'))
    except Exception as e:
        logger.exception('Error sending email via SendGrid: %s', e)


